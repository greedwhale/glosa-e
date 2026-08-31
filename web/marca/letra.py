# -*- coding: utf-8 -*-
"""Genera la Literata que sirve la página, y le pone la huella al CSS.

Por qué existe
--------------
La marca es Literata 400 desde `trazar.py`, pero va **trazada a contornos**: no
viaja ningún fichero de letra. El texto de al lado se componía con `--serif`,
que era una lista de respaldos —Iowan, Palatino, Georgia—, así que en una
máquina Windows el titular junto a la marca salía en Georgia. Marca y titular,
dos letras distintas, a dos centímetros.

Esto sirve Literata de verdad, **desde el propio dominio**. El comentario de
`glosa.css` objetaba pedirle la letra a un servidor ajeno, y tiene toda la
razón: eso contradiría en la primera línea del HTML la promesa de que el
fichero no sale del ordenador. Servirla desde `glosa-e` no la contradice —sigue
siendo cero peticiones a terceros, que es lo que la política de privacidad
publica medido— y son 49 KB al lado de los nueve megas de intérprete.

Las decisiones, con su número
-----------------------------
- **`opsz` fijado en 12, no variable.** Dejar el eje óptico abierto costaba
  109,4 KB frente a 49,1: más del doble, para un eje que aquí no se usa —la
  serif compone dos cosas, el lema y los títulos de sección—. Y 12 no es un
  número cualquiera: es exactamente el que usa `trazar.py` para la marca, así
  que el titular y el logotipo salen de la misma forma de letra.
- **`wght` de 400 a 600, variable.** 400 para el lema y los títulos, 600 para
  lo destacado. Un estático de 400 pesaría 28,0 KB; los 21 KB de diferencia
  compran el peso intermedio sin un segundo fichero.
- **Solo la serif.** El cuerpo, los datos y el informe siguen en la `--sans`
  del sistema, que es lo que ya estaba diseñado: una herramienta de
  cumplimiento se lee en tablas, y una serif de 16 px en una tabla densa se lee
  peor. La serif es la voz, no el vehículo.

La licencia viaja al lado
-------------------------
Literata está bajo SIL Open Font License 1.1, que permite expresamente
incrustarla, redistribuirla y venderla, y **exige que la licencia acompañe al
Font Software**. Por eso este script copia `OFL.txt` junto al `.woff2` y
`paquete.py` lo publica: sin él, el sitio estaría incumpliendo la única
condición que la licencia pone.

Cómo se usa
-----------
    curl -L -o Literata.ttf \\
      "https://raw.githubusercontent.com/google/fonts/main/ofl/literata/Literata%5Bopsz,wght%5D.ttf"
    curl -L -o OFL.txt \\
      "https://raw.githubusercontent.com/google/fonts/main/ofl/literata/OFL.txt"
    python web/marca/letra.py Literata.ttf OFL.txt

Deja `web/letra/literata.woff2`, `web/letra/OFL.txt` y el `@font-face` de
`glosa.css` apuntando a la huella nueva. Es idempotente: correrlo dos veces
sobre la misma fuente deja el mismo fichero y el mismo CSS.
"""
from __future__ import annotations

import hashlib
import io
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "web" / "letra"
DESTINO = CARPETA / "literata.woff2"
LICENCIA = CARPETA / "OFL.txt"
ESTILO = RAIZ / "web" / "glosa.css"

EJE_OPTICO = 12          # el mismo que la marca en `trazar.py`
PESO_MINIMO = 400
PESO_MAXIMO = 600

# El «latin» de Google Fonts, más lo que escribe este validador: comillas
# angulares, rayas, puntos suspensivos, el euro y las flechas de la página.
# Se fija una lista y no «lo que use el HTML de hoy» a propósito: el informe
# compone texto que sale de la factura de quien valida, y ahí puede aparecer
# cualquier cosa. Un carácter que falte no da error, da un hueco.
UNICODES = (
    "0000-00FF,0131,0152-0153,02BB-02BC,02C6,02DA,02DC,0304,0308,0329,"
    "2000-206F,2074,20AC,2122,2191,2193,2212,2215,FEFF,FFFD"
)

# La línea del CSS que hay que dejar apuntando a la huella de ahora. Si alguien
# la reescribe de otra forma, esto se para en vez de dejar un `@font-face`
# apuntando a un fichero que ya no existe —que no da error: da la letra del
# sistema y nadie se entera—.
PATRON_SRC = re.compile(r'(src:\s*url\("\./letra/literata\.woff2)(\?v=[0-9a-f]+)?(")')


def generar(ruta_fuente: Path) -> bytes:
    """Subconjunto e instancia, en ese orden y no al revés.

    Al revés revienta: instanciar primero y subconjuntar después hace que
    fontTools se caiga con `KeyError: 'triagdn'` al recortar `gvar`. Costó un
    rato encontrarlo y no se deduce de nada, así que queda escrito.
    """
    from fontTools.subset import Options, Subsetter, parse_unicodes
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    # `recalcTimestamp=False` no es un detalle: sin él, fontTools pone en
    # `head.modified` la hora de ahora, así que dos pasadas sobre la misma
    # fuente dan dos ficheros distintos y dos huellas distintas. El CSS
    # cambiaría en cada regeneración sin que la letra haya cambiado, y una
    # huella que se mueve sola deja de significar «esto es otro fichero».
    # Medido: 50.376 bytes y la misma huella en tres pasadas, con esto puesto.
    fuente = TTFont(ruta_fuente, recalcTimestamp=False)
    if "fvar" not in fuente:
        raise SystemExit(
            f"«{ruta_fuente}» no es una fuente variable. La que se espera es\n"
            "Literata[opsz,wght].ttf, tal como la publica Google Fonts."
        )

    opciones = Options()
    opciones.layout_features = ["*"]
    opciones.name_IDs = ["*"]      # el nombre y la licencia se quedan dentro
    opciones.notdef_outline = True
    recorte = Subsetter(options=opciones)
    recorte.populate(unicodes=parse_unicodes(UNICODES))
    recorte.subset(fuente)

    fuente = instancer.instantiateVariableFont(
        fuente,
        {"opsz": EJE_OPTICO, "wght": (PESO_MINIMO, PESO_MINIMO, PESO_MAXIMO)},
        inplace=True,
    )
    fuente.flavor = "woff2"
    memoria = io.BytesIO()
    fuente.save(memoria)
    return memoria.getvalue()


def sellar_el_css(huella: str) -> bool:
    """Deja el `@font-face` apuntando a la huella de ahora. ¿Cambió algo?"""
    texto = ESTILO.read_text(encoding="utf-8")
    if not PATRON_SRC.search(texto):
        raise SystemExit(
            f"«{ESTILO}» no lleva el `src: url(\"./letra/literata.woff2\")` que\n"
            "este script sabe firmar. Si la línea se ha escrito de otra forma,\n"
            "hay que cambiarla también en PATRON_SRC: un @font-face apuntando a\n"
            "una huella vieja no da error, da la letra del sistema."
        )
    nuevo = PATRON_SRC.sub(rf"\1?v={huella}\3", texto)
    if nuevo == texto:
        return False
    ESTILO.write_text(nuevo, encoding="utf-8")
    return True


def main(argumentos: list[str]) -> int:
    if len(argumentos) != 2:
        raise SystemExit(
            f"Uso: python {Path(__file__).name} Literata.ttf OFL.txt\n\n"
            "Las dos cosas hacen falta: la licencia tiene que viajar con la\n"
            "letra, y es la única condición que la OFL pone."
        )
    ruta_fuente, ruta_licencia = Path(argumentos[0]), Path(argumentos[1])
    for ruta in (ruta_fuente, ruta_licencia):
        if not ruta.is_file():
            raise SystemExit(f"No existe «{ruta}».")

    CARPETA.mkdir(parents=True, exist_ok=True)
    crudo = generar(ruta_fuente)
    DESTINO.write_bytes(crudo)
    shutil.copy2(ruta_licencia, LICENCIA)

    huella = hashlib.sha256(crudo).hexdigest()[:8]
    movido = sellar_el_css(huella)
    print(
        f"literata.woff2: {len(crudo) / 1024:.1f} KB, huella {huella} "
        f"(opsz {EJE_OPTICO}, wght {PESO_MINIMO}-{PESO_MAXIMO})\n"
        f"glosa.css: {'firmado de nuevo' if movido else 'ya apuntaba ahí'}\n"
        f"OFL.txt: copiada al lado, que es lo que la licencia exige"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
