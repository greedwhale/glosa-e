# -*- coding: utf-8 -*-
"""Este validador contra las pruebas oficiales de la norma.

Por qué existe
--------------
El 13-09-2026 se descubrió que ocho reglas de IGIC e IPSI se habían publicado
como inexistentes. Lo sostenían cuatro comprobaciones que coincidían entre sí,
y coincidían porque salían todas de la misma tabla: coincidir no dice nada de
si coinciden con la norma. Faltaba una opinión que no saliera de aquí.

Existe, y es la del propio comité. `ConnectingEurope/eInvoicing-EN16931` publica
junto al esquematrón oficial **una prueba unitaria por regla**: un fragmento de
factura y la regla que tiene que saltar (`<error>`) o no saltar (`<success>`).
La copia vive en `tests/en16931-oficial/`, fijada a un commit, y de dónde sale
lo cuenta `herramientas/norma_oficial.py`.

Qué se comprueba
----------------
1. Que la copia es la que se fijó, byte a byte.
2. Que **cada una de las 223 reglas** —201 del modelo y 22 de listas de
   códigos, leídas del esquematrón y no de una lista escrita aquí— o está
   implementada o está en `PENDIENTES`. No hay tercera posibilidad, y ningún
   código `BR-` del catálogo puede no estar en la norma.
3. Que la gravedad es la de la norma: `fatal` sale como error.
4. Que en **cada caso oficial de cada regla implementada**, este validador dice
   lo mismo que la prueba. Lo que no, está en `DISCREPANCIAS`, con su motivo,
   y la lista se comprueba en los dos sentidos: una discrepancia nueva es
   rojo, y una declarada que ya no discrepa también, para que la lista no
   pueda quedarse vieja diciendo que falla lo que ya funciona.

Qué no se comprueba
-------------------
Las pruebas oficiales son casi todas de UBL: de CII hay dos ficheros. El mapa
de CII, EDIFACT y Facturae se sigue sosteniendo con las pruebas de cada
sintaxis, que montan el mismo documento de varias formas. Y quedan fuera las
756 reglas de sintaxis del esquematrón (`UBL-SR-*`, `UBL-CR-*`…), que aquí no se
han implementado ni se dice que se hayan implementado.

La medida del primer día
------------------------
Contra la v1.3.16, de las reglas implementadas con prueba oficial **coincidían
en todos los casos 49 de 90**. Las otras 41 discrepaban en
107 casos, repartidos en seis motivos que están escritos en `MOTIVOS`.
"""
from __future__ import annotations

import collections
import functools
import pathlib
import re

from lxml import etree

from herramientas.norma_oficial import huella
from validador import en16931
from validador.codigos import codigos_del_paquete

OFICIAL = pathlib.Path(__file__).resolve().parent / "en16931-oficial"

# La huella de la copia. Si alguien la rehace con otro commit, esto se pone en
# rojo y hay que cambiarla a sabiendas, junto con `PROCEDENCIA.md`.
HUELLA = "676a5829ff48871a401f0757402d687be0c47f15d3f71cf5e526168cb52bc8a3"

ISO = "{http://purl.oclc.org/dsdl/schematron}"
VEFA = "{http://difi.no/xsd/vefa/validator/1.0}"
CARPETAS = ("Invoice-unit-UBL", "CreditNote-unit-UBL", "cii")

# Las reglas de la norma que este validador todavía no comprueba. Son las que
# salen de restar el catálogo al esquematrón, escritas aquí para que la cuenta
# no dependa de nadie: una regla nueva en el catálogo tiene que salir de esta
# lista a mano, y eso obliga a mirar sus pruebas oficiales.
PENDIENTES = (
    # Campos y coherencia del modelo que todavía no se miran.
    "BR-17", "BR-18", "BR-19", "BR-20", "BR-27", "BR-28", "BR-29", "BR-30",
    "BR-31", "BR-32", "BR-33", "BR-36", "BR-37", "BR-38", "BR-41", "BR-42",
    "BR-43", "BR-44", "BR-49", "BR-50", "BR-51", "BR-52", "BR-53", "BR-54",
    "BR-55", "BR-56", "BR-57", "BR-61", "BR-62", "BR-63", "BR-64", "BR-65",
    # Condiciones que cruzan dos campos.
    "BR-CO-03", "BR-CO-04", "BR-CO-05", "BR-CO-06", "BR-CO-07", "BR-CO-08",
    "BR-CO-09", "BR-CO-19", "BR-CO-20", "BR-CO-21", "BR-CO-22", "BR-CO-23",
    "BR-CO-24", "BR-CO-26",
    # Cuántos decimales admite cada importe: dos.
    "BR-DEC-01", "BR-DEC-02", "BR-DEC-05", "BR-DEC-06", "BR-DEC-09",
    "BR-DEC-10", "BR-DEC-11", "BR-DEC-12", "BR-DEC-13", "BR-DEC-14",
    "BR-DEC-15", "BR-DEC-16", "BR-DEC-17", "BR-DEC-18", "BR-DEC-19",
    "BR-DEC-20", "BR-DEC-23", "BR-DEC-24", "BR-DEC-25", "BR-DEC-27",
    "BR-DEC-28",
    # Tipo general: el NIF del vendedor (02-04) y la cuota (09).
    "BR-S-02", "BR-S-03", "BR-S-04", "BR-S-09",
    # Tipo cero: el NIF del vendedor (02-04) y la cuota a cero (09).
    "BR-Z-02", "BR-Z-03", "BR-Z-04", "BR-Z-09",
    # Exenta: el NIF del vendedor (02-04) y la cuota a cero (09).
    "BR-E-02", "BR-E-03", "BR-E-04", "BR-E-09",
    # Inversión del sujeto pasivo: los NIF (02-04) y la cuota a cero (09).
    "BR-AE-02", "BR-AE-03", "BR-AE-04", "BR-AE-09",
    # Intracomunitaria: los NIF (02-04), la cuota (09), la fecha de entrega (11)
    # y el país de destino (12).
    "BR-IC-02", "BR-IC-03", "BR-IC-04", "BR-IC-09", "BR-IC-11", "BR-IC-12",
    # Exportación: el NIF del vendedor (02-04) y la cuota a cero (09).
    "BR-G-02", "BR-G-03", "BR-G-04", "BR-G-09",
    # No sujeta: que no haya NIF (02-04), cuota a cero (09) y que no se mezcle
    # con otras categorías (12-14).
    "BR-O-02", "BR-O-03", "BR-O-04", "BR-O-09", "BR-O-12", "BR-O-13",
    "BR-O-14",
    # IGIC: el NIF del vendedor (02-04) y la cuota (09).
    "BR-AF-02", "BR-AF-03", "BR-AF-04", "BR-AF-09",
    # IPSI: el NIF del vendedor (02-04) y la cuota (09).
    "BR-AG-02", "BR-AG-03", "BR-AG-04", "BR-AG-09",
    # El pago fraccionado italiano (split payment).
    "BR-B-01", "BR-B-02",
    # Listas de códigos.
    "BR-CL-03", "BR-CL-04", "BR-CL-05", "BR-CL-06", "BR-CL-07", "BR-CL-08",
    "BR-CL-10", "BR-CL-11", "BR-CL-13", "BR-CL-14", "BR-CL-15", "BR-CL-16",
    "BR-CL-17", "BR-CL-18", "BR-CL-19", "BR-CL-20", "BR-CL-21", "BR-CL-22",
    "BR-CL-23", "BR-CL-24", "BR-CL-25", "BR-CL-26",
)

# Por qué este validador no dice lo mismo que la prueba oficial. Cada
# discrepancia apunta a uno de estos.
MOTIVOS = {
    "perfil": (
        "BR-01 solo pide que el identificador de especificación esté. Aquí se "
        "usaba además para avisar de que no declara EN 16931, que es una "
        "opinión de la casa con el código de una regla que dice otra cosa."
    ),
    "centimo": (
        "La norma exige que la suma cuadre exacta, redondeada a dos "
        "decimales. Aquí se toleraba un céntimo, y un total que se aparta un "
        "céntimo de la suma de sus partes salía limpio."
    ),
    "centimo-y-cuenta": (
        "Lo del céntimo, y además la norma exige un único total de impuestos "
        "en la moneda del documento. Con dos, aquí se leía uno."
    ),
    "unidad": (
        "Al revés que el céntimo: la norma admite que la cuota se aparte hasta "
        "una unidad de la base por el tipo, porque el redondeo línea a línea "
        "lo produce, y aquí se exigía el céntimo. Esto rechazaba lo que la "
        "norma acepta."
    ),
    "desglose": (
        "La regla mira cada línea, descuento o cargo con su categoría, haya "
        "desglose o no y tenga importe o no, y en algunas categorías exige un "
        "desglose y solo uno. Aquí sin desglose no se miraba, se descartaban "
        "los conceptos sin importe y no se contaban los desgloses repetidos."
    ),
    "sin-desglose": (
        "Sin desglose de IVA, el módulo se paraba en BR-CO-18 y no miraba el "
        "tipo de las líneas, los descuentos y los cargos. La norma los mira "
        "igual: son defectos distintos y se dicen los dos."
    ),
}

DISCREPANCIAS: dict[str, tuple[str, tuple[str, ...]]] = {
    "BR-01": ('perfil', (
        "Invoice-unit-UBL/BR-01.xml#0:success",
        "CreditNote-unit-UBL/BR-01.xml#0:success",
    )),
    "BR-AE-01": ('desglose', (
        "Invoice-unit-UBL/BR-AE-01.xml#4:error",
        "Invoice-unit-UBL/BR-AE-01.xml#5:error",
        "Invoice-unit-UBL/BR-AE-01.xml#6:error",
        "Invoice-unit-UBL/BR-AE-01.xml#7:error",
        "Invoice-unit-UBL/BR-AE-01.xml#8:error",
    )),
    "BR-AE-05": ('sin-desglose', (
        "Invoice-unit-UBL/BR-AE-05.xml#1:error",
        "Invoice-unit-UBL/BR-AE-05.xml#2:error",
    )),
    "BR-AE-06": ('sin-desglose', (
        "Invoice-unit-UBL/BR-AE-06.xml#1:error",
        "Invoice-unit-UBL/BR-AE-06.xml#2:error",
    )),
    "BR-AE-07": ('sin-desglose', (
        "Invoice-unit-UBL/BR-AE-07.xml#1:error",
        "Invoice-unit-UBL/BR-AE-07.xml#2:error",
    )),
    "BR-AF-01": ('desglose', (
        "Invoice-unit-UBL/BR-IG-01.xml#4:error",
        "Invoice-unit-UBL/BR-IG-01.xml#5:error",
        "Invoice-unit-UBL/BR-IG-01.xml#6:error",
        "Invoice-unit-UBL/BR-IG-01.xml#7:error",
    )),
    "BR-AF-05": ('sin-desglose', (
        "Invoice-unit-UBL/BR-IG-05.xml#2:error",
    )),
    "BR-AF-06": ('sin-desglose', (
        "Invoice-unit-UBL/BR-IG-06.xml#2:error",
    )),
    "BR-AF-07": ('sin-desglose', (
        "Invoice-unit-UBL/BR-IG-07.xml#2:error",
    )),
    "BR-AG-01": ('desglose', (
        "Invoice-unit-UBL/BR-IP-01.xml#4:error",
        "Invoice-unit-UBL/BR-IP-01.xml#5:error",
        "Invoice-unit-UBL/BR-IP-01.xml#6:error",
        "Invoice-unit-UBL/BR-IP-01.xml#7:error",
    )),
    "BR-AG-05": ('sin-desglose', (
        "Invoice-unit-UBL/BR-IP-05.xml#2:error",
    )),
    "BR-AG-06": ('sin-desglose', (
        "Invoice-unit-UBL/BR-IP-06.xml#2:error",
    )),
    "BR-AG-07": ('sin-desglose', (
        "Invoice-unit-UBL/BR-IP-07.xml#2:error",
    )),
    "BR-CO-10": ('centimo', (
        "Invoice-unit-UBL/BR-CO-10.xml#7:error",
    )),
    "BR-CO-13": ('centimo', (
        "Invoice-unit-UBL/BR-CO-13.xml#10:error",
        "CreditNote-unit-UBL/BR-CO-13.xml#10:error",
    )),
    "BR-CO-15": ('centimo-y-cuenta', (
        "Invoice-unit-UBL/BR-CO-15.xml#4:error",
        "Invoice-unit-UBL/BR-CO-15.xml#6:error",
        "Invoice-unit-UBL/BR-CO-15.xml#7:error",
        "CreditNote-unit-UBL/BR-CO-15.xml#4:error",
        "CreditNote-unit-UBL/BR-CO-15.xml#6:error",
        "CreditNote-unit-UBL/BR-CO-15.xml#7:error",
        "cii/BR-CO-15-2.xml#2:error",
        "cii/BR-CO-15-2.xml#3:error",
    )),
    "BR-CO-17": ('unidad', (
        "cii/BR-CO-17.xml#1:success",
        "cii/BR-CO-17.xml#2:success",
    )),
    "BR-E-01": ('desglose', (
        "Invoice-unit-UBL/BR-E-01.xml#4:error",
        "Invoice-unit-UBL/BR-E-01.xml#5:error",
        "Invoice-unit-UBL/BR-E-01.xml#6:error",
        "Invoice-unit-UBL/BR-E-01.xml#7:error",
        "Invoice-unit-UBL/BR-E-01.xml#8:error",
        "CreditNote-unit-UBL/BR-E-01.xml#4:error",
        "CreditNote-unit-UBL/BR-E-01.xml#5:error",
        "CreditNote-unit-UBL/BR-E-01.xml#6:error",
        "CreditNote-unit-UBL/BR-E-01.xml#7:error",
        "CreditNote-unit-UBL/BR-E-01.xml#8:error",
    )),
    "BR-E-05": ('sin-desglose', (
        "Invoice-unit-UBL/BR-E-05.xml#1:error",
        "Invoice-unit-UBL/BR-E-05.xml#2:error",
    )),
    "BR-E-06": ('sin-desglose', (
        "Invoice-unit-UBL/BR-E-06.xml#1:error",
        "Invoice-unit-UBL/BR-E-06.xml#2:error",
    )),
    "BR-E-07": ('sin-desglose', (
        "Invoice-unit-UBL/BR-E-07.xml#1:error",
        "Invoice-unit-UBL/BR-E-07.xml#2:error",
    )),
    "BR-G-01": ('desglose', (
        "Invoice-unit-UBL/BR-G-01.xml#4:error",
        "Invoice-unit-UBL/BR-G-01.xml#5:error",
        "Invoice-unit-UBL/BR-G-01.xml#6:error",
        "Invoice-unit-UBL/BR-G-01.xml#7:error",
        "Invoice-unit-UBL/BR-G-01.xml#8:error",
    )),
    "BR-G-05": ('sin-desglose', (
        "Invoice-unit-UBL/BR-G-05.xml#1:error",
        "Invoice-unit-UBL/BR-G-05.xml#2:error",
    )),
    "BR-G-06": ('sin-desglose', (
        "Invoice-unit-UBL/BR-G-06.xml#1:error",
        "Invoice-unit-UBL/BR-G-06.xml#2:error",
    )),
    "BR-G-07": ('sin-desglose', (
        "Invoice-unit-UBL/BR-G-07.xml#1:error",
        "Invoice-unit-UBL/BR-G-07.xml#2:error",
    )),
    "BR-IC-01": ('desglose', (
        "Invoice-unit-UBL/BR-IC-01.xml#4:error",
        "Invoice-unit-UBL/BR-IC-01.xml#5:error",
        "Invoice-unit-UBL/BR-IC-01.xml#6:error",
        "Invoice-unit-UBL/BR-IC-01.xml#7:error",
        "Invoice-unit-UBL/BR-IC-01.xml#8:error",
    )),
    "BR-IC-05": ('sin-desglose', (
        "Invoice-unit-UBL/BR-IC-05.xml#1:error",
        "Invoice-unit-UBL/BR-IC-05.xml#2:error",
    )),
    "BR-IC-06": ('sin-desglose', (
        "Invoice-unit-UBL/BR-IC-06.xml#1:error",
        "Invoice-unit-UBL/BR-IC-06.xml#2:error",
    )),
    "BR-IC-07": ('sin-desglose', (
        "Invoice-unit-UBL/BR-IC-07.xml#1:error",
        "Invoice-unit-UBL/BR-IC-07.xml#2:error",
    )),
    "BR-O-01": ('desglose', (
        "Invoice-unit-UBL/BR-O-01.xml#4:error",
        "Invoice-unit-UBL/BR-O-01.xml#5:error",
        "Invoice-unit-UBL/BR-O-01.xml#6:error",
        "Invoice-unit-UBL/BR-O-01.xml#7:error",
        "Invoice-unit-UBL/BR-O-01.xml#8:error",
    )),
    "BR-O-05": ('sin-desglose', (
        "Invoice-unit-UBL/BR-O-05.xml#1:error",
    )),
    "BR-O-06": ('sin-desglose', (
        "Invoice-unit-UBL/BR-O-06.xml#1:error",
    )),
    "BR-O-07": ('sin-desglose', (
        "Invoice-unit-UBL/BR-O-07.xml#1:error",
    )),
    "BR-S-01": ('desglose', (
        "Invoice-unit-UBL/BR-S-01.xml#4:error",
        "Invoice-unit-UBL/BR-S-01.xml#5:error",
        "Invoice-unit-UBL/BR-S-01.xml#6:error",
        "Invoice-unit-UBL/BR-S-01.xml#7:error",
    )),
    "BR-S-05": ('sin-desglose', (
        "Invoice-unit-UBL/BR-S-05.xml#1:error",
        "Invoice-unit-UBL/BR-S-05.xml#2:error",
    )),
    "BR-S-06": ('sin-desglose', (
        "Invoice-unit-UBL/BR-S-06.xml#1:error",
        "Invoice-unit-UBL/BR-S-06.xml#2:error",
    )),
    "BR-S-07": ('sin-desglose', (
        "Invoice-unit-UBL/BR-S-07.xml#1:error",
        "Invoice-unit-UBL/BR-S-07.xml#2:error",
    )),
    "BR-Z-01": ('desglose', (
        "Invoice-unit-UBL/BR-Z-01.xml#4:error",
        "Invoice-unit-UBL/BR-Z-01.xml#5:error",
        "Invoice-unit-UBL/BR-Z-01.xml#6:error",
        "Invoice-unit-UBL/BR-Z-01.xml#7:error",
        "Invoice-unit-UBL/BR-Z-01.xml#8:error",
    )),
    "BR-Z-05": ('sin-desglose', (
        "Invoice-unit-UBL/BR-Z-05.xml#1:error",
        "Invoice-unit-UBL/BR-Z-05.xml#2:error",
    )),
    "BR-Z-06": ('sin-desglose', (
        "Invoice-unit-UBL/BR-Z-06.xml#1:error",
        "Invoice-unit-UBL/BR-Z-06.xml#2:error",
    )),
    "BR-Z-07": ('sin-desglose', (
        "Invoice-unit-UBL/BR-Z-07.xml#1:error",
        "Invoice-unit-UBL/BR-Z-07.xml#2:error",
    )),
}

# Implementadas sin ninguna prueba oficial que las provoque. Se dice, porque
# una regla sin prueba oficial solo tiene las de aquí.
SIN_PRUEBA_OFICIAL = ("BR-IC-10",)


@functools.cache
def inventario() -> dict[str, str]:
    """Las reglas de la norma, leídas del esquematrón: código y gravedad."""
    reglas: dict[str, str] = {}
    for sch in ("EN16931-model.sch", "EN16931-UBL-codes.sch"):
        raiz = etree.parse(str(OFICIAL / sch)).getroot()
        for a in raiz.iter(ISO + "assert", ISO + "report"):
            reglas[a.get("id")] = a.get("flag")
    return reglas


@functools.cache
def implementadas() -> frozenset[str]:
    return frozenset(c.codigo for c in codigos_del_paquete()) & frozenset(inventario())


@functools.cache
def casos() -> tuple[tuple[str, str, str, frozenset[str]], ...]:
    """Cada caso oficial de cada regla implementada: (caso, regla, tipo, lo que sale)."""
    salida = []
    for carpeta in CARPETAS:
        for f in sorted((OFICIAL / carpeta).glob("*.xml")):
            raiz = etree.parse(str(f)).getroot()
            for n, test in enumerate(raiz.iterfind(VEFA + "test")):
                docs = [e for e in test
                        if isinstance(e.tag, str) and not e.tag.startswith(VEFA)]
                if not docs:
                    continue
                salen = None
                for e in test.find(VEFA + "assert"):
                    tipo = etree.QName(e).localname
                    regla = (e.text or "").strip()
                    if tipo not in ("error", "warning", "success"):
                        continue
                    if regla not in implementadas():
                        continue
                    if salen is None:
                        informe = en16931.validar(etree.tostring(docs[0]))
                        salen = frozenset(i.codigo for i in informe.incidencias)
                    salida.append((f"{carpeta}/{f.name}#{n}", regla, tipo, salen))
    return tuple(salida)


def test_la_copia_oficial_es_la_que_se_fijo():
    assert huella(OFICIAL) == HUELLA, (
        "tests/en16931-oficial/ no es la copia que se fijó. Si se ha rehecho a "
        "propósito con otro commit, cambia HUELLA y mira qué reglas y casos "
        "han cambiado; si no, alguien ha tocado una prueba oficial.")


def test_la_norma_tiene_las_reglas_que_se_contaron():
    """201 en el modelo y 22 en las listas, sin repetidas entre los dos.

    Contadas por fichero y no por prefijo: el modelo trae una `BR-CL` propia,
    la 08, y contando por prefijo salían 200 y 23.
    """
    cuantas = []
    for sch in ("EN16931-model.sch", "EN16931-UBL-codes.sch"):
        raiz = etree.parse(str(OFICIAL / sch)).getroot()
        cuantas.append(len({a.get("id") for a in raiz.iter(ISO + "assert", ISO + "report")}))
    assert cuantas == [201, 22]
    assert len(inventario()) == 223


def test_cada_regla_de_la_norma_esta_hecha_o_pendiente():
    reglas = set(inventario())
    pendientes = set(PENDIENTES)
    hechas = set(implementadas())
    assert len(PENDIENTES) == len(pendientes), "hay pendientes repetidas"
    ambas = sorted(hechas & pendientes)
    assert not ambas, (
        f"implementadas y todavía en PENDIENTES: {', '.join(ambas)}. "
        "Quítalas de la lista: sus casos oficiales pasan a comprobarse.")
    ninguna = sorted(reglas - hechas - pendientes)
    assert not ninguna, (
        f"reglas de la norma que ni están hechas ni pendientes: {', '.join(ninguna)}")
    sobran = sorted(pendientes - reglas)
    assert not sobran, f"pendientes que no son de la norma: {', '.join(sobran)}"


def test_ningun_codigo_br_es_inventado():
    inventados = sorted(
        c.codigo for c in codigos_del_paquete()
        if c.codigo.startswith("BR-") and c.codigo not in inventario())
    assert not inventados, (
        f"códigos BR- que no están en el esquematrón oficial: {', '.join(inventados)}")


def test_la_gravedad_es_la_de_la_norma():
    esperada = {"fatal": "error", "warning": "aviso"}
    mal = []
    for c in codigos_del_paquete():
        flag = inventario().get(c.codigo)
        if flag and esperada[flag] not in c.gravedades:
            mal.append(f"{c.codigo} es {flag} y sale como {'/'.join(c.gravedades)}")
    assert not mal, "; ".join(mal)


def _discrepancias_medidas() -> dict[str, set[str]]:
    medidas: dict[str, set[str]] = collections.defaultdict(set)
    for caso, regla, tipo, salen in casos():
        dispara = regla in salen
        if dispara != (tipo != "success"):
            medidas[regla].add(f"{caso}:{tipo}")
    return medidas


def test_en_cada_caso_oficial_se_dice_lo_mismo_que_la_norma():
    medidas = _discrepancias_medidas()
    declaradas = {r: set(c) for r, (_, c) in DISCREPANCIAS.items()}
    nuevas = sorted(f"{r} {c}" for r, cs in medidas.items()
                    for c in cs - declaradas.get(r, set()))
    assert not nuevas, (
        f"{len(nuevas)} casos oficiales en los que este validador no dice lo "
        "mismo que la norma:\n  " + "\n  ".join(nuevas[:40]))


def test_ninguna_discrepancia_declarada_se_ha_arreglado_sin_decirlo():
    medidas = _discrepancias_medidas()
    arregladas = sorted(f"{r} {c}" for r, (_, cs) in DISCREPANCIAS.items()
                        for c in set(cs) - medidas.get(r, set()))
    assert not arregladas, (
        f"{len(arregladas)} discrepancias declaradas ya no discrepan. Quítalas "
        "de DISCREPANCIAS:\n  " + "\n  ".join(arregladas[:40]))


def test_cada_discrepancia_tiene_su_motivo():
    for regla, (motivo, casos_) in DISCREPANCIAS.items():
        assert motivo in MOTIVOS, f"{regla}: motivo «{motivo}» sin explicar"
        assert casos_, f"{regla}: declarada sin casos"


def test_toda_regla_implementada_tiene_prueba_oficial_o_se_dice():
    con_prueba = {regla for _, regla, _, _ in casos()}
    sin = sorted(set(implementadas()) - con_prueba)
    assert sin == sorted(SIN_PRUEBA_OFICIAL), (
        f"sin prueba oficial: {sin}; declaradas: {sorted(SIN_PRUEBA_OFICIAL)}")
