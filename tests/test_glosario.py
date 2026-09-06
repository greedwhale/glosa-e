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
    texto, propia = explicar("BR-22", "BR")
    assert texto, "BR-22 no recibe ni la explicación de su familia"
    assert propia is False, "BR-22 no tiene explicación propia, y se dice así"
    assert texto == FAMILIAS["BR"]


def test_un_codigo_desconocido_no_se_inventa_nada():
    """El hueco se dice, no se rellena: es lo que la página cuenta como hueco."""
    texto, propia = explicar("NO-EXISTE-ESTE", "TAMPOCO")
    assert texto == ""
    assert propia is False
