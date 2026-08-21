"""Comprobaciones del orquestador y de la línea de órdenes."""

from datetime import date
from pathlib import Path

import pytest

from validador import __main__ as consola
from validador import factura
from validador.incidencias import AVISO, ERROR

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
    <cac:PostalAddress><cac:Country>
      <cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyTaxScheme><cbc:CompanyID>{nif}</cbc:CompanyID></cac:PartyTaxScheme>
    <cac:PartyLegalEntity><cbc:RegistrationName>Vendedor SL</cbc:RegistrationName>
    </cac:PartyLegalEntity>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PostalAddress><cac:Country>
      <cbc:IdentificationCode>ES</cbc:IdentificationCode></cac:Country></cac:PostalAddress>
    <cac:PartyLegalEntity><cbc:RegistrationName>Cliente SA</cbc:RegistrationName>
    </cac:PartyLegalEntity>
  </cac:Party></cac:AccountingCustomerParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID="EUR">21.00</cbc:TaxAmount></cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="EUR">{declarado}</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="EUR">100.00</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="EUR">121.00</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="EUR">121.00</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
  <cac:InvoiceLine><cbc:ID>1</cbc:ID>
    <cbc:LineExtensionAmount currencyID="EUR">{linea}</cbc:LineExtensionAmount>
  </cac:InvoiceLine>
</Invoice>"""


def ubl(numero="F-2026-0001", fecha="2026-03-02", nif=NIF_BUENO,
        linea="100.00", declarado="100.00"):
    return UBL.format(
        numero=numero, fecha=fecha, nif=nif, linea=linea, declarado=declarado
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

    def test_no_dice_dos_veces_que_falta_el_numero(self):
        """BR-02 y CU-00 son la misma queja de dos reglamentos distintos."""
        sin_numero = ubl().replace("<cbc:ID>F-2026-0001</cbc:ID>", "", 1)
        informe = factura.validar(sin_numero, hoy=HOY)
        assert "BR-02" in codigos(informe, ERROR)
        assert "CU-00" not in codigos(informe)
        assert "CU-02" not in codigos(informe)

    def test_pero_cu_00_sale_si_la_europea_no_lo_ha_dicho(self):
        """En Facturae no hay reglas BR, así que CU-00 no lo tapa nadie."""
        sin_fecha = facturae().replace("<IssueDate>2026-03-02</IssueDate>", "")
        informe = factura.validar(sin_fecha, hoy=HOY)
        assert "CU-00" in codigos(informe, ERROR)

    def test_facturae_se_valida_con_las_reglas_espanolas(self):
        """Aunque EN 16931 no esté portado a Facturae, el código único sí."""
        informe = factura.validar(facturae(nif=NIF_MALO), hoy=HOY)
        assert "SIN-SOPORTE" in codigos(informe, AVISO)
        assert "CU-01" in codigos(informe, ERROR)

    def test_dos_facturas_iguales_en_el_mismo_fichero(self):
        informe = factura.validar(facturae(primera="F-001", segunda="F-001"), hoy=HOY)
        assert "CU-10" in codigos(informe, ERROR)

    def test_edifact_no_revienta(self):
        datos = b"UNB+UNOC:3+EMISOR+RECEPTOR+260819:1200+1'UNH+1+INVOIC:D:96A:UN'"
        informe = factura.validar(datos, hoy=HOY)
        assert "SIN-SOPORTE" in codigos(informe, AVISO)
        # No se ha podido leer nada, así que tampoco se reprocha nada.
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
        assert "[CU-10]" in detalle

    def test_lote_limpio_es_conforme(self, tmp_path):
        ruta = escribir(tmp_path, "a.xml", ubl())
        lote = factura.validar_lote([ruta], hoy=HOY)
        assert lote
        assert lote.errores == []


class TestOrigen:
    @pytest.mark.parametrize(
        "codigo,esperado",
        [
            ("BR-02", factura.EUROPEA),
            ("BR-CO-10", factura.EUROPEA),
            ("CU-01", factura.ESPANOLA),
            ("SIN-SOPORTE", factura.OTRA),
        ],
    )
    def test_por_el_prefijo(self, codigo, esperado):
        from validador.incidencias import Incidencia

        assert factura.origen(Incidencia(codigo, ERROR, "da igual")) == esperado


# --- Línea de órdenes ------------------------------------------------------


class TestConsola:
    def test_todo_bien_devuelve_cero(self, tmp_path, capsys):
        escribir(tmp_path, "a.xml", ubl())
        assert consola.main([str(tmp_path), "--hoy", "2026-09-20"]) == 0
        assert "sin errores" in capsys.readouterr().out

    def test_con_errores_devuelve_uno(self, tmp_path, capsys):
        escribir(tmp_path, "a.xml", ubl(linea="90.00"))
        assert consola.main([str(tmp_path), "--hoy", "2026-09-20"]) == 1

    def test_sin_ficheros_devuelve_dos(self, tmp_path, capsys):
        assert consola.main([str(tmp_path)]) == 2
        assert "ningún fichero" in capsys.readouterr().err

    def test_solo_errores_calla_los_avisos(self, tmp_path, capsys):
        escribir(tmp_path, "a.xml", facturae())  # SIN-SOPORTE es un aviso
        consola.main([str(tmp_path), "--hoy", "2026-09-20", "--solo-errores"])
        assert "SIN-SOPORTE" not in capsys.readouterr().out

    def test_sin_solo_errores_los_avisos_salen(self, tmp_path, capsys):
        escribir(tmp_path, "a.xml", facturae())
        consola.main([str(tmp_path), "--hoy", "2026-09-20"])
        assert "SIN-SOPORTE" in capsys.readouterr().out

    def test_fecha_mal_escrita(self, tmp_path):
        with pytest.raises(SystemExit):
            consola.main([str(tmp_path), "--hoy", "20 de septiembre"])

    def test_una_carpeta_se_expande(self, tmp_path):
        escribir(tmp_path, "a.xml", ubl())
        escribir(tmp_path, "notas.txt", "esto no es una factura")
        caminos = consola.expandir([str(tmp_path)])
        assert [c.name for c in caminos] == ["a.xml"]

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
