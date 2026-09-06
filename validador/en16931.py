"""Reglas de negocio de la norma EN 16931, sobre UBL y sobre CII.

La norma son 955 reglas y ahí es donde se produce la mayoría de los rechazos:
un documento puede pasar la validación de forma (XSD) y fallar la de contenido.

Este módulo implementa las reglas de mayor valor —campos obligatorios y las de
cuadre aritmético— con el mensaje escrito en castellano llano. La traducción es
el producto: las reglas son públicas y de todos, pero un error como «BR-CO-13»
no le dice nada a quien tiene que arreglar la factura.

Las reglas de IVA, que son una familia entera y siguen su propio patrón, viven
en `iva.py` y se llaman desde aquí: para quien usa el validador son las mismas
reglas de la misma norma.

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

from validador import edifact, iva
from validador.formato import FACTURAE, detectar, parser
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
    cuadra,
    fmt,
    importe,
    importe_en_moneda,
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
        if cuadra(detallados[es_cargo], declarado):
            continue
        incidencias.append(
            Incidencia(
                codigo,
                ERROR,
                f"El total de {nombre} que declara la factura no es la suma de "
                f"los {nombre} que detalla.",
                campo=f"Total de {nombre} de documento",
                esperado=f"{detallados[es_cargo]:.2f} (lo que suman los detallados)",
                encontrado=fmt(declarado),
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
    if lineas and suma_lineas is not None and not sin_importe:
        if not cuadra(acumulado, suma_lineas):
            incidencias.append(
                Incidencia(
                    "BR-CO-10",
                    ERROR,
                    "La suma de importes de línea que declara la factura no "
                    "coincide con la suma real de sus líneas. Suele ser una "
                    "línea añadida o modificada sin recalcular el total.",
                    campo="Suma de importes de línea",
                    esperado=(
                        f"{acumulado:.2f} (suma de "
                        + (
                            "la única línea"
                            if len(lineas) == 1
                            else f"las {len(lineas)} líneas"
                        )
                        + ")"
                    ),
                    encontrado=fmt(suma_lineas),
                )
            )

    # BR-CO-11 y BR-CO-12: el total de descuentos y el de cargos que declara la
    # factura tienen que ser la suma de los que detalla. Sin esto, el error
    # salía igualmente pero por el sitio equivocado: como BR-{X}-8, señalando
    # el desglose de IVA, cuando lo que estaba mal era el total del ajuste.
    incidencias.extend(_reglas_ajustes(raiz, sintaxis, descuentos, cargos))

    # BR-CO-13: base imponible = suma de líneas - descuentos + cargos.
    if suma_lineas is not None and base is not None:
        calculada = suma_lineas - descuentos + cargos
        if not cuadra(calculada, base):
            detalle = f"{suma_lineas:.2f}"
            if descuentos:
                detalle += f" - {descuentos:.2f} de descuentos"
            if cargos:
                detalle += f" + {cargos:.2f} de cargos"
            incidencias.append(
                Incidencia(
                    "BR-CO-13",
                    ERROR,
                    "La base imponible no cuadra con las líneas menos los "
                    "descuentos más los cargos.",
                    campo="Base imponible total",
                    esperado=f"{calculada:.2f}  ({detalle})",
                    encontrado=fmt(base),
                )
            )

    # BR-CO-15: total con impuestos = base imponible + impuestos.
    if base is not None and con_impuestos is not None:
        if impuestos is None:
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
            if not cuadra(calculada, con_impuestos):
                incidencias.append(
                    Incidencia(
                        "BR-CO-15",
                        ERROR,
                        "El total con impuestos no es la base imponible más el "
                        "importe de impuestos.",
                        campo="Total con impuestos",
                        esperado=(
                            f"{calculada:.2f}  ({base:.2f} + {impuestos:.2f} "
                            "de impuestos)"
                        ),
                        encontrado=fmt(con_impuestos),
                    )
                )

    # BR-CO-16: a pagar = total con impuestos - anticipos + redondeo.
    if con_impuestos is not None and a_pagar is not None:
        calculada = con_impuestos - anticipos + redondeo
        if not cuadra(calculada, a_pagar):
            desglose = []
            if anticipos:
                desglose.append(f"- {anticipos:.2f} ya pagados")
            if redondeo:
                desglose.append(f"+ {redondeo:.2f} de redondeo")
            explicacion = (
                f"{calculada:.2f}  ({con_impuestos:.2f} {' '.join(desglose)})"
                if desglose
                else f"{calculada:.2f}, que es el total con impuestos"
            )
            incidencias.append(
                Incidencia(
                    "BR-CO-16",
                    ERROR,
                    "El importe a pagar no cuadra con el total menos lo ya "
                    "anticipado.",
                    campo="Total a pagar",
                    esperado=explicacion,
                    encontrado=fmt(a_pagar),
                )
            )

    return incidencias


# --- Entrada pública -------------------------------------------------------


def reglas(raiz, deteccion, espanola: bool = True) -> list[Incidencia]:
    """Las reglas EN 16931 sobre un documento ya parseado.

    Separado de `validar` para que el orquestador pueda pasar el mismo árbol a
    varios conjuntos de reglas en vez de que cada uno se lo parsee por su
    cuenta. `raiz` puede ser None cuando el documento no es XML (EDIFACT), y
    entonces ni se mira.
    """
    sintaxis = SINTAXIS.get(deteccion.familia or "")
    if sintaxis is None or raiz is None:
        return [
            Incidencia(
                "SIN-SOPORTE",
                AVISO,
                "Las reglas EN 16931 están implementadas para UBL y para CII. "
                f"Este documento es {deteccion.familia} y solo se ha "
                "identificado, no validado.",
                campo="Formato",
                encontrado=deteccion.familia,
            )
        ]

    if deteccion.familia == FACTURAE:
        # Facturae va por su camino: es un lote y sus partes están fuera de la
        # factura. El porqué, entero, en `_reglas_facturae`.
        return _reglas_facturae(raiz, sintaxis, espanola)

    incidencias: list[Incidencia] = []
    if not deteccion.conforme_en16931:
        incidencias.append(
            Incidencia(
                "BR-01",
                AVISO,
                "El documento no declara conformidad con EN 16931 en su "
                f"{sintaxis.nombre_perfil}. Se valida igualmente, pero un "
                "receptor estricto podría rechazarlo por eso.",
                campo="Identificador de especificación",
                esperado="urn:cen.eu:en16931:2017...",
                encontrado=deteccion.perfil or "(falta)",
            )
        )

    incidencias.extend(_reglas_obligatorios(raiz, sintaxis))
    incidencias.extend(_regla_lineas(raiz, sintaxis))
    incidencias.extend(_reglas_campos_de_linea(raiz, sintaxis))
    incidencias.extend(_reglas_cuadre(raiz, sintaxis))
    incidencias.extend(iva.reglas(raiz, sintaxis, espanola=espanola))
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
