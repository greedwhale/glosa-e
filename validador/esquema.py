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
from pathlib import Path

from lxml import etree

from validador.formato import CII, FACTURAE, UBL, detectar, parser
from validador.incidencias import AVISO, ERROR, Incidencia, Informe

# Variable de entorno con la carpeta de esquemas, si no se quiere la de al lado.
VARIABLE_ENTORNO = "FACTURAE_ESQUEMAS"
CARPETA_POR_DEFECTO = "esquemas"

# Un documento roto de verdad puede dar cientos de incumplimientos, casi todos
# consecuencia del primero. Pasado este tope se corta y se dice cuántos faltan.
TOPE_INCIDENCIAS = 20


# --- Dónde están los esquemas ----------------------------------------------


def _nombres_esperados(deteccion) -> tuple[str, ...]:
    """Nombres de fichero del esquema que le toca a un documento."""
    if deteccion.familia == UBL:
        if deteccion.tipo_documento == "abono":
            return ("UBL-CreditNote-2.1.xsd", "UBL-CreditNote-2.0.xsd")
        return ("UBL-Invoice-2.1.xsd", "UBL-Invoice-2.0.xsd")
    if deteccion.familia == CII:
        return (
            "CrossIndustryInvoice_100pD16B.xsd",
            "CrossIndustryInvoice_100pD22B.xsd",
        )
    if deteccion.familia == FACTURAE:
        version = (deteccion.version or "3.2.2").replace(".", "_")
        return (f"Facturaev{version}.xsd",)
    return ()


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
    _compilados: dict[Path, etree.XMLSchema] = field(
        default_factory=dict, repr=False
    )
    _indice: dict[str, Path] | None = field(default=None, repr=False)
    _rotos: dict[Path, str] = field(default_factory=dict, repr=False)

    @classmethod
    def por_defecto(cls, carpeta: str | Path | None = None) -> Catalogo:
        if carpeta is None:
            carpeta = os.environ.get(VARIABLE_ENTORNO) or CARPETA_POR_DEFECTO
        return cls(Path(carpeta))

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
            try:
                self._compilados[ruta] = etree.XMLSchema(
                    etree.parse(str(ruta), parser=parser())
                )
            except (etree.LxmlError, OSError) as error:
                self._rotos[ruta] = str(error)
                return None
        return self._compilados[ruta]

    def por_que_no_compila(self, deteccion) -> tuple[Path, str] | None:
        """El esquema que le toca existe pero está roto, y por qué."""
        ruta = self.ruta_para(deteccion)
        if ruta is None or ruta not in self._rotos:
            return None
        return (ruta, self._rotos[ruta])


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
}


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
            f"El documento no cumple el esquema. {_limpiar(entrada.message)}",
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
        pista = _PISTAS.get(m["tipo"], f"El esquema espera un {m['tipo']}.")
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
        return [
            Incidencia(
                "XSD-SIN-ESQUEMA",
                AVISO,
                "No se ha comprobado la forma: falta el esquema de este "
                "formato. Los que le tocan se llaman "
                + " o ".join(_nombres_esperados(deteccion) or ("(ninguno)",))
                + f", y se buscan dentro de {catalogo.carpeta}.",
                campo="Esquema",
                encontrado=f"{deteccion.familia} {deteccion.version or ''}".strip(),
            )
        ]

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
    return informe
