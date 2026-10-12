"""Lo que la orden pide a sus mensajes: la anulación y los ocho estados.

A qué se aplica
---------------
A cada `cac:DocumentResponse` de un `ApplicationResponse` cuyo
`cbc:ResponseCode` sea uno de los nueve que define la Orden HAC/1028/2026:
`CANCELINVOICE`, el mensaje de anulación de una factura o copia fiel (la
segunda tabla del anexo I), y los ocho del anexo II, el pago, el rechazo, el
cobro y el impago con sus bajas.

El código y no el identificador de especificación, porque la orden no le da
ninguno a los mensajes: sus tablas no tienen fila para `cbc:CustomizationID`,
y lo que dice cuál es cada uno es su código. Ninguno de los nueve es de la
lista de códigos de respuesta de UN/CEFACT (UNCL 4343) que usa Peppol (`AP`,
`RE`, `AB`…), así que una respuesta de otra red no se confunde con uno de
estos. Una respuesta con otro código sigue como estaba: se le mira la forma y
la firma, y del contenido el informe dice que no se mira.

Hasta el 12-10-2026 no se medía ninguno, y medido sobre `26e9a5d` con
mensajes escritos aquí: de nueve rotos (sin la fecha, sin el vencimiento del
pago, sin el NIF de la factura, un rechazo con un motivo que no está en la
lista) ocho salían sin una queja, y el noveno, una anulación escrita como
dice el BOE, solo por la forma.

De dónde sale cada comprobación
-------------------------------
De la tabla de cada mensaje, que `mensajes_es` trae del XML del BOE, y no de
una lista escrita aquí. Al importar se lee fila a fila y cada fila tiene que
ser de una clase que este módulo sabe medir: la fecha del mensaje, una fecha
con su condición, un indicador, el motivo del rechazo o un dato de la
factura. Una fila que no se entienda, un dato de la factura que deje de ser
obligatorio o un mensaje nuevo hacen que el módulo **no se importe**: un
anexo regenerado no deja reglas que miran lo de antes sin que nadie se entere.

Las erratas de las rutas
------------------------
La columna de la ruta trae cuatro clases de errata de escritura, que se
arreglan al leerla y se cuentan en `ARREGLOS` (si el BOE las corrige, la
cuenta cambia y una prueba salta):

- **dos rutas en una celda**, una detrás de otra: la de la fecha
  (`cac:Status/cbc:ReferenceDate`) y la de su condición
  (`cac:Status/cac:Condition/cbc:AttributeID=DueDate`). Son las dos mitades
  de un mismo campo, y así se leen;
- **un renglón partido** detrás de una barra, `DocumentResponse/ cac:Response`;
- **un espacio donde va una barra**, `DocumentResponse cac:Response`;
- **una barra doble**, `cac:Response//cac:Status`.

Y la tabla del mensaje de anulación trae dos que no son de escritura, y por
eso las dice la nota `SPFE-MENSAJE-ALCANCE` en cada anulación:

- **cuelga la factura anulada de `cac:Response`**, que en UBL 2.5 no tiene
  `cac:DocumentReference`. Lo tiene `cac:DocumentResponse`, obligatorio y
  repetible, que es donde la pone el anexo II. Se lee ahí: es el único sitio
  donde cabe;
- **pone el nombre del vendedor en `cac:PartyTaxScheme/cac:PartyLegalEntity`**,
  y `cac:PartyTaxScheme` no tiene `cac:PartyLegalEntity`. Hay dos arreglos de
  un paso, y no se sabe cuál quiso la orden: el de quitar `cac:PartyTaxScheme`,
  que es como lo escribe el anexo II, o el de quitar `cac:PartyLegalEntity`,
  porque `cac:PartyTaxScheme` tiene su propio `cbc:RegistrationName`. Se
  buscan los dos, y solo falta si no está en ninguno.

Lo que no se mide
-----------------
Lo dice la nota `SPFE-MENSAJE-ALCANCE` de cada mensaje: lo que la orden deja a
la Sede electrónica, la cabecera de la respuesta, que la factura exista y que
las fechas sean ciertas.
"""

from __future__ import annotations

import collections
import re
from dataclasses import dataclass

from validador import mensajes_es, nif
from validador.codigo_unico import limpiar_nif, parece_de_fuera
from validador.formato import RESPUESTA
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia
from validador.solucion_publica import AnexoCambiado

_CAC = "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
_NS = {"cac": _CAC, "cbc": _CBC}

# Cómo se llama cada mensaje en lo que lee quien recibe el informe. Escrito
# aquí, y no sacado del título de la tabla, porque el título está en
# mayúsculas y dice quién lo manda, no qué es. Si la orden trae un mensaje
# nuevo, no se importa hasta ponerle nombre.
NOMBRES = {
    "CANCELINVOICE": "el mensaje de anulación de la factura",
    "PAYMENT": "la comunicación del pago",
    "CANCELPAYMENT": "la baja de la comunicación del pago",
    "REJECTION": "la comunicación del rechazo",
    "CANCELREJECTION": "la baja de la comunicación del rechazo",
    "SETTLEMENT": "la comunicación del cobro",
    "CANCELSETTLEMENT": "la baja de la comunicación del cobro",
    "DEFAULT": "la comunicación del impago",
    "CANCELDEFAULT": "la baja de la comunicación del impago",
}
if set(NOMBRES) != set(mensajes_es.MENSAJES):
    raise AnexoCambiado(
        f"los mensajes de la orden ya no son estos: {sorted(mensajes_es.MENSAJES)}")


# --- Las rutas, leídas y arregladas a la vista ------------------------------

_RAIZ = "ApplicationResponse/cac:DocumentResponse/"
if mensajes_es.RUTA_DEL_CODIGO != _RAIZ + "cac:Response/cbc:ResponseCode":
    raise AnexoCambiado(
        f"el código del mensaje ya no va donde iba: {mensajes_es.RUTA_DEL_CODIGO}")

_FACTURA = "cac:DocumentReference"
_FACTURA_EN_LA_RESPUESTA = "cac:Response/" + _FACTURA
_VENDEDOR = _FACTURA + "/cac:IssuerParty"
_NOMBRE_DENTRO_DEL_IMPUESTO = (
    _VENDEDOR + "/cac:PartyTaxScheme/cac:PartyLegalEntity/cbc:RegistrationName")

# Los cuatro datos que identifican la factura de la que se informa, que son
# los del código único del artículo 6 más el nombre: el número, la fecha de
# expedición y el NIF del emisor. Cada uno con las rutas, relativas a
# `cac:DocumentReference`, donde se busca.
_NUMERO = "el número"
_FECHA_DE_EXPEDICION = "la fecha de expedición"
_NIF = "el NIF del emisor"
_NOMBRE = "el nombre o razón social del emisor"
_DATOS = {
    "cbc:ID": _NUMERO,
    "cbc:IssueDate": _FECHA_DE_EXPEDICION,
    "cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID": _NIF,
    "cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName": _NOMBRE,
}
_NOMBRE_EN_EL_IMPUESTO = "cac:IssuerParty/cac:PartyTaxScheme/cbc:RegistrationName"

_FECHA = "cac:Response/cbc:EffectiveDate"
_STATUS = "cac:Response/cac:Status"
_FECHA_DE_ESTADO = _STATUS + "/cbc:ReferenceDate"
_CONDICION = re.compile(re.escape(_STATUS) + r"/cac:Condition/cbc:AttributeID=([A-Za-z]+)$")
_RAZON = re.compile(re.escape(_STATUS) + r"/cbc:StatusReason=([A-Za-z]+)$")
_MOTIVO = _STATUS + "/cbc:ConditionCode"

DOS_RUTAS = "dos rutas en una celda"
RENGLON = "un renglón partido detrás de una barra"
ESPACIO = "un espacio donde va una barra"
BARRA_DOBLE = "una barra doble"
FACTURA_EN_LA_RESPUESTA = "la factura anulada colgada de cac:Response"
NOMBRE_EN_EL_IMPUESTO = "el nombre del vendedor dentro de cac:PartyTaxScheme"


def _rutas(celda: str, arreglos: collections.Counter) -> list[str]:
    """Las rutas de una celda, relativas a `cac:DocumentResponse` y arregladas.

    Cada arreglo se cuenta en `arreglos`. Lo que después de arreglado no
    empiece por la raíz no se sabe leer, y el módulo no se importa.
    """
    if not celda.strip():
        return []
    trozos = [t for t in re.split(r"\s*(?=ApplicationResponse/)", celda.strip()) if t]
    if len(trozos) > 1:
        arreglos[DOS_RUTAS] += 1
    salida = []
    for ruta in trozos:
        if re.search(r"/\s+", ruta):
            arreglos[RENGLON] += 1
            ruta = re.sub(r"/\s+", "/", ruta)
        if re.search(r"\s", ruta):
            arreglos[ESPACIO] += 1
            ruta = re.sub(r"\s+", "/", ruta)
        if "//" in ruta:
            arreglos[BARRA_DOBLE] += 1
            ruta = re.sub(r"/{2,}", "/", ruta)
        if not ruta.startswith(_RAIZ):
            raise AnexoCambiado(f"una ruta que no empieza por {_RAIZ}: {ruta}")
        ruta = ruta[len(_RAIZ):]
        if ruta == _FACTURA_EN_LA_RESPUESTA or ruta.startswith(_FACTURA_EN_LA_RESPUESTA + "/"):
            arreglos[FACTURA_EN_LA_RESPUESTA] += 1
            ruta = ruta[len("cac:Response/"):]
        salida.append(ruta)
    return salida


# --- Lo que se mide de cada mensaje, leído de su tabla ------------------------


@dataclass(frozen=True)
class Plan:
    """Lo que la tabla de un mensaje pide, en las clases que aquí se miden."""

    codigo: str
    anexo: str
    # El término de la fecha del mensaje (`cbc:EffectiveDate`), si la pide.
    fecha: str
    # Las fechas que van en un `cac:Status` con su condición: atributo →
    # (término, obligatoria).
    fechas: dict
    # Las condiciones sin fecha, que son indicadores: atributo → término.
    indicadores: dict
    # Los `cbc:StatusReason` que la tabla prevé: valor → término.
    razones: dict
    # La lista del motivo del rechazo, si lo pide.
    motivo: str
    # Si caben varias facturas en un mensaje.
    varias_facturas: bool
    # Los datos de cada factura: nombre → rutas donde se busca.
    datos: dict
    # Las erratas que se le arreglaron a su tabla al leerla, contadas.
    arreglos: collections.Counter

    @property
    def erratas(self) -> list[str]:
        """Las que no son de escritura, que la nota dice."""
        return [e for e in (FACTURA_EN_LA_RESPUESTA, NOMBRE_EN_EL_IMPUESTO) if self.arreglos[e]]

    @property
    def nombre(self) -> str:
        return NOMBRES[self.codigo]

    @property
    def condiciones(self) -> list[str]:
        return [*self.fechas, *self.indicadores]


def _plan(codigo: str, mensaje) -> Plan:
    fecha, fechas, indicadores, razones = "", {}, {}, {}
    motivo, varias, datos = "", None, {}
    arreglos = collections.Counter()
    for fila in mensaje.filas:
        rutas = _rutas(fila.ruta, arreglos)
        donde = f"{codigo}, «{fila.termino}»"
        if not rutas or rutas == [_FACTURA]:
            # El grupo de la factura: sin ruta en el anexo II, con la de
            # `cac:Response` (ya arreglada) en la anulación.
            if not fila.termino.isupper() or not fila.termino.startswith("FACTURA"):
                raise AnexoCambiado(f"{donde}: una fila sin ruta que no es el grupo de la factura")
            if varias is not None:
                raise AnexoCambiado(f"{donde}: dos grupos de factura")
            varias = fila.repetible
        elif rutas == [_VENDEDOR]:
            # «DATOS DEL VENDEDOR», el grupo de dentro: lo que se mide son
            # sus dos campos, que vienen detrás.
            if not fila.obligatorio:
                raise AnexoCambiado(f"{donde}: el vendedor ya no es obligatorio")
        elif rutas == [_FECHA]:
            if not fila.obligatorio or fecha:
                raise AnexoCambiado(f"{donde}: la fecha del mensaje ya no es una y obligatoria")
            fecha = fila.termino.rstrip(".")
        elif len(rutas) == 2 and rutas[0] == _FECHA_DE_ESTADO and _CONDICION.match(rutas[1]):
            atributo = _CONDICION.match(rutas[1]).group(1)
            if fila.obligatorio and atributo != "DueDate":
                # `SPFE-MENSAJE-VENCIMIENTO` es la de la fecha de vencimiento:
                # otra fecha obligatoria necesitaría su propia regla.
                raise AnexoCambiado(f"{donde}: una fecha obligatoria que no es el vencimiento")
            fechas[atributo] = (fila.termino, fila.obligatorio)
        elif len(rutas) == 1 and _CONDICION.match(rutas[0]) and fila.tipo == "Indicador":
            indicadores[_CONDICION.match(rutas[0]).group(1)] = fila.termino
        elif len(rutas) == 1 and _RAZON.match(rutas[0]) and fila.tipo == "Indicador":
            razones[_RAZON.match(rutas[0]).group(1)] = fila.termino
        elif rutas == [_MOTIVO]:
            lista = re.fullmatch(r"Código \((L\d+)\)", fila.tipo)
            if not lista or lista.group(1) not in mensajes_es.LISTAS or not fila.obligatorio:
                raise AnexoCambiado(f"{donde}: el motivo ya no es obligatorio o no tiene lista")
            motivo = lista.group(1)
        elif len(rutas) == 1 and rutas[0].startswith(_FACTURA + "/"):
            relativa = rutas[0][len(_FACTURA) + 1:]
            if rutas[0] == _NOMBRE_DENTRO_DEL_IMPUESTO:
                arreglos[NOMBRE_EN_EL_IMPUESTO] += 1
                datos[_NOMBRE] = ("cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName",
                                  _NOMBRE_EN_EL_IMPUESTO)
            elif relativa in _DATOS:
                datos[_DATOS[relativa]] = (relativa,)
            else:
                raise AnexoCambiado(
                    f"{donde}: un dato de la factura que no se sabe medir: {relativa}")
            if not fila.obligatorio:
                raise AnexoCambiado(f"{donde}: un dato de la factura ya no es obligatorio")
        else:
            raise AnexoCambiado(f"{donde}: una fila que no se sabe medir: {fila.ruta}")
    if varias is None and len(datos) == len(_DATOS):
        # Los mensajes de baja no traen fila de grupo: sus cuatro datos van en
        # el primer nivel. Es una factura, como en los de alta.
        varias = False
    if varias is None or set(datos) != set(_DATOS.values()):
        raise AnexoCambiado(
            f"{codigo}: la factura no lleva los cuatro datos de siempre: {sorted(datos)}")
    return Plan(codigo, mensaje.anexo, fecha, fechas, indicadores, razones, motivo,
                varias, datos, arreglos)


PLANES = {codigo: _plan(codigo, mensaje) for codigo, mensaje in mensajes_es.MENSAJES.items()}
# Todas las erratas arregladas, de todas las tablas: una prueba fija cuántas
# hay de cada clase, y si el BOE corrige alguna, salta.
ARREGLOS = sum((plan.arreglos for plan in PLANES.values()), collections.Counter())
_MOTIVOS = {clave: lista.valores for clave, lista in mensajes_es.LISTAS.items()}


# --- Las reglas -------------------------------------------------------------


def _texto(nodo, ruta: str) -> str:
    return " ".join(" ".join(nodo.xpath(f"{ruta}//text()", namespaces=_NS)).split())


def _y(cosas: list[str]) -> str:
    return cosas[0] if len(cosas) == 1 else ", ".join(cosas[:-1]) + " y " + cosas[-1]


def _o(cosas) -> str:
    cosas = [f"«{c}»" for c in cosas]
    return cosas[0] if len(cosas) == 1 else ", ".join(cosas[:-1]) + " o " + cosas[-1]


def _de(nombre: str) -> str:
    """«de» delante de un nombre, con la contracción: «del mensaje», no «de el»."""
    return "del " + nombre[3:] if nombre.startswith("el ") else "de " + nombre


def _mayuscula(texto: str) -> str:
    return texto[0].upper() + texto[1:]


def reglas(raiz, deteccion) -> list[Incidencia]:
    """Las tablas de la orden, sobre cada mensaje que lleve uno de sus códigos."""
    if raiz is None or not deteccion or deteccion.familia != RESPUESTA:
        return []
    respuestas = raiz.findall("cac:DocumentResponse", _NS)
    medidas = []
    incidencias: list[Incidencia] = []
    for respuesta in respuestas:
        plan = PLANES.get(_texto(respuesta, "cac:Response/cbc:ResponseCode"))
        if plan is None:
            continue
        medidas.append(plan)
        incidencias.extend(_fecha(respuesta, plan))
        incidencias.extend(_estado(respuesta, plan))
        incidencias.extend(_motivo(respuesta, plan))
        incidencias.extend(_facturas(respuesta, plan))
    if not medidas:
        return []
    return [_alcance(medidas, len(respuestas) - len(medidas))] + incidencias


def _fecha(respuesta, plan: Plan) -> list[Incidencia]:
    if not plan.fecha or _texto(respuesta, _FECHA):
        return []
    return [
        Incidencia(
            "SPFE-MENSAJE-FECHA",
            ERROR,
            f"Falta la {plan.fecha[0].lower() + plan.fecha[1:]} en "
            f"{plan.nombre}: la orden la pide en el cbc:EffectiveDate de la "
            "respuesta.",
            campo=plan.fecha,
            esperado="una fecha en cac:Response/cbc:EffectiveDate",
            encontrado="(nada)",
        )
    ]


def _estado(respuesta, plan: Plan) -> list[Incidencia]:
    """Lo que va en `cac:Status`: las fechas con su condición y los indicadores."""
    salida = []
    vistas = collections.Counter()
    estados = respuesta.findall(_STATUS, _NS)
    for estado in estados:
        con_fecha = bool(_texto(estado, "cbc:ReferenceDate"))
        for condicion in estado.findall("cac:Condition", _NS):
            atributo = _texto(condicion, "cbc:AttributeID")
            vistas[atributo] += 1
            if atributo in plan.fechas and not con_fecha:
                salida.append(Incidencia(
                    "SPFE-MENSAJE-ESTADO",
                    ERROR,
                    f"La condición {atributo} ({plan.fechas[atributo][0].lower()}) "
                    f"va sin su fecha en {plan.nombre}: la orden la pone en el "
                    "cbc:ReferenceDate del mismo cac:Status.",
                    campo=plan.fechas[atributo][0],
                    esperado="cbc:ReferenceDate junto a la condición",
                    encontrado="(nada)",
                ))
            elif atributo not in plan.fechas and atributo not in plan.indicadores:
                salida.append(_no_prevista(plan, "la condición", atributo, plan.condiciones))
        for razon in estado.findall("cbc:StatusReason", _NS):
            valor = " ".join("".join(razon.itertext()).split())
            if valor not in plan.razones:
                salida.append(_no_prevista(plan, "el cbc:StatusReason", valor, list(plan.razones)))
        if not plan.motivo and _texto(estado, "cbc:ConditionCode"):
            salida.append(_no_prevista(
                plan, "el cbc:ConditionCode", _texto(estado, "cbc:ConditionCode"), []))
    for atributo, veces in vistas.items():
        if veces > 1 and atributo in plan.condiciones:
            salida.append(Incidencia(
                "SPFE-MENSAJE-ESTADO",
                ERROR,
                f"La condición {atributo} va {veces} veces en {plan.nombre}, y la "
                "orden la pone una sola vez: con dos no se sabe cuál vale.",
                campo=(plan.fechas.get(atributo) or (plan.indicadores.get(atributo),))[0],
                esperado="una vez",
                encontrado=f"{veces} veces",
            ))
    for atributo, (termino, obligatoria) in plan.fechas.items():
        if obligatoria and not any(
            _texto(e, "cbc:ReferenceDate")
            and atributo in [_texto(c, "cbc:AttributeID") for c in e.findall("cac:Condition", _NS)]
            for e in estados
        ):
            salida.append(Incidencia(
                "SPFE-MENSAJE-VENCIMIENTO",
                ERROR,
                f"Falta la {termino[0].lower() + termino[1:]} en {plan.nombre}. "
                "Es lo que el destinatario está obligado a comunicar con el pago "
                "(apartado 1 del artículo 7 de la orden), y va en un cac:Status con su fecha en "
                f"cbc:ReferenceDate y la condición {atributo}.",
                campo=termino,
                esperado=f"cac:Status con cbc:ReferenceDate y la condición {atributo}",
                encontrado="(nada)",
            ))
    return salida


def _no_prevista(plan: Plan, que: str, valor: str, previstas: list[str]) -> Incidencia:
    if previstas:
        cuales = (f"allí solo están {_y([f'«{p}»' for p in previstas])}"
                  if len(previstas) > 1 else f"allí solo está «{previstas[0]}»")
    else:
        cuales = "allí no hay ninguno" if que != "la condición" else "allí no hay ninguna"
    return Incidencia(
        "SPFE-MENSAJE-ESTADO",
        AVISO,
        f"{_mayuscula(plan.nombre)} lleva {que} «{valor}», que su "
        f"tabla de la orden no prevé: {cuales}. Si es una errata, lo que "
        "quería decir no se ha leído.",
        campo="cac:Status",
        esperado=_o(previstas) if previstas else "nada",
        encontrado=valor or "(vacío)",
    )


def _motivo(respuesta, plan: Plan) -> list[Incidencia]:
    if not plan.motivo:
        return []
    valores = _MOTIVOS[plan.motivo]
    lista = "; ".join(f"{k}, {v.rstrip('.').lower()}" for k, v in valores.items())
    escritos = [
        " ".join("".join(c.itertext()).split())
        for c in respuesta.findall(_STATUS + "/cbc:ConditionCode", _NS)
    ]
    campo = "Motivo de rechazo"
    if not escritos:
        return [Incidencia(
            "SPFE-MENSAJE-MOTIVO",
            ERROR,
            f"Falta el motivo del rechazo en {plan.nombre}: la orden lo pide en "
            f"el cbc:ConditionCode de un cac:Status, con un valor de su lista "
            f"{plan.motivo} ({lista}).",
            campo=campo,
            esperado=_o(valores),
            encontrado="(nada)",
        )]
    salida = []
    if len(escritos) > 1:
        salida.append(Incidencia(
            "SPFE-MENSAJE-MOTIVO",
            ERROR,
            f"{_mayuscula(plan.nombre)} lleva {len(escritos)} "
            "motivos, y la orden pide uno.",
            campo=campo,
            esperado="un motivo",
            encontrado=", ".join(escritos),
        ))
    for escrito in escritos:
        if escrito not in valores:
            salida.append(Incidencia(
                "SPFE-MENSAJE-MOTIVO",
                ERROR,
                f"«{escrito}» no es un motivo de rechazo de la lista "
                f"{plan.motivo} del anexo II: {lista}.",
                campo=campo,
                esperado=_o(valores),
                encontrado=escrito or "(vacío)",
            ))
    return salida


def _facturas(respuesta, plan: Plan) -> list[Incidencia]:
    facturas = respuesta.findall(_FACTURA, _NS)
    campo = "Factura informada" if not plan.varias_facturas else "Factura anulada"
    if not facturas:
        return [Incidencia(
            "SPFE-MENSAJE-FACTURA",
            ERROR,
            f"{_mayuscula(plan.nombre)} no dice de qué factura "
            "es: falta el cac:DocumentReference.",
            campo=campo,
            esperado="cac:DocumentResponse/cac:DocumentReference",
            encontrado="(nada)",
        )]
    salida = []
    if len(facturas) > 1 and not plan.varias_facturas:
        salida.append(Incidencia(
            "SPFE-MENSAJE-FACTURA",
            ERROR,
            f"{_mayuscula(plan.nombre)} informa de una sola factura (su tabla "
            f"le da 1..1), y lleva {len(facturas)}.",
            campo=campo,
            esperado="un cac:DocumentReference",
            encontrado=f"{len(facturas)}",
        ))
    for factura in facturas:
        numero = _texto(factura, "cbc:ID")
        cual = f"la factura {numero}" if numero else "la factura sin número"
        faltan = [dato for dato, rutas in plan.datos.items()
                  if not any(_texto(factura, r) for r in rutas)]
        if faltan:
            salida.append(Incidencia(
                "SPFE-MENSAJE-FACTURA",
                ERROR,
                f"A {cual} {_de(plan.nombre)} le "
                f"{'falta' if len(faltan) == 1 else 'faltan'} {_y(faltan)}. Con el "
                "número, la fecha y el NIF del emisor es como la solución "
                "pública identifica la factura (su código único, artículo 6 de "
                "la orden).",
                campo=campo,
                esperado=_y(list(plan.datos)),
                encontrado="falta " + _y(faltan),
            ))
        escrito = _texto(factura, "cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID")
        if not escrito:
            continue
        if parece_de_fuera(escrito):
            salida.append(Incidencia(
                "SPFE-MENSAJE-FACTURA",
                AVISO,
                f"El emisor de {cual} no lleva un NIF español sino un número de "
                f"otro país, y la orden pide el NIF del vendedor.",
                campo="NIF emisor",
                esperado="un NIF español",
                encontrado=escrito,
            ))
            continue
        resultado = nif.validar(limpiar_nif(escrito))
        if not resultado:
            salida.append(Incidencia(
                "SPFE-MENSAJE-FACTURA",
                ERROR,
                f"El NIF del emisor de {cual} no es válido, y es parte de lo que "
                f"identifica la factura. {resultado.motivo}",
                campo="NIF emisor",
                encontrado=escrito,
            ))
    return salida


def _alcance(medidas: list[Plan], otras: int) -> Incidencia:
    codigos = list(dict.fromkeys(p.codigo for p in medidas))
    nombres = [PLANES[c].nombre for c in codigos]
    anexos = sorted({PLANES[c].anexo for c in codigos})
    tablas = "su tabla" if len(codigos) == 1 else "sus tablas"
    de_anexo = _y([f"anexo {a}" for a in anexos])
    # El artículo que deja a la Sede las especificaciones de los estados es
    # el 7.3; la anulación no tiene uno propio, y no se le inventa.
    articulo = " (apartado 3 del artículo 7)" if "II" in anexos else ""
    # La fecha de vencimiento solo la llevan el pago, el cobro y el impago:
    # decirla en una baja sería hablar de lo que el mensaje no trae.
    vencimiento = any("DueDate" in PLANES[c].fechas or c == "DEFAULT" for c in codigos)
    partes = [
        f"Es {_y(nombres)} de la solución pública ({', '.join(codigos)}), y se ha "
        f"medido con {tablas} de la Orden HAC/1028/2026 ({de_anexo}).",
        "No se mide lo que la orden deja a la Sede electrónica de la AEAT, que "
        f"todavía no lo ha sacado: las especificaciones técnicas y la volumetría{articulo}, "
        "y con ellas la cabecera de la respuesta (quién la manda, a quién, su "
        "número y su fecha), que las tablas no definen. Tampoco que la factura "
        "exista y sea esa, ni que las fechas sean ciertas"
        + (": la de vencimiento se calcula con la Ley 3/2004, y eso no se ve en "
           "el mensaje." if vencimiento else "."),
        "El NIF del emisor se acepta con el prefijo ES y sin él: la tabla dice "
        "NIF y lo pone en cac:PartyTaxScheme/cbc:CompanyID, que en la factura "
        "es el NIF-IVA del vendedor (BT-31) y lleva el prefijo. Y con cualquier "
        "impuesto en su cac:TaxScheme, que el esquema exige y ninguna tabla da.",
    ]
    erratas = {e for c in codigos for e in PLANES[c].erratas}
    if erratas:
        partes.append(
            "La tabla del mensaje de anulación escribe dos rutas que no existen "
            "en UBL 2.5, y un mensaje escrito así no pasa el esquema: cuelga la "
            "factura anulada de cac:Response y pone el nombre del vendedor en "
            "cac:PartyTaxScheme/cac:PartyLegalEntity. Se ha leído como el "
            "anexo II: la factura en cac:DocumentResponse/cac:DocumentReference, "
            "y el nombre en cac:PartyLegalEntity o en el cbc:RegistrationName "
            "de cac:PartyTaxScheme, que son los dos arreglos posibles."
        )
    if otras:
        partes.append(
            f"{'La otra respuesta' if otras == 1 else f'Las otras {otras} respuestas'} "
            f"del documento no {'es un mensaje' if otras == 1 else 'son mensajes'} "
            "de la orden, y su contenido no se mira."
        )
    partes.append(
        "Que no salga ninguna queja SPFE- no quiere decir que el mensaje cumpla "
        "la orden."
    )
    return Incidencia(
        "SPFE-MENSAJE-ALCANCE",
        NOTA,
        " ".join(partes),
        campo="Código de respuesta",
        encontrado=", ".join(codigos),
    )
