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

import hashlib
import json
import re
import zipfile
from datetime import date
from pathlib import Path

import pytest

from validador import bitacora, cadena, paquete
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
    def test_el_informe_dice_lo_que_ha_mirado_con_el_paquete(self, tmp_path):
        """El resumen del final cambia según lo que de verdad se ha mirado.

        Es la razón de ser de todo esto: sin el paquete, la página comprueba
        el contenido y su propia frase final lo dice. Con él, dice la forma, y
        de la cadena dice lo que ha pasado.

        Se llamaba «promete las tres cosas» y pedía «autoridad de confianza
        instalada» sobre el ejemplo firmado, cuya cadena no llega a ninguna de
        las anclas del paquete: pedía la promesa que el punto 8 de la auditoría
        del 15-09-2026 encontró falsa.
        """
        from validador import factura

        suelto = self.armado(tmp_path)
        con = factura.validar_lote(
            [EJEMPLO],
            catalogo=Catalogo(suelto / "esquemas"),
            almacen=Almacen(suelto / "anclas"),
        ).alcance(forma=True, anclas=True)
        assert "esquema XSD" in con
        assert "sin anclas de confianza no se sabe" not in con
        assert "lleve a un ancla de confianza" not in con
        assert "de quién es el certificado de este documento" in con


# --- El sitio que se publica -----------------------------------------------

# El cargador tal como está en el repositorio, reducido a las dos líneas que
# importan aquí. Son las que dicen dónde busca el wheel y los ejemplos, y las
# comparten las dos páginas.
CARGADOR = """const VERSION_PYODIDE = "{}";
const TITULAR = {{ nombre: "Glosa-e", correo: "contacto@glosa-e.com" }};
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

# La página en pequeño, pero con cabecera de verdad: desde que el montaje le
# pone a cada una su canónica y su tarjeta social, una sin `<head>`, sin
# `<title>` o sin descripción **no se publica**, y con razón. Una plantilla de
# prueba sin nada de eso probaba un montaje que ya no existe.
# Lleva los tres enlaces que hay que distinguir: uno que se va del sitio, uno
# de casa y uno que ya trae `rel`. Sin ellos, la prueba de que los de fuera se
# abren aparte no probaría nada.
PAGINA = """<!doctype html>
<head><meta charset="utf-8">
<title>glosa</title>
<meta name="description" content="La de prueba.">
<link rel="stylesheet" href="./glosa.css">
<script src="./glosa.js"></script>
</head><body>
<a href="https://www.boe.es/uno">el BOE</a>
<a href="./legal.html">de casa</a>
<a href="https://aidoks.eu/dos" rel="nofollow">con rel</a>
</body>
"""

ESTILO = ('@font-face { src: url("./letra/literata.woff2?v=abc12345"); }\n'
          ":root { --papel: #fbfaf7; }\n")


def _apuntar_huellas(carpeta):
    """`HUELLAS.txt` de una carpeta de intérprete, como lo deja traerlo."""
    lineas = [f"# de mentira, para las pruebas", ""]
    for fichero in sorted(carpeta.glob("*")):
        if fichero.is_file() and fichero.name != paquete.NOMBRE_DE_HUELLAS:
            huella = hashlib.sha256(fichero.read_bytes()).hexdigest()
            lineas.append(f"{huella}  {fichero.name}")
    (carpeta / paquete.NOMBRE_DE_HUELLAS).write_text(
        "\n".join(lineas) + "\n", encoding="utf-8")


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
    # La tarjeta social. Va con negativa en el montaje, así que sin ella aquí
    # no se monta nada: es un PNG de mentira, que para esto vale.
    (tmp_path / "web" / "marca").mkdir()
    (tmp_path / "web" / "marca" / "tarjeta.png").write_bytes(
        bytes([137, 80, 78, 71, 13, 10, 26, 10])
    )
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
    # Y su recibo, que es lo que `--sitio` mira para saber si algo se ha
    # estropeado después de traerlo. Lo escribe `--traer-pyodide` de verdad;
    # aquí se escribe a mano porque este intérprete de mentira no se baja.
    _apuntar_huellas(py)

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
            # Entera, desde el 20-09-2026. Para que la dirección cambie cuando
            # el fichero cambia bastan ocho caracteres, y son los ocho que la
            # página sigue poniendo en el `?v=`; lo que no se puede hacer con
            # ocho es **comparar** lo que llega, que es lo que la página hace
            # ahora con el wheel, el fichero del banco y los ejemplos.
            assert len(huellas[pedido]) == 64, pedido
            assert huellas[pedido] == hashlib.sha256(
                (repositorio / "sitio" / pedido).read_bytes()).hexdigest()

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

    def test_cada_pagina_lleva_la_politica_antes_que_nada(self, repositorio):
        _montar(repositorio)
        for ruta in (repositorio / "sitio").glob("*.html"):
            texto = ruta.read_text(encoding="utf-8")
            assert texto.count("Content-Security-Policy") == 1, ruta.name
            cabeza = texto[texto.index('<meta charset="utf-8">'):]
            siguiente = cabeza.split("\n", 2)[1]
            assert siguiente.startswith('<meta http-equiv="Content-Security-Policy"'), (
                f"en «{ruta.name}» la política no va justo detrás del charset, y "
                "lo que se cargue antes que ella no la obedece")
            assert "connect-src 'self'" in texto and "default-src 'none'" in texto

    def test_la_politica_autoriza_cada_script_en_linea_por_su_huella(self, repositorio):
        """Y la huella es la del texto con LF, que es como lo lee el navegador.

        Una página escrita en Windows lleva CRLF; si la huella se calculara
        sobre esos bytes no coincidiría con ninguna, y la página se quedaría
        sin su script sin un solo error a la vista del que monta.
        """
        import base64
        import hashlib

        con_script = PAGINA.replace("</head>", "<script>\r\nuno();\r\ndos();\r\n</script>\n</head>")
        (repositorio / "web" / "index.html").write_bytes(con_script.encode("utf-8"))
        _montar(repositorio)
        texto = (repositorio / "sitio" / "index.html").read_text(encoding="utf-8")
        esperada = base64.b64encode(
            hashlib.sha256("\nuno();\ndos();\n".encode("utf-8")).digest()).decode()
        assert f"'sha256-{esperada}'" in texto

    def test_la_huella_no_depende_de_como_se_escribio_el_fichero(self):
        import base64
        import hashlib

        esperada = base64.b64encode(hashlib.sha256(b"uno();\ndos();").digest()).decode()
        for fin in ("\n", "\r\n", "\r"):
            politica = paquete.politica_de_contenido(f"<script>uno();{fin}dos();</script>")
            assert f"'sha256-{esperada}'" in politica, repr(fin)

    @pytest.mark.parametrize("trozo", [
        '<button onclick="hacer()">hacer</button>',
        '<a href="javascript:hacer()">hacer</a>',
        '<script type="module">hacer();</script>',
    ], ids=["manejador", "javascript", "script-con-atributos"])
    def test_lo_que_la_politica_bloquearia_en_silencio_no_se_monta(self, repositorio, trozo):
        (repositorio / "web" / "banco.html").write_text(
            PAGINA.replace("</body>", trozo + "\n</body>"), encoding="utf-8")
        with pytest.raises(paquete.SinPolitica):
            _montar(repositorio)

    def test_sin_charset_no_hay_donde_ponerla_y_no_se_monta(self, repositorio):
        (repositorio / "web" / "legal.html").write_text(
            PAGINA.replace('<meta charset="utf-8">', ""), encoding="utf-8")
        with pytest.raises(paquete.SinPolitica, match="charset"):
            _montar(repositorio)

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



class TestLaBitacoraSeComprueba:
    """Una entrada rota no deja montar, y no deja media carpeta detrás.

    La primera versión generaba la bitácora al final, que es donde tiene
    sentido escribirla, y **la comprobaba también al final**. La negativa salía
    perfecta y el sitio quedaba a medio montar: carpeta creada, páginas
    copiadas, wheel dentro. Una carpeta a medias con salida 2 es peor que un
    fallo limpio, porque el paso siguiente de una construcción la publica sin
    enterarse —que es el fallo que este repositorio ya tuvo con `--sitio` y el
    paquete de anclas—. Ahora las entradas se leen antes de tocar nada.
    """

    def _con_bitacora(self, repositorio, articulo: str):
        # Con `<head>`, `<title>` y descripción: el montaje le pone a cada
        # página su canónica y su tarjeta, y se niega con la que no los tenga.
        (repositorio / "web" / bitacora.NOMBRE).write_text(
            '<html><head><meta charset="utf-8"><title>bitacora</title>'
            '<meta name="description" content="La de prueba.">'
            "</head><body>" + bitacora.HUECO + "</body></html>",
            encoding="utf-8")
        carpeta = repositorio / "web" / bitacora.CARPETA
        carpeta.mkdir(exist_ok=True)
        (carpeta / "una.html").write_text(articulo, encoding="utf-8")

    BUENA = ('<article class="entrada" data-fecha="2026-09-07" '
             'data-titulo="Un titulo" data-entradilla="Una entradilla.">'
             '<p>Cuerpo.</p><footer class="fuentes"><ul><li>'
             '<a href="https://www.boe.es/">BOE</a></li></ul></footer></article>')

    def test_con_una_entrada_completa_se_monta(self, repositorio):
        self._con_bitacora(repositorio, self.BUENA)
        _montar(repositorio)
        assert (repositorio / "sitio" / bitacora.NOMBRE).is_file()
        assert (repositorio / "sitio" / f"{bitacora.PREFIJO}una.html").is_file()

    def test_sin_fecha_no_se_monta_ni_se_escribe_una_carpeta(self, repositorio):
        self._con_bitacora(repositorio, self.BUENA.replace(
            ' data-fecha="2026-09-07"', ""))
        with pytest.raises(bitacora.SinEntrada, match="de cuándo es"):
            _montar(repositorio)
        assert not (repositorio / "sitio").exists(), (
            "se ha negado a montar, pero ha dejado la carpeta del sitio "
            "escrita a medias")

    def test_sin_fuentes_no_se_monta_ni_se_escribe_una_carpeta(self, repositorio):
        self._con_bitacora(repositorio, self.BUENA.replace(
            '<footer class="fuentes"><ul><li>'
            '<a href="https://www.boe.es/">BOE</a></li></ul></footer>', ""))
        with pytest.raises(bitacora.SinEntrada, match="fuentes"):
            _montar(repositorio)
        assert not (repositorio / "sitio").exists()


class TestQueDosVueltasDenElMismoFichero:
    """El SHA-256 publicado tiene que poder comprobarlo alguien de fuera.

    El README ofrece esa huella para contrastar las anclas que se reparten con
    la página. Eso solo tiene sentido si quien arme el paquete de las mismas
    carpetas obtiene **el mismo fichero**; si no, la huella dice que la
    descarga llegó entera y nada más, que es bastante menos de lo que está
    escrito.

    No lo daba. `writestr` con un nombre a secas le pone a la entrada la hora
    del reloj, así que dos vueltas separadas por un minuto salían con huellas
    distintas. Medido: de 436 entradas, las 436 con el contenido idéntico y
    una sola con la fecha cambiada, la del `PAQUETE.json` de dentro.
    """

    def test_armar_dos_veces_da_los_mismos_bytes(
        self, carpetas, tmp_path, monkeypatch
    ):
        """Con el reloj movido entre una vuelta y la otra, a propósito.

        Sin mover el reloj esta prueba **pasaba con el fallo dentro**: las dos
        vueltas caían en el mismo segundo y la fecha de la entrada salía
        igual. Es el fallo de siempre de esta casa con el disfraz más fino que
        se le ha visto —una prueba de reproducibilidad que no reproduce nada—,
        así que el reloj se mueve una hora entre las dos y se acabó la suerte.
        """
        import time as reloj

        esquemas, anclas, sellos = carpetas
        vueltas = iter([1_757_000_000.0, 1_757_003_600.0] * 400)
        monkeypatch.setattr(reloj, "time", lambda: next(vueltas))

        huellas = []
        for nombre in ("uno.zip", "dos.zip"):
            paquete.armar(
                tmp_path / nombre, esquemas, anclas, sellos, hoy=date(2026, 9, 10)
            )
            huellas.append((tmp_path / nombre).read_bytes())
        assert huellas[0] == huellas[1]

    def test_y_la_fecha_de_esa_entrada_es_la_del_dia_en_que_se_armo(
        self, carpetas, tmp_path
    ):
        """Ni la hora del reloj ni una fecha inventada: la que ya declara.

        `armado` sale en el propio manifiesto, así que la entrada no dice nada
        que el paquete no dijera ya.
        """
        esquemas, anclas, sellos = carpetas
        paquete.armar(
            tmp_path / "p.zip", esquemas, anclas, sellos, hoy=date(2026, 9, 10)
        )
        with zipfile.ZipFile(tmp_path / "p.zip") as z:
            ficha = z.getinfo(paquete.MANIFIESTO)
        assert ficha.date_time == (2026, 9, 10, 0, 0, 0)

    def test_el_manifiesto_de_dentro_sigue_saliendo_legible(self, carpetas, tmp_path):
        """Poner la ficha a mano es fácil que deje la entrada sin permisos.

        Y eso no se ve en Windows: se ve el día que alguien lo descomprime en
        un sistema que sí los mira y el fichero no se deja leer.
        """
        esquemas, anclas, sellos = carpetas
        paquete.armar(
            tmp_path / "p.zip", esquemas, anclas, sellos, hoy=date(2026, 9, 10)
        )
        with zipfile.ZipFile(tmp_path / "p.zip") as z:
            ficha = z.getinfo(paquete.MANIFIESTO)
            dentro = json.loads(z.read(paquete.MANIFIESTO))
        assert ficha.external_attr >> 16 & 0o400, "sin permiso de lectura"
        assert dentro["armado"] == "2026-09-10"


class TestSoloSeBorraLoQueMontoEsto:
    """Montar el sitio empieza por borrar el destino entero.

    Y lo borraba fuera lo que fuera. Probado en una carpeta temporal que hacía
    de carpeta de trabajo: se llevó un `anclas/` y un `Proyecto 1/` y salió con
    código 0. Un `--sitio ..` lanzado desde Factura-e hacía eso de verdad.
    """

    def test_una_carpeta_ajena_no_se_toca(self, repositorio):
        ajena = repositorio / "trabajo"
        (ajena / "Proyecto 1").mkdir(parents=True)
        (ajena / "Proyecto 1" / "estrategia.py").write_text("# suyo\n", encoding="utf-8")
        with pytest.raises(paquete.NoEsUnSitio):
            _montar(repositorio, destino="trabajo")
        assert (ajena / "Proyecto 1" / "estrategia.py").is_file()

    def test_ni_un_fichero(self, repositorio):
        (repositorio / "nota.txt").write_text("mía\n", encoding="utf-8")
        with pytest.raises(paquete.NoEsUnSitio):
            _montar(repositorio, destino="nota.txt")
        assert (repositorio / "nota.txt").read_text(encoding="utf-8") == "mía\n"

    def test_ni_la_carpeta_desde_la_que_se_trabaja_aunque_lleve_el_testigo(
        self, repositorio, monkeypatch
    ):
        # Ni con testigo: es la única que no se arregla montando otra vez. Se
        # trabaja desde `web/` y se apunta a la carpeta que la contiene; si la
        # guardia falla, lo que se borra es el repositorio de mentira de esta
        # prueba y no nada de fuera de ella.
        (repositorio / paquete.TESTIGO_DEL_SITIO).write_text("", encoding="utf-8")
        monkeypatch.chdir(repositorio / "web")
        with pytest.raises(paquete.NoEsUnSitio):
            _montar(repositorio, destino=".")
        assert (repositorio / "muestras" / "de-un-cliente.xml").is_file()

    def test_una_carpeta_vacia_si(self, repositorio):
        (repositorio / "sitio").mkdir()
        _montar(repositorio)
        assert (repositorio / "sitio" / "index.html").is_file()

    def test_y_un_sitio_montado_antes_tambien(self, repositorio):
        # Lo normal: montar encima del de la vez anterior.
        _montar(repositorio)
        (repositorio / "sitio" / "sobra.txt").write_text("de ayer\n", encoding="utf-8")
        _montar(repositorio)
        assert not (repositorio / "sitio" / "sobra.txt").exists()

    def test_el_testigo_va_nada_mas_crear_la_carpeta(self, repositorio, monkeypatch):
        # Un montaje que se para a medias tiene que poder repetirse sin borrar
        # a mano: el testigo ya está puesto aunque no haya llegado al final.
        def se_cae(*_):
            raise RuntimeError("a medias")

        monkeypatch.setattr(paquete, "_para_buscadores", se_cae)
        with pytest.raises(RuntimeError):
            _montar(repositorio)
        assert (repositorio / "sitio" / paquete.TESTIGO_DEL_SITIO).is_file()
        monkeypatch.undo()
        _montar(repositorio)
        assert (repositorio / "sitio" / "index.html").is_file()


class TestParaQueSeLlegueDesdeFuera:
    """Canónica, tarjeta social, `robots.txt` y `sitemap.xml`.

    Hasta que esto existió, el sitio se montaba entero y **no existía para
    ningún buscador**. No es un fallo que se vea desde dentro: la página
    funciona perfectamente para quien ya sabe la dirección. Se vio buscando
    «glosa-e.com» y comprobando que no salía ni una vez.
    """

    def test_hay_robots_y_dice_donde_esta_el_sitemap(self, repositorio):
        sitio = _montar(repositorio).carpeta
        robots = (sitio / "robots.txt").read_text(encoding="utf-8")
        assert "User-agent: *" in robots
        assert f"Sitemap: {paquete.DOMINIO}/sitemap.xml" in robots

    def test_el_sitemap_lista_todas_las_paginas_y_ninguna_mas(self, repositorio):
        sitio = _montar(repositorio).carpeta
        mapa = (sitio / "sitemap.xml").read_text(encoding="utf-8")
        paginas = sorted(p.name for p in sitio.glob("*.html"))
        assert mapa.count("<loc>") == len(paginas)
        # La portada va como la raíz, no como `/index`: con `cleanUrls` es la
        # dirección que Vercel sirve de verdad.
        assert f"<loc>{paquete.DOMINIO}/</loc>" in mapa
        assert "/index<" not in mapa

    def test_ninguna_direccion_del_sitemap_lleva_punto_html(self, repositorio):
        """`cleanUrls` hace que `/legal.html` conteste con un 308 a `/legal`.

        Mandar al buscador a la que redirige es mandarlo a una mudanza.
        """
        sitio = _montar(repositorio).carpeta
        mapa = (sitio / "sitemap.xml").read_text(encoding="utf-8")
        assert ".html" not in mapa

    def test_cada_pagina_lleva_su_canonica_y_su_tarjeta(self, repositorio):
        sitio = _montar(repositorio).carpeta
        for pagina in sorted(sitio.glob("*.html")):
            texto = pagina.read_text(encoding="utf-8")
            assert 'rel="canonical"' in texto, pagina.name
            assert 'property="og:image"' in texto, pagina.name
            assert 'name="twitter:card"' in texto, pagina.name
            assert 'property="og:title"' in texto, pagina.name

    def test_la_canonica_de_cada_una_es_la_suya(self, repositorio):
        """Una canónica repetida le dice al buscador que dos páginas son una."""
        sitio = _montar(repositorio).carpeta
        canonicas = [
            re.search(r'rel="canonical" href="([^"]*)"', p.read_text("utf-8")).group(1)
            for p in sorted(sitio.glob("*.html"))
        ]
        assert len(set(canonicas)) == len(canonicas)

    def test_la_tarjeta_viaja(self, repositorio):
        sitio = _montar(repositorio).carpeta
        assert (sitio / "marca" / "tarjeta.png").is_file()

    def test_la_tarjeta_lleva_la_huella_de_la_que_se_publica(self, repositorio):
        """Telegram enseñó el 25-09-2026 la tarjeta de antes, con la nueva ya
        publicada: quien pinta la vista previa guarda la imagen por dirección,
        y `tarjeta.png` a secas era la misma dirección para siempre."""
        sitio = _montar(repositorio).carpeta
        huella = hashlib.sha256(
            (sitio / "marca" / "tarjeta.png").read_bytes()).hexdigest()[:8]
        esperada = f"{paquete.DOMINIO}/marca/tarjeta.png?v={huella}"
        vistas = 0
        for pagina in sorted(sitio.glob("*.html")):
            imagen = re.search(r'property="og:image" content="([^"]*)"',
                               pagina.read_text(encoding="utf-8"))
            if imagen:
                vistas += 1
                assert imagen[1] == esperada, (pagina.name, imagen[1])
        assert vistas, "ninguna página lleva og:image"

    def test_otra_tarjeta_es_otra_direccion(self, repositorio):
        """Lo que importa de la huella: que cambie cuando cambia la imagen."""
        def direccion(sitio):
            texto = (sitio / "index.html").read_text(encoding="utf-8")
            return re.search(r'property="og:image" content="([^"]*)"', texto)[1]

        antes = direccion(_montar(repositorio).carpeta)
        (repositorio / "web" / "marca" / "tarjeta.png").write_bytes(b"otra tarjeta")
        despues = direccion(_montar(repositorio, destino="otro").carpeta)
        assert antes != despues

    def test_los_guiones_de_la_marca_no_se_publican(self, repositorio):
        """En `web/marca/` viven también los que generan la marca y la letra.

        Son herramientas, no página. Se copia lo que se nombra y nada más.
        """
        (repositorio / "web" / "marca" / "trazar.py").write_text(
            "# la herramienta\n", encoding="utf-8")
        sitio = _montar(repositorio).carpeta
        assert not (sitio / "marca" / "trazar.py").exists()

    def test_sin_la_tarjeta_no_se_monta(self, repositorio):
        """Un `og:image` a una dirección que da 404 no falla aquí: falla fuera."""
        (repositorio / "web" / "marca" / "tarjeta.png").unlink()
        with pytest.raises(paquete.SinPagina) as motivo:
            _montar(repositorio)
        assert "herramientas.tarjeta" in str(motivo.value)

    def test_una_pagina_sin_cabecera_no_se_monta(self, repositorio):
        """`replace` sobre lo que no está no falla: devuelve el texto igual."""
        (repositorio / "web" / "legal.html").write_text(
            "<!doctype html><title>x</title>", encoding="utf-8")
        with pytest.raises(paquete.SinPagina) as motivo:
            _montar(repositorio)
        assert "</head>" in str(motivo.value)

    def test_una_pagina_sin_descripcion_no_se_monta(self, repositorio):
        """En un buscador saldría sin resumen, que se ve y se ve mal."""
        (repositorio / "web" / "legal.html").write_text(
            "<!doctype html><head><title>x</title></head><body></body>",
            encoding="utf-8")
        with pytest.raises(paquete.SinPagina) as motivo:
            _montar(repositorio)
        assert "descripción" in str(motivo.value)


class TestLosEnlacesQueSeVanDelSitio:
    """Un enlace a otro sitio se abre en otra pestaña, y sin dejar el mando.

    Se resuelve al montar y no a mano en cada página por lo de siempre: a mano
    se escriben los de hoy y se olvidan los de mañana. Y `noopener` no es
    cosmética —sin él la página que se abre puede cambiar de sitio a esta desde
    su propia pestaña—, así que esto no es un detalle de comodidad.
    """

    def _enlaces(self, sitio) -> str:
        return (sitio / "index.html").read_text(encoding="utf-8")

    def test_el_que_se_va_se_abre_aparte_y_sin_dejar_el_mando(self, repositorio):
        texto = self._enlaces(_montar(repositorio).carpeta)
        salida = re.search(r'<a href="https://www\.boe\.es/uno"[^>]*>', texto)
        assert salida, "el enlace de fuera ha desaparecido de la página"
        assert 'target="_blank"' in salida.group(0)
        assert "noopener" in salida.group(0)
        assert "noreferrer" in salida.group(0)

    def test_el_de_casa_se_queda_en_casa(self, repositorio):
        texto = self._enlaces(_montar(repositorio).carpeta)
        # Ya en su forma limpia: ver `TestLosEnlacesDeCasa`.
        casa = re.search(r'<a href="\./legal"[^>]*>', texto)
        assert casa and "target=" not in casa.group(0), (
            "un enlace del propio sitio abriendo pestaña nueva es ruido: se "
            "va llenando el navegador de copias de la misma página")

    def test_el_rel_que_ya_traia_no_se_pierde(self, repositorio):
        """`nofollow` estaba puesto a propósito: no se le regala posición a un
        competidor por citarlo. Añadir `noopener` no puede quitarlo."""
        texto = self._enlaces(_montar(repositorio).carpeta)
        con_rel = re.search(r'<a href="https://aidoks\.eu/dos"[^>]*>', texto)
        assert con_rel, "el enlace con rel ha desaparecido"
        for señal in ("nofollow", "noopener", "noreferrer"):
            assert señal in con_rel.group(0), señal

    def test_ninguna_pagina_montada_deja_uno_suelto(self, repositorio):
        """El recuento, que es lo que caza al que se añada mañana."""
        sitio = _montar(repositorio).carpeta
        for pagina in sorted(sitio.glob("*.html")):
            texto = pagina.read_text(encoding="utf-8")
            for etiqueta in re.findall(r"<a\b[^>]*>", texto):
                url = re.search(r'href="([^"]*)"', etiqueta)
                if not url or not paquete._es_de_fuera(url.group(1)):
                    continue
                assert 'target="_blank"' in etiqueta, f"{pagina.name}: {etiqueta}"


class TestLosEnlacesDeCasa:
    """Los enlaces de una página a otra, en la dirección que se sirve.

    Search Console, el 25-09-2026: 19 páginas «con redirección» y las dos
    formas de BR-47 y de BR-51 recibiendo impresiones por separado. La
    canónica y el sitemap ya decían la limpia; los enlaces, no —225 por ficha,
    396 en el catálogo, medido en producción—, y cada uno era un 308.
    """

    def _con(self, repositorio, *enlaces):
        cuerpo = "".join(f'<a href="{e}">x</a>' for e in enlaces)
        (repositorio / "web" / "legal.html").write_text(
            PAGINA.replace("</body>", cuerpo + "</body>"), encoding="utf-8")

    def test_ninguna_pagina_montada_enlaza_a_una_redireccion(self, repositorio):
        sitio = _montar(repositorio).carpeta
        for pagina in sorted(sitio.glob("*.html")):
            texto = pagina.read_text(encoding="utf-8")
            assert paquete._de_casa_con_html(texto) == [], pagina.name
        assert 'href="./legal"' in (sitio / "index.html").read_text(encoding="utf-8")

    def test_el_ancla_no_se_pierde_y_la_portada_es_la_raiz(self, repositorio):
        self._con(repositorio, "./legal.html#aviso", "./index.html#zona",
                  "./index.html")
        texto = (_montar(repositorio).carpeta / "legal.html").read_text(encoding="utf-8")
        assert 'href="./legal#aviso"' in texto
        assert 'href="./#zona"' in texto
        assert 'href="./"' in texto
        assert "index" not in re.findall(r'href="(\./[^"]*)"', texto)

    def test_lo_que_no_es_una_pagina_de_casa_no_se_toca(self, repositorio):
        """Un `.html` de otro sitio es de otro sitio, y un fichero no es una
        página: `cleanUrls` solo quita el `.html`."""
        self._con(repositorio, "https://www.boe.es/buscar/act.html",
                  "./letra/OFL.txt", "mailto:a@b.es")
        texto = (_montar(repositorio).carpeta / "legal.html").read_text(encoding="utf-8")
        assert 'href="https://www.boe.es/buscar/act.html"' in texto
        assert 'href="./letra/OFL.txt"' in texto

    def test_uno_que_no_se_sabe_limpiar_no_se_monta(self, repositorio):
        """Sin el `./` la expresión no lo toca, y sin la negativa volvería a
        publicarse la redirección sin que nadie se enterara."""
        self._con(repositorio, "legal.html#privacidad")
        with pytest.raises(paquete.SinPagina) as motivo:
            _montar(repositorio)
        assert "legal.html#privacidad" in str(motivo.value)

    def test_las_plantillas_y_las_fichas_de_verdad_se_saben_limpiar(self, tmp_path):
        """El montaje de arriba es de mentira. Esto pasa la limpieza por lo que
        se publica de verdad —las plantillas de `web/`, los artículos, el
        catálogo y las 390 fichas— para que un enlace mal escrito se vea aquí y
        no en el despliegue."""
        from validador import pagina_incidencias
        web = Path(__file__).resolve().parent.parent / "web"
        textos = {p.name: p.read_text(encoding="utf-8")
                  for p in [*web.glob("*.html"), *(web / "bitacora").glob("*.html")]}
        pagina_incidencias.montar_pagina(web / "incidencias.html", tmp_path / "catalogo.html")
        textos["catalogo"] = (tmp_path / "catalogo.html").read_text(encoding="utf-8")
        for ficha in pagina_incidencias.montar_fichas(web / "incidencias.html", tmp_path):
            textos[ficha] = (tmp_path / ficha).read_text(encoding="utf-8")
        sueltos = {n: q for n, t in textos.items()
                   if (q := paquete._de_casa_con_html(paquete._a_la_limpia(t)[0]))}
        assert not sueltos, sueltos


class TestElServidorDeLocal:
    """`herramientas/servir_sitio.py`: el sitio montado, como lo sirve Vercel.

    Sin él, la vista previa local se rompía con el arreglo de arriba:
    `http.server` no sabe de `cleanUrls` y `./legal` le da 404.
    """

    @pytest.fixture
    def servidor(self, tmp_path):
        import http.client
        import threading
        from functools import partial
        from http.server import ThreadingHTTPServer
        from herramientas.servir_sitio import ComoVercel

        for nombre, texto in (("index.html", "portada"), ("legal.html", "legal"),
                              ("404.html", "no hay nada"),
                              ("codigo-BR-01.html", "br-01"), ("glosa.css", "css")):
            (tmp_path / nombre).write_text(texto, encoding="utf-8")
        manejador = partial(ComoVercel, directory=str(tmp_path))
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), manejador)
        ComoVercel.log_message = lambda *a: None
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()

        def pedir(ruta):
            conexion = http.client.HTTPConnection("127.0.0.1", servidor.server_address[1])
            conexion.request("GET", ruta)
            respuesta = conexion.getresponse()
            cuerpo = respuesta.read().decode("utf-8")
            conexion.close()
            return respuesta.status, respuesta.getheader("Location"), cuerpo

        yield pedir
        servidor.shutdown()
        servidor.server_close()

    def test_la_direccion_limpia_sirve_la_pagina(self, servidor):
        assert servidor("/legal") == (200, None, "legal")
        assert servidor("/") == (200, None, "portada")
        assert servidor("/glosa.css?v=1a2b3c4d")[0] == 200

    def test_la_forma_con_html_redirige_como_en_produccion(self, servidor):
        assert servidor("/legal.html")[:2] == (308, "/legal")
        assert servidor("/index.html")[:2] == (308, "/")
        assert servidor("/legal/")[:2] == (308, "/legal")

    def test_lo_que_no_esta_da_la_pagina_de_error(self, servidor):
        assert servidor("/nada") == (404, None, "no hay nada")

    def test_distingue_mayusculas_aunque_windows_no(self, servidor):
        """Vercel da 404 a `/codigo-br-01`. Un servidor local que no lo diera
        enseñaría como buena una dirección que en producción no existe."""
        assert servidor("/codigo-BR-01")[0] == 200
        assert servidor("/codigo-br-01")[0] == 404


class TestElBuzonDeSeguridad:
    """`.well-known/security.txt`, que es donde se mira antes de avisar.

    Quien encuentra un fallo mira ahí primero; si no encuentra a dónde
    escribir, lo normal es que lo publique en vez de contarlo. En algo que
    verifica firmas, eso importa.
    """

    def test_esta_donde_se_busca_y_dice_a_quien_escribir(self, repositorio):
        sitio = _montar(repositorio).carpeta
        texto = (sitio / ".well-known" / "security.txt").read_text(encoding="utf-8")
        assert "Contact: mailto:contacto@glosa-e.com" in texto
        assert f"Canonical: {paquete.DOMINIO}/.well-known/security.txt" in texto

    def test_caduca_dentro_de_un_anio_y_no_ayer(self, repositorio):
        """Un `security.txt` caducado dice que esto está abandonado.

        Por eso la fecha se calcula al montar y no se escribe a mano: cada
        despliegue la renueva, y si el sitio pasa un año sin desplegarse
        caduca, que es justo lo que hay que decir en ese caso.
        """
        sitio = _montar(repositorio).carpeta
        texto = (sitio / ".well-known" / "security.txt").read_text(encoding="utf-8")
        dicha = re.search(r"Expires: (\d{4}-\d{2}-\d{2})T", texto)
        assert dicha, "no dice cuándo caduca, y el RFC 9116 lo exige"
        caduca = date.fromisoformat(dicha.group(1))
        assert caduca > date.today(), "nace caducado"
        assert (caduca - date.today()).days <= 366

    def test_sin_correo_en_la_ficha_no_se_promete_un_buzon(self, repositorio):
        """La ficha se puede vaciar —lo hace `hayIdentificacion()`— y entonces
        un `security.txt` mandaría a escribir a nadie."""
        cargador = repositorio / "web" / "glosa.js"
        cargador.write_text(
            cargador.read_text(encoding="utf-8").replace(
                'correo: "contacto@glosa-e.com"', 'correo: ""'),
            encoding="utf-8")
        with pytest.raises(paquete.SinPagina) as motivo:
            _montar(repositorio)
        assert "security.txt" in str(motivo.value)


class TestNingunaNegativaSaleConTraza:
    """La lista de negativas que `--sitio` cazaba estaba escrita a mano.

    Lo que pasó, medido el 20-09-2026: `SinPolitica` se añadió después y nadie
    tocó el `except`, así que una página con un `onclick=` salía con traza de
    Python y código 1 —no 2— y dejaba 409 ficheros montados y ningún
    `rueda.json`. Es una carpeta a medias con cara de sitio, que es justo lo
    que el paso siguiente publica sin enterarse.
    """

    def test_todas_cuelgan_de_la_raiz(self):
        """La que se escriba mañana ya está cazada el día que se escribe."""
        import inspect

        # Las dos de `--empaquetar`, que no montan ningún sitio. Están aquí
        # escritas para que añadir una excepción obligue a decidir de cuál de
        # las dos clases es, en vez de dejarla suelta sin que nadie lo note.
        DE_OTRA_COSA = {"SinManifiesto", "SinRenovar", "NoSeMonta"}

        sueltas = [
            nombre
            for nombre, cosa in vars(paquete).items()
            if inspect.isclass(cosa)
            and issubclass(cosa, Exception)
            and cosa.__module__ == paquete.__name__
            and nombre not in DE_OTRA_COSA
            and not issubclass(cosa, paquete.NoSeMonta)
        ]
        assert not sueltas, (
            f"{sueltas} no hereda(n) de `NoSeMonta`, así que `--sitio` saldría "
            "con traza de Python y código 1 al levantarla(s). O hereda, o "
            "consta en DE_OTRA_COSA."
        )

    def test_la_raiz_caza_a_las_siete(self):
        for cual in (paquete.SinRueda, paquete.SinPagina, paquete.SinPyodide,
                     paquete.RuedaVieja, paquete.SinPaquete,
                     paquete.NoEsUnSitio, paquete.SinPolitica):
            assert issubclass(cual, paquete.NoSeMonta), cual.__name__

    def test_la_orden_sale_con_2_y_cuenta_el_motivo(self, monkeypatch, capsys):
        from validador import __main__

        def negarse(*_, **__):
            raise paquete.SinPolitica("un onclick= de mentira")

        monkeypatch.setattr(paquete, "montar_sitio", negarse)
        assert __main__._montar_sitio(Path("sitio")) == 2
        error = capsys.readouterr().err
        assert "No se ha montado nada" in error
        assert "un onclick= de mentira" in error


class TestLaPoliticaSeMiraAntesDeTocarNada:
    """Como la bitácora, y por lo mismo: no dejar una carpeta a medias.

    `_con_politica` corre al final, que es donde tiene que correr —las huellas
    de los scripts tienen que ser las del texto que de verdad se publica—. Lo
    que no tenía que esperar al final es mirar si una página lleva un
    `onclick=`: eso se ve leyendo `web/`.
    """

    def test_un_manejador_en_linea_no_deja_carpeta(self, repositorio):
        (repositorio / "web" / "banco.html").write_text(
            PAGINA.replace("<body>", '<body onclick="nada()">'),
            encoding="utf-8",
        )
        with pytest.raises(paquete.SinPolitica) as fallo:
            _montar(repositorio)
        assert "banco.html" in str(fallo.value)
        assert not (repositorio / "sitio").exists(), (
            "se ha quedado media carpeta montada: con salida 2 es peor que un "
            "fallo limpio, porque el paso siguiente la publica igual"
        )

    def test_un_enlace_javascript_tampoco(self, repositorio):
        (repositorio / "web" / "legal.html").write_text(
            PAGINA.replace("</body>", '<a href="javascript:void(0)">x</a></body>'),
            encoding="utf-8",
        )
        with pytest.raises(paquete.SinPolitica):
            _montar(repositorio)
        assert not (repositorio / "sitio").exists()

    def test_un_script_en_linea_con_atributos_tampoco(self, repositorio):
        """Quedaría fuera de la política y bloqueado sin decir nada."""
        (repositorio / "web" / "index.html").write_text(
            PAGINA.replace("</body>", "<script defer>hola()</script></body>"),
            encoding="utf-8",
        )
        with pytest.raises(paquete.SinPolitica):
            _montar(repositorio)
        assert not (repositorio / "sitio").exists()

    def test_una_pagina_sana_se_monta_y_lleva_su_politica(self, repositorio):
        _montar(repositorio)
        texto = (repositorio / "sitio" / "index.html").read_text(encoding="utf-8")
        assert 'http-equiv="Content-Security-Policy"' in texto


class TestUnInterpreteEstropeadoNoSePublica:
    """Lo que se sirve al navegador tiene que ser lo que se trajo.

    `--traer-pyodide` contrasta lo que baja con las huellas fijadas en
    `HUELLAS_DE_PYODIDE`. Aquí se caza lo otro: que un fichero se estropee
    **después**, en el disco, entre traerlo y publicarlo. Eso se mira contra
    `HUELLAS.txt`, que es el recibo que dejó traerlo.
    """

    def test_un_fichero_cambiado_despues_de_traerlo(self, repositorio):
        roto = repositorio / "vendor" / "pyodide" / "pyodide.asm.wasm"
        roto.write_bytes(b"otra cosa")
        with pytest.raises(paquete.PyodideQueNoCuadra) as motivo:
            _montar(repositorio)
        assert "pyodide.asm.wasm" in str(motivo.value)
        assert not (repositorio / "sitio").exists(), (
            "se ha quedado media carpeta: la negativa va antes de tocar nada"
        )

    def test_uno_a_medias_tampoco(self, repositorio):
        """Una descarga cortada no da error: deja el fichero corto y sigue."""
        corto = repositorio / "vendor" / "pyodide" / "python_stdlib.zip"
        corto.write_bytes(b"")
        with pytest.raises(paquete.PyodideQueNoCuadra):
            _montar(repositorio)

    def test_sin_recibo_no_se_inventa_una_queja(self, repositorio):
        """Sin `HUELLAS.txt` no hay con qué comparar, y eso no es un hallazgo.

        La carpeta se trajo antes de que existiera el recibo, o se montó a
        mano. Lo que se publique se sigue mirando por otros sitios; lo que no
        se puede es dar por malo algo que no se ha podido comprobar.
        """
        (repositorio / "vendor" / "pyodide" / paquete.NOMBRE_DE_HUELLAS).unlink()
        _montar(repositorio)
        assert (repositorio / "sitio" / "index.html").is_file()


class TestComoSeSirveLoQueSeMonta:
    """Dos ficheros de configuración que deciden cómo llega esto a alguien."""

    VERCEL = Path(__file__).resolve().parent.parent / "vercel.json"
    LANZADOR = Path(__file__).resolve().parent.parent / ".claude" / "launch.json"

    def test_la_barra_final_no_deja_la_pagina_desnuda(self):
        """Punto 13 de la auditoría, medido sobre `www.glosa-e.com`.

        `/banco/` contestaba 200 con el HTML del banco, y `/banco/glosa.css`,
        `/banco/glosa.js` y `/banco/prueba.py` contestaban 404: la página
        cargaba sin estilo ni validador y el banco se quedaba colgado. Es lo
        que pasa cuando `cleanUrls` sirve también la forma con barra y la
        página busca sus cosas con rutas relativas.
        """
        dicho = json.loads(self.VERCEL.read_text(encoding="utf-8"))
        assert dicho.get("trailingSlash") is False, (
            "sin `\"trailingSlash\": false`, `/banco/` sirve la página y sus "
            "`./glosa.css` y `./glosa.js` se piden dentro de `/banco/`, donde "
            "no hay nada"
        )

    def test_las_cabeceras_que_no_pone_nadie_por_nosotros(self):
        """Punto 39 de la auditoría, medido sobre `www.glosa-e.com` el
        22-09-2026 y vuelto a medir al cerrarlo.

        | Cabecera | Antes | Después |
        |---|---|---|
        | `Strict-Transport-Security` | `max-age=63072000`, sin subdominios —el `.vercel.app` sí los llevaba— | con `includeSubDomains` |
        | `Permissions-Policy` | no estaba | cámara, micrófono, ubicación y cinco más, apagadas |
        | `Cross-Origin-Opener-Policy` | no estaba | `same-origin` |
        | `Cross-Origin-Resource-Policy` | no estaba | `same-origin` |

        No se pide `preload` en la HSTS **a propósito**: es una lista de la que
        cuesta salir, y esto se puede querer deshacer.
        """
        dicho = json.loads(self.VERCEL.read_text(encoding="utf-8"))
        globales = next(b for b in dicho["headers"] if b["source"] == "/(.*)")
        puestas = {h["key"]: h["value"] for h in globales["headers"]}
        for clave in ("Strict-Transport-Security", "Permissions-Policy",
                      "Cross-Origin-Opener-Policy", "Cross-Origin-Resource-Policy",
                      "X-Content-Type-Options", "Referrer-Policy",
                      "Content-Security-Policy"):
            assert clave in puestas, f"el sitio se sirve sin «{clave}»"
        assert "includeSubDomains" in puestas["Strict-Transport-Security"], (
            "la HSTS no alcanza a los subdominios, así que uno servido por "
            "http seguiría siendo una puerta"
        )
        assert "preload" not in puestas["Strict-Transport-Security"], (
            "`preload` es una lista de la que cuesta salir: si se quiere, que "
            "sea una decisión y no un arrastre"
        )
        for apagada in ("camera=()", "microphone=()", "geolocation=()"):
            assert apagada in puestas["Permissions-Policy"]

    def test_el_fichero_de_comprobaciones_se_puede_leer_de_un_clic(self):
        """Punto 39. Se servía como `application/octet-stream`, medido, así que
        abrirlo en el navegador lo descargaba en vez de enseñarlo. Es el
        fichero que dice si el validador hace lo que promete: si no se puede
        leer sin bajárselo, media promesa se queda en el aire."""
        dicho = json.loads(self.VERCEL.read_text(encoding="utf-8"))
        bloque = next(b for b in dicho["headers"] if b["source"] == "/prueba.py")
        tipos = [h["value"] for h in bloque["headers"] if h["key"] == "Content-Type"]
        assert tipos and tipos[0].startswith("text/plain"), (
            "`prueba.py` vuelve a servirse como una descarga"
        )


    def test_los_servidores_de_local_no_salen_a_la_red(self):
        """Punto 23. `http.server` sin `--bind` escucha en `0.0.0.0`.

        Medido: el de `web` contestaba en la IP de la red local de esta
        máquina sirviendo el repositorio entero, `.git/HEAD` incluido, que es
        `muestras/` y `anclas/` repartidas a quien pase.
        """
        dicho = json.loads(self.LANZADOR.read_text(encoding="utf-8"))
        for servidor in dicho["configuraciones" if "configuraciones" in dicho
                              else "configurations"]:
            argumentos = servidor.get("runtimeArgs", [])
            assert "--bind" in argumentos, (
                f"el servidor «{servidor['name']}» escucha en todas las "
                "interfaces"
            )
            assert argumentos[argumentos.index("--bind") + 1] == "127.0.0.1", (
                f"el servidor «{servidor['name']}» se ata a algo que no es "
                "esta máquina"
            )


class TestLaPaginaDeCuandoNoHayNada:
    """Punto 38 de la auditoría, medido sobre `www.glosa-e.com`.

    `/codigo-BR-01` contesta 200 y `/codigo-br-01` contestaba **404 con 79
    bytes que dicen `NOT_FOUND`**: la página genérica de Vercel, en inglés y
    sin decir de quién es el sitio. Y no hay redirección que lo arregle —no se
    le puede decir a Vercel «pon esto en mayúsculas», y escribir 390 reglas a
    mano es la clase de lista que se queda atrás—, así que se arregla donde se
    nota.

    Probado sirviendo el sitio montado **como lo sirve Vercel** —`cleanUrls` y
    `404.html` en lo que no encuentra— y distinguiendo mayúsculas a mano,
    porque Windows no las distingue y sin eso el fallo no se reproduce en esta
    máquina:

    | Dirección | Antes | Después |
    |---|---|---|
    | `/codigo-BR-01` | 200 | 200 |
    | `/codigo-br-01` | 404 «NOT_FOUND» | 404 con la página propia y un enlace a `/codigo-BR-01` |
    | `/lo-que-sea` | 404 «NOT_FOUND» | 404 con la página propia, sin rescate |
    """

    PAGINA = Path(__file__).resolve().parent.parent / "web" / "404.html"

    def test_existe_y_se_monta_con_el_sitio(self):
        assert self.PAGINA.is_file()
        assert "404.html" in paquete._DE_LA_PAGINA, (
            "la página existe y no se copia al sitio, que es como no existir"
        )

    def test_no_se_indexa(self):
        """Ni sitemap ni tarjeta social: no es contenido, es lo que queda
        cuando el contenido no está."""
        assert 'name="robots" content="noindex"' in self.PAGINA.read_text(encoding="utf-8")
        assert "404.html" in paquete._FUERA_DEL_INDICE

    def test_rescata_el_codigo_escrito_en_minusculas(self):
        """Y se mira **la dirección que se arma**, no que la palabra salga.

        La primera versión de esta prueba buscaba `toUpperCase()` en la
        página, y eso no sujetaba nada: quitándoselo a la dirección seguía
        pasando, porque la misma palabra está en la línea que pinta el texto
        del enlace. Provocado, y por eso está escrito.
        """
        texto = self.PAGINA.read_text(encoding="utf-8")
        assert 'const canonica = "/codigo-" + parecido[1].toUpperCase();' in texto, (
            "la dirección del rescate ya no se arma en mayúsculas, así que "
            "lleva otra vez a donde no hay nada"
        )
        assert 'method: "HEAD"' in texto, (
            "se ofrece el enlace sin comprobar que existe: uno que vuelva a "
            "dar 404 es peor que ninguno"
        )

    def test_dice_de_quien_es_el_sitio(self):
        """Que es lo que la genérica de Vercel no hacía."""
        texto = self.PAGINA.read_text(encoding="utf-8")
        assert "Glosa-e" in texto and 'lang="es"' in texto
        assert "Agencia Tributaria" in texto, "se ha quedado sin el aviso del pie"
