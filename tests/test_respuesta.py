"""Un `ApplicationResponse` de UBL: se reconoce, se le mira la forma, y nada más.

Nada más salvo que sea uno de los mensajes de la orden, por su código: a esos
se les mide además su tabla desde el 12-10-2026, y eso está en
`test_mensajes.py`. Las respuestas de aquí llevan `AP`, que no es de la orden,
y por eso lo de este fichero sigue valiendo tal cual.

Hasta el 29-09-2026 un `ApplicationResponse` salía «No se ha podido validar.
XML válido, pero su elemento raíz no corresponde a Facturae, UBL, CII ni
EDIFACT»: igual si estaba bien que si estaba roto. Reconocerlo tiene dos
maneras de salir mal, y las dos se midieron antes de escribir nada:

- **Como factura.** Con `familia=UBL`, una respuesta que valida contra su
  esquema recibía 16 errores que no le tocan: `XSD-RAIZ`, 13 reglas `BR-*` y dos
  `CU-*`. Es el «acusar en falso» de HALLAZGOS.md.
- **Como nada.** Con una familia nueva que no se parsea, la respuesta con la
  forma rota salía «1 correcto(s)» y código de salida 0, con la columna de la
  forma diciendo «Sin errores». Absolver en silencio es peor que acusar.

Cada guardia de aquí tiene su prueba, y cada una se ha visto ponerse en rojo
quitando la guardia (ver HALLAZGOS.md). Los esquemas salen de `web/paquete.zip`
—ver la fixture `esquemas_del_paquete`— y no de `esquemas/`, así que las pruebas
corren también en GitHub.
"""

import ast
from pathlib import Path

import pytest

from validador import __main__ as consola
from validador import (
    codigo_unico,
    en16931,
    esquema,
    factura,
    formato,
    cius_es,
    sintaxis,
    solucion_publica,
)
from validador.esquema import Catalogo
from validador.formato import (
    EDIFACT,
    FACTURAE,
    RESPUESTA,
    UBL,
    detectar,
)
from validador.incidencias import Informe

RAIZ = Path(__file__).resolve().parent.parent

PERFIL_CIUS = "urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0"
PERFIL_DE_LA_ORDEN = cius_es.ESPECIFICACION
PERFIL_EN16931 = "urn:cen.eu:en16931:2017"


def respuesta(
    *,
    version: str | None = "2.5",
    perfil: str | None = None,
    identificador: str = "R-2026-0001",
    de_mas: str = "",
    antes: str = "",
) -> str:
    """Una respuesta mínima que valida contra `UBL-ApplicationResponse-2.5.xsd`."""
    partes = []
    if version:
        partes.append(f"<cbc:UBLVersionID>{version}</cbc:UBLVersionID>")
    if perfil:
        partes.append(f"<cbc:CustomizationID>{perfil}</cbc:CustomizationID>")
    partes.append(f"<cbc:ID>{identificador}</cbc:ID>")
    partes.append("<cbc:IssueDate>2026-10-02</cbc:IssueDate>")
    return f"""<?xml version="1.0" encoding="UTF-8"?>{antes}
<ApplicationResponse xmlns="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  {"".join(partes)}{de_mas}
  <cac:SenderParty>
    <cac:PartyLegalEntity><cbc:RegistrationName>Emisor SL</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:SenderParty>
  <cac:ReceiverParty>
    <cac:PartyLegalEntity><cbc:RegistrationName>Receptor SA</cbc:RegistrationName></cac:PartyLegalEntity>
  </cac:ReceiverParty>
  <cac:DocumentResponse>
    <cac:Response><cbc:ResponseCode>AP</cbc:ResponseCode></cac:Response>
    <cac:DocumentReference><cbc:ID>F-2026-0001</cbc:ID></cac:DocumentReference>
  </cac:DocumentResponse>
</ApplicationResponse>"""


@pytest.fixture
def catalogo(esquemas_del_paquete):
    return Catalogo(esquemas_del_paquete)


@pytest.fixture
def sin_esquemas(tmp_path):
    return Catalogo(tmp_path / "no-hay-esquemas")


def codigos(informe: Informe) -> list[str]:
    return [i.codigo for i in informe.incidencias]


def escribir(carpeta: Path, nombre: str, texto: str | bytes) -> Path:
    ruta = carpeta / nombre
    if isinstance(texto, str):
        texto = texto.encode("utf-8")
    ruta.write_bytes(texto)
    return ruta


# --- Se reconoce -------------------------------------------------------------


class TestSeReconoce:
    def test_una_respuesta_2_5(self):
        d = detectar(respuesta())
        assert d.familia == RESPUESTA
        assert d.version == "2.5"
        assert d.tipo_documento is None  # ni factura ni abono
        assert d.resumen() == "ApplicationResponse v2.5"

    def test_sin_version_se_supone_la_2_1_como_en_las_facturas(self):
        assert detectar(respuesta(version=None)).version == "2.1"

    def test_sin_version_y_con_otro_perfil_tambien_la_2_1(self):
        """Solo un identificador de la AEAT sube la suposición a la 2.5."""
        d = detectar(respuesta(version=None, perfil=PERFIL_EN16931))
        assert d.version == "2.1"

    def test_sin_version_pero_con_el_cius_de_la_solucion_publica_es_la_2_5(self):
        """Solo existe sobre UBL 2.5: suponerle la 2.1 sería medirla mal."""
        d = detectar(respuesta(version=None, perfil=PERFIL_CIUS))
        assert d.version == "2.5"
        assert "solo existe sobre UBL 2.5" in d.motivo

    def test_sin_version_y_con_el_identificador_de_la_orden_tambien_la_2_5(self):
        """Una sola regla para todo lo que es UBL, también con el de la orden."""
        d = detectar(respuesta(version=None, perfil=PERFIL_DE_LA_ORDEN))
        assert d.version == "2.5"
        assert "solo existe sobre UBL 2.5" in d.motivo

    def test_no_dice_seguir_la_en_16931_aunque_lleve_el_perfil_de_una_factura(self):
        """Declarar el perfil de una factura no la hace factura: la norma no se
        le aplica."""
        d = detectar(respuesta(perfil=PERFIL_EN16931))
        assert d.perfil == PERFIL_EN16931
        assert d.conforme_en16931 is False
        assert "EN 16931" not in d.resumen()

    def test_otro_documento_de_ubl_sigue_sin_reconocerse(self):
        """Solo se reconoce lo que se sabe mirar: no «todo lo que sea UBL»."""
        pedido = (
            '<Order xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2"/>'
        )
        d = detectar(pedido)
        assert not d
        # Y no se le dice que no es UBL, que lo es: se le dice qué se valida.
        assert "no es de ningún documento que se valide aquí" in d.motivo
        assert "respuestas ApplicationResponse de UBL" in d.motivo

    @pytest.mark.parametrize(
        "raiz",
        [
            # Otro documento de UBL que también es una respuesta, de pedido.
            '<OrderResponse xmlns="urn:oasis:names:specification:ubl:schema:xsd:'
            'OrderResponse-2"/>',
            # El nombre de una respuesta sin su namespace, o con el de otro.
            "<ApplicationResponse/>",
            '<ApplicationResponse xmlns="urn:oasis:names:specification:ubl:schema:'
            'xsd:Invoice-2"/>',
            # Una factura con el namespace de la respuesta.
            '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:'
            'ApplicationResponse-2"/>',
        ],
    )
    def test_se_reconoce_por_el_nombre_y_el_namespace_a_la_vez(self, raiz):
        """Con cualquiera de los dos solo, se acusaría con reglas que no le tocan.

        Medido con el reconocimiento ensanchado: un `OrderResponse` válido salía
        con `XSD-RAIZ`, un error de forma sobre un documento que está bien.
        """
        assert detectar(raiz).familia is None

    @pytest.mark.parametrize(
        "raiz, esperado",
        [
            ("<ApplicationResponse/>", formato.NS_UBL_RESPUESTA),
            (
                '<ApplicationResponse xmlns="urn:oasis:names:specification:ubl:'
                'schema:xsd:Invoice-2"/>',
                formato.NS_UBL_RESPUESTA,
            ),
            (
                '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:'
                'ApplicationResponse-2"/>',
                formato.NS_UBL_FACTURA,
            ),
        ],
    )
    def test_con_el_nombre_bien_y_el_namespace_mal_se_dice_el_namespace(
        self, raiz, esperado
    ):
        """Decirle que la raíz no es de nada que se valide manda a otro sitio."""
        motivo = detectar(raiz).motivo
        assert "namespace" in motivo
        if "xmlns" in raiz:
            assert f"y tendría que ser {esperado}." in motivo
        else:
            assert f"no lleva namespace, y tendría que llevar {esperado}." in motivo

    def test_la_firma_se_ve(self):
        firmada = respuesta(
            de_mas='<ds:Signature xmlns:ds="http://www.w3.org/2000/09/xmldsig#"/>'
        )
        assert detectar(firmada).firmado


# --- No se le acusa de ser una factura ----------------------------------------


class TestNoSeLeAcusaDeSerUnaFactura:
    def test_una_respuesta_que_valida_sale_limpia(self, catalogo):
        informe = factura.validar(respuesta(), catalogo=catalogo)
        assert informe.incidencias == [], informe.detalle()
        assert informe.validado and informe.conforme

    @pytest.mark.parametrize("perfil", [
        PERFIL_EN16931, PERFIL_CIUS, PERFIL_DE_LA_ORDEN,
        "urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:2.0.0:extended", None])
    def test_ni_con_el_perfil_de_una_factura_ni_con_el_del_cius(self, catalogo, perfil):
        """Ni `BR-*`, ni `CU-*`, ni `PERFIL-*`, ni `SPFE-*`: nada de facturas.

        Tampoco el aviso de un identificador de la AEAT que no se conoce: el
        anexo no mide respuestas, y avisar de que no se le ha aplicado sería
        dar a entender que se le habría aplicado.
        """
        informe = factura.validar(respuesta(perfil=perfil), catalogo=catalogo)
        assert informe.incidencias == [], informe.detalle()

    def test_las_reglas_europeas_no_le_tocan_aunque_alguien_amplie_el_mapa(
        self, monkeypatch
    ):
        """La guardia va antes del mapa a propósito.

        Si `SINTAXIS` ganara una clave que nombrara a la respuesta, sin esta
        prueba la guardia seguiría «funcionando» solo por no encontrarla.
        """
        # Se parchea el mapa de `sintaxis`, que es el objeto de verdad: `en16931`
        # lo importa y no tiene que seguir reexportándolo para que esto pruebe.
        monkeypatch.setitem(sintaxis.SINTAXIS, RESPUESTA, sintaxis.SINTAXIS[UBL])
        datos = respuesta().encode()
        d = detectar(datos)
        assert en16931.reglas(None, d) == []

    def test_el_anexo_i_no_mide_una_respuesta(self):
        """Ni siquiera con el CIUS declarado: el anexo mide facturas.

        Sin la guardia recibía `SPFE-SINTAXIS`, «el anexo solo define el CIUS
        sobre UBL», que es falso: la respuesta es UBL.
        """
        d = detectar(respuesta(perfil=PERFIL_CIUS))
        assert solucion_publica.declara_el_cius(d)
        assert solucion_publica.reglas(None, d) == []

    def test_el_codigo_unico_no_le_saca_un_cu_00(self):
        informe = codigo_unico.validar(respuesta())
        assert informe.incidencias == []

    def test_dos_respuestas_seguidas_no_hacen_una_serie_con_huecos(
        self, tmp_path, catalogo
    ):
        rutas = [
            escribir(tmp_path, "r1.xml", respuesta(identificador="AR-0001")),
            escribir(tmp_path, "r3.xml", respuesta(identificador="AR-0003")),
            escribir(tmp_path, "r3-bis.xml", respuesta(identificador="AR-0003")),
        ]
        lote = factura.validar_lote(rutas, catalogo=catalogo)
        assert lote.cruzadas == []
        assert lote.conforme

    def test_las_facturas_no_cambian_por_ir_con_respuestas(self, tmp_path, catalogo):
        """La prueba de que nada se ha movido en lo de antes."""
        facturas = sorted((RAIZ / "ejemplos").glob("*.xml"))
        solas = factura.validar_lote(facturas, catalogo=catalogo)
        mezcla = factura.validar_lote(
            [*facturas, escribir(tmp_path, "r.xml", respuesta())], catalogo=catalogo
        )
        assert [i.detalle() for _, i in solas.informes] == [
            i.detalle() for _, i in mezcla.informes[: len(facturas)]
        ]
        assert solas.cruzadas == mezcla.cruzadas


# --- Se le mira la forma ------------------------------------------------------


class TestSeLeMiraLaForma:
    def test_con_un_elemento_de_mas_sale_un_error_de_forma(self, catalogo):
        rota = respuesta().replace(
            "<cbc:IssueDate>2026-10-02</cbc:IssueDate>",
            "<cbc:IssueDate>2026-10-02</cbc:IssueDate>"
            "<cbc:IssueDate>2026-10-03</cbc:IssueDate>",
        )
        informe = factura.validar(rota, catalogo=catalogo)
        assert "XSD-ORDEN" in codigos(informe)
        assert not informe.conforme

    def test_una_fecha_imposible_se_traduce(self, catalogo):
        rota = respuesta().replace("2026-10-02", "2026-02-31")
        informe = factura.validar(rota, catalogo=catalogo)
        assert codigos(informe) == ["XSD-TIPO"]
        assert "febrero de 2026 tiene 28 días" in informe.incidencias[0].mensaje

    @pytest.mark.parametrize("version", ["2.1", "2.2", "2.3", "2.4"])
    def test_las_de_2_1_a_2_4_se_miden_con_el_esquema_2_5(self, catalogo, version):
        """Se sube: está medido (HALLAZGOS.md) que no hay violaciones al subir.

        En el paquete solo está el 2.5. Una respuesta de Peppol declara la 2.1
        y con esto se comprueba en vez de quedarse sin mirar.
        """
        informe = factura.validar(respuesta(version=version), catalogo=catalogo)
        assert informe.incidencias == [], informe.detalle()
        assert informe.validado

    def test_de_la_2_0_no_se_sube_y_no_se_da_por_buena(self, catalogo):
        """Medido: `ExtensionContent` cambió entre la 2.0 y la 2.1.

        Sin `UBL-ApplicationResponse-2.0.xsd` no se mide. Y como la forma es lo
        único que se le comprueba a una respuesta sin firma, no medirla es no
        haber comprobado nada: no puede salir «correcta».
        """
        informe = factura.validar(respuesta(version="2.0"), catalogo=catalogo)
        assert codigos(informe) == ["XSD-SIN-ESQUEMA"]
        assert "UBL-ApplicationResponse-2.0.xsd" in informe.incidencias[0].mensaje
        assert not informe.validado

    def test_una_version_que_no_conocemos_pide_la_suya(self, catalogo):
        informe = factura.validar(respuesta(version="2.9"), catalogo=catalogo)
        assert codigos(informe) == ["XSD-SIN-ESQUEMA"]
        assert "UBL-ApplicationResponse-2.9.xsd" in informe.incidencias[0].mensaje

    def test_entidades_en_el_prologo_se_dicen_y_no_revientan(self, catalogo):
        """Sin que la respuesta pase por el árbol, ni siquiera se vería."""
        antes = '\n<!DOCTYPE ApplicationResponse [<!ENTITY r "R-1">]>'
        informe = factura.validar(
            respuesta(antes=antes).replace("R-2026-0001", "&r;"), catalogo=catalogo
        )
        assert "XML-ENTIDADES" in codigos(informe)
        assert "VALIDADOR-SE-ATRAGANTA" not in codigos(informe)


# --- Y la firma ---------------------------------------------------------------


class TestSiVaFirmada:
    """`_FAMILIAS_XML` decide si la respuesta pasa por el árbol, y con él, la firma.

    Medido: con la familia fuera de esa lista, una respuesta tocada después de
    firmar salía «correcta».
    """

    @pytest.fixture
    def firmadas(self, monkeypatch):
        import test_firma as tf

        monkeypatch.setattr(
            tf,
            "CUERPO",
            """<?xml version="1.0" encoding="UTF-8"?>
<ApplicationResponse xmlns="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:UBLVersionID>2.5</cbc:UBLVersionID>
  <cbc:ID>R-1</cbc:ID>
  <cbc:IssueDate>2026-03-01</cbc:IssueDate>
  <cbc:Note>{total}</cbc:Note>
</ApplicationResponse>""",
        )
        bueno = tf.documento(total="121.00")
        tocado = bueno.replace(b"<cbc:Note>121.00", b"<cbc:Note>999.00")
        assert bueno != tocado
        return bueno, tocado

    def test_una_respuesta_tocada_despues_de_firmar_lo_dice(
        self, firmadas, sin_esquemas
    ):
        _, tocado = firmadas
        informe = factura.validar(tocado, catalogo=sin_esquemas)
        assert detectar(tocado).firmado
        assert "FIRMA-ALTERADA" in {i.codigo for i in informe.errores}
        assert not informe.conforme

    def test_y_la_buena_queda_con_la_firma_en_pie(self, firmadas, sin_esquemas):
        bueno, _ = firmadas
        informe = factura.validar(bueno, catalogo=sin_esquemas)
        assert informe.firma == formato.FIRMA_EN_PIE
        assert not informe.errores

    def test_la_buena_sin_esquema_sigue_sin_estar_comprobada(
        self, firmadas, sin_esquemas, tmp_path
    ):
        """Una firma en pie no es la forma: sin esquema, SIN COMPROBAR igual.

        Lo que se ha visto de ella es que nadie la ha tocado, no que esté bien
        escrita. Por los dos caminos, que cada uno calcula lo suyo.
        """
        bueno, _ = firmadas
        assert not factura.validar(bueno, catalogo=sin_esquemas).validado
        lote = factura.validar_lote(
            [escribir(tmp_path, "r.xml", bueno)], catalogo=sin_esquemas
        )
        assert "0 correcto(s)" in lote.resumen()
        assert "1 SIN COMPROBAR" in lote.resumen()

    def test_la_tocada_sin_esquema_se_cuenta_con_errores(
        self, firmadas, sin_esquemas, tmp_path
    ):
        """Un error encontrado es un veredicto, aunque la forma no se mirara.

        Medido antes de arreglarlo: el lote decía «0 con errores · 1 SIN
        COMPROBAR» encima del propio `FIRMA-ALTERADA`, y la línea del fichero
        decía «no se ha podido comprobar» sin nombrar el error.
        """
        _, tocado = firmadas
        informe = factura.validar(tocado, catalogo=sin_esquemas)
        assert informe.validado and not informe.conforme
        assert "1 error(es)" in informe.resumen()
        assert "la forma no se ha podido comprobar" in informe.resumen()
        lote = factura.validar_lote(
            [escribir(tmp_path, "r.xml", tocado)], catalogo=sin_esquemas
        )
        assert "0 correcto(s) · 1 con errores." in lote.resumen()
        assert not lote.sin_comprobar

    def test_la_columna_de_la_forma_no_dice_edifact(self, firmadas, sin_esquemas, tmp_path):
        """Sin esquema, la forma de una respuesta firmada queda «Sin mirar»."""
        bueno, _ = firmadas
        lote = factura.validar_lote(
            [escribir(tmp_path, "r.xml", bueno)], catalogo=sin_esquemas
        )
        forma = {p.nombre: p for p in lote.partes(forma=False)}["La forma"]
        assert forma.resultado == "Sin mirar"
        assert "EDIFACT" not in forma.sin_mirar


# --- Sin esquema no hay comprobación ninguna ----------------------------------


class TestSinEsquemaNoEsCorrecta:
    """De una respuesta solo se mira la forma: sin esquema no se mira nada.

    Medido antes de escribirlo: con `esquemas/` vacío —el caso por defecto del
    CLI— una respuesta con la forma rota salía «1 correcto(s)» y código de
    salida 0, con «No se ha comprobado nada» escrito justo debajo.
    """

    ROTA = respuesta().replace(
        "<cbc:IssueDate>2026-10-02</cbc:IssueDate>",
        "<cbc:IssueDate>2026-10-02</cbc:IssueDate><cbc:IssueDate>x</cbc:IssueDate>",
    )

    def test_el_informe_no_la_da_por_correcta(self, sin_esquemas):
        informe = factura.validar(self.ROTA, catalogo=sin_esquemas)
        assert informe.mirado is False
        assert not informe.validado
        # Entera: la promesa es la frase, no su principio.
        assert informe.resumen() == (
            "ApplicationResponse v2.5: no se ha podido comprobar, porque no hay "
            "un esquema que se pueda usar para mirar su forma."
        )

    def test_el_lote_la_cuenta_como_sin_comprobar(self, tmp_path, sin_esquemas):
        ruta = escribir(tmp_path, "r.xml", self.ROTA)
        lote = factura.validar_lote([ruta], catalogo=sin_esquemas)
        assert len(lote.sin_comprobar) == 1
        assert not lote.conforme
        assert lote.resumen() == (
            "1 fichero(s) · 0 correcto(s) · 0 con errores · 1 SIN COMPROBAR."
        )
        # «Leer como factura», que decía antes, sería falso de una respuesta.
        assert lote.alcance() == (
            "No se ha comprobado nada: ninguno de los ficheros se ha podido "
            "comprobar."
        )

    def test_la_funcion_de_solo_la_forma_tampoco(self, sin_esquemas):
        """`esquema.validar` es pública, y de ella no se espera otra cosa."""
        assert not esquema.validar(self.ROTA, sin_esquemas).validado

    def test_la_consola_sale_con_1(self, tmp_path):
        ruta = escribir(tmp_path, "r.xml", self.ROTA)
        assert consola.main([str(ruta), "--esquemas", str(tmp_path / "nada")]) == 1

    def test_una_factura_en_las_mismas_condiciones_sigue_siendo_correcta(
        self, sin_esquemas
    ):
        """La otra mitad: con una factura, sin esquemas aún se le miden las
        cuentas y el código único. No se ha tocado."""
        ejemplo = (RAIZ / "ejemplos" / "f-0001.xml").read_bytes()
        informe = factura.validar(ejemplo, catalogo=sin_esquemas)
        assert informe.mirado and informe.validado

    def test_con_el_esquema_de_otra_version_tampoco(self, tmp_path, esquemas_del_paquete):
        """Un catálogo con Invoice y CreditNote pero sin `ApplicationResponse`.

        Es lo que trae la carpeta `ubl/` de `web/paquete.zip`, la de la 2.1: hay
        esquemas, y ninguno sirve para esto.
        """
        carpeta = tmp_path / "solo-facturas"
        for ruta in esquemas_del_paquete.rglob("*.xsd"):
            if "ApplicationResponse" not in ruta.name:
                destino = carpeta / ruta.relative_to(esquemas_del_paquete)
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_bytes(ruta.read_bytes())
        informe = factura.validar(respuesta(), catalogo=Catalogo(carpeta))
        assert codigos(informe) == ["XSD-SIN-ESQUEMA"]
        assert not informe.validado

    def test_con_su_esquema_roto_tampoco(self, tmp_path, esquemas_del_paquete):
        """Que el fichero esté no basta: tiene que compilar.

        Es la mitad de `se_puede_comprobar` que ninguna prueba de facturas
        fija, porque a una factura con el esquema roto aún le quedan las cuentas
        y sigue validada. Con «basta con que esté», una respuesta con su XSD a
        medias salía correcta sin que nadie le mirara la forma.
        """
        carpeta = tmp_path / "roto"
        for ruta in esquemas_del_paquete.rglob("*.xsd"):
            destino = carpeta / ruta.relative_to(esquemas_del_paquete)
            destino.parent.mkdir(parents=True, exist_ok=True)
            contenido = ruta.read_bytes()
            if ruta.name == "UBL-ApplicationResponse-2.5.xsd":
                contenido = contenido[: len(contenido) // 2]  # una descarga a medias
            destino.write_bytes(contenido)
        informe = factura.validar(respuesta(), catalogo=Catalogo(carpeta))
        assert codigos(informe) == ["XSD-ESQUEMA-ROTO"]
        assert not informe.validado
        assert "no hay un esquema que se pueda usar" in informe.resumen()

    def test_su_esquema_se_compila_una_vez(self, monkeypatch, esquemas_del_paquete):
        """Las reglas y `_mirado` usan el mismo catálogo.

        Medido antes de juntarlos: sin catálogo, `validar` compilaba dos veces
        el esquema de una respuesta, uno por cada `Catalogo.por_defecto()`.
        """
        from lxml import etree

        monkeypatch.setenv(esquema.VARIABLE_ENTORNO, str(esquemas_del_paquete))
        original = etree.XMLSchema
        compilados = []

        def contando(*args, **kwargs):
            compilados.append(1)
            return original(*args, **kwargs)

        monkeypatch.setattr(esquema.etree, "XMLSchema", contando)
        informe = factura.validar(respuesta())
        assert informe.validado and not informe.incidencias, informe.detalle()
        assert len(compilados) == 1


# --- Lo que el informe promete -------------------------------------------------


class TestLoQueElInformeDice:
    def test_de_una_respuesta_solo_se_promete_la_forma(self, tmp_path, catalogo):
        lote = factura.validar_lote(
            [escribir(tmp_path, "r.xml", respuesta())], catalogo=catalogo
        )
        frase = lote.alcance()
        assert "la forma contra el esquema XSD" in frase
        # Lo que se promete de una factura, no de esto:
        assert "las reglas EN 16931" not in frase
        assert "código único" not in frase
        assert "el contenido de las respuestas (ApplicationResponse)" in frase

    def test_las_columnas_lo_dicen_igual(self, tmp_path, catalogo):
        lote = factura.validar_lote(
            [escribir(tmp_path, "r.xml", respuesta())], catalogo=catalogo
        )
        partes = {p.nombre: p for p in lote.partes()}
        assert partes["La forma"].resultado == "Sin errores"
        assert partes["El contenido"].resultado == "Sin mirar"
        assert "respuestas (ApplicationResponse)" in partes["El contenido"].sin_mirar

    def test_en_un_lote_mixto_las_facturas_siguen_prometiendo_lo_suyo(
        self, tmp_path, catalogo
    ):
        ejemplo = (RAIZ / "ejemplos" / "f-0001.xml").read_bytes()
        lote = factura.validar_lote(
            [
                escribir(tmp_path, "f.xml", ejemplo),
                escribir(tmp_path, "r.xml", respuesta()),
            ],
            catalogo=catalogo,
        )
        frase = lote.alcance()
        assert "las reglas EN 16931" in frase
        assert "el contenido de las respuestas (ApplicationResponse)" in frase

    def test_un_lote_de_respuestas_sin_su_esquema_no_promete_la_forma(
        self, tmp_path, sin_esquemas
    ):
        lote = factura.validar_lote(
            [escribir(tmp_path, "r.xml", respuesta())], catalogo=sin_esquemas
        )
        assert "la forma contra el esquema XSD" not in lote.alcance(forma=True)

    def test_la_frase_entera_de_una_respuesta(self, tmp_path, catalogo):
        """Lo que se promete, entero: ni «y la firma» sin firma, ni de más."""
        lote = factura.validar_lote(
            [escribir(tmp_path, "r.xml", respuesta())], catalogo=catalogo
        )
        assert lote.alcance() == (
            "Que no haya errores quiere decir que se ha comprobado la forma "
            "contra el esquema XSD.\nNo se comprueba la validez de las firmas "
            "electrónicas, ni el contenido de las respuestas (ApplicationResponse), "
            "ni si lo que dice la factura es cierto."
        )

    def test_con_una_respuesta_mirada_y_otra_sin_esquema(self, tmp_path, catalogo):
        """Alguna y no todas: con el mismo criterio que las facturas.

        La 2.0 no se mide y sale SIN COMPROBAR, así que el lote no puede salir
        «sin errores»; la frase de la forma sigue siendo cierta de la otra.
        """
        lote = factura.validar_lote(
            [
                escribir(tmp_path, "r25.xml", respuesta()),
                escribir(tmp_path, "r20.xml", respuesta(version="2.0")),
            ],
            catalogo=catalogo,
        )
        assert "la forma contra el esquema XSD" in lote.alcance()
        assert "1 SIN COMPROBAR" in lote.resumen()
        assert not lote.conforme

    def test_sin_esquemas_la_consola_no_promete_la_forma_de_nadie(
        self, tmp_path, sin_esquemas
    ):
        """Es lo que hace la consola sin `esquemas/`: `forma=False`."""
        ejemplo = (RAIZ / "ejemplos" / "f-0001.xml").read_bytes()
        lote = factura.validar_lote(
            [
                escribir(tmp_path, "f.xml", ejemplo),
                escribir(tmp_path, "r.xml", respuesta()),
            ],
            catalogo=sin_esquemas,
        )
        assert "la forma" not in lote.alcance(forma=False).split("\n")[0]

    def test_con_el_cius_declarado_no_se_promete_el_anexo(self, tmp_path, catalogo):
        """El anexo I no se le pasa a una respuesta: la frase no puede decirlo."""
        lote = factura.validar_lote(
            [escribir(tmp_path, "r.xml", respuesta(perfil=PERFIL_CIUS))],
            catalogo=catalogo,
        )
        assert "anexo I" not in lote.alcance()
        assert all("anexo I" not in p.mirado for p in lote.partes())

    def test_informe_a_mano_sin_mirar_no_esta_validado(self):
        """`mirado` por defecto es True: lo de antes no cambia."""
        d = detectar(respuesta())
        assert Informe(deteccion=d).validado
        assert not Informe(deteccion=d, mirado=False).validado


# --- Que no se pueda añadir una familia sin enterarse ----------------------------


class TestNadieSeOlvidaDeUnaFamilia:
    def test_toda_familia_que_detecta_formato_pasa_por_el_arbol(self):
        """Una familia de XML que falte en `_FAMILIAS_XML` no falla: absuelve.

        Se lee `formato.py` y se recogen todas las familias con que se construye
        una `Deteccion`; ninguna puede quedarse fuera de la lista del
        orquestador, salvo EDIFACT, que tiene su propio camino. Es la negativa
        de la casa: la próxima familia que alguien añada no se puede montar sin
        enterarse.
        """
        fuente = (RAIZ / "validador" / "formato.py").read_text(encoding="utf-8")
        usadas, a_mano = set(), []
        for nodo in ast.walk(ast.parse(fuente)):
            # Por posición la familia no se ve: se exige que vaya con nombre.
            if (
                isinstance(nodo, ast.Call)
                and getattr(nodo.func, "id", None) == "Deteccion"
                and nodo.args
            ):
                a_mano.append(f"línea {nodo.lineno}: Deteccion por posición")
            if isinstance(nodo, ast.keyword) and nodo.arg == "familia":
                if isinstance(nodo.value, ast.Name):
                    usadas.add(nodo.value.id)
                else:
                    # Un literal, un atributo, una llamada: no se sabe cuál es,
                    # y no saberlo es justo lo que esta prueba no puede dejar
                    # pasar. Medido: `familia="Order"` pasaba en verde.
                    a_mano.append(
                        f"línea {nodo.lineno}: familia={ast.unparse(nodo.value)}"
                    )
        assert not a_mano, (
            "familias que esta prueba no puede ver; escríbelas con una constante "
            f"de formato.py: {a_mano}"
        )
        assert {"FACTURAE", "UBL", "CII", "EDIFACT", "RESPUESTA"} <= usadas
        conocidas = {
            "FACTURAE": FACTURAE,
            "UBL": UBL,
            "CII": formato.CII,
            "EDIFACT": EDIFACT,
            "RESPUESTA": RESPUESTA,
            "ACUSE": formato.ACUSE,
        }
        desconocidas = usadas - set(conocidas)
        assert not desconocidas, (
            f"{sorted(desconocidas)} es una familia nueva: añádela a "
            "`factura._FAMILIAS_XML` (o justifica por qué no) y a esta prueba"
        )
        for nombre in usadas:
            familia = conocidas[nombre]
            assert familia == EDIFACT or familia in factura._FAMILIAS_XML, (
                f"la familia {familia} no está en `factura._FAMILIAS_XML`: "
                "sus documentos saldrían «correctos» sin haberse abierto"
            )

    def test_toda_familia_de_xml_tiene_esquema_que_pedir(self):
        for familia in factura._FAMILIAS_XML:
            d = formato.Deteccion(familia=familia, version="2.5", tipo_documento="factura")
            assert esquema._nombres_esperados(d), (
                f"{familia} no dice qué esquema le toca: saldría «correcta» "
                "sin que nadie le mirara la forma"
            )


def test_la_respuesta_sube_de_version_como_las_facturas():
    """Sin depender de lo que traiga el zip.

    Las pruebas de arriba distinguen «sube» de «no sube» solo porque en el
    paquete no hay más `ApplicationResponse` que el 2.5; con los de la 2.1 a la
    2.4 instalados pasarían igual sin subir. Esta mira la lista.
    """
    def nombres(version):
        return esquema._nombres_esperados(
            formato.Deteccion(familia=RESPUESTA, version=version)
        )

    assert nombres("2.1") == tuple(
        f"UBL-ApplicationResponse-2.{n}.xsd" for n in range(1, 6)
    )
    assert nombres("2.0") == ("UBL-ApplicationResponse-2.0.xsd",)
    assert nombres("2.9") == ("UBL-ApplicationResponse-2.9.xsd",)


def test_la_portada_no_promete_la_forma_de_la_2_0():
    """La pregunta de los formatos, contra lo que hace `esquema.py`.

    Publicada el 29-09-2026 decía que la forma se mira con el esquema 2.5
    «aunque declaren otra versión», y una respuesta 2.0 sale sin comprobar
    (`_NO_SUBEN`). Medido en producción. La frase tiene que nombrar cada versión
    que no sube, y así, si la lista cambia, la frase no se queda atrás en
    silencio.
    """
    import re

    portada = (RAIZ / "web" / "index.html").read_text(encoding="utf-8")
    bloque = re.search(r'<details id="formatos">(.*?)</details>', portada, re.S)
    assert bloque, "la pregunta de los formatos ya no está en la portada"
    texto = " ".join(bloque.group(1).split())
    assert "ApplicationResponse" in texto
    assert "otra versión" not in texto
    for version in esquema._NO_SUBEN:
        assert f"la {version} sale sin comprobar" in texto, version
