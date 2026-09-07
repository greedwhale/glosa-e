"""Validador de facturas desde la línea de órdenes.

    python -m validador factura.xml
    python -m validador facturas/
    python -m validador facturas/*.xml --hoy 2026-09-20

Devuelve 0 si todo está bien, 1 si hay algún error y 2 si no hay nada que
mirar. Así se puede encadenar en un script sin leer la salida.
"""

from __future__ import annotations

import argparse
import glob
import sys
from datetime import date, datetime, timezone
from pathlib import Path

from validador import bitacora, factura, paquete, tsl
from validador.cadena import Almacen
from validador.cadena import CARPETA_POR_DEFECTO as ANCLAS_POR_DEFECTO
from validador.cadena import SUFIJO_DE_SELLOS
from validador.cadena import VARIABLE_ENTORNO as ANCLAS_ENTORNO
from validador.esquema import CARPETA_POR_DEFECTO, VARIABLE_ENTORNO, Catalogo
from validador.incidencias import ERROR
from validador.revocacion import CARPETA_POR_DEFECTO as LISTAS_POR_DEFECTO
from validador.revocacion import VARIABLE_ENTORNO as LISTAS_ENTORNO
from validador.revocacion import AlmacenDeListas

# Las extensiones que se recogen al apuntar a una carpeta. Sin las de EDIFACT,
# apuntar a una carpeta con facturas EDIFACT dentro las saltaba **en
# silencio** y el resumen contaba solo las que si habia mirado, que es la
# forma de dejar a alguien creyendo que ha revisado un lote entero.
#
# `.txt` no entra, aunque tambien haya EDIFACT que viaje asi: una carpeta de
# facturas suele tener ademas un leeme o unas notas, y recogerlos llenaria el
# informe de «formato no reconocido» sobre ficheros que nadie dijo que fueran
# facturas. Un `.txt` que si lo sea se valida nombrandolo: un fichero pedido
# por su nombre se lee siempre, tenga la extension que tenga.
EXTENSIONES = (".xml", ".xsig", ".edi", ".edifact")


def _fecha(texto: str) -> date:
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"«{texto}» no es una fecha. Se espera AAAA-MM-DD."
        ) from None


def expandir(patrones: list[str]) -> list[Path]:
    """Convierte lo que venga en una lista de ficheros.

    Se aceptan ficheros sueltos, carpetas y comodines. Los comodines se
    expanden aquí porque la consola de Windows, a diferencia de la de Unix, no
    lo hace por su cuenta.
    """
    caminos: list[Path] = []
    for patron in patrones:
        camino = Path(patron)
        if camino.is_dir():
            caminos.extend(
                sorted(
                    hijo
                    for hijo in camino.iterdir()
                    if hijo.suffix.lower() in EXTENSIONES
                )
            )
        elif camino.exists():
            caminos.append(camino)
        else:
            encontrados = sorted(Path(p) for p in glob.glob(patron))
            # Si el comodín no casa con nada, se deja tal cual para que el
            # informe diga «no existe» en vez de callarse.
            caminos.extend(encontrados or [camino])
    return caminos


def main(argumentos: list[str] | None = None) -> int:
    analizador = argparse.ArgumentParser(
        prog="python -m validador",
        description=(
            "Valida facturas electrónicas contra la norma europea EN 16931 y "
            "contra las reglas españolas del RD 238/2026."
        ),
    )
    analizador.add_argument(
        "rutas",
        # Cero permitido a proposito: `--ver-anclas` no valida nada y pedirle
        # un fichero para poder mirar el almacen seria absurdo. Sin ficheros y
        # sin --ver-anclas se sale con 2, que es lo que ya hacia.
        nargs="*",
        metavar="FICHERO",
        help="ficheros, carpetas o comodines",
    )
    analizador.add_argument(
        "--hoy",
        type=_fecha,
        metavar="AAAA-MM-DD",
        help="fecha desde la que se juzga si una factura es futura o está "
        "prescrita. Por defecto, hoy.",
    )
    analizador.add_argument(
        "--esquemas",
        metavar="CARPETA",
        help="carpeta con los esquemas XSD oficiales, para comprobar también "
        f"la forma. Por defecto, la variable de entorno {VARIABLE_ENTORNO} "
        f"o ./{CARPETA_POR_DEFECTO}.",
    )
    analizador.add_argument(
        "--anclas",
        metavar="CARPETA",
        help="carpeta con los certificados raiz de las autoridades en las que "
        "confias, para comprobar tambien de quien es la firma. Por defecto, la "
        f"variable de entorno {ANCLAS_ENTORNO} o ./{ANCLAS_POR_DEFECTO}.",
    )
    analizador.add_argument(
        "--ver-anclas",
        action="store_true",
        help="enseña las anclas instaladas con su huella y cuando caducan, y "
        "no valida nada. La huella es lo que permite contrastar cada ancla con "
        "la que publica su autoridad, sin fiarse de por donde llego el fichero.",
    )
    analizador.add_argument(
        "--revocaciones",
        metavar="CARPETA",
        help="carpeta con las listas de revocacion (CRL) de esas autoridades, "
        "para comprobar tambien si el certificado esta anulado. Por defecto, la "
        f"variable de entorno {LISTAS_ENTORNO} o ./{LISTAS_POR_DEFECTO}. "
        "Bajarlas es cosa tuya: este programa no abre ninguna conexion.",
    )
    analizador.add_argument(
        "--ver-revocaciones",
        action="store_true",
        help="enseña las listas de revocacion instaladas, de que autoridad son "
        "y hasta cuando valen, y no valida nada.",
    )
    analizador.add_argument(
        "--ver-tsl",
        metavar="FICHERO",
        help="enseña lo que dice una lista de confianza (TSL) sin montar nada: "
        "de quien es, de cuando, y cuantas autoridades trae concedidas y "
        "retiradas.",
    )
    analizador.add_argument(
        "--montar-anclas",
        metavar="FICHERO",
        help="monta la carpeta de anclas a partir de una lista de confianza "
        "(TSL). Hay que decir quien tenia que firmarla con --firmante: de una "
        "lista sin comprobar no se monta nada.",
    )
    analizador.add_argument(
        "--firmante",
        metavar="HUELLA",
        action="append",
        help="la huella SHA-256 del certificado que tenia que firmar la lista. "
        "Para la lista de listas europea (LOTL) esta publicada en el Diario "
        "Oficial de la UE; para la de un pais, en la LOTL. Se puede repetir: el "
        "Diario Oficial publica seis certificados a la vez, cualquiera de los "
        "cuales puede ser el que este firmando hoy.",
    )
    analizador.add_argument(
        "--segun",
        metavar="LOTL",
        help="saca de esta lista de listas quien puede firmar la que se monta, "
        "en vez de escribir la huella a mano. La LOTL hay que comprobarla "
        "tambien: --firmante se aplica entonces a ella.",
    )
    analizador.add_argument(
        "--en",
        metavar="CARPETA",
        help="donde escribir las anclas montadas. Por defecto, la misma que "
        "usaria --anclas.",
    )
    analizador.add_argument(
        "--empaquetar",
        metavar="FICHERO",
        nargs="?",
        const="web/paquete.zip",
        help="arma el paquete que la pagina web necesita para comprobar las "
        "tres cosas: los esquemas XSD y las anclas de confianza, en un solo "
        "zip. Sin el, la pagina solo comprueba el contenido. No se empaquetan "
        "anclas sin manifiesto ni anclas cuya lista debia haberse renovado.",
    )
    analizador.add_argument(
        "--aunque-esten-vencidas",
        action="store_true",
        help="empaqueta las anclas aunque su lista de confianza debiera "
        "haberse renovado ya. Para probar, no para repartir.",
    )
    analizador.add_argument(
        "--sitio",
        metavar="CARPETA",
        nargs="?",
        const="sitio",
        help="monta en CARPETA lo que hay que publicar y nada mas: la pagina, "
        "el wheel con su rueda.json, las facturas de ejemplo y el paquete de "
        "esquemas y anclas si esta armado. No sube el repositorio entero, que "
        "lleva facturas de terceros y anclas sueltas.",
    )
    analizador.add_argument(
        "--exigir-paquete",
        action="store_true",
        help="con --sitio, se niega a montar si no esta el paquete de "
        "esquemas y anclas, o si esta vacio. Sin esta bandera se monta igual y "
        "se avisa por pantalla, que es lo que hace falta en local; con ella no "
        "se monta, que es lo que hace falta al publicar, donde el aviso no lo "
        "lee nadie y lo unico que se mira es el codigo de salida.",
    )
    analizador.add_argument(
        "--traer-pyodide",
        metavar="CARPETA",
        nargs="?",
        const=paquete.CARPETA_DE_PYODIDE,
        help="baja el interprete de Python para WebAssembly y lo deja en "
        "CARPETA, para servirlo desde el propio sitio en vez de pedirselo a un "
        "CDN ajeno en cada visita. Son unos 8 MB y se baja una vez.",
    )
    analizador.add_argument(
        "--solo-errores",
        action="store_true",
        help="calla los avisos y deja solo lo que impide cobrar",
    )
    opciones = analizador.parse_args(argumentos)

    almacen = Almacen.por_defecto(opciones.anclas)
    listas = AlmacenDeListas.por_defecto(opciones.revocaciones)
    if opciones.ver_tsl:
        return _ver_tsl(Path(opciones.ver_tsl), opciones.hoy or date.today())
    if opciones.montar_anclas:
        return _montar_anclas(
            Path(opciones.montar_anclas),
            Path(opciones.segun) if opciones.segun else None,
            opciones.firmante,
            Path(opciones.en) if opciones.en else almacen.carpeta,
            opciones.hoy or date.today(),
        )
    if opciones.ver_anclas:
        return _ver_anclas(almacen, opciones.hoy or date.today())
    if opciones.ver_revocaciones:
        return _ver_revocaciones(listas, opciones.hoy or date.today())
    if opciones.traer_pyodide:
        return _traer_pyodide(Path(opciones.traer_pyodide))
    if opciones.sitio:
        return _montar_sitio(Path(opciones.sitio), opciones.exigir_paquete)
    if opciones.empaquetar:
        return _empaquetar(
            Path(opciones.empaquetar),
            opciones.esquemas,
            almacen.carpeta,
            opciones.hoy or date.today(),
            opciones.aunque_esten_vencidas,
        )

    caminos = expandir(opciones.rutas)
    if not caminos:
        print("No hay ningún fichero que mirar.", file=sys.stderr)
        return 2

    catalogo = Catalogo.por_defecto(opciones.esquemas)
    lote = factura.validar_lote(
        caminos,
        hoy=opciones.hoy,
        catalogo=catalogo,
        almacen=almacen,
        listas=listas,
    )
    if opciones.solo_errores:
        for _, informe in lote.informes:
            informe.incidencias = informe.errores
        lote.cruzadas = [i for i in lote.cruzadas if i.gravedad == ERROR]

    print(
        lote.detalle(
            forma=not catalogo.vacio,
            anclas=not almacen.vacio,
            listas=not listas.vacio,
        )
    )
    if catalogo.vacio:
        # Una sola línea al final, no un aviso por fichero: quien no tiene los
        # esquemas puestos ya lo sabe, y no hace falta repetírselo cien veces.
        print()
        print(
            f"No se ha comprobado la forma: no hay esquemas XSD en "
            f"{catalogo.carpeta}. El README dice de dónde bajarlos."
        )
    if almacen.vacio and lote.firmados:
        # Solo si hay algo firmado: sobre un lote sin firmas, echar de menos
        # las anclas seria hablar de algo que no viene al caso.
        print(
            f"No se ha comprobado de quién son las firmas: no hay anclas de "
            f"confianza en {almacen.carpeta}. El README dice cómo ponerlas."
        )
    elif listas.vacio and lote.firmados:
        # Solo cuando las anclas si estan: sin ellas no se llega ni a saber de
        # quien es el certificado, y echar de menos su lista de revocacion
        # seria pedir el segundo paso antes que el primero.
        print(
            f"No se ha comprobado si los certificados están anulados: no hay "
            f"listas de revocación en {listas.carpeta}. El informe de cada "
            "factura dice de dónde bajar la que le falta."
        )
    return 0 if lote.conforme else 1


# Por debajo de esto, un ancla se considera «a punto de caducar». Tres meses es
# tiempo de sobra para conseguir la nueva sin prisas, y lo bastante poco como
# para que el aviso no sea permanente.
DIAS_DE_AVISO = 90

# Para ordenar por caducidad cuando alguna no se ha podido leer. Va con
# zona horaria porque las del certificado la llevan, y Python se niega a
# comparar una fecha con hora con otra sin ella: sin esto, un ancla con la
# fecha ilegible reventaba el listado a media impresion.
_ETERNO = datetime.max.replace(tzinfo=timezone.utc)


def _empaquetar(
    destino: Path, esquemas, anclas: Path, hoy: date, aunque_vencidas: bool
) -> int:
    """Arma el zip que la página se lleva puesto, o se niega y dice por qué.

    Las dos negativas —sin manifiesto y sin renovar— salen por aquí en vez de
    por una traza, porque son la parte que importa: no son fallos técnicos
    sino la razón por la que ese paquete no se puede repartir.
    """
    from validador.esquema import CARPETA_POR_DEFECTO as ESQUEMAS_POR_DEFECTO

    try:
        contenido = paquete.armar(
            destino,
            esquemas=esquemas or ESQUEMAS_POR_DEFECTO,
            anclas=anclas,
            hoy=hoy,
            aunque_esten_vencidas=aunque_vencidas,
        )
    except (paquete.SinManifiesto, paquete.SinRenovar) as motivo:
        print(f"No se ha empaquetado nada.\n\n  {motivo}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"No se ha podido escribir {destino}: {error}", file=sys.stderr)
        return 2

    print(f"Escrito {destino} ({contenido.bytes / 1024 / 1024:.2f} MB)")
    print(f"  SHA-256  {contenido.huella}")
    print()
    print(f"  esquemas XSD          {contenido.esquemas}")
    print(f"  anclas de firma       {contenido.anclas}")
    print(f"  anclas de sellado     {contenido.anclas_de_sellos}")
    print()
    print(f"  {contenido.declarada}")
    print(f"  montadas el {contenido.montada or '(no consta)'}, "
          f"la lista se renueva el {contenido.siguiente or '(no dice)'}")
    if contenido.siguiente:
        quedan = (date.fromisoformat(contenido.siguiente) - hoy).days
        # El aviso va aquí y no solo al validar porque quien arma el paquete es
        # quien puede arreglarlo, y porque el paquete va a estar sirviéndose
        # meses: lo que hoy vence dentro de tres semanas, en la página vence.
        if quedan <= DIAS_DE_AVISO:
            print(
                f"\n  Ojo: quedan {quedan} días. Cuando pase esa fecha, la "
                "página seguirá creyendo a autoridades que quizá ya no lo "
                "sean, y lo dirá en cada informe. Vuelve a montar las anclas "
                "y a empaquetar antes."
            )
    return 0


def _traer_pyodide(destino: Path) -> int:
    """Baja el intérprete que se sirve con la página.

    Se baja aquí, al construir, y no en el navegador de quien visita: que este
    ordenador hable con el CDN no le importa a nadie; que hable el navegador de
    un desconocido, sí, porque le lleva su IP a un tercero antes de que haya
    hecho nada.
    """
    try:
        traidos = paquete.traer_pyodide(destino)
    except OSError as error:
        print(
            f"No se ha podido traer el intérprete: {error}\n\n  Hace falta "
            "conexión, y solo esta vez: después se sirve desde el sitio.",
            file=sys.stderr,
        )
        return 2

    pesa = sum(f.stat().st_size for f in destino.rglob("*") if f.is_file())
    if traidos:
        print(f"Traídos {len(traidos)} fichero(s) a {destino}.")
    else:
        print(f"Ya estaban todos en {destino}.")
    print(f"  Pyodide {paquete.VERSION_DE_PYODIDE}, {pesa / 1024 / 1024:.2f} MB")
    print(f"  Huellas en {destino / paquete.NOMBRE_DE_HUELLAS}")
    return 0


def _montar_sitio(destino: Path, exigir_paquete: bool = False) -> int:
    """Deja listo lo que se sube, y dice si va completo o cojo.

    El aviso de que falta el paquete no es decorativo: un sitio sin esquemas ni
    anclas arranca, valida y no comprueba ni la forma ni de quién es la firma.
    La página lo dice en su recuadro, pero quien publica se entera aquí, que es
    cuando todavía puede armarlo.

    Y avisar no basta cuando quien monta no es una persona. La construcción de
    Vercel corre esto y lo único que mira es el código de salida, así que un
    aviso perfecto por pantalla y un `return 0` publican el sitio cojo igual.
    Por eso el despliegue pasa `--exigir-paquete` y entonces esto **se niega**:
    es la misma diferencia que hay entre un comentario que pide memoria y un
    guardián que no deja montar.
    """
    try:
        sitio = paquete.montar_sitio(destino, exigir_paquete=exigir_paquete)
    except (paquete.SinRueda, paquete.SinPagina, paquete.SinPyodide,
            paquete.RuedaVieja, paquete.SinPaquete,
            bitacora.SinEntrada) as motivo:
        print(f"No se ha montado nada.\n\n  {motivo}", file=sys.stderr)
        return 2
    except OSError as error:
        print(f"No se ha podido montar {destino}: {error}", file=sys.stderr)
        return 2

    print(f"Montado {sitio.carpeta} ({sitio.bytes / 1024 / 1024:.2f} MB)")
    print()
    print(f"  validador             {sitio.rueda}")
    print(f"  facturas de ejemplo   {sitio.ejemplos}")
    if sitio.con_paquete:
        print("  esquemas y anclas     van dentro")
    else:
        print("  esquemas y anclas     NO VAN")
        print()
        print(
            "  Este sitio arranca y valida el contenido, pero no comprueba ni "
            "la\n  forma ni de quién es la firma, y lo dirá en cada informe. "
            "Ármalo\n  antes con `python -m validador --empaquetar`."
        )
    return 0


def _ver_anclas(almacen, hoy: date) -> int:
    """Las anclas instaladas, con su huella y su caducidad.

    La huella es para contrastarlas con lo que publica su autoridad; la
    caducidad es la respuesta a «¿y esto hay que mantenerlo?». Las raíces duran
    veinte o treinta años y las intermedias mucho menos: lo que hay que vigilar
    es cuál se apaga, y para eso hay que poder verlo de un vistazo.
    """
    if almacen.vacio:
        print(f"No hay ninguna ancla de confianza en {almacen.carpeta}.")
        return 2
    print(f"Anclas de confianza en {almacen.carpeta}:")
    if almacen.declarada:
        # Si la carpeta la montó `--montar-anclas`, dice de dónde salió. Es la
        # misma línea que acaba en el informe de cada factura, y aquí sirve
        # para lo contrario: saber qué hay instalado antes de validar nada.
        print(f"  ({almacen.declarada})")
    print()
    caducando = 0
    for cert in sorted(almacen.todas(), key=lambda c: c.hasta or _ETERNO):
        print(f"  {cert.sujeto or '(sin nombre común)'}")
        print(f"    SHA-256  {cert.huella()}")
        if cert.hasta is None:
            print("    caduca   (no se ha podido leer)")
            continue
        quedan = (cert.hasta.date() - hoy).days
        if quedan < 0:
            print(f"    caduca   {cert.hasta.date().isoformat()}  ¡YA CADUCADA!")
            caducando += 1
        elif quedan <= DIAS_DE_AVISO:
            print(
                f"    caduca   {cert.hasta.date().isoformat()}  "
                f"(quedan {quedan} días)"
            )
            caducando += 1
        else:
            print(f"    caduca   {cert.hasta.date().isoformat()}")
    for ruta, motivo in almacen.ilegibles:
        print(f"  (no se ha podido leer {ruta}: {motivo})")
    print()
    print(
        "Contrasta cada huella con la que publica su autoridad antes de "
        "fiarte de ella."
    )
    if caducando:
        print(
            f"Hay {caducando} ancla(s) caducada(s) o a punto: consigue la nueva "
            "en la web de su autoridad y comprueba su huella allí mismo."
        )
    return 0


def _ver_revocaciones(listas, hoy: date) -> int:
    """Las listas de revocación instaladas y hasta cuándo valen.

    Una lista vencida no es inútil —lo que dice, dicho está—, pero deja de
    poder decir «este certificado no está anulado», que es para lo que se
    consulta el 99% de las veces.
    """
    if listas.vacio:
        print(f"No hay ninguna lista de revocación en {listas.carpeta}.")
        print()
        print(
            "Se bajan de la dirección que da cada certificado, y el informe de "
            "cada factura la dice. Este programa no las baja solo."
        )
        return 2
    print(f"Listas de revocación en {listas.carpeta}:")
    print()
    vencidas = 0
    for una in sorted(listas.todas(), key=lambda l: l.emisor_nombre or ""):
        print(f"  {una.emisor_nombre or '(sin nombre común)'}")
        print(f"    anulados  {len(una.anulaciones)}")
        print(
            f"    publicada {una.desde.date().isoformat() if una.desde else '?'}"
        )
        if una.hasta is None:
            print("    vale      (sin fecha de caducidad)")
        elif una.hasta.date() < hoy:
            print(f"    vale      hasta {una.hasta.date().isoformat()}  ¡VENCIDA!")
            vencidas += 1
        else:
            print(f"    vale      hasta {una.hasta.date().isoformat()}")
        if una.es_delta:
            print("    aviso     es incremental: no sirve para dar por vigente")
    for ruta, motivo in listas.ilegibles:
        print(f"  (no se ha podido leer {ruta}: {motivo})")
    if vencidas:
        print()
        print(
            f"Hay {vencidas} lista(s) vencida(s). Mientras no las renueves, no "
            "aparecer en ellas no demuestra que un certificado siga vigente."
        )
    return 0


def _lista_de_confianza(ruta: Path):
    """Abre una TSL de disco, o dice por qué no. Devuelve (lista, motivo)."""
    try:
        datos = ruta.read_bytes()
    except OSError as error:
        return None, f"no se ha podido leer {ruta}: {error}"
    try:
        return tsl.leer(datos), ""
    except Exception as error:  # lxml lanza de todo ante un fichero que no lo es
        return None, f"{ruta} no parece una lista de confianza: {error}"


def _ver_tsl(ruta: Path, hoy: date) -> int:
    """Qué dice una lista de confianza, sin montar nada con ella.

    Aquí **no se comprueba la firma** y se dice: mirar una lista es una cosa y
    creérsela es otra, y confundirlas es exactamente el fallo del que va este
    módulo. Para lo segundo está `--montar-anclas`, que sin firmante se niega.
    """
    lista, motivo = _lista_de_confianza(ruta)
    if lista is None:
        print(motivo, file=sys.stderr)
        return 2

    print(f"Lista de confianza en {ruta}:")
    print()
    print(f"  territorio  {lista.territorio or '(no dice)'}")
    print(f"  operador    {lista.operador or '(no dice)'}")
    print(f"  secuencia   {lista.secuencia or '(no dice)'}")
    print(
        f"  publicada   "
        f"{lista.emitida.date().isoformat() if lista.emitida else '(no dice)'}"
    )
    siguiente = lista.siguiente.date().isoformat() if lista.siguiente else None
    vencida = lista.siguiente is not None and lista.siguiente.date() < hoy
    print(
        f"  siguiente   {siguiente or '(no dice)'}"
        + ("  ¡VENCIDA!" if vencida else "")
    )
    print()

    if lista.es_lista_de_listas:
        # Esto es lo que evita escribir de memoria la dirección de un país: la
        # dice la propia lista de listas, que es quien tiene autoridad para
        # decirla. La del ministerio español, sin ir más lejos, ha cambiado.
        print(f"Es una lista de listas: apunta a {len(lista.punteros)} más.")
        print()
        for puntero in sorted(lista.punteros, key=lambda p: p.territorio):
            print(f"  {puntero.territorio or '??'}  {puntero.donde}")
            print(
                f"      la pueden firmar {len(puntero.firmantes)} certificado(s)"
            )
        print()
        print(
            "Para montar las anclas de un país: --montar-anclas su.xml "
            f"--segun {ruta} --firmante <huella de quien firma esta>."
        )
        return 0

    resumen = tsl.cuentas(lista)
    print(f"Servicios que emiten certificados cualificados: "
          f"{resumen.servicios_mirados}")
    print(f"  concedidos       {resumen.concedidos}")
    print(f"  retirados        {resumen.retirados}")
    print(f"  sin certificado  {resumen.sin_certificado}")
    print(f"  no utilizables   {resumen.no_usables}")
    for cual, cuantos in resumen.motivos:
        print(f"     {cuantos:>4}  {cual}")
    print()
    print(f"  anclas que saldrían: {resumen.escritas}")
    print()

    retirados = [
        s
        for s in lista.servicios
        if s.emite_cualificados and not s.concedido
    ]
    if retirados:
        print("Retirados —no se instalan, y las facturas que firmaron antes de")
        print("retirarse eran buenas—:")
        for uno in sorted(retirados, key=lambda s: s.desde or _ETERNO):
            cuando = uno.desde.date().isoformat() if uno.desde else "?"
            print(f"  {cuando}  {uno.estado_corto:12} {uno.prestador or uno.nombre}")
        print()
    print(
        "La firma de esta lista no se ha comprobado aquí: mirarla es una cosa "
        "y creérsela es otra. Para lo segundo, --montar-anclas."
    )
    return 0


def _montar_anclas(
    ruta: Path,
    segun: Path | None,
    huella: list[str] | None,
    destino: Path,
    hoy: date,
) -> int:
    """Monta la carpeta de anclas desde una lista de confianza comprobada.

    Todo el rigor está en decidir **contra qué** se comprueba la firma. Sin esa
    parte esto sería bajarse un fichero de internet y creerle la lista de en
    quién confiar a quien contestara al DNS.
    """
    lista, motivo = _lista_de_confianza(ruta)
    if lista is None:
        print(motivo, file=sys.stderr)
        return 2

    if segun is not None:
        if not huella:
            print(
                "Falta --firmante. La lista de listas también hay que "
                "comprobarla: si te la crees porque sí, lo que has hecho es "
                "elegir en quién confiar a partir de un fichero que no has "
                "verificado.\n"
                "Su huella se publica en el Diario Oficial de la UE; el README "
                "dice en qué documento.",
                file=sys.stderr,
            )
            return 2
        madre, motivo = _lista_de_confianza(segun)
        if madre is None:
            print(motivo, file=sys.stderr)
            return 2
        fallo = tsl.comprobar_firma(madre, huella)
        if fallo:
            print(f"No me creo {segun}: {fallo}.", file=sys.stderr)
            return 1
        puntero = madre.puntero_de(lista.territorio)
        if puntero is None:
            cual = lista.territorio or "(sin territorio)"
            print(
                f"{segun} no dice nada de «{cual}», así que no puede decir "
                "quién firma su lista.",
                file=sys.stderr,
            )
            return 1
        esperados = list(puntero.firmantes)
        print(
            f"{segun} está comprobada, y dice que la lista de "
            f"{lista.territorio} la firma uno de {len(esperados)} certificado(s)."
        )
    elif huella:
        esperados = list(huella)
    else:
        print(
            "Falta decir quién tenía que firmar la lista, y sin eso no se monta "
            "nada: verificarla contra el certificado que ella misma trae dentro "
            "no demuestra nada, porque cualquiera firma su propia lista.\n"
            "  --firmante HUELLA   la huella SHA-256 de quien la firma\n"
            "  --segun LOTL        sacarla de la lista de listas europea\n"
            "El README dice de dónde sale cada una.",
            file=sys.stderr,
        )
        return 2

    fallo = tsl.comprobar_firma(lista, esperados)
    if fallo:
        print(f"No me creo {ruta}: {fallo}.", file=sys.stderr)
        return 1

    if not tsl.anclas_de(lista) and not tsl.anclas_de(
        lista, tsl.TIPOS_QUE_SELLAN
    ):
        print(
            f"{ruta} está comprobada, pero no trae ninguna autoridad "
            "cualificada concedida, ni de certificación ni de sellado: no hay "
            "anclas que montar.",
            file=sys.stderr,
        )
        return 2

    resumen = tsl.montar(lista, destino, cuando=datetime.now(timezone.utc))
    print(f"Comprobada la firma de {ruta}.")
    print(f"  la firmó   {lista.firmante.sujeto or '(sin nombre común)'}")
    print(f"  huella     {lista.firmante.huella()}")
    print()
    print(f"Montadas {resumen.escritas} anclas en {destino}.")
    print(
        f"  de {resumen.servicios_mirados} servicios: {resumen.concedidos} "
        f"concedidos, {resumen.retirados} retirados (fuera), "
        f"{resumen.sin_certificado} sin certificado (fuera)."
    )
    if resumen.motivos:
        # Esto no se puede callar en el resumen. Que 46 autoridades
        # cualificadas se queden fuera porque el corto es este validador es
        # una noticia distinta de que se queden fuera las retiradas, y quien
        # monta el conjunto tiene que enterarse sin abrir el manifiesto.
        print(
            f"  {resumen.no_usables} traen certificado y no sabemos usarlo, "
            "y siguen siendo autoridades cualificadas:"
        )
        for cual, cuantos in resumen.motivos:
            print(f"     {cuantos:>4}  {cual}")
    if lista.siguiente is not None and lista.siguiente.date() < hoy:
        print()
        print(
            f"Ojo: esta lista prometía volver a publicarse el "
            f"{lista.siguiente.date().isoformat()} y ya ha pasado. Lo que dice "
            "sigue siendo cierto de aquel día; lo que haya cambiado desde "
            "entonces no está aquí."
        )
    # Y las de sellado, que van en la carpeta hermana. Se montan aquí y no
    # con otra orden porque salen de la misma lista y del mismo momento: dos
    # órdenes serían dos conjuntos con dos fechas, y una que se olvida.
    sellado = destino.parent / (destino.name + SUFIJO_DE_SELLOS)
    de_sellado = tsl.montar(
        lista, sellado, tsl.TIPOS_QUE_SELLAN, cuando=datetime.now(timezone.utc)
    )
    print()
    print(f"Montadas {de_sellado.escritas} anclas de sellado en {sellado}.")
    print(
        f"  de {de_sellado.servicios_mirados} servicios de sellado: "
        f"{de_sellado.concedidos} concedidos, {de_sellado.retirados} "
        f"retirados (aparte)."
    )
    print(
        "  van en otra carpeta a propósito: una autoridad cualificada solo "
        "para sellar el tiempo no avala la firma de una factura."
    )

    print()
    print(
        f"El porqué de cada cosa queda en {destino / tsl.NOMBRE_DEL_MANIFIESTO}, "
        "y su primera línea es la que sale en el informe de cada factura."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
