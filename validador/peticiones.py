"""Las peticiones de consulta y de descarga a la solución pública.

A qué se aplica
---------------
A cada `cac:DocumentResponse` de un `ApplicationResponse` cuyo
`cbc:ResponseCode` sea QUERYBYID, DOWNLOADBYID o DOWNLOADBYLOC: la consulta por
identificador, la descarga por identificador y la descarga por localizador.
Son los tres servicios del catálogo de servicios de la AEAT (versión 0.1.5,
del 10-11-2026, apartados 6.4, 6.6 y 6.7) cuya entrada es un
`ApplicationResponse`, y así vienen en los ejemplos que la AEAT publicó ese
día. La consulta por filtro de fechas no tiene documento: sus filtros van en
el sobre ebXML (apartado 6.5.1), que aquí no llega.

La orden no tiene tabla para ninguno de los tres, porque no son mensajes de la
factura sino peticiones a un servicio: por eso no se miden en `mensajes.py`,
que solo mide lo que dicen las tablas del BOE.

Hasta el 11-11-2026 pasaban en silencio: «sin errores» y ni una nota. Medido
el 10-11-2026 con los tres ejemplos. Está en HALLAZGOS.md.

De dónde sale cada comprobación
-------------------------------
Del catálogo, y de nada más:

- **cuántas facturas pide**: 1.000 identificadores como mucho en la consulta
  (apartado 6.4.3) y 100 facturas en la descarga (apartado 6.6.3, «las
  remesas de descarga»). La descarga por localizador no tiene apartado de
  restricciones propio; el 6.7.2 dice que la diferencia con la descarga por
  identificador «se encuentra exclusivamente en el mecanismo utilizado para
  identificar la factura», y por eso se le aplica el mismo máximo;
- **que cada factura venga identificada**: por «NIF del emisor + Nº de
  serie-factura + Fecha de expedición» en la consulta y en la descarga por
  identificador (apartados 6.4.2 y 6.6.2), y por su localizador en la otra.
  Dónde va cada dato se toma de los ejemplos, que es lo único publicado: el
  número en `cbc:ID`, la fecha en `cbc:IssueDate` y el NIF en
  `cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID`; el localizador, en
  `cbc:ID`.

Las dos quejas son AVISO y no ERROR, como en los acuses: lo que manda en estos
servicios es la Sede electrónica, y el catálogo es lo que la AEAT ha publicado
de ella, en una versión que todavía cambia.

Lo que no se mide
-----------------
La forma del localizador: solo se ha visto `LOCGENV1:`, y darla por buena o
mala sería poner nombre a lo que no está publicado. Tampoco el rol con que se
actúa, emisor o destinatario, que el catálogo exige y no dice dónde va, ni que
las facturas existan. Lo dice la nota `SPFE-PETICION-ALCANCE`.
"""

from __future__ import annotations

from dataclasses import dataclass

from validador.formato import RESPUESTA, como_texto
from validador.incidencias import AVISO, NOTA, Incidencia

_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_NS = {"cac": _CAC, "cbc": _CBC}

_CODIGO = "cac:Response/cbc:ResponseCode"
_FACTURA = "cac:DocumentReference"


@dataclass(frozen=True)
class Peticion:
    nombre: str
    apartado: str
    maximo: int
    apartado_del_maximo: str
    por_localizador: bool


PETICIONES = {
    "QUERYBYID": Peticion("la consulta por identificador", "6.4", 1000, "6.4.3", False),
    "DOWNLOADBYID": Peticion("la descarga por identificador", "6.6", 100, "6.6.3", False),
    "DOWNLOADBYLOC": Peticion("la descarga por localizador", "6.7", 100, "6.6.3", True),
}

# Los tres datos que identifican una factura, según el catálogo, y dónde los
# ponen los ejemplos.
_IDENTIFICADOR = (
    ("el NIF del emisor", "cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"),
    ("el número", "cbc:ID"),
    ("la fecha de expedición", "cbc:IssueDate"),
)


def _texto(nodo, ruta: str) -> str:
    encontrado = nodo.find(ruta, namespaces=_NS)
    return " ".join((como_texto(encontrado) if encontrado is not None else "").split())


def _miles(n: int) -> str:
    """1.000 y no 1,000 ni 1000, como el catálogo."""
    return f"{n:,}".replace(",", ".")


def _y(cosas: list[str]) -> str:
    return cosas[0] if len(cosas) == 1 else ", ".join(cosas[:-1]) + " y " + cosas[-1]


def reglas(raiz, deteccion) -> list[Incidencia]:
    """Qué es cada petición, y si pide lo que el catálogo admite."""
    if raiz is None or not deteccion or deteccion.familia != RESPUESTA:
        return []
    incidencias: list[Incidencia] = []
    for respuesta in raiz.findall("cac:DocumentResponse", _NS):
        codigo = _texto(respuesta, _CODIGO)
        peticion = PETICIONES.get(codigo)
        if peticion is None:
            continue
        facturas = respuesta.findall(_FACTURA, _NS)
        incidencias.append(_alcance(codigo, peticion))
        if not facturas:
            incidencias.append(
                Incidencia(
                    "SPFE-PETICION-FACTURA",
                    AVISO,
                    f"Es {peticion.nombre} ({codigo}) y no pide ninguna factura: "
                    "cada una va en un cac:DocumentReference dentro de "
                    "cac:DocumentResponse, y no hay ninguno.",
                    campo="Facturas",
                    esperado="al menos un cac:DocumentReference",
                    encontrado="(ninguno)",
                )
            )
        if len(facturas) > peticion.maximo:
            incidencias.append(
                Incidencia(
                    "SPFE-PETICION-LIMITE",
                    AVISO,
                    f"Pide {len(facturas)} facturas, y el catálogo de servicios de "
                    f"la AEAT pone para {peticion.nombre} un máximo de "
                    f"{_miles(peticion.maximo)} (apartado "
                    f"{peticion.apartado_del_maximo}).",
                    campo="Facturas",
                    esperado=f"{peticion.maximo} como mucho",
                    encontrado=str(len(facturas)),
                )
            )
        incidencias.extend(_factura(f, codigo, peticion) for f in facturas
                           if _falta(f, peticion))
    return incidencias


def _falta(factura, peticion: Peticion) -> list[str]:
    if peticion.por_localizador:
        return [] if _texto(factura, "cbc:ID") else ["el localizador"]
    return [nombre for nombre, ruta in _IDENTIFICADOR if not _texto(factura, ruta)]


def _factura(factura, codigo: str, peticion: Peticion) -> Incidencia:
    faltan = _falta(factura, peticion)
    if peticion.por_localizador:
        mensaje = (
            f"Es {peticion.nombre} ({codigo}), y una de las facturas que pide "
            "no trae su localizador, en el cbc:ID de su cac:DocumentReference: "
            "sin él no se sabe qué factura es."
        )
        esperado = "el localizador, en cbc:ID"
        campo = "Factura (sin localizador)"
    else:
        numero = _texto(factura, "cbc:ID")
        mensaje = (
            f"Es {peticion.nombre} ({codigo}), y a una de las facturas que pide "
            f"le falta {_y(faltan)}. El catálogo de servicios de la AEAT dice "
            "que una factura se identifica por el NIF del emisor, número y "
            "fecha de expedición, los tres: sin uno, no se sabe cuál es."
        )
        esperado = "NIF del emisor, número y fecha de expedición"
        campo = f"Factura {numero}" if numero else "Factura (sin número)"
    return Incidencia(
        "SPFE-PETICION-FACTURA",
        AVISO,
        mensaje,
        campo=campo,
        esperado=esperado,
        encontrado="(falta " + _y(faltan) + ")",
    )


def _alcance(codigo: str, peticion: Peticion) -> Incidencia:
    como = ("por su localizador" if peticion.por_localizador
            else "por el NIF del emisor, su número y su fecha")
    return Incidencia(
        "SPFE-PETICION-ALCANCE",
        NOTA,
        f"Es la petición de {peticion.nombre} a la solución pública de la AEAT "
        f"({codigo}), y se ha leído con su catálogo de servicios (apartado "
        f"{peticion.apartado}) y los ejemplos que publicó el 10-11-2026. La "
        "orden no le da tabla, y el catálogo no dice campo a campo qué lleva: "
        f"se mira cuántas facturas pide (como mucho {_miles(peticion.maximo)}) "
        f"y que cada una venga identificada {como}. No se mira el sobre "
        "ebXML que la acompaña, ni que diga el rol con que se actúa, emisor o "
        "destinatario, que el catálogo pide y no dice dónde va, ni que las "
        "facturas existan."
        + (" Tampoco la forma del localizador, que no está publicada."
           if peticion.por_localizador else ""),
        campo="Código de respuesta",
        encontrado=codigo,
    )
