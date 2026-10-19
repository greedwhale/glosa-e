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
    assert re.search(r"^ +\d+  UBL 2\.1 \(factura\)$", formatos, re.M)


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
