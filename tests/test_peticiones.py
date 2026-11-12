"""Las peticiones de consulta y de descarga a la solución pública.

Hasta el 11-11-2026 pasaban en silencio. Medido el 10-11-2026 con los ejemplos
que la AEAT publicó ese día (`ConsultaFacturasPorIDs.xml`,
`DescargarFacturaPorID.xml` y `DescargarFacturaPorLOC.xml`): son
`ApplicationResponse` con los códigos QUERYBYID, DOWNLOADBYID y DOWNLOADBYLOC,
y Glosa-e contestaba "sin errores" sin una sola nota que dijera qué eran ni que
su contenido no se había medido. Es el mismo fallo que se arregló el 03-11 con
las facturas alemanas. Está en HALLAZGOS.md.

Lo que se mide sale del catálogo de servicios de la AEAT (versión 0.1.5, del
10-11-2026), y nada más: cuántas facturas pide cada petición (apartados 6.4.3
y 6.6.3) y que cada una venga identificada como dice el catálogo, por el NIF
de quien la emite, su número y su fecha, o por su localizador.

Las peticiones de aquí tienen la forma de las de los ejemplos, con datos
inventados.
"""

import pytest

from validador import factura, glosario, normas, peticiones
from validador.esquema import Catalogo
from validador.incidencias import AVISO, NOTA

LOCALIZADOR = "LOCGENV1:C:prueba+de+localizador="


def por_identificador(numero="CLASEA00000182", fecha="2026-10-05", nif="B12345674"):
    partes = []
    if numero:
        partes.append(f"<cbc:ID>{numero}</cbc:ID>")
    if fecha:
        partes.append(f"<cbc:IssueDate>{fecha}</cbc:IssueDate>")
    partes.append("<cbc:DocumentType>Invoice</cbc:DocumentType>")
    if nif:
        partes.append("<cac:IssuerParty><cac:PartyTaxScheme>"
                      f"<cbc:CompanyID>{nif}</cbc:CompanyID><cac:TaxScheme/>"
                      "</cac:PartyTaxScheme></cac:IssuerParty>")
    return "<cac:DocumentReference>" + "".join(partes) + "</cac:DocumentReference>"


def por_localizador(localizador=LOCALIZADOR):
    return f"<cac:DocumentReference><cbc:ID>{localizador}</cbc:ID></cac:DocumentReference>"


def peticion(codigo="QUERYBYID", facturas=None):
    if facturas is None:
        facturas = [por_localizador() if codigo == "DOWNLOADBYLOC" else por_identificador()]
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ApplicationResponse xmlns="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>PRUEBA-0001</cbc:ID>
  <cbc:IssueDate>2026-11-11</cbc:IssueDate>
  <cac:SenderParty></cac:SenderParty>
  <cac:ReceiverParty></cac:ReceiverParty>
  <cac:DocumentResponse>
    <cac:Response>
      <cbc:ResponseCode>{codigo}</cbc:ResponseCode>
      <cbc:Description>Solicitud</cbc:Description>
    </cac:Response>
    {"".join(facturas)}
  </cac:DocumentResponse>
</ApplicationResponse>"""


@pytest.fixture(scope="module")
def catalogo(esquemas_del_paquete):
    return Catalogo(esquemas_del_paquete)


def medir(xml, catalogo=None):
    return factura.validar(xml.encode("utf-8"), catalogo=catalogo)


def de_peticion(informe):
    return [(i.codigo, i.gravedad) for i in informe.incidencias
            if i.codigo.startswith("SPFE-PETICION-")]


def una(informe, codigo):
    (encontrada,) = [i for i in informe.incidencias if i.codigo == codigo]
    return encontrada


CODIGOS = ["QUERYBYID", "DOWNLOADBYID", "DOWNLOADBYLOC"]


class TestYaNoPasanEnSilencio:
    @pytest.mark.parametrize("codigo", CODIGOS)
    def test_cada_una_trae_su_nota(self, codigo):
        nota = una(medir(peticion(codigo)), "SPFE-PETICION-ALCANCE")
        assert nota.gravedad == NOTA
        assert nota.encontrado == codigo
        assert "catálogo de servicios" in nota.mensaje
        assert "10-11-2026" in nota.mensaje
        assert "No se mira" in nota.mensaje

    @pytest.mark.parametrize("codigo, dice", [
        ("QUERYBYID", "consulta por identificador"),
        ("DOWNLOADBYID", "descarga por identificador"),
        ("DOWNLOADBYLOC", "descarga por localizador"),
    ])
    def test_dice_que_es(self, codigo, dice):
        assert dice in una(medir(peticion(codigo)), "SPFE-PETICION-ALCANCE").mensaje

    @pytest.mark.parametrize("codigo", CODIGOS)
    def test_bien_hecha_no_tiene_quejas(self, codigo, catalogo):
        informe = medir(peticion(codigo), catalogo)
        assert de_peticion(informe) == [("SPFE-PETICION-ALCANCE", NOTA)]
        assert informe.validado and informe.conforme

    def test_un_mensaje_de_la_orden_no_es_una_peticion(self):
        assert de_peticion(medir(peticion("CANCELINVOICE"))) == []

    def test_ni_una_respuesta_de_otra_red(self):
        assert de_peticion(medir(peticion("AP"))) == []

    def test_la_frase_del_lote_sigue_diciendo_que_el_contenido_no_se_mide(self, tmp_path, catalogo):
        ruta = tmp_path / "p.xml"
        ruta.write_text(peticion(), encoding="utf-8")
        frase = factura.validar_lote([ruta], catalogo=catalogo).alcance()
        assert "ni el contenido de las respuestas (ApplicationResponse)" in frase


class TestCadaFacturaIdentificada:
    @pytest.mark.parametrize("codigo", ["QUERYBYID", "DOWNLOADBYID"])
    @pytest.mark.parametrize("falta, referencia", [
        ("el número", por_identificador(numero="")),
        ("la fecha de expedición", por_identificador(fecha="")),
        ("el NIF del emisor", por_identificador(nif="")),
    ], ids=["numero", "fecha", "nif"])
    def test_por_identificador_le_falta_un_dato(self, codigo, falta, referencia):
        aviso = una(medir(peticion(codigo, [referencia])), "SPFE-PETICION-FACTURA")
        assert aviso.gravedad == AVISO
        assert falta in aviso.mensaje
        assert "NIF del emisor, número y fecha de expedición" in aviso.mensaje

    def test_dice_cual_es_la_factura(self):
        aviso = una(medir(peticion("QUERYBYID", [por_identificador(fecha="")])),
                    "SPFE-PETICION-FACTURA")
        assert "CLASEA00000182" in aviso.campo

    def test_por_localizador_sin_localizador(self):
        aviso = una(medir(peticion("DOWNLOADBYLOC", [por_localizador("")])),
                    "SPFE-PETICION-FACTURA")
        assert aviso.gravedad == AVISO and "localizador" in aviso.mensaje

    def test_el_localizador_no_se_mira_por_su_forma(self):
        """Solo se ha visto LOCGENV1:; adivinar su forma sería poner nombre a
        lo que no está publicado."""
        assert de_peticion(medir(peticion("DOWNLOADBYLOC", [por_localizador("cualquiera")]))) \
            == [("SPFE-PETICION-ALCANCE", NOTA)]

    def test_un_aviso_por_factura(self):
        facturas = [por_identificador(numero=f"F{n}", fecha="") for n in range(3)]
        codigos = [c for c, _ in de_peticion(medir(peticion("DOWNLOADBYID", facturas)))]
        assert codigos.count("SPFE-PETICION-FACTURA") == 3

    @pytest.mark.parametrize("codigo", CODIGOS)
    def test_sin_ninguna_factura(self, codigo):
        aviso = una(medir(peticion(codigo, [])), "SPFE-PETICION-FACTURA")
        assert aviso.gravedad == AVISO and "ninguna factura" in aviso.mensaje


class TestElMaximo:
    @pytest.mark.parametrize("codigo, maximo, apartado", [
        ("QUERYBYID", 1000, "6.4.3"),
        ("DOWNLOADBYID", 100, "6.6.3"),
        ("DOWNLOADBYLOC", 100, "6.6.3"),
    ])
    def test_uno_mas_del_maximo(self, codigo, maximo, apartado):
        una_ = por_localizador() if codigo == "DOWNLOADBYLOC" else por_identificador()
        aviso = una(medir(peticion(codigo, [una_] * (maximo + 1))), "SPFE-PETICION-LIMITE")
        assert aviso.gravedad == AVISO
        assert apartado in aviso.mensaje
        assert aviso.encontrado == str(maximo + 1)

    @pytest.mark.parametrize("codigo, maximo", [
        ("QUERYBYID", 1000), ("DOWNLOADBYID", 100), ("DOWNLOADBYLOC", 100)])
    def test_el_maximo_justo_pasa(self, codigo, maximo):
        una_ = por_localizador() if codigo == "DOWNLOADBYLOC" else por_identificador()
        assert "SPFE-PETICION-LIMITE" not in [
            c for c, _ in de_peticion(medir(peticion(codigo, [una_] * maximo)))]


class TestLoDeAlrededor:
    def test_cada_codigo_tiene_su_ficha(self):
        for codigo in ("SPFE-PETICION-ALCANCE", "SPFE-PETICION-FACTURA",
                       "SPFE-PETICION-LIMITE", "SPFE-ACUSE-CONSULTA"):
            assert codigo in glosario.CODIGOS, codigo

    def test_y_su_norma_es_la_de_los_servicios_web(self):
        assert normas.norma("SPFE-PETICION-ALCANCE")[0] == normas.ACUSES

    def test_los_tres_y_nada_mas(self):
        assert set(peticiones.PETICIONES) == set(CODIGOS)


# --- Lo que no es ningún código conocido, 12-11-2026 -------------------------
#
# Verificado desde otra sesión el 12-11-2026: el ejemplo de consulta de la AEAT
# con QUERYBYID cambiado por BORRARTODO, o escrito querybyid, salía "sin
# errores" y ni una nota. Se cerraron los tres códigos el 11-11, no la clase.


class TestUnCodigoQueNoSeConoce:
    @pytest.mark.parametrize("codigo", ["BORRARTODO", "querybyid", "AP"])
    def test_lleva_su_nota(self, codigo):
        informe = medir(peticion(codigo))
        (nota,) = [i for i in informe.incidencias if i.codigo == "RESPUESTA-NO-MEDIDA"]
        assert nota.gravedad == NOTA
        assert codigo in nota.mensaje and nota.encontrado == codigo
        assert "no se mira" in nota.mensaje

    def test_en_minusculas_dice_a_cual_se_parece(self):
        informe = medir(peticion("querybyid"))
        (nota,) = [i for i in informe.incidencias if i.codigo == "RESPUESTA-NO-MEDIDA"]
        assert "QUERYBYID" in nota.mensaje and "mayúsculas" in nota.mensaje

    def test_tambien_un_mensaje_de_la_orden_en_minusculas(self):
        (nota,) = [i for i in medir(peticion("payment")).incidencias
                   if i.codigo == "RESPUESTA-NO-MEDIDA"]
        assert "PAYMENT" in nota.mensaje

    def test_uno_que_no_se_parece_a_nada_no_dice_que_se_parece(self):
        (nota,) = [i for i in medir(peticion("BORRARTODO")).incidencias
                   if i.codigo == "RESPUESTA-NO-MEDIDA"]
        assert "mayúsculas" not in nota.mensaje

    @pytest.mark.parametrize("codigo", ["QUERYBYID", "DOWNLOADBYLOC", "PAYMENT", "CANCELINVOICE"])
    def test_los_conocidos_no_la_llevan(self, codigo):
        assert "RESPUESTA-NO-MEDIDA" not in [i.codigo for i in medir(peticion(codigo)).incidencias]

    def test_varios_codigos_desconocidos_dan_una_sola_nota(self):
        dos = peticion("UNO").replace(
            "</ApplicationResponse>",
            "<cac:DocumentResponse><cac:Response><cbc:ResponseCode>DOS"
            "</cbc:ResponseCode></cac:Response></cac:DocumentResponse></ApplicationResponse>")
        notas = [i for i in medir(dos).incidencias if i.codigo == "RESPUESTA-NO-MEDIDA"]
        assert len(notas) == 1 and "UNO" in notas[0].mensaje and "DOS" in notas[0].mensaje

    def test_el_mismo_codigo_dos_veces_se_nombra_una(self):
        """La rotura que salió verde el 12-11-2026: sin quitar repetidos, la
        nota decía "los códigos UNO y UNO"."""
        dos = peticion("UNO").replace(
            "</ApplicationResponse>",
            "<cac:DocumentResponse><cac:Response><cbc:ResponseCode>UNO"
            "</cbc:ResponseCode></cac:Response></cac:DocumentResponse></ApplicationResponse>")
        (nota,) = [i for i in medir(dos).incidencias if i.codigo == "RESPUESTA-NO-MEDIDA"]
        assert nota.encontrado == "UNO" and "el código UNO," in nota.mensaje

    def test_tiene_ficha_y_es_de_la_casa(self):
        assert "RESPUESTA-NO-MEDIDA" in glosario.CODIGOS
        assert normas.norma("RESPUESTA-NO-MEDIDA")[0] == normas.CASA
