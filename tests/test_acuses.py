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
