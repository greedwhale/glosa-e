"""Lo que el anexo I pide a una factura de la solución pública, además de la norma.

A quién se aplica
-----------------
A las facturas UBL que declaran el CIUS de la solución pública en su
`CustomizationID` —`urn:aeat.es:CIUS-ES-SPFE`—.

Y, desde el **02-10-2026**, también a las que declaran el identificador que la
AEAT enseñó ese día en un ejemplo,
`urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:1.0.0:extended`, que no
es el del anexo de abril y que el correo no explica. Hasta ese día una
factura escrita exactamente como el ejemplo de la Agencia pasaba por aquí sin
que se le aplicara nada y sin que nada lo dijera (`formato.ESPECIFICACION_DEL_EJEMPLO`
cuenta lo medido). Se le mide igual que a la otra, y `SPFE-ESPECIFICACION` lo
dice en una NOTA. Lo que nombre a la AEAT sin ser ninguno de los dos recibe un
AVISO: no se le mide, pero no se calla.

El anexo I del proyecto de orden dice qué tienen que llevar «como mínimo» las
facturas que se remiten a la AEAT, y lo dice **en UBL**: sus rutas son de UBL y
de nada más. Qué le corresponde a cada campo en Facturae, en CII o en EDIFACT
no lo publica nadie, y aplicarlo a otra sintaxis sería inventarse esa
correspondencia. A un documento de otra sintaxis que declare el CIUS se le
avisa de que no se ha comprobado, que es distinto de callar.

Esto dejó de ser una ausencia el **17-09-2026**. Preguntada por escrito si
pensaba publicar esa correspondencia, la AEAT contestó que no es suya: «cae en
la responsabilidad de las plataformas privadas, o en su caso, de la definición
por parte del Ministerio de Economía que regula la interconexión entre
plataformas privadas y sus formatos». Y remitió, para la semántica europea, a
las partes de CEN que sí existen —`16931-3-2` para UBL, `-3-3` para CII y
`-3-4` para EDIFACT, ratificadas por UNE en septiembre de 2026—, que mapean la
EN 16931 y **no** los campos españoles del anexo. Para Facturae no hay ninguna.

Lo que cambia es la frase, no el código: antes aquí se decía que no constaba
publicada, que es lo único que se podía sostener; ahora consta que quien podría
publicarla ha dicho que no lo hará. Se sigue avisando igual, porque una
correspondencia escrita por cada plataforma para sí misma no es una que este
validador pueda dar por buena.

Tampoco se aplica a una factura UBL que no lo declare. Quien emite para Peppol
o para una plataforma privada no se ha comprometido con este CIUS, y exigírselo
sería dar por mal una factura que no pretende ser eso. Quien lo declara sí
acepta sus listas —el tipo de factura sin el 381, la categoría de IVA sin la
K— y con ellas se le mide.

Es un borrador
--------------
Sometido a audiencia pública el 17-04-2026 y sin publicar en el BOE. Todo lo
que sale de aquí lleva el prefijo `SPFE-`, y cada factura que se mide con él
lleva una NOTA que lo dice: que no salga ninguna queja quiere decir que cumple
el borrador, no la orden.

Y es un borrador que ya cambió
------------------------------
El **10-09-2026**, en un seminario del portal de entidades desarrolladoras, la
AEAT presentó las «principales novedades» del anexo I. El texto nuevo no está
publicado —solo las transparencias—, y la orden se quiere en vigor el
01-10-2026. Lo que se anunció toca a este módulo por lo menos aquí:

- **La extensión de rectificativas desaparece**, y esto ya no lo dice una
  transparencia: el **22-09-2026** la AEAT lo confirmó por escrito en el buzón
  —«el grupo de extensión nacional BG-ES-1 para datos rectificados (presente en
  el borrador de abril) deja de existir de forma definitiva»—, y dice que las
  rectificativas se estructuran con el grupo `BG-24` de la norma usando los
  calificadores de las listas L10 y L2. El **23-09-2026** dio por escrito la
  L10 entera —`QR`, `AUT`, `RECT:TIPO`, `RECT:MODALIDAD`, `RECT:IMPORTES`—,
  y aquí se tomó por lo nuevo de esa respuesta. **No lo era**: la misma tabla,
  con el esquema sin `ubl:`, estaba en la diapositiva 8 de estas mismas
  transparencias. Va como imagen, `pdftotext` no la saca, y nadie la vio hasta
  el 05-10-2026. Las L2 que mandó son palabra por palabra las que el anexo de
  abril ya trae. Con eso, `_rectificativa()` ni exige la extensión ni se
  limita a decir que hay algo colgado: **reconoce** los calificadores y dice
  cuáles hay y cuál falta, en una NOTA. El **valor** no se podía comprobar
  porque nadie había dicho en qué campo del `BG-24` va; el **02-10-2026** la
  AEAT lo enseñó en un ejemplo, `cbc:DocumentTypeCode`, y desde entonces se
  compara con las listas L2 (ver «Lo que enseñó el ejemplo», más abajo).
- **El indicador de copia pasa a `0..1`**. `_copia()` lo pide como obligatorio.
- **El 389** para las facturas expedidas por el destinatario, junto al 471.
  Aquí se escribió que entraba, y no: la L1 de abril ya lo trae. Lo que
  dice la transparencia es que «la expedición de facturas por el
  destinatario o por tercero está plenamente contemplada en el Anexo I».
- **El NIF del vendedor va en `BT-31` o en `BT-32`**, y el de `BT-32` con el
  esquema «LOC» y `@schemeID` «FC», no con «VAT». `_nif()` solo admite «VAT».
- **L4 gana las categorías nuevas de la EN 16931:2026**, entre ellas la `N`,
  y se han pedido códigos VATEX propios de España.
- **L3A se recorta**: fuera el régimen simplificado, el recargo de equivalencia
  y el de agricultura, ganadería y pesca. `_claves_de_regimen()` los admite.
- **`BG-34` (`BT-179` y `BT-180`) se usa para el IEDMT**, y esos términos están
  en la edición de 2026. Aquí están en `NO_SE_COMPRUEBA` por no tener ruta.
- Se incorpora un **mensaje de anulación** —un `ApplicationResponse` de UBL—,
  que es un documento nuevo y no una regla sobre la factura. Desde el
  29-09-2026 se reconoce (`formato.RESPUESTA`) y se le mide la forma y la firma;
  `reglas()` no lo toca: el texto de ese mensaje no está publicado, y medirlo
  con el anexo de las facturas sería inventar una regla.

De todo eso se ha tocado **una sola cosa**, la de las rectificativas, y no por
las transparencias: por una respuesta escrita del buzón de la AEAT del
22-09-2026. La diferencia importa —**unas transparencias no son una fuente con
la que reescribir reglas**— y lo que se hizo tampoco es reescribir la regla: es
dejar de dar por mala la forma nueva, que no es lo mismo que saber medirla. El
anexo de abril sigue siendo el único texto publicado, y el resto de las reglas
lo miden a él. Lo que sí se hace es decirlo donde se ve, en la NOTA
`SPFE-BORRADOR` de cada factura medida. El día que salga el texto, esta sección
es la lista de lo que hay que revisar.

Esa misma respuesta del 22-09-2026 contesta otras tres cosas que no cambian
ninguna regla de hoy pero sí lo que se puede esperar:

- **No habrá texto del anexo antes del BOE**: «a priori, no está prevista la
  publicación de una nueva versión borrador o texto actualizado». Lo que
  espera al texto, espera al boletín.
- **La edición de la norma es la de 2026 para todo el sistema**, y no solo para
  la solución pública: `UNE-EN 16931-1:2026` y `UNE-CEN/TS 16931-3-2:2026`
  —UBL 2.5— valen también para las copias fieles y para el intercambio privado
  del artículo 7.1.
- **Los documentos de validación no traerán esquematrón**: serán las reglas de
  negocio escritas, «sin incluir ficheros ejecutables Schematron». Y en el
  entorno de pruebas habrá un servicio de validación de facturas UBL 2.5
  sueltas, que es lo primero contra lo que se podrá contrastar esto.

Y la del **23-09-2026** contesta dos cosas más, ninguna de las cuales cambia
una regla de hoy:

- **El 381 y la `K` siguen fuera**, y ahora por escrito: «no se aceptan
  InvoiceType de tipo 381 en L1. Tampoco se aceptará la categoría K en L4».
  Eso confirma lo que este módulo ya mide, y confirma también el precio: una
  factura válida según la EN 16931 —un abono 381, una entrega intracomunitaria
  con categoría `K`— no pasa el anexo español. La AEAT añade que **eleva la
  cuestión a gestión para que reevalúen el criterio**, así que está confirmado
  y vivo a la vez. Por eso el `BT-3`/381 y la L4 siguen aparcados.
- **PRE y los documentos de validación, en octubre**, «pero dependerá de la
  publicación de la Orden Ministerial y el texto final con el que se publique».
  Una ventana, no una fecha, y colgando de lo mismo que todo lo demás.

Lo que enseñó el ejemplo del 02-10-2026
--------------------------------------
La consulta del 23-09-2026 preguntaba tres cosas: si el esquema de L10 lleva
`ubl:` o no, en qué campo del `BG-24` va el valor del calificador y dónde va el
número de la autorización. La respuesta llegó el 02-10-2026 y fue solo una
captura de un XML, «un ejemplo a modo de captura de pantalla para resolver las
dudas», sin una frase de criterio:

| Pregunta | Lo que enseña el ejemplo |
|---|---|
| El esquema | `urn:aeat:names:specification:schema:`, **sin `ubl:`**, en los cuatro calificadores que trae, QR incluido |
| El valor del calificador | en **`cbc:DocumentTypeCode`**: `R1` en RECT:TIPO, `S` en RECT:MODALIDAD; la descripción es texto libre |
| El número de la autorización | en **`cbc:UUID`**, como la URL del QR; el `cbc:ID` lo ocupa el calificador |

Y trae dos cosas que no se preguntaron: otro `CustomizationID` y otro
`ProfileID` que los del anexo de abril.

Pesa más que una transparencia, porque es la Agencia contestando por escrito a
lo que se le preguntó, y menos que la prosa del 22 y el 23-09: enseña una
forma, no dice qué es obligatorio. Así que se usa como se usaron aquellas
respuestas, **para dejar de condenar y para leer donde ya se sabe leer**, y
nunca para un ERROR nuevo:

- los dos identificadores del ejemplo se aceptan con una NOTA que lo dice;
- el QR y la autorización se reconocen con los dos esquemas, como ya se hacía
  con los de la rectificativa (el QR solo se reconocía con el de abril, y un
  QR escrito como el ejemplo dejaba mudo a `SPFE-QR`);
- el tipo y la modalidad se leen en `cbc:DocumentTypeCode` y se comparan con
  L2.A y L2.B, que son del anexo publicado; un código que no esté en su lista
  sale como AVISO, no como ERROR, porque el sitio lo dice un ejemplo.

Glosa había apostado por la descripción, «por analogía con el QR», y no lo
programó. Bien hecho: hoy daría por malas las facturas escritas como enseña la
AEAT.

De dónde sale cada comprobación
-------------------------------
De una fila del anexo, y lo que se puede sacar de la tabla se saca de ella al
importar, en vez de copiarse aquí:

- **Las rutas de los campos españoles**, de `sintaxis.RUTAS_CIUS_ES`. Las de
  dentro de un grupo se piden relativas al grupo, y si el anexo deja de
  colgarlas de ahí, este módulo no importa.
- **Los valores fijos** —los URN, «VAT», «S», «WTH», «EUR»—, de la descripción
  de su fila. Si la frase ya no está, tampoco importa.
- **Que lo que se exige sea obligatorio en el anexo.** Cada campo que aquí se
  pide tiene que tener allí cardinalidad `1..`; si un anexo nuevo lo relaja,
  el módulo no importa.

Es la negativa de siempre: un anexo nuevo que mueva algo no deja un validador
que comprueba lo de antes sin decir nada, deja uno que no se monta —y la suite
lo dice antes de publicar—.

Los campos que la EN 16931 ya tiene van por la vinculación UBL de 2017, la de
`SINTAXIS_UBL`, porque el anexo no les da ruta: remite a la vinculación de la
edición de 2026, que no está publicada. Que esos elementos existen en UBL 2.5
donde se buscan está comprobado contra el esquema en las pruebas; que la
vinculación de 2026 los use para lo mismo no se puede comprobar hasta que
salga.

Lo que no se comprueba está en `NO_SE_COMPRUEBA`, con el porqué de cada cosa.
"""

from __future__ import annotations

import re

from validador import cius_es
from validador.en16931 import _UNCL1001
from validador.formato import (
    ESPECIFICACION_DEL_EJEMPLO,
    NOMBRA_A_LA_AEAT,
    RESPUESTA,
    UBL,
    declara_la_solucion_publica,
)
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia
from validador.listas_de_codigos import lista
from validador.modelo import grupos
from validador.sintaxis import NS_CIUS_ES, POR_ID, SIN_MAPA, SINTAXIS_UBL, a_decimal

__all__ = ["AnexoCambiado", "NO_SE_COMPRUEBA", "declara_el_cius", "reglas"]


class AnexoCambiado(LookupError):
    """Lo que este módulo lee del anexo ya no está donde estaba.

    Sale al importar, no al validar: un anexo regenerado que mueva una ruta o
    cambie un valor fijo no puede dejar reglas que miran lo de antes.
    """


# --- Lo que se lee del anexo al importar -------------------------------------

_COMILLAS = re.compile(r"[\"'«»“”‘’]")
_URN = re.compile(r"urn:aeat:names:specification:ubl:schema:[A-Za-z:]*[A-Z]")


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


def _dice(identificador: str, frase: str, termino: str = "") -> None:
    """Que la descripción de la fila siga diciendo esto, sin comillas ni saltos."""
    descripcion = " ".join(_COMILLAS.sub("", _fila(identificador, termino).descripcion).split())
    if frase not in descripcion:
        raise AnexoCambiado(f"la descripción de {identificador} ya no dice «{frase}»")


def _urn(identificador: str, termino: str = "") -> str:
    encontrado = _URN.search(_fila(identificador, termino).descripcion)
    if not encontrado:
        raise AnexoCambiado(f"la descripción de {identificador} ya no trae su URN")
    return encontrado.group(0)


def _ruta(identificador: str, termino: str = "") -> str:
    rutas = [r.ruta for r in POR_ID.get(identificador, ()) if termino in r.termino]
    if len(rutas) != 1 or rutas[0] == SIN_MAPA:
        raise AnexoCambiado(f"{identificador} «{termino}» ya no trae una ruta en el anexo")
    return rutas[0]


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


# El CIUS entero, y el proceso.
ESPECIFICACION = cius_es.ESPECIFICACION
PROCESO = cius_es.PROCESO
_dice(_obligatorio("BT-23"), PROCESO)
_obligatorio("BT-24")

# Y los dos del ejemplo que enseñó la AEAT el 02-10-2026, que no son los de
# abril y que no salen del anexo: salen de la captura, y por eso van escritos
# a mano y no en `cius_es`, que se genera del PDF. El de la especificación es
# `formato.ESPECIFICACION_DEL_EJEMPLO`, porque de él cuelga también qué versión
# de UBL se supone. El del proceso cambia en dos sitios a la vez: pierde el
# `ubl:`, como los calificadores de L10, y gana un `profile:` que no está en
# ningún otro texto.
PROCESO_DEL_EJEMPLO = "urn:aeat:names:specification:schema:profile:B2B"

_L = cius_es.LISTAS

# «Original o copia», que UBL deja opcional.
_COPIA = _ruta(_obligatorio("BT-ES-1"))

# El tipo de factura, y cuáles son rectificativas: «Las facturas emitidas con
# valores 384 y 471 incorporarán la extensión correspondiente a facturas
# rectificativas».
_dice("BT-3", "Sólo podrán adoptarse los valores definidos en la lista L1")
_dice("BT-3", "valores 384 y 471 incorporarán la extensión correspondiente a facturas rectificativas")
_RECTIFICATIVOS = ("384", "471")

# La extensión de rectificativas.
_URN_RECT = _urn("BT-ES-2", "extensión")
_RECTIFICATIVA = _ruta("BG-ES-1")
_RECT_TIPO = _relativa(_ruta(_obligatorio("BT-ES-2", "Tipo de factura rectificativa"),
                             "Tipo de factura rectificativa"), _RECTIFICATIVA)
_RECT_MODALIDAD = _relativa(_ruta(_obligatorio("BT-ES-3")), _RECTIFICATIVA)
_RECT_IMPORTES = _relativa(_ruta("BG-ES-2"), _RECTIFICATIVA)
_RECT_BASE = _relativa(_ruta(_obligatorio("BT-ES-4")), _ruta("BG-ES-2"))
# La extensión se identifica en el `cbc:ID` de su `ext:UBLExtension`, el mismo
# que contiene el `ExtensionContent` de donde cuelgan los datos.
if _ruta("BT-ES-2", "extensión") != _RECTIFICATIVA.split("/ext:ExtensionContent/")[0] + "/cbc:ID":
    raise AnexoCambiado("el identificador de la extensión de rectificativas ya no va en su UBLExtension")

# La moneda del IVA: «Valor obligatorio: usar EUR».
_dice("BT-6", "usar EUR")
_dice("BT-6", "se consignará obligatoriamente como moneda de contabilización del IVA el euro")

# El importe pagado: «Su valor solo puede ser 0 en caso de informarse».
_dice("BT-113", "solo puede ser 0 en caso de informarse")

# Las dos partes: el NIF va en un `PartyTaxScheme` cuyo impuesto es «VAT».
_IMPUESTO = "VAT"
for _identificador in ("BT-ES-7", "BT-ES-8", "BT-ES-13", "BT-ES-17", "BT-ES-19",
                       "BT-ES-22", "BT-ES-42", "BT-ES-46"):
    _dice(_obligatorio(_identificador), "usar VAT")
_obligatorio("BT-32")
_obligatorio("BT-48")
_ESQUEMAS_DEL_VENDEDOR = _padre(_ruta("BT-ES-7"), "cac:TaxScheme/cbc:ID")
_ESQUEMAS_DEL_COMPRADOR = _padre(_ruta("BT-ES-8"), "cac:TaxScheme/cbc:ID")
_IMPUESTO_DEL_ESQUEMA = _relativa(_ruta("BT-ES-7"), _ESQUEMAS_DEL_VENDEDOR)

# Las direcciones: la calle siempre, y ciudad, código postal y provincia
# «cuando la dirección postal esté en España».
_obligatorio("BT-35")
_obligatorio("BT-50")
for _identificador, _quien in (("BT-37", "vendedor"), ("BT-38", "vendedor"), ("BT-39", "vendedor"),
                               ("BT-52", "comprador"), ("BT-53", "comprador"), ("BT-54", "comprador")):
    _dice(_identificador, f"obligatorio cuando la dirección postal del {_quien} esté en España")

# El tipo de impuesto fuera de las partes: descuentos y cargos del documento,
# líneas y desglose.
_IMPUESTO_EN = (
    (_ruta("BT-ES-17"), "descuentos del documento"),
    (_ruta("BT-ES-19"), "cargos del documento"),
    (_ruta("BT-ES-42"), "líneas"),
    (_ruta("BT-ES-46"), "desglose del IVA"),
)

# El tercero que expide la factura en lugar del vendedor.
_TERCERO = _ruta("BG-ES-3")
_TERCERO_NIF = _relativa(_ruta(_obligatorio("BT-ES-12")), _TERCERO)
_TERCERO_IMPUESTO = _relativa(_ruta("BT-ES-13"), _TERCERO)
_TERCERO_NOMBRE = _relativa(_ruta(_obligatorio("BT-ES-14")), _TERCERO)
_TERCERO_TIPO = _relativa(_ruta(_obligatorio("BT-ES-15")), _TERCERO)

# La factura referenciada, con fecha.
_obligatorio("BT-26")

# El motivo en texto de descuentos y cargos.
_MOTIVOS = (
    ("descuentos_documento", _obligatorio("BT-97")),
    ("cargos_documento", _obligatorio("BT-104")),
    ("descuentos_linea", _obligatorio("BT-139")),
    ("cargos_linea", _obligatorio("BT-144")),
)

# La categoría de IVA, lista L4.
for _identificador in ("BT-95", "BT-102", "BT-151", "BT-118"):
    _dice(_identificador, "incluidos en la lista L4")
_CATEGORIAS = frozenset(_L["L4"].valores)
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
if _fila("BG-32", "CLAVE DE RÉGIMEN").cardinalidad != "1..2":
    raise AnexoCambiado("la clave de régimen ya no es 1..2 por línea")
if _fila("BG-32", "REFERENCIA CATASTRAL").cardinalidad != "0..1":
    raise AnexoCambiado("la referencia catastral ya no es 0..1 por línea")
_CLAVE = _relativa(_padre(_ruta(_obligatorio("BT-ES-44")), "cbc:ValueQualifier"), _LINEAS)
_CATASTRO = _relativa(_padre(_ruta(_obligatorio("BT-ES-43")), "cbc:ValueQualifier"), _LINEAS)
_CALIFICADOR = "./cbc:ValueQualifier"
_obligatorio("BT-161", "Código de clave de régimen")
_obligatorio("BT-161", "Referencia catastral")
_REGIMENES = {_L[clave].calificador: clave for clave in ("L3A", "L3B", "L3C")}
if len(_REGIMENES) != 3 or "" in _REGIMENES:
    raise AnexoCambiado("las listas de claves de régimen ya no dicen de qué impuesto son")

# Las líneas de cobro: cinco grupos, cada uno con su URN (lista L7).
_LINEA_DE_COBRO = "./cac:CollectionInvoiceLine"
_COBROS = {
    "SUPL": _urn("BT-ES-20"), "MINO": _urn("BT-ES-21"), "REEQ": _urn("BT-ES-27"),
    "REGE": _urn("BT-ES-31"), "RETE": _urn("BT-ES-32"),
}
if {urn.rsplit(":", 1)[1] for urn in _COBROS.values()} != set(_L["L7"].valores):
    raise AnexoCambiado("los URN de las líneas de cobro ya no son los de la lista L7")
_UNO_POR_FACTURA = {"REEQ": "RECARGO DE EQUIVALENCIA", "REGE": "GRUPO DE ENTIDADES",
                    "RETE": "RETENCIONES"}
for _termino in _UNO_POR_FACTURA.values():
    if _fila("BG-34", _termino).cardinalidad != "0..1":
        raise AnexoCambiado(f"el grupo «{_termino}» ya no es 0..1")

# El recargo de equivalencia.
_RECARGO = _padre(_ruta("BT-ES-27"), "cbc:ID")
_RECARGO_TOTAL = _relativa(_ruta(_obligatorio("BT-ES-28")), _LINEA_DE_COBRO)
_SUBTOTAL_DEL_RECARGO = _LINEA_DE_COBRO + "/cac:TaxTotal/cac:TaxSubtotal"
_RECARGO_SUBTOTALES = _relativa(_SUBTOTAL_DEL_RECARGO, _LINEA_DE_COBRO)
_dice("BT-ES-23", "es necesariamente S")
_RECARGO_HIJOS = {
    identificador: _relativa(_ruta(_obligatorio(identificador)), _SUBTOTAL_DEL_RECARGO)
    for identificador in ("BT-ES-22", "BT-ES-23", "BT-ES-24", "BT-ES-25", "BT-ES-26")
}

# Las retenciones.
_RETENCION = _padre(_ruta("BT-ES-32"), "cbc:ID")
_RETENCION_TOTAL = _ruta(_obligatorio("BT-ES-33"))
_RETENCIONES = _padre(_RETENCION_TOTAL, "cbc:TaxAmount")
_RETENCIONES_APLICADAS = _RETENCIONES + "/cac:TaxSubtotal"
_dice("BT-ES-36", "Valor fijo S")
_dice("BT-ES-38", "valor fijo WTH")
_dice("BT-ES-39", "tabla L5")
_RETENCION_HIJOS = {
    identificador: _relativa(_ruta(_obligatorio(identificador)), _RETENCIONES_APLICADAS)
    for identificador in ("BT-ES-34", "BT-ES-35", "BT-ES-36", "BT-ES-37", "BT-ES-38", "BT-ES-39")
}

# El régimen especial del grupo de entidades.
_GRUPO = _padre(_ruta("BT-ES-31"), "cbc:ID")
_URN_REGE = _urn(_obligatorio("BT-ES-29"))
_GRUPO_EXTENSION = _relativa(_ruta("BT-ES-29"), _LINEA_DE_COBRO)
_GRUPO_BASE = _relativa(_ruta(_obligatorio("BT-ES-30")), _LINEA_DE_COBRO)

# El QR fiscal.
_URN_QR = _urn("BT-122", "ID")
if _fila("BG-24", "QR FISCAL").cardinalidad != "0..1":
    raise AnexoCambiado("el grupo del QR ya no es 0..1")
# El QR ya no se busca por su URN entera: se reconoce por su calificador de
# L10, con cualquiera de los dos esquemas (ver `_calificador`, más abajo).
if not _URN_QR.endswith(":QR"):
    raise AnexoCambiado("la URN del QR ya no acaba en su calificador, QR")
# La descripción del QR es la fila BT-123 que trae ruta; la otra es la de la
# autorización. No se busca por el término porque el PDF lo parte —«doc
# umento»— y una errata de extracción no puede ser una clave.
if [c.cardinalidad for c in cius_es.CAMPOS if c.id == "BT-123" and c.ruta] != ["1..1"]:
    raise AnexoCambiado("la descripción del QR ya no es una sola fila obligatoria")
_QR_URL = _relativa(_ruta(_obligatorio("BT-ES-47")), SINTAXIS_UBL.adjuntos)

# Los calificadores de L10, que la AEAT dio por escrito el 23-09-2026. Son lo
# que hace legible un BG-24, que es justo lo que el anexo de abril daba por
# imposible: decía que el de la autorizacion «no trae ni ruta ni valor fijo
# con que distinguirlo de cualquier otro documento adjunto».
#
# **El anexo de abril no tiene L10.** Tiene de L1 a L8, y ni L9 ni L10. Aquí
# se dijo que era lo único nuevo de la respuesta del 23-09-2026, y no lo era:
# la tabla entera, con el esquema sin `ubl:`, estaba ya en la diapositiva 8 de
# las novedades del 10-09-2026, como imagen. `pdftotext` no saca las tablas
# que van como imagen, y nadie la miró como imagen hasta el 05-10-2026.
_L10_RECTIFICATIVA = {
    "RECT:TIPO": "el tipo de rectificativa",
    "RECT:MODALIDAD": "la modalidad de rectificación",
    "RECT:IMPORTES": "los importes rectificados",
}

# Los otros dos de L10, que no son de la rectificativa. Hasta el 05-10-2026
# solo se reconocía el QR, y solo con el esquema de abril, así que un QR o una
# autorización escritos como el ejemplo del 02-10-2026 contaban como «un BG-24
# que puede llevar los datos rectificados». Medido ese día: una 384 que no
# decía qué rectificaba pasaba de ERROR a NOTA por llevar un QR sin `ubl:`, y
# una con la autorización salía diciendo que ninguno de sus identificadores era
# de L10, que es falso. Ni el QR ni la autorización dicen qué se rectifica.
_L10_AJENOS_A_LA_RECTIFICATIVA = {
    "QR": "el QR fiscal",
    "AUT": "la autorización de facturación",
}

# El valor del tipo y de la modalidad, y con qué lista se compara. El campo
# sale del ejemplo del 02-10-2026, y no de un texto publicado: la captura pone
# `R1` en el `cbc:DocumentTypeCode` del BG-24 de RECT:TIPO y `S` en el de
# RECT:MODALIDAD. Las listas sí son del anexo de abril, y la AEAT las confirmó
# palabra por palabra el 23-09-2026. Por eso lo que no casa sale como AVISO y
# no como ERROR: la lista es firme, el sitio no.
_CODIGO_DEL_CALIFICADOR = "./cbc:DocumentTypeCode"
_LISTA_DEL_CALIFICADOR = {"RECT:TIPO": "L2.A", "RECT:MODALIDAD": "L2.B"}

# Se reconoce con cualquiera de los dos esquemas, porque los textos que lo
# escriben no dicen lo mismo:
#
# | Dónde | Esquema |
# |---|---|
# | el anexo de abril, para el QR | `urn:aeat:names:specification:ubl:schema:` |
# | la diapositiva 8 del 10-09-2026, para toda L10 | `urn:aeat:names:specification:schema:` |
# | el correo de la AEAT del 23-09-2026, para toda L10 | `urn:aeat:names:specification:schema:` |
# | el ejemplo del 02-10-2026, en los cuatro que trae | `urn:aeat:names:specification:schema:` |
#
# Tres contra uno, y el uno es el único que está en un texto con forma de
# norma. Elegir mal no daría un fallo: daría un validador que no encuentra
# nada y se calla, que es el disfraz de siempre. Aceptando los dos no hay nada
# que elegir. **Y se aceptan los dos para toda L10**: hasta el 05-10-2026 solo
# se hacía con los de la rectificativa, y el QR, que era justo el que el
# ejemplo escribe sin `ubl:`, solo se reconocía con el de abril.
_ESQUEMA_DEL_ANEXO = _URN_QR[: -len("QR")]
_ESQUEMA_SIN_UBL = "urn:aeat:names:specification:schema:"
if _ESQUEMA_DEL_ANEXO.replace(":ubl:", ":") != _ESQUEMA_SIN_UBL:
    raise AnexoCambiado(
        f"el esquema del QR del anexo, «{_ESQUEMA_DEL_ANEXO}», ya no es el de "
        f"L10 con «ubl:» dentro")
_ESQUEMAS_L10 = (_ESQUEMA_DEL_ANEXO, _ESQUEMA_SIN_UBL)

# Y lo que falta, escrito como negativa y no como recordatorio, que es el
# patron de este repositorio. Desde el ejemplo del 02-10-2026 el tipo y la
# modalidad se leen en `cbc:DocumentTypeCode`, pero todo sale como NOTA o
# AVISO, y queda una regla sin aplicar:
#
# - exigir los importes rectificados cuando la modalidad es `S`. Eso es **mas
#   estricto** que el anexo de abril, que solo pide la base *si* se informan
#   los importes, y nadie ha dicho como se escriben: el ejemplo es una S y no
#   los trae, y un `DocumentReference` no tiene ningun elemento de importe.
#
# Y lo que hoy es NOTA o AVISO pasa a medirse con el texto: que el valor vaya
# de verdad en `cbc:DocumentTypeCode`, que falte el tipo o la modalidad. Todo
# eso lo dira el anexo nuevo, y cuando lo diga traera L10 consigo -el de abril
# tiene de L1 a L8, sin L9 ni L10-, asi que en cuanto L10 aparezca esto se
# niega a importarse. No hay que acordarse de nada: no arranca.
if "L10" in cius_es.LISTAS:
    raise AnexoCambiado(
        "el anexo ya trae L10: falta terminar de leer el BG-24 (comprobar "
        "que el valor va en cbc:DocumentTypeCode, como en el ejemplo de la "
        "AEAT del 02-10-2026; exigir los importes cuando la modalidad es S; "
        "y medir con ERROR lo que hasta hoy es NOTA o AVISO)")


def _calificador(identificador: str) -> str:
    """El calificador de L10 de un BG-24, o «» si no lo lleva.

    Tiene que ser uno de los dos esquemas **entero** y, detrás, un calificador
    de L10 **entero**: ni un `MIRECT:TIPO` de cualquiera ni un esquema
    parecido de otro cuelan por el final.
    """
    for esquema in _ESQUEMAS_L10:
        if identificador.startswith(esquema):
            resto = identificador[len(esquema):]
            if resto in _L10_RECTIFICATIVA or resto in _L10_AJENOS_A_LA_RECTIFICATIVA:
                return resto
    return ""


def _adjuntos(raiz) -> list[tuple[str, object]]:
    """Cada BG-24 de la factura con su calificador de L10, o «» si no lo lleva."""
    return [(_calificador(_valor(adjunto, "./cbc:ID")), adjunto)
            for adjunto in _nodos(raiz, SINTAXIS_UBL.adjuntos)]

# El total a pagar, que suma los importes de terceros.
_dice("BT-115", "junto con los importes correspondientes a los conceptos BT-179")


# Lo que el anexo pide y aquí no se mira, con el porqué. Se dice porque un
# informe sin quejas sobre esto podría leerse como que se ha comprobado.
NO_SE_COMPRUEBA: dict[str, str] = {
    "BT-179 y BT-180": (
        "El importe y la descripción de los cinco grupos de cobros (suplidos, "
        "minoraciones, recargo de equivalencia, grupo de entidades y "
        "retenciones). El anexo no les da ruta: son términos de la EN 16931 "
        "de 2026, y su vinculación UBL no está publicada."
    ),
    "BT-115": (
        "El total a pagar suma los importes de BT-179, que no tienen ruta. Con "
        "líneas de cobro, el cuadre del total a pagar (BR-CO-16) no se "
        "comprueba, y SPFE-TOTAL-A-PAGAR lo dice en el informe."
    ),
    "BT-111": (
        "Con recargo de equivalencia, la cuota del IVA en euros suma también "
        "las cuotas del recargo, y esas están en BT-179."
    ),
    "BT-195": (
        "Solo admite códigos VATEX-EU o VATEX-ES, dice el anexo, pero es un "
        "término de la edición de 2026 sin ruta en ninguna vinculación "
        "publicada."
    ),
    "BT-ES-15": (
        "El código «ThirdPartyInvoicing» es obligatorio cuando el tercero expide "
        "materialmente la factura, y eso no se ve en el documento. Se comprueba "
        "que la tipología esté, no cuál es."
    ),
    "BT-123": (
        "La descripción del QR es «VERIFACTU o el que corresponda según "
        "normativa aplicable»: no es una lista cerrada. Se comprueba que esté."
    ),
    "BG-24 de la autorización": (
        "El grupo de la autorización de facturación se reconoce por su "
        "calificador de L10, AUT, pero no se comprueba que lleve el número: el "
        "anexo de abril no le da ruta, y que vaya en cbc:UUID solo lo enseña un "
        "ejemplo que la AEAT mandó por correo el 02-10-2026."
    ),
    "BG-17": (
        "El anexo admite una transferencia como mucho, y la vinculación UBL "
        "escribe cada una en su propio medio de pago. No dice cómo se lee lo "
        "uno sobre lo otro."
    ),
    "Cardinalidades máximas": (
        "Que un campo que no se repite no se repita se mira en los grupos donde "
        "repetirlo cambia lo que se declara: la clave de régimen y la "
        "referencia catastral de cada línea, el QR, y el recargo, las "
        "retenciones y el grupo de entidades. El resto es cosa del esquema, y "
        "dentro de las extensiones de la AEAT no hay esquema publicado."
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


def _de(nombre: str) -> str:
    """«del tipo», «de la modalidad»: la contracción que el castellano pide."""
    return "del " + nombre[3:] if nombre.startswith("el ") else "de " + nombre


def _y(cosas: list[str]) -> str:
    return cosas[0] if len(cosas) == 1 else ", ".join(cosas[:-1]) + " y " + cosas[-1]


# --- Entrada ----------------------------------------------------------------


def declara_el_cius(deteccion) -> bool:
    """Si el documento dice ser de la solución pública.

    Con el identificador del anexo de abril o con el del ejemplo que la AEAT
    enseñó el 02-10-2026 (`formato.declara_la_solucion_publica`). El nombre
    se queda, aunque el del ejemplo no diga «CIUS», porque es lo que
    preguntan quienes lo usan: si a este documento se le mide con el anexo.
    """
    return bool(deteccion) and declara_la_solucion_publica(deteccion.perfil)


def reglas(raiz, deteccion) -> list[Incidencia]:
    """Las reglas del anexo I, sobre un documento que declara la solución pública."""
    if not declara_el_cius(deteccion):
        return _de_la_aeat_sin_reconocer(deteccion)
    if deteccion.familia == RESPUESTA:
        # El anexo I mide facturas. Una respuesta puede llevar el mismo
        # `CustomizationID` (si el mensaje de anulación lo lleva no se sabe), y
        # sin esta línea recibía SPFE-SINTAXIS diciendo que el anexo «solo
        # define» el CIUS sobre UBL, que es falso: la respuesta es UBL. El
        # mensaje de anulación de la solución pública es una respuesta, y su
        # texto no está publicado: medirlo con el anexo de las facturas sería
        # inventar una regla. Cuando salga, tendrá las suyas.
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
        # El aviso dice dos cosas y las dos hacen falta. Que el anexo es un
        # borrador se sabía desde el principio. Que ese borrador **ya no es el
        # último** se sabe desde el 10-09-2026, cuando la AEAT presentó sus
        # novedades en el portal de desarrolladores sin publicar el texto
        # nuevo: hay reglas de aquí que con el anexo nuevo darían por mala una
        # factura bien hecha —la extensión de rectificativas desaparece—. No se
        # pueden reescribir sobre unas transparencias, así que lo que toca es
        # decirlo en cada factura que se mide. Se quita cuando salga el texto.
        Incidencia(
            "SPFE-BORRADOR",
            NOTA,
            "La factura dice ser de la solución pública y se ha medido "
            "con el anexo I del proyecto de orden, que es un borrador: se "
            "sometió a audiencia pública el 17-04-2026 y no está publicado en "
            "el BOE. Además, el 10-09-2026 la AEAT anunció cambios en ese "
            "anexo y todavía no ha publicado el texto: aquí se mide con el de "
            "abril, así que alguna regla SPFE- puede haber quedado vieja.",
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
        _recargo, _retenciones, _grupo_de_entidades, _qr, _total_a_pagar,
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
            "ninguno de los dos que se conocen de la solución pública: ni el "
            "del anexo de abril ni el del ejemplo que la AEAT mandó por correo "
            "el 02-10-2026. Las reglas del anexo no se han comprobado.",
            campo="Identificador de especificación (BT-24)",
            esperado=f"{ESPECIFICACION} o {ESPECIFICACION_DEL_EJEMPLO}",
            encontrado=perfil,
        )
    ]


def _especificacion(raiz) -> list[Incidencia]:
    """BT-24: el valor entero, no solo el nombre del CIUS.

    El del ejemplo del 02-10-2026 se acepta, y se dice: con una NOTA, no con
    un silencio, porque no es el del anexo y el anexo es el único texto con
    forma de norma que hay.
    """
    declarado = _valor(raiz, SINTAXIS_UBL.perfil)
    if declarado == ESPECIFICACION:
        return []
    if declarado == ESPECIFICACION_DEL_EJEMPLO:
        return [
            Incidencia(
                "SPFE-ESPECIFICACION",
                NOTA,
                "El identificador de especificación no es el del anexo de "
                "abril, sino el que enseñó la AEAT el 02-10-2026 en un ejemplo, "
                "contestando por correo a una consulta. Se acepta, y la factura "
                "se mide con el anexo de abril, que es el único publicado. El "
                "correo no explica el cambio, y un ejemplo no es el BOE: valdrá "
                "el que diga el texto que se publique.",
                campo="Identificador de especificación (BT-24)",
                encontrado=declarado,
            )
        ]
    return [
        Incidencia(
            "SPFE-ESPECIFICACION",
            ERROR,
            "El identificador de especificación nombra el CIUS de la solución "
            "pública, pero no con el valor que fija el anexo. El anexo da el "
            "valor entero, y cualquier diferencia (otra edición de la norma, "
            "otra versión del CIUS) es otro identificador.",
            campo="Identificador de especificación (BT-24)",
            esperado=ESPECIFICACION,
            encontrado=declarado,
        )
    ]


def _proceso(raiz) -> list[Incidencia]:
    """BT-23: opcional en la norma, obligatorio y con valor fijo en el anexo.

    `cbc:ProfileID` es donde la vinculación UBL escribe BT-23; `SINTAXIS_UBL`
    no lo lleva porque ninguna regla europea lo miraba.
    """
    declarado = _valor(raiz, "./cbc:ProfileID")
    if declarado == PROCESO:
        return []
    if declarado == PROCESO_DEL_EJEMPLO:
        # Con cualquiera de los dos identificadores, y no solo con el del
        # ejemplo: es una NOTA, que no condena ni absuelve, y la base que
        # tiene, la captura del 02-10-2026, es la misma en los dos casos.
        return [
            Incidencia(
                "SPFE-PROCESO",
                NOTA,
                "El tipo de proceso de negocio no es el del anexo de abril, "
                "sino el del ejemplo que la AEAT mandó por correo el "
                "02-10-2026. Se acepta porque lo enseña la propia AEAT y el "
                "anexo nuevo no está publicado: valdrá el que diga el texto "
                "que se publique.",
                campo="Tipo de proceso de negocio (BT-23)",
                encontrado=declarado,
            )
        ]
    mensaje = (
        "Falta el tipo de proceso de negocio. La norma europea lo deja "
        "opcional; el anexo lo hace obligatorio, y con un valor fijo."
        if not declarado else
        "El tipo de proceso de negocio no es el que fija el anexo, que admite "
        "un solo valor."
    )
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
    """BT-ES-1: si es el original o una copia."""
    if _valor(raiz, _COPIA):
        return []
    return [
        Incidencia(
            "SPFE-COPIA",
            ERROR,
            "Falta decir si la factura es el original o una copia. En UBL es "
            "opcional; el anexo lo hace obligatorio: false para el original, "
            "true para una copia.",
            campo="Original o copia (BT-ES-1)",
            esperado="cbc:CopyIndicator con false o true",
            encontrado="(falta)",
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
               "los que admite el anexo, que son los de la lista L1.")
    if codigo == "381":
        mensaje += (" El 381 es el abono de la EN 16931 y en la solución pública "
                    "no existe: una rectificativa es 384, o 471 si la expide el "
                    "destinatario. Si rectifica por diferencias o por "
                    "sustitución se dice en la extensión de rectificativas del "
                    "anexo de abril, o en un documento justificativo adicional "
                    "(BG-24), que es donde van los datos rectificados en el "
                    "anexo nuevo.")
    return [
        Incidencia(
            "SPFE-TIPO-DE-FACTURA",
            ERROR,
            mensaje,
            campo="Tipo de factura (BT-3)",
            esperado=_y(list(_L["L1"].valores)).replace(" y ", " o "),
            encontrado=codigo,
        )
    ]


def _rectificativa(raiz) -> list[Incidencia]:
    """BG-ES-1: la extensión de rectificativas, y lo que lleva dentro.

    Y desde el 22-09-2026, también lo que pasa cuando no está. Ese día la AEAT
    contestó por escrito que `BG-ES-1` «deja de existir de forma definitiva» y
    que las rectificativas se estructuran con el grupo `BG-24` de la norma, con
    los calificadores de L10 y L2. El anexo de abril sigue siendo el único
    texto publicado, así que aquí se sigue midiendo con él; lo que no se puede
    es dar **por mala** una factura escrita a la forma nueva, que es lo que
    hacía esta regla.

    La forma nueva se lee en `_bg24_de_la_forma_nueva`. Aquí solo se decide si
    hay algo que leer: un BG-24 que no sea ni el QR ni la autorización, que
    son de L10 pero no dicen qué se rectifica. Si no hay nada, la factura no
    lleva los datos rectificados de ninguna de las dos maneras, y eso es el
    ERROR de siempre.
    """
    tipo = _valor(raiz, "./cbc:InvoiceTypeCode")
    datos = _nodos(raiz, _RECTIFICATIVA)
    if not datos:
        if tipo not in _RECTIFICATIVOS:
            return []
        adjuntos = [(calificador, adjunto) for calificador, adjunto in _adjuntos(raiz)
                    if calificador not in _L10_AJENOS_A_LA_RECTIFICATIVA]
        if adjuntos:
            return _bg24_de_la_forma_nueva(tipo, adjuntos)
        return [
            Incidencia(
                "SPFE-RECTIFICATIVA",
                ERROR,
                f"La factura es rectificativa ({tipo}) y no dice qué "
                "rectifica: ni la extensión de rectificativas que exige el "
                "anexo de abril, ni un documento justificativo adicional "
                "(BG-24), que es donde van los datos rectificados en el anexo "
                "nuevo. Hace falta una de las dos: es donde se dice qué se "
                "rectifica (R1 a R4) y cómo, por diferencias (I) o por "
                "sustitución (S).",
                campo="Datos rectificados (BG-ES-1)",
                esperado="la extensión de rectificativas, o un BG-24",
                encontrado="(falta)",
            )
        ]

    incidencias: list[Incidencia] = []
    faltan: list[str] = []
    for correccion in datos:
        extension = _valor(correccion, "ancestor::ext:UBLExtension[1]/cbc:ID")
        if extension != _URN_RECT:
            incidencias.append(
                Incidencia(
                    "SPFE-RECTIFICATIVA",
                    ERROR,
                    "La extensión de rectificativas no se identifica con el "
                    "valor que fija el anexo. Ese valor, en el cbc:ID de la "
                    "extensión, es lo que dice qué extensión es.",
                    campo="Identificador de la extensión (BT-ES-2)",
                    esperado=_URN_RECT,
                    encontrado=extension or "(falta)",
                )
            )
        for ruta, lista_, nombre, codigo in (
            (_RECT_TIPO, "L2.A", "el tipo de rectificativa", "BT-ES-2"),
            (_RECT_MODALIDAD, "L2.B", "la modalidad de rectificación", "BT-ES-3"),
        ):
            escrito = _valor(correccion, ruta)
            valores = _L[lista_].valores
            if not escrito:
                faltan.append(f"{nombre} ({codigo})")
            elif escrito not in valores:
                incidencias.append(
                    Incidencia(
                        "SPFE-RECTIFICATIVA",
                        ERROR,
                        f"El código de {nombre} no está en la lista {lista_} "
                        "del anexo.",
                        campo=f"{nombre[0].upper()}{nombre[1:]} ({codigo})",
                        esperado=_y(list(valores)).replace(" y ", " o "),
                        encontrado=escrito,
                    )
                )
        for importes in _nodos(correccion, _RECT_IMPORTES):
            if not _valor(importes, _RECT_BASE):
                faltan.append("la base rectificada (BT-ES-4)")
    if faltan:
        incidencias.insert(
            0,
            Incidencia(
                "SPFE-RECTIFICATIVA",
                ERROR,
                f"A la extensión de rectificativas le falta {_y(faltan)}. El "
                "anexo pide siempre el tipo y la modalidad, y la base "
                "rectificada si se informan los importes rectificados.",
                campo="Datos rectificados (BG-ES-1)",
                esperado="el tipo (L2.A) y la modalidad (L2.B)",
                encontrado="(falta)",
            ),
        )
    return incidencias


def _bg24_de_la_forma_nueva(tipo: str, adjuntos: list) -> list[Incidencia]:
    """Lo que se puede decir de un BG-24 con los calificadores de L10.

    Se puede decir **cuál** es cada uno, y eso ya distingue una rectificativa
    escrita a la forma nueva de un albarán colgado de la factura: hasta el
    23-09-2026 las dos salían con la misma frase, «un BG-24 sin leer».

    Y desde el 02-10-2026 se puede decir **cuánto vale** el tipo y la
    modalidad. Hasta entonces no estaba escrito en ninguna parte: los dos
    BG-24 que publica el anexo de abril ponen el valor en sitios distintos, y
    aquí se apostó, por analogía con el QR, por la descripción. No se programó
    porque razonable no es publicado, y fue lo correcto: el ejemplo que mandó
    la AEAT lo pone en `cbc:DocumentTypeCode` (`R1`, `S`) y deja la
    descripción para un texto libre. Si se hubiera programado, hoy daría por
    malas las facturas escritas como enseña la Agencia.

    Lo que no casa con su lista sale como AVISO y no como ERROR, y lo que
    falta, como NOTA: la lista es del anexo publicado, pero el sitio lo dice
    un ejemplo, y que todas lleven tipo y modalidad lo dice la prosa del
    23-09-2026, que describe un anexo que no está en el BOE.
    """
    # Todos los de cada calificador, y no el primero: quedarse con uno hacía
    # desaparecer sin decirlo un R9 que viniera detrás de un R1, y la nota
    # daba por comprobado lo que no se había mirado entero.
    presentes: dict[str, list] = {}
    for calificador, adjunto in adjuntos:
        if calificador in _L10_RECTIFICATIVA:
            presentes.setdefault(calificador, []).append(adjunto)
    if not presentes:
        return [
            Incidencia(
                "SPFE-RECTIFICATIVA",
                NOTA,
                f"La factura es rectificativa ({tipo}) y no lleva la "
                "extensión de rectificativas del anexo de abril, pero sí "
                "trae un documento justificativo adicional (BG-24), que es "
                "donde van los datos rectificados desde que la AEAT "
                "confirmó, el 22-09-2026, que la extensión desaparece. No "
                "se comprueba lo que dice: ninguno de sus identificadores es "
                "un calificador de la rectificativa de los de la lista L10, "
                "y el anexo que los fija no está publicado.",
                campo="Datos rectificados (BG-24)",
                esperado="el tipo y la modalidad, con L10 y L2",
                encontrado="un BG-24 sin leer",
            )
        ]

    incidencias: list[Incidencia] = []
    leidos: list[str] = []
    sin_codigo: list[str] = []
    repetidos: list[str] = []
    for calificador, lista_ in _LISTA_DEL_CALIFICADOR.items():
        if calificador not in presentes:
            continue
        nombre = _L10_RECTIFICATIVA[calificador]
        valores = _L[lista_].valores
        if len(presentes[calificador]) > 1:
            repetidos.append(f"{len(presentes[calificador])} documentos con {nombre}")
        for adjunto in presentes[calificador]:
            codigo = _valor(adjunto, _CODIGO_DEL_CALIFICADOR)
            if not codigo:
                sin_codigo.append(nombre if len(presentes[calificador]) == 1
                                  else f"uno de los documentos {_de(nombre)}")
                continue
            if codigo in valores:
                leidos.append(f"{nombre}, {codigo}, está en la lista {lista_}")
                continue
            incidencias.append(
                Incidencia(
                    "SPFE-RECTIFICATIVA",
                    AVISO,
                    f"El código {_de(nombre)} no está en la lista {lista_} del "
                    "anexo. Se ha leído en cbc:DocumentTypeCode, que es donde "
                    "lo pone el ejemplo que la AEAT mandó por correo el "
                    "02-10-2026; la lista es la del anexo de abril, que la AEAT "
                    "confirmó palabra por palabra el 23-09-2026. Es un aviso y "
                    "no un error porque el anexo que fija ese sitio no está "
                    "publicado.",
                    campo=f"{nombre[0].upper()}{nombre[1:]} ({calificador})",
                    esperado=_y(list(valores)).replace(" y ", " o "),
                    encontrado=codigo,
                )
            )

    mensaje = (
        f"La factura es rectificativa ({tipo}) y lleva los datos "
        "rectificados en documentos justificativos adicionales (BG-24), "
        "que es donde van desde que la AEAT confirmó, el 22-09-2026, que "
        "la extensión del anexo de abril desaparece. Se reconoce "
        f"{_y(sorted(_L10_RECTIFICATIVA[c] for c in presentes))}, por sus "
        "calificadores de la lista L10."
    )
    if repetidos:
        mensaje += (f" Hay {_y(repetidos)}: se leen todos, y ni el anexo ni el "
                    "ejemplo de la AEAT dicen si pueden repetirse.")
    if leidos:
        mensaje += (
            f" Se comprueba el código: {_y(leidos)}. Se lee en "
            "cbc:DocumentTypeCode, que es donde lo pone el ejemplo que la AEAT "
            "mandó por correo el 02-10-2026; el anexo nuevo, que es el que lo "
            "fijará, no está publicado."
        )
    sin_codigo = list(dict.fromkeys(sin_codigo))
    if sin_codigo:
        mensaje += (
            f" No se comprueba {_y(sin_codigo)}: "
            f"{'no lleva' if len(sin_codigo) == 1 else 'no llevan'} código en "
            "cbc:DocumentTypeCode, que es donde lo pone el ejemplo de la AEAT "
            "del 02-10-2026, y en otro sitio no se busca porque nadie ha dicho "
            "que vaya ahí."
        )
    faltan = [nombre for calificador, nombre in _L10_RECTIFICATIVA.items()
              if calificador not in presentes and calificador != "RECT:IMPORTES"]
    if faltan:
        mensaje += (f" Falta {_y(faltan)}: la AEAT escribió que todas llevan el "
                    "tipo y la modalidad. No se da por mala porque el anexo que "
                    "lo dice no está publicado.")
    modalidades = {_valor(adjunto, _CODIGO_DEL_CALIFICADOR)
                   for adjunto in presentes.get("RECT:MODALIDAD", [])}
    if "S" in modalidades and "RECT:IMPORTES" not in presentes:
        mensaje += (" La modalidad es S y no trae los importes rectificados: la "
                    "AEAT escribió el 23-09-2026 que las de sustitución los "
                    "llevan, pero ni el anexo ni el ejemplo de la AEAT dicen "
                    "cómo se escriben, así que no se da por mala.")
    incidencias.insert(
        0,
        Incidencia(
            "SPFE-RECTIFICATIVA",
            NOTA,
            mensaje,
            campo="Datos rectificados (BG-24)",
            esperado="el tipo (RECT:TIPO) y la modalidad (RECT:MODALIDAD), con L10",
            encontrado=_y(sorted(presentes)),
        ),
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
    """BT-113: si se informa, cero."""
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
                ERROR,
                "El importe pagado por adelantado no es cero. El anexo solo "
                "admite este importe si vale cero.",
                campo="Importe pagado (BT-113)",
                esperado="0",
                encontrado=escrito,
            )
        )
    return incidencias


def _nif_de(raiz, esquemas: str) -> str | None:
    """None si el NIF está con el impuesto «VAT»; si no, qué hay en su lugar."""
    encontrados = []
    for esquema in _nodos(raiz, esquemas):
        nif = _valor(esquema, "./cbc:CompanyID")
        impuesto = _valor(esquema, _IMPUESTO_DEL_ESQUEMA)
        if nif and impuesto == _IMPUESTO:
            return None
        if nif:
            encontrados.append(f"{nif} con el impuesto «{impuesto or '(sin impuesto)'}»")
    return ", ".join(encontrados) or "(falta)"


def _nif(raiz) -> list[Incidencia]:
    """BT-32 y BT-48 con BT-ES-7 y BT-ES-8: el NIF de cada parte, en «VAT».

    El anexo llama BT-32 al del vendedor —el registro fiscal de la norma— y le
    pone la ruta del esquema de impuesto «VAT», que es donde la vinculación
    escribe BT-31. Aquí se mira lo que dice la ruta, que es lo que se puede
    comprobar, y el campo se nombra como lo nombra el anexo.
    """
    incidencias: list[Incidencia] = []
    for quien, esquemas, codigos in (
        ("vendedor", _ESQUEMAS_DEL_VENDEDOR, "BT-32, BT-ES-7"),
        ("comprador", _ESQUEMAS_DEL_COMPRADOR, "BT-48, BT-ES-8"),
    ):
        encontrado = _nif_de(raiz, esquemas)
        if encontrado is None:
            continue
        incidencias.append(
            Incidencia(
                "SPFE-NIF",
                ERROR,
                f"Falta el NIF del {quien} donde lo pide el anexo: en un "
                "esquema de impuesto «VAT». La norma europea lo deja opcional; "
                "el anexo lo hace obligatorio para las dos partes.",
                campo=f"NIF del {quien} ({codigos})",
                esperado="cac:PartyTaxScheme con cbc:CompanyID y cac:TaxScheme/cbc:ID «VAT»",
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
    """BT-ES-17, 19, 42 y 46: el impuesto es «VAT» en todas partes."""
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
            "El tipo de impuesto no es «VAT». El anexo lo fija en «VAT» sin "
            "excepciones; el IGIC y el IPSI tienen su propia categoría en la "
            "lista L4, la L y la M.",
            campo=_donde("Tipo de impuesto (cac:TaxScheme/cbc:ID)", lugares),
            esperado="VAT",
            encontrado=", ".join(malos),
        )
    ]


def _tercero(raiz) -> list[Incidencia]:
    """BG-ES-3: si está el tercero, su NIF en «VAT», su nombre y su tipología."""
    incidencias: list[Incidencia] = []
    for nombre, tercero in _nombrados(_nodos(raiz, _TERCERO), "tercero"):
        faltan = [
            texto for ruta, texto in (
                (_TERCERO_NIF, "el NIF (BT-ES-12)"),
                (_TERCERO_NOMBRE, "el nombre (BT-ES-14)"),
                (_TERCERO_TIPO, "la tipología (BT-ES-15)"),
            )
            if not _valor(tercero, ruta)
        ]
        impuesto = _valor(tercero, _TERCERO_IMPUESTO)
        if impuesto != _IMPUESTO:
            faltan.append(f"el impuesto «VAT» (BT-ES-13, hay «{impuesto or '(nada)'}»)")
        if not faltan:
            continue
        incidencias.append(
            Incidencia(
                "SPFE-TERCERO",
                ERROR,
                f"Al tercero que expide la factura le falta {_y(faltan)}. Si "
                "el grupo del tercero está, el anexo pide su NIF con el "
                "impuesto «VAT», su nombre y la tipología del tercero.",
                campo=_donde("Datos del tercero (BG-ES-3)", [nombre]),
                esperado="NIF, impuesto VAT, nombre y tipología",
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
    for grupo, campo in _CATEGORIAS_EN:
        for nombre, nodo in grupos(raiz, SINTAXIS_UBL, grupo):
            for encontrado in _nodos(nodo, getattr(SINTAXIS_UBL, campo)):
                codigo = _escrito(encontrado)
                if codigo in _CATEGORIAS or codigo not in europeas:
                    continue
                lugar = nombre or ("desglose" if grupo == "desglose" else "")
                if lugar not in lugares:
                    lugares.append(lugar)
                if codigo not in malos:
                    malos.append(codigo)
    if not malos:
        return []
    mensaje = ("La categoría de IVA es de la norma europea, pero no de la lista "
               "L4 del anexo.")
    if "K" in malos:
        mensaje += " La K, la entrega intracomunitaria, no tiene código en L4."
    if "B" in malos:
        mensaje += " La B, el pago fraccionado italiano, tampoco."
    return [
        Incidencia(
            "SPFE-CATEGORIA",
            ERROR,
            mensaje,
            campo=_donde("Categoría de IVA (BT-95, BT-102, BT-118, BT-151)", lugares),
            esperado=_y(list(_L["L4"].valores)).replace(" y ", " o "),
            encontrado=", ".join(malos),
        )
    ]


def _claves_de_regimen(raiz) -> list[Incidencia]:
    """BG-32 «CLAVE DE RÉGIMEN»: una o dos en cada línea, cada una en su lista."""
    sin_clave: list[str] = []
    demasiadas: list[str] = []
    calificadores: list[tuple[str, str]] = []
    claves: list[tuple[str, str]] = []
    for nombre, linea in grupos(raiz, SINTAXIS_UBL, "lineas"):
        propiedades = _nodos(linea, _CLAVE)
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
                "Hay líneas sin clave de régimen. El anexo la pide en cada "
                "línea, como una propiedad del artículo llamada «REGI»: la "
                "clave en el valor y el impuesto (IVA, IGIC o IPSI) en el "
                "calificador.",
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
                "que son los tres que tienen lista de claves en el anexo.",
                campo=_donde("Impuesto de la clave de régimen (BT-ES-44)",
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
                "IVA, y la 20 en el IVA y no en el IGIC.",
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
        propiedades = _nodos(linea, _CATASTRO)
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
                campo=_donde("Situación del inmueble (BT-ES-43)", [n for n, _ in situaciones]),
                esperado=_y(list(_L["L6"].valores)).replace(" y ", " o "),
                encontrado=", ".join(dict.fromkeys(s for _, s in situaciones)),
            )
        )
    return incidencias


def _lineas_de_cobro(raiz) -> list[Incidencia]:
    """La lista L7, y un solo recargo, grupo de entidades y retención."""
    incidencias: list[Incidencia] = []
    identificadores = [_escrito(n) for n in _nodos(raiz, _LINEA_DE_COBRO + "/cbc:ID")]
    desconocidos = [i or "(vacío)" for i in identificadores if i not in _COBROS.values()]
    if desconocidos:
        incidencias.append(
            Incidencia(
                "SPFE-LINEA-DE-COBRO",
                ERROR,
                "Una línea de cobro no se identifica con ninguno de los cinco "
                "valores del anexo (lista L7): suplido, minoración, recargo de "
                "equivalencia, grupo de entidades o retención.",
                campo="Identificación de la línea de cobro (CollectionInvoiceLine/cbc:ID)",
                esperado="urn:aeat:names:specification:ubl:schema: y SUPL, MINO, REEQ, REGE o RETE",
                encontrado=", ".join(dict.fromkeys(desconocidos)),
            )
        )
    repetidos = [
        termino.lower() for clave, termino in _UNO_POR_FACTURA.items()
        if identificadores.count(_COBROS[clave]) > 1
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


def _recargo(raiz) -> list[Incidencia]:
    """El recargo de equivalencia: su suma y, en cada subtotal, todo."""
    faltan: list[str] = []
    for linea in _nodos(raiz, _RECARGO):
        if not _valor(linea, _RECARGO_TOTAL):
            faltan.append("la suma de los recargos (BT-ES-28)")
        for nombre, subtotal in _nombrados(_nodos(linea, _RECARGO_SUBTOTALES), "subtotal"):
            sufijo = f" del {nombre}" if nombre else ""
            for identificador, texto, fijo in (
                ("BT-ES-22", "el impuesto «VAT»", _IMPUESTO),
                ("BT-ES-23", "la categoría «S»", "S"),
                ("BT-ES-24", "la base", None),
                ("BT-ES-25", "el tipo", None),
                ("BT-ES-26", "la cuota", None),
            ):
                escrito = _valor(subtotal, _RECARGO_HIJOS[identificador])
                if not escrito or (fijo and escrito != fijo):
                    faltan.append(f"{texto}{sufijo} ({identificador})")
    if not faltan:
        return []
    return [
        Incidencia(
            "SPFE-RECARGO-DE-EQUIVALENCIA",
            ERROR,
            f"Al recargo de equivalencia le falta {_y(faltan)}. El anexo pide "
            "la suma de los recargos y, en cada subtotal, el impuesto «VAT», "
            "la categoría «S», la base, el tipo y la cuota.",
            campo="Recargo de equivalencia (BG-34, BG-ES-34)",
            esperado="la suma y cada subtotal completo",
            encontrado=f"falta {_y(faltan)}",
        )
    ]


def _retenciones(raiz) -> list[Incidencia]:
    """Las retenciones: la línea que las identifica, su total y cada una."""
    faltan: list[str] = []
    lineas = _nodos(raiz, _RETENCION)
    totales = _nodos(raiz, _RETENCIONES)
    if lineas and not _valor(raiz, _RETENCION_TOTAL):
        faltan.append("la suma de retenciones (BT-ES-33)")
    if totales and not lineas:
        faltan.append("la línea de cobro que identifica la retención (BT-ES-32)")
    for nombre, subtotal in _nombrados(_nodos(raiz, _RETENCIONES_APLICADAS), "retención"):
        sufijo = f" de la {nombre}" if nombre else ""
        for identificador, texto, fijo in (
            ("BT-ES-34", "la base", None),
            ("BT-ES-35", "el importe", None),
            ("BT-ES-36", "la categoría «S»", "S"),
            ("BT-ES-37", "el porcentaje", None),
            ("BT-ES-38", "el esquema «WTH»", "WTH"),
        ):
            escrito = _valor(subtotal, _RETENCION_HIJOS[identificador])
            if not escrito or (fijo and escrito != fijo):
                faltan.append(f"{texto}{sufijo} ({identificador})")
        concepto = _valor(subtotal, _RETENCION_HIJOS["BT-ES-39"])
        if concepto not in _L["L5"].valores:
            faltan.append(f"un concepto de la lista L5{sufijo} (BT-ES-39, hay «{concepto or '(nada)'}»)")
    if not faltan:
        return []
    return [
        Incidencia(
            "SPFE-RETENCION",
            ERROR,
            f"A las retenciones les falta {_y(faltan)}. El anexo pide la línea "
            "que las identifica, la suma, y en cada retención la base, el "
            "importe, la categoría «S», el porcentaje, el esquema «WTH» y el "
            "concepto de la lista L5.",
            campo="Retenciones (BG-34, BG-ES-4)",
            esperado="la identificación, la suma y cada retención completa",
            encontrado=f"falta {_y(faltan)}",
        )
    ]


def _grupo_de_entidades(raiz) -> list[Incidencia]:
    """El grupo de entidades: su extensión identificada y la base imponible."""
    faltan: list[str] = []
    for linea in _nodos(raiz, _GRUPO):
        if _URN_REGE not in [_escrito(n) for n in _nodos(linea, _GRUPO_EXTENSION)]:
            faltan.append("la extensión identificada con su URN (BT-ES-29)")
        if not _valor(linea, _GRUPO_BASE):
            faltan.append("la base imponible (BT-ES-30)")
    if not faltan:
        return []
    return [
        Incidencia(
            "SPFE-GRUPO-DE-ENTIDADES",
            ERROR,
            f"Al grupo de entidades le falta {_y(faltan)}. El anexo pide la "
            "extensión del régimen, identificada con su URN, y dentro la base "
            "imponible calculada según los artículos 78 y 79 de la Ley del IVA.",
            campo="Grupo de entidades (BG-34)",
            esperado=_URN_REGE,
            encontrado=f"falta {_y(faltan)}",
        )
    ]


def _qr(raiz) -> list[Incidencia]:
    """BG-24 del QR fiscal: uno como mucho, con descripción y dirección.

    Se reconoce con los dos esquemas de L10. Con el de abril solo, un QR
    escrito como el ejemplo de la AEAT del 02-10-2026 dejaba mudo a SPFE-QR:
    medido ese día, sin la dirección del QR no salía nada.
    """
    incidencias: list[Incidencia] = []
    qrs = [adjunto for calificador, adjunto in _adjuntos(raiz) if calificador == "QR"]
    if len(qrs) > 1:
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
    faltan: list[str] = []
    for qr in qrs:
        if not _valor(qr, "./cbc:DocumentDescription"):
            faltan.append("la descripción (BT-123)")
        if not _valor(qr, _QR_URL):
            faltan.append("la dirección del QR (BT-ES-47)")
    if faltan:
        incidencias.append(
            Incidencia(
                "SPFE-QR",
                ERROR,
                f"Al documento del QR fiscal le falta {_y(list(dict.fromkeys(faltan)))}. "
                "El anexo pide la descripción (VERIFACTU o la que corresponda) "
                "y la dirección del QR en cbc:UUID.",
                campo="QR fiscal (BG-24)",
                esperado="cbc:DocumentDescription y cbc:UUID",
                encontrado="(falta)",
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
            "La factura lleva líneas de cobro (suplidos, minoraciones, recargo "
            "de equivalencia, grupo de entidades o retenciones), y el anexo "
            "suma sus importes al total a pagar. La norma de 2017 no los conoce "
            "y el anexo no dice dónde se escriben, así que el cuadre del total "
            "a pagar (BR-CO-16) no se ha comprobado.",
            campo="Total a pagar (BT-115)",
            encontrado=_valor(raiz, SINTAXIS_UBL.a_pagar),
        )
    ]
