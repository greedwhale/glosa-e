# -*- coding: utf-8 -*-
"""Las novedades: cada regla nueva o retirada del validador, con su fecha.

Por qué existe
--------------
Quien programa una factura electrónica quiere enterarse de lo que cambia sin
depender de una red social. Hasta el 25-10-2026 eso solo se podía siguiendo a
Glosa-e en X o en LinkedIn, o volviendo a mirar el catálogo de códigos. Esta
página lo junta, con la fecha delante, y lo da también como **canal Atom**
(`novedades.xml`), que se sigue con un lector de noticias sin que nadie tenga
que acordarse de avisar. Que Slack o Teams lo lean no se ha comprobado, y por
eso la página no lo dice.

Solo reglas, y no los artículos
-------------------------------
Nació el 25-10-2026 con los artículos de la bitácora mezclados por fecha, y
ese mismo día se quitaron: cada artículo se contaba dos veces, en su índice y
aquí. Lo que no está en ningún otro sitio es el registro de lo que cambia en
el validador, código a código. Los artículos tienen su propio canal,
`bitacora.xml`, y los dos se ofrecen juntos en el botón de seguir de esta
página (`panel`), que es donde se elige dónde recibirlo todo.

Las reglas se apuntan a mano en `web/novedades.txt`, porque lo que hay que
decir de un código nuevo (qué mira y por qué) no está escrito en ningún sitio
del que se pueda sacar.

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

from validador import atom

__all__ = [
    "CANAL",
    "FUENTE",
    "HUECO",
    "HUECO_DE_SEGUIR",
    "NOMBRE",
    "Novedad",
    "NovedadMal",
    "Novedades",
    "canal",
    "leer",
    "pagina",
    "panel",
    "revisar",
]

NOMBRE = "novedades.html"
CANAL = "novedades.xml"
FUENTE = "novedades.txt"
HUECO = "<!-- AQUI VAN LAS NOVEDADES -->"
HUECO_DE_SEGUIR = "<!-- AQUI VA COMO SEGUIRLAS -->"

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


# --- Cómo seguirlas ----------------------------------------------------------
#
# Un botón que se despliega con los sitios donde recibirlo, y lo que recibe
# quien elige cada uno: no es lo mismo un boletín al mes que cada regla el día
# que sale. Va en un `<details>` para que abra y cierre sin guion; el guion
# solo copia la dirección de un canal, que es para lo que la caja de antes
# enseñaba la dirección entera. Sin guion, el nombre del canal es un enlace a
# él, que también se copia.
#
# El boletín de LinkedIn entra el día que exista: una opción que manda a un
# boletín que no hay es un cartel. Basta con darle su dirección a `panel`.


def _opcion(titulo: str, enlace: str, texto: str, cuando: str,
            copiar: str | None = None) -> str:
    boton = ("" if copiar is None else
             f'<button type="button" class="copiar" data-copiar="{html.escape(copiar)}" '
             'hidden>Copiar la dirección</button>')
    return (f'<li><p class="opcion"><a href="{html.escape(enlace)}">{html.escape(titulo)}</a>'
            f'<span class="cada">{html.escape(cuando)}</span></p>'
            f"<p>{html.escape(texto)}</p>{boton}</li>")


def panel(dominio: str, cuenta_en_x: str, bitacora: str | None,
          boletin: str | None = None) -> str:
    """El botón de seguir, con un destino por cada sitio que existe: sin
    bitácora montada, tampoco su canal."""
    opciones = []
    if boletin:
        opciones.append(_opcion(
            "Boletín La glosa del mes", boletin,
            "Todo lo del mes en un número, por correo y en el móvil. La "
            "suscripción se hace en LinkedIn.", "uno al mes"))
    opciones += [
        _opcion("Glosa-e en X", cuenta_en_x,
                "Lo que se va publicando allí, el día que sale.", "a diario"),
        _opcion("Canal Atom de las novedades", f"./{CANAL}",
                "Cada regla nueva o retirada, en un lector de noticias, sin que "
                "nadie tenga que acordarse de avisar.", "cada regla",
                copiar=f"{dominio}/{CANAL}"),
    ]
    if bitacora:
        opciones.append(_opcion(
            "Canal Atom del blog", f"./{bitacora}",
            "Cada artículo nuevo del blog, en el mismo lector.",
            "cada artículo", copiar=f"{dominio}/{bitacora}"))
    return ('<details class="seguirlas"><summary>Seguir las novedades '
            '<svg class="galon" viewBox="0 0 10 6" aria-hidden="true">'
            '<path d="M1 1l4 4 4-4"/></svg></summary>'
            '<ul class="destinos">' + "".join(opciones) + "</ul></details>")


def pagina(plantilla: str, novedades: Novedades, fichas: set[str], catalogo: int,
           seguir: str) -> str:
    """`novedades.html` entera: la lista en su hueco y el botón en el suyo."""
    for hueco, que in ((HUECO, "una sola novedad"), (HUECO_DE_SEGUIR, "cómo seguirlas")):
        if plantilla.count(hueco) != 1:
            raise NovedadMal(
                f"{NOMBRE} ya no lleva `{hueco}` una vez, así que la página se "
                f"publicaría sin {que} y sin que nada fallara.")
    partes = []
    for e in novedades.entradas:
        codigos = ""
        if e.nuevos:
            codigos += ('<p class="rotulo-codigos">Nuevos</p>'
                        + _chips(e.nuevos, fichas, "nuevos"))
        if e.retirados:
            codigos += ('<p class="rotulo-codigos">Retirados</p>'
                        + _chips(e.retirados, set(), "retirados"))
        partes.append(
            f'<li class="novedad" id="{e.id}">'
            f'<p class="cuando"><time datetime="{e.fecha.isoformat()}">'
            f"{_dicha(e.fecha)}</time></p>"
            f"<h2>{html.escape(e.titulo)}</h2><p>{html.escape(e.texto)}</p>{codigos}</li>"
        )
    lista = '<ol class="novedades">' + "\n".join(partes) + "</ol>"
    partida = (
        '<p class="partida">La lista empieza el '
        f"{_dicha(novedades.partida + _dt.timedelta(days=1))}. Los "
        f"{len(novedades.de_partida)} códigos que había el "
        f"{_dicha(novedades.partida)}, el día que entró en vigor la orden, no "
        'salen aquí uno a uno: están todos en <a href="./incidencias.html">el '
        f"catálogo</a>, que hoy tiene {catalogo}.</p>"
    )
    return (plantilla.replace(HUECO, lista + "\n" + partida)
            .replace(HUECO_DE_SEGUIR, seguir))


def canal(novedades: Novedades, dominio: str) -> str:
    """El canal Atom con las mismas entradas que la página. El id de cada una
    es su ancla en la página, `/novedades#id`, que no cambia nunca."""
    entradas = []
    for e in novedades.entradas:
        resumen = e.texto
        if e.nuevos:
            resumen += " Nuevos: " + ", ".join(e.nuevos) + "."
        if e.retirados:
            resumen += " Retirados: " + ", ".join(e.retirados) + "."
        entradas.append(atom.Entrada(
            titulo=e.titulo, enlace=atom.direccion(dominio, f"./{NOMBRE}#{e.id}"),
            publicada=e.fecha, cambiada=e.fecha, resumen=resumen))
    return atom.canal(
        dominio=dominio, nombre=CANAL, pagina=NOMBRE.removesuffix(".html"),
        titulo="Novedades de Glosa-e",
        subtitulo="Cada regla nueva o retirada del validador, con su fecha.",
        entradas=entradas, sin_entradas=novedades.partida)
