# -*- coding: utf-8 -*-
"""Qué códigos tuvieron ficha alguna vez, leído de la historia de git.

Por qué existe
--------------
`tests/fichas_publicadas.txt` es lo que impide que retirar un código deje su
ficha en un 404: lo que está ahí y ya no en el catálogo tiene que llevar su
dirección a otra ficha en `vercel.json`. Pero la lista se escribió el
11-10-2026 con el glosario de ese día, y lo que se había retirado antes no
estaba: `COPIA-CUOTA` (del 20-09 al 07-10) dio 404 en producción hasta el
25-10, con la prueba en verde. Y los nombres sin cero de septiembre
(`BR-S-8` y los demás, del 11 al 13-09) tampoco estaban, aunque ya tenían su
redirección por otro camino.

Esto recorre cada commit desde el primero con fichas y junta todos los
códigos que tuvo el catálogo. Lo que salga aquí y no esté en la lista es una
ficha que existió y que nada vigila.

Cómo se lee un commit viejo
---------------------------
Con el `codigos.py` de hoy, que es el único que resuelve los códigos
compuestos del IVA, y solo importando desde la carpeta del commit: se saca
`validador/` con `git archive`, se le pone el lector de hoy y se lee en un
proceso aparte con esa carpeta como raíz. Los commits de antes del 23-09 no
tienen lo que el lector de hoy importa (`incidencias.familia_de`); esos se
leen con su propio `codigos.py`, que es el que montaba sus fichas.

El recorrido entero lleva unos diez minutos (170 commits el 25-10-2026), y
en GitHub la copia viene sin historia, así que no va en la suite. La suite
vigila lo barato (ver `tests/test_pagina_incidencias.py`, las direcciones
viejas), y esto se corre a mano cuando se quiera mirar la historia entera:

    ./.venv/Scripts/python.exe -m herramientas.fichas_que_existieron
    ./.venv/Scripts/python.exe -m herramientas.fichas_que_existieron --produccion

Sale con 1 si hay alguna ficha que existió y no está en la lista. Con
`--produccion` pregunta además por cada retirado a glosa-e.com, siguiendo la
redirección, y sale con 1 si alguno no acaba en 200.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
LISTA = RAIZ / "tests" / "fichas_publicadas.txt"
# El primer commit con una página por código (`montar_fichas`), del 11-09-2026.
PRIMERO = "ecfb38e"
DOMINIO = "https://www.glosa-e.com"

_LEER = ("import sys; sys.path.insert(0, '.'); "
         "from validador.codigos import codigos_del_paquete as c; "
         "print(' '.join(sorted(x.codigo for x in c(None))))")


def _git(*argumentos: str, texto: bool = True):
    return subprocess.run(["git", *argumentos], cwd=RAIZ, capture_output=True,
                          text=texto, check=True).stdout


def _leer_en(carpeta: Path) -> set[str] | None:
    salida = subprocess.run([sys.executable, "-I", "-c", _LEER], cwd=carpeta,
                            capture_output=True, text=True, encoding="utf-8")
    if salida.returncode or not salida.stdout.strip():
        return None
    return set(salida.stdout.split())


def codigos_de(commit: str) -> set[str]:
    """Los códigos del catálogo en un commit. Se niega si no hay forma de leerlo:
    un commit que se salta en silencio es justo el hueco que esto busca."""
    crudo = _git("archive", commit, "validador", texto=False)
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        tarfile.open(fileobj=io.BytesIO(crudo)).extractall(carpeta, filter="data")
        lector = carpeta / "validador" / "codigos.py"
        propio = lector.read_bytes() if lector.is_file() else None
        lector.write_bytes((RAIZ / "validador" / "codigos.py").read_bytes())
        codigos = _leer_en(carpeta)
        if codigos is None and propio is not None:
            lector.write_bytes(propio)
            codigos = _leer_en(carpeta)
    if codigos is None:
        raise RuntimeError(f"el catálogo de {commit} no se puede leer, ni con el "
                           "lector de hoy ni con el suyo")
    return codigos


def commits(desde: str = PRIMERO, hasta: str = "HEAD") -> list[str]:
    return _git("rev-list", "--reverse", f"{desde}^..{hasta}").split()


def historia(lista_de_commits: list[str]) -> dict[str, str]:
    """Cada código que salió, con el primer commit en que salió."""
    vistos: dict[str, str] = {}
    for commit in lista_de_commits:
        for codigo in codigos_de(commit):
            vistos.setdefault(codigo, commit[:7])
    return vistos


def apuntados() -> set[str]:
    lineas = LISTA.read_text(encoding="utf-8").splitlines()
    return {l.strip() for l in lineas if l.strip() and not l.startswith("#")}


def _estado(ruta: str) -> int | str:
    # Con reintentos: el 25-10-2026 producción cortó una conexión a mitad de
    # un recorrido de sesenta peticiones seguidas.
    for _ in range(4):
        try:
            return urllib.request.urlopen(
                urllib.request.Request(DOMINIO + ruta, method="HEAD"), timeout=20).status
        except urllib.error.HTTPError as error:
            return error.code
        except urllib.error.URLError:
            time.sleep(3)
    return "sin respuesta"


def main(argv: list[str]) -> int:
    vistos = historia(commits())
    hoy = codigos_de("HEAD")
    sin_apuntar = sorted(set(vistos) - apuntados())
    retirados = sorted(set(vistos) - hoy)
    print(f"{len(vistos)} códigos con ficha alguna vez, {len(hoy)} hoy, "
          f"{len(retirados)} retirados")
    for codigo in sin_apuntar:
        print(f"  sin apuntar en {LISTA.name}: {codigo} (desde {vistos[codigo]})")
    malos = []
    if "--produccion" in argv:
        redirigen = {r["source"] for r in json.loads(
            (RAIZ / "vercel.json").read_text(encoding="utf-8"))["redirects"]}
        for codigo in retirados:
            ruta = f"/codigo-{codigo}"
            estado = _estado(ruta)
            if estado != 200 or ruta not in redirigen:
                malos.append(codigo)
                print(f"  {codigo}: {'redirige' if ruta in redirigen else 'sin redirección'}"
                      f", producción {estado}")
        print(f"{len(retirados) - len(malos)} de {len(retirados)} retirados acaban en 200")
    return 1 if sin_apuntar or malos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
