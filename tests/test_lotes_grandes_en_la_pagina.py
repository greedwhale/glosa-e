# -*- coding: utf-8 -*-
"""Un mes de facturas en la página: que se vea cómo va y que no se pinte de más.

Por qué existe
--------------
La sección de pago invita a pasar un mes entero de facturas por la página, y
el 20-10-2026 se midió qué pasaba con miles. Dos cosas:

- **La página se quedaba quieta mientras validaba**, sin pintar ni atender un
  clic y sin decir cómo iba. Python corre en el mismo hilo que pinta. Ahora el
  lote cede el turno cada décima de segundo (`LoteEnMarcha`, y el `await` de
  `INFORME` en `glosa.js`) y la página dice cuántas van.
- **Pintar cada informe abierto costaba más que validar.** Con 1.000 ficheros,
  50.000 elementos y 2,2 s de pintar; con 3.000, 21,6 s. Ahora, pasados
  `ABIERTOS_HASTA`, cada fichero sale cerrado y lo suyo se pinta al abrirlo.

Medido después, con el panel del navegador oculto y la máquina en reposo:
3.000 facturas en 31,4 s de principio a fin, informe pintado incluido, y la
página nunca más de 0,65 s sin contestar.

Aquí no hay navegador: lo que se vigila es lo que sostiene eso. El turno que
cede el Python lo prueba `test_factura.TestLoteEnMarcha`; la fila, que nadie
corra Python fuera de ella, `test_fila_del_navegador`.
"""
from __future__ import annotations

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
INDEX = RAIZ / "web" / "index.html"


def _pagina() -> str:
    return INDEX.read_text(encoding="utf-8")


def _cuerpo(codigo: str, cabecera: str) -> str:
    """De una cabecera de función a la primera llave de cierre en la columna 0."""
    arranca = codigo.index(cabecera)
    return codigo[arranca:codigo.index("\n}", arranca)]


class TestSeVeComoVa:
    def test_soltar_pasa_el_avance(self):
        cuerpo = _cuerpo(_pagina(), "async function soltar(")
        assert "Glosa.validar(ficheros, avance)" in cuerpo, (
            "soltar ya no le pasa el avance a la validación: la página vuelve "
            "a quedarse quieta sin decir cómo va")
        assert "id='leyendo-cuantas' role='status'" in cuerpo

    def test_y_no_deja_empezar_otra_encima(self):
        """La página contesta mientras lee: lo que se suelte entonces no se lee."""
        cuerpo = _cuerpo(_pagina(), "async function soltar(")
        assert re.search(r"if \(leyendo\) \{.*?return;\s*\}", cuerpo, re.S), (
            "soltar ya no se niega mientras hay un lote a medias")
        assert "ocuparse(true);" in cuerpo
        # Y se suelta pase lo que pase: si la validación revienta, la página
        # no puede quedarse ocupada para siempre.
        assert re.search(r"\} finally \{\s*ocuparse\(false\);", cuerpo)


class TestNoSePintaDeMas:
    def test_pasado_el_limite_cada_fichero_sale_cerrado(self):
        pagina = _pagina()
        assert re.search(r"const ABIERTOS_HASTA = \d+;", pagina)
        cuerpo = _cuerpo(pagina, "function pintarInforme(")
        assert "datos.documentos.length > ABIERTOS_HASTA" in cuerpo
        assert "<details class='documento' data-n='" in cuerpo

    def test_y_dice_donde_esta_el_recuento(self):
        """Con miles de ficheros cerrados, el recuento queda muy abajo."""
        pagina = _pagina()
        assert "<a href='#recuento-lote'>al final</a>" in pagina
        assert "<section class='recuento' id='recuento-lote'" in pagina

    def test_un_solo_escuchador_para_toda_la_pagina(self):
        """Uno por informe dejaba contestar al de un lote viejo.

        Provocado el 20-10-2026: tras tres lotes, el fichero 500 de uno de
        3.000 se abría vacío, porque el escuchador más viejo era el de un lote
        de 200 y contestaba primero.
        """
        pagina = _pagina()
        assert pagina.count('addEventListener("toggle"') == 1
        assert 'addEventListener("toggle"' not in _cuerpo(pagina, "function pintarInforme(")
        assert "documentosCerrados = cerrados ? datos.documentos : null;" in pagina

    def test_contar_no_copia_lo_acumulado(self):
        """`reduce` con `concat` copiaba todo en cada paso: 335 ms con 1.000."""
        cuerpo = _cuerpo(_pagina(), "function pintarInforme(")
        assert "acc.concat" not in cuerpo
        assert ".flatMap((d) => d.incidencias)" in cuerpo
