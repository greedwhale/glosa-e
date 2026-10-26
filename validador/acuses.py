"""Los acuses de la solución pública: el `DocumentStatus` con que contesta.

A qué se aplica
---------------
A todo `DocumentStatus` de UBL. Es el documento con que la solución pública
contesta a sus servicios, a todos menos a las dos descargas: lo dicen el
documento de formatos de entrada y salida de la AEAT (versión 0.1.2, del
20-10-2026, apartado 5.1.1) y su catálogo de servicios (versión 0.1.3). El
acuse no dice de quién es ni a qué servicio contesta: eso va en el sobre ebXML
que lo acompaña, que aquí no llega. Se lee como acuse de la solución pública
porque es quien lo usa, y la nota `SPFE-ACUSE-ALCANCE` lo dice.

Hasta el 26-10-2026 no se reconocía: el acuse del ejemplo oficial de remisión
(`SendInvoicesSOAP.zip`, del 15-10-2026) salía SIN COMPROBAR, con «su elemento
raíz no es de ningún documento que se valide aquí».

De dónde sale cada comprobación
-------------------------------
De lo único publicado, que es poco, y del apartado 5.2.2 del documento de
formatos:

- la cabecera (`cac:DocumentResponse/cac:Response/cbc:ResponseCode`) es 200
  si todas las facturas se aceptaron, 406 si solo una parte y 400 si ninguna;
- hay un `cac:DocumentReference` por factura, dada de alta o con error, con su
  identificador y su localizador.

Y del ejemplo: una factura dada de alta lleva `cbc:DocumentStatusCode` 200,
con la descripción «Factura Ok». **Es el único código de factura que se ha
visto.** Los de error no están publicados y aquí no se inventan: de una
factura con otro código se dice que no consta como dada de alta, que es lo que
se sabe, y el código y su descripción van tal cual.

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

from datetime import date

from validador import cifras
from validador.formato import ACUSE
from validador.incidencias import AVISO, NOTA, Incidencia

_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_NS = {"cac": _CAC, "cbc": _CBC}

# Lo que dice cada cabecera, con las palabras del documento de formatos:
# «correctamente (200), parcialmente (406) o rechazo completo (400)».
CABECERAS = {
    "200": "todas las facturas se aceptaron",
    "406": "solo se aceptó una parte de las facturas",
    "400": "no se aceptó ninguna factura",
}

# El estado de una factura dada de alta. El único que se ha visto publicado.
DADA_DE_ALTA = "200"

_CABECERA = "cac:DocumentResponse"
_CODIGO = "cac:Response/cbc:ResponseCode"
_DESCRIPCION = "cac:Response/cbc:Description"
_FACTURA = "cac:DocumentReference"
_NIF = "cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"
_LOCALIZADOR = "cbc:ReferencedDocumentInternalAddress"


def _texto(nodo, ruta: str) -> str:
    return " ".join((nodo.findtext(ruta, default="", namespaces=_NS) or "").split())


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
        "(versión 0.1.2, del 20-10-2026) y el ejemplo de remisión del "
        "15-10-2026. La cabecera dice 200 si todas las facturas se aceptaron, "
        "406 si solo una parte y 400 si ninguna, y cada factura lleva su "
        "número, su fecha, el NIF de quien la emite, su estado y el "
        "localizador con que se descarga.",
        "De los estados de cada factura solo está publicado el 200, el de "
        "dada de alta. Los códigos de error no lo están, y se enseñan tal "
        "cual, con la descripción que traigan.",
        "No se mira el sobre ebXML que acompaña al acuse, que es el que dice "
        "a qué servicio contesta y a qué envío, ni que las facturas existan o "
        "que el localizador sea válido. El acuse no dice de quién es: si no "
        "es de la solución pública, lo de esta nota no le aplica.",
    ]
    otras = raiz.findall("cac:AdditionalDocumentResponse", _NS)
    if otras:
        partes.append(
            f"Trae {len(otras)} cac:AdditionalDocumentResponse, que el ejemplo "
            "de la AEAT no usa, y no se leen."
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
                "de cac:Response, que es el que dice si se aceptaron todas las "
                "facturas (200), una parte (406) o ninguna (400). Lo que dice "
                "de cada factura se lee abajo.",
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
                "AEAT solo ha publicado tres: 200 si se aceptaron todas las "
                "facturas, 406 si una parte y 400 si ninguna. Qué quiere decir "
                "este no se sabe. Lo que dice de cada factura se lee abajo.",
                campo="Cabecera",
                esperado="200, 406 o 400",
                encontrado=codigo,
            )
        ]
    altas = sum(1 for estado in estados if estado == DADA_DE_ALTA)
    otras = len(estados) - altas
    cuenta = f"El acuse trae {_facturas(len(estados))}"
    if otras == 0:
        cuenta += ", " + ("dada de alta." if altas == 1 else "todas dadas de alta.")
    elif altas == 0:
        cuenta += ", " + ("que no consta como dada de alta." if otras == 1
                          else "y ninguna consta como dada de alta.")
    else:
        cuenta += (f": {altas} dada{'s' if altas != 1 else ''} de alta y {otras} "
                   f"que no consta{'n' if otras != 1 else ''}.")
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
                encontrado=f"{altas} dada{'s' if altas != 1 else ''} de alta, {otras} no",
            )
        )
    return incidencias


def _desacuerdo(codigo: str, altas: int, otras: int) -> str:
    if codigo == "200" and otras:
        return (f"y {otras} de las facturas no consta{'n' if otras != 1 else ''} "
                "como dada de alta.")
    if codigo == "400" and altas:
        return (f"y {altas} de las facturas consta{'n' if altas != 1 else ''} "
                "como dada de alta.")
    if codigo == "406" and not (altas and otras):
        return ("y las facturas están todas dadas de alta." if altas else
                "y ninguna de las facturas consta como dada de alta.")
    return ""


def _esperado(codigo: str) -> str:
    return {
        "200": "todas las facturas con el estado 200",
        "400": "ninguna factura con el estado 200",
        "406": "unas facturas con el estado 200 y otras no",
    }[codigo]


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
    if estado == DADA_DE_ALTA:
        if localizador:
            despues = (
                " Su localizador es lo que sirve para descargarla después, con "
                "el servicio de descarga por localizador, que la AEAT recomienda "
                "frente a la descarga por identificador: conviene guardarlo."
            )
        else:
            despues = (
                " No trae localizador, y el documento de formatos dice que cada "
                "factura lo lleva: sin él solo se puede descargar por su "
                "identificador (NIF, número y fecha)."
            )
        return Incidencia(
            "SPFE-ACUSE-ACEPTADA",
            NOTA,
            f"{_quien(factura)}, consta como dada de alta en la solución pública "
            f"(estado {estado}{dice}).{despues}",
            campo=f"Factura {numero}",
            esperado=None,
            encontrado=localizador or "(sin localizador)",
        )
    if estado:
        motivo = f"el acuse le da el estado {estado}{dice}"
    else:
        motivo = "el acuse no le da ningún estado"
    return Incidencia(
        "SPFE-ACUSE-RECHAZADA",
        AVISO,
        f"{_quien(factura)}, no consta como dada de alta: {motivo}. La AEAT no "
        "ha publicado qué quiere decir cada código de error de una factura, así "
        "que el motivo es el que diga la descripción.",
        campo=f"Factura {numero}",
        esperado=f"el estado {DADA_DE_ALTA}",
        encontrado=estado or "(sin estado)",
    )
