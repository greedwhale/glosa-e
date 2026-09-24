# -*- coding: utf-8 -*-
"""Pegar el texto de la factura: por el camino del fichero, y en UTF-8.

Por qué existe
--------------
Desde el 24-09-2026 la portada deja pegar la factura como texto, para quien
la tiene copiada de un correo o de su programa de facturación. Lo pegado se
hace fichero en la página y entra por `soltar()`, el camino de uno soltado:
una ruta aparte podría portarse distinto, y lo pegado y el fichero no darían
el mismo informe.

Al pegar cambian dos cosas, y las dos se midieron:

- **El portapapeles da letras, no bytes.** Escritas en UTF-8 bajo una
  declaración que dice ISO-8859-1, lxml lee «Espa\\xc3\\xb1a» donde ponía
  «España», y sin un error. En la página, una moneda «EUÑ» salía en el informe
  como «EUÃ». La página reescribe la declaración a UTF-8 y lo dice encima del
  informe.
- **Lo que se pierda al copiar cambia lo que cubre la firma.** Un salto de
  línea añadido detrás de `<FileHeader>` en `fe-0001.xml` da FIRMA-ALTERADA,
  así que en una factura firmada el informe avisa de que, para la firma, mejor
  el fichero.

Aquí no hay navegador: lo de la página se vio en él —la misma muestra pegada y
abierta con su botón dan el mismo veredicto, las mismas partes y los mismos
códigos—. Lo que sí se puede hacer es sacar las expresiones regulares de la
página, que son también de Python, y probarlas contra las muestras de verdad.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from lxml import etree

RAIZ = Path(__file__).resolve().parents[1]
INDEX = RAIZ / "web" / "index.html"
EJEMPLOS = RAIZ / "ejemplos"


def _script() -> str:
    """El script de la portada, el que va en línea."""
    texto = INDEX.read_text(encoding="utf-8")
    scripts = re.findall(r"<script>(.*?)</script>", texto, re.S)
    assert len(scripts) == 1, f"index.html lleva {len(scripts)} scripts en línea"
    return scripts[0]


def _funcion(nombre: str) -> str:
    script = _script()
    assert script.count(f"function {nombre}(") == 1, f"no hay una sola «function {nombre}»"
    principio = script.index("{", script.index(f"function {nombre}(")) + 1
    nivel, i = 1, principio
    while nivel:
        nivel += {"{": 1, "}": -1}.get(script[i], 0)
        i += 1
    return script[principio:i - 1]


def _regex(patron: str) -> str:
    """Una expresión regular de `comoFichero`, sacada de la página."""
    casa = re.search(patron, _funcion("comoFichero"))
    assert casa, f"comoFichero ya no lleva lo que buscaba esta prueba: {patron}"
    return casa[1]


def _declarada() -> re.Pattern:
    return re.compile(_regex(r"declarada = texto\.match\(/(.+?)/\);"))


def _es_utf8() -> re.Pattern:
    return re.compile(_regex(r"!/(.+?)/i\.test\(declarada\[2\]\)"), re.I)


def _firmada() -> re.Pattern:
    return re.compile(_regex(r"firmada = /(.+?)/\.test\(texto\)"))


# Lo que hace `comoFichero` con la declaración, tal cual está en la página. Aquí
# no se puede correr JavaScript, así que `_como_la_pagina` lo repite en Python;
# y para que la copia no se quede atrás, la primera prueba exige que la página
# diga exactamente esto.
REESCRITURA = """\
  const otra = declarada && !/^utf-?8$/i.test(declarada[2]) ? declarada[2] : "";
  if (otra) {
    const principio = declarada[0].slice(0, -(otra.length + 1));
    texto = principio + "UTF-8" + declarada[1] + texto.slice(declarada[0].length);
  }
"""


def _como_la_pagina(texto: str) -> str:
    """REESCRITURA, en Python, con las expresiones regulares de la página."""
    texto = texto.lstrip()
    casa = _declarada().match(texto)
    if casa and not _es_utf8().match(casa[2]):
        texto = casa[0][:-(len(casa[2]) + 1)] + "UTF-8" + casa[1] + texto[len(casa[0]):]
    return texto


# --- Por el camino del fichero -------------------------------------------------

def test_lo_pegado_entra_por_donde_un_fichero():
    script = _script()
    manejador = re.search(
        r'validarPegado\.addEventListener\("click", \(\) => \{(.*?)\n\}\);', script, re.S)
    assert manejador, "el botón «Validar lo pegado» ya no tiene su manejador"
    assert "soltar([fichero]" in manejador[1] and "Glosa." not in manejador[1], (
        "lo pegado ya no entra por soltar(): una ruta aparte puede portarse "
        "distinto, y lo pegado y el fichero dejarían de dar el mismo informe")
    assert "new File([texto]" in _funcion("comoFichero")
    assert script.count("Glosa.validar(") == 1, (
        "hay más de un sitio que llama a Glosa.validar: solo soltar() tiene que hacerlo")


def test_el_cuadro_va_con_la_zona():
    """Dentro de la mesa de la zona, y con su botón y su nombre."""
    texto = INDEX.read_text(encoding="utf-8")
    mesa = texto[texto.index('<div class="mesa">'):texto.index('<div class="arranque"')]
    for trozo in ('<details class="pegar" id="pegar">', '<textarea id="pegado"',
                  'aria-label="El texto de la factura"', 'id="validar-pegado" disabled'):
        assert trozo in mesa, f"«{trozo}» ya no está junto a la zona"


# --- En UTF-8 --------------------------------------------------------------------

def test_la_pagina_reescribe_lo_que_repite_esta_prueba():
    assert REESCRITURA in _funcion("comoFichero"), (
        "la reescritura de la declaración ya no es la que repite esta prueba en "
        "_como_la_pagina. Si se ha quitado, lo pegado en ISO-8859-1 vuelve a "
        "leerse mal sin un error; si solo ha cambiado, cambia también la copia.")


@pytest.mark.parametrize("declaracion", [
    '<?xml version="1.0" encoding="ISO-8859-1"?>',
    "<?xml version='1.0' encoding='windows-1252'?>",
    '<?xml version="1.0" encoding = "iso-8859-15" standalone="yes"?>',
])
def test_la_declaracion_que_no_es_utf8_se_reescribe(declaracion):
    texto = declaracion + "\n<a>España</a>"
    # Lo que pasaba sin reescribirla: letras en UTF-8 leídas como otra cosa.
    assert etree.fromstring(texto.encode("utf-8")).text != "España"
    assert etree.fromstring(_como_la_pagina(texto).encode("utf-8")).text == "España"


@pytest.mark.parametrize("ejemplo", sorted(p.name for p in EJEMPLOS.glob("*.xml")))
def test_las_muestras_pegadas_no_se_tocan(ejemplo):
    """Todas dicen UTF-8, con comillas dobles o simples: no hay nada que decir."""
    texto = (EJEMPLOS / ejemplo).read_text(encoding="utf-8")
    casa = _declarada().match(texto)
    assert casa, f"la expresión de la página no reconoce la declaración de {ejemplo}"
    assert _es_utf8().match(casa[2]), f"{ejemplo} diría que se ha reescrito"
    assert _como_la_pagina(texto) == texto


def test_los_blancos_de_delante_se_quitan():
    """Son del correo, y delante de la declaración hacen que no abra."""
    from validador import formato

    texto = (EJEMPLOS / "f-0006.xml").read_text(encoding="utf-8")
    assert formato.detectar(("\n\n   " + texto).encode("utf-8")).motivo
    assert formato.detectar(_como_la_pagina("\n\n   " + texto).encode("utf-8")).familia
    assert "replace(/^\\s+/" in _funcion("comoFichero")


@pytest.mark.parametrize("ejemplo, firmada", [
    ("fe-0001.xml", True), ("f-0006.xml", False), ("cii-A-0001.xml", False),
    ("edi-0001.edi", False),
])
def test_la_advertencia_de_la_firma_sale_solo_con_firma(ejemplo, firmada):
    texto = (EJEMPLOS / ejemplo).read_text(encoding="utf-8")
    assert bool(_firmada().search(texto)) is firmada
    assert "la firma no cuadrará" in _funcion("comoFichero")


def test_el_cuadro_no_amplia_la_pagina_en_un_telefono():
    estilo = re.search(r"<style>(.*?)</style>", INDEX.read_text(encoding="utf-8"), re.S)[1]
    tactil = re.search(r"@media \(pointer: coarse\) \{\s*\.pegar textarea \{([^}]*)\}", estilo)
    assert tactil and re.search(r"font-size:\s*(1rem|16px)", tactil[1]), (
        "en un teléfono el cuadro de pegar tiene letra de menos de 16 px, y "
        "Safari amplía la página al tocarlo")
