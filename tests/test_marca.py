# -*- coding: utf-8 -*-
"""La marca no se puede desviar en silencio de lo que sirve la página.

El dibujo vive en varios sitios y ninguno se lee desde otro:

  `web/marca/glosa-e.svg`   el bloque, que genera `web/marca/trazar.py`
  los tres `.html`          el favicon, que es **otro** dibujo: a 16 px el
                            nombre no cabe y la pestaña lleva el signo solo
  `web/glosa.css`           el signo de la cabecera, como máscara, que tiene
                            que ser el mismo que el de la zona de soltar

Hasta el 23-09-2026 la hoja llevaba además el bloque entero, que era la
cabecera. Ya no: la cabecera es el signo y el nombre en la letra de la página,
y el porqué está en `MARCA.md`.

Tres copias de algo de 5 KB se acaban separando. Y la forma en que se separan
es la peor de todas: no rompen nada. La página sigue cargando, sale todo verde,
y la portada enseña una marca y el aviso legal otra hasta que alguien lo ve
publicado.

Estas pruebas no comprueban que la marca sea bonita. Comprueban que sea **la
misma**, que es lo único que una prueba puede saber de un dibujo.
"""

import re

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
SVG = RAIZ / "web" / "marca" / "glosa-e.svg"
HOJA = RAIZ / "web" / "glosa.css"
PAGINAS = ["index.html", "banco.html", "legal.html"]

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


def test_el_favicon_es_el_mismo_en_las_tres_paginas():
    """Es un segundo dibujo, y son tres copias que hay que mantener iguales.

    A 16 px la palabra no cabe, así que la pestaña lleva el cuadro con el
    signo solo. Ese es el precio de haber metido el nombre dentro del bloque, y
    está aceptado. Lo que no se acepta es que las tres copias se separen.
    """
    encontrados = {}
    for nombre in PAGINAS:
        texto = (RAIZ / "web" / nombre).read_text(encoding="utf-8")
        iconos = re.findall(PATRON_FAVICON, texto)
        assert len(iconos) == 1, (
            f"En {nombre} hay {len(iconos)} favicons y tiene que haber uno.")
        encontrados[nombre] = iconos[0]

    distintos = set(encontrados.values())
    assert len(distintos) == 1, (
        "Las tres páginas llevan favicons distintos:\n  "
        + "\n  ".join(f"{p}: …{u[-40:]}" for p, u in encontrados.items()))

    # Y que sea el signo sobre la plata, no cualquier otra cosa que quepa.
    assert PLATA.lower() in distintos.pop().lower().replace("%23", "#"), (
        "El favicon no lleva la plata de la marca.")


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
