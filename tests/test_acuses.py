"""Los acuses de la solución pública: el `DocumentStatus` con que contesta.

Hasta el 26-10-2026 no se reconocían. Medido ese día con el acuse del ejemplo
oficial de remisión de la AEAT (`SendInvoicesSOAP.zip`, del 15-10-2026): salía
SIN COMPROBAR, con «su elemento raíz no es de ningún documento que se valide
aquí», y la salida era 1. Está en HALLAZGOS.md.

El acuse de aquí no es el del ejemplo copiado: es uno escrito con su misma
forma —las mismas etiquetas en el mismo orden, el mismo `CompanyID` con un
`TaxScheme` vacío, la misma falta de `UBLVersionID`— y datos inventados.

Hay cuatro cosas, y hacen falta las cuatro:

1. **Que se reconozca**, como acuse y de la 2.5, y que se le pase su esquema.
2. **Que la fecha que le falta al del ejemplo sea un error**, como decidió el
   titular, y que la nota diga qué es, porque el error del esquema no se
   entiende solo.
3. **Que cada comprobación salte cuando tiene que saltar y calle cuando no.**
4. **Que el informe diga lo que se ha mirado de un acuse**, y no se apunte la
   forma de lo que no la tiene.
"""

import pathlib

import pytest

from validador import acuses, factura
from validador.esquema import Catalogo
from validador.formato import ACUSE, detectar
from validador.incidencias import AVISO, ERROR, NOTA

RAIZ = pathlib.Path(__file__).resolve().parent.parent

LOCALIZADOR = "LOCGENV1:O:prueba+de+localizador="
FECHA = "<cbc:IssueDate>2026-10-26</cbc:IssueDate>"
# El localizador como viene en los acuses de anulación, de pago y de cobro de
# los ejemplos de la AEAT del 10-11-2026: la etiqueta está, y vacía.
VACIO = object()


def factura_(numero="FAC-0001", estado="200", descripcion="Factura Ok",
             localizador=LOCALIZADOR, nif="B12345674"):
    partes = [f"<cbc:ID>{numero}</cbc:ID>", "<cbc:IssueDate>2026-10-05</cbc:IssueDate>"]
    if localizador is VACIO:
        partes.append("<cbc:ReferencedDocumentInternalAddress/>")
    elif localizador:
        partes.append(f"<cbc:ReferencedDocumentInternalAddress>{localizador}"
                      "</cbc:ReferencedDocumentInternalAddress>")
    if estado:
        partes.append(f"<cbc:DocumentStatusCode>{estado}</cbc:DocumentStatusCode>")
    if descripcion:
        partes.append(f"<cbc:DocumentDescription>{descripcion}</cbc:DocumentDescription>")
    partes.append("<cac:IssuerParty><cac:PartyTaxScheme>"
                  f"<cbc:CompanyID>{nif}</cbc:CompanyID><cac:TaxScheme/>"
                  "</cac:PartyTaxScheme></cac:IssuerParty>")
    return "<cac:DocumentReference>" + "".join(partes) + "</cac:DocumentReference>"


def cabecera(codigo="200", descripcion="Todas las facturas correctas", facturas=None):
    dentro = f"<cbc:ResponseCode>{codigo}</cbc:ResponseCode>" if codigo else ""
    if descripcion:
        dentro += f"<cbc:Description>{descripcion}</cbc:Description>"
    return (f"<cac:DocumentResponse><cac:Response>{dentro}</cac:Response>"
            + "".join(facturas if facturas is not None else [factura_()])
            + "</cac:DocumentResponse>")


def acuse(cuerpo=None, fecha=FECHA, despues=""):
    """Un acuse con la forma del del ejemplo; con fecha, valida contra UBL 2.5."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<DocumentStatus xmlns="urn:oasis:names:specification:ubl:schema:xsd:DocumentStatus-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:ID>A-PRUEBA00000001</cbc:ID>
  {fecha}
  {cabecera() if cuerpo is None else cuerpo}
  {despues}
</DocumentStatus>"""


@pytest.fixture(scope="module")
def catalogo(esquemas_del_paquete):
    return Catalogo(esquemas_del_paquete)


def medir(xml, catalogo=None):
    return factura.validar(xml.encode("utf-8"), catalogo=catalogo)


def de_acuse(informe):
    return [(i.codigo, i.gravedad) for i in informe.incidencias
            if i.codigo.startswith("SPFE-ACUSE-")]


def una(informe, codigo):
    (encontrada,) = [i for i in informe.incidencias if i.codigo == codigo]
    return encontrada


# --- 1. Se reconoce -----------------------------------------------------------


class TestSeReconoce:
    def test_como_acuse_y_de_la_2_5(self):
        deteccion = detectar(acuse().encode("utf-8"))
        assert deteccion.familia == ACUSE
        assert deteccion.version == "2.5"
        assert deteccion.tipo_documento is None
        assert not deteccion.conforme_en16931

    def test_con_su_version_se_queda_con_la_suya(self):
        xml = acuse().replace("<cbc:ID>A-PRUEBA", "<cbc:UBLVersionID>2.4</cbc:UBLVersionID><cbc:ID>A-PRUEBA")
        assert detectar(xml.encode("utf-8")).version == "2.4"

    def test_y_se_le_pasa_su_esquema(self, catalogo):
        informe = medir(acuse(), catalogo)
        assert informe.mirado
        assert not [i for i in informe.incidencias if i.codigo.startswith("XSD-")]
        assert informe.validado and informe.conforme

    def test_sin_su_esquema_sale_sin_comprobar(self):
        """Lo que vale de un acuse es su forma: sin ella no se da por bueno."""
        informe = medir(acuse())
        assert not informe.mirado
        assert not informe.validado


# --- 2. La fecha que falta en el del ejemplo -------------------------------------


class TestSinFecha:
    def test_es_un_error_del_esquema(self, catalogo):
        informe = medir(acuse(fecha=""), catalogo)
        errores = [i for i in informe.incidencias if i.gravedad == ERROR]
        assert [i.codigo for i in errores] == ["XSD-ORDEN"]
        assert "DocumentResponse" in errores[0].mensaje
        assert informe.validado and not informe.conforme

    def test_y_la_nota_dice_que_lo_que_falta_es_la_fecha(self, catalogo):
        informe = medir(acuse(fecha=""), catalogo)
        nota = una(informe, "SPFE-ACUSE-FECHA")
        assert nota.gravedad == NOTA
        assert "cbc:IssueDate" in nota.mensaje
        assert "ejemplo" in nota.mensaje
        # Lo que cuenta es lo que cualquiera puede comprobar: el ejemplo
        # publicado y el esquema. Nada de lo que se contestó por correo.
        assert "15-10-2026" in nota.mensaje and "28-10-2026" not in nota.mensaje

    def test_con_fecha_no_hay_nota(self, catalogo):
        assert "SPFE-ACUSE-FECHA" not in [c for c, _ in de_acuse(medir(acuse(), catalogo))]

    def test_lo_demas_se_lee_igual(self, catalogo):
        """El error de forma no tapa lo que dice el acuse."""
        codigos = [c for c, _ in de_acuse(medir(acuse(fecha=""), catalogo))]
        assert codigos == ["SPFE-ACUSE-ALCANCE", "SPFE-ACUSE-FECHA",
                           "SPFE-ACUSE-RESULTADO", "SPFE-ACUSE-ACEPTADA"]


# --- 3. Cada comprobación -----------------------------------------------------------


class TestLaCabecera:
    @pytest.mark.parametrize("codigo, dice", [
        ("200", "se aceptó todo lo que se pedía"),
        ("406", "solo se aceptó una parte de lo que se pedía"),
        ("400", "no se aceptó nada de lo que se pedía"),
    ])
    def test_las_tres_publicadas(self, codigo, dice):
        facturas = {"200": [factura_()],
                    "406": [factura_(), factura_("FAC-0002", "401", "Rechazada")],
                    "400": [factura_(estado="401", descripcion="Rechazada")]}[codigo]
        informe = medir(acuse(cabecera(codigo, "x", facturas)))
        nota = una(informe, "SPFE-ACUSE-RESULTADO")
        assert nota.gravedad == NOTA
        assert dice in nota.mensaje
        assert "SPFE-ACUSE-NO-CUADRA" not in [c for c, _ in de_acuse(informe)]

    def test_la_cuenta(self):
        informe = medir(acuse(cabecera("406", "", [
            factura_(), factura_("FAC-0002"), factura_("FAC-0003", "401")])))
        assert "3 facturas: 2 con el estado 200 y 1 sin él." in una(
            informe, "SPFE-ACUSE-RESULTADO").mensaje

    def test_un_codigo_que_no_esta_publicado(self):
        informe = medir(acuse(cabecera("500", "Error interno")))
        aviso = una(informe, "SPFE-ACUSE-CABECERA")
        assert aviso.gravedad == AVISO
        assert aviso.encontrado == "500"
        assert "SPFE-ACUSE-RESULTADO" not in [c for c, _ in de_acuse(informe)]
        # Las facturas se siguen leyendo.
        assert "SPFE-ACUSE-ACEPTADA" in [c for c, _ in de_acuse(informe)]

    def test_sin_codigo(self):
        aviso = una(medir(acuse(cabecera(""))), "SPFE-ACUSE-CABECERA")
        assert aviso.encontrado == "(no está)"

    def test_sin_document_response(self):
        informe = medir(acuse(""))
        assert de_acuse(informe) == [("SPFE-ACUSE-ALCANCE", NOTA),
                                     ("SPFE-ACUSE-CABECERA", AVISO)]


class TestNoCuadra:
    @pytest.mark.parametrize("codigo, facturas", [
        ("200", [factura_(), factura_("FAC-0002", "401")]),
        ("400", [factura_(), factura_("FAC-0002", "401")]),
        ("406", [factura_(), factura_("FAC-0002")]),
        ("406", [factura_(estado="401"), factura_("FAC-0002", "402")]),
    ])
    def test_la_cabecera_y_las_facturas_no_dicen_lo_mismo(self, codigo, facturas):
        aviso = una(medir(acuse(cabecera(codigo, "", facturas))), "SPFE-ACUSE-NO-CUADRA")
        assert aviso.gravedad == AVISO
        assert codigo in aviso.mensaje

    def test_una_factura_sin_estado_cuenta_como_sin_el_200(self):
        informe = medir(acuse(cabecera("200", "", [factura_(estado="", descripcion="")])))
        assert "SPFE-ACUSE-NO-CUADRA" in [c for c, _ in de_acuse(informe)]


class TestCadaFactura:
    def test_la_aceptada_trae_su_localizador(self):
        nota = una(medir(acuse()), "SPFE-ACUSE-ACEPTADA")
        assert nota.gravedad == NOTA
        assert nota.encontrado == LOCALIZADOR
        assert "La factura FAC-0001, del 05-10-2026, de B12345674:" in nota.mensaje
        assert "descarga por localizador" in nota.mensaje

    def test_sin_localizador_lo_dice(self):
        nota = una(medir(acuse(cabecera(facturas=[factura_(localizador="")]))),
                   "SPFE-ACUSE-ACEPTADA")
        assert nota.encontrado == "(sin localizador)"
        assert "No trae localizador" in nota.mensaje

    def test_la_que_no_consta_trae_su_codigo_tal_cual(self):
        informe = medir(acuse(cabecera("400", "", [factura_(estado="4711", descripcion="NIF no censado")])))
        aviso = una(informe, "SPFE-ACUSE-RECHAZADA")
        assert aviso.gravedad == AVISO
        assert aviso.encontrado == "4711"
        assert '"NIF no censado"' in aviso.mensaje
        assert "no ha publicado" in aviso.mensaje

    def test_un_codigo_que_no_es_de_ninguna_familia_no_se_adivina(self):
        aviso = una(medir(acuse(cabecera("400", "", [factura_(estado="4711", descripcion="NIF no censado")]))),
                    "SPFE-ACUSE-RECHAZADA")
        assert "no es de ninguna regla" in aviso.mensaje
        assert "norma europea" not in aviso.mensaje and "regla de negocio" not in aviso.mensaje

    def test_una_factura_sin_estado_tampoco(self):
        aviso = una(medir(acuse(cabecera("400", "", [factura_(estado="", descripcion="")]))),
                    "SPFE-ACUSE-RECHAZADA")
        assert "no le da ningún estado" in aviso.mensaje
        assert "norma europea" not in aviso.mensaje and "regla de negocio" not in aviso.mensaje


# --- No todo acuse es de una remisión ----------------------------------------------
#
# Con el mismo DocumentStatus contesta la solución pública a la remisión, a la
# anulación y a las comunicaciones de estado, y el acuse no dice a cuál: eso va
# en el Action del sobre ebXML. Hasta el 11-11-2026 todo acuse con 200 se leía
# como de una remisión. Medido ese día con los ejemplos que la AEAT publicó el
# 10-11-2026: del acuse de anulación ("Anulacion correcta") y de los de pago y
# cobro ("Factura SETTLEMENT Ok"), Glosa-e decía que la factura "consta como
# dada de alta", y se quejaba de que el localizador, vacío en los tres, faltara.
# Los acuses de aquí tienen la forma de esos tres, con datos inventados.

ANULACION = acuse(cabecera("200", "Todas las facturas correctas", [
    factura_("A01", "200", "Anulacion correcta", localizador=VACIO)]))
PAGO = acuse(cabecera("200", "Todas las Acciones correctas", [
    factura_("A01", "200", "Factura SETTLEMENT Ok", localizador=VACIO)]))


class TestNoTodoAcuseEsUnaRemision:
    @pytest.mark.parametrize("xml, dice", [(ANULACION, "Anulacion correcta"),
                                           (PAGO, "Factura SETTLEMENT Ok")],
                             ids=["anulacion", "pago"])
    def test_no_dice_dada_de_alta(self, xml, dice):
        nota = una(medir(xml), "SPFE-ACUSE-ACEPTADA")
        assert "alta" not in nota.mensaje
        assert f'"{dice}"' in nota.mensaje
        assert "ebXML" in nota.mensaje

    @pytest.mark.parametrize("xml", [ANULACION, PAGO], ids=["anulacion", "pago"])
    def test_ni_da_por_hecho_que_le_falta_el_localizador(self, xml):
        nota = una(medir(xml), "SPFE-ACUSE-ACEPTADA")
        assert nota.encontrado == "(sin localizador)"
        # Que el de una remisión lo lleva se sigue diciendo, pero como lo que
        # es: una condición, no un defecto de este acuse.
        assert "cada factura lo lleva" not in nota.mensaje
        assert "si es el acuse de una remisión" in nota.mensaje

    @pytest.mark.parametrize("xml", [
        ANULACION, PAGO, acuse(),
        acuse(cabecera("406", "", [factura_(), factura_("FAC-0002", "401")])),
        acuse(cabecera("200", "", [factura_(), factura_("FAC-0002", "401")])),
        acuse(cabecera("400", "", [factura_(estado="", descripcion="")])),
        acuse(""),
    ], ids=["anulacion", "pago", "remision", "406", "200-no-cuadra", "sin-estado",
            "sin-cabecera"])
    def test_ninguna_incidencia_de_un_acuse_dice_alta(self, xml):
        """Ni la de una remisión: con 200 el acuse dice que se aceptó lo
        pedido, y qué se pidió no lo dice."""
        for incidencia in medir(xml).incidencias:
            if incidencia.codigo.startswith("SPFE-ACUSE-"):
                assert "dada de alta" not in incidencia.mensaje, incidencia.codigo
                assert "dadas de alta" not in incidencia.mensaje, incidencia.codigo
                assert "dada" not in (incidencia.encontrado or ""), incidencia.codigo

    def test_ni_las_fichas(self):
        from validador import glosario
        for codigo, ficha in glosario.CODIGOS.items():
            if codigo.startswith("SPFE-ACUSE-"):
                assert "dada de alta" not in ficha, codigo

    def test_la_nota_cita_el_catalogo_de_hoy(self):
        nota = una(medir(ANULACION), "SPFE-ACUSE-ALCANCE")
        assert "0.1.5" in nota.mensaje and "0.1.3" not in nota.mensaje
        assert "10-11-2026" in nota.mensaje
        assert "anulación" in nota.mensaje


# --- Los códigos de error de cada factura ----------------------------------------
#
# La lista de códigos de rechazo de la solución pública no está publicada. Una
# regla de la norma europea con ficha se explica; una que empiece por
# SPFE-CORE, SPFE-LIST o BR-ES se nombra y no se traduce. Ningún texto
# publicado dice en qué campo del acuse va el código: se busca en el estado y
# en la descripción.


class TestLosCodigosDeRechazo:
    def _aviso(self, estado, descripcion=""):
        informe = medir(acuse(cabecera("400", "", [factura_(estado=estado, descripcion=descripcion)])))
        return una(informe, "SPFE-ACUSE-RECHAZADA")

    def test_la_regla_europea_se_explica_con_su_ficha(self):
        aviso = self._aviso("BR-CO-16")
        assert aviso.gravedad == AVISO
        assert "la regla BR-CO-16 de la norma europea" in aviso.mensaje
        assert '"El importe a pagar no cuadra."' in aviso.mensaje
        assert "glosa-e.com/codigo-BR-CO-16" in aviso.mensaje
        assert aviso.encontrado == "BR-CO-16"

    def test_tambien_si_viene_en_la_descripcion(self):
        aviso = self._aviso("4001", "BR-CO-16: el importe a pagar no cuadra")
        assert "la regla BR-CO-16 de la norma europea" in aviso.mensaje
        assert aviso.encontrado == "4001"

    def test_la_del_estado_manda_sobre_la_de_la_descripcion(self):
        aviso = self._aviso("BR-02", "Vea también BR-CO-16")
        assert "BR-02" in aviso.mensaje.split("norma europea")[0]
        assert "glosa-e.com/codigo-BR-CO-16" not in aviso.mensaje

    def test_una_regla_europea_que_no_esta_en_el_glosario(self):
        aviso = self._aviso("BR-CO-99")
        assert "BR-CO-99" in aviso.mensaje and "no la tiene" in aviso.mensaje
        assert "glosa-e.com/codigo-" not in aviso.mensaje

    @pytest.mark.parametrize("codigo", ["SPFE-CORE-0012", "SPFE-LIST-004", "BR-ES-0101"])
    def test_las_de_la_aeat_se_nombran_y_no_se_traducen(self, codigo):
        aviso = self._aviso(codigo, "Campo mal informado")
        assert f"{codigo} no es una regla de la norma europea" in aviso.mensaje
        assert "no está publicada" in aviso.mensaje and "AEAT" not in aviso.mensaje
        assert f"la regla {codigo} de la norma europea" not in aviso.mensaje
        assert '"Campo mal informado"' in aviso.mensaje

    def test_un_codigo_dentro_de_otro_no_cuenta(self):
        aviso = self._aviso("XBR-CO-16X")
        assert "norma europea" not in aviso.mensaje

    def test_el_glosario_cuenta_las_tres_familias(self):
        from validador import glosario
        ficha = glosario.CODIGOS["SPFE-ACUSE-RECHAZADA"]
        for trozo in ("BR-CO-16", "SPFE-CORE", "SPFE-LIST", "BR-ES", "no está publicada"):
            assert trozo in ficha, trozo


class TestUnaFacturaPorAviso:
    def test_una_nota_o_un_aviso_por_factura(self):
        facturas = [factura_(f"FAC-{n:04d}", "200" if n % 2 else "401") for n in range(1, 6)]
        codigos = [c for c, _ in de_acuse(medir(acuse(cabecera("406", "", facturas))))]
        assert codigos.count("SPFE-ACUSE-ACEPTADA") == 3
        assert codigos.count("SPFE-ACUSE-RECHAZADA") == 2


class TestLaNota:
    def test_va_siempre_y_dice_de_donde_sale(self):
        nota = una(medir(acuse()), "SPFE-ACUSE-ALCANCE")
        assert nota.gravedad == NOTA
        assert "20-10-2026" in nota.mensaje and "10-11-2026" in nota.mensaje
        assert "ebXML" in nota.mensaje

    def test_cuenta_lo_que_no_se_lee(self, catalogo):
        otra = ("<cac:AdditionalDocumentResponse><cac:Response><cbc:ResponseCode>200"
                "</cbc:ResponseCode></cac:Response>" + factura_("FAC-0009")
                + "</cac:AdditionalDocumentResponse>")
        informe = medir(acuse(despues=otra), catalogo)
        assert informe.conforme
        assert "Trae 1 cac:AdditionalDocumentResponse" in una(informe, "SPFE-ACUSE-ALCANCE").mensaje

    def test_a_una_respuesta_no_se_le_aplica(self):
        """Un `ApplicationResponse` con la misma cabecera no es un acuse."""
        xml = acuse().replace("DocumentStatus-2", "ApplicationResponse-2").replace(
            "DocumentStatus", "ApplicationResponse")
        assert not [c for c, _ in de_acuse(medir(xml))]


# --- 4. Lo que el informe dice ----------------------------------------------------------


def _lote(tmp_path, catalogo, *xmls):
    rutas = []
    for n, xml in enumerate(xmls):
        ruta = tmp_path / f"a{n}.xml"
        ruta.write_text(xml, encoding="utf-8")
        rutas.append(ruta)
    return factura.validar_lote(rutas, catalogo=catalogo)


class TestLoQueElInformeDice:
    def test_la_frase_de_un_acuse(self, tmp_path, catalogo):
        frase = _lote(tmp_path, catalogo, acuse()).alcance()
        assert "la forma contra el esquema XSD" in frase
        assert ("la cabecera y el estado de cada factura en los acuses de la "
                "solución pública (lo que no se mide lo dice la nota "
                "SPFE-ACUSE-ALCANCE)") in frase
        assert "EN 16931" not in frase

    def test_sin_su_esquema_no_se_apunta_la_forma(self, tmp_path):
        """Sin el esquema del acuse no hay nada mirado, y la frase no puede
        decir que se pasó."""
        frase = _lote(tmp_path, None, acuse()).alcance()
        assert "la forma contra el esquema XSD" not in frase.split("No se comprueba")[0]

    def test_la_fecha_que_falta_no_sale_correcta(self, tmp_path, catalogo):
        lote = _lote(tmp_path, catalogo, acuse(fecha=""))
        assert not lote.conforme


# --- La respuesta a una consulta ---------------------------------------------------
#
# Las dos consultas, por identificador y por filtro de fechas, contestan con un
# DocumentStatus de otra forma: la cabecera trae cac:Status con
# cbc:StatusReasonCode, y no cbc:ResponseCode, y las facturas encontradas van
# en cac:AdditionalDocumentResponse. Medido el 10-11-2026 con los ejemplos de
# la AEAT: Glosa-e avisaba con SPFE-ACUSE-CABECERA de que faltaba el código, y
# no decía nada de las facturas. Las de aquí tienen la forma de esos dos, con
# datos inventados.


def encontrada(numero="F0001-000030717", estado="ACCEPTED", localizador=LOCALIZADOR):
    return ("<cac:AdditionalDocumentResponse><cac:Response>"
            f"<cbc:ResponseCode>{estado}</cbc:ResponseCode></cac:Response>"
            "<cac:DocumentReference>"
            f"<cbc:ID>{numero}</cbc:ID><cbc:IssueDate>2026-10-05</cbc:IssueDate>"
            "<cbc:DocumentType>Invoice</cbc:DocumentType>"
            f"<cbc:ReferencedDocumentInternalAddress>{localizador}"
            "</cbc:ReferencedDocumentInternalAddress>"
            "<cac:IssuerParty><cac:PartyTaxScheme><cbc:CompanyID>B12345674</cbc:CompanyID>"
            "<cac:TaxScheme/></cac:PartyTaxScheme></cac:IssuerParty>"
            "</cac:DocumentReference></cac:AdditionalDocumentResponse>")


def consulta(facturas=None, codigo="200", secuencia=""):
    status = (f"<cbc:StatusReasonCode>{codigo}</cbc:StatusReasonCode>"
              "<cbc:StatusReason>Búsqueda realizada correctamente</cbc:StatusReason>")
    if secuencia:
        status += f"<cbc:SequenceID>{secuencia}</cbc:SequenceID>"
    cabecera_ = (f"<cac:DocumentResponse><cac:Response><cac:Status>{status}"
                 "</cac:Status></cac:Response></cac:DocumentResponse>")
    return acuse(cabecera_, despues="".join(facturas if facturas is not None
                                             else [encontrada()]))


class TestLaRespuestaAUnaConsulta:
    def test_no_avisa_de_que_falte_el_codigo(self):
        assert "SPFE-ACUSE-CABECERA" not in [c for c, _ in de_acuse(medir(consulta()))]

    def test_dice_que_es_y_cuenta_lo_que_encontro(self):
        nota = una(medir(consulta([encontrada(), encontrada("F2"),
                                    encontrada("F3", "REJECTED")])), "SPFE-ACUSE-CONSULTA")
        assert nota.gravedad == NOTA
        assert nota.encontrado == "200"
        assert '"Búsqueda realizada correctamente"' in nota.mensaje
        assert "consulta" in nota.mensaje
        assert "3 facturas: 2 con el estado ACCEPTED y 1 con el estado REJECTED." in nota.mensaje

    def test_una_y_ninguna(self):
        assert "1 factura, con el estado ACCEPTED." in una(
            medir(consulta()), "SPFE-ACUSE-CONSULTA").mensaje
        assert "no trae ninguna factura" in una(
            medir(consulta([])), "SPFE-ACUSE-CONSULTA").mensaje

    def test_la_nota_del_alcance_no_dice_que_no_se_leen(self):
        nota = una(medir(consulta()), "SPFE-ACUSE-ALCANCE")
        assert "no se leen" not in nota.mensaje

    def test_la_clave_de_la_pagina_siguiente(self):
        con = una(medir(consulta(secuencia="1791197075934_0001")), "SPFE-ACUSE-CONSULTA")
        assert "1791197075934_0001" in con.mensaje and "SECUENCE_ID" in con.mensaje
        assert "SECUENCE_ID" not in una(medir(consulta()), "SPFE-ACUSE-CONSULTA").mensaje

    def test_el_error_de_forma_de_los_ejemplos_se_explica(self, catalogo):
        """La errata 1 del informe: a cac:DocumentResponse le falta
        cac:DocumentReference, que UBL 2.5 exige."""
        informe = medir(consulta(), catalogo)
        assert "XSD-FALTA" in [i.codigo for i in informe.incidencias if i.gravedad == ERROR]
        assert "cac:DocumentReference" in una(informe, "SPFE-ACUSE-CONSULTA").mensaje

    def test_con_referencia_no_se_explica_lo_que_no_pasa(self):
        cabecera_ = ("<cac:DocumentResponse><cac:Response><cac:Status>"
                     "<cbc:StatusReasonCode>200</cbc:StatusReasonCode></cac:Status>"
                     "</cac:Response><cac:DocumentReference><cbc:ID>X</cbc:ID>"
                     "</cac:DocumentReference></cac:DocumentResponse>")
        nota = una(medir(acuse(cabecera_)), "SPFE-ACUSE-CONSULTA")
        assert "cac:DocumentReference" not in nota.mensaje

    def test_sin_codigo_ni_status_sigue_avisando(self):
        assert una(medir(acuse(cabecera(""))), "SPFE-ACUSE-CABECERA").gravedad == AVISO


# --- El acuse dentro de un sobre SOAP ------------------------------------------------
#
# Según el catálogo de servicios (0.1.5, apartado 6.10), el validador previo,
# que solo existe en pruebas, devuelve «Directamente XML (DocumentStatus)».
# Su ejemplo del 10-11-2026 lo trae dentro de un sobre SOAP 1.2, env:Envelope,
# y Glosa-e lo dejaba SIN COMPROBAR: «su elemento raíz "Envelope" no es de
# ningún documento que se valide aquí». Era justo el documento que más interesa
# leer. Los de aquí tienen su forma, con datos inventados: la misma factura una
# vez por cada código, sin cbc:IssueDate y con los códigos de la AEAT.

SOAP_12 = "http://www.w3.org/2003/05/soap-envelope"
SOAP_11 = "http://schemas.xmlsoap.org/soap/envelope/"


def sobre(dentro, ns=SOAP_12):
    return (f'<env:Envelope xmlns:env="{ns}">\n   <env:Header/>\n'
            f'   <env:Body Id="Body">\n{dentro}\n   </env:Body>\n</env:Envelope>')


def sin_declaracion(xml):
    return xml.split("?>", 1)[1].lstrip("\n")


VALIDADOR = sin_declaracion(acuse(cabecera("400", "Todas las facturas han fallado", [
    factura_("CLASEA00000182", "SPFE-CORE-18", "El IBAN no es válido", localizador=""),
    factura_("CLASEA00000182", "SPFE-IDEN-02", "El NIF tiene un formato erróneo", localizador=""),
    factura_("CLASEA00000182", "SPFE-IDEN-05", "El NIF tiene un formato erróneo", localizador=""),
    factura_("CLASEA00000182", "SPFE-REPR-01", "El titular del certificado no vale", localizador=""),
]), fecha=""))


class TestElSobreSoap:
    @pytest.mark.parametrize("ns", [SOAP_12, SOAP_11], ids=["soap-1.2", "soap-1.1"])
    def test_se_abre_y_se_lee_el_acuse(self, ns):
        informe = medir(sobre(VALIDADOR, ns))
        assert informe.deteccion.familia == ACUSE
        nota = una(informe, "SPFE-ACUSE-SOBRE")
        assert nota.gravedad == NOTA
        assert "6.10" in nota.mensaje and "SOAP" in nota.mensaje
        assert "SPFE-ACUSE-RESULTADO" in [c for c, _ in de_acuse(informe)]

    def test_tambien_en_un_lote(self, tmp_path):
        ruta = tmp_path / "respuesta.xml"
        ruta.write_text(sobre(VALIDADOR), encoding="utf-8")
        (_, informe, _), = factura.validar_lote([ruta]).nombrados
        assert "SPFE-ACUSE-SOBRE" in [c for c, _ in de_acuse(informe)]

    def test_los_errores_dicen_la_linea_del_fichero(self, catalogo):
        """La errata 6 del informe, medida: sin cbc:IssueDate no pasa el
        esquema. Y la línea es la del fichero, no la del acuse sacado."""
        xml = sobre(VALIDADOR)
        informe = medir(xml, catalogo)
        (orden,) = [i for i in informe.incidencias if i.codigo == "XSD-ORDEN"]
        linea = 1 + xml.split("<cac:DocumentResponse>")[0].count("\n")
        assert f"(línea {linea})" in orden.campo
        assert "SPFE-ACUSE-FECHA" in [c for c, _ in de_acuse(informe)]

    def test_un_sobre_con_otra_cosa_no_se_abre(self):
        factura_ue = ('<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:'
                      'Invoice-2"><ID xmlns="x">1</ID></Invoice>')
        deteccion = detectar(sobre(factura_ue).encode("utf-8"))
        assert not deteccion
        assert "sobre SOAP" in deteccion.motivo and "Invoice" in deteccion.motivo
        # Y al validarla tampoco se saca: una factura firmada dentro de un
        # sobre ya no es la misma fuera de él.
        informe = factura.validar(sobre(factura_ue).encode("utf-8"))
        assert not informe.deteccion and "sobre SOAP" in informe.deteccion.motivo

    def test_ni_uno_con_dos_documentos(self):
        dos = VALIDADOR + "\n" + VALIDADOR
        deteccion = detectar(sobre(dos).encode("utf-8"))
        assert factura.validar(sobre(dos).encode("utf-8")).deteccion.familia is None
        assert "sobre SOAP" in deteccion.motivo

    def test_un_acuse_sin_sobre_no_lleva_la_nota(self):
        assert "SPFE-ACUSE-SOBRE" not in [c for c, _ in de_acuse(medir(acuse()))]


class TestLaRespuestaDelValidador:
    def test_cuenta_una_factura_y_no_cuatro(self):
        nota = una(medir(sobre(VALIDADOR)), "SPFE-ACUSE-RESULTADO")
        assert "4 referencias de 1 factura" in nota.mensaje
        assert "4 facturas" not in nota.mensaje

    def test_sin_repetidas_se_cuenta_como_siempre(self):
        nota = una(medir(acuse(cabecera("406", "", [
            factura_(), factura_("FAC-0002"), factura_("FAC-0003", "401")]))),
            "SPFE-ACUSE-RESULTADO")
        assert "referencias" not in nota.mensaje

    @pytest.mark.parametrize("codigo", ["SPFE-CORE-18", "SPFE-IDEN-02", "SPFE-IDEN-05",
                                        "SPFE-REPR-01"])
    def test_los_cuatro_codigos_de_la_aeat_se_reconocen(self, codigo):
        avisos = [i for i in medir(sobre(VALIDADOR)).incidencias
                  if i.codigo == "SPFE-ACUSE-RECHAZADA" and i.encontrado == codigo]
        (aviso,) = avisos
        assert f"{codigo} no es una regla de la norma europea" in aviso.mensaje
        assert "no es de ninguna regla" not in aviso.mensaje
