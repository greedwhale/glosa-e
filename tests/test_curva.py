"""Firma con curva elíptica: ECDSA sobre P-256, P-384 y P-521.

Hacía falta por un dato, no por completitud: **46 de las 129 autoridades
cualificadas concedidas de la lista de confianza española firman con curva
elíptica**. Sin esto, un tercio de las autoridades de España se quedaba fuera
del almacén de anclas, y sus facturas salían como «no llega a ninguna autoridad
conocida» sin que el motivo real fuera ese.

Aquí hay tres clases de prueba, y las tres hacen falta:

1. **Los parámetros de las curvas.** Van escritos a mano y una errata no da un
   error: da «esta firma no verifica», que es indistinguible de una firma
   falsificada. Se comprueban con la definición —que el generador esté en la
   curva y que n·G sea el punto del infinito— usando una aritmética lenta y
   obvia escrita aquí abajo. Al escribirlos la primera vez se perdieron dos
   dígitos de la `n` de P-521 en un corte de línea, y esta comprobación es la
   que lo cazó.

2. **La aritmética rápida contra la lenta.** El módulo usa coordenadas
   jacobianas para no pagar un inverso modular por operación —P-521 pasa de
   200 ms a 33, y esto tiene que correr también dentro del navegador—. Las
   fórmulas no se leen solas, así que se contrastan contra la versión evidente.

3. **Contra `openssl`.** Es la que sale del círculo. Un verificador y un
   firmador escritos por la misma mano pueden compartir el mismo malentendido;
   `openssl` no comparte nada. Se le pide que firme y que monte una autoridad
   entera con su CRL, y se comprueba con la aritmética de este paquete.
"""

import base64
import hashlib
import random
import re
import shutil
import subprocess
from datetime import datetime, timezone

import pytest
from lxml import etree

from validador import cadena, firma, revocacion
from validador.firma import CURVAS, CURVAS_POR_NOMBRE, Certificado, verificar
from validador.revocacion import leer_lista
from test_firma import _der, certificado as cert_de_prueba

sin_openssl = pytest.mark.skipif(
    shutil.which("openssl") is None, reason="hace falta openssl"
)


# --- Una aritmética lenta, obvia y evidentemente correcta ------------------


def suma_lenta(uno, otro, p):
    """Las fórmulas del libro, en coordenadas afines y sin optimizar nada."""
    if uno is None:
        return otro
    if otro is None:
        return uno
    x1, y1 = uno
    x2, y2 = otro
    if x1 == x2 and (y1 + y2) % p == 0:
        return None
    if uno == otro:
        m = (3 * x1 * x1 - 3) * pow(2 * y1, -1, p) % p
    else:
        m = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (m * m - x1 - x2) % p
    return (x3, (m * (x1 - x3) - y1) % p)


def por_lento(k, punto, p):
    salida = None
    while k:
        if k & 1:
            salida = suma_lenta(salida, punto, p)
        punto = suma_lenta(punto, punto, p)
        k >>= 1
    return salida


TODAS = pytest.mark.parametrize(
    "curva", list(CURVAS.values()), ids=[c.nombre for c in CURVAS.values()]
)


class TestLosParametros:
    """Que las constantes escritas a mano sean las de verdad."""

    @TODAS
    def test_el_generador_esta_en_la_curva(self, curva):
        assert curva.encima(curva.gx, curva.gy)

    @TODAS
    def test_n_por_g_es_el_infinito(self, curva):
        # O sea que n es de verdad el orden del generador. Junto con la
        # anterior, esto caza cualquier errata en p, b, gx, gy o n.
        assert por_lento(curva.n, (curva.gx, curva.gy), curva.p) is None

    @TODAS
    def test_la_n_tiene_el_tamano_que_le_toca(self, curva):
        # La errata de P-521 se vio aquí antes que en ninguna parte: salía una
        # `n` de 517 bits, cuatro menos de los que debía.
        assert abs(curva.n.bit_length() - curva.p.bit_length()) <= 1

    @TODAS
    def test_los_octetos_de_una_coordenada(self, curva):
        assert curva.octetos == (curva.p.bit_length() + 7) // 8

    @TODAS
    def test_un_punto_de_fuera_no_cuela(self, curva):
        assert not curva.encima(curva.gx, curva.gy + 1)
        assert not curva.encima(curva.p, curva.gy)
        assert not curva.encima(-1, curva.gy)


class TestLaAritmeticaRapida:
    """Que las jacobianas den lo mismo que las de toda la vida."""

    @TODAS
    def test_coincide_con_la_lenta(self, curva):
        random.seed(1988)
        g = (curva.gx, curva.gy)
        for _ in range(3):
            k1 = random.randrange(1, curva.n)
            k2 = random.randrange(1, curva.n)
            otro = por_lento(random.randrange(2, curva.n), g, curva.p)
            lento = suma_lenta(
                por_lento(k1, g, curva.p), por_lento(k2, otro, curva.p), curva.p
            )
            assert firma._combinar(k1, g, k2, otro, curva.p) == lento

    @TODAS
    def test_el_infinito_sale_como_infinito(self, curva):
        # k*G + (n-k)*G = n*G = infinito. Si esto devolviera un punto, una
        # firma con r y s conjurados para llegar aquí verificaría.
        g = (curva.gx, curva.gy)
        k = curva.n // 3
        assert firma._combinar(k, g, curva.n - k, g, curva.p) is None


# --- Fuera del círculo: openssl -------------------------------------------


def _pem(datos: bytes, marca: str) -> bytes:
    patron = ("-----BEGIN %s-----(.*?)-----END %s-----" % (marca, marca)).encode()
    return base64.b64decode(re.search(patron, datos, re.S).group(1))


def _numeros_del_der(firma_der: bytes) -> tuple[int, int]:
    """(r, s) de una firma DER, con un lector escrito aparte a propósito.

    No se usa el del módulo: la gracia de estas pruebas es no darse la razón a
    uno mismo, y eso incluye no reutilizar el mismo trozo para las dos cosas.
    """
    assert firma_der[0] == 0x30
    cuerpo = firma_der[2:] if firma_der[1] < 0x80 else firma_der[3:]
    largo_r = cuerpo[1]
    r = int.from_bytes(cuerpo[2 : 2 + largo_r], "big")
    resto = cuerpo[2 + largo_r :]
    s = int.from_bytes(resto[2 : 2 + resto[1]], "big")
    return r, s


@pytest.fixture(scope="module")
def curva_de_openssl(tmp_path_factory):
    """Una clave, un certificado autofirmado y una firma, por cada curva."""
    if shutil.which("openssl") is None:
        pytest.skip("hace falta openssl")
    casa = tmp_path_factory.mktemp("curvas")
    mensaje = b"lo que se firma, que no es una factura sino un mensaje cualquiera"
    (casa / "mensaje.bin").write_bytes(mensaje)
    salida = {}
    # La última pareja es la que importa de verdad: un resumen **más largo** que
    # la curva, que obliga a recortarlo por la izquierda. Quien no lo recorte
    # verifica mal justo estas.
    for nombre, curva, alg in (
        ("p256", "prime256v1", "sha256"),
        ("p384", "secp384r1", "sha384"),
        ("p521", "secp521r1", "sha512"),
        ("p256-sha384", "prime256v1", "sha384"),
    ):
        def ossl(*orden):
            subprocess.run(["openssl", *orden], cwd=casa, capture_output=True,
                           check=True)

        ossl("ecparam", "-name", curva, "-genkey", "-noout", "-out", f"{nombre}.key")
        ossl("req", "-x509", "-new", "-key", f"{nombre}.key", "-days", "3650",
             f"-{alg}", "-subj", f"/CN=AC de curva {curva}", "-out", f"{nombre}.pem")
        ossl("dgst", f"-{alg}", "-sign", f"{nombre}.key", "-out", f"{nombre}.sig",
             "mensaje.bin")
        salida[nombre] = (
            firma.leer_certificado(
                _pem((casa / f"{nombre}.pem").read_bytes(), "CERTIFICATE")
            ),
            (casa / f"{nombre}.sig").read_bytes(),
            alg,
            mensaje,
        )
    return salida


CASOS = ["p256", "p384", "p521", "p256-sha384"]


class TestContraOpenssl:
    @pytest.mark.parametrize("cual", CASOS)
    def test_el_certificado_se_lee(self, curva_de_openssl, cual):
        cert, _, _, _ = curva_de_openssl[cual]
        assert cert.algoritmo_clave == "ecdsa"
        assert cert.curva in CURVAS_POR_NOMBRE
        assert cert.punto is not None
        assert CURVAS_POR_NOMBRE[cert.curva].encima(*cert.punto)
        assert cert.autofirmado
        assert not cert.clave_debil

    @pytest.mark.parametrize("cual", CASOS)
    def test_verifica_lo_que_firmo_openssl(self, curva_de_openssl, cual):
        cert, valor, alg, mensaje = curva_de_openssl[cual]
        assert verificar(valor, mensaje, cert, alg)

    @pytest.mark.parametrize("cual", CASOS)
    def test_el_certificado_verifica_su_propia_firma(self, curva_de_openssl, cual):
        # Es el camino exacto que recorren `cadena.py` y `revocacion.py`.
        cert, _, _, _ = curva_de_openssl[cual]
        assert verificar(cert.valor_firma, cert.tbs, cert, cert.algoritmo_firma)

    @pytest.mark.parametrize("cual", CASOS)
    def test_con_un_byte_cambiado_no(self, curva_de_openssl, cual):
        cert, valor, alg, mensaje = curva_de_openssl[cual]
        roto = bytearray(valor)
        roto[-1] ^= 0xFF
        assert not verificar(bytes(roto), mensaje, cert, alg)

    @pytest.mark.parametrize("cual", CASOS)
    def test_sobre_otro_mensaje_tampoco(self, curva_de_openssl, cual):
        cert, valor, alg, mensaje = curva_de_openssl[cual]
        assert not verificar(valor, mensaje + b"!", cert, alg)

    @pytest.mark.parametrize("cual", CASOS)
    def test_las_dos_codificaciones_no_se_confunden(self, curva_de_openssl, cual):
        """La trampa con nombre de esta parte.

        Dentro de un certificado o una CRL la firma es DER; dentro de una firma
        XML son los dos números pegados y rellenos con ceros. Leer una como la
        otra no da un error de formato: daría una firma buena que no verifica,
        o —lo grave— una mala que sí.
        """
        cert, valor, alg, mensaje = curva_de_openssl[cual]
        assert not verificar(valor, mensaje, cert, alg, concatenada=True)

        curva = CURVAS_POR_NOMBRE[cert.curva]
        r, s = _numeros_del_der(valor)
        pegada = r.to_bytes(curva.octetos, "big") + s.to_bytes(curva.octetos, "big")
        assert verificar(pegada, mensaje, cert, alg, concatenada=True)
        assert not verificar(pegada, mensaje, cert, alg)

    def test_un_resumen_mas_largo_que_la_curva(self, curva_de_openssl):
        # P-256 firmado con SHA-384: sobran 128 bits del resumen y hay que
        # tirarlos por la izquierda. Sin recortar, esta firma no verifica.
        cert, valor, alg, mensaje = curva_de_openssl["p256-sha384"]
        assert cert.curva == "P-256" and alg == "sha384"
        assert verificar(valor, mensaje, cert, alg)


@sin_openssl
def test_una_autoridad_de_curva_entera_con_su_crl(tmp_path):
    """Una CA de curva que emite, revoca y publica su lista. Todo de openssl.

    Es la prueba de conjunto: si esto pasa, `cadena.py` encadena firmas ECDSA y
    `revocacion.py` se cree una CRL firmada con ECDSA, que son los dos sitios
    donde el despachador tenía que enterarse de que la clave no es RSA.
    """
    conf = tmp_path / "ca.cnf"
    conf.write_text(
        "[ca]\ndefault_ca=CA\n\n[CA]\ndir=.\ndatabase=./indice.txt\n"
        "new_certs_dir=./nuevos\ncertificate=./ca.crt\nserial=./serie\n"
        "crlnumber=./crlnum\nprivate_key=./ca.key\ndefault_days=3650\n"
        "default_crl_days=30\ndefault_md=sha384\npolicy=politica\n"
        "email_in_dn=no\nunique_subject=no\n\n[politica]\ncommonName=supplied\n\n"
        "[req]\ndistinguished_name=dn\nprompt=no\n\n[dn]\nCN=CA de curva\n\n"
        "[v3_ca]\nbasicConstraints=critical,CA:true\n"
        "keyUsage=critical,keyCertSign,cRLSign\n\n"
        "[v3_hoja]\nbasicConstraints=CA:false\nkeyUsage=critical,digitalSignature\n",
        encoding="ascii",
    )
    (tmp_path / "nuevos").mkdir()
    (tmp_path / "indice.txt").write_text("")
    (tmp_path / "serie").write_text("2000\n")
    (tmp_path / "crlnum").write_text("2000\n")

    def ossl(*orden):
        subprocess.run(["openssl", *orden], cwd=tmp_path, capture_output=True,
                       check=True)

    ossl("ecparam", "-name", "secp384r1", "-genkey", "-noout", "-out", "ca.key")
    ossl("req", "-x509", "-new", "-key", "ca.key", "-sha384", "-days", "7300",
         "-config", "ca.cnf", "-extensions", "v3_ca", "-out", "ca.crt")
    ossl("ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", "hoja.key")
    ossl("req", "-new", "-key", "hoja.key", "-sha256", "-out", "hoja.csr",
         "-subj", "/CN=Hoja de curva")
    ossl("ca", "-batch", "-config", "ca.cnf", "-extensions", "v3_hoja",
         "-in", "hoja.csr", "-out", "hoja.crt")

    ca = firma.leer_certificado(_pem((tmp_path / "ca.crt").read_bytes(),
                                     "CERTIFICATE"))
    la_hoja = firma.leer_certificado(_pem((tmp_path / "hoja.crt").read_bytes(),
                                          "CERTIFICATE"))
    assert ca.curva == "P-384" and la_hoja.curva == "P-256"

    # 1. La cadena: la hoja de curva encadena hasta la CA de curva.
    almacen = cadena.Almacen(tmp_path / "anclas")
    (tmp_path / "anclas").mkdir()
    (tmp_path / "anclas" / "ca.cer").write_bytes(ca.der)
    resultado = cadena.construir(la_hoja, almacen)
    assert resultado.llega, resultado.motivo
    assert resultado.ancla.sujeto == "CA de curva"

    # 2. Y que no se traga una hoja retocada: cambiarle un byte al `tbs` tiene
    #    que romper la firma, no colarse por ser de curva.
    tocada = bytearray(la_hoja.der)
    tocada[len(tocada) // 2] ^= 0x01
    try:
        otra = firma.leer_certificado(bytes(tocada))
    except (ValueError, IndexError):
        pass  # tan tocada que ni se lee: también vale
    else:
        assert not cadena.construir(otra, almacen).llega

    # 3. La CRL, firmada con ECDSA.
    ossl("ca", "-config", "ca.cnf", "-revoke", "hoja.crt",
         "-crl_reason", "keyCompromise")
    ossl("ca", "-config", "ca.cnf", "-gencrl", "-out", "ca.crl")
    una = leer_lista(_pem((tmp_path / "ca.crl").read_bytes(), "X509 CRL"))
    assert una.emisor_nombre == "CA de curva"
    assert set(una.anulaciones) == {la_hoja.serie}
    veredicto = revocacion.comprobar(la_hoja, ca, [una])
    assert veredicto.estado == "anulado", veredicto.motivo
    assert veredicto.anulacion.compromiso

    # 4. Y que una CRL con la firma tocada deja de valer, en vez de colar como
    #    un «no aparece, luego está vigente».
    rota = bytearray(_pem((tmp_path / "ca.crl").read_bytes(), "X509 CRL"))
    rota[-3] ^= 0xFF
    assert revocacion.comprobar(la_hoja, ca, [leer_lista(bytes(rota))]).estado == (
        "sin_saber"
    )


# --- Lo que tiene que parar ------------------------------------------------



OID_EC = bytes([0x2A, 0x86, 0x48, 0xCE, 0x3D, 0x02, 0x01])  # id-ecPublicKey
OID_P256 = bytes([0x2A, 0x86, 0x48, 0xCE, 0x3D, 0x03, 0x01, 0x07])  # prime256v1


def _spki_p256(punto: bytes) -> bytes:
    """Un `SubjectPublicKeyInfo` de P-256 con el punto que se le dé.

    Los OID van como listas de números y no como cadenas escapadas por una
    razón práctica: en este proyecto los `\\xNN` dentro de un heredoc se han
    convertido en bytes crudos más de una vez, y una vez destrozó este mismo
    fichero.
    """
    return _der(0x30, b"".join([
        _der(0x30, _der(0x06, OID_EC) + _der(0x06, OID_P256)),
        _der(0x03, bytes([0]) + punto),
    ]))


def _cert_de_curva(curva, x=None, y=None) -> Certificado:
    return Certificado(
        modulo=0, exponente=0, desde=None, hasta=None, sujeto="De prueba",
        algoritmo_clave="ecdsa", curva=curva.nombre,
        punto=(x if x is not None else curva.gx, y if y is not None else curva.gy),
    )


class TestLoQueTieneQueParar:
    def test_r_o_s_fuera_de_rango(self):
        curva = CURVAS_POR_NOMBRE["P-256"]
        cert = _cert_de_curva(curva)

        def pegada(r, s):
            return (r % curva.p).to_bytes(curva.octetos, "big") + (
                s % curva.p
            ).to_bytes(curva.octetos, "big")

        # Cero y n están fuera del rango 1..n-1. Sin este filtro, s = 0 llega a
        # un inverso modular que no significa nada y r = 0 compara contra cero.
        for r, s in ((0, 1), (1, 0), (curva.n, 1), (1, curva.n), (0, 0)):
            assert not verificar(pegada(r, s), b"x", cert, "sha256",
                                 concatenada=True)

    def test_un_punto_que_no_esta_en_la_curva_se_para_al_leerlo(self):
        """Y se para **al leer el certificado**, que es donde se puede parar.

        Conviene ser preciso sobre lo que compra esta comprobación. En
        `_verificar_ecdsa` hay otra igual, y esa es a mayores: con un punto de
        fuera la aritmética devuelve algo, ese algo no coincide con `r` y la
        firma se rechaza igual. O sea que quitarla no pone roja ninguna prueba,
        y escribir una que lo aparentara sería engañarse —se intentó, pasaba
        con y sin la comprobación—.

        La que sí manda es esta: un certificado cuya clave dice ser de una
        curva y no lo es **no se llega a construir**, y el mensaje dice qué
        pasa en vez de dejar por ahí un `Certificado` con una clave que no es
        una clave.
        """
        curva = CURVAS_POR_NOMBRE["P-256"]
        fuera = (
            bytes([4])
            + curva.gx.to_bytes(32, "big")
            + (curva.gy + 1).to_bytes(32, "big")
        )
        with pytest.raises(ValueError, match="no está en ella"):
            firma.leer_certificado(cert_de_prueba(spki=_spki_p256(fuera)))

    def test_un_punto_del_tamano_equivocado(self):
        curva = CURVAS_POR_NOMBRE["P-256"]
        corto = bytes([4]) + curva.gx.to_bytes(32, "big") + bytes(31)
        with pytest.raises(ValueError, match="tamaño de su curva"):
            firma.leer_certificado(cert_de_prueba(spki=_spki_p256(corto)))

    def test_una_curva_que_no_conocemos(self):
        cert = Certificado(
            modulo=0, exponente=0, desde=None, hasta=None, sujeto="x",
            algoritmo_clave="ecdsa", curva="P-192", punto=(1, 2),
        )
        assert not verificar(b"\x00" * 48, b"x", cert, "sha256", concatenada=True)

    def test_una_firma_concatenada_del_tamano_equivocado(self):
        curva = CURVAS_POR_NOMBRE["P-256"]
        cert = _cert_de_curva(curva)
        assert not verificar(b"\x01" * 63, b"x", cert, "sha256", concatenada=True)
        assert not verificar(b"\x01" * 65, b"x", cert, "sha256", concatenada=True)

    def test_un_der_con_basura_detras(self):
        curva = CURVAS_POR_NOMBRE["P-256"]
        cert = _cert_de_curva(curva)
        bueno = bytes.fromhex("3006020101020102")
        assert not verificar(bueno + b"basura", b"x", cert, "sha256")

    def test_un_der_que_no_es_una_pareja(self):
        curva = CURVAS_POR_NOMBRE["P-256"]
        cert = _cert_de_curva(curva)
        assert not verificar(bytes.fromhex("3003020101"), b"x", cert, "sha256")

    def test_un_resumen_que_no_conocemos(self):
        curva = CURVAS_POR_NOMBRE["P-256"]
        cert = _cert_de_curva(curva)
        assert not verificar(b"\x01" * 64, b"x", cert, "md4", concatenada=True)


class TestLaFuerzaDeLaClave:
    """Que 256 bits de curva no se comparen con 2048 de RSA."""

    def test_una_p256_no_es_debil(self):
        cert = _cert_de_curva(CURVAS_POR_NOMBRE["P-256"])
        assert cert.bits == 256
        assert not cert.clave_debil

    def test_una_rsa_de_1024_si(self):
        cert = Certificado(modulo=2**1023 + 1, exponente=65537, desde=None,
                           hasta=None, sujeto="x")
        assert cert.bits == 1024
        assert cert.clave_debil

    def test_una_rsa_de_2048_no(self):
        cert = Certificado(modulo=2**2047 + 1, exponente=65537, desde=None,
                           hasta=None, sujeto="x")
        assert not cert.clave_debil

    def _quejas(self, cert, metodo):
        """Lo que dice `_regla_valor` de una clave, sin firma que comprobar.

        Hace falta montar el `SignedInfo`: con un elemento vacío la función
        sale por la primera línea y no llega a mirar la clave. La primera
        versión de esta prueba hacía justo eso y no probaba nada.
        """
        ds = "http://www.w3.org/2000/09/xmldsig#"
        sig = etree.Element("{%s}Signature" % ds)
        firmado = etree.SubElement(sig, "{%s}SignedInfo" % ds)
        etree.SubElement(firmado, "{%s}CanonicalizationMethod" % ds).set(
            "Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
        etree.SubElement(firmado, "{%s}SignatureMethod" % ds).set(
            "Algorithm", metodo)
        # El examen se monta a mano con lo que esta prueba quiere mirar: el
        # certificado y el algoritmo. Lo demás —qué cubre, qué declara— es de
        # otras pruebas, y aquí no hay documento del que colgar la firma.
        examen = firma.Examen(
            certificado=cert,
            certificado_crudo=None,
            ilegible=False,
            referencias=(),
            valor=firma._valor_de_la_firma(sig, cert),
            cubre=False,
            apunta_a_lo_suyo=False,
            a_que_apunta="",
            propiedades=None,
            contrafirma=False,
            padre_verificada=True,
        )
        return firma._regla_valor(examen, "")

    def test_una_clave_de_curva_no_sale_marcada_como_corta(self):
        # Es lo que de verdad cambia: con un solo mínimo —los 2048 de RSA—
        # **toda** clave de curva saldría avisada por tener «solo» 256 bits,
        # que es justo al revés de la realidad. Y como las claves de curva son
        # ahora un tercio de las autoridades españolas, el informe se llenaría
        # de un aviso falso.
        cert = _cert_de_curva(CURVAS_POR_NOMBRE["P-256"])
        quejas = self._quejas(
            cert, "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256")
        assert [q.codigo for q in quejas if q.codigo == "FIRMA-DEBIL"] == []

    def test_una_rsa_corta_sigue_avisando_y_pide_2048(self):
        cert = Certificado(modulo=2**1023 + 1, exponente=65537, desde=None,
                           hasta=None, sujeto="x")
        quejas = self._quejas(
            cert, "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256")
        debiles = [q for q in quejas if q.codigo == "FIRMA-DEBIL"]
        assert len(debiles) == 1
        assert "2048" in debiles[0].mensaje and "1024" in debiles[0].mensaje

    def test_una_firma_con_curva_no_se_da_por_incomprobable(self):
        # Antes de esto, `ecdsa-sha256` no estaba en la tabla de métodos y la
        # firma salía como FIRMA-SIN-COMPROBAR: un aviso que decía «no sé» en
        # lugar de comprobarlo.
        cert = _cert_de_curva(CURVAS_POR_NOMBRE["P-256"])
        quejas = self._quejas(
            cert, "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256")
        assert [q.codigo for q in quejas] == []
