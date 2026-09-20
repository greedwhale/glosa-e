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

from validador import cadena, factura, firma
from validador.cadena import Almacen
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


# Los bits de keyUsage en el orden de X.509, para poder construir uno.
_ORDEN_DE_USOS = (
    "firma",  # 0 digitalSignature
    "no_repudio",  # 1 contentCommitment
    "cifrar_clave",
    "cifrar_datos",
    "acuerdo_clave",
    "firmar_certificados",
    "firmar_crl",
)


def _key_usage(*cuales: str) -> bytes:
    numero = 0
    for nombre in cuales:
        numero |= 1 << (7 - _ORDEN_DE_USOS.index(nombre))
    return _secuencia(
        _der(0x06, b"\x55\x1d\x0f"),
        _der(0x01, b"\xff"),
        _der(0x04, _der(0x03, bytes([0, numero]))),
    )


def certificado(
    modulo: int = N,
    exponente: int = E,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    comun: str = "Pruebas SL",
    spki: bytes | None = None,
    usos: tuple[str, ...] | None = None,
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
        # Sin `usos` no va ninguna extensión, que es como estaba: keyUsage es
        # opcional en X.509 y no ponerla significa «sin restricción».
        _der(0xA3, _secuencia(_key_usage(*usos))) if usos else b"",
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


class TestParaQueSirveElCertificado:
    """`keyUsage` dice para qué se emitió el certificado, y no se miraba.

    Lo encontró la auditoría del 15-09-2026 junto al agujero de la cadena: se
    comprobaba el keyUsage del que **emite** certificados y no el del que
    **firma** el documento. Un certificado de cifrado o de autenticación en
    web firmaba una factura y no lo decía nadie.
    """

    def test_el_que_no_sirve_para_firmar_lo_dice(self):
        der = certificado(usos=("cifrar_clave",))
        salen = quejas(documento(cert=der))
        cual = [i for i in salen if i.codigo == "FIRMA-USO-NO-PERMITIDO"]
        assert cual, codigos(salen)
        assert cual[0].gravedad == AVISO
        assert cual[0].encontrado == "cifrar_clave"

    def test_y_la_firma_sigue_cuadrando(self):
        """Es un aviso, no un error: lo que falla es para qué vale.

        Si esto saliera como error, una firma perfectamente auténtica quedaría
        marcada como rota, que es justo lo contrario de lo que pasa.
        """
        der = certificado(usos=("cifrar_clave",))
        salen = quejas(documento(cert=der))
        assert not [i for i in salen if i.codigo.startswith("FIRMA-NO-")]
        assert "FIRMA-ALTERADA" not in codigos(salen)

    def test_el_que_si_sirve_no_se_queja(self):
        for uso in ("firma", "no_repudio"):
            der = certificado(usos=(uso, "cifrar_clave"))
            assert "FIRMA-USO-NO-PERMITIDO" not in codigos(quejas(documento(cert=der)))

    def test_el_que_no_declara_usos_tampoco(self):
        """Ausente no es «para nada», es «sin restricción».

        Es el caso normal: de 38 certificados de facturas de verdad, dos no
        declaran usos. Quejarse de ellos sería inventar un problema.
        """
        assert "FIRMA-USO-NO-PERMITIDO" not in codigos(quejas(documento()))


class TestUnaFirmaSinSignedInfo:
    """Sin `SignedInfo` no hay nada que verificar, y eso tiene que decirse.

    La auditoría lo encontró callado: en una instalación sin esquemas —la de
    la consola recién clonada, y la de la página antes del paquete— no salía
    ningún FIRMA-*, o sea que un documento con un bloque de firma vacío se leía
    igual que uno sin firma. Con esquemas lo caza el XSD, pero no se puede
    depender de que estén.

    Quedó cerrado al arreglar los tres puntos críticos del 16-09-2026. La
    prueba está aquí para que no vuelva a abrirse sin que nadie se entere.
    """

    def sin_signedinfo(self) -> bytes:
        datos = documento()
        raiz = etree.fromstring(datos)
        firmado = raiz.find(f".//{{{NS_DS}}}SignedInfo")
        assert firmado is not None, "el documento de prueba ya no trae SignedInfo"
        firmado.getparent().remove(firmado)
        return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")

    def test_no_pasa_en_silencio(self):
        salen = codigos(quejas(self.sin_signedinfo()))
        assert [c for c in salen if c.startswith("FIRMA-")], salen

    def test_y_el_documento_no_se_da_por_firmado(self):
        from validador import factura

        informe = factura.validar(self.sin_signedinfo())
        assert "· firmado" not in informe.resumen(), informe.resumen()


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


# --- Firmas que no son de quien dicen, o no de lo que dicen ----------------
#
# Las tres maniobras de la auditoría del 15-09-2026. Ninguna necesita la clave
# privada de nadie: basta con el certificado de la víctima, que viaja en cada
# factura que firma, o con una firma suya sobre cualquier otra cosa. Las tres
# salían «sin errores» y con la nota que nombra al firmante.

ENV = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
EXC = "http://www.w3.org/2001/10/xml-exc-c14n#"


def _ds(nombre):
    return f"{{{NS_DS}}}{nombre}"


def _xa(nombre):
    return f"{{{NS_XADES}}}{nombre}"


def con_ancla(tmp_path, der=None) -> Almacen:
    """Un almacén con el certificado de juguete puesto de ancla.

    Con él la cadena llega y sale la nota que dice de quién es la firma: es la
    nota que no puede salir sobre una firma que no se ha verificado.
    """
    carpeta = tmp_path / "anclas"
    carpeta.mkdir(exist_ok=True)
    (carpeta / "juguete.cer").write_bytes(der or certificado())
    return Almacen(carpeta)


def declaraciones_de_confianza(datos: bytes, almacen: Almacen) -> list:
    raiz = etree.fromstring(datos, parser=parser())
    return [
        i
        for i in cadena.reglas_de_documento(raiz, detectar(datos), almacen)
        if i.codigo == "CONFIANZA-ANCLA"
    ]


def _resumen_del_documento(raiz) -> str:
    """Lo que un falsificador puede recalcular sin clave: un resumen es un hash."""
    copia = etree.fromstring(etree.tostring(raiz))
    for una in copia.xpath("//*[local-name()='Signature']"):
        una.getparent().remove(una)
    return _resumen(_c14n(copia), "sha256")


def falsificada(total="999.00", metodo="urn:un-algoritmo-inventado") -> bytes:
    """Una factura inventada con el certificado de la víctima y sin su clave.

    El resumen del documento se rehace, que es solo un hash; el valor de la
    firma no se puede rehacer, así que se pone basura y un método de firma que
    no existe para que nadie intente comprobarla.
    """
    raiz = etree.fromstring(documento().replace(b"121.00", total.encode()))
    raiz.xpath("//*[local-name()='Reference'][@URI='']/*[local-name()='DigestValue']")[
        0
    ].text = _resumen_del_documento(raiz)
    raiz.xpath("//*[local-name()='SignatureMethod']")[0].set("Algorithm", metodo)
    valor = raiz.xpath("//*[local-name()='SignatureValue']")[0]
    valor.text = base64.b64encode(b"\x01" * ((N.bit_length() + 7) // 8)).decode()
    return etree.tostring(raiz)


def firma_sobre_otra_cosa():
    """Una firma auténtica de la clave de juguete sobre un acuse de recibo.

    Referencia por identificador y canonicalización exclusiva, que es lo que
    permite despegarla de su documento y pegarla en otro sin que deje de
    verificar. Firmas así las produce cualquier herramienta de firma.
    """
    otro = etree.fromstring(b'<Acuse><Texto Id="acuse">Recibido</Texto></Acuse>')
    texto = otro[0]
    exc = lambda n: etree.tostring(n, method="c14n", exclusive=True)  # noqa: E731
    firma_el = etree.SubElement(otro, _ds("Signature"), Id="SigAcuse")
    firmado = etree.SubElement(firma_el, _ds("SignedInfo"))
    etree.SubElement(firmado, _ds("CanonicalizationMethod")).set("Algorithm", EXC)
    etree.SubElement(firmado, _ds("SignatureMethod")).set("Algorithm", _URI_FIRMA["sha256"])
    ref = etree.SubElement(firmado, _ds("Reference"), URI="#acuse")
    etree.SubElement(etree.SubElement(ref, _ds("Transforms")), _ds("Transform")).set(
        "Algorithm", EXC
    )
    etree.SubElement(ref, _ds("DigestMethod")).set("Algorithm", _URI_SHA["sha256"])
    etree.SubElement(ref, _ds("DigestValue")).text = _resumen(exc(texto), "sha256")
    etree.SubElement(firma_el, _ds("SignatureValue")).text = base64.b64encode(
        _firmar(exc(firmado), "sha256", N, D)
    ).decode()
    datos = etree.SubElement(etree.SubElement(firma_el, _ds("KeyInfo")), _ds("X509Data"))
    etree.SubElement(datos, _ds("X509Certificate")).text = base64.b64encode(
        certificado()
    ).decode()
    return firma_el, texto


def trasplantada(total="999.00") -> bytes:
    """Una factura del atacante con la firma del acuse colgada dentro."""
    raiz = etree.fromstring(CUERPO.format(total=total).encode())
    firma_el, texto = firma_sobre_otra_cosa()
    robada = etree.fromstring(etree.tostring(firma_el))
    etree.SubElement(robada, _ds("Object")).append(etree.fromstring(etree.tostring(texto)))
    raiz.append(robada)
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def envolvente(total="121.00") -> bytes:
    """Un Facturae firmado en modo envolvente: la raíz es la firma.

    La factura va dentro de un `ds:Object` con identificador, y la firma cubre
    ese objeto. Es el modo legítimo en que la firma no cubre la raíz.
    """
    firma_el = etree.Element(_ds("Signature"), Id="Sig1", nsmap={"ds": NS_DS})
    firmado = etree.SubElement(firma_el, _ds("SignedInfo"))
    etree.SubElement(firmado, _ds("CanonicalizationMethod")).set("Algorithm", C14N)
    etree.SubElement(firmado, _ds("SignatureMethod")).set("Algorithm", _URI_FIRMA["sha256"])
    ref = etree.SubElement(firmado, _ds("Reference"), URI="#CONTENT")
    etree.SubElement(etree.SubElement(ref, _ds("Transforms")), _ds("Transform")).set(
        "Algorithm", C14N
    )
    etree.SubElement(ref, _ds("DigestMethod")).set("Algorithm", _URI_SHA["sha256"])
    resumen = etree.SubElement(ref, _ds("DigestValue"))
    valor = etree.SubElement(firma_el, _ds("SignatureValue"))
    datos = etree.SubElement(etree.SubElement(firma_el, _ds("KeyInfo")), _ds("X509Data"))
    etree.SubElement(datos, _ds("X509Certificate")).text = base64.b64encode(
        certificado()
    ).decode()
    objeto = etree.SubElement(firma_el, _ds("Object"), Id="CONTENT")
    objeto.append(etree.fromstring(CUERPO.format(total=total).encode()))
    resumen.text = _resumen(_c14n(objeto), "sha256")
    valor.text = base64.b64encode(_firmar(_c14n(firmado), "sha256", N, D)).decode()
    return etree.tostring(firma_el, xml_declaration=True, encoding="UTF-8")


def con_objeto_delante(datos: bytes, contenido) -> bytes:
    """Mete un `ds:Object` sin firmar justo después del `KeyInfo`.

    Es decir, **delante** del objeto de verdad: quien lea «el primero que
    aparezca» se queda con el del atacante. Nada de lo firmado cambia.
    """
    raiz = etree.fromstring(datos)
    info = raiz.xpath("//*[local-name()='KeyInfo']")[0]
    objeto = etree.Element(_ds("Object"))
    objeto.append(contenido)
    info.addnext(objeto)
    return etree.tostring(raiz)


def propiedades_falsas(firmado_el=None, cert=None):
    """Unas propiedades XAdES con la pinta de las buenas y sin firmar."""
    cualificadas = etree.Element(_xa("QualifyingProperties"), Target="#Sig1")
    firmadas = etree.SubElement(cualificadas, _xa("SignedProperties"), Id="Falsas")
    de_la_firma = etree.SubElement(firmadas, _xa("SignedSignatureProperties"))
    if firmado_el is not None:
        etree.SubElement(de_la_firma, _xa("SigningTime")).text = firmado_el.isoformat()
    if cert is not None:
        resumen = etree.SubElement(
            etree.SubElement(etree.SubElement(de_la_firma, _xa("SigningCertificate")),
                             _xa("Cert")),
            _xa("CertDigest"),
        )
        etree.SubElement(resumen, _ds("DigestMethod")).set("Algorithm", _URI_SHA["sha256"])
        etree.SubElement(resumen, _ds("DigestValue")).text = _resumen(cert, "sha256")
    return cualificadas


class TestUnaFirmaQueNoSeHaVerificadoNoNombraANadie:
    """1. La falsificación sin clave.

    Con un método de firma que no se conoce, el valor no se comprueba y sale un
    aviso. Hasta aquí bien. Lo que estaba mal es que `cadena.py` seguía adelante
    por su cuenta y escribía «La firma de «Pruebas SL» llega a …»: una
    declaración de autoría sobre una firma que nadie había comprobado.
    """

    def test_la_buena_si_la_nombra(self, tmp_path):
        # Sin esto, las de abajo pasarían por no mirar nada.
        assert len(declaraciones_de_confianza(documento(), con_ancla(tmp_path))) == 1

    def test_con_un_metodo_inventado_no(self, tmp_path):
        datos = falsificada()
        assert "FIRMA-SIN-COMPROBAR" in codigos(quejas(datos))
        assert declaraciones_de_confianza(datos, con_ancla(tmp_path)) == []

    def test_con_una_firma_que_no_cuadra_tampoco(self, tmp_path):
        datos = falsificada(metodo=_URI_FIRMA["sha256"])
        assert "FIRMA-NO-CUADRA" in codigos(quejas(datos), ERROR)
        assert declaraciones_de_confianza(datos, con_ancla(tmp_path)) == []

    def test_con_una_canonicalizacion_que_no_sabemos_hacer_tampoco(self, tmp_path):
        raiz = etree.fromstring(documento())
        raiz.xpath("//*[local-name()='CanonicalizationMethod']")[0].set(
            "Algorithm", "http://www.w3.org/2006/12/xml-c14n11"
        )
        datos = etree.tostring(raiz)
        assert declaraciones_de_confianza(datos, con_ancla(tmp_path)) == []

    def test_el_informe_entero_no_da_por_buena_la_falsificada(self, tmp_path):
        informe = factura.validar(falsificada(), almacen=con_ancla(tmp_path))
        assert "CONFIANZA-ANCLA" not in {i.codigo for i in informe.notas}

    def test_las_referencias_cuentan_solo_dentro_del_signedinfo(self, tmp_path):
        """Un `SignedInfo` sacado de su sitio no es un `SignedInfo`.

        Sin él no hay valor de firma que comprobar, y antes eso devolvía
        silencio: las referencias se buscaban en cualquier parte de la firma,
        verificaban contra el documento —un resumen lo rehace cualquiera— y
        el informe quedaba sin una sola queja de firma.
        """
        raiz = etree.fromstring(falsificada(metodo=_URI_FIRMA["sha256"]))
        firma_el = raiz.xpath("//*[local-name()='Signature']")[0]
        firmado = firma_el.xpath("./*[local-name()='SignedInfo']")[0]
        firma_el.remove(firmado)
        etree.SubElement(firma_el, _ds("Object")).append(firmado)
        datos = etree.tostring(raiz)
        assert codigos(quejas(datos), ERROR), [i.texto() for i in quejas(datos)]
        assert declaraciones_de_confianza(datos, con_ancla(tmp_path)) == []


class TestUnaFirmaTieneQueCubrirLaFactura:
    """2. El trasplante.

    Una firma auténtica sobre otra cosa, colgada de una factura inventada: el
    valor verifica, las referencias verifican —cubren el acuse, que viaja con
    ella— y nada exigía que alguna cubriera la factura.
    """

    def test_la_firma_trasplantada_verifica_pero_no_cubre(self, tmp_path):
        salen = quejas(trasplantada())
        assert "FIRMA-NO-CUADRA" not in codigos(salen)  # la firma es auténtica
        assert "FIRMA-ALTERADA" not in codigos(salen)  # y lo que cubre, intacto
        assert "FIRMA-NO-CUBRE" in codigos(salen, ERROR)

    def test_y_no_nombra_a_nadie(self, tmp_path):
        assert declaraciones_de_confianza(trasplantada(), con_ancla(tmp_path)) == []

    def test_una_envolvente_de_verdad_si_cubre(self, tmp_path):
        # El modo legítimo en que la referencia no es `URI=""`: la factura va
        # dentro del objeto firmado.
        datos = envolvente()
        assert detectar(datos).familia == "Facturae"
        assert codigos(quejas(datos), ERROR) == set(), [i.texto() for i in quejas(datos)]
        assert len(declaraciones_de_confianza(datos, con_ancla(tmp_path))) == 1

    def test_una_factura_de_mentira_delante_de_la_firmada(self, tmp_path):
        """El envoltorio con señuelo: la factura que se lee no es la firmada.

        Las reglas de Facturae se quedan con el primer `Facturae` que
        aparece. Metiendo uno inventado delante del objeto firmado, la firma
        sigue verificando entera y lo que se valida es el señuelo.
        """
        senuelo = etree.fromstring(CUERPO.format(total="999.00").encode())
        datos = con_objeto_delante(envolvente(), senuelo)
        primera = etree.fromstring(datos).xpath("//*[local-name()='InvoiceTotal']")[0]
        assert primera.text == "999.00"  # lo que leen las reglas es el señuelo
        assert "FIRMA-NO-CUBRE" in codigos(quejas(datos), ERROR)
        assert declaraciones_de_confianza(datos, con_ancla(tmp_path)) == []

    def test_un_identificador_repetido_no_se_resuelve_a_ciegas(self, tmp_path):
        # Dos elementos con el Id que firma la referencia: no se sabe cuál es
        # el firmado, y quedarse con el primero es exactamente la trampa.
        raiz = etree.fromstring(envolvente())
        copia = etree.fromstring(
            etree.tostring(raiz.xpath("//*[@Id='CONTENT']")[0])
        )
        raiz.append(copia)
        datos = etree.tostring(raiz)
        salen = quejas(datos)
        assert any(
            i.codigo == "FIRMA-SIN-COMPROBAR" and "2 veces" in i.mensaje for i in salen
        ), [i.texto() for i in salen]
        assert declaraciones_de_confianza(datos, con_ancla(tmp_path)) == []


class TestLoQueDeclaraLaFirmaSaleDeLoFirmado:
    """3. La fecha, el certificado declarado y las propiedades XAdES.

    Se leían con `.//*[local-name()=…]` en cualquier parte de la firma, y el
    primero que apareciera mandaba. Un `ds:Object` sin firmar, metido delante
    del de verdad, no rompe ningún resumen y decidía la fecha con la que se
    mide la caducidad y la revocación.
    """

    VIEJO = dict(desde=HOY - timedelta(days=800), hasta=HOY - timedelta(days=30))

    def test_una_fecha_sin_firmar_no_tapa_una_caducidad(self):
        datos = documento(cert=certificado(**self.VIEJO))
        assert "FIRMA-CADUCADA" in codigos(quejas(datos), ERROR)  # la de partida
        falsa = propiedades_falsas(firmado_el=HOY - timedelta(days=400))
        manipulada = con_objeto_delante(datos, falsa)
        assert "FIRMA-ALTERADA" not in codigos(quejas(manipulada))
        assert "FIRMA-CADUCADA" in codigos(quejas(manipulada), ERROR)

    def test_la_fecha_que_se_usa_es_la_firmada(self):
        falsa = propiedades_falsas(firmado_el=datetime(2001, 1, 1, tzinfo=timezone.utc))
        raiz = etree.fromstring(con_objeto_delante(documento(), falsa))
        assert firma.momento_de_firma(firma.hay_firma(raiz)[0]) == HOY

    def test_un_certificado_declarado_sin_firmar_no_tapa_la_sustitucion(self):
        otro = certificado(modulo=N2, comun="Otro SL")
        raiz = etree.fromstring(documento())
        raiz.xpath("//*[local-name()='X509Certificate']")[0].text = base64.b64encode(
            otro
        ).decode()
        manipulada = con_objeto_delante(etree.tostring(raiz), propiedades_falsas(cert=otro))
        assert "FIRMA-OTRO-CERTIFICADO" in codigos(quejas(manipulada), ERROR)

    def test_unas_propiedades_xades_sin_firmar_no_la_hacen_xades(self):
        datos = documento(con_xades=False)
        assert "FIRMA-NO-XADES" in codigos(quejas(datos))  # la de partida
        manipulada = con_objeto_delante(datos, propiedades_falsas(firmado_el=HOY))
        assert "FIRMA-NO-XADES" in codigos(quejas(manipulada), AVISO)

    def test_ni_dan_fecha(self):
        raiz = etree.fromstring(
            con_objeto_delante(documento(con_xades=False), propiedades_falsas(firmado_el=HOY))
        )
        assert firma.momento_de_firma(firma.hay_firma(raiz)[0]) is None

    def test_unas_propiedades_tocadas_no_acusan_de_nada(self):
        """Tocar la fecha dentro de lo firmado rompe su resumen, y entonces no
        se usa **para nada**: ni para dar por bueno ni para acusar. Sin
        comprobar ese resumen, una fecha que nadie ha firmado acabaría en el
        informe como un certificado caducado."""
        raiz = etree.fromstring(documento())
        tiempo = raiz.xpath("//*[local-name()='SigningTime']")[0]
        tiempo.text = (HOY - timedelta(days=800)).isoformat()
        salen = quejas(etree.tostring(raiz))
        assert "FIRMA-ALTERADA" in codigos(salen, ERROR)
        assert "FIRMA-CADUCADA" not in codigos(salen)

    def test_y_la_fecha_tocada_tampoco_se_devuelve(self):
        # Lo mismo, un piso más abajo: `momento_de_firma` es lo que usan
        # `cadena.py` y `sellos.py`, y con el resumen de las propiedades roto no
        # hay fecha firmada que devolver.
        raiz = etree.fromstring(documento())
        raiz.xpath("//*[local-name()='SigningTime']")[0].text = (
            HOY - timedelta(days=800)
        ).isoformat()
        assert firma.momento_de_firma(firma.hay_firma(raiz)[0]) is None

    def test_el_certificado_que_firma_sale_del_keyinfo(self):
        # Un certificado metido en un objeto sin firmar, delante del bloque de
        # claves, no es el certificado de la firma.
        otro = etree.Element(_ds("X509Certificate"))
        otro.text = base64.b64encode(certificado(modulo=N2, comun="Otro SL")).decode()
        raiz = etree.fromstring(documento())
        firma_el = firma.hay_firma(raiz)[0]
        objeto = etree.Element(_ds("Object"))
        objeto.append(otro)
        firma_el.xpath("./*[local-name()='SignatureValue']")[0].addnext(objeto)
        certs = firma.certificados_de(firma.hay_firma(raiz)[0])
        assert [c.sujeto for c in certs] == ["Pruebas SL"]
        assert codigos(quejas(etree.tostring(raiz)), ERROR) == set()


# --- La línea de estado ----------------------------------------------------


class TestLaLineaDeEstadoDiceEnQueQuedoLaFirma:
    """«· firmado» tiene que costar más que traer un bloque `Signature`.

    Era la última pieza del mismo fallo: el informe dejó de decir de quién es
    una firma que no ha comprobado, pero la línea de arriba seguía poniendo
    «Facturae v3.2.2 (factura) · firmado» por haber visto el bloque. Encima de
    un «sin errores», ese «firmado» es la palabra que quien lee se lleva.
    """

    def test_una_firma_buena_dice_firmado(self):
        informe = factura.validar(documento())
        assert informe.firma == "en pie"
        assert "· firmado" in informe.resumen()

    def test_una_firma_que_no_se_sabe_comprobar_no_dice_firmado(self):
        # El caso del falsificador sin clave: algoritmo inventado para que
        # nadie llegue a comprobar el valor. También el de una RSA-PSS
        # legítima, y por eso la línea dice «sin comprobar» y no «rota».
        informe = factura.validar(falsificada())
        assert informe.firma == "sin comprobar"
        assert "· firma sin comprobar" in informe.resumen()
        assert "· firmado" not in informe.resumen()

    def test_una_firma_trasplantada_dice_que_no_se_sostiene(self):
        informe = factura.validar(trasplantada())
        assert informe.firma == "rota"
        assert "· firma que no se sostiene" in informe.resumen()

    def test_un_documento_tocado_despues_de_firmarlo_tambien(self):
        roto = documento().replace(b"<InvoiceTotal>121.00", b"<InvoiceTotal>999.00")
        assert factura.validar(roto).firma == "rota"

    def test_una_firma_envolvente_legitima_sigue_diciendo_firmado(self):
        # La que no cubre la raíz porque la factura va dentro de ella. Si esta
        # sale «rota», el arreglo acusa a documentos correctos.
        assert factura.validar(envolvente()).firma == "en pie"

    def test_con_dos_firmas_manda_la_peor(self):
        # Que una cuadre no arregla que la otra no: el documento que sale de
        # aquí no está firmado, está firmado a medias.
        raiz = etree.fromstring(documento())
        robada, texto = firma_sobre_otra_cosa()
        etree.SubElement(robada, _ds("Object")).append(
            etree.fromstring(etree.tostring(texto))
        )
        raiz.append(robada)
        informe = factura.validar(etree.tostring(raiz))
        assert informe.firma == "rota"
        assert "· firmado" not in informe.resumen()

    def test_sin_firma_la_linea_no_habla_de_firmas(self):
        informe = factura.validar(CUERPO.format(total="121.00").encode())
        assert informe.firma is None
        assert "firma" not in informe.resumen()

    def test_la_deteccion_a_secas_no_dice_firmado(self):
        # `detectar` no comprueba nada: solo ve que hay un bloque de firma, y
        # eso es lo único que su línea puede decir.
        assert "· con firma" in detectar(documento()).resumen()
        assert "· firmado" not in detectar(documento()).resumen()


class TestLaFraseDelFinalNoSeApuntaLoQueNoHaMirado:
    """«Qué se ha mirado» es lo que dice cuánto vale el «sin errores».

    Con una firma que no se ha sabido comprobar, la línea del documento y su
    aviso lo decían, y esta frase —la que resume el informe entero— seguía
    diciendo «se ha comprobado que las firmas no estén rotas».
    """

    def _lote(self, tmp_path, **ficheros):
        for nombre, datos in ficheros.items():
            (tmp_path / f"{nombre}.xml").write_bytes(datos)
        return factura.validar_lote(sorted(tmp_path.iterdir()), hoy=HOY.date())

    def test_con_una_firma_sin_comprobar_no_dice_haberla_mirado(self, tmp_path):
        alcance = self._lote(tmp_path, a=falsificada()).alcance()
        assert "que las firmas no estén rotas" not in alcance

    def test_y_lo_dice_donde_dice_lo_que_no_se_mira(self, tmp_path):
        alcance = self._lote(tmp_path, a=falsificada()).alcance()
        assert "No se comprueba la firma de este documento" in alcance

    def test_con_una_firma_buena_lo_sigue_prometiendo(self, tmp_path):
        alcance = self._lote(tmp_path, a=documento()).alcance()
        assert "que las firmas no estén rotas" in alcance
        assert "su aviso dice por qué" not in alcance

    def test_una_firma_rota_si_se_ha_mirado(self, tmp_path):
        # Mirarla y que esté mal es haberla mirado: ahí la promesa se cumple,
        # y de que esté rota ya se queja el error.
        roto = documento().replace(b"<InvoiceTotal>121.00", b"<InvoiceTotal>999.00")
        alcance = self._lote(tmp_path, a=roto).alcance()
        assert "que las firmas no estén rotas" in alcance
        assert "su aviso dice por qué" not in alcance

    def test_con_una_de_cada_dice_las_dos_cosas(self, tmp_path):
        alcance = self._lote(tmp_path, a=documento(), b=falsificada()).alcance()
        assert "que las firmas no estén rotas" in alcance
        assert "la firma de uno de los documentos" in alcance

    def test_y_cuenta_cuantas_son(self, tmp_path):
        alcance = self._lote(
            tmp_path, a=falsificada(), b=falsificada(total="998.00")
        ).alcance()
        assert "la firma de 2 de los documentos" in alcance

    def test_sobre_un_lote_sin_firmas_no_habla_de_ninguna(self, tmp_path):
        alcance = self._lote(
            tmp_path, a=CUERPO.format(total="121.00").encode()
        ).alcance()
        assert "su aviso dice por qué" not in alcance
        assert "la validez de las firmas electrónicas" in alcance


def con_segunda_firma(datos: bytes, cert: bytes) -> bytes:
    """El documento con otra firma que también lo cubre entero y se sostiene.

    Va dentro del `ds:Object` de la primera y no al lado: la primera quita solo
    su propio bloque al resumir el documento, así que una firma puesta al lado
    después la rompería. Dentro, se va con ella. La segunda cubre el documento
    sin sí misma, que es el documento de antes de meterla.
    """
    raiz = etree.fromstring(datos)
    resumen_doc = _resumen(_c14n(raiz), "sha256")
    objeto = raiz.xpath("//*[local-name()='Signature']/*[local-name()='Object']")[0]
    otra = etree.SubElement(objeto, _ds("Signature"), Id="Sig2")
    firmado = etree.SubElement(otra, _ds("SignedInfo"))
    etree.SubElement(firmado, _ds("CanonicalizationMethod")).set("Algorithm", C14N)
    etree.SubElement(firmado, _ds("SignatureMethod")).set("Algorithm", _URI_FIRMA["sha256"])
    ref = etree.SubElement(firmado, _ds("Reference"), URI="")
    etree.SubElement(etree.SubElement(ref, _ds("Transforms")), _ds("Transform")).set(
        "Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
    )
    etree.SubElement(ref, _ds("DigestMethod")).set("Algorithm", _URI_SHA["sha256"])
    etree.SubElement(ref, _ds("DigestValue")).text = resumen_doc
    etree.SubElement(otra, _ds("SignatureValue")).text = base64.b64encode(
        _firmar(_c14n(firmado), "sha256", N, D)
    ).decode()
    datos_x509 = etree.SubElement(etree.SubElement(otra, _ds("KeyInfo")), _ds("X509Data"))
    etree.SubElement(datos_x509, _ds("X509Certificate")).text = base64.b64encode(cert).decode()
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


class TestLaFraseNoPrometeQueLaCadenaLlegue:
    """«se ha comprobado que ese certificado lleve a una autoridad de confianza».

    Salía también con `CADENA-DESCONOCIDA` en el informe. Es un aviso, así que
    el veredicto seguía siendo «sin errores», y la frase prometía justo lo que
    el aviso de encima negaba.
    """

    PROMESA = "que ese certificado lleve a una autoridad de confianza instalada"

    def _alcance(self, tmp_path, *documentos, listas=False):
        almacen = con_ancla(tmp_path)
        rutas = []
        for numero, datos in enumerate(documentos):
            rutas.append(tmp_path / f"{numero}.xml")
            rutas[-1].write_bytes(datos)
        lote = factura.validar_lote(rutas, hoy=HOY.date(), almacen=almacen)
        return lote.alcance(anclas=True, listas=listas)

    def _ajena(self):
        # La misma clave con otro nombre: la firma cuadra, y la cadena no llega
        # a ningún ancla, porque el ancla es el certificado de «Pruebas SL».
        return documento(cert=certificado(comun="Ajena SL"))

    def test_si_llega_lo_promete(self, tmp_path):
        alcance = self._alcance(tmp_path, documento())
        assert self.PROMESA in alcance
        assert "de quién es el certificado" not in alcance

    def test_si_no_llega_no(self, tmp_path):
        alcance = self._alcance(tmp_path, self._ajena())
        assert self.PROMESA not in alcance
        assert "de quién es el certificado de este documento" in alcance

    def test_ni_promete_mirar_la_revocacion_de_lo_que_no_llega(self, tmp_path):
        # La revocación solo se mira sobre una cadena que llega.
        alcance = self._alcance(tmp_path, self._ajena(), listas=True)
        assert "que no lo hayan anulado" not in alcance

    def test_con_una_de_cada_dice_las_dos_cosas(self, tmp_path):
        alcance = self._alcance(tmp_path, documento(), self._ajena())
        assert self.PROMESA in alcance
        assert "de quién es el certificado de uno de los documentos" in alcance

    def test_con_dos_firmas_en_un_documento_tienen_que_llegar_las_dos(self, tmp_path):
        # Una nota de confianza por firma que llega. Con que llegara una, el
        # documento entero pasaba por «llega» y la otra firma, de quien no se
        # sabe, quedaba debajo de la promesa.
        datos = con_segunda_firma(documento(), certificado(comun="Ajena SL"))
        raiz = etree.fromstring(datos)
        assert sum(e.verificada for e in firma.examinar_todas(raiz)) == 2
        alcance = self._alcance(tmp_path, datos)
        assert self.PROMESA not in alcance
        assert "de quién es el certificado de este documento" in alcance

    def test_una_firma_rota_no_cuenta_para_ninguna_de_las_dos(self, tmp_path):
        # Su cadena no se mira —de una firma que no se sostiene no se dice de
        # quién es—, y el error ya deja el veredicto donde tiene que estar.
        roto = documento().replace(b"<InvoiceTotal>121.00", b"<InvoiceTotal>999.00")
        alcance = self._alcance(tmp_path, roto)
        assert self.PROMESA not in alcance
        assert "de quién es el certificado" not in alcance


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
