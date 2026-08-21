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

Sobre los límites concretos: la Orden Ministerial técnica del RD 238/2026 aún
no se ha publicado, así que el tope de longitud está tomado del esquema de
Verifactu (RD 1007/2023), donde el campo equivalente admite 60 caracteres. Si
la Orden fija otro, se cambia esta constante y ya está.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime

from lxml import etree

from validador import nif
from validador.formato import CII, FACTURAE, UBL, detectar, parser
from validador.incidencias import AVISO, ERROR, Incidencia, Informe

# Tope de longitud del número de factura, serie incluida. Tomado de Verifactu.
LONGITUD_MAXIMA_NUMERO = 60

# Plazo de prescripción tributaria. Una factura con fecha anterior a eso no es
# ilegal, pero casi siempre es un error de tecleo en el año.
ANIOS_PRESCRIPCION = 4

# Un número de factura acaba casi siempre en dígitos: "F-2026-001" se parte en
# el prefijo "F-2026-" y el ordinal 001. Es lo que permite ver los huecos.
_RE_SUFIJO_NUMERICO = re.compile(r"^(?P<prefijo>.*?)(?P<digitos>\d+)$")

_RE_ESPACIOS = re.compile(r"\s+")


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
        separador, que es como los trata Verifactu: si la serie necesita un
        guion, ya lo lleva dentro.
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
        """
        partes = (self.nif_emisor, self.numero_completo, self.fecha.isoformat())
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
                esperado=f"{hoy.isoformat()} o anterior",
                encontrado=codigo.fecha.isoformat(),
            )
        )
    # CU-07: o muy anterior, que casi siempre es el año mal tecleado.
    elif codigo.fecha.year < hoy.year - ANIOS_PRESCRIPCION:
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
            # CU-10: la misma factura otra vez. Reenvío o duplicado real.
            incidencias.append(
                Incidencia(
                    "CU-10",
                    ERROR,
                    "Esta factura ya estaba registrada: mismo emisor, mismo "
                    "número y misma fecha. Es la misma factura dos veces."
                    + _de_donde(self._canonicos[canonico][1], procedencia),
                    campo="Código único",
                    encontrado=canonico,
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
                    esperado=f"ya usado el {anterior.fecha.isoformat()}",
                    encontrado=f"reutilizado el {codigo.fecha.isoformat()}",
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
        casa = _RE_SUFIJO_NUMERICO.match(normalizar_numero(codigo.numero_completo))
        if not casa:
            continue  # un número sin dígitos al final no tiene correlatividad
        grupo = (codigo.nif_emisor.upper(), casa["prefijo"])
        series.setdefault(grupo, []).append((int(casa["digitos"]), codigo))
        anchos[grupo] = max(anchos.get(grupo, 0), len(casa["digitos"]))

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
        for (_, anterior), (_, codigo) in zip(entradas, entradas[1:]):
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
                            f"{anterior.fecha.isoformat()} o posterior"
                        ),
                        encontrado=(
                            f"{anterior.numero_completo} el "
                            f"{anterior.fecha.isoformat()}, pero "
                            f"{codigo.numero_completo} el {codigo.fecha.isoformat()}"
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
    return extraer_de(etree.fromstring(datos, parser=parser()), deteccion)


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
    codigos = extraer_de(raiz, deteccion)
    if not codigos:
        # En EDIFACT y en los formatos que no se saben leer no hay nada que
        # reprochar: no es que falte el codigo unico, es que no se ha mirado.
        if deteccion and deteccion.familia in (UBL, FACTURAE, CII):
            return [sin_codigo_unico()]
        return []
    incidencias = [i for codigo in codigos for i in revisar(codigo, hoy=hoy)]
    incidencias.extend(reglas_de_lote(codigos))
    return incidencias


def validar(datos: bytes | str, hoy: date | None = None) -> Informe:
    """Comprueba el código único de las facturas que contenga un documento."""
    deteccion = detectar(datos)
    informe = Informe(deteccion=deteccion)
    if not deteccion:
        return informe

    codigos = extraer(datos)
    if not codigos:
        informe.incidencias.append(sin_codigo_unico())
        return informe

    informe.incidencias.extend(revisar_lote(codigos, hoy=hoy))
    return informe
