"""Comprobaciones de la validación de forma y de su traducción.

Los esquemas de aquí son de mentira, pequeños y escritos a mano. No se
descarga nada: lo que hay que probar es el catálogo y la traducción de los
mensajes de libxml2, y para eso un esquema de doce líneas sirve igual que los
tres megas de UBL 2.1 —y no deja la suite dependiendo de una descarga.

Aun así el esquema está repartido en dos ficheros que se importan entre sí,
como los oficiales, porque que las rutas relativas funcionen es justo lo que
puede fallar al instalarlos de verdad.
"""

from pathlib import Path

import pytest

from validador import esquema, factura
from validador.esquema import Catalogo
from validador.incidencias import AVISO, ERROR

NS_INVOICE = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
NS_CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"

COMUNES = f"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="{NS_CBC}" elementFormDefault="qualified">
  <xs:element name="ID">
    <xs:simpleType><xs:restriction base="xs:string">
      <xs:maxLength value="20"/>
    </xs:restriction></xs:simpleType>
  </xs:element>
  <xs:element name="IssueDate" type="xs:date"/>
  <xs:element name="Note" type="xs:string"/>
  <xs:element name="InvoiceTypeCode">
    <xs:simpleType><xs:restriction base="xs:string">
      <xs:enumeration value="380"/><xs:enumeration value="381"/>
    </xs:restriction></xs:simpleType>
  </xs:element>
  <xs:element name="CompanyID">
    <xs:simpleType><xs:restriction base="xs:string">
      <xs:pattern value="[A-Z][0-9]{{7}}[0-9A-J]"/>
    </xs:restriction></xs:simpleType>
  </xs:element>
  <xs:element name="PayableAmount">
    <xs:complexType><xs:simpleContent><xs:extension base="xs:decimal">
      <xs:attribute name="currencyID" type="xs:string" use="required"/>
    </xs:extension></xs:simpleContent></xs:complexType>
  </xs:element>
</xs:schema>"""

PRINCIPAL = f"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:cbc="{NS_CBC}"
           targetNamespace="{NS_INVOICE}" elementFormDefault="qualified">
  <xs:import namespace="{NS_CBC}"
             schemaLocation="../common/UBL-CommonBasicComponents-2.1.xsd"/>
  <xs:element name="Invoice">
    <xs:complexType><xs:sequence>
      <xs:element ref="cbc:ID"/>
      <!-- Repetible sin limite, como AdditionalDocumentReference en UBL: hace
           falta uno asi para distinguir «esta mal colocado» de «sobra». Va
           antes de IssueDate para poder ponerlo despues en el documento. -->
      <xs:element ref="cbc:Note" minOccurs="0" maxOccurs="unbounded"/>
      <xs:element ref="cbc:IssueDate"/>
      <xs:element ref="cbc:InvoiceTypeCode"/>
      <xs:element ref="cbc:CompanyID" minOccurs="0"/>
      <xs:element ref="cbc:PayableAmount" minOccurs="0"/>
    </xs:sequence></xs:complexType>
  </xs:element>
</xs:schema>"""


@pytest.fixture
def catalogo(tmp_path):
    """Un catálogo con el esquema en dos ficheros, como los de verdad."""
    (tmp_path / "ubl" / "maindoc").mkdir(parents=True)
    (tmp_path / "ubl" / "common").mkdir(parents=True)
    (tmp_path / "ubl" / "maindoc" / "UBL-Invoice-2.1.xsd").write_text(
        PRINCIPAL, encoding="utf-8"
    )
    (tmp_path / "ubl" / "common" / "UBL-CommonBasicComponents-2.1.xsd").write_text(
        COMUNES, encoding="utf-8"
    )
    return Catalogo(tmp_path)


def factura_xml(cuerpo):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="{NS_INVOICE}" xmlns:cbc="{NS_CBC}">
{cuerpo}
</Invoice>"""


CORRECTA = factura_xml(
    """  <cbc:ID>F-2026-0001</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
)


def revisar(xml, catalogo):
    return esquema.validar(xml, catalogo=catalogo).incidencias


def codigos(incidencias, gravedad=None):
    return {
        i.codigo for i in incidencias if gravedad is None or i.gravedad == gravedad
    }


def una(incidencias, codigo):
    return next(i for i in incidencias if i.codigo == codigo)


class TestRepetidoFrenteADesordenado:
    """Que algo aparezca dos veces no significa que sobre.

    Salio de instalar los esquemas oficiales y pasarlos por facturas ajenas: un
    `AdditionalDocumentReference` -que UBL admite sin limite- colocado despues
    de `AccountingCustomerParty` en vez de antes de `AccountingSupplierParty`
    salia como «aparece 2 veces y el esquema no admite tantas». Quien leyera eso
    borraria uno y no arreglaria nada, porque el problema era la posicion.

    La cuenta a secas no distingue los dos casos. Lo que hace que uno sobre es
    que otro igual haya pasado ya por su sitio bueno: si el que se queja es el
    primero, el problema es donde esta.
    """

    def test_repetible_pero_mal_colocado_es_desorden(self, catalogo):
        # Las dos Note van despues de IssueDate cuando el esquema las pone
        # antes, y lo que se espera -InvoiceTypeCode- aparece mas adelante.
        roto = factura_xml(
            """  <cbc:ID>F-2026-0001</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:Note>una</cbc:Note>
  <cbc:Note>y otra</cbc:Note>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-ORDEN")
        assert "cambiados de sitio" in problema.mensaje
        assert "veces" not in problema.mensaje, (
            "contarlos despista: son dos porque la norma deja, y el fallo es "
            "que van despues de InvoiceTypeCode en vez de antes")

    def test_el_que_de_verdad_sobra_se_sigue_llamando_repetido(self, catalogo):
        """La otra mitad: el arreglo no puede tapar el caso que ya funcionaba."""
        roto = factura_xml(
            """  <cbc:ID>F-2026-0001</cbc:ID>
  <cbc:ID>F-2026-0002</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-ORDEN")
        assert "2 veces" in problema.mensaje
        assert "cambiados de sitio" not in problema.mensaje


# --- El catálogo -----------------------------------------------------------


class TestCatalogo:
    def test_carpeta_que_no_existe(self, tmp_path):
        assert Catalogo(tmp_path / "no-esta").vacio

    def test_carpeta_sin_esquemas(self, tmp_path):
        (tmp_path / "leeme.txt").write_text("nada", encoding="utf-8")
        assert Catalogo(tmp_path).vacio

    def test_con_esquemas_no_esta_vacio(self, catalogo):
        assert not catalogo.vacio

    def test_encuentra_el_esquema_donde_sea(self, catalogo):
        from validador.formato import detectar

        ruta = catalogo.ruta_para(detectar(CORRECTA))
        assert ruta is not None
        assert ruta.name == "UBL-Invoice-2.1.xsd"

    def test_las_rutas_relativas_del_import_funcionan(self, catalogo):
        """El esquema principal importa el de comunes con una ruta relativa."""
        from validador.formato import detectar

        assert catalogo.esquema_para(detectar(CORRECTA)) is not None

    def test_el_esquema_compilado_se_reaprovecha(self, catalogo):
        """Compilar UBL 2.1 tarda; en un lote de 300 no puede repetirse."""
        from validador.formato import detectar

        deteccion = detectar(CORRECTA)
        assert catalogo.esquema_para(deteccion) is catalogo.esquema_para(deteccion)

    def test_un_abono_pide_otro_esquema(self, catalogo):
        from validador.formato import Deteccion
        from validador.formato import UBL as familia_ubl

        abono = Deteccion(familia=familia_ubl, tipo_documento="abono")
        assert catalogo.ruta_para(abono) is None  # no hay CreditNote instalado
        assert "UBL-CreditNote-2.1.xsd" in esquema._nombres_esperados(abono)

    def test_por_defecto_lee_la_variable_de_entorno(self, tmp_path, monkeypatch):
        monkeypatch.setenv(esquema.VARIABLE_ENTORNO, str(tmp_path))
        assert Catalogo.por_defecto().carpeta == tmp_path


class TestSinEsquemas:
    def test_sin_nada_instalado_no_se_dice_nada(self, tmp_path):
        """No tiene sentido un aviso por fichero: lo dice quien orquesta."""
        assert revisar(CORRECTA, Catalogo(tmp_path / "vacia")) == []


class TestUnDocumentoConEntidades:
    """libxml2 se niega a validar un árbol con referencias sin expandir.

    Y no se niega con un fallo de esquema, que sería lo llevadero: levanta
    `XMLSchemaValidateError: Internal error in XML Schema validation`, que
    salía por el informe como VALIDADOR-SE-ATRAGANTA y se llevaba por delante
    **todas** las demás comprobaciones del fichero. Medido el 21-09-2026 sobre
    un Facturae con `<!ENTITY monto "1.00">`: una sola línea, y en inglés.

    Aquí no se expanden a propósito —`test_formato.TestSeguridad`—, así que lo
    que se puede hacer es no pasarle a libxml2 un árbol que no sabe validar.
    Que eso pasa se dice en su sitio, con `XML-ENTIDADES`.

    **Hace falta un catálogo de verdad.** El resto de la suite corre sin
    esquemas a propósito (`conftest.py`), así que la llamada ni llegaba a
    `validate` y una regresión aquí salía verde.
    """

    CON_ENTIDAD = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE Invoice [<!ENTITY numero "F-2026-0001">]>
<Invoice xmlns="{NS_INVOICE}" xmlns:cbc="{NS_CBC}">
  <cbc:ID>&numero;</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
</Invoice>'''

    def test_no_se_le_pasa_al_esquema(self, catalogo):
        """Si se le pasa, esto no falla: revienta."""
        assert revisar(self.CON_ENTIDAD, catalogo) == []

    def test_y_la_misma_sin_entidades_si_se_comprueba(self, catalogo):
        """Que el atajo de arriba no se haya llevado por delante la validación.

        Sin esta, saltarse el esquema siempre pasaría las dos.
        """
        mal = self.CON_ENTIDAD.replace(
            '<!DOCTYPE Invoice [<!ENTITY numero "F-2026-0001">]>\n', ""
        ).replace("&numero;", "0" * 30)  # maxLength=20 en el esquema de juguete
        assert codigos(revisar(mal, catalogo)), "el esquema ya no mira nada"

    def test_con_esquemas_pero_no_el_que_toca(self, catalogo):
        """Si instalaste UBL y te llega un CII, eso sí merece un aviso."""
        cii = """<?xml version="1.0"?>
<rsm:CrossIndustryInvoice
    xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"/>"""
        aviso = una(revisar(cii, catalogo), "XSD-SIN-ESQUEMA")
        assert aviso.gravedad == AVISO
        assert "CrossIndustryInvoice_100pD16B.xsd" in aviso.mensaje
        assert str(catalogo.carpeta) in aviso.mensaje


class TestIndice:
    """El disco se recorre una vez por catálogo, no una por consulta.

    Antes cada pregunta —«¿hay esquemas?», «¿dónde está este?»— salía a mirar
    el disco. Dos o tres veces por factura. Cada búsqueda era barata, porque
    `rglob` con un nombre concreto corta en cuanto lo encuentra, así que esto
    no era el cuello de botella que parecía: son décimas de segundo en un lote
    grande. Pero un índice hecho una vez es más simple de razonar y no depende
    de dónde caiga el fichero dentro del árbol.
    """

    def test_el_disco_se_mira_una_sola_vez(self, catalogo, monkeypatch):
        from pathlib import Path

        vueltas = []
        original = Path.rglob

        def contando(self, patron, **kwargs):
            vueltas.append(patron)
            return original(self, patron, **kwargs)

        monkeypatch.setattr(Path, "rglob", contando)
        for _ in range(10):
            assert not catalogo.vacio
            assert catalogo.ruta_para(_deteccion_ubl()) is not None
        assert len(vueltas) == 1, vueltas

    def test_el_indice_encuentra_lo_que_hay(self, catalogo):
        assert "UBL-Invoice-2.1.xsd" in catalogo.indice
        assert "UBL-CommonBasicComponents-2.1.xsd" in catalogo.indice

    def test_recargar_vuelve_a_mirar(self, catalogo, tmp_path):
        """Un esquema añadido en caliente no se ve hasta que se pide."""
        assert catalogo.ruta_para(_deteccion_abono()) is None
        (tmp_path / "ubl" / "maindoc" / "UBL-CreditNote-2.1.xsd").write_text(
            PRINCIPAL.replace('name="Invoice"', 'name="CreditNote"'),
            encoding="utf-8",
        )
        assert catalogo.ruta_para(_deteccion_abono()) is None  # sigue con el de antes
        catalogo.recargar()
        assert catalogo.ruta_para(_deteccion_abono()) is not None


class TestEsquemaRoto:
    """Un fichero que está pero no compila no puede tumbar el lote.

    Pasaba: la excepción de lxml salía de `esquema_para` y subía hasta arriba.
    Una descarga a medias en la carpeta de esquemas y trescientas facturas sin
    validar, con un traceback en vez de una frase.
    """

    @pytest.fixture
    def catalogo_roto(self, tmp_path):
        (tmp_path / "UBL-Invoice-2.1.xsd").write_text(
            "<esto no es un esquema/>", encoding="utf-8"
        )
        return Catalogo(tmp_path)

    def test_no_revienta_y_lo_dice(self, catalogo_roto):
        aviso = una(revisar(CORRECTA, catalogo_roto), "XSD-ESQUEMA-ROTO")
        assert aviso.gravedad == AVISO
        assert "UBL-Invoice-2.1.xsd" in aviso.campo

    def test_el_lote_sigue_adelante(self, catalogo_roto, tmp_path):
        ruta = tmp_path / "f.xml"
        ruta.write_text(CORRECTA, encoding="utf-8")
        lote = factura.validar_lote([ruta, ruta], catalogo=catalogo_roto)
        assert len(lote.informes) == 2

    def test_no_se_reintenta_compilarlo(self, catalogo_roto):
        """Compilar y fallar mil veces cuesta lo mismo que compilar mil veces."""
        for _ in range(5):
            revisar(CORRECTA, catalogo_roto)
        assert len(catalogo_roto._rotos) == 1


def _deteccion_ubl():
    from validador.formato import UBL, Deteccion

    return Deteccion(familia=UBL, tipo_documento="factura")


def _deteccion_abono():
    from validador.formato import UBL, Deteccion

    return Deteccion(familia=UBL, tipo_documento="abono")


# --- Traducción de cada tipo de incumplimiento -----------------------------


class TestTraduccion:
    def test_documento_correcto(self, catalogo):
        assert revisar(CORRECTA, catalogo) == []

    def test_ningun_mensaje_lleva_namespaces(self, catalogo):
        roto = factura_xml("  <cbc:ID>F1</cbc:ID>")
        for incidencia in revisar(roto, catalogo):
            assert "{urn:" not in str(incidencia), str(incidencia)

    def test_falta_un_hijo_obligatorio(self, catalogo):
        roto = factura_xml("  <cbc:ID>F1</cbc:ID>")
        problema = una(revisar(roto, catalogo), "XSD-FALTA")
        assert problema.gravedad == ERROR
        assert "Invoice" in problema.campo
        assert "IssueDate" in problema.esperado

    def test_elementos_cambiados_de_sitio(self, catalogo):
        """El caso que más cuesta ver: el XML es válido, el orden no."""
        roto = factura_xml(
            """  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:ID>F1</cbc:ID>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-ORDEN")
        assert "cambiados de sitio" in problema.mensaje
        assert "«ID» tiene que ir antes" in problema.mensaje

    def test_un_elemento_repetido_no_se_confunde_con_desorden(self, catalogo):
        """Con <ID/><ID/><IssueDate/>, lo esperado también va detrás.

        Si el desorden se mirara antes que la repetición, diría «están
        cambiados de sitio» cuando lo que pasa es que uno sobra.
        """
        roto = factura_xml(
            """  <cbc:ID>F1</cbc:ID>
  <cbc:ID>F2</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-ORDEN")
        assert "aparece 2 veces" in problema.mensaje
        assert "cambiados de sitio" not in problema.mensaje

    def test_elemento_que_el_esquema_no_conoce(self, catalogo):
        roto = factura_xml(
            """  <cbc:ID>F1</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:Chorrada>x</cbc:Chorrada>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-ORDEN")
        assert problema.encontrado == "Chorrada"
        assert "cambiados de sitio" not in problema.mensaje
        assert "O sobra" in problema.mensaje

    def test_valor_fuera_de_la_lista(self, catalogo):
        roto = factura_xml(
            """  <cbc:ID>F1</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>999</cbc:InvoiceTypeCode>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-VALOR")
        assert problema.encontrado == "999"
        assert "380" in problema.esperado and "381" in problema.esperado

    def test_fecha_con_el_formato_de_toda_la_vida(self, catalogo):
        roto = factura_xml(
            """  <cbc:ID>F1</cbc:ID>
  <cbc:IssueDate>02/03/2026</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-TIPO")
        assert "AAAA-MM-DD" in problema.mensaje
        assert "xs:date" not in problema.mensaje  # traducido, no copiado

    def test_una_fecha_que_no_existe(self, catalogo):
        """El 31 de febrero **ya** esta escrito AAAA-MM-DD.

        Contestarle «una fecha se escribe AAAA-MM-DD» es no haber mirado el
        valor: quien lee eso comprueba el formato, lo ve bien y no encuentra el
        fallo. La pista era un literal fijo por tipo y no dependia del valor.
        """
        roto = factura_xml(
            """  <cbc:ID>F1</cbc:ID>
  <cbc:IssueDate>2012-02-31</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-TIPO")
        assert "AAAA-MM-DD" not in problema.mensaje
        assert "febrero de 2012 tiene 29" in problema.mensaje

    def test_y_sabe_de_anios_bisiestos(self, catalogo):
        roto = factura_xml(
            """  <cbc:ID>F1</cbc:ID>
  <cbc:IssueDate>2011-02-29</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-TIPO")
        assert "febrero de 2011 tiene 28" in problema.mensaje

    def test_un_mes_que_no_existe(self, catalogo):
        roto = factura_xml(
            """  <cbc:ID>F1</cbc:ID>
  <cbc:IssueDate>2026-13-01</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-TIPO")
        assert "mes 13" in problema.mensaje

    def test_importe_a_la_espanola(self, catalogo):
        """Coma decimal y separador de miles: el error más repetido que hay."""
        roto = factura_xml(
            """  <cbc:ID>F1</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:PayableAmount currencyID="EUR">1.234,56</cbc:PayableAmount>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-TIPO")
        assert "1234.56" in problema.mensaje
        assert "1.234,56" in problema.mensaje

    def test_texto_demasiado_largo(self, catalogo):
        roto = factura_xml(
            f"""  <cbc:ID>{'F' * 30}</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-LONGITUD")
        assert problema.esperado == "20 caracteres como mucho"
        assert problema.encontrado == "30 caracteres"

    def test_no_encaja_con_el_patron(self, catalogo):
        roto = factura_xml(
            """  <cbc:ID>F1</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:CompanyID>hola</cbc:CompanyID>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-PATRON")
        assert problema.encontrado == "hola"

    def test_falta_un_atributo_obligatorio(self, catalogo):
        roto = factura_xml(
            """  <cbc:ID>F1</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>
  <cbc:PayableAmount>121.00</cbc:PayableAmount>"""
        )
        problema = una(revisar(roto, catalogo), "XSD-ATRIBUTO")
        assert "currencyID" in problema.mensaje

    def test_atributo_que_sobra(self, catalogo):
        roto = CORRECTA.replace("<Invoice ", '<Invoice ola="ke" ')
        problema = una(revisar(roto, catalogo), "XSD-ATRIBUTO")
        assert "ola" in problema.mensaje
        assert "no admite" in problema.mensaje

    def test_texto_suelto_donde_solo_caben_elementos(self, catalogo):
        roto = CORRECTA.replace("<Invoice", "<Invoice", 1).replace(
            f'xmlns:cbc="{NS_CBC}">', f'xmlns:cbc="{NS_CBC}">pegado sin querer'
        )
        problema = una(revisar(roto, catalogo), "XSD-TEXTO")
        assert "texto suelto" in problema.mensaje

    def test_raiz_que_el_esquema_no_reconoce(self, catalogo):
        """Un documento del namespace correcto pero con otra raíz."""
        roto = f'<?xml version="1.0"?><Invoice xmlns="{NS_INVOICE}"/>'
        incidencias = revisar(roto, catalogo)
        assert codigos(incidencias, ERROR)  # algo tiene que decir

    def test_cada_queja_dice_la_linea(self, catalogo):
        roto = factura_xml("  <cbc:ID>F1</cbc:ID>")
        for incidencia in revisar(roto, catalogo):
            assert "línea" in (incidencia.campo or "")


# Cuatro valores malos, cada uno en un elemento distinto. Los errores de tipo
# se acumulan; los de estructura no, porque libxml2 abandona el modelo de
# contenido en cuanto se le tuerce el primero.
CUATRO_MALOS = factura_xml(
    """  <cbc:ID>F1</cbc:ID>
  <cbc:IssueDate>ayer</cbc:IssueDate>
  <cbc:InvoiceTypeCode>999</cbc:InvoiceTypeCode>
  <cbc:CompanyID>hola</cbc:CompanyID>
  <cbc:PayableAmount currencyID="EUR">diez</cbc:PayableAmount>"""
)


class TestDemasiadosFallos:
    def test_sin_tope_salen_todos(self, catalogo):
        assert len(revisar(CUATRO_MALOS, catalogo)) == 4

    def test_se_cortan_y_se_avisa(self, catalogo, monkeypatch):
        monkeypatch.setattr(esquema, "TOPE_INCIDENCIAS", 2)
        incidencias = revisar(CUATRO_MALOS, catalogo)
        assert len(incidencias) == 3  # el tope, más el aviso
        aviso = una(incidencias, "XSD-DEMASIADOS")
        assert aviso.gravedad == AVISO
        assert "2 incumplimientos más" in aviso.mensaje
        assert aviso.encontrado == "4 en total"


class TestMensajeSinCabecera:
    def test_lo_que_no_se_sabe_traducir_se_deja_pasar(self):
        """Nunca perder un incumplimiento por no saber redactarlo."""

        class Entrada:
            message = "Something libxml2 made up"
            line = 7
            path = None

        incidencia = esquema.traducir(Entrada())
        assert incidencia.codigo == "XSD-OTRO"
        assert incidencia.gravedad == ERROR
        assert "Something libxml2 made up" in incidencia.mensaje


# --- Integración con el orquestador ----------------------------------------


class TestEnElOrquestador:
    def test_la_forma_se_comprueba_antes_que_el_contenido(self, catalogo):
        """Un documento que falla el esquema debe decirlo, no solo las cuentas."""
        roto = factura_xml("  <cbc:ID>F1</cbc:ID>")
        informe = factura.validar(roto, catalogo=catalogo)
        assert "XSD-FALTA" in codigos(informe.incidencias, ERROR)

    def test_sin_catalogo_todo_sigue_funcionando(self, tmp_path):
        informe = factura.validar(CORRECTA, catalogo=Catalogo(tmp_path / "nada"))
        assert not codigos(informe.incidencias, ERROR) & {
            "XSD-FALTA",
            "XSD-ORDEN",
            "XSD-OTRO",
        }

    def test_el_esquema_se_compila_una_vez_para_todo_el_lote(self, catalogo, tmp_path):
        """Compilar UBL 2.1 por cada fichero haría el lote inservible."""
        carpeta = tmp_path / "facturas"
        carpeta.mkdir()
        for numero in range(3):
            (carpeta / f"f{numero}.xml").write_text(CORRECTA, encoding="utf-8")

        factura.validar_lote(sorted(carpeta.iterdir()), catalogo=catalogo)
        assert len(catalogo._compilados) == 1

    def test_la_incidencia_sabe_que_es_de_forma(self, catalogo):
        roto = factura_xml("  <cbc:ID>F1</cbc:ID>")
        informe = factura.validar(roto, catalogo=catalogo)
        problema = una(informe.incidencias, "XSD-FALTA")
        assert factura.origen(problema) == factura.FORMA


class TestConsolaConEsquemas:
    def test_la_opcion_esquemas_activa_la_comprobacion(self, catalogo, tmp_path, capsys):
        ruta = tmp_path / "rota.xml"
        ruta.write_text(factura_xml("  <cbc:ID>F1</cbc:ID>"), encoding="utf-8")
        from validador import __main__ as consola

        codigo = consola.main([str(ruta), "--esquemas", str(catalogo.carpeta)])
        assert codigo == 1
        assert "XSD-FALTA" in capsys.readouterr().out

    def test_sin_esquemas_lo_dice_una_sola_vez(self, tmp_path, capsys):
        carpeta = tmp_path / "facturas"
        carpeta.mkdir()
        for numero in range(3):
            (carpeta / f"f{numero}.xml").write_text(CORRECTA, encoding="utf-8")
        from validador import __main__ as consola

        consola.main([str(carpeta), "--esquemas", str(tmp_path / "nada")])
        salida = capsys.readouterr().out
        # Tres ficheros, un solo recordatorio. Repetirlo por factura sería
        # ruido: quien no tiene los esquemas puestos ya lo sabe.
        assert salida.count("No se ha comprobado la forma") == 1
        assert "XSD-SIN-ESQUEMA" not in salida


# --- Compilar un esquema no sale a la red ----------------------------------

# Un esquema mínimo que importa otro **por dirección web**, que es lo que
# hacen los cinco XSD de Facturae con la firma XMLDSig.
FUERA = "http://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd"
IMPORTA_DE_FUERA = f"""<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
           xmlns="urn:prueba" targetNamespace="urn:prueba">
  <xs:import namespace="http://www.w3.org/2000/09/xmldsig#"
             schemaLocation="{FUERA}"/>
  <xs:element name="Invoice">
    <xs:complexType><xs:sequence>
      <xs:element ref="ds:Signature" minOccurs="0"/>
    </xs:sequence></xs:complexType>
  </xs:element>
</xs:schema>
"""

# Y una copia local de lo que ese import pide, con el nombre que le da UBL.
COPIA_DE_XMLDSIG = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns="http://www.w3.org/2000/09/xmldsig#"
           targetNamespace="http://www.w3.org/2000/09/xmldsig#">
  <xs:element name="Signature" type="xs:anyType"/>
</xs:schema>
"""


class TestCompilarNoSaleALaRed:
    """Compilar un esquema es otra cosa que leer un documento, y no lo parecía.

    El parser de `formato.py` lleva `no_network=True` desde el principio, con
    un comentario que dice que un fichero de fuera no debe poder hacer
    peticiones salientes. Eso vale para leer el documento. Las importaciones
    de un esquema las resuelve libxml2 por su cuenta, y se saltaban el parser:
    comprobar la forma de una factura Facturae —el formato nacional— se bajaba
    un XSD de w3.org cada vez, sin decirlo en ninguna parte.

    No se veía porque funcionaba. Se vio en el navegador, donde no hay red, y
    se confirmó aquí fuera apuntando el proxy a un puerto muerto.
    """

    def _catalogo(self, tmp_path, con_copia: bool) -> Catalogo:
        (tmp_path / "Facturaev3_2_2.xsd").write_text(
            IMPORTA_DE_FUERA, encoding="utf-8"
        )
        if con_copia:
            (tmp_path / "UBL-xmldsig-core-schema-2.1.xsd").write_text(
                COPIA_DE_XMLDSIG, encoding="utf-8"
            )
        return Catalogo(tmp_path)

    def _facturae(self):
        from validador.formato import FACTURAE, Deteccion

        return Deteccion(familia=FACTURAE, version="3.2.2", tipo_documento="factura")

    def test_con_la_copia_instalada_compila(self, tmp_path):
        catalogo = self._catalogo(tmp_path, con_copia=True)
        assert catalogo.esquema_para(self._facturae()) is not None

    def test_sin_la_copia_no_compila_y_no_va_a_buscarla(self, tmp_path):
        """La prueba de que no sale: sin copia local, no hay esquema.

        Si se cayera a la red, este esquema compilaría —la URL existe— y la
        comprobación no valdría nada. Que falle es lo que dice que no ha
        salido.
        """
        catalogo = self._catalogo(tmp_path, con_copia=False)
        assert catalogo.esquema_para(self._facturae()) is None

    def test_y_se_dice_la_causa_de_verdad(self, tmp_path):
        """No «vuelve a bajarlo», que manda a rebajar un fichero que está bien.

        El mensaje de siempre para un esquema que no compila habla de una
        descarga a medias, porque es lo que suele ser. Aquí el fichero está
        entero: lo que falta es otro, y encima uno que el esquema pide por una
        dirección web.
        """
        catalogo = self._catalogo(tmp_path, con_copia=False)
        catalogo.esquema_para(self._facturae())
        _, motivo = catalogo.por_que_no_compila(self._facturae())
        assert FUERA in motivo
        assert "no sale a la red" in motivo

    def test_el_resolvedor_nunca_deja_pasar_una_direccion_de_fuera(self):
        """Devolver None sería dejar que libxml2 la bajase él.

        Es la línea que hace el trabajo, y la que es fácil «simplificar» sin
        darse cuenta de que con eso vuelve la red.
        """
        resolvedor = esquema._SinRed({})
        assert resolvedor.resolve("http://ejemplo.invalido/x.xsd", None, None) is not None
        assert resolvedor.no_estaban == ["http://ejemplo.invalido/x.xsd"]

    def test_lo_de_casa_se_resuelve_como_siempre(self):
        """Un `include` relativo no tiene nada de malo y no se toca."""
        resolvedor = esquema._SinRed({})
        assert resolvedor.resolve("comun/UBL-CommonBasicComponents-2.1.xsd", None, None) is None
        assert resolvedor.no_estaban == []


# --- La versión de UBL, que decide qué esquema vale ------------------------


UBL_2_5 = Path("esquemas/ubl-2.5/maindoc/UBL-Invoice-2.5.xsd")
UBL_2_1 = Path("esquemas/ubl/maindoc/UBL-Invoice-2.1.xsd")
con_los_dos = pytest.mark.skipif(
    not (UBL_2_5.is_file() and UBL_2_1.is_file()),
    reason="hacen falta los esquemas de UBL 2.1 y 2.5 instalados",
)


class TestQueVersionDeUblSePide:
    """UBL 2.5 no es un detalle de versión: es lo único que admite la SPFE.

    Y el fallo que se puede colar aquí es de los caros: coger el esquema de al
    lado y llenar el informe de incumplimientos inventados contra una factura
    correcta. Por eso la regla es que **se puede subir de versión y nunca
    bajar**, y por eso está escrita como una propiedad y no como un ejemplo.
    """

    def _ubl(self, version, tipo="factura"):
        from validador.formato import UBL as familia_ubl
        from validador.formato import Deteccion

        return Deteccion(familia=familia_ubl, tipo_documento=tipo, version=version)

    def test_nunca_se_ofrece_un_esquema_anterior_al_declarado(self):
        conocidas = esquema._VERSIONES_UBL
        for i, version in enumerate(conocidas):
            nombres = esquema._nombres_esperados(self._ubl(version))
            ofrecidas = tuple(
                n.removeprefix("UBL-Invoice-").removesuffix(".xsd") for n in nombres
            )
            if version in esquema._NO_SUBEN:
                continue  # su prueba está justo debajo
            assert ofrecidas == conocidas[i:], f"con {version} se ofrece {ofrecidas}"

    def test_de_la_2_0_no_se_sube(self):
        """Un documento 2.0 se mide con el esquema 2.0 o con ninguno.

        Medido el 29-09-2026: un `ext:ExtensionContent` vacío es válido en la
        2.0 y lo rechazan la 2.1 y la 2.5. Ofrecerle la 2.1 a una factura 2.0
        sería acusarla de un fallo que no tiene. La medida está en
        HALLAZGOS.md; aquí solo se fija lo que hace el código con ella.
        """
        for tipo, clase in (("factura", "Invoice"), ("abono", "CreditNote")):
            nombres = esquema._nombres_esperados(self._ubl("2.0", tipo))
            assert nombres == (f"UBL-{clase}-2.0.xsd",)

    def test_sin_el_esquema_de_la_2_0_se_dice_cual_falta(self, catalogo):
        """Y no se cae en el de al lado: con solo la 2.1 instalada, se avisa."""
        xml = factura_xml(
            """  <cbc:UBLVersionID>2.0</cbc:UBLVersionID>
  <cbc:ID>F-2026-0001</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        incidencias = revisar(xml, catalogo)
        assert codigos(incidencias) == {"XSD-SIN-ESQUEMA"}
        assert "UBL-Invoice-2.0.xsd" in una(incidencias, "XSD-SIN-ESQUEMA").mensaje

    def test_el_primero_es_siempre_el_de_la_version_declarada(self):
        assert esquema._nombres_esperados(self._ubl("2.5"))[0] == "UBL-Invoice-2.5.xsd"
        assert esquema._nombres_esperados(self._ubl("2.1"))[0] == "UBL-Invoice-2.1.xsd"
        assert (
            esquema._nombres_esperados(self._ubl("2.5", "abono"))[0]
            == "UBL-CreditNote-2.5.xsd"
        )

    def test_una_version_que_no_conocemos_pide_la_suya_y_nada_mas(self):
        """UBL 2.6 no existe hoy. El día que exista, esto no se lo inventa.

        Ofrecerle la 2.5 sería exactamente el fallo de arriba con otro
        disfraz: un esquema anterior al que el documento declara.
        """
        assert esquema._nombres_esperados(self._ubl("2.6")) == ("UBL-Invoice-2.6.xsd",)

    def test_una_version_que_no_es_una_version_se_trata_como_si_no_hubiera(self):
        for basura in ("2", "dos punto uno", ""):
            nombres = esquema._nombres_esperados(self._ubl(basura))
            assert nombres[0] == "UBL-Invoice-2.1.xsd"

    def test_un_documento_2_5_no_se_valida_contra_el_esquema_2_1(self, catalogo):
        """El guardián. Con solo la 2.1 instalada, se dice que falta.

        Lo que no puede pasar es que salga un XSD-ORDEN: eso sería acusar a
        una factura correcta de tener elementos que se ha inventado, cuando lo
        que pasa es que el esquema con el que se la mide es viejo.
        """
        xml = factura_xml(
            """  <cbc:UBLVersionID>2.5</cbc:UBLVersionID>
  <cbc:ID>F-2026-0001</cbc:ID>
  <cbc:IssueDate>2026-03-02</cbc:IssueDate>
  <cbc:InvoiceTypeCode>380</cbc:InvoiceTypeCode>"""
        )
        incidencias = revisar(xml, catalogo)
        assert codigos(incidencias) == {"XSD-SIN-ESQUEMA"}
        aviso = una(incidencias, "XSD-SIN-ESQUEMA")
        assert "UBL-Invoice-2.5.xsd" in aviso.mensaje

    def test_el_aviso_nombra_uno_y_no_seis(self):
        """Cinco nombres en una frase no son una instrucción, son un ladrillo.

        Con la 2.1, que es la que más candidatos tiene desde que de la 2.0 no
        se sube.
        """
        frase = esquema._como_se_llama(self._ubl("2.1"))
        assert frase.count("UBL-Invoice") == 2  # el que toca y hasta dónde vale
        assert "UBL-Invoice-2.1.xsd" in frase
        assert "UBL-Invoice-2.5.xsd" in frase

    def test_la_copia_local_de_xmldsig_cuenta_con_la_de_2_5(self):
        """Quien instale solo UBL 2.5 no tiene la copia de 2.1 en el disco.

        Y de esa copia depende que se pueda comprobar la forma de **Facturae**,
        que importa la firma del W3C por dirección web. Sin nombrarla aquí, un
        conjunto perfectamente instalado dejaba sin comprobar el formato
        nacional entero.
        """
        copias = esquema._COPIAS_LOCALES["xmldsig-core-schema.xsd"]
        assert "UBL-xmldsig-core-schema-2.5.xsd" in copias
        assert "UBL-xmldsig-core-schema-2.1.xsd" in copias


@con_los_dos
class TestConLosEsquemasDeVerdad:
    """Lo medido sobre los XSD oficiales, no sobre los de doce líneas.

    Es lo que sostiene el comentario de `_VERSIONES_UBL`, y lo que se entera
    el día que OASIS cambie de criterio y una versión menor deje de ser
    compatible hacia arriba.
    """

    def _compilar(self, ruta):
        from lxml import etree

        return etree.XMLSchema(etree.parse(str(ruta)))

    def test_los_ejemplos_de_2_1_pasan_igual_el_esquema_2_5(self):
        from lxml import etree

        esq = self._compilar(UBL_2_5)
        ejemplos = [
            p
            for p in sorted(Path("ejemplos").glob("*.xml"))
            if b"ubl:schema:xsd:Invoice-2" in p.read_bytes()[:600]
        ]
        assert ejemplos, "no hay ejemplos UBL con los que medir esto"
        for p in ejemplos:
            arbol = etree.fromstring(p.read_bytes()).getroottree()
            assert esq.validate(arbol), f"{p.name}: {esq.error_log[0].message}"

    def test_y_al_reves_no(self):
        """Un elemento de 2.5 contra el esquema 2.1: rechazado.

        `DefaultLanguageCode` se añadió en la 2.5 y va detrás de
        `BuyerReference`. Es la mitad que hace falta medir: sin ella, la regla
        de «subir sí, bajar no» sería una suposición.
        """
        from lxml import etree

        texto = Path("ejemplos/f-0001.xml").read_text(encoding="utf-8")
        con25 = texto.replace(
            "<cac:AccountingSupplierParty>",
            "<cbc:DefaultLanguageCode>es</cbc:DefaultLanguageCode>\n  "
            "<cac:AccountingSupplierParty>",
            1,
        )
        assert "DefaultLanguageCode" in con25, "el ejemplo ha cambiado de forma"
        arbol = etree.fromstring(con25.encode("utf-8")).getroottree()
        assert self._compilar(UBL_2_5).validate(arbol)
        assert not self._compilar(UBL_2_1).validate(arbol)

    def test_el_namespace_no_cambia_entre_versiones(self):
        """Si cambiara, «subir de versión» no sería subir: sería otro formato."""
        from lxml import etree

        for ruta in (UBL_2_1, UBL_2_5):
            raiz = etree.parse(str(ruta)).getroot()
            assert raiz.get("targetNamespace") == NS_INVOICE
