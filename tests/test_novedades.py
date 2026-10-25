# -*- coding: utf-8 -*-
"""Las novedades y su canal Atom, desde el 25-10-2026.

Lo que más importa aquí es la negativa: lo que se apunta a mano se queda
atrás, y lo único que lo impide es que `revisar` no deje montar el sitio si
el catálogo no cuadra con lo apuntado. Cada una de sus cuatro salidas se
provoca. Lo demás vigila que la página y el canal digan lo mismo y que el id
de cada entrada no se mueva, porque un lector de noticias que ve un id nuevo
enseña otra vez lo que ya enseñó.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from lxml import etree

from validador import novedades
from validador.codigos import codigos_del_paquete

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"
ATOM = {"a": "http://www.w3.org/2005/Atom"}
DOMINIO = "https://www.glosa-e.com"

PEQUENO = """\
# un comentario
fecha: 2026-10-20
id: la-segunda
titulo: Dos códigos
nuevos: NUEVO-A NUEVO-B
retirados: VIEJO-1
texto: Entran dos y sale uno, con un texto que sigue
  en la línea de abajo.

fecha: 2026-10-10
id: la-primera
titulo: Uno <solo> & sin más
nuevos: NUEVO-C
texto: Entra uno.

partida: 2026-10-06
codigos: VIEJO-1 VIEJO-2
"""
CATALOGO_PEQUENO = {"VIEJO-2", "NUEVO-A", "NUEVO-B", "NUEVO-C"}
PLANTILLA = f"<html><body><main>{novedades.HUECO}</main></body></html>"


def _escrito(tmp_path, texto):
    ruta = tmp_path / novedades.FUENTE
    ruta.write_text(texto, encoding="utf-8")
    return ruta


def _articulo(nombre, fecha, cambiada=None):
    return SimpleNamespace(
        nombre=nombre, fecha=fecha, cambiada=cambiada or fecha,
        titulo=f"El artículo {nombre}", entradilla="De qué va.")


@pytest.fixture
def pequenas(tmp_path):
    return novedades.leer(_escrito(tmp_path, PEQUENO))


class TestLeer:
    def test_lee_las_entradas_y_la_partida(self, pequenas):
        assert [e.id for e in pequenas.entradas] == ["la-segunda", "la-primera"]
        assert pequenas.partida == dt.date(2026, 10, 6)
        assert pequenas.de_partida == {"VIEJO-1", "VIEJO-2"}
        segunda = pequenas.entradas[0]
        assert segunda.nuevos == ("NUEVO-A", "NUEVO-B")
        assert segunda.retirados == ("VIEJO-1",)
        assert segunda.texto.endswith("que sigue en la línea de abajo.")

    @pytest.mark.parametrize("cambio, dice", [
        (("id: la-primera\n", "id: la-primera\nautor: alguien\n"), "claves que no existen"),
        (("id: la-primera\n", "id: la-segunda\n"), "ids repetidos"),
        (("fecha: 2026-10-10\n", "fecha: 2026-10-06\n"), "de la partida o de antes"),
        (("fecha: 2026-10-10\n", "fecha: 10-10-2026\n"), "AAAA-MM-DD"),
        (("id: la-primera\n", "id: La Primera\n"), "minúsculas"),
        (("nuevos: NUEVO-C\n", "nuevos: NUEVO-C NUEVO-C\n"), "repetido"),
        (("texto: Entra uno.\n", ""), "le falta texto"),
        (("partida: 2026-10-06\ncodigos: VIEJO-1 VIEJO-2\n", ""), "no tiene partida"),
    ])
    def test_se_niega_a_lo_mal_escrito(self, tmp_path, cambio, dice):
        viejo, nuevo = cambio
        assert PEQUENO.count(viejo) == 1
        with pytest.raises(novedades.NovedadMal, match=dice):
            novedades.leer(_escrito(tmp_path, PEQUENO.replace(viejo, nuevo)))


class TestRevisar:
    """Las cuatro maneras de quedarse atrás, cada una provocada."""

    def test_lo_que_cuadra_pasa(self, pequenas):
        novedades.revisar(pequenas, CATALOGO_PEQUENO)

    def test_un_codigo_nuevo_sin_apuntar_no_pasa(self, pequenas):
        with pytest.raises(novedades.NovedadMal, match="un código no sale en las novedades: NUEVO-D"):
            novedades.revisar(pequenas, CATALOGO_PEQUENO | {"NUEVO-D"})

    def test_un_retirado_que_sigue_no_pasa(self, pequenas):
        with pytest.raises(novedades.NovedadMal, match="siguen en el catálogo: VIEJO-1"):
            novedades.revisar(pequenas, CATALOGO_PEQUENO | {"VIEJO-1"})

    def test_uno_que_se_va_sin_decirlo_no_pasa(self, pequenas):
        with pytest.raises(novedades.NovedadMal, match="nadie lo ha dicho: VIEJO-2"):
            novedades.revisar(pequenas, CATALOGO_PEQUENO - {"VIEJO-2"})

    def test_retirar_uno_que_nunca_estuvo_no_pasa(self, tmp_path):
        leidas = novedades.leer(_escrito(
            tmp_path, PEQUENO.replace("retirados: VIEJO-1\n", "retirados: VIEJO-1 OTRO\n")))
        with pytest.raises(novedades.NovedadMal, match="nunca estuvieron: OTRO"):
            novedades.revisar(leidas, CATALOGO_PEQUENO)


class TestLasDeVerdad:
    """`web/novedades.txt` contra el catálogo que hay hoy en el fuente."""

    def test_cuadran_con_el_catalogo(self):
        leidas = novedades.leer(WEB / novedades.FUENTE)
        novedades.revisar(leidas, {c.codigo for c in codigos_del_paquete()})

    def test_sin_rayas_ni_comillas_angulares_ni_plural(self):
        # Lo que dice `novedades.txt` sale tal cual en la página y en el
        # canal, así que se le pide lo mismo que a las páginas (test_voz).
        leidas = novedades.leer(WEB / novedades.FUENTE)
        for e in leidas.entradas:
            for texto in (e.titulo, e.texto):
                assert not re.search("[—«»]", texto), e.id
                assert not re.search(r"\b\w+(?:amos|emos|imos)\b", texto), e.id


class TestPagina:
    def test_enlaza_solo_las_fichas_que_hay(self, pequenas):
        hecha = novedades.pagina(PLANTILLA, pequenas, [], {"NUEVO-A"}, 4)
        assert novedades.HUECO not in hecha
        assert re.findall(r'href="(\./codigo-[^"]+)"', hecha) == ["./codigo-NUEVO-A.html"]
        # El retirado sale tachado y sin enlace: su ficha ya no es la suya.
        assert '<ul class="codigos retirados"><li>VIEJO-1</li></ul>' in hecha
        assert 'id="la-segunda"' in hecha and 'id="la-primera"' in hecha
        assert "Uno &lt;solo&gt; &amp; sin más" in hecha
        assert "hoy tiene 4." in hecha

    def test_mezcla_reglas_y_articulos_por_fecha(self, pequenas):
        hecha = novedades.pagina(
            PLANTILLA, pequenas,
            [_articulo("bitacora-medio.html", dt.date(2026, 10, 15))], set(), 4)
        orden = re.findall(r'<time datetime="([^"]+)"', hecha)
        assert orden == ["2026-10-20", "2026-10-15", "2026-10-10"]
        assert '<a href="./bitacora-medio.html">' in hecha

    def test_sin_hueco_se_niega(self, pequenas):
        with pytest.raises(novedades.NovedadMal, match="ya no lleva"):
            novedades.pagina("<html></html>", pequenas, [], set(), 4)


class TestCanal:
    def _leido(self, pequenas, articulos=()):
        return etree.fromstring(
            novedades.canal(pequenas, list(articulos), DOMINIO).encode("utf-8"))

    def test_es_atom_con_lo_que_pide_la_norma(self, pequenas):
        # RFC 4287, 4.1.1: el canal lleva id, title y updated, y autor si no
        # lo lleva cada entrada; cada entrada, id, title y updated.
        raiz = self._leido(pequenas, [_articulo("bitacora-a.html", dt.date(2026, 10, 15),
                                                dt.date(2026, 10, 22))])
        assert raiz.tag == "{http://www.w3.org/2005/Atom}feed"
        for falta in ("a:id", "a:title", "a:updated", "a:author/a:name"):
            assert raiz.find(falta, ATOM) is not None, falta
        assert raiz.find("a:link[@rel='self']", ATOM).get("href") == f"{DOMINIO}/novedades.xml"
        entradas = raiz.findall("a:entry", ATOM)
        assert len(entradas) == 3
        for e in entradas:
            for falta in ("a:id", "a:title", "a:updated", "a:summary"):
                assert e.find(falta, ATOM) is not None, falta
        # El canal se da por cambiado con lo último que cambió, que aquí es
        # un artículo retocado después de las dos reglas.
        assert raiz.findtext("a:updated", namespaces=ATOM) == "2026-10-22T00:00:00Z"

    def test_los_ids_no_dependen_de_nada_mas_que_del_id(self, pequenas, tmp_path):
        # El mismo id con otro título y otra fecha sigue siendo la misma
        # entrada para el lector, que es lo que se quiere al corregir una
        # errata.
        antes = self._leido(pequenas, [_articulo("bitacora-a.html", dt.date(2026, 10, 15))])
        otro = novedades.leer(_escrito(tmp_path, PEQUENO.replace(
            "titulo: Dos códigos", "titulo: Dos códigos, corregido")))
        despues = self._leido(otro, [_articulo("bitacora-a.html", dt.date(2026, 10, 15))])
        ids = [e.findtext("a:id", namespaces=ATOM) for e in antes.findall("a:entry", ATOM)]
        assert ids == [e.findtext("a:id", namespaces=ATOM)
                       for e in despues.findall("a:entry", ATOM)]
        assert ids == [f"{DOMINIO}/novedades#la-segunda", f"{DOMINIO}/bitacora-a",
                       f"{DOMINIO}/novedades#la-primera"]
        assert len(set(ids)) == len(ids)

    def test_escapa_lo_que_lleva_el_texto(self, pequenas):
        raiz = self._leido(pequenas)
        titulos = [e.findtext("a:title", namespaces=ATOM) for e in raiz.findall("a:entry", ATOM)]
        assert "Uno <solo> & sin más" in titulos
