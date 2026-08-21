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
from validador.incidencias import AVISO, ERROR
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
    base: str
    cuota: str
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


# --- Las dos sintaxis ------------------------------------------------------


def ubl(lineas=(), grupos=(), ajustes=(), total_iva="21.00",
        descuentos_total=None, cargos_total=None):
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
      <cbc:TaxableAmount currencyID="{MONEDA}">{g.base}</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="{MONEDA}">{g.cuota}</cbc:TaxAmount>
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
        descuentos_total=None, cargos_total=None):
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
      <ram:CalculatedAmount>{g.cuota}</ram:CalculatedAmount>
      <ram:TypeCode>VAT</ram:TypeCode>
      {'' if g.motivo is None else f'<ram:ExemptionReason>{g.motivo}</ram:ExemptionReason>'}
      <ram:BasisAmount>{g.base}</ram:BasisAmount>
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
    <ram:ApplicableHeaderTradeAgreement/>
    <ram:ApplicableHeaderTradeDelivery/>
    <ram:ApplicableHeaderTradeSettlement>
      <ram:InvoiceCurrencyCode>{MONEDA}</ram:InvoiceCurrencyCode>
      {xml_grupos}
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
        assert "BR-S-8" in codigos(incidencias, ERROR)
        problema = una(incidencias, "BR-S-8")
        assert "100.00" in problema.esperado
        assert "línea 1" in problema.esperado
        assert problema.encontrado == "150.00"

        # Y la otra mitad del mismo error: del 10% no hay ni entrada.
        falta = una(incidencias, "IVA-TIPO-SIN-DESGLOSE")
        assert falta.gravedad == ERROR
        assert "50.00" in falta.mensaje
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
        assert "60.00" in cuantas[0].mensaje

    def test_falta_el_desglose_de_un_tipo_usado(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00"), Linea("2", "50.00", categoria="E", tipo="0")],
            grupos=[Grupo("100.00", "21.00")],
        )
        problema = una(incidencias, "BR-E-1")
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
        assert "26.00" in problema.esperado
        assert problema.encontrado == "21.00"

    def test_la_cuota_no_sale_de_aplicar_el_tipo(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "16.00")],
            total_iva="16.00",
        )
        problema = una(incidencias, "BR-CO-17")
        assert "21.00" in problema.esperado
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
        problema = una(incidencias, "BR-S-8")
        assert "100.00" in problema.esperado


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
        assert "BR-S-8" not in codigos(incidencias)

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


# --- Lo que exige cada categoría -------------------------------------------


class TestCategorias:
    def test_tipo_general_con_tipo_cero(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", tipo="0")],
            grupos=[Grupo("100.00", "0.00", tipo="0")],
            total_iva="0.00",
        )
        problema = una(incidencias, "BR-S-5")
        assert problema.gravedad == ERROR
        assert "Z para tipo cero" in problema.mensaje

    def test_tipo_general_con_motivo_de_exencion(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "21.00", motivo="Articulo 20")],
        )
        problema = una(incidencias, "BR-S-10")
        assert "no hay nada que eximir" in problema.mensaje

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
        assert "BR-E-5" in codigos(incidencias, ERROR)

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
        problema = una(incidencias, "BR-O-5")
        assert "no hay tipo que aplicar" in problema.mensaje

    def test_no_sujeta_bien_puesta(self, revisar):
        assert revisar(
            lineas=[Linea("1", "100.00", categoria="O", tipo=None)],
            grupos=[Grupo("100.00", "0.00", categoria="O", tipo=None,
                          motivo="No sujeta, articulo 7 de la Ley del IVA")],
            total_iva="0.00",
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
        incidencias = revisar(
            lineas=[Linea("1", "100.00")],
            grupos=[Grupo("100.00", "21.00", categoria=None)],
        )
        assert "IVA-SIN-CATEGORIA" in codigos(incidencias, ERROR)

    def test_lineas_sin_categoria_solo_avisan(self, revisar):
        incidencias = revisar(
            lineas=[Linea("1", "100.00", categoria=None)],
            grupos=[Grupo("100.00", "21.00")],
        )
        problema = una(incidencias, "IVA-SIN-CATEGORIA")
        assert problema.gravedad == AVISO
        assert "línea 1" in problema.campo

    def test_iva_declarado_sin_desglose(self, revisar):
        problema = una(revisar(lineas=[Linea("1", "100.00")]), "IVA-SIN-DESGLOSE")
        assert problema.gravedad == AVISO
        assert "21.00 de IVA sin desglosar" == problema.encontrado

    def test_sin_iva_y_sin_desglose_no_se_dice_nada(self, revisar):
        assert revisar(lineas=[Linea("1", "100.00")], total_iva=None) == []

    def test_iva_a_cero_sin_desglose_tampoco(self, revisar):
        assert revisar(lineas=[Linea("1", "100.00")], total_iva="0.00") == []


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
