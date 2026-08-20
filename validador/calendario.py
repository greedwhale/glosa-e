"""Días hábiles españoles y el plazo de cuatro días de los estados de factura.

El RD 238/2026 obliga al destinatario a comunicar el estado de una factura
—aceptación, rechazo comercial, o pago efectivo y su fecha— en un máximo de
cuatro días hábiles, excluyendo sábados, domingos y festivos nacionales.

Calcular eso bien es más fiddly de lo que parece: hay un festivo variable
(Viernes Santo) que depende de la Pascua, y el calendario laboral que publica
el BOE cada año puede trasladar festivos que caen en domingo. Por eso la lista
de festivos es un dato configurable y no una constante enterrada en el código.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

# Plazo que fija el RD 238/2026 para comunicar el estado de una factura.
PLAZO_ESTADOS_DIAS_HABILES = 4

# Festivos nacionales de fecha fija, como (mes, día).
_FESTIVOS_FIJOS: tuple[tuple[int, int], ...] = (
    (1, 1),    # Año Nuevo
    (1, 6),    # Epifanía del Señor
    (5, 1),    # Fiesta del Trabajo
    (8, 15),   # Asunción de la Virgen
    (10, 12),  # Fiesta Nacional de España
    (11, 1),   # Todos los Santos
    (12, 6),   # Día de la Constitución
    (12, 8),   # Inmaculada Concepción
    (12, 25),  # Natividad del Señor
)


def domingo_de_pascua(anio: int) -> date:
    """Devuelve el Domingo de Pascua del año dado.

    Usa el algoritmo gregoriano anónimo (Meeus/Jones/Butcher), que es el
    estándar para el calendario gregoriano.
    """
    a = anio % 19
    b, c = divmod(anio, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ele = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ele) // 451
    mes, dia = divmod(h + ele - 7 * m + 114, 31)
    return date(anio, mes, dia + 1)


def viernes_santo(anio: int) -> date:
    """Viernes Santo: dos días antes del Domingo de Pascua."""
    return domingo_de_pascua(anio) - timedelta(days=2)


def festivos_nacionales(anio: int) -> set[date]:
    """Festivos nacionales de un año, incluido el Viernes Santo.

    No incluye festivos autonómicos ni locales: el RD 238/2026 habla de
    festivos nacionales. Si necesitas añadir otros, pásalos a `Calendario`.
    """
    festivos = {date(anio, mes, dia) for mes, dia in _FESTIVOS_FIJOS}
    festivos.add(viernes_santo(anio))
    return festivos


@dataclass
class Calendario:
    """Calendario de días hábiles.

    `festivos_extra` permite añadir festivos autonómicos, locales o los
    traslados que publique el BOE para un año concreto, sin tocar el código.
    """

    festivos_extra: set[date] = field(default_factory=set)
    _cache_anios: dict[int, set[date]] = field(default_factory=dict, repr=False)

    def festivos(self, anio: int) -> set[date]:
        """Festivos aplicables a un año, nacionales más los añadidos."""
        if anio not in self._cache_anios:
            self._cache_anios[anio] = festivos_nacionales(anio)
        return self._cache_anios[anio] | {
            f for f in self.festivos_extra if f.year == anio
        }

    def es_habil(self, dia: date) -> bool:
        """Un día es hábil si no es sábado, ni domingo, ni festivo."""
        if dia.weekday() >= 5:  # 5 = sábado, 6 = domingo
            return False
        return dia not in self.festivos(dia.year)

    def siguiente_habil(self, desde: date) -> date:
        """Primer día hábil estrictamente posterior a `desde`."""
        dia = desde + timedelta(days=1)
        while not self.es_habil(dia):
            dia += timedelta(days=1)
        return dia

    def sumar_habiles(self, desde: date, dias: int) -> date:
        """Suma `dias` días hábiles a partir de `desde`.

        El día de partida no cuenta: si recibes una factura el lunes y el plazo
        es de cuatro días hábiles, vence el viernes.
        """
        if dias < 0:
            raise ValueError("El número de días hábiles no puede ser negativo.")
        dia = desde
        for _ in range(dias):
            dia = self.siguiente_habil(dia)
        return dia

    def habiles_entre(self, desde: date, hasta: date) -> int:
        """Cuenta días hábiles entre dos fechas, sin contar el día de partida."""
        if hasta < desde:
            raise ValueError("La fecha final es anterior a la inicial.")
        contador = 0
        dia = desde
        while dia < hasta:
            dia += timedelta(days=1)
            if self.es_habil(dia):
                contador += 1
        return contador


@dataclass(frozen=True)
class Plazo:
    """Plazo de comunicación de un estado de factura."""

    inicio: date
    vencimiento: date
    dias_habiles: int

    def dias_restantes(self, hoy: date, calendario: Calendario) -> int:
        """Días hábiles que quedan. Negativo si el plazo ya venció."""
        if hoy <= self.vencimiento:
            return calendario.habiles_entre(hoy, self.vencimiento)
        return -calendario.habiles_entre(self.vencimiento, hoy)

    def vencido(self, hoy: date) -> bool:
        return hoy > self.vencimiento


def plazo_estado(
    fecha_recepcion: date,
    calendario: Calendario | None = None,
    dias: int = PLAZO_ESTADOS_DIAS_HABILES,
) -> Plazo:
    """Calcula cuándo vence el plazo para comunicar el estado de una factura.

    >>> plazo_estado(date(2026, 9, 7)).vencimiento   # un lunes normal
    datetime.date(2026, 9, 11)
    """
    cal = calendario or Calendario()
    return Plazo(
        inicio=fecha_recepcion,
        vencimiento=cal.sumar_habiles(fecha_recepcion, dias),
        dias_habiles=dias,
    )
