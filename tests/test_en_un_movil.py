# -*- coding: utf-8 -*-
"""Que ninguna página se salga de lado en un móvil.

Por qué existe
--------------
El 23-09-2026 se midieron las 399 páginas del sitio montado a 320 px, que es
el ancho con que WCAG mide el reflujo. Se salían por la derecha tres clases de
página, y siempre por lo mismo: **algo que no se puede partir por un espacio**.

| Página | Cuánto | Qué |
|---|---|---|
| `incidencias.html` | 109 px, 285 de 390 fichas | la línea del fuente en mono y la URN del anexo en la prosa |
| `codigo-*.html` | 40 de 390 páginas | la línea del fuente en «Lo escribe» |
| la entrada de la copia fiel | 7 px | `TotalGrossAmountBeforeTaxes`, en negrita |

En un móvil, una página que se sale obliga a leer cada renglón arrastrando de
lado, y el catálogo es a donde llega quien acaba de ver un código en un
informe y no sabe qué hacer con él.

Aquí no hay navegador, así que esto no mide píxeles: vigila que cada plantilla
siga dejando partir lo que no cabe, y con **cuál** de las dos maneras. No son
intercambiables, y la diferencia se midió:

- `anywhere` hace que la rejilla cuente la palabra como partible al medir su
  columna. Es lo que hace falta en las fichas, que son rejillas: con
  `break-word` la página seguía saliéndose los mismos 109 px.
- `break-word` sólo parte al pintar. Es lo que hace falta en la bitácora,
  porque sus tablas se desplazan dentro de `.cuadro`, y con `anywhere` encogían
  partiendo palabras —dos celdas de la segunda tabla de la copia fiel—.

El arreglo se vio en el navegador: 0 px en las 399.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"


def _regla(plantilla: str, selector: str) -> str:
    """El cuerpo de la regla de ese selector, fuera de cualquier @media."""
    estilo = re.search(r"<style>(.*?)</style>", (WEB / plantilla).read_text(
        encoding="utf-8"), re.S)
    assert estilo, f"{plantilla} ya no lleva su <style>"
    # Sólo lo que está a primer nivel: una regla dentro de un @media no vale
    # para todos los anchos, y la de aquí tiene que valer siempre.
    nivel, suelto, trozo = 0, [], []
    for letra in estilo[1]:
        if letra == "{":
            nivel += 1
        if nivel <= 1:
            trozo.append(letra)
        if letra == "}":
            nivel -= 1
            if nivel == 0:
                suelto.append("".join(trozo))
                trozo = []
    reglas = [r for r in suelto
              if re.sub(r"/\*.*?\*/", "", r, flags=re.S).strip().startswith(selector + " {")]
    assert len(reglas) == 1, (
        f"En {plantilla} hay {len(reglas)} reglas «{selector}» a primer nivel "
        "y esta prueba espera una")
    return re.sub(r"/\*.*?\*/", "", reglas[0], flags=re.S)


@pytest.mark.parametrize("plantilla, selector, como", [
    ("incidencias.html", ".codigo-ficha", "anywhere"),
    ("incidencias.html", ".ficha-codigo", "anywhere"),
    ("bitacora.html", "article.entrada", "break-word"),
])
def test_lo_que_no_cabe_se_deja_partir(plantilla, selector, como):
    cuerpo = _regla(plantilla, selector)
    dice = re.search(r"overflow-wrap:\s*([\w-]+)", cuerpo)
    assert dice, (
        f"{selector} en {plantilla} ya no deja partir lo que no cabe. A 320 px "
        "eso sacaba la página de su ancho: mira el docstring de esta prueba.")
    assert dice[1] == como, (
        f"{selector} en {plantilla} lleva overflow-wrap: {dice[1]} y tiene que "
        f"ser {como}. No son lo mismo: mira el docstring de esta prueba.")

