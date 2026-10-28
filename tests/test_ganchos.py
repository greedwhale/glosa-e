# -*- coding: utf-8 -*-
"""Los dos ganchos que guardan la puerta de producción, provocados.

Por qué hay dos
---------------
No hay CI. Un push a `main` lo construye Vercel y lo publica sin correr las
pruebas. Hasta el 16-09-2026 la única puerta era `.claude/hooks/antes-de-
empujar.py`, que leía la orden escrita en Claude Code y corría la suite si le
parecía un push. La auditoría del 15-09-2026 le encontró nueve maneras de pasar
—`git -C . push`, `git.exe push`, un `--dry-run` en un comentario, solo el
primer `cd`...—, que corría las pruebas sobre la carpeta y no sobre lo que se
empujaba, y la de fondo: un push desde la consola no pasaba por él.

Ahora la suite la corre **git**, con `.githooks/pre-push`, en todo push de la
copia. Y el gancho de Claude Code queda de portero: no deja que una orden se
salte a git.

Lo que esto comprueba, y lo que no
-----------------------------------
**Sí:** las decisiones de los dos, con git y pytest sustituidos.

**No:** que estén *conectados*. `core.hooksPath` es configuración local de git
y la declaración del de Claude Code vive en los ajustes de usuario; ninguna de
las dos viaja con el repositorio. Eso solo se comprueba provocándolos de
verdad, como dice `CLAUDE.md`.
"""
from __future__ import annotations

import importlib.util
import io
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PORTERO = RAIZ / ".claude" / "hooks" / "antes-de-empujar.py"
DE_GIT = RAIZ / ".githooks" / "antes-de-empujar.py"
TRABAJO = RAIZ.parent


def _cargar(ruta: pathlib.Path, nombre: str):
    """Un gancho como módulo, que su nombre con guiones no permite importar."""
    especificacion = importlib.util.spec_from_file_location(nombre, ruta)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def portero(monkeypatch):
    modulo = _cargar(PORTERO, "portero")
    # Puesto por defecto. Las pruebas que miran el caso contrario lo cambian.
    monkeypatch.setattr(modulo, "ganchos_puestos", lambda: True)
    return modulo


def decide(portero, orden: str, desde: pathlib.Path = RAIZ) -> bool:
    """¿Para? Por la entrada, como lo llama Claude Code."""
    return portero.decidir(orden, desde) is not None


# --- El portero -------------------------------------------------------------


class TestElPorteroNoSeLeenLasOrdenesComoAntes:
    """Las nueve de la auditoría, y dos más que salieron al reproducirlas.

    Con el gancho de git puesto, un push normal **pasa**: la suite la corre git
    y da igual cómo se escriba la orden. Lo que importa es que, sin el gancho
    puesto, **ninguna** de estas pase.
    """

    PUSHES = [
        "git push origin main",
        "git -C /c/Users/PC/Claude/Factura-e push origin main",
        "git -C . push origin main",
        "git -c core.askPass=x push origin main",
        "git.exe push origin main",
        '"C:\\Program Files\\Git\\cmd\\git.exe" push origin main',
        '& "C:\\Program Files\\Git\\cmd\\git.exe" push origin main',
        "git push origin main # --dry-run",
        "git push --dry-run origin main && git push origin main",
        'cd "/c/Users/PC/Claude/Proyecto 1" && cd /c/Users/PC/Claude/Factura-e && git push',
        "Set-Location C:\\Users\\PC\\Claude\\Factura-e; git -C . push",
        "cd /c/Users/PC/Claude/Factura-e\ngit push origin main",
    ]

    @pytest.mark.parametrize("orden", PUSHES)
    def test_sin_el_gancho_de_git_ningun_push_pasa(self, portero, monkeypatch, orden):
        monkeypatch.setattr(portero, "ganchos_puestos", lambda: False)
        assert decide(portero, orden)

    @pytest.mark.parametrize("orden", PUSHES)
    def test_con_el_gancho_puesto_pasan_y_prueba_git(self, portero, orden):
        assert not decide(portero, orden)


class TestLoQueSeSaltaAGit:
    @pytest.mark.parametrize("orden", [
        "git push --no-verify origin main",
        "git -C . push --no-verify",
        "git send-pack origin main",
        "git -c core.hooksPath=/dev/null push origin main",
        "git --config-env core.hooksPath=VACIO push",
        "GIT_CONFIG_PARAMETERS=\"'core.hooksPath=x'\" git push",
        "$env:GIT_CONFIG_PARAMETERS=\"'core.hooksPath=x'\"; git push",
        "git config --unset core.hooksPath",
        "git config core.hooksPath otra-carpeta",
        'git config alias.p "push --no-verify"',
    ])
    def test_para(self, portero, orden):
        assert decide(portero, orden)

    def test_se_deja_poner_el_gancho_y_leerlo(self, portero):
        assert not decide(portero, "git config core.hooksPath .githooks")
        assert not decide(portero, "git config --get core.hooksPath")


class TestLoQueNoEsAsuntoSuyo:
    def test_lo_que_no_es_git(self, portero, monkeypatch):
        monkeypatch.setattr(portero, "ganchos_puestos", lambda: False)
        assert not decide(portero, "./.venv/Scripts/python.exe -m pytest -q")
        assert not decide(portero, "git status")
        assert not decide(portero, 'git commit -m "push a main"')

    def test_otro_proyecto_de_la_carpeta_de_trabajo(self, portero, monkeypatch):
        monkeypatch.setattr(portero, "ganchos_puestos", lambda: False)
        otro = TRABAJO / "Proyecto 1"
        assert not decide(portero, "git push --no-verify", desde=otro)
        assert not decide(portero, f'cd "{otro}" && git push')
        assert not decide(portero, f'git -C "{otro}" push --no-verify')

    def test_una_orden_ilegible_que_no_parece_un_push(self, portero):
        assert not decide(portero, 'echo "sin cerrar')

    def test_una_orden_ilegible_que_si(self, portero):
        # Sin poder leerla no se sabe si lleva `--no-verify`.
        assert decide(portero, 'git push origin main -m "sin cerrar')


class TestElPorteroComoLoLlamaClaudeCode:
    """Todo lo de aquí tiene que salir con 2. Con 1 la orden sigue adelante."""

    def correr(self, portero, monkeypatch, texto: str) -> int:
        monkeypatch.setattr(portero.sys, "stdin", io.StringIO(texto))
        return portero.main()

    def entrada(self, orden: str) -> str:
        return json.dumps({"tool_input": {"command": orden}, "cwd": str(RAIZ)})

    def test_para_con_dos(self, portero, monkeypatch, capsys):
        assert self.correr(portero, monkeypatch, self.entrada("git push --no-verify")) == 2
        assert "--no-verify" in capsys.readouterr().err

    def test_deja_pasar_con_cero(self, portero, monkeypatch):
        assert self.correr(portero, monkeypatch, self.entrada("git status")) == 0

    def test_una_entrada_ilegible_con_un_push_dentro(self, portero, monkeypatch):
        """Si Claude Code cambiara la forma de la entrada, esto es lo único."""
        assert self.correr(portero, monkeypatch,
                           '{"tool_input": {"comm git push origin main') == 2

    def test_una_entrada_ilegible_sin_push_no_estorba(self, portero, monkeypatch):
        assert self.correr(portero, monkeypatch, "{esto no es JSON") == 0

    def test_si_el_portero_se_rompe_con_un_push_para(self, portero, monkeypatch):
        def revienta(*_a, **_k):
            raise RuntimeError("algo que no se le ocurrió a nadie")

        monkeypatch.setattr(portero, "decidir", revienta)
        assert self.correr(portero, monkeypatch, self.entrada("git push")) == 2
        assert self.correr(portero, monkeypatch, self.entrada("ls")) == 0

    def test_si_no_se_puede_preguntar_a_git_para(self, portero, monkeypatch):
        # Sin git a mano no se sabe si el gancho está puesto.
        def sin_git(*_a, **_k):
            raise OSError("no está git")

        modulo = _cargar(PORTERO, "portero_sin_git")
        monkeypatch.setattr(modulo.subprocess, "run", sin_git)
        assert self.correr(modulo, monkeypatch, self.entrada("git push")) == 2

    def test_ganchos_puestos_lee_la_configuracion_de_git(self, monkeypatch):
        modulo = _cargar(PORTERO, "portero_config")
        for escrito, puesto in ((".githooks\n", True), ("otra\n", False)):
            hecho = subprocess.CompletedProcess([], 0, stdout=escrito, stderr="")
            monkeypatch.setattr(modulo.subprocess, "run", lambda *a, h=hecho, **k: h)
            assert modulo.ganchos_puestos() is puesto
        vacio = subprocess.CompletedProcess([], 1, stdout="", stderr="")
        monkeypatch.setattr(modulo.subprocess, "run", lambda *a, **k: vacio)
        assert modulo.ganchos_puestos() is False


# --- El gancho de git -------------------------------------------------------

HEAD = "a" * 40
OTRO = "b" * 40
CEROS = "0" * 40


class Git:
    """Lo que el gancho le pregunta a git y a pytest, contestado a mano."""

    def __init__(self, cabeza=HEAD, pendiente="", suite=None):
        self.cabeza = cabeza
        self.pendiente = pendiente
        self.suite = suite
        self.corrio_la_suite = False

    def __call__(self, orden, **_k):
        if orden[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(orden, 0, stdout=self.cabeza + "\n")
        if orden[:2] == ["git", "status"]:
            return subprocess.CompletedProcess(orden, 0, stdout=self.pendiente)
        self.corrio_la_suite = True
        if isinstance(self.suite, BaseException):
            raise self.suite
        return self.suite or subprocess.CompletedProcess(orden, 0, stdout="", stderr="")


@pytest.fixture
def de_git(monkeypatch):
    modulo = _cargar(DE_GIT, "gancho_de_git")
    monkeypatch.setattr(modulo, "PYTHON", pathlib.Path(__file__))  # existe
    return modulo


def empujar(modulo, monkeypatch, git: Git, lineas: str) -> int:
    monkeypatch.setattr(modulo.subprocess, "run", git)
    monkeypatch.setattr(modulo.sys, "stdin", io.StringIO(lineas))
    return modulo.main()


def rama(sha=HEAD, remota="refs/heads/main") -> str:
    return f"refs/heads/main {sha} {remota} {CEROS}\n"


class TestElGanchoDeGit:
    def test_head_en_verde_pasa_y_corre_la_suite(self, de_git, monkeypatch):
        git = Git()
        assert empujar(de_git, monkeypatch, git, rama()) == 0
        assert git.corrio_la_suite

    def test_en_rojo_para(self, de_git, monkeypatch, capsys):
        git = Git(suite=subprocess.CompletedProcess(
            [], 1, stdout="E   assert 1 == 2\n1 failed", stderr=""))
        assert empujar(de_git, monkeypatch, git, rama()) != 0
        assert "assert 1 == 2" in capsys.readouterr().err

    def test_lo_que_no_es_head_para_sin_probar(self, de_git, monkeypatch):
        # Se prueba la carpeta: empujar otro commit sería publicar lo no probado.
        git = Git()
        assert empujar(de_git, monkeypatch, git, rama(sha=OTRO)) != 0
        assert not git.corrio_la_suite

    def test_con_cambios_sin_commit_para_sin_probar(self, de_git, monkeypatch, capsys):
        git = Git(pendiente=" M validador/firma.py\n?? nuevo.py\n")
        assert empujar(de_git, monkeypatch, git, rama()) != 0
        assert not git.corrio_la_suite
        assert "validador/firma.py" in capsys.readouterr().err

    def test_borrar_una_rama_o_empujar_una_etiqueta_no_publica(self, de_git, monkeypatch):
        git = Git(pendiente=" M sucio.py\n")
        lineas = (f"(delete) {CEROS} refs/heads/vieja {OTRO}\n"
                  f"refs/tags/v1 {OTRO} refs/tags/v1 {CEROS}\n")
        assert empujar(de_git, monkeypatch, git, lineas) == 0
        assert not git.corrio_la_suite

    def test_una_linea_que_no_se_entiende_para(self, de_git, monkeypatch):
        assert empujar(de_git, monkeypatch, Git(), "esto no son cuatro partes\n") != 0

    def test_la_suite_colgada_para(self, de_git, monkeypatch, capsys):
        git = Git(suite=subprocess.TimeoutExpired(cmd="pytest", timeout=900))
        assert empujar(de_git, monkeypatch, git, rama()) != 0
        # El mensaje dice lo medido, con su fecha, y no una cifra escrita a
        # mano: decía «tarda menos de tres» cuando ya tardaba más de siete.
        error = capsys.readouterr().err
        assert de_git.MEDIDO_EL in error
        assert f"unos {round(de_git.TARDA / 60)}" in error
        assert "menos de tres" not in error

    def test_el_limite_deja_margen_sobre_lo_medido(self, de_git):
        """El 28-10-2026 un push se cortó a los 900 s con una suite que tarda
        445: con la máquina cargada pasó del doble. Por debajo del triple, el
        límite vuelve a confundir una máquina ocupada con una suite colgada."""
        assert de_git.LIMITE >= 3 * de_git.TARDA

    def test_sin_poder_arrancar_la_suite_para(self, de_git, monkeypatch):
        git = Git(suite=OSError(8, "Formato de ejecutable no válido"))
        assert empujar(de_git, monkeypatch, git, rama()) != 0

    def test_sin_entorno_virtual_para(self, de_git, monkeypatch):
        monkeypatch.setattr(de_git, "PYTHON", RAIZ / "no-existe" / "python.exe")
        assert empujar(de_git, monkeypatch, Git(), rama()) != 0

    def test_si_git_falla_para(self, de_git, monkeypatch):
        def roto(orden, **_k):
            raise subprocess.CalledProcessError(128, orden)

        monkeypatch.setattr(de_git.subprocess, "run", roto)
        monkeypatch.setattr(de_git.sys, "stdin", io.StringIO(rama()))
        assert de_git.main() != 0


def test_el_gancho_de_git_sale_con_lf():
    """Con CRLF, `#!/bin/sh` deja de serlo y el push falla sin probar nada."""
    assert b"\r\n" not in (RAIZ / ".githooks" / "pre-push").read_bytes()


def test_el_gancho_de_git_se_versiona_ejecutable():
    """Sin el permiso de ejecución, git en Linux se salta el gancho y empuja.

    Medido el 07-10-2026 en una copia recién clonada en Linux, con
    `core.hooksPath` puesto: `pre-push` estaba en el índice como `100644`, y un
    push con un fichero sin commit no lo paró nadie. Git dejó una pista —«hook
    was ignored because it's not set as executable»— y siguió. En Windows no se
    notaba porque Git for Windows no mira ese permiso (`core.fileMode` falso) y
    el gancho corría. Con `+x` puesto a mano, el mismo push se negó en 0,1 s.

    Se mira el índice y no el disco: el permiso que viaja con el repositorio es
    el del índice, y en Windows el disco no lo tiene nunca.
    """
    salida = subprocess.run(
        ["git", "-C", str(RAIZ), "ls-files", "--stage", "--", ".githooks/pre-push"],
        check=True, capture_output=True, text=True, encoding="utf-8").stdout
    assert salida, "`.githooks/pre-push` no está versionado"
    modo = salida.split(maxsplit=1)[0]
    assert modo == "100755", (
        f"`.githooks/pre-push` está en el índice como {modo}: en Linux y en macOS "
        "git no lo llama y el push sale sin correr la suite. Se arregla con "
        "`git update-index --chmod=+x .githooks/pre-push`."
    )


def test_el_gancho_de_git_llama_al_guion_que_se_prueba_aqui():
    """Si uno cambia de nombre y el otro no, git llamaría a un fichero que no está.

    Fallaría cerrando —`exec` de algo que no existe sale distinto de 0—, pero
    todo lo de este fichero seguiría en verde probando un guion que nadie usa.
    """
    llamada = (RAIZ / ".githooks" / "pre-push").read_text(encoding="utf-8")
    assert f"{DE_GIT.parent.name}/{DE_GIT.name}" in llamada
    assert llamada.startswith("#!/bin/sh\n")


class TestUnWorktreeDeEstaCopiaNoEsOtroProyecto:
    """Medido el 21-09-2026, y era un camino a producción sin pruebas.

    `git worktree add C:\\Users\\PC\\Claude\\copia-de-prueba` deja una
    copia de Factura-e **fuera** de `Factura-e/` y colgando de la carpeta de
    trabajo. El portero la tomaba por otro proyecto y se apartaba: desde ahí,
    un `git push --no-verify` con un fichero sin commit salió con código 0 y
    empujó. Contra `origin` eso publica en producción sin correr nada.

    El fallo de fondo es el de siempre en este repositorio: reconocer una
    cadena de texto en vez de reconocer la cosa. Se le pregunta a git.
    """

    def test_git_reconoce_un_worktree_viva_donde_viva(self, portero, tmp_path):
        """Lo que hace que esto tenga arreglo: comparten el mismo `.git`."""
        fuera = tmp_path / "worktree"
        subprocess.run(
            ["git", "-C", str(RAIZ), "worktree", "add", "--detach", "-q",
             str(fuera), "HEAD"], check=True, capture_output=True)
        try:
            assert portero.del_repositorio(fuera)
        finally:
            subprocess.run(
                ["git", "-C", str(RAIZ), "worktree", "remove", "--force",
                 str(fuera)], capture_output=True)

    def test_el_portero_de_un_worktree_reconoce_las_dos_copias(self, tmp_path):
        """El gancho que se carga en un worktree es **el del worktree**.

        Y allí `REPO` es el worktree, cuyo `.git` es un fichero y no el
        directorio común: comparándolo con `REPO / ".git"` el portero no
        reconocía ni su propia copia ni la principal. Medido el 23-09-2026
        corriendo la suite desde un worktree: dos pruebas en rojo, y con ellas
        el gancho de git negándole el push a un worktree —que es donde este
        repositorio recomienda abrir la segunda sesión—.

        Las otras dos pruebas de esta clase no lo cazan porque cargan el
        gancho de **esta** copia, donde el medio arreglo bastaba. Ésta carga
        el de allí, así que vale desde donde se corra.
        """
        fuera = tmp_path / "worktree"
        subprocess.run(
            ["git", "-C", str(RAIZ), "worktree", "add", "--detach", "-q",
             str(fuera), "HEAD"], check=True, capture_output=True)
        try:
            # El worktree nace en HEAD, y lo que hay que probar es el gancho de
            # **ahora**: si no se copia, esta prueba va un commit por detrás y
            # deja pasar el día que se rompa.
            suyo_en_disco = fuera / ".claude" / "hooks" / "antes-de-empujar.py"
            suyo_en_disco.write_bytes(PORTERO.read_bytes())
            suyo = _cargar(suyo_en_disco, "portero_del_worktree")
            assert suyo.REPO.resolve() == fuera.resolve(), (
                "esta prueba no está mirando el gancho del worktree")
            assert suyo.del_repositorio(fuera), (
                "el portero del worktree no reconoce su propia copia")
            assert suyo.del_repositorio(RAIZ), (
                "el portero del worktree no reconoce la copia principal")
            assert not suyo.del_repositorio(tmp_path), (
                "y lo que no es del repositorio tiene que seguir sin serlo")
        finally:
            subprocess.run(
                ["git", "-C", str(RAIZ), "worktree", "remove", "--force",
                 str(fuera)], capture_output=True)

    def test_la_copia_buena_y_lo_que_cuelga_de_ella(self, portero):
        assert portero.del_repositorio(RAIZ)
        assert portero.del_repositorio(RAIZ / "validador")

    def test_lo_que_no_es_un_repositorio_no_lo_es(self, portero, tmp_path):
        assert not portero.del_repositorio(tmp_path)

    def test_si_git_dice_que_es_de_aqui_el_portero_no_se_aparta(
            self, portero, monkeypatch):
        """El cableado, que es lo que estaba roto."""
        monkeypatch.setattr(portero, "del_repositorio", lambda _c: True)
        copia = TRABAJO / "copia-de-prueba"
        assert decide(portero, "git push --no-verify", desde=copia)
        assert decide(portero, f'cd "{copia}" && git push --no-verify')

    def test_si_git_dice_que_no_sigue_sin_ser_asunto_suyo(
            self, portero, monkeypatch):
        """Los demás proyectos de la carpeta de trabajo tienen sus reglas."""
        monkeypatch.setattr(portero, "del_repositorio", lambda _c: False)
        monkeypatch.setattr(portero, "ganchos_puestos", lambda: False)
        assert not decide(portero, "git push --no-verify",
                          desde=TRABAJO / "Proyecto 1")


class TestElGanchoDeGitDesdeUnWorktree:
    """El otro lado del mismo hueco, y este estaba cerrado por accidente.

    `exec ./.venv/Scripts/python.exe` no existe en un worktree —`.venv` no se
    versiona—, así que salía «No such file or directory» y git cancelaba con
    código 1. Se negaba, sí, pero sin correr la suite ni mirar si había cambios
    sin commit, con un error de shell en vez del mensaje de casa, y se abría en
    cuanto alguien montase un `.venv` ahí.
    """

    def test_no_da_por_hecho_un_entorno_al_lado(self):
        llamada = (RAIZ / ".githooks" / "pre-push").read_text(encoding="utf-8")
        assert "exec ./.venv/" not in llamada, (
            "un worktree no tiene `.venv` propio"
        )
        assert "--git-common-dir" in llamada, (
            "cuál es la copia principal se le pregunta a git, no se deduce"
        )

    def test_sin_interprete_se_niega_con_palabras(self):
        """Que el motivo se lea, en vez de un «No such file or directory»."""
        llamada = (RAIZ / ".githooks" / "pre-push").read_text(encoding="utf-8")
        assert "No se empuja" in llamada
        assert "exit 1" in llamada

    def test_no_se_busca_el_interprete_por_su_cuenta(self):
        """`pre-push` ya eligió el bueno; buscarlo otra vez repite el fallo."""
        fuente = DE_GIT.read_text(encoding="utf-8")
        assert "sys.executable" in fuente, (
            "el intérprete es el que corre este guion, no el que haya junto a "
            "la copia: un worktree no tiene `.venv`"
        )

    def test_la_suite_corre_con_el_interprete_que_corre_el_guion(self):
        """Y esto lo mide, en vez de darlo por cierto.

        Aquí `REPO/.venv/Scripts/python.exe` y `sys.executable` son **el mismo
        fichero**, así que comparar los dos sale verde con la versión buena y
        con la mala. Lo único que las distingue es cargar el guion con otro
        intérprete y ver a cuál de los dos sigue.
        """
        otro = shutil.which("python")
        if not otro:
            pytest.skip("no hay un segundo intérprete con el que distinguirlas")
        guion = (
            "import importlib.util, sys;"
            "e = importlib.util.spec_from_file_location('g', sys.argv[1]);"
            "m = importlib.util.module_from_spec(e);"
            "e.loader.exec_module(m);"
            "print(m.PYTHON);"
            "print(sys.executable)"
        )
        hecho = subprocess.run(
            [otro, "-c", guion, str(DE_GIT)], capture_output=True, text=True,
            encoding="utf-8", errors="replace")
        if hecho.returncode != 0:
            pytest.skip(f"el segundo intérprete no arranca: {hecho.stderr[:80]}")
        suyo, suelto = (pathlib.Path(l) for l in hecho.stdout.split())
        assert suyo == suelto, "el guion no sigue al intérprete que lo corre"
        assert suyo != RAIZ / ".venv" / "Scripts" / "python.exe", (
            "sigue cogiendo el entorno de al lado, que en un worktree no está"
        )
