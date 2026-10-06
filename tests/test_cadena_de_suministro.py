# -*- coding: utf-8 -*-
"""Lo que entra en el sitio publicado: de dónde viene y quién lo mira.

Punto 11 de la auditoría del 15-09-2026, que eran tres agujeros con la misma
forma —algo que viaja al navegador de un desconocido sin que nadie lo
contraste—:

1. **Pyodide no tenía huellas fijadas.** `HUELLAS.txt` se calcula de lo que se
   baja y vive dentro de `vendor/`, que no se versiona: era un recibo, no un
   contrato. Y `traer_pyodide` reutilizaba lo que ya estuviera en la carpeta
   sin mirarlo, así que una descarga cortada de ayer se apuntaba hoy como
   buena.
2. **lxml y setuptools no tenían versión al construir en Vercel.** Lo que se
   prueba aquí es una combinación concreta; con un rango, la construcción se
   trae la del día y la rueda puede cambiar sin que cambie una línea de este
   repositorio.
3. **En el navegador no se comprobaban ni la rueda, ni los ejemplos, ni
   `prueba.py`.** Las huellas de `rueda.json` estaban ahí desde el principio y
   solo servían de `?v=`: medido, una rueda con un byte de más arrancaba y la
   página ponía «Listo».

Lo que **no** se comprueba aquí: que el CDN de jsdelivr siga sirviendo lo mismo.
Eso se contrastó a mano bajándolo dos veces, el 30-08-2026 y el 20-09-2026, y no
se mete en la suite: una prueba que pida red se cae el día que no la hay y
enseña a no creerse los rojos.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import pytest

from validador import paquete

RAIZ = pathlib.Path(__file__).resolve().parent.parent
VERCEL = RAIZ / "vercel.json"
PYPROYECTO = RAIZ / "pyproject.toml"
REQUISITOS = RAIZ / "requisitos-pruebas.txt"
GLOSA_JS = RAIZ / "web" / "glosa.js"


# --- 1. El intérprete que se sirve con la página ---------------------------


class TestLasHuellasDePyodideEstanFijadasAqui:
    def test_estan_las_del_nucleo(self):
        faltan = [n for n in paquete._NUCLEO if n not in paquete.HUELLAS_DE_PYODIDE]
        assert not faltan, (
            f"{faltan} se sirve(n) al navegador de quien visita y no tiene(n) "
            "huella fijada: lo que llegue se daría por bueno"
        )

    def test_son_sha256_de_verdad(self):
        for nombre, huella in paquete.HUELLAS_DE_PYODIDE.items():
            assert re.fullmatch(r"[0-9a-f]{64}", huella), nombre

    def test_la_version_va_con_ellas(self, tmp_path):
        """Subir de versión sin tocar la tabla no puede pasar de largo.

        Sobre `tmp_path` y no sobre una carpeta del repositorio: al provocar
        esta guardia —quitando la negativa— el que se crea la carpeta es
        `traer_pyodide`, y una prueba que deja restos es una prueba que un día
        tapa algo. Pasó al provocarla.
        """
        destino = tmp_path / "pyodide"
        with pytest.raises(paquete.PyodideQueNoCuadra) as motivo:
            paquete.traer_pyodide(destino, version="9.9.9")
        assert paquete.VERSION_DE_PYODIDE in str(motivo.value)
        assert not destino.exists(), (
            "se ha negado después de crear la carpeta: la negativa va primero"
        )

    def test_lo_que_no_cuadra_no_pasa(self):
        nombre = "pyodide.js"
        with pytest.raises(paquete.PyodideQueNoCuadra) as motivo:
            paquete._que_cuadre(nombre, b"otra cosa", "de mentira")
        assert nombre in str(motivo.value)

    def test_lo_que_no_se_sabe_que_es_tampoco(self):
        with pytest.raises(paquete.PyodideQueNoCuadra):
            paquete._que_cuadre("algo-nuevo.wasm", b"x", "de mentira")

    def test_lo_que_cuadra_pasa(self, monkeypatch):
        """Una negativa que se niega a todo tampoco sirve.

        Los 15 MB de verdad no se traen a una prueba, así que se mete una
        entrada de mentira en la tabla y se comprueba con ella.
        """
        crudo = b"unos bytes cualesquiera"
        huella = hashlib.sha256(crudo).hexdigest()
        monkeypatch.setitem(paquete.HUELLAS_DE_PYODIDE, "de-mentira.bin", huella)
        assert paquete._que_cuadre("de-mentira.bin", crudo, "aquí") == huella


@pytest.mark.skipif(
    not (RAIZ / paquete.CARPETA_DE_PYODIDE / "pyodide-lock.json").is_file(),
    reason="el intérprete no está traído en esta copia (`vendor/` no se versiona)",
)
class TestElInterpreteDeEstaCopia:
    """Con `vendor/pyodide` traído: que sea el que la tabla dice.

    En GitHub esto se salta, porque `vendor/` no se versiona a propósito. No
    sobra por eso: aquí es donde se ve que la tabla y lo que se publica de
    verdad no se han separado.
    """

    CARPETA = RAIZ / paquete.CARPETA_DE_PYODIDE

    def test_todo_lo_que_hace_falta_tiene_huella(self):
        faltan = [
            n for n in paquete._lo_que_hace_falta(self.CARPETA)
            if n not in paquete.HUELLAS_DE_PYODIDE
        ]
        assert not faltan, faltan

    def test_y_los_ficheros_son_esos(self):
        for nombre in paquete._lo_que_hace_falta(self.CARPETA):
            ruta = self.CARPETA / nombre
            if not ruta.is_file():
                continue
            medida = hashlib.sha256(ruta.read_bytes()).hexdigest()
            assert medida == paquete.HUELLAS_DE_PYODIDE[nombre], (
                f"«{nombre}» no es el fijado. O se ha estropeado, o alguien "
                "subió de versión sin tocar la tabla."
            )


# --- 2. Lo que se instala al construir -------------------------------------


def _orden_de_construccion() -> str:
    return json.loads(VERCEL.read_text(encoding="utf-8"))["buildCommand"]


def _version_en_requisitos(paquete_pedido: str) -> str:
    for linea in REQUISITOS.read_text(encoding="utf-8").splitlines():
        linea = linea.split("#")[0].strip()
        if linea.lower().startswith(paquete_pedido.lower() + "=="):
            return linea.split("==")[1].split(";")[0].strip()
    raise AssertionError(f"{paquete_pedido} no está fijado en {REQUISITOS.name}")


class TestLoQueSeInstalaAlConstruirTieneVersion:
    """«Las versiones se fijan y no se siguen a latest», también en Vercel."""

    def test_lxml_va_con_version(self):
        orden = _orden_de_construccion()
        assert re.search(r"\blxml==\d+\.\d+\.\d+", orden), (
            "`vercel.json` instala lxml sin versión. Lo que se prueba aquí es "
            "una combinación concreta; si se mueve sola, el día que algo se "
            f"rompa no se sabrá qué cambió. Orden: {orden}"
        )

    def test_y_es_la_misma_que_corre_la_suite(self):
        """Dos versiones distintas son dos productos distintos."""
        en_vercel = re.search(r"\blxml==(\d+\.\d+\.\d+)", _orden_de_construccion())
        assert en_vercel.group(1) == _version_en_requisitos("lxml"), (
            "la lxml que construye el sitio y la que corre la suite no son la "
            "misma, así que lo que se prueba no es lo que se publica"
        )

    def test_setuptools_va_fijado_donde_de_verdad_se_lee(self):
        """En `pyproject.toml`, no en la orden de Vercel.

        `pip wheel` construye en un entorno aislado y se trae el setuptools
        que diga `[build-system] requires`: un `pip install setuptools==X`
        delante no lo toca.
        """
        texto = PYPROYECTO.read_text(encoding="utf-8")
        requiere = re.search(r'requires\s*=\s*\[([^\]]*)\]', texto).group(1)
        assert re.search(r'"setuptools==\d+\.\d+(\.\d+)?"', requiere), (
            f"setuptools no está fijado en pyproject.toml: {requiere.strip()}"
        )


# --- 3. Lo que el navegador se baja ----------------------------------------


class TestElNavegadorMiraLoQueSeBaja:
    """Aquí no hay Node, así que esto comprueba que **sigue escrito**.

    Corrido de verdad en el navegador el 20-09-2026, sobre el sitio montado en
    local: el arranque entero y las 42 del banco en verde con las huellas
    puestas, y en rojo cambiando un byte del wheel.
    """

    @property
    def codigo(self) -> str:
        return GLOSA_JS.read_text(encoding="utf-8")

    def test_existe_la_comparacion(self):
        assert "async function comprobar(clave, bytes, queEs)" in self.codigo

    def test_no_comprobado_no_es_lo_mismo_que_bien(self):
        """Sin manifiesto o sin `crypto.subtle`, devuelve `null`, no `true`."""
        trozo = self.codigo.split("async function comprobar(")[1].split("\n}")[0]
        assert "if (!publicada) return null;" in trozo
        assert "if (medida === null) return null;" in trozo

    @pytest.mark.parametrize("queien", [
        'await comprobar(clave, crudo, "El validador")',
        'await comprobar(clave, crudo, "El ejemplo ',
        'await comprobar("prueba.py", crudo, "El fichero de comprobaciones")',
    ])
    def test_se_llama_para_los_tres(self, queien):
        assert queien in self.codigo, (
            "uno de los tres vuelve a bajarse sin mirarse: la rueda, los "
            "ejemplos o el fichero del banco"
        )

    def test_el_wheel_se_mira_antes_de_instalarlo(self):
        """El orden importa: primero se mira y solo después se instala.

        Se baja dos veces a propósito —`loadPackage` solo acepta una dirección
        y se la pide él—, y la segunda sale de la caché. Lo que no puede
        cambiar de orden es esto: mirar después de instalar es enterarse tarde.
        """
        instalar = self.codigo.split(
            "async function instalarElValidador()")[1].split("\n}")[0]
        assert "await comprobar(" in instalar
        assert instalar.index("await comprobar(") < instalar.index(
            "await pyodide.loadPackage("), (
            "se instala y después se mira, que es enterarse tarde"
        )

    def test_la_huella_entera_se_compara_y_los_ocho_se_escriben(self):
        codigo = self.codigo
        assert 'huella.slice(0, 8)' in codigo, (
            "el `?v=` tiene que seguir siendo de ocho: con la huella entera "
            "cambiarían todas las direcciones y la caché de quien ya haya "
            "pasado dejaría de valer"
        )


class TestElCatalogoYElAlmacenNoSeRehacen:
    """Punto 14: se rehacían en cada validación y no cambian nunca.

    Medido en esta máquina con la factura de ejemplo: 70 ms rehaciéndolos y
    1,9 ms reusándolos. Eso se pagaba en cada factura soltada.
    """

    def test_se_arman_una_vez(self):
        codigo = GLOSA_JS.read_text(encoding="utf-8")
        informe = codigo.split("const INFORME = `")[1].split("`;")[0]
        assert 'if "_c" not in globals():' in informe, (
            "el informe vuelve a armar el catálogo y el almacén en cada "
            "validación"
        )
        # Y que sigan llegando a `validar_lote`, que es de lo que sirve todo
        # esto: guardarlos y no usarlos sería peor que no guardarlos.
        assert "catalogo=_c, almacen=_a" in informe


class TestCadaRutaSeCompilaUnaVez:
    """Punto 14, la otra mitad: `nodo.xpath(ruta)` compila en cada llamada.

    Una factura de 800 líneas hacía 31.235 llamadas a `texto()` y 16.080 a
    `_nodos()`, con las mismas cuatro docenas de rutas. Medido aparte: 8.000
    evaluaciones de la misma ruta cuestan 315 ms sueltas y 32 compilándola una
    vez. Fuera del navegador, una factura de 4.000 líneas pasó de 4.137 ms a
    1.705; dentro, de 20,5–23,8 s a 4,2–5,3.

    Esto no mide tiempos —una prueba de reloj en una máquina cualquiera enseña
    a no creerse los rojos—: comprueba que la ruta compilada se guarda y que
    quien la usa la usa.
    """

    def test_la_misma_ruta_da_la_misma_compilada(self):
        from validador import sintaxis

        espacios = sintaxis.SINTAXIS_UBL.espacios
        una = sintaxis._compilada(".//cbc:ID", espacios)
        otra = sintaxis._compilada(".//cbc:ID", espacios)
        assert una is otra, "la ruta se vuelve a compilar en cada llamada"

    def test_espacios_distintos_no_se_confunden(self):
        """Dos sintaxis con la misma ruta y distintos espacios de nombres."""
        from validador import sintaxis

        ubl = sintaxis._compilada("//x", sintaxis.SINTAXIS_UBL.espacios)
        cii = sintaxis._compilada("//x", sintaxis.SINTAXIS_CII.espacios)
        assert ubl is not cii

    def test_lo_que_leia_a_pelo_pasa_por_ahi(self):
        """Los cuatro sitios calientes del perfil."""
        import inspect

        from validador import decimales, listas_de_codigos, modelo, sintaxis

        for modulo, funciones in (
            (sintaxis, ["texto"]),
            (modelo, ["_nodos", "_esta", "_escrito"]),
            (listas_de_codigos, ["_nodos", "_escrito"]),
            (decimales, ["_nodos", "_escrito"]),
        ):
            for nombre in funciones:
                fuente = inspect.getsource(getattr(modulo, nombre))
                assert ".xpath(" not in fuente, (
                    f"{modulo.__name__}.{nombre} vuelve a compilar la ruta en "
                    "cada llamada"
                )

    def test_la_cache_no_crece_sin_tope(self):
        """Por si alguien llama con diccionarios de espacios recién hechos."""
        from validador import sintaxis

        assert sintaxis._TOPE_DE_RUTAS > 0
        for n in range(sintaxis._TOPE_DE_RUTAS + 5):
            sintaxis._compilada("//x", {"a": f"urn:{n}"})
        guardadas = getattr(sintaxis._COMPILADAS, "rutas", {})
        assert len(guardadas) <= sintaxis._TOPE_DE_RUTAS
