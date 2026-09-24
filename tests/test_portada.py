# -*- coding: utf-8 -*-
"""Lo que la portada enseña de muestra es lo que dice el validador.

Por qué existe
--------------
Desde el 23-09-2026 la herramienta va arriba, dentro de un folio que enseña
antes lo que devuelve: tres glosas de las facturas de muestra y, debajo, la
zona de soltar. Esas tres glosas están escritas a mano en `index.html`, porque
tienen que estar en la primera pantalla antes de que el validador haya
terminado de bajar. Y todo lo que está escrito a mano se desvía: el día que
cambie un mensaje o una regla, la portada enseñaría una glosa que el
validador ya no escribe, que es exactamente prometer de más.

Así que aquí se valida cada muestra y se compara, glosa a glosa: el código,
la gravedad, la norma, el campo, lo que tiene la factura y cada frase del
mensaje, que tiene que ser frase entera del mensaje de verdad. Y lo mismo con
las cuatro facturas de muestra que se pueden abrir: que existan, que viajen
con la página y que sean del formato que dice su etiqueta.
"""
from __future__ import annotations

import datetime
import html
import re
from pathlib import Path

import pytest

from validador import factura
from validador.formato import CII, EDIFACT, FACTURAE, UBL

RAIZ = Path(__file__).resolve().parents[1]
INDEX = RAIZ / "web" / "index.html"
GLOSA_JS = RAIZ / "web" / "glosa.js"
EJEMPLOS = RAIZ / "ejemplos"
HOY = datetime.date(2026, 9, 20)


def _texto(trozo: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", trozo)).split())


def _glosas_del_folio() -> list[dict]:
    pagina = INDEX.read_text(encoding="utf-8")
    folio = re.search(r'<div class="muestra"[^>]*>(.*?)\n          </div>\n', pagina, re.S)
    assert folio, "index.html ya no lleva las glosas de muestra en el folio"
    glosas = []
    for clase, ejemplo, cuerpo in re.findall(
            r'<div class="glosa (\w+)" data-ejemplo="([^"]+)">(.*?)\n            </div>',
            folio[1], re.S):
        campo = lambda patron: _texto(re.search(patron, cuerpo, re.S)[1])
        glosas.append({
            "gravedad": clase, "ejemplo": ejemplo,
            "codigo": campo(r'<span class="codigo">(.*?)</span>'),
            "norma": campo(r'<span class="norma">(.*?)</span>'),
            "campo": campo(r'<p class="dato"><span>(.*?)</span>'),
            "tiene": campo(r'<p class="dato">.*?<b>(.*?)</b>'),
            "mensaje": campo(r'<p class="mensaje">(.*?)</p>'),
        })
    return glosas


def _informe(nombre: str):
    return factura.validar_archivo(str(EJEMPLOS / nombre), hoy=HOY)


def test_el_folio_lleva_un_error_un_aviso_y_una_nota():
    """Las tres gravedades son lo que hay que ver para saber qué da esto."""
    assert [g["gravedad"] for g in _glosas_del_folio()] == ["error", "aviso", "nota"]


@pytest.mark.parametrize("glosa", _glosas_del_folio(), ids=lambda g: g["codigo"])
def test_cada_glosa_del_folio_es_la_que_escribe_el_validador(glosa):
    informe = _informe(glosa["ejemplo"])
    suyas = [i for i in informe.incidencias if i.codigo == glosa["codigo"]]
    assert len(suyas) == 1, (
        f"{glosa['ejemplo']} ya no saca {glosa['codigo']} (o lo saca "
        f"{len(suyas)} veces), y la portada lo enseña como suyo")
    i = suyas[0]
    assert i.gravedad == glosa["gravedad"]
    assert factura.origen(i) == glosa["norma"]
    assert i.campo == glosa["campo"]
    assert i.encontrado == glosa["tiene"]
    # Resumida, pero con frases enteras del mensaje de verdad: ni una palabra
    # que el validador no diga, ni una frase cortada.
    mensaje = " ".join(i.mensaje.split())
    assert glosa["mensaje"] in mensaje, (
        f"«{glosa['mensaje']}» no está en el mensaje de {i.codigo}: {mensaje}")
    empieza = mensaje.index(glosa["mensaje"])
    assert empieza == 0 or mensaje[:empieza].endswith(". "), (
        f"la glosa de {i.codigo} empieza a mitad de una frase")
    assert glosa["mensaje"].endswith("."), (
        f"la glosa de {i.codigo} acaba a mitad de una frase")


def _muestras() -> list[tuple[str, str, str]]:
    pagina = INDEX.read_text(encoding="utf-8")
    return re.findall(
        r'<li><button type="button" data-ejemplo="([^"]+)" disabled>([^<]+)</button> '
        r'<span>([^<]+)</span></li>', pagina)


def test_son_cuatro_y_todas_viajan_con_la_pagina():
    """Solo se puede abrir lo que la página se trae: `EJEMPLOS` de glosa.js."""
    muestras = _muestras()
    assert len(muestras) == 4, f"la portada ofrece {len(muestras)} muestras y son cuatro"
    viajan = GLOSA_JS.read_text(encoding="utf-8")
    for ejemplo, texto, _ in muestras:
        assert texto == ejemplo, f"el botón de {ejemplo} dice «{texto}»"
        assert (EJEMPLOS / ejemplo).is_file(), f"{ejemplo} no está en ejemplos/"
        assert f'"{ejemplo}"' in viajan, f"{ejemplo} no está en EJEMPLOS de glosa.js"


@pytest.mark.parametrize("ejemplo,texto,etiqueta", _muestras())
def test_cada_muestra_es_del_formato_que_dice(ejemplo, texto, etiqueta):
    deteccion = _informe(ejemplo).deteccion
    nombre = {FACTURAE: "Facturae", UBL: "UBL", CII: "CII", EDIFACT: "EDIFACT"}
    esperada = nombre[deteccion.familia] + (" firmada" if deteccion.firmado else "")
    assert etiqueta == esperada, f"{ejemplo} se anuncia como «{etiqueta}» y es «{esperada}»"


def test_entre_las_cuatro_salen_las_tres_gravedades():
    """Lo que dice el comentario de las muestras, y por lo que son estas cuatro."""
    salen = {i.gravedad for ejemplo, _, _ in _muestras()
             for i in _informe(ejemplo).incidencias}
    assert salen >= {"error", "aviso", "nota"}, f"entre las cuatro solo salen {salen}"
