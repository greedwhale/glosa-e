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
           "leer_certificado", "Certificado", "ALGORITMOS_ROTOS",
           "ClaveNoSoportada", "verificar", "CURVAS", "Curva"]

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
    "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha1": ("sha1", True),
    "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256": ("sha256", False),
    "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha384": ("sha384", False),
    "http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha512": ("sha512", False),
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

    # De qué clase es la clave: "rsa" o "ecdsa". Por defecto RSA para no
    # romper a quien construya un `Certificado` a mano —los tests lo hacen—.
    algoritmo_clave: str = "rsa"
    # Solo con curva: el nombre de la curva y el punto (x, y) de la clave.
    curva: str = ""
    punto: tuple[int, int] | None = None

    # Para la cadena. Todo opcional para no romper a quien construya un
    # Certificado a mano —los tests lo hacen— sin querer saber de cadenas.
    der: bytes = b""
    tbs: bytes = b""  # lo que el emisor firmó, tal cual venía
    sujeto_der: bytes = b""
    emisor_der: bytes = b""
    emisor_nombre: str | None = None
    # El número de serie, que es como se busca un certificado en una lista
    # de revocación: el par (emisor, serie) es lo que lo identifica.
    serie: int = 0
    algoritmo_firma: str | None = None  # "sha256", o None si no lo conocemos
    valor_firma: bytes = b""
    es_autoridad: bool | None = None  # basicConstraints cA
    profundidad_max: int | None = None  # pathLenConstraint
    usos: frozenset[str] = frozenset()  # keyUsage
    criticas_sin_entender: frozenset[str] = frozenset()
    # Todas las extensiones sin abrir, por OID. En tuplas y no en un dict
    # porque este dataclass es `frozen` y por tanto se puede usar como clave;
    # un dict dentro rompería el hash el día que alguien lo intente.
    extensiones: tuple[tuple[str, bytes], ...] = ()

    def extension(self, oid: str) -> bytes | None:
        """El contenido de una extensión, tal cual, por su OID en hexadecimal."""
        for cual, valor in self.extensiones:
            if cual == oid:
                return valor
        return None

    @property
    def bits(self) -> int:
        """El tamaño de la clave, en bits.

        Ojo con compararlo entre algoritmos: 256 bits de curva equivalen a unos
        3072 de RSA. Para «¿es corta?» está `clave_debil`, que sabe contra qué
        mínimo va cada una.
        """
        if self.algoritmo_clave == "ecdsa":
            curva = CURVAS_POR_NOMBRE.get(self.curva)
            return curva.n.bit_length() if curva else 0
        return self.modulo.bit_length()

    @property
    def clave_debil(self) -> bool:
        """¿Es esta clave demasiado corta para firma electrónica?

        Cada algoritmo con su mínimo. Con uno solo —los 2048 de RSA— cualquier
        certificado de curva perfectamente bueno saldría marcado como débil por
        tener «solo» 256 bits, que es justo al revés de la realidad.
        """
        minimo = (
            BITS_MINIMOS_CURVA if self.algoritmo_clave == "ecdsa"
            else BITS_MINIMOS
        )
        return 0 < self.bits < minimo

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
    # Con curva elíptica. Aquí solo se guarda el resumen: **con qué esquema se
    # verifica lo decide la clave del firmante**, no este OID. Quien firmó solo
    # pudo usar lo que su clave permite, y si el OID dice otra cosa lo que hay
    # es una incoherencia, no una instrucción.
    "2a8648ce3d0401": ("sha1", True),  # ecdsa-with-SHA1
    "2a8648ce3d040302": ("sha256", False),
    "2a8648ce3d040303": ("sha384", False),
    "2a8648ce3d040304": ("sha512", False),
}
ALGORITMOS_ROTOS = frozenset(
    alg for alg, roto in _OID_ALGORITMO.values() if roto
)

_OID_BASIC_CONSTRAINTS = "551d13"  # 2.5.29.19
_OID_KEY_USAGE = "551d0f"  # 2.5.29.15

# Qué clase de clave lleva el certificado. Aquí solo se sabe verificar RSA, y
# lo que importa es **decirlo bien**: sin mirar este OID, un certificado de
# curva elíptica —bien formado, y son 46 de las 129 autoridades cualificadas
# concedidas de la lista española— reventaba con «DER truncado», que es una
# acusación falsa contra el fichero. El que no sabe leerlo somos nosotros.
_OID_RSA = "2a864886f70d010101"  # 1.2.840.113549.1.1.1
_OID_EC = "2a8648ce3d0201"  # 1.2.840.10045.2.1, id-ecPublicKey
_CLAVES_QUE_NO_SABEMOS = {
    "2b6570": "Ed25519",  # 1.3.101.112
    "2b6571": "Ed448",  # 1.3.101.113
    "2a8648ce380401": "DSA",  # 1.2.840.10040.4.1
}


class ClaveNoSoportada(ValueError):
    """El certificado se lee bien; su clave no es de las que sabemos usar.

    Hereda de `ValueError` para no romper a quien ya capturaba eso al leer una
    carpeta de certificados. Es una clase aparte para que quien quiera pueda
    distinguir «este fichero está roto» de «este fichero está bien y el corto
    soy yo», que no son la misma noticia ni llevan a la misma acción.
    """

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
    todas: list[tuple[str, bytes]] = []
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
            todas.append((identificador, valor))
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
    return es_ca, profundidad, frozenset(usos), frozenset(criticas), tuple(todas)


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
    # Primero **de qué clase es la clave**, y solo después leerla. Al revés se
    # intenta parsear el punto de una curva elíptica como si fuera una
    # SEQUENCE de dos enteros, y lo que sale es un error de DER sobre un
    # fichero que no tiene nada de malo. Ver `_CLAVES_QUE_NO_SABEMOS`.
    tipo = _elementos(spki[0][1]) if spki else []
    cual = _oid(tipo[0][1]) if tipo and tipo[0][0] == 0x06 else ""
    if cual == _OID_EC:
        return _certificado_de_curva(der, tbs, campos, salto, spki, tipo, partes)
    if cual != _OID_RSA:
        nombre = _CLAVES_QUE_NO_SABEMOS.get(cual)
        raise ClaveNoSoportada(
            f"la clave es {nombre}" if nombre
            else f"la clave no es RSA (OID {cual or 'ilegible'})"
        )
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

    es_ca, profundidad, usos, criticas, todas = _leer_extensiones(campos, salto)
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
        serie=int.from_bytes(campos[salto][1], "big") if campos[salto][1] else 0,
        algoritmo_firma=algoritmo,
        valor_firma=valor_firma,
        es_autoridad=es_ca,
        profundidad_max=profundidad,
        usos=usos,
        criticas_sin_entender=criticas,
        extensiones=todas,
    )



def _certificado_de_curva(der, tbs, campos, salto, spki, tipo, partes):
    """La parte de `leer_certificado` que cambia cuando la clave es de curva.

    Lo único distinto es la clave: el resto del certificado —nombres, fechas,
    serie, extensiones— se lee igual, y por eso se reaprovecha entero.
    """
    cual = _oid(tipo[1][1]) if len(tipo) > 1 and tipo[1][0] == 0x06 else ""
    curva = CURVAS.get(cual)
    if curva is None:
        raise ClaveNoSoportada(
            f"la clave usa una curva que aquí no se conoce (OID {cual or 'ilegible'})"
        )
    bits = spki[1][1]
    if not bits or bits[0] != 0:
        raise ValueError("la clave pública no empieza en un byte entero")
    punto = bits[1:]
    if not punto or punto[0] != 0x04:
        # Comprimido (0x02 / 0x03) o vacío. Se podría descomprimir —las tres
        # curvas tienen p ≡ 3 mod 4 y la raíz sale de una potencia— pero no
        # hay ni uno así en circulación: los 63 de la lista española van sin
        # comprimir. Escribirlo sería código que nadie ejerce.
        raise ClaveNoSoportada(
            "la clave de curva viene comprimida y aquí no se sabe descomprimir"
        )
    if len(punto) != curva.octetos * 2 + 1:
        raise ValueError("el punto de la clave no tiene el tamaño de su curva")
    x = int.from_bytes(punto[1 : curva.octetos + 1], "big")
    y = int.from_bytes(punto[curva.octetos + 1 :], "big")
    if not curva.encima(x, y):
        # Un punto fuera de la curva no es una clave pública: es otra cosa, y
        # lo que salga de operar con él no significa nada. Se para aquí y no al
        # verificar, para que el mensaje diga lo que pasa.
        raise ValueError("la clave dice ser de una curva y su punto no está en ella")

    algoritmo = None
    algoritmos = _elementos(partes[1][1])
    if algoritmos and algoritmos[0][0] == 0x06:
        pareja = _OID_ALGORITMO.get(_oid(algoritmos[0][1]))
        algoritmo = pareja[0] if pareja else None
    valor_firma = partes[2][1][1:] if partes[2][1][:1] == b"\x00" else b""
    validez = _elementos(campos[salto + 3][1])
    es_ca, profundidad, usos, criticas, todas = _leer_extensiones(campos, salto)
    return Certificado(
        modulo=0,
        exponente=0,
        desde=_fecha_der(*validez[0]) if len(validez) > 0 else None,
        hasta=_fecha_der(*validez[1]) if len(validez) > 1 else None,
        sujeto=_nombre_der(campos[salto + 4][1]),
        algoritmo_clave="ecdsa",
        curva=curva.nombre,
        punto=(x, y),
        der=der,
        tbs=tbs,
        sujeto_der=_reserializar(campos[salto + 4]),
        emisor_der=_reserializar(campos[salto + 2]),
        emisor_nombre=_nombre_der(campos[salto + 2][1]),
        serie=int.from_bytes(campos[salto][1], "big") if campos[salto][1] else 0,
        algoritmo_firma=algoritmo,
        valor_firma=valor_firma,
        es_autoridad=es_ca,
        profundidad_max=profundidad,
        usos=usos,
        criticas_sin_entender=criticas,
        extensiones=todas,
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



# --- Curva elíptica --------------------------------------------------------
#
# Hace falta porque 46 de las 129 autoridades cualificadas concedidas de la
# lista de confianza española firman con curva elíptica. Sin esto, un tercio
# de las autoridades de España se quedaba fuera del almacén de anclas.
#
# Aquí tampoco hay dependencias nuevas: una curva es aritmética de enteros
# módulo un primo, igual que RSA. Lo que cambia es que el grupo no son los
# enteros sino los puntos de la curva, y que hay que escribir la suma.


@dataclass(frozen=True)
class Curva:
    """Una curva de Weierstrass sobre Fp: y² = x³ + ax + b, con a = -3.

    Las tres del NIST llevan a = -3 y por eso no hace falta guardarlo: es la
    elección que permite la fórmula corta de duplicar un punto. No hay ninguna
    curva de las otras en circulación aquí —comprobado sobre la lista española,
    donde solo aparecen P-256, P-384 y P-521—, así que soportar una `a`
    cualquiera sería código sin caso de uso y sin nadie que lo probara.
    """

    nombre: str
    p: int
    b: int
    gx: int
    gy: int
    n: int

    @property
    def octetos(self) -> int:
        """Lo que ocupa una coordenada. Fija, y con sus ceros por delante."""
        return (self.p.bit_length() + 7) // 8

    def encima(self, x: int, y: int) -> bool:
        """¿Está este punto en la curva?

        Se comprueba siempre, con la misma idea que reconstruir el relleno de
        RSA en vez de leerlo: un punto que no está en la curva no es una clave
        pública, es otra cosa, y lo que salga de operar con él no significa
        nada. Cuesta una multiplicación.
        """
        if not (0 <= x < self.p and 0 <= y < self.p):
            return False
        return (y * y - (x * x % self.p * x - 3 * x + self.b)) % self.p == 0


# Los parámetros van escritos a mano, así que **se comprueban**: que el
# generador esté en la curva y que n·G sea el punto del infinito. Las dos
# comprobaciones están en los tests y no son ceremonia: al escribirlos la
# primera vez se perdieron dos dígitos de la `n` de P-521 en un corte de línea,
# y una constante mal no da un error —da «esta firma no verifica», que es
# indistinguible de una firma falsificada—.
CURVAS = {
    # secp256r1 / prime256v1, OID 1.2.840.10045.3.1.7
    "2a8648ce3d030107": Curva(
        "P-256",
        p=0xFFFFFFFF00000001000000000000000000000000FFFFFFFFFFFFFFFFFFFFFFFF,
        b=0x5AC635D8AA3A93E7B3EBBD55769886BC651D06B0CC53B0F63BCE3C3E27D2604B,
        gx=0x6B17D1F2E12C4247F8BCE6E563A440F277037D812DEB33A0F4A13945D898C296,
        gy=0x4FE342E2FE1A7F9B8EE7EB4A7C0F9E162BCE33576B315ECECBB6406837BF51F5,
        n=0xFFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551,
    ),
    # secp384r1, OID 1.3.132.0.34
    "2b81040022": Curva(
        "P-384",
        p=int("fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffe"
              "ffffffff0000000000000000ffffffff", 16),
        b=int("b3312fa7e23ee7e4988e056be3f82d19181d9c6efe8141120314088f5013875a"
              "c656398d8a2ed19d2a85c8edd3ec2aef", 16),
        gx=int("aa87ca22be8b05378eb1c71ef320ad746e1d3b628ba79b9859f741e082542a38"
               "5502f25dbf55296c3a545e3872760ab7", 16),
        gy=int("3617de4a96262c6f5d9e98bf9292dc29f8f41dbd289a147ce9da3113b5f0b8c0"
               "0a60b1ce1d7e819d7a431d7c90ea0e5f", 16),
        n=int("ffffffffffffffffffffffffffffffffffffffffffffffffc7634d81f4372ddf"
              "581a0db248b0a77aecec196accc52973", 16),
    ),
    # secp521r1, OID 1.3.132.0.35
    "2b81040023": Curva(
        "P-521",
        p=2**521 - 1,
        b=int("0051953eb9618e1c9a1f929a21a0b68540eea2da725b99b315f3b8b489918ef1"
              "09e156193951ec7e937b1652c0bd3bb1bf073573df883d2c34f1ef451fd46b50"
              "3f00", 16),
        gx=int("00c6858e06b70404e9cd9e3ecb662395b4429c648139053fb521f828af606b4d"
               "3dbaa14b5e77efe75928fe1dc127a2ffa8de3348b3c1856a429bf97e7e31c2e5"
               "bd66", 16),
        gy=int("011839296a789a3bc0045c8a5fb42c7d1bd998f54449579b446817afbd17273e"
               "662c97ee72995ef42640c550b9013fad0761353c7086a272c24088be94769fd1"
               "6650", 16),
        # 66 octetos: 01, luego 32 de ff, y la cola. Escrito así, y no de
        # corrido, porque contar efes a ojo es justo lo que salió mal.
        n=int("01" + "f" * 64
              + "fa51868783bf2f966b7fcc0148f709a5d03bb5c9b8899c47aebb6fb71e913"
                "86409", 16),
    ),
}
CURVAS_POR_NOMBRE = {curva.nombre: curva for curva in CURVAS.values()}

# Por debajo de esto una curva se considera corta. 256 bits de curva equivalen
# a unos 3072 de RSA, así que comparar los dos con el mismo número sería un
# disparate: una clave P-256 perfectamente buena saldría marcada como débil por
# tener «solo 256 bits».
BITS_MINIMOS_CURVA = 224


# Los puntos van en coordenadas jacobianas —(X, Y, Z) representa (X/Z², Y/Z³)—
# y no en las de toda la vida. El motivo es de peso: en coordenadas normales
# cada suma necesita un inverso modular, y una verificación son unos cientos de
# sumas. Medido, P-521 pasa de 200 ms a 33, y esto tiene que correr también
# dentro del navegador. El precio es que las fórmulas no se leen solas; la
# defensa es que hay una prueba que las contrasta contra la versión lenta y
# evidente, que es la que sí se lee.
_INFINITO = (0, 0, 0)


def _doblar(punto, p: int):
    x, y, z = punto
    if y == 0 or z == 0:
        return _INFINITO
    a = y * y % p
    b = 4 * x * a % p
    c = 8 * a * a % p
    zz = z * z % p
    d = 3 * (x - zz) * (x + zz) % p  # esta forma solo vale con a = -3
    x3 = (d * d - 2 * b) % p
    return (x3, (d * (b - x3) - c) % p, 2 * y * z % p)


def _sumar(uno, otro, p: int):
    if uno[2] == 0:
        return otro
    if otro[2] == 0:
        return uno
    x1, y1, z1 = uno
    x2, y2, z2 = otro
    z1z1 = z1 * z1 % p
    z2z2 = z2 * z2 % p
    u1 = x1 * z2z2 % p
    u2 = x2 * z1z1 % p
    s1 = y1 * z2 % p * z2z2 % p
    s2 = y2 * z1 % p * z1z1 % p
    if u1 == u2:
        return _doblar(uno, p) if s1 == s2 else _INFINITO
    h = (u2 - u1) % p
    r = (s2 - s1) % p
    hh = h * h % p
    hhh = h * hh % p
    u1hh = u1 * hh % p
    x3 = (r * r - hhh - 2 * u1hh) % p
    return (x3, (r * (u1hh - x3) - s1 * hhh) % p, h * z1 % p * z2 % p)


def _combinar(k1: int, uno, k2: int, otro, p: int):
    """k1·uno + k2·otro de una vez, que es lo que pide verificar ECDSA.

    Hacerlo a la vez —el truco de Shamir— ahorra la mitad de los dobles, que
    es la operación cara. Calcularlos por separado y sumar da lo mismo y tarda
    casi el doble.
    """
    a = (uno[0], uno[1], 1)
    b = (otro[0], otro[1], 1)
    ambos = _sumar(a, b, p)
    salida = _INFINITO
    for i in range(max(k1.bit_length(), k2.bit_length()) - 1, -1, -1):
        salida = _doblar(salida, p)
        cual = ((k1 >> i) & 1) | (((k2 >> i) & 1) << 1)
        if cual == 3:
            salida = _sumar(salida, ambos, p)
        elif cual == 1:
            salida = _sumar(salida, a, p)
        elif cual == 2:
            salida = _sumar(salida, b, p)
    if salida[2] == 0:
        return None
    inverso = pow(salida[2], -1, p)
    cuadrado = inverso * inverso % p
    return (salida[0] * cuadrado % p, salida[1] * cuadrado % p * inverso % p)


def _pareja(firma: bytes, curva: Curva, concatenada: bool):
    """Los dos números (r, s) de una firma ECDSA, vengan como vengan.

    Y vienen de dos formas distintas, que es una trampa con nombre: dentro de
    un certificado o de una CRL la firma es DER —`SEQUENCE { r, s }`—, y dentro
    de una firma XML es la concatenación cruda de los dos, cada uno relleno con
    ceros hasta el tamaño de la curva. Confundirlas no da un error de formato:
    da una firma buena que no verifica.
    """
    if concatenada:
        if len(firma) != curva.octetos * 2:
            return None
        mitad = curva.octetos
        return (
            int.from_bytes(firma[:mitad], "big"),
            int.from_bytes(firma[mitad:], "big"),
        )
    try:
        etiqueta, dentro, sobra = _tlv(firma)
    except (ValueError, IndexError):
        return None
    if etiqueta != 0x30 or sobra != len(firma):
        return None
    numeros = _elementos(dentro)
    if len(numeros) != 2 or any(e != 0x02 for e, _ in numeros):
        return None
    return (
        int.from_bytes(numeros[0][1], "big", signed=True),
        int.from_bytes(numeros[1][1], "big", signed=True),
    )


def _verificar_ecdsa(
    firma: bytes, mensaje: bytes, cert: Certificado, alg: str,
    concatenada: bool = False,
) -> bool:
    """¿Sale este mensaje de firmar con la clave privada de este certificado?

    ECDSA del FIPS 186-4, tal cual: se rechaza todo lo que esté fuera de rango
    —r y s tienen que estar entre 1 y n-1— antes de tocar la curva. Ese
    filtro no es cosmético: sin él, una firma con s = 0 o r = 0 pasa por
    caminos donde el resultado no significa nada.

    El resumen se recorta por la izquierda al tamaño de n, que es lo que dice
    la norma y no lo que sale de escribirlo a ojo: con P-256 y SHA-384 hay que
    tirar 128 bits, y quien no lo haga verifica mal exactamente las firmas
    donde el resumen es más largo que la curva.
    """
    curva = CURVAS_POR_NOMBRE.get(cert.curva)
    if curva is None or cert.punto is None or alg not in _DIGESTINFO:
        return False
    pareja = _pareja(firma, curva, concatenada)
    if pareja is None:
        return False
    r, s = pareja
    n = curva.n
    if not (1 <= r < n and 1 <= s < n):
        return False
    if not curva.encima(*cert.punto):
        return False

    resumen = hashlib.new(alg, mensaje).digest()
    z = int.from_bytes(resumen, "big")
    sobran = len(resumen) * 8 - n.bit_length()
    if sobran > 0:
        z >>= sobran

    inverso = pow(s, -1, n)
    punto = _combinar(
        z * inverso % n, (curva.gx, curva.gy),
        r * inverso % n, cert.punto,
        curva.p,
    )
    if punto is None:
        return False
    return punto[0] % n == r


def verificar(
    firma: bytes, mensaje: bytes, cert: Certificado, alg: str,
    concatenada: bool = False,
) -> bool:
    """Verifica una firma, sea RSA o ECDSA, según la clave del certificado.

    Se decide por **la clave y no por el algoritmo declarado**: quien firmó
    solo pudo usar el esquema que su clave permite, y si el OID declarado dice
    otra cosa lo que hay es una incoherencia, no una instrucción que seguir.
    """
    if cert.algoritmo_clave == "ecdsa":
        return _verificar_ecdsa(firma, mensaje, cert, alg, concatenada)
    return _verificar_rsa(firma, mensaje, cert, alg)


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
        return None, f"lleva una transformación que aquí no se sabe aplicar: {desconocidas[0]}"

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
        return None, "apunta a un fichero de fuera, que aquí no está"

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
                    "resumen usa un algoritmo que aquí no se conoce, o no viene.",
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
                "No se ha podido comprobar la firma: usa un algoritmo que aquí "
                "no se conoce. Solo se sabe verificar RSA.",
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
    if cert is not None and cert.clave_debil:
        de_curva = cert.algoritmo_clave == "ecdsa"
        minimo = BITS_MINIMOS_CURVA if de_curva else BITS_MINIMOS
        que = f"de curva {cert.curva}" if de_curva else "RSA"
        incidencias.append(
            Incidencia(
                "FIRMA-DEBIL",
                AVISO,
                f"La clave {que} del certificado es de {cert.bits} bits. Para "
                f"firma electrónica se piden {minimo} como mínimo.",
                campo=f"{donde}Clave del certificado",
                esperado=f"{minimo} bits o más",
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
                "método que aquí no se sabe reproducir.",
                campo=f"{donde}Canonicalización",
                encontrado=declarado[0] if declarado else "(no dice)",
            )
        )
        return incidencias

    # `concatenada` porque en XML-DSig una firma de curva son los dos números
    # pegados y rellenos con ceros, no el DER que llevan los certificados.
    if not verificar(valor, octetos, cert, alg, concatenada=True):
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
