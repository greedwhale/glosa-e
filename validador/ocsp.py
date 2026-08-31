# -*- coding: utf-8 -*-
"""Las respuestas OCSP que el documento trae dentro.

Hasta ahora este validador sabía **que estaban** y no sabía leerlas. El aviso
lo decía en voz alta —`revocacion.trae_ocsp()`— porque callarlo habría dado a
entender que el documento no traía nada. Esto es lo que faltaba.

Por qué importa, y por qué no contradice a `revocacion.py`
----------------------------------------------------------
`revocacion.py` explica por qué este proyecto no **pregunta** por OCSP: una
consulta OCSP lleva dentro el número de serie del certificado, así que le dice
a la autoridad exactamente qué se está mirando y cuándo. Para una herramienta
cuya promesa es que la factura no sale del ordenador, eso no es un detalle.

Leer una respuesta que **ya viene dentro del documento** es lo contrario: no
se abre ninguna conexión, no se le cuenta nada a nadie, y se aprovecha algo
que el firmante metió ahí precisamente para que se pudiera comprobar sin red.
Un documento XAdES-XL moderno guarda respuestas OCSP y a menudo **no** guarda
CRL, así que sin esto la revocación de esos documentos no se comprueba nunca.

Lo que una respuesta OCSP dice de verdad
-----------------------------------------
Dice si aquel certificado estaba anulado **en el momento en que la respuesta se
produjo**, y nada más. Es una foto con fecha, no un estado permanente. De las
muestras locales, una respuesta declara `thisUpdate` a las 12:22 del 20 de
febrero de 2019 y `nextUpdate` una hora después: hoy está caducadísima, y eso
**no la invalida** como prueba de lo que pasaba aquel día. Lo que invalida es
usarla para afirmar algo de hoy.

De ahí las tres lecturas, que son las mismas que ya aplica `revocacion.py` a
las CRL:

- Si la respuesta es **posterior** a la firma y dice «bueno», se comprobó la
  revocación en un momento en que la firma ya existía. Es la buena.
- Si es **anterior** a la firma, no dice nada de la firma: se firmó después de
  mirar. Sale como aviso.
- Y si la fecha de la firma la escribió quien firma —sin sello de tiempo—,
  comparar las dos fechas es fiarse de su palabra. Se dice, en vez de enseñar
  un tic verde.

Lo que hay que comprobar antes de creerse una
----------------------------------------------
Una respuesta OCSP metida dentro del propio documento la puso quien firma. Si
se leyera sin verificar la firma de la respuesta, cualquiera podría adjuntar
un «este certificado está perfectamente» escrito por él mismo. Así que:

1. **Que la respuesta hable de este certificado.** El `CertID` no lleva el
   certificado: lleva el resumen del nombre del emisor, el resumen de su clave
   pública y el número de serie. Los tres se recalculan aquí y se comparan.
2. **Que la firme quien puede firmarla.** O la propia autoridad que emitió el
   certificado, o un respondedor en quien esa autoridad delegó —y la
   delegación se demuestra: su certificado lo firma la misma autoridad y lleva
   el uso extendido `id-kp-OCSPSigning`, sin el cual no vale—.
3. **Que la firma cuadre**, con la misma maquinaria RSA y ECDSA que el resto.

Si alguna de las tres falla, la respuesta **no se usa** y se dice por qué. Una
respuesta que no se puede verificar es peor que ninguna: ninguna se nota.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
from dataclasses import dataclass
from datetime import datetime

from validador.firma import (
    Certificado,
    ClaveNoSoportada,
    _OID_ALGORITMO,
    _elementos,
    _fecha_der,
    _oid,
    _tlv,
    leer_certificado,
    verificar,
)

__all__ = [
    "Estado",
    "Respuesta",
    "leer_respuesta",
    "respuestas_del_documento",
    "casa_con",
    "quien_la_firma",
    "verificar_respuesta",
    "ESTADOS_DE_RESPUESTA",
]

# 1.3.6.1.5.5.7.48.1.1 — la única clase de respuesta que existe en la práctica.
_OID_BASICA = "2b0601050507300101"
# 1.3.6.1.5.5.7.3.9 — el uso extendido que convierte a un certificado en
# respondedor delegado. Sin él, la delegación no está.
_OID_FIRMA_OCSP = "2b06010505070309"
# 2.5.29.37 extendedKeyUsage
_OID_USOS_EXTENDIDOS = "551d25"
# 2.5.29.37.0 anyExtendedKeyUsage. **No** sirve para delegar: el RFC 6960 pide
# el uso concreto, y aceptar el comodín convertiría a cualquier certificado de
# la autoridad en respondedor válido.
_OID_CUALQUIER_USO = "551d2500"

# Los resúmenes con los que se construye un CertID. Aquí solo los que se saben
# calcular: uno que no esté hace que la respuesta no se pueda emparejar, y eso
# se dice en vez de emparejarla a ojo.
_OID_RESUMEN = {
    "2b0e03021a": "sha1",
    "608648016503040201": "sha256",
    "608648016503040202": "sha384",
    "608648016503040203": "sha512",
    "60864801650304020a": "sha3_512",
}

ESTADOS_DE_RESPUESTA = {
    0: "correcta",
    1: "mal formada, según el propio respondedor",
    2: "el respondedor tuvo un error interno",
    3: "el respondedor pidió que se volviera a intentar más tarde",
    5: "el respondedor exigía que la pregunta fuera firmada",
    6: "el respondedor no atiende a quien preguntó",
}

# Los mismos que en `revocacion.py`, y a propósito: un motivo de anulación no
# significa una cosa distinta por venir en una respuesta OCSP en vez de en una
# lista.
MOTIVOS = {
    0: "sin decir por qué",
    1: "porque la clave privada quedó comprometida",
    2: "porque la clave de la autoridad quedó comprometida",
    3: "porque cambió la afiliación de quien lo tenía",
    4: "porque se sustituyó por otro",
    5: "porque cesó la actividad",
    6: "porque está suspendido temporalmente",
    8: "porque se retiró de la lista de anulados",
    9: "porque se retiró el privilegio",
    10: "porque se retiró la autorización de la autoridad de atributos",
}


@dataclass(frozen=True)
class Estado:
    """Lo que una respuesta dice de **un** certificado.

    Una respuesta puede hablar de varios; en la práctica habla de uno.
    """

    serie: int
    hash_nombre: bytes
    hash_clave: bytes
    resumen: str  # "sha1", "sha256"... o "" si no se sabe calcular
    anulado: bool
    sin_saber: bool  # el respondedor dijo «unknown»
    mirada: datetime | None  # thisUpdate
    vale_hasta: datetime | None  # nextUpdate
    anulado_el: datetime | None = None
    motivo: int | None = None

    @property
    def bueno(self) -> bool:
        return not self.anulado and not self.sin_saber


@dataclass(frozen=True)
class Respuesta:
    """Una respuesta OCSP entera, ya troceada pero **todavía no creída**."""

    estado_global: int
    estados: tuple[Estado, ...] = ()
    producida: datetime | None = None
    # Lo que hay que verificar, byte a byte tal como vino. Reconstruirlo desde
    # los campos daría otra codificación y la firma no cuadraría: DER admite
    # una sola forma, pero quien la escribió pudo no ser estricto.
    tbs: bytes = b""
    firma: bytes = b""
    algoritmo: str = ""
    algoritmo_roto: bool = False
    certificados: tuple[Certificado, ...] = ()
    # ResponderID: o el nombre del respondedor, o el resumen de su clave.
    por_nombre: bytes | None = None
    por_clave: bytes | None = None
    # Por qué no se pudo ni trocear, cuando no se pudo. Una respuesta ilegible
    # se guarda en vez de tirarse: el informe tiene que poder distinguir «no
    # traía ninguna» de «traía una y no se supo leer».
    ilegible: str = ""

    @property
    def correcta(self) -> bool:
        return self.estado_global == 0

    @property
    def que_paso(self) -> str:
        return ESTADOS_DE_RESPUESTA.get(
            self.estado_global, f"con un estado que no se reconoce ({self.estado_global})"
        )


# --- DER, lo justo ---------------------------------------------------------


def _con_bruto(datos: bytes, pos: int = 0):
    """Como `_tlv`, pero devolviendo además el elemento entero sin tocar.

    Hace falta para `tbsResponseData`: es lo que se firma, y se verifica
    contra los bytes que vinieron, no contra una recodificación.
    """
    etiqueta, contenido, siguiente = _tlv(datos, pos)
    return etiqueta, contenido, siguiente, datos[pos:siguiente]


def _clave_cruda(cert: Certificado) -> bytes | None:
    """El `subjectPublicKey` tal cual, sin el byte de bits sobrantes.

    Es lo que el RFC 6960 manda resumir para el `issuerKeyHash`: no el
    SubjectPublicKeyInfo entero, solo la cadena de bits de la clave.
    """
    try:
        _, tbs, _ = _tlv(cert.tbs)
        campos = _elementos(tbs)
        salto = 1 if campos and campos[0][0] == 0xA0 else 0
        spki = _elementos(campos[salto + 5][1])
        bits = spki[1][1]
    except (ValueError, IndexError):
        return None
    if not bits or bits[0] != 0:
        return None
    return bits[1:]


# --- La lectura ------------------------------------------------------------


def _leer_estado(crudo: bytes) -> Estado | None:
    partes = _elementos(crudo)
    if len(partes) < 3:
        return None
    certid = _elementos(partes[0][1])
    if len(certid) < 4:
        return None
    algoritmo = _elementos(certid[0][1])
    resumen = _OID_RESUMEN.get(
        _oid(algoritmo[0][1]) if algoritmo and algoritmo[0][0] == 0x06 else "", ""
    )

    # `CertStatus ::= CHOICE { good [0] IMPLICIT NULL, revoked [1] IMPLICIT
    # RevokedInfo, unknown [2] IMPLICIT UnknownInfo }`. El etiquetado es
    # **implícito**, así que la etiqueta sustituye a la del tipo de dentro y no
    # la envuelve: `revoked` es una SEQUENCE y sale construida (0xA1), pero
    # `good` y `unknown` son NULL y salen primitivas (0x80 y 0x82).
    #
    # Buscar 0xA2 para «unknown» —que es lo que había— hacía que un «no lo sé»
    # se leyera como «está bien», que es el error en la dirección que importa:
    # un respondedor que no reconoce el certificado no está diciendo que esté
    # sano. Se admite también la forma construida, que alguien puede emitir,
    # pero la primitiva es la del RFC.
    etiqueta_estado, dentro = partes[1]
    anulado = etiqueta_estado in (0xA1, 0x81)
    sin_saber = etiqueta_estado in (0x82, 0xA2)
    anulado_el = motivo = None
    if anulado:
        # RevokedInfo ::= SEQUENCE { revocationTime, [0] revocationReason }
        trozos = _elementos(dentro)
        if trozos:
            anulado_el = _fecha_der(*trozos[0])
        for etiqueta, valor in trozos[1:]:
            if etiqueta == 0xA0 and valor:
                try:
                    _, razon, _ = _tlv(valor)
                    motivo = int.from_bytes(razon, "big") if razon else 0
                except ValueError:
                    motivo = None

    mirada = _fecha_der(*partes[2])
    # `nextUpdate` va etiquetado [0] y **explícito**: dentro del A0 hay otro
    # elemento, el GeneralizedTime de verdad. Leer el A0 como si fuera la fecha
    # daría una hora inventada a partir de los bytes de la cabecera.
    vale_hasta = None
    for etiqueta, valor in partes[3:]:
        if etiqueta == 0xA0 and valor:
            try:
                etiqueta_fecha, crudo, _ = _tlv(valor)
                vale_hasta = _fecha_der(etiqueta_fecha, crudo)
            except ValueError:
                vale_hasta = None

    return Estado(
        serie=int.from_bytes(certid[3][1], "big"),
        hash_nombre=certid[1][1],
        hash_clave=certid[2][1],
        resumen=resumen,
        anulado=anulado,
        sin_saber=sin_saber,
        mirada=mirada,
        vale_hasta=vale_hasta,
        anulado_el=anulado_el,
        motivo=motivo,
    )


def _leer_basica(basica: bytes, estado_global: int = 0) -> Respuesta:
    """Trocea una `BasicOCSPResponse`, que es donde está todo lo que importa.

    `basica` es el **contenido** de la SEQUENCE, sin su cabecera.
    """
    campos = _elementos(basica)
    if len(campos) < 3:
        raise ValueError("la respuesta básica está incompleta")

    # `tbsResponseData` hay que guardarlo entero y sin tocar: es lo que se
    # firmó, y reconstruirlo desde los campos daría otra codificación.
    _, tbs_contenido, _, tbs_bruto = _con_bruto(basica)

    algoritmos = _elementos(campos[1][1])
    algoritmo, roto = "", False
    if algoritmos and algoritmos[0][0] == 0x06:
        algoritmo, roto = _OID_ALGORITMO.get(_oid(algoritmos[0][1]), ("", False))

    bits = campos[2][1]
    firma = bits[1:] if bits and bits[0] == 0 else b""

    certificados = []
    for etiqueta, valor in campos[3:]:
        if etiqueta != 0xA0:
            continue
        try:
            _, dentro, _ = _tlv(valor)
        except ValueError:
            continue
        # Se recorre a mano en vez de con `_elementos` porque hace falta el
        # certificado **entero**, con su cabecera: `leer_certificado` espera un
        # DER completo, no el contenido de la SEQUENCE.
        pos = 0
        while pos < len(dentro):
            try:
                _, _, siguiente, bruto = _con_bruto(dentro, pos)
            except ValueError:
                break
            pos = siguiente
            try:
                certificados.append(leer_certificado(bruto))
            except (ValueError, ClaveNoSoportada):
                # Un certificado que no se sabe leer no tumba la respuesta:
                # puede que el que hace falta sea otro de la misma lista.
                continue

    datos = _elementos(tbs_contenido)
    salto = 1 if datos and datos[0][0] == 0xA0 else 0
    por_nombre = por_clave = None
    if len(datos) > salto:
        etiqueta, valor = datos[salto]
        if etiqueta == 0xA1:
            por_nombre = valor
        elif etiqueta == 0xA2:
            try:
                _, dentro, _ = _tlv(valor)
                _, por_clave, _ = _tlv(dentro)
            except ValueError:
                por_clave = None

    producida = _fecha_der(*datos[salto + 1]) if len(datos) > salto + 1 else None
    estados = []
    if len(datos) > salto + 2:
        for _, uno in _elementos(datos[salto + 2][1]):
            leido = _leer_estado(uno)
            if leido is not None:
                estados.append(leido)

    return Respuesta(
        estado_global=estado_global,
        estados=tuple(estados),
        producida=producida,
        tbs=tbs_bruto,
        firma=firma,
        algoritmo=algoritmo,
        algoritmo_roto=roto,
        certificados=tuple(certificados),
        por_nombre=por_nombre,
        por_clave=por_clave,
    )


def leer_respuesta(der: bytes) -> Respuesta:
    """Trocea lo que venga dentro de un `EncapsulatedOCSPValue`.

    Lo que sale de aquí **no está creído**: para eso están `casa_con()` y
    `verificar_respuesta()`. Separarlo es a propósito, porque el informe tiene
    que poder decir «venía una respuesta y no se pudo verificar», que es
    distinto de «no venía ninguna».

    **Y aquí caben dos codificaciones distintas**, porque en la vida real las
    hay. ETSI TS 101 903 dice que este elemento lleva una `OCSPResponse`
    entera: el ENUMERATED del estado y, dentro de un [0], los datos. Pero de
    las cuatro respuestas de `78353__XAdES_A_Detached.xml`, dos vienen así y
    **dos traen el `BasicOCSPResponse` pelado**, sin envoltorio.

    Distinguirlas es mirar la etiqueta del primer hijo, y hacerlo importa: al
    leer un `BasicOCSPResponse` como si fuera una `OCSPResponse`, los 216 bytes
    del `tbsResponseData` se interpretan como el entero del estado y sale un
    número de quinientos dígitos. No revienta —ahí está el problema—: devuelve
    una respuesta vacía y el informe diría que no se pudo leer.
    """
    _, cuerpo, _ = _tlv(der)
    partes = _elementos(cuerpo)
    if not partes:
        raise ValueError("la respuesta OCSP está vacía")

    # `BasicOCSPResponse` pelado: SEQUENCE, SEQUENCE, BIT STRING, [0] opcional.
    if partes[0][0] == 0x30:
        if len(partes) < 3 or partes[2][0] != 0x03:
            raise ValueError("no parece ni una OCSPResponse ni una básica")
        return _leer_basica(cuerpo)

    if partes[0][0] != 0x0A:
        raise ValueError("la respuesta OCSP no empieza por su estado")

    estado_global = int.from_bytes(partes[0][1], "big") if partes[0][1] else 0
    if estado_global != 0 or len(partes) < 2:
        # Un respondedor que contesta «inténtalo luego» no trae datos. Se
        # devuelve igual, para poder contar qué pasó en vez de callarlo.
        return Respuesta(estado_global=estado_global)

    _, bytes_resp, _ = _tlv(partes[1][1])
    trozos = _elementos(bytes_resp)
    if len(trozos) < 2 or _oid(trozos[0][1]) != _OID_BASICA:
        raise ValueError("la respuesta no es del tipo básico de OCSP")

    _, basica, _ = _tlv(trozos[1][1])
    return _leer_basica(basica, estado_global)


def respuestas_del_documento(firma_xml) -> list[Respuesta]:
    """Las respuestas OCSP guardadas dentro de una firma XAdES.

    Una que no se pueda trocear **no se tira**: se devuelve marcada como
    ilegible. Descartarla dejaría un documento con una respuesta rota igual que
    uno sin ninguna, y no es lo mismo —el primero trae una prueba que alguien
    quiso dejar ahí y no se sabe leer, y eso hay que decirlo—. Las demás siguen
    sirviendo: cuatro respuestas y una rota son tres que valen y una que se
    cuenta.
    """
    salida = []
    for nodo in firma_xml.xpath(".//*[local-name()='EncapsulatedOCSPValue']"):
        if nodo.text is None:
            salida.append(Respuesta(estado_global=-1, ilegible="viene vacía"))
            continue
        try:
            der = base64.b64decode("".join(nodo.text.split()))
        except (binascii.Error, ValueError):
            salida.append(
                Respuesta(estado_global=-1, ilegible="el base64 no se descodifica")
            )
            continue
        try:
            salida.append(leer_respuesta(der))
        except (ValueError, IndexError) as error:
            salida.append(Respuesta(estado_global=-1, ilegible=str(error)))
    return salida


# --- Creérsela, o no -------------------------------------------------------


def casa_con(estado: Estado, cert: Certificado, emisor: Certificado) -> bool:
    """¿Este `Estado` habla de este certificado?

    El `CertID` no lleva el certificado dentro: lleva el número de serie y dos
    resúmenes del **emisor** —de su nombre y de su clave pública—. Los tres
    tienen que cuadrar. Comparar solo el número de serie sería un agujero
    grande: las series solo son únicas dentro de una misma autoridad.
    """
    if estado.serie != cert.serie:
        return False
    if not estado.resumen:
        return False
    clave = _clave_cruda(emisor)
    if clave is None or not emisor.sujeto_der:
        return False
    try:
        resumir = getattr(hashlib, estado.resumen)
    except AttributeError:
        return False
    return (
        resumir(emisor.sujeto_der).digest() == estado.hash_nombre
        and resumir(clave).digest() == estado.hash_clave
    )


def _delega(candidato: Certificado) -> bool:
    """¿La autoridad autorizó a este certificado a responder por ella?

    Se exige `id-kp-OCSPSigning` explícito. El comodín `anyExtendedKeyUsage`
    no vale: aceptarlo convertiría en respondedor a cualquier certificado que
    la autoridad haya emitido, que es justo lo que la delegación acota.
    """
    for oid, valor in candidato.extensiones:
        if oid != _OID_USOS_EXTENDIDOS:
            continue
        try:
            _, dentro, _ = _tlv(valor)
        except ValueError:
            return False
        for etiqueta, uno in _elementos(dentro):
            if etiqueta == 0x06 and _oid(uno) == _OID_FIRMA_OCSP:
                return True
    return False


def _es_el_del_id(respuesta: Respuesta, candidato: Certificado) -> bool:
    """¿El `ResponderID` de la respuesta señala a este certificado?

    Por nombre, comparando el `Name` entero; o por resumen de la clave, que es
    siempre SHA-1 —lo fija el RFC 6960 y no es negociable como en el CertID—.
    """
    if respuesta.por_nombre is not None and candidato.sujeto_der:
        if respuesta.por_nombre == candidato.sujeto_der:
            return True
    if respuesta.por_clave is not None:
        clave = _clave_cruda(candidato)
        if clave is not None and hashlib.sha1(clave).digest() == respuesta.por_clave:
            return True
    return False


def _lo_firma(candidato: Certificado, emisor: Certificado) -> bool:
    """¿Emitió esta autoridad ese certificado? Comprobando la firma, no el campo.

    El campo `issuer` lo escribe quien fabrica el certificado y no prueba nada.
    """
    if not candidato.tbs or not candidato.valor_firma:
        return False
    if candidato.emisor_der and emisor.sujeto_der:
        if candidato.emisor_der != emisor.sujeto_der:
            return False
    try:
        return verificar(
            candidato.valor_firma,
            candidato.tbs,
            emisor,
            candidato.algoritmo_firma or "sha256",
        )
    except (ValueError, ClaveNoSoportada):
        return False


def quien_la_firma(
    respuesta: Respuesta, emisor: Certificado
) -> tuple[Certificado | None, str]:
    """El certificado con el que verificar, y por qué se le deja firmar.

    Devuelve `(None, motivo)` cuando no hay ninguno aceptable, y el motivo se
    escribe para poder contarlo en el informe.
    """
    # 1. ¿De quién habla el ResponderID? Puede ser la autoridad o un delegado,
    #    así que se busca entre todos los certificados a mano antes de
    #    preguntarse si a ese se le deja firmar.
    candidatos = [emisor, *respuesta.certificados]
    quien = None
    for uno in candidatos:
        if _es_el_del_id(respuesta, uno):
            quien = uno
            break

    # 2. Si el ResponderID no señala a nadie conocido, aún puede estar el
    #    respondedor entre los certificados adjuntos: hay emisores que ponen
    #    ahí el nombre con una codificación distinta de la del certificado.
    #    Se admite, pero solo si la delegación se demuestra igual.
    if quien is None:
        for uno in respuesta.certificados:
            if _delega(uno) and _lo_firma(uno, emisor):
                return uno, "la firma un respondedor delegado por la autoridad"
        if respuesta.certificados:
            return None, (
                "la respuesta trae certificados, pero ninguno está autorizado "
                "por esta autoridad a responder por ella"
            )
        return None, "no se sabe quién firmó la respuesta"

    # 3. Si quien firma es la propia autoridad, no hace falta delegación: una
    #    autoridad puede responder por lo que ella misma emitió.
    if quien is emisor:
        return emisor, "la firma la propia autoridad"

    # 4. Y si es otro, tiene que estar delegado **y** llevar la firma de la
    #    autoridad. Con una de las dos cosas no basta: el uso extendido lo
    #    escribe quien hace el certificado, y sin comprobar la firma cualquiera
    #    podría fabricarse un respondedor.
    if not _delega(quien):
        return None, (
            "quien firma la respuesta no es la autoridad y su certificado no "
            "lleva el uso de firma OCSP, así que no está delegado"
        )
    if not _lo_firma(quien, emisor):
        return None, (
            "quien firma la respuesta dice estar delegado, pero su certificado "
            "no lo ha emitido esta autoridad"
        )
    return quien, "la firma un respondedor delegado por la autoridad"


def verificar_respuesta(
    respuesta: Respuesta, emisor: Certificado
) -> tuple[bool, str]:
    """¿Se puede creer esta respuesta? Y si no, por qué no.

    Verificar es lo que separa una prueba de un papel que trae quien firma.
    Sin esto, cualquiera podría adjuntar a su documento un «este certificado
    está perfectamente» escrito por él mismo.
    """
    if respuesta.ilegible:
        return False, f"la respuesta no se pudo ni abrir: {respuesta.ilegible}"
    if not respuesta.correcta:
        return False, f"la respuesta viene {respuesta.que_paso}"
    if not respuesta.tbs or not respuesta.firma:
        return False, "la respuesta no trae firma"
    if not respuesta.algoritmo:
        return False, "la respuesta está firmada con un algoritmo que no se reconoce"

    quien, porque = quien_la_firma(respuesta, emisor)
    if quien is None:
        return False, porque
    try:
        bien = verificar(respuesta.firma, respuesta.tbs, quien, respuesta.algoritmo)
    except (ValueError, ClaveNoSoportada) as e:
        return False, f"la firma de la respuesta no se pudo comprobar: {e}"
    if not bien:
        return False, "la firma de la respuesta no cuadra"
    return True, porque
