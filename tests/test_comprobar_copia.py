"""El comprobador de copia fiel: un Facturae y su copia UBL en el mismo lote.

El original es `ejemplos/fe-0001.xml`, sin tocar. La copia se escribe aquí a mano
siguiendo la tabla de `copia_fiel.py`, y cada prueba le cambia una sola cosa: si
la copia intacta no saliera limpia, ninguna de las demás probaría nada.
"""

import re
from pathlib import Path

import pytest
from lxml import etree

from validador import comprobar_copia, copia_fiel, factura
from validador.formato import detectar, parser
from validador.incidencias import AVISO, NOTA

ORIGINAL = Path(__file__).resolve().parents[1] / "ejemplos" / "fe-0001.xml"

COPIA = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:ID>FE0001</cbc:ID>
  <cbc:CopyIndicator>true</cbc:CopyIndicator>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:DueDate>2026-04-01</cbc:DueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PostalAddress><cbc:StreetName>Calle Mayor 1</cbc:StreetName><cbc:CityName>Madrid</cbc:CityName><cbc:PostalZone>28013</cbc:PostalZone><cbc:CountrySubentity>Madrid</cbc:CountrySubentity><cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Talleres Ejemplo SL</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PostalAddress><cbc:StreetName>Gran Via 2</cbc:StreetName><cbc:CityName>Madrid</cbc:CityName><cbc:PostalZone>28013</cbc:PostalZone><cbc:CountrySubentity>Madrid</cbc:CountrySubentity><cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>ESB85905495</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Clientes Ejemplo SL</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingCustomerParty>
  <cac:PaymentMeans><cbc:PaymentMeansCode>30</cbc:PaymentMeansCode><cac:PayeeFinancialAccount><cbc:ID>ES91 2100 0418 4502 0005 1332</cbc:ID></cac:PayeeFinancialAccount></cac:PaymentMeans>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">121.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="C62">2</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cac:Item><cbc:Name>Revision anual del vehiculo</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>
    </cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">50.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</Invoice>
"""

LINEA_DOS = """<cac:InvoiceLine><cbc:ID>2</cbc:ID>
  <cbc:InvoicedQuantity unitCode="C62">1</cbc:InvoicedQuantity>
  <cbc:LineExtensionAmount currencyID="EUR">0.00</cbc:LineExtensionAmount>
  <cac:Item><cbc:Name>Otra</cbc:Name>
    <cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>
  </cac:Item></cac:InvoiceLine></Invoice>"""


def original() -> str:
    return ORIGINAL.read_text(encoding="utf-8")


def leidas(xml: str):
    raiz = etree.fromstring(xml.encode("utf-8"), parser=parser())
    return comprobar_copia.extraer_de(raiz, detectar(xml))


def comparar(copia: str = COPIA, de_original: str | None = None):
    lecturas = leidas(de_original or original()) + leidas(copia)
    return comprobar_copia.reglas_de_lote(lecturas)


def avisos(copia: str = COPIA, de_original: str | None = None) -> dict:
    return {i.codigo: i for i in comparar(copia, de_original) if i.gravedad == AVISO}


def test_la_copia_intacta_no_da_ningun_aviso():
    """La prueba de la que dependen todas las demás."""
    salidas = comparar()
    assert [i.codigo for i in salidas] == ["COPIA-COMPARADA"]
    assert salidas[0].gravedad == NOTA
    assert "1 sin diferencias y 0 con" in salidas[0].mensaje


def test_la_nota_dice_lo_que_no_se_compara_y_que_no_valida():
    mensaje = comparar()[0].mensaje
    assert "No se compara el total a pagar" in mensaje
    assert "no dice que la copia sea válida" in mensaje
    assert "no publica la correspondencia" in mensaje


@pytest.mark.parametrize("cambio, codigo, se_lee", [
    (("<cbc:IssueDate>2026-03-02", "<cbc:IssueDate>2026-03-03"), "COPIA-DATOS", "BT-2"),
    (("<cbc:DocumentCurrencyCode>EUR", "<cbc:DocumentCurrencyCode>USD"), "COPIA-DATOS", "BT-5"),
    (("ESB85905495", "ESA00000000"), "COPIA-DATOS", "BT-48"),
    (("Clientes Ejemplo SL", "Otro Cliente SL"), "COPIA-DATOS", "BT-44"),
    (("Talleres Ejemplo SL", "Otro Taller SL"), "COPIA-DATOS", "BT-27"),
    (("<cbc:CopyIndicator>true</cbc:CopyIndicator>", ""), "COPIA-DATOS", "BT-ES-1"),
    (("<cbc:CopyIndicator>true", "<cbc:CopyIndicator>false"), "COPIA-DATOS", "BT-ES-1"),
    (('<cbc:TaxExclusiveAmount currencyID="EUR">100.00', '<cbc:TaxExclusiveAmount currencyID="EUR">100.01'),
     "COPIA-IMPORTES", "BT-109"),
    (('<cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>',
      '<cbc:TaxAmount currencyID="EUR">20.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>'),
     "COPIA-IMPORTES", "BT-110"),
    (('<cbc:TaxInclusiveAmount currencyID="EUR">121.00', '<cbc:TaxInclusiveAmount currencyID="EUR">120.00'),
     "COPIA-IMPORTES", "BT-112"),
    (('<cbc:TaxableAmount currencyID="EUR">100.00', '<cbc:TaxableAmount currencyID="EUR">90.00'),
     "COPIA-DESGLOSE", "base 100,00"),
    (('<cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>',
      '<cbc:Percent>10</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>'),
     "COPIA-DESGLOSE", "IVA al 21%"),
    (('<cbc:InvoicedQuantity unitCode="C62">2', '<cbc:InvoicedQuantity unitCode="C62">3'),
     "COPIA-LINEAS", "BT-129"),
    (('</cbc:InvoicedQuantity>\n    <cbc:LineExtensionAmount currencyID="EUR">100.00',
      '</cbc:InvoicedQuantity>\n    <cbc:LineExtensionAmount currencyID="EUR">99.00'),
     "COPIA-LINEAS", "BT-131"),
    (('<cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>',
      '<cbc:Percent>10</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>'),
     "COPIA-LINEAS", "BT-152"),
    (('<cbc:PriceAmount currencyID="EUR">50.00', '<cbc:PriceAmount currencyID="EUR">60.00'),
     "COPIA-LINEAS", "BT-146"),
    (("Calle Mayor 1", "Calle Menor 9"), "COPIA-PARTES", "calle del vendedor (BT-35)"),
    (("Gran Via 2", "Gran Via 3"), "COPIA-PARTES", "calle del comprador (BT-50)"),
    (("<cbc:CityName>Madrid", "<cbc:CityName>Alcorcón"), "COPIA-PARTES", "BT-37"),
    (("<cbc:PostalZone>28013", "<cbc:PostalZone>28014"), "COPIA-PARTES", "BT-38"),
    (("<cbc:CountrySubentity>Madrid", "<cbc:CountrySubentity>Ávila"), "COPIA-PARTES", "BT-39"),
    (("<cbc:IdentificationCode>ES", "<cbc:IdentificationCode>PT"), "COPIA-PARTES", "BT-40"),
    (("<cbc:StreetName>Calle Mayor 1</cbc:StreetName>", ""), "COPIA-PARTES", "nada en la copia"),
    (("<cbc:DueDate>2026-04-01", "<cbc:DueDate>2026-05-01"), "COPIA-PAGO", "BT-9"),
    (("  <cbc:DueDate>2026-04-01</cbc:DueDate>\n", ""), "COPIA-PAGO", "BT-9"),
    (("<cbc:PaymentMeansCode>30", "<cbc:PaymentMeansCode>42"), "COPIA-PAGO", "BT-81"),
    (("ES91 2100 0418 4502 0005 1332", "ES79 2100 0813 6101 2345 6789"), "COPIA-PAGO", "BT-84"),
    (("Revision anual del vehiculo", "Otra cosa"), "COPIA-TEXTOS", "BT-153"),
    (("</Invoice>", LINEA_DOS), "COPIA-LINEAS", "1 línea en el original y 2 en la copia"),
])
def test_cada_cambio_en_la_copia_se_detecta(cambio, codigo, se_lee):
    viejo, nuevo = cambio
    assert viejo in COPIA, "la prueba cambia algo que la copia no lleva"
    salidas = avisos(COPIA.replace(viejo, nuevo, 1))
    assert set(salidas) == {codigo}
    assert se_lee in salidas[codigo].mensaje
    assert salidas[codigo].gravedad == AVISO


def test_medio_centimo_de_redondeo_no_es_una_diferencia():
    """Facturae admite más decimales que la copia, y redondear no es equivocarse."""
    con_decimales = original().replace(
        "<TotalGrossAmountBeforeTaxes>100.00", "<TotalGrossAmountBeforeTaxes>100.004", 1)
    assert not avisos(de_original=con_decimales)


def test_un_centimo_si_es_una_diferencia():
    copia = COPIA.replace('<cbc:TaxInclusiveAmount currencyID="EUR">121.00',
                          '<cbc:TaxInclusiveAmount currencyID="EUR">121.01')
    assert "BT-112" in avisos(copia)["COPIA-IMPORTES"].mensaje


RETENIDO = "<TotalTaxesWithheld>15.00</TotalTaxesWithheld>"


def con_retencion() -> str:
    """El original con una retención de 15: su total, 106; el de la copia, 121."""
    texto = original().replace("<TotalTaxesWithheld>0.00</TotalTaxesWithheld>", RETENIDO, 1)
    return texto.replace("<InvoiceTotal>121.00", "<InvoiceTotal>106.00", 1)


def con_retenciones_en_la_copia(copia: str = COPIA, suma: str = "15.00") -> str:
    return copia.replace(
        "<cac:TaxTotal>",
        '<cac:WithholdingTaxTotal><cbc:TaxAmount currencyID="EUR">'
        f"{suma}</cbc:TaxAmount></cac:WithholdingTaxTotal><cac:TaxTotal>", 1)


def test_el_total_con_retencion_no_es_el_de_facturae():
    """BT-112 no resta la retención: el total de la copia sigue siendo 121."""
    assert not avisos(con_retenciones_en_la_copia(), con_retencion())


def test_el_total_de_facturae_copiado_tal_cual_se_diagnostica():
    copia = con_retenciones_en_la_copia().replace(
        '<cbc:TaxInclusiveAmount currencyID="EUR">121.00',
        '<cbc:TaxInclusiveAmount currencyID="EUR">106.00')
    mensaje = avisos(copia, con_retencion())["COPIA-IMPORTES"].mensaje
    assert "BT-112" in mensaje
    assert "resta las retenciones" in mensaje


def test_un_original_que_no_resta_la_retencion_no_acusa_a_la_copia():
    """Medido el 01-11-2026 con las Facturae públicas de Invopop.

    Sumar la retención a un `InvoiceTotal` que no la restó daba 136 y acusaba a
    una copia correcta, con 121, de haber copiado el total tal cual. BT-112 es
    base más cuotas: se calcula de ahí. Que el original no cuadre consigo mismo
    es cosa de FE-TOTAL.
    """
    de_original = original().replace("<TotalTaxesWithheld>0.00</TotalTaxesWithheld>", RETENIDO, 1)
    assert not avisos(con_retenciones_en_la_copia(), de_original)


def test_bt_112_vale_tambien_como_suma_de_los_dos_ya_redondeados():
    """BR-CO-15 suma BT-109 y BT-110, que en la copia ya llevan dos decimales."""
    de_original = original().replace(
        "<TotalGrossAmountBeforeTaxes>100.00", "<TotalGrossAmountBeforeTaxes>100.004", 1
    ).replace("<TotalTaxOutputs>21.00", "<TotalTaxOutputs>21.004", 1)
    assert not avisos(de_original=de_original)
    redondeo_junto = COPIA.replace('<cbc:TaxInclusiveAmount currencyID="EUR">121.00',
                                   '<cbc:TaxInclusiveAmount currencyID="EUR">121.01')
    assert not avisos(redondeo_junto, de_original)


def test_la_retencion_que_falta_en_la_copia_se_detecta():
    assert "BT-ES-17" in avisos(de_original=con_retencion())["COPIA-IMPORTES"].mensaje


def test_una_retencion_en_la_copia_que_el_original_no_tiene_se_detecta():
    assert "BT-ES-17" in avisos(con_retenciones_en_la_copia())["COPIA-IMPORTES"].mensaje


def con_recargo(texto: str = "") -> str:
    """El original con un recargo del 5,2 %: 5,20 sobre la misma base."""
    texto = texto or original()
    texto = texto.replace(
        "<TaxAmount><TotalAmount>21.00</TotalAmount></TaxAmount>",
        "<TaxAmount><TotalAmount>21.00</TotalAmount></TaxAmount>"
        "<EquivalenceSurcharge>5.20</EquivalenceSurcharge>"
        "<EquivalenceSurchargeAmount><TotalAmount>5.20</TotalAmount>"
        "</EquivalenceSurchargeAmount>", 1)
    texto = texto.replace("<TotalTaxOutputs>21.00", "<TotalTaxOutputs>26.20", 1)
    return texto.replace("<InvoiceTotal>121.00", "<InvoiceTotal>126.20", 1)


def copia_con_recargo(cuota: str = "5.20", base: str = "100.00") -> str:
    entrada = (
        f'<cac:TaxSubtotal><cbc:TaxableAmount currencyID="EUR">{base}</cbc:TaxableAmount>'
        f'<cbc:TaxAmount currencyID="EUR">{cuota}</cbc:TaxAmount>'
        "<cac:TaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>5.2</cbc:Percent>"
        "<cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>"
        "</cac:TaxSubtotal></cac:TaxTotal>")
    copia = COPIA.replace("</cac:TaxTotal>", entrada, 1)
    copia = copia.replace('<cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>',
                          '<cbc:TaxAmount currencyID="EUR">26.20</cbc:TaxAmount>\n    <cac:TaxSubtotal>', 1)
    return copia.replace('<cbc:TaxInclusiveAmount currencyID="EUR">121.00',
                         '<cbc:TaxInclusiveAmount currencyID="EUR">126.20')


def test_el_recargo_es_una_entrada_aparte_con_la_categoria_n():
    assert not avisos(copia_con_recargo(), con_recargo())


def test_el_recargo_con_otra_cuota_se_detecta():
    salidas = avisos(copia_con_recargo(cuota="5.00"), con_recargo())
    assert "recargo al 5,2%" in salidas["COPIA-DESGLOSE"].mensaje


def test_la_base_del_recargo_no_se_compara():
    """La orden no explica cuál es, y no se le inventa una."""
    assert not avisos(copia_con_recargo(base="1.00"), con_recargo())


def test_el_recargo_que_falta_en_la_copia_se_detecta():
    assert "la copia no lo lleva" in avisos(de_original=con_recargo())["COPIA-DESGLOSE"].mensaje


def al_cero(categoria: str) -> tuple[str, str]:
    """Una factura al 0 %, con la categoría que se pida en la copia."""
    de_original = original()
    for viejo, nuevo in (("<TaxRate>21.00", "<TaxRate>0.00"),
                         ("<TotalAmount>21.00", "<TotalAmount>0.00"),
                         ("<TotalTaxOutputs>21.00", "<TotalTaxOutputs>0.00"),
                         ("<InvoiceTotal>121.00", "<InvoiceTotal>100.00")):
        de_original = de_original.replace(viejo, nuevo)
    copia = (COPIA.replace("<cbc:ID>S</cbc:ID><cbc:Percent>21", f"<cbc:ID>{categoria}</cbc:ID><cbc:Percent>0")
             .replace('currencyID="EUR">21.00', 'currencyID="EUR">0.00')
             .replace('<cbc:TaxInclusiveAmount currencyID="EUR">121.00',
                      '<cbc:TaxInclusiveAmount currencyID="EUR">100.00'))
    return de_original, copia


@pytest.mark.parametrize("categoria", ["E", "O", "Z", "AE", "K", "G"])
def test_al_cero_no_se_compara_la_categoria(categoria):
    """El código de impuesto de Facturae no la dice: cualquiera de las seis vale."""
    de_original, copia = al_cero(categoria)
    assert not avisos(copia, de_original)


def test_al_cero_la_base_si_se_compara():
    de_original, copia = al_cero("E")
    copia = copia.replace('<cbc:TaxableAmount currencyID="EUR">100.00',
                          '<cbc:TaxableAmount currencyID="EUR">90.00')
    assert "al 0 %" in avisos(copia, de_original)["COPIA-DESGLOSE"].mensaje


@pytest.mark.parametrize("codigo, categoria", [("03", "L"), ("02", "M")])
def test_igic_e_ipsi_con_su_categoria_no_dan_aviso(codigo, categoria):
    de_original = original().replace("<TaxTypeCode>01", f"<TaxTypeCode>{codigo}")
    copia = COPIA.replace("<cbc:ID>S</cbc:ID>", f"<cbc:ID>{categoria}</cbc:ID>")
    assert not avisos(copia, de_original)


def test_igic_copiado_como_iva_se_detecta():
    de_original = original().replace("<TaxTypeCode>01", "<TaxTypeCode>03")
    assert "IGIC al 21%" in avisos(de_original=de_original)["COPIA-DESGLOSE"].mensaje


def con_otro_impuesto() -> str:
    """Un impuesto que no es IVA, IGIC ni IPSI: en la copia va como cargo."""
    return original().replace("<TaxesOutputs>\n        <Tax>\n          <TaxTypeCode>01",
                              "<TaxesOutputs>\n        <Tax>\n          <TaxTypeCode>05", 1)


def test_otros_impuestos_solo_comparan_datos_y_lineas():
    de_original = con_otro_impuesto()
    assert "<TaxTypeCode>05" in de_original
    copia = COPIA.replace('<cbc:TaxExclusiveAmount currencyID="EUR">100.00',
                          '<cbc:TaxExclusiveAmount currencyID="EUR">50.00')
    salidas = comparar(copia, de_original)
    assert not [i for i in salidas if i.gravedad == AVISO]
    assert "solo se comparan los datos y las líneas: FE0001" in salidas[0].mensaje
    # Y los datos siguen comparándose, para que no se calle del todo.
    otra_fecha = copia.replace("2026-03-02", "2026-03-09")
    assert set(avisos(otra_fecha, de_original)) == {"COPIA-DATOS"}


def test_el_separador_del_numero_es_una_nota_y_no_una_diferencia():
    """Medido el 01-11-2026 leyendo otro conversor: `gobl.ubl` junta con un guion.

    Como nadie dice cómo se juntan, un aviso por cada factura con serie acusaba
    a ese conversor de algo que ninguna norma le pide.
    """
    salidas = comparar(COPIA.replace("<cbc:ID>FE0001", "<cbc:ID>FE-0001"))
    assert {i.codigo: i.gravedad for i in salidas} == {
        "COPIA-COMPARADA": NOTA, "COPIA-SEPARADOR": NOTA}
    assert "1 sin diferencias" in salidas[0].mensaje
    nota = next(i for i in salidas if i.codigo == "COPIA-SEPARADOR")
    assert "FE-0001" in nota.mensaje and "FE0001" in nota.mensaje


def test_el_numero_sin_serie_empareja_y_lo_dice():
    salidas = avisos(COPIA.replace("<cbc:ID>FE0001", "<cbc:ID>0001"))
    assert "no identifican la misma factura" in salidas["COPIA-DATOS"].mensaje


def test_el_numero_sin_serie_no_se_empareja_si_hay_dos_que_encajan():
    """Con la serie A y la B del mismo número, adivinar sería comparar con otra."""
    otra_serie = original().replace("<InvoiceSeriesCode>FE", "<InvoiceSeriesCode>XX")
    lecturas = (leidas(original()) + leidas(otra_serie)
                + leidas(COPIA.replace("<cbc:ID>FE0001", "<cbc:ID>0001")))
    assert [i.codigo for i in comprobar_copia.reglas_de_lote(lecturas)] == ["COPIA-SIN-PAREJA"]


def test_otro_emisor_no_se_empareja():
    copia = COPIA.replace("ESB12345674", "ESA58818501")
    salidas = comparar(copia)
    assert [i.codigo for i in salidas] == ["COPIA-SIN-PAREJA"]
    assert "FE0001" in salidas[0].mensaje


def test_el_prefijo_de_pais_del_nif_no_separa_la_pareja():
    copia = COPIA.replace("ESB12345674", "B12345674")
    assert [i.codigo for i in comparar(copia)] == ["COPIA-COMPARADA"]


def test_el_prefijo_de_otro_pais_tampoco_separa_la_pareja():
    """Medido el 01-11-2026: Facturae escribe 123456789012 y la copia, con
    prefijo, FR123456789012. Se quedaban sin pareja, y sin comparar."""
    de_original = original().replace("<TaxIdentificationNumber>ESB12345674", "<TaxIdentificationNumber>123456789012", 1)
    copia = COPIA.replace("ESB12345674", "FR123456789012")
    assert [i.codigo for i in comparar(copia, de_original)] == ["COPIA-COMPARADA"]


def test_un_nif_espanol_no_se_toma_por_un_prefijo():
    """Una letra y un número no son un país: A12345674 no es 12345674."""
    copia = COPIA.replace("ESB12345674", "12345674")
    de_original = original().replace("<TaxIdentificationNumber>ESB12345674", "<TaxIdentificationNumber>B12345674", 1)
    assert [i.codigo for i in comparar(copia, de_original)] == ["COPIA-SIN-PAREJA"]


def test_el_nif_del_comprador_con_otro_prefijo_no_es_una_diferencia():
    de_original = original().replace("<TaxIdentificationNumber>ESB85905495", "<TaxIdentificationNumber>123456789", 1)
    copia = COPIA.replace("ESB85905495", "FR123456789")
    assert not avisos(copia, de_original)


def en_negativo() -> str:
    """El original como rectificativa en negativo, que es como lo escribe Facturae."""
    texto = original()
    for viejo, nuevo in (("<TotalGrossAmountBeforeTaxes>100.00", "<TotalGrossAmountBeforeTaxes>-100.00"),
                         ("<TotalTaxOutputs>21.00", "<TotalTaxOutputs>-21.00"),
                         ("<InvoiceTotal>121.00", "<InvoiceTotal>-121.00"),
                         ("<TotalAmount>100.00", "<TotalAmount>-100.00"),
                         ("<TotalAmount>21.00", "<TotalAmount>-21.00"),
                         ("<Quantity>2.00", "<Quantity>-2.00"),
                         ("<GrossAmount>100.00", "<GrossAmount>-100.00")):
        texto = texto.replace(viejo, nuevo)
    return texto


def test_un_abono_en_positivo_es_la_copia_de_un_original_en_negativo():
    """Medido el 01-11-2026: `gobl.ubl` invierte los signos en un abono, el 381."""
    abono = COPIA.replace("<cbc:InvoiceTypeCode>380", "<cbc:InvoiceTypeCode>381")
    assert not avisos(abono, en_negativo())


def test_un_abono_con_otro_importe_se_sigue_detectando():
    abono = COPIA.replace("<cbc:InvoiceTypeCode>380", "<cbc:InvoiceTypeCode>381").replace(
        '<cbc:TaxExclusiveAmount currencyID="EUR">100.00', '<cbc:TaxExclusiveAmount currencyID="EUR">90.00')
    assert "BT-109" in avisos(abono, en_negativo())["COPIA-IMPORTES"].mensaje


def test_una_factura_en_positivo_de_un_original_en_negativo_si_es_una_diferencia():
    """Sin ser un abono, el signo cambiado es otro importe."""
    assert set(avisos(de_original=en_negativo())) == {"COPIA-IMPORTES", "COPIA-DESGLOSE", "COPIA-LINEAS"}


def test_una_retencion_en_el_desglose_se_llama_por_su_impuesto():
    """Sin categoría, una entrada IRPF al 15 % se anunciaba como IVA al 15 %."""
    copia = COPIA.replace("</cac:TaxTotal>", (
        '<cac:TaxSubtotal><cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>'
        '<cbc:TaxAmount currencyID="EUR">15.00</cbc:TaxAmount><cac:TaxCategory><cbc:Percent>15</cbc:Percent>'
        "<cac:TaxScheme><cbc:ID>IRPF</cbc:ID></cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>"), 1)
    assert "IRPF al 15%" in avisos(copia)["COPIA-DESGLOSE"].mensaje


def test_una_retencion_en_el_desglose_no_dice_que_el_original_no_la_tiene():
    """Medido con la salida de `gobl`: el IRPF sí está en el original, como retención.

    Decir "está en la copia y no en el original" era falso, y mandaba a buscar un
    error donde no estaba.
    """
    copia = COPIA.replace("</cac:TaxTotal>", (
        '<cac:TaxSubtotal><cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>'
        '<cbc:TaxAmount currencyID="EUR">15.00</cbc:TaxAmount><cac:TaxCategory><cbc:Percent>15</cbc:Percent>'
        "<cac:TaxScheme><cbc:ID>IRPF</cbc:ID></cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>"))
    mensaje = avisos(con_retenciones_en_la_copia(copia), con_retencion())["COPIA-DESGLOSE"].mensaje
    assert "IRPF al 15%" in mensaje
    assert "y no en el original" not in mensaje
    assert "es una retención" in mensaje and "BT-ES-17" in mensaje


def test_un_ubl_sin_indicador_y_sin_pareja_no_dice_nada():
    """Un lote de facturas sin relación no tiene por qué oír hablar de copias."""
    copia = COPIA.replace("<cbc:ID>FE0001", "<cbc:ID>OTRA").replace(
        "<cbc:CopyIndicator>true</cbc:CopyIndicator>", "")
    assert comparar(copia) == []


def test_un_lote_sin_facturae_o_sin_ubl_no_dice_nada():
    assert comprobar_copia.reglas_de_lote(leidas(COPIA)) == []
    assert comprobar_copia.reglas_de_lote(leidas(original())) == []


def test_varias_facturas_de_un_facturae_se_comparan_cada_una():
    """Un Facturae son varias facturas, y la copia de la segunda es otro fichero."""
    texto = original()
    inicio = texto.index("<Invoice>")
    fin = texto.index("</Invoice>") + len("</Invoice>")
    segunda = texto[inicio:fin].replace("<InvoiceNumber>0001", "<InvoiceNumber>0002")
    dos = texto[:fin] + segunda + texto[fin:]
    copia_2 = COPIA.replace("<cbc:ID>FE0001", "<cbc:ID>FE0002").replace("2026-03-02", "2026-03-09")
    salidas = comprobar_copia.reglas_de_lote(leidas(dos) + leidas(COPIA) + leidas(copia_2))
    assert "Se han comparado 2 facturas" in salidas[0].mensaje
    assert [i.codigo for i in salidas[1:]] == ["COPIA-DATOS"]
    assert "FE0002" in salidas[1].mensaje


def test_avisa_de_la_factura_que_se_queda_sin_copia():
    texto = original()
    inicio = texto.index("<Invoice>")
    fin = texto.index("</Invoice>") + len("</Invoice>")
    segunda = texto[inicio:fin].replace("<InvoiceNumber>0001", "<InvoiceNumber>0002")
    salidas = comprobar_copia.reglas_de_lote(leidas(texto[:fin] + segunda + texto[fin:]) + leidas(COPIA))
    assert "1 factura de Facturae se queda sin copia" in salidas[0].mensaje


class TestEnElLote:
    """Por el camino de verdad: dos ficheros en disco y el lote entero."""

    def _lote(self, tmp_path, copia: str = COPIA):
        camino_original = tmp_path / "original.xml"
        camino_original.write_bytes(ORIGINAL.read_bytes())
        camino_copia = tmp_path / "copia.xml"
        camino_copia.write_text(copia, encoding="utf-8")
        return factura.validar_lote([camino_original, camino_copia])

    def test_sale_entre_las_cruzadas(self, tmp_path):
        lote = self._lote(tmp_path)
        assert "COPIA-COMPARADA" in {i.codigo for i in lote.cruzadas}

    def test_el_aviso_nombra_los_dos_ficheros(self, tmp_path):
        lote = self._lote(tmp_path, COPIA.replace("2026-03-02", "2026-03-09"))
        aviso = next(i for i in lote.cruzadas if i.codigo == "COPIA-DATOS")
        assert aviso.ficheros == ("original.xml", "copia.xml")

    def test_una_copia_y_su_original_no_son_un_duplicado(self, tmp_path):
        """Medido el 01-11-2026: una copia perfecta junto a su original daba
        CU-16, un error, por llevar el mismo número. Es lo que tiene que llevar."""
        lote = self._lote(tmp_path)
        assert not [i.codigo for i in lote.cruzadas if i.codigo.startswith("CU-")]

    def test_sin_el_indicador_no_es_una_copia_y_se_sigue_quejando(self, tmp_path):
        """La salida no puede ser para cualquiera que comparta número."""
        lote = self._lote(tmp_path, COPIA.replace(
            "<cbc:CopyIndicator>true</cbc:CopyIndicator>", ""))
        assert "CU-16" in {i.codigo for i in lote.cruzadas}

    def test_dos_copias_con_el_mismo_numero_se_siguen_quejando(self, tmp_path):
        una = tmp_path / "una.xml"
        una.write_text(COPIA, encoding="utf-8")
        otra = tmp_path / "otra.xml"
        otra.write_text(COPIA, encoding="utf-8")
        lote = factura.validar_lote([una, otra])
        assert [i for i in lote.cruzadas if i.codigo.startswith("CU-")]

    def test_un_fichero_que_no_se_puede_leer_no_tumba_el_lote(self, tmp_path):
        roto = tmp_path / "roto.xml"
        roto.write_text("<esto no es xml", encoding="utf-8")
        lote = factura.validar_lote([roto, ORIGINAL])
        assert not {i.codigo for i in lote.cruzadas} & {"COPIA-COMPARADA", "COPIA-SIN-PAREJA"}


def con_datos_de_parte(de_original: str = "") -> str:
    """El original, con los contactos y descuentos que el de ejemplo no lleva."""
    return (de_original or original()).replace(
        "</AddressInSpain>",
        "</AddressInSpain><ContactDetails><Telephone>+34 910 000 000</Telephone>"
        "<ElectronicMail>hola@ejemplo.es</ElectronicMail></ContactDetails>", 1)


def test_el_contacto_se_compara_y_sin_espacios():
    de_original = con_datos_de_parte()
    contacto = ("<cac:Contact><cbc:Telephone>+34910000000</cbc:Telephone>"
                "<cbc:ElectronicMail>HOLA@ejemplo.es</cbc:ElectronicMail></cac:Contact>"
                "<cac:PartyTaxScheme><cbc:CompanyID>ESB12345674")
    bien = COPIA.replace("<cac:PartyTaxScheme><cbc:CompanyID>ESB12345674", contacto, 1)
    assert not avisos(bien, de_original)
    mal = bien.replace("+34910000000", "+34910000001")
    assert "teléfono del vendedor (BT-42)" in avisos(mal, de_original)["COPIA-PARTES"].mensaje
    sin_correo = bien.replace("<cbc:ElectronicMail>HOLA@ejemplo.es</cbc:ElectronicMail>", "")
    assert "BT-43" in avisos(sin_correo, de_original)["COPIA-PARTES"].mensaje


@pytest.mark.parametrize("viejo, nuevo, se_lee", [
    ("<cbc:CityName>Madrid", "<cbc:CityName>Alcorcón", "BT-52"),
    ("<cbc:PostalZone>28013", "<cbc:PostalZone>28014", "BT-53"),
    ("<cbc:CountrySubentity>Madrid", "<cbc:CountrySubentity>Ávila", "BT-54"),
    ("<cbc:IdentificationCode>ES", "<cbc:IdentificationCode>PT", "BT-55"),
])
def test_los_campos_del_comprador_no_se_confunden_con_los_del_vendedor(viejo, nuevo, se_lee):
    # El último de cada uno, que es el del comprador: los dos dicen lo mismo aquí.
    cabeza, _, cola = COPIA.rpartition(viejo)
    assert se_lee in avisos(cabeza + nuevo + cola)["COPIA-PARTES"].mensaje


def test_la_calle_repartida_en_dos_lineas_es_la_misma():
    """Medido con `gobl`, que parte "Calle Pradillo, 42, 3" y no pierde nada."""
    de_original = original().replace("Calle Mayor 1", "Calle Mayor, 1, 3")
    repartida = COPIA.replace(
        "<cbc:StreetName>Calle Mayor 1</cbc:StreetName>",
        "<cbc:StreetName>Calle Mayor 1</cbc:StreetName>"
        "<cbc:AdditionalStreetName>3</cbc:AdditionalStreetName>")
    assert not avisos(repartida, de_original)
    assert "COPIA-PARTES" in avisos(de_original=de_original)


def test_de_fuera_de_espana_no_se_compara_lo_que_hay_que_partir():
    """El código postal y la población van juntos, y nadie dice por dónde se parten."""
    de_original = original().replace(
        """<AddressInSpain>
          <Address>Calle Mayor 1</Address>
          <PostCode>28013</PostCode>
          <Town>Madrid</Town>
          <Province>Madrid</Province>
          <CountryCode>ESP</CountryCode>
        </AddressInSpain>""",
        """<OverseasAddress>
          <Address>Calle Mayor 1</Address>
          <PostCodeAndTown>1000-001 Lisboa</PostCodeAndTown>
          <Province>Madrid</Province>
          <CountryCode>PRT</CountryCode>
        </OverseasAddress>""")
    copia = COPIA.replace("<cbc:IdentificationCode>ES", "<cbc:IdentificationCode>PT", 1)
    assert "OverseasAddress" in de_original
    assert not avisos(copia, de_original)
    assert "BT-35" in avisos(copia.replace("Calle Mayor 1", "Otra"), de_original)["COPIA-PARTES"].mensaje


def test_un_pais_retirado_de_iso_no_se_compara():
    de_original = original().replace("<CountryCode>ESP", "<CountryCode>ANT", 1)
    assert not avisos(de_original=de_original)


@pytest.mark.parametrize("de_facturae, de_copia", [
    ("01", "10"), ("02", "49"), ("02", "59"), ("04", "30"), ("04", "58"),
    ("11", "20"), ("19", "48"), ("19", "54"), ("19", "55"),
])
def test_los_medios_que_la_tabla_sostiene_no_dan_aviso(de_facturae, de_copia):
    de_original = original().replace("<PaymentMeans>04", f"<PaymentMeans>{de_facturae}")
    assert not avisos(COPIA.replace("<cbc:PaymentMeansCode>30", f"<cbc:PaymentMeansCode>{de_copia}"),
                      de_original)


@pytest.mark.parametrize("de_facturae, de_copia", [("04", "4"), ("19", "19"), ("04", "04")])
def test_el_digito_de_facturae_copiado_se_llama_por_su_nombre(de_facturae, de_copia):
    de_original = original().replace("<PaymentMeans>04", f"<PaymentMeans>{de_facturae}")
    copia = COPIA.replace("<cbc:PaymentMeansCode>30", f"<cbc:PaymentMeansCode>{de_copia}")
    assert "copiado tal cual" in avisos(copia, de_original)["COPIA-PAGO"].mensaje


def test_un_medio_que_la_tabla_no_sostiene_no_se_compara():
    de_original = original().replace("<PaymentMeans>04", "<PaymentMeans>13")
    assert not avisos(COPIA.replace("<cbc:PaymentMeansCode>30", "<cbc:PaymentMeansCode>1"), de_original)


def varios_vencimientos() -> str:
    return original().replace(
        "</Installment>",
        "</Installment><Installment><InstallmentDueDate>2026-05-01</InstallmentDueDate>"
        "<InstallmentAmount>60.00</InstallmentAmount><PaymentMeans>04</PaymentMeans>"
        "<AccountToBeCredited><IBAN>ES7921000813610123456789</IBAN></AccountToBeCredited>"
        "</Installment>")


def test_con_varios_vencimientos_vale_cualquiera_y_ninguno_otro():
    """La copia solo admite uno, y elegir cuál es de quien copia (COPIA-VENCIMIENTOS)."""
    de_original = varios_vencimientos()
    assert not avisos(de_original=de_original)
    assert not avisos(COPIA.replace("<cbc:DueDate>2026-04-01", "<cbc:DueDate>2026-05-01"), de_original)
    assert "BT-9" in avisos(COPIA.replace("<cbc:DueDate>2026-04-01", "<cbc:DueDate>2026-06-01"),
                            de_original)["COPIA-PAGO"].mensaje


def test_sin_pago_en_el_original_no_se_mira_el_de_la_copia():
    de_original = original()
    inicio, fin = de_original.index("<PaymentDetails>"), de_original.index("</PaymentDetails>")
    de_original = de_original[:inicio] + de_original[fin + len("</PaymentDetails>"):]
    assert not avisos(de_original=de_original)


def test_el_vencimiento_de_una_nota_de_abono_va_en_el_medio_de_pago():
    """CreditNote no tiene DueDate en la cabecera."""
    copia = COPIA.replace("  <cbc:DueDate>2026-04-01</cbc:DueDate>\n", "").replace(
        "<cbc:PaymentMeansCode>30</cbc:PaymentMeansCode>",
        "<cbc:PaymentMeansCode>30</cbc:PaymentMeansCode><cbc:PaymentDueDate>2026-04-01</cbc:PaymentDueDate>")
    assert not avisos(copia)


def test_el_precio_de_varias_unidades_se_lleva_a_una():
    """BT-149: 100 por cada 2 es el precio de 50 del original."""
    copia = COPIA.replace(
        '<cbc:PriceAmount currencyID="EUR">50.00</cbc:PriceAmount>',
        '<cbc:PriceAmount currencyID="EUR">100.00</cbc:PriceAmount>'
        '<cbc:BaseQuantity unitCode="C62">2</cbc:BaseQuantity>')
    assert not avisos(copia)


DESCUENTO_F = ("<TotalCost>100.00</TotalCost><DiscountsAndRebates><Discount>"
               "<DiscountReason>Pronto pago</DiscountReason><DiscountAmount>0.00</DiscountAmount>"
               "</Discount></DiscountsAndRebates>")
DESCUENTO_U = ("<cac:AllowanceCharge><cbc:ChargeIndicator>false</cbc:ChargeIndicator>"
               "<cbc:AllowanceChargeReason>{}</cbc:AllowanceChargeReason>"
               '<cbc:Amount currencyID="EUR">0.00</cbc:Amount></cac:AllowanceCharge>')


def con_descuento() -> str:
    return original().replace("<TotalCost>100.00</TotalCost>", DESCUENTO_F)


def copia_con_motivo(motivo: str) -> str:
    return COPIA.replace("<cac:Item><cbc:Name>",
                         DESCUENTO_U.format(motivo) + "<cac:Item><cbc:Name>")


def test_el_motivo_del_descuento_se_compara():
    assert not avisos(copia_con_motivo("PRONTO PAGO"), con_descuento())
    assert "línea 1, motivo (BT-139)" in avisos(copia_con_motivo("Otro"), con_descuento())["COPIA-TEXTOS"].mensaje
    assert "BT-139" in avisos(de_original=con_descuento())["COPIA-TEXTOS"].mensaje


def test_un_cargo_de_mas_en_la_copia_no_es_una_diferencia_de_textos():
    """Un impuesto que no es IVA va en la copia como cargo, y en el original no es un cargo."""
    cargo = DESCUENTO_U.format("IAE").replace(">false<", ">true<")
    assert "COPIA-TEXTOS" not in avisos(COPIA.replace("<cac:Item><cbc:Name>", cargo + "<cac:Item><cbc:Name>"))


def test_el_motivo_general_se_compara_en_el_documento():
    de_original = original().replace(
        "<PaymentDetails>",
        "<GeneralDiscounts><Discount><DiscountReason>Rappel</DiscountReason>"
        "<DiscountAmount>0.00</DiscountAmount></Discount></GeneralDiscounts><PaymentDetails>")
    assert "motivo (BT-97)" in avisos(de_original=de_original)["COPIA-TEXTOS"].mensaje
    bien = COPIA.replace("<cac:TaxTotal>", DESCUENTO_U.format("Rappel") + "<cac:TaxTotal>", 1)
    assert not avisos(bien, de_original)


def test_un_texto_largo_se_corta_en_el_aviso():
    largo = "Revision " * 40
    de_original = original().replace("Revision anual del vehiculo", largo)
    mensaje = avisos(de_original=de_original)["COPIA-TEXTOS"].mensaje
    assert largo not in mensaje and "..." in mensaje


def test_la_nota_ya_no_dice_que_no_se_comparan():
    mensaje = comparar()[0].mensaje
    assert "la dirección, el pago ni los textos" not in mensaje
    assert "vencimiento" in mensaje


# Las filas que la tabla da por iguales y no se miraban: el 01-11-2026, diez copias
# rotas en ellas pasaban sin un aviso.

EMISION = "<IssueDate>2026-03-02</IssueDate>"
TIPO_DE_FACTURA = "<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"
MONEDA = "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
PERIODO_F = ("<InvoicingPeriod><StartDate>2026-01-01</StartDate>"
             "<EndDate>2026-01-31</EndDate></InvoicingPeriod>")
PERIODO_U = ("<cac:InvoicePeriod><cbc:StartDate>2026-01-01</cbc:StartDate>"
             "<cbc:EndDate>2026-01-31</cbc:EndDate></cac:InvoicePeriod>")
RECTIFICADA_F = ("<Corrective>{}<ReasonCode>01</ReasonCode></Corrective>"
                 "</InvoiceHeader>")
RECTIFICADA_U = ("<cac:BillingReference><cac:InvoiceDocumentReference><cbc:ID>{}</cbc:ID>{}"
                 "</cac:InvoiceDocumentReference></cac:BillingReference>")


def con_operacion(fecha: str = "2026-02-15") -> str:
    return original().replace(EMISION, f"{EMISION}<OperationDate>{fecha}</OperationDate>", 1)


def copia_con_operacion(fecha: str = "2026-02-15") -> str:
    return COPIA.replace(TIPO_DE_FACTURA,
                         f"<cbc:TaxPointDate>{fecha}</cbc:TaxPointDate>{TIPO_DE_FACTURA}")


def test_la_fecha_de_la_operacion_se_compara():
    assert not avisos(copia_con_operacion(), con_operacion())
    assert "BT-7" in avisos(de_original=con_operacion())["COPIA-DATOS"].mensaje
    assert "BT-7" in avisos(copia_con_operacion())["COPIA-DATOS"].mensaje
    assert "BT-7" in avisos(copia_con_operacion("2026-02-16"), con_operacion())["COPIA-DATOS"].mensaje


def test_sin_fecha_aparte_la_operacion_es_la_de_expedicion():
    assert not avisos(copia_con_operacion("2026-03-02"))
    assert not avisos(de_original=con_operacion("2026-03-02"))


def test_una_fecha_de_expedicion_cambiada_no_sale_tambien_como_la_de_la_operacion():
    mensaje = avisos(COPIA.replace("<cbc:IssueDate>2026-03-02", "<cbc:IssueDate>2026-03-03"))
    assert "BT-7" not in mensaje["COPIA-DATOS"].mensaje


def en_otra_moneda_del_iva() -> str:
    return original().replace("<TaxCurrencyCode>EUR", "<TaxCurrencyCode>USD", 1)


def copia_con_moneda_del_iva(moneda: str) -> str:
    return COPIA.replace(MONEDA, f"{MONEDA}<cbc:TaxCurrencyCode>{moneda}</cbc:TaxCurrencyCode>")


def test_la_moneda_del_iva_se_compara():
    assert "BT-6" in avisos(copia_con_moneda_del_iva("USD"))["COPIA-DATOS"].mensaje
    assert "BT-6" in avisos(de_original=en_otra_moneda_del_iva())["COPIA-DATOS"].mensaje
    assert not avisos(copia_con_moneda_del_iva("USD"), en_otra_moneda_del_iva())


def test_la_moneda_del_iva_que_es_la_de_la_factura_no_hace_falta_escribirla():
    """Facturae obliga a escribirla y copiarla rompe la copia: `COPIA-MONEDA-DEL-IVA`."""
    assert "<TaxCurrencyCode>EUR" in original()
    assert not avisos()
    assert not avisos(copia_con_moneda_del_iva("EUR"))


def test_un_facturae_sin_moneda_del_iva_la_tiene_en_la_de_la_factura():
    """Antes de la 3.2 el campo no existía."""
    de_original = original().replace("<TaxCurrencyCode>EUR</TaxCurrencyCode>", "", 1)
    assert not avisos(copia_con_moneda_del_iva("EUR"), de_original)
    assert "BT-6" in avisos(copia_con_moneda_del_iva("USD"), de_original)["COPIA-DATOS"].mensaje


def test_una_moneda_cambiada_no_sale_tambien_como_la_del_iva():
    mensaje = avisos(COPIA.replace(MONEDA, MONEDA.replace("EUR", "USD")))["COPIA-DATOS"].mensaje
    assert "BT-5" in mensaje and "BT-6" not in mensaje


def con_periodo() -> str:
    return original().replace(EMISION, EMISION + PERIODO_F, 1)


def copia_con_periodo(periodo: str = PERIODO_U) -> str:
    return COPIA.replace("<cac:AccountingSupplierParty>", periodo + "<cac:AccountingSupplierParty>")


@pytest.mark.parametrize("cambio, termino", [
    (("2026-01-01", "2026-01-02"), "BT-73"),
    (("2026-01-31", "2026-01-30"), "BT-74"),
])
def test_el_periodo_de_facturacion_se_compara(cambio, termino):
    assert not avisos(copia_con_periodo(), con_periodo())
    assert termino in avisos(copia_con_periodo(PERIODO_U.replace(*cambio)),
                             con_periodo())["COPIA-DATOS"].mensaje
    assert termino in avisos(de_original=con_periodo())["COPIA-DATOS"].mensaje
    assert termino in avisos(copia_con_periodo())["COPIA-DATOS"].mensaje


def rectificativa(de_bloque: str) -> str:
    return original().replace("</InvoiceHeader>", RECTIFICADA_F.format(de_bloque), 1)


NUMERO_RECTIFICADO = ("<InvoiceNumber>0009</InvoiceNumber><InvoiceSeriesCode>FE</InvoiceSeriesCode>"
                      "{}<InvoiceIssueDate>2026-01-10</InvoiceIssueDate>")


def copia_con_rectificada(numero: str = "FE0009", fecha: str = "2026-01-10") -> str:
    fecha = f"<cbc:IssueDate>{fecha}</cbc:IssueDate>" if fecha else ""
    return COPIA.replace("<cac:AccountingSupplierParty>",
                         RECTIFICADA_U.format(numero, fecha) + "<cac:AccountingSupplierParty>")


def test_la_factura_rectificada_y_su_fecha_se_comparan():
    de_original = rectificativa(NUMERO_RECTIFICADO.format(""))
    assert not avisos(copia_con_rectificada(), de_original)
    assert "BT-25" in avisos(de_original=de_original)["COPIA-DATOS"].mensaje
    assert "BT-25" in avisos(copia_con_rectificada("FE0008"), de_original)["COPIA-DATOS"].mensaje
    assert "BT-26" in avisos(copia_con_rectificada(fecha="2026-01-11"), de_original)["COPIA-DATOS"].mensaje
    assert "BT-26" in avisos(copia_con_rectificada(fecha=""), de_original)["COPIA-DATOS"].mensaje


def test_la_rectificada_con_otro_separador_es_la_misma():
    de_original = rectificativa(NUMERO_RECTIFICADO.format(""))
    assert not avisos(copia_con_rectificada("FE-0009"), de_original)


def test_la_rectificada_sin_la_serie_no_es_la_misma():
    de_original = rectificativa(NUMERO_RECTIFICADO.format(""))
    assert "BT-25" in avisos(copia_con_rectificada("0009"), de_original)["COPIA-DATOS"].mensaje


def test_rectificar_un_periodo_no_lleva_numero_y_no_se_exige():
    """El criterio 03: sin número no hay BT-25 que comparar, y la copia puede escribir otro."""
    de_original = rectificativa("<InvoiceIssueDate>2026-01-10</InvoiceIssueDate>")
    assert not avisos(de_original=de_original)
    assert not avisos(copia_con_rectificada(), de_original)


def test_la_factura_asociada_ya_viene_junta_y_sin_fecha():
    de_original = original().replace(
        "</Items>", "</Items><AdditionalData><RelatedInvoice>FE0009</RelatedInvoice></AdditionalData>", 1)
    assert "<RelatedInvoice>" in de_original
    assert "BT-25" in avisos(de_original=de_original)["COPIA-DATOS"].mensaje
    assert not avisos(copia_con_rectificada(), de_original)


def copia_con_total(etiqueta: str, valor: str) -> str:
    return COPIA.replace('<cbc:TaxExclusiveAmount currencyID="EUR">',
                         f'<cbc:{etiqueta} currencyID="EUR">{valor}</cbc:{etiqueta}>'
                         '<cbc:TaxExclusiveAmount currencyID="EUR">', 1)


def con_general(grupo: str, elemento: str, razon: str, importe: str, *total: str) -> str:
    """Un descuento o cargo general, y su suma si se le da. Sin tocar el resto."""
    suma = f"<{total[0]}>{importe}</{total[0]}>" if total else ""
    return original().replace(
        "<PaymentDetails>",
        f"<{grupo}><{elemento}><{elemento}Reason>{razon}</{elemento}Reason>"
        f"<{elemento}Amount>{importe}</{elemento}Amount></{elemento}></{grupo}><PaymentDetails>", 1,
    ).replace("<TotalGrossAmountBeforeTaxes>", f"{suma}<TotalGrossAmountBeforeTaxes>", 1)


def test_la_suma_de_las_lineas_se_compara():
    copia = COPIA.replace('<cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>\n    <cbc:TaxExclusive',
                          '<cbc:LineExtensionAmount currencyID="EUR">90.00</cbc:LineExtensionAmount>\n    <cbc:TaxExclusive')
    assert copia != COPIA
    assert "BT-106" in avisos(copia)["COPIA-IMPORTES"].mensaje


def tres_lineas_con_tercios() -> tuple[str, str]:
    """Tres netos de 0,334: Facturae suma 1,002 y la copia, con BR-CO-10, 0,99."""
    una = ("<InvoiceLine><ItemDescription>Revision anual del vehiculo</ItemDescription>"
           "<Quantity>1</Quantity><UnitPriceWithoutTax>0.334</UnitPriceWithoutTax>"
           "<TotalCost>0.334</TotalCost><GrossAmount>0.334</GrossAmount></InvoiceLine>")
    de_original = original()
    inicio, fin = de_original.index("<Items>"), de_original.index("</Items>")
    de_original = de_original[:inicio] + "<Items>" + una * 3 + de_original[fin:]
    de_original = de_original.replace("<TotalGrossAmount>100.00", "<TotalGrossAmount>1.002")
    linea = ('<cac:InvoiceLine><cbc:ID>1</cbc:ID><cbc:InvoicedQuantity unitCode="C62">1</cbc:InvoicedQuantity>'
             '<cbc:LineExtensionAmount currencyID="EUR">0.33</cbc:LineExtensionAmount>'
             "<cac:Item><cbc:Name>Revision anual del vehiculo</cbc:Name></cac:Item></cac:InvoiceLine>")
    inicio = COPIA.index("<cac:InvoiceLine>")
    copia = COPIA[:inicio] + linea * 3 + "</Invoice>\n"
    copia = copia.replace('<cbc:LineExtensionAmount currencyID="EUR">100.00', '<cbc:LineExtensionAmount currencyID="EUR">0.99', 1)
    return de_original, copia


def test_la_suma_de_las_lineas_ya_redondeadas_no_es_una_diferencia():
    de_original, copia = tres_lineas_con_tercios()
    assert "COPIA-IMPORTES" not in avisos(copia, de_original)
    # Y otra suma cualquiera lo sigue siendo.
    otra = copia.replace('<cbc:LineExtensionAmount currencyID="EUR">0.99', '<cbc:LineExtensionAmount currencyID="EUR">0.98', 1)
    assert "BT-106" in avisos(otra, de_original)["COPIA-IMPORTES"].mensaje


@pytest.mark.parametrize("etiqueta, termino", [
    ("AllowanceTotalAmount", "BT-107"), ("ChargeTotalAmount", "BT-108"),
])
def test_un_total_general_de_mas_en_la_copia_se_detecta(etiqueta, termino):
    assert termino in avisos(copia_con_total(etiqueta, "5.00"))["COPIA-IMPORTES"].mensaje
    assert not avisos(copia_con_total(etiqueta, "0.00"))


@pytest.mark.parametrize("grupo, elemento, etiqueta, de_total, termino, del_motivo", [
    ("GeneralDiscounts", "Discount", "AllowanceTotalAmount", "TotalGeneralDiscounts", "BT-107", "false"),
    ("GeneralSurcharges", "Charge", "ChargeTotalAmount", "TotalGeneralSurcharges", "BT-108", "true"),
])
def test_los_totales_generales_con_y_sin_la_suma_en_facturae(
    grupo, elemento, etiqueta, de_total, termino, del_motivo,
):
    motivo = DESCUENTO_U.format("Rappel").replace(">false<", f">{del_motivo}<")
    bien = copia_con_total(etiqueta, "0.00").replace("<cac:TaxTotal>", motivo + "<cac:TaxTotal>", 1)
    con_suma = con_general(grupo, elemento, "Rappel", "0.00", de_total)
    assert not avisos(bien, con_suma)
    con_diez = con_general(grupo, elemento, "Rappel", "10.00", de_total)
    assert f"{termino}): 10,00" in avisos(bien, con_diez)["COPIA-IMPORTES"].mensaje
    # Sin la suma, que es opcional en Facturae, la suma es la de sus importes.
    sin_suma = con_general(grupo, elemento, "Rappel", "10.00")
    assert f"{termino}): 10,00" in avisos(bien, sin_suma)["COPIA-IMPORTES"].mensaje
    bien_diez = bien.replace(f'<cbc:{etiqueta} currencyID="EUR">0.00', f'<cbc:{etiqueta} currencyID="EUR">10.00')
    assert termino not in " ".join(i.mensaje for i in avisos(bien_diez, sin_suma).values())


def test_un_total_general_sin_sus_descuentos_no_se_da_por_bueno():
    """Sin sumandos, la suma de los redondeados es cero: no puede valer por el total."""
    de_original = original().replace("<TotalGrossAmountBeforeTaxes>",
                                     "<TotalGeneralDiscounts>10.00</TotalGeneralDiscounts>"
                                     "<TotalGrossAmountBeforeTaxes>", 1)
    assert "BT-107" in avisos(de_original=de_original)["COPIA-IMPORTES"].mensaje


DE_LINEA = ('<cac:AllowanceCharge><cbc:ChargeIndicator>{}</cbc:ChargeIndicator>{}'
            '<cbc:AllowanceChargeReason>Motivo</cbc:AllowanceChargeReason>'
            '<cbc:Amount currencyID="EUR">{}</cbc:Amount></cac:AllowanceCharge>')


def con_de_linea(*bloques: str) -> str:
    return original().replace("<TotalCost>100.00</TotalCost>",
                              "<TotalCost>100.00</TotalCost>" + "".join(bloques))


def descuento_f(*importes: str) -> str:
    return "<DiscountsAndRebates>" + "".join(
        f"<Discount><DiscountReason>Motivo</DiscountReason><DiscountAmount>{i}</DiscountAmount></Discount>"
        for i in importes) + "</DiscountsAndRebates>"


def cargo_f(importe: str, tipo: str = "") -> str:
    tipo = f"<ChargeRate>{tipo}</ChargeRate>" if tipo else ""
    return (f"<Charges><Charge><ChargeReason>Motivo</ChargeReason>{tipo}"
            f"<ChargeAmount>{importe}</ChargeAmount></Charge></Charges>")


def copia_de_linea(*bloques: str) -> str:
    return COPIA.replace("<cac:Item><cbc:Name>", "".join(bloques) + "<cac:Item><cbc:Name>")


def test_los_descuentos_de_la_linea_se_comparan():
    de_original = con_de_linea(descuento_f("10.00"))
    bien = copia_de_linea(DE_LINEA.format("false", "", "10.00"))
    assert not avisos(bien, de_original)
    mensaje = avisos(copia_de_linea(DE_LINEA.format("false", "", "9.00")), de_original)["COPIA-LINEAS"].mensaje
    assert "línea 1, descuentos (BT-136): 10,00 en el original y 9,00 en la copia" in mensaje
    assert "BT-136" in avisos(de_original=de_original)["COPIA-LINEAS"].mensaje
    assert "BT-136" in avisos(bien)["COPIA-LINEAS"].mensaje


def test_dos_descuentos_juntados_en_uno_son_los_mismos():
    de_original = con_de_linea(descuento_f("6.00", "4.00"))
    assert not avisos(copia_de_linea(DE_LINEA.format("false", "", "10.00")), de_original)


def test_los_descuentos_ya_redondeados_no_son_una_diferencia():
    de_original = con_de_linea(descuento_f("0.334", "0.334", "0.334"))
    tres = DE_LINEA.format("false", "", "0.33") * 3
    assert not avisos(copia_de_linea(tres), de_original)


def test_los_cargos_de_la_linea_se_comparan():
    de_original = con_de_linea(cargo_f("10.00"))
    assert not avisos(copia_de_linea(DE_LINEA.format("true", "", "10.00")), de_original)
    mensaje = avisos(copia_de_linea(DE_LINEA.format("true", "", "9.00")), de_original)["COPIA-LINEAS"].mensaje
    assert "línea 1, cargos (BT-141): 10,00 en el original y 9,00 en la copia" in mensaje
    assert "BT-141" in avisos(copia_de_linea(DE_LINEA.format("true", "", "9.00")))["COPIA-LINEAS"].mensaje


def test_un_descuento_escrito_como_cargo_no_cuadra():
    de_original = con_de_linea(descuento_f("10.00"))
    mensaje = avisos(copia_de_linea(DE_LINEA.format("true", "", "10.00")), de_original)["COPIA-LINEAS"].mensaje
    assert "BT-136" in mensaje and "BT-141" in mensaje


def test_el_porcentaje_del_cargo_se_compara_y_no_el_del_descuento():
    con_tipo = "<cbc:MultiplierFactorNumeric>{}</cbc:MultiplierFactorNumeric>"
    de_original = con_de_linea(cargo_f("10.00", "5.00"))
    assert not avisos(copia_de_linea(DE_LINEA.format("true", con_tipo.format("5"), "10.00")), de_original)
    otro = copia_de_linea(DE_LINEA.format("true", con_tipo.format("7"), "10.00"))
    assert "BT-143): 5" in avisos(otro, de_original)["COPIA-LINEAS"].mensaje
    assert "BT-143" in avisos(copia_de_linea(DE_LINEA.format("true", "", "10.00")), de_original)["COPIA-LINEAS"].mensaje
    # Un cero no es un porcentaje que se haya perdido.
    assert not avisos(copia_de_linea(DE_LINEA.format("true", "", "10.00")), con_de_linea(cargo_f("10.00", "0.00")))
    # El de un descuento de la copia no vale por el del cargo.
    con_los_dos = copia_de_linea(DE_LINEA.format("true", "", "10.00"),
                                 DE_LINEA.format("false", con_tipo.format("5"), "0.00"))
    assert "BT-143" in avisos(con_los_dos, de_original)["COPIA-LINEAS"].mensaje
    # BT-138 es del descuento, y el anexo no lo recoge.
    assert not avisos(copia_de_linea(DE_LINEA.format("false", con_tipo.format("7"), "10.00")),
                      con_de_linea(descuento_f("10.00")))


def test_un_abono_compara_descuentos_y_cargos_sin_el_signo():
    de_original = en_negativo().replace("</TotalCost>", "</TotalCost>" + descuento_f("-10.00"), 1)
    copia = COPIA.replace("<cbc:InvoiceTypeCode>380", "<cbc:InvoiceTypeCode>381")
    bien = copia.replace("<cac:Item><cbc:Name>", DE_LINEA.format("false", "", "10.00") + "<cac:Item><cbc:Name>")
    assert "COPIA-LINEAS" not in avisos(bien, de_original)
    assert "BT-136" in avisos(bien.replace(">10.00</cbc:Amount>", ">9.00</cbc:Amount>"), de_original)["COPIA-LINEAS"].mensaje


def copia_con_impuesto_en_la_linea(neto: str = "121.00") -> str:
    return (COPIA.replace("<cac:Item><cbc:Name>", DE_LINEA.format("true", "", "21.00") + "<cac:Item><cbc:Name>")
            .replace('</cbc:InvoicedQuantity>\n    <cbc:LineExtensionAmount currencyID="EUR">100.00',
                     f'</cbc:InvoicedQuantity>\n    <cbc:LineExtensionAmount currencyID="EUR">{neto}'))


def test_un_impuesto_escrito_como_cargo_de_la_linea_va_en_el_neto():
    """La fila de la tabla lo dice, y hasta el 01-11-2026 esa copia salía acusada."""
    assert not avisos(copia_con_impuesto_en_la_linea(), con_otro_impuesto())
    assert "línea 1, neto (BT-131): 121,00" in avisos(
        copia_con_impuesto_en_la_linea("122.00"), con_otro_impuesto())["COPIA-LINEAS"].mensaje


def test_sin_impuestos_de_otro_tipo_un_cargo_no_explica_el_neto():
    assert "BT-131" in avisos(copia_con_impuesto_en_la_linea())["COPIA-LINEAS"].mensaje


def test_con_otros_impuestos_no_se_miran_los_totales_nuevos():
    otro = con_otro_impuesto()
    assert not avisos(copia_con_total("ChargeTotalAmount", "21.00"), otro)
    assert not avisos(copia_con_total("AllowanceTotalAmount", "5.00"), otro)


def test_ninguna_fila_igual_de_la_tabla_se_queda_sin_mirar():
    """Hasta el 01-11-2026 las que faltaban estaban en una lista del README."""
    fuente = Path(comprobar_copia.__file__).read_text(encoding="utf-8")
    sin_mirar = {
        termino
        for fila in copia_fiel.CORRESPONDENCIAS if fila.efecto == copia_fiel.IGUAL
        for termino in re.findall(r"BT-(?:ES-)?\d+", fila.destino)
        if not re.search(rf"{termino}\b", fuente)
    }
    assert not sin_mirar


def test_la_nota_dice_lo_nuevo_que_se_compara():
    mensaje = comparar()[0].mensaje
    for dicho in ("fechas de expedición y de operación", "moneda del IVA", "periodo de facturación",
                  "factura rectificada", "suma de las líneas", "descuentos y cargos generales"):
        assert dicho in mensaje
