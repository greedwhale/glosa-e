"""El conjunto que hace falta para validar de verdad, en un solo fichero.

**Qué problema resuelve.** El validador comprueba tres cosas —la forma contra
los esquemas, el contenido contra la norma, y la firma contra una autoridad de
confianza— pero dos de las tres necesitan ficheros que no están en el código:
los XSD oficiales, que son de sus organismos, y las anclas, que salen de la
lista de confianza del Estado. Quien usa la consola se los instala. Quien entra
en una página web no se instala nada, así que o viajan con la página o esa
página comprueba **una de las tres** y tiene que decirlo.

Este módulo arma el fichero que viaja. Es un ZIP con las tres carpetas dentro
—`esquemas/`, `anclas/`, `anclas-sellos/`— y un `PAQUETE.json` que resume qué
lleva y de cuándo es. El navegador lo baja de una vez y lo descomprime en su
disco virtual; sin esto habría que pedir doscientos ficheros sueltos.

**De dónde sale y qué se versiona.** El paquete se arma con
`python -m validador --empaquetar`, desde las carpetas que uno mismo ha montado
y comprobado, y esas carpetas —`esquemas/`, `anclas/`, `anclas-sellos/`— no se
versionan: son la materia prima, no lo que se reparte.

El zip sí, desde que la página se publica. Estuvo fuera mientras se servía en
local, donde cada uno armaba el suyo; al publicarla dejó de tener sentido,
porque el sitio se construye desde el repositorio y sin el zip comprobaría el
contenido y nada más. Y la razón de no versionar anclas —que quien controle ese
fichero controla en quién cree el validador— no desaparece por dejarlo fuera:
publicar la página las reparte igual. Lo que hace falta es poder contrastarlas,
y para eso va el SHA-256 en `PAQUETE.json`, dentro del zip y fuera, y a la vista
en la página.

**Y dos negativas que valen más que el resto del módulo.** No se empaquetan
anclas sin manifiesto, y no se empaquetan anclas cuya lista debía haberse
renovado. La primera porque un conjunto que no dice de dónde viene es justo lo
que habíamos quedado en no repartir. La segunda porque el día que una lista
vence, las autoridades a las que el Estado les haya retirado la cualificación
siguen valiendo dentro del paquete, con su certificado en vigor y su cadena
llegando: nada en el documento lo delata. Repartir eso a desconocidos es peor
que no repartir nada, porque no repartir nada se nota.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from validador.cadena import (
    NOMBRE_DE_ESTADOS,
    NOMBRE_DEL_MANIFIESTO,
    SUFIJO_DE_SELLOS,
    Almacen,
)
from validador import bitacora, cifras, pagina_incidencias
from validador.cadena import CARPETA_POR_DEFECTO as ANCLAS_POR_DEFECTO
from validador.esquema import CARPETA_POR_DEFECTO as ESQUEMAS_POR_DEFECTO

__all__ = [
    "NOMBRE",
    "SinPyodide",
    "traer_pyodide",
    "MANIFIESTO",
    "Contenido",
    "Sitio",
    "SinManifiesto",
    "SinRenovar",
    "SinRueda",
    "SinPagina",
    "RuedaVieja",
    "SinPaquete",
    "rueda_desfasada",
    "licencia_declarada",
    "armar",
    "montar_sitio",
]

# El nombre del zip y el del resumen que va al lado. El resumen va **fuera**
# además de dentro para que la página pueda decir de cuándo son las anclas sin
# haber arrancado Python todavía: son 14 MB de intérprete, y hasta que no
# terminan de bajar no hay forma de leer nada de dentro del zip.
NOMBRE = "paquete.zip"
MANIFIESTO = "PAQUETE.json"

# Qué se recoge de cada carpeta. Los certificados llevan las mismas
# extensiones que reconoce `cadena.py`, y los dos ficheros que no son
# certificados —el manifiesto y la tabla de estados— van sí o sí: sin la tabla,
# las anclas retiradas de `retiradas/` no se usan, y sin el manifiesto el
# informe no puede decir de dónde salen.
_DE_ESQUEMAS = ("*.xsd",)
_DE_ANCLAS = ("*.cer", "*.crt", "*.der", "*.pem", "*.ca-bundle")
_SUELTOS = (NOMBRE_DEL_MANIFIESTO, NOMBRE_DE_ESTADOS)


class SinManifiesto(Exception):
    """Las anclas no dicen de dónde vienen, así que no se reparten."""


class SinRenovar(Exception):
    """La lista de la que salen las anclas debía haberse renovado."""


@dataclass(frozen=True)
class Contenido:
    """Qué lleva el paquete, para poder decirlo sin abrirlo."""

    esquemas: int
    anclas: int
    anclas_de_sellos: int
    bytes: int
    huella: str
    declarada: str
    publicada: str | None = None
    siguiente: str | None = None
    montada: str | None = None
    armado: str | None = None

    def como_json(self) -> str:
        return json.dumps(self.__dict__, ensure_ascii=False, indent=2) + "\n"


def _ficheros(carpeta: Path, patrones: tuple[str, ...]) -> list[Path]:
    encontrados: set[Path] = set()
    for patron in patrones:
        encontrados.update(p for p in carpeta.rglob(patron) if p.is_file())
    for nombre in _SUELTOS:
        for hallado in carpeta.rglob(nombre):
            if hallado.is_file():
                encontrados.add(hallado)
    return sorted(encontrados)


def _contar(rutas: list[Path]) -> int:
    """Cuántos de estos son datos y no papeleo."""
    return sum(1 for r in rutas if r.name not in _SUELTOS)


def _ficha_del_manifiesto(dia: date) -> zipfile.ZipInfo:
    """La entrada del `PAQUETE.json` de dentro, con fecha fija.

    **Por qué esto no es un detalle.** El SHA-256 del zip va publicado al lado
    del zip, y el README lo ofrece para poder contrastar las anclas que se
    reparten. Para eso hace falta que dos personas que armen el paquete de las
    mismas carpetas obtengan el mismo fichero, y no lo obtenían: `writestr`
    con un nombre a secas le pone a la entrada **la hora del reloj**, así que
    dos vueltas separadas por un minuto daban huellas distintas.

    Medido, y medido hasta el final: de las 436 entradas de dos paquetes
    armados con un minuto de diferencia, las 436 tenían el contenido idéntico
    byte a byte y **una sola** cambiaba de fecha, esta. Con lo cual la huella
    servía para saber que la descarga llegó entera y no para lo otro, que es
    lo que estaba escrito.

    La fecha es la del día en que se arma, que ya es un dato del paquete
    —sale en `armado`— y no una hora inventada.
    """
    ficha = zipfile.ZipInfo(MANIFIESTO, date_time=(dia.year, dia.month, dia.day, 0, 0, 0))
    ficha.compress_type = zipfile.ZIP_DEFLATED
    # Lo que `writestr` le pone a una entrada creada desde un nombre. Sin esto
    # el fichero saldría del zip sin permisos y quien lo descomprima en un
    # sistema que los mire se queda sin poder leerlo.
    ficha.external_attr = 0o600 << 16
    return ficha


def armar(
    destino: str | Path,
    esquemas: str | Path = ESQUEMAS_POR_DEFECTO,
    anclas: str | Path = ANCLAS_POR_DEFECTO,
    sellos: str | Path | None = None,
    hoy: date | None = None,
    aunque_esten_vencidas: bool = False,
) -> Contenido:
    """Escribe el paquete y devuelve qué lleva.

    `destino` es el `.zip`; el `PAQUETE.json` se escribe a su lado y también
    dentro, para que las dos copias salgan de la misma vuelta y no puedan
    contar cosas distintas.
    """
    destino = Path(destino)
    carpeta_esquemas = Path(esquemas)
    carpeta_anclas = Path(anclas)
    carpeta_sellos = (
        Path(sellos)
        if sellos is not None
        else carpeta_anclas.parent / (carpeta_anclas.name + SUFIJO_DE_SELLOS)
    )

    almacen = Almacen(carpeta_anclas)
    if not (carpeta_anclas / NOMBRE_DEL_MANIFIESTO).is_file():
        raise SinManifiesto(
            f"«{carpeta_anclas}» no trae {NOMBRE_DEL_MANIFIESTO}, así que no se "
            "sabe de qué lista de confianza salen esas anclas ni de cuándo son. "
            "Un conjunto de anclas que no dice de dónde viene no se reparte: "
            "quien lo reciba estaría creyendo a unas autoridades que nadie le "
            "ha dicho cuáles son. Móntalas con "
            "`python -m validador --montar-anclas`, que deja el manifiesto."
        )
    renovacion = almacen.renovacion
    dia = hoy or date.today()
    if renovacion.vencida(dia) and not aunque_esten_vencidas:
        raise SinRenovar(
            f"La lista de la que salen estas anclas decía renovarse el "
            f"{cifras.fecha(renovacion.siguiente)}, y hoy es {cifras.fecha(dia)}. "
            "Empaquetarlas repartiría a desconocidos un conjunto en el que "
            "cualquier autoridad a la que el Estado le haya retirado la "
            "cualificación desde entonces sigue valiendo, con su certificado "
            "en vigor y su cadena llegando: no hay nada en el documento que lo "
            "delate. Vuelve a montarlas con "
            "`python -m validador --montar-anclas`."
        )

    partes = [
        (carpeta_esquemas, _ficheros(carpeta_esquemas, _DE_ESQUEMAS)),
        (carpeta_anclas, _ficheros(carpeta_anclas, _DE_ANCLAS)),
        (carpeta_sellos, _ficheros(carpeta_sellos, _DE_ANCLAS)),
    ]
    contenido = Contenido(
        esquemas=_contar(partes[0][1]),
        anclas=_contar(partes[1][1]),
        anclas_de_sellos=_contar(partes[2][1]),
        bytes=0,
        huella="",
        declarada=almacen.declarada,
        publicada=renovacion.publicada.isoformat() if renovacion.publicada else None,
        siguiente=renovacion.siguiente.isoformat() if renovacion.siguiente else None,
        montada=renovacion.montada.isoformat() if renovacion.montada else None,
        armado=dia.isoformat(),
    )

    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zf:
        for carpeta, rutas in partes:
            for ruta in rutas:
                zf.write(ruta, str(Path(carpeta.name) / ruta.relative_to(carpeta)))
        zf.writestr(_ficha_del_manifiesto(dia), contenido.como_json())

    crudo = destino.read_bytes()
    contenido = Contenido(
        **{
            **contenido.__dict__,
            "bytes": len(crudo),
            "huella": hashlib.sha256(crudo).hexdigest(),
        }
    )
    # El de fuera lleva el tamaño y la huella del zip ya escrito; el de dentro
    # no puede llevarlos, porque estarían dentro de lo que miden.
    (destino.parent / MANIFIESTO).write_text(
        contenido.como_json(), encoding="utf-8"
    )
    return contenido


# --- Pyodide, alojado aquí -------------------------------------------------
#
# **Por qué está esto.** La página promete que la factura no sale del ordenador
# de quien la mira, y es verdad: se midió, y al validar hace cero peticiones.
# Lo que no era verdad es la frase de al lado, «no se hace ninguna petición a
# nadie». Al abrir la página el navegador pedía siete ficheros —unos 7,8 MB: el
# intérprete, la biblioteca estándar y lxml— a `cdn.jsdelivr.net`, y esa
# petición lleva la IP y el navegador del visitante a un tercero antes de que
# haya hecho nada.
#
# Lo llamativo es que el mismo criterio ya estaba aplicado al lado: se descartó
# Google Fonts por escrito, por esto exactamente. La letra se miró; los 7,8 MB
# que van dos líneas más abajo, no. Llevaban ahí desde que la página era un
# experimento que no iba a visitar nadie.
#
# Así que se bajan una vez y se sirven desde el propio sitio. Se bajan **al
# construir**, no al visitar: que este ordenador hable con el CDN no le importa
# a nadie; que hable el navegador de un desconocido, sí.
VERSION_DE_PYODIDE = "314.0.6"
DE_DONDE_SE_BAJA = "https://cdn.jsdelivr.net/pyodide/v{}/full/"

# Los del intérprete. Los de los paquetes no se escriben aquí porque sus
# nombres llevan la versión dentro: salen de `pyodide-lock.json`, que es quien
# lo sabe.
_NUCLEO = (
    "pyodide.js",
    "pyodide.asm.mjs",
    "pyodide.asm.wasm",
    "python_stdlib.zip",
    "pyodide-lock.json",
)
# Solo lxml. micropip estaba aqui para instalar el wheel del validador, y ya
# no hace falta: `loadPackage` acepta la direccion de un `.whl` y el wheel se
# construye sin dependencias, asi que no habia nada que resolver. Son 115 KB
# menos en cada primera visita. lxml no depende de el (mirado en el candado).
_PAQUETES_DE_PYODIDE = ("lxml",)

CARPETA_DE_PYODIDE = "vendor/pyodide"
NOMBRE_DE_HUELLAS = "HUELLAS.txt"

# Lo que tiene que llegar, escrito aquí y versionado.
#
# `HUELLAS.txt` existía desde el principio y **no fijaba nada**: se calcula de
# lo que se baja, se escribe dentro de `vendor/`, que no se versiona, y por lo
# tanto no viaja. Era un recibo —«esto llegó»— haciéndose pasar por un contrato
# —«esto tenía que llegar»—. La diferencia se ve en lo que cada uno permite
# decir: con un recibo, un día que el CDN sirviera otra cosa, la construcción de
# Vercel la bajaría, la apuntaría como buena y la publicaría; y como
# `traer_pyodide` reutiliza lo que ya está en la carpeta sin mirarlo, un
# fichero a medias de una descarga cortada se apuntaba igual.
#
# Son 15 MB que corren dentro del navegador de quien abre la página. Con la
# tabla aquí, lo que no cuadre no se baja, no se monta y no se publica.
#
# Contrastadas dos veces contra el CDN, a tres semanas de distancia: al bajarlas
# el 30-08-2026 y otra vez el 20-09-2026, los seis ficheros byte a byte iguales.
#
# Subir de versión es cambiar el intérprete de un desconocido: se hace a mano,
# bajándolo, mirando qué trae y escribiendo las huellas nuevas aquí. Lo que no
# puede pasar es que se mueva solo.
HUELLAS_DE_PYODIDE = {
    "lxml-6.0.2-cp314-cp314-pyemscripten_2026_0_wasm32.whl":
        "13b273a49a4737efb22148af07644fb1b2db6540768b92d14ecdf852ed2d6148",
    "pyodide-lock.json":
        "3fdaef09e9e365c85e002737720f8d0ab8f278c1c244a2dde6a37663cf488ad4",
    "pyodide.asm.mjs":
        "2ac5eba365ec12839c75c03b39b3be1dd63b798852cc460b014b52238be042f7",
    "pyodide.asm.wasm":
        "3a0a00dfeaa348ac20f9ef09904233d32d33f644339662d4af368f8a2010f37a",
    "pyodide.js":
        "8d653521230f8e92f2e2f587e03f29d3abcdfb1c1744442d06fd8235007adb6b",
    "python_stdlib.zip":
        "80c5be6babfe03297069703410c3c29404dcf2525d2b128746bae5536f94831f",
}


class NoSeMonta(Exception):
    """La raíz de todas las negativas de montar el sitio.

    Existe por un fallo concreto y aburrido: la lista de las que `__main__`
    cazaba estaba escrita a mano, una a una, y `SinPolitica` se añadió después
    sin tocarla. Resultado —medido el 20-09-2026—: una página con un manejador
    en línea salía con **traza de Python y código 1** en vez de con la negativa
    de esta casa, y dejaba 409 ficheros montados y ningún `rueda.json`.

    Es el patrón de esta casa al revés: una lista que hay que acordarse de
    ampliar. Con una raíz común, la negativa que se escriba mañana ya está
    cazada el día que se escribe. Lo guarda una prueba que recorre el módulo:
    toda excepción de aquí o hereda de esta, o consta a propósito como de otra
    cosa.
    """


class SinPyodide(NoSeMonta):
    """No está el intérprete alojado aquí, así que no se monta el sitio."""


class PyodideQueNoCuadra(NoSeMonta):
    """Un fichero del intérprete no es el que este repositorio fijó.

    Distinta de `SinPyodide` a propósito: que falte se arregla bajándolo y no
    quiere decir nada; que esté y no cuadre quiere decir que lo que se iba a
    servir no es lo que se probó, y eso no se arregla solo.
    """


def _bajar(url: str, destino: Path) -> bytes:
    from urllib.request import urlopen

    with urlopen(url) as respuesta:  # noqa: S310 - es una URL fija nuestra
        crudo = respuesta.read()
    destino.write_bytes(crudo)
    return crudo


def _lo_que_hace_falta(carpeta: Path) -> list[str]:
    """Los ficheros del intérprete más los de los paquetes y sus dependencias.

    El candado dice cómo se llama el fichero de cada paquete y de qué depende.
    Preguntárselo a él, en vez de escribir los nombres a mano, es lo que evita
    que subir la versión de Pyodide deje la página pidiendo un `.whl` que ya no
    existe —y que eso no se note hasta que alguien la abra—.
    """
    candado = json.loads((carpeta / "pyodide-lock.json").read_text(encoding="utf-8"))
    paquetes = candado.get("packages", {})
    porNombre = {n.lower(): d for n, d in paquetes.items()}

    ficheros = list(_NUCLEO)
    pendientes = list(_PAQUETES_DE_PYODIDE)
    vistos: set[str] = set()
    while pendientes:
        nombre = pendientes.pop().lower()
        if nombre in vistos:
            continue
        vistos.add(nombre)
        datos = porNombre.get(nombre)
        if datos is None:
            continue
        ficheros.append(datos["file_name"])
        pendientes.extend(datos.get("depends", []))
    return ficheros


def _que_cuadre(nombre: str, crudo: bytes, de_donde) -> str:
    """La huella de unos bytes, si es la que este repositorio fijó.

    Si no, no devuelve nada: se niega. Lo que se sirve al navegador de quien
    visita la página tiene que ser lo que aquí se probó, y «casi» no vale: un
    `python_stdlib.zip` cortado a la mitad se apunta tan bien como uno entero.
    """
    esperada = HUELLAS_DE_PYODIDE.get(nombre)
    medida = hashlib.sha256(crudo).hexdigest()
    if esperada is None:
        raise PyodideQueNoCuadra(
            f"«{nombre}» hace falta para servir el intérprete y no tiene huella "
            f"fijada en `HUELLAS_DE_PYODIDE`. Si de verdad hace falta, se mira "
            "qué es y se escribe su huella ahí; lo que no se sabe qué es no se "
            "reparte."
        )
    if medida != esperada:
        raise PyodideQueNoCuadra(
            f"«{nombre}» ({de_donde}) no es el que este repositorio fijó: "
            f"aquí consta {esperada[:12]}... y esos bytes resumen "
            f"{medida[:12]}... . No se monta. Si el fichero está a medias de "
            "una descarga cortada, bórralo y vuelve a traerlo; si el CDN ha "
            "cambiado de verdad, es un cambio de intérprete y se mira a mano."
        )
    return medida


def traer_pyodide(
    destino: str | Path = CARPETA_DE_PYODIDE,
    version: str = VERSION_DE_PYODIDE,
) -> list[str]:
    """Baja el intérprete, lo contrasta con lo fijado y apunta las huellas.

    Las huellas no son ceremonia. Estos ficheros se sirven a quien visite la
    página, así que lo que se reparte tiene que poder contrastarse con lo que
    se fijó —ver `HUELLAS_DE_PYODIDE`—. `HUELLAS.txt` se sigue escribiendo al
    lado, pero ya no decide nada: es el recibo de lo que hay en esa carpeta,
    para que `--sitio` pueda ver si algo se ha estropeado después.
    """
    carpeta = Path(destino)
    if version != VERSION_DE_PYODIDE:
        raise PyodideQueNoCuadra(
            f"Las huellas fijadas aquí son las de Pyodide {VERSION_DE_PYODIDE} "
            f"y se ha pedido {version}, así que no habría con qué contrastar lo "
            "que se baje. Subir de versión es cambiar el intérprete que corre "
            "en el navegador de quien visita: se baja a mano, se mira qué trae "
            "y se escriben sus huellas en `HUELLAS_DE_PYODIDE`."
        )
    carpeta.mkdir(parents=True, exist_ok=True)
    raiz = DE_DONDE_SE_BAJA.format(version)

    # El candado primero: sin él no se sabe qué más hace falta. Y se mira antes
    # de creerle, porque de un candado que no es el fijado tampoco vale la
    # lista de lo que dice que hace falta.
    candado = "pyodide-lock.json"
    _que_cuadre(candado, _bajar(raiz + candado, carpeta / candado), raiz)

    huellas: dict[str, str] = {}
    traidos: list[str] = []
    for nombre in _lo_que_hace_falta(carpeta):
        ruta = carpeta / nombre
        if ruta.is_file():
            crudo = ruta.read_bytes()
            de_donde = str(ruta)
        else:
            crudo = _bajar(raiz + nombre, ruta)
            de_donde = raiz
            traidos.append(nombre)
        # También lo que ya estaba. Reutilizar sin mirar es lo que permitía que
        # una descarga cortada de ayer se apuntara hoy como buena.
        huellas[nombre] = _que_cuadre(nombre, crudo, de_donde)

    lineas = [
        f"# Pyodide {version}, bajado de {raiz}",
        "# Se sirve desde el propio sitio para que el navegador de quien visita",
        "# la página no tenga que hablar con nadie más.",
        "",
    ]
    lineas += [f"{h}  {n}" for n, h in sorted(huellas.items())]
    (carpeta / NOMBRE_DE_HUELLAS).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return traidos


def _apuntadas(carpeta: Path) -> dict[str, str]:
    """Lo que dice `HUELLAS.txt` de esa carpeta, si está."""
    ruta = carpeta / NOMBRE_DE_HUELLAS
    if not ruta.is_file():
        return {}
    apuntadas = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.strip() and not linea.startswith("#"):
            huella, _, nombre = linea.partition("  ")
            apuntadas[nombre.strip()] = huella.strip()
    return apuntadas


def _revisar_pyodide(carpeta: Path) -> list[str]:
    """Qué falta de lo que el candado dice que hace falta, y qué no cuadra.

    Lo que falta se devuelve; lo que **está y no cuadra** se niega aquí mismo.
    Son dos cosas distintas: que falte se arregla bajándolo, y que no cuadre
    quiere decir que lo que se iba a publicar no es lo que se trajo.

    Se contrasta con `HUELLAS.txt`, el recibo que dejó `--traer-pyodide`, y no
    con la tabla fijada: esto también corre sobre carpetas que no son la de
    Pyodide de verdad —las pruebas montan una en pequeño— y lo que aquí hay que
    cazar es que un fichero se haya estropeado **después** de traerlo. De que
    lo traído sea lo fijado se encarga `traer_pyodide`, que es donde se puede.
    """
    if not (carpeta / "pyodide-lock.json").is_file():
        raise SinPyodide(
            f"No está «{carpeta}», que es donde vive el intérprete que se "
            "sirve con la página. Tráelo con `python -m validador "
            "--traer-pyodide`. Se baja una vez y pesa unos 8 MB."
        )
    hacen_falta = _lo_que_hace_falta(carpeta)
    faltan = [n for n in hacen_falta if not (carpeta / n).is_file()]

    apuntadas = _apuntadas(carpeta)
    for nombre in hacen_falta:
        esperada = apuntadas.get(nombre)
        if nombre in faltan or esperada is None:
            continue
        medida = hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest()
        if medida != esperada:
            raise PyodideQueNoCuadra(
                f"«{nombre}» no es el que se trajo: «{NOMBRE_DE_HUELLAS}» "
                f"apunta {esperada[:12]}... y el fichero resume "
                f"{medida[:12]}... . Algo lo ha cambiado después de bajarlo, y "
                "eso se sirve a quien abra la página. Vuelve a traerlo con "
                "`python -m validador --traer-pyodide`."
            )
    return faltan


# --- El sitio que se publica -----------------------------------------------

# El manifiesto del wheel. La página necesita saber cómo se llama el `.whl`
# para instalarlo, y el nombre lleva la versión dentro. Sirviendo la carpeta
# en desarrollo basta con leer el listado del directorio; **un sitio publicado
# no tiene listado**: Vercel devuelve 404 y la página se queda sin validador.
# Así que al montar el sitio se deja escrito cuál es.
NOMBRE_DE_LA_RUEDA = "rueda.json"

# Lo que deja cada montaje en la carpeta que monta, y lo primero que escribe.
# Montar empieza por borrar la carpeta entera, y sin esto la borraba **fuera la
# que fuera**: `--sitio ..` lanzado desde Factura-e se llevaba la carpeta de
# trabajo, con `Proyecto 1` dentro, y salía con código 0. Ahora solo se borra
# una carpeta vacía o una que lleve este testigo, o sea, una que montó esto.
#
# Se escribe nada más crear la carpeta y no al final, a propósito: un montaje
# que se para a medias tiene que poder repetirse sin que haya que borrar a mano
# lo que dejó.
TESTIGO_DEL_SITIO = ".montado-por-glosa"

# Quién sabe dónde están el wheel y las facturas de ejemplo. Lo saben las dos
# páginas —la herramienta y el banco—, y por eso está escrito una sola vez en
# el cargador que las dos cargan: dos copias son la forma de que un día
# arreglen cosas distintas y nadie sepa cuál corre.
_CARGADOR = "glosa.js"

# Cómo lo llaman las páginas. Al montar, esta línea se cambia por la misma con
# `?v=` y la huella del fichero detrás.
#
# **Por qué.** Es la tercera vez que este proyecto se tropieza con lo mismo: el
# navegador sirve de su caché una copia vieja y lo que corre no es lo que se
# acaba de cambiar. Pasó con el wheel, pasó con el fichero de comprobaciones
# —se añadieron tres, se recargó, y la página siguió diciendo «las 33 pasan»—,
# y pasó otra vez con esta página mientras se escribía. Nunca se rompe nada:
# sale todo bien y no es lo que crees que has probado, que es el peor fallo que
# puede tener algo que existe para comprobar cosas.
#
# La huella es del contenido, así que la dirección solo cambia cuando el
# fichero cambia de verdad.
_LLAMADA_AL_CARGADOR = '<script src="./glosa.js"></script>'

# Y el estilo, por lo mismo. Estuvo repetido dentro de cada página hasta que
# fueron tres: la copia del banco ya se había quedado sin cinco variables de
# color que la de la herramienta sí tenía, y nada parecía roto —simplemente
# había reglas que no pintaban lo que decían pintar—.
_ESTILO = "glosa.css"
# La carpeta de la letra. `literata.woff2` la genera `web/marca/letra.py`, y
# `OFL.txt` va al lado porque es la única condición que la licencia pone al
# redistribuir la fuente: publicarla sin ella sería incumplirla.
# El dominio con el que se publica. De aquí salen las direcciones absolutas
# que hay que escribir enteras aunque el sitio se sirva de sí mismo: la
# canónica de cada página, el sitemap y la tarjeta social. Un enlace relativo
# no vale en ninguno de los tres.
#
# El ápice redirige aquí con un 308, así que **es este y no `glosa-e.com` a
# secas**: decir la otra en la canónica sería mandar al buscador a una
# dirección que le va a contestar con una mudanza.
DOMINIO = "https://www.glosa-e.com"

# La tarjeta que se enseña cuando alguien pega el enlace en un sitio ajeno.
# La genera `herramientas/tarjeta.py` y va versionada, como la marca: no se
# arma al montar porque haría falta una biblioteca de imágenes en el
# despliegue para producir un fichero que cambia una vez cada seis meses.
_MARCA = "marca"
_TARJETA = "tarjeta.png"
# Lo que se copia de `web/marca/`, y nada más: ahí viven también los guiones
# que generan la marca y la letra, que son herramientas y no se publican.
_DE_LA_MARCA = (_TARJETA,)

_LETRA = "letra"
_TIPOGRAFIA = "literata.woff2"
_LICENCIA_DE_LA_LETRA = "OFL.txt"
_ESTILO_PIDE_LETRA = "./letra/literata.woff2"
_LLAMADA_AL_ESTILO = '<link rel="stylesheet" href="./glosa.css">' 

# Las dos líneas del cargador que dicen dónde están. En el repositorio apuntan
# un nivel arriba, porque en desarrollo se sirve el repositorio entero; en el
# sitio publicado van al lado. Se sustituyen aquí en vez de dejar que la página
# lo adivine en tiempo de ejecución: si alguien renombra la constante, esto
# falla al montar y no en el navegador de un desconocido.
_RUTAS_DEL_SITIO = (
    ('const DIST = "../dist/";', 'const DIST = "./dist/";'),
    ('const EJEMPLOS_EN = "../ejemplos/";', 'const EJEMPLOS_EN = "./ejemplos/";'),
    # La version va **dentro de la direccion**, y no por gusto: el sitio se
    # sirve diciendo que estos ficheros se pueden guardar un ano entero, y eso
    # solo se puede prometer si al subir la version cambia la direccion. Con
    # `./pyodide/` a secas, el dia que se subiera de version habria navegadores
    # corriendo el interprete viejo durante un ano sin forma de avisarles.
    ('const PYODIDE_EN = "../vendor/pyodide/";',
     f'const PYODIDE_EN = "./pyodide/{VERSION_DE_PYODIDE}/";'),
)

# Lo que se copia tal cual desde `web/`. El banco va porque es la mitad de la
# promesa: la herramienta dice que corre entera en el navegador de quien la
# usa, y el banco es donde eso se comprueba sin creernos a nosotros. El LEEME,
# porque explica qué prueba cada comprobación.
_DE_LA_PAGINA = (
    "index.html", "banco.html", "legal.html", "prueba.py", "LEEME.md",
    # Vercel sirve `404.html` en todo lo que no encuentra, y con eso se dejan
    # de servir dos cosas que no eran nuestras: su pagina generica, en ingles y
    # sin decir de quien es el sitio, y un callejon sin salida para quien
    # teclea el codigo en minusculas.
    "404.html",
    # `incidencias.html` y `bitacora.html` no van aquí sino por su propio
    # camino: son plantillas y hay que generarlas, no copiarlas. La primera
    # rellena el catálogo de códigos; la segunda pone el armazón a cada
    # entrada, que es lo que evita que el menú se escriba una vez por artículo.
    "tesis.html",
)


class SinRueda(NoSeMonta):
    """No hay wheel que servir, así que la página no arrancaría."""


class SinPagina(NoSeMonta):
    """Falta el index.html, o ya no dice dónde busca sus cosas."""


class RuedaVieja(NoSeMonta):
    """El wheel de `dist/` no es el del código que hay ahora mismo."""


class NoEsUnSitio(NoSeMonta):
    """La carpeta de destino tiene cosas y no las ha montado `--sitio`."""


def _se_puede_borrar(destino: Path) -> None:
    """Se niega a borrar lo que no ha montado esto. Ver `TESTIGO_DEL_SITIO`.

    Tres negativas. Un fichero no es una carpeta de sitio. La carpeta desde la
    que se trabaja, o una que la contenga, no se borra **nunca**, lleve lo que
    lleve: es el caso que más destroza y el único que no se arregla montando
    otra vez. Y una carpeta con cosas dentro solo se borra si lleva el testigo.
    """
    if not destino.exists():
        return
    if not destino.is_dir():
        raise NoEsUnSitio(
            f"«{destino}» es un fichero, no una carpeta. Montar el sitio empieza "
            "por borrar el destino, y esto no se borra."
        )
    real = destino.resolve()
    aqui = Path.cwd().resolve()
    if real == aqui or real in aqui.parents:
        raise NoEsUnSitio(
            f"«{destino}» es la carpeta desde la que se trabaja, o una que la "
            "contiene. Montar el sitio empieza por borrar el destino entero, y "
            "eso se llevaría el repositorio. Elige una carpeta nueva, como "
            "`sitio`."
        )
    if not any(destino.iterdir()):
        return
    if (destino / TESTIGO_DEL_SITIO).is_file():
        return
    raise NoEsUnSitio(
        f"«{destino}» tiene cosas dentro y no las ha montado `--sitio`: no lleva "
        f"el testigo «{TESTIGO_DEL_SITIO}» que deja cada montaje. Montar empieza "
        "por borrar la carpeta entera, así que no se toca. Si es un sitio montado "
        "antes de que existiera el testigo, bórrala a mano una vez; si no, elige "
        "otra carpeta."
    )


class SinPaquete(NoSeMonta):
    """Se ha exigido el paquete de esquemas y anclas, y no está o está vacío.

    Solo se levanta con `exigir_paquete=True`. Montar sin paquete sigue siendo
    válido y se sigue contando por pantalla: hace falta para probar en local
    sin tener que armar 389 anclas. Lo que no puede pasar es **publicar** así
    sin enterarse, y un aviso por pantalla no lo impide cuando quien monta es
    una construcción automática que solo mira el código de salida.
    """


# La expresión SPDX tal como está escrita en `pyproject.toml`. Se lee con una
# expresión regular y no con `tomllib` a propósito: `tomllib` es de 3.11 y aquí
# se admite 3.10, y para una línea que es literal en el fichero un parser
# entero no compra nada.
_LICENCIA_EN_PYPROJECT = re.compile(r'^license\s*=\s*"([^"]+)"', re.MULTILINE)


def licencia_declarada(raiz: Path) -> str | None:
    """Qué licencia dice el proyecto que tiene, o None si no hay `pyproject`.

    None no es un fallo: `rueda_desfasada` se puede llamar desde un paquete
    instalado, donde el `pyproject.toml` no viaja. Lo que no puede pasar es
    confundir «no hay con qué comparar» con «coinciden».
    """
    pyproject = raiz / "pyproject.toml"
    if not pyproject.is_file():
        return None
    encontrada = _LICENCIA_EN_PYPROJECT.search(
        pyproject.read_text(encoding="utf-8"))
    return encontrada.group(1) if encontrada else None


def _licencia_de_la_rueda(zip_de_la_rueda) -> tuple[str | None, bool]:
    """Qué licencia anuncia el wheel, y si lleva el texto dentro.

    Son dos cosas distintas y las dos importan: `License-Expression` es lo que
    el wheel *dice*, y `dist-info/licenses/` es lo que *entrega*. Anunciar una
    licencia sin adjuntar sus condiciones es no haberla puesto.
    """
    anunciada, texto_dentro = None, False
    for nombre in zip_de_la_rueda.namelist():
        if nombre.endswith(".dist-info/METADATA"):
            cabecera = zip_de_la_rueda.read(nombre).decode("utf-8", "replace")
            for linea in cabecera.splitlines():
                if linea.startswith("License-Expression:"):
                    anunciada = linea.split(":", 1)[1].strip()
                if not linea.strip():      # el cuerpo del README, ya no hay más
                    break                  # cabeceras que mirar
        if ".dist-info/licenses/" in nombre:
            texto_dentro = True
    return anunciada, texto_dentro


def rueda_desfasada(rueda: Path, fuentes: Path | None = None) -> list[str]:
    """Qué módulos del paquete no son los que lleva ese `.whl`.

    Existe por un fallo que salió montando el sitio: `--sitio` no construye el
    wheel, coge el que haya en `dist/`, y el que había era de tres días antes
    de que existiera `ocsp.py`. Dijo «Montado sitio» en verde. La página habría
    arrancado, bajado catorce megas de intérprete e importado un
    `revocacion.py` que hace `from validador import ocsp`: ImportError, y el
    validador entero sin arrancar.

    Se comparan **los bytes**, no las fechas. Una fecha depende del orden en
    que se copiaron los ficheros y de la máquina; los bytes son lo que se va a
    ejecutar. Y así se caza también el caso que una lista de módulos no
    cazaría: un fichero que ya estaba y ha cambiado.
    """
    fuentes = Path(fuentes) if fuentes is not None else Path(__file__).parent
    dentro: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(rueda) as zip_de_la_rueda:
            for nombre in zip_de_la_rueda.namelist():
                if nombre.startswith("validador/") and nombre.endswith(".py"):
                    dentro[nombre.rsplit("/", 1)[-1]] = zip_de_la_rueda.read(nombre)
    except (zipfile.BadZipFile, OSError) as error:
        # Un wheel que ni se abre es peor que uno viejo, y lo que no puede
        # pasar es que salga como un BadZipFile a media función, que no se
        # parece en nada a su causa.
        return [f"no se puede abrir el wheel ({error})"]

    desfasados = []
    for ruta in sorted(fuentes.glob("*.py")):
        if ruta.name not in dentro:
            desfasados.append(f"{ruta.name} (no viaja en el wheel)")
        elif dentro[ruta.name] != ruta.read_bytes():
            desfasados.append(f"{ruta.name} (el del wheel es otro)")

    # La licencia va aquí y no en una prueba suelta porque el daño ocurre aquí:
    # `--sitio` no construye el wheel, copia el de `dist/`. El día que se pasó
    # de MIT a AGPL, el `pyproject.toml` cambió y el wheel de `dist/` siguió
    # siendo el de antes; los módulos eran idénticos byte a byte, así que la
    # comparación de arriba lo daba por bueno y la página habría repartido a
    # cada visitante un motor que se anuncia con la licencia anterior. Es el
    # fallo de siempre de esta casa —algo viejo haciéndose pasar por lo de hoy,
    # y todo en verde—, y la única diferencia con las cuatro veces anteriores es
    # que aquí no lo ve nadie: la licencia no se nota al usar la página.
    declarada = licencia_declarada(fuentes.parent)
    if declarada is not None:
        anunciada, texto_dentro = _licencia_de_la_rueda_por_ruta(rueda)
        if anunciada != declarada:
            desfasados.append(
                f"la licencia (el proyecto dice «{declarada}» y el wheel "
                f"«{anunciada or 'no dice ninguna'}»)")
        elif not texto_dentro:
            desfasados.append(
                f"la licencia (el wheel anuncia «{declarada}» y no lleva el "
                "texto dentro, así que anuncia condiciones que no entrega)")
    return desfasados


def _licencia_de_la_rueda_por_ruta(rueda: Path) -> tuple[str | None, bool]:
    """`_licencia_de_la_rueda` abriendo el fichero, para no colar la excepción.

    El zip ya se abrió y se cerró arriba; volver a abrirlo cuesta nada y evita
    tener que sostener el descriptor abierto por media función.
    """
    try:
        with zipfile.ZipFile(rueda) as zip_de_la_rueda:
            return _licencia_de_la_rueda(zip_de_la_rueda)
    except (zipfile.BadZipFile, OSError):
        return None, False


@dataclass(frozen=True)
class Sitio:
    """Qué ha quedado montado, para poder decirlo antes de publicarlo."""

    carpeta: Path
    rueda: str
    ejemplos: int
    con_paquete: bool
    bytes: int


def _pesa(carpeta: Path) -> int:
    return sum(f.stat().st_size for f in carpeta.rglob("*") if f.is_file())


def _revisar_el_paquete(pagina: Path) -> None:
    """Que el paquete esté, y que traiga algo dentro.

    Las dos preguntas, no una. Que el fichero exista no dice nada: un zip
    armado sin esquemas o sin anclas se copia, se sirve y se descomprime sin
    error, y deja al validador comprobando solo el contenido —sin la forma y
    sin de quién es la firma— mientras la ficha de la página anuncia unas
    cifras que no están. Es el mismo aprobado de más que la huella sin
    comprobar, un piso más arriba.
    """
    zip_ = pagina / NOMBRE
    ficha = pagina / MANIFIESTO
    faltan = [str(f) for f in (zip_, ficha) if not f.is_file()]
    if faltan:
        raise SinPaquete(
            f"Se ha exigido el paquete de esquemas y anclas y falta "
            f"{', '.join(faltan)}. Un sitio sin él arranca y valida el "
            "contenido, pero no comprueba ni la forma ni de quién es la firma. "
            "Ármalo con `python -m validador --empaquetar`, o monta sin "
            "`--exigir-paquete` si es a propósito."
        )

    try:
        dice = json.loads(ficha.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SinPaquete(
            f"«{ficha}» no se deja leer ({error}), así que no se puede saber "
            "qué trae el paquete."
        ) from None

    vacias = [nombre for nombre, clave in (
        ("esquemas XSD", "esquemas"),
        ("anclas de firma", "anclas"),
        ("anclas de sellado", "anclas_de_sellos"),
    ) if not dice.get(clave)]
    if vacias:
        raise SinPaquete(
            f"El paquete está armado pero no trae {', '.join(vacias)}, y "
            f"«{ficha.name}» lo dice. Publicarlo así anunciaría en cada "
            "informe unas comprobaciones que no se hacen."
        )


# --- Lo que hace falta para que a esto se llegue desde fuera ---------------
#
# Hasta aquí el sitio se montaba entero y **no existía para ningún buscador**:
# sin `robots.txt`, sin `sitemap.xml`, sin canónica y sin tarjeta social. Una
# herramienta que nadie encuentra no le sirve a nadie, y esto no se nota desde
# dentro: la página funciona perfectamente para quien ya sabe la dirección.
#
# Las tres cosas se escriben al final y de una vez, sobre lo que haya quedado
# montado, y no página a página. Así no puede pasar lo de siempre —que una
# página nueva salga sin ellas y nadie se entere—: si está en la carpeta, se
# le pone.

# La unica que no se indexa ni lleva tarjeta. Arriba esta escrito que esto se
# hace de una vez sobre lo que haya quedado montado, y **por que**: para que una
# pagina nueva no salga sin canonica sin que nadie se entere. La excepcion va
# aqui, con nombre y en una sola linea, porque una pagina de error no es
# contenido: en el sitemap seria decirle a un buscador que indexe el sitio por
# donde no hay nada, y una tarjeta social suya seria una vista previa de un
# callejon. Lleva su `noindex` escrito dentro.
_FUERA_DEL_INDICE = ("404.html",)

_FIN_DE_LA_CABECERA = "</head>"
_RE_TITULO = re.compile(r"<title>(.*?)</title>", re.S)
_RE_DESCRIPCION = re.compile(r'<meta name="description" content="([^"]*)">')


def _direccion(nombre: str) -> str:
    """La dirección limpia de una página montada.

    `vercel.json` lleva `cleanUrls`, así que lo que se sirve de verdad es
    `/incidencias` y `/incidencias.html` contesta con un 308. La canónica y el
    sitemap tienen que decir la de destino, no la que redirige.
    """
    if nombre == "index.html":
        return DOMINIO + "/"
    return DOMINIO + "/" + nombre.removesuffix(".html")


def _con_tarjeta(texto: str, url: str, nombre: str, huella_de_la_tarjeta: str) -> str:
    """Le pone a una página su canónica y su tarjeta social.

    Se saca de lo que la propia página ya dice —su `<title>` y su
    `description`—, y no de una tabla escrita aparte: una tabla se queda
    atrás y entonces la tarjeta anuncia una página que ya no es esa.
    """
    if _FIN_DE_LA_CABECERA not in texto:
        raise SinPagina(
            f"«{nombre}» no tiene `{_FIN_DE_LA_CABECERA}`, así que no hay "
            "dónde ponerle la canónica ni la tarjeta. Y este es de los que no "
            "dan error: `replace` sobre lo que no está no falla, devuelve el "
            "texto igual, y la página se publica sin nada de esto."
        )
    titulo = _RE_TITULO.search(texto)
    descripcion = _RE_DESCRIPCION.search(texto)
    if not titulo or not descripcion:
        falta = "un <title>" if not titulo else "una descripción"
        raise SinPagina(
            f"«{nombre}» no tiene {falta}, así que no se le puede poner ni la "
            "canónica ni la tarjeta. Publicada así, en un buscador saldría sin "
            "título o sin resumen, que es peor que no salir: se ve, y se ve mal."
        )
    limpio = titulo.group(1).replace("&middot;", "·").strip()
    limpio = " ".join(limpio.split()).replace('"', "&quot;")
    resumen = descripcion.group(1).replace('"', "&quot;")
    # Con la huella de la imagen detrás, como el estilo y el cargador. Sin
    # ella la dirección de la tarjeta era la misma para siempre, y quien pinta
    # la vista previa de un enlace —Telegram, WhatsApp, LinkedIn— la guarda por
    # dirección: el 25-09-2026 Telegram enseñaba la tarjeta de antes con la
    # nueva publicada hacía dos horas. Una dirección que no cambia no tiene por
    # qué volver a pedirse, y nadie de fuera nos va a avisar de que no lo hizo.
    tarjeta = f"{DOMINIO}/{_MARCA}/{_TARJETA}?v={huella_de_la_tarjeta}"
    bloque = (
        f'<link rel="canonical" href="{url}">\n'
        f'<meta property="og:type" content="website">\n'
        f'<meta property="og:site_name" content="Glosa-e">\n'
        f'<meta property="og:locale" content="es_ES">\n'
        f'<meta property="og:url" content="{url}">\n'
        f'<meta property="og:title" content="{limpio}">\n'
        f'<meta property="og:description" content="{resumen}">\n'
        f'<meta property="og:image" content="{tarjeta}">\n'
        f'<meta property="og:image:width" content="1200">\n'
        f'<meta property="og:image:height" content="630">\n'
        f'<meta property="og:image:alt" content="Glosa-e, la factura '
        f'electrónica en castellano">\n'
        f'<meta name="twitter:card" content="summary_large_image">\n'
    )
    return texto.replace(_FIN_DE_LA_CABECERA, bloque + _FIN_DE_LA_CABECERA, 1)


def _sitemap(paginas: list[str]) -> str:
    """El índice de lo publicado, para que un buscador no tenga que adivinar.

    Sin `lastmod` **a propósito**. Google lo usa si se lo puede creer, y aquí
    lo único que se podría poner es la fecha en que se montó el sitio, que es
    la misma para las 168 páginas y no dice nada de si el contenido cambió.
    Una fecha que miente vale menos que ninguna.
    """
    urls = "".join(f"  <url><loc>{_direccion(n)}</loc></url>\n" for n in paginas)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n"
    )


# Un enlace a otro sitio se abre en otra pestaña.
#
# Se hace aquí y no a mano en cada página por lo de siempre: a mano se escriben
# los de hoy y se olvidan los de mañana. Hoy son ocho —dos en la portada, uno
# en el aviso legal, cinco en una entrada de la bitácora— y cada entrada nueva
# trae los suyos, porque la bitácora **exige** un pie de fuentes con un enlace.
#
# `noopener` no es cosmética: sin él la página que se abre recibe un puntero a
# esta por `window.opener` y puede cambiarla de sitio desde su pestaña. Y
# `noreferrer` para no ir contando a un tercero desde dónde se llega.
_RE_ANCLA = re.compile(r"<a\b[^>]*>", re.I)
_RE_HREF = re.compile(r'href="([^"]*)"', re.I)
_RE_REL = re.compile(r'rel="([^"]*)"', re.I)


def _es_de_fuera(url: str) -> bool:
    return url.startswith(("http://", "https://")) and not url.startswith(DOMINIO)


def _hacia_fuera(texto: str) -> tuple[str, int]:
    """Le pone `target` y `rel` a los enlaces que se van del sitio."""
    cuantos = 0

    def _una(encaje: re.Match[str]) -> str:
        nonlocal cuantos
        etiqueta = encaje.group(0)
        href = _RE_HREF.search(etiqueta)
        if not href or not _es_de_fuera(href.group(1)) or "target=" in etiqueta:
            return etiqueta
        cuantos += 1
        rel = _RE_REL.search(etiqueta)
        if rel:
            valores = sorted(set(rel.group(1).split()) | {"noopener", "noreferrer"})
            etiqueta = (etiqueta[: rel.start()] + 'rel="' + " ".join(valores)
                        + '"' + etiqueta[rel.end():])
        else:
            etiqueta = etiqueta[:-1].rstrip() + ' rel="noopener noreferrer">'
        return etiqueta[:-1].rstrip() + ' target="_blank">'

    return _RE_ANCLA.sub(_una, texto), cuantos


# --- Los enlaces de casa, a su dirección limpia ------------------------------
#
# `cleanUrls` sirve `/legal` y contesta `/legal.html` con un 308. La canónica y
# el sitemap decían la limpia desde el principio, pero los enlaces de una
# página a otra seguían diciendo la que redirige. Medido en producción el
# 25-09-2026: 225 por ficha de código, 396 en el catálogo y 9 en la bitácora.
# Search Console lo enseñaba así: 19 páginas «con redirección», y las dos
# formas de la misma página —`codigo-BR-47` y `codigo-BR-47.html`, y lo mismo
# con BR-51— recibiendo impresiones por separado. Con 295 páginas que Google
# conocía y no había visitado, cada enlace le costaba dos peticiones en vez de
# una.
#
# Se arregla al montar y no en las plantillas, por lo mismo que la canónica:
# las plantillas de `web/` se sirven en local con `http.server`, que no sabe
# nada de `cleanUrls`, y ahí `./legal` es un 404. Lo que se publica sí lo sabe.
# Para ver en local el sitio montado como lo sirve Vercel está
# `herramientas/servir_sitio.py`.
#
# Y **se niega** en vez de dejarlo pasar. Un enlace de casa escrito de otra
# manera —sin el `./`, o desde la raíz— no lo toca la expresión, y sin la
# negativa volvería a publicarse la redirección sin que nadie se enterara, que
# es exactamente como estuvo desde el primer día.
_RE_DE_CASA = re.compile(r'href="\./([A-Za-z0-9._-]+)\.html((?:#[^"]*)?)"')
_NO_SON_PAGINAS = ("mailto:", "data:", "tel:", "javascript:", "#")


def _a_la_limpia(texto: str) -> tuple[str, int]:
    """`./legal.html#aviso` pasa a `./legal#aviso`, y `./index.html` a `./`."""
    cuantos = 0

    def _una(encaje: re.Match[str]) -> str:
        nonlocal cuantos
        cuantos += 1
        nombre, ancla = encaje.group(1), encaje.group(2)
        return f'href="./{"" if nombre == "index" else nombre}{ancla}"'

    return _RE_DE_CASA.sub(_una, texto), cuantos


def _de_casa_con_html(texto: str) -> list[str]:
    """Los enlaces de casa que siguen acabando en `.html`: los que no se han
    sabido limpiar."""
    quedan = []
    for url in _RE_HREF.findall(texto):
        if url.startswith(_NO_SON_PAGINAS) or _es_de_fuera(url):
            continue
        if url.split("#", 1)[0].split("?", 1)[0].endswith(".html"):
            quedan.append(url)
    return quedan


# --- La política de contenido ------------------------------------------------
#
# La página promete que no le pide nada a nadie, y hasta aquí eso lo sostenían
# el código y una comprobación del banco que cuenta las peticiones **después**
# de hechas. La política de contenido (CSP) cambia la naturaleza de la frase:
# el navegador tiene orden de no pedirle nada a otro dominio —ni scripts, ni
# datos, ni imágenes, ni letras—, y si un cambio de mañana lo intentara, se
# negaría él. Pasa de «no lo hacemos» a «no se puede».
#
# Va en un <meta> puesto al montar, y no en una cabecera de `vercel.json`,
# por tres razones: viaja con el sitio y no con el alojamiento; se prueba en
# local igual que en producción; y los scripts en línea se autorizan por su
# huella, que solo se puede calcular sobre la página que de verdad se publica.
# Una cabecera escrita a mano tendría que llevar 'unsafe-inline' para ellos, o
# se quedaría vieja el primer día que alguien tocara un script. Lo único que un
# <meta> no admite, `frame-ancestors`, va de cabecera en `vercel.json`.
#
# 'wasm-unsafe-eval' es lo que Pyodide necesita para compilar su WebAssembly, y
# no abre el `eval` de JavaScript. Los estilos van con 'unsafe-inline' porque
# hay atributos style= y esos no se autorizan por huella sin abrir más; un
# estilo tampoco saca nada fuera si imágenes y letras solo pueden venir de aquí.
#
# Y lo que la política bloquearía **en silencio** no se monta: un manejador en
# línea (onclick=) o un enlace javascript: dejarían un botón muerto sin un solo
# error en rojo, que es el fallo de siempre de este repositorio.
_RE_SCRIPT = re.compile(r"<script\b([^>]*)>(.*?)</script>", re.S | re.I)
_RE_MANEJADOR = re.compile(r"<[a-z][^>]*?\son[a-z]+\s*=", re.I)
_CHARSET = '<meta charset="utf-8">'


class SinPolitica(NoSeMonta):
    """Una página en la que la política de contenido no se puede poner bien."""


def politica_de_contenido(texto: str) -> str:
    """La política para una página, con la huella de cada script en línea.

    La huella es la del texto tal como lo lee el navegador, que convierte los
    CRLF en LF antes de nada: calculada sobre los bytes de un fichero escrito
    en Windows, no coincidiría con ninguna y la página no arrancaría.
    """
    huellas = []
    for atributos, cuerpo in _RE_SCRIPT.findall(texto):
        if "src=" in atributos:
            continue
        if atributos.strip():
            raise SinPolitica(
                f"un <script{atributos}> en línea: solo se autorizan por huella "
                "los <script> a secas, y este quedaría bloqueado sin avisar")
        cuerpo = cuerpo.replace("\r\n", "\n").replace("\r", "\n")
        huella = base64.b64encode(hashlib.sha256(cuerpo.encode("utf-8")).digest())
        huellas.append(f"'sha256-{huella.decode('ascii')}'")
    scripts = " ".join(["'self'", *huellas, "'wasm-unsafe-eval'"])
    return (
        "default-src 'none'; "
        f"script-src {scripts}; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "base-uri 'none'; "
        "form-action 'none'"
    )


def _lo_que_la_politica_bloquearia(nombre: str, texto: str) -> None:
    """Se niega si esta página lleva algo que la política mataría en silencio.

    Separada de `_con_politica` para poder preguntarlo **antes** de montar
    nada, sobre las páginas de `web/`, y otra vez al final sobre las que de
    verdad se publican, que incluyen las generadas de una plantilla.

    Aquí no se mira el `<meta charset>`. Eso es una condición de **escribir**
    la política, y adelantarla cambiaba el diagnóstico de una página sin
    cabecera: se llevaba una queja sobre la política en vez de la que dice qué
    le pasa de verdad, que es que no tiene `</head>`.
    """
    cuerpo_sin_scripts = _RE_SCRIPT.sub("", texto)
    if _RE_MANEJADOR.search(cuerpo_sin_scripts) or 'href="javascript:' in texto:
        raise SinPolitica(
            f"«{nombre}» lleva un manejador en línea o un enlace "
            "javascript:, y la política lo bloquearía sin dar error: el "
            "botón se quedaría muerto. Pásalo a un addEventListener.")
    # Y que las huellas se puedan calcular: un `<script defer>` en línea se
    # quedaría fuera de la política y bloqueado sin decir nada.
    politica_de_contenido(texto)


def _con_politica(destino: Path) -> int:
    """Pone la política en cada página, la primera cosa de su <head>."""
    paginas = sorted(destino.glob("*.html"))
    for ruta in paginas:
        texto = ruta.read_text(encoding="utf-8")
        _lo_que_la_politica_bloquearia(ruta.name, texto)
        if texto.count(_CHARSET) != 1:
            raise SinPolitica(
                f"«{ruta.name}» no tiene un {_CHARSET} (o tiene más de uno), así "
                "que no hay dónde poner la política antes que ningún recurso")
        meta = ('<meta http-equiv="Content-Security-Policy" content="'
                + politica_de_contenido(texto) + '">')
        ruta.write_text(texto.replace(_CHARSET, _CHARSET + "\n" + meta), encoding="utf-8")
    return len(paginas)


# El buzón al que escribir si alguien encuentra un fallo de seguridad, donde se
# busca: `.well-known/security.txt`, que es el RFC 9116. Quien investiga mira
# ahí primero, y si no encuentra a dónde escribir lo normal es que lo publique
# en vez de contarlo. En una herramienta que verifica firmas eso importa.
#
# El `Expires` se calcula al montar y no se escribe a mano **a propósito**: es
# una fecha obligatoria, y una caducada dice que esto está abandonado. Puesta
# aquí, cada despliegue la renueva; si el sitio pasa un año sin desplegarse,
# caduca, que es exactamente lo que hay que decir en ese caso.
_INVESTIGADORES = ".well-known"
_SEGURIDAD = "security.txt"


def _correo_del_titular(pagina: Path) -> str:
    codigo = (pagina / _CARGADOR).read_text(encoding="utf-8")
    dentro = codigo[codigo.index("const TITULAR = {"):]
    dentro = dentro[: dentro.index("};")]
    return dict(re.findall(r'(\w+):\s*"([^"]*)"', dentro)).get("correo", "")


def _para_investigadores(destino: Path, correo: str, hoy: date) -> Path:
    if not correo:
        raise SinPagina(
            "La ficha de `glosa.js` no tiene correo, así que no hay a dónde "
            "decirle a nadie que avise de un fallo de seguridad. Un "
            "`security.txt` sin `Contact` no es válido y es peor que no "
            "tenerlo: promete un buzón que no existe."
        )
    caduca = hoy.replace(year=hoy.year + 1)
    carpeta = destino / _INVESTIGADORES
    carpeta.mkdir(parents=True, exist_ok=True)
    fichero = carpeta / _SEGURIDAD
    fichero.write_text(
        "# Glosa-e. Si encuentras un fallo de seguridad, escribe aquí antes\n"
        "# de publicarlo. Se contesta, y se dice qué se ha hecho con lo que\n"
        "# cuentes. El código del validador es AGPL-3.0-only y viaja entero\n"
        "# al navegador: se puede leer sin pedir permiso.\n"
        f"Contact: mailto:{correo}\n"
        f"Expires: {caduca.isoformat()}T00:00:00Z\n"
        "Preferred-Languages: es, en\n"
        f"Canonical: {DOMINIO}/{_INVESTIGADORES}/{_SEGURIDAD}\n",
        encoding="utf-8",
    )
    return fichero


def _para_buscadores(destino: Path) -> int:
    """Canónica, tarjeta, enlaces de salida y enlaces de casa en su forma
    limpia en cada página, y los ficheros de rigor."""
    paginas = sorted(p.name for p in destino.glob("*.html")
                     if p.name not in _FUERA_DEL_INDICE)
    if not paginas:
        raise SinPagina(
            "No ha quedado ni una página HTML que indexar, así que algo se ha "
            "montado mal antes de llegar aquí."
        )
    # La huella es de la tarjeta que se publica y no de la del repositorio:
    # es la que va a pedir quien pegue el enlace.
    huella = hashlib.sha256((destino / _MARCA / _TARJETA).read_bytes()).hexdigest()[:8]
    for nombre in paginas:
        ruta = destino / nombre
        texto, _ = _hacia_fuera(ruta.read_text(encoding="utf-8"))
        texto, _ = _a_la_limpia(texto)
        ruta.write_text(
            _con_tarjeta(texto, _direccion(nombre), nombre, huella), encoding="utf-8")
    # La de error no se indexa, pero se lee, y sus enlaces llevan a páginas
    # que sí: también a la limpia.
    for nombre in _FUERA_DEL_INDICE:
        ruta = destino / nombre
        if ruta.is_file():
            ruta.write_text(_a_la_limpia(ruta.read_text(encoding="utf-8"))[0],
                            encoding="utf-8")
    sueltos = {
        p.name: quedan for p in sorted(destino.glob("*.html"))
        if (quedan := _de_casa_con_html(p.read_text(encoding="utf-8")))
    }
    if sueltos:
        muestra = "; ".join(f"{n}: {', '.join(q[:3])}" for n, q in list(sueltos.items())[:5])
        raise SinPagina(
            f"{len(sueltos)} página(s) enlazan a otra de casa por su forma con "
            f"`.html`, que en producción es una redirección: {muestra}. Solo se "
            "limpia la forma `./nombre.html`; escribe el enlace así."
        )
    (destino / "robots.txt").write_text(
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {DOMINIO}/sitemap.xml\n",
        encoding="utf-8",
    )
    (destino / "sitemap.xml").write_text(_sitemap(paginas), encoding="utf-8")
    return len(paginas)


def montar_sitio(
    destino: str | Path,
    pagina: str | Path = "web",
    ruedas: str | Path = "dist",
    ejemplos: str | Path = "ejemplos",
    pyodide: str | Path = CARPETA_DE_PYODIDE,
    exigir_paquete: bool = False,
) -> Sitio:
    """Deja en `destino` lo que hay que subir, y nada más.

    Se monta desde el repositorio en vez de subirlo entero por dos razones. La
    primera es que hay carpetas que no pueden salir de aquí: `muestras/` son
    facturas de terceros y `anclas/` no se reparte suelta, sino dentro del
    paquete que uno ha armado y comprobado. La segunda es que la página busca
    sus cosas en sitios distintos según dónde esté, y eso se arregla al montar.

    No se niega a montar un sitio **sin** el paquete de esquemas y anclas: la
    página ya sabe decir qué deja de comprobar cuando no está. Lo que sí hace
    es contarlo, porque publicar eso sin enterarse es otra cosa. Quien publica
    de verdad pasa `exigir_paquete=True` y entonces sí se niega, que es lo
    único que sirve cuando quien monta es una construcción automática: un aviso
    por pantalla no lo lee nadie si el código de salida sigue siendo 0.
    """
    import shutil

    destino = Path(destino)
    pagina, ruedas, ejemplos = Path(pagina), Path(ruedas), Path(ejemplos)

    indice = pagina / "index.html"
    if not indice.is_file():
        raise SinPagina(f"No hay «{indice}», que es la página que se publica.")
    cargador = pagina / _CARGADOR
    if not cargador.is_file():
        raise SinPagina(
            f"No hay «{cargador}», que es quien sabe dónde buscar el wheel y "
            "las facturas de ejemplo. Sin él las dos páginas arrancan y se "
            "quedan sin validador."
        )

    faltan_de_pyodide = _revisar_pyodide(Path(pyodide))
    if faltan_de_pyodide:
        raise SinPyodide(
            "Faltan {} ficheros del intérprete en «{}»: {}. Sin ellos la "
            "página volvería a pedírselos a un CDN ajeno, y la política de "
            "privacidad dice que no lo hace. Tráelos con `python -m validador "
            "--traer-pyodide`.".format(
                len(faltan_de_pyodide), pyodide, ", ".join(faltan_de_pyodide[:3])
            )
        )

    encontradas = sorted(ruedas.glob("*.whl"))
    if not encontradas:
        raise SinRueda(
            f"No hay ningún .whl en «{ruedas}», y sin él la página no tiene "
            "validador que instalar: arrancaría, bajaría catorce megas de "
            "Pyodide y se pararía. Constrúyelo antes con "
            "`python -m build --wheel --outdir dist`."
        )
    rueda = encontradas[-1]

    desfasados = rueda_desfasada(rueda)
    if desfasados:
        raise RuedaVieja(
            "El wheel de «{}» no es el del código que hay ahora: {}. Es el "
            "fallo de siempre de este proyecto (algo de una caché haciéndose "
            "pasar por lo de hoy), y aquí no se nota sin mirar dentro: el "
            "sitio se monta, la página arranca, se baja catorce megas de "
            "intérprete y revienta al importar. Reconstrúyelo con `python -m "
            "build --wheel --outdir dist`.".format(
                rueda, ", ".join(desfasados[:4])
            )
        )

    if exigir_paquete:
        # Aquí y no al principio: sigue estando antes de escribir el primer
        # byte —montar medio sitio para tirarlo después deja una carpeta a
        # medias que el paso siguiente podría publicar igual—, pero detrás de
        # `RuedaVieja`, que es el fallo que este repositorio ha tenido cuatro
        # veces y el que peor se ve solo. Cuando las dos cosas están mal,
        # conviene leer primero esa.
        _revisar_el_paquete(pagina)

    # Las entradas de la bitácora se leen **aquí**, aunque no se escriban
    # hasta el final. Generarlas al final y comprobarlas al final significaba
    # descubrir una entrada sin fecha con el sitio ya medio montado: la
    # negativa salía bien, pero dejaba una carpeta a medias, y una carpeta a
    # medias es justo lo que el paso siguiente publica sin enterarse. Leer no
    # cuesta nada y se hace dos veces a propósito.
    if (pagina / bitacora.CARPETA).is_dir():
        bitacora.leer_entradas(pagina / bitacora.CARPETA)

    # Y la política, por lo mismo y con la misma lección. `_con_politica` corre
    # al final, que es donde tiene que correr —las huellas tienen que ser las
    # del texto que de verdad se publica—, y hasta el 20-09-2026 era también el
    # único sitio donde se miraba si una página lleva un `onclick=`. Eso no
    # depende de nada de lo que pasa por el medio: se puede ver aquí, antes de
    # escribir el primer byte. Se mira dos veces a propósito, como la bitácora.
    for html in sorted(pagina.glob("*.html")):
        _lo_que_la_politica_bloquearia(html.name, html.read_text(encoding="utf-8"))

    _se_puede_borrar(destino)
    if destino.exists():
        shutil.rmtree(destino)
    (destino / "dist").mkdir(parents=True)
    (destino / TESTIGO_DEL_SITIO).write_text(
        "Esta carpeta la monta `python -m validador --sitio`, y se borra entera "
        "al volver a montarla.\n",
        encoding="utf-8",
    )
    (destino / "ejemplos").mkdir(parents=True)

    codigo = cargador.read_text(encoding="utf-8")

    # La version esta escrita en dos sitios —aqui y en el cargador— y ahora una
    # de las dos acaba dentro de una direccion que se sirve con permiso para
    # guardarla un ano. Si se separan, el sitio se monta bajo un numero y la
    # pagina dice otro, y esa mentira dura un ano en la cache de quien pase.
    declarada = f'const VERSION_PYODIDE = "{VERSION_DE_PYODIDE}";'
    if declarada not in codigo:
        raise SinPagina(
            f"«{cargador}» no declara `VERSION_PYODIDE = "
            f'"{VERSION_DE_PYODIDE}"`, que es la versión que se monta. El '
            "número va dentro de la dirección del intérprete y esos ficheros "
            "se sirven para guardarse un año: si los dos sitios no dicen lo "
            "mismo, se publicaría una versión bajo el nombre de otra."
        )

    for busca, pon in _RUTAS_DEL_SITIO:
        if busca not in codigo:
            raise SinPagina(
                f"«{cargador}» ya no lleva la línea `{busca}`. Esa línea dice "
                "dónde busca la página el wheel y los ejemplos, y aquí se "
                "cambia para el sitio publicado. Si se ha renombrado, hay que "
                "cambiarla también en `_RUTAS_DEL_SITIO`; si no, el sitio se "
                "subiría buscando ficheros un nivel por encima de su raíz."
            )
        codigo = codigo.replace(busca, pon)
    (destino / _CARGADOR).write_text(codigo, encoding="utf-8")

    # Lo compartido viaja firmado por su contenido: la dirección cambia solo
    # cuando el fichero cambia, y así la caché del navegador no puede servir el
    # de ayer.
    estilo = pagina / _ESTILO
    if not estilo.is_file():
        raise SinPagina(f"No hay «{estilo}», que es de donde salen los colores.")
    shutil.copy2(estilo, destino / _ESTILO)

    # La letra, y la licencia que la ley de la letra obliga a llevar al lado.
    #
    # Va con negativa porque este es de los que no dan error: un `@font-face`
    # apuntando a un fichero que no está no rompe nada, el navegador compone
    # con la del sistema y la página sale «bien». En Windows eso es Georgia
    # junto a un logotipo que es Literata, y nadie se entera hasta que lo ve
    # publicado.
    letra = pagina / _LETRA
    faltan_de_la_letra = [
        n for n in (_TIPOGRAFIA, _LICENCIA_DE_LA_LETRA)
        if not (letra / n).is_file()
    ]
    if _ESTILO_PIDE_LETRA in estilo.read_text(encoding="utf-8") and faltan_de_la_letra:
        raise SinPagina(
            "«{}» pide la letra con `{}` y en «{}» falta {}. Un @font-face que "
            "apunta a lo que no está no da error: el navegador compone con la "
            "del sistema y la página parece correcta. Genérala con `python "
            "web/marca/letra.py Literata.ttf OFL.txt`.{}".format(
                estilo, _ESTILO_PIDE_LETRA, letra, ", ".join(faltan_de_la_letra),
                " La licencia OFL exige que viaje con la fuente."
                if _LICENCIA_DE_LA_LETRA in faltan_de_la_letra else "",
            )
        )
    if letra.is_dir():
        shutil.copytree(letra, destino / _LETRA, dirs_exist_ok=True)

    # La tarjeta social. Con negativa por lo mismo que la letra: un `og:image`
    # que apunta a lo que no está no rompe nada y no da error. Lo que pasa es
    # que el día que alguien pegue el enlace en LinkedIn o en un grupo sale un
    # rectángulo gris, y eso no se ve desde aquí: se ve fuera y ya publicado.
    marca = pagina / _MARCA
    faltan_de_la_marca = [n for n in _DE_LA_MARCA if not (marca / n).is_file()]
    if faltan_de_la_marca:
        raise SinPagina(
            "En «{}» falta {}, que es la imagen que se enseña cuando alguien "
            "pega el enlace fuera. Sin ella el sitio se publica con un "
            "`og:image` apuntando a una dirección que da 404, y eso no falla "
            "aquí: falla en la casa de otro. Genérala con `python -m "
            "herramientas.tarjeta`.".format(marca, ", ".join(faltan_de_la_marca))
        )
    (destino / _MARCA).mkdir(parents=True, exist_ok=True)
    for nombre in _DE_LA_MARCA:
        shutil.copy2(marca / nombre, destino / _MARCA / nombre)

    def _huella(texto: str) -> str:
        return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:8]

    sellos = (
        (
            _LLAMADA_AL_CARGADOR,
            f'<script src="./{_CARGADOR}?v={_huella(codigo)}"></script>',
            "_LLAMADA_AL_CARGADOR",
        ),
        (
            _LLAMADA_AL_ESTILO,
            '<link rel="stylesheet" href="./{}?v={}">'.format(
                _ESTILO, _huella(estilo.read_text(encoding="utf-8"))
            ),
            "_LLAMADA_AL_ESTILO",
        ),
    )

    firmadas = {constante: 0 for _, _, constante in sellos}
    for nombre in _DE_LA_PAGINA:
        origen = pagina / nombre
        if not origen.is_file():
            continue
        if origen.suffix != ".html":
            shutil.copy2(origen, destino / nombre)
            continue
        texto = origen.read_text(encoding="utf-8")
        for busca, pon, constante in sellos:
            if busca in texto:
                texto = texto.replace(busca, pon)
                firmadas[constante] += 1
        (destino / nombre).write_text(texto, encoding="utf-8")

    # El catálogo de códigos, generado del código fuente al montar. No es una
    # página que se escriba: se escriben las explicaciones, y los códigos se
    # leen de las propias llamadas a `Incidencia(...)`. Así no puede faltar
    # aquí uno que exista, que es el único fallo que importa en un catálogo:
    # mandar a buscar a un sitio donde no está.
    plantilla = pagina / pagina_incidencias.NOMBRE
    if plantilla.is_file():
        salida = destino / pagina_incidencias.NOMBRE
        texto = plantilla.read_text(encoding="utf-8")
        for busca, pon, constante in sellos:
            if busca in texto:
                firmadas[constante] += 1
        try:
            pagina_incidencias.montar_pagina(plantilla, salida)
        except ValueError as error:
            raise SinPagina(str(error)) from error
        # La huella se pone después de generar, sobre el fichero ya montado.
        generada = salida.read_text(encoding="utf-8")
        for busca, pon, _ in sellos:
            generada = generada.replace(busca, pon)
        salida.write_text(generada, encoding="utf-8")

    # La bitácora: el índice y una página por entrada, todas del mismo
    # armazón. Va detrás del catálogo porque comparte su forma —plantilla con
    # un hueco— y porque su negativa es menos grave: si falta una fecha no se
    # publica la bitácora, no se cae el validador.
    plantilla_bitacora = pagina / bitacora.NOMBRE
    if plantilla_bitacora.is_file():
        texto_bitacora = plantilla_bitacora.read_text(encoding="utf-8")
        for busca, pon, constante in sellos:
            if busca in texto_bitacora:
                firmadas[constante] += 1
        publicadas = bitacora.montar_bitacora(
            plantilla_bitacora, pagina / bitacora.CARPETA, destino
        )
        # La huella se pone después de generar, sobre cada fichero ya montado.
        for nombre in [bitacora.NOMBRE] + [e.nombre for e in publicadas]:
            salida = destino / nombre
            generada = salida.read_text(encoding="utf-8")
            for busca, pon, _ in sellos:
                generada = generada.replace(busca, pon)
            salida.write_text(generada, encoding="utf-8")

    # Una página por código, del mismo armazón y del mismo catálogo. Va
    # detrás porque necesita la plantilla ya comprobada: si a `incidencias.html`
    # le falta el hueco, lo dice el catálogo y no 160 páginas vacías.
    if plantilla.is_file():
        try:
            fichas = pagina_incidencias.montar_fichas(plantilla, destino)
        except ValueError as error:
            raise SinPagina(str(error)) from error
        for nombre in fichas:
            salida = destino / nombre
            generada = salida.read_text(encoding="utf-8")
            for busca, pon, _ in sellos:
                generada = generada.replace(busca, pon)
            salida.write_text(generada, encoding="utf-8")

    huerfanos = sorted(c for c, cuantas in firmadas.items() if not cuantas)
    if huerfanos:
        raise SinPagina(
            "Ninguna página llama a lo compartido como dice "
            + ", ".join(f"`{c}`" for c in huerfanos)
            + ", así que no se le ha podido poner la huella y el navegador "
            "puede servir de su caché una copia vieja. Si la llamada se ha "
            "escrito de otra forma, hay que cambiarla también ahí."
        )

    bajo_version = destino / "pyodide" / VERSION_DE_PYODIDE
    bajo_version.mkdir(parents=True)
    for nombre in _lo_que_hace_falta(Path(pyodide)):
        shutil.copy2(Path(pyodide) / nombre, bajo_version / nombre)

    # El wheel va bajo una carpeta con su huella dentro: `dist/<huella>/x.whl`.
    #
    # La huella tiene que ir en la **ruta** y no detras con `?v=`, porque quien
    # lo instala es `loadPackage`, y saca el nombre y la version del nombre del
    # fichero con `/^.*?([^/]*)\.whl$/`. Con una query detras lo rechaza: «is
    # not a valid package name or URL». Comprobado contra el sitio publicado.
    #
    # Asi se consiguen las dos cosas: la direccion cambia cuando el wheel
    # cambia —que es lo que impide correr el validador de ayer— y se puede
    # servir con permiso para guardarlo un ano.
    huella_rueda = hashlib.sha256(rueda.read_bytes()).hexdigest()[:8]
    (destino / "dist" / huella_rueda).mkdir(parents=True)
    shutil.copy2(rueda, destino / "dist" / huella_rueda / rueda.name)

    cuantos = 0
    for fichero in sorted(ejemplos.glob("*")):
        if fichero.is_file():
            shutil.copy2(fichero, destino / "ejemplos" / fichero.name)
            cuantos += 1

    con_paquete = (pagina / NOMBRE).is_file() and (pagina / MANIFIESTO).is_file()
    if con_paquete:
        shutil.copy2(pagina / NOMBRE, destino / NOMBRE)
        shutil.copy2(pagina / MANIFIESTO, destino / MANIFIESTO)

    # El manifiesto, y va el ultimo a proposito: firma lo que ya esta montado.
    #
    # Lo que la pagina se baja llevaba hasta ahora `?v=` con la hora, para que
    # el navegador no sirviera de su cache un wheel de ayer. Cumplia, y costaba
    # carisimo: con la hora dentro, la direccion cambia en cada visita y esos
    # ficheros —el paquete, el wheel, los ejemplos: 1,2 MB— **no se podian
    # guardar nunca**. Se bajaban enteros cada vez que alguien abria la pagina.
    #
    # Con la huella del contenido se consiguen las dos cosas: cambia cuando el
    # fichero cambia, y no cambia cuando no. La pagina la lee de aqui.
    # Lo último que se toca de cada página: la canónica y la tarjeta. Va antes
    # de las huellas a propósito, porque las huellas tienen que ser las del
    # fichero que de verdad se publica.
    _para_buscadores(destino)
    _para_investigadores(destino, _correo_del_titular(pagina), date.today())
    # La política, después de todo lo que reescribe una página: las huellas de
    # los scripts tienen que ser las del texto que se publica.
    _con_politica(destino)

    huellas = {}
    for camino in sorted(destino.rglob("*")):
        if not camino.is_file():
            continue
        relativo = camino.relative_to(destino).as_posix()
        if relativo == f"dist/{NOMBRE_DE_LA_RUEDA}":
            continue
        # La huella **entera**, no los ocho primeros. Ocho bastan para que la
        # dirección cambie cuando el fichero cambia, que es para lo único que
        # servía esto; desde el 20-09-2026 la página también las compara con
        # lo que se baja, y ahí ocho caracteres son una comprobación de
        # mentira. En el `?v=` se siguen usando los ocho primeros, así que las
        # direcciones no cambian y la caché de quien ya haya pasado vale.
        huellas[relativo] = hashlib.sha256(camino.read_bytes()).hexdigest()

    (destino / "dist" / NOMBRE_DE_LA_RUEDA).write_text(
        json.dumps({"rueda": f"{huella_rueda}/{rueda.name}", "huellas": huellas},
                   indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    return Sitio(
        carpeta=destino,
        rueda=rueda.name,
        ejemplos=cuantos,
        con_paquete=con_paquete,
        bytes=_pesa(destino),
    )
