"""Las cuentas en que cada emisor pide que se le pague, factura a factura.

Por qué existe
--------------
El fraude más caro que llega con una factura no tiene nada mal escrito. Es
una factura correcta, de un proveedor de verdad, que pide el pago en otra
cuenta: alguien ha entrado en el correo del proveedor, o se hace pasar por él,
y lo único que cambia es el IBAN. INCIBE lo describe así en su página sobre el
fraude del correo comprometido ("cambiando la cuenta del banco donde realizar
los pagos") y aconseja "Comprobar mediante un canal de comunicación ajeno al
correo electrónico, si el número de cuenta corresponde al destinatario de la
factura" (https://www.incibe.es/empresas/te-ayudamos/fraude-email-comprometido,
leída el 25-10-2026; la página no lleva fecha).

Ninguna regla de forma ni de contenido puede verlo, porque mirada sola cada
factura está bien. Solo se ve poniendo juntas las de un mismo emisor, que es
lo que hace un lote: este módulo junta, por el NIF de quien emite, las cuentas
de cobro (BT-84) de sus facturas, y avisa cuando no son las mismas.

Por qué aviso y no error
------------------------
Porque cobrar en dos cuentas es perfectamente legal y bastante corriente: un
banco para unos clientes y otro para otros, o una cuenta nueva de verdad. El
aviso no dice que haya fraude, dice que las cuentas cambian y dónde, para que
quien va a pagar lo confirme antes de pagar. Con código de la casa, porque
ninguna norma de facturación lo pide.

Lo que no se mira
-----------------
EDIFACT no tiene mapa para la instrucción de pago (`SIN_MAPA` en
`sintaxis.SINTAXIS_EDIFACT`), así que sus facturas no entran. Tampoco las que
no dicen quién las emite: sin NIF no hay con qué juntarlas. Y una factura que
no pide transferencia, sin cuenta de cobro, no cuenta para nada: no ha
cambiado de cuenta, es que no da ninguna.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from validador import codigo_unico
from validador.formato import FACTURAE
from validador.incidencias import AVISO, Incidencia
from validador.sintaxis import SIN_MAPA, SINTAXIS, buscar, texto

__all__ = ["Cobro", "extraer_de", "reglas", "reglas_de_lote"]

# Cuántas facturas se nombran por cuenta en el mensaje. Con un lote de
# quinientas, nombrarlas todas taparía lo único que importa, que es la cuenta
# que sale en pocas.
_NOMBRADAS = 3


@dataclass(frozen=True)
class Cobro:
    """Una factura: quién la emite y en qué cuentas pide que se le pague."""

    emisor: str
    factura: str
    cuentas: tuple[str, ...]


def _limpia(cuenta: str) -> str:
    """La misma cuenta escrita con espacios o sin ellos es la misma cuenta.

    El IBAN se escribe en grupos de cuatro en papel y de corrido en el
    fichero. Sin esto, el aviso saltaría por la manera de escribir la cuenta y
    no por la cuenta.
    """
    return re.sub(r"\s+", "", cuenta).upper()


def _cuentas(factura, sintaxis) -> tuple[str, ...]:
    """Las cuentas de cobro de una factura, sin repetir y en su orden."""
    vistas: list[str] = []
    for pago in buscar(factura, sintaxis.pagos, sintaxis.espacios):
        for cuenta in buscar(pago, sintaxis.pago_cuenta, sintaxis.espacios):
            escrita = texto(cuenta, sintaxis.cuenta_id, sintaxis)
            if escrita and _limpia(escrita) not in vistas:
                vistas.append(_limpia(escrita))
    return tuple(vistas)


def extraer_de(raiz, deteccion) -> list[Cobro]:
    """Cada factura del documento, con su emisor y sus cuentas de cobro.

    El emisor es el mismo NIF que compone el código único, leído por el mismo
    camino (`codigo_unico.extraer_de`), para que una factura no pueda ser de
    un emisor para el código y de otro para las cuentas. Si el código no se
    puede componer, de eso ya se queja CU-00, y aquí no se junta.
    """
    if raiz is None or not deteccion:
        return []
    sintaxis = SINTAXIS.get(deteccion.familia or "")
    if sintaxis is None or SIN_MAPA in (sintaxis.pagos, sintaxis.pago_cuenta,
                                        sintaxis.cuenta_id):
        return []
    codigos = codigo_unico.extraer_de(raiz, deteccion)
    emisor = codigos[0].nif_emisor if codigos else ""
    if not emisor:
        return []
    if deteccion.familia != FACTURAE:
        return [Cobro(emisor, codigos[0].numero_completo, _cuentas(raiz, sintaxis))]
    # Un Facturae son varias facturas, cada una con su instrucción de pago, y
    # el mapa lee los pagos desde cada `<Invoice>`. El número se compone aquí
    # y no se toma de `codigos`, que se salta las facturas sin fecha: las dos
    # listas no irían a la par.
    cobros = []
    for factura in raiz.xpath("//*[local-name()='Invoices']/*[local-name()='Invoice']"):
        cabecera = "./*[local-name()='InvoiceHeader']/*[local-name()='{}']"
        numero = (factura.xpath(f"string({cabecera.format('InvoiceSeriesCode')})").strip()
                  + factura.xpath(f"string({cabecera.format('InvoiceNumber')})").strip())
        cobros.append(Cobro(emisor, numero or "(sin número)", _cuentas(factura, sintaxis)))
    return cobros


def _facturas(cuantas: int) -> str:
    return "1 factura" if cuantas == 1 else f"{cuantas} facturas"


def _quienes(usos: list[tuple[str, str | None]]) -> str:
    """Las facturas que piden una cuenta, con su fichero si se sabe."""
    nombradas = [f"{factura} ({fichero})" if fichero else factura
                 for factura, fichero in usos[:_NOMBRADAS]]
    if len(usos) == 1:
        return f"la factura {nombradas[0]}"
    lista = ", ".join(nombradas[:-1]) + " y " + nombradas[-1]
    if len(usos) <= _NOMBRADAS:
        return f"las facturas {lista}"
    return f"{len(usos)} facturas, entre ellas {lista}"


def _cuentas_distintas(emisor: str, suyas: list[tuple[Cobro, str | None]]) -> Incidencia:
    uso: dict[str, list[tuple[str, str | None]]] = {}
    for cobro, fichero in suyas:
        for cuenta in cobro.cuentas:
            uso.setdefault(cuenta, []).append((cobro.factura, fichero))
    # De la que más sale a la que menos: la que sale en pocas es la que hay
    # que mirar, y queda al final, donde se lee la última. A igualdad, en el
    # orden en que aparecen.
    orden = sorted(uso, key=lambda cuenta: -len(uso[cuenta]))
    return Incidencia(
        "CUENTA-DISTINTA",
        AVISO,
        f"Las facturas del emisor {emisor} piden el pago en {len(uso)} cuentas "
        "distintas: "
        + "; ".join(f"{cuenta}, {_quienes(uso[cuenta])}" for cuenta in orden)
        + ". Puede ser legítimo, si cobra en más de una. También es la señal "
        "del fraude del cambio de cuenta, en el que alguien se hace pasar por "
        "el proveedor y pide el pago en otra. Antes de pagar en una cuenta que "
        "no se conoce, conviene confirmarla con el emisor por un canal que no "
        "sea el correo electrónico, como aconseja INCIBE.",
        campo="Cuenta de cobro del vendedor (BT-84)",
        # Sin nombres de fichero a propósito: es lo que compara el lote para no
        # repetir lo que ya dijo un fichero sobre sus propias facturas, y el
        # mismo Facturae mirado solo no sabe cómo se llama.
        encontrado=" · ".join(f"{cuenta} en {_facturas(len(uso[cuenta]))}"
                              for cuenta in orden),
        ficheros=tuple(dict.fromkeys(fichero for _, fichero in suyas if fichero)),
    )


def reglas_de_lote(cobros: list[Cobro],
                   procedencias: list[str] | None = None) -> list[Incidencia]:
    """CUENTA-DISTINTA: un emisor cuyas facturas no piden el pago en las mismas cuentas.

    Se compara el juego de cuentas de cada factura, no cada cuenta suelta:
    una factura que ofrece dos cuentas, y otra igual con las mismas dos, no
    han cambiado nada. Las facturas sin cuenta no cuentan.
    """
    por_emisor: dict[str, list[tuple[Cobro, str | None]]] = {}
    for indice, cobro in enumerate(cobros):
        if cobro.cuentas:
            por_emisor.setdefault(cobro.emisor, []).append(
                (cobro, procedencias[indice] if procedencias else None))
    return [
        _cuentas_distintas(emisor, suyas)
        for emisor, suyas in por_emisor.items()
        if len({frozenset(cobro.cuentas) for cobro, _ in suyas}) > 1
    ]


def reglas(raiz, deteccion) -> list[Incidencia]:
    """Lo mismo dentro de un fichero, que solo en Facturae pueden ser varias
    facturas. Un UBL o un CII es una sola, con un solo juego de cuentas, y no
    puede no cuadrar consigo mismo: leerlo sería trabajo para nada en cada
    fichero de un lote."""
    if not deteccion or deteccion.familia != FACTURAE:
        return []
    return reglas_de_lote(extraer_de(raiz, deteccion))
