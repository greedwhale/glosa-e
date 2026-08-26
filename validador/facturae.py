"""Reglas de negocio del formato Facturae.

Facturae es el formato nacional español, el único que la Administración acepta
por FACe y el que de verdad se usa aquí. Hasta ahora este validador lo
reconocía, le comprobaba la forma contra el XSD y le sacaba el código único del
RD 238/2026 —pero **no le miraba ni un número**. Una factura Facturae con el
total inventado salía «sin errores».

De dónde salen estas reglas
---------------------------
No de la memoria de nadie: del propio esquema. El XSD de Facturae lleva la
aritmética escrita en sus anotaciones, en castellano y con nombre y apellidos.
Por ejemplo, en `TotalGrossAmountBeforeTaxes`:

    «Total importe bruto antes de impuestos. Resultado de: TotalGrossAmount -
    TotalGeneralDiscounts + TotalGeneralSurcharges.»

Cada regla de este módulo cita en su comentario la frase del esquema de la que
sale. Donde el esquema dice «Resultado de» o «Sumatorio de», la queja es ERROR:
no es una opinión, es la definición del campo. Donde el esquema **se abstiene**
—y lo hace, ver `_reglas_cuota`— la queja es AVISO.

Los códigos son nuestros
------------------------
Facturae no numera sus reglas como hace EN 16931 con las BR-*. Así que estos
códigos —FE-BASE, FE-TOTAL...— los ponemos aquí y se llaman por lo que
comprueban, no por un número. Es a propósito: inventar un «FE-07» que suene a
oficial es exactamente el error que ya se cometió una vez en este proyecto con
unos BR-IG-* que no existen en ninguna norma.

Por qué no se reutiliza `sintaxis.Sintaxis`
-------------------------------------------
Porque Facturae no encaja en ese molde, y forzarlo mentiría sobre lo que se
está comprobando:

1. **Un fichero Facturae son varias facturas.** `Facturae/Invoices/Invoice*`
   con una cabecera de lote encima que declara sus propios totales. En UBL y en
   CII el fichero *es* la factura.
2. **No hay categorías de IVA.** EN 16931 clasifica cada operación con una
   letra (S, Z, E, AE, K, G, O) y media norma cuelga de ahí. Facturae usa
   códigos de impuesto (01 IVA, 03 IGIC...) y no tiene equivalente. Toda la
   familia BR-{X}-* de `iva.py` no se puede traducir; se dejaría de comprobar
   igual, pero sin decirlo.
3. **Hay retenciones.** El IRPF es un bloque de primera clase en Facturae
   (`TaxesWithheld`) y resta del total. En el modelo europeo no existe.

Namespaces
----------
Se busca por `local-name()`. Facturae ha cambiado de namespace en cada versión
—2007/v3.1, 2009/v3.2, 2014/v3.2.1, formato/Versiones/...— y además el fichero
puede llegar envuelto en una firma XAdES, con la factura colgando de dentro.
Comprobado sobre los cinco esquemas: de la 3.0 a la 3.2.2 los nombres de los
elementos no han cambiado; solo se han añadido. Un mapa por versión sería
mantener cinco copias de lo mismo.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from validador.formato import FACTURAE, Deteccion
from validador.incidencias import AVISO, ERROR, Incidencia

__all__ = ["reglas"]


# --- Cuánto se puede desviar una suma --------------------------------------

# Los importes se declaran redondeados. Cada cifra escrita puede estar hasta
# medio céntimo lejos de su valor exacto, así que comparar dos cifras admite un
# céntimo de holgura: es la tolerancia de siempre y sale de aquí.
MEDIO_CENTIMO = Decimal("0.005")
UN_CENTIMO = Decimal("0.01")


def _cuadra(calculado: Decimal, declarado: Decimal, sumandos: int = 1) -> bool:
    """¿Coinciden dos importes, contando el redondeo permitido?

    Con un solo sumando esto es la tolerancia de un céntimo de toda la vida.
    Con varios hay que abrirla, porque los redondeos se acumulan: si sumas N
    cifras ya redondeadas y comparas con un total también redondeado, la
    desviación legítima llega a medio céntimo por cifra más medio del total.

    No es teórico. `alphp_factura-prueba-v1-2-0.xml`, que es correcta, suma tres
    cuotas —34,91 + 34,91 + 209,43 = 279,25— y declara 279,24. Con la
    tolerancia fija se salva por el pelo; con una cuota más, no. Una factura
    buena rechazada por un céntimo es peor que un céntimo sin detectar.
    """
    return abs(calculado - declarado) <= MEDIO_CENTIMO * (sumandos + 1)


def _fmt(valor: Decimal | None) -> str:
    return "(vacío)" if valor is None else f"{valor:.2f}"


def _fmt_tipo(valor: Decimal | None) -> str:
    if valor is None:
        return "(sin tipo)"
    normalizado = valor.normalize()
    if normalizado == normalizado.to_integral_value():
        normalizado = normalizado.quantize(Decimal(1))
    return f"{normalizado}%"


# --- Lectura ---------------------------------------------------------------


def _hijos(nodo, *nombres: str) -> list:
    """Descendientes por nombre local, bajando hijo a hijo desde `nodo`.

    Relativo a propósito. Con «//» la consulta arrancaría de la raíz del
    documento sin importar desde dónde se llame, y en un fichero con dos
    facturas los totales de la primera se le medirían a la segunda.
    """
    ruta = "./" + "/".join(f"*[local-name()='{nombre}']" for nombre in nombres)
    return nodo.xpath(ruta)


def _texto(nodo, *nombres: str) -> str | None:
    encontrados = _hijos(nodo, *nombres)
    if not encontrados:
        return None
    crudo = (encontrados[0].text or "").strip()
    return crudo or None


def _numero(nodo, *nombres: str) -> Decimal | None:
    crudo = _texto(nodo, *nombres)
    if crudo is None:
        return None
    try:
        return Decimal(crudo)
    except InvalidOperation:
        # Que el importe no sea un número es un problema de forma, y de eso ya
        # se queja el XSD con su propio mensaje. Aquí lo que toca es callarse y
        # no comprobar esa suma, no inventar una segunda queja peor redactada.
        return None


def _o_cero(nodo, *nombres: str) -> Decimal:
    """Un importe opcional que, si no está, no suma nada.

    Casi todos los campos de ajuste son opcionales y varios ni existían en
    Facturae 3.0. Ausente y cero valen lo mismo para la aritmética.
    """
    return _numero(nodo, *nombres) or Decimal(0)


def _suma(nodos, *nombres: str) -> tuple[Decimal, int]:
    """Lo que suman unos importes, y cuántos son.

    La cuenta hace falta para la tolerancia: ver `_cuadra`.
    """
    total = Decimal(0)
    cuantos = 0
    for nodo in nodos:
        cantidad = _numero(nodo, *nombres)
        if cantidad is not None:
            total += cantidad
            cuantos += 1
    return total, cuantos


# --- Impuestos -------------------------------------------------------------

# Los impuestos cuyo tipo es, por ley, un porcentaje de la base. El esquema
# avisa de que no siempre lo es —«Téngase en cuenta que no siempre son
# porcentajes»— y hay unos cuantos que se liquidan por unidad física: los
# impuestos especiales (07) van por litro o por kilo. A esos no se les puede
# comprobar la cuota multiplicando, así que no se les comprueba.
PORCENTUALES = frozenset({"01", "02", "03", "04", "17", "18", "19"})

NOMBRE_IMPUESTO = {
    "01": "IVA",
    "02": "IPSI",
    "03": "IGIC",
    "04": "IRPF",
    "05": "otro impuesto",
    "06": "ITPAJD",
    "07": "impuestos especiales",
    "17": "IVA de agencias de viajes",
    "18": "IGIC de agencias de viajes",
    "19": "IPSI de agencias de viajes",
}


@dataclass(frozen=True)
class Impuesto:
    """Una entrada de impuesto, repercutido o retenido."""

    codigo: str | None
    tipo: Decimal | None
    base: Decimal | None
    cuota: Decimal | None
    recargo_tipo: Decimal | None
    recargo_cuota: Decimal | None

    @property
    def nombre(self) -> str:
        conocido = NOMBRE_IMPUESTO.get(self.codigo or "")
        if conocido is None:
            return f"impuesto {self.codigo}" if self.codigo else "impuesto"
        return conocido

    def __str__(self) -> str:
        return f"{self.nombre} al {_fmt_tipo(self.tipo)}"


def _impuestos(nodo, bloque: str) -> list[Impuesto]:
    """Las entradas de `TaxesOutputs` o de `TaxesWithheld` que cuelgan de aquí."""
    return [
        Impuesto(
            codigo=_texto(tributo, "TaxTypeCode"),
            tipo=_numero(tributo, "TaxRate"),
            base=_numero(tributo, "TaxableBase", "TotalAmount"),
            cuota=_numero(tributo, "TaxAmount", "TotalAmount"),
            recargo_tipo=_numero(tributo, "EquivalenceSurcharge"),
            recargo_cuota=_numero(
                tributo, "EquivalenceSurchargeAmount", "TotalAmount"
            ),
        )
        for tributo in _hijos(nodo, bloque, "Tax")
    ]


def _repercutido(tributos: list[Impuesto]) -> tuple[Decimal, int]:
    """Lo que suma el desglose de impuestos repercutidos, y con cuántas cifras.

    El esquema, en `TotalTaxOutputs`: «Sumatorio de todas Cuotas **y Recargos
    de Equivalencia**». El recargo va dentro, no aparte. Sin sumarlo,
    `alphp_factura-prueba-v1-2-0.xml` —que es correcta— daría 244,34 frente a
    los 279,24 que declara: 35 euros de diferencia por leer mal una frase.

    Se cuentan **cifras, no entradas**: una entrada con recargo de equivalencia
    aporta dos importes redondeados a la suma, así que la holgura de redondeo
    que le toca es la de dos. Contando entradas, una factura correcta con dos
    impuestos y un recargo se rechazaba por dos céntimos.
    """
    total = Decimal(0)
    cifras = 0
    for tributo in tributos:
        for importe in (tributo.cuota, tributo.recargo_cuota):
            if importe is not None:
                total += importe
                cifras += 1
    return total, cifras


def _por_tipo_de_impuesto(
    tributos: list[Impuesto],
) -> dict[str | None, tuple[Decimal, int]]:
    """Lo que cada clase de impuesto declara como base, sumado y contado.

    Se agrupa por clase porque una misma operación puede llevar dos impuestos
    distintos sobre la misma base —en Ceuta se factura con IPSI y en la
    Península con IVA, y hay facturas que declaran los dos—. Sumarlos todos
    daría el doble de la base y acusaría de descuadre a una factura correcta.
    """
    bases: dict[str | None, tuple[Decimal, int]] = {}
    for tributo in tributos:
        if tributo.base is None:
            continue
        suma, cuantas = bases.get(tributo.codigo, (Decimal(0), 0))
        bases[tributo.codigo] = (suma + tributo.base, cuantas + 1)
    return bases


# --- Reglas de una línea ---------------------------------------------------


def _ajustes(nodo, bloque: str, envoltorio: str) -> list:
    return _hijos(nodo, bloque, envoltorio)


def _reglas_ajustes(
    nodo, donde: str, sobre: Decimal | None, que: str
) -> list[Incidencia]:
    """El importe de cada descuento y cada cargo frente a su porcentaje.

    El esquema define `DiscountRate` como «Porcentaje a descontar del Total
    Importe Bruto» y `ChargeRate` como «Porcentaje a cargar sobre el TIB». Cuál
    es ese TIB depende de dónde cuelgue el ajuste: en una línea es su
    `TotalCost`, y en la factura el `TotalGrossAmount`. Comprobado en tres
    ficheros ajenos independientes —1.200 x 3% = 36, 460 x 5% = 23,
    1.212 x 4% = 48,48— así que la lectura no es una suposición.

    Va como aviso: el esquema lo describe, pero no lo escribe como fórmula, y
    el porcentaje es opcional. Quien declara solo el importe no incumple nada.
    """
    if sobre is None:
        return []
    incidencias: list[Incidencia] = []
    for bloque, envoltorio, campo_tipo, campo_importe, palabra in (
        ("DiscountsAndRebates", "Discount", "DiscountRate", "DiscountAmount", "descuento"),
        ("Charges", "Charge", "ChargeRate", "ChargeAmount", "cargo"),
        ("GeneralDiscounts", "Discount", "DiscountRate", "DiscountAmount", "descuento"),
        ("GeneralSurcharges", "Charge", "ChargeRate", "ChargeAmount", "cargo"),
    ):
        for ajuste in _ajustes(nodo, bloque, envoltorio):
            tipo = _numero(ajuste, campo_tipo)
            importe = _numero(ajuste, campo_importe)
            if tipo is None or importe is None or not tipo:
                continue
            calculado = (sobre * tipo / Decimal(100)).quantize(Decimal("0.01"))
            if _cuadra(calculado, importe):
                continue
            motivo = _texto(ajuste, campo_tipo.replace("Rate", "Reason")) or palabra
            incidencias.append(
                Incidencia(
                    "FE-AJUSTE",
                    AVISO,
                    f"El importe del {palabra} «{motivo}» no sale de aplicar su "
                    f"porcentaje a {que}.",
                    campo=f"{donde}{palabra.capitalize()} «{motivo}»",
                    esperado=f"{calculado:.2f}  ({sobre:.2f} x {_fmt_tipo(tipo)})",
                    encontrado=_fmt(importe),
                )
            )
    return incidencias


def _reglas_linea(linea, donde: str, numero: int) -> list[Incidencia]:
    """Lo que el esquema exige de una línea de detalle."""
    incidencias: list[Incidencia] = []
    etiqueta = _texto(linea, "ItemDescription") or f"línea {numero}"
    donde_linea = f"{donde}Línea {numero} «{etiqueta[:40]}»: "

    cantidad = _numero(linea, "Quantity")
    precio = _numero(linea, "UnitPriceWithoutTax")
    coste = _numero(linea, "TotalCost")
    bruto = _numero(linea, "GrossAmount")

    # «Coste Total. Resultado: Quantity x UnitPriceWithoutTax.»
    if cantidad is not None and precio is not None and coste is not None:
        calculado = cantidad * precio
        if not _cuadra(calculado, coste):
            incidencias.append(
                Incidencia(
                    "FE-LINEA-COSTE",
                    ERROR,
                    "El coste total de la línea no es la cantidad por el precio "
                    "unitario.",
                    campo=f"{donde_linea}Coste total",
                    esperado=f"{calculado:.2f}  ({cantidad} x {precio})",
                    encontrado=_fmt(coste),
                )
            )

    # «Importe bruto. Resultado: TotalCost - DiscountAmount + ChargeAmount.»
    descuentos, cuantos_d = _suma(
        _ajustes(linea, "DiscountsAndRebates", "Discount"), "DiscountAmount"
    )
    cargos, cuantos_c = _suma(_ajustes(linea, "Charges", "Charge"), "ChargeAmount")
    if coste is not None and bruto is not None:
        calculado = coste - descuentos + cargos
        if not _cuadra(calculado, bruto, cuantos_d + cuantos_c + 1):
            detalle = f"{coste:.2f}"
            if descuentos:
                detalle += f" - {descuentos:.2f} de descuentos"
            if cargos:
                detalle += f" + {cargos:.2f} de cargos"
            incidencias.append(
                Incidencia(
                    "FE-LINEA-BRUTO",
                    ERROR,
                    "El importe bruto de la línea no cuadra con su coste menos "
                    "los descuentos más los cargos.",
                    campo=f"{donde_linea}Importe bruto",
                    esperado=f"{calculado:.2f}  ({detalle})",
                    encontrado=_fmt(bruto),
                )
            )

    incidencias.extend(_reglas_ajustes(linea, donde_linea, coste, "su coste total"))

    repercutidos = _impuestos(linea, "TaxesOutputs")
    incidencias.extend(_reglas_cuota(repercutidos, donde_linea))
    incidencias.extend(_reglas_cuota(_impuestos(linea, "TaxesWithheld"), donde_linea))

    # Lo que la línea factura tiene que ser lo que declara como base. No está
    # escrito como fórmula en el esquema, de ahí el aviso, pero es donde se ve
    # antes el fallo más caro de todos: facturar algo y no declararlo.
    if bruto is not None and repercutidos:
        for codigo, (base, cuantas) in _por_tipo_de_impuesto(repercutidos).items():
            if _cuadra(base, bruto, cuantas):
                continue
            nombre = NOMBRE_IMPUESTO.get(codigo or "", f"impuesto {codigo}")
            incidencias.append(
                Incidencia(
                    "FE-LINEA-SIN-GRAVAR",
                    AVISO,
                    f"La línea factura {bruto:.2f} pero solo declara "
                    f"{base:.2f} como base de {nombre}. Quedan "
                    f"{abs(bruto - base):.2f} sin gravar ni justificar.",
                    campo=f"{donde_linea}Base de {nombre}",
                    esperado=f"{bruto:.2f}, que es el importe bruto de la línea",
                    encontrado=_fmt(base),
                )
            )

    return incidencias


def _reglas_cuota(tributos: list[Impuesto], donde: str) -> list[Incidencia]:
    """La cuota frente al tipo y la base.

    Aviso, no error, y aquí la diferencia con EN 16931 no es un descuido. La
    norma europea **manda** que la cuota salga de aplicar el tipo a la base
    (BR-CO-17), y `iva.py` lo da como error. El esquema de Facturae dice justo
    lo contrario sobre su propio campo: «La legislación del impuesto
    correspondiente determina cómo se calcula la cuota». Si la fuente se
    abstiene, nosotros no vamos a sentenciar.
    """
    incidencias: list[Incidencia] = []
    for tributo in tributos:
        if tributo.codigo not in PORCENTUALES:
            continue
        if tributo.base is None or tributo.tipo is None or tributo.cuota is None:
            continue
        calculada = (tributo.base * tributo.tipo / Decimal(100)).quantize(
            Decimal("0.01")
        )
        if not _cuadra(calculada, tributo.cuota):
            incidencias.append(
                Incidencia(
                    "FE-CUOTA",
                    AVISO,
                    f"La cuota de {tributo} no sale de aplicar el tipo a la base.",
                    campo=f"{donde}Cuota de {tributo}",
                    esperado=(
                        f"{calculada:.2f}  ({tributo.base:.2f} x "
                        f"{_fmt_tipo(tributo.tipo)})"
                    ),
                    encontrado=_fmt(tributo.cuota),
                )
            )

        # «Cuota. Importe resultante de aplicar a la Base Imponible, la misma
        # que para el IVA, el porcentaje indicado en EquivalenceSurcharge.»
        if tributo.recargo_tipo is None or tributo.recargo_cuota is None:
            continue
        calculado = (
            tributo.base * tributo.recargo_tipo / Decimal(100)
        ).quantize(Decimal("0.01"))
        if not _cuadra(calculado, tributo.recargo_cuota):
            incidencias.append(
                Incidencia(
                    "FE-RECARGO",
                    AVISO,
                    "El recargo de equivalencia no sale de aplicar su porcentaje "
                    "a la misma base que el impuesto.",
                    campo=f"{donde}Recargo de equivalencia de {tributo}",
                    esperado=(
                        f"{calculado:.2f}  ({tributo.base:.2f} x "
                        f"{_fmt_tipo(tributo.recargo_tipo)})"
                    ),
                    encontrado=_fmt(tributo.recargo_cuota),
                )
            )
    return incidencias


# --- Reglas de una factura -------------------------------------------------


def _cadena_de_totales(totales, donde: str) -> list[Incidencia]:
    """Las fórmulas del bloque `InvoiceTotals`, tal como las escribe el esquema.

    Son una cadena: cada eslabón parte del anterior. Si el primero está mal,
    los siguientes fallan en cascada aunque estén bien calculados —así que cada
    uno se comprueba contra lo que la factura **declara** en el eslabón
    anterior, no contra lo que nosotros hemos calculado. Así el que se equivoca
    en el bruto recibe una queja, no seis.
    """
    incidencias: list[Incidencia] = []

    def declarado(nombre: str) -> Decimal | None:
        return _numero(totales, nombre)

    def cero(nombre: str) -> Decimal:
        return _o_cero(totales, nombre)

    bruto = declarado("TotalGrossAmount")
    descuentos = declarado("TotalGeneralDiscounts")
    cargos = declarado("TotalGeneralSurcharges")
    base = declarado("TotalGrossAmountBeforeTaxes")
    repercutidos = declarado("TotalTaxOutputs")
    retenidos = declarado("TotalTaxesWithheld")
    total = declarado("InvoiceTotal")
    anticipos = declarado("TotalPaymentsOnAccount")
    pendiente = declarado("TotalOutstandingAmount")
    ejecutar = declarado("TotalExecutableAmount")

    # «Total general de descuentos. Sumatorio de los importes de los diferentes
    # campos GeneralDiscounts.» Ídem para los cargos.
    for detalle, envoltorio, campo, valor, codigo, palabra in (
        ("GeneralDiscounts", "Discount", "DiscountAmount", descuentos,
         "FE-DESCUENTOS", "descuentos"),
        ("GeneralSurcharges", "Charge", "ChargeAmount", cargos,
         "FE-CARGOS", "cargos"),
    ):
        detallados = _ajustes(totales, detalle, envoltorio)
        if not detallados or valor is None:
            continue
        sumado, cuantos = _suma(detallados, campo)
        if _cuadra(sumado, valor, cuantos):
            continue
        incidencias.append(
            Incidencia(
                codigo,
                ERROR,
                f"El total general de {palabra} no es la suma de los {palabra} "
                "que detalla la factura.",
                campo=f"{donde}Total general de {palabra}",
                esperado=f"{sumado:.2f}  (lo que suman los {cuantos} detallados)",
                encontrado=_fmt(valor),
            )
        )

    # «Total importe bruto antes de impuestos. Resultado de: TotalGrossAmount -
    # TotalGeneralDiscounts + TotalGeneralSurcharges.»
    if bruto is not None and base is not None:
        calculada = bruto - cero("TotalGeneralDiscounts") + cero(
            "TotalGeneralSurcharges"
        )
        if not _cuadra(calculada, base, 3):
            detalle = f"{bruto:.2f}"
            if cero("TotalGeneralDiscounts"):
                detalle += f" - {cero('TotalGeneralDiscounts'):.2f} de descuentos"
            if cero("TotalGeneralSurcharges"):
                detalle += f" + {cero('TotalGeneralSurcharges'):.2f} de cargos"
            incidencias.append(
                Incidencia(
                    "FE-BASE",
                    ERROR,
                    "La base antes de impuestos no cuadra con el importe bruto "
                    "menos los descuentos más los cargos generales.",
                    campo=f"{donde}Total bruto antes de impuestos",
                    esperado=f"{calculada:.2f}  ({detalle})",
                    encontrado=_fmt(base),
                )
            )

    # «Total factura. Resultado de: TotalGrossAmountBeforeTaxes +
    # TotalTaxOutputs - TotalTaxesWithheld.»
    if base is not None and repercutidos is not None and total is not None:
        calculado = base + repercutidos - (retenidos or Decimal(0))
        if not _cuadra(calculado, total, 3):
            detalle = f"{base:.2f} + {repercutidos:.2f} de impuestos"
            if retenidos:
                detalle += f" - {retenidos:.2f} de retenciones"
            incidencias.append(
                Incidencia(
                    "FE-TOTAL",
                    ERROR,
                    "El total de la factura no es la base más los impuestos "
                    "repercutidos menos los retenidos.",
                    campo=f"{donde}Total factura",
                    esperado=f"{calculado:.2f}  ({detalle})",
                    encontrado=_fmt(total),
                )
            )

    # «Total de anticipos. Sumatorio de los campos PaymentOnAccountAmount.»
    detallados = _ajustes(totales, "PaymentsOnAccount", "PaymentOnAccount")
    if detallados and anticipos is not None:
        sumado, cuantos = _suma(detallados, "PaymentOnAccountAmount")
        if not _cuadra(sumado, anticipos, cuantos):
            incidencias.append(
                Incidencia(
                    "FE-ANTICIPOS",
                    ERROR,
                    "El total de anticipos no es la suma de los anticipos que "
                    "detalla la factura.",
                    campo=f"{donde}Total de anticipos",
                    esperado=f"{sumado:.2f}  (lo que suman los {cuantos} detallados)",
                    encontrado=_fmt(anticipos),
                )
            )

    # «Total a pagar. Resultado de: InvoiceTotal - (Total subvenciones +
    # TotalPaymentsOnAccount).»
    subvenciones, cuantas = _suma(
        _ajustes(totales, "Subsidies", "Subsidy"), "SubsidyAmount"
    )
    if total is not None and pendiente is not None:
        calculado = total - subvenciones - (anticipos or Decimal(0))
        if not _cuadra(calculado, pendiente, cuantas + 2):
            detalle = f"{total:.2f}"
            if subvenciones:
                detalle += f" - {subvenciones:.2f} de subvenciones"
            if anticipos:
                detalle += f" - {anticipos:.2f} de anticipos"
            incidencias.append(
                Incidencia(
                    "FE-PENDIENTE",
                    ERROR,
                    "El total a pagar no cuadra con el total de la factura menos "
                    "las subvenciones y los anticipos.",
                    campo=f"{donde}Total a pagar",
                    esperado=f"{calculado:.2f}  ({detalle})",
                    encontrado=_fmt(pendiente),
                )
            )

    # «Total a ejecutar. Resultado de: TotalOutstandingAmount -
    # WithholdingAmount - PaymentInKindAmount + TotalReimbursableExpenses +
    # TotalFinancialExpenses.»
    retenidas, cuantas_r = _suma(
        _hijos(totales, "AmountsWithheld"), "WithholdingAmount"
    )
    especie, cuantas_e = _suma(_hijos(totales, "PaymentInKind"), "PaymentInKindAmount")
    if pendiente is not None and ejecutar is not None:
        suplidos = cero("TotalReimbursableExpenses")
        financieros = cero("TotalFinancialExpenses")
        calculado = pendiente - retenidas - especie + suplidos + financieros
        if not _cuadra(calculado, ejecutar, cuantas_r + cuantas_e + 3):
            detalle = f"{pendiente:.2f}"
            for cantidad, signo, palabra in (
                (retenidas, "-", "retenido"),
                (especie, "-", "pagado en especie"),
                (suplidos, "+", "de suplidos"),
                (financieros, "+", "de gastos financieros"),
            ):
                if cantidad:
                    detalle += f" {signo} {cantidad:.2f} {palabra}"
            incidencias.append(
                Incidencia(
                    "FE-EJECUTAR",
                    ERROR,
                    "El total a ejecutar no cuadra con el total a pagar una vez "
                    "aplicadas retenciones, suplidos y gastos financieros.",
                    campo=f"{donde}Total a ejecutar",
                    esperado=f"{calculado:.2f}  ({detalle})",
                    encontrado=_fmt(ejecutar),
                )
            )

    return incidencias


def _reglas_impuestos_de_la_factura(
    factura, totales, donde: str
) -> list[Incidencia]:
    """El desglose de impuestos frente a los totales que declara la factura."""
    incidencias: list[Incidencia] = []
    repercutidos = _impuestos(factura, "TaxesOutputs")
    retenidos = _impuestos(factura, "TaxesWithheld")

    incidencias.extend(_reglas_cuota(repercutidos, donde))
    incidencias.extend(_reglas_cuota(retenidos, donde))

    # «Total impuestos repercutidos. Sumatorio de todas Cuotas y Recargos de
    # Equivalencia.»
    declarado = _numero(totales, "TotalTaxOutputs")
    if repercutidos and declarado is not None:
        sumado, cifras = _repercutido(repercutidos)
        if cifras and not _cuadra(sumado, declarado, cifras):
            incidencias.append(
                Incidencia(
                    "FE-REPERCUTIDOS",
                    ERROR,
                    "El total de impuestos repercutidos no es la suma de las "
                    "cuotas del desglose, recargos de equivalencia incluidos.",
                    campo=f"{donde}Total impuestos repercutidos",
                    esperado=(
                        f"{sumado:.2f}  (lo que suman las {cifras} cuotas "
                        "del desglose)"
                    ),
                    encontrado=_fmt(declarado),
                )
            )

    # «Total impuestos retenidos.» El esquema no escribe la fórmula, pero un
    # total de retenciones que no sea la suma de las retenciones detalladas no
    # tiene otra lectura posible.
    declarado = _numero(totales, "TotalTaxesWithheld")
    if retenidos and declarado is not None:
        sumado, cuantos = Decimal(0), 0
        for tributo in retenidos:
            if tributo.cuota is not None:
                sumado += tributo.cuota
                cuantos += 1
        if cuantos and not _cuadra(sumado, declarado, cuantos):
            incidencias.append(
                Incidencia(
                    "FE-RETENIDOS",
                    ERROR,
                    "El total de impuestos retenidos no es la suma de las "
                    "retenciones que detalla la factura.",
                    campo=f"{donde}Total impuestos retenidos",
                    esperado=f"{sumado:.2f}  (lo que suman las {cuantos} retenciones)",
                    encontrado=_fmt(declarado),
                )
            )

    # Lo que se factura tiene que estar gravado o justificado. Aviso, porque el
    # esquema no lo escribe como fórmula y hay regímenes —el especial del grupo
    # de entidades, el de agencias de viajes— donde la base del impuesto no es
    # el importe facturado. Pero es la comprobación que caza el fallo que más
    # dinero mueve, y sin ella dos de las nueve facturas oficiales de prueba
    # pasan sin que nadie diga que les falta base por gravar.
    base = _numero(totales, "TotalGrossAmountBeforeTaxes")
    if base is not None and repercutidos:
        for codigo, (declarada, cuantas) in _por_tipo_de_impuesto(
            repercutidos
        ).items():
            if _cuadra(declarada, base, cuantas):
                continue
            nombre = NOMBRE_IMPUESTO.get(codigo or "", f"impuesto {codigo}")
            incidencias.append(
                Incidencia(
                    "FE-SIN-GRAVAR",
                    AVISO,
                    f"La factura tiene una base de {base:.2f} pero solo declara "
                    f"{declarada:.2f} como base de {nombre}. Quedan "
                    f"{abs(base - declarada):.2f} sin gravar ni justificar.",
                    campo=f"{donde}Base de {nombre} en el desglose",
                    esperado=f"{base:.2f}, que es la base antes de impuestos",
                    encontrado=_fmt(declarada),
                )
            )

    return incidencias


def _etiqueta(factura, cuantas: int) -> str:
    """Cómo nombrar a la factura dentro del fichero.

    Con una sola no se nombra: sobra repetir «Factura 2008/155» en cada queja
    de un fichero que no tiene otra. Con varias es imprescindible, porque si no
    el informe dice que un total no cuadra sin decir el de cuál.
    """
    if cuantas <= 1:
        return ""
    serie = _texto(factura, "InvoiceHeader", "InvoiceSeriesCode") or ""
    numero = _texto(factura, "InvoiceHeader", "InvoiceNumber") or "(sin número)"
    return f"Factura {serie}{numero} · "


def _reglas_factura(factura, donde: str) -> list[Incidencia]:
    incidencias: list[Incidencia] = []
    lineas = _hijos(factura, "Items", "InvoiceLine")
    for numero, linea in enumerate(lineas, start=1):
        incidencias.extend(_reglas_linea(linea, donde, numero))

    bloques = _hijos(factura, "InvoiceTotals")
    if not bloques:
        # Sin totales no hay nada que cuadrar. El XSD ya se queja de que falte
        # un bloque obligatorio, y decirlo otra vez con otras palabras no
        # ayuda a nadie.
        return incidencias
    totales = bloques[0]

    # «Total Importe Bruto. Suma total de importes brutos de los detalles de la
    # factura.»
    declarado = _numero(totales, "TotalGrossAmount")
    if lineas and declarado is not None:
        sumado, cuantas = _suma(lineas, "GrossAmount")
        if cuantas == len(lineas) and not _cuadra(sumado, declarado, cuantas):
            incidencias.append(
                Incidencia(
                    "FE-BRUTO",
                    ERROR,
                    "El importe bruto total no es la suma de los importes brutos "
                    "de las líneas. Suele ser una línea añadida o cambiada sin "
                    "recalcular el total.",
                    campo=f"{donde}Total importe bruto",
                    esperado=(
                        f"{sumado:.2f}  (suma de "
                        + ("la única línea" if cuantas == 1 else f"las {cuantas} líneas")
                        + ")"
                    ),
                    encontrado=_fmt(declarado),
                )
            )

    incidencias.extend(
        _reglas_ajustes(totales, donde, declarado, "el importe bruto total")
    )
    incidencias.extend(_cadena_de_totales(totales, donde))
    incidencias.extend(_reglas_impuestos_de_la_factura(factura, totales, donde))
    return incidencias


# --- Reglas del fichero ----------------------------------------------------


def _reglas_lote(raiz, facturas: list) -> list[Incidencia]:
    """La cabecera del fichero frente a las facturas que trae dentro.

    Este bloque no tiene equivalente en UBL ni en CII, donde un fichero es una
    factura y no hay nada que resumir. Aquí la cabecera declara cuántas
    facturas hay y cuánto suman, así que puede mentir.
    """
    cabeceras = _hijos(raiz, "FileHeader")
    if not cabeceras:
        return []
    cabecera = cabeceras[0]
    incidencias: list[Incidencia] = []

    lotes = _hijos(cabecera, "Batch")
    if not lotes:
        return []
    lote = lotes[0]

    # «Refleja, cuando es lote, el número de facturas del mismo. Siempre será
    # valor "1" cuando el campo Modality tenga el valor "I".»
    declaradas = _numero(lote, "InvoicesCount")
    if declaradas is not None and declaradas != len(facturas):
        incidencias.append(
            Incidencia(
                "FE-LOTE-CUENTA",
                ERROR,
                "La cabecera dice que el fichero trae un número de facturas "
                "distinto del que trae de verdad.",
                campo="Número total de facturas",
                esperado=f"{len(facturas)}, que es lo que hay en el fichero",
                encontrado=str(declaradas.normalize()),
            )
        )

    modalidad = _texto(cabecera, "Modality")
    if modalidad == "I" and len(facturas) > 1:
        incidencias.append(
            Incidencia(
                "FE-MODALIDAD",
                ERROR,
                "El fichero se declara individual pero trae más de una factura. "
                "Con varias, la modalidad es «L» (lote).",
                campo="Modalidad",
                esperado="L, porque el fichero trae varias facturas",
                encontrado="I (individual)",
            )
        )

    # «Total facturas. Suma de los importes InvoiceTotal del Fichero», y lo
    # mismo para el total a pagar y el total a ejecutar.
    for campo, dentro, codigo, nombre in (
        ("TotalInvoicesAmount", "InvoiceTotal", "FE-LOTE-TOTAL", "total de facturas"),
        (
            "TotalOutstandingAmount",
            "TotalOutstandingAmount",
            "FE-LOTE-PENDIENTE",
            "total a pagar del fichero",
        ),
        (
            "TotalExecutableAmount",
            "TotalExecutableAmount",
            "FE-LOTE-EJECUTAR",
            "total a ejecutar del fichero",
        ),
    ):
        declarado = _numero(lote, campo, "TotalAmount")
        if declarado is None:
            continue
        totales = [t for f in facturas for t in _hijos(f, "InvoiceTotals")]
        sumado, cuantos = _suma(totales, dentro)
        if not cuantos or _cuadra(sumado, declarado, cuantos):
            continue
        incidencias.append(
            Incidencia(
                codigo,
                ERROR,
                f"El {nombre} que declara la cabecera no es la suma de las "
                "facturas que trae dentro.",
                campo=f"Cabecera del fichero · {nombre.capitalize()}",
                esperado=(
                    f"{sumado:.2f}  (lo que suman "
                    + ("la única factura" if cuantos == 1 else f"las {cuantos} facturas")
                    + ")"
                ),
                encontrado=_fmt(declarado),
            )
        )

    return incidencias


# --- Entrada pública -------------------------------------------------------


def reglas(raiz, deteccion: Deteccion) -> list[Incidencia]:
    """Las reglas de Facturae sobre un documento ya parseado.

    Devuelve la lista vacía si el documento no es Facturae: quien orquesta
    llama a todos los conjuntos de reglas sin preguntar, y cada uno decide si
    le toca.
    """
    if raiz is None or not deteccion or deteccion.familia != FACTURAE:
        return []

    # El fichero puede llegar envuelto en una firma XAdES, con la factura
    # colgando de dentro. `formato.detectar` ya lo desenvuelve para
    # identificarlo, pero aquí llega el árbol entero, así que hay que volver a
    # buscar el Facturae de verdad o no se encontraría ni un elemento.
    if raiz.xpath("local-name()") != "Facturae":
        internos = raiz.xpath("//*[local-name()='Facturae']")
        if not internos:
            return []
        raiz = internos[0]

    facturas = _hijos(raiz, "Invoices", "Invoice")
    incidencias = _reglas_lote(raiz, facturas)
    for factura in facturas:
        incidencias.extend(_reglas_factura(factura, _etiqueta(factura, len(facturas))))
    return incidencias
