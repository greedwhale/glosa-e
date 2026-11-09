"""Un fichero de otro no puede colgar el validador ni llevarse el lote.

Salió del escaneo de seguridad del 01 al 03-11-2026 y lo cuenta HALLAZGOS. Son
tres causas y van juntas porque las tres acaban igual: la pestaña congelada o
el lote sin informe, sin excepción que capturar en las dos primeras y sin
nombrar al culpable en la tercera.

- **Coste cuadrático.** Tres caminos que, con el doble de entrada, tardaban
  cuatro veces más. Medido antes de arreglarlos: la búsqueda del BGM tardaba
  3,1 s con 20.000 saltos de línea, la lista de parámetros del QR 0,6 s con
  20.000 parámetros y la agrupación de los miles 0,8 s con 200.000 cifras. Con
  la curva de cada uno, 1 MB de saltos de línea eran unas dos horas.
- **Números sin cota.** El importe del QR se leía con `Decimal` a secas, que
  acepta `1E-900000000` y escribe novecientos millones de ceros al ponerlo en
  una frase. Y una clave RSA de cualquier tamaño llegaba a `pow`: medido, un
  módulo y un exponente de 32.768 bits tardan 64 s en una verificación.
- **El lote sin aislar.** Lo que corre después del `try` de cada fichero, y las
  reglas entre ficheros, se llevaban el lote entero con una excepción.

Las pruebas de tiempo usan entradas con las que el código de antes tardaba más
de un minuto, y un tope holgado: lo que se vigila es la forma de la curva, no
los milisegundos de esta máquina.

El escaneo del 08-11-2026, solo de `solucion_publica.py`, encontró el mismo
coste cuadrático en cuatro reglas más. Esas se miden de otra manera, por la
razón que se da al llegar a ellas: cuántas veces más tardan con cuatro veces
más entrada.
"""

from __future__ import annotations

import re
import time
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from validador import cifras, factura, firma, formato, qr_fiscal, solucion_publica
from validador.firma import ClaveNoSoportada
from validador.incidencias import AVISO, ERROR
from test_cadena import HOJA, RAIZ, certificado
from test_comprobar_copia import COPIA, ORIGINAL
from test_firma import _der, _entero, _secuencia
from test_solucion_publica import (DEL_BOE, FIRMA_EN_UN_FICHERO, PDF, _como_copia_fiel,
                                   _contrato, _detras_de_los_documentos, cambia)

TOPE = 5.0  # segundos; el código de antes pasaba del minuto con estas entradas


def _cronometro(hacer):
    inicio = time.perf_counter()
    salida = hacer()
    return salida, time.perf_counter() - inicio


# --- El BGM de un EDIFACT --------------------------------------------------

# La expresión de antes, tal cual, para comprobar que la nueva búsqueda dice lo
# mismo en todo lo que no es una tira de cien mil saltos de línea.
_ANTES = re.compile(rb"(?:^|['\r\n])\s*BGM\+([0-9]{3})", re.IGNORECASE)


class TestElBgm:
    def test_una_tira_de_saltos_no_cuelga_la_deteccion(self):
        datos = b"UNH+1+INVOIC:D:96A:UN'" + b"\n" * 100_000
        deteccion, tarda = _cronometro(lambda: formato.detectar(datos))
        assert tarda < TOPE, f"tarda {tarda:.1f} s"
        assert deteccion.codigo_tipo is None

    @pytest.mark.parametrize("datos", [
        b"UNH+1+INVOIC:D:96A:UN'BGM+380+1'",
        b"UNH+1+INVOIC:D:96A:UN'\r\nBGM+381+1'",
        b"UNH+1+INVOIC:D:96A:UN'\n   BGM+383+1'",
        b"UNH+1+INVOIC:D:96A:UN' \t BGM+384+1'",
        b"UNH+1+INVOIC:D:96A:UN'XBGM+380+1'BGM+381'",
        b"UNH+1+INVOIC:D:96A:UN'  \n  \n bgm+389+1'",
        b"UNH+1+INVOIC:D:96A:UN'NAD+BGM+380'",
        b"BGM+380'UNH+1+INVOIC:D:96A:UN'",
        b"  BGM+380'",
        b"UNH+1+INVOIC'FTX+AAA+++BGM+380'\nBGM+381'",
    ])
    def test_dice_lo_mismo_que_la_expresion_de_antes(self, datos):
        antes = _ANTES.search(datos)
        ahora = formato._buscar_bgm(datos, "+", "'")
        assert ahora == (antes.group(1) if antes else None)


# --- Los miles de una cifra ------------------------------------------------


class TestLasCifras:
    def test_millones_de_cifras_no_cuelgan(self):
        valor = Decimal("9" * 2_000_000 + ".123")
        escrita, tarda = _cronometro(lambda: cifras.en_castellano(valor))
        assert tarda < TOPE, f"tarda {tarda:.1f} s"
        assert len(escrita) < 200

    def test_agrupar_los_miles_es_lineal(self):
        """Aparte: `en_castellano` ya no le pasa cifras así, porque las corta
        antes, y sin esta prueba se podría volver a la cuadrática sin verlo."""
        _, tarda = _cronometro(lambda: cifras._agrupar("9" * 2_000_000))
        assert tarda < TOPE, f"tarda {tarda:.1f} s"
        assert cifras._agrupar("1234567") == "1.234.567"
        assert cifras._agrupar("123456") == "123.456"
        assert cifras._agrupar("12345") == "12.345"

    def test_una_cifra_desmesurada_se_dice_y_no_se_escribe(self):
        """Con `1E-5000` y no con el `1E-900000000` del escaneo: el mensaje es
        el mismo, y así la prueba no se come la memoria si alguien quita el
        corte. El del escaneo ya no llega aquí: ver `TestElQr`."""
        for escribir in (cifras.en_castellano, cifras.tiene, cifras.calculada):
            escrita = escribir(Decimal("1E-5000"))
            assert len(escrita) < 200, escribir.__name__
        # «0,» y cinco mil decimales: 5001 dígitos, sin punto porque los miles
        # se marcan desde cinco cifras, como en todas las demás.
        assert "5001 dígitos" in cifras.en_castellano(Decimal("1E-5000"))

    def test_las_de_siempre_salen_como_siempre(self):
        assert cifras.en_castellano(Decimal("12345.678")) == "12.345,678"
        assert cifras.en_castellano(Decimal("1234")) == "1234,00"
        assert cifras.en_castellano(Decimal("-106.0")) == "-106,00"
        assert cifras.en_castellano(Decimal("1000000")) == "1.000.000,00"

    def test_treinta_cifras_enteras_no_tumban_el_redondeo(self):
        """El `quantize` de antes, con la precisión de 28, lanzaba
        `InvalidOperation` con 27 cifras enteras o más: F29."""
        assert cifras.en_castellano(Decimal("1" * 30)) == (
            "111.111.111.111.111.111.111.111.111.111,00")


# --- La dirección del QR ---------------------------------------------------


class TestElQr:
    def test_muchos_parametros_no_cuelgan(self):
        consulta = "&".join(["a"] * 200_000)
        (pares, repetidos), tarda = _cronometro(lambda: qr_fiscal._parametros(consulta))
        assert tarda < TOPE, f"tarda {tarda:.1f} s"
        assert repetidos == ["a"]
        assert len(pares) == 200_000

    def test_los_repetidos_se_siguen_viendo(self):
        _, repetidos = qr_fiscal._parametros("nif=1&numserie=2&nif=3&fecha=4&fecha=5")
        assert repetidos == ["fecha", "nif"]

    @pytest.mark.parametrize("texto", ["1E-900000000", "NaN", "sNaN", "Infinity", "1_000"])
    def test_un_importe_que_no_es_xs_decimal_no_se_lee(self, texto):
        assert qr_fiscal._importe(texto) is None

    def test_un_importe_normal_se_lee(self):
        assert qr_fiscal._importe("121.00") == Decimal("121.00")


# --- Las claves RSA --------------------------------------------------------

_OID_RSA = b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01"


def _con_clave(modulo: int, exponente: int) -> bytes:
    spki = _secuencia(
        _secuencia(_der(0x06, _OID_RSA), _der(0x05, b"")),
        _der(0x03, b"\x00" + _secuencia(_entero(modulo), _entero(exponente))),
    )
    return certificado("Clave enorme", "Raiz de pruebas", HOJA, RAIZ, spki=spki)


class TestLasClaves:
    def test_un_modulo_desmesurado_no_llega_a_pow(self):
        modulo = (1 << 20_000) | 1
        with pytest.raises(ClaveNoSoportada, match="bits"):
            firma.leer_certificado(_con_clave(modulo, 65537))

    def test_un_exponente_desmesurado_tampoco(self):
        with pytest.raises(ClaveNoSoportada, match="exponente"):
            firma.leer_certificado(_con_clave(HOJA[0], (1 << 300) | 1))

    @pytest.mark.parametrize("bits", [1024, 4096, 8192, 16384])
    def test_las_de_verdad_se_leen(self, bits):
        """Medido: de 339 certificados RSA de las anclas y las muestras, el
        mayor es de 8192 bits y ningún exponente pasa de 17 bits."""
        modulo = (1 << (bits - 1)) | 1
        cert = firma.leer_certificado(_con_clave(modulo, 65537))
        assert cert.modulo.bit_length() == bits


# --- El lote ---------------------------------------------------------------


def _lote(tmp_path: Path, *contenidos: str):
    rutas = []
    for numero, contenido in enumerate(contenidos):
        ruta = tmp_path / f"f{numero}.xml"
        ruta.write_text(contenido, encoding="utf-8")
        rutas.append(ruta)
    marcha = factura.LoteEnMarcha(rutas)
    for _ in marcha:
        pass
    return marcha.lote


class TestElLote:
    def test_un_baseQuantity_extremo_no_se_lleva_el_lote(self, tmp_path):
        """F30: la división del precio daba `Overflow` fuera del `try`."""
        extrema = COPIA.replace(
            "<cbc:PriceAmount currencyID=\"EUR\">50.00</cbc:PriceAmount>",
            "<cbc:PriceAmount currencyID=\"EUR\">50.00</cbc:PriceAmount>"
            "<cbc:BaseQuantity>0." + "0" * 1_000_000 + "1</cbc:BaseQuantity>")
        assert extrema != COPIA
        lote = _lote(tmp_path, extrema, ORIGINAL.read_text(encoding="utf-8"))
        assert len(lote.informes) == 2
        assert all(informe.deteccion for _, informe in lote.informes)
        # Y no porque el `try` del lote lo haya tapado: el precio que no se
        # puede dividir no se compara, y el fichero sale como lo que es.
        _, suyo = lote.informes[0]
        assert "VALIDADOR-SE-ATRAGANTA" not in {i.codigo for i in suyo.incidencias}

    def test_si_lo_de_despues_del_try_falla_el_fichero_lo_dice(
            self, tmp_path, monkeypatch):
        """El último recurso de cada fichero: lo que se saca para las reglas
        del lote corre ahora dentro de un `try`, y si falla, el informe del
        fichero se queda y lleva la queja; los demás ni se enteran."""
        from validador import comprobar_copia

        def revienta(*_, **__):
            raise ArithmeticError("provocado")

        monkeypatch.setattr(comprobar_copia, "extraer_de", revienta)
        lote = _lote(tmp_path, ORIGINAL.read_text(encoding="utf-8"), COPIA)
        assert len(lote.informes) == 2
        for _, informe in lote.informes:
            codigos = {i.codigo for i in informe.incidencias}
            assert "VALIDADOR-SE-ATRAGANTA" in codigos
            assert informe.deteccion, "el informe del fichero se ha perdido"

    def test_una_pareja_con_treinta_cifras_no_se_lleva_el_lote(self, tmp_path):
        """F29: la comparación entre ficheros escribía la diferencia y el
        redondeo lanzaba `InvalidOperation` fuera de todo `try`."""
        enorme = "1" * 30
        copia = COPIA.replace(
            "<cbc:TaxExclusiveAmount currencyID=\"EUR\">100.00</cbc:TaxExclusiveAmount>",
            f"<cbc:TaxExclusiveAmount currencyID=\"EUR\">{enorme}</cbc:TaxExclusiveAmount>")
        assert copia != COPIA
        lote = _lote(tmp_path, ORIGINAL.read_text(encoding="utf-8"), copia)
        assert len(lote.informes) == 2
        assert any(enorme[:3] in i.mensaje or "111.111" in i.mensaje
                   for i in lote.cruzadas)

    def test_si_una_regla_entre_ficheros_falla_se_dice_y_no_se_pierde_nada(
            self, tmp_path, monkeypatch):
        """El último recurso: una regla entre ficheros que se cae deja una queja
        del lote, y los informes de cada fichero siguen ahí."""
        from validador import comprobar_copia

        def revienta(*_, **__):
            raise ArithmeticError("provocado")

        monkeypatch.setattr(comprobar_copia, "reglas_de_lote", revienta)
        lote = _lote(tmp_path, ORIGINAL.read_text(encoding="utf-8"), COPIA)
        assert len(lote.informes) == 2
        caida = [i for i in lote.cruzadas if i.codigo == "VALIDADOR-SE-ATRAGANTA"]
        assert caida and "provocado" in caida[0].mensaje


# --- Las reglas de la solución pública -------------------------------------

# Cuatro reglas de `solucion_publica` quitaban los repetidos de una lista con
# `x not in lista`, y la lista crecía con algo que escribe quien hace la
# factura: el nombre de cada línea, o cada esquema de impuesto distinto. Lo
# encontró el escaneo del 08-11-2026 y lo cuenta HALLAZGOS. Se llama a la
# regla sola, sobre el árbol ya leído, para que el resto del validador no tape
# la curva.
#
# Aquí no vale un tope en segundos como arriba. Lo que queda después del
# arreglo es lineal, pero caro: cada llamada a `xpath` cuesta unos 20 µs
# (medido; no depende del tamaño del documento), y una regla hace dos o tres
# por línea. Con 60.000 líneas, el código de antes tardaba de 41 a 53 s y el de
# ahora, de 4 a 10 s, según lo ocupada que estuviera la máquina, y en GitHub la
# suite corre unas cuatro veces más deprisa: un tope que separe las dos cosas
# aquí las confunde allí. Así que se mide la forma: con cuatro veces más
# entrada, lo lineal tarda cuatro veces más y lo cuadrático, dieciséis.
# Medido el 08-11-2026, de 20.000 a 80.000: el arreglo da de 3,1 a 4,8; el
# código de antes, de 20.000 a 40.000, ya daba de 3,1 a 3,7 por cada doble.

_LINEA = "  <cac:InvoiceLine>"
POCAS = 20_000
CRECE_COMO_MUCHO = 8  # entre el 4 de lo lineal y el 16 de lo cuadrático


def _con_lineas(*lineas: str) -> str:
    return cambia(DEL_BOE, _LINEA, "".join(lineas) + _LINEA)


def _linea(ident, dentro: str) -> str:
    return f"<cac:InvoiceLine><cbc:ID>{ident}</cbc:ID><cac:Item>{dentro}</cac:Item></cac:InvoiceLine>"


def _categoria(codigo: str, esquema: str = "VAT") -> str:
    return (f"<cac:ClassifiedTaxCategory><cbc:ID>{codigo}</cbc:ID><cac:TaxScheme>"
            f"<cbc:ID>{esquema}</cbc:ID></cac:TaxScheme></cac:ClassifiedTaxCategory>")


def _propiedad(nombre: str) -> str:
    return (f"<cac:AdditionalItemProperty><cbc:Name>{nombre}</cbc:Name>"
            "<cbc:Value>v</cbc:Value></cac:AdditionalItemProperty>")


def _crece(regla, hacer) -> tuple[float, list]:
    """Cuántas veces más tarda la regla con cuatro veces más entrada, y lo que
    dice con la mayor."""
    tiempos, salida = [], []
    for cuantas in (POCAS, 4 * POCAS):
        raiz = etree.fromstring(hacer(cuantas).encode("utf-8"))
        salida, tarda = _cronometro(lambda: regla(raiz))
        tiempos.append(tarda)
    return tiempos[1] / tiempos[0], salida


def _resumen(incidencias) -> list[tuple[str, str, str, str]]:
    return [(i.codigo, i.gravedad, i.campo, i.encontrado) for i in incidencias]


class TestLaSolucionPublica:
    def test_muchas_lineas_K_no_cuelgan_las_categorias(self):
        """F1: el lugar de cada línea con una categoría que L4 no tiene."""
        veces, salida = _crece(solucion_publica._categorias, lambda cuantas: _con_lineas(
            *(_linea(n, _categoria("K")) for n in range(cuantas))))
        assert veces < CRECE_COMO_MUCHO, f"con cuatro veces más líneas, {veces:.1f} veces más tiempo"
        assert [i.encontrado for i in salida] == ["K"]

    def test_muchos_impuestos_distintos_no_cuelgan_el_tipo(self):
        """F3: cada `cac:TaxScheme/cbc:ID` distinto de VAT."""
        veces, salida = _crece(solucion_publica._tipo_de_impuesto, lambda cuantas: _con_lineas(
            *(_linea(n, _categoria("S", f"X{n}")) for n in range(cuantas))))
        assert veces < CRECE_COMO_MUCHO, f"con cuatro veces más esquemas, {veces:.1f} veces más tiempo"
        assert salida[0].encontrado.count(",") == 4 * POCAS - 1

    def test_muchas_propiedades_no_cuelgan_la_informacion_adicional(self):
        """F4: el lugar de cada línea con una propiedad fuera de L8."""
        veces, salida = _crece(solucion_publica._informacion_adicional, lambda cuantas: _con_lineas(
            *(_linea(n, _propiedad("Color")) for n in range(cuantas))))
        assert veces < CRECE_COMO_MUCHO, f"con cuatro veces más líneas, {veces:.1f} veces más tiempo"
        assert len(salida) == 1

    def test_muchos_ficheros_en_una_copia_no_cuelgan(self):
        """F2: en una copia fiel, los ficheros de dentro de la firma se
        buscaban uno a uno en la lista de los de fuera."""
        veces, salida = _crece(solucion_publica._ficheros_embebidos, lambda cuantas: _como_copia_fiel(
            _detras_de_los_documentos(_contrato("<cbc:EmbeddedDocument/>" * cuantas))))
        assert veces < CRECE_COMO_MUCHO, f"con cuatro veces más ficheros, {veces:.1f} veces más tiempo"
        assert [i.gravedad for i in salida] == [ERROR]

    # Lo que dicen con pocas líneas, sacado del código de antes del arreglo
    # (a51d53e): el orden es el de la primera vez que sale cada cosa, y los
    # repetidos, una vez.

    def test_las_categorias_dicen_lo_mismo(self):
        xml = _con_lineas(_linea(3, _categoria("K")), _linea(2, _categoria("B")),
                          _linea(3, _categoria("K")), _linea(4, _categoria("K")))
        assert _resumen(solucion_publica._categorias(etree.fromstring(xml.encode()))) == [(
            "SPFE-CATEGORIA", ERROR,
            "Categoría de IVA (BT-95, BT-102, BT-118, BT-151) · línea 3, línea 2, línea 4", "K, B")]

    def test_el_tipo_de_impuesto_dice_lo_mismo(self):
        xml = _con_lineas(_linea(3, _categoria("S", "IGIC")), _linea(4, _categoria("S", "GST")),
                          _linea(5, _categoria("S", "IGIC")))
        assert _resumen(solucion_publica._tipo_de_impuesto(etree.fromstring(xml.encode()))) == [(
            "SPFE-TIPO-DE-IMPUESTO", ERROR, "Tipo de impuesto (cac:TaxScheme/cbc:ID) · líneas",
            "IGIC, GST")]

    def test_la_informacion_adicional_dice_lo_mismo(self):
        xml = _con_lineas(_linea(3, _propiedad("Color") + _propiedad("Lote")),
                          _linea(2, _propiedad("Color")), _linea(3, _propiedad("Talla")))
        assert _resumen(solucion_publica._informacion_adicional(etree.fromstring(xml.encode()))) == [(
            "SPFE-INFORMACION-ADICIONAL", AVISO, "Código de la propiedad (BT-160) · línea 3, línea 2",
            "Color, Lote, Talla")]

    @pytest.mark.parametrize("copia, trozos, esperado", [
        (True, (_contrato(PDF), FIRMA_EN_UN_FICHERO, _contrato(PDF)), [
            ("SPFE-FICHERO-EMBEBIDO", ERROR, "Fichero embebido (cac:Attachment)",
             "contrato.pdf en el documento Contrato-2026-7"),
            ("SPFE-FICHERO-EMBEBIDO", AVISO, "Firma electrónica",
             "la firma en un fichero (cac:Signature)")]),
        (True, (FIRMA_EN_UN_FICHERO,), [
            ("SPFE-FICHERO-EMBEBIDO", AVISO, "Firma electrónica",
             "la firma en un fichero (cac:Signature)")]),
        (False, (_contrato(PDF), FIRMA_EN_UN_FICHERO), [
            ("SPFE-FICHERO-EMBEBIDO", ERROR, "Fichero embebido (cac:Attachment)",
             "contrato.pdf en el documento Contrato-2026-7")]),
    ])
    def test_los_ficheros_embebidos_dicen_lo_mismo(self, copia, trozos, esperado):
        xml = _detras_de_los_documentos(*trozos)
        xml = _como_copia_fiel(xml) if copia else xml
        assert _resumen(solucion_publica._ficheros_embebidos(etree.fromstring(xml.encode()))) == esperado


# --- El tamaño del fichero -------------------------------------------------


class TestElTamano:
    def test_un_fichero_desmesurado_no_se_valida_y_se_dice(self):
        datos = b"<a>" + b" " * (formato.TAMANO_MAXIMO + 1) + b"</a>"
        deteccion = formato.detectar(datos)
        assert not deteccion
        assert "MB" in deteccion.motivo

    def test_la_mayor_de_las_muestras_cabe_de_sobra(self):
        """Medido: de los 173 ficheros de muestras, el mayor pesa 3,3 MB."""
        assert formato.TAMANO_MAXIMO > 5 * 3_300_000
