# -*- coding: utf-8 -*-
"""Lo que no está donde la sintaxis pone la factura no es la factura.

Por qué existe
--------------
El escaneo de seguridad del 01 al 03-11-2026 encontró otra grieta repetida:
varios lectores buscaban las partes de la factura con `//`, en todo el
documento, y se quedaban con **la primera** que apareciera. Eso incluye lo que
cuelga de un `ds:Object` de la firma, que nadie firma, y lo que va en las
extensiones de UBL, que van antes que las partes de verdad. Un tercero sin
ninguna clave metía ahí un vendedor señuelo, con otro país o con otro NIF, y:

  - el país del emisor salía del señuelo, y con un país extranjero se
    apagaban las reglas españolas (`codigo_unico.pais_emisor`);
  - el código único se componía con el NIF del señuelo, y la factura dejaba de
    ser duplicada de sí misma y salía del aviso de cambio de cuenta
    (`codigo_unico._extraer_ubl`, `_extraer_facturae`, `cuentas_de_cobro`);
  - y en una lista de confianza firmada, un prestador metido en la firma
    acababa en el conjunto de anclas (`tsl.leer`), lo que se prueba en
    `test_tsl.py`.

Mientras, la firma seguía diciendo que nadie había tocado nada, porque lo que
se había tocado no estaba firmado: el problema no era la firma, era leer de
donde la firma no llega.

Cómo se prueba
--------------
Cada documento se valida dos veces: con un envoltorio vacío en el sitio donde
iría el señuelo, y con el señuelo dentro. Las dos veces tienen que decir lo
mismo, palabra por palabra. Comparar con el envoltorio vacío y no con el
documento de partida separa lo que es del señuelo de lo que es solo de haber
añadido un elemento donde no va.

El señuelo es una copia de las partes de verdad con otros datos: cada cifra
corrida uno (2 pasa a 3, 9 a 0) y España cambiada por Francia. Un lector que
lea del señuelo cambia algún mensaje, el NIF, el país o el número, y la prueba
sale en rojo, esté en el módulo que esté.
"""
from __future__ import annotations

import copy
import datetime
import pathlib

import pytest
from lxml import etree

from validador import codigo_unico, factura
from validador.formato import detectar, parser

from test_firma import HOY as HOY_DE_LA_FIRMA
from test_firma import _ds, con_objeto_delante, envolvente

RAIZ = pathlib.Path(__file__).resolve().parent.parent
EJEMPLOS = RAIZ / "ejemplos"
HOY = datetime.date(2026, 9, 20)

NS_EXT = "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
NS_AJENO = "urn:ejemplo:senuelo"

_CIFRA_SIGUIENTE = str.maketrans("0123456789", "1234567890")
_PAISES = {"ES": "FR", "ESP": "FRA"}


def senuelo(nodo):
    """Una copia de `nodo` con otros datos en cada hoja."""
    otro = copy.deepcopy(nodo)
    for hoja in otro.iter():
        if not isinstance(hoja.tag, str) or len(hoja) or not hoja.text:
            continue
        escrito = hoja.text.strip()
        hoja.text = _PAISES.get(escrito, escrito.translate(_CIFRA_SIGUIENTE))
    return otro


def _por_nombre(raiz, *nombres):
    return [
        nodo
        for nombre in nombres
        for nodo in raiz.xpath(f".//*[local-name()='{nombre}']")
    ]


def lo_que_dice(informe) -> list[tuple]:
    return sorted(
        (i.codigo, i.gravedad, i.mensaje, i.campo, i.esperado, i.encontrado)
        for i in informe.incidencias or []
    )


def lo_que_se_saca(datos: bytes):
    """Lo que leen del documento los lectores del escaneo, aparte del informe:
    con un informe idéntico por casualidad, esto sigue diciendo qué se leyó."""
    raiz = etree.fromstring(datos, parser())
    deteccion = detectar(datos)
    return (
        deteccion.version,
        deteccion.tipo_documento,
        codigo_unico.pais_emisor(raiz, deteccion),
        codigo_unico.nif_receptor(raiz, deteccion),
        [
            (c.nif_emisor, c.numero_completo, c.fecha)
            for c in codigo_unico.extraer_de(raiz, deteccion)
        ],
    )


def _iguales(sin, con, hoy):
    antes = factura.validar(sin, hoy=hoy)
    despues = factura.validar(con, hoy=hoy)
    assert antes.validado and despues.validado
    assert lo_que_se_saca(con) == lo_que_se_saca(sin)
    assert lo_que_dice(despues) == lo_que_dice(antes)
    assert despues.firma == antes.firma


# --- UBL: el señuelo en las extensiones, que van antes que las partes ------

UBL = ["f-0001.xml", "f-0002.xml", "f-0002-bis.xml", "f-0006.xml"]


def _con_extension(datos: bytes, lleno: bool) -> bytes:
    raiz = etree.fromstring(datos, parser())
    extensiones = etree.Element(f"{{{NS_EXT}}}UBLExtensions")
    contenido = etree.SubElement(
        etree.SubElement(extensiones, f"{{{NS_EXT}}}UBLExtension"),
        f"{{{NS_EXT}}}ExtensionContent",
    )
    envoltorio = etree.SubElement(contenido, f"{{{NS_AJENO}}}Envoltorio")
    if lleno:
        partes = _por_nombre(raiz, "AccountingSupplierParty", "AccountingCustomerParty")
        assert partes
        for parte in partes:
            envoltorio.append(senuelo(parte))
    raiz.insert(0, extensiones)
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


@pytest.mark.parametrize("nombre", UBL)
def test_ubl_con_un_vendedor_en_las_extensiones(nombre):
    datos = (EJEMPLOS / nombre).read_bytes()
    _iguales(_con_extension(datos, False), _con_extension(datos, True), HOY)


# --- CII: no tiene extensiones, así que el señuelo va delante de todo -------


def _cii_con_envoltorio(datos: bytes, lleno: bool) -> bytes:
    raiz = etree.fromstring(datos, parser())
    envoltorio = etree.Element(f"{{{NS_AJENO}}}Envoltorio")
    if lleno:
        partes = _por_nombre(
            raiz, "ExchangedDocumentContext", "ExchangedDocument",
            "SellerTradeParty", "BuyerTradeParty",
        )
        assert len(partes) == 4
        for parte in partes:
            envoltorio.append(senuelo(parte))
    raiz.insert(0, envoltorio)
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def test_cii_con_las_partes_delante():
    datos = (EJEMPLOS / "cii-A-0001.xml").read_bytes()
    _iguales(_cii_con_envoltorio(datos, False), _cii_con_envoltorio(datos, True), HOY)


# --- Facturae: el señuelo en un ds:Object, que nadie firma ------------------


def _facturae_con_objeto(datos: bytes, lleno: bool) -> bytes:
    """Un `ds:Object` sin firmar al final de la firma de un Facturae firmado
    con la firma dentro, que es la forma de `fe-0001.xml`. La firma va al final
    del documento, así que aquí el señuelo va **detrás** de lo de verdad: lo
    que cuenta es quien lo lee todo, como las facturas de `Invoices`."""
    raiz = etree.fromstring(datos, parser())
    firma_el = raiz.xpath("//*[local-name()='Signature']")[0]
    objeto = etree.SubElement(firma_el, _ds("Object"))
    if lleno:
        for nombre in ("FileHeader", "Parties", "Invoices"):
            objeto.append(senuelo(raiz.xpath(f"./*[local-name()='{nombre}']")[0]))
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def test_facturae_firmado_con_un_objeto_al_final():
    datos = (EJEMPLOS / "fe-0001.xml").read_bytes()
    _iguales(_facturae_con_objeto(datos, False), _facturae_con_objeto(datos, True), HOY)


def _envolvente_con_objeto_delante(lleno: bool) -> bytes:
    """El caso del escaneo: Facturae firmado en envolvente, con un `ds:Object`
    sin firmar **delante** del de verdad. Es lo que hace `con_objeto_delante`
    en `test_firma.py`."""
    datos = envolvente()
    envoltorio = etree.Element(f"{{{NS_AJENO}}}Envoltorio")
    if lleno:
        raiz = etree.fromstring(datos, parser())
        factura_de_verdad = raiz.xpath("//*[local-name()='Facturae']")[0]
        for nombre in ("FileHeader", "Parties", "Invoices"):
            hijo = factura_de_verdad.xpath(f"./*[local-name()='{nombre}']")
            assert hijo, nombre
            envoltorio.append(senuelo(hijo[0]))
    return con_objeto_delante(datos, envoltorio)


def test_facturae_envolvente_con_un_objeto_delante():
    _iguales(
        _envolvente_con_objeto_delante(False),
        _envolvente_con_objeto_delante(True),
        HOY_DE_LA_FIRMA.date(),
    )


def test_el_pais_del_emisor_es_el_firmado():
    """El caso del escaneo tal cual, sin comparar informes: si la prueba de
    arriba fallara por otro lector, esta dice si el país está bien.

    El Facturae de `test_firma` no escribe el país del vendedor, así que lo
    firmado es «no se dice», y eso es lo que tiene que salir: no el FR del
    señuelo."""
    vendedor = etree.fromstring(
        "<SellerParty><LegalEntity><OverseasAddress><CountryCode>FRA</CountryCode>"
        "</OverseasAddress></LegalEntity></SellerParty>"
    )
    sin = envolvente()
    con = con_objeto_delante(sin, vendedor)
    raiz_sin = etree.fromstring(sin, parser())
    raiz_con = etree.fromstring(con, parser())
    firmado = codigo_unico.pais_emisor(raiz_sin, detectar(sin))
    assert codigo_unico.pais_emisor(raiz_con, detectar(con)) == firmado != "FR"
