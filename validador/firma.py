"""La firma electrónica de una factura: XAdES sobre XML-DSig.

En Facturae la firma no es un adorno. El propio esquema lo dice de su bloque
`Signature`:

    «Se define como opcional para facilitar la verificación y el tránsito del
    fichero. No obstante, debe cumplimentarse este bloque de firma electrónica
    para que se considere una factura electrónica válida legalmente frente a
    terceros.»

Hasta aquí el validador la ignoraba por completo, y el informe lo decía: «no se
comprueba la validez de las firmas electrónicas». Ahora se comprueba una parte,
y sigue diciéndose cuál no.

Qué se comprueba y qué no
-------------------------
Se comprueba, y sin conexión a ninguna parte:

1. **Que el documento no se haya tocado desde que se firmó.** Cada `Reference`
   de la firma lleva el resumen (digest) de un trozo del documento. Se
   canonicaliza ese trozo, se le calcula el resumen y se compara. Esto es solo
   hash: no hace falta ninguna clave, y es lo que caza el fallo más común de
   todos —alguien edita el XML después de firmarlo, o una herramienta lo vuelve
   a serializar y lo rompe—.
2. **Que la firma la hiciera la clave privada de ese certificado.** RSA sobre
   el `SignedInfo` canonicalizado.
3. **Que el certificado estuviera vigente** en la fecha que la firma declara.
4. **Que el certificado que se presenta sea el que la firma dice haber usado**
   (la propiedad `SigningCertificate` de XAdES guarda su resumen).
5. **Que los algoritmos no estén obsoletos.**

**De quién es el certificado lo responde `cadena.py`**, encadenándolo hasta un
ancla de confianza instalada. Aquí no: aquí solo se mira el certificado que el
documento enseña, sin preguntarse quién lo avala.

**No se comprueba en ninguno de los dos**:

- Que el certificado no esté revocado. Exige OCSP o CRL, o sea red, o que el
  documento traiga la prueba dentro (XAdES-XL).
- Los sellos de tiempo (XAdES-T y por encima).
- Que quien firma esté autorizado a facturar por ese NIF.

Traducido: este módulo responde **«¿alguien ha cambiado este documento después
de firmarlo?»** y **«¿la firma cuadra con el certificado que trae dentro?»**.
Un documento firmado con un certificado que el remitente se haya inventado pasa
las cinco comprobaciones de aquí; lo caza `cadena.py` si hay anclas puestas.

Por qué no se usa una librería de criptografía
----------------------------------------------
Verificar RSA es `pow(firma, e, n)`: aritmética de enteros, que Python hace
nativa y con precisión arbitraria. Lo único que hacía falta de fuera era leer
la clave pública del certificado, y para eso bastan unas líneas de DER.

Traer `cryptography` costaría una extensión compilada, y este validador entero
está pensado para correr dentro del navegador con Pyodide: cada dependencia con
código nativo es un wheel más que buscar, otra versión que casar y varios megas
más de descarga. Este módulo **no le suma ni un byte**: son unos kilobytes
dentro del wheel que ya se bajaba.

Aquí **no se firma nada**: no hay ninguna clave privada de por medio y por
tanto no hay secreto que filtrar por tiempos de ejecución. El riesgo de una
implementación propia es el contrario —dar por buena una firma falsa—, y contra
eso está escrita: ver `_verificar_rsa`.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from lxml import etree

from validador.formato import FACTURAE, NS_FIRMA, Deteccion
from validador.incidencias import AVISO, ERROR, Incidencia

__all__ = ["reglas", "hay_firma", "certificados_de", "momento_de_firma",
           "leer_certificado", "Certificado", "ALGORITMOS_ROTOS"]

# --- Algoritmos ------------------------------------------------------------

# Cómo canonicalizar. lxml sabe hacer C14N 1.0 y exclusiva; C14N 1.1 no, y se
# dice en vez de coger la de al lado y dar un resultado que no significa nada.
_C14N = {
    "http://www.w3.org/TR/2001/REC-xml-c14n-20010315": (False, False),
    "http://www.w3.org/TR/2001/REC-xml-c14n-20010315#WithComments": (False, True),
    "http://www.w3.org/2001/10/xml-exc-c14n#": (True, False),
    "http://www.w3.org/2001/10/xml-exc-c14n#WithComments": (True, True),
}

_RESUMEN = {
    "http://www.w3.org/2000/09/xmldsig#sha1": "sha1",
    "http://www.w3.org/2001/04/xmlenc#sha256": "sha256",
    "http://www.w3.org/2001/04/xmldsig-more#sha384": "sha384",
    "http://www.w3.org/2001/04/xmlenc#sha512": "sha512",
}

# (resumen, ¿está obsoleto?)
_FIRMA = {
    "http://www.w3.org/2000/09/xmldsig#rsa-sha1": ("sha1", True),
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256": ("sha256", False),
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha384": ("sha384", False),
    "http://www.w3.org/2001/04/xmldsig-more#rsa-sha512": ("sha512", False),
}

# Prefijos DigestInfo del RFC 8017, apéndice B.1. Van tal cual porque el bloque
# de relleno se reconstruye entero para compararlo: ver `_verificar_rsa`.
_DIGESTINFO = {
    "sha1": bytes.fromhex("3021300906052b0e03021a05000414"),
    "sha256": bytes.fromhex("3031300d060960864801650304020105000420"),
    "sha384": bytes.fromhex("3041300d060960864801650304020205000430"),
    "sha512": bytes.fromhex("3051300d060960864801650304020305000440"),
}

# Por debajo de esto, la clave se considera corta. 2048 es el mínimo que
# recomiendan hoy tanto ENISA como el CCN para firma cualificada; las de 1024
# bits siguen circulando en facturas antiguas y no se pueden dar por buenas
# sin decir nada.
BITS_MINIMOS = 2048


# --- DER, lo justo ---------------------------------------------------------


def _tlv(datos: bytes, pos: int = 0) -> tuple[int, bytes, int]:
    """Un elemento DER: (etiqueta, contenido, dónde empieza el siguiente).

    DER escribe todo como etiqueta-longitud-valor. La longitud es un byte si
    cabe en siete bits; si no, ese byte dice cuántos bytes ocupa la longitud de
    verdad. No hay más misterio, y con esto se recorre un certificado entero.
    """
    if pos + 2 > len(datos):
        raise ValueError("DER truncado")
    etiqueta = datos[pos]
    largo = datos[pos + 1]
    pos += 2
    if largo & 0x80:
        cuantos = largo & 0x7F
        if cuantos == 0 or pos + cuantos > len(datos):
            raise ValueError("longitud DER indefinida o truncada")
        largo = int.from_bytes(datos[pos : pos + cuantos], "big")
        pos += cuantos
    if pos + largo > len(datos):
        raise ValueError("DER truncado")
    return etiqueta, datos[pos : pos + largo], pos + largo


def _elementos(contenido: bytes) -> list[tuple[int, bytes]]:
    salida = []
    pos = 0
    while pos < len(contenido):
        etiqueta, valor, pos = _tlv(contenido, pos)
        salida.append((etiqueta, valor))
    return salida


@dataclass(frozen=True)
class Certificado:
    """Lo que hace falta de un X.509 para verificar una firma y encadenarla.

    Los nombres van dos veces: en claro (`sujeto`, `emisor_nombre`) para poder
    escribir un mensaje que alguien entienda, y en DER (`sujeto_der`,
    `emisor_der`) para encadenar. Encadenar por el nombre en claro sería un
    error: el nombre completo tiene más atributos que el común, y dos
    autoridades distintas pueden coincidir en el CN.
    """

    modulo: int
    exponente: int
    desde: datetime | None
    hasta: datetime | None
    sujeto: str | None

    # Para la cadena. Todo opcional para no romper a quien construya un
    # Certificado a mano —los tests lo hacen— sin querer saber de cadenas.
    der: bytes = b""
    tbs: bytes = b""  # lo que el emisor firmó, tal cual venía
    sujeto_der: bytes = b""
    emisor_der: bytes = b""
    emisor_nombre: str | None = None
    algoritmo_firma: str | None = None  # "sha256", o None si no lo conocemos
    valor_firma: bytes = b""
    es_autoridad: bool | None = None  # basicConstraints cA
    profundidad_max: int | None = None  # pathLenConstraint
    usos: frozenset[str] = frozenset()  # keyUsage
    criticas_sin_entender: frozenset[str] = frozenset()

    @property
    def bits(self) -> int:
        return self.modulo.bit_length()

    @property
    def autofirmado(self) -> bool:
        return bool(self.sujeto_der) and self.sujeto_der == self.emisor_der

    def huella(self, alg: str = "sha256") -> str:
        """La huella del certificado, en mayúsculas y por parejas.

        Es como las publican las autoridades en su web, y es lo que permite
        comprobar que un ancla de confianza es la que dice ser sin fiarse de
        por dónde ha llegado.
        """
        crudo = hashlib.new(alg, self.der).hexdigest().upper()
        return ":".join(crudo[i : i + 2] for i in range(0, len(crudo), 2))


def _fecha_der(etiqueta: int, crudo: bytes) -> datetime | None:
    """UTCTime (AA...) o GeneralizedTime (AAAA...), siempre en UTC."""
    texto = crudo.decode("ascii", "replace").rstrip("Z")
    formato = "%y%m%d%H%M%S" if etiqueta == 0x17 else "%Y%m%d%H%M%S"
    try:
        return datetime.strptime(texto[: len(formato) + 4], formato).replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


_OID_CN = b"\x55\x04\x03"  # 2.5.4.3, el «nombre común»


def _nombre_der(contenido: bytes) -> str | None:
    """El nombre común (CN) del sujeto, para poder decir de quién es.

    Se recorre el Name buscando el atributo cuyo OID es 2.5.4.3. No se
    reconstruye el nombre entero: en el mensaje solo hace falta algo con lo que
    una persona reconozca el certificado.
    """
    for _, rdn in _elementos(contenido):
        for _, atributo in _elementos(rdn):
            partes = _elementos(atributo)
            if len(partes) != 2:
                continue
            (etiqueta_oid, oid), (_, valor) = partes
            if etiqueta_oid == 0x06 and oid == _OID_CN:
                return valor.decode("utf-8", "replace")
    return None


# Algoritmos de firma de certificado, por su OID. MD5 y SHA-1 están rotos para
# firmar certificados —se saben fabricar colisiones, y con una colisión se
# fabrica un certificado falso que verifica—, así que se reconocen para poder
# decir qué son, no para darlos por buenos: ver `cadena.py`.
_OID_ALGORITMO = {
    "2a864886f70d010104": ("md5", True),
    "2a864886f70d010105": ("sha1", True),
    "2a864886f70d01010b": ("sha256", False),
    "2a864886f70d01010c": ("sha384", False),
    "2a864886f70d01010d": ("sha512", False),
}
ALGORITMOS_ROTOS = frozenset(
    alg for alg, roto in _OID_ALGORITMO.values() if roto
)

_OID_BASIC_CONSTRAINTS = "551d13"  # 2.5.29.19
_OID_KEY_USAGE = "551d0f"  # 2.5.29.15

# keyUsage es un BIT STRING; el bit 5 es el que permite firmar certificados.
_USOS = (
    "firma",  # 0 digitalSignature
    "no_repudio",  # 1 contentCommitment
    "cifrar_clave",
    "cifrar_datos",
    "acuerdo_clave",
    "firmar_certificados",  # 5 keyCertSign
    "firmar_crl",  # 6 cRLSign
    "solo_cifrar",
    "solo_descifrar",
)


def _oid(crudo: bytes) -> str:
    return crudo.hex()


def _leer_extensiones(campos, salto):
    """basicConstraints, keyUsage y qué críticas no entendemos.

    Las extensiones van en `[3] EXPLICIT`, o sea etiqueta 0xA3, y son
    opcionales: un certificado v1 no tiene ninguna.
    """
    es_ca = None
    profundidad = None
    usos: set[str] = set()
    criticas: set[str] = set()
    for etiqueta, contenido in campos[salto + 6 :]:
        if etiqueta != 0xA3:
            continue
        _, lista, _ = _tlv(contenido)
        for _, extension in _elementos(lista):
            partes = _elementos(extension)
            if not partes:
                continue
            identificador = _oid(partes[0][1])
            critica = len(partes) == 3 and partes[1][1] == b"\xff"
            valor = partes[-1][1]
            if identificador == _OID_BASIC_CONSTRAINTS:
                dentro = _elementos(_tlv(valor)[1]) if valor else []
                es_ca = bool(dentro) and dentro[0][0] == 0x01 and dentro[0][1] == b"\xff"
                for et, v in dentro:
                    if et == 0x02:
                        profundidad = int.from_bytes(v, "big")
            elif identificador == _OID_KEY_USAGE:
                _, bits, _ = _tlv(valor)
                if len(bits) >= 2:
                    sobran = bits[0]
                    total = (len(bits) - 1) * 8 - sobran
                    numero = int.from_bytes(bits[1:], "big") >> sobran
                    for posicion in range(total):
                        if numero >> (total - 1 - posicion) & 1 and posicion < len(_USOS):
                            usos.add(_USOS[posicion])
            elif critica:
                # Una extensión crítica que no se entiende obliga, según la
                # norma, a rechazar el certificado. No se rechaza aquí —eso lo
                # decide quien encadena—, pero se apunta cuál era.
                criticas.add(identificador)
    return es_ca, profundidad, frozenset(usos), frozenset(criticas)


def leer_certificado(der: bytes) -> Certificado:
    """Un X.509 abierto: clave, fechas, nombres, firma y extensiones."""
    _, certificado, siguiente = _tlv(der)
    der = der[:siguiente]  # sin la basura que venga detrás, si viene
    partes = _elementos(certificado)
    if len(partes) < 3:
        raise ValueError("no parece un certificado")

    # El `tbsCertificate` hay que quedárselo **tal cual venía**, con su
    # etiqueta y su longitud: es exactamente la ristra de octetos que el emisor
    # firmó. Volver a serializarlo a partir de lo parseado daría otros bytes en
    # cuanto el certificado no fuera DER estricto, y la firma no verificaría.
    fin_tbs = _tlv(certificado)[2]
    tbs = certificado[:fin_tbs]

    campos = _elementos(partes[0][1])
    # El campo `version` es opcional y va etiquetado [0]. Si está, todo lo
    # demás baja una posición: sin esta cuenta se leería el número de serie
    # donde va la clave.
    salto = 1 if campos[0][0] == 0xA0 else 0
    emisor_der = _reserializar(campos[salto + 2])
    validez = _elementos(campos[salto + 3][1])
    desde = _fecha_der(*validez[0]) if len(validez) > 0 else None
    hasta = _fecha_der(*validez[1]) if len(validez) > 1 else None
    sujeto_der = _reserializar(campos[salto + 4])

    spki = _elementos(campos[salto + 5][1])
    bits = spki[1][1]
    if not bits or bits[0] != 0:
        raise ValueError("la clave pública no empieza en un byte entero")
    _, rsa, _ = _tlv(bits[1:])
    numeros = _elementos(rsa)
    if len(numeros) < 2:
        raise ValueError("no parece una clave RSA")

    algoritmo = None
    algoritmos = _elementos(partes[1][1])
    if algoritmos and algoritmos[0][0] == 0x06:
        pareja = _OID_ALGORITMO.get(_oid(algoritmos[0][1]))
        algoritmo = pareja[0] if pareja else None
    valor_firma = partes[2][1][1:] if partes[2][1][:1] == b"\x00" else b""

    es_ca, profundidad, usos, criticas = _leer_extensiones(campos, salto)
    return Certificado(
        modulo=int.from_bytes(numeros[0][1], "big"),
        exponente=int.from_bytes(numeros[1][1], "big"),
        desde=desde,
        hasta=hasta,
        sujeto=_nombre_der(campos[salto + 4][1]),
        der=der,
        tbs=tbs,
        sujeto_der=sujeto_der,
        emisor_der=emisor_der,
        emisor_nombre=_nombre_der(campos[salto + 2][1]),
        algoritmo_firma=algoritmo,
        valor_firma=valor_firma,
        es_autoridad=es_ca,
        profundidad_max=profundidad,
        usos=usos,
        criticas_sin_entender=criticas,
    )


def _reserializar(elemento: tuple[int, bytes]) -> bytes:
    """Devuelve un TLV ya parseado a su forma en bytes.

    Para los nombres, que se comparan en DER y no en claro.
    """
    etiqueta, contenido = elemento
    if len(contenido) < 0x80:
        largo = bytes([len(contenido)])
    else:
        crudo = len(contenido).to_bytes((len(contenido).bit_length() + 7) // 8, "big")
        largo = bytes([0x80 | len(crudo)]) + crudo
    return bytes([etiqueta]) + largo + contenido


def _verificar_rsa(firma: bytes, mensaje: bytes, cert: Certificado, alg: str) -> bool:
    """¿Sale este mensaje de firmar con la clave privada de este certificado?

    RSA con relleno PKCS#1 v1.5: `pow(firma, e, n)` devuelve un bloque que, si
    la firma es buena, tiene exactamente esta forma:

        00 01 FF FF ... FF 00 <DigestInfo> <resumen del mensaje>

    **Se reconstruye ese bloque entero y se comparan los bytes.** Es un detalle
    con nombre propio: la forma «natural» de escribir esto es al revés —abrir
    el bloque, saltarse los FF, leer el DigestInfo y sacar el resumen—, y así
    escrito es como se hizo durante años en medio mundo. El problema es que un
    lector permisivo acepta bloques con el relleno corto y basura detrás, y con
    eso se pueden fabricar firmas falsas sin tener la clave privada: es el fallo
    de Bleichenbacher de 2006, que resucitó en 2014 como «BERserk» y se llevó
    por delante a varias implementaciones grandes.

    Comparando el bloque completo no hay nada que interpretar, así que no hay
    dónde ser permisivo. Y por eso los `_DIGESTINFO` son constantes en vez de
    algo que se decodifique.

    Con precisión, porque conviene no exagerar: fabricar uno de esos bloques
    falsos exige que el exponente público sea pequeño —3 o 17—, porque hay que
    sacarle la raíz cúbica a un número. Con 65537, que es lo normal hoy, no se
    puede. Pero certificados con exponente 3 los hay, el coste de escribirlo
    bien es cero, y la alternativa es un validador que da por buena una firma
    falsa: eso no se deja al azar de qué certificado llegue.
    """
    tamanio = (cert.modulo.bit_length() + 7) // 8
    if len(firma) != tamanio or cert.modulo <= 0 or cert.exponente <= 0:
        return False
    prefijo = _DIGESTINFO.get(alg)
    if prefijo is None:
        return False
    esperado = prefijo + hashlib.new(alg, mensaje).digest()
    if tamanio < len(esperado) + 11:
        return False
    bloque = b"\x00\x01" + b"\xff" * (tamanio - len(esperado) - 3) + b"\x00" + esperado
    obtenido = pow(int.from_bytes(firma, "big"), cert.exponente, cert.modulo)
    return obtenido.to_bytes(tamanio, "big") == bloque


# --- Lectura del XML -------------------------------------------------------


def _hijo(nodo, nombre: str):
    encontrados = nodo.xpath(f"./*[local-name()='{nombre}']")
    return encontrados[0] if encontrados else None


def _texto_b64(nodo) -> bytes | None:
    if nodo is None or nodo.text is None:
        return None
    try:
        return base64.b64decode("".join(nodo.text.split()))
    except (binascii.Error, ValueError):
        return None


def hay_firma(raiz) -> list:
    """Las firmas XML-DSig del documento, estén donde estén."""
    if raiz is None:
        return []
    return raiz.xpath(
        "//*[local-name()='Signature' and namespace-uri()=$ns]", ns=NS_FIRMA
    )


def certificados_de(firma) -> list[Certificado]:
    """Los certificados que trae una firma, el primero el que firma.

    XAdES permite meter la cadena entera en el `KeyInfo`, y lo normal es que el
    primero sea el del firmante. Los que no se puedan leer se saltan en
    silencio: de que falte el del firmante ya se queja `reglas`, y un
    intermedio ilegible solo significa que la cadena no llegará arriba.
    """
    salida = []
    for texto in firma.xpath(".//*[local-name()='X509Certificate']/text()"):
        crudo = base64.b64decode("".join(texto.split()), validate=False)
        try:
            salida.append(leer_certificado(crudo))
        except (ValueError, IndexError, binascii.Error):
            continue
    return salida


def _canonicalizar(nodo, algoritmo: str | None) -> bytes | None:
    modo = _C14N.get(algoritmo or "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")
    if modo is None:
        return None
    exclusiva, comentarios = modo
    return etree.tostring(
        nodo, method="c14n", exclusive=exclusiva, with_comments=comentarios
    )


def _por_identificador(raiz, identificador: str):
    encontrados = raiz.xpath(
        "//*[@Id=$i or @id=$i or @ID=$i]", i=identificador
    )
    return encontrados[0] if encontrados else None


def _contenido_referenciado(raiz, firma, referencia) -> tuple[bytes | None, str]:
    """Los octetos sobre los que se calculó el resumen de una `Reference`.

    Devuelve también el motivo cuando no se ha podido, para poder decirlo en
    vez de dar la referencia por buena.
    """
    uri = referencia.get("URI")
    transformadas = referencia.xpath(
        ".//*[local-name()='Transform']/@Algorithm"
    )
    c14n = next((t for t in transformadas if t in _C14N), None)
    desconocidas = [
        t
        for t in transformadas
        if t not in _C14N
        and t != "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
    ]
    if desconocidas:
        return None, f"lleva una transformación que no sabemos aplicar: {desconocidas[0]}"

    if uri is None:
        return None, "no dice a qué se refiere"

    if uri == "":
        # Documento entero. La transformada «enveloped-signature» quita **esta**
        # firma, no cualquiera: en un fichero con dos firmas, quitar la primera
        # que aparezca daría un resultado distinto y la comprobación mentiría.
        arbol = etree.fromstring(etree.tostring(raiz))
        # `getelementpath` da una ruta en notación {namespace}etiqueta, que no
        # depende de los prefijos declarados. Con `getpath`, que sí los usa, la
        # copia no los tiene declarados en su contexto de evaluación y lxml
        # responde «Undefined namespace prefix» en cualquier documento con
        # prefijos —o sea, en todos los Facturae firmados—.
        ruta = raiz.getroottree().getelementpath(firma)
        gemela = arbol.find(ruta)
        if gemela is None:
            return None, "no se ha podido aislar la firma para quitarla"
        gemela.getparent().remove(gemela)
        return _canonicalizar(arbol, c14n), ""

    if not uri.startswith("#"):
        return None, "apunta a un fichero de fuera, que no tenemos"

    objetivo = _por_identificador(raiz, uri[1:])
    if objetivo is None:
        return None, f"apunta a «{uri}», que no está en el documento"
    return _canonicalizar(objetivo, c14n), ""


# --- Las reglas ------------------------------------------------------------


def _regla_referencias(raiz, firma, donde: str) -> list[Incidencia]:
    """Que cada trozo firmado siga diciendo lo que decía al firmarlo.

    Esta es la comprobación que más vale de todo el módulo, y no necesita
    ninguna clave: es un resumen criptográfico contra otro. Si falla, el
    documento se ha modificado después de firmarse —a mano, o por una
    herramienta que lo volvió a guardar—.
    """
    incidencias: list[Incidencia] = []
    referencias = firma.xpath(".//*[local-name()='Reference']")
    if not referencias:
        return [
            Incidencia(
                "FIRMA-VACIA",
                ERROR,
                "La firma no cubre nada: no tiene ni una referencia. Está "
                "puesta, pero no garantiza ninguna parte del documento.",
                campo=f"{donde}Firma electrónica",
                encontrado="0 referencias",
            )
        ]

    for numero, referencia in enumerate(referencias, start=1):
        uri = referencia.get("URI")
        nombre = "el documento entero" if uri == "" else f"«{uri}»"
        metodo = referencia.xpath("./*[local-name()='DigestMethod']/@Algorithm")
        alg = _RESUMEN.get(metodo[0] if metodo else "")
        declarado = _hijo(referencia, "DigestValue")
        if alg is None or declarado is None or declarado.text is None:
            incidencias.append(
                Incidencia(
                    "FIRMA-SIN-COMPROBAR",
                    AVISO,
                    f"No se ha podido comprobar la parte firmada {nombre}: el "
                    "resumen usa un algoritmo que no conocemos o no viene.",
                    campo=f"{donde}Firma · referencia {numero}",
                    encontrado=metodo[0] if metodo else "(sin algoritmo)",
                )
            )
            continue

        octetos, motivo = _contenido_referenciado(raiz, firma, referencia)
        if octetos is None:
            incidencias.append(
                Incidencia(
                    "FIRMA-SIN-COMPROBAR",
                    AVISO,
                    f"No se ha podido comprobar la parte firmada {nombre}: "
                    f"{motivo}.",
                    campo=f"{donde}Firma · referencia {numero}",
                    encontrado=uri or "(sin URI)",
                )
            )
            continue

        calculado = base64.b64encode(hashlib.new(alg, octetos).digest()).decode()
        if calculado != "".join(declarado.text.split()):
            incidencias.append(
                Incidencia(
                    "FIRMA-ALTERADA",
                    ERROR,
                    f"El documento se ha modificado después de firmarlo: "
                    f"{nombre} ya no coincide con el resumen que guarda la "
                    "firma. La factura no vale como documento firmado.",
                    campo=f"{donde}Firma · referencia {numero}",
                    esperado=f"resumen {declarado.text.strip()[:24]}…",
                    encontrado=f"resumen {calculado[:24]}…",
                )
            )
    return incidencias


def _regla_valor(raiz, firma, cert: Certificado | None, donde: str) -> list[Incidencia]:
    """Que la firma la hiciera la clave privada del certificado que se enseña."""
    firmado = _hijo(firma, "SignedInfo")
    if firmado is None:
        return []
    metodo = firmado.xpath("./*[local-name()='SignatureMethod']/@Algorithm")
    pareja = _FIRMA.get(metodo[0] if metodo else "")
    valor = _texto_b64(_hijo(firma, "SignatureValue"))

    incidencias: list[Incidencia] = []
    if pareja is None:
        return [
            Incidencia(
                "FIRMA-SIN-COMPROBAR",
                AVISO,
                "No se ha podido comprobar la firma: usa un algoritmo que no "
                "conocemos. Solo se sabe verificar RSA.",
                campo=f"{donde}Algoritmo de firma",
                encontrado=metodo[0] if metodo else "(no dice)",
            )
        ]
    alg, obsoleto = pareja
    if obsoleto:
        incidencias.append(
            Incidencia(
                "FIRMA-DEBIL",
                AVISO,
                "La firma usa SHA-1, que está retirado para firma electrónica "
                "desde hace años porque se sabe fabricar colisiones. La firma "
                "puede ser auténtica; el algoritmo ya no da garantías.",
                campo=f"{donde}Algoritmo de firma",
                esperado="RSA con SHA-256 o mejor",
                encontrado="RSA con SHA-1",
            )
        )
    if cert is not None and cert.bits < BITS_MINIMOS:
        incidencias.append(
            Incidencia(
                "FIRMA-DEBIL",
                AVISO,
                f"La clave del certificado es de {cert.bits} bits. Para firma "
                f"electrónica se piden {BITS_MINIMOS} como mínimo.",
                campo=f"{donde}Clave del certificado",
                esperado=f"{BITS_MINIMOS} bits o más",
                encontrado=f"{cert.bits} bits",
            )
        )

    if valor is None or cert is None:
        return incidencias

    declarado = firmado.xpath("./*[local-name()='CanonicalizationMethod']/@Algorithm")
    octetos = _canonicalizar(firmado, declarado[0] if declarado else None)
    if octetos is None:
        incidencias.append(
            Incidencia(
                "FIRMA-SIN-COMPROBAR",
                AVISO,
                "No se ha podido comprobar la firma: canonicaliza con un "
                "método que no sabemos reproducir.",
                campo=f"{donde}Canonicalización",
                encontrado=declarado[0] if declarado else "(no dice)",
            )
        )
        return incidencias

    if not _verificar_rsa(valor, octetos, cert, alg):
        incidencias.append(
            Incidencia(
                "FIRMA-NO-CUADRA",
                ERROR,
                "La firma no cuadra con el certificado que trae el documento. "
                "O se ha manipulado la firma, o el certificado no es el que se "
                "usó para firmar.",
                campo=f"{donde}Valor de la firma",
                encontrado="no verifica",
            )
        )
    return incidencias


def _regla_certificado(
    firma, cert: Certificado | None, cuando: datetime | None, donde: str
) -> list[Incidencia]:
    """Vigencia del certificado, y que sea el que la firma dice haber usado."""
    incidencias: list[Incidencia] = []
    if cert is None:
        return incidencias

    if cuando is not None and cert.desde and cert.hasta:
        if not (cert.desde <= cuando <= cert.hasta):
            quien = f" ({cert.sujeto})" if cert.sujeto else ""
            incidencias.append(
                Incidencia(
                    "FIRMA-CADUCADA",
                    ERROR,
                    f"El certificado{quien} no estaba vigente el día que dice "
                    "haberse firmado la factura.",
                    campo=f"{donde}Vigencia del certificado",
                    esperado=(
                        f"entre {cert.desde.date().isoformat()} y "
                        f"{cert.hasta.date().isoformat()}"
                    ),
                    encontrado=f"firmada el {cuando.date().isoformat()}",
                )
            )

    # XAdES guarda el resumen del certificado con el que se firmó, dentro de
    # las propiedades que la propia firma cubre. Si el certificado que viene en
    # el `KeyInfo` no es ese, alguien lo ha cambiado por el camino.
    guardado = None
    for propiedades in firma.xpath(".//*[local-name()='SigningCertificate']") + firma.xpath(
        ".//*[local-name()='SigningCertificateV2']"
    ):
        metodo = propiedades.xpath(".//*[local-name()='DigestMethod']/@Algorithm")
        valor = propiedades.xpath(".//*[local-name()='DigestValue']/text()")
        if metodo and valor:
            guardado = (_RESUMEN.get(metodo[0]), "".join(valor[0].split()))
        break
    if guardado is None or guardado[0] is None:
        return incidencias

    presentado = firma.xpath(".//*[local-name()='X509Certificate']/text()")
    if not presentado:
        return incidencias
    der = base64.b64decode("".join(presentado[0].split()))
    calculado = base64.b64encode(hashlib.new(guardado[0], der).digest()).decode()
    if calculado != guardado[1]:
        incidencias.append(
            Incidencia(
                "FIRMA-OTRO-CERTIFICADO",
                ERROR,
                "El certificado que trae el documento no es el que la firma "
                "dice haber usado. Alguien lo ha sustituido.",
                campo=f"{donde}Certificado firmante",
                esperado=f"resumen {guardado[1][:24]}…",
                encontrado=f"resumen {calculado[:24]}…",
            )
        )
    return incidencias


def momento_de_firma(firma) -> datetime | None:
    """La fecha que la firma declara. **No es prueba de nada por sí sola.**

    Sin sello de tiempo de un tercero, esta fecha la escribe quien firma y
    puede poner la que quiera. Sirve para comprobar la vigencia del certificado
    contra lo que el propio documento afirma, que es mejor que nada, no para
    demostrar cuándo se firmó.
    """
    for nodo in firma.xpath(".//*[local-name()='SigningTime']"):
        crudo = (nodo.text or "").strip()
        if not crudo:
            continue
        try:
            momento = datetime.fromisoformat(crudo.replace("Z", "+00:00"))
        except ValueError:
            continue
        return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)
    return None


def _regla_es_xades(firma, donde: str) -> list[Incidencia]:
    if firma.xpath(".//*[local-name()='QualifyingProperties']"):
        return []
    return [
        Incidencia(
            "FIRMA-NO-XADES",
            AVISO,
            "La firma es XML-DSig a secas, sin las propiedades XAdES. Facturae "
            "pide XAdES, que es lo que añade la fecha de firma, el certificado "
            "declarado y la política de firma.",
            campo=f"{donde}Tipo de firma",
            esperado="XAdES",
            encontrado="XML-DSig sin propiedades",
        )
    ]


def _sin_firmar(deteccion: Deteccion) -> list[Incidencia]:
    if deteccion.familia != FACTURAE:
        # En UBL y CII la firma no es parte del formato: se firma por fuera, en
        # el sobre del envío. Echarla de menos aquí sería inventarse un
        # requisito que esas sintaxis no tienen.
        return []
    return [
        Incidencia(
            "FIRMA-FALTA",
            AVISO,
            "La factura no está firmada. El esquema de Facturae lo dice de su "
            "propio bloque de firma: hace falta «para que se considere una "
            "factura electrónica válida legalmente frente a terceros».",
            campo="Firma electrónica",
            encontrado="(no hay)",
        )
    ]


def reglas(raiz, deteccion: Deteccion) -> list[Incidencia]:
    """Lo que se puede decir de la firma de un documento sin salir a la red."""
    if raiz is None or not deteccion:
        return []

    firmas = hay_firma(raiz)
    if not firmas:
        return _sin_firmar(deteccion)

    incidencias: list[Incidencia] = []
    for numero, firma in enumerate(firmas, start=1):
        donde = f"Firma {numero} · " if len(firmas) > 1 else ""
        certificado = None
        crudo = firma.xpath(".//*[local-name()='X509Certificate']/text()")
        if crudo:
            try:
                certificado = leer_certificado(
                    base64.b64decode("".join(crudo[0].split()))
                )
            except (ValueError, IndexError, binascii.Error):
                incidencias.append(
                    Incidencia(
                        "FIRMA-SIN-COMPROBAR",
                        AVISO,
                        "No se ha podido leer el certificado del documento, "
                        "así que no se ha comprobado la firma. El resto de la "
                        "factura sí se ha mirado.",
                        campo=f"{donde}Certificado",
                        encontrado="(ilegible)",
                    )
                )
        else:
            incidencias.append(
                Incidencia(
                    "FIRMA-SIN-CERTIFICADO",
                    AVISO,
                    "La firma no trae el certificado con el que se hizo, así "
                    "que no hay con qué comprobarla. Quien reciba la factura "
                    "tendría que conseguirlo por otro lado.",
                    campo=f"{donde}Certificado",
                    encontrado="(no viene)",
                )
            )

        incidencias.extend(_regla_es_xades(firma, donde))
        incidencias.extend(_regla_referencias(raiz, firma, donde))
        incidencias.extend(_regla_valor(raiz, firma, certificado, donde))
        incidencias.extend(
            _regla_certificado(firma, certificado, momento_de_firma(firma), donde)
        )
    return incidencias
