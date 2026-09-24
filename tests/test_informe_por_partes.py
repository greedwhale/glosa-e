# -*- coding: utf-8 -*-
"""La forma, el contenido y la firma: el informe empieza diciendo qué se miró.

Por qué existe
--------------
El informe de la página decía qué se había comprobado **al final**, en una
frase de corrido, debajo de todas las glosas. Quien leía «Sin errores» arriba
no sabía contra qué hasta haber bajado entero, y en un informe de once glosas
eso es no saberlo. Desde el 23-09-2026 lo dice antes del detalle, en tres
columnas numeradas como en «Qué mira» de la portada, con la cuenta de cada
una al lado. La idea es la del resumen del HTTP Observatory de Mozilla.

Lo peligroso de tener dos sitios que dicen lo mismo es que un día digan
cosas distintas, y aquí lo distinto sería una columna diciendo «Sin errores»
de algo que la frase dice que no se ha mirado. Por eso las dos salen de la
misma cuenta, `InformeLote._alcance_por_partes`, y esto vigila las tres cosas
que lo sostienen: que cada familia de códigos tenga su parte, que lo que dice
una columna esté dicho en la frase, y que ninguna columna diga «Sin errores»
sin haber mirado nada.
"""
from __future__ import annotations

import datetime
import pathlib
import re
from itertools import product

import pytest

from validador import factura
from validador.codigos import codigos_del_paquete
from validador.incidencias import AVISO, ERROR, familia_de

from test_en_un_movil import _regla

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EJEMPLOS = RAIZ / "ejemplos"
HOY = datetime.date(2026, 9, 20)
BANDERAS = list(product((True, False), repeat=3))   # forma, anclas, listas


def _lote(*nombres: str) -> factura.InformeLote:
    return factura.validar_lote([EJEMPLOS / n for n in nombres], hoy=HOY)


def _por_nombre(partes) -> dict:
    return {p.nombre: p for p in partes}


def test_cada_familia_tiene_su_parte_y_ninguna_sobra():
    """Cerrada en los dos sentidos, como la tabla de los ejemplos.

    Una familia nueva sin parte haría fallar el informe en el navegador al
    contarla; una parte de una familia que ya no existe es una tabla que
    nadie mira.
    """
    hay = {c.familia for c in codigos_del_paquete()}
    tabla = set(factura.PARTE_DE_LA_FAMILIA)
    assert not hay - tabla, (
        f"estas familias no dicen de qué parte son: {sorted(hay - tabla)}. "
        "Van en PARTE_DE_LA_FAMILIA, en validador/factura.py.")
    assert not tabla - hay, (
        f"estas familias ya no existen: {sorted(tabla - hay)}.")


def test_la_familia_es_la_misma_que_ordena_la_pagina():
    """Una regla, dos usos: si se separan, el catálogo y el informe no casan."""
    for c in codigos_del_paquete():
        assert c.familia == familia_de(c.codigo)
    assert familia_de("REVOCADO") == "REVOCADO"
    assert familia_de("BR-CO-10") == "BR"


@pytest.mark.parametrize("nombre", sorted(p.name for p in EJEMPLOS.iterdir()))
@pytest.mark.parametrize("forma,anclas,listas", BANDERAS)
def test_ninguna_columna_dice_mas_que_la_frase(nombre, forma, anclas, listas):
    """Lo que dice una columna está dicho, tal cual, en la frase del final.

    Y la guarda más importante: «Sin errores» solo en una parte que se ha
    mirado. Con los diez ejemplos y las ocho combinaciones de lo que puede
    faltar —esquemas, anclas, listas—.
    """
    lote = _lote(nombre)
    frase = lote.alcance(forma, anclas, listas)
    partes = lote.partes(forma, anclas, listas)
    assert [p.nombre for p in partes] == list(factura.PARTES)
    for p in partes:
        if p.resultado == "Sin errores":
            assert p.mirado, f"{nombre}: «{p.nombre}» sin errores sin haber mirado nada"
        if p.mirado:
            trozo = p.mirado[0].lower() + p.mirado[1:-1]
            assert trozo in frase, f"{nombre}: «{p.mirado}» no está en la frase"
        if p.sin_mirar and p.nombre != factura.PARTE_FORMA:
            trozo = p.sin_mirar.removeprefix("No se comprueba ")[:-1]
            assert trozo in frase, f"{nombre}: «{p.sin_mirar}» no está en la frase"


@pytest.mark.parametrize("nombre", sorted(p.name for p in EJEMPLOS.iterdir()))
def test_las_cuentas_de_las_tres_suman_lo_que_hay(nombre):
    """Ninguna queja se queda sin columna, y ninguna se cuenta dos veces."""
    lote = _lote(nombre)
    todas = [i for _, inf in lote.informes for i in inf.incidencias] + lote.cruzadas
    for gravedad, palabra in ((ERROR, "error"), (AVISO, "aviso")):
        hay = sum(1 for i in todas if i.gravedad == gravedad
                  and factura.PARTE_DE_LA_FAMILIA[familia_de(i.codigo)])
        dicen = sum(
            int(n) for p in lote.partes(True, True, False)
            for n in re.findall(rf"(\d+) {palabra}", p.resultado))
        assert dicen == hay, f"{nombre}: {dicen} {palabra}(es) contados de {hay}"


def test_la_firmada_de_ejemplo():
    """`fe-0001.xml`, que es la del botón de la portada.

    En la suite no hay esquemas ni anclas —`conftest.py` dice por qué—, así
    que la forma sale sin mirar y la cadena dice que faltan anclas: lo mismo
    que vería quien la validara en consola sin ellas.
    """
    partes = _por_nombre(_lote("fe-0001.xml").partes(forma=False, anclas=False))
    forma = partes[factura.PARTE_FORMA]
    assert forma.resultado == "Sin mirar"
    assert forma.sin_mirar == (
        "No se comprueba la forma: no hay esquemas XSD con que mirarla.")
    contenido = partes[factura.PARTE_CONTENIDO]
    assert (contenido.resultado, contenido.gravedad) == ("Sin errores", None)
    assert contenido.mirado.startswith("La aritmética del formato Facturae")
    firma = partes[factura.PARTE_FIRMA]
    assert (firma.resultado, firma.gravedad) == ("2 avisos", AVISO)
    assert firma.mirado.startswith("Que las firmas no estén rotas")
    assert firma.sin_mirar.startswith("No se comprueba de quién es el certificado")


def test_una_sin_firma_y_con_errores():
    partes = _por_nombre(_lote("f-0006.xml").partes(forma=True))
    assert partes[factura.PARTE_CONTENIDO].resultado == "2 errores"
    assert partes[factura.PARTE_CONTENIDO].gravedad == ERROR
    firma = partes[factura.PARTE_FIRMA]
    assert (firma.resultado, firma.mirado) == ("Sin firma", "")
    assert firma.sin_mirar == "No se comprueba la validez de las firmas electrónicas."


def test_edifact_no_tiene_forma_que_mirar():
    """Con esquemas puestos, EDIFACT sigue sin tener uno: «No aplica», no «Sin errores»."""
    partes = _por_nombre(_lote("edi-0001.edi").partes(forma=True))
    forma = partes[factura.PARTE_FORMA]
    assert (forma.resultado, forma.mirado) == ("No aplica", "")
    assert "EDIFACT no tiene esquema XSD" in forma.sin_mirar
    assert "el código único de las facturas EDIFACT" in (
        partes[factura.PARTE_CONTENIDO].sin_mirar)


def test_sin_nada_leido_no_hay_partes(tmp_path):
    """Sin partes que enseñar, y la frase de siempre lo dice."""
    lote = factura.validar_lote([tmp_path / "no-existe.xml"], hoy=HOY)
    assert lote.partes() == []
    assert lote.alcance().startswith("No se ha comprobado nada")


# --- La página que lo pinta -------------------------------------------------

INDEX = RAIZ / "web" / "index.html"
GLOSA_JS = RAIZ / "web" / "glosa.js"


def test_la_pagina_pinta_las_partes_que_manda_python():
    """Las columnas salen de `partes`, y la frase solo cuando no hay ninguna.

    Si la página volviera a componer lo mirado por su cuenta, tendríamos dos
    versiones de lo que dice el validador y nos creeríamos la que no corre.
    """
    js, pagina = GLOSA_JS.read_text(encoding="utf-8"), INDEX.read_text(encoding="utf-8")
    assert '_lote.partes(forma=not _c.vacio, anclas=not _a.vacio)' in js
    assert '_lote.alcance(forma=not _c.vacio, anclas=not _a.vacio)' in js, (
        "las partes y la frase tienen que pedirse con las mismas banderas")
    assert "datos.partes.map(" in pagina
    assert "datos.partes.length" in pagina and "escapar(datos.alcance)" in pagina


def test_el_margen_no_pisa_el_filete():
    """El fallo medido: 2 px de solape en los 33 rótulos de un informe.

    Salía de dos medidas que tenían que casar y no casaban: el cuerpo se
    corría 1,35rem a la izquierda sobre un hueco de 1,25rem. Ahora el filete
    es el borde del margen y el aire es su relleno, y no hay nada que casar.
    Medido el 23-09-2026 a 1100 px: 19,6 px de aire en los 34 renglones.
    """
    cuerpo = _regla("index.html", ".glosa .cuerpo")
    assert "margin-left" not in cuerpo, (
        "el cuerpo de la glosa vuelve a correrse hacia el margen: así era "
        "como el texto del margen pisaba el filete")
    margen = _regla("index.html", ".glosa .margen")
    assert "border-right: 1px solid" in margen, "el filete tiene que ser el borde del margen"
    relleno = re.search(r"padding:\s*([^;]+);", margen)[1].split()
    assert relleno[1] == "1.25rem", f"el aire antes del filete es {relleno[1]}, no 1.25rem"
