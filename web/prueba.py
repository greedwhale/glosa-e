"""Banco de pruebas: comprueba que Factura-e funciona dentro del navegador.

No basta con que Pyodide arranque. Lo que hay que saber es si la compilacion
de lxml para WebAssembly trae todo lo que el validador usa, en particular el
soporte de esquemas XSD, que libxml2 se puede compilar sin el.
"""
import json
import os
import time
from datetime import date

BASE = os.environ.get("EJEMPLOS", "/ejemplos")
HOY = date(2026, 9, 20)
resultados = []


def comprobar(nombre, critica=False):
    def envoltorio(fn):
        arranque = time.perf_counter()
        try:
            detalle = fn() or "correcto"
            ok = True
        except Exception as error:
            detalle = "{}: {}".format(type(error).__name__, error)
            ok = False
        resultados.append({
            "nombre": nombre,
            "ok": ok,
            "critica": critica,
            "detalle": str(detalle),
            "ms": round((time.perf_counter() - arranque) * 1000, 1),
        })
        return fn
    return envoltorio


@comprobar("lxml carga en WebAssembly", critica=True)
def _():
    from lxml import etree
    return "lxml {} - libxml2 {}".format(
        ".".join(str(n) for n in etree.LXML_VERSION),
        ".".join(str(n) for n in etree.LIBXML_VERSION),
    )


@comprobar("libxml2 trae soporte de esquemas XSD", critica=True)
def _():
    # La pregunta del millon: libxml2 se puede compilar sin schemas, y
    # esquema.py entero depende de etree.XMLSchema.
    from lxml import etree
    xsd = b"""<?xml version="1.0"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="factura">
        <xs:complexType><xs:sequence>
          <xs:element name="total" type="xs:decimal"/>
        </xs:sequence></xs:complexType>
      </xs:element>
    </xs:schema>"""
    esquema = etree.XMLSchema(etree.fromstring(xsd))
    bueno = etree.fromstring(b"<factura><total>121.00</total></factura>")
    malo = etree.fromstring(b"<factura><total>ciento veintiuno</total></factura>")
    assert esquema.validate(bueno), "rechaza un documento valido"
    assert not esquema.validate(malo), "acepta un documento invalido"
    assert esquema.error_log, "no hay error_log, y de ahi salen los mensajes"
    return "compila, acepta, rechaza y explica por que"


@comprobar("el paquete validador importa", critica=True)
def _():
    import validador
    from validador import factura, esquema, en16931, codigo_unico, iva, nif
    return "todos los modulos"


@comprobar("el parser endurecido no expande entidades", critica=True)
def _():
    # XXE: si esto expande, una factura ajena puede leer ficheros.
    from lxml import etree
    from validador.formato import parser
    bomba = (b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "SECRETO">]>'
             b"<r>&x;</r>")
    raiz = etree.fromstring(bomba, parser=parser())
    texto = etree.tostring(raiz, encoding="unicode")
    assert "SECRETO" not in texto, "la entidad se expandio: " + texto
    return "la entidad no se expande"


@comprobar("reconoce el formato de un fichero real")
def _():
    from validador.formato import detectar_archivo
    d = detectar_archivo(BASE + "/f-0001.xml")
    assert d, d.motivo
    return "{} - {}".format(d.familia, d.version or "sin version")


@comprobar("una factura correcta sale conforme", critica=True)
def _():
    from validador import factura
    informe = factura.validar_archivo(BASE + "/f-0001.xml", hoy=HOY)
    assert informe.validado, "no se ha llegado a mirar"
    assert informe.conforme, informe.detalle()
    return informe.resumen()


@comprobar("un abono correcto sale conforme")
def _():
    from validador import factura
    informe = factura.validar_archivo(BASE + "/r-0001.xml", hoy=HOY)
    assert informe.conforme, informe.detalle()
    return informe.resumen()


@comprobar("una factura de otro formato (CII) tambien")
def _():
    from validador import factura
    informe = factura.validar_archivo(BASE + "/cii-A-0001.xml", hoy=HOY)
    assert informe.validado, "no se ha reconocido"
    return informe.resumen()


@comprobar("una factura rota se caza", critica=True)
def _():
    from validador import factura
    with open(BASE + "/f-0001.xml", "rb") as f:
        datos = f.read()
    roto = datos.replace(
        b'<cbc:PayableAmount currencyID="EUR">121.00',
        b'<cbc:PayableAmount currencyID="EUR">999.00',
    )
    assert roto != datos, "no se ha llegado a romper la factura"
    informe = factura.validar(roto, hoy=HOY)
    assert not informe.conforme, "un total falso ha pasado sin queja"
    return "; ".join(i.codigo for i in informe.errores)


@comprobar("el informe se lee en castellano, con tildes")
def _():
    from validador import factura
    with open(BASE + "/f-0001.xml", "rb") as f:
        datos = f.read()
    roto = datos.replace(b"<cbc:ID>F-2026-0001</cbc:ID>", b"<cbc:ID></cbc:ID>")
    texto = factura.validar(roto, hoy=HOY).detalle(norma=factura.origen)
    assert "\u00fa" in texto or "\u00f3" in texto or "\u00e9" in texto, (
        "no hay ni una tilde, algo se ha comido el UTF-8: " + texto[:200])
    return texto.splitlines()[2].strip() if len(texto.splitlines()) > 2 else texto


@comprobar("sin esquemas XSD sigue funcionando, avisando")
def _():
    from validador.esquema import Catalogo
    from pathlib import Path
    catalogo = Catalogo(carpeta=Path("/no-existe"))
    assert catalogo.vacio, "dice que tiene esquemas y no los tiene"
    return "catalogo vacio detectado, sin reventar"


@comprobar("un lote entero de una vez")
def _():
    from validador import factura
    import glob
    rutas = sorted(glob.glob(BASE + "/*.xml"))
    lote = factura.validar_lote(rutas, hoy=HOY)
    return "{} -> {}".format(len(rutas), lote.resumen())


json.dumps(resultados)
