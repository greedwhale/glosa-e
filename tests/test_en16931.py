"""Comprobaciones de las reglas de negocio EN 16931."""

from dataclasses import replace
from decimal import Decimal

import pytest
from lxml import etree

from validador import en16931
from validador.en16931 import AVISO, ERROR, NOTA
from validador.formato import Deteccion


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
        else f"""<cac:Item><cbc:Name>Concepto</cbc:Name><cac:ClassifiedTaxCategory>
          <cbc:ID>{categoria}</cbc:ID><cbc:Percent>{tipo_iva}</cbc:Percent>
        </cac:ClassifiedTaxCategory></cac:Item>"""
    )

    # Cantidad, unidad y precio unitario: BT-129, BT-130 y BT-146, que EN 16931
    # exige en toda línea por BR-22, BR-23 y BR-26. Van con su propio interruptor
    # en `omitir` para poder quitarlos de uno en uno y ver saltar **esa** regla.
    def linea_cantidad():
        if "InvoicedQuantity" in omitir:
            return ""
        unidad = "" if "unitCode" in omitir else ' unitCode="EA"'
        return f"<cbc:InvoicedQuantity{unidad}>1</cbc:InvoicedQuantity>"

    precio = (
        ""
        if "Price" in omitir
        else '<cac:Price><cbc:PriceAmount currencyID="EUR">100.00'
        "</cbc:PriceAmount></cac:Price>"
    )

    xml_lineas = "".join(
        f"""<cac:InvoiceLine><cbc:ID>{ident}</cbc:ID>
        {linea_cantidad()}
        {'' if 'LineExtensionAmount' in omitir else
         f'<cbc:LineExtensionAmount currencyID="EUR">{importe}</cbc:LineExtensionAmount>'}
        {iva_de_linea}
        {precio}
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
        # La cantidad también cambia de nombre, como las líneas y el tipo. Sin
        # esto el abono llevaría `InvoicedQuantity`, que no es lo que escribe
        # un abono de verdad, y la mitad del mapa —la rama `CreditedQuantity`
        # de BR-22 y BR-23— no la probaría nadie.
        .replace("<cbc:InvoicedQuantity", "<cbc:CreditedQuantity")
        .replace("</cbc:InvoicedQuantity>", "</cbc:CreditedQuantity>")
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

    def test_linea_sin_cantidad_salta_br_22(self, documento):
        informe = en16931.validar(documento(omitir=("InvoicedQuantity",)))
        assert "BR-22" in codigos(informe, ERROR)

    def test_linea_sin_unidad_de_medida_salta_br_23(self, documento):
        """Y sobre el abono también, que es donde el mapa se rompía.

        BT-130 va en un atributo de la cantidad, y en un abono esa cantidad se
        llama `CreditedQuantity`. Con media unión en el mapa, BR-23 saldría en
        todos los abonos correctos y en ninguno de los defectuosos.
        """
        informe = en16931.validar(documento(omitir=("unitCode",)))
        assert "BR-23" in codigos(informe, ERROR)

    def test_linea_sin_precio_unitario_salta_br_26(self, documento):
        informe = en16931.validar(documento(omitir=("Price",)))
        assert "BR-26" in codigos(informe, ERROR)

    def test_una_queja_por_regla_y_no_una_por_linea(self, documento):
        """Cinco líneas sin unidad son un problema, no cinco.

        El informe lo lee alguien que tiene que arreglar la factura: lo que le
        sirve es «falta la unidad en las líneas 1 a 5», no cinco párrafos
        idénticos. El campo enumera cuáles, que es lo que hace falta.
        """
        cinco = tuple((str(n), "20.00") for n in range(1, 6))
        informe = en16931.validar(
            documento(lineas=cinco, suma_lineas="100.00", omitir=("unitCode",))
        )
        salieron = [i for i in informe.incidencias if i.codigo == "BR-23"]
        assert len(salieron) == 1
        assert "1, 2, 3, 4, 5" in salieron[0].campo

    def test_las_lineas_no_cuadran_con_el_total(self, documento):
        informe = en16931.validar(
            documento(lineas=(("1", "90.00"),), suma_lineas="100.00")
        )
        assert "BR-CO-10" in codigos(informe, ERROR), informe.detalle()

    def test_el_desglose_de_iva_se_comprueba(self, documento):
        # La base del desglose dice 150.00 y la línea son 100.00. Si no se
        # leen las líneas, esta regla calla y el error más caro pasa.
        informe = en16931.validar(documento(base_iva="150.00"))
        assert "BR-S-08" in codigos(informe, ERROR), informe.detalle()

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
        assert {"BR-06", "BR-08"} <= codigos(informe, ERROR)

    def test_falta_el_comprador(self):
        informe = en16931.validar(factura(omitir=("comprador",)))
        assert {"BR-07", "BR-10"} <= codigos(informe, ERROR)

    def test_sin_direccion_no_se_pide_ademas_el_pais(self):
        """BR-09 cuelga de la direccion del vendedor, no de la factura.

        En el esquematron normativo su contexto es la direccion postal: si no
        hay direccion, la norma dispara BR-08 y calla. Aqui salian las dos, y
        el informe contaba dos defectos donde habia uno, con el segundo ademas
        mal descrito: no es que a la direccion le falte el pais, es que no hay
        direccion. Misma familia de error que el BR-{X}-05 que se comprobaba
        sobre el desglose en vez de sobre la linea.
        """
        del_vendedor = codigos(en16931.validar(factura(omitir=("vendedor",))), ERROR)
        assert "BR-09" not in del_vendedor
        del_comprador = codigos(en16931.validar(factura(omitir=("comprador",))), ERROR)
        assert "BR-11" not in del_comprador

    def test_pero_con_direccion_y_sin_pais_si(self):
        """Que es el caso para el que la regla existe.

        Sin esta prueba, «no digas BR-09» se cumpliria borrando la regla.
        """
        # Se quita solo el codigo de pais: la direccion del vendedor sigue
        # ahi, que es lo que hace que BR-09 tenga contexto donde evaluarse.
        sin_pais = factura().replace(
            "<cbc:IdentificationCode>ES</cbc:IdentificationCode>", "", 1
        )
        informe = en16931.validar(sin_pais)
        assert "BR-09" in codigos(informe, ERROR)
        assert "BR-08" not in codigos(informe, ERROR)

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
    def test_un_centimo_de_diferencia_ya_es_error(self):
        """Aquí ponía «la norma trabaja con dos decimales: un céntimo es redondeo».

        La norma redondea **la suma** a dos decimales y la compara con lo
        declarado sin margen. 33,33 tres veces son 99,99, y una suma declarada
        de 100,00 incumple BR-CO-10. Se toleró durante meses; lo cazó la prueba
        oficial de BR-CO-10, que trae 200,01 contra 110 + 90.
        """
        informe = en16931.validar(
            factura(lineas=(("1", "33.33"), ("2", "33.33"), ("3", "33.33")),
                    suma_lineas="100.00", base="100.00",
                    impuestos="21.00", con_impuestos="121.00", a_pagar="121.00")
        )
        assert "BR-CO-10" in codigos(informe, ERROR), informe.detalle()

    def test_la_suma_se_redondea_antes_de_comparar(self):
        """Lo que sí se admite: tres decimales en las líneas que redondeados cuadran."""
        informe = en16931.validar(
            factura(lineas=(("1", "33.335"), ("2", "33.335"), ("3", "33.33")),
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


FACTURAE_UNA = open("ejemplos/fe-0001.xml", encoding="utf-8").read()


def _rectificativa(metodo: str | None = None) -> str:
    """`fe-0001.xml` convertida en rectificativa, con el método que se pida.

    Sin método se queda como estaba el caso de siempre: una `OR` que no dice
    cómo rectifica.
    """
    corrective = ""
    if metodo is not None:
        corrective = (
            "<Corrective>"
            "<InvoiceNumber>F-2026-0001</InvoiceNumber>"
            "<ReasonCode>01</ReasonCode>"
            "<ReasonDescription>Numero de la factura</ReasonDescription>"
            "<TaxPeriod><StartDate>2026-01-01</StartDate>"
            "<EndDate>2026-03-31</EndDate></TaxPeriod>"
            f"<CorrectionMethod>{metodo}</CorrectionMethod>"
            "<CorrectionMethodDescription>Da igual</CorrectionMethodDescription>"
            "</Corrective>"
        )
    return FACTURAE_UNA.replace(
        "<InvoiceClass>OO</InvoiceClass>",
        "<InvoiceClass>OR</InvoiceClass>" + corrective)

FACTURAE_DOS = """<?xml version="1.0" encoding="UTF-8"?>
<fe:Facturae xmlns:fe="http://www.facturae.es/Facturae/2009/v3.2/Facturae">
  <FileHeader><SchemaVersion>3.2</SchemaVersion></FileHeader>
  <Parties>
    <SellerParty><LegalEntity><CorporateName>Talleres Ejemplo SL</CorporateName>
      <AddressInSpain><Address>Calle Mayor 1</Address>
      <CountryCode>ESP</CountryCode></AddressInSpain></LegalEntity></SellerParty>
    <BuyerParty><LegalEntity><CorporateName>Clientes Ejemplo SL</CorporateName>
      <AddressInSpain><Address>Gran Via 2</Address>
      <CountryCode>ESP</CountryCode></AddressInSpain></LegalEntity></BuyerParty>
  </Parties>
  <Invoices>
    <Invoice>
      <InvoiceHeader><InvoiceSeriesCode>FE</InvoiceSeriesCode>
        <InvoiceNumber>0001</InvoiceNumber>
        <InvoiceDocumentType>FC</InvoiceDocumentType></InvoiceHeader>
      <InvoiceIssueData><IssueDate>2026-03-02</IssueDate>
        <InvoiceCurrencyCode>EUR</InvoiceCurrencyCode></InvoiceIssueData>
    </Invoice>
    <Invoice>
      <InvoiceHeader><InvoiceSeriesCode>FE</InvoiceSeriesCode>
        <InvoiceNumber>0002</InvoiceNumber>
        <InvoiceDocumentType>FC</InvoiceDocumentType></InvoiceHeader>
      <InvoiceIssueData><IssueDate>2026-03-02</IssueDate>
        <InvoiceCurrencyCode>EUR</InvoiceCurrencyCode></InvoiceIssueData>
    </Invoice>
  </Invoices>
</fe:Facturae>"""


class TestBindingDeFacturae:
    """El mapa de Facturae, que no lo publica CEN y está escrito aquí.

    Existe desde el 06-09-2026, cuando el artículo 7.1 del RD 238/2026 pasó a
    exigirle a Facturae el modelo semántico EN 16931 como a las otras tres
    sintaxis. Lo que se prueba aquí no es que las reglas funcionen —de eso ya
    se encargan las clases de arriba, y las reglas son las mismas— sino que
    **los huecos del mapa se comportan como huecos** y no como acusaciones.
    """

    def test_un_hueco_del_mapa_no_acusa_a_la_factura(self):
        """BR-01 sobre Facturae es una NOTA, y esto es lo que sostiene todo.

        EN 16931 exige un identificador de especificación (BT-24). Facturae no
        tiene ese campo: lo más parecido es `SchemaVersion`, que dice qué
        versión del esquema es y no a qué norma se ajusta. Aplicando la regla
        en estricto suspenderían **todas** las facturas de España, siempre, y
        no por estar mal hechas.

        Si esto vuelve a salir como error, el validador está acusando a quien
        emitió el documento de algo que el formato no le deja hacer.
        """
        informe = en16931.validar(FACTURAE_UNA)
        br01 = [i for i in informe.incidencias if i.codigo == "BR-01"]
        assert br01, "BR-01 tiene que constar, aunque sea para decir que no aplica"
        assert br01[0].gravedad == NOTA
        assert "No es un defecto del documento" in br01[0].mensaje
        assert not [i for i in informe.incidencias if i.gravedad == ERROR]

    def test_la_categoria_de_iva_a_tipo_positivo_se_deduce(self):
        """Desde el 06-09-2026 ya no se calla: se deduce lo que se puede.

        Antes, Facturae no tenía categoría UNCL5305 y todas las reglas que
        dependen de ella se callaban en toda factura española. `TaxTypeCode`
        contesta a otra pregunta —qué impuesto es—, pero con IVA a tipo
        positivo solo hay una lectura posible: operación sujeta y no exenta,
        que es la S. Así que las BR-S-* corren de verdad.
        """
        informe = en16931.validar(FACTURAE_UNA)
        assert not [i for i in informe.incidencias
                    if i.codigo == "IVA-CATEGORIA-SIN-MAPA"], (
            "ya no debe salir: la categoría se deduce")
        assert not [i for i in informe.incidencias if i.codigo == "BR-47"]

    def test_a_tipo_cero_no_se_deduce_y_se_dice(self):
        """Lo que la deducción no alcanza, dicho una vez y como nota.

        Un cero en Facturae puede ser exenta, no sujeta, intracomunitaria,
        exportación o inversión del sujeto pasivo, y el formato no tiene
        ningún campo donde se haya escrito cuál. Inventar la más probable y
        presentarla como leída es justo lo que aquí no se hace.
        """
        a_cero = (FACTURAE_UNA
                  .replace("<TaxRate>21.00</TaxRate>", "<TaxRate>0.00</TaxRate>")
                  .replace("<TotalAmount>21.00</TotalAmount>",
                           "<TotalAmount>0.00</TotalAmount>"))
        informe = en16931.validar(a_cero)
        notas = [i for i in informe.incidencias
                 if i.codigo == "IVA-CATEGORIA-A-CERO"]
        assert len(notas) == 1, "una vez por documento, no una por entrada"
        assert notas[0].gravedad == NOTA

    def test_las_reglas_europeas_muerden_de_verdad(self):
        """Un mapa que solo sabe decir «conforme» no está probado.

        Cada rotura de aquí es un defecto que la norma tiene que ver. Se
        comprueba una por una y no todas juntas: si se rompieran a la vez, una
        regla muda pasaría desapercibida detrás de las que sí hablan.
        """
        # Las roturas tienen que dejar el XML **bien formado**, o el validador
        # se queja de la sintaxis y no llega a las reglas. Por eso las líneas
        # no se borran a medias: se les cambia el nombre al elemento entero, y
        # así siguen ahí pero ya no son líneas de factura.
        roturas = {
            "BR-03": [("<IssueDate>2026-03-02</IssueDate>", "")],
            "BR-07": [("<CorporateName>Clientes Ejemplo SL</CorporateName>", "")],
            "BR-16": [("<InvoiceLine>", "<Otra>"), ("</InvoiceLine>", "</Otra>")],
            # La suma de líneas sí se lee (BT-106 = `TotalGrossAmount`), así
            # que la aritmética de línea se comprueba entera. Los totales del
            # documento no: ver el test de abajo.
            "BR-CO-10": [("<TotalGrossAmount>100.00</TotalGrossAmount>",
                          "<TotalGrossAmount>555.00</TotalGrossAmount>")],
        }
        for codigo, cambios in roturas.items():
            roto = FACTURAE_UNA
            for busca, pon in cambios:
                roto = roto.replace(busca, pon)
            assert roto != FACTURAE_UNA, f"la rotura de {codigo} no cambió nada"
            informe = en16931.validar(roto)
            salieron = {i.codigo for i in informe.incidencias if i.gravedad == ERROR}
            assert codigo in salieron, f"{codigo} no saltó; salieron {salieron}"

    def test_los_totales_de_facturae_no_son_los_de_la_norma(self):
        """BT-110 y BT-112 son huecos, y hay que probar **por qué** lo son.

        Facturae carga impuestos que el modelo básico de EN 16931 no modela:
        su `InvoiceTotal` resta las retenciones, y su `TotalTaxOutputs` suma el
        recargo de equivalencia. Los importes se llaman igual y miden cosas
        distintas.

        Medido sobre las 13 Facturae reales que hay a mano: con el mapa directo
        salían 6 acusadas de incumplir BR-CO-15 y 4 de incumplir BR-CO-14, y
        **las diez eran correctas**. Una al céntimo: 1.163,52 + 279,24 =
        1.442,76, menos 58,18 de retención, da los 1.384,58 que escribe.

        Este test existe para que nadie las vuelva a conectar mirando solo que
        el nombre encaje. Si alguna vez se conectan bien —traduciendo, no
        igualando— este test es el que hay que reescribir, y su historia es la
        razón por la que no es tan fácil como parece.
        """
        con_retencion = FACTURAE_UNA.replace(
            "<TotalTaxesWithheld>0.00</TotalTaxesWithheld>",
            "<TotalTaxesWithheld>15.00</TotalTaxesWithheld>",
        )
        assert con_retencion != FACTURAE_UNA
        informe = en16931.validar(con_retencion)
        errores = {i.codigo for i in informe.incidencias if i.gravedad == ERROR}
        assert "BR-CO-15" not in errores, informe.detalle()
        assert "BR-CO-14" not in errores, informe.detalle()
        # Y consta que no se comprobó, que es la otra mitad del trato.
        notas = {i.codigo for i in informe.incidencias if i.gravedad == NOTA}
        assert "BR-14" in notas

    def test_la_unidad_de_medida_es_la_divergencia_que_justifica_esto(self):
        """BR-23 sobre Facturae: opcional en el formato, obligatoria en la norma.

        Es el caso limpio de lo que este binding aporta y el XSD no. `UnitOfMeasure`
        lleva `minOccurs="0"` en el esquema oficial, así que una factura sin
        unidad de medida **pasa el XSD, pasa las reglas de `facturae.py`, y no
        cumple EN 16931**, que es lo que le exige el artículo 7.1.

        Aquí no hay hueco de sintaxis que declarar: el campo existe y se lee.
        Que falte es un defecto del documento, así que BR-23 acusa y hace bien.
        """
        sin_unidad = FACTURAE_UNA.replace(
            "<UnitOfMeasure>01</UnitOfMeasure>", ""
        )
        assert sin_unidad != FACTURAE_UNA
        informe = en16931.validar(sin_unidad)
        assert "BR-23" in {
            i.codigo for i in informe.incidencias if i.gravedad == ERROR
        }, informe.detalle()

    def test_un_hueco_de_linea_tampoco_acusa(self):
        """La misma regla que en cabecera, un piso más abajo.

        Hoy las cuatro sintaxis saben leer las tres, así que esta rama no la
        ejerce ningún fichero real. Se prueba con un mapa fabricado a mano
        porque el día que entre una sintaxis con el hueco, lo que no puede
        pasar es que acuse: sería el mismo fallo de BR-01 con otro número.
        """
        mudo = replace(en16931.SINTAXIS_FACTURAE, linea_unidad=en16931.SIN_MAPA)
        raiz = etree.fromstring(FACTURAE_UNA.encode())
        factura_uno = raiz.xpath("./Invoices/Invoice")[0]
        salieron = en16931._reglas_campos_de_linea(factura_uno, mudo)
        br23 = [i for i in salieron if i.codigo == "BR-23"]
        assert len(br23) == 1
        assert br23[0].gravedad == NOTA
        assert "No es un defecto del documento" in br23[0].mensaje

    def test_con_varias_facturas_el_informe_dice_de_cual(self):
        """Un fichero Facturae es un lote, y sin decir cuál no se arregla nada.

        Las reglas se evalúan una vez por factura. Sin la etiqueta, un informe
        de un lote de cinco diría cinco veces «falta la moneda» sin decir a
        cuál de las cinco le falta.
        """
        informe = en16931.validar(FACTURAE_DOS)
        campos = [i.campo or "" for i in informe.incidencias]
        assert any("Factura FE0001 ·" in c for c in campos), campos
        assert any("Factura FE0002 ·" in c for c in campos), campos

    def test_con_una_sola_factura_no_se_repite_su_nombre(self):
        """Sobra decir «Factura FE0001» en cada queja de un fichero con una."""
        informe = en16931.validar(FACTURAE_UNA)
        assert not [i for i in informe.incidencias if "Factura FE" in (i.campo or "")]

    def test_un_lote_sin_facturas_no_dice_nada(self):
        """Sin `<Invoices>` no hay nada que validar, y callarse es lo correcto.

        Antes este caso probaba otra cosa —que Facturae se lo quedaba entero su
        propio módulo— y pasaba por el mismo camino. Ahora pasa por otro y hay
        que dejarlo dicho, porque el resultado es el mismo y eso esconde de
        cuál de los dos motivos viene.
        """
        xml = """<?xml version="1.0"?>
<fe:Facturae xmlns:fe="http://www.facturae.es/Facturae/2009/v3.2/Facturae">
  <FileHeader><SchemaVersion>3.2</SchemaVersion></FileHeader>
</fe:Facturae>"""
        assert en16931.validar(xml).incidencias == []


def solo_sin_soporte(deteccion):
    """El unico SIN-SOPORTE de un documento que no se ha podido leer."""
    avisos = [
        i for i in en16931.reglas(None, deteccion) if i.codigo == "SIN-SOPORTE"
    ]
    assert len(avisos) == 1, f"salen {len(avisos)} y tenia que salir uno"
    return avisos[0]


class TestOtrosFormatos:

    def test_un_edifact_ilegible_si_lo_dice(self):
        """Lo que de verdad no se puede leer se sigue diciendo.

        `SIN-SOPORTE` dejó de salir sobre EDIFACT el día que EDIFACT se pudo
        validar, pero no se ha quedado sin uso: sigue siendo lo que se
        contesta cuando el fichero no da ni para montar un árbol.
        """
        datos = b"UNB+UNOC:3+A+B'UNH+1+INVOIC:D:96A:UN"
        aviso = [i for i in en16931.validar(datos).avisos if i.codigo == "SIN-SOPORTE"]
        assert aviso and "solo se ha identificado" in aviso[0].mensaje

    def test_a_un_formato_implementado_no_se_le_dice_que_no_lo_esta(self):
        """El aviso decia «implementadas para UBL y para CII» sobre un Facturae.

        Dos cosas falsas en la misma frase: Facturae esta implementado desde
        hace meses, y el motivo de que esta vez no se haya validado no es el
        formato sino que el fichero no se ha podido leer. Quien leyera eso se
        pondria a buscar un validador de Facturae teniendo uno delante.
        """
        aviso = solo_sin_soporte(Deteccion(familia="Facturae"))
        assert "no se ha podido leer" in aviso.mensaje
        assert "UBL" not in aviso.mensaje

    def test_la_lista_de_sintaxis_implementadas_sale_del_mapa(self):
        """Escrita a mano envejece sola, que es el fallo de siempre aqui."""
        aviso = solo_sin_soporte(Deteccion(familia="Cualquiera"))
        for nombre in en16931.SINTAXIS:
            assert nombre in aviso.mensaje, f"{nombre} esta y no se nombra"

    def test_documento_irreconocible(self):
        informe = en16931.validar(b"<pedido/>")
        assert not informe.deteccion
        assert "No se ha podido validar" in informe.resumen()

    def test_sin_declarar_en16931_avisa(self):
        informe = en16931.validar(factura(perfil="urn:otra:cosa"))
        avisos = [i for i in informe.avisos if i.codigo == "PERFIL-SIN-EN16931"]
        assert avisos
        assert "urn:otra:cosa" in avisos[0].encontrado

    def test_br01_no_opina_de_lo_que_dice_el_campo(self):
        """BR-01 pide que el identificador esté; la prueba oficial acepta un «123»."""
        informe = en16931.validar(factura(perfil="123"))
        assert "BR-01" not in codigos(informe)


# --- BT-3, el tipo de documento --------------------------------------------


class TestElTipoDeDocumento:
    """BR-CL-01 y su hermana de Facturae, provocadas.

    Las dos entraron el 05-09-2026 con el binding de Facturae y ninguna prueba
    las nombraba por su código: se comprobaba el valor que salía de la
    traducción, no la queja. Lo delató el guardián del catálogo el día
    siguiente, y la diferencia importa —un código mal escrito habría pasado
    igual, y ese código es lo que se publica y lo que se busca—.
    """

    def test_un_tipo_que_no_esta_en_la_lista_de_la_norma(self):
        """`220` es «pedido» en UNTDID 1001, y aparece de verdad.

        Sobre 157 facturas ajenas salta una: un EDIFACT cuyo BGM declara 220.
        No es un capricho de laboratorio.
        """
        roto = factura().replace(
            "<cbc:InvoiceTypeCode>380", "<cbc:InvoiceTypeCode>220")
        salta = [i for i in en16931.validar(roto).incidencias
                 if i.codigo == "BR-CL-01"]
        assert salta and salta[0].gravedad == ERROR
        assert salta[0].encontrado == "220"
        assert "UNTDID 1001" in salta[0].mensaje

    def test_una_factura_normal_no_dice_nada(self):
        assert "BR-CL-01" not in codigos(en16931.validar(factura()))

    def test_una_rectificativa_sin_metodo_no_se_inventa_el_tipo(self):
        """Sin `CorrectionMethod` no hay de dónde deducir 384 o 381.

        Este era el único caso durante meses, y por un motivo equivocado: se
        decía que la lista de valores del método «no se ha podido contrastar
        contra una fuente oficial». La fuente oficial es
        `CorrectionMethodType` del esquema `Facturaev3_2_2.xsd`, que este
        repositorio **sirve dentro de `web/paquete.zip`**. Nadie lo abrió.
        """
        salta = [i for i in en16931.validar(_rectificativa()).incidencias
                 if i.codigo == "FE-TIPO-SIN-EQUIVALENTE"]
        assert salta and salta[0].gravedad == NOTA
        assert salta[0].encontrado == "OR"
        assert "no declara con qué método" in salta[0].mensaje

    @pytest.mark.parametrize("metodo, codigo, dice", [
        ("01", "384", "íntegra"),
        ("03", "381", "volumen"),
    ])
    def test_los_dos_metodos_que_si_se_traducen(self, metodo, codigo, dice):
        """Se traduce **y se dice con qué base**, que es para lo que existe NOTA.

        `01` rehace la factura entera con los datos corregidos, que es la
        definición literal del 384 de UNTDID 1001. `03` es un descuento por
        volumen sobre lo ya facturado, que solo puede restar: 381.
        """
        salidas = en16931.validar(_rectificativa(metodo)).incidencias
        assert "FE-TIPO-SIN-EQUIVALENTE" not in {i.codigo for i in salidas}
        assert "BR-CL-01" not in {i.codigo for i in salidas}
        nota = [i for i in salidas if i.codigo == "FE-TIPO-POR-METODO"]
        assert nota and nota[0].gravedad == NOTA
        assert codigo in nota[0].mensaje
        assert dice in nota[0].mensaje
        assert nota[0].encontrado == metodo
        assert "no hay mapa oficial" in nota[0].mensaje

    @pytest.mark.parametrize("metodo, porque", [
        ("02", "los importes"),
        ("04", "quién la autorizó"),
    ])
    def test_los_dos_que_siguen_sin_traducirse_y_por_que(self, metodo, porque):
        """La mitad que no se resuelve, y la razón concreta de cada una.

        `02` factura solo la diferencia y el método no dice si sube o baja;
        deducirlo del signo sería sacar el tipo de una cuenta y no de lo que el
        documento declara. `04` dice quién autorizó, no cómo se rectifica.
        """
        salta = [i for i in en16931.validar(_rectificativa(metodo)).incidencias
                 if i.codigo == "FE-TIPO-SIN-EQUIVALENTE"]
        assert salta and salta[0].gravedad == NOTA
        assert porque in salta[0].mensaje
        assert "FE-TIPO-POR-METODO" not in {
            i.codigo for i in en16931.validar(_rectificativa(metodo)).incidencias}

    def test_y_una_ordinaria_si_se_traduce(self):
        """El control: `OO` es 380 y no se queja nadie."""
        codigos_vistos = codigos(en16931.validar(FACTURAE_UNA))
        assert "FE-TIPO-SIN-EQUIVALENTE" not in codigos_vistos
        assert "BR-CL-01" not in codigos_vistos
