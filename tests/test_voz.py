# -*- coding: utf-8 -*-
"""Una sola voz: la del informe.

Hasta el 15-09-2026 la web hablaba en tres personas a la vez: «te decimos»,
«miramos», «lo que no nos gusta» y «Escríbenos» al lado de «Escríbeme» y
«dímelo». Y el informe decía «un método que no sabemos reproducir» en una línea
y «solo se sabe verificar RSA» en la siguiente. Una herramienta cuyo valor es
que se le pueda creer no puede sonar a tres autores distintos.

Se eligió la voz del informe, la impersonal —«se ha comprobado»—, y la primera
persona del singular **solo para el contacto**, porque quien contesta un correo
es una persona. Está escrito en MARCA.md, en el tono.

Lo que se vigila es la primera persona del plural y el vosotros, que es lo que
se cuela al escribir deprisa: en las páginas publicadas sin sus comentarios, en
el JavaScript que pinta textos, y en las cadenas del informe y del banco sin
sus docstrings. La red es de forma —-amos, -emos, -imos, -áis, -éis, nos,
nuestro— y por eso lleva lista de excepciones: una palabra que acaba igual y no
es un verbo se añade ahí, con su motivo, en vez de aflojar la red.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"

PAGINAS = sorted([WEB / p for p in ("index.html", "banco.html", "legal.html",
                                     "incidencias.html", "tesis.html", "bitacora.html")]
                 + list((WEB / "bitacora").glob("*.html")))

# La primera del plural y el vosotros, por su forma.
PLURAL = re.compile(
    r"\b(?:[a-záéíóúüñ]+(?:amos|emos|imos|áis|éis)|somos|sois|pedís|"
    r"nosotr[oa]s|vosotr[oa]s|nuestr[oa]s?|vuestr[oa]s?|nos)\b",
    re.IGNORECASE)
# Sin «os» suelto: el JavaScript lleva código Python en cadenas —`import os`— y
# la red gritaría por eso. El vosotros se caza por los verbos.

# Palabras que caen en la red sin ser de nadie. Cada una con su motivo.
NO_SON_VERBOS = {
    "tramos": "sustantivo: los tramos de una numeración que faltan",
}


def _sin_comentarios(texto: str) -> str:
    texto = re.sub(r"<!--.*?-->", " ", texto, flags=re.S)
    texto = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
    return re.sub(r"(?:^|\s)//[^\n]*", " ", texto)


def _cadenas_sin_docstrings(fuente: Path) -> list[str]:
    arbol = ast.parse(fuente.read_text(encoding="utf-8"))
    docstrings = set()
    for nodo in ast.walk(arbol):
        cuerpo = getattr(nodo, "body", None)
        if (isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and cuerpo and isinstance(cuerpo[0], ast.Expr)
                and isinstance(cuerpo[0].value, ast.Constant)
                and isinstance(cuerpo[0].value.value, str)):
            docstrings.add(id(cuerpo[0].value))
    return [n.value for n in ast.walk(arbol)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstrings]


def en_plural(texto: str) -> list[str]:
    return sorted({p for p in PLURAL.findall(texto) if p.lower() not in NO_SON_VERBOS})


def test_la_red_caza_lo_que_ya_se_colo():
    """Si la red no cazara esto, todo lo de abajo saldría verde sin mirar."""
    for frase in ("Suelta un fichero y te decimos qué pone",
                  "incluido lo que no nos gusta",
                  "Aplicamos las reglas y las comparamos",
                  "un método que no sabemos reproducir",
                  "¿Cuánto cuesta y qué datos pedís?",
                  "Volveremos a esto, porque nosotros la confundimos",
                  "los textos son nuestros"):
        assert en_plural(frase), frase
    assert not en_plural("Se ha comprobado. Escríbeme y dímelo, y lo corrijo.")


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.name)
def test_las_paginas_hablan_con_una_voz(pagina):
    encontradas = en_plural(_sin_comentarios(pagina.read_text(encoding="utf-8")))
    assert not encontradas, (
        f"«{pagina.name}» habla en plural: {', '.join(encontradas)}. La voz del "
        "sitio es la del informe —«se ha comprobado»—, y la primera persona "
        "del singular solo para el contacto. Si es una palabra que no es un "
        "verbo, va a NO_SON_VERBOS con su motivo.")


def test_el_javascript_que_pinta_textos_tambien():
    encontradas = en_plural(_sin_comentarios((WEB / "glosa.js").read_text(encoding="utf-8")))
    assert not encontradas, f"glosa.js habla en plural: {', '.join(encontradas)}"


@pytest.mark.parametrize(
    "fuente", sorted((RAIZ / "validador").glob("*.py")) + [WEB / "prueba.py"],
    ids=lambda p: p.name)
def test_el_informe_y_el_banco_tambien(fuente):
    encontradas = sorted({p for cadena in _cadenas_sin_docstrings(fuente)
                          for p in en_plural(cadena)})
    assert not encontradas, (
        f"«{fuente.name}» tiene mensajes en plural: {', '.join(encontradas)}. "
        "El informe dice «aquí no se sabe», no «no sabemos».")
