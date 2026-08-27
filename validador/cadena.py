"""¿De quién es el certificado que firma esta factura?

`firma.py` responde «este documento no se ha tocado y la firma cuadra con el
certificado que trae dentro». Falta lo otro: **de quién es ese certificado**.
Sin esto, un documento firmado con un certificado que el propio remitente se ha
inventado pasa todas las comprobaciones.

Aquí se responde encadenando: el certificado de la factura lo emitió otro, y
ese otro lo emitió otro, hasta llegar a uno que **ya conocemos de antes**. Los
que conocemos de antes son las anclas de confianza.

Esto no necesita red
--------------------
Es la idea que hace el problema tratable. Un ancla de confianza no se consulta:
se conoce. Tu navegador no llama a nadie para saber qué es una autoridad raíz;
las lleva dentro. El sistema operativo, igual.

Así que las anclas se instalan en una carpeta, como los esquemas XSD, y a
partir de ahí encadenar es aritmética local: la misma verificación RSA que ya
está escrita, aplicada hacia arriba. La promesa de que la factura no sale del
ordenador queda intacta.

Lo que **no** responde esto es si el certificado está revocado. Eso sí necesita
red, o que el propio documento traiga la prueba dentro —que es lo que hace
XAdES-XL, y ninguna de las muestras que tenemos llega a ese nivel—. Se dice.

Por qué las anclas no vienen en el repositorio
----------------------------------------------
Porque meter un certificado raíz en el paquete es una decisión de seguridad,
no de comodidad: quien controle ese fichero controla a quién cree el validador.
Bajarlos «como sea» y hornearlos dentro sería crear el problema que este módulo
pretende resolver.

Van en una carpeta que instala quien usa la herramienta, y el validador
**enseña la huella de cada ancla que ha cargado** para que se pueda contrastar
con la que publica la autoridad. No hay que fiarse de por dónde llegó el
fichero: se comprueba.

Sin anclas instaladas no se inventa nada. Se dice que no se ha comprobado, que
es lo mismo que hace `esquema.py` cuando no hay XSD.

Los tres fallos clásicos, y dónde se paran
------------------------------------------
1. **`basicConstraints`.** Un certificado que no es de autoridad no puede haber
   emitido a otro. Los validadores que no lo comprobaban —que fueron muchos, y
   grandes, hasta bien entrados los 2000— permitían que cualquiera con un
   certificado normal emitiera certificados a nombre de quien quisiera. Se
   comprueba en `_eslabon`, y es `ERROR`.
2. **Firmar solo por el nombre.** Que el emisor declarado coincida con el
   sujeto del siguiente no prueba nada: los nombres los escribe quien hace el
   certificado. Cada eslabón se **verifica criptográficamente**.
3. **SHA-1 y MD5 en la cadena.** Con una colisión se fabrica un certificado
   falso que verifica de verdad. Contra SHA-1 se demostró en 2017 y contra MD5
   ya en 2008, con una CA falsa como demostración. Se avisa.
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from validador import firma, revocacion
from validador.firma import (
    ALGORITMOS_ROTOS,
    Certificado,
    leer_certificado,
    verificar,
)
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia

__all__ = ["Almacen", "Cadena", "construir", "reglas", "reglas_de_documento"]

VARIABLE_ENTORNO = "FACTURAE_ANCLAS"
CARPETA_POR_DEFECTO = "anclas"

_EXTENSIONES = (".cer", ".crt", ".der", ".pem", ".ca-bundle")

# Un conjunto de anclas montado desde una lista de confianza deja aquí de dónde
# salió. La primera línea acaba en el informe de cada factura.
#
# Va en un fichero y no en el código de quien monta el almacén a propósito: la
# procedencia tiene que viajar **con los ficheros**. Si hay que acordarse de
# pasarla en la llamada, el día que alguien copie la carpeta a otro sitio se
# quedará sin ella, y un conjunto de anclas que no dice de dónde viene es justo
# lo que habíamos quedado en no repartir.
NOMBRE_DEL_MANIFIESTO = "PROCEDENCIA.txt"

# Qué dice la lista de confianza de cada ancla: si sigue concedida o se retiró,
# y desde cuándo. Una tabla aparte y no un dato dentro del `.cer` porque no es
# un dato del certificado: es lo que **el Estado** dice de esa autoridad, y
# puede cambiar sin que el certificado cambie.
NOMBRE_DE_ESTADOS = "ESTADOS.tsv"

# Dónde van las anclas retiradas. Separadas del resto a propósito: una retirada
# solo vale para lo que se firmó antes de que la retiraran, y mezclarlas con
# las demás haría que copiar la carpeta sin la tabla de estados convirtiera
# cien autoridades caducadas en cien autoridades de confianza. Aquí, si falta
# la fila, el ancla no se usa.
CARPETA_DE_RETIRADAS = "retiradas"
_PEM = re.compile(
    rb"-----BEGIN CERTIFICATE-----(.*?)-----END CERTIFICATE-----", re.S
)

# Más de esto y es que hay un ciclo o alguien está intentando algo.
PROFUNDIDAD_MAXIMA = 10


def certificados_del_fichero(datos: bytes) -> list[bytes]:
    """Los certificados de un fichero, venga en PEM o en DER pelado."""
    trozos = [base64.b64decode(m.group(1)) for m in _PEM.finditer(datos)]
    if trozos:
        return trozos
    return [datos] if datos[:1] == b"\x30" else []


@dataclass
class Almacen:
    """Las anclas de confianza instaladas, si es que hay alguna.

    Se indexan por el nombre del sujeto **en DER**, que es como se encadena.
    Puede haber varias con el mismo sujeto: una autoridad que renueva su raíz
    mantiene las dos en circulación un tiempo, y las dos son buenas.
    """

    carpeta: Path
    # De dónde salen estas anclas, dicho para una persona. Vacío significa
    # «de esa carpeta», que es lo normal cuando las instala quien valida. Una
    # distribución que las traiga puestas —la página web, por ejemplo— tiene
    # que decirlo aquí: «vienen con esta página». Es la diferencia entre una
    # decisión declarada y una tomada a espaldas de quien lee el informe.
    procedencia: str = ""
    _por_sujeto: dict[bytes, list[Certificado]] | None = field(
        default=None, repr=False
    )
    _de_donde: dict[bytes, Path] = field(default_factory=dict, repr=False)
    # huella (sin dos puntos, en minúsculas) -> (estado, fecha, prestador)
    _estados: dict[str, tuple[str, date | None, str]] = field(
        default_factory=dict, repr=False
    )
    _retiradas: set[bytes] = field(default_factory=set, repr=False)
    _ilegibles: list[tuple[Path, str]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        # `Almacen("anclas")` es lo natural de escribir desde fuera, y sin esto
        # no reventaba hasta la primera consulta —«'str' object has no
        # attribute 'is_dir'»— en mitad de validar un lote.
        if not isinstance(self.carpeta, Path):
            self.carpeta = Path(self.carpeta)

    @classmethod
    def por_defecto(
        cls, carpeta: str | Path | None = None, procedencia: str = ""
    ) -> Almacen:
        if carpeta is None:
            carpeta = os.environ.get(VARIABLE_ENTORNO) or CARPETA_POR_DEFECTO
        return cls(Path(carpeta), procedencia)

    @property
    def por_sujeto(self) -> dict[bytes, list[Certificado]]:
        if self._por_sujeto is None:
            encontradas: dict[bytes, list[Certificado]] = {}
            self._de_donde = {}
            self._ilegibles = []
            self._estados = self._leer_estados()
            self._retiradas = set()
            if self.carpeta.is_dir():
                for ruta in sorted(self.carpeta.rglob("*")):
                    if ruta.suffix.lower() not in _EXTENSIONES or not ruta.is_file():
                        continue
                    try:
                        crudos = certificados_del_fichero(ruta.read_bytes())
                    except OSError as error:
                        self._ilegibles.append((ruta, str(error)))
                        continue
                    if not crudos:
                        self._ilegibles.append((ruta, "no trae ningún certificado"))
                        continue
                    for crudo in crudos:
                        try:
                            cert = leer_certificado(crudo)
                        except (ValueError, IndexError) as error:
                            self._ilegibles.append((ruta, str(error)))
                            continue
                        encontradas.setdefault(cert.sujeto_der, []).append(cert)
                        self._de_donde.setdefault(cert.der, ruta)
                        if CARPETA_DE_RETIRADAS in ruta.parts:
                            self._retiradas.add(cert.der)
            self._por_sujeto = encontradas
        return self._por_sujeto

    def _leer_estados(self) -> dict[str, tuple[str, "date | None", str]]:
        """La tabla que dice qué es cada ancla para la lista de confianza."""
        salida: dict[str, tuple[str, date | None, str]] = {}
        try:
            texto = (self.carpeta / NOMBRE_DE_ESTADOS).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return salida
        for linea in texto.splitlines():
            if not linea.strip() or linea.lstrip().startswith("#"):
                continue
            trozos = linea.split("\t")
            if len(trozos) < 3:
                continue
            huella, estado, cuando = trozos[0].strip().lower(), trozos[1].strip(), trozos[2].strip()
            quien = trozos[3].strip() if len(trozos) > 3 else ""
            try:
                fecha = date.fromisoformat(cuando) if cuando else None
            except ValueError:
                fecha = None
            salida[huella] = (estado, fecha, quien)
        return salida

    def estado_de(self, cert: Certificado) -> tuple[str, "date | None", str]:
        """Qué dice la lista de confianza de esta ancla, si es que dice algo.

        Sin fila, `("", None, "")`: no se sabe. Para una que está en la carpeta
        normal eso es lo corriente —un ancla puesta a mano no tiene fila—; para
        una que está entre las retiradas, es lo que hace que no se use.
        """
        self.por_sujeto  # fuerza el recorrido
        return self._estados.get(cert.huella().replace(":", "").lower(),
                                 ("", None, ""))

    def retirada(self, cert: Certificado) -> bool:
        self.por_sujeto
        return cert.der in self._retiradas

    def vale_para(self, cert: Certificado, cuando) -> str:
        """¿Sirve esta ancla para algo firmado en esa fecha? El motivo, o «».

        La regla tiene una asimetría que conviene explicar, porque parece un
        descuido y no lo es: **solo se comprueba el final de la ventana, no el
        principio**.

        El final es real: si el Estado retiró a una autoridad el 14 de
        septiembre de 2023, lo que se firmó después no está amparado por ella.

        El principio, en cambio, no dice lo que parece. Casi todas las anclas
        españolas concedidas ponen 2016-06-30, que no es el día en que esa
        autoridad se volvió fiable: es el día en que empezó a aplicarse eIDAS.
        Rechazar por ahí tiraría todas las facturas anteriores a 2016 de
        autoridades que existían y eran válidas, y estaría contestando a una
        pregunta que la lista no responde.
        """
        if not self.retirada(cert):
            return ""
        estado, desde, quien = self.estado_de(cert)
        if desde is None:
            return (
                "está entre las retiradas y no consta desde cuándo, así que no "
                "se puede saber para qué vale"
            )
        if cuando is None:
            return (
                f"dejó de ser una autoridad cualificada el {desde.isoformat()} "
                "y el documento no dice cuándo se firmó"
            )
        fecha = cuando.date() if hasattr(cuando, "date") else cuando
        if fecha >= desde:
            return (
                f"dejó de ser una autoridad cualificada el {desde.isoformat()}, "
                f"antes de la fecha de la firma"
            )
        return ""

    @property
    def declarada(self) -> str:
        """Lo que dice el manifiesto de la carpeta, si es que lo hay.

        Una línea, la primera: el resto del fichero es para quien lo abra a
        mano. Si no se puede leer se devuelve vacío y se cae en la ruta, que
        es peor pero cierto.
        """
        try:
            texto = (self.carpeta / NOMBRE_DEL_MANIFIESTO).read_text(
                encoding="utf-8"
            )
        except (OSError, UnicodeDecodeError):
            return ""
        return texto.strip().splitlines()[0].strip() if texto.strip() else ""

    def procedencia_de(self, cert: Certificado) -> str:
        """De dónde salió esta ancla, para poder decirlo en el informe.

        Tres respuestas por orden de autoridad. La declarada al construir el
        almacén manda sobre todo: quien distribuye un conjunto sabe mejor que
        nosotros cómo llega a quien lo recibe —«viene con esta página»—. Luego
        el manifiesto que dejó quien lo montó desde una lista de confianza. Y
        de última, la ruta del fichero, que es lo único que se puede decir de
        una carpeta que alguien llenó a mano.
        """
        if self.procedencia:
            return self.procedencia
        declarada = self.declarada
        if declarada:
            return declarada
        self.por_sujeto  # fuerza el recorrido
        ruta = self._de_donde.get(cert.der)
        return f"instalada en {ruta}" if ruta else f"instalada en {self.carpeta}"

    @property
    def ilegibles(self) -> list[tuple[Path, str]]:
        self.por_sujeto  # fuerza el recorrido
        return self._ilegibles

    @property
    def vacio(self) -> bool:
        return not self.por_sujeto

    def recargar(self) -> None:
        self._por_sujeto = None
        self._de_donde = {}
        self._ilegibles = []
        self._estados = {}
        self._retiradas = set()

    def todas(self) -> list[Certificado]:
        return [c for lista in self.por_sujeto.values() for c in lista]

    def emisores_de(self, cert: Certificado) -> list[Certificado]:
        return list(self.por_sujeto.get(cert.emisor_der, ()))

    def contiene(self, cert: Certificado) -> bool:
        """¿Es este certificado, byte a byte, una de las anclas?

        Byte a byte y no por sujeto: si bastara el nombre, cualquiera fabrica
        un certificado que dice llamarse igual que una raíz conocida y entra
        por la puerta grande.
        """
        return any(
            otro.der == cert.der for otro in self.por_sujeto.get(cert.sujeto_der, ())
        )

    def inventario(self) -> list[str]:
        """Qué anclas hay y con qué huella, para poder contrastarlas."""
        return [
            f"{cert.sujeto or '(sin nombre común)'} — {cert.huella()}"
            for cert in sorted(self.todas(), key=lambda c: c.sujeto or "")
        ]


@dataclass(frozen=True)
class Cadena:
    """El resultado de intentar encadenar un certificado hasta un ancla."""

    eslabones: list[Certificado]
    llega: bool
    motivo: str = ""
    ancla: Certificado | None = None
    # La cadena habría llegado, pero el ancla ya no valía para esa fecha. Es
    # información distinta de «no la reconozco» y por eso va aparte.
    caducada: bool = False

    @property
    def hoja(self) -> Certificado | None:
        return self.eslabones[0] if self.eslabones else None


def _eslabon(hijo: Certificado, padre: Certificado, hondo: int) -> str | None:
    """¿Puede el padre haber emitido al hijo? Devuelve el fallo, o None.

    El orden importa: primero lo que descalifica al padre como autoridad, y
    solo después la criptografía. Verificar la firma de un certificado que no
    tenía derecho a firmarla contestaría a la pregunta equivocada.
    """
    # En un certificado v3, `basicConstraints` es obligatorio en una CA. Un v1
    # no tiene extensiones y no se puede saber; se acepta solo si es un ancla,
    # y eso ya lo ha decidido quien nos llama.
    if padre.es_autoridad is False:
        return (
            f"«{padre.sujeto or 'el emisor'}» no es un certificado de autoridad "
            "y aun así aparece emitiendo a otro"
        )
    if padre.usos and "firmar_certificados" not in padre.usos:
        return (
            f"«{padre.sujeto or 'el emisor'}» no tiene permiso para firmar "
            "certificados"
        )
    if padre.profundidad_max is not None and hondo > padre.profundidad_max:
        return (
            f"«{padre.sujeto or 'el emisor'}» solo puede encadenar "
            f"{padre.profundidad_max} nivel(es) por debajo"
        )
    if not hijo.algoritmo_firma or not hijo.valor_firma or not hijo.tbs:
        return "no se ha podido leer con qué se firmó"
    if not verificar(hijo.valor_firma, hijo.tbs, padre, hijo.algoritmo_firma):
        return (
            f"la firma de «{hijo.sujeto or 'el certificado'}» no la hizo "
            f"«{padre.sujeto or 'su emisor declarado'}»"
        )
    return None


def construir(
    hoja: Certificado,
    almacen: Almacen,
    sueltos: list[Certificado] | None = None,
    cuando: datetime | None = None,
) -> Cadena:
    """Encadena desde la hoja hasta un ancla, si se puede.

    `sueltos` son los certificados que venían dentro del documento: en XAdES es
    normal que la firma lleve los intermedios. **Solo sirven de escalón**: por
    muchos que traiga el documento, la cadena no vale hasta que toca un ancla,
    porque los de dentro los eligió quien firmó.
    """
    sueltos = sueltos or []
    # Las anclas que no valen para esta fecha se apartan **antes** de encadenar,
    # no después: si se dejaran y se rechazara al final, una cadena que llega a
    # una autoridad retirada taparía otra que llega a una vigente.
    fuera: list[tuple[Certificado, str]] = []

    def sirve(cert: Certificado) -> bool:
        motivo = almacen.vale_para(cert, cuando)
        if motivo:
            fuera.append((cert, motivo))
        return not motivo

    if almacen.contiene(hoja) and sirve(hoja):
        return Cadena([hoja], llega=True, motivo="el propio certificado es un ancla",
                      ancla=hoja)

    eslabones = [hoja]
    vistos = {hoja.der}
    actual = hoja
    for hondo in range(PROFUNDIDAD_MAXIMA):
        candidatos = [c for c in almacen.emisores_de(actual) if sirve(c)]
        anclas = {c.der for c in candidatos}
        candidatos += [c for c in sueltos if c.sujeto_der == actual.emisor_der]
        if not candidatos:
            quien = actual.emisor_nombre or "(sin nombre)"
            if fuera:
                # Teníamos su certificado y no vale para esta fecha. Decirlo así
                # es la diferencia entre «no lo reconozco» y «lo reconozco y
                # dejó de valer», que llevan a cosas distintas.
                cual, motivo = fuera[0]
                return Cadena(
                    eslabones,
                    llega=False,
                    motivo=f"«{cual.sujeto or quien}» {motivo}",
                    caducada=True,
                )
            return Cadena(
                eslabones,
                llega=False,
                motivo=f"no tenemos el certificado de «{quien}»",
            )

        fallo = None
        for padre in candidatos:
            if padre.der in vistos:
                continue
            fallo = _eslabon(actual, padre, hondo)
            if fallo is None:
                if padre.der in anclas:
                    return Cadena(
                        eslabones + [padre], llega=True, ancla=padre
                    )
                vistos.add(padre.der)
                eslabones.append(padre)
                actual = padre
                break
        else:
            return Cadena(eslabones, llega=False, motivo=fallo or "cadena circular")

    return Cadena(eslabones, llega=False, motivo="la cadena es demasiado larga")


# --- Las reglas ------------------------------------------------------------


def _regla_vigencias(cadena: Cadena, cuando: datetime | None, donde: str):
    if cuando is None:
        return []
    incidencias = []
    for cert in cadena.eslabones[1:]:  # la hoja ya la mira `firma.py`
        if cert.desde and cert.hasta and not (cert.desde <= cuando <= cert.hasta):
            incidencias.append(
                Incidencia(
                    "CADENA-CADUCADA",
                    ERROR,
                    f"«{cert.sujeto or 'un certificado de la cadena'}», que está "
                    "por encima del que firma, no estaba vigente el día que la "
                    "factura dice haberse firmado.",
                    campo=f"{donde}Cadena de confianza",
                    esperado=(
                        f"entre {cert.desde.date().isoformat()} y "
                        f"{cert.hasta.date().isoformat()}"
                    ),
                    encontrado=f"firmada el {cuando.date().isoformat()}",
                )
            )
    return incidencias


def _regla_algoritmos(cadena: Cadena, donde: str):
    # El ancla se deja fuera a propósito: su firma no la comprueba nadie —se
    # confía en ella porque está en el almacén, no porque su firma verifique—,
    # así que con qué la firmaron da igual. Casi todas las autoridades en
    # circulación arrastran SHA-1 arriba del todo y avisar sería ruido.
    #
    # Esto decía «autofirmado», que es lo mismo solo mientras las anclas son
    # raíces. Una lista de confianza (TSL) no publica raíces: publica las CA
    # **emisoras**, que están firmadas por alguien. Con el conjunto montado
    # desde la TSL, la regla avisaba de la CA de media España por un algoritmo
    # que aquí no se usa para nada.
    arriba = cadena.ancla.der if cadena.ancla is not None else None
    debiles = [
        c
        for c in cadena.eslabones
        if c.algoritmo_firma in ALGORITMOS_ROTOS and c.der != arriba
    ]
    if not debiles:
        return []
    cual = debiles[0]
    return [
        Incidencia(
            "CADENA-DEBIL",
            AVISO,
            f"«{cual.sujeto or 'un certificado de la cadena'}» está firmado con "
            f"{cual.algoritmo_firma.upper()}, que está roto para firmar "
            "certificados: con una colisión se fabrica uno falso que verifica.",
            campo=f"{donde}Cadena de confianza",
            esperado="SHA-256 o mejor en toda la cadena",
            encontrado=f"{cual.algoritmo_firma.upper()} en {len(debiles)} de "
            f"{len(cadena.eslabones)} eslabones",
        )
    ]


def _describir(cadena: Cadena) -> str:
    return " ← ".join(c.sujeto or "(sin nombre)" for c in cadena.eslabones)


def _nota_de_confianza(cadena: Cadena, almacen: Almacen, donde: str) -> Incidencia:
    """Declarar en qué se ha confiado, cuando la cadena llega.

    Hasta aquí una cadena buena no decía nada: el silencio hacía de aprobado.
    Pero que una firma llegue a una autoridad no es la ausencia de un problema,
    es **una decisión** —creerle a esa autoridad— y quien la toma no es quien
    lee el informe. Si la toma el almacén que viene puesto con la herramienta,
    con más razón hay que decirlo.

    Va la huella entera a propósito, aunque ocupe: es lo que hace la validación
    reproducible. Quien la guarde puede demostrar años después contra qué se
    contrastó, que es lo que pide una inspección y lo que ninguna captura de
    pantalla de un tic verde puede dar.
    """
    ancla = cadena.ancla
    procedencia = almacen.procedencia_de(ancla) if ancla is not None else ""
    huella = ancla.huella() if ancla is not None else "(no se ha podido calcular)"
    quien = cadena.hoja.sujeto if cadena.hoja is not None else "el firmante"
    # Si el ancla está retirada, la firma se ha dado por buena **por la fecha**,
    # y eso hay que decirlo: es una decisión más discutible que la normal y
    # quien lea el informe tiene que poder verla, no deducirla.
    retirada = ""
    if ancla is not None and almacen.retirada(ancla):
        _, desde, _ = almacen.estado_de(ancla)
        retirada = (
            " Esa autoridad dejó de ser cualificada el "
            f"{desde.isoformat() if desde else '(no consta)'}: se acepta porque "
            "la factura es anterior, no porque siga vigente."
        )

    if len(cadena.eslabones) == 1:
        cuerpo = (
            f"El certificado que firma, «{quien}», es él mismo un ancla de "
            "confianza: no se ha encadenado a nadie porque ya estaba en el "
            "almacén."
        )
    else:
        arriba = ancla.sujeto or "una autoridad sin nombre común"
        cuerpo = (
            f"La firma de «{quien}» llega a «{arriba}» en "
            f"{len(cadena.eslabones)} eslabones."
        )
    return Incidencia(
        "CONFIANZA-ANCLA",
        NOTA,
        f"{cuerpo} Esta validación se fía de esa autoridad porque es un ancla "
        f"{procedencia}, con huella SHA-256 {huella}.{retirada}",
        campo=f"{donde}Cadena de confianza",
    )


def reglas(
    certificados: list[Certificado],
    almacen: Almacen | None,
    cuando: datetime | None = None,
    donde: str = "",
    listas: list | None = None,
    listas_dentro: list | None = None,
    hoy=None,
    hay_ocsp: bool = False,
) -> list[Incidencia]:
    """De quién es el certificado que firma, hasta donde se pueda saber.

    `certificados` son los del documento, el primero el que firma.

    La revocación se mira **después** y solo si la cadena llega: preguntar si
    está anulado un certificado que no lleva a ninguna autoridad conocida sería
    contestar a la pregunta equivocada. Y para creerle una lista a alguien hace
    falta la clave de quien la firma, que es justo lo que la cadena acaba de
    encontrar.
    """
    if not certificados:
        return []
    almacen = almacen if almacen is not None else Almacen.por_defecto()

    if almacen.vacio:
        return [
            Incidencia(
                "CADENA-SIN-ANCLAS",
                AVISO,
                "No hay anclas de confianza instaladas, así que no se ha "
                "comprobado de quién es el certificado que firma: solo que la "
                "firma cuadra con él. Un certificado que el remitente se haya "
                f"inventado pasaría igual. Se instalan en «{almacen.carpeta}».",
                campo=f"{donde}Cadena de confianza",
                encontrado="(no hay anclas)",
            )
        ]

    hoja, sueltos = certificados[0], certificados[1:]
    cadena = construir(hoja, almacen, sueltos, cuando=cuando)

    incidencias: list[Incidencia] = []
    if not cadena.llega and cadena.caducada:
        # Sí teníamos su autoridad, y la lista de confianza dice que dejó de
        # serlo antes de esta firma. Es una queja distinta y más fuerte que «no
        # la reconozco»: aquí sí sabemos quién es, y sabemos que ya no valía.
        return [
            Incidencia(
                "CADENA-RETIRADA",
                AVISO,
                f"El certificado que firma lleva a una autoridad que ya no era "
                f"cualificada cuando se firmó: {cadena.motivo}. La firma puede "
                "ser auténtica; lo que no la ampara es la lista de confianza "
                "del Estado.",
                campo=f"{donde}Cadena de confianza",
                esperado="una autoridad cualificada en la fecha de la firma",
                encontrado=_describir(cadena),
            )
        ]
    if not cadena.llega:
        incidencias.append(
            Incidencia(
                "CADENA-DESCONOCIDA",
                AVISO,
                "El certificado que firma no lleva a ninguna autoridad "
                f"conocida: {cadena.motivo}. Puede ser que falte un certificado "
                "en el almacén, o que no lo emitiera nadie de fiar. No es lo "
                "mismo y desde aquí no se distingue.",
                campo=f"{donde}Cadena de confianza",
                esperado="llegar a un ancla instalada",
                encontrado=_describir(cadena),
            )
        )
        # Aun sin llegar arriba, si un eslabón está mal hay que decirlo: es
        # información distinta de «no lo reconozco».
        if "no la hizo" in cadena.motivo or "no es un certificado de autoridad" in cadena.motivo:
            incidencias.append(
                Incidencia(
                    "CADENA-ROTA",
                    ERROR,
                    f"La cadena del certificado está mal formada: {cadena.motivo}.",
                    campo=f"{donde}Cadena de confianza",
                    encontrado=_describir(cadena),
                )
            )
        return incidencias

    incidencias.append(_nota_de_confianza(cadena, almacen, donde))
    incidencias.extend(_regla_vigencias(cadena, cuando, donde))
    incidencias.extend(_regla_algoritmos(cadena, donde))
    incidencias.extend(
        revocacion.reglas(
            cadena.eslabones,
            listas or [],
            listas_dentro=listas_dentro,
            cuando=cuando,
            hoy=hoy,
            donde=donde,
            hay_ocsp=hay_ocsp,
        )
    )
    return incidencias


def reglas_de_documento(
    raiz, deteccion, almacen: Almacen | None = None, listas=None, hoy=None
):
    """Lo mismo, sacando los certificados del documento.

    Vive aquí y no en `firma.py` para que las dependencias vayan en un solo
    sentido: `cadena` sabe de `firma` y `firma` no sabe de `cadena`. Al revés
    habría que importar en diferido dentro de una función, que es la forma
    educada de decir que dos módulos se necesitan mutuamente.
    """
    if raiz is None or not deteccion:
        return []
    firmas = firma.hay_firma(raiz)
    incidencias: list[Incidencia] = []
    for numero, una in enumerate(firmas, start=1):
        donde = f"Firma {numero} · " if len(firmas) > 1 else ""
        incidencias.extend(
            reglas(
                firma.certificados_de(una),
                almacen,
                cuando=firma.momento_de_firma(una),
                donde=donde,
                listas=listas.todas() if listas is not None else [],
                listas_dentro=revocacion.listas_del_documento(una),
                hoy=hoy,
                hay_ocsp=revocacion.trae_ocsp(una),
            )
        )
    return incidencias
