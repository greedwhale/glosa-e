"""Lo que el anexo I pide a una factura de la solución pública, además de la norma.

A quién se aplica
-----------------
A las facturas UBL que declaran la solución pública en su `CustomizationID`:
el identificador que fija la orden en su fila BT-24 (`cius_es.ESPECIFICACION`,
letra a letra el que enseñó la AEAT en su ejemplo del 02-10-2026), o el CIUS
del borrador de abril (`urn:aeat.es:CIUS-ES-SPFE`). El de abril ya no vale, y
se le mide igual para poder decírselo: `SPFE-ESPECIFICACION` sale en ERROR. Lo
que nombre a la AEAT sin ser ninguno de los dos recibe un AVISO: no se le
mide, pero no se calla.

El anexo I dice qué tienen que llevar «como mínimo» las facturas que se
remiten a la AEAT, y lo dice **en UBL**: sus rutas son de UBL y de nada más.
Qué le corresponde a cada campo en Facturae, en CII o en EDIFACT no lo publica
nadie, y aplicarlo a otra sintaxis sería inventarse esa correspondencia. A un
documento de otra sintaxis que declare la solución pública se le avisa de que
no se ha comprobado, que es distinto de callar.

Esto dejó de ser una ausencia el **17-09-2026**. Preguntada por escrito si
pensaba publicar esa correspondencia, la AEAT contestó que no es suya: «cae en
la responsabilidad de las plataformas privadas, o en su caso, de la definición
por parte del Ministerio de Economía que regula la interconexión entre
plataformas privadas y sus formatos». Y remitió, para la semántica europea, a
las partes de CEN que sí existen —`16931-3-2` para UBL, `-3-3` para CII y
`-3-4` para EDIFACT—, que mapean la EN 16931 y **no** los campos españoles del
anexo. Para Facturae no hay ninguna.

Tampoco se aplica a una factura UBL que no lo declare. Quien emite para Peppol
o para una plataforma privada no se ha comprometido con la solución pública, y
exigírselo sería dar por mal una factura que no pretende ser eso. Quien lo
declara sí acepta sus listas —el tipo de factura sin el 381, la categoría de
IVA sin la K— y con ellas se le mide.

Con qué se mide
---------------
Con el anexo I de la Orden HAC/1028/2026, publicada en el BOE el 05-10-2026 y
en vigor desde el 06-10-2026, tal y como lo trae `cius_es`, que se genera del
XML del BOE.

Las reglas se escribieron contra el borrador de abril y se fueron poniendo al
día por partes: el 22-09-2026 con la respuesta del buzón sobre las
rectificativas, el 02-10-2026 con el ejemplo de la AEAT y el 07-10-2026 con
la orden, a mano y solo para dejar de condenar lo que la orden admite. Desde
el 11-10-2026 todo lo que se mide sale de la tabla del BOE, y dos reglas que
solo existían en el borrador —el recargo de equivalencia y el grupo de
entidades en sus propias líneas de cobro— ya no están. Qué cambió en cada paso
y por qué está en el README y en HALLAZGOS.md.

Lo que la orden pide y aquí todavía no se mide va en
`LO_QUE_TODAVIA_NO_SE_MIDE`, vacía desde el 11-10-2026, y la NOTA
`SPFE-ALCANCE` de cada factura lo dice, con lo que no se puede comprobar: que
no salga ninguna queja no quiere decir que la factura cumpla la orden.

Lo que la orden no dice y aquí se decide
----------------------------------------
- **La cuota de un cargo con más de un impuesto.** BT-ES-8 pide la misma
  cuota en el impuesto y en el total del cargo, que es uno por cargo: con dos
  impuestos no se puede. Se le preguntó al buzón el 07-10-2026 si va la suma,
  y hasta entonces no se compara: lo dice una NOTA.
- **El margen de las cuotas que la orden define como una cuenta**, las
  retenciones y los impuestos y tasas: el de la cuota del IVA (BR-CO-17).
- **La firma en la copia fiel**, en AVISO. La orden deja ir con la firma a
  las facturas interconectadas (artículo 3) y no lo dice de las copias fieles
  (artículo 4), y tampoco dice si la firma es uno de los ficheros integrados o
  embebidos que prohíbe a las dos.
- **La suma de retenciones sin ninguna retención detallada**, en NOTA. La
  orden deja el detalle en `0..n` y define la suma como el sumatorio de lo
  practicado: sin detalle no hay con qué compararla.

Lo que dijo el buzón y sigue valiendo
-------------------------------------
- **El `ProfileID` es el que no lleva `ubl:`** (13-10-2026),
  `urn:aeat:names:specification:schema:profile:B2B`, como en el ejemplo del
  02-10-2026 y como el resto de campos, aunque la orden publicada lo escriba
  con él. El del BOE sale en AVISO, porque es lo que dice el texto publicado.
- **Los valores de L7, L8 y L10 llevan el calificador de su lista delante**
  (13-10-2026), en las tres listas, como escribió la AEAT los de L10 en su
  ejemplo del 02-10-2026. Las filas dan solo el valor, y la lista el
  calificador aparte. Se siguen reconociendo los dos, para medir lo demás, y
  el valor solo sale en AVISO (`SPFE-CALIFICADOR`).
- **El prefijo ES del NIF-IVA es también para el comprador** (13-10-2026). La
  fila BT-48 lo pide y llama al comprador NIF del vendedor; la AEAT contestó
  que es una errata de la descripción y la corrige. Hasta ese día salía en
  AVISO; desde entonces, en ERROR, como el del vendedor.
- **La edición de la norma es la de 2026 para todo el sistema** (22-09-2026):
  `UNE-EN 16931-1:2026` y `UNE-CEN/TS 16931-3-2:2026` valen también para las
  copias fieles y para el intercambio privado del artículo 7.1.
- **Los documentos de validación no traerán esquematrón**, sino las reglas de
  negocio escritas, y en el entorno de pruebas habrá un servicio de validación
  de facturas UBL 2.5 sueltas (22-09-2026).
- **El 381 y la `K` siguen fuera** (23-09-2026), y la AEAT eleva la cuestión a
  gestión para que reevalúen el criterio. Una factura válida según la EN 16931
  —un abono 381, una entrega intracomunitaria con `K`— no pasa el anexo
  español.

De dónde sale cada comprobación
-------------------------------
De una fila del anexo, y lo que se puede sacar de la tabla se saca de ella al
importar, en vez de copiarse aquí:

- **Las rutas de los campos españoles**, de `sintaxis.RUTAS_CIUS_ES`. Las de
  dentro de un grupo se piden relativas al grupo, y si el anexo deja de
  colgarlas de ahí, este módulo no importa.
- **Lo que una fila impone en otra parte** —«VAT», «LOC» y «FC», «S» y
  «WTH»—, de `sintaxis.condiciones`, que lo lee de la columna de la ruta.
- **Los valores fijos** —«EUR», los de L7 y L10, «VERIFACTU»—, de la
  descripción de su fila. Si la frase ya no está, tampoco importa.
- **Las listas**, de `cius_es.LISTAS`, y cuál va con cada campo, de su tipo
  semántico («Código (L2.A)»).
- **Que lo que se exige sea obligatorio en el anexo.** Cada campo que aquí se
  pide tiene que tener allí cardinalidad `1..`; si un anexo nuevo lo relaja,
  el módulo no importa.

Es la negativa de siempre: un anexo nuevo que mueva algo no deja un validador
que comprueba lo de antes sin decir nada, deja uno que no se monta —y la suite
lo dice antes de publicar—.

Los campos que la EN 16931 ya tiene van por la vinculación UBL de 2017, la de
`SINTAXIS_UBL`, porque el anexo no les da ruta: remite a la de la edición de
2026, la UNE-CEN/TS 16931-3-2:2026, que aquí no se ha podido leer. Que esos
elementos existen en UBL 2.5 donde se buscan está comprobado contra el esquema
en las pruebas.

Lo que no se comprueba está en `NO_SE_COMPRUEBA`, con el porqué de cada cosa.
"""

from __future__ import annotations

import re
from datetime import date

from validador import cifras, cius_es, nif
from validador.codigo_unico import limpiar_nif
from validador.en16931 import _UNCL1001
from validador.formato import (
    MARCADOR_CIUS_ES,
    NOMBRA_A_LA_AEAT,
    NS_FIRMA,
    RESPUESTA,
    UBL,
    declara_la_solucion_publica,
)
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia, entre_comillas
from validador.listas_de_codigos import lista
from validador.modelo import grupos
from validador.sintaxis import (
    _ARREGLOS,
    NS_CIUS_ES,
    POR_ID,
    SIN_MAPA,
    SINTAXIS_UBL,
    a_decimal,
    a_menos_de_una_unidad,
    condiciones,
    cuadra_exacto,
    redondear,
)

__all__ = ["AnexoCambiado", "LO_QUE_TODAVIA_NO_SE_MIDE", "NO_SE_COMPRUEBA",
           "bt47_de_la_orden", "categorias_que_la_norma_no_tiene", "declara_el_cius",
           "reglas"]


class AnexoCambiado(LookupError):
    """Lo que este módulo lee del anexo ya no está donde estaba.

    Sale al importar, no al validar: un anexo regenerado que mueva una ruta o
    cambie un valor fijo no puede dejar reglas que miran lo de antes.
    """


# --- Lo que se lee del anexo al importar -------------------------------------

_COMILLAS = re.compile(r"[\"'«»“”‘’]")
_ENTRE_COMILLAS = re.compile(r"«([^»]+)»")
_LISTA_DEL_TIPO = re.compile(r"\((L\d+(?:\.[A-Z])?)\)")
_PREDICADO_FINAL = re.compile(r"\[[^\]]*\]$")


def _fila(identificador: str, termino: str = "") -> cius_es.Campo:
    filas = [c for c in cius_es.CAMPOS
             if c.id == identificador and termino in c.termino]
    if len(filas) != 1:
        raise AnexoCambiado(
            f"se buscaba una fila {identificador} «{termino}» y hay {len(filas)}")
    return filas[0]


def _obligatorio(identificador: str, termino: str = "") -> str:
    """El identificador, después de comprobar que el anexo lo hace obligatorio."""
    fila = _fila(identificador, termino)
    if not fila.obligatorio:
        raise AnexoCambiado(
            f"{identificador} «{fila.termino}» ya no es obligatorio en el anexo: "
            f"{fila.cardinalidad}")
    return identificador


def _cuantos(fila: cius_es.Campo, cardinalidad: str) -> int | None:
    """El máximo de una fila, después de comprobar que sigue siendo ese.

    Sin máximo («0..n»), nada: lo que se comprueba entonces es que se pueda
    repetir.
    """
    if fila.cardinalidad != cardinalidad:
        raise AnexoCambiado(
            f"{fila.id} «{fila.termino}» ya no es {cardinalidad} en el anexo: "
            f"{fila.cardinalidad}")
    maximo = cardinalidad.split("..")[1]
    return None if maximo == "n" else int(maximo)


def _dice(identificador: str, frase: str, termino: str = "") -> None:
    """Que la descripción de la fila siga diciendo esto, sin comillas ni saltos."""
    descripcion = " ".join(_COMILLAS.sub("", _fila(identificador, termino).descripcion).split())
    if frase not in descripcion:
        raise AnexoCambiado(f"la descripción de {identificador} ya no dice «{frase}»")


def _usar(fila: cius_es.Campo) -> tuple[str, ...]:
    """Los valores que la descripción manda usar: «usar «QR»», «… o «OTROS»»."""
    _, usar, resto = fila.descripcion.partition("usar ")
    valores = tuple(_ENTRE_COMILLAS.findall(resto)) if usar else ()
    if not valores:
        raise AnexoCambiado(f"la descripción de {fila.id} «{fila.termino}» ya no dice qué usar")
    return valores


def _valor_fijo(identificador: str, termino: str) -> str:
    """El valor que la fila manda adoptar: «Adoptará el valor fijo «INFO»».

    Entero, y no como un trozo de la frase: «valor fijo INFORMACION» contiene
    «valor fijo INFO», y hasta el 11-10-2026 las tres de BT-160 se comprobaban
    así. Un REGIX en la orden pasaba por REGI.
    """
    fila = _fila(identificador, termino)
    _, fijo, resto = fila.descripcion.partition("valor fijo")
    valores = _ENTRE_COMILLAS.findall(resto) if fijo else []
    if len(valores) != 1:
        raise AnexoCambiado(
            f"la descripción de {identificador} «{fila.termino}» ya no dice qué valor fijo adopta")
    return valores[0]


def _lista(fila: cius_es.Campo) -> str:
    """La lista de códigos de un campo, por su tipo semántico: «Código (L2.A)»."""
    encontrada = _LISTA_DEL_TIPO.search(fila.tipo)
    if not encontrada or encontrada.group(1) not in cius_es.LISTAS:
        raise AnexoCambiado(f"{fila.id} «{fila.termino}» ya no dice de qué lista es")
    return encontrada.group(1)


def _dentro(grupo: cius_es.Campo) -> list[cius_es.Campo]:
    """Las filas que cuelgan de un grupo del anexo: las que vienen detrás con más nivel."""
    desde = next(n for n, c in enumerate(cius_es.CAMPOS) if c is grupo) + 1
    filas = []
    for campo in cius_es.CAMPOS[desde:]:
        if campo.nivel <= grupo.nivel:
            break
        filas.append(campo)
    return filas


def _de(grupo: cius_es.Campo, identificador: str) -> cius_es.Campo:
    """La fila de un identificador dentro de un grupo, que tiene que ser una."""
    filas = [c for c in _dentro(grupo) if c.id == identificador]
    if len(filas) != 1:
        raise AnexoCambiado(
            f"en {grupo.id} «{grupo.termino}» se buscaba un {identificador} y hay {len(filas)}")
    return filas[0]


def _ruta(identificador: str, termino: str = "") -> str:
    rutas = [r.ruta for r in POR_ID.get(identificador, ()) if termino in r.termino]
    if len(rutas) != 1 or rutas[0] == SIN_MAPA:
        raise AnexoCambiado(f"{identificador} «{termino}» ya no trae una ruta en el anexo")
    return rutas[0]


def _condicion(identificador: str, final: str, termino: str = "") -> tuple[str, str]:
    """La ruta y el valor que la fila impone en un sitio que acaba así."""
    encontradas = [(ruta, valor) for ruta, valor in condiciones(_fila(identificador, termino))
                   if ruta.endswith("/" + final)]
    if len(encontradas) != 1:
        raise AnexoCambiado(
            f"{identificador} ya no impone un valor en «…/{final}»: {encontradas}")
    return encontradas[0]


def _relativa(ruta: str, grupo: str) -> str:
    """Una ruta del anexo contada desde su grupo."""
    if not ruta.startswith(grupo + "/"):
        raise AnexoCambiado(f"«{ruta}» ya no cuelga de «{grupo}» en el anexo")
    return "./" + ruta[len(grupo) + 1:]


def _padre(ruta: str, final: str) -> str:
    """Una ruta del anexo sin sus últimos pasos: el grupo que la contiene."""
    if not ruta.endswith("/" + final):
        raise AnexoCambiado(f"«{ruta}» ya no acaba en «{final}»")
    return ruta[: -len(final) - 1]


def _sin_predicado(ruta: str, debe_nombrar: str) -> str:
    """Una ruta sin el predicado que `sintaxis` le pone al final para distinguirla.

    Aquí el valor se mira aparte, con las dos lecturas del calificador, y el
    predicado tiene que nombrar el valor que se espera: si no, la ruta ya no es
    la que se creía.
    """
    predicado = _PREDICADO_FINAL.search(ruta)
    if not predicado or f"'{debe_nombrar}'" not in predicado.group(0):
        raise AnexoCambiado(f"«{ruta}» ya no se distingue por «{debe_nombrar}»")
    return ruta[: predicado.start()]


# El identificador de especificación y el proceso, de las filas BT-24 y BT-23.
ESPECIFICACION = cius_es.ESPECIFICACION
PROCESO_DE_LA_ORDEN = cius_es.PROCESO
_obligatorio("BT-23")
_obligatorio("BT-24")

# El proceso que vale no es el de la fila BT-23, y por eso va escrito a mano.
# La orden publicada lo escribe con ubl:, y el ejemplo que la AEAT mandó por
# correo el 02-10-2026, sin él. El buzón contestó dos veces el 13-10-2026 que
# el bueno es el del ejemplo, sin ubl:, como el resto de campos. No dijo que lo
# corrija en el anexo, y el anexo 2.0 que mandó ese mismo día todavía lo lleva
# con ubl: (medido). Si la fila deja de decir lo que dice el BOE, el módulo no
# se importa: o es la corrección, y el valor sale otra vez de la tabla, o es
# otra cosa, y hay que mirarla.
PROCESO = "urn:aeat:names:specification:schema:profile:B2B"
if PROCESO_DE_LA_ORDEN != "urn:aeat:names:specification:ubl:schema:profile:B2B":
    raise AnexoCambiado(
        f"la fila BT-23 ya no dice lo que el BOE del 05-10-2026: {PROCESO_DE_LA_ORDEN}")

# Los del borrador de abril. No salen de la tabla, y por eso van escritos a
# mano: el borrador no está en el BOE. Se reconocen para decir qué son en vez
# de tratarlos como cualquier otro valor equivocado.
ESPECIFICACION_DEL_BORRADOR = "urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0"
PROCESO_DEL_BORRADOR = "urn:aeat:names:specification:ubl:schema:B2B"
# El esquema de los calificadores de abril, con «ubl:», que la orden quitó. Un
# BG-24 escrito con él no es de la lista L10, y del QR se dice (ver `_qr`).
ESQUEMA_DEL_BORRADOR = "urn:aeat:names:specification:ubl:schema:"
if MARCADOR_CIUS_ES not in ESPECIFICACION_DEL_BORRADOR:
    raise AnexoCambiado("el borrador de abril ya no se reconoce por su CIUS")

_L = cius_es.LISTAS

# «Original o copia», que UBL deja opcional y la orden también: «False (o sin
# informar): original».
_COPIA = _ruta("BT-ES-1")
_cuantos(_fila("BT-ES-1"), "0..1")
_dice("BT-ES-1", "False (o sin informar): original")

# El tipo de factura, y cuáles son rectificativas.
_dice("BT-3", "Sólo podrán adoptarse los valores definidos en la lista L1")
_dice("BT-3", "Las facturas emitidas con valores 384 y 471 incorporarán el grupo de "
              "términos de negocio de tipo de factura rectificativa (BG-24), el grupo de "
              "términos de negocio de modalidad de factura rectificativa (BG-24)")
_RECTIFICATIVOS = ("384", "471")

# Los documentos justificativos adicionales (BG-24) de la lista L10: cada uno
# es un BG-24 del anexo, y lo que lo identifica es el valor de su BT-122.
_ESQUEMA_L10 = _L["L10"].calificador
_DOCUMENTOS: dict[str, cius_es.Campo] = {}
for _grupo in (c for c in cius_es.CAMPOS if c.id == "BG-24"):
    for _valor_l10 in _usar(_de(_grupo, "BT-122")):
        _DOCUMENTOS[_valor_l10] = _grupo
if set(_DOCUMENTOS) != set(_L["L10"].valores):
    raise AnexoCambiado("los BG-24 del anexo ya no son los documentos de la lista L10")
_ID_DEL_DOCUMENTO = SINTAXIS_UBL.adjunto_id
# BT-123, la descripción del documento: un término de la norma, sin ruta en el
# anexo, que la vinculación de 2017 pone en `cbc:DocumentDescription`.
_DESCRIPCION_DEL_DOCUMENTO = "./cbc:DocumentDescription"


def _en_el_documento(identificador: str) -> str:
    """La ruta de un campo español del BG-24, contada desde su documento."""
    ruta = _ruta(identificador)
    encontrada = re.fullmatch(r"\./cac:AdditionalDocumentReference\[[^\]]*\]/(.+)", ruta)
    if not encontrada:
        raise AnexoCambiado(f"{identificador} ya no cuelga de un documento justificativo")
    return "./" + encontrada.group(1)


# Los tres de la rectificativa: dónde va su código y con qué lista se compara.
# El nombre es el que sale en los mensajes.
_RECTIFICATIVA = {
    "RECT:TIPO": ("el tipo de rectificativa", "BT-ES-27"),
    "RECT:MODALIDAD": ("la modalidad de rectificación", "BT-ES-28"),
    "RECT:IMPORTES": ("los importes rectificados", "BT-ES-29"),
}
_CODIGO_DEL_DOCUMENTO: dict[str, str] = {}
_LISTA_DEL_DOCUMENTO: dict[str, str] = {}
_MAXIMO_DEL_DOCUMENTO: dict[str, int] = {}
for _valor_l10, (_nombre, _identificador) in _RECTIFICATIVA.items():
    _campo = _de(_DOCUMENTOS[_valor_l10], _obligatorio(_identificador))
    _CODIGO_DEL_DOCUMENTO[_valor_l10] = _en_el_documento(_identificador)
    _LISTA_DEL_DOCUMENTO[_valor_l10] = _lista(_campo)
_MAXIMO_DEL_DOCUMENTO["RECT:TIPO"] = _cuantos(_DOCUMENTOS["RECT:TIPO"], "0..1")
_MAXIMO_DEL_DOCUMENTO["RECT:MODALIDAD"] = _cuantos(_DOCUMENTOS["RECT:MODALIDAD"], "0..1")
_MAXIMO_DEL_DOCUMENTO["RECT:IMPORTES"] = _cuantos(_DOCUMENTOS["RECT:IMPORTES"], "0..5")
# La fila BT-3 dice "hasta tres grupos" de importes rectificados, y el grupo es
# `0..5`: la orden se contradice. Hasta el 11-10-2026 se callaba (lo midió el
# auditor), y hasta el 13-10-2026 cuatro o cinco salían en una NOTA. Ese día el
# buzón contestó que el grupo pasa a `0..1` en el anexo que publicará en su
# Portal de Desarrolladores, y mandó un ejemplo con tres, uno por código de
# L2.C: Base, Cuota y CuotaRecargo. Las tres cifras solo casan leídas así, uno
# por código, y los tres de BT-3 son los tres de la lista; si la lista cambia,
# el módulo no importa. Un código repetido sale en AVISO, y más de cinco sigue
# siendo ERROR, porque es lo que dice el BOE.
_dice("BT-3", "hasta tres grupos de términos de negocio de importes rectificados")
_IMPORTES_SEGUN_BT3 = 3
_CODIGOS_DE_IMPORTE = tuple(_L["L2.C"].valores)
if len(_CODIGOS_DE_IMPORTE) != _IMPORTES_SEGUN_BT3:
    raise AnexoCambiado("la lista L2.C ya no son los tres importes de BT-3")
# Y el grupo es para la sustitución, con una única factura.
_dice("BG-24", "en los casos en los que se proceda a la rectificación por sustitución",
      "IMPORTES RECTIFICADOS")
# El importe rectificado va en la descripción del documento (BT-123), que en
# este grupo, y solo en este, es obligatoria.
if not _de(_DOCUMENTOS["RECT:IMPORTES"], "BT-123").obligatorio:
    raise AnexoCambiado("el importe rectificado (BT-123) ya no es obligatorio")
# Los dos de L10 que no son de la rectificativa, y que no dicen qué se rectifica.
_AJENOS_A_LA_RECTIFICATIVA = {
    "QR": "el QR fiscal",
    "AUT": "la autorización de facturación",
}
if set(_RECTIFICATIVA) | set(_AJENOS_A_LA_RECTIFICATIVA) != set(_L["L10"].valores):
    raise AnexoCambiado("la lista L10 ya no tiene los cinco documentos de siempre")

# El QR fiscal: uno como mucho, con su dirección, y si lleva descripción, la
# de su fila.
_MAXIMO_DE_QR = _cuantos(_DOCUMENTOS["QR"], "0..1")
_QR_URL = _en_el_documento(_obligatorio("BT-ES-25"))
_TIPOS_DE_QR = _usar(_de(_DOCUMENTOS["QR"], "BT-123"))
_cuantos(_de(_DOCUMENTOS["QR"], "BT-123"), "0..1")

# La autorización de facturación: tantas como haga falta, y en cada una el
# número de la autorización, en el mismo cbc:UUID que la dirección del QR.
_cuantos(_DOCUMENTOS["AUT"], "0..n")
_NUMERO_DE_AUTORIZACION = _en_el_documento(_obligatorio("BT-ES-26"))
_dice("BT-ES-26", "Número de referencia de la autorización concedida")

# Los ficheros embebidos. No los prohíbe el anexo sino el articulado de la
# orden: las facturas emitidas o interconectadas «no podrán incorporar otros
# ficheros integrados o embebidos» (apartado 6 del artículo 3), salvo la
# firma en las interconectadas, y las copias fieles tampoco, sin salvedad
# (apartado 4 del artículo 4). Esos dos textos no están en `cius_es`, que es
# el anexo, y no hay fila que leer al importar. En UBL un fichero va dentro de
# la factura en un `cac:Attachment`, en base64 o en texto; la firma, en
# `cac:Signature` o envuelta en `ds:Signature`.
_EMBEBIDOS = ".//cbc:EmbeddedDocumentBinaryObject | .//cbc:EmbeddedDocument"
_DENTRO_DE_LA_FIRMA = "ancestor::cac:Signature"
_FIRMAS_ENVUELTAS = ".//ds:Signature"
_NS_CON_LA_FIRMA = dict(NS_CIUS_ES, ds=NS_FIRMA)

# La moneda del IVA: «Valor obligatorio: usar «EUR»».
_dice("BT-6", "usar EUR")
_dice("BT-6", "se consignará obligatoriamente como moneda de contabilización del IVA el euro")

# El importe pagado: ya no tiene que ser cero, pero no vale para un anticipo
# que devengó el IVA.
_dice("BT-113", "no debe ser utilizado en el caso de pagos anticipados que hayan "
                "supuesto el devengo del IVA")

# La fecha efectiva de pago (BT-ES-2): una como mucho, no después de la
# expedición y no antes de la operación. La fecha de la operación es BT-7, que
# la orden pide solo «siempre que sea diferente a la fecha de expedición»: sin
# él, la operación es del día de la expedición.
_FECHA_DE_PAGO = _ruta("BT-ES-2")
_cuantos(_fila("BT-ES-2"), "0..1")
_dice("BT-ES-2", "pagada con anterioridad a la fecha de expedición de la factura o en dicha fecha")
_dice("BT-ES-2", "deberá ser necesariamente coincidente o posterior a la fecha de "
                 "realización de las operaciones")
_dice("BT-7", "siempre que sea diferente a la fecha de expedición")

# El NIF de cada parte: con el impuesto «VAT» (BT-31, BT-48) o con «LOC» y el
# atributo «FC» en el propio NIF (BT-32, BT-47). Uno de los dos.
_dice("BT-31", "Será obligatorio consignar un NIF-IVA válido en el caso de que el campo BT-32 no tenga contenido")
_dice("BT-32", "Será obligatorio consignar un NIF válido en el caso de que el campo BT-31 no tenga contenido")
_dice("BT-48", "Será obligatorio consignar un NIF-IVA válido en el caso de que el campo BT-47 no tenga contenido")
_dice("BT-47", "Será obligatorio consignar un NIF válido en el caso de que el campo BT-48 no tenga contenido")
_IMPUESTO_DEL_ESQUEMA = "./cac:TaxScheme/cbc:ID"
_ATRIBUTO_DEL_NIF = "./cbc:CompanyID/@schemeID"
_ruta_vat, _IMPUESTO = _condicion("BT-31", "cac:TaxScheme/cbc:ID")
_ESQUEMAS_DEL_VENDEDOR = _padre(_ruta_vat, "cac:TaxScheme/cbc:ID")
_, _IMPUESTO_LOCAL = _condicion("BT-32", "cac:TaxScheme/cbc:ID")
_ruta_fc, _ESQUEMA_DEL_NIF = _condicion("BT-32", "cbc:CompanyID/@schemeID")
if _padre(_ruta_fc, "cbc:CompanyID/@schemeID") != _ESQUEMAS_DEL_VENDEDOR:
    raise AnexoCambiado("el atributo «FC» del vendedor ya no va en su mismo PartyTaxScheme")
_ruta_vat, _impuesto = _condicion("BT-48", "cac:TaxScheme/cbc:ID")
_ESQUEMAS_DEL_COMPRADOR = _padre(_ruta_vat, "cac:TaxScheme/cbc:ID")
if (_impuesto, _condicion("BT-47", "cac:TaxScheme/cbc:ID")[1],
        _condicion("BT-47", "cbc:CompanyID/@schemeID")[1]) != (
        _IMPUESTO, _IMPUESTO_LOCAL, _ESQUEMA_DEL_NIF):
    raise AnexoCambiado("el NIF del comprador ya no se escribe como el del vendedor")

# El registro legal del vendedor (BT-30), obligatorio cuando su NIF va en
# BT-32. La fila no trae ruta, y se lee donde la pone la vinculación de 2017,
# como los demás términos de la norma: si un anexo nuevo le da una, este
# módulo no importa hasta que se mire. Y lo describe como el NIF del vendedor,
# que es de donde sale mirar su contenido como un NIF: si deja de decirlo, la
# norma admite ahí el de cualquier registro oficial, y hay que volver a decidir.
_dice("BT-30", "Será obligatorio en los casos en los que venga informado el campo BT-32")
_dice("BT-30", "Número de identificación fiscal (NIF) del vendedor")
if _fila("BT-30").ruta:
    raise AnexoCambiado("BT-30 trae ruta en el anexo, y aquí se lee la de 2017")

# El prefijo de España en el NIF-IVA de las dos partes (BT-31 y BT-48), según
# los códigos ISO 3166-1, que para España es ES. La fila del comprador copia la
# del vendedor hasta en decir "del vendedor"; se le señaló al buzón como errata
# el 07-10-2026, y hasta su respuesta lo del comprador salía en AVISO. El
# 13-10-2026 contestó que corrige la descripción, y su anexo 2.0 dice "del
# comprador, con el prefijo correspondiente a España": desde ese día es ERROR,
# como el del vendedor. Si el BOE corrige la fila, este módulo no importa
# hasta que se mire otra vez.
_PREFIJO_DE_ESPANA = "ES"
for _identificador in ("BT-31", "BT-48"):
    _dice(_identificador, "con el prefijo correspondiente a España, según los códigos ISO 3166-1")
_dice("BT-48", "Número de identificación fiscal a efectos de IVA del vendedor")

# Las direcciones: la calle siempre, y ciudad, código postal y provincia
# «cuando la dirección postal esté en España».
_obligatorio("BT-35")
_obligatorio("BT-50")
for _identificador, _quien in (("BT-37", "vendedor"), ("BT-38", "vendedor"), ("BT-39", "vendedor"),
                               ("BT-52", "comprador"), ("BT-53", "comprador"), ("BT-54", "comprador")):
    _dice(_identificador, f"obligatorio cuando la dirección postal del {_quien} esté en España")

# El tipo de impuesto, «VAT», en los descuentos y cargos del documento (BT-95
# y BT-102, que lo ponen en la misma ruta), en las líneas (BG-30) y en el
# desglose (BG-23). La orden no lo dice en una fila propia, como el borrador:
# lo dice en la columna de la ruta de esas cuatro.
_IMPUESTO_EN: list[tuple[str, str]] = []
for _identificador, _lugar in (("BT-95", "descuentos y cargos del documento"),
                               ("BT-102", "descuentos y cargos del documento"),
                               ("BG-30", "líneas"),
                               ("BG-23", "desglose del IVA")):
    _ruta_vat, _impuesto = _condicion(_identificador, "cac:TaxScheme/cbc:ID")
    if _impuesto != _IMPUESTO:
        raise AnexoCambiado(f"{_identificador} ya no pide el impuesto «{_IMPUESTO}»")
    if (_ruta_vat, _lugar) not in _IMPUESTO_EN:
        _IMPUESTO_EN.append((_ruta_vat, _lugar))
# Y tiene que estar: «su uso implica» que la ruta tome el valor, y sin el
# elemento no lo toma. Se mira desde la categoría de cada sitio, que la norma
# pide siempre, para ver también la que no lo lleva. Hasta el 11-10-2026 se
# miraba solo el valor escrito, y una factura sin un solo «VAT» pasaba sin una
# queja: lo destapó quitar, uno a uno, cada elemento de las facturas buenas.
_ESQUEMA_DE_LA_CATEGORIA = "cac:TaxScheme/cbc:ID"
_CATEGORIAS_CON_IMPUESTO = [(_padre(_ruta_vat, _ESQUEMA_DE_LA_CATEGORIA), _lugar)
                            for _ruta_vat, _lugar in _IMPUESTO_EN]

# El tercero que expide la factura en lugar del vendedor.
_TERCERO = _ruta("BG-ES-1")
_TERCERO_NOMBRE = _relativa(_ruta(_obligatorio("BT-ES-3")), _TERCERO)
_TERCERO_NIF = _relativa(_ruta(_obligatorio("BT-ES-4")), _TERCERO)
_TERCERO_TIPO = _relativa(_ruta(_obligatorio("BT-ES-5")), _TERCERO)
# Donde la orden escribe la tipología, que en UBL no existe y se lee donde sí
# (`sintaxis._ARREGLOS`). Quien la escribe ahí la ha escrito: la queja lo dice,
# en vez de decir que falta. Hasta el 11-10-2026 decía «le falta la tipología»
# junto a XSD-ORDEN, que ya decía que estaba donde no podía. Lo vio el auditor.
_TERCERO_TIPO_DE_LA_ORDEN = "./cac:Party/" + _TERCERO_TIPO.removeprefix("./")
if not any(arreglo.mal.endswith("cac:ServiceProviderParty/cac:Party/cbc:ServiceTypeCode")
           and arreglo.bien.endswith("cac:ServiceProviderParty/cbc:ServiceTypeCode")
           for arreglo in _ARREGLOS):
    raise AnexoCambiado("la tipología del tercero ya no se lee arreglando la ruta de la orden")
_TERCERO_ESQUEMAS = _padre(_TERCERO_NIF, "cbc:CompanyID")
_TERCERO_IMPUESTO = _TERCERO_ESQUEMAS + "/cac:TaxScheme/cbc:ID"
if {valor for _, valor in condiciones(_fila("BT-ES-4"))} != {
        _IMPUESTO, _IMPUESTO_LOCAL, _ESQUEMA_DEL_NIF}:
    raise AnexoCambiado("el NIF del tercero ya no se escribe como el del vendedor")

# La factura referenciada, con fecha.
_obligatorio("BT-26")

# El motivo en texto de descuentos y cargos.
_MOTIVOS = (
    ("descuentos_documento", _obligatorio("BT-97")),
    ("cargos_documento", _obligatorio("BT-104")),
    ("descuentos_linea", _obligatorio("BT-139")),
    ("cargos_linea", _obligatorio("BT-144")),
)

# La categoría de IVA, lista L4. Trae tres categorías que la lista de la
# edición de 2017 de la norma no tiene: la N («Regímenes nacionales de IVA»:
# el grupo de entidades de nivel avanzado y el recargo de equivalencia), la D
# (agencias de viajes) y la F (bienes usados, arte, antigüedades y colección).
# Lo que no tiene la norma se saca restando, no se escribe.
for _identificador in ("BT-95", "BT-102", "BT-151", "BT-118"):
    _dice(_identificador, "incluidos en la lista L4")
_CATEGORIAS = frozenset(_L["L4"].valores)
_L4_QUE_LA_NORMA_NO_TIENE = _CATEGORIAS - lista("UNCL_5305", SINTAXIS_UBL)
_CATEGORIAS_EN = (
    ("desglose", "desglose_categoria"),
    ("descuentos_documento", "cargo_categoria"),
    ("cargos_documento", "cargo_categoria"),
    ("lineas", "linea_categoria"),
)

# El tipo de cada entrada del desglose (BT-119): la norma lo pide en todas menos
# en la no sujeta (BR-48), y la orden, en todas.
_obligatorio("BT-119")
_NO_SUJETA = "O"
if _NO_SUJETA not in _CATEGORIAS:
    raise AnexoCambiado("la L4 de la orden ya no tiene la categoría no sujeta")

# Los códigos de exención (BT-121): «Solo podrán adoptar valores VATEX-EU o
# VATEX-ES». La lista es la CEF-VATEX, y en la versión que lleva Glosa no hay
# ningún VATEX-ES: uno que no esté en ella lo dice BR-CL-22.
_dice("BT-121", "Lista CEF-VATEX. Solo podrán adoptar valores VATEX-EU o VATEX-ES")
_EXENCIONES = ("VATEX-EU-", "VATEX-ES-")

# La clave de régimen de cada línea: una propiedad del artículo llamada
# «REGI», una o dos por línea, con el impuesto en el calificador.
_LINEAS = "./cac:InvoiceLine"
for _termino, _nombre in (("Régimen", "REGI"), ("Referencia catastral", "RCAT")):
    if _valor_fijo("BT-160", _termino) != _nombre:
        raise AnexoCambiado(f"BT-160 «{_termino}» ya no adopta «{_nombre}»")
_cuantos(_fila("BG-32", "CLAVE DE RÉGIMEN"), "1..2")
_cuantos(_fila("BG-32", "REFERENCIA CATASTRAL"), "0..1")
_CLAVE = _relativa(_padre(_ruta(_obligatorio("BT-ES-24")), "cbc:ValueQualifier"), _LINEAS)
_CATASTRO = _relativa(_padre(_ruta(_obligatorio("BT-ES-23")), "cbc:ValueQualifier"), _LINEAS)
_CALIFICADOR = "./cbc:ValueQualifier"
# Las propiedades se buscan por su nombre con `_propiedades`, con el
# calificador de L8 delante o sin él.
_PROPIEDADES = _sin_predicado(_CLAVE, "REGI")
if _sin_predicado(_CATASTRO, "RCAT") != _PROPIEDADES:
    raise AnexoCambiado("la referencia catastral y la clave de régimen ya no son "
                        "propiedades del mismo sitio")
_CALIFICADOR_L8 = _L["L8"].calificador
_obligatorio("BT-161", "Código de clave de régimen")
_obligatorio("BT-161", "Referencia catastral")
_REGIMENES = {_L[clave].calificador: clave for clave in ("L3A", "L3B", "L3C")}
if len(_REGIMENES) != 3 or "" in _REGIMENES:
    raise AnexoCambiado("las listas de claves de régimen ya no dicen de qué impuesto son")
if _lista(_fila("BT-ES-23")) != "L6":
    raise AnexoCambiado("la situación del inmueble ya no es de la lista L6")

# La información adicional de la línea: otra propiedad del artículo, con el
# nombre fijo «INFO» y el texto en el valor. Con la clave de régimen y la
# referencia catastral son las tres de L8, y no hay más: la norma deja el
# nombre libre, y la orden no.
if _valor_fijo("BT-160", "Información adicional") != "INFO":
    raise AnexoCambiado("BT-160 «Información adicional» ya no adopta «INFO»")
_cuantos(_fila("BG-32", "INFORMACIÓN ADICIONAL"), "0..n")
_obligatorio("BT-161", "Información adicional")
_NOMBRES_L8 = tuple(_L["L8"].valores)
if set(_NOMBRES_L8) != {"INFO", "RCAT", "REGI"}:
    raise AnexoCambiado("la lista L8 ya no son las tres propiedades de la línea de BT-160")

# Las líneas de cobro: cuatro grupos (BG-34), cada uno con su valor de L7 en
# la fila que lo identifica. Los que el anexo admite una vez por factura salen
# de su cardinalidad.
_LINEA_DE_COBRO = _sin_predicado(_padre(_ruta("BT-ES-16"), "cbc:ID"), "RETE")
_CALIFICADOR_L7 = _L["L7"].calificador
_L7 = tuple(_L["L7"].valores)
_UNO_POR_FACTURA: dict[str, str] = {}
_valores_de_cobro: set[str] = set()
for _grupo in (c for c in cius_es.CAMPOS if c.id == "BG-34"):
    _identifica = [c for c in _dentro(_grupo) if c.espanol and c.tipo == "Código (L7)"]
    if len(_identifica) != 1:
        raise AnexoCambiado(f"el grupo «{_grupo.termino}» ya no se identifica con un valor de L7")
    _valores = _usar(_identifica[0])
    _valores_de_cobro |= set(_valores)
    if _grupo.cardinalidad == "0..1":
        _UNO_POR_FACTURA.update({v: _grupo.termino for v in _valores})
if _valores_de_cobro != set(_L7):
    raise AnexoCambiado("los grupos de líneas de cobro ya no son los de la lista L7")

# Las retenciones.
_RETENCION_TOTAL = _ruta(_obligatorio("BT-ES-17"))
_RETENCIONES = _padre(_RETENCION_TOTAL, "cbc:TaxAmount")
_RETENCIONES_APLICADAS = _RETENCIONES + "/cac:TaxSubtotal"
_dice("BT-ES-21", "tabla L5")
# Las dos cuentas de las retenciones son definiciones de la orden, y aquí se
# hacen: si una orden nueva las escribe de otra forma, el módulo no importa.
_dice("BT-ES-17", "Sumatorio de todas las retenciones practicadas")
_dice("BT-ES-19", "Resultado de aplicar a la Base imponible de la retención, el porcentaje")
_RETENCION_HIJOS = {
    identificador: _relativa(_ruta(_obligatorio(identificador)), _RETENCIONES_APLICADAS)
    for identificador in ("BT-ES-18", "BT-ES-19", "BT-ES-20", "BT-ES-21")
}
# Cada retención aplicada es `0..n`: la suma puede llegar sin ninguna, y
# entonces no hay con qué compararla (ver `_cuadre_de_las_retenciones`).
_cuantos(_fila("BG-ES-4"), "0..n")
_ruta_s, _CATEGORIA_DE_LA_RETENCION = _condicion("BG-ES-4", "cac:TaxCategory/cbc:ID")
_ruta_wth, _ESQUEMA_DE_LA_RETENCION = _condicion("BG-ES-4", "cac:TaxScheme/cbc:ID")
_RETENCION_CATEGORIA = _relativa(_ruta_s, _RETENCIONES_APLICADAS)
_RETENCION_ESQUEMA = _relativa(_ruta_wth, _RETENCIONES_APLICADAS)

# Los impuestos y tasas que no son el IVA, cada uno con su código de la lista
# L9: en cada cargo de línea (BT-ES-22, obligatorio en todos, y «RESTO» es el
# de un cargo que no es un impuesto), en el detalle de un cargo del documento
# (BG-ES-2) y en el desglose de una línea de cobro de impuestos y tasas
# (BG-ES-3), que se escribe con «VAT» y «S» aunque no sea el IVA. La L9 no
# trae calificador: el código va solo.
_L9 = tuple(_L["L9"].valores)
if _L["L9"].calificador:
    raise AnexoCambiado("la lista L9 trae calificador, y aquí se compara el código solo")
for _identificador in ("BT-ES-9", "BT-ES-22"):
    if _lista(_fila(_identificador)) != "L9":
        raise AnexoCambiado(f"{_identificador} ya no es de la lista L9")
_CODIGO_L9 = "cac:TaxCategory/cac:TaxScheme/cbc:TaxTypeCode"
_CODIGO_DEL_CARGO_DE_LINEA = _relativa(
    _ruta(_obligatorio("BT-ES-22")), _LINEAS + "/cac:AllowanceCharge[cbc:ChargeIndicator='true']")

_CARGOS_DEL_DOCUMENTO = "./cac:AllowanceCharge[cbc:ChargeIndicator='true']"
_cuantos(_fila("BG-ES-2"), "0..n")
_impuestos_del_cargo = _padre(_ruta(_obligatorio("BT-ES-9")), _CODIGO_L9)
_IMPUESTOS_DEL_CARGO = _relativa(_impuestos_del_cargo, _CARGOS_DEL_DOCUMENTO)
_DEL_IMPUESTO_DEL_CARGO = {identificador: _relativa(_ruta(identificador), _impuestos_del_cargo)
                           for identificador in ("BT-ES-6", "BT-ES-7", "BT-ES-9")}
# La cuota (BT-ES-8) va en dos sitios: «El mismo importe debe consignarse en
# dos rutas distintas», la del impuesto y la del total del cargo.
_obligatorio("BT-ES-8")
_dice("BT-ES-8", "Resultado de aplicar a la base del impuesto o tasa el tipo correspondiente")
if "El mismo importe debe consignarse en dos rutas distintas" not in " ".join(
        _fila("BT-ES-8").ruta.split()):
    raise AnexoCambiado("BT-ES-8 ya no pide el mismo importe en dos rutas")
_cuotas_del_cargo = [r.ruta for r in POR_ID.get("BT-ES-8", ())]
_en_el_impuesto = [r for r in _cuotas_del_cargo if r.startswith(_impuestos_del_cargo + "/")]
_en_el_total = [r for r in _cuotas_del_cargo if r not in _en_el_impuesto]
if len(_en_el_impuesto) != 1 or len(_en_el_total) != 1:
    raise AnexoCambiado("BT-ES-8 ya no trae una ruta en el impuesto y otra en el total del cargo")
_CUOTA_DEL_IMPUESTO_DEL_CARGO = _relativa(_en_el_impuesto[0], _impuestos_del_cargo)
_CUOTA_DEL_CARGO = _relativa(_en_el_total[0], _CARGOS_DEL_DOCUMENTO)

_cuantos(_fila("BG-ES-3"), "0..n")
_impuestos_del_cobro = _padre(_ruta(_obligatorio("BT-ES-14")), "cbc:TaxAmount")
_IMPUESTOS_DEL_COBRO = _relativa(_impuestos_del_cobro, _LINEA_DE_COBRO)
_DEL_IMPUESTO_DEL_COBRO = {identificador: _relativa(_ruta(identificador), _impuestos_del_cobro)
                           for identificador in ("BT-ES-12", "BT-ES-13", "BT-ES-14")}
_dice("BT-ES-14", "Cuota resultante de aplicar a la base del impuesto o tasa el tipo correspondiente")
_ruta_del_esquema, _ESQUEMA_DEL_COBRO = _condicion("BG-ES-3", "cac:TaxScheme/cbc:ID")
_ruta_de_la_categoria, _CATEGORIA_DEL_COBRO = _condicion("BG-ES-3", "cac:TaxCategory/cbc:ID")
_ESQUEMA_DEL_IMPUESTO_DEL_COBRO = _relativa(_ruta_del_esquema, _impuestos_del_cobro)
_CATEGORIA_DEL_IMPUESTO_DEL_COBRO = _relativa(_ruta_de_la_categoria, _impuestos_del_cobro)

# El total a pagar, que suma los importes de terceros.
_dice("BT-115", "junto con los importes correspondientes a los conceptos BT-179")


def _calificador(identificador: str) -> str:
    """El valor de L10 de un BG-24, o «» si no lo lleva.

    El valor solo o con el calificador de L10 delante, y enteros: ni un
    `MIRECT:TIPO` de cualquiera ni un esquema parecido de otro cuelan por el
    final. El esquema del borrador de abril, con `ubl:`, ya no vale.
    """
    resto = identificador.removeprefix(_ESQUEMA_L10)
    return resto if resto in _DOCUMENTOS else ""


def _cobro(identificador: str) -> str:
    """El valor de L7 de una línea de cobro, o «» si no se reconoce.

    Con su calificador delante o solo, y entero: un `XRETE` no es `RETE`, y un
    REEQ o un REGE, las líneas del borrador de abril, tampoco, porque la orden
    no los tiene.
    """
    resto = identificador.removeprefix(_CALIFICADOR_L7)
    return resto if resto in _L7 else ""


def _cobros(raiz, valor: str) -> list:
    """Las líneas de cobro de la factura que se identifican con ese valor de L7."""
    return [linea for linea in _nodos(raiz, _LINEA_DE_COBRO)
            if _cobro(_valor(linea, "./cbc:ID")) == valor]


def _propiedades(linea, nombre: str) -> list:
    """Las propiedades del artículo de una línea con ese nombre de L8.

    Con el calificador de L8 delante o sin él, y enteras: un `XREGI` no es
    `REGI`.
    """
    return [propiedad for propiedad in _nodos(linea, _PROPIEDADES)
            if _valor(propiedad, "./cbc:Name").removeprefix(_CALIFICADOR_L8) == nombre]


def _adjuntos(raiz) -> list[tuple[str, object]]:
    """Cada BG-24 de la factura con su valor de L10, o «» si no lo lleva."""
    return [(_calificador(_valor(adjunto, _ID_DEL_DOCUMENTO)), adjunto)
            for adjunto in _nodos(raiz, SINTAXIS_UBL.adjuntos)]


# Lo que la orden pide y aquí todavía no se mide, una cosa por frase. Lo dice
# la nota SPFE-ALCANCE de cada factura, y el glosario lo copia letra a letra:
# la lista estuvo escrita dos veces hasta el 07-10-2026, y ya no decía lo
# mismo. Cada frase nombra la fila o la lista de la orden de la que sale, y
# hay prueba de que existe en la tabla. Desde el 11-10-2026 no queda nada: lo
# último fue el número de la autorización (BT-ES-26), y antes de vaciarla se
# quitó cada elemento de las facturas buenas, uno a uno, para ver qué pasaba
# en silencio. La tupla se queda, vacía, para lo que traiga una orden nueva, y
# la nota deja de nombrarla.
LO_QUE_TODAVIA_NO_SE_MIDE: tuple[str, ...] = ()


# Lo que el anexo pide y aquí no se mira porque no se puede, con el porqué. Se
# dice porque un informe sin quejas sobre esto podría leerse como que se ha
# comprobado.
NO_SE_COMPRUEBA: dict[str, str] = {
    "BT-179 y BT-180": (
        "El importe y la descripción de los grupos de cobros: los cargos en "
        "nombre de un tercero, los impuestos y tasas, las minoraciones y las "
        "retenciones. La orden no les da ruta: son términos de la edición de "
        "2026 de la norma, y su vinculación UBL, la UNE-CEN/TS 16931-3-2:2026, "
        "no se ha podido leer aquí."
    ),
    "BT-115": (
        "El total a pagar suma los importes de BT-179, que no tienen ruta. Si "
        "las únicas líneas de cobro son retenciones, se cuadra restando su "
        "suma (BT-ES-17); con suplidos, minoraciones o impuestos y tasas, el "
        "cuadre del total a pagar (BR-CO-16) no se comprueba, y "
        "SPFE-TOTAL-A-PAGAR lo dice en el informe."
    ),
    "BT-111": (
        "Con recargo de equivalencia, la cuota del IVA en euros suma también "
        "las cuotas del recargo, que la orden pone en el desglose del IVA "
        "(BT-117). Ese cuadre no se comprueba."
    ),
    "BT-195": (
        "Solo admite códigos VATEX-EU o VATEX-ES, dice la orden, pero es un "
        "término de la edición de 2026 de la norma sin ruta en la vinculación "
        "de 2017, y la de 2026 no se ha podido leer aquí."
    ),
    "BT-ES-5": (
        "La tipología del tercero tiene que ser FacturaciónPorTercero cuando "
        "el tercero expide materialmente la factura, y eso no se ve en el "
        "documento. Se comprueba que la tipología esté, no cuál es."
    ),
    "BT-113": (
        "El importe pagado no puede usarse para anticipos que hayan devengado "
        "el IVA (artículo 75.Dos de la Ley del IVA), y eso no se ve en la "
        "factura. SPFE-IMPORTE-PAGADO lo dice en una nota cuando lo hay."
    ),
    "BT-21": (
        "La nota de la factura lleva el código REG cuando es una mención "
        "obligatoria según una normativa específica, y qué menciones lo son no "
        "se ve en la factura."
    ),
    "Especificaciones técnicas": (
        "La orden deja las especificaciones técnicas y la volumetría, y el "
        "tamaño máximo de las copias fieles, a lo que conste en la Sede "
        "electrónica de la Agencia (apartado 1 del artículo 3 y apartado 2 del "
        "artículo 4). No son el anexo, y lo que se publique allí puede cambiar "
        "sin pasar por el BOE: aquí no se mide."
    ),
    "Cardinalidades máximas": (
        "Que un campo que no se repite no se repita se mira en los grupos donde "
        "repetirlo cambia lo que se declara: la clave de régimen y la "
        "referencia catastral de cada línea, la fecha efectiva de pago, el QR, "
        "los documentos de la rectificativa y las retenciones. El resto es cosa "
        "del esquema."
    ),
}


# --- Lectura -----------------------------------------------------------------


def _nodos(nodo, ruta: str) -> list:
    return list(nodo.xpath(ruta, namespaces=NS_CIUS_ES))


def _escrito(nodo) -> str:
    return (nodo if isinstance(nodo, str) else nodo.xpath("string()")).strip()


def _valor(nodo, ruta: str) -> str:
    """El primer texto no vacío de la ruta, o cadena vacía."""
    for encontrado in _nodos(nodo, ruta):
        escrito = _escrito(encontrado)
        if escrito:
            return escrito
    return ""


def _nombrados(nodos: list, nombre: str) -> list[tuple[str, object]]:
    """Cada nodo con su nombre, numerado solo si hay más de uno."""
    if len(nodos) == 1:
        return [("", nodos[0])]
    return [(f"{nombre} {n}", nodo) for n, nodo in enumerate(nodos, start=1)]


def _donde(campo: str, lugares: list[str]) -> str:
    lugares = [lugar for lugar in lugares if lugar]
    return campo + (f" · {', '.join(lugares)}" if lugares else "")


def _y(cosas: list[str]) -> str:
    return cosas[0] if len(cosas) == 1 else ", ".join(cosas[:-1]) + " y " + cosas[-1]


def _o(cosas) -> str:
    cosas = list(cosas)
    return cosas[0] if len(cosas) == 1 else ", ".join(cosas[:-1]) + " o " + cosas[-1]


def _en_una_frase(cosas) -> str:
    """Una lista larga en castellano, con punto y coma: sus cosas llevan comas dentro."""
    if len(cosas) == 1:
        return cosas[0]
    return "; ".join(cosas[:-1]) + "; y " + cosas[-1]


def _lo_que_todavia() -> str:
    """El principio de la frase de lo que falta: lo que no se mide, si queda algo."""
    if not LO_QUE_TODAVIA_NO_SE_MIDE:
        return "Hay cosas que "
    return ("De lo que la orden pide, todavía no se mide "
            f"{_en_una_frase(LO_QUE_TODAVIA_NO_SE_MIDE)}. Y hay cosas que ")


def _lo_que_no_se_puede() -> str:
    """Lo de `NO_SE_COMPRUEBA`, nombrado: los campos, y lo que no es un campo al final."""
    return _y([que if que.startswith(("BT-", "BG-")) else "las " + que.lower()
               for que in NO_SE_COMPRUEBA])


# --- Entrada ----------------------------------------------------------------


def declara_el_cius(deteccion) -> bool:
    """Si el documento dice ser de la solución pública.

    Con el identificador de la orden o con el del borrador de abril
    (`formato.declara_la_solucion_publica`). El nombre se queda, aunque el de
    la orden no diga «CIUS», porque es lo que preguntan quienes lo usan: si a
    este documento se le mide con el anexo.
    """
    return bool(deteccion) and declara_la_solucion_publica(deteccion.perfil)


def reglas(raiz, deteccion) -> list[Incidencia]:
    """Las reglas del anexo I, sobre un documento que declara la solución pública."""
    if not declara_el_cius(deteccion):
        return _de_la_aeat_sin_reconocer(deteccion)
    if deteccion.familia == RESPUESTA:
        # El anexo I mide facturas. Una respuesta puede llevar el mismo
        # `CustomizationID`, y sin esta línea recibía SPFE-SINTAXIS diciendo
        # que el anexo «solo define» la solución pública sobre UBL, que es
        # falso: la respuesta es UBL. El mensaje de anulación es una respuesta
        # con sus propios campos en el anexo I («Mensaje de anulación»), y se
        # mide con los suyos en `mensajes`, por su código y no por esto.
        return []
    if deteccion.familia != UBL:
        return [
            Incidencia(
                "SPFE-SINTAXIS",
                AVISO,
                f"El documento es {deteccion.familia} y dice ser de la "
                "solución pública, que el anexo I solo define sobre UBL. Las "
                "reglas del anexo no se han comprobado: no hay correspondencia "
                "publicada de sus campos con esta sintaxis, y la AEAT contestó "
                "el 17-09-2026 que escribirla es cosa de cada plataforma.",
                campo="Identificador de especificación",
                esperado="una factura UBL 2.5",
                encontrado=deteccion.perfil,
            )
        ]
    if raiz is None:
        return []

    if raiz.xpath("local-name()") != "Invoice":
        # Sin la nota del alcance: decía «se mide con el anexo I» junto a esta
        # queja, que dice que el resto no se ha comprobado, y la línea de
        # alcance del lote, que cuelga de esa nota, contaba el abono como
        # medido. Lo vio el revisor de promesas el 11-10-2026.
        return [
            Incidencia(
                "SPFE-TIPO-DE-FACTURA",
                ERROR,
                "El documento es un abono (CreditNote), y el anexo solo define "
                "facturas: su lista de tipos no tiene el 381. En la solución "
                "pública una rectificativa es una factura (Invoice) de tipo "
                "384, o 471 si la expide el destinatario. El resto de reglas "
                "del anexo no se ha comprobado.",
                campo="Tipo de documento",
                esperado="Invoice, con un tipo de la lista L1",
                encontrado=f"{raiz.xpath('local-name()')} "
                           f"{_valor(raiz, './cbc:CreditNoteTypeCode')}".strip(),
            )
        ]

    incidencias = [
        # La nota dice con qué se ha medido y qué no. «Ninguna queja» no quiere
        # decir «cumple la orden», y lo que falta va entero: lo que todavía no
        # se mide, de `LO_QUE_TODAVIA_NO_SE_MIDE`, y lo que no se puede, de
        # `NO_SE_COMPRUEBA`, con su porqué en la ficha. Hasta el 11-10-2026 la
        # segunda lista no llegaba al informe, y la portada y la política de
        # privacidad dicen que lo que no se mide lo dice el informe; y la nota
        # acababa «no quiere decir que la factura cumpla la orden en eso», como
        # si lo demás estuviera medido entero. Lo vio el revisor de promesas.
        Incidencia(
            "SPFE-ALCANCE",
            NOTA,
            "La factura dice ser de la solución pública, y se mide con el anexo "
            "I de la Orden HAC/1028/2026, publicada en el BOE el 05-10-2026 y en "
            f"vigor desde el 06-10-2026. {_lo_que_todavia()}"
            "no se comprueban, con el porqué en la ficha de esta nota: "
            f"{_lo_que_no_se_puede()}. Que no salga ninguna queja no quiere "
            "decir que la factura cumpla la orden.",
            campo="Identificador de especificación",
            encontrado=_valor(raiz, SINTAXIS_UBL.perfil),
        )
    ]
    for regla in (
        _especificacion, _proceso, _copia, _tipo_de_factura, _rectificativa,
        _moneda_del_iva, _importe_pagado, _fecha_de_pago, _nif, _registro_legal,
        _prefijo_del_nif, _direcciones, _tipo_de_impuesto, _tercero,
        _facturas_referenciadas, _motivos, _categorias, _tipo_del_desglose,
        _exenciones, _impuestos_de_los_cargos_de_linea, _impuestos_de_los_cargos,
        _claves_de_regimen, _referencias_catastrales, _informacion_adicional,
        _lineas_de_cobro, _retenciones, _cuadre_de_las_retenciones,
        _impuestos_de_los_cobros, _qr, _autorizacion, _ficheros_embebidos,
        _total_a_pagar, _calificadores,
    ):
        incidencias.extend(regla(raiz))
    return incidencias


# --- Las reglas ----------------------------------------------------------------


def _de_la_aeat_sin_reconocer(deteccion) -> list[Incidencia]:
    """Un identificador que nombra a la AEAT y no es ninguno de los dos.

    No se le mide con el anexo: no dice ser lo que el anexo define, y medirlo
    sería afirmar algo que no se sabe. Pero callarse es peor, y es lo que pasó
    con el ejemplo de la AEAT del 02-10-2026 hasta que se midió: un
    identificador nuevo, sin que nada lo dijera, y todo en verde. Si mañana
    sale un tercero, que se vea.
    """
    perfil = (deteccion.perfil if deteccion else "") or ""
    if NOMBRA_A_LA_AEAT not in perfil or deteccion.familia == RESPUESTA:
        return []
    return [
        Incidencia(
            "SPFE-ESPECIFICACION",
            AVISO,
            "El identificador de especificación nombra a la AEAT, pero no es "
            "el que fija la orden publicada en el BOE el 05-10-2026 (fila "
            "BT-24) ni el CIUS del borrador de abril. Las reglas del anexo no "
            "se han comprobado.",
            campo="Identificador de especificación (BT-24)",
            esperado=ESPECIFICACION,
            encontrado=perfil,
        )
    ]


def _especificacion(raiz) -> list[Incidencia]:
    """BT-24: el valor entero que fija la orden.

    Al revés que hasta el 11-10-2026, cuando el que se pedía era el del
    borrador de abril y el de la orden se aceptaba como «el del ejemplo». El
    de abril ya no vale, y el mensaje dice de dónde sale para que quien lo
    escribió sepa qué cambiar.
    """
    declarado = _valor(raiz, SINTAXIS_UBL.perfil)
    if declarado == ESPECIFICACION:
        return []
    if declarado == ESPECIFICACION_DEL_BORRADOR:
        mensaje = ("El identificador de especificación es el del borrador de "
                   "abril, que no llegó al BOE. La orden publicada el 05-10-2026 "
                   "fija otro en su fila BT-24, y es el único que vale.")
    else:
        mensaje = ("El identificador de especificación nombra el CIUS del "
                   "borrador de abril, pero no con su valor entero, y tampoco es "
                   "el que fija la orden publicada el 05-10-2026 en su fila "
                   "BT-24, que es el único que vale.")
    return [
        Incidencia(
            "SPFE-ESPECIFICACION",
            ERROR,
            mensaje,
            campo="Identificador de especificación (BT-24)",
            esperado=ESPECIFICACION,
            encontrado=declarado,
        )
    ]


def _proceso(raiz) -> list[Incidencia]:
    """BT-23: opcional en la norma, obligatorio y con valor fijo en la orden.

    `cbc:ProfileID` es donde la vinculación UBL escribe BT-23; `SINTAXIS_UBL`
    no lo lleva porque ninguna regla europea lo miraba.
    """
    declarado = _valor(raiz, "./cbc:ProfileID")
    if declarado == PROCESO:
        return []
    if declarado == PROCESO_DE_LA_ORDEN:
        # Un AVISO: es lo que dice el BOE, y la corrección no está publicada
        # todavía. Pero no una NOTA, porque la AEAT ha dicho por escrito que el
        # bueno es el otro.
        return [
            Incidencia(
                "SPFE-PROCESO",
                AVISO,
                "El tipo de proceso de negocio es el que escribe la orden "
                "publicada en el BOE el 05-10-2026, el que lleva ubl. La AEAT "
                f"contestó por escrito el 13-10-2026 que el que vale es {PROCESO}, "
                "sin ubl, como el resto de campos y como en su ejemplo del "
                "02-10-2026. Es un aviso y no un error porque es lo que dice el "
                "texto publicado.",
                campo="Tipo de proceso de negocio (BT-23)",
                esperado=PROCESO,
                encontrado=declarado,
            )
        ]
    if not declarado:
        mensaje = ("Falta el tipo de proceso de negocio. La norma europea lo deja "
                   "opcional; la orden lo hace obligatorio, y con un valor fijo.")
    elif declarado == PROCESO_DEL_BORRADOR:
        mensaje = ("El tipo de proceso de negocio es el del borrador de abril, "
                   "que no llegó al BOE. La orden admite un solo valor, y no es "
                   "ese.")
    else:
        mensaje = ("El tipo de proceso de negocio no es el que vale. La orden "
                   "admite un solo valor, y la AEAT contestó el 13-10-2026 que "
                   "es el que no lleva ubl.")
    return [
        Incidencia(
            "SPFE-PROCESO",
            ERROR,
            mensaje,
            campo="Tipo de proceso de negocio (BT-23)",
            esperado=PROCESO,
            encontrado=declarado or "(falta)",
        )
    ]


def _calificadores(raiz) -> list[Incidencia]:
    """Los valores de L7, L8 y L10 escritos sin el calificador de su lista.

    Las filas de la orden dan solo el valor, "usar RETE", y cada lista trae su
    calificador aparte. Hasta el 13-10-2026 se aceptaban las dos formas sin
    decir nada, porque la orden no dice cómo se juntan; ese día el buzón
    contestó que se escriben con el calificador seguido del valor, en las tres
    listas. Las demás reglas los siguen reconociendo de las dos maneras, para
    no dejar de medir una retención por cómo se escribe su línea; esta dice,
    una vez por factura, cuáles van sin él.
    """
    solos: dict[str, str] = {}
    for adjunto in _nodos(raiz, SINTAXIS_UBL.adjuntos):
        escrito = _valor(adjunto, _ID_DEL_DOCUMENTO)
        if escrito in _DOCUMENTOS:
            solos.setdefault(escrito, _ESQUEMA_L10)
    for linea in _nodos(raiz, _LINEA_DE_COBRO):
        escrito = _valor(linea, "./cbc:ID")
        if escrito in _L7:
            solos.setdefault(escrito, _CALIFICADOR_L7)
    for linea in _nodos(raiz, _LINEAS):
        for propiedad in _nodos(linea, _PROPIEDADES):
            escrito = _valor(propiedad, "./cbc:Name")
            if escrito in _NOMBRES_L8:
                solos.setdefault(escrito, _CALIFICADOR_L8)
    if not solos:
        return []
    return [
        Incidencia(
            "SPFE-CALIFICADOR",
            AVISO,
            f"{_y(list(solos))} {'va' if len(solos) == 1 else 'van'} sin el "
            "calificador de su lista delante. Las filas de la orden dan solo el "
            "valor, y la AEAT contestó por escrito el 13-10-2026 que en las "
            "listas L7, L8 y L10 se escribe el calificador seguido del valor, "
            "como en su ejemplo del 02-10-2026. Se ha leído igual, y lo demás "
            "se ha medido.",
            campo="Valores de las listas L7, L8 y L10",
            esperado=", ".join(f"{calificador}{valor}" for valor, calificador in solos.items()),
            encontrado=", ".join(solos),
        )
    ]


def _copia(raiz) -> list[Incidencia]:
    """BT-ES-1: si es el original o una copia.

    La orden lo deja en `0..1` —«True: copia. False (o sin informar):
    original»—, así que sin él la factura es el original, y eso se dice en una
    NOTA: quien mande una copia fiel sin el indicador está mandando, para la
    orden, un original, y el artículo 4.3 pide que la copia fiel se identifique
    justo ahí.
    """
    if _valor(raiz, _COPIA):
        return []
    return [
        Incidencia(
            "SPFE-COPIA",
            NOTA,
            "La factura no dice si es el original o una copia, y la orden "
            "publicada en el BOE el 05-10-2026 la toma entonces por el "
            "original. Si es una copia "
            "fiel, el apartado 3 del artículo 4 de la orden pide identificarla "
            "ahí, con true.",
            campo="Indicador de copia (BT-ES-1)",
            encontrado="(sin informar)",
        )
    ]


def _tipo_de_factura(raiz) -> list[Incidencia]:
    """BT-3 y la lista L1.

    Solo los códigos que la norma europea sí admite: de uno que no está ni en
    UNTDID 1001 ya se queja BR-CL-01, y dos quejas por el mismo código no dicen
    más que una.
    """
    codigo = _valor(raiz, "./cbc:InvoiceTypeCode")
    if not codigo or codigo in _L["L1"].valores or codigo not in _UNCL1001:
        return []
    mensaje = ("El tipo de factura es un código de la norma europea, pero no de "
               "los que admite la orden, que son los de la lista L1.")
    if codigo == "381":
        mensaje += (" El 381 es el abono de la EN 16931 y en la solución pública "
                    "no existe: una rectificativa es 384, o 471 si la expide el "
                    "destinatario. Si rectifica por diferencias o por "
                    "sustitución se dice en dos documentos justificativos "
                    "adicionales (BG-24), con los valores RECT:TIPO y "
                    "RECT:MODALIDAD de la lista L10, como pide la orden en su "
                    "fila BT-3.")
    return [
        Incidencia(
            "SPFE-TIPO-DE-FACTURA",
            ERROR,
            mensaje,
            campo="Tipo de factura (BT-3)",
            esperado=_o(_L["L1"].valores),
            encontrado=codigo,
        )
    ]


def _rectificativa(raiz) -> list[Incidencia]:
    """Los BG-24 de la rectificativa: el tipo y la modalidad, y los importes si los hay.

    La orden pide en toda 384 y 471 un documento justificativo adicional con
    el tipo (RECT:TIPO) y otro con la modalidad (RECT:MODALIDAD), cada uno con
    su código en `cbc:DocumentTypeCode` (filas BT-ES-27 y BT-ES-28) y de su
    lista; y, si se rectifica por sustitución con una sola factura, los
    importes rectificados (RECT:IMPORTES), uno por código de L2.C, con su
    importe en la descripción.

    Hasta el 11-10-2026, salvo la rectificativa que no decía nada, que ya era
    ERROR, todo esto salía como NOTA o AVISO, porque el sitio lo decía un
    ejemplo de la AEAT y no un texto publicado; y se aceptaba además la
    extensión de rectificativas del borrador de abril. La orden lo dice, y la
    extensión no está en ella.
    """
    tipo = _valor(raiz, "./cbc:InvoiceTypeCode")
    if tipo not in _RECTIFICATIVOS:
        return []
    presentes: dict[str, list] = {}
    for calificador, adjunto in _adjuntos(raiz):
        if calificador in _RECTIFICATIVA:
            presentes.setdefault(calificador, []).append(adjunto)

    incidencias: list[Incidencia] = []
    faltan = [_RECTIFICATIVA[c][0] for c in ("RECT:TIPO", "RECT:MODALIDAD") if c not in presentes]
    if faltan:
        incidencias.append(
            Incidencia(
                "SPFE-RECTIFICATIVA",
                ERROR,
                f"La factura es rectificativa ({tipo}) y no dice {_y(faltan)}. "
                "La orden pide en toda 384 y 471 un documento justificativo "
                "adicional (BG-24) con el tipo, identificado con RECT:TIPO, y "
                "otro con la modalidad, identificado con RECT:MODALIDAD, los dos "
                "de la lista L10 (fila BT-3). Ahí se dice qué se rectifica (R1 a "
                "R4) y cómo, por diferencias (I) o por sustitución (S).",
                campo="Datos rectificados (BG-24, BT-3)",
                esperado="los BG-24 RECT:TIPO y RECT:MODALIDAD",
                encontrado="falta " + _y(faltan),
            )
        )

    for calificador, adjuntos in presentes.items():
        nombre, identificador = _RECTIFICATIVA[calificador]
        maximo = _MAXIMO_DEL_DOCUMENTO[calificador]
        if len(adjuntos) > maximo:
            incidencias.append(
                Incidencia(
                    "SPFE-RECTIFICATIVA",
                    ERROR,
                    f"Hay {len(adjuntos)} documentos con {nombre} ({calificador}), "
                    f"y la orden admite {'uno' if maximo == 1 else maximo} como mucho.",
                    campo=f"Datos rectificados (BG-24 {calificador})",
                    esperado=f"{'uno' if maximo == 1 else maximo} como mucho",
                    encontrado=str(len(adjuntos)),
                )
            )
        lista_ = _LISTA_DEL_DOCUMENTO[calificador]
        valores = _L[lista_].valores
        for n, adjunto in enumerate(adjuntos, start=1):
            cual = f" ({n}.º)" if len(adjuntos) > 1 else ""
            codigo = _valor(adjunto, _CODIGO_DEL_DOCUMENTO[calificador])
            if not codigo:
                incidencias.append(
                    Incidencia(
                        "SPFE-RECTIFICATIVA",
                        ERROR,
                        f"El documento con {nombre} ({calificador}) no lleva su "
                        "código. La orden lo pide en cbc:DocumentTypeCode, de la "
                        f"lista {lista_} (fila {identificador}).",
                        campo=f"{nombre[0].upper()}{nombre[1:]} ({identificador}){cual}",
                        esperado=_o(valores),
                        encontrado="(falta)",
                    )
                )
            elif codigo not in valores:
                incidencias.append(
                    Incidencia(
                        "SPFE-RECTIFICATIVA",
                        ERROR,
                        f"El código de {nombre} no está en la lista {lista_} de "
                        f"la orden (fila {identificador}).",
                        campo=f"{nombre[0].upper()}{nombre[1:]} ({identificador}){cual}",
                        esperado=_o(valores),
                        encontrado=codigo,
                    )
                )
            if calificador == "RECT:IMPORTES" and not _valor(adjunto, _DESCRIPCION_DEL_DOCUMENTO):
                incidencias.append(
                    Incidencia(
                        "SPFE-RECTIFICATIVA",
                        ERROR,
                        "El documento de los importes rectificados no lleva el "
                        "importe. La orden lo pide en la descripción del documento "
                        "(BT-123), obligatoria en este grupo.",
                        campo=f"Importe rectificado (BT-123){cual}",
                        esperado="el importe en cbc:DocumentDescription",
                        encontrado="(falta)",
                    )
                )

    modalidades = {_valor(adjunto, _CODIGO_DEL_DOCUMENTO["RECT:MODALIDAD"])
                   for adjunto in presentes.get("RECT:MODALIDAD", [])}
    if "S" in modalidades and "RECT:IMPORTES" not in presentes:
        incidencias.append(
            Incidencia(
                "SPFE-RECTIFICATIVA",
                NOTA,
                "La modalidad es S y la factura no trae los importes "
                "rectificados. La orden solo los prevé cuando, en una "
                "sustitución, se opta por emitir una única factura con los "
                "importes correctos (BG-24 RECT:IMPORTES), y si se optó por eso "
                "no se ve en la factura, así que no se da por mala.",
                campo="Importes rectificados (BG-24 RECT:IMPORTES)",
                encontrado="(no los trae)",
            )
        )
    # Lo que la orden dice de los importes y aquí se callaba, hasta que el
    # auditor lo midió el 11-10-2026: que van en una sustitución, y cuántos.
    importes = presentes.get("RECT:IMPORTES", [])
    conocidas = modalidades - {""}
    if importes and conocidas and "S" not in conocidas:
        incidencias.append(
            Incidencia(
                "SPFE-RECTIFICATIVA",
                AVISO,
                "La factura trae los importes rectificados y la modalidad no es "
                "la de sustitución. La orden prevé ese grupo para los casos en "
                "que se rectifica por sustitución (S) y se opta por una única "
                "factura con los importes correctos; por diferencias (I) no se "
                "rectifica así.",
                campo="Importes rectificados (BG-24 RECT:IMPORTES)",
                esperado="la modalidad S",
                encontrado=", ".join(sorted(conocidas)),
            )
        )
    # Más de cinco ya es ERROR por la cardinalidad del grupo, arriba.
    codigos = [_valor(adjunto, _CODIGO_DEL_DOCUMENTO["RECT:IMPORTES"]) for adjunto in importes]
    repetidos = [c for c in dict.fromkeys(codigos) if c in _CODIGOS_DE_IMPORTE and codigos.count(c) > 1]
    if repetidos and len(importes) <= _MAXIMO_DEL_DOCUMENTO["RECT:IMPORTES"]:
        incidencias.append(
            Incidencia(
                "SPFE-RECTIFICATIVA",
                AVISO,
                f"Hay más de un importe rectificado con {_y(repetidos)}. La fila "
                "BT-3 habla de hasta tres grupos y el BOE le da al grupo cinco "
                "(0..5); la AEAT contestó el 13-10-2026 que el grupo pasa a 0..1 en "
                "el anexo que publicará en su Portal de Desarrolladores, y en el "
                "ejemplo que mandó ese día lleva uno por código de la lista L2.C: "
                f"{_y(list(_CODIGOS_DE_IMPORTE))}. Es un aviso y no un error "
                "porque el BOE lo admite.",
                campo="Importes rectificados (BG-24 RECT:IMPORTES)",
                esperado="uno por código de L2.C",
                encontrado=", ".join(f"{c} {codigos.count(c)} veces" for c in repetidos),
            )
        )
    return incidencias


def _moneda_del_iva(raiz) -> list[Incidencia]:
    """BT-6: el euro, y obligatorio si la factura va en otra moneda.

    Un código que no es de ISO 4217 ya lo denuncia BR-CL-04 o BR-CL-05.
    """
    iso = lista("ISO_4217", SINTAXIS_UBL)
    moneda = _valor(raiz, SINTAXIS_UBL.moneda)
    del_iva = _valor(raiz, SINTAXIS_UBL.moneda_impuestos)
    if del_iva:
        if del_iva == "EUR" or del_iva not in iso:
            return []
        mensaje = ("La moneda de contabilización del IVA no es el euro, y el "
                   "anexo no admite otra.")
    elif moneda and moneda != "EUR" and moneda in iso:
        mensaje = (f"La factura está en {moneda} y no dice la moneda de "
                   "contabilización del IVA. Cuando la factura no va en euros, "
                   "el anexo obliga a consignar el euro como moneda del IVA, y "
                   "con él la cuota total del IVA en euros (BT-111).")
    else:
        return []
    return [
        Incidencia(
            "SPFE-MONEDA-DEL-IVA",
            ERROR,
            mensaje,
            campo="Moneda de contabilización del IVA (BT-6)",
            esperado="EUR",
            encontrado=del_iva or "(falta)",
        )
    ]


def _importe_pagado(raiz) -> list[Incidencia]:
    """BT-113: lo pagado por adelantado.

    El borrador de abril solo lo admitía a cero. La orden quita esa frase y
    pone otra: «Este campo no debe ser utilizado en el caso de pagos
    anticipados que hayan supuesto el devengo del IVA previsto en el artículo
    75.Dos de la Ley 37/1992». Si un anticipo devengó el IVA no se ve en la
    factura, así que eso no se puede comprobar, y se dice en una NOTA en vez
    de callarlo.
    """
    incidencias: list[Incidencia] = []
    for pagado in _nodos(raiz, SINTAXIS_UBL.anticipos):
        escrito = _escrito(pagado)
        valor = a_decimal(escrito)
        # Un importe que no es un número es cosa del esquema. «NaN» también:
        # con `Decimal` a secas no era igual a cero y salía acusado de no serlo.
        if valor is None or valor == 0:
            continue
        incidencias.append(
            Incidencia(
                "SPFE-IMPORTE-PAGADO",
                NOTA,
                "La factura lleva un importe pagado por adelantado. La orden "
                "publicada en el BOE el 05-10-2026 lo admite, pero no para los "
                "anticipos que hayan devengado el IVA (artículo 75.Dos de la Ley "
                "del IVA), y eso no se ve en la factura: no se ha comprobado.",
                campo="Importe pagado (BT-113)",
                encontrado=escrito,
            )
        )
    return incidencias


# Una fecha como la escribe UBL (xs:date): 2026-10-06, con zona o sin ella. Lo
# que no tenga esa forma no se compara: eso es cosa del esquema.
_DIA = re.compile(r"(\d{4})-(\d{2})-(\d{2})")


def _dia(escrito: str) -> date | None:
    encontrado = _DIA.match(escrito)
    if not encontrado:
        return None
    try:
        return date(*map(int, encontrado.groups()))
    except ValueError:
        return None


def _fecha_de_pago(raiz) -> list[Incidencia]:
    """BT-ES-2: la fecha efectiva de pago, si está.

    La orden la admite cuando la factura «ha sido pagada con anterioridad a la
    fecha de expedición de la factura o en dicha fecha», y pide que sea
    «coincidente o posterior a la fecha de realización de las operaciones».
    Con ella, si además coincide con la de la operación, el destinatario no
    tiene que comunicar el pago (apartado 4 del artículo 7), y por eso importa
    que diga lo que puede decir. La fila admite más que el artículo: un pago
    posterior a la operación vale, pero no libera de comunicarlo, y una nota
    lo dice.

    La fecha de la operación es BT-7, y la orden lo pide solo cuando es otra
    que la de expedición: sin BT-7, la operación es del día de la expedición, y
    un pago anterior es un pago anterior a la operación. Salvo que la factura
    dé un periodo (BG-14, la factura recapitulativa): entonces las operaciones
    son del periodo, la orden no dice con cuál se compara, y se dice en una
    nota en vez de condenar.
    """
    escritas = [e for e in (_escrito(n) for n in _nodos(raiz, _FECHA_DE_PAGO)) if e]
    if not escritas:
        return []
    campo = "Fecha efectiva de pago (BT-ES-2)"
    incidencias: list[Incidencia] = []
    if len(escritas) > 1:
        incidencias.append(
            Incidencia(
                "SPFE-FECHA-DE-PAGO",
                ERROR,
                f"Hay {len(escritas)} fechas efectivas de pago, y la orden admite "
                "una por factura.",
                campo=campo,
                esperado="una como mucho",
                encontrado=", ".join(escritas),
            )
        )
    expedicion = _dia(_valor(raiz, SINTAXIS_UBL.fecha))
    operacion_escrita = _valor(raiz, SINTAXIS_UBL.fecha_devengo)
    operacion = _dia(operacion_escrita)
    if expedicion is None:
        return incidencias
    despues, antes_de_la_operacion, antes_sin_operacion = [], [], []
    despues_de_la_operacion: list[str] = []
    for escrita in escritas:
        pago = _dia(escrita)
        if pago is None:
            continue
        if pago > expedicion:
            despues.append(escrita)
        elif operacion_escrita:
            if operacion is not None and pago < operacion:
                antes_de_la_operacion.append(escrita)
            elif operacion is not None and pago > operacion:
                despues_de_la_operacion.append(escrita)
        elif pago < expedicion:
            antes_sin_operacion.append(escrita)
    if despues:
        incidencias.append(
            Incidencia(
                "SPFE-FECHA-DE-PAGO",
                ERROR,
                "La fecha efectiva de pago es posterior a la de expedición. La "
                "orden la admite cuando la factura se pagó antes de expedirse o "
                "ese mismo día (fila BT-ES-2).",
                campo=campo,
                esperado=f"el {cifras.fecha(expedicion)} o antes",
                encontrado=", ".join(despues),
            )
        )
    if antes_de_la_operacion:
        incidencias.append(
            Incidencia(
                "SPFE-FECHA-DE-PAGO",
                ERROR,
                "La fecha efectiva de pago es anterior a la de la operación "
                "(BT-7), y la orden la pide coincidente o posterior a la fecha "
                "de realización de las operaciones (fila BT-ES-2). Un pago "
                "anterior a la operación es un anticipo.",
                campo=campo,
                esperado=f"del {cifras.fecha(operacion)} al {cifras.fecha(expedicion)}",
                encontrado=", ".join(antes_de_la_operacion),
            )
        )
    if despues_de_la_operacion:
        incidencias.append(
            Incidencia(
                "SPFE-FECHA-DE-PAGO",
                NOTA,
                "La fecha efectiva de pago es posterior a la de la operación "
                "(BT-7) y no a la de expedición, y la orden la admite (fila "
                "BT-ES-2). Pero el apartado 4 de su artículo 7 da por cumplida la "
                "comunicación del pago solo cuando la fecha coincide con la de la "
                "operación o el devengo: con esta, el destinatario tiene que "
                "comunicar el pago igual.",
                campo=campo,
                encontrado=", ".join(despues_de_la_operacion),
            )
        )
    if antes_sin_operacion and _nodos(raiz, SINTAXIS_UBL.periodo_grupo):
        incidencias.append(
            Incidencia(
                "SPFE-FECHA-DE-PAGO",
                NOTA,
                "La fecha efectiva de pago es anterior a la de expedición, y la "
                "factura da un periodo de facturación (BG-14) en vez de la fecha "
                "de la operación (BT-7). La orden pide el pago coincidente o "
                "posterior a la fecha de realización de las operaciones, y no "
                "dice con qué fecha del periodo se compara: no se ha comprobado.",
                campo=campo,
                encontrado=", ".join(antes_sin_operacion),
            )
        )
    elif antes_sin_operacion:
        incidencias.append(
            Incidencia(
                "SPFE-FECHA-DE-PAGO",
                ERROR,
                "La fecha efectiva de pago es anterior a la de expedición, y la "
                "factura no da otra fecha de operación (BT-7). La orden pide BT-7 "
                "solo cuando la operación es de otro día que la expedición, así "
                "que la operación es del día de la expedición; y el pago tiene que "
                "ser coincidente o posterior a la fecha de realización de las "
                "operaciones (fila BT-ES-2). Si la operación fue antes, falta su "
                "fecha en BT-7.",
                campo=campo,
                esperado=f"el {cifras.fecha(expedicion)}, o la fecha de la operación en BT-7",
                encontrado=", ".join(antes_sin_operacion),
            )
        )
    return incidencias


def _nif_bien_puesto(esquema) -> bool:
    """Si un `cac:PartyTaxScheme` lleva el NIF como admite la orden.

    Con el impuesto «VAT» (BT-31, BT-48), o con «LOC» y el atributo
    `schemeID` «FC» en el propio NIF (BT-32, BT-47).
    """
    if not _valor(esquema, "./cbc:CompanyID"):
        return False
    impuesto = _valor(esquema, _IMPUESTO_DEL_ESQUEMA)
    if impuesto == _IMPUESTO:
        return True
    return (impuesto == _IMPUESTO_LOCAL
            and _valor(esquema, _ATRIBUTO_DEL_NIF) == _ESQUEMA_DEL_NIF)


def _nif_de(raiz, esquemas: str) -> str | None:
    """None si el NIF está como lo admite la orden; si no, qué hay en su lugar."""
    encontrados = []
    for esquema in _nodos(raiz, esquemas):
        if _nif_bien_puesto(esquema):
            return None
        nif = _valor(esquema, "./cbc:CompanyID")
        impuesto = _valor(esquema, _IMPUESTO_DEL_ESQUEMA)
        if nif:
            atributo = _valor(esquema, _ATRIBUTO_DEL_NIF)
            con = f" y schemeID \"{atributo}\"" if atributo else ""
            encontrados.append(f"{nif} con el impuesto {entre_comillas(impuesto, '(sin impuesto)')}{con}")
    return ", ".join(encontrados) or "(falta)"


def _nif(raiz) -> list[Incidencia]:
    """El NIF de cada parte, en «VAT» o en «LOC» con «FC».

    La orden da dos sitios para el NIF de cada parte, y basta uno: el del
    vendedor va en BT-31, con el impuesto «VAT», o en BT-32, con «LOC» y el
    atributo «FC» —«Será obligatorio consignar un NIF válido en el caso de que
    el campo BT-31 no tenga contenido»—; el del comprador, igual, en BT-48 o
    en BT-47.
    """
    incidencias: list[Incidencia] = []
    for quien, esquemas, codigos in (
        ("vendedor", _ESQUEMAS_DEL_VENDEDOR, "BT-31 o BT-32"),
        ("comprador", _ESQUEMAS_DEL_COMPRADOR, "BT-48 o BT-47"),
    ):
        encontrado = _nif_de(raiz, esquemas)
        if encontrado is None:
            continue
        incidencias.append(
            Incidencia(
                "SPFE-NIF",
                ERROR,
                f"Falta el NIF del {quien} donde lo pide la orden, que admite "
                f"dos sitios: un esquema de impuesto {_IMPUESTO}, o uno "
                f"{_IMPUESTO_LOCAL} con el atributo schemeID {_ESQUEMA_DEL_NIF} "
                "en el NIF. La norma europea lo deja opcional; la orden lo hace "
                "obligatorio para las dos partes.",
                campo=f"NIF del {quien} ({codigos})",
                esperado=f"cac:PartyTaxScheme con cbc:CompanyID y cac:TaxScheme/cbc:ID "
                         f"{_IMPUESTO}, o {_IMPUESTO_LOCAL} con cbc:CompanyID@schemeID "
                         f"{_ESQUEMA_DEL_NIF}",
                encontrado=encontrado,
            )
        )
    return incidencias


def _registro_legal(raiz) -> list[Incidencia]:
    """BT-30: el registro legal del vendedor, que la orden describe como su NIF.

    La norma pide uno de tres para identificar al vendedor (BR-CO-26): su
    identificador (BT-29), su registro legal (BT-30) o su NIF-IVA (BT-31). La
    orden pide BT-30 en concreto cuando el NIF va con «LOC» y el atributo
    «FC», y lo describe como el NIF del vendedor. Si falta todo, sale también
    BR-CO-26, que dice otra cosa: que no hay ninguno de los tres.

    Hasta el 12-10-2026 se miraba que estuviera y no qué llevaba: un registro
    mercantil, o el NIF de otro, pasaban sin una queja. Lo vio el auditor.
    Ahora tiene que ser un NIF, con el prefijo ES o sin él, y el mismo que el
    vendedor da en BT-31 o en BT-32 si alguno se lee como NIF español. Con el
    NIF en BT-32 es un ERROR, porque la orden lo pide; sin él, un AVISO: la
    orden no lo pide, y la norma admite ahí el de cualquier registro oficial.
    """
    con_bt32 = [esquema for esquema in _nodos(raiz, _ESQUEMAS_DEL_VENDEDOR)
                if _valor(esquema, _IMPUESTO_DEL_ESQUEMA) == _IMPUESTO_LOCAL
                and _nif_bien_puesto(esquema)]
    registro = _valor(raiz, SINTAXIS_UBL.vendedor_registro)
    if registro:
        return _que_lleva_el_registro(raiz, registro, bool(con_bt32))
    if not con_bt32:
        return []
    return [
        Incidencia(
            "SPFE-NIF",
            ERROR,
            f"El NIF del vendedor va con {_IMPUESTO_LOCAL} y el atributo "
            f"{_ESQUEMA_DEL_NIF} (BT-32), y falta su identificador de "
            "inscripción legal (BT-30). La orden lo hace obligatorio en ese caso "
            "y lo describe como el NIF del vendedor. No le da ruta: la "
            "vinculación UBL de la norma lo pone en "
            "cac:PartyLegalEntity/cbc:CompanyID.",
            campo="Identificador de inscripción legal del vendedor (BT-30)",
            esperado="el NIF del vendedor en cac:PartyLegalEntity/cbc:CompanyID",
            encontrado="(falta)",
        )
    ]


def _que_lleva_el_registro(raiz, registro: str, con_bt32: bool) -> list[Incidencia]:
    """Que BT-30 sea el NIF del vendedor, como lo describe la orden."""
    # Los NIF del vendedor que se leen como españoles. Con uno de otro país en
    # BT-31 no hay con qué comparar, y su prefijo ya lo dice SPFE-NIF.
    suyos = sorted({limpio for limpio in (limpiar_nif(_valor(esquema, "./cbc:CompanyID"))
                                          for esquema in _nodos(raiz, _ESQUEMAS_DEL_VENDEDOR)
                                          if _nif_bien_puesto(esquema))
                    if nif.validar(limpio)})
    escrito = limpiar_nif(registro)
    es_nif = nif.validar(escrito)
    if es_nif and (not suyos or escrito in suyos):
        return []
    gravedad = ERROR if con_bt32 else AVISO
    if not es_nif:
        que = (f"El identificador de inscripción legal del vendedor (BT-30) no es un "
               f"NIF. {es_nif.motivo}")
    else:
        que = ("El identificador de inscripción legal del vendedor (BT-30) es un NIF, "
               f"pero no el del vendedor, que la factura da como {_o(suyos)}.")
    porque = (" La orden lo describe como el NIF del vendedor, y lo pide cuando su "
              f"NIF va con {_IMPUESTO_LOCAL} y el atributo {_ESQUEMA_DEL_NIF} "
              "(BT-32), como aquí."
              if con_bt32 else
              " La orden lo describe como el NIF del vendedor. Es un aviso porque "
              "solo lo pide cuando el NIF va en BT-32, y la norma europea admite "
              "ahí el identificador de cualquier registro oficial.")
    return [
        Incidencia(
            "SPFE-NIF",
            gravedad,
            que + porque,
            campo="Identificador de inscripción legal del vendedor (BT-30)",
            esperado="el NIF del vendedor" + (f", {_o(suyos)}," if suyos else "")
                     + " con el prefijo ES o sin él",
            encontrado=registro,
        )
    ]


def _prefijo_del_nif(raiz) -> list[Incidencia]:
    """BT-31 y BT-48: el NIF-IVA con el prefijo de España.

    La norma admite el prefijo de cualquier país (BR-CO-09), y la orden pide
    el de España, a los dos. Lo del comprador salía en AVISO hasta el
    13-10-2026, porque su fila lo llama NIF del vendedor (ver al importar).
    """
    incidencias: list[Incidencia] = []
    for quien, esquemas, identificador, otro, gravedad, mensaje in (
        ("vendedor", _ESQUEMAS_DEL_VENDEDOR, "BT-31", "BT-32", ERROR,
         "La orden lo pide con el prefijo de España (fila BT-31); la norma "
         "europea admite el de cualquier país."),
        ("comprador", _ESQUEMAS_DEL_COMPRADOR, "BT-48", "BT-47", ERROR,
         "La orden lo pide con el prefijo de España (fila BT-48). La fila lo "
         "llama NIF del vendedor, y la AEAT contestó por escrito el 13-10-2026 "
         "que es una errata de la descripción: el prefijo es para el comprador."),
    ):
        otros = [nif for esquema in _nodos(raiz, esquemas)
                 if _valor(esquema, _IMPUESTO_DEL_ESQUEMA) == _IMPUESTO
                 and (nif := _valor(esquema, "./cbc:CompanyID"))
                 and not nif.startswith(_PREFIJO_DE_ESPANA)]
        if not otros:
            continue
        incidencias.append(
            Incidencia(
                "SPFE-NIF",
                gravedad,
                f"El NIF-IVA del {quien} ({identificador}) no lleva el prefijo "
                f"{_PREFIJO_DE_ESPANA}. {mensaje} Si se identifica con el NIF y no "
                f"con el NIF-IVA, la orden lo admite con {_IMPUESTO_LOCAL} y el "
                f"atributo {_ESQUEMA_DEL_NIF} ({otro}).",
                campo=f"NIF-IVA del {quien} ({identificador})",
                esperado=f"el NIF con {_PREFIJO_DE_ESPANA} delante",
                encontrado=", ".join(otros),
            )
        )
    return incidencias


def _direcciones(raiz) -> list[Incidencia]:
    """La calle siempre; ciudad, código postal y provincia si está en España.

    Si no hay dirección, eso ya lo dicen BR-08 y BR-10.
    """
    incidencias: list[Incidencia] = []
    for quien, ruta, calle, resto in (
        ("vendedor", SINTAXIS_UBL.vendedor_direccion, "BT-35", ("BT-37", "BT-38", "BT-39")),
        ("comprador", SINTAXIS_UBL.comprador_direccion, "BT-50", ("BT-52", "BT-53", "BT-54")),
    ):
        direcciones = _nodos(raiz, ruta)
        if not direcciones:
            continue
        direccion = direcciones[0]
        pedidos = [("./cbc:StreetName", f"la calle ({calle})")]
        en_espana = _valor(direccion, "./cac:Country/cbc:IdentificationCode") == "ES"
        if en_espana:
            pedidos += [
                ("./cbc:CityName", f"la ciudad ({resto[0]})"),
                ("./cbc:PostalZone", f"el código postal ({resto[1]})"),
                ("./cbc:CountrySubentity", f"la provincia ({resto[2]})"),
            ]
        faltan = [nombre for sub, nombre in pedidos if not _valor(direccion, sub)]
        if not faltan:
            continue
        incidencias.append(
            Incidencia(
                "SPFE-DIRECCION",
                ERROR,
                f"A la dirección del {quien} le falta {_y(faltan)}. El anexo "
                "pide siempre la calle, y la ciudad, el código postal y la "
                "provincia cuando la dirección está en España.",
                campo=f"Dirección del {quien}",
                esperado=("calle, ciudad, código postal y provincia" if en_espana
                          else "la calle"),
                encontrado=f"falta {_y(faltan)}",
            )
        )
    return incidencias


def _tipo_de_impuesto(raiz) -> list[Incidencia]:
    """El impuesto es «VAT» en los descuentos, los cargos, las líneas y el desglose.

    Lo dicen las filas BT-95, BT-102, BG-30 y BG-23 en su columna de ruta. Y
    tiene que estar: una categoría sin `cac:TaxScheme/cbc:ID` no lo dice.
    """
    lugares: list[str] = []
    malos: list[str] = []
    for ruta, lugar in _CATEGORIAS_CON_IMPUESTO:
        for categoria in _nodos(raiz, ruta):
            escritos = _nodos(categoria, "./" + _ESQUEMA_DE_LA_CATEGORIA)
            escrito = (_escrito(escritos[0]) or "(vacío)") if escritos else "(falta)"
            if escrito == _IMPUESTO:
                continue
            if lugar not in lugares:
                lugares.append(lugar)
            if escrito not in malos:
                malos.append(escrito)
    if not malos:
        return []
    return [
        Incidencia(
            "SPFE-TIPO-DE-IMPUESTO",
            ERROR,
            f"El tipo de impuesto no es {_IMPUESTO} o no está. La orden lo fija en "
            f"{_IMPUESTO} en los descuentos y cargos del documento, en cada "
            "línea y en el desglose (filas BT-95, BT-102, BG-30 y BG-23); el "
            "IGIC y el IPSI tienen su propia categoría en la lista L4, la L y "
            "la M.",
            campo=_donde("Tipo de impuesto (cac:TaxScheme/cbc:ID)", lugares),
            esperado=_IMPUESTO,
            encontrado=", ".join(malos),
        )
    ]


def _tercero(raiz) -> list[Incidencia]:
    """El tercero, si está: su nombre, su NIF y su tipología (BG-ES-1).

    El nombre va en la razón social, `cac:PartyLegalEntity/cbc:RegistrationName`
    (BT-ES-3), y el NIF, con «VAT», o con «LOC» y el atributo «FC», como el del
    vendedor (BT-ES-4). La ruta que la orden da a la tipología (BT-ES-5) no
    existe en UBL, y se lee donde sí: `sintaxis._ARREGLOS` dice por qué.
    """
    incidencias: list[Incidencia] = []
    for nombre, tercero in _nombrados(_nodos(raiz, _TERCERO), "tercero"):
        faltan = []
        if not _valor(tercero, _TERCERO_NIF):
            faltan.append("el NIF (BT-ES-4)")
        if not _valor(tercero, _TERCERO_NOMBRE):
            faltan.append("el nombre o razón social (BT-ES-3)")
        if not _valor(tercero, _TERCERO_TIPO):
            if _valor(tercero, _TERCERO_TIPO_DE_LA_ORDEN):
                faltan.append(
                    "la tipología (BT-ES-5) donde UBL la admite, en "
                    "cac:ServiceProviderParty/cbc:ServiceTypeCode: está en su "
                    "cac:Party, que es la ruta que escribe la orden y el esquema "
                    "no admite")
            else:
                faltan.append("la tipología (BT-ES-5)")
        esquemas = _nodos(tercero, _TERCERO_ESQUEMAS)
        if _valor(tercero, _TERCERO_NIF) and not any(_nif_bien_puesto(e) for e in esquemas):
            impuesto = _valor(tercero, _TERCERO_IMPUESTO)
            faltan.append(f"el impuesto {_IMPUESTO}, o {_IMPUESTO_LOCAL} con el "
                          f"atributo {_ESQUEMA_DEL_NIF} (hay {entre_comillas(impuesto, '(nada)')})")
        if not faltan:
            continue
        incidencias.append(
            Incidencia(
                "SPFE-TERCERO",
                ERROR,
                f"Al tercero que expide la factura le falta {_y(faltan)}. Si "
                "el grupo del tercero está, la orden pide su nombre o razón "
                f"social, su NIF (con el impuesto {_IMPUESTO}, o con "
                f"{_IMPUESTO_LOCAL} y el atributo {_ESQUEMA_DEL_NIF}) y la "
                "tipología del tercero.",
                campo=_donde("Datos del tercero (BG-ES-1)", [nombre]),
                esperado="nombre, NIF con su impuesto y tipología",
                encontrado=f"falta {_y(faltan)}",
            )
        )
    return incidencias


def _facturas_referenciadas(raiz) -> list[Incidencia]:
    """BT-26: la fecha de la factura referenciada, opcional en la norma."""
    sin_fecha = []
    for n, referencia in enumerate(
        _nodos(raiz, SINTAXIS_UBL.facturas_previas + "/cac:InvoiceDocumentReference"), start=1
    ):
        if not _valor(referencia, "./cbc:IssueDate"):
            sin_fecha.append(_valor(referencia, "./cbc:ID") or f"la referencia {n}")
    if not sin_fecha:
        return []
    return [
        Incidencia(
            "SPFE-FACTURA-REFERENCIADA",
            ERROR,
            "Una factura referenciada no lleva su fecha de expedición. La norma "
            "europea la deja opcional; el anexo la hace obligatoria, junto con "
            "el número.",
            campo="Fecha de expedición de la factura referenciada (BT-26)",
            esperado="cbc:IssueDate en cada factura referenciada",
            encontrado="sin fecha: " + ", ".join(sin_fecha),
        )
    ]


def _motivos(raiz) -> list[Incidencia]:
    """BT-97, BT-104, BT-139 y BT-144: el motivo en texto, no solo su código."""
    lugares: list[str] = []
    for grupo, _codigo in _MOTIVOS:
        for nombre, ajuste in grupos(raiz, SINTAXIS_UBL, grupo):
            if not _valor(ajuste, SINTAXIS_UBL.cargo_motivo):
                lugares.append(nombre)
    if not lugares:
        return []
    return [
        Incidencia(
            "SPFE-MOTIVO",
            ERROR,
            "Hay descuentos o cargos sin el motivo escrito. La norma europea se "
            "conforma con el motivo o con su código; el anexo pide el texto "
            "siempre.",
            campo=_donde("Motivo (BT-97, BT-104, BT-139, BT-144)", lugares),
            esperado="el motivo en texto (cbc:AllowanceChargeReason)",
            encontrado="(falta)",
        )
    ]


def _categorias(raiz) -> list[Incidencia]:
    """BT-95, BT-102, BT-118 y BT-151 contra la lista L4.

    Solo los códigos que la norma europea admite: de los demás ya se quejan
    BR-CL-17 y BR-CL-18. Aquí quedan los que la norma tiene y el anexo quita.
    """
    europeas = lista("UNCL_5305", SINTAXIS_UBL)
    lugares: list[str] = []
    malos: list[str] = []
    nuevas: list[str] = []
    for grupo, campo in _CATEGORIAS_EN:
        for nombre, nodo in grupos(raiz, SINTAXIS_UBL, grupo):
            for encontrado in _nodos(nodo, getattr(SINTAXIS_UBL, campo)):
                codigo = _escrito(encontrado)
                if codigo in _L4_QUE_LA_NORMA_NO_TIENE:
                    if codigo not in nuevas:
                        nuevas.append(codigo)
                    continue
                if codigo in _CATEGORIAS or codigo not in europeas:
                    continue
                lugar = nombre or ("desglose" if grupo == "desglose" else "")
                if lugar not in lugares:
                    lugares.append(lugar)
                if codigo not in malos:
                    malos.append(codigo)
    incidencias: list[Incidencia] = []
    if malos:
        mensaje = ("La categoría de IVA es de la norma europea, pero no de la "
                   "lista L4 de la orden.")
        if "K" in malos:
            mensaje += " La K, la entrega intracomunitaria, no tiene código en L4."
        if "B" in malos:
            mensaje += " La B, el pago fraccionado italiano, tampoco."
        incidencias.append(
            Incidencia(
                "SPFE-CATEGORIA",
                ERROR,
                mensaje,
                campo=_donde("Categoría de IVA (BT-95, BT-102, BT-118, BT-151)", lugares),
                esperado=_o(_L["L4"].valores),
                encontrado=", ".join(malos),
            )
        )
    if nuevas:
        # Lo que se aceptó y con qué base: la L4 de la orden. Hasta el
        # 07-10-2026 la N salía con dos ERROR de la norma, BR-CL-17 y
        # BR-CL-18, y dos AVISO de la casa, IVA-CATEGORIA-RARA e IVA-TIPO (el
        # 5,2% del recargo «no es un tipo vigente en España»). Medido con una
        # línea y un desglose de recargo de equivalencia escritos como la orden.
        incidencias.append(
            Incidencia(
                "SPFE-CATEGORIA",
                NOTA,
                f"La factura usa {_y(nuevas)} como categoría de IVA. Están en la "
                "lista L4 de la orden publicada en el BOE el 05-10-2026, que trae "
                "las categorías de la edición de 2026 de la norma europea, y no "
                "en la de la edición de 2017, con la que se miden aquí BR-CL-17 y "
                "BR-CL-18 y avisan IVA-CATEGORIA-RARA e IVA-TIPO. Se aceptan, y "
                "esas cuatro reglas no se les han aplicado. Su base tampoco se ha "
                "comparado con las líneas: en "
                "la N la orden la desliga (el grupo de entidades la informa a "
                "coste y el recargo no tiene línea propia), y en la D y la F puede "
                "ser el margen. Su cuota con su base y su tipo, y la suma de "
                "todas, sí. Lo que la edición de 2026 les pida no se ha "
                "comprobado.",
                campo="Categoría de IVA (BT-95, BT-102, BT-118, BT-151)",
                encontrado=", ".join(nuevas),
            )
        )
    return incidencias


def _tipo_del_desglose(raiz) -> list[Incidencia]:
    """BT-119 en la entrada no sujeta: la norma la deja sin tipo y la orden no.

    En las demás categorías el tipo es obligatorio también en la norma, y que
    falte lo dice BR-48: dos quejas por lo mismo no dicen más que una. Medido
    el 11-10-2026: una entrada O con tipo no hace saltar ninguna regla de la
    norma, así que lo que la orden pide se puede cumplir sin romper nada.
    """
    sin_tipo = [nombre or "desglose" for nombre, entrada in grupos(raiz, SINTAXIS_UBL, "desglose")
                if _valor(entrada, SINTAXIS_UBL.desglose_categoria) == _NO_SUJETA
                and not _valor(entrada, SINTAXIS_UBL.desglose_tipo)]
    if not sin_tipo:
        return []
    return [
        Incidencia(
            "SPFE-TIPO-DE-IVA",
            ERROR,
            f"La entrada no sujeta del desglose ({_NO_SUJETA}) no lleva tipo de "
            "IVA. La norma europea lo deja sin tipo en lo no sujeto (BR-48), y la "
            "orden lo pide en todas las entradas del desglose (fila BT-119, "
            "obligatoria).",
            campo=_donde("Tipo de IVA por categoría (BT-119)", sin_tipo),
            esperado="un tipo en cac:TaxCategory/cbc:Percent",
            encontrado="(falta)",
        )
    ]


def _exenciones(raiz) -> list[Incidencia]:
    """BT-121: el código de exención, solo VATEX-EU o VATEX-ES.

    La lista CEF-VATEX tiene también los de otros países, como los VATEX-FR, y
    la norma los admite (BR-CL-22). Mayúsculas o minúsculas como allí: la
    comparación es en mayúsculas.
    """
    otros: list[str] = []
    lugares: list[str] = []
    for nombre, entrada in grupos(raiz, SINTAXIS_UBL, "desglose"):
        codigo = _valor(entrada, SINTAXIS_UBL.desglose_motivo_codigo)
        if codigo and not codigo.upper().startswith(_EXENCIONES):
            otros.append(codigo)
            if nombre:
                lugares.append(nombre)
    if not otros:
        return []
    return [
        Incidencia(
            "SPFE-EXENCION",
            ERROR,
            "El código de exención no es de los que admite la orden, que solo "
            "acepta los VATEX-EU y los VATEX-ES de la lista CEF-VATEX (fila "
            "BT-121). Los de otros países son de su IVA, no del español.",
            campo=_donde("Código de razón de exención (BT-121)", lugares),
            esperado="un código VATEX-EU- o VATEX-ES-",
            encontrado=", ".join(dict.fromkeys(otros)),
        )
    ]


def _se_mide_con_el_anexo(raiz, deteccion) -> bool:
    """Si a esta factura se le aplican las reglas del anexo, y no solo la queja de ser otra cosa.

    Hace falta las tres cosas: que declare la solución pública, que sea UBL y
    que sea una factura (`Invoice`). Un abono declara lo mismo y es UBL, pero
    `reglas` se para en él con SPFE-TIPO-DE-FACTURA y no le mide nada más del
    anexo. Las dos funciones de abajo miraban solo las dos primeras, y el
    abono recibía la L4 de la orden sin la NOTA que lo dice: lo vio la
    revisión del 07-10-2026, antes de publicar.
    """
    return (declara_el_cius(deteccion) and deteccion.familia == UBL
            and raiz is not None and raiz.xpath("local-name()") == "Invoice")


def categorias_que_la_norma_no_tiene(raiz, deteccion) -> frozenset[str]:
    """Las categorías de la L4 de la orden que la lista de 2017 no tiene.

    Solo para una factura UBL que declara la solución pública: a esa se le
    mide con la L4 de la orden, y las reglas europeas que miran la categoría
    (BR-CL-17, BR-CL-18 y los avisos de IVA) no pueden darla por mala por
    usar una que la orden admite. A cualquier otra, nada: fuera de la
    solución pública rige la lista de la norma, como decidió el titular el
    11-10-2026. Al abono, tampoco: no se le mide con el anexo
    (`_se_mide_con_el_anexo`).
    """
    if not _se_mide_con_el_anexo(raiz, deteccion):
        return frozenset()
    return _L4_QUE_LA_NORMA_NO_TIENE


def bt47_de_la_orden(raiz, deteccion) -> tuple[str, ...]:
    """Dónde pone la orden el registro del comprador (BT-47), si es de la solución pública.

    La fila BT-47 de la orden lo pone en un `cac:PartyTaxScheme` con «LOC» y el
    atributo «FC» en el NIF, y la vinculación de 2017 en
    `cac:PartyLegalEntity/cbc:CompanyID`. Se cuenta para BR-AE-02, que pide
    uno u otro identificador del comprador, y solo en una factura UBL que
    declara la solución pública: en las demás, BT-47 es el de la norma. Que
    la regla europea lea BT-47 donde lo pone la orden es la lectura que no
    condena lo que el texto admite; la otra, que la orden rotuló mal su fila,
    también se puede sostener, y por eso se dice aquí y en el README.

    «LOC» y «FC» se comparan sin los espacios de alrededor, con
    `normalize-space`, porque así los lee `_nif_bien_puesto` —con `_valor`,
    como todo este módulo— y así lee la vinculación de 2017 el «VAT» de BT-48.
    Se comparaban exactos, y un espacio tras «FC» daba el NIF por bien puesto
    en SPFE-NIF y al comprador por no identificado en BR-AE-02, en el mismo
    informe: lo vio la revisión del 07-10-2026, antes de publicar.
    """
    if not _se_mide_con_el_anexo(raiz, deteccion):
        return ()
    return (f"{_ESQUEMAS_DEL_COMPRADOR}"
            f"[normalize-space(cac:TaxScheme/cbc:ID)='{_IMPUESTO_LOCAL}']"
            f"[normalize-space(cbc:CompanyID/@schemeID)='{_ESQUEMA_DEL_NIF}']/cbc:CompanyID",)


def _codigos_l9(sin: list[str], otros: list[tuple[str, str]], fila: str,
                donde: str, que: str) -> list[Incidencia]:
    """Lo que falta o no es de L9 en el código de un impuesto o tasa."""
    incidencias: list[Incidencia] = []
    campo = f"Código del tipo de impuesto o tasa ({fila})"
    if sin:
        incidencias.append(
            Incidencia(
                "SPFE-IMPUESTO-O-TASA",
                ERROR,
                f"Hay {que} sin el código del impuesto o tasa de la lista L9. La "
                f"orden lo pide en cada uno (fila {fila}, obligatoria), y para lo "
                "que no es un impuesto ni una tasa tiene el código RESTO. La norma europea "
                "no lo tiene.",
                campo=_donde(campo, sin),
                esperado=f"un código de la lista L9 en {donde}",
                encontrado="(falta)",
            )
        )
    if otros:
        incidencias.append(
            Incidencia(
                "SPFE-IMPUESTO-O-TASA",
                ERROR,
                f"Hay {que} con un código de impuesto o tasa que no es de la lista "
                f"L9 de la orden (fila {fila}).",
                campo=_donde(campo, list(dict.fromkeys(lugar for lugar, _ in otros))),
                esperado=_o(_L9),
                encontrado=", ".join(dict.fromkeys(codigo for _, codigo in otros)),
            )
        )
    return incidencias


def _impuestos_de_los_cargos_de_linea(raiz) -> list[Incidencia]:
    """BT-ES-22: el código de L9 de cada cargo de línea, obligatorio en todos.

    La norma no lo tiene. Los descuentos de línea no lo llevan: el grupo BG-27
    de la orden no tiene ningún código de impuesto.
    """
    sin: list[str] = []
    otros: list[tuple[str, str]] = []
    for nombre, cargo in grupos(raiz, SINTAXIS_UBL, "cargos_linea"):
        codigos = [codigo for codigo in (_escrito(n) for n in _nodos(cargo, _CODIGO_DEL_CARGO_DE_LINEA))
                   if codigo]
        if not codigos:
            sin.append(nombre)
        otros.extend((nombre, codigo) for codigo in codigos if codigo not in _L9)
    return _codigos_l9(sin, otros, "BT-ES-22", "cac:TaxCategory/cac:TaxScheme/cbc:TaxTypeCode",
                       "cargos de línea")


def _impuestos_de_los_cargos(raiz) -> list[Incidencia]:
    """BG-ES-2: el impuesto o tasa que se cobra como un cargo del documento.

    Un cargo lo lleva si trae un `cac:TaxTotal`, y con él su desglose: el
    código de L9 en cada impuesto (BT-ES-9) y la cuota (BT-ES-8), que es la
    base por el tipo cuando la factura da los dos y que va también en el total
    del cargo. Con más de un impuesto en el cargo eso no se puede cumplir, y se
    dice.
    """
    incidencias: list[Incidencia] = []
    sin: list[str] = []
    otros: list[tuple[str, str]] = []
    distintas: list[tuple[str, str, str]] = []
    varios: list[tuple[str, int]] = []
    for nombre, cargo in grupos(raiz, SINTAXIS_UBL, "cargos_documento"):
        impuestos = _nodos(cargo, _IMPUESTOS_DEL_CARGO)
        if not impuestos and _nodos(cargo, _CUOTA_DEL_CARGO):
            # El total del impuesto sin su detalle: la cuota en una sola de sus
            # dos rutas, y nada que diga qué impuesto es. Pasaba sin una queja
            # hasta el 11-10-2026; lo destapó quitar cada elemento, uno a uno.
            sin.append(nombre)
        for numero, impuesto in _nombrados(impuestos, "impuesto"):
            lugar = f"{numero} del {nombre}" if numero else nombre
            codigo = _valor(impuesto, _DEL_IMPUESTO_DEL_CARGO["BT-ES-9"])
            if not codigo:
                sin.append(lugar)
            elif codigo not in _L9:
                otros.append((lugar, codigo))
            incidencias.extend(_cuota_del_impuesto(
                "BT-ES-8", lugar,
                a_decimal(_valor(impuesto, _DEL_IMPUESTO_DEL_CARGO["BT-ES-6"])),
                a_decimal(_valor(impuesto, _DEL_IMPUESTO_DEL_CARGO["BT-ES-7"])),
                a_decimal(_valor(impuesto, _CUOTA_DEL_IMPUESTO_DEL_CARGO))))
        if len(impuestos) > 1:
            varios.append((nombre, len(impuestos)))
        elif impuestos:
            cuota = _valor(impuestos[0], _CUOTA_DEL_IMPUESTO_DEL_CARGO)
            total = _valor(cargo, _CUOTA_DEL_CARGO)
            if (a_decimal(cuota) is not None and a_decimal(total) is not None
                    and not cuadra_exacto(a_decimal(cuota), a_decimal(total))):
                distintas.append((nombre, cuota, total))
    incidencias[:0] = _codigos_l9(sin, otros, "BT-ES-9",
                                  "cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:TaxTypeCode",
                                  "cargos del documento con un impuesto o tasa")
    for nombre, cuota, total in distintas:
        incidencias.append(
            Incidencia(
                "SPFE-IMPUESTO-O-TASA",
                ERROR,
                "La cuota del impuesto o tasa del cargo no es la misma en sus dos "
                "sitios. La orden pide el mismo importe en el impuesto y en el "
                "total del cargo (fila BT-ES-8): cac:TaxTotal/cac:TaxSubtotal/"
                "cbc:TaxAmount y cac:TaxTotal/cbc:TaxAmount.",
                campo=_donde("Cuota del impuesto o tasa (BT-ES-8)", [nombre]),
                esperado="el mismo importe en los dos",
                encontrado=f"{cifras.tiene(a_decimal(cuota))} en el impuesto y "
                           f"{cifras.tiene(a_decimal(total))} en el total",
            )
        )
    for nombre, cuantos in varios:
        incidencias.append(
            Incidencia(
                "SPFE-IMPUESTO-O-TASA",
                NOTA,
                f"El cargo lleva {cuantos} impuestos o tasas (BG-ES-2). La orden pide "
                "la cuota de cada uno (BT-ES-8) también en el total del cargo, "
                "cac:TaxTotal/cbc:TaxAmount, que es uno por cargo: con más de un "
                "impuesto no se puede cumplir al pie de la letra. Se le preguntó a "
                "la Agencia el 07-10-2026 si ahí va la suma, y hasta que conteste "
                "no se compara.",
                campo=_donde("Cuota del impuesto o tasa (BT-ES-8)", [nombre]),
                encontrado=f"{cuantos} impuestos",
            )
        )
    return incidencias


def _impuestos_de_los_cobros(raiz) -> list[Incidencia]:
    """BG-ES-3: el desglose de un impuesto o tasa cobrado en nombre de un tercero.

    Va en la línea de cobro, con «VAT» y «S» aunque no sea el IVA, porque así
    lo pide el grupo («Su uso implica…»), y con la cuota (BT-ES-14), que es la
    base por el tipo cuando la factura da los dos.
    """
    incidencias: list[Incidencia] = []
    malos: list[tuple[str, str]] = []
    for nombre, linea in _nombrados(_nodos(raiz, _LINEA_DE_COBRO), "línea de cobro"):
        for numero, impuesto in _nombrados(_nodos(linea, _IMPUESTOS_DEL_COBRO), "impuesto"):
            lugar = " de la ".join(x for x in (numero, nombre) if x)
            esquema = _valor(impuesto, _ESQUEMA_DEL_IMPUESTO_DEL_COBRO)
            categoria = _valor(impuesto, _CATEGORIA_DEL_IMPUESTO_DEL_COBRO)
            if (esquema, categoria) != (_ESQUEMA_DEL_COBRO, _CATEGORIA_DEL_COBRO):
                malos.append((lugar, f"{esquema or '(falta)'} y {categoria or '(falta)'}"))
            incidencias.extend(_cuota_del_impuesto(
                "BT-ES-14", lugar,
                a_decimal(_valor(impuesto, _DEL_IMPUESTO_DEL_COBRO["BT-ES-12"])),
                a_decimal(_valor(impuesto, _DEL_IMPUESTO_DEL_COBRO["BT-ES-13"])),
                a_decimal(_valor(impuesto, _DEL_IMPUESTO_DEL_COBRO["BT-ES-14"]))))
    if malos:
        incidencias.insert(0, Incidencia(
            "SPFE-IMPUESTO-O-TASA",
            ERROR,
            "El desglose de un impuesto o tasa cobrado en nombre de un tercero "
            f"(BG-ES-3) no lleva {_ESQUEMA_DEL_COBRO} y {_CATEGORIA_DEL_COBRO}. "
            "La orden los pide así aunque no sea el IVA: dice que su uso implica que "
            f"cac:TaxScheme/cbc:ID tome {_ESQUEMA_DEL_COBRO} y cac:TaxCategory/"
            f"cbc:ID, {_CATEGORIA_DEL_COBRO}.",
            campo=_donde("Desglose de impuestos y tasas (BG-ES-3)",
                         [lugar for lugar, _ in malos]),
            esperado=f"{_ESQUEMA_DEL_COBRO} y {_CATEGORIA_DEL_COBRO}",
            encontrado=", ".join(dict.fromkeys(escrito for _, escrito in malos)),
        ))
    return incidencias


def _informacion_adicional(raiz) -> list[Incidencia]:
    """BT-160: el nombre de cada propiedad del artículo, de la lista L8.

    La norma deja el nombre libre («Color», «Lote»). La orden escribe la
    información adicional de la línea con el nombre fijo «INFO» y el texto en
    el valor, y las otras dos propiedades que admite son la clave de régimen y
    la referencia catastral. Con el calificador de L8 delante o sin él, como
    las otras dos. Un nombre vacío lo dice BR-54.

    Hasta el 12-10-2026 era un ERROR, y lo vio el auditor: la factura que se
    emite con la solución pública se ajusta al anexo I (apartado 2 del
    artículo 3), pero la interconectada lo lleva «como mínimo» y puede
    incluir contenido adicional que cumpla la norma europea (apartado 3), que
    deja el nombre libre. Desde el fichero no se sabe por cuál de las dos va:
    es un aviso.
    """
    otros: list[str] = []
    lugares: list[str] = []
    for nombre, linea in grupos(raiz, SINTAXIS_UBL, "lineas"):
        for propiedad in _nodos(linea, _PROPIEDADES):
            escrito = _valor(propiedad, "./cbc:Name")
            if escrito and escrito.removeprefix(_CALIFICADOR_L8) not in _NOMBRES_L8:
                otros.append(escrito)
                if nombre not in lugares:
                    lugares.append(nombre)
    if not otros:
        return []
    return [
        Incidencia(
            "SPFE-INFORMACION-ADICIONAL",
            AVISO,
            "Hay propiedades del artículo con un nombre que no es de la lista L8. "
            "La orden escribe la información adicional de la línea como una "
            "propiedad llamada INFO, con el texto en el valor (fila BT-160, "
            "valor fijo); las otras dos que admite son la clave de régimen "
            "(REGI) y la referencia catastral (RCAT). Si la factura se emite "
            "con la solución pública, su contenido se ajusta al anexo I (apartado "
            "2 del artículo 3) y esto no cabe. Si va interconectada, la orden "
            "admite contenido adicional que cumpla la norma europea (apartado 3), "
            "y la norma deja el nombre libre: por eso es un aviso.",
            campo=_donde("Código de la propiedad (BT-160)", lugares),
            esperado=f"{_o(_NOMBRES_L8)}, con el calificador de L8 delante o sin él",
            encontrado=", ".join(dict.fromkeys(otros)),
        )
    ]


def _claves_de_regimen(raiz) -> list[Incidencia]:
    """BG-32 «CLAVE DE RÉGIMEN»: una o dos en cada línea, cada una en su lista.

    Las listas son las de la orden: la L3A ya no tiene las claves 18, 19 y 20
    del borrador de abril (el recargo de equivalencia, el de agricultura,
    ganadería y pesca y el simplificado), y una línea con ellas en el IVA
    sale aquí, como cualquier otra clave que no es de su lista.
    """
    sin_clave: list[str] = []
    demasiadas: list[str] = []
    calificadores: list[tuple[str, str]] = []
    claves: list[tuple[str, str]] = []
    for nombre, linea in grupos(raiz, SINTAXIS_UBL, "lineas"):
        propiedades = _propiedades(linea, "REGI")
        if not propiedades:
            sin_clave.append(nombre)
        elif len(propiedades) > 2:
            demasiadas.append(nombre)
        for propiedad in propiedades:
            calificador = _valor(propiedad, _CALIFICADOR)
            clave = _valor(propiedad, SINTAXIS_UBL.atributo_valor)
            if calificador not in _REGIMENES:
                calificadores.append((nombre, calificador or "(falta)"))
            elif clave not in _L[_REGIMENES[calificador]].valores:
                claves.append((nombre, f"{clave or '(falta)'} de {calificador}"))

    incidencias: list[Incidencia] = []
    if sin_clave:
        incidencias.append(
            Incidencia(
                "SPFE-CLAVE-DE-REGIMEN",
                ERROR,
                "Hay líneas sin clave de régimen. La orden la pide en cada "
                "línea, como una propiedad del artículo llamada REGI (sola o "
                "con el calificador de la lista L8 delante): la clave en el "
                "valor y el impuesto (IVA, IGIC o IPSI) en el calificador.",
                campo=_donde("Clave de régimen (BG-32)", sin_clave),
                esperado="cac:AdditionalItemProperty con cbc:Name REGI",
                encontrado="(falta)",
            )
        )
    if demasiadas:
        incidencias.append(
            Incidencia(
                "SPFE-CLAVE-DE-REGIMEN",
                ERROR,
                "Hay líneas con más de dos claves de régimen, y el anexo admite "
                "una o dos por línea.",
                campo=_donde("Clave de régimen (BG-32)", demasiadas),
                esperado="una o dos",
                encontrado="más de dos",
            )
        )
    if calificadores:
        incidencias.append(
            Incidencia(
                "SPFE-CLAVE-DE-REGIMEN",
                ERROR,
                "El impuesto de la clave de régimen no es IVA, IGIC ni IPSI, "
                "que son los tres que tienen lista de claves en la orden.",
                campo=_donde("Impuesto de la clave de régimen (BT-ES-24)",
                             [n for n, _ in calificadores]),
                esperado="IVA, IGIC o IPSI",
                encontrado=", ".join(dict.fromkeys(c for _, c in calificadores)),
            )
        )
    if claves:
        incidencias.append(
            Incidencia(
                "SPFE-CLAVE-DE-REGIMEN",
                ERROR,
                "La clave de régimen no está en la lista de su impuesto. Cada "
                "impuesto tiene la suya: la 17 existe en el IGIC y no en el "
                "IVA, y la 02 en el IVA y no en el IPSI. Y la orden quitó del "
                "IVA la 18, la 19 y la 20, que el borrador de abril tenía.",
                campo=_donde("Clave de régimen (BT-161)", [n for n, _ in claves]),
                esperado="una clave de L3A (IVA), L3B (IGIC) o L3C (IPSI)",
                encontrado=", ".join(dict.fromkeys(c for _, c in claves)),
            )
        )
    return incidencias


def _referencias_catastrales(raiz) -> list[Incidencia]:
    """BG-32 «REFERENCIA CATASTRAL»: como mucho una por línea, completa."""
    incidencias: list[Incidencia] = []
    repetidas: list[str] = []
    incompletas: list[str] = []
    situaciones: list[tuple[str, str]] = []
    for nombre, linea in grupos(raiz, SINTAXIS_UBL, "lineas"):
        propiedades = _propiedades(linea, "RCAT")
        if len(propiedades) > 1:
            repetidas.append(nombre)
        for propiedad in propiedades:
            if not _valor(propiedad, SINTAXIS_UBL.atributo_valor):
                incompletas.append(nombre)
            situacion = _valor(propiedad, _CALIFICADOR)
            if situacion not in _L["L6"].valores:
                situaciones.append((nombre, situacion or "(falta)"))
    if repetidas:
        incidencias.append(
            Incidencia(
                "SPFE-REFERENCIA-CATASTRAL",
                ERROR,
                "Hay líneas con más de una referencia catastral, y el anexo "
                "admite una por línea.",
                campo=_donde("Referencia catastral (BG-32)", repetidas),
                esperado="una como mucho",
                encontrado="más de una",
            )
        )
    if incompletas:
        incidencias.append(
            Incidencia(
                "SPFE-REFERENCIA-CATASTRAL",
                ERROR,
                "Hay una propiedad RCAT sin la referencia catastral. Si el "
                "grupo está, el anexo pide la referencia en el valor.",
                campo=_donde("Referencia catastral (BT-161)", incompletas),
                esperado="la referencia en cbc:Value",
                encontrado="(falta)",
            )
        )
    if situaciones:
        incidencias.append(
            Incidencia(
                "SPFE-REFERENCIA-CATASTRAL",
                ERROR,
                "La situación del inmueble no es un código de la lista L6 del "
                "anexo.",
                campo=_donde("Situación del inmueble (BT-ES-23)", [n for n, _ in situaciones]),
                esperado=_o(_L["L6"].valores),
                encontrado=", ".join(dict.fromkeys(s for _, s in situaciones)),
            )
        )
    return incidencias


def _lineas_de_cobro(raiz) -> list[Incidencia]:
    """La lista L7, y una sola línea de retenciones."""
    incidencias: list[Incidencia] = []
    identificadores = [_escrito(n) for n in _nodos(raiz, _LINEA_DE_COBRO + "/cbc:ID")]
    desconocidos = [i or "(vacío)" for i in identificadores if not _cobro(i)]
    if desconocidos:
        incidencias.append(
            Incidencia(
                "SPFE-LINEA-DE-COBRO",
                ERROR,
                "Una línea de cobro no se identifica con ningún valor de la "
                "lista L7 de la orden, que tiene cinco: suplido (SUPL), "
                "minoración (MINO), retención (RETE), el impuesto especial "
                "sobre determinados medios de transporte (IEDMT) y otros "
                "impuestos o tasas (OTROS), solos o con su calificador delante. "
                "Las líneas del recargo de equivalencia (REEQ) y del grupo de "
                "entidades (REGE) eran del borrador de abril: la orden pone los "
                "dos regímenes en el desglose del IVA, con la categoría N.",
                campo="Identificación de la línea de cobro (CollectionInvoiceLine/cbc:ID)",
                esperado=f"{_o(_L7)}, o con {_CALIFICADOR_L7} delante",
                encontrado=", ".join(dict.fromkeys(desconocidos)),
            )
        )
    valores = [_cobro(i) for i in identificadores]
    repetidos = [
        termino.lower() for clave, termino in _UNO_POR_FACTURA.items()
        if valores.count(clave) > 1
    ]
    if repetidos:
        incidencias.append(
            Incidencia(
                "SPFE-LINEA-DE-COBRO",
                ERROR,
                f"Hay más de un grupo de {_y(repetidos)}, y el anexo admite uno "
                "por factura.",
                campo="Líneas de cobro (BG-34)",
                esperado="uno como mucho",
                encontrado="más de uno",
            )
        )
    return incidencias


def _retenciones(raiz) -> list[Incidencia]:
    """Las retenciones: la línea que las identifica, su total y cada una."""
    faltan: list[str] = []
    # Por su valor de L7, y no por una ruta con el valor dentro: una línea RETE
    # escrita con el calificador o sin él es la misma línea.
    lineas = _cobros(raiz, "RETE")
    totales = _nodos(raiz, _RETENCIONES)
    if lineas and not _valor(raiz, _RETENCION_TOTAL):
        faltan.append("la suma de retenciones (BT-ES-17)")
    if totales and not lineas:
        faltan.append("la línea de cobro que identifica la retención (BT-ES-16)")
    for nombre, subtotal in _nombrados(_nodos(raiz, _RETENCIONES_APLICADAS), "retención"):
        sufijo = f" de la {nombre}" if nombre else ""
        for ruta, texto, fijo, identificador in (
            (_RETENCION_HIJOS["BT-ES-18"], "la base", None, "BT-ES-18"),
            (_RETENCION_HIJOS["BT-ES-19"], "el importe", None, "BT-ES-19"),
            (_RETENCION_CATEGORIA, f"la categoría {_CATEGORIA_DE_LA_RETENCION}",
             _CATEGORIA_DE_LA_RETENCION, "BG-ES-4"),
            (_RETENCION_HIJOS["BT-ES-20"], "el porcentaje", None, "BT-ES-20"),
            (_RETENCION_ESQUEMA, f"el esquema {_ESQUEMA_DE_LA_RETENCION}",
             _ESQUEMA_DE_LA_RETENCION, "BG-ES-4"),
        ):
            escrito = _valor(subtotal, ruta)
            if not escrito or (fijo and escrito != fijo):
                faltan.append(f"{texto}{sufijo} ({identificador})")
        concepto = _valor(subtotal, _RETENCION_HIJOS["BT-ES-21"])
        if concepto not in _L["L5"].valores:
            faltan.append(f"un concepto de la lista L5{sufijo} (BT-ES-21, hay {entre_comillas(concepto, '(nada)')})")
    if not faltan:
        return []
    return [
        Incidencia(
            "SPFE-RETENCION",
            ERROR,
            f"A las retenciones les falta {_y(faltan)}. La orden pide la línea "
            "que las identifica, la suma, y en cada retención la base, el "
            f"importe, la categoría {_CATEGORIA_DE_LA_RETENCION}, el "
            f"porcentaje, el esquema {_ESQUEMA_DE_LA_RETENCION} y el concepto "
            "de la lista L5.",
            campo="Retenciones (BG-34, BG-ES-4)",
            esperado="la identificación, la suma y cada retención completa",
            encontrado=f"falta {_y(faltan)}",
        )
    ]


def _cuenta_de_la_cuota(base, tipo, cuota) -> tuple[str, str, str, str] | None:
    """Una cuota que la orden define como la base por el tipo, si no sale.

    La de cada retención (BT-ES-19) y la de cada impuesto o tasa (BT-ES-8 y
    BT-ES-14), que la orden define igual y sin margen. Se les da el de la
    cuota del IVA, que es la misma cuenta (BR-CO-17): hasta una unidad es una
    NOTA que dice cuánto se aparta, y más, un ERROR. Devuelve la gravedad, la
    cuenta escrita, lo calculado y cuánto se aparta; o nada, si cuadra al
    céntimo o falta una cifra, porque que falte lo dice la regla de cada sitio.
    """
    if base is None or tipo is None or cuota is None:
        return None
    # Como BR-CO-17: la base en valor absoluto por el tipo, y el signo después,
    # para que en una rectificativa las mitades vayan hacia el mismo lado que
    # en una factura.
    exacta = abs(base) * tipo / 100
    if redondear(exacta) == abs(cuota):
        return None
    calculada = redondear(exacta) * (-1 if base < 0 else 1)
    cuenta = (f"{cifras.en_castellano(base)} al {cifras.tipo(tipo)} da "
              f"{cifras.calculada(calculada)}")
    if a_menos_de_una_unidad(exacta, cuota):
        distancia = abs(redondear(exacta) - abs(cuota))
        return NOTA, cuenta, cifras.calculada(calculada), cifras.calculada(distancia)
    return ERROR, cuenta, cifras.calculada(calculada), ""


def _sin_dividir_por_cien(base, tipo, cuota) -> str:
    """La cuenta de base por tipo sin dividir por cien, si es justo la cuota.

    Pasa de dos maneras, y desde la factura no se distinguen: el tipo escrito
    como fracción (0,0511 por un 5,11 %) o un impuesto por unidad, con la
    cantidad en la base y el importe por unidad en el tipo. La segunda es la
    de casi toda la lista L9: hidrocarburos, alcohol y tabaco van por litro o
    por mil unidades, y el plástico, a 0,45 euros por kilo (art. 78 de la Ley
    7/2022). La orden define la base como un importe y el tipo como un
    porcentaje, así que ninguna de las dos es como la orden la escribe.
    """
    if base is None or tipo is None or cuota is None:
        return ""
    if redondear(abs(base) * tipo) != abs(cuota):
        return ""
    return (f"{cifras.en_castellano(base)} por {cifras.en_castellano(tipo)} da "
            f"{cifras.calculada(redondear(abs(base) * tipo))}")


def _cuota_del_impuesto(fila: str, lugar: str, base, tipo, cuota) -> list[Incidencia]:
    """La cuenta de la cuota de un impuesto o tasa (BT-ES-8 o BT-ES-14).

    Si la cuota es justo la base por el tipo sin dividir por cien, es ERROR
    aunque se aparte menos de una unidad, y dice las dos causas posibles. Hasta
    el 19-10-2026 el mensaje daba la cuenta y no la causa, y por debajo de una
    unidad era una NOTA que la daba por buena: 1,11 kilos de plástico a 0,45
    euros, con cuota 0,50, salían «dados por buenos» con un error del cien por
    cien (lo midió el auditor del informe de ese día). El margen de BR-CO-17
    es para el redondeo, y esto no lo es.
    """
    cuadre = _cuenta_de_la_cuota(base, tipo, cuota)
    if cuadre is None:
        return []
    gravedad, cuenta, calculada, distancia = cuadre
    sin_cien = _sin_dividir_por_cien(base, tipo, cuota)
    if sin_cien:
        gravedad = ERROR
        mensaje = ("La cuota del impuesto o tasa no sale de aplicar el tipo a la "
                   f"base ({cuenta}), y sí de multiplicarlos sin dividir por cien "
                   f"({sin_cien}). O el tipo está escrito como fracción (0,0511 "
                   "por un 5,11 %), o es un impuesto por unidad, con la cantidad "
                   "en la base y el importe por unidad en el tipo. La orden "
                   f"define la cuota como esa cuenta (fila {fila}), la base como "
                   "un importe y el tipo como un porcentaje: en un impuesto por "
                   "litro, por kilo o por unidad, lo que cabe es dar solo la "
                   "cuota, sin base ni tipo. La cantidad (los kilos de plástico "
                   "no reciclado que pide la Ley 7/2022, por ejemplo) no tiene "
                   "campo en la orden y solo cabe como texto.")
    elif gravedad == NOTA:
        mensaje = (f"La cuota del impuesto o tasa se aparta {distancia} de aplicar "
                   f"el tipo a la base ({cuenta}). La orden la define como esa "
                   "cuenta y no da margen; se ha dado por buena con el de la cuota "
                   "del IVA, que es la misma cuenta (hasta una unidad, BR-CO-17). "
                   "Si no hay redondeo que lo explique, conviene revisarlo.")
    else:
        mensaje = ("La cuota del impuesto o tasa no sale de aplicar el tipo a la "
                   f"base ({cuenta}), que es como la define la orden en la fila "
                   f"{fila}.")
    return [
        Incidencia(
            "SPFE-IMPUESTO-O-TASA",
            gravedad,
            mensaje,
            campo=_donde(f"Cuota del impuesto o tasa ({fila})", [lugar]),
            esperado=calculada,
            encontrado=cifras.tiene(cuota),
        )
    ]


def _cuadre_de_las_retenciones(raiz) -> list[Incidencia]:
    """Las dos cuentas que la orden define: cada retención (BT-ES-19) y su suma (BT-ES-17).

    Cada retención es el «resultado de aplicar a la base imponible de la
    retención el porcentaje», y la suma, el «sumatorio de todas las retenciones
    practicadas». Hasta el 11-10-2026 se pedía que estuvieran y no se hacía
    ninguna de las dos cuentas: una suma de 999 sobre una retención de 15 salía
    sin una queja, y la nota del alcance no decía que eso no se miraba. Lo vio
    el revisor de promesas.

    La orden no da margen, y aquí se usan los de la norma para lo mismo. Una
    retención es la cuenta de la cuota del IVA con otro porcentaje, y se le da
    el margen de BR-CO-17: hasta una unidad, con una nota que dice cuánto se
    aparta si no cuadra al céntimo, como IVA-CUOTA-REDONDEO. Sin él, una
    retención calculada por líneas y sumada sería un ERROR que la norma no
    pondría en la cuota. La suma es como las de la cabecera (BR-CO-10 a
    BR-CO-16): exacta. Si falta una cifra o no se deja leer, la cuenta no se
    hace; que falte ya lo dice `_retenciones`. Y si la factura da la suma y no
    detalla ninguna retención, que la orden deja en `0..n`, no hay con qué
    compararla: una nota lo dice. Pasaba sin una palabra hasta el 11-10-2026.
    """
    incidencias: list[Incidencia] = []
    importes = []
    for nombre, subtotal in _nombrados(_nodos(raiz, _RETENCIONES_APLICADAS), "retención"):
        base = a_decimal(_valor(subtotal, _RETENCION_HIJOS["BT-ES-18"]))
        importe = a_decimal(_valor(subtotal, _RETENCION_HIJOS["BT-ES-19"]))
        porcentaje = a_decimal(_valor(subtotal, _RETENCION_HIJOS["BT-ES-20"]))
        importes.append(importe)
        cuadre = _cuenta_de_la_cuota(base, porcentaje, importe)
        if cuadre is None:
            continue
        gravedad, cuenta, calculada, distancia = cuadre
        campo = _donde("Total retención (BT-ES-19)", [nombre])
        if gravedad == NOTA:
            incidencias.append(
                Incidencia(
                    "SPFE-RETENCION",
                    NOTA,
                    f"El importe de la retención se aparta {distancia} "
                    f"de aplicar el porcentaje a la base ({cuenta}). La orden lo "
                    "define como esa cuenta y no da margen; se ha dado por bueno "
                    "con el de la cuota del IVA, que es la misma cuenta (hasta una "
                    "unidad, BR-CO-17). Si no hay redondeo por líneas que lo "
                    "explique, conviene revisarlo.",
                    campo=campo,
                    esperado=calculada,
                    encontrado=cifras.tiene(importe),
                )
            )
        else:
            incidencias.append(
                Incidencia(
                    "SPFE-RETENCION",
                    ERROR,
                    "El importe de la retención no sale de aplicar el porcentaje "
                    f"a la base ({cuenta}), que es como lo define la orden en la "
                    "fila BT-ES-19.",
                    campo=campo,
                    esperado=calculada,
                    encontrado=cifras.tiene(importe),
                )
            )
    total = a_decimal(_valor(raiz, _RETENCION_TOTAL))
    if total and not importes:
        incidencias.append(
            Incidencia(
                "SPFE-RETENCION",
                NOTA,
                "La factura da una suma de retenciones y no detalla ninguna "
                "(BG-ES-4). La orden define la suma como el sumatorio de las "
                "retenciones practicadas y deja el detalle en 0..n: sin él no "
                "hay con qué compararla, y no se ha comprobado.",
                campo="Suma de retenciones (BT-ES-17)",
                encontrado=cifras.tiene(total),
            )
        )
    if total is not None and importes and None not in importes:
        suma = sum(importes)
        if not cuadra_exacto(suma, total):
            incidencias.append(
                Incidencia(
                    "SPFE-RETENCION",
                    ERROR,
                    "La suma de retenciones no es la suma de las retenciones de "
                    "la factura, que es como la define la orden en la fila "
                    "BT-ES-17: el sumatorio de todas las retenciones practicadas.",
                    campo="Suma de retenciones (BT-ES-17)",
                    esperado=cifras.calculada(suma),
                    encontrado=cifras.tiene(total),
                )
            )
    return incidencias


def _qr(raiz) -> list[Incidencia]:
    """BG-24 del QR fiscal: uno como mucho, con su dirección y, si la lleva, su descripción.

    La descripción (BT-123) es `0..1` en la orden —en el borrador de abril era
    obligatoria—, y cuando está tiene que ser «VERIFACTU» o «TICKETBAI».
    """
    incidencias: list[Incidencia] = []
    qrs = [adjunto for calificador, adjunto in _adjuntos(raiz) if calificador == "QR"]
    if len(qrs) > _MAXIMO_DE_QR:
        incidencias.append(
            Incidencia(
                "SPFE-QR",
                ERROR,
                "Hay más de un documento del QR fiscal, y el anexo admite uno.",
                campo="QR fiscal (BG-24)",
                esperado="uno como mucho",
                encontrado=str(len(qrs)),
            )
        )
    if any(not _valor(qr, _QR_URL) for qr in qrs):
        incidencias.append(
            Incidencia(
                "SPFE-QR",
                ERROR,
                "Al documento del QR fiscal le falta la dirección del QR. La "
                "orden la pide en cbc:UUID: la URL del QR de VERI*FACTU o de "
                "TicketBAI, según corresponda (BT-ES-25).",
                campo="QR fiscal (BG-24)",
                esperado="cbc:UUID",
                encontrado="(falta)",
            )
        )
    # Un QR escrito con el esquema de abril no es el QR para la orden: ni se le
    # pide la dirección ni cuenta para estar repetido. Pero se dice. Con el
    # identificador de la orden y ese QR sin dirección no salía nada, y la
    # factura parecía llevar un QR que para la orden no lleva. Lo vio el
    # revisor de promesas el 11-10-2026. Nota y no fallo: un BG-24 puede llevar
    # cualquier identificador, y la orden no obliga al QR.
    de_abril = [identificador for adjunto in _nodos(raiz, SINTAXIS_UBL.adjuntos)
                if (identificador := _valor(adjunto, _ID_DEL_DOCUMENTO))
                == ESQUEMA_DEL_BORRADOR + "QR"]
    if de_abril:
        incidencias.append(
            Incidencia(
                "SPFE-QR",
                NOTA,
                "Hay un documento identificado como el QR con el esquema del "
                "borrador de abril, que lleva ubl en el identificador, y la orden ya no. No "
                "se ha leído como el QR fiscal: para la orden, esta factura no "
                "lo trae. El QR va con el valor QR de la lista L10, solo o con su "
                "calificador delante.",
                campo="QR fiscal (BG-24)",
                esperado=f"{_ESQUEMA_L10}QR o QR",
                encontrado=", ".join(dict.fromkeys(de_abril)),
            )
        )
    otros = [d for qr in qrs if (d := _valor(qr, _DESCRIPCION_DEL_DOCUMENTO))
             and d not in _TIPOS_DE_QR]
    if otros:
        incidencias.append(
            Incidencia(
                "SPFE-QR",
                ERROR,
                "La descripción del QR fiscal no es una de las dos que admite la "
                "orden, que dice qué QR es. Se puede dejar sin descripción.",
                campo="Tipo de QR (BT-123)",
                esperado=_o(_TIPOS_DE_QR),
                encontrado=", ".join(dict.fromkeys(otros)),
            )
        )
    return incidencias


def _autorizacion(raiz) -> list[Incidencia]:
    """BG-24 de la autorización de facturación: cada uno con su número (BT-ES-26).

    La orden admite tantos como hagan falta, y en cada uno pide el número de
    referencia de la autorización en cbc:UUID. La descripción (BT-123) es
    libre.
    """
    autorizaciones = [adjunto for calificador, adjunto in _adjuntos(raiz) if calificador == "AUT"]
    sin = [nombre for nombre, adjunto in _nombrados(autorizaciones, "autorización")
           if not _valor(adjunto, _NUMERO_DE_AUTORIZACION)]
    if not sin:
        return []
    return [
        Incidencia(
            "SPFE-AUTORIZACION",
            ERROR,
            "Falta el número de la autorización de facturación. La orden lo "
            "pide en cbc:UUID de cada documento de la autorización (fila "
            "BT-ES-26): el número de referencia de la que concedió la Agencia "
            "Tributaria, la Administración Tributaria Canaria o la Diputación "
            "Foral que corresponda.",
            campo=_donde("Autorización de facturación (BG-24, BT-ES-26)", sin),
            esperado="cbc:UUID",
            encontrado="(falta)",
        )
    ]


def _es_copia(raiz) -> bool:
    """Si el indicador de copia (BT-ES-1) dice que lo es: «True: copia»."""
    return _valor(raiz, _COPIA) in ("true", "1")


def _fichero(nodo) -> str:
    """Un fichero embebido, por su nombre y por el documento en el que va."""
    nombre = nodo.get("filename") or nodo.get("mimeCode") or "un texto"
    documento = nodo.xpath("ancestor::cac:Attachment/../cbc:ID", namespaces=NS_CIUS_ES)
    referencia = _escrito(documento[0]) if documento else ""
    return f"{nombre} en el documento {referencia}" if referencia else nombre


def _ficheros_embebidos(raiz) -> list[Incidencia]:
    """Los ficheros integrados o embebidos, que la orden no deja llevar.

    Ninguno fuera de la firma, sea la factura original o una copia fiel: el
    apartado 6 del artículo 3 lo dice de las emitidas o interconectadas, y el
    apartado 4 del artículo 4, de las copias. Con la firma, el artículo 3 deja
    ir a las interconectadas, y el 4 no dice nada de las copias: si una copia
    fiel la lleva, un aviso. La firma envuelta en el XML (`ds:Signature`) no
    es un fichero pegado, pero es la firma que el artículo 3 exceptúa, y se
    trata igual que la que va en un fichero.
    """
    incidencias: list[Incidencia] = []
    copia = _es_copia(raiz)
    embebidos = _nodos(raiz, _EMBEBIDOS)
    fuera = [nodo for nodo in embebidos if not nodo.xpath(_DENTRO_DE_LA_FIRMA, namespaces=NS_CIUS_ES)]
    if fuera:
        articulo = ("el apartado 4 de su artículo 4, de las copias fieles" if copia else
                    "el apartado 6 de su artículo 3, de las facturas emitidas o "
                    "interconectadas a través de la solución pública")
        incidencias.append(
            Incidencia(
                "SPFE-FICHERO-EMBEBIDO",
                ERROR,
                "La factura lleva un fichero dentro, y la orden no lo admite: dice "
                f"que no podrán incorporar otros ficheros integrados o embebidos ({articulo}). "
                "La norma europea sí lo admite, como documento adjunto (BT-125), y "
                "el anexo I no lo recoge.",
                campo="Fichero embebido (cac:Attachment)",
                esperado="ningún fichero dentro de la factura",
                encontrado=", ".join(dict.fromkeys(_fichero(nodo) for nodo in fuera)),
            )
        )
    if copia:
        firmas = [que for que, hay in (
            ("la firma envuelta (ds:Signature)", raiz.xpath(_FIRMAS_ENVUELTAS, namespaces=_NS_CON_LA_FIRMA)),
            ("la firma en un fichero (cac:Signature)", [n for n in embebidos if n not in fuera]),
        ) if hay]
        if firmas:
            incidencias.append(
                Incidencia(
                    "SPFE-FICHERO-EMBEBIDO",
                    AVISO,
                    "La factura es una copia fiel (BT-ES-1) y lleva la firma "
                    "electrónica. El apartado 4 del artículo 4 de la orden no deja a "
                    "las copias fieles incorporar otros ficheros integrados o "
                    "embebidos, y no hace con la firma la salvedad que el apartado 6 "
                    "del artículo 3 hace con las facturas interconectadas. La orden "
                    "no dice si la firma cuenta como uno de esos ficheros: por eso es "
                    "un aviso y no un error.",
                    campo="Firma electrónica",
                    esperado="la copia fiel sin firma",
                    encontrado=_y(firmas),
                )
            )
    return incidencias


def _total_a_pagar(raiz) -> list[Incidencia]:
    """BT-115 con líneas de cobro: se cuadra si solo hay retenciones, y si no, se dice.

    El anexo suma al total a pagar los importes de BT-179, que no tienen ruta.
    BR-CO-16, que es de la edición de 2017, no los conoce y daba por mal una
    factura bien hecha. `factura._SOBRA_SI` lo quita cuando sale esta queja,
    sea nota o aviso.

    Con las retenciones sí hay cifra: la orden define el BT-179 de su grupo y
    BT-ES-17 con la misma frase, «sumatorio de todas las retenciones
    practicadas en factura», y BT-ES-17 tiene ruta. Hasta el 19-10-2026 no se
    usaba, y un total a pagar de 500,00 en una factura de 121,00 con su
    retención pasaba con la nota y sin una queja (medido ese día, con IRPF y
    con el concepto 11). La orden no escribe el signo, dice «junto con»; se
    resta, porque eso es una retención (lo que el pagador no paga) y porque
    Facturae lo hace igual (`TotalExecutableAmount`, `facturae.py`). Por no
    estar escrito, lo que no cuadra es un AVISO y no un ERROR. Con suplidos,
    minoraciones o impuestos y tasas, cuyo importe no tiene ruta o puede no
    traer el desglose (BG-ES-3 es 0..n), se queda la nota de siempre: medio
    cuadre sería un aviso falso.
    """
    lineas = _nodos(raiz, _LINEA_DE_COBRO)
    if not lineas:
        return []
    a_pagar = _valor(raiz, SINTAXIS_UBL.a_pagar)
    solo_retenciones = {_cobro(_valor(linea, "./cbc:ID")) for linea in lineas} == {"RETE"}
    retenido = a_decimal(_valor(raiz, _RETENCION_TOTAL))
    con_iva = a_decimal(_valor(raiz, SINTAXIS_UBL.con_impuestos))
    pagar = a_decimal(a_pagar)
    # Lo pagado y el redondeo son 0..1: si faltan, cuentan cero; si están y no
    # se dejan leer, la cuenta no se hace.
    pagado = a_decimal(_valor(raiz, SINTAXIS_UBL.anticipos) or "0")
    redondeo = a_decimal(_valor(raiz, SINTAXIS_UBL.redondeo) or "0")
    if solo_retenciones and None not in (retenido, con_iva, pagar, pagado, redondeo):
        sin_retener = con_iva - pagado + redondeo
        esperado = sin_retener - retenido
        cuenta = (f"{cifras.en_castellano(con_iva)} con IVA, menos "
                  f"{cifras.en_castellano(pagado)} pagado, más "
                  f"{cifras.en_castellano(redondeo)} de redondeo y menos "
                  f"{cifras.en_castellano(retenido)} retenido")
        if cuadra_exacto(esperado, pagar):
            return [
                Incidencia(
                    "SPFE-TOTAL-A-PAGAR",
                    NOTA,
                    "El total a pagar cuadra restando las retenciones "
                    f"({cuenta}). La orden lo suma \"junto con\" ellas y no "
                    "escribe el signo; se ha leído como resta, que es lo que "
                    "hace Facturae. La regla europea del total (BR-CO-16), de "
                    "2017, no conoce las retenciones y no se ha aplicado.",
                    campo="Total a pagar (BT-115)",
                    encontrado=a_pagar,
                )
            ]
        olvidada = (" Es justo lo que daría sin la retención: parece que no se "
                    "ha restado." if cuadra_exacto(sin_retener, pagar) else "")
        return [
            Incidencia(
                "SPFE-TOTAL-A-PAGAR",
                AVISO,
                "El total a pagar no cuadra con el total con IVA, lo pagado, "
                f"el redondeo y las retenciones ({cuenta} dan "
                f"{cifras.calculada(esperado)}).{olvidada} La orden suma las "
                "retenciones al total a pagar \"junto con\" lo demás y no "
                "escribe el signo; se han restado, como hace Facturae, y por "
                "eso es un aviso y no un error.",
                campo="Total a pagar (BT-115)",
                esperado=cifras.calculada(esperado),
                encontrado=cifras.tiene(pagar),
            )
        ]
    return [
        Incidencia(
            "SPFE-TOTAL-A-PAGAR",
            NOTA,
            "La factura lleva líneas de cobro (suplidos, minoraciones, "
            "retenciones, o impuestos y tasas cobrados en nombre de un tercero, "
            "como el IEDMT), y la orden suma sus importes al total a pagar "
            "(BT-115). La norma de 2017 no los conoce y la orden no dice dónde "
            "se escriben, así que el cuadre del total a pagar (BR-CO-16) no se "
            "ha comprobado. Con retenciones solas sí se comprueba.",
            campo="Total a pagar (BT-115)",
            encontrado=a_pagar,
        )
    ]
