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

from validador import cius_es, factura, glosario, iva, solucion_publica
from validador.formato import ESPECIFICACION_DEL_EJEMPLO, detectar
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia

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

    def test_la_nota_sale_siempre_y_dice_con_que_se_ha_medido(self):
        """Hasta el 07-10-2026 decía que el anexo «no está publicado en el BOE».

        La orden salió el 05-10-2026. Lo que la nota tiene que decir ahora es
        la mezcla de verdad: la orden publicada, lo que de ella ya se admite, y
        que el resto sigue midiendo el borrador de abril.
        """
        nota = la(BUENA, "SPFE-BORRADOR")
        assert nota.gravedad == NOTA
        assert "HAC/1028/2026" in nota.mensaje and "05-10-2026" in nota.mensaje
        assert "borrador de abril" in nota.mensaje
        assert "no quiere decir que la factura cumpla la orden" in nota.mensaje
        assert "no está publicad" not in nota.mensaje
        assert nota.encontrado == CIUS
        # «No siempre»: una 384 con un BG-24 cualquiera, o el proceso del
        # ejemplo, siguen en NOTA hasta poner las reglas al texto, y alguna de
        # lo que la orden quita sí sale. «Todavía no se rechaza», a secas, era
        # verdad solo en parte.
        assert "no siempre se rechaza" in nota.mensaje

    def test_el_alcance_dice_el_anexo_solo_si_hay_una_factura_que_lo_declara(self, tmp_path):
        """«Sin errores» en una factura del CIUS quiere decir también que cumple
        el anexo hasta donde se ha puesto al día, y la frase que dice qué se ha
        mirado lo tiene que decir. En un lote sin facturas del CIUS no se ha
        mirado, y no lo dice."""
        (tmp_path / "cius.xml").write_text(BUENA, encoding="utf-8")
        con = factura.validar_lote([tmp_path / "cius.xml"]).alcance()
        assert "anexo I de la solución pública" in con
        # «Parte de»: lo que se mide es lo que ya pedía el borrador de abril,
        # y salían «sin errores» facturas que incumplen la orden en cosas que
        # en UBL se pueden ver. Lo midió el revisor de promesas el 07-10-2026.
        assert "parte de lo que el anexo I de la solución pública pide" in con
        assert "las reglas nuevas de la orden todavía no" in con
        (tmp_path / "otra.xml").write_text(cambia(BUENA, CIUS, "urn:cen.eu:en16931:2017"),
                                           encoding="utf-8")
        sin = factura.validar_lote([tmp_path / "otra.xml"]).alcance()
        assert "anexo I" not in sin

    def test_llevan_la_etiqueta_del_anexo_y_no_la_del_real_decreto(self):
        assert factura.origen(Incidencia("SPFE-NIF", ERROR, "")) == factura.SOLUCION_PUBLICA
        detalle = factura.validar(cambia(BUENA, "<cbc:ProfileID>urn:aeat:names:specification:ubl:schema:B2B</cbc:ProfileID>", "")
                                  .encode("utf-8")).detalle(norma=factura.origen)
        # Contra un literal, y no contra la constante: compararla consigo misma
        # no fijaba nada, y la etiqueta podía volver a decir «borrador» sin que
        # ninguna prueba lo viera (lo encontró la revisión del 07-10-2026).
        assert "[SPFE-PROCESO · Anexo I]" in detalle
        assert "borrador" not in factura.SOLUCION_PUBLICA


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
        # Lo que se pide es el de la orden publicada, no el de abril.
        assert la(otra, "SPFE-ESPECIFICACION").esperado == ESPECIFICACION_DEL_EJEMPLO

    def test_el_proceso_falta_o_es_otro(self):
        sin = cambia(BUENA, "<cbc:ProfileID>urn:aeat:names:specification:ubl:schema:B2B</cbc:ProfileID>", "")
        assert la(sin, "SPFE-PROCESO").encontrado == "(falta)"
        otro = cambia(BUENA, "schema:B2B<", "schema:B2G<")
        assert codigos(otro) == {"SPFE-PROCESO"}
        assert la(otro, "SPFE-PROCESO").encontrado.endswith("B2G")

    def test_sin_indicador_de_copia_es_el_original_y_se_dice(self):
        """En abril era obligatorio; en la orden, `0..1` y «sin informar: original».

        Hasta el 07-10-2026 esto era un ERROR. Ahora es una NOTA, que dice lo
        que la orden supone y lo que pide a una copia fiel (artículo 4.3).
        """
        sin = cambia(BUENA, "<cbc:CopyIndicator>false</cbc:CopyIndicator>", "")
        assert codigos(sin) == set()
        nota = la(sin, "SPFE-COPIA")
        assert nota.gravedad == NOTA
        assert "original" in nota.mensaje and "apartado 3 del artículo 4" in nota.mensaje
        assert las(cambia(BUENA, ">false</cbc:CopyIndicator>", ">true</cbc:CopyIndicator>"),
                   "SPFE-COPIA") == []
        assert las(BUENA, "SPFE-COPIA") == []

    def test_el_381_no_existe_en_la_solucion_publica(self):
        abono = cambia(BUENA, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>381<")
        queja = la(abono, "SPFE-TIPO-DE-FACTURA")
        assert "384" in queja.mensaje and queja.encontrado == "381"
        # Desde el 22-09-2026 la extensión de rectificativas desaparece y los
        # datos rectificados van en BG-24: un mensaje que solo mande a la
        # extensión manda a un sitio que ya no va a existir.
        assert "BG-24" in queja.mensaje
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

    def test_el_importe_pagado_se_admite_y_se_dice_lo_que_no_se_ve(self):
        """Abril lo admitía solo a cero; la orden lo admite, salvo anticipos con IVA devengado.

        Hasta el 07-10-2026 un importe distinto de cero era ERROR. Lo que la
        orden prohíbe (art. 75.Dos de la Ley del IVA) no se ve en la factura, y
        la NOTA lo dice en vez de callarlo.
        """
        antes = "<cbc:PayableAmount currencyID"
        pagado = cambia(BUENA, antes, '<cbc:PrepaidAmount currencyID="EUR">10.00</cbc:PrepaidAmount>' + antes)
        assert codigos(pagado) == set()
        nota = la(pagado, "SPFE-IMPORTE-PAGADO")
        assert nota.gravedad == NOTA and nota.encontrado == "10.00"
        assert "75.Dos" in nota.mensaje
        cero = cambia(BUENA, antes, '<cbc:PrepaidAmount currencyID="EUR">0.00</cbc:PrepaidAmount>' + antes)
        assert las(cero, "SPFE-IMPORTE-PAGADO") == []

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
        # Desde el 07-10-2026 cita la orden, que es la que lo dice, y no la
        # respuesta del 22-09-2026; y ya no dice que «no está publicado».
        assert "05-10-2026" in queja.mensaje and "L10" in queja.mensaje
        assert "no está publicad" not in queja.mensaje

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
        assert queja.esperado == "los BG-24 RECT:TIPO y RECT:MODALIDAD, o la extensión de abril"

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


class TestLosCalificadoresDeL10:
    """Lo que la AEAT dio por escrito el 23-09-2026.

    Antes de esto, seis facturas distintas -una rectificativa completa y bien
    escrita, otra sin modalidad, otra con un tipo inventado y un albaran
    colgado de la factura- salian todas con la misma frase: «un BG-24 sin
    leer». L10 es lo que las separa.
    """

    ESQUEMA_DEL_CORREO = "urn:aeat:names:specification:schema:"
    ESQUEMA_DEL_ANEXO = "urn:aeat:names:specification:ubl:schema:"

    @staticmethod
    def adjunto(calificador, valor="R4", codigo=None):
        """`valor` va en la descripción y `codigo` en cbc:DocumentTypeCode.

        El código va donde lo pone el ejemplo de la AEAT del 02-10-2026; la
        descripción es donde se apostaba que iría antes de ese día.
        """
        codigo = f"    <cbc:DocumentTypeCode>{codigo}</cbc:DocumentTypeCode>\n" if codigo else ""
        return (
            "  <cac:AdditionalDocumentReference>\n"
            f"    <cbc:ID>{calificador}</cbc:ID>\n"
            f"{codigo}"
            f"    <cbc:DocumentDescription>{valor}</cbc:DocumentDescription>\n"
            "  </cac:AdditionalDocumentReference>\n"
        )

    @classmethod
    def rectificativa_con(cls, *adjuntos):
        return cambia(
            cambia(BUENA, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>384<"),
            "  <cac:AccountingSupplierParty>",
            "".join(adjuntos) + "  <cac:AccountingSupplierParty>")

    @classmethod
    def completa(cls, esquema, tipo="R4", modalidad="S"):
        return cls.rectificativa_con(cls.adjunto(esquema + "RECT:TIPO", "texto libre", tipo),
                                     cls.adjunto(esquema + "RECT:MODALIDAD", "texto libre", modalidad))

    def test_reconoce_el_tipo_y_la_modalidad(self):
        queja = la(self.completa(self.ESQUEMA_DEL_CORREO), "SPFE-RECTIFICATIVA")
        assert queja.gravedad == NOTA
        assert queja.encontrado == "RECT:MODALIDAD y RECT:TIPO"
        assert "sin leer" not in queja.encontrado

    def test_los_dos_esquemas_se_leen_igual(self):
        """Porque los dos textos no dicen lo mismo y uno de ellos se equivoca.

        El anexo publicado escribe el del QR con `ubl:` dentro, y el correo
        escribe toda L10 sin el. `QR` esta en las dos listas, asi que la
        contradiccion es comprobable. Elegir uno y fallar no daria un error:
        daria un validador que no encuentra nada y se calla.
        """
        del_correo = la(self.completa(self.ESQUEMA_DEL_CORREO), "SPFE-RECTIFICATIVA")
        del_anexo = la(self.completa(self.ESQUEMA_DEL_ANEXO), "SPFE-RECTIFICATIVA")
        assert del_correo.encontrado == del_anexo.encontrado == "RECT:MODALIDAD y RECT:TIPO"

    def test_dice_cual_de_los_dos_falta(self):
        queja = la(self.rectificativa_con(
            self.adjunto(self.ESQUEMA_DEL_CORREO + "RECT:TIPO", "R4")),
            "SPFE-RECTIFICATIVA")
        assert queja.encontrado == "RECT:TIPO"
        assert "Falta la modalidad de rectificación" in queja.mensaje
        assert queja.gravedad == NOTA, "el anexo que lo pide no esta publicado"

    def test_el_codigo_se_lee_en_document_type_code(self):
        """Donde lo pone el ejemplo que la AEAT mandó por correo el 02-10-2026.

        Hasta ese día no se sabía en qué campo del BG-24 iba el valor, y un
        R9 salía con la misma nota que un R4. Ahora el R4 se dice comprobado.
        """
        bueno = la(self.completa(self.ESQUEMA_DEL_CORREO), "SPFE-RECTIFICATIVA")
        assert bueno.gravedad == NOTA
        assert "Se comprueba el código" in bueno.mensaje
        assert "R4, está en la lista L2.A" in bueno.mensaje
        assert "S, está en la lista L2.B" in bueno.mensaje
        # El sitio lo enseñó el ejemplo del 02-10-2026 y lo fija la orden.
        assert "BT-ES-27" in bueno.mensaje and "no está publicad" not in bueno.mensaje

    def test_un_codigo_fuera_de_su_lista_es_aviso_y_no_error(self):
        """La lista es la del anexo publicado; el sitio solo lo enseña un
        ejemplo. Eso da para avisar y no para condenar."""
        malo = self.completa(self.ESQUEMA_DEL_CORREO, tipo="R9", modalidad="X")
        quejas = las(malo, "SPFE-RECTIFICATIVA")
        assert [q.gravedad for q in quejas] == [NOTA, AVISO, AVISO]
        assert [(q.encontrado, q.esperado) for q in quejas[1:]] == [
            ("R9", "R1, R2, R3 o R4"), ("X", "I o S")]
        assert "Se comprueba el código" not in quejas[0].mensaje
        assert not [i for i in spfe(malo) if i.gravedad == ERROR]

    def test_en_la_descripcion_no_se_busca_y_se_dice(self):
        """La apuesta de antes del 02-10-2026 era la descripción, y era mala.

        Un valor escrito ahí no se lee: ni se da por bueno ni por malo, y la
        nota dice que no se ha comprobado y por qué.
        """
        en_la_descripcion = self.rectificativa_con(
            self.adjunto(self.ESQUEMA_DEL_CORREO + "RECT:TIPO", "R9"),
            self.adjunto(self.ESQUEMA_DEL_CORREO + "RECT:MODALIDAD", "S"))
        quejas = las(en_la_descripcion, "SPFE-RECTIFICATIVA")
        assert [q.gravedad for q in quejas] == [NOTA]
        assert "No se comprueba el tipo de rectificativa y la modalidad" in quejas[0].mensaje
        assert "Se comprueba el código" not in quejas[0].mensaje

    def test_la_sustitucion_sin_importes_se_dice_y_no_se_condena(self):
        """La AEAT escribió el 23-09-2026 que las S llevan importes; ni el
        anexo ni el ejemplo dicen cómo se escriben."""
        queja = la(self.completa(self.ESQUEMA_DEL_CORREO), "SPFE-RECTIFICATIVA")
        assert "La modalidad es S y no trae los importes rectificados" in queja.mensaje
        por_diferencias = la(self.completa(self.ESQUEMA_DEL_CORREO, modalidad="I"),
                             "SPFE-RECTIFICATIVA")
        assert "no trae los importes" not in por_diferencias.mensaje

    def test_un_tipo_repetido_se_lee_entero(self):
        """Antes se leía el primero y el resto desaparecía sin decirlo: un R9
        detrás de un R1 no salía, y la nota daba el tipo por comprobado."""
        tipo = self.ESQUEMA_DEL_CORREO + "RECT:TIPO"
        modalidad = self.ESQUEMA_DEL_CORREO + "RECT:MODALIDAD"
        dos = self.rectificativa_con(self.adjunto(tipo, "uno", "R1"), self.adjunto(tipo, "otro", "R9"),
                                     self.adjunto(modalidad, "texto libre", "I"))
        quejas = las(dos, "SPFE-RECTIFICATIVA")
        assert [(q.gravedad, q.encontrado) for q in quejas] == [
            (NOTA, "RECT:MODALIDAD y RECT:TIPO"), (AVISO, "R9")]
        assert "Hay 2 documentos con el tipo de rectificativa" in quejas[0].mensaje
        assert "R1, está en la lista L2.A" in quejas[0].mensaje

    def test_un_repetido_sin_codigo_no_tapa_al_que_lo_lleva(self):
        tipo = self.ESQUEMA_DEL_CORREO + "RECT:TIPO"
        mezcla = self.rectificativa_con(
            self.adjunto(tipo, "sin código"), self.adjunto(tipo, "texto libre", "R1"),
            self.adjunto(self.ESQUEMA_DEL_CORREO + "RECT:MODALIDAD", "texto libre", "I"))
        nota = la(mezcla, "SPFE-RECTIFICATIVA")
        assert "No se comprueba uno de los documentos del tipo de rectificativa" in nota.mensaje
        assert "R1, está en la lista L2.A" in nota.mensaje

    def test_la_s_se_mira_en_todas_las_modalidades(self):
        modalidad = self.ESQUEMA_DEL_CORREO + "RECT:MODALIDAD"
        dos = self.rectificativa_con(
            self.adjunto(self.ESQUEMA_DEL_CORREO + "RECT:TIPO", "texto libre", "R1"),
            self.adjunto(modalidad, "texto libre", "I"), self.adjunto(modalidad, "texto libre", "S"))
        assert "La modalidad es S y no trae los importes" in la(dos, "SPFE-RECTIFICATIVA").mensaje

    def test_la_s_con_importes_no_dice_que_le_faltan(self):
        con_importes = self.rectificativa_con(
            self.adjunto(self.ESQUEMA_DEL_CORREO + "RECT:TIPO", "texto libre", "R1"),
            self.adjunto(self.ESQUEMA_DEL_CORREO + "RECT:MODALIDAD", "texto libre", "S"),
            self.adjunto(self.ESQUEMA_DEL_CORREO + "RECT:IMPORTES", "70.00"))
        nota = la(con_importes, "SPFE-RECTIFICATIVA")
        assert "no trae los importes" not in nota.mensaje
        assert nota.encontrado == "RECT:IMPORTES, RECT:MODALIDAD y RECT:TIPO"

    def test_el_qr_y_la_autorizacion_no_dicen_que_se_rectifica(self):
        """Son de L10, pero no de la rectificativa.

        Antes del 05-10-2026 la autorización no se reconocía, y una 384 que
        solo la llevaba a ella salía con una nota y no con el error de no
        decir qué rectifica: un BG-24 cualquiera bastaba para eso.
        """
        # Y a secas: desde el 07-10-2026 el calificador de L10 se reconoce
        # también sin el esquema delante.
        for esquema in (self.ESQUEMA_DEL_CORREO, self.ESQUEMA_DEL_ANEXO, ""):
            pelada = self.rectificativa_con(
                "  <cac:AdditionalDocumentReference>\n"
                f"    <cbc:ID>{esquema}AUT</cbc:ID>\n"
                "    <cbc:UUID>REG015642102461</cbc:UUID>\n"
                "  </cac:AdditionalDocumentReference>\n")
            queja = la(pelada, "SPFE-RECTIFICATIVA")
            assert queja.gravedad == ERROR, esquema

    def test_los_de_la_rectificativa_a_secas_se_leen_como_los_demas(self):
        """`RECT:TIPO` y `RECT:MODALIDAD` sin el esquema delante.

        Antes de publicar solo se probaba «QR» a secas, y la rotura que deja
        reconocer solo ése pasaba toda la suite: un R9 dejaba de avisar y la
        pareja completa salía como «un BG-24 sin leer». Lo vio la revisión del
        07-10-2026.
        """
        fuera = las(self.rectificativa_con(self.adjunto("RECT:TIPO", "texto libre", "R9")),
                    "SPFE-RECTIFICATIVA")
        assert (AVISO, "R9") in [(q.gravedad, q.encontrado) for q in fuera]
        completa = la(self.rectificativa_con(
            self.adjunto("RECT:TIPO", "texto libre", "R1"),
            self.adjunto("RECT:MODALIDAD", "texto libre", "S")), "SPFE-RECTIFICATIVA")
        assert completa.encontrado == "RECT:MODALIDAD y RECT:TIPO"

    def test_un_bg24_ajeno_sigue_sin_leerse(self):
        """Un albaran no es una rectificativa, y ahora se distingue."""
        queja = la(self.rectificativa_con(
            "  <cac:AdditionalDocumentReference>\n"
            "    <cbc:ID>ALB-2026-77</cbc:ID>\n"
            "    <cbc:DocumentTypeCode>130</cbc:DocumentTypeCode>\n"
            "  </cac:AdditionalDocumentReference>\n"),
            "SPFE-RECTIFICATIVA")
        assert queja.encontrado == "un BG-24 sin leer"

    def test_la_cola_sola_no_basta(self):
        """Si bastara, cualquiera podria llamar RECT:TIPO a lo suyo.

        Se piden los dos pedazos: el espacio de nombres de la AEAT delante y
        el calificador detras de sus dos puntos.
        """
        for ajeno in ("urn:otra:empresa:cualquiera:RECT:TIPO",
                      "urn:aeat:names:specification:schema:MIRECT:TIPO",
                      # Hasta el 05-10-2026 valía cualquier prefijo de la AEAT;
                      # ahora, uno de los dos esquemas escritos de L10.
                      "urn:aeat:names:specification:ubl:schema:ext:id:RECT:TIPO"):
            queja = la(self.rectificativa_con(self.adjunto(ajeno, "R4")),
                       "SPFE-RECTIFICATIVA")
            assert queja.encontrado == "un BG-24 sin leer", ajeno


# Lo que la AEAT mandó por correo el 02-10-2026, tal cual, sobre el cuerpo de
# la BUENA: la captura era solo la cabecera y los cuatro BG-24, sin partes,
# totales ni líneas. Va sin `UBLVersionID`, con los dos identificadores nuevos
# y con los cuatro calificadores de L10 sin `ubl:`. La URL del QR se deja la de
# la BUENA: la del ejemplo apunta a un dominio, `gob.aeat`, que no existe.
BG24_DEL_EJEMPLO = """  <cac:AdditionalDocumentReference>
    <cbc:ID>urn:aeat:names:specification:schema:RECT:TIPO</cbc:ID>
    <cbc:DocumentTypeCode>R1</cbc:DocumentTypeCode>
    <cbc:DocumentDescription>Rectificación por el artículo 80.1 de la LIVA</cbc:DocumentDescription>
  </cac:AdditionalDocumentReference>
  <cac:AdditionalDocumentReference>
    <cbc:ID>urn:aeat:names:specification:schema:RECT:MODALIDAD</cbc:ID>
    <cbc:DocumentTypeCode>S</cbc:DocumentTypeCode>
    <cbc:DocumentDescription>Rectificación por sustitución</cbc:DocumentDescription>
  </cac:AdditionalDocumentReference>
  <cac:AdditionalDocumentReference>
    <cbc:ID>urn:aeat:names:specification:schema:AUT</cbc:ID>
    <cbc:UUID>REG015642102461</cbc:UUID>
    <cbc:DocumentDescription>Autorización facturación máquina vending</cbc:DocumentDescription>
  </cac:AdditionalDocumentReference>
"""
PROCESO_DEL_EJEMPLO = "urn:aeat:names:specification:schema:profile:B2B"
_CABECERA_DEL_EJEMPLO = cambia(
    cambia(
        cambia(
            cambia(BUENA, "  <cbc:UBLVersionID>2.5</cbc:UBLVersionID>\n", ""),
            CIUS, ESPECIFICACION_DEL_EJEMPLO),
        "urn:aeat:names:specification:ubl:schema:B2B", PROCESO_DEL_EJEMPLO),
    "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>384<")
SIN_LOS_BG24 = cambia(_CABECERA_DEL_EJEMPLO, "urn:aeat:names:specification:ubl:schema:QR",
                      "urn:aeat:names:specification:schema:QR")
EJEMPLO = cambia(SIN_LOS_BG24, "  <cac:AccountingSupplierParty>",
                 BG24_DEL_EJEMPLO + "  <cac:AccountingSupplierParty>")


class TestElEjemploDeLaAEAT:
    """La respuesta del 02-10-2026: una captura, y ni una frase de criterio.

    Medido el 05-10-2026, antes de tocar nada: con el identificador del
    ejemplo no se aplicaba ni una regla del anexo y nada lo decía, se le
    suponía UBL 2.1, el QR sin `ubl:` no era el QR y la autorización no se
    reconocía. Una rectificativa que no dice qué rectifica salía «sin
    errores». Cada prueba de aquí rompe una de esas cosas.
    """

    def test_pasa_el_validador_entero_y_dice_lo_que_ha_aceptado(self):
        informe = factura.validar(EJEMPLO.encode("utf-8"))
        assert informe.deteccion.version == "2.5"
        assert [(i.codigo, i.campo) for i in informe.errores] == []
        assert [(i.codigo, i.campo) for i in informe.avisos] == []
        # Sin SPFE-ESPECIFICACION desde el 07-10-2026: el identificador del
        # ejemplo es el que fija la orden publicada, y ya no hay nada que anotar.
        assert {i.codigo for i in informe.notas} == {
            "SPFE-BORRADOR", "SPFE-TOTAL-A-PAGAR", "SPFE-PROCESO", "SPFE-RECTIFICATIVA"}

    def test_con_el_namespace_de_las_extensiones_del_ejemplo_tambien(self):
        """El ejemplo declara `aeat:` con un namespace; las pruebas usan otro
        a propósito, y las reglas van por nombre local. Que sea verdad, con una
        extensión dentro que se lea: sin la base, el grupo de entidades se queja.
        """
        con_el_suyo = cambia(EJEMPLO, "  <cac:InvoiceLine>", LINEA_REGE + "  <cac:InvoiceLine>").replace(
            "urn:glosa:pruebas:aeat", "urn:es:aeat:names:specification:ubl:schema:xsd:Extensiones-1")
        assert "<aeat:TaxableAmount>" in con_el_suyo
        assert factura.validar(con_el_suyo.encode("utf-8")).errores == []
        sin_base = cambia(con_el_suyo, "<aeat:TaxableAmount>95.00</aeat:TaxableAmount>", "")
        assert "BT-ES-30" in la(sin_base, "SPFE-GRUPO-DE-ENTIDADES").mensaje

    def test_el_identificador_del_ejemplo_es_el_de_la_orden_y_no_se_anota(self):
        """Hasta el 07-10-2026 salía con una NOTA: «un ejemplo no es el BOE».

        La fila BT-24 de la orden publicada el 05-10-2026 dice, letra a letra,
        el identificador del ejemplo. Ya no hay nada que anotar, y la NOTA que
        sigue diciendo con qué se ha medido es SPFE-BORRADOR.
        """
        assert las(EJEMPLO, "SPFE-ESPECIFICACION") == []
        assert la(EJEMPLO, "SPFE-BORRADOR").encontrado == ESPECIFICACION_DEL_EJEMPLO

    def test_el_alcance_nombra_el_anexo(self, tmp_path):
        (tmp_path / "ejemplo.xml").write_text(EJEMPLO, encoding="utf-8")
        assert "anexo I de la solución pública" in factura.validar_lote([tmp_path / "ejemplo.xml"]).alcance()

    def test_una_384_que_no_dice_que_rectifica_ya_no_sale_limpia(self):
        """El caso que se midió el 05-10-2026 con «sin errores» y exit 0."""
        informe = factura.validar(SIN_LOS_BG24.encode("utf-8"))
        assert "SPFE-RECTIFICATIVA" in {i.codigo for i in informe.errores}

    def test_r1_y_s_se_comprueban_y_la_sustitucion_sin_importes_se_dice(self):
        queja = la(EJEMPLO, "SPFE-RECTIFICATIVA")
        assert queja.gravedad == NOTA
        assert queja.encontrado == "RECT:MODALIDAD y RECT:TIPO"
        assert "R1, está en la lista L2.A" in queja.mensaje
        assert "La modalidad es S y no trae los importes" in queja.mensaje

    def test_el_proceso_del_ejemplo_es_nota_con_cualquiera_de_los_dos(self):
        con_el_de_abril = cambia(BUENA, "urn:aeat:names:specification:ubl:schema:B2B",
                                 PROCESO_DEL_EJEMPLO)
        assert la(con_el_de_abril, "SPFE-PROCESO").gravedad == NOTA
        assert codigos(con_el_de_abril) == set()
        assert la(EJEMPLO, "SPFE-PROCESO").encontrado == PROCESO_DEL_EJEMPLO

    def test_otro_identificador_de_la_aeat_se_avisa_y_no_se_mide(self, tmp_path):
        """No se le aplica el anexo, porque no dice ser lo que el anexo define.
        Pero no se calla, que es lo que pasaba con el del ejemplo."""
        otro = "urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:2.0.0:extended"
        tercero = cambia(SIN_LOS_BG24, ESPECIFICACION_DEL_EJEMPLO, otro)
        quejas = spfe(tercero)
        assert [(q.codigo, q.gravedad) for q in quejas] == [("SPFE-ESPECIFICACION", AVISO)]
        assert quejas[0].encontrado == otro and "no se han comprobado" in quejas[0].mensaje
        (tmp_path / "tercero.xml").write_text(tercero, encoding="utf-8")
        assert "anexo I" not in factura.validar_lote([tmp_path / "tercero.xml"]).alcance()

    def test_en_otra_sintaxis_el_del_ejemplo_se_avisa_como_el_cius(self):
        with open("ejemplos/cii-A-0001.xml", encoding="utf-8") as f:
            cii = f.read()
        marcador = "<ram:ID>urn:cen.eu:en16931:2017</ram:ID>"
        con_el_del_ejemplo = cambia(cii, marcador, f"<ram:ID>{ESPECIFICACION_DEL_EJEMPLO}</ram:ID>")
        quejas = spfe(con_el_del_ejemplo)
        assert [(q.codigo, q.gravedad) for q in quejas] == [("SPFE-SINTAXIS", AVISO)]
        assert "dice ser de la solución pública" in quejas[0].mensaje
        otro = "urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:2.0.0:extended"
        con_otro = cambia(cii, marcador, f"<ram:ID>{otro}</ram:ID>")
        assert [(q.codigo, q.gravedad) for q in spfe(con_otro)] == [("SPFE-ESPECIFICACION", AVISO)]

    def test_lo_que_no_nombra_a_la_aeat_sigue_sin_nada(self):
        assert spfe(cambia(SIN_LOS_BG24, ESPECIFICACION_DEL_EJEMPLO, "urn:cen.eu:en16931:2026")) == []


class TestElQrConYSinUbl:
    """El anexo de abril escribe el QR con `ubl:`; L10 y el ejemplo, sin él."""

    QR_SIN_UBL = "urn:aeat:names:specification:schema:QR"

    def test_sin_ubl_es_el_qr(self):
        sin_ubl = cambia(BUENA, "urn:aeat:names:specification:ubl:schema:QR", self.QR_SIN_UBL)
        assert codigos(sin_ubl) == set()
        sin_direccion = cambia(
            sin_ubl,
            "<cbc:UUID>https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR?nif=B12345674</cbc:UUID>",
            "")
        assert "BT-ES-25" in la(sin_direccion, "SPFE-QR").mensaje

    def test_uno_de_cada_esquema_son_dos(self):
        otro = ("  <cac:AdditionalDocumentReference>\n"
                f"    <cbc:ID>{self.QR_SIN_UBL}</cbc:ID>\n"
                "    <cbc:UUID>https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR</cbc:UUID>\n"
                "    <cbc:DocumentDescription>VERIFACTU</cbc:DocumentDescription>\n"
                "  </cac:AdditionalDocumentReference>\n")
        doble = cambia(BUENA, "  <cac:AccountingSupplierParty>", otro + "  <cac:AccountingSupplierParty>")
        assert la(doble, "SPFE-QR").encontrado == "2"

    def test_un_parecido_no_es_el_qr(self):
        """El calificador entero detrás del esquema, no un trozo."""
        parecido = cambia(BUENA, "urn:aeat:names:specification:ubl:schema:QR",
                          "urn:aeat:names:specification:schema:QRX")
        sin_direccion = cambia(
            parecido,
            "<cbc:UUID>https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR?nif=B12345674</cbc:UUID>",
            "")
        assert "SPFE-QR" not in codigos(sin_direccion)


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
        # Con el número de la orden, BT-ES-5, que en abril era BT-ES-15.
        assert "BT-ES-5" in la(sin, "SPFE-TERCERO").mensaje

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
        assert "BT-ES-25" in quejas[1].mensaje

    def test_el_qr_sin_descripcion_vale(self):
        """La descripción era `1..1` en abril y es `0..1` en la orden.

        Hasta el 07-10-2026, un QR con su dirección y sin descripción salía con
        ERROR. Que la dirección siga siendo obligatoria lo prueba la de arriba.
        """
        sin = cambia(BUENA, "<cbc:DocumentDescription>VERIFACTU</cbc:DocumentDescription>", "")
        assert las(sin, "SPFE-QR") == []


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
        assert queja.encontrado == "05" and "BT-ES-23" in queja.campo  # el número de la orden

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
        # Con los números de la orden: el concepto es BT-ES-21, y el esquema lo pide su grupo.
        assert "BT-ES-21" in queja.mensaje and "«99»" in queja.mensaje and "«WTH» (BG-ES-4)" in queja.mensaje

    def test_la_retencion_sin_su_linea_de_cobro(self):
        linea = ("  <cac:CollectionInvoiceLine>\n    <cbc:ID>urn:aeat:names:specification:ubl:schema:RETE</cbc:ID>\n"
                 "    <cac:Item><cbc:Name>Retencion IRPF</cbc:Name></cac:Item>\n  </cac:CollectionInvoiceLine>\n")
        assert "BT-ES-16" in la(cambia(BUENA, linea, ""), "SPFE-RETENCION").mensaje

    def test_la_linea_de_retencion_sin_retenciones(self):
        inicio = BUENA.index("  <cac:WithholdingTaxTotal>")
        fin = BUENA.index("</cac:WithholdingTaxTotal>\n") + len("</cac:WithholdingTaxTotal>\n")
        assert "BT-ES-17" in la(BUENA[:inicio] + BUENA[fin:], "SPFE-RETENCION").mensaje

    def test_el_grupo_de_entidades_mal_identificado_y_sin_base(self):
        malo = cambia(cambia(CON_GRUPO, "ext:id:REGE", "ext:id:OTRA"),
                      "<aeat:TaxableAmount>95.00</aeat:TaxableAmount>", "")
        queja = la(malo, "SPFE-GRUPO-DE-ENTIDADES")
        assert "BT-ES-29" in queja.mensaje and "BT-ES-30" in queja.mensaje


# --- Que salga del anexo, y que se niegue si el anexo cambia -------------------


# --- La orden publicada ----------------------------------------------------------

# Una factura escrita al pie de la letra del anexo I de la Orden HAC/1028/2026,
# BOE del 05-10-2026 (BOE-A-2026-20587), con las formas que el borrador de abril
# no admitía: el proceso de la orden, sin indicador de copia, el vendedor
# identificado en BT-32 con «LOC» y el atributo «FC» y en BT-30, un anticipo
# pagado, la retención con el calificador de la L7 de la orden y el QR con el
# calificador de L10. Medido el 07-10-2026 sobre `cc0a935`, antes de tocar
# nada: seis ERROR (SPFE-PROCESO, -COPIA, -IMPORTE-PAGADO, -NIF,
# -LINEA-DE-COBRO y -RETENCION). Con las variantes, más: el tercero, el NIF del
# comprador en BT-47 y el QR sin descripción.
PROCESO_DEL_BOE = "urn:aeat:names:specification:ubl:schema:profile:B2B"
L7_DEL_BOE = "urn:aeat:names:specification:schema:add:"

DEL_BOE = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:UBLVersionID>2.5</cbc:UBLVersionID>
  <cbc:CustomizationID>{ESPECIFICACION_DEL_EJEMPLO}</cbc:CustomizationID>
  <cbc:ProfileID>{PROCESO_DEL_BOE}</cbc:ProfileID>
  <cbc:ID>F-2026-0101</cbc:ID>
  <cbc:IssueDate>2026-10-06</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AdditionalDocumentReference>
    <cbc:ID>urn:aeat:names:specification:schema:QR</cbc:ID>
    <cbc:UUID>https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR?nif=B12345674</cbc:UUID>
    <cbc:DocumentDescription>VERIFACTU</cbc:DocumentDescription>
  </cac:AdditionalDocumentReference>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PostalAddress>
      <cbc:StreetName>Calle Mayor 1</cbc:StreetName><cbc:CityName>Madrid</cbc:CityName>
      <cbc:PostalZone>28001</cbc:PostalZone><cbc:CountrySubentity>Madrid</cbc:CountrySubentity>
      <cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country>
    </cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID schemeID="FC">B12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Talleres Ejemplo SL</cbc:RegistrationName><cbc:CompanyID>B12345674</cbc:CompanyID></cac:PartyLegalEntity>
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
  <cac:PrepaidPayment><cbc:PaidAmount currencyID="EUR">20.00</cbc:PaidAmount><cbc:PaidDate>2026-10-06</cbc:PaidDate></cac:PrepaidPayment>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:WithholdingTaxTotal>
    <cbc:TaxAmount currencyID="EUR">15.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">15.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>15</cbc:Percent>
        <cac:TaxScheme><cbc:ID>WTH</cbc:ID><cbc:TaxTypeCode>01</cbc:TaxTypeCode></cac:TaxScheme>
      </cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:WithholdingTaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>
    <cbc:PrepaidAmount currencyID="EUR">20.00</cbc:PrepaidAmount>
    <cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:CollectionInvoiceLine>
    <cbc:ID>{L7_DEL_BOE}RETE</cbc:ID>
    <cac:Item><cbc:Name>Retencion IRPF</cbc:Name></cac:Item>
  </cac:CollectionInvoiceLine>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="H87">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Name>Asesoria fiscal de octubre</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>
      <cac:AdditionalItemProperty><cbc:Name>REGI</cbc:Name><cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>
    </cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">100.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</Invoice>"""

_VENDEDOR_LOC = ('<cac:PartyTaxScheme><cbc:CompanyID schemeID="FC">B12345674</cbc:CompanyID>'
                 '<cac:TaxScheme><cbc:ID>LOC</cbc:ID>')
_COMPRADOR_VAT = ("<cac:PartyTaxScheme><cbc:CompanyID>ESA12345674</cbc:CompanyID>"
                  "<cac:TaxScheme><cbc:ID>VAT</cbc:ID>")
_TERCERO_DEL_BOE = """    <cac:ServiceProviderParty>
      <cbc:ServiceTypeCode>FacturaciónPorTercero</cbc:ServiceTypeCode>
      <cac:Party>
        <cac:PartyTaxScheme><cbc:CompanyID schemeID="FC">B87654321</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
        <cac:PartyLegalEntity><cbc:RegistrationName>Gestoria Ejemplo SL</cbc:RegistrationName></cac:PartyLegalEntity>
      </cac:Party>
    </cac:ServiceProviderParty>
  </cac:Party></cac:AccountingSupplierParty>"""
_COBROS_DEL_BOE = "".join(
    f"""  <cac:CollectionInvoiceLine>
    <cbc:ID>{prefijo}{valor}</cbc:ID>
    <cac:Item><cbc:Name>{nombre}</cbc:Name></cac:Item>
  </cac:CollectionInvoiceLine>
""" for prefijo, valor, nombre in (
        (L7_DEL_BOE, "IEDMT", "Impuesto especial sobre determinados medios de transporte"),
        (L7_DEL_BOE, "SUPL", "Tasas pagadas por cuenta del cliente"),
        (L7_DEL_BOE, "MINO", "Devolucion de un suplido"),
        ("", "OTROS", "Otra tasa"),
    ))

CON_EL_TERCERO_DEL_BOE = cambia(DEL_BOE, "  </cac:Party></cac:AccountingSupplierParty>", _TERCERO_DEL_BOE)
CON_LOS_COBROS_DEL_BOE = cambia(DEL_BOE, "  <cac:InvoiceLine>", _COBROS_DEL_BOE + "  <cac:InvoiceLine>")
CON_EL_COMPRADOR_EN_BT47 = cambia(
    DEL_BOE, _COMPRADOR_VAT,
    '<cac:PartyTaxScheme><cbc:CompanyID schemeID="FC">A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID>')
CON_EL_VENDEDOR_EN_BT31 = cambia(
    DEL_BOE, _VENDEDOR_LOC,
    "<cac:PartyTaxScheme><cbc:CompanyID>ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID>")
CON_LA_RETENCION_SIN_CALIFICADOR = cambia(DEL_BOE, f"{L7_DEL_BOE}RETE<", "RETE<")
CON_EL_QR_SIN_DESCRIPCION = cambia(DEL_BOE, "<cbc:DocumentDescription>VERIFACTU</cbc:DocumentDescription>", "")
# El recargo de equivalencia como lo pone la orden: sin línea propia, en el
# desglose del IVA (BG-23) con la categoría N, su tipo (BT-119) y su cuota
# (BT-117), sobre la misma base que la entrada S. La cuota total y el total con
# impuestos lo suman (BR-CO-14 y BR-CO-15). Medido el 07-10-2026 con la N ya
# admitida: IVA-BASE en ERROR, «base fantasma» al 5,2%, porque ninguna línea
# va a ese tipo, y ninguna puede ir (BT-151 y BT-152 son 1..1 por línea).
CON_EL_RECARGO_EN_EL_DESGLOSE = cambia(cambia(cambia(cambia(
    DEL_BOE,
    "    </cac:TaxSubtotal>\n  </cac:TaxTotal>",
    """    </cac:TaxSubtotal>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">5.20</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>5.2</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>"""),
    '<cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>',
    '<cbc:TaxAmount currencyID="EUR">26.20</cbc:TaxAmount>\n    <cac:TaxSubtotal>'),
    '<cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>',
    '<cbc:TaxInclusiveAmount currencyID="EUR">126.20</cbc:TaxInclusiveAmount>'),
    '<cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>',
    '<cbc:PayableAmount currencyID="EUR">91.20</cbc:PayableAmount>')

# El grupo de entidades de nivel avanzado: la línea lleva el importe total de
# la contraprestación (BT-131) y el desglose, la base imponible a coste
# (BT-116), con la categoría N. Las dos cosas las dice la orden en sus filas, y
# no tienen por qué coincidir. Medido el 07-10-2026: IVA-BASE en ERROR,
# esperado 150,00 (la línea) y encontrado 100,00 (la base a coste).
CON_EL_GRUPO_DE_ENTIDADES = cambia(cambia(cambia(cambia(cambia(
    DEL_BOE,
    '<cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>\n    <cac:Item>',
    '<cbc:LineExtensionAmount currencyID="EUR">150.00</cbc:LineExtensionAmount>\n    <cac:Item>'),
    "<cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent>",
    "<cac:ClassifiedTaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>21</cbc:Percent>"),
    "<cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent>",
    "<cac:TaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>21</cbc:Percent>"),
    """    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>""",
    """    <cbc:LineExtensionAmount currencyID="EUR">150.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">150.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">171.00</cbc:TaxInclusiveAmount>"""),
    '<cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>',
    '<cbc:PayableAmount currencyID="EUR">136.00</cbc:PayableAmount>')

# Una inversión del sujeto pasivo (AE) con el comprador identificado solo en
# BT-47, con «LOC» y «FC», como dice la fila de la orden. BR-AE-02 pide el
# identificador de IVA del comprador (BT-48) o su registro legal (BT-47), y lo
# buscaba donde lo pone la vinculación de 2017, en cac:PartyLegalEntity.
# Medido el 07-10-2026: BR-AE-02 en ERROR, «no identifica fiscalmente al
# comprador», con el NIF del comprador puesto donde lo pide la orden.
CON_AE_Y_EL_COMPRADOR_EN_BT47 = cambia(cambia(cambia(cambia(cambia(cambia(
    CON_EL_COMPRADOR_EN_BT47,
    "<cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent>",
    "<cac:ClassifiedTaxCategory><cbc:ID>AE</cbc:ID><cbc:Percent>0</cbc:Percent>"),
    """      <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme>""",
    """      <cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>AE</cbc:ID><cbc:Percent>0</cbc:Percent><cbc:TaxExemptionReasonCode>VATEX-EU-AE</cbc:TaxExemptionReasonCode><cac:TaxScheme>"""),
    '<cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>',
    '<cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>'),
    '<cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>',
    '<cbc:TaxInclusiveAmount currencyID="EUR">100.00</cbc:TaxInclusiveAmount>'),
    '<cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>',
    '<cbc:PayableAmount currencyID="EUR">65.00</cbc:PayableAmount>'),
    "<cbc:Name>Asesoria fiscal de octubre</cbc:Name>",
    "<cbc:Name>Ejecucion de obra con inversion del sujeto pasivo</cbc:Name>")

# La L8 de la orden da el valor, «REGI», y aparte el calificador
# urn:aeat:names:specification:schema:lin:, sin decir cómo se juntan.
CON_LA_CLAVE_CON_CALIFICADOR = cambia(DEL_BOE, "<cbc:Name>REGI</cbc:Name>",
                                      "<cbc:Name>urn:aeat:names:specification:schema:lin:REGI</cbc:Name>")

# Una segunda línea y su desglose en la categoría N, la del recargo de
# equivalencia en la L4 de la orden, al 5,2%. Medido el 07-10-2026 antes de
# tocar nada: BR-CL-17 y BR-CL-18 en ERROR, e IVA-CATEGORIA-RARA e IVA-TIPO en
# AVISO, porque la lista de 2017 no tiene la N.
_LINEA_N = """  <cac:InvoiceLine>
    <cbc:ID>2</cbc:ID>
    <cbc:InvoicedQuantity unitCode="H87">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">0.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Name>Recargo de equivalencia</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>5.2</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>
      <cac:AdditionalItemProperty><cbc:Name>REGI</cbc:Name><cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>
    </cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">0.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
"""
_SUBTOTAL_N = """    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">0.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>5.2</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>"""
CON_LA_N = cambia(
    cambia(DEL_BOE, "</cac:InvoiceLine>\n</Invoice>", "</cac:InvoiceLine>\n" + _LINEA_N + "</Invoice>"),
    "    </cac:TaxSubtotal>\n  </cac:TaxTotal>", "    </cac:TaxSubtotal>\n" + _SUBTOTAL_N)


def _en_la_categoria(xml: str, viejo: str, nuevo: str) -> str:
    """La línea y el desglose al 21% de una categoría pasados a otra.

    Con el tipo en la búsqueda: la retención de la factura de la orden también
    lleva un `cac:TaxCategory` S, al 15%, y ésa no es del IVA.
    """
    tipo = "</cbc:ID><cbc:Percent>21</cbc:Percent>"
    return cambia(cambia(xml, f"<cac:ClassifiedTaxCategory><cbc:ID>{viejo}{tipo}",
                         f"<cac:ClassifiedTaxCategory><cbc:ID>{nuevo}{tipo}"),
                  f"<cac:TaxCategory><cbc:ID>{viejo}{tipo}", f"<cac:TaxCategory><cbc:ID>{nuevo}{tipo}")


# La D (agencias de viajes) y la F (bienes usados) de la L4 de la orden, con
# la línea y el desglose de la factura de la orden. Antes de publicar solo la
# N tenía prueba: con `_L4_QUE_LA_NORMA_NO_TIENE` reducido a la N, la suite
# entera pasaba y estas dos salían con BR-CL-17 y BR-CL-18 en ERROR (lo vio la
# revisión del 07-10-2026).
CON_LA_D = _en_la_categoria(DEL_BOE, "S", "D")
CON_LA_F = _en_la_categoria(DEL_BOE, "S", "F")
# Y la D con la base del desglose distinta del importe de la línea, que es lo
# que pasa si la base es el margen: el salto de IVA-BASE, medido también en ella.
CON_LA_D_SOBRE_EL_MARGEN = _en_la_categoria(CON_EL_GRUPO_DE_ENTIDADES, "N", "D")

# La referencia catastral con el calificador de L8 delante, como la clave de
# régimen. `_referencias_catastrales` la lee igual que la REGI desde el
# 07-10-2026, y hasta la revisión no lo probaba nadie.
_RCAT_CON_CALIFICADOR = (
    "<cac:AdditionalItemProperty><cbc:Name>urn:aeat:names:specification:schema:lin:RCAT</cbc:Name>"
    "<cbc:Value>9872023VH5797S0001WX</cbc:Value><cbc:ValueQualifier>{}</cbc:ValueQualifier>"
    "</cac:AdditionalItemProperty>")
_REGI_DEL_BOE = ("<cac:AdditionalItemProperty><cbc:Name>REGI</cbc:Name><cbc:Value>01</cbc:Value>"
                 "<cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>")
CON_LA_REFERENCIA_CON_CALIFICADOR = cambia(
    DEL_BOE, _REGI_DEL_BOE, _REGI_DEL_BOE + "\n      " + _RCAT_CON_CALIFICADOR.format("01"))


class TestUnaFacturaEscritaComoDiceLaOrden:
    """La primera tanda del BOE: que lo que la orden admite no salga condenado.

    Lo que la orden ya no admite (las claves 18, 19 y 20, las líneas REEQ y
    REGE, el proceso y la especificación de abril) se sigue aceptando: dejar
    de hacerlo pide poner todas las reglas al texto, y es otra tanda.
    """

    @pytest.mark.parametrize("xml", [
        DEL_BOE, CON_EL_TERCERO_DEL_BOE, CON_LOS_COBROS_DEL_BOE, CON_EL_COMPRADOR_EN_BT47,
        CON_EL_VENDEDOR_EN_BT31, CON_LA_RETENCION_SIN_CALIFICADOR, CON_EL_QR_SIN_DESCRIPCION,
        CON_LA_N, CON_LA_CLAVE_CON_CALIFICADOR, CON_EL_RECARGO_EN_EL_DESGLOSE,
        CON_EL_GRUPO_DE_ENTIDADES, CON_AE_Y_EL_COMPRADOR_EN_BT47,
        CON_LA_D, CON_LA_F, CON_LA_D_SOBRE_EL_MARGEN, CON_LA_REFERENCIA_CON_CALIFICADOR,
    ], ids=["la de la orden", "con el tercero", "con suplidos, minoraciones e impuestos",
            "el comprador en BT-47", "el vendedor en BT-31", "la retención sin calificador",
            "el QR sin descripción", "con la categoría N", "la clave con calificador",
            "el recargo en el desglose", "el grupo de entidades",
            "AE con el comprador en BT-47", "con la categoría D", "con la categoría F",
            "la D sobre el margen", "la referencia catastral con calificador"])
    def test_no_da_ni_un_error_ni_un_aviso_en_todo_el_validador(self, xml):
        informe = factura.validar(xml.encode("utf-8"))
        assert [(i.codigo, i.campo) for i in informe.errores] == []
        assert [(i.codigo, i.campo) for i in informe.avisos] == []

    # Cada frase de lo que la nota SPFE-BORRADOR dice que ya se admite, con un
    # trozo que la reconoce, las facturas que lo demuestran y qué tiene que
    # llevar cada una para que lo demuestre de verdad. Una frase nueva en
    # `LO_QUE_YA_SE_ADMITE` sin su fila aquí no pasa: la nota prometería algo
    # que nadie ha visto pasar el validador entero.
    QUE_LO_DEMUESTRA = (
        ("el tipo de proceso", [DEL_BOE], lambda x: PROCESO_DEL_BOE in x),
        ("sin indicador de copia", [DEL_BOE], lambda x: "CopyIndicator" not in x),
        ("«LOC» y «FC» del vendedor", [DEL_BOE, CON_EL_COMPRADOR_EN_BT47, CON_EL_TERCERO_DEL_BOE],
         lambda x: 'schemeID="FC"' in x),
        ("registro del comprador (BT-47)", [CON_AE_Y_EL_COMPRADOR_EN_BT47],
         lambda x: "<cbc:ID>AE</cbc:ID>" in x and 'schemeID="FC">A12345674' in x),
        ("el importe pagado", [DEL_BOE], lambda x: '<cbc:PrepaidAmount currencyID="EUR">20.00' in x),
        ("su lista L7", [CON_LOS_COBROS_DEL_BOE, CON_LA_RETENCION_SIN_CALIFICADOR],
         lambda x: "<cac:CollectionInvoiceLine>" in x),
        ("nombre del tercero", [CON_EL_TERCERO_DEL_BOE],
         lambda x: "<cbc:RegistrationName>Gestoria Ejemplo SL</cbc:RegistrationName>" in x),
        ("el QR sin descripción", [CON_EL_QR_SIN_DESCRIPCION], lambda x: "VERIFACTU" not in x),
        ("clave de régimen con el calificador", [CON_LA_CLAVE_CON_CALIFICADOR],
         lambda x: "schema:lin:REGI<" in x),
        ("las categorías N, D y F", [CON_LA_N, CON_LA_D, CON_LA_F, CON_EL_RECARGO_EN_EL_DESGLOSE,
                                     CON_EL_GRUPO_DE_ENTIDADES, CON_LA_D_SOBRE_EL_MARGEN],
         lambda x: any(f"<cac:TaxCategory><cbc:ID>{c}</cbc:ID>" in x for c in "NDF")),
    )

    def test_cada_cosa_que_la_nota_dice_admitir_tiene_su_factura(self):
        """Las frases y las filas se casan una a una, y cada factura pasa limpia."""
        frases = solucion_publica.LO_QUE_YA_SE_ADMITE
        for trozo, _, _ in self.QUE_LO_DEMUESTRA:
            casadas = [f for f in frases if trozo in f]
            assert len(casadas) == 1, (trozo, casadas)
        for frase in frases:
            casados = [t for t, _, _ in self.QUE_LO_DEMUESTRA if t in frase]
            assert len(casados) == 1, (frase, casados)
        for trozo, facturas, lo_lleva in self.QUE_LO_DEMUESTRA:
            for xml in facturas:
                assert lo_lleva(xml), trozo
                informe = factura.validar(xml.encode("utf-8"))
                assert [(i.codigo, i.campo) for i in informe.errores + informe.avisos] == [], trozo

    def test_la_nota_y_el_glosario_dicen_la_misma_lista(self):
        """Estaba escrita dos veces y ya no decía lo mismo: el glosario se había
        dejado la clave de régimen. Lo vio el revisor de promesas el 07-10-2026,
        antes de publicar."""
        cosas = solucion_publica.LO_QUE_YA_SE_ADMITE
        frase = "; ".join(cosas[:-1]) + "; y " + cosas[-1]
        assert frase in la(DEL_BOE, "SPFE-BORRADOR").mensaje
        assert frase in glosario.CODIGOS["SPFE-BORRADOR"]

    def test_dice_en_notas_lo_que_ha_aceptado_y_con_que_base(self):
        informe = factura.validar(DEL_BOE.encode("utf-8"))
        assert {i.codigo for i in informe.notas} == {
            "SPFE-BORRADOR", "SPFE-COPIA", "SPFE-IMPORTE-PAGADO", "SPFE-TOTAL-A-PAGAR"}

    def test_el_proceso_de_la_orden_es_el_que_se_pide(self):
        assert las(DEL_BOE, "SPFE-PROCESO") == []
        otro = cambia(DEL_BOE, PROCESO_DEL_BOE, PROCESO_DEL_BOE + "X")
        assert la(otro, "SPFE-PROCESO").esperado == PROCESO_DEL_BOE
        del_ejemplo = cambia(DEL_BOE, PROCESO_DEL_BOE, PROCESO_DEL_EJEMPLO)
        nota = la(del_ejemplo, "SPFE-PROCESO")
        # Una NOTA que ya no dice que el texto no está publicado: dice el valor
        # que fija la orden, y que es el que manda.
        assert nota.gravedad == NOTA and nota.esperado == PROCESO_DEL_BOE
        assert "05-10-2026" in nota.mensaje and "no está publicad" not in nota.mensaje

    def test_el_nif_con_loc_tiene_que_llevar_fc(self):
        """La orden pide las dos cosas: el impuesto «LOC» y el atributo «FC»."""
        sin_fc = cambia(DEL_BOE, ' schemeID="FC">B12345674', ">B12345674")
        queja = la(sin_fc, "SPFE-NIF")
        assert queja.campo == "NIF del vendedor (BT-31 o BT-32)"
        assert queja.encontrado == "B12345674 con el impuesto «LOC»"
        otro = cambia(DEL_BOE, ' schemeID="FC">B12345674', ' schemeID="NIF">B12345674')
        assert la(otro, "SPFE-NIF").encontrado == "B12345674 con el impuesto «LOC» y schemeID «NIF»"

    @pytest.mark.parametrize("identificador", [
        f"{L7_DEL_BOE}REEQ",        # la de abril, con el calificador de la orden
        f"{L7_DEL_BOE}RETEX",       # un parecido
        f"X{L7_DEL_BOE}RETE",       # el calificador con algo delante
        "urn:aeat:names:specification:ubl:schema:IEDMT",  # la de la orden, con la URN de abril
        "REGE",                     # la de abril, sin calificador
    ])
    def test_lo_que_no_es_de_ninguna_l7_sigue_sin_valer(self, identificador):
        mala = cambia(DEL_BOE, f"{L7_DEL_BOE}RETE<", f"{identificador}<")
        assert la(mala, "SPFE-LINEA-DE-COBRO").encontrado == identificador

    def test_dos_retenciones_son_dos_aunque_se_escriban_distinto(self):
        """Una con la URN de abril y otra con el calificador de la orden siguen
        siendo dos grupos de retenciones, y la orden admite uno (`0..1`)."""
        otra = """  <cac:CollectionInvoiceLine>
    <cbc:ID>urn:aeat:names:specification:ubl:schema:RETE</cbc:ID>
    <cac:Item><cbc:Name>Otra retencion</cbc:Name></cac:Item>
  </cac:CollectionInvoiceLine>
"""
        doble = cambia(DEL_BOE, "  <cac:InvoiceLine>", otra + "  <cac:InvoiceLine>")
        assert "retenciones" in la(doble, "SPFE-LINEA-DE-COBRO").mensaje

    def test_la_retencion_de_la_orden_se_reconoce_y_se_le_mide_lo_demas(self):
        """Antes no se veía la línea, y salía que le faltaba. Ahora se ve, y se
        le pide la suma, como a la de abril."""
        inicio = DEL_BOE.index("  <cac:WithholdingTaxTotal>")
        fin = DEL_BOE.index("</cac:WithholdingTaxTotal>\n") + len("</cac:WithholdingTaxTotal>\n")
        sin_suma = DEL_BOE[:inicio] + DEL_BOE[fin:]
        assert "la suma de retenciones" in la(sin_suma, "SPFE-RETENCION").mensaje

    def test_al_tercero_de_la_orden_se_le_pide_el_nombre_y_el_fc(self):
        sin_nombre = cambia(CON_EL_TERCERO_DEL_BOE,
                            "<cbc:RegistrationName>Gestoria Ejemplo SL</cbc:RegistrationName>", "")
        assert "el nombre o razón social (BT-ES-3)" in la(sin_nombre, "SPFE-TERCERO").mensaje
        sin_fc = cambia(CON_EL_TERCERO_DEL_BOE, ' schemeID="FC">B87654321', ">B87654321")
        assert "«LOC» con el atributo «FC»" in la(sin_fc, "SPFE-TERCERO").mensaje

    @pytest.mark.parametrize(("xml", "categoria"), [
        (CON_LA_N, "N"), (CON_LA_D, "D"), (CON_LA_F, "F"),
    ], ids=["N", "D", "F"])
    def test_la_n_la_d_y_la_f_se_aceptan_y_se_dice_con_que_base(self, xml, categoria):
        nota = la(xml, "SPFE-CATEGORIA")
        assert nota.gravedad == NOTA and nota.encontrado == categoria
        assert "lista L4 de la orden" in nota.mensaje and "no se ha comprobado" in nota.mensaje
        # Las cuatro reglas que no se les aplican, con su nombre: decía «los
        # tipos de IVA» y callaba IVA-CATEGORIA-RARA (el revisor de promesas,
        # antes de publicar).
        for regla in ("BR-CL-17", "BR-CL-18", "IVA-CATEGORIA-RARA", "IVA-TIPO"):
            assert regla in nota.mensaje, regla

    def test_la_n_tiene_nombre_en_los_mensajes_de_la_norma(self):
        """Ni «categoría no reconocida» en el mismo informe que dice que la admite.

        Con la cuota del recargo mal, BR-CO-17 hablaba de «N (categoría no
        reconocida)» y la NOTA SPFE-CATEGORIA de la misma factura decía que la
        N está en la L4 de la orden. Lo vio la revisión del 07-10-2026, antes
        de publicar. El nombre va aparte
        de `iva.CATEGORIAS`, que es la lista de la norma y la que da el «Las
        admitidas son…» de IVA-CATEGORIA-RARA.
        """
        mala = cambia(CON_EL_RECARGO_EN_EL_DESGLOSE,
                      '<cbc:TaxAmount currencyID="EUR">5.20</cbc:TaxAmount>',
                      '<cbc:TaxAmount currencyID="EUR">9.00</cbc:TaxAmount>')
        cuota = next(i for i in factura.validar(mala.encode("utf-8")).errores
                     if i.codigo == "BR-CO-17")
        assert "no reconocida" not in cuota.mensaje and "no reconocida" not in cuota.campo
        assert "N (regímenes nacionales" in cuota.mensaje
        for codigo in ("N", "D", "F"):
            assert "no reconocida" not in iva.nombre_categoria(codigo)
            assert codigo not in iva.CATEGORIAS
        assert iva.nombre_categoria("X") == "X (categoría no reconocida)"

    def test_un_abono_no_recibe_la_lista_de_la_orden(self):
        """Al abono no se le mide con el anexo, y por eso tampoco con su L4.

        `solucion_publica.reglas` corta en el abono antes de `_categorias`, y
        la NOTA que dice qué se aceptó no salía; pero la N se aceptaba igual,
        sin BR-CL-17, BR-CL-18 ni los avisos de IVA. Lo vio la revisión del
        07-10-2026, antes de publicar.
        """
        abono = (CON_LA_N.replace("Invoice-2", "CreditNote-2")
                 .replace("<Invoice ", "<CreditNote ").replace("</Invoice>", "</CreditNote>")
                 .replace("<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>",
                          "<cbc:CreditNoteTypeCode>381</cbc:CreditNoteTypeCode>")
                 .replace("<cac:InvoiceLine>", "<cac:CreditNoteLine>")
                 .replace("</cac:InvoiceLine>", "</cac:CreditNoteLine>")
                 .replace("<cbc:InvoicedQuantity", "<cbc:CreditedQuantity")
                 .replace("</cbc:InvoicedQuantity>", "</cbc:CreditedQuantity>"))
        assert "<Invoice " not in abono and "<cac:InvoiceLine>" not in abono
        informe = factura.validar(abono.encode("utf-8"))
        assert {"BR-CL-17", "BR-CL-18"} <= {i.codigo for i in informe.errores}
        assert "SPFE-CATEGORIA" not in {i.codigo for i in informe.incidencias}

    def test_la_referencia_catastral_con_calificador_se_mide(self):
        mala = cambia(DEL_BOE, _REGI_DEL_BOE, _REGI_DEL_BOE + _RCAT_CON_CALIFICADOR.format("05"))
        assert la(mala, "SPFE-REFERENCIA-CATASTRAL").encontrado == "05"

    def test_la_n_no_tapa_un_codigo_que_no_es_de_ninguna_lista(self):
        """La N se añade a la lista; la queja no se borra después.

        Con `_SOBRA_SI`, que apaga el código entero, una X en otra línea de la
        misma factura se habría callado con la N. Así sigue saliendo, y sola.
        """
        con_una_x = cambia(CON_LA_N, "<cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>",
                           "<cbc:ID>X</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>")
        queja = next(i for i in factura.validar(con_una_x.encode("utf-8")).errores
                     if i.codigo == "BR-CL-18")
        assert queja.encontrado == "X"

    def test_sin_declarar_la_solucion_publica_la_n_se_mide_como_siempre(self):
        """Qué lista rige para quien declara la edición de 2026 sin la solución
        pública no está decidido, y entretanto no se cambia nada."""
        sin = cambia(CON_LA_N, ESPECIFICACION_DEL_EJEMPLO, "urn:cen.eu:en16931:2026")
        errores = {i.codigo for i in factura.validar(sin.encode("utf-8")).errores}
        assert {"BR-CL-17", "BR-CL-18"} <= errores

    @pytest.mark.parametrize("nombre", [
        "XREGI", "urn:aeat:names:specification:schema:lin:REGIX",
        "urn:aeat:names:specification:ubl:schema:lin:REGI",
    ])
    def test_un_parecido_de_regi_no_es_una_clave_de_regimen(self, nombre):
        parecido = cambia(DEL_BOE, "<cbc:Name>REGI</cbc:Name>", f"<cbc:Name>{nombre}</cbc:Name>")
        assert la(parecido, "SPFE-CLAVE-DE-REGIMEN").encontrado == "(falta)"

    def test_la_base_de_la_n_no_se_compara_pero_su_cuota_si(self):
        """La base no se ata a las líneas; BR-CO-17 sigue atando la cuota."""
        mala = cambia(CON_EL_RECARGO_EN_EL_DESGLOSE,
                      '<cbc:TaxAmount currencyID="EUR">5.20</cbc:TaxAmount>',
                      '<cbc:TaxAmount currencyID="EUR">9.00</cbc:TaxAmount>')
        errores = {i.codigo for i in factura.validar(mala.encode("utf-8")).errores}
        assert "BR-CO-17" in errores and "IVA-BASE" not in errores

    def test_bt47_de_la_orden_solo_cuenta_con_loc_y_fc(self):
        sin_fc = cambia(CON_AE_Y_EL_COMPRADOR_EN_BT47, ' schemeID="FC">A12345674', ">A12345674")
        errores = {i.codigo for i in factura.validar(sin_fc.encode("utf-8")).errores}
        assert "BR-AE-02" in errores
        # Y la otra mitad: el FC bajo otro impuesto que «LOC» tampoco es el
        # BT-47 de la orden. Hasta la revisión del 07-10-2026 solo se quitaba
        # el FC, y el filtro de «LOC» se podía borrar sin que nada fallara.
        otro_impuesto = cambia(
            CON_AE_Y_EL_COMPRADOR_EN_BT47,
            'schemeID="FC">A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID>',
            'schemeID="FC">A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>IRPF</cbc:ID>')
        errores = {i.codigo for i in factura.validar(otro_impuesto.encode("utf-8")).errores}
        assert "BR-AE-02" in errores

    @pytest.mark.parametrize(("viejo", "nuevo"), [
        ('schemeID="FC">A12345674', 'schemeID="FC ">A12345674'),
        ("A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID>",
         "A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC </cbc:ID>"),
        ("A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID>",
         "A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>\n LOC\n</cbc:ID>"),
    ], ids=["FC con un espacio", "LOC con un espacio", "LOC entre saltos de línea"])
    def test_los_espacios_de_loc_y_fc_se_leen_igual_en_las_dos_reglas(self, viejo, nuevo):
        """SPFE-NIF y BR-AE-02 no pueden decir lo contrario del mismo NIF.

        `_nif_bien_puesto` recorta los espacios, como todo el módulo; el BT-47
        de la orden se buscaba con el texto exacto, y un espacio tras «FC»
        daba el NIF por bien puesto y, a la vez, al comprador por no
        identificado. Lo vio la revisión del 07-10-2026, antes de publicar.
        """
        con_espacios = cambia(CON_AE_Y_EL_COMPRADOR_EN_BT47, viejo, nuevo)
        errores = {i.codigo for i in factura.validar(con_espacios.encode("utf-8")).errores}
        assert errores == set()

    def test_sin_desglose_el_bt47_de_la_orden_sigue_contando(self):
        """La rama de BR-CO-18 también mira BR-AE-02, y tiene que mirarlo igual.

        Esa rama no recibía el sitio de la orden, y una AE sin desglose salía
        con BR-AE-02 por tener al comprador donde lo pone la orden, además de
        con BR-CO-18 por no traer desglose. Lo vio la revisión del 07-10-2026,
        antes de publicar.
        """
        inicio = CON_AE_Y_EL_COMPRADOR_EN_BT47.index("  <cac:TaxTotal>")
        fin = CON_AE_Y_EL_COMPRADOR_EN_BT47.index("</cac:TaxTotal>\n") + len("</cac:TaxTotal>\n")
        sin_desglose = CON_AE_Y_EL_COMPRADOR_EN_BT47[:inicio] + CON_AE_Y_EL_COMPRADOR_EN_BT47[fin:]
        errores = {i.codigo for i in factura.validar(sin_desglose.encode("utf-8")).errores}
        assert "BR-CO-18" in errores and "BR-AE-02" not in errores

    def test_sin_declarar_la_solucion_publica_bt47_es_el_de_la_norma(self):
        """Fuera de la solución pública, BT-47 sigue siendo el registro legal
        de la vinculación de 2017, y el NIF con LOC no lo cumple."""
        sin = cambia(CON_AE_Y_EL_COMPRADOR_EN_BT47, ESPECIFICACION_DEL_EJEMPLO, "urn:cen.eu:en16931:2026")
        errores = {i.codigo for i in factura.validar(sin.encode("utf-8")).errores}
        assert "BR-AE-02" in errores

    def test_el_qr_con_el_calificador_solo_se_reconoce(self):
        """La fila dice «usar «QR»», y la lista L10 da el esquema aparte.

        Hasta el 07-10-2026 un QR escrito «QR» a secas no era el QR: no se le
        miraba ni la dirección ni si estaba repetido. Ahora sí, y sin la
        dirección sale el ERROR de siempre.
        """
        solo = cambia(DEL_BOE, "<cbc:ID>urn:aeat:names:specification:schema:QR</cbc:ID>",
                      "<cbc:ID>QR</cbc:ID>")
        assert las(solo, "SPFE-QR") == []
        sin_direccion = cambia(
            solo,
            "<cbc:UUID>https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR?nif=B12345674</cbc:UUID>",
            "")
        assert la(sin_direccion, "SPFE-QR").encontrado == "(falta)"

    def test_ningun_mensaje_dice_que_la_orden_no_esta_publicada(self):
        """Ni en la factura de la orden ni en sus variantes, ni rompiéndolas.

        Hasta el 07-10-2026 varios mensajes decían que el anexo nuevo «no está
        publicado» o que «el anexo nuevo» lo fijaría: la rectificativa, el 381,
        el identificador de la AEAT y el total a pagar.
        """
        casos = [
            DEL_BOE, CON_LA_N, CON_EL_TERCERO_DEL_BOE, CON_LOS_COBROS_DEL_BOE,
            cambia(DEL_BOE, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>381<"),
            cambia(DEL_BOE, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>384<"),
            cambia(DEL_BOE, ESPECIFICACION_DEL_EJEMPLO,
                   "urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:2.0.0:extended"),
            EJEMPLO, SIN_LOS_BG24,
            # Un R9 solo: el AVISO de fuera de L2.A y el «falta la modalidad».
            # Ninguno de los de arriba llegaba a esos dos mensajes, y los dos
            # podían volver a decir «no está publicado» con la suite verde.
            cambia(cambia(DEL_BOE, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>384<"),
                   "  <cac:AccountingSupplierParty>",
                   TestLosCalificadoresDeL10.adjunto(
                       "urn:aeat:names:specification:schema:RECT:TIPO", "texto libre", "R9")
                   + "  <cac:AccountingSupplierParty>"),
        ]
        for xml in casos:
            for i in spfe(xml):
                assert "no está publicad" not in i.mensaje, (i.codigo, i.mensaje)
                assert "anexo nuevo" not in i.mensaje, (i.codigo, i.mensaje)

    def test_el_381_manda_a_los_bg24_de_la_orden(self):
        queja = la(cambia(DEL_BOE, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>381<"),
                   "SPFE-TIPO-DE-FACTURA")
        assert "RECT:TIPO" in queja.mensaje and "BT-3" in queja.mensaje
        assert "extensión" not in queja.mensaje

    def test_otro_identificador_de_la_aeat_pide_el_de_la_orden(self):
        otro = cambia(DEL_BOE, ESPECIFICACION_DEL_EJEMPLO,
                      "urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:2.0.0:extended")
        queja = la(otro, "SPFE-ESPECIFICACION")
        assert queja.esperado == ESPECIFICACION_DEL_EJEMPLO
        assert "ejemplo" not in queja.mensaje

    def test_el_total_a_pagar_nombra_la_l7_de_la_orden(self):
        nota = la(CON_LOS_COBROS_DEL_BOE, "SPFE-TOTAL-A-PAGAR")
        assert "IEDMT" in nota.mensaje and "BT-115" in nota.mensaje

    def test_el_ejemplo_de_las_claves_sale_de_las_listas(self):
        """El mensaje decía que la 20 existe en el IVA: en la L3A de la orden ya
        no. El ejemplo de ahora vale con las dos, y se comprueba con la tabla."""
        queja = la(cambia(DEL_BOE, "<cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA<",
                          "<cbc:Value>17</cbc:Value><cbc:ValueQualifier>IVA<"),
                   "SPFE-CLAVE-DE-REGIMEN")
        assert "la 17 existe en el IGIC y no en el IVA" in queja.mensaje
        assert "la 02 en el IVA y no en el IPSI" in queja.mensaje
        listas = cius_es.LISTAS
        assert "17" in listas["L3B"].valores and "17" not in listas["L3A"].valores
        assert "02" in listas["L3A"].valores and "02" not in listas["L3C"].valores

    def test_la_k_sigue_fuera_de_la_l4_de_la_orden(self):
        con_k = cambia(DEL_BOE, "<cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID>",
                       "<cac:ClassifiedTaxCategory><cbc:ID>K</cbc:ID>")
        queja = next(i for i in las(con_k, "SPFE-CATEGORIA") if i.gravedad == ERROR)
        assert queja.encontrado == "K" and "N" in queja.esperado


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

    def test_si_aparece_l10_se_niega_hasta_terminar_de_leer_el_bg24(self, monkeypatch):
        """El anexo de abril tiene de L1 a L8, sin L9 ni L10.

        L10 es la lista de calificadores que la AEAT escribio en las
        transparencias del 10-09-2026 y en el correo del 23-09-2026. Desde el
        ejemplo del 02-10-2026 el tipo y la modalidad se comprueban contra
        L2.A y L2.B en cbc:DocumentTypeCode, con AVISO. El dia que llegue el
        texto queda por hacer: confirmar ese sitio, exigir los importes
        cuando la modalidad es S y pasar a ERROR lo que hoy es NOTA o AVISO.
        Es una anotacion que no depende de que nadie se acuerde.
        """
        assert "L10" not in cius_es.LISTAS, "ya llego: hay una regla que terminar"
        monkeypatch.setitem(cius_es.LISTAS, "L10", cius_es.LISTAS["L2.B"])
        try:
            with pytest.raises(LookupError) as negativa:
                importlib.reload(solucion_publica)
            assert type(negativa.value).__name__ == "AnexoCambiado"
            assert "DocumentTypeCode" in str(negativa.value)
            assert "modalidad es S" in str(negativa.value)
            assert "ERROR" in str(negativa.value)
        finally:
            monkeypatch.undo()
            importlib.reload(solucion_publica)

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
