"""Cuántos decimales lleva cada importe: dos, como mucho.

Son las veintiuna reglas BR-DEC de EN 16931, y dicen todas lo mismo sobre un
importe distinto: los descuentos y cargos y sus bases, los totales, el
desglose y el neto de cada línea. Los precios y las cantidades no están en la
lista, y pueden llevar los decimales que hagan falta; los importes no.

Cada una corre en el mismo contexto que en el esquematrón —sin descuentos,
BR-DEC-01 no llega a correr— y los descuentos, cargos y líneas se buscan con
`modelo.grupos`, así que «descuento 2» es el mismo aquí que en BR-31.

Lo escrito o el valor
---------------------
La norma dice «dos decimales como mucho» y no dice si `10.500` son tres. Las
vinculaciones oficiales lo resuelven de dos formas: casi todas cuentan los
caracteres que hay detrás del punto, y ahí son tres; las de CII para el total
del impuesto redondean y comparan, y ahí son dos. Aquí se hace lo que haga la
de cada sintaxis, regla a regla, y lo dice `Sintaxis.decimales_por_valor`,
que se contrasta con la copia oficial. Cuando lo que sobra son ceros el
informe lo dice, porque entonces el importe está bien y lo que hay que cambiar
es cómo se escribe.

El total del impuesto
---------------------
BR-DEC-13 y BR-DEC-15 miran el mismo elemento en dos monedas: BT-110 es el
total en la de la factura y BT-111 en la de contabilidad. La vinculación de
UBL las escribe con un filtro que no deja pasar nada —compara la moneda del
importe con un `cbc:DocumentCurrencyCode` que busca **dentro** del importe— y
se cumplen siempre; está medido en `tests/test_decimales.py`. Aquí se hacen
como dice la norma, y BT-111 como en la vinculación de CII: el total cuya
moneda es la de contabilidad, lo sea también de la factura o no.
"""
from __future__ import annotations

from validador.incidencias import ERROR, Incidencia
from validador.modelo import grupos
from validador.sintaxis import (
    SIN_MAPA,
    Sintaxis,
    a_decimal,
    buscar,
    como_texto,
    texto,
)

__all__ = ["reglas"]

# (código, dónde se busca, qué campo de `Sintaxis`, cómo se llama en el informe)
#
# «Dónde» es un grupo de `modelo.grupos`. Los dos campos entre corchetes no
# están en el mapa con ese nombre: son el mismo total del impuesto separado
# por su moneda, y los resuelve `_importes`.
_IMPORTES = (
    ("BR-DEC-01", "descuentos_documento", "cargo_importe",
     "Importe del descuento de documento (BT-92)"),
    ("BR-DEC-02", "descuentos_documento", "cargo_base",
     "Base del descuento de documento (BT-93)"),
    ("BR-DEC-05", "cargos_documento", "cargo_importe",
     "Importe del cargo de documento (BT-99)"),
    ("BR-DEC-06", "cargos_documento", "cargo_base",
     "Base del cargo de documento (BT-100)"),
    ("BR-DEC-09", "documento", "suma_lineas",
     "Suma de los importes netos de las líneas (BT-106)"),
    ("BR-DEC-10", "documento", "descuentos_total",
     "Total de descuentos de documento (BT-107)"),
    ("BR-DEC-11", "documento", "cargos_total",
     "Total de cargos de documento (BT-108)"),
    ("BR-DEC-12", "documento", "base",
     "Total de la factura sin IVA (BT-109)"),
    ("BR-DEC-13", "documento", "[total del IVA]",
     "Total del IVA (BT-110)"),
    ("BR-DEC-14", "documento", "con_impuestos",
     "Total de la factura con IVA (BT-112)"),
    ("BR-DEC-15", "documento", "[total del IVA en la moneda de contabilidad]",
     "Total del IVA en la moneda de contabilidad (BT-111)"),
    ("BR-DEC-16", "documento", "anticipos",
     "Importe ya pagado (BT-113)"),
    ("BR-DEC-17", "documento", "redondeo",
     "Redondeo (BT-114)"),
    ("BR-DEC-18", "documento", "a_pagar",
     "Importe a pagar (BT-115)"),
    ("BR-DEC-19", "desglose", "desglose_base",
     "Base de la categoría de IVA (BT-116)"),
    ("BR-DEC-20", "desglose", "desglose_cuota",
     "Cuota de la categoría de IVA (BT-117)"),
    ("BR-DEC-23", "lineas", "linea_importe",
     "Importe neto de la línea (BT-131)"),
    ("BR-DEC-24", "descuentos_linea", "cargo_importe",
     "Importe del descuento de línea (BT-136)"),
    ("BR-DEC-25", "descuentos_linea", "cargo_base",
     "Base del descuento de línea (BT-137)"),
    ("BR-DEC-27", "cargos_linea", "cargo_importe",
     "Importe del cargo de línea (BT-141)"),
    ("BR-DEC-28", "cargos_linea", "cargo_base",
     "Base del cargo de línea (BT-142)"),
)


def _escrito(nodo) -> str:
    return (nodo if isinstance(nodo, str) else como_texto(nodo)).strip()


def _nodos(nodo, ruta: str, sintaxis: Sintaxis) -> list:
    if ruta == SIN_MAPA:
        return []
    return list(buscar(nodo, ruta, sintaxis.espacios))


def _importes(raiz, nodo, sintaxis: Sintaxis, campo: str) -> list:
    """Los elementos de un campo dentro de su grupo.

    El total del impuesto se separa por su moneda. Lo que no lleva moneda
    —EDIFACT la escribe aparte— es de la factura, y si la factura no dice
    la suya, todos lo son: separar sin saber por qué es inventar.
    """
    if not campo.startswith("["):
        return _nodos(nodo, getattr(sintaxis, campo), sintaxis)
    totales = _nodos(raiz, sintaxis.impuestos, sintaxis)
    def moneda_de(total):
        return None if isinstance(total, str) else total.get("currencyID")
    if "contabilidad" not in campo:
        moneda = texto(raiz, sintaxis.moneda, sintaxis)
        if not moneda:
            return totales
        return [t for t in totales if moneda_de(t) in (None, moneda)]
    if sintaxis.moneda_impuestos == SIN_MAPA:
        return []
    contabilidad = texto(raiz, sintaxis.moneda_impuestos, sintaxis)
    if not contabilidad:
        return []
    return [t for t in totales if moneda_de(t) == contabilidad]


def _decimales_del_valor(valor) -> int:
    """Cuántos decimales tiene un número sin contar los ceros del final.

    Con los dígitos y no con `quantize`: redondear a céntimos un importe de
    treinta cifras pasa de la precisión de `Decimal` y lanza una excepción.
    """
    _, digitos, exponente = valor.as_tuple()
    if exponente >= 0:
        return 0
    fraccion = "".join(map(str, digitos)).rjust(-exponente, "0")[exponente:]
    return len(fraccion.rstrip("0"))


def _sobran(escrito: str, por_valor: bool) -> bool | None:
    """Si lleva más de dos decimales, o None si no es un número.

    Lo que no es un número no es cosa de esta regla: lo dice el esquema de la
    sintaxis, o la regla que lo usa para una cuenta.
    """
    valor = a_decimal(escrito)
    if valor is None or not valor.is_finite():
        return None
    if por_valor:
        return _decimales_del_valor(valor) > 2
    return len(escrito.partition(".")[2]) > 2


def reglas(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    incidencias: list[Incidencia] = []
    for codigo, grupo, campo, que in _IMPORTES:
        por_valor = codigo in sintaxis.decimales_por_valor
        donde: list[str] = []
        escritos: list[str] = []
        for nombre, nodo in grupos(raiz, sintaxis, grupo):
            for importe in _importes(raiz, nodo, sintaxis, campo):
                escrito = _escrito(importe)
                if _sobran(escrito, por_valor):
                    if nombre not in donde:
                        donde.append(nombre)
                    escritos.append(escrito)
        if not escritos:
            continue
        ceros = all(_decimales_del_valor(a_decimal(e)) <= 2 for e in escritos)
        lugares = ", ".join(n for n in donde if n)
        incidencias.append(
            Incidencia(
                codigo,
                ERROR,
                "El importe lleva más de dos decimales, y la norma admite dos "
                "como mucho en los importes; los precios y las cantidades "
                "pueden llevar más, los importes no."
                + (" Aquí los que sobran son ceros: el importe está bien y "
                   "basta con no escribirlos." if ceros else ""),
                campo=que + (f" · {lugares}" if lugares else ""),
                esperado="dos decimales como mucho",
                encontrado=", ".join(escritos),
            )
        )
    return incidencias
