"""Comprobaciones de las reglas de negocio del formato Facturae.

La factura de prueba está construida para que cada fórmula del esquema tenga
algo que morder: dos líneas, descuento y cargo de línea, descuento y recargo
generales, un impuesto repercutido con recargo de equivalencia, una retención,
una subvención, un anticipo, una cantidad retenida, un pago en especie,
suplidos y gastos financieros. Cuadra entera; cada prueba mueve **un** número y
comprueba que salta **esa** regla.

Que cuadre entera importa: si el punto de partida ya tuviera una queja, ninguna
prueba distinguiría entre la queja nueva y la que ya estaba.
"""

from datetime import date

import pytest

from validador import facturae, factura
from validador.formato import detectar
from validador.incidencias import AVISO, ERROR

HOY = date(2026, 9, 20)
NIF = "B12345674"

# Las cuentas de la factura de prueba, para que se puedan seguir a mano:
#
#   línea 1: 2 x 100,00 = 200,00 - 10% (20,00) + 5% (10,00) = 190,00
#   línea 2: 1 x  10,00 =  10,00                            =  10,00
#   bruto total .................................  200,00
#   - descuento general 10% ......................  20,00
#   + recargo general    5% ......................  10,00
#   base antes de impuestos ......................  190,00
#   IVA 21% .. 39,90   + recargo de equivalencia 5,2% .. 9,88  => 49,78
#   IRPF 15% ..................................... -28,50
#   total factura ................................  211,28
#   - subvención 10,00 - anticipo 1,28 ...........  200,00 a pagar
#   - retenido 5,00 - especie 3,00 + suplidos 7,00 + financieros 1,00
#   total a ejecutar .............................  200,00
PLANTILLA = """<?xml version="1.0" encoding="UTF-8"?>
<fe:Facturae xmlns:fe="http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml">
  <FileHeader>
    <SchemaVersion>3.2.2</SchemaVersion>
    <Modality>{modalidad}</Modality>
    <InvoiceIssuerType>EM</InvoiceIssuerType>
    <Batch>
      <BatchIdentifier>{nif}F-001</BatchIdentifier>
      <InvoicesCount>{cuantas}</InvoicesCount>
      <TotalInvoicesAmount><TotalAmount>{lote_total}</TotalAmount></TotalInvoicesAmount>
      <TotalOutstandingAmount><TotalAmount>{lote_pagar}</TotalAmount></TotalOutstandingAmount>
      <TotalExecutableAmount><TotalAmount>{lote_ejecutar}</TotalAmount></TotalExecutableAmount>
      <InvoiceCurrencyCode>EUR</InvoiceCurrencyCode>
    </Batch>
  </FileHeader>
  <Parties>
    <SellerParty><TaxIdentification>
      <PersonTypeCode>J</PersonTypeCode>
      <ResidenceTypeCode>R</ResidenceTypeCode>
      <TaxIdentificationNumber>{nif}</TaxIdentificationNumber>
    </TaxIdentification></SellerParty>
    <BuyerParty><TaxIdentification>
      <PersonTypeCode>J</PersonTypeCode>
      <ResidenceTypeCode>R</ResidenceTypeCode>
      <TaxIdentificationNumber>{nif}</TaxIdentificationNumber>
    </TaxIdentification></BuyerParty>
  </Parties>
  <Invoices>{facturas}</Invoices>
</fe:Facturae>"""

UNA_FACTURA = """
    <Invoice>
      <InvoiceHeader>
        <InvoiceNumber>{numero}</InvoiceNumber>
        <InvoiceSeriesCode>A</InvoiceSeriesCode>
        <InvoiceDocumentType>FC</InvoiceDocumentType>
        <InvoiceClass>OO</InvoiceClass>
      </InvoiceHeader>
      <InvoiceIssueData>
        <IssueDate>2026-03-02</IssueDate>
        <InvoiceCurrencyCode>EUR</InvoiceCurrencyCode>
        <TaxCurrencyCode>EUR</TaxCurrencyCode>
        <LanguageName>es</LanguageName>
      </InvoiceIssueData>
      <TaxesOutputs><Tax>
        <TaxTypeCode>{cod_iva}</TaxTypeCode>
        <TaxRate>{tipo_iva}</TaxRate>
        <TaxableBase><TotalAmount>{base_iva}</TotalAmount></TaxableBase>
        <TaxAmount><TotalAmount>{cuota_iva}</TotalAmount></TaxAmount>
        <EquivalenceSurcharge>5.20</EquivalenceSurcharge>
        <EquivalenceSurchargeAmount><TotalAmount>{recargo}</TotalAmount>
        </EquivalenceSurchargeAmount>
      </Tax>{iva_extra}</TaxesOutputs>
      <TaxesWithheld><Tax>
        <TaxTypeCode>04</TaxTypeCode>
        <TaxRate>15.00</TaxRate>
        <TaxableBase><TotalAmount>190.00</TotalAmount></TaxableBase>
        <TaxAmount><TotalAmount>{cuota_irpf}</TotalAmount></TaxAmount>
      </Tax></TaxesWithheld>
      <InvoiceTotals>
        <TotalGrossAmount>{bruto_total}</TotalGrossAmount>
        <GeneralDiscounts><Discount>
          <DiscountReason>Fidelidad</DiscountReason>
          <DiscountRate>10.0000</DiscountRate>
          <DiscountAmount>{desc_general}</DiscountAmount>
        </Discount></GeneralDiscounts>
        <GeneralSurcharges><Charge>
          <ChargeReason>Portes</ChargeReason>
          <ChargeRate>5.0000</ChargeRate>
          <ChargeAmount>10.00</ChargeAmount>
        </Charge></GeneralSurcharges>
        <TotalGeneralDiscounts>{total_desc}</TotalGeneralDiscounts>
        <TotalGeneralSurcharges>10.00</TotalGeneralSurcharges>
        <TotalGrossAmountBeforeTaxes>{base}</TotalGrossAmountBeforeTaxes>
        <TotalTaxOutputs>{repercutidos}</TotalTaxOutputs>
        <TotalTaxesWithheld>{retenidos}</TotalTaxesWithheld>
        <InvoiceTotal>{total}</InvoiceTotal>
        <Subsidies><Subsidy>
          <SubsidyDescription>Plan de ayudas</SubsidyDescription>
          <SubsidyAmount>10.00</SubsidyAmount>
        </Subsidy></Subsidies>
        <PaymentsOnAccount><PaymentOnAccount>
          <PaymentOnAccountDate>2026-02-01</PaymentOnAccountDate>
          <PaymentOnAccountAmount>1.28</PaymentOnAccountAmount>
        </PaymentOnAccount></PaymentsOnAccount>
        <TotalFinancialExpenses>1.00</TotalFinancialExpenses>
        <TotalOutstandingAmount>{pagar}</TotalOutstandingAmount>
        <TotalPaymentsOnAccount>{total_anticipos}</TotalPaymentsOnAccount>
        <AmountsWithheld>
          <WithholdingReason>Garantia</WithholdingReason>
          <WithholdingAmount>5.00</WithholdingAmount>
        </AmountsWithheld>
        <TotalExecutableAmount>{ejecutar}</TotalExecutableAmount>
        <TotalReimbursableExpenses>7.00</TotalReimbursableExpenses>
        <PaymentInKind>
          <PaymentInKindReason>Material</PaymentInKindReason>
          <PaymentInKindAmount>3.00</PaymentInKindAmount>
        </PaymentInKind>
      </InvoiceTotals>
      <Items>
        <InvoiceLine>
          <ItemDescription>Servicio</ItemDescription>
          <Quantity>{cantidad}</Quantity>
          <UnitPriceWithoutTax>100.00</UnitPriceWithoutTax>
          <TotalCost>{coste}</TotalCost>
          <DiscountsAndRebates><Discount>
            <DiscountReason>Volumen</DiscountReason>
            <DiscountRate>10.0000</DiscountRate>
            <DiscountAmount>{desc_linea}</DiscountAmount>
          </Discount></DiscountsAndRebates>
          <Charges><Charge>
            <ChargeReason>Urgencia</ChargeReason>
            <ChargeRate>5.0000</ChargeRate>
            <ChargeAmount>10.00</ChargeAmount>
          </Charge></Charges>
          <GrossAmount>{bruto_1}</GrossAmount>
          <TaxesOutputs><Tax>
            <TaxTypeCode>01</TaxTypeCode>
            <TaxRate>21.00</TaxRate>
            <TaxableBase><TotalAmount>{base_linea_1}</TotalAmount></TaxableBase>
            <TaxAmount><TotalAmount>39.90</TotalAmount></TaxAmount>
          </Tax></TaxesOutputs>
        </InvoiceLine>
        <InvoiceLine>
          <ItemDescription>Portes</ItemDescription>
          <Quantity>1.00</Quantity>
          <UnitPriceWithoutTax>10.00</UnitPriceWithoutTax>
          <TotalCost>10.00</TotalCost>
          <GrossAmount>10.00</GrossAmount>
          <TaxesOutputs><Tax>
            <TaxTypeCode>01</TaxTypeCode>
            <TaxRate>21.00</TaxRate>
            <TaxableBase><TotalAmount>10.00</TotalAmount></TaxableBase>
            <TaxAmount><TotalAmount>2.10</TotalAmount></TaxAmount>
          </Tax></TaxesOutputs>
        </InvoiceLine>
      </Items>
    </Invoice>"""

CORRECTA = {
    "nif": NIF,
    "modalidad": "I",
    "cuantas": "1",
    "lote_total": "211.28",
    "lote_pagar": "200.00",
    "lote_ejecutar": "200.00",
    "numero": "F-001",
    "cod_iva": "01",
    "tipo_iva": "21.00",
    "base_iva": "190.00",
    "cuota_iva": "39.90",
    "recargo": "9.88",
    "iva_extra": "",
    "cuota_irpf": "28.50",
    "bruto_total": "200.00",
    "desc_general": "20.00",
    "total_desc": "20.00",
    "base": "190.00",
    "repercutidos": "49.78",
    "retenidos": "28.50",
    "total": "211.28",
    "total_anticipos": "1.28",
    "pagar": "200.00",
    "ejecutar": "200.00",
    "cantidad": "2.00",
    "coste": "200.00",
    "desc_linea": "20.00",
    "bruto_1": "190.00",
    "base_linea_1": "190.00",
}


def fe(**cambios) -> str:
    """La factura de prueba, con los números que se le pidan cambiados."""
    valores = {**CORRECTA, **cambios}
    numeros = [valores["numero"]] + list(cambios.pop("mas_facturas", []))
    facturas = "".join(
        UNA_FACTURA.format(**{**valores, "numero": numero}) for numero in numeros
    )
    return PLANTILLA.format(**valores, facturas=facturas)


def quejas(xml: str):
    """Las incidencias de Facturae sobre un documento, y solo esas."""
    return facturae.reglas(detectar_arbol(xml), detectar(xml))


def detectar_arbol(xml: str):
    from lxml import etree

    from validador.formato import parser

    return etree.fromstring(xml.encode("utf-8"), parser=parser())


# Un segundo impuesto repercutido sobre la misma base: 3% de IPSI, 5,70.
IPSI = """<Tax>
        <TaxTypeCode>02</TaxTypeCode>
        <TaxRate>3.00</TaxRate>
        <TaxableBase><TotalAmount>190.00</TotalAmount></TaxableBase>
        <TaxAmount><TotalAmount>5.70</TotalAmount></TaxAmount>
      </Tax>"""


def codigos(incidencias, gravedad=None) -> set[str]:
    return {i.codigo for i in incidencias if gravedad is None or i.gravedad == gravedad}


# --- El punto de partida ---------------------------------------------------


class TestUnaFacturaQueCuadra:
    def test_no_recibe_ninguna_queja(self):
        # Si esto falla, ninguna otra prueba de este fichero significa nada:
        # no se podria distinguir la queja nueva de la que ya estaba.
        assert quejas(fe()) == []

    def test_tampoco_con_dos_facturas_iguales_en_el_mismo_fichero(self):
        documento = fe(
            modalidad="L",
            cuantas="2",
            lote_total="422.56",
            lote_pagar="400.00",
            lote_ejecutar="400.00",
            mas_facturas=["F-002"],
        )
        assert quejas(documento) == []


# --- La cadena de totales --------------------------------------------------


class TestLaCadenaDeTotales:
    """Las fórmulas que el esquema escribe con «Resultado de:»."""

    def test_la_base_antes_de_impuestos(self):
        # 200 - 20 + 10 = 190, no 500.
        salta = [i for i in quejas(fe(base="500.00")) if i.codigo == "FE-BASE"]
        assert salta and salta[0].gravedad == ERROR
        assert "190,00" in salta[0].esperado

    def test_el_total_de_la_factura(self):
        assert "FE-TOTAL" in codigos(quejas(fe(total="999.99")), ERROR)

    def test_el_total_a_pagar(self):
        assert "FE-PENDIENTE" in codigos(quejas(fe(pagar="150.00")), ERROR)

    def test_el_total_a_ejecutar(self):
        # 200 - 5 retenido - 3 en especie + 7 de suplidos + 1 financiero = 200.
        salta = [i for i in quejas(fe(ejecutar="180.00")) if i.codigo == "FE-EJECUTAR"]
        assert salta and "200,00" in salta[0].esperado

    def test_el_total_general_de_descuentos(self):
        # El detallado sigue diciendo 20,00 y el total dice 35,00.
        assert "FE-DESCUENTOS" in codigos(quejas(fe(total_desc="35.00")), ERROR)

    def test_el_total_de_anticipos(self):
        assert "FE-ANTICIPOS" in codigos(quejas(fe(total_anticipos="9.00")), ERROR)

    def test_un_eslabon_roto_no_dispara_la_cadena_entera(self):
        """Cada fórmula se mide contra lo que la factura declara, no contra lo
        que hemos calculado nosotros.

        Si la base estuviera mal y cada eslabón partiera del anterior ya
        corregido, un solo dedazo daría cuatro quejas de totales y quien las
        recibe no sabría cuál arreglar.
        """
        de_totales = {
            i.codigo
            for i in quejas(fe(base="500.00"))
            if i.codigo in ("FE-BASE", "FE-TOTAL", "FE-PENDIENTE", "FE-EJECUTAR")
        }
        assert de_totales == {"FE-BASE", "FE-TOTAL"}


# --- Las líneas ------------------------------------------------------------


class TestLasLineas:
    def test_el_coste_es_cantidad_por_precio(self):
        salta = [i for i in quejas(fe(cantidad="3.00")) if i.codigo == "FE-LINEA-COSTE"]
        assert salta and salta[0].gravedad == ERROR
        assert "300,00" in salta[0].esperado

    def test_el_bruto_es_el_coste_menos_descuentos_mas_cargos(self):
        # 200 - 20 + 10 = 190, y la línea dice 175.
        salta = [i for i in quejas(fe(bruto_1="175.00")) if i.codigo == "FE-LINEA-BRUTO"]
        assert salta and "190,00" in salta[0].esperado

    def test_el_bruto_total_es_la_suma_de_las_lineas(self):
        salta = [i for i in quejas(fe(bruto_total="123.00")) if i.codigo == "FE-BRUTO"]
        assert salta and "200,00" in salta[0].esperado

    def test_la_queja_dice_en_que_linea_esta(self):
        """Con cincuenta líneas, «una línea no cuadra» no sirve de nada."""
        salta = [i for i in quejas(fe(cantidad="3.00")) if i.codigo == "FE-LINEA-COSTE"]
        assert "Línea 1" in salta[0].campo and "Servicio" in salta[0].campo

    def test_el_importe_de_un_descuento_frente_a_su_porcentaje(self):
        # 10% de 200 son 20, no 55.
        salta = [i for i in quejas(fe(desc_linea="55.00")) if i.codigo == "FE-AJUSTE"]
        assert salta and salta[0].gravedad == AVISO
        assert "Volumen" in salta[0].campo


# --- Los impuestos ---------------------------------------------------------


class TestLosImpuestos:
    def test_el_recargo_de_equivalencia_cuenta_en_el_total_repercutido(self):
        """«Sumatorio de todas Cuotas **y Recargos de Equivalencia**».

        Sin el recargo, la suma de esta factura daría 39,90 en vez de 49,78 y
        una factura correcta recibiría una queja de casi diez euros. Es la
        misma frase que se leyó mal una vez en `alphp_factura-prueba-v1-2-0`.
        """
        assert "FE-REPERCUTIDOS" not in codigos(quejas(fe()))
        assert "FE-REPERCUTIDOS" in codigos(quejas(fe(repercutidos="39.90")), ERROR)

    def test_el_total_de_retenciones(self):
        assert "FE-RETENIDOS" in codigos(quejas(fe(retenidos="10.00")), ERROR)

    def test_la_cuota_frente_al_tipo(self):
        salta = [i for i in quejas(fe(cuota_iva="1.00")) if i.codigo == "FE-CUOTA"]
        assert salta and "39,90" in salta[0].esperado

    def test_la_cuota_es_aviso_y_no_error(self):
        """A diferencia de BR-CO-17, que sí es error en UBL y en CII.

        No es un descuido: la norma europea manda que la cuota salga de aplicar
        el tipo a la base; el esquema de Facturae dice de su propio campo que
        «la legislación del impuesto correspondiente determina cómo se calcula
        la cuota». Si la fuente se abstiene, aquí no se sentencia.
        """
        salta = [i for i in quejas(fe(cuota_iva="1.00")) if i.codigo == "FE-CUOTA"]
        assert salta[0].gravedad == AVISO

    def test_no_se_le_mide_la_cuota_a_un_impuesto_que_no_va_por_porcentaje(self):
        """Los impuestos especiales se liquidan por litro o por kilo.

        Multiplicar su «tipo» por la base no significa nada, y el esquema avisa
        de que «no siempre son porcentajes».
        """
        roto = dict(tipo_iva="77.00")
        assert "FE-CUOTA" in codigos(quejas(fe(**roto)))
        assert "FE-CUOTA" not in codigos(quejas(fe(**roto, cod_iva="07")))

    def test_el_recargo_frente_a_su_porcentaje(self):
        salta = [i for i in quejas(fe(recargo="2.00")) if i.codigo == "FE-RECARGO"]
        assert salta and "9,88" in salta[0].esperado

    def test_dos_impuestos_sobre_la_misma_base_no_son_un_descuadre(self):
        """En Ceuta se factura con IPSI y en la Península con IVA, y hay
        facturas que declaran los dos sobre la misma base.

        Sumar todas las bases del desglose daría el doble de la base de la
        factura y acusaría de descuadre a una factura correcta. Pasa en
        `alphp_factura-prueba-v1-2-0.xml`, que es de verdad y está bien.
        """
        documento = fe(iva_extra=IPSI, repercutidos="55.48")
        assert "FE-SIN-GRAVAR" not in codigos(quejas(documento))
        assert "FE-REPERCUTIDOS" not in codigos(quejas(documento))


# --- Lo que se factura y no se grava ---------------------------------------


class TestLoQueSeFacturaYNoSeGrava:
    """El fallo que más dinero mueve y del que no decíamos nada.

    Dos de las nueve facturas oficiales de prueba lo tienen: 33,75 € en una y
    22,08 € en otra, facturados y sin base declarada.
    """

    def test_en_el_desglose_de_la_factura(self):
        salta = [i for i in quejas(fe(base_iva="100.00")) if i.codigo == "FE-SIN-GRAVAR"]
        assert salta and "90,00" in salta[0].mensaje

    def test_en_una_linea(self):
        salta = [
            i for i in quejas(fe(base_linea_1="0.00")) if i.codigo == "FE-LINEA-SIN-GRAVAR"
        ]
        assert salta and "190,00" in salta[0].mensaje

    def test_va_como_aviso(self):
        """El esquema no lo escribe como fórmula, y hay regímenes —agencias de
        viajes, grupo de entidades— donde la base del impuesto no es el importe
        facturado. Se dice, pero no se sentencia.
        """
        salta = [i for i in quejas(fe(base_iva="100.00")) if i.codigo == "FE-SIN-GRAVAR"]
        assert salta[0].gravedad == AVISO


# --- La cabecera del fichero -----------------------------------------------


class TestElLote:
    def test_la_cuenta_de_facturas(self):
        salta = [i for i in quejas(fe(cuantas="7")) if i.codigo == "FE-LOTE-CUENTA"]
        assert salta and salta[0].esperado.startswith("1,")

    def test_el_total_del_fichero(self):
        assert "FE-LOTE-TOTAL" in codigos(quejas(fe(lote_total="1.00")), ERROR)

    def test_individual_con_varias_facturas_dentro(self):
        documento = fe(
            modalidad="I",
            cuantas="2",
            lote_total="422.56",
            lote_pagar="400.00",
            lote_ejecutar="400.00",
            mas_facturas=["F-002"],
        )
        assert "FE-MODALIDAD" in codigos(quejas(documento), ERROR)

    def test_con_varias_facturas_cada_queja_dice_de_cual(self):
        documento = fe(
            modalidad="L",
            cuantas="2",
            lote_total="422.56",
            lote_pagar="400.00",
            lote_ejecutar="400.00",
            total="999.99",
            mas_facturas=["F-002"],
        )
        de_total = [i for i in quejas(documento) if i.codigo == "FE-TOTAL"]
        assert len(de_total) == 2
        assert all("Factura A" in i.campo for i in de_total)

    def test_con_una_sola_no_se_repite_el_numero_en_cada_queja(self):
        """Sobra decir «Factura AF-001» en cada línea de un fichero que no
        tiene otra: alarga el informe y no desambigua nada."""
        salta = [i for i in quejas(fe(total="999.99")) if i.codigo == "FE-TOTAL"]
        assert salta[0].campo == "Total factura"


# --- A qué documentos se les aplica ----------------------------------------


class TestAQueDocumentosSeLesAplica:
    def test_a_un_ubl_no(self):
        ubl = (
            '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">'
            "</Invoice>"
        )
        assert quejas(ubl) == []

    def test_a_un_facturae_metido_dentro_de_una_firma_si(self):
        """Firma XAdES «enveloping»: la raíz es la firma y la factura cuelga de
        dentro. Sin desenvolverlo aquí, las rutas relativas no encontrarían un
        solo elemento y el fichero saldría sin una queja —que es peor que
        fallar, porque parece que está bien.
        """
        dentro = fe(total="999.99").split("?>", 1)[1]
        firmado = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">'
            f"<ds:Object>{dentro}</ds:Object></ds:Signature>"
        )
        assert "FE-TOTAL" in codigos(quejas(firmado), ERROR)


# --- Cuánto se puede desviar una suma --------------------------------------


class TestLaTolerancia:
    def test_tres_cuotas_redondeadas_no_son_un_descuadre(self):
        """Cada cifra escrita está redondeada, así que al sumarlas los medios
        céntimos se acumulan.

        `alphp_factura-prueba-v1-2-0.xml`, que es correcta, suma tres cuotas
        —34,91 + 34,91 + 209,43 = 279,25— y declara 279,24. Con la tolerancia
        fija de un céntimo se salvaba por el pelo; con una cuota más, no.
        """
        # Aquí: 39,90 + 9,88 de recargo + 5,70 de IPSI = 55,48, y se declaran
        # 55,46. Dos céntimos, que es justo el máximo legítimo de tres cifras
        # redondeadas más el total —y que con la tolerancia fija de un céntimo
        # se rechazaría. Con 55,47 esta prueba no distinguiría nada: un céntimo
        # lo perdona también la tolerancia fija.
        assert "FE-REPERCUTIDOS" not in codigos(
            quejas(fe(iva_extra=IPSI, repercutidos="55.46"))
        )

    def test_pero_un_descuadre_de_verdad_sigue_saltando(self):
        assert "FE-REPERCUTIDOS" in codigos(quejas(fe(repercutidos="45.00")), ERROR)

    def test_y_el_primer_centimo_de_mas_tambien(self):
        """La holgura tiene un límite, y está donde acaba el redondeo."""
        assert "FE-REPERCUTIDOS" in codigos(
            quejas(fe(iva_extra=IPSI, repercutidos="55.45")), ERROR
        )


# --- En el orquestador -----------------------------------------------------


class TestEnElOrquestador:
    def test_una_factura_facturae_rota_se_queja(self):
        informe = factura.validar(fe(total="999.99"), hoy=HOY)
        assert "FE-TOTAL" in codigos(informe.incidencias, ERROR)
        assert not informe.conforme

    def test_ya_no_dice_que_no_se_ha_validado(self):
        """Antes, un Facturae recibía un aviso SIN-SOPORTE diciendo que «solo
        se ha identificado, no validado», y a la vez el resumen decía «sin
        errores». Las dos cosas eran verdad a medias y juntas engañaban.
        """
        informe = factura.validar(fe(), hoy=HOY)
        assert "SIN-SOPORTE" not in codigos(informe.incidencias)

    def test_la_queja_dice_de_donde_sale(self):
        informe = factura.validar(fe(total="999.99"), hoy=HOY)
        salta = [i for i in informe.incidencias if i.codigo == "FE-TOTAL"][0]
        # En mayúscula desde que la etiqueta es una sola y la usan los dos
        # sitios: en la ficha de la página es un título.
        assert factura.origen(salta) == "Formato Facturae"


# --- Las ramas gemelas que nadie provocaba ---------------------------------
#
# Las cuatro de aquí salieron el 06-09-2026 del guardián nuevo de
# `test_inventario.py`, que compara el catálogo de códigos publicado con lo
# que alguna prueba nombra. Tres son la otra mitad de una tabla que sí estaba
# probada —los descuentos sí y los cargos no, el total del fichero sí y el
# pendiente y el ejecutable no—, que es el sitio exacto donde se cuela una
# errata: la rama probada tapa a la que no lo está.


class TestLasRamasQueFaltaban:
    def test_el_total_general_de_cargos(self):
        """El gemelo de `FE-DESCUENTOS`, que sí tenía prueba desde el principio."""
        roto = fe().replace(
            "<TotalGeneralSurcharges>10.00", "<TotalGeneralSurcharges>99.00")
        salta = [i for i in quejas(roto) if i.codigo == "FE-CARGOS"]
        assert salta and salta[0].gravedad == ERROR
        assert "10,00" in salta[0].esperado

    def test_el_total_a_pagar_del_fichero(self):
        salta = [i for i in quejas(fe(lote_pagar="1.00"))
                 if i.codigo == "FE-LOTE-PENDIENTE"]
        assert salta and salta[0].gravedad == ERROR

    def test_el_total_a_ejecutar_del_fichero(self):
        salta = [i for i in quejas(fe(lote_ejecutar="1.00"))
                 if i.codigo == "FE-LOTE-EJECUTAR"]
        assert salta and salta[0].gravedad == ERROR


class TestLosPaisesQueISORetiro:
    """`ANT` y `ZAR`: Facturae los admite y la lista ISO vigente no los tiene.

    No se traducen a propósito —convertir `ZAR` en `CD` sería decidir qué
    quiso decir quien lo escribió—, así que el dato no puede viajar a
    EN 16931 y de eso hay que enterarse en vez de que desaparezca callando.
    """

    def _con_pais(self, codigo: str) -> str:
        return fe().replace(
            "</TaxIdentification></SellerParty>",
            "</TaxIdentification><LegalEntity><AddressInSpain>"
            f"<CountryCode>{codigo}</CountryCode></AddressInSpain>"
            "</LegalEntity></SellerParty>")

    def test_un_pais_retirado_sale_como_aviso(self):
        salta = [i for i in quejas(self._con_pais("ZAR"))
                 if i.codigo == "FE-PAIS-RETIRADO"]
        assert salta and salta[0].gravedad == AVISO
        assert salta[0].encontrado == "ZAR"
        assert "Zaire" in salta[0].mensaje

    def test_y_el_otro_tambien(self):
        salta = [i for i in quejas(self._con_pais("ANT"))
                 if i.codigo == "FE-PAIS-RETIRADO"]
        assert salta and "Antillas" in salta[0].mensaje

    def test_un_pais_normal_no_dice_nada(self):
        assert "FE-PAIS-RETIRADO" not in codigos(quejas(self._con_pais("ESP")))
        assert "FE-PAIS-RETIRADO" not in codigos(quejas(self._con_pais("FRA")))

    def test_de_un_pais_que_no_existe_se_queja_el_esquema_y_no_esto(self):
        """Aquí solo caben los dos retirados. `XYZ` no es un país retirado:
        es un país que no existe, y de eso se queja el XSD con mejor consejo.
        """
        assert "FE-PAIS-RETIRADO" not in codigos(quejas(self._con_pais("XYZ")))
