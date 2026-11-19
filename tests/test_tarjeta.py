# -*- coding: utf-8 -*-
"""Las tarjetas sociales dicen lo que dice su página, con la marca de la página.

Por qué existe
--------------
Hasta el 19-11-2026 había una sola tarjeta, `web/marca/tarjeta.png`,
versionada ya hecha, y su guion escribía el titular de la portada a mano. El
23-09-2026 la hoja cambió de gris, el guion se puso al día y el PNG no, y la
tarjeta que veía quien pegaba el enlace decía una cosa y la hoja otra. Aquí se
comparaba la publicada con la que pintaba el guion.

Desde ese día hay una por página y se pintan al montar, de la página montada
(el porqué, en `validador/tarjetas.py`), así que ya no hay una publicada que
pueda quedarse atrás. Lo que queda por vigilar es lo que se copia a mano: la
marca, de la hoja, y la glosa del folio, del glosario. Y que cada molde sepa
leer las páginas de verdad: si cambia cómo se escribe una ficha o un artículo,
tiene que ponerse rojo aquí y no al montar el sitio en el despliegue.
"""
from __future__ import annotations

import ast
import hashlib
import html
import re
from pathlib import Path

import pytest

from validador import bitacora, pagina_incidencias, tarjetas
from validador.codigos import codigos_del_paquete

RAIZ = Path(__file__).resolve().parents[1]
GUION = RAIZ / "validador" / "tarjetas.py"
WEB = RAIZ / "web"
LETRA = tarjetas.Letra((WEB / "letra" / "literata.woff2").read_bytes())


def test_la_portada_dice_su_titular_y_su_lema():
    """La tarjeta promete lo que la página cumple: si dijera otra cosa sería
    un anzuelo. El salto de línea del titular cuenta como un espacio."""
    portada = (WEB / "index.html").read_text(encoding="utf-8")
    h1 = re.search(r"<h1>(.*?)</h1>", portada, re.S)[1].replace("<br>", " ")
    lema = re.search(r'<p class="lema"><b>(.*?)</b>', portada, re.S)[1]
    _, alt = tarjetas._pintar("index.html", portada, LETRA, set(), set())
    assert alt == " ".join(f"{h1} {lema}".split())


def test_cada_ficha_dice_su_codigo_su_gravedad_y_su_primera_frase():
    """Se lee de la ficha escrita como la escribe `pagina_incidencias`."""
    from validador import glosario

    todos = codigos_del_paquete()
    uno = next(c for c in todos if c.codigo == "BR-CO-15")
    escrita = pagina_incidencias._ficha(uno, todos)
    nombre = pagina_incidencias.nombre_de(uno.codigo)
    _, alt = tarjetas._pintar(nombre, escrita, LETRA, {nombre}, set())
    frase = tarjetas.primera_frase(glosario.CODIGOS["BR-CO-15"])
    assert alt == f"BR-CO-15 (error, EN 16931): {frase}"


def test_una_ficha_de_la_casa_dice_de_quien_es_el_criterio():
    """De la casa se entiende en la página; suelto en una tarjeta, no."""
    todos = codigos_del_paquete()
    for uno in todos:
        if pagina_incidencias._norma(uno.codigo)[0] == "De la casa":
            break
    else:
        pytest.skip("no queda ningún código de la casa")
    nombre = pagina_incidencias.nombre_de(uno.codigo)
    _, alt = tarjetas._pintar(nombre, pagina_incidencias._ficha(uno, todos), LETRA,
                              {nombre}, set())
    assert "Criterio de Glosa-e" in alt and "De la casa" not in alt


@pytest.mark.parametrize(
    "entrada", bitacora.leer_entradas(WEB / bitacora.CARPETA), ids=lambda e: e.slug)
def test_cada_articulo_dice_su_titulo_y_su_fecha(entrada):
    """La tarjeta de un artículo lee su `<h1>` y la fecha de justo delante;
    tienen que ser los que el artículo declara en `data-titulo` y
    `data-fecha`, que son los del índice, el canal y el `<title>`."""
    texto = (f'<meta name="description" content="{html.escape(entrada.entradilla)}">\n'
             + entrada.cuerpo)
    _, alt = tarjetas._pintar(entrada.nombre, texto, LETRA, set(), {entrada.nombre})
    assert alt == f"Blog de Glosa-e, {entrada.dicha}: {entrada.titulo}"


@pytest.mark.parametrize("pagina", sorted(
    p.name for p in WEB.glob("*.html")
    if p.name not in tarjetas.SIN_TARJETA + ("index.html", bitacora.NOMBRE)))
def test_el_titular_de_cada_pagina_cabe(pagina):
    texto = (WEB / pagina).read_text(encoding="utf-8")
    imagen, alt = tarjetas._pintar(pagina, texto, LETRA, set(), set())
    assert imagen.size == (tarjetas.ANCHO, tarjetas.ALTO) and alt


def test_un_titular_que_no_cabe_no_se_pinta():
    """Cortado no se publica: se dice, y el titular se acorta a mano."""
    with pytest.raises(tarjetas.TarjetaMal, match="no cabe"):
        tarjetas.pagina("Un titular larguísimo " * 12, LETRA)
    with pytest.raises(tarjetas.TarjetaMal, match="no cabe"):
        tarjetas.portada("Un titular larguísimo " * 12, "El lema.", LETRA)


def test_sin_titular_no_hay_tarjeta():
    with pytest.raises(tarjetas.TarjetaMal, match="<h1>"):
        tarjetas._pintar("legal.html", "<p>sin titular</p>", LETRA, set(), set())


def test_la_huella_es_de_los_pixeles_y_no_de_como_se_comprimen(tmp_path):
    """La dirección de la tarjeta tiene que salir igual montando aquí que en
    el alojamiento, o `--avisar-indexnow` vería todas las páginas distintas.
    Los mismos píxeles comprimidos de otra manera son otros bytes y la misma
    huella."""
    from PIL import Image

    def de_los_pixeles(ruta):
        leida = Image.open(ruta)
        return hashlib.sha256(f"{leida.width}x{leida.height}".encode()
                              + bytes(leida.getpalette()) + leida.tobytes()).hexdigest()[:8]

    huella = tarjetas._guardar(tarjetas.pagina("Un titular", LETRA), tmp_path / "a.png")
    Image.open(tmp_path / "a.png").save(tmp_path / "b.png", compress_level=1)
    assert (tmp_path / "a.png").read_bytes() != (tmp_path / "b.png").read_bytes()
    assert huella == de_los_pixeles(tmp_path / "a.png") == de_los_pixeles(tmp_path / "b.png")


def test_sin_pillow_se_sabe_antes_de_montar(monkeypatch):
    monkeypatch.setattr(tarjetas, "Image", None)
    assert "Pillow" in tarjetas.que_falta(WEB / "letra" / "literata.woff2")


def test_una_letra_que_no_se_abre_se_sabe_antes_de_montar(tmp_path):
    (tmp_path / "literata.woff2").write_bytes(b"wOF2 de mentira")
    assert "no sabe abrir" in tarjetas.que_falta(tmp_path / "literata.woff2")
    assert tarjetas.que_falta(WEB / "letra" / "literata.woff2") is None


def _constantes_del_guion() -> dict:
    """Las cifras de la marca de `tarjetas.py`, leídas de su texto.

    Se leen sin importarlo porque son las asignaciones lo que se compara: una
    cifra calculada en otro sitio no sería la copia a mano que hay que vigilar.
    """
    valores = {}
    for nodo in ast.parse(GUION.read_text(encoding="utf-8")).body:
        if isinstance(nodo, ast.Assign):
            for destino in nodo.targets:
                nombres = destino.elts if isinstance(destino, ast.Tuple) else [destino]
                try:
                    valor = ast.literal_eval(nodo.value)
                except ValueError:
                    continue
                if len(nombres) == 1:
                    valores[nombres[0].id] = valor
                else:
                    valores.update({n.id: v for n, v in zip(nombres, valor)})
    return valores


def _trazos(d: str) -> list[tuple[tuple[float, float], ...]]:
    """Los trazos de un `d` de SVG con M, H, V, h y v, que es lo que usa el signo."""
    trazos, actual, x, y = [], [], 0.0, 0.0
    for orden, cifras in re.findall(r"([MHVhv])\s*([-\d.\s]+)", d):
        n = [float(c) for c in cifras.split()]
        if orden == "M":
            if actual:
                trazos.append(tuple(actual))
            x, y = n
            actual = [(x, y)]
            continue
        if orden == "H":
            x = n[0]
        elif orden == "V":
            y = n[0]
        elif orden == "h":
            x += n[0]
        elif orden == "v":
            y += n[0]
        actual.append((x, y))
    trazos.append(tuple(actual))
    return trazos


def test_la_marca_de_la_tarjeta_es_la_de_la_cabecera():
    """La marca de la tarjeta sale de las cifras de `.marca` en la hoja.

    Hasta el 24-09-2026 la tarjeta pintaba la marca del favicon —el bloque
    gris, dos líneas blancas, el nombre en 400— y la cabecera, desde el
    23-09-2026, el signo en azul con tres líneas y el nombre en 600. Nadie lo
    vio porque las dos se escriben en sitios distintos. Aquí se comparan.
    """
    hoja = (RAIZ / "web" / "glosa.css").read_text(encoding="utf-8")
    guion = _constantes_del_guion()

    antes = re.search(r"^\.marca::before \{(.*?)^\}", hoja, re.S | re.M)[1]
    mascara = re.search(r'mask: url\("data:image/svg\+xml,([^"]+)"\)', antes)[1]
    mascara = mascara.replace("%3C", "<").replace("%3E", ">")
    caja = [float(c) for c in re.search(r"viewBox='([^']+)'", mascara)[1].split()]
    assert tuple(caja[2:]) == guion["SIGNO_CAJA"], "la caja del signo no es la de la hoja"
    trazos = [t for d in re.findall(r"d='([^']+)'", mascara) for t in _trazos(d)]
    assert trazos == [tuple(map(tuple, t)) for t in guion["SIGNO_TRAZOS"]], (
        f"la tarjeta dibuja otro signo que la cabecera:\n  hoja:    {trazos}\n"
        f"  tarjeta: {guion['SIGNO_TRAZOS']}")
    assert float(re.search(r"stroke-width='([\d.]+)'", mascara)[1]) == guion["SIGNO_GROSOR"]
    assert "background: var(--acento)" in antes, "el signo de la cabecera ya no es del acento"
    assert re.search(r"signo: str = ACENTO", GUION.read_text(encoding="utf-8")), (
        "el signo de la tarjeta ya no se pinta en el acento")
    rem = lambda propiedad: float(re.search(propiedad + r":\s*([\d.]+)rem", antes)[1])
    assert (rem("width"), rem("height")) == guion["SIGNO_REM"]

    marca = re.search(r"^\.marca \{(.*?)^\}", hoja, re.S | re.M)[1]
    assert float(re.search(r"gap:\s*([\d.]+)rem", marca)[1]) == guion["HUECO_REM"]
    nombre = re.search(r"^\.marca \.nombre \{(.*?)\}", hoja, re.S | re.M)[1]
    peso, tamano = re.search(r"font:\s*(\d+)\s+([\d.]+)rem", nombre).groups()
    assert (int(peso), float(tamano)) == (guion["NOMBRE_PESO"], guion["NOMBRE_REM"])
    espaciado = float(re.search(r"letter-spacing:\s*(-?[\d.]+)em", nombre)[1])
    assert espaciado == guion["NOMBRE_ESPACIADO"]


def test_la_glosa_de_la_tarjeta_es_la_del_glosario():
    """La tarjeta enseña una glosa, y tiene que ser una que la página escribe.

    Desde el 25-09-2026 la tarjeta es un trozo de factura con su glosa al
    margen. Una tarjeta que explicara un código de otra manera que la página,
    o con otra gravedad, sería la peor forma de presentarse: lo primero que se
    ve de Glosa-e diciendo algo que Glosa-e no dice.
    """
    from validador import glosario
    from validador.codigos import codigos_del_paquete

    guion = _constantes_del_guion()
    codigo, frase = guion["GLOSA_CODIGO"], guion["GLOSA_FRASE"]
    suyo = {c.codigo: c for c in codigos_del_paquete()}.get(codigo)
    assert suyo, f"la tarjeta glosa {codigo}, que el validador no emite"
    assert suyo.gravedades == ("error",), (
        f"la tarjeta dice ERROR y {codigo} sale como {suyo.gravedades}")
    assert glosario.CODIGOS.get(codigo, "").startswith(frase), (
        f"la tarjeta explica {codigo} con «{frase}», y el glosario no empieza así")
    # Y la cuenta: el total declarado no puede ser el bueno, o no hay glosa.
    base, tipo, total = guion["BASE"], guion["TIPO"], guion["TOTAL_DECLARADO"]
    assert base * (100 + tipo) / 100 != total, "el total de muestra cuadra: no hay error que glosar"
