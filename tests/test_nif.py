"""Comprobaciones de la validación de NIF, NIE y CIF."""

import pytest

from validador import nif


class TestNIF:
    @pytest.mark.parametrize(
        "documento",
        [
            "12345678Z",  # la letra de 12345678 es Z
            "00000000T",
            "99999999R",
            "12345678-Z",  # con guion
            "12345678 z",  # con espacio y en minúscula
        ],
    )
    def test_nif_valido(self, documento):
        assert nif.validar(documento)

    def test_letra_incorrecta_dice_cual_toca(self):
        resultado = nif.validar("12345678A")
        assert not resultado
        assert resultado.tipo == "NIF"
        assert "Z" in resultado.motivo

    def test_formato_invalido(self):
        assert not nif.validar("1234567Z")  # solo siete dígitos
        assert not nif.validar("123456789")  # sin letra


class TestNIE:
    @pytest.mark.parametrize(
        "documento",
        [
            "X0000000T",  # X equivale a 0, así que es el mismo que 00000000T
            "Y0000000Z",  # Y equivale a 1 -> 10000000
            "Z0000000M",  # Z equivale a 2 -> 20000000
        ],
    )
    def test_nie_valido(self, documento):
        resultado = nif.validar(documento)
        assert resultado, resultado.motivo
        assert resultado.tipo == "NIE"

    def test_prefijo_cambia_la_letra(self):
        # Mismo número, distinto prefijo: la letra de control cambia.
        assert nif.validar("X0000000T")
        assert not nif.validar("Y0000000T")

    def test_prefijo_invalido(self):
        assert not nif.validar("W0000000T")  # W no es prefijo de NIE


class TestCIF:
    def test_control_digito_obligatorio(self):
        # Las entidades tipo A y B llevan siempre dígito de control.
        resultado = nif.validar("A0000000J")
        assert not resultado
        assert "dígito de control" in resultado.motivo

    def test_control_letra_obligatorio(self):
        # Las entidades tipo P, Q, R, S, N, W y K llevan siempre letra.
        resultado = nif.validar("P00000000")
        assert not resultado
        assert "letra de control" in resultado.motivo

    def test_cif_valido_con_digito(self):
        resultado = nif.validar("A00000000")
        assert resultado, resultado.motivo
        assert resultado.tipo == "CIF"

    def test_cif_valido_con_letra(self):
        resultado = nif.validar("P0000000J")
        assert resultado, resultado.motivo
        assert resultado.tipo == "CIF"

    def test_tipo_de_entidad_desconocido(self):
        # I, O, T, X, Y, Z no son tipos válidos de entidad.
        assert not nif.validar("I0000000J")


class TestDeteccion:
    def test_documento_vacio(self):
        resultado = nif.validar("")
        assert not resultado
        assert "No se ha indicado" in resultado.motivo

    def test_basura(self):
        resultado = nif.validar("no soy un documento")
        assert not resultado
        assert resultado.tipo is None

    def test_normalizar_quita_separadores(self):
        assert nif.normalizar(" 12.345.678-z ") == "12345678Z"
