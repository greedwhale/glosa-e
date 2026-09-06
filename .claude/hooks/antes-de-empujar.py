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


# Un `git push` en cualquier punto de la orden. Se usa dos veces: sobre la
# orden bien leida, y sobre el texto crudo cuando la entrada no se deja leer.
ES_PUSH = re.compile(r"\bgit\s+(?:-\S+\s+)*push\b")


def main() -> int:
    crudo = ""
    try:
        crudo = sys.stdin.read()
        entrada = json.loads(crudo)
    except Exception:
        # Aqui no se sabe que orden es, y esa es justamente la situacion
        # peligrosa: devolver 0 a ciegas convierte el gancho en un adorno el
        # dia que Claude Code cambie la forma de la entrada. Asi que se mira
        # el texto tal cual llego. Si ni siquiera se parece a un push, se deja
        # pasar —bloquear cada orden de la sesion por no saber leer un JSON
        # seria peor—; si se parece, se para y se dice por que.
        if ES_PUSH.search(crudo or ""):
            print(
                "El gancho no ha podido leer su entrada, asi que no puede "
                "correr los tests, y esta orden parece un `git push` a "
                "produccion. Se para: un gancho que falla abriendo publica "
                "igual y ademas tranquiliza.",
                file=sys.stderr,
            )
            return 2
        return 0

    # Y la red de debajo de todo, por lo que no se ha previsto. Solo se
    # bloquea si la orden es un push: de las demas este gancho no guarda nada
    # y pararlas seria estorbar por un fallo suyo.
    try:
        return _guardar(entrada)
    except Exception as error:
        if ES_PUSH.search((entrada.get("tool_input") or {}).get("command", "")):
            print(
                f"El gancho se ha roto ({type(error).__name__}: {error}) y no "
                "ha llegado a comprobar nada. Esta orden publica en "
                "produccion, asi que no sale.",
                file=sys.stderr,
            )
            return 2
        return 0


def _guardar(entrada: dict) -> int:
    orden = (entrada.get("tool_input") or {}).get("command", "")
    # Un `git push` en cualquier punto de la orden, no solo al principio:
    # aqui llegan cosas como `cd /ruta/al/repo && git push`. El precio de
    # buscar la subcadena es que tambien disparan `git push --help` y hasta un
    # `echo "git push"`, que no publican nada y se comen igual la suite (36 s
    # medidos el 2026-08-30). Se deja asi a proposito: es el mismo sesgo que en
    # `hay_que_mirar()` —equivocarse hacia parar cuesta esos segundos, y
    # equivocarse hacia dejar pasar publica algo roto sin enterarse—. Lo unico
    # que la `\b` final descarta es lo que solo se le parece: `git pushear`.
    if not ES_PUSH.search(orden):
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

    # Todo lo que puede salir mal aqui sale con codigo 2, no con el 1 que deja
    # una excepcion sin recoger. **Esa era la puerta de atras**: Claude Code
    # solo bloquea con 2, asi que un `TimeoutExpired` o un `OSError` —el disco
    # lleno, el ejecutable que se va a medio arrancar— imprimian una traza,
    # salian con 1 y el push se publicaba igual. Un gancho que falla abriendo
    # es peor que no tenerlo, porque ademas tranquiliza.
    try:
        hecho = subprocess.run(
            [str(PYTHON), "-m", "pytest", "-q", "--no-header", "-x"],
            cwd=str(REPO), capture_output=True, text=True, timeout=600,
        )
    except subprocess.TimeoutExpired:
        print(
            "La suite no ha terminado en diez minutos y tarda medio. Algo se "
            "ha quedado colgado, y este push publica en produccion: no se "
            "sabe si pasa o no pasa, asi que no sale.",
            file=sys.stderr,
        )
        return 2
    except OSError as error:
        print(
            f"No se ha podido correr la suite: {error}. Este push publica en "
            "produccion y nadie ha comprobado nada.",
            file=sys.stderr,
        )
        return 2

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
