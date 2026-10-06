# -*- coding: utf-8 -*-
"""Una sola voz: la del informe.

Hasta el 15-09-2026 la web hablaba en tres personas a la vez: «te decimos»,
«miramos», «lo que no nos gusta» y «Escríbenos» al lado de «Escríbeme» y
«dímelo». Y el informe decía «un método que no sabemos reproducir» en una línea
y «solo se sabe verificar RSA» en la siguiente. Una herramienta cuyo valor es
que se le pueda creer no puede sonar a tres autores distintos.

Se eligió la voz del informe, la impersonal —«se ha comprobado»—, y la primera
persona del singular **solo para el contacto**, porque quien contesta un correo
es una persona. Está escrito en MARCA.md, en el tono.

Lo que se vigila es la primera persona del plural y el vosotros, que es lo que
se cuela al escribir deprisa: en las páginas publicadas sin sus comentarios, en
el JavaScript que pinta textos, y en las cadenas del informe y del banco sin
sus docstrings. La red es de forma —-amos, -emos, -imos, -áis, -éis, nos,
nuestro— y por eso lleva lista de excepciones: una palabra que acaba igual y no
es un verbo se añade ahí, con su motivo, en vez de aflojar la red.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"

PAGINAS = sorted([WEB / p for p in ("index.html", "banco.html", "legal.html",
                                     "incidencias.html", "tesis.html", "bitacora.html")]
                 + list((WEB / "bitacora").glob("*.html")))

# La primera del plural y el vosotros, por su forma.
PLURAL = re.compile(
    r"\b(?:[a-záéíóúüñ]+(?:amos|emos|imos|áis|éis)|somos|sois|pedís|"
    r"nosotr[oa]s|vosotr[oa]s|nuestr[oa]s?|vuestr[oa]s?|nos)\b",
    re.IGNORECASE)
# Sin «os» suelto: el JavaScript lleva código Python en cadenas —`import os`— y
# la red gritaría por eso. El vosotros se caza por los verbos.

# Palabras que caen en la red sin ser de nadie. Cada una con su motivo.
NO_SON_VERBOS = {
    "tramos": "sustantivo: los tramos de una numeración que faltan",
}


def _sin_comentarios(texto: str) -> str:
    texto = re.sub(r"<!--.*?-->", " ", texto, flags=re.S)
    texto = re.sub(r"/\*.*?\*/", " ", texto, flags=re.S)
    return re.sub(r"(?:^|\s)//[^\n]*", " ", texto)


def _cadenas_sin_docstrings(fuente: Path) -> list[str]:
    arbol = ast.parse(fuente.read_text(encoding="utf-8"))
    docstrings = set()
    for nodo in ast.walk(arbol):
        cuerpo = getattr(nodo, "body", None)
        if (isinstance(nodo, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                and cuerpo and isinstance(cuerpo[0], ast.Expr)
                and isinstance(cuerpo[0].value, ast.Constant)
                and isinstance(cuerpo[0].value.value, str)):
            docstrings.add(id(cuerpo[0].value))
    return [n.value for n in ast.walk(arbol)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstrings]


def en_plural(texto: str) -> list[str]:
    return sorted({p for p in PLURAL.findall(texto) if p.lower() not in NO_SON_VERBOS})


def test_la_red_caza_lo_que_ya_se_colo():
    """Si la red no cazara esto, todo lo de abajo saldría verde sin mirar."""
    for frase in ("Suelta un fichero y te decimos qué pone",
                  "incluido lo que no nos gusta",
                  "Aplicamos las reglas y las comparamos",
                  "un método que no sabemos reproducir",
                  "¿Cuánto cuesta y qué datos pedís?",
                  "Volveremos a esto, porque nosotros la confundimos",
                  "los textos son nuestros"):
        assert en_plural(frase), frase
    assert not en_plural("Se ha comprobado. Escríbeme y dímelo, y lo corrijo.")


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.name)
def test_las_paginas_hablan_con_una_voz(pagina):
    encontradas = en_plural(_sin_comentarios(pagina.read_text(encoding="utf-8")))
    assert not encontradas, (
        f"«{pagina.name}» habla en plural: {', '.join(encontradas)}. La voz del "
        "sitio es la del informe —«se ha comprobado»—, y la primera persona "
        "del singular solo para el contacto. Si es una palabra que no es un "
        "verbo, va a NO_SON_VERBOS con su motivo.")


def test_el_javascript_que_pinta_textos_tambien():
    encontradas = en_plural(_sin_comentarios((WEB / "glosa.js").read_text(encoding="utf-8")))
    assert not encontradas, f"glosa.js habla en plural: {', '.join(encontradas)}"


@pytest.mark.parametrize(
    "fuente", sorted((RAIZ / "validador").glob("*.py")) + [WEB / "prueba.py"],
    ids=lambda p: p.name)
def test_el_informe_y_el_banco_tambien(fuente):
    encontradas = sorted({p for cadena in _cadenas_sin_docstrings(fuente)
                          for p in en_plural(cadena)})
    assert not encontradas, (
        f"«{fuente.name}» tiene mensajes en plural: {', '.join(encontradas)}. "
        "El informe dice «aquí no se sabe», no «no sabemos».")


# --- Las tildes --------------------------------------------------------------
#
# Hasta el 06-10-2026 el banco tenía unas sesenta cadenas sin tildes («esta
# pagina no le pide nada a nadie», 13 de las 42 comprobaciones en el nombre),
# y si la página no arrancaba decía «No esta el interprete en ./pyodide/.
# Traelo con `python -m validador --traer-pyodide`».
#
# La red es de palabras que en castellano **no existen** sin su tilde. Las que
# existen con y sin ella se quedan fuera, porque cambian de sentido y no de
# ortografía: «esta», «valida», «publica», «solo», «aun», «mas», «que»,
# «quien», «donde», «cuando». Esas se corrigen leyendo. Tampoco van
# «interprete», «numero», «titulo» ni «invalido», que son formas de verbos.
# «pagina» y «linea» sí, aunque también lo sean: paginar y linear no salen en
# este sitio, y las dos se colaban.
SIN_TILDE = re.compile(
    r"(?<![\w-])(?:[a-zñ]+(?:ci|si)on|aqui|alli|asi|tambien|despues|ademas|"
    r"todavia|ningun|algun|segun|pagina|paginas|deberia|deberian|podria|"
    r"podrian|habria|habrian|comprobaria|habia|habian|venia|leido|leida|"
    r"traido|linea|lineas|raiz|patron|vacio|vacia|catalogo|politica|eliptica|"
    r"modulo|modulos|expandio|minimo|maximo|codigo|codigos|electronica|"
    r"electronico|tecnico|tecnica|unico|unica|rapido|automatico|metodo|indice|"
    r"traelo|dias|estan|esta (?:el|la|los|las|un|una|rota|roto|vacia|vacio))"
    r"(?![\w-])",
    re.IGNORECASE)

# Lo que no es castellano de nadie, sino lo que está escrito en otro sitio y
# se copia tal cual. Cada una con su motivo.
TAL_CUAL = {
    "Suministros Ibericos SL": "el nombre del vendedor en el EDIFACT de ejemplo: "
                               "el banco lo compara con lo que lee del fichero",
}

_MARCAS = re.compile(r"<[^>]*>|[\w-]+=(['\"])[^'\"]*\1")
_CODIGO = re.compile(r"`[^`]*`")


def sin_tilde(texto: str) -> list[str]:
    """Las palabras de la red, fuera de marcas, atributos y `código`.

    Con una mayúscula por dentro no es una palabra sino un nombre del XML
    (`SchemaVersion`, `UBLExtension`) o un código («ASI», en una lista de
    códigos), y se deja.
    """
    if texto in TAL_CUAL:
        return []
    limpio = _CODIGO.sub(" ", _MARCAS.sub(" ", texto))
    return sorted({p for p in SIN_TILDE.findall(limpio)
                   if not any(c.isupper() for c in p[1:])})


def _cadenas_js(codigo: str) -> list[str]:
    """Las cadenas de un JavaScript, saltando comentarios y expresiones regulares.

    Con una expresión regular no vale. `glosa.js` lleva `/href="([^"]+\\.whl)"/g`,
    con comillas dentro, y desde ahí cada cadena salía con el principio de la
    siguiente: la guardia dio por buena una «pagina» sin tilde. Se vio al
    provocarla, el 06-10-2026. Una «/» abre una expresión regular cuando lo de
    antes no puede acabar una división: un paréntesis, una coma, un igual.
    """
    cadenas, i, n, anterior = [], 0, len(codigo), ""
    while i < n:
        c = codigo[i]
        if codigo.startswith("//", i):
            i = codigo.find("\n", i)
            i = n if i < 0 else i
        elif codigo.startswith("/*", i):
            i = codigo.find("*/", i + 2)
            i = n if i < 0 else i + 2
        elif c in "\"'`":
            j, trozo = i + 1, []
            while j < n and codigo[j] != c:
                trozo.append(codigo[j:j + 2] if codigo[j] == "\\" else codigo[j])
                j += 2 if codigo[j] == "\\" else 1
            cadenas.append("".join(trozo))
            i, anterior = j + 1, c
        elif c == "/" and (not anterior or anterior in "(,=:[!&|?{};+-*%<>~^"):
            j, en_clase = i + 1, False
            while j < n and codigo[j] != "\n" and (en_clase or codigo[j] != "/"):
                if codigo[j] == "\\":
                    j += 1
                elif codigo[j] in "[]":
                    en_clase = codigo[j] == "["
                j += 1
            i = j + 1
            while i < n and codigo[i].isalpha():
                i += 1
            anterior = "/"
        else:
            if not c.isspace():
                anterior = c
            i += 1
    return cadenas


def _literales_js(codigo: str) -> list[str]:
    """Las cadenas con algún espacio: sin él son nombres («codigo»), no texto."""
    return [c for c in _cadenas_js(codigo) if " " in c]


def _lo_que_se_lee_de_la_pagina(pagina: Path) -> list[str]:
    """El texto de la página y las cadenas de sus scripts, sin estilos."""
    texto = re.sub(r"<!--.*?-->", " ", pagina.read_text(encoding="utf-8"), flags=re.S)
    texto = re.sub(r"<style.*?</style>", " ", texto, flags=re.S)
    cadenas = [c for guion in re.findall(r"<script[^>]*>(.*?)</script>", texto, flags=re.S)
               for c in _literales_js(guion)]
    return cadenas + [re.sub(r"<script.*?</script>", " ", texto, flags=re.S)]


def _lo_que_se_lee_de_glosa_js() -> list[str]:
    """Las cadenas de `glosa.js`, y del Python que lleva dentro, las suyas.

    El informe va en una plantilla con código Python, con sus comentarios: de
    ahí solo cuentan las cadenas, igual que en `validador/`.
    """
    codigo = (WEB / "glosa.js").read_text(encoding="utf-8")
    informe = re.search(r"const INFORME = `(.*?)`;", codigo, flags=re.S)
    assert informe, "glosa.js ya no lleva el informe en `const INFORME`"
    fuera = codigo[:informe.start()] + codigo[informe.end():]
    arbol = ast.parse(informe.group(1))
    dentro = [n.value for n in ast.walk(arbol)
              if isinstance(n, ast.Constant) and isinstance(n.value, str) and " " in n.value]
    return _literales_js(fuera) + dentro


def test_la_red_de_tildes_caza_lo_que_ya_se_colo():
    for frase in ("No esta el interprete en ./pyodide/. Traelo con",
                  "esta pagina no le pide nada a nadie",
                  "la cadena de confianza se encadena aqui tambien",
                  "una lista de revocacion se lee y se comprueba aqui",
                  "no hay paquete: no hay ningun esquema que compilar",
                  "catalogo vacio detectado, sin reventar",
                  "esta factura esta rota y deberia saltar",
                  "lo que se lee en el codigo unico"):
        assert sin_tilde(frase), frase
    for frase in ("esta página no le pide nada a nadie, y se valida aquí",
                  "La primera viene en uno y esta en otro",
                  "El documento declara SchemaVersion 3.2.2",
                  "el grupo dice `aeat:Extension`",
                  '<a class="codigo" href="./codigo-BR-01.html">',
                  "Suministros Ibericos SL"):
        assert not sin_tilde(frase), frase


@pytest.mark.parametrize("pagina", PAGINAS, ids=lambda p: p.name)
def test_las_paginas_llevan_sus_tildes(pagina):
    encontradas = sorted({p for t in _lo_que_se_lee_de_la_pagina(pagina) for p in sin_tilde(t)})
    assert not encontradas, f"«{pagina.name}» lleva sin tilde: {', '.join(encontradas)}"


def test_glosa_js_lleva_sus_tildes():
    encontradas = sorted({p for t in _lo_que_se_lee_de_glosa_js() for p in sin_tilde(t)})
    assert not encontradas, f"glosa.js lleva sin tilde: {', '.join(encontradas)}"


@pytest.mark.parametrize(
    "fuente", sorted((RAIZ / "validador").glob("*.py")) + [WEB / "prueba.py"],
    ids=lambda p: p.name)
def test_el_informe_el_banco_y_la_consola_llevan_sus_tildes(fuente):
    encontradas = sorted({p for cadena in _cadenas_sin_docstrings(fuente)
                          if " " in cadena for p in sin_tilde(cadena)})
    assert not encontradas, (
        f"«{fuente.name}» tiene cadenas sin tilde: {', '.join(encontradas)}. "
        "Si es algo que se copia tal cual de otro sitio, va a TAL_CUAL con su "
        "motivo.")
