"""Detección del formato y la versión de una factura electrónica.

El RD 238/2026 admite cuatro formatos estructurados: Facturae, UBL, CII y
EDIFACT. Antes de poder validar nada hay que saber cuál de los cuatro tienes
delante, en qué versión, y si dice ser conforme a la norma europea EN 16931.

Nota de diseño: la versión **no** se deduce solo del namespace. Facturae ha
cambiado de convención de namespace entre versiones y hay documentación que se
contradice sobre la 3.2.1, así que se usa el namespace para identificar la
familia y el campo `SchemaVersion` del propio documento para la versión. Si
aparece un namespace desconocido pero la raíz se llama `Facturae`, se reconoce
la familia igualmente y se informa del namespace no catalogado, en vez de
fallar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

# --- Namespaces conocidos --------------------------------------------------

NS_FACTURAE: dict[str, str] = {
    "http://www.facturae.es/Facturae/2007/v3.1/Facturae": "3.1",
    "http://www.facturae.es/Facturae/2009/v3.2/Facturae": "3.2",
    "http://www.facturae.es/Facturae/2014/v3.2.1/Facturae": "3.2.1",
    "http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_1.xml": "3.2.1",
    "http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml": "3.2.2",
}

NS_UBL_FACTURA = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS_UBL_ABONO = "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
NS_UBL_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

NS_CII = "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
NS_CII_RAM = (
    "urn:un:unece:uncefact:data:standard:"
    "ReusableAggregateBusinessInformationEntity:100"
)

NS_FIRMA = "http://www.w3.org/2000/09/xmldsig#"

# Marcador de conformidad con la norma europea, tanto en UBL como en CII.
MARCADOR_EN16931 = "urn:cen.eu:en16931:2017"

# Familias
FACTURAE = "Facturae"
UBL = "UBL"
CII = "CII"
EDIFACT = "EDIFACT"

_RE_EDIFACT_INVOIC = re.compile(rb"UNH\+[^+]*\+INVOIC", re.IGNORECASE)


@dataclass(frozen=True)
class Deteccion:
    """Lo que se ha podido averiguar sobre un documento."""

    familia: str | None = None
    version: str | None = None
    tipo_documento: str | None = None  # "factura" o "abono"
    perfil: str | None = None
    conforme_en16931: bool = False
    firmado: bool = False
    namespace: str | None = None
    motivo: str = ""

    def __bool__(self) -> bool:
        return self.familia is not None

    def resumen(self) -> str:
        """Una línea legible, para logs y para el informe al usuario."""
        if not self:
            return f"Formato no reconocido: {self.motivo}"
        partes = [self.familia]
        if self.version:
            partes.append(f"v{self.version}")
        if self.tipo_documento:
            partes.append(f"({self.tipo_documento})")
        if self.conforme_en16931:
            partes.append("· conforme EN 16931")
        if self.firmado:
            partes.append("· firmado")
        return " ".join(partes)


def _parser() -> etree.XMLParser:
    """Parser endurecido para XML que llega de fuera.

    Sin resolución de entidades ni acceso a red: un fichero subido por un
    tercero no debe poder leer ficheros del servidor ni hacer peticiones
    salientes.
    """
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        huge_tree=False,
        recover=False,
    )


def _partir_nombre(etiqueta: str) -> tuple[str | None, str]:
    """Separa '{namespace}nombre' en sus dos partes."""
    if etiqueta.startswith("{"):
        namespace, _, nombre = etiqueta[1:].partition("}")
        return namespace, nombre
    return None, etiqueta


def _texto(raiz: etree._Element, ruta: str, espacios: dict[str, str]) -> str | None:
    encontrados = raiz.xpath(ruta, namespaces=espacios)
    if not encontrados:
        return None
    valor = encontrados[0]
    texto = valor if isinstance(valor, str) else (valor.text or "")
    texto = texto.strip()
    return texto or None


def _tiene_firma(raiz: etree._Element) -> bool:
    return bool(raiz.xpath("//ds:Signature", namespaces={"ds": NS_FIRMA}))


def _detectar_facturae(raiz: etree._Element, namespace: str | None) -> Deteccion:
    # SchemaVersion manda sobre el namespace. Puede venir con o sin namespace
    # según cómo se haya generado el fichero, así que se busca por nombre local.
    version = _texto(raiz, "//*[local-name()='SchemaVersion']", {})
    version_ns = NS_FACTURAE.get(namespace or "")

    if version and version_ns and version != version_ns:
        motivo = (
            f"El documento declara SchemaVersion {version} pero su namespace "
            f"corresponde a la versión {version_ns}. Se toma SchemaVersion."
        )
    elif not version and version_ns:
        version = version_ns
        motivo = "Versión deducida del namespace: el documento no trae SchemaVersion."
    elif version and not version_ns:
        motivo = (
            f"Namespace no catalogado ({namespace}). "
            f"Versión tomada de SchemaVersion."
        )
    elif version:
        motivo = "Formato reconocido."
    else:
        motivo = (
            "Se reconoce como Facturae por el elemento raíz, pero no trae "
            "SchemaVersion ni un namespace conocido."
        )

    # En Facturae el tipo va en cada factura, no en la cabecera. Si hay al
    # menos un documento rectificativo, se marca como abono.
    tipo = None
    if raiz.xpath("//*[local-name()='InvoiceDocumentType']"):
        tipos = raiz.xpath("//*[local-name()='InvoiceDocumentType']/text()")
        tipo = "abono" if any("RECTIFICATIVA" in t.upper() for t in tipos) else "factura"

    return Deteccion(
        familia=FACTURAE,
        version=version,
        tipo_documento=tipo,
        perfil=None,
        conforme_en16931=False,  # Facturae es formato nacional, no CIUS de EN 16931
        firmado=_tiene_firma(raiz),
        namespace=namespace,
        motivo=motivo,
    )


def _detectar_ubl(raiz: etree._Element, namespace: str, nombre: str) -> Deteccion:
    espacios = {"cbc": NS_UBL_CBC}
    perfil = _texto(raiz, "./cbc:CustomizationID", espacios)
    version = _texto(raiz, "./cbc:UBLVersionID", espacios)
    return Deteccion(
        familia=UBL,
        version=version or "2.1",
        tipo_documento="abono" if nombre == "CreditNote" else "factura",
        perfil=perfil,
        conforme_en16931=bool(perfil and perfil.startswith(MARCADOR_EN16931)),
        firmado=_tiene_firma(raiz),
        namespace=namespace,
        motivo="Formato reconocido."
        if version
        else "Sin UBLVersionID; se asume UBL 2.1, que es lo habitual.",
    )


def _detectar_cii(raiz: etree._Element, namespace: str) -> Deteccion:
    perfil = _texto(
        raiz,
        "//*[local-name()='GuidelineSpecifiedDocumentContextParameter']"
        "/*[local-name()='ID']",
        {},
    )
    # En CII el tipo de documento va en un código: 380 factura, 381 abono.
    codigo = _texto(
        raiz,
        "//*[local-name()='ExchangedDocument']/*[local-name()='TypeCode']",
        {},
    )
    tipo = {"380": "factura", "381": "abono"}.get(codigo or "")
    return Deteccion(
        familia=CII,
        version="D16B",
        tipo_documento=tipo,
        perfil=perfil,
        conforme_en16931=bool(perfil and perfil.startswith(MARCADOR_EN16931)),
        firmado=_tiene_firma(raiz),
        namespace=namespace,
        motivo="Formato reconocido."
        if perfil
        else "Sin perfil declarado: no dice a qué guía se ajusta.",
    )


def _detectar_edifact(datos: bytes) -> Deteccion | None:
    cabeza = datos.lstrip()[:3].upper()
    if cabeza[:3] not in (b"UNA", b"UNB"):
        return None
    if not _RE_EDIFACT_INVOIC.search(datos):
        return Deteccion(
            familia=EDIFACT,
            motivo="Mensaje EDIFACT, pero no parece un INVOIC (factura).",
        )
    return Deteccion(
        familia=EDIFACT,
        tipo_documento="factura",
        motivo="Mensaje EDIFACT INVOIC. La validación EDIFACT no está implementada.",
    )


def detectar(datos: bytes | str) -> Deteccion:
    """Identifica el formato de una factura a partir de su contenido."""
    if isinstance(datos, str):
        datos = datos.encode("utf-8")
    if not datos.strip():
        return Deteccion(motivo="El fichero está vacío.")

    edifact = _detectar_edifact(datos)
    if edifact is not None:
        return edifact

    try:
        raiz = etree.fromstring(datos, parser=_parser())
    except etree.XMLSyntaxError as error:
        return Deteccion(
            motivo=f"No es XML válido y tampoco EDIFACT. Detalle: {error.msg}"
        )

    namespace, nombre = _partir_nombre(raiz.tag)

    # Facturae firmado en modo «enveloping»: la raíz es la firma y la factura
    # cuelga de dentro. Se busca el Facturae real antes de rendirse.
    if nombre == "Signature" and namespace == NS_FIRMA:
        internos = raiz.xpath("//*[local-name()='Facturae']")
        if internos:
            interno = internos[0]
            namespace_interno, _ = _partir_nombre(interno.tag)
            deteccion = _detectar_facturae(interno, namespace_interno)
            return Deteccion(**{**deteccion.__dict__, "firmado": True})

    if nombre == "Facturae":
        return _detectar_facturae(raiz, namespace)
    if namespace == NS_UBL_FACTURA and nombre == "Invoice":
        return _detectar_ubl(raiz, namespace, nombre)
    if namespace == NS_UBL_ABONO and nombre == "CreditNote":
        return _detectar_ubl(raiz, namespace, nombre)
    if namespace == NS_CII and nombre == "CrossIndustryInvoice":
        return _detectar_cii(raiz, namespace)

    return Deteccion(
        namespace=namespace,
        motivo=(
            f"XML válido, pero su elemento raíz «{nombre}» no corresponde a "
            "Facturae, UBL ni CII."
        ),
    )


def detectar_archivo(ruta: str | Path) -> Deteccion:
    """Igual que `detectar`, leyendo de un fichero."""
    camino = Path(ruta)
    try:
        return detectar(camino.read_bytes())
    except FileNotFoundError:
        return Deteccion(motivo=f"No existe el fichero {camino}.")
    except OSError as error:
        return Deteccion(motivo=f"No se ha podido leer {camino}: {error}")
