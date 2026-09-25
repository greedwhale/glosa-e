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
está para poder rehacerla. Generarla al montar obligaría a instalar Pillow
**en cada despliegue**, para producir un fichero que cambia una vez cada seis
meses.

Cómo se ejecuta
---------------
    pip install pillow                           # no es dependencia del proyecto
    python -m herramientas.tarjeta

Pinta con `web/letra/literata.woff2`, **la Literata que sirve la página**, y no
hay que bajar nada. Hasta el 24-09-2026 pedía la de Google Fonts, y por eso,
cuando la hoja cambió de gris el 23-09-2026, la tarjeta se quedó con el
viejo: regenerarla exigía una descarga. La de la página vale igual: viene con el eje óptico ya
fijado en 12, que es el que usa la marca, y con los pesos de 400 a 600, que son
los dos que usa la tarjeta; y trae todas las letras que la tarjeta escribe. Se
le puede pasar otra, como la de Google Fonts con sus dos ejes:

    python -m herramientas.tarjeta Literata.ttf

La tipografía es **Literata**, bajo SIL Open Font License 1.1, la misma que la
marca y la misma que sirve la página. Usar la del sistema aquí haría que la
tarjeta saliera distinta en cada máquina que la regenerase, que es justo lo que
`trazar.py` documentó y resolvió para el logotipo.
"""

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# Los colores son los de `web/glosa.css`, tema claro. No se inventa ninguno:
# la tarjeta es lo primero que se ve de la página y tiene que ser la página.
PAPEL = "#fbfaf7"
PANEL = "#ffffff"
TINTA = "#16181c"
TINTA_2 = "#454b54"
TENUE = "#676c76"
BORDE = "#e3e0d7"
ACENTO = "#1c4e80"
ERROR = "#a3231c"
ERROR_FLOJO = "#fbeceb"

ANCHO, ALTO = 1200, 630
MARGEN = 84

# La marca es la de la cabecera de la página, `.marca` en `web/glosa.css`, y
# no otra. Hasta el 24-09-2026 la tarjeta pintaba la del favicon —el bloque
# gris con dos líneas blancas— y el nombre en Literata 400; la página lleva el
# signo en el azul del acento, sin caja y con tres líneas, y el nombre en 600.
# Quien pegaba el enlace veía una marca que la página no usa.
# `tests/test_tarjeta.py` lee estas cifras y las compara con las de la hoja.
#
# El signo, en la caja de su máscara (el `viewBox` de `.marca::before`).
SIGNO_CAJA = (48, 40)
SIGNO_TRAZOS = (
    ((16, 7), (8, 7), (8, 33), (16, 33)),
    ((25, 12), (46, 12)),
    ((25, 20), (46, 20)),
    ((25, 28), (38, 28)),
)
SIGNO_GROSOR = 3.5
# Las medidas de la cabecera, en rem: el nombre, 1.3; la caja del signo,
# 1.85 × 1.55; el hueco entre los dos, .6. Van tal cual y se escalan al tamaño
# que lleve el nombre en la tarjeta.
NOMBRE_REM, SIGNO_REM, HUECO_REM = 1.3, (1.85, 1.55), 0.6
NOMBRE_PESO, NOMBRE_ESPACIADO = 600, -0.01
# Dónde cae la línea de base del nombre bajo el centro del signo, en em.
# Medido en el navegador el 24-09-2026: 0,4408. CSS centra la caja de línea y
# no la letra, y Pillow no tiene cajas de línea, así que se copia la medida en
# vez de rehacer el cálculo con métricas que no son las del navegador.
BASE_BAJO_EL_CENTRO = 0.4408
# El signo se pinta a este múltiplo y se reduce: Pillow no suaviza los trazos,
# y a tamaño real salía dentado, que se veía en la tarjeta vieja.
SOBREMUESTREO = 4

# La glosa del folio. Es un código de verdad y su explicación de verdad: la
# primera frase sale de `validador/glosario.py` tal cual, y
# `tests/test_tarjeta.py` lo comprueba. Los importes son de muestra, y la
# cuenta se hace aquí para que la tarjeta no pueda sumar mal.
GLOSA_CODIGO = "BR-CO-15"
GLOSA_FRASE = "El total con impuestos no es la base imponible más el importe de impuestos"
BASE, TIPO, TOTAL_DECLARADO = 1000, 21, 1200

DESTINO = pathlib.Path("web/marca/tarjeta.png")
LETRA = pathlib.Path("web/letra/literata.woff2")


def _letra(ruta: str, tamano: int, peso: int) -> ImageFont.FreeTypeFont:
    fuente = ImageFont.truetype(ruta, tamano)
    # El eje óptico fijo en 12, el mismo que usa `trazar.py` para la marca y
    # `letra.py` para la que sirve la página. Así el titular de la tarjeta y el
    # logotipo salen de la misma forma de letra.
    #
    # Los ejes se ponen por su nombre y no por su sitio: la Literata de Google
    # trae dos, el óptico y el peso, y la que sirve la página solo el peso,
    # porque el óptico ya viene fijado en 12. Por posición, un [12, peso]
    # sobre la de la página pedía un peso de 12.
    valores = []
    for eje in fuente.get_variation_axes():
        nombre = eje["name"].decode() if isinstance(eje["name"], bytes) else eje["name"]
        if "weight" in nombre.lower():
            if not eje["minimum"] <= peso <= eje["maximum"]:
                raise SystemExit(f"{ruta} no llega al peso {peso}: va de "
                                 f"{eje['minimum']} a {eje['maximum']}")
            valores.append(peso)
        elif "optical" in nombre.lower():
            valores.append(12)
        else:
            valores.append(eje["default"])
    fuente.set_variation_by_axes(valores)
    return fuente


def _marca(lienzo: Image.Image, x: float, centro: float, tamano: float,
           ruta_letra: str, signo: str = ACENTO, nombre: str = TINTA) -> float:
    """La marca de la cabecera: el signo y «Glosa-e», con el nombre a `tamano` px.

    `x` es donde empieza el signo y `centro`, su centro vertical, que es la
    línea sobre la que la cabecera alinea los dos. Devuelve dónde acaba el
    nombre.
    """
    rem = tamano / NOMBRE_REM
    ancho, alto = SIGNO_REM[0] * rem, SIGNO_REM[1] * rem
    # `contain`: la máscara entra entera en su caja, escalada y centrada.
    escala = min(ancho / SIGNO_CAJA[0], alto / SIGNO_CAJA[1])
    izq = x + (ancho - SIGNO_CAJA[0] * escala) / 2
    arriba = centro - SIGNO_CAJA[1] * escala / 2

    k = SOBREMUESTREO
    x0, y0 = int(izq) - 2, int(arriba) - 2
    capa = Image.new("RGBA", ((int(ancho) + 5) * k, (int(alto) + 5) * k), (0, 0, 0, 0))
    trazo = ImageDraw.Draw(capa)
    grosor = SIGNO_GROSOR * escala * k
    for puntos in SIGNO_TRAZOS:
        escalados = [((izq - x0 + px * escala) * k, (arriba - y0 + py * escala) * k)
                     for px, py in puntos]
        trazo.line(escalados, fill=signo, width=round(grosor), joint="curve")
        # Pillow no tiene extremos redondeados, y la máscara los lleva.
        for px, py in (escalados[0], escalados[-1]):
            r = grosor / 2
            trazo.ellipse([px - r, py - r, px + r, py + r], fill=signo)
    capa = capa.resize((capa.width // k, capa.height // k), Image.LANCZOS)
    lienzo.paste(capa, (x0, y0), capa)

    # El nombre, letra a letra para poder apretarlo lo que la cabecera: cada
    # letra va donde la deja la anterior, con su espaciado de par, menos el
    # `letter-spacing`.
    fuente = _letra(ruta_letra, round(tamano), NOMBRE_PESO)
    dibujo = ImageDraw.Draw(lienzo)
    empieza = x + ancho + HUECO_REM * rem
    base = centro + BASE_BAJO_EL_CENTRO * tamano
    palabra = "Glosa-e"
    for i, letra in enumerate(palabra):
        dx = fuente.getlength(palabra[:i + 1]) - fuente.getlength(letra)
        dibujo.text((empieza + dx + i * NOMBRE_ESPACIADO * tamano, base), letra,
                    font=fuente, fill=nombre, anchor="ls")
    return empieza + fuente.getlength(palabra) + (len(palabra) - 1) * NOMBRE_ESPACIADO * tamano


def _importe(n: float) -> str:
    """Como se escribe un importe en una factura española: 1.210,00."""
    return f"{n:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def _partir(texto: str, fuente: ImageFont.FreeTypeFont, ancho: float) -> list[str]:
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if fuente.getlength(prueba) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    return lineas + [actual]


def _versalitas(dibujo, x, y, texto, fuente, color, aire) -> float:
    """Letra a letra, con `aire` px entre cada una; devuelve dónde acaba."""
    for letra in texto:
        dibujo.text((x, y), letra, font=fuente, fill=color, anchor="ls")
        x += fuente.getlength(letra) + aire
    return x


def dibujar(ruta_letra: str) -> Image.Image:
    """La glosa al margen: el titular a un lado, y al otro un trozo de factura
    con la glosa que le pondría la página. Elegida por el titular el
    25-09-2026 entre tres propuestas: es la única que enseña lo que hace la
    herramienta en vez de decirlo.

    Todo va en Literata, también las cifras y el código, aunque la página los
    pone en su mono: la mono de la página es la del sistema, y una tarjeta
    pintada con la letra de la máquina que la regenera sale distinta en cada
    una, que es lo que este guion evita desde el principio.
    """
    lienzo = Image.new("RGBA", (ANCHO, ALTO), PAPEL)
    _marca(lienzo, MARGEN, 104, 38, ruta_letra)
    dibujo = ImageDraw.Draw(lienzo)

    # El titular. Es el de la portada, palabra por palabra: la tarjeta promete
    # lo que la página cumple, y si dijera otra cosa sería un anzuelo. En tres
    # líneas, como en la portada a lo estrecho.
    titular = _letra(ruta_letra, 64, 600)
    dibujo.text((MARGEN, 236), "La factura", font=titular, fill=TINTA, anchor="ls")
    dibujo.text((MARGEN, 310), "electrónica,", font=titular, fill=TINTA, anchor="ls")
    dibujo.text((MARGEN, 384), "en castellano.", font=titular, fill=TINTA, anchor="ls")
    lema = _letra(ruta_letra, 27, 400)
    lineas = _partir("Lo que dice tu factura, y lo que no se ha podido mirar.", lema, 440)
    for i, linea in enumerate(lineas):
        dibujo.text((MARGEN, 440 + i * 38), linea, font=lema, fill=TINTA_2, anchor="ls")
    dibujo.text((MARGEN, ALTO - 72), "Facturae · UBL · CII · EDIFACT",
                font=_letra(ruta_letra, 21, 400), fill=TENUE, anchor="ls")

    # El folio, con la sombra de `--sombra`: poca, y hacia abajo.
    x0, y0, x1, y1 = 620, 70, ANCHO - MARGEN + 20, ALTO - 70
    sombra = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle([x0 + 6, y0 + 10, x1 - 6, y1 + 10], 14,
                                             fill=(20, 24, 28, 40))
    lienzo.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(18)))
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.rounded_rectangle([x0, y0, x1, y1], 14, fill=PANEL, outline=BORDE, width=2)
    pad = 40
    _versalitas(dibujo, x0 + pad, y0 + 58, "FACTURA DE MUESTRA",
                _letra(ruta_letra, 17, 600), TENUE, 2)

    cifras = _letra(ruta_letra, 25, 400)
    iva = BASE * TIPO / 100
    y = y0 + 118
    for concepto, importe in (("Base imponible", BASE), (f"IVA {TIPO} %", iva)):
        dibujo.text((x0 + pad, y), concepto, font=cifras, fill=TINTA_2, anchor="ls")
        dibujo.text((x1 - pad, y), _importe(importe), font=cifras, fill=TINTA, anchor="rs")
        y += 44
    dibujo.line([(x0 + pad, y - 22), (x1 - pad, y - 22)], fill=BORDE, width=2)
    y += 14
    # El total que no cuadra, marcado como lo marca el informe.
    total = _letra(ruta_letra, 27, 600)
    declarado = _importe(TOTAL_DECLARADO)
    ancho = total.getlength(declarado)
    dibujo.rounded_rectangle([x1 - pad - ancho - 12, y - 30, x1 - pad + 12, y + 12], 6,
                             fill=ERROR_FLOJO)
    dibujo.text((x0 + pad, y), "Total", font=total, fill=TINTA, anchor="ls")
    dibujo.text((x1 - pad, y), declarado, font=total, fill=ERROR, anchor="rs")
    dibujo.line([(x1 - pad - ancho, y + 6), (x1 - pad, y + 6)], fill=ERROR, width=2)

    # La glosa: el código fuera, contra un filete, como en la página.
    gy, gx = y + 62, x0 + pad + 22
    fin = _versalitas(dibujo, gx, gy, GLOSA_CODIGO, _letra(ruta_letra, 22, 600), ERROR, 0.5)
    _versalitas(dibujo, fin + 14, gy - 1, "ERROR", _letra(ruta_letra, 14, 600), ERROR, 2)
    cuerpo = _letra(ruta_letra, 22, 400)
    frase = (f"{GLOSA_FRASE}: {_importe(BASE)} y {_importe(iva)} "
             f"suman {_importe(BASE + iva)}.")
    lineas = _partir(frase, cuerpo, x1 - pad - gx)
    for i, linea in enumerate(lineas):
        dibujo.text((gx, gy + 40 + i * 31), linea, font=cuerpo, fill=TINTA_2, anchor="ls")
    dibujo.line([(x0 + pad, gy - 22), (x0 + pad, gy + 40 + (len(lineas) - 1) * 31 + 8)],
                fill=ERROR, width=3)
    return lienzo.convert("RGB")


if __name__ == "__main__":
    letra = sys.argv[1] if len(sys.argv) > 1 else str(LETRA)
    if not pathlib.Path(letra).is_file():
        raise SystemExit(
            f"no está «{letra}». Se corre desde la raíz del repositorio, donde "
            f"está {LETRA}, o se le pasa la letra como argumento."
        )
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    dibujar(letra).save(DESTINO, "PNG", optimize=True)
    print(f"{DESTINO}: {DESTINO.stat().st_size} bytes, {ANCHO}x{ALTO}")
