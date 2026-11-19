"""Las reglas del alojamiento, escritas una vez y servidas en dos sitios.

Desde el 15-11-2026 el sitio se prepara para mudarse de Vercel a Cloudflare
(Workers con ficheros estáticos). El plan gratuito de Vercel es solo para uso
personal y no comercial; las condiciones de Cloudflare no ponen esa condición
y solo prohíben recoger datos de tarjeta en una propiedad gratuita (releídas
ese día). Los pasos, en el README: «La mudanza a Cloudflare».

Mientras dure la mudanza **los dos alojamientos tienen que servir lo mismo**, y
cada uno se configura a su manera: Vercel lee `vercel.json`; Cloudflare lee
`_headers` y `_redirects` dentro de la carpeta publicada. Escribirlos a mano
serían dos copias de las mismas reglas, y dos copias se separan en silencio:
una cabecera de caché que se queda en una y no en la otra no rompe nada, solo
congela el sitio para quien ya pasó. Es el fallo de siempre de este
repositorio, así que no se deja montar: **`vercel.json` es la única fuente**, y
`--sitio` traduce sus reglas al formato de Cloudflare. Lo que no sabe traducir
lo dice y no monta, en vez de dejar una regla fuera.

Las tres cosas que no son traducción literal, cada una por lo que se midió en
la documentación de Cloudflare el 15-11-2026:

- **`no-transform` en todo.** Cloudflare enciende sola la ofuscación de correos
  al dar de alta un dominio: reescribe los `mailto:` de cada página y le mete un
  script suyo. Eso cambia los bytes que se publican (la página compara lo que
  se baja con sus huellas) y añade código que el sitio no ha escrito. Su
  documentación dice que no la aplica a respuestas con `Cache-Control:
  no-transform`. Se pone aquí, versionado, en vez de depender de que alguien
  apague un interruptor del panel.
- **Lo de las páginas se repite entero.** Una cabecera escrita en `_headers`
  sustituye la que Cloudflare pone por defecto, y la suya para las páginas es
  `public, max-age=0, must-revalidate`. Si solo se escribiera `no-transform`,
  las páginas perderían el `must-revalidate` y el navegador podría guardarlas
  a su criterio: la portada de ayer haciéndose pasar por la de hoy.
- **Lo que se repite se suelta antes.** Cuando una dirección encaja con dos
  reglas, Cloudflare une los valores de la misma cabecera con una coma, y para
  `Cache-Control` eso da dos `max-age` que se contradicen sin error. Vercel se
  queda con el de la regla más concreta. Para que Cloudflare haga lo mismo, la
  regla que vuelve a poner una cabecera la suelta antes (`! Cache-Control`),
  que es lo que su documentación indica.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# La única fuente de las reglas del alojamiento.
CONFIGURACION = RAIZ / "vercel.json"

# Lo que lee Cloudflare, dentro de la carpeta publicada. No se sirven: su
# documentación dice que los dos se leen al desplegar y no quedan a la vista.
CABECERAS = "_headers"
REDIRECCIONES = "_redirects"

# Los límites del plan gratuito, de la documentación de Workers (15-11-2026):
# 100 reglas de cabeceras, 2.000 caracteres por línea, 2.000 redirecciones
# fijas. Pasarse no da error al desplegar: las de más se ignoran.
MAXIMO_DE_REGLAS_DE_CABECERAS = 100
MAXIMO_DE_CARACTERES_POR_LINEA = 2000
MAXIMO_DE_REDIRECCIONES = 2000

# La cabecera de caché de las páginas en Cloudflare, con `no-transform`
# añadido. Ver arriba por qué va entera.
CACHE_DE_LAS_PAGINAS = "public, max-age=0, must-revalidate, no-transform"

# Lo único de las expresiones de Vercel que tiene equivalente directo: un
# comodín, una vez. Lo demás (parámetros con nombre, grupos, alternativas) se
# niega en vez de traducirse a medias.
_COMODIN = "(.*)"
_RE_RUTA_SIMPLE = re.compile(r"^/[A-Za-z0-9._~/-]*$")


def leer(configuracion: Path = CONFIGURACION) -> dict:
    if not configuracion.is_file():
        raise ValueError(
            f"No hay «{configuracion}», que es de donde salen las reglas del "
            "alojamiento: cabeceras, caché y redirecciones. Sin él, Cloudflare "
            "serviría el sitio con las suyas por defecto."
        )
    return json.loads(configuracion.read_text(encoding="utf-8"))


def _ruta(fuente: str) -> str:
    """La ruta de Vercel en la forma de Cloudflare: `(.*)` pasa a `*`."""
    if fuente.count(_COMODIN) > 1:
        raise ValueError(
            f"La regla «{fuente}» lleva más de un comodín, y Cloudflare solo "
            "admite uno por regla."
        )
    traducida = fuente.replace(_COMODIN, "*")
    if not _RE_RUTA_SIMPLE.match(traducida.replace("*", "")):
        raise ValueError(
            f"La regla «{fuente}» usa algo de las expresiones de Vercel que "
            "aquí no se sabe traducir (solo una ruta fija o con un `(.*)`). "
            "Traducida a medias serviría otra cosa en Cloudflare sin avisar."
        )
    return traducida


def cabeceras(datos: dict) -> str:
    """El `_headers` de Cloudflare con las reglas de `headers` de Vercel."""
    reglas = datos.get("headers", [])
    if len(reglas) > MAXIMO_DE_REGLAS_DE_CABECERAS:
        raise ValueError(
            f"`vercel.json` tiene {len(reglas)} reglas de cabeceras y "
            f"Cloudflare solo lee {MAXIMO_DE_REGLAS_DE_CABECERAS}: las de más se "
            "quedarían fuera sin error."
        )
    lineas = [
        "# Generado por `python -m validador --sitio` a partir de `vercel.json`.",
        "# No se edita a mano: ver `validador/alojamiento.py`.",
    ]
    puestas: set[str] = set()
    for regla in reglas:
        ruta = _ruta(regla["source"])
        valores = [(c["key"], c["value"]) for c in regla["headers"]]
        if ruta == "/*" and not any(k.lower() == "cache-control" for k, _ in valores):
            valores.insert(0, ("Cache-Control", CACHE_DE_LAS_PAGINAS))
        lineas.append(ruta)
        for clave, valor in valores:
            if clave.lower() in puestas:
                lineas.append(f"  ! {clave}")
            lineas.append(f"  {clave}: {valor}")
            puestas.add(clave.lower())
    if not any(l == "/*" for l in lineas):
        raise ValueError(
            "`vercel.json` no tiene una regla para todo el sitio (`/(.*)`), y "
            "de ahí cuelgan las cabeceras de seguridad y el `no-transform` que "
            "impide que Cloudflare reescriba las páginas."
        )
    largas = [l for l in lineas if len(l) > MAXIMO_DE_CARACTERES_POR_LINEA]
    if largas:
        raise ValueError(
            f"Hay {len(largas)} línea(s) de cabecera de más de "
            f"{MAXIMO_DE_CARACTERES_POR_LINEA} caracteres, y Cloudflare no las lee."
        )
    return "\n".join(lineas) + "\n"


def _formas(origen: str) -> list[str]:
    """Las direcciones que en Vercel acaban en la misma redirección.

    Vercel, con `cleanUrls` y sin barra final, lleva `/tesis.html` y `/tesis/`
    a `/tesis` antes de mirar las redirecciones, así que las tres llegan a
    `/sobre`. En Cloudflare `html_handling` solo hace eso con los ficheros que
    existen, y la fuente de una redirección es justo una página que ya no
    está: `/tesis.html` daba 404. Medido el 19-11-2026, cuatro días después
    de la mudanza, cuando Search Console avisó de páginas nuevas en 404: de
    las 141 fuentes de `vercel.json`, 114 con su `.html` en 404, y la barra
    final igual. Por eso cada redirección se escribe tres veces, y las tres
    van directas al destino (un salto, no los dos de Vercel)."""
    if origen == "/" or origen.endswith((".html", "/")):
        return [origen]
    return [origen, f"{origen}.html", f"{origen}/"]


def redirecciones(datos: dict) -> str:
    """El `_redirects` de Cloudflare con las de Vercel, con el mismo código."""
    reglas = datos.get("redirects", [])
    lineas = [
        "# Generado por `python -m validador --sitio` a partir de `vercel.json`.",
        "# No se edita a mano: ver `validador/alojamiento.py`.",
    ]
    # Una forma que `vercel.json` ya escribe como regla propia manda sobre la
    # que se deduce de otra: si no, Cloudflare se quedaría con la primera que
    # encuentra y no se sabría cuál.
    escritas = {regla["source"] for regla in reglas}
    reglas_escritas = 0
    for regla in reglas:
        origen, destino = regla["source"], regla["destination"]
        for cual in (origen, destino):
            if _COMODIN in cual or not _RE_RUTA_SIMPLE.match(cual):
                raise ValueError(
                    f"La redirección «{origen}» → «{destino}» no es de una "
                    "ruta fija a otra, y aquí solo se traducen esas."
                )
        # Vercel contesta `permanent` con 308 y lo demás con 307. En
        # Cloudflare, sin código, sería un 302: hay que decirlo.
        codigo = 308 if regla.get("permanent") else 307
        for forma in _formas(origen):
            if forma != origen and forma in escritas:
                continue
            lineas.append(f"{forma} {destino} {codigo}")
            reglas_escritas += 1
    # El límite cuenta las líneas que se escriben, no las reglas de
    # `vercel.json`: con las formas, cada una son tres.
    if reglas_escritas > MAXIMO_DE_REDIRECCIONES:
        raise ValueError(
            f"Las redirecciones de `vercel.json`, con sus formas `.html` y con "
            f"barra, son {reglas_escritas} líneas y Cloudflare solo lee "
            f"{MAXIMO_DE_REDIRECCIONES}: las de más se ignorarían sin error."
        )
    return "\n".join(lineas) + "\n"
