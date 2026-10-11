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
import pathlib
import re
from dataclasses import replace

import pytest
from lxml import etree

from validador import cius_es, factura, glosario, iva, listas_de_codigos, solucion_publica
from validador.formato import detectar
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia

from tests.test_rutas_cius import _andar, _esquema_de_ubl, con_esquema

ESPECIFICACION = cius_es.ESPECIFICACION
PROCESO = cius_es.PROCESO
L7 = cius_es.LISTAS["L7"].calificador
L8 = cius_es.LISTAS["L8"].calificador
L10 = cius_es.LISTAS["L10"].calificador

# Lo del borrador de abril, que ya no vale y se reconoce para decirlo.
DEL_BORRADOR = "urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0"
PROCESO_DEL_BORRADOR = "urn:aeat:names:specification:ubl:schema:B2B"
URN_DEL_BORRADOR = "urn:aeat:names:specification:ubl:schema:"
# El del ejemplo que la AEAT mandó por correo el 02-10-2026, sin «ubl:».
PROCESO_DEL_EJEMPLO = "urn:aeat:names:specification:schema:profile:B2B"

QR_URL = "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR?nif=B12345674"


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


def limpia(xml: str) -> list[tuple[str, str]]:
    """Los errores y los avisos de todo el validador, que tienen que ser ninguno."""
    informe = factura.validar(xml.encode("utf-8"))
    return [(i.codigo, i.campo) for i in informe.errores + informe.avisos]


# --- La factura de la orden ------------------------------------------------------
#
# Con las formas que el borrador de abril no admitía: el proceso de la orden,
# sin indicador de copia, el vendedor identificado en BT-32 con «LOC» y el
# atributo «FC», un anticipo pagado con su fecha, la retención con el
# calificador de la L7 de la orden y el QR con el de L10. Medido el 07-10-2026
# sobre `cc0a935`, con las reglas del borrador: seis ERROR (SPFE-PROCESO,
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
    <cbc:UUID>https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR?nif=B12345674</cbc:UUID>
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
      <cac:AdditionalItemProperty><cbc:Name>REGI</cbc:Name><cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>
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
        ("", "OTROS", "Otra tasa"),
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

# La L8 de la orden da el valor, «REGI», y aparte el calificador
# urn:aeat:names:specification:schema:lin:, sin decir cómo se juntan.
CON_LA_CLAVE_CON_CALIFICADOR = cambia(DEL_BOE, "<cbc:Name>REGI</cbc:Name>",
                                      "<cbc:Name>urn:aeat:names:specification:schema:lin:REGI</cbc:Name>")

# Una segunda línea y su desglose en la categoría N, la del recargo de
# equivalencia en la L4 de la orden, al 5,2%. Medido el 07-10-2026 antes de
# tocar nada: BR-CL-17 y BR-CL-18 en ERROR, e IVA-CATEGORIA-RARA e IVA-TIPO en
# AVISO, porque la lista de 2017 no tiene la N.
_LINEA_N = """  <cac:InvoiceLine>
    <cbc:ID>2</cbc:ID>
    <cbc:InvoicedQuantity unitCode="H87">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">0.00</cbc:LineExtensionAmount>
    <cac:Item>
      <cbc:Name>Recargo de equivalencia</cbc:Name>
      <cac:ClassifiedTaxCategory><cbc:ID>N</cbc:ID><cbc:Percent>5.2</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>
      <cac:AdditionalItemProperty><cbc:Name>REGI</cbc:Name><cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA</cbc:ValueQualifier></cac:AdditionalItemProperty>
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
_REGI_DEL_BOE = ("<cac:AdditionalItemProperty><cbc:Name>REGI</cbc:Name><cbc:Value>01</cbc:Value>"
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

LAS_DE_LA_ORDEN = {
    "la de la orden": DEL_BOE,
    "con el tercero": CON_EL_TERCERO_DEL_BOE,
    "con suplidos, minoraciones e impuestos": CON_LOS_COBROS_DEL_BOE,
    "el comprador en BT-47": CON_EL_COMPRADOR_EN_BT47,
    "el vendedor en BT-31": CON_EL_VENDEDOR_EN_BT31,
    "la retención sin calificador": CON_LA_RETENCION_SIN_CALIFICADOR,
    "el QR sin descripción": CON_EL_QR_SIN_DESCRIPCION,
    "con la categoría N": CON_LA_N,
    "la clave con calificador": CON_LA_CLAVE_CON_CALIFICADOR,
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
}


# --- Las buenas, en el validador entero -------------------------------------------


class TestLasBuenas:

    @pytest.mark.parametrize("xml", LAS_DE_LA_ORDEN.values(), ids=LAS_DE_LA_ORDEN.keys())
    def test_no_dan_ni_un_error_ni_un_aviso_en_todo_el_validador(self, xml):
        assert limpia(xml) == []

    def test_dice_en_notas_lo_que_ha_aceptado_y_con_que_base(self):
        informe = factura.validar(DEL_BOE.encode("utf-8"))
        assert {i.codigo for i in informe.notas} == {
            "SPFE-ALCANCE", "SPFE-COPIA", "SPFE-IMPORTE-PAGADO", "SPFE-TOTAL-A-PAGAR"}

    def test_la_nota_del_alcance_sale_siempre_y_dice_con_que_se_ha_medido(self):
        """Hasta el 07-10-2026 decía que el anexo «no está publicado en el BOE».

        Del 07-10-2026 al 11-10-2026 se llamaba SPFE-BORRADOR y decía la
        mezcla: la orden publicada, lo que de ella ya se admitía, y que el
        resto seguía midiendo el borrador de abril. Desde ese día se mide con
        la orden, y la nota dice lo que de ella todavía no se mide.
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
        frase = "; ".join(cosas[:-1]) + "; y " + cosas[-1]
        assert frase in la(DEL_BOE, "SPFE-ALCANCE").mensaje
        assert frase in glosario.CODIGOS["SPFE-ALCANCE"]

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

    def test_la_nota_no_se_limita_a_lo_que_enumera(self):
        """Decía «no quiere decir que la factura cumpla la orden en eso», y lo
        que no enumeraba tampoco estaba medido entero."""
        assert la(DEL_BOE, "SPFE-ALCANCE").mensaje.endswith(
            "no quiere decir que la factura cumpla la orden.")
        assert "en eso" not in glosario.CODIGOS["SPFE-ALCANCE"]

    def test_el_prefijo_del_nif_iva_del_comprador_no_se_mide_y_la_nota_lo_dice(self):
        """La fila BT-48 pide el prefijo de España, y un FR pasaba sin que la
        nota lo dijera. Lo vio el revisor de promesas el 11-10-2026. Si un día
        se mide, esta prueba se pone en rojo: hay que sacarlo de la lista."""
        otro = cambia(DEL_BOE, "<cbc:CompanyID>ESA12345674<", "<cbc:CompanyID>FRA12345674<")
        assert codigos(otro) == set()
        assert ("el prefijo ES del NIF-IVA del comprador (BT-48)"
                in la(otro, "SPFE-ALCANCE").mensaje)

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
        codigo = pathlib.Path(solucion_publica.__file__).read_text(encoding="utf-8")
        reglas = codigo[codigo.index("# --- Las reglas"):]
        for identificador in ("BT-ES-2", "BT-30", "BT-119", "BG-ES-2", "BG-ES-3",
                              "BT-ES-22", "BT-ES-26", "BT-121"):
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
        """El régimen simplificado, el recargo y la agricultura: fuera de la L3A."""
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

    def test_el_proceso_del_ejemplo_es_nota_y_pide_el_de_la_orden(self):
        """La AEAT lo escribió sin «ubl:» en su ejemplo del 02-10-2026, y se le
        preguntó al buzón el 07-10-2026 cuál vale. Mientras, ni condena ni
        absuelve."""
        del_ejemplo = cambia(DEL_BOE, PROCESO, PROCESO_DEL_EJEMPLO)
        nota = la(del_ejemplo, "SPFE-PROCESO")
        assert nota.gravedad == NOTA and nota.esperado == PROCESO
        assert "05-10-2026" in nota.mensaje and "no está publicad" not in nota.mensaje
        assert codigos(del_ejemplo) == set()

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

    @pytest.mark.parametrize("cuantos", [4, 5])
    def test_de_cuatro_a_cinco_importes_es_nota_porque_la_orden_dice_tres_y_cinco(self, cuantos):
        """La fila BT-3 dice «hasta tres grupos» y el grupo es `0..5`. Se
        acepta con el grupo, y se dice: pasaba en silencio."""
        xml = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "S"),
                                *[adjunto("RECT:IMPORTES", "Base", "100.00")] * cuantos)
        nota = la(xml, "SPFE-RECTIFICATIVA")
        assert nota.gravedad == NOTA and nota.encontrado == str(cuantos)
        assert "hasta tres grupos" in nota.mensaje and "0..5" in nota.mensaje

    def test_tres_importes_en_una_sustitucion_no_dicen_nada(self):
        xml = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "S"),
                                *[adjunto("RECT:IMPORTES", "Base", "100.00")] * 3)
        assert las(xml, "SPFE-RECTIFICATIVA") == []

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
# líneas. Va sin `UBLVersionID`, con el proceso sin «ubl:» y los calificadores
# de L10 delante. La URL del QR se deja la de la orden: la del ejemplo apunta a
# un dominio, `gob.aeat`, que no existe.
_SIN_VERSION = cambia(cambia(DEL_BOE, "  <cbc:UBLVersionID>2.5</cbc:UBLVersionID>\n", ""),
                      PROCESO, PROCESO_DEL_EJEMPLO)
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
            "SPFE-PROCESO", "SPFE-RECTIFICATIVA"}

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


class TestPartes:

    def test_el_nif_del_vendedor_con_otro_impuesto(self):
        otro = cambia(CON_EL_VENDEDOR_EN_BT31, "ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT<",
                      "ESB12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>IVA<")
        queja = la(otro, "SPFE-NIF")
        assert queja.campo == "NIF del vendedor (BT-31 o BT-32)"
        assert queja.encontrado == "ESB12345674 con el impuesto «IVA»"

    def test_sin_nif_del_comprador(self):
        sin = cambia(DEL_BOE, "<cac:PartyTaxScheme><cbc:CompanyID>ESA12345674</cbc:CompanyID>"
                              "<cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>", "")
        queja = la(sin, "SPFE-NIF")
        assert queja.campo == "NIF del comprador (BT-48 o BT-47)" and queja.encontrado == "(falta)"

    def test_el_nif_con_loc_tiene_que_llevar_fc(self):
        """La orden pide las dos cosas: el impuesto «LOC» y el atributo «FC»."""
        sin_fc = cambia(DEL_BOE, ' schemeID="FC">B12345674', ">B12345674")
        assert la(sin_fc, "SPFE-NIF").encontrado == "B12345674 con el impuesto «LOC»"
        otro = cambia(DEL_BOE, ' schemeID="FC">B12345674', ' schemeID="NIF">B12345674')
        assert la(otro, "SPFE-NIF").encontrado == "B12345674 con el impuesto «LOC» y schemeID «NIF»"

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
        assert "(hay «IGIC»)" in la(otro, "SPFE-TERCERO").mensaje

    def test_al_tercero_se_le_pide_el_nombre_y_el_fc(self):
        sin_nombre = cambia(CON_EL_TERCERO_DEL_BOE,
                            "<cbc:RegistrationName>Gestoria Ejemplo SL</cbc:RegistrationName>", "")
        assert "el nombre o razón social (BT-ES-3)" in la(sin_nombre, "SPFE-TERCERO").mensaje
        sin_fc = cambia(CON_EL_TERCERO_DEL_BOE, ' schemeID="FC">B87654321', ">B87654321")
        assert "«LOC» con el atributo «FC»" in la(sin_fc, "SPFE-TERCERO").mensaje

    def test_el_nombre_del_tercero_donde_lo_ponia_el_borrador_no_se_lee(self):
        """En `cac:PartyName`: hasta el 11-10-2026 se aceptaba también ahí."""
        en_abril = cambia(CON_EL_TERCERO_DEL_BOE,
                          "<cac:PartyLegalEntity><cbc:RegistrationName>Gestoria Ejemplo SL"
                          "</cbc:RegistrationName></cac:PartyLegalEntity>",
                          "<cac:PartyName><cbc:Name>Gestoria Ejemplo SL</cbc:Name></cac:PartyName>")
        assert "el nombre o razón social (BT-ES-3)" in la(en_abril, "SPFE-TERCERO").mensaje


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

    @pytest.mark.parametrize(("xml", "viejo", "lugar"), [
        (DEL_BOE, "<cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>"
                  "</cac:ClassifiedTaxCategory>", "líneas"),
        (DEL_BOE, "<cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>"
                  "</cac:TaxCategory>\n    </cac:TaxSubtotal>", "desglose del IVA"),
        (CON_DESCUENTOS, "<cbc:Percent>21</cbc:Percent><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme>"
                         "</cac:TaxCategory>\n  </cac:AllowanceCharge>", "descuentos y cargos del documento"),
    ], ids=["la línea", "el desglose", "el descuento"])
    def test_el_impuesto_no_es_vat(self, xml, viejo, lugar):
        """Lo dicen las filas BG-30, BG-23, BT-95 y BT-102, en su columna de la ruta."""
        otro = cambia(xml, viejo, viejo.replace(">VAT<", ">IGIC<"))
        queja = la(otro, "SPFE-TIPO-DE-IMPUESTO")
        assert queja.campo.endswith(lugar) and queja.encontrado == "IGIC"
        assert "BT-95, BT-102, BG-30 y BG-23" in queja.mensaje

    def test_la_k_no_esta_en_la_lista_l4(self):
        con_k = cambia(DEL_BOE, "<cac:ClassifiedTaxCategory><cbc:ID>S<", "<cac:ClassifiedTaxCategory><cbc:ID>K<")
        queja = la(con_k, "SPFE-CATEGORIA")
        assert queja.gravedad == ERROR and queja.encontrado == "K" and "intracomunitaria" in queja.mensaje
        assert queja.campo.endswith("línea 1")
        assert queja.esperado == "S, Z, E, AE, O, G, L, M, N, D o F"

    def test_una_categoria_que_ni_la_norma_admite_se_la_deja_a_br_cl(self):
        assert "SPFE-CATEGORIA" not in codigos(
            cambia(DEL_BOE, "<cac:ClassifiedTaxCategory><cbc:ID>S<", "<cac:ClassifiedTaxCategory><cbc:ID>X<"))


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
        parecido = cambia(DEL_BOE, "<cbc:Name>REGI</cbc:Name>", f"<cbc:Name>{nombre}</cbc:Name>")
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

    def test_la_referencia_catastral_a_secas_se_lee_igual(self):
        a_secas = cambia(CON_LA_REFERENCIA_CON_CALIFICADOR, f"{L8}RCAT<", "RCAT<")
        assert las(a_secas, "SPFE-REFERENCIA-CATASTRAL") == []
        assert la(cambia(a_secas, ">01</cbc:ValueQualifier></cac:AdditionalItemProperty>",
                         ">05</cbc:ValueQualifier></cac:AdditionalItemProperty>"),
                  "SPFE-REFERENCIA-CATASTRAL").encontrado == "05"


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
        assert "BT-ES-21" in queja.mensaje and "«99»" in queja.mensaje
        assert "el esquema «WTH» (BG-ES-4)" in queja.mensaje

    def test_la_retencion_sin_su_linea_de_cobro(self):
        sin = quita(DEL_BOE, "  <cac:CollectionInvoiceLine>", "</cac:CollectionInvoiceLine>\n")
        assert "BT-ES-16" in la(sin, "SPFE-RETENCION").mensaje

    def test_la_linea_de_retencion_sin_retenciones(self):
        sin = quita(DEL_BOE, "  <cac:WithholdingTaxTotal>", "</cac:WithholdingTaxTotal>\n")
        assert "la suma de retenciones (BT-ES-17)" in la(sin, "SPFE-RETENCION").mensaje

    def test_la_retencion_a_secas_se_mide_igual(self):
        malo = cambia(CON_LA_RETENCION_SIN_CALIFICADOR, "<cbc:TaxTypeCode>01<", "<cbc:TaxTypeCode>99<")
        assert "«99»" in la(malo, "SPFE-RETENCION").mensaje

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
        Medido ese día sobre `354b6bd`, con la N y con la D sin declararla.
        """
        sin = cambia(xml, ESPECIFICACION, "urn:cen.eu:en16931:2026")
        quejas = [i for i in factura.validar(sin.encode("utf-8")).errores
                  if i.codigo in ("BR-CL-17", "BR-CL-18")]
        assert {q.codigo for q in quejas} == {"BR-CL-17", "BR-CL-18"}
        for queja in quejas:
            assert f"La {categoria} es de la lista L4 de la Orden HAC/1028/2026" in queja.mensaje
            assert "BT-24" in queja.mensaje and ESPECIFICACION in queja.mensaje
            assert "no es de UNCL 5305" in queja.mensaje

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
        assert "Con cuatro o cinco sale una NOTA" in hoy
        assert [i.gravedad for i in self.rectificativa(cuatro)] == [NOTA]
        con_i = rectificativa_con(adjunto("RECT:TIPO", "R1"), adjunto("RECT:MODALIDAD", "I"),
                                  adjunto("RECT:IMPORTES", "Base", "1.00"))
        assert "con la modalidad I, un AVISO" in hoy
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
    ])
    def test_si_cambia_una_cuenta_o_un_limite_que_se_comprueba(self, monkeypatch, identificador,
                                                              viejo, nuevo):
        """Las dos cuentas de las retenciones y lo que se dice de los importes
        rectificados salen de la descripción de su fila desde el 11-10-2026."""
        negativa = _recargar_con(monkeypatch, _diciendo(identificador, viejo, nuevo))
        assert negativa and identificador in negativa

    def test_con_la_tabla_de_verdad_no_se_niega(self, monkeypatch):
        assert _recargar_con(monkeypatch, cius_es.CAMPOS) is None

    def test_si_una_ruta_deja_de_colgar_de_su_grupo(self):
        with pytest.raises(solucion_publica.AnexoCambiado, match="ya no cuelga"):
            solucion_publica._relativa("./cac:WithholdingTaxTotal/cbc:TaxAmount",
                                       "./cac:CollectionInvoiceLine")

    def test_y_despues_de_negarse_vuelve_a_ser_el_de_siempre(self):
        assert codigos(DEL_BOE) == set()


class TestDeDondeSale:

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
        ]
        for parte in ("StreetName", "CityName", "PostalZone", "CountrySubentity"):
            for quien in ("AccountingSupplierParty", "AccountingCustomerParty"):
                rutas.append(f"cac:{quien}/cac:Party/cac:PostalAddress/cbc:{parte}")
                rutas.append(f"cac:{quien}/cac:Party/cac:PostalAddress/cac:Country/cbc:IdentificationCode")
        fallos = {r: _andar(r, tipo_de, hijos_de) for r in rutas}
        assert {r: f for r, f in fallos.items() if f} == {}

    def test_las_lineas_de_cobro_son_las_de_l7_y_solo_la_retencion_va_una_vez(self):
        assert set(solucion_publica._L7) == set(cius_es.LISTAS["L7"].valores)
        assert solucion_publica._UNO_POR_FACTURA == {"RETE": "RETENCIONES"}

    def test_los_documentos_son_los_de_l10_y_cada_uno_con_su_lista(self):
        assert set(solucion_publica._DOCUMENTOS) == set(cius_es.LISTAS["L10"].valores)
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
