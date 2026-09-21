"""La fila de validaciones del navegador, en `web/glosa.js`.

Aqui no hay Node ni navegador, asi que el JavaScript no se ejecuta en la
suite: lo que se comprueba es que **nadie escribe `_rutas` fuera de la fila**.
La prueba de verdad se hizo en el navegador el 21-09-2026, y las cifras estan
aqui porque una prueba de texto que no diga que se midio es justo la clase de
verde que este repositorio no se cree.

Que pasaba
----------
`_rutas` y `_nombres` son globales de Pyodide. Una llamada las escribia y
`INFORME` las leia cuando el Python llegaba a ejecutarse; entre esas dos cosas
hay un `await`, y ahi cabia otra llamada entera, que las pisaba.

Medido en produccion, dos facturas propias soltadas en el mismo tick, una con
errores y otra sin ellos:

| Cuando                         | Informes de la mala que salian conformes |
|--------------------------------|------------------------------------------|
| antes, en el mismo tick        | **20 de 20**, hablando de la buena       |
| antes, con 1 ms de separacion  | 0 de 8                                   |
| despues, en el mismo tick      | **0 de 20**                              |

El informe de la factura con errores volvia diciendo «1 fichero(s) · 1
correcto(s) · 0 con errores» y `conforme: true`. No era una carrera rara: era
lo que pasaba siempre que dos validaciones arrancaban juntas.

Lo que no cambia
----------------
Encolar no hace esperar mas de lo que ya se esperaba: Pyodide corre Python en
el hilo principal, asi que dos validaciones nunca fueron simultaneas de
verdad. Lo unico que hacian a la vez era corromperse.
"""

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GLOSA_JS = RAIZ / "web" / "glosa.js"


def _codigo() -> str:
    return GLOSA_JS.read_text(encoding="utf-8")


def _cuerpo(codigo: str, nombre: str) -> str:
    """El texto de una funcion, desde su cabecera hasta la siguiente."""
    arranca = codigo.index(f"function {nombre}(")
    siguiente = codigo.find("\nasync function ", arranca + 1)
    otra = codigo.find("\nfunction ", arranca + 1)
    finales = [f for f in (siguiente, otra) if f != -1]
    return codigo[arranca:min(finales)] if finales else codigo[arranca:]


class TestLaFilaSigueAhi:
    def test_existe(self):
        codigo = _codigo()
        assert "let _cola = Promise.resolve();" in codigo
        assert "function enFila(faena)" in codigo

    def test_no_se_rompe_porque_una_falle(self):
        """Sin tragarse el error, una validacion mala mata la pagina entera."""
        assert "_cola = mio.then(() => {}, () => {});" in _codigo(), (
            "la cola tiene que seguir viva despues de un error"
        )

    def test_la_faena_se_encadena_una_sola_vez(self):
        """`then(faena, faena)` la correria otra vez si la cola se rompiera."""
        assert "_cola.then(faena);" in _codigo()
        assert "_cola.then(faena, faena)" not in _codigo()


class TestNadieEscribeRutasFueraDeLaFila:
    """Esto es lo que de verdad guarda el arreglo.

    Una entrada nueva que escriba `_rutas` sin pasar por `enFila` devuelve el
    fallo entero, y no hay comentario que lo impida. La prueba, si.
    """

    LAS_DE_DENTRO = ("_validarAhora", "_validarEjemploAhora")

    def test_solo_las_dos_de_dentro_tocan_las_globales(self):
        codigo = _codigo()
        quienes = set()
        for casa in re.finditer(r'pyodide\.globals\.set\("_(?:rutas|nombres)"',
                                codigo):
            # De quien es la funcion donde cae esta linea.
            delante = codigo[:casa.start()]
            cabeceras = re.findall(r"function (\w+)\(", delante)
            quienes.add(cabeceras[-1] if cabeceras else "(suelta)")
        assert quienes and quienes <= set(self.LAS_DE_DENTRO), (
            f"«{quienes - set(self.LAS_DE_DENTRO)}» escribe `_rutas` fuera de "
            "la fila: dos validaciones a la vez volverian a pisarse"
        )

    def test_solo_las_dos_de_dentro_corren_el_informe(self):
        codigo = _codigo()
        quienes = set()
        for casa in re.finditer(r"runPythonAsync\(INFORME\)", codigo):
            cabeceras = re.findall(r"function (\w+)\(", codigo[:casa.start()])
            quienes.add(cabeceras[-1] if cabeceras else "(suelta)")
        assert quienes and quienes <= set(self.LAS_DE_DENTRO), (
            f"«{quienes - set(self.LAS_DE_DENTRO)}» corre el informe fuera de "
            "la fila"
        )

    def test_las_dos_publicas_pasan_por_la_fila(self):
        codigo = _codigo()
        for publica in ("validar", "validarEjemplo"):
            cuerpo = _cuerpo(codigo, publica)
            assert "enFila(" in cuerpo, (
                f"`{publica}()` no encola: puede pisar a la que este corriendo"
            )

    def test_y_siguen_siendo_las_que_se_exportan(self):
        """Si se exportara la de dentro, la fila se saltaria sin tocarla."""
        codigo = _codigo()
        exporta = codigo[codigo.index("window.Glosa = {"):]
        exporta = exporta[:exporta.index("}")]
        assert "validar," in exporta and "validarEjemplo," in exporta
        for dentro in self.LAS_DE_DENTRO:
            assert dentro not in exporta
