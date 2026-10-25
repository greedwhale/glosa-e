"""CUENTA-DISTINTA: el mismo emisor pidiendo el pago en cuentas distintas.

Cada factura de aquí está bien mirada sola; lo que se prueba es lo que solo se
ve poniéndolas juntas. Las facturas son las de prueba de `test_factura.py`
(UBL), `test_facturae.py` (Facturae) y `test_codigo_unico.py` (CII), con la
instrucción de pago añadida, para que no haya una cuarta manera de fabricarlas.
"""

from lxml import etree

import pytest

from test_codigo_unico import CII
from test_facturae import fe
from test_factura import HOY, ubl

from validador import cuentas_de_cobro, factura
from validador.cuentas_de_cobro import Cobro
from validador.formato import detectar, parser
from validador.incidencias import AVISO

# Dos IBAN de forma correcta: el de ejemplo de la documentación bancaria, que
# ya usa `ejemplos/fe-0001.xml`, y otro de la misma entidad.
CUENTA_A = "ES9121000418450200051332"
CUENTA_B = "ES7921000813610123456789"


def con_cuenta_ubl(cuenta: str | None, numero="F-2026-0001", nif="ESB12345674",
                   pais="ES") -> str:
    documento = ubl(numero=numero, nif=nif, pais=pais)
    if cuenta is None:
        return documento
    return documento.replace(
        "<cac:TaxTotal>",
        "<cac:PaymentMeans><cbc:PaymentMeansCode>58</cbc:PaymentMeansCode>"
        f"<cac:PayeeFinancialAccount><cbc:ID>{cuenta}</cbc:ID>"
        "</cac:PayeeFinancialAccount></cac:PaymentMeans><cac:TaxTotal>", 1)


def con_cuenta_cii(cuenta: str) -> str:
    return CII.replace(
        "</ram:ApplicableHeaderTradeAgreement>",
        "</ram:ApplicableHeaderTradeAgreement><ram:ApplicableHeaderTradeSettlement>"
        "<ram:SpecifiedTradeSettlementPaymentMeans><ram:TypeCode>58</ram:TypeCode>"
        f"<ram:PayeePartyCreditorFinancialAccount><ram:IBANID>{cuenta}</ram:IBANID>"
        "</ram:PayeePartyCreditorFinancialAccount>"
        "</ram:SpecifiedTradeSettlementPaymentMeans>"
        "</ram:ApplicableHeaderTradeSettlement>", 1)


def facturae_con_cuentas(*cuentas: str) -> str:
    """Un Facturae con una factura por cuenta, cada una pidiendo la suya."""
    numeros = [f"F-{n:03d}" for n in range(1, len(cuentas) + 1)]
    documento = fe(mas_facturas=numeros[1:], modalidad="L", cuantas=str(len(cuentas)))
    trozos = documento.split("</Invoice>")
    for indice, cuenta in enumerate(cuentas):
        trozos[indice] += (
            "<PaymentDetails><Installment><InstallmentDueDate>2026-04-02"
            "</InstallmentDueDate><InstallmentAmount>200.00</InstallmentAmount>"
            "<PaymentMeans>04</PaymentMeans><AccountToBeCredited>"
            f"<IBAN>{cuenta}</IBAN></AccountToBeCredited></Installment>"
            "</PaymentDetails>")
    return "</Invoice>".join(trozos)


def cobros(xml: str):
    raiz = etree.fromstring(xml.encode("utf-8"), parser=parser())
    return cuentas_de_cobro.extraer_de(raiz, detectar(xml))


def lote(tmp_path, *documentos: str):
    rutas = []
    for indice, documento in enumerate(documentos, start=1):
        ruta = tmp_path / f"f{indice}.xml"
        ruta.write_text(documento, encoding="utf-8")
        rutas.append(ruta)
    return factura.validar_lote(rutas, hoy=HOY)


def distintas(incidencias):
    return [i for i in incidencias if i.codigo == "CUENTA-DISTINTA"]


class TestLaLecturaDeCadaSintaxis:
    def test_ubl(self):
        assert cobros(con_cuenta_ubl(CUENTA_A)) == [
            Cobro("B12345674", "F-2026-0001", (CUENTA_A,))]

    def test_cii(self):
        assert cobros(con_cuenta_cii(CUENTA_A)) == [
            Cobro("B12345674", "F-2026-001", (CUENTA_A,))]

    def test_facturae_una_por_factura_con_su_serie(self):
        assert cobros(facturae_con_cuentas(CUENTA_A, CUENTA_B)) == [
            Cobro("B12345674", "AF-001", (CUENTA_A,)),
            Cobro("B12345674", "AF-002", (CUENTA_B,)),
        ]

    def test_la_misma_cuenta_con_espacios_es_la_misma(self):
        con_espacios = " ".join(CUENTA_A[i:i + 4] for i in range(0, len(CUENTA_A), 4))
        assert cobros(con_cuenta_ubl(con_espacios.lower()))[0].cuentas == (CUENTA_A,)

    def test_sin_instruccion_de_pago_no_hay_cuenta(self):
        assert cobros(con_cuenta_ubl(None))[0].cuentas == ()


class TestLaRegla:
    def test_dos_facturas_dos_cuentas_es_un_aviso(self):
        salta = cuentas_de_cobro.reglas_de_lote([
            Cobro("B12345674", "F-1", (CUENTA_A,)),
            Cobro("B12345674", "F-2", (CUENTA_B,)),
        ], procedencias=["a.xml", "b.xml"])
        assert len(salta) == 1 and salta[0].gravedad == AVISO
        assert salta[0].encontrado == f"{CUENTA_A} en 1 factura · {CUENTA_B} en 1 factura"
        assert "la factura F-2 (b.xml)" in salta[0].mensaje
        assert salta[0].ficheros == ("a.xml", "b.xml")

    def test_la_que_sale_en_pocas_va_al_final_y_las_muchas_se_resumen(self):
        muchas = [Cobro("B12345674", f"F-{n}", (CUENTA_A,)) for n in range(1, 10)]
        salta = cuentas_de_cobro.reglas_de_lote(muchas + [Cobro("B12345674", "F-10", (CUENTA_B,))])
        assert salta[0].encontrado == f"{CUENTA_A} en 9 facturas · {CUENTA_B} en 1 factura"
        assert "9 facturas, entre ellas F-1, F-2 y F-3" in salta[0].mensaje
        assert salta[0].mensaje.index(CUENTA_A) < salta[0].mensaje.index(CUENTA_B)

    def test_la_misma_cuenta_siempre_no_dice_nada(self):
        assert cuentas_de_cobro.reglas_de_lote([
            Cobro("B12345674", "F-1", (CUENTA_A,)),
            Cobro("B12345674", "F-2", (CUENTA_A,)),
        ]) == []

    def test_dos_emisores_cada_uno_con_la_suya_no_dice_nada(self):
        assert cuentas_de_cobro.reglas_de_lote([
            Cobro("B12345674", "F-1", (CUENTA_A,)),
            Cobro("B85905495", "F-1", (CUENTA_B,)),
        ]) == []

    def test_las_mismas_dos_cuentas_en_cada_factura_no_es_un_cambio(self):
        assert cuentas_de_cobro.reglas_de_lote([
            Cobro("B12345674", "F-1", (CUENTA_A, CUENTA_B)),
            Cobro("B12345674", "F-2", (CUENTA_B, CUENTA_A)),
        ]) == []

    def test_una_cuenta_de_mas_si_lo_es(self):
        assert len(cuentas_de_cobro.reglas_de_lote([
            Cobro("B12345674", "F-1", (CUENTA_A,)),
            Cobro("B12345674", "F-2", (CUENTA_A, CUENTA_B)),
        ])) == 1

    def test_una_factura_sin_cuenta_no_cuenta(self):
        assert cuentas_de_cobro.reglas_de_lote([
            Cobro("B12345674", "F-1", (CUENTA_A,)),
            Cobro("B12345674", "F-2", ()),
        ]) == []


class TestEnElOrquestador:
    def test_un_facturae_con_dos_cuentas_lo_dice_en_su_informe(self):
        informe = factura.validar(facturae_con_cuentas(CUENTA_A, CUENTA_B), hoy=HOY)
        salta = distintas(informe.incidencias)
        assert len(salta) == 1 and salta[0].gravedad == AVISO
        assert factura.origen(salta[0]) == "De la casa"

    def test_entre_dos_ficheros_sale_entre_ficheros(self, tmp_path):
        hecho = lote(tmp_path, con_cuenta_ubl(CUENTA_A, numero="F-1"),
                     con_cuenta_ubl(CUENTA_B, numero="F-2"))
        salta = distintas(hecho.cruzadas)
        assert len(salta) == 1
        assert "la factura F-2 (f2.xml)" in salta[0].mensaje
        assert not any(distintas(i.incidencias) for _, i in hecho.informes)

    def test_es_un_aviso_y_no_quita_la_conformidad_del_lote(self, tmp_path):
        hecho = lote(tmp_path, con_cuenta_ubl(CUENTA_A, numero="F-1"),
                     con_cuenta_ubl(CUENTA_B, numero="F-2"))
        assert not distintas(hecho.errores) and not hecho.senialados

    def test_lo_que_ya_dijo_un_facturae_no_se_repite_entre_ficheros(self, tmp_path):
        hecho = lote(tmp_path, facturae_con_cuentas(CUENTA_A, CUENTA_B))
        assert len(distintas(hecho.informes[0][1].incidencias)) == 1
        assert distintas(hecho.cruzadas) == []

    def test_un_proveedor_de_fuera_tambien(self, tmp_path):
        """El código único solo junta facturas españolas; las cuentas, todas."""
        hecho = lote(tmp_path,
                     con_cuenta_ubl(CUENTA_A, numero="F-1", nif="NL123456789B01", pais="NL"),
                     con_cuenta_ubl(CUENTA_B, numero="F-2", nif="NL123456789B01", pais="NL"))
        assert len(distintas(hecho.cruzadas)) == 1
        assert "NL123456789B01" in distintas(hecho.cruzadas)[0].mensaje

    @pytest.mark.parametrize("cuentas", [(CUENTA_A, CUENTA_A), (CUENTA_A,)])
    def test_y_sin_cambio_de_cuenta_no_sale(self, tmp_path, cuentas):
        hecho = lote(tmp_path, *(con_cuenta_ubl(c, numero=f"F-{n}")
                                 for n, c in enumerate(cuentas, start=1)))
        assert distintas(hecho.cruzadas) == []
