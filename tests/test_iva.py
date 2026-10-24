"""Comprobaciones de las reglas de IVA.

Como en `test_cii`, cada comprobación se ejecuta sobre UBL y sobre CII con el
mismo documento semántico montado de las dos formas. Aquí las facturas se
construyen a medida —varios tipos, varias categorías, descuentos con su propio
tipo— porque el desglose es justo lo que hay que poder retorcer.

Casi todo llama a `iva.reglas` directamente en vez de a `en16931.validar`: así
no hace falta mantener cuadrados los totales generales, que no son lo que se
está probando, y las incidencias que salen son solo las de IVA.
"""

from dataclasses import dataclass
from decimal import Decimal

import pytest
from lxml import etree

from validador import en16931, iva
from validador.formato import parser
from validador.glosario import CODIGOS
from validador.incidencias import AVISO, ERROR, NOTA
from validador.sintaxis import SINTAXIS_CII, SINTAXIS_UBL

MONEDA = "EUR"


@dataclass
class Linea:
    ident: str
    importe: str
    categoria: str | None = "S"
    tipo: str | None = "21"


@dataclass
class Grupo:
    # base y cuota admiten None porque una entrada del desglose incompleta es
    # justo lo que comprueban BR-45 y BR-46.
    base: str | None
    cuota: str | None
    categoria: str | None = "S"
    tipo: str | None = "21"
    motivo: str | None = None


@dataclass
class Ajuste:
    """Un descuento o un cargo a nivel de documento."""

    importe: str
    es_cargo: bool = False
    categoria: str | None = "S"
    tipo: str | None = "21"


# Los identificadores fiscales que traen las facturas de estas pruebas si no se
# dice otra cosa: el de IVA del vendedor y el del comprador, que es lo que pide
# la categoría más exigente de las que usan casi todas —la inversión del sujeto
# pasivo y la intracomunitaria piden los dos—. Las pruebas de BR-{X}-02 a 04 los
# quitan o los cambian con `partes`.
PARTES = {"vendedor_nif": "ESB12345678", "comprador_nif": "ESA87654321"}


# --- Las dos sintaxis ------------------------------------------------------


def _partes_ubl(partes):
    def esquema(numero, esquema):
        return (f"<cac:PartyTaxScheme><cbc:CompanyID>{numero}</cbc:CompanyID>"
                f"<cac:TaxScheme><cbc:ID>{esquema}</cbc:ID></cac:TaxScheme>"
                "</cac:PartyTaxScheme>")
    vendedor = "".join((
        esquema(partes["vendedor_nif"], "VAT") if "vendedor_nif" in partes else "",
        esquema(partes["vendedor_registro_fiscal"], "TAX")
        if "vendedor_registro_fiscal" in partes else "",
    ))
    comprador = "".join((
        esquema(partes["comprador_nif"], "VAT") if "comprador_nif" in partes else "",
        f"<cac:PartyLegalEntity><cbc:CompanyID>{partes['comprador_registro']}"
        "</cbc:CompanyID></cac:PartyLegalEntity>"
        if "comprador_registro" in partes else "",
    ))
    representante = (
        f"<cac:TaxRepresentativeParty>{esquema(partes['representante_nif'], 'VAT')}"
        "</cac:TaxRepresentativeParty>" if "representante_nif" in partes else ""
    )
    return (f"<cac:AccountingSupplierParty><cac:Party>{vendedor}</cac:Party>"
            "</cac:AccountingSupplierParty>"
            f"<cac:AccountingCustomerParty><cac:Party>{comprador}</cac:Party>"
            f"</cac:AccountingCustomerParty>{representante}")


def _partes_cii(partes):
    def registro(numero, esquema):
        return (f"<ram:SpecifiedTaxRegistration><ram:ID schemeID=\"{esquema}\">"
                f"{numero}</ram:ID></ram:SpecifiedTaxRegistration>")
    vendedor = "".join((
        registro(partes["vendedor_nif"], "VA") if "vendedor_nif" in partes else "",
        registro(partes["vendedor_registro_fiscal"], "FC")
        if "vendedor_registro_fiscal" in partes else "",
    ))
    comprador = "".join((
        f"<ram:SpecifiedLegalOrganization><ram:ID>{partes['comprador_registro']}"
        "</ram:ID></ram:SpecifiedLegalOrganization>"
        if "comprador_registro" in partes else "",
        registro(partes["comprador_nif"], "VA") if "comprador_nif" in partes else "",
    ))
    representante = (
        f"<ram:SellerTaxRepresentativeTradeParty>"
        f"{registro(partes['representante_nif'], 'VA')}"
        "</ram:SellerTaxRepresentativeTradeParty>"
        if "representante_nif" in partes else ""
    )
    return (f"<ram:SellerTradeParty>{vendedor}</ram:SellerTradeParty>"
            f"<ram:BuyerTradeParty>{comprador}</ram:BuyerTradeParty>"
            f"{representante}")


def ubl(lineas=(), grupos=(), ajustes=(), total_iva="21.00",
        descuentos_total=None, cargos_total=None, partes=PARTES,
        fecha_entrega=None, periodo=None, pais_entrega=None):
    xml_lineas = "".join(
        f"""<cac:InvoiceLine>
    <cbc:ID>{l.ident}</cbc:ID>
    <cbc:LineExtensionAmount currencyID="{MONEDA}">{l.importe}</cbc:LineExtensionAmount>
    {'' if l.categoria is None else f'''<cac:Item><cac:ClassifiedTaxCategory>
      <cbc:ID>{l.categoria}</cbc:ID>
      {'' if l.tipo is None else f'<cbc:Percent>{l.tipo}</cbc:Percent>'}
    </cac:ClassifiedTaxCategory></cac:Item>'''}
  </cac:InvoiceLine>"""
        for l in lineas
    )
    xml_grupos = "".join(
        f"""<cac:TaxSubtotal>
      {'' if g.base is None else
       f'<cbc:TaxableAmount currencyID="{MONEDA}">{g.base}</cbc:TaxableAmount>'}
      {'' if g.cuota is None else
       f'<cbc:TaxAmount currencyID="{MONEDA}">{g.cuota}</cbc:TaxAmount>'}
      <cac:TaxCategory>
        {'' if g.categoria is None else f'<cbc:ID>{g.categoria}</cbc:ID>'}
        {'' if g.tipo is None else f'<cbc:Percent>{g.tipo}</cbc:Percent>'}
        {'' if g.motivo is None else
         f'<cbc:TaxExemptionReason>{g.motivo}</cbc:TaxExemptionReason>'}
      </cac:TaxCategory>
    </cac:TaxSubtotal>"""
        for g in grupos
    )
    xml_ajustes = "".join(
        f"""<cac:AllowanceCharge>
    <cbc:ChargeIndicator>{'true' if a.es_cargo else 'false'}</cbc:ChargeIndicator>
    <cbc:Amount currencyID="{MONEDA}">{a.importe}</cbc:Amount>
    {'' if a.categoria is None else f'''<cac:TaxCategory>
      <cbc:ID>{a.categoria}</cbc:ID>
      {'' if a.tipo is None else f'<cbc:Percent>{a.tipo}</cbc:Percent>'}
    </cac:TaxCategory>'''}
  </cac:AllowanceCharge>"""
        for a in ajustes
    )
    totales = "".join(
        f'<cbc:{etiqueta} currencyID="{MONEDA}">{valor}</cbc:{etiqueta}>'
        for etiqueta, valor in (
            ("AllowanceTotalAmount", descuentos_total),
            ("ChargeTotalAmount", cargos_total),
        )
        if valor is not None
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:ID>F-2026-0001</cbc:ID>
  <cbc:DocumentCurrencyCode>{MONEDA}</cbc:DocumentCurrencyCode>
  {_partes_ubl(partes)}
  {'' if periodo is None else
   f'<cac:InvoicePeriod><cbc:StartDate>{periodo}</cbc:StartDate></cac:InvoicePeriod>'}
  {'' if fecha_entrega is None and pais_entrega is None else
   '<cac:Delivery>'
   + ('' if fecha_entrega is None else
      f'<cbc:ActualDeliveryDate>{fecha_entrega}</cbc:ActualDeliveryDate>')
   + ('' if pais_entrega is None else
      '<cac:DeliveryLocation><cac:Address><cac:Country>'
      f'<cbc:IdentificationCode>{pais_entrega}</cbc:IdentificationCode>'
      '</cac:Country></cac:Address></cac:DeliveryLocation>')
   + '</cac:Delivery>'}
  {xml_ajustes}
  <cac:TaxTotal>
    {'' if total_iva is None else
     f'<cbc:TaxAmount currencyID="{MONEDA}">{total_iva}</cbc:TaxAmount>'}
    {xml_grupos}
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>{totales}</cac:LegalMonetaryTotal>
  {xml_lineas}
</Invoice>"""


def cii(lineas=(), grupos=(), ajustes=(), total_iva="21.00",
        descuentos_total=None, cargos_total=None, partes=PARTES,
        fecha_entrega=None, periodo=None, pais_entrega=None):
    xml_lineas = "".join(
        f"""<ram:IncludedSupplyChainTradeLineItem>
    <ram:AssociatedDocumentLineDocument><ram:LineID>{l.ident}</ram:LineID>
    </ram:AssociatedDocumentLineDocument>
    <ram:SpecifiedLineTradeSettlement>
      {'' if l.categoria is None else f'''<ram:ApplicableTradeTax>
        <ram:TypeCode>VAT</ram:TypeCode>
        <ram:CategoryCode>{l.categoria}</ram:CategoryCode>
        {'' if l.tipo is None else
         f'<ram:RateApplicablePercent>{l.tipo}</ram:RateApplicablePercent>'}
      </ram:ApplicableTradeTax>'''}
      <ram:SpecifiedTradeSettlementLineMonetarySummation>
        <ram:LineTotalAmount>{l.importe}</ram:LineTotalAmount>
      </ram:SpecifiedTradeSettlementLineMonetarySummation>
    </ram:SpecifiedLineTradeSettlement>
  </ram:IncludedSupplyChainTradeLineItem>"""
        for l in lineas
    )
    xml_grupos = "".join(
        f"""<ram:ApplicableTradeTax>
      {'' if g.cuota is None else f'<ram:CalculatedAmount>{g.cuota}</ram:CalculatedAmount>'}
      <ram:TypeCode>VAT</ram:TypeCode>
      {'' if g.motivo is None else f'<ram:ExemptionReason>{g.motivo}</ram:ExemptionReason>'}
      {'' if g.base is None else f'<ram:BasisAmount>{g.base}</ram:BasisAmount>'}
      {'' if g.categoria is None else f'<ram:CategoryCode>{g.categoria}</ram:CategoryCode>'}
      {'' if g.tipo is None else
       f'<ram:RateApplicablePercent>{g.tipo}</ram:RateApplicablePercent>'}
    </ram:ApplicableTradeTax>"""
        for g in grupos
    )
    xml_ajustes = "".join(
        f"""<ram:SpecifiedTradeAllowanceCharge>
      <ram:ChargeIndicator>
        <udt:Indicator>{'true' if a.es_cargo else 'false'}</udt:Indicator>
      </ram:ChargeIndicator>
      <ram:ActualAmount>{a.importe}</ram:ActualAmount>
      {'' if a.categoria is None else f'''<ram:CategoryTradeTax>
        <ram:CategoryCode>{a.categoria}</ram:CategoryCode>
        {'' if a.tipo is None else
         f'<ram:RateApplicablePercent>{a.tipo}</ram:RateApplicablePercent>'}
      </ram:CategoryTradeTax>'''}
    </ram:SpecifiedTradeAllowanceCharge>"""
        for a in ajustes
    )
    totales = "".join(
        f"<ram:{etiqueta}>{valor}</ram:{etiqueta}>"
        for etiqueta, valor in (
            ("AllowanceTotalAmount", descuentos_total),
            ("ChargeTotalAmount", cargos_total),
        )
        if valor is not None
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocument><ram:ID>F-2026-0001</ram:ID></rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction>
    {xml_lineas}
    <ram:ApplicableHeaderTradeAgreement>{_partes_cii(partes)}</ram:ApplicableHeaderTradeAgreement>
    <ram:ApplicableHeaderTradeDelivery>
      {'' if pais_entrega is None else
       f'<ram:ShipToTradeParty><ram:PostalTradeAddress><ram:CountryID>{pais_entrega}'
       '</ram:CountryID></ram:PostalTradeAddress></ram:ShipToTradeParty>'}
      {'' if fecha_entrega is None else
       '<ram:ActualDeliverySupplyChainEvent><ram:OccurrenceDateTime>'
       f'<udt:DateTimeString format="102">{fecha_entrega}</udt:DateTimeString>'
       '</ram:OccurrenceDateTime></ram:ActualDeliverySupplyChainEvent>'}
    </ram:ApplicableHeaderTradeDelivery>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>{MONEDA}</ram:InvoiceCurrencyCode>
      {xml_grupos}
      {'' if periodo is None else
       '<ram:BillingSpecifiedPeriod><ram:StartDateTime>'
       f'<udt:DateTimeString format="102">{periodo}</udt:DateTimeString>'
       '</ram:StartDateTime></ram:BillingSpecifiedPeriod>'}
      {xml_ajustes}
      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>
        {totales}
        {'' if total_iva is None else
         f'<ram:TaxTotalAmount currencyID="{MONEDA}">{total_iva}</ram:TaxTotalAmount>'}
      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>
    </ram:ApplicableHeaderTradeSettlement>
  </rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""


CONSTRUCTORES = {"UBL": (ubl, SINTAXIS_UBL), "CII": (cii, SINTAXIS_CII)}


@pytest.fixture(params=sorted(CONSTRUCTORES))
def revisar(request):
    """Devuelve una función que monta la factura y le pasa las reglas de IVA."""
    montar, sintaxis = CONSTRUCTORES[request.param]

    def hacer(**kwargs):
        xml = montar(**kwargs)
        raiz = etree.fromstring(xml.encode("utf-8"), parser=parser())
        return iva.reglas(raiz, sintaxis)

    return hacer


def codigos(incidencias, gravedad=None):
    return {
        i.codigo for i in incidencias if gravedad is None or i.gravedad == gravedad
    }


def una(incidencias, codigo):
    return next(i for i in incidencias if i.codigo == codigo)


# --- Lo que tiene que cuadrar ----------------------------------------------


class TestCuadre:
    def test_un_solo_tipo_bien_puesto(self, revisar):
        assert revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "21.00")],
        ) == []

    def test_dos_tipos_bien_puestos(self, revisar):
        """Material al 21 y comida al 10: el caso normal de un bar o un hotel."""
        assert revisar(
            lineas=[
                Linea("1", "100.00", tipo="21"),
                Linea("2", "50.00", tipo="10"),
            ],
            grupos=[
                Grupo("100.00", "21.00", tipo="21"),
                Grupo("50.00", "5.00", tipo="10"),
            ],
            total_iva="26.00",
        ) == []

    def test_una_linea_cambia_de_tipo_y_el_desglose_no(self, revisar):
        """El error caro: los totales generales siguen cuadrando y el IVA no.

        La línea 2 pasa al 10% pero el desglose sigue diciendo que todo va al
        21%. La suma de líneas no se entera: 150 sigue siendo 150.
        """
        incidencias = revisar(
            lineas=[
                Linea("1", "100.00", tipo="21"),
                Linea("2", "50.00", tipo="10"),
            ],
            grupos=[Grupo("150.00", "31.50", tipo="21")],
            total_iva="31.50",
        )
        assert "BR-S-08" in codigos(incidencias, ERROR)
        problema = una(incidencias, "BR-S-08")
        assert "100,00" in problema.esperado
        assert "línea 1" in problema.esperado
        assert problema.encontrado == "150.00"

        # Y la otra mitad del mismo error: del 10% no hay ni entrada.
        falta = una(incidencias, "IVA-TIPO-SIN-DESGLOSE")
        assert falta.gravedad == ERROR
        assert "50,00" in falta.mensaje
        assert "10%" in falta.esperado
        assert "línea 2" in falta.encontrado

    def test_un_tipo_por_entrada_no_avisa_de_mas(self, revisar):
        """Cada tipo con su entrada: no debe saltar IVA-TIPO-SIN-DESGLOSE."""
        incidencias = revisar(
            lineas=[
                Linea("1", "100.00", tipo="21"),
                Linea("2", "50.00", tipo="10"),
            ],
            grupos=[
                Grupo("100.00", "21.00", tipo="21"),
                Grupo("50.00", "5.00", tipo="10"),
            ],
            total_iva="26.00",
        )
        assert "IVA-TIPO-SIN-DESGLOSE" not in codigos(incidencias)

    def test_solo_se_dice_una_vez_por_tipo(self, revisar):
        """Tres líneas al 10% sin desglose son un problema, no tres."""
        incidencias = revisar(
            lineas=[
                Linea("1", "100.00", tipo="21"),
                Linea("2", "10.00", tipo="10"),
                Linea("3", "20.00", tipo="10"),
                Linea("4", "30.00", tipo="10"),
            ],
            grupos=[Grupo("100.00", "21.00", tipo="21")],
        )
        cuantas = [i for i in incidencias if i.codigo == "IVA-TIPO-SIN-DESGLOSE"]
        assert len(cuantas) == 1
        assert "60,00" in cuantas[0].mensaje

    def test_falta_el_desglose_de_un_tipo_usado(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00"), Linea("2", "50.00", categoria="E", tipo="0")],
            grupos=[Grupo("100.00", "21.00")],
        )
        problema = una(incidencias, "BR-E-01")
        assert problema.gravedad == ERROR
        assert "línea 2" in problema.encontrado

    def test_el_total_no_es_la_suma_de_las_cuotas(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00"), Linea("2", "50.00", tipo="10")],
            grupos=[
                Grupo("100.00", "21.00", tipo="21"),
                Grupo("50.00", "5.00", tipo="10"),
            ],
            total_iva="21.00",  # se ha olvidado el 10%
        )
        problema = una(incidencias, "BR-CO-14")
        assert problema.gravedad == ERROR
        assert "26,00" in problema.esperado
        assert problema.encontrado == "21.00"

    def test_la_cuota_no_sale_de_aplicar_el_tipo(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "16.00")],
            total_iva="16.00",
        )
        problema = una(incidencias, "BR-CO-17")
        assert "21,00" in problema.esperado
        assert problema.encontrado == "16.00"

    def test_un_centimo_se_tolera(self, revisar):
        """33.33 al 21% da 6.9993. Redondear a 7.00 es correcto."""
        assert revisar(
            lineas=[Linea("1", "33.33")],
            grupos=[Grupo("33.33", "7.00")],
            total_iva="7.00",
        ) == []

    def test_los_descuentos_restan_de_su_base(self, revisar):
        assert revisar(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("10.00")],
            grupos=[Grupo("90.00", "18.90")],
            total_iva="18.90",
            descuentos_total="10.00",
        ) == []

    def test_los_cargos_suman_a_su_base(self, revisar):
        assert revisar(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("10.00", es_cargo=True)],
            grupos=[Grupo("110.00", "23.10")],
            total_iva="23.10",
            cargos_total="10.00",
        ) == []

    def test_un_descuento_a_otro_tipo_va_a_su_base(self, revisar):
        """Un descuento al 10% no puede restar de la base del 21%."""
        incidencias = revisar(
            lineas=[Linea("1", "100.00"), Linea("2", "50.00", tipo="10")],
            ajustes=[Ajuste("10.00", tipo="10")],
            grupos=[
                Grupo("90.00", "18.90", tipo="21"),  # mal: el descuento no es suyo
                Grupo("40.00", "4.00", tipo="10"),
            ],
            total_iva="22.90",
            descuentos_total="10.00",
        )
        problema = una(incidencias, "BR-S-08")
        assert "100,00" in problema.esperado


class TestBaseFantasma:
    """Un grupo del desglose sin ningún concepto detrás.

    `BR-{X}-8` comparaba la base declarada con la suma de lo suyo, pero si no
    había nada suyo se callaba: la suma daba cero y no había con qué comparar.
    Así, un desglose que cobra sobre algo que no está en ninguna parte pasaba
    entero.
    """

    def test_la_base_no_tiene_nada_detras(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "150.00", tipo="10")],
            grupos=[Grupo("150.00", "31.50", tipo="21")],
            total_iva="31.50",
        )
        problema = una(incidencias, "BR-S-08")
        assert problema.gravedad == ERROR
        assert "sin nada detrás" in problema.encontrado

    def test_y_ademas_se_dice_lo_que_falta(self, revisar):
        """Las dos mitades del mismo error, cada una por su lado."""
        incidencias = revisar(
            lineas=[Linea("1", "150.00", tipo="10")],
            grupos=[Grupo("150.00", "31.50", tipo="21")],
            total_iva="31.50",
        )
        assert "IVA-TIPO-SIN-DESGLOSE" in codigos(incidencias, ERROR)

    def test_no_se_acusa_si_las_lineas_no_llevan_categoria(self, revisar):
        """Sin categoría en las líneas no es que falten: es que no se leen."""
        incidencias = revisar(
            lineas=[Linea("1", "150.00", categoria=None)],
            grupos=[Grupo("150.00", "31.50")],
            total_iva="31.50",
        )
        assert "BR-S-08" not in codigos(incidencias)
        assert "IVA-SIN-CATEGORIA" in codigos(incidencias, AVISO)

    def test_una_entrada_a_cero_sin_nada_detras_no_molesta(self, revisar):
        """Una entrada vacía a cero no le cuesta dinero a nadie."""
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "21.00"),
                    Grupo("0.00", "0.00", categoria="Z", tipo="0")],
        )
        assert "BR-Z-08" not in codigos(incidencias)


class TestAjustesSinDetallar:
    def test_no_se_acusa_en_falso(self, revisar):
        """Si los descuentos no vienen detallados, no se puede repartirlos.

        Decir «no se ha podido comprobar» es mejor que acusar a una factura
        que a lo mejor está bien.
        """
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("90.00", "18.90")],
            total_iva="18.90",
            descuentos_total="10.00",  # declarado, pero sin detallar
        )
        assert "IVA-AJUSTES-SIN-DETALLAR" in codigos(incidencias, AVISO)
        assert "BR-S-08" not in codigos(incidencias)

    def test_detallados_si_se_comprueban(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("10.00")],
            grupos=[Grupo("90.00", "18.90")],
            total_iva="18.90",
            descuentos_total="10.00",
        )
        assert "IVA-AJUSTES-SIN-DETALLAR" not in codigos(incidencias)

    def test_descuentos_y_cargos_se_miran_por_separado(self, revisar):
        """Sumados, un descuento y un cargo que se anulan borran la salvaguarda.

        Los dos totales son no negativos en una factura bien hecha, así que
        esto solo pasa con un documento mal generado. Pero es justo ahí donde
        importa: sumando, el módulo creería que no se declara ningún ajuste,
        se pondría a comprobar bases que no puede repartir, y acusaría en
        falso a la factura más rota, que es la que menos lo aguanta.
        """
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "21.00")],
            descuentos_total="-10.00",
            cargos_total="10.00",
        )
        assert "IVA-AJUSTES-SIN-DETALLAR" in codigos(incidencias, AVISO)

    def test_el_ajuste_se_reconoce_por_lo_que_es_no_por_como_se_llama(self):
        """La salvaguarda no puede depender del texto que lee el usuario.

        Antes se preguntaba si la descripción empezaba por «cargo» o por
        «descuento». Reescribir esa cadena —que es texto de interfaz— habría
        apagado la salvaguarda sin que ningún test se enterase.
        """
        from decimal import Decimal

        from validador import iva

        linea = iva.Apunte("línea 1", Decimal("100.00"), "S", Decimal(21))
        descuento = iva.Apunte("lo que sea", Decimal("-10.00"), "S", Decimal(21),
                               es_ajuste=True)
        assert not linea.es_ajuste
        assert descuento.es_ajuste


class TestTotalesDeAjustes:
    """BR-CO-11 y BR-CO-12: el total declarado es la suma de lo detallado.

    Antes esto no se comprobaba y el error salía igual, pero **por el sitio
    equivocado**: como `BR-{X}-8`, señalando el desglose de IVA, cuando lo que
    estaba mal era el total del descuento. La queja llegaba; la dirección, no.
    """

    def test_el_total_de_descuentos_no_cuadra(self):
        xml = ubl(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("10.00")],
            grupos=[Grupo("90.00", "18.90")],
            total_iva="18.90",
            descuentos_total="50.00",  # detalla 10, declara 50
        )
        problema = una(en16931.validar(xml).incidencias, "BR-CO-11")
        assert problema.gravedad == ERROR
        assert "10,00" in problema.esperado
        assert problema.encontrado == "50.00"

    def test_el_total_de_cargos_no_cuadra(self):
        xml = ubl(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("10.00", es_cargo=True)],
            grupos=[Grupo("110.00", "23.10")],
            total_iva="23.10",
            cargos_total="50.00",
        )
        assert "BR-CO-12" in codigos(en16931.validar(xml).incidencias, ERROR)

    def test_lo_que_deberia_ser_es_lo_que_se_comparo(self):
        # Un descuento de 10.005 se compara como 10.01; con `:.2f` se escribía
        # 10.00, lo mismo que declara la factura. Ver la de BR-CO-10.
        xml = ubl(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("10.005")],
            grupos=[Grupo("90.00", "18.90")],
            total_iva="18.90",
            descuentos_total="10.00",
        )
        problema = una(en16931.validar(xml).incidencias, "BR-CO-11")
        assert problema.esperado.startswith("10,01 "), problema.esperado

    def test_y_entonces_el_desglose_se_calla(self):
        """Una sola queja, en el campo que está mal.

        Con los ajustes descuadrados no se sabe cuál de las dos cifras es la
        buena, así que la base por tipo no se puede repartir. Comprobarla
        igualmente sacaría una segunda queja apuntando al desglose de IVA,
        que es justo donde no está el problema.
        """
        xml = ubl(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("10.00")],
            grupos=[Grupo("50.00", "10.50")],
            total_iva="10.50",
            descuentos_total="50.00",
        )
        codigos_vistos = codigos(en16931.validar(xml).incidencias, ERROR)
        assert "BR-CO-11" in codigos_vistos
        assert "BR-S-08" not in codigos_vistos

    def test_y_un_solo_centimo_tambien_calla_el_desglose(self):
        """El hueco entre dos margenes, que valia justo un centimo.

        BR-CO-12 compara sin margen desde el 13-09-2026, porque es lo que hace
        el esquematron oficial. El guardian que decide si el desglose se calla
        se quedo con el margen de un centimo de antes, asi que con exactamente
        un centimo de diferencia la regla se quejaba y el guardian decia que
        todo cuadraba: salian las dos quejas, y la segunda —IVA-BASE-TOLERADA—
        senala el desglose, que es donde no esta el problema.
        """
        xml = ubl(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("10.00", es_cargo=True)],
            grupos=[Grupo("110.01", "23.10")],
            total_iva="23.10",
            cargos_total="10.01",  # detalla 10,00 y declara 10,01
        )
        vistos = codigos(en16931.validar(xml).incidencias)
        assert "BR-CO-12" in vistos, "el centimo del total de cargos si se dice"
        assert "IVA-BASE-TOLERADA" not in vistos, (
            "dos quejas por el mismo centimo, y la segunda manda a mirar el "
            "desglose, que es justo donde no hay nada que arreglar"
        )

    def test_si_cuadran_no_se_dice_nada(self):
        xml = ubl(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("10.00")],
            grupos=[Grupo("90.00", "18.90")],
            total_iva="18.90",
            descuentos_total="10.00",
        )
        vistos = codigos(en16931.validar(xml).incidencias)
        assert "BR-CO-11" not in vistos
        assert "BR-S-08" not in vistos

    def test_descuentos_y_cargos_no_se_confunden(self):
        """Un cargo de 10 no justifica un total de descuentos de 10."""
        xml = ubl(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("10.00", es_cargo=True)],
            grupos=[Grupo("110.00", "23.10")],
            total_iva="23.10",
            descuentos_total="10.00",
            cargos_total="10.00",
        )
        assert "BR-CO-11" in codigos(en16931.validar(xml).incidencias, ERROR)


# --- Los cuatro datos de toda entrada del desglose -------------------------


class TestCamposDelDesglose:
    """BR-45 a BR-48.

    Sin estas reglas, una entrada a la que le faltaban la base y la cuota era
    completamente invisible: las de cuadre se saltan lo que está a None, así
    que el desglose más roto posible salía en el informe más limpio.
    """

    def test_sin_base(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo(None, "21.00")],
        )
        problema = una(incidencias, "BR-45")
        assert problema.gravedad == ERROR
        assert problema.encontrado == "(falta)"

    def test_sin_cuota(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", None)],
        )
        problema = una(incidencias, "BR-46")
        assert problema.gravedad == ERROR

    def test_sin_tipo(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "21.00", tipo=None)],
        )
        problema = una(incidencias, "BR-48")
        assert problema.gravedad == ERROR

    def test_lo_no_sujeto_puede_ir_sin_tipo(self, revisar):
        """BR-48 tiene una excepción, y es la única: la categoría O."""
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo=None)],
            grupos=[Grupo("100.00", "0.00", categoria="O", tipo=None,
                          motivo="No sujeta por el artículo 7")],
            total_iva="0.00",
        )
        assert "BR-48" not in codigos(incidencias)

    def test_el_tipo_ausente_solo_se_dice_una_vez(self, revisar):
        """BR-48 dice que falta; BR-{X}-5 dice que el valor no es el que toca.

        Antes BR-{X}-5 cubría los dos casos, así que al añadir BR-48 el tipo
        ausente habría salido por partida doble. Dos quejas para un solo
        agujero es exactamente lo que este validador intenta no hacer.
        """
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "21.00", tipo=None)],
        )
        assert "BR-S-05" not in codigos(incidencias)

    def test_el_desglose_vacio_no_enmudece_br_co_14(self, revisar):
        """Una entrada sin cuota dejaba muda también la suma de cuotas.

        `BR-CO-14` suma las cuotas del desglose; si ninguna entrada trae
        cuota, no encontraba nada que sumar y se callaba. El resultado era que
        la factura peor formada del mundo no daba ni una queja.
        """
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo(None, None)],
            total_iva="21.00",
        )
        assert {"BR-45", "BR-46"} <= codigos(incidencias, ERROR)


# --- Lo que exige cada categoría -------------------------------------------


class TestCategorias:
    def test_tipo_general_con_tipo_cero(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", tipo="0")],
            grupos=[Grupo("100.00", "0.00", tipo="0")],
            total_iva="0.00",
        )
        problema = una(incidencias, "BR-S-05")
        assert problema.gravedad == ERROR
        assert "Z para tipo cero" in problema.mensaje

    @pytest.mark.parametrize(
        "categoria,tipo,cuota,codigo",
        [
            ("S", "21", "21.00", "BR-S-10"),
            # BR-Z-10 no saltaba: la tabla solo sabia si el motivo era
            # obligatorio o no, y "no obligatorio" se leia como "da igual".
            # Una entrada a tipo cero con motivo de exencion pasaba entera.
            ("Z", "0", "0.00", "BR-Z-10"),
        ],
    )
    def test_motivo_de_exencion_donde_no_toca(
        self, revisar, categoria, tipo, cuota, codigo
    ):
        """La norma no solo exige el motivo: tambien lo prohibe.

        Tipo general y tipo cero no son exenciones, asi que no hay nada que
        justificar. Llevar motivo ahi es senal de que la categoria esta mal
        elegida, que es un error caro: el receptor se deduce un IVA que no
        deberia, o al reves.
        """
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria=categoria, tipo=tipo)],
            grupos=[Grupo("100.00", cuota, categoria=categoria, tipo=tipo,
                          motivo="Articulo 20")],
            total_iva=cuota,
        )
        problema = una(incidencias, codigo)
        assert problema.gravedad == ERROR
        assert "no es una exención" in problema.mensaje

    @pytest.mark.parametrize("categoria,codigo", [("L", "BR-IG-10"),
                                                  ("M", "BR-IP-10")])
    def test_el_igic_y_el_ipsi_no_llevan_motivo(self, revisar, categoria, codigo):
        """BR-IG-10 y BR-IP-10: «shall not have a VAT exemption reason».

        Hasta el 13-09-2026 esta prueba se llamaba «del IGIC y el IPSI no se
        opina» y exigía que esta misma factura pasara limpia: se creía que la
        norma no ataba a estas dos categorías. El esquematrón oficial las ata
        igual que al tipo general, y la factura de aquí abajo es un error.
        """
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria=categoria, tipo="7")],
            grupos=[Grupo("100.00", "7.00", categoria=categoria, tipo="7",
                          motivo="Regimen especial de Canarias")],
            total_iva="7.00",
        )
        problema = una(incidencias, codigo)
        assert problema.gravedad == ERROR
        assert problema.encontrado == "Regimen especial de Canarias"

    @pytest.mark.parametrize("categoria", ["L", "M"])
    def test_el_igic_y_el_ipsi_sin_motivo_pasan(self, revisar, categoria):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria=categoria, tipo="7")],
            grupos=[Grupo("100.00", "7.00", categoria=categoria, tipo="7")],
            total_iva="7.00",
        )
        assert incidencias == []

    @pytest.mark.parametrize("categoria", ["L", "M"])
    def test_el_igic_y_el_ipsi_admiten_el_cero(self, revisar, categoria):
        """«0 (zero) or greater than zero»: el cero no es un error.

        Ni un aviso. El IGIC en CII sale con una nota, la de que su
        esquematrón lo rechaza: ver `TestElCeroDelIgicEnCII`.
        """
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria=categoria, tipo="0")],
            grupos=[Grupo("100.00", "0.00", categoria=categoria, tipo="0")],
            total_iva="0.00",
        )
        assert [i.codigo for i in incidencias if i.gravedad != NOTA] == []

    @pytest.mark.parametrize("categoria,codigo", [("L", "BR-IG-05"),
                                                  ("M", "BR-IP-05")])
    def test_el_igic_y_el_ipsi_no_admiten_tipo_negativo(
            self, revisar, categoria, codigo):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria=categoria, tipo="-7")],
            grupos=[Grupo("100.00", "-7.00", categoria=categoria, tipo="-7")],
            total_iva="-7.00",
        )
        problema = una(incidencias, codigo)
        assert problema.gravedad == ERROR
        assert "línea 1" in problema.campo

    def test_exenta_sin_motivo(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="E", tipo="0")],
            grupos=[Grupo("100.00", "0.00", categoria="E", tipo="0")],
            total_iva="0.00",
        )
        problema = una(incidencias, "BR-E-10")
        assert problema.gravedad == ERROR
        assert "deducción" in problema.mensaje

    def test_exenta_con_motivo(self, revisar):
        assert revisar(
            lineas=[Linea("1", "100.00", categoria="E", tipo="0")],
            grupos=[
                Grupo("100.00", "0.00", categoria="E", tipo="0",
                      motivo="Exenta por el articulo 20.Uno.9 de la Ley del IVA")
            ],
            total_iva="0.00",
        ) == []

    def test_exenta_con_tipo(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="E", tipo="21")],
            grupos=[Grupo("100.00", "21.00", categoria="E", tipo="21",
                          motivo="Articulo 20")],
        )
        assert "BR-E-05" in codigos(incidencias, ERROR)

    def test_inversion_del_sujeto_pasivo(self, revisar):
        assert revisar(
            lineas=[Linea("1", "100.00", categoria="AE", tipo="0")],
            grupos=[
                Grupo("100.00", "0.00", categoria="AE", tipo="0",
                      motivo="Inversion del sujeto pasivo, articulo 84.Uno.2")
            ],
            total_iva="0.00",
        ) == []

    def test_inversion_sin_explicar(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="AE", tipo="0")],
            grupos=[Grupo("100.00", "0.00", categoria="AE", tipo="0")],
            total_iva="0.00",
        )
        assert "BR-AE-10" in codigos(incidencias, ERROR)

    def test_entrega_intracomunitaria(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="K", tipo="0")],
            grupos=[Grupo("100.00", "0.00", categoria="K", tipo="0")],
            total_iva="0.00",
        )
        assert "BR-IC-10" in codigos(incidencias, ERROR)

    def test_exportacion(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="G", tipo="0")],
            grupos=[Grupo("100.00", "0.00", categoria="G", tipo="0")],
            total_iva="0.00",
        )
        assert "BR-G-10" in codigos(incidencias, ERROR)

    def test_no_sujeta_no_lleva_tipo(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo="0")],
            grupos=[Grupo("100.00", "0.00", categoria="O", tipo="0",
                          motivo="No sujeta, articulo 7")],
            total_iva="0.00",
        )
        problema = una(incidencias, "BR-O-05")
        assert "no hay tipo que aplicar" in problema.mensaje

    def test_no_sujeta_bien_puesta(self, revisar):
        """Y bien puesta es también sin identificadores de IVA: BR-O-02."""
        assert revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo=None)],
            grupos=[Grupo("100.00", "0.00", categoria="O", tipo=None,
                          motivo="No sujeta, articulo 7 de la Ley del IVA")],
            total_iva="0.00",
            partes={},
        ) == []

    def test_no_sujeta_no_se_mezcla(self, revisar):
        incidencias = revisar(
            lineas=[
                Linea("1", "100.00"),
                Linea("2", "50.00", categoria="O", tipo=None),
            ],
            grupos=[
                Grupo("100.00", "21.00"),
                Grupo("50.00", "0.00", categoria="O", tipo=None,
                      motivo="No sujeta, articulo 7"),
            ],
        )
        problema = una(incidencias, "BR-O-11")
        assert "factura aparte" in problema.mensaje

    def test_igic_de_canarias(self, revisar):
        """Categoría española que casi ninguna herramienta europea nombra."""
        assert revisar(
            lineas=[Linea("1", "100.00", categoria="L", tipo="7")],
            grupos=[Grupo("100.00", "7.00", categoria="L", tipo="7")],
            total_iva="7.00",
        ) == []

    def test_ipsi_de_ceuta_y_melilla(self, revisar):
        assert revisar(
            lineas=[Linea("1", "100.00", categoria="M", tipo="4")],
            grupos=[Grupo("100.00", "4.00", categoria="M", tipo="4")],
            total_iva="4.00",
        ) == []

    def test_los_mensajes_nombran_la_categoria_en_castellano(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="AE", tipo="0")],
            grupos=[Grupo("100.00", "0.00", categoria="AE", tipo="0")],
            total_iva="0.00",
        )
        assert "inversión del sujeto pasivo" in una(incidencias, "BR-AE-10").mensaje


# --- Comprobaciones de la casa ---------------------------------------------


class TestNoSujeta:
    """La categoria O: lo que no esta sujeto no tiene tipo que aplicar.

    Salio de pasar el validador por `cef_XRechnung-O.xml`, una factura ajena
    correcta que recibia **tres** quejas, y ademas contradictorias entre si.
    """

    def test_lineas_sin_tipo_y_desglose_a_cero_es_la_misma_cosa(self, revisar):
        """El desglose trae 0 y las lineas no traen nada: no hay descuadre.

        La clave de agrupacion era (categoria, tipo), asi que ("O", None) y
        ("O", 0) caian en cubos distintos y se inventaban un desajuste. Salia
        BR-O-08 diciendo que al desglose le sobraban 100 sin conceptos detras, y
        a la vez IVA-TIPO-SIN-DESGLOSE diciendo que a los conceptos les faltaba
        desglose. Las dos sobre lo mismo, contandolo desde los dos lados.
        """
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo=None)],
            grupos=[Grupo("100.00", "0.00", categoria="O", tipo="0",
                          motivo="No sujeta")],
            total_iva="0.00",
        )
        assert "BR-O-08" not in codigos(incidencias)
        assert "IVA-TIPO-SIN-DESGLOSE" not in codigos(incidencias)
        assert "BR-O-05" not in codigos(incidencias), (
            "el tipo del desglose no es asunto de BR-O-05, que es de la linea")

    def test_la_linea_con_tipo_si_se_caza(self, revisar):
        """Lo que BR-O-05 si prohibe: que la **linea** declare tipo."""
        problema = una(
            revisar(
                lineas=[Linea("1", "100.00", categoria="O", tipo="21")],
                grupos=[Grupo("100.00", "0.00", categoria="O", tipo=None,
                              motivo="No sujeta")],
                total_iva="0.00",
            ),
            "BR-O-05",
        )
        assert problema.gravedad == ERROR
        assert "línea 1" in problema.campo


class TestDondeViveCadaRegla:
    """BR-{X}-5 es de la linea, no de la entrada del desglose.

    Comprobado en el esquematron oficial de EN 16931: BR-S-05 cuelga de
    `$VATS_Line` y BR-O-05 de `$VATO_Line`. Se miraba en el desglose, que casi
    siempre lleva el mismo tipo que sus lineas; por eso ningun test lo noto.
    """

    def test_el_tipo_malo_de_la_linea_es_lo_que_se_denuncia(self, revisar):
        problema = una(
            revisar(
                lineas=[Linea("1", "100.00", tipo="0")],
                grupos=[Grupo("100.00", "0.00", tipo="0")],
                total_iva="0.00",
            ),
            "BR-S-05",
        )
        assert "línea 1" in problema.campo, (
            "tiene que sennalar la linea, que es de donde sale la regla")

    def test_el_igic_y_el_ipsi_usan_los_codigos_de_la_copia_fijada(self, revisar):
        """BR-IG-* y BR-IP-*, los del modelo de la copia oficial que se fija (1.3.17).

        No son los unicos que han tenido: en UBL fueron BR-AF-* y BR-AG-* de la
        1.3.14 a la 1.3.16, y CII los cruza en la 1.3.17. Si otra copia los
        cambia, test_norma_oficial se pone en rojo y esto cambia con ella.
        """
        assert iva.REGLAS["L"].codigo == "IG"
        assert iva.REGLAS["M"].codigo == "IP"


# El tipo bueno de cada categoría que tiene que llevarlo, para montar al lado
# del concepto sin tipo una entrada del desglose que no se queje de nada.
_TIPO_DE_CADA_CATEGORIA = {"S": "21", "Z": "0", "E": "0", "AE": "0", "K": "0",
                           "G": "0", "L": "7", "M": "4"}


def _sin_tipo(categoria, linea=None, ajuste=None):
    """La factura de una categoría con la línea o el ajuste sin tipo."""
    tipo = _TIPO_DE_CADA_CATEGORIA[categoria]
    cuota = f"{Decimal(tipo):.2f}"
    return dict(
        lineas=[Linea("1", "100.00", categoria=categoria,
                      tipo=None if linea is None else tipo)],
        ajustes=[] if ajuste is None else [
            Ajuste("10.00", es_cargo=ajuste == "cargo", categoria=categoria, tipo=None)],
        grupos=[Grupo("100.00", cuota, categoria=categoria, tipo=tipo)],
        total_iva=cuota,
    )


class TestElTipoQueFalta:
    """BR-{X}-05, 06 y 07 también cuando el concepto no trae tipo.

    Hasta el 11-10-2026 aquí se callaba, con un comentario: «que el tipo falte
    lo dice BR-48». BR-48 es del desglose, no de la línea, y una línea exenta
    sin tipo con su entrada del desglose a cero pasaba sin una queja. En el
    esquematrón oficial las tres son una comparación con el tipo, y sin tipo
    la comparación es falsa: saltan en todas las categorías menos en la O, que
    pide lo contrario. Que eso dice el texto oficial de cada vinculación lo
    comprueba `test_norma_oficial`.
    """

    @pytest.mark.parametrize("categoria", sorted(_TIPO_DE_CADA_CATEGORIA))
    def test_la_linea_sin_tipo(self, revisar, categoria):
        incidencias = revisar(**_sin_tipo(categoria))
        codigo = f"BR-{iva.REGLAS[categoria].codigo}-05"
        assert codigo in codigos(incidencias, ERROR)
        problema = una(incidencias, codigo)
        assert problema.encontrado == "(sin tipo)"
        assert "línea 1" in problema.campo

    @pytest.mark.parametrize("ajuste,sufijo", [("descuento", "06"), ("cargo", "07")])
    @pytest.mark.parametrize("categoria", sorted(_TIPO_DE_CADA_CATEGORIA))
    def test_el_descuento_o_el_cargo_sin_tipo(self, revisar, categoria, ajuste, sufijo):
        incidencias = revisar(**_sin_tipo(categoria, linea="con tipo", ajuste=ajuste))
        familia = iva.REGLAS[categoria].codigo
        assert f"BR-{familia}-{sufijo}" in codigos(incidencias, ERROR)
        assert una(incidencias, f"BR-{familia}-{sufijo}").encontrado == "(sin tipo)"
        assert f"BR-{familia}-05" not in codigos(incidencias), (
            "la línea trae su tipo: la queja es del ajuste y solo del ajuste")

    def test_con_su_tipo_no_salta(self, revisar):
        for categoria in _TIPO_DE_CADA_CATEGORIA:
            incidencias = revisar(**_sin_tipo(categoria, linea="con tipo"))
            assert f"BR-{iva.REGLAS[categoria].codigo}-05" not in codigos(incidencias), categoria

    def test_dice_que_falta_y_no_que_esta_mal(self, revisar):
        problema = una(revisar(**_sin_tipo("E")), "BR-E-05")
        assert "sin tipo" in problema.mensaje
        assert "no está a cero" not in problema.mensaje
        assert problema.esperado == "0"

    def test_el_que_falta_y_el_malo_son_dos_quejas(self, revisar):
        """Agrupadas por tipo, como siempre: el que falta no se mezcla con el cero."""
        incidencias = revisar(
            lineas=[Linea("1", "100.00", tipo="0"), Linea("2", "100.00", tipo=None),
                    Linea("3", "100.00")],
            grupos=[Grupo("300.00", "21.00")],
        )
        salen = sorted((i.encontrado, i.campo) for i in incidencias if i.codigo == "BR-S-05")
        assert salen == [("(sin tipo)", "Conceptos: línea 2"), ("0", "Conceptos: línea 1")]

    def test_la_no_sujeta_sin_tipo_sigue_valiendo(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo=None)],
            ajustes=[Ajuste("10.00", categoria="O", tipo=None),
                     Ajuste("10.00", es_cargo=True, categoria="O", tipo=None)],
            grupos=[Grupo("100.00", "0.00", categoria="O", tipo=None, motivo="Art. 7")],
            total_iva="0.00",
        )
        assert not {"BR-O-05", "BR-O-06", "BR-O-07"} & codigos(incidencias)

    def test_la_ficha_de_cada_una_lo_dice(self):
        """La de BR-IP-05 decía lo contrario: «la queja no es ésta sino BR-48»."""
        callan = [f"BR-{iva.REGLAS[c].codigo}-{s}" for c in _TIPO_DE_CADA_CATEGORIA
                  for s in ("05", "06", "07")
                  if "solo lo no sujeto va sin" not in CODIGOS[f"BR-{iva.REGLAS[c].codigo}-{s}"]]
        assert not callan, f"fichas que no dicen que sin tipo también salta: {callan}"


def _igic(nombre, categoria="L", tipo="0", ajuste=None):
    """Las reglas de IVA de una factura de IGIC (o de IPSI) en una sintaxis."""
    montar, sintaxis = CONSTRUCTORES[nombre]
    cuota = f"{Decimal(tipo):.2f}"
    xml = montar(
        lineas=[Linea("1", "100.00", categoria=categoria, tipo=tipo)],
        ajustes=[] if ajuste is None else [
            Ajuste("10.00", es_cargo=ajuste == "cargo", categoria=categoria, tipo=tipo)],
        grupos=[Grupo("100.00", cuota, categoria=categoria, tipo=tipo)],
        total_iva=cuota,
    )
    return iva.reglas(etree.fromstring(xml.encode("utf-8"), parser=parser()), sintaxis)


class TestElCeroDelIgicEnCII:
    """El IGIC a tipo cero: la norma lo admite y el esquematrón de CII no.

    BR-IG-05, 06 y 07 dicen «0 (zero) or greater than zero», y así las escribe
    la vinculación de UBL, `>= 0`. La de CII compara con `> 0`, y en el IPSI,
    BR-IP, con `>= 0`. Se denunció en el repositorio oficial (issue 519) y se
    cerró el 29-09-2026 cambiando los nombres, no la comparación. Aquí se sigue
    a la norma, y una nota dice que el esquematrón de CII la rechaza. Lo que
    dice cada vinculación lo lee `test_norma_oficial`.
    """

    def test_en_cii_es_una_nota_y_no_un_error(self):
        incidencias = _igic("CII")
        assert "BR-IG-05" not in codigos(incidencias)
        nota = una(incidencias, "IVA-CERO-ESQUEMATRON")
        assert nota.gravedad == NOTA
        assert "BR-IG-05" in nota.mensaje and "CII" in nota.mensaje
        assert nota.campo == "Conceptos: línea 1"

    def test_cita_la_regla_con_el_nombre_que_le_da_cii(self):
        """BR-IP-05 es lo que dirá el esquematrón de CII de la 1.3.17, y BR-IG-05 la de aquí."""
        nota = una(_igic("CII"), "IVA-CERO-ESQUEMATRON")
        assert "BR-IP-05 (aquí, BR-IG-05)" in nota.mensaje

    @pytest.mark.parametrize("ajuste,regla", [("descuento", "BR-IG-06"), ("cargo", "BR-IG-07")])
    def test_el_descuento_y_el_cargo_dicen_su_regla(self, ajuste, regla):
        nota = una(_igic("CII", ajuste=ajuste), "IVA-CERO-ESQUEMATRON")
        assert "BR-IG-05" in nota.mensaje and regla in nota.mensaje
        assert nota.campo == f"Conceptos: línea 1, {ajuste} 1"

    def test_en_ubl_no_hay_nada_que_decir(self):
        assert "IVA-CERO-ESQUEMATRON" not in codigos(_igic("UBL"))

    def test_el_ipsi_a_cero_tampoco(self):
        assert "IVA-CERO-ESQUEMATRON" not in codigos(_igic("CII", categoria="M"))

    def test_el_igic_con_tipo_no(self):
        assert "IVA-CERO-ESQUEMATRON" not in codigos(_igic("CII", tipo="7"))

    def test_el_negativo_sigue_siendo_un_error(self):
        incidencias = _igic("CII", tipo="-7")
        assert "BR-IG-05" in codigos(incidencias, ERROR)
        assert "IVA-CERO-ESQUEMATRON" not in codigos(incidencias)

    def test_sin_desglose_tambien(self):
        """Sin desglose las reglas del tipo siguen corriendo, y esta con ellas."""
        montar, sintaxis = CONSTRUCTORES["CII"]
        xml = montar(lineas=[Linea("1", "100.00", categoria="L", tipo="0")], grupos=[])
        incidencias = iva.reglas(etree.fromstring(xml.encode("utf-8"), parser=parser()), sintaxis)
        assert "IVA-CERO-ESQUEMATRON" in codigos(incidencias, NOTA)

    def test_las_fichas_de_br_ig_lo_dicen(self):
        """Es adonde llega quien vea su CII rechazada con BR-IP-05, por la frase del cruce."""
        for sufijo in ("05", "06", "07"):
            assert "IVA-CERO-ESQUEMATRON" in CODIGOS[f"BR-IG-{sufijo}"], sufijo


class TestPropias:
    def test_tipo_que_no_existe_en_espana(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", tipo="15")],
            grupos=[Grupo("100.00", "15.00", tipo="15")],
            total_iva="15.00",
        )
        problema = una(incidencias, "IVA-TIPO")
        assert problema.gravedad == AVISO
        assert "21%, 10%, 4% o 0%" == problema.esperado

    def test_los_tipos_espanoles_no_avisan(self, revisar):
        for tipo, cuota in (("21", "21.00"), ("10", "10.00"), ("4", "4.00")):
            incidencias = revisar(
                lineas=[Linea("1", "100.00", tipo=tipo)],
                grupos=[Grupo("100.00", cuota, tipo=tipo)],
                total_iva=cuota,
            )
            assert "IVA-TIPO" not in codigos(incidencias), tipo

    def test_el_igic_no_se_mide_con_los_tipos_peninsulares(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="L", tipo="7")],
            grupos=[Grupo("100.00", "7.00", categoria="L", tipo="7")],
            total_iva="7.00",
        )
        assert "IVA-TIPO" not in codigos(incidencias)

    def test_categoria_inventada(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="X", tipo="21")],
            grupos=[Grupo("100.00", "21.00", categoria="X", tipo="21")],
        )
        problema = una(incidencias, "IVA-CATEGORIA-RARA")
        assert problema.gravedad == AVISO
        assert "AE" in problema.mensaje

    def test_desglose_sin_categoria(self, revisar):
        """Lleva BR-47, que es su codigo oficial, no uno de la casa.

        La norma ya tiene regla para esto: "cada entrada del desglose se
        define por su codigo de categoria". Ponerle un codigo inventado le
        quita al lector la posibilidad de buscarlo, que es el mismo dano que
        hacia BR-CO-14 usado al reves.
        """
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "21.00", categoria=None)],
        )
        assert "BR-47" in codigos(incidencias, ERROR)
        assert "IVA-SIN-CATEGORIA" not in codigos(incidencias, ERROR)

    def test_lineas_sin_categoria_solo_avisan(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria=None)],
            grupos=[Grupo("100.00", "21.00")],
        )
        problema = una(incidencias, "IVA-SIN-CATEGORIA")
        assert problema.gravedad == AVISO
        assert "línea 1" in problema.campo

    def test_iva_declarado_sin_desglose(self, revisar):
        problema = una(revisar(lineas=[Linea("1", "100.00")]), "BR-CO-18")
        assert problema.gravedad == ERROR
        assert "21.00 de IVA sin desglosar" == problema.encontrado

    @pytest.mark.parametrize("total", [None, "0.00"])
    def test_sin_desglose_no_hay_factura_valida(self, revisar, total):
        """Antes esto callaba, y era el hueco mas grande del modulo.

        BR-CO-18 exige al menos una entrada del desglose, sin excepciones. La
        version anterior solo avisaba -aviso, no error- y ademas solo si el
        IVA declarado no era cero, asi que una factura sin desglose y sin
        total pasaba en el informe mas limpio posible.
        """
        problema = una(
            revisar(lineas=[Linea("1", "100.00")], total_iva=total), "BR-CO-18"
        )
        assert problema.gravedad == ERROR


# --- Que entren en el informe de siempre -----------------------------------


class TestIntegracion:
    def test_salen_por_en16931(self):
        """Son reglas de EN 16931: quien llama a `validar` debe verlas."""
        xml = ubl(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "16.00")],
            total_iva="16.00",
        )
        assert "BR-CO-17" in codigos(en16931.validar(xml).incidencias, ERROR)

    def test_el_decimal_no_se_va_por_el_float(self):
        incidencias = iva.reglas(
            etree.fromstring(
                ubl(
                    lineas=[Linea("1", "0.10"), Linea("2", "0.20")],
                    grupos=[Grupo("0.30", "0.06")],
                    total_iva="0.06",
                ).encode("utf-8"),
                parser=parser(),
            ),
            SINTAXIS_UBL,
        )
        assert incidencias == []
        assert Decimal("0.10") + Decimal("0.20") == Decimal("0.30")


# --- La base de un desglose con una categoría que no es de la lista --------


class TestUnaCategoriaFueraDeLaLista:
    """`IVA-BASE`: la misma regla que las BR-{X}-8, sin una BR a la que colgarse.

    Las nueve categorías de UNCL5305 tienen cada una su regla numerada —BR-S-08,
    BR-Z-08, BR-E-08…— y la comprobación es siempre la misma: la base declarada
    en el desglose es la suma de lo que se le imputa. Cuando el documento
    escribe una categoría que no está en la lista, la cuenta se sigue pudiendo
    hacer y la BR no existe, así que sale con nombre propio.

    No lo provocaba nadie hasta el 06-09-2026. Es una rama de un `if` de una
    línea, y de las que se rompen sin ruido: con la categoría mal leída, el
    código sería `BR-None-8` y nadie lo vería porque nadie lo miraba.
    """

    def test_la_base_que_no_cuadra_sale_con_nombre_propio(self, revisar):
        salta = revisar(
            lineas=[Linea("1", "100.00", categoria="B")],
            grupos=[Grupo("999.00", "21.00", categoria="B")],
        )
        problema = una(salta, "IVA-BASE")
        assert problema.gravedad == ERROR
        assert "100,00" in problema.esperado

    def test_con_una_categoria_de_la_lista_sale_su_BR(self, revisar):
        """El control: si esto también diera `IVA-BASE`, lo de arriba no
        distinguiría la rama nueva de la de siempre."""
        salta = revisar(
            lineas=[Linea("1", "100.00", categoria="S")],
            grupos=[Grupo("999.00", "21.00", categoria="S")],
        )
        assert "BR-S-08" in codigos(salta)
        assert "IVA-BASE" not in codigos(salta)

    def test_si_cuadra_no_dice_nada(self, revisar):
        salta = revisar(
            lineas=[Linea("1", "100.00", categoria="B")],
            grupos=[Grupo("100.00", "21.00", categoria="B")],
        )
        assert "IVA-BASE" not in codigos(salta)


class TestUnaSintaxisSinCategoriaDeIVA:
    """`IVA-CATEGORIA-SIN-MAPA`, el código que hoy no puede sacar ningún fichero.

    Las cuatro sintaxis admitidas tienen su ruta a la categoría —UBL, CII y
    EDIFACT la escriben, y de Facturae se deduce desde el 06-09-2026—, así que
    hoy esta rama no la alcanza ninguna factura real. Eso no la hace inútil:
    es lo que dirá el validador el día que entre una sintaxis que no tenga
    dónde escribirla, y sin ella esa sintaxis se saltaría en silencio todas
    las reglas que dependen de la categoría.

    Lo que sí sería mentira es publicarla en el catálogo de «los códigos que
    puede sacar este validador» sin que nada la haya visto salir nunca. Así
    que se provoca con un mapa al que se le quita la ruta, que es exactamente
    la situación que describe.
    """

    def _sin_mapa(self, xml: str):
        import dataclasses

        from validador.sintaxis import SIN_MAPA, SINTAXIS_UBL

        mapa = dataclasses.replace(
            SINTAXIS_UBL, desglose_categoria=SIN_MAPA, linea_categoria=SIN_MAPA)
        raiz = etree.fromstring(xml.encode("utf-8"), parser=parser())
        return iva.reglas(raiz, mapa)

    def test_se_dice_una_vez_y_como_nota(self):
        salta = [i for i in self._sin_mapa(
            ubl(lineas=[Linea("1", "100.00")], grupos=[Grupo("100.00", "21.00")]))
            if i.codigo == "IVA-CATEGORIA-SIN-MAPA"]
        assert len(salta) == 1, "una por documento, no una por entrada"
        assert salta[0].gravedad == NOTA
        assert "UNCL5305" in salta[0].mensaje

    def test_con_dos_entradas_del_desglose_sigue_siendo_una(self):
        """Es una propiedad de la sintaxis, no de la factura."""
        salta = [i for i in self._sin_mapa(ubl(
            lineas=[Linea("1", "100.00"), Linea("2", "50.00", tipo="10")],
            grupos=[Grupo("100.00", "21.00"), Grupo("50.00", "5.00", tipo="10")]))
            if i.codigo == "IVA-CATEGORIA-SIN-MAPA"]
        assert len(salta) == 1

    def test_con_el_mapa_de_verdad_no_sale(self, revisar):
        assert "IVA-CATEGORIA-SIN-MAPA" not in codigos(revisar(
            lineas=[Linea("1", "100.00")], grupos=[Grupo("100.00", "21.00")]))


class TestLoQueDicenLasPruebasOficiales:
    """Lo que las pruebas unitarias oficiales cazaron el 13-09-2026, por UBL y CII.

    Las pruebas oficiales son de UBL. Estas montan lo mismo en las dos
    sintaxis, para que el arreglo no quede probado solo en una.
    """

    def test_sin_desglose_se_sigue_mirando_el_tipo_de_las_lineas(self, revisar):
        """BR-CO-18 y BR-S-05 son dos defectos, y se dicen los dos."""
        incidencias = revisar(lineas=[Linea("1", "100.00", tipo="0")], grupos=[])
        assert {"BR-CO-18", "BR-S-05", "BR-S-01"} <= codigos(incidencias, ERROR)

    def test_un_descuento_sin_importe_no_esconde_su_categoria(self, revisar):
        """El descuento sin importe tiene categoría, y el desglose no la trae."""
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            ajustes=[Ajuste("", categoria="E", tipo="0")],
            grupos=[Grupo("100.00", "21.00")],
        )
        assert "BR-E-01" in codigos(incidencias, ERROR)

    def test_dos_entradas_exentas_incumplen_br_e_01(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="E", tipo="0")],
            grupos=[Grupo("60.00", "0.00", categoria="E", tipo="0", motivo="Art. 20"),
                    Grupo("40.00", "0.00", categoria="E", tipo="0", motivo="Art. 25")],
            total_iva="0.00",
        )
        problema = una(incidencias, "BR-E-01")
        assert problema.encontrado == "2 entradas"

    def test_dos_entradas_al_tipo_general_si_valen(self, revisar):
        """Una por tipo: el 21 y el 10 son dos, y la norma pide al menos una."""
        incidencias = revisar(
            lineas=[Linea("1", "100.00"), Linea("2", "50.00", tipo="10")],
            grupos=[Grupo("100.00", "21.00"), Grupo("50.00", "5.00", tipo="10")],
            total_iva="26.00",
        )
        assert "BR-S-01" not in codigos(incidencias)

    def test_la_cuota_a_menos_de_una_unidad_es_una_nota(self, revisar):
        """21,50 sobre 100 al 21%: la norma lo admite, y se dice que se admitió."""
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "21.50")],
            total_iva="21.50",
        )
        assert "BR-CO-17" not in codigos(incidencias)
        nota = una(incidencias, "IVA-CUOTA-REDONDEO")
        assert nota.gravedad == NOTA
        assert "0,50" in nota.mensaje

    def test_la_cuota_a_mas_de_una_unidad_es_error(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "22.01")],
            total_iva="22.01",
        )
        assert "BR-CO-17" in codigos(incidencias, ERROR)

    def test_a_la_unidad_justa_ubl_y_cii_dicen_cosas_distintas(self):
        """Los dos esquematrones oficiales, al revés en el borde, y los dos se siguen."""
        grupo = iva.Grupo("S", Decimal(25), Decimal(1000), Decimal(251), None)
        en_ubl = [i.codigo for i in iva._regla_cuota_por_grupo(grupo, SINTAXIS_UBL)]
        en_cii = [i.codigo for i in iva._regla_cuota_por_grupo(grupo, SINTAXIS_CII)]
        assert en_ubl == ["BR-CO-17"]
        assert en_cii == ["IVA-CUOTA-REDONDEO"]

    def test_a_tipo_cero_la_cuota_tiene_que_ser_cero(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="Z", tipo="0")],
            grupos=[Grupo("100.00", "3.00", categoria="Z", tipo="0")],
            total_iva="3.00",
        )
        assert "BR-CO-17" in codigos(incidencias, ERROR)


class TestLaBaseComoCadaEsquematron:
    """BR-{X}-08 con el margen del esquematrón de cada sintaxis.

    Los dos oficiales no dicen lo mismo. El de UBL admite menos de una unidad
    en el tipo general, el IGIC y el IPSI, y exige exacto lo demás; el de CII,
    al revés, salvo la no sujeta, que exige exacta en los dos. Hasta el
    14-09-2026 aquí se daba un céntimo a todo, que era equivocarse en las dos
    direcciones y en las dos sintaxis. Qué margen lleva cada una lo sostiene
    `test_norma_oficial` leyendo el esquematrón; aquí se prueba que se aplica.
    """

    S = ("S", Decimal(21))
    E = ("E", Decimal(0))
    O = ("O", None)

    @staticmethod
    def base(categoria, tipo, declarada, suma, sintaxis):
        grupo = iva.Grupo(categoria, tipo, Decimal(declarada), Decimal(0), None)
        apuntes = [iva.Apunte("línea 1", Decimal(suma), categoria, tipo)]
        return [(i.codigo, i.gravedad)
                for i in iva._regla_base_por_grupo(grupo, apuntes, sintaxis)]

    def test_ubl_admite_menos_de_una_unidad_en_el_tipo_general(self):
        assert self.base(*self.S, "100.99", "100.00", SINTAXIS_UBL) == [
            ("IVA-BASE-TOLERADA", AVISO)]

    def test_pero_no_la_unidad_entera(self):
        assert self.base(*self.S, "101.00", "100.00", SINTAXIS_UBL) == [("BR-S-08", ERROR)]
        assert self.base(*self.S, "99.00", "100.00", SINTAXIS_UBL) == [("BR-S-08", ERROR)]

    def test_ubl_exige_exacta_la_exenta(self):
        assert self.base(*self.E, "100.01", "100.00", SINTAXIS_UBL) == [("BR-E-08", ERROR)]

    def test_cii_exige_exacto_el_tipo_general(self):
        """Un céntimo, que aquí se dejó pasar durante meses, es error en CII."""
        assert self.base(*self.S, "100.01", "100.00", SINTAXIS_CII) == [("BR-S-08", ERROR)]

    def test_cii_admite_menos_de_una_unidad_en_la_exenta(self):
        assert self.base(*self.E, "100.99", "100.00", SINTAXIS_CII) == [
            ("IVA-BASE-TOLERADA", AVISO)]
        assert self.base(*self.E, "101.00", "100.00", SINTAXIS_CII) == [("BR-E-08", ERROR)]

    def test_lo_que_deberia_ser_es_lo_que_se_comparo(self):
        # Una línea de 100.005 se compara como 100.01. Con `:.2f` el error
        # decía «Debería ser: 100.00 · Tiene: 100.00».
        grupo = iva.Grupo("S", Decimal(21), Decimal("100.00"), Decimal(0), None)
        apuntes = [iva.Apunte("línea 1", Decimal("100.005"), "S", Decimal(21))]
        (problema,) = iva._regla_base_por_grupo(grupo, apuntes, SINTAXIS_CII)
        assert problema.codigo == "BR-S-08"
        assert problema.esperado.startswith("100,01 "), problema.esperado

    def test_la_no_sujeta_es_exacta_en_las_dos(self):
        for sintaxis in (SINTAXIS_UBL, SINTAXIS_CII):
            assert self.base(*self.O, "100.01", "100.00", sintaxis) == [("BR-O-08", ERROR)]

    def test_la_base_exacta_no_dice_nada(self):
        for sintaxis in (SINTAXIS_UBL, SINTAXIS_CII):
            for categoria in (self.S, self.E, self.O):
                assert self.base(*categoria, "100.00", "100.00", sintaxis) == []

    def test_la_exenta_se_suma_entera_aunque_una_linea_traiga_otro_tipo(self, revisar):
        """Z, E, AE, K, G y O se suman por categoría, sin mirar el tipo.

        Así las suman los dos esquematrones: son las categorías de una sola
        entrada. Con el tipo en la clave, una línea exenta con un 5% escrito
        caía fuera de su entrada, y salían la base descuadrada y la línea sin
        desglose: dos quejas de un defecto que es BR-E-05 y nada más.
        """
        incidencias = revisar(
            lineas=[Linea("1", "60.00", categoria="E", tipo="0"),
                    Linea("2", "40.00", categoria="E", tipo="5")],
            grupos=[Grupo("100.00", "0.00", categoria="E", tipo="0", motivo="Art. 20")],
            total_iva="0.00",
        )
        salen = codigos(incidencias)
        assert "BR-E-05" in salen
        assert "BR-E-08" not in salen
        assert "IVA-TIPO-SIN-DESGLOSE" not in salen


class TestLaCuotaDeCadaCategoria:
    """BR-{X}-09. Cero exacto donde no hay impuesto, y base por tipo donde lo hay.

    Donde no hay impuesto, BR-CO-17 redondea a entero y deja pasar 0,40; esta
    no deja pasar un céntimo. Donde lo hay, repite la cuenta de BR-CO-17, y
    en CII no del todo: en el borde de la unidad escribe «menos de» y no
    «hasta», y el IGIC y el IPSI no los mira.
    """

    @staticmethod
    def cuota(categoria, tipo, base, cuota, sintaxis):
        grupo = iva.Grupo(categoria, None if tipo is None else Decimal(tipo),
                          Decimal(base), Decimal(cuota), None)
        salen = iva._reglas_cuota(grupo, sintaxis)
        return sorted((i.codigo, i.gravedad) for i in salen)

    def test_a_tipo_cero_ni_un_centimo(self):
        assert self.cuota("Z", "0", "100.00", "0.40", SINTAXIS_UBL) == [("BR-Z-09", ERROR)]

    def test_y_las_cinco_de_tipo_cero_igual(self):
        for categoria, familia in (("E", "E"), ("AE", "AE"), ("K", "IC"), ("G", "G")):
            assert self.cuota(categoria, "0", "100.00", "0.01", SINTAXIS_CII) == [
                (f"BR-{familia}-09", ERROR)]

    def test_la_no_sujeta_tambien_sin_tipo(self):
        assert self.cuota("O", None, "100.00", "0.01", SINTAXIS_UBL) == [("BR-O-09", ERROR)]

    def test_cuota_cero_no_dice_nada(self):
        for sintaxis in (SINTAXIS_UBL, SINTAXIS_CII):
            assert self.cuota("E", "0", "100.00", "0.00", sintaxis) == []

    def test_con_mucha_cuota_salen_las_dos(self):
        """BR-CO-17 y BR-Z-09 son dos reglas de la norma, y el oficial dice las dos."""
        assert self.cuota("Z", "0", "100.00", "21.00", SINTAXIS_UBL) == [
            ("BR-CO-17", ERROR), ("BR-Z-09", ERROR)]

    def test_tipo_general_a_menos_de_una_unidad_no_es_error(self):
        assert self.cuota("S", "21", "100.00", "21.99", SINTAXIS_UBL) == [
            ("IVA-CUOTA-REDONDEO", NOTA)]

    def test_tipo_general_a_una_unidad_en_ubl(self):
        assert self.cuota("S", "21", "100.00", "22.00", SINTAXIS_UBL) == [
            ("BR-CO-17", ERROR), ("BR-S-09", ERROR)]

    def test_en_cii_la_unidad_justa_pasa_una_y_no_la_otra(self):
        """BR-CO-17 escribe `<=` y BR-S-09 `<`: 22,00 sobre 100 al 21%.

        Y la nota de redondeo no sale: no se puede decir a la vez que la norma
        lo admite y que no.
        """
        assert self.cuota("S", "21", "100.00", "22.00", SINTAXIS_CII) == [("BR-S-09", ERROR)]

    def test_el_igic_se_mira_en_ubl_y_no_en_cii(self):
        assert self.cuota("L", "7", "100.00", "12.00", SINTAXIS_UBL) == [
            ("BR-CO-17", ERROR), ("BR-IG-09", ERROR)]
        assert self.cuota("L", "7", "100.00", "12.00", SINTAXIS_CII) == [("BR-CO-17", ERROR)]


class TestLosIdentificadoresDeCadaCategoria:
    """BR-{X}-02 a 04: a quién tiene que identificar la factura según la categoría.

    Cinco categorías se conforman con cualquier identificador fiscal del
    vendedor o de su representante; la inversión del sujeto pasivo pide además
    el del comprador, sea de IVA o su registro; la intracomunitaria y la
    exportación no se conforman con cualquiera, piden el de IVA; y la no sujeta
    los prohíbe. La cifra final dice de qué cuelga la categoría: 02 una línea,
    03 un descuento de documento, 04 un cargo.
    """

    SIN = {}

    def test_al_tipo_general_sin_identificar_al_vendedor(self, revisar):
        incidencias = revisar(lineas=[Linea("1", "100.00"), Linea("2", "0.00")],
                              grupos=[Grupo("100.00", "21.00")], partes=self.SIN)
        problema = una(incidencias, "BR-S-02")
        assert problema.gravedad == ERROR
        # Una queja para las dos líneas, que las nombra.
        assert "línea 1" in problema.encontrado and "línea 2" in problema.encontrado

    def test_basta_otro_identificador_fiscal(self, revisar):
        """BT-32: no hace falta que sea el de IVA."""
        incidencias = revisar(lineas=[Linea("1", "100.00")], grupos=[Grupo("100.00", "21.00")],
                              partes={"vendedor_registro_fiscal": "B12345678"})
        assert "BR-S-02" not in codigos(incidencias)

    def test_basta_el_del_representante(self, revisar):
        incidencias = revisar(lineas=[Linea("1", "100.00")], grupos=[Grupo("100.00", "21.00")],
                              partes={"representante_nif": "ESB87654321"})
        assert "BR-S-02" not in codigos(incidencias)

    def test_un_descuento_y_un_cargo_llevan_su_cifra(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="Z", tipo="0")],
            ajustes=[Ajuste("10.00", categoria="Z", tipo="0"),
                     Ajuste("5.00", es_cargo=True, categoria="Z", tipo="0")],
            grupos=[Grupo("95.00", "0.00", categoria="Z", tipo="0")],
            total_iva="0.00", descuentos_total="10.00", cargos_total="5.00",
            partes=self.SIN,
        )
        assert {"BR-Z-02", "BR-Z-03", "BR-Z-04"} <= codigos(incidencias, ERROR)

    def test_la_inversion_pide_tambien_al_comprador(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="AE", tipo="0")],
            grupos=[Grupo("100.00", "0.00", categoria="AE", tipo="0", motivo="Art. 84")],
            total_iva="0.00", partes={"vendedor_nif": "ESB12345678"},
        )
        problema = una(incidencias, "BR-AE-02")
        assert "comprador" in problema.campo

    def test_y_al_comprador_le_basta_su_registro(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="AE", tipo="0")],
            grupos=[Grupo("100.00", "0.00", categoria="AE", tipo="0", motivo="Art. 84")],
            total_iva="0.00",
            partes={"vendedor_nif": "ESB12345678", "comprador_registro": "A87654321"},
        )
        assert "BR-AE-02" not in codigos(incidencias)

    def test_la_intracomunitaria_no_se_conforma_con_cualquiera(self, revisar):
        """Del vendedor, el de IVA; del comprador, el de IVA. Un registro no vale."""
        for partes, quien in (
            ({"vendedor_registro_fiscal": "B12345678", "comprador_nif": "FR123"}, "vendedor"),
            ({"vendedor_nif": "ESB12345678", "comprador_registro": "123"}, "comprador"),
        ):
            incidencias = revisar(
                lineas=[Linea("1", "100.00", categoria="K", tipo="0")],
                grupos=[Grupo("100.00", "0.00", categoria="K", tipo="0", motivo="Art. 25")],
                total_iva="0.00", partes=partes,
            )
            assert quien in una(incidencias, "BR-IC-02").campo

    def test_la_exportacion_pide_el_de_iva_del_vendedor(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="G", tipo="0")],
            grupos=[Grupo("100.00", "0.00", categoria="G", tipo="0", motivo="Art. 21")],
            total_iva="0.00", partes={"vendedor_registro_fiscal": "B12345678"},
        )
        assert "BR-G-02" in codigos(incidencias, ERROR)

    def test_la_no_sujeta_prohibe_los_de_iva(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo=None)],
            grupos=[Grupo("100.00", "0.00", categoria="O", tipo=None, motivo="Art. 7")],
            total_iva="0.00",
        )
        problema = una(incidencias, "BR-O-02")
        assert "BT-31" in problema.encontrado and "BT-48" in problema.encontrado

    def test_pero_no_los_que_no_son_de_iva(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo=None)],
            grupos=[Grupo("100.00", "0.00", categoria="O", tipo=None, motivo="Art. 7")],
            total_iva="0.00",
            partes={"vendedor_registro_fiscal": "B12345678", "comprador_registro": "123"},
        )
        assert "BR-O-02" not in codigos(incidencias)

    def test_en_facturae_se_calla_lo_que_no_se_sabe(self):
        """Facturae no distingue la clase de identificador: ni exige ni prohíbe."""
        from validador.sintaxis import SINTAXIS_FACTURAE

        for categoria in ("S", "K", "G", "O", "AE"):
            apunte = iva.Apunte("línea 1", Decimal(100), categoria, Decimal(0))
            assert iva._regla_identificadores(
                etree.Element("Invoice"), SINTAXIS_FACTURAE, [apunte]) == []


class TestLaNoSujetaSinNadaMas:
    """BR-O-12, 13 y 14: con una entrada no sujeta, nada de otra categoría.

    BR-O-11 lo mira en el desglose; estas tres en lo que lo alimenta: las
    líneas, los descuentos de documento y los cargos. Un concepto sin
    categoría no cuenta, como en el esquematrón: no es «de otra categoría», es
    de ninguna, y de eso ya se queja otra regla.
    """

    GRUPO_O = Grupo("100.00", "0.00", categoria="O", tipo=None, motivo="Art. 7")

    def test_una_linea_de_otra_categoria(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo=None), Linea("2", "0.00")],
            grupos=[self.GRUPO_O], total_iva="0.00", partes={},
        )
        problema = una(incidencias, "BR-O-12")
        assert "línea 2" in problema.encontrado

    def test_un_descuento_y_un_cargo_de_otra_categoria(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo=None)],
            ajustes=[Ajuste("0.00"), Ajuste("0.00", es_cargo=True)],
            grupos=[self.GRUPO_O], total_iva="0.00", partes={},
            descuentos_total="0.00", cargos_total="0.00",
        )
        assert {"BR-O-13", "BR-O-14"} <= codigos(incidencias, ERROR)

    def test_sin_entrada_no_sujeta_no_se_mira(self, revisar):
        incidencias = revisar(lineas=[Linea("1", "100.00")], grupos=[Grupo("100.00", "21.00")])
        assert not {"BR-O-12", "BR-O-13", "BR-O-14"} & codigos(incidencias)

    def test_un_concepto_sin_categoria_no_es_de_otra(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo=None),
                    Linea("2", "0.00", categoria=None)],
            grupos=[self.GRUPO_O], total_iva="0.00", partes={},
        )
        assert "BR-O-12" not in codigos(incidencias)


class TestLaEntregaIntracomunitaria:
    """BR-IC-11 y 12: cuándo y adónde, que es lo que sostiene la exención."""

    LINEA_K = Linea("1", "100.00", categoria="K", tipo="0")
    GRUPO_K = Grupo("100.00", "0.00", categoria="K", tipo="0", motivo="Art. 25")

    def entrega(self, revisar, **extra):
        return revisar(lineas=[self.LINEA_K], grupos=[self.GRUPO_K], total_iva="0.00",
                       **extra)

    def test_sin_fecha_ni_periodo_ni_pais(self, revisar):
        salen = codigos(self.entrega(revisar), ERROR)
        assert {"BR-IC-11", "BR-IC-12"} <= salen

    def test_con_la_fecha_de_entrega(self, revisar):
        salen = codigos(self.entrega(revisar, fecha_entrega="20260901", pais_entrega="FR"))
        assert not {"BR-IC-11", "BR-IC-12"} & salen

    def test_o_con_el_periodo(self, revisar):
        salen = codigos(self.entrega(revisar, periodo="20260901", pais_entrega="FR"))
        assert "BR-IC-11" not in salen

    def test_sin_entrada_intracomunitaria_no_se_mira(self, revisar):
        salen = codigos(revisar(lineas=[Linea("1", "100.00")], grupos=[Grupo("100.00", "21.00")]))
        assert not {"BR-IC-11", "BR-IC-12"} & salen

    def test_lo_que_facturae_no_puede_escribir_no_se_reclama(self):
        """Ni el país de entrega ni la fecha de entrega tienen sitio en Facturae.

        La fecha podría venir por el periodo, que sí lo tiene; como falta la
        otra mitad, no se sabe, y no se reclama nada.
        """
        from validador.sintaxis import SIN_MAPA, SINTAXIS_FACTURAE

        assert SINTAXIS_FACTURAE.pais_entrega == SIN_MAPA
        assert SINTAXIS_FACTURAE.fecha_entrega == SIN_MAPA
        grupo = iva.Grupo("K", Decimal(0), Decimal(100), Decimal(0), "Art. 25")
        assert iva._regla_intracomunitaria(
            etree.Element("Invoice"), SINTAXIS_FACTURAE, [grupo]) == []


def test_la_s_no_se_llama_tipo_general():
    """En España la S lleva el 21 %, el 10 % y el 4 %, y el tipo general es
    solo el 21 %. Hasta el 18-10-2026 un libro salía como "S (tipo general) al
    4%". El nombre es el de la lista L4 de la Orden HAC/1028/2026."""
    from validador import glosario

    assert iva.nombre_categoria("S") == "S (régimen general)"
    assert not [codigo for codigo, ficha in glosario.CODIGOS.items()
                if "tipo general" in ficha.lower()]
