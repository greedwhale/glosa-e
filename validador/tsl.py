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
from validador.cadena import (
    CARPETA_DE_RETIRADAS,
    NOMBRE_DEL_MANIFIESTO,
    NOMBRE_DE_ESTADOS,
)
from validador.firma import Certificado, ClaveNoSoportada, leer_certificado
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

# El tipo de fichero de una lista procesable. Hace falta porque en la lista
# de listas **cada país puede aparecer dos veces**: una entrada para la
# versión legible en PDF y otra para el XML, y la del PDF va primero. Sin
# mirar esto, «el puntero de España» es el que manda a bajar un documento
# que ninguna máquina va a leer.
MIME_PROCESABLE = "application/vnd.etsi.tsl+xml"

# El tipo que declara la lista de listas. Va dentro de lo que está firmado, que
# es lo que lo hace utilizable para decidir qué se tiene delante.
TIPO_LISTA_DE_LISTAS = (
    "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUlistofthelists"
)


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


def _certificados(nodo) -> tuple[list[Certificado], list[str]]:
    """Los certificados utilizables, y por qué no lo son los que no.

    Lo segundo importa tanto como lo primero. Un servicio trae varias formas de
    identificarse —el certificado, el nombre del sujeto, la huella de la clave—
    y lo normal es que solo una sea un certificado; contar «las que no lo son»
    daba un número enorme y sin significado que además **tapaba** la noticia de
    verdad: que 46 de las 129 autoridades cualificadas concedidas de la lista
    española usan curva elíptica, y este validador todavía no sabe verificarla.

    Un certificado que está y no se puede usar no es lo mismo que un servicio
    que no trae ninguno, y saltárselos juntos y en silencio deja el conjunto
    corto sin que nadie se entere.
    """
    salida: list[Certificado] = []
    no_usables: list[str] = []
    for identidad in nodo.xpath(".//*[local-name()='DigitalId']"):
        crudo = identidad.xpath("./*[local-name()='X509Certificate']/text()")
        if not crudo:
            continue
        try:
            salida.append(
                leer_certificado(base64.b64decode("".join(crudo[0].split())))
            )
        except ClaveNoSoportada as error:
            no_usables.append(str(error))
        except (ValueError, IndexError, binascii.Error) as error:
            no_usables.append(f"no se ha podido leer: {error}")
    return salida, no_usables


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
    # Por qué no se ha podido usar un certificado que **sí está**. Vacío es lo
    # normal. Ver `_certificados`: contar esto junto con «no trae ninguno» fue
    # lo que escondió el asunto de las claves de curva elíptica.
    no_usables: tuple[str, ...] = ()

    @property
    def sin_certificado(self) -> bool:
        """No trae ningún certificado: se identifica de otra forma.

        Es legal —basta el nombre del sujeto o la huella de la clave— y no da
        ancla. Distinto de traer uno que no sabemos usar.
        """
        return not self.certificados and not self.no_usables

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
    # El tipo de fichero al que apunta: PDF o XML. Ver `MIME_PROCESABLE`.
    mime: str = ""

    @property
    def procesable(self) -> bool:
        return self.mime == MIME_PROCESABLE


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
        """¿Es la lista de listas, o la de un país?

        No vale mirar si trae punteros: **la lista de un país también trae
        uno**, de vuelta a la lista de listas, porque el formato se lo exige.
        Con ese criterio la lista española pasaba por lista de listas, y
        `--ver-tsl` enseñaba el puntero de vuelta en lugar de las 243
        autoridades que trae dentro. No se ve con una lista inventada: se ve
        con la de verdad.

        Lo que las distingue es el tipo que declara, que además va dentro de lo
        firmado.
        """
        if self.tipo:
            return self.tipo == TIPO_LISTA_DE_LISTAS
        # Sin tipo declarado —las hay antiguas—, lo que queda es la forma:
        # punteros y ningún servicio.
        return bool(self.punteros) and not self.servicios

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
        """El puntero al fichero **procesable** de un país, no al PDF.

        En la lista de listas de verdad, once países aparecen dos veces —la
        versión legible y la XML— y la del PDF va primero. Quedarse con «la
        primera que case» mandaba a bajar un PDF, y de paso daba por buenos los
        certificados de esa entrada confiando en que fueran los mismos que los
        de la otra: hoy lo son, y nadie lo ha prometido.
        """
        candidatos = [
            uno
            for uno in self.punteros
            if uno.territorio.upper() == territorio.upper()
        ]
        for uno in candidatos:
            if uno.procesable:
                return uno
        # Sin ninguno marcado como procesable se devuelve el primero: hay
        # listas antiguas que no declaran el tipo de fichero, y quedarse
        # callado sería peor que devolver lo único que hay.
        return candidatos[0] if candidatos else None


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
            certificados, no_usables = (
                _certificados(identidad[0]) if identidad else ([], [])
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
                    no_usables=tuple(no_usables),
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
        firmantes, _ = _certificados(identidades[0]) if identidades else ([], [])
        punteros.append(
            Puntero(
                territorio=territorio,
                donde=_de_dentro(puntero, "TSLLocation"),
                tipo=next(
                    iter(puntero.xpath(".//*[local-name()='TSLType']/text()")), ""
                ),
                firmantes=tuple(firmantes),
                mime=next(
                    iter(puntero.xpath(".//*[local-name()='MimeType']/text()")), ""
                ).strip(),
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
    if not firma.verificar(valor, octetos, cert, pareja[0], concatenada=True):
        return "la firma no cuadra con el certificado que la lista enseña"

    lista.firmante = cert
    lista.verificada = True
    return ""


# --- El conjunto -----------------------------------------------------------


@dataclass(frozen=True)
class Resumen:
    """Qué salió de montar el conjunto, para poder contarlo sin adivinar."""

    escritas: int
    # Las que se instalan en la subcarpeta de retiradas, con su ventana.
    escritas_retiradas: int = 0
    servicios_mirados: int = 0
    concedidos: int = 0
    retirados: int = 0
    # Servicios concedidos que no traen ningún certificado: se identifican de
    # otra forma. Legal, y no dan ancla.
    sin_certificado: int = 0
    # Servicios concedidos cuyo certificado **está** y no sabemos usar. Es la
    # cuenta que importa vigilar: mide lo que este validador se está perdiendo.
    no_usables: int = 0
    # Por qué, agrupado, para poder decirlo en vez de dar un número pelado.
    motivos: tuple[tuple[str, int], ...] = ()
    repetidos: int = 0
    carpeta: Path | None = None


def anclas_de(
    lista: Lista, tipos=TIPOS_QUE_EMITEN, retiradas: bool = False
) -> list[tuple[Certificado, Servicio]]:
    """Los certificados que sirven de ancla, con el servicio del que salen.

    Sin repetir: una autoridad que emite certificados de firma y de sello
    aparece en dos servicios con el mismo certificado, y sin quitar los
    repetidos el mismo fichero se escribiría dos veces.

    Con `retiradas` salen también las que dejaron de ser cualificadas. **No es
    lo mismo y no van al mismo sitio**: una retirada solo vale para lo que se
    firmó antes de que la retiraran, y quien las use tiene que saber cuándo
    fue. Ver `montar`.
    """
    salida: list[tuple[Certificado, Servicio]] = []
    vistos: set[bytes] = set()
    for servicio in lista.servicios:
        if servicio.tipo not in tipos:
            continue
        if not servicio.concedido and not (retiradas and servicio.desde):
            # Sin fecha de retirada no se instala aunque se pidan: una ventana
            # que no se sabe dónde empieza no es una ventana.
            continue
        for cert in servicio.certificados:
            if cert.der in vistos:
                continue
            vistos.add(cert.der)
            salida.append((cert, servicio))
    return salida


def cuentas(lista: Lista, tipos=TIPOS_QUE_EMITEN) -> Resumen:
    """Lo mismo que `anclas_de`, pero contando también lo que se deja fuera."""
    mirados = concedidos = retirados = sin_certificado = no_usables = 0
    repetidos = 0
    motivos: dict[str, int] = {}
    vistos: set[bytes] = set()
    for servicio in lista.servicios:
        if servicio.tipo not in tipos:
            continue
        mirados += 1
        if not servicio.concedido:
            retirados += 1
            continue
        concedidos += 1
        if servicio.sin_certificado:
            sin_certificado += 1
        elif not servicio.certificados:
            # Trae certificado y no sirve. Se cuenta una vez por servicio, no
            # una por identidad: lo que se pierde son autoridades, no líneas.
            no_usables += 1
            for cual in servicio.no_usables:
                motivos[cual] = motivos.get(cual, 0) + 1
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
        no_usables=no_usables,
        motivos=tuple(sorted(motivos.items(), key=lambda par: -par[1])),
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
        f"  retiradas        {resumen.escritas_retiradas}  "
        f"(en {CARPETA_DE_RETIRADAS}/, solo para lo firmado antes de su fecha)",
        f"  servicios que emiten certificados cualificados: "
        f"{resumen.servicios_mirados}",
        f"    {'concedidos':<16}{resumen.concedidos}",
        f"    {'retirados':<16}{resumen.retirados}  (no se instalan)",
        f"    {'sin certificado':<16}{resumen.sin_certificado}  "
        "(se identifican de otra forma)",
        f"    {'no utilizables':<16}{resumen.no_usables}  "
        "(traen certificado y no sabemos usarlo)",
        f"    {'repetidos':<16}{resumen.repetidos}  "
        "(un certificado, varios servicios)",
    ]
    if resumen.motivos:
        lineas.append("")
        lineas.append("  Por qué no se ha podido usar el que traen:")
        for cual, cuantos in resumen.motivos:
            lineas.append(f"    {cuantos:>4}  {cual}")
    lineas += [
        "",
        "Las retiradas están en su subcarpeta y solo sirven para lo que se",
        "firmó antes de la fecha que dice ESTADOS.tsv. Sin esa fila no se usan:",
        "una ventana que no se sabe dónde acaba no es una ventana.",
        "",
        "Las que no sabemos usar no están en ninguna de las dos, y sus facturas",
        "saldrán como «no llega a ninguna autoridad conocida». No es la misma",
        "noticia que una retirada: esa autoridad sigue siendo cualificada y el",
        "corto es este validador.",
        "",
        "Cada .cer se puede contrastar con la huella que publica su autoridad.",
    ]
    return "\n".join(lineas) + "\n"


def montar(
    lista: Lista,
    carpeta: str | Path,
    tipos=TIPOS_QUE_EMITEN,
    cuando: datetime | None = None,
    retiradas: bool = True,
) -> Resumen:
    """Escribe el conjunto de anclas en una carpeta, con su manifiesto.

    Se niega si la lista no se ha verificado. No es una comprobación defensiva
    de más: montar anclas de una lista sin verificar es fabricar exactamente el
    problema que este módulo existe para no tener, y hacerlo con un aviso en
    vez de una negativa sería dejar la decisión en manos del que tiene prisa.

    Las **retiradas van aparte**, en una subcarpeta, y su fecha de retirada en
    una tabla. Esa separación es la que hace que ampliar el conjunto no amplíe
    la confianza: una autoridad retirada solo vale para lo que se firmó antes
    de que la retiraran, y `cadena.py` se niega a usarla sin esa fecha. Si
    fueran mezcladas con las demás, copiar la carpeta sin la tabla convertiría
    114 autoridades caducadas en 114 autoridades de confianza.
    """
    if not lista.verificada:
        raise ValueError(
            "no se monta un conjunto de anclas de una lista cuya firma no se "
            "ha comprobado: hay que decir quién tenía que firmarla"
        )
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    estados: list[str] = []
    escritas = 0
    for cert, servicio in anclas_de(lista, tipos):
        (carpeta / _nombre_de_fichero(cert)).write_bytes(cert.der)
        estados.append(_fila(cert, servicio))
        escritas += 1

    fuera = carpeta / CARPETA_DE_RETIRADAS
    escritas_retiradas = 0
    if retiradas:
        con_fecha = [
            (cert, servicio)
            for cert, servicio in anclas_de(lista, tipos, retiradas=True)
            if not servicio.concedido
        ]
        if con_fecha:
            fuera.mkdir(exist_ok=True)
            for cert, servicio in con_fecha:
                (fuera / _nombre_de_fichero(cert)).write_bytes(cert.der)
                estados.append(_fila(cert, servicio))
                escritas_retiradas += 1

    (carpeta / NOMBRE_DE_ESTADOS).write_text(
        _cabecera_de_estados() + "".join(estados), encoding="utf-8"
    )
    resumen = cuentas(lista, tipos)
    resumen = Resumen(
        **{**resumen.__dict__, "escritas_retiradas": escritas_retiradas}
    )
    (carpeta / NOMBRE_DEL_MANIFIESTO).write_text(
        _manifiesto(lista, resumen, cuando or datetime.now(timezone.utc)),
        encoding="utf-8",
    )
    return Resumen(**{**resumen.__dict__, "carpeta": carpeta})


def _fila(cert: Certificado, servicio: Servicio) -> str:
    """Una línea de la tabla de estados: huella, estado, fecha y de quién."""
    cuando = servicio.desde.date().isoformat() if servicio.desde else ""
    quien = (servicio.prestador or servicio.nombre or "").replace("\t", " ")
    return "%s\t%s\t%s\t%s\n" % (
        cert.huella().replace(":", "").lower(),
        "granted" if servicio.concedido else "withdrawn",
        cuando,
        quien,
    )


def _cabecera_de_estados() -> str:
    return (
        "# Qué dice la lista de confianza de cada ancla de esta carpeta.\n"
        "# La lee `cadena.py`: sin la fila de una retirada, esa no se usa.\n"
        "# huella SHA-256\testado\tdesde\tprestador\n"
    )
