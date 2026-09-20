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
    </TaxIdentification></SellerParty>
    <BuyerParty><TaxIdentification>
      <TaxIdentificationNumber>B12345674</TaxIdentificationNumber>
    </TaxIdentification></BuyerParty>
  </Parties>
  <Invoices><Invoice>
    <InvoiceHeader><InvoiceNumber>1</InvoiceNumber></InvoiceHeader>
    <TaxesOutputs><Tax>
      <TaxTypeCode>01</TaxTypeCode>
      <TaxRate>21.00</TaxRate>
      <TaxableBase><TotalAmount>100.00</TotalAmount></TaxableBase>
      <TaxAmount><TotalAmount>21.00</TotalAmount></TaxAmount>
      {recargo}
    </Tax></TaxesOutputs>
    <InvoiceTotals>
      <TotalGrossAmountBeforeTaxes>100.00</TotalGrossAmountBeforeTaxes>
      <TotalTaxOutputs>{repercutido}</TotalTaxOutputs>
      <TotalTaxesWithheld>{retenido}</TotalTaxesWithheld>
      <InvoiceTotal>{total}</InvoiceTotal>
      {suplidos}
      {financieros}
    </InvoiceTotals>
  </Invoice></Invoices>
</fe:Facturae>
"""

RECARGO = """<EquivalenceSurcharge>5.20</EquivalenceSurcharge>
      <EquivalenceSurchargeAmount><TotalAmount>5.20</TotalAmount></EquivalenceSurchargeAmount>"""


def factura(recargo=False, retenido="0.00", suplidos=None, financieros=None):
    """Una factura de 100 de base y 21 de IVA, con lo que se le encienda."""
    repercutido = "26.20" if recargo else "21.00"
    total = str(round(100 + float(repercutido) - float(retenido), 2))
    bruto = PLANTILLA.format(
        recargo=RECARGO if recargo else "",
        repercutido=repercutido,
        retenido=retenido,
        total=total,
        suplidos=(f"<TotalReimbursableExpenses>{suplidos}</TotalReimbursableExpenses>"
                  if suplidos else ""),
        financieros=(f"<TotalFinancialExpenses>{financieros}</TotalFinancialExpenses>"
                     if financieros else ""),
    ).encode("utf-8")
    from lxml import etree

    return etree.fromstring(bruto), detectar(bruto)


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
    assert "121.00" in nota.esperado  # 100 de base + 21 de cuota
    assert "106.00" in nota.encontrado  # lo que pone la factura
    assert "15.00" in nota.encontrado  # y por qué es distinto


def test_con_recargo_la_cuota_de_la_copia_no_es_la_de_la_factura():
    salidas = notas(recargo=True)
    assert set(salidas) == {"COPIA-CUOTA", "COPIA-TOTAL"}
    cuota = salidas["COPIA-CUOTA"]
    assert "21.00" in cuota.esperado
    assert "26.20" in cuota.encontrado and "5.20" in cuota.encontrado


def test_con_las_dos_cosas_los_dos_numeros_cambian():
    salidas = notas(recargo=True, retenido="15.00")
    assert set(salidas) == {"COPIA-CUOTA", "COPIA-TOTAL"}
    # El total europeo no lleva ni la retención restada ni el recargo sumado.
    assert "121.00" in salidas["COPIA-TOTAL"].esperado


def test_los_suplidos_no_se_sabe_donde_se_escriben():
    salidas = notas(suplidos="7.00")
    assert set(salidas) == {"COPIA-SUPLIDO"}
    assert "7.00" in salidas["COPIA-SUPLIDO"].encontrado
    assert "BT-179" in salidas["COPIA-SUPLIDO"].mensaje or "2026" in salidas[
        "COPIA-SUPLIDO"].mensaje


def test_los_gastos_financieros_no_tienen_sitio():
    salidas = notas(financieros="1.00")
    assert set(salidas) == {"COPIA-SIN-SITIO"}
    assert "1.00" in salidas["COPIA-SIN-SITIO"].encontrado


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
               copia_fiel.SIN_SITIO, copia_fiel.POR_DECIDIR}
    for fila in copia_fiel.CORRESPONDENCIAS:
        assert fila.efecto in efectos, fila.concepto
        assert len(fila.porque) > 20, fila.concepto
        # Lo que cambia de número o no tiene sitio es lo que hay que explicar
        # con un destino escrito; lo que llega igual, también.
        if fila.efecto in (copia_fiel.IGUAL, copia_fiel.CAMBIA, copia_fiel.APARTE):
            assert fila.destino, fila.concepto
