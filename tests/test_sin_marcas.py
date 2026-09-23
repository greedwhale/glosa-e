# -*- coding: utf-8 -*-
"""Lo que se lee no lleva las marcas con que se escribió.

Por qué existe
--------------
Este repositorio se escribe con dos marcas —`**así**` para lo que pesa y
comillas invertidas para el nombre de una etiqueta— y dos sitios las
publicaban tal cual, sin que nada lo notara.

El informe de ejemplo de la portada decía «los 19 códigos de Facturae
\\*\\*existen los 19\\*\\*»: el mensaje de `COPIA-PAGO-MEDIO` llevaba los
asteriscos dentro, y el mismo texto sale en la consola, en el JSON y en la
página, así que ninguno de los tres podía pintarlos. Eran seis mensajes.

Y la página de códigos imprimía las explicaciones de `glosario.py` con un
`html.escape` y nada más. Medido el 23-09-2026 sobre el sitio montado: **15
páginas** con asteriscos o comillas invertidas a la vista —14 fichas y el
catálogo—, cinco de ellas también en la descripción que sale en el buscador.

Las dos mitades se arreglan distinto porque son cosas distintas. Un mensaje
del informe es texto llano que va a tres sitios, y ahí no caben marcas: lo que
se aparta se aparta con «», como en el resto de mensajes. Las explicaciones del
glosario solo van a HTML, y ahí las marcas dicen algo que se quiere decir, así
que se traducen a `<strong>` y a `<code>`; y en la descripción, que es texto
llano, se quitan.
"""
from __future__ import annotations

import ast
import datetime
import pathlib
from html.parser import HTMLParser

import pytest

from validador import pagina_incidencias

RAIZ = pathlib.Path(__file__).resolve().parent.parent
VALIDADOR = RAIZ / "validador"
EJEMPLOS = RAIZ / "ejemplos"
MARCAS = ("**", "`")


def _con_marca(texto: str) -> bool:
    return any(m in texto for m in MARCAS)


def _cadenas_de_incidencias() -> list[tuple[str, int, str]]:
    """Toda cadena escrita dentro de una llamada a `Incidencia(...)`."""
    halladas = []
    for fuente in sorted(VALIDADOR.glob("*.py")):
        arbol = ast.parse(fuente.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            nombre = getattr(nodo.func, "id", getattr(nodo.func, "attr", ""))
            if nombre != "Incidencia":
                continue
            for sub in ast.walk(nodo):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    halladas.append((fuente.name, sub.lineno, sub.value))
    return halladas


def test_se_leen_las_llamadas_de_verdad():
    """Que el recorrido de abajo encuentre algo que recorrer.

    Sin esto, un cambio de nombre de la clase dejaría la lista vacía y la
    prueba de abajo en verde para siempre.
    """
    cadenas = _cadenas_de_incidencias()
    assert len(cadenas) > 500, (
        f"solo se han encontrado {len(cadenas)} cadenas dentro de "
        "`Incidencia(...)`: el recorrido ya no reconoce las llamadas.")


def test_ningun_mensaje_del_informe_lleva_marcas():
    """El mismo texto sale en la consola, en el JSON y en la página."""
    malas = [f"{f}:{n}  {t[:60]!r}" for f, n, t in _cadenas_de_incidencias()
             if _con_marca(t)]
    assert not malas, (
        "estos mensajes llevan `**` o comillas invertidas, que salen tal cual "
        "en el informe. Lo que se aparta, con «»:\n  " + "\n  ".join(malas))


@pytest.mark.parametrize(
    "nombre", sorted(p.name for p in EJEMPLOS.iterdir() if p.is_file()))
def test_los_ejemplos_salen_sin_marcas(nombre):
    """Lo mismo, visto desde lo que sale: los diez ejemplos, campo a campo.

    La de arriba lee el fuente y no ve un mensaje que se componga fuera de la
    llamada; esta lo ve, pero solo en lo que sacan los ejemplos. Son la
    primera cosa que lee quien llega a la portada.
    """
    from validador import factura

    informe = factura.validar_archivo(str(EJEMPLOS / nombre),
                                      hoy=datetime.date(2026, 9, 20))
    malas = [
        f"{i.codigo}.{campo}"
        for i in informe.incidencias or []
        for campo in ("mensaje", "campo", "esperado", "encontrado")
        if _con_marca(str(getattr(i, campo) or ""))
    ]
    assert not malas, f"{nombre} saca marcas a la vista en: {', '.join(malas)}"


class _Visible(HTMLParser):
    """El texto que pinta el navegador y la descripción del buscador."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._dentro = 0
        self.texto: list[str] = []
        self.descripcion = ""

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._dentro += 1
        elif tag == "meta" and dict(attrs).get("name") == "description":
            self.descripcion = dict(attrs).get("content") or ""

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._dentro -= 1

    def handle_data(self, data):
        if not self._dentro:
            self.texto.append(data)


def _leer(ruta: pathlib.Path) -> _Visible:
    lector = _Visible()
    lector.feed(ruta.read_text(encoding="utf-8"))
    return lector


@pytest.fixture(scope="module")
def montado(tmp_path_factory) -> pathlib.Path:
    """El catálogo y las fichas de cada código, montados de verdad."""
    carpeta = tmp_path_factory.mktemp("sitio")
    plantilla = RAIZ / "web" / pagina_incidencias.NOMBRE
    pagina_incidencias.montar_pagina(plantilla, carpeta / pagina_incidencias.NOMBRE)
    pagina_incidencias.montar_fichas(plantilla, carpeta)
    return carpeta


def test_la_pagina_de_codigos_no_ensena_las_marcas(montado):
    paginas = sorted(montado.glob("*.html"))
    assert len(paginas) > 300, "no se han montado las fichas de cada código"
    malas = []
    for ruta in paginas:
        leido = _leer(ruta)
        if _con_marca("".join(leido.texto)):
            malas.append(ruta.name)
        if _con_marca(leido.descripcion):
            malas.append(ruta.name + " (en la descripción)")
    assert not malas, (
        f"{len(malas)} páginas enseñan `**` o comillas invertidas: "
        + ", ".join(malas[:10]))


def test_las_marcas_se_traducen_y_lo_de_dentro_sigue_escapado():
    """Se escapa primero y se traduce después, y no al revés.

    Al revés, una explicación que nombrara `<Invoice>` entre comillas
    invertidas metería una etiqueta de verdad en la página.
    """
    assert pagina_incidencias._con_marcas(
        "la **única** vez que sale `<Invoice>` & compañía"
    ) == ("la <strong>única</strong> vez que sale "
          "<code>&lt;Invoice&gt;</code> &amp; compañía")


def test_la_traduccion_llega_a_la_pagina(montado):
    """Que la ficha lleve la negrita y la mono, no solo que no lleve marcas.

    Quitar las marcas también dejaba la prueba de arriba en verde, y se
    perdía lo que quien las escribió quería decir.
    """
    ficha = (montado / pagina_incidencias.nombre_de("COPIA-PAGO-MEDIO")
             ).read_text(encoding="utf-8")
    assert "<strong>19 códigos de Facturae existen los 19</strong>" in ficha
    assert "<code>19</code>" in ficha


def test_la_descripcion_va_sin_marcas_y_sin_etiquetas():
    """El buscador enseña la descripción como texto: ni asteriscos ni `<code>`."""
    from validador.codigos import codigos_del_paquete

    uno = next(c for c in codigos_del_paquete() if c.codigo == "COPIA-NOMBRE")
    resumen = pagina_incidencias._resumen(uno)
    assert not _con_marca(resumen)
    assert "<" not in resumen
