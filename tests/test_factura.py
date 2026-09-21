"""Comprobaciones del orquestador y de la línea de órdenes."""

from datetime import date
from pathlib import Path

import pytest

from validador import __main__ as consola
from validador import factura
from validador.incidencias import AVISO, ERROR, Incidencia

HOY = date(2026, 9, 20)
NIF_BUENO = "ESB12345674"
NIF_MALO = "ESB12345670"  # mismo número, dígito de control cambiado

UBL = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:CustomizationID>urn:cen.eu:en16931:2017</cbc:CustomizationID>
  <cbc:ID>{numero}</cbc:ID>
  <cbc:IssueDate>{fecha}</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:DocumentCurrencyCode>EUR</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PostalAddress>{direccion_vendedor}</cac:PostalAddress>
    <!-- Con su esquema: sin él, el número no es el identificador de IVA
         (BT-31) y el vendedor queda sin identificar para BR-CO-26. -->
    <cac:PartyTaxScheme><cbc:CompanyID>{nif}</cbc:CompanyID>
      <cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Vendedor SL</cbc:RegistrationName>
    </cac:PartyLegalEntity>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PostalAddress><cac:Country>
      <cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyLegalEntity><cbc:RegistrationName>Cliente SA</cbc:RegistrationName>
    </cac:PartyLegalEntity>
  </cac:Party></cac:AccountingCustomerParty>
  <!-- El desglose por tipo no es adorno: BR-CO-18 lo exige, y sin él esta
       factura de prueba era una que ningún receptor aceptaría. -->
  <cac:TaxTotal>
    <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
    <cac:TaxSubtotal>
      <cbc:TaxableAmount currencyID="EUR">100.00</cbc:TaxableAmount>
      <cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount>
      <cac:TaxCategory><cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent></cac:TaxCategory>
    </cac:TaxSubtotal>
  </cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">{declarado}</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">121.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine><cbc:ID>1</cbc:ID>
    <cbc:InvoicedQuantity unitCode="EA">1</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="EUR">{linea}</cbc:LineExtensionAmount>
    <cac:Item><cbc:Name>Concepto</cbc:Name><cac:ClassifiedTaxCategory>
      <cbc:ID>S</cbc:ID><cbc:Percent>21</cbc:Percent>
    </cac:ClassifiedTaxCategory></cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="EUR">100.00</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>
</Invoice>"""


PAIS = ("<cac:Country><cbc:IdentificationCode>{}</cbc:IdentificationCode>"
        "</cac:Country>")


def ubl(numero="F-2026-0001", fecha="2026-03-02", nif=NIF_BUENO,
        linea="100.00", declarado="100.00", pais="ES"):
    """Una factura UBL de prueba.

    `pais` es el del **vendedor**, y a None se queda sin direccion de pais:
    hace falta para probar a quien le aplica el reglamento espaniol.
    """
    return UBL.format(
        numero=numero, fecha=fecha, nif=nif, linea=linea, declarado=declarado,
        direccion_vendedor="" if pais is None else PAIS.format(pais),
    )


FACTURAE = """<?xml version="1.0" encoding="UTF-8"?>
<fe:Facturae xmlns:fe="http://www.facturae.es/Facturae/2009/v3.2/Facturae">
  <FileHeader><SchemaVersion>3.2</SchemaVersion></FileHeader>
  <Parties><SellerParty><TaxIdentification>
    <TaxIdentificationNumber>{nif}</TaxIdentificationNumber>
  </TaxIdentification></SellerParty></Parties>
  <Invoices>
    <Invoice>
      <InvoiceHeader><InvoiceNumber>{primera}</InvoiceNumber></InvoiceHeader>
      <InvoiceIssueData><IssueDate>2026-03-02</IssueDate></InvoiceIssueData>
    </Invoice>
    <Invoice>
      <InvoiceHeader><InvoiceNumber>{segunda}</InvoiceNumber></InvoiceHeader>
      <InvoiceIssueData><IssueDate>2026-03-02</IssueDate></InvoiceIssueData>
    </Invoice>
  </Invoices>
</fe:Facturae>"""


def facturae(primera="F-001", segunda="F-002", nif=NIF_BUENO):
    return FACTURAE.format(primera=primera, segunda=segunda, nif=nif)


def al_25(**opciones):
    """La misma factura pero al 25%, que es el tipo general danes.

    El constructor de arriba va al 21%, que es vigente en Espania y por tanto
    no dispara IVA-TIPO: con el no se puede probar nada sobre ese aviso. Se
    cambian tambien las cuotas para que la factura siga cuadrando y el unico
    motivo de queja sea el tipo.
    """
    return (ubl(**opciones)
            .replace("<cbc:Percent>21</cbc:Percent>", "<cbc:Percent>25</cbc:Percent>")
            .replace(">21.00<", ">25.00<")
            .replace(">121.00<", ">125.00<"))


def codigos(informe, gravedad=None):
    fuente = informe.incidencias if hasattr(informe, "incidencias") else informe
    return {i.codigo for i in fuente if gravedad is None or i.gravedad == gravedad}


# --- Un documento ----------------------------------------------------------


class TestValidar:
    def test_documento_correcto(self):
        informe = factura.validar(ubl(), hoy=HOY)
        assert informe.conforme, informe.detalle()

    def test_corre_las_dos_normas_a_la_vez(self):
        """Lo que justifica que exista este módulo: una queja de cada bando."""
        informe = factura.validar(ubl(nif=NIF_MALO, linea="90.00"), hoy=HOY)
        assert "BR-CO-10" in codigos(informe, ERROR)  # europea
        assert "CU-01" in codigos(informe, ERROR)  # española

    def test_las_incidencias_saben_de_donde_vienen(self):
        informe = factura.validar(ubl(nif=NIF_MALO, linea="90.00"), hoy=HOY)
        origenes = {factura.origen(i) for i in informe.errores}
        assert origenes == {factura.EUROPEA, factura.ESPANOLA}

    def test_el_informe_dice_de_donde_sale_cada_queja(self):
        informe = factura.validar(ubl(nif=NIF_MALO, linea="90.00"), hoy=HOY)
        texto = informe.detalle(factura.origen)
        assert f"[BR-CO-10 · {factura.EUROPEA}]" in texto
        assert f"[CU-01 · {factura.ESPANOLA}]" in texto

    def test_un_abono_correcto_no_da_quejas(self):
        """Un abono es el documento con el que se corrige una factura.

        En UBL cambian el elemento raíz, el código de tipo y el nombre de las
        líneas. Con el mapa de la factura salían BR-04 y BR-16 inventados y,
        de paso, enmudecían todas las reglas que leen las líneas.
        """
        informe = factura.validar_archivo("ejemplos/r-0001.xml", hoy=HOY)
        assert informe.deteccion.tipo_documento == "abono"
        assert informe.conforme, informe.detalle(factura.origen)
        assert not informe.avisos, informe.detalle(factura.origen)

    def test_no_dice_dos_veces_que_falta_el_numero(self):
        """BR-02 y CU-00 son la misma queja de dos reglamentos distintos."""
        sin_numero = ubl().replace("<cbc:ID>F-2026-0001</cbc:ID>", "", 1)
        informe = factura.validar(sin_numero, hoy=HOY)
        assert "BR-02" in codigos(informe, ERROR)
        assert "CU-00" not in codigos(informe)
        assert "CU-02" not in codigos(informe)

    def test_en_facturae_tambien_lo_tapa_la_europea(self):
        """Antes CU-00 salía solo en Facturae, y ya no.

        Este test decía lo contrario —«en Facturae no hay reglas BR, así que
        CU-00 no lo tapa nadie»— y era verdad hasta el 06-09-2026, cuando
        Facturae entró en `SINTAXIS` con su propio mapa de EN 16931. Desde
        entonces la falta de fecha la denuncia BR-03 como en las otras tres
        sintaxis, y CU-00 sobra por lo mismo que sobraba allí.

        Que el hueco se cerrara es la mejora: la deduplicación entre el
        reglamento europeo y el español ya no depende de en qué sintaxis venga
        la factura, que es lo que hacía falta para que el informe se lea igual
        vengan como vengan.
        """
        sin_fecha = facturae().replace("<IssueDate>2026-03-02</IssueDate>", "")
        informe = factura.validar(sin_fecha, hoy=HOY)
        assert "BR-03" in codigos(informe, ERROR)
        assert "CU-00" not in codigos(informe)

    def test_facturae_se_valida_con_las_reglas_espanolas(self):
        """El código único se le mide a Facturae como a cualquier otro.

        Y ya no aparece el SIN-SOPORTE que decía que el documento no se había
        validado: la aritmética de Facturae la comprueba `facturae.py` contra
        las fórmulas del propio esquema del formato.
        """
        informe = factura.validar(facturae(nif=NIF_MALO), hoy=HOY)
        assert "CU-01" in codigos(informe, ERROR)
        assert "SIN-SOPORTE" not in codigos(informe)

    def test_dos_facturas_iguales_en_el_mismo_fichero(self):
        informe = factura.validar(facturae(primera="F-001", segunda="F-001"), hoy=HOY)
        assert "CU-10" in codigos(informe, ERROR)

    def test_edifact_no_revienta(self):
        datos = b"UNB+UNOC:3+EMISOR+RECEPTOR+260819:1200+1'UNH+1+INVOIC:D:96A:UN'"
        informe = factura.validar(datos, hoy=HOY)
        assert "SIN-SOPORTE" not in codigos(informe, AVISO)
        # El código único no se reprocha: EDIFACT no tiene dónde escribirlo,
        # así que no es que falte, es que no se ha mirado.
        assert "CU-00" not in codigos(informe)

    def test_documento_ajeno(self):
        informe = factura.validar(b"<pedido/>", hoy=HOY)
        assert not informe.deteccion
        assert informe.incidencias == []
        assert "No se ha podido validar" in informe.resumen()


class TestValidarArchivo:
    def test_lee_del_disco(self, tmp_path):
        ruta = tmp_path / "f.xml"
        ruta.write_text(ubl(), encoding="utf-8")
        assert factura.validar_archivo(ruta, hoy=HOY).conforme

    def test_fichero_que_no_existe(self, tmp_path):
        informe = factura.validar_archivo(tmp_path / "no-esta.xml", hoy=HOY)
        assert not informe.deteccion
        assert "No existe" in informe.deteccion.motivo


# --- Un lote de ficheros ---------------------------------------------------


def escribir(carpeta: Path, nombre: str, contenido: str) -> Path:
    ruta = carpeta / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


class TestCadaFicheroPorSuNombre:
    """Dos ficheros que se llaman igual siguen siendo dos.

    El lote identificaba cada fichero por `camino.name`. Con `a/factura.xml` y
    `b/factura.xml` duplicados y un `c/factura.xml` distinto, el duplicado
    marcaba a los tres y la queja decía «las dos vienen en factura.xml».
    """

    def _tres(self, tmp_path):
        rutas = []
        for carpeta, numero in (("a", "F-2026-0001"), ("b", "F-2026-0001"),
                                ("c", "F-2026-0002")):
            (tmp_path / carpeta).mkdir()
            rutas.append(escribir(tmp_path / carpeta, "factura.xml",
                                  ubl(numero=numero, fecha="2026-03-02")))
        return factura.validar_lote(rutas, hoy=HOY)

    def test_el_duplicado_no_arrastra_al_tercero(self, tmp_path):
        lote = self._tres(tmp_path)
        assert lote.senialados == {"a/factura.xml", "b/factura.xml"}
        assert "1 correcto(s)" in lote.resumen()

    def test_y_la_queja_dice_cuales_son(self, tmp_path):
        lote = self._tres(tmp_path)
        queja = next(i for i in lote.cruzadas if i.codigo == "CU-10")
        assert "a/factura.xml" in queja.mensaje and "b/factura.xml" in queja.mensaje

    def test_los_nombres_se_quedan_cortos_si_no_se_repiten(self, tmp_path):
        a = escribir(tmp_path, "a.xml", ubl())
        (tmp_path / "otra").mkdir()
        b = escribir(tmp_path / "otra", "b.xml", ubl(numero="F-2026-0002"))
        assert factura.validar_lote([a, b], hoy=HOY).nombres == ["a.xml", "b.xml"]

    def test_con_nombres_dados_manda_el_dado(self, tmp_path):
        # Es el caso del navegador: la ruta es la del disco virtual, y el
        # nombre, el que tenía en el ordenador de quien lo soltó.
        (tmp_path / "0").mkdir()
        (tmp_path / "1").mkdir()
        a = escribir(tmp_path / "0", "factura__.xml", ubl(numero="F-2026-0001"))
        b = escribir(tmp_path / "1", "factura__.xml", ubl(numero="F-2026-0002"))
        lote = factura.validar_lote([a, b], hoy=HOY,
                                    nombres=["factura ñ.xml", "factura ç.xml"])
        assert lote.nombres == ["factura ñ.xml", "factura ç.xml"]
        assert lote.cruzadas == [] and lote.conforme, lote.detalle()

    def test_lo_que_sigue_repetido_se_numera(self, tmp_path):
        a = escribir(tmp_path, "a.xml", ubl())
        assert factura.nombres_unicos([a, a]) == ["a.xml", "a.xml (2)"]
        assert factura.nombres_unicos([a, a], ["x", "x"]) == ["x", "x (2)"]

    def test_y_se_niega_si_no_hay_un_nombre_por_fichero(self, tmp_path):
        a = escribir(tmp_path, "a.xml", ubl())
        with pytest.raises(ValueError):
            factura.validar_lote([a], hoy=HOY, nombres=["a.xml", "b.xml"])

    def test_el_informe_de_la_pagina_usa_los_nombres_de_quien_los_solto(
        self, tmp_path, monkeypatch
    ):
        """El Python que corre la página, tal cual está escrito en `glosa.js`.

        Con lo que le deja `validar()`: cada fichero en su carpeta, con el
        nombre limpio, y al lado los nombres de verdad. Sin los nombres, la
        página enseñaba «factura__.xml» dos veces y no se sabía cuál era cuál.
        """
        import json
        import re

        from validador.cadena import Almacen
        from validador.esquema import Catalogo

        codigo = (Path(__file__).resolve().parent.parent / "web" / "glosa.js").read_text(
            encoding="utf-8")
        informe = re.search(r"const INFORME = `(.*?)`;", codigo, re.S).group(1)
        rutas = []
        for orden, numero in enumerate(("F-2026-0001", "F-2026-0002")):
            (tmp_path / str(orden)).mkdir()
            rutas.append(str(escribir(tmp_path / str(orden), "factura__.xml",
                                      ubl(numero=numero))))
        # Lo que el navegador tiene y aquí no: el catálogo y las anclas por
        # defecto de la página. Vacíos, que para esto basta.
        monkeypatch.setattr(Almacen, "por_defecto",
                            classmethod(lambda cls, *a: Almacen(tmp_path / "nada")))
        monkeypatch.setattr(Catalogo, "por_defecto",
                            classmethod(lambda cls, *a: Catalogo(tmp_path / "nada")))
        espacio = {"_rutas": rutas, "_nombres": ["factura ñ.xml", "factura ç.xml"]}
        *cuerpo, ultima = informe.strip().rsplit("\n\njson.dumps", 1)
        exec(cuerpo[0], espacio)
        datos = json.loads(eval("json.dumps" + ultima, espacio))
        assert [d["nombre"] for d in datos["documentos"]] == ["factura ñ.xml",
                                                              "factura ç.xml"]
        assert datos["cruzadas"] == []


class TestValidarLote:
    def test_duplicado_entre_ficheros(self, tmp_path):
        """Ningún fichero por separado puede ver esto: es la razón de la clase."""
        a = escribir(tmp_path, "a.xml", ubl(numero="F-2026-0001"))
        b = escribir(tmp_path, "b.xml", ubl(numero="F-2026-0001"))
        lote = factura.validar_lote([a, b], hoy=HOY)

        assert "CU-10" in codigos(lote.cruzadas, ERROR)
        # Y cada informe individual está limpio, porque mirando un solo
        # fichero no hay nada que ver.
        for _, informe in lote.informes:
            assert "CU-10" not in codigos(informe)

    def test_el_mensaje_nombra_los_dos_ficheros(self, tmp_path):
        a = escribir(tmp_path, "a.xml", ubl(numero="F-2026-0001"))
        b = escribir(tmp_path, "b.xml", ubl(numero="F-2026-0001"))
        lote = factura.validar_lote([a, b], hoy=HOY)
        problema = next(i for i in lote.cruzadas if i.codigo == "CU-10")
        assert "a.xml" in problema.mensaje and "b.xml" in problema.mensaje

    def test_un_duplicado_dentro_de_un_fichero_no_se_cuenta_dos_veces(self, tmp_path):
        """El informe del fichero ya lo dice; el del lote no debe repetirlo.

        Este caso se escapaba comparando los textos de las incidencias: el
        mensaje del lote lleva de qué fichero venía la anterior y el del
        fichero no, así que nunca coincidían y la queja salía por duplicado.
        """
        uno = escribir(tmp_path, "uno.xml", facturae(primera="F-001", segunda="F-001"))
        lote = factura.validar_lote([uno], hoy=HOY)

        (_, informe), = lote.informes
        assert "CU-10" in codigos(informe, ERROR)
        assert "CU-10" not in codigos(lote.cruzadas)

    def test_hueco_en_una_serie_repartida_entre_ficheros(self, tmp_path):
        rutas = [
            escribir(tmp_path, "a.xml", ubl(numero="F-2026-0001")),
            escribir(tmp_path, "b.xml", ubl(numero="F-2026-0004")),
        ]
        lote = factura.validar_lote(rutas, hoy=HOY)
        assert "CU-13" in codigos(lote.cruzadas, AVISO)

    def test_serie_completa_no_se_queja(self, tmp_path):
        rutas = [
            escribir(tmp_path, "a.xml", ubl(numero="F-2026-0001")),
            escribir(tmp_path, "b.xml", ubl(numero="F-2026-0002", fecha="2026-03-03")),
        ]
        lote = factura.validar_lote(rutas, hoy=HOY)
        assert lote.conforme, lote.detalle()
        assert lote.cruzadas == []

    def test_un_fichero_ilegible_no_tumba_el_lote(self, tmp_path):
        bueno = escribir(tmp_path, "bueno.xml", ubl())
        lote = factura.validar_lote([tmp_path / "fantasma.xml", bueno], hoy=HOY)
        assert len(lote.informes) == 2
        assert lote.informes[1][1].conforme

    def test_resumen_cuenta_bien(self, tmp_path):
        rutas = [
            escribir(tmp_path, "a.xml", ubl(numero="F-2026-0001")),
            escribir(tmp_path, "b.xml", ubl(numero="F-2026-0002",
                                            fecha="2026-03-03", linea="90.00")),
        ]
        resumen = factura.validar_lote(rutas, hoy=HOY).resumen()
        assert "2 fichero(s)" in resumen
        assert "1 correcto(s)" in resumen
        assert "1 con errores" in resumen

    def test_detalle_se_puede_leer(self, tmp_path):
        a = escribir(tmp_path, "a.xml", ubl(numero="F-2026-0001"))
        b = escribir(tmp_path, "b.xml", ubl(numero="F-2026-0001"))
        detalle = factura.validar_lote([a, b], hoy=HOY).detalle()
        assert "Entre ficheros:" in detalle
        # El informe dice el código y, al lado, de qué reglamento sale. Un
        # «CU-10» a secas no le dice a nadie si esto se lo rechaza el receptor
        # o si es una opinión nuestra.
        assert f"[CU-10 · {factura.ESPANOLA}]" in detalle

    def test_lote_limpio_es_conforme(self, tmp_path):
        ruta = escribir(tmp_path, "a.xml", ubl())
        lote = factura.validar_lote([ruta], hoy=HOY)
        assert lote
        assert lote.errores == []


EDI = Path(__file__).resolve().parent.parent / "ejemplos" / "edi-0001.edi"


def edi_aleman() -> bytes:
    """El ejemplo EDIFACT mudado a Berlin y al 19%, que es el tipo aleman.

    Se cambian tambien los importes para que la factura siga cuadrando: si no,
    las quejas serian de aritmetica y no del tipo, que es lo que se mira aqui.
    """
    texto = EDI.read_text(encoding="utf-8")
    aleman = (texto
              .replace("Valladolid++47001+ES'RFF+VA:ESB47123456",
                       "Berlin++10115+DE'RFF+VA:DE123456789")
              .replace(":::21+S", ":::19+S")
              .replace("MOA+176:172.20", "MOA+176:155.80")
              .replace("MOA+388:992.20", "MOA+388:975.80")
              .replace("MOA+9:992.20", "MOA+9:975.80")
              .replace("MOA+124:172.20", "MOA+124:155.80"))
    assert aleman.count("19+S") == 4 and "DE123456789" in aleman, (
        "el ejemplo EDIFACT ha cambiado y este apanio ya no lo muda de pais")
    return aleman.encode("utf-8")


def edi_al_25() -> bytes:
    """El ejemplo espaniol con un tipo que no esta vigente en Espania."""
    texto = EDI.read_text(encoding="utf-8")
    al_25 = texto.replace(":::21+S", ":::25+S")
    assert al_25 != texto
    return al_25.encode("utf-8")


class TestOrigen:
    @pytest.mark.parametrize(
        "codigo,esperado",
        [
            ("BR-02", factura.EUROPEA),
            ("BR-CO-10", factura.EUROPEA),
            ("BR-S-08", factura.EUROPEA),
            ("CU-01", factura.ESPANOLA),
            ("XSD-ORDEN", factura.FORMA),
            # Las de IVA que no son de la norma caían en OTRA, que se lee
            # «Formato». Un aviso sobre el desglose de IVA no es un problema
            # de formato: es que opinamos nosotros, y eso cambia lo que hay
            # que hacer con la queja.
            ("IVA-TIPO-SIN-DESGLOSE", factura.CASA),
            ("IVA-SIN-TOTAL", factura.CASA),
            # `SIN-SOPORTE` salia con la etiqueta del cajon de por defecto,
            # que se leia «Formato»: ni lo exige una norma de formato ni sale
            # de ninguna otra. Es de la casa, y el cajon de por defecto ya no
            # miente sobre eso.
            ("SIN-SOPORTE", factura.CASA),
            ("PERFIL-SIN-EN16931", factura.CASA),
            ("VALIDADOR-SE-ATRAGANTA", factura.CASA),
            # Se quedaba fuera de la lista de la firma y caia en el mismo
            # cajon, mientras la pagina publicada lo daba por firma.
            ("ANCLAS-SIN-RENOVAR", factura.SELLO),
        ],
    )
    def test_por_el_prefijo(self, codigo, esperado):
        from validador.incidencias import Incidencia

        assert factura.origen(Incidencia(codigo, ERROR, "da igual")) == esperado


class TestAQuienLeAplicaElReglamentoEspanol:
    """El RD 238/2026 obliga a quien factura en Espania, y a nadie mas.

    Salio de la primera prueba contra facturas ajenas: CU-01 saltaba en 61 de
    62 documentos y ni uno era espaniol. Se le estaba aplicando el digito de
    control del NIF espaniol a identificadores holandeses y alemanes, que no
    siguen ese algoritmo y por tanto no lo pasan jamas. Una gestoria con un
    solo proveedor europeo habria visto un muro de errores inventados.
    """

    def test_a_la_holandesa_no_se_le_aplican(self):
        informe = factura.validar(ubl(nif="NL820098395B01", pais="NL"), hoy=HOY)
        assert not [c for c in codigos(informe) if c.startswith("CU-")], (
            informe.detalle())

    def test_a_la_espaniola_si(self):
        """La otra mitad: acotar no puede significar dejar de comprobar."""
        informe = factura.validar(ubl(nif=NIF_MALO), hoy=HOY)
        assert "CU-01" in codigos(informe, ERROR)

    def test_las_reglas_europeas_siguen_corriendo_sobre_la_extranjera(self):
        """Acotar las espaniolas no exime de EN 16931."""
        informe = factura.validar(
            ubl(nif="NL820098395B01", pais="NL", numero=""), hoy=HOY)
        assert "BR-02" in codigos(informe, ERROR)

    def test_sin_pais_manda_el_prefijo_del_identificador(self):
        """Un fichero real traia el pais comentado y el NIF con prefijo NL."""
        informe = factura.validar(ubl(nif="NL820098395B01", pais=None), hoy=HOY)
        assert "CU-01" not in codigos(informe)

    def test_sin_pais_y_sin_prefijo_se_da_por_espaniola(self):
        """No saber no puede ser excusa para no mirar.

        Callarse las reglas por un dato que falta seria dar por revisado lo que
        nadie ha comprobado, que es peor que una queja de mas.
        """
        informe = factura.validar(ubl(nif="B12345670", pais=None), hoy=HOY)
        assert "CU-01" in codigos(informe, ERROR)

    def test_facturae_siempre_es_espaniola(self):
        """Es el formato nacional: no hace falta preguntarle de donde es."""
        informe = factura.validar(facturae(nif=NIF_MALO), hoy=HOY)
        assert "CU-01" in codigos(informe, ERROR)

    def test_a_la_extranjera_no_se_le_miden_los_tipos_espanoles(self):
        """El aviso IVA-TIPO tambien es una regla espaniola, y se colaba.

        El filtro se cableo a la familia CU-* y se olvido esta. Lo encontro un
        auditor independiente: 64 quejas en 50 de las 73 facturas europeas de
        muestras/ -el 70% de todo lo que decia el programa- denunciando el 25%
        danes, el 19% aleman y el 27% hungaro como si fueran dedazos.
        """
        informe = factura.validar(al_25(pais="DK", nif="DK12345678"), hoy=HOY)
        assert "IVA-TIPO" not in codigos(informe), informe.detalle()

    def test_a_la_espaniola_si_se_le_miden(self):
        """Y la otra mitad: acotar no puede ser dejar de comprobar.

        El 25% no es tipo vigente en Espania, asi que sobre una factura
        espaniola el aviso tiene que seguir saliendo.
        """
        informe = factura.validar(al_25(), hoy=HOY)
        assert "IVA-TIPO" in codigos(informe, AVISO), informe.detalle()

    def test_a_la_edifact_extranjera_tampoco_se_le_miden(self):
        """El mismo fallo, por el cuarto formato.

        `pais_emisor` tenia una tabla de rutas con UBL y CII, y EDIFACT no
        estaba: contestaba None para todas y de EDIFACT no se sacan codigos
        unicos, asi que el repaso siguiente se quedaba sin nada que mirar y las
        daba por espaniolas. Una factura alemana al 19% recibia IVA-TIPO.
        """
        informe = factura.validar(edi_aleman(), hoy=HOY)
        assert "IVA-TIPO" not in codigos(informe), informe.detalle()

    def test_a_la_edifact_espaniola_si(self):
        """Y la otra mitad: el ejemplo espaniol, al 21%, con un tipo inventado."""
        informe = factura.validar(edi_al_25(), hoy=HOY)
        assert "IVA-TIPO" in codigos(informe, AVISO), informe.detalle()

    def test_el_pais_del_sobre_manda_aunque_el_iva_no_lleve_prefijo(self):
        """El caso que de verdad prueba que se lee el pais del NAD.

        Provocado: quitando esa lectura, la prueba de arriba seguia en verde,
        porque el numero de IVA de la factura alemana empieza por DE y la pista
        del prefijo la salvaba. Hay facturas alemanas cuyo numero de IVA viene
        sin el prefijo —lo dice el comentario de `pais_emisor`— y esas son las
        que se apoyan solo en el pais.
        """
        sin_prefijo = edi_aleman().replace(b"RFF+VA:DE123456789",
                                           b"RFF+VA:123456789")
        assert b"DE123456789" not in sin_prefijo
        informe = factura.validar(sin_prefijo, hoy=HOY)
        assert "IVA-TIPO" not in codigos(informe), informe.detalle()

    def test_sin_pais_en_el_sobre_manda_el_numero_de_iva(self):
        """Un EDIFACT sin NAD de pais: queda el RFF+VA, que trae el prefijo."""
        sin_pais = edi_aleman().replace(b"Berlin++10115+DE", b"Berlin++10115")
        assert b"+DE'" not in sin_pais
        informe = factura.validar(sin_pais, hoy=HOY)
        assert "IVA-TIPO" not in codigos(informe), informe.detalle()

    def test_dos_facturas_de_paises_distintos_no_son_un_duplicado(self, tmp_path):
        """Las reglas de conjunto tambien tenian que acotarse.

        Dos suites de prueba europeas compartian el numero de ejemplo, y el
        lote las denunciaba como la misma factura repetida. Numeraciones de
        paises distintos no tienen por que guardar relacion ninguna.
        """
        holandesa = ubl(nif="NL820098395B01", pais="NL")
        rutas = [
            escribir(tmp_path, "una.xml", holandesa),
            escribir(tmp_path, "otra.xml", holandesa),
        ]
        lote = factura.validar_lote(rutas, hoy=HOY)
        assert "CU-10" not in codigos(lote.cruzadas), lote.detalle()

    def test_pero_dos_espaniolas_repetidas_si(self, tmp_path):
        rutas = [
            escribir(tmp_path, "a.xml", ubl()),
            escribir(tmp_path, "b.xml", ubl()),
        ]
        lote = factura.validar_lote(rutas, hoy=HOY)
        assert "CU-10" in codigos(lote.cruzadas)


class TestUnDuplicadoNoDejaLimpio_A_Nadie:
    """Hallazgo 8 de la auditoria.

    Un duplicado no es de ninguno de los dos ficheros por separado: cada uno,
    mirado solo, esta perfecto. Los dos se imprimian «sin errores» y los dos se
    contaban entre los correctos, asi que el resumen podia decir «2 correctos,
    0 con errores» sobre un lote que si tiene un error -el error salia al
    final, huerfano, sin que nada en las lineas de arriba llevara hasta el-.
    """

    def test_ninguno_de_los_dos_cuenta_como_correcto(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl(numero="F-1"))
        escribir(tmp_path, "b.xml", ubl(numero="F-1"))
        lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY)
        assert "CU-10" in {i.codigo for i in lote.cruzadas}
        assert "2 correcto(s)" not in lote.resumen()
        assert "0 correcto(s)" in lote.resumen()

    def test_y_la_linea_de_cada_uno_lo_dice(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl(numero="F-1"))
        escribir(tmp_path, "b.xml", ubl(numero="F-1"))
        lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY)
        detalle = lote.detalle()
        # Quien revisa doscientos ficheros lee la linea de cada uno. Si esa
        # linea dice «sin errores» a secas, no vuelve a bajar a mirar.
        assert detalle.count("choca con otro fichero") == 2

    def test_la_incidencia_sabe_a_que_ficheros_apunta(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl(numero="F-1"))
        escribir(tmp_path, "b.xml", ubl(numero="F-1"))
        lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY)
        choque = next(i for i in lote.cruzadas if i.codigo == "CU-10")
        assert set(choque.ficheros) == {"a.xml", "b.xml"}

    def test_un_fichero_limpio_de_verdad_sigue_contando(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl(numero="F-1"))
        escribir(tmp_path, "b.xml", ubl(numero="F-2"))
        lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY)
        assert "2 correcto(s)" in lote.resumen()
        assert "choca con otro fichero" not in lote.detalle()


class TestElNifDelReceptor:
    """Hallazgo 9: no se validaba nunca."""

    @staticmethod
    def con_nif(documento):
        """La misma factura UBL, pero con NIF en el comprador."""
        return ubl().replace(
            "<cac:AccountingCustomerParty><cac:Party>",
            "<cac:AccountingCustomerParty><cac:Party>"
            f"<cac:PartyTaxScheme><cbc:CompanyID>{documento}</cbc:CompanyID>"
            "</cac:PartyTaxScheme>",
        )

    def test_un_nif_de_receptor_invalido_avisa(self):
        informe = factura.validar(self.con_nif("B12345670"), hoy=HOY)
        assert "NIF-RECEPTOR" in codigos(informe, AVISO)

    def test_uno_valido_no_dice_nada(self):
        informe = factura.validar(self.con_nif("B12345674"), hoy=HOY)
        assert "NIF-RECEPTOR" not in codigos(informe)

    def test_a_un_receptor_extranjero_no_se_le_mide_el_digito_espaniol(self):
        """El mismo error que costo 61 quejas falsas en 62 facturas ajenas.

        Un NL999999999B01 no pasa el algoritmo espaniol porque no es el suyo.
        """
        informe = factura.validar(self.con_nif("NL999999999B01"), hoy=HOY)
        assert "NIF-RECEPTOR" not in codigos(informe)

    def test_pero_uno_espaniol_escrito_como_iva_intracomunitario_si(self):
        """ESB12345670 es un NIF espaniol con prefijo, y esta mal."""
        informe = factura.validar(self.con_nif("ESB12345670"), hoy=HOY)
        assert "NIF-RECEPTOR" in codigos(informe, AVISO)

    def test_sin_nif_de_receptor_no_se_dice_nada(self):
        """Si hace falta o no depende del tipo de operacion, y sin una fuente
        que citar aqui no se sentencia."""
        assert "NIF-RECEPTOR" not in codigos(factura.validar(ubl(), hoy=HOY))

    def test_no_lo_firma_el_reglamento_espaniol(self):
        """El codigo unico solo usa el NIF del emisor.

        Asi que esta queja no puede salir etiquetada «RD 238/2026»: seria
        firmar con una norma algo que esa norma no dice. Es el mismo error que
        se cometio aqui con unos BR-IG-* inventados.
        """
        assert factura.origen(Incidencia("NIF-RECEPTOR", AVISO, "")) == factura.CASA


class TestLoQueSeHaMirado:
    """Hallazgo 7: «sin errores» promete mas de lo hecho.

    Es el mensaje mas peligroso del programa. No quiere decir «esta factura
    esta bien»: quiere decir «no ha fallado ninguna de las comprobaciones que
    existen», y quien lo lee no tiene por que saber cuales son.
    """

    def test_el_informe_dice_que_se_ha_mirado(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl())
        lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY)
        assert "EN 16931" in lote.detalle()
        assert "código único del RD 238/2026" in lote.detalle()

    def test_y_dice_lo_que_no(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl())
        lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY)
        assert "firmas" in lote.detalle()

    def test_no_promete_reglas_europeas_sobre_un_facturae(self, tmp_path):
        """A un Facturae no se le miden las BR-*, y decirlo seria mentir."""
        escribir(tmp_path, "a.xml", facturae())
        lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY)
        assert "EN 16931" not in lote.alcance()
        assert "Facturae" in lote.alcance()

    def test_ni_reglas_de_facturae_sobre_un_ubl(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl())
        lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY)
        assert "formato Facturae" not in lote.alcance()

    def test_no_promete_la_forma_si_no_hay_esquemas(self, tmp_path):
        """Decia «se ha comprobado la forma contra el esquema XSD» justo
        encima del recordatorio de que no hay esquemas puestos: dos lineas
        seguidas contradiciendose, que es peor que no decir nada.
        """
        escribir(tmp_path, "a.xml", ubl())
        lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY)
        assert "esquema XSD" in lote.alcance(forma=True)
        assert "esquema XSD" not in lote.alcance(forma=False)

    def test_el_codigo_unico_se_promete_donde_se_mira(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl())
        lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY)
        assert "código único" in lote.alcance().splitlines()[0]

    def test_no_en_edifact(self, tmp_path):
        """De un EDIFACT no se saca el código único.

        Dos copias idénticas salían «2 correctos», sin el duplicado, debajo de
        una frase que decía haber comprobado el código único.
        """
        ejemplo = Path(__file__).resolve().parent.parent / "ejemplos" / "edi-0001.edi"
        if not ejemplo.is_file():
            pytest.skip("no está el ejemplo EDIFACT")
        rutas = []
        for nombre in ("uno.edi", "dos.edi"):
            rutas.append(tmp_path / nombre)
            rutas[-1].write_bytes(ejemplo.read_bytes())
        alcance = factura.validar_lote(rutas, hoy=HOY).alcance()
        primera, segunda = alcance.splitlines()
        assert "código único" not in primera
        assert "el código único de las facturas EDIFACT" in segunda

    def test_ni_sobre_ficheros_que_no_se_han_podido_leer(self, tmp_path):
        lote = factura.validar_lote(
            [tmp_path / "no-existe.xml", tmp_path / "tampoco.xml"], hoy=HOY
        )
        alcance = lote.alcance()
        assert "código único" not in alcance
        assert alcance.startswith("No se ha comprobado nada")

    def test_la_consola_lo_dice_segun_tenga_esquemas(self, tmp_path, capsys):
        escribir(tmp_path, "a.xml", ubl())
        consola.main([str(tmp_path), "--hoy", "2026-09-20", "--esquemas", "no-existe"])
        salida = capsys.readouterr().out
        assert "No se ha comprobado la forma" in salida
        assert "se ha comprobado la forma contra el esquema XSD" not in salida


class TestSinComprobar:
    """Un fichero que no se ha podido mirar no es un fichero correcto.

    Era un fallo real y silencioso: `Informe.conforme` decía que sí —no hay
    errores porque no hay nada— así que un fichero inexistente salía en el
    resumen entre los buenos y `factura-e` devolvía 0. Quien se equivocaba al
    escribir la ruta se quedaba tan tranquilo creyendo que había revisado un
    lote que nadie llegó a abrir.
    """

    def test_el_que_no_existe_no_cuenta_como_correcto(self, tmp_path):
        bueno = escribir(tmp_path, "bueno.xml", ubl())
        lote = factura.validar_lote([bueno, tmp_path / "fantasma.xml"], hoy=HOY)
        assert "1 correcto(s)" in lote.resumen()
        assert "1 SIN COMPROBAR" in lote.resumen()

    def test_el_lote_no_es_conforme(self, tmp_path):
        bueno = escribir(tmp_path, "bueno.xml", ubl())
        lote = factura.validar_lote([bueno, tmp_path / "fantasma.xml"], hoy=HOY)
        assert not lote.conforme
        assert lote.errores == []  # no hay errores; hay algo peor: un hueco

    def test_la_consola_no_devuelve_cero(self, tmp_path, capsys):
        escribir(tmp_path, "bueno.xml", ubl())
        salida = consola.main(
            [str(tmp_path / "bueno.xml"), str(tmp_path / "fantasma.xml"),
             "--hoy", "2026-09-20"]
        )
        assert salida == 1, "un guion encadenado se creería que todo fue bien"
        assert "SIN COMPROBAR" in capsys.readouterr().out

    def test_un_formato_ajeno_tampoco_es_correcto(self, tmp_path):
        """No solo el que falta: el que está pero no se reconoce."""
        ruta = escribir(tmp_path, "pedido.xml", "<pedido><linea/></pedido>")
        lote = factura.validar_lote([ruta], hoy=HOY)
        assert "1 SIN COMPROBAR" in lote.resumen()
        assert not lote.conforme

    def test_solo_errores_no_esconde_el_hueco(self, tmp_path, capsys):
        """El aviso se puede callar; el fichero que falta, no.

        Con --solo-errores se silencian los avisos, y si el hueco viajara como
        aviso desaparecería justo para quien pide ver «solo lo importante».
        Va en el resumen, que no se filtra.
        """
        escribir(tmp_path, "bueno.xml", ubl())
        consola.main(
            [str(tmp_path / "bueno.xml"), str(tmp_path / "fantasma.xml"),
             "--hoy", "2026-09-20", "--solo-errores"]
        )
        assert "SIN COMPROBAR" in capsys.readouterr().out

    def test_un_lote_entero_bueno_sigue_saliendo_limpio(self, tmp_path):
        """La comprobación nueva no puede ensuciar el caso normal."""
        rutas = [
            escribir(tmp_path, "a.xml", ubl(numero="F-2026-0001")),
            escribir(tmp_path, "b.xml", ubl(numero="F-2026-0002",
                                            fecha="2026-03-03")),
        ]
        lote = factura.validar_lote(rutas, hoy=HOY)
        assert lote.conforme, lote.detalle()
        assert lote.sin_comprobar == []
        assert "SIN COMPROBAR" not in lote.resumen()

    def test_informe_suelto_sabe_si_lo_ha_mirado(self):
        assert factura.validar(ubl(), hoy=HOY).validado
        assert not factura.validar(b"<pedido/>", hoy=HOY).validado
        # Un EDIFACT sí se identifica, aunque no se validen sus reglas: la
        # queja SIN-SOPORTE lo dice, y eso es distinto de no poder abrirlo.
        edifact = b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+INVOIC:D:96A:UN'"
        assert factura.validar(edifact, hoy=HOY).validado


# --- Línea de órdenes ------------------------------------------------------


class TestConsola:
    def test_todo_bien_devuelve_cero(self, tmp_path, capsys):
        escribir(tmp_path, "a.xml", ubl())
        assert consola.main([str(tmp_path), "--hoy", "2026-09-20"]) == 0
        assert "sin errores" in capsys.readouterr().out

    def test_con_errores_devuelve_uno(self, tmp_path, capsys):
        escribir(tmp_path, "a.xml", ubl(linea="90.00"))
        assert consola.main([str(tmp_path), "--hoy", "2026-09-20"]) == 1

    def test_lo_malo_de_una_subcarpeta_tambien_cuenta(self, tmp_path, capsys):
        """La prueba de verdad del 29: lo que ve quien encadena guiones.

        Medido antes de arreglarlo: esta misma carpeta salia «1 fichero(s) · 1
        correcto(s) · 0 con errores» y **codigo 0**, con la factura mala
        escondida un nivel mas abajo.
        """
        escribir(tmp_path, "buena.xml", ubl())
        dentro = tmp_path / "marzo"
        dentro.mkdir()
        escribir(dentro, "mala.xml", ubl(linea="90.00"))
        assert consola.main([str(tmp_path), "--hoy", "2026-09-20"]) == 1
        salida = capsys.readouterr().out
        assert "mala.xml" in salida, (
            "no basta con el codigo de salida: si no se nombra, quien lo lee "
            "no sabe cual de las facturas hay que mirar"
        )
        assert "2 fichero(s)" in salida

    def test_sin_ficheros_devuelve_dos(self, tmp_path, capsys):
        assert consola.main([str(tmp_path)]) == 2
        assert "ningún fichero" in capsys.readouterr().err

    def test_solo_errores_calla_los_avisos(self, tmp_path, capsys):
        escribir(tmp_path, "a.xml", al_25())  # IVA-TIPO es un aviso
        consola.main([str(tmp_path), "--hoy", "2026-09-20", "--solo-errores"])
        assert "IVA-TIPO" not in capsys.readouterr().out

    def test_sin_solo_errores_los_avisos_salen(self, tmp_path, capsys):
        escribir(tmp_path, "a.xml", al_25())
        consola.main([str(tmp_path), "--hoy", "2026-09-20"])
        assert "IVA-TIPO" in capsys.readouterr().out

    def test_fecha_mal_escrita(self, tmp_path):
        with pytest.raises(SystemExit):
            consola.main([str(tmp_path), "--hoy", "20 de septiembre"])

    def test_una_carpeta_se_expande(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl())
        escribir(tmp_path, "notas.txt", "esto no es una factura")
        caminos = consola.expandir([str(tmp_path)])
        assert [c.name for c in caminos] == ["a.xml"]

    def test_y_se_expande_entera_subcarpetas_incluidas(self, tmp_path):
        """Hasta el 21-09-2026 solo se miraba el primer nivel.

        Es el peor fallo que puede tener un validador, porque no falla: dice
        que si. Una carpeta de facturas viene organizada por mes o por cliente
        casi siempre, y lo de dentro no se nombraba, no se contaba y no se
        avisaba.
        """
        escribir(tmp_path, "arriba.xml", ubl())
        dentro = tmp_path / "enero" / "un cliente"
        dentro.mkdir(parents=True)
        escribir(dentro, "abajo.xml", ubl())
        caminos = consola.expandir([str(tmp_path)])
        assert sorted(c.name for c in caminos) == ["abajo.xml", "arriba.xml"]

    def test_y_una_carpeta_dentro_de_otra_no_se_cuela(self, tmp_path):
        """Que la recursion no se trague las carpetas como si fueran ficheros.

        `rglob("*")` devuelve tambien los directorios, y uno llamado
        `cosas.xml` casaria con la extension.
        """
        escribir(tmp_path, "a.xml", ubl())
        (tmp_path / "esto.xml").mkdir()
        caminos = consola.expandir([str(tmp_path)])
        assert [c.name for c in caminos] == ["a.xml"]

    def test_una_carpeta_recoge_tambien_los_edifact(self, tmp_path):
        """Sin esto, apuntar a una carpeta los saltaba en silencio.

        Y el resumen contaba los que si habia mirado, que es como se deja a
        alguien creyendo que ha revisado un lote entero cuando le faltaba un
        cuarto.
        """
        escribir(tmp_path, "a.xml", ubl())
        (tmp_path / "b.edi").write_bytes(
            b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+INVOIC:D:96A:UN'"
            b"BGM+380+F-1'UNT+3+1'UNZ+1+1'"
        )
        caminos = consola.expandir([str(tmp_path)])
        assert [c.name for c in caminos] == ["a.xml", "b.edi"]

    def test_pero_un_txt_suelto_sigue_sin_ser_una_factura(self, tmp_path):
        """Una carpeta de facturas suele traer ademas un leeme.

        Recogerlo llenaria el informe de «formato no reconocido» sobre
        ficheros que nadie dijo que fueran facturas.
        """
        escribir(tmp_path, "a.xml", ubl())
        escribir(tmp_path, "leeme.txt", "esto no es una factura")
        assert [c.name for c in consola.expandir([str(tmp_path)])] == ["a.xml"]

    def test_y_aun_asi_se_puede_validar_nombrandolo(self, tmp_path):
        """Hay EDIFACT que viaja en `.txt`. Pedido por su nombre, se lee."""
        ruta = tmp_path / "factura.txt"
        ruta.write_bytes(
            b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+INVOIC:D:96A:UN'"
            b"BGM+380+F-1'UNT+3+1'UNZ+1+1'"
        )
        assert consola.expandir([str(ruta)]) == [ruta]
        informe = factura.validar_archivo(ruta)
        assert informe.deteccion.familia == "EDIFACT"

    def test_un_fichero_suelto(self, tmp_path):
        ruta = escribir(tmp_path, "a.xml", ubl())
        assert consola.expandir([str(ruta)]) == [ruta]

    def test_comodin(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl())
        escribir(tmp_path, "b.xml", ubl())
        caminos = consola.expandir([str(tmp_path / "*.xml")])
        assert [c.name for c in caminos] == ["a.xml", "b.xml"]

    def test_lo_que_no_existe_se_mantiene_para_poder_quejarse(self, tmp_path):
        """Si se descartara en silencio, el usuario no sabría que se equivocó."""
        fantasma = tmp_path / "no-esta.xml"
        assert consola.expandir([str(fantasma)]) == [fantasma]


class TestUnFicheroNoSeLlevaElLote:
    """Que el validador falle con un fichero no puede tapar a los demás.

    Salió con una factura de verdad: un apóstrofo sin soltar dentro del
    título de una revista hacía que el nombre del segmento no fuera un nombre
    válido de etiqueta XML, y `lxml` levantaba un `ValueError`. Aquello no
    salía por el informe: salía por la consola, como una traza de Python, y
    se llevaba por delante todos los ficheros del lote que vinieran detrás.

    Ese fallo concreto está arreglado, pero el que se lleve el lote por
    delante es lo que había que arreglar aparte: los ficheros son de otros y
    siempre habrá uno que traiga algo que aquí no se haya previsto.
    """

    def _carpeta(self, tmp_path):
        buena = tmp_path / "buena.edi"
        buena.write_bytes(
            b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+INVOIC:D:96A:UN'BGM+380+F1'"
            b"UNT+3+1'UNZ+1+1'"
        )
        mala = tmp_path / "mala.edi"
        mala.write_bytes(b"UNB+UNOC:3+A+B+260819:1200+2'UNH+2+INVOIC:D:96A:UN'")
        return mala, buena

    def test_las_demas_se_revisan_igual(self, tmp_path, monkeypatch):
        mala, buena = self._carpeta(tmp_path)
        de_verdad = factura._arbol

        def revienta(datos, deteccion):
            if b"+2'" in datos:
                raise RuntimeError("algo que no se habia previsto")
            return de_verdad(datos, deteccion)

        monkeypatch.setattr(factura, "_arbol", revienta)
        lote = factura.validar_lote([mala, buena])
        assert len(lote.informes) == 2
        codigos = {
            i.codigo for _, informe in lote.informes for i in informe.incidencias
        }
        assert "VALIDADOR-SE-ATRAGANTA" in codigos

    def test_se_cuenta_como_error_y_no_como_correcto(self, tmp_path, monkeypatch):
        """Si no, un lote daría por bueno un fichero que no ha mirado."""
        mala, _ = self._carpeta(tmp_path)
        monkeypatch.setattr(
            factura, "_arbol", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
        )
        informe = factura.validar_archivo(mala)
        assert [i.codigo for i in informe.incidencias] == ["VALIDADOR-SE-ATRAGANTA"]
        assert any(i.gravedad == ERROR for i in informe.incidencias)


class TestUnDoctypeConEntidades:
    """El punto 24 de la auditoria del 15-09-2026.

    Un Facturae con `<!ENTITY monto "1.00">` usado en un importe salia con
    **una sola** linea: «Este fichero ha hecho fallar al validador:
    XMLSchemaValidateError: Internal error in XML Schema validation». En
    ingles, dentro del informe, y con todas las demas comprobaciones calladas.

    libxml2 se niega a validar contra un XSD un arbol que trae referencias a
    entidad sin expandir, y aqui no se expanden a proposito —lo guarda
    `test_formato.TestSeguridad`—. Asi que ahora se dice lo que pasa, que es
    ademas lo que de verdad le importa a quien recibe la factura: ese campo se
    lee vacio, y el siguiente que abra el fichero puede leer otra cosa.
    """

    def _con_entidad(self):
        """La misma UBL de siempre, con el total escrito como entidad."""
        sana = ubl()
        assert sana.count("<cbc:PayableAmount currencyID=\"EUR\">121.00<") == 1
        return sana.replace(
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE Invoice [<!ENTITY total "121.00">]>',
        ).replace(
            '<cbc:PayableAmount currencyID="EUR">121.00<',
            '<cbc:PayableAmount currencyID="EUR">&total;<',
        )

    def test_se_dice_y_no_se_atraganta(self):
        informe = factura.validar(self._con_entidad())
        salen = codigos(informe)
        assert "XML-ENTIDADES" in salen
        assert "VALIDADOR-SE-ATRAGANTA" not in salen, (
            "el informe vuelve a ser una sola linea sobre el propio validador"
        )

    def test_y_el_resto_de_la_factura_se_sigue_mirando(self):
        """Lo que se perdia no era una queja: eran todas las demas."""
        informe = factura.validar(self._con_entidad())
        assert len(informe.incidencias) > 1, [i.codigo for i in informe.incidencias]

    def test_y_lo_dice_en_castellano(self):
        """El mensaje de libxml2 llegaba tal cual al informe, en ingles."""
        informe = factura.validar(self._con_entidad())
        queja = next(i for i in informe.incidencias if i.codigo == "XML-ENTIDADES")
        assert queja.gravedad == ERROR
        assert "PayableAmount" in queja.encontrado
        todo = " ".join(str(i.mensaje) + str(i.encontrado)
                        for i in informe.incidencias)
        assert "Internal error" not in todo

    def test_una_factura_sin_doctype_no_se_entera(self):
        assert "XML-ENTIDADES" not in codigos(factura.validar(ubl()))
