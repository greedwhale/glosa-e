# -*- coding: utf-8 -*-
"""Una página por código, que es lo que un buscador puede indexar.

Por qué existe esto
-------------------
El catálogo ya traía los 160 códigos, cada uno con su ancla. Pero un ancla no
es una página: `incidencias.html#BR-CO-10` es, para cualquier buscador, la
misma dirección que `incidencias.html`. Quien tiene el problema delante no
busca «validador de facturas» —busca el código que le acaba de escribir su
programa— y hasta ahora no había nada que contestara a esa búsqueda.

Lo que se comprueba aquí es lo que puede salir mal al partirlo en 160:

1. **Que salgan las 160 y sean las del catálogo**, no una lista aparte.
2. **Que cada una sea distinta de las otras.** Es el fallo que casi se cuela:
   de los 160 códigos sólo 15 tienen explicación propia, así que con la
   explicación a secas 145 páginas salían con la misma descripción. Medido
   antes de arreglarlo: 27 descripciones distintas para 160 páginas.
3. **Que no se traigan lo que es del catálogo**, ni el titular ni el buscador.
4. **Que las negativas funcionen**, porque las tres fallan en silencio: una
   plantilla sin hueco publica 160 páginas vacías, una sin la marca publica
   160 titulares equivocados, y un código que no quepa en un nombre de
   fichero se publicaría a medias.
"""

import html
import pathlib
import re

import pytest

from validador import codigos, glosario, pagina_incidencias

from validador import pagina_incidencias
from validador.codigos import codigos_del_paquete

PLANTILLA = pathlib.Path("web/incidencias.html")

RE_TITULO = re.compile(r"<title>(.*?)</title>", re.S)
RE_DESCRIPCION = re.compile(r'<meta name="description" content="([^"]*)">')


@pytest.fixture(scope="module")
def montadas(tmp_path_factory):
    """Las 160 páginas, montadas una vez para todas las comprobaciones."""
    destino = tmp_path_factory.mktemp("codigos")
    escritas = pagina_incidencias.montar_fichas(PLANTILLA, destino)
    return destino, escritas


class TestLasQueSalen:

    def test_hay_una_por_cada_codigo_del_catalogo(self, montadas):
        _destino, escritas = montadas
        codigos = codigos_del_paquete()
        assert len(escritas) == len(codigos)
        assert set(escritas) == {
            pagina_incidencias.nombre_de(c.codigo) for c in codigos
        }

    def test_cada_codigo_es_el_titular_de_la_suya(self, montadas):
        destino, _ = montadas
        for uno in codigos_del_paquete()[:20]:
            texto = (destino / pagina_incidencias.nombre_de(uno.codigo)).read_text(
                encoding="utf-8"
            )
            assert f"<h1>{uno.codigo}</h1>" in texto

    def test_los_titulos_son_todos_distintos(self, montadas):
        destino, escritas = montadas
        titulos = [
            RE_TITULO.search((destino / n).read_text(encoding="utf-8")).group(1)
            for n in escritas
        ]
        assert len(set(titulos)) == len(titulos)

    def test_las_descripciones_son_todas_distintas(self, montadas):
        """El guardián del fallo que casi se publica.

        Ciento cuarenta y cinco de los 160 códigos no tienen explicación
        propia: llevan la de su familia. Poniendo esa explicación como
        descripción, 145 páginas salían en el buscador con la misma frase, y
        quien viera cuatro resultados idénticos no sabría cuál abrir. Medido
        entonces: 27 distintas de 160.
        """
        destino, escritas = montadas
        descripciones = [
            RE_DESCRIPCION.search(
                (destino / n).read_text(encoding="utf-8")
            ).group(1)
            for n in escritas
        ]
        assert len(set(descripciones)) == len(descripciones)

    def test_ninguna_pasa_de_lo_que_cabe_en_un_resultado(self, montadas):
        """Una descripción de 300 caracteres sale cortada con puntos suspensivos.

        No es un fallo, pero la frase que se corta es la que tenía que
        convencer a alguien de entrar.
        """
        destino, escritas = montadas
        for nombre in escritas:
            texto = (destino / nombre).read_text(encoding="utf-8")
            assert len(RE_DESCRIPCION.search(texto).group(1)) <= 165, nombre

    def test_y_se_mide_lo_que_ocupa_ya_escapado(self, monkeypatch):
        """El corte contaba caracteres del texto; la página guarda el escapado.

        Un `<` ocupa cuatro dentro del atributo `content`. La prueba de arriba
        mide la página montada, así que esto sólo lo caza cuando existe un
        código cuya explicación nombre una etiqueta XML en sus primeras
        líneas: el 21-09-2026 había **uno** de 381, y fue el que lo destapó.
        Ésta lo prueba sin depender de que ese código siga existiendo.
        """
        inventado = codigos.Codigo(
            codigo="XSD-INVENTADO",
            gravedades=("error",),
            modulo="esquema.py",
            linea=1,
        )
        monkeypatch.setitem(
            glosario.CODIGOS,
            inventado.codigo,
            "Un <cbc:ID> donde va un <cbc:UUID>, con el <cac:Party> al lado. "
            + "palabra " * 40,
        )
        salida = pagina_incidencias._resumen(inventado)
        assert len(html.escape(salida)) <= 165, (
            f"{len(html.escape(salida))} caracteres escapados: el "
            "presupuesto vuelve a contarse sobre el texto sin escapar"
        )

    def test_no_se_traen_el_titular_ni_el_buscador_del_catalogo(self, montadas):
        destino, escritas = montadas
        for nombre in escritas[:20]:
            texto = (destino / nombre).read_text(encoding="utf-8")
            assert 'id="filtro"' not in texto
            assert "filtrar();" not in texto
            # El titular del catálogo, no su enlace en el menú: ese sí va en
            # todas las páginas del sitio y tiene que seguir yendo.
            assert "<h1>Qué significa cada aviso</h1>" not in texto

    def test_cada_una_lleva_de_vuelta_al_catalogo_y_a_la_herramienta(self, montadas):
        destino, escritas = montadas
        for nombre in escritas[:20]:
            texto = (destino / nombre).read_text(encoding="utf-8")
            assert f'href="./{pagina_incidencias.NOMBRE}"' in texto
            assert 'href="./"' in texto

    def test_el_catalogo_enlaza_a_cada_una(self, tmp_path):
        """Si no, las 160 son huérfanas: no se llega a ellas desde ninguna parte.

        El sitemap ayuda, pero lo que de verdad las hace existir es que haya
        un enlace que lleve hasta ellas.
        """
        salida = tmp_path / "incidencias.html"
        pagina_incidencias.montar_pagina(PLANTILLA, salida)
        catalogo = salida.read_text(encoding="utf-8")
        for uno in codigos_del_paquete():
            assert f'href="./{pagina_incidencias.nombre_de(uno.codigo)}"' in catalogo

    def test_los_de_una_familia_se_enlazan_entre_si(self, montadas):
        destino, _ = montadas
        texto = (destino / "codigo-REVOCACION-SOLO-OCSP.html").read_text(
            encoding="utf-8"
        )
        assert 'href="./codigo-REVOCACION-SUSPENDIDO.html"' in texto
        # Y no se enlaza a sí mismo, que sería una fila muerta en la lista.
        assert texto.count('href="./codigo-REVOCACION-SOLO-OCSP.html"') == 0


class TestLasNegativas:
    """Las tres fallan calladas, que es por lo que hay que provocarlas."""

    def _plantilla(self, tmp_path, texto: str) -> pathlib.Path:
        copia = tmp_path / "incidencias.html"
        copia.write_text(texto, encoding="utf-8")
        return copia

    def test_sin_el_hueco_no_se_publican_160_paginas_vacias(self, tmp_path):
        original = PLANTILLA.read_text(encoding="utf-8")
        copia = self._plantilla(
            tmp_path, original.replace(pagina_incidencias.HUECO, "")
        )
        with pytest.raises(ValueError) as motivo:
            pagina_incidencias.montar_fichas(copia, tmp_path)
        assert "vacías" in str(motivo.value)

    def test_sin_la_marca_no_se_publican_160_titulares_equivocados(self, tmp_path):
        original = PLANTILLA.read_text(encoding="utf-8")
        copia = self._plantilla(
            tmp_path, original.replace("<!-- SOLO EL CATALOGO -->", "")
        )
        with pytest.raises(ValueError) as motivo:
            pagina_incidencias.montar_fichas(copia, tmp_path)
        assert "buscador" in str(motivo.value)

    def test_un_codigo_que_no_cabe_en_un_nombre_de_fichero_se_dice(
        self, tmp_path, monkeypatch
    ):
        """Hoy los 160 caben. El catálogo se lee del fuente y mañana no se sabe."""
        from validador.codigos import Codigo

        raro = Codigo("BR-{X}-8", ("error",), "iva.py", 1)
        monkeypatch.setattr(
            pagina_incidencias, "codigos_del_paquete", lambda *a, **k: [raro]
        )
        with pytest.raises(ValueError) as motivo:
            pagina_incidencias.montar_fichas(PLANTILLA, tmp_path)
        assert "BR-{X}-8" in str(motivo.value)


class TestQueSigaSiendoUnaConsulta:
    """No arrastra el intérprete, que son catorce megas para leer una tabla."""

    def test_no_carga_pyodide_ni_el_validador(self, montadas):
        destino, escritas = montadas
        texto = (destino / escritas[0]).read_text(encoding="utf-8")
        assert "pyodide" not in texto.lower()
        assert "glosa.js" not in texto
