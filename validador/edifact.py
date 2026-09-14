"""Lectura de facturas EDIFACT INVOIC, el cuarto formato que admite la ley.

El RD 238/2026 admite cuatro formatos y hasta ahora este validador entendía
tres. Con un EDIFACT contestaba «no se ha podido validar», que para quien
recibe la factura es lo mismo que no tener validador.

**Por qué hace falta un módulo entero y no un mapa más.** UBL, CII y Facturae
son XML: se parsean con lxml y se leen con XPath, y por eso les basta con una
`Sintaxis` en `sintaxis.py`. EDIFACT no es XML. Es una tira de segmentos
separados por apóstrofos donde el significado de cada dato depende de **su
posición**, no de su nombre:

    NAD+SU+++OTTO HARRASSOWITZ+KREUZBERGER RING 7C-D+WIESBADEN++65174+DE'

Ahí no pone en ninguna parte «nombre» ni «país». Pone que el cuarto elemento
del segmento NAD es el nombre y el noveno el país, y eso hay que saberlo de
antes. Ese saber —qué hay en cada posición de cada segmento— es el directorio
de EDIFACT, y es lo que este módulo escribe.

**Y una segunda dificultad, que es la de verdad.** EDIFACT tampoco marca los
grupos. En XML, que una línea de factura tenga su propio IVA se ve porque el
IVA está *dentro* de la línea. En EDIFACT todo va al mismo nivel, uno detrás
de otro, y qué cuelga de qué se deduce de en qué orden viene:

    LIN+1'  QTY+47:100'  MOA+203:18550'  TAX+7+VAT+++:::21+S'  LIN+2'...

El TAX de ahí es el de la línea 1, y se sabe solo porque viene después del LIN
y antes del siguiente. Reconstruir esa jerarquía es el trabajo de `_agrupar`.

**La decisión de diseño que ahorra el resto.** Una vez reconstruida la
jerarquía, se escribe como XML y a partir de ahí no hay nada especial: las
reglas de EN 16931 y la aritmética del IVA son las mismas de siempre, leídas
con XPath sobre un árbol. La forma del árbol es la de ISO 20625 —el propio
EDIFACT escrito como XML, que es como la Comisión Europea publica sus
ejemplos—, así que las dos maneras de traer un EDIFACT, la plana y la XML,
acaban en el mismo sitio y las reglas se escriben una sola vez.

Lo que este módulo **no** hace es inventarse el orden. Cuando un mensaje no es
un INVOIC, o las cuentas del sobre no cuadran, lo dice y sigue: un fichero mal
cerrado suele seguir siendo legible, y callarse el descuadre sería peor que
avisar.
"""

from __future__ import annotations

import re as _re
from dataclasses import dataclass

from lxml import etree

from validador.formato import EDIFACT as FAMILIA
from validador.formato import parser as _parser
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia

# --- Los caracteres de servicio --------------------------------------------

# ISO 9735 los deja elegir al emisor, que los declara en el segmento UNA. Casi
# todo el mundo usa estos, pero «casi» no es «todos»: hay ficheros con la coma
# como marca decimal, y leerlos con el punto convierte 1.234,56 en dos números.
COMPONENTE = ":"
ELEMENTO = "+"
DECIMAL = "."
ESCAPE = "?"
TERMINADOR = "'"


@dataclass(frozen=True)
class Servicio:
    """Los cinco caracteres con los que está escrito un intercambio."""

    componente: str = COMPONENTE
    elemento: str = ELEMENTO
    decimal: str = DECIMAL
    escape: str = ESCAPE
    terminador: str = TERMINADOR


POR_DEFECTO = Servicio()


@dataclass(frozen=True)
class Segmento:
    """Un segmento ya partido: la etiqueta y sus elementos.

    Cada elemento es una tupla de componentes, porque en EDIFACT un elemento
    puede ser simple («380») o compuesto («380:::JINV»). Tratar los dos igual
    —siempre una tupla— evita la mitad de los `if` que suele haber en estos
    lectores.
    """

    etiqueta: str
    elementos: tuple[tuple[str, ...], ...] = ()

    def dato(self, posicion: int, componente: int = 0) -> str:
        """El componente que haya en esa posición, o cadena vacía.

        Las posiciones van como en el directorio: 1 es el primer elemento
        **después** de la etiqueta.
        """
        if not 1 <= posicion <= len(self.elementos):
            return ""
        partes = self.elementos[posicion - 1]
        if componente >= len(partes):
            return ""
        return partes[componente]


# --- Partir la tira --------------------------------------------------------


def cuantos_de_servicio(datos: str) -> int:
    """Cuántos caracteres declara el UNA: seis, cinco, o cero si no hay UNA.

    La norma dice seis y en orden fijo: componente, elemento, decimal, escape,
    un hueco reservado, y terminador. Pero hay quien escribe cinco y se salta
    el hueco —«UNA:+.?\'» pegado al UNB— y esa variante no es rara: de los 64
    ficheros ajenos con los que se ha probado esto la usan 23, con 18 emisores
    distintos en el UNB.

    Leerla no es adivinar. Después del UNA solo puede venir el UNB, porque
    ISO 9735 no admite ninguna otra cosa ahí. Así que se prueban las dos
    longitudes y se queda la que deja un UNB detrás; si ninguna lo deja, se
    respeta lo que manda la norma y que el resto de las comprobaciones digan
    lo que pasa.

    Sin esto, un UNA de cinco hacía leer la «U» del UNB como terminador de
    segmento: el fichero se partía por cada U, no aparecía ningún UNH, y el
    validador contestaba «el fichero no trae ningún mensaje» sobre un fichero
    con veinticuatro facturas dentro.
    """
    limpio = datos.lstrip()
    if not limpio.upper().startswith("UNA") or len(limpio) < 8:
        return 0
    for cuantos in (6, 5):
        if limpio[3 + cuantos :].lstrip().upper().startswith("UNB"):
            return cuantos
    return 6


def servicio_de(datos: str) -> tuple[Servicio, int]:
    """Lee el UNA si lo hay. Devuelve los caracteres y por dónde seguir.

    El UNA es la única parte de un fichero EDIFACT que se lee sin saber ya los
    separadores, porque es la que los declara.
    """
    limpio = datos.lstrip()
    salto = len(datos) - len(limpio)
    cuantos = cuantos_de_servicio(datos)
    if not cuantos:
        return POR_DEFECTO, 0
    letras = limpio[3 : 3 + cuantos]
    return (
        Servicio(
            componente=letras[0],
            elemento=letras[1],
            decimal=letras[2],
            escape=letras[3],
            # El último es siempre el terminador, lo lleve el hueco o no.
            terminador=letras[-1],
        ),
        salto + 3 + cuantos,
    )


def partir(datos: str, servicio: Servicio) -> tuple[list[Segmento], str]:
    """Parte la tira en segmentos. Devuelve también lo que quede suelto.

    Lo que queda suelto es lo que había después del último terminador. En un
    fichero bien cerrado es cadena vacía o espacios; si trae texto, el fichero
    está cortado y hay que decirlo en vez de tragárselo.
    """
    segmentos: list[Segmento] = []
    elementos: list[tuple[str, ...]] = []
    componentes: list[str] = []
    letras: list[str] = []
    escapando = False
    # Dónde empieza el segmento que se está leyendo. Sirve para poder
    # devolver **entero** lo que quede sin cerrar: sin esto, de un
    # «DTM+137» cortado se devolvía «137», que es justo la mitad que no dice
    # dónde se ha roto el fichero.
    inicio = 0

    for indice, caracter in enumerate(datos):
        if escapando:
            # El carácter de escape hace literal al siguiente, y así es como un
            # apóstrofo puede aparecer dentro de un dato sin cerrar el
            # segmento. Sin esto, «d?'Histoire» parte la factura en dos.
            letras.append(caracter)
            escapando = False
            continue
        if caracter == servicio.escape:
            escapando = True
            continue
        if caracter == servicio.componente:
            componentes.append("".join(letras))
            letras = []
            continue
        if caracter == servicio.elemento:
            componentes.append("".join(letras))
            elementos.append(tuple(componentes))
            letras, componentes = [], []
            continue
        if caracter == servicio.terminador:
            componentes.append("".join(letras))
            elementos.append(tuple(componentes))
            if elementos and elementos[0]:
                segmentos.append(
                    Segmento(elementos[0][0].strip().upper(), tuple(elementos[1:]))
                )
            letras, componentes, elementos = [], [], []
            inicio = indice + 1
            continue
        if not elementos and not componentes and not letras and caracter.isspace():
            # Los saltos de línea entre segmentos son adorno: unos ficheros los
            # traen y otros vienen en una sola tira kilométrica. Sin saltárselos
            # aquí, la etiqueta del segmento siguiente saldría con un «\n»
            # delante y no la reconocería nadie.
            inicio = indice + 1
            continue
        letras.append(caracter)

    return segmentos, datos[inicio:].strip()


# --- El directorio: qué hay en cada posición -------------------------------

# Lo que cambia un montón de posiciones en un montón de nombres. Cada entrada
# es la lista de posiciones de un segmento, en orden; una posición es o el
# código de un dato simple, o un par (compuesto, componentes).
#
# Está escrito solo para los segmentos que INVOIC usa de verdad. Un directorio
# completo de EDIFACT son miles de páginas y aquí sobrarían: lo que no se
# nombra no se lee, y lo que no se lee no lo mira ninguna regla.
_Posicion = "str | tuple[str, tuple[str, ...]]"

DIRECTORIO: dict[str, tuple] = {
    # El sobre. No entra en el árbol, pero sus cuentas sí se comprueban.
    "UNB": (
        ("S001", ("0001", "0002", "0080", "0133")),
        ("S002", ("0004", "0007", "0008", "0042")),
        ("S003", ("0010", "0007", "0014", "0046")),
        ("S004", ("0017", "0019")),
        "0020",
        ("S005", ("0022", "0025")),
        "0026",
        "0029",
        "0031",
        "0032",
        "0035",
    ),
    "UNZ": ("0036", "0020"),
    "UNG": (
        "0038",
        ("S006", ("0040", "0007")),
        ("S007", ("0044", "0007")),
        ("S004", ("0017", "0019")),
        "0048",
        "0051",
        ("S008", ("0052", "0054", "0057", "0110")),
        "0058",
    ),
    "UNE": ("0060", "0048"),
    # La cabecera y el cierre del mensaje, que sí entran.
    "UNH": (
        "0062",
        ("S009", ("0065", "0052", "0054", "0051", "0057", "0110", "0113")),
        "0068",
        ("S010", ("0070", "0073")),
    ),
    "UNT": ("0074", "0062"),
    "UNS": ("0081",),
    # El cuerpo.
    "BGM": (
        ("C002", ("1001", "1131", "3055", "1000")),
        ("C106", ("1004", "1056", "1060")),
        "4343",
        "4447",
    ),
    "DTM": (("C507", ("2005", "2380", "2379")),),
    "PAI": (("C534", ("4439", "4431", "4461", "1131", "3055")),),
    "ALI": ("3239", "9213", "4183", "4183", "4183", "4183", "4183"),
    "IMD": (
        "7077",
        "7081",
        ("C273", ("7009", "1131", "3055", "7008", "7008", "3453")),
        "7383",
    ),
    "FTX": (
        "4451",
        "4453",
        ("C107", ("4441", "1131", "3055")),
        ("C108", ("4440", "4440", "4440", "4440", "4440")),
        "3453",
        "4447",
    ),
    "RFF": (("C506", ("1153", "1154", "1156", "4000", "1060")),),
    "NAD": (
        "3035",
        ("C082", ("3039", "1131", "3055")),
        ("C058", ("3124", "3124", "3124", "3124", "3124")),
        ("C080", ("3036", "3036", "3036", "3036", "3036")),
        ("C059", ("3042", "3042", "3042", "3042")),
        "3164",
        ("C819", ("3229", "1131", "3055", "3228")),
        "3251",
        "3207",
    ),
    "CTA": ("3139", ("C056", ("3413", "3412"))),
    "COM": (("C076", ("3148", "3155")),),
    "FII": (
        "3035",
        ("C078", ("3194", "3192", "3192", "6345", "6347")),
        ("C088", ("3433", "1131", "3055", "3434", "1131", "3055", "3432")),
        "3207",
    ),
    "CUX": (
        ("C504", ("6347", "6345", "6343", "6348")),
        ("C504", ("6347", "6345", "6343", "6348")),
        "5402",
        "6341",
    ),
    "PAT": (
        "4279",
        ("C110", ("2475", "2009", "2151", "4404")),
        ("C112", ("2152", "2151", "2151", "4404")),
    ),
    "PYT": (
        "4279",
        ("C110", ("2475", "2009", "2151", "4404")),
        ("C112", ("2152", "2151", "2151", "4404")),
    ),
    "PCD": (("C501", ("5245", "5482", "5249", "4405")),),
    "ALC": (
        "5463",
        ("C552", ("1230", "5189")),
        "4471",
        "1227",
        ("C214", ("7161", "1131", "3055", "7160", "7160")),
    ),
    "MOA": (("C516", ("5025", "5004", "6345", "6343", "4405")),),
    # Ojo con TAX: la cuarta posición es un dato simple (5286) y el compuesto
    # con el tipo impositivo es el quinto. Escribirlo de memoria y ponerlo en
    # el cuarto deja el porcentaje del IVA fuera de sitio en todas las
    # facturas; lo enseñaron los ficheros reales, donde «TAX+7+VAT+++:::21+S»
    # solo cuadra si C243 va en la quinta.
    "TAX": (
        "5283",
        ("C241", ("5153", "1131", "3055", "5152")),
        ("C533", ("5289", "1131", "3055")),
        "5286",
        ("C243", ("5279", "1131", "3055", "5278", "5273")),
        "5305",
        "3446",
        "1227",
    ),
    "LIN": (
        "1082",
        "1229",
        ("C212", ("7140", "7143", "1131", "3055")),
        ("C829", ("5495", "1082")),
        "1222",
        "7083",
    ),
    "PIA": (
        "4347",
        ("C212", ("7140", "7143", "1131", "3055")),
        ("C212", ("7140", "7143", "1131", "3055")),
        ("C212", ("7140", "7143", "1131", "3055")),
        ("C212", ("7140", "7143", "1131", "3055")),
        ("C212", ("7140", "7143", "1131", "3055")),
    ),
    "QTY": (("C186", ("6063", "6060", "6411")),),
    "MEA": (
        "6311",
        ("C502", ("6313", "6321", "6155", "6154")),
        ("C174", ("6411", "6314", "6162", "6152", "6432")),
    ),
    "PRI": (
        ("C509", ("5125", "5118", "5375", "5387", "5284", "6411")),
        "5213",
    ),
    "RTE": (("C128", ("5419", "5420", "5284", "6411")),),
    "CNT": (("C270", ("6069", "6066", "6411")),),
    "GIR": (
        "7297",
        ("C206", ("7402", "7405", "1131", "3055")),
    ),
    "EFI": (
        ("C077", ("1508", "7008", "3153", "1050", "1049")),
        ("C099", ("1050", "1049", "1054", "1052", "1053", "1051")),
        "1050",
        "1049",
    ),
    "LOC": (
        "3227",
        ("C517", ("3225", "1131", "3055", "3224")),
        ("C519", ("3223", "1131", "3055", "3222")),
        ("C553", ("3233", "1131", "3055", "3232")),
        "5479",
    ),
}

# Los datos que son números y no códigos. Importa por la marca decimal: si el
# intercambio la declara como coma, «1234,56» es mil doscientos treinta y
# cuatro con cincuenta y seis, y hay que escribirlo con punto para que el resto
# del validador lo lea como el número que es. En los códigos no se toca nada:
# un «102» de formato de fecha no es una cantidad.
NUMERICOS = frozenset(
    {"5004", "5482", "6060", "5118", "5278", "5286", "5420", "6314", "6066"}
)


# --- Los grupos: qué cuelga de qué -----------------------------------------


@dataclass(frozen=True)
class Grupo:
    """Un segmento que abre grupo, con lo que se lleva dentro.

    `sueltos` son los segmentos que van dentro del grupo sin abrir uno propio;
    `dentro` son los que sí lo abren.
    """

    sueltos: frozenset[str] = frozenset()
    dentro: frozenset[str] = frozenset()


# El mapa está escrito por **segmento que dispara**, no por número de grupo, y
# eso es a propósito. En EDIFACT los grupos se numeran (SG1, SG2, SG27…) y esa
# numeración cambia con la versión del directorio: en la D.14B que publica la
# Comisión el grupo de las líneas es el SG27, y en otras versiones no. Un mapa
# por números obligaría a tener una tabla por versión y a no saber leer las
# versiones que no estuvieran.
#
# Por dónde cuelga cada cosa, en cambio, no cambia: el IVA de una línea va
# detrás de su línea en todas las versiones, porque si no, no sería de esa
# línea. Escribiéndolo así, la misma tabla lee la D.96A que traen las facturas
# de verdad y la D.14B que publica la Comisión Europea.
#
# De dónde sale. La primera versión se dedujo de los nueve ejemplos de la
# Comisión, y le faltaba media docena de segmentos que esos nueve no usan. Eso
# no es un hueco inofensivo: un segmento que no esté en la tabla **no se queda
# fuera del grupo, lo cierra**. Un PAC —el embalaje de una línea— cerraba la
# línea, y el MOA que viniera detrás ya no era el importe de esa línea sino un
# total de la factura. Sin dar ningún error.
#
# Así que la tabla se contrastó contra la gramática D.96A de `bots-edi`, un
# proyecto de EDI que no tiene nada que ver con este, y es la unión de las dos:
# lo que enseñan los ejemplos de la D.14B y lo que dice esa gramática de la
# D.96A. Once grupos más de los que había.
GRUPOS: dict[str, Grupo] = {
    "AJT": Grupo(sueltos=frozenset({"FTX"})),
    "ALC": Grupo(
        sueltos=frozenset({"ALI", "DTM", "FTX"}),
        dentro=frozenset({"MOA", "PCD", "QTY", "RFF", "RTE", "TAX"}),
    ),
    "CTA": Grupo(sueltos=frozenset({"COM"})),
    "CUX": Grupo(sueltos=frozenset({"DTM"})),
    "DOC": Grupo(sueltos=frozenset({"DTM"})),
    "EFI": Grupo(sueltos=frozenset({"COM", "RFF"})),
    "INP": Grupo(sueltos=frozenset({"FTX"})),
    "LIN": Grupo(
        sueltos=frozenset(
            {
                "ALI", "DTM", "EQD", "FTX", "GIN", "GIR", "IMD", "MEA", "PCD",
                "PIA", "QTY", "QVR"
            }
        ),
        dentro=frozenset(
            {
                "ALC", "LOC", "MOA", "NAD", "PAC", "PAT", "PRI", "RCS", "RFF",
                "TAX", "TDT", "TOD"
            }
        ),
    ),
    "LOC": Grupo(sueltos=frozenset({"DTM", "QTY"})),
    "MOA": Grupo(sueltos=frozenset({"CUX", "RNG"}), dentro=frozenset({"RFF"})),
    "NAD": Grupo(
        sueltos=frozenset({"FII", "LOC"}),
        dentro=frozenset({"CTA", "DOC", "RFF"}),
    ),
    "PAC": Grupo(sueltos=frozenset({"MEA"}), dentro=frozenset({"PCI"})),
    "PAT": Grupo(sueltos=frozenset({"DTM", "FII", "MOA", "PAI", "PCD"})),
    "PCD": Grupo(sueltos=frozenset({"RNG"})),
    "PCI": Grupo(sueltos=frozenset({"DTM", "GIN", "RFF"})),
    "PRI": Grupo(sueltos=frozenset({"APR", "CUX", "DTM", "RNG"})),
    "PYT": Grupo(sueltos=frozenset({"DTM", "MOA", "PAI", "PCD"})),
    "QTY": Grupo(sueltos=frozenset({"RNG"})),
    "RCS": Grupo(sueltos=frozenset({"DTM", "FTX", "RFF"})),
    "RFF": Grupo(sueltos=frozenset({"DTM", "GIR"})),
    "RTE": Grupo(sueltos=frozenset({"RNG"})),
    "TAX": Grupo(sueltos=frozenset({"FTX", "LOC", "MOA"})),
    "TDT": Grupo(dentro=frozenset({"LOC", "RFF"})),
    "TOD": Grupo(sueltos=frozenset({"LOC"})),
}

# Segmentos de servicio: ni abren grupo ni se meten en ninguno. UNS es el que
# parte la factura en dos mitades —el detalle y los totales—, y por eso cierra
# todo lo que hubiera abierto.
SERVICIO = frozenset({"UNH", "UNT", "UNS", "UNB", "UNZ", "UNG", "UNE", "UNA"})


def _agrupar(segmentos: list[Segmento]) -> list:
    """Reconstruye la jerarquía a partir del orden.

    Se lleva una pila con los grupos abiertos. Para cada segmento se prueba, de
    dentro hacia fuera: ¿abre un grupo del que está abierto?, ¿va suelto dentro
    de él? Si no es ninguna de las dos, ese grupo se ha terminado, se cierra y
    se vuelve a preguntar un nivel más afuera.

    Que un segmento repetido cierre y vuelva a abrir su propio grupo sale solo:
    un LIN no está en la lista de lo que cabe dentro de un LIN, así que el
    segundo LIN cierra el primero y abre el suyo, que es justo lo que significa.
    """
    raiz: list = []
    pila: list[tuple[str, list]] = []

    for segmento in segmentos:
        etiqueta = segmento.etiqueta
        if etiqueta in SERVICIO:
            pila.clear()
            raiz.append(segmento)
            continue
        while True:
            if pila:
                nombre, contenido = pila[-1]
                marco = GRUPOS[nombre]
                if etiqueta in marco.dentro:
                    nuevo: list = [segmento]
                    contenido.append((etiqueta, nuevo))
                    pila.append((etiqueta, nuevo))
                    break
                if etiqueta in marco.sueltos:
                    contenido.append(segmento)
                    break
                pila.pop()
                continue
            if etiqueta in GRUPOS:
                nuevo = [segmento]
                raiz.append((etiqueta, nuevo))
                pila.append((etiqueta, nuevo))
                break
            raiz.append(segmento)
            break
    return raiz


# --- De segmentos a árbol --------------------------------------------------


def _escribir_segmento(padre, segmento: Segmento, servicio: Servicio) -> None:
    """Cuelga un segmento del árbol con los nombres del directorio."""
    nodo = etree.SubElement(padre, "S_" + segmento.etiqueta)
    plantilla = DIRECTORIO.get(segmento.etiqueta)
    if plantilla is None:
        # Un segmento que no está en el directorio se escribe por posiciones.
        # Es mejor que tirarlo: no lo va a leer ninguna regla, pero quien mire
        # el árbol para entender por qué falla algo lo verá.
        for indice, elemento in enumerate(segmento.elementos, 1):
            for parte in elemento:
                if parte:
                    etree.SubElement(nodo, "E_%02d" % indice).text = parte
        return

    for indice, posicion in enumerate(plantilla):
        if indice >= len(segmento.elementos):
            break
        valores = segmento.elementos[indice]
        if isinstance(posicion, str):
            if valores and valores[0]:
                etree.SubElement(nodo, "D_" + posicion).text = _valor(
                    posicion, valores[0], servicio
                )
            continue
        nombre, componentes = posicion
        if not any(valores):
            continue
        compuesto = etree.SubElement(nodo, "C_" + nombre)
        for sitio, valor in enumerate(valores):
            if not valor or sitio >= len(componentes):
                continue
            etree.SubElement(compuesto, "D_" + componentes[sitio]).text = _valor(
                componentes[sitio], valor, servicio
            )


def _valor(codigo: str, bruto: str, servicio: Servicio) -> str:
    if servicio.decimal != DECIMAL and codigo in NUMERICOS:
        return bruto.replace(servicio.decimal, DECIMAL)
    return bruto


def _escribir(padre, cosas: list, servicio: Servicio) -> None:
    for cosa in cosas:
        if isinstance(cosa, Segmento):
            _escribir_segmento(padre, cosa, servicio)
        else:
            etiqueta, contenido = cosa
            _escribir(etree.SubElement(padre, "G_" + etiqueta), contenido, servicio)


def a_arbol(segmentos: list[Segmento], servicio: Servicio = POR_DEFECTO):
    """Los segmentos de un mensaje, escritos como el XML de ISO 20625.

    El nombre de los grupos es el del segmento que los abre —`G_LIN`,
    `G_NAD`— y no su número de grupo. Los ejemplos de la Comisión Europea los
    numeran (`G_SG27`), y las dos formas conviven sin problema porque ninguna
    regla pregunta por el nombre del grupo: preguntan por lo que hay dentro.
    """
    raiz = etree.Element("M_INVOIC")
    _escribir(raiz, _agrupar(segmentos), servicio)
    return raiz


# --- Las cuentas del sobre -------------------------------------------------


def _mensajes(segmentos: list[Segmento]) -> list[tuple[int, int]]:
    """Los tramos (inicio, fin) de cada UNH…UNT, por posición."""
    tramos: list[tuple[int, int]] = []
    abierto: int | None = None
    for indice, segmento in enumerate(segmentos):
        if segmento.etiqueta == "UNH":
            abierto = indice
        elif segmento.etiqueta == "UNT" and abierto is not None:
            tramos.append((abierto, indice))
            abierto = None
    if abierto is not None:
        tramos.append((abierto, len(segmentos) - 1))
    return tramos


def _reglas_del_sobre(
    segmentos: list[Segmento], tramos: list[tuple[int, int]]
) -> list[Incidencia]:
    """Lo que ISO 9735 manda contar, contado.

    Son reglas de aritmética pura y por eso valen la pena: el emisor declara
    cuántos segmentos lleva el mensaje y cuántos mensajes lleva el sobre, y
    ese número es lo único que detecta un fichero que se ha cortado por el
    camino. Un EDIFACT truncado sigue pareciendo legible hasta que se cuenta.
    """
    incidencias: list[Incidencia] = []
    etiquetas = [s.etiqueta for s in segmentos]

    cabecera = next((s for s in segmentos if s.etiqueta == "UNH"), None)
    if cabecera is None:
        incidencias.append(
            Incidencia(
                "EDI-SIN-MENSAJE",
                ERROR,
                "El fichero no trae ningún segmento UNH, que es el que abre un "
                "mensaje. Sin él no hay nada que validar: lo que hay es un "
                "sobre vacío.",
                campo="UNH",
            )
        )
        return incidencias

    tipo = cabecera.dato(2, 0).upper()
    if tipo and tipo != "INVOIC":
        incidencias.append(
            Incidencia(
                "EDI-NO-ES-FACTURA",
                ERROR,
                f"El mensaje es de tipo «{tipo}», no INVOIC. EDIFACT sirve "
                "para muchas cosas —pedidos, albaranes, avisos de pago— y "
                "solo el INVOIC es una factura.",
                campo="UNH, tipo de mensaje",
                esperado="INVOIC",
                encontrado=tipo,
            )
        )

    if len(tramos) > 1:
        incidencias.append(
            Incidencia(
                "EDI-VARIOS-MENSAJES",
                AVISO,
                f"El intercambio trae {len(tramos)} mensajes. Se valida el "
                "primero. Los demás habría que separarlos en ficheros "
                "aparte para verlos.",
                campo="UNB…UNZ",
                encontrado=f"{len(tramos)} mensajes",
            )
        )

    for inicio, fin in tramos:
        cierre = segmentos[fin]
        if cierre.etiqueta != "UNT":
            incidencias.append(
                Incidencia(
                    "EDI-MENSAJE-SIN-CERRAR",
                    ERROR,
                    "El mensaje empieza con UNH pero no termina con UNT. O "
                    "está cortado, o le falta el cierre.",
                    campo="UNT",
                )
            )
            continue
        referencia = segmentos[inicio].dato(1, 0)
        if cierre.dato(2, 0) != referencia:
            incidencias.append(
                Incidencia(
                    "EDI-MENSAJE-DESCUADRADO",
                    ERROR,
                    "La referencia del cierre del mensaje no es la de su "
                    "cabecera. El UNT tiene que repetir la referencia del "
                    "UNH, y así se sabe que abren y cierran lo mismo.",
                    campo="UNT, referencia",
                    esperado=referencia,
                    encontrado=cierre.dato(2, 0) or "(vacío)",
                )
            )
        contados = fin - inicio + 1
        declarados = cierre.dato(1, 0)
        if declarados.isdigit() and int(declarados) != contados:
            incidencias.append(
                Incidencia(
                    "EDI-MENSAJE-DESCONTADO",
                    ERROR,
                    "El mensaje dice tener un número de segmentos distinto "
                    "del que tiene. Esa cuenta incluye el UNH y el UNT, y es "
                    "lo único que delata un fichero al que le falta un trozo.",
                    campo="UNT, número de segmentos",
                    esperado=declarados,
                    encontrado=str(contados),
                )
            )

    if "UNB" in etiquetas:
        sobre = segmentos[etiquetas.index("UNB")]
        cierres = [s for s in segmentos if s.etiqueta == "UNZ"]
        if not cierres:
            incidencias.append(
                Incidencia(
                    "EDI-SOBRE-SIN-CERRAR",
                    ERROR,
                    "El intercambio empieza con UNB y no termina con UNZ. Sin "
                    "el cierre no hay forma de saber si ha llegado entero.",
                    campo="UNZ",
                )
            )
        else:
            final = cierres[-1]
            referencia = sobre.dato(5, 0)
            if final.dato(2, 0) != referencia:
                incidencias.append(
                    Incidencia(
                        "EDI-SOBRE-DESCUADRADO",
                        ERROR,
                        "La referencia del cierre del intercambio no es la de "
                        "su cabecera. El UNZ tiene que repetir la referencia "
                        "del UNB.",
                        campo="UNZ, referencia",
                        esperado=referencia or "(vacío)",
                        encontrado=final.dato(2, 0) or "(vacío)",
                    )
                )
            declarados = final.dato(1, 0)
            # Cuando hay grupos funcionales (UNG…UNE), el UNZ cuenta grupos y
            # no mensajes. Contar mensajes contra ese número acusaría en falso
            # a un fichero correcto.
            grupos = etiquetas.count("UNG")
            esperados = grupos if grupos else len(tramos)
            if declarados.isdigit() and int(declarados) != esperados:
                incidencias.append(
                    Incidencia(
                        "EDI-SOBRE-DESCONTADO",
                        ERROR,
                        "El intercambio dice llevar un número de "
                        f"{'grupos' if grupos else 'mensajes'} distinto del "
                        "que lleva.",
                        campo="UNZ, número de mensajes",
                        esperado=declarados,
                        encontrado=str(esperados),
                    )
                )
    return incidencias



# --- Los totales escritos con otra guía ------------------------------------

# Los cualificadores de importe que usa la vinculación de EN 16931 con
# EDIFACT, comprobados uno a uno contra los nueve ejemplos de la Comisión
# haciendo la cuenta.
DE_LA_NORMA = {
    "9": "lo que hay que pagar",
    "79": "la suma de las líneas",
    "113": "los anticipos",
    "125": "la base de un tipo",
    "124": "la cuota de un tipo",
    "176": "el total de impuestos",
    "203": "el importe de una línea",
    "259": "el total de cargos",
    "260": "el total de descuentos",
    "388": "el total con impuestos",
    "389": "el total sin impuestos",
}

# Los que usan las guías de antes de la norma —EANCOM y las suyas propias de
# cada sector—, con lo que significan. No se leen: están aquí para poder
# **nombrarlos** en el aviso, que es lo único que hace falta para que quien
# recibe la queja sepa dónde mirar.
DE_OTRAS_GUIAS = {
    "77": "el importe de la factura",
    "86": "el total del mensaje",
    "128": "el total",
    "129": "el total de la factura",
    "131": "el total de cargos",
    "23": "un cargo",
    "8": "un descuento o un cargo",
}


def _y(cosas: list[str]) -> str:
    """«a», «a y b», «a, b y c». Con « y » a secas quedaba «a y b y c»."""
    if len(cosas) < 2:
        return "".join(cosas)
    return ", ".join(cosas[:-1]) + " y " + cosas[-1]


def totales_de_otra_guia(raiz, deteccion) -> list[Incidencia]:
    """Avisa cuando los totales están, pero escritos con otros códigos.

    En EDIFACT un importe no se distingue por dónde está sino por el código
    que lleva al lado: el 389 es el total sin impuestos y el 203 el importe de
    una línea, y los dos son un MOA. EN 16931 fijó qué código va en cada
    campo, pero las facturas EDIFACT llevan décadas circulando con las guías
    de cada sector, que eligieron otros.

    Sin este aviso, una factura que trae su total con el código 128 recibe un
    «falta el importe total con impuestos incluidos». Y es verdad que falta
    **donde la norma lo pone**, pero quien lo lee entiende que no está, y se
    va a buscar un dato que su factura ya trae. Decirlo entero cuesta una
    línea y cambia la tarea: no es añadir un importe, es moverlo de código.
    """
    if raiz is None or not deteccion or deteccion.familia != FAMILIA:
        return []
    faltan = [
        nombre
        for codigo, nombre in (
            ("389", "el total sin impuestos"),
            ("388", "el total con impuestos"),
            ("9", "lo que hay que pagar"),
        )
        if not raiz.xpath(f"./*/S_MOA/C_C516[D_5025='{codigo}']")
    ]
    if not faltan:
        return []
    ajenos = sorted(
        {
            (nodo.text or "").strip()
            for nodo in raiz.xpath("./*/S_MOA/C_C516/D_5025")
            if (nodo.text or "").strip() not in DE_LA_NORMA
        }
    )
    if not ajenos:
        return []
    conocidos = [c for c in ajenos if c in DE_OTRAS_GUIAS]
    if not conocidos:
        return []
    lista = ", ".join(f"{c} ({DE_OTRAS_GUIAS[c]})" for c in conocidos)
    return [
        Incidencia(
            "EDI-TOTALES-DE-OTRA-GUIA",
            AVISO,
            "Los totales de esta factura no llevan los códigos que usa "
            f"EN 16931, sino estos: {lista}. Por eso las reglas europeas dan "
            f"por ausente {_y(faltan)}: el importe está escrito, pero "
            "con un código que la norma no mira. Es lo normal en las facturas "
            "EDIFACT de antes de la norma, y para cumplirla hay que cambiar el "
            "código, no añadir el importe.",
            campo="MOA, cualificador de importe",
            esperado="389 sin impuestos, 388 con impuestos, 9 a pagar",
            encontrado=", ".join(conocidos),
        )
    ]


def iva_fuera_del_desglose(raiz, deteccion) -> list[Incidencia]:
    """Avisa cuando no hay desglose, pero sí un TAX donde la norma no lo busca.

    Es el mismo problema que el de los totales, con el impuesto. EN 16931 lee
    el desglose en el grupo 54: después del UNS y marcado como IVA. Hay
    facturas que lo escriben en la cabecera, en el grupo 6, que es el impuesto
    del documento entero; y hay facturas que lo escriben al final pero sin el
    tipo VAT, así que no dicen de qué impuesto es. En los dos casos BR-CO-18
    dice que no hay desglose, y quien lo lee busca un TAX que tiene delante.

    Solo se avisa cuando no hay ninguna entrada del desglose: con desglose, un
    TAX en la cabecera es EDIFACT legítimo y no estorba a nada.
    """
    if raiz is None or not deteccion or deteccion.familia != FAMILIA:
        return []
    from validador.sintaxis import SINTAXIS_EDIFACT

    if raiz.xpath(SINTAXIS_EDIFACT.desglose):
        return []
    cabecera = raiz.xpath("./*[S_TAX][not(preceding-sibling::S_UNS)]")
    resumen = raiz.xpath("./*[S_TAX][preceding-sibling::S_UNS]")
    if not cabecera and not resumen:
        return []
    donde = []
    if cabecera:
        donde.append(
            f"{len(cabecera)} en la cabecera, antes del UNS"
            if len(cabecera) > 1
            else "uno en la cabecera, antes del UNS"
        )
    if resumen:
        donde.append(
            f"{len(resumen)} en el resumen sin decir que son IVA"
            if len(resumen) > 1
            else "uno en el resumen sin decir que es IVA"
        )
    return [
        Incidencia(
            "EDI-IVA-FUERA-DEL-DESGLOSE",
            AVISO,
            f"La factura trae grupos de impuesto —{_y(donde)}—, pero ninguno "
            "donde EN 16931 lee el desglose: después del UNS y marcado como "
            "IVA, TAX+7+VAT. Por eso BR-CO-18 dice que no hay desglose: el "
            "impuesto está escrito, pero donde la norma no lo mira. El de la "
            "cabecera es el impuesto del documento entero y no sustituye al "
            "desglose; el del resumen necesita el tipo VAT para ser del IVA.",
            campo="TAX, grupo de impuesto",
            esperado="TAX+7+VAT después del UNS, con su MOA+125 y su MOA+124",
            encontrado=_y(donde),
        )
    ]

# --- Entrada pública -------------------------------------------------------


def es_plano(datos: bytes) -> bool:
    """Si esto parece un EDIFACT de los de verdad, en tira."""
    cabeza = datos.lstrip()[:3].upper()
    return cabeza in (b"UNA", b"UNB", b"UNH")


def descifrar(datos: bytes) -> str:
    """El texto de un EDIFACT.

    ISO 9735 declara el juego de caracteres en el UNB (UNOA, UNOC, UNOY…) y
    casi todos son de un byte. Se prueba UTF-8 primero porque UNOY lo es y
    porque un fichero moderno suele venir así, y se cae a latin-1, que no
    falla nunca y deja el texto legible aunque alguna tilde salga rara. Fallar
    aquí sería no poder decir nada de la factura.
    """
    for juego in ("utf-8", "latin-1"):
        try:
            return datos.decode(juego)
        except UnicodeDecodeError:
            continue
    return datos.decode("latin-1", errors="replace")


# Una etiqueta de segmento son tres caracteres y el primero es una letra. No
# hay ninguna que no lo sea. Si al partir la tira sale otra cosa, lo que ha
# pasado casi siempre es que dentro de un dato había un carácter de servicio
# que el emisor no soltó con «?», y el segmento se partió por la mitad.
_ETIQUETA = _re.compile(r"^[A-Z][A-Z0-9]{2}$")


def _quitar_las_imposibles(
    segmentos: list[Segmento],
) -> tuple[list[Segmento], list[Segmento]]:
    """Aparta los trozos que no son un segmento.

    Se apartan **antes** de agrupar, y esa es la parte que importa. Un trozo
    con una etiqueta que no está en la tabla de grupos no se queda fuera del
    grupo: lo cierra. Un apóstrofo suelto en medio del nombre de una empresa
    cerraría la línea, y los importes de esa línea pasarían a contarse como
    totales de la factura sin dar ningún error.

    Apartarlos también deja cuadrar la cuenta del UNT, que es la que prueba
    que apartarlos era lo correcto: el emisor declara cuántos segmentos lleva
    el mensaje, y ese número es el de antes de romperse.
    """
    buenos = [s for s in segmentos if _ETIQUETA.match(s.etiqueta)]
    return buenos, [s for s in segmentos if not _ETIQUETA.match(s.etiqueta)]


def _queja_de_etiqueta(imposibles: list[Segmento], servicio: Servicio) -> Incidencia:
    muestra = _y([f"«{s.etiqueta[:40]}»" for s in imposibles[:3]])
    de_mas = len(imposibles) - 3
    if de_mas > 0:
        muestra += f" y {de_mas} más"
    return Incidencia(
        "EDI-ETIQUETA-IMPOSIBLE",
        ERROR,
        "Hay texto donde tenía que haber una etiqueta de segmento: "
        f"{muestra}. Una etiqueta son tres caracteres, así que eso no lo es. "
        f"Lo que suele haber detrás es un «{servicio.terminador}» dentro de "
        f"un dato que se escribió sin el «{servicio.escape}» delante, y el "
        "segmento se partió por ahí. El trozo se ha dejado fuera para no "
        "arrastrar el error al resto, pero el dato que llevara está perdido.",
        campo="Etiqueta de segmento",
        esperado="tres caracteres",
        encontrado=imposibles[0].etiqueta[:60],
    )


def leer(datos: bytes) -> tuple[list[Segmento], Servicio, list[Incidencia]]:
    """Parte un EDIFACT plano en segmentos y comprueba las cuentas del sobre."""
    texto = descifrar(datos)
    servicio, desde = servicio_de(texto)
    segmentos, suelto = partir(texto[desde:], servicio)
    incidencias: list[Incidencia] = []
    if cuantos_de_servicio(texto) == 5:
        incidencias.append(
            Incidencia(
                "EDI-UNA-DE-CINCO",
                NOTA,
                "El UNA declara cinco caracteres de servicio en vez de los "
                "seis que manda ISO 9735: falta el hueco reservado. Se ha "
                "leído el último como terminador de segmento, que es la "
                "única lectura posible porque detrás del UNA solo puede "
                "venir el UNB.",
                campo="UNA",
                esperado="seis caracteres",
                encontrado=texto.lstrip()[3:8],
            )
        )
    segmentos, imposibles = _quitar_las_imposibles(segmentos)
    if imposibles:
        incidencias.append(_queja_de_etiqueta(imposibles, servicio))
    if suelto:
        incidencias.append(
            Incidencia(
                "EDI-SEGMENTO-SIN-CERRAR",
                ERROR,
                "Después del último segmento cerrado queda texto sin "
                "terminar. El fichero está cortado o el carácter que separa "
                "los segmentos no es el que dice.",
                campo="Final del fichero",
                encontrado=suelto[:40] + ("…" if len(suelto) > 40 else ""),
            )
        )
    if not segmentos:
        incidencias.append(
            Incidencia(
                "EDI-SIN-SEGMENTOS",
                ERROR,
                "No se ha podido partir el fichero en segmentos.",
                campo="Fichero",
            )
        )
        return segmentos, servicio, incidencias
    incidencias.extend(_reglas_del_sobre(segmentos, _mensajes(segmentos)))
    return segmentos, servicio, incidencias


def arbol(datos: bytes, deteccion):
    """El árbol de un documento, sea XML o sea una tira de EDIFACT.

    Existe para que nadie tenga que acordarse de que uno de los cuatro
    formatos no se parsea con lxml. Antes de esto, cualquier función que
    recibiera un EDIFACT plano y llamara a `etree.fromstring` reventaba con
    una excepción de XML mal formado —cosa que era verdad y no venía a
    cuento—, y le tocaba al que llamara acordarse de mirarlo antes.

    Devuelve el árbol —o None si no lo hay— y lo que se haya visto al leer.
    """
    if not deteccion:
        return None, []
    if deteccion.familia == FAMILIA and es_plano(datos):
        return convertir(datos)
    try:
        return etree.fromstring(datos, parser=_parser()), []
    except etree.XMLSyntaxError:
        return None, []


def convertir(datos: bytes):
    """De EDIFACT plano al árbol que leen las reglas.

    Devuelve el árbol del primer mensaje y las quejas de sintaxis. El árbol es
    None solo cuando no se ha podido partir nada.
    """
    segmentos, servicio, incidencias = leer(datos)
    if not segmentos:
        return None, incidencias
    tramos = _mensajes(segmentos)
    if not tramos:
        return None, incidencias
    inicio, fin = tramos[0]
    return a_arbol(segmentos[inicio : fin + 1], servicio), incidencias
