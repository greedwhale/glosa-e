# -*- coding: utf-8 -*-
"""Que ninguna orden de Claude Code se salte la puerta de producción.

La puerta ya no está aquí
-------------------------
Hasta el 16-09-2026 este gancho corría la suite él mismo, y para saber cuándo
leía la orden escrita con una expresión regular. La auditoría del 15-09-2026
le encontró nueve maneras de pasar: `git -C . push`, `git -c x=y push`,
`git.exe push`, la ruta entera de git, un `--dry-run` en cualquier parte —hasta
en un comentario—, solo el primer `cd` de la orden, y las pruebas corridas
sobre la carpeta y no sobre lo empujado. Y la de fondo: **un push desde la
consola de siempre no pasaba por aquí**.

Ahora la suite la corre git, en `.githooks/pre-push`, en todo push de esta
copia. Leer bien la orden deja de ser lo que separa publicar probado de
publicar sin probar: un alias, un guion o una ruta rara llegan igual al gancho
de git.

Lo que queda aquí
-----------------
Lo único que git no puede guardarse solo: que no se lo salten. Para una orden
que toca Factura-e, sale con **2** —lo único que bloquea en Claude Code— si:

1. es un push y el gancho de git **no está puesto** (`core.hooksPath`); sin él
   el push publica sin probar, y no falla ni avisa;
2. es un push con `--no-verify`, que le dice a git que no llame al gancho;
3. es un `git send-pack`, que empuja por debajo de `push` y no lo llama;
4. toca `core.hooksPath` de cualquier manera —`-c`, `--config-env`,
   `GIT_CONFIG_PARAMETERS`, `git config`— salvo para ponerlo en `.githooks`;
5. no se deja leer y parece uno de los anteriores.

Con los demás proyectos de la carpeta de trabajo no se mete: tienen sus reglas.
"""
from __future__ import annotations

import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[2]
GANCHOS = ".githooks"

# Lo que puede ir delante del ejecutable sin ser él: `& "C:\...\git.exe"` en
# PowerShell, `env`, `command`...
_DELANTE = {"&", "env", "command", "exec", "time", "nice", "nohup", "call", "sudo"}
# Las opciones de git que llevan su valor en la palabra siguiente. Las demás
# opciones van solas o con `=`.
_CON_VALOR = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
              "--config-env", "--exec-path", "--super-prefix"}
_CAMBIAN_DE_CARPETA = {"cd", "set-location", "sl", "chdir", "pushd", "push-location"}
_SEPARADORES = {"&&", "||", ";", "|", "&"}

# Lo que se busca cuando la orden no se deja leer.
_PARECE_GIT = re.compile(r"git(?:\.exe)?\b", re.I)
_PARECE_PELIGRO = re.compile(r"\bpush\b|send-pack|hookspath", re.I)


class Ilegible(Exception):
    """La orden no se ha podido partir en palabras."""


def normalizar(camino: str) -> Path:
    """Una ruta de verdad, venga de Bash (`/c/Users/...`) o de PowerShell.

    `Path("/c/Users/...")` en Windows **no** resuelve a `C:\\Users\\...` sino a
    `C:\\c\\Users\\...`. Costó un fallo silencioso: el gancho creía que el push
    venía de otro proyecto y dejaba pasar sin mirar nada.
    """
    camino = camino.strip().strip('"').strip("'").replace("\\", "/")
    trozos = camino.split("/")
    if len(trozos) > 2 and trozos[1] == "cygdrive" and len(trozos[2]) == 1:
        camino = trozos[2] + ":/" + "/".join(trozos[3:])
    elif len(trozos) > 1 and len(trozos[1]) == 1 and trozos[1].isalpha():
        camino = trozos[1] + ":/" + "/".join(trozos[2:])
    return Path(camino)


def _palabras(orden: str) -> list[str]:
    """La orden partida en palabras y separadores, sin comentarios.

    `posix=False` porque llegan rutas de Windows: en modo POSIX la barra
    invertida escapa y `C:\\Users` sale `C:Users`. Los saltos de línea separan
    órdenes igual que `;`.
    """
    lector = shlex.shlex(orden.replace("\r", "").replace("\n", " ; "),
                         posix=False, punctuation_chars="&|;")
    lector.whitespace_split = True
    try:
        return list(lector)
    except ValueError as error:
        raise Ilegible(str(error)) from error


def _sin_comillas(palabra: str) -> str:
    if len(palabra) >= 2 and palabra[0] == palabra[-1] and palabra[0] in "\"'":
        return palabra[1:-1]
    return palabra


def _es_git(palabra: str) -> bool:
    nombre = _sin_comillas(palabra).replace("\\", "/").rsplit("/", 1)[-1].lower()
    return nombre in ("git", "git.exe")


def invocaciones(orden: str, desde: Path) -> list[tuple[Path, str, list[str]]]:
    """Cada llamada a git de la orden: `(carpeta, subórden, palabras)`.

    La carpeta sale de **todos** los `cd` —y `Set-Location`, `pushd`— que van
    delante, en orden, y de los `-C` de la propia llamada. Antes solo se miraba
    el primer `cd`, y `cd ../Proyecto 1 && cd ../Factura-e && git push` parecía
    un push de otro proyecto.
    """
    salida = []
    carpeta = desde
    orden_actual: list[str] = []
    for palabra in _palabras(orden) + [";"]:
        if palabra not in _SEPARADORES:
            orden_actual.append(palabra)
            continue
        if orden_actual:
            primera = _sin_comillas(orden_actual[0]).lower()
            if primera in _CAMBIAN_DE_CARPETA and len(orden_actual) > 1:
                destino = normalizar(_sin_comillas(orden_actual[-1]))
                carpeta = destino if destino.is_absolute() else carpeta / destino
            else:
                encontrada = _llamada_a_git(orden_actual, carpeta)
                if encontrada:
                    salida.append(encontrada)
        orden_actual = []
    return salida


def _llamada_a_git(palabras: list[str], carpeta: Path):
    i = 0
    while i < len(palabras) and (
        _sin_comillas(palabras[i]).lower() in _DELANTE
        or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*=.*", palabras[i])
    ):
        i += 1
    if i >= len(palabras) or not _es_git(palabras[i]):
        return None
    i += 1
    while i < len(palabras) and palabras[i].startswith("-"):
        opcion = palabras[i]
        if opcion in _CON_VALOR and i + 1 < len(palabras):
            if opcion == "-C":
                destino = normalizar(_sin_comillas(palabras[i + 1]))
                carpeta = destino if destino.is_absolute() else carpeta / destino
            i += 2
        else:
            i += 1
    subordenes = _sin_comillas(palabras[i]).lower() if i < len(palabras) else ""
    return carpeta, subordenes, palabras


def de_factura_e(carpeta: Path) -> bool:
    """Si no se sabe de dónde sale, se da por Factura-e: el sesgo es parar."""
    try:
        carpeta = carpeta.resolve()
    except OSError:
        return True
    if carpeta == REPO or REPO in carpeta.parents:
        return True
    trabajo = REPO.parent
    if trabajo in carpeta.parents:
        # Otro proyecto de la carpeta de trabajo: tiene sus propias reglas.
        return False
    return True


def ganchos_puestos() -> bool:
    hecho = subprocess.run(
        ["git", "-C", str(REPO), "config", "--get", "core.hooksPath"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return hecho.returncode == 0 and hecho.stdout.strip().replace("\\", "/") in (
        GANCHOS, f"./{GANCHOS}", (REPO / GANCHOS).as_posix(),
    )


def _pone_o_lee_los_ganchos(subordenes: str, palabras: list[str]) -> bool:
    """`git config core.hooksPath .githooks`, o leerlo con `--get`. Nada más."""
    resto = [_sin_comillas(p) for p in palabras]
    if subordenes != "config":
        return False
    tras = resto[[p.lower() for p in resto].index("config") + 1:]
    if [p.lower() for p in tras] == ["--get", "core.hookspath"]:
        return True
    return [p.lower() for p in tras[:1]] == ["core.hookspath"] and tras[1:] == [GANCHOS]


def decidir(orden: str, desde: Path) -> str | None:
    """El motivo para parar, o `None` si la orden puede seguir."""
    try:
        llamadas = invocaciones(orden, desde)
    except Ilegible:
        if _PARECE_GIT.search(orden) and _PARECE_PELIGRO.search(orden):
            return (
                "Esta orden no se deja leer —comillas sin cerrar— y parece un push "
                "o que toca los ganchos de git. Sin poder leerla no se sabe si se "
                "salta la puerta de producción, así que no sale."
            )
        return None

    nuestras = [(c, s, p) for c, s, p in llamadas if de_factura_e(c)]
    # `core.hooksPath` nombrado fuera de toda llamada a git —una variable puesta
    # en otra orden de la misma línea, `$env:GIT_CONFIG_PARAMETERS=...; git
    # push`— no se deja leer como llamada, y pisa el gancho igual.
    fuera = "hookspath" in orden.lower() and not any(
        "hookspath" in " ".join(p).lower() for _, _, p in llamadas
    )
    if fuera and any(s == "push" for _, s, _ in nuestras):
        return (
            "Esta orden nombra `core.hooksPath` y empuja Factura-e. De ahí cuelga "
            "que git corra las pruebas antes de publicar, y pisarlo desde una "
            "variable deja pasar el push sin probar."
        )

    for carpeta, subordenes, palabras in nuestras:
        minusculas = [_sin_comillas(p).lower() for p in palabras]
        if subordenes == "config" and any("--no-verify" in p for p in minusculas):
            # Un alias con `--no-verify` dentro es un `git push --no-verify`
            # que ya no se ve al escribirlo.
            return (
                "Esta orden mete `--no-verify` en la configuración de git de "
                "Factura-e —un alias, casi seguro—, y con eso un push se salta "
                "las pruebas sin que se vea al escribirlo."
            )
        if any("hookspath" in p for p in minusculas) and not _pone_o_lee_los_ganchos(
            subordenes, palabras
        ):
            return (
                "Esta orden toca `core.hooksPath` de Factura-e. De ahí cuelga que "
                "git corra las pruebas antes de publicar: cambiarlo, quitarlo o "
                "pisarlo con `-c` deja pasar un push sin probar. Lo único que se "
                "deja es ponerlo: `git config core.hooksPath .githooks`."
            )
        if subordenes == "send-pack":
            return (
                "`git send-pack` empuja por debajo de `git push` y no llama al "
                "gancho de git: publicaría sin probar nada. Usa `git push`."
            )
        if subordenes != "push":
            continue
        if "--no-verify" in minusculas:
            return (
                "`--no-verify` le dice a git que no llame al gancho que corre las "
                "pruebas, y este push publica en producción. Si de verdad hay que "
                "publicar así, que lo haga una persona desde su consola."
            )
        if not ganchos_puestos():
            return (
                "El gancho de git que corre las pruebas antes de publicar no está "
                "puesto en esta copia, y sin él el push publica sin probar nada, "
                "sin fallar ni avisar. Ponlo una vez:\n\n"
                "    git config core.hooksPath .githooks"
            )
    return None


def main() -> int:
    crudo = ""
    try:
        crudo = sys.stdin.read()
        entrada = json.loads(crudo)
        orden = (entrada.get("tool_input") or {}).get("command", "")
        desde = normalizar(entrada.get("cwd") or ".")
    except Exception:
        # No se sabe qué orden es, y esa es justo la situación peligrosa:
        # devolver 0 a ciegas convierte el gancho en un adorno el día que
        # Claude Code cambie la forma de la entrada.
        if _PARECE_GIT.search(crudo or "") and _PARECE_PELIGRO.search(crudo or ""):
            print(
                "El gancho no ha podido leer su entrada, y la orden parece un push "
                "a producción. Se para: un gancho que falla abriendo publica igual "
                "y además tranquiliza.",
                file=sys.stderr,
            )
            return 2
        return 0

    try:
        motivo = decidir(orden, desde)
    except Exception as error:  # noqa: BLE001 - la red de debajo de todo
        if _PARECE_GIT.search(orden) and _PARECE_PELIGRO.search(orden):
            print(
                f"El gancho se ha roto ({type(error).__name__}: {error}) y no ha "
                "llegado a comprobar nada. Esta orden parece publicar en "
                "producción, así que no sale.",
                file=sys.stderr,
            )
            return 2
        return 0
    if motivo:
        print(motivo, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
