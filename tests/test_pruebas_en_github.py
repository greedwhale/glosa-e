# -*- coding: utf-8 -*-
"""Que lo que corre en GitHub sea la suite entera, y con lo mismo que aquí.

Por qué existe
--------------
`.github/workflows/pruebas.yml` corre la suite en GitHub en cada push y en cada
pull request, y es la comprobación que la protección de `main` puede exigir
antes de fusionar. Sale verde o rojo, y un verde solo vale si lo que corrió es
lo que se cree:

- **con las mismas versiones**: si allí se instalara otra lxml u otro Python,
  el verde de allí no diría nada de lo probado aquí;
- **la suite entera, siempre**: un filtro de ramas o de rutas, un `-k`, un
  `continue-on-error` o un `if:` dejan el verde y quitan la prueba;
- **con el mismo nombre**: la protección exige la comprobación por su nombre,
  y si el nombre cambia la sigue esperando para siempre;
- **con las acciones fijadas**: una etiqueta como `v7` se mueve sola.

Es el disfraz de siempre en este repositorio —sale todo verde y no es lo que
crees que has probado—, así que se vigila en vez de recordarlo.

Lo que no puede vigilar: que GitHub exija de verdad esta comprobación. Eso es
configuración de GitHub y no vive en el repositorio. Desde el 21-10-2026, con
el repositorio público, la protección de `main` la exige; hasta entonces, en
privado y con el plan gratuito, GitHub no la ofrecía (medido el 16-09-2026: la
API contestaba 403).
"""
from __future__ import annotations

import platform
import re
from importlib import metadata
from pathlib import Path

from packaging.requirements import Requirement

RAIZ = Path(__file__).resolve().parent.parent
FLUJO = RAIZ / ".github" / "workflows" / "pruebas.yml"
REQUISITOS = RAIZ / "requisitos-pruebas.txt"

# Lo único que se le puede pasar a pytest en GitHub. Una lista de lo permitido
# y no de lo prohibido: `-k`, `-m`, `--deselect`, `--ignore`, `--lf`, una ruta
# suelta... la lista de maneras de correr menos que la suite no se acaba.
OPCIONES_ADMITIDAS = ("-q", "--no-header", "-p", "no:cacheprovider", "-rs")


def _sin_comentarios(texto: str) -> list[str]:
    """Las líneas con contenido, sin comentarios enteros ni finales."""
    lineas = []
    for linea in texto.splitlines():
        linea = re.sub(r"\s+#.*$", "", linea).rstrip()
        if linea and not linea.lstrip().startswith("#"):
            lineas.append(linea)
    return lineas


def _flujo() -> list[str]:
    return _sin_comentarios(FLUJO.read_text(encoding="utf-8"))


def _requisitos() -> list[Requirement]:
    return [
        Requirement(linea)
        for linea in _sin_comentarios(REQUISITOS.read_text(encoding="utf-8"))
    ]


def test_lo_instalado_es_lo_fijado():
    """Aquí y en GitHub, las mismas versiones de todo lo que corre la suite."""
    requisitos = _requisitos()
    nombres = {r.name.lower() for r in requisitos}
    assert {"lxml", "pytest"} <= nombres, (
        "requisitos-pruebas.txt no fija lxml y pytest. Un fichero vacío pasaría "
        "esta comprobación sin comprobar nada."
    )
    distintas = []
    for requisito in requisitos:
        fijadas = [s.version for s in requisito.specifier if s.operator == "=="]
        assert len(fijadas) == 1 and len(requisito.specifier) == 1, (
            f"{requisito}: cada dependencia va con `==` y una sola versión. "
            "Un intervalo deja que GitHub instale la última que salga."
        )
        if requisito.marker is not None and not requisito.marker.evaluate():
            continue
        try:
            instalada = metadata.version(requisito.name)
        except metadata.PackageNotFoundError:
            instalada = "ninguna"
        if instalada != fijadas[0]:
            distintas.append(
                f"{requisito.name}: fijada {fijadas[0]}, instalada {instalada}"
            )
    assert not distintas, (
        "Lo instalado aquí no es lo que instala GitHub, así que su verde no "
        "habla de estas pruebas. O se vuelve a lo fijado, o se cambia "
        "requisitos-pruebas.txt:\n  " + "\n  ".join(distintas)
    )


def test_el_python_es_el_de_github():
    versiones = [
        m.group(1)
        for linea in _flujo()
        if (m := re.match(r'\s*python-version:\s*"([^"]+)"$', linea))
    ]
    assert len(versiones) == 1, (
        f"el flujo fija {len(versiones)} versiones de Python y tiene que fijar "
        "una, entre comillas: sin comillas, YAML lee 3.10 como 3.1."
    )
    assert platform.python_version() == versiones[0], (
        f"aquí corre Python {platform.python_version()} y GitHub instala "
        f"{versiones[0]}. Un verde allí no dice nada de lo que pasa aquí."
    )


def test_corre_en_cada_push_y_cada_pull_request_sin_filtros():
    """El bloque `on:` exacto: con un filtro, la protección esperaría para siempre.

    Si la protección de `main` exige esta comprobación y un filtro de ramas o
    de rutas la deja sin correr en un pull request, GitHub la da por pendiente
    y no deja fusionar nunca. Y un filtro de rutas que se deje fuera un
    directorio deja pasar sin probar justo el cambio que la rompe.
    """
    lineas = _flujo()
    inicio = lineas.index("on:")
    bloque = ["on:"]
    for linea in lineas[inicio + 1:]:
        if not linea.startswith(" "):
            break
        bloque.append(linea)
    assert bloque == ["on:", "  push:", "  pull_request:"], (
        "el flujo tiene que dispararse en todo push y todo pull request, sin "
        "filtros. Tiene:\n  " + "\n  ".join(bloque)
    )


def test_un_solo_trabajo_y_se_llama_suite():
    """La protección exige la comprobación por su nombre: `suite`.

    Uno solo, además, para que exigir ese nombre sea exigir todo lo que corre.
    """
    lineas = _flujo()
    inicio = lineas.index("jobs:")
    trabajos = [
        l.strip().rstrip(":") for l in lineas[inicio + 1:]
        if re.match(r"  [^ ].*:$", l)
    ]
    nombres = [
        l.split(":", 1)[1].strip() for l in lineas[inicio + 1:]
        if re.match(r"    name:", l)
    ]
    assert trabajos == ["suite"] and nombres == ["suite"], (
        f"trabajos {trabajos}, nombres {nombres}. La protección de `main` "
        "espera una comprobación llamada `suite`: si se cambia aquí, hay que "
        "cambiarla también en la regla de GitHub, o no se fusiona nada."
    )


def test_la_suite_corre_entera_y_su_fallo_cuenta():
    texto = "\n".join(_flujo())
    for trampa in ("continue-on-error", "if:", "|| true", "|| exit 0"):
        assert trampa not in texto, (
            f"`{trampa}` en el flujo: con eso, un paso que falla puede dejar "
            "la comprobación en verde o no llegar a correr."
        )
    ordenes = [l for l in _flujo() if "pytest" in l and "pip" not in l]
    assert len(ordenes) == 1, f"se esperaba una orden de pytest y hay {ordenes}"
    detras = ordenes[0].split("pytest", 1)[1].split()
    sobran = [o for o in detras if o not in OPCIONES_ADMITIDAS]
    assert not sobran, (
        f"pytest corre en GitHub con {sobran}. Cualquier cosa fuera de "
        f"{OPCIONES_ADMITIDAS} puede estar corriendo menos que la suite."
    )


def test_las_acciones_van_fijadas_por_commit():
    usadas = [
        m.group(1) for l in _flujo() if (m := re.search(r"uses:\s*(\S+)", l))
    ]
    assert usadas, "el flujo no usa ninguna acción: no puede sacar el código"
    sueltas = [u for u in usadas if not re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", u)]
    assert not sueltas, (
        f"{sueltas}: van por etiqueta o rama, y eso se mueve sin tocar este "
        "repositorio. Se fijan por el commit de 40 cifras."
    )
