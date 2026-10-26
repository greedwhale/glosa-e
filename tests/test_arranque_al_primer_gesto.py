# -*- coding: utf-8 -*-
"""La portada y el banco arrancan el validador al primer gesto, no al abrirse.

Medido el 26-10-2026 en Search Console: la prueba en directo, y con ella
Solicitar indexación, fallaba con "Se ha producido un error" en las dos
páginas que bajaban el validador al abrirse (unos 10 MB) y salía bien en Sobre
Glosa-e y en el aviso legal, que no lo bajan. El robot que hace esa prueba no
mueve el ratón ni toca nada. Si una de las dos vuelve a arrancar al abrirse,
no falla nada aquí ni en el navegador: se vuelve a cerrar la puerta de Google
sin que nadie se entere. Esto lo mira en el código.
"""
from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


def _sin_comentarios(texto: str) -> str:
    return re.sub(r"//[^\n]*", "", re.sub(r"<!--.*?-->", "", texto, flags=re.S))


def test_la_portada_arranca_al_primer_gesto():
    texto = _sin_comentarios((WEB / "index.html").read_text(encoding="utf-8"))
    assert "Glosa.alPrimerGesto(() => { elArranque = empezar(); });" in texto, (
        "la portada ya no arranca el validador al primer gesto")
    # La otra es la de reserva, dentro de `soltar`, por si algo llega a soltar
    # sin gesto delante.
    assert texto.count("elArranque = empezar()") == 2, (
        "la portada llama a `empezar()` desde un sitio nuevo: si es al abrirse, "
        "Search Console vuelve a fallar en ella")


def test_el_banco_arranca_al_primer_gesto():
    texto = _sin_comentarios((WEB / "banco.html").read_text(encoding="utf-8"))
    assert texto.count("Glosa.arrancar(") == 1
    assert "Glosa.alPrimerGesto(() => Glosa.arrancar(" in texto, (
        "el banco ya no arranca el validador al primer gesto")


def test_el_desplazamiento_solo_no_cuenta_como_gesto():
    """`scroll` lo dispara también la página, al abrir una pregunta por su
    ancla: con él en la lista, abrir `./#preguntas` arrancaría sin persona."""
    texto = (WEB / "glosa.js").read_text(encoding="utf-8")
    gestos = re.search(r"const GESTOS = \[([^\]]*)\]", texto)
    assert gestos, "glosa.js ya no declara GESTOS como se espera"
    lista = re.findall(r'"([a-z]+)"', gestos.group(1))
    assert "scroll" not in lista
    assert {"pointerdown", "keydown", "touchstart"} <= set(lista)
