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
3. **Que lo que la firma cubre sea esta factura.** Las tres de arriba se pueden
   cumplir todas sobre otro documento: una firma XAdES de cualquiera sobre
   cualquier cosa se despega y se cuelga de una factura inventada, y sigue
   verificando entera porque lo que cubre viaja con ella. Ver `_regla_cubre`.
4. **Que el certificado estuviera vigente** en la fecha que la firma declara,
   que se lee **de lo firmado** y no de cualquier sitio: ver
   `propiedades_firmadas`.
5. **Que el certificado que se presenta sea el que la firma dice haber usado**
   (la propiedad `SigningCertificate` de XAdES guarda su resumen).
6. **Que los algoritmos no estén obsoletos.**

Las tres cosas de las que sale «esta firma se sostiene» —que el valor cuadre,
que ninguna referencia esté alterada y que alguna cubra la factura— las junta
`examinar`, y ahí las mira también `cadena.py` antes de decir de quién es el
certificado. Que cada uno lo mirara por su cuenta es lo que permitía que el
informe no comprobara una firma y aun así nombrara a su firmante.

**De quién es el certificado lo responde `cadena.py`**, encadenándolo hasta un
ancla de confianza instalada. Aquí no: aquí solo se mira el certificado que el
documento enseña, sin preguntarse quién lo avala.

**No se comprueba en ninguno de los dos**:

- Que el certificado no esté revocado. Exige OCSP o CRL, o sea red, o que el
  documento traiga la prueba dentro (XAdES-XL).
- Los sellos de tiempo (XAdES-T y por encima).
- Que quien firma esté autorizado a facturar por ese NIF.

Traducido: este módulo responde **«¿alguien ha cambiado este documento después
de firmarlo?»**, **«¿la firma cuadra con el certificado que trae dentro?»** y
**«¿es esta factura lo que se firmó?»**. Un documento firmado con un
certificado que el remitente se haya inventado pasa las seis comprobaciones de
aquí; lo caza `cadena.py` si hay anclas puestas.

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

from validador.formato import (
    FACTURAE,
    FIRMA_EN_PIE,
    FIRMA_ROTA,
    FIRMA_SIN_COMPROBAR,
    NS_FIRMA,
    Deteccion,
)
from validador.incidencias import AVISO, ERROR, Incidencia

__all__ = ["reglas", "hay_firma", "certificados_de", "momento_de_firma",
           "leer_certificado", "Certificado", "ALGORITMOS_ROTOS",
           "ClaveNoSoportada", "verificar", "CURVAS", "Curva",
           "examinar", "Examen", "Comprobada", "referencias_de",
           "comprobar_referencia", "propiedades_firmadas",
           "examinar_todas", "estado_de_la_firma"]

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
# Los dos usos de keyUsage con los que se firma un documento: digitalSignature
# y contentCommitment —el que antes se llamaba nonRepudiation—. Ver
# `_regla_valor`.
_USOS_DE_FIRMA = frozenset({"firma", "no_repudio"})

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


_NS = {"ds": NS_FIRMA}

# Las propiedades XAdES han pasado por tres namespaces —1.2.2, 1.3.1 y 1.3.2— y
# en las facturas reales conviven: de las 24 firmas del corpus, 5 declaran
# 1.2.2 y 17 la 1.3.2. Se reconocen por el prefijo común en vez de por una
# lista, y **no** por el nombre a secas: aceptar cualquier `SignedProperties`
# de cualquier namespace deja que valga un elemento inventado con ese nombre.
_XADES = "http://uri.etsi.org/01903/"


def _hijo(nodo, nombre: str):
    encontrados = nodo.xpath(f"./*[local-name()='{nombre}']")
    return encontrados[0] if encontrados else None


def _hijo_ds(nodo, nombre: str):
    """Un hijo del namespace de XML-DSig, y solo de ese.

    La diferencia con `_hijo` importa donde se decide algo: un
    `<x:SignatureValue>` de otro namespace no es el valor de una firma, y
    tratarlo como si lo fuera es dejar que quien escribe el documento elija qué
    se comprueba.
    """
    encontrados = nodo.xpath(f"./ds:{nombre}", namespaces=_NS)
    return encontrados[0] if encontrados else None


def _signedinfo(firma):
    """El `SignedInfo` **hijo** de la firma. El único que cuenta.

    Lo que el valor de la firma cubre es este bloque y nada más. Buscarlo por
    descendiente —o buscar las referencias por descendiente, que es lo que se
    hacía— deja que cuenten unas escritas en cualquier otro sitio de la firma,
    por ejemplo dentro de un `ds:Object`, que nadie firmó.
    """
    return _hijo_ds(firma, "SignedInfo")


def referencias_de(firma) -> list:
    """Las `Reference` que la firma cubre de verdad: las de su `SignedInfo`.

    **Este es el agujero número dos de la auditoría del 15-09-2026.** Estaban
    cogidas con `.//Reference`, o sea en cualquier parte de la firma. Un
    resumen es un hash y lo rehace cualquiera sin ninguna clave, así que
    bastaba colgar de un `ds:Object` una referencia al documento —con su
    resumen bien calculado— para que el validador diera por comprobado lo que
    la firma no cubría. Con el `SignedInfo` fuera de su sitio, además, no había
    valor de firma que comprobar y el informe salía **sin una sola queja**.
    """
    firmado = _signedinfo(firma)
    if firmado is None:
        return []
    return firmado.xpath("./ds:Reference", namespaces=_NS)


def _es_propiedades(nodo) -> bool:
    """¿Es este elemento unas `SignedProperties` de XAdES?"""
    if nodo is None:
        return False
    etiqueta = str(nodo.tag)
    return etiqueta.startswith("{" + _XADES) and etiqueta.endswith("}SignedProperties")


def _dentro_de(nodo, posible_antepasado) -> bool:
    """¿Cuelga `nodo` de `posible_antepasado`? (o es él mismo)"""
    if nodo is None or posible_antepasado is None:
        return False
    actual = nodo
    while actual is not None:
        if actual is posible_antepasado:
            return True
        actual = actual.getparent()
    return False


def factura_leida(raiz):
    """El elemento que las reglas leen como factura.

    Casi siempre es la raíz. Cuando la raíz es la propia firma —Facturae
    firmado «en envolvente», que está en el corpus— la factura cuelga de
    dentro, y `formato.detectar`, `facturae.py` y `en16931.py` se quedan con
    **el primer** `Facturae` que aparece. Aquí hay que mirar el mismo, porque
    la pregunta que se contesta es si la firma cubre lo que se está validando,
    no si cubre algo.
    """
    if raiz is None:
        return None
    if str(raiz.tag) == f"{{{NS_FIRMA}}}Signature":
        internos = raiz.xpath("//*[local-name()='Facturae']")
        if internos:
            return internos[0]
    return raiz


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
    """Los certificados del `KeyInfo` de la firma, el primero el que firma.

    XAdES permite meter la cadena entera en el `KeyInfo`, y lo normal es que el
    primero sea el del firmante. Los que no se puedan leer se saltan en
    silencio: de que falte el del firmante ya se queja `reglas`, y un
    intermedio ilegible solo significa que la cadena no llegará arriba.

    **Del `KeyInfo` y no de toda la firma.** Con `.//` entraban también los
    certificados de un `ds:Object` cualquiera —hay dos firmas así en el
    corpus— y el primero en orden de documento decidía con qué certificado se
    comprobaba todo. No permite falsificar nada, porque la firma tiene que
    cuadrar con el certificado que se elija, pero sí acusar en falso a un
    documento correcto al que alguien haya colgado un certificado de adorno.
    """
    salida = []
    for texto in firma.xpath("./ds:KeyInfo//ds:X509Certificate/text()", namespaces=_NS):
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


def _con_identificador(raiz, identificador: str) -> list:
    """**Todos** los elementos con ese identificador, no el primero.

    Que haya más de uno no es un detalle de higiene: un `Id` es único por
    definición del esquema, y quedarse con el primero que aparezca es la
    maniobra clásica contra los verificadores de XML firmado —se deja el
    elemento firmado donde estaba y se mete una copia con el mismo `Id`
    delante—. Aquí se cuentan para poder decir que no se sabe cuál es.
    """
    return raiz.xpath("//*[@Id=$i or @id=$i or @ID=$i]", i=identificador)


def _sin_esta_firma(raiz, firma):
    """Una copia del documento sin **esta** firma, que es lo que quita XAdES.

    «Esta» y no cualquiera: en un fichero con dos firmas, quitar la primera que
    aparezca daría otros bytes y la comprobación mentiría.
    """
    arbol = etree.fromstring(etree.tostring(raiz))
    # `getelementpath` da una ruta en notación {namespace}etiqueta, que no
    # depende de los prefijos declarados. Con `getpath`, que sí los usa, la
    # copia no los tiene declarados en su contexto de evaluación y lxml
    # responde «Undefined namespace prefix» en cualquier documento con
    # prefijos —o sea, en todos los Facturae firmados—.
    ruta = raiz.getroottree().getelementpath(firma)
    gemela = arbol.find(ruta)
    if gemela is None:
        return None
    gemela.getparent().remove(gemela)
    return arbol


def _contenido_referenciado(raiz, firma, referencia):
    """Los octetos sobre los que se calculó el resumen de una `Reference`.

    Devuelve `(octetos, motivo, objetivo)`: el motivo cuando no se ha podido
    —para poder decirlo en vez de dar la referencia por buena— y el elemento al
    que apunta, que es lo que permite saber **qué** cubre la firma y no solo si
    el resumen cuadra.
    """
    uri = referencia.get("URI")
    transformadas = referencia.xpath(
        "./ds:Transforms/ds:Transform/@Algorithm", namespaces=_NS
    )
    c14n = next((t for t in transformadas if t in _C14N), None)
    envolvente = "http://www.w3.org/2000/09/xmldsig#enveloped-signature" in transformadas
    desconocidas = [
        t
        for t in transformadas
        if t not in _C14N
        and t != "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
    ]
    if desconocidas:
        return (
            None,
            f"lleva una transformación que aquí no se sabe aplicar: {desconocidas[0]}",
            None,
        )

    if uri is None:
        return None, "no dice a qué se refiere", None

    if uri == "":
        arbol = _sin_esta_firma(raiz, firma)
        if arbol is None:
            return None, "no se ha podido aislar la firma para quitarla", None
        return _canonicalizar(arbol, c14n), "", raiz

    if not uri.startswith("#"):
        return None, "apunta a un fichero de fuera, que aquí no está", None

    hallados = _con_identificador(raiz, uri[1:])
    if not hallados:
        return None, f"apunta a «{uri}», que no está en el documento", None
    if len(hallados) > 1:
        return (
            None,
            f"apunta a «{uri}» y ese identificador aparece {len(hallados)} veces "
            "en el documento: no se sabe cuál es el que se firmó",
            None,
        )
    objetivo = hallados[0]

    if envolvente and _dentro_de(firma, objetivo):
        # La firma va dentro de lo que dice cubrir, así que hay que quitarla
        # antes de resumir. Con la raíz se sabe hacer —es el mismo camino que
        # `URI=""`—; con un elemento de en medio no, porque canonicalizar un
        # trozo arrastra los namespaces declarados por encima y copiarlo suelto
        # da otros bytes. Decirlo es mejor que acusar al documento de alterado,
        # que es lo que salía antes.
        if objetivo is raiz:
            arbol = _sin_esta_firma(raiz, firma)
            if arbol is None:
                return None, "no se ha podido aislar la firma para quitarla", None
            return _canonicalizar(arbol, c14n), "", raiz
        return (
            None,
            "la firma va dentro de lo que dice cubrir y aquí no se sabe "
            "quitarla de en medio",
            objetivo,
        )
    return _canonicalizar(objetivo, c14n), "", objetivo


@dataclass(frozen=True)
class Comprobada:
    """Una `Reference` de la firma, ya comprobada.

    `estado` es «bien», «alterada» —el resumen no cuadra— o «sin_comprobar»,
    que es lo que sale cuando aquí no se sabe rehacer ese resumen. Los tres son
    distintos y ninguno se puede leer como los otros dos.
    """

    uri: str | None
    alg: str | None
    estado: str
    motivo: str = ""
    objetivo: object | None = None
    declarado: str = ""
    calculado: str = ""


def comprobar_referencia(raiz, firma, referencia) -> Comprobada:
    """Rehace el resumen de una referencia y lo compara con el declarado."""
    uri = referencia.get("URI")
    metodo = referencia.xpath("./ds:DigestMethod/@Algorithm", namespaces=_NS)
    alg = _RESUMEN.get(metodo[0] if metodo else "")
    declarado = _hijo_ds(referencia, "DigestValue")
    if alg is None or declarado is None or declarado.text is None:
        return Comprobada(
            uri,
            None,
            "sin_comprobar",
            "el resumen usa un algoritmo que aquí no se conoce, o no viene",
            declarado=metodo[0] if metodo else "",
        )
    octetos, motivo, objetivo = _contenido_referenciado(raiz, firma, referencia)
    if octetos is None:
        return Comprobada(uri, alg, "sin_comprobar", motivo, objetivo)
    calculado = base64.b64encode(hashlib.new(alg, octetos).digest()).decode()
    escrito = "".join(declarado.text.split())
    if calculado != escrito:
        return Comprobada(uri, alg, "alterada", "", objetivo, escrito, calculado)
    return Comprobada(uri, alg, "bien", "", objetivo, escrito, calculado)


def _lo_que_tiene_que_cubrir(raiz, firma, padre):
    """Qué tiene que cubrir esta firma para que garantice algo. Y si es contrafirma.

    Lo normal es la factura que se lee. La excepción es la contrafirma —una
    firma que cuelga de otra y que lo que firma es el valor de aquella—: pedirle
    que cubra la factura sería inventarse un requisito que XAdES no tiene.

    Una firma que envuelve a la factura, o que va dentro de ella, no es una
    contrafirma aunque cuelgue de otra: firma la factura.
    """
    documento = factura_leida(raiz)
    if padre is None or _dentro_de(firma, documento) or _dentro_de(documento, firma):
        return documento, False
    valores = padre.xpath("./ds:SignatureValue", namespaces=_NS)
    return (valores[0] if valores else padre), True


@dataclass(frozen=True)
class Examen:
    """Todo lo que se sabe de una firma después de comprobarla.

    Existe para que **una sola** respuesta valga para los dos que preguntan: el
    informe, que escribe cada queja, y `cadena.py`, que decide si puede decir de
    quién es el certificado. Antes cada uno miraba por su cuenta y `cadena.py`
    no se enteraba de que la firma no se había comprobado: escribía igual «La
    firma de Fulano llega a tal autoridad» sobre una firma falsificada.
    """

    certificado: Certificado | None
    certificado_crudo: bytes | None
    ilegible: bool
    referencias: tuple[Comprobada, ...]
    # (estado, motivo, campo, encontrado, algoritmo, obsoleto) — ver `_valor_de_la_firma`
    valor: tuple
    cubre: bool
    apunta_a_lo_suyo: bool
    a_que_apunta: str
    propiedades: object | None
    contrafirma: bool
    padre_verificada: bool

    @property
    def verificada(self) -> bool:
        """La firma se sostiene entera: cuadra y cubre lo que tiene que cubrir.

        Las cuatro condiciones son una sola cosa dicha por partes. Que falte
        cualquiera significa que esta firma no acredita esta factura, y por
        tanto que **no se puede decir de quién es**: ni el nombre del
        certificado, ni la autoridad a la que llega, ni la nota de confianza.
        """
        return (
            self.valor[0] == "bien"
            and self.cubre
            and self.padre_verificada
            and all(una.estado != "alterada" for una in self.referencias)
        )

    @property
    def momento(self) -> datetime | None:
        """La fecha que declara lo firmado. Ver `momento_de_firma`."""
        return _fecha_de(self.propiedades)


def examinar(firma, raiz=None) -> Examen:
    """Comprueba una firma entera: certificado, referencias, valor y alcance.

    **Lo que cuesta, medido el 15-09-2026** (CPython 3.14, este ordenador):
    0,9 ms en una factura de 3 KB y 160 ms en una de 1 MB con 4.000 líneas,
    casi todo en canonicalizar el documento para rehacer el resumen. Se hace
    tres veces por firma —el informe, la cadena y los sellos preguntan cada uno
    por su cuenta— y sale a un 4 % del tiempo de validar la factura de 1 MB y a
    un 10 % de la pequeña.

    **No se guarda en caché a propósito.** Una caché aquí tendría que saber
    cuándo el documento deja de ser el mismo, y el fallo que este repositorio
    ha tenido cuatro veces con distinto disfraz es exactamente ese: algo
    guardado haciéndose pasar por lo de ahora. En el navegador, además, el
    intérprete sigue vivo entre factura y factura. Un 4 % se paga; un veredicto
    de la factura anterior, no.
    """
    if raiz is None:
        raiz = firma.getroottree().getroot()

    cert = None
    crudo = None
    ilegible = False
    textos = firma.xpath("./ds:KeyInfo//ds:X509Certificate/text()", namespaces=_NS)
    if textos:
        try:
            crudo = base64.b64decode("".join(textos[0].split()))
            cert = leer_certificado(crudo)
        except (ValueError, IndexError, binascii.Error):
            ilegible = True
            crudo = None

    referencias = tuple(
        comprobar_referencia(raiz, firma, una) for una in referencias_de(firma)
    )
    padre = next(firma.iterancestors(f"{{{NS_FIRMA}}}Signature"), None)
    objetivo, contrafirma = _lo_que_tiene_que_cubrir(raiz, firma, padre)
    cubre = any(
        una.estado == "bien" and _dentro_de(objetivo, una.objetivo)
        for una in referencias
    )
    # «Apunta» aunque no se haya podido comprobar: es la diferencia entre una
    # firma que no cubre la factura y una que sí la cubre y cuyo resumen no se
    # ha sabido rehacer. La segunda ya tiene su queja y no es esta.
    apunta = any(_dentro_de(objetivo, una.objetivo) for una in referencias)
    propiedades = next(
        (
            una.objetivo
            for una in referencias
            if una.estado == "bien" and _es_propiedades(una.objetivo)
        ),
        None,
    )
    return Examen(
        certificado=cert,
        certificado_crudo=crudo,
        ilegible=ilegible,
        referencias=referencias,
        valor=_valor_de_la_firma(firma, cert),
        cubre=cubre,
        apunta_a_lo_suyo=apunta,
        a_que_apunta=", ".join(
            una.uri if una.uri else "el documento entero" for una in referencias
        ),
        propiedades=propiedades,
        contrafirma=contrafirma,
        padre_verificada=(
            examinar(padre, raiz).verificada if contrafirma and padre is not None
            else True
        ),
    )


def examinar_todas(raiz) -> tuple[Examen, ...]:
    """Las firmas del documento, ya comprobadas, en orden de documento.

    Se hace una sola vez y el resultado va a los dos que lo necesitan: las
    reglas, que escriben cada queja, y la línea de estado del informe. Que cada
    uno llamara a `examinar` por su cuenta costaría otra pasada entera —160 ms
    en una factura de 1 MB— y, peor, permitiría que la línea dijera una cosa y
    las glosas otra.
    """
    return tuple(examinar(una, raiz) for una in hay_firma(raiz))


def estado_de_la_firma(examenes) -> str | None:
    """En qué queda la firma del documento. `None` si no trae ninguna.

    Tres estados, y la diferencia entre los dos malos importa: **rota** es que
    se ha mirado y no se sostiene —el valor no cuadra, alguien tocó un trozo
    firmado, o lo que firma no es esta factura—; **sin comprobar** es que no se
    ha sabido mirar, casi siempre porque usa un algoritmo que aquí no se conoce
    (RSA-PSS, por ejemplo, que es legítimo). Acusar a la segunda de lo que hizo
    la primera sería señalar a facturas correctas.

    Con varias firmas manda la peor: que una cuadre no arregla que otra no.
    """
    if not examenes:
        return None
    if all(uno.verificada for uno in examenes):
        return FIRMA_EN_PIE
    if any(_esta_rota(uno) for uno in examenes):
        return FIRMA_ROTA
    return FIRMA_SIN_COMPROBAR


def _esta_rota(examen: Examen) -> bool:
    """Se ha podido mirar y está mal, frente a no haberse podido mirar.

    Lo de `apunta_a_lo_suyo` y no `cubre`: una firma que apunta a la factura
    pero cuyo resumen no se ha sabido rehacer tiene `cubre` en falso sin que
    nadie haya demostrado nada contra ella. La que no apunta siquiera —la firma
    trasplantada— sí está rota, y se ve sin criptografía ninguna.
    """
    return (
        examen.valor[0] == "mal"
        or any(una.estado == "alterada" for una in examen.referencias)
        or not examen.apunta_a_lo_suyo
    )


# --- Las reglas ------------------------------------------------------------


def _regla_referencias(examen: Examen, donde: str) -> list[Incidencia]:
    """Que cada trozo firmado siga diciendo lo que decía al firmarlo.

    Esta es la comprobación que más vale de todo el módulo, y no necesita
    ninguna clave: es un resumen criptográfico contra otro. Si falla, el
    documento se ha modificado después de firmarse —a mano, o por una
    herramienta que lo volvió a guardar—.
    """
    if not examen.referencias:
        return [
            Incidencia(
                "FIRMA-VACIA",
                ERROR,
                "La firma no cubre nada: no tiene ni una referencia en su "
                "bloque `SignedInfo`. Está puesta, pero no garantiza ninguna "
                "parte del documento.",
                campo=f"{donde}Firma electrónica",
                encontrado="0 referencias",
            )
        ]

    incidencias: list[Incidencia] = []
    for numero, una in enumerate(examen.referencias, start=1):
        nombre = "el documento entero" if una.uri == "" else f"«{una.uri}»"
        if una.estado == "sin_comprobar":
            incidencias.append(
                Incidencia(
                    "FIRMA-SIN-COMPROBAR",
                    AVISO,
                    f"No se ha podido comprobar la parte firmada {nombre}: "
                    f"{una.motivo}.",
                    campo=f"{donde}Firma · referencia {numero}",
                    encontrado=(
                        una.declarado or una.uri or "(sin URI)"
                        if una.alg is None
                        else una.uri or "(sin URI)"
                    ),
                )
            )
        elif una.estado == "alterada":
            incidencias.append(
                Incidencia(
                    "FIRMA-ALTERADA",
                    ERROR,
                    f"El documento se ha modificado después de firmarlo: "
                    f"{nombre} ya no coincide con el resumen que guarda la "
                    "firma. La factura no vale como documento firmado.",
                    campo=f"{donde}Firma · referencia {numero}",
                    esperado=f"resumen {una.declarado[:24]}…",
                    encontrado=f"resumen {una.calculado[:24]}…",
                )
            )
    return incidencias


def _regla_cubre(examen: Examen, donde: str) -> list[Incidencia]:
    """Que lo que la firma cubre sea **esta factura**.

    **El agujero número dos de la auditoría del 15-09-2026**, y el más difícil
    de ver porque aquí no falla nada: la firma verifica, los resúmenes cuadran
    y el certificado es de quien dice. Lo que nadie comprobaba es *sobre qué*.

    Una firma XAdES de cualquiera sobre cualquier cosa —un acuse de recibo, un
    documento de otro trámite— se despega de su documento y se cuelga de una
    factura inventada: sigue verificando, porque lo que cubre viaja con ella, y
    el informe la daba por buena y nombraba al firmante. No hace falta ninguna
    clave privada, solo una firma suya sobre otra cosa.

    Lo mismo, dentro de un mismo fichero, es el señuelo: en una firma
    envolvente se mete un `Facturae` inventado delante del que está firmado y
    las reglas leen el primero.

    Se exige, por tanto, que alguna referencia comprobada cubra la factura que
    se está leyendo. Una contrafirma es el caso aparte: cubre el valor de la
    firma de la que cuelga, y a través de ella el documento.
    """
    if not examen.referencias or examen.apunta_a_lo_suyo:
        # Sin referencias ya se queja `FIRMA-VACIA`; y si alguna apunta a lo
        # que toca pero no se ha podido comprobar o no cuadra, eso ya lo dicen
        # `FIRMA-SIN-COMPROBAR` y `FIRMA-ALTERADA` con su motivo. Repetirlo
        # aquí sería contar dos veces el mismo problema.
        return []
    if examen.contrafirma:
        return [
            Incidencia(
                "FIRMA-NO-CUBRE",
                ERROR,
                "Esta contrafirma no cubre la firma de la que cuelga, así que "
                "no acredita nada de ella ni de la factura.",
                campo=f"{donde}Qué cubre la firma",
                esperado="una referencia al valor de la firma contrafirmada",
                encontrado=examen.a_que_apunta or "(a nada del documento)",
            )
        ]
    return [
        Incidencia(
            "FIRMA-NO-CUBRE",
            ERROR,
            "La firma no cubre la factura: lo que garantiza es otro trozo del "
            "documento. Puede ser auténtica y estar intacta —y aun así no dice "
            "nada de esta factura—: una firma de otra cosa, colgada aquí, "
            "verifica igual. Como documento firmado, esta factura no vale.",
            campo=f"{donde}Qué cubre la firma",
            esperado="una referencia que cubra la factura",
            encontrado=examen.a_que_apunta or "(a nada de la factura)",
        )
    ]


def _valor_de_la_firma(firma, cert: Certificado | None):
    """¿Cuadra el valor de la firma con el certificado? Y si no se sabe, por qué.

    Devuelve `(estado, motivo, campo, encontrado, alg, obsoleto)`, con estado
    «bien», «mal» o «sin_comprobar». Va aparte de la regla porque la respuesta
    la necesitan dos: el informe, para escribirla, y `cadena.py`, para no
    decir de quién es un certificado cuya firma nadie ha comprobado.
    """
    firmado = _signedinfo(firma)
    if firmado is None:
        return (
            "sin_comprobar",
            "la firma no trae su bloque `SignedInfo` en su sitio, así que no "
            "hay nada que comprobar",
            "Firma electrónica",
            "(sin SignedInfo)",
            None,
            False,
        )
    metodo = firmado.xpath("./ds:SignatureMethod/@Algorithm", namespaces=_NS)
    pareja = _FIRMA.get(metodo[0] if metodo else "")
    if pareja is None:
        return (
            "sin_comprobar",
            "usa un algoritmo que aquí no se conoce. Se saben verificar RSA y "
            "curva elíptica (ECDSA), con SHA-1, SHA-256, SHA-384 y SHA-512",
            "Algoritmo de firma",
            metodo[0] if metodo else "(no dice)",
            None,
            False,
        )
    alg, obsoleto = pareja
    valor = _texto_b64(_hijo_ds(firma, "SignatureValue"))
    if valor is None or cert is None:
        return ("sin_comprobar", "", "", "", alg, obsoleto)
    declarado = firmado.xpath("./ds:CanonicalizationMethod/@Algorithm", namespaces=_NS)
    octetos = _canonicalizar(firmado, declarado[0] if declarado else None)
    if octetos is None:
        return (
            "sin_comprobar",
            "canonicaliza con un método que aquí no se sabe reproducir",
            "Canonicalización",
            declarado[0] if declarado else "(no dice)",
            alg,
            obsoleto,
        )
    # `concatenada` porque en XML-DSig una firma de curva son los dos números
    # pegados y rellenos con ceros, no el DER que llevan los certificados.
    bien = verificar(valor, octetos, cert, alg, concatenada=True)
    return ("bien" if bien else "mal", "", "", "", alg, obsoleto)


def _regla_valor(examen: Examen, donde: str) -> list[Incidencia]:
    """Que la firma la hiciera la clave privada del certificado que se enseña."""
    cert = examen.certificado
    estado, motivo, campo, encontrado, alg, obsoleto = examen.valor

    incidencias: list[Incidencia] = []
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
    if cert is not None and cert.usos and not (_USOS_DE_FIRMA & cert.usos):
        # El certificado dice para qué sirve y firmar no está en la lista. No
        # invalida la aritmética —la firma puede cuadrar— pero sí dice que
        # quien lo emitió no lo emitió para esto, y eso no se puede callar:
        # aceptarlo sin más es dar por buena una firma hecha con un certificado
        # de cifrado o de autenticación. Aviso y no error por lo mismo que
        # FIRMA-DEBIL: lo que falla es para qué vale, no si cuadra.
        #
        # Solo cuando el certificado declara sus usos: keyUsage es opcional, y
        # ausente no significa «para nada», significa «sin restricción».
        # Medido en 38 certificados de facturas reales: 36 declaran keyUsage y
        # todos los que firman traen digitalSignature o contentCommitment.
        incidencias.append(
            Incidencia(
                "FIRMA-USO-NO-PERMITIDO",
                AVISO,
                "El certificado con el que se ha firmado dice, en su keyUsage, "
                "que no sirve para firmar: no lleva ni digitalSignature ni "
                "contentCommitment (no repudio). La firma puede cuadrar, pero "
                "quien emitió el certificado no lo emitió para esto.",
                campo=f"{donde}Usos del certificado",
                esperado="digitalSignature o contentCommitment",
                encontrado=", ".join(sorted(cert.usos)),
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

    if estado == "sin_comprobar":
        if motivo:
            incidencias.append(
                Incidencia(
                    "FIRMA-SIN-COMPROBAR",
                    AVISO,
                    f"No se ha podido comprobar la firma: {motivo}. Sin eso "
                    "tampoco se mira de quién es el certificado.",
                    campo=f"{donde}{campo}",
                    encontrado=encontrado,
                )
            )
        return incidencias

    if estado == "mal":
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


def _regla_certificado(examen: Examen, donde: str) -> list[Incidencia]:
    """Vigencia del certificado, y que sea el que la firma dice haber usado."""
    cert = examen.certificado
    cuando = examen.momento
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
    #
    # **Se lee de las propiedades firmadas y de ningún otro sitio.** Estaba
    # cogido con `.//SigningCertificate` en cualquier parte de la firma, así
    # que metiendo un `ds:Object` sin firmar delante del de verdad se declaraba
    # el resumen del certificado sustituido y esta comprobación —que existe
    # justo para cazar esa sustitución— daba por bueno el cambio. Es el agujero
    # número tres de la auditoría del 15-09-2026, el mismo de la fecha.
    propiedades = examen.propiedades
    if propiedades is None:
        return incidencias
    guardado = None
    for declarado in propiedades.xpath(
        ".//*[local-name()='SigningCertificate' or local-name()='SigningCertificateV2']"
    ):
        metodo = declarado.xpath(".//*[local-name()='DigestMethod']/@Algorithm")
        valor = declarado.xpath(".//*[local-name()='DigestValue']/text()")
        if metodo and valor:
            guardado = (_RESUMEN.get(metodo[0]), "".join(valor[0].split()))
        break
    if guardado is None or guardado[0] is None:
        return incidencias

    presentado = examen.certificado_crudo
    if presentado is None:
        return incidencias
    calculado = base64.b64encode(
        hashlib.new(guardado[0], presentado).digest()
    ).decode()
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


def propiedades_firmadas(firma, raiz=None):
    """Las `SignedProperties` de XAdES **que la firma cubre**, si las hay.

    Es donde XAdES guarda lo que la firma declara de sí misma: cuándo se firmó,
    con qué certificado y con qué política. Todo eso vale porque va dentro de
    un trozo que una referencia del `SignedInfo` resume; fuera de ahí lo
    escribe cualquiera.

    Y eso es justo lo que pasaba: se leían con `.//*[local-name()=…]` en
    cualquier parte de la firma, y el primero en orden de documento mandaba.
    Un `ds:Object` sin firmar metido delante del de verdad no rompe ningún
    resumen —no lo cubre nadie— y decidía la fecha con la que se miden la
    caducidad del certificado y su revocación. Con eso, un tercero que ni
    firmó ni tiene clave alguna borraba un `FIRMA-CADUCADA` del informe.

    Se resuelven solo las referencias que apuntan a unas `SignedProperties`,
    que son cuatro líneas de XML: no hace falta rehacer el resumen del
    documento entero para saber qué fecha se firmó.
    """
    if raiz is None:
        raiz = firma.getroottree().getroot()
    for referencia in referencias_de(firma):
        uri = referencia.get("URI") or ""
        if not uri.startswith("#"):
            continue
        hallados = _con_identificador(raiz, uri[1:])
        if len(hallados) != 1 or not _es_propiedades(hallados[0]):
            continue
        if comprobar_referencia(raiz, firma, referencia).estado == "bien":
            return hallados[0]
    return None


def momento_de_firma(firma) -> datetime | None:
    """La fecha que la firma declara. **No es prueba de nada por sí sola.**

    Sin sello de tiempo de un tercero, esta fecha la escribe quien firma y
    puede poner la que quiera. Sirve para comprobar la vigencia del certificado
    contra lo que el propio documento afirma, que es mejor que nada, no para
    demostrar cuándo se firmó.

    Lo que sí garantiza ahora es que la escribió **quien firma** y no quien
    tocara el fichero después: sale de las propiedades que la firma cubre. Ver
    `propiedades_firmadas`.
    """
    return _fecha_de(propiedades_firmadas(firma))


def _fecha_de(propiedades) -> datetime | None:
    """El `SigningTime` que hay dentro de unas propiedades firmadas."""
    if propiedades is None:
        return None
    for nodo in propiedades.xpath(".//*[local-name()='SigningTime']"):
        crudo = (nodo.text or "").strip()
        if not crudo:
            continue
        try:
            momento = datetime.fromisoformat(crudo.replace("Z", "+00:00"))
        except ValueError:
            continue
        return momento if momento.tzinfo else momento.replace(tzinfo=timezone.utc)
    return None


def _regla_es_xades(firma, examen: Examen, donde: str) -> list[Incidencia]:
    """Que sea XAdES de verdad: con propiedades **firmadas**.

    Unas propiedades XAdES que la firma no cubre son un adorno: dicen la fecha
    y el certificado que quiera quien las escriba, y las escribe cualquiera que
    toque el fichero. Antes bastaba que existieran en alguna parte de la firma,
    así que pegar un `ds:Object` con pinta de XAdES callaba este aviso.
    """
    if examen.propiedades is not None:
        return []
    if firma.xpath(".//*[local-name()='QualifyingProperties']"):
        return [
            Incidencia(
                "FIRMA-NO-XADES",
                AVISO,
                "La firma lleva propiedades XAdES y no las cubre: ninguna "
                "referencia firmada apunta a ellas. La fecha de firma y el "
                "certificado que declaran no los garantiza nadie, así que aquí "
                "no se usan.",
                campo=f"{donde}Tipo de firma",
                esperado="unas propiedades XAdES cubiertas por la firma",
                encontrado="propiedades sin firmar",
            )
        ]
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


def _regla_certificado_presente(examen: Examen, donde: str) -> list[Incidencia]:
    if examen.ilegible:
        return [
            Incidencia(
                "FIRMA-SIN-COMPROBAR",
                AVISO,
                "No se ha podido leer el certificado del documento, así que no "
                "se ha comprobado la firma. El resto de la factura sí se ha "
                "mirado.",
                campo=f"{donde}Certificado",
                encontrado="(ilegible)",
            )
        ]
    if examen.certificado is None:
        return [
            Incidencia(
                "FIRMA-SIN-CERTIFICADO",
                AVISO,
                "La firma no trae el certificado con el que se hizo, así que no "
                "hay con qué comprobarla. Quien reciba la factura tendría que "
                "conseguirlo por otro lado.",
                campo=f"{donde}Certificado",
                encontrado="(no viene)",
            )
        ]
    return []


def reglas(raiz, deteccion: Deteccion, examenes=None) -> list[Incidencia]:
    """Lo que se puede decir de la firma de un documento sin salir a la red.

    `examenes` lo trae quien ya los tiene hechos —`factura._reglas`, que
    también los necesita para la línea de estado— y así se comprueba una vez en
    lugar de dos. Sin él se hacen aquí, que es como lo llaman las pruebas.
    """
    if raiz is None or not deteccion:
        return []

    firmas = hay_firma(raiz)
    if not firmas:
        return _sin_firmar(deteccion)
    if examenes is None:
        examenes = examinar_todas(raiz)

    incidencias: list[Incidencia] = []
    # `strict` porque unos exámenes que no sean de estas firmas es un error de
    # quien llama, y en silencio saldrían glosas sobre la firma equivocada.
    for numero, (una, examen) in enumerate(
        zip(firmas, examenes, strict=True), start=1
    ):
        donde = f"Firma {numero} · " if len(firmas) > 1 else ""
        incidencias.extend(_regla_certificado_presente(examen, donde))
        incidencias.extend(_regla_es_xades(una, examen, donde))
        incidencias.extend(_regla_referencias(examen, donde))
        incidencias.extend(_regla_cubre(examen, donde))
        incidencias.extend(_regla_valor(examen, donde))
        incidencias.extend(_regla_certificado(examen, donde))
    return incidencias
