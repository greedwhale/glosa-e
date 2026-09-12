# -*- coding: utf-8 -*-
"""Las anclas que están publicadas, contra el calendario.

Por qué existe
--------------
Hasta aquí, del vencimiento de las anclas avisaban tres cosas y ninguna
avisaba a quien tiene que arreglarlo:

1. **`--montar-anclas` y `--empaquetar`** lo dicen por pantalla en cuanto
   quedan 90 días o menos, y `--empaquetar` **se niega** —`SinRenovar`— el día
   después de la fecha. Pero eso sólo se entera quien los ejecuta, y no hay
   ningún motivo para ejecutarlos: el paquete ya está montado y versionado.
2. **El informe** lo dice en cada validación.
3. **La página** lo pinta en «Lo que trae puesto».

O sea que el día que venzan, **el sitio se lo dice a quien lo visita antes que
a quien lo mantiene**. La suite sigue verde, el gancho de empujar deja publicar
y el despliegue sale sin una queja. Es el reparto de papeles al revés.

Esto lo arregla mirando lo único que de verdad está publicado: `web/PAQUETE.json`,
que **sí** se versiona y es el que la página lee para decir de cuándo son sus
anclas. Con eso, el aviso llega por donde llega todo lo demás en este
repositorio —la suite en rojo— y el gancho de `git push` no deja publicar un
sitio que va a creerle a autoridades que quizá ya no lo sean.

Lo que no hace, a propósito
---------------------------
**No rompe el despliegue.** Vercel monta con `--sitio --exigir-paquete`, y una
negativa ahí dejaría en pie el despliegue anterior —el mismo paquete vencido—
además de bloquear cualquier arreglo que no tenga nada que ver. La página ya
dice la verdad sobre sus anclas cuando vencen; lo que faltaba era que se
enterase su autor, y para eso el sitio correcto es la suite.
"""
from __future__ import annotations

import json
import pathlib
import warnings
from datetime import date

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[1]
MANIFIESTO = RAIZ / "web" / "PAQUETE.json"

# El mismo margen que usan `--montar-anclas` y `--empaquetar` por pantalla. Si
# allí 90 días es cuando hay que empezar a preocuparse, aquí también: dos
# umbrales distintos para la misma cuenta atrás son dos verdades.
DIAS_DE_AVISO = 90

COMO_SE_ARREGLA = (
    "Se arregla con dos órdenes, en este orden:\n"
    "  python -m validador --montar-anclas\n"
    "  python -m validador --empaquetar\n"
    "y commiteando `web/paquete.zip` y `web/PAQUETE.json`, que se versionan "
    "a propósito."
)


def _publicado() -> dict:
    if not MANIFIESTO.is_file():
        pytest.skip(f"no está {MANIFIESTO.name}, que es lo que se publica")
    return json.loads(MANIFIESTO.read_text(encoding="utf-8"))


def test_las_anclas_publicadas_no_se_han_quedado_viejas():
    """El día siguiente a la fecha de renovación, esto se pone en rojo.

    Y tiene que ponerse. Un conjunto de anclas no caduca —los certificados de
    dentro duran veinte años— pero la lista de **quién sigue estando
    autorizado** se renueva cada seis meses. Pasada esa fecha, lo que viaja con
    la página sigue dando por buena a cualquier autoridad a la que el Estado le
    haya retirado la cualificación desde entonces, con su certificado en vigor
    y su cadena llegando hasta el final: no hay nada en el documento que lo
    delate.
    """
    manifiesto = _publicado()
    siguiente = manifiesto.get("siguiente")
    if not siguiente:
        pytest.skip(
            "la lista de la que salen no dice cuándo se renueva, así que no se "
            "puede afirmar que esté vencida. La página lo dice con esas "
            "palabras y aquí se calla por lo mismo.")

    renovacion = date.fromisoformat(siguiente)
    hoy = date.today()
    quedan = (renovacion - hoy).days

    assert quedan >= 0, (
        f"Las anclas que está sirviendo la página son de una lista que decía "
        f"renovarse el {siguiente}, y hoy es {hoy.isoformat()}: hace "
        f"{-quedan} días que venció. Ahora mismo, cada informe y cada visita "
        f"lo están diciendo en la página —lo sabe quien entra antes que tú—.\n"
        f"{COMO_SE_ARREGLA}")

    if quedan <= DIAS_DE_AVISO:
        # Aviso y no fallo: una fecha que se acerca es un recordatorio, y poner
        # la suite en rojo con un mes por delante sólo enseña a saltarse el
        # gancho, que es peor que no tener aviso.
        warnings.warn(
            f"A las anclas publicadas les quedan {quedan} días: la lista se "
            f"renueva el {siguiente}. Cuando pase, esta prueba se pone en rojo "
            f"y el gancho de empujar no dejará publicar.\n{COMO_SE_ARREGLA}",
            stacklevel=1,
        )


def test_el_manifiesto_publicado_dice_de_cuando_son():
    """Sin fechas, lo de arriba no puede vigilar nada y no se entera nadie.

    El manifiesto podría quedarse sin `siguiente` de dos maneras: porque la
    lista del Estado deje de decirlo —y entonces hay que saberlo— o porque
    alguien lo quite al tocar el formato. Las dos acaban en un guardián que se
    salta a sí mismo con un `skip` verde.
    """
    manifiesto = _publicado()
    for campo in ("declarada", "publicada", "montada"):
        assert manifiesto.get(campo), (
            f"`web/PAQUETE.json` no dice «{campo}». Quien lee un informe no "
            "eligió estas anclas: lo mínimo es poder saber de dónde salen y "
            "de cuándo son.")
    assert "siguiente" in manifiesto, (
        "`web/PAQUETE.json` ya no trae el campo «siguiente». Con o sin fecha "
        "dentro, el campo tiene que estar: es lo que mira el guardián de "
        "arriba, y sin él se salta solo y en verde.")
