"""Comprobaciones de las reglas de negocio EN 16931."""

from decimal import Decimal

import pytest

from validador import en16931
from validador.en16931 import AVISO, ERROR


def factura(
    lineas=((("1", "100.00"),)),
    suma_lineas="100.00",
    base="100.00",
    impuestos="21.00",
    con_impuestos="121.00",
    a_pagar="121.00",
    descuentos=None,
    cargos=None,
    anticipos=None,
    redondeo=None,
    perfil="urn:cen.eu:en16931:2017",
    categoria="S",
    tipo_iva="21",
    base_iva=None,
    omitir=(),
):
    """Construye una factura UBL. `omitir` quita campos para probar las BR."""

    def campo(etiqueta, valor, ns="cbc"):
        if etiqueta in omitir or valor is None:
            return ""
        return f"<{ns}:{etiqueta}>{valor}</{ns}:{etiqueta}>"

    iva_de_linea = (
        ""
        if categoria is None
        else f"""<cac:Item><cac:ClassifiedTaxCategory>
          <cbc:ID>{categoria}</cbc:ID><cbc:Percent>{tipo_iva}</cbc:Percent>
        </cac:ClassifiedTaxCategory></cac:Item>"""
    )

    xml_lineas = "".join(
        f"""<cac:InvoiceLine><cbc:ID>{ident}</cbc:ID>
        {'' if 'LineExtensionAmount' in omitir else
         f'<cbc:LineExtensionAmount currencyID="EUR">{importe}</cbc:LineExtensionAmount>'}
        {iva_de_linea}
        </cac:InvoiceLine>"""
        for ident, importe in lineas
    )
    if "InvoiceLine" in omitir:
        xml_lineas = ""

    def total(etiqueta, valor):
        if etiqueta in omitir or valor is None:
            return ""
        return f'<cbc:{etiqueta} currencyID="EUR">{valor}</cbc:{etiqueta}>'

    vendedor = (
        ""
        if "vendedor" in omitir
        else """<cac:AccountingSupplierParty><cac:Party>
        <cac:PostalAddress><cac:Country>
          <cbc:IdentificationCode>ES</cbc:IdentificationCode>
        </cac:Country></cac:PostalAddress>
        <cac:PartyLegalEntity><cbc:RegistrationName>Vendedor SL</cbc:RegistrationName>
        </cac:PartyLegalEntity></cac:Party></cac:AccountingSupplierParty>"""
    )
    comprador = (
        ""
        if "comprador" in omitir
        else """<cac:AccountingCustomerParty><cac:Party>
        <cac:PostalAddress><cac:Country>
          <cbc:IdentificationCode>ES</cbc:IdentificationCode>
        </cac:Country></cac:PostalAddress>
        <cac:PartyLegalEntity><cbc:RegistrationName>Comprador SA</cbc:RegistrationName>
        </cac:PartyLegalEntity></cac:Party></cac:AccountingCustomerParty>"""
    )
    # Una factura EN 16931 de verdad siempre trae el desglose por tipo de IVA,
    # no solo el importe total. Sin él, `iva.py` avisa y con razón.
    xml_impuestos = (
        ""
        if impuestos is None
        else f"""<cac:TaxTotal>
      <cbc:TaxAmount currencyID="EUR">{impuestos}</cbc:TaxAmount>
      {'' if 'TaxSubtotal' in omitir else f'''<cac:TaxSubtotal>
        <cbc:TaxableAmount currencyID="EUR">{base if base_iva is None else base_iva}</cbc:TaxableAmount>
        <cbc:TaxAmount currencyID="EUR">{impuestos}</cbc:TaxAmount>
        <cac:TaxCategory>
          <cbc:ID>{categoria}</cbc:ID><cbc:Percent>{tipo_iva}</cbc:Percent>
        </cac:TaxCategory>
      </cac:TaxSubtotal>'''}
    </cac:TaxTotal>"""
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  {campo('CustomizationID', perfil)}
  {campo('ID', 'F-2026-001')}
  {campo('IssueDate', '2026-09-07')}
  {campo('InvoiceTypeCode', '380')}
  {campo('DocumentCurrencyCode', 'EUR')}
  {vendedor}
  {comprador}
  {xml_impuestos}
  <cac:LegalMonetaryTotal>
    {total('LineExtensionAmount', suma_lineas)}
    {total('TaxExclusiveAmount', base)}
    {total('TaxInclusiveAmount', con_impuestos)}
    {total('AllowanceTotalAmount', descuentos)}
    {total('ChargeTotalAmount', cargos)}
    {total('PrepaidAmount', anticipos)}
    {total('PayableRoundingAmount', redondeo)}
    {total('PayableAmount', a_pagar)}
  </cac:LegalMonetaryTotal>
  {xml_lineas}
</Invoice>"""


def abono(**opciones):
    """La misma factura, escrita como abono (CreditNote).

    Un abono no es un documento exótico: es con lo que se corrige una factura,
    y el RD 238/2026 lo trata igual. En UBL cambian tres cosas —el elemento
    raíz, el código de tipo y el nombre de las líneas— y todo lo demás es
    idéntico, así que se genera reescribiendo la factura. Hacerlo así obliga a
    que las dos vayan siempre a la par: no se puede arreglar una y olvidar la
    otra.
    """
    return (
        factura(**opciones)
        .replace("schema:xsd:Invoice-2", "schema:xsd:CreditNote-2")
        .replace("<Invoice ", "<CreditNote ")
        .replace("</Invoice>", "</CreditNote>")
        .replace(
            "<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>",
            "<cbc:CreditNoteTypeCode>381</cbc:CreditNoteTypeCode>",
        )
        .replace("<cac:InvoiceLine>", "<cac:CreditNoteLine>")
        .replace("</cac:InvoiceLine>", "</cac:CreditNoteLine>")
    )


@pytest.fixture(params=["factura", "abono"])
def documento(request):
    """Cada comprobación de esta clase se hace sobre los dos documentos.

    Antes solo se probaba la factura, y por eso pasó lo siguiente: el mapa de
    UBL apuntaba a `InvoiceTypeCode` e `InvoiceLine`, que en un abono se
    llaman de otra forma. Un abono correcto salía con BR-04 y BR-16
    inventados y, al no encontrársele las líneas, enmudecían de golpe BR-24,
    BR-CO-10 y todas las reglas de IVA. Los 375 tests seguían en verde porque
    ninguno pasaba las reglas de negocio sobre un abono.
    """
    return factura if request.param == "factura" else abono


def codigos(informe, gravedad=None):
    return {
        i.codigo
        for i in informe.incidencias
        if gravedad is None or i.gravedad == gravedad
    }


class TestSobreFacturaYAbono:
    """Las reglas que dependen del tipo de documento o de las líneas.

    Son justo las que el mapa equivocado rompía, así que se prueban sobre los
    dos documentos. La factura ya las tenía cubiertas más abajo; lo que aquí
    se garantiza es que el abono no vuelva a quedarse fuera.
    """

    def test_documento_correcto_sin_errores(self, documento):
        informe = en16931.validar(documento())
        assert informe.conforme, informe.detalle()
        assert not informe.avisos, informe.detalle()

    def test_se_le_encuentran_las_lineas(self, documento):
        informe = en16931.validar(documento())
        assert "BR-16" not in codigos(informe), informe.detalle()

    def test_sin_lineas_salta_br_16(self, documento):
        informe = en16931.validar(documento(omitir=("InvoiceLine",)))
        assert "BR-16" in codigos(informe, ERROR)

    def test_linea_sin_importe_salta_br_24(self, documento):
        informe = en16931.validar(documento(omitir=("LineExtensionAmount",)))
        assert "BR-24" in codigos(informe, ERROR)

    def test_las_lineas_no_cuadran_con_el_total(self, documento):
        informe = en16931.validar(
            documento(lineas=(("1", "90.00"),), suma_lineas="100.00")
        )
        assert "BR-CO-10" in codigos(informe, ERROR), informe.detalle()

    def test_el_desglose_de_iva_se_comprueba(self, documento):
        # La base del desglose dice 150.00 y la línea son 100.00. Si no se
        # leen las líneas, esta regla calla y el error más caro pasa.
        informe = en16931.validar(documento(base_iva="150.00"))
        assert "BR-S-8" in codigos(informe, ERROR), informe.detalle()

    def test_sin_codigo_de_tipo_salta_br_04(self, documento):
        informe = en16931.validar(documento(omitir=("InvoiceTypeCode",)))
        assert "BR-04" in codigos(informe, ERROR)

    def test_el_mensaje_de_br_04_vale_para_los_dos(self, documento):
        informe = en16931.validar(documento(omitir=("InvoiceTypeCode",)))
        incidencia = next(i for i in informe.errores if i.codigo == "BR-04")
        # Decir solo «380 para factura ordinaria» deja al que trae un abono
        # sin la respuesta, que es el número que necesita.
        assert "381" in incidencia.mensaje


class TestFacturaCorrecta:
    def test_sin_errores(self):
        informe = en16931.validar(factura())
        assert informe.conforme, informe.detalle()
        assert not informe.errores

    def test_resumen_legible(self):
        assert "sin errores" in en16931.validar(factura()).resumen()

    def test_con_descuentos_y_cargos(self):
        informe = en16931.validar(
            factura(
                suma_lineas="100.00",
                descuentos="10.00",
                cargos="5.00",
                base="95.00",
                impuestos="19.95",
                con_impuestos="114.95",
                a_pagar="114.95",
            )
        )
        assert informe.conforme, informe.detalle()

    def test_con_anticipo(self):
        informe = en16931.validar(
            factura(anticipos="21.00", a_pagar="100.00")
        )
        assert informe.conforme, informe.detalle()


class TestCamposObligatorios:
    @pytest.mark.parametrize(
        "campo,codigo",
        [
            ("ID", "BR-02"),
            ("IssueDate", "BR-03"),
            ("InvoiceTypeCode", "BR-04"),
            ("DocumentCurrencyCode", "BR-05"),
        ],
    )
    def test_falta_campo_de_cabecera(self, campo, codigo):
        informe = en16931.validar(factura(omitir=(campo,)))
        assert codigo in codigos(informe, ERROR)

    def test_falta_el_vendedor(self):
        informe = en16931.validar(factura(omitir=("vendedor",)))
        assert {"BR-06", "BR-08", "BR-09"} <= codigos(informe, ERROR)

    def test_falta_el_comprador(self):
        informe = en16931.validar(factura(omitir=("comprador",)))
        assert {"BR-07", "BR-10", "BR-11"} <= codigos(informe, ERROR)

    def test_sin_lineas(self):
        informe = en16931.validar(factura(omitir=("InvoiceLine",)))
        assert "BR-16" in codigos(informe, ERROR)

    def test_linea_sin_importe(self):
        informe = en16931.validar(factura(omitir=("LineExtensionAmount",)))
        assert "BR-24" in codigos(informe, ERROR)

    def test_el_mensaje_dice_que_falta(self):
        informe = en16931.validar(factura(omitir=("ID",)))
        incidencia = next(i for i in informe.errores if i.codigo == "BR-02")
        assert "número" in incidencia.mensaje.lower()
        assert incidencia.encontrado == "(falta)"


class TestCuadreAritmetico:
    def test_suma_de_lineas_no_cuadra(self):
        informe = en16931.validar(
            factura(
                lineas=(("1", "60.00"), ("2", "30.00")),  # suman 90, no 100
                suma_lineas="100.00",
            )
        )
        assert "BR-CO-10" in codigos(informe, ERROR)
        incidencia = next(i for i in informe.errores if i.codigo == "BR-CO-10")
        assert "90.00" in incidencia.esperado
        assert "2 líneas" in incidencia.esperado
        assert incidencia.encontrado == "100.00"

    def test_base_imponible_no_cuadra(self):
        informe = en16931.validar(factura(suma_lineas="100.00", base="90.00"))
        assert "BR-CO-13" in codigos(informe, ERROR)

    def test_el_mensaje_explica_el_calculo(self):
        informe = en16931.validar(
            factura(suma_lineas="100.00", descuentos="10.00", base="100.00")
        )
        incidencia = next(i for i in informe.errores if i.codigo == "BR-CO-13")
        assert "descuentos" in incidencia.esperado
        assert "90.00" in incidencia.esperado

    def test_total_con_impuestos_no_cuadra(self):
        informe = en16931.validar(factura(impuestos="21.00", con_impuestos="130.00"))
        assert "BR-CO-15" in codigos(informe, ERROR)

    def test_a_pagar_no_cuadra(self):
        informe = en16931.validar(factura(a_pagar="200.00"))
        assert "BR-CO-16" in codigos(informe, ERROR)

    def test_sin_importe_de_impuestos_avisa_pero_no_falla(self):
        """El aviso se llama IVA-SIN-TOTAL: BR-CO-14 es otra cosa.

        BR-CO-14 es de la norma y dice que el total de IVA sea la suma de las
        cuotas del desglose. Se estaba usando ese código para un aviso propio.
        Ahora la regla de verdad vive en `iva.py` y el aviso lleva un código
        de la casa.
        """
        informe = en16931.validar(factura(impuestos=None, con_impuestos="100.00"))
        assert "IVA-SIN-TOTAL" in codigos(informe, AVISO)
        assert "BR-CO-15" not in codigos(informe, ERROR)

    def test_sin_desglose_de_iva_no_hay_factura(self):
        """BR-CO-18: sin desglose no hay factura valida, y no es un aviso.

        Antes esto era un aviso propio y la factura salia "conforme". Una
        factura sin desglose de IVA no la acepta ningun receptor: darla por
        buena era el error mas caro que podia cometer este validador, porque
        el usuario se fia y la manda.
        """
        informe = en16931.validar(factura(omitir=("TaxSubtotal",)))
        assert "BR-CO-18" in codigos(informe, ERROR)
        assert not informe.conforme


class TestRedondeo:
    def test_un_centimo_de_diferencia_se_tolera(self):
        # La norma trabaja con dos decimales: un céntimo es redondeo, no error.
        informe = en16931.validar(
            factura(lineas=(("1", "33.33"), ("2", "33.33"), ("3", "33.33")),
                    suma_lineas="100.00", base="100.00",
                    impuestos="21.00", con_impuestos="121.00", a_pagar="121.00")
        )
        assert "BR-CO-10" not in codigos(informe, ERROR), informe.detalle()

    def test_dos_centimos_ya_es_error(self):
        informe = en16931.validar(
            factura(lineas=(("1", "33.33"), ("2", "33.33"), ("3", "33.32")),
                    suma_lineas="100.00")
        )
        assert "BR-CO-10" in codigos(informe, ERROR)

    def test_no_usa_float(self):
        """0.1 + 0.2 no da 0.3 en float. Con Decimal, sí."""
        informe = en16931.validar(
            factura(
                lineas=(("1", "0.10"), ("2", "0.20")),
                suma_lineas="0.30",
                base="0.30",
                impuestos="0.06",
                con_impuestos="0.36",
                a_pagar="0.36",
            )
        )
        assert informe.conforme, informe.detalle()
        # Y la prueba de que el problema era real:
        assert 0.1 + 0.2 != 0.3
        assert Decimal("0.10") + Decimal("0.20") == Decimal("0.30")


class TestOtrosFormatos:
    def test_facturae_se_lo_queda_su_propio_modulo(self):
        """Este modulo implementa la norma europea sobre UBL y CII y ya esta.

        Las reglas de Facturae salen de otro sitio -del propio esquema del
        formato- y las aplica `facturae.py`. Aqui, callarse es lo correcto: el
        SIN-SOPORTE que salia antes era un aviso que sobraba y se quedaba corto
        a la vez.
        """
        xml = """<?xml version="1.0"?>
<fe:Facturae xmlns:fe="http://www.facturae.es/Facturae/2009/v3.2/Facturae">
  <FileHeader><SchemaVersion>3.2</SchemaVersion></FileHeader>
</fe:Facturae>"""
        assert en16931.validar(xml).incidencias == []

    def test_edifact_si_sigue_sin_soporte(self):
        """Lo que de verdad no se valida se sigue diciendo, y con estas letras."""
        datos = b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+INVOIC:D:96A:UN'"
        aviso = [i for i in en16931.validar(datos).avisos if i.codigo == "SIN-SOPORTE"]
        assert aviso and "UBL y para CII" in aviso[0].mensaje

    def test_documento_irreconocible(self):
        informe = en16931.validar(b"<pedido/>")
        assert not informe.deteccion
        assert "No se ha podido validar" in informe.resumen()

    def test_sin_declarar_en16931_avisa(self):
        informe = en16931.validar(factura(perfil="urn:otra:cosa"))
        avisos = [i for i in informe.avisos if i.codigo == "BR-01"]
        assert avisos
        assert "urn:otra:cosa" in avisos[0].encontrado
