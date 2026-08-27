"""Banco de pruebas: comprueba que Factura-e funciona dentro del navegador.

No basta con que Pyodide arranque. Lo que hay que saber es si la compilacion
de lxml para WebAssembly trae todo lo que el validador usa, en particular el
soporte de esquemas XSD, que libxml2 se puede compilar sin el.
"""
import json
import os
import time
from datetime import date

BASE = os.environ.get("EJEMPLOS", "/ejemplos")
HOY = date(2026, 9, 20)

# Medido fuera, con CPython 3.14 y lxml 6.0.2. Ver la comprobacion de c14n.
ESPERADO_C14N = "AesuDLQkGMXkd5ZOqjQXwGzUHYaUE4/PuR5VUXJZ/Gw="

# Un par de primos para firmar en la prueba. Es de juguete: no protege nada.
P_JUGUETE = 102537101091278998115987341585599416127626670398059308299795465171831775139903
Q_JUGUETE = 68075505016498421992239704630051902902248104096335391022395579103563275678179
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
    assert esquema.validate(bueno), "rechaza un documento valido"
    assert not esquema.validate(malo), "acepta un documento invalido"
    assert esquema.error_log, "no hay error_log, y de ahi salen los mensajes"
    return "compila, acepta, rechaza y explica por que"


@comprobar("el paquete validador importa", critica=True)
def _():
    # Se recorre el paquete en vez de nombrar los modulos a mano. La lista
    # escrita a mano se quedo corta cuando entro `revocacion`: esta
    # comprobacion siguio en verde con un wheel viejo dentro y el fallo salio
    # tres pruebas mas abajo, disfrazado de otra cosa.
    import importlib
    import pkgutil
    import validador
    nombres = sorted(m.name for m in pkgutil.iter_modules(validador.__path__))
    assert nombres, "el paquete no trae ningun modulo"
    for nombre in nombres:
        importlib.import_module("validador." + nombre)
    return "los {} modulos: {}".format(len(nombres), ", ".join(nombres))


@comprobar("el parser endurecido no expande entidades", critica=True)
def _():
    # XXE: si esto expande, una factura ajena puede leer ficheros.
    from lxml import etree
    from validador.formato import parser
    bomba = (b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x "SECRETO">]>'
             b"<r>&x;</r>")
    raiz = etree.fromstring(bomba, parser=parser())
    texto = etree.tostring(raiz, encoding="unicode")
    assert "SECRETO" not in texto, "la entidad se expandio: " + texto
    return "la entidad no se expande"


@comprobar("reconoce el formato de un fichero real")
def _():
    from validador.formato import detectar_archivo
    d = detectar_archivo(BASE + "/f-0001.xml")
    assert d, d.motivo
    return "{} - {}".format(d.familia, d.version or "sin version")


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
    assert not informe.conforme, "esta factura esta rota y deberia saltar"
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
    return "catalogo vacio detectado, sin reventar"


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
    assert lote.informes, "el lote ha vuelto vacio"
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
    assert not rotas, "dice que esta manipulada una factura intacta: " + str(rotas)
    return firmadas[0].split("/")[-1] + " -> firma intacta"



@comprobar("la cadena de confianza se encadena aqui tambien", critica=True)
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
    os.makedirs("/anclas", exist_ok=True)
    with open("/anclas/ejemplo.cer", "wb") as f:
        f.write(crudo)
    almacen = Almacen("/anclas")
    assert not almacen.vacio, "no ha leido el ancla del disco virtual"
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
    assert [i.codigo for i in salen] == ["CADENA-SIN-ANCLAS"],         "deberia avisar de que no ha comprobado nada: " + str(salen)
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


@comprobar("una lista de revocacion se lee y se comprueba aqui", critica=True)
def _():
    from validador.revocacion import comprobar as comprobar_revocacion
    from validador.revocacion import leer_lista
    hoja = _certificado_del_ejemplo()
    if hoja is None:
        return "no hay ninguna firmada entre los ejemplos"

    crudo = _lista_de_juguete(hoja.emisor_der, serie=hoja.serie)
    una = leer_lista(crudo)
    assert len(una.anulaciones) == 1, "no ha leido la linea de anulados"
    assert una.anulaciones[hoja.serie].compromiso, "no ha leido el motivo"

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
    assert comprobar_revocacion(hoja, hoja, [completa]).estado == "vigente",         "una lista completa y limpia deberia poder decir que esta vigente"

    incremental = leer_lista(_lista_de_juguete(hoja.emisor_der, delta=True))
    salida = comprobar_revocacion(hoja, hoja, [incremental])
    assert salida.estado == "sin_saber", "da por vigente con una lista delta"
    return "distingue la completa de la incremental"


json.dumps(resultados)
