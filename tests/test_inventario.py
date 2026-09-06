# -*- coding: utf-8 -*-
"""Lo que existe contra lo que alguien mira.

Por qué existe
--------------
El 6 de septiembre de 2026 aparecieron tres agujeros en un día, y los tres eran
la misma cosa con distinta cara: **algo que existía y no estaba en ninguna
cuenta**.

- El banco: 38 comprobaciones que `pytest` no corría, tres de ellas en rojo en
  producción durante dos despliegues.
- El catálogo: 26 códigos que el lector se saltaba en silencio.
- Los ejemplos: ocho de diez sin cantidad ni precio, porque solo se arreglaron
  los que rompían pruebas.

Ninguno salió en rojo. Los tres los encontró alguien mirando, y por eso el
arreglo de cada uno no basta: lo que falta es que **una cosa nueva sin nadie
que la mire no pueda entrar sin enterarse**. De eso va este fichero.

Cómo funciona, y qué no es
--------------------------
No mide cobertura. Mide algo mucho más tonto y mucho más difícil de engañar:
**si alguien nombra esa cosa en alguna parte**. Un módulo que ningún test
menciona, un ejemplo que se publica en el sitio y no aparece en ninguna
comprobación, una página en `web/` que el montador no mete. Es un listón bajo a
propósito: por debajo de él no hay ninguna duda de que nadie está mirando.

Cada lista de excepciones está escrita, con su porqué. Eso las hace visibles y
contables, que es lo único que separa un hueco conocido de uno que nadie sabe
que está. Si algo entra y no está cubierto, esto se pone en rojo y dice las dos
salidas: cubrirlo, o declararlo sabiendo lo que se declara.
"""
from __future__ import annotations

import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent

# Módulos que ninguna prueba nombra por su nombre, y por qué se acepta.
# Vacía a propósito: hoy no hay ninguno. Si mañana lo hay, que cueste
# escribirlo aquí y explicarlo.
MODULOS_SIN_PRUEBA: dict[str, str] = {}

# Ejemplos que ninguna comprobación mira. También vacía: un ejemplo se publica
# en el sitio y lo abre gente que está decidiendo si fiarse, así que uno que
# nadie valida es peor que no tenerlo.
EJEMPLOS_SIN_COMPROBAR: dict[str, str] = {}


def _todo_lo_que_mira() -> str:
    """El texto de todo lo que comprueba algo: las pruebas y el banco.

    El banco cuenta porque corre de verdad —en el navegador y, desde el
    06-09-2026, también aquí— y porque fue justamente el sitio donde se vio lo
    que las pruebas no veían.
    """
    trozos = [p.read_text(encoding="utf-8", errors="replace")
              for p in sorted((RAIZ / "tests").glob("test_*.py"))]
    trozos.append((RAIZ / "web" / "prueba.py").read_text(
        encoding="utf-8", errors="replace"))
    return "\n".join(trozos)


def test_todo_modulo_lo_nombra_alguna_prueba():
    """Un módulo que ningún test menciona no lo está mirando nadie."""
    import re

    mira = _todo_lo_que_mira()
    huerfanos = []
    for ruta in sorted((RAIZ / "validador").glob("*.py")):
        nombre = ruta.stem
        if nombre.startswith("__"):
            continue  # `__init__` y `__main__` no se nombran, se ejecutan
        if nombre in MODULOS_SIN_PRUEBA:
            continue
        # Basta con que aparezca como `validador.x` o en un `from validador
        # import x`: no se pide una prueba dedicada, solo que exista alguien
        # que lo toque.
        if not re.search(
            rf"validador[.\s]+{nombre}\b|validador import[^\n]*\b{nombre}\b",
            mira,
        ):
            huerfanos.append(nombre)

    assert not huerfanos, (
        "estos módulos de validador/ no los nombra ninguna prueba ni el "
        f"banco: {', '.join(huerfanos)}.\n"
        "No es una queja de cobertura: es que si se rompen, nada se entera. "
        "O los toca alguna prueba, o se añaden a MODULOS_SIN_PRUEBA con el "
        "motivo escrito."
    )


def test_todo_ejemplo_lo_comprueba_alguien():
    """Un ejemplo se publica en el sitio; uno que nadie valida es una trampa."""
    mira = _todo_lo_que_mira()
    huerfanos = [
        e.name for e in sorted((RAIZ / "ejemplos").iterdir())
        if e.is_file()
        and e.name not in EJEMPLOS_SIN_COMPROBAR
        and e.name not in mira
    ]
    assert not huerfanos, (
        f"estos ejemplos no los nombra ninguna comprobación: "
        f"{', '.join(huerfanos)}.\n"
        "Van dentro del sitio publicado y los abre quien está decidiendo si "
        "fiarse. Los ocho que se quedaron sin cantidad ni precio en septiembre "
        "de 2026 eran exactamente estos: los que no rompían nada."
    )


def test_toda_pagina_de_web_la_monta_el_sitio():
    """Una página que el montador no nombra no llega a publicarse."""
    montador = (RAIZ / "validador" / "paquete.py").read_text(encoding="utf-8")
    # `pagina_incidencias.py` monta la suya aparte, por su plantilla.
    montador += (RAIZ / "validador" / "pagina_incidencias.py").read_text(
        encoding="utf-8")
    fuera = [h.name for h in sorted((RAIZ / "web").glob("*.html"))
             if h.name not in montador]
    assert not fuera, (
        f"estas páginas de web/ no las nombra quien monta el sitio: "
        f"{', '.join(fuera)}. Se escribirían, se versionarían y no llegarían "
        "a la dirección publicada, sin que nada fallara."
    )
