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
