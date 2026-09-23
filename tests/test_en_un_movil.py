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


# --- El orden de la portada en estrecho ------------------------------------
#
# A 375x812 no caben en una pantalla el testigo y la zona de soltar, así que
# hubo que elegir qué va primero, y el 23-09-2026 se eligió **el testigo** —lo
# dice el comentario de arriba de `index.html`: la respuesta a «¿adónde va
# esto?» en la primera pantalla—. Lo que sí se movió es la ficha, que estaba
# entre los dos: baja detrás de la herramienta. La zona pasó de empezar a 1,59
# pantallas a 1,22, y a 768 px cabe entera en la primera.
#
# Se hace con `display: contents` y `order`, así que el orden que se ve ya no
# es el del documento. Sin navegador, esta prueba lo calcula como lo haría él:
# el `order` de cada pieza en la media query de estrecho, y a igual `order`,
# el orden del documento.

ESTRECHO = "@media (max-width: 54rem)"

# Las piezas, en el orden en que están escritas en index.html.
PIEZAS = [
    ("titular", ".portada h1"),
    ("lema", ".portada .lema"),
    ("testigo", ".testigo"),
    ("ficha", ".portada .ficha"),
    ("herramienta", "#herramienta"),
    ("resto", "#herramienta ~ *"),
]


def _estrecho() -> dict[str, str]:
    """Selector -> declaraciones, de la media query de estrecho de la portada."""
    texto = (WEB / "index.html").read_text(encoding="utf-8")
    estilo = re.search(r"<style>(.*?)</style>", texto, re.S)[1]
    estilo = re.sub(r"/\*.*?\*/", "", estilo, flags=re.S)
    assert estilo.count(ESTRECHO) == 1, (
        f"index.html tiene {estilo.count(ESTRECHO)} «{ESTRECHO}» y esta prueba "
        "espera una")
    desde = estilo.index("{", estilo.index(ESTRECHO)) + 1
    nivel, hasta = 1, desde
    while nivel:
        nivel += {"{": 1, "}": -1}.get(estilo[hasta], 0)
        hasta += 1
    reglas = {}
    for selectores, cuerpo in re.findall(r"([^{}]+)\{([^{}]*)\}", estilo[desde:hasta - 1]):
        for selector in selectores.split(","):
            reglas[" ".join(selector.split())] = reglas.get(
                " ".join(selector.split()), "") + cuerpo
    return reglas


def test_en_estrecho_la_ficha_va_detras_de_la_herramienta_y_el_testigo_delante():
    reglas = _estrecho()
    for contenedor in (".portada", ".portada .cuerpo"):
        assert re.search(r"display:\s*contents", reglas.get(contenedor, "")), (
            f"{contenedor} ya no es `display: contents` en estrecho, y sin eso "
            "el `order` de lo que lleva dentro no hace nada")
    assert re.search(r"display:\s*flex", reglas.get("main > .envoltorio", "")), (
        "el envoltorio ya no es flex en estrecho: el `order` no hace nada")

    def orden(selector):
        dice = re.search(r"(?<![\w-])order:\s*(-?\d+)", reglas.get(selector, ""))
        return int(dice[1]) if dice else 0

    se_ve = [nombre for _, (nombre, selector) in sorted(
        enumerate(PIEZAS), key=lambda par: (orden(par[1][1]), par[0]))]
    assert se_ve == ["titular", "lema", "testigo", "herramienta", "ficha", "resto"], (
        "En estrecho la portada se ve en este orden: " + ", ".join(se_ve) + ". "
        "El testigo va delante de la herramienta por decisión —el comentario de "
        "arriba de index.html— y la ficha detrás, antes que las secciones.")


def test_la_ficha_no_tiene_nada_que_se_pueda_pulsar():
    """Lo que hace que moverla con `order` no descoloque el teclado.

    El tabulador sigue el orden del documento, no el que se ve. Mientras la
    ficha no tenga nada enfocable, da igual dónde se pinte; el día que lleve un
    enlace, el foco saltaría de la zona de soltar hacia atrás, a la ficha, y
    habría que moverla en el HTML.
    """
    texto = (WEB / "index.html").read_text(encoding="utf-8")
    fichas = re.findall(r'<dl class="ficha">(.*?)</dl>', texto, re.S)
    assert len(fichas) == 1, f"index.html tiene {len(fichas)} fichas y esta prueba espera una"
    enfocable = re.search(r"<(a|button|input|select|textarea|summary)\b|tabindex=", fichas[0])
    assert not enfocable, (
        f"La ficha de la portada lleva «{enfocable[0]}». En estrecho se pinta "
        "detrás de la herramienta sin moverla en el documento, así que el foco "
        "del teclado ya no seguiría a lo que se ve.")
