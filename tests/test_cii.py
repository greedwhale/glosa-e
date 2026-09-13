"""Las reglas EN 16931 sobre la sintaxis CII.

La gracia de este fichero está en `TestLasMismasReglas`: cada comprobación se
ejecuta sobre UBL y sobre CII con el mismo documento semántico. Si una regla
dejara de funcionar en una de las dos sintaxis, la mitad de los tests caería.
"""

import pathlib

import pytest
from lxml import etree

from validador import en16931, sintaxis
from validador.en16931 import AVISO, ERROR
from validador.formato import CII, EDIFACT, FACTURAE, UBL

# Los ejemplos EDIFACT de la Comisión, si están. No se versionan —son de
# terceros—, así que las pruebas que los usan se saltan cuando no están.
MUESTRAS_EDIFACT = sorted(
    pathlib.Path("muestras").glob("cef_EDIFACT_EXAMPLE*.xml")
)

# --- Construcción de facturas equivalentes en las dos sintaxis -------------

PLANTILLA_CII = """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>{perfil}</rsm:ExchangedDocumentContext>
  <rsm:ExchangedDocument>
    {numero}
    {tipo}
    {fecha}
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    {lineas}
    <ram:ApplicableHeaderTradeAgreement>
      {vendedor}
      {comprador}
    </ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeDelivery/>
    <ram:ApplicableHeaderTradeSettlement>
      {moneda}
      {impuestos}
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        {suma_lineas}
        {base}
        {impuesto_total}
        {con_impuestos}
        {anticipos}
        {a_pagar}
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""

PLANTILLA_UBL = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  {perfil}
  {numero}
  {fecha}
  {tipo}
  {moneda}
  {vendedor}
  {comprador}
  {impuestos}
  <cac:LegalMonetaryTotal>
    {suma_lineas}
    {base}
    {con_impuestos}
    {anticipos}
    {a_pagar}
  </cac:LegalMonetaryTotal>
  {lineas}
</Invoice>"""


def cii(lineas=(("1", "100.00"),), suma_lineas="100.00", base="100.00",
        impuestos="21.00", con_impuestos="121.00", a_pagar="121.00",
        anticipos=None, perfil="urn:cen.eu:en16931:2017", moneda="EUR",
        categoria="S", tipo_iva="21", base_iva=None, motivo=None,
        omitir=()):
    """Una factura CII. `omitir` quita campos para provocar cada BR."""

    def si(clave, texto):
        return "" if clave in omitir else texto

    iva_de_linea = (
        ""
        if categoria is None or "categoria_linea" in omitir
        else f"""<ram:ApplicableTradeTax>
          <ram:TypeCode>VAT</ram:TypeCode>
          <ram:CategoryCode>{categoria}</ram:CategoryCode>
          {'' if tipo_iva is None else
           f'<ram:RateApplicablePercent>{tipo_iva}</ram:RateApplicablePercent>'}
        </ram:ApplicableTradeTax>"""
    )

    # BT-146, BT-129 y BT-130: el precio unitario cuelga del acuerdo de línea y
    # la cantidad de la entrega, que en CII son dos bloques distintos. La
    # unidad va en un atributo, no en un elemento.
    precio_xml = (
        ""
        if "precio_linea" in omitir
        else """<ram:SpecifiedLineTradeAgreement>
        <ram:NetPriceProductTradePrice><ram:ChargeAmount>100.00</ram:ChargeAmount>
        </ram:NetPriceProductTradePrice>
      </ram:SpecifiedLineTradeAgreement>"""
    )

    def entrega_xml():
        if "cantidad_linea" in omitir:
            return ""
        unidad = "" if "unidad_linea" in omitir else ' unitCode="H87"'
        return (
            "<ram:SpecifiedLineTradeDelivery>"
            f"<ram:BilledQuantity{unidad}>1</ram:BilledQuantity>"
            "</ram:SpecifiedLineTradeDelivery>"
        )

    linea_xml = "".join(
        f"""<ram:IncludedSupplyChainTradeLineItem>
      <ram:AssociatedDocumentLineDocument><ram:LineID>{ident}</ram:LineID>
      </ram:AssociatedDocumentLineDocument>
      {'' if 'nombre_linea' in omitir else
       '<ram:SpecifiedTradeProduct><ram:Name>Concepto</ram:Name>'
       '</ram:SpecifiedTradeProduct>'}
      {precio_xml}
      {entrega_xml()}
      <ram:SpecifiedLineTradeSettlement>
        {iva_de_linea}
        <ram:SpecifiedTradeSettlementLineMonetarySummation>
          {'' if 'importe_linea' in omitir else
           f'<ram:LineTotalAmount>{importe}</ram:LineTotalAmount>'}
        </ram:SpecifiedTradeSettlementLineMonetarySummation>
      </ram:SpecifiedLineTradeSettlement>
    </ram:IncludedSupplyChainTradeLineItem>"""
        for ident, importe in lineas
    )

    def parte(etiqueta, nombre, clave):
        if clave in omitir:
            return ""
        direccion = (
            ""
            if f"direccion_{clave}" in omitir
            else "<ram:PostalTradeAddress>"
            + ("" if f"pais_{clave}" in omitir
               else "<ram:CountryID>ES</ram:CountryID>")
            + "</ram:PostalTradeAddress>"
        )
        return f"<ram:{etiqueta}><ram:Name>{nombre}</ram:Name>{direccion}</ram:{etiqueta}>"

    return PLANTILLA_CII.format(
        perfil=si(
            "perfil",
            "<ram:GuidelineSpecifiedDocumentContextParameter>"
            f"<ram:ID>{perfil}</ram:ID>"
            "</ram:GuidelineSpecifiedDocumentContextParameter>",
        ),
        numero=si("numero", "<ram:ID>F-2026-0001</ram:ID>"),
        tipo=si("tipo", "<ram:TypeCode>380</ram:TypeCode>"),
        fecha=si(
            "fecha",
            '<ram:IssueDateTime><udt:DateTimeString format="102">20260302'
            "</udt:DateTimeString></ram:IssueDateTime>",
        ),
        lineas="" if "lineas" in omitir else linea_xml,
        vendedor=parte("SellerTradeParty", "Talleres Ejemplo SL", "vendedor"),
        comprador=parte("BuyerTradeParty", "Cliente SA", "comprador"),
        moneda=si("moneda", f"<ram:InvoiceCurrencyCode>{moneda}</ram:InvoiceCurrencyCode>"),
        impuestos=""
        if impuestos is None
        else f"""<ram:ApplicableTradeTax>
        <ram:CalculatedAmount>{impuestos}</ram:CalculatedAmount>
        <ram:TypeCode>VAT</ram:TypeCode>
        {'' if motivo is None else f'<ram:ExemptionReason>{motivo}</ram:ExemptionReason>'}
        <ram:BasisAmount>{base if base_iva is None else base_iva}</ram:BasisAmount>
        {'' if categoria is None else f'<ram:CategoryCode>{categoria}</ram:CategoryCode>'}
        {'' if tipo_iva is None else
         f'<ram:RateApplicablePercent>{tipo_iva}</ram:RateApplicablePercent>'}
      </ram:ApplicableTradeTax>""",
        impuesto_total=""
        if impuestos is None
        else f'<ram:TaxTotalAmount currencyID="{moneda}">{impuestos}</ram:TaxTotalAmount>',
        suma_lineas=si("suma_lineas", f"<ram:LineTotalAmount>{suma_lineas}</ram:LineTotalAmount>"),
        base=si("base", f"<ram:TaxBasisTotalAmount>{base}</ram:TaxBasisTotalAmount>"),
        con_impuestos=si(
            "con_impuestos", f"<ram:GrandTotalAmount>{con_impuestos}</ram:GrandTotalAmount>"
        ),
        anticipos=""
        if anticipos is None
        else f"<ram:TotalPrepaidAmount>{anticipos}</ram:TotalPrepaidAmount>",
        a_pagar=si("a_pagar", f"<ram:DuePayableAmount>{a_pagar}</ram:DuePayableAmount>"),
    )


def ubl(lineas=(("1", "100.00"),), suma_lineas="100.00", base="100.00",
        impuestos="21.00", con_impuestos="121.00", a_pagar="121.00",
        anticipos=None, perfil="urn:cen.eu:en16931:2017", moneda="EUR",
        categoria="S", tipo_iva="21", base_iva=None, motivo=None,
        omitir=()):
    """La misma factura, en UBL. Mismos nombres de campo para `omitir`."""

    def si(clave, texto):
        return "" if clave in omitir else texto

    iva_de_linea = (
        ""
        if categoria is None or "categoria_linea" in omitir
        else f"""<cac:Item><cbc:Name>Concepto</cbc:Name><cac:ClassifiedTaxCategory>
          <cbc:ID>{categoria}</cbc:ID>
          {'' if tipo_iva is None else f'<cbc:Percent>{tipo_iva}</cbc:Percent>'}
        </cac:ClassifiedTaxCategory></cac:Item>"""
    )

    # Los mismos BT-129, BT-130 y BT-146 que en el constructor de CII, para que
    # las dos sintaxis se comparen sobre facturas igual de completas. Es el
    # sentido de esta clase: si una lleva precio unitario y la otra no, lo que
    # se compara ya no son las reglas sino los ficheros.
    cantidad_xml = (
        ""
        if "cantidad_linea" in omitir
        else '<cbc:InvoicedQuantity unitCode="EA">1</cbc:InvoicedQuantity>'
    )
    precio_xml = (
        ""
        if "precio_linea" in omitir
        else f'<cac:Price><cbc:PriceAmount currencyID="{moneda}">100.00'
        "</cbc:PriceAmount></cac:Price>"
    )

    linea_xml = "".join(
        f"""<cac:InvoiceLine><cbc:ID>{ident}</cbc:ID>
        {cantidad_xml}
        {'' if 'importe_linea' in omitir else
         f'<cbc:LineExtensionAmount currencyID="{moneda}">{importe}</cbc:LineExtensionAmount>'}
        {iva_de_linea}
        {precio_xml}
        </cac:InvoiceLine>"""
        for ident, importe in lineas
    )

    def parte(etiqueta, nombre, clave):
        if clave in omitir:
            return ""
        direccion = (
            ""
            if f"direccion_{clave}" in omitir
            else "<cac:PostalAddress>"
            + ("" if f"pais_{clave}" in omitir
               else "<cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode>"
                    "</cac:Country>")
            + "</cac:PostalAddress>"
        )
        return (
            f"<cac:{etiqueta}><cac:Party>{direccion}"
            f"<cac:PartyLegalEntity><cbc:RegistrationName>{nombre}"
            f"</cbc:RegistrationName></cac:PartyLegalEntity>"
            f"</cac:Party></cac:{etiqueta}>"
        )

    def total(clave, etiqueta, valor):
        if clave in omitir or valor is None:
            return ""
        return f'<cbc:{etiqueta} currencyID="{moneda}">{valor}</cbc:{etiqueta}>'

    return PLANTILLA_UBL.format(
        perfil=si("perfil", f"<cbc:CustomizationID>{perfil}</cbc:CustomizationID>"),
        numero=si("numero", "<cbc:ID>F-2026-0001</cbc:ID>"),
        fecha=si("fecha", "<cbc:IssueDate>2026-03-02</cbc:IssueDate>"),
        tipo=si("tipo", "<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"),
        moneda=si("moneda", f"<cbc:DocumentCurrencyCode>{moneda}</cbc:DocumentCurrencyCode>"),
        lineas="" if "lineas" in omitir else linea_xml,
        vendedor=parte("AccountingSupplierParty", "Talleres Ejemplo SL", "vendedor"),
        comprador=parte("AccountingCustomerParty", "Cliente SA", "comprador"),
        impuestos=""
        if impuestos is None
        else f"""<cac:TaxTotal>
        <cbc:TaxAmount currencyID="{moneda}">{impuestos}</cbc:TaxAmount>
        <cac:TaxSubtotal>
          <cbc:TaxableAmount currencyID="{moneda}">{base if base_iva is None else base_iva}</cbc:TaxableAmount>
          <cbc:TaxAmount currencyID="{moneda}">{impuestos}</cbc:TaxAmount>
          <cac:TaxCategory>
            {'' if categoria is None else f'<cbc:ID>{categoria}</cbc:ID>'}
            {'' if tipo_iva is None else f'<cbc:Percent>{tipo_iva}</cbc:Percent>'}
            {'' if motivo is None else
             f'<cbc:TaxExemptionReason>{motivo}</cbc:TaxExemptionReason>'}
          </cac:TaxCategory>
        </cac:TaxSubtotal>
      </cac:TaxTotal>""",
        suma_lineas=total("suma_lineas", "LineExtensionAmount", suma_lineas),
        base=total("base", "TaxExclusiveAmount", base),
        con_impuestos=total("con_impuestos", "TaxInclusiveAmount", con_impuestos),
        anticipos=total("anticipos", "PrepaidAmount", anticipos),
        a_pagar=total("a_pagar", "PayableAmount", a_pagar),
    )


SINTAXIS = {"UBL": ubl, "CII": cii}


@pytest.fixture(params=sorted(SINTAXIS))
def montar(request):
    """Devuelve el constructor de una de las dos sintaxis."""
    return SINTAXIS[request.param]


def codigos(informe, gravedad=None):
    return {
        i.codigo
        for i in informe.incidencias
        if gravedad is None or i.gravedad == gravedad
    }


# --- Las mismas reglas en las dos sintaxis ---------------------------------


class TestLasMismasReglas:
    """Cada test se ejecuta dos veces: una en UBL y otra en CII."""

    def test_factura_correcta(self, montar):
        informe = en16931.validar(montar())
        assert informe.conforme, informe.detalle()
        assert not informe.avisos, informe.detalle()

    @pytest.mark.parametrize(
        "campo,codigo",
        [
            ("numero", "BR-02"),
            ("fecha", "BR-03"),
            ("tipo", "BR-04"),
            ("moneda", "BR-05"),
            ("vendedor", "BR-06"),
            ("comprador", "BR-07"),
            ("direccion_vendedor", "BR-08"),
            ("pais_vendedor", "BR-09"),
            ("direccion_comprador", "BR-10"),
            ("pais_comprador", "BR-11"),
            ("suma_lineas", "BR-12"),
            ("base", "BR-13"),
            ("con_impuestos", "BR-14"),
            ("a_pagar", "BR-15"),
            ("lineas", "BR-16"),
            ("importe_linea", "BR-24"),
        ],
    )
    def test_campo_obligatorio_que_falta(self, montar, campo, codigo):
        informe = en16931.validar(montar(omitir=(campo,)))
        assert codigo in codigos(informe, ERROR), informe.detalle()

    def test_una_direccion_no_esta_vacia_por_no_tener_texto(self, montar):
        """La dirección es un contenedor: su texto propio siempre es None.

        Se comprobaba mirando si la ruta acababa en «PostalAddress», que en
        UBL colaba y en CII —«PostalTradeAddress»— habría dado BR-08 y BR-10
        en todas las facturas correctas.
        """
        informe = en16931.validar(montar(omitir=("pais_vendedor",)))
        assert "BR-09" in codigos(informe, ERROR)
        assert "BR-08" not in codigos(informe)  # la dirección sigue estando

    def test_suma_de_lineas_no_cuadra(self, montar):
        informe = en16931.validar(
            montar(lineas=(("1", "60.00"), ("2", "30.00")), suma_lineas="100.00")
        )
        problema = next(i for i in informe.errores if i.codigo == "BR-CO-10")
        assert "90.00" in problema.esperado
        assert "2 líneas" in problema.esperado
        assert problema.encontrado == "100.00"

    def test_base_imponible_no_cuadra(self, montar):
        informe = en16931.validar(montar(base="90.00"))
        assert "BR-CO-13" in codigos(informe, ERROR)

    def test_total_con_impuestos_no_cuadra(self, montar):
        informe = en16931.validar(montar(con_impuestos="130.00", a_pagar="130.00"))
        assert "BR-CO-15" in codigos(informe, ERROR)

    def test_a_pagar_no_cuadra(self, montar):
        informe = en16931.validar(montar(a_pagar="200.00"))
        assert "BR-CO-16" in codigos(informe, ERROR)

    def test_anticipo_bien_descontado(self, montar):
        informe = en16931.validar(montar(anticipos="21.00", a_pagar="100.00"))
        assert informe.conforme, informe.detalle()

    def test_sin_impuestos_avisa_pero_no_falla(self, montar):
        """El aviso se llama IVA-SIN-TOTAL, no BR-CO-14.

        Llevaba el código BR-CO-14, que es de la norma y significa otra cosa:
        que el total de IVA sea la suma de las cuotas del desglose. Ahora esa
        regla está implementada de verdad en `iva.py` y este aviso —que es de
        la casa— usa un código de la casa.
        """
        informe = en16931.validar(montar(impuestos=None, con_impuestos="100.00",
                                         a_pagar="100.00"))
        assert "IVA-SIN-TOTAL" in codigos(informe, AVISO)
        assert "BR-CO-15" not in codigos(informe, ERROR)

    def test_un_centimo_ya_es_error(self, montar):
        """Se llamó «un céntimo se tolera» hasta el 13-09-2026.

        Esta misma factura —tres líneas de 33,33 y una suma declarada de
        100,00— pasaba limpia. La norma redondea la suma a dos decimales y la
        compara sin margen: 99,99 no es 100,00. Lo dicen el esquematrón de UBL
        y el de CII, y lo prueba la prueba oficial de BR-CO-10.
        """
        informe = en16931.validar(
            montar(lineas=(("1", "33.33"), ("2", "33.33"), ("3", "33.33")))
        )
        assert "BR-CO-10" in codigos(informe, ERROR), informe.detalle()

    def test_dos_centimos_ya_es_error(self, montar):
        informe = en16931.validar(
            montar(lineas=(("1", "33.33"), ("2", "33.33"), ("3", "33.32")))
        )
        assert "BR-CO-10" in codigos(informe, ERROR)

    def test_sin_declarar_en16931_avisa(self, montar):
        """Con código de la casa: BR-01 solo pide que el campo esté."""
        informe = en16931.validar(montar(perfil="urn:otra:cosa"))
        aviso = next(i for i in informe.avisos if i.codigo == "PERFIL-SIN-EN16931")
        assert "urn:otra:cosa" in aviso.encontrado
        assert "BR-01" not in codigos(informe)

    def test_la_linea_sin_importe_se_nombra_por_su_id(self, montar):
        informe = en16931.validar(montar(omitir=("importe_linea",)))
        problema = next(i for i in informe.errores if i.codigo == "BR-24")
        assert "1" in problema.campo


# --- Lo propio de CII ------------------------------------------------------


class TestPropioDeCII:
    def test_se_reconoce_como_cii(self):
        informe = en16931.validar(cii())
        assert informe.deteccion.familia == CII
        assert "SIN-SOPORTE" not in codigos(informe)

    def test_el_aviso_nombra_el_campo_de_cada_sintaxis(self):
        """«CustomizationID» no existe en CII: decirlo confundiría a quien lea."""
        en_cii = next(
            i for i in en16931.validar(cii(perfil="x")).avisos
            if i.codigo == "PERFIL-SIN-EN16931"
        )
        en_ubl = next(
            i for i in en16931.validar(ubl(perfil="x")).avisos
            if i.codigo == "PERFIL-SIN-EN16931"
        )
        assert "GuidelineSpecifiedDocumentContextParameter" in en_cii.mensaje
        assert "CustomizationID" in en_ubl.mensaje

    def test_facturae_no_es_asunto_de_este_modulo(self):
        """Antes recibia un SIN-SOPORTE; ahora no recibe nada, y es mejor.

        Facturae no es un perfil de EN 16931 y no tiene por que serlo: es el
        formato nacional, con su propio esquema y su propia aritmetica. De el
        se encarga `facturae.py`. El aviso de antes decia «solo se ha
        identificado, no validado» mientras el resumen decia «sin errores», y
        las dos cosas eran verdad a medias.
        """
        facturae = """<?xml version="1.0"?>
<fe:Facturae xmlns:fe="http://www.facturae.es/Facturae/2009/v3.2/Facturae">
  <FileHeader><SchemaVersion>3.2</SchemaVersion></FileHeader>
</fe:Facturae>"""
        assert en16931.validar(facturae).incidencias == []

    def test_edifact_ya_no_se_queda_sin_validar(self):
        """Antes contestaba «solo se ha identificado». Ahora se valida.

        La factura del ejemplo es una cabecera pelada: no trae ni partes ni
        importes. Lo que se comprueba aquí es que las reglas **corren** sobre
        ella —y por eso echan de menos lo que falta— en vez de rendirse.
        """
        datos = b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+INVOIC:D:96A:UN'"
        informe = en16931.validar(datos)
        assert "SIN-SOPORTE" not in codigos(informe, AVISO)
        assert "BR-02" in codigos(informe, ERROR)


class TestImpuestoEnVariasMonedas:
    """BT-110 y BT-111: el total de impuestos puede venir dos veces.

    Las dos sintaxis permiten declararlo en la moneda de la factura y en la de
    contabilidad. Coger el primero que aparezca es coger uno al azar, y si el
    documento los trae en el otro orden el cuadre falla por una factura buena.
    """

    def _cii_con_dos_monedas(self, primero, segundo):
        base = cii()
        return base.replace(
            '<ram:TaxTotalAmount currencyID="EUR">21.00</ram:TaxTotalAmount>',
            f"<ram:TaxTotalAmount {primero}</ram:TaxTotalAmount>"
            f"<ram:TaxTotalAmount {segundo}</ram:TaxTotalAmount>",
        )

    def test_coge_la_moneda_de_la_factura_aunque_vaya_segunda(self):
        xml = self._cii_con_dos_monedas(
            'currencyID="USD">23.10', 'currencyID="EUR">21.00'
        )
        informe = en16931.validar(xml)
        assert informe.conforme, informe.detalle()

    def test_y_tambien_si_va_primera(self):
        xml = self._cii_con_dos_monedas(
            'currencyID="EUR">21.00', 'currencyID="USD">23.10'
        )
        assert en16931.validar(xml).conforme

    def test_sin_currency_id_se_coge_el_primero(self):
        """Sin atributo no hay forma de elegir; al menos que no reviente."""
        xml = cii().replace(
            '<ram:TaxTotalAmount currencyID="EUR">21.00</ram:TaxTotalAmount>',
            "<ram:TaxTotalAmount>21.00</ram:TaxTotalAmount>",
        )
        assert en16931.validar(xml).conforme

    def test_lo_mismo_en_ubl(self):
        xml = ubl().replace(
            '<cac:TaxTotal><cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount></cac:TaxTotal>',
            '<cac:TaxTotal><cbc:TaxAmount currencyID="USD">23.10</cbc:TaxAmount></cac:TaxTotal>'
            '<cac:TaxTotal><cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount></cac:TaxTotal>',
        )
        informe = en16931.validar(xml)
        assert informe.conforme, informe.detalle()


class TestElMapaEsSoloUnMapa:
    """La `Sintaxis` no debería tener lógica: solo rutas."""

    def test_las_dos_sintaxis_declaran_los_mismos_campos(self):
        campos_ubl = set(vars(en16931.SINTAXIS_UBL))
        campos_cii = set(vars(en16931.SINTAXIS_CII))
        assert campos_ubl == campos_cii

    def test_ninguna_ruta_se_ha_quedado_a_medias(self):
        for mapa in en16931.SINTAXIS.values():
            for nombre, valor in vars(mapa).items():
                if nombre in (
                    "nombre",
                    "espacios",
                    "nombre_perfil",
                    "marcas_de_cargo",
                    # No es una ruta y no debe parecerlo: dice qué vocabulario
                    # usa esta sintaxis para la categoría de IVA. Vacío
                    # significa «ya viene en UNCL5305»; «facturae» significa
                    # que hay que deducirla, y de eso se encarga `iva.py`.
                    # Se excluye aquí a mano, y no con una regla del tipo «los
                    # que no empiecen por ./ se saltan», porque esa regla
                    # dejaría pasar en silencio la próxima ruta mal escrita,
                    # que es justo lo que esta prueba existe para cazar.
                    "categoria_derivada",
                    # Igual que el de arriba: dice qué vocabulario usa
                    # esta sintaxis para BT-3, no dónde está escrito.
                    "tipo_derivado",
                    # Un sí o un no: qué esquematrón oficial se sigue en el
                    # borde de BR-CO-17. Tampoco es una ruta.
                    "cuota_admite_la_unidad_justa",
                ):
                    continue
                # «self::» es tan relativa como «./», y hace falta en EDIFACT
                # para filtrar por el propio nodo antes de subir a buscar.
                #
                # «../» también lo es, y hace falta en Facturae: ahí las rutas
                # se evalúan sobre cada `<Invoice>` porque un fichero es un
                # lote, y el vendedor y el comprador están fuera de la factura,
                # colgando de la raíz y compartidos por todas.
                #
                # «name(» no es una ruta sino una función, y es la única forma
                # de leer un dato que Facturae escribe en el nombre del
                # elemento y no en su contenido: un ajuste general es un
                # descuento o un cargo según se llame `Discount` o `Charge`.
                assert valor.startswith(("./", "../", "self::", "name(")), (
                    f"{mapa.nombre}.{nombre} = {valor}"
                )
                # Los ejes de XPath llevan dos puntos dobles («self::») y no
                # son prefijos de espacio de nombres. Sin quitarlos primero,
                # un eje sale acusado de usar un espacio sin declarar.
                sin_ejes = valor.replace("::", " ")
                prefijos = {
                    trozo.split(":", 1)[0]
                    for trozo in sin_ejes.removeprefix("./").split("/")
                    if ":" in trozo
                }
                sobran = prefijos - set(mapa.espacios)
                assert not sobran, f"{mapa.nombre}.{nombre} usa {sobran}"

    def test_las_familias_registradas_son_las_que_se_validan(self):
        # Facturae entró el 06-09-2026, cuando el artículo 7.1 del RD 238/2026
        # pasó a exigirle el modelo semántico EN 16931 como a las otras tres.
        # Su mapa no lo publica CEN —no hay `CEN/TS 16931-3-x` para Facturae—,
        # así que está escrito aquí con cada hueco declarado.
        assert set(en16931.SINTAXIS) == {UBL, CII, EDIFACT, FACTURAE}

    def test_lo_que_no_se_sabe_leer_no_lee_nada(self):
        """`SIN_MAPA` tiene que ser de verdad una ruta que no encuentra nada.

        Es el hueco declarado de un campo que no se ha podido situar. Si
        alguna vez casara con algo, se estaría metiendo un dato ajeno en las
        cuentas por la puerta de atrás, que es justo lo que el hueco evita.
        """
        if not MUESTRAS_EDIFACT:
            pytest.skip("no están las muestras de la Comisión")
        for muestra in MUESTRAS_EDIFACT:
            raiz = etree.fromstring(muestra.read_bytes())
            assert raiz.xpath(sintaxis.SIN_MAPA) == []
