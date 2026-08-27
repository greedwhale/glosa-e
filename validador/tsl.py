"""De dónde salen las anclas: la lista de confianza (TSL).

`cadena.py` sabe encadenar un certificado hasta un ancla. Lo que no contesta es
**de dónde salen las anclas**, y de eso depende que todo lo demás signifique
algo: un almacén mal montado no da un error, da un aprobado. Es el único sitio
de este validador donde equivocarse es silencioso.

Hasta aquí la respuesta era «las pone quien valida, y nosotros enseñamos la
huella». Eso vale para quien tiene una autoridad y sabe cuál. No vale para
recibir facturas de cualquiera: harían falta las de todas las autoridades
cualificadas de España, y nadie va a recopilarlas a mano.

Recopilarlas a mano tampoco sería lo correcto, que es lo importante. Un montón
de raíces bajadas de por ahí es exactamente el problema que este módulo existe
para no tener: **quien elige el montón elige a quién cree el validador**. La
respuesta correcta ya existe y es pública.

La lista de confianza
---------------------
El artículo 22 del reglamento eIDAS obliga a cada Estado miembro a publicar,
firmada y en un formato procesable, la lista de sus prestadores cualificados:
quién es autoridad de certificación cualificada, desde cuándo, y con qué
certificado. El formato es ETSI TS 119 612 y es lo que aquí se llama TSL.

O sea que la pregunta «¿en quién hay que confiar?» tiene respuesta oficial,
publicada, firmada y con fecha. No hay que inventar el conjunto: hay que leerlo.

La cadena de la cadena, y dónde acaba
-------------------------------------
Una lista de confianza bajada de una dirección no vale nada por sí sola: si no
compruebas quién la firmó, has aceptado la lista de en quién confiar de manos
de quien contestara al DNS. Así que la lista hay que verificarla, y contra algo
que ya sepas. Ese algo es otra lista:

1. El **Diario Oficial de la Unión Europea** publica dónde está la lista de
   listas (LOTL) y los certificados que pueden firmarla. En papel, con número
   de expediente. Ahí acaba la cadena, y acaba fuera de internet.
2. La **LOTL** dice, para cada país, dónde está su lista y qué certificados
   pueden firmarla.
3. La **lista del país** dice qué autoridades son cualificadas.

Por eso `montar` **se niega** a producir anclas de una lista cuya firma no ha
comprobado. No avisa: se niega. La salida de esta función es la raíz de
confianza de todo lo demás, y un aviso en un informe que nadie lee no es una
defensa.

Se dice cómo, y no de memoria
-----------------------------
Las dos direcciones que hacen falta están verificadas contra la fuente y no
escritas de cabeza —la del ministerio había cambiado desde la que yo recordaba,
que es justo por lo que no se escriben de memoria—. Están en el README, no
aquí: una dirección en el código parece un dato de confianza y no lo es.

Esto tampoco abre una conexión
------------------------------
Igual que con las listas de revocación: bajar el fichero es cosa de quien usa
la herramienta. Aquí se lee de disco. Se puede comprobar con un `grep`: en todo
el paquete no hay ni un `urlopen`, ni un `requests`, ni un `socket`.

Lo que este módulo **no** resuelve
----------------------------------
Que una autoridad esté cualificada **hoy** no dice que lo estuviera cuando se
firmó la factura, ni al revés. La lista lleva la fecha de cada cambio de estado
—`StatusStartingTime`— y aquí se lee y se cuenta, pero el conjunto que se monta
es el de las que están concedidas hoy. Una autoridad retirada el año pasado
firmó facturas buenas hace dos, y con este conjunto esas facturas salen como
«no llega a ninguna autoridad conocida»: un aviso, no un error, y el mensaje ya
dice que no se distingue de la otra posibilidad. Está anotado en el manifiesto
y sale en `--ver-tsl`. Cerrarlo del todo es dar al almacén una ventana de
validez por ancla, que es otro trabajo.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

from validador import firma
from validador.cadena import NOMBRE_DEL_MANIFIESTO
from validador.firma import Certificado, leer_certificado
from validador.formato import parser

__all__ = [
    "Lista",
    "Puntero",
    "Servicio",
    "leer",
    "comprobar_firma",
    "anclas_de",
    "montar",
    "NOMBRE_DEL_MANIFIESTO",
]

# Los tipos de servicio de ETSI TS 119 612 que emiten certificados de los que
# pueden acabar dentro de una factura. Los demás —sellos de tiempo, servicios
# de estado, entrega electrónica— están en la misma lista y no son anclas para
# esto; meterlos sería ampliar la confianza sin motivo.
CA_CUALIFICADA = "http://uri.etsi.org/TrstSvc/Svctype/CA/QC"
RAIZ_NACIONAL = "http://uri.etsi.org/TrstSvc/Svctype/NationalRootCA-QC"
TIPOS_QUE_EMITEN = (CA_CUALIFICADA, RAIZ_NACIONAL)

# El estado que cuenta. Los demás —`withdrawn`, y los antiguos de antes de
# eIDAS que siguen apareciendo en el historial— significan que esa autoridad
# ya no es cualificada.
CONCEDIDO = "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/granted"


def _limpio(texto: str) -> str:
    """El texto de una etiqueta, sin los saltos de línea con que viene sangrado.

    Un espacio, no ninguno. Esto decía `"".join(texto.split())`, que es lo que
    hace falta para el base64 de un certificado y es destructivo para un
    nombre: la lista española habría acabado diciendo «FABRICANACIONALDEMONEDA
    YTIMBRE» en el informe de cada factura. No sale con datos inventados de una
    sola palabra; sale en cuanto el nombre lleva un espacio, que es siempre.
    """
    return " ".join(texto.split())


def _texto(nodo, nombre: str) -> str:
    """El texto de un descendiente por nombre local, mire donde mire.

    Sin mirar el espacio de nombres a propósito: las listas en circulación no
    comparten el mismo —hay ficheros con el de la v1 y ficheros con el de la
    v2— y encadenar por el prefijo declarado sería atarse a una versión del
    formato.

    Esto vale para los nombres, que van envueltos en un `Name` con idioma. Para
    todo lo demás está `_de_dentro`, y la diferencia importa: ver allí.
    """
    if nodo is None:
        return ""
    encontrados = nodo.xpath(f".//*[local-name()='{nombre}']/text()")
    return _limpio(encontrados[0]) if encontrados else ""


def _de_dentro(nodo, nombre: str) -> str:
    """El texto de un hijo **directo**, no de cualquier descendiente.

    Que sea directo no es tiquismiquis. En una lista de listas, los punteros a
    los demás países cuelgan de la misma `SchemeInformation` que la cabecera, y
    cada puntero repite etiquetas que también son de la cabecera —`TSLType`,
    `SchemeTerritory`—. Buscando por descendiente, una lista de listas acabaría
    diciendo que es la de otro país en cuanto alguien reordenara el fichero.
    """
    if nodo is None:
        return ""
    encontrados = nodo.xpath(f"./*[local-name()='{nombre}']/text()")
    return _limpio(encontrados[0]) if encontrados else ""


def _fecha(texto: str) -> datetime | None:
    if not texto:
        return None
    try:
        cuando = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError:
        return None
    return cuando if cuando.tzinfo else cuando.replace(tzinfo=timezone.utc)


def _certificados(nodo) -> tuple[list[Certificado], int]:
    """Los certificados de un `ServiceDigitalIdentity`, y cuántos no lo son.

    Un servicio se puede identificar sin certificado —solo por el nombre del
    sujeto, o por la huella de su clave—. Eso no da un ancla, y saltárselo en
    silencio dejaría el conjunto corto sin que nadie se enterara: por eso se
    devuelve la cuenta y se acaba diciendo en el manifiesto.
    """
    salida: list[Certificado] = []
    sin_certificado = 0
    for identidad in nodo.xpath(".//*[local-name()='DigitalId']"):
        crudo = identidad.xpath("./*[local-name()='X509Certificate']/text()")
        if not crudo:
            sin_certificado += 1
            continue
        try:
            salida.append(leer_certificado(base64.b64decode("".join(crudo[0].split()))))
        except (ValueError, IndexError, binascii.Error):
            sin_certificado += 1
    return salida, sin_certificado


@dataclass(frozen=True)
class Servicio:
    """Un servicio de la lista: qué es, de quién, en qué estado y desde cuándo.

    Lo importante es que **un servicio no es un ancla**. Es un ancla con un
    estado y una fecha, y quien se quede solo con el certificado está montando
    un conjunto que incluye a las autoridades retiradas.
    """

    prestador: str
    nombre: str
    tipo: str
    estado: str
    desde: datetime | None
    certificados: tuple[Certificado, ...] = ()
    sin_certificado: int = 0

    @property
    def emite_cualificados(self) -> bool:
        return self.tipo in TIPOS_QUE_EMITEN

    @property
    def concedido(self) -> bool:
        return self.estado == CONCEDIDO

    @property
    def estado_corto(self) -> str:
        return self.estado.rsplit("/", 1)[-1] if self.estado else "(sin estado)"

    @property
    def tipo_corto(self) -> str:
        return self.tipo.rsplit("/Svctype/", 1)[-1] if self.tipo else "(sin tipo)"


@dataclass(frozen=True)
class Puntero:
    """Una entrada de la lista de listas: dónde está la de un país y quién la firma."""

    territorio: str
    donde: str
    tipo: str
    firmantes: tuple[Certificado, ...] = ()


@dataclass
class Lista:
    """Una lista de confianza leída. Todavía sin creer: ver `comprobar_firma`."""

    territorio: str
    operador: str
    tipo: str
    secuencia: str
    emitida: datetime | None
    siguiente: datetime | None
    servicios: tuple[Servicio, ...] = ()
    punteros: tuple[Puntero, ...] = ()
    # El árbol y el nodo de la firma se guardan para poder comprobarla después.
    # No se comprueba al leer a propósito: para comprobarla hace falta saber
    # quién debería haberla firmado, y eso no lo sabe esta función.
    _arbol: object = field(default=None, repr=False)
    _firma: object = field(default=None, repr=False)
    firmante: Certificado | None = None
    verificada: bool = False

    @property
    def es_lista_de_listas(self) -> bool:
        return bool(self.punteros)

    def vencida(self, hoy: datetime | None = None) -> bool:
        """¿Ha pasado ya la fecha en la que prometía volver a publicarse?

        Una lista vencida no es falsa —lo que dice, dicho está— pero deja de
        responder por lo que haya cambiado desde entonces, que es el mismo
        razonamiento que con una lista de revocación caducada.
        """
        if self.siguiente is None:
            return False
        return self.siguiente < (hoy or datetime.now(timezone.utc))

    def puntero_de(self, territorio: str) -> Puntero | None:
        for uno in self.punteros:
            if uno.territorio.upper() == territorio.upper():
                return uno
        return None


def leer(datos: bytes) -> Lista:
    """Abre una lista de confianza. No la cree: solo la lee."""
    raiz = etree.fromstring(datos, parser=parser())
    informacion = raiz.xpath("./*[local-name()='SchemeInformation']")
    cabecera = informacion[0] if informacion else raiz

    siguiente = cabecera.xpath("./*[local-name()='NextUpdate']")
    servicios: list[Servicio] = []
    for prestador in raiz.xpath(".//*[local-name()='TrustServiceProvider']"):
        quien = _texto(
            prestador.xpath("./*[local-name()='TSPInformation']")[0]
            if prestador.xpath("./*[local-name()='TSPInformation']")
            else None,
            "Name",
        )
        for servicio in prestador.xpath(".//*[local-name()='TSPService']"):
            actual = servicio.xpath("./*[local-name()='ServiceInformation']")
            if not actual:
                continue
            actual = actual[0]
            identidad = actual.xpath("./*[local-name()='ServiceDigitalIdentity']")
            certificados, sueltos = (
                _certificados(identidad[0]) if identidad else ([], 0)
            )
            servicios.append(
                Servicio(
                    prestador=quien,
                    nombre=_texto(
                        actual.xpath("./*[local-name()='ServiceName']")[0]
                        if actual.xpath("./*[local-name()='ServiceName']")
                        else None,
                        "Name",
                    ),
                    tipo=_de_dentro(actual, "ServiceTypeIdentifier"),
                    estado=_de_dentro(actual, "ServiceStatus"),
                    desde=_fecha(_de_dentro(actual, "StatusStartingTime")),
                    certificados=tuple(certificados),
                    sin_certificado=sueltos,
                )
            )

    punteros: list[Puntero] = []
    for puntero in raiz.xpath(".//*[local-name()='OtherTSLPointer']"):
        # El territorio va dentro de `AdditionalInformation`, no como atributo.
        territorio = ""
        for otro in puntero.xpath(".//*[local-name()='SchemeTerritory']/text()"):
            territorio = otro.strip()
            break
        identidades = puntero.xpath(
            "./*[local-name()='ServiceDigitalIdentities']"
        )
        firmantes, _ = _certificados(identidades[0]) if identidades else ([], 0)
        punteros.append(
            Puntero(
                territorio=territorio,
                donde=_de_dentro(puntero, "TSLLocation"),
                tipo=next(
                    iter(puntero.xpath(".//*[local-name()='TSLType']/text()")), ""
                ),
                firmantes=tuple(firmantes),
            )
        )

    firmas = firma.hay_firma(raiz)
    return Lista(
        territorio=_de_dentro(cabecera, "SchemeTerritory"),
        operador=_texto(
            cabecera.xpath("./*[local-name()='SchemeOperatorName']")[0]
            if cabecera.xpath("./*[local-name()='SchemeOperatorName']")
            else None,
            "Name",
        ),
        tipo=_de_dentro(cabecera, "TSLType"),
        secuencia=_de_dentro(cabecera, "TSLSequenceNumber"),
        emitida=_fecha(_de_dentro(cabecera, "ListIssueDateTime")),
        siguiente=_fecha(_de_dentro(siguiente[0], "dateTime")) if siguiente else None,
        servicios=tuple(servicios),
        punteros=tuple(punteros),
        _arbol=raiz,
        _firma=firmas[0] if firmas else None,
    )


# --- Creerla, que es lo otro -----------------------------------------------


def _huella_normal(texto: str) -> str:
    """Una huella escrita a mano, comparable: sin separadores y en mayúsculas."""
    return re.sub(r"[^0-9A-Fa-f]", "", texto).upper()


def comprobar_firma(lista: Lista, esperados) -> str:
    """¿La firmó quien tenía que firmarla? Devuelve el motivo, o «» si sí.

    `esperados` son certificados o huellas SHA-256. Que no pueda ir vacío es
    la mitad del asunto: verificar la firma contra el certificado que la propia
    lista trae dentro no demuestra nada —cualquiera firma su propia lista con
    su propio certificado y la mete en el `KeyInfo`—. Hace falta saber de
    antemano quién es, y eso viene del Diario Oficial o de la lista de listas.

    Marca `lista.verificada` cuando sale bien, que es lo que mira `montar`.
    """
    if not esperados:
        return "no se ha dicho quién tenía que firmarla"
    if lista._firma is None:
        return "la lista no viene firmada"

    certificados = firma.certificados_de(lista._firma)
    if not certificados:
        return "la firma no trae ningún certificado"
    cert = certificados[0]

    huellas = set()
    for uno in esperados:
        if isinstance(uno, Certificado):
            huellas.add(_huella_normal(uno.huella()))
        else:
            huellas.add(_huella_normal(str(uno)))
    if _huella_normal(cert.huella()) not in huellas:
        return (
            f"la firma la hizo «{cert.sujeto or 'un certificado sin nombre'}», "
            f"con huella SHA-256 {cert.huella()}, que no es ninguno de los "
            f"{len(huellas)} autorizados"
        )

    # A partir de aquí ya sabemos de quién es el certificado. Falta lo otro:
    # que la firma sea suya de verdad y que cubra lo que estamos leyendo.
    referencias = lista._firma.xpath(".//*[local-name()='Reference']")
    if not referencias:
        return "la firma no cubre nada: no tiene ni una referencia"
    cubre_el_documento = False
    for referencia in referencias:
        metodo = referencia.xpath("./*[local-name()='DigestMethod']/@Algorithm")
        alg = firma._RESUMEN.get(metodo[0] if metodo else "")
        declarado = firma._hijo(referencia, "DigestValue")
        if alg is None or declarado is None or declarado.text is None:
            return "la firma usa un resumen que no conocemos"
        octetos, motivo = firma._contenido_referenciado(
            lista._arbol, lista._firma, referencia
        )
        if octetos is None:
            return f"no se ha podido comprobar lo que cubre la firma: {motivo}"
        calculado = base64.b64encode(hashlib.new(alg, octetos).digest()).decode()
        if calculado != "".join(declarado.text.split()):
            return "la lista se ha modificado después de firmarla"
        if referencia.get("URI") == "":
            cubre_el_documento = True

    if not cubre_el_documento:
        # Una firma que verifica pero solo cubre sus propias propiedades es una
        # firma auténtica sobre nada. Sin esto, bastaría con quedarse la firma
        # de una lista buena y colgarla de otra inventada.
        return "la firma no cubre la lista entera, solo trozos sueltos"

    firmado = firma._hijo(lista._firma, "SignedInfo")
    metodo = firmado.xpath("./*[local-name()='SignatureMethod']/@Algorithm")
    pareja = firma._FIRMA.get(metodo[0] if metodo else "")
    valor = firma._texto_b64(firma._hijo(lista._firma, "SignatureValue"))
    if pareja is None or valor is None:
        return "la firma usa un algoritmo que no sabemos comprobar"
    declarada = firmado.xpath("./*[local-name()='CanonicalizationMethod']/@Algorithm")
    octetos = firma._canonicalizar(firmado, declarada[0] if declarada else None)
    if octetos is None:
        return "la firma canonicaliza de una forma que no sabemos reproducir"
    if not firma._verificar_rsa(valor, octetos, cert, pareja[0]):
        return "la firma no cuadra con el certificado que la lista enseña"

    lista.firmante = cert
    lista.verificada = True
    return ""


# --- El conjunto -----------------------------------------------------------


@dataclass(frozen=True)
class Resumen:
    """Qué salió de montar el conjunto, para poder contarlo sin adivinar."""

    escritas: int
    servicios_mirados: int
    concedidos: int
    retirados: int
    sin_certificado: int
    repetidos: int
    carpeta: Path | None = None


def anclas_de(lista: Lista, tipos=TIPOS_QUE_EMITEN) -> list[tuple[Certificado, Servicio]]:
    """Los certificados que sirven de ancla, con el servicio del que salen.

    Solo los concedidos, y sin repetir: una autoridad que emite certificados
    de firma y de sello aparece en dos servicios con el mismo certificado, y
    sin quitar los repetidos el mismo fichero se escribiría dos veces.
    """
    salida: list[tuple[Certificado, Servicio]] = []
    vistos: set[bytes] = set()
    for servicio in lista.servicios:
        if servicio.tipo not in tipos or not servicio.concedido:
            continue
        for cert in servicio.certificados:
            if cert.der in vistos:
                continue
            vistos.add(cert.der)
            salida.append((cert, servicio))
    return salida


def cuentas(lista: Lista, tipos=TIPOS_QUE_EMITEN) -> Resumen:
    """Lo mismo que `anclas_de`, pero contando también lo que se deja fuera."""
    mirados = concedidos = retirados = sin_certificado = repetidos = 0
    vistos: set[bytes] = set()
    for servicio in lista.servicios:
        if servicio.tipo not in tipos:
            continue
        mirados += 1
        sin_certificado += servicio.sin_certificado
        if not servicio.concedido:
            retirados += 1
            continue
        concedidos += 1
        for cert in servicio.certificados:
            if cert.der in vistos:
                repetidos += 1
            else:
                vistos.add(cert.der)
    return Resumen(
        escritas=len(vistos),
        servicios_mirados=mirados,
        concedidos=concedidos,
        retirados=retirados,
        sin_certificado=sin_certificado,
        repetidos=repetidos,
    )


_FEO = re.compile(r"[^a-z0-9]+")


def _nombre_de_fichero(cert: Certificado) -> str:
    """Un nombre de fichero legible y sin colisiones para un ancla.

    Legible porque quien abra la carpeta tiene que poder reconocer lo que hay,
    y con la huella detrás porque dos autoridades distintas pueden llamarse
    igual —y una que renueva su certificado se llama igual que ella misma—.
    """
    crudo = unicodedata.normalize("NFKD", cert.sujeto or "sin-nombre")
    crudo = crudo.encode("ascii", "ignore").decode("ascii").lower()
    limpio = _FEO.sub("-", crudo).strip("-")[:60] or "sin-nombre"
    corta = cert.huella().replace(":", "")[:16].lower()
    return f"{limpio}-{corta}.cer"


def _manifiesto(lista: Lista, resumen: Resumen, cuando: datetime) -> str:
    """Lo que hay que poder contestar dentro de tres años sobre esta carpeta.

    La primera línea la lee `Almacen` y acaba en el informe de cada factura,
    así que dice de dónde salen las anclas en una frase que se entienda sola.
    El resto es para quien abra la carpeta a mano.
    """
    quien = lista.operador or f"el operador de la lista de {lista.territorio}"
    emitida = lista.emitida.date().isoformat() if lista.emitida else "(sin fecha)"
    cabecera = (
        f"de la lista de confianza de {lista.territorio or '(sin territorio)'}, "
        f"publicada por {quien} el {emitida}"
    )
    lineas = [
        cabecera,
        "",
        "Esta carpeta la ha montado `python -m validador --montar-anclas`.",
        "No se edita a mano: se vuelve a montar.",
        "",
        f"  lista            {lista.tipo or '(sin tipo)'}",
        f"  secuencia        {lista.secuencia or '(sin número)'}",
        f"  publicada        {emitida}",
        f"  siguiente        "
        + (lista.siguiente.date().isoformat() if lista.siguiente else "(no dice)"),
        f"  montada          {cuando.date().isoformat()}",
    ]
    if lista.firmante is not None:
        lineas += [
            f"  firmada por      {lista.firmante.sujeto or '(sin nombre común)'}",
            f"  huella del firmante",
            f"                   {lista.firmante.huella()}",
        ]
    lineas += [
        "",
        f"  anclas escritas  {resumen.escritas}",
        f"  servicios que emiten certificados cualificados: "
        f"{resumen.servicios_mirados}",
        f"    {'concedidos':<16}{resumen.concedidos}",
        f"    {'retirados':<16}{resumen.retirados}  (no se instalan)",
        f"    {'sin certificado':<16}{resumen.sin_certificado}  (no dan ancla)",
        f"    {'repetidos':<16}{resumen.repetidos}  "
        "(un certificado, varios servicios)",
        "",
        "Los retirados no están aquí. Una autoridad retirada firmó certificados",
        "buenos mientras estuvo concedida, así que una factura antigua suya",
        "saldrá como «no llega a ninguna autoridad conocida»: es un aviso, no un",
        "error, y no se distingue de que falte el certificado.",
        "",
        "Cada .cer se puede contrastar con la huella que publica su autoridad.",
    ]
    return "\n".join(lineas) + "\n"


def montar(
    lista: Lista,
    carpeta: str | Path,
    tipos=TIPOS_QUE_EMITEN,
    cuando: datetime | None = None,
) -> Resumen:
    """Escribe el conjunto de anclas en una carpeta, con su manifiesto.

    Se niega si la lista no se ha verificado. No es una comprobación defensiva
    de más: montar anclas de una lista sin verificar es fabricar exactamente el
    problema que este módulo existe para no tener, y hacerlo con un aviso en
    vez de una negativa sería dejar la decisión en manos del que tiene prisa.
    """
    if not lista.verificada:
        raise ValueError(
            "no se monta un conjunto de anclas de una lista cuya firma no se "
            "ha comprobado: hay que decir quién tenía que firmarla"
        )
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    for cert, _ in anclas_de(lista, tipos):
        (carpeta / _nombre_de_fichero(cert)).write_bytes(cert.der)
    resumen = cuentas(lista, tipos)
    (carpeta / NOMBRE_DEL_MANIFIESTO).write_text(
        _manifiesto(lista, resumen, cuando or datetime.now(timezone.utc)),
        encoding="utf-8",
    )
    return Resumen(**{**resumen.__dict__, "carpeta": carpeta})
