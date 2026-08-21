"""Comprobaciones de la validación de forma y de su traducción.

Los esquemas de aquí son de mentira, pequeños y escritos a mano. No se
descarga nada: lo que hay que probar es el catálogo y la traducción de los
mensajes de libxml2, y para eso un esquema de doce líneas sirve igual que los
tres megas de UBL 2.1 —y no deja la suite dependiendo de una descarga.

Aun así el esquema está repartido en dos ficheros que se importan entre sí,
como los oficiales, porque que las rutas relativas funcionen es justo lo que
puede fallar al instalarlos de verdad.
"""

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
