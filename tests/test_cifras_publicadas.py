# -*- coding: utf-8 -*-
"""Las cifras que `web/LEEME.md` publica, contra lo que se puede contar.

Por qué existe
--------------
`web/LEEME.md` es el documento de lo medido: dice cuántas comprobaciones corre
el navegador, cuáles son críticas y cuánto tarda cada cosa. Es el que se le
enseña a alguien que pregunta si esto funciona de verdad.

El 6 de septiembre de 2026 decía «Validar las **siete** de `ejemplos/`» y en
`ejemplos/` había diez. Y no era la única: decía veintisiete críticas cuando
eran veintiocho, treinta y siete resultados cuando eran treinta y ocho, y «las
veinte» cuando eran treinta y ocho. Ninguna de esas cifras rompía nada. Se
quedaron atrás una a una, cada vez que alguien añadió algo, y siguieron
publicadas.

Lo que las hacía invisibles no era el descuido: era que **estaban escritas en
letra**. `README.md` y `web/tesis.html` llevan guardián desde hace tiempo
—«1.147 tests, todos en verde», «159 códigos de aviso»— y esos no se quedan
atrás nunca, porque están en dígitos y hay un `re` que los busca y los compara.
Una cifra escrita «treinta y siete» no la encuentra ningún guardián, y por eso
sobrevive a todo.

Así que aquí hay dos cosas, y la segunda es la que evita que vuelva a pasar:

1. **Las cifras declaradas**, en `CIFRAS`: cada una con dónde está escrita, el
   patrón que la encuentra y cómo se mide de verdad.
2. **El cepo**: cualquier línea del documento que afirme una cantidad sobre
   algo que este repositorio sabe contar tiene que estar vigilada por alguna
   de las de arriba, o declarada en `SIN_VIGILAR` con su motivo. Escribir una
   cifra nueva sin guardián deja la suite en rojo, que es lo único que
   funciona.

Solo `web/LEEME.md`, y a propósito: es el documento cuyo trabajo entero es
publicar medidas. `README.md` y `HALLAZGOS.md` son prosa con cifras dentro y
un cepo así allí gritaría más de lo que cazaría.
"""
from __future__ import annotations

import pathlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Callable

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
LEEME = RAIZ / "web" / "LEEME.md"
BANCO = RAIZ / "web" / "prueba.py"


# --- Cómo se mide cada cosa ------------------------------------------------


def _comprobaciones_del_banco() -> int:
    return len(re.findall(r"^@comprobar\(", BANCO.read_text(encoding="utf-8"),
                          re.M))


def _criticas_del_banco() -> int:
    return len(_nombres_criticos())


def _nombres_criticos() -> list[str]:
    """Los nombres de las comprobaciones críticas, en el orden en que corren."""
    texto = BANCO.read_text(encoding="utf-8")
    salida = []
    for decorador in re.findall(r"@comprobar\((.*?)\)\s*\ndef", texto, re.S):
        if "critica=True" not in decorador:
            continue
        nombre = re.search(r'"(.*?)"', decorador, re.S).group(1)
        salida.append(re.sub(r"\s+", " ", nombre).strip())
    return salida


def _ficheros_de_ejemplos() -> int:
    return sum(1 for e in (RAIZ / "ejemplos").iterdir() if e.is_file())


@dataclass(frozen=True)
class Cifra:
    patron: str          # tiene que capturar el número en el grupo 1
    medir: Callable[[], int]
    que_es: str


CIFRAS = (
    Cifra(r"Abajo, (\d+) comprobaciones", _comprobaciones_del_banco,
          "las comprobaciones del banco"),
    Cifra(r"en verde; (\d+) están marcadas como \*\*críticas\*\*",
          _criticas_del_banco, "las comprobaciones críticas del banco"),
    Cifra(r"Validar los (\d+) de `ejemplos/`", _ficheros_de_ejemplos,
          "los ficheros de `ejemplos/`"),
    Cifra(r"el wheel y los (\d+) ejemplos", _ficheros_de_ejemplos,
          "los ejemplos que se bajan al arrancar"),
    Cifra(r"Los (\d+) resultados coinciden", _comprobaciones_del_banco,
          "los resultados del banco comparados con Python nativo"),
    Cifra(r"No basta con que las (\d+) salgan verdes",
          _comprobaciones_del_banco, "las comprobaciones del banco"),
)


@pytest.mark.parametrize("cifra", CIFRAS, ids=lambda c: c.que_es)
def test_la_cifra_publicada_es_la_de_hoy(cifra: Cifra):
    texto = LEEME.read_text(encoding="utf-8")
    encontrados = re.findall(cifra.patron, texto)
    assert len(encontrados) == 1, (
        f"«{cifra.patron}» aparece {len(encontrados)} veces en "
        f"{LEEME.name} y tiene que aparecer una. Si se ha reescrito la frase, "
        "este guardián se ha quedado ciego y hay que volver a apuntarlo.")
    dice, hay = int(encontrados[0]), cifra.medir()
    assert dice == hay, (
        f"{LEEME.name} dice {dice} y {cifra.que_es} son {hay}. No es un fallo "
        f"de código: es una cifra que se quedó atrás. Cámbiala a {hay}.")


# --- La tabla de las críticas, atada al banco por los dos lados ------------


def _sin_tildes(texto: str) -> str:
    plano = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in plano if unicodedata.category(c) != "Mn")


def _filas_de_la_tabla() -> list[str]:
    bloque = re.search(
        r"\| Comprobación \| Por qué es crítica \|\n\|---\|---\|\n((?:\|.*\n)+)",
        LEEME.read_text(encoding="utf-8"))
    assert bloque, "la tabla de comprobaciones críticas ya no está donde estaba"
    return [f.split("|")[1].strip() for f in bloque.group(1).strip().splitlines()]


def test_la_tabla_lista_todas_las_criticas():
    """Seis críticas vivieron meses fuera de esta tabla sin que nadie lo notara.

    Y entre ellas estaban las dos que sostienen la validación de forma —los
    esquemas que viajan con la página y el que compila sin red—, que son
    justamente las que fallarían solo en producción.
    """
    en_la_tabla = {_sin_tildes(f) for f in _filas_de_la_tabla()}
    faltan = [n for n in _nombres_criticos() if _sin_tildes(n) not in en_la_tabla]
    assert not faltan, (
        "estas comprobaciones críticas del banco no salen en la tabla de "
        f"«Qué mirar» de {LEEME.name}:\n  - " + "\n  - ".join(faltan)
        + "\nQuien lee esa tabla cree que ahí está todo lo que puede tumbar "
          "la idea. Añádelas con su porqué.")


def test_la_tabla_no_lista_nada_que_el_banco_no_corra():
    """Una fila sin comprobación detrás es peor que una comprobación sin fila.

    La comprobación sin fila deja a alguien sin enterarse de que se mira algo.
    La fila sin comprobación le dice que se mira algo que no se mira.
    """
    criticas = {_sin_tildes(n) for n in _nombres_criticos()}
    sobran = [f for f in _filas_de_la_tabla() if _sin_tildes(f) not in criticas]
    assert not sobran, (
        "estas filas de la tabla no corresponden a ninguna comprobación "
        f"crítica del banco: {sobran}. O se ha renombrado en `prueba.py` y "
        "aquí no, o promete algo que no se comprueba.")


# --- El cepo: ninguna cantidad sin quien la mida ---------------------------

# Números escritos en letra. `un`, `uno` y `una` no están: son artículos, y
# meterlos convertiría el cepo en ruido —«una factura», «una lista»— hasta que
# alguien lo apagara. Una cifra de una unidad tampoco es de las que se quedan
# atrás.
PALABRAS = (
    "dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce "
    "quince dieciseis dieciséis diecisiete dieciocho diecinueve veinte "
    "veintiuna veintiuno veintidos veintidós veintitres veintitrés "
    "veinticuatro veinticinco veintiseis veintiséis veintisiete veintiocho "
    "veintinueve treinta cuarenta cincuenta sesenta setenta ochenta noventa "
    "cien ciento"
).split()

# Un entero suelto o un número en letra —«treinta y ocho»—. Los decimales
# quedan fuera: `3,2 ms` y `14,71 MB` son medidas de tiempo y de tamaño, no
# cuentas de cosas, y las vigila el ritual de despliegue midiéndolas otra vez.
CANTIDAD = (r"(?:(?<![\d.,])\d+(?![.,]\d)|(?:" + "|".join(PALABRAS)
            + r")(?:\s+y\s+\w+)?)")

# Las cosas que este repositorio sabe contar. Si aparecen justo detrás de una
# cantidad, esa cantidad es comprobable y tiene que estar comprobada.
CONTABLES = (
    r"comprobaciones|cr[ií]ticas|c[oó]digos|pruebas|tests|esquemas|anclas|"
    r"resultados|m[oó]dulos|reglas|formatos|incidencias|ejemplos|autoridades"
)

# Hasta dos palabras entre la cantidad y la cosa: «los 10 de `ejemplos/`»,
# «cuatro reglas», «31 están marcadas como críticas».
CEPO = re.compile(
    r"(?i)\b" + CANTIDAD + r"\b(?:\s+\S+){0,2}\s+`?(?:" + CONTABLES + r")\b")

# Cantidades que se publican y que ningún guardián puede medir, con su motivo.
# Escribirlo aquí cuesta, y ese es el precio: lo que no se puede medir se dice
# en voz alta en vez de colarse.
SIN_VIGILAR: dict[str, str] = {
    "esa comprobación salió **en verde** diciendo «los 17 módulos» sin `edifact`":
        "es la cita textual de lo que dijo el banco aquel día, no una cifra de "
        "hoy: corregirla sería falsear el relato del fallo",
    "entre ellos; el fallo apareció cinco pruebas más abajo como un `ImportError`.":
        "cuenta un fallo concreto de agosto de 2026, no el estado de nada",
    "| una autoridad retirada solo vale para lo de antes | si la ventana no se "
    "aplica, 135 autoridades caducadas pasan a ser de confianza |":
        "sale de la lista de confianza del Estado, que no está en el "
        "repositorio: se midió una vez sobre la TSL de agosto de 2026",
    "| las anclas de sellado van aparte de las de firma | juntas, 11 "
    "autoridades pasarían a avalar firmas de facturas |":
        "lo mismo: es una cuenta sobre el contenido de la TSL, no sobre el "
        "código",
    "Cuatro reglas de tres módulos distintos cazándola a la vez, dentro de":
        "describe el informe concreto que se enseña justo debajo, y ese "
        "informe está pegado entero: la cifra se comprueba leyéndolo",
}


def _lineas_con_cantidad_de_algo_contable() -> list[tuple[int, str]]:
    return [(n, l) for n, l in
            enumerate(LEEME.read_text(encoding="utf-8").splitlines(), 1)
            if CEPO.search(l)]


def test_toda_cantidad_publicada_tiene_quien_la_mida():
    """El guardián del guardián: una cifra nueva sin vigilancia sale en rojo.

    Es lo que faltaba. Las cinco cifras que se quedaron atrás en `LEEME.md` no
    estaban mal comprobadas: no las comprobaba nadie, y nada decía que no las
    comprobara nadie.
    """
    patrones = [re.compile(c.patron) for c in CIFRAS]
    huerfanas = [
        (numero, linea) for numero, linea in _lineas_con_cantidad_de_algo_contable()
        if not any(p.search(linea) for p in patrones)
        and linea.strip() not in SIN_VIGILAR
    ]
    assert not huerfanas, (
        "estas líneas de `web/LEEME.md` afirman una cantidad sobre algo que "
        "este repositorio sabe contar, y no la comprueba nadie:\n"
        + "\n".join(f"  {n}: {l.strip()[:100]}" for n, l in huerfanas)
        + "\n\nHay dos salidas y las dos son buenas: añadirla a `CIFRAS` con "
          "su forma de medirla, o a `SIN_VIGILAR` con el motivo por el que no "
          "se puede medir. Lo que no vale es publicarla y confiar en que "
          "alguien se acuerde.")


def test_ninguna_excepcion_declarada_ha_dejado_de_existir():
    """Si una excepción se queda sin su línea, sobra: que no se acumulen."""
    texto = LEEME.read_text(encoding="utf-8")
    fantasmas = [l for l in SIN_VIGILAR if l not in texto]
    assert not fantasmas, (
        "estas líneas están declaradas en `SIN_VIGILAR` y ya no están en el "
        f"documento: {fantasmas}. Quítalas, o la lista de excepciones acaba "
        "siendo más larga que lo que vigila.")


def test_las_cifras_del_documento_van_en_digitos():
    """Lo que hizo invisible al fallo, dicho como norma.

    `«treinta y siete resultados»` no lo encuentra ningún `re`. Este documento
    publica medidas: sus cantidades se escriben con cifras para que se puedan
    comparar con la realidad, y no como prosa.
    """
    en_letra = [
        (n, l) for n, l in _lineas_con_cantidad_de_algo_contable()
        if re.search(r"(?i)\b(?:" + "|".join(PALABRAS) + r")\b", l)
        and l.strip() not in SIN_VIGILAR
    ]
    assert not en_letra, (
        "estas cantidades van escritas en letra:\n"
        + "\n".join(f"  {n}: {l.strip()[:100]}" for n, l in en_letra)
        + "\n\nEn dígitos, que es lo que un guardián puede leer. Una cifra en "
          "letra sobrevive a todos los cambios porque nadie la encuentra.")
