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


# --- Las cifras que la página publica --------------------------------------
#
# El mismo problema, un piso más arriba. El libro blanco (`web/tesis.html`)
# publica cuatro cifras como argumento de credibilidad, y dos de ellas se
# mueven solas: los códigos de incidencia crecen cuando alguien añade una
# regla, y las comprobaciones del navegador cuando alguien añade una al banco.
#
# Una cifra vieja ahí es peor que en el README, porque el README lo lee quien
# trabaja en esto y la página la lee quien está decidiendo si fiarse.

TESIS = RAIZ / "web" / "tesis.html"
BANCO = RAIZ / "web" / "prueba.py"


def _cifra_de_la_tesis(rotulo: str) -> int:
    """La cifra que la página publica bajo ese rótulo."""
    texto = TESIS.read_text(encoding="utf-8")
    patron = (
        r"<dt>" + re.escape(rotulo) + r"</dt>\s*<dd>(\d+)"
    )
    hallado = re.search(patron, texto)
    assert hallado, f"«{rotulo}» ya no está en {TESIS.name} con la forma esperada"
    return int(hallado.group(1))


def test_la_tesis_dice_cuantos_codigos_hay_de_verdad():
    from validador.codigos import codigos_del_paquete

    hay = len(codigos_del_paquete())
    dice = _cifra_de_la_tesis("Códigos de aviso")
    assert dice == hay, (
        f"web/tesis.html dice «{dice} códigos de aviso» y hay {hay}. La página "
        f"la lee quien está decidiendo si fiarse. Cámbiala a {hay}.")


def test_la_tesis_dice_cuantas_comprobaciones_corre_el_navegador():
    # Se cuentan los decoradores del banco, que es donde están de verdad. La
    # otra forma sería correr el banco entero aquí, que necesita el paquete
    # montado y los ejemplos: esta prueba tiene que valer en un clon recién
    # bajado.
    hay = len(re.findall(r"^@comprobar\(", BANCO.read_text(encoding="utf-8"),
                         re.MULTILINE))
    dice = _cifra_de_la_tesis("Comprobaciones en tu navegador")
    assert dice == hay, (
        f"web/tesis.html dice «{dice} comprobaciones» y el banco tiene {hay}. "
        f"Cámbiala a {hay}.")


def test_el_catalogo_no_se_puede_publicar_vacio():
    """La plantilla tiene que llevar la marca donde se pega el catálogo.

    Si desaparece, montar el sitio no falla: publica una página de consulta con
    cero códigos y un título que dice que están todos.
    """
    from validador import pagina_incidencias

    plantilla = RAIZ / "web" / pagina_incidencias.NOMBRE
    assert plantilla.is_file(), "no está la plantilla del catálogo"
    assert pagina_incidencias.HUECO in plantilla.read_text(encoding="utf-8"), (
        f"«{plantilla.name}» ya no lleva {pagina_incidencias.HUECO}")
