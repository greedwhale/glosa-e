"""Un fallo de la página se le cuenta a dos personas, y no con las mismas palabras.

Hasta el 06-10-2026, si la página no arrancaba, quien la abría leía «No esta
el interprete en ./pyodide/. Traelo con `python -m validador
--traer-pyodide`»: sin tildes, con una ruta y con una orden de consola que no
puede dar. O «El validador (factura_e-0.1.0-py3-none-any.whl) no es lo que la
pagina dice traer: rueda.json publica 3f2a...». Lo que sí puede hacer es
recargar, y eso no lo decía ninguno.

Ahora `glosa.js` lanza esos fallos por `averia(paraQuienMira,
paraQuienMantiene)`: el mensaje dice qué ha pasado y que se recargue, y el
detalle va a la consola del navegador, que es donde lo busca quien mantiene la
página. La portada y el banco enseñan `error.message`, sin el «Error:» que
antepone `String`.

Aquí no hay navegador, así que lo que se comprueba es que siga escrito así.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"


def _sin_comentarios(texto: str) -> str:
    texto = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
    return re.sub(r"(?:^|\s)//[^\n]*", " ", texto)


def _codigo() -> str:
    return _sin_comentarios((WEB / "glosa.js").read_text(encoding="utf-8"))


def _argumentos(codigo: str, desde: int) -> list[str]:
    """Los argumentos de la llamada cuyo paréntesis abre justo antes de `desde`.

    Cuenta paréntesis y salta lo que va entre comillas: con una expresión
    regular, la coma de dentro de una cadena partiría el argumento.
    """
    nivel, actual, argumentos, comilla, i = 0, [], [], None, desde
    while i < len(codigo):
        c = codigo[i]
        if comilla:
            actual.append(c)
            if c == "\\":
                actual.append(codigo[i + 1])
                i += 1
            elif c == comilla:
                comilla = None
        elif c in "\"'`":
            comilla = c
            actual.append(c)
        elif c in "([{":
            nivel += 1
            actual.append(c)
        elif c in ")]}":
            if nivel == 0:
                argumentos.append("".join(actual).strip())
                return argumentos
            nivel -= 1
            actual.append(c)
        elif c == "," and nivel == 0:
            argumentos.append("".join(actual).strip())
            actual = []
        else:
            actual.append(c)
        i += 1
    raise AssertionError("una llamada sin cerrar en glosa.js")


def _averias() -> list[list[str]]:
    codigo = _codigo()
    return [_argumentos(codigo, m.end())
            for m in re.finditer(r"(?<!function )\baveria\(", codigo)]


# Lo que no le puede llegar a quien abre la página: rutas, ficheros que solo
# conoce quien la monta, huellas y órdenes de consola.
SOLO_PARA_QUIEN_MANTIENE = re.compile(
    r"python -m|rueda\.json|PAQUETE\.json|\.whl|\.zip|contesta|DIST|PYODIDE_EN"
    r"|direccion|publicada|medida|elWheel|clave")


def test_hay_averias_que_mirar():
    """Si la búsqueda dejara de encontrarlas, todo lo de abajo saldría verde."""
    assert len(_averias()) >= 7


def test_quien_mira_lee_que_recargue_y_nada_mas():
    for paraQuienMira, *resto in _averias():
        assert "RECARGA" in paraQuienMira, paraQuienMira
        assert not SOLO_PARA_QUIEN_MANTIENE.search(paraQuienMira), paraQuienMira
        assert len(resto) == 1 and resto[0], (
            f"una avería sin detalle para quien mantiene la página: {paraQuienMira}")


def test_el_detalle_va_a_la_consola_y_viaja_en_cause():
    codigo = _codigo()
    cuerpo = codigo.split("function averia(paraQuienMira, paraQuienMantiene) {")[1]
    cuerpo = cuerpo.split("\n}")[0]
    assert "console.error(" in cuerpo and "paraQuienMantiene" in cuerpo
    assert "new Error(paraQuienMira, { cause: paraQuienMantiene })" in cuerpo


# Los `new Error` que no pasan por `averia`, cada uno con su motivo.
SIN_AVERIA = {
    '"no está el zip"': "se caza en la línea siguiente, y deja la página sin "
                        "paquete diciéndolo en la ficha",
    '"\\"" + nombre': "lo lanza un botón de la propia página con un nombre que no "
                    "es de las muestras: es un fallo de quien la escribe",
    "paraQuienMira": "el de la propia `averia`",
}


def test_ningun_error_llega_a_la_pantalla_sin_pasar_por_averia():
    codigo = _codigo()
    sueltos = []
    for m in re.finditer(r"\bnew Error\(", codigo):
        primero = _argumentos(codigo, m.end())[0]
        if not any(primero.startswith(permitido) for permitido in SIN_AVERIA):
            sueltos.append(primero[:80])
    assert not sueltos, (
        "estos errores le llegan a quien abre la página sin pasar por `averia`:\n"
        + "\n".join(sueltos))


def test_las_paginas_ensenan_el_mensaje_sin_el_error_delante():
    portada = (WEB / "index.html").read_text(encoding="utf-8")
    assert "String(error)" not in _sin_comentarios(portada).replace(
        "|| String(error)", "")
    assert "const motivo = (error) => (error && error.message) || String(error);" in portada
    banco = (WEB / "banco.html").read_text(encoding="utf-8")
    assert '"No ha arrancado: " + (error.message || error)' in banco
