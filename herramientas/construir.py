"""La construcción del sitio en Cloudflare: la misma orden que en Vercel.

    python3 herramientas/construir.py

Es la orden de construcción que se escribe en el panel de Cloudflare
(Workers Builds), y no la orden entera, por una razón: lo que se escribe en un
panel no se versiona, no lo ve ninguna prueba y se queda atrás el día que
cambia `vercel.json`. Así el panel dice siempre lo mismo y lo que se ejecuta
sale de `vercel.json`, que es la única fuente (ver `validador/alojamiento.py`).
Si las dos construcciones corrieran órdenes distintas, los dos alojamientos
servirían sitios distintos con el mismo commit, y nada se pondría rojo.

**Y se niega si el Python no es el de la suite.** Cloudflare lo elige con la
variable `PYTHON_VERSION` del panel, y sin ella usa el suyo por defecto (3.14.8
el 15-11-2026, y lo sube solo). Un sitio montado con otro Python que el que
pasó la suite es lo de siempre: sale todo verde y no es lo que se probó. La
versión buena es la de `.github/workflows/pruebas.yml`, que es con la que corre
`suite` en GitHub.
"""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FLUJO = RAIZ / ".github" / "workflows" / "pruebas.yml"
CONFIGURACION = RAIZ / "vercel.json"

_RE_PYTHON_DEL_FLUJO = re.compile(r'^\s*python-version:\s*"([^"]+)"\s*$', re.M)


def python_de_la_suite(flujo: Path = FLUJO) -> str:
    encontradas = _RE_PYTHON_DEL_FLUJO.findall(flujo.read_text(encoding="utf-8"))
    if len(encontradas) != 1:
        raise ValueError(
            f"«{flujo}» debería fijar un solo `python-version` y fija "
            f"{len(encontradas)}: no se sabe con qué Python se probó."
        )
    return encontradas[0]


def orden_de_construccion(configuracion: Path = CONFIGURACION) -> str:
    return json.loads(configuracion.read_text(encoding="utf-8"))["buildCommand"]


def main() -> int:
    esperado, actual = python_de_la_suite(), platform.python_version()
    if actual != esperado:
        print(
            f"Este Python es {actual} y la suite pasó con {esperado} (ver "
            f"`{FLUJO.relative_to(RAIZ).as_posix()}`). No se monta: el sitio "
            "saldría de una combinación que nadie ha probado. En Cloudflare, "
            f"pon la variable de construcción PYTHON_VERSION={esperado}.",
            file=sys.stderr,
        )
        return 2
    orden = orden_de_construccion()
    print(f"Python {actual}, el de la suite. Orden de `vercel.json`:\n  {orden}",
          flush=True)
    return subprocess.run(orden, shell=True, cwd=RAIZ).returncode


if __name__ == "__main__":
    sys.exit(main())
