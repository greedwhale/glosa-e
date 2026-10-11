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

Lo que la orden pide y aquí todavía no se mide está en
`LO_QUE_TODAVIA_NO_SE_MIDE`, y la NOTA `SPFE-ALCANCE` de cada factura lo
dice: que no salga ninguna queja no quiere decir que la factura cumpla la
orden.

Lo que la orden no dice y aquí se decide
----------------------------------------
- **Cómo se juntan el calificador y el valor** de L7, L8 y L10. La orden da el
  valor en la fila («usar «RETE»») y el calificador aparte, en su lista, sin
  decir si va delante. Se aceptan las dos formas: el valor solo, como dice la
  fila, y con el calificador delante, como escribió la AEAT los de L10 en su
  ejemplo del 02-10-2026. Se le preguntó al buzón el 07-10-2026.
- **El `ProfileID` del ejemplo**, `urn:aeat:names:specification:schema:profile:B2B`,
  sin el `ubl:` que lleva el de la orden. Sale en NOTA y no en ERROR mientras
  el buzón no conteste, porque es la AEAT quien lo escribió así.

Lo que dijo el buzón y sigue valiendo
-------------------------------------
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

from validador import cius_es
from validador.en16931 import _UNCL1001
from validador.formato import (
    MARCADOR_CIUS_ES,
    NOMBRA_A_LA_AEAT,
    RESPUESTA,
    UBL,
    declara_la_solucion_publica,
)
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia
from validador.listas_de_codigos import lista
from validador.modelo import grupos
from validador.sintaxis import NS_CIUS_ES, POR_ID, SIN_MAPA, SINTAXIS_UBL, a_decimal, condiciones

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


def _cuantos(fila: cius_es.Campo, cardinalidad: str) -> int:
    """El máximo de una fila, después de comprobar que sigue siendo ese."""
    if fila.cardinalidad != cardinalidad:
        raise AnexoCambiado(
            f"{fila.id} «{fila.termino}» ya no es {cardinalidad} en el anexo: "
            f"{fila.cardinalidad}")
    return int(cardinalidad.split("..")[1])


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
PROCESO = cius_es.PROCESO
_obligatorio("BT-23")
_obligatorio("BT-24")

# Los del borrador de abril y el proceso del ejemplo de la AEAT del 02-10-2026.
# No salen de la tabla, y por eso van escritos a mano: el borrador no está en
# el BOE, y el ejemplo es una captura de pantalla. Se reconocen para decir qué
# son en vez de tratarlos como cualquier otro valor equivocado.
ESPECIFICACION_DEL_BORRADOR = "urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0"
PROCESO_DEL_BORRADOR = "urn:aeat:names:specification:ubl:schema:B2B"
PROCESO_DEL_EJEMPLO = "urn:aeat:names:specification:schema:profile:B2B"
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

# La moneda del IVA: «Valor obligatorio: usar «EUR»».
_dice("BT-6", "usar EUR")
_dice("BT-6", "se consignará obligatoriamente como moneda de contabilización del IVA el euro")

# El importe pagado: ya no tiene que ser cero, pero no vale para un anticipo
# que devengó el IVA.
_dice("BT-113", "no debe ser utilizado en el caso de pagos anticipados que hayan "
                "supuesto el devengo del IVA")

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

# El tercero que expide la factura en lugar del vendedor.
_TERCERO = _ruta("BG-ES-1")
_TERCERO_NOMBRE = _relativa(_ruta(_obligatorio("BT-ES-3")), _TERCERO)
_TERCERO_NIF = _relativa(_ruta(_obligatorio("BT-ES-4")), _TERCERO)
_TERCERO_TIPO = _relativa(_ruta(_obligatorio("BT-ES-5")), _TERCERO)
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

# La clave de régimen de cada línea: una propiedad del artículo llamada
# «REGI», una o dos por línea, con el impuesto en el calificador.
_LINEAS = "./cac:InvoiceLine"
_dice("BT-160", "valor fijo REGI", "Régimen")
_dice("BT-160", "valor fijo RCAT", "Referencia catastral")
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
_RETENCION_HIJOS = {
    identificador: _relativa(_ruta(_obligatorio(identificador)), _RETENCIONES_APLICADAS)
    for identificador in ("BT-ES-18", "BT-ES-19", "BT-ES-20", "BT-ES-21")
}
_ruta_s, _CATEGORIA_DE_LA_RETENCION = _condicion("BG-ES-4", "cac:TaxCategory/cbc:ID")
_ruta_wth, _ESQUEMA_DE_LA_RETENCION = _condicion("BG-ES-4", "cac:TaxScheme/cbc:ID")
_RETENCION_CATEGORIA = _relativa(_ruta_s, _RETENCIONES_APLICADAS)
_RETENCION_ESQUEMA = _relativa(_ruta_wth, _RETENCIONES_APLICADAS)

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
# hay prueba de que existe en la tabla.
LO_QUE_TODAVIA_NO_SE_MIDE = (
    "la fecha efectiva de pago (BT-ES-2)",
    "el registro legal del vendedor cuando su NIF va con «LOC» (BT-30)",
    "el prefijo ES del NIF-IVA del vendedor (BT-31)",
    "el tipo de cada entrada del desglose del IVA (BT-119)",
    ("los impuestos y tasas que no son el IVA, en el documento (BG-ES-2), en las "
     "líneas (BT-ES-22) y cobrados para un tercero (BG-ES-3), con su lista L9"),
    "el número de la autorización de facturación (BT-ES-26)",
    "la información adicional de cada línea (BT-160, con el valor INFO de L8)",
    "los códigos de exención, que solo pueden ser VATEX-EU o VATEX-ES (BT-121)",
)


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
        "El total a pagar suma los importes de BT-179, que no tienen ruta. Con "
        "líneas de cobro, el cuadre del total a pagar (BR-CO-16) no se "
        "comprueba, y SPFE-TOTAL-A-PAGAR lo dice en el informe."
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
        "La tipología del tercero tiene que ser «FacturaciónPorTercero» cuando "
        "el tercero expide materialmente la factura, y eso no se ve en el "
        "documento. Se comprueba que la tipología esté, no cuál es."
    ),
    "BT-113": (
        "El importe pagado no puede usarse para anticipos que hayan devengado "
        "el IVA (artículo 75.Dos de la Ley del IVA), y eso no se ve en la "
        "factura. SPFE-IMPORTE-PAGADO lo dice en una nota cuando lo hay."
    ),
    "BT-21": (
        "La nota de la factura lleva el código «REG» cuando es una mención "
        "obligatoria según una normativa específica, y qué menciones lo son no "
        "se ve en la factura."
    ),
    "Cardinalidades máximas": (
        "Que un campo que no se repite no se repita se mira en los grupos donde "
        "repetirlo cambia lo que se declara: la clave de régimen y la "
        "referencia catastral de cada línea, el QR, los documentos de la "
        "rectificativa y las retenciones. El resto es cosa del esquema."
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
    return "; ".join(cosas[:-1]) + "; y " + cosas[-1]


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
        # con sus propios campos en el anexo I («Mensaje de anulación»):
        # medirlo con las reglas de las facturas sería inventar una regla, y
        # medirlo con las suyas es una regla nueva, que todavía no está escrita.
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

    incidencias = [
        # La nota dice con qué se ha medido y qué no. «Ninguna queja» no quiere
        # decir «cumple la orden», y la lista de lo que falta va entera, de
        # `LO_QUE_TODAVIA_NO_SE_MIDE`, para que la nota no prometa más de lo
        # que se ha hecho.
        Incidencia(
            "SPFE-ALCANCE",
            NOTA,
            "La factura dice ser de la solución pública, y se mide con el anexo "
            "I de la Orden HAC/1028/2026, publicada en el BOE el 05-10-2026 y en "
            "vigor desde el 06-10-2026. De lo que la orden pide, todavía no se "
            f"mide {_en_una_frase(LO_QUE_TODAVIA_NO_SE_MIDE)}. Que no salga "
            "ninguna queja no quiere decir que la factura cumpla la orden en "
            "eso.",
            campo="Identificador de especificación",
            encontrado=_valor(raiz, SINTAXIS_UBL.perfil),
        )
    ]
    if raiz.xpath("local-name()") != "Invoice":
        incidencias.append(
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
        )
        return incidencias

    for regla in (
        _especificacion, _proceso, _copia, _tipo_de_factura, _rectificativa,
        _moneda_del_iva, _importe_pagado, _nif, _direcciones, _tipo_de_impuesto,
        _tercero, _facturas_referenciadas, _motivos, _categorias,
        _claves_de_regimen, _referencias_catastrales, _lineas_de_cobro,
        _retenciones, _qr, _total_a_pagar,
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
    if declarado == PROCESO_DEL_EJEMPLO:
        # Una NOTA, que no condena ni absuelve: lo escribió así la AEAT en su
        # ejemplo del 02-10-2026, y se le preguntó al buzón el 07-10-2026 cuál
        # de los dos vale.
        return [
            Incidencia(
                "SPFE-PROCESO",
                NOTA,
                "El tipo de proceso de negocio es el del ejemplo que la AEAT "
                "mandó por correo el 02-10-2026, y no el que fija la orden "
                f"publicada en el BOE el 05-10-2026, que es {PROCESO}: con "
                "«ubl:». Se acepta mientras la AEAT no diga cuál de los dos "
                "vale, pero lo que manda es el valor de la orden.",
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
                   "que no llegó al BOE. La orden publicada el 05-10-2026 fija "
                   "otro en su fila BT-23, y admite un solo valor.")
    else:
        mensaje = ("El tipo de proceso de negocio no es el que fija la orden "
                   "publicada en el BOE el 05-10-2026, que admite un solo valor.")
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
            "original: «False (o sin informar): original». Si es una copia "
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
    lista; y, si se rectifica por sustitución con una sola factura, hasta cinco
    con los importes rectificados (RECT:IMPORTES), cada uno con su código de
    L2.C y su importe en la descripción.

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
            con = f" y schemeID «{atributo}»" if atributo else ""
            encontrados.append(f"{nif} con el impuesto «{impuesto or '(sin impuesto)'}»{con}")
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
                f"dos sitios: un esquema de impuesto «{_IMPUESTO}», o uno "
                f"«{_IMPUESTO_LOCAL}» con el atributo schemeID «{_ESQUEMA_DEL_NIF}» "
                "en el NIF. La norma europea lo deja opcional; la orden lo hace "
                "obligatorio para las dos partes.",
                campo=f"NIF del {quien} ({codigos})",
                esperado=f"cac:PartyTaxScheme con cbc:CompanyID y cac:TaxScheme/cbc:ID "
                         f"«{_IMPUESTO}», o «{_IMPUESTO_LOCAL}» con cbc:CompanyID@schemeID "
                         f"«{_ESQUEMA_DEL_NIF}»",
                encontrado=encontrado,
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

    Lo dicen las filas BT-95, BT-102, BG-30 y BG-23 en su columna de ruta.
    """
    lugares: list[str] = []
    malos: list[str] = []
    for ruta, lugar in _IMPUESTO_EN:
        for nodo in _nodos(raiz, ruta):
            escrito = _escrito(nodo)
            if escrito == _IMPUESTO:
                continue
            if lugar not in lugares:
                lugares.append(lugar)
            if (escrito or "(vacío)") not in malos:
                malos.append(escrito or "(vacío)")
    if not malos:
        return []
    return [
        Incidencia(
            "SPFE-TIPO-DE-IMPUESTO",
            ERROR,
            f"El tipo de impuesto no es «{_IMPUESTO}». La orden lo fija en "
            f"«{_IMPUESTO}» en los descuentos y cargos del documento, en cada "
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
            faltan.append("la tipología (BT-ES-5)")
        esquemas = _nodos(tercero, _TERCERO_ESQUEMAS)
        if _valor(tercero, _TERCERO_NIF) and not any(_nif_bien_puesto(e) for e in esquemas):
            impuesto = _valor(tercero, _TERCERO_IMPUESTO)
            faltan.append(f"el impuesto «{_IMPUESTO}», o «{_IMPUESTO_LOCAL}» con el "
                          f"atributo «{_ESQUEMA_DEL_NIF}» (hay «{impuesto or '(nada)'}»)")
        if not faltan:
            continue
        incidencias.append(
            Incidencia(
                "SPFE-TERCERO",
                ERROR,
                f"Al tercero que expide la factura le falta {_y(faltan)}. Si "
                "el grupo del tercero está, la orden pide su nombre o razón "
                f"social, su NIF (con el impuesto «{_IMPUESTO}», o con "
                f"«{_IMPUESTO_LOCAL}» y el atributo «{_ESQUEMA_DEL_NIF}») y la "
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


def _claves_de_regimen(raiz) -> list[Incidencia]:
    """BG-32 «CLAVE DE RÉGIMEN»: una o dos en cada línea, cada una en su lista.

    Las listas son las de la orden: la L3A ya no tiene las claves 18, 19 y 20
    del borrador de abril (el régimen simplificado, el recargo de equivalencia
    y el de agricultura, ganadería y pesca), y una línea con ellas en el IVA
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
                "línea, como una propiedad del artículo llamada «REGI» (sola o "
                "con el calificador de la lista L8 delante): la clave en el "
                "valor y el impuesto (IVA, IGIC o IPSI) en el calificador.",
                campo=_donde("Clave de régimen (BG-32)", sin_clave),
                esperado="cac:AdditionalItemProperty con cbc:Name «REGI»",
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
                "Hay una propiedad «RCAT» sin la referencia catastral. Si el "
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
            (_RETENCION_CATEGORIA, f"la categoría «{_CATEGORIA_DE_LA_RETENCION}»",
             _CATEGORIA_DE_LA_RETENCION, "BG-ES-4"),
            (_RETENCION_HIJOS["BT-ES-20"], "el porcentaje", None, "BT-ES-20"),
            (_RETENCION_ESQUEMA, f"el esquema «{_ESQUEMA_DE_LA_RETENCION}»",
             _ESQUEMA_DE_LA_RETENCION, "BG-ES-4"),
        ):
            escrito = _valor(subtotal, ruta)
            if not escrito or (fijo and escrito != fijo):
                faltan.append(f"{texto}{sufijo} ({identificador})")
        concepto = _valor(subtotal, _RETENCION_HIJOS["BT-ES-21"])
        if concepto not in _L["L5"].valores:
            faltan.append(f"un concepto de la lista L5{sufijo} (BT-ES-21, hay «{concepto or '(nada)'}»)")
    if not faltan:
        return []
    return [
        Incidencia(
            "SPFE-RETENCION",
            ERROR,
            f"A las retenciones les falta {_y(faltan)}. La orden pide la línea "
            "que las identifica, la suma, y en cada retención la base, el "
            f"importe, la categoría «{_CATEGORIA_DE_LA_RETENCION}», el "
            f"porcentaje, el esquema «{_ESQUEMA_DE_LA_RETENCION}» y el concepto "
            "de la lista L5.",
            campo="Retenciones (BG-34, BG-ES-4)",
            esperado="la identificación, la suma y cada retención completa",
            encontrado=f"falta {_y(faltan)}",
        )
    ]


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


def _total_a_pagar(raiz) -> list[Incidencia]:
    """BT-115 con líneas de cobro: no se puede cuadrar, y se dice.

    El anexo suma al total a pagar los importes de BT-179, que no tienen ruta.
    BR-CO-16, que es de la edición de 2017, no los conoce y daba por mal una
    factura bien hecha. `factura._SOBRA_SI` lo quita cuando sale esta nota.
    """
    if not _nodos(raiz, _LINEA_DE_COBRO):
        return []
    return [
        Incidencia(
            "SPFE-TOTAL-A-PAGAR",
            NOTA,
            "La factura lleva líneas de cobro (suplidos, minoraciones, "
            "retenciones, o impuestos y tasas cobrados en nombre de un tercero, "
            "como el IEDMT), y la orden suma sus importes al total a pagar "
            "(BT-115). La norma de 2017 no los conoce y la orden no dice dónde "
            "se escriben, así que el cuadre del total a pagar (BR-CO-16) no se "
            "ha comprobado.",
            campo="Total a pagar (BT-115)",
            encontrado=_valor(raiz, SINTAXIS_UBL.a_pagar),
        )
    ]
