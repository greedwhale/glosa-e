# -*- coding: utf-8 -*-
"""Lo que le pasa a una factura Facturae al copiarla a la solución pública.

Las cuentas de la factura de prueba, para poder seguirlas a mano:

    base antes de impuestos ....................... 100,00
    IVA 21% ....................................... 21,00
    recargo de equivalencia 5,2% ..................  5,20
    total de impuestos repercutidos (Facturae) .... 26,20
    retención 15% ................................. 15,00
    total factura (Facturae) = 100 + 26,20 - 15 ... 111,20

Y lo que tendría que llevar la copia, con los términos de la norma:

    BT-110, cuotas de IVA ......................... 21,00   (sin el recargo)
    BT-112, total con impuestos = 100 + 21 ........ 121,00  (sin restar la retención)

Los dos números de la copia son distintos de los dos de la factura, y esa es
toda la razón de ser del módulo: no falta un dato, cambia una cifra. Cada
prueba enciende **un** concepto y comprueba que sale **esa** nota.
"""
from __future__ import annotations

import re

import pytest

from validador import copia_fiel
from validador.formato import detectar
from validador.incidencias import NOTA

PLANTILLA = """<?xml version="1.0" encoding="UTF-8"?>
<fe:Facturae xmlns:fe="http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml">
  <FileHeader>
    <SchemaVersion>3.2.2</SchemaVersion>
    <Modality>I</Modality>
    <InvoiceIssuerType>EM</InvoiceIssuerType>
  </FileHeader>
  <Parties>
    <SellerParty><TaxIdentification>
      <TaxIdentificationNumber>B12345674</TaxIdentificationNumber>
    </TaxIdentification>{persona}{contacto}</SellerParty>
    <BuyerParty><TaxIdentification>
      <TaxIdentificationNumber>B12345674</TaxIdentificationNumber>
    </TaxIdentification>{fuera}</BuyerParty>
  </Parties>
  <Invoices><Invoice>
    <InvoiceHeader>{serie}<InvoiceNumber>0001</InvoiceNumber>
      {rectificada}</InvoiceHeader>
    <InvoiceIssueData>
      <IssueDate>2026-09-20</IssueDate>
      {monedas}
      {idioma}
      {cabecera}
    </InvoiceIssueData>
    <TaxesOutputs><Tax>
      <TaxTypeCode>01</TaxTypeCode>
      <TaxRate>21.00</TaxRate>
      <TaxableBase><TotalAmount>100.00</TotalAmount></TaxableBase>
      <TaxAmount><TotalAmount>21.00</TotalAmount></TaxAmount>
      {recargo}
    </Tax>{segundo_tipo}{cero}</TaxesOutputs>
    {retenciones}
    {lineas}
    <InvoiceTotals>
      <TotalGrossAmountBeforeTaxes>100.00</TotalGrossAmountBeforeTaxes>
      <TotalTaxOutputs>{repercutido}</TotalTaxOutputs>
      <TotalTaxesWithheld>{retenido}</TotalTaxesWithheld>
      <InvoiceTotal>{total}</InvoiceTotal>
      {generales}
      {suplidos}
      {financieros}
      {subvenciones}
    </InvoiceTotals>
    {pago}
    {adicional}
  </Invoice></Invoices>
</fe:Facturae>
"""

# Una línea suelta, con lo justo para encender una nota cada vez. Por defecto
# la factura no lleva ninguna: así `test_una_factura_sin_nada_de_eso_no_dice_nada`
# sigue diciendo lo que dice. `{extra}` es lo que Facturae mete dentro de la
# línea y la copia querría en el documento: las referencias.
LINEA = """<InvoiceLine>
      {extra}
      <ItemDescription>Una cosa</ItemDescription>
      <Quantity>1.00</Quantity>
      {unidad}
      <UnitPriceWithoutTax>100.00</UnitPriceWithoutTax>
      {coste}
      {bruto}
    </InvoiceLine>"""

# Las cinco referencias que Facturae guarda dentro de la línea, juntas, que es
# como llegan: las facturas que traen una traen las cuatro primeras.
REFERENCIAS = """<IssuerContractReference>C-EM-1</IssuerContractReference>
      <IssuerTransactionReference>P-EM-1</IssuerTransactionReference>
      <ReceiverContractReference>C-RE-1</ReceiverContractReference>
      <ReceiverTransactionReference>P-RE-1</ReceiverTransactionReference>
      <FileReference>EXP-2026-1</FileReference>"""

# Un vencimiento, con lo justo. La dirección de la sucursal es lo que no
# viaja: de la cuenta, la norma se queda con el identificador.
VENCIMIENTO = """<Installment>
      <InstallmentDueDate>2026-10-{dia:02d}</InstallmentDueDate>
      <InstallmentAmount>121.00</InstallmentAmount>
      {medio}
      <AccountToBeCredited>
        <IBAN>ES9121000418450200051332</IBAN>
        {sucursal}
      </AccountToBeCredited>
    </Installment>"""

SUCURSAL = """<BranchInSpainAddress>
          <Address>Gran Via 1</Address>
          <PostCode>28013</PostCode>
          <Town>Madrid</Town>
          <Province>Madrid</Province>
          <CountryCode>ESP</CountryCode>
        </BranchInSpainAddress>"""

# Una entrada del desglose al 0 %, que es donde la copia se queda sin saber
# de qué categoría hablar: un cero puede ser seis cosas distintas.
CERO = """<Tax>
      <TaxTypeCode>01</TaxTypeCode>
      <TaxRate>0.00</TaxRate>
      <TaxableBase><TotalAmount>50.00</TotalAmount></TaxableBase>
      <TaxAmount><TotalAmount>0.00</TotalAmount></TaxAmount>
    </Tax>"""

# La fiscalidad especial, que vive en la línea y solo tiene dos valores: 01
# «sujeta y exenta» y 02 «no sujeta». Su motivo es obligatorio en el esquema.
FISCALIDAD = """<SpecialTaxableEvent>
        <SpecialTaxableEventCode>{clave}</SpecialTaxableEventCode>
        <SpecialTaxableEventReason>{motivo}</SpecialTaxableEventReason>
      </SpecialTaxableEvent>"""

# Un segundo tipo de IVA, que es lo que convierte el descuento general en una
# decisión: con una sola categoría la cuenta está forzada.
SEGUNDO_TIPO = """<Tax>
      <TaxTypeCode>01</TaxTypeCode>
      <TaxRate>10.00</TaxRate>
      <TaxableBase><TotalAmount>100.00</TotalAmount></TaxableBase>
      <TaxAmount><TotalAmount>10.00</TotalAmount></TaxAmount>
    </Tax>"""

# Una retención con su desglose, que también escribe un `TaxRate`. Está aquí
# para provocar el fallo de contar categorías por todo el documento: contarla
# diría que esta factura tiene dos cuando tiene una.
RETENCIONES = """<TaxesWithheld><Tax>
      <TaxTypeCode>04</TaxTypeCode>
      <TaxRate>15.00</TaxRate>
      <TaxableBase><TotalAmount>100.00</TotalAmount></TaxableBase>
      <TaxAmount><TotalAmount>15.00</TotalAmount></TaxAmount>
    </Tax></TaxesWithheld>"""

RECARGO = """<EquivalenceSurcharge>5.20</EquivalenceSurcharge>
      <EquivalenceSurchargeAmount><TotalAmount>5.20</TotalAmount></EquivalenceSurchargeAmount>"""

# El fax cuelga de la entidad, que es donde lo pone el esquema. Y la dirección
# de fuera junta el código postal y la población en un solo campo: es el dato
# que hay que partir en dos para la copia.
CONTACTO = """<LegalEntity><ContactDetails>
      <TeleFax>911234567</TeleFax>
    </ContactDetails></LegalEntity>"""
FUERA = """<Individual><OverseasAddress>
      <Address>1 High Street</Address>
      <PostCodeAndTown>SW1A 1AA London</PostCodeAndTown>
      <CountryCode>GBR</CountryCode>
    </OverseasAddress></Individual>"""
# Una persona física como vendedor: su nombre va en tres campos y en la copia
# va en uno. El segundo apellido se deja fuera cuando no se pide, que es la
# mitad de los casos de las facturas reales.
PERSONA = """<Individual>
      <Name>{nombre}</Name>
      <FirstSurname>{primero}</FirstSurname>
      {segundo}
    </Individual>"""

# La misma dirección de fuera, pero colgada de un centro administrativo, que
# **no** tiene ese destino en el anexo. Es la mitad de las que hay en las
# facturas reales, así que la exclusión se prueba y no se comenta.
FUERA_EN_UN_CENTRO = """<AdministrativeCentres><AdministrativeCentre>
      <CentreCode>E00000012</CentreCode>
      <OverseasAddress>
        <Address>1 High Street</Address>
        <PostCodeAndTown>SW1A 1AA London</PostCodeAndTown>
        <CountryCode>GBR</CountryCode>
      </OverseasAddress>
    </AdministrativeCentre></AdministrativeCentres>"""


def factura(recargo=False, retenido="0.00", suplidos=None, financieros=None,
            serie=None, idioma=False, fax=False, fuera=None, subvenciones=None,
            unidad=None, coste=None, neto=None,
            descuento_general=None, cargo_general=None, segundo_tipo=False,
            retencion_detallada=False, medio=None, vencimientos=0,
            sucursal=False, referencias=False, albaranes=(), secuencias=(),
            cabecera=None, asociada=None, rectificada=None,
            tipo_cero=False, fiscalidad=(), motivo="01 exenta por el 20.Uno",
            moneda=None, moneda_impuesto=None, persona=None):
    """Una factura de 100 de base y 21 de IVA, con lo que se le encienda."""
    repercutido = "26.20" if recargo else "21.00"
    total = str(round(100 + float(repercutido) - float(retenido), 2))
    # La línea se arma si se pide alguna de sus tres piezas. `unidad=""` pide
    # una línea **sin** unidad, que es un caso distinto de no pedir línea.
    #
    # Y cada albarán o cada número de secuencia pide **su** línea, que es como
    # llegan en las facturas de verdad: la referencia vive dentro de la línea
    # y por eso dos líneas pueden traer dos distintas.
    dentro = []
    if unidad is not None or coste is not None or neto is not None:
        dentro.append("")
    if referencias:
        dentro.append(REFERENCIAS)
    dentro.extend(
        f"<DeliveryNotesReferences><DeliveryNote>"
        f"<DeliveryNoteNumber>{uno}</DeliveryNoteNumber>"
        f"</DeliveryNote></DeliveryNotesReferences>" for uno in albaranes
    )
    dentro.extend(f"<SequenceNumber>{uno}</SequenceNumber>" for uno in secuencias)
    dentro.extend(FISCALIDAD.format(clave=uno, motivo=motivo)
                  for uno in fiscalidad)
    lineas = ""
    if dentro:
        cuerpos = "".join(
            LINEA.format(
                extra=extra,
                unidad=f"<UnitOfMeasure>{unidad}</UnitOfMeasure>" if unidad else "",
                coste=f"<TotalCost>{coste}</TotalCost>" if coste else "",
                bruto=f"<GrossAmount>{neto}</GrossAmount>" if neto else "",
            )
            for extra in dentro
        )
        lineas = "<Items>" + cuerpos + "</Items>"

    generales = ""
    if descuento_general:
        generales += (f"<GeneralDiscounts><Discount>"
                      f"<DiscountReason>pronto pago</DiscountReason>"
                      f"<DiscountRate>10.00</DiscountRate>"
                      f"<DiscountAmount>{descuento_general}</DiscountAmount>"
                      f"</Discount></GeneralDiscounts>")
    if cargo_general:
        generales += (f"<GeneralSurcharges><Charge>"
                      f"<ChargeReason>portes</ChargeReason>"
                      f"<ChargeAmount>{cargo_general}</ChargeAmount>"
                      f"</Charge></GeneralSurcharges>")
    # `medio` o `sucursal` piden un vencimiento aunque no se pida ninguno:
    # así una prueba del medio de pago no tiene que acordarse de los dos.
    cuantos = vencimientos or (1 if (medio or sucursal) else 0)
    pago = ""
    if cuantos:
        dentro = "".join(
            VENCIMIENTO.format(
                dia=1 + i,
                medio=f"<PaymentMeans>{medio}</PaymentMeans>" if medio else "",
                sucursal=SUCURSAL if sucursal else "",
            )
            for i in range(cuantos)
        )
        pago = f"<PaymentDetails>{dentro}</PaymentDetails>"
    # La rectificada lleva el número y la serie en dos campos; la asociada,
    # los dos en uno. Son los dos caminos a BG-3 y se prueban los dos.
    rectificada_xml = ""
    if rectificada:
        numero, serie_previa, fecha = rectificada
        rectificada_xml = (
            "<Corrective>"
            + (f"<InvoiceNumber>{numero}</InvoiceNumber>" if numero else "")
            + (f"<InvoiceSeriesCode>{serie_previa}</InvoiceSeriesCode>"
               if serie_previa else "")
            + "<ReasonCode>01</ReasonCode><CorrectionMethod>03</CorrectionMethod>"
            + (f"<InvoiceIssueDate>{fecha}</InvoiceIssueDate>" if fecha else "")
            + "</Corrective>"
        )
    documento = PLANTILLA.format(
        pago=pago,
        rectificada=rectificada_xml,
        cabecera=(f"<ReceiverTransactionReference>{cabecera}"
                  f"</ReceiverTransactionReference>" if cabecera else ""),
        adicional=(f"<AdditionalData><RelatedInvoice>{asociada}"
                   f"</RelatedInvoice></AdditionalData>" if asociada else ""),
        generales=generales,
        segundo_tipo=SEGUNDO_TIPO if segundo_tipo else "",
        cero=CERO if tipo_cero else "",
        monedas=(
            (f"<InvoiceCurrencyCode>{moneda}</InvoiceCurrencyCode>"
             if moneda else "")
            + (f"<TaxCurrencyCode>{moneda_impuesto}</TaxCurrencyCode>"
               if moneda_impuesto else "")
        ),
        persona=(PERSONA.format(
            nombre=persona[0], primero=persona[1],
            segundo=(f"<SecondSurname>{persona[2]}</SecondSurname>"
                     if len(persona) > 2 and persona[2] else ""),
        ) if persona else ""),
        retenciones=RETENCIONES if retencion_detallada else "",
        lineas=lineas,
        recargo=RECARGO if recargo else "",
        repercutido=repercutido,
        retenido=retenido,
        total=total,
        suplidos=(f"<TotalReimbursableExpenses>{suplidos}</TotalReimbursableExpenses>"
                  if suplidos else ""),
        financieros=(f"<TotalFinancialExpenses>{financieros}</TotalFinancialExpenses>"
                     if financieros else ""),
        subvenciones=(f"<Subsidies><Subsidy><SubsidyDescription>obra</SubsidyDescription>"
                      f"<SubsidyRate>10.00</SubsidyRate>"
                      f"<SubsidyAmount>{subvenciones}</SubsidyAmount>"
                      f"</Subsidy></Subsidies>" if subvenciones else ""),
        serie=(f"<InvoiceSeriesCode>{serie}</InvoiceSeriesCode>" if serie else ""),
        idioma="<LanguageName>es</LanguageName>" if idioma else "",
        contacto=CONTACTO if fax else "",
        fuera={"parte": FUERA, "centro": FUERA_EN_UN_CENTRO}.get(fuera, ""),
    ).encode("utf-8")
    from lxml import etree

    return etree.fromstring(documento), detectar(documento)


def notas(**como):
    raiz, deteccion = factura(**como)
    return {i.codigo: i for i in copia_fiel.reglas(raiz, deteccion)}


def test_una_factura_sin_nada_de_eso_no_dice_nada():
    """Si saliera una nota en cualquier factura, las demás pruebas no dirían nada."""
    assert notas() == {}


def test_con_retencion_el_total_de_la_copia_no_es_el_de_la_factura():
    salidas = notas(retenido="15.00")
    assert set(salidas) == {"COPIA-TOTAL"}
    nota = salidas["COPIA-TOTAL"]
    assert nota.gravedad == NOTA
    assert "121,00" in nota.esperado  # 100 de base + 21 de cuota
    assert "106,00" in nota.encontrado  # lo que pone la factura
    assert "15,00" in nota.encontrado  # y por qué es distinto


def test_con_recargo_la_cuota_de_la_copia_no_es_la_de_la_factura():
    salidas = notas(recargo=True)
    assert set(salidas) == {"COPIA-CUOTA", "COPIA-TOTAL"}
    cuota = salidas["COPIA-CUOTA"]
    assert "21,00" in cuota.esperado
    assert "26,20" in cuota.encontrado and "5,20" in cuota.encontrado


def test_con_las_dos_cosas_los_dos_numeros_cambian():
    salidas = notas(recargo=True, retenido="15.00")
    assert set(salidas) == {"COPIA-CUOTA", "COPIA-TOTAL"}
    # El total europeo no lleva ni la retención restada ni el recargo sumado.
    assert "121,00" in salidas["COPIA-TOTAL"].esperado


# La copia en UBL de la factura de prueba, con la cuota y el total a elegir.
# El total a pagar (BT-115) va igual que el total porque qué entra en él está
# `POR_DECIDIR` en la tabla, y así la prueba de abajo solo mueve lo que mide.
COPIA_UBL = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:CustomizationID>urn:cen.eu:en16931:2017</cbc:CustomizationID>
  <cbc:ID>FE-0001</cbc:ID>
  <cbc:IssueDate>2026-09-20</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PostalAddress><cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Vendedor</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PostalAddress><cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyLegalEntity><cbc:RegistrationName>Comprador</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingCustomerParty>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">{cuota}</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">{total}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">{total}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="C62">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Name>Una cosa</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>
    </cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">100.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</Invoice>
"""


def test_el_total_copiado_tal_cual_no_pasa_las_reglas_de_la_copia():
    """Un total mal copiado se ve: la copia deja de cuadrar consigo misma.

    Hasta el 26-09-2026 la cabecera del módulo y la bitácora del 21-09 decían
    lo contrario —que un número equivocado «cuadra consigo mismo, pasa las
    validaciones de la copia»— y no era cierto. Con la cuota de Facturae
    (26,20, con el recargo dentro) y su total (111,20, con la retención
    restada) llevados a BT-110 y BT-112, la copia rompe `BR-CO-14` —la cuota
    no es la suma del desglose, que son 21— y `BR-CO-15` —el total no es la
    base más la cuota, que serían 126,20—.

    Lo que sí pasa en silencio es el medio de pago, y eso lo fija
    `test_el_medio_de_pago_pasa_la_validacion_diciendo_otra_cosa`.

    La copia bien traducida, con 21 y 121, sale limpia, y eso es lo que hace
    que la prueba mida algo: un validador que rechazara todo pasaría la
    segunda comprobación sin pasar la primera.
    """
    from validador import factura

    def de_cuentas(cuota: str, total: str) -> set[str]:
        informe = factura.validar(COPIA_UBL.format(cuota=cuota, total=total))
        assert informe.validado
        return {i.codigo for i in informe.incidencias
                if i.codigo.startswith("BR-CO-")}

    assert de_cuentas("21.00", "121.00") == set()
    assert de_cuentas("26.20", "111.20") == {"BR-CO-14", "BR-CO-15"}


def test_los_suplidos_no_se_sabe_donde_se_escriben():
    salidas = notas(suplidos="7.00")
    assert set(salidas) == {"COPIA-SUPLIDO"}
    assert "7.00" in salidas["COPIA-SUPLIDO"].encontrado
    assert "BT-179" in salidas["COPIA-SUPLIDO"].mensaje or "2026" in salidas[
        "COPIA-SUPLIDO"].mensaje


def test_los_gastos_financieros_no_tienen_sitio():
    salidas = notas(financieros="1.00")
    assert set(salidas) == {"COPIA-SIN-SITIO"}
    assert "1,00" in salidas["COPIA-SIN-SITIO"].encontrado


def test_todas_son_notas_y_ninguna_es_un_fallo():
    """La AEAT dijo el 17-09-2026 que un concepto sin equivalente se puede omitir."""
    salidas = notas(recargo=True, retenido="15.00", suplidos="7.00", financieros="1.00")
    assert len(salidas) == 4
    assert {i.gravedad for i in salidas.values()} == {NOTA}


def test_en_otra_sintaxis_no_se_mete():
    ubl = b"""<?xml version="1.0"?>
    <Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">
      <ID>1</ID>
    </Invoice>"""
    from lxml import etree

    assert copia_fiel.reglas(etree.fromstring(ubl), detectar(ubl)) == []


def test_sin_documento_no_hay_nada_que_decir():
    assert copia_fiel.reglas(None, None) == []


def test_la_serie_y_el_numero_van_juntos_en_la_copia():
    """BT-1 es «número y serie», un solo campo, y Facturae tiene dos."""
    salidas = notas(serie="FRA")
    assert set(salidas) == {"COPIA-SERIE"}
    nota = salidas["COPIA-SERIE"]
    assert nota.gravedad == NOTA
    assert "FRA0001" in nota.esperado
    assert "0001" in nota.encontrado and "FRA" in nota.encontrado


def test_sin_serie_no_hay_nada_que_juntar():
    """Seis de las catorce facturas de aquí traen el campo vacío."""
    assert notas(serie="") == {}
    assert notas(serie="   ") == {}


def test_la_direccion_de_fuera_hay_que_partirla_en_dos():
    salidas = notas(fuera="parte")
    assert set(salidas) == {"COPIA-DIRECCION"}
    nota = salidas["COPIA-DIRECCION"]
    assert "BT-53" in nota.campo and "BT-52" in nota.campo
    assert "SW1A 1AA London" in nota.encontrado


def test_la_direccion_de_un_centro_administrativo_no_es_la_de_la_parte():
    """Provocada: la mitad de las direcciones de fuera cuelgan de un centro.

    Del centro, el anexo se queda con sus identificadores y no con su
    domicilio, así que BT-52 y BT-53 no son su destino y la nota mentiría.
    """
    assert notas(fuera="centro") == {}


def test_lo_que_se_queda_en_el_original_va_en_una_sola_nota():
    salidas = notas(idioma=True, fax=True, financieros="1.00", subvenciones="50.00")
    assert set(salidas) == {"COPIA-SIN-SITIO"}
    quedan = salidas["COPIA-SIN-SITIO"].encontrado
    for cosa in ("idioma", "fax", "gastos financieros", "subvenciones"):
        assert cosa in quedan, quedan
    # Los importes van con su cifra; los datos, solo nombrados.
    assert "1,00" in quedan and "50,00" in quedan


def test_la_unidad_de_medida_no_vale_escrita_asi():
    """`01` es «Units» en Facturae y no es un código de UN/ECE.

    Las 18 líneas medidas aquí escriben ese mismo `01`, y es justo uno de los
    seis códigos de la lista de Facturae que no llevan el europeo en su propia
    etiqueta: el que más se usa es el que menos ayuda.
    """
    unidad = notas(unidad="01")["COPIA-LINEA-UNIDAD"]
    assert unidad.gravedad == NOTA
    assert "C62" in unidad.esperado
    assert "01" in unidad.encontrado


def test_sin_unidad_de_medida_no_se_dice_nada():
    """Que falte es otro problema, y lo acusa `BR-23`, no esto."""
    assert "COPIA-LINEA-UNIDAD" not in notas(unidad="")


def test_una_unidad_que_no_es_la_suelta_no_promete_el_codigo():
    """De `02` el esquema dice «Hours-HUR» y de `01` no dice nada.

    Aquí solo se promete lo comprobado: la traducción de `01`. Con cualquier
    otro código la nota dice que hay que traducirlo y no se inventa a qué, que
    es lo que se puede sostener sin la tabla entera escrita.
    """
    unidad = notas(unidad="02")["COPIA-LINEA-UNIDAD"]
    assert "C62" not in unidad.esperado
    assert "UN/ECE" in unidad.esperado


def test_el_importe_neto_de_la_linea_es_el_bruto_y_no_el_coste():
    """Con un descuento de línea, `TotalCost` y `GrossAmount` se separan.

    Es el mismo fallo que el de los totales un piso más arriba: copiar el
    campo de al lado no deja un hueco, deja un número que parece bueno.
    """
    neto = notas(coste="100.00", neto="90.00")["COPIA-LINEA-NETO"]
    assert neto.gravedad == NOTA
    assert "90,00" in neto.esperado
    assert "100,00" in neto.encontrado
    assert "1 de 1" in neto.encontrado


def test_una_linea_sin_descuento_no_saca_nota_de_importe():
    """Cuando los dos campos valen lo mismo no hay nada que decidir."""
    assert "COPIA-LINEA-NETO" not in notas(coste="100.00", neto="100.00")


def test_una_linea_a_la_que_le_falta_un_campo_no_inventa_la_queja():
    """Provocado: sin `TotalCost`, comparar contra cero acusaría de mentira.

    `_numero` devuelve cero cuando el campo falta, así que la comparación a
    secas daría «0,00 frente a 90,00» en una factura a la que solo le falta un
    campo que su propio esquema exige.
    """
    assert "COPIA-LINEA-NETO" not in notas(neto="90.00")


def test_un_descuento_general_pide_un_iva_que_la_factura_no_lleva():
    """La norma agrupa las minoraciones por categoría y Facturae no las agrupa.

    Con una sola categoría en la factura no hay nada que decidir, pero sí algo
    que escribir: BT-95 y BT-96 no existen en el original.
    """
    cargo = notas(descuento_general="10.00")["COPIA-CARGO-IVA"]
    assert cargo.gravedad == NOTA
    assert "al 21%," in cargo.esperado
    assert "1 en esta factura" in cargo.encontrado


def test_con_dos_categorias_el_descuento_general_hay_que_repartirlo():
    """Aquí sí hay decisión, y ningún texto dice cómo se toma."""
    cargo = notas(descuento_general="10.00", segundo_tipo=True)["COPIA-CARGO-IVA"]
    assert "2 categorías" in cargo.esperado
    assert "prorrata" in cargo.esperado


def test_un_cargo_general_cuenta_igual_que_un_descuento():
    """`BG-21` lleva su categoría y su tipo por el mismo motivo que `BG-20`."""
    cargo = notas(cargo_general="5.00")["COPIA-CARGO-IVA"]
    assert "1 en esta factura" in cargo.encontrado


def test_los_dos_juntos_salen_en_una_sola_nota():
    """Dos notas seguidas diciendo lo mismo no las lee nadie."""
    salidas = notas(descuento_general="10.00", cargo_general="5.00")
    assert "2 en esta factura" in salidas["COPIA-CARGO-IVA"].encontrado


def test_una_retencion_no_cuenta_como_otra_categoria_de_iva():
    """Provocado: una retención también escribe `TaxRate`.

    Contando los tipos por todo el documento, esta factura -que tiene una sola
    categoría de IVA y una retención- saldría con dos y pediría un reparto que
    no hace falta.
    """
    cargo = notas(descuento_general="10.00",
                  retencion_detallada=True)["COPIA-CARGO-IVA"]
    assert "al 21%," in cargo.esperado
    assert "prorrata" not in cargo.esperado


def test_sin_descuentos_ni_cargos_generales_no_se_dice_nada():
    """Los de línea no cuentan: ésos pasan sin discusión."""
    assert "COPIA-CARGO-IVA" not in notas(coste="100.00", neto="90.00")


def test_el_medio_de_pago_pasa_la_validacion_diciendo_otra_cosa():
    """El caso más feo de la tabla, y el que no se ve.

    Los 19 códigos de Facturae existen los 19 en UNCL4461 con otro
    significado, así que copiar el dígito no da un error: da una factura
    válida que dice que se paga de otra manera.
    """
    medio = notas(medio="19")["COPIA-PAGO-MEDIO"]
    assert medio.gravedad == NOTA
    assert "48" in medio.esperado
    assert "bank card" in medio.esperado
    assert "pago mediante tarjeta" in medio.encontrado


def test_un_medio_de_pago_sin_equivalente_no_se_inventa():
    """El 06 es un crédito documentario y no tiene equivalente sostenible.

    Ponerle uno «parecido» es justo el fallo del que avisa la nota, así que
    aquí se dice que hay que elegirlo a mano y no se da ninguno.
    """
    medio = notas(medio="06")["COPIA-PAGO-MEDIO"]
    assert "a mano" in medio.esperado
    assert "UNCL4461" in medio.esperado
    assert "06 en esta factura" in medio.encontrado


def test_dos_vencimientos_no_caben_en_la_copia():
    """Provocado: ninguna de las 14 facturas de aquí trae más de uno.

    El corte existe -`Installment` es `maxOccurs="unbounded"` y `BG-16` es
    0..1- y no se ha visto, así que se prueba a mano o no se prueba.
    """
    vencimientos = notas(vencimientos=2)["COPIA-VENCIMIENTOS"]
    assert vencimientos.gravedad == NOTA
    assert "2 en esta factura" in vencimientos.encontrado
    assert "2026-10-01" in vencimientos.encontrado


def test_un_solo_vencimiento_no_saca_esa_nota():
    """Con uno, la copia lo recoge entero y no hay nada que elegir."""
    assert "COPIA-VENCIMIENTOS" not in notas(vencimientos=1)


def test_la_direccion_de_la_sucursal_se_queda_en_el_original():
    """De la cuenta, la norma se queda con el identificador y poco más."""
    sin_sitio = notas(sucursal=True)["COPIA-SIN-SITIO"]
    assert "sucursal" in sin_sitio.encontrado


def test_sin_bloque_de_pago_no_se_dice_nada_del_pago():
    """Una factura sin `PaymentDetails` no tiene nada que contar aquí."""
    salidas = notas()
    assert "COPIA-PAGO-MEDIO" not in salidas
    assert "COPIA-VENCIMIENTOS" not in salidas


def test_las_referencias_de_la_linea_salen_todas_en_una_nota():
    """Cinco referencias, una nota: cinco notas seguidas no las lee nadie."""
    nota = notas(referencias=True)["COPIA-REFERENCIAS"]
    assert nota.gravedad == NOTA
    for concepto in ("pedido del comprador", "pedido del vendedor",
                     "contrato del comprador", "contrato del vendedor",
                     "expediente"):
        assert concepto in nota.encontrado
    # Y el aviso de lo que hay que hacer con el hueco que queda libre.
    assert "BT-10" in nota.mensaje


def test_dos_albaranes_distintos_son_algo_que_elegir():
    """El corte que sí se ha visto: 3 de las 14 traen más de uno.

    Facturae los pone dentro de cada línea y la norma tiene una referencia
    por documento, así que con dos hay que elegir cuál viaja.
    """
    nota = notas(albaranes=("ALB-1", "ALB-2"))["COPIA-REFERENCIAS"]
    assert "albarán (2 distintos)" in nota.encontrado


def test_el_mismo_albaran_en_dos_lineas_no_es_una_eleccion():
    """Repetido no es distinto: no hay nada que elegir y no se cuenta."""
    nota = notas(albaranes=("ALB-1", "ALB-1"))["COPIA-REFERENCIAS"]
    assert "albarán" in nota.encontrado and "distintos" not in nota.encontrado


def test_el_numero_de_linea_del_pedido_no_se_cuenta_por_lineas():
    """BT-132 es de línea en los dos formatos: uno por línea es lo correcto.

    Contarlos diría que hay algo que elegir, y el corte no le afecta.
    """
    nota = notas(secuencias=("1.0", "2.0"))["COPIA-REFERENCIAS"]
    assert "número de línea del pedido" in nota.encontrado
    assert "distintos" not in nota.encontrado


def test_la_referencia_de_la_cabecera_tambien_cuenta():
    """Provocado: ninguna de las 14 la escribe en la cabecera.

    Facturae admite el pedido en `InvoiceIssueData` y en la línea, y las 14
    facturas de aquí lo ponen siempre en la línea. Si solo se mirase ahí,
    una factura que lo ponga arriba no diría nada.
    """
    nota = notas(cabecera="P-RE-9")["COPIA-REFERENCIAS"]
    assert "pedido del comprador" in nota.encontrado


def test_la_factura_asociada_llega_junta_y_sin_fecha():
    """`RelatedInvoice` es el único campo de Facturae que ya viene junto.

    Y aun así hace falta la nota, por lo de al lado: BT-26 es obligatorio
    dentro del grupo y este campo no trae ninguna fecha.
    """
    nota = notas(asociada="FA0001")["COPIA-FACTURA-PREVIA"]
    assert nota.gravedad == NOTA
    assert "FA0001" in nota.esperado
    assert "fecha de expedición" in nota.esperado
    assert nota.encontrado == "FA0001"


def test_la_rectificada_va_en_dos_campos_y_se_pega():
    """El mismo pegado que BT-1, y por la misma razón."""
    nota = notas(rectificada=("0001", "FE", "2026-08-01"))["COPIA-FACTURA-PREVIA"]
    assert "FE0001" in nota.esperado and "2026-08-01" in nota.esperado
    assert "en dos campos" in nota.encontrado


def test_una_rectificativa_de_un_periodo_no_señala_a_ninguna_factura():
    """Con el criterio 03 se rectifica un periodo y no hay número que copiar.

    Es la razón por la que `sintaxis.py` deja `facturas_previas` sin mapa en
    Facturae, y aquí tiene que valer igual: sin número, no hay nota.
    """
    assert "COPIA-FACTURA-PREVIA" not in notas(rectificada=("", "", ""))


def test_una_entrada_al_cero_no_dice_de_que_categoria_es():
    """BT-118 es obligatorio y el código de impuesto no lo decide.

    Un cero en Facturae puede ser exenta, no sujeta, tipo cero,
    intracomunitaria, exportación o inversión del sujeto pasivo.
    """
    nota = notas(tipo_cero=True)["COPIA-DESGLOSE-CERO"]
    assert nota.gravedad == NOTA
    assert "a mano" in nota.esperado
    for categoria in ("E", "O", "Z", "K", "G", "AE"):
        assert categoria in nota.esperado
    assert "0 %" in nota.encontrado


def test_la_fiscalidad_especial_estrecha_el_cero_a_la_E():
    """El `01` de Facturae es «sujeta y exenta», que en UNCL5305 es la E."""
    nota = notas(tipo_cero=True, fiscalidad=("01",))["COPIA-DESGLOSE-CERO"]
    assert nota.esperado.startswith("E en la copia")
    assert "sujeta y exenta" in nota.esperado
    # Y al ser exenta, el motivo deja de ser opcional en la copia.
    assert "BR-E-10" in nota.mensaje


def test_el_02_es_la_no_sujeta():
    nota = notas(tipo_cero=True, fiscalidad=("02",))["COPIA-DESGLOSE-CERO"]
    assert nota.esperado.startswith("O en la copia")
    assert "BR-E-10" not in nota.mensaje


def test_dos_claves_distintas_no_deciden_la_categoria():
    """Provocado: la fiscalidad especial es de la línea y el 0 % del impuesto.

    Con una exenta y una no sujeta en la misma factura, no hay manera de
    saber de cuál es la entrada del desglose, y elegir la más probable es lo
    que este módulo no hace.
    """
    nota = notas(tipo_cero=True, fiscalidad=("01", "02"))["COPIA-DESGLOSE-CERO"]
    assert "a mano" in nota.esperado


def test_el_motivo_escrito_sale_en_la_nota():
    """Porque hay que leerlo: es texto libre y la copia lo quiere estructurado."""
    nota = notas(tipo_cero=True, fiscalidad=("01",),
                 motivo="01 exenta por el 20.Uno")["COPIA-DESGLOSE-CERO"]
    assert "01 exenta por el 20.Uno" in nota.encontrado


def test_con_tipo_positivo_no_se_dice_nada_del_desglose():
    """A tipo positivo la deducción está forzada: eso es la S y no hay más."""
    assert "COPIA-DESGLOSE-CERO" not in notas()


def test_la_moneda_del_iva_igual_a_la_de_la_factura_no_se_copia():
    """El caso de las 14: Facturae obliga a escribirla y repite la moneda.

    Copiarla enciende `BR-53` en la copia, que pide `BT-111`, y ese número
    no está en el original.
    """
    nota = notas(moneda="EUR", moneda_impuesto="EUR")["COPIA-MONEDA-DEL-IVA"]
    assert nota.gravedad == NOTA
    assert "BT-6 vacío" in nota.esperado
    assert "BR-53" in nota.mensaje


def test_con_otra_moneda_del_iva_hay_que_calcular_la_cuota():
    """Y entonces sí va, con un BT-111 que hay que sacar del tipo de cambio."""
    nota = notas(moneda="USD", moneda_impuesto="EUR")["COPIA-MONEDA-DEL-IVA"]
    assert "BT-111" in nota.esperado and "calcular" in nota.esperado
    assert "USD" in nota.encontrado


def test_sin_moneda_del_impuesto_no_se_dice_nada_de_la_moneda():
    assert "COPIA-MONEDA-DEL-IVA" not in notas(moneda="EUR")


def test_el_nombre_de_una_persona_fisica_va_en_tres_campos():
    """Y en la copia va en uno, que además es obligatorio."""
    nota = notas(persona=("Juana", "Mauriño", "Pérez"))["COPIA-NOMBRE"]
    assert nota.gravedad == NOTA
    assert "3 de 3 campos" in nota.encontrado
    assert "«Juana»" in nota.encontrado and "«Mauriño»" in nota.encontrado
    # No se propone un orden: eso es justo lo que nadie ha fijado.
    assert nota.esperado == "un solo campo en la copia"


def test_un_nombre_sin_segundo_apellido_se_cuenta_como_lo_que_es():
    """La mitad de las personas de las facturas de aquí no lo traen."""
    nota = notas(persona=("DORADO", "", ""))["COPIA-NOMBRE"]
    assert "1 de 3 campos" in nota.encontrado


def test_una_persona_juridica_no_saca_esa_nota():
    """Su razón social ya es un campo, y llega igual."""
    assert "COPIA-NOMBRE" not in notas()


def test_el_destino_de_cada_fila_existe_en_el_anexo():
    """El cepo de verdad de esta tabla: los BT- se comparan con el anexo.

    `cius_es.CAMPOS` es la lista de contenido mínimo del anexo I, y de ahí
    salen los destinos. Si una fila dice que algo llega a un término que el
    anexo no recoge, o si una fila dice «el anexo no lo pide» de un término
    que sí recoge, es que la tabla ya no describe el anexo que hay.
    """
    from validador import cius_es

    del_anexo = {campo.id for campo in cius_es.CAMPOS}
    for fila in copia_fiel.CORRESPONDENCIAS:
        nombrados = re.findall(r"B[TG]-\d+", fila.destino)
        if fila.efecto in (copia_fiel.IGUAL, copia_fiel.CAMBIA,
                           copia_fiel.OTRO_CORTE, copia_fiel.OTRA_LISTA,
                           copia_fiel.SE_INVENTA):
            assert nombrados, fila.concepto
            for uno in nombrados:
                assert uno in del_anexo, f"{fila.concepto}: {uno}"
        if fila.efecto == copia_fiel.NO_LO_PIDEN:
            assert nombrados, fila.concepto
            for uno in nombrados:
                assert uno not in del_anexo, f"{fila.concepto}: {uno}"


def test_el_anexo_sigue_teniendo_los_terminos_que_dice_la_cabecera():
    """104 términos europeos, que es lo que dice el módulo al explicarse.

    No es una cifra de adorno: de esa lista salen los destinos de la tabla y
    contra ella se comparan. El 10-09-2026 la AEAT anunció que el anexo cambia,
    así que el día que llegue el texto nuevo esto salta, y saltar es lo que hay
    que hacer: la tabla entera se vuelve a mirar.
    """
    from validador import cius_es

    europeos = {campo.id for campo in cius_es.CAMPOS
                if not campo.id.startswith(("BT-ES", "BG-ES"))}
    assert len(europeos) == 104, (
        f"el anexo trae {len(europeos)} términos europeos y la cabecera de "
        "`copia_fiel.py` dice 104. Cámbiala, y de paso vuelve a mirar los "
        "destinos de la tabla: si el anexo se ha movido, alguno habrá dejado "
        "de ser verdad."
    )


def test_lo_que_las_reglas_miran_tiene_que_estar_en_la_tabla(monkeypatch):
    """El cepo, provocado: una regla sin su fila no se monta.

    Es lo que evita que quede una queja cuyo porqué ya no está escrito en
    ningún sitio, que es como se pierde la mitad del valor de este módulo.
    """
    monkeypatch.setattr(
        copia_fiel, "CORRESPONDENCIAS",
        tuple(f for f in copia_fiel.CORRESPONDENCIAS if f.facturae != "InvoiceTotal"),
    )
    with pytest.raises(copia_fiel.TablaIncompleta) as fallo:
        copia_fiel._comprobar_la_tabla()
    assert "InvoiceTotal" in str(fallo.value)


def test_cada_fila_dice_que_le_pasa_y_por_que():
    efectos = {copia_fiel.IGUAL, copia_fiel.APARTE, copia_fiel.CAMBIA,
               copia_fiel.OTRO_CORTE, copia_fiel.NO_LO_PIDEN,
               copia_fiel.OTRA_LISTA, copia_fiel.SE_INVENTA,
               copia_fiel.SIN_SITIO, copia_fiel.POR_DECIDIR}
    for fila in copia_fiel.CORRESPONDENCIAS:
        assert fila.efecto in efectos, fila.concepto
        assert len(fila.porque) > 20, fila.concepto
        # Todo lo que llega de alguna manera tiene que decir adónde; lo único
        # que puede quedarse sin destino es lo que no tiene sitio.
        if fila.efecto != copia_fiel.SIN_SITIO:
            assert fila.destino, fila.concepto
        else:
            assert not fila.destino, fila.concepto
        # Lo que se inventa la copia no sale de ningún campo de Facturae, y la
        # fila lo dice en voz alta. Si algún día nombra un elemento, es que ha
        # dejado de inventárselo y el estado está mal puesto.
        if fila.efecto == copia_fiel.SE_INVENTA:
            assert fila.facturae == "(no lo tiene)", fila.concepto
