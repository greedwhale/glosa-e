"""Comprobaciones del calendario de días hábiles y del plazo de estados."""

from datetime import date

import pytest

from validador.calendario import (
    PLAZO_ESTADOS_DIAS_HABILES,
    Calendario,
    domingo_de_pascua,
    festivos_nacionales,
    plazo_estado,
    viernes_santo,
)


class TestPascua:
    @pytest.mark.parametrize(
        "anio,esperado",
        [
            (2024, date(2024, 3, 31)),
            (2025, date(2025, 4, 20)),
            (2026, date(2026, 4, 5)),
            (2027, date(2027, 3, 28)),
            (2028, date(2028, 4, 16)),
        ],
    )
    def test_domingo_de_pascua(self, anio, esperado):
        assert domingo_de_pascua(anio) == esperado

    def test_viernes_santo_es_dos_dias_antes(self):
        assert viernes_santo(2026) == date(2026, 4, 3)

    def test_viernes_santo_siempre_cae_en_viernes(self):
        for anio in range(2024, 2040):
            assert viernes_santo(anio).weekday() == 4


class TestFestivos:
    def test_incluye_los_fijos_y_el_variable(self):
        festivos = festivos_nacionales(2027)
        assert date(2027, 1, 1) in festivos       # Año Nuevo
        assert date(2027, 12, 25) in festivos     # Navidad
        assert viernes_santo(2027) in festivos    # variable

    def test_son_diez_festivos_nacionales(self):
        assert len(festivos_nacionales(2027)) == 10


class TestDiasHabiles:
    def setup_method(self):
        self.cal = Calendario()

    def test_sabado_y_domingo_no_son_habiles(self):
        assert not self.cal.es_habil(date(2026, 9, 5))  # sábado
        assert not self.cal.es_habil(date(2026, 9, 6))  # domingo
        assert self.cal.es_habil(date(2026, 9, 7))      # lunes

    def test_festivo_nacional_no_es_habil(self):
        # 12 de octubre de 2026 cae en lunes y es Fiesta Nacional.
        assert date(2026, 10, 12).weekday() == 0
        assert not self.cal.es_habil(date(2026, 10, 12))

    def test_cuatro_habiles_desde_un_lunes_normal(self):
        # Lunes 7 de septiembre de 2026: sin festivos de por medio.
        assert self.cal.sumar_habiles(date(2026, 9, 7), 4) == date(2026, 9, 11)

    def test_el_fin_de_semana_empuja_el_vencimiento(self):
        # Jueves 10 de septiembre de 2026 + 4 hábiles salta el fin de semana.
        assert self.cal.sumar_habiles(date(2026, 9, 10), 4) == date(2026, 9, 16)

    def test_un_festivo_empuja_un_dia_mas(self):
        # Jueves 8 de octubre de 2026 + 4 hábiles. Sin festivos el plazo
        # vencería el miércoles 14, pero el lunes 12 es Fiesta Nacional y se
        # salta, así que el cuarto hábil cae en el jueves 15.
        assert self.cal.sumar_habiles(date(2026, 10, 8), 4) == date(2026, 10, 15)
        # Comparación directa: la misma cuenta sin ese festivo sí da el 14.
        sin_festivos = Calendario()
        sin_festivos._cache_anios[2026] = set()
        assert sin_festivos.sumar_habiles(date(2026, 10, 8), 4) == date(2026, 10, 14)

    def test_sumar_cero_devuelve_el_mismo_dia(self):
        assert self.cal.sumar_habiles(date(2026, 9, 7), 0) == date(2026, 9, 7)

    def test_dias_negativos_dan_error(self):
        with pytest.raises(ValueError):
            self.cal.sumar_habiles(date(2026, 9, 7), -1)

    def test_festivo_extra_se_respeta(self):
        # Un festivo autonómico añadido a mano debe contar.
        cal = Calendario(festivos_extra={date(2026, 9, 8)})
        assert not cal.es_habil(date(2026, 9, 8))
        assert cal.sumar_habiles(date(2026, 9, 7), 4) == date(2026, 9, 14)

    def test_habiles_entre_es_coherente_con_sumar(self):
        inicio = date(2026, 10, 8)
        fin = self.cal.sumar_habiles(inicio, 4)
        assert self.cal.habiles_entre(inicio, fin) == 4


class TestPlazoEstados:
    def test_plazo_por_defecto_son_cuatro_dias(self):
        plazo = plazo_estado(date(2026, 9, 7))
        assert plazo.dias_habiles == PLAZO_ESTADOS_DIAS_HABILES
        assert plazo.vencimiento == date(2026, 9, 11)

    def test_dias_restantes_antes_del_vencimiento(self):
        cal = Calendario()
        plazo = plazo_estado(date(2026, 9, 7), cal)
        assert plazo.dias_restantes(date(2026, 9, 9), cal) == 2
        assert not plazo.vencido(date(2026, 9, 9))

    def test_dias_restantes_negativos_si_ya_vencio(self):
        cal = Calendario()
        plazo = plazo_estado(date(2026, 9, 7), cal)
        assert plazo.vencido(date(2026, 9, 15))
        assert plazo.dias_restantes(date(2026, 9, 15), cal) == -2

    def test_el_dia_de_vencimiento_todavia_cuenta(self):
        cal = Calendario()
        plazo = plazo_estado(date(2026, 9, 7), cal)
        assert not plazo.vencido(plazo.vencimiento)
        assert plazo.dias_restantes(plazo.vencimiento, cal) == 0
