# -*- coding: utf-8 -*-
"""Un push a `main` despliega a producción. Que pasen los tests antes.

Este es el hueco real del repositorio: Vercel construye y publica en cada push
a `main`, y hasta ahora nada corría los tests antes. La única puerta era que
`--sitio` se negara ante errores estructurales —falta el intérprete, falta el
wheel, la página cambió de rutas—, que son de los que se ven. Un test rojo, que
es de los que no se ven, se publicaba igual.

No es CI y no lo sustituye: es la puerta que hay mientras no la haya. Corre
solo para Factura-e; los demás proyectos de la carpeta tienen sus propias
reglas y este gancho se aparta de ellos.

Bloquea con código 2 y enseña la cola de pytest, que es donde está el motivo.
"""
import json
import re
import subprocess
import sys

from pathlib import Path

# Lo mismo que en el guardian: si la consola no es UTF-8, un
# `UnicodeEncodeError` mataria el gancho con codigo 1 y el push saldria. Un
# gancho que falla abriendo es peor que no tenerlo, porque ademas tranquiliza.
for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Una linea de solo puntos, letras de estado y el porcentaje: progreso, no
# informacion. `.....F..  [ 42%]` y sus parientes.
PURO_PROGRESO = re.compile(r"[.sxXFEup]+\s*(?:\[\s*\d+%\])?")

REPO = Path(__file__).resolve().parents[2]
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"


def normalizar(camino: str) -> Path:
    """Una ruta de verdad, venga de donde venga.

    Aquí llegan rutas de dos mundos. La consola Bash escribe
    `/c/Users/PC/...` y PowerShell escribe `C:\\Users\\PC\\...`, y
    `Path("/c/Users/...")` en Windows **no** resuelve a `C:\\Users\\...`
    sino a `C:\\c\\Users\\...`, que no existe.

    Esto costó un fallo silencioso: el gancho creía que el push venía de otro
    proyecto y dejaba pasar sin correr nada. Salía código 0 y parecía que
    funcionaba, que es la peor forma de estar roto.
    """
    camino = camino.strip().strip('"').replace("\\", "/")
    trozos = camino.split("/")
    # /cygdrive/c/loquesea  ->  c:/loquesea
    if len(trozos) > 2 and trozos[1] == "cygdrive" and len(trozos[2]) == 1:
        camino = trozos[2] + ":/" + "/".join(trozos[3:])
    # /c/loquesea  ->  c:/loquesea
    elif len(trozos) > 1 and len(trozos[1]) == 1 and trozos[1].isalpha():
        camino = trozos[1] + ":/" + "/".join(trozos[2:])
    return Path(camino)


def donde_corre(entrada: dict) -> Path:
    """La carpeta desde la que se empuja de verdad.

    El `cwd` del gancho es el de la sesión, y aquí las órdenes se escriben como
    `cd /ruta/al/repo && git push`. Si no se mira el `cd`, este gancho creería
    que todos los push salen de la carpeta de trabajo.
    """
    orden = (entrada.get("tool_input") or {}).get("command", "")
    encontrado = re.search(r'cd\s+"?([^"&;|\n]+)"?\s*(?:&&|;)', orden)
    if encontrado:
        return normalizar(encontrado.group(1))
    return normalizar(entrada.get("cwd") or ".")


def hay_que_mirar(carpeta: Path) -> bool:
    """Si no se sabe de dónde sale el push, se miran los tests igual.

    El sesgo va a propósito hacia parar. Este gancho guarda una puerta que
    publica en producción: equivocarse hacia «corro unos tests de más» cuesta
    veinte segundos, y equivocarse hacia «dejo pasar» cuesta publicar algo roto
    sin enterarse. Solo se aparta cuando **reconoce** que el push sale de otro
    proyecto de la carpeta de trabajo.
    """
    try:
        carpeta = carpeta.resolve()
    except OSError:
        return True

    if carpeta == REPO or REPO in carpeta.parents:
        return True

    trabajo = REPO.parent
    if carpeta == trabajo or trabajo in carpeta.parents:
        # Está en la carpeta de trabajo pero fuera de Factura-e: es otro
        # proyecto —`Proyecto 1`, `Investigacion`, `Trabajo remoto`— y tiene
        # sus propias reglas.
        return carpeta == trabajo

    # De fuera de la carpeta de trabajo no se sabe nada. Se mira.
    return True


def main() -> int:
    try:
        entrada = json.load(sys.stdin)
    except Exception:
        return 0

    orden = (entrada.get("tool_input") or {}).get("command", "")
    # Un `git push` en cualquier punto de la orden, no solo al principio:
    # aqui llegan cosas como `cd /ruta/al/repo && git push`. El precio de
    # buscar la subcadena es que tambien disparan `git push --help` y hasta un
    # `echo "git push"`, que no publican nada y se comen igual la suite (36 s
    # medidos el 2026-08-30). Se deja asi a proposito: es el mismo sesgo que en
    # `hay_que_mirar()` —equivocarse hacia parar cuesta esos segundos, y
    # equivocarse hacia dejar pasar publica algo roto sin enterarse—. Lo unico
    # que la `\b` final descarta es lo que solo se le parece: `git pushear`.
    if not re.search(r"\bgit\s+(?:-\S+\s+)*push\b", orden):
        return 0
    # Un ensayo no publica, asi que no hay puerta que guardar.
    if "--dry-run" in orden:
        return 0
    if not hay_que_mirar(donde_corre(entrada)):
        return 0

    if not PYTHON.is_file():
        print(
            f"No está «{PYTHON}», y sin el entorno virtual no hay lxml ni "
            "manera de correr los tests. Este push publica en producción: "
            "crea el entorno antes.",
            file=sys.stderr,
        )
        return 2

    hecho = subprocess.run(
        [str(PYTHON), "-m", "pytest", "-q", "--no-header", "-x"],
        cwd=str(REPO), capture_output=True, text=True, timeout=600,
    )
    if hecho.returncode == 0:
        return 0

    # Sin filtrar, las ultimas lineas de pytest son los puntitos del progreso y
    # el motivo se queda fuera del recorte. Lo que hace falta aqui es lo que
    # fallo, no cuanto se avanzo.
    lineas = (hecho.stdout or hecho.stderr or "").strip().splitlines()
    utiles = [x for x in lineas
              if x.strip() and not PURO_PROGRESO.fullmatch(x.strip())]
    print(
        "Los tests no pasan, y este push publica en producción.\n\n"
        + "\n".join((utiles or lineas)[-20:])
        + "\n\nArréglalo, o di explícitamente que quieres publicar así.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
