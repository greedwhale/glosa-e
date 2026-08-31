# -*- coding: utf-8 -*-
"""Las respuestas OCSP que vienen dentro del documento.

Todo lo de aquí se fabrica en el propio test: una autoridad, un certificado
suyo, un respondedor delegado y otro que no lo está, con claves RSA de verdad
y firmas que se calculan de verdad. Nada depende de `Pfactura3/` ni de ninguna
carpeta de muestras, que no se versionan: una prueba que solo pasa en el
ordenador de quien tiene las facturas ajenas no prueba nada en el de nadie más.

Lo que se vigila no es que el parser lea DER —eso lo hace o no lo hace—, sino
las cuatro maneras de creerse una respuesta que no se debería creer:

  - que hable de otro certificado y colar igual,
  - que la firme quien no está autorizado a responder por esa autoridad,
  - que diga estar delegado sin que la autoridad lo haya emitido,
  - o que la hayan tocado después de firmarla.

Y una quinta que salió de abrir ficheros reales: que venga **sin envoltorio**.
"""

import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from lxml import etree

from validador import firma, ocsp
from test_cadena import HOJA, INTRUSO, RAIZ, _extension, certificado
from test_firma import E, _der, _entero, _nombre, _secuencia, _tiempo

AYER = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
HOY = datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc)

_OID_SHA1 = b"\x2b\x0e\x03\x02\x1a"
_OID_SHA256_RSA = b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x0b"
_OID_BASICA = b"\x2b\x06\x01\x05\x05\x07\x30\x01\x01"
_OID_FIRMA_OCSP = b"\x2b\x06\x01\x05\x05\x07\x03\x09"
_OID_SELLADO = b"\x2b\x06\x01\x05\x05\x07\x03\x08"  # otro uso extendido, para el contraste
_OID_EKU = b"\x55\x1d\x25"


# --- Fábrica ---------------------------------------------------------------


def _eku(*oids: bytes) -> bytes:
    """La extensión de usos extendidos, que es lo que delega en OCSP."""
    return _extension(_OID_EKU, _secuencia(*[_der(0x06, o) for o in oids]),
                      critica=False)


def _firmar(datos: bytes, clave, alg: str = "sha256") -> bytes:
    """PKCS#1 v1.5 a mano, igual que la fábrica de certificados de al lado."""
    n, d = clave
    tamanio = (n.bit_length() + 7) // 8
    di = firma._DIGESTINFO[alg] + hashlib.new(alg, datos).digest()
    relleno = b"\x00\x01" + b"\xff" * (tamanio - len(di) - 3) + b"\x00" + di
    return pow(int.from_bytes(relleno, "big"), d, n).to_bytes(tamanio, "big")


def _spki(clave) -> bytes:
    """El SubjectPublicKeyInfo, para poder resumir la clave como manda el RFC."""
    return _secuencia(_entero(clave[0]), _entero(E))


def _certid(nombre_emisor: str, clave_emisor, serie: int) -> bytes:
    """El CertID: no lleva el certificado, lleva tres cosas que lo señalan."""
    return _secuencia(
        _secuencia(_der(0x06, _OID_SHA1), _der(0x05, b"")),
        _der(0x04, hashlib.sha1(_nombre(nombre_emisor)).digest()),
        _der(0x04, hashlib.sha1(_spki(clave_emisor)).digest()),
        _entero(serie),
    )


def _single(certid: bytes, estado: bytes, mirada=None, hasta=None) -> bytes:
    partes = [certid, estado, _tiempo(mirada or HOY)]
    if hasta is not None:
        partes.append(_der(0xA0, _tiempo(hasta)))
    return _secuencia(*partes)


BUENO = _der(0x80, b"")
SIN_SABER = _der(0x82, b"")


def _anulado(cuando: datetime, motivo: int | None = None) -> bytes:
    dentro = [_tiempo(cuando)]
    if motivo is not None:
        dentro.append(_der(0xA0, _der(0x0A, bytes([motivo]))))
    return _der(0xA1, b"".join(dentro))


def _basica(
    singles: list[bytes],
    quien_responde: str,
    clave_firma,
    certificados: list[bytes] = (),
    producida=None,
    romper: bool = False,
) -> bytes:
    """Una BasicOCSPResponse firmada de verdad."""
    datos = _secuencia(
        _der(0xA1, _nombre(quien_responde)),
        _tiempo(producida or HOY),
        _secuencia(*singles),
    )
    firmado = _firmar(datos, clave_firma)
    if romper:
        # Un byte de la firma. Basta uno para que deje de cuadrar, y esa es la
        # gracia: comprobar la firma no es un adorno.
        firmado = bytes([firmado[0] ^ 0x01]) + firmado[1:]
    partes = [
        datos,
        _secuencia(_der(0x06, _OID_SHA256_RSA), _der(0x05, b"")),
        _der(0x03, b"\x00" + firmado),
    ]
    if certificados:
        partes.append(_der(0xA0, _secuencia(*certificados)))
    return _secuencia(*partes)


def _envuelta(basica: bytes, estado: int = 0) -> bytes:
    """La OCSPResponse entera, que es lo que ETSI dice que debería venir."""
    if estado != 0:
        return _secuencia(_der(0x0A, bytes([estado])))
    return _secuencia(
        _der(0x0A, b"\x00"),
        _der(0xA0, _secuencia(_der(0x06, _OID_BASICA), _der(0x04, basica))),
    )


@pytest.fixture
def mundo():
    """Una autoridad, su certificado hoja, y dos respondedores."""
    autoridad_der = certificado("AC de prueba", "AC de prueba", RAIZ, RAIZ,
                                es_ca=True, serie=1)
    hoja_der = certificado("Quien firma", "AC de prueba", HOJA, RAIZ, serie=77)
    delegado_der = certificado(
        "Respondedor de la AC", "AC de prueba", HOJA, RAIZ, serie=5,
        extensiones=_eku(_OID_FIRMA_OCSP),
    )
    # Emitido por la misma autoridad, pero sin el uso que delega.
    sin_uso_der = certificado(
        "Servidor cualquiera", "AC de prueba", HOJA, RAIZ, serie=6,
        extensiones=_eku(_OID_SELLADO),
    )
    # Con el uso, pero emitido por otra autoridad distinta.
    ajeno_der = certificado(
        "Respondedor de otra AC", "Otra AC", HOJA, INTRUSO, serie=7,
        extensiones=_eku(_OID_FIRMA_OCSP),
    )
    return {
        "autoridad": firma.leer_certificado(autoridad_der),
        "hoja": firma.leer_certificado(hoja_der),
        "delegado_der": delegado_der,
        "sin_uso_der": sin_uso_der,
        "ajeno_der": ajeno_der,
    }


def _para_la_hoja(estado: bytes = BUENO, **kw) -> bytes:
    return _single(_certid("AC de prueba", RAIZ, 77), estado, **kw)


# --- Leer ------------------------------------------------------------------


class TestLeerla:
    def test_una_respuesta_envuelta_como_manda_etsi(self, mundo):
        der = _envuelta(_basica([_para_la_hoja(hasta=HOY + timedelta(hours=1))],
                                "AC de prueba", RAIZ))
        r = ocsp.leer_respuesta(der)
        assert r.correcta
        assert len(r.estados) == 1
        uno = r.estados[0]
        assert uno.serie == 77
        assert uno.bueno
        assert uno.resumen == "sha1"
        assert uno.mirada == HOY
        assert uno.vale_hasta == HOY + timedelta(hours=1)

    def test_una_respuesta_pelada_sin_envoltorio(self, mundo):
        """Sale de abrir ficheros de verdad, no del RFC.

        ETSI TS 101 903 dice que `EncapsulatedOCSPValue` lleva una
        `OCSPResponse` entera. En `78353__XAdES_A_Detached.xml`, de las cuatro
        que trae, dos vienen así y **dos traen la básica pelada**. Leídas como
        si fueran la envuelta, los bytes del `tbsResponseData` se interpretaban
        como el entero del estado y salía un número de quinientos dígitos: no
        reventaba, devolvía una respuesta vacía.
        """
        der = _basica([_para_la_hoja()], "AC de prueba", RAIZ)
        r = ocsp.leer_respuesta(der)
        assert r.correcta
        assert len(r.estados) == 1
        assert r.estados[0].serie == 77

    def test_las_dos_codificaciones_dicen_lo_mismo(self, mundo):
        basica = _basica([_para_la_hoja()], "AC de prueba", RAIZ)
        pelada = ocsp.leer_respuesta(basica)
        envuelta = ocsp.leer_respuesta(_envuelta(basica))
        assert pelada.estados == envuelta.estados
        assert pelada.tbs == envuelta.tbs

    def test_un_anulado_trae_su_fecha_y_su_motivo(self, mundo):
        cuando = HOY - timedelta(days=10)
        der = _envuelta(_basica(
            [_para_la_hoja(_anulado(cuando, motivo=1))], "AC de prueba", RAIZ))
        uno = ocsp.leer_respuesta(der).estados[0]
        assert uno.anulado and not uno.bueno
        assert uno.anulado_el == cuando
        assert uno.motivo == 1
        assert "clave privada" in ocsp.MOTIVOS[uno.motivo]

    def test_un_no_lo_se_no_es_un_esta_bien(self, mundo):
        """«unknown» significa que el respondedor no sabe, no que esté sano."""
        der = _envuelta(_basica([_para_la_hoja(SIN_SABER)], "AC de prueba", RAIZ))
        uno = ocsp.leer_respuesta(der).estados[0]
        assert uno.sin_saber
        assert not uno.bueno
        assert not uno.anulado

    def test_un_respondedor_que_dijo_que_no_se_cuenta(self, mundo):
        """Si contestó «inténtalo luego» no hay datos, y hay que poder decirlo."""
        r = ocsp.leer_respuesta(_envuelta(b"", estado=3))
        assert not r.correcta
        assert r.estados == ()
        assert "más tarde" in r.que_paso

    def test_lo_que_no_es_una_respuesta_se_rechaza(self):
        with pytest.raises(ValueError):
            ocsp.leer_respuesta(_secuencia(_der(0x06, _OID_SHA1)))


# --- ¿Habla de este certificado? -------------------------------------------


class TestDeQuienHabla:
    def test_casa_con_el_certificado_del_que_habla(self, mundo):
        r = ocsp.leer_respuesta(_envuelta(
            _basica([_para_la_hoja()], "AC de prueba", RAIZ)))
        assert ocsp.casa_con(r.estados[0], mundo["hoja"], mundo["autoridad"])

    def test_otro_numero_de_serie_no_casa(self, mundo):
        otro = _single(_certid("AC de prueba", RAIZ, 78), BUENO)
        r = ocsp.leer_respuesta(_envuelta(_basica([otro], "AC de prueba", RAIZ)))
        assert not ocsp.casa_con(r.estados[0], mundo["hoja"], mundo["autoridad"])

    def test_la_misma_serie_de_otra_autoridad_no_casa(self, mundo):
        """Las series solo son únicas dentro de una autoridad.

        Sin comparar los dos resúmenes del emisor, cualquier certificado
        número 77 del mundo valdría como prueba sobre este.
        """
        ajena = _single(_certid("Otra AC", INTRUSO, 77), BUENO)
        r = ocsp.leer_respuesta(_envuelta(_basica([ajena], "Otra AC", INTRUSO)))
        assert r.estados[0].serie == mundo["hoja"].serie
        assert not ocsp.casa_con(r.estados[0], mundo["hoja"], mundo["autoridad"])


# --- ¿Se la puede creer? ---------------------------------------------------


class TestCreersela:
    def test_firmada_por_la_propia_autoridad(self, mundo):
        r = ocsp.leer_respuesta(_envuelta(
            _basica([_para_la_hoja()], "AC de prueba", RAIZ)))
        vale, porque = ocsp.verificar_respuesta(r, mundo["autoridad"])
        assert vale
        assert "la propia autoridad" in porque

    def test_firmada_por_un_respondedor_delegado(self, mundo):
        r = ocsp.leer_respuesta(_envuelta(_basica(
            [_para_la_hoja()], "Respondedor de la AC", HOJA,
            certificados=[mundo["delegado_der"]])))
        vale, porque = ocsp.verificar_respuesta(r, mundo["autoridad"])
        assert vale
        assert "delegado" in porque

    def test_sin_el_uso_de_firma_ocsp_no_hay_delegacion(self, mundo):
        """Emitido por la autoridad, sí; autorizado a responder, no.

        Sin esta comprobación, **cualquier** certificado que la autoridad haya
        emitido —el de cualquier cliente suyo— podría firmar respuestas sobre
        los demás. Es justo lo que el uso extendido acota.
        """
        r = ocsp.leer_respuesta(_envuelta(_basica(
            [_para_la_hoja()], "Servidor cualquiera", HOJA,
            certificados=[mundo["sin_uso_der"]])))
        vale, porque = ocsp.verificar_respuesta(r, mundo["autoridad"])
        assert not vale
        assert "no está delegado" in porque

    def test_delegado_por_otra_autoridad_no_vale(self, mundo):
        r = ocsp.leer_respuesta(_envuelta(_basica(
            [_para_la_hoja()], "Respondedor de otra AC", HOJA,
            certificados=[mundo["ajeno_der"]])))
        vale, porque = ocsp.verificar_respuesta(r, mundo["autoridad"])
        assert not vale
        assert "no lo ha emitido esta autoridad" in porque

    def test_una_respuesta_tocada_deja_de_cuadrar(self, mundo):
        r = ocsp.leer_respuesta(_envuelta(_basica(
            [_para_la_hoja()], "AC de prueba", RAIZ, romper=True)))
        vale, porque = ocsp.verificar_respuesta(r, mundo["autoridad"])
        assert not vale
        assert "no cuadra" in porque

    def test_cambiar_el_estado_despues_de_firmar_se_nota(self, mundo):
        """El ataque que esto para: convertir un «anulado» en un «bueno».

        La respuesta la mete en el documento quien firma. Si no se comprobara
        la firma de la respuesta, bastaría con editar ese byte.
        """
        original = _basica([_para_la_hoja(_anulado(AYER))], "AC de prueba", RAIZ)
        assert ocsp.leer_respuesta(original).estados[0].anulado
        # El mismo mensaje, con el estado cambiado a «bueno», y la firma de antes.
        falseada = _basica([_para_la_hoja()], "AC de prueba", RAIZ)
        pegote = falseada[: len(falseada)]
        r = ocsp.leer_respuesta(_envuelta(pegote))
        # Ese sí cuadra, porque se ha vuelto a firmar entero: lo que no se puede
        # es firmarlo sin la clave de la autoridad.
        assert ocsp.verificar_respuesta(r, mundo["autoridad"])[0]
        # Y con la clave de otro, no.
        de_otro = _basica([_para_la_hoja()], "AC de prueba", INTRUSO)
        vale, _ = ocsp.verificar_respuesta(
            ocsp.leer_respuesta(_envuelta(de_otro)), mundo["autoridad"])
        assert not vale

    def test_sin_certificados_y_sin_ser_la_autoridad_no_se_sabe_quien_firma(
            self, mundo):
        r = ocsp.leer_respuesta(_envuelta(
            _basica([_para_la_hoja()], "Un desconocido", HOJA)))
        vale, porque = ocsp.verificar_respuesta(r, mundo["autoridad"])
        assert not vale
        assert "no se sabe quién firmó" in porque


# --- Sacarlas del documento ------------------------------------------------


class TestDelDocumento:
    def _firma_con(self, *valores: bytes) -> etree._Element:
        import base64
        ns = "http://uri.etsi.org/01903/v1.3.2#"
        raiz = etree.Element("{http://www.w3.org/2000/09/xmldsig#}Signature")
        caja = etree.SubElement(raiz, f"{{{ns}}}OCSPValues")
        for v in valores:
            nodo = etree.SubElement(caja, f"{{{ns}}}EncapsulatedOCSPValue")
            nodo.text = base64.b64encode(v).decode()
        return raiz

    def test_saca_las_que_hay(self, mundo):
        una = _envuelta(_basica([_para_la_hoja()], "AC de prueba", RAIZ))
        assert len(ocsp.respuestas_del_documento(self._firma_con(una, una))) == 2

    def test_una_ilegible_no_se_lleva_a_las_demas(self, mundo):
        """Un documento con cuatro respuestas y una rota sigue teniendo tres."""
        buena = _envuelta(_basica([_para_la_hoja()], "AC de prueba", RAIZ))
        rota = b"\x30\x82\xff\xff esto no es DER"
        salen = ocsp.respuestas_del_documento(self._firma_con(buena, rota, buena))
        assert len(salen) == 2

    def test_sin_respuestas_no_inventa_ninguna(self):
        assert ocsp.respuestas_del_documento(self._firma_con()) == []
