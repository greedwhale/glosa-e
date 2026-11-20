# -*- coding: utf-8 -*-
"""Un lote, en corto: una línea por aviso, y la explicación en la ficha.

Por qué existe
--------------
Lo propuso el titular el 20-11-2026: con un lote, la página se llenaba de la
misma explicación repetida factura tras factura. Medido ese día con las 169
facturas de muestra: 1.488 glosas y unas 389.000 letras, y las notas eran 302
con solo 33 textos distintos. Con 20 facturas, de 28.657 px de alto a 8.991 en
el escritorio, y de 51.153 a 16.709 en el móvil.

Lo que se vigila aquí es lo que hace que ir en corto no cueste nada:

- **Una factura sola sale entera.** Son unas líneas, y ahí la explicación
  está mejor que a un clic.
- **Un código sin ficha sale entero** aunque el resto vaya en corto, y sin
  montar (sin fichas) todo sale entero. La explicación se lleva a la ficha;
  si no hay ficha, una línea con un código que no lleva a ninguna parte deja
  a quien acaba de ver un ERROR sin saber qué es.
- **La casilla devuelve el lote entero**, también en los ficheros cerrados de
  un lote grande, y repinta solo los ficheros: repintar el informe lo subiría
  arriba del todo.

Aquí no hay navegador, como en `test_lotes_grandes_en_la_pagina`: se lee el
código de la página. Lo que hace de verdad se vio el 20-11-2026 en Edge, en el
escritorio y en el móvil (en `web/LEEME.md`, en el apartado del lote en corto).
"""
from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
INDEX = RAIZ / "web" / "index.html"


def _pagina() -> str:
    return INDEX.read_text(encoding="utf-8")


def _cuerpo(codigo: str, cabecera: str) -> str:
    """De una cabecera de función a la primera llave de cierre en la columna 0."""
    arranca = codigo.index(cabecera)
    return codigo[arranca:codigo.index("\n}", arranca)]


class TestCuandoVaEnCorto:
    def test_solo_un_lote_con_fichas_y_sin_la_casilla(self):
        cuerpo = _cuerpo(_pagina(), "function vaEnCorto(")
        assert "datos.documentos.length > 1" in cuerpo, (
            "una factura sola tiene que salir entera, con su explicación")
        assert "CON_FICHA.size > 0" in cuerpo, (
            "sin fichas no hay dónde leer la explicación: todo tiene que salir entero")
        assert "!conExplicacion" in cuerpo

    def test_por_defecto_va_en_corto(self):
        assert re.search(r"^let conExplicacion = false;$", _pagina(), re.M)


class TestNoSePierdeLaExplicacion:
    def test_un_codigo_sin_ficha_sale_entero(self):
        cuerpo = _cuerpo(_pagina(), "function pintarIncidencias(")
        assert "if (!corto) return incidencias.map(pintarGlosa)" in cuerpo
        assert "conFicha(i) ? pintarLinea(i) : pintarGlosa(i)" in cuerpo, (
            "un código sin ficha iría en una línea que no explica nada y no "
            "lleva a ningún sitio")

    def test_las_notas_que_se_juntan_son_solo_las_que_tienen_ficha(self):
        cuerpo = _cuerpo(_pagina(), "function pintarIncidencias(")
        assert 'i.gravedad === "nota" && conFicha(i)' in cuerpo
        assert "!(i.gravedad === \"nota\" && conFicha(i))" in cuerpo, (
            "una nota sin ficha se quedaría fuera de las dos listas")

    def test_la_linea_lleva_el_codigo_por_quien_decide_el_enlace(self):
        cuerpo = _cuerpo(_pagina(), "function pintarLinea(")
        assert "pintarCodigo(inc.codigo)" in cuerpo
        # Lo que es de esa factura y no está en la ficha: dónde y qué tiene.
        for campo in ("inc.campo", "inc.encontrado", "inc.esperado"):
            assert campo in cuerpo, f"la línea ya no dice {campo}"


class TestLaCasilla:
    def test_sale_en_todo_lote_con_fichas_aunque_este_marcada(self):
        cuerpo = _cuerpo(_pagina(), "function pintarInforme(")
        assert "if (datos.documentos.length > 1 && CON_FICHA.size > 0) {" in cuerpo
        assert "id='con-explicacion'" in cuerpo
        assert '(conExplicacion ? " checked" : "")' in cuerpo, (
            "marcada, la casilla se desmarcaría sola en el lote siguiente")

    def test_repinta_solo_los_ficheros(self):
        cuerpo = _cuerpo(_pagina(), "function pintarInforme(")
        assert "conExplicacion = casilla.checked;" in cuerpo
        assert '$("documentos").innerHTML = pintarDocumentos(datos);' in cuerpo
        assert "<div id='documentos'>" in cuerpo

    def test_los_ficheros_cerrados_siguen_la_casilla(self):
        pagina = _pagina()
        documentos = _cuerpo(pagina, "function pintarDocumentos(")
        assert "cerradosEnCorto = corto;" in documentos
        assert "pintarIncidencias(doc.incidencias, corto)" in documentos
        escuchador = pagina[pagina.index('$("informe").addEventListener("toggle"'):]
        escuchador = escuchador[:escuchador.index("}, true);")]
        assert "pintarIncidencias(doc.incidencias, cerradosEnCorto)" in escuchador, (
            "un fichero cerrado de un lote grande saldría entero con la casilla "
            "sin marcar, o en corto con ella marcada")

    def test_entre_ficheros_sale_entero(self):
        """Lo cruzado son pocas glosas y su explicación es de ese lote."""
        cuerpo = _cuerpo(_pagina(), "function pintarInforme(")
        assert "datos.cruzadas.map(pintarGlosa)" in cuerpo
