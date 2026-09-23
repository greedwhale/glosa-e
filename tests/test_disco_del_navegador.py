"""El disco virtual del navegador: lo que se escribe en él y lo que se borra.

Aquí no hay Node ni navegador, así que el JavaScript no se ejecuta en la
suite: lo que se comprueba es que las dos reglas **siguen escritas** en
`web/glosa.js`. Las pruebas de verdad se hicieron en el navegador el
22-09-2026, sirviendo el repositorio como en desarrollo —sin manifiesto, que
es la condición en la que esto pasaba—, y las cifras están aquí porque una
prueba de texto que no diga qué se midió es justo la clase de verde que este
repositorio no se cree.

Lo que no llegó no se escribe
----------------------------
Un `fetch` no falla porque el servidor conteste 404: devuelve la respuesta con
el cuerpo del error dentro. Con `ejemplos/f-0001.xml` devolviendo un 404:

| | Antes | Después |
|---|---|---|
| El arranque | «Listo en 10,80 s» | «No ha arrancado» |
| Lo que quedaba con nombre de factura | **164 bytes de «404 Not Found»** | nada |
| Lo que decía la página | nada | «El ejemplo «f-0001.xml» no ha llegado: ../ejemplos/f-0001.xml contesta 404.» |

Y el informe de ese ejemplo salía: «1 fichero(s) · 0 correcto(s) · 0 con
errores · 1 SIN COMPROBAR», un veredicto sobre un documento que nunca llegó.
En el sitio publicado lo paraba la huella del manifiesto, pero **de rebote**;
en desarrollo no hay manifiesto y pasaba entero.

Lo que se soltó no se queda
---------------------------
El disco virtual vive en la memoria de la pestaña y no se vacía solo:

| | Antes | Después |
|---|---|---|
| Tres validaciones seguidas | tres facturas vivas en `/entrada/0`, 8.343 bytes | `/entrada` vacío, sin ficheros ni carpetas |
| Con el Python roto a propósito | —  | el error sale, `/entrada` queda vacío y la siguiente validación funciona |

Seis validaciones dejaban 480.438 bytes. No es que salieran de ahí —a ningún
sitio se suben—: es que son de quien las soltó y ya no hacen falta.
"""

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GLOSA_JS = RAIZ / "web" / "glosa.js"


def _codigo() -> str:
    return GLOSA_JS.read_text(encoding="utf-8")


class TestLoQueNoLlegaNoSeEscribe:
    """El fallo 31 de la auditoría, reproducido y cerrado el 22-09-2026."""

    def test_hay_una_manera_de_pedir_lo_que_tiene_que_estar(self):
        codigo = _codigo()
        assert "async function pedir(direccion, queEs, opciones) {" in codigo
        assert re.search(r"if \(!respuesta\.ok\) \{\s*\n\s*throw new Error\(queEs", codigo), (
            "`pedir` ya no se niega cuando el servidor contesta otra cosa"
        )

    def test_ningun_fetch_se_salta_el_estado(self):
        """La regla de fondo, y la que caza el fallo 31 en un sitio nuevo.

        Un `fetch` cuyo estado no mira nadie se traga la página de error como
        si fuera lo que pidió. Los que pueden faltar a propósito —el
        manifiesto, el listado de `dist/`, el resumen del paquete y el zip—
        miran el estado igual, cada uno con su porqué escrito al lado.
        """
        codigo = _codigo()
        lineas = codigo.splitlines()
        sueltos = []
        for i, linea in enumerate(lineas):
            if not re.search(r"(?<!async function )\bfetch\(", linea):
                continue
            if linea.lstrip().startswith("//"):
                continue
            cerca = "\n".join(lineas[i:i + 4])
            if ".ok" not in cerca:
                sueltos.append((i + 1, linea.strip()))
        assert sueltos == [], (
            "estos `fetch` no miran el estado de la respuesta, así que un 404 "
            f"les entra como si fuera el fichero: {sueltos}"
        )

    def test_los_tres_que_tienen_que_estar_pasan_por_pedir(self):
        codigo = _codigo()
        for quien in ('pedir(donde, "El validador"',
                      'pedir(conHuella(EJEMPLOS_EN + nombre, clave)',
                      'pedir(conHuella("./prueba.py", "prueba.py")'):
            assert quien in codigo, f"ya no pasa por `pedir`: {quien}"


class TestLoQueSeSueltaNoSeQueda:
    """El fallo 33 de la auditoría, reproducido y cerrado el 22-09-2026."""

    def test_se_borra_lo_que_se_escribio(self):
        codigo = _codigo()
        assert "function borrarLoSoltado(rutas) {" in codigo
        assert "pyodide.FS.unlink(ruta);" in codigo, "ya no se borra el fichero"
        assert "pyodide.FS.rmdir(" in codigo, "ya no se borra su carpeta"

    def test_se_borra_aunque_la_validacion_reviente(self):
        """Y es justo cuando más fácil es olvidarse.

        Comprobado en el navegador rompiendo `runPythonAsync` a propósito: el
        error sale, `/entrada` queda vacío y la siguiente validación funciona.
        """
        codigo = _codigo()
        assert re.search(
            r"try \{\s*\n\s*return JSON\.parse\(await pyodide\.runPythonAsync\(INFORME\)\);"
            r"\s*\n\s*\} finally \{\s*\n\s*borrarLoSoltado\(rutas\);", codigo
        ), "el borrado ya no está en el `finally` de la validación"

    def test_la_limpieza_no_puede_tapar_el_fallo_de_la_validacion(self):
        """Cada borrado va por su cuenta: si esto reventara, taparía aquel."""
        codigo = _codigo()
        cuerpo = codigo[codigo.index("function borrarLoSoltado"):]
        cuerpo = cuerpo[:cuerpo.index("\n}")]
        assert cuerpo.count("try {") == 2 and cuerpo.count("catch") == 2, (
            "el borrado ya no está protegido pieza a pieza"
        )
