"""Facturas con precios fijados con el IVA incluido.

La norma europea solo conoce precios sin IVA (BT-146). Un libro tiene precio
fijo de venta al público (Ley 10/2007, art. 9), y al público el precio se le
da con los impuestos (TRLGDCU, art. 20.1.c); un ticket que se canjea por
factura completa lleva el IVA dentro (RD 1619/2012, arts. 7.1.f y 15.6).
Para escribirlos en la norma hay que dividir por (1 + tipo) y redondear, y el
redondeo se multiplica por la cantidad. Lo planteó Svante Schubert en el CEN
(propuestas #163 y #164 a la EN 16931-1) y se midió aquí el 18-10-2026 con
siete facturas de libros al 4%:

- a la letra de la norma, con o sin BT-114 para cobrar el precio fijo: limpias;
- con la cuota sacada del precio con IVA y el precio sin IVA a cuatro
  decimales: la nota IVA-CUOTA-REDONDEO, 0,55 en 400 líneas y 0,30 en 25.000
  ejemplares;
- con el precio sin IVA a dos decimales y 25.000 ejemplares: BR-CO-17 y
  BR-S-09 en ERROR, 28,80 de cuota de más, y un mensaje que no decía por qué.

El ERROR es justo: la base se queda 27,69 corta de lo cobrado sin IVA. Lo que
faltaba era decirlo, y es lo que se prueba aquí. La factura de partida es la
de la orden de `test_solucion_publica`, sin anticipo, sin retención y sin la
línea de cobro.
"""

from decimal import ROUND_HALF_UP, Decimal

from validador import factura, glosario
from validador.incidencias import ERROR, NOTA

from tests.test_solucion_publica import DEL_BOE, cambia, quita

PROPIEDAD = DEL_BOE[DEL_BOE.index("<cac:AdditionalItemProperty>"):].split(
    "</cac:AdditionalItemProperty>")[0] + "</cac:AdditionalItemProperty>"


def _cabecera() -> str:
    xml = quita(DEL_BOE, "  <cac:PrepaidPayment>", "</cac:PrepaidPayment>\n")
    xml = quita(xml, "  <cac:WithholdingTaxTotal>", "</cac:WithholdingTaxTotal>\n")
    xml = quita(xml, "  <cac:CollectionInvoiceLine>", "</cac:CollectionInvoiceLine>\n")
    return xml[:xml.index("  <cac:TaxTotal>")]


CABECERA = _cabecera()


def _r(valor: Decimal, escala: str = "0.01") -> Decimal:
    return valor.quantize(Decimal(escala), rounding=ROUND_HALF_UP)


def libros(lineas, *, cuota_del_bruto: bool, decimales: str = "0.0001",
           cuota: Decimal | None = None, descuento: Decimal | None = None) -> str:
    """Una factura de libros al 4%: `lineas` son (precio con IVA, cantidad).

    `cuota_del_bruto` es lo que hace quien factura con precios fijos: el total
    es lo cobrado y la cuota sale por diferencia. Sin él, la cuota es base por
    tipo, a la letra de la norma.
    """
    trozos, base, bruto = [], Decimal(0), Decimal(0)
    for n, (pvp, cantidad) in enumerate(lineas, 1):
        neto = _r(pvp / Decimal("1.04"), decimales)
        importe = _r(neto * cantidad)
        base += importe
        bruto += pvp * cantidad
        trozos.append(f"""  <cac:InvoiceLine>
    <cbc:ID>{n}</cbc:ID>
    <cbc:InvoicedQuantity unitCode="H87">{cantidad}</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">{importe}</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Name>Libro {n}</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>4</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>
      {PROPIEDAD}
    </cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">{neto}</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
""")
    lineas_suma = base
    ajuste = ""
    if descuento is not None:
        base -= descuento
        bruto -= _r(descuento * Decimal("1.04"))
        ajuste = f"""  <cac:AllowanceCharge>
    <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
    <cbc:AllowanceChargeReason>Descuento a biblioteca</cbc:AllowanceChargeReason>
    <cbc:Amount currencyID="EUR">{descuento}</cbc:Amount>
    <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>4</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
  </cac:AllowanceCharge>
"""
    if cuota is None:
        cuota = _r(bruto) - base if cuota_del_bruto else _r(base * Decimal("0.04"))
    total = base + cuota
    descuentos = (f'    <cbc:AllowanceTotalAmount currencyID="EUR">{descuento}'
                  '</cbc:AllowanceTotalAmount>\n') if descuento is not None else ""
    return CABECERA + ajuste + f"""  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">{cuota}</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">{base}</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">{cuota}</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>4</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">{lineas_suma}</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">{base}</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">{total}</cbc:TaxInclusiveAmount>
{descuentos}    <cbc:PayableAmount currencyID="EUR">{total}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
""" + "".join(trozos) + "</Invoice>"


def _incidencias(xml: str):
    return factura.validar(xml.encode("utf-8")).incidencias


def _la(xml: str, codigo: str):
    suyas = [i for i in _incidencias(xml) if i.codigo == codigo]
    assert len(suyas) == 1, [(i.codigo, i.mensaje) for i in _incidencias(xml)]
    return suyas[0]


def _cuentas(xml: str) -> set[str]:
    return {i.codigo for i in _incidencias(xml) if i.gravedad != NOTA}


PEDIDO = [(Decimal("19.90"), 30), (Decimal("22.50"), 30), (Decimal("9.95"), 60),
          (Decimal("14.95"), 25), (Decimal("32.00"), 12)]
# 400 líneas de un ejemplar, de 9,95 a 10,25: el precio sin IVA redondea a
# cuatro decimales y el desfase se acumula línea a línea.
SUELTOS = [(Decimal("9.95") + Decimal("0.05") * (k % 7), 1) for k in range(400)]
# Una distribuidora: 25.000 ejemplares en tres líneas.
DISTRIBUIDORA = [(Decimal("19.90"), 5000), (Decimal("22.50"), 8000), (Decimal("9.95"), 12000)]

PISTA = "Las líneas cuadran con precios con el IVA incluido"


class TestLoQueEstaBien:
    def test_a_la_letra_de_la_norma_sale_limpia(self):
        xml = libros(PEDIDO, cuota_del_bruto=False)
        assert not _cuentas(xml) - {"SPFE-ALCANCE", "SPFE-COPIA"}
        assert not any(PISTA in i.mensaje for i in _incidencias(xml))

    def test_la_cuota_del_bruto_que_cuadra_al_centimo_no_dice_nada(self):
        # 101,02 contra 101,03: dentro del céntimo, sin nota y sin pista.
        xml = libros(PEDIDO, cuota_del_bruto=True)
        assert not [i for i in _incidencias(xml) if i.codigo in ("IVA-CUOTA-REDONDEO", "BR-CO-17")]


class TestLaNota:
    def test_400_lineas_dan_la_nota_y_su_explicacion(self):
        nota = _la(libros(SUELTOS, cuota_del_bruto=True), "IVA-CUOTA-REDONDEO")
        assert nota.gravedad == NOTA
        assert "0,55" in nota.mensaje
        assert PISTA in nota.mensaje
        assert "4039,85" in nota.mensaje

    def test_la_distribuidora_a_cuatro_decimales_tambien(self):
        nota = _la(libros(DISTRIBUIDORA, cuota_del_bruto=True), "IVA-CUOTA-REDONDEO")
        assert "0,30" in nota.mensaje and PISTA in nota.mensaje


class TestElError:
    XML = libros(DISTRIBUIDORA, cuota_del_bruto=True, decimales="0.01")

    def test_sigue_siendo_error(self):
        assert {"BR-CO-17", "BR-S-09"} <= _cuentas(self.XML)
        assert _la(self.XML, "BR-CO-17").gravedad == ERROR

    def test_dice_el_reparto_y_lo_que_se_pierde(self):
        mensaje = _la(self.XML, "BR-CO-17").mensaje
        assert PISTA in mensaje
        assert "398.900,00" in mensaje
        assert "383.557,69 de base y 15.342,31 de cuota" in mensaje
        assert "se queda corta en 27,69" in mensaje
        assert "más decimales" in mensaje

    def test_la_pista_va_una_vez(self):
        # BR-S-09 sale también y no repite el párrafo.
        assert PISTA not in _la(self.XML, "BR-S-09").mensaje


class TestCuandoNoSeDice:
    def test_un_error_de_cuota_cualquiera_no_lleva_pista(self):
        # Precios sin IVA de verdad y la cuota al 5% en vez del 4%.
        xml = libros(PEDIDO, cuota_del_bruto=False, cuota=Decimal("126.29"))
        error = _la(xml, "BR-CO-17")
        assert PISTA not in error.mensaje

    def test_con_un_descuento_en_la_entrada_no_se_afirma(self):
        # La cuota escogida para que la base, ya descontada, más la cuota
        # sumen justo los precios con IVA de las líneas (398.900,00): sin
        # mirar los descuentos, la pista saldría, y un descuento no tiene
        # precio con el que afirmarla. Base: 383.530,00 - 100,00.
        xml = libros(DISTRIBUIDORA, cuota_del_bruto=True, decimales="0.01",
                     descuento=Decimal("100.00"), cuota=Decimal("15470.00"))
        error = _la(xml, "BR-CO-17")
        assert PISTA not in error.mensaje

    def test_si_la_linea_no_es_su_precio_por_su_cantidad_no_se_afirma(self):
        # La primera línea, 50 por debajo de 19,13 x 5.000, y la cuota 50 por
        # encima: los precios con IVA siguen sumando la base más la cuota,
        # pero esa línea no es lo que dice su precio.
        xml = libros(DISTRIBUIDORA, cuota_del_bruto=True, decimales="0.01")
        xml = cambia(xml, '<cbc:LineExtensionAmount currencyID="EUR">95650.00</cbc:LineExtensionAmount>',
                     '<cbc:LineExtensionAmount currencyID="EUR">95600.00</cbc:LineExtensionAmount>')
        for viejo, nuevo in (("383530.00", "383480.00"), ("15370.00", "15420.00")):
            xml = xml.replace(viejo, nuevo)
        error = _la(xml, "BR-CO-17")
        assert "BR-CO-10" not in _cuentas(xml)
        assert PISTA not in error.mensaje

    def test_si_el_precio_no_es_por_unidad_no_se_afirma(self):
        xml = libros(DISTRIBUIDORA, cuota_del_bruto=True, decimales="0.01")
        # Una cantidad base del precio (BT-149): la línea ya no es precio por
        # cantidad, y de ahí no se puede sacar el precio con IVA.
        xml = cambia(xml, '<cbc:PriceAmount currencyID="EUR">19.13</cbc:PriceAmount>',
                     '<cbc:PriceAmount currencyID="EUR">19.13</cbc:PriceAmount>'
                     '<cbc:BaseQuantity unitCode="H87">10</cbc:BaseQuantity>')
        assert PISTA not in _la(xml, "BR-CO-17").mensaje


class TestElGlosario:
    def test_las_dos_fichas_lo_cuentan(self):
        assert "IVA incluido" in glosario.CODIGOS["BR-CO-17"]
        assert "IVA incluido" in glosario.CODIGOS["IVA-CUOTA-REDONDEO"]
