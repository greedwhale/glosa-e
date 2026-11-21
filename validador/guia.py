# -*- coding: utf-8 -*-
"""El guía: contesta en la página con lo que el sitio ya tiene escrito.

Qué es, y qué no
----------------
Un asistente en la esquina de cada página (`web/guia.js`, desde el
17-11-2026) donde el visitante escribe su duda con sus palabras («me rechazan la
factura por el IVA», «qué es BR-CO-10», «desde cuándo me obliga») y recibe la
ficha, la pregunta frecuente o el artículo que la contesta, con su enlace y su
fuente. **No es un modelo de lenguaje y no escribe nada**: busca entre textos
que ya están publicados y comprobados, y cuando no encuentra, lo dice. Un
asistente que redacta puede inventarse una norma, y aquí inventarse una norma
es el peor fallo posible; por eso este no redacta.

Tampoco pide nada a nadie. Lo que sabe viaja en un fichero, `guia.json`, que
se arma al montar el sitio, y la búsqueda corre en el navegador de quien
pregunta. La pregunta no sale de ahí, igual que la factura.

Por qué el índice se calcula aquí y no en la página
---------------------------------------------------
Porque aquí se puede probar. La suite no tiene con qué ejecutar JavaScript, y
una búsqueda escrita solo en la página sería código sin una sola prueba. Así
que todo lo que decide (qué palabras cuentan, cuánto pesa cada una, qué ficha
gana) se calcula en Python, al montar, y viaja ya resuelto. La página solo
trocea la pregunta y suma. Ese troceo sí está escrito dos veces, aquí y en
`web/guia.js`, y para que las dos copias no se separen en silencio el fichero
lleva unas **comprobaciones**: preguntas con la respuesta que da esta
implementación. El asistente las repite con la suya al abrir cualquier página
con `#comprobar-guia`, y dice cuántas coinciden.

De dónde sale cada respuesta
----------------------------
- **Los códigos y las familias**, de `glosario.py`, que es de donde sale el
  catálogo. Se copia el principio de la explicación; la entera está en su ficha.
- **Las preguntas frecuentes**, de la portada; **los apartados**, de «Sobre
  Glosa-e»; **los artículos**, del blog. Se extraen del HTML publicado, a
  máquina: el guía no puede decir de ellos otra cosa que lo que dice la página.
- **Los temas**, escritos a mano más abajo. Son lo único que el sitio no
  publicaba ya: las fechas y el alcance de la obligación. Cada uno lleva la
  cita del BOE de la que sale y el día en que se leyó, y **un tema sin fuente
  oficial no se monta** (`GuiaMal`). Tampoco **un tema leído hace más de
  `TEMAS_VALEN_DIAS`**: lo demás se rehace solo en cada montaje, y esto no.

Lo que el guía no hace, a propósito
-----------------------------------
No agrupa los fallos de un informe, no dice a quién le toca arreglar cada uno
y no redacta nada. Explica y orienta, que es lo que hace el resto de la página
(MARCA.md: una glosa explica). Cuando la duda no cabe aquí, lo dice y ofrece
escribir al titular.

Y los enlaces a casa
--------------------
El sitio vive en `www.glosa-e.com` y en ningún otro subdominio. Un enlace a un
subdominio que no existe no falla al montar: falla en casa del visitante. Por
eso `revisar_los_subdominios` se niega si alguna página nombra uno que no esté
en `SUBDOMINIOS`.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import html
import json
import math
import re
import unicodedata
from pathlib import Path

from validador import cifras, normas
from validador.codigos import Codigo
from validador.glosario import FAMILIAS, explicar

__all__ = [
    "CODIGO", "DATOS", "LLAMADA_A_LOS_DATOS", "SUBDOMINIOS", "GuiaMal",
    "TEMAS_LEIDOS_EL", "TEMAS_VALEN_DIAS",
    "armar", "escribir", "montar", "buscar", "trocear",
    "revisar_la_lectura", "revisar_los_subdominios",
]

# El asistente, que el montaje pone en todas las páginas, y lo que sabe.
CODIGO = "guia.js"
DATOS = "guia.json"
# La línea del asistente que dice dónde están los datos. Al montar se le pone
# la huella del fichero, como al resto de lo que se sirve: si el índice
# cambia, cambia la dirección.
LLAMADA_A_LOS_DATOS = 'const DATOS_EN = "./guia.json";'

# Los subdominios de glosa-e.com que existen y se pueden enlazar. Uno nuevo se
# apunta aquí el día que conteste, no antes.
SUBDOMINIOS = frozenset({"www"})
_RE_SUBDOMINIO = re.compile(r"\b([a-z0-9-]+)\.glosa-e\.com\b", re.I)

# Los dos textos del BOE de los que salen los temas, y cuándo entró en vigor la
# orden, que es desde donde se cuentan todos los plazos (su disposición final
# única: «el día siguiente al de su publicación», y se publicó el 05-10-2026).
RD = ("Real Decreto 238/2026", "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-7295")
ORDEN = ("Orden HAC/1028/2026", "https://www.boe.es/diario_boe/txt.php?id=BOE-A-2026-20587")
ORDEN_EN_VIGOR = _dt.date(2026, 10, 6)
_FUENTES_OFICIALES = ("https://www.boe.es/",)
# El día en que se leyeron esos dos textos para escribir los temas y el
# cuestionario. Cuando se vuelvan a leer, se cambia aquí, y si dicen otra cosa,
# también el texto de los temas.
TEMAS_LEIDOS_EL = _dt.date(2026, 11, 16)
# Cuánto vale esa lectura. Todo lo demás que sabe el guía sale de lo publicado
# y se rehace en cada montaje; los temas y el cuestionario no, porque los
# escribe una persona leyendo el BOE. Si la norma cambia (otra orden, un
# aplazamiento), el guía seguiría contestando lo de antes, con su cita y su
# fecha, sin que nada lo delatara: es el fallo de esta casa, lo de ayer
# haciéndose pasar por lo de hoy. Por eso, pasado el plazo, el sitio no se
# monta hasta que alguien vuelva a leerlo. Treinta días, decidido el
# 20-11-2026, para que caiga dentro del repaso de cada mes y no se acumule.
# La página del estado de la norma tendrá su propio freno, más corto, cuando
# se haga: aquello lo comprueba una máquina y esto una persona.
TEMAS_VALEN_DIAS = 30

_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")


class GuiaMal(ValueError):
    """El guía no se puede armar sin faltar a lo que promete."""


def revisar_la_lectura(hoy: _dt.date | None = None) -> None:
    """Se niega si los temas llevan demasiado sin leerse en el BOE.

    También si dicen haberse leído en el futuro: es una errata al cambiar la
    fecha, y con ella el plazo no vencería nunca.
    """
    dia = hoy or _dt.date.today()
    if TEMAS_LEIDOS_EL > dia:
        raise GuiaMal(
            f"`TEMAS_LEIDOS_EL` dice {cifras.fecha(TEMAS_LEIDOS_EL)}, y hoy es "
            f"{cifras.fecha(dia)}. Una lectura que todavía no ha pasado no "
            "vale como lectura, y el plazo de los temas no vencería nunca.")
    vence = TEMAS_LEIDOS_EL + _dt.timedelta(days=TEMAS_VALEN_DIAS)
    if dia > vence:
        raise GuiaMal(
            f"Los temas del guía se leyeron en el BOE el "
            f"{cifras.fecha(TEMAS_LEIDOS_EL)} y esa lectura valía hasta el "
            f"{cifras.fecha(vence)}. Son lo único del guía que no se rehace "
            "solo: si la norma ha cambiado desde entonces, el guía seguiría "
            "contestando lo de antes con su cita. Vuelve a leer las fuentes de "
            "cada tema y del cuestionario en `validador/guia.py`, corrige lo "
            "que haya cambiado y pon la fecha de hoy en `TEMAS_LEIDOS_EL`.")


def _meses_despues(dia: _dt.date, meses: int) -> _dt.date:
    """De fecha a fecha, que es como cuenta los meses el Código Civil (art. 5)."""
    total = dia.month - 1 + meses
    return dia.replace(year=dia.year + total // 12, month=total % 12 + 1)


def _en_letra(dia: _dt.date) -> str:
    return f"{dia.day} de {_MESES[dia.month - 1]} de {dia.year}"


# Las cuatro fechas, calculadas y no tecleadas: si un día se corrige la de la
# orden, se mueven todas a la vez.
FECHA_GRANDES = _meses_despues(ORDEN_EN_VIGOR, 12)
FECHA_RESTO = _meses_despues(ORDEN_EN_VIGOR, 24)
FECHA_ESTADOS = _meses_despues(FECHA_RESTO, 12)
FECHA_SOLUCION = _meses_despues(FECHA_GRANDES, -2)

_NO_CERTIFICA = (
    "Esto orienta y no certifica: lo que cuenta es el texto del BOE, que va "
    "enlazado, y tu caso puede tener un matiz que aquí no se ve."
)


def _temas() -> list[dict]:
    """Lo que el sitio no publicaba todavía, cada cosa con su cita.

    Leídos el 16-11-2026 en los dos textos del BOE. Las frases siguen el
    texto de cerca a propósito: aquí una paráfrasis libre es una norma nueva.
    """
    grandes, resto = _en_letra(FECHA_GRANDES), _en_letra(FECHA_RESTO)
    return [
        {
            "id": "tema-fechas",
            "titulo": "Desde cuándo es obligatoria la factura electrónica entre empresas",
            "texto": (
                f"Depende de tu volumen de operaciones del año natural anterior. "
                f"Si pasó de 8 millones de euros, desde el {grandes}. Para el "
                f"resto de empresarios y profesionales, desde el {resto}. Son doce "
                f"y veinticuatro meses contados desde el {_en_letra(ORDEN_EN_VIGOR)}, "
                "el día en que entró en vigor la orden que desarrolla la solución "
                "pública."
            ),
            "palabras": "cuando obliga obligatoria fecha plazo empieza entra vigor "
                        "calendario autonomo pyme empresa grande millones",
            "fuentes": [
                (f"{RD[0]}, disposición final cuarta, apartado 1", RD[1]),
                (f"{ORDEN[0]}, disposición final única", ORDEN[1]),
            ],
        },
        {
            "id": "tema-ambito",
            "titulo": "A quién obliga la factura electrónica",
            "texto": (
                "A los empresarios y profesionales que ya están obligados a "
                "expedir factura, cuando el destinatario es otro empresario o "
                "profesional con sede, establecimiento permanente, domicilio o "
                "residencia habitual en España. El real decreto trata de las "
                "facturas entre empresarios y profesionales."
            ),
            "palabras": "quien obliga obligado afecta alcanza ambito aplicación "
                        "autonomo empresa profesional particular consumidor cliente",
            "fuentes": [(f"{RD[0]}, artículo 3.1", RD[1])],
        },
        {
            "id": "tema-excepciones",
            "titulo": "Qué facturas quedan fuera de la obligación",
            "texto": (
                "Las facturas simplificadas, salvo las cualificadas del artículo "
                "7.2 del Reglamento de facturación. Una orden ministerial puede "
                "excluir otras operaciones, en principio de forma temporal. Y el "
                "real decreto no se aplica a las actividades reguladas del "
                "operador del mercado eléctrico, a las funciones del operador del "
                "mercado organizado de gas ni a las operaciones liquidadas en las "
                "cámaras de compensación de la IATA."
            ),
            "palabras": "excepción excepciones excluida exenta fuera simplificada "
                        "tique ticket electrico gas iata libra",
            "fuentes": [
                (f"{RD[0]}, artículo 4", RD[1]),
                (f"{RD[0]}, disposición adicional segunda", RD[1]),
            ],
        },
        {
            "id": "tema-plataformas",
            "titulo": "Desde cuándo obliga a las plataformas privadas de intercambio",
            "texto": (
                f"Desde el {grandes}, doce meses después de la entrada en vigor de "
                "la orden: remitir la copia fiel de cada factura a la solución "
                "pública, interconectarse entre ellas y cumplir los requisitos "
                "para operar como plataforma."
            ),
            "palabras": "plataforma plataformas privada intercambio copia fiel "
                        "interconexion operador cuando fecha",
            "fuentes": [(f"{RD[0]}, disposición final cuarta, apartado 2", RD[1])],
        },
        {
            "id": "tema-estados",
            "titulo": "Los estados de la factura: plazo, y desde cuándo para un autónomo",
            "texto": (
                "El destinatario informa de los estados de la factura en un plazo "
                "máximo de cuatro días naturales, sin contar sábados, domingos ni "
                "festivos nacionales, desde que se produce cada estado. Para las "
                "personas físicas y las entidades en atribución de rentas que no "
                f"pasaron de 8 millones de euros, informar es voluntario hasta el "
                f"{_en_letra(FECHA_ESTADOS)}, doce meses después de su fecha de "
                "obligación."
            ),
            "palabras": "estado estados aceptación pago pagada cuatro días "
                        "plazo informar comunicar autonomo persona fisica voluntario",
            "fuentes": [
                (f"{RD[0]}, artículo 10.3", RD[1]),
                (f"{RD[0]}, disposición transitoria tercera", RD[1]),
            ],
        },
        {
            "id": "tema-solucion-publica",
            "titulo": "Cuándo estará disponible la solución pública de la AEAT",
            "texto": (
                "Al menos dos meses antes de la primera fecha de obligación, es "
                f"decir, a más tardar el {_en_letra(FECHA_SOLUCION)}."
            ),
            "palabras": "solución publica aeat hacienda agencia tributaria spfe "
                        "disponible cuando abre funcionamiento",
            "fuentes": [(f"{ORDEN[0]}, disposición adicional segunda", ORDEN[1])],
        },
    ]


def _cuestionario() -> dict:
    """«¿Me obliga, y desde cuándo?», con las mismas citas que los temas.

    Cada paso es una pregunta con sus salidas; una salida lleva a otro paso o
    a una respuesta. Las respuestas no añaden nada a los temas: los nombran.
    """
    grandes, resto = _en_letra(FECHA_GRANDES), _en_letra(FECHA_RESTO)
    df4 = [(f"{RD[0]}, disposición final cuarta, apartado 1", RD[1])]
    art3 = [(f"{RD[0]}, artículo 3.1", RD[1])]
    excepciones = (
        " Quedan fuera las facturas simplificadas que no sean cualificadas "
        "(artículo 4)."
    )
    return {
        "titulo": "¿Me obliga, y desde cuándo?",
        "inicio": "destinatario",
        "pasos": {
            "destinatario": {
                "pregunta": "¿A quién le facturas?",
                "salidas": [
                    ["A otras empresas o a profesionales, en España", "volumen"],
                    ["Solo a particulares", "particulares"],
                    ["A la Administración", "administracion"],
                ],
            },
            "volumen": {
                "pregunta": "¿Tu volumen de operaciones del año natural anterior "
                            "pasó de 8 millones de euros?",
                "salidas": [
                    ["Sí", "grandes"],
                    ["No", "forma"],
                    ["No lo sé", "sin-volumen"],
                ],
            },
            "forma": {
                "pregunta": "¿Facturas como persona física (autónomo) o como "
                            "entidad en atribución de rentas?",
                "salidas": [
                    ["Sí", "resto-fisica"],
                    ["No, es una sociedad u otra entidad", "resto"],
                ],
            },
        },
        "respuestas": {
            "grandes": {
                "texto": f"Te obliga desde el {grandes}, por las facturas que "
                         "expidas a otros empresarios o profesionales." + excepciones,
                "fuentes": df4 + art3,
            },
            "resto": {
                "texto": f"Te obliga desde el {resto}, por las facturas que "
                         "expidas a otros empresarios o profesionales." + excepciones,
                "fuentes": df4 + art3,
            },
            "resto-fisica": {
                "texto": f"Te obliga desde el {resto}, por las facturas que "
                         "expidas a otros empresarios o profesionales. Informar de "
                         "los estados de las facturas que recibas es voluntario "
                         f"hasta el {_en_letra(FECHA_ESTADOS)}." + excepciones,
                "fuentes": df4 + art3 + [
                    (f"{RD[0]}, disposición transitoria tercera", RD[1])],
            },
            "sin-volumen": {
                "texto": "La fecha depende de esa cifra. El real decreto la "
                         "calcula conforme al artículo 121 de la Ley del IVA. Si "
                         f"pasó de 8 millones de euros, te obliga desde el {grandes}; "
                         f"si no, desde el {resto}.",
                "fuentes": df4,
            },
            "particulares": {
                "texto": "El real decreto obliga cuando el destinatario de la "
                         "factura es otro empresario o profesional. De las "
                         "facturas a particulares no dice nada, y este guía "
                         "tampoco.",
                "fuentes": art3,
            },
            "administracion": {
                "texto": "Este cuestionario solo sabe del Real Decreto 238/2026, "
                         "que trata de las facturas entre empresarios y "
                         "profesionales. Las facturas a la Administración tienen "
                         "su propia norma, que no se ha leído para escribirlo.",
                "fuentes": art3,
            },
        },
        "aviso": _NO_CERTIFICA,
    }


# --- Trocear -----------------------------------------------------------------
#
# Lo único que la página tiene que hacer igual que esto. Es corto a propósito:
# cada regla de más es una regla que hay que escribir dos veces.

_RE_PIEZA = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

def _sin_acentos(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


# Palabras que no distinguen una pregunta de otra. Viajan en el fichero, para
# que la página use esta lista y no una suya.
# Se escriben con sus tildes y se guardan sin ellas, que es como se comparan.
VACIAS = frozenset(_sin_acentos("""
a al algo algún alguna ante aquí así aun con como cual cuales cuando de del
desde donde dos el ella ellas ellos en entre era es esa ese eso esta están este
esto estoy fue ha hace hacer han hay he hola la las le les lo los mas me mi mis
muy ni no o otra otro para pero por porque puedo puede que quien quiere
quiero se según ser si sin sobre son su sus también te tengo tiene tu tus un
una uno unas unos y ya yo decir dice significa sale salio saber necesito
gracias favor ayuda cuanto cuanta cuantos cuantas sirve sirven funciona
""").split())

# Nombres propios que la regla del plural estropearía: sin esto, «Facturae»
# se quedaba en «factura» y encajaba con todo el sitio.
PROPIAS = frozenset({"facturae"})

# Maneras distintas de decir lo mismo. Las dos columnas pasan por `_raiz`, así
# que aquí se escriben como se escriben.
_IGUALES_ESCRITAS = {
    "dias": "dia", "pais": "paises",
    "vat": "iva",
    "cif": "nif", "dni": "nif",
    "rechazan": "rechazo", "rechaza": "rechazo", "rechazada": "rechazo",
    "rechazado": "rechazo", "rechazar": "rechazo", "devuelven": "rechazo",
    "obligatorio": "obliga", "obligatoria": "obliga", "obligado": "obliga",
    "obligada": "obliga", "obligacion": "obliga", "obligaciones": "obliga",
    "obligan": "obliga", "obligar": "obliga",
    "firmar": "firma", "firmada": "firma", "firmado": "firma",
    "certificados": "certificado",
    "hacienda": "aeat", "tributaria": "aeat",
    "autonomos": "autonomo", "autonoma": "autonomo",
    "gratuito": "gratis", "gratuita": "gratis", "cuesta": "gratis",
    "precio": "gratis", "cobra": "gratis", "pagar": "gratis",
    "privacidad": "privado", "datos": "dato", "sube": "subir", "suben": "subir",
    "guarda": "guardar", "guardan": "guardar",
}


def _raiz(palabra: str) -> str:
    """Quita el plural y la `e` final: «bases» y «base» tienen que ser la misma."""
    if not palabra.isalpha() or palabra in PROPIAS:
        return palabra
    if len(palabra) > 4 and palabra.endswith("es"):
        palabra = palabra[:-2]
    elif len(palabra) > 4 and palabra.endswith("s"):
        palabra = palabra[:-1]
    if len(palabra) > 3 and palabra.endswith("e"):
        palabra = palabra[:-1]
    return palabra


IGUALES = {_raiz(a): _raiz(b) for a, b in _IGUALES_ESCRITAS.items()}


def trocear(texto: str) -> list[str]:
    """Las palabras que cuentan de un texto, en la forma en que se comparan.

    Un término con guiones y alguna cifra (`BT-10`, `BR-CO-10`) es una sola
    pieza, `bt10`: partido en `bt` y `10` encajaría con cualquier otro número.
    """
    piezas: list[str] = []
    for encaje in _RE_PIEZA.findall(_sin_acentos(texto)):
        if "-" in encaje and any(c.isdigit() for c in encaje):
            partes = [encaje.replace("-", "")]
        else:
            partes = encaje.split("-")
        for parte in partes:
            # Una letra suelta no dice nada: es la «e» de «Glosa-e».
            if parte in VACIAS or len(parte) < 2:
                continue
            raiz = _raiz(parte)
            piezas.append(IGUALES.get(raiz, raiz))
    return piezas


# --- Las fichas ----------------------------------------------------------------

_RE_ETIQUETA = re.compile(r"<[^>]+>")
_RE_BLANCOS = re.compile(r"\s+")
# Solo si detrás del signo se acaba la palabra: « .xsig» no se toca.
_RE_ANTES_DEL_SIGNO = re.compile(r" ([,;:.])(?= |$)")
_NEGRITA = re.compile(r"\*\*(.+?)\*\*", re.S)
_MONO = re.compile(r"`([^`]+)`")


def _llano(trozo: str) -> str:
    """El texto que se lee de un trozo de HTML, en una línea."""
    sin_scripts = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", trozo, flags=re.S | re.I)
    llano = _RE_BLANCOS.sub(" ", html.unescape(_RE_ETIQUETA.sub(" ", sin_scripts))).strip()
    # Quitar una etiqueta deja un hueco donde había un cierre pegado a una
    # coma: «no se mira</a>, porque» salía «no se mira , porque».
    return _RE_ANTES_DEL_SIGNO.sub(r"\1", llano)


def _sin_marcas(texto: str) -> str:
    return _NEGRITA.sub(r"\1", _MONO.sub(r"\1", texto))


def _principio(texto: str, tope: int = 320) -> str:
    """Las primeras frases enteras que quepan. Nunca se corta a media frase."""
    texto = _RE_BLANCOS.sub(" ", texto).strip()
    if len(texto) <= tope:
        return texto
    corte = texto.rfind(". ", 0, tope)
    if corte < 80:
        corte = texto.rfind(" ", 0, tope)
        return texto[:corte].rstrip(",;:") + "…"
    return texto[:corte + 1]


def _limpia(nombre: str, ancla: str = "") -> str:
    """La dirección de una página como la sirve el sitio: sin `.html`."""
    base = "./" if nombre == "index.html" else "./" + nombre.removesuffix(".html")
    return base + (f"#{ancla}" if ancla else "")


def _fichas_de_codigos(codigos: list[Codigo], nombre_de) -> list[dict]:
    fichas = []
    for uno in codigos:
        texto, _propia = explicar(uno.codigo, uno.familia)
        etiqueta, _detalle = normas.norma(uno.codigo)
        llano = _sin_marcas(texto)
        fichas.append({
            "id": uno.codigo,
            "tipo": "codigo",
            "titulo": uno.codigo,
            "pie": ", ".join(uno.gravedades) or "según el caso",
            "texto": _principio(llano) if llano else
                     "Todavía no tiene una explicación escrita. En su ficha está "
                     "con qué gravedad sale y de qué norma viene.",
            "url": _limpia(nombre_de(uno.codigo)),
            "enlace": "Leer la ficha entera",
            "_titulo": f"{uno.codigo} {etiqueta}",
            "_cuerpo": llano,
        })
    return fichas


def _fichas_de_familias(codigos: list[Codigo], catalogo: str) -> list[dict]:
    presentes = {c.familia for c in codigos}
    fichas = []
    for familia, texto in FAMILIAS.items():
        if familia not in presentes:
            continue
        llano = _sin_marcas(texto)
        fichas.append({
            "id": f"familia-{familia}",
            "tipo": "familia",
            "titulo": f"Los códigos que empiezan por {familia}",
            "pie": "familia de códigos",
            "texto": _principio(llano),
            "url": _limpia(catalogo, f"familia-{familia}"),
            "enlace": "Verlos en el catálogo",
            "_titulo": f"familia {familia} códigos {familia}",
            "_cuerpo": llano,
        })
    return fichas


_RE_PREGUNTA = re.compile(
    r'<details id="([^"]+)">\s*<summary>\s*<h3>(.*?)</h3>(.*?)</summary>'
    r'\s*<div class="r">(.*?)</div>\s*</details>', re.S)
_RE_CORTA = re.compile(r'<span class="corta[^"]*">(.*?)</span>', re.S)
_RE_PARRAFO = re.compile(r"<p\b[^>]*>(.*?)</p>", re.S)


def _fichas_de_preguntas(portada: str) -> list[dict]:
    """Las preguntas frecuentes de la portada, con su primer párrafo."""
    fichas = []
    for ancla, pregunta, resumen, respuesta in _RE_PREGUNTA.findall(portada):
        parrafos = [_llano(p) for p in _RE_PARRAFO.findall(respuesta)]
        corta = _RE_CORTA.search(resumen)
        primero = parrafos[0] if parrafos else _llano(respuesta)
        fichas.append({
            "id": f"pregunta-{ancla}",
            "tipo": "pregunta",
            "titulo": _llano(pregunta),
            "pie": "pregunta frecuente",
            "corta": _llano(corta.group(1)) if corta else "",
            "texto": _principio(primero, 420),
            "url": _limpia("index.html", ancla),
            "enlace": "Leer la respuesta entera",
            "_titulo": _llano(pregunta),
            "_cuerpo": _llano(respuesta),
        })
    return fichas


_RE_FILAS = re.compile(r'<ul class="filas">(.*?)</ul>', re.S)
_RE_NEGRITA_DE_FILA = re.compile(r"<li>\s*<b>(.*?)</b>", re.S)
_RE_PARRAFO_DE_TEXTO = re.compile(r"<p(?![^>]*class=)[^>]*>(.*?)</p>", re.S)


def _principio_de_un_apartado(cuerpo: str) -> str:
    """Con qué empieza un apartado: su primer párrafo, o los rótulos de su lista.

    Los apartados «Qué hace» y «Lo que no hace» son una lista de filas, cada
    una con su rótulo en negrita. De esos se dan los rótulos, que son suyos
    palabra por palabra, y no el primer párrafo que haya más abajo, que habla
    ya de otra cosa.
    """
    parrafo = _RE_PARRAFO_DE_TEXTO.search(cuerpo)
    filas = _RE_FILAS.search(cuerpo)
    if filas and (not parrafo or filas.start() < parrafo.start()):
        rotulos = [_llano(r) for r in _RE_NEGRITA_DE_FILA.findall(filas.group(1))]
        return ". ".join(rotulos) + "." if rotulos else ""
    return _principio(_llano(parrafo.group(1)), 420) if parrafo else ""


_RE_APARTADO = re.compile(
    r'<h2 id="([^"]+)">(.*?)</h2>(.*?)(?=<h2\b|</article>)', re.S)


def _fichas_de_apartados(nombre: str, texto: str, de_donde: str) -> list[dict]:
    """Los apartados con ancla de una página larga, cada uno con su principio."""
    fichas = []
    for ancla, titulo, cuerpo in _RE_APARTADO.findall(texto):
        primero = _principio_de_un_apartado(cuerpo)
        if not primero:
            continue
        fichas.append({
            "id": f"{nombre.removesuffix('.html')}-{ancla}",
            "tipo": "apartado",
            "titulo": _llano(titulo),
            "pie": de_donde,
            "texto": primero,
            "url": _limpia(nombre, ancla),
            "enlace": "Leer el apartado",
            "_titulo": _llano(titulo),
            "_cuerpo": _llano(cuerpo),
        })
    return fichas


_RE_TITULO = re.compile(r"<title>(.*?)</title>", re.S)
_RE_DESCRIPCION = re.compile(r'<meta name="description" content="([^"]*)">')


def _ficha_de_pagina(nombre: str, texto: str) -> dict | None:
    """Una página entera, por su título y la descripción que ella da de sí."""
    titulo = _RE_TITULO.search(texto)
    descripcion = _RE_DESCRIPCION.search(texto)
    if not titulo or not descripcion:
        return None
    limpio = _llano(titulo.group(1)).replace("· Glosa-e", "").strip(" ·")
    return {
        "id": f"pagina-{nombre.removesuffix('.html')}",
        "tipo": "pagina",
        "titulo": limpio,
        "pie": "página de Glosa-e",
        "texto": html.unescape(descripcion.group(1)),
        "url": _limpia(nombre),
        "enlace": "Abrir la página",
        "_titulo": limpio,
        "_cuerpo": html.unescape(descripcion.group(1)),
    }


def _fichas_del_blog(entradas) -> list[dict]:
    return [{
        "id": f"blog-{e.slug}",
        "tipo": "articulo",
        "titulo": e.titulo,
        "pie": f"blog, {cifras.fecha(e.fecha)}",
        "texto": e.entradilla,
        "url": _limpia(e.nombre),
        "enlace": "Leer el artículo",
        "_titulo": e.titulo,
        "_cuerpo": f"{e.entradilla} {_llano(e.cuerpo)}",
    } for e in entradas]


def _fichas_de_temas() -> list[dict]:
    fichas = []
    for tema in _temas():
        fuentes = tema.get("fuentes") or []
        if not fuentes or not all(
                url.startswith(_FUENTES_OFICIALES) for _rotulo, url in fuentes):
            raise GuiaMal(
                f"El tema «{tema['id']}» no lleva una fuente del BOE. Es lo "
                "único del guía que no sale de una página ya publicada, así "
                "que sin la cita no hay forma de comprobar lo que dice.")
        fichas.append({
            "id": tema["id"],
            "tipo": "tema",
            "titulo": tema["titulo"],
            "pie": f"leído en el BOE el {cifras.fecha(TEMAS_LEIDOS_EL)}",
            "texto": tema["texto"],
            "fuentes": [list(f) for f in fuentes],
            "aviso": _NO_CERTIFICA,
            "_titulo": f"{tema['titulo']} {tema['palabras']}",
            "_cuerpo": tema["texto"],
        })
    return fichas


# Palabras con las que la gente pregunta y que la página no usa. Se suman al
# título de la ficha para buscar, no a lo que se enseña: lo que se lee sigue
# siendo lo que dice la página.
PALABRAS_DE_MAS = {
    "pregunta-formatos": "formato tipo fichero xml xsig cual clase ubl cii "
                         "facturae edifact",
    "pregunta-sube": "privacidad datos seguro confidencial guardar",
    "pregunta-aeat": "oficial hacienda validez",
    "pregunta-cuesta": "servicio tarifa coste registro cuenta",
    "sobre-no-hace": "limite limites alcance verifactu glosa",
    "sobre-que-es": "glosa nombre",
    "sobre-que-hace": "glosa",
    # El contacto: desde el 21-11-2026 no hay apartado propio en Sobre, y el
    # correo está en la ficha del titular del aviso legal.
    "pagina-legal": "detras titular responsable autor cookies rgpd contacto "
                    "contactar escribir escribo correo email mail hablar "
                    "consulta duda telefono",
}


# --- El índice -------------------------------------------------------------------

# Cuánto más pesa una palabra en el título que en el cuerpo.
_PESO_DEL_TITULO = 4
# Lo mínimo para dar una respuesta. Por debajo, el guía dice que no lo sabe:
# una ficha que encaja por una sola palabra corriente no es una respuesta.
UMBRAL = 40
# Cuántas se ofrecen detrás de la primera, y lo cerca que tienen que quedar.
OTRAS = 3
_CERCA = 0.55


def _indice(fichas: list[dict]) -> dict[str, list[list[int]]]:
    """Palabra → [[ficha, peso], …], con el peso ya resuelto.

    El peso es mayor cuanto más rara es la palabra en el conjunto (lo corriente
    no distingue nada) y si está en el título. La página no calcula: suma.
    """
    en_cada: list[dict[str, int]] = []
    for ficha in fichas:
        suyas: dict[str, int] = {}
        for pieza in trocear(ficha["_cuerpo"]):
            suyas[pieza] = 1
        for pieza in trocear(ficha["_titulo"]):
            suyas[pieza] = _PESO_DEL_TITULO
        en_cada.append(suyas)
    en_cuantas: dict[str, int] = {}
    for suyas in en_cada:
        for pieza in suyas:
            en_cuantas[pieza] = en_cuantas.get(pieza, 0) + 1
    total = len(fichas)
    indice: dict[str, list[list[int]]] = {}
    for numero, suyas in enumerate(en_cada):
        for pieza, campo in suyas.items():
            rareza = math.log(1 + total / en_cuantas[pieza])
            indice.setdefault(pieza, []).append([numero, round(10 * rareza * campo)])
    return indice


def _codigos_nombrados(datos: dict, consulta: str) -> list[int]:
    """Las fichas de los códigos que la consulta nombra, en su orden."""
    vistos: list[int] = []
    mayusculas = _sin_acentos(consulta).upper()
    for encaje in re.findall(r"[A-Z0-9]+(?:-[A-Z0-9]+)*", mayusculas):
        numero = datos["codigos"].get(encaje)
        if numero is not None and numero not in vistos:
            vistos.append(numero)
    return vistos


def buscar(datos: dict, consulta: str) -> list[int]:
    """Las fichas que contestan a una consulta, la mejor primero.

    Es la referencia: `web/guia.js` hace lo mismo y las comprobaciones del
    fichero vigilan que lo siga haciendo. Vacía quiere decir «no lo sé».
    """
    nombrados = _codigos_nombrados(datos, consulta)
    if nombrados:
        return nombrados
    # Solo cuentan las palabras que el índice conoce: una que no está en
    # ninguna ficha no puede acercar ni alejar ninguna respuesta.
    piezas = [p for p in dict.fromkeys(trocear(consulta)) if p in datos["indice"]]
    if not piezas:
        return []
    puntos: dict[int, int] = {}
    aciertos: dict[int, int] = {}
    for pieza in piezas:
        for numero, peso in datos["indice"].get(pieza, ()):
            puntos[numero] = puntos.get(numero, 0) + peso
            aciertos[numero] = aciertos.get(numero, 0) + 1
    # Dos de cada tres, redondeando hacia arriba: con dos palabras, las dos.
    hacen_falta = (2 * len(piezas) + 2) // 3
    validas = [n for n in puntos
               if aciertos[n] >= hacen_falta and puntos[n] >= datos["umbral"]]
    if not validas:
        return []
    validas.sort(key=lambda n: (-puntos[n], n))
    mejor = puntos[validas[0]]
    return [n for n in validas[:1 + datos["otras"]]
            if puntos[n] * 100 >= mejor * datos["cerca"]]


# Preguntas con las que la página comprueba que trocea y suma igual que esto.
# Se escogen para tocar cada regla del troceo: acentos, plurales, términos con
# guion y cifra, un código en minúsculas, varias formas de decir lo mismo y
# una pregunta que no tiene respuesta.
_PREGUNTAS_DE_COMPROBACION = (
    "qué significa br-co-10",
    "BT-10",
    "me rechazan la factura por el IVA",
    "¿desde cuándo es obligatoria?",
    "¿esto certifica que mi factura es válida?",
    "las bases imponibles no cuadran",
    "certificado revocado",
    "¿por qué es gratis?",
    "plataformas privadas copia fiel",
    "cuatro días para informar de los estados",
    "Facturae 3.2.2",
    "¿sirve para VeriFactu?",
    "no sé qué formato es mi factura",
    "receta de paella valenciana",
    "",
)


def armar(pagina: Path, codigos: list[Codigo], entradas, nombre_de,
          catalogo: str, correo: str, hoy: _dt.date | None = None) -> dict:
    """Todo lo que la página necesita, en un diccionario listo para escribir."""
    pagina = Path(pagina)
    revisar_la_lectura(hoy)
    fichas = _fichas_de_temas()
    portada = pagina / "index.html"
    if portada.is_file():
        fichas += _fichas_de_preguntas(portada.read_text(encoding="utf-8"))
    sobre = pagina / "sobre.html"
    if sobre.is_file():
        fichas += _fichas_de_apartados(
            "sobre.html", sobre.read_text(encoding="utf-8"), "Sobre Glosa-e")
    for nombre in ("legal.html", "banco.html", "novedades.html", catalogo):
        ruta = pagina / nombre
        if ruta.is_file():
            una = _ficha_de_pagina(nombre, ruta.read_text(encoding="utf-8"))
            if una:
                fichas.append(una)
    fichas += _fichas_del_blog(entradas)
    fichas += _fichas_de_familias(codigos, catalogo)
    fichas += _fichas_de_codigos(codigos, nombre_de)

    repetidas = {f["id"] for f in fichas if sum(g["id"] == f["id"] for g in fichas) > 1}
    if repetidas:
        raise GuiaMal(
            "Dos fichas del guía se llaman igual, así que una taparía a la "
            f"otra: {', '.join(sorted(repetidas))}.")

    sin_ficha = sorted(set(PALABRAS_DE_MAS) - {f["id"] for f in fichas})
    if sin_ficha and portada.is_file() and sobre.is_file():
        raise GuiaMal(
            "`PALABRAS_DE_MAS` nombra fichas que ya no existen: "
            f"{', '.join(sin_ficha)}. Se habrá renombrado un apartado o una "
            "pregunta, y sus palabras se quedarían sin nadie que las oiga.")
    for ficha in fichas:
        ficha["_titulo"] += " " + PALABRAS_DE_MAS.get(ficha["id"], "")

    indice = _indice(fichas)
    datos = {
        "fichas": [{k: v for k, v in f.items() if not k.startswith("_")}
                   for f in fichas],
        "indice": indice,
        "codigos": {f["id"]: n for n, f in enumerate(fichas) if f["tipo"] == "codigo"},
        "vacias": sorted(VACIAS),
        "propias": sorted(PROPIAS),
        "iguales": dict(sorted(IGUALES.items())),
        "umbral": UMBRAL,
        "otras": OTRAS,
        "cerca": round(_CERCA * 100),
        "cuestionario": _cuestionario(),
        "correo": correo,
    }
    datos["comprobaciones"] = [
        [pregunta, [datos["fichas"][n]["id"] for n in buscar(datos, pregunta)]]
        for pregunta in _PREGUNTAS_DE_COMPROBACION
    ]
    return datos


def montar(pagina: Path, destino: Path, codigos: list[Codigo], entradas,
           nombre_de, catalogo: str, correo: str) -> tuple[str, int]:
    """Escribe `guia.json` y devuelve su huella y cuántas fichas lleva."""
    return escribir(armar(pagina, codigos, entradas, nombre_de, catalogo, correo),
                    destino)


def _en_json(datos: dict) -> str:
    return json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def escribir(datos: dict, destino: Path) -> tuple[str, int]:
    """Escribe lo ya armado. Aparte de `armar` porque el montaje arma antes de
    escribir el primer byte, que es cuando todavía puede negarse sin dejar
    una carpeta a medias."""
    texto = _en_json(datos)
    (Path(destino) / DATOS).write_text(texto, encoding="utf-8", newline="\n")
    huella = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8]
    return huella, len(datos["fichas"])


def revisar_los_subdominios(carpeta: Path, datos: dict | None = None) -> None:
    """Se niega si alguna página nombra un subdominio que no existe.

    Un enlace a una dirección que no contesta es un cartel roto, y este no se
    vería desde aquí: se vería fuera y ya publicado. Vale para `web/`, antes
    de montar, y para lo montado; `datos` es lo que el guía sabe cuando
    todavía no se ha escrito.
    """
    carpeta = Path(carpeta)
    textos = [(ruta.relative_to(carpeta).as_posix(), ruta.read_text(encoding="utf-8"))
              for ruta in sorted([*carpeta.rglob("*.html"), carpeta / DATOS, carpeta / CODIGO])
              if ruta.is_file()]
    if datos is not None:
        textos.append((DATOS, _en_json(datos)))
    culpables = []
    for nombre, texto in textos:
        nombrados = {s.lower() for s in _RE_SUBDOMINIO.findall(texto)}
        de_mas = sorted(nombrados - SUBDOMINIOS)
        if de_mas:
            culpables.append(f"{nombre} ({', '.join(de_mas)})")
    if culpables:
        raise GuiaMal(
            "Estas páginas nombran un subdominio de glosa-e.com que no está en "
            f"`guia.SUBDOMINIOS`: {'; '.join(culpables)}. Si el sitio existe "
            "ya, apúntalo allí; si no, el enlace no puede salir publicado.")
