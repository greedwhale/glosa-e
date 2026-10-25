# -*- coding: utf-8 -*-
"""Las novedades: cada regla nueva o retirada y cada artículo, con su fecha.

Por qué existe
--------------
Quien programa una factura electrónica quiere enterarse de lo que cambia sin
depender de una red social. Hasta el 25-10-2026 eso solo se podía siguiendo a
Glosa-e en X o en LinkedIn, o volviendo a mirar el catálogo de códigos. Esta
página lo junta todo, con la fecha delante, y lo da también como **canal
Atom** (`novedades.xml`), que se sigue con un lector de noticias sin que
nadie tenga que acordarse de avisar. Que Slack o Teams lo lean no se ha
comprobado, y por eso la página no lo dice.

Lo que se apunta y lo que se lee solo
-------------------------------------
Los artículos salen solos de la bitácora, con su fecha y su entradilla. Las
reglas se apuntan a mano en `web/novedades.txt`, porque lo que hay que decir
de un código nuevo (qué mira y por qué) no está escrito en ningún sitio del
que se pueda sacar.

Y como lo que se apunta a mano se queda atrás, **el montaje se niega** si el
catálogo no cuadra con lo apuntado: un código que exista y no salga ni en la
partida ni en ninguna novedad, uno que se dé por retirado y siga, o uno que
haya desaparecido sin decirlo. La partida son los códigos que había el
06-10-2026, el día que entró en vigor la orden, medidos sobre el commit de
ese día; la lista empieza al siguiente. Lo que esto **no** vigila es el
cambio de una regla que ya estaba: no hay forma de medirlo desde fuera, y sale
cuando se apunta. La página lo dice.

El formato de `novedades.txt`
-----------------------------
Bloques de líneas `clave: valor`, separados por una línea en blanco. Una
línea que empieza por espacio sigue el valor de la anterior, y las que
empiezan por `#` son comentarios. Las claves de una novedad son `fecha`
(AAAA-MM-DD), `id` (el ancla, que no cambia nunca porque es la identidad de
la entrada en el canal), `titulo`, `texto` y, si los hay, `nuevos` y
`retirados`, separados por espacios. La partida es un bloque aparte con
`partida` (la fecha) y `codigos`.

Estática y sin Pyodide, como la bitácora y el catálogo.
"""
from __future__ import annotations

import datetime as _dt
import html
import re
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape as _xml

__all__ = [
    "CANAL",
    "FUENTE",
    "HUECO",
    "NOMBRE",
    "Novedad",
    "NovedadMal",
    "Novedades",
    "canal",
    "leer",
    "pagina",
    "revisar",
]

NOMBRE = "novedades.html"
CANAL = "novedades.xml"
FUENTE = "novedades.txt"
HUECO = "<!-- AQUI VAN LAS NOVEDADES -->"

_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
# La misma forma que un nombre de ficha: un código que no cabe en una
# dirección no podría enlazar la suya.
_CODIGO = re.compile(r"^[A-Z0-9-]{2,60}$")
_DE_UNA_NOVEDAD = {"fecha", "id", "titulo", "texto", "nuevos", "retirados"}
_OBLIGATORIAS = {"fecha", "id", "titulo", "texto"}
_DE_LA_PARTIDA = {"partida", "codigos"}
_CLASE_DE_LOS_CODIGOS = "codigos"


class NovedadMal(ValueError):
    """`novedades.txt` no se puede leer, o no cuadra con el catálogo."""


@dataclass(frozen=True)
class Novedad:
    """Una entrada de `novedades.txt`, ya comprobada."""

    fecha: _dt.date
    id: str
    titulo: str
    texto: str
    nuevos: tuple[str, ...] = ()
    retirados: tuple[str, ...] = ()


@dataclass(frozen=True)
class Novedades:
    """Lo que dice `novedades.txt`: las entradas y la partida."""

    entradas: tuple[Novedad, ...]
    partida: _dt.date
    de_partida: frozenset[str]


def _bloques(texto: str, nombre: str) -> list[dict[str, str]]:
    bloques: list[dict[str, str]] = []
    actual: dict[str, str] = {}
    clave = None
    for numero, linea in enumerate(texto.splitlines(), 1):
        if linea.startswith("#"):
            continue
        if not linea.strip():
            if actual:
                bloques.append(actual)
            actual, clave = {}, None
            continue
        if linea[0].isspace():
            if clave is None:
                raise NovedadMal(f"{nombre}:{numero}: una línea que sigue a nada")
            actual[clave] += " " + linea.strip()
            continue
        if ":" not in linea:
            raise NovedadMal(f"{nombre}:{numero}: no es `clave: valor`")
        clave, valor = (p.strip() for p in linea.split(":", 1))
        if clave in actual:
            raise NovedadMal(f"{nombre}:{numero}: `{clave}` dos veces en el mismo bloque")
        actual[clave] = valor
    if actual:
        bloques.append(actual)
    return bloques


def _fecha(valor: str, donde: str) -> _dt.date:
    if not _FECHA.match(valor):
        raise NovedadMal(f"{donde}: la fecha tiene que ser AAAA-MM-DD, y es {valor}")
    try:
        return _dt.date.fromisoformat(valor)
    except ValueError as error:
        raise NovedadMal(f"{donde}: {valor} no es una fecha") from error


def _codigos(valor: str, donde: str) -> tuple[str, ...]:
    codigos = tuple(valor.split())
    malos = [c for c in codigos if not _CODIGO.match(c)]
    if malos:
        raise NovedadMal(f"{donde}: no son códigos: {', '.join(malos)}")
    if len(set(codigos)) != len(codigos):
        raise NovedadMal(f"{donde}: hay un código repetido")
    return codigos


def leer(ruta: Path) -> Novedades:
    """Lee `novedades.txt` y comprueba su forma. No mira el catálogo."""
    entradas: list[Novedad] = []
    partida: tuple[_dt.date, frozenset[str]] | None = None
    for bloque in _bloques(ruta.read_text(encoding="utf-8"), ruta.name):
        if "partida" in bloque:
            sobran = set(bloque) - _DE_LA_PARTIDA
            if sobran or set(bloque) != _DE_LA_PARTIDA:
                raise NovedadMal(
                    f"{ruta.name}: la partida lleva `partida` y `codigos` y nada más")
            if partida is not None:
                raise NovedadMal(f"{ruta.name}: hay dos partidas")
            partida = (_fecha(bloque["partida"], f"{ruta.name}, la partida"),
                       frozenset(_codigos(bloque["codigos"], f"{ruta.name}, la partida")))
            continue
        donde = f"{ruta.name}, `{bloque.get('id', bloque.get('titulo', '?'))}`"
        sobran = set(bloque) - _DE_UNA_NOVEDAD
        if sobran:
            raise NovedadMal(f"{donde}: claves que no existen: {', '.join(sorted(sobran))}")
        faltan = _OBLIGATORIAS - set(bloque)
        if faltan:
            raise NovedadMal(f"{donde}: le falta {', '.join(sorted(faltan))}")
        if not _ID.match(bloque["id"]):
            raise NovedadMal(f"{donde}: el id va en minúsculas, cifras y guiones")
        entradas.append(Novedad(
            fecha=_fecha(bloque["fecha"], donde),
            id=bloque["id"],
            titulo=bloque["titulo"],
            texto=bloque["texto"],
            nuevos=_codigos(bloque.get("nuevos", ""), donde),
            retirados=_codigos(bloque.get("retirados", ""), donde),
        ))
    if partida is None:
        raise NovedadMal(
            f"{ruta.name} no tiene partida, así que no se puede saber qué códigos "
            "ya estaban y cuáles son nuevos sin apuntar")
    ids = [e.id for e in entradas]
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    if repetidos:
        raise NovedadMal(
            f"{ruta.name}: ids repetidos: {', '.join(repetidos)}. El id es la "
            "identidad de la entrada en el canal, y dos iguales se leen como una")
    antes = [e.id for e in entradas if e.fecha <= partida[0]]
    if antes:
        raise NovedadMal(
            f"{ruta.name}: {', '.join(antes)} es de la partida o de antes, y la "
            "lista empieza al día siguiente")
    return Novedades(
        entradas=tuple(sorted(entradas, key=lambda e: (e.fecha, e.id), reverse=True)),
        partida=partida[0],
        de_partida=partida[1],
    )


def revisar(novedades: Novedades, catalogo: set[str]) -> None:
    """Se niega si lo apuntado no cuadra con los códigos que hay de verdad."""
    nuevos = {c for e in novedades.entradas for c in e.nuevos}
    retirados = {c for e in novedades.entradas for c in e.retirados}
    sin_apuntar = sorted(catalogo - novedades.de_partida - nuevos)
    if sin_apuntar:
        cuantos = ("un código no sale" if len(sin_apuntar) == 1
                   else f"{len(sin_apuntar)} códigos no salen")
        raise NovedadMal(
            f"{cuantos} en las novedades: "
            f"{', '.join(sin_apuntar[:8])}. Un código nuevo se apunta en "
            f"web/{FUENTE}, en `nuevos`, con la fecha en que sale y lo que mira. "
            "Sin eso, la página y el canal dirían que no ha cambiado nada.")
    siguen = sorted(retirados & catalogo)
    if siguen:
        raise NovedadMal(
            f"se dan por retirados y siguen en el catálogo: {', '.join(siguen)}")
    idos = sorted((novedades.de_partida | nuevos) - catalogo - retirados)
    if idos:
        raise NovedadMal(
            f"ya no están en el catálogo y nadie lo ha dicho: {', '.join(idos[:8])}. "
            f"Un código que se quita se apunta en web/{FUENTE}, en `retirados`.")
    fantasmas = sorted(retirados - novedades.de_partida - nuevos)
    if fantasmas:
        raise NovedadMal(
            f"se dan por retirados y nunca estuvieron: {', '.join(fantasmas)}")


# --- Lo que se publica -------------------------------------------------------
#
# Una sola lista, con las dos clases de entrada mezcladas por fecha: quien
# sigue las novedades quiere saber qué ha cambiado esta semana, no ir a dos
# sitios. La de regla se reconoce por los códigos; la de bitácora, por llevar
# a su artículo.


@dataclass(frozen=True)
class _Fila:
    fecha: _dt.date
    cambiada: _dt.date
    tipo: str
    titulo: str
    texto: str
    enlace: str
    ancla: str
    nuevos: tuple[str, ...] = ()
    retirados: tuple[str, ...] = ()


def _filas(novedades: Novedades, articulos) -> list[_Fila]:
    filas = [
        _Fila(e.fecha, e.fecha, "Reglas", e.titulo, e.texto,
              f"./{NOMBRE}#{e.id}", e.id, e.nuevos, e.retirados)
        for e in novedades.entradas
    ] + [
        _Fila(a.fecha, a.cambiada, "Bitácora", a.titulo, a.entradilla,
              f"./{a.nombre}", "")
        for a in articulos
    ]
    return sorted(filas, key=lambda f: (f.fecha, f.tipo == "Reglas", f.titulo),
                  reverse=True)


_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def _dicha(fecha: _dt.date) -> str:
    return f"{fecha.day} de {_MESES[fecha.month - 1]} de {fecha.year}"


def _chips(codigos, fichas: set[str], clase: str) -> str:
    def uno(c: str) -> str:
        if c in fichas:
            return f'<li><a href="./codigo-{html.escape(c)}.html">{html.escape(c)}</a></li>'
        return f"<li>{html.escape(c)}</li>"
    # La clase va aparte porque es un nombre de CSS y no una palabra: dentro
    # del f-string, test_voz la leería como la palabra sin tilde.
    return (f'<ul class="{_CLASE_DE_LOS_CODIGOS} {clase}">'
            + "".join(uno(c) for c in codigos) + "</ul>")


def pagina(plantilla: str, novedades: Novedades, articulos, fichas: set[str],
           catalogo: int) -> str:
    """El cuerpo de `novedades.html`, ya metido en su plantilla."""
    if HUECO not in plantilla:
        raise NovedadMal(
            f"{NOMBRE} ya no lleva `{HUECO}`, así que la página se publicaría "
            "sin una sola novedad y sin que nada fallara.")
    partes = []
    for f in _filas(novedades, articulos):
        ancla = f' id="{f.ancla}"' if f.ancla else ""
        if f.tipo == "Reglas":
            titulo = f"<h2>{html.escape(f.titulo)}</h2>"
            codigos = ""
            if f.nuevos:
                codigos += ('<p class="rotulo-codigos">Nuevos</p>'
                            + _chips(f.nuevos, fichas, "nuevos"))
            if f.retirados:
                codigos += ('<p class="rotulo-codigos">Retirados</p>'
                            + _chips(f.retirados, set(), "retirados"))
        else:
            titulo = f'<h2><a href="{f.enlace}">{html.escape(f.titulo)}</a></h2>'
            codigos = ""
        partes.append(
            f'<li class="novedad {"de-reglas" if f.tipo == "Reglas" else "de-bitacora"}"{ancla}>'
            f'<p class="cuando"><time datetime="{f.fecha.isoformat()}">'
            f"{_dicha(f.fecha)}</time> <span>{f.tipo}</span></p>"
            f"{titulo}<p>{html.escape(f.texto)}</p>{codigos}</li>"
        )
    lista = '<ol class="novedades">' + "\n".join(partes) + "</ol>"
    partida = (
        '<p class="partida">La lista de reglas empieza el '
        f"{_dicha(novedades.partida + _dt.timedelta(days=1))}. Los "
        f"{len(novedades.de_partida)} códigos que había el "
        f"{_dicha(novedades.partida)}, el día que entró en vigor la orden, no "
        'salen aquí uno a uno: están todos en <a href="./incidencias.html">el '
        f"catálogo</a>, que hoy tiene {catalogo}.</p>"
    )
    return plantilla.replace(HUECO, lista + "\n" + partida)


def canal(novedades: Novedades, articulos, dominio: str) -> str:
    """El canal Atom (RFC 4287) con las mismas entradas que la página.

    La hora no se apunta en ningún sitio, así que va la medianoche UTC del día:
    Atom pide fecha y hora, y lo que vale es el día. El id de cada entrada no
    cambia nunca, porque es lo que usa el lector para saber que ya la enseñó:
    el ancla para las de reglas, la dirección del artículo para las de la
    bitácora.
    """
    filas = _filas(novedades, articulos)

    def momento(dia: _dt.date) -> str:
        return f"{dia.isoformat()}T00:00:00Z"

    def direccion(enlace: str) -> str:
        # `./x.html#y` → `https://dominio/x#y`, la dirección limpia que sirve
        # producción, como la canónica y el sitemap.
        sin_punto = enlace.removeprefix("./")
        pagina_, _, ancla = sin_punto.partition("#")
        limpia = pagina_.removesuffix(".html")
        return f"{dominio}/{limpia}" + (f"#{ancla}" if ancla else "")

    entradas = []
    for f in filas:
        resumen = f.texto
        if f.nuevos:
            resumen += " Nuevos: " + ", ".join(f.nuevos) + "."
        if f.retirados:
            resumen += " Retirados: " + ", ".join(f.retirados) + "."
        enlace = direccion(f.enlace)
        entradas.append(
            "  <entry>\n"
            f"    <title>{_xml(f.titulo)}</title>\n"
            f'    <link rel="alternate" type="text/html" href="{_xml(enlace)}"/>\n'
            f"    <id>{_xml(enlace)}</id>\n"
            f"    <published>{momento(f.fecha)}</published>\n"
            f"    <updated>{momento(f.cambiada)}</updated>\n"
            f"    <category term=\"{'reglas' if f.tipo == 'Reglas' else 'bitacora'}\" "
            f'label="{_xml(f.tipo)}"/>\n'
            f"    <summary>{_xml(resumen)}</summary>\n"
            "  </entry>\n"
        )
    ultima = max((f.cambiada for f in filas), default=novedades.partida)
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="es">\n'
        "  <title>Novedades de Glosa-e</title>\n"
        "  <subtitle>Cada regla nueva o retirada del validador y cada artículo "
        "de la bitácora, con su fecha.</subtitle>\n"
        f'  <link rel="self" type="application/atom+xml" href="{dominio}/{CANAL}"/>\n'
        f'  <link rel="alternate" type="text/html" href="{dominio}/novedades"/>\n'
        f"  <id>{dominio}/novedades</id>\n"
        f"  <updated>{momento(ultima)}</updated>\n"
        "  <author><name>Glosa-e</name>"
        f"<uri>{dominio}/</uri></author>\n"
        + "".join(entradas)
        + "</feed>\n"
    )
