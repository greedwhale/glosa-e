# -*- coding: utf-8 -*-
"""Que el catálogo no vuelva a quedarse corto en silencio.

Esto es lo que faltaba cuando se descubrió el agujero. `codigos.py` leía el
primer argumento de cada `Incidencia(...)` y, si no era una cadena, seguía
adelante **sin decir nada**: diecisiete códigos —BR-02 a BR-15, BR-22, BR-23 y
BR-26— se emitían de verdad y no salían en el catálogo publicado, que además
prometía que eso no podía pasar. No hubo error, no hubo aviso y todo estaba en
verde; el hueco solo se vio porque alguien fue a buscar un código concreto.

Las pruebas de aquí son de las dos clases que hacen falta:

- que el lector **lea** lo que ahora sabe leer, con los códigos escritos uno a
  uno para que la prueba diga cuál falta y no solo que la cuenta no cuadra;
- que lo que **no** sepa leer salga a la luz, y que la lista de esos huecos
  esté declarada. Si mañana alguien escribe una llamada nueva de una forma que
  el lector no entiende, esto se pone en rojo con el fichero y la línea en vez
  de dejar caer un código.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from validador.codigos import codigos_del_paquete, sin_leer_del_paquete

# Los diecisiete que estaban perdidos. Escritos, y no `range(2, 16)`, porque
# una prueba que genera lo que comprueba deja de comprobar el día que la
# generación se equivoque igual que el código.
LOS_QUE_FALTABAN = (
    "BR-02", "BR-03", "BR-04", "BR-05", "BR-06", "BR-07", "BR-08", "BR-09",
    "BR-10", "BR-11", "BR-12", "BR-13", "BR-14", "BR-15",
    "BR-22", "BR-23", "BR-26",
)

# Lo que el lector no sabe leer del fuente. **Hoy está vacía**, y llegar a eso
# costó: los seis patrones que había aquí —los `BR-{}-8` del IVA y sus
# hermanos— se componen al validar con la categoría de la operación, así que
# no hay una cadena que leer. Ahora `iva.py` declara qué códigos puede
# componer, pegado a la tabla de la que salen, y el catálogo los recoge.
#
# Vacía no quiere decir inútil: esta tupla es la declaración de que no hay
# ninguno, y la prueba se pone en rojo el día que aparezca una forma nueva de
# emitir un código que nadie sepa leer. Un hueco declarado se puede cerrar;
# uno silencioso no se sabe ni que está.
HUECOS_CONOCIDOS: tuple[tuple[str, str], ...] = ()


def test_los_codigos_de_las_tablas_estan_en_el_catalogo():
    hay = {c.codigo for c in codigos_del_paquete()}
    faltan = [c for c in LOS_QUE_FALTABAN if c not in hay]
    assert not faltan, (
        f"El catálogo no trae {', '.join(faltan)}. Son códigos que el "
        "validador emite de verdad, y salen de una tabla recorrida con un "
        "`for`: si `codigos.py` deja de desatar el bucle, vuelven a "
        "desaparecer sin que nada falle."
    )


def test_lo_que_el_lector_no_sabe_leer_esta_declarado():
    """El guardián. En rojo cuando aparece una forma nueva de emitir códigos."""
    hay = tuple(sorted((s.modulo, s.patron) for s in sin_leer_del_paquete()))
    esperado = tuple(sorted(HUECOS_CONOCIDOS))
    nuevos = [x for x in hay if x not in esperado]
    idos = [x for x in esperado if x not in hay]
    donde = {(s.modulo, s.patron): f"{s.modulo}:{s.linea}"
             for s in sin_leer_del_paquete()}
    assert hay == esperado, (
        "La lista de códigos que no se pueden leer del fuente ha cambiado.\n"
        + (f"  Nuevos: {', '.join(donde[x] + ' ' + x[1] for x in nuevos)}\n"
           "  Esos códigos NO van a salir en el catálogo publicado. O se "
           "escriben de forma que `codigos.py` los lea —una tabla, una "
           "constante— o se añaden a HUECOS_CONOCIDOS sabiendo que quedan "
           "fuera.\n" if nuevos else "")
        + (f"  Ya no están: {', '.join(x[1] for x in idos)}\n"
           "  Si es que se han arreglado, quítalos de HUECOS_CONOCIDOS.\n"
           if idos else "")
    )


def test_el_lector_desata_los_bucles(tmp_path: Path):
    """Provocado: una tabla de reglas recorrida con un `for`, como las de verdad."""
    (tmp_path / "inventado.py").write_text(
        "TABLA = (\n"
        "    ('XX-01', 'lo uno'),\n"
        "    ('XX-02', 'lo otro'),\n"
        ")\n"
        "def reglas():\n"
        "    for codigo, texto in TABLA:\n"
        "        yield Incidencia(codigo, ERROR, texto)\n",
        encoding="utf-8",
    )
    hay = {c.codigo: c for c in codigos_del_paquete(tmp_path)}
    assert set(hay) == {"XX-01", "XX-02"}
    # La gravedad se lee de la llamada aunque el código venga de la tabla.
    assert hay["XX-01"].gravedades == ("error",)
    assert not sin_leer_del_paquete(tmp_path)


def test_el_lector_delata_lo_que_no_entiende(tmp_path: Path):
    """El arreglo, roto a propósito: un código que no se puede leer del fuente."""
    (tmp_path / "inventado.py").write_text(
        "def reglas(cosa):\n"
        "    return Incidencia(cosa.codigo_de_donde_sea, ERROR, 'lo que sea')\n",
        encoding="utf-8",
    )
    assert not codigos_del_paquete(tmp_path)
    huecos = sin_leer_del_paquete(tmp_path)
    assert len(huecos) == 1
    assert huecos[0].modulo == "inventado.py"
    assert huecos[0].linea == 2
    # Se enseña lo que se ve desde fuera, no el nombre de la variable.
    assert huecos[0].patron == "cosa.codigo_de_donde_sea"


def test_el_lector_enseña_el_patron_de_una_f_string(tmp_path: Path):
    """Un código compuesto se dice como «BR-{}-8», que es reconocible."""
    (tmp_path / "inventado.py").write_text(
        "def reglas(regla):\n"
        "    return Incidencia(f'BR-{regla.codigo}-8', ERROR, 'lo que sea')\n",
        encoding="utf-8",
    )
    huecos = sin_leer_del_paquete(tmp_path)
    assert [h.patron for h in huecos] == ["BR-{}-8"]


def test_una_rama_legible_no_se_pierde_por_la_otra(tmp_path: Path):
    """`f"BR-{x}-1" if regla else "IVA-CATEGORIA-SIN-DESGLOSE"`: cuentan las dos.

    Antes de separarlas, el código escrito de la rama `else` se perdía con la
    f-string de la otra, y era un código real que no salía en ninguna parte.
    """
    (tmp_path / "inventado.py").write_text(
        "def reglas(regla):\n"
        "    return Incidencia(\n"
        "        f'BR-{regla.codigo}-1' if regla else 'XX-SIN-NADA',\n"
        "        ERROR, 'lo que sea')\n",
        encoding="utf-8",
    )
    assert [c.codigo for c in codigos_del_paquete(tmp_path)] == ["XX-SIN-NADA"]
    assert [h.patron for h in sin_leer_del_paquete(tmp_path)] == ["BR-{}-1"]


def test_la_tabla_con_filas_de_otra_forma_no_se_adivina(tmp_path: Path):
    """Media tabla leída es peor que ninguna: saldría una lista incompleta."""
    (tmp_path / "inventado.py").write_text(
        "TABLA = (\n"
        "    ('XX-01', 'lo uno'),\n"
        "    OTRA_COSA,\n"
        ")\n"
        "def reglas():\n"
        "    for codigo, texto in TABLA:\n"
        "        yield Incidencia(codigo, ERROR, texto)\n",
        encoding="utf-8",
    )
    assert not codigos_del_paquete(tmp_path)
    assert [h.patron for h in sin_leer_del_paquete(tmp_path)] == ["codigo"]


def test_el_bucle_de_dentro_manda_sobre_el_de_fuera(tmp_path: Path):
    """Como en Python. Si no, la llamada saldría con el código del bucle ajeno."""
    (tmp_path / "inventado.py").write_text(
        "def reglas():\n"
        "    for codigo, _ in (('FUERA-01', 1),):\n"
        "        for codigo, _ in (('DENTRO-01', 2),):\n"
        "            yield Incidencia(codigo, ERROR, 'lo que sea')\n",
        encoding="utf-8",
    )
    assert [c.codigo for c in codigos_del_paquete(tmp_path)] == ["DENTRO-01"]


def test_un_nombre_que_se_resuelve_a_si_mismo_no_cuelga(tmp_path: Path):
    """`codigo = codigo or "X"` es Python legal; el lector no puede quedarse ahí."""
    (tmp_path / "inventado.py").write_text(
        "def reglas(codigo):\n"
        "    codigo = codigo\n"
        "    return Incidencia(codigo, ERROR, 'lo que sea')\n",
        encoding="utf-8",
    )
    # Lo que importa es que conteste; que no lo resuelva es lo correcto.
    assert not codigos_del_paquete(tmp_path)
    assert len(sin_leer_del_paquete(tmp_path)) == 1


@pytest.mark.parametrize("codigo", ["BR-22", "BR-23", "BR-26"])
def test_las_reglas_de_linea_salen_en_el_catalogo(codigo):
    """Las tres últimas en entrar, que son las que destaparon el agujero."""
    assert codigo in {c.codigo for c in codigos_del_paquete()}

# Cómo escribe la norma sus códigos, sacado del esquematrón oficial
# (`eInvoicing-EN16931`, v1.3.16): el número va **siempre con dos cifras**
# —BR-01, BR-CO-10, BR-S-08, BR-CL-01—, y el prefijo de grupo es de letras.
_COMO_LOS_ESCRIBE_LA_NORMA = r"^BR-(?:[A-Z]+-)?\d{2}$"


def test_los_codigos_de_la_norma_se_escriben_como_la_norma():
    """Un código con otro nombre es un código que nadie encuentra.

    Durante un tiempo el IVA publicó `BR-S-8`, `BR-O-5` y otros treinta y
    siete así, sin el cero. La norma los llama `BR-S-08` y `BR-O-05`, y así
    los escribe cualquier otro validador en su rechazo: quien copiara el código
    de ese rechazo para buscarlo aquí no encontraba la ficha. No lo vio ninguna
    prueba porque todas se escribieron con el mismo nombre equivocado que el
    código; se vio al medir la cobertura contra el esquematrón y encontrar la
    mitad de las coincidencias solo después de quitar los ceros.

    Se comprueba la forma y no una lista, a propósito: la lista la puede
    escribir mal la misma mano que escribe mal el código.
    """
    import re

    mal = sorted(
        c.codigo for c in codigos_del_paquete()
        if c.codigo.startswith("BR-")
        and not re.match(_COMO_LOS_ESCRIBE_LA_NORMA, c.codigo)
    )
    assert not mal, (
        f"{len(mal)} códigos de la norma no se escriben como en la norma: "
        + ", ".join(mal))
