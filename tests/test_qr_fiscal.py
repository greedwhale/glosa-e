"""La dirección del QR fiscal contra la factura: `validador.qr_fiscal`.

Hasta el 22-10-2026 el anexo solo miraba que hubiera dirección. Reproducido
ese día sobre `44cc805`: la factura de la orden con el QR de otro NIF, de
otra fecha, de otro importe o del entorno de pruebas salía sin una queja.
"""

from datetime import date

import pytest

from validador import qr_fiscal
from validador.incidencias import AVISO, NOTA

AEAT = "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR"
PRUEBAS = "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR"
BUENA = f"{AEAT}?nif=B12345674&numserie=F-2026-0101&fecha=06-10-2026&importe=121.00"

# El ejemplo de la especificación de TicketBAI, con sus dos CRC: 237 el del
# identificador y 007 el de la dirección.
TBAI = "https://batuz.eus/QRTBAI/?id=TBAI-00000006Y-251019-btFpwP8dcLGAF-237&s=T&nf=27174&i=4.70&cr=007"

LA_FACTURA = {"nifs_del_vendedor": {"B12345674"}, "numero": "F-2026-0101",
              "fecha": date(2026, 10, 6), "total": "121.00", "moneda": "EUR"}
LA_DE_TICKETBAI = {"nifs_del_vendedor": {"00000006Y"}, "numero": "T27174",
                   "fecha": date(2019, 10, 25), "total": "4.70", "moneda": "EUR"}


def revisar(direccion, tipo="VERIFACTU", **cambios):
    return qr_fiscal.revisar(direccion, tipo, **{**LA_FACTURA, **cambios})


def tbai(direccion, tipo="TICKETBAI", **cambios):
    return qr_fiscal.revisar(direccion, tipo, **{**LA_DE_TICKETBAI, **cambios})


def con_crc(sin_crc: str) -> str:
    return f"{sin_crc}&cr={qr_fiscal.crc8(sin_crc)}"


class TestElCrcDeTicketBAI:
    def test_da_los_dos_de_la_especificacion(self):
        assert qr_fiscal.crc8("TBAI-00000006Y-251019-btFpwP8dcLGAF-") == "237"
        assert qr_fiscal.crc8(TBAI.rpartition("&cr=")[0]) == "007"


class TestVeriFactu:
    def test_la_buena_no_dice_nada(self):
        assert revisar(BUENA) == []

    def test_sin_descripcion_tampoco(self):
        assert revisar(BUENA, tipo=None) == []

    def test_la_de_no_verificables_vale_igual(self):
        assert revisar(BUENA.replace("ValidarQR?", "ValidarQRNoVerifactu?")) == []

    def test_el_importe_es_el_mismo_numero_con_otra_escritura(self):
        """La especificación pone de ejemplo 241.4: es el mismo que 241.40."""
        assert revisar(BUENA.replace("importe=121.00", "importe=121")) == []

    @pytest.mark.parametrize("viejo, nuevo, esperado, encontrado", [
        ("nif=B12345674", "nif=A12345674", "B12345674", "A12345674"),
        ("numserie=F-2026-0101", "numserie=F-2026-0102", "F-2026-0101", "F-2026-0102"),
        ("fecha=06-10-2026", "fecha=07-10-2026", "06-10-2026", "07-10-2026"),
        ("importe=121.00", "importe=100.00", "121.00", "100.00"),
    ], ids=["el NIF", "el número", "la fecha", "el importe"])
    def test_lo_que_no_cuadra_con_la_factura(self, viejo, nuevo, esperado, encontrado):
        [aviso] = revisar(BUENA.replace(viejo, nuevo))
        assert aviso.codigo == "SPFE-QR-URL" and aviso.gravedad == AVISO
        assert (aviso.esperado, aviso.encontrado) == (esperado, encontrado)

    def test_el_entorno_de_pruebas(self):
        [aviso] = revisar(BUENA.replace(AEAT, PRUEBAS))
        assert "pruebas" in aviso.mensaje and aviso.encontrado == "prewww2.aeat.es"

    def test_una_direccion_que_no_es_de_nadie(self):
        """Como la del ejemplo que mandó la AEAT el 02-10-2026, a un dominio que no existe."""
        [aviso] = revisar("https://www.gob.aeat/wlpl/TIKE-CONT/ValidarQR?nif=B12345674")
        assert "ninguna de las publicadas" in aviso.mensaje
        assert "no se han comparado" in aviso.mensaje

    def test_sin_https(self):
        [aviso] = revisar(BUENA.replace("https://", "http://"))
        assert "https" in aviso.mensaje

    def test_la_de_la_suite_hasta_ahora_solo_llevaba_el_nif(self):
        [aviso] = revisar(f"{AEAT}?nif=B12345674")
        assert aviso.encontrado == "faltan numserie, fecha, importe"

    def test_el_formato_json_nunca_va_en_el_qr(self):
        [aviso] = revisar(BUENA + "&formato=json")
        assert "nunca" in aviso.mensaje and aviso.encontrado == "formato"

    def test_el_idioma_es_del_servicio_y_no_del_qr(self):
        [aviso] = revisar(BUENA + "&idioma=eu")
        assert aviso.encontrado == "idioma"

    def test_un_ampersand_sin_codificar_en_el_numero(self):
        """El ejemplo de error de la especificación: 12345678&G33 sin %26."""
        numero = "12345678&G33"
        bien = BUENA.replace("F-2026-0101", "12345678%26G33")
        assert revisar(bien, numero=numero) == []
        mal = revisar(BUENA.replace("F-2026-0101", numero), numero=numero)
        assert {a.encontrado for a in mal} == {"G33", "12345678"}

    def test_parametros_repetidos(self):
        avisos = revisar(BUENA + "&nif=A12345674")
        assert any(a.encontrado == "nif" for a in avisos)

    @pytest.mark.parametrize("viejo, nuevo", [
        ("nif=B12345674", "nif=ESB12345674"),
        ("fecha=06-10-2026", "fecha=2026-10-06"),
        ("fecha=06-10-2026", "fecha=31-02-2026"),
        ("importe=121.00", "importe=121,00"),
        ("importe=121.00", "importe=121.000"),
    ], ids=["NIF con prefijo", "fecha ISO", "fecha que no existe", "coma decimal",
            "tres decimales"])
    def test_la_forma_de_cada_parametro(self, viejo, nuevo):
        [aviso] = revisar(BUENA.replace(viejo, nuevo))
        assert aviso.encontrado == nuevo.partition("=")[2]

    def test_la_serie_y_el_numero_de_mas_de_sesenta(self):
        largo = "F" * 61
        [aviso] = revisar(BUENA.replace("F-2026-0101", largo), numero=largo)
        assert "sesenta" in aviso.mensaje

    def test_en_otra_moneda_el_importe_no_se_compara_y_se_dice(self):
        [nota] = revisar(BUENA.replace("importe=121.00", "importe=99.00"), moneda="USD")
        assert nota.gravedad == NOTA and "USD" in nota.mensaje

    def test_sin_nif_del_vendedor_no_se_compara(self):
        """Su falta la dice SPFE-NIF: aquí no se repite."""
        assert revisar(BUENA, nifs_del_vendedor=set()) == []

    def test_la_descripcion_dice_ticketbai(self):
        [aviso] = revisar(BUENA, tipo="TICKETBAI")
        assert aviso.campo == "Tipo de QR (BT-123)"


class TestTicketBAI:
    def test_el_ejemplo_de_la_especificacion_no_dice_nada(self):
        assert tbai(TBAI) == []

    @pytest.mark.parametrize("direccion", [
        "https://ticketbai.araba.eus/TBAI/QRTBAI",
        "https://ticketbai.araba.eus/tbai/qrtbai/",
        "https://tbai.egoitza.gipuzkoa.eus/qr/",
    ], ids=["Araba, la especificación", "Araba, su anexo V", "Gipuzkoa"])
    def test_las_otras_dos_haciendas(self, direccion):
        sin_crc = TBAI.rpartition("&cr=")[0].replace("https://batuz.eus/QRTBAI/", direccion)
        assert tbai(con_crc(sin_crc)) == []

    def test_el_crc_de_la_direccion(self):
        [aviso] = tbai(TBAI.replace("cr=007", "cr=008"))
        assert (aviso.esperado, aviso.encontrado) == ("007", "008")

    def test_el_crc_no_va_el_ultimo(self):
        avisos = tbai(TBAI.replace("&i=4.70&cr=007", "&cr=007&i=4.70"))
        assert any("el último" in a.mensaje for a in avisos)

    def test_el_crc_del_identificador(self):
        sin_crc = TBAI.rpartition("&cr=")[0].replace("-237", "-238")
        [aviso] = tbai(con_crc(sin_crc))
        assert (aviso.esperado, aviso.encontrado) == ("237", "238")

    @pytest.mark.parametrize("cambio, esperado, encontrado", [
        ({"nifs_del_vendedor": {"B12345674"}}, "B12345674", "00000006Y"),
        ({"fecha": date(2019, 10, 26)}, "26-10-2019", "25-10-2019"),
        ({"numero": "T27175"}, "T27175", "T27174"),
        ({"total": "4.71"}, "4.71", "4.70"),
    ], ids=["el NIF", "la fecha", "la serie y el número", "el importe"])
    def test_lo_que_no_cuadra_con_la_factura(self, cambio, esperado, encontrado):
        [aviso] = tbai(TBAI, **cambio)
        assert aviso.gravedad == AVISO
        assert (aviso.esperado, aviso.encontrado) == (esperado, encontrado)

    def test_sin_serie(self):
        sin_crc = TBAI.rpartition("&cr=")[0].replace("&s=T", "")
        assert tbai(con_crc(sin_crc), numero="27174") == []

    def test_un_identificador_sin_su_forma(self):
        sin_crc = TBAI.rpartition("&cr=")[0].replace("TBAI-00000006Y", "TBAI-0000006Y")
        [aviso] = tbai(con_crc(sin_crc))
        assert "treinta y nueve" in aviso.mensaje

    def test_la_descripcion_dice_verifactu(self):
        [aviso] = tbai(TBAI, tipo="VERIFACTU")
        assert aviso.campo == "Tipo de QR (BT-123)"
