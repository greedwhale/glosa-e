# -*- coding: utf-8 -*-
"""Los códigos que `iva.py` compone al validar, y que no están escritos.

Un `f"BR-{regla.codigo}-8"` no dice cuál es hasta que hay una factura delante,
así que el lector del catálogo no puede sacarlos del fuente. Durante un tiempo
se contaron como huecos —seis patrones, a la vista y declarados—, que era
honrado y dejaba a cuarenta y seis códigos reales sin ficha: le salen a alguien
en su informe y no tiene dónde mirar.

Ahora `iva.py` declara lo que compone, pegado a la tabla de la que sale. Eso
es una declaración, y una declaración no comprueba nada por sí sola. Este
fichero la sostiene con tres opiniones que tienen que coincidir:

1. **La lista escrita a mano de aquí abajo.** Envejece, y por eso está: es la
   que se pone en rojo el día que la derivación cambie sin que nadie lo diga.
2. **Lo que `iva.py` declara**, derivado de la tabla de reglas.
3. **Lo que sale de verdad** al provocar las cuatro reglas con cada categoría.

Y una cuarta comprobación al revés, que es la que de verdad importa: los ocho
códigos que saldrían de multiplicar nueve categorías por seis sufijos y **no
existen** no tienen que salir nunca. Publicar uno sería inventarlo, que es
exactamente lo que ya pasó una vez aquí con unos `BR-IG-*` que no están en
ninguna norma.
"""
from __future__ import annotations

from decimal import Decimal

from validador import iva
from validador.codigos import codigos_del_paquete
from validador.iva import (
    CERO,
    CODIGOS_COMPUESTOS,
    CUALQUIERA,
    POSITIVO,
    REGLAS,
    Apunte,
    Grupo,
)

# Los cuarenta y seis, escritos. Seis por cada una de las siete categorías que
# la norma ata, y solo dos para IGIC e IPSI, que no ata.
LOS_CUARENTA_Y_SEIS = (
    "BR-S-1", "BR-S-5", "BR-S-6", "BR-S-7", "BR-S-8", "BR-S-10",
    "BR-Z-1", "BR-Z-5", "BR-Z-6", "BR-Z-7", "BR-Z-8", "BR-Z-10",
    "BR-E-1", "BR-E-5", "BR-E-6", "BR-E-7", "BR-E-8", "BR-E-10",
    "BR-AE-1", "BR-AE-5", "BR-AE-6", "BR-AE-7", "BR-AE-8", "BR-AE-10",
    "BR-IC-1", "BR-IC-5", "BR-IC-6", "BR-IC-7", "BR-IC-8", "BR-IC-10",
    "BR-G-1", "BR-G-5", "BR-G-6", "BR-G-7", "BR-G-8", "BR-G-10",
    "BR-O-1", "BR-O-5", "BR-O-6", "BR-O-7", "BR-O-8", "BR-O-10",
    "BR-AF-1", "BR-AF-8",
    "BR-AG-1", "BR-AG-8",
)

# Y los ocho que no existen. IGIC e IPSI llevan `tipo = cualquiera` y
# `motivo = libre`: la comprobación del tipo no marca nada como malo y la del
# motivo ni lo exige ni lo prohíbe, así que esas ramas no se disparan nunca.
LOS_OCHO_QUE_NO_EXISTEN = (
    "BR-AF-5", "BR-AF-6", "BR-AF-7", "BR-AF-10",
    "BR-AG-5", "BR-AG-6", "BR-AG-7", "BR-AG-10",
)

CERO_D = Decimal(0)
VEINTIUNO = Decimal(21)


def _apunte(categoria: str, tipo: Decimal, **extra) -> Apunte:
    return Apunte("concepto", Decimal(100), categoria, tipo, **extra)


def _lo_que_sale_de_verdad() -> set[str]:
    """Provoca las cuatro reglas con cada categoría y recoge lo que sale.

    Se llama a las reglas, no a la tabla: si mañana una de ellas cambia de
    condición, esto lo ve y la derivación de `iva.py` se queda sola.
    """
    salen: set[str] = set()
    for categoria, regla in REGLAS.items():
        # Un tipo que esa categoría no admite. Con CUALQUIERA no hay ninguno
        # que no admita, y de eso trata la comprobación de los ocho.
        malo = CERO_D if regla.tipo == POSITIVO else VEINTIUNO

        # BR-{X}-5, -6 y -7: el mismo concepto colgando de la línea, de un
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

        # BR-{X}-8: base declarada que no cuadra con lo que va a ese tipo.
        grupo = Grupo(categoria, VEINTIUNO, Decimal(999), CERO_D, None)
        for i in iva._regla_base_por_grupo(
            grupo, [_apunte(categoria, VEINTIUNO)]
        ):
            salen.add(i.codigo)

        # BR-{X}-1: hay conceptos de esa categoría y el desglose no la recoge.
        for i in iva._regla_hay_desglose([], [_apunte(categoria, VEINTIUNO)]):
            salen.add(i.codigo)
    return salen


def test_lo_que_iva_declara_es_lo_que_esta_escrito_aqui():
    """La derivación contra la lista de arriba."""
    declarados = sorted({c for v in CODIGOS_COMPUESTOS.values() for c in v})
    assert declarados == sorted(LOS_CUARENTA_Y_SEIS)


def test_lo_que_sale_de_verdad_es_lo_que_esta_escrito_aqui():
    """Y la lista de arriba contra lo que las reglas emiten cuando se provocan."""
    salen = _lo_que_sale_de_verdad()
    compuestos = {c for c in salen if c not in {"IVA-BASE",
                                                "IVA-CATEGORIA-SIN-DESGLOSE"}}
    faltan = sorted(c for c in LOS_CUARENTA_Y_SEIS if c not in compuestos)
    sobran = sorted(c for c in compuestos if c not in LOS_CUARENTA_Y_SEIS)
    assert not faltan, f"declarados y no salen: {', '.join(faltan)}"
    assert not sobran, f"salen y no están declarados: {', '.join(sobran)}"


def test_los_ocho_que_no_existen_no_salen():
    """El que de verdad protege: publicar un código inventado es lo peor.

    IGIC e IPSI recibieron una vez el nombre de unas reglas `BR-IG-*` que no
    existen en ninguna norma, inventadas aquí por analogía con el
    intracomunitario. Esta comprobación es para que no vuelva a pasar por el
    otro lado: anunciando ramas que con esas categorías no se disparan.
    """
    salen = _lo_que_sale_de_verdad()
    for codigo in LOS_OCHO_QUE_NO_EXISTEN:
        assert codigo not in salen, f"{codigo} ha salido, y no debería existir"
        assert codigo not in LOS_CUARENTA_Y_SEIS


def test_las_dos_categorias_sin_atar_solo_tienen_dos_reglas():
    """Por qué son dos y no seis, dicho donde se pueda comprobar."""
    for categoria in ("L", "M"):
        regla = REGLAS[categoria]
        assert regla.tipo == CUALQUIERA
        assert regla.motivo == "libre"
        suyos = [c for c in LOS_CUARENTA_Y_SEIS
                 if c.startswith(f"BR-{regla.codigo}-")]
        assert len(suyos) == 2, f"{categoria} tiene {len(suyos)} y son dos"


def test_los_cuarenta_y_seis_estan_en_el_catalogo():
    """Y de ahí salen sus fichas, que era el agujero que esto viene a cerrar."""
    hay = {c.codigo for c in codigos_del_paquete()}
    faltan = sorted(c for c in LOS_CUARENTA_Y_SEIS if c not in hay)
    assert not faltan, (
        f"{len(faltan)} códigos compuestos no llegan al catálogo: "
        + ", ".join(faltan)
    )


def test_todos_salen_como_error():
    """Ninguna de estas cuatro reglas avisa: las cuatro son error."""
    for codigo in sorted({c.codigo for c in codigos_del_paquete()}
                         & set(LOS_CUARENTA_Y_SEIS)):
        suyo = next(c for c in codigos_del_paquete() if c.codigo == codigo)
        assert suyo.gravedades == ("error",), f"{codigo}: {suyo.gravedades}"


def test_el_tipo_cero_y_la_exenta_no_se_tratan_igual():
    """Las dos van a cero, y la norma les pide lo contrario sobre el motivo.

    Es la diferencia de la que viven BR-Z-10 y BR-E-10, y la que hace que la
    tabla necesite tres estados y no dos: si «no obligatorio» y «prohibido»
    fueran lo mismo, una entrada a tipo cero con un artículo de exención
    pegado pasaría sin que nadie mirara.
    """
    assert REGLAS["Z"].tipo == CERO and REGLAS["E"].tipo == CERO
    assert REGLAS["Z"].motivo == "prohibido"
    assert REGLAS["E"].motivo == "obligatorio"

    con_motivo = Grupo("Z", CERO_D, Decimal(100), CERO_D, "artículo 20")
    codigos = [i.codigo for i in iva._regla_forma_del_grupo(con_motivo)]
    assert "BR-Z-10" in codigos

    sin_motivo = Grupo("E", CERO_D, Decimal(100), CERO_D, None)
    codigos = [i.codigo for i in iva._regla_forma_del_grupo(sin_motivo)]
    assert "BR-E-10" in codigos
