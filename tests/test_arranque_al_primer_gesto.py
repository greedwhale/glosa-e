# -*- coding: utf-8 -*-
"""La portada y el banco arrancan el validador al primer gesto, no al abrirse.

Medido el 26-10-2026 en Search Console: la prueba en directo, y con ella
Solicitar indexación, fallaba con "Se ha producido un error" en las dos
páginas que bajaban el validador al abrirse (unos 10 MB) y salía bien en Sobre
Glosa-e y en el aviso legal, que no lo bajan. El robot que hace esa prueba sí
mueve el ratón, pero no toca, ni pulsa, ni gira la rueda. Si una de las dos vuelve a arrancar al abrirse,
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


# Lo que hizo el robot de la prueba en directo sin que nadie lo tocara, medido
# el 26-10-2026 con una página que solo apuntaba lo que le llegaba: los cuatro
# primeros a los 121 ms y una vez cada uno, y `resize` dos veces. `scroll` no
# lo hizo él, pero lo hace la página sola al abrir una pregunta por su ancla:
# con él en la lista, abrir `./#preguntas` arrancaría sin persona.
LO_QUE_HACE_SIN_PERSONA = {
    "pointerover", "mouseover", "pointermove", "mousemove", "resize", "scroll",
}


def _gestos() -> list[str]:
    texto = (WEB / "glosa.js").read_text(encoding="utf-8")
    gestos = re.search(r"const GESTOS = \[([^\]]*)\]", texto)
    assert gestos, "glosa.js ya no declara GESTOS como se espera"
    return re.findall(r'"([a-z]+)"', gestos.group(1))


def test_ningun_gesto_es_de_los_que_hace_el_robot():
    """Con `pointermove` en la lista, el 26-10-2026 la portada y el banco
    seguían fallando en Search Console: el robot mueve el ratón."""
    sobran = LO_QUE_HACE_SIN_PERSONA & set(_gestos())
    assert not sobran, (
        f"{sorted(sobran)} lo dispara la prueba en directo de Google sin que nadie "
        "toque la página: el validador arrancaría mientras la lee y la prueba "
        "volvería a fallar")


def test_quedan_los_gestos_de_una_persona():
    assert {"pointerdown", "keydown", "touchstart"} <= set(_gestos())
