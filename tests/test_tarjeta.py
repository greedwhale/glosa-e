# -*- coding: utf-8 -*-
"""La tarjeta social que se publica es la que pinta hoy su guion.

Por qué existe
--------------
`web/marca/tarjeta.png` se versiona ya hecha y `herramientas/tarjeta.py` está
para rehacerla. El 23-09-2026 la hoja cambió de gris, el guion se puso al día
—`tests/test_contraste.py` lo exige— y el PNG no: regenerarlo pedía bajar
Literata, y se quedó con el gris viejo hasta el 24-09-2026. Nada se rompía;
la tarjeta que ve quien pega el enlace decía una cosa y la hoja otra.

Desde ese día el guion pinta con la Literata que sirve la página, sin bajar
nada, y esto lo vigila: pinta la tarjeta y la compara con la publicada. Medido
al escribirlo: 0 píxeles distintos con la de hoy, 5475 con la del gris viejo.

Pillow no es dependencia del proyecto, así que donde no está —en GitHub— la
comparación se salta. La del titular no la necesita y corre siempre.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
GUION = RAIZ / "herramientas" / "tarjeta.py"
PUBLICADA = RAIZ / "web" / "marca" / "tarjeta.png"

# Lo que se tolera: un cambio de versión de FreeType puede mover algún píxel
# del suavizado de los bordes. Un color de la hoja cambia miles.
UMBRAL, TOLERADOS = 2, 100


def test_la_tarjeta_publicada_es_la_que_pinta_el_guion(monkeypatch):
    pytest.importorskip("PIL")
    from PIL import Image, ImageChops

    monkeypatch.chdir(RAIZ)   # el guion busca la letra desde la raíz
    monkeypatch.syspath_prepend(str(RAIZ))
    from herramientas import tarjeta

    pintada = tarjeta.dibujar(str(tarjeta.LETRA))
    publicada = Image.open(PUBLICADA).convert("RGB")
    assert publicada.size == pintada.size == (1200, 630)
    distintos = sum(1 for p in ImageChops.difference(pintada, publicada).get_flattened_data()
                    if max(p) > UMBRAL)
    assert distintos <= TOLERADOS, (
        f"web/marca/tarjeta.png no es la que pinta hoy su guion: {distintos} "
        "píxeles distintos. Rehazla desde la raíz con "
        "`python -m herramientas.tarjeta`; ya no hay que bajar nada.")


def test_la_tarjeta_dice_el_titular_de_la_portada():
    """El guion dice que el titular es el de la portada, palabra por palabra."""
    guion = GUION.read_text(encoding="utf-8")
    portada = (RAIZ / "web" / "index.html").read_text(encoding="utf-8")
    h1 = re.search(r"<h1>(.*?)</h1>", portada, re.S)[1].replace("<br>", " ")
    lema = re.search(r'<p class="lema"><b>(.*?)</b>', portada, re.S)[1]
    lineas = re.findall(r'dibujo\.text\(\(MARGEN, \d+\), "([^"]+)", font=titular', guion)
    assert " ".join(lineas) == " ".join(h1.split()), (
        f"la tarjeta dice «{' '.join(lineas)}» y la portada «{h1}»")
    assert f'"{lema}"' in guion, f"la tarjeta ya no lleva el lema de la portada: «{lema}»"


def _constantes_del_guion() -> dict:
    """Las cifras de la marca de `tarjeta.py`, leídas sin importarlo.

    Importarlo pide Pillow, y esta comparación tiene que correr también donde
    no está —en GitHub—: es aritmética sobre dos textos.
    """
    valores = {}
    for nodo in ast.parse(GUION.read_text(encoding="utf-8")).body:
        if isinstance(nodo, ast.Assign):
            for destino in nodo.targets:
                nombres = destino.elts if isinstance(destino, ast.Tuple) else [destino]
                try:
                    valor = ast.literal_eval(nodo.value)
                except ValueError:
                    continue
                if len(nombres) == 1:
                    valores[nombres[0].id] = valor
                else:
                    valores.update({n.id: v for n, v in zip(nombres, valor)})
    return valores


def _trazos(d: str) -> list[tuple[tuple[float, float], ...]]:
    """Los trazos de un `d` de SVG con M, H, V, h y v, que es lo que usa el signo."""
    trazos, actual, x, y = [], [], 0.0, 0.0
    for orden, cifras in re.findall(r"([MHVhv])\s*([-\d.\s]+)", d):
        n = [float(c) for c in cifras.split()]
        if orden == "M":
            if actual:
                trazos.append(tuple(actual))
            x, y = n
            actual = [(x, y)]
            continue
        if orden == "H":
            x = n[0]
        elif orden == "V":
            y = n[0]
        elif orden == "h":
            x += n[0]
        elif orden == "v":
            y += n[0]
        actual.append((x, y))
    trazos.append(tuple(actual))
    return trazos


def test_la_marca_de_la_tarjeta_es_la_de_la_cabecera():
    """La marca de la tarjeta sale de las cifras de `.marca` en la hoja.

    Hasta el 24-09-2026 la tarjeta pintaba la marca del favicon —el bloque
    gris, dos líneas blancas, el nombre en 400— y la cabecera, desde el
    23-09-2026, el signo en azul con tres líneas y el nombre en 600. Nadie lo
    vio porque las dos se escriben en sitios distintos. Aquí se comparan.
    """
    hoja = (RAIZ / "web" / "glosa.css").read_text(encoding="utf-8")
    guion = _constantes_del_guion()

    antes = re.search(r"^\.marca::before \{(.*?)^\}", hoja, re.S | re.M)[1]
    mascara = re.search(r'mask: url\("data:image/svg\+xml,([^"]+)"\)', antes)[1]
    mascara = mascara.replace("%3C", "<").replace("%3E", ">")
    caja = [float(c) for c in re.search(r"viewBox='([^']+)'", mascara)[1].split()]
    assert tuple(caja[2:]) == guion["SIGNO_CAJA"], "la caja del signo no es la de la hoja"
    trazos = [t for d in re.findall(r"d='([^']+)'", mascara) for t in _trazos(d)]
    assert trazos == [tuple(map(tuple, t)) for t in guion["SIGNO_TRAZOS"]], (
        f"la tarjeta dibuja otro signo que la cabecera:\n  hoja:    {trazos}\n"
        f"  tarjeta: {guion['SIGNO_TRAZOS']}")
    assert float(re.search(r"stroke-width='([\d.]+)'", mascara)[1]) == guion["SIGNO_GROSOR"]
    assert "background: var(--acento)" in antes, "el signo de la cabecera ya no es del acento"
    assert re.search(r"signo: str = ACENTO", GUION.read_text(encoding="utf-8")), (
        "el signo de la tarjeta ya no se pinta en el acento")
    rem = lambda propiedad: float(re.search(propiedad + r":\s*([\d.]+)rem", antes)[1])
    assert (rem("width"), rem("height")) == guion["SIGNO_REM"]

    marca = re.search(r"^\.marca \{(.*?)^\}", hoja, re.S | re.M)[1]
    assert float(re.search(r"gap:\s*([\d.]+)rem", marca)[1]) == guion["HUECO_REM"]
    nombre = re.search(r"^\.marca \.nombre \{(.*?)\}", hoja, re.S | re.M)[1]
    peso, tamano = re.search(r"font:\s*(\d+)\s+([\d.]+)rem", nombre).groups()
    assert (int(peso), float(tamano)) == (guion["NOMBRE_PESO"], guion["NOMBRE_REM"])
    espaciado = float(re.search(r"letter-spacing:\s*(-?[\d.]+)em", nombre)[1])
    assert espaciado == guion["NOMBRE_ESPACIADO"]
