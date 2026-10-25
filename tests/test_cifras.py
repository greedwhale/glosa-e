"""Las cifras que lee una persona: con coma, y «Tiene» tal cual.

Hasta el 05-10-2026 el motor escribía todo con `:.2f`: «Debería ser: 90.00»,
«se aparta 0.50», y en «Tiene» un 100 salía 100.00 y un 100.125 salía 100.12.
Ver `validador/cifras.py` para las tres maneras y por qué.
"""

from __future__ import annotations

import ast
import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from validador import cifras, factura

import test_copia_fiel
import test_en16931
import test_facturae
import test_iva

RAIZ = Path(__file__).resolve().parent.parent
HOY = date(2026, 10, 5)


class TestLasCuatro:
    @pytest.mark.parametrize("valor,escrita", [
        ("90", "90,00"),
        ("100.125", "100,13"),   # las mitades hacia arriba, como la regla
        ("-100.135", "-100,13"),  # hacia arriba también en negativo
        ("0.005", "0,01"),
        ("1234.56", "1234,56"),   # cuatro cifras: sin punto de miles
        ("12345.67", "12.345,67"),
        ("1234567", "1.234.567,00"),
        ("-12345.6", "-12.345,60"),
    ])
    def test_calculada(self, valor, escrita):
        assert cifras.calculada(Decimal(valor)) == escrita

    @pytest.mark.parametrize("valor,escrita", [
        ("0.125", "0,125"),       # sin redondear: la cuenta tiene que sumar
        ("106.0", "106,00"),      # dos decimales como mínimo
        ("100", "100,00"),
        ("12345.678", "12.345,678"),
        ("-3.5", "-3,50"),
    ])
    def test_en_castellano(self, valor, escrita):
        assert cifras.en_castellano(Decimal(valor)) == escrita

    @pytest.mark.parametrize("valor,escrita", [
        ("100", "100"),
        ("100.125", "100.125"),
        ("100.00", "100.00"),
        ("12345.67", "12345.67"),  # sin miles: el fichero no los lleva
        ("-0.50", "-0.50"),
    ])
    def test_tiene(self, valor, escrita):
        assert cifras.tiene(Decimal(valor)) == escrita

    def test_tiene_sin_nada(self):
        assert cifras.tiene(None) == "(vacío)"

    @pytest.mark.parametrize("valor,escrita", [
        ("21.00", "21%"), ("21", "21%"), ("6.5", "6,5%"), ("0", "0%"),
        ("5.20", "5,2%"),
    ])
    def test_tipo(self, valor, escrita):
        assert cifras.tipo(Decimal(valor)) == escrita

    def test_tipo_sin_nada(self):
        assert cifras.tipo(None) == "(sin tipo)"


class TestFechasYRecuentos:
    """Del 06-10-2026: «publicada el 2026-08-06» y «1247225 bytes»."""

    def test_fecha(self):
        assert cifras.fecha(date(2026, 8, 6)) == "06-08-2026"

    def test_fecha_de_un_momento_es_su_dia(self):
        cuando = datetime(2027, 2, 2, 23, 59, 59, tzinfo=timezone.utc)
        assert cifras.fecha(cuando) == "02-02-2027"

    def test_momento_en_utc(self):
        cuando = datetime(2026, 3, 2, 10, 20, 30, tzinfo=timezone.utc)
        assert cifras.momento(cuando) == "02-03-2026 a las 10:20:30 UTC"

    def test_momento_de_otra_zona_se_pasa_a_utc(self):
        madrid = timezone(timedelta(hours=1))
        cuando = datetime(2026, 3, 2, 0, 30, tzinfo=madrid)
        assert cifras.momento(cuando) == "01-03-2026 a las 23:30:00 UTC"

    def test_momento_sin_zona_no_se_inventa_una(self):
        assert cifras.momento(datetime(2026, 3, 2, 10, 20, 30)) == (
            "02-03-2026 a las 10:20:30")

    @pytest.mark.parametrize("cuantos,escrito", [
        (1247225, "1.247.225"), (4096, "4096"), (12345, "12.345"), (0, "0"),
    ])
    def test_recuento(self, cuantos, escrito):
        assert cifras.recuento(cuantos) == escrito


# Lo que puede seguir escribiendo fechas en ISO, por función, y por qué. Lo
# demás va por `cifras.fecha` o `cifras.momento`.
EN_ISO = {
    ("__main__.py", "_ver_anclas"): "inventario de consola: son columnas, y en ISO "
                                    "se ordenan solas",
    ("__main__.py", "_ver_revocaciones"): "inventario de consola",
    ("__main__.py", "_ver_tsl"): "inventario de consola",
    ("revocacion.py", "inventario"): "el de `--ver-revocaciones`",
    ("bitacora.py", "_indice"): "el atributo `datetime` de `<time>`, que es para "
                                "máquina",
    ("codigo_unico.py", "canonico"): "el código único, que se compara y no se lee",
    ("codigo_unico.py", "huella"): "lo que se resume para la huella",
    ("codigo_unico.py", "revisar"): "la fecha del fichero en «Tiene», que va tal "
                                    "cual como las cifras",
    ("novedades.py", "pagina"): "el atributo `datetime` de `<time>`, como en "
                                "el índice de la bitácora",
    ("atom.py", "momento"): "las fechas de los canales Atom, que su norma pide "
                            "en RFC 3339",
    ("paquete.py", "armar"): "`PAQUETE.json`, que es para máquina",
    ("paquete.py", "_sitemap"): "el `lastmod` del sitemap, que es para máquina "
                                "y su norma pide W3C Datetime",
    ("paquete.py", "_con_lo_ultimo"): "el atributo `datetime` de `<time>`, como "
                                      "en el índice de la bitácora",
    ("paquete.py", "_para_investigadores"): "la cabecera `Expires` de security.txt, "
                                            "que la fija su norma",
    ("tsl.py", "_manifiesto"): "las líneas del manifiesto que lee "
                               "`Almacen.renovacion` con `date.fromisoformat`",
    ("tsl.py", "_fila"): "la tabla de estados, que se lee de vuelta",
}


def _fechas_en_iso() -> list[tuple[str, str, int]]:
    halladas = []
    for ruta in sorted((RAIZ / "validador").glob("*.py")):
        def visitar(nodo, funcion):
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funcion = nodo.name
            if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
                    and nodo.func.attr in ("isoformat", "strftime")):
                halladas.append((ruta.name, funcion, nodo.lineno))
            for hijo in ast.iter_child_nodes(nodo):
                visitar(hijo, funcion)
        visitar(ast.parse(ruta.read_text(encoding="utf-8")), "(módulo)")
    return halladas


def test_ninguna_fecha_se_escribe_por_su_cuenta():
    """Así salían unas cincuenta fechas del informe: «se publicó el 2026-03-02».

    Por función y no por línea: lo que decide si una fecha es para leer o para
    máquina es para qué sirve lo que la escribe.
    """
    sueltas = [f"{fichero}:{linea} en {funcion}"
               for fichero, funcion, linea in _fechas_en_iso()
               if (fichero, funcion) not in EN_ISO]
    assert not sueltas, (
        "estas fechas no pasan por `cifras.fecha` ni `cifras.momento`:\n"
        + "\n".join(sueltas))


def test_la_lista_de_excepciones_no_guarda_nada_que_ya_no_este():
    vivas = {(fichero, funcion) for fichero, funcion, _ in _fechas_en_iso()}
    assert not set(EN_ISO) - vivas, set(EN_ISO) - vivas


def test_la_procedencia_de_un_paquete_montado_antes_va_en_dd_mm_aaaa(tmp_path):
    """Las anclas montadas antes del 06-10-2026 escribieron la frase en ISO.

    Y así viajan en el paquete publicado hasta que se vuelva a montar. La frase
    se pasa al leerla; las líneas de debajo, que son para máquina, se siguen
    leyendo.
    """
    from validador.cadena import NOMBRE_DEL_MANIFIESTO, Almacen
    (tmp_path / NOMBRE_DEL_MANIFIESTO).write_text(
        "de la lista de confianza de ES, publicada por el Ministerio el 2026-08-06\n"
        "\n"
        "  publicada        2026-08-06\n"
        "  siguiente        2027-02-02\n"
        "  montada          2026-08-27\n", encoding="utf-8")
    almacen = Almacen(tmp_path)
    assert almacen.declarada == (
        "de la lista de confianza de ES, publicada por el Ministerio el 06-08-2026")
    assert almacen.renovacion.siguiente == date(2027, 2, 2)


# Lo único que puede seguir escribiendo cifras con su propio formato, y por qué.
FUERA_DE_CIFRAS = {
    "cifras.py": "es la puerta",
    "sintaxis.py": "define `fmt` y `fmt_tipo`, que ya no usa nadie; quitarlas "
                   "toca `sintaxis.py`, que lleva otro hilo",
    "__main__.py": "los megas de lo que se monta, para quien monta el sitio en "
                   "consola",
}
FORMATEA = re.compile(r":\.\d+f\}|(?<![\w.])_?fmt(?:_tipo)?\(")


def test_ninguna_cifra_se_escribe_por_su_cuenta():
    """Una cifra nueva con `:.2f` volvería a salir con punto, y con otro redondeo.

    Así se escribieron las cerca de 110 que hubo que cambiar, cada módulo con su
    `_fmt`.
    """
    sueltas = []
    for ruta in sorted((RAIZ / "validador").glob("*.py")):
        if ruta.name in FUERA_DE_CIFRAS:
            continue
        for numero, linea in enumerate(
                ruta.read_text(encoding="utf-8").splitlines(), start=1):
            if FORMATEA.search(linea.split("#")[0]):
                sueltas.append(f"{ruta.name}:{numero}: {linea.strip()}")
    assert not sueltas, (
        "estas cifras no pasan por `validador.cifras`:\n" + "\n".join(sueltas))


# --- Lo que sale del motor --------------------------------------------------

# Un número con punto decimal: el punto entre dos cifras que no sea de miles.
# Los miles van seguidos siempre de coma y decimales, porque `calculada` y
# `en_castellano` escriben dos decimales como mínimo, y solo desde cinco
# cifras: 1.234,56 no es un número bien escrito aquí, y cuenta como punto.
_MILES = re.compile(r"(?:\d{2,3}(?:\.\d{3})+|\d(?:\.\d{3}){2,}),\d+")
_PUNTO = re.compile(r"\d\.\d")


def _con_punto(texto: str) -> list[str]:
    limpio = _MILES.sub("#", texto)
    return [limpio[max(0, m.start() - 40):m.end() + 20]
            for m in _PUNTO.finditer(limpio)]


def _documentos():
    """Facturas con las cuentas rotas a propósito, de los cuatro motores.

    Los constructores de las pruebas de cada módulo, con un importe cambiado,
    con tres decimales o con cinco cifras: lo que hace falta para que salga
    cada cuenta, y con miles.
    """
    for ruta in sorted((RAIZ / "ejemplos").iterdir()):
        yield ruta.name, ruta.read_bytes()
    for opciones in [
        dict(lineas=(("1", "100.125"),), suma_lineas="100.12", base="100.12"),
        dict(cargos="0.125", base="100.12"),
        dict(impuestos="21.005"),
        dict(anticipos="0.015", a_pagar="120.98"),
        dict(redondeo="0.01"),
        dict(base_iva="150.00"),
        dict(tipo_iva="7.5"),
        dict(descuentos="10.00", base="100.00"),
        dict(lineas=(("1", "12345.67"),), suma_lineas="12345.67",
             base="12345.67"),
    ]:
        yield f"UBL {opciones}", test_en16931.factura(**opciones).encode()
    linea, grupo, ajuste = test_iva.Linea, test_iva.Grupo, test_iva.Ajuste
    for montar in (test_iva.ubl, test_iva.cii):
        for opciones in [
            dict(lineas=[linea("1", "100.00")], grupos=[grupo("100.00", "25.00")],
                 total_iva="25.00"),
            dict(lineas=[linea("1", "100.00"), linea("2", "50.00", tipo="10")],
                 grupos=[grupo("100.00", "21.00")], total_iva="21.00"),
            dict(lineas=[linea("1", "100.00")], grupos=[grupo("100.50", "21.10")],
                 total_iva="21.10"),
            dict(lineas=[linea("1", "100.00")],
                 grupos=[grupo("100.00", "21.00", tipo="7.5")], total_iva="21.00"),
            dict(lineas=[linea("1", "100.00")], ajustes=[ajuste("10.005")],
                 grupos=[grupo("90.00", "18.90")], total_iva="18.90",
                 descuentos_total="10.00"),
        ]:
            yield f"{montar.__name__} {opciones}", montar(**opciones).encode()
    for clave in test_facturae.CORRECTA:
        if clave in ("nif", "modalidad", "cuantas", "numero", "cod_iva",
                     "iva_extra"):
            continue
        for nuevo in ("1.00", "12345.678"):
            yield (f"Facturae {clave}={nuevo}",
                   test_facturae.fe(**{clave: nuevo}).encode())
    for opciones in [dict(recargo=True), dict(retenido="15.00"),
                     dict(financieros="1.00"), dict(subvenciones="50.00"),
                     dict(suplidos="7.00"), dict(coste="100.00", neto="90.00")]:
        raiz, _ = test_copia_fiel.factura(**opciones)
        yield f"copia {opciones}", etree.tostring(raiz)


def test_lo_que_se_lee_va_con_coma():
    """En el mensaje y en «Debería ser», ninguna cifra con punto decimal.

    «Tiene» sí puede llevarlo: va tal cual está en el fichero. Y las
    versiones («UBL 2.1», «Facturae 3.2.2») tendrían que estar aquí escritas
    con su porqué si alguna saliera; con estos documentos no sale ninguna.
    """
    con_punto = []
    codigos = set()
    for nombre, datos in _documentos():
        for i in factura.validar(datos, hoy=HOY).incidencias:
            codigos.add(i.codigo)
            for campo in ("mensaje", "esperado"):
                for trozo in _con_punto(getattr(i, campo) or ""):
                    con_punto.append(f"{i.codigo} ({nombre}), {campo}: …{trozo}…")
    # Que el corpus siga trayendo las cuentas: si un constructor cambia y deja
    # de romperlas, esto pasaría en verde sin mirar nada.
    for codigo in ("BR-CO-10", "BR-CO-13", "BR-CO-15", "BR-CO-17", "BR-S-08",
                   "FE-LINEA-BRUTO", "FE-CUOTA", "FE-EJECUTAR", "COPIA-TOTAL",
                   "COPIA-CARGO-IVA", "IVA-CUOTA-REDONDEO"):
        assert codigo in codigos, f"{codigo} ya no sale con estos documentos"
    assert not con_punto, "\n".join(sorted(set(con_punto)))


def test_la_cuenta_que_explica_suma():
    """La cuenta del paréntesis lleva las cifras del fichero sin redondear.

    Con dos decimales, una línea de 100.00 más 0.125 de cargos decía «100,13
    (100,00 + 0,12 de cargos)», que no suma.
    """
    informe = factura.validar(
        test_en16931.factura(cargos="0.125", base="100.12").encode(), hoy=HOY)
    (incidencia,) = [i for i in informe.incidencias if i.codigo == "BR-CO-13"]
    assert incidencia.esperado == "100,13  (100,00 + 0,125 de cargos)"
    assert incidencia.encontrado == "100.12"


def test_tiene_es_lo_que_hay_en_el_fichero():
    """Un 21.005 del fichero no sale 21.00: sale 21.005, que es lo que se busca."""
    informe = factura.validar(
        test_en16931.factura(impuestos="21.005").encode(), hoy=HOY)
    (incidencia,) = [i for i in informe.incidencias if i.codigo == "BR-CO-14"]
    assert incidencia.esperado.startswith("21,01 ")
    assert incidencia.encontrado == "21.005"
