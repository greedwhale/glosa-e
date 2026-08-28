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

**Lo que no hace, a propósito.** No se mete en el repositorio. Ni el paquete ni
las carpetas de las que sale: las anclas no se versionan porque quien controle
ese fichero controla en quién cree el validador, y eso no puede depender de que
nadie haya tocado un `.zip` en un repositorio. El paquete se arma con
`python -m validador --empaquetar`, desde las carpetas que uno mismo ha montado
y comprobado.

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


# --- El sitio que se publica -----------------------------------------------

# El manifiesto del wheel. La página necesita saber cómo se llama el `.whl`
# para instalarlo, y el nombre lleva la versión dentro. Sirviendo la carpeta
# en desarrollo basta con leer el listado del directorio; **un sitio publicado
# no tiene listado**: Vercel devuelve 404 y la página se queda sin validador.
# Así que al montar el sitio se deja escrito cuál es.
NOMBRE_DE_LA_RUEDA = "rueda.json"

# Las dos líneas de `index.html` que dicen dónde están el wheel y los
# ejemplos. En el repositorio apuntan un nivel arriba, porque en desarrollo se
# sirve el repositorio entero; en el sitio publicado van al lado. Se sustituyen
# aquí en vez de dejar que la página lo adivine en tiempo de ejecución: si
# alguien renombra la constante, esto falla al montar y no en el navegador de
# un desconocido.
_RUTAS_DEL_SITIO = (
    ('const DIST = "../dist/";', 'const DIST = "./dist/";'),
    ('const EJEMPLOS_EN = "../ejemplos/";', 'const EJEMPLOS_EN = "./ejemplos/";'),
)

# Lo que se copia tal cual desde `web/`. El LEEME va porque explica qué es esta
# página y cómo leer el banco; sin él, quien llegue de fuera ve una lista de
# comprobaciones sin saber qué prueban.
_DE_LA_PAGINA = ("prueba.py", "LEEME.md")


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

    html = indice.read_text(encoding="utf-8")
    for busca, pon in _RUTAS_DEL_SITIO:
        if busca not in html:
            raise SinPagina(
                f"«{indice}» ya no lleva la línea `{busca}`. Esa línea dice "
                "dónde busca la página el wheel y los ejemplos, y aquí se "
                "cambia para el sitio publicado. Si se ha renombrado, hay que "
                "cambiarla también en `_RUTAS_DEL_SITIO`; si no, el sitio se "
                "subiría buscando ficheros un nivel por encima de su raíz."
            )
        html = html.replace(busca, pon)
    (destino / "index.html").write_text(html, encoding="utf-8")

    for nombre in _DE_LA_PAGINA:
        if (pagina / nombre).is_file():
            shutil.copy2(pagina / nombre, destino / nombre)

    shutil.copy2(rueda, destino / "dist" / rueda.name)
    (destino / "dist" / NOMBRE_DE_LA_RUEDA).write_text(
        json.dumps({"rueda": rueda.name}, indent=2) + "\n", encoding="utf-8"
    )

    cuantos = 0
    for fichero in sorted(ejemplos.glob("*")):
        if fichero.is_file():
            shutil.copy2(fichero, destino / "ejemplos" / fichero.name)
            cuantos += 1

    con_paquete = (pagina / NOMBRE).is_file() and (pagina / MANIFIESTO).is_file()
    if con_paquete:
        shutil.copy2(pagina / NOMBRE, destino / NOMBRE)
        shutil.copy2(pagina / MANIFIESTO, destino / MANIFIESTO)

    return Sitio(
        carpeta=destino,
        rueda=rueda.name,
        ejemplos=cuantos,
        con_paquete=con_paquete,
        bytes=_pesa(destino),
    )
