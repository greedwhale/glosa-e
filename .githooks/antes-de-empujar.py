# -*- coding: utf-8 -*-
"""Lo que git corre antes de empujar: que lo que sale sea lo probado, y en verde.

Lo llama `.githooks/pre-push`, así que corre en **todo** push de esta copia:
desde Claude Code, desde la consola, con un alias o desde un guion. Git le pasa
por la entrada una línea por referencia que va a empujar, y cualquier código de
salida que no sea 0 cancela el push.

Tres negativas, en este orden
-----------------------------
1. **Solo se empuja HEAD.** Lo que se prueba es la carpeta de trabajo. Empujar
   otra rama u otro commit sería probar una cosa y publicar otra.
2. **Sin cambios a medio hacer.** Con un fichero modificado o uno nuevo sin
   añadir, la carpeta no es el commit: las pruebas pasan con un arreglo que no
   viaja, o fallan por uno que tampoco. Era el cuarto agujero de los nueve que
   encontró la auditoría del 15-09-2026 en el gancho anterior —probaba la
   carpeta, no lo que se empujaba—.
3. **La suite en verde.** Colgada, sin intérprete o sin poder arrancar también
   para: un gancho que no ha podido comprobar nada no puede dejar publicar.

Borrar ramas y empujar etiquetas no publica nada y no se mira. Un `--dry-run`
sí se mira —git llama al gancho igual y no le dice que es un ensayo—: cuesta la
suite, que es el sesgo de siempre aquí, equivocarse hacia parar.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Si la consola no es UTF-8, un `UnicodeEncodeError` mataría el gancho a medio
# explicar por qué para. Para igual —git cancela con cualquier código que no
# sea 0—, pero sin decir por qué.
for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[1]
# El intérprete es **este mismo**: `pre-push` lo busca en la copia principal y
# lo ejecuta, porque un worktree no tiene `.venv` propio. `REPO` sigue siendo
# la copia desde la que se empuja —la suite prueba lo que se publica—, y solo
# el intérprete viene de fuera.
PYTHON = (Path(sys.executable) if sys.executable
          else REPO / ".venv" / "Scripts" / "python.exe")
CEROS = "0" * 40

# Lo que tarda la suite en esta máquina, y cuándo se midió. El 16-09-2026 eran
# 140 s; el 28-10-2026, con 3803 pruebas, 442 s a mano y unos 445 s dentro de
# este mismo gancho. Ese día un push se cortó a los 900 s, que era el límite
# de entonces, y a mano no se volvió a ver: con la máquina ocupada en otra cosa
# la suite pasó del doble. Un límite que se queda a menos del doble de lo
# normal no distingue una suite colgada de una máquina cargada, y el mensaje
# decía que tardaba menos de tres minutos, que ya no era verdad. Por eso el
# límite va atado a la medida (cuatro veces) y el mensaje la cita con su fecha:
# cuando la suite crezca, se vuelve a medir y se cambian las dos cifras aquí.
TARDA = 445
MEDIDO_EL = "28-10-2026"
LIMITE = 4 * TARDA

# Una línea de solo puntos, letras de estado y el porcentaje: progreso, no
# información. `.....F..  [ 42%]` y sus parientes.
PURO_PROGRESO = re.compile(r"[.sxXFEup]+\s*(?:\[\s*\d+%\])?")


def decir(texto: str) -> int:
    print(texto, file=sys.stderr)
    return 1


def git(*argumentos: str) -> str:
    return subprocess.run(
        ["git", *argumentos], cwd=str(REPO), capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=True,
    ).stdout


def lo_que_se_empuja(entrada: str) -> list[tuple[str, str]]:
    """Las ramas que se actualizan: `(sha local, referencia remota)`.

    Fuera las que se borran —sha local a ceros— y lo que no es una rama, que no
    publica nada. Una línea que no tiene las cuatro partes no se sabe qué es, y
    se trata como una rama: parar de más cuesta la suite, dejar pasar publica.
    """
    ramas = []
    for linea in entrada.splitlines():
        partes = linea.split()
        if not partes:
            continue
        if len(partes) != 4:
            ramas.append(("", linea))
            continue
        _, sha_local, remota, _ = partes
        if sha_local == CEROS:
            continue
        if remota.startswith("refs/tags/"):
            continue
        ramas.append((sha_local, remota))
    return ramas


def main() -> int:
    try:
        return _guardar(sys.stdin.read())
    except Exception as error:  # noqa: BLE001 - la red de debajo de todo
        return decir(
            f"El gancho se ha roto ({type(error).__name__}: {error}) y no ha "
            "llegado a comprobar nada. Este push publica en producción, así que "
            "no sale."
        )


def _guardar(entrada: str) -> int:
    ramas = lo_que_se_empuja(entrada)
    if not ramas:
        return 0

    cabeza = git("rev-parse", "HEAD").strip()
    otras = [remota for sha, remota in ramas if sha != cabeza]
    if otras:
        return decir(
            f"Se empuja algo que no es HEAD ({', '.join(otras)}). Lo que se "
            "prueba antes de empujar es la carpeta de trabajo, así que solo se "
            "puede empujar el commit que está puesto: cámbiate a esa rama "
            "primero."
        )

    pendiente = git("status", "--porcelain", "--untracked-files=normal").splitlines()
    if pendiente:
        return decir(
            "Hay cambios sin guardar en un commit, y lo que se probaría no es lo "
            "que se empuja:\n\n  " + "\n  ".join(pendiente[:10])
            + ("\n  ..." if len(pendiente) > 10 else "")
            + "\n\nHaz commit, o apártalos con `git stash -u`, y vuelve a empujar."
        )

    if not PYTHON.is_file():
        return decir(
            f"No está «{PYTHON}», y sin el entorno virtual no hay lxml ni manera "
            "de correr las pruebas. Este push publica en producción: crea el "
            "entorno antes."
        )

    try:
        hecho = subprocess.run(
            [str(PYTHON), "-m", "pytest", "-q", "--no-header", "-x",
             "-p", "no:cacheprovider"],
            cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=LIMITE,
        )
    except subprocess.TimeoutExpired:
        return decir(
            f"La suite no ha terminado en {LIMITE // 60} minutos, y el "
            f"{MEDIDO_EL} tardaba unos {round(TARDA / 60)}. O algo se ha quedado "
            "colgado o la máquina va muy cargada. Este push publica en "
            "producción y no se sabe si pasa, así que no sale. Córrela a mano "
            "con `-v` para ver dónde se para, y vuelve a empujar."
        )
    except OSError as error:
        return decir(
            f"No se ha podido correr la suite: {error}. Este push publica en "
            "producción y nadie ha comprobado nada."
        )

    if hecho.returncode == 0:
        return 0

    # Sin filtrar, las últimas líneas de pytest son los puntitos del progreso y
    # el motivo se queda fuera del recorte.
    lineas = (hecho.stdout or hecho.stderr or "").strip().splitlines()
    utiles = [x for x in lineas if x.strip() and not PURO_PROGRESO.fullmatch(x.strip())]
    return decir(
        "Las pruebas no pasan, y este push publica en producción.\n\n"
        + "\n".join((utiles or lineas)[-20:])
    )


if __name__ == "__main__":
    sys.exit(main())
