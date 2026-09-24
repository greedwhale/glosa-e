# -*- coding: utf-8 -*-
"""Lo que se ve en un móvil: ninguna página de lado, y la portada en su orden.

El orden de la portada va al final, con su propio porqué.

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


# --- El orden de la portada ------------------------------------------------
#
# A 375x812 no caben en una pantalla el testigo y la zona de soltar, así que
# hubo que elegir qué va primero, y el 23-09-2026 se eligió **el testigo** —lo
# dice el comentario de arriba de `index.html`: la respuesta a «¿adónde va
# esto?» en la primera pantalla—. La ficha, que estaba entre los dos, bajó
# detrás de la herramienta.
#
# Primero se hizo con `display: contents` y `order`, y el orden que se veía ya
# no era el del documento. Desde la portada B, ese mismo día, el documento ya
# está en ese orden: la ficha va debajo de la herramienta también en ancho. Así
# que esto mira el documento, y que nada lo reordene por encima.

# Las piezas, con lo que las marca en index.html, en el orden en que se leen.
PIEZAS = [
    ("titular", "<h1>"),
    ("lema", '<p class="lema">'),
    ("testigo", '<aside class="testigo"'),
    ("herramienta", '<section id="herramienta"'),
    ("ficha", '<dl class="ficha">'),
    ("resto", '<section id="que-mira">'),
]


def _reglas_de_index() -> list[tuple[str, str]]:
    """(selector, declaraciones) de cada regla de la hoja de index.html."""
    texto = (WEB / "index.html").read_text(encoding="utf-8")
    estilo = re.sub(r"/\*.*?\*/", "", re.search(r"<style>(.*?)</style>", texto, re.S)[1],
                    flags=re.S)
    return [(" ".join(s.split()), c) for s, c in re.findall(r"([^{}]+)\{([^{}]*)\}", estilo)]


def test_la_portada_se_lee_en_el_orden_del_documento():
    texto = (WEB / "index.html").read_text(encoding="utf-8")
    donde = {}
    for nombre, marca in PIEZAS:
        assert texto.count(marca) == 1, f"index.html lleva {texto.count(marca)} «{marca}»"
        donde[nombre] = texto.index(marca)
    se_lee = sorted(donde, key=donde.get)
    assert se_lee == [nombre for nombre, _ in PIEZAS], (
        "La portada está escrita en este orden: " + ", ".join(se_lee) + ". "
        "El testigo va delante de la herramienta por decisión —el comentario de "
        "arriba de index.html— y la ficha detrás, antes que las secciones.")


def test_nada_reordena_la_portada_por_encima_del_documento():
    """El tabulador sigue el documento; la vista tiene que seguirlo también.

    `display: contents` era lo que dejaba a `order` mover la ficha por encima
    de su sitio. Si vuelve alguno de los dos sobre las piezas de la portada, lo
    que se ve y lo que recorre el teclado dejan de ser lo mismo.
    """
    piezas = (".portada", ".presenta", ".testigo", "#herramienta", ".ficha", ".lema", "h1")
    malas = [selector for selector, cuerpo in _reglas_de_index()
             if any(p in selector for p in piezas)
             and re.search(r"(?<![\w-])order:|display:\s*contents", cuerpo)]
    assert not malas, f"estas reglas reordenan la portada: {malas}"
