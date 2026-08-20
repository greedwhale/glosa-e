"""Reglas de negocio de la norma EN 16931 sobre facturas en UBL.

La norma son 955 reglas y ahí es donde se produce la mayoría de los rechazos:
un documento puede pasar la validación de forma (XSD) y fallar la de contenido.

Este módulo implementa las reglas de mayor valor —campos obligatorios y, sobre
todo, las de cuadre aritmético— con el mensaje escrito en castellano llano. La
traducción es el producto: las reglas son públicas y de todos, pero un error
como «BR-CO-13» no le dice nada a quien tiene que arreglar la factura.

El importe se maneja siempre con Decimal. Con float, 0.1 + 0.2 no da 0.3 y una
factura correcta se rechazaría por un céntimo fantasma.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from lxml import etree

from validador.formato import UBL, Deteccion, detectar

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}

# La norma trabaja con importes redondeados a dos decimales, así que una
# diferencia de un céntimo no es un error: es el redondeo permitido.
TOLERANCIA = Decimal("0.01")

ERROR = "error"
AVISO = "aviso"


@dataclass(frozen=True)
class Incidencia:
    """Un incumplimiento concreto, explicado para quien tiene que arreglarlo."""

    codigo: str
    gravedad: str
    mensaje: str
    campo: str | None = None
    esperado: str | None = None
    encontrado: str | None = None

    def __str__(self) -> str:
        partes = [f"[{self.codigo}] {self.mensaje}"]
        if self.campo:
            partes.append(f"  Campo: {self.campo}")
        if self.esperado is not None:
            partes.append(f"  Debería ser: {self.esperado}")
        if self.encontrado is not None:
            partes.append(f"  Tiene: {self.encontrado}")
        return "\n".join(partes)


@dataclass
class Informe:
    """Resultado de validar un documento."""

    deteccion: Deteccion | None = None
    incidencias: list[Incidencia] = field(default_factory=list)

    @property
    def errores(self) -> list[Incidencia]:
        return [i for i in self.incidencias if i.gravedad == ERROR]

    @property
    def avisos(self) -> list[Incidencia]:
        return [i for i in self.incidencias if i.gravedad == AVISO]

    @property
    def conforme(self) -> bool:
        return not self.errores

    def __bool__(self) -> bool:
        return self.conforme

    def resumen(self) -> str:
        # Ojo: `Deteccion` define __bool__, así que hay que preguntar por None
        # explícitamente. Escrito como `self.deteccion and not self.deteccion`
        # la condición es siempre falsa y el mensaje no salía nunca.
        if self.deteccion is not None and not self.deteccion:
            return f"No se ha podido validar. {self.deteccion.motivo}"
        cabecera = self.deteccion.resumen() if self.deteccion else "Documento"
        if self.conforme:
            cola = "sin errores"
            if self.avisos:
                cola += f", {len(self.avisos)} aviso(s)"
            return f"{cabecera} — {cola}."
        return (
            f"{cabecera} — {len(self.errores)} error(es)"
            f"{f', {len(self.avisos)} aviso(s)' if self.avisos else ''}."
        )

    def detalle(self) -> str:
        lineas = [self.resumen()]
        for incidencia in self.errores + self.avisos:
            lineas.append("")
            lineas.append(str(incidencia))
        return "\n".join(lineas)


# --- Utilidades ------------------------------------------------------------


def _texto(nodo, ruta: str) -> str | None:
    encontrados = nodo.xpath(ruta, namespaces=NS)
    if not encontrados:
        return None
    valor = encontrados[0]
    texto = valor if isinstance(valor, str) else (valor.text or "")
    texto = texto.strip()
    return texto or None


def _importe(nodo, ruta: str) -> Decimal | None:
    """Lee un importe como Decimal. Devuelve None si falta o no es un número."""
    bruto = _texto(nodo, ruta)
    if bruto is None:
        return None
    try:
        return Decimal(bruto)
    except InvalidOperation:
        return None


def _cuadra(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= TOLERANCIA


def _fmt(valor: Decimal | None) -> str:
    return "(vacío)" if valor is None else f"{valor:.2f}"


# --- Reglas de campos obligatorios -----------------------------------------

# (código, ruta XPath, nombre en castellano del campo, explicación)
_OBLIGATORIOS: tuple[tuple[str, str, str, str], ...] = (
    (
        "BR-01",
        "./cbc:CustomizationID",
        "Identificador de especificación",
        "La factura debe declarar a qué especificación se ajusta.",
    ),
    (
        "BR-02",
        "./cbc:ID",
        "Número de factura",
        "La factura debe llevar número.",
    ),
    (
        "BR-03",
        "./cbc:IssueDate",
        "Fecha de expedición",
        "La factura debe llevar fecha de expedición.",
    ),
    (
        "BR-04",
        "./cbc:InvoiceTypeCode",
        "Código de tipo de factura",
        "La factura debe indicar de qué tipo es (380 para factura ordinaria).",
    ),
    (
        "BR-05",
        "./cbc:DocumentCurrencyCode",
        "Moneda",
        "La factura debe indicar en qué moneda está.",
    ),
    (
        "BR-06",
        "./cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity"
        "/cbc:RegistrationName",
        "Nombre del vendedor",
        "Falta el nombre o razón social de quien emite la factura.",
    ),
    (
        "BR-07",
        "./cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity"
        "/cbc:RegistrationName",
        "Nombre del comprador",
        "Falta el nombre o razón social de quien recibe la factura.",
    ),
    (
        "BR-08",
        "./cac:AccountingSupplierParty/cac:Party/cac:PostalAddress",
        "Dirección del vendedor",
        "Falta la dirección postal del vendedor.",
    ),
    (
        "BR-09",
        "./cac:AccountingSupplierParty/cac:Party/cac:PostalAddress"
        "/cac:Country/cbc:IdentificationCode",
        "País del vendedor",
        "La dirección del vendedor debe incluir el código de país (ES, FR...).",
    ),
    (
        "BR-10",
        "./cac:AccountingCustomerParty/cac:Party/cac:PostalAddress",
        "Dirección del comprador",
        "Falta la dirección postal del comprador.",
    ),
    (
        "BR-11",
        "./cac:AccountingCustomerParty/cac:Party/cac:PostalAddress"
        "/cac:Country/cbc:IdentificationCode",
        "País del comprador",
        "La dirección del comprador debe incluir el código de país.",
    ),
    (
        "BR-12",
        "./cac:LegalMonetaryTotal/cbc:LineExtensionAmount",
        "Suma de importes de línea",
        "Falta la suma de los importes netos de las líneas.",
    ),
    (
        "BR-13",
        "./cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount",
        "Base imponible total",
        "Falta el importe total sin impuestos.",
    ),
    (
        "BR-14",
        "./cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount",
        "Total con impuestos",
        "Falta el importe total con impuestos incluidos.",
    ),
    (
        "BR-15",
        "./cac:LegalMonetaryTotal/cbc:PayableAmount",
        "Total a pagar",
        "Falta el importe que hay que pagar.",
    ),
)


def _reglas_obligatorios(raiz) -> list[Incidencia]:
    incidencias = []
    for codigo, ruta, campo, explicacion in _OBLIGATORIOS:
        if not raiz.xpath(ruta, namespaces=NS):
            incidencias.append(
                Incidencia(codigo, ERROR, explicacion, campo=campo, encontrado="(falta)")
            )
        elif _texto(raiz, ruta) is None and not ruta.endswith("PostalAddress"):
            incidencias.append(
                Incidencia(
                    codigo,
                    ERROR,
                    f"{explicacion} El elemento existe pero está vacío.",
                    campo=campo,
                    encontrado="(vacío)",
                )
            )
    return incidencias


def _regla_lineas(raiz) -> list[Incidencia]:
    """BR-16: la factura debe tener al menos una línea."""
    if not raiz.xpath("./cac:InvoiceLine", namespaces=NS):
        return [
            Incidencia(
                "BR-16",
                ERROR,
                "La factura no tiene ninguna línea. Debe detallar al menos un "
                "concepto facturado.",
                campo="Líneas de factura",
                encontrado="0 líneas",
            )
        ]
    return []


# --- Reglas de cuadre aritmético -------------------------------------------


def _reglas_cuadre(raiz) -> list[Incidencia]:
    """Las BR-CO-*: que las sumas de la factura cuadren entre sí.

    Son las que más rechazos provocan y las más difíciles de ver a ojo, porque
    el error suele estar en una línea perdida entre cincuenta.
    """
    incidencias: list[Incidencia] = []
    total = "./cac:LegalMonetaryTotal"

    suma_lineas = _importe(raiz, f"{total}/cbc:LineExtensionAmount")
    base = _importe(raiz, f"{total}/cbc:TaxExclusiveAmount")
    con_impuestos = _importe(raiz, f"{total}/cbc:TaxInclusiveAmount")
    a_pagar = _importe(raiz, f"{total}/cbc:PayableAmount")
    descuentos = _importe(raiz, f"{total}/cbc:AllowanceTotalAmount") or Decimal(0)
    cargos = _importe(raiz, f"{total}/cbc:ChargeTotalAmount") or Decimal(0)
    anticipos = _importe(raiz, f"{total}/cbc:PrepaidAmount") or Decimal(0)
    redondeo = _importe(raiz, f"{total}/cbc:PayableRoundingAmount") or Decimal(0)
    impuestos = _importe(raiz, "./cac:TaxTotal/cbc:TaxAmount")

    # BR-24: cada línea debe llevar su importe neto. Se comprueba aparte del
    # cuadre, porque una línea sin importe es un error aunque la factura no
    # declare el total; si se anida bajo esa condición, deja de avisar justo
    # en el caso en que faltan las dos cosas.
    lineas = raiz.xpath("./cac:InvoiceLine", namespaces=NS)
    acumulado = Decimal(0)
    sin_importe: list[str] = []
    for indice, linea in enumerate(lineas, start=1):
        importe = _importe(linea, "./cbc:LineExtensionAmount")
        if importe is None:
            sin_importe.append(_texto(linea, "./cbc:ID") or str(indice))
        else:
            acumulado += importe

    if sin_importe:
        incidencias.append(
            Incidencia(
                "BR-24",
                ERROR,
                "Hay líneas sin importe neto. Cada línea debe llevar el suyo.",
                campo="Líneas " + ", ".join(sin_importe),
                encontrado="(falta el importe)",
            )
        )

    # BR-CO-10: la suma declarada debe coincidir con la suma real de las líneas.
    # Solo tiene sentido si todas las líneas tienen importe.
    if lineas and suma_lineas is not None and not sin_importe:
        if not _cuadra(acumulado, suma_lineas):
            incidencias.append(
                Incidencia(
                    "BR-CO-10",
                    ERROR,
                    "La suma de importes de línea que declara la factura no "
                    "coincide con la suma real de sus líneas. Suele ser una "
                    "línea añadida o modificada sin recalcular el total.",
                    campo="Suma de importes de línea",
                    esperado=f"{acumulado:.2f} (suma de las {len(lineas)} líneas)",
                    encontrado=_fmt(suma_lineas),
                )
            )

    # BR-CO-13: base imponible = suma de líneas - descuentos + cargos.
    if suma_lineas is not None and base is not None:
        calculada = suma_lineas - descuentos + cargos
        if not _cuadra(calculada, base):
            detalle = f"{suma_lineas:.2f}"
            if descuentos:
                detalle += f" - {descuentos:.2f} de descuentos"
            if cargos:
                detalle += f" + {cargos:.2f} de cargos"
            incidencias.append(
                Incidencia(
                    "BR-CO-13",
                    ERROR,
                    "La base imponible no cuadra con las líneas menos los "
                    "descuentos más los cargos.",
                    campo="Base imponible total",
                    esperado=f"{calculada:.2f}  ({detalle})",
                    encontrado=_fmt(base),
                )
            )

    # BR-CO-15: total con impuestos = base imponible + impuestos.
    if base is not None and con_impuestos is not None:
        if impuestos is None:
            incidencias.append(
                Incidencia(
                    "BR-CO-14",
                    AVISO,
                    "La factura no declara el importe total de impuestos, así "
                    "que no se ha podido comprobar que el total cuadre.",
                    campo="Importe total de impuestos",
                    encontrado="(falta)",
                )
            )
        else:
            calculada = base + impuestos
            if not _cuadra(calculada, con_impuestos):
                incidencias.append(
                    Incidencia(
                        "BR-CO-15",
                        ERROR,
                        "El total con impuestos no es la base imponible más el "
                        "importe de impuestos.",
                        campo="Total con impuestos",
                        esperado=(
                            f"{calculada:.2f}  ({base:.2f} + {impuestos:.2f} "
                            "de impuestos)"
                        ),
                        encontrado=_fmt(con_impuestos),
                    )
                )

    # BR-CO-16: a pagar = total con impuestos - anticipos + redondeo.
    if con_impuestos is not None and a_pagar is not None:
        calculada = con_impuestos - anticipos + redondeo
        if not _cuadra(calculada, a_pagar):
            desglose = []
            if anticipos:
                desglose.append(f"- {anticipos:.2f} ya pagados")
            if redondeo:
                desglose.append(f"+ {redondeo:.2f} de redondeo")
            explicacion = (
                f"{calculada:.2f}  ({con_impuestos:.2f} {' '.join(desglose)})"
                if desglose
                else f"{calculada:.2f}, que es el total con impuestos"
            )
            incidencias.append(
                Incidencia(
                    "BR-CO-16",
                    ERROR,
                    "El importe a pagar no cuadra con el total menos lo ya "
                    "anticipado.",
                    campo="Total a pagar",
                    esperado=explicacion,
                    encontrado=_fmt(a_pagar),
                )
            )

    return incidencias


# --- Entrada pública -------------------------------------------------------


def validar(datos: bytes | str) -> Informe:
    """Valida una factura contra las reglas de negocio implementadas."""
    deteccion = detectar(datos)
    informe = Informe(deteccion=deteccion)

    if not deteccion:
        return informe

    if deteccion.familia != UBL:
        informe.incidencias.append(
            Incidencia(
                "SIN-SOPORTE",
                AVISO,
                f"Las reglas EN 16931 solo están implementadas para UBL. "
                f"Este documento es {deteccion.familia} y solo se ha "
                f"identificado, no validado.",
                campo="Formato",
                encontrado=deteccion.familia,
            )
        )
        return informe

    if isinstance(datos, str):
        datos = datos.encode("utf-8")
    raiz = etree.fromstring(datos, parser=_parser_seguro())

    if not deteccion.conforme_en16931:
        informe.incidencias.append(
            Incidencia(
                "BR-01",
                AVISO,
                "El documento no declara conformidad con EN 16931 en su "
                "CustomizationID. Se valida igualmente, pero un receptor "
                "estricto podría rechazarlo por eso.",
                campo="Identificador de especificación",
                esperado="urn:cen.eu:en16931:2017...",
                encontrado=deteccion.perfil or "(falta)",
            )
        )

    informe.incidencias.extend(_reglas_obligatorios(raiz))
    informe.incidencias.extend(_regla_lineas(raiz))
    informe.incidencias.extend(_reglas_cuadre(raiz))
    return informe


def _parser_seguro() -> etree.XMLParser:
    from validador.formato import _parser

    return _parser()
