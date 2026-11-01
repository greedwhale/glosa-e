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
Porque la correspondencia entre Facturae y UBL no la publica nadie: es la tabla
de `copia_fiel.py`, leída aquí del esquema de Facturae y del anexo de la orden.
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
- la base de la entrada del recargo de equivalencia, que la orden no explica.

Y una factura con impuestos que no son IVA, IGIC ni IPSI se compara solo en sus
datos y en sus líneas: esos impuestos van en la copia como cargo, y entonces ni
la base, ni las cuotas, ni el total llegan con el mismo número.

Lo que falta en la copia porque no tiene sitio no es una diferencia. Y todo
esto no dice que la copia ni el original sean válidos: eso lo dice el informe
de cada fichero.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal

from validador import cifras, codigo_unico
from validador.formato import FACTURAE, UBL
from validador.incidencias import AVISO, NOTA, Incidencia, entre_comillas
from validador.sintaxis import (
    SINTAXIS,
    a_decimal,
    buscar,
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


@dataclass(frozen=True)
class Linea:
    """Lo que se compara de una línea. `tipo` es None si no se puede comparar."""

    cantidad: Decimal | None
    neto: Decimal | None
    tipo: Decimal | None


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
        lineas.append(Linea(_numero(linea, "Quantity"),
                            _numero(linea, "GrossAmount"), tipo))
    return tuple(lineas)


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
            # El total de Facturae resta las retenciones y BT-112 no: se le
            # devuelven, y así este campo es lo que debería decir la copia.
            total=None if total is None else total + (retenciones or Decimal(0)),
            retenciones=retenciones,
            desglose=desglose,
            lineas=_lineas_facturae(factura),
            otros_impuestos=otros,
        ))
    return lecturas


def _desglose_ubl(raiz, sintaxis) -> tuple:
    desglose: dict = {}
    for grupo in buscar(raiz, sintaxis.desglose, sintaxis.espacios):
        categoria = (texto(grupo, sintaxis.desglose_categoria, sintaxis) or "").upper()
        tipo = importe(grupo, sintaxis.desglose_tipo, sintaxis) or Decimal(0)
        base = importe(grupo, sintaxis.desglose_base, sintaxis) or Decimal(0)
        cuota = importe(grupo, sintaxis.desglose_cuota, sintaxis) or Decimal(0)
        familia = _IMPUESTOS_COPIA.get(categoria, "IVA")
        if familia == "recargo":
            _sumar(desglose, (familia, tipo), None, cuota)
        else:
            _sumar(desglose, (familia if tipo else "", tipo), base, cuota)
    return _congelado(desglose)


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
        lineas=tuple(
            Linea(importe(linea, sintaxis.linea_cantidad, sintaxis),
                  importe(linea, "./cbc:LineExtensionAmount", sintaxis),
                  importe(linea, sintaxis.linea_tipo, sintaxis) or Decimal(0))
            for linea in buscar(raiz, sintaxis.lineas, espacios)
        ),
        indicador_de_copia=texto_es(raiz, "BT-ES-1"),
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


def _igual(a: Decimal | None, b: Decimal | None) -> bool:
    return a is not None and b is not None and abs(a - b) <= _MARGEN


def _pareja_de(copia: Lectura, originales: list[int], lecturas: list[Lectura]) -> int | None:
    """El original de una copia: primero exacto, luego sin separadores, y por
    último por el número sin la serie, solo si no hay dos que encajen."""
    del_emisor = [i for i in originales if lecturas[i].emisor == copia.emisor]
    for i in del_emisor:
        if lecturas[i].numero == copia.numero:
            return i
    for i in del_emisor:
        if _compacto(lecturas[i].numero) == _compacto(copia.numero):
            return i
    solo_numero = [i for i in del_emisor
                   if _compacto(lecturas[i].numero_solo) == _compacto(copia.numero)]
    return solo_numero[0] if len(solo_numero) == 1 else None


def _de_datos(original: Lectura, copia: Lectura) -> list[str]:
    diferencias = []
    if original.numero != copia.numero:
        if _compacto(original.numero) == _compacto(copia.numero):
            diferencias.append(
                f"número (BT-1): {copia.numero} en la copia y {original.numero} con "
                "la serie y el número pegados. La orden no dice cómo se juntan, "
                "y aquí se pegan sin separador")
        else:
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
    if original.comprador and original.comprador[0] not in copia.comprador:
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


def _de_importes(original: Lectura, copia: Lectura) -> list[str]:
    diferencias = []
    if not original.otros_impuestos:
        for nombre, de_original, de_copia in (
            ("base (BT-109)", original.base, copia.base),
            ("cuotas (BT-110)", original.cuotas, copia.cuotas),
            ("total con impuestos (BT-112)", original.total, copia.total),
        ):
            if de_original is not None and not _igual(de_original, de_copia):
                diferencias.append(f"{nombre}: {_cifra(de_original)} según el original "
                                   f"y {_cifra(de_copia)} en la copia")
    retenido = original.retenciones or Decimal(0)
    if (not original.otros_impuestos and retenido and original.total is not None
            and _igual(original.total - retenido, copia.total)):
        diferencias.append("el total de la copia es el de Facturae tal cual, que "
                           "resta las retenciones, y BT-112 no las resta")
    if not _igual(retenido, copia.retenciones or Decimal(0)):
        diferencias.append(f"retenciones (BT-ES-17): {_cifra(retenido)} en el original y "
                           f"{_cifra(copia.retenciones)} en la copia")
    return diferencias


def _nombre_de_entrada(clave: tuple[str, Decimal]) -> str:
    familia, tipo = clave
    return f"{familia} al {cifras.tipo(tipo)}" if familia else "al 0 %"


def _de_desglose(original: Lectura, copia: Lectura) -> list[str]:
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
        if clave not in claves_original and (base or cuota):
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
        if suya.neto is not None and not _igual(suya.neto, de_copia.neto):
            diferencias.append(f"línea {numero}, neto (BT-131): {_cifra(suya.neto)} en el "
                               f"original y {_cifra(de_copia.neto)} en la copia")
        if (not original.otros_impuestos and suya.tipo is not None
                and suya.tipo != de_copia.tipo):
            diferencias.append(f"línea {numero}, tipo (BT-152): {cifras.tipo(suya.tipo)} "
                               f"en el original y {cifras.tipo(de_copia.tipo)} en la copia")
    return diferencias


_COMPARACIONES = (
    ("COPIA-DATOS", _de_datos, "los datos", "Número, fecha, moneda y partes"),
    ("COPIA-IMPORTES", _de_importes, "los importes",
     "Totales (BT-109, BT-110, BT-112 y BT-ES-17)"),
    ("COPIA-DESGLOSE", _de_desglose, "el desglose de impuestos",
     "Desglose de impuestos (BG-23)"),
    ("COPIA-LINEAS", _de_lineas, "las líneas", "Líneas (BG-25)"),
)


def _resumidas(diferencias: list[str]) -> str:
    escritas = diferencias[:_NOMBRADAS]
    resto = len(diferencias) - len(escritas)
    return "; ".join(escritas) + (f"; y {resto} más" if resto else "")


def _de_una_pareja(original: Lectura, copia: Lectura,
                   ficheros: tuple[str, ...]) -> list[Incidencia]:
    incidencias = []
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
            "alguna, que salen aparte. Se compara número, fecha, moneda, identificación y "
            "razón social de las partes, base, cuotas, total con impuestos, "
            "retenciones, desglose de impuestos y, línea a línea, cantidad, neto y "
            "tipo. No se compara el total a pagar, los anticipos, los suplidos, el "
            "nombre de una persona física, la dirección, el pago ni los textos. La "
            "correspondencia entre los dos formatos no la publica nadie, es la lectura "
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
