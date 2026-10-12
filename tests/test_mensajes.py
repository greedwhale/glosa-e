"""Los mensajes de la orden: la anulación y los ocho estados del anexo II.

Hasta el 12-10-2026 a un `ApplicationResponse` solo se le miraba la forma y la
firma. Medido ese día sobre `26e9a5d` con nueve mensajes rotos escritos aquí
(sin la fecha, sin el vencimiento del pago, sin el NIF de la factura, un
rechazo con el motivo 03): ocho salían sin una queja, y el noveno, una
anulación escrita como dice el BOE, solo por la forma. Está en HALLAZGOS.md.

Aquí hay cuatro cosas, y hacen falta las cuatro:

1. **Que la tabla sea la del BOE.** `mensajes_es` es generado; si alguien toca
   el extractor o sale una corrección de errores, salta.
2. **Que se lea como se decidió**: las erratas arregladas, contadas, y las
   rutas arregladas andando de verdad por el esquema de UBL 2.5.
3. **Que cada regla salte cuando tiene que saltar y calle cuando no.** Con los
   esquemas de `web/paquete.zip`, para que el mensaje bueno sea bueno también
   en la forma.
4. **Que el informe no prometa de más ni de menos**: lo que se mide de los
   mensajes, y que de las demás respuestas sigue sin mirarse el contenido.
"""

import dataclasses
import hashlib
import pathlib
import re

import pytest
from lxml import etree

from validador import cius_es, factura, mensajes, mensajes_es
from validador.esquema import Catalogo
from validador.formato import detectar
from validador.incidencias import AVISO, ERROR, NOTA
from validador.solucion_publica import AnexoCambiado

RAIZ = pathlib.Path(__file__).resolve().parent.parent
ANEXO = RAIZ / "anexos" / "orden-hac-1028-2026.xml"

CODIGOS = {
    "CANCELINVOICE", "PAYMENT", "CANCELPAYMENT", "REJECTION", "CANCELREJECTION",
    "SETTLEMENT", "CANCELSETTLEMENT", "DEFAULT", "CANCELDEFAULT",
}
ALTAS = {"CANCELINVOICE", "PAYMENT", "REJECTION", "SETTLEMENT", "DEFAULT"}
BAJAS = CODIGOS - ALTAS


# --- Un mensaje, escrito como dicen las tablas ---------------------------------

FACTURA = """
    <cac:DocumentReference>
      <cbc:ID>F-2026-0101</cbc:ID>
      <cbc:IssueDate>2026-10-06</cbc:IssueDate>
      <cac:IssuerParty>
        <cac:PartyTaxScheme><cbc:CompanyID>B12345674</cbc:CompanyID><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:PartyTaxScheme>
        <cac:PartyLegalEntity><cbc:RegistrationName>Vendedor SL</cbc:RegistrationName></cac:PartyLegalEntity>
      </cac:IssuerParty>
    </cac:DocumentReference>"""

FECHA = "<cbc:EffectiveDate>2026-10-12</cbc:EffectiveDate>"


def estado(atributo, fecha="2026-11-05"):
    con_fecha = f"<cbc:ReferenceDate>{fecha}</cbc:ReferenceDate>" if fecha else ""
    return (f"<cac:Status>{con_fecha}<cac:Condition><cbc:AttributeID>{atributo}"
            "</cbc:AttributeID></cac:Condition></cac:Status>")


def motivo(valor):
    return f"<cac:Status><cbc:ConditionCode>{valor}</cbc:ConditionCode></cac:Status>"


# Lo mínimo que cada mensaje pide además de la factura.
BUENO = {
    "CANCELINVOICE": FECHA,
    "PAYMENT": FECHA + estado("DueDate"),
    "CANCELPAYMENT": "",
    "REJECTION": FECHA + motivo("01"),
    "CANCELREJECTION": "",
    "SETTLEMENT": FECHA,
    "CANCELSETTLEMENT": "",
    "DEFAULT": FECHA,
    "CANCELDEFAULT": "",
}


def respuesta(codigo, dentro="", factura_=FACTURA):
    return (f"<cac:DocumentResponse><cac:Response><cbc:ResponseCode>{codigo}"
            f"</cbc:ResponseCode>{dentro}</cac:Response>{factura_}</cac:DocumentResponse>")


def mensaje(codigo=None, dentro=None, factura_=FACTURA, respuestas=None):
    """Un `ApplicationResponse` que valida contra UBL 2.5, con sus respuestas."""
    if respuestas is None:
        respuestas = respuesta(codigo, BUENO[codigo] if dentro is None else dentro, factura_)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<ApplicationResponse xmlns="urn:oasis:names:specification:ubl:schema:xsd:ApplicationResponse-2"
    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:UBLVersionID>2.5</cbc:UBLVersionID>
  <cbc:ID>M-1</cbc:ID>
  <cbc:IssueDate>2026-10-12</cbc:IssueDate>
  <cac:SenderParty><cac:PartyLegalEntity><cbc:RegistrationName>Comprador SA</cbc:RegistrationName></cac:PartyLegalEntity></cac:SenderParty>
  <cac:ReceiverParty><cac:PartyLegalEntity><cbc:RegistrationName>AEAT</cbc:RegistrationName></cac:PartyLegalEntity></cac:ReceiverParty>
  {respuestas}
</ApplicationResponse>"""


@pytest.fixture(scope="module")
def catalogo(esquemas_del_paquete):
    return Catalogo(esquemas_del_paquete)


def medir(xml, catalogo=None):
    return factura.validar(xml.encode("utf-8"), catalogo=catalogo)


def quejas(informe, gravedad=None):
    return [i for i in informe.incidencias
            if i.codigo.startswith("SPFE-MENSAJE-") and i.codigo != "SPFE-MENSAJE-ALCANCE"
            and (gravedad is None or i.gravedad == gravedad)]


def codigos(informe):
    return [(i.codigo, i.gravedad) for i in quejas(informe)]


# --- 1. La tabla es la del BOE --------------------------------------------------


class TestLaTabla:
    def test_los_recuentos_son_los_medidos(self):
        """Nueve mensajes, 59 filas y una lista, del XML del BOE del 05-10-2026."""
        assert set(mensajes_es.MENSAJES) == CODIGOS
        assert sum(len(m.filas) for m in mensajes_es.MENSAJES.values()) == 59
        assert {c for c, m in mensajes_es.MENSAJES.items() if m.anexo == "I"} == {"CANCELINVOICE"}
        assert mensajes_es.LISTAS["L1"].valores == {
            "01": "Rechazo comercial",
            "02": "Rechazo por ser un consumo particular o no estar afectado a la actividad.",
        }

    def test_la_l1_de_aqui_no_es_la_del_anexo_i(self):
        """Dos listas «L1» en la misma orden: errata 9 del informe del 06-10."""
        assert cius_es.LISTAS["L1"].valores != mensajes_es.LISTAS["L1"].valores
        assert "380" in cius_es.LISTAS["L1"].valores

    def test_sale_del_mismo_xml_que_el_anexo_i(self):
        huella = re.search(r"SHA-256 ([0-9a-f]{64})", mensajes_es.__doc__).group(1)
        assert huella == re.search(r"SHA-256 ([0-9a-f]{64})", cius_es.__doc__).group(1)

    @pytest.mark.skipif(not ANEXO.exists(), reason="no está `anexos/orden-hac-1028-2026.xml`")
    def test_la_huella_es_la_del_xml(self):
        declarada = re.search(r"SHA-256 ([0-9a-f]{64})", mensajes_es.__doc__).group(1)
        assert hashlib.sha256(ANEXO.read_bytes()).hexdigest() == declarada

    @pytest.mark.skipif(not ANEXO.exists(), reason="no está `anexos/orden-hac-1028-2026.xml`")
    def test_volver_a_extraer_da_exactamente_lo_mismo(self, tmp_path):
        """No basta con que el XML no cambie: alguien puede tocar el extractor."""
        from herramientas import mensajes as extractor

        destino = tmp_path / "mensajes_es.py"
        extractor.escribe_modulo(str(ANEXO), destino)
        hoy = (RAIZ / "validador" / "mensajes_es.py").read_bytes().replace(b"\r\n", b"\n")
        assert destino.read_bytes().replace(b"\r\n", b"\n") == hoy

    def test_la_celda_que_ocupa_dos_filas_se_pone_en_las_dos(self):
        """Sin esto, la fila de abajo salía con las columnas corridas."""
        from herramientas.mensajes import _filas_con_huecos

        tabla = etree.fromstring(
            "<table><tr><td>a</td><td rowspan='2'>larga</td><td>x</td></tr>"
            "<tr><td>b</td><td>y</td></tr></table>")
        assert _filas_con_huecos(tabla) == [["a", "larga", "x"], ["b", "larga", "y"]]


# --- 2. Se lee como se decidió ---------------------------------------------------

XS = "{http://www.w3.org/2001/XMLSchema}"


def _esquema(raiz):
    """Qué hijos admite cada tipo, y de qué tipo es cada elemento, por prefijo."""
    comun = raiz / "ubl-2.5" / "common"
    modulos = {
        "cbc": comun / "UBL-CommonBasicComponents-2.5.xsd",
        "cac": comun / "UBL-CommonAggregateComponents-2.5.xsd",
        "": raiz / "ubl-2.5" / "maindoc" / "UBL-ApplicationResponse-2.5.xsd",
    }
    tipo_de, hijos_de = {}, {}
    for prefijo, modulo in modulos.items():
        for e in etree.parse(str(modulo)).getroot():
            if e.tag == XS + "element" and e.get("name"):
                tipo_de[(prefijo, e.get("name"))] = (e.get("type") or "").split(":")[-1]
            if e.tag == XS + "complexType" and e.get("name"):
                hijos_de[e.get("name")] = [
                    h.get("ref") for h in e.iter(XS + "element") if h.get("ref")]
    return tipo_de, hijos_de


def _andar(ruta, tipo_de, hijos_de):
    """Recorre una ruta relativa a `cac:DocumentResponse`. None si llega."""
    actual = "DocumentResponseType"
    for paso in ruta.split("/"):
        paso = paso.split("=")[0]
        if paso not in hijos_de.get(actual, []):
            return f"«{paso}» no es hijo de {actual}"
        prefijo, nombre = paso.split(":")
        actual = tipo_de.get((prefijo, nombre), "?")
    return None


class TestComoSeLee:
    def test_las_erratas_arregladas_son_las_medidas(self):
        """Si el BOE corrige una, la cuenta cambia y esto salta: el arreglo sobra."""
        assert dict(mensajes.ARREGLOS) == {
            mensajes.DOS_RUTAS: 8,
            mensajes.RENGLON: 16,
            mensajes.ESPACIO: 1,
            mensajes.BARRA_DOBLE: 1,
            mensajes.FACTURA_EN_LA_RESPUESTA: 6,
            mensajes.NOMBRE_EN_EL_IMPUESTO: 1,
        }

    def test_las_dos_de_la_anulacion_son_solo_de_la_anulacion(self):
        con = {c for c, p in mensajes.PLANES.items() if p.erratas}
        assert con == {"CANCELINVOICE"}

    def test_lo_que_se_mide_de_cada_mensaje(self):
        p = mensajes.PLANES
        assert {c for c in CODIGOS if p[c].fecha} == ALTAS
        assert p["PAYMENT"].fechas == {
            "DueDate": ("Fecha de vencimiento del plazo de pago", True),
            "ShipmentDate": ("Fecha de recepción de las mercancías o de los servicios prestados", False),
            "ReceptionDate": ("Fecha de recepción de la factura", False),
        }
        assert set(p["SETTLEMENT"].fechas) == {"DueDate", "ShipmentDate", "ReceptionDate"}
        assert not any(o for _, o in p["SETTLEMENT"].fechas.values())
        assert set(p["DEFAULT"].fechas) == {"ShipmentDate", "ReceptionDate"}
        assert p["SETTLEMENT"].indicadores == {"FinancingArrangement": "Mecanismo de financiación"}
        assert set(p["PAYMENT"].razones) == {"CorrectedInvoice", "NegativeAmountInvoice"}
        assert {c for c in CODIGOS if p[c].motivo} == {"REJECTION"}
        assert {c for c in CODIGOS if p[c].varias_facturas} == {"CANCELINVOICE"}
        for c in BAJAS:
            assert (p[c].fecha, p[c].fechas, p[c].indicadores, p[c].razones) == ("", {}, {}, {})

    def test_las_rutas_que_se_buscan_andan_por_ubl_2_5(self, esquemas_del_paquete):
        tipo_de, hijos_de = _esquema(esquemas_del_paquete)
        rutas = {mensajes._FECHA, mensajes._FECHA_DE_ESTADO, mensajes._MOTIVO,
                 mensajes._STATUS + "/cac:Condition/cbc:AttributeID",
                 mensajes._STATUS + "/cbc:StatusReason", "cac:Response/cbc:ResponseCode"}
        for plan in mensajes.PLANES.values():
            for donde in plan.datos.values():
                rutas.update(f"{mensajes._FACTURA}/{r}" for r in donde)
        assert {r: f for r in sorted(rutas) if (f := _andar(r, tipo_de, hijos_de))} == {}

    def test_y_las_dos_de_la_anulacion_tal_cual_no(self, esquemas_del_paquete):
        """Lo que dice la nota: escritas como en el BOE, no existen."""
        tipo_de, hijos_de = _esquema(esquemas_del_paquete)
        assert _andar("cac:Response/cac:DocumentReference", tipo_de, hijos_de)
        assert _andar(mensajes._NOMBRE_DENTRO_DEL_IMPUESTO, tipo_de, hijos_de)

    def test_una_fila_que_no_se_sabe_medir_no_deja_importar(self):
        pago = mensajes_es.MENSAJES["PAYMENT"]
        rara = dataclasses.replace(pago.filas[0], ruta=mensajes_es.RUTA_DEL_CODIGO.replace(
            "cbc:ResponseCode", "cbc:Description"))
        with pytest.raises(AnexoCambiado):
            mensajes._plan("PAYMENT", dataclasses.replace(pago, filas=(rara, *pago.filas[1:])))

    def test_un_dato_de_la_factura_que_deja_de_ser_obligatorio_tampoco(self):
        pago = mensajes_es.MENSAJES["CANCELPAYMENT"]
        relajada = dataclasses.replace(pago.filas[2], cardinalidad="0..1")
        with pytest.raises(AnexoCambiado):
            mensajes._plan("CANCELPAYMENT", dataclasses.replace(
                pago, filas=(*pago.filas[:2], relajada, *pago.filas[3:])))

    def test_otra_fecha_obligatoria_tampoco(self):
        """`SPFE-MENSAJE-VENCIMIENTO` es la del vencimiento: otra pediría otra regla."""
        pago = mensajes_es.MENSAJES["PAYMENT"]
        obligatoria = dataclasses.replace(pago.filas[3], cardinalidad="1..1")
        with pytest.raises(AnexoCambiado):
            mensajes._plan("PAYMENT", dataclasses.replace(
                pago, filas=(*pago.filas[:3], obligatoria, *pago.filas[4:])))

    def test_cada_mensaje_tiene_nombre(self):
        assert set(mensajes.NOMBRES) == set(mensajes_es.MENSAJES)


# --- 3. Las reglas -----------------------------------------------------------------


class TestElMensajeBueno:
    @pytest.mark.parametrize("codigo", sorted(CODIGOS))
    def test_sale_limpio_con_su_nota(self, codigo, catalogo):
        informe = medir(mensaje(codigo), catalogo)
        assert informe.validado
        assert [(i.codigo, i.gravedad) for i in informe.incidencias] == [
            ("SPFE-MENSAJE-ALCANCE", NOTA)]

    def test_con_todo_lo_opcional_tambien(self, catalogo):
        pago = (FECHA + estado("DueDate") + estado("ShipmentDate") + estado("ReceptionDate")
                + "<cac:Status><cbc:StatusReason>CorrectedInvoice</cbc:StatusReason></cac:Status>")
        cobro = FECHA + estado("DueDate") + estado("FinancingArrangement", fecha=None)
        for codigo, dentro in (("PAYMENT", pago), ("SETTLEMENT", cobro)):
            informe = medir(mensaje(codigo, dentro), catalogo)
            assert [i.codigo for i in informe.incidencias] == ["SPFE-MENSAJE-ALCANCE"]

    def test_una_respuesta_de_peppol_no_se_mide(self):
        """`AP` es de la UNCL 4343: ni nota ni quejas, como hasta ahora."""
        informe = medir(mensaje("AP", ""))
        assert not [i for i in informe.incidencias if i.codigo.startswith("SPFE-")]

    def test_el_codigo_se_lee_letra_a_letra(self):
        """`payment` no es `PAYMENT`: no se mide, y el informe dice que no se mira."""
        informe = medir(mensaje("payment", ""))
        assert not [i for i in informe.incidencias if i.codigo.startswith("SPFE-")]

    def test_a_una_factura_no_le_toca(self):
        datos = (RAIZ / "ejemplos" / "f-0001.xml").read_bytes()
        d = detectar(datos)
        assert mensajes.reglas(etree.fromstring(datos), d) == []


class TestLaFecha:
    @pytest.mark.parametrize("codigo", sorted(ALTAS))
    def test_sin_la_fecha_del_mensaje(self, codigo):
        dentro = BUENO[codigo].replace(FECHA, "")
        informe = medir(mensaje(codigo, dentro))
        assert codigos(informe) == [("SPFE-MENSAJE-FECHA", ERROR)]
        assert mensajes.PLANES[codigo].fecha.lower() in quejas(informe)[0].mensaje.lower()

    @pytest.mark.parametrize("codigo", sorted(BAJAS))
    def test_las_bajas_no_la_llevan(self, codigo):
        assert codigos(medir(mensaje(codigo, ""))) == []

    def test_en_el_impago_es_la_del_vencimiento(self):
        queja = quejas(medir(mensaje("DEFAULT", "")))[0]
        assert "Falta la fecha de vencimiento del pago en la comunicación del impago" in queja.mensaje


class TestElVencimiento:
    def test_el_pago_sin_vencimiento(self):
        informe = medir(mensaje("PAYMENT", FECHA))
        assert codigos(informe) == [("SPFE-MENSAJE-VENCIMIENTO", ERROR)]
        assert "apartado 1 del artículo 7" in quejas(informe)[0].mensaje

    def test_con_la_condicion_y_sin_la_fecha_no_vale(self):
        informe = medir(mensaje("PAYMENT", FECHA + estado("DueDate", fecha=None)))
        assert sorted(codigos(informe)) == [
            ("SPFE-MENSAJE-ESTADO", ERROR), ("SPFE-MENSAJE-VENCIMIENTO", ERROR)]

    def test_con_la_fecha_y_otra_condicion_tampoco(self):
        informe = medir(mensaje("PAYMENT", FECHA + estado("ShipmentDate")))
        assert codigos(informe) == [("SPFE-MENSAJE-VENCIMIENTO", ERROR)]

    def test_en_el_cobro_es_opcional(self):
        assert codigos(medir(mensaje("SETTLEMENT", FECHA))) == []


class TestLoQueVaEnElEstado:
    def test_una_condicion_repetida(self):
        informe = medir(mensaje("PAYMENT", FECHA + estado("DueDate") + estado("DueDate", "2026-12-01")))
        assert codigos(informe) == [("SPFE-MENSAJE-ESTADO", ERROR)]
        assert "2 veces" in quejas(informe)[0].mensaje

    def test_una_fecha_opcional_sin_su_fecha(self):
        informe = medir(mensaje("SETTLEMENT", FECHA + estado("ReceptionDate", fecha=None)))
        assert codigos(informe) == [("SPFE-MENSAJE-ESTADO", ERROR)]

    def test_una_condicion_con_otra_mayuscula_es_un_aviso(self):
        informe = medir(mensaje("PAYMENT", FECHA + estado("DueDate") + estado("Duedate")))
        assert codigos(informe) == [("SPFE-MENSAJE-ESTADO", AVISO)]
        assert "«Duedate»" in quejas(informe)[0].mensaje

    def test_la_financiacion_es_del_cobro_y_no_del_pago(self):
        con = estado("FinancingArrangement", fecha=None)
        assert codigos(medir(mensaje("SETTLEMENT", FECHA + con))) == []
        assert codigos(medir(mensaje("PAYMENT", BUENO["PAYMENT"] + con))) == [
            ("SPFE-MENSAJE-ESTADO", AVISO)]

    def test_un_status_reason_que_no_esta(self):
        raro = "<cac:Status><cbc:StatusReason>Pagada</cbc:StatusReason></cac:Status>"
        assert codigos(medir(mensaje("PAYMENT", BUENO["PAYMENT"] + raro))) == [
            ("SPFE-MENSAJE-ESTADO", AVISO)]

    def test_un_motivo_fuera_del_rechazo(self):
        assert codigos(medir(mensaje("PAYMENT", BUENO["PAYMENT"] + motivo("01")))) == [
            ("SPFE-MENSAJE-ESTADO", AVISO)]

    def test_en_una_baja_no_va_nada(self):
        queja = quejas(medir(mensaje("CANCELPAYMENT", estado("DueDate"))))
        assert [(q.codigo, q.gravedad) for q in queja] == [("SPFE-MENSAJE-ESTADO", AVISO)]
        assert "allí no hay ninguna" in queja[0].mensaje


class TestElMotivo:
    @pytest.mark.parametrize("valor", ["01", "02"])
    def test_los_dos_de_la_lista(self, valor):
        assert codigos(medir(mensaje("REJECTION", FECHA + motivo(valor)))) == []

    def test_sin_motivo(self):
        informe = medir(mensaje("REJECTION", FECHA))
        assert codigos(informe) == [("SPFE-MENSAJE-MOTIVO", ERROR)]
        assert "lista L1" in quejas(informe)[0].mensaje

    def test_uno_que_no_esta(self):
        informe = medir(mensaje("REJECTION", FECHA + motivo("03")))
        assert codigos(informe) == [("SPFE-MENSAJE-MOTIVO", ERROR)]
        assert quejas(informe)[0].encontrado == "03"

    def test_dos(self):
        informe = medir(mensaje("REJECTION", FECHA + motivo("01") + motivo("02")))
        assert codigos(informe) == [("SPFE-MENSAJE-MOTIVO", ERROR)]


class TestLaFactura:
    @pytest.mark.parametrize("quitar,falta", [
        ("<cbc:ID>F-2026-0101</cbc:ID>", "el número"),
        ("<cbc:IssueDate>2026-10-06</cbc:IssueDate>", "la fecha de expedición"),
        ("<cbc:CompanyID>B12345674</cbc:CompanyID>", "el NIF del emisor"),
        ("<cbc:RegistrationName>Vendedor SL</cbc:RegistrationName>", "el nombre o razón social"),
    ])
    @pytest.mark.parametrize("codigo", sorted(CODIGOS))
    def test_cada_dato_que_falta(self, codigo, quitar, falta):
        informe = medir(mensaje(codigo, factura_=FACTURA.replace(quitar, "")))
        assert codigos(informe) == [("SPFE-MENSAJE-FACTURA", ERROR)]
        assert falta in quejas(informe)[0].mensaje

    def test_dos_que_faltan_en_plural(self):
        sin = FACTURA.replace("<cbc:IssueDate>2026-10-06</cbc:IssueDate>", "").replace(
            "<cbc:CompanyID>B12345674</cbc:CompanyID>", "")
        assert "le faltan la fecha de expedición y el NIF del emisor" in quejas(
            medir(mensaje("CANCELPAYMENT", factura_=sin)))[0].mensaje

    def test_en_la_anulacion_el_nombre_vale_en_los_dos_sitios(self, catalogo):
        en_el_impuesto = FACTURA.replace(
            "<cbc:CompanyID>B12345674</cbc:CompanyID>",
            "<cbc:RegistrationName>Vendedor SL</cbc:RegistrationName>"
            "<cbc:CompanyID>B12345674</cbc:CompanyID>").replace(
            "<cac:PartyLegalEntity><cbc:RegistrationName>Vendedor SL</cbc:RegistrationName>"
            "</cac:PartyLegalEntity>", "")
        assert codigos(medir(mensaje("CANCELINVOICE", factura_=en_el_impuesto), catalogo)) == []
        # En el anexo II la ruta está bien escrita, y no se busca en otro sitio.
        assert codigos(medir(mensaje("CANCELPAYMENT", factura_=en_el_impuesto))) == [
            ("SPFE-MENSAJE-FACTURA", ERROR)]

    def test_la_anulacion_admite_varias_y_el_anexo_ii_una(self, catalogo):
        assert codigos(medir(mensaje("CANCELINVOICE", factura_=FACTURA * 2), catalogo)) == []
        informe = medir(mensaje("PAYMENT", factura_=FACTURA * 2), catalogo)
        assert codigos(informe) == [("SPFE-MENSAJE-FACTURA", ERROR)]
        assert "1..1" in quejas(informe)[0].mensaje

    def test_sin_ninguna(self):
        """El esquema ya lo pide; sin esquema, que no se cuele."""
        assert codigos(medir(mensaje("CANCELPAYMENT", factura_=""))) == [
            ("SPFE-MENSAJE-FACTURA", ERROR)]

    def test_un_nif_con_el_control_mal(self):
        informe = medir(mensaje("CANCELPAYMENT", factura_=FACTURA.replace("B12345674", "B12345678")))
        assert codigos(informe) == [("SPFE-MENSAJE-FACTURA", ERROR)]
        assert "debería ser 4" in quejas(informe)[0].mensaje

    def test_con_el_prefijo_es_vale(self):
        """La nota lo dice: la ruta es la del NIF-IVA, que lo lleva."""
        assert codigos(medir(mensaje("CANCELPAYMENT", factura_=FACTURA.replace(
            "B12345674", "ESB12345674")))) == []

    def test_uno_de_otro_pais_es_un_aviso(self):
        assert codigos(medir(mensaje("CANCELPAYMENT", factura_=FACTURA.replace(
            "B12345674", "NL123456789B01")))) == [("SPFE-MENSAJE-FACTURA", AVISO)]


class TestLaAnulacionComoLaEscribeElBoe:
    def test_no_pasa_el_esquema_y_la_factura_queda_a_medias(self, catalogo):
        """La factura dentro de `cac:Response`, y en `cac:DocumentResponse` solo
        lo que el esquema obliga a poner."""
        xml = mensaje(respuestas=respuesta(
            "CANCELINVOICE", FECHA + FACTURA,
            "<cac:DocumentReference><cbc:ID>F-2026-0101</cbc:ID></cac:DocumentReference>"))
        informe = medir(xml, catalogo)
        assert ("XSD-ORDEN", ERROR) in [(i.codigo, i.gravedad) for i in informe.incidencias]
        assert codigos(informe) == [("SPFE-MENSAJE-FACTURA", ERROR)]

    def test_la_nota_dice_como_se_ha_leido(self):
        nota = medir(mensaje("CANCELINVOICE")).incidencias[0]
        assert nota.codigo == "SPFE-MENSAJE-ALCANCE"
        assert "no existen en UBL 2.5" in nota.mensaje
        assert "cac:DocumentResponse/cac:DocumentReference" in nota.mensaje

    @pytest.mark.parametrize("codigo", sorted(CODIGOS - {"CANCELINVOICE"}))
    def test_y_en_los_demas_no_lo_dice(self, codigo):
        nota = medir(mensaje(codigo)).incidencias[0]
        assert "no existen en UBL 2.5" not in nota.mensaje


class TestLaNota:
    def test_una_por_documento_con_todos_sus_mensajes(self):
        xml = mensaje(respuestas=respuesta("PAYMENT", BUENO["PAYMENT"])
                      + respuesta("REJECTION", BUENO["REJECTION"]))
        notas = [i for i in medir(xml).incidencias if i.codigo == "SPFE-MENSAJE-ALCANCE"]
        assert len(notas) == 1
        assert notas[0].encontrado == "PAYMENT, REJECTION"

    def test_dice_las_respuestas_que_no_son_de_la_orden(self):
        xml = mensaje(respuestas=respuesta("PAYMENT", BUENO["PAYMENT"]) + respuesta("AP"))
        nota = medir(xml).incidencias[0]
        assert "La otra respuesta del documento no es un mensaje de la orden" in nota.mensaje

    def test_el_vencimiento_solo_donde_lo_hay(self):
        con = {c for c in CODIGOS if "Ley 3/2004" in medir(mensaje(c)).incidencias[0].mensaje}
        assert con == {"PAYMENT", "SETTLEMENT", "DEFAULT"}

    def test_el_tax_scheme_del_nif_no_se_mira_y_se_dice(self):
        """Preguntado al buzón el 07-10-2026: ninguna tabla dice cuál."""
        sin_vat = FACTURA.replace("<cbc:ID>VAT</cbc:ID>", "<cbc:ID>LOC</cbc:ID>")
        informe = medir(mensaje("CANCELPAYMENT", factura_=sin_vat))
        assert codigos(informe) == []
        assert "cualquier impuesto en su cac:TaxScheme" in informe.incidencias[0].mensaje

    def test_el_articulo_de_la_sede_solo_en_el_anexo_ii(self):
        assert "artículo 7" not in medir(mensaje("CANCELINVOICE")).incidencias[0].mensaje
        assert "apartado 3 del artículo 7" in medir(mensaje("CANCELPAYMENT")).incidencias[0].mensaje


# --- 4. Lo que el informe promete ------------------------------------------------------


def _lote(tmp_path, catalogo, *xmls):
    rutas = []
    for n, xml in enumerate(xmls):
        ruta = tmp_path / f"m{n}.xml"
        ruta.write_text(xml, encoding="utf-8")
        rutas.append(ruta)
    return factura.validar_lote(rutas, catalogo=catalogo)


class TestLoQueElInformeDice:
    def test_la_frase_entera_de_un_pago(self, tmp_path, catalogo):
        lote = _lote(tmp_path, catalogo, mensaje("PAYMENT"))
        assert lote.alcance() == (
            "«Sin errores» quiere decir que se ha comprobado la forma contra el "
            "esquema XSD, lo que la orden de la solución pública pide a sus "
            "mensajes de anulación y de estado (lo que no se mide lo dice la nota "
            "SPFE-MENSAJE-ALCANCE).\nNo se comprueba la validez de las firmas "
            "electrónicas, ni si lo que dice la factura es cierto."
        )
        partes = {p.nombre: p for p in lote.partes()}
        assert partes["El contenido"].resultado == "Sin errores"

    def test_con_otra_respuesta_al_lado_dice_las_demas(self, tmp_path, catalogo):
        de_peppol = mensaje("AP", "")
        lote = _lote(tmp_path, catalogo, mensaje("PAYMENT"), de_peppol)
        frase = lote.alcance()
        assert "SPFE-MENSAJE-ALCANCE" in frase
        assert "el contenido de las demás respuestas (ApplicationResponse)" in frase

    def test_sin_ningun_mensaje_de_la_orden_como_siempre(self, tmp_path, catalogo):
        frase = _lote(tmp_path, catalogo, mensaje("AP", "")).alcance()
        assert "SPFE-MENSAJE-ALCANCE" not in frase
        assert "el contenido de las respuestas (ApplicationResponse)" in frase

    def test_sin_su_esquema_sigue_sin_comprobar(self):
        """Medida la tabla, la comprobación principal sigue siendo la forma."""
        informe = medir(mensaje("PAYMENT"))
        assert [i.codigo for i in informe.incidencias] == ["SPFE-MENSAJE-ALCANCE"]
        assert not informe.validado

    def test_un_mensaje_roto_no_sale_correcto(self, tmp_path, catalogo):
        lote = _lote(tmp_path, catalogo, mensaje("PAYMENT", FECHA))
        assert not lote.conforme
        partes = {p.nombre: p for p in lote.partes()}
        assert partes["El contenido"].resultado == "1 error"
