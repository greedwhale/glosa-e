"""Comprobaciones de la firma electrónica: XAdES sobre XML-DSig.

Las facturas firmadas de verdad viven en `MuestrasFE/`, que no se versiona. Así
que aquí se **firma de verdad**: se genera un certificado X.509 a mano, se
canonicaliza el documento, se calculan los resúmenes y se firma con una clave
RSA de juguete. El resultado es un documento que el módulo verifica por el
mismo camino que una factura del Gobierno, y del que se puede mover cualquier
byte para ver qué salta.

La clave es de 512 bits y sus primos están escritos aquí: es para probar, no
para proteger nada. Lo que importa es que **tenemos la clave privada**, y eso
permite lo que ninguna factura real permite: fabricar firmas a medida —incluida
una falsificación clásica de PKCS#1— y comprobar que se rechazan.
"""

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from lxml import etree

from validador import factura, firma
from validador.formato import detectar, parser
from validador.incidencias import AVISO, ERROR

# Un par de claves RSA de 512 bits, generado una vez y escrito aquí para que
# las pruebas den siempre lo mismo.
P = 102537101091278998115987341585599416127626670398059308299795465171831775139903
Q = 68075505016498421992239704630051902902248104096335391022395579103563275678179
N = P * Q
E = 65537
D = pow(E, -1, (P - 1) * (Q - 1))

# Un segundo par, para poder presentar «el certificado de otro».
P2 = 0xD9D8C5F2B1A7E3C9F5B2A8D4E6C1F7B3A9D5E2C8F4B1A7D3E9C5F2B8A4D1E7C3
Q2 = 0xC7B3A9D5E1F7C3B9A5D1E7F3C9B5A1D7E3F9C5B1A7D3E9F5C1B7A3D9E5F1C7B3
N2 = P2 * Q2

NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_XADES = "http://uri.etsi.org/01903/v1.3.2#"
HOY = datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc)


# --- Un certificado X.509 escrito a mano -----------------------------------


def _der(etiqueta: int, contenido: bytes) -> bytes:
    """Envuelve un contenido en su etiqueta y su longitud DER."""
    if len(contenido) < 0x80:
        largo = bytes([len(contenido)])
    else:
        crudo = len(contenido).to_bytes((len(contenido).bit_length() + 7) // 8, "big")
        largo = bytes([0x80 | len(crudo)]) + crudo
    return bytes([etiqueta]) + largo + contenido


def _entero(valor: int) -> bytes:
    crudo = valor.to_bytes((valor.bit_length() + 8) // 8, "big")
    return _der(0x02, crudo)


def _secuencia(*partes: bytes) -> bytes:
    return _der(0x30, b"".join(partes))


def _tiempo(momento: datetime) -> bytes:
    return _der(0x18, momento.strftime("%Y%m%d%H%M%SZ").encode())


def _nombre(comun: str) -> bytes:
    """Un Name con un solo atributo: el nombre común (OID 2.5.4.3)."""
    atributo = _secuencia(_der(0x06, b"\x55\x04\x03"), _der(0x0C, comun.encode()))
    return _secuencia(_der(0x31, atributo))


def certificado(
    modulo: int = N,
    exponente: int = E,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    comun: str = "Pruebas SL",
    spki: bytes | None = None,
) -> bytes:
    """Un X.509 con lo justo para que `leer_certificado` lo entienda.

    No es un certificado de verdad —no lo firma nadie y le faltan extensiones—,
    pero tiene la estructura exacta donde el módulo busca: versión etiquetada
    [0], serie, algoritmo, emisor, validez, sujeto y la clave pública. Que un
    certificado inventado valga para esto es justo lo que dice el módulo de sí
    mismo: comprueba que la firma cuadra con el certificado, **no** de quién es
    el certificado.
    """
    desde = desde or HOY - timedelta(days=365)
    hasta = hasta or HOY + timedelta(days=365)
    clave = _secuencia(_entero(modulo), _entero(exponente))
    spki = spki or _secuencia(
        _secuencia(_der(0x06, b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01"), _der(0x05, b"")),
        _der(0x03, b"\x00" + clave),
    )
    tbs = _secuencia(
        _der(0xA0, _entero(2)),
        _entero(1),
        _secuencia(_der(0x06, b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x0b")),
        _nombre("CA de pruebas"),
        _secuencia(_tiempo(desde), _tiempo(hasta)),
        _nombre(comun),
        spki,
    )
    return _secuencia(
        tbs,
        _secuencia(_der(0x06, b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x0b")),
        _der(0x03, b"\x00" + b"\x00" * 64),
    )


# --- Firmar un documento ---------------------------------------------------

CUERPO = """<?xml version="1.0" encoding="UTF-8"?>
<fe:Facturae xmlns:fe="http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml">
  <FileHeader><SchemaVersion>3.2.2</SchemaVersion></FileHeader>
  <Parties><SellerParty><TaxIdentification>
    <TaxIdentificationNumber>B12345674</TaxIdentificationNumber>
  </TaxIdentification></SellerParty></Parties>
  <Invoices><Invoice>
    <InvoiceHeader><InvoiceNumber>F-001</InvoiceNumber></InvoiceHeader>
    <InvoiceIssueData><IssueDate>2026-03-02</IssueDate></InvoiceIssueData>
    <InvoiceTotals><InvoiceTotal>{total}</InvoiceTotal></InvoiceTotals>
  </Invoice></Invoices>
</fe:Facturae>"""

_URI_SHA = {
    "sha1": "http://www.w3.org/2000/09/xmldsig#sha1",
    "sha256": "http://www.w3.org/2001/04/xmlenc#sha256",
}
_URI_FIRMA = {
    "sha1": "http://www.w3.org/2000/09/xmldsig#rsa-sha1",
    "sha256": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
}
C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"


def _c14n(nodo) -> bytes:
    return etree.tostring(nodo, method="c14n", exclusive=False, with_comments=False)


def _resumen(octetos: bytes, alg: str) -> str:
    return base64.b64encode(hashlib.new(alg, octetos).digest()).decode()


def _firmar(bloque: bytes, alg: str, modulo: int, privada: int) -> bytes:
    """Firma PKCS#1 v1.5 con la clave de juguete. Aquí sí hay clave privada."""
    tamanio = (modulo.bit_length() + 7) // 8
    di = firma._DIGESTINFO[alg] + hashlib.new(alg, bloque).digest()
    relleno = b"\x00\x01" + b"\xff" * (tamanio - len(di) - 3) + b"\x00" + di
    return pow(int.from_bytes(relleno, "big"), privada, modulo).to_bytes(tamanio, "big")


def documento(
    total="121.00",
    alg="sha256",
    cert=None,
    firmado_el=None,
    modulo=N,
    privada=D,
    c14n=C14N,
    transformada="http://www.w3.org/2000/09/xmldsig#enveloped-signature",
    con_xades=True,
) -> bytes:
    """Un Facturae firmado de verdad, con los tornillos accesibles."""
    cert = certificado() if cert is None else cert
    firmado_el = firmado_el or HOY
    raiz = etree.fromstring(CUERPO.format(total=total).encode())

    # 1. El resumen del documento, calculado **antes** de meterle la firma:
    #    es lo mismo que quitarla después, que es lo que hace el verificador.
    resumen_doc = _resumen(_c14n(raiz), alg)

    ds = lambda n: f"{{{NS_DS}}}{n}"  # noqa: E731
    xa = lambda n: f"{{{NS_XADES}}}{n}"  # noqa: E731

    firma_el = etree.SubElement(raiz, ds("Signature"), Id="Sig1")
    objeto = None
    resumen_props = None
    if con_xades:
        objeto = etree.SubElement(firma_el, ds("Object"))
        cualificadas = etree.SubElement(objeto, xa("QualifyingProperties"), Target="#Sig1")
        firmadas = etree.SubElement(
            cualificadas, xa("SignedProperties"), Id="SignedProps"
        )
        de_la_firma = etree.SubElement(firmadas, xa("SignedSignatureProperties"))
        etree.SubElement(de_la_firma, xa("SigningTime")).text = firmado_el.isoformat()
        certificados = etree.SubElement(de_la_firma, xa("SigningCertificate"))
        uno = etree.SubElement(certificados, xa("Cert"))
        resumen_cert = etree.SubElement(uno, xa("CertDigest"))
        etree.SubElement(resumen_cert, ds("DigestMethod")).set("Algorithm", _URI_SHA[alg])
        etree.SubElement(resumen_cert, ds("DigestValue")).text = _resumen(cert, alg)
        resumen_props = _resumen(_c14n(firmadas), alg)

    # 2. El SignedInfo, que es lo que se firma de verdad.
    firmado = etree.SubElement(firma_el, ds("SignedInfo"))
    etree.SubElement(firmado, ds("CanonicalizationMethod")).set("Algorithm", c14n)
    etree.SubElement(firmado, ds("SignatureMethod")).set("Algorithm", _URI_FIRMA[alg])

    def referencia(uri, resumen, tipo=None, transformar=None):
        ref = etree.SubElement(firmado, ds("Reference"), URI=uri)
        if tipo:
            ref.set("Type", tipo)
        if transformar:
            trs = etree.SubElement(ref, ds("Transforms"))
            etree.SubElement(trs, ds("Transform")).set("Algorithm", transformar)
        etree.SubElement(ref, ds("DigestMethod")).set("Algorithm", _URI_SHA[alg])
        etree.SubElement(ref, ds("DigestValue")).text = resumen

    referencia("", resumen_doc, transformar=transformada)
    if resumen_props is not None:
        referencia(
            "#SignedProps",
            resumen_props,
            tipo="http://uri.etsi.org/01903#SignedProperties",
        )

    valor = _firmar(_c14n(firmado), alg, modulo, privada)
    etree.SubElement(firma_el, ds("SignatureValue")).text = base64.b64encode(
        valor
    ).decode()
    info = etree.SubElement(firma_el, ds("KeyInfo"))
    datos = etree.SubElement(info, ds("X509Data"))
    etree.SubElement(datos, ds("X509Certificate")).text = base64.b64encode(cert).decode()
    if objeto is not None:
        firma_el.append(objeto)  # el Object va al final, después del KeyInfo
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def quejas(datos: bytes):
    raiz = etree.fromstring(datos, parser=parser())
    return firma.reglas(raiz, detectar(datos))


def codigos(incidencias, gravedad=None) -> set[str]:
    return {i.codigo for i in incidencias if gravedad is None or i.gravedad == gravedad}


# --- El punto de partida ---------------------------------------------------


class TestUnaFirmaBuena:
    def test_no_recibe_ninguna_queja_de_fondo(self):
        # Si esto falla, ninguna otra prueba de este fichero significa nada.
        #
        # El único aviso que queda es el del tamaño de la clave, y es correcto:
        # la de juguete es de 512 bits. Se comprueba que sea **ese** y no otro,
        # porque «hay un aviso» es justo lo que diría un fallo de verdad.
        salen = quejas(documento())
        assert codigos(salen, ERROR) == set()
        assert [i.codigo for i in salen] == ["FIRMA-DEBIL"]
        assert "512 bits" in salen[0].encontrado

    def test_el_documento_sigue_siendo_valido_xml(self):
        raiz = etree.fromstring(documento())
        assert raiz.xpath("//*[local-name()='InvoiceTotal']")[0].text == "121.00"


# --- Integridad: ¿lo han tocado? -------------------------------------------


class TestSiLoHanTocado:
    """La comprobación que más vale, y la que no necesita ninguna clave."""

    def test_un_importe_cambiado_despues_de_firmar(self):
        bueno = documento(total="121.00")
        roto = bueno.replace(b"<InvoiceTotal>121.00", b"<InvoiceTotal>999.00")
        assert roto != bueno
        salta = [i for i in quejas(roto) if i.codigo == "FIRMA-ALTERADA"]
        assert salta and salta[0].gravedad == ERROR
        assert "modificado después de firmarlo" in salta[0].mensaje

    def test_hasta_un_espacio_de_mas(self):
        """Un resumen criptográfico no perdona ni un byte, y eso es lo suyo:
        una herramienta que vuelva a guardar el XML rompe la firma aunque no
        cambie ni un número, y quien lo envía tiene que enterarse."""
        roto = documento().replace(b"<InvoiceTotal>", b"<InvoiceTotal> ", 1)
        assert "FIRMA-ALTERADA" in codigos(quejas(roto), ERROR)

    def test_la_queja_dice_que_referencia_ha_fallado(self):
        roto = documento().replace(b"<InvoiceTotal>121.00", b"<InvoiceTotal>999.00")
        salta = [i for i in quejas(roto) if i.codigo == "FIRMA-ALTERADA"][0]
        assert "referencia 1" in salta.campo

    def test_una_firma_que_no_cubre_nada(self):
        """Una firma sin referencias está puesta y no garantiza nada. Callarse
        ahí sería lo peor: el documento parece firmado y no lo está."""
        entero = documento()
        raiz = etree.fromstring(entero)
        for ref in raiz.xpath("//*[local-name()='Reference']"):
            ref.getparent().remove(ref)
        assert "FIRMA-VACIA" in codigos(quejas(etree.tostring(raiz)), ERROR)


# --- La firma en sí --------------------------------------------------------


class TestLaFirmaEnSi:
    def test_una_firma_manipulada(self):
        raiz = etree.fromstring(documento())
        valor = raiz.xpath("//*[local-name()='SignatureValue']")[0]
        crudo = bytearray(base64.b64decode(valor.text))
        crudo[10] ^= 0xFF
        valor.text = base64.b64encode(bytes(crudo)).decode()
        salta = [i for i in quejas(etree.tostring(raiz)) if i.codigo == "FIRMA-NO-CUADRA"]
        assert salta and salta[0].gravedad == ERROR

    def test_firmada_con_otra_clave(self):
        """El documento está entero y la firma es una firma de verdad, pero de
        otra clave. Solo lo caza la verificación RSA."""
        roto = documento(modulo=N2, privada=pow(E, -1, (P2 - 1) * (Q2 - 1)))
        # El certificado que se enseña sigue siendo el de la clave buena.
        raiz = etree.fromstring(roto)
        raiz.xpath("//*[local-name()='X509Certificate']")[0].text = base64.b64encode(
            certificado()
        ).decode()
        salta = codigos(quejas(etree.tostring(raiz)), ERROR)
        assert "FIRMA-NO-CUADRA" in salta

    def test_el_certificado_cambiado_por_otro(self):
        """XAdES guarda el resumen del certificado con el que se firmó, y esa
        propiedad va dentro de lo firmado. Sustituirlo se nota."""
        raiz = etree.fromstring(documento())
        raiz.xpath("//*[local-name()='X509Certificate']")[0].text = base64.b64encode(
            certificado(modulo=N2, comun="Otro SL")
        ).decode()
        salta = codigos(quejas(etree.tostring(raiz)), ERROR)
        assert "FIRMA-OTRO-CERTIFICADO" in salta

    def test_sin_certificado_no_se_calla(self):
        raiz = etree.fromstring(documento())
        nodo = raiz.xpath("//*[local-name()='X509Data']")[0]
        nodo.getparent().remove(nodo)
        salta = [i for i in quejas(etree.tostring(raiz)) if i.codigo == "FIRMA-SIN-CERTIFICADO"]
        assert salta and salta[0].gravedad == AVISO

    def test_un_certificado_ilegible_tampoco(self):
        raiz = etree.fromstring(documento())
        raiz.xpath("//*[local-name()='X509Certificate']")[0].text = "esto no es DER"
        assert "FIRMA-SIN-COMPROBAR" in codigos(quejas(etree.tostring(raiz)), AVISO)


# --- Falsificar el relleno de PKCS#1 ---------------------------------------


class TestRellenoFalsificado:
    """El fallo con nombre propio de PKCS#1 v1.5.

    La forma «natural» de verificar es abrir el bloque descifrado, saltarse los
    bytes de relleno y leer el resumen de dentro. Escrito así, un lector
    permisivo acepta bloques con el relleno corto y basura detrás —y con eso se
    fabrican firmas falsas sin tener la clave privada—. Es el fallo de
    Bleichenbacher de 2006, que volvió en 2014 como «BERserk».

    Aquí el bloque se reconstruye entero y se comparan los bytes, así que no
    hay nada que interpretar. Estas pruebas lo demuestran: con la clave privada
    de juguete se fabrican bloques mal formados y ninguno pasa.
    """

    @staticmethod
    def con_bloque(bloque: bytes) -> bool:
        """¿Acepta el verificador una firma que descifra a este bloque?"""
        cert = firma.leer_certificado(certificado())
        tamanio = (N.bit_length() + 7) // 8
        valor = pow(int.from_bytes(bloque, "big"), D, N).to_bytes(tamanio, "big")
        return firma._verificar_rsa(valor, b"mensaje", cert, "sha256")

    def _partes(self):
        tamanio = (N.bit_length() + 7) // 8
        di = firma._DIGESTINFO["sha256"] + hashlib.sha256(b"mensaje").digest()
        return tamanio, di

    def test_el_bloque_correcto_si_pasa(self):
        tamanio, di = self._partes()
        bueno = b"\x00\x01" + b"\xff" * (tamanio - len(di) - 3) + b"\x00" + di
        assert self.con_bloque(bueno)

    def test_relleno_corto_con_basura_detras(self):
        """El ataque clásico: 00 01 FF 00 <DigestInfo> <lo que sea>."""
        tamanio, di = self._partes()
        falso = b"\x00\x01\xff\x00" + di
        falso += b"\x42" * (tamanio - len(falso))
        assert not self.con_bloque(falso)

    def test_sin_el_byte_separador(self):
        tamanio, di = self._partes()
        falso = b"\x00\x01" + b"\xff" * (tamanio - len(di) - 2) + di
        assert not self.con_bloque(falso)

    def test_con_el_resumen_de_otro_mensaje(self):
        tamanio = (N.bit_length() + 7) // 8
        di = firma._DIGESTINFO["sha256"] + hashlib.sha256(b"otro").digest()
        falso = b"\x00\x01" + b"\xff" * (tamanio - len(di) - 3) + b"\x00" + di
        assert not self.con_bloque(falso)

    def test_con_el_digestinfo_de_otro_algoritmo(self):
        tamanio = (N.bit_length() + 7) // 8
        di = firma._DIGESTINFO["sha1"] + hashlib.sha1(b"mensaje").digest()
        falso = b"\x00\x01" + b"\xff" * (tamanio - len(di) - 3) + b"\x00" + di
        assert not self.con_bloque(falso)

    def test_una_firma_del_tamanio_equivocado(self):
        cert = firma.leer_certificado(certificado())
        assert not firma._verificar_rsa(b"\x01\x02\x03", b"mensaje", cert, "sha256")


# --- El certificado --------------------------------------------------------


class TestQueClaseDeClave:
    """Que un certificado que no sabemos usar no se confunda con uno roto.

    Este validador solo verifica RSA, y eso está bien dicho. Lo que estaba mal
    era **cómo** lo decía: al intentar leer el punto de una curva elíptica como
    si fuera una pareja de enteros salía «DER truncado», que es una acusación
    falsa contra un fichero perfectamente válido. No es una distinción
    académica: 46 de las 129 autoridades cualificadas concedidas de la lista
    de confianza española usan curva elíptica.
    """

    def _con_clave(self, oid_alg, oid_curva=None):
        alg = [_der(0x06, oid_alg)]
        alg.append(_der(0x06, oid_curva) if oid_curva else _der(0x05, b""))
        spki = _secuencia(_secuencia(*alg), _der(0x03, b"\x00\x04" + bytes(64)))
        return certificado(spki=spki)

    def test_una_curva_que_no_conocemos_se_dice_por_su_nombre(self):
        # P-256 y P-384 sí se leen ahora —ver `test_curva.py`—; lo que queda
        # fuera son las curvas que no están en la tabla. El mensaje tiene que
        # decir eso y no acusar al fichero de estar roto.
        crudo = self._con_clave(
            b"\x2a\x86\x48\xce\x3d\x02\x01",  # id-ecPublicKey
            b"\x2b\x81\x04\x00\x21",  # secp224r1, que no soportamos
        )
        with pytest.raises(firma.ClaveNoSoportada) as fallo:
            firma.leer_certificado(crudo)
        assert "curva que aquí no se conoce" in str(fallo.value)
        assert "truncado" not in str(fallo.value)

    def test_una_clave_de_curva_comprimida(self):
        # Legal y no la sabemos descomprimir. No hay ninguna en circulación
        # —los 63 de la lista española van sin comprimir— así que se dice en
        # vez de escribir código que nadie ejerce.
        spki = _secuencia(
            _secuencia(_der(0x06, b"\x2a\x86\x48\xce\x3d\x02\x01"),
                       _der(0x06, b"\x2a\x86\x48\xce\x3d\x03\x01\x07")),
            _der(0x03, b"\x00\x02" + bytes(32)),
        )
        with pytest.raises(firma.ClaveNoSoportada, match="comprimida"):
            firma.leer_certificado(certificado(spki=spki))

    def test_ed25519_tambien(self):
        with pytest.raises(firma.ClaveNoSoportada, match="Ed25519"):
            firma.leer_certificado(self._con_clave(b"\x2b\x65\x70"))

    def test_una_clave_desconocida_dice_su_oid(self):
        with pytest.raises(firma.ClaveNoSoportada, match="no es RSA"):
            firma.leer_certificado(self._con_clave(b"\x2a\x03\x04"))

    def test_se_puede_distinguir_de_un_fichero_roto(self):
        # Hereda de ValueError para no romper a quien ya lo capturaba, y es
        # una clase aparte para poder decir cosas distintas.
        assert issubclass(firma.ClaveNoSoportada, ValueError)
        with pytest.raises(ValueError) as fallo:
            firma.leer_certificado(certificado()[:-40])
        assert not isinstance(fallo.value, firma.ClaveNoSoportada)

    def test_una_rsa_normal_sigue_leyendose(self):
        cert = firma.leer_certificado(certificado())
        assert cert.bits == N.bit_length()


class TestElCertificado:
    def test_caducado_al_firmar(self):
        viejo = certificado(
            desde=HOY - timedelta(days=800), hasta=HOY - timedelta(days=30)
        )
        salta = [i for i in quejas(documento(cert=viejo)) if i.codigo == "FIRMA-CADUCADA"]
        assert salta and salta[0].gravedad == ERROR
        assert "no estaba vigente" in salta[0].mensaje

    def test_todavia_no_valido_al_firmar(self):
        futuro = certificado(
            desde=HOY + timedelta(days=30), hasta=HOY + timedelta(days=800)
        )
        assert "FIRMA-CADUCADA" in codigos(quejas(documento(cert=futuro)), ERROR)

    def test_la_queja_dice_de_quien_es_el_certificado(self):
        viejo = certificado(
            desde=HOY - timedelta(days=800),
            hasta=HOY - timedelta(days=30),
            comun="Talleres Paco SL",
        )
        salta = [i for i in quejas(documento(cert=viejo)) if i.codigo == "FIRMA-CADUCADA"][0]
        assert "Talleres Paco SL" in salta.mensaje

    def test_se_leen_las_fechas_y_el_nombre(self):
        cert = firma.leer_certificado(certificado(comun="Pruebas SL"))
        assert cert.sujeto == "Pruebas SL"
        assert cert.exponente == E and cert.modulo == N
        assert cert.desde < HOY < cert.hasta


# --- Algoritmos ------------------------------------------------------------


class TestAlgoritmos:
    def test_sha1_avisa_pero_no_es_error(self):
        """La firma puede ser auténtica; el algoritmo ya no da garantías. Que
        media Administración española tenga facturas antiguas firmadas con
        SHA-1 no las convierte en falsas."""
        salta = [i for i in quejas(documento(alg="sha1")) if i.codigo == "FIRMA-DEBIL"]
        assert salta and all(i.gravedad == AVISO for i in salta)
        assert any("SHA-1" in i.mensaje for i in salta)

    def test_y_aun_asi_la_verifica(self):
        assert "FIRMA-NO-CUADRA" not in codigos(quejas(documento(alg="sha1")))
        assert "FIRMA-ALTERADA" not in codigos(quejas(documento(alg="sha1")))

    def test_una_clave_corta_avisa(self):
        salta = [i for i in quejas(documento()) if i.codigo == "FIRMA-DEBIL"]
        assert salta and "512 bits" in salta[0].encontrado

    def test_una_canonicalizacion_que_no_sabemos_hacer(self):
        """C14N 1.1 existe y lxml no la hace. Coger la de al lado daría un
        resultado que no significa nada, así que se dice."""
        raiz = etree.fromstring(documento())
        metodo = raiz.xpath("//*[local-name()='CanonicalizationMethod']")[0]
        metodo.set("Algorithm", "http://www.w3.org/2006/12/xml-c14n11")
        salta = [
            i
            for i in quejas(etree.tostring(raiz))
            if i.codigo == "FIRMA-SIN-COMPROBAR"
        ]
        assert salta and salta[0].gravedad == AVISO

    def test_una_transformada_que_no_sabemos_aplicar(self):
        roto = documento(transformada="http://www.w3.org/TR/1999/REC-xslt-19991116")
        salta = [i for i in quejas(roto) if i.codigo == "FIRMA-SIN-COMPROBAR"]
        assert salta and "transformación" in salta[0].mensaje

    def test_no_se_da_por_buena_la_que_no_se_ha_comprobado(self):
        """Lo importante del caso anterior: al no poder comprobar la
        referencia, **no** sale FIRMA-ALTERADA ni tampoco silencio."""
        roto = documento(transformada="http://www.w3.org/TR/1999/REC-xslt-19991116")
        assert "FIRMA-ALTERADA" not in codigos(quejas(roto))
        assert quejas(roto) != []


# --- Qué documentos llevan firma -------------------------------------------


class TestAQuienSeLePide:
    def test_un_facturae_sin_firmar_avisa(self):
        salta = [
            i
            for i in quejas(CUERPO.format(total="121.00").encode())
            if i.codigo == "FIRMA-FALTA"
        ]
        assert salta and salta[0].gravedad == AVISO
        assert "válida legalmente frente a terceros" in salta[0].mensaje

    def test_un_ubl_sin_firmar_no(self):
        """En UBL y CII la firma no es parte del formato: se firma por fuera,
        en el sobre del envío. Pedirla aquí sería inventarse un requisito."""
        ubl = (
            '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">'
            "</Invoice>"
        )
        assert quejas(ubl.encode()) == []

    def test_una_firma_sin_propiedades_xades(self):
        salta = [i for i in quejas(documento(con_xades=False)) if i.codigo == "FIRMA-NO-XADES"]
        assert salta and salta[0].gravedad == AVISO

    def test_pero_la_verifica_igual(self):
        sin_xades = codigos(quejas(documento(con_xades=False)))
        assert "FIRMA-ALTERADA" not in sin_xades
        assert "FIRMA-NO-CUADRA" not in sin_xades


# --- En el orquestador -----------------------------------------------------


class TestEnElOrquestador:
    def test_una_factura_manipulada_no_es_conforme(self):
        roto = documento(total="121.00").replace(
            b"<InvoiceTotal>121.00", b"<InvoiceTotal>999.00"
        )
        informe = factura.validar(roto)
        assert "FIRMA-ALTERADA" in {i.codigo for i in informe.errores}
        assert not informe.conforme

    def test_la_queja_dice_de_donde_sale(self):
        roto = documento().replace(b"<InvoiceTotal>121.00", b"<InvoiceTotal>999.00")
        salta = [
            i for i in factura.validar(roto).incidencias if i.codigo == "FIRMA-ALTERADA"
        ][0]
        assert factura.origen(salta) == factura.SELLO


# --- El ejemplo que sí se versiona -----------------------------------------

EJEMPLO = Path(__file__).resolve().parent.parent / "ejemplos" / "fe-0001.xml"


class TestElEjemploFirmado:
    """`ejemplos/fe-0001.xml` va en el repositorio y lo usa la página.

    Su firma se rompe con tocarle un byte, y quien lo edite para cambiar un
    importe no tiene por qué acordarse de volver a firmarlo. Sin esta prueba se
    quedaría en el repositorio un ejemplo que el propio validador denuncia como
    manipulado —y nadie se enteraría hasta enseñarlo—.
    """

    @pytest.mark.skipif(not EJEMPLO.exists(), reason="no está el ejemplo")
    def test_sigue_verificando(self):
        salen = quejas(EJEMPLO.read_bytes())
        assert codigos(salen, ERROR) == set(), [i.texto() for i in salen]

    @pytest.mark.skipif(not EJEMPLO.exists(), reason="no está el ejemplo")
    def test_y_la_prueba_distingue(self):
        # Que la de arriba no pase por no mirar nada.
        roto = EJEMPLO.read_bytes().replace(
            b"<InvoiceTotal>121.00", b"<InvoiceTotal>121.01"
        )
        assert "FIRMA-ALTERADA" in codigos(quejas(roto), ERROR)

    @pytest.mark.skipif(not EJEMPLO.exists(), reason="no está el ejemplo")
    def test_y_es_una_factura_correcta_ademas(self):
        # Un ejemplo que se enseña tiene que estar bien entero, no solo firmado.
        informe = factura.validar_archivo(EJEMPLO)
        assert informe.validado and informe.conforme, informe.detalle()
