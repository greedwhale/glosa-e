# -*- coding: utf-8 -*-
"""La fiscalidad especial de Facturae, que es media respuesta a BT-118.

Por qué existe
--------------
Durante semanas este repositorio afirmó, en el README y en el propio código,
que a tipo cero Facturae «no tiene ningún campo donde se haya escrito cuál» es
la categoría de IVA. Era falso, y nadie lo cazó porque **nadie fue a mirar el
esquema que nosotros mismos servimos** dentro de `web/paquete.zip`.

`SpecialTaxableEvent/SpecialTaxableEventCode` está en `Facturaev3_2_2.xsd`, en
la línea, y su enumeración tiene exactamente dos valores:

    01  Operación sujeta y exenta   -> E de UNCL5305
    02  Operación no sujeta         -> O de UNCL5305

Es media respuesta y no una entera: Z, K, G y AE se siguen escribiendo igual,
y el elemento es opcional. De ahí las tres condiciones que fija este fichero.

Lo que se prueba es el borde, no el caso bonito: que **basta una línea muda
para que no se conteste**. Esa es la mitad que impide que el arreglo se
convierta en un dedazo.
"""
from __future__ import annotations

import pytest
from lxml import etree

from validador import iva
from validador.formato import parser
from validador.sintaxis import SINTAXIS_FACTURAE, SINTAXIS_UBL

# Dos líneas de 100, las dos a tipo cero, y un desglose que cuadra con ellas.
# `{especial_1}` y `{especial_2}` se rellenan con el bloque de fiscalidad
# especial o con nada.
PLANTILLA = """<Invoice>
  <InvoiceHeader>
    <InvoiceNumber>F-001</InvoiceNumber>
    <InvoiceDocumentType>FC</InvoiceDocumentType>
    <InvoiceClass>OO</InvoiceClass>
  </InvoiceHeader>
  <InvoiceIssueData>
    <IssueDate>2026-03-05</IssueDate>
    <InvoiceCurrencyCode>EUR</InvoiceCurrencyCode>
  </InvoiceIssueData>
  <TaxesOutputs>
    <Tax>
      <TaxTypeCode>01</TaxTypeCode>
      <TaxRate>0.00</TaxRate>
      <TaxableBase><TotalAmount>200.00</TotalAmount></TaxableBase>
      <TaxAmount><TotalAmount>0.00</TotalAmount></TaxAmount>
    </Tax>
  </TaxesOutputs>
  <InvoiceTotals>
    <TotalGrossAmount>200.00</TotalGrossAmount>
    <TotalGrossAmountBeforeTaxes>200.00</TotalGrossAmountBeforeTaxes>
    <TotalTaxOutputs>0.00</TotalTaxOutputs>
    <TotalTaxesWithheld>0.00</TotalTaxesWithheld>
    <InvoiceTotal>200.00</InvoiceTotal>
    <TotalExecutableAmount>200.00</TotalExecutableAmount>
  </InvoiceTotals>
  <Items>
    <InvoiceLine>
      <ItemDescription>Uno</ItemDescription>
      <Quantity>1.00</Quantity>
      <UnitOfMeasure>01</UnitOfMeasure>
      <UnitPriceWithoutTax>100.00</UnitPriceWithoutTax>
      <TotalCost>100.00</TotalCost>
      <GrossAmount>100.00</GrossAmount>
      {especial_1}
      <TaxesOutputs><Tax>
        <TaxTypeCode>01</TaxTypeCode>
        <TaxRate>0.00</TaxRate>
        <TaxableBase><TotalAmount>100.00</TotalAmount></TaxableBase>
        <TaxAmount><TotalAmount>0.00</TotalAmount></TaxAmount>
      </Tax></TaxesOutputs>
    </InvoiceLine>
    <InvoiceLine>
      <ItemDescription>Dos</ItemDescription>
      <Quantity>1.00</Quantity>
      <UnitOfMeasure>01</UnitOfMeasure>
      <UnitPriceWithoutTax>100.00</UnitPriceWithoutTax>
      <TotalCost>100.00</TotalCost>
      <GrossAmount>100.00</GrossAmount>
      {especial_2}
      <TaxesOutputs><Tax>
        <TaxTypeCode>01</TaxTypeCode>
        <TaxRate>0.00</TaxRate>
        <TaxableBase><TotalAmount>100.00</TotalAmount></TaxableBase>
        <TaxAmount><TotalAmount>0.00</TotalAmount></TaxAmount>
      </Tax></TaxesOutputs>
    </InvoiceLine>
  </Items>
</Invoice>"""

ESPECIAL = """<SpecialTaxableEvent>
        <SpecialTaxableEventCode>{codigo}</SpecialTaxableEventCode>
        <SpecialTaxableEventReason>Porque si</SpecialTaxableEventReason>
      </SpecialTaxableEvent>"""


def factura(primera: str | None, segunda: str | None):
    """Una Facturae de dos líneas a cero, con o sin fiscalidad especial."""
    return etree.fromstring(
        PLANTILLA.format(
            especial_1=ESPECIAL.format(codigo=primera) if primera else "",
            especial_2=ESPECIAL.format(codigo=segunda) if segunda else "",
        ).encode("utf-8"),
        parser=parser(),
    )


def categoria(primera: str | None, segunda: str | None):
    grupos = iva._leer_grupos(factura(primera, segunda), SINTAXIS_FACTURAE)
    assert len(grupos) == 1, "la plantilla tiene una sola entrada de desglose"
    return grupos[0].categoria


def codigos(primera: str | None, segunda: str | None):
    return {i.codigo for i in iva.reglas(factura(primera, segunda),
                                         SINTAXIS_FACTURAE)}


class TestCuandoElDocumentoSiLoDice:
    """Las dos líneas lo traen y dicen lo mismo: hay respuesta y se da."""

    @pytest.mark.parametrize("codigo, espera", [("01", "E"), ("02", "O")])
    def test_se_lee_del_documento(self, codigo, espera):
        assert categoria(codigo, codigo) == espera

    @pytest.mark.parametrize("codigo", ["01", "02"])
    def test_y_entonces_la_nota_no_sale(self, codigo):
        assert "IVA-CATEGORIA-A-CERO" not in codigos(codigo, codigo)


class TestCuandoNoAlcanza:
    """El borde, que es lo que impide que esto sea un dedazo."""

    def test_una_linea_muda_basta_para_no_contestar(self):
        """Su cero puede ser una Z, una K o una G, y no se le atribuye la de al lado."""
        assert categoria("01", None) is None
        assert "IVA-CATEGORIA-A-CERO" in codigos("01", None)

    def test_si_no_coinciden_tampoco(self):
        assert categoria("01", "02") is None
        assert "IVA-CATEGORIA-A-CERO" in codigos("01", "02")

    def test_sin_fiscalidad_especial_se_sigue_avisando(self):
        """El comportamiento de siempre, que no ha cambiado."""
        assert categoria(None, None) is None
        assert "IVA-CATEGORIA-A-CERO" in codigos(None, None)


class TestLoQueNoSeToca:
    def test_las_otras_sintaxis_no_tienen_esto(self):
        """UBL, CII y EDIFACT escriben la categoría directamente y no lo necesitan."""
        from validador.sintaxis import (
            SINTAXIS_CII,
            SINTAXIS_EDIFACT,
            SIN_MAPA,
        )

        for sintaxis in (SINTAXIS_UBL, SINTAXIS_CII, SINTAXIS_EDIFACT):
            assert sintaxis.linea_fiscalidad_especial == SIN_MAPA, sintaxis.nombre

    def test_la_ruta_de_facturae_es_la_del_esquema(self):
        assert (SINTAXIS_FACTURAE.linea_fiscalidad_especial
                == "./SpecialTaxableEvent/SpecialTaxableEventCode")
