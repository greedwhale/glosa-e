# -*- coding: utf-8 -*-
"""Las reglas del modelo que miran un grupo y lo que tiene que llevar dentro.

Las pruebas oficiales de la norma, en `test_norma_oficial.py`, son de UBL: de
cada una de estas reglas hay un par de casos, uno bueno y uno malo, y los dos
se pasan allí. Lo que no prueban es el mapa de las otras tres sintaxis, que es
donde se decide qué elemento es qué. Eso es lo de aquí: el mismo defecto
montado en CII, en EDIFACT y en Facturae, y la regla tiene que saltar en el
malo y callar en el bueno.

Y lo que las oficiales no prueban ni en UBL, que se dice donde toca: el
beneficiario que es el propio vendedor, el prefijo griego, la moneda de
contabilidad igual a la de la factura, y que el número de una tarjeta no se
repite en el informe.
"""
from __future__ import annotations

import pytest
from lxml import etree

from validador import edifact, modelo
from validador.codigos import codigos_del_paquete
from validador.formato import detectar
from validador.incidencias import AVISO, ERROR
from validador.sintaxis import (
    SINTAXIS_CII,
    SINTAXIS_EDIFACT,
    SINTAXIS_FACTURAE,
    SINTAXIS_UBL,
)

NS_UBL = (
    'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" '
    'xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"'
)


def ubl(cuerpo: str, raiz: str = "Invoice"):
    return etree.fromstring(
        f'<{raiz} xmlns="urn:oasis:names:specification:ubl:schema:xsd:{raiz}-2" '
        f"{NS_UBL}>{cuerpo}</{raiz}>")


def cii(acuerdo: str = "", entrega: str = "", cobro: str = "", linea: str = ""):
    """Una CII con lo que se le dé en cada uno de sus tres bloques y en una línea."""
    return etree.fromstring(
        '<rsm:CrossIndustryInvoice '
        'xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" '
        'xmlns:ram="urn:un:unece:uncefact:data:standard:'
        'ReusableAggregateBusinessInformationEntity:100" '
        'xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">'
        "<rsm:SupplyChainTradeTransaction>"
        + (f"<ram:IncludedSupplyChainTradeLineItem>{linea}"
           "</ram:IncludedSupplyChainTradeLineItem>" if linea else "")
        + f"<ram:ApplicableHeaderTradeAgreement>{acuerdo}</ram:ApplicableHeaderTradeAgreement>"
        f"<ram:ApplicableHeaderTradeDelivery>{entrega}</ram:ApplicableHeaderTradeDelivery>"
        f"<ram:ApplicableHeaderTradeSettlement>{cobro}</ram:ApplicableHeaderTradeSettlement>"
        "</rsm:SupplyChainTradeTransaction></rsm:CrossIndustryInvoice>")


def edi(cuerpo: str):
    """Un INVOIC D.96A con el cuerpo que se le dé, ya convertido en árbol."""
    segmentos = [s for s in cuerpo.split("'") if s.strip()]
    datos = (
        "UNB+UNOC:3+EMISOR+RECEPTOR+260819:1200+1'UNH+1+INVOIC:D:96A:UN'"
        f"BGM+380+F-1'{cuerpo}UNT+{len(segmentos) + 3}+1'UNZ+1+1'"
    ).encode("utf-8")
    raiz, _ = edifact.arbol(datos, detectar(datos))
    return raiz


def facturae(factura: str, partes: str = ""):
    """Un `<Invoice>` de Facturae dentro de su lote, que es donde se evalúa."""
    raiz = etree.fromstring(
        '<fe:Facturae xmlns:fe="http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml">'
        f"<Parties>{partes}</Parties><Invoices><Invoice>{factura}</Invoice></Invoices>"
        "</fe:Facturae>")
    return raiz.find("Invoices/Invoice")


def salen(raiz, sintaxis) -> set[str]:
    return {i.codigo for i in modelo.reglas(raiz, sintaxis)}


def la(raiz, sintaxis, codigo: str):
    return next(i for i in modelo.reglas(raiz, sintaxis) if i.codigo == codigo)


# --- CII: cada regla, en malo y en bueno ------------------------------------

_REPRESENTANTE = "<ram:SellerTaxRepresentativeTradeParty>{}</ram:SellerTaxRepresentativeTradeParty>"
_AJUSTE = (
    "<ram:SpecifiedTradeAllowanceCharge><ram:ChargeIndicator><udt:Indicator>{}"
    "</udt:Indicator></ram:ChargeIndicator>{}</ram:SpecifiedTradeAllowanceCharge>"
)
_AJUSTE_COMPLETO = (
    "<ram:ActualAmount>10</ram:ActualAmount><ram:Reason>Porte</ram:Reason>"
    "<ram:CategoryTradeTax><ram:TypeCode>VAT</ram:TypeCode>"
    "<ram:CategoryCode>S</ram:CategoryCode></ram:CategoryTradeTax>"
)
_LINEA_AJUSTE = "<ram:SpecifiedLineTradeSettlement>{}</ram:SpecifiedLineTradeSettlement>"
_PAGO = "<ram:SpecifiedTradeSettlementPaymentMeans>{}</ram:SpecifiedTradeSettlementPaymentMeans>"
_PERIODO = (
    "<ram:BillingSpecifiedPeriod>{}</ram:BillingSpecifiedPeriod>"
)


def _fecha(etiqueta: str, dia: str) -> str:
    return (f"<ram:{etiqueta}><udt:DateTimeString format=\"102\">{dia}"
            f"</udt:DateTimeString></ram:{etiqueta}>")


_PAIS_CII = (
    "<ram:SellerTradeParty><ram:PostalTradeAddress><ram:CountryID>{}</ram:CountryID>"
    "</ram:PostalTradeAddress></ram:SellerTradeParty>"
)
_DESGLOSE_CII = "<ram:ApplicableTradeTax><ram:CategoryCode>{}</ram:CategoryCode></ram:ApplicableTradeTax>"

# (código, la factura mala, la buena). La buena es la mala con lo que falta.
CASOS_CII = [
    ("BR-17",
     cii(cobro="<ram:PayeeTradeParty></ram:PayeeTradeParty>"),
     cii(cobro="<ram:PayeeTradeParty><ram:Name>Factoring SA</ram:Name></ram:PayeeTradeParty>")),
    ("BR-18",
     cii(acuerdo=_REPRESENTANTE.format("")),
     cii(acuerdo=_REPRESENTANTE.format("<ram:Name>Representante SL</ram:Name>"))),
    ("BR-19",
     cii(acuerdo=_REPRESENTANTE.format("")),
     cii(acuerdo=_REPRESENTANTE.format("<ram:PostalTradeAddress/>"))),
    ("BR-20",
     cii(acuerdo=_REPRESENTANTE.format("<ram:PostalTradeAddress/>")),
     cii(acuerdo=_REPRESENTANTE.format(
         "<ram:PostalTradeAddress><ram:CountryID>ES</ram:CountryID></ram:PostalTradeAddress>"))),
    ("BR-56",
     cii(acuerdo=_REPRESENTANTE.format("")),
     cii(acuerdo=_REPRESENTANTE.format(
         "<ram:SpecifiedTaxRegistration><ram:ID schemeID=\"VA\">ESB12345678</ram:ID>"
         "</ram:SpecifiedTaxRegistration>"))),
    ("BR-27",
     cii(linea="<ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice>"
               "<ram:ChargeAmount>-1</ram:ChargeAmount></ram:NetPriceProductTradePrice>"
               "</ram:SpecifiedLineTradeAgreement>"),
     cii(linea="<ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice>"
               "<ram:ChargeAmount>0</ram:ChargeAmount></ram:NetPriceProductTradePrice>"
               "</ram:SpecifiedLineTradeAgreement>")),
    ("BR-28",
     cii(linea="<ram:SpecifiedLineTradeAgreement><ram:GrossPriceProductTradePrice>"
               "<ram:ChargeAmount>-1</ram:ChargeAmount></ram:GrossPriceProductTradePrice>"
               "</ram:SpecifiedLineTradeAgreement>"),
     cii(linea="<ram:SpecifiedLineTradeAgreement><ram:GrossPriceProductTradePrice>"
               "<ram:ChargeAmount>1</ram:ChargeAmount></ram:GrossPriceProductTradePrice>"
               "</ram:SpecifiedLineTradeAgreement>")),
    ("BR-29",
     cii(cobro=_PERIODO.format(_fecha("StartDateTime", "20260601") + _fecha("EndDateTime", "20260501"))),
     cii(cobro=_PERIODO.format(_fecha("StartDateTime", "20260601") + _fecha("EndDateTime", "20260601")))),
    ("BR-30",
     cii(linea=_LINEA_AJUSTE.format(_PERIODO.format(
         _fecha("StartDateTime", "20260601") + _fecha("EndDateTime", "20260501")))),
     cii(linea=_LINEA_AJUSTE.format(_PERIODO.format(
         _fecha("StartDateTime", "20260601") + _fecha("EndDateTime", "20260701"))))),
    ("BR-CO-19",
     cii(cobro=_PERIODO.format("")),
     cii(cobro=_PERIODO.format(_fecha("EndDateTime", "20260630")))),
    ("BR-CO-20",
     cii(linea=_LINEA_AJUSTE.format(_PERIODO.format(""))),
     cii(linea=_LINEA_AJUSTE.format(_PERIODO.format(_fecha("StartDateTime", "20260601"))))),
    ("BR-31", cii(cobro=_AJUSTE.format("false", "")), cii(cobro=_AJUSTE.format("false", _AJUSTE_COMPLETO))),
    ("BR-32", cii(cobro=_AJUSTE.format("false", "")), cii(cobro=_AJUSTE.format("false", _AJUSTE_COMPLETO))),
    ("BR-33", cii(cobro=_AJUSTE.format("false", "")), cii(cobro=_AJUSTE.format("false", _AJUSTE_COMPLETO))),
    ("BR-CO-21", cii(cobro=_AJUSTE.format("false", "")),
     cii(cobro=_AJUSTE.format("false", "<ram:ReasonCode>95</ram:ReasonCode>"))),
    ("BR-36", cii(cobro=_AJUSTE.format("true", "")), cii(cobro=_AJUSTE.format("true", _AJUSTE_COMPLETO))),
    ("BR-37", cii(cobro=_AJUSTE.format("true", "")), cii(cobro=_AJUSTE.format("true", _AJUSTE_COMPLETO))),
    ("BR-38", cii(cobro=_AJUSTE.format("true", "")), cii(cobro=_AJUSTE.format("true", _AJUSTE_COMPLETO))),
    ("BR-CO-22", cii(cobro=_AJUSTE.format("true", "")),
     cii(cobro=_AJUSTE.format("true", "<ram:ReasonCode>FC</ram:ReasonCode>"))),
    ("BR-41", cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("false", ""))),
     cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("false", _AJUSTE_COMPLETO)))),
    ("BR-42", cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("false", ""))),
     cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("false", _AJUSTE_COMPLETO)))),
    ("BR-CO-23", cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("false", ""))),
     cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("false", "<ram:ReasonCode>95</ram:ReasonCode>")))),
    ("BR-43", cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("true", ""))),
     cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("true", _AJUSTE_COMPLETO)))),
    ("BR-44", cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("true", ""))),
     cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("true", _AJUSTE_COMPLETO)))),
    ("BR-CO-24", cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("true", ""))),
     cii(linea=_LINEA_AJUSTE.format(_AJUSTE.format("true", "<ram:Reason>Montaje</ram:Reason>")))),
    ("BR-49", cii(cobro=_PAGO.format("")), cii(cobro=_PAGO.format("<ram:TypeCode>49</ram:TypeCode>"))),
    ("BR-50",
     cii(cobro=_PAGO.format("<ram:TypeCode>30</ram:TypeCode>"
                            "<ram:PayeePartyCreditorFinancialAccount/>")),
     cii(cobro=_PAGO.format("<ram:TypeCode>30</ram:TypeCode><ram:PayeePartyCreditorFinancialAccount>"
                            "<ram:IBANID>ES7620770024003102575766</ram:IBANID>"
                            "</ram:PayeePartyCreditorFinancialAccount>"))),
    ("BR-61",
     cii(cobro=_PAGO.format("<ram:TypeCode>58</ram:TypeCode>")),
     cii(cobro=_PAGO.format("<ram:TypeCode>58</ram:TypeCode><ram:PayeePartyCreditorFinancialAccount>"
                            "<ram:ProprietaryID>0001</ram:ProprietaryID>"
                            "</ram:PayeePartyCreditorFinancialAccount>"))),
    ("BR-51",
     cii(cobro=_PAGO.format("<ram:ApplicableTradeSettlementFinancialCard><ram:ID>4111111111111111"
                            "</ram:ID></ram:ApplicableTradeSettlementFinancialCard>")),
     cii(cobro=_PAGO.format("<ram:ApplicableTradeSettlementFinancialCard><ram:ID>1111"
                            "</ram:ID></ram:ApplicableTradeSettlementFinancialCard>"))),
    ("BR-52",
     cii(acuerdo="<ram:AdditionalReferencedDocument><ram:TypeCode>916</ram:TypeCode>"
                 "</ram:AdditionalReferencedDocument>"),
     cii(acuerdo="<ram:AdditionalReferencedDocument><ram:IssuerAssignedID>Albarán 7</ram:IssuerAssignedID>"
                 "<ram:TypeCode>916</ram:TypeCode></ram:AdditionalReferencedDocument>")),
    ("BR-53",
     cii(cobro="<ram:TaxCurrencyCode>USD</ram:TaxCurrencyCode>"
               "<ram:SpecifiedTradeSettlementHeaderMonetarySummation>"
               "<ram:TaxTotalAmount currencyID=\"EUR\">21</ram:TaxTotalAmount>"
               "</ram:SpecifiedTradeSettlementHeaderMonetarySummation>"),
     cii(cobro="<ram:TaxCurrencyCode>USD</ram:TaxCurrencyCode>"
               "<ram:SpecifiedTradeSettlementHeaderMonetarySummation>"
               "<ram:TaxTotalAmount currencyID=\"EUR\">21</ram:TaxTotalAmount>"
               "<ram:TaxTotalAmount currencyID=\"USD\">23</ram:TaxTotalAmount>"
               "</ram:SpecifiedTradeSettlementHeaderMonetarySummation>")),
    ("BR-54",
     cii(linea="<ram:SpecifiedTradeProduct><ram:ApplicableProductCharacteristic>"
               "<ram:Description>Color</ram:Description>"
               "</ram:ApplicableProductCharacteristic></ram:SpecifiedTradeProduct>"),
     cii(linea="<ram:SpecifiedTradeProduct><ram:ApplicableProductCharacteristic>"
               "<ram:Description>Color</ram:Description><ram:Value>Negro</ram:Value>"
               "</ram:ApplicableProductCharacteristic></ram:SpecifiedTradeProduct>")),
    ("BR-55",
     cii(cobro="<ram:InvoiceReferencedDocument/>"),
     cii(cobro="<ram:InvoiceReferencedDocument><ram:IssuerAssignedID>F-2026-1</ram:IssuerAssignedID>"
               "</ram:InvoiceReferencedDocument>")),
    ("BR-57",
     cii(entrega="<ram:ShipToTradeParty><ram:PostalTradeAddress><ram:CityName>Soria</ram:CityName>"
                 "</ram:PostalTradeAddress></ram:ShipToTradeParty>"),
     cii(entrega="<ram:ShipToTradeParty><ram:PostalTradeAddress><ram:CountryID>ES</ram:CountryID>"
                 "</ram:PostalTradeAddress></ram:ShipToTradeParty>")),
    ("BR-62",
     cii(acuerdo="<ram:SellerTradeParty><ram:URIUniversalCommunication><ram:URIID>a@b.es</ram:URIID>"
                 "</ram:URIUniversalCommunication></ram:SellerTradeParty>"),
     cii(acuerdo="<ram:SellerTradeParty><ram:URIUniversalCommunication>"
                 "<ram:URIID schemeID=\"EM\">a@b.es</ram:URIID>"
                 "</ram:URIUniversalCommunication></ram:SellerTradeParty>")),
    ("BR-63",
     cii(acuerdo="<ram:BuyerTradeParty><ram:URIUniversalCommunication><ram:URIID>a@b.es</ram:URIID>"
                 "</ram:URIUniversalCommunication></ram:BuyerTradeParty>"),
     cii(acuerdo="<ram:BuyerTradeParty><ram:URIUniversalCommunication>"
                 "<ram:URIID schemeID=\"EM\">a@b.es</ram:URIID>"
                 "</ram:URIUniversalCommunication></ram:BuyerTradeParty>")),
    ("BR-64",
     cii(linea="<ram:SpecifiedTradeProduct><ram:GlobalID>8412345000019</ram:GlobalID>"
               "</ram:SpecifiedTradeProduct>"),
     cii(linea="<ram:SpecifiedTradeProduct><ram:GlobalID schemeID=\"0160\">8412345000019"
               "</ram:GlobalID></ram:SpecifiedTradeProduct>")),
    ("BR-65",
     cii(linea="<ram:SpecifiedTradeProduct><ram:DesignatedProductClassification>"
               "<ram:ClassCode>44111500</ram:ClassCode></ram:DesignatedProductClassification>"
               "</ram:SpecifiedTradeProduct>"),
     cii(linea="<ram:SpecifiedTradeProduct><ram:DesignatedProductClassification>"
               "<ram:ClassCode listID=\"STI\">44111500</ram:ClassCode>"
               "</ram:DesignatedProductClassification></ram:SpecifiedTradeProduct>")),
    ("BR-CO-03",
     cii(cobro="<ram:ApplicableTradeTax><ram:TaxPointDate><udt:DateString>20260601</udt:DateString>"
               "</ram:TaxPointDate><ram:DueDateTypeCode>72</ram:DueDateTypeCode></ram:ApplicableTradeTax>"),
     cii(cobro="<ram:ApplicableTradeTax><ram:DueDateTypeCode>72</ram:DueDateTypeCode>"
               "</ram:ApplicableTradeTax>")),
    ("BR-CO-04",
     cii(linea="<ram:SpecifiedLineTradeSettlement/>"),
     cii(linea="<ram:SpecifiedLineTradeSettlement><ram:ApplicableTradeTax><ram:TypeCode>VAT"
               "</ram:TypeCode><ram:CategoryCode>S</ram:CategoryCode></ram:ApplicableTradeTax>"
               "</ram:SpecifiedLineTradeSettlement>")),
    ("BR-CO-09",
     cii(acuerdo="<ram:SellerTradeParty><ram:SpecifiedTaxRegistration>"
                 "<ram:ID schemeID=\"VA\">B12345678</ram:ID></ram:SpecifiedTaxRegistration>"
                 "</ram:SellerTradeParty>"),
     cii(acuerdo="<ram:SellerTradeParty><ram:SpecifiedTaxRegistration>"
                 "<ram:ID schemeID=\"VA\">ESB12345678</ram:ID></ram:SpecifiedTaxRegistration>"
                 "</ram:SellerTradeParty>")),
    ("BR-CO-26",
     cii(acuerdo="<ram:SellerTradeParty><ram:Name>Vendedor SL</ram:Name></ram:SellerTradeParty>"),
     cii(acuerdo="<ram:SellerTradeParty><ram:Name>Vendedor SL</ram:Name>"
                 "<ram:SpecifiedLegalOrganization><ram:ID>B12345678</ram:ID>"
                 "</ram:SpecifiedLegalOrganization></ram:SellerTradeParty>")),
    # La B es el pago fraccionado italiano: solo entre partes en Italia, y sin S.
    ("BR-B-01",
     cii(acuerdo=_PAIS_CII.format("ES"), cobro=_DESGLOSE_CII.format("B")),
     cii(acuerdo=_PAIS_CII.format("IT"), cobro=_DESGLOSE_CII.format("B"))),
    ("BR-B-02",
     cii(cobro=_DESGLOSE_CII.format("B") + _DESGLOSE_CII.format("S")),
     cii(cobro=_DESGLOSE_CII.format("B") + _DESGLOSE_CII.format("B"))),
]


@pytest.mark.parametrize("codigo, mala, buena", CASOS_CII, ids=[c[0] for c in CASOS_CII])
def test_cii_cada_regla_salta_en_la_mala_y_calla_en_la_buena(codigo, mala, buena):
    assert codigo in salen(mala, SINTAXIS_CII)
    assert codigo not in salen(buena, SINTAXIS_CII)


def test_cii_todas_las_reglas_del_modulo_tienen_su_caso():
    """Que la lista de arriba no se quede corta el día que entre una regla.

    Los códigos del módulo se leen del fuente, como los lee el catálogo: una
    lista escrita aquí se quedaría atrás igual que la de arriba.
    """
    del_modulo = {c.codigo for c in codigos_del_paquete() if c.modulo == "modelo.py"}
    assert {c[0] for c in CASOS_CII} == del_modulo


# --- EDIFACT -----------------------------------------------------------------

_NAD_SE = "NAD+SE+8412345000019::9++Vendedor SL+Calle 1+Madrid++28001+ES'RFF+VA:ESB12345678'"

CASOS_EDIFACT = [
    # El representante fiscal es el NAD+LC, como en 27 reglas del esquematrón
    # oficial de EDIFACT; el AE lo usa una sola, y aquí no se sigue.
    ("BR-18", "NAD+LC'", "NAD+LC+++Representante SL'"),
    ("BR-19", "NAD+LC+++Representante SL'", "NAD+LC+++Representante SL+Calle 2'"),
    ("BR-20", "NAD+LC+++Representante SL+Calle 2+Soria'", "NAD+LC+++Representante SL+Calle 2+Soria++42001+ES'"),
    ("BR-56", "NAD+LC+++Representante SL'", "NAD+LC+++Representante SL'RFF+VA:ESB87654321'"),
    ("BR-17", "NAD+PE'", "NAD+PE+++Factoring SA'"),
    ("BR-55", "RFF+OI'", "RFF+OI:F-2026-1'"),
    ("BR-57", "NAD+DP+++++Soria'", "NAD+DP+++++Soria++42001+ES'"),
    ("BR-29", "DTM+167:20260601:102'DTM+168:20260501:102'", "DTM+167:20260601:102'DTM+168:20260630:102'"),
    ("BR-CO-03", "DTM+131:20260601:102'DTM+3:20260601:102'", "DTM+131:20260601:102'"),
    ("BR-CO-09", "NAD+SE+++Vendedor SL'RFF+VA:B12345678'", "NAD+SE+++Vendedor SL'RFF+VA:ESB12345678'"),
    ("BR-CO-26", "NAD+SE+++Vendedor SL'", _NAD_SE),
    ("BR-31", "ALC+A++++TD'", "ALC+A++++TD'MOA+204:10'TAX+7+VAT+++:::21+S'"),
    ("BR-32", "ALC+A++++TD'MOA+204:10'", "ALC+A++++TD'MOA+204:10'TAX+7+VAT+++:::21+S'"),
    ("BR-33", "ALC+A'MOA+204:10'", "ALC+A++++TD'MOA+204:10'"),
    ("BR-CO-21", "ALC+A'MOA+204:10'", "ALC+A+Promocion'MOA+204:10'"),
    ("BR-36", "ALC+C++++FC'", "ALC+C++++FC'MOA+23:10'"),
    ("BR-37", "ALC+C++++FC'MOA+23:10'", "ALC+C++++FC'MOA+23:10'TAX+7+VAT+++:::21+S'"),
    ("BR-38", "ALC+C'MOA+23:10'", "ALC+C++++FC'MOA+23:10'"),
    ("BR-CO-22", "ALC+C'MOA+23:10'", "ALC+C++++:::Porte'MOA+23:10'"),
    ("BR-27", "LIN+1'PRI+AAA:-1'", "LIN+1'PRI+AAA:1'"),
    ("BR-28", "LIN+1'PRI+AAB:-1'", "LIN+1'PRI+AAB:1'"),
    ("BR-30", "LIN+1'DTM+167:20260601:102'DTM+168:20260501:102'", "LIN+1'DTM+167:20260601:102'"),
    ("BR-CO-04", "LIN+1'", "LIN+1'TAX+7+VAT+++:::21+S'"),
    ("BR-41", "LIN+1'ALC+A++++TD'", "LIN+1'ALC+A++++TD'MOA+204:1'"),
    ("BR-42", "LIN+1'ALC+A'MOA+204:1'", "LIN+1'ALC+A++++TD'MOA+204:1'"),
    ("BR-CO-23", "LIN+1'ALC+A'MOA+204:1'", "LIN+1'ALC+A++++TD'MOA+204:1'"),
    ("BR-43", "LIN+1'ALC+C++++FC'", "LIN+1'ALC+C++++FC'MOA+23:1'"),
    ("BR-44", "LIN+1'ALC+C'MOA+23:1'", "LIN+1'ALC+C++++FC'MOA+23:1'"),
    ("BR-CO-24", "LIN+1'ALC+C'MOA+23:1'", "LIN+1'ALC+C++++FC'MOA+23:1'"),
    ("BR-64", "LIN+1++8412345000019'", "LIN+1++8412345000019:EN'"),
    ("BR-54", "LIN+1'FTX+ACF+++Color'", "LIN+1'FTX+ACF+++Color:Negro'"),
    ("BR-B-01", "NAD+SE+++Vendedor+Via Roma 1+Milano++20121+FR'LIN+1'TAX+7+VAT+++:::22+B'",
     "NAD+SE+++Vendedor+Via Roma 1+Milano++20121+IT'LIN+1'TAX+7+VAT+++:::22+B'"),
    ("BR-B-02", "LIN+1'TAX+7+VAT+++:::22+B'LIN+2'TAX+7+VAT+++:::22+S'",
     "LIN+1'TAX+7+VAT+++:::22+B'LIN+2'TAX+7+VAT+++:::22+B'"),
]


@pytest.mark.parametrize("codigo, mala, buena", CASOS_EDIFACT, ids=[c[0] for c in CASOS_EDIFACT])
def test_edifact_cada_regla_salta_en_la_mala_y_calla_en_la_buena(codigo, mala, buena):
    assert codigo in salen(edi(mala), SINTAXIS_EDIFACT)
    assert codigo not in salen(edi(buena), SINTAXIS_EDIFACT)


def test_edifact_el_descuento_sobre_el_precio_no_es_de_la_linea():
    """El ALC con importe 509 es BT-147: va del precio bruto al neto."""
    raiz = edi("LIN+1'PRI+AAA:1273'PRI+AAB:1498'ALC+A'MOA+509:225'")
    assert not {"BR-41", "BR-42", "BR-CO-23"} & salen(raiz, SINTAXIS_EDIFACT)


def test_edifact_no_tiene_instruccion_de_pago_que_mirar():
    """El medio va en un PAI de las condiciones de pago y la cuenta en un FII de
    la parte: no hay grupo que sea la instrucción, y no se inventa."""
    raiz = edi("PAT+1'PAI+::30'" + _NAD_SE)
    assert not {"BR-49", "BR-50", "BR-61"} & salen(raiz, SINTAXIS_EDIFACT)


# --- Facturae ----------------------------------------------------------------

_LINEA_FE = (
    "<Items><InvoiceLine><ItemDescription>Concepto</ItemDescription>{}"
    "<TaxesOutputs><Tax><TaxTypeCode>01</TaxTypeCode><TaxRate>21</TaxRate></Tax></TaxesOutputs>"
    "</InvoiceLine></Items>"
)
_PLAZO_FE = (
    "<PaymentDetails><Installment><InstallmentDueDate>2026-10-01</InstallmentDueDate>"
    "<InstallmentAmount>121</InstallmentAmount>{}</Installment></PaymentDetails>"
)

CASOS_FACTURAE = [
    ("BR-29",
     "<InvoiceIssueData><InvoicingPeriod><StartDate>2026-06-01</StartDate>"
     "<EndDate>2026-05-01</EndDate></InvoicingPeriod></InvoiceIssueData>",
     "<InvoiceIssueData><InvoicingPeriod><StartDate>2026-06-01</StartDate>"
     "<EndDate>2026-06-30</EndDate></InvoicingPeriod></InvoiceIssueData>"),
    ("BR-30",
     _LINEA_FE.format("<LineItemPeriod><StartDate>2026-06-01</StartDate>"
                      "<EndDate>2026-05-01</EndDate></LineItemPeriod>"),
     _LINEA_FE.format("<LineItemPeriod><StartDate>2026-06-01</StartDate>"
                      "<EndDate>2026-06-01</EndDate></LineItemPeriod>")),
    ("BR-27",
     _LINEA_FE.format("<UnitPriceWithoutTax>-1</UnitPriceWithoutTax>"),
     _LINEA_FE.format("<UnitPriceWithoutTax>1</UnitPriceWithoutTax>")),
    ("BR-41",
     _LINEA_FE.format("<DiscountsAndRebates><Discount><DiscountReason>Pronto pago</DiscountReason>"
                      "</Discount></DiscountsAndRebates>"),
     _LINEA_FE.format("<DiscountsAndRebates><Discount><DiscountReason>Pronto pago</DiscountReason>"
                      "<DiscountAmount>1</DiscountAmount></Discount></DiscountsAndRebates>")),
    ("BR-43",
     _LINEA_FE.format("<Charges><Charge><ChargeReason>Porte</ChargeReason></Charge></Charges>"),
     _LINEA_FE.format("<Charges><Charge><ChargeReason>Porte</ChargeReason>"
                      "<ChargeAmount>1</ChargeAmount></Charge></Charges>")),
    ("BR-31",
     "<InvoiceTotals><GeneralDiscounts><Discount><DiscountReason>Rappel</DiscountReason>"
     "</Discount></GeneralDiscounts></InvoiceTotals>",
     "<InvoiceTotals><GeneralDiscounts><Discount><DiscountReason>Rappel</DiscountReason>"
     "<DiscountAmount>5</DiscountAmount></Discount></GeneralDiscounts></InvoiceTotals>"),
    ("BR-49", _PLAZO_FE.format(""), _PLAZO_FE.format("<PaymentMeans>01</PaymentMeans>")),
    # «04 Transferencia» en la enumeración `PaymentMeansType` del esquema.
    ("BR-61",
     _PLAZO_FE.format("<PaymentMeans>04</PaymentMeans>"),
     _PLAZO_FE.format("<PaymentMeans>04</PaymentMeans><AccountToBeCredited>"
                      "<IBAN>ES7620770024003102575766</IBAN></AccountToBeCredited>")),
    ("BR-50",
     _PLAZO_FE.format("<PaymentMeans>04</PaymentMeans><AccountToBeCredited/>"),
     _PLAZO_FE.format("<PaymentMeans>04</PaymentMeans><AccountToBeCredited>"
                      "<AccountNumber>0049 0001 5</AccountNumber></AccountToBeCredited>")),
    ("BR-CO-04",
     "<Items><InvoiceLine><ItemDescription>Concepto</ItemDescription></InvoiceLine></Items>",
     _LINEA_FE.format("")),
]


@pytest.mark.parametrize("codigo, mala, buena", CASOS_FACTURAE, ids=[c[0] for c in CASOS_FACTURAE])
def test_facturae_cada_regla_salta_en_la_mala_y_calla_en_la_buena(codigo, mala, buena):
    assert codigo in salen(facturae(mala), SINTAXIS_FACTURAE)
    assert codigo not in salen(facturae(buena), SINTAXIS_FACTURAE)


def test_facturae_una_domiciliacion_no_pide_cuenta_de_abono():
    """Solo la transferencia pide cuenta: el recibo domiciliado (02) no."""
    raiz = facturae(_PLAZO_FE.format("<PaymentMeans>02</PaymentMeans>"))
    assert "BR-61" not in salen(raiz, SINTAXIS_FACTURAE)


def test_facturae_calla_lo_que_no_sabe_de_quien_es():
    """El número fiscal de Facturae no dice de qué clase es, y BR-CO-26 lo pide
    de tres clases concretas. Se calla, no acusa; y BR-CO-09 tampoco lo mira."""
    partes = (
        "<SellerParty><TaxIdentification><TaxIdentificationNumber>B12345678"
        "</TaxIdentificationNumber></TaxIdentification></SellerParty>"
    )
    assert not {"BR-CO-26", "BR-CO-09"} & salen(facturae("", partes), SINTAXIS_FACTURAE)


# --- Lo que las pruebas oficiales no montan ni en UBL ------------------------


def test_el_beneficiario_que_es_el_propio_vendedor():
    """Las dos vinculaciones lo tratan como BR-17: el beneficiario se declara
    cuando es otro, y uno que se llama igual que el vendedor no lo es."""
    raiz = ubl(
        "<cac:AccountingSupplierParty><cac:Party><cac:PartyName><cbc:Name>Vendedor SL</cbc:Name>"
        "</cac:PartyName></cac:Party></cac:AccountingSupplierParty>"
        "<cac:PayeeParty><cac:PartyName><cbc:Name>Vendedor SL</cbc:Name></cac:PartyName>"
        "</cac:PayeeParty>")
    incidencia = la(raiz, SINTAXIS_UBL, "BR-17")
    assert "propio vendedor" in incidencia.mensaje
    otro = ubl(
        "<cac:AccountingSupplierParty><cac:Party><cac:PartyName><cbc:Name>Vendedor SL</cbc:Name>"
        "</cac:PartyName></cac:Party></cac:AccountingSupplierParty>"
        "<cac:PayeeParty><cac:PartyName><cbc:Name>Factoring SA</cbc:Name></cac:PartyName>"
        "</cac:PayeeParty>")
    assert "BR-17" not in salen(otro, SINTAXIS_UBL)


def test_el_prefijo_de_grecia_es_el_y_no_gr():
    vendedor = ("<cac:AccountingSupplierParty><cac:Party><cac:PartyTaxScheme>"
                "<cbc:CompanyID>{}</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID>"
                "</cac:TaxScheme></cac:PartyTaxScheme></cac:Party></cac:AccountingSupplierParty>")
    assert "BR-CO-09" not in salen(ubl(vendedor.format("EL094259216")), SINTAXIS_UBL)
    assert "BR-CO-09" in salen(ubl(vendedor.format("XX094259216")), SINTAXIS_UBL)


def test_el_pago_fraccionado_mira_las_direcciones_y_no_el_origen_de_los_articulos():
    """Como la vinculación de CII. La de UBL mira todos los `IdentificationCode`
    y con eso cuenta el país de origen de un artículo, que no dice dónde está
    nadie."""
    raiz = ubl(
        "<cac:AccountingSupplierParty><cac:Party><cac:PostalAddress><cac:Country>"
        "<cbc:IdentificationCode>IT</cbc:IdentificationCode></cac:Country></cac:PostalAddress>"
        "</cac:Party></cac:AccountingSupplierParty>"
        "<cac:InvoiceLine><cbc:ID>1</cbc:ID><cac:Item><cac:OriginCountry>"
        "<cbc:IdentificationCode>CN</cbc:IdentificationCode></cac:OriginCountry>"
        "<cac:ClassifiedTaxCategory><cbc:ID>B</cbc:ID></cac:ClassifiedTaxCategory></cac:Item>"
        "</cac:InvoiceLine>")
    assert not {"BR-B-01", "BR-B-02"} & salen(raiz, SINTAXIS_UBL)


def test_sin_la_b_no_corre_ninguna_de_las_dos():
    raiz = ubl(
        "<cac:AccountingSupplierParty><cac:Party><cac:PostalAddress><cac:Country>"
        "<cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country></cac:PostalAddress>"
        "</cac:Party></cac:AccountingSupplierParty>"
        "<cac:TaxTotal><cac:TaxSubtotal><cac:TaxCategory><cbc:ID>S</cbc:ID></cac:TaxCategory>"
        "</cac:TaxSubtotal></cac:TaxTotal>")
    assert not {"BR-B-01", "BR-B-02"} & salen(raiz, SINTAXIS_UBL)


def test_la_b_de_un_descuento_tambien_cuenta():
    raiz = ubl(
        "<cac:AllowanceCharge><cbc:ChargeIndicator>false</cbc:ChargeIndicator>"
        "<cac:TaxCategory><cbc:ID>B</cbc:ID></cac:TaxCategory></cac:AllowanceCharge>"
        "<cac:InvoiceLine><cbc:ID>1</cbc:ID><cac:Item><cac:ClassifiedTaxCategory>"
        "<cbc:ID>S</cbc:ID></cac:ClassifiedTaxCategory></cac:Item></cac:InvoiceLine>")
    assert "BR-B-02" in salen(raiz, SINTAXIS_UBL)


def test_la_moneda_de_contabilidad_igual_a_la_de_la_factura_no_pide_otro_total():
    raiz = ubl("<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
               "<cbc:TaxCurrencyCode>EUR</cbc:TaxCurrencyCode>"
               "<cac:TaxTotal><cbc:TaxAmount currencyID=\"EUR\">21</cbc:TaxAmount></cac:TaxTotal>")
    assert "BR-53" not in salen(raiz, SINTAXIS_UBL)


def test_la_tarjeta_es_un_aviso_y_no_repite_el_numero():
    """BR-51 es `warning` en la norma. Y el informe no puede ser el sitio donde
    el número completo de una tarjeta acabe copiado otra vez."""
    raiz = ubl("<cac:PaymentMeans><cbc:PaymentMeansCode>48</cbc:PaymentMeansCode>"
               "<cac:CardAccount><cbc:PrimaryAccountNumberID>4111111111111111"
               "</cbc:PrimaryAccountNumberID></cac:CardAccount></cac:PaymentMeans>")
    incidencia = la(raiz, SINTAXIS_UBL, "BR-51")
    assert incidencia.gravedad == AVISO
    assert "4111111111111111" not in " ".join(
        str(x) for x in (incidencia.mensaje, incidencia.campo, incidencia.esperado, incidencia.encontrado))


def test_en_un_abono_las_lineas_se_llaman_de_otra_forma():
    raiz = ubl("<cac:CreditNoteLine><cbc:ID>7</cbc:ID><cac:Item/></cac:CreditNoteLine>", "CreditNote")
    incidencia = la(raiz, SINTAXIS_UBL, "BR-CO-04")
    assert incidencia.gravedad == ERROR
    assert "7" in incidencia.campo


def test_un_defecto_repetido_es_una_incidencia_que_dice_donde():
    """Tres descuentos sin motivo son un problema, no tres: sale una vez y
    nombra los tres."""
    ajuste = ("<cac:AllowanceCharge><cbc:ChargeIndicator>false</cbc:ChargeIndicator>"
              "<cbc:Amount>1</cbc:Amount></cac:AllowanceCharge>")
    quejas = [i for i in modelo.reglas(ubl(ajuste * 3), SINTAXIS_UBL) if i.codigo == "BR-33"]
    assert len(quejas) == 1
    assert all(f"descuento {n}" in quejas[0].campo for n in (1, 2, 3))


def test_los_de_linea_se_nombran_con_la_linea_detras():
    """El informe junta los sitios con comas: con la línea delante y otra coma,
    «línea 1, descuento 1, línea 2, descuento 1» no deja ver cuántos son."""
    ajuste = ("<cac:AllowanceCharge><cbc:ChargeIndicator>false</cbc:ChargeIndicator>"
              "<cbc:Amount>1</cbc:Amount></cac:AllowanceCharge>")
    raiz = ubl(f"<cac:InvoiceLine><cbc:ID>1</cbc:ID>{ajuste}</cac:InvoiceLine>"
               f"<cac:InvoiceLine><cbc:ID>2</cbc:ID>{ajuste}</cac:InvoiceLine>")
    assert la(raiz, SINTAXIS_UBL, "BR-42").campo == (
        "Descuentos de línea · descuento 1 de la línea 1, descuento 1 de la línea 2")


def test_un_nombre_en_blanco_no_es_un_nombre():
    """Donde las dos vinculaciones piden texto —`normalize-space(...) != ''`—,
    aquí también: espacios o un comentario no son un nombre. Donde piden que
    el elemento esté, basta con que esté, y el motivo de un descuento es de
    esas."""
    for dentro in ("   ", "<!-- nada -->"):
        raiz = ubl("<cac:TaxRepresentativeParty><cac:PartyName><cbc:Name>"
                   f"{dentro}</cbc:Name></cac:PartyName></cac:TaxRepresentativeParty>")
        assert "BR-18" in salen(raiz, SINTAXIS_UBL), dentro
    vacio = ubl("<cac:AllowanceCharge><cbc:ChargeIndicator>false</cbc:ChargeIndicator>"
                "<cbc:AllowanceChargeReason/></cac:AllowanceCharge>")
    assert "BR-33" not in salen(vacio, SINTAXIS_UBL)
