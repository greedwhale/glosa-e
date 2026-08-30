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

import hashlib
import json
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
            f"{renovacion.siguiente.isoformat()}, y hoy es {dia.isoformat()}. "
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
        zf.writestr(MANIFIESTO, contenido.como_json())

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
_PAQUETES_DE_PYODIDE = ("lxml", "micropip")

CARPETA_DE_PYODIDE = "vendor/pyodide"
NOMBRE_DE_HUELLAS = "HUELLAS.txt"


class SinPyodide(Exception):
    """No está el intérprete alojado aquí, así que no se monta el sitio."""


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


def traer_pyodide(
    destino: str | Path = CARPETA_DE_PYODIDE,
    version: str = VERSION_DE_PYODIDE,
) -> list[str]:
    """Baja el intérprete y deja sus huellas escritas al lado.

    Las huellas no son ceremonia. Estos ficheros se sirven a quien visite la
    página, así que lo que se reparte tiene que poder contrastarse con lo que
    se bajó: si un día el CDN sirviera otra cosa, la única forma de enterarse
    es tener apuntado lo de antes.
    """
    carpeta = Path(destino)
    carpeta.mkdir(parents=True, exist_ok=True)
    raiz = DE_DONDE_SE_BAJA.format(version)

    # El candado primero: sin él no se sabe qué más hace falta.
    _bajar(raiz + "pyodide-lock.json", carpeta / "pyodide-lock.json")

    huellas: dict[str, str] = {}
    traidos: list[str] = []
    for nombre in _lo_que_hace_falta(carpeta):
        ruta = carpeta / nombre
        if ruta.is_file():
            crudo = ruta.read_bytes()
        else:
            crudo = _bajar(raiz + nombre, ruta)
            traidos.append(nombre)
        huellas[nombre] = hashlib.sha256(crudo).hexdigest()

    lineas = [
        f"# Pyodide {version}, bajado de {raiz}",
        "# Se sirve desde el propio sitio para que el navegador de quien visita",
        "# la pagina no tenga que hablar con nadie mas.",
        "",
    ]
    lineas += [f"{h}  {n}" for n, h in sorted(huellas.items())]
    (carpeta / NOMBRE_DE_HUELLAS).write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return traidos


def _revisar_pyodide(carpeta: Path) -> list[str]:
    """Qué falta de lo que el candado dice que hace falta."""
    if not (carpeta / "pyodide-lock.json").is_file():
        raise SinPyodide(
            f"No está «{carpeta}», que es donde vive el intérprete que se "
            "sirve con la página. Tráelo con `python -m validador "
            "--traer-pyodide`. Se baja una vez y pesa unos 8 MB."
        )
    return [n for n in _lo_que_hace_falta(carpeta) if not (carpeta / n).is_file()]


# --- El sitio que se publica -----------------------------------------------

# El manifiesto del wheel. La página necesita saber cómo se llama el `.whl`
# para instalarlo, y el nombre lleva la versión dentro. Sirviendo la carpeta
# en desarrollo basta con leer el listado del directorio; **un sitio publicado
# no tiene listado**: Vercel devuelve 404 y la página se queda sin validador.
# Así que al montar el sitio se deja escrito cuál es.
NOMBRE_DE_LA_RUEDA = "rueda.json"

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
    "index.html", "banco.html", "legal.html", "prueba.py", "LEEME.md"
)


class SinRueda(Exception):
    """No hay wheel que servir, así que la página no arrancaría."""


class SinPagina(Exception):
    """Falta el index.html, o ya no dice dónde busca sus cosas."""


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


def montar_sitio(
    destino: str | Path,
    pagina: str | Path = "web",
    ruedas: str | Path = "dist",
    ejemplos: str | Path = "ejemplos",
    pyodide: str | Path = CARPETA_DE_PYODIDE,
) -> Sitio:
    """Deja en `destino` lo que hay que subir, y nada más.

    Se monta desde el repositorio en vez de subirlo entero por dos razones. La
    primera es que hay carpetas que no pueden salir de aquí: `muestras/` son
    facturas de terceros y `anclas/` no se reparte suelta, sino dentro del
    paquete que uno ha armado y comprobado. La segunda es que la página busca
    sus cosas en sitios distintos según dónde esté, y eso se arregla al montar.

    No se niega a montar un sitio **sin** el paquete de esquemas y anclas: la
    página ya sabe decir qué deja de comprobar cuando no está. Lo que sí hace
    es contarlo, porque publicar eso sin enterarse es otra cosa.
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

    if destino.exists():
        shutil.rmtree(destino)
    (destino / "dist").mkdir(parents=True)
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

    shutil.copy2(rueda, destino / "dist" / rueda.name)

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
    huellas = {}
    for camino in sorted(destino.rglob("*")):
        if not camino.is_file():
            continue
        relativo = camino.relative_to(destino).as_posix()
        if relativo == f"dist/{NOMBRE_DE_LA_RUEDA}":
            continue
        huellas[relativo] = hashlib.sha256(camino.read_bytes()).hexdigest()[:8]

    (destino / "dist" / NOMBRE_DE_LA_RUEDA).write_text(
        json.dumps({"rueda": rueda.name, "huellas": huellas},
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
