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

from validador import cius_es

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
NS_UBL_RESPUESTA = "urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
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
# —`urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:1.0.0:extended`, que
# es el valor literal de la fila BT-24 del anexo I y está en
# `cius_es.ESPECIFICACION`—.
#
# Con un solo marcador, una factura del CIUS español salía «no declara
# conformidad con EN 16931» **por declarar la edición correcta**. No es un
# detalle: BR-01 avisa de eso, y avisar de lo que está bien es peor que
# callarse.
MARCADORES_EN16931 = ("urn:cen.eu:en16931:2017", "urn:cen.eu:en16931:2026")

# El de 2017 a secas, que es el que sigue viéndose en el 99 % de lo que llega
# y el que se enseña como ejemplo cuando falta.
MARCADOR_EN16931 = MARCADORES_EN16931[0]

# El CIUS del borrador de abril, que no llegó al BOE. La orden del 05-10-2026
# fija otro identificador (`cius_es.ESPECIFICACION`, de su fila BT-24), y el
# de abril se sigue reconociendo por este trozo para medirlo y poder decir que
# ya no vale: `SPFE-ESPECIFICACION` sale en ERROR. Sin él, una factura escrita
# con el borrador saldría sin una regla del anexo y sin que nada lo dijera.
MARCADOR_CIUS_ES = "urn:aeat.es:CIUS-ES-SPFE"

# El identificador de la orden se reconoce **entero**, y no por un trozo.
#
# Lo enseñó primero la AEAT, el 02-10-2026, en la captura de un XML de
# ejemplo que fue toda la respuesta del buzón a la consulta del 23-09-2026; y
# tres días después lo fijó la orden en su fila BT-24, letra a letra:
#
# | Dónde | Identificador |
# |---|---|
# | el borrador de abril | `urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0` |
# | el ejemplo del 02-10-2026 y la orden | `urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:1.0.0:extended` |
#
# `MARCADOR_CIUS_ES` no está en el segundo, y medido el 02-10-2026: una
# factura escrita como el ejemplo **no se reconocía** como de la solución
# pública. No se le aplicaba ni una regla del anexo y nada lo decía, así que
# una rectificativa que no dice qué rectifica salía «sin errores»; y sin
# `UBLVersionID` se suponía la 2.1, con lo que unas líneas de cobro, que solo
# existen en la 2.5, salían «cambiadas de sitio». El fallo de siempre: todo
# verde, y no es lo que crees haber probado.
#
# Un trozo ancho daría por de la solución pública cualquier cosa que nombre a
# la AEAT, y la orden da un valor, no un patrón. Lo que nombre a la AEAT sin
# ser ninguno de los dos no se calla tampoco: lo avisa `solucion_publica` (ver
# `NOMBRA_A_LA_AEAT`).
#
# Que `#conformant#` marque una extensión de la norma y `#compliant#` un CIUS
# es como lo usan otros: Factur-X declara su perfil EXTENDED con
# `#conformant#…:extended` y los demás con `#compliant#` (visto el 05-10-2026
# en `Profiles.java` de mustangproject), y XRechnung, su extensión con
# `#conformant#` (en su esquematrón). El texto de la EN 16931-1 que lo define
# no se ha podido leer. La orden declara su formato como extensión y no como
# CIUS; aquí no cambia nada, se mide igual.

# Lo que llevan delante los dos identificadores de la AEAT, el de la orden y
# el del borrador. No identifica la solución pública: sirve para no callarse ante
# un tercero que no sea ninguno de los dos, y para saber que lo que lo declara
# va en UBL 2.5.
NOMBRA_A_LA_AEAT = "urn:aeat.es:"


def declara_la_solucion_publica(perfil: str | None) -> bool:
    """Si el `CustomizationID` es de la solución pública: el de la orden o el de abril.

    El de la orden, por el valor entero. El del borrador de abril, por el
    trozo que nombra a su CIUS, con cualquier edición de la norma o versión
    del CIUS: se le mide igual, y `SPFE-ESPECIFICACION` dice que no es el que
    fija la orden.
    """
    return bool(perfil) and (
        perfil.strip() == cius_es.ESPECIFICACION or MARCADOR_CIUS_ES in perfil
    )


def _supone_ubl_25(perfil: str | None) -> bool:
    """Sin `UBLVersionID`, si lo que declara es de la AEAT.

    Basta con que nombre a la AEAT, y no hace falta que sea uno de los dos
    identificadores conocidos: la solución pública solo admite UBL 2.5, así
    que un tercero de la AEAT sin versión es mucho más probable que sea 2.5
    que 2.1. Suponer 2.1 era lo que hacía salir «cambiadas de sitio» unas
    líneas de cobro que en la 2.1 no existen.
    """
    return bool(perfil) and NOMBRA_A_LA_AEAT in perfil

# Familias
FACTURAE = "Facturae"
UBL = "UBL"
CII = "CII"
EDIFACT = "EDIFACT"

# El `ApplicationResponse` de UBL: una respuesta a otro documento (aceptada,
# rechazada, en trámite). **Es UBL pero no es una factura**, y por eso no lleva
# `UBL` como familia: hay nueve sitios que deciden por `familia == UBL` y todos
# suponen una factura, así que una respuesta con esa familia recibía, medido
# con una que valida contra su esquema, 16 errores que no le tocan: `XSD-RAIZ`,
# 13 reglas `BR-*` y dos `CU-*`. Con una familia propia, todo `if familia == X`
# y todo `SINTAXIS.get(familia)` contestan «no me toca», que es lo que hay que
# contestar; y lo único que hay que enseñar a mirarla es el esquema y la firma.
#
# El nombre es el del elemento raíz y no «respuesta a factura»: el mismo
# documento sirve para lo que Peppol llama respuesta de mensaje o de factura, y
# para el mensaje de anulación de la solución pública, cuyo texto no está
# publicado. Reconocerlo no es saber de cuál es.
RESPUESTA = "ApplicationResponse"

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
    tipo_documento: str | None = None  # "factura" o "abono"; ninguno en una respuesta
    # El código del tipo, tal cual lo trae el documento: el BT-3 (380, 381,
    # 384...) en UBL, CII y EDIFACT; en Facturae, el tipo y la clase ("FC OO"),
    # si todas las facturas del fichero llevan los mismos. "factura" no basta
    # para leer un lote: una rectificativa 384 es "factura" en UBL, y es justo
    # la que hay que separar. Va crudo; quien lo enseñe fuera lo filtra (ver
    # `factura._tipo_que_se_cuenta`).
    codigo_tipo: str | None = None
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
    parejas = {
        " ".join(
            (cabecera.xpath(f"string(./*[local-name()='{hijo}'])") or "").strip()
            for hijo in ("InvoiceDocumentType", "InvoiceClass")
        )
        for cabecera in raiz.xpath("//*[local-name()='InvoiceHeader']")
    }

    return Deteccion(
        familia=FACTURAE,
        version=version,
        tipo_documento=tipo,
        codigo_tipo=parejas.pop() if len(parejas) == 1 else None,
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
    # dice ser de la solución pública **solo puede ser UBL 2.5**,
    # porque la SPFE no admite otra cosa y porque media docena de sus campos
    # —los que cuelgan de `CollectionInvoiceLine`: suplidos, minoraciones,
    # recargo de equivalencia, régimen de grupo— usan elementos que en UBL 2.1
    # no existen. Comprobado contra los dos esquemas.
    #
    # Suponer 2.1 ahí no era una imprecisión: mandaba a comprobar la factura
    # contra un esquema que la rechaza entera, y el informe habría acusado de
    # inventarse elementos a una factura correcta.
    #
    # Y volvió a pasar el 02-10-2026, con el ejemplo de la propia AEAT: la
    # defensa colgaba de la cadena del CIUS de abril, y el ejemplo declara
    # otro identificador. Ahora cuelga de que nombre a la AEAT
    # (`_supone_ubl_25`), que es lo que de verdad dice «solución pública».
    if version:
        motivo = "Formato reconocido."
    elif _supone_ubl_25(perfil):
        version = "2.5"
        motivo = (
            "Sin UBLVersionID, pero declara una especificación de la AEAT, y "
            "la solución pública solo existe sobre UBL 2.5."
        )
    else:
        version = "2.1"
        motivo = "Sin UBLVersionID; se asume UBL 2.1, que es lo habitual."
    return Deteccion(
        familia=UBL,
        version=version,
        tipo_documento="abono" if nombre == "CreditNote" else "factura",
        codigo_tipo=_texto(raiz, "./cbc:InvoiceTypeCode | ./cbc:CreditNoteTypeCode", espacios),
        perfil=perfil,
        conforme_en16931=bool(perfil and perfil.startswith(MARCADORES_EN16931)),
        firmado=_tiene_firma(raiz),
        namespace=namespace,
        motivo=motivo,
    )


def _detectar_respuesta(raiz: etree._Element, namespace: str) -> Deteccion:
    """Un `ApplicationResponse`: se reconoce, y se dice hasta dónde.

    Sin `tipo_documento`, porque no es ni factura ni abono, y sin
    `conforme_en16931`, que no puede ser cierto de un documento al que esa
    norma no se aplica. Declarar el `CustomizationID` de una factura no la hace
    factura: sigue sin traer nada de lo que esa norma pide.

    La versión se deduce igual que en `_detectar_ubl`, a propósito: una sola
    regla para todo lo que es UBL. Sin `UBLVersionID`, la 2.1, salvo que
    declare una especificación de la AEAT, porque la solución pública solo
    existe sobre UBL 2.5. Que
    una respuesta de verdad lo declare es una suposición: la tabla del mensaje
    de anulación, en el anexo I de la orden publicada el 05-10-2026, no dice
    qué identificador de especificación lleva, ni si lleva alguno. Con el
    paquete de hoy da igual, porque de
    la 2.1 se sube a la 2.5 (ver `esquema._VERSIONES_UBL`); cambia la versión
    que dice el informe y el nombre del esquema que pide si falta.
    """
    espacios = {"cbc": NS_UBL_CBC}
    perfil = _texto(raiz, "./cbc:CustomizationID", espacios)
    version = _texto(raiz, "./cbc:UBLVersionID", espacios)
    if version:
        motivo = "Formato reconocido."
    elif _supone_ubl_25(perfil):
        version = "2.5"
        motivo = (
            "Sin UBLVersionID, pero declara una especificación de la AEAT, y "
            "la solución pública solo existe sobre UBL 2.5."
        )
    else:
        version = "2.1"
        motivo = "Sin UBLVersionID; se asume UBL 2.1, que es lo habitual."
    return Deteccion(
        familia=RESPUESTA,
        version=version,
        tipo_documento=None,
        perfil=perfil,
        conforme_en16931=False,
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
        codigo_tipo=codigo,
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
        codigo_tipo=((re_bgm.search(datos) or _VACIO).group(1) or b"").decode("latin-1") or None,
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
        codigo_tipo=codigo,
        perfil=perfil,
        conforme_en16931=bool(perfil and perfil.startswith(MARCADORES_EN16931)),
        firmado=_tiene_firma(raiz),
        motivo="Formato reconocido."
        if perfil
        else "Sin perfil declarado: no dice a qué guía se ajusta.",
    )


# --- Cuando el XML ni siquiera abre ----------------------------------------
#
# libxml2 explica bien por qué no abre, pero lo explica en inglés y con sus
# palabras —«Premature end of data in tag FileHeader», «xmlParseEntityRef: no
# name»—, y eso se iba entero al informe. Medido el 22-09-2026 sobre los 172
# ficheros ajenos de los tres corpus: **cero**. Sólo sale con un fichero roto,
# que es justo cuando quien lo recibe menos sabe qué mirar, y por eso llevaba
# tanto sin verse.
#
# La traducción se cuelga del **código** del error y no de su frase. El código
# es la enumeración de libxml2 y no cambia; la frase es texto y cambia entre
# versiones, y este proyecto fija la suya pero la del navegador es otra —lxml
# 6.1.2 aquí, 6.0.2 en Pyodide—. Del mensaje sólo se saca el nombre del
# elemento cuando lo trae, con una expresión por código: si algún día deja de
# casar, se pierde el nombre y queda la explicación, que es la degradación
# correcta.
#
# Los quince están medidos rompiendo un XML de veinticinco maneras distintas;
# lo que no salga de ahí cae en el remate, que pasa las palabras de libxml2
# diciendo que son suyas en vez de hacerlas pasar por nuestras.

_NOMBRE_EN_TAG = re.compile(r"in tag (\S+)")
_NOMBRE_EN_CIERRE = re.compile(r"mismatch: (\S+)")
_NOMBRE_EN_INICIO = re.compile(r"end of Start Tag (\S+)")
_NOMBRE_DE_ATRIBUTO = re.compile(r"Attribute (\S+) redefined")
_NOMBRE_DE_ENTIDAD = re.compile(r"Entity '([^']+)'")
_NOMBRE_DE_PREFIJO = re.compile(r"Namespace prefix (\S+)")
_NOMBRE_DE_CODIFICACION = re.compile(r"Unsupported encoding (\S+)")

# nombre del error en libxml2 -> (qué decir, de dónde sacar el nombre del
# elemento si el mensaje lo trae)
_NO_ABRE: dict[str, tuple[str, "re.Pattern[str] | None"]] = {
    "ERR_DOCUMENT_EMPTY": (
        "el fichero no empieza por el signo <, así que donde tenía que ir la primera "
        "etiqueta hay otra cosa. Un PDF, un ZIP, un correo o un texto suelto "
        "no son una factura en XML.", None),
    "ERR_TAG_NOT_FINISHED": (
        "una etiqueta{nombre} se abre y el fichero se acaba sin cerrarla. Suele "
        "ser una copia o una descarga a medias.", _NOMBRE_EN_TAG),
    # Este no salía aquí y sí en el navegador: el mismo fichero cortado a
    # medias da ERR_TAG_NOT_FINISHED con libxml2 6.1.2 y ERR_LTSLASH_REQUIRED
    # con el 6.0.2 que lleva Pyodide. Es la razón de que esto se cuelgue del
    # código y no de la frase, y de que haya remate: se vio soltándole los
    # veintidós ficheros rotos a la página, no leyendo el código.
    "ERR_LTSLASH_REQUIRED": (
        "se esperaba el cierre de una etiqueta (un </) y no está. Suele ser "
        "una copia o una descarga a medias.", None),
    "ERR_GT_REQUIRED": (
        "una etiqueta{nombre} se queda sin su signo de cierre, >.", _NOMBRE_EN_INICIO),
    "ERR_TAG_NAME_MISMATCH": (
        "una etiqueta{nombre} se cierra con un nombre distinto del que se "
        "abrió. En XML las dos tienen que decir lo mismo.", _NOMBRE_EN_CIERRE),
    "ERR_NAME_REQUIRED": (
        "después de un signo & o < tiene que venir un nombre, y aquí no lo "
        "hay. Si forman parte del texto de la factura, van escritos &amp; y "
        "&lt;.", None),
    "ERR_ATTRIBUTE_NOT_STARTED": (
        "el valor de un atributo va entre comillas y aquí no las lleva.", None),
    "ERR_ATTRIBUTE_REDEFINED": (
        "el mismo atributo{nombre} está puesto dos veces en la misma etiqueta.",
        _NOMBRE_DE_ATRIBUTO),
    "ERR_UNDECLARED_ENTITY": (
        "el documento usa una entidad{nombre} que no declara en ninguna parte.",
        _NOMBRE_DE_ENTIDAD),
    "ERR_DOCUMENT_END": (
        "hay contenido después de donde el documento tenía que acabar. Un XML "
        "lleva un solo elemento raíz y todo lo demás va dentro.", None),
    "NS_ERR_UNDEFINED_NAMESPACE": (
        "se usa un prefijo de espacio de nombres{nombre} que no se declara en "
        "ninguna parte.", _NOMBRE_DE_PREFIJO),
    "ERR_COMMENT_NOT_FINISHED": (
        "hay un comentario que se abre con <!-- y no se cierra con -->.",
        None),
    "ERR_CDATA_NOT_FINISHED": (
        "hay una sección CDATA que se abre y no se cierra con ]]>.", None),
    "ERR_INVALID_CHAR": (
        "hay un carácter que XML no admite: o el fichero no está en la "
        "codificación que declara, o lleva dentro un carácter de control.",
        None),
    "ERR_UNSUPPORTED_ENCODING": (
        "el prólogo declara una codificación{nombre} que no se reconoce.",
        _NOMBRE_DE_CODIFICACION),
    "ERR_VERSION_MISSING": (
        "el prólogo <?xml …?> está mal escrito: le falta la versión.", None),
}


# Los nombres se traducen a los números de esta versión de libxml2 una sola
# vez, y preguntando por el **atributo público** de `ErrorTypes`. La tentación
# era `ErrorTypes._names`, que da el camino inverso en una línea, pero empieza
# por guión bajo: aquí corre lxml 6.1.2 y en el navegador 6.0.2, y de lo
# privado no hay nada que garantice que siga estando. Un nombre que esta
# versión no conozca se cae de la tabla y su error acaba en el remate, que es
# lo que tiene que pasar.
_POR_CODIGO = {
    codigo: dicho
    for nombre, dicho in _NO_ABRE.items()
    if (codigo := getattr(etree.ErrorTypes, nombre, None)) is not None
}


def por_que_no_abre(error: etree.XMLSyntaxError) -> str:
    """Por qué no abre este XML, dicho en castellano y con dónde mirar."""
    donde = ""
    if error.lineno:
        donde = f" Línea {error.lineno}"
        # La columna la cuenta libxml2 desde 1 y `offset` desde 0; sin sumar
        # uno, el informe manda un carácter antes de donde está la cosa.
        if error.offset is not None:
            donde += f", columna {error.offset + 1}"
        donde += "."
    if error.code not in _POR_CODIGO:
        # No se inventa una traducción de lo que no se ha medido: se pasan las
        # palabras de libxml2 **diciendo que son suyas**, que es distinto de
        # colarlas como si fueran las de este validador.
        return f"el analizador de XML lo describe así: \"{error.msg}\".{donde}"
    plantilla, saca_nombre = _POR_CODIGO[error.code]
    cual = ""
    if saca_nombre is not None and (casa := saca_nombre.search(error.msg or "")):
        # El \S+ de la expresión se lleva por delante la coma con la que
        # libxml2 separa el nombre de la posición —«Unsupported encoding
        # PEPE-9, line 1»—, y sin quitarla el informe dice «PEPE-9,».
        if apodo := casa[1].strip(" ,.:;"):
            cual = f" \"{apodo}\""
    return plantilla.format(nombre=cual) + donde


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
            motivo="No es XML válido y tampoco EDIFACT: "
            + por_que_no_abre(error)
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
    if namespace == NS_UBL_RESPUESTA and nombre == "ApplicationResponse":
        return _detectar_respuesta(raiz, namespace)
    if namespace == NS_CII and nombre == "CrossIndustryInvoice":
        return _detectar_cii(raiz, namespace)
    if namespace is None and nombre.startswith("M_"):
        return _detectar_edifact_xml(raiz, nombre)

    # Con el nombre de uno de ellos y otro namespace, lo que está mal es el
    # namespace, y decir que la raíz no es de nada que se valide mandaría a
    # buscar a otro sitio.
    esperado = _NAMESPACE_DE_LA_RAIZ.get(nombre)
    if esperado is not None and namespace != esperado:
        return Deteccion(
            namespace=namespace,
            motivo=(
                f"XML válido, y su elemento raíz se llama \"{nombre}\", pero "
                + (f"su namespace es \"{namespace}\" y tendría que ser {esperado}"
                   if namespace else
                   f"no lleva namespace, y tendría que llevar {esperado}")
                + ". Sin ese namespace no es el documento de UBL o de CII que "
                "parece, y no se valida."
            ),
        )
    # La lista de lo que sí se valida, entera: decía «no corresponde a
    # Facturae, UBL, CII ni EDIFACT», y un `Order` de UBL es UBL. Lo que no se
    # valida de UBL no es el formato, es el documento.
    return Deteccion(
        namespace=namespace,
        motivo=(
            f"XML válido, pero su elemento raíz \"{nombre}\" no es de ningún "
            "documento que se valide aquí: facturas Facturae, UBL, CII o "
            "EDIFACT, y respuestas ApplicationResponse de UBL."
        ),
    )


# El namespace que tiene que llevar cada raíz que se reconoce por su nombre y su
# namespace a la vez. Facturae no está: se reconoce por el nombre, en cualquiera
# de sus versiones, y EDIFACT en XML no lleva.
_NAMESPACE_DE_LA_RAIZ = {
    "Invoice": NS_UBL_FACTURA,
    "CreditNote": NS_UBL_ABONO,
    "ApplicationResponse": NS_UBL_RESPUESTA,
    "CrossIndustryInvoice": NS_CII,
}


def detectar_archivo(ruta: str | Path) -> Deteccion:
    """Igual que `detectar`, leyendo de un fichero."""
    camino = Path(ruta)
    try:
        return detectar(camino.read_bytes())
    except FileNotFoundError:
        return Deteccion(motivo=f"No existe el fichero {camino}.")
    except OSError as error:
        return Deteccion(motivo=f"No se ha podido leer {camino}: {error}")
