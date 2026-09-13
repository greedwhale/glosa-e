"""Trae la copia de la norma contra la que se mide este validador.

Qué se trae y por qué
---------------------
La Comisión Europea mantiene, para el comité CEN/TC 434, el repositorio
`ConnectingEurope/eInvoicing-EN16931`: el esquematrón oficial de la EN 16931 y,
al lado, **una prueba unitaria por regla**. Cada una trae un fragmento de
factura y dice qué regla tiene que saltar (`<error>`) o no saltar
(`<success>`). Son las pruebas con las que el propio comité comprueba su
esquematrón.

Aquí sirven para lo contrario: para comprobar este validador contra ellas. Es
la opinión que faltaba el día que se descubrió que ocho reglas de IGIC e IPSI
se habían dado por inexistentes. Las comprobaciones de este repositorio salían
todas de la misma tabla y coincidían entre sí estando mal; estas no salen de
aquí.

Se trae, de un commit fijo:

- `test/Invoice-unit-UBL`, `test/CreditNote-unit-UBL` y `test/cii`: las pruebas.
- `ubl/schematron/abstract/EN16931-model.sch`: las 201 reglas del modelo.
- `ubl/schematron/codelist/EN16931-UBL-codes.sch`: las 22 de listas de códigos.
- `LICENSE.txt`: la EUPL 1.2, que acompaña a la copia porque la licencia lo pide.

Por qué se versiona, a diferencia del anexo de la AEAT
------------------------------------------------------
El PDF del anexo no se versiona y sus pruebas se saltan si no está. Con esto se
decidió lo contrario: una prueba que se salta en la máquina donde falta la
copia es un verde que no ha comprobado nada, y aquí lo que se comprueba es si
el motor dice lo mismo que la norma. Son ficheros sintéticos del comité —no
facturas de nadie—, bajo EUPL 1.2, y pesan menos de un mega.

Cómo se usa
-----------
    python -m herramientas.norma_oficial <commit>

y reescribe `tests/en16931-oficial/`. El commit va escrito en
`PROCEDENCIA.md`, y la huella de todo lo copiado en la prueba que lo usa: una
copia nueva no se cuela sin que alguien cambie esa huella a sabiendas.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import pathlib
import shutil
import sys
import urllib.request

REPO = "ConnectingEurope/eInvoicing-EN16931"
RAIZ = pathlib.Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "tests" / "en16931-oficial"

CARPETAS = ("test/Invoice-unit-UBL", "test/CreditNote-unit-UBL", "test/cii")
SUELTOS = {
    "ubl/schematron/abstract/EN16931-model.sch": "EN16931-model.sch",
    "ubl/schematron/codelist/EN16931-UBL-codes.sch": "EN16931-UBL-codes.sch",
    "LICENSE.txt": "LICENSE.txt",
}


def _bajar(url: str) -> bytes:
    # Con reintentos: la descarga fichero a fichero se cortó más de una vez al
    # montar esto, y una copia a medias no puede quedarse en el disco sin que
    # nadie lo note. Si no llega, se aborta entero.
    ultimo = None
    for _ in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except OSError as e:
            ultimo = e
    raise SystemExit(f"no se ha podido bajar {url}: {ultimo}")


def huella(carpeta: pathlib.Path) -> str:
    """SHA-256 de todo lo copiado, con los finales de línea normalizados.

    Normalizados porque git en Windows convierte LF en CRLF al sacar los
    ficheros de texto: sin esto la huella cambiaría según la máquina, y un
    guardián que salta en unas máquinas sí y en otras no enseña a ignorarlo.
    """
    h = hashlib.sha256()
    for f in sorted(p for p in carpeta.rglob("*") if p.is_file()):
        if f.name == "PROCEDENCIA.md":
            continue
        h.update(f.relative_to(carpeta).as_posix().encode("utf-8") + b"\0")
        h.update(f.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def main(commit: str) -> None:
    api = f"https://api.github.com/repos/{REPO}/contents/{{}}?ref={commit}"
    crudo = f"https://raw.githubusercontent.com/{REPO}/{commit}/{{}}"

    encargos: dict[pathlib.Path, str] = {}
    for carpeta in CARPETAS:
        lista = json.loads(_bajar(api.format(carpeta)))
        for f in lista:
            if f["type"] == "file" and f["name"].endswith(".xml"):
                destino = pathlib.Path(carpeta.split("/")[-1]) / f["name"]
                encargos[destino] = crudo.format(f["path"])
    for origen, nombre in SUELTOS.items():
        encargos[pathlib.Path(nombre)] = crudo.format(origen)

    temporal = DESTINO.with_name(DESTINO.name + ".nuevo")
    shutil.rmtree(temporal, ignore_errors=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as hilos:
        contenidos = dict(zip(encargos, hilos.map(_bajar, encargos.values())))
    for relativo, datos in contenidos.items():
        (temporal / relativo).parent.mkdir(parents=True, exist_ok=True)
        (temporal / relativo).write_bytes(datos)

    pruebas = sum(1 for p in encargos if p.suffix == ".xml")
    (temporal / "PROCEDENCIA.md").write_text(
        "# De dónde sale esta carpeta\n\n"
        f"Copia sin tocar de <https://github.com/{REPO}>, commit `{commit}`.\n"
        "No la ha escrito este proyecto y no se edita a mano: se rehace con\n"
        "`python -m herramientas.norma_oficial <commit>`.\n\n"
        f"- {pruebas} ficheros de pruebas unitarias: "
        + ", ".join(f"`{c}`" for c in CARPETAS) + ".\n"
        "- `EN16931-model.sch` y `EN16931-UBL-codes.sch`, de `ubl/schematron/`.\n"
        "- `LICENSE.txt`: European Union Public Licence 1.2, la licencia de\n"
        "  todo lo anterior.\n\n"
        f"Huella del contenido (SHA-256, finales de línea normalizados):\n`{huella(temporal)}`\n",
        encoding="utf-8",
    )

    # Se sustituye solo cuando todo ha llegado: una copia a medias no pisa a
    # la buena.
    shutil.rmtree(DESTINO, ignore_errors=True)
    temporal.rename(DESTINO)
    print(f"{DESTINO.relative_to(RAIZ)}: {len(encargos)} ficheros, huella {huella(DESTINO)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("uso: python -m herramientas.norma_oficial <commit>")
    main(sys.argv[1])
