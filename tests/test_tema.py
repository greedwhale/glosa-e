# -*- coding: utf-8 -*-
"""El botón de tema claro u oscuro de la cabecera, desde el 27-10-2026.

Lo pidió el titular: cambiar de tema sin salir de la página. Son tres piezas
que se pueden separar sin que nada dé error, y cada una tiene aquí su prueba:

- el guion del `<head>`, copiado en las ocho páginas, que pone el tema elegido
  antes de pintar y atiende al botón;
- las dos copias forzadas de la paleta en `glosa.css`, que tienen que decir lo
  mismo que los dos bloques que copian, porque `test_contraste` solo mide los
  originales;
- la frase del aviso legal, porque guardar la elección en el navegador era lo
  único que la política decía que no se hacía.

Lo que no se puede mirar aquí, porque no hay navegador en la suite, se midió
en el panel el día que entró y está en HALLAZGOS.
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"
HOJA = WEB / "glosa.css"
PAGINAS = ("index.html", "banco.html", "legal.html", "incidencias.html",
           "sobre.html", "bitacora.html", "novedades.html", "404.html")
PRINCIPIO, FIN = "<!-- TEMA:", "<!-- FIN TEMA -->"


def _texto(nombre: str) -> str:
    return (WEB / nombre).read_text(encoding="utf-8")


def _guion_de(nombre: str) -> str:
    texto = _texto(nombre)
    assert PRINCIPIO in texto and FIN in texto, (
        f"«{nombre}» se ha quedado sin el guion del tema: el botón no haría nada "
        "y la página no recordaría lo elegido en las demás")
    cabeza = texto[:texto.index("</head>")]
    assert FIN in cabeza, f"en «{nombre}» el guion del tema ya no va en el <head>"
    return texto[texto.index(PRINCIPIO):texto.index(FIN) + len(FIN)]


def test_el_guion_es_el_mismo_en_las_ocho():
    referencia = _guion_de("index.html")
    distintas = [p for p in PAGINAS if _guion_de(p) != referencia]
    assert not distintas, (
        "el guion del tema ya no es el mismo en " + ", ".join(distintas) +
        ": se copia entero desde la portada, no se retoca en una sola")


def test_el_boton_va_en_el_menu():
    """En el bloque del menú, que `test_documentacion` exige igual en las
    ocho: así el botón no puede faltar en una sin que esa prueba lo diga."""
    texto = _texto("index.html")
    menu = texto[texto.index("<!-- MENU"):texto.index("<!-- FIN MENU -->")]
    assert '<button type="button" class="tema"' in menu, (
        "el botón de tema ya no está dentro del menú de la cabecera")


def test_sin_codigo_no_se_ve():
    hoja = HOJA.read_text(encoding="utf-8")
    assert re.search(r"^\.tema \{ display: none; \}", hoja, re.M), (
        "el botón de tema se ve aunque no haya código que lo atienda")
    assert ':root[data-con-tema] .tema {' in hoja
    assert 'raiz.setAttribute("data-con-tema", "");' in _guion_de("index.html")


def test_solo_se_guarda_claro_u_oscuro():
    guion = _guion_de("index.html")
    escrituras = re.findall(r"localStorage\.setItem\(([^)]*)\)", guion)
    assert escrituras == ['"glosa-e:tema", nuevo'], escrituras
    assert 'var nuevo = oscuro() ? "claro" : "oscuro";' in guion
    assert 'elegido === "claro" || elegido === "oscuro"' in guion, (
        "se aplica lo guardado sin mirar que sea una de las dos palabras")


def _declaraciones(bloque: str) -> dict[str, str]:
    return {k: v.strip() for k, v in re.findall(r"(--[\w-]+):\s*([^;]+);", bloque)}


def test_las_copias_forzadas_dicen_lo_mismo_que_sus_bloques():
    hoja = HOJA.read_text(encoding="utf-8")
    claro = _declaraciones(re.search(r":root \{(.*?)\n\}", hoja, re.S)[1])
    oscuro = _declaraciones(re.search(
        r"@media \(prefers-color-scheme: dark\) \{\s*:root \{(.*?)\}", hoja, re.S)[1])
    forzado_claro = _declaraciones(re.search(
        r':root\[data-tema="claro"\] \{(.*?)\}', hoja, re.S)[1])
    forzado_oscuro = _declaraciones(re.search(
        r':root\[data-tema="oscuro"\] \{(.*?)\}', hoja, re.S)[1])
    assert forzado_oscuro == oscuro, (
        "el tema oscuro elegido con el botón ya no es el del sistema")
    assert set(forzado_claro) == set(oscuro), (
        "el tema claro elegido no redefine lo mismo que el oscuro: con el "
        "sistema de noche, lo que falte se quedaría oscuro")
    assert forzado_claro == {k: claro[k] for k in forzado_claro}, (
        "el tema claro elegido con el botón ya no es el de la hoja")


def test_ninguna_pagina_tiene_noche_propia():
    """Una regla con su propio `prefers-color-scheme` no se entera del botón.

    Así estaban los dos botones llenos de la portada, y con el sistema de
    noche y la página en claro pintaban letra casi negra sobre azul oscuro.
    El favicon es la excepción: es una imagen y el navegador la pinta con el
    tema de su barra, no con el de la página.
    """
    for nombre in PAGINAS:
        sin_icono = re.sub(r'<link rel="icon"[^>]*>', "", _texto(nombre))
        assert "prefers-color-scheme" not in sin_icono.replace(
            _guion_de(nombre), ""), (
            f"«{nombre}» tiene una regla de noche propia, que el botón de tema "
            "no puede apagar: pásala a un token de glosa.css")


def test_el_aviso_legal_dice_lo_que_se_guarda():
    legal = _texto("legal.html")
    assert "tu navegador guarda esa elección" in legal, (
        "el botón de tema guarda una palabra en el navegador y el aviso legal "
        "ya no lo dice: la política volvería a prometer que no se guarda nada")


def test_la_lista_del_menu_se_ancla_a_la_barra():
    """Visto por el titular en un Android el 27-10-2026, con el botón ya
    publicado: la lista del menú se cortaba por la izquierda. Se anclaba al
    borde derecho de la pestaña, y la pestaña dejó de ser lo último de la
    barra. Medido a 393 px: empezaba en -23 px; anclada a la barra, de 24 a
    369, el mismo borde derecho que el botón de tema. A 320 px, de 24 a 296."""
    hoja = HOJA.read_text(encoding="utf-8")
    assert re.search(r"^\.barra \{ position: relative; \}", hoja, re.M), (
        "la barra ya no es el ancla de la lista del menú")
    # Todas las reglas `.menu`, que hay más de una: la primera es la que la
    # esconde en ancho, y mirando solo esa la prueba no vigilaba nada.
    menus = re.findall(r"^\s*\.menu \{([^}]*)\}", hoja, re.M)
    assert len(menus) >= 2, menus
    assert not any("position" in m for m in menus), (
        "la pestaña vuelve a ser el ancla de la lista: con el botón de tema a "
        "su derecha, en el móvil se corta por la izquierda")
    lista = re.search(r"^\.menu > nav \{([^}]*)\}", hoja, re.M)[1]
    assert "right: 1.5rem;" in lista, (
        "la lista del menú ya no acaba en el margen derecho de la barra")
