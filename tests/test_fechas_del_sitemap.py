# -*- coding: utf-8 -*-
"""Las fechas de `web/fechas.txt`, que van al `lastmod` del sitemap.

Desde el 26-10-2026 la portada, el banco, Sobre Glosa-e, el aviso legal y el
catálogo llevan fecha en el sitemap, y se escribe a mano. Lo que se escribe a
mano se queda atrás, y una fecha atrasada le dice a Google que una página no
ha cambiado cuando sí. Por eso cada fecha va con la huella de su página, y
aquí se niega si la página ya no es la que se apuntó.

Cómo entra al sitemap, y que una línea mal escrita no deje montar, se mira en
`tests/test_paquete.py`, en `TestLasFechasApuntadas`.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from validador import paquete

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"

# Las cinco que no tienen otra de dónde sacar la fecha. Si una sale de la
# lista, sale del sitemap con su fecha, y eso se decide, no se pierde.
CON_FECHA = {"index.html", "banco.html", "sobre.html", "legal.html", "incidencias.html"}


def test_cada_fecha_es_de_la_pagina_de_hoy():
    fechas = paquete._fechas_de_las_paginas(WEB)
    viejas = []
    for nombre, (dia, apuntada) in sorted(fechas.items()):
        hoy = paquete.huella_para_la_fecha((WEB / nombre).read_text(encoding="utf-8"))
        if hoy != apuntada:
            viejas.append(f"{nombre}: dice {dia:%d-%m-%Y}, huella {apuntada}; "
                          f"la de ahora es {hoy}")
    assert not viejas, (
        "Ha cambiado una página y su fecha del sitemap no: "
        + "; ".join(viejas)
        + f". Pon en web/{paquete.FECHAS} la fecha del día en que se publica y "
        "la huella nueva.")


def test_las_cinco_tienen_fecha():
    assert set(paquete._fechas_de_las_paginas(WEB)) == CON_FECHA


def test_ninguna_fecha_es_de_un_dia_que_no_ha_llegado():
    hoy = dt.date.today()
    futuras = {n: d for n, (d, _) in paquete._fechas_de_las_paginas(WEB).items() if d > hoy}
    assert not futuras, f"fechas de días que no han llegado: {futuras}"


def test_un_comentario_no_cambia_la_huella_y_una_palabra_si():
    pagina = "<p>Lo que dice.</p>\n"
    assert paquete.huella_para_la_fecha(pagina) == paquete.huella_para_la_fecha(
        "<!-- una nota al margen -->\n   <p>Lo que   dice.</p>")
    assert paquete.huella_para_la_fecha(pagina) != paquete.huella_para_la_fecha(
        "<p>Lo que dice hoy.</p>\n")
