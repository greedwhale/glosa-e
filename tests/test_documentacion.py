# -*- coding: utf-8 -*-
"""Las cifras que el README afirma tienen que ser las de hoy.

Esto empezó con una cifra vieja. El README decía «985 tests, todos en verde» y
eran 1017. Nadie mintió: el número se escribió cuando era cierto y se quedó
ahí, que es lo que hacen los números escritos a mano.

Y en este repositorio esa cifra no es decoración. La primera pantalla del
README es la tabla de módulos terminados y el número de pruebas debajo: es lo
que sostiene «terminado». Un producto cuya tesis es *no afirmar de más* no
puede tener en la primera pantalla una afirmación que se ha quedado atrás.

La solución es la de siempre aquí: que no se pueda, en vez de pedir que
alguien se acuerde.
"""

import re
import subprocess
import sys

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
README = RAIZ / "README.md"

# «985 tests, todos en verde.» El número y su unidad, tal cual está escrito.
PATRON = r"^(\d+) tests, todos en verde\.$"


def cuantas_pruebas_hay() -> int:
    """Cuenta las pruebas recolectando de verdad, en otro proceso.

    Se podría mirar `request.session.testscollected`, que sale gratis, y sería
    un error: ese número es el de la ejecución **actual**. Quien corriera
    `pytest tests/test_nif.py` recolectaría cuarenta y pico y esta prueba
    diría que el README miente. Ha de contar la suite entera pase lo que pase,
    y para eso hay que recolectarla entera.

    `--collect-only` no ejecuta nada, así que no hay recursión: el proceso de
    dentro recoge nombres y sale.
    """
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=RAIZ, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip("no se ha podido recolectar la suite en un subproceso; "
                    "sin eso esta comprobación no puede saber nada")
    hallado = re.search(r"^(\d+) tests collected", r.stdout, re.M)
    if not hallado:
        pytest.skip("pytest ha cambiado el formato de `--collect-only -q` y "
                    "esta comprobación ya no sabe leerlo")
    return int(hallado.group(1))


def test_el_readme_dice_cuantas_pruebas_hay_de_verdad():
    lineas = README.read_text(encoding="utf-8").splitlines()
    afirmadas = [(n, int(m.group(1)))
                 for n, l in enumerate(lineas, 1)
                 if (m := re.match(PATRON, l.strip()))]

    assert len(afirmadas) == 1, (
        f"En el README hay {len(afirmadas)} líneas que afirman un número de "
        "pruebas y tiene que haber una. Si se ha añadido otra, esta "
        "comprobación no puede saber cuál vigilar.")

    linea, dice = afirmadas[0]
    hay = cuantas_pruebas_hay()
    assert dice == hay, (
        f"README.md:{linea} dice «{dice} tests» y hay {hay}. No es un fallo "
        f"de código: es una cifra que se quedó atrás. Cámbiala a {hay}.")
