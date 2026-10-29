"""Saca a tabla el anexo I de la orden de la solución pública, del XML del BOE.

Qué es ese anexo y por qué hace falta leerlo
--------------------------------------------
El RD 238/2026 admite cuatro sintaxis (artículo 7.1), pero la solución pública
de la AEAT **toma UBL 2.5 como referencia**, y no UBL a secas: una especificación
española propia con campos que la EN 16931 no tiene —retenciones, suplidos,
minoraciones, impuestos y tasas cobrados en nombre de un tercero, el QR
fiscal, la rectificativa—. No se publica como esquema ni como esquematrón: se
publica como **una tabla dentro de una orden ministerial**, la Orden
HAC/1028/2026, en el BOE del 05-10-2026.

Así que o se lee la tabla o no se sabe qué hay que comprobar. Esto la lee.

Por qué del XML del BOE y no del PDF
------------------------------------
Hasta el 11-10-2026 esto leía el PDF del proyecto de orden de abril, por
coordenadas: el modo `layout` de pypdf partía `BT-179` en dos renglones y
metía el `21` de `BT-ES-21` en la columna del término, y lo que salía había
que contrastarlo con una segunda lectura que no compartiera código. El BOE
publica cada disposición también en XML, y ahí la tabla **es una tabla**:
`<table>`, `<tr>`, `<td>`. No hay geometría que adivinar, y el texto es el
oficial, no una conversión.

Lo único que hay que saber del XML:

- **Una celda puede llevar varios `<p>`**, uno por renglón del original. Se
  juntan con un espacio. Por eso una ruta partida en dos renglones sale con un
  espacio dentro —`/in:Invoice/cac:PrepaidPayment/ cbc:PaidDate`— y se deja
  así: es lo que dice el texto. Quitarlo es cosa de quien interpreta la ruta
  (`validador/sintaxis.py`), y allí se dice.
- **Las listas llevan el título de dos maneras.** Las que no tienen
  calificador lo llevan en el `<caption>` de su tabla. Las que sí (L3A, L3B,
  L3C, L7, L8 y L10) lo llevan en un párrafo suelto, seguido de una tabla de
  una fila, «CALIFICADOR» y su valor, y después la de los valores.
- **Lo que no es del anexo I se queda fuera.** El anexo II, con sus propias
  tablas y su propia «L1 – Motivos de rechazo», empieza en el párrafo
  «ANEXO II». La segunda tabla del anexo I, el mensaje de anulación, no tiene
  columna de identificador: la saca `herramientas/mensajes.py`, con las del
  anexo II, a `validador/mensajes_es.py`.

Esto no viaja en la rueda
-------------------------
Vive fuera de `validador/` a propósito: se corre una vez, cuando cambia la
orden, y lo que viaja es su resultado, `validador/cius_es.py`.

Cómo se usa
-----------
    python -m herramientas.anexo_i anexos/orden-hac-1028-2026.xml

y reescribe `validador/cius_es.py`. El XML se baja de
https://www.boe.es/diario_boe/xml.php?id=BOE-A-2026-20587 y no se versiona; lo
que se versiona es la tabla, con la huella SHA-256 del XML del que salió al
lado, para que una corrección de errores no se cuele sin que nadie se entere.
"""

import collections
import hashlib
import json
import pathlib
import re

from lxml import etree

# Dónde empieza y dónde acaba el anexo I dentro del texto de la orden.
ANEXO_I = "ANEXO I"
ANEXO_II = "ANEXO II"

CABECERA = ["ID", "Nivel", "Cardinalidad"]
TITULO_LISTA = re.compile(r"^(L\d+(?:\.[A-Z])?[A-Z]?)\s*[–-]\s*(.+)$")
# Los dos valores que el anexo fija en la descripción de BT-23 y de BT-24.
FIJADO = re.compile(r"Adoptará el valor:\s*(\S+)")


def _celda(nodo):
    """El texto de una celda, con un espacio entre sus renglones."""
    parrafos = [p for p in nodo if p.tag == "p"]
    trozos = ["".join(p.itertext()) for p in parrafos] if parrafos else ["".join(nodo.itertext())]
    return " ".join(" ".join(trozos).split())


def _filas(tabla):
    return [[_celda(c) for c in tr if c.tag in ("td", "th")] for tr in tabla.iter("tr")]


def _del_anexo_i(camino):
    """Los nodos del texto de la orden que son del anexo I, en orden."""
    texto = etree.parse(str(camino)).getroot().find("texto")
    dentro, nodos = False, []
    for nodo in texto:
        if nodo.tag == "p" and nodo.get("class") == "anexo_num":
            rotulo = _celda(nodo)
            if rotulo == ANEXO_I:
                dentro = True
                continue
            if rotulo == ANEXO_II:
                break
        if dentro:
            nodos.append(nodo)
    if not nodos:
        raise ValueError(f"no se encuentra «{ANEXO_I}» en {camino}")
    return nodos


def campos(camino):
    """Las filas de la tabla del mensaje de alta, en orden.

    Es la única tabla del anexo I cuya cabecera empieza por «ID», «Nivel» y
    «Cardinalidad». Si hubiera dos, o ninguna, el anexo ha cambiado de forma y
    esto no puede saber cuál es la buena.
    """
    tablas = [_filas(n) for n in _del_anexo_i(camino) if n.tag == "table"]
    principales = [f for f in tablas if f and f[0][:3] == CABECERA]
    if len(principales) != 1:
        raise ValueError(f"se esperaba una tabla con la cabecera {CABECERA} y hay {len(principales)}")
    salida = []
    for fila in principales[0][1:]:
        if len(fila) != 7:
            raise ValueError(f"fila con {len(fila)} celdas y no 7: {fila}")
        ident, nivel, cardinalidad, termino, descripcion, tipo, ruta = fila
        salida.append({
            "id": ident.replace(" ", ""),
            "nivel": nivel.count("+"),
            "cardinalidad": cardinalidad.replace(" ", ""),
            "termino": termino,
            "descripcion": descripcion,
            "tipo": tipo,
            "ruta": ruta,
        })
    return salida


def listas(camino):
    """Las listas de códigos del anexo I, de L1 a L10.

    El título sale del `<caption>` o del párrafo que va delante; el
    calificador, de la tabla de una fila que hay entre el título y los
    valores. Un título que no llega a tener valores, o unos valores sin
    título, son un anexo con otra forma, y se dice en vez de adivinar.
    """
    salida, titulo, calificador = {}, None, ""
    for nodo in _del_anexo_i(camino):
        if nodo.tag == "p":
            encontrado = TITULO_LISTA.match(_celda(nodo))
            if encontrado:
                if titulo:
                    raise ValueError(f"la lista {titulo[0]} no trae valores")
                titulo, calificador = encontrado.groups(), ""
            continue
        if nodo.tag != "table":
            continue
        filas = _filas(nodo)
        encontrado = TITULO_LISTA.match(_celda(nodo.find("caption"))) if nodo.find("caption") is not None else None
        if encontrado:
            if titulo:
                raise ValueError(f"la lista {titulo[0]} no trae valores")
            titulo, calificador = encontrado.groups(), ""
        if len(filas) == 1 and filas[0][:1] == ["CALIFICADOR"]:
            calificador = filas[0][1]
            continue
        if filas and filas[0][:1] == ["Valores"]:
            if not titulo:
                raise ValueError(f"una tabla de valores sin título de lista: {filas[:2]}")
            clave, nombre = titulo
            if clave in salida:
                raise ValueError(f"la lista {clave} sale dos veces en el anexo I")
            salida[clave] = {
                "titulo": nombre,
                "calificador": calificador,
                "valores": [{"valor": f[0], "descripcion": f[1]} for f in filas[1:]],
            }
            titulo, calificador = None, ""
    if titulo:
        raise ValueError(f"la lista {titulo[0]} no trae valores")
    return salida


def fijado(filas, identificador):
    """El valor que la descripción de la fila manda adoptar, si es uno solo."""
    descripciones = [f["descripcion"] for f in filas if f["id"] == identificador]
    valores = [v for d in descripciones for v in FIJADO.findall(d)]
    if len(valores) != 1:
        raise ValueError(f"{identificador}: se esperaba un valor fijado y hay {valores}")
    return valores[0]


def metadatos(camino):
    """Lo que el propio BOE dice del documento: de dónde sale cada cosa."""
    datos = etree.parse(str(camino)).getroot().find("metadatos")
    return {clave: (datos.findtext(clave) or "").strip() for clave in (
        "identificador", "numero_oficial", "fecha_publicacion", "diario_numero",
        "fecha_vigencia", "url_eli")}


def huella(camino):
    return hashlib.sha256(pathlib.Path(camino).read_bytes()).hexdigest()


def _fecha(aaaammdd):
    return f"{aaaammdd[6:8]}-{aaaammdd[4:6]}-{aaaammdd[:4]}"


def _cita(s):
    return json.dumps(s, ensure_ascii=False)


def escribe_modulo(camino_xml, destino):
    """Reescribe `validador/cius_es.py` con lo que diga este XML."""
    filas = campos(camino_xml)
    codigos = listas(camino_xml)
    datos = metadatos(camino_xml)
    repetidos = {k: v for k, v in
                 collections.Counter(f["id"] for f in filas).items() if v > 1}

    trozos = [CABEZA % {
        "orden": datos["numero_oficial"],
        "boe": datos["identificador"],
        "numero": datos["diario_numero"],
        "publicada": _fecha(datos["fecha_publicacion"]),
        "vigencia": _fecha(datos["fecha_vigencia"]),
        "eli": datos["url_eli"],
        "huella": huella(camino_xml),
        "campos": len(filas),
        "distintos": len({f["id"] for f in filas}),
        "listas": len(codigos),
    }]

    trozos.append(f"ESPECIFICACION = {_cita(fijado(filas, 'BT-24'))}\n")
    trozos.append(f"PROCESO = {_cita(fijado(filas, 'BT-23'))}\n\n")

    trozos.append(
        "# Identificadores que el anexo usa más de una vez, con los términos a los que\n"
        "# se los pone. Ninguno es un fallo de numeración: son los cajones europeos\n"
        "# que el anexo reutiliza, uno por grupo español.\n"
        "REPETIDOS = {\n")
    for k, v in sorted(repetidos.items()):
        cuales = [f["termino"] for f in filas if f["id"] == k]
        trozos.append(f"    {_cita(k)}: {v},   # {' · '.join(c[:30] for c in cuales)}\n")
    trozos.append("}\n\n")

    trozos.append("CAMPOS = (\n")
    for f in filas:
        trozos.append(
            f'    Campo({_cita(f["id"])}, {f["nivel"]}, {_cita(f["cardinalidad"])},\n'
            f'          {_cita(f["termino"])},\n'
            f'          {_cita(f["descripcion"])},\n'
            f'          {_cita(f["tipo"])}, {_cita(f["ruta"])}),\n')
    trozos.append(")\n\n")

    trozos.append("LISTAS = {\n")
    for clave, lista in codigos.items():
        trozos.append(f'    {_cita(clave)}: Lista({_cita(lista["titulo"])}, {{\n')
        for v in lista["valores"]:
            trozos.append(f'        {_cita(v["valor"])}: {_cita(v["descripcion"])},\n')
        cierre = f', calificador={_cita(lista["calificador"])}' if lista["calificador"] else ""
        trozos.append(f"    }}{cierre}),\n")
    trozos.append("}\n")

    pathlib.Path(destino).write_text("".join(trozos), encoding="utf-8")
    return len(filas), len(codigos)


CABEZA = '''"""El anexo I de la solución pública, tal y como lo publica el BOE.

Esto **no se escribe a mano**: lo genera `herramientas/anexo_i.py` leyendo el
XML del BOE. Si algo de aquí no cuadra con el anexo, lo que está mal es el
extractor, no esta tabla.

De dónde sale
-------------
De la Orden %(orden)s, BOE núm. %(numero)s del %(publicada)s (%(boe)s), en vigor
desde el %(vigencia)s: anexo I, «Contenido y estructura de los campos de la
factura electrónica conforme al modelo UBL y la EN 16931», tabla del mensaje
de alta y listas de códigos.

    %(eli)s
    https://www.boe.es/diario_boe/xml.php?id=%(boe)s
    SHA-256 %(huella)s

Qué trae: %(campos)d filas, %(distintos)d identificadores distintos y
%(listas)d listas de códigos. No trae el mensaje de anulación, que es la otra
tabla del anexo I, ni el anexo II: están en `mensajes_es`.

Lo que hay que tener presente al usarlo
---------------------------------------
**El identificador no es una clave.** El anexo reutiliza a propósito unos
cuantos términos europeos como cajones para sus grupos: `BG-34`, `BT-179` y
`BT-180` aparecen una vez por cada línea de cobro (cargos en nombre de un
tercero, impuestos y tasas, minoraciones y retenciones), y `BG-24`, `BT-122`
y `BT-123` una vez por cada documento justificativo de la lista L10. Lo que
distingue una fila de otra es su término, y en las españolas su ruta. En
`REPETIDOS` está la lista entera, y con ella una prueba se entera si aparece
un repetido nuevo.

**La columna de la ruta no siempre es una ruta.** Unas filas traen la ruta
del campo; otras, la condición que su uso impone en otra parte («Su uso
implica que la ruta … tomará el valor «VAT»»); y alguna, las dos cosas o dos
rutas a la vez. Se copia tal cual, con sus erratas —rutas que no existen en
UBL 2.5, una `in:invoice` en minúscula—: separar una cosa de otra y arreglar
lo que hay que arreglar lo hace `validador/sintaxis.py`, a la vista y con el
porqué de cada arreglo.

**ESPECIFICACION y PROCESO salen de la tabla**, de la frase «Adoptará el
valor: …» de las filas BT-24 y BT-23, y no se escriben a mano.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Campo:
    """Una fila del anexo. `nivel` es la profundidad: 1 es `+`, 4 es `++++`."""

    id: str
    nivel: int
    cardinalidad: str
    termino: str
    descripcion: str
    tipo: str
    ruta: str

    @property
    def obligatorio(self) -> bool:
        return self.cardinalidad.startswith("1")

    @property
    def repetible(self) -> bool:
        return not self.cardinalidad.endswith("..1")

    @property
    def grupo(self) -> bool:
        return self.id.startswith("BG")

    @property
    def espanol(self) -> bool:
        """Un campo que la EN 16931 no tiene y el anexo añade."""
        return "-ES-" in self.id


@dataclass(frozen=True)
class Lista:
    titulo: str
    valores: dict
    # Lo que la lista lleva debajo del título como «CALIFICADOR», cuando lo
    # lleva. En las tres de claves de régimen es el impuesto (IVA, IGIC o
    # IPSI), que es el valor de BT-ES-24; en L7, L8 y L10, el esquema que
    # precede a sus valores.
    calificador: str = ""


# Los valores que el anexo obliga a poner en BT-24 y BT-23.
'''


if __name__ == "__main__":
    import sys

    xml = sys.argv[1] if len(sys.argv) > 1 else "anexos/orden-hac-1028-2026.xml"
    n, m = escribe_modulo(xml, "validador/cius_es.py")
    print(f"validador/cius_es.py: {n} campos y {m} listas")
