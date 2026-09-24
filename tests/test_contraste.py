# -*- coding: utf-8 -*-
"""Que todo color de texto se lea sobre todo fondo, en claro y en oscuro.

Por qué existe
--------------
El 23-09-2026 se midió el sitio en un móvil y en los dos temas, y el gris de
los rótulos y los pies, `--tenue`, no llegaba a AA en claro: 4,20:1 sobre
`--panel-2`, 4,10:1 sobre los fondos flojos del veredicto. WCAG pide 4,5 para
texto normal. En oscuro la página pasaba entera… mientras nadie arrastrase un
fichero encima de la zona, que se tiñe de `--acento-flojo` y deja el pie a
4,37:1. Eso no lo vio la medida sobre la página, porque la página medida no
tenía a nadie arrastrando nada.

Por eso aquí no se prueban las parejas que hoy existen, sino **todas**: cada
color de texto contra cada fondo. La pareja que hoy no se pinta la pone mañana
alguien sin mirar, y lo que no se puede leer no avisa.

La fórmula es la de WCAG 2.1 —luminancia relativa y (L1 + 0,05) / (L2 + 0,05)—,
la misma con que están calculadas las razones de la marca en MARCA.md.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
HOJA = RAIZ / "web" / "glosa.css"
TARJETA = RAIZ / "herramientas" / "tarjeta.py"

# Lo que se pinta como letra y sobre qué se pinta. Los bordes y la sombra no
# están: un filete no se lee.
TEXTOS = ["tinta", "tinta-2", "tenue", "acento", "error", "aviso", "nota", "bien"]
FONDOS = ["papel", "panel", "panel-2", "acento-flojo", "error-flojo",
          "aviso-flojo", "nota-flojo", "bien-flojo"]
AA = 4.5


def _colores(bloque: str) -> dict[str, str]:
    return {k: v.lower() for k, v in
            re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})\s*;", bloque)}


def _temas() -> dict[str, dict[str, str]]:
    hoja = HOJA.read_text(encoding="utf-8")
    claro = re.search(r":root\s*\{(.*?)\}", hoja, re.S)
    oscuro = re.search(
        r"@media \(prefers-color-scheme: dark\)\s*\{\s*:root\s*\{(.*?)\}",
        hoja, re.S)
    assert claro and oscuro, "glosa.css ya no tiene los dos :root que esta prueba lee"
    return {"claro": _colores(claro[1]), "oscuro": _colores(oscuro[1])}


def _luminancia(color: str) -> float:
    canales = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    canales = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
               for c in canales]
    return 0.2126 * canales[0] + 0.7152 * canales[1] + 0.0722 * canales[2]


def razon(a: str, b: str) -> float:
    mas, menos = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (mas + 0.05) / (menos + 0.05)


def test_la_formula_da_las_razones_que_publica_marca_md():
    """Si la fórmula estuviera mal, todo lo de abajo pasaría o fallaría en falso."""
    assert round(razon("#ffffff", "#949494"), 2) == 3.03
    assert round(razon("#000000", "#949494"), 2) == 6.92
    assert round(razon("#000000", "#ffffff"), 2) == 21.0


@pytest.mark.parametrize("tema", ["claro", "oscuro"])
def test_los_dos_temas_definen_todos_los_colores(tema):
    colores = _temas()[tema]
    faltan = [c for c in TEXTOS + FONDOS if c not in colores]
    assert not faltan, (
        f"El tema {tema} no define {', '.join(faltan)}: o se ha renombrado y "
        "esta prueba ya no mira lo que cree, o el tema hereda del otro un "
        "color pensado para el fondo contrario.")


@pytest.mark.parametrize("tema", ["claro", "oscuro"])
def test_todo_texto_se_lee_sobre_todo_fondo(tema):
    colores = _temas()[tema]
    cortos = [
        f"--{t} ({colores[t]}) sobre --{f} ({colores[f]}): "
        f"{razon(colores[t], colores[f]):.2f}:1"
        for t in TEXTOS for f in FONDOS
        if razon(colores[t], colores[f]) < AA
    ]
    assert not cortos, (
        f"En el tema {tema}, {len(cortos)} parejas no llegan a {AA}:1, que es "
        "lo que pide WCAG AA para texto normal:\n  " + "\n  ".join(cortos))


def test_la_tarjeta_pinta_con_los_colores_de_la_hoja():
    """`herramientas/tarjeta.py` copia los colores del tema claro a mano.

    Lo dice su propio comentario —«no se inventa ninguno»—, y el día que se
    cambió `--tenue` la copia se quedó en el gris viejo. Aquí se compara.
    """
    claro = set(_temas()["claro"].values())
    guion = TARJETA.read_text(encoding="utf-8")
    suyos = dict(re.findall(r'^([A-Z_0-9]+) = "(#[0-9a-fA-F]{6})"', guion, re.M))
    assert len(suyos) >= 5, "la prueba ya no encuentra los colores de la tarjeta"
    # Hasta el 24-09-2026 aquí se perdonaba `BLOQUE`, el gris del bloque de la
    # marca. La cabecera lo dejó el 23-09-2026 y la tarjeta el 24: si vuelve,
    # es la marca vieja, y tiene que salir aquí.
    ajenos = {k: v for k, v in suyos.items() if v.lower() not in claro}
    assert not ajenos, (
        "La tarjeta pinta con colores que glosa.css ya no tiene: "
        + ", ".join(f"{k} = {v}" for k, v in ajenos.items()))
