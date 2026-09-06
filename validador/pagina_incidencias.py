# -*- coding: utf-8 -*-
"""La página que explica cada código de incidencia, generada del código fuente.

Por qué existe
--------------
Cuando a alguien le sale `REVOCACION-OCSP-NO-VALE` en un informe, lo que hace
es buscar ese código. Si no encuentra nada, se queda con una frase de veinte
palabras y ninguna forma de saber si eso es grave, de dónde sale la exigencia
ni a quién hay que reclamarle. Esta página contesta eso, y es enlazable código
a código: `incidencias.html#REVOCACION-OCSP-NO-VALE`.

Por qué se genera y no se escribe
---------------------------------
Porque un catálogo escrito a mano se queda atrás, y entonces manda a buscar a
un sitio donde no está, que es peor que no tenerlo. Los códigos salen de
`codigos.py`, que los lee con `ast` de los propios módulos y de las tablas de
reglas que los alimentan. Se añade uno nuevo en `firma.py` y aparece aquí sin
que nadie se acuerde de nada.

Los que se componen al validar —los `BR-{X}-8` del IVA, que llevan dentro la
categoría de la operación— no se pueden leer del fuente y **no están en la
lista**. Salen contados en la ficha de arriba, porque un catálogo al que le
faltan seis y lo dice sigue sirviendo, y uno al que le faltan y no lo dice no.

Lo que sí está escrito a mano son las explicaciones, en `glosario.py`, porque
el mensaje del informe se compone en tiempo de ejecución y no hay frase fija
que extraer. Los códigos sin explicación propia salen con la de su familia, y
los que no tienen ninguna salen **dichos como huecos** y contados arriba: un
catálogo que rellena con paráfrasis del propio código miente mejor que uno con
huecos a la vista.

Estática y sin Pyodide, a propósito
------------------------------------
Es una página de consulta: se llega a ella desde un buscador con un código
entre las manos. Hacerla depender de catorce megas de intérprete para leer una
tabla sería cobrar carísimo por nada.
"""
from __future__ import annotations

import html
from pathlib import Path

from validador.codigos import (
    Codigo,
    SinLeer,
    codigos_del_paquete,
    sin_leer_del_paquete,
)
from validador.glosario import explicar

__all__ = ["montar_pagina", "NOMBRE"]

NOMBRE = "incidencias.html"
# La marca de la plantilla donde se pega el catálogo. Si desaparece, montar
# la página no falla solo: publica una página sin un solo código.
HUECO = "<!-- AQUI VA EL CATALOGO -->"

# El mismo reparto que `factura.origen`, pero por prefijo y no por incidencia:
# aquí no hay incidencias, hay códigos. Se escribe al lado a propósito en vez
# de importar `factura`, que arrastra lxml y el catálogo entero para contestar
# una pregunta que es una tabla de prefijos.
_NORMAS = (
    ("BR-", "EN 16931", "la norma europea de factura electrónica"),
    ("CU-", "RD 238/2026", "el real decreto español del código único"),
    ("XSD-", "Esquema XSD", "el esquema oficial del formato"),
    ("FE-", "Formato Facturae", "la especificación española de Facturae"),
    ("EDI-", "ISO 9735", "la sintaxis de EDIFACT"),
    ("NIF-", "De la casa", "no lo exige ninguna norma de las anteriores"),
    ("IVA-", "Ley del IVA", "el desglose de impuestos"),
)
_DE_LA_FIRMA = ("FIRMA-", "CADENA-", "REVOCA", "CONFIANZA-", "SELLO-", "ANCLAS-")


def _norma(codigo: str) -> tuple[str, str]:
    for prefijo, etiqueta, detalle in _NORMAS:
        if codigo.startswith(prefijo):
            return etiqueta, detalle
    if codigo.startswith(_DE_LA_FIRMA):
        # «REVOCA» y no «REVOCACION-», igual que en `factura.origen`: el código
        # de la anulación confirmada es `REVOCADO` a secas, y sin esto salía
        # etiquetado como un problema de formato, que es justo lo que no es.
        return "Firma electrónica", "eIDAS y las normas ETSI de firma"
    return "De la casa", "no lo exige ninguna norma concreta"


def _fila(uno: Codigo) -> str:
    texto, propia = explicar(uno.codigo, uno.familia)
    etiqueta, detalle = _norma(uno.codigo)
    gravedades = "".join(
        f'<span class="cuenta {g}">{g}</span>' for g in uno.gravedades
    ) or '<span class="cuenta">sin gravedad fija</span>'

    if not texto:
        cuerpo = (
            '<p class="sin-explicar">Sin explicación escrita todavía. Lo que '
            "se sabe de él está aquí: su gravedad, la norma a la que responde "
            "y el módulo que lo emite.</p>"
        )
    else:
        cuerpo = f"<p>{html.escape(texto)}</p>"
        if not propia:
            cuerpo += (
                '<p class="de-familia">Es la explicación de la familia '
                f'<b>{html.escape(uno.familia)}</b>: este código todavía no '
                "tiene una suya.</p>"
            )

    varias = (
        '<p class="de-familia">Sale con más de una gravedad según el caso, y '
        "eso no es un descuido: el mismo hecho vale distinto según con qué "
        "esté probado.</p>"
        if len(uno.gravedades) > 1 else ""
    )

    return (
        f'<article class="codigo-ficha" id="{html.escape(uno.codigo)}">'
        f'<div class="margen"><a class="codigo" href="#{html.escape(uno.codigo)}">'
        f"{html.escape(uno.codigo)}</a>{gravedades}</div>"
        f'<div class="cuerpo">{cuerpo}{varias}'
        f'<dl><dt>Norma</dt><dd>{html.escape(etiqueta)} — {html.escape(detalle)}</dd>'
        f"<dt>Se emite en</dt><dd>validador/{html.escape(uno.modulo)}"
        f":{uno.linea}</dd></dl></div></article>"
    )


def _cuerpo(codigos: list[Codigo], sin_leer: list[SinLeer]) -> str:
    familias: dict[str, list[Codigo]] = {}
    for uno in codigos:
        familias.setdefault(uno.familia, []).append(uno)

    sin_explicar = sum(1 for c in codigos if not explicar(c.codigo, c.familia)[0])
    propias = sum(1 for c in codigos if explicar(c.codigo, c.familia)[1])

    partes = [
        '<section id="resumen"><p class="rotulo">Catálogo</p>',
        '<h2 class="titulo">Los {} códigos que puede sacar este validador.</h2>'
        .format(len(codigos)),
        '<p class="texto" style="color:var(--tinta-2)">Salen del código fuente, '
        "no de una lista escrita a mano: se leen de las propias llamadas a "
        "<code>Incidencia(...)</code> al montar esta página, y de las tablas de "
        "reglas que las alimentan. Lo que puede faltar es la explicación, y "
        "cuando falta se dice."
        # Antes aquí ponía «así que aquí no puede faltar uno que exista», y era
        # mentira: el lector solo miraba el primer argumento de la llamada, y
        # los diecisiete códigos que salen de una tabla recorrida con un `for`
        # —BR-02 a BR-15, BR-22, BR-23 y BR-26— no aparecían. Ahora las tablas
        # se leen, y lo que sigue sin poder leerse se cuenta aquí al lado en
        # vez de prometerse que no existe.
        + (f" Otros {len(sin_leer)} se componen al validar, con la categoría "
           "de la operación, y no se pueden leer del fuente: no están en esta "
           "lista, y por eso se dicen." if sin_leer else "")
        + "</p>",
        # Las tres cifras y no solo la buena. «Sin explicar: 0» a secas es
        # verdad y engaña: deja creer que están explicados uno a uno cuando la
        # mayoría llevan la de su familia, que dice de dónde viene la
        # exigencia y no qué pasó exactamente. El hueco es ese, y se cuenta.
        '<dl class="ficha">'
        f"<div><dt>Códigos</dt><dd>{len(codigos)}</dd></div>"
        f"<div><dt>Familias</dt><dd>{len(familias)}</dd></div>"
        f"<div><dt>Explicados uno a uno</dt><dd>{propias}</dd></div>"
        f"<div><dt>Solo con la de su familia</dt>"
        f"<dd>{len(codigos) - propias - sin_explicar}</dd></div>"
        + (f"<div><dt>Sin explicar</dt><dd>{sin_explicar}</dd></div>"
           if sin_explicar else "")
        # A la vista y con las demás, no en una nota al pie: es el único sitio
        # donde este catálogo admite que no está entero, y esconderlo abajo
        # sería la versión educada de no decirlo.
        # Sin coletilla debajo del numero: `.pie` solo esta definida en
        # `tesis.html` y aqui saldria el texto pegado a la cifra. Lo que
        # significa ya lo dice el parrafo de arriba.
        + (f"<div><dt>Compuestos al validar</dt>"
           f"<dd>{len(sin_leer)}</dd></div>" if sin_leer else "")
        + "</dl></section>",
    ]

    for familia, suyos in familias.items():
        texto, _ = explicar("", familia)
        partes.append(
            f'<section id="familia-{html.escape(familia)}">'
            f'<p class="rotulo">{html.escape(familia)}</p>'
            f'<h2 class="titulo">{len(suyos)} '
            f"{'código' if len(suyos) == 1 else 'códigos'}</h2>"
            + (f'<p class="texto" style="color:var(--tinta-2)">'
               f"{html.escape(texto)}</p>" if texto else "")
            + '<div class="fichas">'
            + "".join(_fila(uno) for uno in suyos)
            + "</div></section>"
        )
    return "\n".join(partes)


def montar_pagina(plantilla: Path, destino: Path,
                  carpeta: Path | None = None) -> int:
    """Escribe la página y devuelve cuántos códigos ha metido.

    `plantilla` es `web/incidencias.html`, que trae la cabecera, el pie y el
    hueco donde va esto. Se separa así para que la página comparta cabecera y
    estilo con las demás sin copiarlos, que es como acaban derivando.
    """
    codigos = codigos_del_paquete(carpeta)
    sin_leer = sin_leer_del_paquete(carpeta)
    texto = plantilla.read_text(encoding="utf-8")
    if HUECO not in texto:
        raise ValueError(
            f"«{plantilla}» ya no lleva la marca {HUECO}, que es donde va el "
            "catálogo. Sin ella se publicaría la página con el hueco vacío y "
            "sin un solo código, que es de las cosas que no dan error."
        )
    destino.write_text(texto.replace(HUECO, _cuerpo(codigos, sin_leer)), encoding="utf-8")
    return len(codigos)
