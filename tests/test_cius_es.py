"""El CIUS español, y los guardianes que impiden que cambie en silencio.

`validador/cius_es.py` está generado a partir de un PDF que no se versiona y
que además **va a cambiar**: es un borrador en audiencia pública, la orden que
lo aprueba no está en el BOE y la AEAT ya ha dicho que lo alineará con UBL 2.5.

Una tabla generada de una fuente que se mueve es exactamente la clase de cosa
que en este repositorio se rompe en silencio, así que aquí se hace lo de
siempre: declarar en voz alta lo que se midió el día que se extrajo, y negarse
cuando la realidad deje de coincidir.

Los recuentos de abajo salieron de leer el PDF por dos caminos que no comparten
una línea de código —por coordenadas, que es lo que hace `herramientas/`, y con
una expresión regular sobre el texto en plano— y las dos lecturas dan **el
mismo conjunto de 155 identificadores**, sin ninguno que aparezca en una y no
en la otra. Los recuentos brutos difieren, y las dos diferencias están
explicadas:

- 176 menciones en plano frente a 174 filas: sobran exactamente dos, las citas
  a `BT-179` y `BT-114` que hay **dentro de la descripción** de `BT-115`.
- 178 cardinalidades en plano frente a 174: sobran exactamente cuatro, las de
  la introducción, que explica qué quiere decir `1..1`, `1..n`, `0..1` y `0..n`.
"""

import hashlib
import pathlib
import re

import pytest

from validador import cius_es

ANEXO = pathlib.Path("anexos/anexo-i.pdf")

# Lo medido el día de la extracción, sobre el anexo del 17-04-2026.
CAMPOS = 174
DISTINTOS = 155
ESPANOLES = 52
GRUPOS = 35
LISTAS = 11

ID = re.compile(r"^B[GT]-(?:ES-)?\d+$")

# El vocabulario cerrado de tipos semánticos del anexo. Si aparece uno nuevo es
# que el anexo ha cambiado, o que el extractor ha vuelto a pegar dos celdas.
TIPOS = {
    "Cantidad", "Código", "Código (L1)", "Código (L2.A)", "Código (L2.B)",
    "Código (L3A/L3B/L3C)", "Código (L4)", "Código (L5)", "Código (L6)",
    "Código (L7)", "Código (L8)", "Código - Calificador (L3A/L3B/L3C)",
    "Fecha", "Hora", "Identificador", "Importe", "Importe de precio unitario",
    "Indicador", "Porcentaje", "Referencia de documento", "Texto",
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

        Es la comprobación que más veces falló mientras se escribía el
        extractor: `BT-` sin número, `BG-20BT-` con dos pegados, o el
        identificador entero comido por la introducción de la página 3.
        """
        malos = [c.id for c in cius_es.CAMPOS if not ID.match(c.id)]
        assert malos == []

    def test_los_niveles_y_las_cardinalidades_son_las_del_anexo(self):
        assert {c.nivel for c in cius_es.CAMPOS} == {1, 2, 3, 4}
        assert {c.cardinalidad for c in cius_es.CAMPOS} == {
            "0..1", "0..n", "1..1", "1..2", "1..n"}

    def test_el_vocabulario_de_tipos_esta_cerrado(self):
        vistos = {c.tipo for c in cius_es.CAMPOS if c.tipo}
        assert vistos <= TIPOS, f"tipo nuevo: {vistos - TIPOS}"

    def test_las_extensiones_espanolas_dicen_donde_van(self):
        """Un campo que la EN 16931 no tiene solo sirve si dice su ruta UBL.

        Dos grupos se quedan sin ella en el borrador —`BG-ES-34` y `BG-ES-4`—,
        y eso va declarado aquí en vez de disimulado: si un anexo nuevo trae
        más huérfanos, esto se entera.
        """
        sin_ruta = sorted(c.id for c in cius_es.CAMPOS if c.espanol and not c.ruta)
        assert sin_ruta == ["BG-ES-34", "BG-ES-4"]


class TestLoQueElBorradorHaceMal:

    def test_los_repetidos_son_exactamente_estos(self):
        """El identificador no es una clave, y hay que saber hasta dónde.

        Cinco de estos son reutilización deliberada: el anexo usa `BG-34`,
        `BT-179` y `BT-180` como cajones para cada grupo español. `BT-ES-2` no
        lo es: son dos términos distintos con el mismo número, y es un fallo
        del borrador.
        """
        assert cius_es.REPETIDOS == {
            "BG-24": 2, "BG-32": 2, "BG-34": 5, "BT-122": 2, "BT-123": 2,
            "BT-160": 2, "BT-161": 2, "BT-179": 5, "BT-180": 5, "BT-ES-2": 2,
        }

    def test_bt_es_2_esta_puesto_en_dos_terminos_que_no_tienen_que_ver(self):
        terminos = [c.termino for c in cius_es.CAMPOS if c.id == "BT-ES-2"]
        assert len(terminos) == 2
        assert "extensión" in terminos[0]
        assert "Tipo de factura rectificativa" == terminos[1]


class TestLasConstantes:

    def test_bt24_lleva_el_identificador_del_cius(self):
        """El valor de BT-24 **es** la declaración de que esto es CIUS-ES.

        Va escrito en la descripción del campo, no en una columna aparte, así
        que se comprueba donde está.
        """
        bt24 = [c for c in cius_es.CAMPOS if c.id == "BT-24"]
        assert len(bt24) == 1
        assert cius_es.ESPECIFICACION in bt24[0].descripcion.replace(" ", "")
        assert bt24[0].obligatorio

    def test_bt23_lleva_el_proceso_de_negocio(self):
        bt23 = [c for c in cius_es.CAMPOS if c.id == "BT-23"]
        assert len(bt23) == 1
        assert cius_es.PROCESO in bt23[0].descripcion.replace(" ", "")


class TestLasListasDeCodigos:

    def test_l1_no_admite_el_381(self):
        """Esto es lo que obliga a corregir `en16931.py`, y por eso está aquí.

        En España una rectificativa es 384, o 471 si la expide el destinatario.
        Que rectifique por diferencias o por sustitución no se dice en el BT-3
        sino en `BT-ES-3`, con la lista L2.B. El 381 —el abono de la EN 16931 a
        secas— no cabe en este CIUS.

        `_METODO_A_UNCL1001` traduce hoy el `CorrectionMethod` 03 de Facturae a
        381. Es correcto para la norma europea y no vale aquí.
        """
        assert set(cius_es.LISTAS["L1"].valores) == {"380", "384", "388", "389", "471"}
        assert "381" not in cius_es.LISTAS["L1"].valores

    def test_l2b_es_la_que_dice_como_rectifica(self):
        assert cius_es.LISTAS["L2.B"].valores == {
            "I": "Rectificativa por diferencias",
            "S": "Rectificativa por sustitución",
        }

    def test_l4_anade_dos_categorias_que_la_norma_europea_no_tiene(self):
        """`L` y `M` no están en la UNCL5305 de la EN 16931.

        Son el IGIC y el IPSI, que solo existen aquí. Cualquier traducción de
        la categoría de IVA hacia este CIUS tiene que contar con ellas.
        """
        assert set(cius_es.LISTAS["L4"].valores) == {
            "S", "Z", "E", "AE", "O", "G", "L", "M"}
        assert cius_es.LISTAS["L4"].valores["L"] == "Operación sujeta al IGIC"
        assert cius_es.LISTAS["L4"].valores["M"] == "Operación sujeta al IPSI"

    def test_ninguna_lista_se_quedo_vacia(self):
        vacias = [k for k, v in cius_es.LISTAS.items() if not v.valores]
        assert vacias == []


class TestQueSigaSiendoEsteAnexo:
    """Los dos guardianes que hacen falta cuando la fuente no se versiona."""

    @pytest.mark.skipif(not ANEXO.exists(),
                        reason="no está `anexos/anexo-i.pdf`; se baja del "
                               "portal de Hacienda y no se versiona")
    def test_la_huella_del_pdf_es_la_declarada(self):
        """Si sale otro anexo, esto se entera antes que nadie.

        La huella está escrita en el docstring del módulo generado, que es
        donde se lee y donde tiene que estar.
        """
        declarada = re.search(r"SHA-256 ([0-9a-f]{64})", cius_es.__doc__)
        assert declarada, "el módulo generado ya no declara la huella del PDF"
        assert hashlib.sha256(ANEXO.read_bytes()).hexdigest() == declarada.group(1)

    @pytest.mark.skipif(not ANEXO.exists(), reason="no está `anexos/anexo-i.pdf`")
    def test_volver_a_extraer_da_exactamente_lo_mismo(self):
        """La tabla publicada tiene que ser lo que el PDF dice hoy.

        No basta con que el PDF no haya cambiado: también hay que saber si
        alguien tocó el extractor y la tabla se quedó vieja.
        """
        pypdf = pytest.importorskip("pypdf", reason="el extractor necesita pypdf")
        from herramientas import anexo_i

        filas = anexo_i.campos(str(ANEXO))
        assert len(filas) == len(cius_es.CAMPOS)
        for fila, campo in zip(filas, cius_es.CAMPOS):
            assert fila["id"] == campo.id
            assert fila["cardinalidad"] == campo.cardinalidad
            assert fila["termino"] == campo.termino
            assert fila["ruta"] == campo.ruta

        listas = anexo_i.listas(str(ANEXO))
        assert set(listas) == set(cius_es.LISTAS)
        for clave, lista in listas.items():
            esperado = {v["valor"]: v["descripcion"] for v in lista["valores"]}
            assert esperado == cius_es.LISTAS[clave].valores
