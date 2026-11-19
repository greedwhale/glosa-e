"""Comprueba que un alojamiento sirve el sitio como manda `vercel.json`.

    python -m herramientas.comparar_alojamiento https://glosa.<cuenta>.workers.dev
    python -m herramientas.comparar_alojamiento                 # producción

Se escribió el 15-11-2026 para la mudanza a Cloudflare, y es lo que dice si se
puede mover el dominio: se corre contra la dirección de prueba de Cloudflare
**antes** de tocar el DNS, y otra vez contra `www.glosa-e.com` después. Con
producción en Vercel tiene que salir limpio; si no, falla la herramienta y no
el alojamiento.

Mira lo que un alojamiento puede cambiar sin que nada se ponga rojo, que es lo
que en este repositorio se rompe (el fallo de siempre: sale todo verde y no es
lo que crees):

- **Que cada fichero sea el que se montó.** `dist/rueda.json` lleva la huella
  SHA-256 de cada fichero publicado, calculada por la misma construcción que lo
  publicó; se bajan todos y se comparan. Así se ve un alojamiento que reescribe
  una página (Cloudflare lo hace con los correos si se le deja) o que no sube
  un fichero.
- **La caché de cada regla.** Lo que `vercel.json` manda guardar un año, un
  año; lo demás, `must-revalidate`. Un manifiesto o una portada con
  `immutable` congelan el sitio para quien ya pasó, sin forma de avisarle.
- **Las cabeceras de seguridad, las redirecciones, las direcciones limpias y
  el 404**, que son lo que cada alojamiento hace a su manera.
- **Que nadie ponga cookies ni scripts suyos.** La política de privacidad dice
  que no hay cookies; una de bots de Cloudflare la desmentiría.

Sale con 0 si todo cuadra y con 1 si no, con la lista de lo que no cuadra.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CONFIGURACION = RAIZ / "vercel.json"
PRODUCCION = "https://www.glosa-e.com"

# Como en `validador/indexnow.py`: la conexión desde donde se publica se corta
# a ratos (medido el 23-10-2026), así que plazo corto y varios intentos.
_PLAZO = 30
_INTENTOS = 5
_HILOS = 8

# Lo que delataría a un alojamiento metiendo cosas suyas en las páginas.
_AJENOS_EN_LAS_PAGINAS = ("/cdn-cgi/", "__cf_email__", "email-protection")

_UN_ANO = "max-age=31536000"


@dataclass
class Respuesta:
    estado: int
    cabeceras: dict[str, str]
    cuerpo: bytes
    cookies: list[str] = field(default_factory=list)


class _SinSeguir(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401
        return None


_SIGUE = urllib.request.build_opener()
_NO_SIGUE = urllib.request.build_opener(_SinSeguir)


def pedir(url: str, seguir: bool = True) -> Respuesta:
    """GET con reintentos. Un 4xx o 5xx es una respuesta, no un fallo."""
    abridor = _SIGUE if seguir else _NO_SIGUE
    peticion = urllib.request.Request(
        url, headers={"User-Agent": "glosa-e/comparar-alojamiento",
                      "Cache-Control": "no-cache"})
    ultimo: Exception | None = None
    for intento in range(_INTENTOS):
        try:
            try:
                with abridor.open(peticion, timeout=_PLAZO) as r:
                    return Respuesta(r.status, {k.lower(): v for k, v in r.headers.items()},
                                     r.read(), r.headers.get_all("Set-Cookie") or [])
            except urllib.error.HTTPError as r:
                # El cuerpo de un 3xx o un 4xx también se lee por la red, y
                # también se corta. Leído fuera del reintento, un corte ahí
                # tumbaba la comparación entera: pasó el 19-11-2026 a mitad de
                # las 423 redirecciones, con un `TimeoutError` en `r.read()`.
                return Respuesta(r.code, {k.lower(): v for k, v in r.headers.items()},
                                 r.read(), r.headers.get_all("Set-Cookie") or [])
        except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
            ultimo = error
            time.sleep(1 + intento)
    raise ConnectionError(f"{url}: sin respuesta tras {_INTENTOS} intentos ({ultimo})")


def _patron(fuente: str) -> re.Pattern[str]:
    """La ruta de `vercel.json` como expresión: solo `(.*)` es comodín."""
    return re.compile("^" + re.escape(fuente).replace(re.escape("(.*)"), ".*") + "$")


def cache_esperada(ruta: str, reglas: list[dict]) -> str | None:
    """El `Cache-Control` que `vercel.json` manda para esa ruta, o None si
    ninguna regla lo dice (entonces vale el del alojamiento, que tiene que
    obligar a revalidar). Gana la última regla que encaja, como en Vercel."""
    valor = None
    for regla in reglas:
        if _patron(regla["source"]).match(ruta):
            for c in regla["headers"]:
                if c["key"].lower() == "cache-control":
                    valor = c["value"]
    return valor


def limpia_de(huellas: dict[str, str]) -> str | None:
    """Una página cualquiera del sitio, sin su `.html`, para las pruebas que
    necesitan una dirección limpia que exista."""
    return next((p[:-5] for p in sorted(huellas) if p.endswith(".html")
                 and "/" not in p and p not in ("index.html", "404.html")), None)


def _servidor(url: str) -> str:
    return urllib.parse.urlsplit(url).hostname or ""


def _formas_de_la_fuente(fuente: str) -> list[str]:
    """La fuente de una redirección y las dos formas que Vercel lleva al mismo
    sitio. Las mismas que escribe `validador/alojamiento.py`, pero contadas
    aquí aparte: si esta herramienta las sacara de allí, un error en la
    traducción saldría también en la comprobación y no se vería."""
    if fuente == "/" or fuente.endswith((".html", "/")):
        return [fuente]
    return [fuente, f"{fuente}.html", f"{fuente}/"]


_SALTOS = 4


def _cadena(base: str, ruta: str, destino: str) -> str | None:
    """Sigue las redirecciones de `ruta` sin dejar que lo haga urllib. None si
    todos los saltos son permanentes y la cadena acaba en `destino`; si no,
    lo que falla."""
    actual = ruta
    for _ in range(_SALTOS):
        r = pedir(base + actual, seguir=False)
        hacia = r.cabeceras.get("location", "")
        if r.estado not in (301, 308):
            return (f"contesta {r.estado} hacia «{hacia}», y debería ser "
                    f"permanente hacia {destino}.")
        partes = urllib.parse.urlsplit(hacia)
        if partes.hostname and partes.hostname != _servidor(base):
            return f"lleva a otro servidor, «{hacia}», y debería llevar a {destino}."
        actual = partes.path or "/"
        if actual == destino:
            return None
    return f"no llega a {destino} en {_SALTOS} saltos (va por «{actual}»)."


def comprobar(base: str, configuracion: Path = CONFIGURACION) -> list[str]:
    base = base.rstrip("/")
    datos = json.loads(configuracion.read_text(encoding="utf-8"))
    reglas = datos.get("headers", [])
    fallos: list[str] = []

    manifiesto = pedir(f"{base}/dist/rueda.json")
    if manifiesto.estado != 200:
        return [f"/dist/rueda.json contesta {manifiesto.estado}: no hay con qué comparar."]
    huellas: dict[str, str] = json.loads(manifiesto.cuerpo)["huellas"]

    def uno(ruta: str) -> list[str]:
        r = pedir(f"{base}/{ruta}")
        mal = []
        if r.estado != 200:
            return [f"/{ruta}: contesta {r.estado}."]
        if hashlib.sha256(r.cuerpo).hexdigest() != huellas[ruta]:
            mal.append(f"/{ruta}: los bytes no son los que se montaron.")
        mandada = cache_esperada("/" + ruta, reglas)
        servida = r.cabeceras.get("cache-control", "")
        if mandada and _UN_ANO in mandada and (_UN_ANO not in servida or "immutable" not in servida):
            mal.append(f"/{ruta}: debería guardarse un año y llega con «{servida}».")
        if not (mandada and _UN_ANO in mandada) and ("immutable" in servida or "must-revalidate" not in servida):
            mal.append(f"/{ruta}: debería revalidarse y llega con «{servida}».")
        if r.cookies:
            mal.append(f"/{ruta}: pone cookies: {r.cookies}.")
        if ruta.endswith(".html"):
            texto = r.cuerpo.decode("utf-8", "replace")
            mal += [f"/{ruta}: lleva «{a}», que el sitio no escribe."
                    for a in _AJENOS_EN_LAS_PAGINAS if a in texto]
        return mal

    with ThreadPoolExecutor(_HILOS) as hilos:
        for mal in hilos.map(uno, sorted(huellas)):
            fallos += mal

    # Las cabeceras de seguridad y los tipos, tal como los dice `vercel.json`.
    portada = pedir(f"{base}/")
    for regla in reglas:
        if regla["source"] == "/(.*)":
            for c in regla["headers"]:
                if portada.cabeceras.get(c["key"].lower()) != c["value"]:
                    fallos.append(f"/: {c['key']} llega como "
                                  f"«{portada.cabeceras.get(c['key'].lower())}».")
        elif "(.*)" not in regla["source"]:
            for c in regla["headers"]:
                if c["key"].lower() == "content-type":
                    r = pedir(base + regla["source"])
                    if r.cabeceras.get("content-type", "").replace(" ", "").lower() != c["value"].replace(" ", "").lower():
                        fallos.append(f"{regla['source']}: Content-Type llega como "
                                      f"«{r.cabeceras.get('content-type')}».")

    # Las redirecciones, una a una y con sus formas `.html` y con barra, que
    # en Vercel llegan al mismo sitio. Hasta el 19-11-2026 solo se miraba la
    # fuente, y Cloudflare contestaba 404 a `/tesis.html` sin que esto lo
    # viera: Search Console lo vio antes. Se sigue la cadena a mano, salto a
    # salto, porque Vercel da dos (quita el `.html` y luego redirige) y
    # Cloudflare uno, y los dos valen si todos son permanentes y acaban en el
    # destino.
    for regla in datos.get("redirects", []):
        for forma in _formas_de_la_fuente(regla["source"]):
            mal = _cadena(base, forma, regla["destination"])
            if mal:
                fallos.append(f"{forma}: {mal}")

    # `http://` lleva a `https://`. Vercel lo hacía solo, con un 308; en
    # Cloudflare es "Usar siempre HTTPS", un interruptor de la zona, y la
    # mudanza del 15-11-2026 lo dejó apagado: medido el 19-11, `http://`
    # servía cada página con un 200. No se mira en `*.workers.dev`, que no es
    # la dirección que conoce Google ni hereda los ajustes de la zona.
    if base.startswith("https://") and not _servidor(base).endswith(".workers.dev"):
        plana = "http://" + base[len("https://"):]
        for ruta in ("/", f"/{limpia_de(huellas)}" if limpia_de(huellas) else None):
            if ruta is None:
                continue
            r = pedir(plana + ruta, seguir=False)
            destino = r.cabeceras.get("location", "")
            if r.estado not in (301, 308) or destino != base + ruta:
                fallos.append(f"{plana}{ruta}: contesta {r.estado} hacia «{destino}», "
                              f"y debería llevar a {base}{ruta} de forma permanente.")

    # Las direcciones limpias: la buena se sirve y las otras dos llevan a ella.
    limpia = limpia_de(huellas)
    if limpia:
        if pedir(f"{base}/{limpia}").estado != 200:
            fallos.append(f"/{limpia}: la dirección limpia no se sirve.")
        for otra in (f"/{limpia}.html", f"/{limpia}/"):
            r = pedir(base + otra, seguir=False)
            if r.estado not in (301, 302, 307, 308) or not r.cabeceras.get("location", "").rstrip("/").endswith(f"/{limpia}"):
                fallos.append(f"{otra}: contesta {r.estado} hacia "
                              f"«{r.cabeceras.get('location')}» y debería llevar a /{limpia}.")

    # El 404: lo que no existe, y lo que existe con otras mayúsculas.
    for ruta in (f"/no-existe-{uuid.uuid4().hex[:8]}", "/codigo-br-01"):
        r = pedir(base + ruta)
        if r.estado != 404:
            fallos.append(f"{ruta}: contesta {r.estado} y debería ser 404.")
        elif "404.html" in huellas and hashlib.sha256(r.cuerpo).hexdigest() != huellas["404.html"]:
            fallos.append(f"{ruta}: el 404 no es nuestra `404.html`.")

    return fallos


def main(argumentos: list[str] | None = None) -> int:
    lector = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    lector.add_argument("base", nargs="?", default=PRODUCCION)
    opciones = lector.parse_args(argumentos)
    fallos = comprobar(opciones.base)
    if fallos:
        print(f"{opciones.base}: {len(fallos)} cosa(s) no cuadran con lo montado.")
        for f in fallos:
            print("  -", f)
        return 1
    print(f"{opciones.base}: sirve lo montado, con las reglas de `vercel.json`.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
