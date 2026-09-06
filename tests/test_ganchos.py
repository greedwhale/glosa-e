# -*- coding: utf-8 -*-
"""El gancho que guarda la puerta de producción, provocado.

Por qué existe
--------------
No hay CI. Un push a `main` lo construye Vercel y lo publica, y lo único que
hay entre un test rojo y la página que ve la gente es
`.claude/hooks/antes-de-empujar.py`. Claude Code solo bloquea una orden cuando
el gancho **sale con código 2**: con cualquier otro código —incluido el 1 que
deja una excepción sin recoger— la orden sigue adelante.

Ahí estaba el agujero. `subprocess.run(..., timeout=600)` lanza
`TimeoutExpired`, y arrancar un ejecutable puede lanzar `OSError`; las dos
subían sin recoger hasta `sys.exit(main())`, imprimían una traza y salían con
1. El push se publicaba **después de que el gancho hubiera fallado**, que es la
peor forma de tener una puerta: la que además tranquiliza.

Lo que esto comprueba, y lo que no
-----------------------------------
**Sí:** que cada camino de fallo del gancho acaba en 2, y que las órdenes que
no son un push siguen pasando sin pagar la suite.

**No:** que el gancho esté *conectado*. La declaración vive en los ajustes de
usuario (`C:\\Users\\PC\\.claude\\settings.json`), fuera del repositorio, así
que en una máquina nueva este fichero está y la puerta no existe. Eso solo se
comprueba provocándolo de verdad, y así está escrito en `CLAUDE.md`:

    git push remoto-que-no-existe main   # con gancho tarda ~36 s; sin él, uno
"""
from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import subprocess

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GANCHO = RAIZ / ".claude" / "hooks" / "antes-de-empujar.py"


@pytest.fixture(scope="module")
def gancho():
    """El gancho cargado como módulo, que su nombre con guiones no permite."""
    especificacion = importlib.util.spec_from_file_location(
        "antes_de_empujar", GANCHO)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def correr(gancho, monkeypatch, orden: str, *, entrada: str | None = None,
           corriendo=None) -> int:
    """Llama al gancho como lo llama Claude Code: un JSON por la entrada.

    `corriendo` sustituye a `subprocess.run` **siempre**, incluso cuando la
    prueba no espera que se use: si algún camino lo llamara de verdad, esto
    lanzaría la suite entera desde dentro de la suite.
    """
    texto = entrada if entrada is not None else json.dumps(
        {"tool_input": {"command": orden}, "cwd": str(RAIZ)})
    monkeypatch.setattr(gancho.sys, "stdin", io.StringIO(texto))

    def prohibido(*_a, **_k):
        raise AssertionError("no debería haber llegado a correr los tests")

    monkeypatch.setattr(gancho.subprocess, "run", corriendo or prohibido)
    return gancho.main()


class TestLoQueDejaPasar:
    def test_una_orden_que_no_es_un_push_no_paga_la_suite(self, gancho,
                                                          monkeypatch):
        assert correr(gancho, monkeypatch, "git status") == 0

    def test_un_ensayo_no_publica_y_no_se_mira(self, gancho, monkeypatch):
        assert correr(gancho, monkeypatch, "git push --dry-run origin main") == 0

    def test_una_entrada_ilegible_sin_push_no_estorba(self, gancho, monkeypatch):
        """El gancho está roto, pero esa orden no publica nada."""
        assert correr(gancho, monkeypatch, "", entrada="{esto no es JSON") == 0

    def test_la_suite_en_verde_deja_publicar(self, gancho, monkeypatch):
        hecho = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        assert correr(gancho, monkeypatch, "git push origin main",
                      corriendo=lambda *a, **k: hecho) == 0


class TestLoQuePara:
    """Todo lo de aquí tiene que salir con 2. Con 1 el push se publica igual."""

    def test_la_suite_en_rojo(self, gancho, monkeypatch):
        hecho = subprocess.CompletedProcess(
            [], 1, stdout="E   assert 1 == 2\n1 failed", stderr="")
        assert correr(gancho, monkeypatch, "git push origin main",
                      corriendo=lambda *a, **k: hecho) == 2

    def test_la_suite_que_se_queda_colgada(self, gancho, monkeypatch, capsys):
        """El fallo que salía con 1: `TimeoutExpired` subía sin recoger."""
        def cuelga(*_a, **_k):
            raise subprocess.TimeoutExpired(cmd="pytest", timeout=600)

        assert correr(gancho, monkeypatch, "git push origin main",
                      corriendo=cuelga) == 2
        assert "produccion" in capsys.readouterr().err

    def test_el_interprete_que_no_arranca(self, gancho, monkeypatch, capsys):
        """El otro: cualquier `OSError` al lanzar el proceso."""
        def revienta(*_a, **_k):
            raise OSError(8, "Formato de ejecutable no válido")

        assert correr(gancho, monkeypatch, "git push origin main",
                      corriendo=revienta) == 2
        assert "nadie ha comprobado nada" in capsys.readouterr().err

    def test_cualquier_otra_rotura_del_gancho(self, gancho, monkeypatch, capsys):
        """La red de debajo de todo, por lo que no está previsto."""
        def revienta(*_a, **_k):
            raise RuntimeError("algo que no se le ocurrió a nadie")

        assert correr(gancho, monkeypatch, "git push origin main",
                      corriendo=revienta) == 2
        assert "no ha llegado a comprobar nada" in capsys.readouterr().err

    def test_una_entrada_ilegible_con_un_push_dentro(self, gancho, monkeypatch,
                                                     capsys):
        """Si Claude Code cambiara la forma de la entrada, esto es lo único.

        Sin esto el gancho devolvería 0 a todo y seguiría pareciendo que
        guarda la puerta: verde, y no es lo que crees que has probado.
        """
        assert correr(gancho, monkeypatch, "",
                      entrada='{"tool_input": {"comm git push origin main') == 2
        assert "no ha podido leer su entrada" in capsys.readouterr().err

    def test_sin_entorno_virtual_no_hay_manera_de_comprobar_nada(
            self, gancho, monkeypatch, capsys):
        monkeypatch.setattr(gancho, "PYTHON", RAIZ / "no-existe" / "python.exe")
        assert correr(gancho, monkeypatch, "git push origin main") == 2
        assert "publica en producción" in capsys.readouterr().err


def test_ningun_camino_del_gancho_sale_con_uno(gancho, monkeypatch):
    """El resumen de todo lo de arriba, dicho de una vez.

    El 1 es el código que no sirve para nada aquí: no bloquea, y quien lo ve
    en el registro cree que el gancho ha hecho algo. Los únicos dos válidos
    son 0 —pasa— y 2 —no pasa—.
    """
    casos = [
        ("git status", None, "{}"),
        ("git push --dry-run x y", None, None),
        ("git push origin main", lambda *a, **k: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(cmd="pytest", timeout=600)), None),
        ("git push origin main", lambda *a, **k: (_ for _ in ()).throw(
            OSError("lo que sea")), None),
        ("git push origin main", lambda *a, **k: subprocess.CompletedProcess(
            [], 1, stdout="1 failed", stderr=""), None),
        ("", None, "no es json y no habla de git"),
        ("", None, "no es json y dice git push"),
    ]
    for orden, corriendo, entrada in casos:
        salida = correr(gancho, monkeypatch, orden, entrada=entrada,
                        corriendo=corriendo)
        assert salida in (0, 2), f"«{orden or entrada}» ha salido con {salida}"
