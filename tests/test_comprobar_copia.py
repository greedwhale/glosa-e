"""El comprobador de copia fiel: un Facturae y su copia UBL en el mismo lote.

El original es `ejemplos/fe-0001.xml`, sin tocar. La copia se escribe aquí a mano
siguiendo la tabla de `copia_fiel.py`, y cada prueba le cambia una sola cosa: si
la copia intacta no saliera limpia, ninguna de las demás probaría nada.
"""

from pathlib import Path

import pytest
from lxml import etree

from validador import comprobar_copia, factura
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
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PostalAddress><cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Talleres Ejemplo SL</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PostalAddress><cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>ESB85905495</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Clientes Ejemplo SL</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingCustomerParty>
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
    assert "no la publica nadie" in mensaje


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
