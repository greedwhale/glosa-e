"""Escribe las listas de códigos de `validador/listas_de_codigos.py` desde la copia oficial.

Las listas se versionan escritas enteras, y no se leen de la copia al validar,
porque la copia vive en `tests/` y no viaja en la rueda: el validador que corre
en el navegador no la tiene. Así que se copian, y para que la copia no sea a
mano la hace esto:

    python -m herramientas.listas_de_codigos

Lee `tests/en16931-oficial/EN16931-UBL-codes.sch` y `EN16931-CII-codes.sch`,
elige la lista de cada regla —la de UBL, salvo la de asuntos de nota, que es la
de CII y la contiene— y reescribe lo que hay debajo de la marca en el módulo.
Si una lista que se usa en varias reglas no dice lo mismo en todas, se niega:
esa diferencia hay que mirarla, no repartirla.
"""
from __future__ import annotations

import pathlib
import re

from lxml import etree

RAIZ = pathlib.Path(__file__).resolve().parent.parent
OFICIAL = RAIZ / "tests" / "en16931-oficial"
MODULO = RAIZ / "validador" / "listas_de_codigos.py"
MARCA = "# comparadas con ella en `tests/test_norma_oficial.py`. No se editan a mano.\n"
ISO = "{http://purl.oclc.org/dsdl/schematron}"

LISTA = re.compile(r"'( [^']+ )'")
MIME = re.compile(r"@mimeCode\s*=\s*'([^']+)'")

# Qué regla da cada lista, y de qué esquematrón.
FUENTES = {
    "ISO_4217": ("UBL", ("BR-CL-03", "BR-CL-04", "BR-CL-05")),
    "UNTDID_1153": ("UBL", ("BR-CL-07",)),
    "UNCL_4451": ("CII", ("BR-CL-08",)),
    "ISO_6523": ("UBL", ("BR-CL-10", "BR-CL-11", "BR-CL-21", "BR-CL-26")),
    "UNTDID_7143": ("UBL", ("BR-CL-13",)),
    "ISO_3166": ("UBL", ("BR-CL-14", "BR-CL-15")),
    "UNCL_4461": ("UBL", ("BR-CL-16",)),
    "UNCL_5305": ("UBL", ("BR-CL-17", "BR-CL-18")),
    "UNCL_5189": ("UBL", ("BR-CL-19",)),
    "UNCL_7161": ("UBL", ("BR-CL-20",)),
    "VATEX": ("UBL", ("BR-CL-22",)),
    "UNECE_REC_20": ("UBL", ("BR-CL-23",)),
    "MIME": ("UBL", ("BR-CL-24",)),
    "EAS": ("UBL", ("BR-CL-25",)),
}


def pruebas(sintaxis: str) -> dict[str, str]:
    """La expresión de cada regla del esquematrón de códigos de una sintaxis."""
    raiz = etree.parse(str(OFICIAL / f"EN16931-{sintaxis}-codes.sch")).getroot()
    return {a.get("id"): a.get("test") for a in raiz.iter(ISO + "assert") if a.get("id")}


def codigos(prueba: str) -> frozenset[str]:
    """La lista de una expresión: la primera entre espacios, o los tipos MIME.

    BR-CL-10 trae dos —la de ISO 6523 y la de SEPA, que es su excepción— y
    la que es lista es la primera.
    """
    tipos = MIME.findall(prueba)
    if tipos:
        return frozenset(tipos)
    return frozenset(LISTA.findall(prueba)[0].split())


def listas() -> dict[str, frozenset[str]]:
    por_sintaxis = {s: pruebas(s) for s in ("UBL", "CII")}
    salida = {}
    for nombre, (sintaxis, reglas) in FUENTES.items():
        leidas = {regla: codigos(por_sintaxis[sintaxis][regla]) for regla in reglas}
        distintas = set(leidas.values())
        if len(distintas) != 1:
            raise SystemExit(f"{nombre}: las reglas {reglas} no dicen la misma lista")
        salida[nombre] = distintas.pop()
    return salida


def escribir(nombre: str, valores: frozenset[str]) -> str:
    lineas, actual = [], ""
    for valor in sorted(valores):
        if actual and len(actual) + 1 + len(valor) > 76:
            lineas.append(actual)
            actual = valor
        else:
            actual = f"{actual} {valor}" if actual else valor
    lineas.append(actual)
    cuerpo = "\n".join(lineas)
    return f'{nombre} = frozenset("""\n{cuerpo}\n""".split())  # {len(valores)}\n'


def main() -> None:
    texto = MODULO.read_text(encoding="utf-8")
    if MARCA not in texto:
        raise SystemExit(f"no está la marca en {MODULO.name}")
    cabeza = texto[: texto.index(MARCA) + len(MARCA)]
    cuerpo = "".join("\n" + escribir(n, v) for n, v in listas().items())
    MODULO.write_text(cabeza + cuerpo, encoding="utf-8")
    print(f"{MODULO.relative_to(RAIZ)}: {len(FUENTES)} listas")


if __name__ == "__main__":
    main()
