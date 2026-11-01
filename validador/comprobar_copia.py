"""Comparar un Facturae con su copia fiel en UBL, cuando vienen en el mismo lote.

Por qué existe
--------------
`copia_fiel.py` dice qué le pasará a una Facturae al copiarse, y se queda ahí:
no ve la copia. Las reglas de la solución pública ven la copia y no el original.
Ninguna de las dos cosas contesta lo que quiere saber quien ha convertido sus
facturas, que es si la copia **dice lo mismo** que el original. Una copia con
la base equivocada puede cuadrar por dentro y pasar todas las reglas, y solo se
ve poniendo las dos juntas, que es lo que hace un lote.

Por qué aviso y no error
------------------------
Porque la orden no publica la correspondencia entre Facturae y UBL, y lo que hay
de otros es su lectura (el `gobl` de Invopop, por ejemplo, escribe EN 16931 y no la
copia de la orden). Aquí es la tabla de `copia_fiel.py`, leída aquí del esquema de Facturae y del anexo de la orden.
Un aviso dice "estos dos ficheros no dicen lo mismo", que está comprobado; un
error diría que la copia incumple una norma, y ninguna norma escribe esta
comparación. Con código de la casa, por lo mismo (`COPIA-`, en `normas.py`).

Lo que no se compara
--------------------
Lo que la tabla no deja comparar sin inventar:

- el total a pagar (BT-115), que está `POR_DECIDIR` en la tabla;
- los anticipos (BT-113), porque la orden los corta por otro sitio;
- los suplidos, que van en líneas de cobro a las que la orden no da ruta;
- el nombre de una persona física: tres campos en Facturae, uno en la copia, y
  nadie dice cómo se juntan (`COPIA-NOMBRE`);
- la categoría de una entrada al 0 %: al cero caben seis, y el código de
  impuesto de Facturae no distingue ninguna. Se comparan juntas, solo por
  importes (`COPIA-DESGLOSE-CERO`);
- la base de la entrada del recargo de equivalencia, que la orden no explica;
- el código postal y la población de fuera de España: van juntos y la copia los
  pide en dos, y nadie dice por dónde se parten (`COPIA-DIRECCION`);
- el medio de pago, fuera de los cinco códigos que la tabla sostiene por su nombre;
- las notas de la factura: la norma tiene un grupo repetible y Facturae tres campos
  que no se parecen, y lo que va en cada sitio lo decide quien copia;
- una factura rectificada que la copia nombra y el original no: con el criterio 03
  se rectifica un periodo entero, sin número, y de dónde lo saca la copia no se ve.

Y una factura con impuestos que no son IVA, IGIC ni IPSI se compara solo en sus
datos y en sus líneas: esos impuestos van en la copia como cargo, y entonces ni
la base, ni las cuotas, ni el total llegan con el mismo número.

Lo que no es diferencia aunque lo parezca
-----------------------------------------
Salió de medirlo con facturas y código de otro autor, el 01-11-2026, y las de
aquí no lo podían enseñar (en HALLAZGOS):

- BT-112 se espera como la base más las cuotas, y no a partir de `InvoiceTotal`:
  hay Facturae que no restan ahí la retención, aunque su esquema diga que sí;
- el prefijo del NIF, sea del país que sea, porque Facturae lo lleva aparte;
- el signo en un abono: Facturae rectifica en negativo y el 381 va en positivo;
- el separador entre la serie y el número, que nadie fija: es una nota
  (`COPIA-SEPARADOR`) y no un aviso;
- la calle repartida en dos líneas de la copia, si dice lo mismo;
- un cargo de más en la copia: un impuesto que no es IVA va ahí como cargo, y si va
  en la línea, además, su neto lo lleva dentro;
- la fecha de la operación que no se escribe porque es la de expedición;
- la moneda del IVA que no se escribe porque es la de la factura: Facturae obliga a
  escribirla y copiarla rompe la copia (`COPIA-MONEDA-DEL-IVA`);
- una suma que no es la de Facturae y sí la de sus sumandos ya redondeados, que es la
  que pide la norma (BR-CO-10, BR-CO-11 y BR-CO-12).

Lo que falta en la copia porque no tiene sitio no es una diferencia. Y todo
esto no dice que la copia ni el original sean válidos: eso lo dice el informe
de cada fichero.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from decimal import Decimal

from lxml import etree

from validador import cifras, codigo_unico, paises
from validador.copia_fiel import MEDIOS_EN_LA_COPIA
from validador.formato import FACTURAE, UBL
from validador.incidencias import AVISO, NOTA, Incidencia, entre_comillas
from validador.sintaxis import (
    SINTAXIS,
    a_decimal,
    buscar,
    redondear,
    importe,
    importe_en_moneda,
    texto,
    texto_es,
)

__all__ = ["Linea", "Lectura", "extraer_de", "reglas_de_lote"]

# Medio céntimo y no el céntimo de `sintaxis.cuadra`: Facturae admite hasta ocho
# decimales y la copia lleva dos, así que redondear aparta el número hasta
# 0,005 sin que nadie se haya equivocado. Y un céntimo de verdad, entre dos
# importes escritos con dos decimales, tiene que verse: esa es la diferencia que
# este módulo existe para encontrar.
_MARGEN = Decimal("0.005")

# Cuántas diferencias se escriben por aviso. Una copia con el desglose cambiado
# en cuarenta líneas no necesita las cuarenta para que se vaya a mirar.
_NOMBRADAS = 5

# Los tres impuestos de Facturae que tienen categoría en la L4. Cualquier otro
# va en la copia como cargo (ver la fila de `TotalTaxOutputs`).
_IMPUESTOS_FACTURAE = {"01": "IVA", "02": "IPSI", "03": "IGIC"}
_IMPUESTOS_COPIA = {"L": "IGIC", "M": "IPSI", "N": "recargo"}
# Lo que el desglose lleva de verdad. Lo demás que aparezca ahí, como el IRPF, es
# una retención en el original.
_DEL_DESGLOSE = ("IVA", "", *_IMPUESTOS_COPIA.values())

# Hasta dónde se cita un texto del fichero en un aviso.
_LARGO_CITADO = 60

# Los campos de una parte: dónde se leen, cómo se llaman y su término en cada una.
_CAMPOS_DE_UNA_PARTE = (
    ("calle", "calle"),
    ("poblacion", "población"),
    ("postal", "código postal"),
    ("provincia", "provincia"),
    ("pais", "país"),
    ("telefono", "teléfono"),
    ("correo", "correo"),
)
_CAMPOS_DEL_VENDEDOR = tuple(
    (campo, nombre, termino) for (campo, nombre), termino in zip(
        _CAMPOS_DE_UNA_PARTE,
        ("BT-35", "BT-37", "BT-38", "BT-39", "BT-40", "BT-42", "BT-43"), strict=True)
)
_CAMPOS_DEL_COMPRADOR = tuple(
    (campo, nombre, termino) for (campo, nombre), termino in zip(
        _CAMPOS_DE_UNA_PARTE,
        ("BT-50", "BT-52", "BT-53", "BT-54", "BT-55", "BT-57", "BT-58"), strict=True)
)


@dataclass(frozen=True)
class Linea:
    """Lo que se compara de una línea. `tipo` es None si no se puede comparar."""

    cantidad: Decimal | None
    neto: Decimal | None
    tipo: Decimal | None
    nombre: str | None = None
    precio: Decimal | None = None
    # (código del término, motivo). Los descuentos y cargos de la línea.
    motivos: tuple[tuple[str, str], ...] = ()
    descuentos: tuple[Decimal, ...] = ()
    cargos: tuple[Decimal, ...] = ()
    tipos_de_cargo: tuple[Decimal, ...] = ()


@dataclass(frozen=True)
class Parte:
    """La dirección y el contacto de una parte, que en la tabla llegan igual."""

    calle: str | None = None
    poblacion: str | None = None
    postal: str | None = None
    provincia: str | None = None
    pais: str | None = None
    telefono: str | None = None
    correo: str | None = None


@dataclass(frozen=True)
class Lectura:
    """Una factura, leída igual venga de Facturae o de UBL."""

    formato: str
    emisor: str
    numero: str
    numero_solo: str
    fecha: str | None
    moneda: str | None
    emisor_nombre: str | None
    comprador: tuple[str, ...]
    comprador_nombre: str | None
    base: Decimal | None
    cuotas: Decimal | None
    total: Decimal | None
    retenciones: Decimal | None
    # (impuesto, tipo) con su base y su cuota. Los ceros van juntos, con el
    # impuesto vacío; la base del recargo, a None.
    desglose: tuple[tuple[tuple[str, Decimal], Decimal | None, Decimal], ...]
    lineas: tuple[Linea, ...]
    indicador_de_copia: str | None = None
    otros_impuestos: bool = False
    # El `InvoiceTotal` tal cual, solo para reconocerlo si la copia lo trae.
    total_de_facturae: Decimal | None = None
    es_abono: bool = False
    vendedor: Parte = Parte()
    cliente: Parte = Parte()
    vencimientos: tuple[str, ...] = ()
    medios: tuple[str, ...] = ()
    cuentas: tuple[str, ...] = ()
    # (código del término, motivo). Los descuentos y cargos del documento.
    motivos: tuple[tuple[str, str], ...] = ()
    fecha_operacion: str | None = None
    moneda_del_impuesto: str | None = None
    periodo: tuple[str | None, str | None] = (None, None)
    # (número con su serie, fecha). La fecha, si el original la escribe.
    rectificadas: tuple[tuple[str, str | None], ...] = ()
    suma_lineas: Decimal | None = None
    suma_descuentos: Decimal | None = None
    suma_cargos: Decimal | None = None
    descuentos: tuple[Decimal, ...] = ()
    cargos: tuple[Decimal, ...] = ()

    @property
    def es_copia(self) -> bool:
        return (self.indicador_de_copia or "").strip().lower() == "true"


def _hijos(nodo, *nombres: str) -> list:
    actuales = [nodo]
    for nombre in nombres:
        siguientes = []
        for uno in actuales:
            siguientes.extend(uno.xpath(f"./*[local-name()='{nombre}']"))
        actuales = siguientes
    return actuales


def _texto(nodo, *nombres: str) -> str | None:
    for encontrado in _hijos(nodo, *nombres):
        escrito = (encontrado.text or "").strip()
        if escrito:
            return escrito
    return None


def _numero(nodo, *nombres: str) -> Decimal | None:
    return a_decimal(_texto(nodo, *nombres))


def _importes(nodo, *nombres: str) -> tuple[Decimal, ...]:
    leidos = (a_decimal((uno.text or "").strip()) for uno in _hijos(nodo, *nombres))
    return tuple(valor for valor in leidos if valor is not None)


def _sumar(desglose: dict, clave, base: Decimal | None, cuota: Decimal) -> None:
    """Dos entradas iguales son una: la copia puede juntarlas y el original no."""
    suma_base, suma_cuota = desglose.get(clave, (None, Decimal(0)))
    if base is not None:
        suma_base = (suma_base or Decimal(0)) + base
    desglose[clave] = (suma_base, suma_cuota + cuota)


def _congelado(desglose: dict) -> tuple:
    return tuple((clave, base, cuota) for clave, (base, cuota) in desglose.items())


def _desglose_facturae(factura) -> tuple[tuple, bool]:
    desglose: dict = {}
    otros = False
    for impuesto in _hijos(factura, "TaxesOutputs", "Tax"):
        familia = _IMPUESTOS_FACTURAE.get(_texto(impuesto, "TaxTypeCode") or "")
        if familia is None:
            otros = True
            continue
        tipo = _numero(impuesto, "TaxRate") or Decimal(0)
        base = _numero(impuesto, "TaxableBase", "TotalAmount") or Decimal(0)
        cuota = _numero(impuesto, "TaxAmount", "TotalAmount") or Decimal(0)
        _sumar(desglose, (familia if tipo else "", tipo), base, cuota)
        recargo = _numero(impuesto, "EquivalenceSurchargeAmount", "TotalAmount")
        if recargo is not None:
            tipo_recargo = _numero(impuesto, "EquivalenceSurcharge") or Decimal(0)
            _sumar(desglose, ("recargo", tipo_recargo), None, recargo)
    return _congelado(desglose), otros


def _lineas_facturae(factura) -> tuple[Linea, ...]:
    lineas = []
    for linea in _hijos(factura, "Items", "InvoiceLine"):
        impuestos = _hijos(linea, "TaxesOutputs", "Tax")
        # Con dos impuestos o con recargo, la línea de la copia, que tiene un
        # solo tipo, no dice cuál lleva: no hay nada que comparar.
        tipo = None
        if len(impuestos) == 1 and not _hijos(impuestos[0], "EquivalenceSurcharge"):
            tipo = _numero(impuestos[0], "TaxRate")
        lineas.append(Linea(
            _numero(linea, "Quantity"), _numero(linea, "GrossAmount"), tipo,
            nombre=_texto(linea, "ItemDescription"),
            precio=_numero(linea, "UnitPriceWithoutTax"),
            motivos=_motivos_facturae(linea, "DiscountsAndRebates", "Charges", "BT-139", "BT-144"),
            descuentos=_importes(linea, "DiscountsAndRebates", "Discount", "DiscountAmount"),
            cargos=_importes(linea, "Charges", "Charge", "ChargeAmount"),
            tipos_de_cargo=_importes(linea, "Charges", "Charge", "ChargeRate"),
        ))
    return tuple(lineas)


def _motivos_facturae(nodo, descuentos: str, cargos: str,
                      de_descuento: str, de_cargo: str) -> tuple[tuple[str, str], ...]:
    motivos = []
    for grupo, elemento, motivo, termino in (
        (descuentos, "Discount", "DiscountReason", de_descuento),
        (cargos, "Charge", "ChargeReason", de_cargo),
    ):
        for uno in _hijos(nodo, grupo, elemento):
            escrito = _texto(uno, motivo)
            if escrito:
                motivos.append((termino, escrito))
    return tuple(motivos)


def _parte_facturae(parte) -> Parte:
    """Sea empresa o persona, de aquí o de fuera.

    De fuera, sin el código postal ni la población: van juntos en un campo y la
    copia los pide en dos, y nadie dice por dónde se parte (`COPIA-DIRECCION`).
    Solo la dirección de la parte: la de un centro administrativo no es la suya.
    """
    for entidad in (*_hijos(parte, "LegalEntity"), *_hijos(parte, "Individual")):
        direccion = (_hijos(entidad, "AddressInSpain") or _hijos(entidad, "OverseasAddress")
                     or [entidad])[0]
        return Parte(
            calle=_texto(direccion, "Address"),
            poblacion=_texto(direccion, "Town"),
            postal=_texto(direccion, "PostCode"),
            provincia=_texto(direccion, "Province"),
            # ESP en Facturae y ES en la copia. `alpha2` no afirma nada de los
            # códigos que ISO ya retiró, y entonces esto no se compara.
            pais=paises.alpha2(_texto(direccion, "CountryCode")),
            telefono=_texto(entidad, "ContactDetails", "Telephone"),
            correo=_texto(entidad, "ContactDetails", "ElectronicMail"),
        )
    return Parte()


def _pago_facturae(factura) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    vencimientos, medios, cuentas = [], [], []
    for plazo in _hijos(factura, "PaymentDetails", "Installment"):
        for lista, escrito in (
            (vencimientos, _texto(plazo, "InstallmentDueDate")),
            (medios, _texto(plazo, "PaymentMeans")),
            (cuentas, _texto(plazo, "AccountToBeCredited", "IBAN")
             or _texto(plazo, "AccountToBeCredited", "AccountNumber")),
        ):
            if escrito and escrito not in lista:
                lista.append(escrito)
    return tuple(vencimientos), tuple(medios), tuple(cuentas)


def _rectificadas_facturae(factura) -> tuple[tuple[str, str | None], ...]:
    """Con su número. Con el criterio 03 se rectifica un periodo, y no hay ninguno.

    `RelatedInvoice` ya viene con la serie y el número juntos, y sin fecha.
    """
    rectificadas = []
    for bloque in _hijos(factura, "InvoiceHeader", "Corrective"):
        numero = _texto(bloque, "InvoiceNumber")
        if numero:
            serie = _texto(bloque, "InvoiceSeriesCode") or ""
            rectificadas.append((f"{serie}{numero}", _texto(bloque, "InvoiceIssueDate")))
    asociada = _texto(factura, "AdditionalData", "RelatedInvoice")
    if asociada:
        rectificadas.append((asociada, None))
    return tuple(rectificadas)


def _facturae(raiz) -> list[Lectura]:
    vendedor = _hijos(raiz, "Parties", "SellerParty")
    comprador = _hijos(raiz, "Parties", "BuyerParty")
    emisor = codigo_unico.limpiar_nif(
        _texto(vendedor[0], "TaxIdentification", "TaxIdentificationNumber")
        if vendedor else None)
    if not emisor:
        return []
    id_comprador = (_texto(comprador[0], "TaxIdentification", "TaxIdentificationNumber")
                    if comprador else None)
    lecturas = []
    for factura in _hijos(raiz, "Invoices", "Invoice"):
        numero = _texto(factura, "InvoiceHeader", "InvoiceNumber") or ""
        serie = _texto(factura, "InvoiceHeader", "InvoiceSeriesCode") or ""
        if not numero:
            continue
        totales = _hijos(factura, "InvoiceTotals")
        de_totales = totales[0] if totales else factura
        cuotas = _numero(de_totales, "TotalTaxOutputs")
        base = _numero(de_totales, "TotalGrossAmountBeforeTaxes")
        total = _numero(de_totales, "InvoiceTotal")
        retenciones = _numero(de_totales, "TotalTaxesWithheld")
        desglose, otros = _desglose_facturae(factura)
        vencimientos, medios, cuentas = _pago_facturae(factura)
        lecturas.append(Lectura(
            formato=FACTURAE,
            emisor=emisor,
            numero=f"{serie}{numero}",
            numero_solo=numero,
            fecha=_texto(factura, "InvoiceIssueData", "IssueDate"),
            moneda=_texto(factura, "InvoiceIssueData", "InvoiceCurrencyCode"),
            emisor_nombre=(_texto(vendedor[0], "LegalEntity", "CorporateName")
                           if vendedor else None),
            comprador=(codigo_unico.limpiar_nif(id_comprador),) if id_comprador else (),
            comprador_nombre=(_texto(comprador[0], "LegalEntity", "CorporateName")
                              if comprador else None),
            base=base,
            cuotas=cuotas,
            # BT-112 es base más cuotas (BR-CO-15). No se saca de `InvoiceTotal`
            # sumándole la retención que resta: medido el 01-11-2026, las
            # Facturae públicas de Invopop no la restan, y una copia correcta
            # salía acusada. Que el original no cuadre es cosa de FE-TOTAL.
            total=None if base is None or cuotas is None else base + cuotas,
            total_de_facturae=total,
            retenciones=retenciones,
            desglose=desglose,
            lineas=_lineas_facturae(factura),
            otros_impuestos=otros,
            vendedor=_parte_facturae(vendedor[0]) if vendedor else Parte(),
            cliente=_parte_facturae(comprador[0]) if comprador else Parte(),
            vencimientos=vencimientos,
            medios=medios,
            cuentas=cuentas,
            motivos=_motivos_facturae(factura, "GeneralDiscounts", "GeneralSurcharges",
                                      "BT-97", "BT-104"),
            fecha_operacion=_texto(factura, "InvoiceIssueData", "OperationDate"),
            moneda_del_impuesto=_texto(factura, "InvoiceIssueData", "TaxCurrencyCode"),
            periodo=(_texto(factura, "InvoiceIssueData", "InvoicingPeriod", "StartDate"),
                     _texto(factura, "InvoiceIssueData", "InvoicingPeriod", "EndDate")),
            rectificadas=_rectificadas_facturae(factura),
            suma_lineas=_numero(de_totales, "TotalGrossAmount"),
            suma_descuentos=_numero(de_totales, "TotalGeneralDiscounts"),
            suma_cargos=_numero(de_totales, "TotalGeneralSurcharges"),
            descuentos=_importes(factura, "GeneralDiscounts", "Discount", "DiscountAmount"),
            cargos=_importes(factura, "GeneralSurcharges", "Charge", "ChargeAmount"),
        ))
    return lecturas


def _desglose_ubl(raiz, sintaxis) -> tuple:
    desglose: dict = {}
    for grupo in buscar(raiz, sintaxis.desglose, sintaxis.espacios):
        categoria = (texto(grupo, sintaxis.desglose_categoria, sintaxis) or "").upper()
        tipo = importe(grupo, sintaxis.desglose_tipo, sintaxis) or Decimal(0)
        base = importe(grupo, sintaxis.desglose_base, sintaxis) or Decimal(0)
        cuota = importe(grupo, sintaxis.desglose_cuota, sintaxis) or Decimal(0)
        esquema = (grupo.xpath("string(./cac:TaxCategory/cac:TaxScheme/cbc:ID)",
                               namespaces=sintaxis.espacios) or "").strip().upper()
        # Por la categoría, y si no por el esquema: sin esto, una retención
        # metida en el desglose se anunciaba como IVA.
        familia = _IMPUESTOS_COPIA.get(categoria) or (
            esquema if esquema not in ("", "VAT", "IVA") else "IVA")
        if familia == "recargo":
            _sumar(desglose, (familia, tipo), None, cuota)
        else:
            _sumar(desglose, (familia if tipo else "", tipo), base, cuota)
    return _congelado(desglose)


def _parte_ubl(raiz, cual: str) -> Parte:
    partes = _hijos(raiz, cual, "Party")
    if not partes:
        return Parte()
    direccion = (_hijos(partes[0], "PostalAddress") or [partes[0]])[0]
    # La calle de Facturae es una sola línea, y un conversor puede repartirla.
    # Medido el 01-11-2026 con `gobl`: "Calle Pradillo, 42, 3" se escribe en
    # StreetName y AdditionalStreetName, sin perder nada, y salía como otra calle.
    trozos = (_texto(direccion, "StreetName"), _texto(direccion, "AdditionalStreetName"),
              _texto(direccion, "AddressLine", "Line"))
    return Parte(
        calle=" ".join(t for t in trozos if t) or None,
        poblacion=_texto(direccion, "CityName"),
        postal=_texto(direccion, "PostalZone"),
        provincia=_texto(direccion, "CountrySubentity"),
        pais=(_texto(direccion, "Country", "IdentificationCode") or "").upper() or None,
        telefono=_texto(partes[0], "Contact", "Telephone"),
        correo=_texto(partes[0], "Contact", "ElectronicMail"),
    )


def _motivos_ubl(nodo, de_descuento: str, de_cargo: str) -> tuple[tuple[str, str], ...]:
    motivos = []
    for uno in _hijos(nodo, "AllowanceCharge"):
        escrito = _texto(uno, "AllowanceChargeReason")
        if escrito:
            es_cargo = (_texto(uno, "ChargeIndicator") or "").lower() == "true"
            motivos.append((de_cargo if es_cargo else de_descuento, escrito))
    return tuple(motivos)


def _pago_ubl(raiz) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    medios = _hijos(raiz, "PaymentMeans")
    # En una nota de abono BT-9 no va en la cabecera: va dentro del medio de pago.
    vencimientos = [_texto(raiz, "DueDate"), *(_texto(m, "PaymentDueDate") for m in medios)]
    return (
        tuple(dict.fromkeys(f for f in vencimientos if f)),
        tuple(dict.fromkeys(c for c in (_texto(m, "PaymentMeansCode") for m in medios) if c)),
        tuple(dict.fromkeys(c for c in (_texto(m, "PayeeFinancialAccount", "ID")
                                        for m in medios) if c)),
    )


def _de_los_cargos_ubl(nodo) -> tuple[list[Decimal], list[Decimal], list[Decimal]]:
    descuentos, cargos, tipos = [], [], []
    for uno in _hijos(nodo, "AllowanceCharge"):
        es_cargo = (_texto(uno, "ChargeIndicator") or "").lower() == "true"
        (cargos if es_cargo else descuentos).extend(_importes(uno, "Amount"))
        if es_cargo:
            tipos.extend(_importes(uno, "MultiplierFactorNumeric"))
    return descuentos, cargos, tipos


def _linea_ubl(linea, sintaxis) -> Linea:
    precio = importe(linea, sintaxis.linea_precio, sintaxis)
    # BT-149: el precio puede ser el de varias unidades, y el de Facturae es de una.
    por_cuantas = _numero(linea, "Price", "BaseQuantity")
    if precio is not None and por_cuantas:
        precio = precio / por_cuantas
    descuentos, cargos, tipos = _de_los_cargos_ubl(linea)
    return Linea(
        importe(linea, sintaxis.linea_cantidad, sintaxis),
        importe(linea, "./cbc:LineExtensionAmount", sintaxis),
        importe(linea, sintaxis.linea_tipo, sintaxis) or Decimal(0),
        nombre=texto(linea, sintaxis.linea_nombre, sintaxis),
        precio=precio,
        motivos=_motivos_ubl(linea, "BT-139", "BT-144"),
        descuentos=tuple(descuentos),
        cargos=tuple(cargos),
        tipos_de_cargo=tuple(tipos),
    )


def _ubl(raiz, deteccion) -> list[Lectura]:
    sintaxis = SINTAXIS[UBL]
    # El emisor, por el mismo camino que el código único: una factura no puede
    # ser de uno para el código y de otro para esta comparación.
    codigos = codigo_unico.extraer_de(raiz, deteccion)
    if not codigos or not codigos[0].nif_emisor:
        return []
    numero = codigos[0].numero_completo
    moneda = texto(raiz, sintaxis.moneda, sintaxis)
    espacios = sintaxis.espacios
    comprador = [
        codigo_unico.limpiar_nif(texto(raiz, ruta, sintaxis))
        for ruta in (sintaxis.comprador_nif, sintaxis.comprador_registro,
                     "./cac:AccountingCustomerParty/cac:Party"
                     "/cac:PartyIdentification/cbc:ID")
        if texto(raiz, ruta, sintaxis)
    ]
    total = "./cac:LegalMonetaryTotal/"
    vencimientos, medios, cuentas = _pago_ubl(raiz)
    return [Lectura(
        formato=UBL,
        emisor=codigos[0].nif_emisor,
        numero=numero,
        numero_solo=numero,
        fecha=texto(raiz, sintaxis.fecha, sintaxis),
        moneda=moneda,
        emisor_nombre=texto(raiz, sintaxis.vendedor_nombre, sintaxis),
        comprador=tuple(comprador),
        comprador_nombre=texto(raiz, sintaxis.comprador_nombre, sintaxis),
        base=importe(raiz, f"{total}cbc:TaxExclusiveAmount", sintaxis),
        cuotas=importe_en_moneda(raiz, sintaxis.impuestos, sintaxis, moneda),
        total=importe(raiz, f"{total}cbc:TaxInclusiveAmount", sintaxis),
        retenciones=a_decimal(texto_es(raiz, "BT-ES-17")),
        desglose=_desglose_ubl(raiz, sintaxis),
        lineas=tuple(_linea_ubl(linea, sintaxis)
                     for linea in buscar(raiz, sintaxis.lineas, espacios)),
        indicador_de_copia=texto_es(raiz, "BT-ES-1"),
        es_abono=(texto(raiz, sintaxis.tipo, sintaxis) == "381"
                  or etree.QName(raiz).localname == "CreditNote"),
        vendedor=_parte_ubl(raiz, "AccountingSupplierParty"),
        cliente=_parte_ubl(raiz, "AccountingCustomerParty"),
        vencimientos=vencimientos,
        medios=medios,
        cuentas=cuentas,
        motivos=_motivos_ubl(raiz, "BT-97", "BT-104"),
        fecha_operacion=texto(raiz, sintaxis.fecha_devengo, sintaxis),
        moneda_del_impuesto=texto(raiz, sintaxis.moneda_impuestos, sintaxis),
        periodo=(_texto(raiz, "InvoicePeriod", "StartDate"),
                 _texto(raiz, "InvoicePeriod", "EndDate")),
        rectificadas=tuple(
            (_texto(uno, "ID") or "", _texto(uno, "IssueDate"))
            for uno in _hijos(raiz, "BillingReference", "InvoiceDocumentReference")
        ),
        suma_lineas=importe(raiz, sintaxis.suma_lineas, sintaxis),
        suma_descuentos=importe(raiz, sintaxis.descuentos_total, sintaxis),
        suma_cargos=importe(raiz, sintaxis.cargos_total, sintaxis),
    )]


def extraer_de(raiz, deteccion) -> list[Lectura]:
    """Las facturas del documento, si es de los dos formatos que se comparan.

    La copia fiel es UBL porque es lo que pide la orden; un CII o un EDIFACT no
    son la copia de nada aquí.
    """
    if raiz is None or not deteccion:
        return []
    if deteccion.familia == FACTURAE:
        return _facturae(raiz)
    if deteccion.familia == UBL:
        return _ubl(raiz, deteccion)
    return []


def _compacto(escrito: str | None) -> str:
    """Sin espacios, puntos ni mayúsculas: "Ejemplo, S.L." y "EJEMPLO SL" son el mismo."""
    return re.sub(r"[\W_]+", "", escrito or "").casefold()


def _plural(cuantas: int, una: str, varias: str) -> str:
    return f"{cuantas} {una if cuantas == 1 else varias}"


def _cifra(valor: Decimal | None) -> str:
    """Una cifra del fichero dentro de una frase, o que no la lleva."""
    return "nada" if valor is None else cifras.en_castellano(valor)


def _sin_pais(nif: str) -> str:
    """Sin el prefijo de cualquier país. `limpiar_nif` solo quita el ES.

    Medido el 01-11-2026: un vendedor francés, 123456789012 en el Facturae y
    FR123456789012 en la copia, se quedaba sin pareja y sin comparar. Dos letras
    y no una: la letra de un NIF español no es ningún país.
    """
    return re.sub(r"^[A-Z]{2}", "", nif.upper())


def _en_positivo(lectura: Lectura) -> Lectura:
    """Un abono sin signos. Facturae rectifica en negativo, y el 381 va en positivo."""
    def sin_signo(valor):
        return None if valor is None else abs(valor)

    def sin_signos(valores):
        return tuple(abs(valor) for valor in valores)
    return replace(
        lectura,
        base=sin_signo(lectura.base),
        cuotas=sin_signo(lectura.cuotas),
        total=sin_signo(lectura.total),
        total_de_facturae=sin_signo(lectura.total_de_facturae),
        retenciones=sin_signo(lectura.retenciones),
        desglose=tuple((clave, sin_signo(base), sin_signo(cuota))
                       for clave, base, cuota in lectura.desglose),
        lineas=tuple(replace(l, cantidad=sin_signo(l.cantidad), neto=sin_signo(l.neto),
                             precio=sin_signo(l.precio), descuentos=sin_signos(l.descuentos),
                             cargos=sin_signos(l.cargos))
                     for l in lectura.lineas),
        suma_lineas=sin_signo(lectura.suma_lineas),
        suma_descuentos=sin_signo(lectura.suma_descuentos),
        suma_cargos=sin_signo(lectura.suma_cargos),
        descuentos=sin_signos(lectura.descuentos),
        cargos=sin_signos(lectura.cargos),
    )


def _igual(a: Decimal | None, b: Decimal | None) -> bool:
    return a is not None and b is not None and abs(a - b) <= _MARGEN


def _suma_cuadra(total: Decimal, sumandos, de_copia: Decimal) -> bool:
    """Vale la suma tal cual y la de los sumandos ya redondeados, que es la de la norma.

    Con tres líneas de 0,334 Facturae suma 1,002 y la copia, 0,99: las dos bien.
    Sin sumandos no hay otra suma: un cero no puede dar por bueno un total que falta.
    """
    if _igual(total, de_copia):
        return True
    return bool(sumandos) and _igual(sum((redondear(s) for s in sumandos), Decimal(0)), de_copia)


def _pareja_de(copia: Lectura, originales: list[int], lecturas: list[Lectura]) -> int | None:
    """El original de una copia: primero exacto, luego sin separadores, y por
    último por el número sin la serie, solo si no hay dos que encajen."""
    del_emisor = [i for i in originales
                  if _sin_pais(lecturas[i].emisor) == _sin_pais(copia.emisor)]
    for i in del_emisor:
        if lecturas[i].numero == copia.numero:
            return i
    for i in del_emisor:
        if _compacto(lecturas[i].numero) == _compacto(copia.numero):
            return i
    solo_numero = [i for i in del_emisor
                   if _compacto(lecturas[i].numero_solo) == _compacto(copia.numero)]
    return solo_numero[0] if len(solo_numero) == 1 else None


def _de_las_rectificadas(original: Lectura, copia: Lectura) -> list[str]:
    """Las del original tienen que estar. Con otro separador sigue siendo la misma."""
    de_copia = {_compacto(numero): fecha for numero, fecha in copia.rectificadas}
    diferencias = []
    for numero, fecha in original.rectificadas:
        clave = _compacto(numero)
        if clave not in de_copia:
            escritas = ", ".join(n for n, _ in copia.rectificadas) or "nada"
            diferencias.append(f"factura rectificada (BT-25): {numero} en el original y "
                               f"{escritas} en la copia")
        elif fecha and fecha != de_copia[clave]:
            diferencias.append(f"fecha de la factura rectificada (BT-26): {fecha} en el "
                               f"original y {de_copia[clave] or 'nada'} en la copia")
    return diferencias


def _de_datos(original: Lectura, copia: Lectura) -> list[str]:
    diferencias = []
    # Con otro separador no es una diferencia: lo dice COPIA-SEPARADOR.
    if _compacto(original.numero) != _compacto(copia.numero):
        diferencias.append(
            f"número (BT-1): {copia.numero} en la copia, sin la serie, y "
            f"{original.numero} en el original. Así la copia y el original no "
            "identifican la misma factura")
    if original.fecha != copia.fecha:
        diferencias.append(f"fecha de expedición (BT-2): {original.fecha} en el "
                           f"original y {copia.fecha} en la copia")
    if original.moneda != copia.moneda:
        diferencias.append(f"moneda (BT-5): {original.moneda} en el original y "
                           f"{copia.moneda} en la copia")
    # Sin fecha aparte es la de expedición: en Facturae solo se escribe si es otra.
    if (original.fecha_operacion or copia.fecha_operacion) and (
        (original.fecha_operacion or original.fecha) != (copia.fecha_operacion or copia.fecha)
    ):
        diferencias.append(f"fecha de la operación (BT-7): "
                           f"{original.fecha_operacion or original.fecha} en el original y "
                           f"{copia.fecha_operacion or copia.fecha} en la copia")
    # Sin moneda aparte es la de la factura, y la copia no debe escribirla si es esa
    # (`COPIA-MONEDA-DEL-IVA`). Solo se mira si alguien dice otra cosa: si no, una
    # moneda cambiada en BT-5 salía dos veces.
    del_impuesto = original.moneda_del_impuesto or original.moneda
    if (copia.moneda_del_impuesto or del_impuesto != original.moneda) and (
        del_impuesto != (copia.moneda_del_impuesto or copia.moneda)
    ):
        diferencias.append(f"moneda del IVA (BT-6): {del_impuesto} en el original y "
                           f"{copia.moneda_del_impuesto or copia.moneda} en la copia")
    for nombre, suyo, de_copia in (
        ("inicio del periodo de facturación (BT-73)", original.periodo[0], copia.periodo[0]),
        ("fin del periodo de facturación (BT-74)", original.periodo[1], copia.periodo[1]),
    ):
        if suyo != de_copia:
            diferencias.append(f"{nombre}: {suyo or 'nada'} en el original y "
                               f"{de_copia or 'nada'} en la copia")
    diferencias += _de_las_rectificadas(original, copia)
    if original.comprador and _sin_pais(original.comprador[0]) not in {
        _sin_pais(nif) for nif in copia.comprador
    }:
        escrito = ", ".join(copia.comprador) or "ninguno"
        diferencias.append(f"NIF del comprador (BT-48 o BT-47): {original.comprador[0]} "
                           f"en el original y {escrito} en la copia")
    for quien, campo, de_original, de_copia in (
        ("emisor", "BT-27", original.emisor_nombre, copia.emisor_nombre),
        ("comprador", "BT-44", original.comprador_nombre, copia.comprador_nombre),
    ):
        # Sin razón social en el original es una persona física, que no se compara.
        if de_original and _compacto(de_original) != _compacto(de_copia):
            diferencias.append(f"nombre del {quien} ({campo}): \"{de_original}\" en "
                               f"el original y {entre_comillas(de_copia, 'nada')} en la copia")
    if not copia.es_copia:
        diferencias.append("indicador de copia (BT-ES-1): la copia no dice true, y "
                           "sin eso la orden la toma por el original")
    return diferencias


def _total_cuadra(original: Lectura, copia: Lectura) -> bool:
    """Vale la suma exacta y la de los dos ya redondeados, que es la de BR-CO-15."""
    if _igual(original.total, copia.total):
        return True
    return (original.base is not None and original.cuotas is not None
            and _igual(redondear(original.base) + redondear(original.cuotas), copia.total))


def _de_importes(original: Lectura, copia: Lectura) -> list[str]:
    diferencias = []
    if not original.otros_impuestos:
        for nombre, de_original, de_copia in (
            ("base (BT-109)", original.base, copia.base),
            ("cuotas (BT-110)", original.cuotas, copia.cuotas),
        ):
            if de_original is not None and not _igual(de_original, de_copia):
                diferencias.append(f"{nombre}: {_cifra(de_original)} según el original "
                                   f"y {_cifra(de_copia)} en la copia")
        if original.total is not None and not _total_cuadra(original, copia):
            frase = (f"total con impuestos (BT-112): {_cifra(original.total)} según el "
                     f"original y {_cifra(copia.total)} en la copia")
            if original.retenciones and _igual(original.total_de_facturae, copia.total):
                frase += (". Es el total de Facturae tal cual, que resta las retenciones, "
                          "y BT-112 no las resta")
            diferencias.append(frase)
        netos = [l.neto for l in original.lineas if l.neto is not None]
        if original.suma_lineas is not None and not _suma_cuadra(
            original.suma_lineas, netos, copia.suma_lineas or Decimal(0)
        ):
            diferencias.append(f"suma de las líneas (BT-106): {_cifra(original.suma_lineas)} "
                               f"según el original y {_cifra(copia.suma_lineas)} en la copia")
        for nombre, suya, sumandos, de_copia in (
            ("descuentos generales (BT-107)", original.suma_descuentos, original.descuentos,
             copia.suma_descuentos),
            ("cargos generales (BT-108)", original.suma_cargos, original.cargos,
             copia.suma_cargos),
        ):
            # La suma es opcional en Facturae, y los descuentos pueden venir sin ella.
            total = sum(sumandos, Decimal(0)) if suya is None else suya
            if not _suma_cuadra(total, sumandos, de_copia or Decimal(0)):
                diferencias.append(f"{nombre}: {_cifra(total)} según el original y "
                                   f"{_cifra(de_copia)} en la copia")
    retenido = original.retenciones or Decimal(0)
    if not _igual(retenido, copia.retenciones or Decimal(0)):
        diferencias.append(f"retenciones (BT-ES-17): {_cifra(retenido)} en el original y "
                           f"{_cifra(copia.retenciones)} en la copia")
    return diferencias


def _nombre_de_entrada(clave: tuple[str, Decimal]) -> str:
    familia, tipo = clave
    return f"{familia} al {cifras.tipo(tipo)}" if familia else "al 0 %"


def _de_desglose(original: Lectura, copia: Lectura) -> list[str]:
    """BG-23 por impuesto y tipo: la base (BT-116), la cuota (BT-117) y el tipo (BT-119)."""
    if original.otros_impuestos:
        return []
    de_copia = {clave: (base, cuota) for clave, base, cuota in copia.desglose}
    diferencias = []
    for clave, base, cuota in original.desglose:
        if clave not in de_copia:
            # Un grupo sin nada no es una diferencia: es no escribir un cero.
            if base or cuota:
                diferencias.append(f"{_nombre_de_entrada(clave)}: la copia no lo lleva")
            continue
        base_copia, cuota_copia = de_copia[clave]
        if base is not None and not _igual(base, base_copia):
            diferencias.append(f"{_nombre_de_entrada(clave)}: base {_cifra(base)} en el "
                               f"original y {_cifra(base_copia)} en la copia")
        if not _igual(cuota, cuota_copia):
            diferencias.append(f"{_nombre_de_entrada(clave)}: cuota {_cifra(cuota)} en el "
                               f"original y {_cifra(cuota_copia)} en la copia")
    claves_original = {clave for clave, _, _ in original.desglose}
    for clave, base, cuota in copia.desglose:
        if clave in claves_original or not (base or cuota):
            continue
        if original.retenciones and clave[0] not in _DEL_DESGLOSE:
            # Medido con la salida de `gobl`, que escribe el IRPF en el desglose: decir
            # que el original no lo tiene era falso.
            diferencias.append(f"{_nombre_de_entrada(clave)}: en la copia va en el desglose "
                               "de impuestos, y en el original es una retención, que en la "
                               "copia va aparte (BT-ES-17)")
        else:
            diferencias.append(f"{_nombre_de_entrada(clave)}: está en la copia y no en "
                               "el original")
    return diferencias


def _de_lineas(original: Lectura, copia: Lectura) -> list[str]:
    if len(original.lineas) != len(copia.lineas):
        return [f"{_plural(len(original.lineas), 'línea', 'líneas')} en el original y "
                f"{len(copia.lineas)} en la copia"]
    diferencias = []
    # Por posición: es el orden del fichero, y Facturae no obliga a numerarlas.
    for numero, (suya, de_copia) in enumerate(
        zip(original.lineas, copia.lineas, strict=True), start=1
    ):
        if suya.cantidad != de_copia.cantidad:
            diferencias.append(f"línea {numero}, cantidad (BT-129): {_cifra(suya.cantidad)} en "
                               f"el original y {_cifra(de_copia.cantidad)} en la copia")
        cargos_suyos = sum(suya.cargos, Decimal(0))
        cargos_de_copia = sum(de_copia.cargos, Decimal(0))
        neto = suya.neto
        # Un impuesto que no es IVA, escrito como cargo de la línea, suma en BT-131:
        # la propia fila de la tabla lo dice, y una copia correcta salía acusada.
        if neto is not None and original.otros_impuestos and cargos_de_copia > cargos_suyos:
            neto += cargos_de_copia - cargos_suyos
        if neto is not None and not _igual(neto, de_copia.neto):
            diferencias.append(f"línea {numero}, neto (BT-131): {_cifra(neto)} en el "
                               f"original y {_cifra(de_copia.neto)} en la copia")
        descuentos_de_copia = sum(de_copia.descuentos, Decimal(0))
        descuentos_suyos = sum(suya.descuentos, Decimal(0))
        if not _suma_cuadra(descuentos_suyos, suya.descuentos, descuentos_de_copia):
            diferencias.append(f"línea {numero}, descuentos (BT-136): "
                               f"{_cifra(descuentos_suyos)} en el original y "
                               f"{_cifra(descuentos_de_copia)} en la copia")
        if not original.otros_impuestos:
            if not _suma_cuadra(cargos_suyos, suya.cargos, cargos_de_copia):
                diferencias.append(f"línea {numero}, cargos (BT-141): {_cifra(cargos_suyos)} "
                                   f"en el original y {_cifra(cargos_de_copia)} en la copia")
            for tipo in suya.tipos_de_cargo:
                if tipo and not any(_igual(tipo, t) for t in de_copia.tipos_de_cargo):
                    diferencias.append(f"línea {numero}, porcentaje del cargo (BT-143): "
                                       f"{cifras.tipo(tipo)} en el original, y no en la copia")
        if suya.precio is not None and not _igual(suya.precio, de_copia.precio):
            diferencias.append(f"línea {numero}, precio (BT-146): {_cifra(suya.precio)} en el "
                               f"original y {_cifra(de_copia.precio)} en la copia")
        if (not original.otros_impuestos and suya.tipo is not None
                and suya.tipo != de_copia.tipo):
            diferencias.append(f"línea {numero}, tipo (BT-152): {cifras.tipo(suya.tipo)} "
                               f"en el original y {cifras.tipo(de_copia.tipo)} en la copia")
    return diferencias


def _corto(escrito: str | None) -> str:
    """Un texto dentro de una frase. El nombre de un artículo puede ser un párrafo."""
    if escrito and len(escrito) > _LARGO_CITADO:
        escrito = escrito[:_LARGO_CITADO].rstrip() + "..."
    return entre_comillas(escrito, "nada")


def _de_las_partes(original: Lectura, copia: Lectura) -> list[str]:
    diferencias = []
    for quien, suya, de_copia, campos in (
        ("vendedor", original.vendedor, copia.vendedor, _CAMPOS_DEL_VENDEDOR),
        ("comprador", original.cliente, copia.cliente, _CAMPOS_DEL_COMPRADOR),
    ):
        for campo, nombre, termino in campos:
            de_original, escrito = getattr(suya, campo), getattr(de_copia, campo)
            if de_original and _compacto(de_original) != _compacto(escrito):
                diferencias.append(f"{nombre} del {quien} ({termino}): {_corto(de_original)} "
                                   f"en el original y {_corto(escrito)} en la copia")
    return diferencias


def _medio_cambiado(original: Lectura, copia: Lectura) -> str | None:
    """El medio de pago, solo con los códigos que la tabla sostiene por su nombre.

    Con los demás no se afirma nada: en `copia_fiel.py` la equivalencia se elige
    a mano. Y el dígito copiado tal cual se dice aparte, porque es el fallo que
    la tabla llama el más peligroso: da un código válido que significa otra cosa.
    """
    conocidos = [m for m in original.medios if m in MEDIOS_EN_LA_COPIA]
    if not conocidos or any(c in MEDIOS_EN_LA_COPIA[m] for m in conocidos for c in copia.medios):
        return None
    esperados = " o ".join(dict.fromkeys(c for m in conocidos for c in MEDIOS_EN_LA_COPIA[m]))
    frase = (f"medio de pago (BT-81): {' y '.join(conocidos)} en el original, que en la copia "
             f"es {esperados}, y {' y '.join(copia.medios) or 'nada'} en la copia")
    if any(c.lstrip("0") == m.lstrip("0") for m in conocidos for c in copia.medios):
        frase += (". Es el código de Facturae copiado tal cual, y en la lista europea "
                  "significa otra cosa")
    return frase


def _de_pago(original: Lectura, copia: Lectura) -> list[str]:
    """Con varios vencimientos la copia solo lleva uno, y vale cualquiera de ellos."""
    diferencias = []
    if original.vencimientos and not set(original.vencimientos) & set(copia.vencimientos):
        diferencias.append(f"vencimiento (BT-9): {', '.join(original.vencimientos)} en el "
                           f"original y {', '.join(copia.vencimientos) or 'nada'} en la copia")
    medio = _medio_cambiado(original, copia)
    if medio:
        diferencias.append(medio)
    if original.cuentas and not ({_compacto(c) for c in original.cuentas}
                                 & {_compacto(c) for c in copia.cuentas}):
        diferencias.append(f"cuenta de abono (BT-84): {', '.join(original.cuentas)} en el "
                           f"original y {', '.join(copia.cuentas) or 'nada'} en la copia")
    return diferencias


def _motivos_que_faltan(suyos, de_copia, donde: str) -> list[str]:
    """Los del original tienen que estar. Al revés no: un impuesto que no es IVA va
    en la copia como cargo, con su motivo, y en el original no es un cargo."""
    escritos = {(termino, _compacto(motivo)) for termino, motivo in de_copia}
    return [f"{donde}motivo ({termino}): {_corto(motivo)} en el original, y no en la copia"
            for termino, motivo in suyos if (termino, _compacto(motivo)) not in escritos]


def _de_textos(original: Lectura, copia: Lectura) -> list[str]:
    diferencias = _motivos_que_faltan(original.motivos, copia.motivos, "")
    # Con otro número de líneas ya lo dice COPIA-LINEAS, y por posición no se
    # sabe cuál es cuál.
    if len(original.lineas) == len(copia.lineas):
        for numero, (suya, de_copia) in enumerate(zip(original.lineas, copia.lineas), start=1):
            if suya.nombre and _compacto(suya.nombre) != _compacto(de_copia.nombre):
                diferencias.append(f"línea {numero}, nombre (BT-153): {_corto(suya.nombre)} en "
                                   f"el original y {_corto(de_copia.nombre)} en la copia")
            diferencias += _motivos_que_faltan(suya.motivos, de_copia.motivos,
                                               f"línea {numero}, ")
    return diferencias


_COMPARACIONES = (
    ("COPIA-DATOS", _de_datos, "los datos",
     "Número, fechas, monedas, periodo, factura rectificada y partes"),
    ("COPIA-PARTES", _de_las_partes, "la dirección o el contacto de las partes",
     "Dirección y contacto (BT-35 a BT-43 y BT-50 a BT-58)"),
    ("COPIA-IMPORTES", _de_importes, "los importes",
     "Totales (BT-106 a BT-110, BT-112 y BT-ES-17)"),
    ("COPIA-DESGLOSE", _de_desglose, "el desglose de impuestos",
     "Desglose de impuestos (BG-23)"),
    ("COPIA-LINEAS", _de_lineas, "las líneas", "Líneas (BG-25)"),
    ("COPIA-PAGO", _de_pago, "el pago", "Pago (BT-9, BT-81 y BT-84)"),
    ("COPIA-TEXTOS", _de_textos, "los textos",
     "Nombre del artículo (BT-153) y motivos de descuentos y cargos"),
)


def _resumidas(diferencias: list[str]) -> str:
    escritas = diferencias[:_NOMBRADAS]
    resto = len(diferencias) - len(escritas)
    return "; ".join(escritas) + (f"; y {resto} más" if resto else "")


def _de_una_pareja(original: Lectura, copia: Lectura,
                   ficheros: tuple[str, ...]) -> list[Incidencia]:
    incidencias = []
    if copia.es_abono:
        original, copia = _en_positivo(original), _en_positivo(copia)
    for codigo, comparar, que, campo in _COMPARACIONES:
        diferencias = comparar(original, copia)
        if diferencias:
            incidencias.append(Incidencia(
                codigo,
                AVISO,
                f"La copia de la factura {original.numero} no dice lo mismo que su "
                f"original en {que}: {_resumidas(diferencias)}.",
                campo=campo,
                encontrado=_resumidas(diferencias),
                ficheros=ficheros,
            ))
    return incidencias


def reglas_de_lote(lecturas: list[Lectura],
                   procedencias: list[str] | None = None) -> list[Incidencia]:
    """Empareja cada copia con su original y dice en qué no coinciden.

    Solo se empareja dentro del mismo emisor, por el NIF sin el prefijo de país,
    y un lote sin Facturae o sin UBL no da nada: la inmensa mayoría de los lotes
    no traen copias, y no tienen por qué oír hablar de ellas.
    """
    originales = [i for i, l in enumerate(lecturas) if l.formato == FACTURAE]
    copias = [i for i, l in enumerate(lecturas) if l.formato == UBL]
    if not originales or not copias:
        return []

    def fichero(indice: int) -> tuple[str, ...]:
        return (procedencias[indice],) if procedencias else ()

    avisos: list[Incidencia] = []
    con_diferencias = comparadas = 0
    emparejados: set[int] = set()
    otros: list[str] = []
    sueltas: list[int] = []
    separadores: list[tuple[str, str]] = []
    for indice in copias:
        pareja = _pareja_de(lecturas[indice], originales, lecturas)
        if pareja is None:
            if lecturas[indice].es_copia:
                sueltas.append(indice)
            continue
        comparadas += 1
        emparejados.add(pareja)
        if lecturas[pareja].otros_impuestos:
            otros.append(lecturas[pareja].numero)
        if (lecturas[pareja].numero != lecturas[indice].numero
                and _compacto(lecturas[pareja].numero) == _compacto(lecturas[indice].numero)):
            separadores.append((lecturas[indice].numero, lecturas[pareja].numero))
        suyas = _de_una_pareja(lecturas[pareja], lecturas[indice],
                               tuple(dict.fromkeys(fichero(pareja) + fichero(indice))))
        con_diferencias += bool(suyas)
        avisos.extend(suyas)

    salida: list[Incidencia] = []
    if comparadas:
        mensaje = (
            f"Se {'ha' if comparadas == 1 else 'han'} comparado "
            f"{_plural(comparadas, 'factura', 'facturas')} de "
            "Facturae con su copia en UBL de este lote: "
            f"{comparadas - con_diferencias} sin diferencias y {con_diferencias} con "
            "alguna, que salen aparte. Se compara número, fechas de expedición y de "
            "operación, moneda y moneda del IVA, periodo de facturación, factura "
            "rectificada, identificación, razón social, dirección y contacto de las "
            "partes, suma de las líneas, descuentos y cargos generales, base, cuotas, "
            "total con impuestos, retenciones, desglose de impuestos, vencimiento, medio "
            "de pago, cuenta de abono, motivos de descuentos y cargos y, línea a línea, "
            "nombre, cantidad, precio, neto, tipo, descuentos y cargos. No se compara el total a pagar, los anticipos, "
            "los suplidos, el nombre de una persona física, el código postal y la población "
            "de fuera de España, los medios de pago que la tabla no sostiene por su nombre "
            "ni las notas de la factura. La "
            "orden no publica la correspondencia entre los dos formatos, es la lectura "
            "de esta herramienta. Esto no dice que la copia sea válida: eso lo "
            "dice el informe de cada fichero."
        )
        if otros:
            mensaje += (" Con impuestos que no son IVA, IGIC ni IPSI, que en la copia "
                        "van como cargo, solo se comparan los datos y las líneas: "
                        + ", ".join(otros[:_NOMBRADAS]) + ".")
        sin_copia = len(originales) - len(emparejados)
        if sin_copia:
            mensaje += (" "
                        + _plural(sin_copia, "factura de Facturae se queda",
                                  "facturas de Facturae se quedan")
                        + " sin copia en este lote.")
        salida.append(Incidencia(
            "COPIA-COMPARADA",
            NOTA,
            mensaje,
            campo="Copia fiel",
            encontrado=f"{_plural(comparadas, 'comparada', 'comparadas')}, "
                       f"{con_diferencias} con diferencias",
        ))
    salida.extend(avisos)
    if separadores:
        # Nota y una sola: un conversor que junta con guion lo hace en todas sus
        # facturas con serie, y ninguna norma le dice que no. Medido el
        # 01-11-2026 leyendo `gobl.ubl`, que junta con guion.
        nombradas = ", ".join(f"{copia} y {suya}" for copia, suya in separadores[:_NOMBRADAS])
        salida.append(Incidencia(
            "COPIA-SEPARADOR",
            NOTA,
            f"En {_plural(len(separadores), 'copia', 'copias')} el número junta la serie "
            f"y el número de otra manera que aquí: {nombradas}. La orden tiene un solo "
            "campo para los dos y no dice cómo se juntan. Aquí se pegan sin nada, que es "
            "como los junta el código único. Si tu programa o la AEAT buscan la factura "
            "por su número, conviene escribirlo igual en todas partes.",
            campo="Número de factura (BT-1)",
            encontrado=nombradas,
        ))
    if sueltas:
        nombres = ", ".join(lecturas[i].numero for i in sueltas[:_NOMBRADAS])
        resto = len(sueltas) - _NOMBRADAS
        salida.append(Incidencia(
            "COPIA-SIN-PAREJA",
            NOTA,
            f"{_plural(len(sueltas), 'copia', 'copias')} de este lote no "
            f"{'encuentra' if len(sueltas) == 1 else 'encuentran'} su original entre "
            f"los Facturae: {nombres}{f' y {resto} más' if resto > 0 else ''}. Se "
            "emparejan por el NIF del emisor y por el número, serie incluida. Sin "
            "pareja no se comparan.",
            campo="Copia fiel",
            encontrado=nombres,
            ficheros=tuple(dict.fromkeys(f for i in sueltas for f in fichero(i))),
        ))
    return salida
