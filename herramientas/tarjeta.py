# -*- coding: utf-8 -*-
"""Genera `web/marca/tarjeta.png`: lo que se ve al pegar el enlace fuera.

Por qué hace falta
------------------
Cuando alguien pega `glosa-e.com` en LinkedIn, en un grupo de WhatsApp o en un
correo, lo que sale no es la página: es lo que digan las etiquetas `og:` de la
cabecera. Sin `og:image` sale un rectángulo gris, y un rectángulo gris al lado
de un enlace es lo que la gente no pulsa.

Ninguna red social admite SVG ahí —ni X, ni LinkedIn, ni WhatsApp, ni
Facebook—, así que tiene que ser un PNG de verdad, de 1200x630.

Por qué se genera aquí y no al montar el sitio
----------------------------------------------
Igual que `web/marca/trazar.py`: la imagen se versiona ya hecha y este guion
está para poder rehacerla. Generarla al montar obligaría a instalar Pillow y a
bajar un megabyte de tipografía **en cada despliegue**, para producir un
fichero que cambia una vez cada seis meses.

Y por lo mismo que allí, la letra no se versiona: lo que se reparte es el PNG.

Cómo se ejecuta
---------------
    pip install pillow                           # no es dependencia del proyecto
    curl -L -o Literata.ttf \\
      "https://raw.githubusercontent.com/google/fonts/main/ofl/literata/Literata%5Bopsz,wght%5D.ttf"
    python -m herramientas.tarjeta Literata.ttf

La tipografía es **Literata 400**, bajo SIL Open Font License 1.1, la misma que
la marca y la misma que sirve la página. Usar la del sistema aquí haría que la
tarjeta saliera distinta en cada máquina que la regenerase, que es justo lo que
`trazar.py` documentó y resolvió para el logotipo.
"""

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

# Los colores son los de `web/glosa.css`, tema claro. No se inventa ninguno:
# la tarjeta es lo primero que se ve de la página y tiene que ser la página.
PAPEL = "#fbfaf7"
TINTA = "#16181c"
TINTA_2 = "#454b54"
TENUE = "#6e747e"
BORDE = "#e3e0d7"
ACENTO = "#1c4e80"
BLOQUE = "#949494"

ANCHO, ALTO = 1200, 630
MARGEN = 84

DESTINO = pathlib.Path("web/marca/tarjeta.png")


def _letra(ruta: str, tamano: int, peso: int) -> ImageFont.FreeTypeFont:
    fuente = ImageFont.truetype(ruta, tamano)
    # El eje óptico fijo en 12, el mismo que usa `trazar.py` para la marca y
    # `letra.py` para la que sirve la página. Así el titular de la tarjeta y el
    # logotipo salen de la misma forma de letra.
    fuente.set_variation_by_axes([12, peso])
    return fuente


def _marca(dibujo: ImageDraw.ImageDraw, x: int, y: int, lado: int) -> None:
    """El bloque de la marca: el corchete y las dos líneas, en blanco.

    Son las mismas coordenadas del icono de la página, sobre una caja de 64,
    escaladas. Se redibujan en vez de traerse el SVG porque aquí hay que
    rasterizar de todas formas y son seis trazos.
    """
    dibujo.rectangle([x, y, x + lado, y + lado], fill=BLOQUE)
    k = lado / 64
    grosor = max(2, round(6 * k))

    def linea(puntos):
        escalados = [(x + px * k, y + py * k) for px, py in puntos]
        dibujo.line(escalados, fill="#ffffff", width=grosor, joint="curve")
        # Pillow no tiene extremos redondeados, y el icono los lleva. Con los
        # trazos cortados en recto la marca se ve distinta de la de la página.
        for px, py in (escalados[0], escalados[-1]):
            r = grosor / 2
            dibujo.ellipse([px - r, py - r, px + r, py + r], fill="#ffffff")

    linea([(25, 17), (15, 17), (15, 47), (25, 47)])
    linea([(34, 24), (50, 24)])
    linea([(34, 40), (50, 40)])


def dibujar(ruta_letra: str) -> Image.Image:
    lienzo = Image.new("RGB", (ANCHO, ALTO), PAPEL)
    dibujo = ImageDraw.Draw(lienzo)

    # La franja del acento, a la izquierda y estrecha. Es el único color fuerte
    # de la tarjeta: el resto es papel y tinta, como la página.
    dibujo.rectangle([0, 0, 10, ALTO], fill=ACENTO)

    lado = 84
    _marca(dibujo, MARGEN, MARGEN, lado)
    dibujo.text(
        (MARGEN + lado + 26, MARGEN + lado / 2),
        "Glosa-e",
        font=_letra(ruta_letra, 50, 400),
        fill=TINTA,
        anchor="lm",
    )

    # El titular. Es el de la portada, palabra por palabra: la tarjeta promete
    # lo que la página cumple, y si dijera otra cosa sería un anzuelo.
    titular = _letra(ruta_letra, 74, 600)
    dibujo.text((MARGEN, 248), "La factura electrónica,", font=titular, fill=TINTA)
    dibujo.text((MARGEN, 336), "en castellano.", font=titular, fill=TINTA)

    dibujo.text(
        (MARGEN, 446),
        "Lo que dice tu factura, y lo que no se ha podido mirar.",
        font=_letra(ruta_letra, 30, 400),
        fill=TINTA_2,
    )

    dibujo.line([(MARGEN, 516), (ANCHO - MARGEN, 516)], fill=BORDE, width=2)

    # Abajo, lo que nos separa y no una lista de virtudes. Las tres
    # comprobaciones van primero **porque la firma es la que no hace ningún
    # otro validador gratuito**, y en una tarjeta que se ve dos segundos eso
    # es lo único que hay que conseguir que se lea.
    dibujo.text(
        (MARGEN, 552),
        "Forma, contenido y firma      Facturae · UBL · CII · EDIFACT"
        "      Gratis, en tu navegador",
        font=_letra(ruta_letra, 25, 400),
        fill=TENUE,
    )
    return lienzo


if __name__ == "__main__":
    letra = sys.argv[1] if len(sys.argv) > 1 else "Literata.ttf"
    if not pathlib.Path(letra).is_file():
        raise SystemExit(
            f"no está «{letra}». Bájala con:\n"
            '  curl -L -o Literata.ttf "https://raw.githubusercontent.com/'
            'google/fonts/main/ofl/literata/Literata%5Bopsz,wght%5D.ttf"'
        )
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    dibujar(letra).save(DESTINO, "PNG", optimize=True)
    print(f"{DESTINO}: {DESTINO.stat().st_size} bytes, {ANCHO}x{ALTO}")
