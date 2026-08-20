"""Comprobaciones del código único de factura (RD 238/2026)."""

from datetime import date

import pytest

from validador import codigo_unico
from validador.codigo_unico import CodigoUnico, Registro
from validador.incidencias import AVISO, ERROR

# NIF de empresa válido: B12345674. El dígito de control está calculado, no
# inventado; hay un test abajo que lo deja por escrito.
NIF_EMISOR = "B12345674"
HOY = date(2026, 9, 20)
FECHA = date(2026, 9, 7)


def cu(numero="F-2026-001", fecha=FECHA, nif=NIF_EMISOR, serie=None):
    return CodigoUnico(nif, numero, fecha, serie=serie)


def codigos(incidencias, gravedad=None):
    return {
        i.codigo for i in incidencias if gravedad is None or i.gravedad == gravedad
    }


# --- El objeto -------------------------------------------------------------


class TestCodigoUnico:
    def test_el_nif_de_prueba_es_valido(self):
        """Si este NIF fuera inválido, media suite estaría midiendo otra cosa."""
        from validador import nif

        assert nif.validar(NIF_EMISOR), nif.validar(NIF_EMISOR).motivo

    def test_serie_y_numero_se_juntan(self):
        assert cu(numero="001", serie="F2026-").numero_completo == "F2026-001"

    def test_sin_serie_el_numero_va_solo(self):
        assert cu(numero="F-2026-001").numero_completo == "F-2026-001"

    def test_canonico_lleva_los_tres_datos(self):
        assert cu().canonico() == f"{NIF_EMISOR}|F-2026-001|2026-09-07"

    def test_la_huella_es_estable(self):
        assert cu().huella() == cu().huella()
        assert len(cu().huella()) == 64

    def test_la_huella_distingue_facturas_distintas(self):
        assert cu(numero="F-2026-001").huella() != cu(numero="F-2026-002").huella()
        assert cu(fecha=date(2026, 9, 8)).huella() != cu().huella()

    def test_la_huella_no_colisiona_al_partir_distinto(self):
        """Sin la longitud por delante, estas dos darían la misma huella.

        Concatenadas a pelo, ("", "B12345674X") y ("B12345674", "X") producen
        la misma cadena. Son facturas distintas y deben tener huella distinta.
        """
        a = CodigoUnico("", "B12345674X", FECHA)
        b = CodigoUnico("B12345674", "X", FECHA)
        assert a.huella() != b.huella()

    def test_la_clave_ignora_mayusculas_y_espacios(self):
        assert cu(numero="f-2026-001").clave() == cu(numero="  F-2026-001 ").clave()

    def test_la_clave_no_ignora_la_fecha(self):
        assert cu().clave() != cu(fecha=date(2026, 9, 8)).clave()


# --- Reglas sobre un código suelto -----------------------------------------


class TestCodigoSuelto:
    def test_uno_bueno_no_da_nada(self):
        assert codigo_unico.revisar(cu(), hoy=HOY) == []

    def test_nif_invalido(self):
        incidencias = codigo_unico.revisar(cu(nif="B12345670"), hoy=HOY)
        assert "CU-01" in codigos(incidencias, ERROR)

    def test_sin_nif(self):
        incidencias = codigo_unico.revisar(cu(nif=""), hoy=HOY)
        problema = next(i for i in incidencias if i.codigo == "CU-01")
        assert problema.encontrado == "(falta)"

    def test_el_mensaje_del_nif_explica_por_que(self):
        incidencias = codigo_unico.revisar(cu(nif="12345678A"), hoy=HOY)
        problema = next(i for i in incidencias if i.codigo == "CU-01")
        assert "Z" in problema.mensaje  # la letra que debería llevar

    def test_sin_numero(self):
        incidencias = codigo_unico.revisar(cu(numero="  "), hoy=HOY)
        assert "CU-02" in codigos(incidencias, ERROR)

    def test_sin_numero_sigue_mirando_la_fecha(self):
        """Que falte el número no debe tapar un problema de fecha."""
        incidencias = codigo_unico.revisar(
            cu(numero="", fecha=date(2027, 1, 1)), hoy=HOY
        )
        assert {"CU-02", "CU-06"} <= codigos(incidencias, ERROR)

    def test_numero_demasiado_largo(self):
        incidencias = codigo_unico.revisar(cu(numero="F" * 61), hoy=HOY)
        problema = next(i for i in incidencias if i.codigo == "CU-03")
        assert problema.gravedad == ERROR
        assert "61 caracteres" == problema.encontrado

    def test_justo_en_el_limite_pasa(self):
        assert codigo_unico.revisar(cu(numero="F" * 60), hoy=HOY) == []

    def test_salto_de_linea_en_el_numero(self):
        incidencias = codigo_unico.revisar(cu(numero="F-2026\n-001"), hoy=HOY)
        assert "CU-04" in codigos(incidencias, ERROR)

    def test_caracteres_no_ascii_solo_avisan(self):
        incidencias = codigo_unico.revisar(cu(numero="FACTURAÑ-001"), hoy=HOY)
        assert "CU-04" in codigos(incidencias, AVISO)
        assert "CU-04" not in codigos(incidencias, ERROR)

    def test_espacios_sobrantes(self):
        incidencias = codigo_unico.revisar(cu(numero=" F-2026-001 "), hoy=HOY)
        problema = next(i for i in incidencias if i.codigo == "CU-05")
        assert problema.gravedad == AVISO
        assert problema.esperado == repr("F-2026-001")

    def test_fecha_futura_es_error(self):
        incidencias = codigo_unico.revisar(cu(fecha=date(2026, 9, 21)), hoy=HOY)
        assert "CU-06" in codigos(incidencias, ERROR)

    def test_hoy_no_es_futuro(self):
        assert codigo_unico.revisar(cu(fecha=HOY), hoy=HOY) == []

    def test_fecha_prescrita_avisa(self):
        incidencias = codigo_unico.revisar(cu(fecha=date(2021, 5, 1)), hoy=HOY)
        assert "CU-07" in codigos(incidencias, AVISO)

    def test_fecha_dentro_de_prescripcion_no_avisa(self):
        assert codigo_unico.revisar(cu(fecha=date(2022, 5, 1)), hoy=HOY) == []


# --- Duplicados ------------------------------------------------------------


class TestRegistro:
    def test_la_primera_vez_no_choca(self):
        registro = Registro()
        assert registro.anotar(cu()) == []
        assert len(registro) == 1

    def test_duplicado_exacto(self):
        registro = Registro()
        registro.anotar(cu())
        incidencias = registro.anotar(cu())
        assert "CU-10" in codigos(incidencias, ERROR)

    def test_mismo_numero_distinta_fecha(self):
        registro = Registro()
        registro.anotar(cu(fecha=date(2026, 9, 7)))
        incidencias = registro.anotar(cu(fecha=date(2026, 9, 8)))
        problema = next(i for i in incidencias if i.codigo == "CU-11")
        assert problema.gravedad == ERROR
        assert "2026-09-07" in problema.esperado
        assert "2026-09-08" in problema.encontrado

    def test_solo_cambia_la_caja(self):
        registro = Registro()
        registro.anotar(cu(numero="F-2026-001"))
        incidencias = registro.anotar(cu(numero="f-2026-001"))
        assert "CU-12" in codigos(incidencias, ERROR)
        assert "CU-10" not in codigos(incidencias)

    def test_facturas_distintas_conviven(self):
        registro = Registro()
        registro.anotar(cu(numero="F-2026-001"))
        assert registro.anotar(cu(numero="F-2026-002")) == []
        assert len(registro) == 2

    def test_contiene(self):
        registro = Registro()
        assert not registro.contiene(cu())
        registro.anotar(cu())
        assert registro.contiene(cu())

    def test_el_mismo_numero_de_otro_emisor_no_choca(self):
        """Dos empresas pueden numerar igual: el NIF forma parte del código."""
        registro = Registro()
        registro.anotar(cu(nif="B12345674"))
        assert registro.anotar(cu(nif="12345678Z")) == []


# --- Correlatividad de la serie --------------------------------------------


class TestSerie:
    def test_serie_correlativa_no_da_nada(self):
        lote = [
            cu(numero="F-2026-001", fecha=date(2026, 9, 1)),
            cu(numero="F-2026-002", fecha=date(2026, 9, 2)),
            cu(numero="F-2026-003", fecha=date(2026, 9, 3)),
        ]
        assert codigo_unico.revisar_lote(lote, hoy=HOY) == []

    def test_hueco_en_la_numeracion(self):
        lote = [cu(numero="F-2026-001"), cu(numero="F-2026-002"), cu(numero="F-2026-005")]
        incidencias = codigo_unico.revisar_lote(lote, hoy=HOY)
        problema = next(i for i in incidencias if i.codigo == "CU-13")
        assert problema.gravedad == AVISO
        assert "2 número(s)" in problema.mensaje
        assert "003 al 004" in problema.encontrado

    def test_un_hueco_de_un_numero_no_se_escribe_como_tramo(self):
        lote = [cu(numero="A-1"), cu(numero="A-3")]
        problema = next(
            i for i in codigo_unico.revisar_lote(lote, hoy=HOY) if i.codigo == "CU-13"
        )
        assert problema.encontrado == "falta(n) 2"
        assert " al " not in problema.encontrado

    def test_series_distintas_no_se_mezclan(self):
        """A-001 y B-001 son dos series: no hay hueco entre ellas."""
        lote = [cu(numero="A-001"), cu(numero="B-001")]
        assert "CU-13" not in codigos(codigo_unico.revisar_lote(lote, hoy=HOY))

    def test_emisores_distintos_no_se_mezclan(self):
        lote = [
            cu(numero="F-001", nif="B12345674"),
            cu(numero="F-009", nif="12345678Z"),
        ]
        assert "CU-13" not in codigos(codigo_unico.revisar_lote(lote, hoy=HOY))

    def test_fecha_que_retrocede(self):
        lote = [
            cu(numero="F-2026-001", fecha=date(2026, 9, 10)),
            cu(numero="F-2026-002", fecha=date(2026, 9, 5)),
        ]
        problema = next(
            i for i in codigo_unico.revisar_lote(lote, hoy=HOY) if i.codigo == "CU-14"
        )
        assert problema.gravedad == AVISO
        assert "2026-09-10" in problema.encontrado

    def test_misma_fecha_no_es_retroceso(self):
        lote = [
            cu(numero="F-2026-001", fecha=FECHA),
            cu(numero="F-2026-002", fecha=FECHA),
        ]
        assert "CU-14" not in codigos(codigo_unico.revisar_lote(lote, hoy=HOY))

    def test_el_orden_de_llegada_no_importa(self):
        """La serie se ordena por número, no por el orden del fichero."""
        lote = [
            cu(numero="F-2026-002", fecha=date(2026, 9, 5)),
            cu(numero="F-2026-001", fecha=date(2026, 9, 10)),
        ]
        assert "CU-14" in codigos(codigo_unico.revisar_lote(lote, hoy=HOY))

    def test_relleno_de_ceros_incoherente(self):
        lote = [cu(numero="F-1"), cu(numero="F-001")]
        incidencias = codigo_unico.revisar_lote(lote, hoy=HOY)
        problema = next(i for i in incidencias if i.codigo == "CU-15")
        assert problema.gravedad == AVISO
        assert "F-001" in problema.encontrado and "F-1" in problema.encontrado
        # No es un duplicado: son dos códigos únicos distintos, y ese es
        # justamente el problema.
        assert "CU-10" not in codigos(incidencias)

    def test_mayusculas_y_espacios_no_son_relleno_de_ceros(self):
        """Dos escrituras de la misma factura son CU-12, no CU-15.

        Antes se comparaban los numeros en crudo, asi que cualquier diferencia
        de caja o de espacios se contaba tambien como relleno incoherente y el
        informe daba dos quejas por un solo problema.
        """
        lote = [cu(numero="F-2026-006"), cu(numero="f-2026-006 ")]
        resultado = codigos(codigo_unico.revisar_lote(lote, hoy=HOY))
        assert "CU-12" in resultado
        assert "CU-15" not in resultado

    def test_una_factura_sola_no_tiene_correlatividad(self):
        assert codigo_unico.revisar_lote([cu()], hoy=HOY) == []

    def test_numero_sin_digitos_no_rompe(self):
        lote = [cu(numero="FACTURA"), cu(numero="ABONO")]
        assert codigo_unico.revisar_lote(lote, hoy=HOY) == []

    def test_muchos_huecos_se_resumen(self):
        lote = [cu(numero=f"F-{n:03d}") for n in (1, 3, 5, 7, 9, 11, 13, 15)]
        problema = next(
            i for i in codigo_unico.revisar_lote(lote, hoy=HOY) if i.codigo == "CU-13"
        )
        assert "tramo(s) mas" in problema.encontrado


# --- Extracción desde el documento -----------------------------------------


UBL = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:UBLVersionID>2.1</cbc:UBLVersionID>
  <cbc:CustomizationID>urn:cen.eu:en16931:2017</cbc:CustomizationID>
  <cbc:ID>F-2026-001</cbc:ID>
  <cbc:IssueDate>2026-09-07</cbc:IssueDate>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PartyTaxScheme><cbc:CompanyID>ESB12345674</cbc:CompanyID></cac:PartyTaxScheme>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:InvoiceLine><cbc:ID>1</cbc:ID></cac:InvoiceLine>
</Invoice>"""

# El vendedor solo trae PartyLegalEntity; el comprador sí trae PartyTaxScheme.
# Si la búsqueda del NIF no fuera relativa al vendedor, cogería la del comprador.
UBL_NIF_EN_OTRO_SITIO = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:ID>F-2026-001</cbc:ID>
  <cbc:IssueDate>2026-09-07</cbc:IssueDate>
  <cac:AccountingSupplierParty><cac:Party>
    <cac:PartyLegalEntity><cbc:CompanyID>ESB12345674</cbc:CompanyID></cac:PartyLegalEntity>
  </cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PartyTaxScheme><cbc:CompanyID>ES12345678Z</cbc:CompanyID></cac:PartyTaxScheme>
  </cac:Party></cac:AccountingCustomerParty>
</Invoice>"""

FACTURAE = """<?xml version="1.0" encoding="UTF-8"?>
<fe:Facturae xmlns:fe="http://www.facturae.es/Facturae/2009/v3.2/Facturae">
  <FileHeader><SchemaVersion>3.2</SchemaVersion></FileHeader>
  <Parties><SellerParty><TaxIdentification>
    <TaxIdentificationNumber>ESB12345674</TaxIdentificationNumber>
  </TaxIdentification></SellerParty></Parties>
  <Invoices>
    <Invoice>
      <InvoiceHeader>
        <InvoiceNumber>001</InvoiceNumber>
        <InvoiceSeriesCode>F2026-</InvoiceSeriesCode>
      </InvoiceHeader>
      <InvoiceIssueData><IssueDate>2026-09-01</IssueDate></InvoiceIssueData>
    </Invoice>
    <Invoice>
      <InvoiceHeader>
        <InvoiceNumber>002</InvoiceNumber>
        <InvoiceSeriesCode>F2026-</InvoiceSeriesCode>
      </InvoiceHeader>
      <InvoiceIssueData><IssueDate>2026-09-02</IssueDate></InvoiceIssueData>
    </Invoice>
  </Invoices>
</fe:Facturae>"""

CII = """<?xml version="1.0" encoding="UTF-8"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
    xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"
    xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">
  <rsm:ExchangedDocumentContext>
    <ram:GuidelineSpecifiedDocumentContextParameter>
      <ram:ID>urn:cen.eu:en16931:2017</ram:ID>
    </ram:GuidelineSpecifiedDocumentContextParameter>
  </rsm:ExchangedDocumentContext>
  <rsm:ExchangedDocument>
    <ram:ID>F-2026-001</ram:ID>
    <ram:TypeCode>380</ram:TypeCode>
    <ram:IssueDateTime>
      <udt:DateTimeString format="102">20260907</udt:DateTimeString>
    </ram:IssueDateTime>
  </rsm:ExchangedDocument>
  <rsm:SupplyChainTradeTransaction><ram:ApplicableHeaderTradeAgreement>
    <ram:SellerTradeParty><ram:SpecifiedTaxRegistration>
      <ram:ID schemeID="VA">ESB12345674</ram:ID>
    </ram:SpecifiedTaxRegistration></ram:SellerTradeParty>
  </ram:ApplicableHeaderTradeAgreement></rsm:SupplyChainTradeTransaction>
</rsm:CrossIndustryInvoice>"""


class TestExtraccion:
    def test_ubl(self):
        (codigo,) = codigo_unico.extraer(UBL)
        assert codigo.nif_emisor == NIF_EMISOR  # sin el prefijo ES
        assert codigo.numero == "F-2026-001"
        assert codigo.fecha == FECHA

    def test_ubl_no_confunde_el_numero_con_el_de_una_linea(self):
        (codigo,) = codigo_unico.extraer(UBL)
        assert codigo.numero != "1"

    def test_ubl_lee_el_nif_del_vendedor_no_el_del_comprador(self):
        (codigo,) = codigo_unico.extraer(UBL_NIF_EN_OTRO_SITIO)
        assert codigo.nif_emisor == NIF_EMISOR
        assert codigo.nif_emisor != "12345678Z"

    def test_facturae_puede_traer_varias(self):
        extraidos = codigo_unico.extraer(FACTURAE)
        assert len(extraidos) == 2
        assert [c.numero_completo for c in extraidos] == ["F2026-001", "F2026-002"]
        assert all(c.nif_emisor == NIF_EMISOR for c in extraidos)

    def test_cii_con_fecha_en_formato_102(self):
        (codigo,) = codigo_unico.extraer(CII)
        assert codigo.fecha == FECHA
        assert codigo.nif_emisor == NIF_EMISOR

    def test_documento_ajeno(self):
        assert codigo_unico.extraer(b"<pedido/>") == []

    def test_sin_fecha_no_se_puede_componer(self):
        assert codigo_unico.extraer(UBL.replace("<cbc:IssueDate>2026-09-07</cbc:IssueDate>", "")) == []


class TestLeerFecha:
    @pytest.mark.parametrize(
        "bruto",
        ["2026-09-07", "20260907", "07-09-2026", "07/09/2026", "2026-09-07+02:00"],
    )
    def test_formatos_admitidos(self, bruto):
        assert codigo_unico.leer_fecha(bruto) == FECHA

    @pytest.mark.parametrize("bruto", [None, "", "  ", "no es fecha", "2026-13-40"])
    def test_lo_que_no_es_fecha(self, bruto):
        assert codigo_unico.leer_fecha(bruto) is None


class TestLimpiarNif:
    def test_quita_el_prefijo_de_pais(self):
        assert codigo_unico.limpiar_nif("ESB12345674") == "B12345674"

    def test_deja_en_paz_un_nif_sin_prefijo(self):
        assert codigo_unico.limpiar_nif("B12345674") == "B12345674"

    def test_no_muerde_un_cif_que_empieza_por_es(self):
        """ES1234567 es un CIF válido de comunidad de bienes: nueve caracteres."""
        assert codigo_unico.limpiar_nif("E51234567") == "E51234567"
        assert len(codigo_unico.limpiar_nif("ES1234567")) == 9

    def test_normaliza_guiones_y_espacios(self):
        assert codigo_unico.limpiar_nif(" es-b12345674 ") == "B12345674"


# --- De punta a punta ------------------------------------------------------


class TestValidar:
    def test_documento_correcto(self):
        informe = codigo_unico.validar(UBL, hoy=HOY)
        assert informe.conforme, informe.detalle()

    def test_facturae_con_dos_facturas_iguales(self):
        repetido = FACTURAE.replace("<InvoiceNumber>002</InvoiceNumber>",
                                    "<InvoiceNumber>001</InvoiceNumber>")
        informe = codigo_unico.validar(repetido, hoy=HOY)
        # Mismo número, distinta fecha: numeración reutilizada.
        assert "CU-11" in codigos(informe.incidencias, ERROR)

    def test_sin_numero_ni_fecha(self):
        informe = codigo_unico.validar(b"<pedido/>", hoy=HOY)
        assert not informe.deteccion
        assert informe.incidencias == []

    def test_xml_reconocido_pero_incompleto(self):
        sin_fecha = UBL.replace("<cbc:IssueDate>2026-09-07</cbc:IssueDate>", "")
        informe = codigo_unico.validar(sin_fecha, hoy=HOY)
        assert "CU-00" in codigos(informe.incidencias, ERROR)

    def test_el_informe_se_puede_leer(self):
        futuro = UBL.replace("2026-09-07", "2027-01-15")
        informe = codigo_unico.validar(futuro, hoy=HOY)
        texto = informe.detalle()
        assert "CU-06" in texto
        assert "fecha futura" in texto
