"""Banco de pruebas: comprueba que Factura-e funciona dentro del navegador.

No basta con que Pyodide arranque. Lo que hay que saber es si la compilacion
de lxml para WebAssembly trae todo lo que el validador usa, en particular el
soporte de esquemas XSD, que libxml2 se puede compilar sin el.
"""
import base64
import json
import os
import time
from datetime import date

BASE = os.environ.get("EJEMPLOS", "/ejemplos")

# Donde escribe el banco las anclas que monta. En el navegador, la raiz del
# disco virtual de Pyodide, que nace vacio con cada pagina y muere con ella.
# Fuera del navegador hay que darle una carpeta: con la raiz por defecto,
# `test_banco.py` escribia `anclas`, `anclas-tsl` y cuatro mas en la raiz del
# disco de quien corria la suite, y las reutilizaba de una vez a la siguiente.
# En Linux, donde `/` no se puede escribir, cinco comprobaciones criticas caian
# con PermissionError: asi se descubrio, al correr la suite en GitHub.
DISCO = os.environ.get("DISCO_DEL_BANCO", "/")
HOY = date(2026, 9, 20)

# Medido fuera, con CPython 3.14 y lxml 6.0.2. Ver la comprobacion de c14n.
ESPERADO_C14N = "AesuDLQkGMXkd5ZOqjQXwGzUHYaUE4/PuR5VUXJZ/Gw="

# Un par de primos para firmar en la prueba. Es de juguete: no protege nada.
P_JUGUETE = 102537101091278998115987341585599416127626670398059308299795465171831775139903
Q_JUGUETE = 68075505016498421992239704630051902902248104096335391022395579103563275678179
# --- Los sellos de tiempo --------------------------------------------------

#
# Los dos los hizo openssl, y van escritos porque aqui dentro no hay ninguno.
# El bueno esta sellado sobre SELLADO, que es el `ds:SignatureValue`
# canonicalizado de una factura firmada de verdad; asi la comprobacion pasa
# por el mismo camino que fuera: DER, RSA, sha256 y la canonicalizacion de
# esta compilacion de libxml2.
#
# El segundo es el que importa: esta perfectamente firmado y su firma
# verifica, y aun asi hay que rechazarlo, porque el certificado que lo firma
# no esta autorizado a sellar el tiempo. Es una comprobacion de
# sobre-confianza, y esas no avisan solas.

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
    "MIIGPQYJKoZIhvcNAQcCoIIGLjCCBioCAQMxDTALBglghkgBZQMEAgEwgZ4GCyqGSIb3"
    "DQEJEAEEoIGOBIGLMIGIAgEBBgQqAwQBMDEwDQYJYIZIAWUDBAIBBQAEIPaGiYg8VYPl"
    "PKtvLd78zRh8Om2I+7jsGHfmE/yrMtW1AgEDGA8yMDI2MDgyNzIyMzIxM1owCgIBAYAC"
    "AfSBAWQBAf8CCQDQ89vYlMFfKqAcpBowGDEWMBQGA1UEAwwNVFNVIGRlIHBydWViYaCC"
    "AzcwggMzMIICG6ADAgECAgEJMA0GCSqGSIb3DQEBCwUAMCExHzAdBgNVBAMMFkFDIGRl"
    "IHNlbGxvcyBkZSBwcnVlYmEwHhcNMjYwODI3MjIzMjQzWhcNMzYwODI0MjIzMjQzWjAf"
    "MR0wGwYDVQQDDBRUU1Ugc2luIGF1dG9yaXphY2lvbjCCASIwDQYJKoZIhvcNAQEBBQAD"
    "ggEPADCCAQoCggEBAMAr0OgP+uUSN+9TZbwURCNdJyol8FmnTfVldHZ4Hl4KBiWuRgCK"
    "dPg8uMTPnKrLzroC681I7c2WaHeG1QSgAzKRdTYXE18CTtI60XcKlXiTTziEsC2wOPXO"
    "ESKuHNUB9wZLdvc2UV0Gefrn2A7J2o1VNlANzkk1XQQ5q1Oe2ghZ28fZiatilPy+HtFe"
    "8jkIzk64uqjjDU3uPveCS3Db/iVIO24iEgUjOrnx/bLhr7wrcJDioj4xSKV8Lh8ijPVb"
    "Iaiij8l9oWGqCEvHZSvrkvaWYd77tOFfNgVrjoueuvdq2w6erPCOxUXxfmI9PG1GF2TQ"
    "lPWjD2bjYYriSYm/LWUCAwEAAaN4MHYwDAYDVR0TAQH/BAIwADAOBgNVHQ8BAf8EBAMC"
    "B4AwFgYDVR0lAQH/BAwwCgYIKwYBBQUHAwQwHQYDVR0OBBYEFLI9HmiIo5NMwVusCRyn"
    "jU5T+xKuMB8GA1UdIwQYMBaAFKmFTrg5WNzgllf83zXPk05Io+PSMA0GCSqGSIb3DQEB"
    "CwUAA4IBAQBKnQGe8xGHr+TnoskhQRipVjLyd383AQ5MTCMaA1DwmfacST5RSf0S1eFg"
    "+Cl/92rym1ilXpNDKZPuJUs6sK/9CANRw/idAEB5pPeofxdHKoJiIxKGxzJgAAuiqFST"
    "ab6QXRTy2L8NIjnBWZOkCh1jyFBITsV+bB61+1SRltAWMgoFbIiHZAFUozlANo6G5DAb"
    "AsDZ9AwK3ZJM21fJzr9P3+gmsH58+mzljLeh4cExSGItExFNhEAOvt8HaHGJpShoIfOA"
    "NzqL5Y8dpGuc8hllp3EtfcMWkg8nI/XkSAiK867BRk7BRj74PT/OVfllzvuvLPJ4bWoL"
    "gBRvfLnOmzo+MYICODCCAjQCAQEwJjAhMR8wHQYDVQQDDBZBQyBkZSBzZWxsb3MgZGUg"
    "cHJ1ZWJhAgEJMAsGCWCGSAFlAwQCAaCB5jAaBgkqhkiG9w0BCQMxDQYLKoZIhvcNAQkQ"
    "AQQwHAYJKoZIhvcNAQkFMQ8XDTI2MDgyNzIyMzI0NFowLwYJKoZIhvcNAQkEMSIEIPu/"
    "J3jf1ddvmNbwpCah/Hx/ps6rXUo3BcfHV0pNc64hMHkGCSqGSIb3DQEJDzFsMGowCwYJ"
    "YIZIAWUDBAEqMAsGCWCGSAFlAwQBFjALBglghkgBZQMEAQIwCgYIKoZIhvcNAwcwDgYI"
    "KoZIhvcNAwICAgCAMA0GCCqGSIb3DQMCAgFAMAcGBSsOAwIHMA0GCCqGSIb3DQMCAgEo"
    "MA0GCSqGSIb3DQEBAQUABIIBACAC1/WVUtEA6tRk4uvffk+lw8iS+PuCPuot4RFcvWJw"
    "XRM7MlmfjfUmNkaLPh/XEBEyNjx9QQDrKhNUsyAvzhcSbjAA5H/zpeRuehs8B4dSO3wq"
    "MKrss87cNWt6j1SM32cQck8LifIVS4gf721v+cl6S9pMPW49rFDKDXZFYwcRJPuacvji"
    "hD0QVvC5YH3UJC3muoTml26sqGODPUJ5d+nM0XpXmApuZlxAtBiF/eqFzmunpNCmafvl"
    "uYJ2JIxDf8XIcom5vak8o8VWAfiEgRYSBBcwoWw57EyXn3GvwoQtxp8I2mhAFmkEAC/X"
    "9JcRgjARo9XlUvHmwAcgbdZJGgI="
)

SELLADO = (
    "PG5zMDpTaWduYXR1cmVWYWx1ZSB4bWxuczpmZT0iaHR0cDovL3d3dy5mYWN0dXJhZS5n"
    "b2IuZXMvZm9ybWF0by9WZXJzaW9uZXMvRmFjdHVyYWV2M18yXzIueG1sIiB4bWxuczpu"
    "czA9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvMDkveG1sZHNpZyMiPmJYemlMeGJBYk1N"
    "OTZiMGROQU1SYnlZTXBjM2hHU1BsNHJhWlU3WUx5eEJsUG95OXU1RkVOOHUvMWl0WEJP"
    "NzJ4bjQrei80WkJMSy9tRWltUVl5TWVBPT08L25zMDpTaWduYXR1cmVWYWx1ZT4="
)

resultados = []


def comprobar(nombre, critica=False):
    def envoltorio(fn):
        arranque = time.perf_counter()
        try:
            detalle = fn() or "correcto"
            ok = True
        except Exception as error:
            detalle = "{}: {}".format(type(error).__name__, error)
            ok = False
        resultados.append({
            "nombre": nombre,
            "ok": ok,
            "critica": critica,
            "detalle": str(detalle),
            "ms": round((time.perf_counter() - arranque) * 1000, 1),
        })
        return fn
    return envoltorio


@comprobar("lxml carga en WebAssembly", critica=True)
def _():
    from lxml import etree
    return "lxml {} - libxml2 {}".format(
        ".".join(str(n) for n in etree.LXML_VERSION),
        ".".join(str(n) for n in etree.LIBXML_VERSION),
    )


@comprobar("libxml2 trae soporte de esquemas XSD", critica=True)
def _():
    # La pregunta del millon: libxml2 se puede compilar sin schemas, y
    # esquema.py entero depende de etree.XMLSchema.
    from lxml import etree
    xsd = b"""<?xml version="1.0"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
      <xs:element name="factura">
        <xs:complexType><xs:sequence>
          <xs:element name="total" type="xs:decimal"/>
        </xs:sequence></xs:complexType>
      </xs:element>
    </xs:schema>"""
    esquema = etree.XMLSchema(etree.fromstring(xsd))
    bueno = etree.fromstring(b"<factura><total>121.00</total></factura>")
    malo = etree.fromstring(b"<factura><total>ciento veintiuno</total></factura>")
    assert esquema.validate(bueno), "rechaza un documento válido"
    assert not esquema.validate(malo), "acepta un documento inválido"
    assert esquema.error_log, "no hay error_log, y de ahí salen los mensajes"
    return "compila, acepta, rechaza y explica por qué"


@comprobar("el paquete validador importa", critica=True)
def _():
    # Se recorre el paquete Y ADEMAS se comprueba que estan los que tienen que
    # estar. Las dos cosas, y por este orden de razones.
    #
    # Recorrerlo solo no vale. Se hizo asi cuando entro `revocacion`, porque
    # una lista escrita a mano se habia quedado corta; pero recorrer el
    # paquete pregunta que trae el wheel, no si el wheel es el de ahora.
    # Volvio a pasar exactamente igual con `edifact`: el .whl de dist/ era de
    # la vispera, esta comprobacion salio en verde diciendo «los 17 modulos»
    # tan tranquila, y el fallo aparecio cinco pruebas mas abajo como un
    # ImportError que no se parecia en nada a su causa.
    #
    # Una lista escrita a mano se queda corta, si; pero quedarse corta hace
    # que esto FALLE, que es lo que tiene que pasar. Recorrer el paquete hace
    # que PASE. De los dos fallos posibles, el caro es el segundo.
    #
    # Sobrar no molesta: un modulo nuevo que no este aqui no rompe nada.
    # Faltar si, y se dice cual falta y que hay que hacer.
    import importlib
    import pkgutil
    import validador
    ESPERADOS = {
        "cadena", "calendario", "codigo_unico", "edifact", "en16931",
        "esquema", "factura", "facturae", "firma", "formato", "incidencias",
        "iva", "nif", "ocsp", "revocacion", "sellos", "sintaxis", "tsl",
    }
    nombres = sorted(m.name for m in pkgutil.iter_modules(validador.__path__))
    faltan = sorted(ESPERADOS - set(nombres))
    assert not faltan, (
        "al wheel de dist/ le faltan estos módulos: {}. Suele querer decir "
        "que es de antes: python -m build --wheel --outdir dist".format(
            ", ".join(faltan))
    )
    for nombre in nombres:
        importlib.import_module("validador." + nombre)
    return "los {} módulos: {}".format(len(nombres), ", ".join(nombres))


@comprobar("el parser endurecido no expande entidades", critica=True)
def _():
    # XXE: si esto expande, una factura ajena puede leer ficheros.
    from lxml import etree
    from validador.formato import parser
    bomba = (b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "SECRETO">]>'
             b"<r>&x;</r>")
    raiz = etree.fromstring(bomba, parser=parser())
    texto = etree.tostring(raiz, encoding="unicode")
    assert "SECRETO" not in texto, "la entidad se expandió: " + texto
    return "la entidad no se expande"


@comprobar("reconoce el formato de un fichero real")
def _():
    from validador.formato import detectar_archivo
    d = detectar_archivo(BASE + "/f-0001.xml")
    assert d, d.motivo
    return "{} - {}".format(d.familia, d.version or "sin versión")


@comprobar("una factura correcta sale conforme", critica=True)
def _():
    from validador import factura
    informe = factura.validar_archivo(BASE + "/f-0001.xml", hoy=HOY)
    assert informe.validado, "no se ha llegado a mirar"
    assert informe.conforme, informe.detalle()
    return informe.resumen()


@comprobar("un abono correcto sale conforme")
def _():
    from validador import factura
    informe = factura.validar_archivo(BASE + "/r-0001.xml", hoy=HOY)
    # `validado` primero, y no es floritura: sobre un fichero que no existe
    # `conforme` responde que si -no hay errores porque no se ha mirado nada-,
    # asi que sin esta linea la comprobacion salia verde con la carpeta
    # equivocada. Es el mismo fallo que ya se arreglo en `InformeLote.conforme`
    # y que aqui habia sobrevivido.
    assert informe.validado, "no se ha llegado a mirar: " + informe.resumen()
    assert informe.conforme, informe.detalle()
    return informe.resumen()


@comprobar("una factura en CII se lee y se le cazan los fallos")
def _():
    # El nombre de antes era «una factura de otro formato (CII) tambien»,
    # detras de «una factura correcta sale conforme», y se leia como que esta
    # tambien salia conforme. No sale ni tiene que salir: cii-A-0001 esta rota
    # a proposito -dos tipos de IVA en las lineas y una sola entrada en el
    # desglose- y lo dice en su propio comentario. Lo que se comprueba aqui es
    # que la sintaxis CII se reconoce y que sus reglas se aplican.
    from validador import factura
    informe = factura.validar_archivo(BASE + "/cii-A-0001.xml", hoy=HOY)
    assert informe.validado, "no se ha reconocido"
    assert not informe.conforme, "esta factura está rota y debería saltar"
    return informe.resumen()


@comprobar("una factura rota se caza", critica=True)
def _():
    from validador import factura
    with open(BASE + "/f-0001.xml", "rb") as f:
        datos = f.read()
    roto = datos.replace(
        b'<cbc:PayableAmount currencyID="EUR">121.00',
        b'<cbc:PayableAmount currencyID="EUR">999.00',
    )
    assert roto != datos, "no se ha llegado a romper la factura"
    informe = factura.validar(roto, hoy=HOY)
    assert not informe.conforme, "un total falso ha pasado sin queja"
    return "; ".join(i.codigo for i in informe.errores)


@comprobar("el informe se lee en castellano, con tildes")
def _():
    from validador import factura
    with open(BASE + "/f-0001.xml", "rb") as f:
        datos = f.read()
    roto = datos.replace(b"<cbc:ID>F-2026-0001</cbc:ID>", b"<cbc:ID></cbc:ID>")
    texto = factura.validar(roto, hoy=HOY).detalle(norma=factura.origen)
    assert "\u00fa" in texto or "\u00f3" in texto or "\u00e9" in texto, (
        "no hay ni una tilde, algo se ha comido el UTF-8: " + texto[:200])
    return texto.splitlines()[2].strip() if len(texto.splitlines()) > 2 else texto


@comprobar("sin esquemas XSD sigue funcionando, avisando")
def _():
    from validador.esquema import Catalogo
    from pathlib import Path
    catalogo = Catalogo(carpeta=Path("/no-existe"))
    assert catalogo.vacio, "dice que tiene esquemas y no los tiene"
    return "catálogo vacío detectado, sin reventar"


@comprobar("un lote entero de una vez")
def _():
    from validador import factura
    import glob
    rutas = sorted(glob.glob(BASE + "/*.xml"))
    # Un lote de cero ficheros sale «0 correcto(s), 0 con errores» y esta
    # comprobacion daba verde con la carpeta equivocada, que es justo el fallo
    # que no puede tener un validador: dar por bueno lo que no ha visto.
    assert rutas, "no hay ni un fichero en " + BASE
    lote = factura.validar_lote(rutas, hoy=HOY)
    assert lote.informes, "el lote ha vuelto vacío"
    return "{} -> {}".format(len(rutas), lote.resumen())


@comprobar("lxml canonicaliza igual que fuera del navegador", critica=True)
def _():
    # La segunda pregunta del millon. firma.py entero depende de que
    # etree.tostring(method="c14n") de exactamente los mismos bytes aqui que en
    # CPython: si difiere en un solo byte -en como escribe un atributo, en el
    # orden de los namespaces, en los saltos de linea- el resumen sale distinto
    # y **todas** las facturas firmadas se denunciarian como manipuladas.
    #
    # El valor esperado se calculo con CPython 3.14 y lxml 6.0.2 sobre el
    # documento de aqui abajo. No es un numero magico: es la respuesta correcta
    # medida fuera.
    import hashlib, base64
    from lxml import etree
    doc = b"""<?xml version="1.0"?>
<a:raiz xmlns:a="urn:a" xmlns:b="urn:b" z="1" a="2">
  <b:hijo>  texto  con   espacios </b:hijo>
  <vacio/><!-- comentario -->
</a:raiz>"""
    octetos = etree.tostring(etree.fromstring(doc), method="c14n",
                             exclusive=False, with_comments=False)
    obtenido = base64.b64encode(hashlib.sha256(octetos).digest()).decode()
    assert obtenido == ESPERADO_C14N, (
        "canonicaliza distinto: " + obtenido + " en vez de " + ESPERADO_C14N)
    return "byte a byte igual que en CPython"


@comprobar("se verifica una firma RSA de verdad", critica=True)
def _():
    # Sin `cryptography`: pow(firma, e, n) y unas lineas de DER. Si esto
    # funciona aqui, la firma se comprueba en el navegador sin descargar nada
    # mas. Se firma con una clave de juguete y se comprueba que acepta la buena
    # y rechaza la que le cambia un byte.
    from validador import firma
    n = P_JUGUETE * Q_JUGUETE
    d = pow(65537, -1, (P_JUGUETE - 1) * (Q_JUGUETE - 1))
    tam = (n.bit_length() + 7) // 8
    import hashlib
    di = firma._DIGESTINFO["sha256"] + hashlib.sha256(b"factura").digest()
    bloque = bytes([0, 1]) + bytes([0xFF]) * (tam - len(di) - 3) + bytes([0]) + di
    valor = pow(int.from_bytes(bloque, "big"), d, n).to_bytes(tam, "big")

    class Falso:
        modulo, exponente = n, 65537
    assert firma._verificar_rsa(valor, b"factura", Falso(), "sha256"), "no acepta la buena"
    roto = bytearray(valor); roto[5] ^= 0xFF
    assert not firma._verificar_rsa(bytes(roto), b"factura", Falso(), "sha256"),         "acepta una firma manipulada"
    return "{} bits, acepta la buena y rechaza la rota".format(n.bit_length())


@comprobar("una factura firmada se valida entera")
def _():
    # De punta a punta con un fichero de verdad, si lo hay: el mismo camino que
    # sigue una factura al soltarla en la pagina.
    import glob
    from validador import factura
    firmadas = [r for r in sorted(glob.glob(BASE + "/*.xml"))
                if b"Signature" in open(r, "rb").read()]
    if not firmadas:
        return "no hay ninguna firmada entre los ejemplos"
    informe = factura.validar_archivo(firmadas[0], hoy=HOY)
    rotas = [i.codigo for i in informe.errores
             if i.codigo in ("FIRMA-ALTERADA", "FIRMA-NO-CUADRA")]
    assert not rotas, "dice que está manipulada una factura intacta: " + str(rotas)
    return firmadas[0].split("/")[-1] + " -> firma intacta"



@comprobar("la cadena de confianza se encadena aquí también", critica=True)
def _():
    # cadena.py es RSA y DER: aritmetica pura, sin nada que pueda faltar en
    # WebAssembly. Se comprueba igualmente porque el coste es cero y porque
    # «deberia funcionar» no es haberlo mirado.
    #
    # Se monta la jerarquia entera al vuelo: el propio certificado del ejemplo
    # firmado hace de ancla de si mismo, que es el caso que se puede montar sin
    # traer ningun fichero mas.
    import base64, glob
    from lxml import etree
    from validador.cadena import Almacen, construir
    from validador.firma import leer_certificado

    firmadas = [r for r in sorted(glob.glob(BASE + "/*.xml"))
                if b"Signature" in open(r, "rb").read()]
    if not firmadas:
        return "no hay ninguna firmada entre los ejemplos"
    raiz = etree.parse(firmadas[0]).getroot()
    crudo = base64.b64decode("".join(
        raiz.xpath("//*[local-name()='X509Certificate']/text()")[0].split()))
    hoja = leer_certificado(crudo)

    import os
    carpeta = os.path.join(DISCO, "anclas")
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "ejemplo.cer"), "wb") as f:
        f.write(crudo)
    almacen = Almacen(carpeta)
    assert not almacen.vacio, "no ha leído el ancla del disco virtual"
    assert almacen.contiene(hoja), "no reconoce su propio certificado"
    assert construir(hoja, almacen).llega, "no encadena hasta el ancla"

    # Y que rechaza lo que no es: un certificado con el mismo nombre pero otros
    # bytes no vale como ancla.
    otro = leer_certificado(crudo[:-1] + bytes([crudo[-1] ^ 1]))
    assert not almacen.contiene(otro), "acepta un ancla por el nombre"
    return "{} -> encadena, y rechaza la copia alterada".format(hoja.sujeto)


@comprobar("sin anclas no se inventa nada")
def _():
    from validador.cadena import Almacen, reglas
    from validador.firma import leer_certificado
    import base64, glob
    from lxml import etree
    firmadas = [r for r in sorted(glob.glob(BASE + "/*.xml"))
                if b"Signature" in open(r, "rb").read()]
    if not firmadas:
        return "no hay ninguna firmada entre los ejemplos"
    raiz = etree.parse(firmadas[0]).getroot()
    crudo = base64.b64decode("".join(
        raiz.xpath("//*[local-name()='X509Certificate']/text()")[0].split()))
    salen = reglas([leer_certificado(crudo)], Almacen("/no-hay-anclas"))
    assert [i.codigo for i in salen] == ["CADENA-SIN-ANCLAS"],         "debería avisar de que no ha comprobado nada: " + str(salen)
    return "avisa en vez de callarse"


# --- Revocacion ------------------------------------------------------------
#
# Se fabrica una CRL aqui mismo, firmada con la clave de juguete, y se le pasa
# al lector. Es DER y aritmetica, igual que la cadena, pero «deberia funcionar»
# sigue sin ser haberlo mirado.

def _der(etiqueta, contenido):
    if len(contenido) < 0x80:
        largo = bytes([len(contenido)])
    else:
        crudo = len(contenido).to_bytes((len(contenido).bit_length() + 7) // 8, "big")
        largo = bytes([0x80 | len(crudo)]) + crudo
    return bytes([etiqueta]) + largo + contenido


def _seq(*partes):
    return _der(0x30, b"".join(partes))


def _entero(valor):
    return _der(0x02, valor.to_bytes((valor.bit_length() + 8) // 8, "big"))


def _tiempo(texto):
    return _der(0x18, texto.encode())


def _lista_de_juguete(emisor_der, serie=None, delta=False):
    """Una CRL de verdad: firmada, con su numero y su motivo."""
    import hashlib
    from validador import firma
    n = P_JUGUETE * Q_JUGUETE
    d = pow(65537, -1, (P_JUGUETE - 1) * (Q_JUGUETE - 1))
    oid = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x01, 0x0B])

    lineas = b""
    if serie is not None:
        motivo = _seq(_seq(_der(0x06, bytes([0x55, 0x1D, 0x15])),
                           _der(0x04, _der(0x0A, bytes([1])))))
        lineas = _seq(_seq(_entero(serie), _tiempo("20260101000000Z"), motivo))
    extensiones = [_seq(_der(0x06, bytes([0x55, 0x1D, 0x14])),
                        _der(0x04, _entero(1)))]
    if delta:
        extensiones.append(_seq(_der(0x06, bytes([0x55, 0x1D, 0x1B])),
                                _der(0x01, bytes([0xFF])),
                                _der(0x04, _entero(1))))
    tbs = _seq(
        _entero(1),
        _seq(_der(0x06, oid)),
        emisor_der,
        _tiempo("20260901000000Z"),
        _tiempo("20271001000000Z"),
        lineas,
        _der(0xA0, _seq(*extensiones)),
    )
    tam = (n.bit_length() + 7) // 8
    di = firma._DIGESTINFO["sha256"] + hashlib.sha256(tbs).digest()
    bloque = bytes([0, 1]) + bytes([0xFF]) * (tam - len(di) - 3) + bytes([0]) + di
    valor = pow(int.from_bytes(bloque, "big"), d, n).to_bytes(tam, "big")
    return _seq(tbs, _seq(_der(0x06, oid)), _der(0x03, bytes([0]) + valor))


def _respuesta_de_juguete(cert):
    """Una respuesta OCSP de verdad: firmada, con su CertID y su motivo.

    El `CertID` no lleva el certificado dentro: lleva el numero de serie y dos
    resumenes del emisor —de su nombre y de su clave—. Se calculan aqui, que es
    la parte que de verdad hay que ver funcionar dentro de WebAssembly: es el
    unico sitio del validador donde entra SHA-1, y no por descuido sino porque
    el RFC 6960 lo fija para esto.
    """
    import hashlib
    from validador import firma
    from validador.ocsp import _clave_cruda
    n = P_JUGUETE * Q_JUGUETE
    d = pow(65537, -1, (P_JUGUETE - 1) * (Q_JUGUETE - 1))
    oid_rsa = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x01, 0x0B])
    oid_sha1 = bytes([0x2B, 0x0E, 0x03, 0x02, 0x1A])
    oid_basica = bytes([0x2B, 0x06, 0x01, 0x05, 0x05, 0x07, 0x30, 0x01, 0x01])

    certid = _seq(
        _seq(_der(0x06, oid_sha1), _der(0x05, b"")),
        _der(0x04, hashlib.sha1(cert.sujeto_der).digest()),
        _der(0x04, hashlib.sha1(_clave_cruda(cert)).digest()),
        _entero(cert.serie),
    )
    # revoked [1] IMPLICIT, con su fecha y su motivo: clave comprometida.
    anulado = _der(0xA1, _tiempo("20260101000000Z")
                   + _der(0xA0, _der(0x0A, bytes([1]))))
    single = _seq(certid, anulado, _tiempo("20260901000000Z"))
    datos = _seq(_der(0xA1, cert.sujeto_der), _tiempo("20260901000000Z"),
                 _seq(single))

    tam = (n.bit_length() + 7) // 8
    di = firma._DIGESTINFO["sha256"] + hashlib.sha256(datos).digest()
    bloque = bytes([0, 1]) + bytes([0xFF]) * (tam - len(di) - 3) + bytes([0]) + di
    valor = pow(int.from_bytes(bloque, "big"), d, n).to_bytes(tam, "big")
    basica = _seq(datos, _seq(_der(0x06, oid_rsa), _der(0x05, b"")),
                  _der(0x03, bytes([0]) + valor))
    return _seq(_der(0x0A, bytes([0])),
                _der(0xA0, _seq(_der(0x06, oid_basica), _der(0x04, basica))))


def _certificado_del_ejemplo():
    import base64, glob
    from lxml import etree
    from validador.firma import leer_certificado
    firmadas = [r for r in sorted(glob.glob(BASE + "/*.xml"))
                if b"Signature" in open(r, "rb").read()]
    if not firmadas:
        return None
    raiz = etree.parse(firmadas[0]).getroot()
    crudo = base64.b64decode("".join(
        raiz.xpath("//*[local-name()='X509Certificate']/text()")[0].split()))
    return leer_certificado(crudo)


@comprobar("el informe declara de dónde salen las anclas", critica=True)
def _():
    # Esta es la condicion que hace aceptable que la pagina traiga las anclas
    # puestas: la decision de en quien creer la toma la pagina y no quien lee
    # el informe, asi que hay que decirsela. Sin esta linea, traerlas seria
    # fabricar confianza en silencio, que es lo que este validador existe para
    # no hacer. Aqui va sin tildes por seguir el fichero; en la pagina de
    # verdad la frase se escribe bien.
    import os
    from validador.cadena import Almacen, reglas
    hoja = _certificado_del_ejemplo()
    if hoja is None:
        return "no hay ninguna firmada entre los ejemplos"

    carpeta = os.path.join(DISCO, "anclas-pagina")
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, "ejemplo.cer"), "wb") as f:
        f.write(hoja.der)
    almacen = Almacen(carpeta, procedencia="viene con la página")

    notas = [i for i in reglas([hoja], almacen) if i.gravedad == "nota"]
    assert len(notas) == 1, "no declara nada: " + str(notas)
    nota = notas[0]
    assert nota.codigo == "CONFIANZA-ANCLA", nota.codigo
    assert "viene con la página" in nota.mensaje, nota.mensaje
    assert hoja.huella() in nota.mensaje, "no deja constancia de la huella"
    # Y que no se cuela la ruta del disco virtual, que a quien lee no le dice
    # nada y encima suena a que el ancla la puso el.
    assert "anclas-pagina" not in nota.mensaje, nota.mensaje
    return "dice de dónde viene el ancla y con qué huella"


@comprobar("una lista de revocación se lee y se comprueba aquí", critica=True)
def _():
    from validador.revocacion import comprobar as comprobar_revocacion
    from validador.revocacion import leer_lista
    hoja = _certificado_del_ejemplo()
    if hoja is None:
        return "no hay ninguna firmada entre los ejemplos"

    crudo = _lista_de_juguete(hoja.emisor_der, serie=hoja.serie)
    una = leer_lista(crudo)
    assert len(una.anulaciones) == 1, "no ha leído la línea de anulados"
    assert una.anulaciones[hoja.serie].compromiso, "no ha leído el motivo"

    salida = comprobar_revocacion(hoja, hoja, [una])
    assert salida.estado == "anulado", "no lo da por anulado: " + salida.estado

    # Y lo que de verdad importa: que no se crea una lista que no cuadra. Se le
    # cambia un byte a la firma y tiene que dejar de valer, no colar como un
    # «no aparece, luego esta vigente».
    roto = bytearray(crudo); roto[-3] ^= 0xFF
    otra = comprobar_revocacion(hoja, hoja, [leer_lista(bytes(roto))])
    assert otra.estado == "sin_saber", "se cree una lista con la firma rota"
    assert "no la firmo" in otra.motivo.replace("ó", "o"), otra.motivo
    return "lee la lista, la verifica y rechaza la manipulada"


@comprobar("una respuesta OCSP del documento se verifica aquí", critica=True)
def _():
    # Un XAdES-XL moderno guarda respuestas OCSP y a menudo no guarda CRL, asi
    # que sin esto la revocacion de esos documentos no se comprueba nunca. Se
    # leen sin salir a la red: vienen dentro del fichero.
    #
    # Y lo que hay que ver aqui es lo mismo que con la lista: que **no se cree
    # la que no cuadra**. La respuesta la mete en el documento quien firma, asi
    # que sin verificarla cualquiera adjunta un «este certificado esta
    # perfectamente» escrito por si mismo.
    from validador import ocsp
    from validador.revocacion import comprobar_ocsp
    hoja = _certificado_del_ejemplo()
    if hoja is None:
        return "no hay ninguna firmada entre los ejemplos"

    crudo = _respuesta_de_juguete(hoja)
    una = ocsp.leer_respuesta(crudo)
    assert una.correcta, "no ha leído la respuesta: " + una.que_paso
    assert len(una.estados) == 1, "no ha leído el estado del certificado"
    assert ocsp.casa_con(una.estados[0], hoja, hoja),         "el CertID no cuadra: SHA-1 no da lo mismo aquí dentro"

    salida = comprobar_ocsp(hoja, hoja, [una])
    assert salida.estado == "anulado", "no lo da por anulado: " + salida.estado
    assert salida.ocsp is not None, "no dice de qué respuesta lo ha sacado"

    roto = bytearray(crudo); roto[-3] ^= 0xFF
    otra = comprobar_ocsp(hoja, hoja, [ocsp.leer_respuesta(bytes(roto))])
    assert otra.estado == "sin_saber", "se cree una respuesta con la firma rota"
    return "lee la respuesta, la verifica y rechaza la manipulada"


@comprobar("una lista incremental no da a nadie por vigente")
def _():
    # El fallo mas traicionero de esta parte: una CRL delta parece una lista
    # normal, y quien la lea como completa dara por vigente a todo el que no
    # aparezca en ella.
    from validador.revocacion import comprobar as comprobar_revocacion
    from validador.revocacion import leer_lista
    hoja = _certificado_del_ejemplo()
    if hoja is None:
        return "no hay ninguna firmada entre los ejemplos"

    completa = leer_lista(_lista_de_juguete(hoja.emisor_der))
    assert comprobar_revocacion(hoja, hoja, [completa]).estado == "vigente",         "una lista completa y limpia debería poder decir que está vigente"

    incremental = leer_lista(_lista_de_juguete(hoja.emisor_der, delta=True))
    salida = comprobar_revocacion(hoja, hoja, [incremental])
    assert salida.estado == "sin_saber", "da por vigente con una lista delta"
    return "distingue la completa de la incremental"


# --- Curva eliptica --------------------------------------------------------
#
# 46 de las 129 autoridades cualificadas concedidas de la lista espanola firman
# con curva. Aqui hay dos preguntas: si la aritmetica da lo mismo dentro de
# WebAssembly -es aritmetica de enteros, deberia, pero «deberia» no es haberlo
# mirado- y **cuanto tarda**, que es lo unico nuevo que puede doler: P-521 es
# lo mas caro que hace este validador.
#
# Los vectores son fijos y salieron de openssl fuera del navegador. Empotrados
# a proposito: un vector generado aqui mismo comprobaria que el codigo se da la
# razon a si mismo, que es justo lo que no interesa.

VECTORES = {
    "P-256": ("sha256",
      "3f4310e25cdd32d2b0464cdc08a58876e6e7b612e0c77da696b0bf12d9df14ba",
      "0d7d7921416a46c86b5699f782d6f3458705c05918000e03d72979c29f247d55",
      "0dbb464221f4af5e560e31ee889985528eb872792f1646f67763e9c90714b0c2"
      "6aef14886e62fd0aac78f05d8540f658a00b02fe9a1ab4ef8f6b66a3b6348024"),
    "P-384": ("sha384",
      "0782e67f240f76d08090a0ca80b4d2a056afa12d0af719d35c0dfd8a415968f3"
      "c746cb599937e6ad94bf812d90191a8a",
      "b4749c814d31e0b3bf1827b752e9bcd65cb93ef4e1689183f1e7f88c8c6186ab"
      "d3dc399e2ac4cfac1a590c65824a4e17",
      "70af1effeec721f961a6e08c921aba9460f07cca0f26ade858eb2bda21bc9fed"
      "4663017133b0165dc7f89e087da82fe954af71ecdbe21213e56accb821f9e22b"
      "f8d95f9868749d26a143852c1d13fa90a8bb4e2a2185caa473ef04b479ec09a2"),
    "P-521": ("sha512",
      "01feeaa639b99d584a8dfa50042918a09b8ae0001bc4330aeb9474e7b56609493"
      "045aff6329aa6a8bb982ae12587c0e6e22d2bcffebc457a6a49df296688b45ee45d",
      "007574d036548894048c1cd3eb32a0b4908806d21d104b555fe09bc557b1c742a"
      "8846fed33aea16df5af7d9a8b9ed71013832ba66ab2c00335ec8a6080e13196dc1a",
      "0117499aaf2292a8a56620a844b35a0b70025acd6d50735906ee01f8386bb7b00"
      "6936116c8aa3932cdf8f37a3fee2cb9c7df4d8901dc95522f26c912474489c3c77"
      "301204d2ac9a853b6c326abafffce6f582ab947a4d749192fee4304de8f842fd8a"
      "1ef79da69bf359ef52f9c010239942873ea4f97731ad976d9f37d857bb6f4bd33a5"),
}
MENSAJE_DEL_VECTOR = b"Factura-e: vector fijo para la prueba del navegador"


@comprobar("se verifica una firma de curva elíptica", critica=True)
def _():
    from validador.firma import CURVAS_POR_NOMBRE, Certificado, verificar
    tiempos = []
    for nombre, (alg, x, y, firmada) in VECTORES.items():
        curva = CURVAS_POR_NOMBRE[nombre]
        cert = Certificado(
            modulo=0, exponente=0, desde=None, hasta=None, sujeto="Vector",
            algoritmo_clave="ecdsa", curva=nombre,
            punto=(int(x, 16), int(y, 16)),
        )
        assert curva.encima(*cert.punto), nombre + ": el punto no está en la curva"
        valor = bytes.fromhex(firmada)
        arranque = time.perf_counter()
        ok = verificar(valor, MENSAJE_DEL_VECTOR, cert, alg, concatenada=True)
        tiempos.append("%s %.0f ms" % (nombre, (time.perf_counter() - arranque) * 1000))
        assert ok, nombre + ": no verifica una firma buena de openssl"
        # Y que no se traga la misma firma sobre otro mensaje.
        assert not verificar(valor, MENSAJE_DEL_VECTOR + b"!", cert, alg,
                             concatenada=True), nombre + ": acepta otro mensaje"
    return ", ".join(tiempos)


@comprobar("las curvas son las de verdad, también aquí", critica=True)
def _():
    # Los parametros van escritos a mano en el codigo. Si el wheel trajera una
    # version con una errata, las firmas de curva dejarian de verificar y el
    # informe diria «no llega a ninguna autoridad conocida» sobre un tercio de
    # las autoridades espanolas, sin decir por que.
    from validador.firma import CURVAS
    for curva in CURVAS.values():
        assert curva.encima(curva.gx, curva.gy), curva.nombre + ": G fuera"
    return "%d curvas, con su generador en su sitio" % len(CURVAS)


# --- La lista de confianza -------------------------------------------------
#
# De aqui salen las anclas, asi que es el sitio donde equivocarse sale en
# verde. Lo que se comprueba aqui no es que lea el XML: es que **se niegue**.
# Ademas depende de la canonicalizacion, que es lo mas fragil de esta
# compilacion —libxml2 es 2.9.10 aqui y 2.11.9 fuera—: si escribiera un byte
# distinto, la lista se rechazaria y la pagina se quedaria sin anclas.


def _certificado_de_juguete(sujeto="Ministerio de juguete"):
    """Un X.509 autofirmado con la clave de juguete, para firmar la lista."""
    import hashlib
    from validador import firma
    n = P_JUGUETE * Q_JUGUETE
    d = pow(65537, -1, (P_JUGUETE - 1) * (Q_JUGUETE - 1))
    oid = bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x01, 0x0B])
    nombre = _seq(_der(0x31, _seq(
        _der(0x06, bytes([0x55, 0x04, 0x03])), _der(0x0C, sujeto.encode()))))
    spki = _seq(
        _seq(_der(0x06, bytes([0x2A, 0x86, 0x48, 0x86, 0xF7, 0x0D, 0x01, 0x01,
                               0x01])), _der(0x05, b"")),
        _der(0x03, bytes([0]) + _seq(_entero(n), _entero(65537))),
    )
    tbs = _seq(
        _der(0xA0, _entero(2)), _entero(7), _seq(_der(0x06, oid)), nombre,
        _seq(_tiempo("20250101000000Z"), _tiempo("20300101000000Z")),
        nombre, spki,
    )
    tam = (n.bit_length() + 7) // 8
    di = firma._DIGESTINFO["sha256"] + hashlib.sha256(tbs).digest()
    bloque = bytes([0, 1]) + bytes([0xFF]) * (tam - len(di) - 3) + bytes([0]) + di
    valor = pow(int.from_bytes(bloque, "big"), d, n).to_bytes(tam, "big")
    return _seq(tbs, _seq(_der(0x06, oid)), _der(0x03, bytes([0]) + valor))


def _huella(der):
    import hashlib
    crudo = hashlib.sha256(der).hexdigest().upper()
    return ":".join(crudo[i:i + 2] for i in range(0, len(crudo), 2))


def _tsl_de_juguete(firmante_der, ancla_der, estado="granted",
                    tipo="http://uri.etsi.org/TrstSvc/Svctype/CA/QC"):
    """Una lista de confianza ETSI TS 119 612 firmada de verdad."""
    import base64, hashlib
    from lxml import etree
    from validador import firma
    NS = "http://uri.etsi.org/02231/v2#"
    DS = "http://www.w3.org/2000/09/xmldsig#"

    def t(padre, nombre, texto=None):
        hijo = etree.SubElement(padre, "{%s}%s" % (NS, nombre))
        if texto is not None:
            hijo.text = texto
        return hijo

    raiz = etree.Element("{%s}TrustServiceStatusList" % NS)
    cab = t(raiz, "SchemeInformation")
    t(cab, "TSLSequenceNumber", "3")
    t(cab, "TSLType",
      "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric")
    t(t(cab, "SchemeOperatorName"), "Name", "Ministerio de juguete")
    t(cab, "SchemeTerritory", "ES")
    t(cab, "ListIssueDateTime", "2026-08-01T00:00:00Z")
    t(t(cab, "NextUpdate"), "dateTime", "2026-11-01T00:00:00Z")

    prov = t(t(raiz, "TrustServiceProviderList"), "TrustServiceProvider")
    t(t(t(prov, "TSPInformation"), "TSPName"), "Name",
      "Certificadora de juguete")
    serv = t(t(t(prov, "TSPServices"), "TSPService"), "ServiceInformation")
    t(serv, "ServiceTypeIdentifier", tipo)
    t(t(serv, "ServiceName"), "Name", "AC de juguete")
    ident = t(serv, "ServiceDigitalIdentity")
    t(t(ident, "DigitalId"), "X509Certificate",
      base64.b64encode(ancla_der).decode())
    t(serv, "ServiceStatus",
      "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/" + estado)
    t(serv, "StatusStartingTime", "2016-07-01T00:00:00Z")

    def c14n(nodo):
        return etree.tostring(nodo, method="c14n", exclusive=False,
                              with_comments=False)

    def resumen(octetos):
        return base64.b64encode(hashlib.sha256(octetos).digest()).decode()

    del_doc = resumen(c14n(raiz))
    ds = lambda n_: "{%s}%s" % (DS, n_)  # noqa: E731
    f = etree.SubElement(raiz, ds("Signature"))
    si = etree.SubElement(f, ds("SignedInfo"))
    etree.SubElement(si, ds("CanonicalizationMethod")).set(
        "Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
    etree.SubElement(si, ds("SignatureMethod")).set(
        "Algorithm", "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256")
    ref = etree.SubElement(si, ds("Reference"))
    ref.set("URI", "")
    trs = etree.SubElement(ref, ds("Transforms"))
    etree.SubElement(trs, ds("Transform")).set(
        "Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature")
    etree.SubElement(ref, ds("DigestMethod")).set(
        "Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    etree.SubElement(ref, ds("DigestValue")).text = del_doc

    n = P_JUGUETE * Q_JUGUETE
    d = pow(65537, -1, (P_JUGUETE - 1) * (Q_JUGUETE - 1))
    tam = (n.bit_length() + 7) // 8
    di = firma._DIGESTINFO["sha256"] + hashlib.sha256(c14n(si)).digest()
    bloque = bytes([0, 1]) + bytes([0xFF]) * (tam - len(di) - 3) + bytes([0]) + di
    valor = pow(int.from_bytes(bloque, "big"), d, n).to_bytes(tam, "big")
    etree.SubElement(f, ds("SignatureValue")).text = base64.b64encode(
        valor).decode()
    datos = etree.SubElement(etree.SubElement(f, ds("KeyInfo")), ds("X509Data"))
    etree.SubElement(datos, ds("X509Certificate")).text = base64.b64encode(
        firmante_der).decode()
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


@comprobar("una lista de confianza se comprueba y se monta aquí", critica=True)
def _():
    import os
    from validador import tsl
    from validador.cadena import Almacen, reglas
    hoja = _certificado_del_ejemplo()
    if hoja is None:
        return "no hay ninguna firmada entre los ejemplos"

    cert = _certificado_de_juguete()
    una = tsl.leer(_tsl_de_juguete(cert, hoja.der))
    assert una.territorio == "ES", una.territorio
    # El nombre con sus espacios: `"".join(x.split())` los borraba y dejaba
    # «Ministeriodejuguete» en el informe de cada factura.
    assert una.operador == "Ministerio de juguete", una.operador

    fallo = tsl.comprobar_firma(una, [_huella(cert)])
    assert fallo == "", "no se cree una lista buena: " + fallo

    carpeta = os.path.join(DISCO, "anclas-tsl")
    os.makedirs(carpeta, exist_ok=True)
    resumen = tsl.montar(una, carpeta)
    assert resumen.escritas == 1, resumen.escritas

    almacen = Almacen(carpeta)
    assert almacen.contiene(hoja), "lo montado no sirve de ancla"
    notas = [i for i in reglas([hoja], almacen)
             if i.gravedad == "nota" and i.codigo == "CONFIANZA-ANCLA"]
    assert len(notas) == 1, "no declara de donde sale: " + str(notas)
    assert "lista de confianza de ES" in notas[0].mensaje, notas[0].mensaje
    return "verifica la lista, monta el ancla y dice de dónde sale"


@comprobar("una lista de confianza manipulada no monta nada", critica=True)
def _():
    # Lo que de verdad importa de este modulo. Un almacen de anclas mal montado
    # no da un error: da un aprobado.
    from validador import tsl
    hoja = _certificado_del_ejemplo()
    if hoja is None:
        return "no hay ninguna firmada entre los ejemplos"
    cert = _certificado_de_juguete()
    datos = _tsl_de_juguete(cert, hoja.der)

    tocada = datos.replace(b"Ministerio de juguete", b"Ministerio del timo")
    assert tocada != datos, "no se ha podido tocar la lista"
    fallo = tsl.comprobar_firma(tsl.leer(tocada), [_huella(cert)])
    assert "se ha modificado" in fallo, "se cree una lista tocada: " + fallo

    # Y sin decir quien tenia que firmarla, tampoco: verificarla contra el
    # certificado que ella misma trae dentro no demuestra nada.
    otra = tsl.leer(datos)
    assert "no se ha dicho" in tsl.comprobar_firma(otra, [])
    try:
        tsl.montar(otra, os.path.join(DISCO, "anclas-coladas"))
    except ValueError:
        pass
    else:
        raise AssertionError("monta anclas de una lista sin comprobar")
    return "rechaza la tocada y se niega sin firmante"



@comprobar("una autoridad retirada solo vale para lo de antes", critica=True)
def _():
    # Es una comprobacion de sobre-confianza, que son las que no avisan: si la
    # ventana no se aplicara aqui, 135 autoridades retiradas pasarian a ser
    # autoridades de confianza sin fecha de caducidad, y el informe no diria
    # nada raro.
    import datetime
    import os
    from validador import tsl
    from validador.cadena import Almacen, CARPETA_DE_RETIRADAS
    hoja = _certificado_del_ejemplo()
    if hoja is None:
        return "no hay ninguna firmada entre los ejemplos"

    cert = _certificado_de_juguete()
    una = tsl.leer(_tsl_de_juguete(cert, hoja.der, estado="withdrawn"))
    assert tsl.comprobar_firma(una, [_huella(cert)]) == "", "no se cree la lista"

    destino = os.path.join(DISCO, "anclas-retiradas")
    os.makedirs(destino, exist_ok=True)
    resumen = tsl.montar(una, destino)
    assert resumen.escritas == 0, "una retirada no es un ancla vigente"
    assert resumen.escritas_retiradas == 1, resumen.escritas_retiradas
    assert os.path.isdir(destino + "/" + CARPETA_DE_RETIRADAS), "sin subcarpeta"

    almacen = Almacen(destino)
    assert almacen.retirada(hoja), "no la reconoce como retirada"
    utc = datetime.timezone.utc
    antes = datetime.datetime(2015, 1, 1, tzinfo=utc)
    despues = datetime.datetime(2020, 1, 1, tzinfo=utc)
    assert almacen.vale_para(hoja, antes) == "", "no vale para lo de antes"
    assert almacen.vale_para(hoja, despues), "vale para lo de después, y no debe"
    assert almacen.vale_para(hoja, None), "vale sin fecha, y no debe"

    # Y sin la tabla de estados no se usa: es lo que hace que copiar la carpeta
    # a medias no convierta las retiradas en anclas de confianza.
    os.remove(destino + "/ESTADOS.tsv")
    almacen.recargar()
    assert almacen.vale_para(hoja, antes), "sin tabla se la da por buena"
    return "vale antes del 01-07-2016, no después, y sin la tabla no vale"


@comprobar("un sello de tiempo se lee y se comprueba aquí", critica=True)
def _():
    from validador import cifras, sellos
    sello = sellos.leer(base64.b64decode(SELLO_BUENO))
    assert sello.momento is not None, "no se lee la fecha"
    assert sello.firmante is not None, "no encuentra el certificado de la TSA"
    motivo = sellos.comprobar(sello)
    assert motivo == "", "no se cree un sello bueno: " + motivo
    sellado = base64.b64decode(SELLADO)
    motivo = sellos.cubre(sello, sellado)
    assert motivo == "", "no ata el sello a lo que selló: " + motivo
    # Y que no se lo trague sobre otra cosa, que es de lo que sirve.
    assert sellos.cubre(sello, sellado + b" "), "acepta el sello sobre otros bytes"
    return "sello de %s del %s" % (sello.quien, cifras.fecha(sello.momento))


@comprobar("un sello sin permiso para sellar no vale", critica=True)
def _():
    # La firma de este sello es correcta y cubre lo mismo que el bueno. Lo
    # unico que le pasa es que su certificado no esta autorizado a sellar el
    # tiempo. Si esta comprobacion se afloja, cualquiera con un certificado de
    # firma corriente se fabrica la fecha que quiera, y la fecha es de lo que
    # cuelgan la caducidad y la revocacion.
    from validador import sellos
    from validador.firma import verificar
    sello = sellos.leer(base64.b64decode(SELLO_SIN_PERMISO))
    mensaje = b"\x31" + sello.atributos_der[1:]
    assert verificar(sello.valor_firma, mensaje, sello.firmante,
                     sello.resumen_firma), "la firma del vector debería valer"
    assert sellos.cubre(sello, base64.b64decode(SELLADO)) == "", "no cubre lo mismo"
    motivo = sellos.comprobar(sello)
    assert "sellar el tiempo" in motivo, "lo da por bueno: " + repr(motivo)
    return "firma válida, permiso no: se rechaza"


@comprobar("las anclas de sellado van aparte de las de firma", critica=True)
def _():
    # Otra de sobre-confianza. En la lista espanola hay 121 anclas de sellado y
    # solo 2 estan tambien entre las de firma: las otras 119 son autoridades que
    # el Estado tiene por cualificadas para sellar el tiempo y **no** para
    # avalar la firma de una factura, y once de ellas son autoridades de
    # certificacion. Si las dos carpetas se juntaran, esas once pasarian a
    # poder emitir certificados que el validador aceptaria como firmantes de
    # facturas, y nada en el informe lo diria.
    import os
    from validador import tsl
    from validador.cadena import Almacen, SUFIJO_DE_SELLOS
    hoja = _certificado_del_ejemplo()
    if hoja is None:
        return "no hay ninguna firmada entre los ejemplos"

    cert = _certificado_de_juguete()
    una = tsl.leer(_tsl_de_juguete(cert, hoja.der, tipo=tsl.SELLADO_CUALIFICADO))
    assert tsl.comprobar_firma(una, [_huella(cert)]) == "", "no se cree la lista"

    # Con los tipos de siempre no sale nada: una autoridad de sellado no es una
    # autoridad de certificacion, y montarla ahi seria ampliar la confianza.
    destino = os.path.join(DISCO, "anclas-mezcla")
    os.makedirs(destino, exist_ok=True)
    assert tsl.montar(una, destino).escritas == 0, "monta un sellador como CA"

    sellado = destino + SUFIJO_DE_SELLOS
    os.makedirs(sellado, exist_ok=True)
    resumen = tsl.montar(una, sellado, tsl.TIPOS_QUE_SELLAN)
    assert resumen.escritas == 1, resumen.escritas

    # Y el almacen encuentra la carpeta hermana sin que nadie se lo diga, pero
    # no mete lo de una en la otra.
    almacen = Almacen(destino)
    assert str(almacen.sellos.carpeta).replace("\\", "/").endswith(SUFIJO_DE_SELLOS)
    assert almacen.vacio, "la de firma no está vacía"
    assert not almacen.sellos.vacio, "la de sellado sí debería tener algo"
    assert not almacen.contiene(hoja), "un ancla de sellado avala una firma"
    assert almacen.sellos.contiene(hoja), "no reconoce su propia ancla de sellado"
    return "el sellador no entra entre las de firma, y se encuentra al lado"


# --- EDIFACT ---------------------------------------------------------------


@comprobar("un EDIFACT plano se lee y se valida aquí", critica=True)
def _():
    """El cuarto formato de la ley, y el unico que no es XML.

    Se parte a mano, en Python puro, asi que aqui no deberia haber sorpresas.
    Lo que si las puede dar es lo de despues: el arbol se monta con lxml y se
    lee con XPath, y de eso se encarga la comprobacion siguiente.
    """
    from validador import factura

    informe = factura.validar_archivo(BASE + "/edi-0001.edi", hoy=HOY)
    assert informe.deteccion.familia == "EDIFACT", informe.deteccion.resumen()
    assert informe.deteccion.version == "96A", informe.deteccion.version
    assert informe.deteccion.conforme_en16931, "no ve el perfil"
    errores = [i.codigo for i in informe.incidencias if i.gravedad == "error"]
    assert not errores, errores
    return "una factura EDIFACT correcta sale correcta"


@comprobar("las rutas de EDIFACT valen con este libxml2", critica=True)
def _():
    """Aqui esta el riesgo de verdad de EDIFACT en el navegador.

    El mapa de EDIFACT no puede nombrar los grupos, porque su numeracion
    cambia con la version del directorio, asi que pregunta por lo que hay
    dentro: «el grupo que contiene un S_LIN». Eso sale con predicados y con el
    eje `self::`, que es mas XPath del que usan UBL y CII, y esta compilacion
    de libxml2 es mas vieja que la de fuera.

    Si algo de esto no funcionara aqui, el validador no daria error: daria una
    factura sin lineas y sin desglose, o sea sin nada que comprobar, y diria
    que esta bien.
    """
    from lxml import etree
    from validador import edifact, sintaxis

    with open(BASE + "/edi-0001.edi", "rb") as f:
        raiz, _ = edifact.convertir(f.read())
    mapa = sintaxis.SINTAXIS_EDIFACT

    assert len(raiz.xpath(mapa.lineas)) == 2, "no encuentra las dos líneas"
    assert len(raiz.xpath(mapa.desglose)) == 1, "no encuentra el desglose"
    assert len(raiz.xpath(mapa.cargos)) == 1, "no encuentra el cargo"
    assert sintaxis.texto(raiz, mapa.vendedor_nombre, mapa) == (
        "Suministros Ibericos SL"
    )
    assert sintaxis.importe(raiz, mapa.con_impuestos, mapa) is not None

    # El eje `self::` con un filtro y una subida, que es lo mas raro del mapa.
    grupo = raiz.xpath(mapa.desglose)[0]
    assert grupo.xpath(mapa.desglose_motivo) == [], "un tipo general sin exención"

    # Y el `SIN_MAPA`, que tiene que no encontrar nada nunca.
    assert raiz.xpath(sintaxis.SIN_MAPA) == []
    return "predicados, ejes y subidas funcionan igual que fuera"


@comprobar("un intercambio cortado se caza por la cuenta")
def _():
    """Lo unico que delata un EDIFACT al que le falta un trozo.

    Los segmentos que quedan estan bien formados, asi que no hay error de
    lectura por ninguna parte. Lo que no sale es la cuenta que el propio
    mensaje declara en su UNT.
    """
    from validador import factura

    informe = factura.validar_archivo(BASE + "/edi-0002-cortado.edi", hoy=HOY)
    codigos = [i.codigo for i in informe.incidencias]
    assert "EDI-MENSAJE-DESCONTADO" in codigos, codigos
    return "el UNT no cuadra y se dice"


@comprobar("un UNA de cinco caracteres se lee igual", critica=True)
def _():
    """La norma manda seis caracteres de servicio y hay quien escribe cinco.

    Se salta el hueco reservado: «UNA:+.?'UNB...». De 64 ficheros EDIFACT
    ajenos, 23 lo hacen. Sin leerlo bien, el terminador que sale es la «U»
    del UNB, el fichero se parte por cada letra U, no aparece ningun UNH y la
    respuesta es «este fichero no trae ningun mensaje» sobre una factura
    entera. Es critica porque el fallo no se ve: no hay excepcion ninguna,
    hay una frase bien escrita que dice algo falso.
    """
    from validador import factura

    informe = factura.validar_archivo(BASE + "/edi-0003-una-de-cinco.edi", hoy=HOY)
    codigos = [i.codigo for i in informe.incidencias]
    assert "EDI-UNA-DE-CINCO" in codigos, codigos
    assert "EDI-SIN-MENSAJE" not in codigos, codigos
    assert not [i for i in informe.incidencias if i.gravedad == "error"], codigos
    return "se lee la factura entera y se dice que el UNA venía de cinco"


@comprobar("un separador sin soltar no tumba el lote", critica=True)
def _():
    """Un apostrofo dentro de un dato parte el segmento por la mitad.

    El trozo de detras no es un segmento, y montar un elemento XML con su
    «etiqueta» levantaba un ValueError de lxml que no salia por el informe
    sino por la consola, llevandose por delante los demas ficheros. Aqui se
    comprueba lo mismo dentro del navegador, donde una excepcion no atrapada
    deja la pagina sin respuesta.
    """
    from validador import factura

    roto = (
        b"UNB+UNOC:2+A+B+260304:0930+1'"
        b"UNH+1+INVOIC:D:96A:UN'BGM+380+F1'"
        b"LIN+1'IMD+L+050+:::Cesky Casopis'a Historicky'MOA+203:100'"
        b"UNS+S'MOA+79:100'UNT+8+1'UNZ+1+1'"
    )
    informe = factura.validar(roto, hoy=HOY)
    codigos = [i.codigo for i in informe.incidencias]
    assert "EDI-ETIQUETA-IMPOSIBLE" in codigos, codigos
    return "se aparta el trozo roto, se dice, y no revienta nada"


# --- Lo que la pagina trae puesto ------------------------------------------


@comprobar("la promesa del informe cuadra con los esquemas y las anclas que hay", critica=True)
def _():
    """La frase del final dice de que se ha fiado quien lee el informe.

    Es la unica comprobacion de aqui que vale con paquete y sin el, porque no
    mira si hay esquemas y anclas sino si lo que el informe dice haber mirado
    es lo que habia con que mirarlo. Prometer de mas es el peor fallo que
    puede tener un informe; prometer de menos, esconder trabajo hecho.
    """
    from validador import factura
    from validador.cadena import Almacen
    from validador.esquema import Catalogo

    # Con una firmada, que si no la mitad de la frase no llega a escribirse:
    # las anclas solo se prometen si hay algo que contrastar con ellas, y en
    # un lote sin firmas no se promete ninguna aunque esten instaladas.
    catalogo = Catalogo.por_defecto()
    almacen = Almacen.por_defecto()
    lote = factura.validar_lote(
        [BASE + "/fe-0001.xml"], hoy=HOY, catalogo=catalogo, almacen=almacen
    )
    dice = lote.alcance(forma=not catalogo.vacio, anclas=not almacen.vacio)
    assert ("esquema XSD" in dice) == (not catalogo.vacio), dice
    # Con anclas puestas no puede echarlas de menos, y sin ellas no puede
    # callarse que faltan.
    #
    # Las frases son las del 05-10-2026, cuando dejaron de decir «instaladas»
    # (en la pagina no se instala nada). Con las de antes esto se quedo
    # buscando lo que ya no se escribe: con anclas pasaba en verde sin mirar
    # nada, y sin ellas fallaba. Se vio corriendo el banco sin anclas, como
    # corre en GitHub.
    assert ("sin anclas de confianza no se sabe" in dice) == almacen.vacio, dice
    # Y que la cadena llega solo se promete si llega. Hasta el 16-09-2026 esto
    # pedia la promesa en cuanto habia anclas, y la cadena del ejemplo no llega
    # a ninguna: la comprobacion daba por bueno justo lo que era falso.
    llega = lote.con_cadena_que_llega > 0
    assert ("que ese certificado lleve a un ancla de confianza" in dice) == (
        not almacen.vacio and llega
    ), dice
    return "promete %s la forma; anclas %s, y la cadena del ejemplo %s" % (
        "si" if not catalogo.vacio else "no",
        "puestas" if not almacen.vacio else "sin poner",
        "llega" if llega else "no llega, y lo dice",
    )


@comprobar("los esquemas viajan con la página y comprueban la forma",
           critica=True)
def _():
    """Sin esto, de las tres comprobaciones la pagina hace una.

    La forma se comprueba contra los XSD oficiales, que son de sus organismos
    y no estan en el codigo. Quien usa la consola se los instala; quien entra
    en una pagina no se instala nada.
    """
    from validador import factura
    from validador.esquema import Catalogo
    from validador.formato import detectar

    catalogo = Catalogo.por_defecto()
    if catalogo.vacio:
        # Se cuenta en vez de callarse, que es lo que dice la pagina tambien.
        return "no hay paquete: la página comprobaría solo el contenido"
    with open(BASE + "/f-0001.xml", "rb") as f:
        datos = f.read()
    assert catalogo.ruta_para(detectar(datos)) is not None, "sin XSD para Facturae"
    informe = factura.validar(datos, hoy=HOY, catalogo=catalogo)
    codigos = [i.codigo for i in informe.incidencias]
    assert "XSD-SIN-ESQUEMA" not in codigos, codigos
    return "%d esquemas dentro, y la forma se mide contra ellos" % len(
        catalogo.indice)


@comprobar("el esquema de Facturae compila sin red", critica=True)
def _():
    """Aqui no hay red, y por eso esta comprobacion vale.

    Los cinco XSD de Facturae importan la firma XMLDSig **por direccion web**,
    en su tercera linea. Compilar un esquema no lo hace el parser endurecido
    de `formato.py` sino libxml2 por su cuenta, asi que ese import se bajaba
    de w3.org cada vez que se comprobaba la forma de una factura del formato
    nacional. Fuera no se notaba, porque funcionaba.

    Se noto aqui: sin red el esquema no compilaba y salia «el esquema esta ahi
    pero no se puede leer, suele ser una descarga a medias», mandando a
    rebajar un fichero que estaba entero. Ahora se resuelve con la copia que
    trae el paquete de UBL, y esta comprobacion es la unica que puede afirmar
    que no se sale: en este navegador no hay a donde salir.
    """
    from lxml import etree
    from validador.esquema import Catalogo
    from validador.formato import detectar

    catalogo = Catalogo.por_defecto()
    if catalogo.vacio:
        return "no hay paquete: no hay ningún esquema que compilar"
    with open(BASE + "/fe-0001.xml", "rb") as f:
        datos = f.read()
    deteccion = detectar(datos)
    esquema = catalogo.esquema_para(deteccion)
    assert esquema is not None, catalogo.por_que_no_compila(deteccion)
    assert esquema.validate(etree.fromstring(datos)), "no valida contra su XSD"
    return "compila y valida sin poder pedirle nada a w3.org"


# --- La traduccion de los mensajes de libxml2 ------------------------------
#
# Este riesgo no rompe nada: degrada, que es peor.
#
# `esquema.py` no se limita a decir «esto no cumple el XSD». Lee el mensaje de
# libxml2 y lo traduce con doce expresiones regulares, y de ahi salen los
# codigos que ensena el informe —XSD-ORDEN, XSD-TIPO, XSD-VALOR— y la
# explicacion en castellano, que es el producto entero. Cuando ninguna encaja
# hay una salida de emergencia, `XSD-OTRO`, que copia el mensaje ingles tal
# cual y ya no dice donde ni por que.
#
# Esas regex se escribieron leyendo lo que dice **libxml2 2.11.9**, que es el
# de los tests. Aqui dentro hay **2.9.10**. Si esa version redactara una sola
# de esas frases de otra manera, no fallaria nada: los errores de forma
# saldrian todos como `XSD-OTRO`, en ingles, **solo en el navegador** —o sea,
# solo delante de quien no sabe leer un mensaje de libxml2, que es justamente
# a quien se le vende esto—.
#
# Asi que se provocan a proposito, uno por uno, contra un esquema de juguete
# que viaja en este fichero, y se comprueba que sale el codigo que tiene que
# salir. La suite corre esta misma tabla con el libxml2 de fuera
# (`tests/test_banco.py`): dos versiones distintas diciendo lo mismo es lo
# unico que se puede afirmar de esto.
#
# El esquema es de juguete a proposito. Los oficiales estan aqui dentro y
# valdrian para validar, pero no para esto: hacen falta incumplimientos
# concretos y de uno en uno, no una factura rota de verdad con doce quejas
# encadenadas de las que once son consecuencia de la primera.

_NS_UBL = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"

_ESQUEMA_DE_JUGUETE = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
           elementFormDefault="qualified">
  <xs:element name="Invoice">
    <xs:complexType><xs:sequence>
      <xs:element name="ID">
        <xs:simpleType><xs:restriction base="xs:string">
          <xs:maxLength value="20"/>
        </xs:restriction></xs:simpleType>
      </xs:element>
      <xs:element name="IssueDate" type="xs:date"/>
      <xs:element name="InvoiceTypeCode">
        <xs:simpleType><xs:restriction base="xs:string">
          <xs:enumeration value="380"/><xs:enumeration value="381"/>
        </xs:restriction></xs:simpleType>
      </xs:element>
      <xs:element name="CompanyID" minOccurs="0">
        <xs:simpleType><xs:restriction base="xs:string">
          <xs:pattern value="[A-Z][0-9]{7}[0-9A-J]"/>
        </xs:restriction></xs:simpleType>
      </xs:element>
      <xs:element name="PayableAmount" minOccurs="0">
        <xs:complexType><xs:simpleContent><xs:extension base="xs:decimal">
          <xs:attribute name="currencyID" type="xs:string" use="required"/>
        </xs:extension></xs:simpleContent></xs:complexType>
      </xs:element>
    </xs:sequence></xs:complexType>
  </xs:element>
</xs:schema>"""

# El mismo esquema con la raiz cambiada de nombre. Hace falta uno aparte para
# el ultimo caso: un documento que empieza por algo que el esquema no declara
# no se puede provocar con un esquema que si lo declara.
_ESQUEMA_SIN_INVOICE = _ESQUEMA_DE_JUGUETE.replace(
    'name="Invoice"', 'name="Otra"')

_CABEZA = '<?xml version="1.0" encoding="UTF-8"?>\n<Invoice xmlns="%s">' % _NS_UBL
_BIEN = ("<ID>F1</ID><IssueDate>2026-03-02</IssueDate>"
         "<InvoiceTypeCode>380</InvoiceTypeCode>")


def _forma(cuerpo):
    return _CABEZA + cuerpo + "</Invoice>"


# Cada provocacion con los codigos que tienen que salir, exactos. La lista
# entera y no «que contenga»: si esta version de libxml2 dijera dos cosas
# donde la otra dice una, eso tambien hay que verlo.
FORMA_ESPERADA = (
    ("una correcta no se queja",
     _forma(_BIEN), (), _ESQUEMA_DE_JUGUETE),
    ("falta un hijo obligatorio",
     _forma("<ID>F1</ID>"), ("XSD-FALTA",), _ESQUEMA_DE_JUGUETE),
    ("elementos cambiados de sitio",
     _forma("<IssueDate>2026-03-02</IssueDate><ID>F1</ID>"
            "<InvoiceTypeCode>380</InvoiceTypeCode>"),
     ("XSD-ORDEN",), _ESQUEMA_DE_JUGUETE),
    ("un elemento que el esquema no conoce",
     _forma(_BIEN + "<Chorrada>x</Chorrada>"),
     ("XSD-ORDEN",), _ESQUEMA_DE_JUGUETE),
    ("un valor fuera de la lista",
     _forma("<ID>F1</ID><IssueDate>2026-03-02</IssueDate>"
            "<InvoiceTypeCode>999</InvoiceTypeCode>"),
     ("XSD-VALOR",), _ESQUEMA_DE_JUGUETE),
    ("una fecha con el formato de toda la vida",
     _forma("<ID>F1</ID><IssueDate>02/03/2026</IssueDate>"
            "<InvoiceTypeCode>380</InvoiceTypeCode>"),
     ("XSD-TIPO",), _ESQUEMA_DE_JUGUETE),
    ("un importe con coma decimal",
     _forma(_BIEN + '<PayableAmount currencyID="EUR">1.234,56</PayableAmount>'),
     ("XSD-TIPO",), _ESQUEMA_DE_JUGUETE),
    ("un texto más largo de lo que cabe",
     _forma("<ID>" + "F" * 30 + "</ID><IssueDate>2026-03-02</IssueDate>"
            "<InvoiceTypeCode>380</InvoiceTypeCode>"),
     ("XSD-LONGITUD",), _ESQUEMA_DE_JUGUETE),
    ("un valor que no encaja con el patrón",
     _forma(_BIEN + "<CompanyID>hola</CompanyID>"),
     ("XSD-PATRON",), _ESQUEMA_DE_JUGUETE),
    ("falta un atributo obligatorio",
     _forma(_BIEN + "<PayableAmount>121.00</PayableAmount>"),
     ("XSD-ATRIBUTO",), _ESQUEMA_DE_JUGUETE),
    ("un atributo que sobra",
     _CABEZA.replace("<Invoice ", '<Invoice ola="ke" ') + _BIEN + "</Invoice>",
     ("XSD-ATRIBUTO",), _ESQUEMA_DE_JUGUETE),
    ("texto suelto donde solo caben elementos",
     _CABEZA + "pegado sin querer" + _BIEN + "</Invoice>",
     ("XSD-TEXTO",), _ESQUEMA_DE_JUGUETE),
    ("una raíz que el esquema no declara",
     _forma(_BIEN), ("XSD-RAIZ",), _ESQUEMA_SIN_INVOICE),
)


def _provocar_forma():
    """Corre la tabla entera y devuelve [(nombre, esperados, obtenidos)].

    Se monta el catalogo en una carpeta temporal porque es lo unico que
    `Catalogo` sabe hacer: buscar los XSD por nombre de fichero. Aqui dentro
    esa carpeta esta en la memoria del navegador y no toca el disco de nadie.
    """
    import tempfile
    from pathlib import Path
    from validador import esquema as mod
    from validador.esquema import Catalogo

    catalogos = {}
    for caso in FORMA_ESPERADA:
        texto = caso[3]
        if texto in catalogos:
            continue
        carpeta = Path(tempfile.mkdtemp())
        (carpeta / "UBL-Invoice-2.1.xsd").write_text(texto, encoding="utf-8")
        catalogos[texto] = Catalogo(carpeta)

    salida = []
    for nombre, documento, esperados, texto in FORMA_ESPERADA:
        incidencias = mod.validar(documento, catalogo=catalogos[texto]).incidencias
        salida.append((nombre, esperados, tuple(i.codigo for i in incidencias)))
    return salida


@comprobar("los mensajes de libxml2 se traducen igual con esta versión",
           critica=True)
def _():
    fallos = [
        "%s: se esperaba %s y salio %s" % (
            nombre, list(esperados) or "nada", list(obtenidos) or "nada")
        for nombre, esperados, obtenidos in _provocar_forma()
        if obtenidos != esperados
    ]
    assert not fallos, " | ".join(fallos)
    return "%d incumplimientos provocados, y los %d se leen igual que fuera" % (
        len(FORMA_ESPERADA), len(FORMA_ESPERADA))


@comprobar("las anclas viajan con la página y dicen de cuándo son",
           critica=True)
def _():
    """Y la otra mitad: de quien es el certificado que firma.

    Con las anclas puestas hay que decir dos cosas que quien valida no puede
    saber: de que lista salen —eso lo dice el manifiesto, que viaja con
    ellas— y de cuando es esa lista. Un conjunto montado hace dos anios sigue
    creyendo a autoridades a las que el Estado ya les retiro la
    cualificacion, con su certificado en vigor y su cadena llegando.
    """
    from validador import cifras
    from validador.cadena import Almacen

    almacen = Almacen.por_defecto()
    if almacen.vacio:
        return "no hay paquete: no se comprueba de quién es el certificado"
    assert almacen.declarada, "las anclas no dicen de dónde vienen"
    renovacion = almacen.renovacion
    assert renovacion.hay, "las anclas no dicen de cuándo son"
    # Y las de sellado, que van en la carpeta hermana y son las que se olvidan.
    assert not almacen.sellos.vacio, "faltan las anclas de sellado de tiempo"
    return "%d anclas y %d de sellado, de una lista del %s" % (
        len(almacen.todas()),
        len(almacen.sellos.todas()),
        cifras.fecha(renovacion.publicada) if renovacion.publicada else "?",
    )


# --- Lo que solo se puede mirar desde dentro del navegador -----------------
#
# Las dos de aqui preguntan por cosas que fuera no existen: lo que este
# navegador ha pedido de verdad, y lo que `glosa.js` comprobo al arrancar.
# Corriendo el banco en CPython —`tests/test_banco.py`— no hay `js` ni hay
# red, asi que dicen que no se ha mirado en vez de salir en verde. Una
# comprobacion que no puede correr y aprueba igual es lo contrario de una
# comprobacion.


def _desde_el_navegador():
    """El modulo `js` de Pyodide, o None si esto no corre en un navegador."""
    try:
        import js
    except ImportError:
        return None
    return js if getattr(js, "location", None) is not None else None


@comprobar("el paquete que ha llegado es el que la ficha dice", critica=True)
def _():
    """La huella publicada, comprobada.

    `PAQUETE.json` lleva el SHA-256 del zip escrito al lado desde el
    principio, y hasta el 06-09-2026 no lo miraba nadie: se publicaba una
    huella y se descomprimia lo que llegara. No es una frontera de seguridad
    —el zip y su ficha vienen del mismo sitio— y no se dice que lo sea: lo que
    caza es la cache vieja y la descarga a medias, que se descomprime **sin
    error** y deja al validador con menos anclas de las que la pagina dice que
    trae. Eso son aprobados de mas repartidos en silencio.
    """
    js = _desde_el_navegador()
    if js is None:
        return "fuera del navegador no se baja ningún paquete"
    paquete = js.window.Glosa.paquete
    if paquete is None:
        return "no hay paquete: no hay huella que comprobar"
    comprobada = getattr(paquete, "huella_comprobada", None)
    assert comprobada is not False, (
        "el zip no resume lo que dice PAQUETE.json y aun así está descomprimido"
    )
    assert comprobada is not None, (
        "no se ha podido calcular la huella: `crypto.subtle` no está, o sea "
        "que esto no es un contexto seguro. Sin ella no se ha comprobado nada"
    )
    from validador import cifras
    return "el zip resume lo que PAQUETE.json publica, y son %s bytes" % (
        cifras.recuento(paquete.bytes),)


@comprobar("esta página no le pide nada a nadie", critica=True)
def _():
    """La cifra de cabecera de la tesis, medida donde se puede medir.

    La politica de privacidad publica una tabla que dice «0 dominios de
    terceros», y hasta ahora eso solo lo comprobaba una persona abriendo el
    panel del navegador en el ritual de despliegue. Un `@import` en el CSS o
    una tipografia de fuera la volverian falsa sin romper nada.

    `pyodide.js` ademas lleva dentro la direccion de su CDN como respaldo, asi
    que la pregunta no es teorica: si algun dia tirara de ella, esto es lo
    unico que lo diria.
    """
    js = _desde_el_navegador()
    if js is None:
        return "fuera del navegador no hay peticiones que contar"
    nombres = [r.name for r in js.performance.getEntriesByType("resource")]
    # Solo `http(s)` tiene un dominio al que pedirle algo. `data:` y `blob:`
    # salen del propio documento y no tocan la red; contarlos fue lo que hizo
    # que el ritual diera una vez `null` por dominio ajeno, que es lo que
    # devuelve `new URL('data:...').origin`. Una comprobacion de privacidad
    # que grita sin motivo se deja de mirar, y entonces ya no comprueba nada.
    ajenos = sorted({
        n.split("/")[2] for n in nombres
        if n.startswith("http://") or n.startswith("https://")
    } - {js.location.host})
    assert not ajenos, "esta página le ha pedido algo a " + ", ".join(ajenos)
    return "%d peticiones y todas a %s" % (len(nombres), js.location.host)


# Lo que la politica tiene que decir para que la frase «no le pide nada a
# nadie» sea del navegador y no solo nuestra.
_POLITICA_EXIGIDA = {
    "default-src": {"'none'"},
    "connect-src": {"'self'"},
    "img-src": {"'self'", "data:"},
    "font-src": {"'self'"},
}


@comprobar("el navegador tiene orden de no pedir nada fuera")
def _():
    """La politica de contenido: puesta, diciendo lo que tiene que decir, y
    cumplida por el navegador.

    La de arriba cuenta las peticiones despues de hechas: dice que no ha
    pasado. Esta dice que **no puede pasar**. `--sitio` pone en cada pagina una
    politica que solo deja pedir a este mismo sitio.

    Que el navegador la hace cumplir se prueba sin tocar la red: la politica no
    permite `eval`, asi que si `eval` corre, la politica esta escrita y nadie
    la aplica. Probarlo pidiendo algo a otro dominio seria justo lo que esta
    pagina no hace; y un intento bloqueado deja apunte en Resource Timing, que
    pondria en rojo al testigo de la portada sin que nada hubiera salido.

    En la carpeta `web/` sin montar sale en rojo, y es verdad: esa copia no
    lleva politica.
    """
    js = _desde_el_navegador()
    if js is None:
        return "fuera del navegador no hay política que mirar"
    meta = js.document.querySelector('meta[http-equiv="Content-Security-Policy"]')
    # El `null` de JavaScript llega como JsNull y no como None: con un `is not
    # None` a secas esto pasaba y reventaba una linea mas abajo, en rojo pero
    # sin decir por que. Provocado quitando la politica de la pagina montada.
    assert meta is not None and type(meta).__name__ != "JsNull", (
        "esta página no lleva política de contenido: la pone `--sitio` al montar")
    directivas = {}
    for trozo in str(meta.content).split(";"):
        partes = trozo.split()
        if partes:
            directivas[partes[0]] = set(partes[1:])
    for nombre, exigido in _POLITICA_EXIGIDA.items():
        assert directivas.get(nombre) == exigido, "%s dice %s y tiene que decir %s" % (
            nombre, " ".join(sorted(directivas.get(nombre, ()))) or "nada",
            " ".join(sorted(exigido)))
    sueltos = sorted(v for v in directivas.get("script-src", ())
                     if v not in ("'self'", "'wasm-unsafe-eval'")
                     and not v.startswith("'sha256-"))
    assert not sueltos, "script-src deja pasar " + ", ".join(sueltos)
    try:
        js.eval("1")
    except Exception:
        pass
    else:
        raise AssertionError(
            "eval ha corrido: la política está escrita y el navegador no la aplica")
    return "solo a %s, y el navegador la cumple" % js.location.host


json.dumps(resultados)
