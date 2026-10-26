# -*- coding: utf-8 -*-
"""«0 dominios de terceros», atado a lo que hay escrito en la página.

Por qué existe
--------------
Es la cifra de cabecera del producto. `legal.html` publica «Dominios de
terceros contactados: 0», `tesis.html` publica «Peticiones a terceros: 0», y
la política de privacidad entera cuelga de ahí: sin red no hay tratamiento que
declarar, y por eso la factura de nadie sale de su ordenador.

Hasta el 6 de septiembre de 2026 esa cifra **no la comprobaba nada**. La
medía una persona abriendo el panel del navegador durante el ritual de
despliegue, cuando se acordaba. Un `@import` en el CSS, una tipografía de
Google o una biblioteca desde un CDN la volverían falsa sin romper nada, sin
salir en rojo y sin que nadie se enterara —y lo que se vuelve falso ahí no es
una cifra: es una política de privacidad publicada—.

Ahora hay dos guardianes y hacen falta los dos:

- **Este**, estático, que mira lo que se escribe: ninguna página, hoja de
  estilo ni script pide nada a un dominio de fuera. Corre en cada `pytest`,
  antes de publicar.
- **El del banco** («esta página no le pide nada a nadie»), que mide lo que el
  navegador ha pedido de verdad, dentro de la página publicada. Ese es el que
  cazaría un respaldo a la CDN de Pyodide, que va escrito dentro de
  `pyodide.js` y no en ningún fichero de aquí.

Lo que este no puede ver, dicho: `pyodide.js` y el `.whl` no se leen aquí —son
de fuera y se traen montados—, y una dirección compuesta en tiempo de
ejecución tampoco. Para eso está el otro.
"""
from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"

# Lo que un navegador se baja **solo**, sin que nadie pulse nada. Un enlace no
# está aquí a propósito: `<a href="https://www.aepd.es">` en el aviso legal es
# una dirección que se ofrece, no una petición que se hace. La diferencia es
# justo la que separa «no hablo con nadie» de «no te llevo a ninguna parte».
SE_PIDE_SOLO = (
    ("link", "href"), ("script", "src"), ("img", "src"), ("img", "srcset"),
    ("iframe", "src"), ("frame", "src"), ("embed", "src"), ("object", "data"),
    ("source", "src"), ("source", "srcset"), ("video", "src"),
    ("video", "poster"), ("audio", "src"), ("track", "src"), ("input", "src"),
    ("use", "href"), ("image", "href"),
)

DE_FUERA = re.compile(r"^(?:https?:)?//", re.I)
# `data:` y `blob:` salen del propio documento y no tocan la red.
UNA_DIRECCION = re.compile(r"""url\(\s*['"]?([^'")]+)""", re.I)


def _paginas() -> list[pathlib.Path]:
    """Las páginas del sitio y los artículos de la bitácora.

    Los segundos son trozos y no páginas enteras —el armazón se lo pone
    `bitacora.html` al montar—, pero acaban servidos al navegador igual que
    todo lo demás. Una `<img>` a un dominio ajeno dentro de un artículo
    rompería la cifra publicada sin que nada fallara, que es exactamente el
    fallo que esta prueba existe para no tener.
    """
    return sorted(WEB.glob("*.html")) + sorted((WEB / "bitacora").glob("*.html"))


def _sin_comentarios(texto: str, marcas=("//", "/*", "*")) -> list[str]:
    """Las líneas que no son prosa.

    No es un analizador: es un filtro de líneas. Se queda corto a propósito
    —un comentario al final de una línea de código no lo quita— y eso lo hace
    equivocarse siempre hacia el lado bueno: mira de más, nunca de menos.
    """
    return [l for l in texto.splitlines() if not l.strip().startswith(marcas)]


@pytest.mark.parametrize("pagina", _paginas(), ids=lambda p: p.name)
def test_ninguna_pagina_se_baja_nada_de_fuera(pagina):
    from lxml import html as lhtml

    arbol = lhtml.fromstring(pagina.read_text(encoding="utf-8"))
    fuera = []
    for etiqueta, atributo in SE_PIDE_SOLO:
        for nodo in arbol.iter(etiqueta):
            valor = (nodo.get(atributo) or "").strip()
            if valor and DE_FUERA.match(valor):
                fuera.append(f"<{etiqueta} {atributo}=\"{valor}\">")
    # Y lo que se pide desde el estilo, que es por donde entran las letras.
    estilos = [nodo.get("style") or "" for nodo in arbol.iter()]
    estilos += [nodo.text or "" for nodo in arbol.iter("style")]
    for estilo in estilos:
        fuera += [f"url({d})" for d in UNA_DIRECCION.findall(estilo)
                  if DE_FUERA.match(d.strip())]
        if "@import" in estilo:
            fuera.append("@import en un <style>")

    assert not fuera, (
        f"«{pagina.name}» se baja algo de otro dominio: {', '.join(fuera)}.\n"
        "La política de privacidad publica «0 dominios de terceros» y de esa "
        "frase cuelga que aquí no haya nada que declarar. O se quita, o se "
        "cambia la política."
    )


def test_la_hoja_de_estilo_no_trae_nada_de_fuera():
    """Por aquí es por donde entran las tipografías, que es lo normal."""
    fuera = []
    for hoja in sorted(WEB.glob("*.css")):
        texto = "\n".join(_sin_comentarios(hoja.read_text(encoding="utf-8")))
        fuera += [f"{hoja.name}: url({d})" for d in UNA_DIRECCION.findall(texto)
                  if DE_FUERA.match(d.strip())]
        if re.search(r"@import", texto):
            fuera.append(f"{hoja.name}: @import")
    assert not fuera, (
        f"la hoja de estilo pide algo de fuera: {', '.join(fuera)}. Las letras "
        "de esta página viajan con ella (`web/letra/`) justamente para que "
        "«tipos de letra externos: ninguno» siga siendo verdad."
    )


def test_ningun_script_de_la_pagina_nombra_una_direccion_de_fuera():
    """No es un analizador y no lo pretende: es un cepo.

    Cualquier `https://` fuera de un comentario en el JavaScript de la página
    es sospechoso, aunque no llegue a pedirse nunca. Lo que no puede pasar es
    que aparezca uno y nadie lo mire.
    """
    fuera = []
    for guion in sorted(WEB.glob("*.js")):
        for numero, linea in enumerate(
                guion.read_text(encoding="utf-8").splitlines(), 1):
            if linea.strip().startswith(("//", "/*", "*")):
                continue
            for direccion in re.findall(r"https?://[^\s\"'`)]+", linea):
                # El namespace de un SVG es un identificador, no una dirección:
                # nadie lo pide nunca.
                if direccion.startswith("http://www.w3.org/"):
                    continue
                fuera.append(f"{guion.name}:{numero} {direccion}")
    assert not fuera, (
        "el JavaScript de la página nombra direcciones de fuera:\n"
        + "\n".join(fuera)
        + "\nSi es deliberado, esto tiene que decirlo y la política de "
          "privacidad también."
    )


def test_las_cifras_publicadas_siguen_diciendo_cero():
    """El guardián y la promesa, atados: si una se mueve, la otra falla.

    Sin esto, alguien podría cambiar la cifra publicada a «3» y las pruebas
    de arriba seguirían en verde comprobando algo que ya nadie afirma.
    """
    legal = (WEB / "legal.html").read_text(encoding="utf-8")
    assert re.search(
        r"<dt>Dominios de terceros contactados</dt>\s*<dd>0</dd>", legal), (
        "`legal.html` ya no publica «Dominios de terceros contactados: 0» con "
        "esa forma. O ha cambiado la cifra —y entonces hay que mirar por qué— "
        "o ha cambiado la redacción y este guardián se ha quedado ciego.")

    tesis = (WEB / "sobre.html").read_text(encoding="utf-8")
    assert re.search(
        r"<dt>Peticiones a terceros</dt>\s*<dd>0<", tesis), (
        "`sobre.html` ya no publica «Peticiones a terceros: 0» con esa forma.")
