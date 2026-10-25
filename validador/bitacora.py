# -*- coding: utf-8 -*-
"""La bitácora: lo que se va midiendo, publicado con la fecha y la fuente.

Por qué existe
--------------
Este proyecto produce sin parar una cosa que casi nadie publica: medidas sobre
facturas reales, contra normas que se mueven. Eso llevaba meses cayendo en
`HALLAZGOS.md`, que es un fichero de un repositorio y no lo lee un asesor
fiscal. La bitácora es el mismo material puesto donde sí se lee.

No es un blog de novedades del producto. La regla de qué entra es la misma que
la del resto de la casa: **si no está medido, no se publica**, y si está
medido se publica con la fecha en que se midió y con la fuente al lado.

Por qué se genera y no se escribe
---------------------------------
Porque el armazón —la cabecera, el menú, el pie, el aviso legal— es el mismo
en todas las páginas del sitio y ya hay una prueba que se niega a dejarlo
diverger. Si cada entrada fuera una página entera escrita a mano, publicar la
sexta sería copiar el menú por sexta vez, y el día que cambie una línea del
aviso legal habría que acordarse de siete sitios. Aquí se escribe **solo el
artículo** y el armazón lo pone `bitacora.html`, que es la plantilla.

El guardián, y por qué es de fecha y de fuente
----------------------------------------------
Una entrada sin fecha no es una medida: es una opinión con tipografía. Y una
entrada sin fuente le pide al lector que se fíe, que es exactamente lo que
este validador dice no hacer. Las dos cosas son fáciles de olvidar escribiendo
deprisa y **ninguna se nota al mirar la página publicada** —sale bien, se lee
bien, y no hay forma de saber de cuándo es ni de dónde salió—, que es el
disfraz de siempre.

Así que no se avisa: no se monta. `SinEntrada` para las dos.

Estática y sin Pyodide, a propósito
------------------------------------
Se llega desde un buscador a leer un texto. Bajar catorce megas de intérprete
para eso sería cobrar carísimo por nada, igual que en el catálogo de códigos.
"""
from __future__ import annotations

import datetime as _dt
import html
import re
from dataclasses import dataclass
from pathlib import Path

from validador import atom

__all__ = [
    "CANAL",
    "CARPETA",
    "Entrada",
    "HUECO",
    "NOMBRE",
    "PREFIJO",
    "SinEntrada",
    "canal",
    "leer_entradas",
    "montar_bitacora",
]

NOMBRE = "bitacora.html"
# El canal Atom de los artículos, desde el 25-10-2026. Hasta ese día iban en el
# de las novedades, mezclados con las reglas, y se contaban dos veces.
CANAL = "bitacora.xml"
# Donde viven los artículos, dentro de `web/`. Son trozos, no páginas: no
# llevan cabecera ni pie porque se los pone la plantilla.
CARPETA = "bitacora"
# La marca de la plantilla donde se pega el cuerpo. Si desaparece, montar no
# falla solo: publica una bitácora sin una sola entrada.
HUECO = "<!-- AQUI VA EL CUERPO -->"
# Cada entrada se monta **al lado** de la plantilla y no dentro de una carpeta.
# La razón es de rutas: la cabecera compartida enlaza `./glosa.css`, `./` y
# `./legal.html`, y el sello de la huella busca esa línea letra por letra. Una
# entrada un nivel más abajo obligaría a reescribir esas rutas a `../`, que es
# una transformación que **no da error cuando se hace mal**: la página sale, y
# sale sin estilo. Se prefiere una dirección más fea y ningún camino nuevo.
PREFIJO = "bitacora-"

_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SinEntrada(Exception):
    """Una entrada no dice de cuándo es, o no dice de dónde sale."""


@dataclass(frozen=True)
class Entrada:
    """Un artículo leído de `web/bitacora/`, ya comprobado."""

    ruta: Path
    slug: str
    titulo: str
    fecha: _dt.date
    entradilla: str
    fuentes: int
    cuerpo: str
    # La fecha del último cambio que la entrada **dice** que tuvo: la suya, o
    # la de su último «Corregida el…» o «Actualizada el…», si es más tarde.
    cambiada: _dt.date

    @property
    def nombre(self) -> str:
        """Cómo se llama esta entrada una vez montada."""
        return f"{PREFIJO}{self.slug}.html"

    @property
    def dicha(self) -> str:
        """La fecha como la lee una persona: «7 de septiembre de 2026»."""
        return "{} de {} de {}".format(
            self.fecha.day, _MESES[self.fecha.month - 1], self.fecha.year
        )


_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)


def _atributo(cuerpo: str, nombre: str) -> str:
    """El valor de `data-<nombre>` del `<article>` de cabeza, o cadena vacía.

    Se lee con expresión regular y no con lxml a propósito: esto corre al
    montar el sitio, donde lxml está, pero también lo llaman las pruebas sobre
    ficheros sueltos. Un trozo de HTML escrito aquí mismo no necesita un
    analizador entero para sacarle un atributo que está en la primera línea.
    """
    hallado = re.search(
        r'<article\b[^>]*\bdata-' + re.escape(nombre) + r'="([^"]*)"', cuerpo
    )
    return hallado.group(1).strip() if hallado else ""


def _fuentes_de(cuerpo: str) -> int:
    """Cuántos enlaces hay en el pie de fuentes. Cero es lo que se persigue."""
    pie = re.search(
        r'<footer class="fuentes">(.*?)</footer>', cuerpo, re.S
    )
    return len(re.findall(r"<a\b", pie.group(1))) if pie else 0


# Las marcas con que una entrada dice que se tocó después de publicarse. Es lo
# que va al `lastmod` del sitemap, y por qué no vale otra cosa está medido: el
# artículo de EDIFACT es del 7 de septiembre y se actualizó el 7 de octubre, y
# el de la copia fiel, del 21 de septiembre, se corrigió el 26 y se actualizó
# el 7 de octubre. Con `data-fecha` el sitemap le diría a Google que no han
# cambiado. La fecha del último commit tampoco vale: la historia se rehízo el
# 21-10-2026 y todas dicen ese día.
#
# Un retoque que no merece la marca —una errata, unas comillas— no cuenta, y
# está bien que no cuente: no es contenido nuevo que un buscador deba volver a
# leer. Lo que se cuenta al lector como cambio es lo que se le cuenta a Google.
_CAMBIO = re.compile(
    r"<b>(?:Corregida|Actualizada) el (\d{1,2}) de ([a-z]+) de (\d{4})"
)


def _cambios(ruta: Path, cuerpo: str) -> list[_dt.date]:
    """Las fechas de las marcas de cambio. Se niega ante una que no se lee."""
    fechas = []
    for dia, mes, anyo in _CAMBIO.findall(cuerpo):
        if mes not in _MESES:
            raise SinEntrada(
                f"«{ruta.name}» dice que se cambió el «{dia} de {mes} de {anyo}», "
                "y ese mes no existe. Ignorarla dejaría en el sitemap una fecha "
                "anterior al cambio, que es decirle a un buscador que no lo hubo."
            )
        try:
            fechas.append(_dt.date(int(anyo), _MESES.index(mes) + 1, int(dia)))
        except ValueError as error:
            raise SinEntrada(
                f"«{ruta.name}» tiene una marca de cambio imposible: {error}"
            ) from error
    return fechas


def leer_entradas(carpeta: Path) -> list[Entrada]:
    """Lee y comprueba todas las entradas. La más nueva primero.

    Se niega en cuanto una no cumple, con el nombre del fichero delante: una
    bitácora a la que le falta la mitad de una entrada es peor que una a la
    que le falta la entrada entera, porque la primera no se ve.
    """
    entradas: list[Entrada] = []
    for ruta in sorted(carpeta.glob("*.html")):
        cuerpo = ruta.read_text(encoding="utf-8")
        slug = ruta.stem

        crudo = _atributo(cuerpo, "fecha")
        if not _FECHA.match(crudo):
            raise SinEntrada(
                f"«{ruta.name}» no dice de cuándo es. Hace falta "
                f'`<article data-fecha="AAAA-MM-DD">` y hay «{crudo or "nada"}». '
                "Una entrada sin fecha no es una medida: es una opinión con "
                "tipografía, y publicada no hay forma de notarlo."
            )
        try:
            fecha = _dt.date.fromisoformat(crudo)
        except ValueError as error:
            raise SinEntrada(f"«{ruta.name}» tiene una fecha imposible: {error}") from error

        titulo = _atributo(cuerpo, "titulo")
        if not titulo:
            raise SinEntrada(
                f"«{ruta.name}» no tiene `data-titulo`, así que en el índice "
                "saldría una fila sin nombre y en la pestaña del navegador, "
                "nada."
            )

        entradilla = _atributo(cuerpo, "entradilla")
        if not entradilla:
            raise SinEntrada(
                f"«{ruta.name}» no tiene `data-entradilla`. Es lo que se lee "
                "en el índice y lo que se lleva un buscador; sin ella la "
                "entrada existe y no la encuentra nadie."
            )

        cuantas = _fuentes_de(cuerpo)
        if not cuantas:
            raise SinEntrada(
                f"«{ruta.name}» no lleva `<footer class=\"fuentes\">` con al "
                "menos un enlace. Una entrada sin fuente le pide al lector "
                "que se fíe, que es justo lo que esta herramienta dice no "
                "hacer."
            )

        entradas.append(Entrada(
            ruta=ruta, slug=slug, titulo=titulo, fecha=fecha,
            entradilla=entradilla, fuentes=cuantas, cuerpo=cuerpo,
            cambiada=max([fecha, *_cambios(ruta, cuerpo)]),
        ))

    repetidos = sorted({e.slug for e in entradas
                        if sum(1 for o in entradas if o.slug == e.slug) > 1})
    if repetidos:
        raise SinEntrada(
            "Dos entradas se llaman igual y una pisaría a la otra al montar: "
            + ", ".join(repetidos)
        )

    return sorted(entradas, key=lambda e: (e.fecha, e.slug), reverse=True)


_PORTADA = """<div class="portada">
  <h1>Bitácora</h1>
  <p class="entrada-lema">Lo que se va midiendo sobre facturas y normas
  reales. Cada entrada lleva la fecha en que se midió y la fuente al lado, y
  las que se han corregido dicen qué se corrigió.</p>
</div>
"""


def _indice(entradas: list[Entrada]) -> str:
    """La lista del índice. Sin entradas dice que no hay, en vez de callar."""
    if not entradas:
        return _PORTADA + (
            '<p class="vacio">Todavía no hay ninguna entrada publicada.</p>'
        )
    filas = []
    for e in entradas:
        filas.append(
            '<li>\n'
            f'  <a href="./{e.nombre}">\n'
            f'    <time datetime="{e.fecha.isoformat()}">{html.escape(e.dicha)}</time>\n'
            f'    <b>{html.escape(e.titulo)}</b>\n'
            f'    <span>{html.escape(e.entradilla)}</span>\n'
            '  </a>\n'
            '</li>'
        )
    return _PORTADA + '<ul class="entradas">\n' + "\n".join(filas) + "\n</ul>"


def _pagina(plantilla: str, titulo: str, descripcion: str, cuerpo: str) -> str:
    """Mete un cuerpo en la plantilla y le pone su título y su descripción."""
    salida = plantilla.replace(HUECO, cuerpo)
    salida = re.sub(
        r"<title>.*?</title>",
        "<title>{} &middot; Glosa-e</title>".format(html.escape(titulo)),
        salida, count=1, flags=re.S,
    )
    return re.sub(
        r'<meta name="description" content="[^"]*">',
        '<meta name="description" content="{}">'.format(html.escape(descripcion)),
        salida, count=1,
    )


def montar_bitacora(plantilla: Path, carpeta: Path, destino: Path) -> list[Entrada]:
    """Escribe el índice y una página por entrada. Devuelve lo publicado.

    `destino` es la carpeta del sitio montado, no un fichero: de aquí salen
    `bitacora.html` y un `bitacora-<slug>.html` por cada artículo.
    """
    texto = plantilla.read_text(encoding="utf-8")
    if HUECO not in texto:
        raise SinEntrada(
            f"«{plantilla.name}» ya no lleva `{HUECO}`, así que la bitácora se "
            "publicaría sin una sola entrada y sin que nada fallara."
        )

    entradas = leer_entradas(carpeta) if carpeta.is_dir() else []

    (destino / NOMBRE).write_text(
        _pagina(
            texto,
            "Bitácora",
            "Lo que Glosa-e va midiendo sobre facturas y normas reales, "
            "con la fecha en que se midió y la fuente al lado.",
            _indice(entradas),
        ),
        encoding="utf-8",
    )

    for e in entradas:
        volver = (
            '<p class="volver"><a href="./bitacora.html">&larr; '
            "Todas las entradas</a></p>"
        )
        (destino / e.nombre).write_text(
            _pagina(texto, e.titulo, e.entradilla, volver + "\n" + e.cuerpo),
            encoding="utf-8",
        )

    return entradas


def canal(entradas: list[Entrada], dominio: str) -> str:
    """El canal Atom de la bitácora: un artículo por entrada, con su entradilla.

    El id de cada una es la dirección del artículo, la misma que tenía en el
    canal de las novedades, para que quien ya lo leyó allí no lo vea como
    nuevo si se cambia de canal. Se niega sin artículos: el canal tendría que
    inventarse una fecha.
    """
    if not entradas:
        raise SinEntrada("la bitácora no tiene artículos, y su canal no tendría "
                         "ni una entrada ni una fecha cierta")
    ordenadas = sorted(entradas, key=lambda e: (e.fecha, e.slug), reverse=True)
    return atom.canal(
        dominio=dominio, nombre=CANAL, pagina=NOMBRE.removesuffix(".html"),
        titulo="Bitácora de Glosa-e",
        subtitulo="Lo que Glosa-e va midiendo sobre facturas y normas reales, "
                  "con la fecha en que se midió y la fuente al lado.",
        entradas=[atom.Entrada(
            titulo=e.titulo, enlace=atom.direccion(dominio, f"./{e.nombre}"),
            publicada=e.fecha, cambiada=e.cambiada, resumen=e.entradilla)
            for e in ordenadas],
        sin_entradas=ordenadas[0].fecha)
