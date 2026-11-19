# -*- coding: utf-8 -*-
"""Las tarjetas sociales: una por página, pintadas al montar el sitio.

Por qué hace falta
------------------
Cuando alguien pega un enlace de glosa-e.com en LinkedIn, en un grupo de
WhatsApp o en un correo, lo que sale no es la página: es lo que digan las
etiquetas `og:` de su cabecera. Sin `og:image` sale un rectángulo gris, y un
rectángulo gris al lado de un enlace es lo que la gente no pulsa.

Ninguna red social admite SVG ahí, ni X, ni LinkedIn, ni WhatsApp, ni
Facebook, así que tiene que ser un PNG de verdad, de 1200x630.

Por qué una por página, y por qué al montar
-------------------------------------------
Hasta el 19-11-2026 había una sola, `web/marca/tarjeta.png`, versionada ya
hecha y generada a mano con `herramientas/tarjeta.py`. Se hacía así para no
instalar Pillow en cada despliegue por un fichero que cambiaba una vez cada
seis meses. Con una sola, quien pegaba el enlace de la ficha de BR-CO-15 veía
la portada, y la vista previa no decía de qué iba la página que se compartía:
de las 454 páginas con tarjeta, 453 se presentaban con la cara de la portada.

Una por página son 454 imágenes, y cambian con lo que cambia la página, así
que ya no se pueden versionar hechas: se pintan **de la página montada**, al
final del montaje, y no de una tabla escrita aparte. Una tabla se queda atrás
y entonces la tarjeta anuncia una página que ya no es esa; leída de la página,
dice lo mismo que ella por construcción. Pillow pasa a ser dependencia de la
construcción, fijada como lxml en `vercel.json` y `requisitos-pruebas.txt`.

Medido el 19-11-2026 en el equipo del titular, sobre el sitio entero: 5,4 s en
pintarlas y 8,3 s en guardarlas, 6,6 MB en total, 14 kB de media y 26 kB la
mayor. Se guardan con paleta de 256 colores y no en RGB: en RGB eran 18,3 MB
y 17,5 s, y la paleta se aparta del original como mucho 13/255 en unos 180
píxeles del suavizado de los bordes, que no se ven.

Tres moldes, elegidos por el titular sobre maquetas ese mismo día:

- **portada**: el titular y el lema de la portada a un lado, y al otro un
  trozo de factura con la glosa que le pondría la página (la de siempre, del
  25-09-2026: es la única que enseña lo que hace la herramienta en vez de
  decirlo);
- **ficha**: la glosa del código en grande, abrazada por el corchete del color
  de su gravedad, como la glosa en el informe;
- **página**: lo mismo con el corchete en el acento, para los artículos (con
  Blog encima y la fecha debajo) y para las demás páginas (su titular y la
  primera frase de su descripción).

La de error, `404.html`, no tiene: no se indexa ni se comparte.

Lo que se copia de la página, y no se inventa
---------------------------------------------
La tipografía es **Literata**, bajo SIL Open Font License 1.1: la misma
`web/letra/literata.woff2` que sirve la página, con el eje óptico ya fijado en
12, que es el de la marca, y los pesos de 400 a 600. Hasta el 24-09-2026 se
pintaba con la de Google Fonts y por eso, cuando la hoja cambió de gris el
23-09-2026, la tarjeta se quedó con el viejo: regenerarla pedía una descarga.
Usar la del sistema haría que cada máquina pintara una tarjeta distinta, que es
justo lo que `web/marca/trazar.py` documentó y resolvió para el logotipo.

Los colores son los de `web/glosa.css`, tema claro, y la marca es la de la
cabecera: `tests/test_contraste.py` y `tests/test_tarjeta.py` comparan las dos
copias con la hoja.

Todo va en Literata, también las cifras y los códigos, aunque la página los
pone en su mono: la mono de la página es la del sistema, y por lo mismo de
arriba la tarjeta saldría distinta en cada máquina que la montase.
"""
from __future__ import annotations

import hashlib
import html
import io
import re
from dataclasses import dataclass
from functools import cached_property
from itertools import combinations
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:   # en el navegador no hace falta, y allí no está
    Image = ImageDraw = ImageFilter = ImageFont = None

# Dónde se dejan dentro del sitio montado: `tarjetas/<página>.png`.
CARPETA = "tarjetas"
# Las páginas que no llevan tarjeta.
SIN_TARJETA = ("404.html",)


class TarjetaMal(ValueError):
    """Una página de la que no se puede pintar su tarjeta, y por qué.

    `paquete` la convierte en su negativa, `SinTarjetas`: este módulo no puede
    importar `paquete`, que lo importa a él.
    """


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
AVISO = "#85560a"
NOTA = "#3f4d63"

COLOR_DE = {"error": ERROR, "aviso": AVISO, "nota": NOTA}

ANCHO, ALTO = 1200, 630
MARGEN = 84

# La marca es la de la cabecera de la página, `.marca` en `web/glosa.css`, y
# no otra. Hasta el 24-09-2026 la tarjeta pintaba la del favicon (el bloque
# gris con dos líneas blancas) y el nombre en Literata 400; la página lleva el
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

# La glosa del folio de la portada. Es un código de verdad y su explicación de
# verdad: la primera frase sale de `validador/glosario.py` tal cual, y
# `tests/test_tarjeta.py` lo comprueba. Los importes son de muestra, y la
# cuenta se hace aquí para que la tarjeta no pueda sumar mal.
GLOSA_CODIGO = "BR-CO-15"
GLOSA_FRASE = "El total con impuestos no es la base imponible más el importe de impuestos"
BASE, TIPO, TOTAL_DECLARADO = 1000, 21, 1200

# Los formatos, al pie de la portada.
FORMATOS = "Facturae · UBL · CII · EDIFACT"

# Donde se pinta la glosa en las fichas y las páginas: el corchete en el
# margen y el texto a su derecha.
X_CORCHETE = MARGEN
X_TEXTO = MARGEN + 46
ANCHO_TEXTO = ANCHO - X_TEXTO - MARGEN
# La línea de base del pie: la fecha de un artículo y los formatos de la portada.
Y_PIE = ALTO - 72

# Las palabras que no se dejan al final de una línea de un titular, como no
# las dejaría quien compone a mano: "de la" arriba y "factura" abajo se lee
# como dos titulares.
_DEBILES = frozenset(
    "de la el en y a un una los las del al que se su no o con por para lo es e u".split())


# --- la letra ---------------------------------------------------------------

_FUENTES: dict[tuple[str, int, int], "ImageFont.FreeTypeFont"] = {}
_BASES: dict[str, "Image.Image"] = {}


@dataclass(frozen=True)
class Letra:
    """La Literata de la página, leída una vez y servida a cada tamaño.

    Abrir un woff2 es descomprimirlo, y cada tarjeta pide la letra a seis o
    siete tamaños: sin guardarla, pintar las 454 tardaba 14,9 s y no 5,4.
    """

    datos: bytes

    @cached_property
    def huella(self) -> str:
        return hashlib.sha256(self.datos).hexdigest()

    def __call__(self, tamano: int, peso: int) -> "ImageFont.FreeTypeFont":
        clave = (self.huella, tamano, peso)
        if clave not in _FUENTES:
            _FUENTES[clave] = _abrir(self.datos, tamano, peso)
        return _FUENTES[clave]


def _abrir(datos: bytes, tamano: int, peso: int) -> "ImageFont.FreeTypeFont":
    # El motor de composición, fijado. Sin decirlo, Pillow usa RAQM donde
    # encuentra libfribidi y BASIC donde no: en el equipo del titular es BASIC
    # (medido el 19-11-2026), y en la construcción del alojamiento no se sabe.
    # La Literata servida lleva el interletraje solo en GPOS, que BASIC no
    # aplica y RAQM sí, así que con motores distintos cambian los avances, los
    # cortes de línea, los píxeles y el `?v=` de las 454 páginas, y
    # `--avisar-indexnow` vería todas distintas. Se fija el que hay aquí, que
    # es con el que se aprobaron las maquetas; `tests/test_tarjeta.py` lleva
    # las huellas de tres tarjetas, y GitHub las comprueba en Linux.
    fuente = ImageFont.truetype(io.BytesIO(datos), tamano,
                                layout_engine=ImageFont.Layout.BASIC)
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
                raise TarjetaMal(
                    f"La letra no llega al peso {peso}: va de {eje['minimum']} "
                    f"a {eje['maximum']}.")
            valores.append(peso)
        elif "optical" in nombre.lower():
            valores.append(12)
        else:
            valores.append(eje["default"])
    fuente.set_variation_by_axes(valores)
    return fuente


def que_falta(ruta_letra: Path) -> str | None:
    """Por qué no se podrían pintar las tarjetas, o `None` si se puede.

    Se pregunta antes de escribir el primer byte del sitio. Abre la letra de
    verdad, y no solo mira que esté: un FreeType compilado sin brotli no lee
    woff2, y eso no se sabe hasta que se intenta.
    """
    if Image is None:
        return (
            "no está Pillow, que es con lo que se pintan. Instala la versión "
            "fijada en `requisitos-pruebas.txt`."
        )
    if not ruta_letra.is_file():
        return (
            f"no está la letra, {ruta_letra}. Se genera con `python "
            "web/marca/letra.py Literata.ttf OFL.txt`."
        )
    try:
        Letra(ruta_letra.read_bytes())(20, 400)
    except (OSError, TarjetaMal) as error:
        return f"Pillow no sabe abrir la letra {ruta_letra}: {error}."
    return None


# --- partir y encajar el texto ----------------------------------------------

def _partir(texto: str, fuente, ancho: float) -> list[str]:
    """Las líneas, llenando cada una todo lo que cabe.

    Una palabra más ancha que la caja se parte por donde llegue: la URN de la
    especificación de la AEAT son 67 caracteres sin un espacio, y sin esto se
    salía de la tarjeta por la derecha.
    """
    lineas, actual = [], ""
    for palabra in texto.split():
        while fuente.getlength(palabra) > ancho:
            corte = len(palabra)
            while corte > 1 and fuente.getlength(palabra[:corte]) > ancho:
                corte -= 1
            if actual:
                lineas.append(actual)
                actual = ""
            lineas.append(palabra[:corte])
            palabra = palabra[corte:]
        prueba = f"{actual} {palabra}".strip()
        if fuente.getlength(prueba) <= ancho:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    return [linea for linea in lineas + [actual] if linea]


def _equilibrar(texto: str, fuente, ancho: float, n: int) -> list[str] | None:
    """Como `text-wrap: balance` en la página: `n` líneas de ancho parecido,
    sin dejar al final de una un artículo o una preposición. Por fuerza bruta,
    que un titular son pocas palabras."""
    palabras = texto.split()
    if n <= 1:
        return [texto]
    if len(palabras) <= n or len(palabras) > 24:
        return None
    mejor = None
    for cortes in combinations(range(1, len(palabras)), n - 1):
        trozos = [" ".join(palabras[a:b])
                  for a, b in zip((0,) + cortes, cortes + (len(palabras),))]
        anchos = [fuente.getlength(t) for t in trozos]
        if max(anchos) > ancho:
            continue
        debiles = sum(1 for t in trozos[:-1] if t.split()[-1].lower() in _DEBILES)
        nota = (max(anchos) - min(anchos)) + 400 * debiles
        if mejor is None or nota < mejor[0]:
            mejor = (nota, trozos)
    return mejor[1] if mejor else None


def _titular(texto: str, letra: Letra, ancho: float,
             tamanos: tuple[tuple[int, int], ...]):
    """El tamaño más grande al que el titular cabe en sus líneas, repartido
    con equilibrio; `None` si no cabe ni al más pequeño."""
    for tamano, maximo in tamanos:
        fuente = letra(tamano, 600)
        lineas = _partir(texto, fuente, ancho)
        if len(lineas) <= maximo:
            return fuente, tamano, _equilibrar(texto, fuente, ancho, len(lineas)) or lineas
    return None


def _cortar_en_clausula(texto: str, fuente, ancho: float, maximo: int) -> list[str] | None:
    """Si no cabe, se corta en la última pausa que deje lo de delante dentro:
    dos puntos, punto y coma o coma, por ese orden, y se dice con puntos
    suspensivos. Cortar en una pausa deja una frase que se entiende; cortar
    en la última palabra que cabe, no siempre."""
    # Con el espacio detrás: los dos puntos de urn:aeat:names no son una pausa.
    for signo in (": ", "; ", ", "):
        trozos = texto.split(signo)
        for i in range(len(trozos) - 1, 0, -1):
            cabeza = signo.join(trozos[:i]).strip().rstrip(":;,")
            if len(cabeza) >= 40 and len(_partir(cabeza + "…", fuente, ancho)) <= maximo:
                return _partir(cabeza + "…", fuente, ancho)
    return None


def _cortar_en_palabra(texto: str, fuente, ancho: float, maximo: int) -> list[str]:
    """Lo que cabe en `maximo` líneas, cortado en la última palabra entera."""
    lineas = _partir(texto, fuente, ancho)[:maximo]
    ultima = lineas[-1]
    while " " in ultima:
        ultima = ultima.rsplit(" ", 1)[0]
        if fuente.getlength(ultima.rstrip(",;:.") + "…") <= ancho:
            break
    lineas[-1] = ultima.rstrip(",;:.") + "…"
    return lineas


# --- dibujar ----------------------------------------------------------------

def _marca(lienzo, x: float, centro: float, tamano: float, letra: Letra,
           signo: str = ACENTO, nombre: str = TINTA) -> float:
    """La marca de la cabecera: el signo y el nombre, con el nombre a `tamano` px.

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
    fuente = letra(round(tamano), NOMBRE_PESO)
    dibujo = ImageDraw.Draw(lienzo)
    empieza = x + ancho + HUECO_REM * rem
    base = centro + BASE_BAJO_EL_CENTRO * tamano
    palabra = "Glosa-e"
    for i, una in enumerate(palabra):
        dx = fuente.getlength(palabra[:i + 1]) - fuente.getlength(una)
        dibujo.text((empieza + dx + i * NOMBRE_ESPACIADO * tamano, base), una,
                    font=fuente, fill=nombre, anchor="ls")
    return empieza + fuente.getlength(palabra) + (len(palabra) - 1) * NOMBRE_ESPACIADO * tamano


def _lienzo(letra: Letra):
    """El papel con la marca arriba, que es igual en todas: se pinta una vez
    por letra y se copia."""
    if letra.huella not in _BASES:
        base = Image.new("RGBA", (ANCHO, ALTO), PAPEL)
        _marca(base, MARGEN, 104, 38, letra)
        _BASES[letra.huella] = base
    lienzo = _BASES[letra.huella].copy()
    return lienzo, ImageDraw.Draw(lienzo)


def _importe(n: float) -> str:
    """Como se escribe un importe en una factura española: 1.210,00."""
    return f"{n:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def _versalitas(dibujo, x, y, texto, fuente, color, aire) -> float:
    """Letra a letra, con `aire` px entre cada una; devuelve dónde acaba."""
    for una in texto:
        dibujo.text((x, y), una, font=fuente, fill=color, anchor="ls")
        x += fuente.getlength(una) + aire
    return x


def _corchete(dibujo, x, arriba, abajo, color, grosor=4, brazo=18) -> None:
    """El de `.glosa .cuerpo::before`: borde arriba, a la izquierda y abajo."""
    dibujo.rectangle([x, arriba, x + grosor - 1, abajo], fill=color)
    dibujo.rectangle([x, arriba, x + brazo, arriba + grosor - 1], fill=color)
    dibujo.rectangle([x, abajo - grosor + 1, x + brazo, abajo], fill=color)


def _centrar(lienzo, arriba: int, abajo: int, desde: int = 150, hasta: int = 590):
    """Mueve el bloque de la glosa para que quede centrado entre la marca y el
    pie. Se pinta arriba y se mueve después porque cuánto mide no se sabe
    hasta haberlo partido en líneas."""
    destino = desde + max(0, (hasta - desde - (abajo - arriba)) // 2)
    if destino == arriba:
        return lienzo
    trozo = lienzo.crop((0, arriba - 4, ANCHO, abajo + 4))
    limpio = lienzo.copy()
    ImageDraw.Draw(limpio).rectangle([0, arriba - 4, ANCHO, abajo + 4], fill=PAPEL)
    limpio.paste(trozo, (0, destino - 4))
    return limpio


# Los tamaños que se prueban para el titular de la portada, del mayor al menor,
# y cuántas líneas se le consienten. La columna acaba donde empieza el folio.
_TAMANOS_DE_LA_PORTADA = ((64, 4), (60, 4), (56, 4), (52, 4), (48, 4))
_X_DEL_FOLIO = 640


def portada(titular: str, lema: str, letra: Letra):
    """El titular y el lema de la portada, y el folio con su glosa al margen.

    El titular y el lema son los de la portada, leídos de ella: la tarjeta
    promete lo que la página cumple, y si dijera otra cosa sería un anzuelo.
    """
    lienzo, dibujo = _lienzo(letra)
    # El folio empieza en 640 y no en 620 como hasta el 19-11-2026: la columna
    # del titular llega así a 516 px, y "factura electrónica," mide 509 a 52 px.
    x0, y0, x1, y1 = _X_DEL_FOLIO, 70, ANCHO - MARGEN + 20, ALTO - 70
    columna = x0 - 40 - MARGEN
    fuente_lema = letra(27, 400)
    lineas_lema = _partir(lema, fuente_lema, 440)
    for tamano, maximo in _TAMANOS_DE_LA_PORTADA:
        fuente = letra(tamano, 600)
        lineas = _partir(titular, fuente, columna)
        salto = round(tamano * 1.155)
        primera = 162 + tamano
        fin_del_lema = primera + (len(lineas) - 1) * salto + 52 + (len(lineas_lema) - 1) * 36
        if len(lineas) <= maximo and fin_del_lema <= 520:
            break
    else:
        raise TarjetaMal(
            f"el titular de la portada no cabe en la tarjeta ni a 48 px en "
            f"cuatro líneas con el lema debajo: {titular}")
    lineas = _equilibrar(titular, fuente, columna, len(lineas)) or lineas
    y = primera
    for linea in lineas:
        dibujo.text((MARGEN, y), linea, font=fuente, fill=TINTA, anchor="ls")
        y += salto
    y += 52 - salto
    for linea in lineas_lema:
        dibujo.text((MARGEN, y), linea, font=fuente_lema, fill=TINTA_2, anchor="ls")
        y += 36
    dibujo.text((MARGEN, Y_PIE), FORMATOS, font=letra(21, 400), fill=TENUE, anchor="ls")

    # El folio, con la sombra de `--sombra`: poca, y hacia abajo.
    sombra = Image.new("RGBA", lienzo.size, (0, 0, 0, 0))
    ImageDraw.Draw(sombra).rounded_rectangle([x0 + 6, y0 + 10, x1 - 6, y1 + 10], 14,
                                             fill=(20, 24, 28, 40))
    lienzo.alpha_composite(sombra.filter(ImageFilter.GaussianBlur(18)))
    dibujo = ImageDraw.Draw(lienzo)
    dibujo.rounded_rectangle([x0, y0, x1, y1], 14, fill=PANEL, outline=BORDE, width=2)
    pad = 40
    _versalitas(dibujo, x0 + pad, y0 + 58, "FACTURA DE MUESTRA", letra(17, 600), TENUE, 2)

    cifras = letra(25, 400)
    iva = BASE * TIPO / 100
    y = y0 + 118
    for concepto, importe in (("Base imponible", BASE), (f"IVA {TIPO} %", iva)):
        dibujo.text((x0 + pad, y), concepto, font=cifras, fill=TINTA_2, anchor="ls")
        dibujo.text((x1 - pad, y), _importe(importe), font=cifras, fill=TINTA, anchor="rs")
        y += 44
    dibujo.line([(x0 + pad, y - 22), (x1 - pad, y - 22)], fill=BORDE, width=2)
    y += 14
    # El total que no cuadra, marcado como lo marca el informe.
    total = letra(27, 600)
    declarado = _importe(TOTAL_DECLARADO)
    ancho = total.getlength(declarado)
    dibujo.rounded_rectangle([x1 - pad - ancho - 12, y - 30, x1 - pad + 12, y + 12], 6,
                             fill=ERROR_FLOJO)
    dibujo.text((x0 + pad, y), "Total", font=total, fill=TINTA, anchor="ls")
    dibujo.text((x1 - pad, y), declarado, font=total, fill=ERROR, anchor="rs")
    dibujo.line([(x1 - pad - ancho, y + 6), (x1 - pad, y + 6)], fill=ERROR, width=2)

    # La glosa: el código fuera, contra un filete, como en la página.
    gy, gx = y + 62, x0 + pad + 22
    fin = _versalitas(dibujo, gx, gy, GLOSA_CODIGO, letra(22, 600), ERROR, 0.5)
    _versalitas(dibujo, fin + 14, gy - 1, "ERROR", letra(14, 600), ERROR, 2)
    cuerpo = letra(22, 400)
    frase = (f"{GLOSA_FRASE}: {_importe(BASE)} y {_importe(iva)} "
             f"suman {_importe(BASE + iva)}.")
    lineas = _partir(frase, cuerpo, x1 - pad - gx)
    for i, linea in enumerate(lineas):
        dibujo.text((gx, gy + 40 + i * 31), linea, font=cuerpo, fill=TINTA_2, anchor="ls")
    dibujo.line([(x0 + pad, gy - 22), (x0 + pad, gy + 40 + (len(lineas) - 1) * 31 + 8)],
                fill=ERROR, width=3)
    return lienzo.convert("RGB")


def ficha(codigo: str, gravedades: tuple[str, ...], norma: str, mensaje: str,
          letra: Letra):
    """La glosa de un código: con qué gravedad sale, el código, de qué norma
    viene y la primera frase de su explicación, como la dice su página."""
    lienzo, dibujo = _lienzo(letra)
    color = COLOR_DE[gravedades[0]] if gravedades else TENUE

    # El código, tan grande como quepa en una línea, entre 52 y 76.
    tamano = 76
    while letra(tamano, 600).getlength(codigo) > ANCHO_TEXTO and tamano > 52:
        tamano -= 2
    if letra(tamano, 600).getlength(codigo) > ANCHO_TEXTO:
        raise TarjetaMal(f"el código {codigo} no cabe en una línea de la tarjeta ni a 52 px.")

    arriba = 176
    y = arriba + 30
    if gravedades:
        x = X_TEXTO
        for i, gravedad in enumerate(gravedades):
            if i:
                enlace = " o " if i == len(gravedades) - 1 else ", "
                x = _versalitas(dibujo, x, y, enlace, letra(19, 400), TENUE, 1)
            x = _versalitas(dibujo, x, y, gravedad.upper(), letra(19, 600),
                            COLOR_DE[gravedad], 2.5)
    else:
        _versalitas(dibujo, X_TEXTO, y, "SIN GRAVEDAD FIJA", letra(19, 600), TENUE, 2.5)
    y += 18 + round(tamano * 0.82)
    _versalitas(dibujo, X_TEXTO, y, codigo, letra(tamano, 600), color, 0)
    y += 40
    dibujo.text((X_TEXTO, y), norma, font=letra(22, 400), fill=TENUE, anchor="ls")

    # El mensaje: entero a 40 px en tres líneas o a 36 en cuatro; si no, se
    # corta en una pausa a 36, y si no la hay, en una palabra a 33 en cinco.
    for tm, maximo in ((40, 3), (36, 4)):
        fm = letra(tm, 400)
        lineas = _partir(mensaje, fm, ANCHO_TEXTO)
        if len(lineas) <= maximo:
            break
    else:
        lineas = _cortar_en_clausula(mensaje, fm, ANCHO_TEXTO, 4)
        if lineas is None:
            tm = 33
            fm = letra(tm, 400)
            lineas = _partir(mensaje, fm, ANCHO_TEXTO)
            if len(lineas) > 5:
                lineas = _cortar_en_palabra(mensaje, fm, ANCHO_TEXTO, 5)
    salto = round(tm * 1.36)
    y += 30 + round(tm * 1.1)
    for linea in lineas:
        dibujo.text((X_TEXTO, y), linea, font=fm, fill=TINTA, anchor="ls")
        y += salto
    abajo = y - salto + round(tm * 0.42)
    _corchete(dibujo, X_CORCHETE, arriba, abajo, color)
    return _centrar(lienzo, arriba, abajo).convert("RGB")


_TAMANOS_DE_LA_PAGINA = ((64, 3), (56, 4), (50, 4), (46, 5))


def pagina(titulo: str, letra: Letra, rotulo: str | None = None,
           entradilla: str | None = None, pie: str | None = None):
    """El titular de una página con el corchete en el acento, la primera
    frase de su descripción si cabe entera, y para los artículos, Blog encima
    y la fecha debajo."""
    lienzo, dibujo = _lienzo(letra)
    arriba = 176
    y = arriba + 30
    if rotulo:
        dibujo.text((X_TEXTO, y), rotulo, font=letra(24, 600), fill=ACENTO, anchor="ls")
        y += 22
    encajado = _titular(titulo, letra, ANCHO_TEXTO, _TAMANOS_DE_LA_PAGINA)
    if encajado is None:
        raise TarjetaMal(
            f"el titular no cabe en la tarjeta ni a 46 px en cinco líneas: {titulo}")
    fuente, tamano, lineas = encajado
    salto = round(tamano * 1.16)
    y += round(tamano * 0.95)
    for linea in lineas:
        dibujo.text((X_TEXTO, y), linea, font=fuente, fill=TINTA, anchor="ls")
        y += salto
    y -= salto
    # La entradilla, solo entera: cortada a media frase diría menos que nada.
    if entradilla:
        cabe = min(2, max(0, (ALTO - 120 - y - 10) // 38))
        fe = letra(27, 400)
        lineas = _partir(entradilla, fe, ANCHO_TEXTO)
        if cabe and len(lineas) <= cabe:
            y += 54
            for linea in lineas:
                dibujo.text((X_TEXTO, y), linea, font=fe, fill=TINTA_2, anchor="ls")
                y += 38
            y -= 38
    abajo = y + round(tamano * 0.3)
    _corchete(dibujo, X_CORCHETE, arriba, abajo, ACENTO)
    lienzo = _centrar(lienzo, arriba, abajo, hasta=520 if pie else 590)
    if pie:
        ImageDraw.Draw(lienzo).text((X_TEXTO, Y_PIE), pie, font=letra(22, 400),
                                    fill=TENUE, anchor="ls")
    return lienzo.convert("RGB")


# --- leer la página montada -------------------------------------------------

_RE_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
_RE_DESCRIPCION = re.compile(r'<meta name="description" content="([^"]*)"')
_RE_LEMA = re.compile(r'<p class="lema">\s*<b>(.*?)</b>', re.S)
_RE_FECHA = re.compile(r"<time[^>]*>([^<]*)</time>\s*<h1", re.S)
_RE_DICE = re.compile(r'<p class="dice">(.*?)</p>', re.S)
_RE_GRAVEDADES = re.compile(r'<p class="gravedades">(.*?)</p>', re.S)
_RE_GRAVEDAD = re.compile(r'<span class="cuenta (error|aviso|nota)">')
_RE_VIENE = re.compile(r"<dt>De dónde viene</dt><dd>(.*?)</dd>", re.S)
# El final de la primera frase: un punto y, detrás, lo que empieza otra.
_RE_FIN_DE_FRASE = re.compile(r"\.\s+(?=[A-ZÁÉÍÓÚÑ¿¡\u00ab\"(])")


def _texto(fragmento: str) -> str:
    """Lo que lee una persona de un trozo de HTML: sin etiquetas, sin
    entidades, y un salto de línea forzado como un espacio."""
    fragmento = re.sub(r"<br\s*/?>", " ", fragmento)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", fragmento)).split())


def primera_frase(texto: str) -> str:
    fin = _RE_FIN_DE_FRASE.search(texto)
    return texto[: fin.start() + 1] if fin else texto


def _con_punto(frase: str) -> str:
    return frase if frase.endswith((".", ":", "?", "!")) else frase + "."


def _uno(patron: re.Pattern, texto: str, nombre: str, que: str) -> str:
    hallado = patron.search(texto)
    if not hallado:
        raise TarjetaMal(f"no tiene {que}, que es de donde sale su tarjeta.")
    return hallado.group(1)


@dataclass(frozen=True)
class Tarjeta:
    """Lo que la cabecera de una página necesita saber de su tarjeta."""

    ruta: str      # dentro del sitio: `tarjetas/<página>.png`
    huella: str    # los ocho primeros, para el `?v=`
    alt: str       # lo que dice, para quien no la ve


def _pintar(nombre: str, texto: str, letra: Letra, fichas: set[str],
            articulos: set[str]):
    """La imagen de una página y su texto alternativo, según de qué molde sea."""
    titulo = _texto(_uno(_RE_H1, texto, nombre, "un <h1>"))
    if nombre == "index.html":
        lema = _texto(_uno(_RE_LEMA, texto, nombre, "un lema en negrita"))
        return portada(titulo, lema, letra), f"{_con_punto(titulo)} {lema}"
    if nombre in fichas:
        gravedades = tuple(_RE_GRAVEDAD.findall(
            _uno(_RE_GRAVEDADES, texto, nombre, "sus gravedades")))
        viene = _texto(_uno(_RE_VIENE, texto, nombre, "de dónde viene"))
        norma = viene.split(": ", 1)[0]
        # "De la casa" se entiende en la página, donde lo explica la línea de
        # al lado; suelto en una tarjeta no dice de qué casa.
        if norma == "De la casa":
            norma = "Criterio de Glosa-e"
        mensaje = primera_frase(_texto(_uno(_RE_DICE, texto, nombre, "su explicación")))
        imagen = ficha(titulo, gravedades, norma, mensaje, letra)
        dicha = " o ".join(gravedades) or "sin gravedad fija"
        return imagen, f"{titulo} ({dicha}, {norma}): {mensaje}"
    # Sin descripción no se para aquí: la exige la canónica, en `paquete`, con
    # su porqué, y esta tarjeta se pinta igual sin la entradilla.
    descripcion = _RE_DESCRIPCION.search(texto)
    entradilla = primera_frase(_texto(descripcion[1])) if descripcion else None
    if nombre in articulos:
        fecha = _texto(_uno(_RE_FECHA, texto, nombre, "su fecha justo antes del <h1>"))
        imagen = pagina(titulo, letra, rotulo="Blog", entradilla=entradilla, pie=fecha)
        return imagen, f"Blog de Glosa-e, {fecha}: {titulo}"
    alt = f"{_con_punto(titulo)} {entradilla}" if entradilla else titulo
    return pagina(titulo, letra, entradilla=entradilla), alt


# Los cubos de color con los que cuantiza FASTOCTREE: 16 niveles por canal
# para los finos y 4 para los gruesos (`QuantOctree.c` de Pillow 12.3.0).
_FINO, _GRUESO = 4, 6


def _cubos(rgb, bits: int) -> int:
    """Cuántos cubos de color usa la imagen, con `8 - bits` bits por canal."""
    return len(rgb.point(lambda v: v >> bits).getcolors(256 ** 3 >> (3 * bits)))


def _guardar(imagen, ruta: Path) -> str:
    """Guarda la imagen con paleta y devuelve su huella para el `?v=`.

    La huella es la de **los píxeles**, el color que acaba teniendo cada uno,
    y no la del PNG ni la de la paleta. Tiene que salir igual montando aquí
    que en el alojamiento, porque el `?v=` va dentro de cada página y
    `--avisar-indexnow` compara las páginas montadas aquí con las que sirve
    producción: con otra huella allí, se negaría siempre.

    Medido el 19-11-2026, la primera vez que GitHub pintó tarjetas en Linux:
    los colores salían iguales y las huellas no, porque la de entonces miraba
    la paleta y sus índices. Pillow ordena la paleta por cuántos píxeles tiene
    cada color, con el `qsort` de la biblioteca de C del sistema, y cuando dos
    cuentas empatan cada sistema las deja en otro orden: la de glibc conserva
    el de llegada y la de Windows no. Mismos colores, otro orden, otros
    índices, otra huella. Se arregla en dos sitios:

    - La huella sale de la imagen pasada a RGB, que no sabe en qué orden
      estaba la paleta.
    - La paleta se guarda ordenada por color, para que el PNG tampoco dependa
      de eso (dos colores idénticos en la paleta quedarían en cualquier orden,
      pero eso no toca la huella).

    El orden de los empates puede decidir también **qué** colores entran, y
    eso sí cambiaría los píxeles: FASTOCTREE mete primero los cubos gruesos
    usados y llena lo que queda con los finos de más píxeles. Mientras quepan
    todos los finos, ningún empate deja uno fuera, y cada píxel acaba con la
    media de su cubo fino, que no depende del orden. Si no cupieran, se niega:
    medido ese día en las 454 tarjetas, la más justa (la de
    SPFE-RECTIFICATIVA) usa 122 finos y 19 gruesos, 115 por debajo del tope,
    y las 454 salen con los mismos colores que antes del arreglo.
    """
    rgb = imagen.convert("RGB")
    finos, gruesos = _cubos(rgb, _FINO), _cubos(rgb, _GRUESO)
    if finos + gruesos > 256:
        raise TarjetaMal(
            f"la tarjeta usa {finos} cubos de color finos y {gruesos} gruesos, "
            "más de los 256 de la paleta, y cuáles entran dependería de cómo "
            "ordene el sistema: aquí y en el alojamiento saldrían píxeles "
            "distintos. Se arregla con menos colores (un degradado, una foto) en "
            "el molde."
        )
    cuantizada = rgb.quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                              dither=Image.Dither.NONE)
    colores = cuantizada.getpalette()
    usados = sorted((i for _, i in cuantizada.getcolors(256)),
                    key=lambda i: tuple(colores[3 * i:3 * i + 3]))
    ordenada = cuantizada.remap_palette(usados)
    huella = hashlib.sha256(
        f"{ordenada.width}x{ordenada.height}".encode()
        + ordenada.convert("RGB").tobytes()).hexdigest()[:8]
    ordenada.save(ruta, optimize=True)
    return huella


def fabricar(destino: Path, letra: Letra, fichas: set[str],
             articulos: set[str]) -> dict[str, Tarjeta]:
    """Pinta la tarjeta de cada página de `destino` y dice cuál es la de cada una.

    `fichas` y `articulos` son los nombres de las páginas que el montaje ha
    escrito de cada clase; la portada es `index.html`, y el resto son páginas
    sueltas. Se niega con `TarjetaMal` si una página no dice lo que su molde
    necesita, o si su titular no cabe.
    """
    carpeta = destino / CARPETA
    carpeta.mkdir(parents=True, exist_ok=True)
    tarjetas = {}
    for ruta in sorted(destino.glob("*.html")):
        if ruta.name in SIN_TARJETA:
            continue
        try:
            imagen, alt = _pintar(ruta.name, ruta.read_text(encoding="utf-8"), letra,
                                  fichas, articulos)
        except TarjetaMal as error:
            raise TarjetaMal(f"{ruta.name}: {error}") from error
        publicada = f"{CARPETA}/{ruta.stem}.png"
        tarjetas[ruta.name] = Tarjeta(publicada, _guardar(imagen, destino / publicada), alt)
    return tarjetas
