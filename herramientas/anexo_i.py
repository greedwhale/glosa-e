"""Saca a tabla el anexo I del proyecto de orden de la solución pública.

Qué es ese anexo y por qué hace falta leerlo
--------------------------------------------
El RD 238/2026 admite cuatro sintaxis (artículo 7.1), pero la solución pública
de la AEAT **solo admite UBL 2.5**, y no UBL a secas: un CIUS español propio,
`urn:aeat.es:CIUS-ES-SPFE:1.0.0`, con 46 campos que la EN 16931 no tiene
—retenciones, suplidos, minoraciones, recargo de equivalencia, régimen de grupo
de entidades, QR fiscal—. Ese CIUS no se publica como esquema ni como
esquematrón: se publica como **una tabla dentro de un PDF**.

Así que o se lee el PDF o no se sabe qué hay que generar. Esto lo lee.

Por qué por coordenadas y no por columnas de texto
--------------------------------------------------
Se probaron las dos. El modo `layout` de pypdf coloca los dígitos donde le
cuadra: `BT-179` sale partido en dos renglones y el `21` de `BT-ES-21` aparece
dentro de la columna del término. Un parser que se fíe de eso produce 174 filas
plausibles y equivocadas, que es el fallo de siempre de esta casa —sale verde y
no es lo que crees haber comprobado—.

Con la (x, y) de cada pieza el reparto es geometría, y la geometría se puede
contrastar. Se contrastó: el conjunto de identificadores que sale de aquí
coincide **exactamente** con el que sale de leer el mismo PDF en plano y buscar
`B[GT]-(ES-)?\\d+` con una expresión regular, que no comparte una sola línea de
código con esto. Las diferencias de recuento están explicadas una a una en
`tests/test_cius_es.py`.

Esto no viaja en la rueda
-------------------------
Vive fuera de `validador/` a propósito. Necesita `pypdf`, y `lxml` es la única
dependencia del paquete porque el motor entero se descarga al navegador de
quien abre la página: una dependencia más son megabytes más para todo el que
entre. Aquí se genera `validador/cius_es.py` y lo que viaja es el resultado.

Cómo se usa
-----------
    python -m herramientas.anexo_i anexos/anexo-i.pdf

y reescribe `validador/cius_es.py`. El PDF no se versiona —es de la AEAT y pesa
un mega—; lo que se versiona es la tabla, con la huella SHA-256 del PDF del que
salió al lado, para que un anexo nuevo no se cuele sin que nadie se entere.
"""

import collections
import hashlib
import json
import pathlib
import re

import pypdf

# Fronteras de columna de la tabla principal, en puntos, medidas sobre la
# cabecera de las catorce páginas que la llevan.
COLUMNAS = [("id", 0), ("nivel", 92), ("cardinalidad", 126),
            ("termino", 157), ("descripcion", 261), ("tipo", 503), ("ruta", 573)]

NIVEL = re.compile(r"^\+{1,4}$")
CARD = re.compile(r"^\d+\.\.[\dn]$")
ENTERO = re.compile(r"^B[GT]-(?:ES-)?\d+$")
PEDAZO = re.compile(r"^(?:B[GT]|B[GT]-|-|ES|ES-|ES-\d+|\d{1,3}|B[GT]-\d+|B[GT]-ES-?\d*)$")

# La cabecera de la tabla, que se repite en cada página y marca dónde empieza.
CABECERA = ("Tipo semántico", "Término de negocio")
# Ruido que el PDF cuela **dentro** de un renglón con contenido de verdad: el
# sello de audiencia pública comparte línea con la fila que trae el número de
# `BT-ES-31`. Tirar el renglón entero por llevar el sello perdía ese número, así
# que se tira la pieza, no el renglón.
RUIDO = ("Documento sometido a trámite", "Agencia Tributaria")
# La cabecera ocupa tres renglones y el tercero solo lleva las continuaciones
# «Cardina|lidad» y «Tipo semántico|de dato». Medido: cada una aparece 14
# veces, una por página de tabla, y nunca como contenido.
SOBRAS = ("de dato", "lidad", "Cardina")

# Donde acaban los campos y empiezan las listas de códigos.
CORTE = "II. CLAVES Y VALORES"

TITULO_LISTA = re.compile(r"^(L\d(?:\.[A-Z])?[A-Z]?)\s*[–-]\s*(.+)$")
ROTULO = re.compile(r"^(valores|descripci[oó]n)\b", re.I)
CODIGO = re.compile(r"^[A-Z0-9]{1,4}$")
CALIFICADOR = re.compile(r"^CALIFICADOR\s+([A-Z]+)$")
CABECERA_DE_PAGINA = re.compile(r"^\s*Agencia Tributaria\s*\n(?:\s*\n)*\s*\d+\s*\n")


def _columna(x):
    nombre = "id"
    for clave, desde in COLUMNAS:
        if x >= desde:
            nombre = clave
    return nombre


def renglones(camino):
    """Cada renglón del PDF como lista de (x, texto), de arriba abajo.

    La `y` se redondea a dos puntos porque dos piezas del mismo renglón no caen
    en el mismo punto exacto, y el interlineado medido es de unos diez.
    """
    lector = pypdf.PdfReader(camino)
    piezas = collections.defaultdict(list)
    for n, pagina in enumerate(lector.pages):
        def visita(texto, cm, tm, fuente, tam, _n=n):
            if texto.strip():
                piezas[(_n, round(tm[5] / 2) * 2)].append((tm[4], texto))
        pagina.extract_text(visitor_text=visita)
    for (n, y), trozos in sorted(piezas.items(), key=lambda kv: (kv[0][0], -kv[0][1])):
        yield n, y, sorted(trozos)


def _limpia(trozos):
    return [(x, s) for x, s in trozos
            if not any(s.strip().startswith(r) for r in RUIDO)
            and s.strip() not in SOBRAS and x < 700]


def paginas_de_tabla(camino):
    """Las páginas que llevan la cabecera de la tabla, y solo esas.

    Detrás del anexo vienen las listas de códigos, que son otra tabla con otras
    columnas. Sin este corte, la última fila se tragaba entera la lista de
    claves de régimen: 416 caracteres de nivel y media página de cardinalidad.
    """
    lector = pypdf.PdfReader(camino)
    return {n for n, p in enumerate(lector.pages)
            if all(c in (p.extract_text() or "") for c in CABECERA)}


def campos(camino):
    """Las filas de la tabla del anexo I, en orden.

    El identificador es lo único que llega roto de verdad, y llega roto de dos
    formas contrarias: unas veces `BT` y `-` van en el renglón que abre la fila
    y el número cae en el siguiente; otras es al revés y el `+++ 1..1` aparece
    abajo. Se resuelve con una antesala: lo que no se sabe de quién es se
    guarda y se le entrega a la fila que abra después.
    """
    de_tabla = paginas_de_tabla(camino)
    filas, abierta = [], None
    antesala = collections.defaultdict(list)

    for n, y, trozos in renglones(camino):
        if n not in de_tabla:
            continue
        trozos = _limpia(trozos)
        if not trozos:
            continue
        if any(CORTE in s for _, s in trozos):
            break
        entera = " ".join(s for _, s in trozos)
        if any(c in entera for c in CABECERA) or entera.strip().startswith("ID "):
            # La cabecera marca dónde empieza la tabla en cada página. Lo que
            # quedara en la antesala es de antes de la tabla —la prosa de la
            # introducción, en la página 3— y no es de ninguna fila.
            antesala = collections.defaultdict(list)
            continue

        celdas = collections.defaultdict(list)
        for x, texto in trozos:
            celdas[_columna(x)].append(texto.strip())
        celda = {k: " ".join(v).strip() for k, v in celdas.items()}
        # Estos tres llegan en pedazos sueltos —`BT`, `-`, `21`— y el espacio
        # que los separa no es parte del dato: estorba para reconocerlo.
        for clave in ("id", "nivel", "cardinalidad"):
            if clave in celda:
                celda[clave] = celda[clave].replace(" ", "")
        if celda.get("id") and not PEDAZO.match(celda["id"]):
            celda.pop("id")

        if NIVEL.match(celda.get("nivel", "")) and CARD.match(celda.get("cardinalidad", "")):
            if abierta:
                filas.append(abierta)
            abierta = collections.defaultdict(
                list, {k: [v] for k, v in celda.items() if v})
            for k, v in antesala.items():
                abierta[k] = v + abierta.get(k, [])
            antesala = collections.defaultdict(list)
            abierta["pagina"] = n
            continue

        if abierta is None:
            destino = antesala
        elif celda.get("id") and ENTERO.match("".join(abierta["id"]).replace(" ", "")):
            # La fila abierta ya tiene identificador entero, así que este
            # renglón es el arranque de la siguiente: **todo** él, no solo el
            # ID. Sin esto, el término de la fila que viene se pega a la
            # anterior.
            destino = antesala
        else:
            destino = abierta
        for k, v in celda.items():
            if v:
                destino[k].append(v)
    if abierta:
        filas.append(abierta)

    return [{
        "id": "".join(f.get("id", [])).replace(" ", ""),
        "nivel": len(" ".join(f.get("nivel", []))),
        "cardinalidad": " ".join(f.get("cardinalidad", [])),
        "termino": re.sub(r"\s+", " ", " ".join(f.get("termino", []))).strip(),
        "descripcion": re.sub(r"\s+", " ", " ".join(f.get("descripcion", []))).strip(),
        "tipo": " ".join(f.get("tipo", [])),
        "ruta": "".join(f.get("ruta", [])).replace(" ", ""),
    } for f in filas]


def _texto_de_listas(camino):
    """El texto de las listas en el orden en que el PDF lo escribe.

    Cada página empieza con «Agencia Tributaria» y su número, y acaba con el
    sello de audiencia pública. Se quitan página a página y no al final: el
    número de página es un renglón de dos cifras suelto, y en las listas de
    claves eso es exactamente lo que parece un código.
    """
    lector = pypdf.PdfReader(camino)
    trozos = []
    for pagina in lector.pages:
        texto = CABECERA_DE_PAGINA.sub("", pagina.extract_text() or "", count=1)
        trozos.append(texto.split(RUIDO[0])[0])
    entero = "\n".join(trozos)
    return entero[entero.index(CORTE):]


def listas(camino):
    """Las listas de códigos L1..L8 que van detrás de la tabla.

    **Se leen en el orden del PDF y no por coordenadas**, al revés que la
    tabla, y es a propósito. Se leyeron por coordenadas hasta el 14-09-2026 y
    las descripciones salían corridas una fila en cinco de las once listas: en
    una celda de dos renglones el código va centrado **entre** los dos, así que
    al repartir por altura el primer renglón caía en el código de arriba. El
    01 de L6 decía «País Vasco y Navarra», que es justo lo que excluye. Los
    códigos salían bien, y por eso no se vio.

    El orden del PDF sí va por celdas, porque así lo escribe quien lo generó:
    código, descripción, continuación. Lo que hay que separar es el ruido.

    - Un renglón es de código si empieza por algo con forma de código y el
      resto lleva minúsculas, o si el código va solo: en L5 el 07 y el 09
      ocupan su propio renglón encima de la descripción. Sin lo de las
      minúsculas, el «DE APLICACIÓN ES EL IGIC» con que sigue la cabecera de
      L3B se tomaba por el código «DE».
    - Debajo del título de las tres listas de claves de régimen va un
      «CALIFICADOR IVA», «IGIC» o «IPSI». Es el valor de BT-ES-44, lo que dice
      en qué lista se busca la clave, y se guarda.
    """
    salida, actual, abierto = {}, None, None
    for renglon in _texto_de_listas(camino).splitlines():
        entera = renglon.strip()
        if not entera or entera.startswith(CORTE):
            continue
        t = TITULO_LISTA.match(entera)
        if t:
            actual, abierto = t.group(1), None
            salida[actual] = {"titulo": t.group(2).strip(), "calificador": "",
                              "valores": []}
            continue
        if actual is None:
            continue
        c = CALIFICADOR.match(entera)
        if c:
            salida[actual]["calificador"] = c.group(1)
            continue
        if ROTULO.match(entera):
            abierto = None
            continue
        primero, _, resto = entera.partition(" ")
        if CODIGO.match(primero) and (not resto.strip() or re.search(r"[a-zá-ú]", resto)):
            abierto = {"valor": primero, "descripcion": " ".join(resto.split())}
            salida[actual]["valores"].append(abierto)
        elif abierto:
            abierto["descripcion"] = " ".join((abierto["descripcion"] + " " + entera).split())
    return salida


def huella(camino):
    return hashlib.sha256(pathlib.Path(camino).read_bytes()).hexdigest()


def _cita(s):
    return json.dumps(s, ensure_ascii=False)


def escribe_modulo(camino_pdf, destino, fecha, url):
    """Reescribe `validador/cius_es.py` con lo que diga este PDF."""
    filas = campos(camino_pdf)
    codigos = listas(camino_pdf)
    repetidos = {k: v for k, v in
                 collections.Counter(f["id"] for f in filas).items() if v > 1}

    trozos = [CABEZA % {
        "fecha": fecha,
        "url": url,
        "huella": huella(camino_pdf),
        "campos": len(filas),
        "distintos": len({f["id"] for f in filas}),
        "listas": len(codigos),
    }]

    trozos.append("REPETIDOS = {\n")
    for k, v in sorted(repetidos.items()):
        cuales = [f["termino"] for f in filas if f["id"] == k]
        trozos.append(f"    {_cita(k)}: {v},   # {' · '.join(c[:34] for c in cuales)}\n")
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


CABEZA = '''"""El CIUS español de la solución pública, tal y como lo dice el anexo I.

Esto **no se escribe a mano**: lo genera `herramientas/anexo_i.py` leyendo el
PDF del anexo. Si algo de aquí no cuadra con el anexo, lo que está mal es el
extractor, no esta tabla.

De dónde sale
-------------
Del proyecto de orden ministerial sometido a audiencia pública el %(fecha)s,
anexo I, «Contenido y estructura de los campos de la factura electrónica
conforme al modelo UBL y la EN 16931».

    %(url)s
    SHA-256 %(huella)s

Qué trae: %(campos)d filas, %(distintos)d identificadores distintos y
%(listas)d listas de códigos.

Lo que hay que tener presente al usarlo
---------------------------------------
**Es un borrador, y ya cambió.** Este anexo, el de abril, nunca salió en el
BOE: la orden se publicó el 05-10-2026 (Orden HAC/1028/2026) con otro anexo I,
y lo que de ese ya se aplica va escrito a mano en `solucion_publica.py` hasta
que esta tabla salga de su XML. La propia AEAT había respondido en su seminario
del 19-05-2026 que el anexo «se alineará plenamente» con UBL 2.5 y la norma
europea. La huella de arriba
está para que el día que salga otro anexo esto no se quede en silencio: hay una
prueba que la comprueba si el PDF está a mano.

**El identificador no es una clave.** El anexo reutiliza a propósito unos
cuantos términos europeos como cajones para sus extensiones: `BG-34`, `BT-179`
y `BT-180` aparecen cinco veces cada uno, uno por grupo español —cargos a
terceros, minoraciones, recargo de equivalencia, grupo de entidades y
retenciones—. Lo que distingue una fila de otra es su ruta UBL. En `REPETIDOS`
está la lista entera, y con ella una prueba se entera si aparece un repetido
nuevo.

**Y hay al menos un fallo de numeración en el borrador**: `BT-ES-2` está usado
dos veces para dos términos distintos —«Identificador de la extensión para la
gestión de facturas rectificativas» y «Tipo de factura rectificativa»—. No es
un fallo de extracción: los dos métodos de lectura lo ven igual.

Lo que esto obliga a corregir del motor
---------------------------------------
La lista L1 —los tipos de factura admitidos— es `380, 384, 388, 389, 471`, y
**no lleva el 381**. En España una rectificativa es siempre 384, o 471 si la
expide el destinatario; que rectifique por diferencias o por sustitución no se
dice en el BT-3 sino en `BT-ES-3`, con la lista L2.B (`I` o `S`).

`en16931.py` traduce hoy el `CorrectionMethod` 03 de Facturae a **381**, que es
correcto para la EN 16931 a secas y no vale dentro de este CIUS. Está anotado
en `HALLAZGOS.md` y pendiente de arreglar.
"""

from dataclasses import dataclass, field


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
        return self.cardinalidad.endswith("n")

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
    # El impuesto al que pertenece la lista, cuando lo dice. Solo las tres de
    # claves de régimen: es el valor que va en BT-ES-44.
    calificador: str = ""


# El valor constante que el anexo obliga a poner en BT-24 y BT-23.
ESPECIFICACION = "urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0"
PROCESO = "urn:aeat:names:specification:ubl:schema:B2B"

# Identificadores que el anexo usa más de una vez, con los términos a los que
# se los pone. Los cinco primeros son reutilización deliberada de cajones
# europeos; `BT-ES-2` es un fallo de numeración del borrador.
'''


if __name__ == "__main__":
    import sys

    pdf = sys.argv[1] if len(sys.argv) > 1 else "anexos/anexo-i.pdf"
    n, m = escribe_modulo(
        pdf,
        "validador/cius_es.py",
        fecha="17 de abril de 2026",
        url="https://www.hacienda.gob.es/sgt/normativadoctrina/proyectos/"
            "16042026-anexo-i-pom-factura-electronica.pdf",
    )
    print(f"validador/cius_es.py: {n} campos y {m} listas")
