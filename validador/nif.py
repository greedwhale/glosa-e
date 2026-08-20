"""Validación de NIF, NIE y CIF españoles.

Todo documento identificativo que aparece en una factura lleva un dígito o una
letra de control. Comprobarlo antes de enviar evita el rechazo más tonto y más
frecuente que existe: un identificador mal tecleado.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Letra de control del NIF: se toma el resto de dividir el número entre 23.
_LETRAS_NIF = "TRWAGMYFPDXBNJZSQVHLCKE"

# Prefijos del NIE y su equivalencia numérica.
_PREFIJOS_NIE = {"X": "0", "Y": "1", "Z": "2"}

# Letras de control del CIF, indexadas por el dígito de control calculado.
_LETRAS_CIF = "JABCDEFGHI"

# Tipos de entidad cuyo control es siempre una letra.
_CIF_CONTROL_LETRA = set("KPQRSNW")
# Tipos de entidad cuyo control es siempre un dígito.
_CIF_CONTROL_DIGITO = set("ABEH")
# Tipos de entidad reconocidos. El resto admite letra o dígito indistintamente.
_CIF_TIPOS = set("ABCDEFGHJKLMNPQRSUVW")

_RE_NIF = re.compile(r"^\d{8}[A-Z]$")
_RE_NIE = re.compile(r"^[XYZ]\d{7}[A-Z]$")
_RE_CIF = re.compile(r"^[A-Z]\d{7}[0-9A-J]$")


@dataclass(frozen=True)
class Resultado:
    """Resultado de una comprobación, con el motivo escrito en castellano llano."""

    valido: bool
    tipo: str | None
    motivo: str

    def __bool__(self) -> bool:
        return self.valido


def normalizar(documento: str) -> str:
    """Quita espacios, guiones y puntos, y pasa a mayúsculas."""
    return re.sub(r"[\s\-.]", "", documento or "").upper()


def _letra_nif(numero: int) -> str:
    return _LETRAS_NIF[numero % 23]


def validar_nif(documento: str) -> Resultado:
    """Comprueba un NIF de persona física: ocho dígitos y una letra."""
    doc = normalizar(documento)
    if not _RE_NIF.match(doc):
        return Resultado(False, None, "Un NIF son ocho dígitos seguidos de una letra.")
    esperada = _letra_nif(int(doc[:8]))
    if doc[8] != esperada:
        return Resultado(
            False,
            "NIF",
            f"La letra no corresponde al número: debería terminar en {esperada}, no en {doc[8]}.",
        )
    return Resultado(True, "NIF", "NIF correcto.")


def validar_nie(documento: str) -> Resultado:
    """Comprueba un NIE de extranjero: X, Y o Z, siete dígitos y una letra."""
    doc = normalizar(documento)
    if not _RE_NIE.match(doc):
        return Resultado(
            False,
            None,
            "Un NIE empieza por X, Y o Z, y sigue con siete dígitos y una letra.",
        )
    numero = int(_PREFIJOS_NIE[doc[0]] + doc[1:8])
    esperada = _letra_nif(numero)
    if doc[8] != esperada:
        return Resultado(
            False,
            "NIE",
            f"La letra no corresponde al número: debería terminar en {esperada}, no en {doc[8]}.",
        )
    return Resultado(True, "NIE", "NIE correcto.")


def _control_cif(cuerpo: str) -> int:
    """Calcula el dígito de control de un CIF a partir de sus siete dígitos.

    Las posiciones impares contando desde uno (la 1ª, 3ª, 5ª y 7ª) se duplican
    y, si el resultado pasa de nueve, se suman sus dos cifras. Las pares se
    suman tal cual.
    """
    total = 0
    for indice, caracter in enumerate(cuerpo):
        digito = int(caracter)
        if indice % 2 == 0:  # posición impar contando desde uno
            doble = digito * 2
            total += doble - 9 if doble > 9 else doble
        else:
            total += digito
    return (10 - total % 10) % 10


def validar_cif(documento: str) -> Resultado:
    """Comprueba un CIF de persona jurídica: letra, siete dígitos y control."""
    doc = normalizar(documento)
    if not _RE_CIF.match(doc):
        return Resultado(
            False, None, "Un CIF es una letra, siete dígitos y un carácter de control."
        )
    tipo = doc[0]
    if tipo not in _CIF_TIPOS:
        return Resultado(
            False, "CIF", f"La letra {tipo} no corresponde a ningún tipo de entidad."
        )

    control_calculado = _control_cif(doc[1:8])
    control_real = doc[8]
    letra_esperada = _LETRAS_CIF[control_calculado]
    digito_esperado = str(control_calculado)

    if tipo in _CIF_CONTROL_LETRA:
        if control_real != letra_esperada:
            return Resultado(
                False,
                "CIF",
                f"Las entidades de tipo {tipo} llevan letra de control: "
                f"debería ser {letra_esperada}.",
            )
    elif tipo in _CIF_CONTROL_DIGITO:
        if control_real != digito_esperado:
            return Resultado(
                False,
                "CIF",
                f"Las entidades de tipo {tipo} llevan dígito de control: "
                f"debería ser {digito_esperado}.",
            )
    elif control_real not in (letra_esperada, digito_esperado):
        return Resultado(
            False,
            "CIF",
            f"El control no cuadra: debería ser {digito_esperado} o {letra_esperada}.",
        )
    return Resultado(True, "CIF", "CIF correcto.")


def validar(documento: str) -> Resultado:
    """Detecta el tipo de documento y lo comprueba.

    Es la función de uso habitual: no hace falta saber de antemano si lo que
    llega es un NIF, un NIE o un CIF.
    """
    doc = normalizar(documento)
    if not doc:
        return Resultado(False, None, "No se ha indicado ningún documento.")
    if _RE_NIF.match(doc):
        return validar_nif(doc)
    if _RE_NIE.match(doc):
        return validar_nie(doc)
    if _RE_CIF.match(doc):
        return validar_cif(doc)
    return Resultado(
        False, None, "El formato no corresponde a un NIF, NIE ni CIF español."
    )
