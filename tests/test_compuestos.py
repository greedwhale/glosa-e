# -*- coding: utf-8 -*-
"""Los códigos que `iva.py` compone al validar, y que no están escritos.

Un `f"BR-{regla.codigo}-08"` no dice cuál es hasta que hay una factura delante,
así que el lector del catálogo no puede sacarlos del fuente. Durante un tiempo
se contaron como huecos —seis patrones, a la vista y declarados—, que era
honrado y dejaba a decenas de códigos reales sin ficha: le salen a alguien en
su informe y no tiene dónde mirar.

Ahora `iva.py` declara lo que compone, pegado a la tabla de la que sale. Eso
es una declaración, y una declaración no comprueba nada por sí sola. Este
fichero la sostiene con tres opiniones que tienen que coincidir:

1. **La lista escrita a mano de aquí abajo.** Envejece, y por eso está: es la
   que se pone en rojo el día que la derivación cambie sin que nadie lo diga.
2. **Lo que `iva.py` declara**, derivado de la tabla de reglas.
3. **Lo que sale de verdad** al provocar las cuatro reglas con cada categoría.

Y hace falta una cuarta, que es la que faltó: **las tres pueden coincidir y
estar mal a la vez**, si la tabla de la que salen dice algo que la norma no
dice. Pasó. Del 12 al 13 de septiembre de 2026 este fichero sostenía que eran
46 y no 54, que ocho códigos de IGIC e IPSI «no existen», y lo comprobaba
provocándolos y viendo que no salían. No salían porque la tabla decía que la
norma no ataba a esas dos categorías, y la norma sí las ata: el esquematrón
oficial trae BR-AF-05, 06, 07 y 10 y los mismos de BR-AG. Las tres opiniones
eran la misma equivocación contada tres veces. La cuarta es la norma escrita,
y está en `test_la_tabla_dice_lo_que_dice_el_esquematron`.
"""
from __future__ import annotations

import re
from decimal import Decimal

from validador import iva
from validador.codigos import codigos_del_paquete
from validador.iva import (
    AL_MENOS_UNA,
    CERO,
    CODIGOS_COMPUESTOS,
    NO_NEGATIVO,
    OBLIGATORIO,
    POSITIVO,
    PROHIBIDO,
    REGLAS,
    SIN_TIPO,
    UNA_SOLA,
    Apunte,
    Grupo,
)

# Los cincuenta y cuatro, escritos. Seis por cada una de las nueve categorías:
# la que no aparece en el desglose (01), el tipo del concepto según cuelgue de
# la línea, de un descuento o de un cargo (05, 06, 07), la base (08) y el
# motivo de exención (10). Con dos cifras, como los escribe la norma.
LOS_CINCUENTA_Y_CUATRO = (
    "BR-S-01", "BR-S-05", "BR-S-06", "BR-S-07", "BR-S-08", "BR-S-10",
    "BR-Z-01", "BR-Z-05", "BR-Z-06", "BR-Z-07", "BR-Z-08", "BR-Z-10",
    "BR-E-01", "BR-E-05", "BR-E-06", "BR-E-07", "BR-E-08", "BR-E-10",
    "BR-AE-01", "BR-AE-05", "BR-AE-06", "BR-AE-07", "BR-AE-08", "BR-AE-10",
    "BR-IC-01", "BR-IC-05", "BR-IC-06", "BR-IC-07", "BR-IC-08", "BR-IC-10",
    "BR-G-01", "BR-G-05", "BR-G-06", "BR-G-07", "BR-G-08", "BR-G-10",
    "BR-O-01", "BR-O-05", "BR-O-06", "BR-O-07", "BR-O-08", "BR-O-10",
    "BR-AF-01", "BR-AF-05", "BR-AF-06", "BR-AF-07", "BR-AF-08", "BR-AF-10",
    "BR-AG-01", "BR-AG-05", "BR-AG-06", "BR-AG-07", "BR-AG-08", "BR-AG-10",
)

# Los ocho que este fichero dio por inexistentes, nombrados uno a uno para que
# la corrección no dependa de que alguien se acuerde de ella.
LOS_OCHO_QUE_SI_EXISTEN = (
    "BR-AF-05", "BR-AF-06", "BR-AF-07", "BR-AF-10",
    "BR-AG-05", "BR-AG-06", "BR-AG-07", "BR-AG-10",
)

# Lo que dice el esquematrón oficial de cada categoría, copiado de su texto
# (`eInvoicing-EN16931`, v1.3.16, `schematron/abstract/EN16931-model.sch`) y no
# de la tabla de `iva.py`. Tipo: BR-{X}-05 a 07. Motivo: BR-{X}-10.
#
#   S   «shall be greater than zero»             · «shall not have» motivo
#   Z   «shall be 0 (zero)»                      · «shall not have» motivo
#   E   «shall be 0 (zero)»                      · «shall have» motivo
#   AE  «shall be 0 (zero)»                      · «shall have» motivo
#   K   «shall be 0 (zero)»                      · «shall have» motivo
#   G   «shall be 0 (zero)»                      · «shall have» motivo
#   O   «shall not contain» tipo                 · «shall have» motivo
#   L   «shall be 0 (zero) or greater than zero» · «shall not have» motivo
#   M   «shall be 0 (zero) or greater than zero» · «shall not have» motivo
#
# Y cuántas entradas del desglose, de BR-{X}-01:
#
#   S, L, M             «at least one VAT category code … equal with»
#   Z, E, AE, K, G, O   «exactly one VAT category code …» / «exactly one VAT
#                       breakdown (BG-23) with the VAT category code …»
LO_QUE_DICE_EL_ESQUEMATRON = {
    "S": (POSITIVO, PROHIBIDO, AL_MENOS_UNA),
    "Z": (CERO, PROHIBIDO, UNA_SOLA),
    "E": (CERO, OBLIGATORIO, UNA_SOLA),
    "AE": (CERO, OBLIGATORIO, UNA_SOLA),
    "K": (CERO, OBLIGATORIO, UNA_SOLA),
    "G": (CERO, OBLIGATORIO, UNA_SOLA),
    "O": (SIN_TIPO, OBLIGATORIO, UNA_SOLA),
    "L": (NO_NEGATIVO, PROHIBIDO, AL_MENOS_UNA),
    "M": (NO_NEGATIVO, PROHIBIDO, AL_MENOS_UNA),
}

CERO_D = Decimal(0)
VEINTIUNO = Decimal(21)
NEGATIVO = Decimal(-7)


def _apunte(categoria: str, tipo: Decimal, **extra) -> Apunte:
    return Apunte("concepto", Decimal(100), categoria, tipo, **extra)


def _un_tipo_que_no_admite(regla) -> Decimal:
    """Un tipo que esa categoría rechaza. Todas rechazan alguno."""
    if regla.tipo == POSITIVO:
        return CERO_D
    if regla.tipo == NO_NEGATIVO:
        return NEGATIVO
    return VEINTIUNO  # CERO lo rechaza, y SIN_TIPO rechaza cualquiera


def _lo_que_sale_de_verdad() -> set[str]:
    """Provoca las cuatro reglas con cada categoría y recoge lo que sale.

    Se llama a las reglas, no a la tabla: si mañana una de ellas cambia de
    condición, esto lo ve y la derivación de `iva.py` se queda sola.
    """
    salen: set[str] = set()
    for categoria, regla in REGLAS.items():
        malo = _un_tipo_que_no_admite(regla)

        # BR-{X}-05, -06 y -07: el mismo concepto colgando de la línea, de un
        # descuento de documento y de un cargo de documento.
        for extra in (
            {},
            {"es_ajuste": True},
            {"es_ajuste": True, "es_cargo": True},
        ):
            for i in iva._regla_tipo_de_los_conceptos(
                [_apunte(categoria, malo, **extra)]
            ):
                salen.add(i.codigo)

        # BR-{X}-10: el motivo, por los dos lados —que falte y que sobre—.
        for motivo in (None, "artículo 20"):
            grupo = Grupo(categoria, CERO_D, Decimal(100), CERO_D, motivo)
            for i in iva._regla_forma_del_grupo(grupo):
                salen.add(i.codigo)

        # BR-{X}-08: base declarada que no cuadra con lo que va a ese tipo.
        grupo = Grupo(categoria, VEINTIUNO, Decimal(999), CERO_D, None)
        for i in iva._regla_base_por_grupo(
            grupo, [_apunte(categoria, VEINTIUNO)]
        ):
            salen.add(i.codigo)

        # BR-{X}-01: hay conceptos de esa categoría y el desglose no la recoge.
        for i in iva._regla_hay_desglose([], [_apunte(categoria, VEINTIUNO)]):
            salen.add(i.codigo)
    return salen


def test_la_tabla_dice_lo_que_dice_el_esquematron():
    """La cuarta opinión, la que no sale de este repositorio."""
    for categoria, esperado in LO_QUE_DICE_EL_ESQUEMATRON.items():
        regla = REGLAS[categoria]
        tabla = (regla.tipo, regla.motivo, regla.desgloses)
        assert tabla == esperado, (
            f"{categoria} (BR-{regla.codigo}-*): la tabla dice "
            f"{'/'.join(tabla)} y el esquematrón {'/'.join(esperado)}")
    assert set(REGLAS) == set(LO_QUE_DICE_EL_ESQUEMATRON)


def test_lo_que_iva_declara_es_lo_que_esta_escrito_aqui():
    """La derivación contra la lista de arriba."""
    declarados = sorted({c for v in CODIGOS_COMPUESTOS.values() for c in v})
    assert declarados == sorted(LOS_CINCUENTA_Y_CUATRO)


def test_lo_que_sale_de_verdad_es_lo_que_esta_escrito_aqui():
    """Y la lista de arriba contra lo que las reglas emiten cuando se provocan."""
    salen = _lo_que_sale_de_verdad()
    compuestos = {c for c in salen if c not in {"IVA-BASE",
                                                "IVA-CATEGORIA-SIN-DESGLOSE"}}
    faltan = sorted(c for c in LOS_CINCUENTA_Y_CUATRO if c not in compuestos)
    sobran = sorted(c for c in compuestos if c not in LOS_CINCUENTA_Y_CUATRO)
    assert not faltan, f"declarados y no salen: {', '.join(faltan)}"
    assert not sobran, f"salen y no están declarados: {', '.join(sobran)}"


def test_los_ocho_que_se_dieron_por_inexistentes_salen():
    """La corrección, dicha por su nombre.

    IGIC e IPSI llevaban `tipo = cualquiera` y `motivo = libre`, con un
    comentario que decía que la norma no las ataba. Con eso la comprobación del
    tipo no marcaba nada como malo y la del motivo no exigía ni prohibía, así
    que estos ocho no salían nunca, y se publicó que no existían. Existen: un
    IGIC con tipo negativo o con motivo de exención es un error para la norma.
    """
    salen = _lo_que_sale_de_verdad()
    for codigo in LOS_OCHO_QUE_SI_EXISTEN:
        assert codigo in salen, f"{codigo} no sale, y la norma lo tiene"
        assert codigo in LOS_CINCUENTA_Y_CUATRO


def test_los_nombres_llevan_dos_cifras():
    """Como en la norma: BR-S-08, no BR-S-8."""
    for codigo in LOS_CINCUENTA_Y_CUATRO:
        assert re.match(r"^BR-[A-Z]+-\d{2}$", codigo), codigo


def test_los_cincuenta_y_cuatro_estan_en_el_catalogo():
    """Y de ahí salen sus fichas, que era el agujero que esto viene a cerrar."""
    hay = {c.codigo for c in codigos_del_paquete()}
    faltan = sorted(c for c in LOS_CINCUENTA_Y_CUATRO if c not in hay)
    assert not faltan, (
        f"{len(faltan)} códigos compuestos no llegan al catálogo: "
        + ", ".join(faltan)
    )


def test_todos_salen_como_error():
    """Ninguna de estas cuatro reglas avisa: las cuatro son error."""
    # El catálogo se lee una vez: leerlo dentro del bucle eran cincuenta y
    # cuatro pasadas por el fuente entero, cuarenta segundos de la suite.
    catalogo = {c.codigo: c for c in codigos_del_paquete()}
    for codigo in LOS_CINCUENTA_Y_CUATRO:
        suyo = catalogo[codigo]
        assert suyo.gravedades == ("error",), f"{codigo}: {suyo.gravedades}"


def test_el_tipo_cero_y_la_exenta_no_se_tratan_igual():
    """Las dos van a cero, y la norma les pide lo contrario sobre el motivo.

    Es la diferencia de la que viven BR-Z-10 y BR-E-10, y la que hace que la
    tabla necesite dos estados para el motivo y no uno: si «no obligatorio» y
    «prohibido» fueran lo mismo, una entrada a tipo cero con un artículo de
    exención pegado pasaría sin que nadie mirara.
    """
    assert REGLAS["Z"].tipo == CERO and REGLAS["E"].tipo == CERO
    assert REGLAS["Z"].motivo == PROHIBIDO
    assert REGLAS["E"].motivo == OBLIGATORIO

    con_motivo = Grupo("Z", CERO_D, Decimal(100), CERO_D, "artículo 20")
    codigos = [i.codigo for i in iva._regla_forma_del_grupo(con_motivo)]
    assert "BR-Z-10" in codigos

    sin_motivo = Grupo("E", CERO_D, Decimal(100), CERO_D, None)
    codigos = [i.codigo for i in iva._regla_forma_del_grupo(sin_motivo)]
    assert "BR-E-10" in codigos


def test_el_igic_a_cero_no_es_un_error():
    """«0 (zero) or greater than zero»: el cero vale, lo negativo no.

    Es la diferencia con el tipo general, que exige mayor que cero, y la razón
    de que haga falta un estado propio en la tabla y no baste con POSITIVO.
    """
    for categoria in ("L", "M"):
        a_cero = iva._regla_tipo_de_los_conceptos([_apunte(categoria, CERO_D)])
        assert a_cero == [], f"{categoria} al 0%: {[i.codigo for i in a_cero]}"
        positivo = iva._regla_tipo_de_los_conceptos([_apunte(categoria, Decimal(7))])
        assert positivo == []
