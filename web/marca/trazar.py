# -*- coding: utf-8 -*-
"""Genera `glosa-e.svg`: el bloque de la marca, con la palabra trazada.

Este script no hace falta para nada del día a día. El SVG que produce está
versionado al lado. Está aquí por lo contrario: porque sin él la marca sería un
dibujo de 5 KB imposible de retocar sin volver a hacerlo entero.

Hasta el 23-09-2026 la página lo llevaba además incrustado en `glosa.css`, como
fondo de la cabecera, y este script escribía las dos copias a la vez. Ya no: la
cabecera lleva el signo y el nombre en la letra de la página, y el bloque queda
para donde va suelto —el favicon, la tarjeta social y este SVG—. El porqué, en
`MARCA.md`.

## Por qué la palabra va trazada y no como `<text>`

Desde que el nombre vive dentro del bloque, si viajara como texto cada máquina
lo compondría con la serif que tuviera a mano —Iowan Old Style en un Mac,
Palatino Linotype en Windows, Georgia si no hay ninguna— y la marca cambiaría
de forma sin que nadie la tocara. Trazada, es la misma en todas partes.

## Qué fuente, y por qué esa

**Literata, peso 400**, bajo SIL Open Font License 1.1:

    https://github.com/google/fonts/blob/main/ofl/literata/

La fuente **no está en este repositorio** y no hace falta que lo esté: lo que
se reparte son contornos dentro de un SVG, no el fichero de la tipografía. Para
volver a generar la marca hay que bajarla; son 933 KB y la licencia permite
redistribuirla, pero versionar un megabyte que se usa una vez cada seis meses
no compensa.

Estuvo trazada de Palatino Linotype unas horas del 30 de agosto de 2026. Se
cambió porque Palatino viene con Windows, no es redistribuible y su licencia
no dice nada de llevar sus contornos dentro de una marca: la marca colgaba de
un permiso inexistente. El porqué entero, y las otras tres candidatas que se
miraron, están en `MARCA.md`.

## Cómo se ejecuta

    pip install fonttools                        # no es dependencia del proyecto
    curl -L -o Literata.ttf \\
      "https://raw.githubusercontent.com/google/fonts/main/ofl/literata/Literata%5Bopsz,wght%5D.ttf"
    python web/marca/trazar.py Literata.ttf

Escribe `web/marca/glosa-e.svg`. Y `tests/test_marca.py` se pone rojo si el
bloque vuelve a aparecer en la hoja de estilo, donde ya no se regenera: una
copia que nadie reescribe es una copia que se desvía en silencio.
"""
import sys

from pathlib import Path

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "glosa-e.svg"

PALABRA = "Glosa-e"
PESO = 400
EJE_OPTICO = 12          # Literata trae opsz 7..72; 12 es su tamaño de lectura
TRACKING = 0.01          # el letter-spacing .01em que tenía la marca en texto

# La geometría, en unidades de un alto de 100. Son las proporciones aprobadas
# mirándolas el 30 de agosto de 2026 y no se tocan al cambiar de fuente: si se
# movieran a la vez la letra y la caja, no se estaría comparando nada.
ALTO = 100
PROPORCION = 2.85
SIGNO_ANCHO = 62.0
HUECO = 16.0
PLATA = "#949494"

# El signo: el corchete al margen y las tres líneas. Es lo que se pone, desde
# siempre, para señalar el pasaje que se comenta.
SIGNO = ["M16 7 H8 V33 H16", "M25 12 h21", "M25 20 h21", "M25 28 h13"]
SIGNO_CAJA = (48, 40)

# La altura de la tinta, heredada de la marca aprobada. Normalizar por aquí y
# no por el cuerpo es lo que permite cambiar de tipografía sin cambiar de
# tamaño: dos fuentes al mismo cuerpo dan palabras de alturas distintas, porque
# la equis de una está en 400/1000 y la de otra en 530.
ALTO_DE_TINTA = 28.2


def trazar(ruta_fuente: Path):
    """Devuelve (camino SVG, caja de la tinta) de la palabra."""
    try:
        from fontTools.pens.boundsPen import BoundsPen
        from fontTools.pens.svgPathPen import SVGPathPen
        from fontTools.pens.transformPen import TransformPen
        from fontTools.ttLib import TTFont
        from fontTools.varLib import instancer
    except ImportError:
        raise SystemExit(
            "Falta fontTools, que no es dependencia del proyecto: se instala\n"
            "solo para esto. `pip install fonttools`.")

    fuente = TTFont(ruta_fuente)
    if "fvar" not in fuente:
        raise SystemExit(
            f"«{ruta_fuente}» no es una fuente variable. La que se espera es\n"
            "Literata[opsz,wght].ttf, tal como la publica Google Fonts.")
    # Un variable sin instanciar dibuja siempre su instancia por defecto: pedir
    # peso 400 y no instanciar daría el mismo trazo que pedir 700, sin que nada
    # avisara. Sale todo verde y no es lo que crees que has probado.
    fuente = instancer.instantiateVariableFont(
        fuente, {"wght": PESO, "opsz": EJE_OPTICO})

    upem = fuente["head"].unitsPerEm
    cmap = fuente.getBestCmap()
    juego = fuente.getGlyphSet()

    pluma = SVGPathPen(juego, ntos=lambda v: f"{v:.1f}")
    limites = BoundsPen(juego)
    x = 0.0
    for letra in PALABRA:
        nombre = cmap.get(ord(letra))
        if nombre is None:
            raise SystemExit(f"La fuente no tiene «{letra}».")
        glifo = juego[nombre]
        glifo.draw(TransformPen(pluma, (1, 0, 0, 1, x, 0)))
        glifo.draw(TransformPen(limites, (1, 0, 0, 1, x, 0)))
        x += glifo.width + TRACKING * upem
    return pluma.getCommands(), limites.bounds


def armar(camino: str, caja):
    """Devuelve (svg, ancho de la palabra, holgura que sobra en el bloque)."""
    x0, y0, x1, y1 = caja
    escala = ALTO_DE_TINTA / (y1 - y0)
    ancho_palabra = (x1 - x0) * escala
    ancho_bloque = round(ALTO * PROPORCION)

    contenido = SIGNO_ANCHO + HUECO + ancho_palabra
    if contenido > ancho_bloque - 20:
        # No se recorta ni se aprieta el hueco: se para y se dice. Una marca
        # que se ajusta sola deja de ser la marca aprobada.
        raise SystemExit(
            f"La palabra no cabe: {contenido:.1f} de contenido en un bloque de "
            f"{ancho_bloque}. Hay que subir la proporción a mano.")

    izq = (ancho_bloque - contenido) / 2
    signo_escala = SIGNO_ANCHO / SIGNO_CAJA[0]
    signo_y = (ALTO - SIGNO_CAJA[1] * signo_escala) / 2
    # Se centra por la caja real de la tinta y no por la línea base: «Glosa-e»
    # no tiene descendentes, y centrarla por la base la dejaría alta.
    palabra_x = izq + SIGNO_ANCHO + HUECO - x0 * escala
    palabra_y = (ALTO + ALTO_DE_TINTA) / 2 + y0 * escala

    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ancho_bloque} {ALTO}"',
        f'     width="{ancho_bloque}" height="{ALTO}" role="img" aria-label="{PALABRA}">',
        f'  <rect width="{ancho_bloque}" height="{ALTO}" fill="{PLATA}"/>',
        f'  <g transform="translate({izq:.2f} {signo_y:.2f}) scale({signo_escala:.5f})"',
        '     fill="none" stroke="#FFFFFF" stroke-width="3"',
        '     stroke-linecap="round" stroke-linejoin="round">',
    ]
    partes += [f'    <path d="{d}"/>' for d in SIGNO]
    partes += [
        '  </g>',
        f'  <path transform="translate({palabra_x:.2f} {palabra_y:.2f}) '
        f'scale({escala:.6f} -{escala:.6f})"',
        f'        fill="#000000" d="{camino}"/>',
        '</svg>',
    ]
    return "\n".join(partes) + "\n", ancho_palabra, ancho_bloque - 20 - contenido


def main(argv) -> int:
    if len(argv) != 2:
        raise SystemExit(f"Uso: python {Path(__file__).name} Literata.ttf")
    fuente = Path(argv[1])
    if not fuente.is_file():
        raise SystemExit(f"No encuentro «{fuente}».")

    svg, ancho, holgura = armar(*trazar(fuente))
    antes = SALIDA.read_text(encoding="utf-8") if SALIDA.is_file() else None
    # `newline=""` para que Windows no meta retornos de carro: este fichero
    # acaba dentro de una hoja de estilo y se compara byte a byte en una
    # prueba, así que una diferencia que no significa nada sobra.
    SALIDA.write_text(svg, encoding="utf-8", newline="")

    print(f"{SALIDA.name}: {len(svg.encode('utf-8'))} bytes")
    print(f"  la palabra mide {ancho:.1f} de ancho sobre un bloque de "
          f"{round(ALTO * PROPORCION)}, y sobran {holgura:.1f}")
    if antes is None:
        print("  no había nada antes")
    elif antes == svg:
        print("  idéntico al que había: la fuente y los parámetros son los mismos")
    else:
        print("  **ha cambiado**. Si no era la intención, mira qué fuente le "
              "has dado.")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
