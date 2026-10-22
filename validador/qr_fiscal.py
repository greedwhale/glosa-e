"""La dirección del QR fiscal, comparada con la factura que la lleva.

La orden pide en BT-ES-25 "la URL correspondiente al QR VERI*FACTU o
TICKETBAI, según corresponda conforme normativa aplicable", y no dice más: la
forma de esa dirección la dan las especificaciones de cada sistema. Hasta el
22-10-2026 aquí solo se miraba que hubiera una dirección. Una con el NIF de
otro, la fecha de otra factura o el entorno de pruebas de la AEAT pasaba sin
una palabra, y es justo lo que el receptor va a escanear para cotejar la
factura con Hacienda.

Lo que se compara, sin salir a la red:

- **VERI*FACTU.** La dirección lleva el NIF del obligado a expedir, la serie y
  el número, la fecha de expedición y el importe total, y "únicamente" esos
  cuatro parámetros. Se comparan con el NIF del vendedor (BT-31 o BT-32), con
  BT-1, con BT-2 y con BT-112. Con el servidor de pruebas, aviso.
- **TicketBAI.** El identificador TBAI lleva el NIF y la fecha, y la dirección
  la serie, el número y el importe con IVA. Los dos llevan un CRC-8, que se
  recalcula.

No se valida el registro de VERI*FACTU ni su encadenamiento, ni se consulta a
la AEAT si la factura está registrada: eso pide red y el registro, que no
viaja con la factura.

Todo es AVISO y no ERROR. La orden no copia el formato de la dirección en su
anexo, lo deja a la "normativa aplicable", y el validador no sabe qué sistema
de facturación usó el emisor.

Fuentes, bajadas el 22-10-2026 y fijadas por su huella. Las copias no se
versionan, como el resto de documentos de terceros:

- AEAT, "Detalle de las especificaciones técnicas del código QR de la factura
  y de la URL del servicio de cotejo o remisión de información por parte del
  receptor de la factura", versión 0.5.0 de 10-12-2025, 35 páginas.
  https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/IVA/VERI-FACTU/DetalleEspecificacTecnCodigoQRfactura.pdf
  SHA-256 f86b3c260d8a4963dbc18c5007732b53199156c5d1db63242e68db71501b49eb
- TicketBAI, especificaciones técnicas, versión 1.1 de 12-02-2020 (la edición
  en inglés, la que publica Euskadi), apartados 4.3.2, 4.3.3 y anexo 3.
  https://www.euskadi.eus/contenidos/informacion/ticketbai/es_14815/adjuntos/2020.851_TicketBAI_Especificaciones_v_1_1.pdf
  SHA-256 673955d174a10e75ca669363a7c3dc0ad9411283b745a5dd828d50ebc21fe4e0
- Diputación Foral de Araba, anexo V de su orden foral de TicketBAI.
  https://web.araba.eus/documents/d/araba/anexo-v-1-pdf
  SHA-256 91f7e196b9e42b67649567cba34e467672d3758ef8735773bae71c4a674093d4
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from urllib.parse import unquote_plus, urlsplit

from validador import cifras
from validador.incidencias import AVISO, NOTA, Incidencia

# El código va escrito en cada llamada, y no en una constante: `codigos.py` lee
# el catálogo del fuente, y una constante de módulo no la sabe leer.
CAMPO = "Dirección del QR fiscal (BT-ES-25)"

VERIFACTU = "VERIFACTU"
TICKETBAI = "TICKETBAI"

# Los dos servicios de cotejo de la AEAT: el de los sistemas que emiten
# facturas verificables y el de los que no. Los dos son el QR del reglamento de
# VERI*FACTU, y BT-123 dice VERIFACTU en los dos casos: la lista de la orden no
# tiene un tercer valor.
_RUTAS_DE_LA_AEAT = ("/wlpl/TIKE-CONT/ValidarQR", "/wlpl/TIKE-CONT/ValidarQRNoVerifactu")
_AEAT = "www2.agenciatributaria.gob.es"
_AEAT_PRUEBAS = "prewww2.aeat.es"

# Las tres haciendas forales, con la ruta que da la especificación de 2020.
# Para Araba hay dos: la especificación da /TBAI/QRTBAI, sin barra final, y el
# anexo V de su orden foral, en castellano, /tbai/qrtbai/, con ella. Las dos se
# aceptan. La barra cambia el CRC, que se calcula sobre la dirección tal cual
# va, así que el CRC no depende de cuál se elija.
_HACIENDAS_FORALES = {
    "ticketbai.araba.eus": ("Araba", ("/tbai/qrtbai",)),
    "batuz.eus": ("Bizkaia", ("/qrtbai",)),
    "tbai.egoitza.gipuzkoa.eus": ("Gipuzkoa", ("/qr",)),
}

# Los cuatro de la AEAT, en el orden de su tabla. El servicio admite además
# idioma y formato, pero son del servicio, no del QR: la tabla dice que la
# dirección del QR lleva "únicamente" los cuatro, y de formato dice que "nunca
# podrá incorporarse en la URL que va en el código QR".
_PARAMETROS_DE_LA_AEAT = ("nif", "numserie", "fecha", "importe")
_PARAMETROS_DE_TICKETBAI = ("id", "s", "nf", "i", "cr")

_NIF = re.compile(r"[0-9A-Z]{9}")
_FECHA_AEAT = re.compile(r"(\d{2})-(\d{2})-(\d{4})")
_IMPORTE = re.compile(r"-?\d{1,12}(\.\d{1,2})?")
_ID_TBAI = re.compile(r"TBAI-([0-9A-Z]{9})-(\d{2})(\d{2})(\d{2})-(.{13})-(\d{3})")


def crc8(texto: str) -> str:
    """El CRC-8 de TicketBAI, en decimal y con tres cifras.

    Polinomio 0x07, sin reflejar, empezando y acabando en cero: es el del anexo
    3 de la especificación. Comprobado con sus dos ejemplos, el 237 del
    identificador y el 007 de la dirección.
    """
    crc = 0
    for byte in texto.encode("utf-8"):
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return f"{crc:03d}"


def _aviso(mensaje: str, esperado: str, encontrado: str, campo: str = CAMPO) -> Incidencia:
    return Incidencia("SPFE-QR-URL", AVISO, mensaje, campo=campo,
                      esperado=esperado, encontrado=encontrado)


def _parametros(consulta: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Los parámetros de la dirección, decodificados, y los que salen repetidos.

    A mano y no con `parse_qsl`: hay que ver los repetidos, y un "&" sin
    codificar dentro del número de serie, que la especificación pone como
    ejemplo de error, parte el valor en dos y deja un parámetro de sobra.
    """
    pares: list[tuple[str, str]] = []
    for trozo in consulta.split("&"):
        if not trozo:
            continue
        nombre, _, valor = trozo.partition("=")
        pares.append((unquote_plus(nombre), unquote_plus(valor)))
    nombres = [nombre for nombre, _ in pares]
    repetidos = sorted({nombre for nombre in nombres if nombres.count(nombre) > 1})
    return pares, repetidos


def _importe(texto: str) -> Decimal | None:
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def revisar(
    direccion: str,
    tipo: str | None,
    *,
    nifs_del_vendedor: set[str],
    numero: str,
    fecha: date | None,
    total: str,
    moneda: str,
) -> list[Incidencia]:
    """Lo que la dirección del QR dice de la factura, contra lo que dice ella.

    `tipo` es BT-123, VERIFACTU o TICKETBAI, o None si no viene. El resto son
    los datos de la factura: el NIF del vendedor, sin prefijo de país, BT-1,
    BT-2, BT-112 tal cual está escrito y BT-5.
    """
    partes = urlsplit(direccion.strip())
    servidor = (partes.hostname or "").lower()
    ruta = partes.path.rstrip("/").lower()
    if partes.scheme.lower() != "https" or not servidor:
        return [_aviso(
            "La dirección del QR fiscal no es una dirección web con https. Tiene "
            "que ser la del servicio de cotejo de la AEAT o la de una hacienda "
            "foral, con los datos de la factura.",
            "https://...", direccion)]

    if servidor in (_AEAT, _AEAT_PRUEBAS) and ruta in {r.lower() for r in _RUTAS_DE_LA_AEAT}:
        sistema = VERIFACTU
    elif servidor in _HACIENDAS_FORALES and ruta in _HACIENDAS_FORALES[servidor][1]:
        sistema = TICKETBAI
    else:
        conocidas = [f"https://{_AEAT}{_RUTAS_DE_LA_AEAT[0]}"] + [
            f"https://{host}{rutas[0]}" for host, (_, rutas) in _HACIENDAS_FORALES.items()]
        return [_aviso(
            "La dirección del QR fiscal no es ninguna de las publicadas: ni el "
            "servicio de cotejo de la AEAT ni el de una hacienda foral. Puede ser "
            "un entorno de pruebas, o una dirección propia del emisor; el "
            "receptor que la escanee no podrá cotejar la factura con Hacienda. "
            "Los datos de la factura que lleve no se han comparado.",
            ", ".join(conocidas), direccion)]

    incidencias: list[Incidencia] = []
    if tipo and tipo != sistema:
        de_quien = ("la AEAT, que es el QR de VERI*FACTU" if sistema == VERIFACTU
                    else "una hacienda foral, que es el QR de TicketBAI")
        incidencias.append(_aviso(
            f"La descripción del QR dice {tipo} y la dirección es la de {de_quien}.",
            sistema, tipo, campo="Tipo de QR (BT-123)"))

    pares, repetidos = _parametros(partes.query)
    if repetidos:
        incidencias.append(_aviso(
            "La dirección del QR lleva parámetros repetidos, y no se sabe cuál "
            "lee el servicio de cotejo.",
            "cada parámetro una vez", ", ".join(repetidos)))
    valores = dict(reversed(pares))

    if sistema == VERIFACTU:
        if servidor == _AEAT_PRUEBAS:
            incidencias.append(_aviso(
                "La dirección del QR es la del entorno de pruebas de la AEAT "
                f"({_AEAT_PRUEBAS}), no la de producción. Una factura de verdad "
                "con este QR no se puede cotejar.",
                _AEAT, servidor))
        incidencias += _de_la_aeat(pares, valores, nifs_del_vendedor, numero,
                                   fecha, total, moneda)
    else:
        incidencias += _de_ticketbai(direccion.strip(), pares, valores, nifs_del_vendedor,
                                     numero, fecha, total, moneda)
    return incidencias


def _sobrantes(pares, admitidos) -> list[str]:
    return list(dict.fromkeys(nombre for nombre, _ in pares if nombre not in admitidos))


def _nif_contra(nif_del_qr: str, nifs_del_vendedor: set[str]) -> list[Incidencia]:
    # Sin un NIF del vendedor que leer no hay con qué comparar, y su falta ya
    # la dice SPFE-NIF.
    if not nifs_del_vendedor or nif_del_qr in nifs_del_vendedor:
        return []
    return [_aviso(
        "El NIF de la dirección del QR no es el del vendedor. El QR lleva el "
        "del obligado a expedir la factura, que es el vendedor también cuando "
        "la expide un tercero o el destinatario.",
        " o ".join(sorted(nifs_del_vendedor)), nif_del_qr)]


def _fecha_contra(del_qr: date, fecha: date | None) -> list[Incidencia]:
    if fecha is None or del_qr == fecha:
        return []
    return [_aviso(
        "La fecha de la dirección del QR no es la fecha de expedición de la "
        "factura (BT-2).",
        cifras.fecha(fecha), cifras.fecha(del_qr))]


def _total_contra(del_qr: str, total: str, moneda: str) -> list[Incidencia]:
    escrito, en_la_factura = _importe(del_qr), _importe(total)
    if escrito is None or en_la_factura is None:
        return []
    if moneda and moneda != "EUR":
        # La especificación dice "importe total de la factura" y no dice en qué
        # moneda. Compararlo con un total en dólares sería inventarse la regla,
        # y callarlo haría pasar por comparado lo que no lo está.
        return [Incidencia(
            "SPFE-QR-URL", NOTA,
            f"El importe de la dirección del QR no se ha comparado con el total "
            f"de la factura, que está en {moneda}: las especificaciones del QR "
            "no dicen en qué moneda va.",
            campo=CAMPO, esperado="(no se compara)", encontrado=del_qr)]
    if escrito == en_la_factura:
        return []
    return [_aviso(
        "El importe de la dirección del QR no es el total de la factura con "
        f"IVA (BT-112), {cifras.en_castellano(en_la_factura)}.",
        cifras.tiene(en_la_factura), del_qr)]


def _de_la_aeat(pares, valores, nifs_del_vendedor, numero, fecha, total, moneda):
    incidencias: list[Incidencia] = []
    faltan = [p for p in _PARAMETROS_DE_LA_AEAT if not valores.get(p)]
    if faltan:
        incidencias.append(_aviso(
            "A la dirección del QR le faltan parámetros que la especificación de "
            "la AEAT hace obligatorios: el NIF, la serie y el número, la fecha y "
            "el importe. Sin ellos el servicio de cotejo devuelve un error.",
            ", ".join(_PARAMETROS_DE_LA_AEAT), "faltan " + ", ".join(faltan)))
    sobran = _sobrantes(pares, _PARAMETROS_DE_LA_AEAT)
    if sobran:
        porque = (" El de formato, la especificación dice que nunca puede ir en "
                  "el QR." if "formato" in sobran else "")
        incidencias.append(_aviso(
            "La dirección del QR lleva parámetros que no son de la "
            "especificación de la AEAT, que pide únicamente cuatro. Un & sin "
            "codificar dentro de la serie y el número también deja uno de sobra."
            + porque,
            ", ".join(_PARAMETROS_DE_LA_AEAT), ", ".join(sobran)))

    if nif_del_qr := valores.get("nif"):
        if not _NIF.fullmatch(nif_del_qr):
            incidencias.append(_aviso(
                "El NIF de la dirección del QR no tiene la forma de un NIF: nueve "
                "caracteres, sin prefijo de país.",
                "nueve caracteres", nif_del_qr))
        else:
            incidencias += _nif_contra(nif_del_qr, nifs_del_vendedor)

    if serie_y_numero := valores.get("numserie"):
        if len(serie_y_numero) > 60 or any(not 32 <= ord(c) <= 126 for c in serie_y_numero):
            incidencias.append(_aviso(
                "La serie y el número de la dirección del QR no cumplen la "
                "especificación de la AEAT: como mucho sesenta caracteres, y "
                "solo los imprimibles del ASCII.",
                "hasta sesenta caracteres ASCII imprimibles", serie_y_numero))
        if numero and serie_y_numero != numero:
            incidencias.append(_aviso(
                "La serie y el número de la dirección del QR no son los de la "
                "factura (BT-1).",
                numero, serie_y_numero))

    if escrita := valores.get("fecha"):
        trozos = _FECHA_AEAT.fullmatch(escrita)
        try:
            del_qr = date(int(trozos[3]), int(trozos[2]), int(trozos[1])) if trozos else None
        except ValueError:
            del_qr = None
        if del_qr is None:
            incidencias.append(_aviso(
                "La fecha de la dirección del QR no es una fecha con la forma "
                "que pide la AEAT, día, mes y año con guiones.",
                "DD-MM-AAAA", escrita))
        else:
            incidencias += _fecha_contra(del_qr, fecha)

    if importe := valores.get("importe"):
        if not _IMPORTE.fullmatch(importe):
            incidencias.append(_aviso(
                "El importe de la dirección del QR no tiene la forma que pide la "
                "AEAT: punto decimal, hasta doce cifras enteras y dos decimales.",
                "NNNNNNNNNNNN.DD", importe))
        else:
            incidencias += _total_contra(importe, total, moneda)
    return incidencias


def _de_ticketbai(direccion, pares, valores, nifs_del_vendedor, numero, fecha, total, moneda):
    incidencias: list[Incidencia] = []
    # La serie puede no existir en TicketBAI, y entonces s va vacío o no va.
    faltan = [p for p in _PARAMETROS_DE_TICKETBAI if p != "s" and not valores.get(p)]
    if faltan:
        incidencias.append(_aviso(
            "A la dirección del QR de TicketBAI le faltan parámetros: el "
            "identificador TBAI, el número, el importe y el CRC.",
            ", ".join(_PARAMETROS_DE_TICKETBAI), "faltan " + ", ".join(faltan)))
    sobran = _sobrantes(pares, _PARAMETROS_DE_TICKETBAI)
    if sobran:
        incidencias.append(_aviso(
            "La dirección del QR lleva parámetros que no son de la "
            "especificación de TicketBAI.",
            ", ".join(_PARAMETROS_DE_TICKETBAI), ", ".join(sobran)))

    # El CRC de la dirección va el último, y se calcula sobre todo lo que va
    # delante sin el &cr= que lo añade.
    if valores.get("cr"):
        antes, separador, cr = direccion.rpartition("&cr=")
        if not separador or "&" in cr:
            incidencias.append(_aviso(
                "El CRC de la dirección del QR de TicketBAI no va el último, "
                "como pide la especificación.",
                "...&cr=NNN al final", direccion))
        elif crc8(antes) != cr:
            incidencias.append(_aviso(
                "El CRC de la dirección del QR de TicketBAI no cuadra con la "
                "dirección: algo se cambió después de calcularlo, o se calculó "
                "sobre otra.",
                crc8(antes), cr))

    if identificador := valores.get("id"):
        trozos = _ID_TBAI.fullmatch(identificador)
        if not trozos:
            incidencias.append(_aviso(
                "El identificador TBAI de la dirección del QR no tiene su forma: "
                "TBAI, el NIF, la fecha, trece caracteres de la firma y el CRC, "
                "separados por guiones, treinta y nueve caracteres.",
                "TBAI-NNNNNNNNN-DDMMAA-FFFFFFFFFFFFF-CRC", identificador))
        else:
            if crc8(identificador[:36]) != trozos[6]:
                incidencias.append(_aviso(
                    "El CRC del identificador TBAI no cuadra con el resto del "
                    "identificador.",
                    crc8(identificador[:36]), trozos[6]))
            incidencias += _nif_contra(trozos[1], nifs_del_vendedor)
            try:
                del_qr = date(2000 + int(trozos[4]), int(trozos[3]), int(trozos[2]))
            except ValueError:
                del_qr = None
            if del_qr is None:
                incidencias.append(_aviso(
                    "La fecha del identificador TBAI no es una fecha.",
                    "DDMMAA", identificador))
            else:
                incidencias += _fecha_contra(del_qr, fecha)

    # BT-1 es la serie y el número juntos, sin separador: como lo contestó el
    # buzón de la AEAT el 13-10-2026, y como lo trata `codigo_unico`.
    if (numero_tbai := valores.get("nf")) and numero:
        del_qr = valores.get("s", "") + numero_tbai
        if del_qr != numero:
            incidencias.append(_aviso(
                "La serie y el número de la dirección del QR de TicketBAI, "
                "juntos, no son los de la factura (BT-1).",
                numero, del_qr))

    if importe := valores.get("i"):
        if not _IMPORTE.fullmatch(importe):
            incidencias.append(_aviso(
                "El importe de la dirección del QR de TicketBAI no es un importe "
                "con punto decimal.",
                "NNNN.DD", importe))
        else:
            incidencias += _total_contra(importe, total, moneda)
    return incidencias
