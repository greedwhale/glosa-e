"""Las rutas UBL del CIUS español: que lleven a algún sitio de verdad.

`sintaxis.RUTAS_CIUS_ES` no se escribe a mano: se deriva de la tabla del anexo
al importar. Eso quita el riesgo de que se quede vieja y pone otro en su
sitio: que la derivación calle un fallo del anexo y lo convierta en una ruta
con buena pinta que no encuentra nada. Aquí se comprueba lo segundo.

Hay tres niveles, y hacen falta los tres:

1. **Que sean XPath.** Una ruta que no compila revienta el día que alguien la
   evalúe, no el día que se escribe.
2. **Que anden por el esquema.** No que exista un elemento que se llame así en
   alguna parte de UBL —eso lo cumple casi cualquier cosa—, sino que exista
   **donde la ruta dice**, paso a paso desde `InvoiceType`. Es lo que encontró
   que `cac:ThirdPartyInvoicing` no existe.
3. **Que lo que se le ha tocado al anexo siga haciendo falta.** Los arreglos y
   los distintivos salen de lo que dice el propio anexo; si el anexo cambia,
   tienen que saltar aquí y no quedarse aplicándose a ciegas.
"""

import pathlib
import re

import pytest
from lxml import etree

from validador import cius_es, sintaxis

# Lo medido sobre el anexo del 17-04-2026.
FILAS = 52
IDS = 51
CON_RUTA = 50
SIN_RUTA = ["BG-ES-34", "BG-ES-4"]

UBL_2_5 = pathlib.Path("esquemas/ubl-2.5")
con_esquema = pytest.mark.skipif(
    not (UBL_2_5 / "maindoc" / "UBL-Invoice-2.5.xsd").is_file(),
    reason="hacen falta los esquemas de UBL 2.5 instalados",
)

XS = "{http://www.w3.org/2001/XMLSchema}"
_PASO = re.compile(r"^(?:c[ab]c|ext):([A-Za-z]+)(\[.*\])?$")


def _esquema_de_ubl():
    """El esquema de UBL 2.5 reducido a lo que hace falta para andar rutas.

    Dos diccionarios: de qué tipo es cada elemento global, y qué hijos admite
    cada tipo. Con eso se recorre un camino sin construir ningún documento.
    """
    tipo_de: dict[str, str] = {}
    hijos_de: dict[str, list[str]] = {}
    modulos = [
        UBL_2_5 / "maindoc" / "UBL-Invoice-2.5.xsd",
        UBL_2_5 / "common" / "UBL-CommonAggregateComponents-2.5.xsd",
        UBL_2_5 / "common" / "UBL-CommonBasicComponents-2.5.xsd",
        UBL_2_5 / "common" / "UBL-CommonExtensionComponents-2.5.xsd",
    ]
    for modulo in modulos:
        for elemento in etree.parse(str(modulo)).getroot():
            if elemento.tag == XS + "element" and elemento.get("name"):
                tipo_de[elemento.get("name")] = (
                    elemento.get("type") or ""
                ).split(":")[-1]
            if elemento.tag == XS + "complexType" and elemento.get("name"):
                hijos_de[elemento.get("name")] = [
                    hijo.get("ref").split(":")[-1]
                    for hijo in elemento.iter(XS + "element")
                    if hijo.get("ref")
                ]
    return tipo_de, hijos_de


def _andar(ruta, tipo_de, hijos_de):
    """Recorre una ruta por el esquema. Devuelve el fallo, o None si llega."""
    actual = "InvoiceType"
    for paso in ruta.removeprefix("./").split("/"):
        if paso.startswith("*["):
            # Contenido de una extensión de la AEAT. UBL declara
            # `ExtensionContent` como `xsd:any` a propósito: ahí dentro no hay
            # esquema que recorrer, y no es un fallo.
            return None
        casa = _PASO.match(paso)
        if not casa:
            return f"paso que no se entiende: {paso}"
        nombre = casa.group(1)
        if nombre not in hijos_de.get(actual, []):
            return f"«{nombre}» no es hijo de {actual}"
        actual = tipo_de.get(nombre, "?")
    return None


def _sin_comillas(texto):
    """Las comillas del PDF son curvas y no siempre las mismas."""
    return re.sub(r"[\"'«»“”‘’]", "", texto)


class TestLaTablaQueSale:
    def test_los_recuentos_son_los_medidos(self):
        assert len(sintaxis.RUTAS_CIUS_ES) == FILAS
        assert len(sintaxis.POR_ID) == IDS
        con_ruta = [r for r in sintaxis.RUTAS_CIUS_ES if r.ruta != sintaxis.SIN_MAPA]
        assert len(con_ruta) == CON_RUTA

    def test_los_dos_sin_ruta_son_los_dos_que_el_anexo_deja_sin_ella(self):
        huerfanos = sorted(
            r.id for r in sintaxis.RUTAS_CIUS_ES if r.ruta == sintaxis.SIN_MAPA
        )
        assert huerfanos == SIN_RUTA

    def test_todas_compilan_como_xpath(self):
        """Una ruta que no compila no falla hoy: falla el día que se use."""
        for r in sintaxis.RUTAS_CIUS_ES:
            if r.ruta == sintaxis.SIN_MAPA:
                continue
            etree.XPath(r.ruta, namespaces=sintaxis.NS_CIUS_ES)

    def test_no_queda_ni_un_prefijo_de_los_que_el_anexo_no_declara(self):
        """`in:` y `aeat:` no están declarados en ninguna parte del anexo.

        Dejarlos sería repartir rutas que no se pueden evaluar, con el
        agravante de que `lxml` no avisa hasta que se las pasas.
        """
        for r in sintaxis.RUTAS_CIUS_ES:
            pasos = [p for p in r.ruta.split("/") if ":" in p]
            for paso in pasos:
                if "local-name()" in paso or "[" in paso:
                    continue
                assert paso.split(":")[0] in ("cbc", "cac", "ext"), r

    def test_ninguna_conserva_la_raiz_del_anexo(self):
        for r in sintaxis.RUTAS_CIUS_ES:
            assert "in:Invoice" not in r.ruta
            assert "in:invoice" not in r.ruta, "el anexo la escribe en minúscula"

    def test_el_anexo_original_se_conserva_al_lado(self):
        """Para poder comparar sin volver al PDF."""
        for r in sintaxis.RUTAS_CIUS_ES:
            campo = [c for c in cius_es.CAMPOS if c.id == r.id]
            assert r.anexo in [c.ruta for c in campo]


@con_esquema
class TestQueLlevenADondeDicen:
    """El nivel que de verdad cuesta, y el que encontró el fallo del anexo."""

    def test_las_cincuenta_andan_enteras_por_el_esquema_de_ubl_2_5(self):
        tipo_de, hijos_de = _esquema_de_ubl()
        rotas = []
        for r in sintaxis.RUTAS_CIUS_ES:
            if r.ruta == sintaxis.SIN_MAPA:
                continue
            fallo = _andar(r.ruta, tipo_de, hijos_de)
            if fallo:
                rotas.append(f"{r.id}: {fallo}")
        assert rotas == []

    def test_y_la_del_anexo_sin_arreglar_no(self):
        """Sin esto, el arreglo de BT-ES-15 sería una opinión.

        La ruta que el anexo le da a ese campo mete dos niveles que en UBL no
        existen. Aquí se comprueba que de verdad no andan, para que el arreglo
        esté sostenido por una medida y no por lo que parece.
        """
        tipo_de, hijos_de = _esquema_de_ubl()
        fila = sintaxis.POR_ID["BT-ES-15"][0]
        # La ruta entera tal y como la escribe el anexo, sin más cambio que
        # quitarle la raíz: es la que hay que medir, no el trozo del arreglo.
        tal_cual = "./" + fila.anexo.removeprefix("/in:Invoice/")
        assert _andar(tal_cual, tipo_de, hijos_de) is not None
        assert _andar(fila.ruta, tipo_de, hijos_de) is None

    def test_collectioninvoiceline_no_existiria_en_ubl_2_1(self):
        """Trece campos españoles cuelgan de ahí, y por eso hace falta la 2.5.

        Es el argumento entero de por qué la SPFE no admite UBL 2.1, y
        conviene que esté medido y no contado.
        """
        cuelgan = [
            r.id
            for r in sintaxis.RUTAS_CIUS_ES
            if "CollectionInvoiceLine" in r.ruta
        ]
        assert len(cuelgan) == 13
        viejo = pathlib.Path("esquemas/ubl/common/UBL-CommonAggregateComponents-2.1.xsd")
        if viejo.is_file():
            assert "CollectionInvoiceLine" not in viejo.read_text(encoding="utf-8")


class TestLoQueSeLeHaTocadoAlAnexo:
    """Dos arreglos y catorce distintivos, y los dieciséis con su porqué.

    Todos salen de lo que el propio anexo dice en otra columna. Si el anexo
    cambia de opinión, tienen que saltar aquí: aplicarlos a ciegas sobre un
    anexo nuevo sería inventarse la norma.
    """

    def test_las_tocadas_son_exactamente_dos(self):
        tocadas = sorted(r.id for r in sintaxis.RUTAS_CIUS_ES if r.tocada)
        assert tocadas == ["BG-ES-1", "BT-ES-15"]
        for r in sintaxis.RUTAS_CIUS_ES:
            if r.tocada:
                assert len(r.porque) > 80, "un arreglo sin explicar no vale"

    def test_los_arreglos_siguen_haciendo_falta(self):
        """Si el anexo ya no dice eso, el arreglo sobra y hay que mirarlo."""
        for identificador, (viejo, _, _) in sintaxis._ARREGLOS.items():
            rutas = [c.ruta for c in cius_es.CAMPOS if c.id == identificador]
            assert any(viejo in r for r in rutas), (
                f"{identificador}: el anexo ya no escribe «{viejo}». "
                "El arreglo se ha quedado sin objeto: vuelve a mirarlo."
            )

    def test_cada_distintivo_lo_dice_el_anexo_en_su_descripcion(self):
        """El guardián contra inventarse la norma.

        Cada predicado que se le añade a una ruta —un `schemeName`, un valor
        de `ChargeIndicator`, un URN de extensión— tiene que aparecer en la
        descripción del campo en el anexo. Si no aparece, no sale del anexo:
        sale de nosotros, y eso no vale.
        """
        for identificador, (_, con_predicado, dicho_en) in sintaxis._DISTINTIVOS.items():
            literal = re.search(r"'([^']+)'", con_predicado).group(1)
            descripciones = _sin_comillas(
                " ".join(c.descripcion for c in cius_es.CAMPOS if c.id == dicho_en)
            )
            assert literal in descripciones, (
                f"{identificador}: el anexo no dice «{literal}» en la "
                f"descripción de {dicho_en}, que es de donde se dijo que "
                "salía."
            )

    def test_despues_de_los_distintivos_solo_queda_una_ruta_repartida(self):
        """Y va dicha en voz alta, que es lo que se puede hacer con ella.

        `BT-ES-43` y `BT-ES-44` comparten el `ValueQualifier` de un
        `AdditionalItemProperty` y el anexo no da nada con que separarlos.
        """
        assert list(sintaxis.AMBIGUAS.values()) == [("BT-ES-43", "BT-ES-44")]

    def test_los_cinco_urn_de_extension_son_cinco_distintos(self):
        """Son las cinco cajas del anexo, y confundirlas las mezcla todas."""
        urns = {
            re.search(r"'([^']+)'", con).group(1)
            for identificador, (_, con, _dicho) in sintaxis._DISTINTIVOS.items()
            if "CollectionInvoiceLine" in con
        }
        assert len(urns) == 5
        assert all(u.startswith("urn:aeat:names:specification:ubl:schema:") for u in urns)


class TestQueSeLeanDeVerdad:
    """Una factura pequeña con campos españoles dentro, y leerlos."""

    FACTURA = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:CopyIndicator>false</cbc:CopyIndicator>
  <cac:AccountingCustomerParty><cac:Party>
    <cac:PartyIdentification><cbc:ID schemeName="Organo">E00003301</cbc:ID></cac:PartyIdentification>
    <cac:PartyIdentification><cbc:ID schemeName="Unidad">GE0004586</cbc:ID></cac:PartyIdentification>
    <cac:PartyIdentification><cbc:ID schemeName="Oficina">GE0001234</cbc:ID></cac:PartyIdentification>
  </cac:Party></cac:AccountingCustomerParty>
  <cac:AllowanceCharge>
    <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
    <cac:TaxCategory><cac:TaxScheme><cbc:ID>VAT</cbc:ID></cac:TaxScheme></cac:TaxCategory>
  </cac:AllowanceCharge>
  <cac:CollectionInvoiceLine>
    <cbc:ID>urn:aeat:names:specification:ubl:schema:RETE</cbc:ID>
  </cac:CollectionInvoiceLine>
  <cac:CollectionInvoiceLine>
    <cbc:ID>urn:aeat:names:specification:ubl:schema:SUPL</cbc:ID>
  </cac:CollectionInvoiceLine>
</Invoice>"""

    def raiz(self):
        return etree.fromstring(self.FACTURA.encode("utf-8"))

    def test_el_organo_la_unidad_y_la_oficina_no_se_confunden(self):
        """Las tres viven en la misma ruta del anexo. Es el caso de prueba.

        Tal y como el anexo las publica, las tres devolverían «E00003301», y
        la factura diría que la oficina destinataria es el órgano.
        """
        raiz = self.raiz()
        assert sintaxis.texto_es(raiz, "BT-ES-9") == "E00003301"
        assert sintaxis.texto_es(raiz, "BT-ES-10") == "GE0004586"
        assert sintaxis.texto_es(raiz, "BT-ES-11") == "GE0001234"

    def test_la_retencion_y_el_suplido_no_se_confunden(self):
        """Cinco campos comparten `CollectionInvoiceLine/cbc:ID` en el anexo."""
        raiz = self.raiz()
        assert sintaxis.texto_es(raiz, "BT-ES-32").endswith("RETE")
        assert sintaxis.texto_es(raiz, "BT-ES-20").endswith("SUPL")
        assert sintaxis.texto_es(raiz, "BT-ES-21") is None  # no hay minoración

    def test_el_descuento_encuentra_su_impuesto_y_el_cargo_no(self):
        raiz = self.raiz()
        assert sintaxis.texto_es(raiz, "BT-ES-17") == "VAT"
        assert sintaxis.texto_es(raiz, "BT-ES-19") is None

    def test_un_campo_sin_ruta_no_devuelve_nada_y_no_revienta(self):
        assert sintaxis.texto_es(self.raiz(), "BG-ES-4") is None
        assert sintaxis.campos_es(self.raiz(), "BG-ES-4") == []

    def test_un_identificador_que_no_existe_tampoco(self):
        assert sintaxis.texto_es(self.raiz(), "BT-ES-999") is None


class TestElAnexoSoloHablaDeFacturas:
    """No hay rutas de abono, y no es un olvido nuestro.

    Las cincuenta rutas del anexo arrancan en `/in:Invoice/`, y su lista de
    tipos de factura —L1— **no admite el 381**, que es el código del abono en
    la EN 16931. En este CIUS una rectificativa es un `Invoice` con el código
    384. Así que aquí no se inventan rutas de `CreditNote`: el día que el
    anexo las traiga, se derivarán solas.
    """

    def test_ninguna_ruta_menciona_creditnote(self):
        assert not [r.id for r in sintaxis.RUTAS_CIUS_ES if "CreditNote" in r.ruta]

    def test_y_la_lista_de_tipos_no_admite_el_abono_europeo(self):
        assert "381" not in cius_es.LISTAS["L1"].valores
        assert "384" in cius_es.LISTAS["L1"].valores
