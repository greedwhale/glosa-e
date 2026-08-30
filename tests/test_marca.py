# -*- coding: utf-8 -*-
"""La marca no se puede desviar en silencio de lo que sirve la página.

El dibujo vive en tres sitios y ninguno se lee desde otro:

  `web/marca/glosa-e.svg`   el original, que genera `web/marca/trazar.py`
  `web/glosa.css`           el mismo dibujo, incrustado como `data:` URI
  los tres `.html`          el favicon, que es **otro** dibujo: a 16 px el
                            nombre no cabe y la pestaña lleva el signo solo

Tres copias de algo de 5 KB se acaban separando. Y la forma en que se separan
es la peor de todas: no rompen nada. La página sigue cargando, sale todo verde,
y la portada enseña una marca y el aviso legal otra hasta que alguien lo ve
publicado.

Estas pruebas no comprueban que la marca sea bonita. Comprueban que sea **la
misma**, que es lo único que una prueba puede saber de un dibujo.
"""

import importlib.util
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

PATRON_FONDO = (r'background: url\("(data:image/svg\+xml,[^"]+)"\)'
                r' center / contain no-repeat;')
PATRON_FAVICON = r'<link rel="icon" href="(data:image/svg\+xml,[^"]+)">'


def _trazar():
    """Carga `web/marca/trazar.py` sin que sea un módulo instalable.

    Se carga por ruta, y no se copia aquí su función de escapado, porque dos
    copias de una regla de escape se separan igual que se separan dos copias de
    un dibujo. Si la prueba tuviera la suya, compararía su idea de la url
    contra sí misma y diría que todo cuadra pasara lo que pasara.
    """
    ruta = RAIZ / "web" / "marca" / "trazar.py"
    spec = importlib.util.spec_from_file_location("trazar_marca", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_svg_original_esta_donde_dice_estar():
    assert SVG.is_file(), (
        "Falta web/marca/glosa-e.svg. Sin él, la marca es un blob de 5 KB "
        "dentro de una hoja de estilo y no hay forma de retocarla.")


def test_la_hoja_de_estilo_lleva_el_mismo_dibujo_que_el_original():
    """El fondo de `.marca` tiene que ser exactamente el SVG de al lado."""
    hoja = HOJA.read_text(encoding="utf-8")
    fondos = re.findall(PATRON_FONDO, hoja)
    assert len(fondos) == 1, (
        f"Hay {len(fondos)} fondos de marca en glosa.css y tiene que haber "
        "uno: la marca vive ahí una sola vez a propósito, para que las tres "
        "páginas no puedan llevar dibujos distintos.")

    esperada = _trazar().url_de_css(SVG.read_text(encoding="utf-8"))
    assert fondos[0] == esperada, (
        "El dibujo de glosa.css y el de web/marca/glosa-e.svg ya no son el "
        "mismo. Vuelve a correr `python web/marca/trazar.py Literata.ttf`, "
        "que escribe los dos.")


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
    """El nombre está dibujado; esto es lo que queda para un lector de pantalla.

    La cabecera es `<a class="marca"><span class="nombre">Glosa-e</span></a>`
    con el span escondido visualmente. Si alguien quita el span porque «no se
    ve», la marca deja de tener nombre para quien no ve el dibujo.
    """
    texto = (RAIZ / "web" / pagina).read_text(encoding="utf-8")
    assert '<span class="nombre">Glosa-e</span>' in texto, (
        f"En {pagina} la marca se ha quedado sin nombre accesible.")
