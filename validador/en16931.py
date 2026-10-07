"""Reglas de negocio de la norma EN 16931, sobre UBL y sobre CII.

La norma son 955 reglas y ahí es donde se produce la mayoría de los rechazos:
un documento puede pasar la validación de forma (XSD) y fallar la de contenido.

Este módulo implementa las reglas de mayor valor —campos obligatorios y las de
cuadre aritmético— con el mensaje escrito en castellano llano. La traducción es
el producto: las reglas son públicas y de todos, pero un error como «BR-CO-13»
no le dice nada a quien tiene que arreglar la factura.

Las reglas de IVA, que son una familia entera y siguen su propio patrón, viven
en `iva.py` y se llaman desde aquí: para quien usa el validador son las mismas
reglas de la misma norma. Lo mismo las que miran un grupo y lo que tiene que
llevar dentro —el representante fiscal, los descuentos, los pagos—, que viven
en `modelo.py`; las de cuántos decimales lleva cada importe, en
`decimales.py`, y las de los códigos que tienen que salir de una lista, en
`listas_de_codigos.py`.

**Nada de esto depende de la sintaxis.** EN 16931 define un modelo semántico
—BT-1, BT-109, BT-112…— y luego UBL y CII lo escriben de dos maneras. Que la
base imponible más los impuestos den el total es verdad en las dos; lo único
que cambia es dónde está escrito cada número. El mapa está en `sintaxis.py`.

El importe se maneja siempre con Decimal. Con float, 0.1 + 0.2 no da 0.3 y una
factura correcta se rechazaría por un céntimo fantasma.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from lxml import etree

from validador import cifras, decimales, edifact, iva, listas_de_codigos, modelo
from validador.formato import FACTURAE, RESPUESTA, detectar, parser
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia, Informe
from validador.sintaxis import (
    NS_CII,
    NS_UBL,
    SIN_MAPA,
    SINTAXIS,
    SINTAXIS_CII,
    SINTAXIS_FACTURAE,
    SINTAXIS_UBL,
    TOLERANCIA,
    Sintaxis,
    a_decimal,
    cuadra,
    cuadra_exacto,
    importe,
    importe_en_moneda,
    redondear,
    texto,
)

__all__ = [
    "AVISO",
    "ERROR",
    "Incidencia",
    "Informe",
    "NOTA",
    "NS",
    "NS_CII",
    "NS_UBL",
    "SIN_MAPA",
    "SINTAXIS",
    "SINTAXIS_CII",
    "SINTAXIS_FACTURAE",
    "SINTAXIS_UBL",
    "Sintaxis",
    "TOLERANCIA",
    "reglas",
    "validar",
]

# Nombre de antes, cuando este módulo llevaba dentro el mapa y solo sabía de UBL.
NS = NS_UBL


# --- Reglas de campos obligatorios -----------------------------------------

# (código, campo de `Sintaxis`, nombre en castellano, explicación, contenedor,
#  de qué cuelga)
#
# «contenedor» marca los elementos que agrupan a otros y por tanto no tienen
# texto propio: una dirección postal no está vacía por no llevar texto suelto.
# Antes esto se deducía mirando si la ruta acababa en «PostalAddress», que en
# UBL colaba y en CII —donde se llama «PostalTradeAddress»— habría dado un
# error falso en todas las facturas.
#
# «de qué cuelga» es el contexto de la regla en el esquematrón normativo. BR-09
# no se evalúa sobre la factura: se evalúa **sobre la dirección del vendedor**,
# y si no hay dirección la norma dispara BR-08 y calla. Aquí salían las dos, y
# quien recibía el informe leía dos defectos donde solo había uno —encima con
# el segundo mal descrito, porque no es que a la dirección le falte el país,
# es que no hay dirección—. Es la misma familia de error que el BR-{X}-05 que
# se comprobaba sobre el desglose en vez de sobre la línea.
_OBLIGATORIOS: tuple[tuple[str, str, str, str, bool, str | None], ...] = (
    (
        "BR-01",
        "perfil",
        "Identificador de especificación",
        "La factura debe declarar a qué especificación se ajusta.",
        False,
        None,
    ),
    (
        "BR-02",
        "numero",
        "Número de factura",
        "La factura debe llevar número.",
        False,
        None,
    ),
    (
        "BR-03",
        "fecha",
        "Fecha de expedición",
        "La factura debe llevar fecha de expedición.",
        False,
        None,
    ),
    (
        "BR-04",
        "tipo",
        "Código de tipo de documento",
        "El documento debe indicar de qué tipo es: 380 para una factura "
        "ordinaria, 381 para un abono.",
        False,
        None,
    ),
    (
        "BR-05",
        "moneda",
        "Moneda",
        "La factura debe indicar en qué moneda está.",
        False,
        None,
    ),
    (
        "BR-06",
        "vendedor_nombre",
        "Nombre del vendedor",
        "Falta el nombre o razón social de quien emite la factura.",
        False,
        None,
    ),
    (
        "BR-07",
        "comprador_nombre",
        "Nombre del comprador",
        "Falta el nombre o razón social de quien recibe la factura.",
        False,
        None,
    ),
    (
        "BR-08",
        "vendedor_direccion",
        "Dirección del vendedor",
        "Falta la dirección postal del vendedor.",
        True,
        None,
    ),
    (
        "BR-09",
        "vendedor_pais",
        "País del vendedor",
        "La dirección del vendedor debe incluir el código de país (ES, FR...).",
        False,
        "vendedor_direccion",
    ),
    (
        "BR-10",
        "comprador_direccion",
        "Dirección del comprador",
        "Falta la dirección postal del comprador.",
        True,
        None,
    ),
    (
        "BR-11",
        "comprador_pais",
        "País del comprador",
        "La dirección del comprador debe incluir el código de país.",
        False,
        "comprador_direccion",
    ),
    (
        "BR-12",
        "suma_lineas",
        "Suma de importes de línea",
        "Falta la suma de los importes netos de las líneas.",
        False,
        None,
    ),
    (
        "BR-13",
        "base",
        "Base imponible total",
        "Falta el importe total sin impuestos.",
        False,
        None,
    ),
    (
        "BR-14",
        "con_impuestos",
        "Total con impuestos",
        "Falta el importe total con impuestos incluidos.",
        False,
        None,
    ),
    (
        "BR-15",
        "a_pagar",
        "Total a pagar",
        "Falta el importe que hay que pagar.",
        False,
        None,
    ),
)


def _reglas_obligatorios(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    incidencias = []
    for codigo, atributo, campo, explicacion, contenedor, cuelga_de in _OBLIGATORIOS:
        ruta = getattr(sintaxis, atributo)
        if ruta == SIN_MAPA:
            # Un término sin correspondencia en la sintaxis **no es un campo
            # que falte en la factura**: es un campo que el formato no tiene
            # dónde escribir. La diferencia importa, porque un ERROR aquí
            # acusa a quien emitió el documento de algo que no podía hacer.
            #
            # Lo destapó Facturae, que no tiene equivalente de BT-24: con esta
            # rama sin escribir, BR-01 salía como «(falta)» en todas las
            # facturas de España, siempre, hicieran lo que hicieran. EDIFACT ya
            # traía dos huecos —BT-114 y BT-121— pero ninguno cae en esta
            # tabla, así que nunca llegó a verse.
            #
            # Sale NOTA y no AVISO a propósito: NOTA es la gravedad que existe
            # para decir qué se aceptó y con qué base, y esto es exactamente
            # eso. No hay nada que arreglar en el documento.
            incidencias.append(
                Incidencia(
                    codigo,
                    NOTA,
                    f"{explicacion} La sintaxis {sintaxis.nombre} no tiene "
                    "ningún elemento con ese significado, así que no se ha "
                    "podido comprobar. No es un defecto del documento.",
                    campo=campo,
                    encontrado="(sin correspondencia en esta sintaxis)",
                )
            )
            continue
        if cuelga_de is not None and not raiz.xpath(
            getattr(sintaxis, cuelga_de), namespaces=sintaxis.espacios
        ):
            # Sin el bloque del que cuelga, esta regla no se evalúa: es lo que
            # dice su contexto en el esquematrón, y de que falte el bloque ya
            # se queja la regla de al lado.
            continue
        if not raiz.xpath(ruta, namespaces=sintaxis.espacios):
            incidencias.append(
                Incidencia(
                    codigo, ERROR, explicacion, campo=campo, encontrado="(falta)"
                )
            )
        elif not contenedor and texto(raiz, ruta, sintaxis) is None:
            incidencias.append(
                Incidencia(
                    codigo,
                    ERROR,
                    f"{explicacion} El elemento existe pero está vacío.",
                    campo=campo,
                    encontrado="(vacío)",
                )
            )
    return incidencias


# (código, campo de `Sintaxis`, qué es, por qué hace falta)
#
# Las tres reglas de campo obligatorio de línea que faltaban. BR-24 —el importe
# neto— vive aparte porque además alimenta el cuadre de BR-CO-10; estas tres
# solo miran que el dato esté.
_DE_LINEA: tuple[tuple[str, str, str, str], ...] = (
    (
        "BR-22",
        "linea_cantidad",
        "Cantidad facturada",
        "Cada línea debe decir cuántas unidades se facturan.",
    ),
    (
        "BR-23",
        "linea_unidad",
        "Unidad de medida",
        "Cada línea debe decir en qué unidad se mide lo que factura: "
        "unidades, kilos, horas...",
    ),
    (
        "BR-26",
        "linea_precio",
        "Precio unitario neto",
        "Cada línea debe llevar el precio por unidad, sin impuestos.",
    ),
    (
        "BR-21",
        "linea_id",
        "Identificador de línea",
        "Cada línea debe llevar un identificador que la distinga de las "
        "demás. Sin él, una queja sobre «la línea 3» no se puede referir a "
        "nada concreto del documento.",
    ),
    (
        "BR-25",
        "linea_nombre",
        "Nombre del concepto",
        "Cada línea debe decir qué se factura en ella.",
    ),
)


def _reglas_campos_de_linea(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-22, BR-23 y BR-26: lo que toda línea tiene que traer.

    Son las tres que separan «esta factura está bien formada» de «esta factura
    dice qué se vendió». Sin cantidad, sin unidad y sin precio unitario, una
    línea es una descripción y un importe: se puede pagar, pero no se puede
    comprobar, ni casar con un albarán, ni discutir.

    Se agrupan por regla y no por línea: un documento de cien líneas sin unidad
    de medida tiene **un** problema, no cien. El campo enumera cuáles, que es
    lo que hace falta para arreglarlo.

    Las líneas se nombran por su identificador (BT-126) cuando la sintaxis lo
    tiene, y por su posición cuando no —Facturae, por ejemplo, no lo tiene—.
    Decir «línea 3» siempre es peor que decir «línea A-0003», pero es infinitamente
    mejor que no decir cuál.
    """
    lineas = raiz.xpath(sintaxis.lineas, namespaces=sintaxis.espacios)
    if not lineas:
        # De que no haya ninguna ya se queja BR-16, y con mejor consejo.
        return []

    incidencias: list[Incidencia] = []
    for codigo, atributo, campo, explicacion in _DE_LINEA:
        ruta = getattr(sintaxis, atributo)
        if ruta == SIN_MAPA:
            # Igual que en los campos de cabecera: si la sintaxis no tiene
            # dónde escribirlo, la línea no está incompleta. Se dice una vez
            # por documento y no una por línea, que sería el mismo hueco
            # repetido tantas veces como conceptos tenga la factura.
            incidencias.append(
                Incidencia(
                    codigo,
                    NOTA,
                    f"{explicacion} La sintaxis {sintaxis.nombre} no tiene "
                    "ningún elemento con ese significado en la línea, así que "
                    "no se ha podido comprobar. No es un defecto del documento.",
                    campo=campo,
                    encontrado="(sin correspondencia en esta sintaxis)",
                )
            )
            continue

        faltan = [
            texto(linea, sintaxis.linea_id, sintaxis) or str(indice)
            for indice, linea in enumerate(lineas, start=1)
            if texto(linea, ruta, sintaxis) is None
        ]
        if faltan:
            incidencias.append(
                Incidencia(
                    codigo,
                    ERROR,
                    explicacion,
                    campo=f"{campo} · líneas " + ", ".join(faltan),
                    encontrado="(falta)",
                )
            )
    return incidencias


def _regla_lineas(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-16: la factura debe tener al menos una línea."""
    if not raiz.xpath(sintaxis.lineas, namespaces=sintaxis.espacios):
        return [
            Incidencia(
                "BR-16",
                ERROR,
                "La factura no tiene ninguna línea. Debe detallar al menos un "
                "concepto facturado.",
                campo="Líneas de factura",
                encontrado="0 líneas",
            )
        ]
    return []


# --- Reglas de cuadre aritmético -------------------------------------------


def _reglas_ajustes(
    raiz, sintaxis: Sintaxis, descuentos: Decimal, cargos: Decimal
) -> list[Incidencia]:
    """BR-CO-11 y BR-CO-12: los totales de ajustes son la suma de los ajustes.

    Un descuento o un cargo de documento se escribe dos veces: detallado en su
    bloque, con su importe y su tipo de IVA, y sumado en el total de la
    factura. Que las dos cifras digan lo mismo es lo que permite fiarse de
    cualquiera de las dos.
    """
    detallados: dict[bool, Decimal] = {True: Decimal(0), False: Decimal(0)}
    hay_alguno = False
    for nodo in raiz.xpath(sintaxis.cargos, namespaces=sintaxis.espacios):
        cantidad = importe(nodo, sintaxis.cargo_importe, sintaxis)
        if cantidad is None:
            continue
        marca = (texto(nodo, sintaxis.cargo_es_cargo, sintaxis) or "").lower()
        detallados[marca in sintaxis.marcas_de_cargo] += cantidad
        hay_alguno = True

    # Si no se detalla ni uno, no se compara nada: de esa factura ya se queja
    # `iva` diciendo que no ha podido repartir la base por tipos, y ahí el
    # consejo útil es «detállalos», no «la resta no cuadra».
    #
    # Basta con que haya **alguno**, no uno de cada lado: una factura que
    # detalla sus cargos y declara además un total de descuentos que no
    # detalla se queda sin ese aviso —ajustes tiene—, así que si aquí se
    # exigiera un descuento detallado para mirar los descuentos, ese total
    # fantasma no lo cazaría nadie.
    if not hay_alguno:
        return []

    incidencias: list[Incidencia] = []
    for es_cargo, codigo, nombre, declarado in (
        (False, "BR-CO-11", "descuentos", descuentos),
        (True, "BR-CO-12", "cargos", cargos),
    ):
        if cuadra_exacto(detallados[es_cargo], declarado):
            continue
        incidencias.append(
            Incidencia(
                codigo,
                ERROR,
                f"El total de {nombre} que declara la factura no es la suma de "
                f"los {nombre} que detalla.",
                campo=f"Total de {nombre} de documento",
                esperado=(
                    f"{cifras.calculada(redondear(detallados[es_cargo]))} "
                    "(lo que suman los detallados)"
                ),
                encontrado=cifras.tiene(declarado),
            )
        )
    return incidencias


def _reglas_cuadre(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """Las BR-CO-*: que las sumas de la factura cuadren entre sí.

    Son las que más rechazos provocan y las más difíciles de ver a ojo, porque
    el error suele estar en una línea perdida entre cincuenta.
    """
    incidencias: list[Incidencia] = []

    def leer(atributo: str) -> Decimal | None:
        return importe(raiz, getattr(sintaxis, atributo), sintaxis)

    def leer_o_cero(atributo: str) -> Decimal:
        return leer(atributo) or Decimal(0)

    moneda = texto(raiz, sintaxis.moneda, sintaxis)
    suma_lineas = leer("suma_lineas")
    base = leer("base")
    con_impuestos = leer("con_impuestos")
    a_pagar = leer("a_pagar")
    descuentos = leer_o_cero("descuentos_total")
    cargos = leer_o_cero("cargos_total")
    anticipos = leer_o_cero("anticipos")
    redondeo = leer_o_cero("redondeo")
    impuestos = importe_en_moneda(raiz, sintaxis.impuestos, sintaxis, moneda)

    # BR-24: cada línea debe llevar su importe neto. Se comprueba aparte del
    # cuadre, porque una línea sin importe es un error aunque la factura no
    # declare el total; si se anida bajo esa condición, deja de avisar justo
    # en el caso en que faltan las dos cosas.
    lineas = raiz.xpath(sintaxis.lineas, namespaces=sintaxis.espacios)
    acumulado = Decimal(0)
    sin_importe: list[str] = []
    for indice, linea in enumerate(lineas, start=1):
        cantidad = importe(linea, sintaxis.linea_importe, sintaxis)
        if cantidad is None:
            sin_importe.append(
                texto(linea, sintaxis.linea_id, sintaxis) or str(indice)
            )
        else:
            acumulado += cantidad

    if sin_importe:
        incidencias.append(
            Incidencia(
                "BR-24",
                ERROR,
                "Hay líneas sin importe neto. Cada línea debe llevar el suyo.",
                campo="Líneas " + ", ".join(sin_importe),
                encontrado="(falta el importe)",
            )
        )

    # BR-CO-10: la suma declarada debe coincidir con la suma real de las líneas.
    # Solo tiene sentido si todas las líneas tienen importe.
    #
    # **Exacta**, redondeando la suma a dos decimales, como todas las sumas de
    # la cabecera de aquí abajo. Durante meses se toleró un céntimo con el
    # argumento de que la norma redondea; la norma redondea la suma y luego
    # compara sin margen, y un total que se aparta un céntimo de sus líneas
    # salía limpio. Lo cazaron las pruebas oficiales el 13-09-2026.
    #
    # Y lo que se escribe como «debería ser» es **la cifra que se comparó**,
    # `redondear(…)`, en esta regla y en todas las de `cuadra_exacto`. Con
    # `:.2f` a secas la cifra salía de otro redondeo, el de `Decimal`, que
    # lleva las mitades al par: una línea de 100.125 con suma declarada
    # 100.12 daba «Debería ser: 100.12 · Tiene: 100.12», un error que se
    # contradice. La regla, como la oficial, redondea a 100.13. Medido el
    # 05-10-2026, y lo mismo en BR-CO-13 a BR-CO-16 y en negativo.
    if lineas and suma_lineas is not None and not sin_importe:
        if not cuadra_exacto(acumulado, suma_lineas):
            incidencias.append(
                Incidencia(
                    "BR-CO-10",
                    ERROR,
                    "La suma de importes de línea que declara la factura no "
                    "coincide con la suma real de sus líneas. Suele ser una "
                    "línea añadida o modificada sin recalcular el total.",
                    campo="Suma de importes de línea",
                    esperado=(
                        f"{cifras.calculada(redondear(acumulado))} (suma de "
                        + (
                            "la única línea"
                            if len(lineas) == 1
                            else f"las {len(lineas)} líneas"
                        )
                        + ")"
                    ),
                    encontrado=cifras.tiene(suma_lineas),
                )
            )

    # BR-CO-11 y BR-CO-12: el total de descuentos y el de cargos que declara la
    # factura tienen que ser la suma de los que detalla. Sin esto, el error
    # salía igualmente pero por el sitio equivocado: como BR-{X}-08, señalando
    # el desglose de IVA, cuando lo que estaba mal era el total del ajuste.
    incidencias.extend(_reglas_ajustes(raiz, sintaxis, descuentos, cargos))

    # BR-CO-13: base imponible = suma de líneas - descuentos + cargos.
    if suma_lineas is not None and base is not None:
        calculada = suma_lineas - descuentos + cargos
        if not cuadra_exacto(calculada, base):
            detalle = cifras.en_castellano(suma_lineas)
            if descuentos:
                detalle += f" - {cifras.en_castellano(descuentos)} de descuentos"
            if cargos:
                detalle += f" + {cifras.en_castellano(cargos)} de cargos"
            incidencias.append(
                Incidencia(
                    "BR-CO-13",
                    ERROR,
                    "La base imponible no cuadra con las líneas menos los "
                    "descuentos más los cargos.",
                    campo="Base imponible total",
                    esperado=f"{cifras.calculada(redondear(calculada))}  ({detalle})",
                    encontrado=cifras.tiene(base),
                )
            )

    # BR-CO-15: total con impuestos = base imponible + impuestos, exacta.
    #
    # Y con **un solo** total de impuestos en la moneda de la factura. UBL y
    # CII dejan declararlo otra vez en la moneda de contabilidad (BT-111), con
    # otro `currencyID`, y eso está bien; dos en la misma moneda no, porque no
    # se sabe cuál es. Aquí se leía el primero y se seguía: lo cazaron las
    # pruebas oficiales, que traen justo ese caso.
    #
    # Contar solo se puede donde cada total dice su moneda. EDIFACT no la dice
    # en el importe, y en una factura EANCOM el `MOA+176` sale una vez en el
    # resumen y otra por cada tipo: contarlos daba dos totales en cuatro
    # facturas reales que traen uno. Ahí no se cuenta.
    totales = [
        nodo for nodo in raiz.xpath(sintaxis.impuestos, namespaces=sintaxis.espacios)
        if not isinstance(nodo, str)
    ]
    se_puede_contar = bool(moneda) and any(
        nodo.get("currencyID") is not None for nodo in totales)
    en_su_moneda = (
        [n for n in totales if n.get("currencyID") == moneda]
        if se_puede_contar else totales
    )
    if se_puede_contar and len(en_su_moneda) > 1:
        incidencias.append(
            Incidencia(
                "BR-CO-15",
                ERROR,
                f"La factura declara {len(en_su_moneda)} veces el importe total "
                "de impuestos en su moneda, y tiene que declararlo una. Si una "
                "de las dos es la de la moneda de contabilidad, tiene que "
                "decirlo con su código de moneda.",
                campo="Importe total de impuestos",
                esperado=f"uno solo en {moneda or 'la moneda de la factura'}",
                encontrado=", ".join(
                    cifras.tiene(a_decimal(n.text)) for n in en_su_moneda),
            )
        )
    elif base is not None and con_impuestos is not None:
        if impuestos is not None and not en_su_moneda:
            # Hay total de impuestos, pero en otra moneda. Para la norma eso
            # es no tenerlo en la de la factura, salvo que la factura no
            # lleve impuesto ninguno: el esquematrón de CII acepta entonces un
            # total igual a la base.
            if con_impuestos != base:
                incidencias.append(
                    Incidencia(
                        "BR-CO-15",
                        ERROR,
                        "El importe total de impuestos no está en la moneda "
                        "de la factura, así que el total con impuestos no se "
                        "puede comprobar contra él.",
                        campo="Importe total de impuestos",
                        esperado=f"un total en {moneda}",
                        encontrado="solo en otra moneda",
                    )
                )
        elif impuestos is None:
            incidencias.append(
                Incidencia(
                    "IVA-SIN-TOTAL",
                    AVISO,
                    "La factura no declara el importe total de impuestos, así "
                    "que no se ha podido comprobar que el total cuadre.",
                    campo="Importe total de impuestos",
                    encontrado="(falta)",
                )
            )
        else:
            calculada = base + impuestos
            if not cuadra_exacto(calculada, con_impuestos):
                incidencias.append(
                    Incidencia(
                        "BR-CO-15",
                        ERROR,
                        "El total con impuestos no es la base imponible más el "
                        "importe de impuestos.",
                        campo="Total con impuestos",
                        esperado=(
                            f"{cifras.calculada(redondear(calculada))}  "
                            f"({cifras.en_castellano(base)} + "
                            f"{cifras.en_castellano(impuestos)} de impuestos)"
                        ),
                        encontrado=cifras.tiene(con_impuestos),
                    )
                )

    # BR-CO-16: a pagar = total con impuestos - anticipos + redondeo.
    if con_impuestos is not None and a_pagar is not None:
        calculada = con_impuestos - anticipos + redondeo
        if not cuadra_exacto(calculada, a_pagar):
            desglose = []
            if anticipos:
                desglose.append(f"- {cifras.en_castellano(anticipos)} ya pagados")
            if redondeo:
                desglose.append(f"+ {cifras.en_castellano(redondeo)} de redondeo")
            explicacion = (
                f"{cifras.calculada(redondear(calculada))}  "
                f"({cifras.en_castellano(con_impuestos)} {' '.join(desglose)})"
                if desglose
                else f"{cifras.calculada(redondear(calculada))}, que es el "
                "total con impuestos"
            )
            incidencias.append(
                Incidencia(
                    "BR-CO-16",
                    ERROR,
                    "El importe a pagar no cuadra con el total menos lo ya "
                    "anticipado.",
                    campo="Total a pagar",
                    esperado=explicacion,
                    encontrado=cifras.tiene(a_pagar),
                )
            )

    return incidencias


# --- BT-3: el tipo de documento --------------------------------------------

# Los 62 códigos de UNTDID 1001 que EN 16931 admite en BT-3. No están escritos
# de memoria: se sacaron el 06-09-2026 de `BR-CL-01` en
# `cii/schematron/codelist/EN16931-CII-codes.sch`, los artefactos oficiales de
# la Comisión Europea, que es la misma regla que aplican los validadores de
# PEPPOL y de XRechnung.
_UNCL1001 = frozenset(
    "71 80 81 82 83 84 102 130 202 203 204 211 218 219 261 262 295 296 308 "
    "325 326 331 380 381 382 383 384 385 386 387 388 389 390 393 394 395 396 "
    "420 456 457 458 471 472 473 500 501 502 503 527 532 553 575 623 633 751 "
    "780 817 870 875 876 877 935".split()
)

# Del vocabulario de Facturae al de EN 16931.
#
# `InvoiceClass` dice qué es el documento: OO original, OC original
# recapitulativa, CO copia de la original, CC copia recapitulativa. Las cuatro
# son facturas ordinarias, y una copia no deja de serlo: 380.
#
# Las rectificativas —OR y CR— no están aquí, y no es un olvido: ver
# `_bt3_de_facturae`.
_CLASE_A_UNCL1001 = {"OO": "380", "OC": "380", "CO": "380", "CC": "380"}

# Cómo rectifica una rectificativa española, y qué se puede decir de cada
# método en UNTDID 1001. Los cuatro códigos y sus significados salen del
# esquema oficial —`CorrectionMethodType` en `Facturaev3_2_2.xsd`—, no de una
# reconstrucción: la fuente estaba dentro de `web/paquete.zip` desde el
# principio y aquí se afirmó durante meses que no se había podido contrastar.
#
# Dos se pueden traducir y dos no, y la diferencia importa:
#
# - `01` **rectificación íntegra** rehace la factura entera con los datos
#   corregidos. La definición de 384 en UNTDID 1001 es «commercial invoice
#   which includes revised information differing from an earlier submission of
#   the same invoice». Es lo mismo dicho en dos idiomas.
# - `03` **descuento por volumen de operaciones durante un periodo** solo puede
#   restar de lo ya facturado, y eso es un abono: 381.
# - `02` **por diferencias** factura únicamente la diferencia, y si esa
#   diferencia sube o baja no lo dice el método: lo dicen los importes. Se
#   podría mirar el signo, pero entonces el código europeo dependería de una
#   cuenta y no de lo que el documento declara, que es otra cosa distinta.
# - `04` **autorizadas por la Agencia Tributaria** no dice cómo se rectifica,
#   dice quién lo autorizó. No hay nada que traducir.
#
# La correspondencia de `01` y `03` es **nuestra lectura de las definiciones**,
# no un mapa oficial: el anexo I del proyecto de orden no menciona Facturae ni
# una vez. Por eso, cuando se usa, sale dicho con una NOTA.
_METODO_A_UNCL1001 = {"01": "384", "03": "381"}

_METODO_DICHO = {
    "01": "rectificación íntegra",
    "02": "rectificación por diferencias",
    "03": "rectificación por descuento por volumen de operaciones",
    "04": "rectificación autorizada por la Agencia Tributaria",
}


def _bt3_de_facturae(
    raiz, sintaxis: Sintaxis
) -> tuple[str | None, str | None, str | None]:
    """El tipo de documento de una factura Facturae, en el vocabulario europeo.

    Devuelve `(codigo, por_qué_no_se_sabe, con_qué_base)`. El tercero solo
    viene cuando el código se ha deducido del método de rectificación, para
    que salga dicho de dónde sale.

    Hay tres piezas y ninguna es `InvoiceDocumentType`, que es lo que uno
    esperaría por el nombre. Ese campo distingue factura completa (FC) de
    simplificada (FA), que es una pregunta española sobre el contenido y no
    sobre el tipo de documento; su tercer valor, AF de autofactura, **está en
    desuso** desde el RD 1789/2010 y la propia documentación de Facturae manda
    usar `InvoiceIssuerType` en su lugar.

    Así que:

    - `InvoiceIssuerType = RE` («Recipient», la emite quien la recibe) es
      exactamente la definición de 389, «Self-billed invoice: an invoice the
      invoicee is producing instead of the seller».
    - `InvoiceClass` original o copia es 380.
    - Una rectificativa lo dice `CorrectionMethod`, y de los cuatro métodos
      del esquema dos se traducen y dos no. El porqué de cada uno está en
      `_METODO_A_UNCL1001`, arriba.
    """
    emisor = texto(raiz, sintaxis.tipo_emisor, sintaxis)
    if emisor == "RE":
        return "389", None, None
    clase = texto(raiz, sintaxis.tipo_clase, sintaxis)
    if clase in _CLASE_A_UNCL1001:
        return _CLASE_A_UNCL1001[clase], None, None
    if clase in ("OR", "CR"):
        metodo = texto(raiz, sintaxis.tipo_metodo, sintaxis)
        if metodo in _METODO_A_UNCL1001:
            return _METODO_A_UNCL1001[metodo], None, _METODO_DICHO[metodo]
        if metodo == "02":
            return None, (
                "es una rectificativa por diferencias: factura solo la "
                "diferencia, y si esa diferencia suma o resta no lo dice el "
                "método sino los importes. Su equivalente europeo es 384 "
                "(factura corregida) o 381 (abono) según el caso, y deducirlo "
                "de una cuenta no es lo mismo que leerlo del documento."
            ), None
        if metodo == "04":
            return None, (
                "es una rectificativa autorizada por la Agencia Tributaria, y "
                "eso dice quién la autorizó, no cómo rectifica. No hay de "
                "dónde deducir el tipo europeo."
            ), None
        return None, (
            "es una factura rectificativa y no declara con qué método "
            "rectifica, que es lo que decidiría entre 384 (factura corregida) "
            "y 381 (abono)."
        ), None
    return None, None, None


def _regla_tipo_de_documento(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-CL-01: el tipo de documento tiene que estar en la lista UNTDID 1001."""
    notas: list[Incidencia] = []
    if sintaxis.tipo_derivado == "facturae":
        codigo, por_que_no, con_que_base = _bt3_de_facturae(raiz, sintaxis)
        if por_que_no:
            return [
                Incidencia(
                    "FE-TIPO-SIN-EQUIVALENTE",
                    NOTA,
                    f"El tipo de documento no se ha traducido a EN 16931: "
                    f"{por_que_no}",
                    campo="Tipo de documento",
                    encontrado=texto(raiz, sintaxis.tipo_clase, sintaxis) or "",
                )
            ]
        if con_que_base:
            # Se acepta y se dice con qué base, que es para lo que existe NOTA.
            # La correspondencia es nuestra lectura de las definiciones del
            # esquema, no un mapa publicado por nadie, y eso va dicho.
            notas.append(
                Incidencia(
                    "FE-TIPO-POR-METODO",
                    NOTA,
                    f"El tipo europeo {codigo} se ha deducido de que la "
                    f"factura declara una {con_que_base}. Facturae no escribe "
                    "el código de UNTDID 1001 en ningún sitio y no hay mapa "
                    "oficial que lo traduzca: esta correspondencia sale de las "
                    "definiciones del propio esquema de Facturae.",
                    campo="Tipo de documento",
                    encontrado=texto(raiz, sintaxis.tipo_metodo, sintaxis) or "",
                )
            )
    else:
        codigo = texto(raiz, sintaxis.tipo, sintaxis)

    if codigo is None or codigo in _UNCL1001:
        # De que falte ya se queja BR-04, y con mejor consejo.
        return notas
    return notas + [
        Incidencia(
            "BR-CL-01",
            ERROR,
            "El tipo de documento no es ninguno de los que admite EN 16931. "
            "La norma exige que salga de la lista UNTDID 1001: 380 para una "
            "factura ordinaria, 381 para un abono, 384 para una corregida.",
            campo="Tipo de documento",
            esperado="un código de UNTDID 1001",
            encontrado=codigo,
        )
    ]


# --- Entrada pública -------------------------------------------------------


def reglas(raiz, deteccion, espanola: bool = True,
           categorias_de_mas: frozenset[str] = frozenset(),
           comprador_registro_de_mas: tuple[str, ...] = ()) -> list[Incidencia]:
    """Las reglas EN 16931 sobre un documento ya parseado.

    Separado de `validar` para que el orquestador pueda pasar el mismo árbol a
    varios conjuntos de reglas en vez de que cada uno se lo parsee por su
    cuenta. `raiz` puede ser None cuando el documento no es XML (EDIFACT), y
    entonces ni se mira.

    `categorias_de_mas` son categorías de IVA que este documento puede usar
    aunque la lista de 2017 no las tenga. Las decide el orquestador, que es
    quien sabe si la factura declara la solución pública
    (`solucion_publica.categorias_que_la_norma_no_tiene`): este módulo no
    puede importar aquel, que ya importa de este.

    `comprador_registro_de_mas`, lo mismo con el sitio donde la orden pone el
    registro del comprador (BT-47): ver `iva._regla_identificadores`.
    """
    if deteccion.familia == RESPUESTA:
        # Una respuesta no es una factura: la EN 16931 no dice nada de ella, y
        # el aviso de abajo —«solo se ha identificado, no validado»— sería
        # falso, porque su forma sí se mira (en `esquema.reglas`) y la columna
        # de la forma diría «Sin errores» al lado de un «no validado». Va
        # antes del mapa a propósito: si algún día `SINTAXIS` gana una clave
        # que la nombre, esto tiene que seguir contestando «no me toca».
        return []
    sintaxis = SINTAXIS.get(deteccion.familia or "")
    if sintaxis is None:
        # La lista sale del mapa y no de la memoria. Escrita a mano decía «UBL
        # y CII» mucho después de que EDIFACT y Facturae tuvieran el suyo: una
        # cifra publicada que envejece sola, que es el fallo de siempre.
        return [
            Incidencia(
                "SIN-SOPORTE",
                AVISO,
                "Las reglas EN 16931 están implementadas para "
                + ", ".join(sorted(SINTAXIS))
                + f". Este documento es {deteccion.familia} y solo se ha "
                "identificado, no validado.",
                campo="Formato",
                encontrado=deteccion.familia,
            )
        ]
    if raiz is None:
        # Y este es el caso que de verdad se da: el formato está
        # implementado, lo que pasa es que el fichero no da ni para montar un
        # árbol. Decirle a un Facturae que Facturae no se comprueba es mentir
        # sobre lo que hace este validador y mandar a buscar el fallo donde no
        # está.
        return [
            Incidencia(
                "SIN-SOPORTE",
                AVISO,
                f"El documento se ha identificado como {deteccion.familia}, "
                "pero no se ha podido leer entero, así que solo se ha "
                "identificado, no validado. Las reglas EN 16931 sí están "
                "implementadas para este formato.",
                campo="Formato",
                encontrado=deteccion.familia,
            )
        ]

    if deteccion.familia == FACTURAE:
        # Facturae va por su camino: es un lote y sus partes están fuera de la
        # factura. El porqué, entero, en `_reglas_facturae`.
        return _reglas_facturae(raiz, sintaxis, espanola)

    incidencias: list[Incidencia] = []
    if not deteccion.conforme_en16931 and deteccion.perfil:
        # Esto se llamó BR-01 hasta el 13-09-2026, y BR-01 no dice esto: pide
        # que el identificador de especificación **esté**, no que nombre a la
        # EN 16931. Las pruebas oficiales dan por bueno un `123`. Que no la
        # nombre es algo que conviene saber, y es una opinión de la casa, así
        # que va con código de la casa. Si falta del todo, eso sí es BR-01, y
        # lo dice la regla de los campos obligatorios.
        incidencias.append(
            Incidencia(
                "PERFIL-SIN-EN16931",
                AVISO,
                "El documento no declara conformidad con EN 16931 en su "
                f"{sintaxis.nombre_perfil}. Se valida igualmente, pero un "
                "receptor estricto podría rechazarlo por eso.",
                campo="Identificador de especificación",
                esperado="urn:cen.eu:en16931:2017... o :2026...",
                encontrado=deteccion.perfil or "(falta)",
            )
        )

    incidencias.extend(_reglas_obligatorios(raiz, sintaxis))
    incidencias.extend(_regla_tipo_de_documento(raiz, sintaxis))
    incidencias.extend(_regla_lineas(raiz, sintaxis))
    incidencias.extend(_reglas_campos_de_linea(raiz, sintaxis))
    incidencias.extend(_reglas_cuadre(raiz, sintaxis))
    incidencias.extend(modelo.reglas(raiz, sintaxis))
    incidencias.extend(decimales.reglas(raiz, sintaxis))
    incidencias.extend(listas_de_codigos.reglas(
        raiz, sintaxis, de_mas={"UNCL_5305": categorias_de_mas}))
    incidencias.extend(iva.reglas(
        raiz, sintaxis, espanola=espanola, categorias_de_mas=categorias_de_mas,
        comprador_registro_de_mas=comprador_registro_de_mas))
    return incidencias


# --- Facturae ---------------------------------------------------------------


def _etiqueta_facturae(factura, cuantas: int) -> str:
    """Cómo nombrar a una factura dentro del lote.

    Mismo criterio que en `facturae.py`, y a propósito: los dos conjuntos de
    reglas caen en el mismo informe, y que la misma factura se llame de dos
    maneras distintas según quién se queje sería peor que no nombrarla.
    """
    if cuantas <= 1:
        return ""
    cabecera = factura.xpath("./InvoiceHeader")
    if not cabecera:
        return ""
    serie = (cabecera[0].findtext("InvoiceSeriesCode") or "").strip()
    numero = (cabecera[0].findtext("InvoiceNumber") or "").strip() or "(sin número)"
    return f"Factura {serie}{numero} · "


def _reglas_facturae(raiz, sintaxis: Sintaxis, espanola: bool) -> list[Incidencia]:
    """Las reglas EN 16931 sobre un lote Facturae.

    Facturae no se parece a UBL ni a CII en la forma, y son dos diferencias las
    que obligan a tener esta función en vez de reutilizar el camino común:

    1. **Un fichero es un lote.** Puede traer varias facturas, y cada una tiene
       sus líneas, su desglose y sus totales. Las reglas se evalúan una vez por
       factura, no una vez por fichero, o los totales de la segunda se
       compararían con las líneas de la primera.

    2. **Las partes están fuera de la factura.** Vendedor y comprador cuelgan
       de la raíz y son comunes al lote, así que el mapa los pide subiendo dos
       pisos desde el `<Invoice>`. Es la razón de que las rutas de `Sintaxis`
       se evalúen sobre la factura y no sobre la raíz.
    """
    # El fichero puede llegar envuelto en una firma XAdES, con el Facturae
    # colgando de dentro. Mismo desenvoltorio que en `facturae.py`: sin él no
    # se encontraría ni un elemento y el informe saldría vacío y tranquilo,
    # que es la peor forma de fallar.
    if raiz.xpath("local-name()") != "Facturae":
        internos = raiz.xpath("//*[local-name()='Facturae']")
        if not internos:
            return []
        raiz = internos[0]

    facturas = raiz.xpath("./Invoices/Invoice")
    if not facturas:
        return []

    incidencias: list[Incidencia] = []
    for factura in facturas:
        donde = _etiqueta_facturae(factura, len(facturas))
        de_esta: list[Incidencia] = []
        de_esta.extend(_reglas_obligatorios(factura, sintaxis))
        de_esta.extend(_regla_lineas(factura, sintaxis))
        de_esta.extend(_reglas_campos_de_linea(factura, sintaxis))
        de_esta.extend(_reglas_cuadre(factura, sintaxis))
        de_esta.extend(_regla_tipo_de_documento(factura, sintaxis))
        de_esta.extend(modelo.reglas(factura, sintaxis))
        de_esta.extend(decimales.reglas(factura, sintaxis))
        de_esta.extend(listas_de_codigos.reglas(factura, sintaxis))
        de_esta.extend(iva.reglas(factura, sintaxis, espanola=espanola))
        if donde:
            de_esta = [
                replace(i, campo=f"{donde}{i.campo}" if i.campo else donde.rstrip(" ·"))
                for i in de_esta
            ]
        incidencias.extend(de_esta)
    return incidencias


def validar(datos: bytes | str) -> Informe:
    """Valida una factura contra las reglas de negocio implementadas."""
    deteccion = detectar(datos)
    informe = Informe(deteccion=deteccion)
    if not deteccion:
        return informe

    raiz = None
    if deteccion.familia in SINTAXIS:
        if isinstance(datos, str):
            datos = datos.encode("utf-8")
        raiz, _ = edifact.arbol(datos, deteccion)

    informe.incidencias.extend(reglas(raiz, deteccion))
    return informe
