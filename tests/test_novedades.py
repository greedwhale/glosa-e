# -*- coding: utf-8 -*-
"""Las novedades y su canal Atom, desde el 25-10-2026, y el botón de seguirlas.

Lo que más importa aquí es la negativa: lo que se apunta a mano se queda
atrás, y lo único que lo impide es que `revisar` no deje montar el sitio si
el catálogo no cuadra con lo apuntado. Cada una de sus cuatro salidas se
provoca. Lo demás vigila que la página y el canal digan lo mismo y que el id
de cada entrada no se mueva, porque un lector de noticias que ve un id nuevo
enseña otra vez lo que ya enseñó. Y el botón de seguir: que no ofrezca un
sitio que no existe, como el boletín de LinkedIn antes de crearse.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

import pytest
from lxml import etree

from validador import atom, novedades
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
PLANTILLA = (f"<html><body><header>{novedades.HUECO_DE_SEGUIR}</header>"
             f"<main>{novedades.HUECO}</main></body></html>")
SEGUIR = '<details class="seguirlas">el botón</details>'
X = "https://x.com/glosa_e"


def _escrito(tmp_path, texto):
    ruta = tmp_path / novedades.FUENTE
    ruta.write_text(texto, encoding="utf-8")
    return ruta


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
        hecha = novedades.pagina(PLANTILLA, pequenas, {"NUEVO-A"}, 4, SEGUIR)
        assert novedades.HUECO not in hecha
        assert re.findall(r'href="(\./codigo-[^"]+)"', hecha) == ["./codigo-NUEVO-A.html"]
        # El retirado sale tachado y sin enlace: su ficha ya no es la suya.
        assert '<ul class="codigos retirados"><li>VIEJO-1</li></ul>' in hecha
        assert 'id="la-segunda"' in hecha and 'id="la-primera"' in hecha
        assert "Uno &lt;solo&gt; &amp; sin más" in hecha
        assert "hoy tiene 4." in hecha

    def test_solo_reglas_y_el_boton_en_su_hueco(self, pequenas):
        hecha = novedades.pagina(PLANTILLA, pequenas, set(), 4, SEGUIR)
        orden = re.findall(r'<li class="novedad" id="([^"]+)"', hecha)
        assert orden == ["la-segunda", "la-primera"]
        assert "bitacora-" not in hecha
        assert f"<header>{SEGUIR}</header>" in hecha
        assert novedades.HUECO_DE_SEGUIR not in hecha

    @pytest.mark.parametrize("hueco", [novedades.HUECO, novedades.HUECO_DE_SEGUIR])
    @pytest.mark.parametrize("veces", [0, 2])
    def test_sin_cada_hueco_o_con_dos_se_niega(self, pequenas, hueco, veces):
        plantilla = PLANTILLA.replace(hueco, hueco * veces)
        with pytest.raises(novedades.NovedadMal, match="ya no lleva"):
            novedades.pagina(plantilla, pequenas, set(), 4, SEGUIR)


class TestPanel:
    """El botón de seguir: un destino por cada sitio que existe."""

    @staticmethod
    def _destinos(hecho):
        return re.findall(r'<p class="opcion"><a href="([^"]+)">([^<]+)</a>', hecho)

    def test_sin_boletin_x_y_los_dos_canales(self):
        hecho = novedades.panel(DOMINIO, X, "bitacora.xml")
        assert self._destinos(hecho) == [
            (X, "Glosa-e en X"),
            ("./novedades.xml", "Canal Atom de las novedades"),
            ("./bitacora.xml", "Canal Atom de la bitácora"),
        ]
        assert "Boletín" not in hecho
        assert hecho.startswith('<details class="seguirlas"><summary>')

    def test_el_boletin_entra_el_primero_cuando_existe(self):
        hecho = novedades.panel(DOMINIO, X, "bitacora.xml",
                                "https://www.linkedin.com/newsletters/la-glosa")
        assert self._destinos(hecho)[0] == (
            "https://www.linkedin.com/newsletters/la-glosa", "Boletín La glosa del mes")

    def test_sin_bitacora_no_ofrece_su_canal(self):
        hecho = novedades.panel(DOMINIO, X, None)
        assert [t for _, t in self._destinos(hecho)] == [
            "Glosa-e en X", "Canal Atom de las novedades"]
        assert "bitacora" not in hecho

    def test_cada_canal_copia_su_direccion_entera(self):
        # Lo que se pega en un lector es la dirección entera: una relativa
        # no le sirve de nada fuera de la página.
        hecho = novedades.panel(DOMINIO, X, "bitacora.xml")
        assert re.findall(r'data-copiar="([^"]+)"', hecho) == [
            f"{DOMINIO}/novedades.xml", f"{DOMINIO}/bitacora.xml"]
        # Sin guion no hay con qué copiar: el botón nace escondido y la
        # plantilla lo enseña.
        assert hecho.count(" hidden>Copiar la dirección</button>") == 2

    def test_la_plantilla_de_verdad_lleva_su_hueco_y_el_guion_de_copiar(self):
        plantilla = (WEB / novedades.NOMBRE).read_text(encoding="utf-8")
        assert plantilla.count(novedades.HUECO_DE_SEGUIR) == 1
        guion = plantilla[plantilla.rindex("<script>"):]
        assert 'querySelectorAll("button.copiar")' in guion
        assert "boton.hidden = false" in guion
        assert "navigator.clipboard.writeText(boton.dataset.copiar)" in guion
        # Si el navegador no deja copiar, la dirección se enseña: un botón que
        # no hace nada al tocarlo es peor que no tenerlo.
        assert "catch" in guion and "replaceWith" in guion


class TestCanal:
    def _leido(self, pequenas):
        return etree.fromstring(novedades.canal(pequenas, DOMINIO).encode("utf-8"))

    def test_es_atom_con_lo_que_pide_la_norma(self, pequenas):
        # RFC 4287, 4.1.1: el canal lleva id, title y updated, y autor si no
        # lo lleva cada entrada; cada entrada, id, title y updated.
        raiz = self._leido(pequenas)
        assert raiz.tag == "{http://www.w3.org/2005/Atom}feed"
        for falta in ("a:id", "a:title", "a:updated", "a:author/a:name"):
            assert raiz.find(falta, ATOM) is not None, falta
        assert raiz.find("a:link[@rel='self']", ATOM).get("href") == f"{DOMINIO}/novedades.xml"
        entradas = raiz.findall("a:entry", ATOM)
        assert len(entradas) == 2
        for e in entradas:
            for falta in ("a:id", "a:title", "a:updated", "a:summary"):
                assert e.find(falta, ATOM) is not None, falta
        # El canal se da por cambiado con la regla más nueva.
        assert raiz.findtext("a:updated", namespaces=ATOM) == "2026-10-20T00:00:00Z"

    def test_los_ids_no_dependen_de_nada_mas_que_del_id(self, pequenas, tmp_path):
        # El mismo id con otro título y otra fecha sigue siendo la misma
        # entrada para el lector, que es lo que se quiere al corregir una
        # errata.
        antes = self._leido(pequenas)
        otro = novedades.leer(_escrito(tmp_path, PEQUENO.replace(
            "titulo: Dos códigos", "titulo: Dos códigos, corregido")))
        despues = self._leido(otro)
        ids = [e.findtext("a:id", namespaces=ATOM) for e in antes.findall("a:entry", ATOM)]
        assert ids == [e.findtext("a:id", namespaces=ATOM)
                       for e in despues.findall("a:entry", ATOM)]
        assert ids == [f"{DOMINIO}/novedades#la-segunda", f"{DOMINIO}/novedades#la-primera"]
        assert len(set(ids)) == len(ids)

    def test_escapa_lo_que_lleva_el_texto(self, pequenas):
        raiz = self._leido(pequenas)
        titulos = [e.findtext("a:title", namespaces=ATOM) for e in raiz.findall("a:entry", ATOM)]
        assert "Uno <solo> & sin más" in titulos

    def test_sin_entradas_lleva_la_fecha_de_la_partida(self, tmp_path):
        # Atom pide una fecha siempre; la de hoy diría que cambió algo.
        solo = novedades.leer(_escrito(tmp_path, PEQUENO[PEQUENO.index("partida:"):]))
        raiz = self._leido(solo)
        assert raiz.findall("a:entry", ATOM) == []
        assert raiz.findtext("a:updated", namespaces=ATOM) == "2026-10-06T00:00:00Z"


class TestAtom:
    @pytest.mark.parametrize("enlace, sale", [
        ("./novedades.html#la-orden", f"{DOMINIO}/novedades#la-orden"),
        ("./bitacora-el-mes.html", f"{DOMINIO}/bitacora-el-mes"),
        ("./bitacora", f"{DOMINIO}/bitacora"),
    ])
    def test_la_direccion_es_la_limpia_de_produccion(self, enlace, sale):
        assert atom.direccion(DOMINIO, enlace) == sale

    def test_vercel_sirve_los_dos_canales_con_su_tipo(self):
        # Sin la cabecera, Vercel los sirve como application/xml, y hay
        # lectores que no los reconocen como canal (RFC 4287, apartado 7).
        vercel = json.loads((RAIZ / "vercel.json").read_text(encoding="utf-8"))
        tipos = {b["source"]: {h["key"]: h["value"] for h in b["headers"]}
                 for b in vercel["headers"]}
        for canal in ("/novedades.xml", "/bitacora.xml"):
            assert tipos[canal]["Content-Type"] == "application/atom+xml; charset=utf-8", canal
