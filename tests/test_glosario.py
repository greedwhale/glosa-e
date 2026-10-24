# -*- coding: utf-8 -*-
"""Las explicaciones escritas a mano, atadas al catálogo que las usa.

Por qué existe
--------------
`glosario.py` era, hasta el 6 de septiembre de 2026, **el único módulo de
`validador/` que ninguna prueba nombraba**. Lo destapó el inventario de
`test_inventario.py`, no una avería.

Y es un módulo con consecuencias visibles: es lo que hace que la página de
incidencias diga algo cuando a alguien le sale `REVOCACION-OCSP-NO-VALE` en un
informe. Si una familia se quedara sin explicación, la página no fallaría —
seguiría montándose— y todos sus códigos saldrían dichos como huecos. Verde por
fuera y vacío por dentro, que es el fallo de siempre de esta casa.

Lo que se comprueba es el enganche entre las dos mitades: los códigos se leen
del fuente y las explicaciones se escriben a mano, así que lo que se puede
romper es que dejen de encajar.
"""
from __future__ import annotations

import re

from validador.codigos import codigos_del_paquete
from validador.glosario import CODIGOS, FAMILIAS, explicar


def test_toda_familia_del_catalogo_tiene_explicacion():
    """Sin esto, una familia entera sale sin una palabra y nada avisa."""
    familias = sorted({c.familia for c in codigos_del_paquete()})
    sin = [f for f in familias if not FAMILIAS.get(f)]
    assert not sin, (
        f"estas familias salen en el catálogo y no tienen explicación: "
        f"{', '.join(sin)}. Sus códigos se publicarían dichos como huecos, y "
        "la página se montaría igual sin quejarse."
    )


def test_ninguna_explicacion_lleva_rayas():
    """La raya (—) hace que un texto suene escrito por una máquina.

    Lo decidió el titular el 28-09-2026. Estas explicaciones son el cuerpo de
    cada ficha de código de la web, y se escriben a mano: los incisos van
    entre comas o entre paréntesis.
    """
    con = sorted(clave for clave, texto in [*FAMILIAS.items(), *CODIGOS.items()]
                 if "—" in texto)
    assert not con, (
        f"estas explicaciones llevan raya: {', '.join(con)}. Los incisos, "
        "entre comas o entre paréntesis.")


def test_lo_escrito_en_el_fichero_va_entre_comillas_invertidas():
    """«`10.500` son tres decimales», y no «10.500 son tres decimales».

    Sin las comillas, en castellano se lee diez mil quinientos. Hasta el
    05-10-2026 estaban así los ejemplos de las BR-DEC, 37 veces en 19 fichas.
    Fuera de las comillas una cifra va como en el informe: coma decimal, y
    punto de miles desde cinco cifras (1163,52, no 1.163,52). Lo único con
    punto que queda fuera es una versión, y está escrita aquí.
    """
    versiones = {("SPFE-SINTAXIS", "2.5"), ("SPFE-MENSAJE-ALCANCE", "2.5")}
    # Las del esquematrón del CEN, que las fichas de BR-IG-01 y BR-IP-01 citan
    # para contar cómo se han llamado las reglas del IGIC y del IPSI en cada una.
    versiones |= {(ficha, v) for ficha in ("BR-IG-01", "BR-IP-01")
                  for v in ("1.3.13", "1.3.14", "1.3.16", "1.3.17")}
    # Y las que dicen desde qué versión CII las llama de otro modo: la nota del
    # cero y las demás fichas de las dos familias.
    versiones.add(("IVA-CERO-ESQUEMATRON", "1.3.17"))
    # Y las de dos listas que la 1.3.17 igualó entre UBL y CII.
    versiones |= {("BR-CL-08", "1.3.17"), ("BR-CL-14", "1.3.17")}
    # Y la nota de EL, que dice qué versión lo admitía y cuál lo quitó.
    versiones |= {("IVA-PREFIJO-EL", "1.3.16"), ("IVA-PREFIJO-EL", "1.3.17")}
    versiones |= {("IVA-VATEX-ES", "1.3.16"), ("IVA-VATEX-ES", "1.3.17")}
    versiones |= {(f"BR-{f}-{n:02d}", "1.3.17") for f in ("IG", "IP") for n in range(2, 11)}
    con_punto = []
    for clave, texto in [*FAMILIAS.items(), *CODIGOS.items()]:
        fuera = re.sub(r"`[^`]*`", "", texto)
        # Los miles bien puestos, desde cinco cifras: 12.345,67 sí, 1.163,52 no.
        fuera = re.sub(r"(?:\d{2,3}(?:\.\d{3})+|\d(?:\.\d{3}){2,}),\d+", "", fuera)
        for cifra in re.findall(r"\d+(?:\.\d+)+", fuera):
            if (clave, cifra) not in versiones:
                con_punto.append(f"{clave}: {cifra}")
    assert not con_punto, (
        "estas cifras se leen con el punto como miles: "
        + ", ".join(con_punto)
        + ". Lo que está escrito así en el fichero, entre comillas invertidas.")


def test_ninguna_explicacion_escrita_sobra():
    """Una explicación de un código que ya no existe manda a buscar a un sitio vacío."""
    hay = {c.codigo for c in codigos_del_paquete()}
    fantasmas = sorted(c for c in CODIGOS if c not in hay)
    assert not fantasmas, (
        f"hay explicación escrita para códigos que el validador ya no emite: "
        f"{', '.join(fantasmas)}. O el código volvió a llamarse de otra "
        "manera, o la explicación se quedó atrás."
    )


def test_un_codigo_sin_explicacion_propia_hereda_la_de_su_familia():
    """El código de la prueba es inventado, y eso es lo que la sostiene.

    Ha tenido tres formas. Nombraba a BR-22, y el día que a BR-22 se le
    escribió la suya se puso en rojo sin que nada estuviera mal. Pasó entonces
    a buscar uno de los que no la tenían, y el día que los ciento sesenta la
    tuvieron se empezó a saltar sola: verde, y sin comprobar nada.

    El mecanismo sigue haciendo falta, porque una regla nueva nace sin
    explicación propia y tiene que recibir la de su familia hasta que se le
    escriba la suya. Lo que no puede es depender de que exista un código así
    hoy. Con uno inventado se comprueba lo mismo y no se agota nunca.
    """
    inventado = "BR-NO-EXISTE-99"
    assert inventado not in CODIGOS, "deja de estar inventado y ya no prueba"

    texto, propia = explicar(inventado, "BR")
    assert texto, "un código sin explicación propia no recibe la de su familia"
    assert propia is False, "`explicar` dice que es propia y no lo es"
    assert texto == FAMILIAS["BR"]


def test_todos_los_codigos_del_paquete_tienen_la_suya():
    """Hoy los 165 la tienen, y eso se dice en vez de darse por supuesto.

    No es una regla que haya que cumplir siempre: un código nuevo entra sin
    explicación y hereda, que para eso está la herencia. Pero la cuenta se
    publica en la página de incidencias, así que esta prueba es la que obliga
    a mirarla el día que deje de ser cierta.
    """
    heredan = [c.codigo for c in codigos_del_paquete() if c.codigo not in CODIGOS]
    assert not heredan, (
        f"{len(heredan)} códigos siguen con la de su familia: "
        + ", ".join(heredan[:8]))


def test_un_codigo_desconocido_no_se_inventa_nada():
    """El hueco se dice, no se rellena: es lo que la página cuenta como hueco."""
    texto, propia = explicar("NO-EXISTE-ESTE", "TAMPOCO")
    assert texto == ""
    assert propia is False


def test_las_fichas_del_igic_y_del_ipsi_dicen_como_las_llama_cii():
    """El código que da un validador de CII lleva a la ficha de la otra categoría.

    Lo que dice cada ficha, contra `Sintaxis.familias_de_su_esquematron`, que
    `test_norma_oficial` compara con la vinculación de CII. Si el CEN deshace
    el cruce, esto se pone en rojo y las dieciocho frases sobran.
    """
    from validador import iva
    from validador.sintaxis import SINTAXIS_CII

    for categoria, otra in (("L", "M"), ("M", "L")):
        aqui = iva.REGLAS[categoria].codigo
        en_cii = SINTAXIS_CII.familias_de_su_esquematron[categoria]
        assert en_cii == iva.REGLAS[otra].codigo, (
            f"CII ya no cruza {aqui}: sobran las frases del cruce en las fichas")
        for numero in range(2, 11):
            texto = " ".join(CODIGOS[f"BR-{aqui}-{numero:02d}"].split())
            assert (f"llama a esta regla BR-{en_cii}-{numero:02d}," in texto
                    and f"la ficha que lo explica es BR-{en_cii}-{numero:02d}." in texto), (
                aqui, numero)
