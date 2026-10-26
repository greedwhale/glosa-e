# -*- coding: utf-8 -*-
"""La página que explica cada código de incidencia, generada del código fuente.

Por qué existe
--------------
Cuando a alguien le sale `REVOCACION-OCSP-NO-VALE` en un informe, lo que hace
es buscar ese código. Si no encuentra nada, se queda con una frase de veinte
palabras y ninguna forma de saber si eso es grave, de dónde sale la exigencia
ni a quién hay que reclamarle. Esta página contesta eso, y es enlazable código
a código: `incidencias.html#REVOCACION-OCSP-NO-VALE`.

Por qué se genera y no se escribe
---------------------------------
Porque un catálogo escrito a mano se queda atrás, y entonces manda a buscar a
un sitio donde no está, que es peor que no tenerlo. Los códigos salen de
`codigos.py`, que los lee con `ast` de los propios módulos y de las tablas de
reglas que los alimentan. Se añade uno nuevo en `firma.py` y aparece aquí sin
que nadie se acuerde de nada.

Los que se componen al validar —los `BR-{X}-8` del IVA, que llevan dentro la
categoría de la operación— no se pueden leer del fuente y **no están en la
lista**. Salen contados en la ficha de arriba, porque un catálogo al que le
faltan seis y lo dice sigue sirviendo, y uno al que le faltan y no lo dice no.

Lo que sí está escrito a mano son las explicaciones, en `glosario.py`, porque
el mensaje del informe se compone en tiempo de ejecución y no hay frase fija
que extraer. Los códigos sin explicación propia salen con la de su familia, y
los que no tienen ninguna salen **dichos como huecos** y contados arriba: un
catálogo que rellena con paráfrasis del propio código miente mejor que uno con
huecos a la vista.

Estática y sin Pyodide, a propósito
------------------------------------
Es una página de consulta: se llega a ella desde un buscador con un código
entre las manos. Hacerla depender de catorce megas de intérprete para leer una
tabla sería cobrar carísimo por nada.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from validador import normas
from validador.codigos import (
    Codigo,
    SinLeer,
    codigos_del_paquete,
    sin_leer_del_paquete,
)
from validador.glosario import explicar

__all__ = ["montar_pagina", "montar_fichas", "nombre_de", "NOMBRE"]

NOMBRE = "incidencias.html"
# La marca de la plantilla donde se pega el catálogo. Si desaparece, montar
# la página no falla solo: publica una página sin un solo código.
HUECO = "<!-- AQUI VA EL CATALOGO -->"
# Lo que solo tiene sentido en el catálogo —su titular, el buscador y el
# filtro— y que en la página de un código suelto sobra. Va marcado en la
# plantilla en vez de duplicar el armazón en un séptimo fichero: cabecera,
# menú y pie se escriben una vez, como en la bitácora.
SOLO_CATALOGO = re.compile(
    r"<!-- SOLO EL CATALOGO -->.*?<!-- /SOLO EL CATALOGO -->", re.S
)

# El nombre del fichero de cada código. Planos y al lado de los demás, como
# los de la bitácora: en una subcarpeta habría que reescribir todas las rutas
# relativas del armazón —`./glosa.css`, `./letra/…`— y eso no se rompe al
# montar, se rompe en el navegador de quien entra.
FICHA = "codigo-{}.html"
# Un código que no se pueda escribir en un nombre de fichero no se publica a
# medias: se dice. Hoy son 160 y todos encajan, pero el catálogo se lee del
# fuente y mañana puede salir cualquier cosa de una llamada nueva.
_SEGURO = re.compile(r"^[A-Z0-9-]{2,60}$")


def nombre_de(codigo: str) -> str:
    """El fichero que le toca a un código. `BR-CO-10` → `codigo-BR-CO-10.html`."""
    return FICHA.format(codigo)


# Las explicaciones de `glosario.py` se escriben como el resto del
# repositorio: `**así**` para lo que pesa y comillas invertidas para el nombre
# de una etiqueta o de un código. Aquí solo se escapaban, y la página las
# enseñaba tal cual —medido el 23-09-2026: 15 páginas publicadas, cinco de
# ellas también en la descripción del buscador—. En HTML dicen algo que se
# quiere decir, así que se traducen; en la descripción, que es texto llano, se
# quitan.
_NEGRITA = re.compile(r"\*\*(.+?)\*\*", re.S)
_MONO = re.compile(r"`([^`]+)`")


def _con_marcas(texto: str) -> str:
    """El texto escapado, con las dos marcas vueltas etiquetas.

    Se escapa primero y se traduce después: al revés, una explicación que
    nombrara `<Invoice>` entre comillas invertidas metería una etiqueta de
    verdad en la página.
    """
    salida = _MONO.sub(r"<code>\1</code>", html.escape(texto))
    return _NEGRITA.sub(r"<strong>\1</strong>", salida)


def _sin_marcas(texto: str) -> str:
    """El mismo texto sin marcas, para donde no hay HTML que las pinte."""
    return _NEGRITA.sub(r"\1", _MONO.sub(r"\1", texto))

# La tabla la comparte con el informe y vive en `normas.py`, que no importa
# nada: aquí tenerla aparte costó que la página dijera «Ley del IVA» de doce
# códigos que son criterio propio. Ver el porqué entero allí.
_norma = normas.norma


def _fila(uno: Codigo) -> str:
    texto, propia = explicar(uno.codigo, uno.familia)
    etiqueta, detalle = _norma(uno.codigo)
    gravedades = "".join(
        f'<span class="cuenta {g}">{g}</span>' for g in uno.gravedades
    ) or '<span class="cuenta">sin gravedad fija</span>'

    if not texto:
        cuerpo = (
            '<p class="sin-explicar">Sin explicación escrita todavía. Lo que '
            "se sabe de él está aquí: su gravedad, la norma a la que responde "
            "y el módulo que lo emite.</p>"
        )
    else:
        cuerpo = f"<p>{_con_marcas(texto)}</p>"
        if not propia:
            cuerpo += (
                '<p class="de-familia">Es la explicación de la familia '
                f'<b>{html.escape(uno.familia)}</b>: este código todavía no '
                "tiene una suya.</p>"
            )

    varias = (
        '<p class="de-familia">Sale con más de una gravedad según el caso, y '
        "eso no es un descuido: el mismo hecho vale distinto según con qué "
        "esté probado.</p>"
        if len(uno.gravedades) > 1 else ""
    )

    return (
        f'<article class="codigo-ficha" id="{html.escape(uno.codigo)}">'
        f'<div class="margen"><a class="codigo" href="./{html.escape(nombre_de(uno.codigo))}">'
        f"{html.escape(uno.codigo)}</a>{gravedades}</div>"
        f'<div class="cuerpo">{cuerpo}{varias}'
        f'<dl><dt>Norma</dt><dd>{html.escape(etiqueta)}: {html.escape(detalle)}</dd>'
        f"<dt>Se emite en</dt><dd>validador/{html.escape(uno.modulo)}"
        f":{uno.linea}</dd></dl></div></article>"
    )


def _cuerpo(codigos: list[Codigo], sin_leer: list[SinLeer]) -> str:
    familias: dict[str, list[Codigo]] = {}
    for uno in codigos:
        familias.setdefault(uno.familia, []).append(uno)

    sin_explicar = sum(1 for c in codigos if not explicar(c.codigo, c.familia)[0])
    propias = sum(1 for c in codigos if explicar(c.codigo, c.familia)[1])

    partes = [
        '<section id="resumen"><p class="rotulo">Catálogo</p>',
        '<h2 class="titulo">Los {} códigos que puede sacar este validador.</h2>'
        .format(len(codigos)),
        '<p class="texto" style="color:var(--tinta-2)">Salen del código fuente, '
        "no de una lista escrita a mano: se leen de las propias llamadas a "
        "<code>Incidencia(...)</code> al montar esta página, y de las tablas de "
        "reglas que las alimentan. Lo que puede faltar es la explicación, y "
        "cuando falta se dice."
        # Antes aquí ponía «así que aquí no puede faltar uno que exista», y era
        # mentira: el lector solo miraba el primer argumento de la llamada, y
        # los diecisiete códigos que salen de una tabla recorrida con un `for`
        # —BR-02 a BR-15, BR-22, BR-23 y BR-26— no aparecían. Ahora las tablas
        # se leen, y lo que sigue sin poder leerse se cuenta aquí al lado en
        # vez de prometerse que no existe.
        + (f" Otros {len(sin_leer)} se componen al validar, con la categoría "
           "de la operación, y no se pueden leer del fuente: no están en esta "
           "lista, y por eso se dicen." if sin_leer else "")
        + "</p>",
        # Las tres cifras y no solo la buena. «Sin explicar: 0» a secas es
        # verdad y engaña: deja creer que están explicados uno a uno cuando la
        # mayoría llevan la de su familia, que dice de dónde viene la
        # exigencia y no qué pasó exactamente. El hueco es ese, y se cuenta.
        '<dl class="ficha">'
        f"<div><dt>Códigos</dt><dd>{len(codigos)}</dd></div>"
        f"<div><dt>Familias</dt><dd>{len(familias)}</dd></div>"
        f"<div><dt>Explicados uno a uno</dt><dd>{propias}</dd></div>"
        f"<div><dt>Solo con la de su familia</dt>"
        f"<dd>{len(codigos) - propias - sin_explicar}</dd></div>"
        + (f"<div><dt>Sin explicar</dt><dd>{sin_explicar}</dd></div>"
           if sin_explicar else "")
        # A la vista y con las demás, no en una nota al pie: es el único sitio
        # donde este catálogo admite que no está entero, y esconderlo abajo
        # sería la versión educada de no decirlo.
        # Sin coletilla debajo del numero: `.pie` solo esta definida en
        # `sobre.html` y aqui saldria el texto pegado a la cifra. Lo que
        # significa ya lo dice el parrafo de arriba.
        + (f"<div><dt>Compuestos al validar</dt>"
           f"<dd>{len(sin_leer)}</dd></div>" if sin_leer else "")
        + "</dl></section>",
    ]

    for familia, suyos in familias.items():
        texto, _ = explicar("", familia)
        partes.append(
            f'<section id="familia-{html.escape(familia)}">'
            f'<p class="rotulo">{html.escape(familia)}</p>'
            f'<h2 class="titulo">{len(suyos)} '
            f"{'código' if len(suyos) == 1 else 'códigos'}</h2>"
            + (f'<p class="texto" style="color:var(--tinta-2)">'
               f"{_con_marcas(texto)}</p>" if texto else "")
            + '<div class="fichas">'
            + "".join(_fila(uno) for uno in suyos)
            + "</div></section>"
        )
    return "\n".join(partes)


def montar_pagina(plantilla: Path, destino: Path,
                  carpeta: Path | None = None) -> int:
    """Escribe la página y devuelve cuántos códigos ha metido.

    `plantilla` es `web/incidencias.html`, que trae la cabecera, el pie y el
    hueco donde va esto. Se separa así para que la página comparta cabecera y
    estilo con las demás sin copiarlos, que es como acaban derivando.
    """
    codigos = codigos_del_paquete(carpeta)
    sin_leer = sin_leer_del_paquete(carpeta)
    texto = plantilla.read_text(encoding="utf-8")
    if HUECO not in texto:
        raise ValueError(
            f"«{plantilla}» ya no lleva la marca {HUECO}, que es donde va el "
            "catálogo. Sin ella se publicaría la página con el hueco vacío y "
            "sin un solo código, que es de las cosas que no dan error."
        )
    destino.write_text(texto.replace(HUECO, _cuerpo(codigos, sin_leer)), encoding="utf-8")
    return len(codigos)

# --- Una página por código -------------------------------------------------
#
# Por qué, si el catálogo ya los trae todos. Porque un ancla no es una página:
# `incidencias.html#BR-CO-10` es la misma dirección que `incidencias.html` para
# cualquiera que no sea el navegador de quien ya está dentro. Quien tiene el
# problema delante no busca «validador de facturas»: busca el código que le
# acaba de escribir su programa, y hasta hoy no había nada que contestara a esa
# búsqueda.
#
# Se genera del mismo sitio que el catálogo y del mismo armazón, así que no hay
# una segunda verdad que mantener: si mañana aparece un código nuevo en
# `firma.py`, aparece su página sin que nadie se acuerde.


def _chips(gravedades) -> str:
    return "".join(
        f'<span class="cuenta {g}">{g}</span>' for g in gravedades
    ) or '<span class="cuenta">sin gravedad fija</span>'


def _resumen(uno: Codigo) -> str:
    """La descripción de la página, que es lo que sale en el buscador.

    **Empieza por el código, y no es un capricho.** De los 160, sólo 15 tienen
    explicación propia: los otros 145 llevan la de su familia. Con la
    explicación a secas, esas 145 páginas salían en el buscador con la misma
    frase —medido: 27 descripciones distintas para 160 páginas—, y quien
    viera cuatro resultados idénticos no sabría cuál abrir. Empezando por el
    código son 160 distintas, y encima la primera línea contesta ya lo que se
    ha venido a preguntar: qué gravedad tiene y de qué norma sale.

    Se corta por la última frase entera que quepa y no a media palabra: un
    resumen cortado por la mitad se lee como un fallo de la página.

    **El presupuesto se cuenta ya escapado.** El corte medía caracteres del
    texto y lo que acaba en el atributo `content` es el texto escapado, donde
    un `<` ocupa cuatro. Una explicación que nombre una etiqueta XML en su
    primera frase salía más larga de lo que se había presupuestado: medido el
    21-09-2026, 159 caracteres que en la página eran 168. Sólo le pasaba a una
    de las 381, y por eso no se había visto nunca; la que lo destapó fue la
    prueba, no la página.
    """
    texto = _sin_marcas(explicar(uno.codigo, uno.familia)[0])
    etiqueta, _detalle = _norma(uno.codigo)
    # «error o aviso o nota» no lo escribe nadie. Con coma hasta el último.
    gs = list(uno.gravedades)
    gravedad = (
        ", ".join(gs[:-1]) + " o " + gs[-1] if len(gs) > 1 else (gs or ["aviso"])[0]
    )
    # «De la casa» es el rótulo de la tabla, donde va solo y en su columna. En
    # una frase queda «aviso de De la casa», que es de las cosas que hacen
    # pensar que la página la escribió una máquina — y son las tres únicas que
    # no responden a ninguna norma, o sea justo las que más falta hace que se
    # lean bien.
    de_quien = (
        "propio de este validador" if etiqueta == "De la casa" else f"de {etiqueta}"
    )
    cabeza = f"{uno.codigo} en una factura electrónica: {gravedad} {de_quien}."
    if not texto:
        return f"{cabeza} Qué gravedad tiene y de dónde sale la exigencia."
    sitio = 158 - len(html.escape(cabeza))
    if len(html.escape(texto)) <= sitio:
        return f"{cabeza} {texto}"
    # Se recorta sobre el texto sin escapar —es donde están las frases— pero
    # se mide sobre el escapado, que es lo que ocupa de verdad.
    recorte = texto[:sitio]
    while len(html.escape(recorte)) > sitio:
        recorte = recorte[:-1]
    corte = max(recorte.rfind(". "), recorte.rfind(" "))
    return f"{cabeza} {recorte[: corte + 1].strip().rstrip(',;:')}…"


# Cuántos hermanos se enlazan, como mucho, desde una ficha.
#
# Hasta el 25-09-2026 se enlazaban todos los de la familia. En casi todas son
# pocos —la mayor después de la europea tiene 25—, pero la europea tiene 219, y
# cada una de sus fichas llevaba 218 enlaces. Medido en BR-47: de sus 532
# palabras visibles, 223 eran esa lista, un 42 %. Con 12 vecinos se quedan en
# 331, y la lista en 22. (La primera medida dio 304 y estaba mal: juntaba los
# enlaces seguidos sin espacio y la lista entera contaba casi como una
# palabra.) Así, 219 páginas eran en buena parte la misma lista, y ese día Search
# Console tenía 295 páginas «descubiertas» sin visitar y 13 «rastreadas» sin
# indexar, todas fichas BR-. **Que la causa sea la lista es una hipótesis**:
# Google no dice por qué no indexa una página. Se comprueba a las cuatro
# semanas, en `informes/2026-09-25-buscadores.md`.
#
# Por encima del tope se enlazan los vecinos de la misma serie —la de BR-CO-10
# es BR-CO, la de BR-47 es BR—, que son los que se buscan juntos, y la familia
# entera queda a un clic, en el catálogo.
_TOPE_DE_HERMANOS = 24
_VECINOS = 12
_RE_NUMERO_FINAL = re.compile(r"-\d+$")


def _serie(codigo: str) -> str:
    """`BR-CO-10` → `BR-CO`; `BR-47` → `BR`; un código sin número, él mismo."""
    return _RE_NUMERO_FINAL.sub("", codigo)


def _cercanos(uno: Codigo, todos: list[Codigo]) -> list[Codigo]:
    """Los `_VECINOS` más cercanos a `uno` en su serie, en el orden del catálogo."""
    familia = [c for c in todos if c.familia == uno.familia]
    serie = [c for c in familia if _serie(c.codigo) == _serie(uno.codigo)]
    if len(serie) < 2:
        serie = familia
    donde = next(i for i, c in enumerate(serie) if c.codigo == uno.codigo)
    inicio = max(0, min(donde - _VECINOS // 2, len(serie) - _VECINOS - 1))
    return [c for c in serie[inicio:inicio + _VECINOS + 1] if c.codigo != uno.codigo]


def _hermanos(uno: Codigo, todos: list[Codigo]) -> str:
    otros = [c for c in todos if c.familia == uno.familia and c.codigo != uno.codigo]
    if not otros:
        return ""
    familia = html.escape(uno.familia)
    if len(otros) <= _TOPE_DE_HERMANOS:
        titulo = f"Los otros {len(otros)} de {familia}"
        elegidos, al_catalogo = otros, ""
    else:
        titulo = f"Cerca de {html.escape(uno.codigo)}"
        elegidos = _cercanos(uno, todos)
        al_catalogo = (
            f'<p class="todos"><a href="./{NOMBRE}#familia-{familia}">Los '
            f"{len(otros) + 1} de {familia}, en el catálogo</a></p>"
        )
    enlaces = "".join(
        f'<li><a href="./{nombre_de(o.codigo)}">{html.escape(o.codigo)}</a></li>'
        for o in elegidos
    )
    return (
        f'<section class="hermanos"><h2>{titulo}</h2><ul>{enlaces}</ul>'
        f"{al_catalogo}</section>"
    )


def _ficha(uno: Codigo, todos: list[Codigo]) -> str:
    texto, propia = explicar(uno.codigo, uno.familia)
    etiqueta, detalle = _norma(uno.codigo)

    if texto:
        dice = f'<p class="dice">{_con_marcas(texto)}</p>'
    else:
        dice = (
            '<p class="dice">Todavía no tiene una explicación escrita. Lo que '
            "se sabe de él está aquí abajo: con qué gravedad sale, de qué "
            "norma viene la exigencia y qué parte del validador lo emite.</p>"
        )
    matices = []
    if texto and not propia:
        matices.append(
            "Esta es la explicación de la familia "
            f"<b>{html.escape(uno.familia)}</b>: dice de dónde viene la "
            "exigencia, no qué ha pasado exactamente en tu factura. Este "
            "código todavía no tiene una suya."
        )
    if len(uno.gravedades) > 1:
        matices.append(
            "Sale con más de una gravedad según el caso, y eso no es un "
            "descuido: el mismo hecho vale distinto según con qué esté "
            "probado."
        )
    matiz = "".join(f'<p class="matiz">{m}</p>' for m in matices)

    return (
        '<article class="ficha-codigo">'
        f'<p class="migas"><a href="./{NOMBRE}">Todos los códigos</a> '
        f"&middot; familia {html.escape(uno.familia)}</p>"
        f"<h1>{html.escape(uno.codigo)}</h1>"
        f'<p class="gravedades">{_chips(uno.gravedades)}</p>'
        f"{dice}{matiz}"
        '<dl class="procedencia">'
        f"<div><dt>De dónde viene</dt><dd>{html.escape(etiqueta)}: "
        f"{html.escape(detalle)}</dd></div>"
        f"<div><dt>Lo escribe</dt><dd><code>validador/{html.escape(uno.modulo)}"
        f":{uno.linea}</code></dd></div>"
        f"<div><dt>Puede salir como</dt><dd>{', '.join(uno.gravedades) or 'según el caso'}"
        "</dd></div></dl>"
        '<div class="probar"><b>Míralo en tu propia factura</b>'
        "<p>Suéltala en la herramienta y te dice si este código sale y por "
        "qué. Se lee en tu navegador: el fichero no se sube a ningún sitio. "
        '<a href="./">Ir a la herramienta</a>.</p></div>'
        f"{_hermanos(uno, todos)}"
        "</article>"
    )


def _enmarcar(plantilla: str, titulo: str, descripcion: str, cuerpo: str) -> str:
    """Mete un cuerpo en el armazón y le pone su título y su descripción.

    Hace la misma cirugía que `bitacora._pagina` sobre otra plantilla. No se
    comparten porque comparten la operación y no la decisión: allí el título
    es el del artículo y aquí se compone con el código, y una función que
    sirva para las dos acabaría con un parámetro que diga cuál de las dos es.
    """
    salida = SOLO_CATALOGO.sub("", plantilla).replace(HUECO, cuerpo)
    salida = re.sub(
        r"<title>.*?</title>",
        f"<title>{html.escape(titulo)} &middot; Glosa-e</title>",
        salida, count=1, flags=re.S,
    )
    return re.sub(
        r'<meta name="description" content="[^"]*">',
        f'<meta name="description" content="{html.escape(descripcion)}">',
        salida, count=1,
    )


def montar_fichas(plantilla: Path, destino: Path,
                  carpeta: Path | None = None) -> list[str]:
    """Escribe una página por código. Devuelve los ficheros escritos.

    `destino` es la carpeta del sitio montado, no un fichero.
    """
    texto = plantilla.read_text(encoding="utf-8")
    if HUECO not in texto:
        raise ValueError(
            f"«{plantilla}» ya no lleva la marca {HUECO}, que es donde va cada "
            "código. Sin ella se publicarían 160 páginas vacías, que es de las "
            "cosas que no dan error."
        )
    if not SOLO_CATALOGO.search(texto):
        raise ValueError(
            f"«{plantilla}» ya no marca con `<!-- SOLO EL CATALOGO -->` lo que "
            "es solo del catálogo. Sin esa marca, cada página de un código "
            "saldría con el titular «Qué significa cada aviso» y un buscador "
            "que no filtra nada."
        )

    codigos = codigos_del_paquete(carpeta)
    malos = [c.codigo for c in codigos if not _SEGURO.match(c.codigo)]
    if malos:
        raise ValueError(
            "estos códigos no se pueden escribir en un nombre de fichero, así "
            f"que no tendrían página propia: {', '.join(malos)}. Antes de "
            "publicarlos hay que decidir cómo se llaman."
        )

    escritos = []
    for uno in codigos:
        nombre = nombre_de(uno.codigo)
        (destino / nombre).write_text(
            _enmarcar(
                texto,
                f"{uno.codigo} · qué significa y de dónde sale",
                _resumen(uno),
                _ficha(uno, codigos),
            ),
            encoding="utf-8",
        )
        escritos.append(nombre)
    return escritos
