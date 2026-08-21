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

from decimal import Decimal

from lxml import etree

from validador import iva
from validador.formato import detectar, parser
from validador.incidencias import AVISO, ERROR, Incidencia, Informe
from validador.sintaxis import (
    NS_CII,
    NS_UBL,
    SINTAXIS,
    SINTAXIS_CII,
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
    "NS",
    "NS_CII",
    "NS_UBL",
    "SINTAXIS",
    "SINTAXIS_CII",
    "SINTAXIS_UBL",
    "Sintaxis",
    "TOLERANCIA",
    "reglas",
    "validar",
]

# Nombre de antes, cuando este módulo llevaba dentro el mapa y solo sabía de UBL.
NS = NS_UBL


# --- Reglas de campos obligatorios -----------------------------------------

# (código, campo de `Sintaxis`, nombre en castellano, explicación, contenedor)
#
# «contenedor» marca los elementos que agrupan a otros y por tanto no tienen
# texto propio: una dirección postal no está vacía por no llevar texto suelto.
# Antes esto se deducía mirando si la ruta acababa en «PostalAddress», que en
# UBL colaba y en CII —donde se llama «PostalTradeAddress»— habría dado un
# error falso en todas las facturas.
_OBLIGATORIOS: tuple[tuple[str, str, str, str, bool], ...] = (
    (
        "BR-01",
        "perfil",
        "Identificador de especificación",
        "La factura debe declarar a qué especificación se ajusta.",
        False,
    ),
    (
        "BR-02",
        "numero",
        "Número de factura",
        "La factura debe llevar número.",
        False,
    ),
    (
        "BR-03",
        "fecha",
        "Fecha de expedición",
        "La factura debe llevar fecha de expedición.",
        False,
    ),
    (
        "BR-04",
        "tipo",
        "Código de tipo de documento",
        "El documento debe indicar de qué tipo es: 380 para una factura "
        "ordinaria, 381 para un abono.",
        False,
    ),
    (
        "BR-05",
        "moneda",
        "Moneda",
        "La factura debe indicar en qué moneda está.",
        False,
    ),
    (
        "BR-06",
        "vendedor_nombre",
        "Nombre del vendedor",
        "Falta el nombre o razón social de quien emite la factura.",
        False,
    ),
    (
        "BR-07",
        "comprador_nombre",
        "Nombre del comprador",
        "Falta el nombre o razón social de quien recibe la factura.",
        False,
    ),
    (
        "BR-08",
        "vendedor_direccion",
        "Dirección del vendedor",
        "Falta la dirección postal del vendedor.",
        True,
    ),
    (
        "BR-09",
        "vendedor_pais",
        "País del vendedor",
        "La dirección del vendedor debe incluir el código de país (ES, FR...).",
        False,
    ),
    (
        "BR-10",
        "comprador_direccion",
        "Dirección del comprador",
        "Falta la dirección postal del comprador.",
        True,
    ),
    (
        "BR-11",
        "comprador_pais",
        "País del comprador",
        "La dirección del comprador debe incluir el código de país.",
        False,
    ),
    (
        "BR-12",
        "suma_lineas",
        "Suma de importes de línea",
        "Falta la suma de los importes netos de las líneas.",
        False,
    ),
    (
        "BR-13",
        "base",
        "Base imponible total",
        "Falta el importe total sin impuestos.",
        False,
    ),
    (
        "BR-14",
        "con_impuestos",
        "Total con impuestos",
        "Falta el importe total con impuestos incluidos.",
        False,
    ),
    (
        "BR-15",
        "a_pagar",
        "Total a pagar",
        "Falta el importe que hay que pagar.",
        False,
    ),
)


def _reglas_obligatorios(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    incidencias = []
    for codigo, atributo, campo, explicacion, contenedor in _OBLIGATORIOS:
        ruta = getattr(sintaxis, atributo)
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
        detallados[marca in ("true", "1")] += cantidad
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


def reglas(raiz, deteccion) -> list[Incidencia]:
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
    incidencias.extend(_reglas_cuadre(raiz, sintaxis))
    incidencias.extend(iva.reglas(raiz, sintaxis))
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
        raiz = etree.fromstring(datos, parser=parser())

    informe.incidencias.extend(reglas(raiz, deteccion))
    return informe
