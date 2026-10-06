"""El sello de tiempo: quién dice cuándo se firmó, y por qué no da igual.

El problema que resuelve
------------------------
Hasta aquí, la fecha de una firma salía de `SigningTime`, una propiedad que
**escribe quien firma**. Ese dato no es un adorno: es la bisagra de la que
cuelgan las dos comprobaciones más caras del validador.

- La **vigencia** del certificado se mide contra esa fecha.
- La **revocación** también: «se anuló el 3 de marzo» solo dice algo si se sabe
  si la factura es de antes o de después.

Con la fecha en manos del firmante, las dos se esquivan a la vez y con el mismo
gesto: fechar hacia atrás. Un certificado caducado o anulado ayer firma hoy una
factura que declara ser del año pasado, y las dos reglas la dan por buena. No
es un fallo del validador —hace lo que puede con lo que tiene—: es el límite de
lo que un documento puede demostrar sobre sí mismo.

Un sello de tiempo es la salida: un tercero —una autoridad de sellado, TSA—
firma «he visto estos bytes en este instante». Como los bytes que ve son el
`SignatureValue`, y ese valor no se puede fabricar sin la clave privada, el
sello demuestra que **la firma ya existía** en esa fecha. La fecha deja de ser
una afirmación del interesado y pasa a ser el testimonio de otro.

Qué se comprueba aquí
---------------------
1. Que el sello sea un `TimeStampToken` de RFC 3161 bien formado.
2. Que lo que la autoridad firmó sea **este** sello y no otro: el atributo
   `messageDigest`, que va dentro de lo firmado, tiene que ser el resumen del
   `TSTInfo` que trae el documento.
3. Que la firma de la autoridad cuadre con su certificado.
4. Que el certificado que trae el sello sea el que la autoridad dice haber
   usado (`signingCertificate`, el equivalente de lo que XAdES hace fuera).
5. Que ese certificado **esté autorizado a sellar el tiempo**: la extensión de
   uso extendido con `id-kp-timeStamping` y nada más. Sin esto, cualquier
   certificado de firma corriente serviría para fabricar sellos.
6. Que el sello sea **de esta firma**: el resumen que lleva dentro tiene que
   ser el del `ds:SignatureValue` canonicalizado.

Y con la fecha ya acreditada, dos cosas que antes no se podían ni mirar: que el
sello no sea anterior a la emisión del certificado —imposible— y que no sea
posterior a su caducidad —posible, pero entonces no consta que la firma se
hiciera mientras el certificado valía—.

Qué no se comprueba aquí
------------------------
**De quién es esa autoridad de sellado.** Aquí se comprueba que el sello es
coherente y que lo firmó el certificado que trae dentro; que ese certificado
sea de una TSA cualificada lo responde `cadena.py`, encadenándolo hasta un
ancla de sellado instalada. Sin ese paso un sello se puede fabricar entero
—autoridad incluida— y pasa las seis comprobaciones de arriba.

Es el mismo reparto que con la firma, y por el mismo motivo: `firma.py` dice
que la firma cuadra y `cadena.py` dice de quién es. Primero que cuadre, después
de quién es.

Dos trampas que solo se ven probando
------------------------------------
Las dos salieron de contrastar el código contra un `TimeStampToken` hecho con
`openssl`, no de leer la norma:

- **La firma no va sobre los atributos tal y como vienen.** En el DER los
  atributos firmados llevan la etiqueta `[0]` (0xA0); lo que se firma es esa
  misma secuencia **reetiquetada como `SET OF`** (0x31). Verificar sobre los
  bytes tal cual da «firma incorrecta» en todos los sellos del mundo, que es un
  fallo ruidoso y por tanto benigno. El de verdad sería el contrario, y por eso
  hay una prueba que exige que la forma ingenua **no** verifique.
- **El algoritmo de resumen no sale de donde parece.** El `signatureAlgorithm`
  del firmante suele ser `rsaEncryption` a secas, sin decir con qué resumen. El
  bueno es el `digestAlgorithm`, que va aparte. Leer el primero deja el resumen
  en «desconocido» y, según cómo se escriba, en «sha1 por defecto».

Aquí tampoco hay dependencias nuevas: un `TimeStampToken` es DER, y de DER ya
sabe `firma.py` lo justo.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from validador import cifras
from validador.firma import (
    _C14N,
    momento_de_firma,
    Certificado,
    _canonicalizar,
    _elementos,
    _hijo,
    _nombre_der,
    _oid,
    _tlv,
    leer_certificado,
    verificar,
)
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia

__all__ = [
    "Sello",
    "leer",
    "comprobar",
    "cubre",
    "autorizado_a_sellar",
    "sellos_de",
    "momento_probado",
    "reglas",
    "CLASES",
]

# --- Los OID que hacen falta -----------------------------------------------

_OID_SIGNED_DATA = "2a864886f70d010702"  # 1.2.840.113549.1.7.2
_OID_TSTINFO = "2a864886f70d0109100104"  # 1.2.840.113549.1.9.16.1.4
_OID_TIPO_CONTENIDO = "2a864886f70d010903"  # 1.2.840.113549.1.9.3
_OID_RESUMEN_MENSAJE = "2a864886f70d010904"  # 1.2.840.113549.1.9.4
_OID_CERT_FIRMANTE = "2a864886f70d010910020c"  # 1.2.840.113549.1.9.16.2.12
_OID_CERT_FIRMANTE_V2 = "2a864886f70d010910022f"  # 1.2.840.113549.1.9.16.2.47

_OID_USO_EXTENDIDO = "551d25"  # 2.5.29.37
_OID_SELLAR_TIEMPO = "2b06010505070308"  # 1.3.6.1.5.5.7.3.8, id-kp-timeStamping
_OID_IDENTIFICADOR_CLAVE = "551d0e"  # 2.5.29.14, subjectKeyIdentifier

# Los resúmenes por su OID. Sin MD5: un sello con MD5 no es un sello, y
# reconocerlo solo serviría para poder darlo por bueno.
_RESUMENES = {
    "2b0e03021a": "sha1",
    "608648016503040201": "sha256",
    "608648016503040202": "sha384",
    "608648016503040203": "sha512",
}

# Se reconoce para poder decir qué es, no para aceptarlo: ver `reglas`.
RESUMENES_ROTOS = frozenset({"sha1"})

# Las clases de sello que XAdES define, y cómo se llaman en castellano. Solo el
# primero se comprueba contra su entrada; de los demás se dice que están y que
# no se miran, porque callar daría a entender que el documento no traía nada.
CLASES = {
    "SignatureTimeStamp": "sobre la firma",
    "SigAndRefsTimeStamp": "sobre la firma y las referencias de validación",
    "RefsOnlyTimeStamp": "sobre las referencias de validación",
    "ArchiveTimeStamp": "de archivo",
    "AllDataObjectsTimeStamp": "sobre todo lo firmado",
    "IndividualDataObjectsTimeStamp": "sobre un objeto firmado",
}
SOBRE_LA_FIRMA = "SignatureTimeStamp"


# --- DER, con los trozos originales a mano ---------------------------------


def _partes(contenido: bytes) -> list[tuple[int, bytes, bytes]]:
    """Como `_elementos`, pero devolviendo también los bytes tal cual venían.

    Hacen falta sin tocar para los atributos firmados: lo que se verifica es la
    secuencia original con **un byte cambiado**, no una reconstrucción. Volver
    a serializarla daría los mismos bytes en cualquier sello bien hecho, y unos
    distintos —o sea, un «no verifica» falso— en cuanto uno de verdad codifique
    una longitud de forma que no sea la mínima.
    """
    salida = []
    pos = 0
    while pos < len(contenido):
        inicio = pos
        etiqueta, valor, pos = _tlv(contenido, pos)
        salida.append((etiqueta, valor, contenido[inicio:pos]))
    return salida


def _entero(crudo: bytes) -> int:
    return int.from_bytes(crudo, "big") if crudo else 0


def _momento(crudo: bytes) -> datetime | None:
    """Un `GeneralizedTime` de RFC 3161: AAAAMMDDHHMMSS[.fff]Z.

    La fracción de segundo es opcional y la norma la permite con los decimales
    que quiera. Se lee entera: no hace falta para nada, pero truncarla sería
    cambiar el dato que la autoridad firmó.
    """
    texto = crudo.decode("ascii", "replace").strip()
    # La norma pide la Z. Si falta, se toma como UTC igual: es lo que la propia
    # norma dice que significa, y negarse dejaría sin leer un sello entero por
    # un byte que no cambia lo que ese sello afirma.
    if texto.endswith("Z"):
        texto = texto[:-1]
    entero, _, fraccion = texto.partition(".")
    try:
        cuando = datetime.strptime(entero, "%Y%m%d%H%M%S")
    except ValueError:
        return None
    cuando = cuando.replace(tzinfo=timezone.utc)
    if fraccion.isdigit():
        cuando += timedelta(seconds=float("0." + fraccion))
    return cuando


def _precision(contenido: bytes) -> str:
    """`Accuracy` en algo que se pueda leer: «±1 s 500 ms»."""
    trozos = []
    for etiqueta, valor in _elementos(contenido):
        cuanto = _entero(valor)
        if etiqueta == 0x02:
            trozos.append(f"{cuanto} s")
        elif etiqueta == 0x80:
            trozos.append(f"{cuanto} ms")
        elif etiqueta == 0x81:
            trozos.append(f"{cuanto} µs")
    return "±" + " ".join(trozos) if trozos else ""


def _algoritmo(contenido: bytes) -> str:
    """El resumen de un `AlgorithmIdentifier`, por su nombre o «»."""
    partes = _elementos(contenido)
    if not partes or partes[0][0] != 0x06:
        return ""
    return _RESUMENES.get(_oid(partes[0][1]), "")


# --- El sello --------------------------------------------------------------


@dataclass(frozen=True)
class Sello:
    """Un `TimeStampToken` de RFC 3161, leído. Leído no es comprobado."""

    momento: datetime | None
    politica: str
    serie: int
    # De qué es el resumen que el sello lleva dentro: con qué algoritmo y cuál.
    resumen_de: str
    resumen: bytes
    precision: str
    nombre: str  # el que la autoridad se da a sí misma, si se lo da

    certificados: tuple[Certificado, ...] = ()
    firmante: Certificado | None = None
    # Con qué resumen firmó la autoridad, del `digestAlgorithm` y no del OID de
    # firma: ver la cabecera del módulo.
    resumen_firma: str = ""

    # Lo crudo, para poder comprobar la firma sin volver a abrir el DER.
    contenido: bytes = b""  # el TSTInfo en DER, que es lo que se resume
    atributos: tuple[tuple[str, bytes], ...] = ()
    atributos_der: bytes = b""  # tal cual venían, con su etiqueta [0]
    valor_firma: bytes = b""

    def atributo(self, oid: str) -> bytes | None:
        for cual, valor in self.atributos:
            if cual == oid:
                return valor
        return None

    @property
    def quien(self) -> str:
        """Cómo llamar a la autoridad en un mensaje, con lo que se tenga."""
        if self.firmante is not None and self.firmante.sujeto:
            return self.firmante.sujeto
        return self.nombre or "una autoridad que no se identifica"


def _nombre_de_tsa(contenido: bytes) -> str:
    """El campo `tsa` del sello, que es un `GeneralName`.

    Casi siempre es un nombre X.500, y entonces vale el nombre común. No se
    reconstruye el nombre entero: para el mensaje basta con algo que una
    persona reconozca, y **el dato de verdad —de quién es— sale del
    certificado**, no de aquí. Este campo lo escribe la propia autoridad sobre
    sí misma y no lo respalda nada.
    """
    try:
        partes = _elementos(contenido)
    except ValueError:
        return ""
    for etiqueta, valor in partes:
        if etiqueta == 0xA4:  # [4] directoryName
            try:
                _, dentro, _ = _tlv(valor)
            except ValueError:
                return ""
            return _nombre_der(dentro) or ""
        if etiqueta in (0x81, 0x82, 0x86):  # correo, DNS o URI
            return valor.decode("utf-8", "replace")
    return ""


def _certificados_del_sello(contenido: bytes) -> tuple[Certificado, ...]:
    """Los X.509 que el sello lleva dentro.

    El `CertificateSet` admite además certificados de atributos y otras cosas
    con etiquetas de contexto. Aquí solo se cogen los `SEQUENCE`, que son los
    X.509: lo demás no sirve para verificar una firma y colarlo por el mismo
    sitio solo daría errores de lectura donde no hay ningún problema.
    """
    salida = []
    for etiqueta, _, crudo in _partes(contenido):
        if etiqueta != 0x30:
            continue
        try:
            salida.append(leer_certificado(crudo))
        except (ValueError, IndexError):
            continue
    return tuple(salida)


def _elegir_firmante(sid: tuple[int, bytes], certificados) -> Certificado | None:
    """Cuál de los certificados del sello es el que firmó.

    Dos formas de decirlo, y las dos se usan en el mundo real: por (emisor,
    número de serie) o por el identificador de la clave. Se comparan en DER,
    igual que en `cadena.py` y por el mismo motivo: dos autoridades distintas
    pueden coincidir en el nombre común.
    """
    etiqueta, valor = sid
    if etiqueta == 0x30:  # IssuerAndSerialNumber
        trozos = _partes(valor)
        if len(trozos) != 2:
            return None
        emisor = trozos[0][2]
        serie = _entero(trozos[1][1])
        for cert in certificados:
            if cert.emisor_der == emisor and cert.serie == serie:
                return cert
        return None
    if etiqueta == 0x80:  # [0] subjectKeyIdentifier
        for cert in certificados:
            crudo = cert.extension(_OID_IDENTIFICADOR_CLAVE)
            if crudo is None:
                continue
            try:
                _, dentro, _ = _tlv(crudo)
            except ValueError:
                continue
            if dentro == valor:
                return cert
    return None


def leer(der: bytes) -> Sello:
    """Abre un `TimeStampToken`. No lo cree: solo lo lee.

    Levanta `ValueError` con el motivo escrito para que se pueda contar. Un
    sello ilegible y un sello falso no son la misma noticia.
    """
    etiqueta, contenido, _ = _tlv(der)
    if etiqueta != 0x30:
        raise ValueError("no empieza por una secuencia DER")
    trozos = _partes(contenido)
    if len(trozos) < 2 or trozos[0][0] != 0x06:
        raise ValueError("no tiene la forma de un ContentInfo")
    if _oid(trozos[0][1]) != _OID_SIGNED_DATA:
        raise ValueError("no es un contenido firmado (CMS SignedData)")

    _, firmado, _ = _tlv(trozos[1][1])
    campos = _partes(firmado)
    if len(campos) < 4:
        raise ValueError("al SignedData le faltan campos")

    tipo_y_contenido = _partes(campos[2][1])
    if not tipo_y_contenido or tipo_y_contenido[0][0] != 0x06:
        raise ValueError("no dice qué clase de contenido firma")
    if _oid(tipo_y_contenido[0][1]) != _OID_TSTINFO:
        raise ValueError("lo que firma no es un sello de tiempo")
    if len(tipo_y_contenido) < 2:
        raise ValueError("es un sello sin sello dentro: no trae el TSTInfo")
    # eContent es `[0] EXPLICIT OCTET STRING`: se abre el [0] y luego la
    # cadena de octetos, cuyo contenido es el TSTInfo en DER.
    _, cadena, _ = _tlv(tipo_y_contenido[1][1])

    certificados: tuple[Certificado, ...] = ()
    firmantes: list[bytes] = []
    for etiqueta, valor, _ in campos[3:]:
        if etiqueta == 0xA0:
            certificados = _certificados_del_sello(valor)
        elif etiqueta == 0x31:
            firmantes = [crudo for _, _, crudo in _partes(valor)]
    if len(firmantes) != 1:
        # RFC 3161 pide exactamente uno. Con varios no hay forma de decir cuál
        # es «el» sello, y elegir uno sería inventarse la respuesta.
        raise ValueError(
            f"un sello lo firma una autoridad y este trae {len(firmantes)}"
        )

    datos = _leer_tstinfo(cadena)
    _, dentro_firmante, _ = _tlv(firmantes[0])
    firmante = _leer_signerinfo(dentro_firmante, certificados)
    return Sello(contenido=cadena, certificados=certificados, **datos, **firmante)


def _leer_tstinfo(der: bytes) -> dict:
    """El TSTInfo: qué se selló, cuándo y con qué política."""
    etiqueta, contenido, _ = _tlv(der)
    if etiqueta != 0x30:
        raise ValueError("el TSTInfo no es una secuencia")
    campos = _partes(contenido)
    if len(campos) < 5:
        raise ValueError("al TSTInfo le faltan campos")
    if _entero(campos[0][1]) != 1:
        raise ValueError(
            f"es un sello de una versión que aquí no se conoce "
            f"(la {_entero(campos[0][1])})"
        )

    impronta = _elementos(campos[2][1])
    if len(impronta) < 2:
        raise ValueError("el sello no dice de qué es el resumen que lleva")
    resumen_de = _algoritmo(impronta[0][1])
    if not resumen_de:
        raise ValueError("el resumen del sello es de un algoritmo desconocido")

    cuando = _momento(campos[4][1]) if campos[4][0] == 0x18 else None
    if cuando is None:
        raise ValueError("la fecha del sello no se lee")

    precision, nombre = "", ""
    for etiqueta, valor, _ in campos[5:]:
        if etiqueta == 0x30:
            precision = _precision(valor)
        elif etiqueta == 0xA0:
            nombre = _nombre_de_tsa(valor)
    return {
        "momento": cuando,
        "politica": _oid(campos[1][1]) if campos[1][0] == 0x06 else "",
        "serie": _entero(campos[3][1]),
        "resumen_de": resumen_de,
        "resumen": impronta[1][1],
        "precision": precision,
        "nombre": nombre,
    }


def _leer_signerinfo(contenido: bytes, certificados) -> dict:
    """Quién firmó el sello, con qué y sobre qué atributos.

    Los tres primeros campos son fijos —versión, quién es, con qué resumen— y
    después vienen los atributos firmados, que son opcionales en CMS pero no en
    un sello: sin ellos no hay `messageDigest` que atar el sello a lo que dice
    sellar.
    """
    campos = _partes(contenido)
    if len(campos) < 5:
        raise ValueError("al firmante del sello le faltan campos")
    resumen_firma = _algoritmo(campos[2][1])
    firmante = _elegir_firmante((campos[1][0], campos[1][1]), certificados)

    atributos: list[tuple[str, bytes]] = []
    atributos_der = b""
    valor_firma = b""
    for etiqueta, valor, crudo in campos[3:]:
        if etiqueta == 0xA0:
            atributos_der = crudo
            for _, uno in _elementos(valor):
                partes = _elementos(uno)
                if len(partes) == 2 and partes[0][0] == 0x06:
                    dentro = _elementos(partes[1][1])
                    if dentro:
                        atributos.append((_oid(partes[0][1]), dentro[0][1]))
        elif etiqueta == 0x04:
            valor_firma = valor
    return {
        "firmante": firmante,
        "resumen_firma": resumen_firma,
        "atributos": tuple(atributos),
        "atributos_der": atributos_der,
        "valor_firma": valor_firma,
    }


# --- Creérselo o no --------------------------------------------------------


def autorizado_a_sellar(cert: Certificado) -> str:
    """¿Puede este certificado sellar el tiempo? El motivo si no, o «».

    RFC 3161 §2.3 lo pide con una rotundidad rara en una norma: la extensión de
    uso extendido tiene que estar, tiene que llevar `id-kp-timeStamping` y **no
    puede llevar nada más**. La razón es que el sello es el único documento que
    nadie puede fechar; si valiera cualquier certificado de firma, quien tuviera
    uno podría fabricarse la fecha que quisiera, que es justo lo que el sello
    viene a impedir.

    Que la norma sea tan estricta no la hace realista por sí sola, así que se
    contrastó contra la lista española: de sus 69 certificados de sellado
    concedidos, 60 son certificados de firma —los que sellan— y **los 60**
    llevan la extensión con ese uso y solo ese. Los otros nueve son autoridades
    de certificación, que no sellan nada; aquí no llegan, porque lo que se
    comprueba es el certificado que firma el sello.
    """
    crudo = cert.extension(_OID_USO_EXTENDIDO)
    if crudo is None:
        return (
            "su certificado no dice estar autorizado a sellar el tiempo: le "
            "falta la extensión de uso extendido"
        )
    try:
        _, dentro, _ = _tlv(crudo)
        usos = [_oid(valor) for etiqueta, valor in _elementos(dentro)
                if etiqueta == 0x06]
    except ValueError:
        return "su certificado dice para qué vale de una forma que no se lee"
    if _OID_SELLAR_TIEMPO not in usos:
        return (
            "su certificado está autorizado para otras cosas, pero no para "
            "sellar el tiempo"
        )
    if len(usos) > 1:
        return (
            "su certificado mezcla el sellado de tiempo con otros usos, y la "
            "norma pide que sea el único"
        )
    return ""


def comprobar(sello: Sello) -> str:
    """¿Se sostiene este sello por dentro? El motivo si no, o «».

    Aquí no se mira **a qué** se refiere el sello —eso es `cubre`— ni de quién
    es la autoridad. Se mira que el sello sea lo que dice ser y que lo firmara
    quien dice haberlo firmado.
    """
    if sello.firmante is None:
        return (
            "no trae el certificado de la autoridad que lo emitió, así que no "
            "hay con qué comprobarlo"
        )
    if not sello.atributos_der:
        return "no trae atributos firmados, así que no ata el sello a nada"

    tipo = sello.atributo(_OID_TIPO_CONTENIDO)
    if tipo is None or _oid(tipo) != _OID_TSTINFO:
        return "la autoridad firmó declarando que no era un sello de tiempo"

    guardado = sello.atributo(_OID_RESUMEN_MENSAJE)
    if guardado is None:
        return "lo que la autoridad firmó no incluye el resumen del sello"
    if not sello.resumen_firma:
        return "está firmado con un algoritmo de resumen que aquí no se conoce"
    calculado = hashlib.new(sello.resumen_firma, sello.contenido).digest()
    if guardado != calculado:
        return (
            "lo que la autoridad firmó no es el sello que trae el documento: "
            "alguien ha cambiado uno por otro"
        )

    motivo = _cuadra_el_certificado(sello)
    if motivo:
        return motivo

    # La trampa: se firma la secuencia de atributos reetiquetada como SET OF.
    # Se cambia **el byte de la etiqueta y nada más**, para no depender de que
    # nuestra reserialización coincida con la de quien lo emitió.
    mensaje = b"\x31" + sello.atributos_der[1:]
    if not verificar(sello.valor_firma, mensaje, sello.firmante,
                     sello.resumen_firma):
        return "la firma de la autoridad de sellado no cuadra con su certificado"

    fallo = autorizado_a_sellar(sello.firmante)
    if fallo:
        return fallo
    return ""


def _cuadra_el_certificado(sello: Sello) -> str:
    """El `signingCertificate` de CMS: lo mismo que XAdES hace por fuera.

    El atributo va **dentro de lo firmado** y guarda el resumen del certificado
    que la autoridad usó. Sin esta comprobación, cambiar el certificado del
    sello por otro no rompería nada visible hasta la verificación de la firma,
    y con un certificado elegido a propósito podría no romper nada en absoluto.
    """
    # El algoritmo por defecto **no es el mismo en las dos versiones**: en la
    # 1 el resumen es SHA-1 siempre y no se escribe; en la 2 se escribe solo
    # cuando no es SHA-256. Tomar SHA-1 en la 2 —que es lo que sale de
    # escribir un único valor por defecto— haría fallar la comprobación en
    # todos los sellos modernos, que es justo donde importa.
    for oid, defecto in ((_OID_CERT_FIRMANTE, "sha1"),
                         (_OID_CERT_FIRMANTE_V2, "sha256")):
        crudo = sello.atributo(oid)
        if crudo is None:
            continue
        esperado, algoritmo = _resumen_declarado(crudo, defecto)
        if esperado is None or not algoritmo:
            continue
        if hashlib.new(algoritmo, sello.firmante.der).digest() != esperado:
            return (
                "el certificado que trae el sello no es el que la autoridad "
                "dice haber usado"
            )
    return ""


def _resumen_declarado(crudo: bytes, por_defecto: str):
    """El resumen del primer `ESSCertID` de un `SigningCertificate[V2]`.

    En la versión 1 el algoritmo no se escribe nunca: es SHA-1. En la 2 va
    delante y es opcional, y cuando falta significa SHA-256.
    """
    try:
        certificados = _elementos(crudo)
        if not certificados:
            return None, ""
        primero = _elementos(certificados[0][1])
        if not primero:
            return None, ""
        campos = _elementos(primero[0][1])
    except ValueError:
        return None, ""
    if not campos:
        return None, ""
    if campos[0][0] == 0x30:  # AlgorithmIdentifier delante: es la versión 2
        algoritmo = _algoritmo(campos[0][1])
        resto = campos[1:]
    else:
        algoritmo = por_defecto
        resto = campos
    if not resto or resto[0][0] != 0x04:
        return None, ""
    return resto[0][1], algoritmo


def cubre(sello: Sello, datos: bytes) -> str:
    """¿Es este sello de estos bytes? El motivo si no, o «».

    Separado de `comprobar` a propósito: «el sello está mal» y «el sello está
    bien pero es de otra cosa» son dos diagnósticos distintos y llevan a dos
    acciones distintas. El segundo es el que aparece cuando alguien copia un
    sello bueno de un documento a otro.
    """
    if not sello.resumen_de:
        return "no dice con qué algoritmo se hizo el resumen que lleva"
    if hashlib.new(sello.resumen_de, datos).digest() != sello.resumen:
        return "el resumen que lleva dentro no es el de esta firma"
    return ""


# --- El lado XAdES ---------------------------------------------------------


@dataclass(frozen=True)
class Hallado:
    """Un sello encontrado en una firma, con lo que se sabe de él."""

    clase: str
    sello: Sello | None = None
    motivo: str = ""  # por qué no se ha podido leer, si no hay sello
    c14n: str | None = None  # el algoritmo que el sello declara para su entrada
    # El sello viene en una forma que existe y que no sabemos leer, en vez de
    # venir roto. Son dos noticias distintas: una se arregla volviendo a
    # sellar, la otra no se arregla, se implementa.
    otro_formato: bool = False

    @property
    def sobre_la_firma(self) -> bool:
        return self.clase == SOBRE_LA_FIRMA


def sellos_de(firma) -> list[Hallado]:
    """Los sellos de tiempo que lleva una firma XAdES.

    Se recogen **todas** las clases, no solo la que se sabe comprobar. Un
    documento con un sello de archivo que aquí no se mira no es un documento sin
    sellos, y el informe tiene que poder decir la diferencia.
    """
    salida: list[Hallado] = []
    if firma is None:
        return salida
    for clase in CLASES:
        for nodo in firma.xpath(f".//*[local-name()='{clase}']"):
            metodo = _hijo(nodo, "CanonicalizationMethod")
            c14n = metodo.get("Algorithm") if metodo is not None else None
            # XAdES admite el sello en dos formas: el token de RFC 3161 en
            # base64 —`EncapsulatedTimeStamp`, que es la que se usa— y el
            # mismo sello escrito como XML. Aquí solo se lee la primera; la
            # segunda **se dice**, porque callarla hacía que un documento
            # sellado saliera como si no lo estuviera.
            if not nodo.xpath(".//*[local-name()='EncapsulatedTimeStamp']"):
                if nodo.xpath(".//*[local-name()='XMLTimeStamp']"):
                    salida.append(Hallado(
                        clase, c14n=c14n, otro_formato=True,
                        motivo="viene escrito como XML y no como un token de "
                               "RFC 3161, que es la forma que aquí se sabe leer"))
                continue
            for texto in nodo.xpath(
                ".//*[local-name()='EncapsulatedTimeStamp']/text()"
            ):
                try:
                    der = base64.b64decode("".join(texto.split()))
                except (binascii.Error, ValueError):
                    salida.append(Hallado(clase, motivo="no está bien codificado"))
                    continue
                try:
                    salida.append(Hallado(clase, sello=leer(der), c14n=c14n))
                except (ValueError, IndexError) as error:
                    salida.append(Hallado(clase, motivo=str(error), c14n=c14n))
    return salida


def entrada_del_sello(firma, c14n: str | None) -> tuple[bytes | None, str]:
    """Los octetos que un `SignatureTimeStamp` tiene que estar sellando.

    XAdES lo define en una línea: el `ds:SignatureValue` **entero**, con sus
    etiquetas, canonicalizado. Que sea el valor de la firma y no el documento
    es lo que hace que el sello demuestre algo: ese valor no se puede fabricar
    sin la clave privada, así que sellarlo es sellar la firma.

    Cuando el sello no dice cómo canonicalizar se usa la del `SignedInfo`, que
    es lo que manda la norma.

    Devuelve también el motivo cuando no se ha podido, para poder decirlo en
    vez de dar el sello por bueno.
    """
    valor = _hijo(firma, "SignatureValue")
    if valor is None:
        return None, "la firma no trae el valor que el sello tendría que cubrir"
    if c14n is None:
        info = _hijo(firma, "SignedInfo")
        metodo = _hijo(info, "CanonicalizationMethod") if info is not None else None
        c14n = metodo.get("Algorithm") if metodo is not None else None
    # Se mira contra la tabla de `firma.py` para no aceptar un algoritmo que
    # luego `_canonicalizar` resolvería por su cuenta: eso daría unos bytes que
    # no son los que el sello dice cubrir, y con ellos un veredicto inventado
    # —«este sello no es de esta firma» sobre un sello que sí lo es—.
    if c14n is not None and c14n not in _C14N:
        return None, f"el sello se canonicaliza de una forma que aquí no se sabe aplicar: {c14n}"
    return _canonicalizar(valor, c14n), ""


def momento_probado(firma) -> tuple[datetime, Sello] | None:
    """La fecha que un tercero acredita para esta firma, si hay alguna.

    Solo cuenta un `SignatureTimeStamp` que se sostenga por dentro y que además
    cubra el `SignatureValue` de esta firma. Lo demás es la palabra de quien
    firma, que ya se tenía.

    Con varios sellos buenos se coge **el más antiguo**. Lo que un sello prueba
    es que la firma ya existía en esa fecha, así que el más antiguo es la cota
    más ajustada, y la única que se sostiene: los demás también son ciertos,
    pero dicen menos.
    """
    candidatos = []
    for hallado in sellos_de(firma):
        if not hallado.sobre_la_firma or hallado.sello is None:
            continue
        if comprobar(hallado.sello):
            continue
        datos, _ = entrada_del_sello(firma, hallado.c14n)
        if datos is None or cubre(hallado.sello, datos):
            continue
        if hallado.sello.momento is not None:
            candidatos.append((hallado.sello.momento, hallado.sello))
    if not candidatos:
        return None
    return min(candidatos, key=lambda par: par[0])


# --- Las reglas ------------------------------------------------------------

# Cuánto se le perdona al reloj de quien firma. La fecha declarada tiene que ser
# anterior o igual a la del sello —no se puede firmar algo después de que un
# tercero lo haya visto—, pero el reloj de un ordenador cualquiera se va unos
# minutos sin que eso signifique nada. Cinco minutos dejan pasar el desajuste
# corriente y siguen cazando el que importa, que se cuenta en días.
TOLERANCIA = timedelta(minutes=5)


def _cuando(momento: datetime) -> str:
    return cifras.momento(momento)


def _sin_sello(firma, donde: str, llevaba: bool = False) -> list[Incidencia]:
    """Que la fecha la ponga el firmante es una decisión, no un silencio.

    `llevaba` distingue los dos casos, que acaban en la misma fecha y no en la
    misma noticia: un documento sin sello necesita que alguien lo selle; uno
    con un sello que no sirve ya lo tiene puesto, y decirle que no lo lleva
    manda a pedir dos veces lo mismo. El fallo salió con un fichero real que
    traía el sello escrito en XML.
    """
    declarada = momento_de_firma(firma)
    if declarada is not None:
        cual = f"la que declara quien firma, el {cifras.fecha(declarada)}"
    else:
        cual = "ninguna, porque el documento tampoco dice cuándo se firmó"
    aviso = (
        "quien firma puede escribir la que quiera, y fechando hacia atrás se "
        "esquivan la caducidad y la revocación a la vez."
    )
    if llevaba:
        return [
            Incidencia(
                "SELLO-SIN-USAR",
                NOTA,
                "La firma lleva sello de tiempo, pero ninguno se ha podido "
                "usar (arriba está el motivo de cada uno). Así que la fecha "
                "que se ha usado para comprobar la vigencia del certificado y "
                f"la revocación es {cual}: {aviso}",
                campo=f"{donde}Sello de tiempo",
                esperado="un sello de tiempo que se sostenga y sea de esta firma",
                encontrado="lleva sello, pero no sirve",
            )
        ]
    return [
        Incidencia(
            "SELLO-FALTA",
            NOTA,
            "La firma no lleva sello de tiempo de un tercero. La fecha que se "
            "ha usado para comprobar la vigencia del certificado y la "
            f"revocación es {cual}: {aviso}",
            campo=f"{donde}Sello de tiempo",
            esperado="un sello de tiempo de una autoridad de sellado",
            encontrado="(no lleva)",
        )
    ]


def _otra_clase(hallado: Hallado, donde: str) -> Incidencia:
    """Un sello que está pero que no se comprueba. Decirlo, no callarlo."""
    fecha = ""
    if hallado.sello is not None and hallado.sello.momento is not None:
        fecha = f" Dice ser del {cifras.fecha(hallado.sello.momento)}."
    return Incidencia(
        "SELLO-NO-COMPROBADO",
        NOTA,
        f"La firma lleva un sello de tiempo {CLASES[hallado.clase]}, que este "
        "validador todavía no sabe comprobar: no se ha mirado ni de qué es ni "
        f"si cuadra.{fecha} No cuenta como fecha acreditada.",
        campo=f"{donde}Sello de tiempo",
        encontrado=hallado.clase,
    )


def _correcto(sello: Sello, donde: str) -> Incidencia:
    """Lo que se ha dado por bueno, con qué, y qué falta por mirar."""
    precision = f", con una precisión de {sello.precision}" if sello.precision else ""
    return Incidencia(
        "SELLO-TIEMPO",
        NOTA,
        f"La firma lleva un sello de tiempo de «{sello.quien}» del "
        f"{_cuando(sello.momento)}{precision}, y el sello cuadra: esa "
        "autoridad vio esta firma ese día, así que la firma ya existía "
        "entonces. Esa es la fecha que se usa para la vigencia y la "
        "revocación, en vez de la que declara quien firma.",
        campo=f"{donde}Sello de tiempo",
        encontrado=f"sello de «{sello.quien}», serie {sello.serie}",
    )


def _contra_el_certificado(sello: Sello, cert, donde: str) -> list[Incidencia]:
    """El sello contra la vigencia del certificado que firma.

    Solo se mira **el principio de la vigencia**, y la asimetría es a propósito
    —la misma que con las anclas retiradas, y por el mismo motivo—: lo que un
    sello demuestra es que la firma ya existía en esa fecha, o sea una cota por
    arriba y no una fecha exacta.

    Que el sello sea posterior a la caducidad del certificado no prueba nada
    malo: se firma un martes y se sella el jueves, y nada impide sellar meses
    después. Que sea **anterior al día en que se emitió el certificado**, en
    cambio, es imposible: la firma existía antes que la clave con la que dice
    estar hecha, y eso no se explica con un reloj mal puesto.
    """
    if cert is None or sello.momento is None or not cert.desde:
        return []
    if sello.momento >= cert.desde - TOLERANCIA:
        return []
    quien = f" ({cert.sujeto})" if cert.sujeto else ""
    return [
        Incidencia(
            "SELLO-ANTES-DEL-CERTIFICADO",
            ERROR,
            "El sello de tiempo acredita que esta firma ya existía el "
            f"{cifras.fecha(sello.momento)}, antes de que se emitiera el "
            f"certificado{quien} con el que dice estar hecha. Una de las dos "
            "cosas es falsa.",
            campo=f"{donde}Sello de tiempo",
            esperado=f"un sello posterior al {cifras.fecha(cert.desde)}",
            encontrado=f"sellada el {cifras.fecha(sello.momento)}",
        )
    ]


def _despues_de_caducar(sello: Sello, cert, donde: str) -> list[Incidencia]:
    """Lo único que consta de esta firma es posterior a la caducidad.

    No es lo mismo que `_contra_el_certificado`, y por eso va aparte: aquello
    es una imposibilidad y esto es una **ausencia de prueba**. La firma pudo
    hacerse antes, mientras el certificado valía; lo que pasa es que nada lo
    demuestra, y el único dato que lo diría —la fecha declarada— es el que
    escribe quien firma.

    Es AVISO y no ERROR a propósito. Sellar tarde es legítimo y pasa, así que
    afirmar que la factura no vale sería rechazar facturas buenas. Pero callar
    sería peor: es justo la maniobra para la que sirve un sello —firmar con un
    certificado caducado y fechar hacia atrás—, y sin esta regla la fecha
    declarada la esquiva sin que nadie diga nada.
    """
    if cert is None or sello.momento is None or not cert.hasta:
        return []
    if sello.momento <= cert.hasta:
        return []
    quien = f" ({cert.sujeto})" if cert.sujeto else ""
    return [
        Incidencia(
            "SELLO-DESPUES-DE-CADUCAR",
            AVISO,
            f"El certificado{quien} caducó el "
            f"{cifras.fecha(cert.hasta)}, y lo único que hay acreditado "
            f"de esta firma es que ya existía el "
            f"{cifras.fecha(sello.momento)}, después. Pudo firmarse "
            "antes, cuando el certificado aún valía, pero eso solo lo dice la "
            "fecha que escribe quien firma. Sellar tarde es legítimo; fechar "
            "hacia atrás para tapar una caducidad, también se ve así.",
            campo=f"{donde}Sello de tiempo",
            esperado=f"un sello anterior al {cifras.fecha(cert.hasta)}",
            encontrado=f"sellada el {cifras.fecha(sello.momento)}",
        )
    ]


def _contradice(sello: Sello, firma, donde: str) -> list[Incidencia]:
    """La fecha declarada contra la acreditada, cuando no puede ser."""
    declarada = momento_de_firma(firma)
    if declarada is None or sello.momento is None:
        return []
    if declarada <= sello.momento + TOLERANCIA:
        return []
    return [
        Incidencia(
            "SELLO-CONTRADICE",
            AVISO,
            f"El documento dice haberse firmado el {_cuando(declarada)}, "
            f"después del {_cuando(sello.momento)} en que la autoridad de "
            "sellado ya había visto esta firma. No se puede firmar algo "
            "después de que otro lo haya visto: la fecha que declara el "
            "documento no es cierta. Se usa la del sello, que es la que está "
            "acreditada.",
            campo=f"{donde}Sello de tiempo",
            esperado=f"una fecha anterior al {cifras.fecha(sello.momento)}",
            encontrado=f"declara el {cifras.fecha(declarada)}",
        )
    ]


def _algoritmos(sello: Sello, donde: str) -> list[Incidencia]:
    viejos = sorted({sello.resumen_de, sello.resumen_firma} & RESUMENES_ROTOS)
    if not viejos:
        return []
    return [
        Incidencia(
            "SELLO-ALGORITMO-VIEJO",
            AVISO,
            f"El sello de tiempo usa {', '.join(viejos)}, que está roto: se "
            "saben fabricar dos documentos con el mismo resumen. Un sello así "
            "acredita menos de lo que parece, porque lo que la autoridad vio "
            "pudo ser otra cosa con ese mismo resumen.",
            campo=f"{donde}Sello de tiempo",
            esperado="sha256 o mejor",
            encontrado=", ".join(viejos),
        )
    ]


def reglas(firma, cert: Certificado | None = None, donde: str = "") -> list[Incidencia]:
    """Lo que se puede decir de los sellos de tiempo de una firma.

    `cert` es el certificado con el que se firmó la factura, que hace falta
    para cruzar el sello con su vigencia. Sin él las demás reglas siguen
    valiendo, así que es opcional en vez de obligatorio.
    """
    if firma is None:
        return []
    # Sin propiedades XAdES no hay dónde meter un sello, y `firma.py` ya se
    # queja de eso. Repetirlo aquí con otras palabras sería ruido.
    if not firma.xpath(".//*[local-name()='QualifyingProperties']"):
        return []

    hallados = sellos_de(firma)
    if not hallados:
        return _sin_sello(firma, donde)

    incidencias: list[Incidencia] = []
    alguno_bueno = False
    for hallado in hallados:
        if hallado.otro_formato:
            incidencias.append(
                Incidencia(
                    "SELLO-OTRO-FORMATO",
                    AVISO,
                    f"La firma lleva un sello de tiempo {CLASES[hallado.clase]} "
                    f"que {hallado.motivo}. El documento está sellado y el "
                    "sello puede ser perfectamente bueno; lo que pasa es que "
                    "este validador no sabe leer esa forma, así que su fecha "
                    "no se ha usado.",
                    campo=f"{donde}Sello de tiempo",
                    esperado="el sello como token de RFC 3161 en base64",
                    encontrado="un sello escrito en XML",
                )
            )
            continue
        if hallado.sello is None:
            incidencias.append(
                Incidencia(
                    "SELLO-ILEGIBLE",
                    AVISO,
                    "La firma lleva un sello de tiempo que no se ha podido "
                    f"leer: {hallado.motivo}. No se ha usado su fecha para "
                    "nada, así que la del documento sigue siendo la que "
                    "declara quien firma.",
                    campo=f"{donde}Sello de tiempo",
                    encontrado=hallado.clase,
                )
            )
            continue
        if not hallado.sobre_la_firma:
            incidencias.append(_otra_clase(hallado, donde))
            continue

        sello = hallado.sello
        motivo = comprobar(sello)
        if motivo:
            incidencias.append(
                Incidencia(
                    "SELLO-ROTO",
                    ERROR,
                    f"El sello de tiempo de la firma no se sostiene: {motivo}. "
                    "Un sello que no cuadra no acredita ninguna fecha.",
                    campo=f"{donde}Sello de tiempo",
                    esperado="un sello coherente y firmado por su autoridad",
                    encontrado=f"sello de «{sello.quien}»",
                )
            )
            continue

        datos, fallo = entrada_del_sello(firma, hallado.c14n)
        if datos is None:
            incidencias.append(
                Incidencia(
                    "SELLO-SIN-COMPROBAR",
                    AVISO,
                    "El sello de tiempo está bien formado, pero no se ha "
                    f"podido comprobar a qué se refiere: {fallo}. No se ha "
                    "dado por buena su fecha.",
                    campo=f"{donde}Sello de tiempo",
                    encontrado=f"sello de «{sello.quien}»",
                )
            )
            continue

        motivo = cubre(sello, datos)
        if motivo:
            incidencias.append(
                Incidencia(
                    "SELLO-NO-CUBRE",
                    ERROR,
                    f"El sello de tiempo está bien y lo firmó «{sello.quien}», "
                    f"pero no es de esta firma: {motivo}. Un sello copiado de "
                    "otro documento no acredita nada de este.",
                    campo=f"{donde}Sello de tiempo",
                    esperado="un sello del valor de esta firma",
                    encontrado="un sello de otra cosa, del "
                    f"{cifras.fecha(sello.momento)}",
                )
            )
            continue

        alguno_bueno = True
        incidencias.extend(_algoritmos(sello, donde))
        incidencias.extend(_contra_el_certificado(sello, cert, donde))
        incidencias.extend(_despues_de_caducar(sello, cert, donde))
        incidencias.extend(_contradice(sello, firma, donde))
        incidencias.append(_correcto(sello, donde))

    # Traer un sello que no sirve no es lo mismo que no traer ninguno, aunque
    # acabe en la misma fecha: hay que decir con cuál se ha trabajado, y hay
    # que decirlo sin negar un sello que está puesto. Cuando hay sellos de otra
    # clase ya se ha dicho por ellos.
    if not alguno_bueno and not any(
        i.codigo == "SELLO-NO-COMPROBADO" for i in incidencias
    ):
        incidencias.extend(_sin_sello(firma, donde, llevaba=bool(hallados)))
    return incidencias


def reglas_de_documento(raiz, deteccion) -> list[Incidencia]:
    """Lo mismo, sacando las firmas del documento.

    El certificado que firma sale de `firma.py`, que es de quien depende este
    módulo; el import va aquí dentro y no arriba porque arriba solo entran los
    nombres que el módulo usa siempre.
    """
    from validador.firma import certificados_de, hay_firma

    if raiz is None or not deteccion:
        return []
    firmas = hay_firma(raiz)
    incidencias: list[Incidencia] = []
    for numero, una in enumerate(firmas, start=1):
        donde = f"Firma {numero} · " if len(firmas) > 1 else ""
        certificados = certificados_de(una)
        primero = certificados[0] if certificados else None
        incidencias.extend(reglas(una, primero, donde))
    return incidencias
