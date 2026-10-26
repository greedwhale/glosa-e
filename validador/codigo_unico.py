"""El código único de factura que exige el RD 238/2026.

Cada factura debe quedar identificada de forma inequívoca por la combinación
de tres datos: el **NIF del emisor**, el **número y serie**, y la **fecha de
expedición**. Ese triple es lo que permite al receptor saber si una factura ya
le había llegado, y al emisor demostrar que no ha repetido ni salteado
numeración.

Esta regla no está en EN 16931. Ningún validador europeo la comprueba, porque
es española: sale del artículo 6 del Reglamento de Facturación (numeración
correlativa dentro de cada serie) y del sistema de facturación del RD 238/2026.

Lo que aquí se comprueba va en dos niveles:

1. **Un código suelto**: que el NIF sea real, que el número quepa y no traiga
   basura, que la fecha exista y no sea del futuro.
2. **Un conjunto de códigos**: duplicados, numeración reutilizada, huecos en
   la serie y fechas que retroceden. Esto último es lo que de verdad se paga,
   porque a ojo no se ve en un lote de trescientas facturas.

Sobre los límites concretos: la orden técnica del RD 238/2026, la Orden
HAC/1028/2026, salió en el BOE el 05-10-2026 y no fija ninguno. Su anexo I
describe `BT-1` como la serie y número que identifican la factura emitida, sin
longitud, y su artículo 6 define el código único como la concatenación del NIF
del emisor, la serie y número y la fecha de expedición según lo especificado
en el anexo I, que no lo especifica: ni separador ni formato.

Se le preguntó al buzón el 07-10-2026, y contestó el 13-10-2026 (en el README,
en la sección de esa consulta). La concatenación no es literal: el
identificador son los tres datos por separado. La fecha va en AAAA-MM-DD. El
NIF, sin ES, y si viene el sistema lo trata igual sin él. Y `BT-1` es la serie
seguida del número, sin separador. Es lo que aquí ya se hacía: los tres datos
se comparan por separado, el NIF con `limpiar_nif`, y la serie y el número se
pegan sin separador, como en Verifactu. La longitud no la dijo, y el tope
sigue tomado del esquema de Verifactu (RD 1007/2023), donde el campo
equivalente admite 60 caracteres. Si se fija otro, se cambia esta constante,
y ya está.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

from lxml import etree

from validador import cifras, edifact, nif
from validador import paises
from validador.formato import (
    CII,
    EDIFACT,
    FACTURAE,
    RESPUESTAS,
    UBL,
    detectar,
    parser,
)
from validador.incidencias import AVISO, ERROR, Incidencia, Informe

# Tope de longitud del número de factura, serie incluida. Tomado de Verifactu.
LONGITUD_MAXIMA_NUMERO = 60

# Plazo de prescripción tributaria. Una factura con fecha anterior a eso no es
# ilegal, pero casi siempre es un error de tecleo en el año.
ANIOS_PRESCRIPCION = 4

def partir_ordinal(numero: str) -> tuple[str, str] | None:
    r"""Parte "F-2026-001" en el prefijo "F-2026-" y el ordinal "001".

    Es lo que permite ver los huecos de una serie. Devuelve `None` cuando no
    hay ordinal que sacar, y también cuando el número es más largo de lo que
    cabe en el campo: ahí ya se ha quejado CU-03, y de un número que no es
    válido no hay correlatividad que reconstruir.

    **Por qué no es una expresión regular.** Lo era:
    `^(?P<prefijo>.*?)(?P<digitos>\d+)$`. Con un número que acaba en algo que
    no es un dígito, el motor prueba cada corte posible y todos fallan, así que
    el coste crece con el cuadrado de la longitud. Medido el 21-09-2026 con
    dígitos y una letra al final: 303 ms con 5.000 caracteres, 961 ms con
    10.000, 8.891 ms con 20.000. El mismo número acabado en dígitos: 0,2 ms.
    Recorrerlo del final hacia delante da la misma respuesta en una pasada.

    **Y por qué el tope.** Con el ordinal entre las manos se hace `int()`, y
    Python se niega a convertir cadenas de más de 4.300 dígitos desde la 3.11
    —es la defensa contra un `int()` cuadrático—. Un número de 4.301 unos
    levantaba `ValueError` y el informe entero se convertía en
    `VALIDADOR-SE-ATRAGANTA`. El tope de aquí es sesenta, así que eso ya no
    puede pasar; que sea el mismo de CU-03 no es casualidad sino el motivo.

    `isdecimal()` y no `isdigit()`: el primero es exactamente la categoría
    Unicode Nd, que es lo que casaba `\d`. `isdigit()` acepta además los
    superíndices, que `int()` no convierte.
    """
    if len(numero) > LONGITUD_MAXIMA_NUMERO:
        return None
    corte = len(numero)
    while corte and numero[corte - 1].isdecimal():
        corte -= 1
    if corte == len(numero):
        return None  # no acaba en dígitos: no hay ordinal
    return numero[:corte], numero[corte:]

_RE_ESPACIOS = re.compile(r"\s+")


def _hace_anios(desde: date, anios: int) -> date:
    """El mismo día de hace tantos años.

    Antes esto se hacía comparando años de calendario —`fecha.year < hoy.year -
    4`— y el mensaje prometía algo que la comprobación no hacía: dice «más de 4
    años» pero se saltaba entero el tramo entre 4 y casi 5. Un 20 de septiembre
    de 2026, una factura del 1 de enero de 2022 tiene cuatro años y siete meses
    y no se decía nada de ella; una del 31 de diciembre de 2021, tres semanas
    más vieja, sí saltaba. La diferencia real entre las dos es de tres semanas
    y la respuesta del programa era la contraria.
    """
    try:
        return desde.replace(year=desde.year - anios)
    except ValueError:
        # 29 de febrero: el año de destino no tiene ese día. Se toma el 28,
        # que es como cuenta los plazos la Administración.
        return desde.replace(year=desde.year - anios, month=2, day=28)


# --- El código único -------------------------------------------------------


@dataclass(frozen=True)
class CodigoUnico:
    """Los tres datos que identifican una factura de forma inequívoca."""

    nif_emisor: str
    numero: str
    fecha: date
    serie: str | None = None

    @property
    def numero_completo(self) -> str:
        """Serie y número tal y como identifican la factura.

        Facturae los guarda en dos campos y UBL en uno solo. Se concatenan sin
        separador, que es como los trata Verifactu y como contestó el buzón el
        13-10-2026 que es `BT-1`: si la serie necesita un guion, ya lo lleva
        dentro.
        """
        return f"{self.serie or ''}{self.numero}"

    def canonico(self) -> str:
        """El código único en texto, tal cual viene en el documento."""
        return f"{self.nif_emisor}|{self.numero_completo}|{self.fecha.isoformat()}"

    def huella(self) -> str:
        """Resumen SHA-256 del código, para indexar sin guardar el texto.

        Las partes se cifran con su longitud por delante. Sin eso, concatenar
        ("AB", "C") y ("A", "BC") daría la misma cadena y dos facturas
        distintas compartirían huella.

        **Y la serie va aparte del número**, que es lo que faltaba hasta el
        22-09-2026. La defensa estaba puesta un nivel por encima de donde
        ocurre el choque: se le daba `numero_completo`, que ya ha pegado serie
        y número sin separador, así que la serie «A» con el número «12» y la
        serie «A1» con el número «2» llegaban aquí como la misma cadena —y
        salían con la misma huella—. La prueba que guardaba esto probaba el
        otro borde, el de NIF contra número, y por eso estaba en verde.
        """
        partes = (
            self.nif_emisor,
            self.serie or "",
            self.numero,
            self.fecha.isoformat(),
        )
        crudo = "".join(f"{len(parte)}:{parte}" for parte in partes)
        return hashlib.sha256(crudo.encode("utf-8")).hexdigest()

    def clave(self) -> tuple[str, str, date]:
        """Clave de comparación, indiferente a mayúsculas y espacios sobrantes.

        Sirve para cazar el caso en que la misma factura llega dos veces
        escrita de forma ligeramente distinta.
        """
        return (
            self.nif_emisor.upper(),
            normalizar_numero(self.numero_completo),
            self.fecha,
        )

    def __str__(self) -> str:
        return self.canonico()


def normalizar_numero(texto: str) -> str:
    """Deja el número listo para comparar: sin espacios sobrantes ni minúsculas."""
    limpio = unicodedata.normalize("NFKC", texto).strip()
    return _RE_ESPACIOS.sub(" ", limpio).upper()


# --- Reglas sobre un código suelto -----------------------------------------


def revisar(codigo: CodigoUnico, hoy: date | None = None) -> list[Incidencia]:
    """Comprueba un código único aislado."""
    hoy = hoy or date.today()
    incidencias: list[Incidencia] = []
    numero = codigo.numero_completo

    # CU-01: el NIF del emisor forma parte del código, así que si está mal, el
    # código único está mal. Se aprovecha la validación que ya existe.
    resultado = nif.validar(codigo.nif_emisor)
    if not resultado:
        incidencias.append(
            Incidencia(
                "CU-01",
                ERROR,
                "El NIF del emisor no es válido, y forma parte del código único "
                f"de la factura. {resultado.motivo}",
                campo="NIF del emisor",
                encontrado=codigo.nif_emisor or "(falta)",
            )
        )

    if not numero.strip():
        # CU-02: sin número no hay código único posible. Las comprobaciones de
        # forma del número dejan de tener sentido, pero las de fecha no, así
        # que se siguen haciendo más abajo.
        incidencias.append(
            Incidencia(
                "CU-02",
                ERROR,
                "La factura no tiene número. Sin él no puede componerse el "
                "código único.",
                campo="Número de factura",
                encontrado="(vacío)",
            )
        )
    else:
        incidencias.extend(_revisar_numero(numero))

    # CU-06: una factura no puede expedirse con fecha del futuro.
    if codigo.fecha > hoy:
        incidencias.append(
            Incidencia(
                "CU-06",
                ERROR,
                "La fecha de expedición es posterior a hoy. Una factura no puede "
                "emitirse con fecha futura.",
                campo="Fecha de expedición",
                esperado=f"{cifras.fecha(hoy)} o anterior",
                encontrado=codigo.fecha.isoformat(),
            )
        )
    # CU-07: o muy anterior, que casi siempre es el año mal tecleado.
    elif codigo.fecha < _hace_anios(hoy, ANIOS_PRESCRIPCION):
        incidencias.append(
            Incidencia(
                "CU-07",
                AVISO,
                f"La fecha de expedición tiene más de {ANIOS_PRESCRIPCION} años, "
                "que es el plazo de prescripción. Comprueba que el año esté bien.",
                campo="Fecha de expedición",
                encontrado=codigo.fecha.isoformat(),
            )
        )

    return incidencias


def _revisar_numero(numero: str) -> list[Incidencia]:
    """Forma del número de factura: longitud, caracteres y espacios."""
    incidencias: list[Incidencia] = []

    # CU-03: longitud.
    if len(numero) > LONGITUD_MAXIMA_NUMERO:
        incidencias.append(
            Incidencia(
                "CU-03",
                ERROR,
                "El número de factura es demasiado largo. El campo admite "
                f"{LONGITUD_MAXIMA_NUMERO} caracteres.",
                campo="Número de factura",
                esperado=f"{LONGITUD_MAXIMA_NUMERO} caracteres como mucho",
                encontrado=f"{len(numero)} caracteres",
            )
        )

    # CU-04: caracteres que no sobreviven a un intercambio entre sistemas.
    if any(unicodedata.category(caracter) == "Cc" for caracter in numero):
        incidencias.append(
            Incidencia(
                "CU-04",
                ERROR,
                "El número de factura contiene caracteres de control (saltos de "
                "línea o tabuladores). Suele venir de un copiar y pegar.",
                campo="Número de factura",
                encontrado=repr(numero),
            )
        )
    else:
        raros = sorted({caracter for caracter in numero if ord(caracter) > 127})
        if raros:
            incidencias.append(
                Incidencia(
                    "CU-04",
                    AVISO,
                    "El número de factura lleva caracteres no ASCII. Es legal, "
                    "pero al pasar por sistemas antiguos puede transformarse, y "
                    "entonces el código único deja de coincidir.",
                    campo="Número de factura",
                    encontrado=f"{numero}  (caracteres: {' '.join(raros)})",
                )
            )

    # CU-05: espacios sobrantes. Invisibles al ojo y letales al comparar.
    espaciado = _RE_ESPACIOS.sub(" ", numero.strip())
    if numero != espaciado:
        incidencias.append(
            Incidencia(
                "CU-05",
                AVISO,
                "El número de factura tiene espacios sobrantes al principio, al "
                "final o repetidos. Dos sistemas que los traten distinto verán "
                "dos facturas donde solo hay una.",
                campo="Número de factura",
                esperado=repr(espaciado),
                encontrado=repr(numero),
            )
        )

    return incidencias


# --- Reglas sobre un conjunto de códigos -----------------------------------


def _de_donde(antes: str | None, ahora: str | None) -> str:
    """Coletilla que dice en que ficheros estan las dos facturas del choque.

    Nombrar solo la primera deja al lector a medias: para arreglar un
    duplicado hay que saber cual de los dos ficheros sobra.
    """
    if not antes:
        return ""
    if antes == ahora:
        return f" Las dos vienen en {antes}."
    return f" La primera viene en {antes} y esta en {ahora}."


def _implicados(*procedencias: str | None) -> tuple[str, ...]:
    """Los ficheros que hacen falta para que la queja exista, sin repetir."""
    vistos: list[str] = []
    for nombre in procedencias:
        if nombre and nombre not in vistos:
            vistos.append(nombre)
    return tuple(vistos)


@dataclass
class Registro:
    """Lleva la cuenta de las facturas ya vistas y avisa al repetirse una.

    Pensado para el caso real: las facturas llegan de una en una y hay que
    decidir en ese momento si es nueva o ya estaba. Guarda tres índices porque
    hay tres formas distintas de repetir una factura, y cada una significa una
    cosa diferente.
    """

    # Cada indice guarda la factura y, si se sabe, de donde venia: en un lote
    # de ficheros lo primero que se pregunta uno al ver un duplicado es "en
    # cual de los dos estaba".
    _canonicos: dict[str, tuple[CodigoUnico, str | None]] = field(default_factory=dict)
    _claves: dict[tuple[str, str, date], tuple[CodigoUnico, str | None]] = field(
        default_factory=dict
    )
    _numeros: dict[tuple[str, str], tuple[CodigoUnico, str | None]] = field(
        default_factory=dict
    )

    def __len__(self) -> int:
        return len(self._canonicos)

    def contiene(self, codigo: CodigoUnico) -> bool:
        return codigo.canonico() in self._canonicos

    def anotar(
        self, codigo: CodigoUnico, procedencia: str | None = None
    ) -> list[Incidencia]:
        """Registra una factura y devuelve lo que choque con las anteriores.

        `procedencia` es de donde sale la factura (un nombre de fichero, por
        ejemplo). Si se pasa, los avisos dicen donde estaba la primera.
        """
        incidencias: list[Incidencia] = []
        canonico = codigo.canonico()
        clave = codigo.clave()
        por_numero = (clave[0], clave[1])

        if canonico in self._canonicos:
            anterior, de_antes = self._canonicos[canonico]
            if (anterior.serie or "", anterior.numero) != (
                codigo.serie or "",
                codigo.numero,
            ):
                # CU-16: el código único se forma pegando serie y número sin
                # separador, así que dos facturas que parten ese texto por
                # sitios distintos producen el mismo. No es un duplicado —son
                # dos facturas— y decirle a quien lo lee que son la misma es
                # mandarle a buscar una copia que no existe.
                #
                # De las tres sintaxis, la única que puede partirlo es
                # **Facturae**: UBL y CII llevan el número entero en un campo
                # —`cbc:ID`, `ram:ID`— y de ahí sale siempre `serie=None`, así
                # que mismo canónico implica mismo número y la rama de abajo
                # es la correcta. Dos UBL nunca llegan aquí; una Facturae
                # contra un UBL, sí, y ese es el caso más feo de todos porque
                # cada formato cree tener su propio número.
                incidencias.append(
                    Incidencia(
                        "CU-16",
                        ERROR,
                        "Dos facturas distintas producen el mismo código "
                        "único. El código pega la serie y el número sin nada "
                        "en medio, y estas dos parten ese mismo texto por "
                        "sitios diferentes. No son la misma factura, pero "
                        "para cualquier registro que las indexe por su código "
                        "lo son: una tapa a la otra."
                        + _de_donde(de_antes, procedencia),
                        campo="Código único",
                        esperado=f"la anterior: {_como_se_parte(anterior)}",
                        encontrado=f"{_como_se_parte(codigo)} "
                        f"; las dos dan {canonico}",
                        ficheros=_implicados(de_antes, procedencia),
                    )
                )
            else:
                # CU-10: la misma factura otra vez. Reenvío o duplicado real.
                incidencias.append(
                    Incidencia(
                        "CU-10",
                        ERROR,
                        "Esta factura ya estaba registrada: mismo emisor, "
                        "mismo número y misma fecha. Es la misma factura dos "
                        "veces, salvo que sean los duplicados de una operación "
                        "con varios destinatarios (art. 14.2 del Reglamento de "
                        "facturación), que repiten el número a propósito."
                        + _de_donde(de_antes, procedencia),
                        campo="Código único",
                        encontrado=canonico,
                        ficheros=_implicados(de_antes, procedencia),
                    )
                )
        elif clave in self._claves:
            # CU-12: es la misma, pero escrita distinto. Peor que un duplicado,
            # porque cada sistema cree tener una factura diferente.
            anterior, de_antes = self._claves[clave]
            incidencias.append(
                Incidencia(
                    "CU-12",
                    ERROR,
                    "Hay dos facturas que solo se distinguen por mayúsculas o "
                    "espacios. Son la misma factura escrita de dos maneras, y "
                    "cada sistema la contará por separado." + _de_donde(de_antes, procedencia),
                    campo="Número de factura",
                    esperado=f"la anterior: {anterior.numero_completo!r}",
                    encontrado=repr(codigo.numero_completo),
                    ficheros=_implicados(de_antes, procedencia),
                )
            )
        elif por_numero in self._numeros:
            # CU-11: mismo número, otra fecha. Numeración reutilizada, que es
            # justo lo que el código único existe para impedir.
            anterior, de_antes = self._numeros[por_numero]
            incidencias.append(
                Incidencia(
                    "CU-11",
                    ERROR,
                    "El número de factura está repetido con otra fecha. Dentro "
                    "de una serie, un número no puede usarse dos veces."
                    + _de_donde(de_antes, procedencia),
                    campo=f"Factura {codigo.numero_completo}",
                    esperado=f"ya usado el {cifras.fecha(anterior.fecha)}",
                    encontrado=f"reutilizado el {cifras.fecha(codigo.fecha)}",
                    ficheros=_implicados(de_antes, procedencia),
                )
            )

        self._canonicos.setdefault(canonico, (codigo, procedencia))
        self._claves.setdefault(clave, (codigo, procedencia))
        self._numeros.setdefault(por_numero, (codigo, procedencia))
        return incidencias


def _huecos(ordinales: list[int]) -> list[tuple[int, int]]:
    """Tramos que faltan en una lista de ordinales ya ordenada."""
    return [
        (anterior + 1, siguiente - 1)
        for anterior, siguiente in zip(ordinales, ordinales[1:])
        if siguiente > anterior + 1
    ]


def _describir_huecos(huecos: list[tuple[int, int]], ancho: int) -> str:
    """Pone los huecos en palabras, sin llenar la pantalla si son muchos."""
    trozos = [
        f"{desde:0{ancho}d}"
        if desde == hasta
        else f"{desde:0{ancho}d} al {hasta:0{ancho}d}"
        for desde, hasta in huecos[:5]
    ]
    if len(huecos) > 5:
        trozos.append(f"y {len(huecos) - 5} tramo(s) mas")
    return ", ".join(trozos)


def _como_se_parte(codigo: CodigoUnico) -> str:
    """«serie "A" + número "12"», para poder enseñar las dos particiones."""
    if not codigo.serie:
        return f"sin serie, número {codigo.numero!r}"
    return f"serie {codigo.serie!r} + número {codigo.numero!r}"


def _reglas_de_serie(codigos: list[CodigoUnico]) -> list[Incidencia]:
    """Correlatividad: huecos, retrocesos de fecha y ceros mal puestos.

    El artículo 6 del Reglamento de Facturación exige que la numeración sea
    correlativa dentro de cada serie. Un hueco no siempre es una infracción
    (puede ser una factura anulada), pero siempre merece una mirada, así que
    va como aviso y no como error.
    """
    incidencias: list[Incidencia] = []
    series: dict[tuple[str, str], list[tuple[int, CodigoUnico]]] = {}
    anchos: dict[tuple[str, str], int] = {}

    for codigo in codigos:
        partes = partir_ordinal(normalizar_numero(codigo.numero_completo))
        if partes is None:
            continue  # un número sin dígitos al final no tiene correlatividad
        prefijo, digitos = partes
        grupo = (codigo.nif_emisor.upper(), prefijo)
        series.setdefault(grupo, []).append((int(digitos), codigo))
        anchos[grupo] = max(anchos.get(grupo, 0), len(digitos))

    for grupo, entradas in sorted(series.items()):
        if len(entradas) < 2:
            continue
        entradas.sort(key=lambda par: par[0])
        prefijo = grupo[1]
        nombre_serie = f"{prefijo}*" if prefijo else "(sin prefijo)"
        ancho = anchos[grupo]

        # CU-15: el mismo ordinal escrito con distinto relleno de ceros. Para
        # una persona es el mismo número; para el código único, no.
        # Se comparan las formas normalizadas: si dos numeros solo se
        # distinguen por mayusculas o espacios, el problema es otro y ya lo
        # canta CU-12. Aqui interesa solo el relleno de ceros.
        por_ordinal: dict[int, set[str]] = {}
        for ordinal, codigo in entradas:
            forma = normalizar_numero(codigo.numero_completo)
            por_ordinal.setdefault(ordinal, set()).add(forma)
        for ordinal, formas in sorted(por_ordinal.items()):
            if len(formas) > 1:
                incidencias.append(
                    Incidencia(
                        "CU-15",
                        AVISO,
                        "El mismo número aparece escrito con distinto relleno de "
                        "ceros. Para una persona es la misma factura; para el "
                        "código único son dos.",
                        campo=f"Serie {nombre_serie}",
                        encontrado=" y ".join(sorted(formas)),
                    )
                )

        ordinales = sorted(por_ordinal)
        huecos = _huecos(ordinales)
        if huecos:
            faltan = sum(hasta - desde + 1 for desde, hasta in huecos)
            incidencias.append(
                Incidencia(
                    "CU-13",
                    AVISO,
                    f"La serie tiene huecos: falta(n) {faltan} número(s) entre el "
                    "primero y el último. Si son facturas anuladas, no pasa nada; "
                    "si no, la numeración no es correlativa.",
                    campo=f"Serie {nombre_serie}",
                    esperado=(
                        f"del {ordinales[0]:0{ancho}d} al {ordinales[-1]:0{ancho}d} "
                        "sin saltos"
                    ),
                    encontrado=f"falta(n) {_describir_huecos(huecos, ancho)}",
                )
            )

        # CU-14: dentro de una serie, la fecha no debería retroceder al avanzar
        # el número. Cuando lo hace, suele ser una factura metida a posteriori.
        for (ordinal_antes, anterior), (ordinal, codigo) in zip(
            entradas, entradas[1:]
        ):
            # Con el mismo ordinal el número no ha avanzado, así que decir que
            # «la fecha retrocede al avanzar el número» es afirmar algo que no
            # ha pasado: la queja salía mostrando F-001 y F-001. Las entradas se
            # ordenan solo por ordinal, y al empatar quedan en el orden en que
            # llegaron, que es el de los ficheros de la carpeta. De ese caso ya
            # se queja CU-11, que sí sabe lo que es: número reutilizado.
            if ordinal == ordinal_antes:
                continue
            if codigo.fecha < anterior.fecha:
                incidencias.append(
                    Incidencia(
                        "CU-14",
                        AVISO,
                        "La fecha retrocede al avanzar el número. Dentro de una "
                        "serie correlativa, una factura posterior no debería "
                        "llevar fecha anterior.",
                        campo=f"Serie {nombre_serie}",
                        esperado=(
                            f"{codigo.numero_completo}: "
                            f"{cifras.fecha(anterior.fecha)} o posterior"
                        ),
                        encontrado=(
                            f"{anterior.numero_completo} el "
                            f"{cifras.fecha(anterior.fecha)}, pero "
                            f"{codigo.numero_completo} el {cifras.fecha(codigo.fecha)}"
                        ),
                    )
                )

    return incidencias


def reglas_de_lote(
    codigos: list[CodigoUnico], procedencias: list[str] | None = None
) -> list[Incidencia]:
    """Lo que solo se ve mirando varias facturas a la vez.

    Va aparte de `revisar` a proposito: cuando se validan cien ficheros, las
    comprobaciones de cada factura se hacen fichero a fichero, pero estas hay
    que hacerlas una sola vez sobre el monton entero. Si no, un duplicado
    entre dos ficheros no se ve, o se cuenta dos veces.
    """
    incidencias: list[Incidencia] = []
    registro = Registro()
    for indice, codigo in enumerate(codigos):
        de_donde = procedencias[indice] if procedencias else None
        incidencias.extend(registro.anotar(codigo, procedencia=de_donde))
    incidencias.extend(_reglas_de_serie(codigos))
    return incidencias


def revisar_lote(
    codigos: list[CodigoUnico], hoy: date | None = None
) -> list[Incidencia]:
    """Revisa un conjunto de facturas: cada una por su cuenta y todas juntas."""
    incidencias: list[Incidencia] = []
    for codigo in codigos:
        incidencias.extend(revisar(codigo, hoy=hoy))
    incidencias.extend(reglas_de_lote(codigos))
    return incidencias


# --- Extracción desde el documento -----------------------------------------

_FORMATOS_FECHA = (
    ("%Y-%m-%d", 10),  # ISO, que es lo que usan UBL y Facturae
    ("%Y%m%d", 8),  # formato 102 de CII
    ("%d-%m-%Y", 10),  # el que usa Verifactu
    ("%d/%m/%Y", 10),
)


def leer_fecha(bruto: str | None) -> date | None:
    """Interpreta una fecha de factura en cualquiera de los formatos al uso.

    Se prueba ISO primero. Un valor como "07-09-2026" no encaja en ISO (el día
    se quedaría con cuatro cifras), así que no hay ambigüedad posible entre los
    dos formatos con guiones.
    """
    if not bruto:
        return None
    texto = bruto.strip()
    for patron, ancho in _FORMATOS_FECHA:
        try:
            return datetime.strptime(texto[:ancho], patron).date()
        except ValueError:
            continue
    return None


def limpiar_nif(bruto: str | None) -> str:
    """Quita el prefijo de país que llevan los identificadores fiscales.

    En UBL y en Facturae el NIF suele venir en formato de IVA intracomunitario,
    con el país delante: ESB12345678. El NIF español son nueve caracteres, así
    que once empezando por ES es el mismo con prefijo.
    """
    documento = nif.normalizar(bruto or "")
    if len(documento) == 11 and documento.startswith("ES"):
        return documento[2:]
    return documento


def _local(nodo, *nombres: str) -> str | None:
    """Texto de un descendiente directo, buscando por nombre local.

    La ruta es relativa al nodo y baja hijo a hijo a proposito. Con "//" la
    consulta arrancaria de la raiz del documento sin importar desde donde se
    llame, y el NIF del vendedor podria acabar leyendose del comprador.
    """
    ruta = "./" + "/".join(f"*[local-name()='{nombre}']" for nombre in nombres)
    encontrados = nodo.xpath(ruta)
    if not encontrados:
        return None
    texto = (encontrados[0].text or "").strip()
    return texto or None


def _extraer_ubl(raiz) -> list[CodigoUnico]:
    numero = _local(raiz, "ID")
    fecha = leer_fecha(_local(raiz, "IssueDate"))
    # El identificador fiscal del vendedor puede venir en tres sitios distintos
    # segun quien haya generado el fichero. Se prueban por orden de preferencia.
    vendedor = raiz.xpath("//*[local-name()='AccountingSupplierParty']")
    documento = None
    if vendedor:
        for camino in (
            ("Party", "PartyTaxScheme", "CompanyID"),
            ("Party", "PartyLegalEntity", "CompanyID"),
            ("Party", "PartyIdentification", "ID"),
        ):
            documento = _local(vendedor[0], *camino)
            if documento:
                break
    if numero is None or fecha is None:
        return []
    return [CodigoUnico(limpiar_nif(documento), numero, fecha)]


def _extraer_facturae(raiz) -> list[CodigoUnico]:
    """Un fichero Facturae puede llevar varias facturas del mismo emisor."""
    vendedor = raiz.xpath("//*[local-name()='SellerParty']")
    documento = (
        _local(vendedor[0], "TaxIdentification", "TaxIdentificationNumber")
        if vendedor
        else None
    )
    codigos = []
    for factura in raiz.xpath("//*[local-name()='Invoices']/*[local-name()='Invoice']"):
        numero = _local(factura, "InvoiceHeader", "InvoiceNumber")
        serie = _local(factura, "InvoiceHeader", "InvoiceSeriesCode")
        fecha = leer_fecha(_local(factura, "InvoiceIssueData", "IssueDate"))
        if numero is None or fecha is None:
            continue
        codigos.append(CodigoUnico(limpiar_nif(documento), numero, fecha, serie=serie))
    return codigos


def _extraer_cii(raiz) -> list[CodigoUnico]:
    documento = raiz.xpath(
        "//*[local-name()='SellerTradeParty']"
        "/*[local-name()='SpecifiedTaxRegistration']/*[local-name()='ID']"
    )
    cabecera = raiz.xpath("//*[local-name()='ExchangedDocument']")
    if not cabecera:
        return []
    numero = _local(cabecera[0], "ID")
    fecha = leer_fecha(_local(cabecera[0], "IssueDateTime", "DateTimeString"))
    if numero is None or fecha is None:
        return []
    texto = (documento[0].text or "").strip() if documento else None
    return [CodigoUnico(limpiar_nif(texto), numero, fecha)]


# --- ¿A esta factura le aplica el reglamento español? -----------------------

# Donde dice cada sintaxis de que pais es quien emite. Facturae no aparece
# porque es el formato nacional espaniol: si el documento es Facturae, la
# respuesta ya la sabemos.
_PAIS_DEL_EMISOR = {
    UBL: (
        "AccountingSupplierParty",
        ("Party", "PostalAddress", "Country", "IdentificationCode"),
    ),
    CII: ("SellerTradeParty", ("PostalTradeAddress", "CountryID")),
}


def pais_emisor(raiz, deteccion) -> str | None:
    """Codigo de pais de quien emite la factura, o None si no se dice.

    Se mira la direccion postal y no el prefijo del identificador fiscal,
    porque el prefijo se lo pone quien quiere: hay facturas alemanas cuyo
    numero de IVA viene sin `DE` delante.
    """
    if raiz is None or not deteccion:
        return None
    if deteccion.familia == FACTURAE:
        # Antes aqui ponia `return "ES"` a secas, y el comentario de la tabla
        # decia que Facturae no hacia falta "porque es el formato nacional
        # espaniol". Es verdad que lo es, y no es verdad que su emisor sea
        # siempre espaniol: el esquema oficial admite 235 paises en
        # `CountryCode`, y un proveedor extranjero que factura a una
        # administracion espaniola escribe el suyo. A esos se les estaban
        # aplicando las reglas CU-* del RD 238/2026 sin mirar, que es
        # exactamente el fallo grande que documenta HALLAZGOS.md: reglas
        # espaniolas cayendo sobre facturas de fuera.
        #
        # Se lee `LegalEntity` y no `Individual` porque los dos cuelgan de
        # `SellerParty` y solo hay uno de los dos; se prueban los dos sitios
        # donde el esquema deja poner la direccion.
        vendedores = raiz.xpath("//*[local-name()='SellerParty']")
        if not vendedores:
            return None
        for envoltorio in ("LegalEntity", "Individual"):
            for donde in ("AddressInSpain", "OverseasAddress"):
                escrito = _local(
                    vendedores[0], envoltorio, donde, "CountryCode")
                if escrito:
                    # Se devuelve traducido o None: un `ZAR` que ISO ya
                    # retiro no se convierte en Congo por nuestra cuenta.
                    return paises.alpha2(escrito)
        return None
    if deteccion.familia == EDIFACT:
        # EDIFACT no estaba en la tabla, así que esta función contestaba None
        # para todas y `obligado_en_espania` las daba por españolas: a una
        # factura alemana al 19 % le salía IVA-TIPO diciendo que ese tipo no
        # está vigente en España. Es el hallazgo n.º 1 del proyecto —reglas
        # españolas cayendo sobre facturas de fuera— volviendo por el cuarto
        # formato, el único que no es XML y por eso no encaja en la tabla de
        # rutas: el país del vendedor vive en el NAD del sobre y se lee con el
        # mapa de sintaxis, como el resto de los campos de EDIFACT.
        from validador import sintaxis

        escrito = sintaxis.texto(
            raiz, sintaxis.SINTAXIS_EDIFACT.vendedor_pais, sintaxis.SINTAXIS_EDIFACT
        )
        return escrito.strip().upper() if escrito else None
    camino = _PAIS_DEL_EMISOR.get(deteccion.familia)
    if camino is None:
        return None
    contenedor, resto = camino
    nodos = raiz.xpath(f"//*[local-name()='{contenedor}']")
    if not nodos:
        return None
    encontrado = _local(nodos[0], *resto)
    return encontrado.strip().upper() if encontrado else None


# Donde guarda cada sintaxis el identificador fiscal del receptor. Se prueban
# por orden: quien genera el fichero elige uno de los tres y no hay convención.
_NIF_DEL_RECEPTOR: dict[str, tuple[str, tuple[tuple[str, ...], ...]]] = {
    UBL: (
        "AccountingCustomerParty",
        (
            ("Party", "PartyTaxScheme", "CompanyID"),
            ("Party", "PartyLegalEntity", "CompanyID"),
            ("Party", "PartyIdentification", "ID"),
        ),
    ),
    CII: ("BuyerTradeParty", (("SpecifiedTaxRegistration", "ID"),)),
    FACTURAE: (
        "BuyerParty",
        (("TaxIdentification", "TaxIdentificationNumber"),),
    ),
}


def parece_de_fuera(documento: str | None) -> bool:
    """¿Es un identificador fiscal que no sigue el algoritmo español?

    Dos letras seguidas al principio son el prefijo de país de un número de IVA
    intracomunitario: NL999999999B01, DE123456789. **Ningún NIF, NIE ni CIF
    español empieza por dos letras seguidas** —el CIF lleva una letra y ocho
    dígitos, el NIE una letra y siete—, así que la pista no falla por el lado
    que importa, que es no medirle el dígito de control español a quien no lo
    tiene. `ES` se excluye porque ahí sí hay un NIF español debajo.

    Esta misma pista la usa `obligado_en_espania`. Vive aquí para que las dos
    la lean del mismo sitio: la primera vez que se escribió estaba solo en un
    lado, y al copiarla al otro salió mal y una factura holandesa recibía la
    queja igualmente.
    """
    prefijo = nif.normalizar(documento or "")[:2]
    return len(prefijo) == 2 and prefijo.isalpha() and prefijo != "ES"


def nif_receptor(raiz, deteccion) -> str | None:
    """El identificador fiscal de quien recibe la factura, si lo lleva."""
    if raiz is None or not deteccion:
        return None
    camino = _NIF_DEL_RECEPTOR.get(deteccion.familia or "")
    if camino is None:
        return None
    contenedor, opciones = camino
    nodos = raiz.xpath(f"//*[local-name()='{contenedor}']")
    if not nodos:
        return None
    for ruta in opciones:
        encontrado = _local(nodos[0], *ruta)
        if encontrado:
            return encontrado
    return None


def regla_nif_receptor(raiz, deteccion) -> list[Incidencia]:
    """NIF-RECEPTOR: si el receptor lleva NIF español, que sea uno de verdad.

    El código único solo usa el del emisor, así que esto no lo exige el
    RD 238/2026 y por eso no lleva prefijo `CU-`: **no vamos a firmar con una
    norma una queja que esa norma no hace**. Sale como aviso «de la casa».

    Pero un dígito de control que no sale es un hecho, no una opinión, y a
    quien recibe la factura le importa: con el NIF mal no puede deducirse el
    IVA soportado y devuelve la factura. Estaba entre los hallazgos de la
    auditoría precisamente porque no se comprobaba nunca.

    Solo se mira cuando el documento está sujeto a la facturación española.
    Medirle el dígito de control español a un identificador holandés es
    inventarse un error, que es exactamente lo que hacía CU-01 en 61 de 62
    facturas ajenas antes de acotarlo.
    """
    documento = nif_receptor(raiz, deteccion)
    if not documento:
        # Que no lo lleve es otra discusión —depende del tipo de operación— y
        # sin una fuente que citar aquí no se sentencia.
        return []
    if parece_de_fuera(documento):
        return []
    resultado = nif.validar(limpiar_nif(documento))
    if resultado:
        return []
    return [
        Incidencia(
            "NIF-RECEPTOR",
            AVISO,
            "El NIF del receptor no es válido. No forma parte del código "
            f"único, pero quien reciba la factura no podrá deducir el IVA con "
            f"un identificador que no existe. {resultado.motivo}",
            campo="NIF del receptor",
            encontrado=documento,
        )
    ]


def obligado_en_espania(raiz, deteccion) -> bool:
    """Si a este documento le aplica el RD 238/2026.

    El reglamento obliga a quien expide facturas **en España**. Una factura de
    un proveedor holandés a un cliente español no está sujeta a él, y aplicarle
    sus reglas es sencillamente inventarse errores: el dígito de control del
    NIF español no lo pasa ningún identificador extranjero, porque no es su
    algoritmo. En la primera prueba contra facturas ajenas esto saltó en 61 de
    62 documentos, ninguno español.

    Cuando el documento no dice de qué país es se mira el prefijo del
    identificador fiscal, que es peor pista pero alguna es. Vale solo para
    descartar: dos letras que no son `ES` delante de un identificador es un
    número de IVA intracomunitario de otro país, y ningún NIF, NIE ni CIF
    español empieza por dos letras seguidas.

    Y si tampoco hay prefijo, se responde que sí. Es una herramienta para
    facturación española y ese es el caso por defecto; callarse las reglas por
    un dato que falta sería dar por revisado lo que no se ha mirado, que es
    peor que una queja de más. Del país ausente ya se queja BR-09.
    """
    if raiz is None:
        # De un documento que no se ha podido leer no se sabe de dónde es, y
        # la respuesta por defecto es la de abajo: sí. Va explícito porque las
        # ramas que siguen leen del árbol y sin esto reventaban con un
        # AttributeError sobre None —visto al probar un EDIFACT con separadores
        # propios, que se detecta como EDIFACT y no se llega a convertir—.
        return True
    pais = pais_emisor(raiz, deteccion)
    if pais is not None:
        return pais == "ES"
    if deteccion.familia == EDIFACT:
        # De EDIFACT no se sacan códigos únicos —el RD no se los pide— así que
        # el repaso de abajo se quedaba sin nada que mirar y contestaba «sí».
        # La pista que queda es la misma: el número de IVA del vendedor, que
        # en EDIFACT va en el RFF+VA detrás de su NAD.
        from validador import sintaxis

        return not parece_de_fuera(
            sintaxis.texto(
                raiz, sintaxis.SINTAXIS_EDIFACT.vendedor_nif, sintaxis.SINTAXIS_EDIFACT
            )
        )
    return not any(
        parece_de_fuera(codigo.nif_emisor) for codigo in extraer_de(raiz, deteccion)
    )


def extraer_de(raiz, deteccion) -> list[CodigoUnico]:
    """Saca los codigos unicos de un documento ya parseado."""
    if raiz is None or not deteccion:
        return []
    if deteccion.familia == UBL:
        return _extraer_ubl(raiz)
    if deteccion.familia == FACTURAE:
        return _extraer_facturae(raiz)
    if deteccion.familia == CII:
        return _extraer_cii(raiz)
    return []


def extraer(datos: bytes | str) -> list[CodigoUnico]:
    """Saca los códigos únicos de un documento, sea del formato que sea.

    Devuelve una lista porque un fichero Facturae puede contener varias
    facturas. En UBL y CII siempre será cero o una.
    """
    deteccion = detectar(datos)
    if not deteccion:
        return []
    if isinstance(datos, str):
        datos = datos.encode("utf-8")
    # `arbol` y no `etree.fromstring`: un EDIFACT plano no es XML y esto
    # reventaba con un error de sintaxis XML, que era verdad y no venía a
    # cuento. Sacar el código único de un EDIFACT sigue dando cero —ahí no
    # hay dónde escribirlo—, pero devolver cero no es lo mismo que reventar.
    raiz, _ = edifact.arbol(datos, deteccion)
    if raiz is None:
        return []
    return extraer_de(raiz, deteccion)


def sin_codigo_unico() -> Incidencia:
    """La queja de cuando no hay con que componer el codigo unico."""
    return Incidencia(
        "CU-00",
        ERROR,
        "No se ha podido componer el código único: falta el número de "
        "factura, la fecha de expedición, o ambos.",
        campo="Código único",
        esperado="NIF del emisor + serie y número + fecha de expedición",
        encontrado="(incompleto)",
    )


def reglas(raiz, deteccion, hoy: date | None = None) -> list[Incidencia]:
    """Las reglas del codigo unico sobre un documento ya parseado.

    Incluye las de conjunto, porque un solo fichero Facturae puede traer
    varias facturas y pueden chocar entre ellas. Para comparar facturas de
    ficheros distintos esta `reglas_de_lote`, que el orquestador ejecuta una
    sola vez sobre el monton entero.
    """
    if not obligado_en_espania(raiz, deteccion):
        # Factura extranjera: el RD 238/2026 no le aplica. Las reglas europeas
        # sí, y de esas se encarga `en16931`.
        return []
    codigos = extraer_de(raiz, deteccion)
    if not codigos:
        # En EDIFACT y en los formatos que no se saben leer no hay nada que
        # reprochar: no es que falte el codigo unico, es que no se ha mirado.
        if deteccion and deteccion.familia in (UBL, FACTURAE, CII):
            return [sin_codigo_unico()]
        return []
    incidencias = [i for codigo in codigos for i in revisar(codigo, hoy=hoy)]
    incidencias.extend(reglas_de_lote(codigos))
    incidencias.extend(regla_nif_receptor(raiz, deteccion))
    return incidencias


def validar(datos: bytes | str, hoy: date | None = None) -> Informe:
    """Comprueba el código único de las facturas que contenga un documento."""
    deteccion = detectar(datos)
    informe = Informe(deteccion=deteccion)
    if not deteccion:
        return informe
    if deteccion.familia in RESPUESTAS:
        # Una respuesta no lleva código único: no es una factura. Sin esta
        # línea, `extraer` no encontraba nada y salía CU-00, «falta el número
        # de factura», sobre un documento que no tiene por qué llevarlo.
        return informe

    codigos = extraer(datos)
    if not codigos:
        informe.incidencias.append(sin_codigo_unico())
        return informe

    informe.incidencias.extend(revisar_lote(codigos, hoy=hoy))
    return informe
