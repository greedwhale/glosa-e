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
from datetime import date, datetime
from pathlib import Path

from validador import factura
from validador.cadena import Almacen
from validador.cadena import CARPETA_POR_DEFECTO as ANCLAS_POR_DEFECTO
from validador.cadena import VARIABLE_ENTORNO as ANCLAS_ENTORNO
from validador.esquema import CARPETA_POR_DEFECTO, VARIABLE_ENTORNO, Catalogo
from validador.incidencias import ERROR
from validador.revocacion import CARPETA_POR_DEFECTO as LISTAS_POR_DEFECTO
from validador.revocacion import VARIABLE_ENTORNO as LISTAS_ENTORNO
from validador.revocacion import AlmacenDeListas

EXTENSIONES = (".xml", ".xsig")


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
        "--solo-errores",
        action="store_true",
        help="calla los avisos y deja solo lo que impide cobrar",
    )
    opciones = analizador.parse_args(argumentos)

    almacen = Almacen.por_defecto(opciones.anclas)
    listas = AlmacenDeListas.por_defecto(opciones.revocaciones)
    if opciones.ver_anclas:
        return _ver_anclas(almacen, opciones.hoy or date.today())
    if opciones.ver_revocaciones:
        return _ver_revocaciones(listas, opciones.hoy or date.today())

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
    print()
    caducando = 0
    for cert in sorted(almacen.todas(), key=lambda c: c.hasta or datetime.max.date()):
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


if __name__ == "__main__":
    sys.exit(main())
