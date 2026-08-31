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


# --- El menú -----------------------------------------------------------------
# Las cinco páginas llevan el mismo menú copiado, porque no hay plantilla que
# lo monte: se sirven tal cual están en `web/`, y en desarrollo se abren desde
# el repositorio sin construir nada. Copiado no es problema; copiado y
# **divergiendo**, sí: se toca una página, se olvida otra, y el sitio empieza a
# decir que tiene cosas distintas según por dónde se entre. Nadie ve el fallo,
# porque cada página por separado está bien.
#
# Se comprueba letra por letra a propósito. «Que estén los mismos enlaces» deja
# pasar un texto cambiado en una sola, que es justo la forma en que esto se
# rompe de verdad.
PAGINAS = ("index.html", "banco.html", "legal.html", "incidencias.html",
           "tesis.html")
PRINCIPIO, FIN = "<!-- MENU", "<!-- FIN MENU -->"


def _menu_de(pagina: Path) -> str:
    texto = pagina.read_text(encoding="utf-8")
    assert PRINCIPIO in texto and FIN in texto, (
        f"«{pagina.name}» se ha quedado sin el menú: entre {PRINCIPIO}… y "
        f"{FIN} es donde va, y ahí no hay nada.")
    return texto[texto.index(PRINCIPIO):texto.index(FIN) + len(FIN)]


def test_el_menu_es_el_mismo_en_las_cinco_paginas():
    menus = {p: _menu_de(RAIZ / "web" / p) for p in PAGINAS}
    referencia = menus["index.html"]
    distintas = [p for p, m in menus.items() if m != referencia]
    assert not distintas, (
        "el menú de la portada y el de "
        + ", ".join(f"«{p}»" for p in distintas)
        + " ya no son el mismo. Se copia entero, no se retoca en una sola: "
        "quien entre por esa página verá un sitio distinto del que ve quien "
        "entre por otra.")


def test_el_menu_no_apunta_a_paginas_que_no_existen():
    """Un menú con un enlace roto es peor que uno corto: manda a un 404."""
    import re

    menu = _menu_de(RAIZ / "web" / "index.html")
    for destino in re.findall(r'href="\./([^"#]+)"', menu):
        assert (RAIZ / "web" / destino).is_file(), (
            f"el menú lleva a «{destino}» y ese fichero no está en web/")


# --- La ficha de quien esta detras -------------------------------------------
# Desde que la pagina se identifica, hay dos puertas donde antes habia una:
# `hayIdentificacion()` -nombre y correo- enciende la ficha del aviso legal, y
# `puedeVender()` -ademas, NIF y domicilio- enciende la seccion comercial.
#
# Separarlas resolvio un problema real, pero abre otro: es facil, tocando esto
# con prisa, dejar la tienda colgando de la puerta floja. Entonces la pagina
# ofreceria un servicio de pago sin decir quien lo ofrece, que es exactamente lo
# que el articulo 10 de la LSSI no permite, y no fallaria nada.
GLOSA_JS = RAIZ / "web" / "glosa.js"
PORTADA = RAIZ / "web" / "index.html"
LEGAL = RAIZ / "web" / "legal.html"


def _ficha() -> dict:
    """Lo que dice el literal TITULAR de `glosa.js`, campo a campo."""
    codigo = GLOSA_JS.read_text(encoding="utf-8")
    dentro = codigo[codigo.index("const TITULAR = {"):]
    dentro = dentro[:dentro.index("};")]
    return dict(re.findall(r'(\w+):\s*"([^"]*)"', dentro))


def test_no_se_puede_encender_la_tienda_sin_la_ficha_entera():
    codigo = GLOSA_JS.read_text(encoding="utf-8")
    cuerpo = codigo[codigo.index("function puedeVender()"):]
    cuerpo = cuerpo[:cuerpo.index("}")]
    for campo in ("nombre", "nif", "domicilio", "correo"):
        assert f"TITULAR.{campo}" in cuerpo, (
            f"`puedeVender()` ya no mira TITULAR.{campo}. Los cuatro son lo que "
            "el articulo 10 de la LSSI pide antes de cobrar; si sobra uno, la "
            "seccion comercial puede encenderse sin el.")

    portada = PORTADA.read_text(encoding="utf-8")
    assert "if (Glosa.puedeVender()) {" in portada, (
        "la seccion comercial de la portada ya no cuelga de `puedeVender()`")
    encendido = portada[portada.index("if (Glosa.puedeVender()) {"):]
    encendido = encendido[:encendido.index("\n}")]
    assert '$("escalon").hidden = false;' in encendido, (
        "el escalon comercial se enciende fuera del `if (Glosa.puedeVender())`")


def test_si_la_pagina_se_identifica_la_privacidad_dice_quien_responde():
    """Publicar un correo de contacto y no decir quien trata los datos, no.

    El RGPD pide identificar al responsable del tratamiento. Mientras la ficha
    estuvo vacia no habia nada que decir; desde que hay nombre y correo, la
    politica tiene que llevarlos, y los lleva de la misma fuente que el aviso
    legal para que no puedan decir cosas distintas.
    """
    ficha = _ficha()
    if not (ficha.get("nombre") and ficha.get("correo")):
        pytest.skip("la ficha esta vacia: no hay nada que publicar todavia")

    legal = LEGAL.read_text(encoding="utf-8")
    for hueco in ('id="p-responsable"', 'id="p-correo"'):
        assert hueco in legal, (
            f"la politica de privacidad ya no tiene {hueco}, asi que no dice "
            "quien responde del tratamiento")
    assert '$("p-responsable").textContent = t.nombre;' in legal, (
        "el responsable ya no se rellena desde la ficha de glosa.js, y dos "
        "sitios que dicen quien esta detras acaban diciendo cosas distintas")


def test_el_menu_escribe_a_la_direccion_de_la_ficha():
    """La única copia de la dirección que no sale de `glosa.js`.

    El menú es HTML plano en cinco páginas, y dos de ellas -el catálogo y la
    tesis- no cargan `glosa.js` a propósito: son páginas de consulta y no
    arrastran el validador para pintar una tabla. Asi que el correo del menú va
    escrito, no inyectado, y esa es la única forma de que exista una segunda
    copia de la dirección.

    Una dirección en dos sitios se separa el día que se cambia una. Aquí no
    puede: si dejan de decir lo mismo, esto se queja. Y si la ficha se vacía, el
    menú no puede seguir mandando correo a nadie.
    """
    correo = _ficha().get("correo", "")
    menu = _menu_de(RAIZ / "web" / "index.html")
    escritos = re.findall(r'href="mailto:([^"?]+)', menu)

    if not correo:
        assert not escritos, (
            "la ficha de `glosa.js` no tiene correo y el menú sigue llevando "
            f"{escritos}: manda a escribir a una dirección que ya no es de nadie")
        return

    assert escritos == [correo], (
        f"el menú escribe a {escritos} y la ficha de `glosa.js` dice "
        f"«{correo}». Son la misma dirección o no son nada: quien cambie una "
        "tiene que cambiar la otra.")
