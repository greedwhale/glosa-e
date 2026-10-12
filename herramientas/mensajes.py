"""Saca a tabla los mensajes de la solución pública, del XML del BOE.

Qué mensajes son
----------------
La Orden HAC/1028/2026 define nueve mensajes `ApplicationResponse` de UBL,
cada uno con su tabla y su `cbc:ResponseCode`:

- **el de anulación de una factura o copia fiel** (`CANCELINVOICE`), que es la
  segunda tabla del anexo I, detrás de la del mensaje de alta;
- **los ocho del anexo II**, los estados de la factura: el pago y su baja
  (`PAYMENT`, `CANCELPAYMENT`), que manda el destinatario; el rechazo y su baja
  (`REJECTION`, `CANCELREJECTION`), también del destinatario; y el cobro y el
  impago con sus bajas (`SETTLEMENT`, `CANCELSETTLEMENT`, `DEFAULT`,
  `CANCELDEFAULT`), que el emisor manda si quiere (artículo 7.2).

El anexo II trae además su propia lista «L1», los motivos de rechazo, que no
es la L1 del anexo I (los tipos de factura): por eso aquí las listas son las
de cada anexo y no se mezclan con las de `cius_es`.

Cómo vienen en el XML
---------------------
Cada mensaje son dos tablas seguidas. La primera tiene una fila y dos celdas:
el nombre del mensaje y la ruta de su código con el valor detrás,
«ApplicationResponse/…/cbc:ResponseCode: PAYMENT». La segunda es la del
contenido, con la cabecera «Nivel», «Cardinalidad», «Término de negocio»,
«Descripción», «Tipo semántico de dato» y «Ruta UBL»; sin columna de
identificador, a diferencia de la del alta de la factura.

Lo único que hay que saber, además de lo de `anexo_i`:

- **Una celda puede ocupar dos filas.** En los mensajes de pago, cobro e
  impago, la descripción de la fecha de recepción de las mercancías vale
  también para la de recepción de la factura (`rowspan="2"`), y la segunda
  fila trae una celda menos. Se le pone la de arriba, que es lo que se ve en
  el BOE impreso.
- **Las rutas se copian tal cual**, con sus erratas y con las dos rutas que
  traen algunas celdas una detrás de otra. Separarlas y arreglar lo que haya
  que arreglar lo hace `validador/mensajes.py`, a la vista y con el porqué.

Esto no viaja en la rueda
-------------------------
Como `anexo_i`, vive fuera de `validador/` y se corre cuando cambia la orden:

    python -m herramientas.mensajes anexos/orden-hac-1028-2026.xml

y reescribe `validador/mensajes_es.py`, con la huella SHA-256 del XML del que
salió.
"""

import pathlib

from lxml import etree

from herramientas.anexo_i import (
    ANEXO_I,
    ANEXO_II,
    TITULO_LISTA,
    _celda,
    _cita,
    _fecha,
    huella,
    metadatos,
)

CABECERA = ["Nivel", "Cardinalidad", "Término de negocio (BT)", "Descripción",
            "Tipo semántico de dato", "Ruta UBL"]
SEPARADOR_DEL_CODIGO = ": "


def _de_cada_anexo(camino):
    """Los nodos del texto de la orden, repartidos por anexo y en orden."""
    texto = etree.parse(str(camino)).getroot().find("texto")
    anexo, nodos = None, {ANEXO_I: [], ANEXO_II: []}
    for nodo in texto:
        if nodo.tag == "p" and nodo.get("class") == "anexo_num":
            rotulo = _celda(nodo)
            anexo = rotulo if rotulo in nodos else None
            continue
        if anexo:
            nodos[anexo].append(nodo)
    if not nodos[ANEXO_I] or not nodos[ANEXO_II]:
        raise ValueError(f"no se encuentran «{ANEXO_I}» y «{ANEXO_II}» en {camino}")
    return nodos


def _filas_con_huecos(tabla):
    """Las filas de una tabla, rellenando lo que una celda de arriba ocupa.

    `anexo_i._filas` no hace falta que lo sepa: en el anexo I no hay ninguna
    celda que ocupe dos filas. Aquí sí, y sin esto la fila de abajo sale con
    las columnas corridas: el tipo donde va la descripción.
    """
    filas, arrastradas = [], {}
    for tr in tabla.iter("tr"):
        celdas = [c for c in tr if c.tag in ("td", "th")]
        fila, columna = [], 0
        while celdas or columna in arrastradas:
            if columna in arrastradas:
                texto, quedan = arrastradas.pop(columna)
                fila.append(texto)
                if quedan > 1:
                    arrastradas[columna] = (texto, quedan - 1)
            else:
                celda = celdas.pop(0)
                texto = _celda(celda)
                fila.append(texto)
                ocupa = int(celda.get("rowspan") or 1)
                if ocupa > 1:
                    arrastradas[columna] = (texto, ocupa - 1)
            columna += 1
        filas.append(fila)
    if arrastradas:
        raise ValueError(f"una celda ocupa más filas de las que tiene la tabla: {arrastradas}")
    return filas


def mensajes(camino):
    """Los nueve mensajes: su anexo, su título, su código y sus filas."""
    salida = {}
    for anexo, nodos in _de_cada_anexo(camino).items():
        tablas = [n for n in nodos if n.tag == "table"]
        for i, tabla in enumerate(tablas):
            filas = _filas_con_huecos(tabla)
            if not (len(filas) == 1 and len(filas[0]) == 2
                    and "ResponseCode" in filas[0][1]):
                continue
            titulo, celda_del_codigo = filas[0]
            ruta, _, codigo = celda_del_codigo.rpartition(SEPARADOR_DEL_CODIGO)
            if not codigo or " " in codigo:
                raise ValueError(f"no se entiende el código de «{titulo}»: {celda_del_codigo}")
            if codigo in salida:
                raise ValueError(f"el código {codigo} sale dos veces")
            if i + 1 >= len(tablas):
                raise ValueError(f"«{titulo}» no trae tabla de contenido detrás")
            contenido = _filas_con_huecos(tablas[i + 1])
            if contenido[0] != CABECERA:
                raise ValueError(f"«{titulo}»: la tabla de detrás no es la del contenido: {contenido[0]}")
            campos = []
            for fila in contenido[1:]:
                if len(fila) != len(CABECERA):
                    raise ValueError(f"«{titulo}»: fila con {len(fila)} celdas y no {len(CABECERA)}: {fila}")
                nivel, cardinalidad, termino, descripcion, tipo, ruta_ubl = fila
                campos.append({
                    "nivel": nivel.count("+"),
                    "cardinalidad": cardinalidad.replace(" ", ""),
                    "termino": termino,
                    "descripcion": descripcion,
                    "tipo": tipo,
                    "ruta": ruta_ubl,
                })
            salida[codigo] = {
                "anexo": "I" if anexo == ANEXO_I else "II",
                "titulo": titulo,
                "ruta_del_codigo": ruta,
                "filas": campos,
            }
    return salida


def listas_del_anexo_ii(camino):
    """Las listas del anexo II: de momento, una, la L1 de motivos de rechazo."""
    salida = {}
    for nodo in _de_cada_anexo(camino)[ANEXO_II]:
        if nodo.tag != "table" or nodo.find("caption") is None:
            continue
        titulo = TITULO_LISTA.match(_celda(nodo.find("caption")))
        filas = _filas_con_huecos(nodo)
        if not titulo or not filas or filas[0][:1] != ["Valores"]:
            continue
        clave, nombre = titulo.groups()
        if clave in salida:
            raise ValueError(f"la lista {clave} sale dos veces en el anexo II")
        salida[clave] = {"titulo": nombre, "valores": {f[0]: f[1] for f in filas[1:]}}
    return salida


def escribe_modulo(camino_xml, destino):
    """Reescribe `validador/mensajes_es.py` con lo que diga este XML."""
    todos = mensajes(camino_xml)
    codigos = listas_del_anexo_ii(camino_xml)
    datos = metadatos(camino_xml)
    rutas = {m["ruta_del_codigo"] for m in todos.values()}
    if len(rutas) != 1:
        raise ValueError(f"los mensajes no ponen el código en el mismo sitio: {sorted(rutas)}")

    trozos = [CABEZA % {
        "orden": datos["numero_oficial"],
        "boe": datos["identificador"],
        "numero": datos["diario_numero"],
        "publicada": _fecha(datos["fecha_publicacion"]),
        "vigencia": _fecha(datos["fecha_vigencia"]),
        "eli": datos["url_eli"],
        "huella": huella(camino_xml),
        "mensajes": len(todos),
        "filas": sum(len(m["filas"]) for m in todos.values()),
        "listas": len(codigos),
    }]
    trozos.append(f"RUTA_DEL_CODIGO = {_cita(rutas.pop())}\n\n")
    trozos.append("MENSAJES = {\n")
    for codigo, mensaje in todos.items():
        trozos.append(
            f'    {_cita(codigo)}: Mensaje({_cita(mensaje["anexo"])},\n'
            f'        {_cita(mensaje["titulo"])}, (\n')
        for f in mensaje["filas"]:
            trozos.append(
                f'        Fila({f["nivel"]}, {_cita(f["cardinalidad"])}, {_cita(f["termino"])},\n'
                f'             {_cita(f["descripcion"])},\n'
                f'             {_cita(f["tipo"])}, {_cita(f["ruta"])}),\n')
        trozos.append("    )),\n")
    trozos.append("}\n\n")
    trozos.append("LISTAS = {\n")
    for clave, lista in codigos.items():
        trozos.append(f'    {_cita(clave)}: Lista({_cita(lista["titulo"])}, {{\n')
        for valor, descripcion in lista["valores"].items():
            trozos.append(f'        {_cita(valor)}: {_cita(descripcion)},\n')
        trozos.append("    }),\n")
    trozos.append("}\n")
    pathlib.Path(destino).write_text("".join(trozos), encoding="utf-8")
    return len(todos), len(codigos)


CABEZA = '''"""Los mensajes de la solución pública, tal y como los publica el BOE.

Esto **no se escribe a mano**: lo genera `herramientas/mensajes.py` leyendo el
XML del BOE. Si algo de aquí no cuadra con la orden, lo que está mal es el
extractor, no esta tabla.

De dónde sale
-------------
De la Orden %(orden)s, BOE núm. %(numero)s del %(publicada)s (%(boe)s), en vigor
desde el %(vigencia)s: la tabla del mensaje de anulación del anexo I y las
ocho del anexo II, «Contenido y estructura de los campos del mensaje relativo
a los estados de pago, rechazo, cobro o impago de las facturas conforme al
modelo UBL», con su lista de códigos.

    %(eli)s
    https://www.boe.es/diario_boe/xml.php?id=%(boe)s
    SHA-256 %(huella)s

Qué trae: %(mensajes)d mensajes, %(filas)d filas y %(listas)d lista de códigos.

Lo que hay que tener presente al usarlo
---------------------------------------
**La clave de cada mensaje es su `cbc:ResponseCode`**, que el BOE pone en la
cabecera de su tabla y no en una fila. Las filas no traen identificador: no
son términos de la norma europea.

**La columna de la ruta se copia tal cual**, con sus erratas: rutas que no
existen en UBL 2.5, dos rutas seguidas en una celda, un espacio donde va una
barra. Separarlas y arreglarlas lo hace `validador/mensajes.py`, a la vista y
con el porqué de cada arreglo.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Fila:
    """Una fila de la tabla de un mensaje. `nivel` es 1 para `+`, 3 para `+++`."""

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


@dataclass(frozen=True)
class Mensaje:
    anexo: str
    titulo: str
    filas: tuple


@dataclass(frozen=True)
class Lista:
    titulo: str
    valores: dict


# Dónde pone cada mensaje su código. Es la misma en los nueve, y si un día no
# lo es, el extractor se niega.
'''


if __name__ == "__main__":
    import sys

    xml = sys.argv[1] if len(sys.argv) > 1 else "anexos/orden-hac-1028-2026.xml"
    n, m = escribe_modulo(xml, "validador/mensajes_es.py")
    print(f"validador/mensajes_es.py: {n} mensajes y {m} lista(s)")
