"""--recuento: lo que se manda a otra persona no lleva nada de quien factura.

Es la salida del informe de brecha: quien factura pasa Glosa-e en su equipo y
manda solo esto. La prueba de fondo no mira una lista de datos escrita a mano,
que se quedaría corta el día que salga otro: saca **todos** los textos de las
facturas de ejemplo (cada valor y cada atributo del XML, cada elemento del
EDIFACT) y los nombres de los ficheros, y falla si alguno aparece en la salida.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from lxml import etree

from test_lo_que_ensena_la_pagina import la_pagina  # noqa: F401  (la fixture)
from validador import __main__ as consola
from validador import factura

EJEMPLOS = Path(__file__).resolve().parents[1] / "ejemplos"

# Lo que una factura lleva escrito y el recuento dice con todo derecho: la
# versión de la sintaxis, que es lo que se cuenta en «Formatos».
_LO_QUE_SE_CUENTA = {"3.2.2", "3.2.1", "3.2", "D.93A", "D16B", "D.16B", "2.1"}


def _textos(camino: Path) -> set[str]:
    datos = camino.read_bytes()
    if camino.suffix == ".xml":
        textos = set()
        for elemento in etree.fromstring(datos).iter():
            if isinstance(elemento.tag, str):
                textos.add((elemento.text or "").strip())
                textos.update(v.strip() for v in elemento.attrib.values())
    else:
        textos = set(re.split(r"[+:'\n\r]", datos.decode("latin-1")))
    # Por debajo de cuatro letras salen gravedades y códigos de lista (S, EUR,
    # 380) que no identifican a nadie y pueden coincidir con la salida.
    return {x for x in textos if len(x) >= 4 and x not in _LO_QUE_SE_CUENTA}


def _con_nombres_reconocibles(destino: Path) -> list[str]:
    nombres = []
    for i, ejemplo in enumerate(sorted(EJEMPLOS.iterdir())):
        nombre = f"cliente-Zarzuela-{i:02d}{ejemplo.suffix}"
        shutil.copy(ejemplo, destino / nombre)
        nombres.append(nombre)
    return nombres


def _recuento(capsys, carpeta: Path) -> tuple[int, str]:
    codigo = consola.main([str(carpeta), "--recuento", "--hoy", "2026-10-19"])
    return codigo, capsys.readouterr().out


def test_no_sale_ningun_texto_de_las_facturas(tmp_path, capsys):
    carpeta = tmp_path / "facturas de Zarzuela SL"
    carpeta.mkdir()
    nombres = _con_nombres_reconocibles(carpeta)
    _, salida = _recuento(capsys, carpeta)
    textos = set().union(*(_textos(carpeta / n) for n in nombres))
    assert len(textos) > 80, "la prueba no ha leído las facturas"
    for prohibido in ("Zarzuela", str(tmp_path), *nombres, "B12345674"):
        assert prohibido not in salida
    fugados = sorted(x for x in textos if x in salida)
    assert not fugados, f"el recuento enseña textos de las facturas: {fugados[:10]}"


def test_cuenta_documentos_y_veces(tmp_path, capsys):
    """Las cuentas se comparan con las del lote, no con números escritos a mano."""
    nombres = _con_nombres_reconocibles(tmp_path)
    codigo, salida = _recuento(capsys, tmp_path)
    lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=None)
    assert codigo == (0 if lote.conforme else 1)
    assert lote.resumen() in salida
    for _, informe in lote.informes:
        for incidencia in informe.incidencias:
            docs = sum(1 for _, i in lote.informes
                       if any((x.gravedad, x.codigo) == (incidencia.gravedad, incidencia.codigo)
                              for x in i.incidencias))
            veces = sum(1 for _, i in lote.informes for x in i.incidencias
                        if (x.gravedad, x.codigo) == (incidencia.gravedad, incidencia.codigo))
            linea = re.search(rf"^  {incidencia.gravedad.upper():<5}  {re.escape(incidencia.codigo)} +(\d+) doc\. +(\d+) (?:vez|veces)",
                              salida, re.M)
            assert linea, incidencia.codigo
            assert (int(linea.group(1)), int(linea.group(2))) == (docs, veces), incidencia.codigo
    assert len(nombres) == len(lote.informes)


def test_el_duplicado_sale_entre_ficheros_sin_el_codigo_unico(tmp_path, capsys):
    shutil.copy(EJEMPLOS / "f-0002.xml", tmp_path / "a.xml")
    shutil.copy(EJEMPLOS / "f-0002-bis.xml", tmp_path / "b.xml")
    _, salida = _recuento(capsys, tmp_path)
    entre = salida.split("Entre ficheros (cuántas veces):")[1]
    assert re.search(r"^  ERROR  CU-10 +1 vez  ", entre, re.M)
    assert "F-2026-0002" not in salida and "2026-03-05" not in salida


def test_cuenta_los_formatos(tmp_path, capsys):
    _con_nombres_reconocibles(tmp_path)
    (tmp_path / "notas.xml").write_text("esto no es una factura", encoding="utf-8")
    _, salida = _recuento(capsys, tmp_path)
    formatos = salida.split("Formatos:")[1].split("\n\n")[0]
    assert re.search(r"^ +1  sin reconocer o sin leer$", formatos, re.M)
    assert re.search(r"^ +\d+  UBL 2\.1 \(factura 380\)$", formatos, re.M)
    assert re.search(r"^ +1  UBL 2\.1 \(abono 381\)$", formatos, re.M)
    assert re.search(r"^ +1  Facturae 3\.2\.2 \(factura FC OO\)$", formatos, re.M)
    assert re.search(r"^ +1  CII D16B \(factura 380\)$", formatos, re.M)
    assert re.search(r"^ +3  EDIFACT 96A \(factura 380\)$", formatos, re.M)


def test_sin_esquemas_lo_dice_sin_la_ruta(tmp_path, capsys):
    _con_nombres_reconocibles(tmp_path)
    codigo = consola.main([str(tmp_path), "--recuento", "--esquemas", str(tmp_path / "no-existe")])
    salida = capsys.readouterr().out
    assert "No se ha comprobado la forma: no había esquemas XSD." in salida
    assert "no-existe" not in salida
    assert codigo in (0, 1)


def test_dos_veces_en_un_documento_es_un_documento_y_dos_veces():
    """En los ejemplos ningún código sale dos veces en la misma factura, y
    contar veces por documento no ponía nada en rojo (provocado el 19-10)."""
    from validador.formato import Deteccion
    from validador.incidencias import ERROR, Incidencia, Informe

    informe = Informe(
        deteccion=Deteccion(familia="UBL", version="2.1", tipo_documento="factura"),
        incidencias=[Incidencia("BR-01", ERROR, "uno"), Incidencia("BR-01", ERROR, "otro")],
    )
    lote = factura.InformeLote(informes=[(Path("a.xml"), informe), (Path("b.xml"), Informe(
        deteccion=informe.deteccion, incidencias=[Incidencia("BR-01", ERROR, "solo")]))])
    assert re.search(r"^  ERROR  BR-01 +2 doc\. +3 veces", lote.recuento(), re.M)


# --- Las combinaciones (paso 13c) ---------------------------------------------

def _lote_a_mano(*documentos, formato=("UBL", "2.5", "factura", "380")):
    """Un lote hecho a mano: cada documento, la lista de sus (gravedad, código)."""
    from validador.formato import Deteccion
    from validador.incidencias import Incidencia, Informe

    familia, version, tipo, codigo = formato
    return factura.InformeLote(informes=[
        (Path(f"{n}.xml"), Informe(
            deteccion=Deteccion(familia=familia, version=version, tipo_documento=tipo, codigo_tipo=codigo),
            incidencias=[Incidencia(c, g, "lo que sea") for g, c in documento]))
        for n, documento in enumerate(documentos)])


def _bloque_de_combinaciones(salida: str) -> str:
    return salida.split("Combinaciones (cuántos documentos llevan exactamente lo mismo):\n")[1].split("\n\n")[0]


def test_las_combinaciones_cuentan_lo_exacto_y_no_lo_que_contiene():
    """Tres documentos con E1, y uno de ellos también con E2: E1 a secas son
    dos, no tres. Lo que llevan todos va una vez arriba."""
    from validador.incidencias import AVISO, ERROR, NOTA

    n0, e1, e2, a1 = (NOTA, "N-0"), (ERROR, "E-1"), (ERROR, "E-2"), (AVISO, "A-1")
    lote = _lote_a_mano([e1, n0], [n0, e1], [e1, e2, n0], [n0], [a1, n0])
    bloque = _bloque_de_combinaciones(lote.recuento())
    assert bloque.splitlines() == [
        "  En todos, y por eso no se repite abajo: NOTA N-0.",
        "      2  ERROR E-1",
        "      1  ERROR E-1 + ERROR E-2",
        "      1  AVISO A-1",
        "      1  nada más",
    ]


def _bloque_de_juntos(salida: str) -> str:
    return salida.split("Códigos que van siempre juntos (salen en los mismos documentos, "
                        "ni uno más ni uno menos):\n")[1].split("\n\n")[0]


def test_van_juntos_los_que_salen_en_los_mismos_documentos_y_no_los_que_cuentan_igual():
    """E-1 y E-5 salen en tres documentos cada uno, pero no en los mismos: no
    van juntos. E-2 y E-4 sí, y E-3 con A-1. N-0 y N-1 están en todos y no se
    repiten."""
    from validador.incidencias import AVISO, ERROR, NOTA

    n0, n1, a1 = (NOTA, "N-0"), (NOTA, "N-1"), (AVISO, "A-1")
    e1, e2, e3, e4, e5 = ((ERROR, f"E-{n}") for n in range(1, 6))
    # N-0 y N-1 en todos, como las dos notas que lleva cualquier factura de la
    # solución pública: van juntas, pero ya lo dice la línea de "En todos".
    lote = _lote_a_mano([e1, e2, e4, n0, n1], [e1, e2, e4, n0, n1], [e1, e5, n0, n1],
                        [e3, a1, e5, n0, n1], [e5, n1, n0])
    assert _bloque_de_juntos(lote.recuento()).splitlines() == [
        "      2 doc.  ERROR E-2 + ERROR E-4",
        "      1 doc.  ERROR E-3 + AVISO A-1",
    ]


def test_sin_nada_que_vaya_junto_lo_dice():
    from validador.incidencias import ERROR

    lote = _lote_a_mano([(ERROR, "E-1")], [(ERROR, "E-2")])
    assert _bloque_de_juntos(lote.recuento()).splitlines() == ["  Ninguno."]


def test_con_un_documento_no_hay_nada_en_comun():
    from validador.incidencias import ERROR, NOTA

    salida = _lote_a_mano([(ERROR, "E-1"), (NOTA, "N-0")]).recuento()
    assert _bloque_de_combinaciones(salida).splitlines() == ["      1  ERROR E-1 + NOTA N-0"]
    # Y con uno, todo lo suyo iría junto: la sección no sale.
    assert "Códigos que van siempre juntos" not in salida


def test_sin_nada_en_comun_dice_ningun_codigo():
    from validador.incidencias import ERROR

    bloque = _bloque_de_combinaciones(_lote_a_mano([(ERROR, "E-1")], []).recuento())
    assert bloque.splitlines() == ["      1  ERROR E-1", "      1  ningún código"]


def test_las_combinaciones_suman_los_documentos_de_los_ejemplos(tmp_path, capsys):
    """Y cada línea es exactamente lo que llevan esos documentos, comparado con
    el lote y no con números escritos a mano."""
    _con_nombres_reconocibles(tmp_path)
    _, salida = _recuento(capsys, tmp_path)
    lote = factura.validar_lote(sorted(tmp_path.iterdir()), hoy=None)
    bloque = _bloque_de_combinaciones(salida)
    cuentas = [int(m.group(1)) for m in re.finditer(r"^ +(\d+)  ", bloque, re.M)]
    assert sum(cuentas) == len(lote.informes)
    # Y lo de arriba, en todos de verdad: ningún documento del lote sin ello.
    arriba = re.search(r"^  En todos, y por eso no se repite abajo: (.*)\.$", bloque, re.M)
    if arriba:
        for escrito in arriba.group(1).split(" + "):
            gravedad, codigo = escrito.split(" ", 1)
            assert all(any((i.gravedad.upper(), i.codigo) == (gravedad, codigo) for i in informe.incidencias)
                       for _, informe in lote.informes), escrito


def test_con_varios_formatos_cada_linea_dice_el_suyo(tmp_path, capsys):
    """La rectificativa (384) se separa de las demás, que es para lo que está."""
    ubl = (EJEMPLOS / "f-0001.xml").read_text(encoding="utf-8")
    (tmp_path / "a.xml").write_text(ubl, encoding="utf-8")
    viejo = "<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"
    assert ubl.count(viejo) == 1
    (tmp_path / "b.xml").write_text(ubl.replace(viejo, "<cbc:InvoiceTypeCode>384</cbc:InvoiceTypeCode>"), encoding="utf-8")
    _, salida = _recuento(capsys, tmp_path)
    bloque = _bloque_de_combinaciones(salida)
    assert re.search(r"^ +1  UBL 2\.1 \(factura 380\)  ", bloque, re.M), bloque
    assert re.search(r"^ +1  UBL 2\.1 \(factura 384\)  ", bloque, re.M), bloque


def test_un_tipo_que_no_es_un_codigo_no_sale(tmp_path, capsys):
    """El tipo es texto del documento: si trae otra cosa, no se enseña."""
    ubl = (EJEMPLOS / "f-0001.xml").read_text(encoding="utf-8")
    viejo = "<cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"
    (tmp_path / "a.xml").write_text(
        ubl.replace(viejo, "<cbc:InvoiceTypeCode>Zarzuela 2026</cbc:InvoiceTypeCode>"), encoding="utf-8")
    _, salida = _recuento(capsys, tmp_path)
    assert "Zarzuela" not in salida
    assert re.search(r"^ +1  UBL 2\.1 \(factura tipo sin código\)$", salida, re.M), salida


# --- En la web (paso 13b) ----------------------------------------------------

PORTADA = Path(__file__).resolve().parents[1] / "web" / "index.html"


def test_la_pagina_trae_el_mismo_recuento_y_sin_nada_de_las_facturas(tmp_path, la_pagina):  # noqa: F811
    """El Python de `glosa.js`, tal cual, con las facturas de ejemplo soltadas
    con nombres reconocibles: el recuento que recibe la página es el del lote,
    y no lleva ningún texto de dentro, ningún nombre ni la carpeta."""
    import json

    ficheros = {
        f"cliente-Zarzuela-{i:02d}{ejemplo.suffix}": ejemplo.read_bytes()
        for i, ejemplo in enumerate(sorted(EJEMPLOS.iterdir()))
    }
    datos = json.loads(la_pagina(ficheros))
    recuento = datos["recuento"]
    espacio = la_pagina.espacio
    lote, c, a = espacio["_lote"], espacio["_c"], espacio["_a"]
    assert recuento == lote.recuento(forma=not c.vacio, anclas=not a.vacio)
    assert recuento.startswith("Recuento de Glosa-e\n")
    textos = set().union(*(_textos(EJEMPLOS / e.name) for e in sorted(EJEMPLOS.iterdir())))
    assert len(textos) > 80, "la prueba no ha leído las facturas"
    for prohibido in ("Zarzuela", la_pagina.carpeta.as_posix(), str(la_pagina.carpeta),
                      "/entrada/", *ficheros):
        assert prohibido not in recuento
    fugados = sorted(x for x in textos if x in recuento)
    assert not fugados, f"el recuento de la página enseña textos de las facturas: {fugados[:10]}"


def test_la_portada_lo_pinta_escapado_y_lo_deja_copiar():
    """Lo que no puede faltar en `pintarInforme`: el texto escapado dentro del
    `pre` (un código con < rompería el marcado), el botón enganchado después de
    pintar, y la salida a mano cuando el portapapeles no deja."""
    portada = PORTADA.read_text(encoding="utf-8")
    pintar = portada.split("function pintarInforme(datos) {")[1].split("\n}\n")[0]
    assert "<pre id='recuento-texto'>\" + escapar(datos.recuento) + \"</pre>" in pintar
    assert pintar.index('$("informe").innerHTML = partes.join("");') < pintar.index(
        '$("copiar-recuento").addEventListener("click", copiarRecuento)')
    copiar = portada.split("function copiarRecuento() {")[1].split("\n}\n")[0]
    assert "navigator.clipboard.writeText(texto).then(" in copiar and ", aMano);" in copiar
    assert "if (!navigator.clipboard || !navigator.clipboard.writeText) { aMano(); return; }" in copiar
