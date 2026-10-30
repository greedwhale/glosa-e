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
   que `cac:ThirdPartyInvoicing` no existía en el borrador, y que en la orden
   tampoco existen una factura dentro de la factura ni un `TaxSubTotal`.
3. **Que lo que se le ha tocado al anexo siga haciendo falta.** Los arreglos y
   los distintivos salen de lo que dice el propio anexo; si el anexo cambia,
   tienen que saltar aquí y no quedarse aplicándose a ciegas.
"""

import pathlib
import re

import pytest
from lxml import etree

from validador import cius_es, sintaxis

# Lo medido sobre el anexo I de la orden, del XML del BOE del 05-10-2026.
# BT-ES-8, la cuota del impuesto o tasa, trae dos rutas, y por eso hay una
# fila más que identificadores.
FILAS = 34
IDS = 33
CON_RUTA = 31
SIN_RUTA = ["BG-ES-2", "BG-ES-3", "BG-ES-4"]

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
    """Las comillas del BOE son angulares, y las de algún valor, rectas."""
    return re.sub(r"[\"'«»“”‘’]", "", texto)


def _tal_cual(ruta):
    """Una ruta del anexo sin más cambio que quitarle la raíz y su espacio."""
    return "./" + sintaxis._RAIZ_DEL_ANEXO.sub("", ruta).replace("@", "/@")


class TestLaTablaQueSale:
    def test_los_recuentos_son_los_medidos(self):
        assert len(sintaxis.RUTAS_CIUS_ES) == FILAS
        assert len(sintaxis.POR_ID) == IDS
        con_ruta = [r for r in sintaxis.RUTAS_CIUS_ES if r.ruta != sintaxis.SIN_MAPA]
        assert len(con_ruta) == CON_RUTA

    def test_los_tres_sin_ruta_son_los_tres_que_el_anexo_deja_sin_sitio(self):
        """BG-ES-2 no trae nada en la columna; BG-ES-3 y BG-ES-4, solo condiciones.

        Lo que traen esos dos —«VAT» y «S» en los cobros, «S» y «WTH» en las
        retenciones— no es dónde van, sino qué imponen sus filas en otra parte,
        y sale por `condiciones`.
        """
        huerfanos = sorted(
            r.id for r in sintaxis.RUTAS_CIUS_ES if r.ruta == sintaxis.SIN_MAPA
        )
        assert huerfanos == SIN_RUTA
        assert sintaxis.condiciones(next(c for c in cius_es.CAMPOS if c.id == "BG-ES-4"))

    def test_todas_compilan_como_xpath(self):
        """Una ruta que no compila no falla hoy: falla el día que se use."""
        for r in sintaxis.RUTAS_CIUS_ES:
            if r.ruta == sintaxis.SIN_MAPA:
                continue
            etree.XPath(r.ruta, namespaces=sintaxis.NS_CIUS_ES)
        for campo in cius_es.CAMPOS:
            for ruta, _ in sintaxis.condiciones(campo):
                etree.XPath(ruta, namespaces=sintaxis.NS_CIUS_ES)

    def test_no_queda_ni_un_prefijo_de_los_que_el_anexo_no_declara(self):
        """`in:` no está declarado en ninguna parte del anexo.

        Dejarlo sería repartir rutas que no se pueden evaluar, con el
        agravante de que `lxml` no avisa hasta que se las pasas.
        """
        for r in sintaxis.RUTAS_CIUS_ES:
            pasos = [p for p in r.ruta.split("/") if ":" in p]
            for paso in pasos:
                if "[" in paso:
                    continue
                assert paso.split(":")[0] in ("cbc", "cac", "ext"), r

    def test_ninguna_conserva_la_raiz_del_anexo(self):
        for r in sintaxis.RUTAS_CIUS_ES:
            assert "in:Invoice" not in r.ruta
            assert "in:invoice" not in r.ruta, "el anexo la escribe en minúscula"

    def test_ninguna_conserva_los_renglones_del_boe(self):
        """`cac:PrepaidPayment/ cbc:PaidDate` y `cac:TaxTotal/ /cbc:TaxAmount`.

        Una ruta con un espacio dentro no es XPath, y con la barra repetida
        busca a cualquier profundidad: las dos cosas salen del BOE partiendo
        la celda en renglones.
        """
        for r in sintaxis.RUTAS_CIUS_ES:
            sin_predicados = re.sub(r"\[[^\]]*\]", "", r.ruta)
            assert " " not in sin_predicados and "//" not in sin_predicados, r
        assert sintaxis.POR_ID["BT-ES-2"][0].ruta == "./cac:PrepaidPayment/cbc:PaidDate"

    def test_el_anexo_original_se_conserva_al_lado(self):
        """Para poder comparar sin volver al XML."""
        for r in sintaxis.RUTAS_CIUS_ES:
            campo = [c for c in cius_es.CAMPOS if c.id == r.id]
            assert r.anexo in [c.ruta for c in campo]


class TestLasCondiciones:
    """Lo que una fila impone en otra parte, separado de dónde va el campo."""

    def fila(self, identificador):
        return next(c for c in cius_es.CAMPOS if c.id == identificador)

    def test_el_nif_va_con_vat_o_con_loc_y_fc(self):
        """La orden da dos sitios para el NIF de cada parte, y basta uno."""
        assert sintaxis.condiciones(self.fila("BT-31")) == (
            ("./cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cac:TaxScheme/cbc:ID",
             "VAT"),)
        assert sintaxis.condiciones(self.fila("BT-32")) == (
            ("./cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cac:TaxScheme/cbc:ID",
             "LOC"),
            ("./cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme/cbc:CompanyID/@schemeID",
             "FC"),
        )

    def test_las_retenciones_son_s_y_wth(self):
        assert {valor for _, valor in sintaxis.condiciones(self.fila("BG-ES-4"))} == {"S", "WTH"}

    def test_el_nif_del_tercero_trae_su_sitio_y_sus_condiciones(self):
        """La única fila con las dos cosas en la misma celda."""
        assert [r.ruta for r in sintaxis.POR_ID["BT-ES-4"]] == [
            "./cac:AccountingSupplierParty/cac:Party/cac:ServiceProviderParty/cac:Party"
            "/cac:PartyTaxScheme/cbc:CompanyID"]
        assert {valor for _, valor in sintaxis.condiciones(self.fila("BT-ES-4"))} == {
            "VAT", "LOC", "FC"}

    def test_una_fila_que_solo_da_su_sitio_no_impone_nada(self):
        assert sintaxis.condiciones(self.fila("BT-ES-17")) == ()


@con_esquema
class TestQueLlevenADondeDicen:
    """El nivel que de verdad cuesta, y el que encontró los fallos del anexo."""

    def test_las_treinta_y_una_andan_enteras_por_el_esquema_de_ubl_2_5(self):
        tipo_de, hijos_de = _esquema_de_ubl()
        rotas = []
        for r in sintaxis.RUTAS_CIUS_ES:
            if r.ruta == sintaxis.SIN_MAPA:
                continue
            fallo = _andar(r.ruta, tipo_de, hijos_de)
            if fallo:
                rotas.append(f"{r.id}: {fallo}")
        assert rotas == []

    def test_y_las_condiciones_tambien(self):
        """Hasta el elemento: el atributo `schemeID` no se anda."""
        tipo_de, hijos_de = _esquema_de_ubl()
        rotas = []
        for campo in cius_es.CAMPOS:
            for ruta, _ in sintaxis.condiciones(campo):
                fallo = _andar(re.sub(r"/@\w+$", "", ruta), tipo_de, hijos_de)
                if fallo:
                    rotas.append(f"{campo.id}: {fallo}")
        assert rotas == []

    def test_y_las_del_anexo_sin_arreglar_no(self):
        """Sin esto, cada arreglo sería una opinión.

        Las rutas que el anexo da a esos campos meten pasos que en UBL no
        existen. Aquí se comprueba que de verdad no andan, para que el arreglo
        esté sostenido por una medida y no por lo que parece.
        """
        tipo_de, hijos_de = _esquema_de_ubl()
        for arreglo in sintaxis._ARREGLOS:
            filas = [r for r in sintaxis.RUTAS_CIUS_ES
                     if arreglo.porque in r.porque and r.ruta != sintaxis.SIN_MAPA]
            assert filas, arreglo.mal
            for r in filas:
                sitios = [ruta for ruta, valor in sintaxis._trozos(r.anexo) if not valor]
                assert any(_andar(_tal_cual(s), tipo_de, hijos_de) for s in sitios), r.id
                assert _andar(r.ruta, tipo_de, hijos_de) is None, r.id

    def test_collectioninvoiceline_no_existiria_en_ubl_2_1(self):
        """Siete campos españoles cuelgan de ahí, y por eso hace falta la 2.5.

        Es el argumento entero de por qué una factura con esos datos no cabe
        en UBL 2.1, aunque la AEAT admita versiones anteriores, y conviene que
        esté medido y no contado. En el borrador eran trece, y el README siguió
        contando trece hasta el 30-10-2026: por eso se mira también lo que dice.
        """
        cuelgan = [
            r.id
            for r in sintaxis.RUTAS_CIUS_ES
            if "CollectionInvoiceLine" in r.ruta
        ]
        assert len(cuelgan) == 7
        readme = pathlib.Path("README.md").read_text(encoding="utf-8")
        assert "**siete rutas del anexo cuelgan de `cac:CollectionInvoiceLine`**" in readme
        assert "no puede admitir UBL 2.1" not in readme
        viejo = pathlib.Path("esquemas/ubl/common/UBL-CommonAggregateComponents-2.1.xsd")
        if viejo.is_file():
            assert "CollectionInvoiceLine" not in viejo.read_text(encoding="utf-8")


class TestLoQueSeLeHaTocadoAlAnexo:
    """Tres arreglos y quince distintivos, todos con su porqué.

    Todos salen de lo que el propio anexo dice en otra columna o en otra fila.
    Si el anexo cambia de opinión, tienen que saltar aquí: aplicarlos a ciegas
    sobre un anexo nuevo sería inventarse la norma.
    """

    def test_las_tocadas_son_exactamente_estas(self):
        """La tipología del tercero, y los cuatro del impuesto o tasa del documento."""
        tocadas = sorted({r.id for r in sintaxis.RUTAS_CIUS_ES if r.tocada})
        assert tocadas == ["BT-ES-5", "BT-ES-6", "BT-ES-7", "BT-ES-8", "BT-ES-9"]
        for r in sintaxis.RUTAS_CIUS_ES:
            if r.tocada:
                assert len(r.porque) > 80, "un arreglo sin explicar no vale"

    def test_los_arreglos_siguen_haciendo_falta(self):
        """Si el anexo ya no dice eso, el arreglo sobra y hay que mirarlo."""
        for arreglo in sintaxis._ARREGLOS:
            assert any(arreglo.mal in c.ruta for c in cius_es.CAMPOS), (
                f"el anexo ya no escribe «{arreglo.mal}». "
                "El arreglo se ha quedado sin objeto: vuelve a mirarlo."
            )

    def test_cada_distintivo_lo_dice_el_anexo(self):
        """El guardián contra inventarse la norma.

        Cada valor que se le mete a una ruta en un predicado —un «true», un
        valor de L7, L8 o L10— tiene que aparecer en la fila del anexo de la
        que se dice que sale: en su descripción o, como el «true» de los
        cargos, en su columna de ruta. El calificador que puede ir delante no
        cuenta: sale de la lista, no de la fila.
        """
        calificadores = [v.calificador for v in cius_es.LISTAS.values() if v.calificador]
        for identificador, (_, con_predicado, dicho_en) in sintaxis._DISTINTIVOS.items():
            dicho = _sin_comillas(" ".join(
                c.descripcion + " " + c.ruta for c in cius_es.CAMPOS if c.id == dicho_en))
            for literal in re.findall(r"'([^']+)'", con_predicado):
                for calificador in calificadores:
                    literal = literal.removeprefix(calificador)
                assert literal in dicho, (
                    f"{identificador}: el anexo no dice «{literal}» en la fila "
                    f"{dicho_en}, que es de donde se dijo que salía."
                )

    def test_el_anexo_reparte_cuatro_rutas_entre_once_campos(self):
        """Las líneas de cobro, los documentos de L10 y las propiedades de L8."""
        por_ruta: dict[str, list[str]] = {}
        for r in sintaxis.RUTAS_CIUS_ES:
            for sitio, valor in sintaxis._trozos(r.anexo):
                if not valor:
                    clave = sintaxis._normalizar(sitio, "")[0]
                    por_ruta.setdefault(clave, []).append(r.id)
        repartidas = [ids for ids in por_ruta.values() if len(set(ids)) > 1]
        assert len(repartidas) == 4
        assert sum(len(set(ids)) for ids in repartidas) == 11

    def test_despues_de_los_distintivos_no_queda_ninguna_ruta_repartida(self):
        """Hasta el 14-09-2026, con el borrador, quedaba una: la situación del
        inmueble y el impuesto de la clave de régimen, con la frase «el anexo
        no da nada con que separarlos». Lo da, en BT-160: el nombre de la
        propiedad es «RCAT» en un grupo y «REGI» en el otro.
        """
        assert sintaxis.AMBIGUAS == {}

    def test_las_lineas_de_cobro_y_los_documentos_son_los_de_sus_listas(self):
        """Ni uno de más ni uno de menos: confundirlos los mezcla todos."""
        def valores(lista, cuales):
            calificador = cius_es.LISTAS[lista].calificador
            return {
                v.removeprefix(calificador)
                for identificador in cuales
                for v in re.findall(r"'([^']+)'", sintaxis._DISTINTIVOS[identificador][1])
            }

        assert valores("L7", ("BT-ES-10", "BT-ES-11", "BT-ES-15", "BT-ES-16")) == set(
            cius_es.LISTAS["L7"].valores)
        assert valores("L10", ("BT-ES-25", "BT-ES-26", "BT-ES-27", "BT-ES-28",
                               "BT-ES-29")) == set(cius_es.LISTAS["L10"].valores)


class TestQueSeLeanDeVerdad:
    """Una factura pequeña con campos españoles dentro, y leerlos."""

    FACTURA = """<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2">
  <cbc:CopyIndicator>false</cbc:CopyIndicator>
  <cac:AdditionalDocumentReference>
    <cbc:ID>QR</cbc:ID><cbc:UUID>https://www2.agenciatributaria.gob.es/qr</cbc:UUID>
  </cac:AdditionalDocumentReference>
  <cac:AdditionalDocumentReference>
    <cbc:ID>urn:aeat:names:specification:schema:AUT</cbc:ID><cbc:UUID>AUT-2026-1</cbc:UUID>
  </cac:AdditionalDocumentReference>
  <cac:AdditionalDocumentReference>
    <cbc:ID>RECT:TIPO</cbc:ID><cbc:DocumentTypeCode>R1</cbc:DocumentTypeCode>
  </cac:AdditionalDocumentReference>
  <cac:AdditionalDocumentReference>
    <cbc:ID>RECT:MODALIDAD</cbc:ID><cbc:DocumentTypeCode>I</cbc:DocumentTypeCode>
  </cac:AdditionalDocumentReference>
  <cac:AllowanceCharge>
    <cbc:ChargeIndicator>false</cbc:ChargeIndicator>
    <cac:TaxTotal><cac:TaxSubtotal><cac:TaxCategory><cac:TaxScheme>
      <cbc:TaxTypeCode>DESCUENTO</cbc:TaxTypeCode>
    </cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>
  </cac:AllowanceCharge>
  <cac:AllowanceCharge>
    <cbc:ChargeIndicator>true</cbc:ChargeIndicator>
    <cac:TaxTotal><cac:TaxSubtotal><cac:TaxCategory><cac:TaxScheme>
      <cbc:TaxTypeCode>IEH</cbc:TaxTypeCode>
    </cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal></cac:TaxTotal>
  </cac:AllowanceCharge>
  <cac:CollectionInvoiceLine>
    <cbc:ID>urn:aeat:names:specification:schema:add:RETE</cbc:ID>
  </cac:CollectionInvoiceLine>
  <cac:CollectionInvoiceLine>
    <cbc:ID>SUPL</cbc:ID>
  </cac:CollectionInvoiceLine>
  <cac:InvoiceLine><cac:Item>
    <cac:AdditionalItemProperty>
      <cbc:Name>REGI</cbc:Name><cbc:Value>01</cbc:Value><cbc:ValueQualifier>IVA</cbc:ValueQualifier>
    </cac:AdditionalItemProperty>
    <cac:AdditionalItemProperty>
      <cbc:Name>urn:aeat:names:specification:schema:lin:RCAT</cbc:Name>
      <cbc:Value>9872023VH5797S0001WX</cbc:Value><cbc:ValueQualifier>01</cbc:ValueQualifier>
    </cac:AdditionalItemProperty>
  </cac:Item></cac:InvoiceLine>
</Invoice>"""

    def raiz(self):
        return etree.fromstring(self.FACTURA.encode("utf-8"))

    def test_la_retencion_y_el_suplido_no_se_confunden(self):
        """Cuatro campos comparten `CollectionInvoiceLine/cbc:ID` en el anexo.

        La retención va con el calificador de L7 delante y el suplido sin él:
        las dos formas se leen.
        """
        raiz = self.raiz()
        assert sintaxis.texto_es(raiz, "BT-ES-16").endswith("RETE")
        assert sintaxis.texto_es(raiz, "BT-ES-10") == "SUPL"
        assert sintaxis.texto_es(raiz, "BT-ES-15") is None  # no hay minoración

    def test_el_cargo_encuentra_su_impuesto_y_el_descuento_no(self):
        assert sintaxis.texto_es(self.raiz(), "BT-ES-9") == "IEH"

    def test_la_situacion_del_inmueble_y_el_impuesto_de_la_clave_no_se_confunden(self):
        """Los dos van en el `ValueQualifier` de un `AdditionalItemProperty`.
        Lo que los separa es el nombre de la propiedad, que el anexo fija en
        BT-160: «RCAT» para la referencia catastral y «REGI» para la clave de
        régimen. Sin eso, la situación del inmueble devolvía «IVA»."""
        raiz = self.raiz()
        assert sintaxis.texto_es(raiz, "BT-ES-23") == "01"
        assert sintaxis.texto_es(raiz, "BT-ES-24") == "IVA"

    def test_los_documentos_de_l10_no_se_confunden(self):
        """Dos comparten `cbc:UUID`, y tres `cbc:DocumentTypeCode`."""
        raiz = self.raiz()
        assert sintaxis.texto_es(raiz, "BT-ES-25").startswith("https://")
        assert sintaxis.texto_es(raiz, "BT-ES-26") == "AUT-2026-1"
        assert sintaxis.texto_es(raiz, "BT-ES-27") == "R1"
        assert sintaxis.texto_es(raiz, "BT-ES-28") == "I"
        assert sintaxis.texto_es(raiz, "BT-ES-29") is None

    def test_un_campo_sin_ruta_no_devuelve_nada_y_no_revienta(self):
        assert sintaxis.texto_es(self.raiz(), "BG-ES-4") is None
        assert sintaxis.campos_es(self.raiz(), "BG-ES-4") == []

    def test_un_identificador_que_no_existe_tampoco(self):
        assert sintaxis.texto_es(self.raiz(), "BT-ES-999") is None


class TestElAnexoSoloHablaDeFacturas:
    """No hay rutas de abono, y no es un olvido nuestro.

    Todas las rutas del anexo arrancan en `/in:Invoice/`, y su lista de tipos
    de factura —L1— **no admite el 381**, que es el código del abono en la EN
    16931. En la solución pública una rectificativa es un `Invoice` con el
    código 384. Así que aquí no se inventan rutas de `CreditNote`: el día que
    el anexo las traiga, se derivarán solas.
    """

    def test_ninguna_ruta_menciona_creditnote(self):
        assert not [r.id for r in sintaxis.RUTAS_CIUS_ES if "CreditNote" in r.ruta]

    def test_y_la_lista_de_tipos_no_admite_el_abono_europeo(self):
        assert "381" not in cius_es.LISTAS["L1"].valores
        assert "384" in cius_es.LISTAS["L1"].valores
