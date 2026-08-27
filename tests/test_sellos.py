"""Comprobaciones del sello de tiempo: RFC 3161 dentro de XAdES.

Aquí el círculo se rompe de la misma forma que en `test_curva.py`: **el sello
no lo fabrica este código**. Los dos que van escritos abajo los hizo `openssl`,
y el bueno está hecho sobre el `SignatureValue` exacto del documento que
`test_firma.documento()` firma —que es determinista, con su clave de juguete y
su fecha fija—, canonicalizado por lxml. O sea que los bytes que la autoridad
selló no los eligió este módulo: los eligió la norma, los serializó lxml y los
resumió `openssl`.

Van escritos en vez de generarse al vuelo para que estas pruebas corran sin
`openssl` instalado y dentro del navegador, donde no hay ninguno. Las que sí lo
necesitan —montar una autoridad entera y sellar cosas a medida— se saltan solas
cuando no está.

Los dos vectores dicen cosas distintas y las dos hacen falta:

- `SELLO_BUENO` es un sello correcto de una autoridad con permiso.
- `SELLO_SIN_PERMISO` lleva **la misma fecha y el mismo resumen**, está
  perfectamente firmado y su firma verifica; lo único que le pasa es que el
  certificado que lo firma no está autorizado a sellar el tiempo. Es el caso
  que importa: el que pasa todas las comprobaciones criptográficas y aun así
  hay que rechazar. Si un día alguien afloja `autorizado_a_sellar`, esa prueba
  es la única que se pone roja.
"""

import base64
import dataclasses
import hashlib
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

import pytest
from lxml import etree

from validador import sellos
from validador.firma import _hijo, leer_certificado, verificar
from validador.formato import detectar, parser
from validador.incidencias import AVISO, ERROR, NOTA
from tests.test_firma import HOY, C14N, certificado, documento

NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_XADES = "http://uri.etsi.org/01903/v1.3.2#"

SELLO_BUENO = (
    "MIIJDgYJKoZIhvcNAQcCoIII/zCCCPsCAQMxDzANBglghkgBZQMEAgEFADCBngYLKoZI"
    "hvcNAQkQAQSggY4EgYswgYgCAQEGBCoDBAEwMTANBglghkgBZQMEAgEFAAQg9oaJiDxV"
    "g+U8q28t3vzNGHw6bYj7uOwYd+YT/Ksy1bUCAQMYDzIwMjYwODI3MjIzMjEzWjAKAgEB"
    "gAIB9IEBZAEB/wIJANDz29iUwV8qoBykGjAYMRYwFAYDVQQDDA1UU1UgZGUgcHJ1ZWJh"
    "oIIGRjCCAywwggIUoAMCAQICAQcwDQYJKoZIhvcNAQELBQAwITEfMB0GA1UEAwwWQUMg"
    "ZGUgc2VsbG9zIGRlIHBydWViYTAeFw0yNjA4MjcyMjE4MTNaFw0zNjA4MjQyMjE4MTNa"
    "MBgxFjAUBgNVBAMMDVRTVSBkZSBwcnVlYmEwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAw"
    "ggEKAoIBAQCrEjGq5EESLiBqKcDPFdi8Nf9J/mxs6F7ssCHeF0Fu5cfe4WcrdMPpwFSK"
    "oBk4Yj/W51gsdoWSoA2hEBqAhknvaYR6EoFUZCwKsDUAYUpXpdK4z4QnVBdBEIRS03yA"
    "2iiIbIuVAXp0RQBrVcO/Zggq3emOx6dVC86PZ5CowDxSgtgzSVlwMqcOvEGrlWCpjXLX"
    "24OWdtGVzrXotxkBTHGPAWoVi0hQmXW8EypRvbSrETlyqLYTosvVHgD7UEWQt95kyJjG"
    "m7ajxE5+nhRBrPxKnVKKtaWgeiGUmH+qlS9a328uXJ2S48Q/hxjAbBTDjKnhLz+PqJ3h"
    "XSGGvBN4wTh5AgMBAAGjeDB2MAwGA1UdEwEB/wQCMAAwDgYDVR0PAQH/BAQDAgeAMBYG"
    "A1UdJQEB/wQMMAoGCCsGAQUFBwMIMB0GA1UdDgQWBBQYjX/AhEd2UbH8e78FzGMmNihs"
    "GDAfBgNVHSMEGDAWgBSphU64OVjc4JZX/N81z5NOSKPj0jANBgkqhkiG9w0BAQsFAAOC"
    "AQEAnAgyagPf/PgiprcYmqOEkgic8IC0zAY64j3X+x75ae6dgBeA5s18gZL9NVbdBhqh"
    "Z+etalBg4w/7boAR+9kFkNf7Caf213bL5gs7IVVsR1I75X58Zh4n457IVQOoDzjD/Gen"
    "oZRS4cUlvJsmlmeKP72LN04hdFUvqA/kUAPIf6Coi+MP6MiIr7ulZZNZLhbhqhSCU2VR"
    "YD9FakGcZ9AncdD4o5TXudggyZrlTEZoY194P+fkI4KX0gOQs5MxS62Ke0XDWD7XB5cH"
    "4IphxzaokgeegrVR52YD6PFJ3FdgANmgv5gvx96iTdxX98Smz160HD2xPo9/opMeVzGD"
    "JpymczCCAxIwggH6oAMCAQICFECLVOo+cDTDn/g0nINpkJFOsovQMA0GCSqGSIb3DQEB"
    "CwUAMCExHzAdBgNVBAMMFkFDIGRlIHNlbGxvcyBkZSBwcnVlYmEwHhcNMjYwODI3MjIx"
    "ODEyWhcNMzYwODI0MjIxODEyWjAhMR8wHQYDVQQDDBZBQyBkZSBzZWxsb3MgZGUgcHJ1"
    "ZWJhMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAvFlHuEuTtp3lnCPdSS5S"
    "RGdLZpjed9sZYOIyvxmkNW1bjFzvTPH+UUUyJJJ4g8DPgb3TsfBUkURNC1LfBYGt31o7"
    "zRhIUFPqWEPot/Wcvq6OnrZE1J4nqSw5yxEo973qsubn9GvR2CcK0lL60F9bNrll8PM8"
    "wF+FcotjyQmntoV7Gk3xr648/5znedh2JpmlY7GsV0ev+5+oIwU1fffJt1eGeGGuDCEq"
    "Pad2mKqfEkW3dSadV5fD0cBa94wdcEH0su1CYnbBUDk532Vz2OwIyBN8gQnsWgfPTYPC"
    "uu8xPRD/nDz5MZTrNI+qP4lELt6nsToXXeezGyHxkYVAujQ/LwIDAQABo0IwQDAPBgNV"
    "HRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBBjAdBgNVHQ4EFgQUqYVOuDlY3OCWV/zf"
    "Nc+TTkij49IwDQYJKoZIhvcNAQELBQADggEBAAc8Pz62/8CzkzyMvcg++LrBy7yXbUQR"
    "5ADHBmvr/Ye9TYWtp2xUFZXoZguzaU3gkvhIEk0xnOZMXIQAHmy7h8yGlizI3L5rzVOM"
    "XQX78Y6wqQxC2Y3fv710B97vicXoLnyuhobSrN07SX1ufh35y3gUePCl04s9Ek+Q9dvs"
    "eVhJDOAcvVrYd9zUq5zilWZUph2azeu2/jt7ec3Z9CveVydIvyYq/qnKctx+vajo05rj"
    "fy196jl6mP0IaCUTU1HU2soa/01Akw2p0trxIeDlHeG7FPhj6V+OFqOYBV8d5o3MhAGH"
    "q6W5v/CG0JILWYTimeNjfouzWNciBI6tgUKznLgxggH4MIIB9AIBATAmMCExHzAdBgNV"
    "BAMMFkFDIGRlIHNlbGxvcyBkZSBwcnVlYmECAQcwDQYJYIZIAWUDBAIBBQCggaQwGgYJ"
    "KoZIhvcNAQkDMQ0GCyqGSIb3DQEJEAEEMBwGCSqGSIb3DQEJBTEPFw0yNjA4MjcyMjMy"
    "MTNaMC8GCSqGSIb3DQEJBDEiBCD7vyd439XXb5jW8KQmofx8f6bOq11KNwXHx1dKTXOu"
    "ITA3BgsqhkiG9w0BCRACLzEoMCYwJDAiBCA+pGlS9jQ+tLVHJJFopR7Dwloe41dz1Liz"
    "1m7poyUfNDANBgkqhkiG9w0BAQEFAASCAQCplUH6+da5M2PRtoCALEmKxlKXqn6DgPzi"
    "PMahZiqXollco3uT9E5rpsiyk6EAl3cjKxrz3bZ7dTAV6Ixq5Wsvhi0Eh9Dx5q7xPY+Z"
    "3JEgZHChWyqQmpDGhJ5xhFq+uq4D2m6b+3+FkhtqLF3yqcLG7rglKcnwB3O5m+Vq4Vxe"
    "lMepoffSKDVIDGu7b1nigfFl7uteOzMkM27jkf+5KZARbbeu+3+L8s8Yi+Pc9krNhaJ5"
    "dFzn9jdei5bTYCiqynE/hoKpONgQUUajg/Phm53sOm0knsj2Zm8Bfwl8STRaf0HocMwa"
    "avRyzerE8ORydch1ERQhu7thR6EXdtGf0NdP"
)

SELLO_SIN_PERMISO = (
    "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"
    "9JcRgjARo9XlUvHmwAcgbdZJGgI="
)


def token(cual: str = "bueno") -> bytes:
    return base64.b64decode(SELLO_BUENO if cual == "bueno" else SELLO_SIN_PERMISO)


def valor_firmado(datos: bytes) -> bytes:
    """Los octetos que un sello sobre la firma tiene que cubrir."""
    raiz = etree.fromstring(datos)
    firma = raiz.xpath(".//*[local-name()='Signature']")[0]
    return etree.tostring(
        _hijo(firma, "SignatureValue"), method="c14n", exclusive=False,
        with_comments=False,
    )


# --- Meter el sello en el documento ----------------------------------------


def con_sello(datos: bytes = None, der: bytes = None, clase: str = "SignatureTimeStamp",
              c14n: str | None = None) -> bytes:
    """Añade un sello de tiempo a un Facturae ya firmado.

    El sello va en `UnsignedSignatureProperties`, que es donde XAdES lo pone y
    que **la firma no cubre**: por eso se puede sellar después de firmar sin
    romper nada. Meterlo en las propiedades firmadas invalidaría la firma, que
    es una forma bonita de comprobar que el sitio importa.
    """
    datos = documento() if datos is None else datos
    der = token() if der is None else der
    raiz = etree.fromstring(datos)
    firma = raiz.xpath(".//*[local-name()='Signature']")[0]
    cualificadas = firma.xpath(".//*[local-name()='QualifyingProperties']")[0]

    xa = lambda n: f"{{{NS_XADES}}}{n}"  # noqa: E731
    ds = lambda n: f"{{{NS_DS}}}{n}"  # noqa: E731
    sin_firmar = etree.SubElement(cualificadas, xa("UnsignedProperties"))
    de_la_firma = etree.SubElement(sin_firmar, xa("UnsignedSignatureProperties"))
    nodo = etree.SubElement(de_la_firma, xa(clase))
    if c14n is not None:
        etree.SubElement(nodo, ds("CanonicalizationMethod")).set("Algorithm", c14n)
    etree.SubElement(nodo, xa("EncapsulatedTimeStamp")).text = base64.b64encode(
        der
    ).decode()
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def quejas(datos: bytes):
    raiz = etree.fromstring(datos, parser=parser())
    return sellos.reglas_de_documento(raiz, detectar(datos))


def codigos(incidencias, gravedad=None) -> set[str]:
    return {i.codigo for i in incidencias if gravedad is None or i.gravedad == gravedad}


def texto_de(incidencias, codigo: str) -> str:
    return next(i.mensaje for i in incidencias if i.codigo == codigo)


# --- Lo que dice el sello --------------------------------------------------


class TestLoQueDiceElSello:
    def test_se_lee_entero(self):
        sello = sellos.leer(token())
        assert sello.momento.year == 2026
        assert sello.momento.tzinfo is not None
        assert sello.serie > 0
        assert sello.resumen_de == "sha256"
        assert len(sello.resumen) == 32
        assert sello.resumen_firma == "sha256"

    def test_trae_el_certificado_de_la_autoridad(self):
        sello = sellos.leer(token())
        assert sello.firmante is not None
        assert sello.firmante.sujeto == "TSU de prueba"
        # Y también la CA que lo emitió: el sello trae la cadena, que es lo que
        # hará falta para saber de quién es esa autoridad.
        assert len(sello.certificados) == 2

    def test_la_precision_se_lee(self):
        # `accuracy = secs:1, millisecs:500, microsecs:100` en la configuración
        # con la que `openssl` lo emitió.
        assert sellos.leer(token()).precision == "±1 s 500 ms 100 µs"

    def test_el_nombre_que_la_autoridad_se_da(self):
        # Sale del campo `tsa` del TSTInfo, que es un GeneralName. Es un dato
        # que no respalda nadie, y por eso `quien` prefiere el certificado.
        sello = sellos.leer(token())
        assert sello.nombre == "TSU de prueba"
        assert sello.quien == sello.firmante.sujeto

    def test_el_resumen_es_el_de_la_firma_del_documento(self):
        """El sello está hecho sobre el SignatureValue de `documento()`.

        Esto es lo que hace que el vector valga: los bytes los canonicalizó
        lxml y los resumió `openssl`, no este módulo.
        """
        sello = sellos.leer(token())
        assert sello.resumen == hashlib.sha256(valor_firmado(documento())).digest()


class TestLaFechaDelSello:
    """`genTime` es un GeneralizedTime, con fracción de segundo opcional."""

    @pytest.mark.parametrize(
        "crudo, esperado",
        [
            (b"20260827221813Z", (2026, 8, 27, 22, 18, 13, 0)),
            (b"20260827221813", (2026, 8, 27, 22, 18, 13, 0)),
            (b"20260827221813.5Z", (2026, 8, 27, 22, 18, 13, 500000)),
            (b"20260827221813.457Z", (2026, 8, 27, 22, 18, 13, 457000)),
        ],
    )
    def test_se_lee_con_su_fraccion(self, crudo, esperado):
        cuando = sellos._momento(crudo)
        assert cuando is not None
        assert (cuando.year, cuando.month, cuando.day, cuando.hour,
                cuando.minute, cuando.second, cuando.microsecond) == esperado
        assert cuando.tzinfo == timezone.utc

    @pytest.mark.parametrize("crudo", [b"", b"no es una fecha", b"20261332221813Z"])
    def test_una_fecha_imposible_no_se_inventa(self, crudo):
        assert sellos._momento(crudo) is None


class TestQueNoEsUnSello:
    @pytest.mark.parametrize(
        "recorte, esperado",
        [
            (b"", "DER"),
            (b"\x30\x03\x02\x01\x01", "ContentInfo"),
        ],
    )
    def test_se_dice_por_que_no_se_lee(self, recorte, esperado):
        with pytest.raises(ValueError) as fallo:
            sellos.leer(recorte)
        assert esperado.lower() in str(fallo.value).lower()

    def test_un_cms_que_no_es_un_sello(self):
        """Un SignedData de otra cosa no se acepta como sello.

        Se cambia el OID del contenido —el que dice «esto es un TSTInfo»— por
        otro. Sin esta comprobación, cualquier fichero firmado con CMS entraría
        por aquí y se leería como si fuera una fecha.
        """
        der = bytearray(token())
        sitio = der.find(bytes.fromhex("2a864886f70d0109100104"))
        assert sitio > 0
        der[sitio + 10] = 0x05  # ...16.1.5 en vez de ...16.1.4
        with pytest.raises(ValueError, match="no es un sello de tiempo"):
            sellos.leer(bytes(der))


# --- Lo que tiene que parar ------------------------------------------------


class TestLoQueTieneQueParar:
    def test_el_sello_bueno_pasa(self):
        """El punto de partida: sin esto, lo de abajo no prueba nada."""
        sello = sellos.leer(token())
        assert sellos.comprobar(sello) == ""
        assert sellos.cubre(sello, valor_firmado(documento())) == ""

    def test_no_verifica_sin_reetiquetar_los_atributos(self):
        """La trampa del módulo, escrita como prueba.

        Lo que se firma es la secuencia de atributos con la etiqueta cambiada
        de `[0]` a `SET OF`. Si alguien «simplifica» eso, esta prueba se pone
        roja; y si no existiera, la simplificación rompería todos los sellos
        del mundo sin que ninguna otra prueba lo dijera.
        """
        sello = sellos.leer(token())
        crudo = sello.atributos_der
        assert crudo[0] == 0xA0
        assert verificar(sello.valor_firma, b"\x31" + crudo[1:], sello.firmante,
                         sello.resumen_firma)
        assert not verificar(sello.valor_firma, crudo, sello.firmante,
                             sello.resumen_firma)

    def test_un_sello_cambiado_por_otro(self):
        """El `messageDigest` ata lo firmado al sello que se enseña."""
        sello = sellos.leer(token())
        tocado = dataclasses.replace(
            sello, contenido=sello.contenido[:-1] + bytes([sello.contenido[-1] ^ 1])
        )
        assert "cambiado uno por otro" in sellos.comprobar(tocado)

    def test_otro_certificado_en_el_sello(self):
        """`signingCertificate` caza el cambiazo antes que la firma.

        Se pone la CA en lugar del TSU. Con la firma bastaría para detectarlo,
        pero el mensaje sería «la firma no cuadra», que manda a mirar al sitio
        equivocado.
        """
        sello = sellos.leer(token())
        otro = dataclasses.replace(sello, firmante=sello.certificados[1])
        assert "no es el que la autoridad dice haber usado" in sellos.comprobar(otro)

    def test_el_resumen_del_certificado_es_sha256_y_no_sha1(self):
        """ESSCertIDv2 va por defecto en SHA-256; ESSCertID, en SHA-1.

        Escribir un único valor por defecto —lo natural— hace que la
        comprobación del certificado falle en todos los sellos modernos, que es
        justo donde hace falta. Se fija aquí porque el fallo sería silencioso
        en la dirección contraria: dar por bueno lo que no se ha comprobado.
        """
        sello = sellos.leer(token())
        crudo = sello.atributo(sellos._OID_CERT_FIRMANTE_V2)
        assert crudo is not None
        guardado, algoritmo = sellos._resumen_declarado(crudo, "sha256")
        assert algoritmo == "sha256"
        assert guardado == hashlib.sha256(sello.firmante.der).digest()
        assert guardado != hashlib.sha1(sello.firmante.der).digest()

    def test_una_firma_tocada(self):
        sello = sellos.leer(token())
        roto = dataclasses.replace(
            sello, valor_firma=sello.valor_firma[:-1]
            + bytes([sello.valor_firma[-1] ^ 1])
        )
        assert "no cuadra con su certificado" in sellos.comprobar(roto)

    def test_sin_certificado_no_se_da_por_bueno(self):
        """Sin el certificado no hay nada que comprobar: no es «vale»."""
        sello = dataclasses.replace(sellos.leer(token()), firmante=None,
                                    certificados=())
        assert "no hay con qué comprobarlo" in sellos.comprobar(sello)

    def test_un_sello_de_otra_cosa(self):
        """El sello está bien; lo que no es, es de esta firma."""
        sello = sellos.leer(token())
        assert sellos.comprobar(sello) == ""
        otro = valor_firmado(documento(total="999.00"))
        assert "no es el de esta firma" in sellos.cubre(sello, otro)


class TestElPermisoParaSellar:
    """La comprobación que no es criptográfica y es la que más pesa."""

    def test_el_sello_sin_permiso_esta_bien_firmado(self):
        """Primero, que quede claro que lo único que le pasa es el permiso."""
        sello = sellos.leer(token("sin_permiso"))
        assert verificar(sello.valor_firma, b"\x31" + sello.atributos_der[1:],
                         sello.firmante, sello.resumen_firma)
        assert sellos.cubre(sello, valor_firmado(documento())) == ""

    def test_y_aun_asi_se_rechaza(self):
        sello = sellos.leer(token("sin_permiso"))
        motivo = sellos.comprobar(sello)
        assert "no para sellar el tiempo" in motivo

    def test_un_certificado_sin_uso_extendido(self):
        # `certificado()` de `test_firma` no lleva extensiones ningunas.
        assert "le falta la extensión" in sellos.autorizado_a_sellar(
            leer_certificado(certificado())
        )

    def test_el_de_la_autoridad_de_verdad_vale(self):
        sello = sellos.leer(token())
        assert sellos.autorizado_a_sellar(sello.firmante) == ""


# --- Dentro de una factura -------------------------------------------------


class TestEnUnaFactura:
    def test_una_factura_sellada(self):
        incidencias = quejas(con_sello())
        assert codigos(incidencias, ERROR) == set()
        assert "SELLO-TIEMPO" in codigos(incidencias)
        assert "SELLO-FALTA" not in codigos(incidencias)
        texto = texto_de(incidencias, "SELLO-TIEMPO")
        assert "TSU de prueba" in texto
        # Y dice lo que todavía no se sabe, que es la mitad del mensaje.
        assert "lista de confianza del Estado" in texto

    def test_sin_sello_se_dice_de_quien_es_la_fecha(self):
        incidencias = quejas(documento())
        assert "SELLO-FALTA" in codigos(incidencias, NOTA)
        texto = texto_de(incidencias, "SELLO-FALTA")
        assert "2026-03-02" in texto
        assert "fechando hacia atrás" in texto

    def test_sin_xades_no_se_dice_nada(self):
        """`firma.py` ya se queja de que no es XAdES. Repetirlo es ruido."""
        assert quejas(documento(con_xades=False)) == []

    def test_un_sello_copiado_de_otro_documento(self):
        """El caso que `cubre` existe para cazar."""
        incidencias = quejas(con_sello(datos=documento(total="999.00")))
        assert "SELLO-NO-CUBRE" in codigos(incidencias, ERROR)
        # Y la fecha vuelve a ser la del firmante, dicho explícitamente.
        assert "SELLO-FALTA" in codigos(incidencias, NOTA)

    def test_un_sello_sin_permiso_en_una_factura(self):
        incidencias = quejas(con_sello(der=token("sin_permiso")))
        assert "SELLO-ROTO" in codigos(incidencias, ERROR)
        assert "no para sellar el tiempo" in texto_de(incidencias, "SELLO-ROTO")

    def test_un_sello_ilegible(self):
        incidencias = quejas(con_sello(der=b"esto no es DER"))
        assert "SELLO-ILEGIBLE" in codigos(incidencias, AVISO)

    def test_un_sello_de_otra_clase_se_dice_y_no_se_usa(self):
        incidencias = quejas(con_sello(clase="ArchiveTimeStamp"))
        assert "SELLO-NO-COMPROBADO" in codigos(incidencias, NOTA)
        assert codigos(incidencias, ERROR) == set()
        assert "de archivo" in texto_de(incidencias, "SELLO-NO-COMPROBADO")

    def test_una_canonicalizacion_que_no_sabemos_no_da_por_bueno(self):
        """Fallar hacia el lado seguro: sin poder calcular la entrada, no vale."""
        incidencias = quejas(con_sello(c14n="http://example.invalid/c14n"))
        assert "SELLO-SIN-COMPROBAR" in codigos(incidencias, AVISO)
        assert "SELLO-TIEMPO" not in codigos(incidencias)

    def test_la_c14n_declarada_en_el_sello_se_usa(self):
        """Declararla explícitamente da el mismo resultado que heredarla."""
        incidencias = quejas(con_sello(c14n=C14N))
        assert "SELLO-TIEMPO" in codigos(incidencias)
        assert codigos(incidencias, ERROR) == set()


class TestLaFechaQueVale:
    def test_el_momento_probado_sale_del_sello(self):
        raiz = etree.fromstring(con_sello())
        firma = raiz.xpath(".//*[local-name()='Signature']")[0]
        probado = sellos.momento_probado(firma)
        assert probado is not None
        cuando, sello = probado
        assert cuando == sello.momento
        assert sello.quien == "TSU de prueba"

    def test_sin_sello_bueno_no_hay_fecha_probada(self):
        for datos in (documento(), con_sello(der=token("sin_permiso")),
                      con_sello(datos=documento(total="999.00"))):
            raiz = etree.fromstring(datos)
            firma = raiz.xpath(".//*[local-name()='Signature']")[0]
            assert sellos.momento_probado(firma) is None

    def test_una_fecha_declarada_imposible(self):
        """Declarar haber firmado después de que un tercero ya lo viera."""
        sello = sellos.leer(token())
        tarde = sello.momento + timedelta(days=30)
        incidencias = quejas(con_sello(datos=documento(firmado_el=tarde)))
        # El documento se ha vuelto a firmar, así que el sello ya no es suyo:
        # lo que se comprueba aquí es la regla, con el sello puesto a mano.
        assert "SELLO-NO-CUBRE" in codigos(incidencias, ERROR)

    def test_la_contradiccion_se_ve_con_el_sello_de_esa_firma(self, tsa):
        """Lo mismo, pero con un sello de verdad de esa firma."""
        datos = documento(firmado_el=HOY + timedelta(days=3650))
        der = tsa(valor_firmado(datos))
        incidencias = quejas(con_sello(datos=datos, der=der))
        assert "SELLO-CONTRADICE" in codigos(incidencias, AVISO)
        assert "no es cierta" in texto_de(incidencias, "SELLO-CONTRADICE")

    def test_un_sello_anterior_al_certificado(self, tsa):
        """Imposible: la firma existía antes que la clave que dice haberla hecho."""
        cert = certificado(desde=HOY + timedelta(days=3650),
                           hasta=HOY + timedelta(days=4000))
        datos = documento(cert=cert)
        der = tsa(valor_firmado(datos))
        incidencias = quejas(con_sello(datos=datos, der=der))
        assert "SELLO-ANTES-DEL-CERTIFICADO" in codigos(incidencias, ERROR)

    def test_un_sello_posterior_a_la_caducidad_no_es_un_error(self, tsa):
        """La asimetría, escrita: sellar tarde es legítimo, pero no prueba.

        Un sello posterior a la caducidad no demuestra nada malo —se firma un
        martes y se sella el jueves, o meses después—, así que no es un error.
        Lo que sí pasa es que entonces **nada acredita** que la firma se hiciera
        mientras el certificado valía, y eso es un aviso: es la maniobra para la
        que sirve un sello, vista desde el otro lado.
        """
        cert = certificado(desde=HOY - timedelta(days=800),
                           hasta=HOY - timedelta(days=400))
        datos = documento(cert=cert, firmado_el=HOY - timedelta(days=500))
        der = tsa(valor_firmado(datos))
        incidencias = quejas(con_sello(datos=datos, der=der))
        assert "SELLO-ANTES-DEL-CERTIFICADO" not in codigos(incidencias)
        assert codigos(incidencias, ERROR) == set()
        assert "SELLO-DESPUES-DE-CADUCAR" in codigos(incidencias, AVISO)
        assert "SELLO-TIEMPO" in codigos(incidencias)

    def test_dentro_de_la_vigencia_no_se_dice_nada_de_la_caducidad(self, tsa):
        """El control de la regla de arriba: sin ella no probaría nada."""
        cert = certificado(desde=HOY - timedelta(days=100),
                           hasta=HOY + timedelta(days=3650))
        datos = documento(cert=cert)
        incidencias = quejas(
            con_sello(datos=datos, der=tsa(valor_firmado(datos)))
        )
        assert "SELLO-DESPUES-DE-CADUCAR" not in codigos(incidencias)



# --- Que la fecha llegue abajo ---------------------------------------------


class TestLaFechaLlegaAlResto:
    """Lo que de verdad importa: que el sello **cambie el veredicto**.

    Leer un sello y escribir una nota bonita no arregla nada. Lo que arregla el
    agujero es que la fecha acreditada sustituya a la declarada en la vigencia
    de la cadena y en la revocación, y eso se comprueba aquí de la única forma
    que vale: con un caso que sale distinto según de dónde venga la fecha.
    """

    def test_la_cadena_se_mide_contra_el_sello(self, tsa, tmp_path):
        """Un ancla que caducó **entre** la fecha declarada y la del sello.

        Con la fecha del firmante no se ve nada. Con la del sello, el ancla
        estaba caducada, y eso es lo que hay que decir: lo único acreditado de
        esta firma es posterior a la caducidad del ancla.
        """
        from tests.test_cadena import HOJA, RAIZ, almacen_con, certificado as cert_de
        from tests.test_cadena import raiz
        from validador import cadena

        # La hoja cuelga de la raíz directamente: el documento solo lleva un
        # certificado dentro —como las facturas de verdad—, así que una cadena
        # con intermedia no se podría cerrar.
        ancla = raiz(hasta=HOY + timedelta(days=30))
        firmante = cert_de("Talleres Paco SL", "Raiz de pruebas", HOJA, RAIZ, serie=3)
        datos = documento(cert=firmante, modulo=HOJA[0], privada=HOJA[1])
        almacen = almacen_con(ancla, tmp_path=tmp_path)

        raiz_xml = etree.fromstring(datos, parser=parser())
        sin = cadena.reglas_de_documento(raiz_xml, detectar(datos), almacen)
        assert "CADENA-CADUCADA" not in codigos(sin)

        sellado = con_sello(datos=datos, der=tsa(valor_firmado(datos)))
        raiz_xml = etree.fromstring(sellado, parser=parser())
        con = cadena.reglas_de_documento(raiz_xml, detectar(sellado), almacen)
        assert "CADENA-CADUCADA" in codigos(con, ERROR)
        assert "acredita el sello de tiempo" in texto_de(con, "CADENA-CADUCADA")

    def test_el_informe_entero_lo_cuenta(self):
        """Que la regla exista no sirve si el orquestador no la llama."""
        from validador.factura import validar

        informe = validar(con_sello())
        assert "SELLO-TIEMPO" in {i.codigo for i in informe.incidencias}
        nota = next(i for i in informe.notas if i.codigo == "SELLO-TIEMPO")
        assert "TSU de prueba" in nota.mensaje

    def test_las_quejas_de_sello_salen_como_lo_que_son(self):
        """Un sello mal no es un problema de formato.

        La etiqueta de la norma va en el informe porque cambia qué hacer con la
        queja. Sin la rama que les toca, todas las de sello salían como
        «Formato», que manda a mirar el XML cuando el problema es la fecha de
        la firma.
        """
        from validador.factura import SELLO, origen
        from validador.incidencias import Incidencia

        for codigo in ("SELLO-TIEMPO", "SELLO-FALTA", "SELLO-ROTO",
                       "SELLO-NO-CUBRE", "SELLO-DESPUES-DE-CADUCAR"):
            assert origen(Incidencia(codigo, NOTA, "x")) == SELLO, codigo

    def test_sin_sello_el_informe_dice_de_quien_es_la_fecha(self):
        from validador.factura import validar

        informe = validar(documento())
        assert "SELLO-FALTA" in {i.codigo for i in informe.incidencias}


# --- Fuera del círculo: una autoridad de sellado entera --------------------


@pytest.fixture(scope="session")
def tsa(tmp_path_factory):
    """Monta una TSA de verdad con `openssl` y devuelve con qué sellar.

    Los vectores escritos arriba cubren el camino entero, pero son fijos: no
    permiten sellar unos bytes elegidos por la prueba. Esto sí, y es lo que
    hace falta para las reglas que cruzan la fecha del sello con otra cosa.
    """
    if shutil.which("openssl") is None:
        pytest.skip("hace falta openssl")
    casa = tmp_path_factory.mktemp("tsa")
    (casa / "serial.txt").write_text("01\n")
    (casa / "tsa.cnf").write_text(CONFIGURACION, encoding="utf-8")

    def corre(*orden):
        hecho = subprocess.run(["openssl", *orden], cwd=casa, capture_output=True)
        if hecho.returncode:
            pytest.skip(f"openssl no pudo: {hecho.stderr.decode()[:200]}")
        return hecho

    corre("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "ca.key",
          "-out", "ca.crt", "-days", "7300", "-subj", "/CN=AC de sellos",
          "-config", "tsa.cnf", "-extensions", "v3_ca")
    corre("req", "-newkey", "rsa:2048", "-nodes", "-keyout", "tsa.key",
          "-out", "tsa.csr", "-subj", "/CN=TSU de las pruebas", "-config", "tsa.cnf")
    corre("x509", "-req", "-in", "tsa.csr", "-CA", "ca.crt", "-CAkey", "ca.key",
          "-set_serial", "7", "-days", "7300", "-out", "tsa.crt",
          "-extfile", "tsa.cnf", "-extensions", "v3_tsa")

    contador = [0]

    def sellar(datos: bytes) -> bytes:
        contador[0] += 1
        nombre = f"d{contador[0]}"
        (casa / nombre).write_bytes(datos)
        corre("ts", "-query", "-data", nombre, "-sha256", "-cert",
              "-out", nombre + ".tsq")
        corre("ts", "-reply", "-queryfile", nombre + ".tsq", "-signer", "tsa.crt",
              "-inkey", "tsa.key", "-config", "tsa.cnf", "-section", "tsa_config",
              "-out", nombre + ".tsr")
        corre("ts", "-reply", "-in", nombre + ".tsr", "-token_out",
              "-out", nombre + ".der")
        return (casa / (nombre + ".der")).read_bytes()

    return sellar


CONFIGURACION = """[ req ]
distinguished_name = dn
prompt = no
[ dn ]
CN = Sellos de prueba
[ v3_ca ]
basicConstraints = critical,CA:TRUE
keyUsage = critical,keyCertSign,cRLSign
[ v3_tsa ]
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature
extendedKeyUsage = critical,timeStamping
[ tsa ]
default_tsa = tsa_config
[ tsa_config ]
serial = serial.txt
crypto_device = builtin
signer_cert = tsa.crt
certs = ca.crt
signer_key = tsa.key
signer_digest = sha256
default_policy = 1.2.3.4.1
digests = sha256, sha384, sha512
accuracy = secs:1
clock_precision_digits = 3
ordering = yes
tsa_name = yes
ess_cert_id_alg = sha256
"""


class TestContraUnaAutoridadDeVerdad:
    def test_un_sello_recien_hecho_vale(self, tsa):
        datos = documento()
        der = tsa(valor_firmado(datos))
        sello = sellos.leer(der)
        assert sellos.comprobar(sello) == ""
        assert sellos.cubre(sello, valor_firmado(datos)) == ""
        assert sello.momento > datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_la_factura_entera_con_su_sello(self, tsa):
        datos = documento()
        incidencias = quejas(con_sello(datos=datos, der=tsa(valor_firmado(datos))))
        assert codigos(incidencias, ERROR) == set()
        assert "SELLO-TIEMPO" in codigos(incidencias)

    def test_dos_sellos_y_manda_el_mas_antiguo(self, tsa):
        """Con varios sellos buenos, el más antiguo es la cota que se sostiene.

        Los dos son ciertos: la firma existía en las dos fechas. Pero lo que un
        sello demuestra es «ya existía entonces», así que el más antiguo dice
        más y es el único que hace falta.
        """
        datos = documento()
        entrada = valor_firmado(datos)
        primero = tsa(entrada)
        segundo = tsa(entrada)

        # Se montan los dos, y el nuevo se pone **delante** para que ganar no
        # pueda salir de coger el primero de la lista.
        raiz = etree.fromstring(con_sello(datos=datos, der=primero))
        firma = raiz.xpath(".//*[local-name()='Signature']")[0]
        propiedades = firma.xpath(
            ".//*[local-name()='UnsignedSignatureProperties']"
        )[0]
        nodo = etree.Element(f"{{{NS_XADES}}}SignatureTimeStamp")
        etree.SubElement(
            nodo, f"{{{NS_XADES}}}EncapsulatedTimeStamp"
        ).text = base64.b64encode(segundo).decode()
        propiedades.insert(0, nodo)

        fechas = [h.sello.momento for h in sellos.sellos_de(firma) if h.sello]
        assert len(fechas) == 2
        # Con la TSA sellando en milisegundos, dos sellos seguidos no caen en
        # el mismo instante. Si cayeran, `min` y `max` darian lo mismo y esta
        # prueba pasaria con las dos: no probaria nada.
        assert fechas[0] != fechas[1], "los dos sellos caen en el mismo instante"
        probado = sellos.momento_probado(firma)
        assert probado is not None
        assert probado[0] == min(fechas)
        assert probado[0] != max(fechas)
