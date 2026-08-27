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


@comprobar("el informe declara de donde salen las anclas", critica=True)
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

    os.makedirs("/anclas-pagina", exist_ok=True)
    with open("/anclas-pagina/ejemplo.cer", "wb") as f:
        f.write(hoja.der)
    almacen = Almacen("/anclas-pagina", procedencia="viene con la pagina")

    notas = [i for i in reglas([hoja], almacen) if i.gravedad == "nota"]
    assert len(notas) == 1, "no declara nada: " + str(notas)
    nota = notas[0]
    assert nota.codigo == "CONFIANZA-ANCLA", nota.codigo
    assert "viene con la pagina" in nota.mensaje, nota.mensaje
    assert hoja.huella() in nota.mensaje, "no deja constancia de la huella"
    # Y que no se cuela la ruta del disco virtual, que a quien lee no le dice
    # nada y encima suena a que el ancla la puso el.
    assert "/anclas-pagina" not in nota.mensaje, nota.mensaje
    return "dice de donde viene el ancla y con que huella"


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


@comprobar("se verifica una firma de curva eliptica", critica=True)
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
        assert curva.encima(*cert.punto), nombre + ": el punto no esta en la curva"
        valor = bytes.fromhex(firmada)
        arranque = time.perf_counter()
        ok = verificar(valor, MENSAJE_DEL_VECTOR, cert, alg, concatenada=True)
        tiempos.append("%s %.0f ms" % (nombre, (time.perf_counter() - arranque) * 1000))
        assert ok, nombre + ": no verifica una firma buena de openssl"
        # Y que no se traga la misma firma sobre otro mensaje.
        assert not verificar(valor, MENSAJE_DEL_VECTOR + b"!", cert, alg,
                             concatenada=True), nombre + ": acepta otro mensaje"
    return ", ".join(tiempos)


@comprobar("las curvas son las de verdad, tambien aqui", critica=True)
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


def _tsl_de_juguete(firmante_der, ancla_der):
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
    t(serv, "ServiceTypeIdentifier",
      "http://uri.etsi.org/TrstSvc/Svctype/CA/QC")
    t(t(serv, "ServiceName"), "Name", "AC de juguete")
    ident = t(serv, "ServiceDigitalIdentity")
    t(t(ident, "DigitalId"), "X509Certificate",
      base64.b64encode(ancla_der).decode())
    t(serv, "ServiceStatus",
      "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted")
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


@comprobar("una lista de confianza se comprueba y se monta aqui", critica=True)
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

    os.makedirs("/anclas-tsl", exist_ok=True)
    resumen = tsl.montar(una, "/anclas-tsl")
    assert resumen.escritas == 1, resumen.escritas

    almacen = Almacen("/anclas-tsl")
    assert almacen.contiene(hoja), "lo montado no sirve de ancla"
    notas = [i for i in reglas([hoja], almacen)
             if i.gravedad == "nota" and i.codigo == "CONFIANZA-ANCLA"]
    assert len(notas) == 1, "no declara de donde sale: " + str(notas)
    assert "lista de confianza de ES" in notas[0].mensaje, notas[0].mensaje
    return "verifica la lista, monta el ancla y dice de donde sale"


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
        tsl.montar(otra, "/anclas-coladas")
    except ValueError:
        pass
    else:
        raise AssertionError("monta anclas de una lista sin comprobar")
    return "rechaza la tocada y se niega sin firmante"


json.dumps(resultados)
