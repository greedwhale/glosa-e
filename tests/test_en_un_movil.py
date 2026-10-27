# -*- coding: utf-8 -*-
"""Lo que se ve en un móvil: ninguna página de lado, y la portada en su orden.

El orden de la portada, el del folio y el pie del testigo van al final, cada
uno con su propio porqué.

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
from html.parser import HTMLParser
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
# que esto mira el documento, y que nada lo reordene por encima. Dentro del
# folio sí se mueve algo en estrecho, y eso va aparte, más abajo.

# Las piezas, con lo que las marca en index.html, en el orden en que se leen.
PIEZAS = [
    ("titular", "<h1>"),
    ("lema", '<p class="lema">'),
    ("testigo", '<aside class="testigo"'),
    ("herramienta", '<section id="herramienta"'),
    ("ficha", '<dl class="ficha">'),
    ("resto", '<section id="que-hace">'),
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


# --- El folio, en estrecho ---------------------------------------------------
#
# La portada B puso la zona de soltar dentro de un folio, debajo de tres glosas
# de muestra. En ancho van al lado del titular y la zona queda a 503 px; en una
# columna, las glosas ocupaban 765 px delante de ella y la zona empezaba a 2,05
# pantallas de un móvil de 375×812 —antes de la portada B, a 1,22—. A 768×1024
# asomaban 62 de sus 159 px.
#
# En estrecho el folio pone la zona delante. Es la única excepción a «nada
# reordena la portada», y es posible porque lo que se mueve no se puede
# enfocar: el tabulador recorre lo que se ve en el orden en que se ve.

ENFOCABLE = {"a", "button", "input", "select", "textarea", "summary", "details", "iframe"}


class _HijosDelFolio(HTMLParser):
    """Los hijos directos de `.folio`, en orden, y si hay algo enfocable en cada uno."""

    VACIAS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
              "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.hondo = 0
        self.folio = None
        self.acabado = False
        self.hijos: list[list] = []   # [clase, enfocable]

    def handle_starttag(self, etiqueta, atributos):
        atributos = dict(atributos)
        clases = (atributos.get("class") or "").split()
        if self.folio is None and not self.acabado and "folio" in clases:
            self.folio = self.hondo
        elif self.folio is not None and self.hondo > self.folio:
            if self.hondo == self.folio + 1:
                self.hijos.append([clases[0] if clases else etiqueta, False])
            if etiqueta in ENFOCABLE or "tabindex" in atributos:
                self.hijos[-1][1] = True
        if etiqueta not in self.VACIAS:
            self.hondo += 1

    def handle_endtag(self, etiqueta):
        if etiqueta in self.VACIAS:
            return
        self.hondo -= 1
        if self.folio is not None and self.hondo == self.folio:
            self.folio, self.acabado = None, True   # cerrado: no se cuenta nada más


def _hijos_del_folio() -> list[tuple[str, bool]]:
    lector = _HijosDelFolio()
    lector.feed((WEB / "index.html").read_text(encoding="utf-8"))
    assert lector.hijos, "index.html ya no tiene .folio, o está vacío"
    return [tuple(h) for h in lector.hijos]


def _bloque(hoja: str, cabecera: str) -> str:
    """Lo que hay dentro de la regla-@ que empieza por `cabecera`."""
    assert hoja.count(cabecera) == 1, f"la hoja lleva {hoja.count(cabecera)} «{cabecera}»"
    principio = hoja.index("{", hoja.index(cabecera)) + 1
    nivel, i = 1, principio
    while nivel:
        nivel += {"{": 1, "}": -1}.get(hoja[i], 0)
        i += 1
    return hoja[principio:i - 1]


def _hoja_de_index() -> str:
    texto = (WEB / "index.html").read_text(encoding="utf-8")
    return re.sub(r"/\*.*?\*/", "", re.search(r"<style>(.*?)</style>", texto, re.S)[1],
                  flags=re.S)


def _como_se_ve_en_estrecho() -> list[tuple[str, bool]]:
    """Los hijos del folio en el orden en que se pintan a 54rem o menos."""
    estrecho = _bloque(_hoja_de_index(), "@media (max-width: 54rem)")
    folio = re.search(r"(?<![\w-])\.folio\s*\{([^}]*)\}", estrecho)
    assert folio and re.search(r"display:\s*flex", folio[1]), (
        "en estrecho .folio ya no es flex, y sin eso el order de sus hijos no "
        "hace nada: la zona vuelve a quedar debajo de las glosas")
    orden = {}
    for clase, _ in _hijos_del_folio():
        dice = re.search(r"\.folio \." + re.escape(clase) + r"\s*\{[^}]*?(?<![\w-])order:\s*(-?\d+)",
                         estrecho)
        orden[clase] = int(dice[1]) if dice else 0
    hijos = _hijos_del_folio()
    return sorted(hijos, key=lambda h: orden[h[0]])   # sorted es estable, como order


def test_en_estrecho_la_zona_va_antes_que_las_glosas():
    se_ve = [clase for clase, _ in _como_se_ve_en_estrecho()]
    assert {"suelta", "muestra"} <= set(se_ve), f"el folio ya no es el que era: {se_ve}"
    assert se_ve.index("suelta") < se_ve.index("muestra"), (
        f"En estrecho el folio se ve así: {se_ve}. Con las glosas delante, la "
        "zona de soltar empezaba a 2,05 pantallas de un móvil: mira el "
        "comentario de «El folio, en estrecho» en esta prueba.")


def test_lo_que_se_mueve_en_el_folio_no_se_enfoca():
    """El tabulador sigue el documento y la vista tiene que seguirlo también.

    Se puede mover lo que no tiene nada enfocable; lo que sí lo tiene, tiene
    que verse en el orden del documento.
    """
    en_el_documento = [clase for clase, enfocable in _hijos_del_folio() if enfocable]
    se_ve = [clase for clase, enfocable in _como_se_ve_en_estrecho() if enfocable]
    assert se_ve == en_el_documento, (
        f"en estrecho el tabulador recorre {en_el_documento} y la vista enseña "
        f"{se_ve}: ahora hay algo enfocable en un bloque que se mueve")


def test_el_order_solo_se_usa_en_el_folio():
    malas = [selector for selector, cuerpo in _reglas_de_index()
             if re.search(r"(?<![\w-])order:", cuerpo) and not selector.startswith(".folio .")]
    assert not malas, (
        f"estas reglas mueven algo fuera del folio: {malas}. La única excepción "
        "al orden del documento es la del folio, y la prueba de arriba la vigila.")


# --- El pie del testigo ------------------------------------------------------
#
# La propuesta 5 del README: en el móvil, el testigo en tres filas y un enlace
# a lo que ha pedido la página, para que la zona entre en la primera pantalla
# sin quitarlo de delante. Medido a 375×812: la zona, de 626 a 610 px con el
# pie plegado y un poco menos de aire, entera en la pantalla también mientras
# carga. En ancho el pie va abierto, porque su nota es la que dice lo que el
# testigo no alcanza a ver.


def test_el_pie_del_testigo_sale_plegado_y_lo_abre_la_hoja_en_ancho():
    texto = (WEB / "index.html").read_text(encoding="utf-8")
    pie = re.search(r'<details class="pie" id="tg-pie"([^>]*)>(.*?)</aside>', texto, re.S)
    assert pie, "el pie del testigo ya no es un <details class=\"pie\" id=\"tg-pie\">"
    assert "open" not in pie[1], (
        "el pie sale abierto: el móvil lo pinta y lo recoge después, y la zona "
        "salta. Sale cerrado y lo abre la hoja en ancho.")
    for dentro in ('id="tg-propias"', 'id="tg-lista-caja"', 'class="nota"'):
        assert dentro in pie[2], f"«{dentro}» ya no va dentro del pie del testigo"

    ancho = _bloque(_bloque(_hoja_de_index(), "@supports selector(::details-content)"),
                    "@media (width > 34rem)")
    abre = re.search(r"\.testigo \.pie::details-content\s*\{([^}]*)\}", ancho)
    assert abre and re.search(r"content-visibility:\s*visible", abre[1]), (
        "en ancho nada abre el pie del testigo, y la nota —lo que no alcanza a "
        "ver— queda escondida detrás de un toque también en escritorio")
    assert re.search(r"\.testigo \.pie > summary\s*\{[^}]*display:\s*none", ancho), (
        "en ancho el pie va abierto y su rótulo de plegar no tiene que verse")
    assert "@media (max-width: 34rem)" in _hoja_de_index(), (
        "el móvil de esta hoja ya no se corta en 34rem, y el pie se abre en "
        "ancho a partir de ahí: hay que moverlos juntos")


def test_el_rotulo_del_folio_va_dentro_del_corchete():
    """A 393 px el rótulo del folio empezaba en 12 px y el corchete ocupa de
    9,6 a 17,6: la E de ERROR caía encima del trazo (visto en un Android el
    27-10-2026, y medido en el panel). El relleno del folio pesa más que el del
    móvil, así que el móvil tiene que decir el suyo para el folio. Con 1,6rem
    el rótulo empieza en 26 px, y a media altura del corchete."""
    texto = (RAIZ / "web" / "index.html").read_text(encoding="utf-8")
    estrecho = texto[texto.index("@media (max-width: 34rem) {\n  .glosa {"):]
    estrecho = estrecho[:estrecho.index("\n}\n")]
    regla = re.search(r"\.folio \.glosa \.margen \{([^}]*)\}", estrecho)
    assert regla, "en estrecho el folio ya no le da relleno propio al margen"
    assert re.search(r"padding:\s*\S+\s+\S+\s+\S+\s+1\.6rem", regla[1]), (
        "el rótulo del folio vuelve a empezar encima del corchete")
    assert "align-self: center" in regla[1], (
        "el rótulo del folio ya no va a media altura del corchete")
