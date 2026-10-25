# -*- coding: utf-8 -*-
"""Los canales Atom del sitio (RFC 4287): el de las novedades y el de la bitácora.

Son dos y no uno desde el 25-10-2026. Las novedades cuentan las reglas que
entran y salen; la bitácora, los artículos. Juntas en un solo canal, cada
artículo se contaba dos veces, una en su índice y otra en las novedades, y
quien solo quería saber qué cambia en el validador recibía también lo que se
escribe sobre la norma. Cada canal dice lo mismo que su página, porque sale de
las mismas entradas.

Las dos cosas que importan a un lector de noticias y que aquí se fijan:

- **La fecha.** No se apunta la hora en ningún sitio, así que va la
  medianoche UTC del día: Atom pide fecha y hora, y lo que vale es el día.
- **El id de cada entrada, que no cambia nunca.** Es lo que usa el lector para
  saber que ya la enseñó; si cambiara al corregir una errata, la enseñaría
  otra vez como nueva.
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from xml.sax.saxutils import escape as _xml

__all__ = ["Entrada", "canal", "direccion"]


@dataclass(frozen=True)
class Entrada:
    titulo: str
    enlace: str  # la dirección entera, que es también su id
    publicada: _dt.date
    cambiada: _dt.date
    resumen: str


def direccion(dominio: str, enlace: str) -> str:
    """`./x.html#y` → `https://dominio/x#y`, la dirección limpia que sirve
    producción, como la canónica y el sitemap."""
    sin_punto = enlace.removeprefix("./")
    pagina, _, ancla = sin_punto.partition("#")
    limpia = pagina.removesuffix(".html")
    return f"{dominio}/{limpia}" + (f"#{ancla}" if ancla else "")


def momento(dia: _dt.date) -> str:
    return f"{dia.isoformat()}T00:00:00Z"


def canal(*, dominio: str, nombre: str, pagina: str, titulo: str, subtitulo: str,
          entradas: list[Entrada], sin_entradas: _dt.date) -> str:
    """El canal entero. `nombre` es su fichero (`novedades.xml`) y `pagina`,
    la página que dice lo mismo (`novedades`). `sin_entradas` es la fecha que
    lleva el canal si no tiene ninguna, porque Atom pide una siempre y
    inventarla con la de hoy diría que cambió algo."""
    ultima = max((e.cambiada for e in entradas), default=sin_entradas)
    cuerpo = "".join(
        "  <entry>\n"
        f"    <title>{_xml(e.titulo)}</title>\n"
        f'    <link rel="alternate" type="text/html" href="{_xml(e.enlace)}"/>\n'
        f"    <id>{_xml(e.enlace)}</id>\n"
        f"    <published>{momento(e.publicada)}</published>\n"
        f"    <updated>{momento(e.cambiada)}</updated>\n"
        f"    <summary>{_xml(e.resumen)}</summary>\n"
        "  </entry>\n"
        for e in entradas
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="es">\n'
        f"  <title>{_xml(titulo)}</title>\n"
        f"  <subtitle>{_xml(subtitulo)}</subtitle>\n"
        f'  <link rel="self" type="application/atom+xml" href="{dominio}/{nombre}"/>\n'
        f'  <link rel="alternate" type="text/html" href="{dominio}/{pagina}"/>\n'
        f"  <id>{dominio}/{pagina}</id>\n"
        f"  <updated>{momento(ultima)}</updated>\n"
        f"  <author><name>Glosa-e</name><uri>{dominio}/</uri></author>\n"
        + cuerpo
        + "</feed>\n"
    )
