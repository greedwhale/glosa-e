"""El CIUS español, y los guardianes que impiden que cambie en silencio.

`validador/cius_es.py` está generado a partir del XML del BOE de la Orden
HAC/1028/2026, que no se versiona. Hasta el 11-10-2026 salía del PDF del
borrador de abril, leído por coordenadas; la orden se publicó el 05-10-2026, y
su tabla no es la del borrador.

Una tabla generada de una fuente que no se versiona es exactamente la clase de
cosa que en este repositorio se rompe en silencio, así que aquí se hace lo de
siempre: declarar en voz alta lo que se midió el día que se extrajo, y negarse
cuando la realidad deje de coincidir.

Los recuentos de abajo salieron de leer el XML por dos caminos que no comparten
una línea de código —el de `herramientas/anexo_i.py` y un guion aparte, escrito
el 06-10-2026 para medir la orden contra el borrador— y las dos lecturas dan
las mismas 176 filas, campo a campo, sin una diferencia.
"""

import hashlib
import pathlib
import re

import pytest

from validador import cius_es

ANEXO = pathlib.Path("anexos/orden-hac-1028-2026.xml")

# Lo medido el día de la extracción, sobre el XML del BOE del 05-10-2026.
CAMPOS = 176
DISTINTOS = 149
ESPANOLES = 33
GRUPOS = 39
LISTAS = 14

ID = re.compile(r"^B[GT]-(?:ES-)?\d+$")

# El vocabulario cerrado de tipos semánticos del anexo. Si aparece uno nuevo es
# que el anexo ha cambiado, o que el extractor ha vuelto a pegar dos celdas.
TIPOS = {
    "Cantidad", "Código", "Código (L1)", "Código (L2.A)", "Código (L2.B)",
    "Código (L2.C)", "Código (L3A/L3B/L3C)", "Código (L4)", "Código (L5)",
    "Código (L6)", "Código (L7)", "Código (L8)", "Código (L9)", "Código (L10)",
    "Código-Calificador (L3A/L3B/L3C)", "Fecha", "Hora", "Identificador",
    "Importe", "Importe de precio unitario", "Indicador", "Porcentaje",
    "Referencia de documento", "Texto",
}


class TestLoQueTraeLaTabla:

    def test_los_recuentos_son_los_medidos(self):
        assert len(cius_es.CAMPOS) == CAMPOS
        assert len({c.id for c in cius_es.CAMPOS}) == DISTINTOS
        assert sum(1 for c in cius_es.CAMPOS if c.espanol) == ESPANOLES
        assert sum(1 for c in cius_es.CAMPOS if c.grupo) == GRUPOS
        assert len(cius_es.LISTAS) == LISTAS

    def test_todos_los_identificadores_tienen_forma_de_identificador(self):
        """Ni uno a medias.

        Con el PDF fue la comprobación que más veces falló mientras se escribía
        el extractor: `BT-` sin número, `BG-20BT-` con dos pegados. En el XML
        el identificador viene con espacios dentro («BT- ES-1»), y el extractor
        los quita.
        """
        malos = [c.id for c in cius_es.CAMPOS if not ID.match(c.id)]
        assert malos == []

    def test_los_niveles_y_las_cardinalidades_son_las_del_anexo(self):
        """`0..5` es nueva en la orden: los importes rectificados, hasta cinco."""
        assert {c.nivel for c in cius_es.CAMPOS} == {1, 2, 3, 4}
        assert {c.cardinalidad for c in cius_es.CAMPOS} == {
            "0..1", "0..5", "0..n", "1..1", "1..2", "1..n"}

    def test_el_vocabulario_de_tipos_esta_cerrado(self):
        vistos = {c.tipo for c in cius_es.CAMPOS if c.tipo}
        assert vistos <= TIPOS, f"tipo nuevo: {vistos - TIPOS}"

    def test_un_solo_campo_espanol_va_sin_nada_en_la_columna_de_la_ruta(self):
        """BG-ES-2, los impuestos y tasas del documento.

        No es el único sin sitio: BG-ES-3 y BG-ES-4 traen en esa columna lo
        que su uso impone en otra parte, y no dónde van. Eso se mide en
        `test_rutas_cius`, que es donde se separa una cosa de otra.
        """
        sin_ruta = sorted(c.id for c in cius_es.CAMPOS if c.espanol and not c.ruta)
        assert sin_ruta == ["BG-ES-2"]


class TestLosRepetidos:

    def test_los_repetidos_son_exactamente_estos(self):
        """El identificador no es una clave, y hay que saber hasta dónde.

        Todos son reutilización deliberada: `BG-24`, `BT-122` y `BT-123`, uno
        por documento de la lista L10; `BG-34`, `BT-179` y `BT-180`, uno por
        grupo de cobros; y `BG-32`, `BT-160` y `BT-161`, uno por propiedad de
        la lista L8.
        """
        assert cius_es.REPETIDOS == {
            "BG-24": 5, "BG-32": 3, "BG-34": 4, "BT-122": 5, "BT-123": 5,
            "BT-160": 3, "BT-161": 3, "BT-179": 4, "BT-180": 4,
        }

    def test_ningun_campo_espanol_se_repite(self):
        """El borrador de abril ponía BT-ES-2 a dos términos sin nada que ver.

        La orden lo arregla renumerando: BT-ES-2 es ahora la fecha efectiva de
        pago y nada más.
        """
        espanoles = [c.id for c in cius_es.CAMPOS if c.espanol]
        assert len(espanoles) == len(set(espanoles))
        assert [c.termino for c in cius_es.CAMPOS if c.id == "BT-ES-2"] == [
            "Fecha efectiva de pago"]


class TestLasConstantes:

    def test_bt24_lleva_el_identificador_de_la_especificacion(self):
        """El valor de BT-24 **es** la declaración de que esto es de la solución pública.

        Va escrito en la descripción del campo, no en una columna aparte, así
        que se comprueba donde está. Es el que enseñó la AEAT en su ejemplo del
        02-10-2026, y no el CIUS del borrador.
        """
        bt24 = [c for c in cius_es.CAMPOS if c.id == "BT-24"]
        assert len(bt24) == 1
        assert cius_es.ESPECIFICACION in bt24[0].descripcion
        assert cius_es.ESPECIFICACION == (
            "urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:1.0.0:extended")
        assert bt24[0].obligatorio

    def test_bt23_lleva_el_proceso_de_negocio(self):
        bt23 = [c for c in cius_es.CAMPOS if c.id == "BT-23"]
        assert len(bt23) == 1
        assert cius_es.PROCESO in bt23[0].descripcion
        assert cius_es.PROCESO == "urn:aeat:names:specification:ubl:schema:profile:B2B"


class TestLasListasDeCodigos:

    def test_l1_no_admite_el_381(self):
        """Esto es lo que obliga a corregir `en16931.py`, y por eso está aquí.

        En España una rectificativa es 384, o 471 si la expide el destinatario.
        Que rectifique por diferencias o por sustitución no se dice en el BT-3
        sino en un documento justificativo adicional, con la lista L2.B. El
        381 —el abono de la EN 16931 a secas— no cabe en la solución pública.
        """
        assert set(cius_es.LISTAS["L1"].valores) == {"380", "384", "388", "389", "471"}
        assert "381" not in cius_es.LISTAS["L1"].valores

    def test_l2b_es_la_que_dice_como_rectifica(self):
        assert cius_es.LISTAS["L2.B"].valores == {
            "I": "Rectificativa por diferencias.",
            "S": "Rectificativa por sustitución.",
        }

    def test_l2c_es_nueva_y_dice_que_se_rectifica(self):
        assert list(cius_es.LISTAS["L2.C"].valores) == ["Base", "Cuota", "CuotaRecargo"]

    def test_l4_quita_dos_categorias_de_la_norma_y_trae_tres_nuevas(self):
        """L4 quita `K` y `B` de la UNCL5305 de 2017, y trae `N`, `D` y `F`.

        Esta prueba se llamó «L4 añade dos categorías que la norma europea no
        tiene», y afirmaba que `L` y `M` no estaban en la UNCL5305. Están: el
        esquematrón las admite en BR-CL-18 (`AE L M E S Z G O K B`). Se
        corrigió el 13-09-2026. Las tres nuevas no son de la lista de la
        norma. La D y la F sí son de la UNTDID 5305, desde su edición D16A (el
        margen de las agencias de viajes y el de los bienes usados), que es de
        donde la orden dice sacar la L4; la N no está ni ahí. Leído en
        edifactory el 11-10-2026. Hasta ese día esto decía que las traía «la
        edición de 2026 de la norma», sin fuente: lo vio el auditor.
        """
        assert set(cius_es.LISTAS["L4"].valores) == {
            "S", "Z", "E", "AE", "O", "G", "L", "M", "N", "D", "F"}
        assert cius_es.LISTAS["L4"].valores["L"] == "Operación sujeta al IGIC."
        assert "recargo de equivalencia" in cius_es.LISTAS["L4"].valores["N"]

    def test_l3a_ya_no_tiene_el_18_el_19_ni_el_20(self):
        """El régimen simplificado, el recargo y la agricultura, en el borrador.

        La orden los quita del IVA: el recargo y el grupo de entidades van con
        la categoría N. En el IGIC y el IPSI hay un 18, un 19 o un 20 que no
        tienen que ver.
        """
        assert not {"18", "19", "20"} & set(cius_es.LISTAS["L3A"].valores)

    def test_las_descripciones_son_las_del_boe(self):
        """Con su punto final, como en el XML, y enteras.

        Del PDF salían corridas una fila hasta el 14-09-2026: el 01 de L6
        decía «País Vasco y Navarra», que es justo lo que excluye.
        """
        l6 = cius_es.LISTAS["L6"].valores
        assert l6["01"] == (
            "Inmueble con referencia catastral situado en cualquier punto del "
            "territorio español, excepto País Vasco y Navarra.")
        assert l6["02"] == (
            "Inmueble situado en la Comunidad Autónoma del País Vasco o en la "
            "Comunidad Foral de Navarra.")
        assert cius_es.LISTAS["L3C"].valores["01"] == (
            "Operación en régimen general y no incluidas en otras claves.")
        assert cius_es.LISTAS["L5"].valores["07"].startswith("Artículo 75.2.b) RIRPF")
        assert cius_es.LISTAS["L5"].valores["11"] == "Otros."

    def test_los_calificadores_son_los_de_la_orden(self):
        """Las claves de régimen dicen de qué impuesto son, y L7, L8 y L10 su URN.

        «CALIFICADOR IVA», «IGIC» o «IPSI» es lo que dice en qué lista hay que
        buscar la clave de régimen: el 17 es una clave del IGIC y no del IVA.
        Los URN de L7, L8 y L10 son los que el borrador tenía con `ubl:` y la
        orden sin él.
        """
        assert {k: v.calificador for k, v in cius_es.LISTAS.items() if v.calificador} == {
            "L3A": "IVA", "L3B": "IGIC", "L3C": "IPSI",
            "L7": "urn:aeat:names:specification:schema:add:",
            "L8": "urn:aeat:names:specification:schema:lin:",
            "L10": "urn:aeat:names:specification:schema:",
        }

    def test_ninguna_lista_se_quedo_vacia(self):
        vacias = [k for k, v in cius_es.LISTAS.items() if not v.valores]
        assert vacias == []


class TestQueSigaSiendoEsteAnexo:
    """Los dos guardianes que hacen falta cuando la fuente no se versiona."""

    @pytest.mark.skipif(not ANEXO.exists(),
                        reason="no está `anexos/orden-hac-1028-2026.xml`; se baja "
                               "del BOE y no se versiona")
    def test_la_huella_del_xml_es_la_declarada(self):
        """Si sale una corrección de errores, esto se entera antes que nadie.

        La huella está escrita en el docstring del módulo generado, que es
        donde se lee y donde tiene que estar.
        """
        declarada = re.search(r"SHA-256 ([0-9a-f]{64})", cius_es.__doc__)
        assert declarada, "el módulo generado ya no declara la huella del XML"
        assert hashlib.sha256(ANEXO.read_bytes()).hexdigest() == declarada.group(1)

    @pytest.mark.skipif(not ANEXO.exists(), reason="no está `anexos/orden-hac-1028-2026.xml`")
    def test_volver_a_extraer_da_exactamente_lo_mismo(self):
        """La tabla publicada tiene que ser lo que el XML dice hoy.

        No basta con que el XML no haya cambiado: también hay que saber si
        alguien tocó el extractor y la tabla se quedó vieja.
        """
        from herramientas import anexo_i

        filas = anexo_i.campos(str(ANEXO))
        assert len(filas) == len(cius_es.CAMPOS)
        for fila, campo in zip(filas, cius_es.CAMPOS):
            assert fila == {
                "id": campo.id, "nivel": campo.nivel,
                "cardinalidad": campo.cardinalidad, "termino": campo.termino,
                "descripcion": campo.descripcion, "tipo": campo.tipo,
                "ruta": campo.ruta,
            }

        listas = anexo_i.listas(str(ANEXO))
        assert set(listas) == set(cius_es.LISTAS)
        for clave, lista in listas.items():
            esperado = {v["valor"]: v["descripcion"] for v in lista["valores"]}
            assert esperado == cius_es.LISTAS[clave].valores
            assert lista["titulo"] == cius_es.LISTAS[clave].titulo
            assert lista["calificador"] == cius_es.LISTAS[clave].calificador

        assert anexo_i.fijado(filas, "BT-24") == cius_es.ESPECIFICACION
        assert anexo_i.fijado(filas, "BT-23") == cius_es.PROCESO
