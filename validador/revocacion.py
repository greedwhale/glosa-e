"""¿Sigue valiendo el certificado, o lo anularon?

`firma.py` dice que el documento no se ha tocado y que la firma cuadra con su
certificado. `cadena.py` dice de quién es ese certificado. Falta la última
pregunta, y es la única que un certificado no puede contestar sobre sí mismo:
**si lo anularon antes de usarlo**.

Un certificado no sabe que ha muerto. Lleva dentro su fecha de caducidad, pero
no lleva —no puede llevar— la noticia de que su titular perdió la clave el mes
pasado. Esa noticia la publica la autoridad después, por separado, y por eso
esta es la única parte del validador que necesita algo de fuera.

Tres formas de conseguir esa prueba, y la que no se usa
-------------------------------------------------------
1. **Que la traiga el documento.** XAdES-XL guarda dentro de la firma la
   prueba de revocación del momento en que se firmó: listas (CRL) o respuestas
   OCSP, y a menudo lo segundo y no lo primero. Es lo que la norma inventó para
   que una firma se pueda comprobar dentro de veinte años, cuando la autoridad
   que la emitió ya no exista. Cero red, y es la única forma que sigue
   funcionando cuando la lista de entonces ya no está publicada.
2. **Una lista puesta en una carpeta**, igual que los esquemas XSD y las
   anclas. Se baja una vez y sirve para todas las facturas de esa autoridad
   hasta que caduque. Solo en consola: en la página no hay carpeta ni forma de
   poner una (`AlmacenDeListas.sin_carpeta`), y lo que vale allí es lo
   primero.
3. **Preguntar por internet.** Aquí no se hace: **este paquete no abre ni una
   conexión**, y eso se puede comprobar con un `grep`. Lo que hace es decir qué
   lista le falta y dónde dice el propio certificado que está. Bajarla es un
   acto explícito de quien usa la herramienta, no algo que pase de fondo.

Por qué no se pregunta por OCSP, y qué sí se lee
------------------------------------------------
Las dos contestan lo mismo y filtran cosas muy distintas.

Una **CRL** es la lista entera de anulados de una autoridad. Al bajarla no se
dice qué certificado interesa: se piden todos. Quien sirve el fichero se entera
de que alguien está validando algo suyo, y de nada más.

Una consulta **OCSP** lleva dentro el número de serie del certificado. Le dice
a la autoridad exactamente qué certificado se está mirando y a qué hora: o sea,
de qué factura se trata y cuándo llegó. Para un validador cuya promesa es que
la factura no sale del ordenador, la diferencia no es un detalle.

Esto no es teórico. De las cinco facturas firmadas que hay de muestra, cuatro
apuntan a una CRL y **la firmada con DNIe no publica CRL ninguna**: solo OCSP.
Con ese certificado no hay forma de comprobar la revocación sin decirle al
emisor qué se está mirando. Se dice, y que elija quien valida.

Ahora bien: eso es **preguntar**. Leer la respuesta que ya viene dentro del
documento es lo contrario —no abre ninguna conexión, no le cuenta nada a nadie,
y aprovecha algo que el firmante metió ahí justamente para que se pudiera
comprobar sin red—. Eso sí se hace: `ocsp.py` las lee y las verifica, y aquí se
consultan con las mismas tres preguntas que a una CRL. Un XAdES-XL moderno
guarda OCSP y muchas veces no guarda CRL, así que sin esto la revocación de
esos documentos no se comprobaba nunca.

El problema de las fechas, que es el que casi nadie cuenta
----------------------------------------------------------
Una revocación tiene fecha, y la firma también. Que un certificado esté anulado
**hoy** no invalida una factura firmada **hace dos años**: en su momento valía.
Salvo que lo anularan porque le robaron la clave, y entonces al revés: todo lo
que esa clave firmó pasa a ser sospechoso, incluso lo anterior a la denuncia,
porque quien la robó pudo firmar con fecha atrasada.

Y hay una vuelta más: la fecha de firma **la escribe quien firma**. Comparar
las dos fechas es entonces fiarse de la palabra del firmante, y eso se dice en
vez de enseñar un tic verde.

Cuando el documento trae sello de tiempo, la fecha ya no es suya y este módulo
lo nota: `cadena.py` le pasa la del sello y, con ella, «se anuló después de
firmar» deja de ser un aviso y pasa a ser una nota. Ver `sellos.py`.

La trampa de la respuesta negativa
----------------------------------
«No está en la lista» solo significa «no está revocado» si la lista **está
firmada por la autoridad que toca**, **es posterior al momento que se juzga** y
**cubre a ese certificado**. Si falla cualquiera de las tres, la ausencia no
prueba nada —y es justo ahí donde un validador tiene la tentación de pintar el
tic verde—. Aquí no se pinta: se dice por qué no se sabe.
"""

from __future__ import annotations

import base64
import binascii
import os
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from validador import cifras, ocsp
from validador.firma import (
    _OID_ALGORITMO,
    Certificado,
    _elementos,
    _fecha_der,
    _nombre_der,
    _oid,
    _tlv,
    verificar,
)
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia

__all__ = [
    "AlmacenDeListas",
    "Anulacion",
    "Lista",
    "PruebaOcsp",
    "Veredicto",
    "comprobar",
    "comprobar_ocsp",
    "donde_esta_el_ocsp",
    "donde_esta_la_lista",
    "leer_lista",
    "listas_del_documento",
    "reglas",
]

VARIABLE_ENTORNO = "FACTURAE_REVOCACIONES"
CARPETA_POR_DEFECTO = "revocaciones"

# Los avisos que dicen que del certificado que firma **no se sabe** si está
# anulado, o que lo que se sabe sale de una lista vencida. La frase del final
# del informe los busca para no apuntarse la revocación de un documento que
# los lleva.
#
# Hacía falta porque la frase colgaba de un solo interruptor, «¿hay alguna
# lista en la carpeta?», que no mira lo que pasó con cada documento. Medido el
# 05-10-2026 con el Python de la página: «No se comprueba si el certificado
# está anulado (hace falta la lista de revocación de su autoridad)» salía
# pegado a un REVOCADO sacado de la lista que traía la propia factura, y en
# consola una lista de otra autoridad bastaba para prometer la revocación de
# todas.
#
# La vieja entra aunque pueda hablar de un certificado de más arriba: es un
# aviso de que la prueba no vale lo que parece, y ante la duda la frase calla.
SIN_CONTESTAR = frozenset({
    "REVOCACION-SIN-COMPROBAR",
    "REVOCACION-SOLO-OCSP",
    "REVOCACION-OCSP-NO-VALE",
    "REVOCACION-LISTA-VIEJA",
})

_EXTENSIONES = (".crl", ".der", ".pem")
_PEM = re.compile(rb"-----BEGIN X509 CRL-----(.*?)-----END X509 CRL-----", re.S)

# Extensiones de la propia lista.
_OID_NUMERO = "551d14"  # 2.5.29.20 cRLNumber
_OID_DELTA = "551d1b"  # 2.5.29.27 deltaCRLIndicator
_OID_ALCANCE = "551d1c"  # 2.5.29.28 issuingDistributionPoint
# Extensiones de cada línea.
_OID_MOTIVO = "551d15"  # 2.5.29.21 CRLReason
_OID_INVALIDA_DESDE = "551d18"  # 2.5.29.24 invalidityDate
_OID_OTRO_EMISOR = "551d1d"  # 2.5.29.29 certificateIssuer
# Extensiones del certificado que dicen dónde buscar.
_OID_PUNTOS = "551d1f"  # 2.5.29.31 cRLDistributionPoints
_OID_ACCESOS = "2b06010505070101"  # 1.3.6.1.5.5.7.1.1 authorityInfoAccess
_OID_OCSP = "2b06010505073001"  # 1.3.6.1.5.5.7.48.1

# Las críticas que sí sabemos leer. Una crítica que no esté aquí inutiliza la
# lista entera: lo manda el RFC 5280 y tiene su lógica —si la autoridad marcó
# algo como imprescindible y no lo entendemos, no sabemos qué estamos leyendo—.
_ENTENDIDAS = frozenset({_OID_NUMERO, _OID_DELTA, _OID_ALCANCE})

MOTIVOS = {
    0: "sin decir por qué",
    1: "porque la clave privada quedó comprometida",
    2: "porque la clave de la autoridad quedó comprometida",
    3: "porque cambió la vinculación del titular",
    4: "porque se sustituyó por otro certificado",
    5: "porque cesó la actividad",
    6: "en suspenso, temporalmente",
    8: "para sacarlo de la lista",
    9: "porque se le retiró un privilegio",
    10: "porque la autoridad de atributos quedó comprometida",
}

# Los motivos que miran hacia atrás: si la clave estaba en malas manos, lo que
# firmó antes de que se supiera tampoco vale.
COMPROMISO = frozenset({1, 2, 10})
SUSPENSION = 6


# --- Leer una lista --------------------------------------------------------


@dataclass(frozen=True)
class Anulacion:
    """Una línea de la lista: este certificado, anulado tal día y por qué."""

    serie: int
    cuando: datetime | None
    motivo: int | None = None
    invalida_desde: datetime | None = None
    otro_emisor: bool = False

    @property
    def compromiso(self) -> bool:
        return self.motivo in COMPROMISO

    @property
    def suspension(self) -> bool:
        return self.motivo == SUSPENSION

    @property
    def texto_motivo(self) -> str:
        return MOTIVOS.get(self.motivo, "sin decir por qué")


@dataclass(frozen=True)
class Lista:
    """Una CRL abierta: quién la firma, cuándo, a quién cubre y a quién anula."""

    emisor_der: bytes
    emisor_nombre: str | None
    desde: datetime | None  # thisUpdate
    hasta: datetime | None  # nextUpdate
    anulaciones: dict[int, Anulacion]
    tbs: bytes = b""
    algoritmo_firma: str | None = None
    valor_firma: bytes = b""
    numero: int | None = None
    es_delta: bool = False
    solo_autoridades: bool = False
    solo_usuarios: bool = False
    solo_algunos_motivos: bool = False
    indirecta: bool = False
    criticas_sin_entender: frozenset[str] = frozenset()

    @property
    def parcial(self) -> str:
        """Por qué esta lista no puede dar un «no está anulado» que valga.

        Son los casos en que la ausencia deja de ser prueba. Una lista
        incremental es el más traicionero: parece una lista normal, y quien la
        lea como completa dará por vigente a todo el que no aparezca.
        """
        if self.es_delta:
            return (
                "es una lista incremental (delta): solo trae los cambios desde "
                "otra anterior, así que quien no aparezca puede estar anulado "
                "en la lista base"
            )
        if self.solo_algunos_motivos:
            return "solo recoge algunos motivos de anulación, no todos"
        if self.indirecta:
            return (
                "es una lista indirecta (cada línea puede venir de una autoridad "
                "distinta) y eso no se sabe leer todavía"
            )
        return ""


def _reserializar(elemento: tuple[int, bytes]) -> bytes:
    """Un TLV ya abierto, de vuelta a bytes. Para comparar nombres en DER."""
    etiqueta, contenido = elemento
    if len(contenido) < 0x80:
        largo = bytes([len(contenido)])
    else:
        crudo = len(contenido).to_bytes((len(contenido).bit_length() + 7) // 8, "big")
        largo = bytes([0x80 | len(crudo)]) + crudo
    return bytes([etiqueta]) + largo + contenido


def _extensiones_de_linea(contenido: bytes):
    motivo = None
    invalida = None
    otro = False
    for _, extension in _elementos(contenido):
        partes = _elementos(extension)
        if not partes:
            continue
        cual = _oid(partes[0][1])
        valor = partes[-1][1]
        if cual == _OID_MOTIVO:
            _, dentro, _ = _tlv(valor)
            motivo = int.from_bytes(dentro, "big") if dentro else None
        elif cual == _OID_INVALIDA_DESDE:
            etiqueta, dentro, _ = _tlv(valor)
            invalida = _fecha_der(etiqueta, dentro)
        elif cual == _OID_OTRO_EMISOR:
            otro = True
    return motivo, invalida, otro


def _alcance(valor: bytes):
    """`issuingDistributionPoint`: a qué parte del mundo contesta la lista.

    Los campos booleanos van con etiqueta implícita —[1], [2], [4], [5]—, o sea
    que llegan como primitivos de contexto con un byte de contenido.
    """
    solo_usuarios = solo_autoridades = solo_motivos = indirecta = False
    try:
        _, dentro, _ = _tlv(valor)
    except ValueError:
        return False, False, False, False
    for etiqueta, contenido in _elementos(dentro):
        cierto = contenido == bytes([0xFF])
        if etiqueta == 0x81:
            solo_usuarios = cierto
        elif etiqueta == 0x82:
            solo_autoridades = cierto
        elif etiqueta == 0x83:
            solo_motivos = True
        elif etiqueta == 0x84:
            indirecta = cierto
    return solo_usuarios, solo_autoridades, solo_motivos, indirecta


def leer_lista(der: bytes) -> Lista:
    """Una CRL en DER, abierta. La estructura está en el RFC 5280, apartado 5.

    El `tbsCertList` se guarda **tal cual venía**, por lo mismo que en un
    certificado: es la ristra exacta de octetos que la autoridad firmó, y
    volver a serializarla daría otros bytes en cuanto el DER no fuera estricto.
    """
    _, lista, _ = _tlv(der)
    partes = _elementos(lista)
    if len(partes) < 3:
        raise ValueError("no parece una lista de revocación")
    tbs = lista[: _tlv(lista)[2]]

    campos = _elementos(partes[0][1])
    # `version` es opcional, y es el único INTEGER que puede ir el primero: lo
    # que va detrás es siempre el algoritmo, que es una SEQUENCE.
    i = 1 if campos and campos[0][0] == 0x02 else 0
    if len(campos) < i + 3:
        raise ValueError("a la lista le faltan campos")
    i += 1  # el algoritmo de dentro; se lee el de fuera, que es el que firma
    emisor_der = _reserializar(campos[i])
    emisor_nombre = _nombre_der(campos[i][1])
    i += 1
    desde = _fecha_der(*campos[i])
    i += 1

    hasta = None
    if i < len(campos) and campos[i][0] in (0x17, 0x18):
        hasta = _fecha_der(*campos[i])
        i += 1

    anulaciones: dict[int, Anulacion] = {}
    if i < len(campos) and campos[i][0] == 0x30:
        for _, linea in _elementos(campos[i][1]):
            trozos = _elementos(linea)
            if len(trozos) < 2:
                continue
            serie = int.from_bytes(trozos[0][1], "big")
            cuando = _fecha_der(*trozos[1])
            motivo = invalida = None
            otro = False
            if len(trozos) > 2:
                motivo, invalida, otro = _extensiones_de_linea(trozos[2][1])
            anulaciones[serie] = Anulacion(serie, cuando, motivo, invalida, otro)
        i += 1

    numero = None
    es_delta = solo_usuarios = solo_autoridades = solo_motivos = indirecta = False
    criticas: set[str] = set()
    if i < len(campos) and campos[i][0] == 0xA0:
        _, dentro, _ = _tlv(campos[i][1])
        for _, extension in _elementos(dentro):
            partes_ext = _elementos(extension)
            if not partes_ext:
                continue
            cual = _oid(partes_ext[0][1])
            critica = len(partes_ext) == 3 and partes_ext[1][1] == bytes([0xFF])
            valor = partes_ext[-1][1]
            if cual == _OID_NUMERO:
                _, crudo, _ = _tlv(valor)
                numero = int.from_bytes(crudo, "big")
            elif cual == _OID_DELTA:
                es_delta = True
            elif cual == _OID_ALCANCE:
                (
                    solo_usuarios,
                    solo_autoridades,
                    solo_motivos,
                    indirecta,
                ) = _alcance(valor)
            elif critica:
                criticas.add(cual)

    algoritmo = None
    algoritmos = _elementos(partes[1][1])
    if algoritmos and algoritmos[0][0] == 0x06:
        pareja = _OID_ALGORITMO.get(_oid(algoritmos[0][1]))
        algoritmo = pareja[0] if pareja else None
    valor_firma = partes[2][1][1:] if partes[2][1][:1] == bytes([0]) else b""

    return Lista(
        emisor_der=emisor_der,
        emisor_nombre=emisor_nombre,
        desde=desde,
        hasta=hasta,
        anulaciones=anulaciones,
        tbs=tbs,
        algoritmo_firma=algoritmo,
        valor_firma=valor_firma,
        numero=numero,
        es_delta=es_delta,
        solo_autoridades=solo_autoridades,
        solo_usuarios=solo_usuarios,
        solo_algunos_motivos=solo_motivos,
        indirecta=indirecta,
        criticas_sin_entender=frozenset(criticas) - _ENTENDIDAS,
    )


def listas_del_fichero(datos: bytes) -> list[bytes]:
    """Las CRL de un fichero, vengan en PEM o en DER pelado."""
    trozos = [base64.b64decode(m.group(1)) for m in _PEM.finditer(datos)]
    if trozos:
        return trozos
    return [datos] if datos[:1] == bytes([0x30]) else []


# --- Dónde dice el certificado que está su lista ----------------------------


def _uris(valor: bytes, hondo: int = 0) -> list[str]:
    """Los `uniformResourceIdentifier` que haya dentro, a cualquier hondura.

    Un `GeneralName` de tipo URI es la etiqueta de contexto 6 en primitivo, y
    en `cRLDistributionPoints` viene envuelto en dos o tres capas según cómo lo
    escriba cada autoridad. Se recorre en vez de contar capas: aquí lo que
    interesa es enseñar la dirección, no reconstruir la estructura.
    """
    if hondo > 6:
        return []
    salida: list[str] = []
    try:
        elementos = _elementos(valor)
    except ValueError:
        return []
    for etiqueta, contenido in elementos:
        if etiqueta == 0x86:
            salida.append(contenido.decode("ascii", "replace"))
        elif etiqueta & 0x20:  # construido: hay más cosas dentro
            salida.extend(_uris(contenido, hondo + 1))
    return salida


def donde_esta_la_lista(cert: Certificado) -> list[str]:
    """Las direcciones que el certificado da para su CRL, si da alguna."""
    valor = cert.extension(_OID_PUNTOS)
    return _uris(valor) if valor else []


def donde_esta_el_ocsp(cert: Certificado) -> list[str]:
    """Las direcciones OCSP de su `authorityInfoAccess`."""
    valor = cert.extension(_OID_ACCESOS)
    if not valor:
        return []
    salida: list[str] = []
    try:
        # Hay que abrir la SEQUENCE de fuera: dentro van los accesos, y cada
        # uno es la pareja (para qué sirve, dónde está). Sin este paso se
        # recorrería la lista entera como si fuera un solo acceso, y entonces
        # la dirección del OCSP no aparece —que es justo lo que pasaba—.
        _, dentro, _ = _tlv(valor)
        for _, acceso in _elementos(dentro):
            partes = _elementos(acceso)
            if len(partes) == 2 and _oid(partes[0][1]) == _OID_OCSP:
                salida.extend(_uris(_reserializar(partes[1])))
    except ValueError:
        return []
    return salida


# --- El almacén ------------------------------------------------------------


@dataclass
class AlmacenDeListas:
    """Las listas de revocación puestas en una carpeta, por quién las firma.

    `carpeta` es `None` cuando no hay carpeta ninguna: en la página, donde
    quien valida no puede poner una lista. Es distinto de una carpeta vacía, y
    cambia lo que dice el aviso: con carpeta se dice dónde está la lista que
    falta, para que la baje quien quiera; sin ella, mandar a ponerla en una
    carpeta era pedir algo imposible. Visto en la página el 05-10-2026: «bájala
    y ponla en la carpeta de revocaciones», en una página que no tiene carpeta.
    """

    carpeta: Path | None
    _por_emisor: dict[bytes, list[Lista]] | None = field(default=None, repr=False)
    _ilegibles: list[tuple[Path, str]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.carpeta is not None and not isinstance(self.carpeta, Path):
            self.carpeta = Path(self.carpeta)

    @classmethod
    def por_defecto(cls, carpeta: str | Path | None = None) -> AlmacenDeListas:
        if carpeta is None:
            carpeta = os.environ.get(VARIABLE_ENTORNO) or CARPETA_POR_DEFECTO
        return cls(Path(carpeta))

    @classmethod
    def sin_carpeta(cls) -> AlmacenDeListas:
        """Ninguna lista y ningún sitio donde ponerla. Ver la clase."""
        return cls(None)

    @property
    def por_emisor(self) -> dict[bytes, list[Lista]]:
        if self._por_emisor is None:
            encontradas: dict[bytes, list[Lista]] = {}
            self._ilegibles = []
            if self.carpeta is not None and self.carpeta.is_dir():
                for ruta in sorted(self.carpeta.rglob("*")):
                    if ruta.suffix.lower() not in _EXTENSIONES or not ruta.is_file():
                        continue
                    try:
                        crudas = listas_del_fichero(ruta.read_bytes())
                    except (OSError, binascii.Error, ValueError) as error:
                        self._ilegibles.append((ruta, str(error)))
                        continue
                    if not crudas:
                        self._ilegibles.append((ruta, "no trae ninguna lista"))
                        continue
                    for cruda in crudas:
                        try:
                            lista = leer_lista(cruda)
                        except (ValueError, IndexError) as error:
                            self._ilegibles.append((ruta, str(error)))
                            continue
                        encontradas.setdefault(lista.emisor_der, []).append(lista)
            self._por_emisor = encontradas
        return self._por_emisor

    @property
    def ilegibles(self) -> list[tuple[Path, str]]:
        self.por_emisor  # fuerza el recorrido
        return self._ilegibles

    @property
    def vacio(self) -> bool:
        return not self.por_emisor

    def recargar(self) -> None:
        self._por_emisor = None
        self._ilegibles = []

    def todas(self) -> list[Lista]:
        return [una for grupo in self.por_emisor.values() for una in grupo]

    def de(self, cert: Certificado) -> list[Lista]:
        """Las listas que dicen venir de quien emitió este certificado.

        «Dicen»: que una lista lleve el nombre de la autoridad no significa que
        la haya firmado ella. Eso se comprueba en `_sirve`, con la clave.
        """
        return list(self.por_emisor.get(cert.emisor_der, ()))

    def inventario(self) -> list[str]:
        salida = []
        for lista in sorted(self.todas(), key=lambda una: una.emisor_nombre or ""):
            cuando = lista.desde.date().isoformat() if lista.desde else "?"
            caduca = lista.hasta.date().isoformat() if lista.hasta else "sin fecha"
            marca = " · INCREMENTAL" if lista.es_delta else ""
            salida.append(
                f"{lista.emisor_nombre or '(sin nombre común)'}: "
                f"{len(lista.anulaciones)} anulado(s) · del {cuando} · "
                f"vale hasta {caduca}{marca}"
            )
        return salida


# --- La comprobación --------------------------------------------------------

_PRINCIPIO = datetime.min.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class PruebaOcsp:
    """Una respuesta OCSP que se ha creído, y por qué se la ha creído.

    `quien` es quien la firmó **comprobado**, no lo que diga un campo: o la
    propia autoridad, o un respondedor al que ella delegó. Y `mirada` es el
    `thisUpdate`, el momento del que la respuesta habla. Sin esa fecha no se
    puede decir qué se ha dado por bueno: una respuesta OCSP es una foto con
    hora, no un estado permanente.
    """

    quien: str
    porque: str  # «la firma la propia autoridad», o delegada por ella
    mirada: datetime | None
    # Hasta cuándo la daba por vigente **el propio respondedor** (`nextUpdate`),
    # y cuánto se miró antes de la firma, cuando se miró antes. Las dos hacen
    # falta para poder decir sobre qué se aceptó, que es lo que distingue una
    # nota de un tic verde.
    vale_hasta: datetime | None = None
    hueco: timedelta | None = None


@dataclass(frozen=True)
class Veredicto:
    """Lo que se ha podido averiguar, y con qué prueba se ha averiguado."""

    estado: str  # "anulado", "vigente" o "sin_saber"
    lista: Lista | None = None
    anulacion: Anulacion | None = None
    motivo: str = ""  # por qué no se sabe, cuando no se sabe
    # Cuando la prueba no fue una CRL sino una respuesta OCSP de las que trae
    # el documento. Va en su propio campo y no dentro de `lista` porque no es
    # una lista, y el informe tiene que poder decir de dónde salió lo que
    # afirma: «según la lista de X» y «según la respuesta OCSP de Y» no son la
    # misma frase ni la misma prueba.
    ocsp: PruebaOcsp | None = None


def _sirve(lista: Lista, emisor: Certificado, cert: Certificado) -> str:
    """¿Se puede creer a esta lista sobre este certificado?

    Devuelve el motivo por el que no, o cadena vacía si sí. El orden importa,
    igual que en `cadena._eslabon`: primero lo que descalifica a la lista o a
    quien la firma, y solo después la criptografía.
    """
    if lista.criticas_sin_entender:
        cual = sorted(lista.criticas_sin_entender)[0]
        return (
            f"trae una extensión marcada como imprescindible que aquí no se "
            f"sabe leer ({cual}), así que no se puede saber qué dice"
        )
    if emisor.usos and "firmar_crl" not in emisor.usos:
        return (
            f"«{emisor.sujeto or 'el emisor'}» no tiene permiso para firmar "
            "listas de revocación"
        )
    if not lista.algoritmo_firma or not lista.valor_firma or not lista.tbs:
        return "no se ha podido leer con qué se firmó"
    if not verificar(lista.valor_firma, lista.tbs, emisor, lista.algoritmo_firma):
        return (
            f"no la firmó «{emisor.sujeto or 'el emisor del certificado'}», "
            "aunque diga venir de ahí"
        )
    if lista.solo_autoridades and cert.es_autoridad is not True:
        return "solo cubre certificados de autoridad, y este no lo es"
    if lista.solo_usuarios and cert.es_autoridad is True:
        return "solo cubre certificados de usuario, y este es de autoridad"
    return ""


def comprobar(
    cert: Certificado,
    emisor: Certificado,
    listas: list[Lista],
    cuando: datetime | None = None,
) -> Veredicto:
    """¿Está anulado este certificado, según las listas que tenemos?

    `cuando` es el momento que se juzga —la fecha que la firma declara—. Sirve
    para dos cosas: para saber si la lista es lo bastante nueva como para haber
    podido enterarse, y para situar la anulación antes o después de la firma.
    """
    if not listas:
        return Veredicto(
            "sin_saber", motivo="no hay ninguna lista de esa autoridad"
        )

    fallos: list[tuple[Lista, str]] = []
    utiles: list[Lista] = []
    for lista in listas:
        fallo = _sirve(lista, emisor, cert)
        if fallo:
            fallos.append((lista, fallo))
        else:
            utiles.append(lista)

    if not utiles:
        lista, fallo = fallos[0]
        return Veredicto("sin_saber", lista=lista, motivo=fallo)

    # Manda la lista más nueva, y solo ella. Recorrerlas todas buscando el
    # número de serie parece más seguro y es justo lo contrario: una suspensión
    # que se levanta desaparece de las listas siguientes, así que una lista
    # vieja resucitaría una anulación que ya no existe.
    mejor = max(utiles, key=lambda una: una.desde or _PRINCIPIO)
    anulacion = mejor.anulaciones.get(cert.serie)
    if anulacion is not None:
        return Veredicto("anulado", lista=mejor, anulacion=anulacion)

    parcial = mejor.parcial
    if parcial:
        # Una lista incremental sí puede **afirmar**: lo que no puede es negar.
        # Si la más nueva es un delta, la base sigue sirviendo para acusar.
        for otra in sorted(
            utiles, key=lambda una: una.desde or _PRINCIPIO, reverse=True
        ):
            anulacion = otra.anulaciones.get(cert.serie)
            if anulacion is not None:
                return Veredicto("anulado", lista=otra, anulacion=anulacion)
        return Veredicto("sin_saber", lista=mejor, motivo=parcial)
    if cuando is not None and mejor.desde is not None and mejor.desde < cuando:
        # Con el rato y no con las dos fechas: lo corriente es bajar la lista
        # al firmar, y entonces las dos caen el mismo día. Salía «la lista es
        # del 2026-03-02 y la firma dice ser del 2026-03-02: se publicó
        # antes», que se lee como una contradicción.
        return Veredicto(
            "sin_saber",
            lista=mejor,
            motivo=(
                f"la lista se publicó el {cifras.fecha(mejor.desde)}, "
                f"{_cuanto(cuando - mejor.desde)} antes de la fecha de la "
                "firma, así que no pudo enterarse de una anulación posterior"
            ),
        )
    return Veredicto("vigente", lista=mejor)


def comprobar_ocsp(
    cert: Certificado,
    emisor: Certificado,
    respuestas: list,
    cuando: datetime | None = None,
) -> Veredicto:
    """Lo mismo que `comprobar`, pero con las respuestas OCSP del documento.

    Las mismas tres preguntas que a una CRL y en el mismo orden: de quién
    habla, quién la firma y de cuándo es. Quien las contesta es `ocsp.py`; aquí
    solo se decide qué significa cada respuesta para el informe.

    Con una diferencia que importa: que una respuesta hable de **otro**
    certificado no es un fallo, es que no venía a cuento. Solo se verifican las
    que dicen algo de este —`casa_con` es aritmética y no hace falta creerse
    nada para saber si el CertID cuadra—, y así un documento con cuatro
    respuestas no suelta cuatro quejas por cada eslabón de la cadena.
    """
    if not respuestas:
        return Veredicto("sin_saber", motivo="el documento no trae respuestas OCSP")

    fallos: list[str] = []
    suyas: list[tuple] = []
    for respuesta in respuestas:
        propios = [uno for uno in respuesta.estados if ocsp.casa_con(uno, cert, emisor)]
        if not propios and respuesta.estados:
            continue
        vale, porque = ocsp.verificar_respuesta(respuesta, emisor)
        if not vale:
            fallos.append(porque)
            continue
        # Ya está verificada; esto es solo para poder nombrar en el informe a
        # quien la firmó, que es la mitad de lo que hace útil a una nota.
        quien, _ = ocsp.quien_la_firma(respuesta, emisor)
        nombre = (quien.sujeto if quien is not None else "") or "su autoridad"
        for uno in propios:
            suyas.append(
                (uno, PruebaOcsp(nombre, porque, uno.mirada, uno.vale_hasta))
            )

    if not suyas:
        if fallos:
            return Veredicto("sin_saber", motivo=fallos[0])
        return Veredicto(
            "sin_saber",
            motivo=(
                "ninguna de las respuestas OCSP que trae el documento habla de "
                "este certificado"
            ),
        )

    # Manda la más nueva, y por lo mismo que entre dos CRL: una suspensión que
    # se levanta desaparece de las respuestas siguientes, así que quedarse con
    # la más vieja resucitaría una anulación que ya no existe.
    estado, prueba = max(suyas, key=lambda par: par[0].mirada or _PRINCIPIO)

    if estado.anulado:
        return Veredicto(
            "anulado",
            anulacion=Anulacion(cert.serie, estado.anulado_el, motivo=estado.motivo),
            ocsp=prueba,
        )
    if estado.sin_saber:
        # «unknown» no es «good». El respondedor dice que ese certificado no le
        # consta, y eso puede ser tanto que nunca existió como que no es suyo.
        return Veredicto(
            "sin_saber",
            ocsp=prueba,
            motivo=(
                "el respondedor contestó que no sabe nada de ese certificado "
                "(«unknown»), que no es lo mismo que decir que está bien"
            ),
        )
    if cuando is not None and prueba.mirada is not None and prueba.mirada < cuando:
        # Se miró antes de firmar, que es lo normal y no lo excepcional: un
        # XAdES-XL se hace preguntando el estado, firmando y sellando, por ese
        # orden. Medido sobre las muestras, el hueco es de 27 segundos en
        # `78353__XAdES_A_Detached.xml` y de poco más de una hora en
        # `firma_cofirma_xades_longeva.xml`. Tratar eso como «no se sabe»
        # levantaría el aviso en casi toda factura archivada, y un aviso que
        # sale siempre deja de leerse.
        #
        # Quien dice si la respuesta seguía valiendo en ese momento no es este
        # validador: es el respondedor, con su `nextUpdate`. Si lo cubre, se
        # acepta y la nota dice el hueco y en qué se apoya. Si no lo dice
        # —que es su manera de pedir que no se guarde—, o si dice que ya no
        # valía, se sigue sin saber.
        prueba = replace(prueba, hueco=cuando - prueba.mirada)
        if estado.vale_hasta is None or estado.vale_hasta < cuando:
            hasta = (
                "el respondedor no dijo hasta cuándo la daba por vigente"
                if estado.vale_hasta is None
                else "el propio respondedor solo la daba por vigente hasta el "
                f"{cifras.momento(estado.vale_hasta)}"
            )
            return Veredicto(
                "sin_saber",
                ocsp=prueba,
                motivo=(
                    f"la respuesta OCSP miró el certificado {_cuanto(prueba.hueco)} "
                    f"antes de esta firma y {hasta}: no pudo enterarse de una "
                    "anulación posterior"
                ),
            )
    return Veredicto("vigente", ocsp=prueba)


def _cuanto(hueco: timedelta) -> str:
    """Un rato, en la unidad que lo hace legible.

    Existe porque el mensaje imprimía dos fechas iguales y decía que una era
    anterior a la otra: entre pedir el estado del certificado y firmar pasan
    segundos, y en días eso no se ve.
    """
    segundos = int(hueco.total_seconds())
    if segundos < 60:
        return f"{segundos} segundo{'' if segundos == 1 else 's'}"
    minutos = segundos // 60
    if minutos < 60:
        return f"{minutos} minuto{'' if minutos == 1 else 's'}"
    horas = minutos // 60
    if horas < 48:
        return f"{horas} hora{'' if horas == 1 else 's'}"
    dias = horas // 24
    return f"{dias} día{'' if dias == 1 else 's'}"


def _cuando_mira(veredicto: Veredicto) -> datetime:
    """De qué momento habla la prueba con la que se contestó."""
    if veredicto.ocsp is not None and veredicto.ocsp.mirada is not None:
        return veredicto.ocsp.mirada
    if veredicto.lista is not None and veredicto.lista.desde is not None:
        return veredicto.lista.desde
    return _PRINCIPIO


def _juntar(por_lista: Veredicto, por_ocsp: Veredicto | None) -> Veredicto:
    """Dos pruebas para la misma pregunta, y qué se hace si no coinciden.

    Manda **la más nueva de las que contestan**, que es exactamente la regla
    que `comprobar` ya aplica entre dos CRL de la misma autoridad, y por el
    mismo motivo: una suspensión levantada desaparece de la prueba siguiente,
    así que quedarse con la vieja resucitaría una anulación que ya no existe.
    Contestar es decir «anulado» o «vigente»; «no lo sé» no compite.

    Y si ninguna sabe, se queda el motivo del OCSP. No es capricho: si el
    documento traía respuestas, lo que hay que contar es por qué no han
    servido. Que además falte la CRL sigue en el aviso, con la dirección donde
    bajarla.
    """
    if por_ocsp is None:
        return por_lista
    contestan = [uno for uno in (por_lista, por_ocsp) if uno.estado != "sin_saber"]
    if not contestan:
        return por_ocsp
    return max(contestan, key=_cuando_mira)


# --- Lo que trae el propio documento ---------------------------------------


def listas_del_documento(firma) -> list[Lista]:
    """Las CRL que la firma lleva dentro, si es XAdES-XL.

    Es la mejor fuente que hay: no sale de aquí, y es la única que sigue
    funcionando dentro de veinte años, cuando la lista de aquel día ya no esté
    publicada en ninguna parte. Que la traiga el firmante no la hace de fiar
    por sí sola —se le comprueba la firma igual que a cualquier otra—, y por
    eso se puede aceptar sin más ceremonia.
    """
    salida = []
    for texto in firma.xpath(".//*[local-name()='EncapsulatedCRLValue']/text()"):
        try:
            salida.append(leer_lista(base64.b64decode("".join(texto.split()))))
        except (ValueError, IndexError, binascii.Error):
            continue
    return salida


# --- Las reglas ------------------------------------------------------------


def _quien(cert: Certificado, primero: bool) -> str:
    if primero:
        return "El certificado que firma"
    return f"«{cert.sujeto or 'un certificado de la cadena'}», que está por encima"


def _donde_buscarla(cert: Certificado, con_carpeta: bool) -> str:
    """La frase que dice qué hacer, que es la parte accionable del aviso.

    Solo donde hay una carpeta en la que ponerla. Sin carpeta no hay nada que
    hacer con la dirección, y decirla invitaba a bajar algo que la página no
    tiene dónde usar.
    """
    listas = donde_esta_la_lista(cert) if con_carpeta else []
    if listas:
        return (
            f" El propio certificado dice que su lista está en {listas[0]}; "
            "bájala y ponla en la carpeta de revocaciones."
        )
    return ""


def _anulado(
    cert: Certificado,
    veredicto: Veredicto,
    cuando: datetime | None,
    primero: bool,
    donde: str,
    sello=None,
) -> Incidencia:
    anulacion = veredicto.anulacion
    quien = _quien(cert, primero)
    fecha = cifras.fecha(anulacion.cuando) if anulacion.cuando else "una fecha que no se lee"
    if veredicto.ocsp is not None:
        miro = (
            cifras.fecha(veredicto.ocsp.mirada)
            if veredicto.ocsp.mirada
            else "una fecha que no se lee"
        )
        segun = (
            f"según la respuesta OCSP de «{veredicto.ocsp.quien}» que trae el "
            f"propio documento, del {miro}"
        )
    else:
        nombre = veredicto.lista.emisor_nombre if veredicto.lista else ""
        segun = f"según la lista de «{nombre or 'su autoridad'}»"
    encontrado = f"anulado el {fecha} {anulacion.texto_motivo}, {segun}"

    if anulacion.compromiso:
        desde = ""
        if anulacion.invalida_desde:
            desde = (
                f" La lista sitúa el compromiso el "
                f"{cifras.fecha(anulacion.invalida_desde)}."
            )
        return Incidencia(
            "REVOCACION-COMPROMISO",
            ERROR,
            f"{quien} está anulado {anulacion.texto_motivo}. Cuando una clave "
            "acaba en malas manos, todo lo que firmó pasa a ser sospechoso, "
            "también lo firmado antes de la denuncia: quien la robó pudo poner "
            f"la fecha que quisiera.{desde}",
            campo=f"{donde}Revocación",
            esperado="un certificado no anulado",
            encontrado=encontrado,
        )

    if anulacion.suspension:
        return Incidencia(
            "REVOCACION-SUSPENDIDO",
            AVISO,
            f"{quien} está en suspenso desde el {fecha}. Una suspensión no es "
            "definitiva: puede levantarse, y entonces el certificado vuelve a "
            "valer. Hoy no vale, y esta lista no dice desde cuándo empezó a no "
            "valer.",
            campo=f"{donde}Revocación",
            esperado="un certificado no anulado",
            encontrado=encontrado,
        )

    if cuando is None or (anulacion.cuando and anulacion.cuando <= cuando):
        segun = (
            f"cuando el sello de tiempo de «{sello.quien}» acredita que ya "
            "existía esta firma"
            if sello is not None
            else "el día que la factura dice haberse firmado"
        )
        return Incidencia(
            "REVOCADO",
            ERROR,
            f"{quien} estaba ya anulado {segun}. Una firma hecha con un "
            "certificado anulado no vale, aunque la aritmética de la firma "
            "cuadre.",
            campo=f"{donde}Revocación",
            esperado="un certificado no anulado",
            encontrado=encontrado,
        )

    # Aquí la anulación es posterior a la firma, y de dónde salga la fecha
    # cambia el veredicto, no solo la redacción. Con la fecha del firmante esto
    # es un aviso —puede haberla escrito él—; con un sello de tiempo es un
    # hecho acreditado por un tercero, y entonces lo que hay que decir no es
    # «cuidado» sino **qué se ha dado por bueno y con qué**, que es una nota.
    if sello is not None:
        return Incidencia(
            "REVOCACION-POSTERIOR",
            NOTA,
            f"{quien} se anuló el {fecha}, después del "
            f"{cifras.fecha(cuando)} en que el sello de tiempo de "
            f"«{sello.quien}» acredita que esta firma ya existía. La factura "
            "se firmó cuando el certificado aún valía, y eso no depende de lo "
            "que declare quien firma.",
            campo=f"{donde}Revocación",
            encontrado=encontrado,
        )

    return Incidencia(
        "REVOCACION-POSTERIOR",
        AVISO,
        f"{quien} se anuló el {fecha}, después del "
        f"{cifras.fecha(cuando)} que declara la firma. Si esa fecha es "
        "cierta, la factura se firmó cuando el certificado aún valía. Pero esa "
        "fecha la escribe quien firma: sin un sello de tiempo de un tercero no "
        "hay forma de comprobarla, y este documento no lo trae.",
        campo=f"{donde}Revocación",
        esperado="un certificado no anulado",
        encontrado=encontrado,
    )


def reglas(
    eslabones: list[Certificado],
    listas_puestas: list[Lista],
    listas_dentro: list[Lista] | None = None,
    cuando: datetime | None = None,
    hoy=None,
    donde: str = "",
    respuestas_ocsp: list | None = None,
    sello=None,
    con_carpeta: bool = True,
) -> list[Incidencia]:
    """¿Anularon alguno de los certificados de esta cadena?

    `eslabones` viene de `cadena.construir`: el primero es el que firma y el
    último es el ancla. Se mira cada pareja (hijo, padre), porque para creerle
    una prueba a alguien hace falta la clave de quien la firma, y esa es la del
    padre. **El ancla no se mira**: por encima no hay nadie que pueda firmar
    una lista que la anule, y en el almacén está porque quien lo mantiene la
    puso; sacarla de ahí es la forma de dejar de creerla.

    Hay dos fuentes y valen las dos: las listas —las instaladas y las que trae
    el documento— y las respuestas OCSP que trae el documento. Se consultan las
    dos siempre, se contrastan en `_juntar`, y lo que decide se dice en el
    informe con su nombre.

    `con_carpeta` dice si quien valida puede poner listas en una carpeta. En la
    página no puede, y el aviso no le manda a hacerlo. Ver `AlmacenDeListas`.
    """
    if len(eslabones) < 2:
        return []
    dentro = listas_dentro or []
    respuestas = respuestas_ocsp or []
    incidencias: list[Incidencia] = []
    ya_dicho = False
    # Contra qué se ha contrastado, para poder declararlo al final. Un «no
    # consta anulado» sin decir según qué lista y de qué día no es una
    # respuesta: es un tic verde con más letras.
    limpios = 0
    firmante_limpio = False
    usadas: list[Lista] = []
    usados: list[PruebaOcsp] = []

    for numero, (hijo, padre) in enumerate(zip(eslabones, eslabones[1:])):
        primero = numero == 0
        candidatas = [una for una in dentro + listas_puestas if una.emisor_der == hijo.emisor_der]
        por_lista = comprobar(hijo, padre, candidatas, cuando)
        por_ocsp = comprobar_ocsp(hijo, padre, respuestas, cuando) if respuestas else None
        veredicto = _juntar(por_lista, por_ocsp)

        if veredicto.estado == "anulado":
            incidencias.append(
                _anulado(hijo, veredicto, cuando, primero, donde, sello)
            )
            continue

        if veredicto.estado == "vigente":
            lista = veredicto.lista
            limpios += 1
            firmante_limpio = firmante_limpio or primero
            if lista is not None and not any(o is lista for o in usadas):
                usadas.append(lista)
            prueba = veredicto.ocsp
            if prueba is not None and not any(
                o.quien == prueba.quien and o.mirada == prueba.mirada for o in usados
            ):
                usados.append(prueba)
            # Aquí no hay equivalente de REVOCACION-LISTA-VIEJA, y es a
            # propósito: una respuesta OCSP que llega hasta aquí ya ha tenido
            # que ser posterior a la firma, y lo que prueba de aquel momento no
            # caduca. Que su `nextUpdate` pasara hace años es lo normal en un
            # documento archivado, y decirlo en cada factura vieja sería ruido.
            #
            # **Y lo mismo una lista que traiga el documento dentro**, por la
            # misma razón: si sirvió para contestar, es que se publicó después
            # de la firma, y lo que dice de aquel momento no caduca. Medido el
            # 05-10-2026 pasando la fecha de hoy: toda factura archivada con su
            # lista dentro salía con «la lista venció el …» al lado del «no
            # consta anulado». La fecha de hoy se aplica a las listas de la
            # carpeta, que son las que alguien bajó un día y pueden quedarse
            # viejas sin que nadie lo note.
            de_fuera = lista is not None and not any(lista is una for una in dentro)
            if de_fuera and lista.hasta and hoy is not None and lista.hasta.date() < hoy:
                incidencias.append(
                    Incidencia(
                        "REVOCACION-LISTA-VIEJA",
                        AVISO,
                        f"{_quien(hijo, primero)} no aparece anulado, pero la "
                        f"lista que lo dice venció el "
                        f"{cifras.fecha(lista.hasta)} y desde entonces "
                        "puede haber anulaciones que no recoge. No aparecer en "
                        "una lista caducada no es lo mismo que estar vigente.",
                        campo=f"{donde}Revocación",
                        esperado="una lista dentro de su plazo",
                        encontrado=f"lista de «{lista.emisor_nombre or '?'}» "
                        f"vencida el {cifras.fecha(lista.hasta)}",
                    )
                )
            continue

        # No se sabe. Se dice una sola vez —la del certificado que firma—,
        # porque en un lote de doscientas facturas el mismo aviso repetido por
        # cada eslabón y por cada fichero deja de leerse.
        if ya_dicho or not primero:
            continue
        ya_dicho = True
        incidencias.append(
            _no_se_sabe(hijo, veredicto, donde, respuestas, con_carpeta)
        )

    if limpios:
        incidencias.append(
            _nota_de_limpieza(limpios, usadas, usados, donde, firmante_limpio)
        )
    return incidencias


def _nota_de_limpieza(
    cuantos: int,
    usadas: list[Lista],
    usados: list[PruebaOcsp],
    donde: str,
    con_el_firmante: bool = True,
) -> Incidencia:
    """Declarar contra qué se ha contrastado, cuando no consta anulado.

    Una sola nota por firma y no una por eslabón: en un lote de doscientas
    facturas, la misma línea repetida por cada certificado de cada cadena deja
    de leerse, y lo que hay que poder leer es de qué día es la prueba.

    Y **qué clase de prueba fue**. Una CRL y una respuesta OCSP no dicen lo
    mismo: la lista responde por lo que su autoridad sabía el día que la
    publicó, y la respuesta por el estado de un certificado concreto en la hora
    en que se miró. Meter las dos en la misma frase escondería justo el dato
    que hace falta para juzgar el «no consta anulado».

    `con_el_firmante` dice si entre los comprobados está el que firma. Con una
    lista de la raíz y ninguna de la autoridad que emitió el certificado, la
    nota decía «no consta anulado ningún certificado de la cadena» al lado del
    aviso de que el que firma no se había comprobado: prometía justo el que
    falta. Medido el 05-10-2026.
    """
    de_cuales = (
        "ningún certificado de la cadena"
        if con_el_firmante
        else "ninguno de los certificados que están por encima del que firma"
    )
    detalles = []
    for lista in usadas:
        cuando = cifras.fecha(lista.desde) if lista.desde else "fecha ilegible"
        quien = lista.emisor_nombre or "una autoridad sin nombre común"
        detalles.append(f"«{quien}», publicada el {cuando}")
    contados = (
        "se ha comprobado 1 certificado"
        if cuantos == 1
        else f"se han comprobado {cuantos} certificados"
    )
    if not usados:
        cuales = "; ".join(detalles) or "las listas disponibles"
        return Incidencia(
            "CONFIANZA-REVOCACION",
            NOTA,
            f"No consta anulado {de_cuales}: {contados} "
            f"contra la lista de {cuales}. Una lista solo responde por lo que se "
            "sabía el día que se publicó.",
            campo=f"{donde}Revocación",
        )
    pruebas = [f"la lista de {uno}" for uno in detalles]
    for prueba in usados:
        # Con hora, y no solo el día: entre mirar el estado y firmar pasan
        # segundos, y en días ese hueco no se ve.
        cuando = (
            cifras.momento(prueba.mirada)
            if prueba.mirada
            else "fecha ilegible"
        )
        detalle = (
            f"la respuesta OCSP de «{prueba.quien}» que trae el propio "
            f"documento, del {cuando}"
        )
        if prueba.hueco is not None:
            # Se miró antes de firmar. Se aceptó, y hay que decir sobre qué:
            # sobre la palabra del respondedor, no sobre la nuestra.
            detalle += (
                f" (mirada {_cuanto(prueba.hueco)} antes de la firma, y el "
                f"propio respondedor la daba por vigente hasta el "
                f"{cifras.momento(prueba.vale_hasta)})"
            )
        pruebas.append(detalle)
    return Incidencia(
        "CONFIANZA-REVOCACION",
        NOTA,
        f"No consta anulado {de_cuales}: {contados} "
        f"contra {'; '.join(pruebas)}. Una respuesta OCSP dice cómo estaba el "
        "certificado el día y la hora en que se miró, no cómo está hoy.",
        campo=f"{donde}Revocación",
    )


def _no_se_sabe(
    cert: Certificado,
    veredicto: Veredicto,
    donde: str,
    respuestas: list,
    con_carpeta: bool = True,
) -> Incidencia:
    """El aviso de que no se sabe, con lo que de verdad ha pasado.

    Sin carpeta, la única prueba que puede valer es la que trae el documento,
    así que el aviso dice qué traía y por qué no ha servido, y no manda a
    ninguna parte. Son tres casos, y cada uno lleva ya su motivo: que no
    traía la lista de esa autoridad ni una respuesta OCSP, que la traía pero
    es anterior a la firma, o que el respondedor contestó «unknown».
    """
    servicio = donde_esta_el_ocsp(cert)
    motivo = veredicto.motivo
    if not con_carpeta and veredicto.lista is None and not respuestas:
        # «No hay ninguna lista de esa autoridad» es cierto en consola, donde
        # puede haberla en la carpeta. Aquí solo puede venir dentro, y
        # decirlo así es lo que deja entender que no hay nada que hacer.
        motivo = (
            "el documento no trae dentro la lista de revocación de la "
            "autoridad que emitió el certificado, ni una respuesta OCSP, y "
            "aquí no se sale a buscarlas"
        )
    if respuestas:
        # El documento traía respuestas y ninguna ha servido. Salir con «no
        # tenemos ninguna lista de esa autoridad» sería falso por omisión: sí
        # traía una prueba, y lo que hay que contar es por qué no vale.
        cual = (
            "una respuesta OCSP"
            if len(respuestas) == 1
            else f"{len(respuestas)} respuestas OCSP"
        )
        con_ella = "ella" if len(respuestas) == 1 else "ellas"
        return Incidencia(
            "REVOCACION-OCSP-NO-VALE",
            AVISO,
            f"El documento trae dentro {cual}, y con {con_ella} no se ha podido "
            f"comprobar si el certificado estaba anulado: "
            f"{motivo}.{_donde_buscarla(cert, con_carpeta)}",
            campo=f"{donde}Revocación",
            esperado="una respuesta OCSP verificable, o una lista de revocación (CRL)",
            encontrado=veredicto.motivo,
        )
    if not donde_esta_la_lista(cert) and servicio:
        return Incidencia(
            "REVOCACION-SOLO-OCSP",
            AVISO,
            "No se ha comprobado si el certificado está anulado: su autoridad "
            "no publica lista de revocación, solo un servicio de consulta "
            f"({servicio[0]}). Preguntarle lleva dentro el número de serie del "
            "certificado, o sea que le diría a la autoridad qué factura se "
            "está mirando y cuándo. Esa consulta no se hace desde aquí: quien "
            "quiera hacerla, que la haga sabiendo lo que cuenta.",
            campo=f"{donde}Revocación",
            esperado="una lista de revocación (CRL)"
            if con_carpeta
            else "una respuesta OCSP dentro del documento, posterior a la firma",
            encontrado="la autoridad solo ofrece OCSP",
        )
    return Incidencia(
        "REVOCACION-SIN-COMPROBAR",
        AVISO,
        f"No se ha comprobado si el certificado está anulado: "
        f"{motivo}.{_donde_buscarla(cert, con_carpeta)}",
        campo=f"{donde}Revocación",
        esperado="una lista de revocación de esa autoridad"
        if con_carpeta
        else "la lista de esa autoridad, o una respuesta OCSP, dentro del "
        "documento y posterior a la firma",
        encontrado=motivo,
    )
