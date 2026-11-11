"""Los acuses de la solución pública: el `DocumentStatus` con que contesta.

A qué se aplica
---------------
A todo `DocumentStatus` de UBL. Es el documento con que la solución pública
contesta a sus servicios, a todos menos a las dos descargas: lo dicen el
documento de formatos de entrada y salida de la AEAT (versión 0.1.2, del
20-10-2026, apartado 5.1.1) y su catálogo de servicios (versión 0.1.5, del
10-11-2026, que da el mismo documento de salida a la remisión, la anulación,
las dos consultas y las dos comunicaciones de estado). El acuse no dice de
quién es ni a qué servicio contesta: eso va en el sobre ebXML que lo acompaña,
en su `Action`, y el sobre aquí no llega. Se lee como acuse de la solución
pública porque es quien lo usa, y la nota `SPFE-ACUSE-ALCANCE` lo dice.

Hasta el 26-10-2026 no se reconocía: el acuse del ejemplo oficial de remisión
(`SendInvoicesSOAP.zip`, del 15-10-2026) salía SIN COMPROBAR, con «su elemento
raíz no es de ningún documento que se valide aquí».

De dónde sale cada comprobación
-------------------------------
De lo único publicado, que es poco, y del apartado 5.2.2 del documento de
formatos:

- la cabecera (`cac:DocumentResponse/cac:Response/cbc:ResponseCode`) es 200
  si todo se aceptó, 406 si solo una parte y 400 si nada;
- hay un `cac:DocumentReference` por factura, aceptada o con error, con su
  identificador y, la de una remisión, su localizador.

Y de los ejemplos: una factura con `cbc:DocumentStatusCode` 200 es una a la
que se le aceptó lo que se pedía. **Es el único código de factura que se ha
visto**, con la descripción «Factura Ok» en la remisión, «Anulacion correcta»
en la anulación y «Factura SETTLEMENT Ok» en el pago y en el cobro. De una
factura con otro código se dice que no consta que se aceptara, que es lo que
se sabe, y el código y su descripción van tal cual.

Lo que el acuse no dice: a qué contesta
---------------------------------------
Hasta el 11-11-2026 todo acuse con 200 se leía como el de una remisión: «la
factura consta como dada de alta». `acuses.py` se escribió el 26-10 con el
único acuse publicado, que era de una remisión. Con los ejemplos de la AEAT
del 10-11-2026, Glosa-e decía eso mismo de una factura anulada, y se quejaba
de que les faltara el localizador a los acuses de anulación, de pago y de
cobro, que lo traen vacío. Está en HALLAZGOS.md.

**No se adivina el servicio por la descripción.** Es texto libre, y el
ejemplo lo demuestra: el acuse de pago (`RespuestaPagar.xml`, contestación a
un `PAYMENT`) dice «Factura SETTLEMENT Ok», que es el código del cobro. Lo que
se dice de una factura con 200 vale para cualquier servicio: que se aceptó lo
que se pedía sobre ella. El localizador, si viene, se enseña con lo que
sirve. Si no viene, se dice que el acuse de una remisión lo lleva, como
condición y no como defecto, porque este acuse puede ser de otro servicio.

Los códigos de error
--------------------
La lista de códigos de rechazo de la solución pública no está publicada. Se
hace lo que se puede sin inventar. Una regla del esquematrón de la norma
europea que tiene ficha, como `BR-CO-16`, se explica con la primera frase de
la ficha, que es la de cualquier factura que la incumpla. Un código que no es
de la norma europea, como uno que empiece por `SPFE-CORE`, `SPFE-LIST` o
`BR-ES` (las familias que se esperan para las reglas propias de la solución
pública, desde el 03-11-2026), se nombra y no se traduce, porque su
significado no está publicado. Nada publicado dice en qué campo va el código,
así que se busca en el estado y, si ahí no está, en la descripción. Los
errores de esquema no se reconocen: no se sabe cómo se escriben, y adivinarlo
sería poner nombre a lo que no se ha visto.

Lo que el ejemplo no trae
-------------------------
El acuse del ejemplo oficial no pasa el esquema de UBL 2.5: le falta
`cbc:IssueDate`, que `DocumentStatus` exige una vez. Medido el 26-10-2026 con
lxml contra el `UBL-DocumentStatus-2.5.xsd` de OASIS: es su único fallo, y con
la fecha puesta valida. El error lo da el esquema, como a cualquier documento
(lo decidió el titular el 26-10-2026: un fallo de forma es un error, venga de
quien venga), y la nota `SPFE-ACUSE-FECHA` dice qué es, porque lo que el
esquema contesta es `XSD-ORDEN` sobre `cac:DocumentResponse`, «no puede ir en
este sitio», y eso no deja ver que lo que falta es la fecha.
"""

from __future__ import annotations

import re
from datetime import date

from validador import cifras, glosario
from validador.formato import ACUSE, como_texto
from validador.incidencias import AVISO, NOTA, Incidencia

_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_NS = {"cac": _CAC, "cbc": _CBC}

# Lo que dice cada cabecera, con las palabras del documento de formatos:
# «correctamente (200), parcialmente (406) o rechazo completo (400)». Sin
# decir de qué: el mismo acuse contesta a la remisión, a la anulación y a las
# comunicaciones de estado, y en los ejemplos del 10-11-2026 la cabecera 200
# dice «Todas las facturas correctas» o «Todas las Acciones correctas».
CABECERAS = {
    "200": "se aceptó todo lo que se pedía",
    "406": "solo se aceptó una parte de lo que se pedía",
    "400": "no se aceptó nada de lo que se pedía",
}

# El estado de una factura a la que se le aceptó lo que se pedía. El único que
# se ha visto publicado, en los acuses de todos los servicios.
ACEPTADA = "200"

_CABECERA = "cac:DocumentResponse"
_CODIGO = "cac:Response/cbc:ResponseCode"
_DESCRIPCION = "cac:Response/cbc:Description"
_FACTURA = "cac:DocumentReference"
_NIF = "cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"
_LOCALIZADOR = "cbc:ReferencedDocumentInternalAddress"


def _texto(nodo, ruta: str) -> str:
    encontrado = nodo.find(ruta, namespaces=_NS)
    return " ".join((como_texto(encontrado) if encontrado is not None else "").split())


def _fecha(texto: str) -> str:
    """La fecha como la escribe el resto del informe, si es una fecha.

    Si no lo es se deja tal cual: que la fecha esté bien escrita lo mide el
    esquema, y aquí solo se dice qué factura es.
    """
    try:
        return cifras.fecha(date.fromisoformat(texto))
    except ValueError:
        return texto


def _facturas(n: int) -> str:
    return "1 factura" if n == 1 else f"{n} facturas"


def reglas(raiz, deteccion) -> list[Incidencia]:
    """Lo que se puede leer de un acuse: la cabecera y cada factura."""
    if raiz is None or not deteccion or deteccion.familia != ACUSE:
        return []
    incidencias = [_alcance(raiz)]
    if raiz.find("cbc:IssueDate", _NS) is None:
        incidencias.append(_sin_fecha())
    cabecera = raiz.find(_CABECERA, _NS)
    if cabecera is None:
        incidencias.append(
            Incidencia(
                "SPFE-ACUSE-CABECERA",
                AVISO,
                "El acuse no trae cac:DocumentResponse, que es donde la "
                "solución pública pone el resultado del envío y el estado de "
                "cada factura. Sin él, este acuse no dice si se aceptó nada.",
                campo="Cabecera",
                esperado="cac:DocumentResponse, con el código y una referencia por factura",
                encontrado="(no está)",
            )
        )
        return incidencias
    codigo = _texto(cabecera, _CODIGO)
    descripcion = _texto(cabecera, _DESCRIPCION)
    facturas = cabecera.findall(_FACTURA, _NS)
    estados = [_texto(factura, "cbc:DocumentStatusCode") for factura in facturas]
    incidencias.extend(_cabecera(codigo, descripcion, estados))
    incidencias.extend(_factura(factura) for factura in facturas)
    return incidencias


def _alcance(raiz) -> Incidencia:
    partes = [
        "Es un acuse de la solución pública de la AEAT (DocumentStatus), y se "
        "ha leído con lo que la AEAT ha publicado en su Portal de "
        "Desarrolladores: el documento de formatos de entrada y salida "
        "(versión 0.1.2, del 20-10-2026), el catálogo de servicios (versión "
        "0.1.5, del 10-11-2026) y los ejemplos de remisión, anulación y "
        "comunicación de estados que publicó con él.",
        "Con este mismo acuse contesta la solución pública a la remisión, a "
        "la anulación y a las comunicaciones de estado, y el acuse no dice a "
        "cuál: eso va en el sobre ebXML que lo acompaña, que aquí no se lee. "
        "Por eso, de cada factura se dice si se aceptó lo que se pedía sobre "
        "ella, y no qué se pedía.",
        "La cabecera dice 200 si se aceptó todo, 406 si solo una parte y 400 "
        "si nada, y cada factura lleva su número, su fecha, el NIF de quien "
        "la emite y su estado; en la remisión, también el localizador con que "
        "se descarga. De los estados de cada factura solo está publicado el "
        "200. Los códigos de error no lo están, y se enseñan tal cual, con la "
        "descripción que traigan.",
        "No se mira que las facturas existan o que el localizador sea válido. "
        "El acuse no dice de quién es: si no es de la solución pública, lo de "
        "esta nota no le aplica.",
    ]
    otras = raiz.findall("cac:AdditionalDocumentResponse", _NS)
    if otras:
        partes.append(
            f"Trae {len(otras)} cac:AdditionalDocumentResponse, que los "
            "ejemplos de remisión, anulación y estados de la AEAT no usan, y "
            "no se leen."
        )
    return Incidencia(
        "SPFE-ACUSE-ALCANCE",
        NOTA,
        " ".join(partes),
        campo="Acuse",
        encontrado="DocumentStatus",
    )


def _sin_fecha() -> Incidencia:
    return Incidencia(
        "SPFE-ACUSE-FECHA",
        NOTA,
        "Al acuse le falta cbc:IssueDate, su fecha, que el esquema de UBL 2.5 "
        "exige, y sin ella el acuse no pasa su forma. El esquema lo marca en "
        "cac:DocumentResponse, que es lo que viene donde esperaba la fecha, y "
        "por eso su error dice que cac:DocumentResponse no puede ir ahí. El "
        "acuse del ejemplo de remisión que la AEAT publicó el 15-10-2026 "
        "tampoco la lleva.",
        campo="cbc:IssueDate",
        esperado="la fecha del acuse, detrás de cbc:ID",
        encontrado="(no está)",
    )


def _cabecera(codigo: str, descripcion: str, estados: list[str]) -> list[Incidencia]:
    dice = f' ("{descripcion}")' if descripcion else ""
    if not codigo:
        return [
            Incidencia(
                "SPFE-ACUSE-CABECERA",
                AVISO,
                "La cabecera del acuse no trae su código, el cbc:ResponseCode "
                "de cac:Response, que es el que dice si se aceptó todo lo que "
                "se pedía (200), una parte (406) o nada (400). Lo que dice de "
                "cada factura se lee abajo.",
                campo="Cabecera",
                esperado="200, 406 o 400",
                encontrado="(no está)",
            )
        ]
    if codigo not in CABECERAS:
        return [
            Incidencia(
                "SPFE-ACUSE-CABECERA",
                AVISO,
                f"La cabecera del acuse trae el código {codigo}{dice}, y la "
                "AEAT solo ha publicado tres: 200 si se aceptó todo, 406 si "
                "una parte y 400 si nada. Qué quiere decir "
                "este no se sabe. Lo que dice de cada factura se lee abajo.",
                campo="Cabecera",
                esperado="200, 406 o 400",
                encontrado=codigo,
            )
        ]
    # Se cuenta por el estado y no por lo que quiere decir: «aceptada» es
    # también un estado de la factura en la solución pública (el catálogo
    # 0.1.5: «todas las facturas que se incorporan a la SPFE se consideran
    # inicialmente aceptadas»), y de una factura anulada no se puede decir eso.
    altas = sum(1 for estado in estados if estado == ACEPTADA)
    otras = len(estados) - altas
    cuenta = f"El acuse trae {_facturas(len(estados))}"
    if otras == 0:
        cuenta += (", con el estado 200." if altas == 1
                   else ", todas con el estado 200.")
    elif altas == 0:
        cuenta += (", sin el estado 200." if otras == 1
                   else ", ninguna con el estado 200.")
    else:
        cuenta += f": {altas} con el estado 200 y {otras} sin él."
    incidencias = [
        Incidencia(
            "SPFE-ACUSE-RESULTADO",
            NOTA,
            f"La cabecera es {codigo}{dice}: según la AEAT, "
            f"{CABECERAS[codigo]}. {cuenta}",
            campo="Cabecera",
            encontrado=codigo,
        )
    ]
    desacuerdo = _desacuerdo(codigo, altas, otras)
    if desacuerdo:
        incidencias.append(
            Incidencia(
                "SPFE-ACUSE-NO-CUADRA",
                AVISO,
                f"La cabecera y las facturas no dicen lo mismo: la cabecera es "
                f"{codigo}, que quiere decir que {CABECERAS[codigo]}, {desacuerdo} "
                "Lo que vale para cada factura es su estado, que va en su "
                "referencia; la cabecera es un resumen, y aquí no cuadra.",
                campo="Cabecera",
                esperado=_esperado(codigo),
                encontrado=f"{altas} con el estado 200, {otras} sin él",
            )
        )
    return incidencias


def _desacuerdo(codigo: str, altas: int, otras: int) -> str:
    if codigo == "200" and otras:
        return (f"y {otras} de las facturas no tiene{'n' if otras != 1 else ''} "
                "el estado 200.")
    if codigo == "400" and altas:
        return (f"y {altas} de las facturas tiene{'n' if altas != 1 else ''} "
                "el estado 200.")
    if codigo == "406" and not (altas and otras):
        return ("y las facturas tienen todas el estado 200." if altas else
                "y ninguna de las facturas tiene el estado 200.")
    return ""


def _esperado(codigo: str) -> str:
    return {
        "200": "todas las facturas con el estado 200",
        "400": "ninguna factura con el estado 200",
        "406": "unas facturas con el estado 200 y otras no",
    }[codigo]


# Los códigos que no son de la norma europea y se esperan de la solución
# pública. Van antes que las europeas porque `BR-ES-` también empieza por `BR-`.
_DE_LA_AEAT = re.compile(r"(?<![\w-])(?:SPFE-CORE|SPFE-LIST|BR-ES)-[A-Z0-9]+(?![\w-])")
# Las del esquematrón de la norma europea, como `BR-CO-16` o `UBL-SR-43`.
_EUROPEA = re.compile(r"(?<![\w-])(?:BR|UBL)(?:-[A-Z0-9]+)+(?![\w-])")
# La primera frase de una ficha: lo que dice de cualquier factura que incumple
# esa regla, sin lo que explica del porqué.
_PRIMERA_FRASE = re.compile(r"(.+?[.!?])(?=\s|$)", re.S)


def _regla(*textos: str) -> str:
    """Qué se sabe del código de rechazo de una factura, o nada si no es de ninguna familia.

    Se mira el primero de los textos que traiga un código: el estado manda
    sobre la descripción, que puede citar otras reglas de pasada.
    """
    for texto in textos:
        aeat = _DE_LA_AEAT.search(texto)
        if aeat:
            return (
                f"{aeat.group(0)} no es una regla de la norma europea, y la "
                "lista de códigos de la solución pública no está publicada: "
                "aquí no se traduce."
            )
        europea = _EUROPEA.search(texto)
        if europea:
            codigo = europea.group(0)
            ficha = glosario.CODIGOS.get(codigo)
            if not ficha:
                return (
                    f"Es la regla {codigo} de la norma europea, por su nombre, "
                    "pero Glosa-e no la tiene: el motivo es el que diga la "
                    "descripción."
                )
            frase = _PRIMERA_FRASE.match(ficha).group(1)
            return (
                f"Es la regla {codigo} de la norma europea: \"{frase}\" La "
                f"explicación entera, en glosa-e.com/codigo-{codigo}."
            )
    return ""


def _quien(factura) -> str:
    """La factura, dicha por lo que la identifica: NIF, número y fecha."""
    numero = _texto(factura, "cbc:ID")
    fecha = _texto(factura, "cbc:IssueDate")
    nif = _texto(factura, _NIF)
    texto = f"La factura {numero}" if numero else "Una factura sin número"
    if fecha:
        texto += f", del {_fecha(fecha)}"
    if nif:
        texto += f", de {nif}"
    return texto


def _factura(factura) -> Incidencia:
    numero = _texto(factura, "cbc:ID") or "(sin número)"
    estado = _texto(factura, "cbc:DocumentStatusCode")
    descripcion = _texto(factura, "cbc:DocumentDescription")
    localizador = _texto(factura, _LOCALIZADOR)
    dice = f', "{descripcion}"' if descripcion else ""
    if estado == ACEPTADA:
        if localizador:
            despues = (
                " Su localizador es lo que sirve para descargarla después, con "
                "el servicio de descarga por localizador, que la AEAT recomienda "
                "frente a la descarga por identificador: conviene guardarlo."
            )
        else:
            # Ni defecto ni silencio: falta donde el acuse es de una remisión,
            # y viene vacío a propósito en los de anulación y de estados. Cuál
            # de los dos es no lo dice el acuse.
            despues = (
                " No trae localizador, que es lo que lleva cada factura si es el "
                "acuse de una remisión, según el documento de formatos: sin él, "
                "solo se podría descargar por su identificador (NIF, número y "
                "fecha). El acuse no dice a qué servicio contesta, porque eso va "
                "en el sobre ebXML, y en los de anulación y de comunicación de "
                "estados el localizador viene vacío, como en los ejemplos de la "
                "AEAT del 10-11-2026."
            )
        return Incidencia(
            "SPFE-ACUSE-ACEPTADA",
            NOTA,
            f"{_quien(factura)}: la solución pública aceptó lo que se le pedía "
            f"sobre ella (estado {estado}{dice}).{despues}",
            campo=f"Factura {numero}",
            esperado=None,
            encontrado=localizador or "(sin localizador)",
        )
    if estado:
        motivo = f"el acuse le da el estado {estado}{dice}"
    else:
        motivo = "el acuse no le da ningún estado"
    regla = _regla(estado, descripcion) or (
        "La AEAT no ha publicado todavía la lista de sus códigos de error, y "
        "este no es de ninguna regla que Glosa-e reconozca: el motivo es el "
        "que diga la descripción." if estado or descripcion else
        "Sin estado no hay código que leer.")
    return Incidencia(
        "SPFE-ACUSE-RECHAZADA",
        AVISO,
        f"{_quien(factura)}: no consta que se aceptara lo que se pedía sobre "
        f"ella, porque {motivo}. {regla}",
        campo=f"Factura {numero}",
        esperado=f"el estado {ACEPTADA}",
        encontrado=estado or "(sin estado)",
    )
