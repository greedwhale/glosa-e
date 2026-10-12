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
   implementada, o está en `PENDIENTES`, o está en `NO_EVALUABLES` porque las
   tres vinculaciones oficiales la dejan en `true()`. No hay cuarta
   posibilidad, y ningún código `BR-` del catálogo puede no estar en la norma.
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

import pytest
from lxml import etree

from herramientas.norma_oficial import huella
from validador import en16931, iva, listas_de_codigos, modelo
from validador.codigos import codigos_del_paquete
from validador.sintaxis import (
    SINTAXIS_CII,
    SINTAXIS_EDIFACT,
    SINTAXIS_FACTURAE,
    SINTAXIS_UBL,
)

OFICIAL = pathlib.Path(__file__).resolve().parent / "en16931-oficial"

# La huella de la copia. Si alguien la rehace con otro commit, esto se pone en
# rojo y hay que cambiarla a sabiendas, junto con `PROCEDENCIA.md`.
HUELLA = "78001153d1161ba4e003c4bd5e9f9d52030a71b9c4afb78fbe00b293a52e4226"

ISO = "{http://purl.oclc.org/dsdl/schematron}"
VEFA = "{http://difi.no/xsd/vefa/validator/1.0}"
CARPETAS = ("Invoice-unit-UBL", "CreditNote-unit-UBL", "cii")

# Las reglas de la norma que este validador todavía no comprueba. Son las que
# salen de restar el catálogo al esquematrón, escritas aquí para que la cuenta
# no dependa de nadie: una regla nueva en el catálogo tiene que salir de esta
# lista a mano, y eso obliga a mirar sus pruebas oficiales.
PENDIENTES: tuple[str, ...] = ()

# Las reglas que ningún validador puede comprobar, y que por eso no se hacen.
# Piden que el código del motivo de un descuento o de un cargo y el motivo
# escrito «indiquen lo mismo»: que el 95 vaya con «descuento» y no con
# «transporte». Eso es leer y entender una frase en cualquier idioma, y las tres
# vinculaciones oficiales las escriben como `true()`, que se cumple siempre. Una
# prueba lo comprueba abajo: si el comité les pone una expresión, se pone en
# rojo y hay que hacerlas.
NO_EVALUABLES = ("BR-CO-05", "BR-CO-06", "BR-CO-07", "BR-CO-08")

# Por qué este validador no dijo lo mismo que la prueba oficial el primer
# día. Cada discrepancia tiene que apuntar a uno de estos.
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

# Los casos oficiales en los que este validador no dice lo mismo que la
# norma. El primer día fueron 107, en 41 reglas y por los seis motivos de
# arriba; se arreglaron todos en la tanda siguiente y la lista quedó vacía.
# Vacía no quiere decir inútil: una discrepancia nueva tiene que entrar aquí
# con su motivo, a la vista, o la suite se pone en rojo.
DISCREPANCIAS: dict[str, tuple[str, tuple[str, ...]]] = {}

# Implementadas sin ninguna prueba oficial que las provoque. Se dice, porque
# una regla sin prueba oficial solo tiene las de aquí.
SIN_PRUEBA_OFICIAL = (
    "BR-IC-10",
    # Las de decimales: ni una. Sus pruebas están en `test_decimales.py`, en
    # las cuatro sintaxis.
    "BR-DEC-01", "BR-DEC-02", "BR-DEC-05", "BR-DEC-06", "BR-DEC-09",
    "BR-DEC-10", "BR-DEC-11", "BR-DEC-12", "BR-DEC-13", "BR-DEC-14",
    "BR-DEC-15", "BR-DEC-16", "BR-DEC-17", "BR-DEC-18", "BR-DEC-19",
    "BR-DEC-20", "BR-DEC-23", "BR-DEC-24", "BR-DEC-25", "BR-DEC-27",
    "BR-DEC-28",
    # Cuatro de las listas de códigos: el asunto de la nota, el motivo de la
    # exención, el esquema de la dirección electrónica y el del lugar de
    # entrega. Sus pruebas, en `test_listas_de_codigos.py`.
    "BR-CL-08", "BR-CL-22", "BR-CL-25", "BR-CL-26",
    # El pago fraccionado italiano. Sus pruebas, en `test_modelo.py`.
    "BR-B-01", "BR-B-02",
)


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
    pendientes = set(PENDIENTES) | set(NO_EVALUABLES)
    hechas = set(implementadas())
    assert len(PENDIENTES) == len(set(PENDIENTES)), "hay pendientes repetidas"
    assert not set(PENDIENTES) & set(NO_EVALUABLES)
    ambas = sorted(hechas & pendientes)
    assert not ambas, (
        f"implementadas y todavía en PENDIENTES o NO_EVALUABLES: {', '.join(ambas)}. "
        "Quítalas de la lista: sus casos oficiales pasan a comprobarse.")
    ninguna = sorted(reglas - hechas - pendientes)
    assert not ninguna, (
        f"reglas de la norma que ni están hechas ni pendientes: {', '.join(ninguna)}")
    sobran = sorted(pendientes - reglas)
    assert not sobran, f"pendientes que no son de la norma: {', '.join(sobran)}"


def test_las_no_evaluables_son_true_en_las_tres_vinculaciones():
    for sintaxis in ("UBL", "CII", "EDIFACT"):
        for regla in NO_EVALUABLES:
            assert vinculacion(sintaxis)[regla].strip() == "true()", (sintaxis, regla)


def test_de_las_no_evaluables_no_hay_prueba_oficial_que_contradiga():
    """Si el comité añade una prueba que las haga saltar, no se pueden seguir
    dando por imposibles."""
    for carpeta in CARPETAS:
        for f in (OFICIAL / carpeta).glob("*.xml"):
            texto = f.read_text(encoding="utf-8")
            assert not any(f">{r}<" in texto for r in NO_EVALUABLES), f.name


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


# --- Lo que no está en las pruebas: el margen de cada sintaxis ----------------
#
# Las pruebas unitarias oficiales no prueban el borde de BR-{X}-08, y el de
# BR-CO-17 solo en un punto. El margen está escrito en otro sitio: en la
# expresión de cada regla dentro de la vinculación de cada sintaxis, que no
# dice lo mismo en UBL que en CII. Hasta el 14-09-2026 eso se leía a mano y se
# copiaba a `sintaxis.py`; ahora se lee de la copia oficial, y si el comité lo
# cambia en otro commit esto se pone en rojo.

# «- 1 <» o «- 1 <=»: la cifra declarada, menos una unidad, contra la
# calculada. Sin esa forma la comparación es exacta. El paréntesis opcional es
# el de UBL, que escribe `xs:decimal(cbc:TaxableAmount - 1) < (…)`.
MARGEN = re.compile(r"-\s*1\s*\)?\s*(<=|<)")

# El código de cada familia de reglas y la categoría UNCL5305 que comprueba.
# Coinciden salvo tres: IC es K, AF es L y AG es M.
FAMILIAS = {"S": "S", "Z": "Z", "E": "E", "AE": "AE", "IC": "K", "G": "G",
            "O": "O", "AF": "L", "AG": "M"}


@functools.cache
def vinculacion(sintaxis: str) -> dict[str, str]:
    """Las expresiones de la vinculación oficial de una sintaxis, por nombre."""
    raiz = etree.parse(str(OFICIAL / f"EN16931-{sintaxis}-model.sch")).getroot()
    # Los nombres llevan a veces un espacio detrás («VAT_breakdown »).
    return {p.get("name").strip(): p.get("value") for p in raiz.iter(ISO + "param")}


def margen(sintaxis: str, regla: str) -> str:
    """«exacta», «<» (menos de una unidad) o «<=» (hasta una unidad)."""
    encontrados = set(MARGEN.findall(vinculacion(sintaxis)[regla]))
    assert len(encontrados) <= 1, f"{sintaxis} {regla}: márgenes mezclados {encontrados}"
    return encontrados.pop() if encontrados else "exacta"


def _con_margen(sintaxis: str) -> set[str]:
    salen = {familia: margen(sintaxis, f"BR-{familia}-08") for familia in FAMILIAS}
    assert set(salen.values()) <= {"exacta", "<"}, (
        f"{sintaxis}: un BR-{{X}}-08 con «<=», que aquí no está previsto: {salen}")
    return {FAMILIAS[f] for f, m in salen.items() if m == "<"}


def test_la_base_lleva_el_margen_del_esquematron_de_ubl():
    """S, L y M con menos de una unidad; las otras seis, exactas."""
    assert _con_margen("UBL") == set(SINTAXIS_UBL.base_admite_una_unidad)


def test_la_base_lleva_el_margen_del_esquematron_de_cii():
    """Al revés que UBL: Z, E, AE, K y G con margen; S, L, M y O, exactas."""
    assert _con_margen("CII") == set(SINTAXIS_CII.base_admite_una_unidad)


def test_la_cuota_lleva_el_borde_del_esquematron_de_cada_sintaxis():
    assert margen("UBL", "BR-CO-17") == "<"
    assert margen("CII", "BR-CO-17") == "<="
    assert SINTAXIS_UBL.cuota_admite_la_unidad_justa is False
    assert SINTAXIS_CII.cuota_admite_la_unidad_justa is True


def test_edifact_y_facturae_siguen_a_ubl_y_no_al_esquematron_de_edifact():
    """Una decisión, y se prueba que sigue teniendo el motivo que la sostiene.

    El esquematrón oficial de EDIFACT compara **todo exacto**, BR-CO-17
    incluida, y su último cambio de contenido es de febrero de 2017: lo que
    vino después fueron cabeceras de licencia. Los márgenes de UBL y CII son
    de después, y son los que se mantienen. Seguir al de EDIFACT sería volver a
    rechazar lo que la norma ya acepta, que es lo que se arregló el 13-09-2026.
    Facturae no tiene esquematrón europeo. Si un commit nuevo pone márgenes en
    el de EDIFACT, esto se pone en rojo y hay que volver a decidir.
    """
    assert _con_margen("EDIFACT") == set()
    assert margen("EDIFACT", "BR-CO-17") == "exacta"
    # Y rechaza el cero del IGIC y del IPSI, que la norma admite: tampoco se
    # sigue, ni se avisa, como no se avisa de sus márgenes.
    assert _rechazan_el_cero("EDIFACT") == {"S", "O", "L", "M"}
    for mapa in (SINTAXIS_EDIFACT, SINTAXIS_FACTURAE):
        assert mapa.base_admite_una_unidad == SINTAXIS_UBL.base_admite_una_unidad
        assert mapa.cuota_admite_la_unidad_justa == SINTAXIS_UBL.cuota_admite_la_unidad_justa
        assert mapa.cero_que_rechaza_su_esquematron == SINTAXIS_UBL.cero_que_rechaza_su_esquematron


def test_el_desglose_de_edifact_es_el_grupo_del_esquematron_oficial():
    """El grupo 54, filtrado por función 7 y tipo VAT, con las mismas palabras.

    En el árbol de aquí los grupos no llevan número —se llaman por el segmento
    que los abre—, así que el «54» se escribe como lo que es: el grupo de
    impuesto que cuelga de la raíz después del UNS. El filtro sí se copia tal
    cual, y se compara letra a letra.
    """
    oficial = vinculacion("EDIFACT")["VAT_breakdown"]
    grupo = "/M_INVOIC/G_SG54"
    assert oficial.startswith(grupo + "[")
    filtro = oficial[len(grupo):]
    assert SINTAXIS_EDIFACT.desglose == "./*[S_TAX][preceding-sibling::S_UNS]" + filtro


def test_sin_tipo_saltan_las_del_tipo_salvo_en_la_no_sujeta():
    """BR-{X}-05, 06 y 07 sobre un concepto sin tipo, con el texto de cada vinculación.

    Las pruebas unitarias oficiales no montan ningún concepto sin tipo: todas
    traen el tipo, bueno o malo. Lo que la norma hace sin él está en la
    expresión, que en las tres vinculaciones es una comparación con el tipo, y
    en XPath una comparación con nada es falsa: la regla salta. Menos en la O,
    que pide `not(...)`. Aquí se evalúa cada expresión tal cual, con lxml,
    sobre un concepto vacío, y se compara con lo que dice el motor.

    lxml habla XPath 1 y no conoce `xs:decimal`, que se cambia por `number`:
    con el tipo ausente las dos dan una comparación falsa (`number` de nada es
    NaN, que no es igual a nada). Es la única traducción.

    Hasta el 11-10-2026 el motor se callaba: «que el tipo falte lo dice BR-48»,
    que es del desglose. Si el comité reescribe alguna para admitir el tipo
    ausente, esto se pone en rojo y hay que volver a decidir.
    """
    espacios = {"cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                "ram": "urn:un:unece:uncefact:data:standard:"
                       "ReusableAggregateBusinessInformationEntity:100"}
    vacio = etree.fromstring("<concepto/>")
    distintos = []
    for sintaxis in ("UBL", "CII", "EDIFACT"):
        for familia, categoria in FAMILIAS.items():
            for sufijo in ("05", "06", "07"):
                regla = f"BR-{familia}-{sufijo}"
                expresion = vinculacion(sintaxis)[regla].replace("xs:decimal(", "number(")
                salta = not vacio.xpath(expresion, namespaces=espacios)
                apunte = iva.Apunte("concepto", None, categoria, None,
                                    es_ajuste=sufijo != "05", es_cargo=sufijo == "07")
                dice = regla in {i.codigo for i in iva._regla_tipo_de_los_conceptos([apunte])}
                assert salta == (familia != "O"), (sintaxis, regla, expresion)
                if dice != salta:
                    distintos.append(f"{sintaxis} {regla}")
    assert not distintos, "sin tipo, el motor no dice lo que la norma: " + ", ".join(distintos)


def _rechazan_el_cero(sintaxis: str) -> set[str]:
    """Las categorías cuyo BR-{X}-05 a 07 salta, en esta vinculación, con un 0 escrito."""
    espacios = {"cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
                "ram": "urn:un:unece:uncefact:data:standard:"
                       "ReusableAggregateBusinessInformationEntity:100"}
    con_cero = etree.fromstring(
        f'<c xmlns:cbc="{espacios["cbc"]}" xmlns:ram="{espacios["ram"]}">'
        "<cbc:Percent>0</cbc:Percent><ram:RateApplicablePercent>0</ram:RateApplicablePercent>"
        "<C_C243><D_5278>0</D_5278></C_C243></c>")
    rechazan = set()
    for familia, categoria in FAMILIAS.items():
        saltan = {not con_cero.xpath(vinculacion(sintaxis)[f"BR-{familia}-{s}"]
                                     .replace("xs:decimal(", "number("), namespaces=espacios)
                  for s in ("05", "06", "07")}
        assert len(saltan) == 1, f"{sintaxis} BR-{familia}: el cero no vale igual en las tres"
        if saltan.pop():
            rechazan.add(categoria)
    return rechazan


def test_el_cero_que_la_norma_admite_y_cada_esquematron_rechaza():
    """BR-AF y BR-AG, 05 a 07: el texto admite el cero, y el esquematrón de CII no.

    El texto de la regla dice «0 (zero) or greater than zero» en el IGIC y en
    el IPSI. La vinculación de UBL lo escribe `>= 0`; la de CII, `> 0` en el
    IGIC y `>= 0` en el IPSI. Se denunció en el repositorio oficial (issue
    519, abierta el 07-09-2026) y se cerró el 29-09-2026 cambiando el nombre de
    las reglas y no la comparación: así seguía en `master` el 12-10-2026. Aquí
    se sigue al texto, y `sintaxis.py` dice en qué categorías el esquematrón de
    cada sintaxis rechaza lo que la norma admite, para que el motor lo diga en
    una nota. Si el comité arregla CII, o rompe UBL, esto se pone en rojo.
    """
    texto = {a.get("id"): "".join(a.itertext())
             for a in etree.parse(str(OFICIAL / "EN16931-model.sch")).getroot().iter(ISO + "assert")}
    for familia in ("AF", "AG"):
        for sufijo in ("05", "06", "07"):
            assert "shall be 0 (zero) or greater than zero" in texto[f"BR-{familia}-{sufijo}"]
    # Las demás piden lo mismo en el texto y en las dos vinculaciones: el cero
    # en Z, E, AE, K y G, ningún tipo en la O y uno positivo en la S.
    assert _rechazan_el_cero("UBL") == {"S", "O"}
    assert _rechazan_el_cero("CII") == {"S", "O", "L"}
    assert SINTAXIS_UBL.cero_que_rechaza_su_esquematron == frozenset()
    assert SINTAXIS_CII.cero_que_rechaza_su_esquematron == frozenset(
        _rechazan_el_cero("CII") - _rechazan_el_cero("UBL"))


def test_la_cuota_de_cada_categoria_es_la_de_su_esquematron():
    """BR-{X}-09: cero exacto en seis categorías, y base por tipo en tres.

    Las seis de tipo cero comparan con `= 0`, sin margen, en UBL y en CII. Las
    tres de tipo positivo repiten la cuenta de BR-CO-17 con menos de una unidad
    de margen, pero no en todas partes: el esquematrón de CII da BR-AF-09 y
    BR-AG-09 por duplicadas de BR-CO-17 y las deja en `true()`. Lo que
    `sintaxis.py` dice de eso se lee de aquí.
    """
    for sintaxis, mapa in (("UBL", SINTAXIS_UBL), ("CII", SINTAXIS_CII)):
        for familia in ("Z", "E", "AE", "IC", "G", "O"):
            regla = f"BR-{familia}-09"
            assert margen(sintaxis, regla) == "exacta", (sintaxis, regla)
            assert re.search(r"=\s*0\s*$", vinculacion(sintaxis)[regla]), (sintaxis, regla)
        activas = set()
        for familia in ("S", "AF", "AG"):
            expresion = vinculacion(sintaxis)[f"BR-{familia}-09"].strip()
            if expresion == "true()":
                continue
            assert margen(sintaxis, f"BR-{familia}-09") == "<", (sintaxis, familia)
            activas.add(FAMILIAS[familia])
        assert activas == set(mapa.comprueba_la_cuota_por_tipo), sintaxis
    for mapa in (SINTAXIS_EDIFACT, SINTAXIS_FACTURAE):
        assert mapa.comprueba_la_cuota_por_tipo == SINTAXIS_UBL.comprueba_la_cuota_por_tipo


# Cómo nombra la vinculación de UBL a cada identificador fiscal, sin espacios.
# «vendedor_cualquiera» es el `PartyTaxScheme` del vendedor sin filtrar por
# esquema: BT-31 o BT-32, lo que haya.
_IVA_UBL = "[cac:TaxScheme/(normalize-space(upper-case(cbc:ID))='VAT')]/cbc:CompanyID"
_IDENTIFICADORES_UBL = {
    "vendedor_cualquiera": "cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID",
    "vendedor_nif": "cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme" + _IVA_UBL,
    "representante_nif": "cac:TaxRepresentativeParty/cac:PartyTaxScheme" + _IVA_UBL,
    "comprador_nif": "cac:AccountingCustomerParty/cac:Party/cac:PartyTaxScheme" + _IVA_UBL,
    "comprador_registro": "cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:CompanyID",
}


def test_los_identificadores_de_cada_categoria_son_los_de_la_vinculacion():
    """BR-{X}-02 a 04: la tabla de `iva.py` contra el texto de cada regla.

    Qué identificadores nombra cada una, y si los nombra para exigirlos o
    —en la no sujeta— para prohibirlos. Las pruebas oficiales ya lo comprueban
    caso a caso; esto comprueba que la tabla no dice de más ni de menos en los
    casos que las pruebas no montan.
    """
    for familia, categoria in FAMILIAS.items():
        exigidos: set[str] = set()
        for _, campos, _ in iva.IDENTIFICADORES_EXIGIDOS.get(categoria, ()):
            campos = set(campos)
            if "vendedor_registro_fiscal" in campos:
                campos -= {"vendedor_nif", "vendedor_registro_fiscal"}
                campos.add("vendedor_cualquiera")
            exigidos |= campos
        prohibidos = set(iva.IDENTIFICADORES_PROHIBIDOS.get(categoria, ()))
        for cifra in "234":
            regla = f"BR-{familia}-0{cifra}"
            texto = re.sub(r"\s+", "", vinculacion("UBL")[regla])
            nombrados = {k for k, v in _IDENTIFICADORES_UBL.items() if v in texto}
            negados = {k for k, v in _IDENTIFICADORES_UBL.items() if "not(//" + v in texto}
            assert nombrados == exigidos | prohibidos, (regla, nombrados)
            assert negados == prohibidos, (regla, negados)



# --- Las reglas de grupo: lo que no se ve en los casos ------------------------


def test_los_prefijos_del_iva_son_los_de_la_vinculacion_de_ubl():
    """BR-CO-09: la lista de `modelo.py`, código a código, contra la oficial.

    La de CII no es la misma —trae AN y le falta SS— y por eso se dice cuál se
    sigue. Si el comité cambia la de UBL, esto se pone en rojo.
    """
    listas = re.findall(r"'( [^']+ )'", vinculacion("UBL")["BR-CO-09"])
    assert len(listas) == 1
    assert modelo.PREFIJOS_IVA == frozenset(listas[0].split())
    cii = frozenset(re.findall(r"'( [^']+ )'", vinculacion("CII")["BR-CO-09"])[0].split())
    assert modelo.PREFIJOS_IVA ^ cii == {"AN", "SS"}


def test_la_transferencia_es_la_que_nombra_cada_vinculacion():
    """BR-50 y BR-61 piden la cuenta con los medios 30 y 58, en UBL y en CII.

    El esquematrón de EDIFACT escribe 30 y 57 sobre un elemento que no existe
    —`D_D4461`, con la D repetida—, así que no filtra nada y no se sigue:
    EDIFACT va con UBL, como en los márgenes.
    """
    ubl = set(re.findall(r"PaymentMeansCode\)\s*=\s*'(\d+)'", vinculacion("UBL")["BR-61"]))
    cii = set(re.findall(r"TypeCode='(\d+)'", vinculacion("CII")["CreditTransfer_information"]))
    assert ubl == set(SINTAXIS_UBL.medios_de_transferencia) == {"30", "58"}
    assert cii == set(SINTAXIS_CII.medios_de_transferencia)
    assert "D_D4461" in vinculacion("EDIFACT")["CreditTransfer_information"]
    assert SINTAXIS_EDIFACT.medios_de_transferencia == SINTAXIS_UBL.medios_de_transferencia


# Las que la norma escribió dos veces: (la de BR-CO, la otra).
REPETIDAS = (("BR-CO-21", "BR-33"), ("BR-CO-22", "BR-38"), ("BR-CO-23", "BR-42"),
             ("BR-CO-24", "BR-44"))


def test_las_repetidas_son_la_misma_regla_en_la_vinculacion_y_aqui():
    """Salen las dos porque el oficial las da las dos, y eso solo se sostiene
    si de verdad dicen lo mismo: misma expresión en UBL y en CII, y misma fila
    en `modelo.py` salvo el código y la frase que lo cuenta."""
    filas = {fila[0]: fila for fila in modelo._GRUPOS}
    for co, otra in REPETIDAS:
        for sintaxis in ("UBL", "CII"):
            assert vinculacion(sintaxis)[co].split() == vinculacion(sintaxis)[otra].split(), (
                sintaxis, co)
        assert filas[co][1:6] == filas[otra][1:6], co
        assert otra in filas[co][6], f"la explicación de {co} no dice que es {otra}"


# --- Los decimales: lo escrito o el valor ----------------------------------------
#
# «Dos decimales como mucho» se lee de dos formas en las vinculaciones: contando
# los caracteres detrás del punto o redondeando y comparando. Cuál usa cada
# regla en cada sintaxis está en `Sintaxis.decimales_por_valor`, y se lee de
# aquí. Facturae no tiene vinculación y se decide en `sintaxis.py`.

CUENTA_LO_ESCRITO = re.compile(r"string-length\(substring-after\(")
MIRA_EL_VALOR = re.compile(r"round\(\s*\.\s*\*\s*100\s*\)\s*div\s*100")


@pytest.mark.parametrize("nombre, sintaxis", [
    ("UBL", SINTAXIS_UBL), ("CII", SINTAXIS_CII), ("EDIFACT", SINTAXIS_EDIFACT),
], ids=["UBL", "CII", "EDIFACT"])
def test_los_decimales_se_cuentan_como_en_cada_vinculacion(nombre, sintaxis):
    expresiones = {r: e for r, e in vinculacion(nombre).items() if r.startswith("BR-DEC-")}
    assert set(expresiones) == {r for r in inventario() if r.startswith("BR-DEC-")}
    por_valor = {r for r, e in expresiones.items() if MIRA_EL_VALOR.search(e)}
    escritas = {r for r, e in expresiones.items() if CUENTA_LO_ESCRITO.search(e)}
    assert not por_valor & escritas, f"{nombre}: las dos formas en {por_valor & escritas}"
    assert por_valor | escritas == set(expresiones), (
        f"{nombre}: ni una ni otra en {set(expresiones) - por_valor - escritas}")
    assert por_valor == set(sintaxis.decimales_por_valor)


def test_facturae_mira_el_valor_en_todas_las_de_decimales():
    assert set(SINTAXIS_FACTURAE.decimales_por_valor) == {
        r for r in inventario() if r.startswith("BR-DEC-")}


# --- Las listas de códigos -------------------------------------------------------
#
# Las listas de `validador/listas_de_codigos.py` están copiadas enteras, porque
# la copia oficial no viaja con el validador. Aquí se comparan con los
# esquematrones de códigos de UBL, CII y EDIFACT, y se dice por qué se usa una
# por regla aunque no digan todos lo mismo.

LISTA_ENTRE_ESPACIOS = re.compile(r"'( [^']+ )'")
TIPO_MIME = re.compile(r"@mimeCode\s*=\s*'([^']+)'")


def listas_oficiales(sintaxis: str) -> dict[str, frozenset[str]]:
    """La primera lista de cada regla del esquematrón de códigos de una sintaxis."""
    raiz = etree.parse(str(OFICIAL / f"EN16931-{sintaxis}-codes.sch")).getroot()
    salida = {}
    for a in raiz.iter(ISO + "assert"):
        prueba = a.get("test")
        tipos = TIPO_MIME.findall(prueba)
        entre = LISTA_ENTRE_ESPACIOS.findall(prueba)
        salida[a.get("id")] = frozenset(tipos) if tipos else frozenset(entre[0].split())
    return salida


def test_cada_lista_es_la_del_esquematron_oficial():
    ubl, cii = listas_oficiales("UBL"), listas_oficiales("CII")
    for codigo, _, cual, _, _, _ in listas_de_codigos._REGLAS:
        if cual == "devengo":
            continue
        aqui = listas_de_codigos.lista(cual, SINTAXIS_UBL)
        oficial = cii[codigo] if codigo == "BR-CL-08" else ubl[codigo]
        assert aqui == oficial, (
            f"{codigo}: sobran {sorted(aqui - oficial)[:10]}, faltan {sorted(oficial - aqui)[:10]}")


def test_donde_cii_dice_otra_lista_es_por_lo_que_se_dice():
    """Una lista por regla, la más al día. Si el comité iguala las dos o cambia
    otra, esto se pone en rojo y hay que volver a decidir."""
    ubl, cii = listas_oficiales("UBL"), listas_oficiales("CII")
    distintas = {r for r in ubl.keys() & cii.keys() if ubl[r] != cii[r]}
    assert distintas == {"BR-CL-01", "BR-CL-06", "BR-CL-14", "BR-CL-15"}, distintas
    for regla in ("BR-CL-14", "BR-CL-15"):
        assert cii[regla] - ubl[regla] == {"AN"} and ubl[regla] - cii[regla] == {"SS"}
    # El asunto de la nota no está en el esquematrón de códigos de UBL: está en
    # su vinculación, con la lista de antes, y la de CII la contiene.
    lista_ubl = frozenset(LISTA_ENTRE_ESPACIOS.findall(vinculacion("UBL")["BR-CL-08"])[0].split())
    assert lista_ubl < cii["BR-CL-08"] and len(cii["BR-CL-08"] - lista_ubl) == 18


def test_los_codigos_de_devengo_son_los_de_cada_esquematron():
    assert listas_oficiales("UBL")["BR-CL-06"] == SINTAXIS_UBL.codigos_de_devengo
    assert listas_oficiales("CII")["BR-CL-06"] == SINTAXIS_CII.codigos_de_devengo


def test_el_esquematron_de_codigos_de_edifact_es_de_otra_epoca():
    """Sin nombre de regla en ninguna comprobación y con las listas de 2017: no
    se puede seguir regla a regla, y se usan las de hoy."""
    raiz = etree.parse(str(OFICIAL / "EN16931-EDIFACT-codes.sch")).getroot()
    comprobaciones = list(raiz.iter(ISO + "assert"))
    assert comprobaciones and not any(a.get("id") for a in comprobaciones)
    unidades = next(a for a in comprobaciones if a.getparent().get("context") == "//D_6411")
    vieja = frozenset(LISTA_ENTRE_ESPACIOS.findall(unidades.get("test"))[0].split())
    assert vieja != listas_de_codigos.UNECE_REC_20


# --- Lo que la web publica de todo esto --------------------------------------
#
# La portada, el aviso legal y el libro blanco dicen cuántas reglas se
# comprueban y con qué se han contrastado. Son cifras que se mueven solas —una
# regla que se declara imposible, un caso nuevo en la próxima versión del
# esquematrón— y están escritas a mano en tres páginas, que es como se quedan
# atrás. Se leen de las páginas y se comparan con lo que mide este fichero.

WEB = pathlib.Path(__file__).resolve().parent.parent / "web"


@functools.cache
def cifras_de_la_norma() -> dict[str, int]:
    hechas = implementadas()
    con_caso = {regla for _, regla, _, _ in casos()}
    return {
        "reglas": len(inventario()),
        "comprobadas": len(hechas),
        "imposibles": len(NO_EVALUABLES),
        "con_caso_oficial": len(con_caso & hechas),
        "sin_caso_oficial": len(hechas - con_caso),
        "casos": len(casos()),
    }


# La página, el patrón con un grupo por cifra —sobre el texto con los espacios
# y saltos de línea reducidos a uno— y qué medida es cada grupo.
PUBLICADAS = (
    ("index.html", r"<dt>De la norma</dt><dd>(\d+) de sus (\d+) reglas</dd>",
     ("comprobadas", "reglas")),
    ("index.html",
     r"Las (\d+) reglas de EN 16931, de los campos obligatorios al desglose de "
     r"IVA: (\d+) se comprueban y (\d+) no se pueden",
     ("reglas", "comprobadas", "imposibles")),
    ("legal.html", r"se comprueban (\d+) de sus (\d+) reglas\. Las otras (\d+)",
     ("comprobadas", "reglas", "imposibles")),
    ("legal.html", r"De las (\d+), (\d+) tienen casos en las pruebas oficiales",
     ("comprobadas", "con_caso_oficial")),
    ("legal.html", r"en sus (\d+) casos este validador dice lo mismo",
     ("casos",)),
    ("legal.html", r"las otras (\d+) no tienen ninguno", ("sin_caso_oficial",)),
    ("tesis.html", r"No comprueba (\d+) de las (\d+) reglas de la EN 16931",
     ("imposibles", "reglas")),
    ("tesis.html", r"qué cubren las otras (\d+)", ("comprobadas",)),
)


@pytest.mark.parametrize("pagina, patron, que", PUBLICADAS,
                         ids=lambda v: v if isinstance(v, str) and v.endswith(".html") else "")
def test_lo_que_la_web_dice_de_la_norma_es_lo_de_hoy(pagina, patron, que):
    texto = " ".join((WEB / pagina).read_text(encoding="utf-8").split())
    encontrados = re.findall(patron, texto)
    assert len(encontrados) == 1, (
        f"«{patron}» aparece {len(encontrados)} veces en {pagina} y tiene que "
        "aparecer una. Si se ha reescrito la frase, este guardián se ha quedado "
        "ciego y hay que volver a apuntarlo.")
    dice = encontrados[0] if isinstance(encontrados[0], tuple) else (encontrados[0],)
    medidas = cifras_de_la_norma()
    for cifra, medida in zip(dice, que, strict=True):
        assert int(cifra) == medidas[medida], (
            f"{pagina} dice {cifra} ({medida}) y hoy son {medidas[medida]}. La "
            "página la lee quien está decidiendo si fiarse: cámbiala.")
    if "casos" in que:
        # «Dice lo mismo que la prueba» solo es cierto con la lista vacía.
        assert not DISCREPANCIAS, (
            f"{pagina} dice que en todos los casos oficiales se dice lo mismo "
            f"que la prueba, y hay {len(DISCREPANCIAS)} discrepancias declaradas")
