"""La lista de mensajes de error de la solución pública, del fichero de la AEAT.

La AEAT la publicó el 23-11-2026 en su Portal de Desarrolladores, y
`validador/errores_de_la_aeat.py` la lleva generada por
`herramientas/errores_de_la_aeat.py`. Tres cosas:

1. **Que la tabla sea la del fichero.** Si está `anexos/errores_negocio.properties`
   (no se versiona, como el XML del BOE), su huella es la declarada y volver a
   generarla da lo mismo. Donde no está, como en GitHub, se saltan.
2. **Que se niegue con lo que no lee como Java**, que es quien lo usa: una
   línea que sigue en la siguiente, una clave con dos puntos o espacios, una
   línea sin `=`, una regla dos veces. Lo que no se entiende no se convierte
   en una tabla que parece buena.
3. **Que la tabla traiga lo que se contó a mano** el día que salió.
"""

import hashlib
import pathlib
import re

import pytest

from herramientas import errores_de_la_aeat as generador
from validador import errores_de_la_aeat

RAIZ = pathlib.Path(__file__).resolve().parent.parent
FICHERO = RAIZ / "anexos" / "errores_negocio.properties"


# --- 1. Que la tabla sea la del fichero ------------------------------------------

@pytest.mark.skipif(not FICHERO.exists(), reason="no está `anexos/errores_negocio.properties`")
def test_la_huella_es_la_del_fichero():
    declarada = re.search(r"SHA-256 ([0-9a-f]{64})", errores_de_la_aeat.__doc__).group(1)
    assert hashlib.sha256(FICHERO.read_bytes()).hexdigest() == declarada


@pytest.mark.skipif(not FICHERO.exists(), reason="no está `anexos/errores_negocio.properties`")
def test_volver_a_generar_da_exactamente_lo_mismo(tmp_path):
    """No basta con que el fichero no cambie: alguien puede tocar el lector."""
    destino = tmp_path / "errores_de_la_aeat.py"
    generador.escribe_modulo(FICHERO, destino, errores_de_la_aeat.PUBLICADA)
    hoy = (RAIZ / "validador" / "errores_de_la_aeat.py").read_bytes().replace(b"\r\n", b"\n")
    assert destino.read_bytes().replace(b"\r\n", b"\n") == hoy


def test_la_fecha_es_la_de_la_cabecera():
    assert errores_de_la_aeat.PUBLICADA == "23-11-2026"
    assert f"publicado el {errores_de_la_aeat.PUBLICADA}" in " ".join(errores_de_la_aeat.__doc__.split())


# --- 2. Que se niegue con lo que no lee como Java ---------------------------------

def _fichero(tmp_path, texto):
    camino = tmp_path / "errores.properties"
    camino.write_bytes(texto.encode("latin-1"))
    return camino


@pytest.mark.parametrize("linea", [
    "RULE_SPFE-CORE-01_MENSAJE=Sigue en la \\",
    "RULE_SPFE-CORE-01:MENSAJE=Java partiría en los dos puntos",
    "RULE SPFE-CORE-01_MENSAJE=Java partiría en el espacio",
    "Una línea sin igual",
    "RULE_raro=Una clave de regla con otra forma",
])
def test_se_niega_con_lo_que_no_lee_como_java(tmp_path, linea):
    camino = _fichero(tmp_path, "#MENSAJES\nRULE_SPFE-CORE-02_MENSAJE=Bien\n" + linea + "\n")
    with pytest.raises(generador.FicheroQueNoSeEntiende):
        generador.tablas(camino)


def test_una_regla_dos_veces_con_textos_distintos_se_niega(tmp_path):
    camino = _fichero(tmp_path, "RULE_SPFE-CORE-02_MENSAJE=Uno\nRULE_SPFE-CORE-02_MENSAJE=Otro\n")
    with pytest.raises(generador.FicheroQueNoSeEntiende):
        generador.tablas(camino)


def test_la_fecha_tiene_que_ir_como_se_escribe_aqui(tmp_path):
    camino = _fichero(tmp_path, "RULE_SPFE-CORE-02_MENSAJE=Bien\n")
    with pytest.raises(ValueError):
        generador.escribe_modulo(camino, tmp_path / "x.py", "2026-11-23")


def test_se_lee_como_lo_lee_java(tmp_path):
    camino = _fichero(tmp_path, "\n".join([
        "#RULE_SPFE-CORE-09_MENSAJE=Comentada, no cuenta",
        "! también es comentario",
        "RULE_SPFE-CORE-01_MENSAJE_1=Primero: con dos puntos y = dentro",
        "RULE_SPFE-CORE-01_MENSAJE_2=  Segundo, sin los espacios de delante",
        "RULE_BR-CO-10_MENSAJE=Con \\u2211 y \\u2013",
        "ERROR_GENERAL=El de antes",
        "ERROR_GENERAL=El de después",
        "",
    ]))
    reglas, generales = generador.tablas(camino)
    assert reglas == {
        "SPFE-CORE-01": ["Primero: con dos puntos y = dentro", "Segundo, sin los espacios de delante"],
        "BR-CO-10": ["Con ∑ y –"],
    }
    # Java se queda con la última; la de antes se guarda para reconocerla.
    assert generales == [("ERROR_GENERAL", "El de antes"), ("ERROR_GENERAL", "El de después")]


# --- 3. Lo que se contó a mano el 23-11-2026 ---------------------------------------

def test_trae_lo_que_se_conto_a_mano():
    """316 reglas con 461 mensajes y 52 generales, contados con grep ese día."""
    assert len(errores_de_la_aeat.REGLAS) == 316
    assert sum(len(m) for m in errores_de_la_aeat.REGLAS.values()) == 461
    assert len(errores_de_la_aeat.GENERALES) == 52


def test_los_cuatro_codigos_del_ejemplo_de_la_aeat():
    """Los de la respuesta de ejemplo de su validador previo (el 09)."""
    reglas = errores_de_la_aeat.REGLAS
    assert reglas["SPFE-IDEN-02"] == ("Nif del Emisor no permitido",)
    assert reglas["SPFE-IDEN-05"] == ("Nif del Destinatario no permitido",)
    assert len(reglas["SPFE-REPR-01"]) == 5
    assert "El valor del identificador de la cuenta de pago (BT-84) debe ser un IBAN válido" in reglas["SPFE-CORE-18"]
    generales = dict(errores_de_la_aeat.GENERALES)
    assert generales["ERROR_NIF_FORMATO_INCORRECTO"] == "El NIF tiene un formato erróneo"


def test_las_claves_con_sufijo_raro_van_con_su_regla():
    """`_CERO`, `_DET` y un `2` pegado: son de la regla, no generales."""
    assert len(errores_de_la_aeat.REGLAS["BR-46"]) == 2
    assert len(errores_de_la_aeat.REGLAS["BR-CO-48"]) == 2
    assert len(errores_de_la_aeat.REGLAS["BR-CO-51"]) == 2
    assert not any(clave.startswith("RULE_") for clave, _ in errores_de_la_aeat.GENERALES)
