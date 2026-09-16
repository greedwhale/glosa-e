# -*- coding: utf-8 -*-
"""Lo que dice cada ejemplo publicado, fijado.

Por qué existe
--------------
Los diez ficheros de `ejemplos/` **viajan dentro del sitio publicado**: quien
abre glosa-e.com y pulsa «probar con un ejemplo» abre uno de estos. Son la
primera y muchas veces la única cosa que ve alguien que está decidiendo si
fiarse.

En septiembre de 2026 ocho de los diez estaban mal —sin cantidad, sin unidad y
sin precio en sus líneas— y llevaban así lo bastante como para desplegarse dos
veces. No lo cazó nada, y el motivo es simple: **solo se comprobaban los que
rompían alguna prueba**. `f-0002.xml`, `f-0002-bis.xml` y `f-0006.xml` no
aparecían en ninguna, así que podían decir cualquier cosa.

Lo que se fija aquí no es que pasen, sino **qué dice cada uno**. Un ejemplo
roto a propósito tiene que seguir roto por lo mismo que antes; si un día
adelgaza sus quejas o le salen otras, eso es una noticia, tanto si el
resultado es mejor como si es peor.

La tabla se lee en los dos sentidos: si aparece un ejemplo nuevo sin declarar,
esto se pone en rojo; si desaparece uno declarado, también.

Sin esquemas ni anclas, como toda la suite
------------------------------------------
`conftest.py` apunta el catálogo de esquemas y el almacén de anclas a carpetas
que no existen, y por buenas razones que están escritas allí. Eso vale también
aquí, y tiene dos consecuencias que conviene saber leyendo la tabla. **Los
códigos `XSD-*` no salen**: sobre el sitio publicado, que sí lleva los 24
esquemas, los tres ficheros EDIFACT añaden un `XSD-NO-APLICA` que aquí no está.
Y **`fe-0001.xml` dice `CADENA-SIN-ANCLAS`**: con las anclas del paquete dice
`CADENA-DESCONOCIDA`, porque su certificado es de juguete. Eso lo fija
`test_cadena.py` con un almacén propio, que no depende de lo que tenga
instalado quien corra la suite.

No es un hueco disimulado: lo que estas pruebas fijan son las reglas de
negocio, el IVA y la sintaxis, que es donde estaban los ocho ejemplos rotos.
De la parte con esquemas se encarga el banco, en `/banco` y en
`test_banco.py`.
"""
from __future__ import annotations

import datetime
import pathlib

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EJEMPLOS = RAIZ / "ejemplos"

# La fecha con la que se validan, y no `date.today()`: los certificados de las
# firmas caducan, y una prueba que depende del día en que se corra falla sola
# un martes cualquiera sin que nadie haya tocado nada.
HOY = datetime.date(2026, 9, 20)

# fichero -> (conforme, los códigos que saca)
#
# `fe-0001.xml` sale conforme **con seis incidencias**, y no es contradictorio:
# cuatro son NOTA -tres del binding de Facturae diciendo lo que esa sintaxis no
# tiene dónde escribir- y dos son AVISO de una firma de juguete. Ninguna es
# ERROR, y `conforme` mira los errores.
ESPERADO: dict[str, tuple[bool, tuple[str, ...]]] = {
    "cii-A-0001.xml": (False, ("BR-S-08", "IVA-TIPO-SIN-DESGLOSE")),
    "edi-0001.edi": (True, ()),
    "edi-0002-cortado.edi": (False, ("EDI-MENSAJE-DESCONTADO",
                                     "IVA-AJUSTES-SIN-DETALLAR")),
    "edi-0003-una-de-cinco.edi": (True, ("EDI-UNA-DE-CINCO",)),
    "f-0001.xml": (True, ()),
    "f-0002.xml": (True, ()),
    "f-0002-bis.xml": (True, ()),
    "f-0006.xml": (False, ("BR-CO-10", "BR-S-08")),
    # BR-21 es la cuarta nota del binding: Facturae no tiene identificador de
    # linea (BT-126), asi que la regla no se puede comprobar y se dice.
    # `IVA-CATEGORIA-SIN-MAPA` ya no sale: desde que la categoria se deduce
    # del `TaxTypeCode` y del tipo, esta factura va a S al 21% y las BR-S-*
    # corren de verdad sobre ella.
    "fe-0001.xml": (True, ("BR-01", "BR-14", "BR-21", "CADENA-SIN-ANCLAS",
                           "FIRMA-DEBIL", "SELLO-FALTA")),
    "r-0001.xml": (True, ()),
}


def test_la_tabla_cubre_la_carpeta_entera():
    """Ni de más ni de menos: un ejemplo sin declarar es uno que nadie mira."""
    hay = {f.name for f in EJEMPLOS.iterdir() if f.is_file()}
    faltan = sorted(hay - set(ESPERADO))
    sobran = sorted(set(ESPERADO) - hay)
    assert not faltan, (
        f"estos ejemplos no están declarados aquí: {', '.join(faltan)}. Van "
        "dentro del sitio publicado, así que hay que decir qué se espera de "
        "ellos."
    )
    assert not sobran, (
        f"estos ejemplos están declarados y ya no existen: {', '.join(sobran)}."
    )


@pytest.mark.parametrize("nombre", sorted(ESPERADO))
def test_cada_ejemplo_dice_lo_que_tiene_que_decir(nombre):
    from validador import factura

    conforme, codigos = ESPERADO[nombre]
    informe = factura.validar_archivo(str(EJEMPLOS / nombre), hoy=HOY)
    assert informe.validado, (
        f"{nombre} no se ha llegado a mirar. Sobre un fichero que no se mira, "
        "`conforme` contesta que sí porque no hay errores, así que sin esta "
        "línea la prueba saldría verde con la carpeta vacía."
    )
    salen = tuple(sorted({i.codigo for i in (informe.incidencias or [])}))
    assert salen == codigos, (
        f"{nombre} saca {salen} y se esperaba {codigos}.\n"
        + informe.detalle()
    )
    assert informe.conforme is conforme, (
        f"{nombre}: conforme={informe.conforme}, se esperaba {conforme}.\n"
        + informe.detalle()
    )


def test_el_duplicado_de_f_0002_es_el_que_enciende_cu_10():
    """`f-0002-bis.xml` es copia byte a byte de `f-0002.xml`, y ese es su oficio.

    Nació sin querer, en `60f736e` («Orquestador: … y lotes de ficheros»): iba
    a ser el segundo de un lote de dos y la diferencia que debía tener se
    perdió por el camino. Durante un tiempo fue solo eso, un duplicado que no
    demostraba nada, y aquí había una prueba que lo dejaba anotado como
    **decisión pendiente**: ni borrarlo ni inventarle una diferencia, pero que
    no se olvidara.

    La decisión está tomada y es quedárselo, porque mientras tanto se ganó un
    trabajo: **es lo único de `ejemplos/` que hace saltar una comprobación
    entre ficheros**. Quien valida la carpeta entera desde la página ve
    funcionar CU-10 —la misma factura dos veces: mismo emisor, mismo número y
    misma fecha— y esa es una regla del RD 238/2026 que mirando un fichero
    solo no hay manera de enseñar.

    Así que esto ya no vigila una duda, vigila un trabajo. Si alguien le
    cambia un byte a cualquiera de los dos, CU-10 deja de salir en los
    ejemplos publicados y no se enteraría nadie.
    """
    from validador import factura

    uno = EJEMPLOS / "f-0002.xml"
    bis = EJEMPLOS / "f-0002-bis.xml"
    assert uno.read_bytes() == bis.read_bytes(), (
        "`f-0002-bis.xml` ya no es una copia de `f-0002.xml`, así que el par "
        "ha dejado de encender CU-10 en los ejemplos publicados. Si es a "
        "propósito, busca otra forma de enseñar la comprobación entre "
        "ficheros y cambia esta prueba."
    )

    lote = factura.validar_lote([uno, bis], hoy=HOY)
    assert "CU-10" in {i.codigo for i in lote.cruzadas}, (
        "el par ya no enciende CU-10, que es la única razón por la que se "
        "conserva un duplicado en `ejemplos/`"
    )
    # Y por separado no dicen nada: eso es lo que hace la demostración útil.
    for _, informe in lote.informes:
        assert "CU-10" not in {i.codigo for i in informe.incidencias}
