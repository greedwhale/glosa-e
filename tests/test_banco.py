# -*- coding: utf-8 -*-
"""El banco del navegador, corrido aquí también.

Por qué existe
--------------
El 6 de septiembre de 2026 se desplegó a producción con **tres comprobaciones
críticas del banco en rojo**, y la suite estaba en verde. Las 1.106 pruebas
pasaban mientras `una factura correcta sale conforme` fallaba en la página
publicada, porque las reglas de línea nuevas —BR-22, BR-23 y BR-26— saltaban
sobre unos ejemplos a los que nadie les había puesto la cantidad ni el precio.

El agujero no era el fallo: era que **el banco vivía fuera del alcance de
`pytest`**. `web/prueba.py` está escrito para que lo ejecute Pyodide dentro del
navegador, así que nada de lo que hay aquí lo tocaba, y lo único que podía
delatarlo era que a alguien se le ocurriera abrir `/banco` y mirar. Se
desplegó dos veces antes de que eso pasara.

Lo que esto comprueba, y lo que no
-----------------------------------
**Sí:** que los 38 casos del banco pasan con este código y con los ejemplos que
hay en `ejemplos/` ahora mismo. Eso es lo que se rompió, y es lo que a partir
de ahora se rompe en rojo y en tres segundos en vez de en producción.

**No:** que el banco pase *dentro del navegador*. Aquí corre CPython con el
lxml del sistema, y allí corre Pyodide con una compilación de libxml2 para
WebAssembly que puede traer otras cosas —de hecho medio banco existe justo para
comprobar eso, que la canonicalización y los esquemas XSD estén dentro—. Las
dos comprobaciones son distintas y ninguna sustituye a la otra: la del
navegador sigue estando en `/banco` y en el ritual de `comprobar-produccion`.

`web/prueba.py` no se importa, se ejecuta: está escrito para Pyodide, que le
pasa el fichero entero y se queda con `resultados`. Aquí se hace lo mismo.
"""
from __future__ import annotations

import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
BANCO = RAIZ / "web" / "prueba.py"


@pytest.fixture(scope="module")
def resultados(tmp_path_factory) -> list[dict]:
    """Corre el banco entero una vez y reparte sus resultados.

    `scope="module"` porque tarda unos tres segundos y las dos pruebas de aquí
    miran lo mismo desde dos ángulos: no hay razón para pagarlo dos veces.
    """
    import os

    anterior = os.environ.get("EJEMPLOS")
    # El banco busca los ejemplos donde se los pongan; en el navegador es la
    # ruta del sitio y aquí es la carpeta del repositorio.
    os.environ["EJEMPLOS"] = str(RAIZ / "ejemplos")
    try:
        espacio: dict = {"__name__": "banco"}
        exec(compile(BANCO.read_text(encoding="utf-8"), str(BANCO), "exec"),
             espacio)
        return espacio["resultados"]
    finally:
        if anterior is None:
            os.environ.pop("EJEMPLOS", None)
        else:
            os.environ["EJEMPLOS"] = anterior


def test_el_banco_corre_entero(resultados):
    """Que no se quede a medias: un banco truncado no falla, calla."""
    declaradas = BANCO.read_text(encoding="utf-8").count("\n@comprobar(")
    assert len(resultados) == declaradas, (
        f"el banco declara {declaradas} comprobaciones y solo han corrido "
        f"{len(resultados)}. Una que ni siquiera llega a ejecutarse no sale "
        "en rojo: desaparece."
    )
    assert declaradas >= 38, (
        f"el banco tiene {declaradas} comprobaciones y antes tenía 38. Si se "
        "ha quitado alguna, que sea a propósito."
    )


def test_ninguna_comprobacion_del_banco_falla(resultados):
    """El guardián. Esto es lo que estaba en rojo en producción con la suite verde."""
    fallan = [r for r in resultados if not r["ok"]]
    criticas = [r for r in fallan if r.get("critica")]
    assert not fallan, (
        f"{len(fallan)} de {len(resultados)} comprobaciones del banco fallan"
        + (f", {len(criticas)} de ellas críticas" if criticas else "")
        + ". Esto es lo que ve quien abre /banco en la página publicada.\n\n"
        + "\n\n".join(
            f"--- {r['nombre']}{' (CRÍTICA)' if r.get('critica') else ''}\n"
            + str(r.get("detalle") or "")
            for r in fallan
        )
    )
