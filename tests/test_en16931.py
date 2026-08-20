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
    omitir=(),
):
    """Construye una factura UBL. `omitir` quita campos para probar las BR."""

    def campo(etiqueta, valor, ns="cbc"):
        if etiqueta in omitir or valor is None:
            return ""
        return f"<{ns}:{etiqueta}>{valor}</{ns}:{etiqueta}>"

    xml_lineas = "".join(
        f"""<cac:InvoiceLine><cbc:ID>{ident}</cbc:ID>
        {'' if 'LineExtensionAmount' in omitir else
         f'<cbc:LineExtensionAmount currencyID="EUR">{importe}</cbc:LineExtensionAmount>'}
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
    xml_impuestos = (
        ""
        if impuestos is None
        else f'<cac:TaxTotal><cbc:TaxAmount currencyID="EUR">{impuestos}</cbc:TaxAmount></cac:TaxTotal>'
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


def codigos(informe, gravedad=None):
    return {
        i.codigo
        for i in informe.incidencias
        if gravedad is None or i.gravedad == gravedad
    }


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
        informe = en16931.validar(factura(impuestos=None, con_impuestos="100.00"))
        assert "BR-CO-14" in codigos(informe, AVISO)
        assert "BR-CO-15" not in codigos(informe, ERROR)


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
    def test_facturae_se_identifica_pero_no_se_valida(self):
        xml = """<?xml version="1.0"?>
<fe:Facturae xmlns:fe="http://www.facturae.es/Facturae/2009/v3.2/Facturae">
  <FileHeader><SchemaVersion>3.2</SchemaVersion></FileHeader>
</fe:Facturae>"""
        informe = en16931.validar(xml)
        assert "SIN-SOPORTE" in codigos(informe, AVISO)
        assert informe.conforme  # no hay errores, simplemente no se ha validado

    def test_documento_irreconocible(self):
        informe = en16931.validar(b"<pedido/>")
        assert not informe.deteccion
        assert "No se ha podido validar" in informe.resumen()

    def test_sin_declarar_en16931_avisa(self):
        informe = en16931.validar(factura(perfil="urn:otra:cosa"))
        avisos = [i for i in informe.avisos if i.codigo == "BR-01"]
        assert avisos
        assert "urn:otra:cosa" in avisos[0].encontrado
