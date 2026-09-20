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

# Las tres claves de persona física que no son un DNI ni un NIE. La AEAT las
# describe en la composición del NIF: K para residentes en España menores de
# catorce años, L para españoles residentes fuera y M para extranjeros sin NIE.
# No son entidades, y por eso su control **no** es el de las personas
# jurídicas: es el mismo del DNI, el resto de dividir entre 23.
#
# Aquí estaban tratadas como tipos de entidad y el resultado era peor que un
# error: `M1234567L` —un NIF real y correcto— no llegaba siquiera a
# comprobarse, porque la expresión del CIF exige que el control esté entre 0 y
# J, y salía «el formato no corresponde a un NIF, NIE ni CIF español», o sea
# CU-01 en error sobre una factura buena.
#
# Lo que la AEAT publica es la composición —letra, siete caracteres y un
# carácter alfabético de verificación—, no el algoritmo. El del módulo 23 es el
# que cuadra con esa forma y el que usan las validaciones de siempre; y aunque
# no fuera exactamente el de la Agencia, esto solo puede mejorar lo de antes,
# que era rechazarlos todos. Se aceptan solo con siete **dígitos**: con letras
# en medio no hay nada que dividir entre 23, y lo que no se sabe comprobar no
# se da por bueno.
_CLAVES_DE_PERSONA = {
    "K": "españoles residentes en España menores de catorce años",
    "L": "españoles residentes en el extranjero",
    "M": "extranjeros sin NIE",
}

# Letras de control del CIF, indexadas por el dígito de control calculado.
_LETRAS_CIF = "JABCDEFGHI"

# Tipos de entidad cuyo control es siempre una letra. Sin la K, que es de
# persona física: ver `_CLAVES_DE_PERSONA`.
_CIF_CONTROL_LETRA = set("PQRSNW")
# Tipos de entidad cuyo control es siempre un dígito.
_CIF_CONTROL_DIGITO = set("ABEH")
# Tipos de entidad reconocidos. El resto admite letra o dígito indistintamente.
# Tampoco están K, L ni M, por lo mismo.
_CIF_TIPOS = set("ABCDEFGHJNPQRSUVW")

_RE_NIF = re.compile(r"^\d{8}[A-Z]$")
_RE_NIF_PERSONAL = re.compile(r"^[KLM]\d{7}[A-Z]$")
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


def validar_nif_personal(documento: str) -> Resultado:
    """Comprueba un NIF de persona física de los que empiezan por K, L o M.

    El control se calcula como el del DNI, sobre los siete dígitos: son
    personas, no entidades. Ver `_CLAVES_DE_PERSONA`.
    """
    doc = normalizar(documento)
    if not _RE_NIF_PERSONAL.match(doc):
        return Resultado(
            False,
            None,
            "Un NIF que empieza por K, L o M lleva siete dígitos y una letra.",
        )
    esperada = _letra_nif(int(doc[1:8]))
    if doc[8] != esperada:
        return Resultado(
            False,
            "NIF",
            f"La letra no corresponde al número: debería terminar en {esperada}, "
            f"no en {doc[8]}. Los NIF que empiezan por {doc[0]} son de "
            f"{_CLAVES_DE_PERSONA[doc[0]]} y llevan la letra del DNI.",
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
    if _RE_NIF_PERSONAL.match(doc):
        return validar_nif_personal(doc)
    if _RE_CIF.match(doc):
        return validar_cif(doc)
    return Resultado(
        False, None, "El formato no corresponde a un NIF, NIE ni CIF español."
    )
