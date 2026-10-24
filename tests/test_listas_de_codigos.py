# -*- coding: utf-8 -*-
"""Los códigos que tienen que salir de una lista (BR-CL).

De dieciocho de las veintidós hay pruebas oficiales, de UBL, y se pasan en
`test_norma_oficial.py`. Lo que no prueban es el mapa de CII, EDIFACT y
Facturae, ni cuatro reglas enteras —el asunto de la nota, el motivo de la
exención, el esquema de la dirección electrónica y el del lugar de entrega—, ni
los bordes de la comparación. Eso es lo de aquí.

Cada caso malo tiene que sacar **esa** regla y ninguna otra: en CII el mismo
elemento sirve para el desglose y para la línea, y un campo que apunte al de al
lado se ve así y no con un «salta algo».
"""
from __future__ import annotations

import pytest
from lxml import etree

from tests.test_modelo import cii, edi, facturae, ubl
from validador import en16931, listas_de_codigos
from validador.codigos import codigos_del_paquete
from validador.incidencias import ERROR, NOTA
from validador.sintaxis import (
    SINTAXIS_CII,
    SINTAXIS_EDIFACT,
    SINTAXIS_FACTURAE,
    SINTAXIS_UBL,
)

TODAS = frozenset({
    "BR-CL-03", "BR-CL-04", "BR-CL-05", "BR-CL-06", "BR-CL-07", "BR-CL-08",
    "BR-CL-10", "BR-CL-11", "BR-CL-13", "BR-CL-14", "BR-CL-15", "BR-CL-16",
    "BR-CL-17", "BR-CL-18", "BR-CL-19", "BR-CL-20", "BR-CL-21", "BR-CL-22",
    "BR-CL-23", "BR-CL-24", "BR-CL-25", "BR-CL-26",
})


def salen(raiz, sintaxis) -> set[str]:
    return {i.codigo for i in listas_de_codigos.reglas(raiz, sintaxis)}


def la(raiz, sintaxis, codigo: str):
    return next(i for i in listas_de_codigos.reglas(raiz, sintaxis) if i.codigo == codigo)


# --- CII -------------------------------------------------------------------------


def cii_con_nota(asunto: str):
    """Una CII con cabecera: el asunto de la nota va en `ExchangedDocument`."""
    raiz = cii()
    cabecera = etree.fromstring(
        '<rsm:ExchangedDocument '
        'xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100" '
        'xmlns:ram="urn:un:unece:uncefact:data:standard:'
        'ReusableAggregateBusinessInformationEntity:100">'
        f"<ram:IncludedNote><ram:Content>Nota</ram:Content><ram:SubjectCode>{asunto}"
        "</ram:SubjectCode></ram:IncludedNote></rsm:ExchangedDocument>")
    raiz.insert(0, cabecera)
    return raiz


_AJUSTE = (
    "<ram:SpecifiedTradeAllowanceCharge><ram:ChargeIndicator><udt:Indicator>{}"
    "</udt:Indicator></ram:ChargeIndicator>{}</ram:SpecifiedTradeAllowanceCharge>"
)
_VENDEDOR = "<ram:SellerTradeParty>{}</ram:SellerTradeParty>"
_PRODUCTO = "<ram:SpecifiedTradeProduct>{}</ram:SpecifiedTradeProduct>"

# (código, dónde va, la plantilla con un hueco, el código malo, el bueno)
CASOS_CII = [
    ("BR-CL-03", "cobro",
     "<ram:SpecifiedTradeSettlementHeaderMonetarySummation>"
     '<ram:TaxTotalAmount currencyID="{}">21</ram:TaxTotalAmount>'
     "</ram:SpecifiedTradeSettlementHeaderMonetarySummation>", "EUX", "EUR"),
    ("BR-CL-04", "cobro", "<ram:InvoiceCurrencyCode>{}</ram:InvoiceCurrencyCode>", "EUX", "EUR"),
    ("BR-CL-05", "cobro", "<ram:TaxCurrencyCode>{}</ram:TaxCurrencyCode>", "EUX", "EUR"),
    # El 3 es el código de UBL para la fecha de la factura; en CII es el 5.
    ("BR-CL-06", "cobro",
     "<ram:ApplicableTradeTax><ram:DueDateTypeCode>{}</ram:DueDateTypeCode></ram:ApplicableTradeTax>",
     "3", "5"),
    ("BR-CL-07", "acuerdo",
     "<ram:AdditionalReferencedDocument><ram:IssuerAssignedID>1</ram:IssuerAssignedID>"
     "<ram:TypeCode>130</ram:TypeCode><ram:ReferenceTypeCode>{}</ram:ReferenceTypeCode>"
     "</ram:AdditionalReferencedDocument>", "XXA", "ABF"),
    ("BR-CL-10", "acuerdo", _VENDEDOR.format('<ram:GlobalID schemeID="{}">1</ram:GlobalID>'),
     "9999", "0088"),
    ("BR-CL-11", "acuerdo", _VENDEDOR.format(
        '<ram:SpecifiedLegalOrganization><ram:ID schemeID="{}">1</ram:ID>'
        "</ram:SpecifiedLegalOrganization>"), "9999", "0002"),
    ("BR-CL-13", "linea", _PRODUCTO.format(
        '<ram:DesignatedProductClassification><ram:ClassCode listID="{}">1</ram:ClassCode>'
        "</ram:DesignatedProductClassification>"), "XXX", "STS"),
    ("BR-CL-14", "acuerdo", _VENDEDOR.format(
        "<ram:PostalTradeAddress><ram:CountryID>{}</ram:CountryID></ram:PostalTradeAddress>"),
     "UK", "GB"),
    ("BR-CL-15", "linea", _PRODUCTO.format(
        "<ram:OriginTradeCountry><ram:ID>{}</ram:ID></ram:OriginTradeCountry>"), "UK", "GB"),
    ("BR-CL-16", "cobro",
     "<ram:SpecifiedTradeSettlementPaymentMeans><ram:TypeCode>{}</ram:TypeCode>"
     "</ram:SpecifiedTradeSettlementPaymentMeans>", "99", "58"),
    # El desglose es BR-CL-17, como en la norma, aunque el esquematrón de CII lo
    # mire con BR-CL-18 porque el elemento se llama igual que el de la línea.
    ("BR-CL-17", "cobro",
     "<ram:ApplicableTradeTax><ram:CategoryCode>{}</ram:CategoryCode></ram:ApplicableTradeTax>",
     "X", "S"),
    ("BR-CL-18", "linea",
     "<ram:SpecifiedLineTradeSettlement><ram:ApplicableTradeTax><ram:CategoryCode>{}"
     "</ram:CategoryCode></ram:ApplicableTradeTax></ram:SpecifiedLineTradeSettlement>", "X", "S"),
    ("BR-CL-19", "cobro", _AJUSTE.format("false", "<ram:ReasonCode>{}</ram:ReasonCode>"),
     "17", "95"),
    ("BR-CL-20", "cobro", _AJUSTE.format("true", "<ram:ReasonCode>{}</ram:ReasonCode>"),
     "SB", "AAA"),
    # Y el identificador del artículo no es de BR-CL-10, aunque sea un GlobalID.
    ("BR-CL-21", "linea", _PRODUCTO.format('<ram:GlobalID schemeID="{}">1</ram:GlobalID>'),
     "9999", "0160"),
    ("BR-CL-22", "cobro",
     "<ram:ApplicableTradeTax><ram:ExemptionReasonCode>{}</ram:ExemptionReasonCode>"
     "</ram:ApplicableTradeTax>", "VATEX-XX", "VATEX-EU-IC"),
    ("BR-CL-23", "linea",
     '<ram:SpecifiedLineTradeDelivery><ram:BilledQuantity unitCode="{}">1</ram:BilledQuantity>'
     "</ram:SpecifiedLineTradeDelivery>", "PCE", "H87"),
    ("BR-CL-24", "acuerdo",
     '<ram:AdditionalReferencedDocument><ram:AttachmentBinaryObject mimeCode="{}">eA==</ram:AttachmentBinaryObject>'
     "</ram:AdditionalReferencedDocument>", "application/xml", "application/pdf"),
    ("BR-CL-25", "acuerdo", _VENDEDOR.format(
        '<ram:URIUniversalCommunication><ram:URIID schemeID="{}">a@b.es</ram:URIID>'
        "</ram:URIUniversalCommunication>"), "XR01", "EM"),
    # Y el del lugar de entrega tampoco es de BR-CL-10.
    ("BR-CL-26", "entrega",
     '<ram:ShipToTradeParty><ram:GlobalID schemeID="{}">1</ram:GlobalID></ram:ShipToTradeParty>',
     "XR01", "0088"),
]


@pytest.mark.parametrize("codigo, donde, plantilla, malo, bueno", CASOS_CII,
                         ids=[c[0] for c in CASOS_CII])
def test_cii_cada_regla_salta_en_la_mala_y_calla_en_la_buena(codigo, donde, plantilla, malo, bueno):
    assert salen(cii(**{donde: plantilla.format(malo)}), SINTAXIS_CII) == {codigo}
    assert salen(cii(**{donde: plantilla.format(bueno)}), SINTAXIS_CII) == set()


def test_cii_el_asunto_de_la_nota_es_un_elemento():
    assert salen(cii_con_nota("XXX"), SINTAXIS_CII) == {"BR-CL-08"}
    assert salen(cii_con_nota("AAI"), SINTAXIS_CII) == set()
    # Uno de los 18 que la lista de UBL no tiene y la de CII sí.
    assert salen(cii_con_nota("BAT"), SINTAXIS_CII) == set()


def test_cii_la_unidad_del_precio_tambien():
    linea = ("<ram:SpecifiedLineTradeAgreement><ram:NetPriceProductTradePrice>"
             '<ram:ChargeAmount>1</ram:ChargeAmount><ram:BasisQuantity unitCode="PCE">1'
             "</ram:BasisQuantity></ram:NetPriceProductTradePrice></ram:SpecifiedLineTradeAgreement>")
    assert salen(cii(linea=linea), SINTAXIS_CII) == {"BR-CL-23"}


def test_todas_las_reglas_del_modulo_tienen_su_caso_en_cii():
    """Y la nota de los VATEX-ES, que tiene el suyo abajo."""
    del_modulo = {c.codigo for c in codigos_del_paquete() if c.modulo == "listas_de_codigos.py"}
    assert del_modulo == TODAS | {"IVA-VATEX-ES"}
    assert TODAS == {c[0] for c in CASOS_CII} | {"BR-CL-08"}


# --- UBL: lo que las pruebas oficiales no prueban ----------------------------------


def test_ubl_el_asunto_va_entre_almohadillas_y_son_tres_letras():
    for nota, sale in (("#XXX#Texto", True), ("#AAI#Texto", False), ("Sin asunto", False),
                       ("#AB#Texto", False), ("#ABCD#Texto", False), ("#XXX sin cerrar", False)):
        raiz = ubl(f"<cbc:Note>{nota}</cbc:Note>")
        assert (salen(raiz, SINTAXIS_UBL) == {"BR-CL-08"}) is sale, nota


def test_ubl_el_motivo_de_exencion_se_compara_en_mayusculas():
    def exencion(codigo):
        return ubl("<cac:TaxTotal><cac:TaxSubtotal><cac:TaxCategory><cbc:ID>E</cbc:ID>"
                   f"<cbc:TaxExemptionReasonCode>{codigo}</cbc:TaxExemptionReasonCode>"
                   "</cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>")
    assert salen(exencion("vatex-eu-ic"), SINTAXIS_UBL) == set()
    assert salen(exencion("VATEX-XX"), SINTAXIS_UBL) == {"BR-CL-22"}


def test_un_vatex_es_vale_y_lleva_la_nota_de_desde_cuando():
    """Los dieciocho de España entraron con la 1.3.17, y la 1.3.16 los rechaza."""
    def exencion(*codigos):
        return ubl("<cac:TaxTotal>" + "".join(
            "<cac:TaxSubtotal><cac:TaxCategory><cbc:ID>E</cbc:ID>"
            f"<cbc:TaxExemptionReasonCode>{c}</cbc:TaxExemptionReasonCode>"
            "</cac:TaxCategory></cac:TaxSubtotal>" for c in codigos) + "</cac:TaxTotal>")
    (nota,) = listas_de_codigos.reglas(exencion("VATEX-ES-IGIC11", "vatex-es-ipsi7"), SINTAXIS_UBL)
    assert nota.codigo == "IVA-VATEX-ES" and nota.gravedad == NOTA
    assert nota.encontrado == "VATEX-ES-IGIC11, vatex-es-ipsi7"
    assert "1.3.17" in nota.mensaje and "BR-CL-22" in nota.mensaje
    # Uno que no está en la lista es BR-CL-22, y no la nota.
    assert salen(exencion("VATEX-ES-20-1"), SINTAXIS_UBL) == {"BR-CL-22"}
    assert salen(exencion("VATEX-EU-IC"), SINTAXIS_UBL) == set()
    # En CII igual.
    raiz = cii(cobro="<ram:ApplicableTradeTax><ram:ExemptionReasonCode>VATEX-ES-N1"
                     "</ram:ExemptionReasonCode></ram:ApplicableTradeTax>")
    assert salen(raiz, SINTAXIS_CII) == {"IVA-VATEX-ES"}


def test_ubl_el_esquema_de_la_direccion_electronica_y_el_del_lugar_de_entrega():
    def direccion(esquema):
        return ubl("<cac:AccountingCustomerParty><cac:Party>"
                   f'<cbc:EndpointID schemeID="{esquema}">a@b.es</cbc:EndpointID>'
                   "</cac:Party></cac:AccountingCustomerParty>")
    def entrega(esquema):
        return ubl("<cac:Delivery><cac:DeliveryLocation>"
                   f'<cbc:ID schemeID="{esquema}">1</cbc:ID></cac:DeliveryLocation></cac:Delivery>')
    assert salen(direccion("XR01"), SINTAXIS_UBL) == {"BR-CL-25"}
    assert salen(direccion("9920"), SINTAXIS_UBL) == set()
    assert salen(entrega("XR01"), SINTAXIS_UBL) == {"BR-CL-26"}
    assert salen(entrega("0088"), SINTAXIS_UBL) == set()


def test_ubl_sepa_vale_para_el_vendedor_y_el_beneficiario_y_no_para_el_comprador():
    def parte(donde):
        dentro = ('<cac:Party><cac:PartyIdentification><cbc:ID schemeID="SEPA">ES12ZZZ</cbc:ID>'
                  "</cac:PartyIdentification></cac:Party>")
        if donde == "cac:PayeeParty":
            dentro = dentro.removeprefix("<cac:Party>").removesuffix("</cac:Party>")
        return ubl(f"<{donde}>{dentro}</{donde}>")
    assert salen(parte("cac:AccountingSupplierParty"), SINTAXIS_UBL) == set()
    assert salen(parte("cac:PayeeParty"), SINTAXIS_UBL) == set()
    assert salen(parte("cac:AccountingCustomerParty"), SINTAXIS_UBL) == {"BR-CL-10"}


def test_ubl_se_quitan_los_espacios_de_los_lados_y_no_los_de_dentro():
    def moneda(escrita):
        return ubl(f"<cbc:DocumentCurrencyCode>{escrita}</cbc:DocumentCurrencyCode>")
    assert salen(moneda(" EUR "), SINTAXIS_UBL) == set()
    assert salen(moneda("E UR"), SINTAXIS_UBL) == {"BR-CL-04"}
    # Y en minúsculas no es el código: solo el motivo de exención se compara así.
    assert salen(moneda("eur"), SINTAXIS_UBL) == {"BR-CL-04"}
    assert la(moneda(""), SINTAXIS_UBL, "BR-CL-04").encontrado == "(vacío)"


def test_ubl_el_tipo_de_adjunto_se_compara_tal_cual():
    def adjunto(tipo):
        return ubl("<cac:AdditionalDocumentReference><cbc:ID>1</cbc:ID><cac:Attachment>"
                   f'<cbc:EmbeddedDocumentBinaryObject mimeCode="{tipo}" filename="a">eA=='
                   "</cbc:EmbeddedDocumentBinaryObject></cac:Attachment>"
                   "</cac:AdditionalDocumentReference>")
    assert salen(adjunto("application/pdf"), SINTAXIS_UBL) == set()
    assert salen(adjunto(" application/pdf"), SINTAXIS_UBL) == {"BR-CL-24"}


def test_un_defecto_repetido_es_una_incidencia_que_dice_donde_y_no_repite_codigos():
    lineas = "".join(
        f'<cac:InvoiceLine><cbc:ID>{n}</cbc:ID><cbc:InvoicedQuantity unitCode="{u}">1'
        "</cbc:InvoicedQuantity></cac:InvoiceLine>"
        for n, u in ((1, "PCE"), (2, "PCE"), (3, "H87"), (4, "QQQ")))
    incidencias = listas_de_codigos.reglas(ubl(lineas), SINTAXIS_UBL)
    assert [i.codigo for i in incidencias] == ["BR-CL-23"]
    assert incidencias[0].campo.endswith("· línea 1, línea 2, línea 4")
    assert incidencias[0].encontrado == "PCE, QQQ"
    assert incidencias[0].gravedad == ERROR


def test_cada_ejemplo_del_informe_esta_en_su_lista():
    for codigo, _, cual, _, _, ejemplo in listas_de_codigos._REGLAS:
        if ejemplo is not None:
            assert ejemplo in listas_de_codigos.lista(cual, SINTAXIS_UBL), codigo


# --- EDIFACT -----------------------------------------------------------------------

CASOS_EDIFACT = [
    ("BR-CL-04", "CUX+2:{}:4'", "EUX", "EUR"),
    ("BR-CL-14", "NAD+SE+++Vendedor SL+Calle 2+Soria++42001+{}'", "UK", "ES"),
    ("BR-CL-17", "UNS+S'TAX+7+VAT+++:::21+{}'", "X", "S"),
    ("BR-CL-18", "LIN+1'TAX+7+VAT+++:::21+{}'", "X", "S"),
    # EANCOM escribe el motivo de un descuento en el C214, con códigos que no
    # son de UNCL 5189; se lee ahí igual que para BR-33.
    ("BR-CL-19", "ALC+A++++{}'", "TD", "95"),
    ("BR-CL-20", "ALC+C++++{}'", "G74", "AAA"),
    # PCE es la pieza de EANCOM; la de la recomendación 20 es H87.
    ("BR-CL-23", "LIN+1'QTY+47:10:{}'", "PCE", "H87"),
]


@pytest.mark.parametrize("codigo, plantilla, malo, bueno", CASOS_EDIFACT,
                         ids=[c[0] for c in CASOS_EDIFACT])
def test_edifact_cada_regla_salta_en_la_mala_y_calla_en_la_buena(codigo, plantilla, malo, bueno):
    assert salen(edi(plantilla.format(malo)), SINTAXIS_EDIFACT) == {codigo}
    assert salen(edi(plantilla.format(bueno)), SINTAXIS_EDIFACT) == set()


def test_edifact_calla_lo_que_escribe_con_otra_lista():
    """El esquema del identificador del artículo es de UNTDID 7143 —EN— y la
    fecha de devengo va en el cualificador del DTM."""
    assert SINTAXIS_EDIFACT.codigos_con_otra_lista == {"BR-CL-06", "BR-CL-21"}
    assert salen(edi("LIN+1++8412345000019:EN'DTM+3:20260601:102'"), SINTAXIS_EDIFACT) == set()


# --- Facturae ----------------------------------------------------------------------


def test_facturae_mira_la_moneda():
    def moneda(codigo):
        return facturae(f"<InvoiceIssueData><InvoiceCurrencyCode>{codigo}"
                        "</InvoiceCurrencyCode></InvoiceIssueData>")
    assert salen(moneda("EUX"), SINTAXIS_FACTURAE) == {"BR-CL-04"}
    assert salen(moneda("EUR"), SINTAXIS_FACTURAE) == set()


def test_facturae_calla_lo_que_escribe_con_sus_listas():
    """04 es transferencia, 01 es IVA y 01 son unidades: en Facturae."""
    raiz = facturae(
        "<TaxesOutputs><Tax><TaxTypeCode>01</TaxTypeCode></Tax></TaxesOutputs>"
        "<Items><InvoiceLine><UnitOfMeasure>01</UnitOfMeasure>"
        "<TaxesOutputs><Tax><TaxTypeCode>01</TaxTypeCode></Tax></TaxesOutputs></InvoiceLine></Items>"
        "<PaymentDetails><Installment><PaymentMeans>04</PaymentMeans></Installment></PaymentDetails>")
    assert salen(raiz, SINTAXIS_FACTURAE) == set()
    assert SINTAXIS_FACTURAE.codigos_con_otra_lista == {"BR-CL-16", "BR-CL-17", "BR-CL-18", "BR-CL-23"}


# --- Que el validador las corre ------------------------------------------------------


def test_el_validador_las_corre_en_las_cuatro_sintaxis():
    documentos = {
        "UBL": etree.tostring(ubl("<cbc:DocumentCurrencyCode>EUX</cbc:DocumentCurrencyCode>")),
        "CII": etree.tostring(cii(cobro="<ram:InvoiceCurrencyCode>EUX</ram:InvoiceCurrencyCode>")),
        "EDIFACT": (
            "UNB+UNOC:3+EMISOR+RECEPTOR+260819:1200+1'UNH+1+INVOIC:D:96A:UN'"
            "BGM+380+F-1'CUX+2:EUX:4'UNT+4+1'UNZ+1+1'").encode("utf-8"),
        "Facturae": etree.tostring(facturae(
            "<InvoiceIssueData><InvoiceCurrencyCode>EUX</InvoiceCurrencyCode>"
            "</InvoiceIssueData>").getroottree()),
    }
    for nombre, datos in documentos.items():
        codigos = {i.codigo for i in en16931.validar(datos).incidencias}
        assert "BR-CL-04" in codigos, nombre
