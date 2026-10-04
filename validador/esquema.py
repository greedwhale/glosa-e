"""Validación de forma contra los esquemas XSD oficiales.

Hay dos maneras de que rechacen una factura. Una es de **contenido**: el
documento está bien formado pero las cuentas no cuadran, y de eso se ocupan
`en16931` y `codigo_unico`. La otra es de **forma**: el documento no respeta el
esquema —falta un elemento, sobra otro, están en el orden equivocado, un
importe lleva una coma donde va un punto— y ahí el receptor ni siquiera llega a
mirar los números.

Este módulo cubre la segunda. La comprobación en sí la hace libxml2 a través de
lxml, que es fiable y no hay nada que reinventar. **El trabajo está en traducir
el resultado**, porque los mensajes de libxml2 son de este tenor:

    Element '{urn:oasis:...:2}Fecha': This element is not expected.
    Expected is ( {urn:oasis:...:2}Numero ).

Que en castellano llano quiere decir: «Fecha va antes de Numero y deberían
estar al revés». Y esa segunda frase es la que sirve para arreglar la factura.

Los esquemas no vienen dentro del repositorio: son de OASIS, de UN/CEFACT y del
Ministerio, pesan lo suyo y tienen sus propias licencias. Hay que descargarlos
y dejarlos en una carpeta; el `Catalogo` los busca por nombre, así que da igual
cómo queden repartidos al descomprimirlos. Si no están, no se comprueba la
forma y se dice, en vez de callar y aparentar que todo está bien.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from lxml import etree

from validador.formato import (
    CII,
    EDIFACT,
    FACTURAE,
    RESPUESTA,
    UBL,
    detectar,
    entidades_sin_resolver,
    parser,
)
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia, Informe

# Variable de entorno con la carpeta de esquemas, si no se quiere la de al lado.
VARIABLE_ENTORNO = "FACTURAE_ESQUEMAS"
CARPETA_POR_DEFECTO = "esquemas"

# Un documento roto de verdad puede dar cientos de incumplimientos, casi todos
# consecuencia del primero. Pasado este tope se corta y se dice cuántos faltan.
TOPE_INCIDENCIAS = 20


# --- Dónde están los esquemas ----------------------------------------------


# Las versiones de UBL que este validador sabe nombrar, **de la más vieja a la
# más nueva**. El orden es la parte importante: de él sale a qué esquema se
# puede recurrir cuando el que toca no está instalado, y la regla es que se
# puede subir pero nunca bajar.
#
# Por qué se puede subir. UBL no cambia de namespace entre versiones menores
# —`...:xsd:Invoice-2` es el mismo en la 2.0 y en la 2.5, comprobado— y lo que
# hace cada versión nueva es añadir elementos opcionales sin quitar ni mover
# los que ya había: entre la 2.1 y la 2.5 la secuencia de `Invoice` pasa de 53
# a 62 hijos, no desaparece ninguno y los 53 de antes siguen en el mismo orden.
# Medido también con documentos enteros: los cinco ejemplos UBL de `ejemplos/`
# pasan igual el esquema 2.1 y el 2.5.
#
# Por qué no se puede bajar, que es lo que esto viene a impedir. Un documento
# que use algo nuevo —`CollectionInvoiceLine`, sin ir más lejos, que es donde
# el CIUS español mete suplidos, minoraciones y recargo de equivalencia— es
# **válido** y el esquema viejo lo rechaza. Medido: una factura 2.5 con un
# `DefaultLanguageCode` pasa el esquema 2.5 y falla contra el 2.1. Si aquí se
# dejara caer a la versión de al lado, el informe se llenaría de XSD-ORDEN
# inventados y quien lo leyera se pondría a arreglar una factura correcta.
# Vale mil veces más decir que falta el esquema.
#
# **Y de la 2.0 no se sube.** Medido el 29-09-2026 con el XSD de `Invoice` de la
# 2.0 (una copia de `phax/ph-ubl`, porque docs.oasis-open.org no contesta desde
# donde se midió) contra el de la 2.1 y el de la 2.5: `ExtensionContent`, el
# hueco donde UBL deja meter lo que se quiera, era `xsd:any ##any
# processContents="skip" minOccurs="0"` en la 2.0 y desde la 2.1 es `##other`,
# `lax` y `minOccurs="1"`. Una factura 2.0 con un `ext:ExtensionContent` vacío,
# o con contenido sin namespace, es válida en la 2.0 y la rechazan la 2.1 y la
# 2.5 con `Missing child element(s)`: acusar de un fallo que el documento no
# tiene. Con contenido de otro namespace y nada raro dentro pasan igual, así que
# el caso es estrecho, pero la regla es «se sube solo si no puede fallar» y de
# la 2.0 no se puede asegurar. De la 2.1 en adelante sí: es lo medido arriba.
#
# **Lo mismo vale para `ApplicationResponse`**, medido aparte porque es otro
# documento con otra secuencia: de la 2.1, la 2.2, la 2.3 y la 2.4 a la 2.5 hay 0
# violaciones sobre todos los tipos alcanzables (38, 41, 45 y 45), y 400
# documentos generados desde cada esquema viejo pasan los 400 en el 2.5. Los XSD
# viejos son copias de `phax/ph-ubl` y no se han cotejado con OASIS; el de la 2.1
# es el CS1, no el OS.
_VERSIONES_UBL = ("2.0", "2.1", "2.2", "2.3", "2.4", "2.5")

# Las versiones que no se dejan subir: un documento que las declara se mide con
# su esquema o con ninguno. Ver arriba.
_NO_SUBEN = ("2.0",)

# La que se supone cuando no se puede saber. Es la de `formato.py` cuando el
# documento no trae `UBLVersionID`, y aquí sirve para lo mismo: no dejar sin
# comprobar un documento que solo tiene la versión mal escrita.
_UBL_POR_DEFECTO = "2.1"

_RE_VERSION_UBL = re.compile(r"^2\.\d+$")


def _versiones_ubl(declarada: str | None) -> tuple[str, ...]:
    """Qué esquemas de UBL valen para un documento, en orden de preferencia.

    El primero es siempre el de la versión que el documento declara, que es
    contra el que lo escribieron. Detrás van **solo las posteriores**, y ninguna
    si la declarada es de las que no se dejan subir (`_NO_SUBEN`).
    """
    declarada = (declarada or "").strip()
    if declarada in _NO_SUBEN:
        return (declarada,)
    if declarada in _VERSIONES_UBL:
        return _VERSIONES_UBL[_VERSIONES_UBL.index(declarada):]
    if _RE_VERSION_UBL.match(declarada):
        # Una versión de UBL que este validador no conoce todavía. No vale
        # ninguna de las de arriba —todas son anteriores— así que se nombra la
        # suya y, si no está, se dice cuál hay que instalar.
        return (declarada,)
    # Ni una versión ni nada que se le parezca. Se hace lo mismo que con un
    # documento sin `UBLVersionID`, que es lo que casi siempre es.
    return _VERSIONES_UBL[_VERSIONES_UBL.index(_UBL_POR_DEFECTO):]


def _nombres_esperados(deteccion) -> tuple[str, ...]:
    """Nombres de fichero del esquema que le toca a un documento."""
    if deteccion.familia == UBL:
        clase = "CreditNote" if deteccion.tipo_documento == "abono" else "Invoice"
        return tuple(
            f"UBL-{clase}-{version}.xsd"
            for version in _versiones_ubl(deteccion.version)
        )
    if deteccion.familia == RESPUESTA:
        # Las mismas versiones y la misma regla que las facturas: el namespace
        # es `ApplicationResponse-2` en todas. Ver `_VERSIONES_UBL`.
        return tuple(
            f"UBL-ApplicationResponse-{version}.xsd"
            for version in _versiones_ubl(deteccion.version)
        )
    if deteccion.familia == CII:
        return (
            "CrossIndustryInvoice_100pD16B.xsd",
            "CrossIndustryInvoice_100pD22B.xsd",
        )
    if deteccion.familia == FACTURAE:
        version = (deteccion.version or "3.2.2").replace(".", "_")
        return (f"Facturaev{version}.xsd",)
    return ()


# Lo que un esquema oficial puede pedir por dirección web, y con qué se le
# contesta desde aquí.
#
# **El agujero que esto tapa.** Los cinco XSD de Facturae importan la firma
# XMLDSig por URL, en su tercera línea:
#
#     <xs:import namespace="http://www.w3.org/2000/09/xmldsig#"
#       schemaLocation="http://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd"/>
#
# El parser de `formato.py` lleva `no_network=True` desde el principio y un
# comentario que dice que un fichero de fuera no debe poder hacer peticiones
# salientes. Eso vale para **leer el documento**; compilar un esquema es otra
# cosa, y esa la resuelve libxml2 por su cuenta, saltándose el parser. Así que
# comprobar la forma de una factura Facturae —el formato nacional— se bajaba
# un fichero de w3.org cada vez, sin decirlo en ninguna parte.
#
# No se veía porque funcionaba. Se ve en el navegador, donde no hay red: allí
# el esquema no compila y sale «el esquema está ahí pero no se puede leer,
# suele ser una descarga a medias», que manda a rebajar un fichero que está
# perfectamente. Y se ve con un proxy muerto, que es como se ha confirmado.
#
# UBL trae en su paquete una copia del mismo esquema —mismo `targetNamespace`,
# mismo `Signature`— y con eso se resuelve, sin bajar nada nuevo. Si alguien
# deja el fichero del W3C con su nombre, también vale.
#
# La copia de UBL 2.5 va delante de la de 2.1 **y no da igual el orden**: quien
# instale solo UBL 2.5 y Facturae no tiene la de 2.1 en el disco, y sin
# nombrarla aquí se quedaba sin comprobar la forma de todas las facturas del
# formato nacional. Las dos declaran el mismo `targetNamespace`
# —`http://www.w3.org/2000/09/xmldsig#`, comprobado— aunque los bytes difieran.
_COPIAS_LOCALES = {
    "xmldsig-core-schema.xsd": (
        "xmldsig-core-schema.xsd",
        "UBL-xmldsig-core-schema-2.5.xsd",
        "UBL-xmldsig-core-schema-2.1.xsd",
    ),
}

_REMOTO = ("http://", "https://", "ftp://")


class _SinRed(etree.Resolver):
    """Resuelve con lo que hay instalado, y no sale a buscar nada.

    Las direcciones locales se dejan pasar —las resuelve libxml2 como
    siempre— y las remotas se contestan con la copia que haya en la carpeta.
    Cuando no la hay, se contesta con un documento vacío **a propósito**: el
    esquema no compilará y se dirá, que es mejor que ir a buscarlo. Devolver
    `None` aquí sería justo lo que se viene a quitar, porque entonces libxml2
    lo baja él.
    """

    def __init__(self, indice: dict[str, Path]) -> None:
        self.indice = indice
        # Lo que se ha pedido de fuera y no estaba, para poder decirlo en vez
        # de dejar que se lea como una descarga a medias.
        self.no_estaban: list[str] = []

    def resolve(self, url, id_, context):
        if not str(url).lower().startswith(_REMOTO):
            return None
        nombre = str(url).rsplit("/", 1)[-1]
        for candidato in _COPIAS_LOCALES.get(nombre, (nombre,)):
            ruta = self.indice.get(candidato)
            if ruta is not None:
                return self.resolve_filename(str(ruta), context)
        self.no_estaban.append(str(url))
        return self.resolve_string(b"", context)


@dataclass
class Catalogo:
    """Los esquemas que hay instalados, si es que hay alguno.

    Busca por nombre de fichero en toda la carpeta, no por una ruta fija: los
    paquetes oficiales se descomprimen cada uno con su propio arbolito y no
    tiene sentido obligar a nadie a recolocarlos a mano.

    El recorrido del disco se hace **una sola vez** por catálogo. Antes se
    hacía uno por cada consulta: tres por factura —uno para saber si había
    esquemas y dos probando nombres— y el paquete de UBL 2.1 trae cientos de
    ficheros, así que un lote de trescientas facturas daba novecientas vueltas
    completas al árbol. El esquema compilado ya se guardaba; lo que faltaba era
    guardar también dónde estaba.

    La contrapartida es que un esquema añadido a la carpeta con el catálogo ya
    en marcha no se ve. Para un lote eso es lo que se quiere —que todos los
    ficheros se midan con la misma vara—; si hiciera falta, `recargar()`.
    """

    carpeta: Path
    # Cómo le llegan los esquemas a quien lee el informe, cuando no es una
    # carpeta suya: la página dice «que vienen con esta página». Vacío, el
    # aviso de que falta uno dice la carpeta, que en consola es lo que hace
    # falta para ponerlo. En la página era «/opt/factura-e/esquemas», el disco
    # virtual del navegador: una ruta que nadie puede abrir, en un sitio donde
    # no se puede añadir nada. Es lo mismo que hace `Almacen` con las anclas.
    procedencia: str = ""
    _compilados: dict[Path, etree.XMLSchema] = field(
        default_factory=dict, repr=False
    )

    def __post_init__(self) -> None:
        # `Catalogo("esquemas")` es lo natural de escribir desde fuera, y sin
        # esto no reventaba hasta la primera consulta, en mitad de un lote.
        if not isinstance(self.carpeta, Path):
            self.carpeta = Path(self.carpeta)

    _indice: dict[str, Path] | None = field(default=None, repr=False)
    _rotos: dict[Path, str] = field(default_factory=dict, repr=False)

    @classmethod
    def por_defecto(
        cls, carpeta: str | Path | None = None, procedencia: str = ""
    ) -> Catalogo:
        if carpeta is None:
            carpeta = os.environ.get(VARIABLE_ENTORNO) or CARPETA_POR_DEFECTO
        return cls(Path(carpeta), procedencia)

    @property
    def indice(self) -> dict[str, Path]:
        """Nombre de fichero -> dónde está, recorriendo el disco una vez.

        Se queda con la primera aparición de cada nombre, que es lo mismo que
        devolvía el `rglob` por nombre de antes.
        """
        if self._indice is None:
            encontrados: dict[str, Path] = {}
            if self.carpeta.is_dir():
                for ruta in self.carpeta.rglob("*.xsd"):
                    encontrados.setdefault(ruta.name, ruta)
            self._indice = encontrados
        return self._indice

    def recargar(self) -> None:
        """Vuelve a mirar el disco. Para cuando se instalan esquemas en caliente."""
        self._indice = None
        self._compilados.clear()
        self._rotos.clear()

    @property
    def vacio(self) -> bool:
        """No hay esquemas instalados, ni siquiera la carpeta."""
        return not self.indice

    def ruta_para(self, deteccion) -> Path | None:
        for nombre in _nombres_esperados(deteccion):
            encontrado = self.indice.get(nombre)
            if encontrado is not None:
                return encontrado
        return None

    def esquema_para(self, deteccion) -> etree.XMLSchema | None:
        """El esquema compilado, cacheado: compilar UBL 2.1 no es barato.

        Sin cache, validar un lote de trescientos ficheros recompilaria el
        mismo esquema trescientas veces.

        Si el fichero está pero no se puede compilar —una descarga a medias, o
        algo que no es un esquema con el nombre de uno— devuelve None y se
        guarda el motivo. Antes la excepción salía de aquí y **se llevaba por
        delante el lote entero**: un fichero mal descargado en la carpeta de
        esquemas y trescientas facturas sin validar, con un traceback en vez de
        una frase.
        """
        ruta = self.ruta_para(deteccion)
        if ruta is None or ruta in self._rotos:
            return None
        if ruta not in self._compilados:
            # El parser lleva el resolvedor pegado porque las importaciones de
            # un esquema las resuelve libxml2 con los del parser que leyó el
            # documento. Uno por compilación: guarda qué se ha pedido de fuera.
            lector = parser()
            sin_red = _SinRed(self.indice)
            lector.resolvers.add(sin_red)
            try:
                self._compilados[ruta] = etree.XMLSchema(
                    etree.parse(str(ruta), parser=lector)
                )
            except (etree.LxmlError, OSError) as error:
                self._rotos[ruta] = _por_que(sin_red, error)
                return None
        return self._compilados[ruta]

    def por_que_no_compila(self, deteccion) -> tuple[Path, str] | None:
        """El esquema que le toca existe pero está roto, y por qué."""
        ruta = self.ruta_para(deteccion)
        if ruta is None or ruta not in self._rotos:
            return None
        return (ruta, self._rotos[ruta])


def se_puede_comprobar(deteccion, catalogo: Catalogo | None = None) -> bool:
    """¿Hay un esquema instalado, y que compile, con el que mirar este documento?

    Lo pregunta quien orquesta para los documentos **cuya única comprobación es
    la forma**, como una respuesta: a una factura sin esquema todavía se le
    miden las cuentas, y decir que no se ha podido comprobar sería mentir por el
    otro lado. A una respuesta sin esquema no se le mide nada, y darla por
    correcta es dar por bueno lo que nadie ha abierto.
    """
    catalogo = catalogo or Catalogo.por_defecto()
    return not catalogo.vacio and catalogo.esquema_para(deteccion) is not None


def _como_se_llama(deteccion) -> str:
    """Qué fichero hay que instalar, dicho para que se pueda ir a buscarlo.

    Con UBL la lista de candidatos puede tener seis nombres, y enumerarlos
    todos convertía el aviso en un ladrillo del que no se saca qué hacer. El
    que hay que instalar es **el primero** —el de la versión que el documento
    declara—; los demás son a lo que se puede recurrir, no lo que se pide.
    """
    nombres = _nombres_esperados(deteccion)
    if not nombres:
        return "No se sabe cómo se llama el que le toca"
    if len(nombres) == 1:
        return f"El que le toca se llama {nombres[0]}"
    return (
        f"El que le toca se llama {nombres[0]} (o el de cualquier versión "
        f"posterior, hasta {nombres[-1]})"
    )


def _por_que(sin_red: _SinRed, error: Exception) -> str:
    """Por qué no ha compilado, diciendo la causa y no el síntoma.

    Si el esquema pedía un fichero de fuera que no está instalado, el error de
    libxml2 habla de una referencia que no resuelve, y el mensaje de siempre
    —«suele ser una descarga a medias, vuelve a bajarlo»— manda a rebajar un
    fichero que está perfectamente.
    """
    if not sin_red.no_estaban:
        return str(error)
    return (
        f"este esquema importa {sin_red.no_estaban[0]} por dirección web y no "
        "hay ninguna copia instalada. El validador no sale a la red a "
        "buscarla: instala el paquete de esquemas que la trae (el de UBL 2.1 "
        "la incluye) o deja el fichero en la carpeta de esquemas. "
        f"({error})"
    )


# --- Traducción de los mensajes de libxml2 ---------------------------------

_RE_CABECERA = re.compile(
    r"^Element '(?P<elemento>[^']+)'"
    r"(?:, attribute '(?P<atributo>[^']+)')?: (?P<resto>.*)$"
)
_RE_ESPERADOS = r"(?: Expected is (?:one of )?\((?P<esperados>[^)]*)\)\.)?"

_RE_NO_ESPERADO = re.compile(r"^This element is not expected\." + _RE_ESPERADOS)
_RE_FALTA_HIJO = re.compile(r"^Missing child element\(s\)\." + _RE_ESPERADOS)
_RE_ENUMERACION = re.compile(
    r"^\[facet 'enumeration'\] The value '(?P<valor>.*)' is not an element "
    r"of the set \{(?P<conjunto>.*)\}\.$"
)
_RE_TIPO = re.compile(
    r"^'(?P<valor>.*)' is not a valid value of the atomic type "
    r"'(?P<tipo>[^']+)'\.$"
)
# El mismo error cuando el tipo no tiene nombre. libxml2 lo dice así con los
# tipos de UBL que **extienden** un primitivo: los importes, desde la 2.1, y
# también las fechas y las horas en la 2.5. El valor se juzga contra un tipo
# anónimo, sin nombre que dar. Es donde cae, sobre el esquema de verdad, el
# fallo más corriente de una factura hecha a mano, una coma decimal (`1.234,56`):
# sin esto salía `XSD-OTRO`, «esta queja no se ha sabido traducir», con la frase
# en inglés. Medido el 29-09-2026 con `PayableAmount` en la 2.1 y en la 2.5, e
# `IssueDate` en la 2.5, que es la versión que pide la solución pública.
_RE_TIPO_LOCAL = re.compile(
    r"^'(?P<valor>.*)' is not a valid value of the local atomic type\.$"
)
_RE_MAXIMO = re.compile(
    r"^\[facet 'maxLength'\] The value has a length of '(?P<largo>\d+)'; "
    r"this exceeds the allowed maximum length of '(?P<tope>\d+)'\.$"
)
_RE_MINIMO = re.compile(
    r"^\[facet 'minLength'\] The value has a length of '(?P<largo>\d+)'; "
    r"this underruns the allowed minimum length of '(?P<tope>\d+)'\.$"
)
_RE_PATRON = re.compile(
    r"^\[facet 'pattern'\] The value '(?P<valor>.*)' is not accepted by "
    r"the pattern '(?P<patron>.*)'\.$"
)
_RE_ATRIBUTO_FALTA = re.compile(
    r"^The attribute '(?P<atributo>[^']+)' is required but missing\.$"
)
_RE_ATRIBUTO_SOBRA = re.compile(
    r"^The attribute '(?P<atributo>[^']+)' is not allowed\.$"
)
_RE_RAIZ = re.compile(r"^No matching global declaration available")
_RE_TEXTO_SUELTO = re.compile(r"^Character content other than whitespace")

_RE_NAMESPACE = re.compile(r"\{[^}]*\}")

# Cómo se escribe cada tipo, para no dejar a nadie con «xs:date» y una duda.
# Una fecha que ya viene con la forma correcta. Si el esquema la rechaza aun
# asi, el problema no es la forma: es que ese dia no existe.
_RE_FECHA_ESCRITA = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$")

_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

_PISTAS: dict[str, str] = {
    "xs:date": "Una fecha se escribe AAAA-MM-DD: 2026-03-02.",
    "xs:dateTime": "Se escribe AAAA-MM-DDThh:mm:ss: 2026-03-02T14:30:00.",
    "xs:decimal": (
        "Un importe lleva punto decimal, sin símbolo de moneda ni separador "
        "de miles: 1234.56, no 1.234,56 EUR."
    ),
    "xs:integer": "Tiene que ser un número entero, sin decimales.",
    "xs:boolean": "Solo admite true o false.",
    "xs:anyURI": "Tiene que ser una dirección, del estilo https://...",
    "xs:time": "Una hora se escribe hh:mm:ss: 14:30:00.",
}

# Los nombres de UBL dicen de qué tipo son, y aquí hace falta porque el mensaje
# de `_RE_TIPO_LOCAL` no lo dice. Medido el 29-09-2026 sobre los 873 elementos
# `cbc:` de UBL 2.1 y los 1.202 de UBL 2.5, resolviendo cada uno hasta su tipo
# primitivo: todo lo que acaba en `Date` es `xsd:date`, en `Time` es `xsd:time`,
# y todo lo decimal —196 de 873 y 260 de 1.202— acaba en uno de los sufijos de
# abajo. Una sola excepción, `TimeAmount`, que es un texto y no puede dar este
# error. `test_ubl_de_verdad.py` repite la medida con los esquemas que viajan en
# `web/paquete.zip`, así que una versión que cambie un tipo lo dice ahí y no en
# un informe.
#
# Solo los sufijos que tienen elementos detrás. Había `Factor` y una rama para
# `DateTime`, puestos por si acaso: ningún elemento `cbc:` acaba así ni en la
# 2.1 ni en la 2.5, contado, y nada los probaba. Si una versión los trae, la
# prueba de arriba se pone en rojo y dice cuál.
_SUFIJOS_DECIMALES = re.compile(r"(Amount|Quantity|Measure|Percent|Rate|Numeric)$")


def _tipo_por_nombre(elemento: str) -> str | None:
    """El tipo de un elemento `cbc:` de UBL, deducido de cómo acaba su nombre."""
    if elemento.endswith("Date"):
        return "xs:date"
    if elemento.endswith("Time"):
        return "xs:time"
    if _SUFIJOS_DECIMALES.search(elemento):
        return "xs:decimal"
    return None


def _pista(tipo: str, valor: str) -> str:
    """La ayuda que acompaña a un valor que el esquema rechaza.

    Para casi todos los tipos basta con recordar la forma. Con las fechas no:
    «2012-02-31» **ya está escrita AAAA-MM-DD**, y contestarle «una fecha se
    escribe AAAA-MM-DD» es no haber mirado el valor. Quien lee eso comprueba
    el formato, lo ve bien, y no encuentra el fallo.

    Lo que pasa es que el 31 de febrero no existe, y eso es lo que hay que
    decir. La pista era un literal fijo por tipo y no dependía del valor
    concreto; ahora, en las fechas, sí.
    """
    if tipo in ("xs:date", "xs:dateTime") and (
        m := _RE_FECHA_ESCRITA.match(valor.strip())
    ):
        anio, mes, dia = (int(g) for g in m.groups())
        if not 1 <= mes <= 12:
            return f"No existe el mes {mes:02d}: los meses van del 01 al 12."
        try:
            date(anio, mes, dia)
        except ValueError:
            ultimo = _ultimo_dia(anio, mes)
            return (
                f"La forma está bien, pero ese día no existe: "
                f"{_MESES[mes - 1]} de {anio} tiene {ultimo} días."
            )
    return _PISTAS.get(tipo, f"El esquema espera un {tipo}.")


def _ultimo_dia(anio: int, mes: int) -> int:
    """Cuántos días tiene un mes, sin traerse el módulo `calendar` entero."""
    if mes == 12:
        return 31
    return (date(anio, mes + 1, 1) - timedelta(days=1)).day


def _limpiar(texto: str | None) -> str:
    """Quita los namespaces, que ocupan tres líneas y no dicen nada."""
    return _RE_NAMESPACE.sub("", texto or "").strip()


def _lista(crudo: str | None) -> list[str]:
    if not crudo:
        return []
    return [_limpiar(trozo) for trozo in crudo.split(",") if trozo.strip()]


def _enumerar(nombres: list[str]) -> str:
    if len(nombres) == 1:
        return f"«{nombres[0]}»"
    return ", ".join(f"«{n}»" for n in nombres[:-1]) + f" o «{nombres[-1]}»"


def _prefijos(arbol) -> dict[str, str]:
    """Todos los prefijos de namespace declarados en el documento.

    libxml2 escribe el `path` con los prefijos del propio fichero
    (`/*/cbc:IssueDate`), pero el evaluador de XPath no los conoce si no se le
    pasan y salta con «Undefined namespace prefix». Se recogen de todo el
    árbol, no solo de la raíz, porque un prefijo puede declararse en
    cualquier elemento.
    """
    mapa: dict[str, str] = {}
    for elemento in arbol.getroot().iter():
        if not isinstance(elemento.tag, str):
            continue
        for prefijo, uri in elemento.nsmap.items():
            if prefijo:
                mapa.setdefault(prefijo, uri)
    return mapa


def _elemento_en(arbol, entrada, nombre: str):
    """El elemento al que se refiere un error de libxml2, si se encuentra."""
    if arbol is None:
        return None
    if entrada.path:
        try:
            encontrados = arbol.xpath(entrada.path, namespaces=_prefijos(arbol))
        except etree.XPathError:
            encontrados = []
        if encontrados:
            return encontrados[0]
    # Último recurso: por número de línea y nombre. No sirve en un XML escrito
    # todo en una línea, que es justo como los generan muchos programas, así
    # que es la reserva y no la vía principal.
    for elemento in arbol.getroot().iter():
        if not isinstance(elemento.tag, str):
            continue
        if elemento.sourceline == entrada.line and _limpiar(elemento.tag) == nombre:
            return elemento
    return None


def _por_que_no_encaja(arbol, entrada, encontrado: str, esperados: list[str]):
    """Distingue «está cambiado de sitio» de «sobra» o «falta».

    libxml2 dice lo mismo en los tres casos —«This element is not expected»—
    pero para quien tiene que arreglar la factura son problemas distintos. Se
    mira el documento: si lo que se esperaba aparece más adelante entre los
    hermanos, es que están al revés.
    """
    elemento = _elemento_en(arbol, entrada, encontrado)
    if elemento is None:
        return None
    padre = elemento.getparent()
    if padre is None:
        return None

    # Solo elementos: entre los hijos puede haber comentarios, y su `tag` no
    # es una cadena sino una función.
    hijos = [hijo for hijo in padre if isinstance(hijo.tag, str)]
    if elemento not in hijos:
        return None
    hermanos = [_limpiar(hijo.tag) for hijo in hijos]

    donde = hijos.index(elemento)

    # El repetido se mira antes que el desordenado. Con <ID/><ID/><Fecha/>, lo
    # que se espera (Fecha) también aparece más adelante, así que la
    # comprobación de orden diría que están cambiados de sitio cuando lo que
    # pasa es que uno sobra.
    #
    # Pero no basta con contar cuántos hay: hay elementos que la norma permite
    # repetir. Lo que hace que uno sobre es que **otro igual haya pasado ya**
    # por su sitio bueno; si el que se queja es el primero, el problema no es
    # que haya dos, es dónde están. Contando a secas, un
    # `AdditionalDocumentReference` —que UBL admite sin límite— colocado en el
    # lugar equivocado salía como «aparece 2 veces y el esquema no admite
    # tantas», y quien leyera eso borraría uno sin arreglar nada.
    if encontrado in hermanos[:donde]:
        return (
            f"«{encontrado}» aparece {hermanos.count(encontrado)} veces y el "
            "esquema no admite tantas."
        )

    posteriores = hermanos[donde + 1 :]
    desordenado = [nombre for nombre in esperados if nombre in posteriores]
    if desordenado:
        return (
            f"«{encontrado}» y {_enumerar(desordenado)} están cambiados de "
            f"sitio. En XML el orden de los elementos es parte del formato: "
            f"{_enumerar(desordenado)} tiene que ir antes."
        )
    return None


def traducir(entrada, arbol=None) -> Incidencia:
    """Convierte un error de libxml2 en una queja que se entienda."""
    casa = _RE_CABECERA.match(entrada.message or "")
    if casa is None:
        # Aquí no se ha reconocido ni la cabecera del mensaje, así que lo único
        # que se puede hacer es pasarlo tal cual. Pero al menos sin los
        # namespaces: dejarlos era devolver exactamente el ladrillo de libxml2
        # que este módulo existe para no enseñar.
        return Incidencia(
            "XSD-OTRO",
            ERROR,
            "El documento no cumple el esquema. Esta queja no se ha sabido "
            "traducir, así que va con las palabras del validador de esquemas, "
            f"que son las de libxml2 y están en inglés: «{_limpiar(entrada.message)}»",
            campo=f"Línea {entrada.line}",
        )

    elemento = _limpiar(casa["elemento"])
    resto = casa["resto"]
    donde = f"{elemento} (línea {entrada.line})"

    if (m := _RE_FALTA_HIJO.match(resto)) is not None:
        esperados = _lista(m["esperados"])
        return Incidencia(
            "XSD-FALTA",
            ERROR,
            f"A «{elemento}» le falta un elemento obligatorio dentro.",
            campo=donde,
            esperado=_enumerar(esperados) if esperados else "(el esquema no lo dice)",
            encontrado="(no está)",
        )

    if (m := _RE_NO_ESPERADO.match(resto)) is not None:
        esperados = _lista(m["esperados"])
        explicacion = _por_que_no_encaja(arbol, entrada, elemento, esperados)
        if explicacion is None:
            explicacion = (
                f"«{elemento}» no puede ir en este sitio. O sobra, o está "
                "cambiado de orden: en XML la secuencia de elementos es parte "
                "del formato."
            )
        return Incidencia(
            "XSD-ORDEN",
            ERROR,
            explicacion,
            campo=donde,
            esperado=_enumerar(esperados) if esperados else None,
            encontrado=elemento,
        )

    if (m := _RE_ENUMERACION.match(resto)) is not None:
        admitidos = [v.strip().strip("'") for v in m["conjunto"].split(",")]
        return Incidencia(
            "XSD-VALOR",
            ERROR,
            f"«{m['valor']}» no es un valor admitido para «{elemento}». El "
            "esquema solo acepta una lista cerrada.",
            campo=donde,
            esperado=", ".join(admitidos),
            encontrado=m["valor"],
        )

    if (m := _RE_TIPO.match(resto)) is not None:
        pista = _pista(m["tipo"], m["valor"])
        return Incidencia(
            "XSD-TIPO",
            ERROR,
            f"«{m['valor']}» no vale como contenido de «{elemento}». {pista}",
            campo=donde,
            encontrado=m["valor"],
        )

    if (m := _RE_TIPO_LOCAL.match(resto)) is not None:
        tipo = _tipo_por_nombre(elemento)
        pista = (
            _pista(tipo, m["valor"])
            if tipo is not None
            else "No tiene la forma que el esquema espera para este elemento."
        )
        return Incidencia(
            "XSD-TIPO",
            ERROR,
            f"«{m['valor']}» no vale como contenido de «{elemento}». {pista}",
            campo=donde,
            encontrado=m["valor"],
        )

    if (m := _RE_MAXIMO.match(resto)) is not None:
        return Incidencia(
            "XSD-LONGITUD",
            ERROR,
            f"El contenido de «{elemento}» es demasiado largo.",
            campo=donde,
            esperado=f"{m['tope']} caracteres como mucho",
            encontrado=f"{m['largo']} caracteres",
        )

    if (m := _RE_MINIMO.match(resto)) is not None:
        return Incidencia(
            "XSD-LONGITUD",
            ERROR,
            f"El contenido de «{elemento}» es demasiado corto.",
            campo=donde,
            esperado=f"{m['tope']} caracteres como mínimo",
            encontrado=f"{m['largo']} caracteres",
        )

    if (m := _RE_PATRON.match(resto)) is not None:
        return Incidencia(
            "XSD-PATRON",
            ERROR,
            f"«{m['valor']}» no tiene la forma que exige el esquema para "
            f"«{elemento}».",
            campo=donde,
            esperado=f"algo que encaje con {m['patron']}",
            encontrado=m["valor"],
        )

    if (m := _RE_ATRIBUTO_FALTA.match(resto)) is not None:
        return Incidencia(
            "XSD-ATRIBUTO",
            ERROR,
            f"A «{elemento}» le falta el atributo «{m['atributo']}», que es "
            "obligatorio.",
            campo=donde,
            esperado=f'{elemento} {m["atributo"]}="..."',
            encontrado="(sin el atributo)",
        )

    if (m := _RE_ATRIBUTO_SOBRA.match(resto)) is not None:
        return Incidencia(
            "XSD-ATRIBUTO",
            ERROR,
            f"«{elemento}» lleva un atributo «{m['atributo']}» que el esquema "
            "no admite.",
            campo=donde,
            encontrado=m["atributo"],
        )

    if _RE_RAIZ.match(resto):
        return Incidencia(
            "XSD-RAIZ",
            ERROR,
            f"El esquema no reconoce «{elemento}» como principio de un "
            "documento. O el fichero no es del formato que aparenta, o le "
            "falta la declaración de namespace.",
            campo=donde,
            encontrado=elemento,
        )

    if _RE_TEXTO_SUELTO.match(resto):
        return Incidencia(
            "XSD-TEXTO",
            ERROR,
            f"Dentro de «{elemento}» hay texto suelto. Ahí solo caben otros "
            "elementos; suele ser un trozo pegado por error.",
            campo=donde,
        )

    return Incidencia(
        "XSD-OTRO",
        ERROR,
        f"«{elemento}» no cumple el esquema. {_limpiar(resto)}",
        campo=donde,
    )


# --- Entrada pública -------------------------------------------------------


def _documento_a_validar(raiz, deteccion):
    """El árbol que hay que pasarle al esquema.

    Un Facturae firmado «por fuera» tiene la firma como raíz y la factura
    colgando dentro. El esquema de Facturae no sabe nada de eso, así que se le
    da el Facturae de dentro y no el envoltorio.
    """
    if deteccion.familia == FACTURAE and _limpiar(raiz.tag) == "Signature":
        internos = raiz.xpath("//*[local-name()='Facturae']")
        if internos:
            return etree.ElementTree(internos[0])
    return raiz.getroottree()


def reglas(raiz, deteccion, catalogo: Catalogo | None = None) -> list[Incidencia]:
    """Comprueba la forma de un documento ya parseado contra su esquema."""
    if raiz is None or not deteccion:
        return []
    catalogo = catalogo or Catalogo.por_defecto()
    if catalogo.vacio:
        # Sin esquemas instalados no hay nada que decir en cada fichero: lo
        # dice una vez quien orquesta, y no una vez por factura.
        return []

    if deteccion.familia == EDIFACT:
        # A un EDIFACT no le falta el esquema: es que no tiene. En su forma de
        # siempre no es XML, así que no hay XSD que aplicarle, y decir «falta
        # el esquema» manda a instalar un fichero que no existe. Lo que hace
        # ese papel es lo que la norma obliga a contar en el sobre, y eso sí
        # se comprueba: va con los códigos EDI-.
        #
        # Es una nota y no un aviso porque no hay nada que arreglar: es una
        # decisión tomada por quien lee —dar por buena la forma sin esquema—
        # y las decisiones tomadas por otro solo valen si se declaran.
        return [
            Incidencia(
                "XSD-NO-APLICA",
                NOTA,
                "La forma no se ha comprobado contra un esquema XSD, y no "
                "hace falta: EDIFACT no es XML y no tiene ninguno. En su "
                "lugar se han comprobado las cuentas que la propia norma "
                "obliga a llevar en el sobre.",
                campo="Esquema",
                encontrado=f"{deteccion.familia} {deteccion.version or ''}".strip(),
            )
        ]

    esquema = catalogo.esquema_para(deteccion)
    if esquema is None:
        roto = catalogo.por_que_no_compila(deteccion)
        if roto is not None:
            ruta, motivo = roto
            return [
                Incidencia(
                    "XSD-ESQUEMA-ROTO",
                    AVISO,
                    "No se ha comprobado la forma: el esquema que le toca a "
                    "este documento está ahí pero no se puede leer. Suele ser "
                    "una descarga a medias; vuelve a bajarlo.",
                    campo=str(ruta),
                    encontrado=_limpiar(motivo),
                )
            ]
        donde = (
            f"no está entre los esquemas {catalogo.procedencia}"
            if catalogo.procedencia
            else f"se busca dentro de {catalogo.carpeta}"
        )
        return [
            Incidencia(
                "XSD-SIN-ESQUEMA",
                AVISO,
                "No se ha comprobado la forma: falta el esquema de este "
                f"formato. {_como_se_llama(deteccion)}, y {donde}.",
                campo="Esquema",
                encontrado=f"{deteccion.familia} {deteccion.version or ''}".strip(),
            )
        ]

    if entidades_sin_resolver(raiz):
        # `XMLSchema.validate` revienta con «Internal error in XML Schema
        # validation» en cuanto el árbol trae una referencia a entidad sin
        # expandir, y esa caída se llevaba el informe entero por delante. No se
        # dice nada aquí a propósito: lo dice `XML-ENTIDADES`, que además
        # explica por qué, y decirlo dos veces con otras palabras es lo que
        # `_podar` existe para evitar.
        return []

    arbol = _documento_a_validar(raiz, deteccion)
    if esquema.validate(arbol):
        return []

    fallos = list(esquema.error_log)
    incidencias = [traducir(entrada, arbol) for entrada in fallos[:TOPE_INCIDENCIAS]]
    if len(fallos) > TOPE_INCIDENCIAS:
        incidencias.append(
            Incidencia(
                "XSD-DEMASIADOS",
                AVISO,
                f"Hay {len(fallos) - TOPE_INCIDENCIAS} incumplimientos más del "
                "esquema, sin listar. Casi siempre son consecuencia de los "
                "primeros: arregla esos y vuelve a pasarlo.",
                campo="Esquema",
                encontrado=f"{len(fallos)} en total",
            )
        )
    return incidencias


def validar(datos: bytes | str, catalogo: Catalogo | None = None) -> Informe:
    """Comprueba la forma de un documento contra su esquema oficial."""
    deteccion = detectar(datos)
    informe = Informe(deteccion=deteccion)
    if not deteccion:
        return informe
    if isinstance(datos, str):
        datos = datos.encode("utf-8")
    try:
        raiz = etree.fromstring(datos, parser=parser())
    except etree.XMLSyntaxError:
        return informe  # no es XML; EDIFACT no tiene esquema que valga
    informe.incidencias.extend(reglas(raiz, deteccion, catalogo))
    if deteccion.familia == RESPUESTA:
        # Lo mismo que `factura.validar`: sin esto, esta función, que es la de
        # solo la forma, daba por validada una respuesta con la forma rota y
        # ningún esquema instalado. Solo lo usan las pruebas, pero es pública.
        informe.mirado = se_puede_comprobar(deteccion, catalogo)
    return informe
