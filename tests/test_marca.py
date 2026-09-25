# -*- coding: utf-8 -*-
"""La marca no se puede desviar en silencio de lo que sirve la página.

El dibujo vive en varios sitios y ninguno se lee desde otro:

  `web/marca/glosa-e.svg`   el bloque, que genera `web/marca/trazar.py`
  los siete `.html`         el favicon: el signo de la cabecera, sin el
                            nombre, que a 16 px no cabe
  `web/glosa.css`           el signo de la cabecera, como máscara, que tiene
                            que ser el mismo que el de la zona de soltar

Hasta el 23-09-2026 la hoja llevaba además el bloque entero, que era la
cabecera. Ya no: la cabecera es el signo y el nombre en la letra de la página,
y el porqué está en `MARCA.md`. Y hasta el 25-09-2026 el favicon siguió siendo
el cuadro plata con el signo en blanco, porque nada lo comparaba con la
cabecera: solo sus copias entre sí, y tres de siete.

Varias copias de algo de 5 KB se acaban separando. Y la forma en que se separan
es la peor de todas: no rompen nada. La página sigue cargando, sale todo verde,
y la portada enseña una marca y el aviso legal otra hasta que alguien lo ve
publicado.

Estas pruebas no comprueban que la marca sea bonita. Comprueban que sea **la
misma**, que es lo único que una prueba puede saber de un dibujo.
"""

import re

from pathlib import Path
from urllib.parse import unquote

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SVG = RAIZ / "web" / "marca" / "glosa-e.svg"
HOJA = RAIZ / "web" / "glosa.css"
PAGINAS = ["index.html", "banco.html", "legal.html"]
# El favicon va en todas, no en las tres de siempre: la prueba miraba esas
# tres y las otras cuatro podían llevar lo que fuera.
CON_ICONO = sorted(p.name for p in (RAIZ / "web").glob("*.html"))

# Los colores aprobados el 30 de agosto de 2026, con sus razones de contraste
# medidas con la fórmula de WCAG 2.1 y publicadas en MARCA.md:
#
#   signo blanco sobre la plata     3,03:1   (mínimo 3:1 para una forma gráfica)
#   palabra negra sobre la plata    6,92:1   (mínimo 4,5:1 para texto pequeño)
#
# Si alguien cambia la plata, esas dos cifras dejan de ser ciertas y MARCA.md
# pasa a mentir. Por eso el color se comprueba aquí y no se deja al ojo.
PLATA = "#949494"
SIGNO = "#FFFFFF"
NOMBRE = "#000000"

INDEX = RAIZ / "web" / "index.html"
PATRON_FAVICON = r'<link rel="icon" href="(data:image/svg\+xml,[^"]+)">'


def test_el_svg_original_esta_donde_dice_estar():
    assert SVG.is_file(), (
        "Falta web/marca/glosa-e.svg. Sin él, la marca es un blob de 5 KB "
        "dentro de una hoja de estilo y no hay forma de retocarla.")


def _trazos(svg: str) -> list[str]:
    """Los caminos de un dibujo, que es lo que lo hace el mismo."""
    return re.findall(r"""<path d=['"]([^'"]+)['"]""", svg)


def test_la_hoja_ya_no_lleva_el_bloque():
    """El bloque salió de la cabecera el 23-09-2026 y no puede volver solo.

    `trazar.py` ya no escribe en la hoja. Un bloque que volviera a ella, pegado
    a mano, sería una copia que nadie regenera: la primera vez que se retocara
    la marca, la cabecera se quedaría con la vieja.
    """
    hoja = HOJA.read_text(encoding="utf-8")
    assert PLATA[1:].lower() not in hoja.lower(), (
        "glosa.css vuelve a llevar la plata del bloque. La cabecera lleva el "
        "signo y el nombre; si se quiere el bloque otra vez, antes hay que "
        "cambiar MARCA.md y volver a hacer que trazar.py escriba aquí.")


def test_el_signo_de_la_cabecera_es_el_de_la_zona():
    """Dos copias del signo —la máscara de la cabecera y el icono de la zona de
    soltar— y un solo dibujo. El de la zona es el que dice MARCA.md."""
    hoja = HOJA.read_text(encoding="utf-8")
    regla = re.search(r"\.marca::before \{(.*?)\}", hoja, re.S)
    assert regla, "glosa.css ya no pinta el signo en `.marca::before`"
    mascaras = set(re.findall(r'mask: url\("([^"]+)"\)', regla[1]))
    assert len(mascaras) == 1, (
        f"`.marca::before` lleva {len(mascaras)} dibujos distintos entre "
        "`mask` y `-webkit-mask`, y tiene que ser uno")
    assert "background: var(--acento)" in regla[1], (
        "el signo tiene que pintarse con --acento, que cambia con el tema")
    cabecera = _trazos(mascaras.pop().replace("%3C", "<").replace("%3E", ">"))
    zona = re.search(r'<div id="zona".*?<svg(.*?)</svg>', INDEX.read_text(
        encoding="utf-8"), re.S)
    assert zona, "la zona de soltar ya no lleva el signo"
    assert cabecera == _trazos(zona[1]), (
        f"el signo de la cabecera {cabecera} no es el de la zona "
        f"{_trazos(zona[1])}")


def test_los_colores_son_los_que_publica_marca_md():
    """Las razones de contraste publicadas dependen de estos tres valores."""
    svg = SVG.read_text(encoding="utf-8")
    for color, que_es in [(PLATA, "la plata del bloque"),
                          (SIGNO, "el blanco del signo"),
                          (NOMBRE, "el negro del nombre")]:
        assert color in svg, (
            f"No encuentro {color} en la marca, que es {que_es}. Si se ha "
            "cambiado a propósito, hay que recalcular las razones de "
            "contraste de MARCA.md antes de tocarlo: las de ahí quedarían "
            "falsas.")


def _icono() -> str:
    """El favicon, decodificado, después de comprobar que es uno y el mismo."""
    encontrados = {}
    for nombre in CON_ICONO:
        texto = (RAIZ / "web" / nombre).read_text(encoding="utf-8")
        iconos = re.findall(PATRON_FAVICON, texto)
        assert len(iconos) == 1, (
            f"En {nombre} hay {len(iconos)} favicons y tiene que haber uno.")
        encontrados[nombre] = iconos[0]
    distintos = set(encontrados.values())
    assert len(distintos) == 1, (
        "Las páginas llevan favicons distintos:\n  "
        + "\n  ".join(f"{p}: …{u[-40:]}" for p, u in encontrados.items()))
    return unquote(distintos.pop().removeprefix("data:image/svg+xml,"))


def _mascara_de_la_cabecera() -> str:
    hoja = HOJA.read_text(encoding="utf-8")
    regla = re.search(r"\.marca::before \{(.*?)\}", hoja, re.S)
    return unquote(re.search(r'mask: url\("([^"]+)"\)', regla[1])[1]
                   .removeprefix("data:image/svg+xml,"))


def _acentos() -> tuple[str, str]:
    """El `--acento` de día y el de noche, tal como los declara la hoja."""
    hoja = HOJA.read_text(encoding="utf-8")
    dia = re.search(r":root \{(.*?)\n\}", hoja, re.S)
    noche = re.search(
        r"@media \(prefers-color-scheme: dark\) \{\s*:root \{(.*?)\}", hoja, re.S)
    return tuple(re.search(r"--acento:\s*(#[0-9a-fA-F]{6})", b[1])[1].lower()
                 for b in (dia, noche))


def _atributo(svg: str, nombre: str) -> str:
    return re.search(rf"{nombre}='([^']+)'", svg)[1]


def test_el_favicon_es_el_mismo_en_todas_las_paginas():
    """Siete copias que hay que mantener iguales, y se comprueban las siete."""
    assert len(CON_ICONO) >= 7, CON_ICONO
    _icono()


def test_el_favicon_es_el_signo_de_la_cabecera():
    """Lo vio el titular el 25-09-2026 en una captura de la pestaña: la
    cabecera llevaba el signo en azul y la pestaña, el cuadro plata con el
    signo en blanco. Eran dos marcas, y esta prueba solo comparaba las copias
    del favicon entre sí. Ahora lo compara con la máscara de `.marca::before`:
    los mismos trazos, con el mismo grosor y los mismos remates."""
    icono, cabecera = _icono(), _mascara_de_la_cabecera()
    assert _trazos(icono) == _trazos(cabecera), (
        f"el favicon dibuja {_trazos(icono)} y la cabecera {_trazos(cabecera)}")
    for atributo in ("stroke-width", "stroke-linecap", "stroke-linejoin"):
        assert _atributo(icono, atributo) == _atributo(cabecera, atributo), (
            f"el favicon lleva otro {atributo} que la cabecera")
    assert PLATA[1:] not in icono.lower() and "<rect" not in icono, (
        "el favicon vuelve a llevar el cuadro: la cabecera no lo lleva")


def test_el_favicon_se_pinta_con_los_acentos_de_la_hoja():
    """La cabecera pinta el signo con `--acento`, que cambia con el tema. El
    favicon es una imagen y no ve la hoja, así que lleva los dos colores
    escritos con su propio `prefers-color-scheme`, y tienen que ser esos dos.
    Uno solo sería el azul oscuro sobre una barra de pestañas de noche."""
    estilo = re.search(r"<style>(.*?)</style>", _icono(), re.S)
    assert estilo, "el favicon no lleva estilo, así que no cambia con el tema"
    noche = re.search(r"@media \(prefers-color-scheme:\s*dark\)\s*\{(.*)\}",
                      estilo[1], re.S)
    assert noche, "el favicon no tiene color de noche"
    dia_icono = re.findall(r"stroke:\s*(#[0-9a-fA-F]{6})", estilo[1][:noche.start()])
    noche_icono = re.findall(r"stroke:\s*(#[0-9a-fA-F]{6})", noche[1])
    dia, de_noche = _acentos()
    assert [c.lower() for c in dia_icono] == [dia], (dia_icono, dia)
    assert [c.lower() for c in noche_icono] == [de_noche], (noche_icono, de_noche)


def test_el_recorte_del_favicon_no_corta_el_dibujo():
    """El favicon recorta el signo a su tinta, para que a 16 px sea todo lo
    grande que puede. Un recorte que se comiera un remate sería otro dibujo,
    y a ese tamaño no se vería hasta tenerlo en la pestaña."""
    icono = _icono()
    x0, y0, ancho, alto = (float(v) for v in _atributo(icono, "viewBox").split())
    assert ancho == alto, "el favicon no es cuadrado y el navegador lo encoge"
    medio = float(_atributo(icono, "stroke-width")) / 2
    for trazo in _trazos(icono):
        x = y = 0.0
        for orden, valor in re.findall(r"([MHVhv])\s*([-\d.]+(?:\s+[-\d.]+)?)", trazo):
            numeros = [float(v) for v in valor.split()]
            if orden == "M":
                x, y = numeros
            elif orden == "H":
                x = numeros[0]
            elif orden == "V":
                y = numeros[0]
            elif orden == "h":
                x += numeros[0]
            else:
                y += numeros[0]
            assert x0 <= x - medio and x + medio <= x0 + ancho, (trazo, x)
            assert y0 <= y - medio and y + medio <= y0 + alto, (trazo, y)


@pytest.mark.parametrize("pagina", PAGINAS)
def test_cada_pagina_lleva_el_nombre_para_quien_no_ve_el_dibujo(pagina):
    """El nombre de la cabecera es texto, y es el que lee un lector de pantalla.

    La cabecera es `<a class="marca"><span class="nombre">Glosa-e</span></a>`:
    el signo lo pone la hoja de estilo y el nombre, este span. Estuvo escondido
    mientras el nombre iba dibujado dentro del bloque; si alguien lo quita, el
    enlace se queda sin nombre para quien ve y para quien no.
    """
    texto = (RAIZ / "web" / pagina).read_text(encoding="utf-8")
    assert '<span class="nombre">Glosa-e</span>' in texto, (
        f"En {pagina} la marca se ha quedado sin nombre accesible.")
