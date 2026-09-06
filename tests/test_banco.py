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
def espacio() -> dict:
    """Ejecuta el banco entero una vez y deja ver todo lo que definió.

    `scope="module"` porque tarda unos tres segundos y las pruebas de aquí
    miran lo mismo desde varios ángulos: no hay razón para pagarlo cada vez.

    Se devuelve el espacio de nombres completo y no solo `resultados` porque
    el banco también define cosas que aquí se vuelven a correr con **el otro
    libxml2** —la tabla de `FORMA_ESPERADA`—, y eso es la mitad del valor de
    tener el banco dentro del alcance de pytest.
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
        return espacio
    finally:
        if anterior is None:
            os.environ.pop("EJEMPLOS", None)
        else:
            os.environ["EJEMPLOS"] = anterior


@pytest.fixture(scope="module")
def resultados(espacio) -> list[dict]:
    return espacio["resultados"]


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


# --- La misma tabla, con el otro libxml2 -----------------------------------
#
# El banco provoca trece incumplimientos de forma y comprueba que `esquema.py`
# los traduce a su código. Allí eso corre con libxml2 2.9.10; aquí, con
# 2.11.9. Las regex de la traducción se escribieron mirando lo que dice esta
# versión, así que **esta prueba es la que no puede fallar**: si falla, el
# fallo es de la tabla y no del navegador, y allí no habría manera de saberlo.


def test_los_incumplimientos_de_forma_se_traducen_igual_aqui(espacio):
    """Con el libxml2 de fuera, la tabla del banco tiene que dar lo mismo."""
    fallos = [
        f"{nombre}: se esperaba {list(esperados) or 'nada'} y salió "
        f"{list(obtenidos) or 'nada'}"
        for nombre, esperados, obtenidos in espacio["_provocar_forma"]()
        if obtenidos != esperados
    ]
    assert not fallos, (
        "la tabla de `FORMA_ESPERADA` del banco no cuadra con este libxml2:\n"
        + "\n".join(fallos)
        + "\n\nSi esto falla aquí, la tabla está mal escrita. El caso "
        "interesante es el contrario: que pase aquí y falle en /banco, que "
        "significa que las dos compilaciones de libxml2 redactan distinto y "
        "que en el navegador los errores de forma salen en inglés."
    )


def _codigos_que_traducir_puede_sacar() -> set[str]:
    """Los códigos que salen de traducir un mensaje de libxml2, leídos del AST.

    Del módulo entero no vale: `XSD-SIN-ESQUEMA`, `XSD-NO-APLICA` y
    `XSD-ESQUEMA-ROTO` los pone `reglas()` y no dependen de cómo redacte
    libxml2. Los que dependen son exactamente los que nacen dentro de
    `traducir()`.
    """
    import ast

    arbol = ast.parse((RAIZ / "validador" / "esquema.py").read_text(
        encoding="utf-8"))
    funcion = next(n for n in ast.walk(arbol)
                   if isinstance(n, ast.FunctionDef) and n.name == "traducir")
    return {
        n.args[0].value
        for n in ast.walk(funcion)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name) and n.func.id == "Incidencia"
        and n.args and isinstance(n.args[0], ast.Constant)
        and isinstance(n.args[0].value, str)
    }


def test_la_tabla_del_banco_provoca_todos_los_codigos_de_la_traduccion(espacio):
    """Una regex nueva sin provocación en el banco es un hueco que no se ve.

    Ese es el modo de fallo entero de esto: alguien añade la traducción de un
    mensaje más, la prueba con el libxml2 de aquí, y en el navegador ese
    mensaje sale en inglés. No se rompe nada; se degrada, y solo allí.
    """
    provocados = {c for caso in espacio["FORMA_ESPERADA"] for c in caso[2]}
    # `XSD-OTRO` es la salida de emergencia: no se provoca porque es
    # justamente lo que no tiene que salir. Que aparezca donde iba otra cosa
    # es la señal de que esto se ha roto.
    faltan = sorted(_codigos_que_traducir_puede_sacar() - provocados - {"XSD-OTRO"})
    assert not faltan, (
        f"`traducir()` puede sacar {', '.join(faltan)} y el banco no lo "
        "provoca. Sin provocarlo, nadie sabe si el libxml2 del navegador "
        "redacta ese mensaje igual: saldría como `XSD-OTRO`, en inglés y solo "
        "en la página. Añade el caso a `FORMA_ESPERADA` en `web/prueba.py`."
    )
    assert "XSD-OTRO" not in provocados, (
        "la tabla del banco espera un `XSD-OTRO`. Ese código es la rendición "
        "de la traducción: esperarlo convierte el guardián en su contrario."
    )
