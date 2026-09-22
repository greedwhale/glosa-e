"""Comprobaciones de la detección de formato."""

import re

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
        d = formato.detectar(
            b"UNB+UNOC:3+EMISOR+RECEPTOR+260819:1200+1'"
            b"UNH+1+INVOIC:D:96A:UN'BGM+380+F-1'"
        )
        assert d.familia == EDIFACT
        assert d.version == "96A"
        assert d.tipo_documento == "factura"

    def test_un_abono_no_es_una_factura(self):
        d = formato.detectar(
            b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+INVOIC:D:96A:UN'BGM+381+A-1'"
        )
        assert d.tipo_documento == "abono"

    def test_sin_bgm_no_se_inventa_el_tipo(self):
        """Antes decía «factura» siempre, y eso no se sabe sin leer el BGM."""
        d = formato.detectar(b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+INVOIC:D:96A:UN'")
        assert d.familia == EDIFACT
        assert d.tipo_documento is None

    def test_edifact_que_no_es_factura(self):
        d = formato.detectar(b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+ORDERS:D:96A:UN'")
        assert d.familia == EDIFACT
        assert d.tipo_documento is None
        assert "ORDERS" in d.motivo and "no es una factura" in d.motivo


class TestUnUnaConSeparadoresPropios:
    """El UNA existe para declarar separadores distintos de los de siempre.

    La deteccion los llevaba escritos a pelo —`+`, `:`, `'`— asi que con un
    UNA propio no casaba nada y contestaba «Mensaje EDIFACT, pero sin cabecera
    UNH: no se ve de que tipo es». Es falso: el partidor de `edifact.py` la
    encuentra, porque el si lee el UNA. Medido el 22-09-2026 sobre la factura
    de W.S. Hein del corpus, que declara `UNA^<.? >`: version None, tipo None.
    Es el unico de los 64 ficheros ajenos que trae separadores propios, y por
    eso esto aguanto tanto sin verse.
    """

    # La misma factura escrita dos veces. `^` componente, `*` elemento, `~`
    # terminador; y los de por defecto.
    PROPIOS = (
        b"UNA^*,! ~"
        b"UNB*UNOC^3*EMISOR*RECEPTOR*260819^1200*1~"
        b"UNH*1*INVOIC^D^96A^UN~"
        b"BGM*380*F-1~"
    )
    DE_SIEMPRE = (
        b"UNB+UNOC:3+EMISOR+RECEPTOR+260819:1200+1'"
        b"UNH+1+INVOIC:D:96A:UN'"
        b"BGM+380+F-1'"
    )

    def test_se_reconoce_igual(self):
        d = formato.detectar(self.PROPIOS)
        assert d.familia == EDIFACT
        assert d.version == "96A"
        assert d.tipo_documento == "factura"
        assert "sin cabecera UNH" not in d.motivo

    def test_y_dice_lo_mismo_que_con_los_de_siempre(self):
        """Dos ficheros que dicen lo mismo no pueden describirse distinto."""
        propios = formato.detectar(self.PROPIOS)
        siempre = formato.detectar(self.DE_SIEMPRE)
        assert (propios.familia, propios.version, propios.tipo_documento,
                propios.motivo) == (
            siempre.familia, siempre.version, siempre.tipo_documento,
            siempre.motivo)

    def test_un_abono_con_separadores_propios(self):
        """El BGM tambien se buscaba con el `+` de siempre."""
        d = formato.detectar(self.PROPIOS.replace(b"BGM*380", b"BGM*381"))
        assert d.tipo_documento == "abono"

    def test_y_lo_que_no_es_factura_se_dice_como_tal(self):
        """Antes salia «sin cabecera UNH» en vez de «no es una factura»."""
        d = formato.detectar(self.PROPIOS.replace(b"INVOIC", b"ORDERS"))
        assert "ORDERS" in d.motivo and "no es una factura" in d.motivo

    def test_un_una_de_cinco_caracteres_tambien(self):
        """Los 23 de los 64 que se saltan el hueco reservado.

        Ahi el terminador es el quinto y no el sexto, y `cuantos_de_servicio`
        lo resuelve mirando si detras queda un UNB.
        """
        d = formato.detectar(
            b"UNA^*,!~UNB*UNOC^3*A*B*260819^1200*1~UNH*1*INVOIC^D^96A^UN~"
            b"BGM*380*F-1~"
        )
        assert d.version == "96A"
        assert d.tipo_documento == "factura"


class TestUnXmlQueNoAbre:
    """Lo que se dice cuando el fichero ni siquiera es XML.

    libxml2 lo explica bien y lo explica en inglés, y eso se iba tal cual al
    informe: «Premature end of data in tag FileHeader», «xmlParseEntityRef: no
    name». Medido el 22-09-2026 sobre los 172 ficheros ajenos de los tres
    corpus: cero veces. Sólo sale con un fichero roto, que es justo cuando
    quien lo recibe menos sabe qué mirar.
    """

    # Palabras que no puede haber en un informe de este validador. Se buscan
    # así, y no comparando el texto entero, porque lo que hay que impedir es
    # que **algo** de libxml2 se cuele, no que la frase sea la de hoy.
    INGLES = re.compile(
        r"\b(expected|found|mismatch|premature|invalid|redefined|Namespace|"
        r"prefix|Unsupported|encoding|Malformed|Input|terminated|finished|"
        r"Extra|content|Attribute|Entity|defined|Couldn|Start|Char|line|"
        r"column)\b")

    ROTOS = {
        "se corta a medias": b'<?xml version="1.0"?>\n<Facturae>\n  <FileHeader>\n',
        "cierre que no casa": b'<?xml version="1.0"?>\n<a>1</b>',
        "un & suelto": b'<?xml version="1.0"?>\n<a>A & B</a>',
        "dos raices": b'<?xml version="1.0"?><a/><b/>',
        "atributo repetido": b'<?xml version="1.0"?>\n<a v="1" v="2"/>',
        "atributo sin comillas": b'<?xml version="1.0"?>\n<a v=1/>',
        "entidad que no existe": b'<?xml version="1.0"?>\n<a>&pepe;</a>',
        "prefijo sin declarar": b'<?xml version="1.0"?><pp:a/>',
        "comentario sin cerrar": b'<?xml version="1.0"?><a><!-- hola </a>',
        "CDATA sin cerrar": b'<?xml version="1.0"?><a><![CDATA[hola</a>',
        "codificacion inventada": b"<?xml version='1.0' encoding='PEPE-9'?><a/>",
        "prologo mal escrito": b"<?xml versio='1.0'?><a/>",
        "caracter de control": b"<?xml version='1.0'?><a>\x01</a>",
        "un PDF": b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n",
    }

    def test_ninguna_deja_pasar_una_palabra_de_libxml2(self):
        cuela = {}
        for que, datos in self.ROTOS.items():
            motivo = formato.detectar(datos).motivo or ""
            if palabras := self.INGLES.findall(motivo):
                cuela[que] = sorted(set(palabras))
        assert not cuela, f"se cuela inglés en el informe: {cuela}"

    def test_y_todas_dicen_que_no_es_ni_xml_ni_edifact(self):
        for que, datos in self.ROTOS.items():
            motivo = formato.detectar(datos).motivo or ""
            assert "No es XML válido y tampoco EDIFACT" in motivo, que

    def test_se_dice_donde_mirar(self):
        motivo = formato.detectar(b'<?xml version="1.0"?>\n<a>1</b>').motivo
        # La columna de libxml2 empieza en 1 y `offset` en 0. Sin sumar uno, el
        # informe mandaba un carácter antes de donde está la cosa.
        assert "Línea 2, columna 9." in motivo, motivo

    def test_se_nombra_la_etiqueta_cuando_libxml2_la_nombra(self):
        motivo = formato.detectar(
            b'<?xml version="1.0"?>\n<Facturae>\n  <FileHeader>\n').motivo
        assert "«FileHeader»" in motivo, motivo

    def test_y_el_nombre_viene_sin_la_puntuacion_de_libxml2(self):
        """«Unsupported encoding PEPE-9, line 1» -> «PEPE-9», no «PEPE-9,»."""
        motivo = formato.detectar(
            b"<?xml version='1.0' encoding='PEPE-9'?><a/>").motivo
        assert "«PEPE-9»" in motivo, motivo

    def test_un_codigo_que_no_esta_en_la_tabla_dice_de_quien_son_las_palabras(self):
        """No se inventa una traducción de lo que no se ha medido.

        Lo que no cae en la tabla se pasa tal cual, pero **diciendo que son
        palabras del analizador**, que es distinto de colarlas como si fueran
        las de este validador.
        """
        class Falso:
            code = -12345          # ningún libxml2 lo usa
            msg = "Something nobody translated"
            lineno = 7
            offset = 3

        dicho = formato.por_que_no_abre(Falso())
        assert "el analizador de XML lo describe así" in dicho
        assert "«Something nobody translated»" in dicho
        assert "Línea 7, columna 4." in dicho

    def test_la_tabla_se_traduce_a_los_numeros_de_esta_version(self):
        """Los quince nombres tienen que existir en el lxml que haya montado.

        Se pregunta por el atributo público de `ErrorTypes` y no por `_names`,
        que es privado: aquí corre lxml 6.1.2 y en el navegador 6.0.2.
        """
        perdidos = [n for n in formato._NO_ABRE
                    if getattr(etree.ErrorTypes, n, None) is None]
        assert not perdidos, f"esta versión de libxml2 no conoce: {perdidos}"
        assert len(formato._POR_CODIGO) == len(formato._NO_ABRE)


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

    def test_la_linea_no_dice_que_cumpla_la_norma(self):
        """Decía «· conforme EN 16931» y esto es solo la detección.

        Lo único mirado aquí es el identificador de perfil que trae escrito el
        documento, y lo escribe quien la emite. La misma línea salía en una
        factura con dos errores de EN 16931, al lado del recuento: «UBL v2.1
        (factura) · conforme EN 16931 — 2 error(es)».
        """
        linea = formato.detectar(UBL_FACTURA.encode("utf-8")).resumen()
        assert "dice seguir EN 16931" in linea
        assert "conforme" not in linea

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

    def test_y_esa_entidad_sin_resolver_se_puede_nombrar(self, tmp_path):
        """La otra mitad de la de arriba, que estaba sin cerrar.

        No resolver la entidad es lo correcto y deja el campo vacio, asi que
        el documento se lee distinto de lo que dice. `entidades_sin_resolver`
        existe para que eso se pueda contar en el informe en vez de callarse;
        quien lo cuenta es `XML-ENTIDADES`.
        """
        ataque = b"""<?xml version="1.0"?>
<!DOCTYPE Invoice [<!ENTITY monto "100.00">]>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:ID>&monto;</cbc:ID>
</Invoice>"""
        raiz = etree.fromstring(ataque, parser=formato._parser())
        assert formato.entidades_sin_resolver(raiz) == ["ID"]

    def test_una_factura_normal_no_tiene_ninguna(self):
        """Si dijera que si de todo, el error saldria en facturas correctas."""
        raiz = etree.fromstring(
            b"""<?xml version="1.0"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>F-2026-001</cbc:ID>
</Invoice>""",
            parser=formato._parser(),
        )
        assert formato.entidades_sin_resolver(raiz) == []

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


# --- La edición de 2026 y el CIUS español ----------------------------------

CIUS_ES = "urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0"


def ubl_cius(version=None):
    linea = f"  <cbc:UBLVersionID>{version}</cbc:UBLVersionID>\n" if version else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
{linea}  <cbc:CustomizationID>{CIUS_ES}</cbc:CustomizationID>
  <cbc:ID>F-2026-003</cbc:ID>
</Invoice>"""


class TestLaEdicionDe2026:
    """La EN 16931 tiene dos ediciones vivas, y las dos son conformidad.

    La de 2017 es la que declara todo lo que circula hoy; la de 2026 es la que
    pide la solución pública española. Con una sola en la lista, una factura
    del CIUS salía «no declara conformidad con EN 16931» **por declarar la
    edición correcta**, y BR-01 avisaba de lo que estaba bien.
    """

    def test_las_dos_ediciones_cuentan_como_conformes(self):
        assert formato.detectar(UBL_FACTURA).conforme_en16931
        assert formato.detectar(ubl_cius("2.5")).conforme_en16931

    def test_el_marcador_de_2017_sigue_siendo_el_que_se_enseña(self):
        """`MARCADOR_EN16931` a secas se usa como ejemplo en los mensajes."""
        assert formato.MARCADOR_EN16931 == "urn:cen.eu:en16931:2017"
        assert formato.MARCADOR_EN16931 in formato.MARCADORES_EN16931

    def test_un_edifact_de_2026_tambien_cuenta(self):
        """En EDIFACT el perfil viaja en un FTX y se busca en los bytes."""
        crudo = (
            "UNA:+.? '"
            "UNH+1+INVOIC:D:96A:UN'"
            "BGM+380+F-2026-004'"
            "FTX+DOC+++urn:cen.eu:en16931:2026'"
        )
        assert formato.detectar(crudo.encode("latin-1")).conforme_en16931

    def test_el_marcador_del_cius_es_el_que_dice_el_anexo(self):
        """El guardián entre los dos sitios donde está escrito el mismo URN.

        `formato.py` lleva el trozo que identifica al CIUS y `cius_es.py` el
        valor entero, que sale del anexo. Si el anexo lo cambia, la tabla se
        regenera y esto salta; sin la prueba, `formato.py` se quedaría
        buscando un CIUS que ya no se llama así y no lo reconocería nunca.
        """
        from validador import cius_es

        assert formato.MARCADOR_CIUS_ES in cius_es.ESPECIFICACION
        assert cius_es.ESPECIFICACION.startswith(formato.MARCADORES_EN16931)


class TestQueVersionDeUblSeSupone:
    def test_lo_que_declara_el_documento_manda_siempre(self):
        assert formato.detectar(ubl_cius("2.5")).version == "2.5"
        # Aunque no cuadre con el CIUS: lo que dice el documento es un hecho,
        # y suponer por encima de un dato es inventar.
        assert formato.detectar(ubl_cius("2.1")).version == "2.1"

    def test_sin_version_pero_con_el_cius_se_supone_2_5(self):
        """Y no 2.1, que sería mandar a medirla con un esquema que la rechaza.

        Media docena de campos del CIUS cuelgan de `CollectionInvoiceLine`,
        que en UBL 2.1 no existe: suponer 2.1 no era redondear, era acusar de
        inventarse elementos a una factura correcta.
        """
        d = formato.detectar(ubl_cius())
        assert d.version == "2.5"
        assert "CIUS" in d.motivo

    def test_sin_version_y_sin_cius_se_sigue_suponiendo_2_1(self):
        d = formato.detectar(UBL_SIN_PERFIL)
        assert d.version == "2.1"
        assert "se asume UBL 2.1" in d.motivo
