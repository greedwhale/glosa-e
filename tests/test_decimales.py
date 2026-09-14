# -*- coding: utf-8 -*-
"""Cuántos decimales lleva cada importe: dos, como mucho (BR-DEC).

De estas veintiuna no hay ni una prueba oficial, así que las de aquí son todas
las que tienen. Cada importe se monta suelto en cada sintaxis con tres
decimales y con dos, y lo que se comprueba es que salte **esa** regla y
ninguna otra: un campo del mapa apuntando al importe de al lado se ve aquí y
no en un «salta algo».

Lo que se decide en cada sintaxis —contar lo escrito o mirar el valor— se
prueba en `test_norma_oficial.py` contra la expresión oficial; aquí, lo que
eso produce.
"""
from __future__ import annotations

import pytest
from lxml import etree

from tests.test_modelo import cii, edi, facturae, ubl
from validador import decimales, en16931
from validador.codigos import codigos_del_paquete
from validador.incidencias import ERROR
from validador.sintaxis import (
    SIN_MAPA,
    SINTAXIS_CII,
    SINTAXIS_EDIFACT,
    SINTAXIS_FACTURAE,
    SINTAXIS_UBL,
)

TODAS = frozenset({
    "BR-DEC-01", "BR-DEC-02", "BR-DEC-05", "BR-DEC-06", "BR-DEC-09",
    "BR-DEC-10", "BR-DEC-11", "BR-DEC-12", "BR-DEC-13", "BR-DEC-14",
    "BR-DEC-15", "BR-DEC-16", "BR-DEC-17", "BR-DEC-18", "BR-DEC-19",
    "BR-DEC-20", "BR-DEC-23", "BR-DEC-24", "BR-DEC-25", "BR-DEC-27",
    "BR-DEC-28",
})


def salen(raiz, sintaxis) -> set[str]:
    return {i.codigo for i in decimales.reglas(raiz, sintaxis)}


def la(raiz, sintaxis, codigo: str):
    return next(i for i in decimales.reglas(raiz, sintaxis) if i.codigo == codigo)


# --- Dónde vive cada importe en cada sintaxis ---------------------------------
#
# Una plantilla por regla, con un hueco para el importe. Lo demás que lleva es
# lo mínimo para que el importe sea el que es: la marca de descuento o de
# cargo, la línea, la moneda.

_AJUSTE_UBL = "<cbc:ChargeIndicator>{}</cbc:ChargeIndicator>{}"
_TOTAL_UBL = "<cac:LegalMonetaryTotal>{}</cac:LegalMonetaryTotal>"
_LINEA_UBL = "<cac:InvoiceLine><cbc:ID>1</cbc:ID>{}</cac:InvoiceLine>"


def _ajuste_ubl(cargo: bool, dentro: str) -> str:
    marca = "true" if cargo else "false"
    return f"<cac:AllowanceCharge>{_AJUSTE_UBL.format(marca, dentro)}</cac:AllowanceCharge>"


UBL = {
    "BR-DEC-01": _ajuste_ubl(False, '<cbc:Amount currencyID="EUR">{}</cbc:Amount>'),
    "BR-DEC-02": _ajuste_ubl(False, '<cbc:BaseAmount currencyID="EUR">{}</cbc:BaseAmount>'),
    "BR-DEC-05": _ajuste_ubl(True, '<cbc:Amount currencyID="EUR">{}</cbc:Amount>'),
    "BR-DEC-06": _ajuste_ubl(True, '<cbc:BaseAmount currencyID="EUR">{}</cbc:BaseAmount>'),
    "BR-DEC-09": _TOTAL_UBL.format("<cbc:LineExtensionAmount>{}</cbc:LineExtensionAmount>"),
    "BR-DEC-10": _TOTAL_UBL.format("<cbc:AllowanceTotalAmount>{}</cbc:AllowanceTotalAmount>"),
    "BR-DEC-11": _TOTAL_UBL.format("<cbc:ChargeTotalAmount>{}</cbc:ChargeTotalAmount>"),
    "BR-DEC-12": _TOTAL_UBL.format("<cbc:TaxExclusiveAmount>{}</cbc:TaxExclusiveAmount>"),
    "BR-DEC-13": (
        "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
        '<cac:TaxTotal><cbc:TaxAmount currencyID="EUR">{}</cbc:TaxAmount></cac:TaxTotal>'),
    "BR-DEC-14": _TOTAL_UBL.format("<cbc:TaxInclusiveAmount>{}</cbc:TaxInclusiveAmount>"),
    "BR-DEC-15": (
        "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
        "<cbc:TaxCurrencyCode>USD</cbc:TaxCurrencyCode>"
        '<cac:TaxTotal><cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount></cac:TaxTotal>'
        '<cac:TaxTotal><cbc:TaxAmount currencyID="USD">{}</cbc:TaxAmount></cac:TaxTotal>'),
    "BR-DEC-16": _TOTAL_UBL.format("<cbc:PrepaidAmount>{}</cbc:PrepaidAmount>"),
    "BR-DEC-17": _TOTAL_UBL.format("<cbc:PayableRoundingAmount>{}</cbc:PayableRoundingAmount>"),
    "BR-DEC-18": _TOTAL_UBL.format("<cbc:PayableAmount>{}</cbc:PayableAmount>"),
    "BR-DEC-19": ("<cac:TaxTotal><cac:TaxSubtotal><cbc:TaxableAmount>{}</cbc:TaxableAmount>"
                  "</cac:TaxSubtotal></cac:TaxTotal>"),
    "BR-DEC-20": ("<cac:TaxTotal><cac:TaxSubtotal><cbc:TaxAmount>{}</cbc:TaxAmount>"
                  "</cac:TaxSubtotal></cac:TaxTotal>"),
    "BR-DEC-23": _LINEA_UBL.format("<cbc:LineExtensionAmount>{}</cbc:LineExtensionAmount>"),
    "BR-DEC-24": _LINEA_UBL.format(_ajuste_ubl(False, "<cbc:Amount>{}</cbc:Amount>")),
    "BR-DEC-25": _LINEA_UBL.format(_ajuste_ubl(False, "<cbc:BaseAmount>{}</cbc:BaseAmount>")),
    "BR-DEC-27": _LINEA_UBL.format(_ajuste_ubl(True, "<cbc:Amount>{}</cbc:Amount>")),
    "BR-DEC-28": _LINEA_UBL.format(_ajuste_ubl(True, "<cbc:BaseAmount>{}</cbc:BaseAmount>")),
}

_AJUSTE_CII = (
    "<ram:SpecifiedTradeAllowanceCharge><ram:ChargeIndicator><udt:Indicator>{}"
    "</udt:Indicator></ram:ChargeIndicator>{}</ram:SpecifiedTradeAllowanceCharge>"
)
_TOTAL_CII = (
    "<ram:SpecifiedTradeSettlementHeaderMonetarySummation>{}"
    "</ram:SpecifiedTradeSettlementHeaderMonetarySummation>"
)
_LINEA_CII = "<ram:SpecifiedLineTradeSettlement>{}</ram:SpecifiedLineTradeSettlement>"


def _ajuste_cii(cargo: bool, dentro: str) -> str:
    return _AJUSTE_CII.format("true" if cargo else "false", dentro)


# (dónde va: «cobro» o «linea», la plantilla)
CII = {
    "BR-DEC-01": ("cobro", _ajuste_cii(False, "<ram:ActualAmount>{}</ram:ActualAmount>")),
    "BR-DEC-02": ("cobro", _ajuste_cii(False, "<ram:BasisAmount>{}</ram:BasisAmount>")),
    "BR-DEC-05": ("cobro", _ajuste_cii(True, "<ram:ActualAmount>{}</ram:ActualAmount>")),
    "BR-DEC-06": ("cobro", _ajuste_cii(True, "<ram:BasisAmount>{}</ram:BasisAmount>")),
    "BR-DEC-09": ("cobro", _TOTAL_CII.format("<ram:LineTotalAmount>{}</ram:LineTotalAmount>")),
    "BR-DEC-10": ("cobro", _TOTAL_CII.format(
        "<ram:AllowanceTotalAmount>{}</ram:AllowanceTotalAmount>")),
    "BR-DEC-11": ("cobro", _TOTAL_CII.format("<ram:ChargeTotalAmount>{}</ram:ChargeTotalAmount>")),
    "BR-DEC-12": ("cobro", _TOTAL_CII.format(
        "<ram:TaxBasisTotalAmount>{}</ram:TaxBasisTotalAmount>")),
    "BR-DEC-13": ("cobro", "<ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>" + _TOTAL_CII.format(
        '<ram:TaxTotalAmount currencyID="EUR">{}</ram:TaxTotalAmount>')),
    "BR-DEC-14": ("cobro", _TOTAL_CII.format("<ram:GrandTotalAmount>{}</ram:GrandTotalAmount>")),
    "BR-DEC-15": ("cobro", "<ram:TaxCurrencyCode>USD</ram:TaxCurrencyCode>"
                  "<ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>" + _TOTAL_CII.format(
                      '<ram:TaxTotalAmount currencyID="EUR">21.00</ram:TaxTotalAmount>'
                      '<ram:TaxTotalAmount currencyID="USD">{}</ram:TaxTotalAmount>')),
    "BR-DEC-16": ("cobro", _TOTAL_CII.format("<ram:TotalPrepaidAmount>{}</ram:TotalPrepaidAmount>")),
    "BR-DEC-17": ("cobro", _TOTAL_CII.format("<ram:RoundingAmount>{}</ram:RoundingAmount>")),
    "BR-DEC-18": ("cobro", _TOTAL_CII.format("<ram:DuePayableAmount>{}</ram:DuePayableAmount>")),
    "BR-DEC-19": ("cobro", "<ram:ApplicableTradeTax><ram:BasisAmount>{}</ram:BasisAmount>"
                  "</ram:ApplicableTradeTax>"),
    "BR-DEC-20": ("cobro", "<ram:ApplicableTradeTax><ram:CalculatedAmount>{}</ram:CalculatedAmount>"
                  "</ram:ApplicableTradeTax>"),
    "BR-DEC-23": ("linea", _LINEA_CII.format(
        "<ram:SpecifiedTradeSettlementLineMonetarySummation><ram:LineTotalAmount>{}"
        "</ram:LineTotalAmount></ram:SpecifiedTradeSettlementLineMonetarySummation>")),
    "BR-DEC-24": ("linea", _LINEA_CII.format(
        _ajuste_cii(False, "<ram:ActualAmount>{}</ram:ActualAmount>"))),
    "BR-DEC-25": ("linea", _LINEA_CII.format(
        _ajuste_cii(False, "<ram:BasisAmount>{}</ram:BasisAmount>"))),
    "BR-DEC-27": ("linea", _LINEA_CII.format(
        _ajuste_cii(True, "<ram:ActualAmount>{}</ram:ActualAmount>"))),
    "BR-DEC-28": ("linea", _LINEA_CII.format(
        _ajuste_cii(True, "<ram:BasisAmount>{}</ram:BasisAmount>"))),
}

EDIFACT = {
    "BR-DEC-01": "ALC+A'MOA+204:{}'",
    "BR-DEC-02": "ALC+A'MOA+25:{}'",
    "BR-DEC-05": "ALC+C'MOA+23:{}'",
    "BR-DEC-06": "ALC+C'MOA+25:{}'",
    "BR-DEC-09": "UNS+S'MOA+79:{}'",
    "BR-DEC-10": "UNS+S'MOA+260:{}'",
    "BR-DEC-11": "UNS+S'MOA+259:{}'",
    "BR-DEC-12": "UNS+S'MOA+389:{}'",
    "BR-DEC-13": "UNS+S'MOA+176:{}'",
    "BR-DEC-14": "UNS+S'MOA+388:{}'",
    "BR-DEC-16": "UNS+S'MOA+113:{}'",
    "BR-DEC-18": "UNS+S'MOA+9:{}'",
    "BR-DEC-19": "UNS+S'TAX+7+VAT+++:::21+S'MOA+125:{}'",
    "BR-DEC-20": "UNS+S'TAX+7+VAT+++:::21+S'MOA+124:{}'",
    "BR-DEC-23": "LIN+1'MOA+203:{}'",
    "BR-DEC-24": "LIN+1'ALC+A'MOA+204:{}'",
    "BR-DEC-25": "LIN+1'ALC+A'MOA+25:{}'",
    "BR-DEC-27": "LIN+1'ALC+C'MOA+23:{}'",
    "BR-DEC-28": "LIN+1'ALC+C'MOA+25:{}'",
}

_TOTALES_FE = "<InvoiceTotals>{}</InvoiceTotals>"
_LINEA_FE = "<Items><InvoiceLine><ItemDescription>Concepto</ItemDescription>{}</InvoiceLine></Items>"

FACTURAE = {
    "BR-DEC-01": _TOTALES_FE.format(
        "<GeneralDiscounts><Discount><DiscountReason>Rappel</DiscountReason>"
        "<DiscountAmount>{}</DiscountAmount></Discount></GeneralDiscounts>"),
    "BR-DEC-05": _TOTALES_FE.format(
        "<GeneralSurcharges><Charge><ChargeReason>Porte</ChargeReason>"
        "<ChargeAmount>{}</ChargeAmount></Charge></GeneralSurcharges>"),
    "BR-DEC-09": _TOTALES_FE.format("<TotalGrossAmount>{}</TotalGrossAmount>"),
    "BR-DEC-10": _TOTALES_FE.format("<TotalGeneralDiscounts>{}</TotalGeneralDiscounts>"),
    "BR-DEC-11": _TOTALES_FE.format("<TotalGeneralSurcharges>{}</TotalGeneralSurcharges>"),
    "BR-DEC-12": _TOTALES_FE.format(
        "<TotalGrossAmountBeforeTaxes>{}</TotalGrossAmountBeforeTaxes>"),
    "BR-DEC-16": _TOTALES_FE.format("<TotalPaymentsOnAccount>{}</TotalPaymentsOnAccount>"),
    "BR-DEC-18": _TOTALES_FE.format("<TotalExecutableAmount>{}</TotalExecutableAmount>"),
    "BR-DEC-19": ("<TaxesOutputs><Tax><TaxableBase><TotalAmount>{}</TotalAmount></TaxableBase>"
                  "</Tax></TaxesOutputs>"),
    "BR-DEC-20": ("<TaxesOutputs><Tax><TaxAmount><TotalAmount>{}</TotalAmount></TaxAmount>"
                  "</Tax></TaxesOutputs>"),
    "BR-DEC-23": _LINEA_FE.format("<GrossAmount>{}</GrossAmount>"),
    "BR-DEC-24": _LINEA_FE.format(
        "<DiscountsAndRebates><Discount><DiscountAmount>{}</DiscountAmount></Discount>"
        "</DiscountsAndRebates>"),
    "BR-DEC-27": _LINEA_FE.format(
        "<Charges><Charge><ChargeAmount>{}</ChargeAmount></Charge></Charges>"),
}

# Lo que cada sintaxis no tiene dónde escribir, y el campo del mapa que lo
# dice. La regla calla ahí, y la prueba de abajo comprueba que calla porque el
# campo no está y no por otra cosa.
CALLAN = {
    "EDIFACT": {
        "BR-DEC-15": "moneda_impuestos",
        "BR-DEC-17": "redondeo",
    },
    "Facturae": {
        "BR-DEC-02": "cargo_base",
        "BR-DEC-06": "cargo_base",
        "BR-DEC-13": "impuestos",
        "BR-DEC-14": "con_impuestos",
        "BR-DEC-15": "impuestos",
        "BR-DEC-17": "redondeo",
        "BR-DEC-25": "cargo_base",
        "BR-DEC-28": "cargo_base",
    },
}


def _cii(donde: str, plantilla: str, importe: str):
    return cii(**{donde: plantilla.format(importe)})


def _documento(nombre: str, codigo: str, importe: str):
    if nombre == "UBL":
        return ubl(UBL[codigo].format(importe)), SINTAXIS_UBL
    if nombre == "CII":
        return _cii(*CII[codigo], importe), SINTAXIS_CII
    if nombre == "EDIFACT":
        return edi(EDIFACT[codigo].format(importe)), SINTAXIS_EDIFACT
    return facturae(FACTURAE[codigo].format(importe)), SINTAXIS_FACTURAE


CASOS = [
    (nombre, codigo)
    for nombre, tabla in (("UBL", UBL), ("CII", CII), ("EDIFACT", EDIFACT), ("Facturae", FACTURAE))
    for codigo in sorted(tabla)
]


@pytest.mark.parametrize("nombre, codigo", CASOS, ids=[f"{n}-{c}" for n, c in CASOS])
def test_tres_decimales_saltan_en_su_regla_y_en_ninguna_otra(nombre, codigo):
    raiz, sintaxis = _documento(nombre, codigo, "10.123")
    assert salen(raiz, sintaxis) == {codigo}


@pytest.mark.parametrize("nombre, codigo", CASOS, ids=[f"{n}-{c}" for n, c in CASOS])
def test_dos_decimales_no_saltan(nombre, codigo):
    for importe in ("10.12", "10.1", "10", "-10.12"):
        raiz, sintaxis = _documento(nombre, codigo, importe)
        assert salen(raiz, sintaxis) == set(), importe


@pytest.mark.parametrize("nombre, tabla, sintaxis", [
    ("UBL", UBL, SINTAXIS_UBL), ("CII", CII, SINTAXIS_CII),
    ("EDIFACT", EDIFACT, SINTAXIS_EDIFACT), ("Facturae", FACTURAE, SINTAXIS_FACTURAE),
], ids=["UBL", "CII", "EDIFACT", "Facturae"])
def test_cada_regla_tiene_su_caso_o_se_dice_por_que_calla(nombre, tabla, sintaxis):
    callan = CALLAN.get(nombre, {})
    assert set(tabla) | set(callan) == TODAS, sorted(TODAS - set(tabla) - set(callan))
    assert not set(tabla) & set(callan)
    for codigo, campo in callan.items():
        assert getattr(sintaxis, campo) == SIN_MAPA, (codigo, campo)


def test_todas_las_reglas_del_modulo_tienen_su_caso():
    del_modulo = {c.codigo for c in codigos_del_paquete() if c.modulo == "decimales.py"}
    assert del_modulo == TODAS == set(UBL)


def test_el_validador_las_corre_en_las_cuatro_sintaxis():
    """Que el módulo exista no es que se use: las de arriba lo llaman directo, y
    esta pasa por la entrada del validador. Facturae va por otro camino, factura
    a factura dentro del lote, y se prueba por separado."""
    for nombre in ("UBL", "CII", "EDIFACT", "Facturae"):
        raiz, _ = _documento(nombre, "BR-DEC-12", "10.123")
        if nombre == "EDIFACT":
            datos = (
                "UNB+UNOC:3+EMISOR+RECEPTOR+260819:1200+1'UNH+1+INVOIC:D:96A:UN'"
                "BGM+380+F-1'UNS+S'MOA+389:10.123'UNT+5+1'UNZ+1+1'").encode("utf-8")
        else:
            datos = etree.tostring(raiz.getroottree())
        codigos = {i.codigo for i in en16931.validar(datos).incidencias}
        assert "BR-DEC-12" in codigos, nombre


def test_son_errores():
    raiz, sintaxis = _documento("UBL", "BR-DEC-12", "10.123")
    assert la(raiz, sintaxis, "BR-DEC-12").gravedad == ERROR


# --- Lo escrito y el valor ------------------------------------------------------


def test_un_negativo_cuenta_sus_decimales_igual():
    raiz, sintaxis = _documento("UBL", "BR-DEC-18", "-10.123")
    assert salen(raiz, sintaxis) == {"BR-DEC-18"}


def test_los_ceros_de_mas_cuentan_donde_la_vinculacion_cuenta_lo_escrito():
    """`10.500` vale lo mismo que `10.50`, y UBL, EDIFACT y casi todo CII cuentan
    tres decimales: es lo que escriben sus vinculaciones. El informe dice que
    sobran ceros, que es lo que hay que saber para arreglarlo."""
    for nombre in ("UBL", "CII", "EDIFACT"):
        raiz, sintaxis = _documento(nombre, "BR-DEC-12", "10.500")
        assert salen(raiz, sintaxis) == {"BR-DEC-12"}, nombre
        assert "ceros" in la(raiz, sintaxis, "BR-DEC-12").mensaje
    raiz, sintaxis = _documento("UBL", "BR-DEC-12", "10.501")
    assert "ceros" not in la(raiz, sintaxis, "BR-DEC-12").mensaje


def test_cii_mira_el_valor_en_el_total_del_impuesto():
    """BR-DEC-13 y 15 redondean en la vinculación de CII; las demás cuentan."""
    for codigo in ("BR-DEC-13", "BR-DEC-15"):
        raiz, sintaxis = _documento("CII", codigo, "21.000")
        assert salen(raiz, sintaxis) == set(), codigo
        raiz, sintaxis = _documento("CII", codigo, "21.001")
        assert salen(raiz, sintaxis) == {codigo}, codigo


def test_facturae_mira_el_valor():
    """Su esquema escribe los importes con hasta ocho decimales: `1500.00000000`
    es un importe de dos."""
    for codigo in FACTURAE:
        raiz, sintaxis = _documento("Facturae", codigo, "1500.00000000")
        assert salen(raiz, sintaxis) == set(), codigo
        raiz, sintaxis = _documento("Facturae", codigo, "1500.00100000")
        assert salen(raiz, sintaxis) == {codigo}, codigo


def test_lo_que_no_es_un_numero_es_cosa_de_otra_regla():
    for importe in ("diez.123", "", "10.12.3"):
        raiz, sintaxis = _documento("UBL", "BR-DEC-12", importe)
        assert salen(raiz, sintaxis) == set(), importe


# --- El total del impuesto, en cada moneda --------------------------------------


def test_el_total_en_la_moneda_de_contabilidad_no_es_el_de_la_factura():
    """BT-110 es el total en la moneda de la factura y BT-111 en la de
    contabilidad; tres decimales en uno no son un defecto del otro."""
    def documento(en_euros: str, en_dolares: str):
        return ubl(
            "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
            "<cbc:TaxCurrencyCode>USD</cbc:TaxCurrencyCode>"
            f'<cac:TaxTotal><cbc:TaxAmount currencyID="USD">{en_dolares}</cbc:TaxAmount></cac:TaxTotal>'
            f'<cac:TaxTotal><cbc:TaxAmount currencyID="EUR">{en_euros}</cbc:TaxAmount></cac:TaxTotal>')
    assert salen(documento("21.00", "23.123"), SINTAXIS_UBL) == {"BR-DEC-15"}
    assert salen(documento("21.001", "23.12"), SINTAXIS_UBL) == {"BR-DEC-13"}


def test_en_edifact_el_impuesto_de_un_tipo_no_es_el_total():
    """EANCOM repite el MOA+176 dentro de cada grupo de impuesto, con el de ese
    tipo. El total de la factura es el del resumen, y es el único que mira
    BR-DEC-13."""
    raiz = edi("UNS+S'MOA+176:21.00'TAX+7+VAT+++:::21+S'MOA+125:100.00'MOA+176:21.000'")
    assert salen(raiz, SINTAXIS_EDIFACT) == set()
    raiz = edi("UNS+S'MOA+176:21.001'TAX+7+VAT+++:::21+S'MOA+125:100.00'MOA+176:21.00'")
    assert la(raiz, SINTAXIS_EDIFACT, "BR-DEC-13").encontrado == "21.001"


def test_sin_moneda_de_contabilidad_un_total_en_otra_moneda_no_es_ninguno_de_los_dos():
    raiz = ubl(
        "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
        '<cac:TaxTotal><cbc:TaxAmount currencyID="USD">23.123</cbc:TaxAmount></cac:TaxTotal>')
    assert salen(raiz, SINTAXIS_UBL) == set()


def test_la_misma_moneda_en_las_dos_es_el_mismo_total_para_las_dos_reglas():
    """Como en la vinculación de CII: BT-111 es el total cuya moneda es la de
    contabilidad, sea o no la de la factura."""
    raiz = ubl(
        "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
        "<cbc:TaxCurrencyCode>EUR</cbc:TaxCurrencyCode>"
        '<cac:TaxTotal><cbc:TaxAmount currencyID="EUR">21.001</cbc:TaxAmount></cac:TaxTotal>')
    assert salen(raiz, SINTAXIS_UBL) == {"BR-DEC-13", "BR-DEC-15"}


def test_el_vinculo_de_ubl_no_ve_el_total_del_impuesto_y_aqui_si():
    """La expresión oficial de BR-DEC-13 en UBL compara la moneda del importe con
    un `cbc:DocumentCurrencyCode` **hijo del importe**, que no existe: el filtro
    no deja pasar ninguno y la regla se cumple siempre. Medido evaluándola
    tal cual sobre una factura con 21,001 de total del impuesto."""
    from tests.test_norma_oficial import vinculacion

    raiz = etree.ElementTree(ubl(UBL["BR-DEC-13"].format("21.001"))).getroot()
    espacios = {
        "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    }
    for codigo in ("BR-DEC-13", "BR-DEC-15"):
        assert raiz.xpath(vinculacion("UBL")[codigo], namespaces=espacios) is True, codigo
    assert salen(raiz, SINTAXIS_UBL) == {"BR-DEC-13"}


# --- Un defecto repetido --------------------------------------------------------


def test_un_defecto_repetido_es_una_incidencia_que_dice_donde():
    raiz = ubl(
        "<cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:LineExtensionAmount>1.001</cbc:LineExtensionAmount>"
        "</cac:InvoiceLine>"
        "<cac:InvoiceLine><cbc:ID>2</cbc:ID><cbc:LineExtensionAmount>2.00</cbc:LineExtensionAmount>"
        "</cac:InvoiceLine>"
        "<cac:InvoiceLine><cbc:ID>3</cbc:ID><cbc:LineExtensionAmount>3.0003</cbc:LineExtensionAmount>"
        "</cac:InvoiceLine>")
    incidencias = decimales.reglas(raiz, SINTAXIS_UBL)
    assert [i.codigo for i in incidencias] == ["BR-DEC-23"]
    assert "línea 1, línea 3" in incidencias[0].campo
    assert incidencias[0].encontrado == "1.001, 3.0003"
