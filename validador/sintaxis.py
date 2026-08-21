"""Dónde vive cada campo de EN 16931 en UBL y en CII.

La norma define un modelo semántico —los campos BT-1, BT-109, BT-117…— y
después cada sintaxis lo escribe a su manera. Este módulo es el diccionario
entre las dos: solo rutas XPath y las utilidades para leerlas.

Estaba dentro de `en16931`, pero las reglas de IVA también lo necesitan y no
tiene sentido que un módulo dependa del otro solo para consultar un mapa.
Añadir una sintaxis nueva debería ser rellenar otra `Sintaxis` sin tocar
ninguna regla.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

NS_UBL = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}

NS_CII = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": (
        "urn:un:unece:uncefact:data:standard:"
        "ReusableAggregateBusinessInformationEntity:100"
    ),
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}

# La norma trabaja con importes redondeados a dos decimales, así que una
# diferencia de un céntimo no es un error: es el redondeo permitido.
TOLERANCIA = Decimal("0.01")


@dataclass(frozen=True)
class Sintaxis:
    """El mapa de una sintaxis. Solo rutas: aquí no hay lógica."""

    nombre: str
    espacios: dict[str, str]
    nombre_perfil: str  # cómo se llama el campo del perfil en esta sintaxis

    perfil: str
    numero: str
    fecha: str
    tipo: str
    moneda: str

    vendedor_nombre: str
    vendedor_direccion: str
    vendedor_pais: str
    comprador_nombre: str
    comprador_direccion: str
    comprador_pais: str

    lineas: str
    linea_id: str  # relativa a una línea
    linea_importe: str  # relativa a una línea
    linea_categoria: str  # relativa a una línea: BT-151
    linea_tipo: str  # relativa a una línea: BT-152

    # El desglose por tipo de IVA (BG-23), que es donde se apoya casi toda la
    # comprobación del impuesto.
    desglose: str
    desglose_base: str  # BT-116, relativa a un grupo
    desglose_cuota: str  # BT-117
    desglose_categoria: str  # BT-118
    desglose_tipo: str  # BT-119
    desglose_motivo: str  # BT-120
    desglose_motivo_codigo: str  # BT-121

    # Descuentos y cargos a nivel de documento (BG-20 y BG-21), que entran en
    # la base de su categoría igual que las líneas.
    cargos: str
    cargo_es_cargo: str  # relativa: true si suma, false si resta
    cargo_importe: str
    cargo_categoria: str
    cargo_tipo: str

    suma_lineas: str
    base: str
    con_impuestos: str
    a_pagar: str
    descuentos_total: str
    cargos_total: str
    anticipos: str
    redondeo: str
    impuestos: str


_TOTAL_UBL = "./cac:LegalMonetaryTotal"
_VENDEDOR_UBL = "./cac:AccountingSupplierParty/cac:Party"
_COMPRADOR_UBL = "./cac:AccountingCustomerParty/cac:Party"

# UBL escribe dos elementos distintos para lo mismo según el documento sea una
# factura o un abono: `InvoiceTypeCode` frente a `CreditNoteTypeCode`, e
# `InvoiceLine` frente a `CreditNoteLine`. Todo lo demás —partes, totales,
# desglose de IVA— se llama igual en los dos.
#
# La unión XPath («a|b») coge el que haya, que es más seguro que mantener dos
# mapas y elegir uno: si se elige mal, las reglas leen el documento
# equivocado. Con el mapa de la factura a secas, un abono correcto salía con
# BR-04 y BR-16 inventados y, al no encontrársele las líneas, enmudecían de
# golpe BR-24, BR-CO-10 y todo el IVA. Acusado en falso y sin comprobar.
_TIPO_UBL = "./cbc:InvoiceTypeCode|./cbc:CreditNoteTypeCode"
_LINEAS_UBL = "./cac:InvoiceLine|./cac:CreditNoteLine"

SINTAXIS_UBL = Sintaxis(
    nombre="UBL",
    espacios=NS_UBL,
    nombre_perfil="CustomizationID",
    perfil="./cbc:CustomizationID",
    numero="./cbc:ID",
    fecha="./cbc:IssueDate",
    tipo=_TIPO_UBL,
    moneda="./cbc:DocumentCurrencyCode",
    vendedor_nombre=f"{_VENDEDOR_UBL}/cac:PartyLegalEntity/cbc:RegistrationName",
    vendedor_direccion=f"{_VENDEDOR_UBL}/cac:PostalAddress",
    vendedor_pais=(
        f"{_VENDEDOR_UBL}/cac:PostalAddress/cac:Country/cbc:IdentificationCode"
    ),
    comprador_nombre=f"{_COMPRADOR_UBL}/cac:PartyLegalEntity/cbc:RegistrationName",
    comprador_direccion=f"{_COMPRADOR_UBL}/cac:PostalAddress",
    comprador_pais=(
        f"{_COMPRADOR_UBL}/cac:PostalAddress/cac:Country/cbc:IdentificationCode"
    ),
    lineas=_LINEAS_UBL,
    linea_id="./cbc:ID",
    linea_importe="./cbc:LineExtensionAmount",
    linea_categoria="./cac:Item/cac:ClassifiedTaxCategory/cbc:ID",
    linea_tipo="./cac:Item/cac:ClassifiedTaxCategory/cbc:Percent",
    desglose="./cac:TaxTotal/cac:TaxSubtotal",
    desglose_base="./cbc:TaxableAmount",
    desglose_cuota="./cbc:TaxAmount",
    desglose_categoria="./cac:TaxCategory/cbc:ID",
    desglose_tipo="./cac:TaxCategory/cbc:Percent",
    desglose_motivo="./cac:TaxCategory/cbc:TaxExemptionReason",
    desglose_motivo_codigo="./cac:TaxCategory/cbc:TaxExemptionReasonCode",
    cargos="./cac:AllowanceCharge",
    cargo_es_cargo="./cbc:ChargeIndicator",
    cargo_importe="./cbc:Amount",
    cargo_categoria="./cac:TaxCategory/cbc:ID",
    cargo_tipo="./cac:TaxCategory/cbc:Percent",
    suma_lineas=f"{_TOTAL_UBL}/cbc:LineExtensionAmount",
    base=f"{_TOTAL_UBL}/cbc:TaxExclusiveAmount",
    con_impuestos=f"{_TOTAL_UBL}/cbc:TaxInclusiveAmount",
    a_pagar=f"{_TOTAL_UBL}/cbc:PayableAmount",
    descuentos_total=f"{_TOTAL_UBL}/cbc:AllowanceTotalAmount",
    cargos_total=f"{_TOTAL_UBL}/cbc:ChargeTotalAmount",
    anticipos=f"{_TOTAL_UBL}/cbc:PrepaidAmount",
    redondeo=f"{_TOTAL_UBL}/cbc:PayableRoundingAmount",
    impuestos="./cac:TaxTotal/cbc:TaxAmount",
)

# En CII casi todo cuelga de SupplyChainTradeTransaction, repartido en tres
# bloques: lo pactado (Agreement), la entrega (Delivery) y el cobro
# (Settlement). Los totales viven en el Settlement, y la cabecera —número,
# fecha y tipo— va aparte, en ExchangedDocument.
_TRANSACCION = "./rsm:SupplyChainTradeTransaction"
_ACUERDO = f"{_TRANSACCION}/ram:ApplicableHeaderTradeAgreement"
_COBRO = f"{_TRANSACCION}/ram:ApplicableHeaderTradeSettlement"
_SUMARIO = f"{_COBRO}/ram:SpecifiedTradeSettlementHeaderMonetarySummation"
_CABECERA = "./rsm:ExchangedDocument"

SINTAXIS_CII = Sintaxis(
    nombre="CII",
    espacios=NS_CII,
    nombre_perfil="GuidelineSpecifiedDocumentContextParameter",
    perfil=(
        "./rsm:ExchangedDocumentContext"
        "/ram:GuidelineSpecifiedDocumentContextParameter/ram:ID"
    ),
    numero=f"{_CABECERA}/ram:ID",
    fecha=f"{_CABECERA}/ram:IssueDateTime/udt:DateTimeString",
    tipo=f"{_CABECERA}/ram:TypeCode",
    moneda=f"{_COBRO}/ram:InvoiceCurrencyCode",
    vendedor_nombre=f"{_ACUERDO}/ram:SellerTradeParty/ram:Name",
    vendedor_direccion=f"{_ACUERDO}/ram:SellerTradeParty/ram:PostalTradeAddress",
    vendedor_pais=(
        f"{_ACUERDO}/ram:SellerTradeParty/ram:PostalTradeAddress/ram:CountryID"
    ),
    comprador_nombre=f"{_ACUERDO}/ram:BuyerTradeParty/ram:Name",
    comprador_direccion=f"{_ACUERDO}/ram:BuyerTradeParty/ram:PostalTradeAddress",
    comprador_pais=(
        f"{_ACUERDO}/ram:BuyerTradeParty/ram:PostalTradeAddress/ram:CountryID"
    ),
    lineas=f"{_TRANSACCION}/ram:IncludedSupplyChainTradeLineItem",
    linea_id="./ram:AssociatedDocumentLineDocument/ram:LineID",
    linea_importe=(
        "./ram:SpecifiedLineTradeSettlement"
        "/ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount"
    ),
    linea_categoria=(
        "./ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax"
        "/ram:CategoryCode"
    ),
    linea_tipo=(
        "./ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax"
        "/ram:RateApplicablePercent"
    ),
    desglose=f"{_COBRO}/ram:ApplicableTradeTax",
    desglose_base="./ram:BasisAmount",
    desglose_cuota="./ram:CalculatedAmount",
    desglose_categoria="./ram:CategoryCode",
    desglose_tipo="./ram:RateApplicablePercent",
    desglose_motivo="./ram:ExemptionReason",
    desglose_motivo_codigo="./ram:ExemptionReasonCode",
    cargos=f"{_COBRO}/ram:SpecifiedTradeAllowanceCharge",
    cargo_es_cargo="./ram:ChargeIndicator/udt:Indicator",
    cargo_importe="./ram:ActualAmount",
    cargo_categoria="./ram:CategoryTradeTax/ram:CategoryCode",
    cargo_tipo="./ram:CategoryTradeTax/ram:RateApplicablePercent",
    suma_lineas=f"{_SUMARIO}/ram:LineTotalAmount",
    base=f"{_SUMARIO}/ram:TaxBasisTotalAmount",
    con_impuestos=f"{_SUMARIO}/ram:GrandTotalAmount",
    a_pagar=f"{_SUMARIO}/ram:DuePayableAmount",
    descuentos_total=f"{_SUMARIO}/ram:AllowanceTotalAmount",
    cargos_total=f"{_SUMARIO}/ram:ChargeTotalAmount",
    anticipos=f"{_SUMARIO}/ram:TotalPrepaidAmount",
    redondeo=f"{_SUMARIO}/ram:RoundingAmount",
    impuestos=f"{_SUMARIO}/ram:TaxTotalAmount",
)

# Nombres de familia sin importar `formato`, que no hace falta aquí.
SINTAXIS: dict[str, Sintaxis] = {"UBL": SINTAXIS_UBL, "CII": SINTAXIS_CII}


# --- Lectura ---------------------------------------------------------------


def texto(nodo, ruta: str, sintaxis: Sintaxis) -> str | None:
    encontrados = nodo.xpath(ruta, namespaces=sintaxis.espacios)
    if not encontrados:
        return None
    valor = encontrados[0]
    crudo = valor if isinstance(valor, str) else (valor.text or "")
    crudo = crudo.strip()
    return crudo or None


def a_decimal(bruto: str | None) -> Decimal | None:
    if bruto is None:
        return None
    try:
        return Decimal(bruto.strip())
    except InvalidOperation:
        return None


def importe(nodo, ruta: str, sintaxis: Sintaxis) -> Decimal | None:
    """Lee un importe como Decimal. Devuelve None si falta o no es un número."""
    return a_decimal(texto(nodo, ruta, sintaxis))


def importe_en_moneda(
    nodo, ruta: str, sintaxis: Sintaxis, moneda: str | None
) -> Decimal | None:
    """El importe declarado en la moneda de la factura.

    Tanto UBL como CII permiten declarar el total de impuestos dos veces: una
    en la moneda de la factura (BT-110) y otra en la moneda de contabilidad
    (BT-111), distinguidas por el atributo `currencyID`. Coger el primero que
    aparezca es coger uno al azar: si el documento las trae en el otro orden,
    el cuadre falla por una factura que está bien.
    """
    encontrados = nodo.xpath(ruta, namespaces=sintaxis.espacios)
    if not encontrados:
        return None
    elegido = encontrados[0]
    if moneda:
        for candidato in encontrados:
            if candidato.get("currencyID") == moneda:
                elegido = candidato
                break
    return a_decimal(elegido.text)


def cuadra(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= TOLERANCIA


def fmt(valor: Decimal | None) -> str:
    return "(vacío)" if valor is None else f"{valor:.2f}"


def fmt_tipo(valor: Decimal | None) -> str:
    """Un tipo de IVA, sin ceros de adorno: 21 y no 21.00."""
    if valor is None:
        return "(sin tipo)"
    normalizado = valor.normalize()
    if normalizado == normalizado.to_integral_value():
        normalizado = normalizado.quantize(Decimal(1))
    return f"{normalizado}%"
