# -*- coding: utf-8 -*-
"""Lo que la página cita de fuera, o invita a comprobar, se dice con su condición.

Por qué existe
--------------
El 24-09-2026 entraron tres cosas que la página no afirma de sí misma sino de
fuera, o que invita a comprobar, y las tres se desvían si nadie las vigila:

- **«Desconecta la red y suelta tu factura».** Se midió antes de escribirlo:
  con la página cargada y el servidor apagado, las cuatro facturas de muestra
  dieron el mismo informe y ninguna petición. Pero solo vale con el validador
  ya cargado; antes de «Listo», sin red no arranca. Así que la invitación solo
  puede salir en la rama en que ha arrancado.
- **El HTTP Observatory de Mozilla.** Es un tercero que mide y su nota cambia:
  una cifra sin fecha acabaría diciendo lo que el Observatory ya no dice.
- **VALIDe**, el servicio oficial de validación de firmas. Hace lo que aquí no
  se puede porque allí la factura se envía; recomendarlo sin decirlo sería
  mandar a alguien a subir su factura sin avisarle, justo desde la página que
  presume de no hacerlo.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"
FECHA = re.compile(r"\b\d{1,2} de (enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
                   r"septiembre|octubre|noviembre|diciembre) de \d{4}\b|\b\d{2}-\d{2}-\d{4}\b")


def _parrafos(pagina: str) -> list[str]:
    texto = re.sub(r"<!--.*?-->", "", (WEB / pagina).read_text(encoding="utf-8"), flags=re.S)
    return [" ".join(p.split()) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", texto, re.S)]


def _empezar() -> str:
    texto = (WEB / "index.html").read_text(encoding="utf-8")
    principio = texto.index("async function empezar() {")
    return texto[principio:texto.index("\n}\n", principio)]


def test_la_prueba_sin_red_solo_se_ofrece_con_el_validador_cargado():
    empezar = _empezar()
    assert "Desconecta la red" in empezar, "la nota de «Listo» ya no invita a desconectar"
    arrancado = empezar[:empezar.index("} catch (error) {")]
    assert "Desconecta la red" in arrancado[arrancado.index("listo = true;"):], (
        "la invitación a desconectar sale antes de que el validador haya "
        "arrancado, y sin red no arranca: solo vale después de «Listo»")
    assert arrancado.count("Desconecta la red") == 1
    # La otra rama, sin el paquete, no promete lo mismo: allí se dice que
    # solo se comprueba el contenido, y eso es lo que tiene que leerse.
    sin_paquete = re.search(r':\s*"Sin el paquete de esquemas y anclas[^"]*"', arrancado)
    assert sin_paquete and "red" not in sin_paquete[0]


@pytest.mark.parametrize("pagina", ["index.html", "legal.html"])
def test_quien_invita_a_desconectar_dice_cuando(pagina):
    for parrafo in _parrafos(pagina):
        if re.search(r"desconecta la red", parrafo, re.I):
            assert "<i>Listo</i>" in parrafo, (
                f"{pagina} invita a desconectar la red sin decir que es con la "
                f"página ya cargada: «{parrafo[:120]}…»")


@pytest.mark.parametrize("pagina", sorted(p.name for p in WEB.glob("*.html")))
def test_el_observatory_se_cita_con_fecha(pagina):
    for parrafo in _parrafos(pagina):
        if "Observatory" in parrafo and re.search(r"\bA\+|\d+ puntos", parrafo):
            assert FECHA.search(parrafo), (
                f"{pagina} cita la nota del Observatory sin fecha, y esa nota "
                f"cambia: «{parrafo[:120]}…»")


def test_el_observatory_enlaza_la_medicion_de_este_sitio():
    politica = (WEB / "legal.html").read_text(encoding="utf-8")
    assert ("https://developer.mozilla.org/en-US/observatory/analyze?host=www.glosa-e.com"
            in politica), "la cita del Observatory ya no enlaza su medición de www.glosa-e.com"


@pytest.mark.parametrize("pagina", sorted(p.name for p in WEB.glob("*.html")))
def test_quien_recomienda_valide_dice_que_alli_se_envia(pagina):
    for parrafo in _parrafos(pagina):
        if "valide.redsara.es" in parrafo:
            assert re.search(r"se env[ií]a|se sube", parrafo), (
                f"{pagina} recomienda VALIDe sin decir que allí la factura se "
                f"envía: «{parrafo[:120]}…»")
