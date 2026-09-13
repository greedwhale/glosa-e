# -*- coding: utf-8 -*-
"""La página del catálogo, montada de verdad.

Por qué existe
--------------
`pagina_incidencias.py` genera `incidencias.html`, que es el catálogo público
de los códigos: la página a la que llega alguien que acaba de ver
`REVOCACION-OCSP-NO-VALE` en un informe y no sabe qué hacer con él.

Hasta el 6 de septiembre de 2026 **ninguna prueba la ejecutaba**. Lo único que
la tocaba comprobaba que la plantilla siguiera llevando su marca; el generador
en sí —el 70 % de sus líneas— se ejecutaba por primera vez **durante la
construcción en Vercel**, con el sitio ya a medio publicar. Un `KeyError` ahí
no es un test rojo: es un despliegue roto, o peor, una página publicada con la
mitad de la tabla.

Lo que se comprueba aquí es lo que hace la página útil o inútil, en este
orden: que cada código tenga su ancla —sin ella el enlace del informe no lleva
a ninguna parte—, que las cifras de arriba sean las de la tabla de abajo, y
que lo que no se sabe se diga en vez de rellenarse.
"""
from __future__ import annotations

import pathlib
import re

import pytest

from validador import pagina_incidencias
from validador.codigos import Codigo, SinLeer, codigos_del_paquete, \
    sin_leer_del_paquete

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PLANTILLA = RAIZ / "web" / pagina_incidencias.NOMBRE


@pytest.fixture(scope="module")
def pagina(tmp_path_factory) -> str:
    """La página montada de verdad, con la plantilla y los códigos de hoy."""
    destino = tmp_path_factory.mktemp("sitio") / pagina_incidencias.NOMBRE
    cuantos = pagina_incidencias.montar_pagina(PLANTILLA, destino)
    assert cuantos == len(codigos_del_paquete()), (
        "montar_pagina dice haber metido otro número de códigos de los que hay")
    return destino.read_text(encoding="utf-8")


class TestLaPaginaQueSePublica:
    def test_todo_codigo_tiene_su_ancla(self, pagina):
        """Es para lo único que existe la página: `incidencias.html#EL-CODIGO`.

        Un código sin ancla no da error en ninguna parte. Deja a quien llega
        con el buscador en mitad de una tabla larga, buscando a ojo.
        """
        faltan = [c.codigo for c in codigos_del_paquete()
                  if f'id="{c.codigo}"' not in pagina]
        assert not faltan, (
            f"{len(faltan)} códigos salen en el catálogo sin ancla propia: "
            f"{', '.join(faltan[:8])}. El enlace del informe no llevaría a "
            "ellos.")

    def test_ninguna_ancla_se_repite(self, pagina):
        """Dos `id` iguales y el navegador se queda con el primero, en silencio."""
        anclas = re.findall(r'<article class="codigo-ficha" id="([^"]+)"', pagina)
        repetidas = sorted({a for a in anclas if anclas.count(a) > 1})
        assert not repetidas, f"anclas repetidas: {repetidas}"

    def test_la_cifra_de_arriba_es_la_de_la_tabla_de_abajo(self, pagina):
        """La cifra del titular la lee quien decide si fiarse."""
        dice = int(re.search(r"Los (\d+) códigos que puede sacar", pagina).group(1))
        hay = len(re.findall(r'<article class="codigo-ficha" id=', pagina))
        assert dice == hay == len(codigos_del_paquete())

    def test_no_anuncia_huecos_que_ya_no_tiene(self, pagina):
        """La página contaba los que no sabía leer, y ya no queda ninguno.

        Estuvo bien mientras fue verdad: seis patrones del IVA se componían al
        validar y la página los contaba a la vista en vez de fingir que el
        catálogo estaba entero. Hoy `iva.py` declara los cincuenta y cuatro
        códigos que compone y el catálogo los trae, así que esa frase se ha
        ido con ellos.

        Esta prueba guarda las dos mitades: que no se anuncien huecos
        inexistentes, y que el día que vuelva a haberlos la página lo diga.
        """
        sin_leer = sin_leer_del_paquete()
        if sin_leer:
            assert f"<dd>{len(sin_leer)}</dd>" in pagina
            assert "se componen al validar" in pagina
        else:
            assert "se componen al validar" not in pagina, (
                "la página dice que hay códigos que se componen al validar y "
                "el lector no encuentra ninguno sin leer")

    def test_los_compuestos_tienen_su_ficha(self, pagina):
        """Los que se componen al validar salen como los demás, con su página.

        Es lo que faltaba: decenas de códigos que podían salirle a
        alguien en su informe y no tenían dónde mirar. Se comprueban contra lo
        que `iva.py` declara, no contra una lista escrita aquí, que envejece.
        """
        from validador.iva import CODIGOS_COMPUESTOS

        esperados = sorted({c for v in CODIGOS_COMPUESTOS.values() for c in v})
        assert esperados, "iva.py ya no declara ninguno y antes eran 54"
        faltan = [c for c in esperados if f'id="{c}"' not in pagina]
        assert not faltan, (
            f"{len(faltan)} códigos compuestos sin ficha en la página: "
            + ", ".join(faltan[:8]))

    def test_no_queda_ningun_hueco_de_plantilla(self, pagina):
        assert pagina_incidencias.HUECO not in pagina

    def test_la_pagina_se_puede_leer_como_html(self, pagina):
        """Que lo generado no rompa la plantilla que lo envuelve.

        Se monta pegando cadenas, así que una comilla mal puesta no falla: sale
        una página que el navegador lee a medias y una tabla que se corta por
        donde nadie sabe.
        """
        from lxml import html as lhtml

        arbol = lhtml.fromstring(pagina)
        fichas = arbol.xpath("//article[contains(@class,'codigo-ficha')]")
        assert len(fichas) == len(codigos_del_paquete())


class TestLoQueSeDiceDeCadaCodigo:
    def test_cada_uno_dice_de_que_norma_sale(self, pagina):
        for codigo in codigos_del_paquete():
            etiqueta, _ = pagina_incidencias._norma(codigo.codigo)
            assert etiqueta, f"{codigo.codigo} sin norma"

    def test_el_revocado_no_es_un_problema_de_la_lista(self):
        """El fallo que ya se cazó una vez, escrito para que no vuelva.

        `REVOCADO` es el resultado de haber leído la lista bien, no un
        problema de formato. Sale de `REVOCA` sin guion, y clasificarlo por
        familia lo mandaba a «De la casa».
        """
        assert pagina_incidencias._norma("REVOCADO")[0] == "Firma electrónica"
        assert pagina_incidencias._norma("REVOCACION-OCSP-NO-VALE")[0] == \
            "Firma electrónica"

    def test_lo_que_no_tiene_explicacion_se_dice(self, tmp_path):
        """Un catálogo con huecos a la vista sirve; uno que parafrasea, no."""
        huerfano = Codigo(codigo="CHORRADA-SIN-GLOSA", gravedades=("error",),
                          modulo="inventado.py", linea=1)
        salida = pagina_incidencias._cuerpo([huerfano], [])
        assert "Sin explicación escrita todavía" in salida
        assert "<dt>Sin explicar</dt><dd>1</dd>" in salida

    def test_una_gravedad_variable_se_explica_en_vez_de_disimularse(self):
        doble = Codigo(codigo="BR-01", gravedades=("error", "aviso"),
                       modulo="en16931.py", linea=1)
        salida = pagina_incidencias._cuerpo([doble], [])
        assert "más de una gravedad" in salida

    def test_sin_codigos_sin_leer_no_se_inventa_la_fila(self):
        salida = pagina_incidencias._cuerpo(
            [Codigo("BR-01", ("error",), "en16931.py", 1)], [])
        assert "Compuestos al validar" not in salida
        assert "se componen al validar" not in salida

    def test_los_que_no_se_leen_se_cuentan_con_su_patron(self):
        salida = pagina_incidencias._cuerpo(
            [Codigo("BR-01", ("error",), "en16931.py", 1)],
            [SinLeer(modulo="iva.py", linea=42, patron="BR-{}-8")])
        assert "Compuestos al validar" in salida
        assert "<dd>1</dd>" in salida


class TestLoQueTieneQueFallar:
    def test_sin_la_marca_no_se_publica_una_pagina_vacia(self, tmp_path):
        """Provocado: es el fallo que no daría error por su cuenta.

        Sin la marca, `replace` no sustituye nada y sale una página perfecta,
        con su cabecera y su pie, y sin un solo código dentro.
        """
        plantilla = tmp_path / "sin-marca.html"
        plantilla.write_text("<html><body>nada</body></html>", encoding="utf-8")
        with pytest.raises(ValueError) as fallo:
            pagina_incidencias.montar_pagina(plantilla, tmp_path / "sale.html")
        assert pagina_incidencias.HUECO in str(fallo.value)
        assert not (tmp_path / "sale.html").exists(), (
            "ha escrito el fichero antes de fallar: quedaría publicada la "
            "página vacía y encima con el error dado")

    def test_lo_que_viene_de_fuera_va_escapado(self):
        """Los códigos salen del fuente, pero el glosario lo escribe alguien."""
        salida = pagina_incidencias._cuerpo(
            [Codigo('X"><script>', ("error",), "inventado.py", 1)], [])
        assert "<script>" not in salida
        assert "&lt;script&gt;" in salida


class TestLasDireccionesViejas:
    """Lo que se publicó con un nombre sigue llevando a su ficha.

    Del 11 al 13 de septiembre de 2026 las fichas del IVA salieron como
    `codigo-BR-S-8`, y la norma las llama `BR-S-08`. Se corrigió el nombre, y
    eso deja las direcciones viejas —ya en el sitemap que leyeron Google y
    Bing— apuntando a nada. Una redirección permanente las lleva a la buena.

    Se comprueba contra el catálogo y no contra una lista: cualquier código
    que la norma escriba con un cero delante tiene que tener su alias sin él,
    se haya publicado así o no —`BR-CL-01` nunca salió como `BR-CL-1`—,
    porque sin el cero es como lo teclea de memoria quien lo busca.
    """

    VERCEL = RAIZ / "vercel.json"

    def _redirecciones(self) -> dict[str, dict]:
        import json

        datos = json.loads(self.VERCEL.read_text(encoding="utf-8"))
        return {r["source"]: r for r in datos.get("redirects", [])}

    def test_cada_nombre_sin_el_cero_lleva_a_su_ficha(self):
        redirecciones = self._redirecciones()
        faltan = []
        for codigo in sorted(c.codigo for c in codigos_del_paquete()):
            corto = re.sub(r"^(BR-[A-Z]+-)0(\d)$", r"\1\2", codigo)
            if corto == codigo:
                continue
            viejo = "/" + pagina_incidencias.FICHA.format(corto).removesuffix(".html")
            nuevo = "/" + pagina_incidencias.FICHA.format(codigo).removesuffix(".html")
            r = redirecciones.get(viejo)
            if not r or r.get("destination") != nuevo or r.get("permanent") is not True:
                faltan.append(viejo)
        assert not faltan, (
            f"{len(faltan)} direcciones viejas sin redirección permanente: "
            + ", ".join(faltan[:6]))

    def test_ninguna_redireccion_tapa_una_ficha_ni_lleva_a_ninguna_parte(self):
        """Una redirección mal puesta es peor que un 404: se lleva la buena."""
        hay = {"/" + pagina_incidencias.FICHA.format(c.codigo).removesuffix(".html")
               for c in codigos_del_paquete()}
        for origen, r in self._redirecciones().items():
            if not origen.startswith("/codigo-"):
                continue
            assert origen not in hay, f"{origen} es una ficha y se redirige"
            assert r["destination"] in hay, (
                f"{origen} lleva a {r['destination']}, que no existe")
