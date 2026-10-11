# -*- coding: utf-8 -*-
"""Los agentes de `.claude/agents/` se cargan, y si uno no se carga, se sabe.

Por qué hace falta
------------------
Claude Code salta **en silencio** un agente cuya cabecera YAML no se puede
leer: no lo dice en la sesión, solo lo escribe en el registro de `--debug`.
Medido el 11-10-2026: `revisor-de-promesas` llevaba desde el 26-09 sin cargarse
nunca, porque su `description` tenía un «: » sin comillas, y en YAML eso abre
un mapa dentro de otro. `claude plugin validate .claude/agents` lo contó así:
«YAML frontmatter failed to parse ... At runtime this agent does not load at
all». No salía en la lista de agentes de la sesión, y nadie lo echó de menos.

Es el fallo de siempre: todo verde, y no es lo que crees que tienes.

Las dos comprobaciones
----------------------
- **La de Claude Code**, `claude plugin validate`, es la que manda, pero solo
  corre donde está instalado Claude Code. En GitHub no lo está, y se salta.
- **La de aquí** corre en todas partes y es más estricta que YAML: lo que
  acepta, YAML lo lee; puede rechazar YAML válido, y eso no importa. Pide una
  clave por línea, y entre comillas dobles todo valor que lleve algo que YAML
  pueda leer como otra cosa.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
AGENTES = RAIZ / ".claude" / "agents"

# Los alias que acepta `model` según la documentación de Claude Code
# (code.claude.com/docs/en/sub-agents, leída el 11-10-2026), más los nombres
# completos, que empiezan por «claude-».
MODELOS = {"sonnet", "opus", "haiku", "fable", "inherit"}

# Un valor sin comillas no puede empezar por un indicador de YAML.
INDICADORES = tuple("-?:,[]{}#&*!|>'\"%@`")

# La cabecera tal como estaba el 26-09: es la que Claude Code saltaba.
ROTO = (
    "---\n"
    "name: roto\n"
    "description: Revisa una promesa. Úsalo cuando un cambio toque una de ellas: la política\n"
    "model: opus\n"
    "---\n"
    "\n"
    "Cuerpo.\n"
)
# La misma, con el arreglo: la descripción entre comillas dobles.
BUENO = ROTO.replace(
    "description: Revisa una promesa. Úsalo cuando un cambio toque una de ellas: la política",
    'description: "Revisa una promesa. Úsalo cuando un cambio toque una de ellas: la política"',
)


def _cabecera(texto: str) -> dict[str, str]:
    """Lee la cabecera con las reglas de aquí, o dice por qué no se cargaría."""
    lineas = texto.splitlines()
    if not lineas or lineas[0] != "---":
        raise ValueError("la cabecera no empieza en la primera línea")
    try:
        fin = lineas.index("---", 1)
    except ValueError:
        raise ValueError("la cabecera no se cierra con ---") from None

    campos: dict[str, str] = {}
    for numero, linea in enumerate(lineas[1:fin], start=2):
        clave, separador, valor = linea.partition(": ")
        if not separador or not clave or not clave.replace("_", "").isalpha():
            raise ValueError(f"línea {numero}: no es «clave: valor» en una línea")
        if valor.startswith('"'):
            try:
                valor = json.loads(valor)
            except json.JSONDecodeError:
                raise ValueError(f"línea {numero}: las comillas no cierran bien") from None
        elif (
            valor.startswith(INDICADORES)
            or ": " in valor
            or " #" in valor
            or valor.endswith(":")
        ):
            raise ValueError(f"línea {numero}: «{clave}» necesita comillas dobles")
        if clave in campos:
            raise ValueError(f"línea {numero}: «{clave}» está repetida")
        campos[clave] = valor

    nombre = campos.get("name", "")
    if not nombre:
        raise ValueError("sin name: Claude Code lo toma por documentación")
    if nombre.startswith("-") or ":" in nombre or len(nombre) > 256:
        raise ValueError(f"name no válido: {nombre!r}")
    if not campos.get("description"):
        raise ValueError("sin description: Claude Code lo salta")
    modelo = campos.get("model")
    if modelo is not None and modelo not in MODELOS and not modelo.startswith("claude-"):
        raise ValueError(f"model desconocido: {modelo!r}")
    return campos


def _ficheros() -> list[pathlib.Path]:
    return sorted(AGENTES.rglob("*.md"))


def test_hay_agentes_que_comprobar():
    # Sin esto, una carpeta movida dejaría pasar las demás pruebas vacías.
    assert _ficheros(), f"no hay agentes en {AGENTES}"


@pytest.mark.parametrize("fichero", _ficheros(), ids=lambda f: f.stem)
def test_cada_agente_se_carga(fichero: pathlib.Path):
    _cabecera(fichero.read_text(encoding="utf-8"))


def test_ningun_nombre_se_repite():
    # Dos ficheros con el mismo name: Claude Code se queda con uno y el otro
    # no se usa nunca, sin avisar.
    nombres = [_cabecera(f.read_text(encoding="utf-8"))["name"] for f in _ficheros()]
    assert len(nombres) == len(set(nombres)), nombres


@pytest.mark.parametrize(
    "texto, motivo",
    [
        (ROTO, "comillas dobles"),
        ("\n" + BUENO, "primera línea"),
        (BUENO.replace("name: roto\n", ""), "sin name"),
        (BUENO.replace("model: opus", "model: gpt"), "model desconocido"),
    ],
    ids=["dos-puntos-sin-comillas", "cabecera-tarde", "sin-name", "modelo-raro"],
)
def test_la_comprobacion_rechaza_lo_que_claude_code_salta(texto: str, motivo: str):
    with pytest.raises(ValueError, match=motivo):
        _cabecera(texto)


def test_la_comprobacion_acepta_lo_mismo_entre_comillas():
    assert _cabecera(BUENO)["description"].endswith("ellas: la política")


CLAUDE = shutil.which("claude")


@pytest.mark.skipif(CLAUDE is None, reason="Claude Code no está instalado aquí")
def test_claude_code_los_valida(tmp_path: pathlib.Path):
    # Primero se provoca: si `validate` no rechaza la cabecera rota, que pase
    # con las buenas no prueba nada.
    (tmp_path / "roto.md").write_text(ROTO, encoding="utf-8")
    roto = subprocess.run(
        [CLAUDE, "plugin", "validate", str(tmp_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    assert roto.returncode != 0, roto.stdout + roto.stderr

    bueno = subprocess.run(
        [CLAUDE, "plugin", "validate", str(AGENTES)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
    )
    assert bueno.returncode == 0, bueno.stdout + bueno.stderr
