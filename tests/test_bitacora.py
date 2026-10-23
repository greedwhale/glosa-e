# -*- coding: utf-8 -*-
"""La bitácora, montada de verdad y rota a propósito.

Por qué existe
--------------
`bitacora.py` genera el índice y una página por artículo, y lo hace **durante
la construcción del sitio**. Sin pruebas, la primera vez que corre de verdad
es en Vercel, con el despliegue a medias: un fallo ahí no es un test rojo, es
una página publicada a la que le falta media entrada, o un sitio entero que no
sube. Es exactamente lo que le pasó al generador del catálogo de códigos y por
lo que aquel tiene ahora sus propias pruebas.

Lo que se comprueba, en este orden de importancia:

1. **Que el guardián se niegue.** Es lo único que evita publicar una entrada
   sin fecha o sin fuente, y las dos cosas son invisibles en la página ya
   montada: sale bien, se lee bien y nadie sabe de cuándo es. Cada negativa se
   provoca rompiendo una entrada de verdad.
2. **Que el armazón sea el mismo.** El motivo de generar en vez de escribir es
   que el menú y el aviso legal no se copien una vez por artículo. Si una
   entrada acabara con un menú distinto, el generador no estaría sirviendo
   para nada.
3. Que el índice liste todo lo que hay, que cada entrada tenga su título y su
   descripción, y que lo publicado se pueda analizar como HTML.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from validador import bitacora

RAIZ = pathlib.Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"
PLANTILLA = WEB / bitacora.NOMBRE
ARTICULOS = WEB / bitacora.CARPETA


# --- Lo que hay publicado hoy ------------------------------------------------

def test_la_plantilla_conserva_su_hueco():
    """Sin la marca, la bitácora se publica vacía y nada falla."""
    assert bitacora.HUECO in PLANTILLA.read_text(encoding="utf-8"), (
        f"«{bitacora.NOMBRE}» ya no lleva `{bitacora.HUECO}`. Sin esa marca el "
        "índice sale sin una sola entrada y el montaje no se queja.")


def test_hay_al_menos_una_entrada():
    assert ARTICULOS.is_dir() and list(ARTICULOS.glob("*.html")), (
        f"no hay ni un artículo en «web/{bitacora.CARPETA}/». Una bitácora "
        "vacía enlazada desde el menú de todas las páginas es una promesa sin "
        "cumplir.")


def test_todas_las_entradas_de_hoy_pasan_el_guardian():
    """Lo publicado cumple. Si no, el sitio no se monta y esto lo dice antes."""
    entradas = bitacora.leer_entradas(ARTICULOS)
    assert len(entradas) == len(list(ARTICULOS.glob("*.html")))
    for e in entradas:
        assert e.fuentes >= 1
        assert e.titulo and e.entradilla


def test_las_entradas_van_de_la_mas_nueva_a_la_mas_vieja(tmp_path):
    for nombre, fecha in (("vieja", "2026-01-02"), ("nueva", "2026-08-09"),
                          ("media", "2026-05-05")):
        (tmp_path / f"{nombre}.html").write_text(
            _entrada(fecha=fecha), encoding="utf-8")
    assert [e.slug for e in bitacora.leer_entradas(tmp_path)] == [
        "nueva", "media", "vieja"]


# --- El guardián, provocado --------------------------------------------------
#
# Cada una de estas rompe una entrada por un sitio distinto y comprueba que no
# se monta. Se escriben a un directorio temporal, no sobre `web/`: una prueba
# que rompe lo publicado para comprobar que romperlo falla deja el repositorio
# roto si se corta a la mitad.

def _entrada(fecha: str = "2026-09-07", titulo: str = "Un título",
             entradilla: str = "Una entradilla.",
             fuentes: str = '<footer class="fuentes"><ul><li>'
                            '<a href="https://www.boe.es/">BOE</a></li></ul></footer>') -> str:
    atributos = []
    if fecha is not None:
        atributos.append(f'data-fecha="{fecha}"')
    if titulo is not None:
        atributos.append(f'data-titulo="{titulo}"')
    if entradilla is not None:
        atributos.append(f'data-entradilla="{entradilla}"')
    return (f'<article class="entrada" {" ".join(atributos)}>\n'
            f"  <h1>{titulo}</h1>\n  <p>Cuerpo.</p>\n  {fuentes}\n</article>\n")


class TestLoQueNoSePublica:
    def test_sin_fecha(self, tmp_path):
        (tmp_path / "x.html").write_text(_entrada(fecha=None), encoding="utf-8")
        with pytest.raises(bitacora.SinEntrada, match="de cuándo es"):
            bitacora.leer_entradas(tmp_path)

    def test_con_una_fecha_que_no_es_una_fecha(self, tmp_path):
        (tmp_path / "x.html").write_text(
            _entrada(fecha="7 de septiembre"), encoding="utf-8")
        with pytest.raises(bitacora.SinEntrada, match="de cuándo es"):
            bitacora.leer_entradas(tmp_path)

    def test_con_una_fecha_imposible(self, tmp_path):
        """`2026-02-31` cumple la forma y no existe."""
        (tmp_path / "x.html").write_text(
            _entrada(fecha="2026-02-31"), encoding="utf-8")
        with pytest.raises(bitacora.SinEntrada, match="fecha imposible"):
            bitacora.leer_entradas(tmp_path)

    def test_sin_titulo(self, tmp_path):
        (tmp_path / "x.html").write_text(_entrada(titulo=None), encoding="utf-8")
        with pytest.raises(bitacora.SinEntrada, match="data-titulo"):
            bitacora.leer_entradas(tmp_path)

    def test_sin_entradilla(self, tmp_path):
        (tmp_path / "x.html").write_text(
            _entrada(entradilla=None), encoding="utf-8")
        with pytest.raises(bitacora.SinEntrada, match="data-entradilla"):
            bitacora.leer_entradas(tmp_path)

    def test_sin_pie_de_fuentes(self, tmp_path):
        (tmp_path / "x.html").write_text(_entrada(fuentes=""), encoding="utf-8")
        with pytest.raises(bitacora.SinEntrada, match="fuentes"):
            bitacora.leer_entradas(tmp_path)

    def test_con_un_pie_de_fuentes_sin_un_solo_enlace(self, tmp_path):
        """El pie está y no lleva nada. Es el caso que más fácil se cuela."""
        (tmp_path / "x.html").write_text(
            _entrada(fuentes='<footer class="fuentes"><h2>De dónde sale</h2>'
                             "</footer>"), encoding="utf-8")
        with pytest.raises(bitacora.SinEntrada, match="fuentes"):
            bitacora.leer_entradas(tmp_path)

    def test_sin_el_hueco_de_la_plantilla_no_escribe_nada(self, tmp_path):
        plantilla = tmp_path / bitacora.NOMBRE
        plantilla.write_text("<html><body>sin marca</body></html>",
                             encoding="utf-8")
        articulos = tmp_path / "articulos"
        articulos.mkdir()
        (articulos / "x.html").write_text(_entrada(), encoding="utf-8")
        destino = tmp_path / "salida"
        destino.mkdir()
        with pytest.raises(bitacora.SinEntrada, match="HUECO|AQUI VA EL CUERPO"):
            bitacora.montar_bitacora(plantilla, articulos, destino)
        assert not list(destino.iterdir()), (
            "se ha negado, pero ha dejado ficheros escritos a medias")


# --- Lo que se monta ---------------------------------------------------------

@pytest.fixture(scope="module")
def montado(tmp_path_factory) -> pathlib.Path:
    """El sitio de verdad: la plantilla y los artículos que hay publicados."""
    destino = tmp_path_factory.mktemp("bitacora")
    bitacora.montar_bitacora(PLANTILLA, ARTICULOS, destino)
    return destino


def test_se_escribe_el_indice_y_una_pagina_por_entrada(montado):
    entradas = bitacora.leer_entradas(ARTICULOS)
    esperados = {bitacora.NOMBRE} | {e.nombre for e in entradas}
    assert {p.name for p in montado.iterdir()} == esperados


def test_el_indice_enlaza_todas_las_entradas(montado):
    indice = (montado / bitacora.NOMBRE).read_text(encoding="utf-8")
    for e in bitacora.leer_entradas(ARTICULOS):
        assert f'href="./{e.nombre}"' in indice, (
            f"«{e.slug}» está publicada y el índice no lleva a ella: existe y "
            "no la encuentra nadie.")


def test_cada_entrada_lleva_su_titulo_y_su_descripcion(montado):
    for e in bitacora.leer_entradas(ARTICULOS):
        texto = (montado / e.nombre).read_text(encoding="utf-8")
        assert f"<title>{e.titulo} &middot; Glosa-e</title>" in texto
        assert f'<meta name="description" content="{e.entradilla}">' in texto
        assert texto.count("<title>") == 1


def test_el_menu_de_cada_entrada_es_el_del_resto_del_sitio(montado):
    """La razón de generar en vez de escribir. Si esto falla, no sirve de nada."""
    def menu(texto: str) -> str:
        return texto[texto.index("<!-- MENU"):
                     texto.index("<!-- FIN MENU -->") + len("<!-- FIN MENU -->")]

    referencia = menu((WEB / "index.html").read_text(encoding="utf-8"))
    for pagina in sorted(montado.iterdir()):
        assert menu(pagina.read_text(encoding="utf-8")) == referencia, (
            f"«{pagina.name}» lleva un menú distinto del de la portada")


def test_lo_publicado_es_html_que_se_puede_analizar(montado):
    from lxml import html as lhtml

    for pagina in sorted(montado.iterdir()):
        arbol = lhtml.fromstring(pagina.read_text(encoding="utf-8"))
        assert arbol.xpath("//header") and arbol.xpath("//footer")


def test_cada_entrada_publica_su_fecha_en_forma_de_maquina(montado):
    """`<time datetime>` para que un lector o un buscador la lea sin adivinar."""
    for e in bitacora.leer_entradas(ARTICULOS):
        texto = (montado / e.nombre).read_text(encoding="utf-8")
        assert f'datetime="{e.fecha.isoformat()}"' in texto


def test_ninguna_entrada_promete_certificar():
    """La tesis de la casa, aplicada a lo que se publica en su nombre.

    Es la palabra que este proyecto no puede usar sobre sí mismo: una glosa
    explica, no da fe. En un artículo suelto se cuela con facilidad, y en el
    sitio publicado nadie la va a ver hasta que la cite alguien.
    """
    prohibidas = re.compile(
        r"\b(certificamos|certifica que|garantizamos|damos fe)\b", re.I)
    for ruta in sorted(ARTICULOS.glob("*.html")):
        hallado = prohibidas.findall(ruta.read_text(encoding="utf-8"))
        assert not hallado, (
            f"«{ruta.name}» dice {hallado}. Glosa-e no certifica nada y no "
            "puede decir que lo haga ni de pasada.")


def test_ninguna_entrada_lleva_rayas():
    """La raya (—) hace que un texto suene escrito por una máquina.

    Lo decidió el titular el 28-09-2026, y es justo lo contrario de lo que
    quiere un artículo firmado por una persona. Los incisos van entre comas o
    entre paréntesis. Una entrada nueva se escribe cada lunes, así que es donde
    más fácil se cuela.
    """
    for ruta in sorted(ARTICULOS.glob("*.html")):
        texto = ruta.read_text(encoding="utf-8")
        assert "—" not in texto, (
            f"«{ruta.name}» lleva {texto.count('—')} raya(s). Los incisos, "
            "entre comas o entre paréntesis.")


def test_el_menu_del_sitio_lleva_a_la_bitacora():
    """Publicada y sin enlazar sería una carpeta bonita que no lee nadie."""
    portada = (WEB / "index.html").read_text(encoding="utf-8")
    assert f'href="./{bitacora.NOMBRE}"' in portada


# --- La fecha del último cambio, para el sitemap ------------------------------
#
# Va al `lastmod`, y por eso tiene que ser la que la entrada dice y no otra:
# con `data-fecha` a secas, el artículo de EDIFACT (del 7 de septiembre,
# actualizado el 7 de octubre) le diría a Google que no ha cambiado.


class TestLaFechaDelUltimoCambio:
    def test_sin_marcas_es_la_suya(self, tmp_path):
        (tmp_path / "x.html").write_text(_entrada(fecha="2026-09-07"), encoding="utf-8")
        (una,) = bitacora.leer_entradas(tmp_path)
        assert una.cambiada == una.fecha

    def test_con_marcas_es_la_ultima(self, tmp_path):
        cuerpo = _entrada(fecha="2026-09-07").replace(
            "<p>Cuerpo.</p>",
            "<p><b>Actualizada el 7 de octubre de 2026.</b> Algo.</p>"
            "<p><b>Corregida el 26 de septiembre de 2026, a mano.</b> Otro.</p>")
        (tmp_path / "x.html").write_text(cuerpo, encoding="utf-8")
        (una,) = bitacora.leer_entradas(tmp_path)
        assert una.cambiada.isoformat() == "2026-10-07"

    def test_con_una_marca_de_un_mes_que_no_existe(self, tmp_path):
        """Ignorarla dejaría en el sitemap una fecha anterior al cambio."""
        cuerpo = _entrada().replace(
            "<p>Cuerpo.</p>", "<p><b>Corregida el 7 de setiembre de 2026.</b></p>")
        (tmp_path / "x.html").write_text(cuerpo, encoding="utf-8")
        with pytest.raises(bitacora.SinEntrada, match="ese mes no existe"):
            bitacora.leer_entradas(tmp_path)

    def test_con_una_marca_imposible(self, tmp_path):
        cuerpo = _entrada().replace(
            "<p>Cuerpo.</p>", "<p><b>Actualizada el 31 de septiembre de 2026.</b></p>")
        (tmp_path / "x.html").write_text(cuerpo, encoding="utf-8")
        with pytest.raises(bitacora.SinEntrada, match="marca de cambio imposible"):
            bitacora.leer_entradas(tmp_path)

    def test_las_de_hoy_que_se_han_tocado_lo_dicen(self):
        """Las dos que se actualizaron el 7 de octubre, leídas de verdad."""
        por_nombre = {e.slug: e for e in bitacora.leer_entradas(ARTICULOS)}
        for slug in ("edifact-reglas-de-2018", "copia-fiel-nadie-traduce"):
            assert por_nombre[slug].cambiada.isoformat() == "2026-10-07", slug
            assert por_nombre[slug].cambiada > por_nombre[slug].fecha, slug
