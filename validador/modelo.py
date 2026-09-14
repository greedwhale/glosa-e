"""Las reglas del modelo que miran un grupo y lo que tiene que llevar dentro.

Casi la mitad de las reglas de EN 16931 dicen lo mismo con distinto nombre:
**si hay un X, tiene que traer un Y**. Si hay representante fiscal, su nombre;
si hay un descuento, su importe y su motivo; si hay un periodo, alguna de sus
dos fechas. El esquematrón oficial las escribe así, con un contexto —el
grupo— y una condición sobre lo de dentro, y eso cambia qué quiere decir que
algo falte: una factura sin representante fiscal no incumple BR-18, porque la
regla no llega a correr. Por eso aquí no hay una lista de campos obligatorios
sino una de grupos, y cada fila dice qué pide el suyo.

De dónde sale cada fila
-----------------------
De la vinculación oficial de cada sintaxis, no de la lectura del texto: las
rutas están en `sintaxis.py` y los casos oficiales se pasan en
`tests/test_norma_oficial.py`. Dos detalles que las filas recogen y que no se
ven leyendo la regla:

- **Que el elemento esté o que diga algo.** Donde las dos vinculaciones, la de
  UBL y la de CII, piden texto —`normalize-space(...) != ''`— aquí se pide
  texto, y un nombre en blanco o con solo un comentario no es un nombre. Donde
  piden que el elemento exista, basta con que exista. Donde no coinciden se
  sigue a la de UBL, que es la de las pruebas oficiales. Son cuatro las que
  piden texto: BR-18, BR-20, BR-50 y BR-52.
- **Tres valores, como en `iva.py`.** Un campo que la sintaxis no tiene dónde
  escribir (`SIN_MAPA`) no está ni falta: no se sabe. Si con lo que se sabe
  basta para dar la regla por cumplida, se da; si no, la regla calla. Acusar
  de no traer lo que el formato no puede traer es lo que este validador no
  hace.

  Hay una excepción, y va marcada con «?» delante del campo: el que solo existe
  en unas sintaxis como **alternativa** a otro. El código de un motivo es la
  otra forma de decir el motivo; Facturae no tiene código, así que ahí no es
  que no se sepa si está: es que no está, y el motivo tiene que ir escrito. Lo
  mismo el código de devengo dentro del periodo, que solo UBL guarda ahí.

Las repetidas
-------------
BR-CO-21 a 24 piden exactamente lo mismo que BR-33, 38, 42 y 44: que un
descuento o un cargo diga por qué. La norma las escribió dos veces y el
esquematrón oficial las evalúa por separado, así que cualquier validador
oficial dará las dos. Aquí también salen las dos, y la explicación de cada una
lo dice: un informe que dijera una sola discreparía del oficial justo en lo
que es igual.

Un defecto repetido es una incidencia
-------------------------------------
Tres descuentos sin motivo son un problema, no tres: sale una incidencia por
regla, y el campo nombra dónde —«descuento 1, descuento 3», «líneas 2, 5»—, que
es lo que hace falta para arreglarlo. Es el mismo criterio que las reglas de
línea de `en16931.py`.
"""
from __future__ import annotations

import re

from validador.incidencias import AVISO, ERROR, Incidencia
from validador.sintaxis import SIN_MAPA, Sintaxis, a_decimal, texto

__all__ = ["PREFIJOS_IVA", "grupos", "reglas"]

# Los prefijos que BR-CO-09 admite en un identificador de IVA: los códigos
# ISO 3166-1 alfa-2, más EL para Grecia y 1A para Kosovo. Copiados de la
# vinculación oficial de UBL, que es de donde salen las pruebas; la de CII trae
# AN —las Antillas Neerlandesas, que dejaron de existir en 2010— y le falta SS,
# Sudán del Sur. `test_norma_oficial` compara esta lista con la oficial, así
# que no puede quedarse vieja sin que se note.
PREFIJOS_IVA = frozenset(
    "1A AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI "
    "BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO "
    "CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH EL ER ES ET FI FJ FK FM "
    "FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR "
    "HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW "
    "KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO "
    "MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA "
    "PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG "
    "SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN "
    "TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS XI YE YT ZA "
    "ZM ZW".split()
)

# Los grupos, y cómo se llama cada uno en el informe.
_NOMBRE_DEL_GRUPO = {
    "vendedor": "Vendedor",
    "beneficiario": "Beneficiario del pago",
    "representante": "Representante fiscal",
    "direccion_representante": "Dirección del representante fiscal",
    "direccion_entrega": "Dirección de entrega",
    "direccion_electronica_vendedor": "Dirección electrónica del vendedor",
    "direccion_electronica_comprador": "Dirección electrónica del comprador",
    "descuentos_documento": "Descuentos de documento",
    "cargos_documento": "Cargos de documento",
    "descuentos_linea": "Descuentos de línea",
    "cargos_linea": "Cargos de línea",
    "pagos": "Instrucciones de pago",
    "cuentas_de_transferencia": "Cuenta de la transferencia",
    "adjuntos": "Documentos adjuntos",
    "facturas_previas": "Facturas a las que se refiere",
    "periodo": "Periodo de facturación",
    "periodos_de_linea": "Periodo de la línea",
    "lineas": "Líneas",
    "atributos": "Atributos del artículo",
    "identificadores_estandar": "Identificador normalizado del artículo",
    "clasificaciones": "Clasificación del artículo",
}

# (código, grupo, qué pide, «alguno» o «todos», si pide texto, qué falta,
#  explicación)
#
# «Qué pide» son campos de `Sintaxis`, relativos al grupo; los que llevan «@»
# delante se leen desde el documento, porque el mapa ya los tenía así para
# otras reglas y un campo con dos rutas es un campo que un día dice dos cosas.
# Los que llevan «?» son alternativas que no todas las sintaxis tienen: donde
# no la tienen, no está (ver el docstring).
_GRUPOS: tuple[tuple[str, str, tuple[str, ...], str, bool, str, str], ...] = (
    (
        "BR-17", "beneficiario", ("beneficiario_nombre",), "alguno", False,
        "el nombre del beneficiario (BT-59)",
        "La factura declara un beneficiario del pago distinto del vendedor y "
        "no dice cómo se llama.",
    ),
    (
        "BR-18", "representante", ("representante_nombre",), "alguno", True,
        "el nombre del representante fiscal (BT-62)",
        "La factura declara un representante fiscal del vendedor y no dice "
        "cómo se llama.",
    ),
    (
        "BR-19", "representante", ("representante_direccion",), "alguno", False,
        "la dirección postal del representante fiscal (BG-12)",
        "La factura declara un representante fiscal del vendedor y no da su "
        "dirección postal.",
    ),
    (
        "BR-20", "direccion_representante", ("representante_pais",), "alguno", True,
        "el código de país del representante fiscal (BT-69)",
        "La dirección del representante fiscal no dice de qué país es.",
    ),
    (
        "BR-56", "representante", ("@representante_nif",), "alguno", False,
        "el identificador de IVA del representante fiscal (BT-63)",
        "La factura declara un representante fiscal del vendedor y no da su "
        "identificador de IVA, que es lo que lo hace representante a efectos "
        "del impuesto.",
    ),
    (
        "BR-CO-26", "vendedor", ("@vendedor_id", "@vendedor_registro", "@vendedor_nif"),
        "alguno", False,
        "un identificador del vendedor (BT-29), su registro legal (BT-30) o su "
        "identificador de IVA (BT-31)",
        "La factura no identifica al vendedor de ninguna de las tres formas "
        "que admite la norma, y sin ninguna el comprador no puede saber de "
        "forma automática quién le factura.",
    ),
    (
        "BR-57", "direccion_entrega", ("@pais_entrega",), "alguno", False,
        "el código de país de la dirección de entrega (BT-80)",
        "La dirección de entrega no dice de qué país es.",
    ),
    (
        "BR-62", "direccion_electronica_vendedor", ("direccion_electronica_esquema",),
        "alguno", False,
        "el esquema de la dirección electrónica del vendedor",
        "La dirección electrónica del vendedor no dice de qué esquema es. Un "
        "número suelto no se puede usar para enviar nada: hace falta saber si "
        "es un NIF, un GLN, un correo…",
    ),
    (
        "BR-63", "direccion_electronica_comprador", ("direccion_electronica_esquema",),
        "alguno", False,
        "el esquema de la dirección electrónica del comprador",
        "La dirección electrónica del comprador no dice de qué esquema es.",
    ),
    (
        "BR-31", "descuentos_documento", ("cargo_importe",), "alguno", False,
        "el importe del descuento (BT-92)",
        "Hay descuentos de documento sin importe.",
    ),
    (
        "BR-32", "descuentos_documento", ("cargo_categoria",), "alguno", False,
        "la categoría de IVA del descuento (BT-95)",
        "Hay descuentos de documento sin categoría de IVA, así que no se sabe "
        "de qué base restan.",
    ),
    (
        "BR-33", "descuentos_documento", ("cargo_motivo", "?cargo_motivo_codigo"),
        "alguno", False,
        "el motivo del descuento (BT-97) o su código (BT-98)",
        "Hay descuentos de documento que no dicen por qué se hacen.",
    ),
    (
        "BR-CO-21", "descuentos_documento", ("cargo_motivo", "?cargo_motivo_codigo"),
        "alguno", False,
        "el motivo del descuento (BT-97) o su código (BT-98)",
        "Hay descuentos de documento sin motivo ni código de motivo. Es lo "
        "mismo que pide BR-33, escrito dos veces en la norma.",
    ),
    (
        "BR-36", "cargos_documento", ("cargo_importe",), "alguno", False,
        "el importe del cargo (BT-99)",
        "Hay cargos de documento sin importe.",
    ),
    (
        "BR-37", "cargos_documento", ("cargo_categoria",), "alguno", False,
        "la categoría de IVA del cargo (BT-102)",
        "Hay cargos de documento sin categoría de IVA, así que no se sabe a "
        "qué base suman.",
    ),
    (
        "BR-38", "cargos_documento", ("cargo_motivo", "?cargo_motivo_codigo"),
        "alguno", False,
        "el motivo del cargo (BT-104) o su código (BT-105)",
        "Hay cargos de documento que no dicen por qué se cobran.",
    ),
    (
        "BR-CO-22", "cargos_documento", ("cargo_motivo", "?cargo_motivo_codigo"),
        "alguno", False,
        "el motivo del cargo (BT-104) o su código (BT-105)",
        "Hay cargos de documento sin motivo ni código de motivo. Es lo mismo "
        "que pide BR-38, escrito dos veces en la norma.",
    ),
    (
        "BR-41", "descuentos_linea", ("cargo_importe",), "alguno", False,
        "el importe del descuento de línea (BT-136)",
        "Hay descuentos de línea sin importe.",
    ),
    (
        "BR-42", "descuentos_linea", ("cargo_motivo", "?cargo_motivo_codigo"),
        "alguno", False,
        "el motivo del descuento de línea (BT-139) o su código (BT-140)",
        "Hay descuentos de línea que no dicen por qué se hacen.",
    ),
    (
        "BR-CO-23", "descuentos_linea", ("cargo_motivo", "?cargo_motivo_codigo"),
        "alguno", False,
        "el motivo del descuento de línea (BT-139) o su código (BT-140)",
        "Hay descuentos de línea sin motivo ni código de motivo. Es lo mismo "
        "que pide BR-42, escrito dos veces en la norma.",
    ),
    (
        "BR-43", "cargos_linea", ("cargo_importe",), "alguno", False,
        "el importe del cargo de línea (BT-141)",
        "Hay cargos de línea sin importe.",
    ),
    (
        "BR-44", "cargos_linea", ("cargo_motivo", "?cargo_motivo_codigo"),
        "alguno", False,
        "el motivo del cargo de línea (BT-144) o su código (BT-145)",
        "Hay cargos de línea que no dicen por qué se cobran.",
    ),
    (
        "BR-CO-24", "cargos_linea", ("cargo_motivo", "?cargo_motivo_codigo"),
        "alguno", False,
        "el motivo del cargo de línea (BT-144) o su código (BT-145)",
        "Hay cargos de línea sin motivo ni código de motivo. Es lo mismo que "
        "pide BR-44, escrito dos veces en la norma.",
    ),
    (
        "BR-49", "pagos", ("pago_medio",), "alguno", False,
        "el código del medio de pago (BT-81)",
        "Hay instrucciones de pago que no dicen cómo se paga.",
    ),
    (
        "BR-50", "cuentas_de_transferencia", ("cuenta_id",), "alguno", True,
        "el identificador de la cuenta (BT-84)",
        "El pago es por transferencia y la cuenta de abono no dice cuál es.",
    ),
    (
        "BR-52", "adjuntos", ("adjunto_id",), "alguno", True,
        "la referencia del documento (BT-122)",
        "Hay documentos adjuntos o referenciados sin referencia que los "
        "identifique.",
    ),
    (
        "BR-55", "facturas_previas", ("previa_id",), "alguno", False,
        "el número de la factura a la que se refiere (BT-25)",
        "La factura se refiere a una anterior y no dice a cuál.",
    ),
    (
        "BR-CO-19", "periodo", ("periodo_inicio", "periodo_fin", "?periodo_codigo"),
        "alguno", False,
        "la fecha de inicio (BT-73) o la de fin (BT-74)",
        "La factura declara un periodo de facturación y no le pone ninguna "
        "de sus dos fechas.",
    ),
    (
        "BR-CO-20", "periodos_de_linea", ("periodo_inicio", "periodo_fin"), "alguno", False,
        "la fecha de inicio (BT-134) o la de fin (BT-135)",
        "Hay líneas que declaran un periodo y no le ponen ninguna de sus dos "
        "fechas.",
    ),
    (
        "BR-CO-04", "lineas", ("linea_categoria",), "alguno", False,
        "la categoría de IVA de la línea (BT-151)",
        "Hay líneas sin categoría de IVA. Sin ella no se sabe en qué entrada "
        "del desglose entran, ni qué reglas del impuesto se les aplican.",
    ),
    (
        "BR-54", "atributos", ("atributo_nombre", "atributo_valor"), "todos", False,
        "el nombre (BT-160) y el valor (BT-161) del atributo",
        "Hay atributos de artículo a los que les falta el nombre o el valor: "
        "«color» sin decir cuál, o «negro» sin decir de qué.",
    ),
    (
        "BR-64", "identificadores_estandar", ("linea_id_estandar_esquema",), "alguno", False,
        "el esquema del identificador (GTIN, por ejemplo)",
        "Hay artículos con un identificador normalizado que no dice de qué "
        "esquema es. Un número sin su esquema no identifica nada.",
    ),
    (
        "BR-65", "clasificaciones", ("linea_clasificacion_esquema",), "alguno", False,
        "la lista de la clasificación (CPV, por ejemplo)",
        "Hay artículos clasificados con un código que no dice de qué lista es.",
    ),
)


def _escrito(nodo) -> str:
    """Lo que dice un nodo, sin comentarios: `string()` de XPath, como el oficial."""
    return (nodo if isinstance(nodo, str) else nodo.xpath("string()")).strip()


def _esta(nodo, ruta: str, sintaxis: Sintaxis, con_texto: bool) -> bool | None:
    """Si el campo está —o dice algo—, si no, o None si la sintaxis no lo tiene."""
    if ruta == SIN_MAPA:
        return None
    encontrados = nodo.xpath(ruta, namespaces=sintaxis.espacios)
    if isinstance(encontrados, str):
        encontrados = [encontrados] if encontrados.strip() else []
    if not con_texto:
        return bool(encontrados)
    return any(_escrito(n) for n in encontrados)


def _nodos(nodo, ruta: str, sintaxis: Sintaxis) -> list:
    if ruta == SIN_MAPA:
        return []
    return list(nodo.xpath(ruta, namespaces=sintaxis.espacios))


def _lineas(raiz, sintaxis: Sintaxis) -> list[tuple[str, object]]:
    """Cada línea con su nombre: su identificador, o su posición si no lo tiene."""
    return [
        (texto(linea, sintaxis.linea_id, sintaxis) or str(indice), linea)
        for indice, linea in enumerate(_nodos(raiz, sintaxis.lineas, sintaxis), start=1)
    ]


def _es_cargo(nodo, sintaxis: Sintaxis) -> bool:
    marca = (texto(nodo, sintaxis.cargo_es_cargo, sintaxis) or "").lower()
    return marca in sintaxis.marcas_de_cargo


def _ajustes(nodos: list, sintaxis: Sintaxis, cargos: bool, sufijo: str) -> list[tuple[str, object]]:
    """Los descuentos o los cargos, numerados como en `iva.py`: por su puesto
    entre todos los ajustes, para que «cargo 3» sea el mismo en los dos informes.

    Los de línea llevan la línea detrás —«cargo 2 de la línea 1»— y no delante
    con una coma: el informe los junta con comas, y «línea 1, cargo 2, línea 1,
    cargo 3» no deja ver dónde acaba cada uno.
    """
    return [
        (f"{'cargo' if cargos else 'descuento'} {indice}{sufijo}", nodo)
        for indice, nodo in enumerate(nodos, start=1)
        if _es_cargo(nodo, sintaxis) == cargos
    ]


def grupos(raiz, sintaxis: Sintaxis, cual: str) -> list[tuple[str, object]]:
    """Las apariciones de un grupo, cada una con cómo nombrarla.

    Pública porque la usan también las reglas de decimales, que miran los
    mismos descuentos, cargos y líneas: numerados igual en los dos sitios.
    """
    def sueltos(ruta: str, nombre: str) -> list[tuple[str, object]]:
        nodos = _nodos(raiz, ruta, sintaxis)
        if len(nodos) == 1:
            return [("", nodos[0])]
        return [(f"{nombre} {n}", nodo) for n, nodo in enumerate(nodos, start=1)]

    def de_cada_linea(ruta: str) -> list[tuple[str, object]]:
        return [
            (f"línea {nombre}", dentro)
            for nombre, linea in _lineas(raiz, sintaxis)
            for dentro in _nodos(linea, ruta, sintaxis)
        ]

    if cual == "documento":
        return [("", raiz)]
    if cual == "lineas":
        return [(f"línea {nombre}", linea) for nombre, linea in _lineas(raiz, sintaxis)]
    if cual == "desglose":
        return sueltos(sintaxis.desglose, "entrada")
    if cual in ("descuentos_documento", "cargos_documento"):
        return _ajustes(_nodos(raiz, sintaxis.cargos, sintaxis), sintaxis,
                        cual == "cargos_documento", "")
    if cual in ("descuentos_linea", "cargos_linea"):
        return [
            encontrado
            for nombre, linea in _lineas(raiz, sintaxis)
            for encontrado in _ajustes(_nodos(linea, sintaxis.linea_cargos, sintaxis),
                                       sintaxis, cual == "cargos_linea", f" de la línea {nombre}")
        ]
    if cual == "direccion_representante":
        return [
            ("", direccion)
            for representante in _nodos(raiz, sintaxis.representante, sintaxis)
            for direccion in _nodos(representante, sintaxis.representante_direccion, sintaxis)[:1]
        ]
    if cual == "cuentas_de_transferencia":
        return [
            (nombre, cuenta)
            for nombre, pago in sueltos(sintaxis.pagos, "instrucción")
            if texto(pago, sintaxis.pago_medio, sintaxis) in sintaxis.medios_de_transferencia
            for cuenta in _nodos(pago, sintaxis.pago_cuenta, sintaxis)
        ]
    if cual == "periodos_de_linea":
        return de_cada_linea(sintaxis.linea_periodo)
    if cual == "atributos":
        return de_cada_linea(sintaxis.linea_atributos)
    if cual == "identificadores_estandar":
        return de_cada_linea(sintaxis.linea_id_estandar)
    if cual == "clasificaciones":
        return de_cada_linea(sintaxis.linea_clasificacion)
    rutas = {
        "vendedor": (sintaxis.vendedor, "vendedor"),
        "beneficiario": (sintaxis.beneficiario, "beneficiario"),
        "representante": (sintaxis.representante, "representante"),
        "direccion_entrega": (sintaxis.direccion_entrega, "dirección"),
        "direccion_electronica_vendedor": (sintaxis.vendedor_direccion_electronica, "dirección"),
        "direccion_electronica_comprador": (sintaxis.comprador_direccion_electronica, "dirección"),
        "pagos": (sintaxis.pagos, "instrucción"),
        "adjuntos": (sintaxis.adjuntos, "documento"),
        "facturas_previas": (sintaxis.facturas_previas, "referencia"),
        "periodo": (sintaxis.periodo_grupo, "periodo"),
    }
    ruta, nombre = rutas[cual]
    if cual == "direccion_entrega" and ruta != SIN_MAPA:
        # La dirección de EDIFACT son varias posiciones del mismo NAD, y cada
        # una sale como un nodo: es una dirección, no cinco.
        nodos = _nodos(raiz, ruta, sintaxis)
        return [("", nodos[0])] if nodos else []
    return sueltos(ruta, nombre)


def _reglas_de_grupo(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    incidencias: list[Incidencia] = []
    for codigo, grupo, pide, modo, con_texto, que_falta, explicacion in _GRUPOS:
        donde = []
        for nombre, nodo in grupos(raiz, sintaxis, grupo):
            valores = []
            for campo in pide:
                ruta = getattr(sintaxis, campo.lstrip("@?"))
                if campo.startswith("?") and ruta == SIN_MAPA:
                    valores.append(False)
                    continue
                valores.append(_esta(raiz if campo.startswith("@") else nodo,
                                     ruta, sintaxis, con_texto))
            if modo == "alguno":
                falta = not any(valores) and None not in valores
            else:
                falta = False in valores
            if falta:
                donde.append(nombre)
        if not donde:
            continue
        lugares = ", ".join(n for n in donde if n)
        incidencias.append(
            Incidencia(
                codigo,
                ERROR,
                explicacion,
                campo=_NOMBRE_DEL_GRUPO[grupo] + (f" · {lugares}" if lugares else ""),
                esperado=que_falta,
                encontrado="(falta)",
            )
        )
    return incidencias


# --- Lo que no es «si está, que traiga» ---------------------------------------


def _regla_beneficiario_que_es_el_vendedor(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-17, la otra mitad: el beneficiario se declara cuando es otro.

    La regla dice «si el beneficiario es distinto del vendedor», y las dos
    vinculaciones lo leen igual: un beneficiario que se llama como el vendedor
    o lleva su mismo identificador es el vendedor, y no tenía que estar. No
    comparan con el mismo nombre —la de UBL con el comercial, la de CII con el
    legal—, así que aquí se compara con los dos.
    """
    def valores(nodo, *rutas: str) -> set[str]:
        return {_escrito(n) for ruta in rutas for n in _nodos(nodo, ruta, sintaxis)} - {""}

    del_vendedor = {
        "nombre": valores(raiz, sintaxis.vendedor_nombre, sintaxis.vendedor_nombre_comercial),
        "id": valores(raiz, sintaxis.vendedor_id),
        "registro": valores(raiz, sintaxis.vendedor_registro),
    }
    for beneficiario in _nodos(raiz, sintaxis.beneficiario, sintaxis):
        suyos = {
            "nombre": valores(beneficiario, sintaxis.beneficiario_nombre),
            "id": valores(beneficiario, sintaxis.beneficiario_id),
            "registro": valores(beneficiario, sintaxis.beneficiario_registro),
        }
        if not suyos["nombre"]:
            continue  # de que falte el nombre ya se queja la tabla
        coinciden = [que for que in suyos if suyos[que] & del_vendedor[que]]
        if coinciden:
            return [
                Incidencia(
                    "BR-17",
                    ERROR,
                    "El beneficiario del pago es el propio vendedor: tiene su "
                    f"mismo {' y su mismo '.join(coinciden)}. El beneficiario "
                    "solo se declara cuando cobra otro; si cobra el vendedor, "
                    "sobra.",
                    campo="Beneficiario del pago",
                    esperado="otro que el vendedor, o ninguno",
                    encontrado=", ".join(sorted(suyos["nombre"])),
                )
            ]
    return []


def _regla_precios(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-27 y BR-28: un precio no es negativo; lo que resta es un descuento."""
    incidencias = []
    for codigo, ruta, cual in (
        ("BR-27", "linea_precio", "neto (BT-146)"),
        ("BR-28", "linea_precio_bruto", "bruto (BT-148)"),
    ):
        negativos = []
        for nombre, linea in _lineas(raiz, sintaxis):
            precio = a_decimal(texto(linea, getattr(sintaxis, ruta), sintaxis))
            if precio is not None and precio < 0:
                negativos.append(f"{nombre} ({precio})")
        if negativos:
            incidencias.append(
                Incidencia(
                    codigo,
                    ERROR,
                    f"Hay líneas con el precio {cual} en negativo. Un precio "
                    "no puede serlo: lo que resta se escribe como descuento, y "
                    "lo que se devuelve, con la cantidad en negativo.",
                    campo="Líneas " + ", ".join(negativos),
                    esperado="cero o más",
                    encontrado="un precio negativo",
                )
            )
    return incidencias


# Una fecha, escrita como en UBL y Facturae (2026-06-01) o como en CII y
# EDIFACT con el formato 102 (20260601). Lo que no tenga esa forma no se
# compara: de que una fecha esté mal escrita se ocupa la forma, no esta regla.
_FECHA = re.compile(r"^(\d{4})-?(\d{2})-?(\d{2})")


def _dia(valor: str | None) -> str | None:
    m = _FECHA.match(valor or "")
    return "".join(m.groups()) if m else None


def _regla_periodos(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-29 y BR-30: un periodo no acaba antes de empezar."""
    incidencias = []
    for codigo, grupo, que in (
        ("BR-29", "periodo", "El periodo de facturación"),
        ("BR-30", "periodos_de_linea", "El periodo de la línea"),
    ):
        al_reves = []
        for nombre, periodo in grupos(raiz, sintaxis, grupo):
            inicio = _dia(texto(periodo, sintaxis.periodo_inicio, sintaxis))
            fin = _dia(texto(periodo, sintaxis.periodo_fin, sintaxis))
            if inicio and fin and fin < inicio:
                al_reves.append((nombre, inicio, fin))
        if al_reves:
            nombre, inicio, fin = al_reves[0]
            lugares = ", ".join(n for n, _, _ in al_reves if n)
            incidencias.append(
                Incidencia(
                    codigo,
                    ERROR,
                    f"{que} acaba antes de empezar.",
                    campo=_NOMBRE_DEL_GRUPO[grupo] + (f" · {lugares}" if lugares else ""),
                    esperado="la fecha de fin igual o posterior a la de inicio",
                    encontrado=f"del {inicio} al {fin}",
                )
            )
    return incidencias


def _regla_tarjeta(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-51: de una tarjeta, como mucho las seis primeras cifras y las cuatro últimas.

    Es `warning` en la norma y sale como aviso. Y el informe no repite el
    número: sería copiar otra vez, en otro sitio, justo lo que la regla pide
    que no se escriba.
    """
    largos = [
        len(re.sub(r"\s+", "", _escrito(n)))
        for n in _nodos(raiz, sintaxis.tarjeta_numero, sintaxis)
    ]
    largos = [n for n in largos if n > 10]
    if not largos:
        return []
    return [
        Incidencia(
            "BR-51",
            AVISO,
            "La factura trae el número de una tarjeta de pago entero, o casi. "
            "Las normas de seguridad de las tarjetas permiten enseñar como "
            "mucho las seis primeras cifras y las cuatro últimas; el resto no "
            "debería viajar en una factura.",
            campo="Número de la tarjeta (BT-87)",
            esperado="10 caracteres como mucho",
            encontrado=f"{max(largos)} caracteres",
        )
    ]


def _regla_moneda_de_contabilidad(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-53: con moneda de contabilidad del IVA, el total del IVA en esa moneda.

    Si la moneda de contabilidad es la misma que la de la factura, el total de
    siempre ya está en ella y no hace falta otro. Así lo lee la vinculación de
    UBL; la de CII exige además que las dos monedas sean distintas, que es
    decir que declarar la misma es un error, y eso la regla no lo dice.
    """
    if sintaxis.impuestos == SIN_MAPA:
        return []
    moneda = texto(raiz, sintaxis.moneda_impuestos, sintaxis) if (
        sintaxis.moneda_impuestos != SIN_MAPA) else None
    if not moneda:
        return []
    totales = _nodos(raiz, sintaxis.impuestos, sintaxis)
    if any(not isinstance(n, str) and n.get("currencyID") == moneda for n in totales):
        return []
    return [
        Incidencia(
            "BR-53",
            ERROR,
            f"La factura dice que el IVA se contabiliza en {moneda} y no da el "
            f"total del IVA en {moneda}.",
            campo="Total del IVA en la moneda de contabilidad (BT-111)",
            esperado=f"un total de impuestos en {moneda}",
            encontrado="(falta)",
        )
    ]


def _regla_transferencia_sin_cuenta(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-61: un pago por transferencia dice a qué cuenta."""
    if SIN_MAPA in (sintaxis.pagos, sintaxis.pago_medio, sintaxis.pago_cuenta, sintaxis.cuenta_id):
        return []
    pagos = grupos(raiz, sintaxis, "pagos")
    sin_cuenta = [
        (nombre, medio)
        for nombre, pago in pagos
        if (medio := texto(pago, sintaxis.pago_medio, sintaxis)) in sintaxis.medios_de_transferencia
        and not any(_nodos(cuenta, sintaxis.cuenta_id, sintaxis)
                    for cuenta in _nodos(pago, sintaxis.pago_cuenta, sintaxis))
    ]
    if not sin_cuenta:
        return []
    lugares = ", ".join(n for n, _ in sin_cuenta if n)
    return [
        Incidencia(
            "BR-61",
            ERROR,
            "El pago es por transferencia y la factura no dice a qué cuenta "
            "hay que hacerla.",
            campo="Instrucciones de pago" + (f" · {lugares}" if lugares else ""),
            esperado="el identificador de la cuenta de abono (BT-84)",
            encontrado=f"medio de pago {sin_cuenta[0][1]}, sin cuenta",
        )
    ]


def _regla_devengo(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-CO-03: la fecha de devengo o su código, pero no los dos."""
    fecha = _esta(raiz, sintaxis.fecha_devengo, sintaxis, False)
    codigo = _esta(raiz, sintaxis.fecha_devengo_codigo, sintaxis, False)
    if not (fecha and codigo):
        return []
    return [
        Incidencia(
            "BR-CO-03",
            ERROR,
            "La factura da a la vez la fecha de devengo del IVA y el código "
            "que dice cuándo se devenga. Son dos formas de decir lo mismo, y "
            "la norma pide una: si las dos dijeran cosas distintas, no se "
            "sabría cuál vale.",
            campo="Fecha de devengo (BT-7) y su código (BT-8)",
            esperado="una de las dos",
            encontrado="las dos",
        )
    ]


def _regla_prefijo_del_nif(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-CO-09: un identificador de IVA empieza por el código de su país.

    Es lo que lo hace legible desde otro país: `B12345678` es un NIF español
    para quien ya sabe que es español, y `ESB12345678` lo es para cualquiera.
    Grecia usa EL, no GR.
    """
    sin_prefijo = []
    for quien, ruta in (
        ("vendedor", sintaxis.vendedor_nif),
        ("representante fiscal", sintaxis.representante_nif),
        ("comprador", sintaxis.comprador_nif),
    ):
        for nodo in _nodos(raiz, ruta, sintaxis):
            valor = _escrito(nodo)
            if valor and valor[:2] not in PREFIJOS_IVA:
                sin_prefijo.append(f"{quien}: {valor}")
    if not sin_prefijo:
        return []
    return [
        Incidencia(
            "BR-CO-09",
            ERROR,
            "Hay identificadores de IVA que no empiezan por el código de su "
            "país. La norma lo exige para que se sepan de qué país son sin "
            "tener que adivinarlo: ESB12345678 y no B12345678.",
            campo="Identificador de IVA",
            esperado="el código ISO del país delante (EL para Grecia)",
            encontrado="; ".join(sin_prefijo),
        )
    ]


# --- Entrada pública -----------------------------------------------------------


def reglas(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """Las reglas de grupo sobre un documento ya parseado —o una factura de un lote."""
    incidencias = _reglas_de_grupo(raiz, sintaxis)
    incidencias.extend(_regla_beneficiario_que_es_el_vendedor(raiz, sintaxis))
    incidencias.extend(_regla_precios(raiz, sintaxis))
    incidencias.extend(_regla_periodos(raiz, sintaxis))
    incidencias.extend(_regla_tarjeta(raiz, sintaxis))
    incidencias.extend(_regla_moneda_de_contabilidad(raiz, sintaxis))
    incidencias.extend(_regla_transferencia_sin_cuenta(raiz, sintaxis))
    incidencias.extend(_regla_devengo(raiz, sintaxis))
    incidencias.extend(_regla_prefijo_del_nif(raiz, sintaxis))
    return incidencias
