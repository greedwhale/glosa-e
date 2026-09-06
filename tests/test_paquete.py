"""El paquete que se lleva la página: los esquemas y las anclas en un zip.

Lo que se prueba aquí no es comprimir, que eso lo hace la biblioteca estándar.
Es lo otro: que dentro vaya **todo** lo que hace falta para que las tres
comprobaciones sigan siendo tres al otro lado, y que no se empaquete un
conjunto de anclas que no se puede repartir.

Las dos negativas son la mitad del módulo. Un conjunto sin manifiesto no dice
de dónde viene, y uno cuya lista venció sigue creyendo a autoridades a las que
el Estado pudo retirarles la cualificación —con su certificado en vigor y su
cadena llegando, sin que nada en el documento lo delate—. Las dos cosas se
notan poco y se reparten fácil, que es la peor combinación.
"""

import json
import zipfile
from datetime import date
from pathlib import Path

import pytest

from validador import cadena, paquete
from validador.cadena import Almacen
from validador.esquema import Catalogo

MANIFIESTO = """de la lista de confianza de ES, publicada por el Ministerio el 2026-08-06

  publicada        2026-08-06
  siguiente        2027-02-02
  montada          2026-08-27
"""

# Un XSD que compila, para no depender de los oficiales.
XSD = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="cualquiera" type="xs:string"/>
</xs:schema>
"""


@pytest.fixture
def carpetas(tmp_path):
    """Las tres carpetas de las que sale un paquete, en pequeño."""
    esquemas = tmp_path / "esquemas"
    esquemas.mkdir()
    (esquemas / "Facturaev3_2_2.xsd").write_text(XSD, encoding="utf-8")
    (esquemas / "ubl").mkdir()
    (esquemas / "ubl" / "UBL-Invoice-2.1.xsd").write_text(XSD, encoding="utf-8")

    anclas = tmp_path / "anclas"
    (anclas / "retiradas").mkdir(parents=True)
    (anclas / cadena.NOMBRE_DEL_MANIFIESTO).write_text(MANIFIESTO, encoding="utf-8")
    (anclas / cadena.NOMBRE_DE_ESTADOS).write_text(
        "# huella\testado\tdesde\tprestador\n", encoding="utf-8"
    )
    (anclas / "una.cer").write_bytes(b"\x30\x01\x00")
    (anclas / "retiradas" / "vieja.cer").write_bytes(b"\x30\x01\x00")

    sellos = tmp_path / "anclas-sellos"
    sellos.mkdir()
    (sellos / "tsu.cer").write_bytes(b"\x30\x01\x00")
    return esquemas, anclas, sellos


def dentro(zip_: Path) -> set[str]:
    with zipfile.ZipFile(zip_) as z:
        return set(z.namelist())


class TestLoQueVaDentro:
    def test_van_las_tres_carpetas(self, tmp_path, carpetas):
        esquemas, anclas, sellos = carpetas
        destino = tmp_path / "paquete.zip"
        paquete.armar(destino, esquemas, anclas, sellos, hoy=date(2026, 9, 1))
        nombres = dentro(destino)
        assert "esquemas/Facturaev3_2_2.xsd" in nombres
        assert "esquemas/ubl/UBL-Invoice-2.1.xsd" in nombres
        assert "anclas/una.cer" in nombres
        assert "anclas-sellos/tsu.cer" in nombres

    def test_van_las_retiradas_y_su_tabla(self, tmp_path, carpetas):
        """Las dos, o ninguna de las dos.

        Una ancla retirada solo vale para lo que se firmó antes de que la
        retiraran, y quién dice cuándo fue es `ESTADOS.tsv`. Sin esa tabla,
        `cadena.py` no usa las retiradas —falla por el lado bueno— pero
        empaquetar unas sin la otra sería repartir un conjunto que en la
        página se comporta distinto que en consola, sin decirlo.
        """
        esquemas, anclas, sellos = carpetas
        destino = tmp_path / "paquete.zip"
        paquete.armar(destino, esquemas, anclas, sellos, hoy=date(2026, 9, 1))
        nombres = dentro(destino)
        assert "anclas/retiradas/vieja.cer" in nombres
        assert f"anclas/{cadena.NOMBRE_DE_ESTADOS}" in nombres

    def test_va_el_manifiesto(self, tmp_path, carpetas):
        """Sin él, el informe no puede decir de dónde salen las anclas."""
        esquemas, anclas, sellos = carpetas
        destino = tmp_path / "paquete.zip"
        paquete.armar(destino, esquemas, anclas, sellos, hoy=date(2026, 9, 1))
        assert f"anclas/{cadena.NOMBRE_DEL_MANIFIESTO}" in dentro(destino)

    def test_se_cuenta_lo_que_lleva(self, tmp_path, carpetas):
        esquemas, anclas, sellos = carpetas
        contenido = paquete.armar(
            tmp_path / "paquete.zip", esquemas, anclas, sellos, hoy=date(2026, 9, 1)
        )
        assert contenido.esquemas == 2
        assert contenido.anclas == 2  # la buena y la retirada
        assert contenido.anclas_de_sellos == 1
        # El papeleo no se cuenta como ancla: son dos certificados, no cuatro.
        assert contenido.bytes > 0
        assert len(contenido.huella) == 64

    def test_las_fechas_salen_del_manifiesto(self, tmp_path, carpetas):
        esquemas, anclas, sellos = carpetas
        contenido = paquete.armar(
            tmp_path / "paquete.zip", esquemas, anclas, sellos, hoy=date(2026, 9, 1)
        )
        assert contenido.publicada == "2026-08-06"
        assert contenido.siguiente == "2027-02-02"
        assert contenido.montada == "2026-08-27"
        assert contenido.armado == "2026-09-01"
        assert contenido.declarada.startswith("de la lista de confianza de ES")


class TestElResumenDeFuera:
    """El JSON de al lado, que la página lee antes de arrancar Python.

    Va fuera además de dentro porque hasta que no terminan de bajar los 14 MB
    del intérprete no hay forma de leer nada del zip, y de cuándo son las
    anclas es justo lo que hay que poder decir cuanto antes.
    """

    def test_se_escribe_al_lado(self, tmp_path, carpetas):
        esquemas, anclas, sellos = carpetas
        paquete.armar(
            tmp_path / "paquete.zip", esquemas, anclas, sellos, hoy=date(2026, 9, 1)
        )
        fuera = json.loads((tmp_path / paquete.MANIFIESTO).read_text("utf-8"))
        assert fuera["anclas"] == 2
        assert fuera["siguiente"] == "2027-02-02"

    def test_el_de_dentro_y_el_de_fuera_cuentan_lo_mismo(self, tmp_path, carpetas):
        """Salen de la misma vuelta, así que no pueden contar cosas distintas.

        Menos el tamaño y la huella, que el de dentro no puede llevar: estarían
        dentro de lo que miden.
        """
        esquemas, anclas, sellos = carpetas
        destino = tmp_path / "paquete.zip"
        paquete.armar(destino, esquemas, anclas, sellos, hoy=date(2026, 9, 1))
        fuera = json.loads((tmp_path / paquete.MANIFIESTO).read_text("utf-8"))
        with zipfile.ZipFile(destino) as z:
            adentro = json.loads(z.read(paquete.MANIFIESTO))
        aparte = {"bytes", "huella"}
        assert {k: v for k, v in fuera.items() if k not in aparte} == {
            k: v for k, v in adentro.items() if k not in aparte
        }


class TestLoQueNoSeEmpaqueta:
    def test_sin_manifiesto_no_se_reparte(self, tmp_path, carpetas):
        """Un conjunto que no dice de dónde viene no sale de aquí."""
        esquemas, anclas, sellos = carpetas
        (anclas / cadena.NOMBRE_DEL_MANIFIESTO).unlink()
        with pytest.raises(paquete.SinManifiesto) as motivo:
            paquete.armar(
                tmp_path / "p.zip", esquemas, anclas, sellos, hoy=date(2026, 9, 1)
            )
        # Y se dice qué hacer, no solo que no.
        assert "--montar-anclas" in str(motivo.value)
        assert not (tmp_path / "p.zip").exists()

    def test_con_la_lista_vencida_no_se_reparte(self, tmp_path, carpetas):
        esquemas, anclas, sellos = carpetas
        with pytest.raises(paquete.SinRenovar) as motivo:
            paquete.armar(
                tmp_path / "p.zip", esquemas, anclas, sellos, hoy=date(2027, 6, 1)
            )
        assert "2027-02-02" in str(motivo.value)
        assert not (tmp_path / "p.zip").exists()

    def test_un_dia_antes_todavia_se_reparte(self, tmp_path, carpetas):
        """La frontera es la que dice la lista, no un margen inventado."""
        esquemas, anclas, sellos = carpetas
        paquete.armar(
            tmp_path / "p.zip", esquemas, anclas, sellos, hoy=date(2027, 2, 2)
        )
        assert (tmp_path / "p.zip").exists()

    def test_se_puede_forzar_para_probar(self, tmp_path, carpetas):
        esquemas, anclas, sellos = carpetas
        paquete.armar(
            tmp_path / "p.zip",
            esquemas,
            anclas,
            sellos,
            hoy=date(2027, 6, 1),
            aunque_esten_vencidas=True,
        )
        assert (tmp_path / "p.zip").exists()

    def test_una_lista_sin_fecha_de_renovacion_no_bloquea(self, tmp_path, carpetas):
        """No se puede afirmar que esté vencida, así que no se impide."""
        esquemas, anclas, sellos = carpetas
        (anclas / cadena.NOMBRE_DEL_MANIFIESTO).write_text(
            "de una lista sin fecha de renovación\n\n  publicada        2020-01-01\n",
            encoding="utf-8",
        )
        paquete.armar(
            tmp_path / "p.zip", esquemas, anclas, sellos, hoy=date(2030, 1, 1)
        )
        assert (tmp_path / "p.zip").exists()


# --- Con las carpetas de verdad, si están instaladas -----------------------

ESQUEMAS = Path("esquemas")
ANCLAS = Path("anclas")
instaladas = pytest.mark.skipif(
    not (ESQUEMAS.is_dir() and (ANCLAS / cadena.NOMBRE_DEL_MANIFIESTO).is_file()),
    reason="no están los esquemas y las anclas montadas",
)
EJEMPLO = Path("ejemplos/fe-0001.xml")


@instaladas
class TestElPaqueteDeVerdad:
    """Que lo que sale de aquí sirva al otro lado, que es de lo que se trata.

    Las pruebas de arriba comprueban que el zip lleva lo que dice llevar. Esta
    comprueba lo siguiente: que descomprimido en otro sitio, el validador
    encuentra los esquemas y las anclas y hace las tres comprobaciones. Un
    paquete bien formado del que no salga un catálogo utilizable es un paquete
    que solo sirve para creer que la página está completa.
    """

    def armado(self, tmp_path) -> Path:
        destino = tmp_path / "paquete.zip"
        paquete.armar(destino, ESQUEMAS, ANCLAS, hoy=date(2026, 8, 28))
        suelto = tmp_path / "suelto"
        with zipfile.ZipFile(destino) as z:
            z.extractall(suelto)
        return suelto

    def test_de_ahi_sale_un_catalogo_que_compila(self, tmp_path):
        catalogo = Catalogo(self.armado(tmp_path) / "esquemas")
        assert not catalogo.vacio
        from validador.formato import detectar

        datos = EJEMPLO.read_bytes()
        assert catalogo.ruta_para(detectar(datos)) is not None

    def test_de_ahi_sale_un_almacen_que_sabe_de_cuando_es(self, tmp_path):
        almacen = Almacen(self.armado(tmp_path) / "anclas")
        assert not almacen.vacio
        assert almacen.declarada.startswith("de la lista de confianza")
        assert almacen.renovacion.siguiente is not None

    def test_y_las_anclas_de_sellado_van_al_lado_y_se_encuentran(self, tmp_path):
        """La carpeta hermana, que es la que se olvida al copiar a mano."""
        almacen = Almacen(self.armado(tmp_path) / "anclas")
        assert not almacen.sellos.vacio

    @pytest.mark.skipif(not EJEMPLO.exists(), reason="no está el ejemplo")
    def test_el_informe_promete_las_tres_cosas(self, tmp_path):
        """El resumen del final cambia según lo que de verdad se ha mirado.

        Es la razón de ser de todo esto: sin el paquete, la página comprueba
        el contenido y su propia frase final lo dice. Con él, dice las tres.
        """
        from validador import factura

        suelto = self.armado(tmp_path)
        con = factura.validar_lote(
            [EJEMPLO],
            catalogo=Catalogo(suelto / "esquemas"),
            almacen=Almacen(suelto / "anclas"),
        ).alcance(forma=True, anclas=True)
        assert "esquema XSD" in con
        assert "autoridad de confianza instalada" in con


# --- El sitio que se publica -----------------------------------------------

# El cargador tal como está en el repositorio, reducido a las dos líneas que
# importan aquí. Son las que dicen dónde busca el wheel y los ejemplos, y las
# comparten las dos páginas.
CARGADOR = """const VERSION_PYODIDE = "{}";
const DIST = "../dist/";
const EJEMPLOS_EN = "../ejemplos/";
const PYODIDE_EN = "../vendor/pyodide/";
async function buscarWheel() {{ return await fetch(DIST + "rueda.json"); }}
""".format(paquete.VERSION_DE_PYODIDE)

# El candado de Pyodide en pequeño. Dice cómo se llama el fichero de cada
# paquete, que es lo que evita escribir a mano unos nombres que llevan la
# versión dentro.
CANDADO = {
    "packages": {
        "lxml": {"file_name": "lxml-0.0.0.whl", "depends": ["micropip"]},
        "micropip": {"file_name": "micropip-0.0.0.whl", "depends": []},
    }
}

PAGINA = """<!doctype html><title>glosa</title>
<link rel="stylesheet" href="./glosa.css">
<script src="./glosa.js"></script>
"""

ESTILO = ('@font-face { src: url("./letra/literata.woff2?v=abc12345"); }\n'
          ":root { --papel: #fbfaf7; }\n")


@pytest.fixture
def repositorio(tmp_path):
    """Un repositorio en pequeño: la página, un wheel y unos ejemplos."""
    (tmp_path / "web").mkdir()
    (tmp_path / "web" / "index.html").write_text(PAGINA, encoding="utf-8")
    (tmp_path / "web" / "banco.html").write_text(PAGINA, encoding="utf-8")
    (tmp_path / "web" / "legal.html").write_text(PAGINA, encoding="utf-8")
    (tmp_path / "web" / "glosa.js").write_text(CARGADOR, encoding="utf-8")
    (tmp_path / "web" / "glosa.css").write_text(ESTILO, encoding="utf-8")
    (tmp_path / "web" / "prueba.py").write_text("# el banco\n", encoding="utf-8")
    (tmp_path / "web" / "LEEME.md").write_text("# la pagina\n", encoding="utf-8")
    # La letra y su licencia. Van juntas porque la OFL obliga a que la segunda
    # viaje con la primera, y el montaje lo comprueba.
    (tmp_path / "web" / "letra").mkdir()
    (tmp_path / "web" / "letra" / "literata.woff2").write_bytes(b"wOF2 de mentira")
    (tmp_path / "web" / "letra" / "OFL.txt").write_text("OFL 1.1\n", encoding="utf-8")
    (tmp_path / "dist").mkdir()
    _rueda_de_verdad(tmp_path / "dist" / "factura_e-0.1.0-py3-none-any.whl")
    (tmp_path / "ejemplos").mkdir()
    (tmp_path / "ejemplos" / "f-0001.xml").write_text("<a/>", encoding="utf-8")
    (tmp_path / "ejemplos" / "edi-0001.edi").write_text("UNA", encoding="utf-8")
    # El intérprete que se sirve con la página, en pequeño.
    py = tmp_path / "vendor" / "pyodide"
    py.mkdir(parents=True)
    (py / "pyodide-lock.json").write_text(json.dumps(CANDADO), encoding="utf-8")
    for nombre in ("pyodide.js", "pyodide.asm.mjs", "pyodide.asm.wasm",
                   "python_stdlib.zip", "lxml-0.0.0.whl", "micropip-0.0.0.whl"):
        (py / nombre).write_bytes(b"x")

    # Facturas de terceros, que no salen de aquí.
    (tmp_path / "muestras").mkdir()
    (tmp_path / "muestras" / "de-un-cliente.xml").write_text("<a/>", encoding="utf-8")
    return tmp_path


DIST_INFO = "factura_e-0.1.0.dist-info"


def _rueda_de_verdad(destino: Path, licencia: str | None = "la declarada",
                     con_texto: bool = True) -> None:
    """Un wheel con los módulos del paquete de verdad dentro.

    Antes bastaba con escribir `b"PK\x03\x04"` y llamarlo wheel, porque nadie
    miraba lo que llevaba. Desde que el montaje se niega a publicar un wheel
    que no sea el del código de ahora, hace falta uno de verdad: si no, la
    prueba de que un wheel bueno pasa no prueba nada.

    Y desde que el montaje también mira la licencia, hace falta el `dist-info`:
    un wheel sin él no anuncia ninguna, que es justo uno de los casos que hay
    que poder provocar. `licencia=None` lo deja fuera; `con_texto=False` anuncia
    la licencia sin adjuntar sus condiciones.
    """
    fuentes = Path(paquete.__file__).parent
    if licencia == "la declarada":
        licencia = paquete.licencia_declarada(fuentes.parent)
    with zipfile.ZipFile(destino, "w") as zip_de_la_rueda:
        for ruta in sorted(fuentes.glob("*.py")):
            zip_de_la_rueda.writestr(f"validador/{ruta.name}", ruta.read_bytes())
        if licencia is None:
            return
        zip_de_la_rueda.writestr(
            f"{DIST_INFO}/METADATA",
            "Metadata-Version: 2.4\nName: factura-e\nVersion: 0.1.0\n"
            f"License-Expression: {licencia}\n\nEl README iría aquí.\n")
        if con_texto:
            zip_de_la_rueda.writestr(f"{DIST_INFO}/licenses/LICENSE",
                                     "El texto de la licencia.\n")


def _tocar_la_rueda(destino: Path, quitar=(), cambiar=()) -> None:
    """Vuelve a escribir el wheel sin un módulo, o con uno cambiado."""
    with zipfile.ZipFile(destino) as vieja:
        dentro = {n: vieja.read(n) for n in vieja.namelist()}
    for nombre in quitar:
        dentro.pop(nombre, None)
    for nombre in cambiar:
        dentro[nombre] = dentro[nombre] + b"\n# de anteayer\n"
    with zipfile.ZipFile(destino, "w") as nueva:
        for nombre, crudo in dentro.items():
            nueva.writestr(nombre, crudo)


def _montar(repositorio, destino="sitio", exigir_paquete=False):
    return paquete.montar_sitio(
        repositorio / destino,
        pagina=repositorio / "web",
        ruedas=repositorio / "dist",
        ejemplos=repositorio / "ejemplos",
        pyodide=repositorio / "vendor" / "pyodide",
        exigir_paquete=exigir_paquete,
    )


class TestElSitioQueSePublica:
    """Lo que se sube es lo que se ha montado, no el repositorio."""

    def test_va_la_pagina_el_wheel_y_los_ejemplos(self, repositorio):
        sitio = _montar(repositorio)
        raiz = repositorio / "sitio"
        assert (raiz / "index.html").is_file()
        assert (raiz / "banco.html").is_file()
        assert (raiz / "legal.html").is_file()
        assert (raiz / "glosa.js").is_file()
        assert (raiz / "glosa.css").is_file()
        assert (raiz / "prueba.py").is_file()
        rueda, = (raiz / "dist").glob("*/factura_e-0.1.0-py3-none-any.whl")
        assert rueda.is_file()
        assert (raiz / "ejemplos" / "f-0001.xml").is_file()
        assert sitio.ejemplos == 2

    def test_el_wheel_se_anuncia_porque_no_hay_listado(self, repositorio):
        """Lo que hace publicable el sitio.

        Sirviendo la carpeta en desarrollo, la página encuentra el `.whl`
        leyendo el listado del directorio. Un sitio publicado no tiene
        listado: devuelve 404 y la página se queda sin validador después de
        bajarse catorce megas de Pyodide.
        """
        _montar(repositorio)
        anuncio = repositorio / "sitio" / "dist" / paquete.NOMBRE_DE_LA_RUEDA
        dicho = json.loads(anuncio.read_text(encoding="utf-8"))
        assert dicho["rueda"].endswith("/factura_e-0.1.0-py3-none-any.whl")
        assert (repositorio / "sitio" / "dist" / dicho["rueda"]).is_file()

    def test_las_rutas_dejan_de_apuntar_un_nivel_arriba(self, repositorio):
        """En el sitio publicado, encima de la raíz no hay nada."""
        _montar(repositorio)
        codigo = (repositorio / "sitio" / "glosa.js").read_text(encoding="utf-8")
        assert 'const DIST = "./dist/";' in codigo
        assert 'const EJEMPLOS_EN = "./ejemplos/";' in codigo
        assert "../" not in codigo

    def test_el_cargador_se_llama_con_su_huella(self, repositorio):
        """Para que la caché del navegador no sirva el de ayer.

        Es la tercera vez que este proyecto se tropieza con lo mismo. Nunca se
        rompe nada: sale todo bien y no es lo que crees que has probado.
        """
        _montar(repositorio)
        for nombre in ("index.html", "banco.html", "legal.html"):
            texto = (repositorio / "sitio" / nombre).read_text(encoding="utf-8")
            assert 'src="./glosa.js?v=' in texto, nombre
            assert 'src="./glosa.js"' not in texto, nombre
            assert 'href="./glosa.css?v=' in texto, nombre
            assert 'href="./glosa.css"' not in texto, nombre

    def test_la_huella_cambia_solo_si_cambia_el_cargador(self, repositorio):
        """Si cambiara en cada montado, la caché no serviría para nada."""
        _montar(repositorio)
        antes = (repositorio / "sitio" / "index.html").read_text(encoding="utf-8")
        _montar(repositorio)
        assert (repositorio / "sitio" / "index.html").read_text(encoding="utf-8") == antes
        (repositorio / "web" / "glosa.js").write_text(
            CARGADOR + "\n// una linea mas\n", encoding="utf-8"
        )
        _montar(repositorio)
        despues = (repositorio / "sitio" / "index.html").read_text(encoding="utf-8")
        assert despues != antes

    def test_si_la_llamada_al_cargador_cambia_se_para_aqui(self, repositorio):
        """Sin huella, la página publicada podría correr un cargador viejo."""
        (repositorio / "web" / "index.html").write_text(
            PAGINA.replace('<script src="./glosa.js"></script>',
                           '<script defer src="./glosa.js"></script>'),
            encoding="utf-8",
        )
        for otra in ("banco.html", "legal.html"):
            (repositorio / "web" / otra).write_text(
                PAGINA.replace('<script src="./glosa.js"></script>',
                               '<script defer src="./glosa.js"></script>'),
                encoding="utf-8",
            )
        with pytest.raises(paquete.SinPagina) as fallo:
            _montar(repositorio)
        assert "_LLAMADA_AL_CARGADOR" in str(fallo.value)

    def test_el_estilo_tambien_se_firma_por_separado(self, repositorio):
        """Tocar solo los colores tiene que cambiar solo la dirección del CSS."""
        _montar(repositorio)
        antes = (repositorio / "sitio" / "index.html").read_text(encoding="utf-8")
        (repositorio / "web" / "glosa.css").write_text(
            ESTILO + "body { margin: 0; }\n", encoding="utf-8"
        )
        _montar(repositorio)
        despues = (repositorio / "sitio" / "index.html").read_text(encoding="utf-8")
        assert despues != antes
        saca = lambda t, q: t.split(q)[1].split('"')[0]
        assert saca(antes, 'glosa.js?v=') == saca(despues, 'glosa.js?v=')
        assert saca(antes, 'glosa.css?v=') != saca(despues, 'glosa.css?v=')

    def test_el_interprete_viaja_con_el_sitio(self, repositorio):
        """Para que el navegador de quien visita no hable con un CDN ajeno."""
        _montar(repositorio)
        dentro = (repositorio / "sitio" / "pyodide"
                  / paquete.VERSION_DE_PYODIDE)
        assert (dentro / "pyodide.js").is_file()
        assert (dentro / "pyodide.asm.wasm").is_file()
        # Los de los paquetes salen del candado, no de una lista escrita a mano.
        assert (dentro / "lxml-0.0.0.whl").is_file()
        assert (dentro / "micropip-0.0.0.whl").is_file()

    def test_el_interprete_va_bajo_su_version(self, repositorio):
        """Lo que hace honesto el «guárdalo un año».

        Estos siete ficheros se sirven con permiso para quedarse un año en la
        caché de quien pase. Eso solo se puede prometer si al subir de versión
        cambia la dirección: con `/pyodide/` a secas, el día que se cambiara de
        intérprete habría gente corriendo el viejo durante un año y ninguna
        forma de avisarles.
        """
        _montar(repositorio)
        raiz = repositorio / "sitio" / "pyodide"
        assert [c.name for c in raiz.iterdir()] == [paquete.VERSION_DE_PYODIDE]
        codigo = (repositorio / "sitio" / "glosa.js").read_text(encoding="utf-8")
        assert f'const PYODIDE_EN = "./pyodide/{paquete.VERSION_DE_PYODIDE}/";' \
            in codigo

    def test_si_las_dos_versiones_no_dicen_lo_mismo_se_para_aqui(
        self, repositorio
    ):
        """Publicar una versión bajo el nombre de otra dura un año."""
        cargador = repositorio / "web" / "glosa.js"
        cargador.write_text(
            CARGADOR.replace(paquete.VERSION_DE_PYODIDE, "0.0.0"),
            encoding="utf-8",
        )
        with pytest.raises(paquete.SinPagina) as fallo:
            _montar(repositorio)
        assert "VERSION_PYODIDE" in str(fallo.value)

    def test_la_pagina_deja_de_apuntar_al_cdn(self, repositorio):
        _montar(repositorio)
        codigo = (repositorio / "sitio" / "glosa.js").read_text(encoding="utf-8")
        assert 'const PYODIDE_EN = "./pyodide/' in codigo
        assert "jsdelivr" not in codigo

    def test_el_manifiesto_firma_todo_lo_que_la_pagina_se_baja(
        self, repositorio
    ):
        """Lo que permite que la caché del navegador sirva de algo.

        Antes cada uno de estos ficheros se pedía con `?v=` y la hora dentro,
        para que el navegador no sirviera el wheel de ayer. Cumplía, y el
        precio era que la dirección cambiaba en cada visita: el paquete, el
        wheel y los ejemplos —1,2 MB— **no se podían guardar nunca** y se
        bajaban enteros cada vez que alguien abría la página.
        """
        (repositorio / "web" / paquete.NOMBRE).write_bytes(b"PK\x03\x04")
        (repositorio / "web" / paquete.MANIFIESTO).write_text(
            "{}", encoding="utf-8")
        _montar(repositorio)
        anuncio = repositorio / "sitio" / "dist" / paquete.NOMBRE_DE_LA_RUEDA
        huellas = json.loads(anuncio.read_text(encoding="utf-8"))["huellas"]
        for pedido in ("paquete.zip", "PAQUETE.json", "prueba.py",
                       "glosa.js", "glosa.css", "ejemplos/f-0001.xml"):
            assert pedido in huellas, pedido
            assert len(huellas[pedido]) == 8

        # El propio manifiesto no se firma: es lo único que se pide siempre
        # fresco, porque de él salen las demás huellas.
        assert f"dist/{paquete.NOMBRE_DE_LA_RUEDA}" not in huellas

    def test_el_wheel_va_bajo_una_carpeta_con_su_huella(self, repositorio):
        """La huella del wheel va en la ruta, y no detrás con `?v=`.

        Quien lo instala es `loadPackage`, que saca el nombre y la versión del
        nombre del fichero con `/^.*?([^/]*)\\.whl$/`. Con una query detrás lo
        rechaza en la cara: «is not a valid package name or URL». Está
        comprobado contra el sitio publicado, no deducido.

        Con la huella en la carpeta se consiguen las dos cosas que hacían falta:
        la dirección cambia cuando el wheel cambia —que es lo que impide correr
        el validador de ayer— y acaba en `.whl`, así que `loadPackage` la toma.
        """
        _montar(repositorio)
        anuncio = repositorio / "sitio" / "dist" / paquete.NOMBRE_DE_LA_RUEDA
        dicho = json.loads(anuncio.read_text(encoding="utf-8"))["rueda"]

        carpeta, nombre = dicho.split("/")
        assert len(carpeta) == 8
        assert nombre.endswith(".whl")
        # Lo que anuncia es lo que hay, y la carpeta es de verdad su huella.
        montado = repositorio / "sitio" / "dist" / dicho
        assert montado.is_file()
        import hashlib
        assert hashlib.sha256(montado.read_bytes()).hexdigest()[:8] == carpeta

        # Y la página la pide tal cual, sin añadirle nada detrás.
        codigo = (repositorio / "sitio" / "glosa.js").read_text(encoding="utf-8")
        assert "conHuella(DIST + rueda" not in codigo

    def test_micropip_ya_no_viaja(self, repositorio):
        """Estaba solo para instalar un wheel que no tiene dependencias.

        `loadPackage` acepta la dirección de un `.whl`, así que micropip era un
        paso de resolución que no resolvía nada y 115 KB en cada primera
        visita. lxml no depende de él: mirado en el candado que se ha bajado, no
        supuesto. Lo que se comprueba aquí es lo que depende del código —que ya
        no se pide ni se importa—; que el fichero no viaje depende además del
        candado, y si algún día lxml pasara a depender de micropip volvería a
        viajar, que es justo lo que debe pasar.
        """
        assert "micropip" not in paquete._PAQUETES_DE_PYODIDE
        _montar(repositorio)
        codigo = (repositorio / "sitio" / "glosa.js").read_text(encoding="utf-8")
        assert "micropip" not in codigo.split("// Aqui habia tres pasos")[0]

    def test_la_huella_del_paquete_cambia_solo_si_cambia_el_paquete(
        self, repositorio
    ):
        """Si cambiara en cada montado no habría caché que valiera."""
        (repositorio / "web" / paquete.NOMBRE).write_bytes(b"PK\x03\x04")
        (repositorio / "web" / paquete.MANIFIESTO).write_text(
            "{}", encoding="utf-8")
        _montar(repositorio)
        anuncio = repositorio / "sitio" / "dist" / paquete.NOMBRE_DE_LA_RUEDA

        def huella(cual):
            return json.loads(anuncio.read_text(encoding="utf-8"))["huellas"][cual]

        antes = huella("paquete.zip")
        _montar(repositorio)
        assert huella("paquete.zip") == antes

        (repositorio / "web" / paquete.NOMBRE).write_bytes(b"otro zip cualquiera")
        _montar(repositorio)
        assert huella("paquete.zip") != antes

    def test_sin_interprete_no_se_monta(self, repositorio):
        """La negativa que sostiene la política de privacidad.

        Sin esto, un despiste publicaría una página que vuelve al CDN con un
        documento al lado diciendo que no lo hace. Que falle al montar es la
        única forma de que eso no dependa de acordarse.
        """
        (repositorio / "vendor" / "pyodide" / "pyodide.asm.wasm").unlink()
        with pytest.raises(paquete.SinPyodide) as fallo:
            _montar(repositorio)
        assert "--traer-pyodide" in str(fallo.value)

    def test_sin_carpeta_de_interprete_se_dice_como_traerlo(self, repositorio):
        import shutil as _sh

        _sh.rmtree(repositorio / "vendor" / "pyodide")
        with pytest.raises(paquete.SinPyodide) as fallo:
            _montar(repositorio)
        assert "--traer-pyodide" in str(fallo.value)

    def test_sin_estilo_no_se_monta(self, repositorio):
        """Sin los colores, las tres páginas salen en blanco y negro del navegador."""
        (repositorio / "web" / "glosa.css").unlink()
        with pytest.raises(paquete.SinPagina) as fallo:
            _montar(repositorio)
        assert "glosa.css" in str(fallo.value)

    def test_sin_cargador_no_se_monta(self, repositorio):
        """Las dos páginas lo cargan; sin él arrancan y se quedan a medias."""
        (repositorio / "web" / "glosa.js").unlink()
        with pytest.raises(paquete.SinPagina) as fallo:
            _montar(repositorio)
        assert "glosa.js" in str(fallo.value)

    def test_las_facturas_de_terceros_no_se_publican(self, repositorio):
        """La razón de montar el sitio en vez de subir el repositorio."""
        _montar(repositorio)
        salidos = {f.name for f in (repositorio / "sitio").rglob("*") if f.is_file()}
        assert "de-un-cliente.xml" not in salidos

    def test_sin_wheel_no_se_monta_y_se_dice_como(self, repositorio):
        (repositorio / "dist" / "factura_e-0.1.0-py3-none-any.whl").unlink()
        with pytest.raises(paquete.SinRueda) as fallo:
            _montar(repositorio)
        assert "python -m build" in str(fallo.value)

    def test_la_letra_y_su_licencia_viajan(self, repositorio):
        """La marca es Literata trazada; sin el fichero, el texto de al lado se
        componía con la serif del sistema —Georgia en Windows— y la cabecera
        salía con dos letras distintas a dos centímetros."""
        _montar(repositorio)
        raiz = repositorio / "sitio"
        assert (raiz / "letra" / "literata.woff2").is_file()
        assert (raiz / "letra" / "OFL.txt").is_file(), (
            "la OFL exige que la licencia viaje con la fuente")

    def test_sin_la_letra_no_se_monta(self, repositorio):
        """De los fallos que no dan error: un `@font-face` que apunta a lo que
        no está compone con la del sistema y la página parece correcta."""
        (repositorio / "web" / "letra" / "literata.woff2").unlink()
        with pytest.raises(paquete.SinPagina) as fallo:
            _montar(repositorio)
        assert "no da error" in str(fallo.value)
        assert "web/marca/letra.py" in str(fallo.value)

    def test_sin_la_licencia_tampoco(self, repositorio):
        """Publicar la fuente sin su licencia incumple la unica condicion que
        la OFL pone, y es la clase de cosa que nadie mira hasta que alguien
        pregunta."""
        (repositorio / "web" / "letra" / "OFL.txt").unlink()
        with pytest.raises(paquete.SinPagina) as fallo:
            _montar(repositorio)
        assert "OFL" in str(fallo.value)

    def test_una_pagina_que_no_pida_letra_se_monta_igual(self, repositorio):
        """La negativa mira el CSS, no la carpeta: si nadie pide la letra, no
        hay nada que echar en falta."""
        (repositorio / "web" / "glosa.css").write_text(
            ":root { --papel: #fbfaf7; }\n", encoding="utf-8")
        (repositorio / "web" / "letra" / "literata.woff2").unlink()
        (repositorio / "web" / "letra" / "OFL.txt").unlink()
        assert _montar(repositorio).carpeta.is_dir()

    def test_un_wheel_de_anteayer_no_se_monta(self, repositorio):
        """Salió montando el sitio de verdad, no leyendo el código.

        `--sitio` no construye el wheel: coge el que haya en `dist/`. El que
        había era de tres días antes de que existiera `ocsp.py`, y el montaje
        dijo «Montado sitio (15.79 MB)» en verde. La página habría arrancado,
        bajado catorce megas de intérprete y reventado al importar un
        `revocacion.py` que hace `from validador import ocsp`.
        """
        rueda = repositorio / "dist" / "factura_e-0.1.0-py3-none-any.whl"
        _tocar_la_rueda(rueda, quitar=["validador/ocsp.py"])
        with pytest.raises(paquete.RuedaVieja) as fallo:
            _montar(repositorio)
        assert "ocsp.py (no viaja en el wheel)" in str(fallo.value)
        assert "python -m build" in str(fallo.value)

    def test_y_tampoco_con_un_modulo_que_esta_pero_es_otro(self, repositorio):
        """Lo que una lista de módulos escrita a mano no cazaría: el fichero
        está, y no es el que se va a ejecutar. Por eso se comparan los bytes."""
        rueda = repositorio / "dist" / "factura_e-0.1.0-py3-none-any.whl"
        _tocar_la_rueda(rueda, cambiar=["validador/revocacion.py"])
        with pytest.raises(paquete.RuedaVieja) as fallo:
            _montar(repositorio)
        assert "revocacion.py (el del wheel es otro)" in str(fallo.value)

    def test_un_wheel_con_la_licencia_de_antes_no_se_monta(self, repositorio):
        """El caso que la comparación de módulos no caza, y el que más duele.

        Cambiar de licencia es tocar `pyproject.toml`, y `pyproject.toml` no
        viaja dentro del wheel. Los veinticuatro módulos siguen siendo idénticos
        byte a byte, así que sin esto el montaje daba el visto bueno y la página
        repartía a cada visitante un motor que se anuncia con la licencia
        anterior —la que ya no rige— sin que se notara en ninguna pantalla.
        """
        rueda = repositorio / "dist" / "factura_e-0.1.0-py3-none-any.whl"
        _rueda_de_verdad(rueda, licencia="MIT")
        with pytest.raises(paquete.RuedaVieja) as fallo:
            _montar(repositorio)
        assert "la licencia" in str(fallo.value)
        assert "MIT" in str(fallo.value)

    def test_un_wheel_que_no_dice_ninguna_licencia_tampoco(self, repositorio):
        """No decir nada no es lo mismo que decir lo de hoy, y aquí no cuela."""
        rueda = repositorio / "dist" / "factura_e-0.1.0-py3-none-any.whl"
        _rueda_de_verdad(rueda, licencia=None)
        with pytest.raises(paquete.RuedaVieja) as fallo:
            _montar(repositorio)
        assert "no dice ninguna" in str(fallo.value)

    def test_un_wheel_que_anuncia_la_licencia_y_no_la_lleva_dentro_tampoco(
            self, repositorio):
        """Anunciar unas condiciones sin entregarlas es no haberlas puesto.

        Es lo que saldría el día que alguien renombre `LICENSE` o quite
        `license-files` del `pyproject.toml`: la etiqueta sigue en su sitio y el
        texto deja de viajar, en silencio.
        """
        rueda = repositorio / "dist" / "factura_e-0.1.0-py3-none-any.whl"
        _rueda_de_verdad(rueda, con_texto=False)
        with pytest.raises(paquete.RuedaVieja) as fallo:
            _montar(repositorio)
        assert "no lleva el texto dentro" in str(fallo.value)

    def test_un_wheel_que_ni_se_abre_lo_dice_con_esas_palabras(self, repositorio):
        """Y no como un `BadZipFile` a media función, que no se parece en nada
        a su causa."""
        rueda = repositorio / "dist" / "factura_e-0.1.0-py3-none-any.whl"
        rueda.write_bytes(b"PK\x03\x04 y nada mas")
        with pytest.raises(paquete.RuedaVieja) as fallo:
            _montar(repositorio)
        assert "no se puede abrir el wheel" in str(fallo.value)

    def test_si_la_pagina_cambia_de_rutas_se_para_aqui(self, repositorio):
        """Y no en el navegador de un desconocido.

        La sustitución busca una línea concreta. El día que alguien la
        renombre, lo que no puede pasar es que el sitio se suba igual y pida
        sus ficheros por encima de su propia raíz.
        """
        cargador = repositorio / "web" / "glosa.js"
        cargador.write_text(
            CARGADOR.replace('const DIST = "../dist/";', 'const RUEDAS = "../dist/";'),
            encoding="utf-8",
        )
        with pytest.raises(paquete.SinPagina) as fallo:
            _montar(repositorio)
        assert "_RUTAS_DEL_SITIO" in str(fallo.value)

    def test_sin_paquete_se_monta_igual_pero_se_cuenta(self, repositorio):
        """La página ya sabe decir qué deja de comprobar; el que publica, no."""
        sitio = _montar(repositorio)
        assert sitio.con_paquete is False
        assert not (repositorio / "sitio" / paquete.NOMBRE).exists()

    def test_con_paquete_viajan_el_zip_y_su_resumen(self, repositorio):
        (repositorio / "web" / paquete.NOMBRE).write_bytes(b"PK\x03\x04")
        (repositorio / "web" / paquete.MANIFIESTO).write_text("{}", encoding="utf-8")
        sitio = _montar(repositorio)
        assert sitio.con_paquete is True
        assert (repositorio / "sitio" / paquete.NOMBRE).is_file()
        assert (repositorio / "sitio" / paquete.MANIFIESTO).is_file()

    def test_montar_dos_veces_no_deja_restos(self, repositorio):
        """Un wheel viejo que sobreviva al remontado es el fallo de siempre."""
        _montar(repositorio)
        viejo = repositorio / "sitio" / "dist" / "factura_e-0.0.9-py3-none-any.whl"
        viejo.write_bytes(b"PK\x03\x04")
        _montar(repositorio)
        assert not viejo.exists()


# --- El par versionado, comprobado contra sí mismo -------------------------


class TestElParQueSeVersiona:
    """`web/paquete.zip` y `web/PAQUETE.json`, la excepción decidida a propósito.

    Todo el material de confianza está fuera del control de versiones porque
    caduca, y repartir una foto vieja es peor que no repartir nada. Estos dos
    son la excepción: van dentro para que el sitio se pueda construir sin
    tener las carpetas fuente, **con su SHA-256 publicado al lado**.

    Ese «al lado» no lo comprobaba nadie. La huella se escribía al montar el
    paquete y a partir de ahí eran dos ficheros sueltos en un commit: bastaba
    con volver a montar uno y no el otro —o con que un `git add` se dejara uno
    fuera— para publicar un zip que no es el que su ficha dice, y descomprimir
    un zip **no falla**. La página se quedaría con menos anclas de las que
    afirma traer, que son aprobados de más repartidos en silencio.

    Desde el 06-09-2026 lo comprueba también el navegador, antes de
    descomprimir (`glosa.js`, `huellaDe`). Aquí se comprueba antes de publicar,
    que es más barato.
    """

    ZIP = Path(__file__).resolve().parent.parent / "web" / paquete.NOMBRE
    FICHA = Path(__file__).resolve().parent.parent / "web" / paquete.MANIFIESTO

    def _ficha(self) -> dict:
        if not self.ZIP.is_file() or not self.FICHA.is_file():
            pytest.skip("este clon no trae el paquete montado")
        return json.loads(self.FICHA.read_text(encoding="utf-8"))

    def test_el_zip_resume_lo_que_su_ficha_publica(self):
        import hashlib

        ficha = self._ficha()
        medida = hashlib.sha256(self.ZIP.read_bytes()).hexdigest()
        assert medida == ficha["huella"], (
            f"`{paquete.NOMBRE}` resume {medida[:12]}… y `{paquete.MANIFIESTO}` "
            f"publica {str(ficha['huella'])[:12]}…. Son dos ficheros que se "
            "versionan juntos y uno de los dos se ha quedado atrás: vuelve a "
            "montar el paquete, o no publiques la ficha de otro."
        )

    def test_y_tambien_el_tamano(self):
        """Redundante con la huella, y hace falta igual.

        Es lo único que se puede comprobar cuando no hay `crypto.subtle` —o
        sea, sirviendo esto por http en una red local—, así que si el tamaño
        publicado fuera mentira, allí no quedaría ninguna comprobación.
        """
        ficha = self._ficha()
        assert self.ZIP.stat().st_size == ficha["bytes"]

    def test_la_ficha_dice_lo_que_hay_dentro_del_zip(self):
        """Las tres cifras que la página enseña sin abrir el paquete."""
        ficha = self._ficha()
        with zipfile.ZipFile(self.ZIP) as z:
            nombres = z.namelist()
        cuenta = {
            "esquemas": sum(1 for n in nombres if n.startswith("esquemas/")
                            and n.endswith(".xsd")),
            "anclas": sum(1 for n in nombres if n.startswith("anclas/")
                          and n.endswith(".cer")),
            "anclas_de_sellos": sum(1 for n in nombres
                                    if n.startswith("anclas-sellos/")
                                    and n.endswith(".cer")),
        }
        malas = {k: (ficha[k], v) for k, v in cuenta.items() if ficha[k] != v}
        assert not malas, (
            f"la ficha publica una cosa y el zip trae otra: {malas} "
            "(publicado, dentro). Esas cifras salen en el informe de cada "
            "factura, al lado de la frase que dice de dónde vienen las anclas."
        )


class TestExigirElPaquete:
    """`--exigir-paquete`: la diferencia entre avisar y no dejar.

    Montar sin el paquete de esquemas y anclas sigue estando permitido y sigue
    saliendo con 0: hace falta para probar en local sin tener que armar 389
    anclas, y la página ya cuenta en su recuadro qué deja de comprobar.

    Lo que no funciona es avisar cuando quien monta no es una persona. La
    construcción de Vercel corre `--sitio` y lo único que mira es el código de
    salida, así que un aviso perfecto por pantalla y un `return 0` publican
    igual un sitio que no comprueba ni la forma ni de quién es la firma. El
    despliegue pasa la bandera, y entonces esto se niega antes de escribir
    nada.
    """

    def test_sin_bandera_se_monta_igual_y_se_cuenta(self, repositorio):
        """El comportamiento de siempre, que no cambia."""
        sitio = _montar(repositorio)
        assert sitio.con_paquete is False

    def test_con_bandera_y_sin_paquete_no_se_monta(self, repositorio):
        with pytest.raises(paquete.SinPaquete) as fallo:
            _montar(repositorio, exigir_paquete=True)
        assert "paquete.zip" in str(fallo.value)

    def test_y_no_deja_media_carpeta_escrita(self, repositorio):
        """Se niega antes de tocar nada.

        Montar medio sitio y fallar después deja una carpeta a medias que el
        paso siguiente podría publicar igual, y entonces la negativa no sirve
        de nada.
        """
        with pytest.raises(paquete.SinPaquete):
            _montar(repositorio, exigir_paquete=True)
        assert not (repositorio / "sitio").exists()

    def test_con_el_paquete_puesto_se_monta(self, repositorio):
        (repositorio / "web" / paquete.NOMBRE).write_bytes(b"PK\x03\x04")
        (repositorio / "web" / paquete.MANIFIESTO).write_text(
            json.dumps({"esquemas": 24, "anclas": 268, "anclas_de_sellos": 121}),
            encoding="utf-8")
        sitio = _montar(repositorio, exigir_paquete=True)
        assert sitio.con_paquete is True

    def test_un_paquete_sin_anclas_tampoco_vale(self, repositorio):
        """Que el fichero exista no dice nada de lo que trae dentro.

        Un zip armado sin anclas se copia, se sirve y se descomprime sin error,
        y deja al validador sin comprobar de quién es la firma mientras la
        ficha de la página anuncia unas cifras que no están.
        """
        (repositorio / "web" / paquete.NOMBRE).write_bytes(b"PK\x03\x04")
        (repositorio / "web" / paquete.MANIFIESTO).write_text(
            json.dumps({"esquemas": 24, "anclas": 0, "anclas_de_sellos": 0}),
            encoding="utf-8")
        with pytest.raises(paquete.SinPaquete) as fallo:
            _montar(repositorio, exigir_paquete=True)
        assert "anclas de firma" in str(fallo.value)
        assert "anclas de sellado" in str(fallo.value)

    def test_una_ficha_ilegible_no_se_da_por_buena(self, repositorio):
        (repositorio / "web" / paquete.NOMBRE).write_bytes(b"PK\x03\x04")
        (repositorio / "web" / paquete.MANIFIESTO).write_text(
            "{esto no es JSON", encoding="utf-8")
        with pytest.raises(paquete.SinPaquete):
            _montar(repositorio, exigir_paquete=True)


class TestElDespliegueExigeElPaquete:
    """La bandera existe y el despliegue no la usa: eso ya ha pasado aquí.

    El gancho de `antes-de-empujar.py` estuvo meses escrito y sin declarar en
    los ajustes, y no fallaba: dejaba pasar. Una bandera que nadie pasa es
    exactamente lo mismo.
    """

    VERCEL = Path(__file__).resolve().parent.parent / "vercel.json"

    def test_la_orden_de_construccion_la_pasa(self):
        orden = json.loads(self.VERCEL.read_text(encoding="utf-8"))["buildCommand"]
        assert "--sitio" in orden, "la construcción ya no monta el sitio"
        assert "--exigir-paquete" in orden, (
            "`vercel.json` monta el sitio sin `--exigir-paquete`. Sin esa "
            "bandera, un despliegue al que le falte el paquete publica un "
            "validador que no comprueba ni la forma ni de quién es la firma, "
            "y sale con 0 igual que si estuviera entero."
        )

    def test_la_bandera_existe_de_verdad_en_la_orden(self, capsys):
        """Que no se haya renombrado por un lado y no por el otro.

        Se mira en la ayuda y no llamando a `--sitio`: montar un sitio de
        verdad desde una prueba escribiría una carpeta dentro del repositorio,
        y una prueba que deja restos es una prueba que un día tapa algo.
        """
        from validador import __main__

        with pytest.raises(SystemExit):
            __main__.main(["--help"])
        assert "--exigir-paquete" in capsys.readouterr().out, (
            "`vercel.json` pasa `--exigir-paquete` y la orden no la reconoce: "
            "la construcción fallaría entera con «unrecognized arguments»")

