# -*- coding: utf-8 -*-
"""Un comentario XML no cambia lo que dice un documento, y aquí tampoco.

Por qué existe
--------------
El escaneo de seguridad del 01 al 03-11-2026 encontró la misma grieta en tres
sitios a la vez: las reglas de Facturae (`facturae._texto`), el lector común
de UBL y CII (`sintaxis.texto`) y la fecha de la firma (`firma._fecha_de`).
Los tres leían el valor de un elemento con `.text` de lxml, y `.text` es solo
el trozo de texto **anterior al primer hijo**: un comentario lo corta.

    <InvoiceNumber>1<!-- -->23</InvoiceNumber>

Para lxml, `.text` vale «1». Para XPath, `string()` vale «123», que es lo que
la norma de XML llama el valor del elemento y lo que lee cualquier otro
programa. Y para la firma el comentario **no existe**: la canonicalización sin
comentarios, que es la habitual, lo quita antes de calcular el resumen. Medido
con el `parser()` de aquí el 08-11-2026: `.text` da «1», `findtext` da «1»,
`string()` da «1234» y C14N escribe `123<?pi y?>4`.

Así que un tercero sin ninguna clave podía coger una factura firmada, meterle
un comentario donde quisiera, y el informe seguía diciendo que nadie la había
tocado mientras las reglas leían otra cosa. Con `20<!-- -->26-03-15` en el
`SigningTime` la fecha de firma desaparecía, y con ella FIRMA-CADUCADA; con
`1<!-- -->23` en el número la factura dejaba de ser duplicada de sí misma.

Por qué se prueba así
---------------------
No basta con mirar los tres sitios del escaneo: leían igual 38 líneas
repartidas en 14 módulos, y la que no se arregle es el siguiente hallazgo. Así que la prueba no pregunta a ningún lector: mete un comentario
**en mitad de cada valor** de cada documento y exige que el informe sea el
mismo, palabra por palabra. Un lector que se quede atrás cambia algún mensaje y
la pone en rojo, esté en el módulo que esté.

Lo que no se hace es quitar los comentarios al leer (`remove_comments=True`
en el parser): una firma con `#WithComments` sí los cubre, y quitarlos daría
por rota una firma buena.
"""
from __future__ import annotations

import datetime
import io
import pathlib
import re
import tokenize
from datetime import timedelta

import pytest
from lxml import etree

from validador import factura, firma
from validador.formato import parser

from test_firma import HOY as HOY_DE_LA_FIRMA
from test_firma import certificado, documento

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EJEMPLOS = RAIZ / "ejemplos"
HOY = datetime.date(2026, 9, 20)


def con_comentarios(datos: bytes) -> bytes:
    """El mismo documento con un comentario en mitad de cada valor.

    Solo en las hojas, que es donde vive el valor de un campo, y solo si tienen
    al menos dos caracteres, para que el comentario quede **dentro** del valor
    y no delante o detrás, donde `.text` ya leía bien.
    """
    raiz = etree.fromstring(datos, parser())
    tocadas = 0
    for nodo in raiz.iter():
        if not isinstance(nodo.tag, str) or len(nodo) or not nodo.text:
            continue
        texto = nodo.text
        if len(texto.strip()) < 2:
            continue
        mitad = len(texto) // 2
        nodo.text = texto[:mitad]
        comentario = etree.Comment(" partido ")
        comentario.tail = texto[mitad:]
        nodo.append(comentario)
        tocadas += 1
    assert tocadas, "el documento no tiene ningún valor que partir"
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def lo_que_dice(informe) -> list[tuple]:
    return sorted(
        (i.codigo, i.gravedad, i.mensaje, i.campo, i.esperado, i.encontrado)
        for i in informe.incidencias or []
    )


XML = sorted(f.name for f in EJEMPLOS.iterdir() if f.suffix == ".xml")


def test_hay_de_cada_sintaxis():
    """Si un día se quitan los ejemplos de una sintaxis, esta prueba deja de
    mirarla sin decir nada. Que lo diga."""
    assert {"fe-0001.xml", "f-0001.xml", "cii-A-0001.xml", "r-0001.xml"} <= set(XML)


@pytest.mark.parametrize("nombre", XML)
def test_un_ejemplo_dice_lo_mismo_con_comentarios(nombre):
    datos = (EJEMPLOS / nombre).read_bytes()
    antes = factura.validar(datos, hoy=HOY)
    despues = factura.validar(con_comentarios(datos), hoy=HOY)
    assert antes.validado and despues.validado
    assert lo_que_dice(despues) == lo_que_dice(antes)
    assert despues.firma == antes.firma


VIEJO = dict(
    desde=HOY_DE_LA_FIRMA - timedelta(days=800),
    hasta=HOY_DE_LA_FIRMA - timedelta(days=30),
)


class TestUnaFirmaDeVerdad:
    """Con una firma que se verifica de verdad, la de `test_firma`, que es
    donde el comentario hacía daño: lo firmado seguía cuadrando."""

    def test_la_firma_se_sigue_verificando(self):
        datos = con_comentarios(documento())
        raiz = etree.fromstring(datos, parser())
        assert firma.momento_de_firma(firma.hay_firma(raiz)[0]) == HOY_DE_LA_FIRMA

    def test_un_comentario_en_la_fecha_no_borra_la_caducidad(self):
        datos = documento(cert=certificado(**VIEJO))
        antes = factura.validar(datos, hoy=HOY_DE_LA_FIRMA.date())
        assert "FIRMA-CADUCADA" in {i.codigo for i in antes.incidencias}
        despues = factura.validar(con_comentarios(datos), hoy=HOY_DE_LA_FIRMA.date())
        assert lo_que_dice(despues) == lo_que_dice(antes)
        assert despues.firma == antes.firma

    def test_ni_un_comentario_solo_en_la_fecha(self):
        # El caso del escaneo tal cual, sin nada más tocado: si la prueba de
        # arriba fallara por otro lector, esta dice si la fecha está bien.
        raiz = etree.fromstring(documento(cert=certificado(**VIEJO)), parser())
        tiempo = raiz.xpath("//*[local-name()='SigningTime']")[0]
        escrito = tiempo.text
        tiempo.text = escrito[:2]
        comentario = etree.Comment(" ")
        comentario.tail = escrito[2:]
        tiempo.append(comentario)
        salen = factura.validar(etree.tostring(raiz), hoy=HOY_DE_LA_FIRMA.date())
        codigos = {i.codigo for i in salen.incidencias}
        assert "FIRMA-ALTERADA" not in codigos
        assert "FIRMA-CADUCADA" in codigos


# --- Que no vuelva a entrar -------------------------------------------------
#
# La prueba de arriba solo ve los lectores por los que pasan los ejemplos. Un
# lector nuevo con `.text` en una regla que ningún ejemplo dispara pasaría por
# ella sin que nadie se enterara, así que esta lee el código: fuera de
# comentarios y cadenas, ni `.text` leído, ni `findtext`, ni rutas con
# `text()`, que devuelven los trozos sueltos que parte un comentario.
#
# EDIFACT se queda fuera con nombre y razón: su árbol lo construye
# `edifact.py` a partir de los segmentos, y ahí no hay comentarios que puedan
# partir nada.
EXENTOS = {"edifact.py"}

# La palabra entera: `getcontext()` también acaba en «text()».
_RUTA_CON_TEXT = re.compile(r"(?<!\w)text\(\)")


def _lecturas_con_text(fuente: str) -> list[int]:
    fichas = list(tokenize.generate_tokens(io.StringIO(fuente).readline))
    lineas = []
    for i, ficha in enumerate(fichas):
        if ficha.type == tokenize.NAME and ficha.string == "findtext":
            lineas.append(ficha.start[0])
        elif ficha.type == tokenize.NAME and ficha.string == "text":
            anterior = fichas[i - 1] if i else None
            siguiente = fichas[i + 1] if i + 1 < len(fichas) else None
            if anterior is None or anterior.string != ".":
                continue
            if siguiente is not None and siguiente.string == "=":
                continue  # escribirlo no es leerlo
            lineas.append(ficha.start[0])
        elif ficha.type in (tokenize.STRING, getattr(tokenize, "FSTRING_MIDDLE", -1)):
            if _RUTA_CON_TEXT.search(ficha.string):
                lineas.append(ficha.start[0])
    return lineas


def test_ningun_lector_usa_text():
    sueltos = []
    for fichero in sorted((RAIZ / "validador").glob("*.py")):
        if fichero.name in EXENTOS:
            continue
        for linea in _lecturas_con_text(fichero.read_text(encoding="utf-8")):
            sueltos.append(f"validador/{fichero.name}:{linea}")
    assert not sueltos, (
        "estos sitios leen el valor de un elemento sin `como_texto`, y un "
        "comentario XML les cambia lo que leen sin romper la firma: "
        + ", ".join(sueltos)
    )


def test_el_vigilante_ve_lo_que_tiene_que_ver():
    """Sin esto, un vigilante que no encuentra nada porque está roto sale
    igual de verde que uno que no encuentra nada porque no hay nada."""
    assert _lecturas_con_text("x = nodo.text\n") == [1]
    assert _lecturas_con_text("x = nodo.findtext('a')\n") == [1]
    assert _lecturas_con_text("x = nodo.xpath('./a/text()')\n") == [1]
    assert _lecturas_con_text("x = nodo.xpath(f'./{a}/text()')\n") == [1]
    assert _lecturas_con_text("nodo.text = 'a'\n") == []
    assert _lecturas_con_text("# .text en un comentario\n") == []
    assert _lecturas_con_text('"""con getcontext()"""\n') == []
