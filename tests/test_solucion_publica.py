"""Las reglas del anexo I sobre facturas de la solución pública.

Dos facturas del CIUS hechas como dice el anexo —una ordinaria con todos los
grupos españoles dentro y una rectificativa— tienen que pasar **el validador
entero** sin un solo error: forma, norma europea, código único y anexo. Es lo
que prueba que las reglas nuevas no se pelean con las de antes. De ahí, cada
regla se rompe tocando lo justo y se mira que salte ella y lo que dice.

No hay facturas de verdad del CIUS con las que medir: la solución pública no
está en marcha y en el corpus hay cero documentos que lo declaren (medido el
14-09-2026). Por eso estas dos están escritas a mano, y por eso las reglas se
prueban también contra un anexo alterado, que es lo que va a pasar cuando
salga la orden.
"""

import importlib
from dataclasses import replace

import pytest
from lxml import etree

from validador import cius_es, factura, solucion_publica
from validador.formato import detectar
from validador.incidencias import ERROR, NOTA, Incidencia

from tests.test_rutas_cius import _andar, _esquema_de_ubl, con_esquema

CIUS = "urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0"

# El anexo usa el prefijo `aeat:` y no declara a qué namespace corresponde. Las
# reglas van por nombre local, así que aquí vale uno cualquiera; se usa uno que
# no puede confundirse con el de verdad el día que se publique.
BUENA = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
         xmlns:aeat="urn:glosa:pruebas:aeat">
  <cbc:UBLVersionID>2.5</cbc:UBLVersionID>
  <cbc:CustomizationID>{CIUS}</cbc:CustomizationID>
  <cbc:ProfileID>urn:aeat:names:specification:ubl:schema:B2B</cbc:ProfileID>
  <cbc:ID>F-2026-0007</cbc:ID>
  <cbc:CopyIndicator>false</cbc:CopyIndicator>
  <cbc:IssueDate>2026-09-14</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:BillingReference><cac:InvoiceDocumentReference>
    <cbc:ID>F-2026-0006</cbc:ID><cbc:IssueDate>2026-09-01</cbc:IssueDate>
  </cac:InvoiceDocumentReference></cac:BillingReference>
  <cac:AdditionalDocumentReference>
    <cbc:ID>urn:aeat:names:specification:ubl:schema:QR</cbc:ID>
    <cbc:UUID>https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR?nif=B12345674</cbc:UUID>
    <cbc:DocumentDescription>VERIFACTU</cbc:DocumentDescription>
  </cac:AdditionalDocumentReference>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PostalAddress>
      <cbc:StreetName>Calle Mayor 1</cbc:StreetName><cbc:CityName>Madrid</cbc:CityName>
      <cbc:PostalZone>28001</cbc:PostalZone><cbc:CountrySubentity>Madrid</cbc:CountrySubentity>
      <cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country>
    </cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Talleres Ejemplo SL</cbc:RegistrationName></cac:PartyLegalEntity>
    <cac:ServiceProviderParty>
      <cbc:ServiceTypeCode>ThirdPartyInvoicing</cbc:ServiceTypeCode>
      <cac:Party>
        <cac:PartyName><cbc:Name>Gestoria Ejemplo SL</cbc:Name></cac:PartyName>
        <cac:PartyTaxScheme><cbc:CompanyID>B87654321</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
      </cac:Party>
    </cac:ServiceProviderParty>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PostalAddress>
      <cbc:StreetName>Calle Menor 2</cbc:StreetName><cbc:CityName>Sevilla</cbc:CityName>
      <cbc:PostalZone>41001</cbc:PostalZone><cbc:CountrySubentity>Sevilla</cbc:CountrySubentity>
      <cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country>
    </cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>ESA12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Comercio Cliente SA</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingCustomerParty>
  <cac:AllowanceCharge>
    <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
    <cbc:AllowanceChargeReason>Descuento por pronto pago</cbc:AllowanceChargeReason>
    <cbc:Amount currencyID="EUR">10.00</cbc:Amount>
    <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
  </cac:AllowanceCharge>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">16.80</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">80.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">16.80</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:WithholdingTaxTotal>
    <cbc:TaxAmount currencyID="EUR">12.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">80.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">12.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>15</cbc:Percent>
        <cac:TaxScheme><cbc:ID>WTH</cbc:ID><cbc:TaxTypeCode>01</cbc:TaxTypeCode></cac:TaxScheme>
      </cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:WithholdingTaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">90.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">80.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">96.80</cbc:TaxInclusiveAmount>
    <cbc:AllowanceTotalAmount currencyID="EUR">10.00</cbc:AllowanceTotalAmount>
    <cbc:PayableAmount currencyID="EUR">138.96</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:CollectionInvoiceLine>
    <cbc:ID>urn:aeat:names:specification:ubl:schema:SUPL</cbc:ID>
    <cac:Item><cbc:Name>Tasas pagadas por cuenta del cliente</cbc:Name></cac:Item>
  </cac:CollectionInvoiceLine>
  <cac:CollectionInvoiceLine>
    <cbc:ID>urn:aeat:names:specification:ubl:schema:REEQ</cbc:ID>
    <cac:TaxTotal>
      <cbc:TaxAmount currencyID="EUR">4.16</cbc:TaxAmount>
      <cac:TaxSubtotal>
        <cbc:TaxableAmount currencyID="EUR">80.00</cbc:TaxableAmount>
        <cbc:TaxAmount currencyID="EUR">4.16</cbc:TaxAmount>
        <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>5.2</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
      </cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:Item><cbc:Name>Operacion con recargo de equivalencia</cbc:Name></cac:Item>
  </cac:CollectionInvoiceLine>
  <cac:CollectionInvoiceLine>
    <cbc:ID>urn:aeat:names:specification:ubl:schema:RETE</cbc:ID>
    <cac:Item><cbc:Name>Retencion IRPF</cbc:Name></cac:Item>
  </cac:CollectionInvoiceLine>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="H87">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">90.00</cbc:LineExtensionAmount>
    <cac:AllowanceCharge>
      <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
      <cbc:AllowanceChargeReason>Descuento de linea</cbc:AllowanceChargeReason>
      <cbc:Amount currencyID="EUR">10.00</cbc:Amount>
    </cac:AllowanceCharge>
    <cac:Item>
      <cbc:Name>Reforma del local</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>
      <cac:AdditionalItemProperty><cbc:Name>RCAT</cbc:Name><cbc:Value>9872023VH5797S0001WX</cbc:Value><cbc:ValueQualifier>01</cbc:ValueQualifier></cac:AdditionalItemProperty>
      <cac:AdditionalItemProperty><cbc:Name>REGI</cbc:Name><cbc:Value>18</cbc:Value><cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>
    </cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">100.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</Invoice>"""

EXTENSION_RECT = """  <ext:UBLExtensions><ext:UBLExtension>
    <cbc:ID>urn:aeat:names:specification:ubl:schema:ext:id:RECT</cbc:ID>
    <ext:ExtensionContent><aeat:InvoiceExtension><aeat:Correction>
      <aeat:Category>R4</aeat:Category><aeat:Method>S</aeat:Method>
      <aeat:Amounts><aeat:TaxableAmountAdjustment>70.00</aeat:TaxableAmountAdjustment></aeat:Amounts>
    </aeat:Correction></aeat:InvoiceExtension></ext:ExtensionContent>
  </ext:UBLExtension></ext:UBLExtensions>
"""

LINEA_REGE = """  <cac:CollectionInvoiceLine>
    <ext:UBLExtensions><ext:UBLExtension>
      <cbc:ID>urn:aeat:names:specification:ubl:schema:ext:id:REGE</cbc:ID>
      <ext:ExtensionContent><aeat:CollectionInvoiceLineExtension><aeat:LargeCompaniesSpecialRegime>
        <aeat:TaxableAmount>95.00</aeat:TaxableAmount>
      </aeat:LargeCompaniesSpecialRegime></aeat:CollectionInvoiceLineExtension></ext:ExtensionContent>
    </ext:UBLExtension></ext:UBLExtensions>
    <cbc:ID>urn:aeat:names:specification:ubl:schema:REGE</cbc:ID>
    <cac:Item><cbc:Name>Operaciones en regimen de grupo de entidades</cbc:Name></cac:Item>
  </cac:CollectionInvoiceLine>
"""


def cambia(xml: str, viejo: str, nuevo: str) -> str:
    """Toca lo justo, y se asegura de que lo tocado está una sola vez."""
    assert xml.count(viejo) == 1, f"«{viejo}» aparece {xml.count(viejo)} veces"
    return xml.replace(viejo, nuevo)


RECTIFICATIVA = cambia(
    cambia(BUENA, "  <cbc:UBLVersionID>", EXTENSION_RECT + "  <cbc:UBLVersionID>"),
    "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>384<")
CON_GRUPO = cambia(BUENA, "  <cac:InvoiceLine>", LINEA_REGE + "  <cac:InvoiceLine>")


def spfe(xml: str) -> list[Incidencia]:
    datos = xml.encode("utf-8")
    return solucion_publica.reglas(etree.fromstring(datos), detectar(datos))


def codigos(xml: str) -> set[str]:
    return {i.codigo for i in spfe(xml) if i.gravedad != NOTA}


def las(xml: str, codigo: str) -> list[Incidencia]:
    return [i for i in spfe(xml) if i.codigo == codigo]


def la(xml: str, codigo: str) -> Incidencia:
    encontradas = las(xml, codigo)
    assert len(encontradas) == 1, [i.campo for i in encontradas]
    return encontradas[0]


# --- Las dos buenas, en el validador entero ----------------------------------


class TestLasBuenas:

    @pytest.mark.parametrize("xml", [BUENA, RECTIFICATIVA, CON_GRUPO],
                             ids=["ordinaria", "rectificativa", "grupo de entidades"])
    def test_no_dan_ni_un_error_en_todo_el_validador(self, xml):
        informe = factura.validar(xml.encode("utf-8"))
        assert [(i.codigo, i.campo) for i in informe.errores] == []
        assert [(i.codigo, i.campo) for i in informe.avisos] == []
        assert {i.codigo for i in informe.notas} == {"SPFE-BORRADOR", "SPFE-TOTAL-A-PAGAR"}

    def test_la_nota_del_borrador_sale_siempre_y_dice_que_es_un_borrador(self):
        nota = la(BUENA, "SPFE-BORRADOR")
        assert nota.gravedad == NOTA
        assert "borrador" in nota.mensaje and "17-04-2026" in nota.mensaje
        assert nota.encontrado == CIUS

    def test_el_alcance_dice_el_anexo_solo_si_hay_una_factura_que_lo_declara(self, tmp_path):
        """«Sin errores» en una factura del CIUS quiere decir también que cumple
        el borrador del anexo, y la frase que dice qué se ha mirado lo tiene que
        decir. En un lote sin facturas del CIUS no se ha mirado, y no lo dice."""
        (tmp_path / "cius.xml").write_text(BUENA, encoding="utf-8")
        con = factura.validar_lote([tmp_path / "cius.xml"]).alcance()
        assert "borrador del anexo I" in con
        (tmp_path / "otra.xml").write_text(cambia(BUENA, CIUS, "urn:cen.eu:en16931:2017"),
                                           encoding="utf-8")
        sin = factura.validar_lote([tmp_path / "otra.xml"]).alcance()
        assert "anexo I" not in sin

    def test_llevan_la_etiqueta_del_anexo_y_no_la_del_real_decreto(self):
        assert factura.origen(Incidencia("SPFE-NIF", ERROR, "")) == factura.SOLUCION_PUBLICA
        detalle = factura.validar(cambia(BUENA, "<cbc:CopyIndicator>false</cbc:CopyIndicator>", "")
                                  .encode("utf-8")).detalle(norma=factura.origen)
        assert "[SPFE-COPIA · Anexo I (borrador)]" in detalle


# --- A quién se aplica ---------------------------------------------------------


class TestAQuienSeAplica:

    def test_una_factura_que_no_declara_el_cius_no_se_mide_con_el_anexo(self):
        """Y entonces BR-CO-16 sí salta con el suplido: sin el CIUS no hay
        anexo que diga que el total a pagar lo suma."""
        sin_cius = cambia(BUENA, CIUS, "urn:cen.eu:en16931:2026")
        assert spfe(sin_cius) == []
        informe = factura.validar(sin_cius.encode("utf-8"))
        assert not [i for i in informe.incidencias if i.codigo.startswith("SPFE-")]
        assert "BR-CO-16" in {i.codigo for i in informe.errores}

    def test_con_el_cius_y_lineas_de_cobro_br_co_16_no_se_da_por_mala(self):
        """El total a pagar suma el suplido, el recargo y la retención, como
        dice el anexo. BR-CO-16 no sale, y la nota dice que no se ha mirado."""
        informe = factura.validar(BUENA.encode("utf-8"))
        assert "BR-CO-16" not in {i.codigo for i in informe.incidencias}
        nota = next(i for i in informe.notas if i.codigo == "SPFE-TOTAL-A-PAGAR")
        assert "BR-CO-16" in nota.mensaje and nota.encontrado == "138.96"

    def test_sin_lineas_de_cobro_br_co_16_se_comprueba_como_siempre(self):
        sin_cobros = BUENA
        for clave in ("SUPL", "REEQ", "RETE"):
            inicio = sin_cobros.index(f"  <cac:CollectionInvoiceLine>\n    <cbc:ID>urn:aeat:names:specification:ubl:schema:{clave}")
            fin = sin_cobros.index("</cac:CollectionInvoiceLine>\n", inicio) + len("</cac:CollectionInvoiceLine>\n")
            sin_cobros = sin_cobros[:inicio] + sin_cobros[fin:]
        inicio = sin_cobros.index("  <cac:WithholdingTaxTotal>")
        fin = sin_cobros.index("</cac:WithholdingTaxTotal>\n") + len("</cac:WithholdingTaxTotal>\n")
        sin_cobros = sin_cobros[:inicio] + sin_cobros[fin:]
        informe = factura.validar(sin_cobros.encode("utf-8"))
        assert "SPFE-TOTAL-A-PAGAR" not in {i.codigo for i in informe.incidencias}
        assert "BR-CO-16" in {i.codigo for i in informe.errores}
        cuadrada = cambia(sin_cobros, ">138.96<", ">96.80<")
        assert factura.validar(cuadrada.encode("utf-8")).errores == []

    def test_otra_sintaxis_que_declara_el_cius_recibe_un_aviso_y_nada_mas(self):
        with open("ejemplos/cii-A-0001.xml", encoding="utf-8") as f:
            cii = f.read()
        cii = cambia(cii, "<ram:ID>urn:cen.eu:en16931:2017</ram:ID>", f"<ram:ID>{CIUS}</ram:ID>")
        incidencias = spfe(cii)
        assert [i.codigo for i in incidencias] == ["SPFE-SINTAXIS"]
        assert "CII" in incidencias[0].mensaje

    def test_un_abono_se_queja_de_ser_abono_y_no_se_mide_lo_demas(self):
        abono = (BUENA.replace("Invoice-2", "CreditNote-2")
                 .replace("<Invoice ", "<CreditNote ").replace("</Invoice>", "</CreditNote>")
                 .replace("InvoiceTypeCode>380<", "CreditNoteTypeCode>381<")
                 .replace("</cbc:InvoiceTypeCode>", "</cbc:CreditNoteTypeCode>")
                 .replace("<cbc:CopyIndicator>false</cbc:CopyIndicator>", ""))
        assert codigos(abono) == {"SPFE-TIPO-DE-FACTURA"}
        assert la(abono, "SPFE-TIPO-DE-FACTURA").encontrado == "CreditNote 381"


# --- Cada regla, rota ------------------------------------------------------------


class TestCabecera:

    def test_la_especificacion_tiene_que_ser_el_valor_entero(self):
        otra = cambia(BUENA, "en16931:2026#compliant", "en16931:2017#compliant")
        assert codigos(otra) == {"SPFE-ESPECIFICACION"}
        assert la(otra, "SPFE-ESPECIFICACION").esperado == CIUS

    def test_el_proceso_falta_o_es_otro(self):
        sin = cambia(BUENA, "<cbc:ProfileID>urn:aeat:names:specification:ubl:schema:B2B</cbc:ProfileID>", "")
        assert la(sin, "SPFE-PROCESO").encontrado == "(falta)"
        otro = cambia(BUENA, "schema:B2B<", "schema:B2G<")
        assert codigos(otro) == {"SPFE-PROCESO"}
        assert la(otro, "SPFE-PROCESO").encontrado.endswith("B2G")

    def test_original_o_copia_es_obligatorio(self):
        assert codigos(cambia(BUENA, "<cbc:CopyIndicator>false</cbc:CopyIndicator>", "")) == {"SPFE-COPIA"}
        assert codigos(cambia(BUENA, ">false</cbc:CopyIndicator>", ">true</cbc:CopyIndicator>")) == set()

    def test_el_381_no_existe_en_la_solucion_publica(self):
        abono = cambia(BUENA, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>381<")
        queja = la(abono, "SPFE-TIPO-DE-FACTURA")
        assert "384" in queja.mensaje and queja.encontrado == "381"
        assert codigos(cambia(BUENA, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>386<")) == {"SPFE-TIPO-DE-FACTURA"}

    def test_un_tipo_que_ni_la_norma_admite_se_lo_deja_a_br_cl_01(self):
        malo = cambia(BUENA, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>999<")
        assert "SPFE-TIPO-DE-FACTURA" not in codigos(malo)
        assert "BR-CL-01" in {i.codigo for i in factura.validar(malo.encode("utf-8")).errores}

    def test_la_moneda_del_iva_es_el_euro(self):
        en_dolares = cambia(BUENA, "<cbc:DocumentCurrencyCode>EUR<", "<cbc:DocumentCurrencyCode>USD<")
        assert la(en_dolares, "SPFE-MONEDA-DEL-IVA").encontrado == "(falta)"
        con_euro = cambia(en_dolares, "<cbc:DocumentCurrencyCode>USD</cbc:DocumentCurrencyCode>",
                          "<cbc:DocumentCurrencyCode>USD</cbc:DocumentCurrencyCode>"
                          "<cbc:TaxCurrencyCode>EUR</cbc:TaxCurrencyCode>")
        assert "SPFE-MONEDA-DEL-IVA" not in codigos(con_euro)
        otra = cambia(BUENA, "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>",
                      "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
                      "<cbc:TaxCurrencyCode>USD</cbc:TaxCurrencyCode>")
        assert la(otra, "SPFE-MONEDA-DEL-IVA").encontrado == "USD"

    def test_el_importe_pagado_solo_puede_ser_cero(self):
        antes = "<cbc:PayableAmount currencyID"
        pagado = cambia(BUENA, antes, '<cbc:PrepaidAmount currencyID="EUR">10.00</cbc:PrepaidAmount>' + antes)
        assert la(pagado, "SPFE-IMPORTE-PAGADO").encontrado == "10.00"
        cero = cambia(BUENA, antes, '<cbc:PrepaidAmount currencyID="EUR">0.00</cbc:PrepaidAmount>' + antes)
        assert codigos(cero) == set()

    @pytest.mark.parametrize("escrito", ["NaN", "1E+3"])
    def test_lo_que_no_es_un_numero_no_se_acusa_de_no_ser_cero(self, escrito):
        # «NaN» no es igual a cero y salía acusado de no serlo, encima de la
        # queja del esquema. Un importe que no es un número es cosa del XSD.
        antes = "<cbc:PayableAmount currencyID"
        raro = cambia(BUENA, antes, f'<cbc:PrepaidAmount currencyID="EUR">{escrito}</cbc:PrepaidAmount>' + antes)
        assert "SPFE-IMPORTE-PAGADO" not in codigos(raro)


# Un documento justificativo adicional que no es el QR. Es lo unico que se
# puede escribir de la forma nueva: la AEAT dijo el 22-09-2026 que las
# rectificativas van en BG-24 con L10 y L2, y no dijo que codigo marca ese uso.
OTRO_ADJUNTO = (
    "  <cac:AdditionalDocumentReference>\n"
    "    <cbc:ID>RECT-2026-0001</cbc:ID>\n"
    "    <cbc:DocumentTypeCode>130</cbc:DocumentTypeCode>\n"
    "    <cbc:DocumentDescription>R4 S</cbc:DocumentDescription>\n"
    "  </cac:AdditionalDocumentReference>\n"
)


class TestRectificativa:

    def test_una_384_sin_extension(self):
        queja = la(cambia(BUENA, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>384<"),
                   "SPFE-RECTIFICATIVA")
        assert queja.campo.startswith("Datos rectificados") and "R1 a R4" in queja.mensaje
        assert "SPFE-RECTIFICATIVA" in codigos(cambia(BUENA, ">380<", ">471<"))

    def test_una_380_sin_extension_no_la_necesita(self):
        assert "SPFE-RECTIFICATIVA" not in codigos(BUENA)

    def test_con_un_bg24_que_no_es_el_qr_es_nota_y_no_error(self):
        """La forma que confirmo la AEAT el 22-09-2026 no puede dar ERROR.

        «El grupo de extension nacional BG-ES-1 para datos rectificados
        (presente en el borrador de abril) deja de existir de forma
        definitiva», y las rectificativas se estructuran con BG-24. Quien la
        escriba asi esta haciendo lo que le dicen, y hasta el 22-09-2026 esta
        regla le devolvia un ERROR.
        """
        nueva = cambia(cambia(BUENA, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>384<"),
                       "  <cac:AccountingSupplierParty>", OTRO_ADJUNTO + "  <cac:AccountingSupplierParty>")
        queja = la(nueva, "SPFE-RECTIFICATIVA")
        assert queja.gravedad == NOTA, "una factura escrita al anexo nuevo sale mala"
        assert "SPFE-RECTIFICATIVA" not in codigos(nueva)
        assert queja.campo == "Datos rectificados (BG-24)"
        assert "22-09-2026" in queja.mensaje and "L10" in queja.mensaje

    def test_la_nota_no_promete_haber_leido_el_bg24(self):
        """Porque no se puede: el anexo dice que un BG-24 no se distingue de
        otro, y del calificador de la forma nueva no se sabe el codigo."""
        nueva = cambia(cambia(BUENA, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>384<"),
                       "  <cac:AccountingSupplierParty>", OTRO_ADJUNTO + "  <cac:AccountingSupplierParty>")
        queja = la(nueva, "SPFE-RECTIFICATIVA")
        assert queja.encontrado == "un BG-24 sin leer"
        assert "No se comprueba lo que dice" in queja.mensaje

    def test_el_qr_solo_no_vale_de_bg24_de_rectificativa(self):
        """La BUENA ya trae un BG-24, el del QR. Si contara, una 384 pelada
        dejaria de dar error por tener QR, que es justo lo contrario."""
        pelada = cambia(BUENA, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>384<")
        assert "urn:aeat:names:specification:ubl:schema:QR" in pelada
        queja = la(pelada, "SPFE-RECTIFICATIVA")
        assert queja.gravedad == ERROR
        assert queja.esperado == "la extensión de rectificativas, o un BG-24"

    def test_le_falta_la_modalidad(self):
        queja = la(cambia(RECTIFICATIVA, "<aeat:Method>S</aeat:Method>", ""), "SPFE-RECTIFICATIVA")
        assert "modalidad" in queja.mensaje and "BT-ES-3" in queja.mensaje

    def test_el_tipo_fuera_de_su_lista(self):
        queja = la(cambia(RECTIFICATIVA, ">R4<", ">R9<"), "SPFE-RECTIFICATIVA")
        assert queja.encontrado == "R9" and "L2.A" in queja.mensaje

    def test_la_modalidad_fuera_de_su_lista(self):
        assert la(cambia(RECTIFICATIVA, "<aeat:Method>S<", "<aeat:Method>X<"),
                  "SPFE-RECTIFICATIVA").esperado == "I o S"

    def test_la_extension_mal_identificada(self):
        queja = la(cambia(RECTIFICATIVA, "ext:id:RECT", "ext:id:OTRA"), "SPFE-RECTIFICATIVA")
        assert queja.esperado.endswith("ext:id:RECT")

    def test_los_importes_rectificados_sin_base(self):
        sin_base = cambia(RECTIFICATIVA,
                          "<aeat:TaxableAmountAdjustment>70.00</aeat:TaxableAmountAdjustment>",
                          "<aeat:TaxAmountAdjustment>14.70</aeat:TaxAmountAdjustment>")
        assert "BT-ES-4" in la(sin_base, "SPFE-RECTIFICATIVA").mensaje

    def test_en_otro_namespace_se_lee_igual(self):
        """El anexo no declara el de `aeat:`; las rutas van por nombre local."""
        otro = RECTIFICATIVA.replace("urn:glosa:pruebas:aeat", "urn:otro:cualquiera")
        assert codigos(otro) == set()
        assert codigos(cambia(otro, ">R4<", ">R9<")) == {"SPFE-RECTIFICATIVA"}


class TestPartes:

    def test_el_nif_del_vendedor_con_otro_impuesto(self):
        otro = cambia(BUENA, "ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT<",
                      "ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>IVA<")
        queja = la(otro, "SPFE-NIF")
        assert queja.campo.startswith("NIF del vendedor")
        assert queja.encontrado == "ESB12345674 con el impuesto «IVA»"

    def test_sin_nif_del_comprador(self):
        sin = cambia(BUENA, "<cac:PartyTaxScheme><cbc:CompanyID>ESA12345674</cbc:CompanyID>"
                            "<cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>", "")
        queja = la(sin, "SPFE-NIF")
        assert queja.campo.startswith("NIF del comprador") and queja.encontrado == "(falta)"

    def test_en_espana_la_direccion_va_entera(self):
        sin_ciudad = cambia(BUENA, "<cbc:CityName>Madrid</cbc:CityName>", "")
        queja = la(sin_ciudad, "SPFE-DIRECCION")
        assert queja.campo == "Dirección del vendedor" and "BT-37" in queja.encontrado

    def test_fuera_de_espana_basta_la_calle(self):
        francesa = cambia(cambia(BUENA, "<cbc:CityName>Sevilla</cbc:CityName>", ""),
                          "Sevilla</cbc:CountrySubentity>\n      <cac:Country><cbc:IdentificationCode>ES<",
                          "Sevilla</cbc:CountrySubentity>\n      <cac:Country><cbc:IdentificationCode>FR<")
        assert "SPFE-DIRECCION" not in codigos(francesa)
        sin_calle = cambia(francesa, "<cbc:StreetName>Calle Menor 2</cbc:StreetName>", "")
        assert "BT-50" in la(sin_calle, "SPFE-DIRECCION").encontrado

    def test_el_tercero_sin_tipologia(self):
        sin = cambia(BUENA, "<cbc:ServiceTypeCode>ThirdPartyInvoicing</cbc:ServiceTypeCode>", "")
        assert "BT-ES-15" in la(sin, "SPFE-TERCERO").mensaje

    def test_el_tercero_con_otro_impuesto(self):
        otro = cambia(BUENA, "B87654321</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT<",
                      "B87654321</cbc:CompanyID><cac:TaxScheme><cbc:ID>IGIC<")
        assert "«IGIC»" in la(otro, "SPFE-TERCERO").mensaje


class TestDocumento:

    def test_la_factura_referenciada_sin_fecha(self):
        sin = cambia(BUENA, "<cbc:IssueDate>2026-09-01</cbc:IssueDate>", "")
        assert la(sin, "SPFE-FACTURA-REFERENCIADA").encontrado == "sin fecha: F-2026-0006"

    def test_el_motivo_con_codigo_y_sin_texto(self):
        solo_codigo = cambia(BUENA, "<cbc:AllowanceChargeReason>Descuento por pronto pago</cbc:AllowanceChargeReason>",
                             "<cbc:AllowanceChargeReasonCode>95</cbc:AllowanceChargeReasonCode>")
        queja = la(solo_codigo, "SPFE-MOTIVO")
        assert queja.campo.endswith("descuento 1")
        sin_linea = cambia(BUENA, "<cbc:AllowanceChargeReason>Descuento de linea</cbc:AllowanceChargeReason>", "")
        assert la(sin_linea, "SPFE-MOTIVO").campo.endswith("descuento 1 de la línea 1")

    def test_el_impuesto_de_una_linea_no_es_vat(self):
        otro = cambia(BUENA, "<cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>",
                      "<cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>IGIC</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>")
        queja = la(otro, "SPFE-TIPO-DE-IMPUESTO")
        assert queja.campo.endswith("líneas") and queja.encontrado == "IGIC"

    def test_la_k_no_esta_en_la_lista_l4(self):
        intracomunitaria = cambia(BUENA, "<cac:ClassifiedTaxCategory><cbc:ID>S<", "<cac:ClassifiedTaxCategory><cbc:ID>K<")
        queja = la(intracomunitaria, "SPFE-CATEGORIA")
        assert queja.encontrado == "K" and "intracomunitaria" in queja.mensaje
        assert queja.campo.endswith("línea 1")

    def test_una_categoria_que_ni_la_norma_admite_se_la_deja_a_br_cl(self):
        assert "SPFE-CATEGORIA" not in codigos(
            cambia(BUENA, "<cac:ClassifiedTaxCategory><cbc:ID>S<", "<cac:ClassifiedTaxCategory><cbc:ID>X<"))

    def test_el_qr_repetido_y_sin_direccion(self):
        qr = ("<cac:AdditionalDocumentReference>\n    <cbc:ID>urn:aeat:names:specification:ubl:schema:QR</cbc:ID>")
        doble = cambia(BUENA, qr, qr.replace("<cac:Add", "<cac:AdditionalDocumentReference><cbc:ID>"
                                                         "urn:aeat:names:specification:ubl:schema:QR</cbc:ID>"
                                                         "<cbc:DocumentDescription>VERIFACTU</cbc:DocumentDescription>"
                                                         "</cac:AdditionalDocumentReference><cac:Add", 1))
        quejas = las(doble, "SPFE-QR")
        assert [q.encontrado for q in quejas] == ["2", "(falta)"]
        assert "BT-ES-47" in quejas[1].mensaje


class TestLineas:

    REGI = "<cac:AdditionalItemProperty><cbc:Name>REGI</cbc:Name><cbc:Value>18</cbc:Value><cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>"
    RCAT = "<cac:AdditionalItemProperty><cbc:Name>RCAT</cbc:Name><cbc:Value>9872023VH5797S0001WX</cbc:Value><cbc:ValueQualifier>01</cbc:ValueQualifier></cac:AdditionalItemProperty>"

    def test_una_linea_sin_clave_de_regimen(self):
        queja = la(cambia(BUENA, self.REGI, ""), "SPFE-CLAVE-DE-REGIMEN")
        assert queja.campo.endswith("línea 1") and "REGI" in queja.esperado

    def test_tres_claves_son_demasiadas(self):
        assert la(cambia(BUENA, self.REGI, self.REGI * 3), "SPFE-CLAVE-DE-REGIMEN").encontrado == "más de dos"
        assert "SPFE-CLAVE-DE-REGIMEN" not in codigos(cambia(BUENA, self.REGI, self.REGI * 2))

    def test_un_impuesto_sin_lista_de_claves(self):
        assert la(cambia(BUENA, ">IVA</cbc:ValueQualifier>", ">IRPF</cbc:ValueQualifier>"),
                  "SPFE-CLAVE-DE-REGIMEN").encontrado == "IRPF"

    def test_cada_impuesto_tiene_su_lista(self):
        """El 17 es del IGIC y no del IVA; el 20, al revés."""
        del_igic_en_iva = cambia(BUENA, "<cbc:Value>18</cbc:Value><cbc:ValueQualifier>IVA<",
                                 "<cbc:Value>17</cbc:Value><cbc:ValueQualifier>IVA<")
        assert la(del_igic_en_iva, "SPFE-CLAVE-DE-REGIMEN").encontrado == "17 de IVA"
        en_igic = cambia(BUENA, "<cbc:Value>18</cbc:Value><cbc:ValueQualifier>IVA<",
                         "<cbc:Value>17</cbc:Value><cbc:ValueQualifier>IGIC<")
        assert "SPFE-CLAVE-DE-REGIMEN" not in codigos(en_igic)
        assert "SPFE-CLAVE-DE-REGIMEN" in codigos(cambia(en_igic, ">17<", ">20<"))

    def test_la_situacion_del_inmueble_fuera_de_la_lista(self):
        queja = la(cambia(BUENA, ">01</cbc:ValueQualifier>", ">05</cbc:ValueQualifier>"),
                   "SPFE-REFERENCIA-CATASTRAL")
        assert queja.encontrado == "05" and "BT-ES-43" in queja.campo

    def test_dos_referencias_catastrales_en_una_linea(self):
        assert la(cambia(BUENA, self.RCAT, self.RCAT * 2), "SPFE-REFERENCIA-CATASTRAL").encontrado == "más de una"

    def test_la_referencia_catastral_sin_referencia(self):
        assert la(cambia(BUENA, "<cbc:Value>9872023VH5797S0001WX</cbc:Value>", ""),
                  "SPFE-REFERENCIA-CATASTRAL").encontrado == "(falta)"

    def test_sin_referencia_catastral_no_pasa_nada(self):
        assert codigos(cambia(BUENA, self.RCAT, "")) == set()


class TestLineasDeCobro:

    def test_una_linea_de_cobro_que_no_es_de_la_lista_l7(self):
        otra = cambia(BUENA, "schema:SUPL<", "schema:OTRA<")
        assert la(otra, "SPFE-LINEA-DE-COBRO").encontrado.endswith("OTRA")

    def test_dos_grupos_de_retenciones(self):
        linea = ("  <cac:CollectionInvoiceLine>\n    <cbc:ID>urn:aeat:names:specification:ubl:schema:RETE</cbc:ID>\n"
                 "    <cac:Item><cbc:Name>Retencion IRPF</cbc:Name></cac:Item>\n  </cac:CollectionInvoiceLine>\n")
        queja = la(cambia(BUENA, linea, linea * 2), "SPFE-LINEA-DE-COBRO")
        assert "retenciones" in queja.mensaje
        sup = ("  <cac:CollectionInvoiceLine>\n    <cbc:ID>urn:aeat:names:specification:ubl:schema:SUPL</cbc:ID>\n"
               "    <cac:Item><cbc:Name>Tasas pagadas por cuenta del cliente</cbc:Name></cac:Item>\n  </cac:CollectionInvoiceLine>\n")
        assert "SPFE-LINEA-DE-COBRO" not in codigos(cambia(BUENA, sup, sup * 2))

    def test_el_recargo_con_otra_categoria_y_sin_suma(self):
        otra = cambia(BUENA, "<cbc:ID>S</cbc:ID><cbc:Percent>5.2</cbc:Percent>", "<cbc:ID>Z</cbc:ID><cbc:Percent>5.2</cbc:Percent>")
        assert "BT-ES-23" in la(otra, "SPFE-RECARGO-DE-EQUIVALENCIA").mensaje
        sin_suma = cambia(BUENA, '<cac:TaxTotal>\n      <cbc:TaxAmount currencyID="EUR">4.16</cbc:TaxAmount>',
                          "<cac:TaxTotal>")
        assert "BT-ES-28" in la(sin_suma, "SPFE-RECARGO-DE-EQUIVALENCIA").mensaje

    def test_la_retencion_con_un_concepto_fuera_de_l5_y_otro_esquema(self):
        malo = cambia(cambia(BUENA, "<cbc:TaxTypeCode>01<", "<cbc:TaxTypeCode>99<"), "<cbc:ID>WTH<", "<cbc:ID>IRPF<")
        queja = la(malo, "SPFE-RETENCION")
        assert "BT-ES-39" in queja.mensaje and "«99»" in queja.mensaje and "BT-ES-38" in queja.mensaje

    def test_la_retencion_sin_su_linea_de_cobro(self):
        linea = ("  <cac:CollectionInvoiceLine>\n    <cbc:ID>urn:aeat:names:specification:ubl:schema:RETE</cbc:ID>\n"
                 "    <cac:Item><cbc:Name>Retencion IRPF</cbc:Name></cac:Item>\n  </cac:CollectionInvoiceLine>\n")
        assert "BT-ES-32" in la(cambia(BUENA, linea, ""), "SPFE-RETENCION").mensaje

    def test_la_linea_de_retencion_sin_retenciones(self):
        inicio = BUENA.index("  <cac:WithholdingTaxTotal>")
        fin = BUENA.index("</cac:WithholdingTaxTotal>\n") + len("</cac:WithholdingTaxTotal>\n")
        assert "BT-ES-33" in la(BUENA[:inicio] + BUENA[fin:], "SPFE-RETENCION").mensaje

    def test_el_grupo_de_entidades_mal_identificado_y_sin_base(self):
        malo = cambia(cambia(CON_GRUPO, "ext:id:REGE", "ext:id:OTRA"),
                      "<aeat:TaxableAmount>95.00</aeat:TaxableAmount>", "")
        queja = la(malo, "SPFE-GRUPO-DE-ENTIDADES")
        assert "BT-ES-29" in queja.mensaje and "BT-ES-30" in queja.mensaje


# --- Que salga del anexo, y que se niegue si el anexo cambia -------------------


def _recargar_con(monkeypatch, campos):
    """Vuelve a importar el módulo con otra tabla, y lo deja como estaba.

    La excepción se compara por nombre y no por clase: al recargar, el módulo
    define su `AnexoCambiado` otra vez, y la que se lanza ya no es la misma
    clase que había antes de recargar.
    """
    monkeypatch.setattr(cius_es, "CAMPOS", tuple(campos))
    try:
        importlib.reload(solucion_publica)
    except LookupError as negativa:
        assert type(negativa).__name__ == "AnexoCambiado"
        return str(negativa)
    finally:
        monkeypatch.undo()
        importlib.reload(solucion_publica)
    return None


def _con(identificador, termino="", **cambios):
    return [replace(c, **cambios) if c.id == identificador and termino in c.termino else c
            for c in cius_es.CAMPOS]


class TestSeNiegaSiElAnexoCambia:
    """Tres formas de cambiar un anexo, y las tres dejan el módulo sin importar."""

    def test_si_un_campo_exigido_pasa_a_opcional(self, monkeypatch):
        negativa = _recargar_con(monkeypatch, _con("BT-ES-1", cardinalidad="0..1"))
        assert negativa and "BT-ES-1" in negativa and "0..1" in negativa

    def test_si_un_valor_fijo_ya_no_es_el_que_era(self, monkeypatch):
        negativa = _recargar_con(monkeypatch, _con("BT-ES-38", descripcion='Adoptará el valor fijo "IRPF".'))
        assert negativa and "WTH" in negativa

    def test_con_la_tabla_de_verdad_no_se_niega(self, monkeypatch):
        assert _recargar_con(monkeypatch, cius_es.CAMPOS) is None

    def test_si_una_ruta_deja_de_colgar_de_su_grupo(self, monkeypatch):
        """Las rutas vienen de `sintaxis`, que se deriva al importar; aquí se
        comprueba la otra mitad: que la relativa se niega si el prefijo falla."""
        with pytest.raises(solucion_publica.AnexoCambiado, match="ya no cuelga"):
            solucion_publica._relativa("./cac:WithholdingTaxTotal/cbc:TaxAmount",
                                       "./cac:CollectionInvoiceLine")

    def test_y_despues_de_negarse_vuelve_a_ser_el_de_siempre(self):
        assert codigos(BUENA) == set()


class TestDeDondeSale:

    @con_esquema
    def test_las_rutas_europeas_que_se_usan_existen_en_ubl_2_5(self):
        """El anexo no da ruta a los campos que la norma ya tiene, y aquí van
        por la vinculación de 2017. Que esos elementos estén en UBL 2.5 donde se
        buscan sí se puede comprobar."""
        tipo_de, hijos_de = _esquema_de_ubl()
        rutas = [
            "cbc:CustomizationID", "cbc:ProfileID", "cbc:CopyIndicator", "cbc:InvoiceTypeCode",
            "cac:InvoiceLine/cbc:ID", "cac:AllowanceCharge/cbc:ChargeIndicator",
            "cac:InvoiceLine/cac:AllowanceCharge/cbc:ChargeIndicator",
            "cbc:DocumentCurrencyCode", "cbc:TaxCurrencyCode",
            "cac:LegalMonetaryTotal/cbc:PrepaidAmount",
            "cac:LegalMonetaryTotal/cbc:PayableAmount",
            "cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
            "cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
            "cac:BillingReference/cac:InvoiceDocumentReference/cbc:IssueDate",
            "cac:AllowanceCharge/cbc:AllowanceChargeReason",
            "cac:AllowanceCharge/cac:TaxCategory/cbc:ID",
            "cac:InvoiceLine/cac:AllowanceCharge/cbc:AllowanceChargeReason",
            "cac:InvoiceLine/cac:Item/cac:ClassifiedTaxCategory/cbc:ID",
            "cac:InvoiceLine/cac:Item/cac:AdditionalItemProperty/cbc:Value",
            "cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:ID",
            "cac:AdditionalDocumentReference/cbc:DocumentDescription",
        ]
        for parte in ("StreetName", "CityName", "PostalZone", "CountrySubentity"):
            for quien in ("AccountingSupplierParty", "AccountingCustomerParty"):
                rutas.append(f"cac:{quien}/cac:Party/cac:PostalAddress/cbc:{parte}")
                rutas.append(f"cac:{quien}/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode")
        fallos = {r: _andar(r, tipo_de, hijos_de) for r in rutas}
        assert {r: f for r, f in fallos.items() if f} == {}

    def test_los_urn_de_las_lineas_de_cobro_son_los_de_l7(self):
        assert {u.rsplit(":", 1)[1] for u in solucion_publica._COBROS.values()} == set(
            cius_es.LISTAS["L7"].valores)

    def test_las_claves_de_regimen_se_buscan_en_la_lista_de_su_impuesto(self):
        assert solucion_publica._REGIMENES == {"IVA": "L3A", "IGIC": "L3B", "IPSI": "L3C"}

    def test_lo_que_no_se_comprueba_esta_dicho_con_su_porque(self):
        assert len(solucion_publica.NO_SE_COMPRUEBA) >= 5
        cortos = [k for k, v in solucion_publica.NO_SE_COMPRUEBA.items() if len(v) < 80]
        assert cortos == []
