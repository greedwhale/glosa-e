"""Las reglas del anexo I sobre facturas de la solución pública.

Las facturas de aquí están escritas al pie de la letra del anexo I de la Orden
HAC/1028/2026, BOE del 05-10-2026 (BOE-A-2026-20587), y tienen que pasar **el
validador entero** sin un error ni un aviso: forma, norma europea, código único
y anexo. Es lo que prueba que las reglas no se pelean con las de antes. De ahí,
cada regla se rompe tocando lo justo y se mira que salte ella y lo que dice.

Hasta el 11-10-2026 la factura de partida era otra, escrita con el borrador de
abril, y la de la orden era una variante. Se dio la vuelta el día que las
reglas se pusieron al texto de la orden: lo del borrador que la orden ya no
admite sale ahora en ERROR, y se prueba aparte (`TestLoQueSoloDeciaElBorrador`).

No hay facturas de verdad de la solución pública con las que medir: no está en
marcha, y en el corpus hay cero documentos que la declaren (medido el
14-09-2026). Por eso están escritas a mano, y por eso las reglas se prueban
también contra un anexo alterado, que es lo que pasará con la próxima
corrección de errores.
"""

import importlib
import os
import pathlib
import re
import subprocess
import sys
from dataclasses import replace

import pytest
from lxml import etree

from validador import cius_es, factura, glosario, iva, listas_de_codigos, solucion_publica
from validador.esquema import Catalogo
from validador.formato import detectar
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia

from tests.test_rutas_cius import _andar, _esquema_de_ubl, con_esquema

ESPECIFICACION = cius_es.ESPECIFICACION
# El que vale, sin ubl:, como contestó el buzón el 13-10-2026; el de la fila
# BT-23 del BOE lo lleva.
PROCESO = solucion_publica.PROCESO
PROCESO_DEL_BOE = cius_es.PROCESO
L7 = cius_es.LISTAS["L7"].calificador
L8 = cius_es.LISTAS["L8"].calificador
L10 = cius_es.LISTAS["L10"].calificador

# Lo del borrador de abril, que ya no vale y se reconoce para decirlo.
DEL_BORRADOR = "urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0"
PROCESO_DEL_BORRADOR = "urn:aeat:names:specification:ubl:schema:B2B"
URN_DEL_BORRADOR = "urn:aeat:names:specification:ubl:schema:"

# La dirección del QR de la factura de la orden, escrita como va en el XML, con
# los & escapados. Hasta el 22-10-2026 llevaba solo el NIF: no se comparaba con
# la factura, y nadie lo veía. Ahora lleva los cuatro datos que pide la
# especificación de la AEAT, y son los de `DEL_BOE`.
QR_URL = ("https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR?nif=B12345674"
          "&amp;numserie=F-2026-0101&amp;fecha=06-10-2026&amp;importe=121.00")


def cambia(xml: str, viejo: str, nuevo: str) -> str:
    """Toca lo justo, y se asegura de que lo tocado está una sola vez."""
    assert xml.count(viejo) == 1, f"«{viejo}» aparece {xml.count(viejo)} veces"
    return xml.replace(viejo, nuevo)


def quita(xml: str, desde: str, hasta: str) -> str:
    """Quita un trozo entero, de su primera línea a la que lo cierra."""
    inicio = xml.index(desde)
    fin = xml.index(hasta, inicio) + len(hasta)
    return xml[:inicio] + xml[fin:]


def spfe(xml: str) -> list[Incidencia]:
    datos = xml.encode("utf-8")
    return solucion_publica.reglas(etree.fromstring(datos), detectar(datos))


def codigos(xml: str) -> set[str]:
    return {i.codigo for i in spfe(xml) if i.gravedad != NOTA}


def las(xml: str, codigo: str) -> list[Incidencia]:
    return [i for i in spfe(xml) if i.codigo == codigo]


def la(xml: str, codigo: str) -> Incidencia:
    encontradas = las(xml, codigo)
    assert len(encontradas) == 1, [(i.campo, i.encontrado) for i in encontradas]
    return encontradas[0]


def limpia(xml: str, catalogo: Catalogo | None = None) -> list[tuple[str, str]]:
    """Los errores y los avisos de todo el validador, que tienen que ser ninguno.

    Con `catalogo`, también la forma: sin él, la suite no tiene esquemas
    (`conftest.py`) y la forma no se mira.
    """
    informe = factura.validar(xml.encode("utf-8"), catalogo=catalogo)
    return [(i.codigo, i.campo) for i in informe.errores + informe.avisos]


@pytest.fixture(scope="module")
def catalogo(esquemas_del_paquete):
    """Los esquemas de UBL 2.5 de verdad, los de `web/paquete.zip`.

    La suite corre sin esquemas, a propósito, y sin ellos «el validador
    entero» no mira la forma. Hasta el 11-10-2026 las buenas se probaban así:
    este módulo y el README decían que pasaban la forma contra UBL 2.5, y en
    la suite no lo comprobaba nadie. Se vio al provocar una prueba que tenía
    que salir en rojo y salió verde. Medido ese día con estos esquemas: las
    21 pasan, en un segundo.
    """
    return Catalogo(esquemas_del_paquete)


# --- La factura de la orden ------------------------------------------------------
#
# Con las formas que el borrador de abril no admitía: el proceso de la orden,
# sin indicador de copia, el vendedor identificado en BT-32 con «LOC» y el
# atributo «FC», un anticipo pagado con su fecha, la retención con el
# calificador de la L7 de la orden y el QR con el de L10. Medido el 07-10-2026
# sobre `6b4a165`, con las reglas del borrador: seis ERROR (SPFE-PROCESO,
# -COPIA, -IMPORTE-PAGADO, -NIF, -LINEA-DE-COBRO y -RETENCION).

DEL_BOE = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:UBLVersionID>2.5</cbc:UBLVersionID>
  <cbc:CustomizationID>{ESPECIFICACION}</cbc:CustomizationID>
  <cbc:ProfileID>{PROCESO}</cbc:ProfileID>
  <cbc:ID>F-2026-0101</cbc:ID>
  <cbc:IssueDate>2026-10-06</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AdditionalDocumentReference>
    <cbc:ID>urn:aeat:names:specification:schema:QR</cbc:ID>
    <cbc:UUID>{QR_URL}</cbc:UUID>
    <cbc:DocumentDescription>VERIFACTU</cbc:DocumentDescription>
  </cac:AdditionalDocumentReference>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PostalAddress>
      <cbc:StreetName>Calle Mayor 1</cbc:StreetName><cbc:CityName>Madrid</cbc:CityName>
      <cbc:PostalZone>28001</cbc:PostalZone><cbc:CountrySubentity>Madrid</cbc:CountrySubentity>
      <cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country>
    </cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID schemeID="FC">B12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Talleres Ejemplo SL</cbc:RegistrationName><cbc:CompanyID>B12345674</cbc:CompanyID></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PostalAddress>
      <cbc:StreetName>Calle Menor 2</cbc:StreetName><cbc:CityName>Sevilla</cbc:CityName>
      <cbc:PostalZone>41001</cbc:PostalZone><cbc:CountrySubentity>Sevilla</cbc:CountrySubentity>
      <cac:Country><cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country>
    </cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>ESA12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Comercio Cliente SA</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingCustomerParty>
  <cac:PrepaidPayment><cbc:PaidAmount currencyID="EUR">20.00</cbc:PaidAmount><cbc:PaidDate>2026-10-06</cbc:PaidDate></cac:PrepaidPayment>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:WithholdingTaxTotal>
    <cbc:TaxAmount currencyID="EUR">15.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">15.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>15</cbc:Percent>
        <cac:TaxScheme><cbc:ID>WTH</cbc:ID><cbc:TaxTypeCode>01</cbc:TaxTypeCode></cac:TaxScheme>
      </cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:WithholdingTaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>
    <cbc:PrepaidAmount currencyID="EUR">20.00</cbc:PrepaidAmount>
    <cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:CollectionInvoiceLine>
    <cbc:ID>{L7}RETE</cbc:ID>
    <cac:Item><cbc:Name>Retencion IRPF</cbc:Name></cac:Item>
  </cac:CollectionInvoiceLine>
  <cac:InvoiceLine>
    <cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="H87">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Name>Asesoria fiscal de octubre</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>
      <cac:AdditionalItemProperty><cbc:Name>{L8}REGI</cbc:Name><cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>
    </cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">100.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</Invoice>"""

_VENDEDOR_LOC = ('<cac:PartyTaxScheme><cbc:CompanyID schemeID="FC">B12345674</cbc:CompanyID>'
                 '<cac:TaxScheme><cbc:ID>LOC</cbc:ID>')
_COMPRADOR_VAT = ("<cac:PartyTaxScheme><cbc:CompanyID>ESA12345674</cbc:CompanyID>"
                  "<cac:TaxScheme><cbc:ID>VAT</cbc:ID>")
_TERCERO_DEL_BOE = """    <cac:ServiceProviderParty>
      <cbc:ServiceTypeCode>FacturaciónPorTercero</cbc:ServiceTypeCode>
      <cac:Party>
        <cac:PartyTaxScheme><cbc:CompanyID schemeID="FC">B87654321</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
        <cac:PartyLegalEntity><cbc:RegistrationName>Gestoria Ejemplo SL</cbc:RegistrationName></cac:PartyLegalEntity>
      </cac:Party>
    </cac:ServiceProviderParty>
  </cac:Party></cac:AccountingSupplierParty>"""
_COBROS_DEL_BOE = "".join(
    f"""  <cac:CollectionInvoiceLine>
    <cbc:ID>{prefijo}{valor}</cbc:ID>
    <cac:Item><cbc:Name>{nombre}</cbc:Name></cac:Item>
  </cac:CollectionInvoiceLine>
""" for prefijo, valor, nombre in (
        (L7, "IEDMT", "Impuesto especial sobre determinados medios de transporte"),
        (L7, "SUPL", "Tasas pagadas por cuenta del cliente"),
        (L7, "MINO", "Devolucion de un suplido"),
        (L7, "OTROS", "Otra tasa"),
    ))

CON_EL_TERCERO_DEL_BOE = cambia(DEL_BOE, "  </cac:Party></cac:AccountingSupplierParty>", _TERCERO_DEL_BOE)
CON_LOS_COBROS_DEL_BOE = cambia(DEL_BOE, "  <cac:InvoiceLine>", _COBROS_DEL_BOE + "  <cac:InvoiceLine>")
CON_EL_COMPRADOR_EN_BT47 = cambia(
    DEL_BOE, _COMPRADOR_VAT,
    '<cac:PartyTaxScheme><cbc:CompanyID schemeID="FC">A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID>')
CON_EL_VENDEDOR_EN_BT31 = cambia(
    DEL_BOE, _VENDEDOR_LOC,
    "<cac:PartyTaxScheme><cbc:CompanyID>ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID>")
CON_LA_RETENCION_SIN_CALIFICADOR = cambia(DEL_BOE, f"{L7}RETE<", "RETE<")
CON_EL_QR_SIN_DESCRIPCION = cambia(DEL_BOE, "<cbc:DocumentDescription>VERIFACTU</cbc:DocumentDescription>", "")
# Las buenas que cambian el total con IVA (BT-112) cambian también el importe
# del QR, que lo copia. Hasta el 22-10-2026 llevaban el de la factura de la
# orden, 121.00, y nadie lo comparaba; al compararlo salieron ocho pruebas de
# este módulo con aviso: las siete de `TestLasBuenas` y la de dos impuestos en
# un cargo.
#
# El recargo de equivalencia como lo pone la orden: sin línea propia, en el
# desglose del IVA (BG-23) con la categoría N, su tipo (BT-119) y su cuota
# (BT-117), sobre la misma base que la entrada S. La cuota total y el total con
# impuestos lo suman (BR-CO-14 y BR-CO-15). Medido el 07-10-2026 con la N ya
# admitida: IVA-BASE en ERROR, «base fantasma» al 5,2%, porque ninguna línea
# va a ese tipo, y ninguna puede ir (BT-151 y BT-152 son 1..1 por línea).
CON_EL_RECARGO_EN_EL_DESGLOSE = cambia(cambia(cambia(cambia(
    DEL_BOE,
    "    </cac:TaxSubtotal>\n  </cac:TaxTotal>",
    """    </cac:TaxSubtotal>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">5.20</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>5.2</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>"""),
    '<cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>',
    '<cbc:TaxAmount currencyID="EUR">26.20</cbc:TaxAmount>\n    <cac:TaxSubtotal>'),
    '<cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>',
    '<cbc:TaxInclusiveAmount currencyID="EUR">126.20</cbc:TaxInclusiveAmount>'),
    '<cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>',
    '<cbc:PayableAmount currencyID="EUR">91.20</cbc:PayableAmount>')
CON_EL_RECARGO_EN_EL_DESGLOSE = cambia(CON_EL_RECARGO_EN_EL_DESGLOSE, "importe=121.00", "importe=126.20")

# El grupo de entidades de nivel avanzado: la línea lleva el importe total de
# la contraprestación (BT-131) y el desglose, la base imponible a coste
# (BT-116), con la categoría N. Las dos cosas las dice la orden en sus filas, y
# no tienen por qué coincidir. Medido el 07-10-2026: IVA-BASE en ERROR,
# esperado 150,00 (la línea) y encontrado 100,00 (la base a coste).
CON_EL_GRUPO_DE_ENTIDADES = cambia(cambia(cambia(cambia(cambia(
    DEL_BOE,
    '<cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>\n    <cac:Item>',
    '<cbc:LineExtensionAmount currencyID="EUR">150.00</cbc:LineExtensionAmount>\n    <cac:Item>'),
    "<cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent>",
    "<cac:ClassifiedTaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>21</cbc:Percent>"),
    "<cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent>",
    "<cac:TaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>21</cbc:Percent>"),
    """    <cbc:LineExtensionAmount currencyID="EUR">100.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>""",
    """    <cbc:LineExtensionAmount currencyID="EUR">150.00</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">150.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">171.00</cbc:TaxInclusiveAmount>"""),
    '<cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>',
    '<cbc:PayableAmount currencyID="EUR">136.00</cbc:PayableAmount>')
CON_EL_GRUPO_DE_ENTIDADES = cambia(CON_EL_GRUPO_DE_ENTIDADES, "importe=121.00", "importe=171.00")

# Una inversión del sujeto pasivo (AE) con el comprador identificado solo en
# BT-47, con «LOC» y «FC», como dice la fila de la orden. BR-AE-02 pide el
# identificador de IVA del comprador (BT-48) o su registro legal (BT-47), y lo
# buscaba donde lo pone la vinculación de 2017, en cac:PartyLegalEntity.
# Medido el 07-10-2026: BR-AE-02 en ERROR, «no identifica fiscalmente al
# comprador», con el NIF del comprador puesto donde lo pide la orden.
CON_AE_Y_EL_COMPRADOR_EN_BT47 = cambia(cambia(cambia(cambia(cambia(cambia(
    CON_EL_COMPRADOR_EN_BT47,
    "<cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent>",
    "<cac:ClassifiedTaxCategory><cbc:ID>AE</cbc:ID><cbc:Percent>0</cbc:Percent>"),
    """      <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme>""",
    """      <cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>AE</cbc:ID><cbc:Percent>0</cbc:Percent><cbc:TaxExemptionReasonCode>VATEX-EU-AE</cbc:TaxExemptionReasonCode><cac:TaxScheme>"""),
    '<cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>',
    '<cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>'),
    '<cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>',
    '<cbc:TaxInclusiveAmount currencyID="EUR">100.00</cbc:TaxInclusiveAmount>'),
    '<cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>',
    '<cbc:PayableAmount currencyID="EUR">65.00</cbc:PayableAmount>'),
    "<cbc:Name>Asesoria fiscal de octubre</cbc:Name>",
    "<cbc:Name>Ejecucion de obra con inversion del sujeto pasivo</cbc:Name>")
CON_AE_Y_EL_COMPRADOR_EN_BT47 = cambia(CON_AE_Y_EL_COMPRADOR_EN_BT47, "importe=121.00", "importe=100.00")

# La L8 de la orden da el valor, REGI, y aparte el calificador
# urn:aeat:names:specification:schema:lin:. El buzón contestó el 13-10-2026 que
# se escriben juntos, como en `DEL_BOE`; con el valor solo sale un AVISO.
CON_LA_CLAVE_SIN_CALIFICADOR = cambia(DEL_BOE, f"<cbc:Name>{L8}REGI</cbc:Name>",
                                      "<cbc:Name>REGI</cbc:Name>")

# Una segunda línea y su desglose en la categoría N, la del recargo de
# equivalencia en la L4 de la orden, al 5,2%. Medido el 07-10-2026 antes de
# tocar nada: BR-CL-17 y BR-CL-18 en ERROR, e IVA-CATEGORIA-RARA e IVA-TIPO en
# AVISO, porque la lista de 2017 no tiene la N.
_LINEA_N = f"""  <cac:InvoiceLine>
    <cbc:ID>2</cbc:ID>
    <cbc:InvoicedQuantity unitCode="H87">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">0.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Name>Recargo de equivalencia</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>5.2</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>
      <cac:AdditionalItemProperty><cbc:Name>{L8}REGI</cbc:Name><cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>
    </cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">0.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
"""
_SUBTOTAL_N = """    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">0.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>5.2</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>"""
CON_LA_N = cambia(
    cambia(DEL_BOE, "</cac:InvoiceLine>\n</Invoice>", "</cac:InvoiceLine>\n" + _LINEA_N + "</Invoice>"),
    "    </cac:TaxSubtotal>\n  </cac:TaxTotal>", "    </cac:TaxSubtotal>\n" + _SUBTOTAL_N)


def _en_la_categoria(xml: str, viejo: str, nuevo: str) -> str:
    """La línea y el desglose al 21% de una categoría pasados a otra.

    Con el tipo en la búsqueda: la retención de la factura de la orden también
    lleva un `cac:TaxCategory` S, al 15%, y ésa no es del IVA.
    """
    tipo = "</cbc:ID><cbc:Percent>21</cbc:Percent>"
    return cambia(cambia(xml, f"<cac:ClassifiedTaxCategory><cbc:ID>{viejo}{tipo}",
                         f"<cac:ClassifiedTaxCategory><cbc:ID>{nuevo}{tipo}"),
                  f"<cac:TaxCategory><cbc:ID>{viejo}{tipo}", f"<cac:TaxCategory><cbc:ID>{nuevo}{tipo}")


# La D (agencias de viajes) y la F (bienes usados) de la L4 de la orden, con
# la línea y el desglose de la factura de la orden. Antes de publicar solo la
# N tenía prueba: con `_L4_QUE_LA_NORMA_NO_TIENE` reducido a la N, la suite
# entera pasaba y estas dos salían con BR-CL-17 y BR-CL-18 en ERROR (lo vio la
# revisión del 07-10-2026).
CON_LA_D = _en_la_categoria(DEL_BOE, "S", "D")
CON_LA_F = _en_la_categoria(DEL_BOE, "S", "F")
# Y la D con la base del desglose distinta del importe de la línea, que es lo
# que pasa si la base es el margen: el salto de IVA-BASE, medido también en ella.
CON_LA_D_SOBRE_EL_MARGEN = _en_la_categoria(CON_EL_GRUPO_DE_ENTIDADES, "N", "D")

# La referencia catastral con el calificador de L8 delante, como la clave de
# régimen. `_referencias_catastrales` la lee igual que la REGI desde el
# 07-10-2026, y hasta la revisión no lo probaba nadie.
_RCAT_CON_CALIFICADOR = (
    "<cac:AdditionalItemProperty><cbc:Name>urn:aeat:names:specification:schema:lin:RCAT</cbc:Name>"
    "<cbc:Value>9872023VH5797S0001WX</cbc:Value><cbc:ValueQualifier>{}</cbc:ValueQualifier>"
    "</cac:AdditionalItemProperty>")
_REGI_DEL_BOE = (f"<cac:AdditionalItemProperty><cbc:Name>{L8}REGI</cbc:Name><cbc:Value>01</cbc:Value>"
                 "<cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>")
CON_LA_REFERENCIA_CON_CALIFICADOR = cambia(
    DEL_BOE, _REGI_DEL_BOE, _REGI_DEL_BOE + "\n      " + _RCAT_CON_CALIFICADOR.format("01"))


# --- Las variantes de la orden que faltaban ------------------------------------


def adjunto(valor: str, codigo: str = "", descripcion: str = "", uuid: str = "",
            calificador: str = L10) -> str:
    """Un documento justificativo adicional (BG-24) de la lista L10.

    El valor va con el calificador de L10 delante, como lo escribió la AEAT en
    su ejemplo del 02-10-2026, salvo que se pida otro o ninguno: la orden da el
    valor en la fila y el calificador en la lista, sin decir cómo se juntan.
    """
    trozos = [f"    <cbc:ID>{calificador}{valor}</cbc:ID>\n"]
    if uuid:
        trozos.append(f"    <cbc:UUID>{uuid}</cbc:UUID>\n")
    if codigo:
        trozos.append(f"    <cbc:DocumentTypeCode>{codigo}</cbc:DocumentTypeCode>\n")
    if descripcion:
        trozos.append(f"    <cbc:DocumentDescription>{descripcion}</cbc:DocumentDescription>\n")
    return ("  <cac:AdditionalDocumentReference>\n" + "".join(trozos)
            + "  </cac:AdditionalDocumentReference>\n")


def rectificativa_con(*adjuntos: str, tipo: str = "384", base: str = "") -> str:
    """La factura de la orden como rectificativa, con estos BG-24 detrás del QR."""
    return cambia(cambia(base or DEL_BOE, "<cbc:InvoiceTypeCode>380<", f"<cbc:InvoiceTypeCode>{tipo}<"),
                  "  <cac:AccountingSupplierParty>",
                  "".join(adjuntos) + "  <cac:AccountingSupplierParty>")


def con_la_retencion(importe: str, total: str = "") -> str:
    """La factura de la orden con otro importe en su retención (BT-ES-19).

    La suma (BT-ES-17) va con el mismo importe, que es lo que cuadra con una
    sola retención, salvo que se diga otra.
    """
    xml = cambia(DEL_BOE, '<cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>\n'
                          '      <cbc:TaxAmount currencyID="EUR">15.00</cbc:TaxAmount>',
                 '<cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>\n'
                 f'      <cbc:TaxAmount currencyID="EUR">{importe}</cbc:TaxAmount>')
    return cambia(xml, '<cbc:TaxAmount currencyID="EUR">15.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>',
                  f'<cbc:TaxAmount currencyID="EUR">{total or importe}</cbc:TaxAmount>\n'
                  '    <cac:TaxSubtotal>')


def como_abono(xml: str) -> str:
    """La misma factura como abono (CreditNote 381), que el anexo no define."""
    abono = (xml.replace("Invoice-2", "CreditNote-2")
             .replace("<Invoice ", "<CreditNote ").replace("</Invoice>", "</CreditNote>")
             .replace("<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>",
                      "<cbc:CreditNoteTypeCode>381</cbc:CreditNoteTypeCode>")
             .replace("<cac:InvoiceLine>", "<cac:CreditNoteLine>")
             .replace("</cac:InvoiceLine>", "</cac:CreditNoteLine>")
             .replace("<cbc:InvoicedQuantity", "<cbc:CreditedQuantity")
             .replace("</cbc:InvoicedQuantity>", "</cbc:CreditedQuantity>"))
    assert "<Invoice " not in abono and "<cac:InvoiceLine>" not in abono
    return abono


# Una rectificativa por diferencias, como pide la fila BT-3: un BG-24 con el
# tipo y otro con la modalidad, los dos con su código en DocumentTypeCode.
RECTIFICATIVA_DEL_BOE = rectificativa_con(
    adjunto("RECT:TIPO", "R1", "Rectificación por el artículo 80.1 de la LIVA"),
    adjunto("RECT:MODALIDAD", "I"))
# Y por sustitución con una sola factura: hasta cinco BG-24 con los importes
# rectificados, cada uno con su código de L2.C y el importe en la descripción.
CON_LOS_IMPORTES = rectificativa_con(
    adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "S"),
    adjunto("RECT:IMPORTES", "Base", "100.00"), adjunto("RECT:IMPORTES", "Cuota", "21.00"))
# Con el indicador de copia, que la orden deja en `0..1`.
CON_COPIA = cambia(DEL_BOE, "<cbc:ID>F-2026-0101</cbc:ID>",
                   "<cbc:ID>F-2026-0101</cbc:ID>\n  <cbc:CopyIndicator>false</cbc:CopyIndicator>")
# Con una factura referenciada, con su fecha (BT-26).
CON_LA_REFERENCIADA = cambia(
    DEL_BOE, "  <cac:AdditionalDocumentReference>",
    "  <cac:BillingReference><cac:InvoiceDocumentReference>\n"
    "    <cbc:ID>F-2026-0100</cbc:ID><cbc:IssueDate>2026-10-01</cbc:IssueDate>\n"
    "  </cac:InvoiceDocumentReference></cac:BillingReference>\n"
    "  <cac:AdditionalDocumentReference>")
# Con la autorización de facturación, que la orden admite repetida (`0..n`).
CON_LA_AUTORIZACION = cambia(DEL_BOE, "  <cac:AccountingSupplierParty>",
                             adjunto("AUT", uuid="REG015642102461",
                                     descripcion="Autorización facturación máquina vending")
                             + "  <cac:AccountingSupplierParty>")

# El pago entre la operación (BT-7) y la expedición, que es lo que pide la
# fila BT-ES-2. `cbc:TaxPointDate` va detrás del tipo de factura en UBL.
CON_LA_FECHA_DE_LA_OPERACION = cambia(cambia(
    DEL_BOE, "<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>",
    "<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>\n  <cbc:TaxPointDate>2026-10-03</cbc:TaxPointDate>"),
    "<cbc:PaidDate>2026-10-06</cbc:PaidDate>", "<cbc:PaidDate>2026-10-04</cbc:PaidDate>")


def _sin_cuota(xml: str, categoria: str, tipo_linea: str | None, tipo_desglose: str | None,
               exencion: str = "") -> str:
    """La línea y el desglose en una categoría sin cuota, con los totales a juego.

    Con el motivo de la exención en texto, o con su código si se da uno. Sin
    tipo en la línea si es `None`, que es lo que pide la norma en lo no sujeto
    (BR-O-05).
    """
    linea = f"<cbc:Percent>{tipo_linea}</cbc:Percent>" if tipo_linea is not None else ""
    desglose = f"<cbc:Percent>{tipo_desglose}</cbc:Percent>" if tipo_desglose is not None else ""
    motivo = (f"<cbc:TaxExemptionReasonCode>{exencion}</cbc:TaxExemptionReasonCode>" if exencion
              else "<cbc:TaxExemptionReason>Operacion no sujeta</cbc:TaxExemptionReason>")
    xml = cambia(xml, "<cac:ClassifiedTaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent>",
                 f"<cac:ClassifiedTaxCategory><cbc:ID>{categoria}</cbc:ID>{linea}")
    xml = cambia(xml, """      <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent>""",
                 f"""      <cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>{categoria}</cbc:ID>{desglose}{motivo}""")
    xml = cambia(xml, '<cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>',
                 '<cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>')
    xml = cambia(xml, '<cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>',
                 '<cbc:TaxInclusiveAmount currencyID="EUR">100.00</cbc:TaxInclusiveAmount>')
    xml = cambia(xml, "importe=121.00", "importe=100.00")
    return cambia(xml, '<cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>',
                  '<cbc:PayableAmount currencyID="EUR">65.00</cbc:PayableAmount>')


# Lo no sujeto con tipo en el desglose, como pide la fila BT-119, y el
# comprador en BT-47: la norma no deja el NIF-IVA de nadie en una factura con
# líneas no sujetas (BR-O-02). Medido el 11-10-2026: limpia en el validador
# entero, también con el tipo.
CON_LA_NO_SUJETA = _sin_cuota(CON_EL_COMPRADOR_EN_BT47, "O", None, "0")
# Una exenta con un código VATEX-EU, que la fila BT-121 admite.
CON_LA_EXENTA = _sin_cuota(DEL_BOE, "E", "0", "0", "VATEX-EU-132-1I")


# Los impuestos y tasas que no son el IVA, como los escribe la orden: en un
# cargo de línea (BT-ES-22), en un cargo del documento (BG-ES-2) y en una línea
# de cobro (BG-ES-3). Medido el 11-10-2026 antes de escribir las reglas: con el
# código fuera de L9 o sin él, con las dos cuotas del cargo distintas o con
# «IGIC» en el desglose de un cobro, todas salían sin una queja.
def _con_un_cargo_de_linea(codigo: str | None = "RESTO") -> str:
    """Un envase cobrado en la línea, con su código de L9. La línea sigue
    siendo de 100: 90 de precio y 10 del cargo."""
    categoria = ("" if codigo is None else
                 f"<cac:TaxCategory><cac:TaxScheme><cbc:TaxTypeCode>{codigo}</cbc:TaxTypeCode>"
                 "</cac:TaxScheme></cac:TaxCategory>")
    xml = cambia(DEL_BOE, "    <cac:Item>\n      <cbc:Name>Asesoria", f"""    <cac:AllowanceCharge>
      <cbc:ChargeIndicator>true</cbc:ChargeIndicator>
      <cbc:AllowanceChargeReason>Envase</cbc:AllowanceChargeReason>
      <cbc:Amount currencyID="EUR">10.00</cbc:Amount>
      {categoria}
    </cac:AllowanceCharge>
    <cac:Item>
      <cbc:Name>Asesoria""")
    return cambia(xml, '<cbc:PriceAmount currencyID="EUR">100.00</cbc:PriceAmount>',
                  '<cbc:PriceAmount currencyID="EUR">90.00</cbc:PriceAmount>')


def _impuesto(base: str, cuota: str, tipo: str, codigo: str) -> str:
    """Un impuesto o tasa de un cargo del documento (BG-ES-2)."""
    base = f'<cbc:TaxableAmount currencyID="EUR">{base}</cbc:TaxableAmount>' if base else ""
    tipo = f"<cbc:Percent>{tipo}</cbc:Percent>" if tipo else ""
    codigo = f"<cbc:TaxTypeCode>{codigo}</cbc:TaxTypeCode>" if codigo else ""
    return f"""      <cac:TaxSubtotal>
        {base}
        <cbc:TaxAmount currencyID="EUR">{cuota}</cbc:TaxAmount>
        <cac:TaxCategory>{tipo}<cac:TaxScheme>{codigo}</cac:TaxScheme></cac:TaxCategory>
      </cac:TaxSubtotal>
"""


def _con_un_impuesto_en_un_cargo(total: str = "5.00", *impuestos: str) -> str:
    """El impuesto sobre la electricidad cobrado como un cargo de 5 euros, que
    suma al IVA: la base pasa a 105 y la cuota, a 22,05."""
    impuestos = impuestos or (_impuesto("100.00", "5.00", "5", "IEE"),)
    xml = cambia(DEL_BOE, '  <cac:TaxTotal>\n    <cbc:TaxAmount currencyID="EUR">21.00', f"""  <cac:AllowanceCharge>
    <cbc:ChargeIndicator>true</cbc:ChargeIndicator>
    <cbc:AllowanceChargeReason>Impuesto especial sobre la electricidad</cbc:AllowanceChargeReason>
    <cbc:Amount currencyID="EUR">5.00</cbc:Amount>
    <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
    <cac:TaxTotal>
      <cbc:TaxAmount currencyID="EUR">{total}</cbc:TaxAmount>
{"".join(impuestos)}    </cac:TaxTotal>
  </cac:AllowanceCharge>
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">21.00""")
    for viejo, nuevo in (
            ('<cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>\n    <cac:TaxSubtotal>\n'
             '      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>\n'
             '      <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>',
             '<cbc:TaxAmount currencyID="EUR">22.05</cbc:TaxAmount>\n    <cac:TaxSubtotal>\n'
             '      <cbc:TaxableAmount currencyID="EUR">105.00</cbc:TaxableAmount>\n'
             '      <cbc:TaxAmount currencyID="EUR">22.05</cbc:TaxAmount>'),
            ('<cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>\n'
             '    <cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>',
             '<cbc:TaxExclusiveAmount currencyID="EUR">105.00</cbc:TaxExclusiveAmount>\n'
             '    <cbc:TaxInclusiveAmount currencyID="EUR">127.05</cbc:TaxInclusiveAmount>\n'
             '    <cbc:ChargeTotalAmount currencyID="EUR">5.00</cbc:ChargeTotalAmount>'),
            ('<cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>',
             '<cbc:PayableAmount currencyID="EUR">92.05</cbc:PayableAmount>'),
            ("importe=121.00", "importe=127.05")):
        xml = cambia(xml, viejo, nuevo)
    return xml


def _con_el_desglose_del_iedmt(esquema: str = "VAT", categoria: str = "S",
                               cuota: str = "120.00") -> str:
    """El impuesto de matriculación cobrado por cuenta del cliente, con su
    desglose: 6 % sobre 2000."""
    return cambia(DEL_BOE, "  <cac:InvoiceLine>", f"""  <cac:CollectionInvoiceLine>
    <cbc:ID>{L7}IEDMT</cbc:ID>
    <cac:TaxTotal>
      <cbc:TaxAmount currencyID="EUR">{cuota}</cbc:TaxAmount>
      <cac:TaxSubtotal>
        <cbc:TaxableAmount currencyID="EUR">2000.00</cbc:TaxableAmount>
        <cbc:TaxAmount currencyID="EUR">{cuota}</cbc:TaxAmount>
        <cac:TaxCategory><cbc:ID>{categoria}</cbc:ID><cbc:Percent>6</cbc:Percent><cac:TaxScheme><cbc:ID>{esquema}</cbc:ID></cac:TaxScheme></cac:TaxCategory>
      </cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:Item><cbc:Name>Impuesto especial sobre determinados medios de transporte</cbc:Name></cac:Item>
  </cac:CollectionInvoiceLine>
  <cac:InvoiceLine>""")


def _con_la_propiedad(nombre: str) -> str:
    """Otra propiedad del artículo de la línea, detrás de la clave de régimen."""
    return cambia(DEL_BOE, "<cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>",
                  "<cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>\n"
                  f"      <cac:AdditionalItemProperty><cbc:Name>{nombre}</cbc:Name>"
                  "<cbc:Value>Lote 12</cbc:Value></cac:AdditionalItemProperty>")


CON_UN_CARGO_DE_LINEA = _con_un_cargo_de_linea()
CON_UN_IMPUESTO_EN_UN_CARGO = _con_un_impuesto_en_un_cargo()
CON_EL_DESGLOSE_DEL_IEDMT = _con_el_desglose_del_iedmt()
CON_LA_INFORMACION_ADICIONAL = _con_la_propiedad(f"{L8}INFO")


def _detras_de_los_documentos(*trozos: str, base: str = DEL_BOE) -> str:
    """La factura con esto detrás de los BG-24, donde UBL pone también la firma."""
    return cambia(base, "  <cac:AccountingSupplierParty>",
                  "".join(trozos) + "  <cac:AccountingSupplierParty>")


def _contrato(dentro: str) -> str:
    """Un documento justificativo cualquiera, con lo que se le pegue dentro."""
    return ("  <cac:AdditionalDocumentReference>\n    <cbc:ID>Contrato-2026-7</cbc:ID>\n"
            f"    <cac:Attachment>{dentro}</cac:Attachment>\n"
            "  </cac:AdditionalDocumentReference>\n")


def _como_copia_fiel(xml: str) -> str:
    return cambia(xml, "<cbc:ID>F-2026-0101</cbc:ID>",
                  "<cbc:ID>F-2026-0101</cbc:ID>\n  <cbc:CopyIndicator>true</cbc:CopyIndicator>")


def _con_la_firma_envuelta(xml: str) -> str:
    """Una firma envuelta en las extensiones, donde la ponen los programas de
    firma. No se sostiene, y no hace falta: aquí solo cuenta que está."""
    xml = cambia(xml, 'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">',
                 'xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"\n'
                 '         xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"\n'
                 '         xmlns:ds="http://www.w3.org/2000/09/xmldsig#">')
    return cambia(xml, "  <cbc:UBLVersionID>",
                  "  <ext:UBLExtensions><ext:UBLExtension><ext:ExtensionContent>\n"
                  '    <ds:Signature Id="firma"><ds:SignedInfo>\n'
                  '      <ds:CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>\n'
                  '      <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>\n'
                  '      <ds:Reference URI=""><ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>\n'
                  "        <ds:DigestValue>AAAA</ds:DigestValue></ds:Reference>\n"
                  "    </ds:SignedInfo><ds:SignatureValue>AAAA</ds:SignatureValue></ds:Signature>\n"
                  "  </ext:ExtensionContent></ext:UBLExtension></ext:UBLExtensions>\n"
                  "  <cbc:UBLVersionID>")


PDF = ('<cbc:EmbeddedDocumentBinaryObject mimeCode="application/pdf" filename="contrato.pdf">'
       "JVBERi0xLjQK</cbc:EmbeddedDocumentBinaryObject>")
FIRMA_EN_UN_FICHERO = (
    "  <cac:Signature>\n    <cbc:ID>firma</cbc:ID>\n"
    "    <cac:DigitalSignatureAttachment>"
    '<cbc:EmbeddedDocumentBinaryObject mimeCode="application/pkcs7-signature" '
    'filename="firma.p7s">MIAGCSqG</cbc:EmbeddedDocumentBinaryObject>'
    "</cac:DigitalSignatureAttachment>\n  </cac:Signature>\n")
# Lo que la orden deja ir con la factura sin ser un fichero dentro de ella: un
# documento por su dirección, y la firma de la interconectada, que puede ir en
# un fichero dentro de `cac:Signature` (apartado 6 del artículo 3).
CON_UN_DOCUMENTO_EXTERNO = _detras_de_los_documentos(_contrato(
    "<cac:ExternalReference><cbc:URI>https://example.org/contrato.pdf</cbc:URI></cac:ExternalReference>"))
CON_LA_FIRMA_EN_UN_FICHERO = _detras_de_los_documentos(FIRMA_EN_UN_FICHERO)

LAS_DE_LA_ORDEN = {
    "la de la orden": DEL_BOE,
    "con el tercero": CON_EL_TERCERO_DEL_BOE,
    "con suplidos, minoraciones e impuestos": CON_LOS_COBROS_DEL_BOE,
    "el comprador en BT-47": CON_EL_COMPRADOR_EN_BT47,
    "el vendedor en BT-31": CON_EL_VENDEDOR_EN_BT31,
    "el QR sin descripción": CON_EL_QR_SIN_DESCRIPCION,
    "con la categoría N": CON_LA_N,
    "el recargo en el desglose": CON_EL_RECARGO_EN_EL_DESGLOSE,
    "el grupo de entidades": CON_EL_GRUPO_DE_ENTIDADES,
    "AE con el comprador en BT-47": CON_AE_Y_EL_COMPRADOR_EN_BT47,
    "con la categoría D": CON_LA_D,
    "con la categoría F": CON_LA_F,
    "la D sobre el margen": CON_LA_D_SOBRE_EL_MARGEN,
    "la referencia catastral con calificador": CON_LA_REFERENCIA_CON_CALIFICADOR,
    "rectificativa por diferencias": RECTIFICATIVA_DEL_BOE,
    "rectificativa con los importes": CON_LOS_IMPORTES,
    "con el indicador de copia": CON_COPIA,
    "con la factura referenciada": CON_LA_REFERENCIADA,
    "con la autorización": CON_LA_AUTORIZACION,
    "con la fecha de la operación": CON_LA_FECHA_DE_LA_OPERACION,
    "lo no sujeto con su tipo": CON_LA_NO_SUJETA,
    "una exenta con VATEX-EU": CON_LA_EXENTA,
    "un cargo de línea con su código": CON_UN_CARGO_DE_LINEA,
    "un impuesto cobrado como cargo": CON_UN_IMPUESTO_EN_UN_CARGO,
    "el desglose del IEDMT": CON_EL_DESGLOSE_DEL_IEDMT,
    "con información adicional": CON_LA_INFORMACION_ADICIONAL,
    "un documento por su dirección": CON_UN_DOCUMENTO_EXTERNO,
    "la firma en un fichero": CON_LA_FIRMA_EN_UN_FICHERO,
}


# --- Las buenas, en el validador entero -------------------------------------------


class TestLasBuenas:

    @pytest.mark.parametrize("xml", LAS_DE_LA_ORDEN.values(), ids=LAS_DE_LA_ORDEN.keys())
    def test_no_dan_ni_un_error_ni_un_aviso_en_todo_el_validador(self, xml, catalogo):
        assert limpia(xml, catalogo) == []

    def test_dice_en_notas_lo_que_ha_aceptado_y_con_que_base(self):
        informe = factura.validar(DEL_BOE.encode("utf-8"))
        # FIRMA-POR-FUERA, desde el 21-10-2026: va sin firma dentro, y si se
        # emitiera por una plataforma privada el art. 7.3 del RD la pediría.
        assert {i.codigo for i in informe.notas} == {
            "SPFE-ALCANCE", "SPFE-COPIA", "SPFE-IMPORTE-PAGADO", "SPFE-TOTAL-A-PAGAR",
            "FIRMA-POR-FUERA"}

    def test_la_nota_del_alcance_sale_siempre_y_dice_con_que_se_ha_medido(self):
        """Hasta el 07-10-2026 decía que el anexo «no está publicado en el BOE».

        Del 07-10-2026 al 11-10-2026 se llamaba SPFE-BORRADOR y decía la
        mezcla: la orden publicada, lo que de ella ya se admitía, y que el
        resto seguía midiendo el borrador de abril. Desde ese día se mide con
        la orden, y la nota dice lo que de ella no se mide.
        """
        nota = la(DEL_BOE, "SPFE-ALCANCE")
        assert nota.gravedad == NOTA
        assert "HAC/1028/2026" in nota.mensaje and "05-10-2026" in nota.mensaje
        assert "no quiere decir que la factura cumpla la orden" in nota.mensaje
        assert "borrador" not in nota.mensaje
        assert "no está publicad" not in nota.mensaje
        assert nota.encontrado == ESPECIFICACION

    def test_la_nota_y_el_glosario_dicen_la_misma_lista(self):
        """Estaba escrita dos veces y ya no decía lo mismo: el glosario se había
        dejado la clave de régimen. Lo vio el revisor de promesas el 07-10-2026,
        antes de publicar."""
        cosas = solucion_publica.LO_QUE_TODAVIA_NO_SE_MIDE
        nota = la(DEL_BOE, "SPFE-ALCANCE").mensaje
        ficha = glosario.CODIGOS["SPFE-ALCANCE"]
        if not cosas:
            # Vacía desde el 11-10-2026: ninguna de las dos dice que falte algo.
            assert "todavía no se mide" not in nota and "todavía no se mide" not in ficha
            return
        frase = cosas[0] if len(cosas) == 1 else "; ".join(cosas[:-1]) + "; y " + cosas[-1]
        assert frase in nota
        assert frase in ficha

    def test_la_nota_nombra_tambien_lo_que_no_se_puede_comprobar(self):
        """La política de privacidad y la portada dicen que lo que no se mide lo
        dice el informe, y `NO_SE_COMPRUEBA` no llegaba a él: el recargo en la
        cuota, los códigos de exención de BT-195, las menciones «REG». Lo vio
        el revisor de promesas el 11-10-2026. La nota los nombra, y la ficha
        dice el porqué de cada uno letra a letra."""
        nota = la(DEL_BOE, "SPFE-ALCANCE").mensaje
        ficha = glosario.CODIGOS["SPFE-ALCANCE"]
        for que, porque in solucion_publica.NO_SE_COMPRUEBA.items():
            assert que.lower() in nota.lower(), que
            assert f"{que}: {porque}" in ficha, que

    def test_la_nota_dice_que_lo_que_la_orden_deja_a_la_sede_no_se_mide(self):
        """Con `LO_QUE_TODAVIA_NO_SE_MIDE` vacía, el 11-10-2026, la nota dejaba
        de decir que faltaba algo, y la orden deja a la Sede las
        especificaciones técnicas, la volumetría y el tamaño máximo de las
        copias fieles, que no son el anexo."""
        nota = la(DEL_BOE, "SPFE-ALCANCE").mensaje
        assert "las especificaciones técnicas" in nota
        assert "Sede electrónica" in solucion_publica.NO_SE_COMPRUEBA["Especificaciones técnicas"]

    def test_la_nota_no_se_limita_a_lo_que_enumera(self):
        """Decía «no quiere decir que la factura cumpla la orden en eso», y lo
        que no enumeraba tampoco estaba medido entero."""
        assert la(DEL_BOE, "SPFE-ALCANCE").mensaje.endswith(
            "no quiere decir que la factura cumpla la orden.")
        assert "en eso" not in glosario.CODIGOS["SPFE-ALCANCE"]

    def test_cada_cosa_que_no_se_mide_nombra_una_fila_o_una_lista_de_la_orden(self):
        """Para que la nota no hable de algo que la orden no pide.

        Y que no la mida nadie: una fila de la lista con su regla escrita
        sería decir que no se comprueba lo que sí, que también es prometer mal.
        """
        filas = {c.id for c in cius_es.CAMPOS}
        for cosa in solucion_publica.LO_QUE_TODAVIA_NO_SE_MIDE:
            nombradas = re.findall(r"\b(B[GT]-(?:ES-)?\d+|L\d+)\b", cosa)
            assert nombradas, cosa
            for nombre in nombradas:
                assert nombre in filas or nombre in cius_es.LISTAS, (cosa, nombre)
        # Los identificadores salen de la propia lista. Hasta el 11-10-2026 iban
        # escritos aquí, y cada tanda que medía una cosa tenía que acordarse de
        # quitarla de los dos sitios.
        codigo = pathlib.Path(solucion_publica.__file__).read_text(encoding="utf-8")
        reglas = codigo[codigo.index("# --- Las reglas"):]
        for cosa in solucion_publica.LO_QUE_TODAVIA_NO_SE_MIDE:
            for identificador in re.findall(r"\bB[GT]-(?:ES-)?\d+\b", cosa):
                assert f'"{identificador}"' not in codigo, identificador
                assert f"({identificador})" not in reglas, identificador

    def test_el_alcance_dice_el_anexo_solo_si_hay_una_factura_que_lo_declara(self, tmp_path):
        """«Sin errores» en una factura de la solución pública quiere decir
        también que cumple lo que del anexo se mide, y la frase que dice qué se
        ha mirado lo tiene que decir. En un lote sin ninguna no se ha mirado, y
        no lo dice."""
        (tmp_path / "orden.xml").write_text(DEL_BOE, encoding="utf-8")
        con = factura.validar_lote([tmp_path / "orden.xml"]).alcance()
        # «Parte de»: lo que la orden pide y no se mide lo dice la nota, y la
        # línea de alcance manda a ella. Hasta el 11-10-2026 decía «lo que ya
        # pedía el borrador de abril».
        assert "parte de lo que el anexo I de la solución pública pide" in con
        assert "SPFE-ALCANCE" in con and "borrador" not in con
        (tmp_path / "otra.xml").write_text(cambia(DEL_BOE, ESPECIFICACION, "urn:cen.eu:en16931:2017"),
                                           encoding="utf-8")
        sin = factura.validar_lote([tmp_path / "otra.xml"]).alcance()
        assert "anexo I" not in sin
        # Ni con un abono que declara la orden: el anexo solo define facturas y
        # no se le mide con él, y hasta el 11-10-2026 la línea decía que sí.
        (tmp_path / "abono.xml").write_text(como_abono(DEL_BOE), encoding="utf-8")
        assert "anexo I" not in factura.validar_lote([tmp_path / "abono.xml"]).alcance()

    def test_llevan_la_etiqueta_del_anexo_y_no_la_del_real_decreto(self):
        assert factura.origen(Incidencia("SPFE-NIF", ERROR, "")) == factura.SOLUCION_PUBLICA
        detalle = factura.validar(cambia(DEL_BOE, f"<cbc:ProfileID>{PROCESO}</cbc:ProfileID>", "")
                                  .encode("utf-8")).detalle(norma=factura.origen)
        # Contra un literal, y no contra la constante: compararla consigo misma
        # no fijaba nada, y la etiqueta podía volver a decir «borrador» sin que
        # ninguna prueba lo viera (lo encontró la revisión del 07-10-2026).
        assert "[SPFE-PROCESO · Anexo I]" in detalle
        assert "borrador" not in factura.SOLUCION_PUBLICA


# --- A quién se aplica ---------------------------------------------------------


class TestLosCalificadores:
    """Los valores de L7, L8 y L10, con el calificador de su lista delante.

    Las filas dan el valor solo y la lista el calificador aparte; hasta el
    13-10-2026 valían las dos formas sin decir nada. Ese día el buzón contestó
    que se escriben juntos, en las tres listas. Sin él, un AVISO, y lo demás se
    mide igual.
    """

    SIN = {
        "la retención (L7)": (CON_LA_RETENCION_SIN_CALIFICADOR, "RETE"),
        "la clave de régimen (L8)": (CON_LA_CLAVE_SIN_CALIFICADOR, "REGI"),
        "el QR (L10)": (cambia(DEL_BOE, f"<cbc:ID>{L10}QR</cbc:ID>", "<cbc:ID>QR</cbc:ID>"), "QR"),
        "la autorización (L10)": (
            rectificativa_con(adjunto("AUT", uuid="REG015642102461", calificador=""), tipo="380"),
            "AUT"),
    }

    @pytest.mark.parametrize("nombre", SIN)
    def test_sin_el_calificador_es_un_aviso_y_nada_mas(self, nombre):
        xml, valor = self.SIN[nombre]
        aviso = la(xml, "SPFE-CALIFICADOR")
        assert aviso.gravedad == AVISO and aviso.encontrado == valor
        assert aviso.esperado.endswith(":" + valor) and aviso.esperado != valor
        assert "13-10-2026" in aviso.mensaje
        assert limpia(xml) == [("SPFE-CALIFICADOR", "Valores de las listas L7, L8 y L10")]

    def test_uno_por_factura_con_todos(self):
        todos = cambia(CON_LA_RETENCION_SIN_CALIFICADOR, f"<cbc:Name>{L8}REGI</cbc:Name>",
                       "<cbc:Name>REGI</cbc:Name>")
        aviso = la(todos, "SPFE-CALIFICADOR")
        assert aviso.encontrado == "RETE, REGI"
        assert aviso.mensaje.startswith("RETE y REGI van sin el calificador")

    def test_con_el_calificador_no_hay_aviso(self):
        assert las(DEL_BOE, "SPFE-CALIFICADOR") == []
        assert las(EJEMPLO, "SPFE-CALIFICADOR") == []

    def test_lo_que_no_es_de_ninguna_lista_no_es_un_calificador_que_falta(self):
        """Eso lo dice la regla de cada campo: aquí no se repite."""
        otra = cambia(DEL_BOE, f"{L7}RETE<", "RETENCION<")
        assert las(otra, "SPFE-CALIFICADOR") == []


class TestAQuienSeAplica:

    def test_una_factura_que_no_la_declara_no_se_mide_con_el_anexo(self):
        """Y entonces BR-CO-16 sí salta con la retención: sin la solución
        pública no hay anexo que diga que el total a pagar la resta."""
        sin = cambia(DEL_BOE, ESPECIFICACION, "urn:cen.eu:en16931:2026")
        assert spfe(sin) == []
        informe = factura.validar(sin.encode("utf-8"))
        assert not [i for i in informe.incidencias if i.codigo.startswith("SPFE-")]
        assert "BR-CO-16" in {i.codigo for i in informe.errores}

    def test_con_lineas_de_cobro_br_co_16_no_se_da_por_mala(self):
        """El total a pagar resta la retención, como dice la orden. BR-CO-16
        no sale, y la nota dice que no se ha mirado."""
        informe = factura.validar(DEL_BOE.encode("utf-8"))
        assert "BR-CO-16" not in {i.codigo for i in informe.incidencias}
        nota = next(i for i in informe.notas if i.codigo == "SPFE-TOTAL-A-PAGAR")
        assert "BR-CO-16" in nota.mensaje and nota.encontrado == "86.00"

    def test_sin_lineas_de_cobro_br_co_16_se_comprueba_como_siempre(self):
        sin_cobros = quita(quita(DEL_BOE, "  <cac:CollectionInvoiceLine>", "</cac:CollectionInvoiceLine>\n"),
                           "  <cac:WithholdingTaxTotal>", "</cac:WithholdingTaxTotal>\n")
        informe = factura.validar(sin_cobros.encode("utf-8"))
        assert "SPFE-TOTAL-A-PAGAR" not in {i.codigo for i in informe.incidencias}
        assert "BR-CO-16" in {i.codigo for i in informe.errores}
        cuadrada = cambia(sin_cobros, ">86.00<", ">101.00<")
        assert limpia(cuadrada) == []

    @pytest.mark.parametrize("perfil", [ESPECIFICACION, DEL_BORRADOR], ids=["la orden", "el borrador"])
    def test_otra_sintaxis_que_la_declara_recibe_un_aviso_y_nada_mas(self, perfil):
        with open("ejemplos/cii-A-0001.xml", encoding="utf-8") as f:
            cii = f.read()
        cii = cambia(cii, "<ram:ID>urn:cen.eu:en16931:2017</ram:ID>", f"<ram:ID>{perfil}</ram:ID>")
        incidencias = spfe(cii)
        assert [(i.codigo, i.gravedad) for i in incidencias] == [("SPFE-SINTAXIS", AVISO)]
        assert "CII" in incidencias[0].mensaje
        assert "dice ser de la solución pública" in incidencias[0].mensaje

    def test_un_abono_se_queja_de_ser_abono_y_no_se_mide_lo_demas(self):
        abono = (DEL_BOE.replace("Invoice-2", "CreditNote-2")
                 .replace("<Invoice ", "<CreditNote ").replace("</Invoice>", "</CreditNote>")
                 .replace("InvoiceTypeCode>380<", "CreditNoteTypeCode>381<")
                 .replace("</cbc:InvoiceTypeCode>", "</cbc:CreditNoteTypeCode>"))
        assert codigos(abono) == {"SPFE-TIPO-DE-FACTURA"}
        assert la(abono, "SPFE-TIPO-DE-FACTURA").encontrado == "CreditNote 381"
        # Ni la nota del alcance, que decía «se mide con el anexo I» junto a la
        # queja que dice que no se ha comprobado. Lo vio el revisor de promesas
        # el 11-10-2026.
        assert las(abono, "SPFE-ALCANCE") == []

    def test_otro_identificador_de_la_aeat_se_avisa_y_no_se_mide(self, tmp_path):
        """No se le aplica el anexo, porque no dice ser lo que el anexo define.
        Pero no se calla, que es lo que pasó con el del ejemplo del 02-10-2026
        hasta que se midió."""
        otro = "urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:2.0.0:extended"
        tercero = cambia(DEL_BOE, ESPECIFICACION, otro)
        quejas = spfe(tercero)
        assert [(q.codigo, q.gravedad) for q in quejas] == [("SPFE-ESPECIFICACION", AVISO)]
        assert quejas[0].encontrado == otro and quejas[0].esperado == ESPECIFICACION
        assert "no se han comprobado" in quejas[0].mensaje and "ejemplo" not in quejas[0].mensaje
        (tmp_path / "tercero.xml").write_text(tercero, encoding="utf-8")
        assert "anexo I" not in factura.validar_lote([tmp_path / "tercero.xml"]).alcance()
        with open("ejemplos/cii-A-0001.xml", encoding="utf-8") as f:
            cii = cambia(f.read(), "<ram:ID>urn:cen.eu:en16931:2017</ram:ID>", f"<ram:ID>{otro}</ram:ID>")
        assert [(q.codigo, q.gravedad) for q in spfe(cii)] == [("SPFE-ESPECIFICACION", AVISO)]

    def test_lo_que_no_nombra_a_la_aeat_sigue_sin_nada(self):
        assert spfe(cambia(DEL_BOE, ESPECIFICACION, "urn:cen.eu:en16931:2026")) == []


# --- Lo que solo decía el borrador ------------------------------------------------


class TestLoQueSoloDeciaElBorrador:
    """Lo que el borrador de abril admitía y la orden no, en ERROR.

    Hasta el 11-10-2026 se seguía aceptando: la primera tanda del BOE, el
    07-10-2026, solo dejó de condenar lo que la orden admite. Una factura
    escrita con el borrador sale ahora con todo lo que tiene que cambiar.
    """

    def con_el_borrador(self):
        """La factura de la orden, con todo lo que en abril se escribía distinto."""
        xml = cambia(DEL_BOE, ESPECIFICACION, DEL_BORRADOR)
        xml = cambia(xml, f"<cbc:ProfileID>{PROCESO}<", f"<cbc:ProfileID>{PROCESO_DEL_BORRADOR}<")
        xml = cambia(xml, f"{L7}RETE<", f"{URN_DEL_BORRADOR}RETE<")
        xml = cambia(xml, f"{L10}QR<", f"{URN_DEL_BORRADOR}QR<")
        xml = cambia(xml, "<cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA<",
                     "<cbc:Value>18</cbc:Value><cbc:ValueQualifier>IVA<")
        return xml

    def test_se_le_mide_y_sale_todo_lo_que_tiene_que_cambiar(self):
        assert codigos(self.con_el_borrador()) == {
            "SPFE-ESPECIFICACION", "SPFE-PROCESO", "SPFE-LINEA-DE-COBRO",
            "SPFE-RETENCION", "SPFE-CLAVE-DE-REGIMEN"}

    def test_la_especificacion_del_borrador_es_error_y_dice_de_donde_sale(self):
        queja = la(self.con_el_borrador(), "SPFE-ESPECIFICACION")
        assert queja.gravedad == ERROR and queja.esperado == ESPECIFICACION
        assert "borrador de abril" in queja.mensaje and "BT-24" in queja.mensaje
        # Y la nota del alcance sale igual: se le ha medido con el anexo.
        assert la(self.con_el_borrador(), "SPFE-ALCANCE").encontrado == DEL_BORRADOR

    def test_el_borrador_con_otra_edicion_tambien(self):
        otra = cambia(DEL_BOE, ESPECIFICACION, DEL_BORRADOR.replace("2026#", "2017#"))
        queja = la(otra, "SPFE-ESPECIFICACION")
        assert queja.gravedad == ERROR and "no con su valor entero" in queja.mensaje

    def test_el_proceso_del_borrador_es_error(self):
        queja = la(self.con_el_borrador(), "SPFE-PROCESO")
        assert queja.gravedad == ERROR and queja.esperado == PROCESO
        assert "borrador de abril" in queja.mensaje

    @pytest.mark.parametrize("clave", ["18", "19", "20"])
    def test_las_claves_18_19_y_20_del_iva_ya_no_valen(self, clave):
        """El recargo, la agricultura y el régimen simplificado: fuera de la L3A."""
        xml = cambia(DEL_BOE, "<cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA<",
                     f"<cbc:Value>{clave}</cbc:Value><cbc:ValueQualifier>IVA<")
        queja = la(xml, "SPFE-CLAVE-DE-REGIMEN")
        assert queja.gravedad == ERROR and queja.encontrado == f"{clave} de IVA"
        assert "la 18, la 19 y la 20" in queja.mensaje

    @pytest.mark.parametrize("valor", ["REEQ", "REGE"])
    @pytest.mark.parametrize("calificador", [L7, URN_DEL_BORRADOR, ""],
                             ids=["el de la orden", "la URN de abril", "a secas"])
    def test_las_lineas_del_recargo_y_del_grupo_ya_no_valen(self, valor, calificador):
        """La orden pone los dos regímenes en el desglose, con la categoría N."""
        linea = (f"  <cac:CollectionInvoiceLine>\n    <cbc:ID>{calificador}{valor}</cbc:ID>\n"
                 "    <cac:Item><cbc:Name>De abril</cbc:Name></cac:Item>\n  </cac:CollectionInvoiceLine>\n")
        xml = cambia(DEL_BOE, "  <cac:InvoiceLine>", linea + "  <cac:InvoiceLine>")
        queja = la(xml, "SPFE-LINEA-DE-COBRO")
        assert queja.gravedad == ERROR and queja.encontrado == f"{calificador}{valor}"
        assert "borrador de abril" in queja.mensaje and "categoría N" in queja.mensaje

    def test_el_qr_con_la_urn_de_abril_no_es_el_qr(self):
        """Ni se le pide la dirección ni cuenta para estar repetido, pero se dice.

        Con el identificador de la orden y el QR escrito con la URN de abril,
        sin dirección, no salía nada: la factura parecía llevar un QR bien
        hecho y para la orden no lleva ninguno. Lo vio el revisor de promesas
        el 11-10-2026. Es una nota y no un fallo, porque un BG-24 puede llevar
        cualquier identificador y la orden no obliga al QR.
        """
        sin_direccion = cambia(cambia(DEL_BOE, f"{L10}QR<", f"{URN_DEL_BORRADOR}QR<"),
                               f"<cbc:UUID>{QR_URL}</cbc:UUID>", "")
        nota = la(sin_direccion, "SPFE-QR")
        assert nota.gravedad == NOTA and nota.encontrado == f"{URN_DEL_BORRADOR}QR"
        assert "borrador de abril" in nota.mensaje and nota.esperado == f"{L10}QR o QR"

    def test_la_extension_de_rectificativas_de_abril_no_dice_que_se_rectifica(self):
        extension = """  <ext:UBLExtensions><ext:UBLExtension>
    <cbc:ID>urn:aeat:names:specification:ubl:schema:ext:id:RECT</cbc:ID>
    <ext:ExtensionContent><aeat:InvoiceExtension xmlns:aeat="urn:glosa:pruebas:aeat"><aeat:Correction>
      <aeat:Category>R4</aeat:Category><aeat:Method>S</aeat:Method>
    </aeat:Correction></aeat:InvoiceExtension></ext:ExtensionContent>
  </ext:UBLExtension></ext:UBLExtensions>
"""
        con_la_extension = cambia(
            rectificativa_con().replace(
                "<Invoice xmlns=", '<Invoice xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:'
                                   'CommonExtensionComponents-2" xmlns=', 1),
            "  <cbc:UBLVersionID>", extension + "  <cbc:UBLVersionID>")
        queja = la(con_la_extension, "SPFE-RECTIFICATIVA")
        assert queja.gravedad == ERROR
        assert queja.encontrado == "falta el tipo de rectificativa y la modalidad de rectificación"

    def test_ninguna_regla_del_borrador_sigue_existiendo(self):
        """El recargo y el grupo de entidades tenían regla propia. Ya no."""
        assert "SPFE-RECARGO-DE-EQUIVALENCIA" not in glosario.CODIGOS
        assert "SPFE-GRUPO-DE-ENTIDADES" not in glosario.CODIGOS
        assert "SPFE-BORRADOR" not in glosario.CODIGOS
        codigo = pathlib.Path(solucion_publica.__file__).read_text(encoding="utf-8")
        for viejo in ("SPFE-RECARGO", "SPFE-GRUPO", '"SPFE-BORRADOR"', "_COBROS =",
                      "LO_QUE_YA_SE_ADMITE"):
            assert viejo not in codigo, viejo


# --- Cada regla, rota ------------------------------------------------------------


class TestCabecera:

    def test_la_especificacion_tiene_que_ser_el_valor_entero(self):
        assert las(DEL_BOE, "SPFE-ESPECIFICACION") == []

    def test_el_proceso_falta_o_es_otro(self):
        sin = cambia(DEL_BOE, f"<cbc:ProfileID>{PROCESO}</cbc:ProfileID>", "")
        queja = la(sin, "SPFE-PROCESO")
        assert queja.gravedad == ERROR and queja.encontrado == "(falta)"
        otro = cambia(DEL_BOE, "profile:B2B<", "profile:B2G<")
        assert codigos(otro) == {"SPFE-PROCESO"}
        assert la(otro, "SPFE-PROCESO").encontrado.endswith("B2G")

    def test_el_proceso_es_el_que_no_lleva_ubl(self):
        """El buzón contestó el 13-10-2026 que vale el del ejemplo del 02-10-2026,
        sin ubl:. Hasta ese día era al revés: limpio el del BOE, y el del
        ejemplo en NOTA."""
        assert PROCESO == "urn:aeat:names:specification:schema:profile:B2B"
        assert PROCESO_DEL_BOE == "urn:aeat:names:specification:ubl:schema:profile:B2B"
        assert las(DEL_BOE, "SPFE-PROCESO") == []

    def test_el_proceso_del_boe_es_aviso_y_pide_el_que_vale(self):
        """Es lo que dice el BOE, y la corrección solo está en el anexo del
        portal de la AEAT, que no es la orden: ni limpio ni error."""
        del_boe = cambia(DEL_BOE, PROCESO, PROCESO_DEL_BOE)
        aviso = la(del_boe, "SPFE-PROCESO")
        assert aviso.gravedad == AVISO and aviso.esperado == PROCESO
        assert "13-10-2026" in aviso.mensaje and "texto publicado" in aviso.mensaje
        # No dijo que lo corrija en el anexo, y su anexo 2.0 lo lleva con ubl:.
        # Lo corrigió el anexo del portal del 21-10-2026, y eso es lo que se dice.
        assert "Portal" not in aviso.mensaje and "portal el 21-10-2026" in aviso.mensaje
        assert codigos(del_boe) == {"SPFE-PROCESO"}

    def test_si_la_fila_bt_23_cambia_el_modulo_no_se_importa(self, monkeypatch):
        """El valor va escrito a mano porque la fila dice otro. El día que la
        fila cambie, o es la corrección o es otra cosa, y hay que mirarla."""
        # Al recargar, la clase AnexoCambiado es otra: se reconoce por el nombre,
        # como en `_negativa`.
        monkeypatch.setattr(cius_es, "PROCESO", PROCESO)
        negativa = None
        try:
            importlib.reload(solucion_publica)
        except LookupError as error:
            negativa = error
        finally:
            monkeypatch.undo()
            importlib.reload(solucion_publica)
        assert type(negativa).__name__ == "AnexoCambiado" and "BT-23" in str(negativa)

    def test_sin_indicador_de_copia_es_el_original_y_se_dice(self):
        """En abril era obligatorio; en la orden, `0..1` y «sin informar: original»."""
        nota = la(DEL_BOE, "SPFE-COPIA")
        assert nota.gravedad == NOTA
        assert "original" in nota.mensaje and "apartado 3 del artículo 4" in nota.mensaje
        assert las(CON_COPIA, "SPFE-COPIA") == []
        assert las(cambia(CON_COPIA, ">false</cbc:CopyIndicator>", ">true</cbc:CopyIndicator>"),
                   "SPFE-COPIA") == []

    def test_el_381_no_existe_en_la_solucion_publica(self):
        queja = la(cambia(DEL_BOE, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>381<"),
                   "SPFE-TIPO-DE-FACTURA")
        assert "384" in queja.mensaje and queja.encontrado == "381"
        assert "RECT:TIPO" in queja.mensaje and "BT-3" in queja.mensaje and "BG-24" in queja.mensaje
        assert "extensión" not in queja.mensaje
        assert codigos(cambia(DEL_BOE, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>386<")) == {
            "SPFE-TIPO-DE-FACTURA"}

    def test_un_tipo_que_ni_la_norma_admite_se_lo_deja_a_br_cl_01(self):
        malo = cambia(DEL_BOE, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>999<")
        assert "SPFE-TIPO-DE-FACTURA" not in codigos(malo)
        assert "BR-CL-01" in {i.codigo for i in factura.validar(malo.encode("utf-8")).errores}

    def test_la_moneda_del_iva_es_el_euro(self):
        en_dolares = cambia(DEL_BOE, "<cbc:DocumentCurrencyCode>EUR<", "<cbc:DocumentCurrencyCode>USD<")
        assert la(en_dolares, "SPFE-MONEDA-DEL-IVA").encontrado == "(falta)"
        con_euro = cambia(en_dolares, "<cbc:DocumentCurrencyCode>USD</cbc:DocumentCurrencyCode>",
                          "<cbc:DocumentCurrencyCode>USD</cbc:DocumentCurrencyCode>"
                          "<cbc:TaxCurrencyCode>EUR</cbc:TaxCurrencyCode>")
        assert "SPFE-MONEDA-DEL-IVA" not in codigos(con_euro)
        otra = cambia(DEL_BOE, "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>",
                      "<cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>"
                      "<cbc:TaxCurrencyCode>USD</cbc:TaxCurrencyCode>")
        assert la(otra, "SPFE-MONEDA-DEL-IVA").encontrado == "USD"

    def test_el_importe_pagado_se_admite_y_se_dice_lo_que_no_se_ve(self):
        """Abril lo admitía solo a cero; la orden, salvo anticipos con IVA devengado."""
        nota = la(DEL_BOE, "SPFE-IMPORTE-PAGADO")
        assert nota.gravedad == NOTA and nota.encontrado == "20.00"
        assert "75.Dos" in nota.mensaje
        cero = cambia(DEL_BOE, '<cbc:PrepaidAmount currencyID="EUR">20.00<',
                      '<cbc:PrepaidAmount currencyID="EUR">0.00<')
        assert las(cero, "SPFE-IMPORTE-PAGADO") == []

    @pytest.mark.parametrize("escrito", ["NaN", "1E+3"])
    def test_lo_que_no_es_un_numero_no_se_anota(self, escrito):
        # «NaN» no es igual a cero y salía acusado de no serlo, encima de la
        # queja del esquema. Un importe que no es un número es cosa del XSD.
        raro = cambia(DEL_BOE, '<cbc:PrepaidAmount currencyID="EUR">20.00<',
                      f'<cbc:PrepaidAmount currencyID="EUR">{escrito}<')
        assert las(raro, "SPFE-IMPORTE-PAGADO") == []


_PAGO = "<cbc:PaidDate>2026-10-06</cbc:PaidDate>"


class TestLaFechaDePago:
    """BT-ES-2: no después de la expedición, no antes de la operación, y una.

    Hasta el 11-10-2026 no se medía, y la nota del alcance lo decía. Medido ese
    día antes de escribir la regla: una fecha posterior a la expedición, una
    anterior a la operación y dos fechas salían sin una queja.
    """

    def test_la_del_dia_de_la_expedicion_vale(self):
        assert las(DEL_BOE, "SPFE-FECHA-DE-PAGO") == []
        del_dia_de_la_operacion = cambia(CON_LA_FECHA_DE_LA_OPERACION, "<cbc:PaidDate>2026-10-04<",
                                         "<cbc:PaidDate>2026-10-03<")
        assert las(del_dia_de_la_operacion, "SPFE-FECHA-DE-PAGO") == []

    def test_despues_de_la_operacion_vale_y_no_libera_de_comunicar_el_pago(self):
        """La fila admite del día de la operación al de la expedición; el
        apartado 4 del artículo 7 libera de comunicar el pago solo si coincide
        con la operación. Hasta que se cotejó con el artículo, el 11-10-2026,
        la ficha decía que con la fecha no había que comunicarlo, sin más."""
        nota = la(CON_LA_FECHA_DE_LA_OPERACION, "SPFE-FECHA-DE-PAGO")
        assert nota.gravedad == NOTA and nota.encontrado == "2026-10-04"
        assert "artículo 7" in nota.mensaje and "comunicar el pago igual" in nota.mensaje

    def test_despues_de_la_expedicion_no(self):
        queja = la(cambia(DEL_BOE, _PAGO, "<cbc:PaidDate>2026-10-07</cbc:PaidDate>"),
                   "SPFE-FECHA-DE-PAGO")
        assert queja.gravedad == ERROR and queja.encontrado == "2026-10-07"
        assert queja.esperado == "el 06-10-2026 o antes" and "BT-ES-2" in queja.mensaje

    def test_antes_de_la_operacion_no(self):
        antes = cambia(CON_LA_FECHA_DE_LA_OPERACION, "<cbc:PaidDate>2026-10-04<",
                       "<cbc:PaidDate>2026-10-02<")
        queja = la(antes, "SPFE-FECHA-DE-PAGO")
        assert queja.gravedad == ERROR and queja.esperado == "del 03-10-2026 al 06-10-2026"
        assert "anticipo" in queja.mensaje

    def test_sin_bt7_la_operacion_es_del_dia_de_la_expedicion(self):
        """La orden pide BT-7 solo cuando la operación es de otro día."""
        queja = la(cambia(DEL_BOE, _PAGO, "<cbc:PaidDate>2026-10-05</cbc:PaidDate>"),
                   "SPFE-FECHA-DE-PAGO")
        assert queja.gravedad == ERROR and "BT-7" in queja.mensaje

    def test_con_un_periodo_no_se_compara_y_se_dice(self, catalogo):
        """En una recapitulativa las operaciones son del periodo, y la orden no
        dice con qué fecha de él se compara: nota, y no fallo."""
        con_periodo = cambia(cambia(DEL_BOE, _PAGO, "<cbc:PaidDate>2026-10-05</cbc:PaidDate>"),
                             "  <cac:AdditionalDocumentReference>",
                             "  <cac:InvoicePeriod><cbc:StartDate>2026-09-01</cbc:StartDate>"
                             "<cbc:EndDate>2026-09-30</cbc:EndDate></cac:InvoicePeriod>\n"
                             "  <cac:AdditionalDocumentReference>")
        nota = la(con_periodo, "SPFE-FECHA-DE-PAGO")
        assert nota.gravedad == NOTA and "BG-14" in nota.mensaje
        assert limpia(con_periodo, catalogo) == []

    def test_una_como_mucho(self):
        dos = cambia(DEL_BOE, "</cac:PrepaidPayment>",
                     "</cac:PrepaidPayment>\n  <cac:PrepaidPayment>"
                     '<cbc:PaidAmount currencyID="EUR">0.00</cbc:PaidAmount>'
                     f"{_PAGO}</cac:PrepaidPayment>")
        queja = la(dos, "SPFE-FECHA-DE-PAGO")
        assert queja.esperado == "una como mucho" and queja.encontrado == "2026-10-06, 2026-10-06"

    def test_una_fecha_mal_escrita_es_cosa_del_esquema(self):
        assert las(cambia(DEL_BOE, _PAGO, "<cbc:PaidDate>06/10/2026</cbc:PaidDate>"),
                   "SPFE-FECHA-DE-PAGO") == []


class TestRectificativa:
    """La fila BT-3 de la orden, y los cinco documentos de la lista L10.

    Hasta el 11-10-2026, salvo la 384 que no decía nada, todo esto salía en
    NOTA o en AVISO, porque el sitio del código lo enseñaba un ejemplo de la
    AEAT y no un texto publicado. La orden lo escribe, y sale en ERROR.
    """

    def test_los_importes_con_la_modalidad_i_son_aviso(self):
        """El grupo es para «los casos en los que se proceda a la rectificación
        por sustitución». Con I pasaba sin una palabra: lo midió el auditor el
        11-10-2026. Aviso y no error, porque la orden lo describe y no lo
        prohíbe con una regla."""
        con_i = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "I"),
                                  adjunto("RECT:IMPORTES", "Base", "100.00"))
        aviso = la(con_i, "SPFE-RECTIFICATIVA")
        assert aviso.gravedad == AVISO and aviso.encontrado == "I"
        assert "sustitución" in aviso.mensaje

    @pytest.mark.parametrize("cuantos", [2, 4, 5])
    def test_un_codigo_repetido_es_aviso(self, cuantos):
        """La fila BT-3 dice hasta tres grupos y el grupo es `0..5`; hasta el
        13-10-2026, de cuatro a cinco salía una NOTA. La AEAT contestó ese día
        que el grupo pasa a `0..1`, con un ejemplo de uno por código, y el anexo
        de su portal del 21-10-2026 le da `0..3`."""
        xml = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "S"),
                                *[adjunto("RECT:IMPORTES", "Base", "100.00")] * cuantos)
        aviso = la(xml, "SPFE-RECTIFICATIVA")
        assert aviso.gravedad == AVISO and aviso.encontrado == f"Base {cuantos} veces"
        assert "0..3" in aviso.mensaje and "21-10-2026" in aviso.mensaje
        assert "0..1" not in aviso.mensaje

    def test_uno_por_codigo_no_dice_nada_como_en_el_ejemplo_de_la_aeat(self):
        """El de importes.xml, del 13-10-2026: Base, Cuota y CuotaRecargo."""
        xml = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "S"),
                                adjunto("RECT:IMPORTES", "Base", "0.0"),
                                adjunto("RECT:IMPORTES", "Cuota", "0.0"),
                                adjunto("RECT:IMPORTES", "CuotaRecargo", "0.0"))
        assert las(xml, "SPFE-RECTIFICATIVA") == []

    def test_si_la_l2c_cambia_el_modulo_no_se_importa(self, monkeypatch):
        """Los tres de BT-3 son los tres códigos de la lista."""
        from dataclasses import replace

        lista = cius_es.LISTAS["L2.C"]
        monkeypatch.setitem(cius_es.LISTAS, "L2.C",
                            replace(lista, valores={**lista.valores, "Otro": "Otro importe."}))
        negativa = None
        try:
            importlib.reload(solucion_publica)
        except LookupError as error:
            negativa = error
        finally:
            monkeypatch.undo()
            importlib.reload(solucion_publica)
        assert type(negativa).__name__ == "AnexoCambiado" and "L2.C" in str(negativa)

    def test_una_384_que_no_dice_que_rectifica(self):
        queja = la(rectificativa_con(), "SPFE-RECTIFICATIVA")
        assert queja.gravedad == ERROR
        assert queja.campo == "Datos rectificados (BG-24, BT-3)" and "R1 a R4" in queja.mensaje
        assert queja.encontrado == "falta el tipo de rectificativa y la modalidad de rectificación"
        assert "SPFE-RECTIFICATIVA" in codigos(rectificativa_con(tipo="471"))

    def test_una_380_no_la_necesita(self):
        assert las(DEL_BOE, "SPFE-RECTIFICATIVA") == []

    def test_le_falta_la_modalidad(self):
        queja = la(rectificativa_con(adjunto("RECT:TIPO", "R1")), "SPFE-RECTIFICATIVA")
        assert queja.gravedad == ERROR and queja.encontrado == "falta la modalidad de rectificación"

    @pytest.mark.parametrize("calificador", [L10, ""], ids=["con el calificador", "a secas"])
    def test_el_calificador_de_l10_delante_o_sin_el(self, calificador):
        """La orden no dice cómo se juntan, y se aceptan las dos formas."""
        completa = rectificativa_con(adjunto("RECT:TIPO", "R1", calificador=calificador),
                                     adjunto("RECT:MODALIDAD", "I", calificador=calificador))
        assert las(completa, "SPFE-RECTIFICATIVA") == []

    def test_el_tipo_fuera_de_su_lista(self):
        queja = la(rectificativa_con(adjunto("RECT:TIPO", "R9"), adjunto("RECT:MODALIDAD", "I")),
                   "SPFE-RECTIFICATIVA")
        assert queja.gravedad == ERROR and queja.encontrado == "R9"
        assert queja.esperado == "R1, R2, R3 o R4"
        assert "BT-ES-27" in queja.campo and "L2.A" in queja.mensaje

    def test_la_modalidad_fuera_de_su_lista(self):
        queja = la(rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "X")),
                   "SPFE-RECTIFICATIVA")
        assert queja.esperado == "I o S" and "BT-ES-28" in queja.campo

    def test_el_codigo_va_en_document_type_code_y_no_en_la_descripcion(self):
        """La apuesta de antes del 02-10-2026 era la descripción, y era mala."""
        en_la_descripcion = rectificativa_con(adjunto("RECT:TIPO", descripcion="R1"),
                                              adjunto("RECT:MODALIDAD", "I"))
        queja = la(en_la_descripcion, "SPFE-RECTIFICATIVA")
        assert queja.gravedad == ERROR and queja.encontrado == "(falta)"
        assert "cbc:DocumentTypeCode" in queja.mensaje

    def test_un_tipo_repetido_se_dice_y_se_lee_entero(self):
        """Antes se leía el primero y el resto desaparecía sin decirlo."""
        dos = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:TIPO", "R9"),
                                adjunto("RECT:MODALIDAD", "I"))
        quejas = las(dos, "SPFE-RECTIFICATIVA")
        assert [(q.gravedad, q.encontrado) for q in quejas] == [(ERROR, "2"), (ERROR, "R9")]
        assert "uno como mucho" in quejas[0].mensaje
        assert quejas[1].campo.endswith("(2.º)")

    def test_la_sustitucion_sin_importes_se_dice_y_no_se_condena(self):
        """La orden solo los prevé si se optó por una única factura."""
        sin = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "S"))
        nota = la(sin, "SPFE-RECTIFICATIVA")
        assert nota.gravedad == NOTA and "La modalidad es S" in nota.mensaje
        assert las(CON_LOS_IMPORTES, "SPFE-RECTIFICATIVA") == []

    def test_los_importes_con_un_codigo_fuera_de_l2c_o_sin_importe(self):
        fuera = cambia(CON_LOS_IMPORTES, "<cbc:DocumentTypeCode>Cuota<", "<cbc:DocumentTypeCode>Total<")
        queja = la(fuera, "SPFE-RECTIFICATIVA")
        assert queja.encontrado == "Total" and queja.esperado == "Base, Cuota o CuotaRecargo"
        sin_importe = cambia(CON_LOS_IMPORTES, "<cbc:DocumentDescription>21.00</cbc:DocumentDescription>", "")
        queja = la(sin_importe, "SPFE-RECTIFICATIVA")
        assert queja.campo.startswith("Importe rectificado (BT-123)") and queja.encontrado == "(falta)"

    def test_seis_importes_son_demasiados(self):
        seis = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "S"),
                                 *[adjunto("RECT:IMPORTES", "Base", "1.00")] * 6)
        queja = la(seis, "SPFE-RECTIFICATIVA")
        assert queja.encontrado == "6" and queja.esperado == "5 como mucho"

    def test_el_qr_y_la_autorizacion_no_dicen_que_se_rectifica(self):
        """Son de L10, pero no de la rectificativa: una 384 que solo los lleva
        a ellos sigue sin decir qué rectifica."""
        for calificador in (L10, ""):
            pelada = rectificativa_con(adjunto("AUT", uuid="REG015642102461", calificador=calificador))
            assert la(pelada, "SPFE-RECTIFICATIVA").gravedad == ERROR, calificador
        assert la(rectificativa_con(), "SPFE-RECTIFICATIVA").gravedad == ERROR  # con el QR

    @pytest.mark.parametrize("ajeno", [
        "urn:otra:empresa:cualquiera:RECT:TIPO",
        f"{L10}MIRECT:TIPO",
        f"{URN_DEL_BORRADOR}RECT:TIPO",
        f"{URN_DEL_BORRADOR}ext:id:RECT:TIPO",
        "RECT-2026-0001",
    ])
    def test_la_cola_sola_no_basta(self, ajeno):
        """Si bastara, cualquiera podría llamar RECT:TIPO a lo suyo: el valor
        entero, solo o detrás del calificador de L10."""
        queja = la(rectificativa_con(adjunto(ajeno, "R1", calificador=""), adjunto("RECT:MODALIDAD", "I")),
                   "SPFE-RECTIFICATIVA")
        assert queja.encontrado == "falta el tipo de rectificativa"


# Lo que la AEAT mandó por correo el 02-10-2026, sobre el cuerpo de la factura de
# la orden: la captura era solo la cabecera y los BG-24, sin partes, totales ni
# líneas. Va sin `UBLVersionID` y con los calificadores de L10 delante; el
# proceso sin ubl: ya lo lleva `DEL_BOE`, que es el que vale desde el
# 13-10-2026. La URL del QR se deja la de la orden: la del ejemplo apunta a
# un dominio, `gob.aeat`, que no existe.
_SIN_VERSION = cambia(DEL_BOE, "  <cbc:UBLVersionID>2.5</cbc:UBLVersionID>\n", "")
SIN_LOS_BG24 = cambia(_SIN_VERSION, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>384<")
EJEMPLO = rectificativa_con(
    adjunto("RECT:TIPO", "R1", "Rectificación por el artículo 80.1 de la LIVA"),
    adjunto("RECT:MODALIDAD", "S", "Rectificación por sustitución"),
    adjunto("AUT", uuid="REG015642102461", descripcion="Autorización facturación máquina vending"),
    base=_SIN_VERSION)


class TestElEjemploDeLaAEAT:
    """La respuesta del 02-10-2026: una captura, y ni una frase de criterio.

    Medido el 05-10-2026, antes de tocar nada: con su identificador no se
    aplicaba ni una regla del anexo y nada lo decía, se le suponía UBL 2.1, el
    QR sin `ubl:` no era el QR y la autorización no se reconocía. Una
    rectificativa que no dice qué rectifica salía «sin errores».
    """

    def test_pasa_el_validador_entero_y_dice_lo_que_ha_aceptado(self):
        informe = factura.validar(EJEMPLO.encode("utf-8"))
        assert informe.deteccion.version == "2.5"
        assert limpia(EJEMPLO) == []
        assert {i.codigo for i in informe.notas} == {
            "SPFE-ALCANCE", "SPFE-COPIA", "SPFE-IMPORTE-PAGADO", "SPFE-TOTAL-A-PAGAR",
            "SPFE-RECTIFICATIVA", "FIRMA-POR-FUERA"}

    def test_una_384_que_no_dice_que_rectifica_ya_no_sale_limpia(self):
        """El caso que se midió el 05-10-2026 con «sin errores» y exit 0."""
        informe = factura.validar(SIN_LOS_BG24.encode("utf-8"))
        assert "SPFE-RECTIFICATIVA" in {i.codigo for i in informe.errores}

    def test_el_alcance_nombra_el_anexo(self, tmp_path):
        (tmp_path / "ejemplo.xml").write_text(EJEMPLO, encoding="utf-8")
        assert "anexo I de la solución pública" in factura.validar_lote([tmp_path / "ejemplo.xml"]).alcance()


class TestElQr:
    """BG-24 «QR FISCAL»: uno como mucho, con su dirección, y la descripción si acaso."""

    @pytest.mark.parametrize("calificador", [L10, ""], ids=["con el calificador", "a secas"])
    def test_se_reconoce_con_el_calificador_y_sin_el(self, calificador):
        """La fila dice «usar «QR»», y la lista L10 da el calificador aparte."""
        xml = cambia(DEL_BOE, f"<cbc:ID>{L10}QR</cbc:ID>", f"<cbc:ID>{calificador}QR</cbc:ID>")
        assert las(xml, "SPFE-QR") == []
        sin_direccion = cambia(xml, f"<cbc:UUID>{QR_URL}</cbc:UUID>", "")
        queja = la(sin_direccion, "SPFE-QR")
        assert queja.encontrado == "(falta)" and "BT-ES-25" in queja.mensaje

    def test_uno_de_cada_forma_son_dos(self):
        otro = adjunto("QR", uuid=QR_URL, calificador="")
        doble = cambia(DEL_BOE, "  <cac:AccountingSupplierParty>", otro + "  <cac:AccountingSupplierParty>")
        assert la(doble, "SPFE-QR").encontrado == "2"

    def test_un_parecido_no_es_el_qr(self):
        parecido = cambia(cambia(DEL_BOE, f"{L10}QR<", f"{L10}QRX<"), f"<cbc:UUID>{QR_URL}</cbc:UUID>", "")
        assert las(parecido, "SPFE-QR") == []

    def test_la_descripcion_es_opcional_pero_si_esta_es_una_de_dos(self):
        """`1..1` en abril y `0..1` en la orden, que dice cuáles valen."""
        assert las(CON_EL_QR_SIN_DESCRIPCION, "SPFE-QR") == []
        assert las(cambia(DEL_BOE, ">VERIFACTU<", ">TICKETBAI<"), "SPFE-QR") == []
        queja = la(cambia(DEL_BOE, ">VERIFACTU<", ">VeriFactu<"), "SPFE-QR")
        assert queja.encontrado == "VeriFactu" and queja.esperado == "VERIFACTU o TICKETBAI"


class TestLaDireccionDelQr:
    """BT-ES-25 contra la factura: el NIF, la serie y el número, la fecha y el importe.

    Lo de cada parámetro se prueba en `test_qr_fiscal`; aquí, que la factura
    de la orden le da sus datos. Reproducido el 22-10-2026 sobre `44cc805`:
    cada uno de estos salía sin una queja.
    """

    def test_la_de_la_orden_cuadra(self):
        assert las(DEL_BOE, "SPFE-QR-URL") == []

    @pytest.mark.parametrize("viejo, nuevo, encontrado", [
        ("nif=B12345674", "nif=A12345674", "A12345674"),
        ("numserie=F-2026-0101", "numserie=F-2026-0102", "F-2026-0102"),
        ("fecha=06-10-2026", "fecha=07-10-2026", "07-10-2026"),
        ("importe=121.00", "importe=86.00", "86.00"),
    ], ids=["otro NIF", "otro número", "otra fecha", "lo que se paga y no el total"])
    def test_lo_que_no_es_de_esta_factura(self, viejo, nuevo, encontrado):
        aviso = la(cambia(DEL_BOE, viejo, nuevo), "SPFE-QR-URL")
        assert aviso.gravedad == AVISO and aviso.encontrado == encontrado

    def test_el_entorno_de_pruebas(self):
        xml = cambia(DEL_BOE, "www2.agenciatributaria.gob.es", "prewww2.aeat.es")
        assert "pruebas" in la(xml, "SPFE-QR-URL").mensaje

    def test_la_del_ejemplo_de_la_aeat(self):
        """La del 02-10-2026 apuntaba a gob.aeat, según se anotó el 05-10-2026
        (el correo no está en el repositorio). Que no existe sí se ha mirado:
        aeat no está en la lista de dominios de primer nivel de la IANA,
        versión 2026102200."""
        xml = cambia(DEL_BOE, "www2.agenciatributaria.gob.es", "www.gob.aeat")
        assert "ninguna de las publicadas" in la(xml, "SPFE-QR-URL").mensaje

    def test_con_el_nif_en_bt31_y_su_prefijo(self):
        assert las(CON_EL_VENDEDOR_EN_BT31, "SPFE-QR-URL") == []

    def test_el_tipo_y_la_direccion_no_dicen_lo_mismo(self):
        aviso = la(cambia(DEL_BOE, ">VERIFACTU<", ">TICKETBAI<"), "SPFE-QR-URL")
        assert aviso.campo == "Tipo de QR (BT-123)"

    def test_en_otra_moneda_lo_dice_y_no_compara(self):
        xml = cambia(DEL_BOE, "<cbc:DocumentCurrencyCode>EUR<", "<cbc:DocumentCurrencyCode>USD<")
        notas = [i for i in las(xml, "SPFE-QR-URL")]
        assert [i.gravedad for i in notas] == [NOTA]

    def test_sin_direccion_lo_dice_spfe_qr_y_no_esta(self):
        sin_direccion = cambia(DEL_BOE, f"<cbc:UUID>{QR_URL}</cbc:UUID>", "")
        assert las(sin_direccion, "SPFE-QR-URL") == []

    def test_el_validador_entero_lo_dice(self):
        informe = factura.validar(cambia(DEL_BOE, "nif=B12345674", "nif=A12345674").encode("utf-8"))
        assert "SPFE-QR-URL" in {i.codigo for i in informe.avisos}


class TestLaAutorizacion:
    """BG-24 «AUTORIZACIÓN DE FACTURACIÓN»: las que hagan falta, cada una con su número."""

    @pytest.mark.parametrize("autorizacion", [
        adjunto("AUT"),
        adjunto("AUT", calificador=""),
        adjunto("AUT").replace("</cbc:ID>\n", "</cbc:ID>\n    <cbc:UUID></cbc:UUID>\n"),
    ], ids=["sin número", "a secas y sin número", "con el número vacío"])
    def test_sin_el_numero_no_vale(self, autorizacion):
        queja = la(_detras_de_los_documentos(autorizacion), "SPFE-AUTORIZACION")
        assert queja.gravedad == ERROR and queja.encontrado == "(falta)"
        assert queja.campo == "Autorización de facturación (BG-24, BT-ES-26)"
        assert "cbc:UUID" in queja.mensaje

    def test_con_varias_dice_a_cual_le_falta(self):
        assert las(_detras_de_los_documentos(adjunto("AUT", uuid="REG01"), adjunto("AUT", uuid="REG02")),
                   "SPFE-AUTORIZACION") == []
        dos = _detras_de_los_documentos(adjunto("AUT", uuid="REG01"), adjunto("AUT"))
        assert la(dos, "SPFE-AUTORIZACION").campo.endswith("· autorización 2")

    def test_un_parecido_no_es_la_autorizacion(self):
        assert las(_detras_de_los_documentos(adjunto("AUTX")), "SPFE-AUTORIZACION") == []


class TestLosFicherosEmbebidos:
    """Los artículos 3 y 4 de la orden: ni las facturas ni las copias fieles
    llevan ficheros dentro, y la firma, la interconectada."""

    QR_CON_SU_IMAGEN = cambia(
        DEL_BOE, "    <cbc:DocumentDescription>VERIFACTU</cbc:DocumentDescription>\n",
        "    <cbc:DocumentDescription>VERIFACTU</cbc:DocumentDescription>\n"
        '    <cac:Attachment><cbc:EmbeddedDocumentBinaryObject mimeCode="image/png" '
        'filename="qr.png">iVBORw0K</cbc:EmbeddedDocumentBinaryObject></cac:Attachment>\n')

    @pytest.mark.parametrize(("xml", "encontrado"), [
        (_detras_de_los_documentos(_contrato(PDF)), "contrato.pdf en el documento Contrato-2026-7"),
        (_detras_de_los_documentos(_contrato("<cbc:EmbeddedDocument>Contrato</cbc:EmbeddedDocument>")),
         "un texto en el documento Contrato-2026-7"),
        (QR_CON_SU_IMAGEN, f"qr.png en el documento {L10}QR"),
    ], ids=["un PDF", "un texto", "la imagen del QR"])
    def test_un_fichero_dentro_no_vale(self, xml, encontrado):
        queja = la(xml, "SPFE-FICHERO-EMBEBIDO")
        assert queja.gravedad == ERROR and queja.encontrado == encontrado
        assert "apartado 6 de su artículo 3" in queja.mensaje and "BT-125" in queja.mensaje

    @pytest.mark.parametrize(("dentro", "lo_dice"), [
        (PDF, True),
        (PDF.replace('application/pdf" filename="contrato.pdf"', 'APPLICATION/PDF" filename="contrato"'), True),
        (PDF.replace(' mimeCode="application/pdf"', ""), True),
        (PDF.replace('application/pdf" filename="contrato.pdf"', 'image/png" filename="plano.png"'), False),
        ("<cbc:EmbeddedDocument>Contrato</cbc:EmbeddedDocument>", False),
    ], ids=["por su tipo", "en mayúsculas", "solo por el nombre", "una imagen", "un texto"])
    def test_si_es_un_pdf_dice_donde_va_el_del_primer_ano(self, dentro, lo_dice):
        """Disposición transitoria segunda del RD 238/2026, apartado 2."""
        queja = la(_detras_de_los_documentos(_contrato(dentro)), "SPFE-FICHERO-EMBEBIDO")
        assert ("transitoria segunda" in queja.mensaje) is lo_dice

    def test_en_la_copia_fiel_no_se_habla_del_pdf_del_primer_ano(self):
        queja = la(_como_copia_fiel(_detras_de_los_documentos(_contrato(PDF))), "SPFE-FICHERO-EMBEBIDO")
        assert "transitoria segunda" not in queja.mensaje

    def test_en_la_copia_fiel_lo_dice_el_articulo_4(self):
        queja = la(_como_copia_fiel(_detras_de_los_documentos(_contrato(PDF))), "SPFE-FICHERO-EMBEBIDO")
        assert queja.gravedad == ERROR and "apartado 4 de su artículo 4" in queja.mensaje

    def test_un_documento_por_su_direccion_no_es_un_fichero_dentro(self):
        assert las(CON_UN_DOCUMENTO_EXTERNO, "SPFE-FICHERO-EMBEBIDO") == []

    @pytest.mark.parametrize("xml", [CON_LA_FIRMA_EN_UN_FICHERO, _con_la_firma_envuelta(DEL_BOE)],
                             ids=["en un fichero", "envuelta"])
    def test_la_factura_interconectada_puede_ir_con_la_firma(self, xml):
        """Segundo párrafo del apartado 6 del artículo 3."""
        assert las(xml, "SPFE-FICHERO-EMBEBIDO") == []

    @pytest.mark.parametrize(("xml", "encontrado"), [
        (CON_LA_FIRMA_EN_UN_FICHERO, "la firma en un fichero (cac:Signature)"),
        (_con_la_firma_envuelta(DEL_BOE), "la firma envuelta (ds:Signature)"),
    ], ids=["en un fichero", "envuelta"])
    def test_la_copia_fiel_con_la_firma_es_un_aviso(self, xml, encontrado):
        """El artículo 4 no hace la salvedad del 3, y la orden no dice si la
        firma es uno de esos ficheros: aviso, y no error."""
        queja = la(_como_copia_fiel(xml), "SPFE-FICHERO-EMBEBIDO")
        assert queja.gravedad == AVISO and queja.encontrado == encontrado

    def test_la_copia_fiel_tambien_con_un_1(self):
        """El esquema admite «1» por «true». Lo vio el auditor: aceptando solo
        «true», la suite pasaba."""
        con_1 = cambia(_como_copia_fiel(_detras_de_los_documentos(_contrato(PDF))),
                       "<cbc:CopyIndicator>true<", "<cbc:CopyIndicator>1<")
        assert "apartado 4 de su artículo 4" in la(con_1, "SPFE-FICHERO-EMBEBIDO").mensaje

    def test_una_firma_que_solo_se_nombra_no_es_una_firma(self):
        """`cac:Signature` con la dirección de la firma y sin ella."""
        nombrada = _detras_de_los_documentos(
            "  <cac:Signature>\n    <cbc:ID>firma</cbc:ID>\n    <cac:DigitalSignatureAttachment>"
            "<cac:ExternalReference><cbc:URI>#firma</cbc:URI></cac:ExternalReference>"
            "</cac:DigitalSignatureAttachment>\n  </cac:Signature>\n")
        assert las(_como_copia_fiel(nombrada), "SPFE-FICHERO-EMBEBIDO") == []


class TestPartes:

    def test_el_nif_del_vendedor_con_otro_impuesto(self):
        otro = cambia(CON_EL_VENDEDOR_EN_BT31, "ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT<",
                      "ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>IVA<")
        queja = la(otro, "SPFE-NIF")
        assert queja.campo == "NIF del vendedor (BT-31 o BT-32)"
        assert queja.encontrado == 'ESB12345674 con el impuesto "IVA"'

    def test_sin_nif_del_comprador(self):
        sin = cambia(DEL_BOE, "<cac:PartyTaxScheme><cbc:CompanyID>ESA12345674</cbc:CompanyID>"
                              "<cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>", "")
        queja = la(sin, "SPFE-NIF")
        assert queja.campo == "NIF del comprador (BT-48 o BT-47)" and queja.encontrado == "(falta)"

    def test_el_nif_con_loc_tiene_que_llevar_fc(self):
        """La orden pide las dos cosas: el impuesto «LOC» y el atributo «FC»."""
        sin_fc = cambia(DEL_BOE, ' schemeID="FC">B12345674', ">B12345674")
        assert la(sin_fc, "SPFE-NIF").encontrado == 'B12345674 con el impuesto "LOC"'
        otro = cambia(DEL_BOE, ' schemeID="FC">B12345674', ' schemeID="NIF">B12345674')
        assert la(otro, "SPFE-NIF").encontrado == 'B12345674 con el impuesto "LOC" y schemeID "NIF"'

    def test_con_el_nif_en_bt32_hace_falta_bt30(self):
        """Medido el 11-10-2026 antes de escribir la regla: sin BT-30 salía
        BR-CO-26, que pide uno de tres, y nada de la orden, que pide este. Y
        con el identificador del vendedor (BT-29) no salía nada: BR-CO-26 se
        conforma con él."""
        registro = "<cbc:RegistrationName>Talleres Ejemplo SL</cbc:RegistrationName>"
        sin = cambia(DEL_BOE, registro + "<cbc:CompanyID>B12345674</cbc:CompanyID>", registro)
        queja = la(sin, "SPFE-NIF")
        assert queja.gravedad == ERROR
        assert queja.campo == "Identificador de inscripción legal del vendedor (BT-30)"
        con_bt29 = cambia(sin, "<cac:AccountingSupplierParty><cac:Party>\n",
                          "<cac:AccountingSupplierParty><cac:Party>\n"
                          "    <cac:PartyIdentification><cbc:ID>T-0001</cbc:ID></cac:PartyIdentification>\n")
        assert "BR-CO-26" not in {i.codigo for i in factura.validar(con_bt29.encode("utf-8")).errores}
        assert "BR-CO-26" in {i.codigo for i in factura.validar(sin.encode("utf-8")).errores}
        assert la(con_bt29, "SPFE-NIF").campo == queja.campo
        # Con el NIF-IVA y sin BT-32, la orden no lo pide.
        assert las(cambia(CON_EL_VENDEDOR_EN_BT31, registro + "<cbc:CompanyID>B12345674</cbc:CompanyID>",
                          registro), "SPFE-NIF") == []

    def test_con_loc_y_sin_fc_no_se_pide_ademas_bt30(self):
        """Sin «FC» el NIF no está en BT-32, y lo dice la queja del NIF: una
        sola. Lo vio el auditor: sin mirar el atributo, la suite pasaba."""
        registro = "<cbc:RegistrationName>Talleres Ejemplo SL</cbc:RegistrationName>"
        sin_fc = cambia(cambia(DEL_BOE, ' schemeID="FC">B12345674', ">B12345674"),
                        registro + "<cbc:CompanyID>B12345674</cbc:CompanyID>", registro)
        assert la(sin_fc, "SPFE-NIF").campo == "NIF del vendedor (BT-31 o BT-32)"

    _BT30 = "<cbc:CompanyID>B12345674</cbc:CompanyID></cac:PartyLegalEntity>"

    @pytest.mark.parametrize(("escrito", "dice"), [
        ("RM Madrid T.1 F.2", "no es un NIF"),
        ("A12345674", "pero no el del vendedor, que la factura da como B12345674"),
    ], ids=["un registro mercantil", "el NIF de otro"])
    def test_bt30_es_el_nif_del_vendedor(self, escrito, dice):
        """La orden lo describe como «Número de identificación fiscal (NIF) del
        vendedor». Hasta el 12-10-2026 se miraba que estuviera, y no qué
        llevaba: lo vio el auditor. Con el NIF en BT-32 es un ERROR, y sin él,
        un AVISO: la norma admite ahí el de cualquier registro oficial."""
        nuevo = f"<cbc:CompanyID>{escrito}</cbc:CompanyID></cac:PartyLegalEntity>"
        queja = la(cambia(DEL_BOE, self._BT30, nuevo), "SPFE-NIF")
        assert queja.gravedad == ERROR and dice in queja.mensaje
        assert queja.campo == "Identificador de inscripción legal del vendedor (BT-30)"
        assert queja.encontrado == escrito and "(BT-32), como aquí" in queja.mensaje
        sin_bt32 = la(cambia(CON_EL_VENDEDOR_EN_BT31, self._BT30, nuevo), "SPFE-NIF")
        assert sin_bt32.gravedad == AVISO and dice in sin_bt32.mensaje
        assert "cualquier registro oficial" in sin_bt32.mensaje

    @pytest.mark.parametrize("xml", [DEL_BOE, CON_EL_VENDEDOR_EN_BT31], ids=["BT-32", "BT-31"])
    def test_bt30_con_el_prefijo_es_vale(self, xml):
        con_es = cambia(xml, self._BT30, "<cbc:CompanyID>ESB12345674</cbc:CompanyID></cac:PartyLegalEntity>")
        assert las(con_es, "SPFE-NIF") == []

    def test_el_nif_iva_del_vendedor_lleva_el_prefijo_de_espana(self):
        frances = cambia(CON_EL_VENDEDOR_EN_BT31, ">ESB12345674<", ">FRB12345674<")
        queja = la(frances, "SPFE-NIF")
        assert queja.gravedad == ERROR and queja.campo == "NIF-IVA del vendedor (BT-31)"
        assert queja.encontrado == "FRB12345674" and "BT-32" in queja.mensaje

    def test_el_del_comprador_tambien_lleva_el_prefijo_de_espana(self):
        """Hasta el 11-10-2026 no se medía, y la nota del alcance lo decía. Hasta
        el 13-10-2026 salía en AVISO, porque la fila dice NIF del vendedor; ese
        día la AEAT contestó que es una errata de la descripción."""
        frances = cambia(DEL_BOE, ">ESA12345674<", ">FRA12345674<")
        queja = la(frances, "SPFE-NIF")
        assert queja.gravedad == ERROR and queja.campo == "NIF-IVA del comprador (BT-48)"
        assert "13-10-2026" in queja.mensaje and "BT-47" in queja.mensaje
        assert "BT-48" not in la(frances, "SPFE-ALCANCE").mensaje

    def test_en_espana_la_direccion_va_entera(self):
        sin_ciudad = cambia(DEL_BOE, "<cbc:CityName>Madrid</cbc:CityName>", "")
        queja = la(sin_ciudad, "SPFE-DIRECCION")
        assert queja.campo == "Dirección del vendedor" and "BT-37" in queja.encontrado

    def test_fuera_de_espana_basta_la_calle(self):
        francesa = cambia(cambia(DEL_BOE, "<cbc:CityName>Sevilla</cbc:CityName>", ""),
                          "Sevilla</cbc:CountrySubentity>\n      <cac:Country><cbc:IdentificationCode>ES<",
                          "Sevilla</cbc:CountrySubentity>\n      <cac:Country><cbc:IdentificationCode>FR<")
        assert "SPFE-DIRECCION" not in codigos(francesa)
        sin_calle = cambia(francesa, "<cbc:StreetName>Calle Menor 2</cbc:StreetName>", "")
        assert "BT-50" in la(sin_calle, "SPFE-DIRECCION").encontrado

    def test_el_tercero_sin_tipologia(self):
        sin = cambia(CON_EL_TERCERO_DEL_BOE, "<cbc:ServiceTypeCode>FacturaciónPorTercero</cbc:ServiceTypeCode>", "")
        assert "la tipología (BT-ES-5)" in la(sin, "SPFE-TERCERO").mensaje

    def test_el_tercero_con_otro_impuesto(self):
        otro = cambia(CON_EL_TERCERO_DEL_BOE, "B87654321</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC<",
                      "B87654321</cbc:CompanyID><cac:TaxScheme><cbc:ID>IGIC<")
        assert '(hay "IGIC")' in la(otro, "SPFE-TERCERO").mensaje

    def test_al_tercero_se_le_pide_el_nombre_y_el_fc(self):
        sin_nombre = cambia(CON_EL_TERCERO_DEL_BOE,
                            "<cbc:RegistrationName>Gestoria Ejemplo SL</cbc:RegistrationName>", "")
        assert "el nombre o razón social (BT-ES-3)" in la(sin_nombre, "SPFE-TERCERO").mensaje
        sin_fc = cambia(CON_EL_TERCERO_DEL_BOE, ' schemeID="FC">B87654321', ">B87654321")
        assert "LOC con el atributo FC (hay" in la(sin_fc, "SPFE-TERCERO").mensaje

    def test_el_nombre_del_tercero_donde_lo_ponia_el_borrador_no_se_lee(self, catalogo):
        """En `cac:PartyName`: hasta el 11-10-2026 se aceptaba también ahí.

        Delante de `cac:PartyTaxScheme`, que es donde UBL lo admite. Hasta la
        revisión de ese día esta factura lo ponía detrás, el esquema la
        rechazaba (XSD-ORDEN) y la prueba no lo veía porque solo miraba el
        anexo; la medida de HALLAZGOS se hizo con ella. Lo vio el auditor.
        Ahora pasa el validador entero, y el único fallo es el del tercero.
        """
        en_abril = cambia(cambia(CON_EL_TERCERO_DEL_BOE,
                                 "<cac:PartyLegalEntity><cbc:RegistrationName>Gestoria Ejemplo SL"
                                 "</cbc:RegistrationName></cac:PartyLegalEntity>", ""),
                          '      <cac:Party>\n        <cac:PartyTaxScheme>',
                          '      <cac:Party>\n'
                          "        <cac:PartyName><cbc:Name>Gestoria Ejemplo SL</cbc:Name></cac:PartyName>\n"
                          "        <cac:PartyTaxScheme>")
        assert "el nombre o razón social (BT-ES-3)" in la(en_abril, "SPFE-TERCERO").mensaje
        assert {codigo for codigo, _ in limpia(en_abril, catalogo)} == {"SPFE-TERCERO"}

    def test_la_tipologia_donde_la_escribe_la_orden_no_se_da_por_ausente(self):
        """La ruta de BT-ES-5 cuelga de `cac:Party`, y ahí UBL no la admite: el
        esquema la rechaza. La queja decía «le falta la tipología», y no falta:
        está donde no puede ir. Lo vio el auditor el 11-10-2026."""
        en_su_party = cambia(cambia(CON_EL_TERCERO_DEL_BOE,
                                    "      <cbc:ServiceTypeCode>FacturaciónPorTercero</cbc:ServiceTypeCode>\n",
                                    ""),
                             "      <cac:Party>\n",
                             "      <cac:Party>\n"
                             "        <cbc:ServiceTypeCode>FacturaciónPorTercero</cbc:ServiceTypeCode>\n")
        queja = la(en_su_party, "SPFE-TERCERO")
        assert "está en su cac:Party" in queja.mensaje
        assert "cac:ServiceProviderParty/cbc:ServiceTypeCode" in queja.mensaje


# Un descuento del documento y uno de la línea, con su motivo escrito. Solo se
# miran con las reglas del anexo: los totales no se tocan.
_DESCUENTO = """  <cac:AllowanceCharge>
    <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
    <cbc:AllowanceChargeReason>Descuento por pronto pago</cbc:AllowanceChargeReason>
    <cbc:Amount currencyID="EUR">10.00</cbc:Amount>
    <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
  </cac:AllowanceCharge>
"""
_DESCUENTO_DE_LINEA = """    <cac:AllowanceCharge>
      <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
      <cbc:AllowanceChargeReason>Descuento de linea</cbc:AllowanceChargeReason>
      <cbc:Amount currencyID="EUR">10.00</cbc:Amount>
    </cac:AllowanceCharge>
"""
CON_DESCUENTOS = cambia(cambia(DEL_BOE, "  <cac:TaxTotal>", _DESCUENTO + "  <cac:TaxTotal>"),
                        "    <cac:Item>\n      <cbc:Name>Asesoria", _DESCUENTO_DE_LINEA
                        + "    <cac:Item>\n      <cbc:Name>Asesoria")


class TestLaGarantiaYElCanje:
    """La retención de garantía escrita como descuento y el 388 sin BG-3.

    Las dos pasaban sin una palabra el 19-10-2026, y ninguna es un error: la
    garantía depende del contrato, que la factura no trae, y el BG-3 es
    opcional. Por eso son notas.
    """

    _GARANTIA = cambia(CON_DESCUENTOS,
                       "<cbc:AllowanceChargeReason>Descuento por pronto pago</cbc:AllowanceChargeReason>",
                       "<cbc:AllowanceChargeReason>Retención de GARANTÍA 5 %</cbc:AllowanceChargeReason>")

    def test_un_descuento_de_garantia_da_las_tres_lecturas(self):
        nota = la(self._GARANTIA, "SPFE-GARANTIA")
        assert nota.gravedad == NOTA
        assert nota.encontrado == "Retención de GARANTÍA 5 %"
        for lectura in ("pago anticipado", "V2823-23", "de la entrega", "inversión del sujeto pasivo"):
            assert lectura in nota.mensaje

    def test_un_descuento_cualquiera_no_la_da(self):
        assert las(CON_DESCUENTOS, "SPFE-GARANTIA") == []

    def test_un_cargo_de_garantia_no_la_da(self):
        """Un cargo sube la base: no es la retención."""
        cargo = cambia(self._GARANTIA, "<cbc:ChargeIndicator>false</cbc:ChargeIndicator>\n    <cbc:AllowanceChargeReason>Ret",
                       "<cbc:ChargeIndicator>true</cbc:ChargeIndicator>\n    <cbc:AllowanceChargeReason>Ret")
        assert las(cargo, "SPFE-GARANTIA") == []

    def test_tambien_en_la_linea(self):
        linea = cambia(CON_DESCUENTOS, "<cbc:AllowanceChargeReason>Descuento de linea</cbc:AllowanceChargeReason>",
                       "<cbc:AllowanceChargeReason>Garantia de obra</cbc:AllowanceChargeReason>")
        assert la(linea, "SPFE-GARANTIA").encontrado == "Garantia de obra"

    def test_un_388_sin_referencia_es_una_nota(self):
        nota = la(cambia(DEL_BOE, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>388<"), "SPFE-CANJE")
        assert nota.gravedad == NOTA and "no lo exige" in nota.mensaje
        assert nota.encontrado == "ninguna"

    def test_con_la_simplificada_citada_no_sale(self):
        assert las(cambia(CON_LA_REFERENCIADA, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>388<"),
                   "SPFE-CANJE") == []

    def test_otro_tipo_sin_referencia_no_la_da(self):
        assert las(DEL_BOE, "SPFE-CANJE") == []


class TestDocumento:

    def test_la_factura_referenciada_sin_fecha(self):
        sin = cambia(CON_LA_REFERENCIADA, "<cbc:IssueDate>2026-10-01</cbc:IssueDate>", "")
        assert la(sin, "SPFE-FACTURA-REFERENCIADA").encontrado == "sin fecha: F-2026-0100"

    def test_el_motivo_con_codigo_y_sin_texto(self):
        assert las(CON_DESCUENTOS, "SPFE-MOTIVO") == []
        solo_codigo = cambia(CON_DESCUENTOS,
                             "<cbc:AllowanceChargeReason>Descuento por pronto pago</cbc:AllowanceChargeReason>",
                             "<cbc:AllowanceChargeReasonCode>95</cbc:AllowanceChargeReasonCode>")
        assert la(solo_codigo, "SPFE-MOTIVO").campo.endswith("descuento 1")
        sin_linea = cambia(CON_DESCUENTOS,
                           "<cbc:AllowanceChargeReason>Descuento de linea</cbc:AllowanceChargeReason>", "")
        assert la(sin_linea, "SPFE-MOTIVO").campo.endswith("descuento 1 de la línea 1")

    _SITIOS_DEL_IMPUESTO = pytest.mark.parametrize(("xml", "viejo", "lugar"), [
        (DEL_BOE, "<cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>"
                  "</cac:ClassifiedTaxCategory>", "líneas"),
        (DEL_BOE, "<cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>"
                  "</cac:TaxCategory>\n    </cac:TaxSubtotal>", "desglose del IVA"),
        (CON_DESCUENTOS, "<cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>"
                         "</cac:TaxCategory>\n  </cac:AllowanceCharge>", "descuentos y cargos del documento"),
    ], ids=["la línea", "el desglose", "el descuento"])

    @_SITIOS_DEL_IMPUESTO
    def test_el_impuesto_no_es_vat(self, xml, viejo, lugar):
        """Lo dicen las filas BG-30, BG-23, BT-95 y BT-102, en su columna de la ruta."""
        otro = cambia(xml, viejo, viejo.replace(">VAT<", ">IGIC<"))
        queja = la(otro, "SPFE-TIPO-DE-IMPUESTO")
        assert queja.campo.endswith(lugar) and queja.encontrado == "IGIC"
        assert "BT-95, BT-102, BG-30 y BG-23" in queja.mensaje

    @_SITIOS_DEL_IMPUESTO
    def test_el_impuesto_que_no_esta_tampoco_es_vat(self, xml, viejo, lugar):
        """«Su uso implica» que la ruta tome el valor, y sin el elemento no lo
        toma. Pasaba sin una queja hasta el 11-10-2026: lo destapó quitar, uno
        a uno, cada elemento de las facturas buenas."""
        sin = cambia(xml, viejo, viejo.replace("<cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>", ""))
        queja = la(sin, "SPFE-TIPO-DE-IMPUESTO")
        assert queja.campo.endswith(lugar) and queja.encontrado == "(falta)"

    def test_la_k_no_esta_en_la_lista_l4(self):
        con_k = cambia(DEL_BOE, "<cac:ClassifiedTaxCategory><cbc:ID>S<", "<cac:ClassifiedTaxCategory><cbc:ID>K<")
        queja = la(con_k, "SPFE-CATEGORIA")
        assert queja.gravedad == ERROR and queja.encontrado == "K" and "intracomunitaria" in queja.mensaje
        assert queja.campo.endswith("línea 1")
        assert queja.esperado == "S, Z, E, AE, O, G, L, M, N, D o F"

    def test_una_categoria_que_ni_la_norma_admite_se_la_deja_a_br_cl(self):
        assert "SPFE-CATEGORIA" not in codigos(
            cambia(DEL_BOE, "<cac:ClassifiedTaxCategory><cbc:ID>S<", "<cac:ClassifiedTaxCategory><cbc:ID>X<"))


class TestElDesglose:

    def test_lo_no_sujeto_tambien_lleva_tipo(self):
        """La norma lo deja sin tipo (BR-48); la fila BT-119 de la orden, no."""
        sin = _sin_cuota(CON_EL_COMPRADOR_EN_BT47, "O", None, None)
        queja = la(sin, "SPFE-TIPO-DE-IVA")
        assert queja.gravedad == ERROR and "BR-48" in queja.mensaje
        assert las(CON_LA_NO_SUJETA, "SPFE-TIPO-DE-IVA") == []

    def test_se_mira_cada_entrada_del_desglose(self):
        """Una no sujeta sin tipo detrás de una S con el suyo. Lo vio el
        auditor: mirando solo la primera entrada, la suite pasaba."""
        con_dos = cambia(
            DEL_BOE, "    </cac:TaxSubtotal>\n  </cac:TaxTotal>\n  <cac:WithholdingTaxTotal>",
            "    </cac:TaxSubtotal>\n    <cac:TaxSubtotal>\n"
            '      <cbc:TaxableAmount currencyID="EUR">0.00</cbc:TaxableAmount>\n'
            '      <cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>\n'
            "      <cac:TaxCategory><cbc:ID>O</cbc:ID>"
            "<cbc:TaxExemptionReason>Operacion no sujeta</cbc:TaxExemptionReason>"
            "<cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>\n"
            "    </cac:TaxSubtotal>\n  </cac:TaxTotal>\n  <cac:WithholdingTaxTotal>")
        queja = la(con_dos, "SPFE-TIPO-DE-IVA")
        assert queja.gravedad == ERROR and queja.encontrado == "(falta)"

    def test_en_las_demas_categorias_lo_dice_br_48(self):
        """Dos quejas por lo mismo no dicen más que una."""
        sin = cambia(DEL_BOE, "<cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent>",
                     "<cac:TaxCategory><cbc:ID>S</cbc:ID>")
        assert "SPFE-TIPO-DE-IVA" not in codigos(sin)
        assert "BR-48" in {i.codigo for i in factura.validar(sin.encode("utf-8")).errores}

    def test_un_codigo_de_exencion_de_otro_pais(self):
        """La norma admite los VATEX-FR (BR-CL-22); la orden, no."""
        francesa = _sin_cuota(DEL_BOE, "E", "0", "0", "VATEX-FR-CGI261-1")
        queja = la(francesa, "SPFE-EXENCION")
        assert queja.gravedad == ERROR and queja.encontrado == "VATEX-FR-CGI261-1"
        assert "BT-121" in queja.mensaje
        assert las(CON_LA_EXENTA, "SPFE-EXENCION") == []
        assert las(cambia(CON_LA_EXENTA, ">VATEX-EU-132-1I<", ">vatex-eu-132-1i<"),
                   "SPFE-EXENCION") == []

    def test_un_vatex_es_lo_juzga_br_cl_22_con_la_lista(self):
        """La orden admite los VATEX-ES. Uno de la lista vale, con la nota de
        desde cuándo; uno que no está lo dice BR-CL-22, y no esta regla."""
        bueno = _sin_cuota(DEL_BOE, "E", "0", "0", "VATEX-ES-IVA20")
        assert "SPFE-EXENCION" not in codigos(bueno)
        informe = factura.validar(bueno.encode("utf-8"))
        assert "BR-CL-22" not in {i.codigo for i in informe.errores}
        assert "IVA-VATEX-ES" in {i.codigo for i in informe.incidencias if i.gravedad == NOTA}
        inventado = _sin_cuota(DEL_BOE, "E", "0", "0", "VATEX-ES-20-1")
        assert "SPFE-EXENCION" not in codigos(inventado)
        informe = factura.validar(inventado.encode("utf-8"))
        assert "BR-CL-22" in {i.codigo for i in informe.errores}
        assert "IVA-VATEX-ES" not in {i.codigo for i in informe.incidencias}
        assert sum(codigo.startswith("VATEX-ES-") for codigo in listas_de_codigos.VATEX) == 18


class TestLosImpuestosYTasas:
    """Los que no son el IVA, con su lista L9: BT-ES-22, BG-ES-2 y BG-ES-3.

    Hasta el 11-10-2026 no se medían, y la nota del alcance lo decía. Medido
    ese día antes de escribir las reglas: los diez casos que la orden da por
    malos salían sin una queja.
    """

    def test_un_cargo_de_linea_sin_codigo(self):
        queja = la(_con_un_cargo_de_linea(None), "SPFE-IMPUESTO-O-TASA")
        assert queja.gravedad == ERROR and queja.encontrado == "(falta)"
        assert queja.campo.endswith("cargo 1 de la línea 1") and "RESTO" in queja.mensaje

    def test_se_mira_cada_cargo_de_la_linea(self):
        """Lo vio el auditor: mirando solo el primero, la suite pasaba."""
        dos = cambia(_con_un_cargo_de_linea(), "    </cac:AllowanceCharge>\n    <cac:Item>",
                     "    </cac:AllowanceCharge>\n    <cac:AllowanceCharge>\n"
                     "      <cbc:ChargeIndicator>true</cbc:ChargeIndicator>\n"
                     "      <cbc:AllowanceChargeReason>Porte</cbc:AllowanceChargeReason>\n"
                     '      <cbc:Amount currencyID="EUR">5.00</cbc:Amount>\n'
                     "    </cac:AllowanceCharge>\n    <cac:Item>")
        queja = la(dos, "SPFE-IMPUESTO-O-TASA")
        assert queja.encontrado == "(falta)" and queja.campo.endswith("cargo 2 de la línea 1")

    def test_la_ficha_dice_que_el_esquematron_de_ubl_avisa_del_cargo_de_linea(self):
        """La ruta de BT-ES-22 dispara UBL-CR-558, un aviso del esquematrón de
        sintaxis de UBL del CEN, que aquí no se corre. La ficha decía que la
        norma «no tiene nada de esto»: lo vio el auditor."""
        ruta = solucion_publica._fila("BT-ES-22").ruta
        assert "cac:InvoiceLine/cac:AllowanceCharge/cac:TaxCategory" in ruta
        ficha = glosario.CODIGOS["SPFE-IMPUESTO-O-TASA"]
        assert "UBL-CR-558" in ficha and "no se corren aquí" in ficha

    def test_un_cargo_de_linea_con_un_codigo_que_no_es_de_l9(self):
        queja = la(_con_un_cargo_de_linea("XYZ"), "SPFE-IMPUESTO-O-TASA")
        assert queja.encontrado == "XYZ" and queja.esperado.endswith("IMPTAS o RESTO")
        assert las(_con_un_cargo_de_linea("IEE"), "SPFE-IMPUESTO-O-TASA") == []

    def test_un_descuento_no_lo_lleva(self):
        """El grupo de los descuentos de línea (BG-27) no tiene código de impuesto."""
        assert las(CON_DESCUENTOS, "SPFE-IMPUESTO-O-TASA") == []

    @pytest.mark.parametrize(("codigo", "encontrado"), [("", "(falta)"), ("XYZ", "XYZ")])
    def test_el_impuesto_de_un_cargo_del_documento_lleva_su_codigo(self, codigo, encontrado):
        xml = _con_un_impuesto_en_un_cargo("5.00", _impuesto("100.00", "5.00", "5", codigo))
        queja = la(xml, "SPFE-IMPUESTO-O-TASA")
        assert queja.gravedad == ERROR and queja.encontrado == encontrado
        assert "BT-ES-9" in queja.campo and queja.campo.endswith("cargo 1")

    def test_la_cuota_del_cargo_es_la_misma_en_sus_dos_sitios(self):
        queja = la(_con_un_impuesto_en_un_cargo("6.00"), "SPFE-IMPUESTO-O-TASA")
        assert queja.gravedad == ERROR and "pide el mismo importe en el impuesto" in queja.mensaje
        assert queja.encontrado == "5.00 en el impuesto y 6.00 en el total"

    def test_con_dos_impuestos_en_el_cargo_no_se_compara_y_se_dice(self, catalogo):
        """La cuota va también en el total del cargo, que es uno: con dos
        impuestos no se puede. Es la pregunta 4 al buzón, del 07-10-2026. Hasta
        el 24-10-2026 salía una NOTA; el anexo del portal de la AEAT del
        21-10-2026 deja el grupo en `0..1`, y el BOE en `0..n`: un AVISO, y
        ninguna otra queja."""
        xml = _con_un_impuesto_en_un_cargo("5.00", _impuesto("50.00", "2.50", "5", "IEE"),
                                           _impuesto("50.00", "2.50", "5", "IMPTAS"))
        aviso = la(xml, "SPFE-IMPUESTO-O-TASA")
        assert aviso.gravedad == AVISO and "21-10-2026" in aviso.mensaje
        assert "0..1" in aviso.mensaje and "0..n" in aviso.mensaje
        assert aviso.encontrado == "2 impuestos"
        assert limpia(xml, catalogo) == [("SPFE-IMPUESTO-O-TASA", aviso.campo)]

    def test_la_cuota_es_la_base_por_el_tipo(self):
        """Con el margen de la cuota del IVA, como las retenciones."""
        mala = _con_un_impuesto_en_un_cargo("7.00", _impuesto("100.00", "7.00", "5", "IEE"))
        queja = la(mala, "SPFE-IMPUESTO-O-TASA")
        assert queja.gravedad == ERROR and queja.esperado == "5,00" and "BT-ES-8" in queja.mensaje
        casi = _con_un_impuesto_en_un_cargo("5.01", _impuesto("100.00", "5.01", "5", "IEE"))
        assert la(casi, "SPFE-IMPUESTO-O-TASA").gravedad == NOTA
        sin_cuenta = _con_un_impuesto_en_un_cargo("5.00", _impuesto("", "5.00", "", "IEE"))
        assert las(sin_cuenta, "SPFE-IMPUESTO-O-TASA") == []

    @pytest.mark.parametrize(("base", "cuota", "tipo"), [
        ("11.11", "5.00", "0.45"),
        ("1.11", "0.50", "0.45"),
        ("100.00", "5.00", "0.05"),
    ], ids=["plástico por kilo", "por debajo de una unidad", "tipo como fracción"])
    def test_la_cuota_sin_dividir_por_cien_es_un_error_que_dice_por_que(self, base, cuota, tipo):
        """Medido el 19-10-2026: el plástico a 0,45 euros por kilo daba un
        ERROR con la cuenta y sin la causa, y con 1,11 kilos, una NOTA que lo
        daba por bueno."""
        xml = _con_un_impuesto_en_un_cargo(cuota, _impuesto(base, cuota, tipo, "IEP"))
        queja = la(xml, "SPFE-IMPUESTO-O-TASA")
        assert queja.gravedad == ERROR
        assert "sin dividir por cien" in queja.mensaje and "solo la cuota" in queja.mensaje
        assert "fracción" in queja.mensaje and "Ley 7/2022" in queja.mensaje

    def test_la_del_cobro_tambien(self):
        queja = la(_con_el_desglose_del_iedmt(cuota="12000.00"), "SPFE-IMPUESTO-O-TASA")
        assert queja.gravedad == ERROR and "sin dividir por cien" in queja.mensaje

    def test_un_error_cualquiera_no_dice_lo_del_cien(self):
        mala = _con_un_impuesto_en_un_cargo("7.00", _impuesto("100.00", "7.00", "5", "IEE"))
        assert "sin dividir por cien" not in la(mala, "SPFE-IMPUESTO-O-TASA").mensaje

    @pytest.mark.parametrize(("cambio", "encontrado"), [
        ({"esquema": "IGIC"}, "IGIC y S"),
        ({"categoria": "E"}, "VAT y E"),
    ])
    def test_el_desglose_de_un_cobro_lleva_vat_y_s(self, cambio, encontrado):
        """Aunque no sea el IVA: «su uso implica» los dos valores (BG-ES-3)."""
        queja = la(_con_el_desglose_del_iedmt(**cambio), "SPFE-IMPUESTO-O-TASA")
        assert queja.gravedad == ERROR and queja.encontrado == encontrado
        assert queja.campo.endswith("línea de cobro 2")

    def test_la_cuota_del_cobro_es_la_base_por_el_tipo(self):
        queja = la(_con_el_desglose_del_iedmt(cuota="150.00"), "SPFE-IMPUESTO-O-TASA")
        assert queja.esperado == "120,00" and "BT-ES-14" in queja.mensaje


class TestLoQueSeQuitabaSinUnaQueja:
    """Antes de dar por medido todo lo que la orden pide, el 11-10-2026, se
    quitó cada elemento de las facturas buenas, uno a uno, y se pasó el
    validador entero. Lo que la orden pide y salía sin una queja está aquí; lo
    del tipo de impuesto, con las otras pruebas del tipo de impuesto."""

    def test_el_total_del_impuesto_de_un_cargo_sin_su_detalle(self):
        """La cuota en una sola de sus dos rutas (BT-ES-8), y nada que diga
        qué impuesto es: le falta el código."""
        sin_detalle = quita(CON_UN_IMPUESTO_EN_UN_CARGO, "      <cac:TaxSubtotal>", "</cac:TaxSubtotal>\n")
        queja = la(sin_detalle, "SPFE-IMPUESTO-O-TASA")
        assert queja.gravedad == ERROR and queja.encontrado == "(falta)"
        assert "(BT-ES-9)" in queja.campo

    def test_la_suma_de_retenciones_sin_ninguna_es_una_nota(self):
        """La orden deja el detalle en `0..n`: sin él no hay con qué comparar
        la suma, y se dice. Con la suma a cero no hay nada que decir."""
        sin = quita(DEL_BOE, '    <cac:TaxSubtotal>\n      <cbc:TaxableAmount currencyID="EUR">100.00'
                    '</cbc:TaxableAmount>\n      <cbc:TaxAmount currencyID="EUR">15.00',
                    "</cac:TaxSubtotal>\n")
        nota = la(sin, "SPFE-RETENCION")
        assert nota.gravedad == NOTA and nota.encontrado == "15.00" and "0..n" in nota.mensaje
        a_cero = cambia(sin, '<cbc:TaxAmount currencyID="EUR">15.00</cbc:TaxAmount>\n  </cac:WithholdingTaxTotal>',
                        '<cbc:TaxAmount currencyID="EUR">0.00</cbc:TaxAmount>\n  </cac:WithholdingTaxTotal>')
        assert las(a_cero, "SPFE-RETENCION") == []


class TestLineas:

    REGI = _REGI_DEL_BOE
    RCAT = _RCAT_CON_CALIFICADOR.format("01")

    def test_una_linea_sin_clave_de_regimen(self):
        queja = la(cambia(DEL_BOE, self.REGI, ""), "SPFE-CLAVE-DE-REGIMEN")
        assert queja.campo.endswith("línea 1") and "REGI" in queja.esperado

    def test_tres_claves_son_demasiadas(self):
        assert la(cambia(DEL_BOE, self.REGI, self.REGI * 3), "SPFE-CLAVE-DE-REGIMEN").encontrado == "más de dos"
        assert las(cambia(DEL_BOE, self.REGI, self.REGI * 2), "SPFE-CLAVE-DE-REGIMEN") == []

    def test_un_impuesto_sin_lista_de_claves(self):
        assert la(cambia(DEL_BOE, ">IVA</cbc:ValueQualifier>", ">IRPF</cbc:ValueQualifier>"),
                  "SPFE-CLAVE-DE-REGIMEN").encontrado == "IRPF"

    def test_cada_impuesto_tiene_su_lista(self):
        """El 17 es del IGIC y no del IVA; el 20 no está en el IGIC."""
        del_igic_en_iva = cambia(DEL_BOE, "<cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA<",
                                 "<cbc:Value>17</cbc:Value><cbc:ValueQualifier>IVA<")
        queja = la(del_igic_en_iva, "SPFE-CLAVE-DE-REGIMEN")
        assert queja.encontrado == "17 de IVA"
        assert "la 17 existe en el IGIC y no en el IVA" in queja.mensaje
        assert "la 02 en el IVA y no en el IPSI" in queja.mensaje
        en_igic = cambia(del_igic_en_iva, ">IVA</cbc:ValueQualifier>", ">IGIC</cbc:ValueQualifier>")
        assert las(en_igic, "SPFE-CLAVE-DE-REGIMEN") == []
        assert la(cambia(en_igic, ">17<", ">20<"), "SPFE-CLAVE-DE-REGIMEN").encontrado == "20 de IGIC"

    def test_el_ejemplo_de_las_claves_sale_de_las_listas(self):
        listas = cius_es.LISTAS
        assert "17" in listas["L3B"].valores and "17" not in listas["L3A"].valores
        assert "02" in listas["L3A"].valores and "02" not in listas["L3C"].valores

    @pytest.mark.parametrize("nombre", [
        "XREGI", f"{L8}REGIX", f"{URN_DEL_BORRADOR}lin:REGI",
    ])
    def test_un_parecido_de_regi_no_es_una_clave_de_regimen(self, nombre):
        parecido = cambia(DEL_BOE, f"<cbc:Name>{L8}REGI</cbc:Name>", f"<cbc:Name>{nombre}</cbc:Name>")
        assert la(parecido, "SPFE-CLAVE-DE-REGIMEN").encontrado == "(falta)"

    def test_la_situacion_del_inmueble_fuera_de_la_lista(self):
        mala = cambia(DEL_BOE, self.REGI, self.REGI + _RCAT_CON_CALIFICADOR.format("05"))
        queja = la(mala, "SPFE-REFERENCIA-CATASTRAL")
        assert queja.encontrado == "05" and "BT-ES-23" in queja.campo

    def test_dos_referencias_catastrales_en_una_linea(self):
        dos = cambia(DEL_BOE, self.REGI, self.REGI + self.RCAT * 2)
        assert la(dos, "SPFE-REFERENCIA-CATASTRAL").encontrado == "más de una"

    def test_la_referencia_catastral_sin_referencia(self):
        sin = cambia(CON_LA_REFERENCIA_CON_CALIFICADOR, "<cbc:Value>9872023VH5797S0001WX</cbc:Value>", "")
        assert la(sin, "SPFE-REFERENCIA-CATASTRAL").encontrado == "(falta)"

    def test_la_informacion_adicional_se_llama_info(self):
        """BT-160 es libre en la norma, y en la orden tiene tres nombres. Hasta
        el 11-10-2026 no se medía, y la nota del alcance lo decía. Hasta el
        12-10-2026 era un ERROR: la interconectada puede llevar contenido
        adicional que cumpla la norma (apartado 3 del artículo 3). Lo vio el
        auditor."""
        queja = la(_con_la_propiedad("Color"), "SPFE-INFORMACION-ADICIONAL")
        assert queja.gravedad == AVISO and queja.encontrado == "Color"
        assert "(apartado 3)" in queja.mensaje and "apartado 2 del artículo 3" in queja.mensaje
        assert queja.campo.endswith("línea 1") and "INFO" in queja.esperado
        assert las(_con_la_propiedad(f"{L8}INFO"), "SPFE-INFORMACION-ADICIONAL") == []
        assert las(CON_LA_REFERENCIA_CON_CALIFICADOR, "SPFE-INFORMACION-ADICIONAL") == []

    def test_la_referencia_catastral_a_secas_se_lee_igual(self):
        a_secas = cambia(CON_LA_REFERENCIA_CON_CALIFICADOR, f"{L8}RCAT<", "RCAT<")
        assert las(a_secas, "SPFE-REFERENCIA-CATASTRAL") == []
        assert la(cambia(a_secas, ">01</cbc:ValueQualifier></cac:AdditionalItemProperty>",
                         ">05</cbc:ValueQualifier></cac:AdditionalItemProperty>"),
                  "SPFE-REFERENCIA-CATASTRAL").encontrado == "05"


class TestElTotalConRetenciones:
    """BT-115 cuando las únicas líneas de cobro son retenciones.

    Hasta el 19-10-2026, con cualquier línea de cobro el total a pagar no se
    miraba: 500,00 a pagar en una factura de 121,00 salía con una nota. La
    suma de retenciones sí tiene ruta (BT-ES-17), y se resta. Las facturas son
    de las pruebas, no ejemplos oficiales: el de la AEAT no trae totales.
    """

    @staticmethod
    def _a_pagar(xml: str, importe: str) -> str:
        return cambia(xml, '<cbc:PayableAmount currencyID="EUR">86.00</cbc:PayableAmount>',
                      f'<cbc:PayableAmount currencyID="EUR">{importe}</cbc:PayableAmount>')

    def test_la_de_la_orden_cuadra_restando_la_retencion(self):
        nota = la(DEL_BOE, "SPFE-TOTAL-A-PAGAR")
        assert nota.gravedad == NOTA and "cuadra restando las retenciones" in nota.mensaje
        assert "121,00 con IVA, menos 20,00 pagado y menos 15,00 retenido" in nota.mensaje
        assert "redondeo" not in nota.mensaje.split(")")[0]

    def test_un_total_que_no_cuadra_es_un_aviso(self):
        informe = factura.validar(self._a_pagar(DEL_BOE, "500.00").encode("utf-8"))
        queja = next(i for i in informe.incidencias if i.codigo == "SPFE-TOTAL-A-PAGAR")
        assert queja.gravedad == AVISO
        assert (queja.esperado, queja.encontrado) == ("86,00", "500.00")
        assert "parece que no" not in queja.mensaje
        assert "BR-CO-16" not in {i.codigo for i in informe.incidencias}

    def test_dice_si_falta_restar_la_retencion(self):
        queja = la(self._a_pagar(DEL_BOE, "101.00"), "SPFE-TOTAL-A-PAGAR")
        assert queja.gravedad == AVISO and "parece que no se ha restado" in queja.mensaje

    def test_sin_anticipo_lo_pagado_cuenta_cero(self):
        sin = quita(DEL_BOE, "  <cac:PrepaidPayment>", "</cac:PrepaidPayment>\n")
        sin = cambia(sin, '    <cbc:PrepaidAmount currencyID="EUR">20.00</cbc:PrepaidAmount>\n', "")
        assert la(self._a_pagar(sin, "106.00"), "SPFE-TOTAL-A-PAGAR").gravedad == NOTA
        assert la(sin, "SPFE-TOTAL-A-PAGAR").esperado == "106,00"

    def test_la_garantia_como_retencion_de_otros_tambien(self):
        """La retención de garantía de una obra escrita con el concepto 11:
        es el artificio que cabe, y el total se cuadra igual."""
        otros = cambia(DEL_BOE, "<cbc:TaxTypeCode>01</cbc:TaxTypeCode>", "<cbc:TaxTypeCode>11</cbc:TaxTypeCode>")
        assert la(self._a_pagar(otros, "500.00"), "SPFE-TOTAL-A-PAGAR").gravedad == AVISO

    def test_con_otras_lineas_de_cobro_no_se_cuadra(self):
        """Un suplido no tiene ruta para su importe: medio cuadre sería un
        aviso falso, y se queda la nota de siempre."""
        nota = la(self._a_pagar(CON_LOS_COBROS_DEL_BOE, "500.00"), "SPFE-TOTAL-A-PAGAR")
        assert nota.gravedad == NOTA and "no se ha comprobado" in nota.mensaje

    def test_sin_la_suma_de_retenciones_no_se_cuadra(self):
        sin = quita(DEL_BOE, "  <cac:WithholdingTaxTotal>", "</cac:WithholdingTaxTotal>\n")
        nota = la(self._a_pagar(sin, "500.00"), "SPFE-TOTAL-A-PAGAR")
        assert nota.gravedad == NOTA and "no se ha comprobado" in nota.mensaje

    def test_la_ficha_lo_cuenta(self):
        ficha = glosario.CODIGOS["SPFE-TOTAL-A-PAGAR"]
        assert "BT-ES-17" in ficha and "aviso" in ficha


class TestLineasDeCobro:

    @pytest.mark.parametrize("identificador", [
        f"{L7}RETEX",                       # un parecido
        f"X{L7}RETE",                       # el calificador con algo delante
        f"{URN_DEL_BORRADOR}IEDMT",         # la de la orden, con la URN de abril
        "OTRA",
    ])
    def test_lo_que_no_es_de_la_l7_no_vale(self, identificador):
        mala = cambia(DEL_BOE, f"{L7}RETE<", f"{identificador}<")
        queja = la(mala, "SPFE-LINEA-DE-COBRO")
        assert queja.gravedad == ERROR and queja.encontrado == identificador

    def test_dos_retenciones_son_dos_aunque_se_escriban_distinto(self):
        """Una con el calificador y otra sin él son dos grupos de retenciones,
        y la orden admite uno (`0..1`)."""
        otra = ("  <cac:CollectionInvoiceLine>\n    <cbc:ID>RETE</cbc:ID>\n"
                "    <cac:Item><cbc:Name>Otra retencion</cbc:Name></cac:Item>\n  </cac:CollectionInvoiceLine>\n")
        doble = cambia(DEL_BOE, "  <cac:InvoiceLine>", otra + "  <cac:InvoiceLine>")
        assert "retenciones" in la(doble, "SPFE-LINEA-DE-COBRO").mensaje

    def test_dos_suplidos_si_valen(self):
        assert las(cambia(CON_LOS_COBROS_DEL_BOE, "  <cac:InvoiceLine>",
                          "  <cac:CollectionInvoiceLine>\n    <cbc:ID>SUPL</cbc:ID>\n"
                          "    <cac:Item><cbc:Name>Otro</cbc:Name></cac:Item>\n"
                          "  </cac:CollectionInvoiceLine>\n  <cac:InvoiceLine>"),
                   "SPFE-LINEA-DE-COBRO") == []

    def test_la_retencion_con_un_concepto_fuera_de_l5_y_otro_esquema(self):
        malo = cambia(cambia(DEL_BOE, "<cbc:TaxTypeCode>01<", "<cbc:TaxTypeCode>99<"),
                      "<cbc:ID>WTH<", "<cbc:ID>IRPF<")
        queja = la(malo, "SPFE-RETENCION")
        assert "BT-ES-21" in queja.mensaje and '"99"' in queja.mensaje
        assert "el esquema WTH (BG-ES-4)" in queja.mensaje

    def test_la_retencion_sin_su_linea_de_cobro(self):
        sin = quita(DEL_BOE, "  <cac:CollectionInvoiceLine>", "</cac:CollectionInvoiceLine>\n")
        assert "BT-ES-16" in la(sin, "SPFE-RETENCION").mensaje

    def test_la_linea_de_retencion_sin_retenciones(self):
        sin = quita(DEL_BOE, "  <cac:WithholdingTaxTotal>", "</cac:WithholdingTaxTotal>\n")
        assert "la suma de retenciones (BT-ES-17)" in la(sin, "SPFE-RETENCION").mensaje

    def test_la_retencion_a_secas_se_mide_igual(self):
        malo = cambia(CON_LA_RETENCION_SIN_CALIFICADOR, "<cbc:TaxTypeCode>01<", "<cbc:TaxTypeCode>99<")
        assert '"99"' in la(malo, "SPFE-RETENCION").mensaje

    def test_la_suma_de_retenciones_es_la_suma_de_cada_una(self):
        """«Sumatorio de todas las retenciones practicadas en factura» (BT-ES-17).

        Hasta el 11-10-2026 se pedía que estuviera y no se sumaba: 999 sobre
        una retención de 15 salía sin una queja, y la nota del alcance no decía
        que eso no se miraba. Lo vio el revisor de promesas.
        """
        queja = la(con_la_retencion("15.00", total="999.00"), "SPFE-RETENCION")
        assert queja.gravedad == ERROR and "(BT-ES-17)" in queja.campo
        assert (queja.esperado, queja.encontrado) == ("15,00", "999.00")

    def test_cada_retencion_es_la_base_por_el_porcentaje(self):
        """«Resultado de aplicar a la Base imponible de la retención, el
        porcentaje» (BT-ES-19). 77 sobre 100 al 15 % también pasaba."""
        queja = la(con_la_retencion("77.00"), "SPFE-RETENCION")
        assert queja.gravedad == ERROR and "(BT-ES-19)" in queja.campo
        assert (queja.esperado, queja.encontrado) == ("15,00", "77.00")

    def test_a_menos_de_una_unidad_es_nota_y_dice_con_que_base(self):
        """La orden no da margen, y aquí se le da el de la cuota del IVA, que
        es la misma cuenta: se dice en una nota, como IVA-CUOTA-REDONDEO."""
        nota = la(con_la_retencion("15.40"), "SPFE-RETENCION")
        assert nota.gravedad == NOTA and "BR-CO-17" in nota.mensaje
        assert (nota.esperado, nota.encontrado) == ("15,00", "15.40")

    def test_dos_retenciones_se_suman(self):
        dos = cambia(con_la_retencion("15.00", total="24.50"),
                     "    </cac:TaxSubtotal>\n  </cac:WithholdingTaxTotal>",
                     "    </cac:TaxSubtotal>\n    <cac:TaxSubtotal>\n"
                     '      <cbc:TaxableAmount currencyID="EUR">50.00</cbc:TaxableAmount>\n'
                     '      <cbc:TaxAmount currencyID="EUR">9.50</cbc:TaxAmount>\n'
                     "      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>19</cbc:Percent>\n"
                     "        <cac:TaxScheme><cbc:ID>WTH</cbc:ID><cbc:TaxTypeCode>01</cbc:TaxTypeCode>"
                     "</cac:TaxScheme>\n"
                     "      </cac:TaxCategory>\n    </cac:TaxSubtotal>\n  </cac:WithholdingTaxTotal>")
        assert las(dos, "SPFE-RETENCION") == []
        queja = la(cambia(dos, ">24.50<", ">15.00<"), "SPFE-RETENCION")
        assert (queja.esperado, queja.encontrado) == ("24,50", "15.00")

    def test_el_total_a_pagar_nombra_la_l7_de_la_orden(self):
        nota = la(CON_LOS_COBROS_DEL_BOE, "SPFE-TOTAL-A-PAGAR")
        assert "IEDMT" in nota.mensaje and "BT-115" in nota.mensaje


class TestCategoriasDeLaOrden:

    @pytest.mark.parametrize(("xml", "categoria"), [
        (CON_LA_N, "N"), (CON_LA_D, "D"), (CON_LA_F, "F"),
    ], ids=["N", "D", "F"])
    def test_la_n_la_d_y_la_f_se_aceptan_y_se_dice_con_que_base(self, xml, categoria):
        nota = la(xml, "SPFE-CATEGORIA")
        assert nota.gravedad == NOTA and nota.encontrado == categoria
        assert "lista L4 de la orden" in nota.mensaje and "no se ha comprobado" in nota.mensaje
        # Las cuatro reglas que no se les aplican, con su nombre: decía «los
        # tipos de IVA» y callaba IVA-CATEGORIA-RARA (el revisor de promesas,
        # antes de publicar).
        for regla in ("BR-CL-17", "BR-CL-18", "IVA-CATEGORIA-RARA", "IVA-TIPO"):
            assert regla in nota.mensaje, regla

    def test_la_n_tiene_nombre_en_los_mensajes_de_la_norma(self):
        """Ni «categoría no reconocida» en el mismo informe que dice que la admite.

        Con la cuota del recargo mal, BR-CO-17 hablaba de «N (categoría no
        reconocida)» y la NOTA SPFE-CATEGORIA de la misma factura decía que la
        N está en la L4 de la orden. Lo vio la revisión del 07-10-2026, antes
        de publicar. El nombre va aparte de `iva.CATEGORIAS`, que es la lista
        de la norma y la que da el «Las admitidas son…» de IVA-CATEGORIA-RARA.
        """
        mala = cambia(CON_EL_RECARGO_EN_EL_DESGLOSE,
                      '<cbc:TaxAmount currencyID="EUR">5.20</cbc:TaxAmount>',
                      '<cbc:TaxAmount currencyID="EUR">9.00</cbc:TaxAmount>')
        cuota = next(i for i in factura.validar(mala.encode("utf-8")).errores
                     if i.codigo == "BR-CO-17")
        assert "no reconocida" not in cuota.mensaje and "no reconocida" not in cuota.campo
        assert "N (regímenes nacionales" in cuota.mensaje
        for codigo in ("N", "D", "F"):
            assert "no reconocida" not in iva.nombre_categoria(codigo)
            assert codigo not in iva.CATEGORIAS
        assert iva.nombre_categoria("X") == "X (categoría no reconocida)"

    def test_un_abono_no_recibe_la_lista_de_la_orden(self):
        """Al abono no se le mide con el anexo, y por eso tampoco con su L4."""
        abono = (CON_LA_N.replace("Invoice-2", "CreditNote-2")
                 .replace("<Invoice ", "<CreditNote ").replace("</Invoice>", "</CreditNote>")
                 .replace("<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>",
                          "<cbc:CreditNoteTypeCode>381</cbc:CreditNoteTypeCode>")
                 .replace("<cac:InvoiceLine>", "<cac:CreditNoteLine>")
                 .replace("</cac:InvoiceLine>", "</cac:CreditNoteLine>")
                 .replace("<cbc:InvoicedQuantity", "<cbc:CreditedQuantity")
                 .replace("</cbc:InvoicedQuantity>", "</cbc:CreditedQuantity>"))
        assert "<Invoice " not in abono and "<cac:InvoiceLine>" not in abono
        informe = factura.validar(abono.encode("utf-8"))
        assert {"BR-CL-17", "BR-CL-18"} <= {i.codigo for i in informe.errores}
        assert "SPFE-CATEGORIA" not in {i.codigo for i in informe.incidencias}
        # Y la queja dice de dónde sale la N, como a cualquier otra factura
        # que no se mide con el anexo.
        queja = next(i for i in informe.errores if i.codigo == "BR-CL-18")
        assert "La N es de la lista L4" in queja.mensaje
        # Y dice por qué no vale aquí: decía «las que van en UBL y declaran el
        # de la orden», y este abono es UBL y lo declara.
        assert "no como abono (CreditNote)" in queja.mensaje

    def test_la_n_no_tapa_un_codigo_que_no_es_de_ninguna_lista(self):
        """La N se añade a la lista; la queja no se borra después."""
        con_una_x = cambia(CON_LA_N, "<cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>",
                           "<cbc:ID>X</cbc:ID><cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>")
        queja = next(i for i in factura.validar(con_una_x.encode("utf-8")).errores
                     if i.codigo == "BR-CL-18")
        assert queja.encontrado == "X"

    def test_sin_declarar_la_solucion_publica_la_n_se_mide_como_siempre(self):
        """Fuera de la solución pública rige la lista de la norma: lo decidió
        el titular el 11-10-2026."""
        sin = cambia(CON_LA_N, ESPECIFICACION, "urn:cen.eu:en16931:2026")
        errores = {i.codigo for i in factura.validar(sin.encode("utf-8")).errores}
        assert {"BR-CL-17", "BR-CL-18"} <= errores

    @pytest.mark.parametrize(("xml", "categoria"), [
        (CON_LA_N, "N"), (CON_LA_D, "D"), (CON_LA_F, "F"),
    ], ids=["N", "D", "F"])
    def test_sin_declararla_el_mensaje_dice_de_donde_sale_y_que_falta(self, xml, categoria):
        """Hasta el 11-10-2026 decía «no es de UNCL 5305» y nada más.

        Y mandaba a buscar el fallo donde no está: quien escribió la N la
        sacó de la orden, y lo que le falta es declarar la solución pública.
        Medido ese día sobre `bbea1b2`, con la N y con la D sin declararla.
        """
        sin = cambia(xml, ESPECIFICACION, "urn:cen.eu:en16931:2026")
        quejas = [i for i in factura.validar(sin.encode("utf-8")).errores
                  if i.codigo in ("BR-CL-17", "BR-CL-18")]
        assert {q.codigo for q in quejas} == {"BR-CL-17", "BR-CL-18"}
        for queja in quejas:
            assert f"La {categoria} es de la lista L4 de la Orden HAC/1028/2026" in queja.mensaje
            assert "BT-24" in queja.mensaje and ESPECIFICACION in queja.mensaje
            assert "no es de UNCL 5305 tal como la recoge la norma" in queja.mensaje

    def test_no_dice_que_la_d_y_la_f_no_son_de_la_untdid_5305(self):
        """Lo son, desde la edición D16A: el margen de las agencias de viajes y
        el de los bienes usados. No son de la lista que la norma admite, que es
        otra cosa. El mensaje y el glosario decían «no es de UNCL 5305» a
        secas. Lo vio el auditor el 11-10-2026, y se leyó en edifactory ese día."""
        for codigo in ("BR-CL-17", "BR-CL-18"):
            assert "no es de UNCL 5305 tal como la recoge la norma" in glosario.CODIGOS[codigo]
            assert "no es de UNCL 5305." not in glosario.CODIGOS[codigo]

    def test_la_frase_nombra_solo_lo_que_es_de_la_orden(self):
        """Una X junto a la N: la queja lleva las dos, y la frase solo la N."""
        sin = cambia(CON_LA_N, ESPECIFICACION, "urn:cen.eu:en16931:2026")
        con_una_x = cambia(sin, "<cac:ClassifiedTaxCategory><cbc:ID>S<",
                           "<cac:ClassifiedTaxCategory><cbc:ID>X<")
        queja = next(i for i in factura.validar(con_una_x.encode("utf-8")).errores
                     if i.codigo == "BR-CL-18")
        assert set(queja.encontrado.split(", ")) == {"N", "X"}
        assert "La N es de la lista L4" in queja.mensaje and "la X" not in queja.mensaje
        solo_la_x = cambia(cambia(DEL_BOE, ESPECIFICACION, "urn:cen.eu:en16931:2026"),
                           "<cac:ClassifiedTaxCategory><cbc:ID>S<", "<cac:ClassifiedTaxCategory><cbc:ID>X<")
        queja = next(i for i in factura.validar(solo_la_x.encode("utf-8")).errores
                     if i.codigo == "BR-CL-18")
        assert "L4" not in queja.mensaje and "HAC/1028/2026" not in queja.mensaje

    def test_la_base_de_la_n_no_se_compara_pero_su_cuota_si(self):
        """La base no se ata a las líneas; BR-CO-17 sigue atando la cuota."""
        mala = cambia(CON_EL_RECARGO_EN_EL_DESGLOSE,
                      '<cbc:TaxAmount currencyID="EUR">5.20</cbc:TaxAmount>',
                      '<cbc:TaxAmount currencyID="EUR">9.00</cbc:TaxAmount>')
        errores = {i.codigo for i in factura.validar(mala.encode("utf-8")).errores}
        assert "BR-CO-17" in errores and "IVA-BASE" not in errores


class TestElBt47DeLaOrden:

    def test_bt47_de_la_orden_solo_cuenta_con_loc_y_fc(self):
        sin_fc = cambia(CON_AE_Y_EL_COMPRADOR_EN_BT47, ' schemeID="FC">A12345674', ">A12345674")
        errores = {i.codigo for i in factura.validar(sin_fc.encode("utf-8")).errores}
        assert "BR-AE-02" in errores
        # Y la otra mitad: el FC bajo otro impuesto que «LOC» tampoco es el
        # BT-47 de la orden. Hasta la revisión del 07-10-2026 solo se quitaba
        # el FC, y el filtro de «LOC» se podía borrar sin que nada fallara.
        otro_impuesto = cambia(
            CON_AE_Y_EL_COMPRADOR_EN_BT47,
            'schemeID="FC">A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID>',
            'schemeID="FC">A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>IRPF</cbc:ID>')
        errores = {i.codigo for i in factura.validar(otro_impuesto.encode("utf-8")).errores}
        assert "BR-AE-02" in errores

    @pytest.mark.parametrize(("viejo", "nuevo"), [
        ('schemeID="FC">A12345674', 'schemeID="FC ">A12345674'),
        ("A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID>",
         "A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC </cbc:ID>"),
        ("A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>LOC</cbc:ID>",
         "A12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>\n LOC\n</cbc:ID>"),
    ], ids=["FC con un espacio", "LOC con un espacio", "LOC entre saltos de línea"])
    def test_los_espacios_de_loc_y_fc_se_leen_igual_en_las_dos_reglas(self, viejo, nuevo):
        """SPFE-NIF y BR-AE-02 no pueden decir lo contrario del mismo NIF."""
        con_espacios = cambia(CON_AE_Y_EL_COMPRADOR_EN_BT47, viejo, nuevo)
        errores = {i.codigo for i in factura.validar(con_espacios.encode("utf-8")).errores}
        assert errores == set()

    def test_sin_desglose_el_bt47_de_la_orden_sigue_contando(self):
        """La rama de BR-CO-18 también mira BR-AE-02, y tiene que mirarlo igual."""
        sin_desglose = quita(CON_AE_Y_EL_COMPRADOR_EN_BT47, "  <cac:TaxTotal>", "</cac:TaxTotal>\n")
        errores = {i.codigo for i in factura.validar(sin_desglose.encode("utf-8")).errores}
        assert "BR-CO-18" in errores and "BR-AE-02" not in errores

    def test_sin_declarar_la_solucion_publica_bt47_es_el_de_la_norma(self):
        sin = cambia(CON_AE_Y_EL_COMPRADOR_EN_BT47, ESPECIFICACION, "urn:cen.eu:en16931:2026")
        errores = {i.codigo for i in factura.validar(sin.encode("utf-8")).errores}
        assert "BR-AE-02" in errores


class TestLoQueDicenLosMensajes:

    def casos(self):
        return [
            *LAS_DE_LA_ORDEN.values(), EJEMPLO, SIN_LOS_BG24,
            TestLoQueSoloDeciaElBorrador().con_el_borrador(),
            cambia(DEL_BOE, "<cbc:InvoiceTypeCode>380<", "<cbc:InvoiceTypeCode>381<"),
            rectificativa_con(adjunto("RECT:TIPO", "R9")),
            cambia(DEL_BOE, ESPECIFICACION,
                   "urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:2.0.0:extended"),
        ]

    def test_ningun_mensaje_dice_que_la_orden_no_esta_publicada(self):
        """Hasta el 07-10-2026 varios decían que el anexo nuevo «no está publicado»."""
        for xml in self.casos():
            for i in spfe(xml):
                assert "no está publicad" not in i.mensaje, (i.codigo, i.mensaje)
                assert "anexo nuevo" not in i.mensaje, (i.codigo, i.mensaje)

    def test_ninguno_dice_que_algo_del_borrador_todavia_se_acepta(self):
        """Hasta el 11-10-2026 era verdad, y lo decían la nota y el glosario."""
        for xml in self.casos():
            for i in spfe(xml):
                assert "todavía se acepta" not in i.mensaje, (i.codigo, i.mensaje)
        for codigo, texto in glosario.CODIGOS.items():
            if codigo.startswith("SPFE"):
                assert "todavía se acepta" not in texto, codigo


class TestLoQueDiceLaBitacora:
    """El artículo de las rectificativas cuenta qué hace Glosa-e «hoy».

    El 11-10-2026, con las reglas ya al texto de la orden, seguía diciendo que
    la extensión de abril «todavía se acepta» y que lo que falta sale en AVISO
    o en NOTA: publicado, y falso desde ese día. Lo vio el revisor de promesas.
    Cada frase de esa sección va aquí con la factura que la comprueba: si la
    regla cambia, la prueba se pone en rojo y obliga a reescribir el artículo.
    """

    ARTICULO = (pathlib.Path(__file__).resolve().parents[1]
                / "web" / "bitacora" / "rectificativas-sin-bg-es-1.html")

    def hoy(self) -> str:
        html = self.ARTICULO.read_text(encoding="utf-8")
        seccion = html.split("Qué hace Glosa-e con esto, hoy</h2>", 1)[1].split("<p>Es gratis", 1)[0]
        return " ".join(re.sub(r"<[^>]+>", "", seccion).split())

    def rectificativa(self, xml: str) -> list[Incidencia]:
        return las(xml, "SPFE-RECTIFICATIVA")

    def test_ya_no_dice_lo_de_antes(self):
        for viejo in ("todavía se acepta", "no la da por mala", "sale como AVISO",
                      "cualquiera de los dos esquemas", "todavía no se comprueban"):
            assert viejo not in self.hoy(), viejo

    def test_sin_el_tipo_ni_la_modalidad_es_error(self):
        assert "y si no los trae es un ERROR" in self.hoy()
        assert [i.gravedad for i in self.rectificativa(rectificativa_con())] == [ERROR]

    def test_con_el_esquema_de_abril_no_se_lee(self):
        assert "con el de abril, el que lleva ubl:, no se lee como dato de la rectificativa" in self.hoy()
        de_abril = rectificativa_con(adjunto("RECT:TIPO", "R1", calificador=URN_DEL_BORRADOR),
                                     adjunto("RECT:MODALIDAD", "I", calificador=URN_DEL_BORRADOR))
        queja, = self.rectificativa(de_abril)
        assert queja.gravedad == ERROR and queja.encontrado.startswith("falta el tipo")

    def test_un_codigo_que_falta_o_no_es_de_su_lista_es_error(self):
        assert "si el código falta o no está en su lista, también es ERROR" in self.hoy()
        for tipo in ("R9", ""):
            quejas = self.rectificativa(rectificativa_con(adjunto("RECT:TIPO", tipo),
                                                          adjunto("RECT:MODALIDAD", "I")))
            assert [i.gravedad for i in quejas] == [ERROR], tipo

    def test_de_los_importes_se_mira_la_forma_y_no_la_cifra(self):
        hoy = self.hoy()
        assert ("cada uno con un código de L2.C y su importe en la descripción, cinco como "
                "mucho, y en una sustitución") in hoy
        assert "Que la cifra sea la buena no se comprueba." in hoy
        cuatro = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "S"),
                                   *[adjunto("RECT:IMPORTES", "Base", "1.00")] * 4)
        assert "Con un código repetido sale un AVISO" in hoy
        assert [i.gravedad for i in self.rectificativa(cuatro)] == [AVISO]
        con_i = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "I"),
                                  adjunto("RECT:IMPORTES", "Base", "1.00"))
        assert "con la modalidad I, otro AVISO" in hoy
        assert [i.gravedad for i in self.rectificativa(con_i)] == [AVISO]
        assert self.rectificativa(cambia(CON_LOS_IMPORTES, ">100.00</cbc:DocumentDescription>",
                                         ">999.00</cbc:DocumentDescription>")) == []
        sin_cifra = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "S"),
                                      adjunto("RECT:IMPORTES", "Base"))
        assert [i.gravedad for i in self.rectificativa(sin_cifra)] == [ERROR]

    def test_la_sustitucion_sin_importes_es_nota(self):
        assert "si la modalidad es S y no trae importes, sale una NOTA y no un fallo" in self.hoy()
        sin = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "S"))
        assert [i.gravedad for i in self.rectificativa(sin)] == [NOTA]


# --- Que salga del anexo, y que se niegue si el anexo cambia -------------------


def _recargar_con(monkeypatch, campos):
    """Vuelve a importar el módulo con otra tabla, y lo deja como estaba.

    La excepción se compara por nombre y no por clase: al recargar, el módulo
    define su `AnexoCambiado` otra vez, y la que se lanza ya no es la misma
    clase que había antes de recargar.
    """
    monkeypatch.setattr(cius_es, "CAMPOS", tuple(campos))
    try:
        importlib.reload(solucion_publica)
    except LookupError as negativa:
        assert type(negativa).__name__ == "AnexoCambiado"
        return str(negativa)
    finally:
        monkeypatch.undo()
        importlib.reload(solucion_publica)
    return None


# La base de la retención (BT-ES-18) movida a las líneas de cobro, y los dos
# módulos otra vez: el que calcula las rutas y el que las usa.
_MOVER_UNA_RUTA = """
from dataclasses import replace
from importlib import reload
from validador import cius_es, sintaxis, solucion_publica
fila = next(c for c in cius_es.CAMPOS if c.id == "BT-ES-18")
movida = fila.ruta.replace("cac:WithholdingTaxTotal/cac:TaxSubtotal", "cac:CollectionInvoiceLine")
assert movida != fila.ruta
cius_es.CAMPOS = tuple(replace(c, ruta=movida) if c is fila else c for c in cius_es.CAMPOS)
try:
    reload(sintaxis)
    reload(solucion_publica)
    print("importa")
except LookupError as negativa:
    print(type(negativa).__name__, negativa)
"""


def _con(identificador, termino="", **cambios):
    return [replace(c, **cambios) if c.id == identificador and termino in c.termino else c
            for c in cius_es.CAMPOS]


def _diciendo(identificador, dice, en_vez):
    """La tabla con una frase cambiada en la descripción o la ruta de una fila."""
    cambiadas = []
    for c in cius_es.CAMPOS:
        if c.id == identificador and (dice in c.descripcion or dice in c.ruta):
            c = replace(c, descripcion=c.descripcion.replace(dice, en_vez),
                        ruta=c.ruta.replace(dice, en_vez))
        cambiadas.append(c)
    assert cambiadas != list(cius_es.CAMPOS), f"{identificador} no dice «{dice}»"
    return cambiadas


class TestSeNiegaSiElAnexoCambia:
    """Cada forma de cambiar un anexo deja el módulo sin importar."""

    def test_si_un_campo_exigido_pasa_a_opcional(self, monkeypatch):
        negativa = _recargar_con(monkeypatch, _con("BT-ES-17", cardinalidad="0..1"))
        assert negativa and "BT-ES-17" in negativa and "0..1" in negativa

    def test_si_un_grupo_que_no_se_repetia_se_repite(self, monkeypatch):
        negativa = _recargar_con(monkeypatch, _con("BG-24", "QR FISCAL", cardinalidad="0..n"))
        assert negativa and "QR FISCAL" in negativa and "0..n" in negativa

    def test_si_un_valor_fijo_ya_no_es_el_que_era(self, monkeypatch):
        negativa = _recargar_con(monkeypatch, _diciendo("BT-6", "usar «EUR»", "usar «USD»"))
        assert negativa and "usar EUR" in negativa

    def test_si_un_documento_ya_no_es_de_l10(self, monkeypatch):
        negativa = _recargar_con(monkeypatch, _diciendo("BT-122", "usar «QR»", "usar «QRF»"))
        assert negativa and "L10" in negativa

    def test_si_una_linea_de_cobro_ya_no_es_de_l7(self, monkeypatch):
        negativa = _recargar_con(monkeypatch, _diciendo("BT-ES-10", "usar «SUPL»", "usar «SUPLE»"))
        assert negativa and "L7" in negativa

    def test_si_el_impuesto_del_nif_cambia_en_una_parte_y_no_en_otra(self, monkeypatch):
        negativa = _recargar_con(monkeypatch, _diciendo("BT-31", "«VAT»", "«IVA»"))
        assert negativa and "comprador" in negativa

    @pytest.mark.parametrize("identificador, viejo, nuevo", [
        ("BT-ES-17", "Sumatorio de todas", "Suma de algunas"),
        ("BT-ES-19", "Resultado de aplicar", "Resultado de restar"),
        ("BT-3", "hasta tres grupos", "hasta dos grupos"),
        ("BG-24", "rectificación por sustitución de la factura original",
         "rectificación de la factura original"),
        ("BT-ES-2", "o en dicha fecha", "o después"),
        ("BT-ES-2", "coincidente o posterior", "anterior"),
        ("BT-7", "siempre que sea diferente", "aunque no sea diferente"),
        ("BT-30", "venga informado el campo BT-32", "venga informado el campo BT-31"),
        ("BT-30", "(NIF) del vendedor", "(NIF) del registro"),
        ("BT-31", "prefijo correspondiente a España", "prefijo del país"),
        ("BT-48", "a efectos de IVA del vendedor", "a efectos de IVA del comprador"),
        ("BT-121", "VATEX-EU o VATEX-ES", "VATEX-EU"),
        ("BT-ES-8", "Resultado de aplicar", "Resultado de sumar"),
        ("BT-ES-8", "El mismo importe debe consignarse en dos rutas distintas",
         "El importe debe consignarse en una de las rutas"),
        ("BT-ES-14", "Cuota resultante de aplicar", "Cuota resultante de sumar"),
        ("BT-160", "«INFO»", "«INFORMACION»"),
        ("BT-160", "«REGI»", "«REGIX»"),
        ("BT-160", "«RCAT»", "«RCATX»"),
        ("BT-ES-26", "Número de referencia de la autorización concedida",
         "Fecha de la autorización concedida"),
    ])
    def test_si_cambia_una_cuenta_o_un_limite_que_se_comprueba(self, monkeypatch, identificador,
                                                              viejo, nuevo):
        """Las dos cuentas de las retenciones y lo que se dice de los importes
        rectificados salen de la descripción de su fila desde el 11-10-2026."""
        negativa = _recargar_con(monkeypatch, _diciendo(identificador, viejo, nuevo))
        assert negativa and identificador in negativa

    @pytest.mark.parametrize("identificador, cambios, dice", [
        ("BT-119", {"cardinalidad": "0..1"}, "0..1"),
        ("BT-ES-2", {"cardinalidad": "0..n"}, "0..n"),
        ("BT-30", {"ruta": "/in:Invoice/cac:AccountingSupplierParty/cac:Party/cbc:EndpointID"}, "ruta"),
        ("BT-ES-22", {"cardinalidad": "0..1"}, "0..1"),
        ("BT-ES-9", {"tipo": "Código (L8)"}, "L9"),
        ("BG-ES-2", {"cardinalidad": "0..1"}, "0..1"),
        ("BG-ES-3", {"cardinalidad": "1..n"}, "1..n"),
        ("BG-32", {"termino": "INFORMACIÓN ADICIONAL", "cardinalidad": "0..1"}, "0..1"),
        ("BT-161", {"termino": "Información adicional", "cardinalidad": "0..1"}, "0..1"),
        ("BT-ES-26", {"cardinalidad": "0..1"}, "0..1"),
        ("BG-24", {"termino": "AUTORIZACIÓN DE FACTURACIÓN", "cardinalidad": "0..1"}, "0..1"),
        ("BG-ES-4", {"cardinalidad": "1..n"}, "1..n"),
    ])
    def test_si_cambia_lo_que_se_lee_de_los_campos_de_la_norma(self, monkeypatch, identificador,
                                                              cambios, dice):
        negativa = _recargar_con(monkeypatch, _con(identificador, **cambios))
        assert negativa and identificador in negativa and dice in negativa

    @pytest.mark.parametrize(("lista", "cambio"), [
        ("L9", {"calificador": "urn:aeat:names:specification:schema:tax:"}),
        ("L8", {"valores": {**cius_es.LISTAS["L8"].valores, "OTRA": "Otra propiedad."}}),
    ])
    def test_si_cambia_una_lista_que_se_lee_entera(self, monkeypatch, lista, cambio):
        """La L9 se compara sin calificador, y la L8 son las tres propiedades
        de la línea: si una lista nueva cambia eso, el módulo no importa."""
        listas = dict(cius_es.LISTAS)
        listas[lista] = replace(listas[lista], **cambio)
        monkeypatch.setattr(cius_es, "LISTAS", listas)
        negativa = _recargar_con(monkeypatch, cius_es.CAMPOS)
        assert negativa and lista in negativa

    def test_con_la_tabla_de_verdad_no_se_niega(self, monkeypatch):
        assert _recargar_con(monkeypatch, cius_es.CAMPOS) is None

    def test_si_el_anexo_mueve_una_ruta_fuera_de_su_grupo_el_modulo_no_importa(self):
        """La tercera forma, entera: la tabla con una ruta movida.

        Las rutas las calcula `sintaxis` al importarse, así que recargar solo
        este módulo no la ve; y recargar `sintaxis` en mitad de la suite deja a
        los demás módulos con objetos de la copia vieja. Va en un proceso
        aparte. Hasta el 11-10-2026 solo se probaba llamando a `_relativa`, y
        el README decía que las tres formas estaban provocadas. Lo vio el
        auditor.
        """
        salida = subprocess.run(
            [sys.executable, "-c", _MOVER_UNA_RUTA],
            cwd=pathlib.Path(__file__).resolve().parents[1], capture_output=True,
            text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        assert salida.stdout.startswith("AnexoCambiado"), (salida.stdout, salida.stderr)
        assert "ya no cuelga" in salida.stdout

    def test_si_una_ruta_deja_de_colgar_de_su_grupo(self):
        with pytest.raises(solucion_publica.AnexoCambiado, match="ya no cuelga"):
            solucion_publica._relativa("./cac:WithholdingTaxTotal/cbc:TaxAmount",
                                       "./cac:CollectionInvoiceLine")

    def test_y_despues_de_negarse_vuelve_a_ser_el_de_siempre(self):
        assert codigos(DEL_BOE) == set()


class TestDeDondeSale:

    def test_el_readme_dice_cuantos_codigos_hay(self):
        """La cifra en negrita se quedó en 25 cuando ya eran 27: la tanda que
        añadió dos cambió la frase de debajo y no esa. Lo vio la tanda
        siguiente, el 11-10-2026. Se cuentan los códigos que el módulo escribe."""
        codigo = pathlib.Path(solucion_publica.__file__).read_text(encoding="utf-8")
        hay = len(set(re.findall(r'"(SPFE-[A-Z-]+)"', codigo)))
        raiz = pathlib.Path(__file__).resolve().parents[1]
        readme = " ".join((raiz / "README.md").read_text(encoding="utf-8").split())
        assert re.findall(r"\*\*(\d+) códigos, todos con el prefijo `SPFE-`\*\*", readme) == [str(hay)]
        assert re.findall(r"llegaron a (\d+) con lo que la orden pide", readme) == [str(hay)]

    @con_esquema
    def test_las_rutas_europeas_que_se_usan_existen_en_ubl_2_5(self):
        """El anexo no da ruta a los campos que la norma ya tiene, y aquí van
        por la vinculación de 2017. Que esos elementos estén en UBL 2.5 donde se
        buscan sí se puede comprobar."""
        tipo_de, hijos_de = _esquema_de_ubl()
        rutas = [
            "cbc:CustomizationID", "cbc:ProfileID", "cbc:CopyIndicator", "cbc:InvoiceTypeCode",
            "cac:InvoiceLine/cbc:ID", "cac:AllowanceCharge/cbc:ChargeIndicator",
            "cac:InvoiceLine/cac:AllowanceCharge/cbc:ChargeIndicator",
            "cbc:DocumentCurrencyCode", "cbc:TaxCurrencyCode",
            "cac:LegalMonetaryTotal/cbc:PrepaidAmount",
            "cac:LegalMonetaryTotal/cbc:PayableAmount",
            "cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
            "cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
            "cac:BillingReference/cac:InvoiceDocumentReference/cbc:IssueDate",
            "cac:AllowanceCharge/cbc:AllowanceChargeReason",
            "cac:AllowanceCharge/cac:TaxCategory/cbc:ID",
            "cac:InvoiceLine/cac:AllowanceCharge/cbc:AllowanceChargeReason",
            "cac:InvoiceLine/cac:Item/cac:ClassifiedTaxCategory/cbc:ID",
            "cac:InvoiceLine/cac:Item/cac:AdditionalItemProperty/cbc:Value",
            "cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:ID",
            "cac:AdditionalDocumentReference/cbc:ID",
            "cac:AdditionalDocumentReference/cbc:DocumentDescription",
            "cbc:TaxPointDate", "cac:InvoicePeriod/cbc:StartDate",
            "cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:CompanyID",
            "cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:Percent",
            "cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TaxExemptionReasonCode",
        ]
        for parte in ("StreetName", "CityName", "PostalZone", "CountrySubentity"):
            for quien in ("AccountingSupplierParty", "AccountingCustomerParty"):
                rutas.append(f"cac:{quien}/cac:Party/cac:PostalAddress/cbc:{parte}")
                rutas.append(f"cac:{quien}/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode")
        fallos = {r: _andar(r, tipo_de, hijos_de) for r in rutas}
        assert {r: f for r, f in fallos.items() if f} == {}

    def test_las_lineas_de_cobro_son_las_de_l7_y_solo_la_retencion_va_una_vez(self):
        # Con la lista escrita aquí: comparar `_L7` con la tabla era comparar
        # la tabla consigo misma, y no podía fallar. Lo vio el auditor.
        assert solucion_publica._L7 == ("SUPL", "MINO", "RETE", "IEDMT", "OTROS")
        assert solucion_publica._UNO_POR_FACTURA == {"RETE": "RETENCIONES"}

    def test_los_documentos_son_los_de_l10_y_cada_uno_con_su_lista(self):
        # Lo mismo: el módulo ya se niega a importar si no son los de L10.
        assert set(solucion_publica._DOCUMENTOS) == {
            "RECT:TIPO", "RECT:MODALIDAD", "RECT:IMPORTES", "QR", "AUT"}
        assert solucion_publica._LISTA_DEL_DOCUMENTO == {
            "RECT:TIPO": "L2.A", "RECT:MODALIDAD": "L2.B", "RECT:IMPORTES": "L2.C"}
        assert solucion_publica._TIPOS_DE_QR == ("VERIFACTU", "TICKETBAI")

    def test_las_categorias_de_mas_son_las_mismas_en_los_dos_sitios(self):
        """Las que la solución pública añade y las que BR-CL explica fuera de
        ella: restadas en dos módulos, y tienen que salir iguales."""
        de_la_orden = listas_de_codigos._de_la_orden("UNCL_5305")
        assert de_la_orden == solucion_publica._L4_QUE_LA_NORMA_NO_TIENE == {"N", "D", "F"}
        assert listas_de_codigos._de_la_orden("ISO_4217") == frozenset()

    def test_las_claves_de_regimen_se_buscan_en_la_lista_de_su_impuesto(self):
        assert solucion_publica._REGIMENES == {"IVA": "L3A", "IGIC": "L3B", "IPSI": "L3C"}

    def test_el_nif_y_las_retenciones_salen_de_la_columna_de_la_ruta(self):
        assert (solucion_publica._IMPUESTO, solucion_publica._IMPUESTO_LOCAL,
                solucion_publica._ESQUEMA_DEL_NIF) == ("VAT", "LOC", "FC")
        assert (solucion_publica._CATEGORIA_DE_LA_RETENCION,
                solucion_publica._ESQUEMA_DE_LA_RETENCION) == ("S", "WTH")

    def test_lo_que_no_se_comprueba_esta_dicho_con_su_porque(self):
        assert len(solucion_publica.NO_SE_COMPRUEBA) >= 5
        cortos = [k for k, v in solucion_publica.NO_SE_COMPRUEBA.items() if len(v) < 80]
        assert cortos == []


# --- El FC en el registro legal, como lo pone el ejemplo de la AEAT -----------------


_REGISTRO_SIN_ESQUEMA = "<cbc:CompanyID>B12345674</cbc:CompanyID></cac:PartyLegalEntity>"
_REGISTRO_CON_FC = '<cbc:CompanyID schemeID="FC">B12345674</cbc:CompanyID></cac:PartyLegalEntity>'


class TestElFcEnElRegistroLegal:
    """El ejemplo UBL de la AEAT pone schemeID="FC" en cac:PartyLegalEntity/cbc:CompanyID.

    La orden pone el «FC» en el NIF del identificador fiscal (BT-32, en
    cac:PartyTaxScheme) y al registro legal (BT-30) no le da ni ruta ni
    esquema. La norma, BR-CL-11, pide que ese esquema, si va, sea de ISO 6523,
    y FC no lo es. El ERROR se queda, como BR-G-02: el anexo es un mínimo y
    nada deroga la regla. Lo que faltaba era decir de dónde sale el FC y cómo
    se arregla: hasta el 18-10-2026 la queja era la genérica, «no es de ISO
    6523», y a quien había copiado el ejemplo oficial no le decía nada. Lo vio
    el auditor el 18-10-2026, con el ejemplo del 14-10 y con el del 15-10.
    El 21-10-2026 la AEAT contestó que lo quita, para no ir contra la norma, y
    su ejemplo nuevo va sin él; no dijo si la solución pública lo rechaza.
    """

    def test_el_fc_en_el_registro_sigue_en_error(self):
        con_fc = cambia(DEL_BOE, _REGISTRO_SIN_ESQUEMA, _REGISTRO_CON_FC)
        queja = next(i for i in factura.validar(con_fc.encode("utf-8")).errores
                     if i.codigo == "BR-CL-11")
        assert queja.gravedad == ERROR
        assert queja.encontrado == "FC"

    def test_dice_de_donde_sale_el_fc_y_como_se_arregla(self):
        con_fc = cambia(DEL_BOE, _REGISTRO_SIN_ESQUEMA, _REGISTRO_CON_FC)
        queja = next(i for i in factura.validar(con_fc.encode("utf-8")).errores
                     if i.codigo == "BR-CL-11")
        assert "BT-32" in queja.mensaje and "cac:PartyTaxScheme" in queja.mensaje
        assert "ejemplo" in queja.mensaje and "AEAT" in queja.mensaje
        assert "schemeID" in queja.mensaje
        # Dice lo que contestó la AEAT y no promete lo que no dijo: ni que la
        # solución pública lo rechace ni que lo acepte.
        assert "21-10-2026" in queja.mensaje and "no ir contra la norma" in queja.mensaje
        assert "no dijo si la solución pública lo rechaza" in queja.mensaje

    def test_sin_el_atributo_no_sale(self):
        """La norma admite el registro legal sin esquema, que es como lo dejan
        las facturas de la orden de estas pruebas."""
        assert "BR-CL-11" not in {i.codigo for i in factura.validar(DEL_BOE.encode("utf-8")).errores}

    def test_otro_codigo_que_no_es_de_la_lista_no_lleva_la_frase(self):
        con_otro = cambia(DEL_BOE, _REGISTRO_SIN_ESQUEMA,
                          '<cbc:CompanyID schemeID="NIF">B12345674</cbc:CompanyID></cac:PartyLegalEntity>')
        queja = next(i for i in factura.validar(con_otro.encode("utf-8")).errores
                     if i.codigo == "BR-CL-11")
        assert "BT-32" not in queja.mensaje

    def test_el_glosario_lo_dice_tambien(self):
        assert "FC" in glosario.CODIGOS["BR-CL-11"]
        assert "BT-32" in glosario.CODIGOS["BR-CL-11"]


# --- La factura en UBL 2.1 ------------------------------------------------------
#
# El documento de validaciones de la SPFE (versión 0.1.0, 16-10-2026, apartado
# 4.1) toma UBL 2.5 como referencia y admite versiones anteriores si el
# documento cumple el contenido mínimo del anexo I. Hasta el 29-10-2026 el
# README decía que la solución pública solo admitía la 2.5. Medido ese día: una
# factura de la orden que declara 2.1 y no usa nada de la 2.5 pasaba limpia,
# como debe; la que usa `CollectionInvoiceLine` salía con un XSD-ORDEN que
# decía que estaba «cambiada de sitio» con la `InvoiceLine`.

_EN_LA_21 = cambia(DEL_BOE, "<cbc:UBLVersionID>2.5<", "<cbc:UBLVersionID>2.1<")


def _sin_la_retencion(xml: str) -> str:
    """Sin retención ni su línea de cobro, que es lo único de la 2.5 que lleva."""
    xml = re.sub(r"  <cac:WithholdingTaxTotal>.*?</cac:WithholdingTaxTotal>\n", "", xml, flags=re.S)
    xml = re.sub(r"  <cac:CollectionInvoiceLine>.*?</cac:CollectionInvoiceLine>\n", "", xml, flags=re.S)
    return cambia(xml, '<cbc:PayableAmount currencyID="EUR">86.00<',
                  '<cbc:PayableAmount currencyID="EUR">101.00<')


class TestEnUbl21:

    def test_sin_nada_de_la_2_5_pasa_limpia(self, catalogo):
        assert "CollectionInvoiceLine" not in _sin_la_retencion(_EN_LA_21)
        assert limpia(_sin_la_retencion(_EN_LA_21), catalogo) == []

    def test_con_una_linea_de_cobro_dice_que_es_la_version(self, catalogo):
        informe = factura.validar(_EN_LA_21.encode("utf-8"), catalogo=catalogo)
        assert [(i.codigo, i.campo) for i in informe.errores + informe.avisos] == [
            ("XSD-VERSION", "UBLVersionID")]
        queja = informe.avisos[0]
        assert '"CollectionInvoiceLine"' in queja.mensaje
        assert "UBL 2.1" in queja.mensaje and "UBL 2.5 pasa" in queja.mensaje
        assert "cambiad" not in queja.mensaje
        assert (queja.esperado, queja.encontrado) == ("2.5 o posterior", "2.1")

    def test_de_la_spfe_es_aviso_porque_la_aeat_mide_con_la_2_5(self, catalogo):
        """Su documento de validaciones dice que comprueba la forma con los
        esquemas de la 2.5, y contra la 2.5 pasa: un ERROR prometería un
        rechazo que nadie ha dicho."""
        queja = next(i for i in factura.validar(_EN_LA_21.encode("utf-8"), catalogo=catalogo).incidencias
                     if i.codigo == "XSD-VERSION")
        assert queja.gravedad == AVISO
        assert "no ha dicho" in queja.mensaje

    def test_de_otro_es_error(self, catalogo):
        otro = cambia(_EN_LA_21, ESPECIFICACION, "urn:cen.eu:en16931:2017")
        queja = next(i for i in factura.validar(otro.encode("utf-8"), catalogo=catalogo).incidencias
                     if i.codigo == "XSD-VERSION")
        assert queja.gravedad == ERROR

    def test_sin_el_esquema_de_la_2_5_no_se_inventa_nada(self, esquemas_del_paquete, tmp_path):
        """Solo con la 2.1 no hay a quién preguntar: se queda lo de la 2.1."""
        import shutil
        shutil.copytree(esquemas_del_paquete / "ubl", tmp_path / "ubl")
        informe = factura.validar(_EN_LA_21.encode("utf-8"), catalogo=Catalogo(tmp_path))
        codigos = {i.codigo for i in informe.errores + informe.avisos}
        assert "XSD-VERSION" not in codigos and "XSD-ORDEN" in codigos

    def test_lo_que_falla_tambien_en_la_2_5_sigue_saliendo_como_antes(self, catalogo):
        """Si la 2.5 tampoco lo admite, la versión no es el problema."""
        roto = cambia(_EN_LA_21, "  <cac:InvoiceLine>", "  <cbc:Inventado>1</cbc:Inventado>\n  <cac:InvoiceLine>")
        codigos = {i.codigo for i in factura.validar(roto.encode("utf-8"), catalogo=catalogo).errores}
        assert "XSD-VERSION" not in codigos and "XSD-ORDEN" in codigos
