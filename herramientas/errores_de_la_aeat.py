"""Saca a tabla los mensajes de error que la AEAT publica para la solución pública.

Qué es
------
El 23-11-2026, a las 06:23 GMT, la AEAT puso en su Portal de Desarrolladores,
en «SPFE - Validaciones y errores», un «Listado de códigos de error» con dos
ficheros. Este lee el de los errores de negocio, `errores_negocio.properties`:
el texto de cada mensaje que dan sus reglas, con la clave con que el programa
de la AEAT lo busca. El otro, `errores_tecnicos.properties`, trae los códigos
de los fallos del servicio (4xxx, 5xxx y 8xxx: el sobre, el ebXML, la base de
datos), que no son el estado de una factura en un acuse, y no se lee.

No es una lista de códigos con su significado, aunque el portal la llame así:
es el fichero de mensajes del programa, tal cual. Por eso hay dos clases de
claves, y se separan:

- **`RULE_<regla>_MENSAJE`**, con o sin sufijo (`_1`, `_2`, `_CERO`, `_DET`,
  o un `2` pegado): los mensajes de una regla. La regla es lo que va entre
  `RULE_` y `_MENSAJE`, y es el código que la solución pública pone en
  `cbc:DocumentStatusCode` (en su ejemplo, `SPFE-CORE-18` llega con el texto
  de `RULE_SPFE-CORE-18_MENSAJE_3`). Una regla puede tener varios mensajes,
  uno por cada forma de incumplirla, y van en el orden del fichero.
- **Todas las demás**: mensajes generales, sin regla (`ERROR_NIF_FORMATO_INCORRECTO`,
  «El NIF tiene un formato erróneo»). La solución pública también los manda
  con el código de una regla: en su propio ejemplo, `SPFE-IDEN-02` llega con
  ese mensaje general y no con el de la regla, «Nif del Emisor no permitido».
  Se guardan para poder decirlo.

Cómo se lee el fichero
----------------------
Como lo lee Java, que es quien lo usa: ISO-8859-1, una clave y un valor por
línea separados por el primer `=`, las líneas que empiezan por `#` o `!` son
comentarios (hay reglas comentadas, que no cuentan), y `\\uXXXX` es un
carácter (el `∑` y la raya de BR-CO-10 a BR-CO-16). Si una clave sale dos
veces vale la última, como en Java, y la de antes se guarda también entre
los generales para reconocerla: pasa con `ERROR_CODIGO_NO_RECONOCIDO`.

Se niega a seguir si el fichero trae algo que este lector no sabe leer igual
que Java: una línea que acaba en `\\` (sigue en la siguiente), una clave con
`:` o con espacios (Java partiría ahí), o una línea sin `=`. Lo que no se
entiende no se convierte en una tabla que parece buena.

Los mensajes se copian tal cual, con sus erratas («No se existe la factura»)
y con sus `%s`, que el programa de la AEAT rellena con el valor del campo.

Esto no viaja en la rueda
-------------------------
Como `mensajes`, vive fuera de `validador/` y se corre cuando la AEAT cambia
el fichero:

    python -m herramientas.errores_de_la_aeat anexos/errores_negocio.properties 23-11-2026

El segundo argumento es la fecha en que la AEAT lo publicó, que el fichero no
dice: se mira en el portal (la fecha del servidor, `Last-Modified`). Reescribe
`validador/errores_de_la_aeat.py` con la huella SHA-256 del fichero.
"""

import hashlib
import json
import pathlib
import re

DIRECCION = ("https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/"
             "EEDD/Facturacion-electronica/errores_negocio.properties")

_REGLA = re.compile(r"RULE_(?P<regla>[A-Z0-9]+(?:-[A-Z0-9]+)+)_MENSAJE\w*")
_UNICODE = re.compile(r"\\u([0-9a-fA-F]{4})")


class FicheroQueNoSeEntiende(ValueError):
    """Una línea que este lector no leería como la lee Java."""


def _cita(s):
    return json.dumps(s, ensure_ascii=False)


def lee(camino):
    """Las claves y los mensajes del fichero, en su orden, repetidas incluidas."""
    texto = pathlib.Path(camino).read_bytes().decode("latin-1")
    pares = []
    for n, linea in enumerate(texto.splitlines(), 1):
        limpia = linea.strip()
        if not limpia or limpia[0] in "#!":
            continue
        if linea.rstrip().endswith("\\"):
            raise FicheroQueNoSeEntiende(f"línea {n}: sigue en la siguiente, y eso no se lee aquí")
        if "=" not in linea:
            raise FicheroQueNoSeEntiende(f"línea {n}: no tiene «=»: {linea[:80]!r}")
        clave, valor = linea.split("=", 1)
        clave = clave.strip()
        if ":" in clave or " " in clave or not clave:
            raise FicheroQueNoSeEntiende(f"línea {n}: Java no partiría la clave igual: {clave!r}")
        valor = _UNICODE.sub(lambda m: chr(int(m.group(1), 16)), valor.lstrip())
        pares.append((clave, valor.rstrip()))
    return pares


def tablas(camino):
    """Las reglas con sus mensajes, y los mensajes generales."""
    pares = lee(camino)
    ultimo = dict(pares)
    reglas, generales = {}, []
    for clave, valor in pares:
        regla = _REGLA.fullmatch(clave)
        if regla and ultimo[clave] == valor:
            reglas.setdefault(regla.group("regla"), []).append(valor)
        elif regla:
            # Una regla con la misma clave dos veces: no pasa hoy, y si pasa
            # la de antes no es un mensaje de la regla para Java.
            raise FicheroQueNoSeEntiende(f"la clave {clave} sale dos veces con textos distintos")
        elif clave.startswith("RULE_"):
            raise FicheroQueNoSeEntiende(f"una clave de regla con otra forma: {clave}")
        else:
            generales.append((clave, valor))
    return reglas, generales


def escribe_modulo(camino, destino, publicada):
    """Reescribe `validador/errores_de_la_aeat.py` con lo que diga este fichero."""
    if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", publicada):
        raise ValueError(f"la fecha va como dd-mm-aaaa: {publicada!r}")
    reglas, generales = tablas(camino)
    trozos = [CABEZA % {
        "publicada": publicada,
        "direccion": DIRECCION,
        "huella": hashlib.sha256(pathlib.Path(camino).read_bytes()).hexdigest(),
        "reglas": len(reglas),
        "mensajes": sum(len(m) for m in reglas.values()),
        "generales": len(generales),
    }]
    trozos.append(f"PUBLICADA = {_cita(publicada)}\n\n")
    trozos.append("REGLAS = {\n")
    for regla, mensajes in reglas.items():
        trozos.append(f"    {_cita(regla)}: (\n")
        for mensaje in mensajes:
            trozos.append(f"        {_cita(mensaje)},\n")
        trozos.append("    ),\n")
    trozos.append("}\n\n")
    trozos.append("GENERALES = (\n")
    for clave, mensaje in generales:
        trozos.append(f"    ({_cita(clave)}, {_cita(mensaje)}),\n")
    trozos.append(")\n")
    pathlib.Path(destino).write_text("".join(trozos), encoding="utf-8")
    return len(reglas), len(generales)


CABEZA = '''"""Los mensajes de error de la solución pública, tal y como los publica la AEAT.

Esto **no se escribe a mano**: lo genera `herramientas/errores_de_la_aeat.py`
leyendo el fichero de la AEAT. Si algo de aquí no cuadra con él, lo que está
mal es el lector, no esta tabla.

De dónde sale
-------------
Del «Listado de códigos de error» del Portal de Desarrolladores de la AEAT,
«SPFE - Validaciones y errores», publicado el %(publicada)s: los errores de
negocio. El portal avisa de que puede cambiar al acabar el periodo de pruebas.

    %(direccion)s
    SHA-256 %(huella)s

Qué trae: %(reglas)d reglas con %(mensajes)d mensajes, y %(generales)d mensajes generales.

Lo que hay que tener presente al usarlo
---------------------------------------
**La clave de `REGLAS` es el código** que la solución pública pone en el
estado de la factura (`SPFE-CORE-18`), y sus mensajes son las formas de
incumplir esa regla, en el orden del fichero.

**El mensaje que llega no es siempre uno de los de su regla.** La solución
pública manda también los de `GENERALES` con el código de una regla: en su
ejemplo del validador previo, `SPFE-IDEN-02` llega con «El NIF tiene un
formato erróneo», que es general. Cuándo usa cada uno no lo dice el fichero.

**Los `%%s` son huecos** que el programa de la AEAT rellena con el valor del
campo, y se copian tal cual, como las erratas.
"""

'''


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        sys.exit("uso: python -m herramientas.errores_de_la_aeat <errores_negocio.properties> <dd-mm-aaaa>")
    n, g = escribe_modulo(sys.argv[1], "validador/errores_de_la_aeat.py", sys.argv[2])
    print(f"validador/errores_de_la_aeat.py: {n} reglas y {g} mensajes generales")
