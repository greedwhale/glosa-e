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
from functools import lru_cache
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

# Marcadores de conformidad con la norma europea, tanto en UBL como en CII.
#
# **Son dos y no uno desde mayo de 2026**, que es cuando se publicó la EN
# 16931-1:2026 y se retiró formalmente la de 2017. Las dos ediciones van a
# convivir años: Peppol y todo lo que hay hoy en circulación declaran la de
# 2017, y la solución pública española pide la de 2026
# —`urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0`, que es
# el valor literal del anexo I y está en `cius_es.ESPECIFICACION`—.
#
# Con un solo marcador, una factura del CIUS español salía «no declara
# conformidad con EN 16931» **por declarar la edición correcta**. No es un
# detalle: BR-01 avisa de eso, y avisar de lo que está bien es peor que
# callarse.
MARCADORES_EN16931 = ("urn:cen.eu:en16931:2017", "urn:cen.eu:en16931:2026")

# El de 2017 a secas, que es el que sigue viéndose en el 99 % de lo que llega
# y el que se enseña como ejemplo cuando falta.
MARCADOR_EN16931 = MARCADORES_EN16931[0]

# El CIUS de la solución pública. Se escribe detrás del marcador de 2026, en el
# mismo `CustomizationID`. El valor entero está en `cius_es.ESPECIFICACION`,
# que sale del anexo; aquí va solo el trozo que identifica al CIUS, y una
# prueba comprueba que los dos siguen diciendo lo mismo. Si el anexo cambia el
# URN, salta ahí y no en producción.
MARCADOR_CIUS_ES = "urn:aeat.es:CIUS-ES-SPFE"

# Familias
FACTURAE = "Facturae"
UBL = "UBL"
CII = "CII"
EDIFACT = "EDIFACT"

# La cabecera de mensaje: UNH+referencia+TIPO:D:96A:UN. De ahí sale el tipo
# de mensaje y la versión del directorio. Y el BGM, de donde sale si es una
# factura o un abono. Los saltos de línea entre segmentos son opcionales: unos
# ficheros vienen en una sola tira y otros con un segmento por línea. Sin
# admitir los dos, la mitad de las facturas se quedaban sin tipo de documento.
#
# **Los separadores no se dan por supuestos.** Estaban escritos aquí a pelo
# —`+` entre elementos, `:` entre componentes, `'` al final del segmento—, que
# son los de por defecto de ISO 9735 y los que usa casi todo el mundo. Pero un
# fichero puede declarar los suyos en el UNA, que es para lo que existe, y
# entonces aquí no casaba nada: la detección contestaba «Mensaje EDIFACT, pero
# sin cabecera UNH: no se ve de qué tipo es», que es **falso** —el partidor de
# `edifact.py` sí lo encuentra, porque él sí lee el UNA— y además dejaba la
# versión y el tipo de documento en blanco. Medido el 22-09-2026 sobre la
# factura de W.S. Hein del corpus, que declara `UNA^<.? >`: familia EDIFACT,
# versión None, tipo None. Es el único de los 64 ficheros ajenos con
# separadores propios, y por eso esto aguantó tanto sin verse.
@lru_cache(maxsize=16)
def _regex_edifact(componente: str, elemento: str, terminador: str):
    """Las dos expresiones, montadas con los separadores de este fichero."""
    comp = re.escape(componente.encode("latin-1"))
    elem = re.escape(elemento.encode("latin-1"))
    fin = re.escape(terminador.encode("latin-1"))
    unh = re.compile(
        rb"UNH" + elem + rb"[^" + elem + rb"]*" + elem + rb"([A-Z]{6})("
        + comp + rb"[^" + fin + rb"]*)?",
        re.IGNORECASE,
    )
    bgm = re.compile(
        rb"(?:^|[" + fin + rb"\r\n])\s*BGM" + elem + rb"([0-9]{3})",
        re.IGNORECASE,
    )
    return unh, bgm


def _separadores(datos: bytes) -> tuple[str, str, str]:
    """Componente, elemento y terminador, según el UNA si lo hay.

    Quien sabe leer un UNA es `edifact.py`, y se le pregunta a él en vez de
    escribirlo otra vez aquí. La importación va dentro porque `edifact.py`
    importa de este módulo y al revés habría un ciclo.

    Se le dan los primeros bytes y no el fichero entero: el UNA, si está, son
    los nueve primeros caracteres, y `cuantos_de_servicio` necesita ver el UNB
    que viene detrás para saber si el UNA trae cinco caracteres o seis.
    """
    from validador.edifact import servicio_de

    cabeza = sin_marca(datos)[:64].decode("latin-1", errors="replace")
    servicio, _ = servicio_de(cabeza)
    return servicio.componente, servicio.elemento, servicio.terminador
_RE_EDIFACT_DIR = re.compile(rb"([0-9]{2}[A-Z])", re.IGNORECASE)
# En EDIFACT el perfil no va en un campo suyo: viaja dentro de un FTX de
# texto libre, asi que se busca en los bytes. Los dos marcadores, por lo
# mismo que arriba.
_MARCADORES_EDIFACT = tuple(
    m.encode("latin-1") for m in MARCADORES_EN16931
)

# En EDIFACT el tipo va en el mismo código que en CII: 380 factura, 381 abono.
_TIPOS_EDIFACT = {b"380": "factura", b"381": "abono"}


class _Vacio:
    def group(self, _):
        return b""


_VACIO = _Vacio()


def _version_edifact(bruto: bytes | None) -> str | None:
    """La versión del directorio, «96A» o «14B», de donde venga."""
    if not bruto:
        return None
    encontrado = _RE_EDIFACT_DIR.search(bruto)
    return encontrado.group(1).decode("latin-1").upper() if encontrado else None


# En qué queda la firma del documento después de mirarla. Los tres estados
# viven aquí, y no en `firma.py`, porque quien los escribe es la línea de
# estado de `Deteccion` y `firma.py` ya importa de este módulo: al revés habría
# un ciclo de importación.
FIRMA_EN_PIE = "en pie"
FIRMA_SIN_COMPROBAR = "sin comprobar"
FIRMA_ROTA = "rota"

# Lo que sale en la línea de estado por cada uno. `None` es el cuarto caso y no
# es lo mismo que «sin comprobar»: significa que nadie ha llegado a mirarlas
# —una detección a secas, sin validar—, y por eso dice solo lo que se ve.
#
# Antes había una sola etiqueta, «· firmado», y salía por el mero hecho de que
# el documento trajera un bloque `Signature`. Una factura con una firma
# falsificada —un algoritmo inventado, que no se puede comprobar— se leía
# «Facturae v3.2.2 (factura) · firmado — sin errores», y ese «firmado» al lado
# de «sin errores» es justo lo que este proyecto no puede decir.
_ETIQUETA_FIRMA = {
    FIRMA_EN_PIE: "· firmado",
    FIRMA_SIN_COMPROBAR: "· firma sin comprobar",
    FIRMA_ROTA: "· firma que no se sostiene",
    None: "· con firma",
}


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

    def resumen(self, firma: str | None = None) -> str:
        """Una línea legible, para logs y para el informe al usuario.

        `firma` es en qué quedó la firma al comprobarla, que aquí no se sabe
        —esto es la detección, y la detección solo ve que hay un bloque de
        firma—. Lo trae quien sí lo sabe: `Informe.resumen`. Ver
        `_ETIQUETA_FIRMA`.
        """
        if not self:
            return f"Formato no reconocido: {self.motivo}"
        partes = [self.familia]
        if self.version:
            partes.append(f"v{self.version}")
        if self.tipo_documento:
            partes.append(f"({self.tipo_documento})")
        if self.conforme_en16931:
            # «Dice seguir» y no «conforme». Esto es la **detección**: lo único
            # que se ha mirado es el identificador de perfil que el documento
            # lleva escrito, y eso lo pone quien la emite. Decía «· conforme
            # EN 16931» y salía igual en una factura con dos errores de esa
            # misma norma —«UBL v2.1 (factura) · conforme EN 16931 — 2
            # error(es)»—, que es la línea contradiciéndose a sí misma en ocho
            # palabras. Si cumple o no lo dicen los errores, no esta etiqueta.
            partes.append("· dice seguir EN 16931")
        if self.firmado:
            partes.append(_ETIQUETA_FIRMA[firma])
        return " ".join(partes)


def parser() -> etree.XMLParser:
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


def entidades_sin_resolver(raiz) -> list[str]:
    """Los elementos cuyo contenido es una entidad que aquí no se expande.

    Viene de `parser()`, que lleva `resolve_entities=False` para que un fichero
    de un tercero no pueda leerse ficheros del servidor. La decisión es buena y
    tiene un efecto que hay que decir: donde el documento escribió `&monto;`,
    el árbol se queda con un nodo de referencia y el `.text` del elemento vale
    `None`. Medido el 21-09-2026 sobre un Facturae con
    `<!ENTITY monto "1.00">`: el `TotalAmount` se lee vacío, no «1.00».

    Eso es peor que una caída. Un importe que desaparece no se nota: la factura
    sale sin ese dato y las reglas se quejan —o no— de algo que el documento sí
    dice. Y el documento no es recuperable leyéndolo de otra manera, porque el
    siguiente que lo abra puede expandir la entidad y leer un importe distinto
    del que hemos leído aquí: una factura que dice dos cosas según quién la
    abra no dice ninguna.

    Devuelve los nombres de los elementos afectados, sin repetir y en el orden
    del documento, para poder nombrarlos en la queja.
    """
    if raiz is None:
        return []
    afectados: list[str] = []
    for nodo in raiz.iter():
        if not isinstance(nodo, etree._Entity):
            continue
        padre = nodo.getparent()
        nombre = _partir_nombre(padre.tag)[1] if padre is not None else "(raíz)"
        if nombre not in afectados:
            afectados.append(nombre)
    return afectados


# Nombre anterior, cuando el parser era privado de este módulo. Se mantiene
# porque lo usan los tests de seguridad y no cuesta nada.
_parser = parser


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
    # Lo que el documento declara manda siempre. Cuando no declara nada hay
    # que suponer, y la suposición no es la misma para todos: un documento que
    # dice ser del CIUS de la solución pública **solo puede ser UBL 2.5**,
    # porque la SPFE no admite otra cosa y porque media docena de sus campos
    # —los que cuelgan de `CollectionInvoiceLine`: suplidos, minoraciones,
    # recargo de equivalencia, régimen de grupo— usan elementos que en UBL 2.1
    # no existen. Comprobado contra los dos esquemas.
    #
    # Suponer 2.1 ahí no era una imprecisión: mandaba a comprobar la factura
    # contra un esquema que la rechaza entera, y el informe habría acusado de
    # inventarse elementos a una factura correcta.
    if version:
        motivo = "Formato reconocido."
    elif perfil and MARCADOR_CIUS_ES in perfil:
        version = "2.5"
        motivo = (
            "Sin UBLVersionID, pero declara el CIUS de la solución pública, "
            "que solo existe sobre UBL 2.5."
        )
    else:
        version = "2.1"
        motivo = "Sin UBLVersionID; se asume UBL 2.1, que es lo habitual."
    return Deteccion(
        familia=UBL,
        version=version,
        tipo_documento="abono" if nombre == "CreditNote" else "factura",
        perfil=perfil,
        conforme_en16931=bool(perfil and perfil.startswith(MARCADORES_EN16931)),
        firmado=_tiene_firma(raiz),
        namespace=namespace,
        motivo=motivo,
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
        conforme_en16931=bool(perfil and perfil.startswith(MARCADORES_EN16931)),
        firmado=_tiene_firma(raiz),
        namespace=namespace,
        motivo="Formato reconocido."
        if perfil
        else "Sin perfil declarado: no dice a qué guía se ajusta.",
    )


# La marca de orden de bytes de UTF-8. La pone delante el Bloc de notas de
# Windows al «Guardar como UTF-8», y también Excel al exportar: no es un error
# de quien manda la factura, es lo que hace su editor.
#
# En XML da igual —el parser la reconoce y la salta— y en EDIFACT no: la tira
# empieza por UNA, UNB o UNH y con tres bytes delante deja de empezar por
# ninguna de las tres. El fichero se caía al otro lado —«no es XML válido y
# tampoco EDIFACT»— y no se comprobaba nada de nada.
#
# Solo la de UTF-8: un EDIFACT en UTF-16 vendría lleno de bytes cero y eso no
# es esto, es otro problema y se vería.
MARCA_DE_BYTES = b"\xef\xbb\xbf"


def sin_marca(datos: bytes) -> bytes:
    """Los bytes sin la marca de orden de UTF-8, si la traían."""
    return datos[len(MARCA_DE_BYTES):] if datos.startswith(MARCA_DE_BYTES) else datos


def _detectar_edifact(datos: bytes) -> Deteccion | None:
    """El EDIFACT de toda la vida: una tira de segmentos, no XML."""
    cabeza = sin_marca(datos).lstrip()[:3].upper()
    if cabeza not in (b"UNA", b"UNB", b"UNH"):
        return None
    re_unh, re_bgm = _regex_edifact(*_separadores(datos))
    encontrado = re_unh.search(datos)
    if encontrado is None:
        return Deteccion(
            familia=EDIFACT,
            motivo="Mensaje EDIFACT, pero sin cabecera UNH: no se ve de qué "
            "tipo es.",
        )
    tipo = encontrado.group(1).decode("latin-1").upper()
    if tipo != "INVOIC":
        return Deteccion(
            familia=EDIFACT,
            version=_version_edifact(encontrado.group(2)),
            motivo=f"Mensaje EDIFACT de tipo {tipo}, que no es una factura. "
            "El mensaje de factura es el INVOIC.",
        )
    return Deteccion(
        familia=EDIFACT,
        version=_version_edifact(encontrado.group(2)),
        tipo_documento=_TIPOS_EDIFACT.get(
            (re_bgm.search(datos) or _VACIO).group(1) or b"", None
        ),
        conforme_en16931=any(m in datos for m in _MARCADORES_EDIFACT),
        motivo="Formato reconocido.",
    )


def _detectar_edifact_xml(raiz: etree._Element, nombre: str) -> Deteccion:
    """El mismo EDIFACT escrito como XML, que es la forma de ISO 20625.

    Es la que publica la Comisión Europea en sus ejemplos de EN 16931, y
    hasta ahora salía por la puerta de «formato no reconocido»: el validador
    decía no saber qué era un fichero que es justamente uno de los cuatro
    formatos que admite la ley, y encima el de referencia.
    """
    perfil = _texto(raiz, "//S_FTX[D_4451='DOC']/C_C108/D_4440", {})
    codigo = _texto(raiz, "//S_BGM/C_C002/D_1001", {})
    directorio = _texto(raiz, "//S_UNH/C_S009/D_0054", {})
    familia_mensaje = (_texto(raiz, "//S_UNH/C_S009/D_0065", {}) or "").upper()
    if nombre != "M_INVOIC" and familia_mensaje != "INVOIC":
        return Deteccion(
            familia=EDIFACT,
            version=_version_edifact(
                (directorio or "").encode("latin-1")
            ),
            motivo=f"Mensaje EDIFACT en XML de tipo {familia_mensaje or nombre}, "
            "que no es una factura.",
        )
    return Deteccion(
        familia=EDIFACT,
        version=_version_edifact((directorio or "").encode("latin-1")),
        tipo_documento=_TIPOS_EDIFACT.get((codigo or "").encode("latin-1")),
        perfil=perfil,
        conforme_en16931=bool(perfil and perfil.startswith(MARCADORES_EN16931)),
        firmado=_tiene_firma(raiz),
        motivo="Formato reconocido."
        if perfil
        else "Sin perfil declarado: no dice a qué guía se ajusta.",
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
    if namespace is None and nombre.startswith("M_"):
        return _detectar_edifact_xml(raiz, nombre)

    return Deteccion(
        namespace=namespace,
        motivo=(
            f"XML válido, pero su elemento raíz «{nombre}» no corresponde a "
            "Facturae, UBL, CII ni EDIFACT."
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
