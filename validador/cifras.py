"""Cómo se escriben las cifras en lo que lee una persona.

Hasta el 05-10-2026 el informe escribía todas las cifras con `:.2f`: con punto
decimal, que en castellano se lee como separador de miles («90.00», «se aparta
0.50»), y redondeando también lo que copiaba del fichero, así que «Tiene» no
decía lo que tenía. Un 100 salía 100.00 y un 100.125 salía 100.12, la cifra que
no está en el fichero y que la regla no había comparado.

Ahora cada cifra va por una de tres puertas, según de dónde sale:

- **`calculada`**: lo que ha calculado el validador. Coma decimal, dos
  decimales y el redondeo de las reglas, `sintaxis.redondear`, que lleva las
  mitades hacia arriba como el esquematrón. Las reglas ya le pasan la cifra
  que compararon (ver BR-CO-10 en `en16931`), así que aquí ese redondeo no
  cambia nada; está para que una cifra que llegue sin redondear no salga con
  otro.
- **`en_castellano`**: una cifra del fichero dentro de una frase, o dentro de
  la cuenta que explica un «Debería ser». Con coma y **sin redondear**: con
  dos decimales, «100,13 (100,00 + 0,12 de cargos)» no suma, y la cuenta está
  para que se pueda rehacer a mano. Dos decimales sí como mínimo, que es como
  se lee un importe.
- **`tiene`**: la cifra del fichero en «Tiene», tal cual está escrita, con su
  punto. Es lo que se busca en el XML, y es como ya salía «Tiene» en el resto
  de avisos (la forma, BR-DEC, el anexo), que copian el texto del fichero.
  Lo único que no se conserva es lo que `Decimal` no guarda: un signo «+» o
  unos ceros a la izquierda. Y en EDIFACT con la coma como marca decimal sale
  con punto, porque el árbol que se valida ya lo trae así (`edifact._valor`).

Los miles van con punto a partir de cinco cifras, 12.345,67 y no 1.234,56,
que es lo que hace `toLocaleString("es-ES")` en la portada: las dos cosas que
lee la misma persona escriben igual. En `tiene`, nunca: el fichero no los
lleva.

Los tipos impositivos tienen su función, `tipo`, porque no son importes: van
sin ceros de adorno, 21% y no 21,00%, y con coma cuando la llevan, 6,5%.

Y tres más, del 06-10-2026. `recuento`, para lo que se cuenta sin decimales
(bytes, anclas), con los mismos miles: el banco decía «1247225 bytes».
`fecha`, para una fecha dentro de una frase: 06-08-2026, como escribe las
fechas el resto del sitio. «Publicada el 2026-08-06» es el formato del XML,
y en una frase en castellano se lee como un código. Y `momento`, la fecha con
su hora, para los sellos y las respuestas OCSP. No pasan por `fecha`
la fecha del fichero en «Tiene», que va tal cual como las cifras;
`PAQUETE.json` y los manifiestos de las anclas, que son para máquina y se
leen con `date.fromisoformat`; y los inventarios de consola, que son
columnas y en ISO se ordenan solas.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from validador.sintaxis import redondear


def _agrupar(entera: str) -> str:
    """Los miles con punto, desde cinco cifras: 1234 se queda, 12345 no."""
    if len(entera) < 5:
        return entera
    grupos = []
    while len(entera) > 3:
        grupos.insert(0, entera[-3:])
        entera = entera[:-3]
    grupos.insert(0, entera)
    return ".".join(grupos)


def _castellano(escrita: str) -> str:
    """De «-12345.678» a «-12.345,678»: la misma cifra, con las marcas de aquí."""
    signo = "-" if escrita.startswith("-") else ""
    entera, _, decimales = escrita.lstrip("-").partition(".")
    return signo + _agrupar(entera) + ("," + decimales if decimales else "")


def calculada(valor: Decimal) -> str:
    """Una cifra que ha calculado el validador: «100,13», «12.345,67»."""
    return _castellano(f"{redondear(valor):.2f}")


def en_castellano(valor: Decimal) -> str:
    """Una cifra del fichero dentro de una frase: con coma, sin redondear.

    Con dos decimales como mínimo, como se escribe un importe: un 106.0 del
    fichero sale 106,00, que es la misma cifra. Quitar no quita nunca.
    """
    if valor.as_tuple().exponent > -2:
        valor = valor.quantize(Decimal("0.01"))
    return _castellano(format(valor, "f"))


def tiene(valor: Decimal | None) -> str:
    """Una cifra del fichero en «Tiene»: como está escrita, con su punto."""
    return "(vacío)" if valor is None else format(valor, "f")


def tipo(valor: Decimal | None) -> str:
    """Un tipo impositivo, sin ceros de adorno: 21% y 6,5%."""
    if valor is None:
        return "(sin tipo)"
    normalizado = valor.normalize()
    if normalizado == normalizado.to_integral_value():
        normalizado = normalizado.quantize(Decimal(1))
    return _castellano(format(normalizado, "f")) + "%"


def recuento(cuantos: int) -> str:
    """Lo que se cuenta, con los mismos miles: «1.247.225», «4096»."""
    return _castellano(str(int(cuantos)))


def fecha(cuando: date) -> str:
    """Una fecha dentro de una frase: «06-08-2026».

    Vale también un `datetime`, del que se escribe el día: la hora, cuando
    importa, la pone quien llama (ver `sellos._cuando`).
    """
    return f"{cuando.day:02d}-{cuando.month:02d}-{cuando.year:04d}"


def momento(cuando: datetime) -> str:
    """Una fecha con su hora: «02-03-2026 a las 10:20:30 UTC».

    En UTC, que es como vienen los sellos de tiempo y las respuestas OCSP.
    Una sin zona se escribe sin ella: no se sabe de dónde es, y no se le
    pone una.
    """
    if cuando.tzinfo is None:
        return f"{fecha(cuando)} a las {cuando:%H:%M:%S}"
    cuando = cuando.astimezone(timezone.utc)
    return f"{fecha(cuando)} a las {cuando:%H:%M:%S} UTC"
