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

import ast
import hashlib
import html
import re
import subprocess
import sys
import tokenize

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


def _cifra_de_la_portada(patron: str) -> int:
    """La cifra que la portada publica con esa frase, sobre el texto con los
    saltos de línea reducidos a un espacio."""
    texto = " ".join(PORTADA.read_text(encoding="utf-8").split())
    hallados = re.findall(patron, texto)
    assert len(hallados) == 1, (
        f"«{patron}» aparece {len(hallados)} veces en la portada y tiene que "
        "aparecer una: si se ha reescrito la frase, este guardián está ciego")
    return int(hallados[0])


def test_la_portada_dice_cuantas_comprobaciones_corre_el_boton():
    hay = len(re.findall(r"^@comprobar\(", BANCO.read_text(encoding="utf-8"),
                         re.MULTILINE))
    dice = _cifra_de_la_portada(r'id="correr-banco" disabled>Correr las (\d+) aquí<')
    assert dice == hay, (
        f"el botón de la portada promete correr {dice} y el banco tiene {hay}. "
        f"Cámbialo a {hay}.")


def test_la_portada_dice_cuantos_codigos_hay_explicados():
    from validador.codigos import codigos_del_paquete

    hay = len(codigos_del_paquete())
    dice = _cifra_de_la_portada(
        r'los (\d+) están <a href="./incidencias.html">explicados uno a uno')
    assert dice == hay, (
        f"la portada dice {dice} códigos explicados y hay {hay}. Cámbiala a {hay}.")


def test_el_ejemplo_de_nota_de_la_portada_sale_de_verdad_como_nota():
    """La FAQ de las gravedades explica la diferencia entre aviso y nota con un
    caso concreto: `BR-01` pide el código del pedido, Facturae no tiene ese
    elemento, y por eso sale como nota y no como aviso.

    Es un hecho del código metido en un texto, y los hechos del código se
    mueven. El día que `BR-01` pase a aviso —o deje de tener rama de nota— la
    FAQ estaría enseñando de ejemplo justo lo contrario de lo que hace el
    programa, que es el fallo que este punto de la auditoría venía a cerrar.
    """
    from validador.codigos import codigos_del_paquete

    texto = " ".join(PORTADA.read_text(encoding="utf-8").split())
    assert "<code>BR-01</code> pide el código del pedido" in texto, (
        "la FAQ de las gravedades ya no pone BR-01 de ejemplo: o se ha "
        "reescrito con otro código —y hay que cambiarlo aquí— o este guardián "
        "se ha quedado ciego")
    suyo = {c.codigo: c for c in codigos_del_paquete()}["BR-01"]
    assert "nota" in suyo.gravedades, (
        f"la portada usa BR-01 de ejemplo de nota y sale como "
        f"{'/'.join(suyo.gravedades)}")


def test_la_portada_no_promete_la_revocacion_a_secas():
    """De las tres cosas que se miran de una firma, la revocación es la única
    que puede quedarse sin contestar: hace falta una CRL o una respuesta OCSP,
    y este validador no sale a la red a buscarlas.

    La condición estaba escrita —en una FAQ, 300 líneas más abajo— y arriba, en
    la ficha, se prometía a secas. Quien lee de arriba abajo se lleva la
    promesa y puede no llegar nunca a la letra pequeña, así que la condición
    subió. Esto vigila que no vuelva a bajar: si la ficha nombra la revocación,
    tiene que nombrar también de qué depende.
    """
    texto = " ".join(PORTADA.read_text(encoding="utf-8").split())
    celdas = re.findall(r"<dt>La firma</dt><dd>(.*?)</dd>", texto)
    assert len(celdas) == 1, (
        f"«La firma» sale {len(celdas)} veces en la ficha y tiene que salir "
        "una: si se ha reescrito, este guardián está ciego")
    dice = celdas[0]
    if "revocación" in dice:
        # Decía «si hay lista», y en la página no hay dónde ponerla: desde el
        # 05-10-2026 la condición es la que de verdad vale allí.
        assert "si trae la prueba" in dice, (
            f"la ficha promete «{dice}» sin decir de qué depende la "
            "revocación. No siempre se puede comprobar: hace falta una CRL o "
            "una respuesta OCSP dentro de la factura, y de aquí no se sale a "
            "buscarlas.")


def test_el_testigo_cuenta_lo_que_ha_ido_por_la_red():
    """El testigo de la portada dice cuánto se ha pedido, y tiene que ser
    cuánto ha **viajado**.

    Apuntaba `encodedBodySize`, que es lo que ocupa el cuerpo del fichero
    venga de donde venga, y lo pintaba como si fuera red. Medido el 22-09-2026
    en una segunda visita: 21 de 23 ficheros no pasaron por la red y el
    testigo seguía diciendo 17,7 MB. `transferSize` vale cero cuando algo sale
    de la caché, que es justo la diferencia que hay que enseñar.
    """
    portada = PORTADA.read_text(encoding="utf-8")
    assert "cable: entrada.transferSize" in portada, (
        "el testigo ya no apunta `transferSize`: sin él no puede distinguir "
        "lo que ha viajado de lo que salió de la caché")
    assert "tamano(porLaRed)" in portada, (
        "la cifra que enseña el testigo ya no se calcula de lo que viajó")


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
# Todas las páginas llevan el mismo menú copiado, porque no hay plantilla que
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
           "tesis.html", "bitacora.html", "404.html")
PRINCIPIO, FIN = "<!-- MENU", "<!-- FIN MENU -->"


def _menu_de(pagina: Path) -> str:
    texto = pagina.read_text(encoding="utf-8")
    assert PRINCIPIO in texto and FIN in texto, (
        f"«{pagina.name}» se ha quedado sin el menú: entre {PRINCIPIO}… y "
        f"{FIN} es donde va, y ahí no hay nada.")
    return texto[texto.index(PRINCIPIO):texto.index(FIN) + len(FIN)]


def test_el_menu_es_el_mismo_en_todas_las_paginas():
    menus = {p: _menu_de(RAIZ / "web" / p) for p in PAGINAS}
    referencia = menus["index.html"]
    distintas = [p for p, m in menus.items() if m != referencia]
    assert not distintas, (
        "el menú de la portada y el de "
        + ", ".join(f"«{p}»" for p in distintas)
        + " ya no son el mismo. Se copia entero, no se retoca en una sola: "
        "quien entre por esa página verá un sitio distinto del que ve quien "
        "entre por otra.")


# Lo mismo que el menú, con una función: `escapar()` está copiada en la portada
# y en el banco, y las dos pegan su resultado dentro del HTML del informe.
_CON_ESCAPAR = ("index.html", "banco.html")


def _escapar_de(pagina: str) -> str:
    """La declaración entera. Se corta en el `;` **de final de línea**: los
    otros están dentro de las entidades, `&amp;` el primero."""
    texto = (RAIZ / "web" / pagina).read_text(encoding="utf-8")
    trozo = texto[texto.index("const escapar ="):]
    return trozo[:trozo.index(";" + chr(10)) + 1]


def test_escapar_escapa_las_cinco():
    """Punto 39 de la auditoría: escapaba tres y se usa dentro de un atributo.

    En la portada el resultado se pega en `class='glosa " + escapar(...) + "'`,
    y ahí una comilla cierra el atributo: lo que venga detrás se lee como
    marcado. Hoy por ahí solo pasan «error», «aviso» y «nota», así que no tiene
    impacto; el día que pase otra cosa, el fallo sería de esta línea y no de
    quien la escribió.
    """
    for pagina in _CON_ESCAPAR:
        trozo = _escapar_de(pagina)
        for que, como in (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"),
                          ('"', "&quot;"), ("'", "&#39;")):
            assert como in trozo, (
                f"«{pagina}» no escapa {que!r}, y eso acaba dentro de un "
                "atributo del informe")


def test_escapar_es_la_misma_en_las_dos_paginas():
    """Dos copias de una función se separan solas, igual que dos menús."""
    primera, segunda = (_escapar_de(p) for p in _CON_ESCAPAR)
    assert primera == segunda, (
        "la `escapar()` de la portada y la del banco ya no son la misma: una "
        "de las dos escapa menos, y el informe que pinte saldrá distinto")


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


def test_el_responsable_del_tratamiento_es_alguien_y_no_la_marca():
    """Hasta el 15-09-2026 la política decía «Responsable del tratamiento:
    Glosa-e». Es un nombre comercial: el RGPD pide la identidad de quien
    responde, y ante una marca no se ejerce ningún derecho. La marca va en su
    propio campo, y el nombre no puede volver a ser ella."""
    ficha = _ficha()
    if not (ficha.get("nombre") and ficha.get("correo")):
        pytest.skip("la ficha esta vacia: no hay responsable que publicar")
    assert ficha.get("marca"), "la ficha ha perdido el campo de la marca"
    assert ficha["nombre"].strip().lower() != ficha["marca"].strip().lower(), (
        "el titular y responsable del tratamiento vuelve a ser la marca "
        f"«{ficha['marca']}», que no identifica a nadie")
    legal = LEGAL.read_text(encoding="utf-8")
    assert "ponSiHay(t.marca," in legal, (
        "el aviso legal ya no pinta la marca, y la ficha dice un nombre sin "
        "decir de qué")


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


def test_si_hay_buzon_publicado_la_politica_dice_quien_lo_aloja():
    """Publicar una dirección es abrir un tratamiento, y hay que contarlo.

    El día que se puso el correo, el buzón se fue a Zoho y a un centro de datos
    de Estados Unidos: un encargado del tratamiento y una transferencia
    internacional que antes no existían. La política lo dice.

    Lo que esta prueba impide es lo fácil: cambiar de proveedor -o poner una
    direccion de otro dominio- y dejar la política contando el anterior. No
    puede comprobar a quién apuntan los MX, que eso es la red y aquí no se sale;
    comprueba lo que sí puede, que es que el apartado exista mientras haya
    buzón que explicar.
    """
    if not _ficha().get("correo"):
        pytest.skip("no hay correo publicado: no hay buzón que explicar")

    legal = LEGAL.read_text(encoding="utf-8")
    assert "Y si me escribes" in legal, (
        "hay un correo publicado y la política de privacidad no tiene el "
        "apartado que explica qué pasa con lo que se manda ahí")
    assert "encargado" in legal, (
        "la política no dice que el buzón lo lleva un encargado del "
        "tratamiento, que es lo que es en cuanto el correo no lo alojas tú")


# Qué texto tiene que haber al lado de cada etiqueta SPDX. La tabla es corta a
# propósito y **rechaza lo que no conoce**: cambiar `license` a algo que no
# esté aquí no puede salir en verde por no saber contra qué comparar, que es
# como se cuela una licencia sin texto.
TEXTO_DE_CADA_LICENCIA = {
    "AGPL-3.0-only": ("GNU AFFERO GENERAL PUBLIC LICENSE", "Version 3",
                      "13. Remote Network Interaction"),
    "MIT": ("MIT License",),
}


def test_la_licencia_declarada_trae_su_texto_al_lado():
    """Una etiqueta SPDX sin el texto es una licencia que no se ha puesto.

    El 01-09-2026 esto pasó de MIT a AGPL-3.0-only, y hasta ese día el
    repositorio no tenía `LICENSE` **ninguno**: la licencia vivía en una línea
    de `pyproject.toml`, la rueda anunciaba «MIT» y no adjuntaba condiciones, y
    todo el mundo se la bajaba así. Con una copyleft eso ya no es un descuido
    de forma: las condiciones son el producto de la licencia.

    Se comprueban las dos direcciones. Que hay texto, y que el texto es el de
    la etiqueta —no vale dejar el de antes—.
    """
    from validador.paquete import licencia_declarada

    declarada = licencia_declarada(RAIZ)
    assert declarada, "`pyproject.toml` no declara ninguna licencia"
    assert declarada in TEXTO_DE_CADA_LICENCIA, (
        f"«{declarada}» no está en la tabla de esta prueba, así que nadie ha "
        "mirado qué texto le corresponde. Añádela con sus señas antes de "
        "declararla")

    licencia = RAIZ / "LICENSE"
    assert licencia.is_file(), (
        f"el proyecto se publica como «{declarada}» y no hay fichero LICENSE: "
        "la rueda anunciaría unas condiciones que no entrega")

    texto = licencia.read_text(encoding="utf-8")
    for senal in TEXTO_DE_CADA_LICENCIA[declarada]:
        assert senal in texto, (
            f"LICENSE no parece el texto de «{declarada}»: le falta "
            f"«{senal}». ¿Se cambió la etiqueta y se dejó el texto anterior?")


def test_el_readme_dice_bajo_que_licencia_se_publica():
    """Quien se baja la rueda se lleva la licencia dentro; quien lee el
    repositorio, no. La primera pantalla de un proyecto copyleft tiene que
    decir cuál es, y con la etiqueta exacta —«AGPL» a secas no distingue
    `only` de `or-later`, que es justo lo que aquí se decidió a mano."""
    from validador.paquete import licencia_declarada

    declarada = licencia_declarada(RAIZ)
    assert declarada in README.read_text(encoding="utf-8"), (
        f"el proyecto se publica como «{declarada}» y el README no lo dice")

def test_el_aviso_legal_dice_bajo_que_licencia_se_publica():
    """El código viaja entero al navegador; el aviso legal dice con qué
    condiciones.

    Hasta el 15-09-2026 decía «el código del validador y los textos de esta
    página son de su autor», mientras `security.txt` decía AGPL-3.0-only y el
    README contaba que el sitio publicaba la licencia. No la publicaba.
    """
    from validador.paquete import licencia_declarada

    declarada = licencia_declarada(RAIZ)
    legal = LEGAL.read_text(encoding="utf-8")
    titulo = "<h3>De quién es cada cosa</h3>"
    assert titulo in legal, (
        "el aviso legal ya no tiene la sección «De quién es cada cosa» con esa "
        "forma, y este guardián se ha quedado ciego")
    seccion = legal[legal.index(titulo) + len(titulo):]
    seccion = seccion[:seccion.index("<h3>")]
    assert declarada in seccion, (
        f"el proyecto se publica como «{declarada}» y el aviso legal no lo "
        "dice donde dice de quién es cada cosa")


# --- La fecha de la política -------------------------------------------------
#
# «Última actualización: 30 de agosto de 2026» siguió ahí después de que el 31
# se añadieran a la política el buzón en Estados Unidos y la ficha del titular.
# En una política de privacidad la fecha es parte de lo que se promete: dice
# desde cuándo vale lo que pone. No se puede deducir de nada, así que se ata al
# texto. Cambiar una palabra de la página, o de la ficha que la página pinta,
# sin cambiar esto deja la suite en rojo.

FECHA_DE_LA_POLITICA = "18 de octubre de 2026"
HUELLA_DE_LA_POLITICA = "211f099f696c31640dc721e8fa372dd5c5a6314e5e2e081abe51e062e9eb6493"


def _texto_de_la_politica() -> str:
    """Lo que dice la página, sin marcado, sin comentarios y sin la fecha.

    Los comentarios fuera: no son lo que se promete. La ficha de `glosa.js`
    dentro: el responsable del tratamiento y el correo salen de ahí.
    """
    pagina = LEGAL.read_text(encoding="utf-8")
    cuerpo = pagina[pagina.index("<main>"):pagina.index("</main>")]
    cuerpo = re.sub(r"<!--.*?-->", " ", cuerpo, flags=re.S)
    cuerpo = re.sub(r'<p class="fecha">.*?</p>', " ", cuerpo, flags=re.S)
    cuerpo = html.unescape(re.sub(r"<[^>]+>", " ", cuerpo))
    ficha = " ".join(f"{campo}={valor}" for campo, valor in sorted(_ficha().items()))
    return " ".join(f"{cuerpo} {ficha}".split())


def test_la_fecha_de_la_politica_es_la_de_su_ultimo_cambio():
    fechas = re.findall(r'<p class="fecha">Última actualización: (.*?)\.</p>',
                        LEGAL.read_text(encoding="utf-8"))
    assert fechas == [FECHA_DE_LA_POLITICA], (
        f"legal.html dice {fechas} y aquí consta «{FECHA_DE_LA_POLITICA}»")
    hay = hashlib.sha256(_texto_de_la_politica().encode("utf-8")).hexdigest()
    assert hay == HUELLA_DE_LA_POLITICA, (
        "La política o el aviso legal han cambiado y su fecha no. Pon la de "
        "hoy en `legal.html` y en FECHA_DE_LA_POLITICA, y "
        f'HUELLA_DE_LA_POLITICA = "{hay}".')


# --- Lo que la portada promete que se puede correr ---------------------------
# La seccion «Por qué este» no cuenta las comprobaciones: las corre, delante de
# quien mira. Eso la hace fuerte y la hace fragil por el mismo motivo — si el
# boton deja de funcionar, **no da error**: se queda apagado, o se queda
# «Corriendo…» para siempre, y la pagina que dice «compruébalo tú» es
# justamente la que ha dejado de poder comprobarse. Nadie lo ve, porque la
# pagina carga perfecta.


def _exportado_por_glosa_js() -> str:
    js = (RAIZ / "web" / "glosa.js").read_text(encoding="utf-8")
    marca = "window.Glosa = {"
    assert marca in js, "glosa.js ya no exporta window.Glosa"
    return js[js.index(marca):]


def test_lo_que_las_paginas_llaman_existe_en_glosa_js():
    """Cada `Glosa.loquesea` de una pagina, contra lo que glosa.js entrega."""
    entregado = _exportado_por_glosa_js()
    for pagina in PAGINAS:
        texto = (RAIZ / "web" / pagina).read_text(encoding="utf-8")
        for usada in sorted(set(re.findall(r"Glosa\.(\w+)", texto))):
            assert usada in entregado, (
                f"«{pagina}» llama a Glosa.{usada} y glosa.js no lo exporta. "
                "No falla nada: el boton se queda muerto y la pagina sigue "
                "diciendo que eso se puede comprobar.")


def test_lo_que_la_portada_dice_de_otros_lleva_fecha_y_donde_mirarlo():
    """Un dato sobre un tercero sin fecha ni enlace se pudre en silencio.

    La portada afirma que los validadores gratuitos que se miraron no enseñan
    sus comprobaciones y dicen poco de la firma. Eso fue verdad el dia que se
    miro y puede dejar de serlo mañana sin que aqui se entere nadie. Lo unico
    que se puede exigir a una afirmacion asi es que diga **de que dia es** y
    **donde comprobarla** — y que se pueda avisar de que ya no vale.
    """
    portada = (RAIZ / "web" / "index.html").read_text(encoding="utf-8")
    trozo = re.search(r'<p class="procedencia">(.*?)</p>', portada, re.S)
    assert trozo, (
        "la portada ha perdido la nota de procedencia de la seccion «Por qué "
        "este», y con ella lo unico que sostiene lo que alli se dice de otros")
    nota = trozo.group(1)
    assert re.search(r"\d{2}-\d{2}-\d{4}", nota), (
        "la nota de procedencia no dice de que dia es lo que se miro")
    enlaces = re.findall(r'href="(https?://[^"]+)"', nota)
    assert len(enlaces) >= 2, (
        f"la nota de procedencia cita a otros y solo trae {len(enlaces)} "
        "enlace(s): lo que se dice de un tercero se enlaza a donde lo dice el")
    assert "mailto:" in nota, (
        "la nota de procedencia no deja avisar de que algo de esto ya no vale")

def test_la_linea_de_autoria_es_la_misma_en_todas_las_paginas():
    """Copiada en siete sitios, y por lo mismo que el menú: sin plantilla.

    Una línea de autoría que dice una cosa en la portada y otra en el aviso
    legal es peor que no tenerla — dice que nadie mira. Se compara letra por
    letra, que es como se rompen estas cosas.
    """
    RE_FIRMA = re.compile(r'<p class="firma-pie">(.*?)</p>', re.S)
    dicen = {}
    for pagina in PAGINAS:
        texto = (RAIZ / "web" / pagina).read_text(encoding="utf-8")
        encaje = RE_FIRMA.search(texto)
        assert encaje, f"«{pagina}» se ha quedado sin la línea de autoría"
        dicen[pagina] = encaje.group(1)

    distintas = {p: d for p, d in dicen.items() if d != dicen["index.html"]}
    assert not distintas, (
        "la línea de autoría de la portada y la de "
        + ", ".join(f"«{p}»" for p in distintas)
        + " ya no dicen lo mismo")

    # «Todos los derechos reservados» sería falso aquí: el validador se publica
    # bajo AGPL y cualquiera puede usarlo y modificarlo. Desde el 24-09-2026 la
    # línea es «© 2026 Glosa-e» a secas; de quién es cada cosa lo dice el aviso
    # legal.
    assert "derechos reservados" not in dicen["index.html"].lower(), (
        "el código es AGPL-3.0-only: decir que todos los derechos están "
        "reservados contradice la licencia que el propio sitio publica")
    assert re.fullmatch(r"© \d{4} Glosa-e", dicen["index.html"]), (
        f"la línea de autoría dice «{dicen['index.html']}», y desde el "
        "24-09-2026 es «© año Glosa-e» y nada más: lo decidió el titular")


def test_donde_la_portada_nombra_el_anexo_dice_que_es_parte_de_el():
    """Ni «comprueba el anexo I de su orden» a secas.

    El revisor de promesas, el 07-10-2026: el pie decía «Comprueba lo que
    dicen EN 16931, el RD 238/2026 y el anexo I de su orden», y la pregunta
    frecuente lo mismo entre paréntesis, cuando de la orden solo se había
    recogido lo que dejaba de condenar a una factura bien hecha. Hasta el
    11-10-2026 los tres párrafos decían además que se medía «en buena parte»
    con el borrador de abril; desde ese día las reglas miden la orden, pero no
    todo lo que pide (`solucion_publica.LO_QUE_TODAVIA_NO_SE_MIDE`), y dicen
    «parte». Si sale un cuarto párrafo, que lo diga también o que esta prueba
    cambie a la vista.
    """
    portada = (RAIZ / "web" / "index.html").read_text(encoding="utf-8")
    parrafos = [" ".join(p.split()) for p in re.findall(r"<p\b.*?</p>", portada, re.S)]
    con_el_anexo = [p for p in parrafos if re.search(r"\banexo I\b", p)]
    assert len(con_el_anexo) == 3, con_el_anexo
    for parrafo in con_el_anexo:
        assert "parte del anexo I" in parrafo, parrafo
        assert "borrador de abril" not in parrafo, parrafo


# --- Lo que el validador dice de la orden -------------------------------------
#
# La Orden HAC/1028/2026 salió en el BOE el 05-10-2026. El 07-10-2026 la nota
# `SPFE-BORRADOR` dejó de decir que no estaba publicada, y el 11-10-2026 se vio
# que lo seguían diciendo la cabecera de `codigo_unico.py` y la ficha de
# `CU-03`, que se publica en la página. Era la misma frase escrita en más sitios
# de los que se cambiaron: buscarla a mano ya falló una vez.

_POR_PUBLICAR = re.compile(
    r"no se ha publicado|no está publicad[ao]|(?:aún|todavía) sin publicar", re.I)


def _frases_de(modulo: Path) -> list[str]:
    """Lo que dice un módulo, sus cadenas y sus comentarios, partido en frases.

    Se lee con `tokenize` y no con una expresión sobre el fichero porque las
    frases largas van partidas en cadenas seguidas o en varias líneas de
    comentario, y la de `CU-03` lo estaba justo por la mitad: «todavía» al final
    de una cadena y «no se ha publicado» en la siguiente.
    """
    trozos = []
    with modulo.open("rb") as f:
        for ficha in tokenize.tokenize(f.readline):
            if ficha.type == tokenize.COMMENT:
                trozos.append(ficha.string.lstrip("#"))
            elif ficha.type == tokenize.FSTRING_MIDDLE:
                trozos.append(ficha.string)
            elif ficha.type == tokenize.STRING:
                valor = ast.literal_eval(ficha.string)
                if isinstance(valor, str):
                    trozos.append(valor)
    texto = " ".join(" ".join(trozos).split())
    return re.split(r"(?<=[.!?»])\s+", texto)


def test_el_validador_no_dice_que_la_orden_este_por_publicar():
    """Ni en una ficha, ni en un mensaje, ni en un comentario.

    Una frase que diga a la vez que algo no se ha publicado y que nombre la
    orden. Lo histórico se escribe en pasado —«no estaba publicada»— y no
    salta; si un día hace falta decir en presente que otra cosa de la orden
    sigue sin publicarse, que se diga sin esas palabras o que esta prueba
    cambie a la vista.
    """
    encontradas = [
        f"{modulo.relative_to(RAIZ)}: «{frase[:160]}»"
        for modulo in sorted((RAIZ / "validador").glob("*.py"))
        for frase in _frases_de(modulo)
        if _POR_PUBLICAR.search(frase) and re.search(r"\borden\b", frase, re.I)]
    assert not encontradas, (
        "La Orden HAC/1028/2026 está publicada desde el 05-10-2026 y esto "
        "sigue diciendo que no:\n" + "\n".join(encontradas))


# --- Lo que se dice de BR-IG y BR-IP ------------------------------------------
#
# El 26-08-2026 las reglas del IGIC y del IPSI pasaron aquí de BR-IG y BR-IP a
# BR-AF y BR-AG, al comprobarlas contra el esquematrón oficial, y se contó
# diciendo que BR-IG y BR-IP eran un invento de este proyecto que no existía en
# ninguna norma. Era falso: el esquematrón del CEN los usó en UBL en todas sus
# versiones publicadas, de la 1.0.0 (2018) a la 1.3.13, y la 1.3.17 vuelve a
# ellos. La frase acabó en cinco sitios del validador y del README, uno de
# ellos la ficha de `BR-AG-01` (hoy `BR-IP-01`), que sale en la página. Lo
# destapó la auditoría de la 1.3.17, el 12-10-2026.

_LOS_NOMBRES = re.compile(r"\bBR-I[GP]\b|«I[GP]»|\bIG(?: e | y |/)IP\b")
# Lo de «en España» va fuera desde el 24-10-2026: con las fichas llamándose
# otra vez BR-IG-*, la de BR-IG-08 nombra la familia en su primera frase y en
# la siguiente habla de «un tipo que no existe en España», que es del IGIC y
# no de su nombre.
_SIN_NORMA = re.compile(
    r"no exist\w*\b(?! en España)|nunca exist\w*|inexistent\w*|invent\w*|"
    r"no aparec\w* en ningun\w*|por analog\w*", re.I)
_LO_DICE_FALSO = re.compile(r"\bfals[oa]s?\b", re.I)


def _en_frases(texto: str) -> list[str]:
    """Partido en frases, pero no detrás de cualquier «»».

    `_frases_de` corta también detrás de una comilla de cierre, y con eso «una
    regla «BR-IG-5» que no existe» quedaba en dos frases y no se veía.
    """
    return re.split(r"(?<=[.!?])\s+|(?<=[.!?][»)])\s+", " ".join(texto.split()))


def test_nadie_dice_que_br_ig_y_br_ip_sean_un_invento_de_aqui():
    """Ni el validador, que escribe las fichas y viaja en la rueda, ni el README.

    Una frase que nombre BR-IG o BR-IP y en la que, o en la de al lado, se diga
    que no existen, que se inventaron o que salieron por analogía. La de al
    lado cuenta porque la ficha de `BR-AG-01` lo decía así: el nombre en una
    frase y «no existe en ninguna norma» en la siguiente. Contarlo como
    historia vale si se dice ahí mismo que era falso. Qué nombre les ha dado
    el CEN en cada versión y en cada sintaxis está en `iva.REGLAS`.
    """
    readme = (RAIZ / "README.md").read_text(encoding="utf-8")
    fuentes = [(modulo.relative_to(RAIZ), _en_frases(" ".join(_frases_de(modulo))))
               for modulo in sorted((RAIZ / "validador").glob("*.py"))]
    fuentes.append((Path("README.md"), _en_frases(readme)))
    encontradas = []
    for donde, frases in fuentes:
        for i, frase in enumerate(frases):
            alrededor = " ".join(frases[max(0, i - 1):i + 2])
            if (_LOS_NOMBRES.search(frase) and _SIN_NORMA.search(alrededor)
                    and not _LO_DICE_FALSO.search(alrededor)):
                encontradas.append(f"{donde}: «{alrededor[:200]}»")
    assert not encontradas, (
        "BR-IG y BR-IP son los nombres que el CEN dio en UBL al IGIC y al IPSI "
        "hasta la 1.3.13, y otra vez en la 1.3.17, y esto dice que no existen:\n"
        + "\n".join(encontradas))


# Lo que las fichas del IGIC y del IPSI cuentan de la copia con la que se
# comparan. Las dos nombran la versión fijada, y la de `BR-IG-01` cuenta las
# reglas de la familia (contaba seis cuando la copia traía diez): las dos cosas
# quedan viejas en silencio el día que se trae otra copia. Con la 1.3.16, la
# ficha que nombraba la versión era la de `BR-AG-01`, y al traer la 1.3.17
# esta prueba se puso en rojo y obligó a reescribirlas.

_HUELLA_DE_LA_1_3_17 = "1f67b2a5d86f0f161d2cfa7ed14d7479a9e0562b299495b8545157a160b97de4"


@pytest.mark.parametrize("ficha", ["BR-IG-01", "BR-IP-01"])
def test_las_fichas_del_igic_y_del_ipsi_nombran_la_copia_con_la_que_se_compara(ficha):
    """Dicen «la 1.3.17», y la huella fijada tiene que ser la de la 1.3.17."""
    from validador.glosario import CODIGOS

    fijada = re.search(r'^HUELLA = "([0-9a-f]{64})"',
                       (RAIZ / "tests" / "test_norma_oficial.py").read_text(encoding="utf-8"),
                       re.M).group(1)
    assert fijada == _HUELLA_DE_LA_1_3_17, (
        f"La copia oficial ya no es la 1.3.17, y la ficha de {ficha} cuenta los "
        "nombres que ha tenido la familia hasta ella: hay que reescribirla con la "
        "versión nueva, y esta prueba con ella.")
    assert "con la que se compara, la 1.3.17," in " ".join(CODIGOS[ficha].split())


def test_la_ficha_de_br_ig_01_cuenta_las_reglas_que_trae_la_copia():
    """«Familia entera de diez reglas», y la copia trae diez BR-IG en UBL."""
    from validador.glosario import CODIGOS

    reglas = set(re.findall(
        r'name="(BR-IG-\d+)"',
        (RAIZ / "tests" / "en16931-oficial" / "EN16931-UBL-model.sch").read_text(encoding="utf-8")))
    en_letra = {10: "diez"}
    assert len(reglas) in en_letra, (
        f"La copia oficial trae {len(reglas)} reglas BR-IG y la ficha de BR-IG-01 "
        "cuenta diez: hay que reescribirla, y esta prueba con ella.")
    assert (f"familia entera de {en_letra[len(reglas)]} reglas"
            in " ".join(CODIGOS["BR-IG-01"].split()))


def test_cada_pie_enlaza_las_dos_cuentas():
    """El pie de cada página lleva la cuenta de X y el perfil de LinkedIn.

    Los pies están escritos a mano, uno por página, y no se parecen: por eso
    se mira cada uno. Las direcciones salen de `paquete`, que es de donde sale
    también la ficha de la portada: si cambia una cuenta, cambia en un sitio y
    esta prueba avisa de los pies que se quedaron con la vieja.

    `rel="me"` dice que la cuenta es de quien firma la página. No cuesta nada
    y algunos sitios lo usan para comprobarlo en sentido contrario.

    Desde el 18-10-2026 van como iconos, sin texto: el nombre lo lleva el
    `aria-label`, y sin él un lector de pantalla diría solo "enlace". Y el
    icono va dentro de la página, nunca como imagen de la red: pedirla
    rompería el "cero dominios de terceros" de la política de privacidad.
    """
    from validador import paquete

    pies = 0
    for pagina in sorted((RAIZ / "web").glob("*.html")):
        texto = pagina.read_text(encoding="utf-8")
        if "<footer>" not in texto:
            continue
        pies += 1
        pie = texto[texto.index("<footer>"):texto.index("</footer>")]
        for cuenta in (paquete.CUENTA_DE_LA_MARCA, paquete.PERFIL_DEL_TITULAR):
            enlace = re.search(
                rf'<a href="{re.escape(cuenta)}" rel="me" aria-label="([^"]+)"[^>]*>(.*?)</a>',
                pie, re.S)
            assert enlace, (pagina.name, cuenta)
            assert enlace.group(2).startswith("<svg"), (pagina.name, cuenta)
            assert "<img" not in enlace.group(2) and "src=" not in enlace.group(2)
    assert pies >= 7, "han desaparecido pies: esta prueba ya no mira lo que creía"
