"""Un importe que no es un número no puede llevarse el informe entero.

`Decimal` lee «NaN», «Infinity» y un número de treinta cifras sin quejarse, y
luego la primera comparación o el primer redondeo a céntimos lanzaba
`InvalidOperation`. Lo que salía era «no se ha podido validar»: se perdía la
forma, la firma y todo lo demás por un solo campo. Medido con una sonda que
cambia cada número de los ejemplos por diez valores raros: 198 combinaciones
tumbaban el informe.
"""

from datetime import date
from decimal import Decimal, getcontext, localcontext
from pathlib import Path

import pytest
from lxml import etree

from validador import factura, sintaxis
from validador.esquema import Catalogo

HOY = date(2026, 9, 20)
EJEMPLOS = Path(__file__).resolve().parent.parent / "ejemplos"

RAROS = ["NaN", "sNaN", "Infinity", "-Infinity", "1E+500", "9" * 30, "9" * 30 + ".99"]

# Los campos donde la sonda vio reventar el informe, por fichero. Uno por
# módulo que revienta: el lector de UBL y CII, el de Facturae, el IVA, las
# reglas de líneas y las de totales.
CAMPOS = [
    ("f-0001.xml", "TaxableAmount"),
    ("f-0001.xml", "Percent"),
    ("f-0001.xml", "PayableAmount"),
    ("cii-A-0001.xml", "BasisAmount"),
    ("cii-A-0001.xml", "RateApplicablePercent"),
    ("cii-A-0001.xml", "CalculatedAmount"),
    ("cii-A-0001.xml", "ChargeAmount"),
    ("cii-A-0001.xml", "LineTotalAmount"),
    ("cii-A-0001.xml", "TaxTotalAmount"),
    ("fe-0001.xml", "TotalAmount"),
    ("fe-0001.xml", "InvoiceTotal"),
    ("fe-0001.xml", "TaxRate"),
    ("fe-0001.xml", "Quantity"),
    ("fe-0001.xml", "TotalTaxOutputs"),
    ("fe-0001.xml", "InvoicesCount"),
]


def con_el_valor(nombre: str, campo: str, valor: str) -> bytes:
    """El ejemplo con **todos** los `campo` cambiados por `valor`."""
    ruta = EJEMPLOS / nombre
    if not ruta.is_file():
        pytest.skip(f"no está el ejemplo {nombre}")
    raiz = etree.fromstring(ruta.read_bytes())
    nodos = raiz.xpath(f"//*[local-name()='{campo}']")
    assert nodos, f"{nombre} no tiene ningún {campo}: la prueba no probaría nada"
    for nodo in nodos:
        nodo.text = valor
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


class TestElInformeNoSePierde:
    @pytest.mark.parametrize("valor", RAROS)
    @pytest.mark.parametrize("nombre,campo", CAMPOS)
    def test_se_valida_igual(self, nombre, campo, valor):
        informe = factura.validar(con_el_valor(nombre, campo, valor), hoy=HOY)
        codigos = {i.codigo for i in informe.incidencias}
        assert informe.validado, informe.resumen()
        assert "VALIDADOR-SE-ATRAGANTA" not in codigos

    def test_y_la_forma_sigue_diciendo_lo_suyo(self):
        # Es lo que más dolía perder: el esquema es quien sabe decir que «NaN»
        # no es un importe.
        # El de la carpeta del repositorio y no `por_defecto()`: la suite
        # apunta ese a una carpeta vacía a propósito (ver `conftest.py`).
        catalogo = Catalogo(EJEMPLOS.parent / "esquemas")
        if catalogo.vacio:
            pytest.skip("no hay esquemas instalados")
        informe = factura.validar(
            con_el_valor("f-0001.xml", "TaxableAmount", "NaN"), hoy=HOY,
            catalogo=catalogo,
        )
        assert any(i.codigo.startswith("XSD-") for i in informe.errores)


class TestLoQueNoEsUnNumeroNoSeCuenta:
    """Lo que el esquema no admite como número tampoco se suma.

    Si no, sale dos veces: el XSD se queja de la forma y las reglas de una
    aritmética hecha con algo que no es un importe.
    """

    @pytest.mark.parametrize(
        "escrito", ["NaN", "sNaN", "Infinity", "-Infinity", "inf", "1E+3", "1e2",
                    "1_000", "12,50", "", "١٢"]
    )
    def test_se_lee_como_ilegible(self, escrito):
        assert sintaxis.a_decimal(escrito) is None

    @pytest.mark.parametrize(
        "escrito,valor",
        [("12.50", "12.50"), ("-3", "-3"), ("+7.", "7"), (".5", "0.5"),
         (" 100.00 ", "100.00"), ("9" * 40, "9" * 40)],
    )
    def test_y_lo_que_si_lo_es_se_lee_igual(self, escrito, valor):
        assert sintaxis.a_decimal(escrito) == Decimal(valor)


class TestLasCuentasConNumerosGrandes:
    def test_un_importe_de_treinta_cifras_se_mide_y_no_revienta(self):
        # Válido para `xs:decimal`, así que el esquema no dice nada: si las
        # reglas no lo miden, no lo mide nadie.
        informe = factura.validar(
            con_el_valor("f-0001.xml", "TaxableAmount", "9" * 30 + ".00"), hoy=HOY
        )
        assert informe.validado
        assert informe.errores, "una base de treinta cifras no cuadra con nada"

    def test_la_precision_no_se_queda_cambiada(self):
        # En el navegador el intérprete sigue vivo entre factura y factura.
        #
        # Con un punto de partida puesto aquí y no leído de `getcontext()`: si
        # la guardia falla, la primera validación de la suite deja la precisión
        # cambiada, y un «antes» leído después ya sale contaminado e igual al
        # «después». Así pasaba esta prueba con el fallo dentro.
        with localcontext() as aqui:
            aqui.prec = 28
            factura.validar((EJEMPLOS / "f-0001.xml").read_bytes(), hoy=HOY)
            assert getcontext().prec == 28
