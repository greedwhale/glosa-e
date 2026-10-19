"""Lo que la página le enseña a quien la usa: sin rutas de dentro y con comas.

Visto en producción el 29-09-2026, con las respuestas pasadas por el navegador
de verdad:

| | Antes | Después |
|---|---|---|
| Una respuesta de UBL 2.0 | «…El que le toca se llama UBL-ApplicationResponse-2.0.xsd, y se busca dentro de /opt/factura-e/esquemas.» | «…y no está entre los esquemas que vienen con esta página.» |
| El arranque | «Listo en 46.67 s» | «Listo en 46,67 s» |

`/opt/factura-e` es el disco virtual del navegador, donde se descomprime el
paquete: nadie lo puede abrir, y en la página no se puede añadir un esquema.
En consola la carpeta sí sirve, y ahí se sigue diciendo.

Al buscar dónde más pasaba se encontraron tres de la misma familia, que van
aquí también: el fichero que tumba al validador salía con su ruta del disco
virtual —`/entrada/0/factura__.xml`, con el nombre limpiado— y «No se ha podido
validar» dos veces; el banco pintaba cada comprobación con «12.3 ms»; y la
procedencia de las anclas decía «esta pagina», sin tilde, en cada firma que
llega a una autoridad de la lista.

Aquí no hay navegador. Lo que sí hay es el Python que corre la página, tal cual
está escrito en `glosa.js`, y el paquete que se descomprime en ella: con eso se
monta lo mismo que monta `traerPaquete`, en una carpeta temporal, y se mira que
**nada** de lo que vuelve a la página la nombre. La carpeta es la de la prueba
y no `/opt/factura-e` a propósito: así también se ven las rutas de los ficheros
soltados, que viven al lado.

Se busca en lo que la página **lee**, no en el JSON escrito. La primera versión
buscaba la ruta en el texto de `json.dumps`, que escribe cada barra invertida
dos veces: en Windows, donde corre el gancho que no deja empujar, la ruta no
salía nunca aunque estuviera, y la prueba de la familia entera pasaba en verde
con el aviso de antes dentro. Lo vio la revisión, emulando Windows con una
carpeta que lleva `\\`. Por eso la carpeta de la prueba lleva una también en
Linux: así la guardia se ejercita con ella en GitHub, y no solo donde la hay.
"""

import json
import re
import zipfile
from pathlib import Path

import pytest

from test_respuesta import respuesta
from validador import en16931, factura
from validador.esquema import Catalogo

RAIZ = Path(__file__).resolve().parent.parent
GLOSA_JS = RAIZ / "web" / "glosa.js"


def _informe_de_la_pagina() -> str:
    """El Python de `INFORME`, cortado donde lo corta JavaScript.

    Hasta el 19-10-2026 se sacaba con `const INFORME = `(.*?)`;`, que busca la
    primera comilla invertida **seguida de punto y coma**. JavaScript corta en
    la primera, a secas: un comentario con `--recuento` entre comillas
    invertidas cerraba la plantilla en el navegador, la página no arrancaba
    («Invalid left-hand side expression in postfix operation») y aquí todas
    las pruebas que corren este Python seguían en verde, porque leían el
    fichero entero. Ahora se corta igual que allí, y si lo que queda no acaba
    la sentencia, no hay Python que probar.
    """
    codigo = GLOSA_JS.read_text(encoding="utf-8")
    apertura = "const INFORME = `"
    inicio = codigo.index(apertura) + len(apertura)
    fin = codigo.index("`", inicio)
    assert codigo[fin:fin + 2] == "`;", (
        "una comilla invertida dentro del Python de la página cierra la plantilla "
        f"de JavaScript antes de tiempo: {codigo[fin - 60:fin + 20]!r}")
    python = codigo[inicio:fin]
    # Lo otro que JavaScript se come antes de que llegue a Python.
    for que in ("\\", "${"):
        assert que not in python, f"{que!r} dentro de INFORME: JavaScript lo interpreta"
    return python


@pytest.fixture
def la_pagina(tmp_path, monkeypatch):
    """El paquete descomprimido como en el navegador, y el Python del informe.

    Devuelve una función que suelta unos ficheros y devuelve el JSON que la
    página recibe, en texto: es lo que se pinta.
    """
    # Con una barra invertida en el nombre: ver el principio del fichero. En
    # Windows es un separador más y quedan dos carpetas, que también vale.
    base = tmp_path / "con\\barra"
    dentro = base / "opt" / "factura-e"
    with zipfile.ZipFile(RAIZ / "web" / "paquete.zip") as paquete:
        paquete.extractall(dentro)
    # Las tres variables que pone `traerPaquete`, y ninguna más.
    monkeypatch.setenv("FACTURAE_ESQUEMAS", str(dentro / "esquemas"))
    monkeypatch.setenv("FACTURAE_ANCLAS", str(dentro / "anclas"))
    monkeypatch.setenv("FACTURAE_ANCLAS_SELLOS", str(dentro / "anclas-sellos"))
    informe = _informe_de_la_pagina()
    *cuerpo, ultima = informe.strip().rsplit("\n\njson.dumps", 1)

    def soltar(ficheros: dict[str, str | bytes]) -> str:
        rutas, nombres = [], []
        for orden, (nombre, contenido) in enumerate(ficheros.items()):
            # Como `validar()` de glosa.js: cada uno en su carpeta, con el
            # nombre limpiado para poder escribirlo, y al lado el de verdad.
            carpeta = base / "entrada" / str(orden)
            carpeta.mkdir(parents=True, exist_ok=True)
            limpio = re.sub(r"[^\w.\-]", "_", nombre, flags=re.ASCII)
            camino = carpeta / limpio
            if isinstance(contenido, str):
                contenido = contenido.encode("utf-8")
            camino.write_bytes(contenido)
            rutas.append(str(camino))
            nombres.append(nombre)
        espacio = {"_rutas": rutas, "_nombres": nombres}
        exec(cuerpo[0], espacio)
        soltar.espacio = espacio
        return eval("json.dumps" + ultima, espacio)

    soltar.carpeta = base
    return soltar


def _cadenas(valor):
    """Todo texto que hay en lo que la página recibe, claves incluidas."""
    if isinstance(valor, str):
        yield valor
    elif isinstance(valor, dict):
        for clave, dentro in valor.items():
            yield clave
            yield from _cadenas(dentro)
    elif isinstance(valor, list):
        for dentro in valor:
            yield from _cadenas(dentro)


def _sin_la_carpeta(salida: str, carpeta: Path) -> None:
    """Que ningún texto de lo que lee la página nombre la carpeta de la prueba.

    Sobre lo descodificado: en el JSON escrito, la barra invertida va doble.
    Y con las dos formas de escribir la ruta, la del sistema y la de barras.
    """
    formas = {str(carpeta), carpeta.as_posix()}
    fugas = [
        texto
        for texto in _cadenas(json.loads(salida))
        if any(forma in texto for forma in formas)
    ]
    assert not fugas, f"la página enseña su disco por dentro: {fugas}"


def _incidencias(salida: str, codigo: str) -> list[dict]:
    return [
        i
        for d in json.loads(salida)["documentos"]
        for i in d["incidencias"]
        if i["codigo"] == codigo
    ]


def test_el_python_de_la_pagina_es_una_plantilla_entera():
    """La guardia de arriba, provocada sola: sin ella, una prueba que no usa la
    fixture no se enteraría de que la plantilla está rota."""
    assert _informe_de_la_pagina().lstrip().startswith("import ")


class TestSinRutasDeDentro:
    def test_el_esquema_que_falta_no_nombra_el_disco_virtual(self, la_pagina):
        """El caso de producción: una respuesta de la 2.0, que no sube."""
        salida = la_pagina({"respuesta.xml": respuesta(version="2.0")})
        avisos = _incidencias(salida, "XSD-SIN-ESQUEMA")
        assert len(avisos) == 1, salida
        assert avisos[0]["mensaje"] == (
            "No se ha comprobado la forma: falta el esquema de este formato. "
            "El que le toca se llama UBL-ApplicationResponse-2.0.xsd, y no está "
            "entre los esquemas que vienen con esta página."
        )
        _sin_la_carpeta(salida, la_pagina.carpeta)

    def test_ni_con_todo_lo_que_trae_la_portada(self, la_pagina):
        """Los ejemplos de la portada, una factura 2.0 y una respuesta 2.0 juntos.

        La guardia de la familia entera: ni la carpeta del paquete ni la de los
        ficheros soltados en nada de lo que vuelve a la página, sea mensaje,
        campo, «tiene», resumen o las partes.
        """
        ficheros = {
            camino.name: camino.read_bytes()
            for camino in sorted((RAIZ / "ejemplos").iterdir())
            if camino.suffix in (".xml", ".edi")
        }
        ubl = (RAIZ / "ejemplos" / "f-0001.xml").read_text(encoding="utf-8")
        viejo = "<cbc:UBLVersionID>2.1</cbc:UBLVersionID>"
        assert ubl.count(viejo) == 1
        ficheros["factura 2.0.xml"] = ubl.replace(
            viejo, "<cbc:UBLVersionID>2.0</cbc:UBLVersionID>"
        )
        ficheros["respuesta ñ.xml"] = respuesta(version="2.0")
        salida = la_pagina(ficheros)
        assert len(_incidencias(salida, "XSD-SIN-ESQUEMA")) == 2, salida
        _sin_la_carpeta(salida, la_pagina.carpeta)

    def test_el_fichero_que_tumba_al_validador_sale_con_su_nombre(
        self, la_pagina, monkeypatch
    ):
        """Salía «No se ha podido validar. No se ha podido validar /entrada/0/…».

        Con la ruta del disco virtual, el nombre limpiado —«factura__.xml» por
        «factura ñ.xml»— y la frase dos veces. Se tumba a propósito: lo que se
        mira es cómo se cuenta la caída, no qué la provoca.
        """

        def revienta(*_a, **_k):
            raise KeyError("BT-99")

        monkeypatch.setattr(en16931, "reglas", revienta)
        salida = la_pagina({"factura ñ.xml": (RAIZ / "ejemplos" / "f-0001.xml").read_bytes()})
        documento = json.loads(salida)["documentos"][0]
        assert documento["resumen"] == (
            "No se ha podido validar. El validador ha fallado con \"factura ñ.xml\"."
        )
        [caida] = _incidencias(salida, "VALIDADOR-SE-ATRAGANTA")
        assert caida["encontrado"] == "factura ñ.xml"
        _sin_la_carpeta(salida, la_pagina.carpeta)


class TestEnConsolaLaCarpetaSiSirve:
    def test_el_aviso_dice_donde_se_ha_buscado(self, tmp_path):
        """Sin procedencia, la carpeta: es lo que hace falta para ponerlo."""
        from validador import esquema, formato

        carpeta = tmp_path / "esquemas"
        carpeta.mkdir()
        (carpeta / "otro.xsd").write_text("<x/>", encoding="utf-8")
        texto = respuesta(version="2.0").encode("utf-8")
        informe = esquema.validar(texto, Catalogo(carpeta))
        assert [i.codigo for i in informe.incidencias] == ["XSD-SIN-ESQUEMA"]
        assert informe.incidencias[0].mensaje.endswith(
            f"y se busca dentro de {carpeta}."
        )
        # Y `por_defecto`, que es lo que llama la consola, no trae ninguna.
        assert Catalogo.por_defecto(carpeta).procedencia == ""
        assert formato.detectar(texto).version == "2.0"

    def test_el_fichero_que_tumba_al_validador_sin_lote(self, tmp_path, monkeypatch):
        """`validar_archivo`, que no tiene nombres: el del fichero, sin ruta."""

        def revienta(*_a, **_k):
            raise KeyError("BT-99")

        monkeypatch.setattr(en16931, "reglas", revienta)
        camino = tmp_path / "f.xml"
        camino.write_bytes((RAIZ / "ejemplos" / "f-0001.xml").read_bytes())
        informe = factura.validar_archivo(camino)
        assert informe.resumen() == (
            "No se ha podido validar. El validador ha fallado con \"f.xml\"."
        )


class TestConComa:
    def test_ningun_decimal_sale_con_punto(self):
        """Todo `toFixed` con decimales de la web va seguido de la coma.

        `toFixed` no mira el idioma: devuelve «46.67» en cualquier navegador.
        La portada ya lo hacía bien con el tiempo del banco —`.replace(".",
        ",")`— y el arranque no. Esto no deja que uno nuevo se escriba sin
        ella. Solo se libra el cero escrito tal cual, que no tiene punto que
        cambiar: con una constante o con espacios dentro también se exige, y
        se mira en las subcarpetas, que la bitácora puede llevar sus scripts.
        """
        sueltos = []
        web = RAIZ / "web"
        for fichero in sorted([*web.rglob("*.html"), *web.rglob("*.js")]):
            texto = fichero.read_text(encoding="utf-8")
            for hallado in re.finditer(r"\.toFixed\(\s*([^)]*?)\s*\)", texto):
                if hallado.group(1) == "0":
                    continue
                detras = texto[hallado.end():hallado.end() + 20]
                if not detras.startswith('.replace(".", ",")'):
                    linea = texto.count("\n", 0, hallado.start()) + 1
                    sueltos.append(f"{fichero.relative_to(web)}:{linea}")
        assert not sueltos, f"decimales con punto en la web: {sueltos}"

    def test_el_arranque_y_el_banco_pasan_por_ahi(self):
        """Los dos que salían con punto: sin `toFixed`, la de arriba no los ve.

        Y en el arranque, que **todas** las cifras pasen por `seg`: con su
        definición bien y un `total: Math.round(…) / 1000` al final, la página
        volvía a decir «Listo en 46.672 s» con todo en verde. Lo midió la
        revisión.
        """
        codigo = GLOSA_JS.read_text(encoding="utf-8")
        assert 'const seg = (ms) => (ms / 1000).toFixed(2).replace(".", ",");' in codigo
        inicio = codigo.index("async function arrancarDeVerdad(avisar) {")
        cuerpo = codigo[inicio:codigo.index("\n}\n", inicio)]
        fases = re.findall(r'\bdecir\(\s*"[^"]*",\s*([^\n]*)', cuerpo)
        assert len(fases) >= 5, fases
        totales = re.findall(r"\btotal:\s*([^,\n]*)", cuerpo)
        assert totales, "el arranque ya no devuelve su total"
        for cifra in fases + totales:
            assert cifra.lstrip().startswith("seg("), cifra
        banco = (RAIZ / "web" / "banco.html").read_text(encoding="utf-8")
        assert 'r.ms.toFixed(1).replace(".", ",") + " ms' in banco
        assert "r.ms + " not in banco


# --- La revocación, y lo que no se puede hacer en la página -----------------
#
# Visto el 05-10-2026 con este mismo Python y una autoridad de prueba de ancla:
# el aviso de la revocación mandaba a «bájala y ponla en la carpeta de
# revocaciones», la columna de la firma decía «hace falta la lista de
# revocación de su autoridad» hasta al lado de un REVOCADO sacado de la lista
# que traía la factura, y la frase prometía «una autoridad de confianza
# instalada». En la página no hay carpeta, no se instala nada y no hay consola.

# Lo que la página no puede pedir ni decir, en minúsculas. «instalad» caza
# instalada, instaladas e instalado.
NO_SE_PUEDE_AQUI = (
    "almacén", "instalad", "python -m", "--montar", "carpeta de revocaciones",
    "bájala", "ponla en",
)


def _sin_lo_que_no_se_puede(salida: str) -> None:
    dichos = [
        (palabra, texto)
        for texto in _cadenas(json.loads(salida))
        for palabra in NO_SE_PUEDE_AQUI
        if palabra in texto.lower()
    ]
    assert not dichos, f"la página pide lo que no se puede hacer en ella: {dichos}"


@pytest.fixture
def con_anclas_de_prueba(la_pagina):
    """La página con la raíz y la intermedia de `test_cadena` entre sus anclas.

    Ninguna factura de muestra llega hoy a un ancla del paquete, así que sin
    esto la revocación no se mira nunca y no hay nada que ver.
    """
    from test_cadena import intermedia, raiz

    anclas = la_pagina.carpeta / "opt" / "factura-e" / "anclas"
    (anclas / "zz-raiz-de-prueba.cer").write_bytes(raiz())
    (anclas / "zz-intermedia-de-prueba.cer").write_bytes(intermedia())
    return la_pagina


def _firmada_con_su_lista_en(url: str) -> bytes:
    from test_cadena import HOJA, HOY, hoja
    from test_firma import documento
    from test_revocacion import _puntos

    return documento(
        cert=hoja(extensiones=_puntos(url)),
        modulo=HOJA[0],
        privada=HOJA[1],
        firmado_el=HOY,
    )


def _la_firma(salida: str) -> dict:
    return {p["nombre"]: p for p in json.loads(salida)["partes"]}["La firma"]


class TestLaRevocacionEnLaPagina:
    def test_sin_prueba_dentro_no_manda_a_ninguna_carpeta(self, con_anclas_de_prueba):
        salida = con_anclas_de_prueba(
            {"f.xml": _firmada_con_su_lista_en("http://pki.ejemplo.es/ca.crl")}
        )
        [aviso] = _incidencias(salida, "REVOCACION-SIN-COMPROBAR")
        assert "http://pki.ejemplo.es/ca.crl" not in aviso["mensaje"]
        assert "no trae dentro la lista de revocación" in aviso["mensaje"]
        firma = _la_firma(salida)
        assert "si está anulado el certificado de este documento" in firma["sin_mirar"]
        assert "hace falta la lista" not in salida
        _sin_lo_que_no_se_puede(salida)

    def test_con_la_lista_dentro_se_apunta_la_revocacion(self, con_anclas_de_prueba):
        from datetime import timedelta

        from test_cadena import HOY
        from test_revocacion import con_lista_dentro, lista

        firmada = _firmada_con_su_lista_en("http://pki.ejemplo.es/ca.crl")
        datos = con_lista_dentro(firmada, lista(desde=HOY + timedelta(hours=1)))
        salida = con_anclas_de_prueba({"f.xml": datos})
        assert _incidencias(salida, "CONFIANZA-REVOCACION")
        assert not _incidencias(salida, "REVOCACION-LISTA-VIEJA")
        firma = _la_firma(salida)
        assert "que no lo hayan anulado" in firma["mirado"]
        assert "si está anulado el certificado" not in firma["sin_mirar"]
        _sin_lo_que_no_se_puede(salida)

    def test_con_un_revocado_no_dice_que_falte_la_lista(self, con_anclas_de_prueba):
        from datetime import timedelta

        from test_cadena import HOY
        from test_revocacion import HOJA_SERIE, _linea, con_lista_dentro, lista

        anulada = lista(
            desde=HOY + timedelta(hours=1),
            lineas=[_linea(HOJA_SERIE, HOY - timedelta(days=3))],
        )
        firmada = _firmada_con_su_lista_en("http://pki.ejemplo.es/ca.crl")
        salida = con_anclas_de_prueba({"f.xml": con_lista_dentro(firmada, anulada)})
        assert _incidencias(salida, "REVOCADO")
        firma = _la_firma(salida)
        assert "si está anulado el certificado" not in firma["sin_mirar"]
        assert "hace falta la lista" not in salida
        _sin_lo_que_no_se_puede(salida)


def test_la_portada_no_promete_la_revocacion_instalada():
    """«si el documento trae la prueba o la tienes instalada», y en la página no
    se puede instalar nada. Lo mismo en la pregunta de por qué no lo sabe."""
    portada = " ".join((RAIZ / "web" / "index.html").read_text(encoding="utf-8").split())
    assert "tienes instalada" not in portada
    assert "si hay lista" not in portada


def test_nada_de_lo_que_recibe_la_pagina_pide_instalar(la_pagina, monkeypatch):
    """Ni almacén, ni instalar, ni órdenes de consola, con lo que trae la portada.

    `fe-0001.xml` salía con «Puede ser que falte un certificado en el almacén».
    Y con el paquete sin llegar, la queja de las anclas decía dónde se
    instalan, que en la página es una carpeta de su disco virtual.
    """
    ficheros = {
        camino.name: camino.read_bytes()
        for camino in sorted((RAIZ / "ejemplos").iterdir())
        if camino.suffix in (".xml", ".edi")
    }
    _sin_lo_que_no_se_puede(la_pagina(ficheros))
    # El paquete que no llega: las variables que pone `traerPaquete` apuntan a
    # carpetas vacías, y la página arma su almacén igual.
    vacia = la_pagina.carpeta / "vacia"
    vacia.mkdir()
    for variable in ("FACTURAE_ESQUEMAS", "FACTURAE_ANCLAS", "FACTURAE_ANCLAS_SELLOS"):
        monkeypatch.setenv(variable, str(vacia))
    salida = la_pagina({"fe-0001.xml": (RAIZ / "ejemplos" / "fe-0001.xml").read_bytes()})
    [sin_anclas] = _incidencias(salida, "CADENA-SIN-ANCLAS")
    assert "recargarla las vuelve a pedir" in sin_anclas["mensaje"]
    _sin_lo_que_no_se_puede(salida)
    _sin_la_carpeta(salida, la_pagina.carpeta)


def test_la_procedencia_de_la_pagina_lleva_tilde(la_pagina):
    """«que viene con esta pagina», en cada firma que llega a un ancla.

    Es texto del informe escrito dentro de un fichero cuyos comentarios van sin
    tildes, y se contagió. Sale en CONFIANZA-ANCLA y en SELLO-CONFIANZA.

    Ningún ejemplo de aquí lleva una firma que llegue a un ancla del paquete,
    así que se pregunta al almacén que ha armado la página, con un ancla de
    verdad de cada uno: el de firma y el de sellado, que hereda la procedencia.
    """
    informe = _informe_de_la_pagina()
    assert "esta pagina" not in informe
    la_pagina({"f.xml": (RAIZ / "ejemplos" / "f-0001.xml").read_bytes()})
    almacen = la_pagina.espacio["_a"]
    for cual in (almacen, almacen.sellos):
        procedencia = cual.procedencia_de(cual.todas()[0])
        assert procedencia.startswith("que viene con esta página, de la lista"), (
            procedencia
        )
    assert la_pagina.espacio["_c"].procedencia == "que vienen con esta página"
