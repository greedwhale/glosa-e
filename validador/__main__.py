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
from validador.esquema import CARPETA_POR_DEFECTO, VARIABLE_ENTORNO, Catalogo
from validador.incidencias import ERROR

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
        nargs="+",
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
        "--solo-errores",
        action="store_true",
        help="calla los avisos y deja solo lo que impide cobrar",
    )
    opciones = analizador.parse_args(argumentos)

    caminos = expandir(opciones.rutas)
    if not caminos:
        print("No hay ningún fichero que mirar.", file=sys.stderr)
        return 2

    catalogo = Catalogo.por_defecto(opciones.esquemas)
    lote = factura.validar_lote(caminos, hoy=opciones.hoy, catalogo=catalogo)
    if opciones.solo_errores:
        for _, informe in lote.informes:
            informe.incidencias = informe.errores
        lote.cruzadas = [i for i in lote.cruzadas if i.gravedad == ERROR]

    print(lote.detalle(forma=not catalogo.vacio))
    if catalogo.vacio:
        # Una sola línea al final, no un aviso por fichero: quien no tiene los
        # esquemas puestos ya lo sabe, y no hace falta repetírselo cien veces.
        print()
        print(
            f"No se ha comprobado la forma: no hay esquemas XSD en "
            f"{catalogo.carpeta}. El README dice de dónde bajarlos."
        )
    return 0 if lote.conforme else 1


if __name__ == "__main__":
    sys.exit(main())
