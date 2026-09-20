# -*- coding: utf-8 -*-
"""El tercer gancho: el que se niega a escribir donde no se debe.

Vive **fuera del repositorio**, en `<carpeta de trabajo>/.claude/hooks/`, y a
propósito: también protege `Proyecto 1/`, que no es asunto de este proyecto.
Por eso aquí solo se prueba cuando está —en esta máquina—, y en GitHub estas
pruebas se saltan. Es lo mismo que pasa con `core.hooksPath`: el guion viaja,
el cableado no.

Lo que cerró esto, de la auditoría del 15-09-2026 (punto 12):

- `Sitio`, `ANCLAS` y `proyecto 1` pasaban los tres. Windows no distingue
  mayúsculas —medido: `ls SITIO/` lista lo mismo que `ls sitio/`—, así que
  escribir en «Sitio/index.html» escribía en `sitio/index.html` con el
  guardián puesto y diciendo que sí.
- `NotebookEdit` pasaba **siempre**: el gancho leía `file_path` y esa
  herramienta manda la ruta en `notebook_path`.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TRABAJO = RAIZ.parent
GUARDIAN = TRABAJO / ".claude" / "hooks" / "guardian-de-rutas.py"

sin_guardian = pytest.mark.skipif(
    not GUARDIAN.is_file(),
    reason=f"el guardián de rutas no está en esta copia ({GUARDIAN})",
)


def _cargar():
    especificacion = importlib.util.spec_from_file_location("guardian", GUARDIAN)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def guardian():
    return _cargar()


def decide(entrada: dict) -> int:
    """El código de salida, provocándolo como lo llama Claude Code.

    Por subproceso y no llamando a `main()`: lo que decide si un gancho para es
    su código de salida, y eso solo se ve corriéndolo.
    """
    hecho = subprocess.run(
        [sys.executable, str(GUARDIAN)],
        input=json.dumps(entrada), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60,
    )
    return hecho.returncode


def _para(camino: str, clave: str = "file_path") -> bool:
    return decide({"tool_input": {clave: camino}, "cwd": str(RAIZ)}) == 2


@sin_guardian
class TestLasMayusculasNoSonUnPermiso:
    """En Windows, `Sitio/` y `sitio/` son la misma carpeta."""

    @pytest.mark.parametrize("camino", [
        "sitio/index.html",
        "Sitio/index.html",
        "SITIO/index.html",
        "anclas/x.pem",
        "ANCLAS/x.pem",
        "Anclas-Sellos/x.pem",
        "Vendor/pyodide/pyodide.js",
        "MUESTRAS/factura.xml",
    ])
    def test_se_para_escriba_como_se_escriba(self, camino):
        assert _para(str(RAIZ / camino)), (
            f"«{camino}» ha pasado. En Windows es la misma carpeta que la "
            "prohibida, así que el guardián estaría mirando el nombre y no el "
            "sitio"
        )

    def test_el_proyecto_del_usuario_tambien(self):
        assert _para(str(TRABAJO / "proyecto 1" / "estrategia.py"))
        assert _para(str(TRABAJO / "Proyecto 1" / "estrategia.py"))


@sin_guardian
class TestTodasLasRutasQueMandaLaHerramienta:
    """`NotebookEdit` manda `notebook_path`, no `file_path`."""

    def test_un_cuaderno_en_lo_prohibido_se_para(self):
        assert _para(str(RAIZ / "muestras" / "x.ipynb"), clave="notebook_path")

    def test_cualquier_campo_que_acabe_en_path(self, guardian):
        """Se acepta el nombre que sea: lo que no se mira es lo que pasa."""
        assert guardian._rutas_pedidas(
            {"notebook_path": "a", "file_path": "b", "cell_id": "c"}
        ) == ["a", "b"]

    def test_lo_que_no_es_una_ruta_no_estorba(self, guardian):
        assert guardian._rutas_pedidas({"content": "x", "old_string": "y"}) == []
        assert guardian._rutas_pedidas({"file_path": ""}) == []
        assert guardian._rutas_pedidas({"file_path": None}) == []


@sin_guardian
class TestLoQueSiSePuedeEscribir:
    """Un guardián que estorba acaba desactivado, que es no tener ninguno."""

    @pytest.mark.parametrize("camino", [
        "README.md",
        "validador/factura.py",
        "web/paquete.zip",       # la excepción versionada, a propósito
        "web/PAQUETE.json",
        "tests/test_paquete.py",
    ])
    def test_pasa(self, camino):
        assert not _para(str(RAIZ / camino))

    def test_fuera_de_la_carpeta_de_trabajo_no_es_asunto_suyo(self):
        """Otro repositorio de la máquina con un `sitio/` suyo."""
        assert not _para(r"D:\otro-proyecto\sitio\index.html")
