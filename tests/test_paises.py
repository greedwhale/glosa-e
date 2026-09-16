# -*- coding: utf-8 -*-
"""La tabla de países, contrastada contra las dos listas oficiales.

Por qué existe
--------------
`validador/paises.py` traduce el país de tres letras que escribe Facturae al
de dos que pide EN 16931. Es una tabla de 233 entradas escrita a mano en el
fuente, y una tabla escrita a mano es exactamente lo que este repositorio no
se fía: se queda atrás y nadie se entera.

Aquí no se vuelve a construir —eso necesitaría red y una descarga— sino que se
comprueba contra lo que **sí está en el repositorio**: el propio esquema
oficial de Facturae, que enumera los 235 países que una factura española puede
escribir. Si mañana alguien toca la tabla o llega un esquema nuevo con países
añadidos, esto lo dice.

**Se lee de `web/paquete.zip`, no de `esquemas/`.** Decía que lo leía «del
repositorio» y lo leía de `esquemas/`, que no se versiona: pasaba en esta
carpeta y en una copia recién clonada reventaba con `FileNotFoundError`. Lo
descubrió montar las pruebas en GitHub, el 16-09-2026. El paquete sí se
versiona y es lo que se publica, así que es además el esquema contra el que
valida la página.

Lo que no cubre, dicho: la lista ISO de dos letras vive en los esquemas CII de
la Comisión y no está desglosada en este repositorio, así que la comprobación
contra ella se hizo una vez, al construir la tabla —233 parejas, cero
discrepancias sobre 249 códigos ISO—, y queda escrita en `paises.py`.
"""
from __future__ import annotations

import pathlib
import re
import zipfile

from validador.paises import ALPHA2, alpha2

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PAQUETE = RAIZ / "web" / "paquete.zip"
ESQUEMA = "esquemas/Facturaev3_2_2.xsd"

# Los dos que Facturae admite y que ISO retiró. Ver `facturae._RETIRADOS`.
RETIRADOS = {"ANT", "ZAR"}


def _paises_del_esquema() -> set[str]:
    with zipfile.ZipFile(PAQUETE) as paquete:
        texto = paquete.read(ESQUEMA).decode("utf-8")
    bloque = re.search(
        r'<xs:simpleType name="CountryType">.*?</xs:simpleType>', texto, re.S)
    assert bloque, "el esquema oficial ya no declara `CountryType` así"
    return set(re.findall(r'value="([A-Z]{3})"', bloque.group(0)))


def test_la_tabla_cubre_todo_lo_que_facturae_admite():
    """Menos los dos retirados, que no tienen a qué traducirse."""
    del_esquema = _paises_del_esquema()
    faltan = sorted(del_esquema - set(ALPHA2) - RETIRADOS)
    assert not faltan, (
        f"el esquema de Facturae admite {', '.join(faltan)} y la tabla no los "
        "traduce. Una factura con ese país quedaría sin país a ojos de "
        "EN 16931 y nadie lo diría."
    )


def test_la_tabla_no_inventa_paises_que_facturae_no_admite():
    del_esquema = _paises_del_esquema()
    sobran = sorted(set(ALPHA2) - del_esquema)
    assert not sobran, (
        f"la tabla traduce {', '.join(sobran)}, que el esquema de Facturae no "
        "admite. O el esquema cambió, o la tabla se copió de otra lista."
    )


def test_los_dos_retirados_no_se_traducen():
    """Traducir `ZAR` a `CD` sería decidir qué quiso decir quien lo escribió."""
    for codigo in sorted(RETIRADOS):
        assert codigo not in ALPHA2, f"{codigo} no debería tener traducción"
        assert alpha2(codigo) is None


def test_toda_traduccion_son_dos_letras_y_ninguna_se_repite():
    malos = [f"{a3}->{a2}" for a3, a2 in ALPHA2.items()
             if not (len(a2) == 2 and a2.isalpha() and a2.isupper())]
    assert not malos, f"traducciones que no son un alpha-2: {malos}"
    # Dos países distintos no pueden compartir código de dos letras.
    vistos: dict[str, str] = {}
    choques = []
    for a3, a2 in sorted(ALPHA2.items()):
        if a2 in vistos:
            choques.append(f"{vistos[a2]} y {a3} comparten {a2}")
        vistos[a2] = a3
    assert not choques, choques


def test_los_de_casa_y_los_vecinos():
    """Un puñado a mano: si la tabla se desplazara una fila, esto lo dice."""
    assert alpha2("ESP") == "ES"
    assert alpha2("PRT") == "PT"
    assert alpha2("FRA") == "FR"
    assert alpha2("DEU") == "DE"
    assert alpha2("AND") == "AD"


def test_no_afirma_nada_cuando_no_hay_nada_que_afirmar():
    for nada in (None, "", "  ", "XX", "XXXX", "esp?"):
        assert alpha2(nada) is None
    # Pero sí tolera lo que traen los ficheros reales: minúsculas y espacios.
    assert alpha2(" esp ") == "ES"
