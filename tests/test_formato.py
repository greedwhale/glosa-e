"""Comprobaciones de la detección de formato."""

import pytest
from lxml import etree

from validador import formato
from validador.formato import CII, EDIFACT, FACTURAE, UBL


def facturae(namespace, schema_version=None, extra=""):
    version = (
        f"<SchemaVersion>{schema_version}</SchemaVersion>" if schema_version else ""
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<fe:Facturae xmlns:fe="{namespace}">
  <FileHeader>{version}<Modality>I</Modality></FileHeader>
  <Invoices><Invoice>{extra}</Invoice></Invoices>
</fe:Facturae>"""


UBL_FACTURA = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:CustomizationID>urn:cen.eu:en16931:2017#compliant#urn:fdc:peppol.eu:2017:poacc:billing:3.0</cbc:CustomizationID>
  <cbc:ID>F-2026-001</cbc:ID>
</Invoice>"""

UBL_ABONO = """<?xml version="1.0" encoding="UTF-8"?>
<CreditNote xmlns="urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:CustomizationID>urn:cen.eu:en16931:2017</cbc:CustomizationID>
</CreditNote>"""

UBL_SIN_PERFIL = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>F-2026-002</cbc:ID>
</Invoice>"""

CII_FACTURA = """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>urn:cen.eu:en16931:2017</ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>
  <rsm:ExchangedDocument><ram:TypeCode>380</ram:TypeCode></rsm:ExchangedDocument>
</rsm:CrossIndustryInvoice>"""


class TestFacturae:
    def test_version_por_namespace(self):
        d = formato.detectar(facturae("http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml"))
        assert d.familia == FACTURAE
        assert d.version == "3.2.2"

    def test_schema_version_manda_sobre_namespace(self):
        # Namespace de la 3.2 pero SchemaVersion dice 3.2.1: gana SchemaVersion
        # y el motivo debe avisar de la discrepancia.
        d = formato.detectar(
            facturae("http://www.facturae.es/Facturae/2009/v3.2/Facturae", "3.2.1")
        )
        assert d.version == "3.2.1"
        assert "namespace" in d.motivo.lower()

    def test_namespace_desconocido_no_impide_reconocerlo(self):
        d = formato.detectar(facturae("http://ejemplo.invalido/facturae/v9", "3.2.2"))
        assert d.familia == FACTURAE
        assert d.version == "3.2.2"
        assert "no catalogado" in d.motivo

    def test_sin_version_ninguna(self):
        d = formato.detectar(facturae("http://ejemplo.invalido/facturae/v9"))
        assert d.familia == FACTURAE
        assert d.version is None

    def test_rectificativa_es_abono(self):
        d = formato.detectar(
            facturae(
                "http://www.facturae.es/Facturae/2009/v3.2/Facturae",
                "3.2",
                "<InvoiceDocumentType>FR</InvoiceDocumentType>",
            )
        )
        assert d.tipo_documento == "factura"

        d2 = formato.detectar(
            facturae(
                "http://www.facturae.es/Facturae/2009/v3.2/Facturae",
                "3.2",
                "<InvoiceDocumentType>RECTIFICATIVA</InvoiceDocumentType>",
            )
        )
        assert d2.tipo_documento == "abono"

    def test_facturae_no_es_cius_de_en16931(self):
        d = formato.detectar(facturae("http://www.facturae.es/Facturae/2009/v3.2/Facturae", "3.2"))
        assert not d.conforme_en16931

    def test_firma_envuelta_dentro(self):
        xml = facturae(
            "http://www.facturae.es/Facturae/2009/v3.2/Facturae",
            "3.2",
            '<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"/>',
        )
        d = formato.detectar(xml)
        assert d.familia == FACTURAE
        assert d.firmado

    def test_firma_por_fuera(self):
        interior = facturae(
            "http://www.facturae.es/Facturae/2009/v3.2/Facturae", "3.2"
        ).split("?>", 1)[1]
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#">'
            f"<ds:Object>{interior}</ds:Object></ds:Signature>"
        )
        d = formato.detectar(xml)
        assert d.familia == FACTURAE
        assert d.version == "3.2"
        assert d.firmado


class TestUBL:
    def test_factura_conforme(self):
        d = formato.detectar(UBL_FACTURA)
        assert d.familia == UBL
        assert d.version == "2.1"
        assert d.tipo_documento == "factura"
        assert d.conforme_en16931

    def test_abono(self):
        d = formato.detectar(UBL_ABONO)
        assert d.familia == UBL
        assert d.tipo_documento == "abono"
        assert d.conforme_en16931

    def test_sin_perfil_no_es_conforme(self):
        d = formato.detectar(UBL_SIN_PERFIL)
        assert d.familia == UBL
        assert not d.conforme_en16931
        assert "UBLVersionID" in d.motivo


class TestCII:
    def test_factura(self):
        d = formato.detectar(CII_FACTURA)
        assert d.familia == CII
        assert d.version == "D16B"
        assert d.tipo_documento == "factura"
        assert d.conforme_en16931

    def test_codigo_381_es_abono(self):
        d = formato.detectar(CII_FACTURA.replace("380", "381"))
        assert d.tipo_documento == "abono"


class TestEdifact:
    def test_invoic(self):
        d = formato.detectar(b"UNB+UNOC:3+EMISOR+RECEPTOR+260819:1200+1'UNH+1+INVOIC:D:96A:UN'")
        assert d.familia == EDIFACT
        assert d.tipo_documento == "factura"
        assert "no está implementada" in d.motivo

    def test_edifact_que_no_es_factura(self):
        d = formato.detectar(b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+ORDERS:D:96A:UN'")
        assert d.familia == EDIFACT
        assert d.tipo_documento is None
        assert "no parece un INVOIC" in d.motivo


class TestCasosLimite:
    def test_vacio(self):
        d = formato.detectar(b"")
        assert not d
        assert "vacío" in d.motivo

    def test_xml_roto(self):
        d = formato.detectar(b"<Invoice><sin cerrar>")
        assert not d
        assert "No es XML válido" in d.motivo

    def test_xml_valido_pero_ajeno(self):
        d = formato.detectar(b"<pedido><linea/></pedido>")
        assert not d
        assert "pedido" in d.motivo

    def test_resumen_legible(self):
        assert "Facturae v3.2.2" in formato.detectar(
            facturae("http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml")
        ).resumen()
        assert "no reconocido" in formato.detectar(b"<x/>").resumen()

    def test_archivo_inexistente(self):
        d = formato.detectar_archivo("no/existe/factura.xml")
        assert not d
        assert "No existe" in d.motivo

    def test_archivo_real(self, tmp_path):
        ruta = tmp_path / "f.xml"
        ruta.write_text(UBL_FACTURA, encoding="utf-8")
        assert formato.detectar_archivo(ruta).familia == UBL


class TestSeguridad:
    def test_no_resuelve_entidades_externas(self, tmp_path):
        """Un XML subido por un tercero no debe poder leer ficheros locales."""
        secreto = tmp_path / "secreto.txt"
        secreto.write_text("CONTRASEÑA", encoding="utf-8")
        ataque = f"""<?xml version="1.0"?>
<!DOCTYPE Invoice [<!ENTITY xxe SYSTEM "file:///{secreto.as_posix()}">]>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:ID>&xxe;</cbc:ID>
</Invoice>""".encode()
        d = formato.detectar(ataque)

        # El documento debe parsearse bien: si fallara el parseo, la comprobación
        # de fuga de abajo pasaría en vacío y no estaría midiendo nada.
        assert d.familia == UBL, "el ataque debe parsearse, no fallar"

        # Y la entidad externa no debe haberse resuelto.
        assert "CONTRASEÑA" not in repr(d)

        raiz = etree.fromstring(ataque, parser=formato._parser())
        identificador = raiz.xpath("//*[local-name()='ID']")[0]
        assert identificador.text is None, "la entidad externa se ha resuelto"

    def test_bomba_de_entidades_no_explota(self):
        bomba = b"""<?xml version="1.0"?>
<!DOCTYPE lolz [
 <!ENTITY lol "lol">
 <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
 <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
 <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
]>
<lolz>&lol3;</lolz>"""
        d = formato.detectar(bomba)  # no debe colgarse ni agotar memoria
        assert not d
