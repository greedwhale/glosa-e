# -*- coding: utf-8 -*-
"""Qué le pasa a una factura cuando se copia a la solución pública.

Qué es una copia fiel
---------------------
Quien no emita por la solución pública tiene que mandarle una **copia fiel** de
cada factura, en UBL, a la vez que la emite (RD 238/2026, y el artículo 4 del
proyecto de orden). La factura original sigue siendo la que es —Facturae, CII,
EDIFACT—; lo que viaja a la AEAT es una copia escrita en otra sintaxis.

Esa traducción no la publica nadie. Preguntada por escrito si pensaba publicar
la correspondencia entre las sintaxis del artículo 7.1 y los campos del anexo I,
la AEAT contestó el **17-09-2026** que no: «cae en la responsabilidad de las
plataformas privadas, o en su caso, de la definición por parte del Ministerio de
Economía que regula la interconexión». Así que cada plataforma escribe la suya,
y esta es la de aquí, con sus porqués a la vista.

La respuesta trae además la regla que decide el tono de todo este módulo: un
concepto del original que no tenga equivalente **se puede omitir o llevar en una
extensión**, y «si el concepto del original no es equivalente, no se realizará
la validación del dato». Es decir: que a la copia le falte algo del original no
es un fallo de nadie. Por eso todo lo que sale de aquí es **NOTA**.

Lo que no es esto
-----------------
No es un conversor: aquí no se escribe ninguna copia. No valida la copia, que
es otro documento y se mide con sus propias reglas —las `SPFE-`—. Y no adivina
dónde se escriben en Facturae los campos españoles del anexo: el anexo los
describe en UBL, y el 10-09-2026 la AEAT anunció que cambian.

Lo que sí hace es decir tres cosas distintas sobre la factura que se está
mirando, y la tercera es la que nadie está diciendo:

1. **Lo que llega igual.** La mayor parte.
2. **Lo que no tiene sitio** y habrá que omitir o meter en una extensión.
3. **Lo que llega con otro número.** Los totales de Facturae no son los
   europeos: `InvoiceTotal` **resta las retenciones** y `TotalTaxOutputs`
   **suma el recargo de equivalencia**, y está en el esquema del formato, no en
   una interpretación. Quien copie campo a campo pondrá esos importes en
   `BT-112` y `BT-110` y serán otros. Medido el 20-09-2026 sobre las facturas
   de terceros que hay aquí: **6 de 14 llevan retenciones o recargo**.

De dónde sale cada fila
-----------------------
De las fórmulas que el propio esquema de Facturae escribe en su documentación y
que `facturae.py` ya comprueba una a una —`FE-TOTAL`, `FE-PENDIENTE`,
`FE-EJECUTAR`—, y de dónde pone el anexo I cada importe español. Lo que no se
sabe va marcado `POR_DECIDIR` y se dice así, en vez de colocarlo donde suene
bien.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from validador.formato import FACTURAE, Deteccion
from validador.incidencias import NOTA, Incidencia
from validador.sintaxis import a_decimal

# Qué le pasa a un concepto al copiarse. Son cuatro y no tres porque «no se
# sabe» es un estado distinto de «no tiene sitio»: el primero se resuelve
# leyendo el anexo nuevo cuando salga, el segundo no se resuelve.
IGUAL = "llega igual"
APARTE = "llega, pero en la extensión española"
CAMBIA = "llega con otro número"
SIN_SITIO = "no tiene sitio"
POR_DECIDIR = "no se sabe todavía"


@dataclass(frozen=True)
class Correspondencia:
    """Una fila de la tabla: de dónde sale, adónde va y qué le pasa."""

    concepto: str
    facturae: str  # el elemento de Facturae, tal y como lo llama su esquema
    destino: str  # el término europeo o el campo del anexo
    efecto: str
    porque: str


# La primera familia: los importes. Se empieza por aquí porque es donde copiar
# campo a campo no omite un dato, sino que **cambia una cifra**, que es peor:
# un hueco se ve y un número equivocado no.
CORRESPONDENCIAS: tuple[Correspondencia, ...] = (
    Correspondencia(
        "base antes de impuestos", "TotalGrossAmountBeforeTaxes", "BT-109", IGUAL,
        "las dos son el importe bruto menos descuentos más cargos generales",
    ),
    Correspondencia(
        "cuotas repercutidas", "TotalTaxOutputs", "BT-110", CAMBIA,
        "el esquema de Facturae dice «sumatorio de todas las cuotas y recargos "
        "repercutidos»: lleva dentro el recargo de equivalencia, que en el "
        "anexo va en su propio grupo y no en la cuota de IVA",
    ),
    Correspondencia(
        "total de la factura", "InvoiceTotal", "BT-112", CAMBIA,
        "el esquema lo define como base más repercutidos **menos retenidos**, y "
        "BT-112 es base más cuotas: la retención no es un impuesto de la "
        "factura para la norma europea",
    ),
    Correspondencia(
        "anticipos", "TotalPaymentsOnAccount", "BT-113", IGUAL,
        "lo ya pagado antes de emitir, que la norma también tiene",
    ),
    Correspondencia(
        "total a pagar", "TotalExecutableAmount", "BT-115", POR_DECIDIR,
        "es el que más se le parece —descuenta retenciones y suma suplidos y "
        "gastos financieros—, pero el anexo manda sumar los importes de "
        "terceros «junto con» el total con IVA y esa cuenta no se puede "
        "comprobar todavía: es la misma duda de SPFE-TOTAL-A-PAGAR",
    ),
    Correspondencia(
        "retenciones de impuestos", "TotalTaxesWithheld", "anexo I: suma de retenciones",
        APARTE,
        "la norma europea no tiene término para la retención; el anexo sí, con "
        "su base, su tipo y su concepto",
    ),
    Correspondencia(
        "importes retenidos", "AmountsWithheld", "anexo I: retención aplicada",
        POR_DECIDIR,
        "Facturae distingue la retención de impuestos de otros importes "
        "retenidos —la retención de garantía de una obra, por ejemplo— y el "
        "anexo describe un solo grupo de retención: si el segundo cabe ahí no "
        "lo dice nadie",
    ),
    Correspondencia(
        "recargo de equivalencia", "EquivalenceSurchargeAmount",
        "anexo I: recargo de equivalencia", APARTE,
        "el anexo le da grupo propio, con base, tipo y cuota, fuera de la cuota "
        "de IVA",
    ),
    Correspondencia(
        "suplidos", "TotalReimbursableExpenses", "BG-34 (BT-179 y BT-180)", POR_DECIDIR,
        "los importes de terceros son términos de la edición de 2026 de la "
        "norma, y el anexo de abril no les da ruta: hasta que salga el texto "
        "nuevo no se sabe dónde se escriben",
    ),
    Correspondencia(
        "gastos financieros", "TotalFinancialExpenses", "", SIN_SITIO,
        "ni la norma europea ni el anexo tienen dónde ponerlos",
    ),
    Correspondencia(
        "subvenciones", "Subsidies", "", SIN_SITIO,
        "restan del total a pagar en Facturae y no tienen término europeo; "
        "quien copie tendrá que dejarlas fuera o inventarse una extensión",
    ),
)

# Lo que la tabla tiene que cubrir para que las reglas de abajo no hablen de
# nada. Es el cepo de este módulo: si alguien quita una fila y deja la regla,
# el paquete no se monta. Un comentario pidiendo memoria no lo evitaría.
_LO_QUE_SE_MIRA = (
    "TotalTaxOutputs", "InvoiceTotal", "TotalTaxesWithheld",
    "EquivalenceSurchargeAmount", "TotalReimbursableExpenses",
    "TotalFinancialExpenses",
)


class TablaIncompleta(Exception):
    """La tabla ya no cubre lo que las reglas dicen mirar."""


def _comprobar_la_tabla() -> None:
    escritos = {fila.facturae for fila in CORRESPONDENCIAS}
    faltan = [nombre for nombre in _LO_QUE_SE_MIRA if nombre not in escritos]
    if faltan:
        raise TablaIncompleta(
            "las reglas de la copia fiel miran campos que ya no están en la "
            "tabla de correspondencias: " + ", ".join(faltan) + ". O vuelve la "
            "fila, o se quita la regla: una queja sin su porqué escrito no sale "
            "de aquí."
        )


_comprobar_la_tabla()


def _hijos(nodo, *nombres: str) -> list:
    actuales = [nodo]
    for nombre in nombres:
        siguientes = []
        for uno in actuales:
            siguientes.extend(uno.xpath(f"./*[local-name()='{nombre}']"))
        actuales = siguientes
    return actuales


def _numero(nodo, *nombres: str) -> Decimal:
    for encontrado in _hijos(nodo, *nombres):
        cantidad = a_decimal((encontrado.text or "").strip())
        if cantidad is not None:
            return cantidad
    return Decimal(0)


def _suma_profunda(nodo, nombre: str) -> Decimal:
    """Lo que suman todos los elementos con ese nombre, estén donde estén.

    El recargo de equivalencia se declara por tipo impositivo, así que hay uno
    por cada línea del desglose y el documento no trae su total.
    """
    total = Decimal(0)
    for encontrado in nodo.xpath(f".//*[local-name()='{nombre}']"):
        cantidad = a_decimal(" ".join(encontrado.itertext()).strip())
        if cantidad is not None:
            total += cantidad
    return total


def _fmt(cantidad: Decimal) -> str:
    return f"{cantidad:.2f}"


def _de_una_factura(factura, etiqueta: str) -> list[Incidencia]:
    totales = _hijos(factura, "InvoiceTotals")
    if not totales:
        return []
    totales = totales[0]
    base = _numero(totales, "TotalGrossAmountBeforeTaxes")
    repercutido = _numero(totales, "TotalTaxOutputs")
    retenido = _numero(totales, "TotalTaxesWithheld")
    total = _numero(totales, "InvoiceTotal")
    suplidos = _numero(totales, "TotalReimbursableExpenses")
    financieros = _numero(totales, "TotalFinancialExpenses")
    recargo = _suma_profunda(factura, "EquivalenceSurchargeAmount")

    incidencias = []
    if recargo:
        # BT-110 es la suma de las cuotas de IVA y nada más. El recargo tiene
        # grupo propio en el anexo, así que sale de aquí.
        incidencias.append(
            Incidencia(
                "COPIA-CUOTA",
                NOTA,
                "La cuota que lleva esta factura no es la que iría en la copia. "
                "El total de impuestos repercutidos de Facturae suma también el "
                "recargo de equivalencia, y en la copia el recargo va en su "
                "propio grupo, fuera de la cuota de IVA.",
                # Sin flechas ni nada fuera del latín de siempre: esto se
                # imprime en consolas que todavía hablan cp1252, y un carácter
                # que no esté ahí no sale mal: revienta el informe entero.
                campo=f"{etiqueta}Total de impuestos repercutidos (BT-110 en la copia)",
                # Con «en la copia» y «en esta factura» pegados al número: el
                # informe rotula estas dos líneas «Debería ser» y «Tiene», y
                # sin el añadido se leería que la factura está mal, que es
                # justo lo contrario de lo que dice la nota.
                esperado=f"{_fmt(repercutido - recargo)} en la copia, sin el recargo",
                encontrado=f"{_fmt(repercutido)} en esta factura, "
                           f"con {_fmt(recargo)} de recargo dentro",
            )
        )
    if retenido or recargo:
        # BT-112 es base más cuotas de IVA. Ni la retención se resta —no es un
        # impuesto de la factura para la norma— ni el recargo se suma ahí.
        europeo = base + repercutido - recargo
        detalle = f"{_fmt(total)} en esta factura"
        if retenido:
            detalle += f", que ya tiene restados {_fmt(retenido)} de retenciones"
        incidencias.append(
            Incidencia(
                "COPIA-TOTAL",
                NOTA,
                "El total de esta factura no es el que iría en la copia. El "
                "total de Facturae resta las retenciones, y el total con "
                "impuestos de la copia es la base más las cuotas de IVA: la "
                "retención viaja aparte, en la extensión española.",
                campo=f"{etiqueta}Total factura (BT-112 en la copia)",
                esperado=f"{_fmt(europeo)} en la copia: base más cuotas de IVA",
                encontrado=detalle,
            )
        )
    if suplidos:
        incidencias.append(
            Incidencia(
                "COPIA-SUPLIDO",
                NOTA,
                "Esta factura lleva suplidos, y no se sabe dónde se escriben en "
                "la copia. Son importes de terceros: términos de la edición de "
                "2026 de la norma europea, y el anexo I de abril no les da "
                "ruta. El 10-09-2026 la AEAT dijo que el anexo nuevo los usa, "
                "pero ese texto no está publicado.",
                campo=f"{etiqueta}Total de suplidos",
                encontrado=_fmt(suplidos),
            )
        )
    if financieros:
        incidencias.append(
            Incidencia(
                "COPIA-SIN-SITIO",
                NOTA,
                "Esta factura lleva gastos financieros y en la copia no hay "
                "dónde ponerlos: ni la norma europea ni el anexo tienen un "
                "campo para eso. Se pueden omitir o llevar en una extensión, "
                "que es lo que contestó la AEAT el 17-09-2026 para los "
                "conceptos sin equivalente.",
                campo=f"{etiqueta}Total de gastos financieros",
                encontrado=_fmt(financieros),
            )
        )
    return incidencias


def reglas(raiz, deteccion: Deteccion) -> list[Incidencia]:
    """Lo que le pasaría a este documento al copiarlo a la solución pública.

    Solo sobre Facturae, que es donde la copia cambia números. En CII y en
    EDIFACT la correspondencia con la norma la publica CEN y los importes son
    los mismos; en UBL no hay nada que copiar.
    """
    if raiz is None or not deteccion or deteccion.familia != FACTURAE:
        return []
    if raiz.xpath("local-name()") != "Facturae":
        internos = raiz.xpath("//*[local-name()='Facturae']")
        if not internos:
            return []
        raiz = internos[0]
    facturas = _hijos(raiz, "Invoices", "Invoice")
    incidencias = []
    for numero, factura in enumerate(facturas, 1):
        etiqueta = f"Factura {numero}: " if len(facturas) > 1 else ""
        incidencias.extend(_de_una_factura(factura, etiqueta))
    return incidencias
