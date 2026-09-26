# -*- coding: utf-8 -*-
"""Sirve el sitio montado como lo sirve Vercel, para mirarlo en local.

Por qué no basta con `http.server`
----------------------------------
Desde el 25-09-2026 el sitio montado enlaza cada página por su dirección
limpia —`./legal`, no `./legal.html`—, porque en producción la forma con
`.html` es una redirección 308 y Search Console la contaba como página aparte.
`http.server` no sabe nada de eso: sirve ficheros, y `./legal` le da un 404.
Así que la vista previa del sitio se rompía justo por el arreglo.

Esto hace lo que `vercel.json` le pide a Vercel, y nada más:

| Petición | Vercel | Aquí |
|---|---|---|
| `/legal` | la página `legal.html` | igual |
| `/legal.html` | 308 a `/legal` (`cleanUrls`) | igual |
| `/banco/` | 308 a `/banco` (`trailingSlash: false`) | igual |
| `/` | `index.html` | igual |
| lo que no existe | 404 con `404.html` | igual |
| `/codigo-br-01` | 404: **distingue mayúsculas** | igual, aunque Windows no las distinga |

Lo último importa. Windows encuentra `codigo-BR-01.html` aunque se le pida en
minúsculas, y Vercel no. Un servidor local que no las distinga enseña como
buena una dirección que en producción da 404, que es el fallo de siempre de
esta casa: todo verde y no es lo que se publica.

Uso, desde la raíz del repositorio (igual que `http.server`, y atado a esta
máquina por lo mismo que los otros servidores de `.claude/launch.json`):

    python herramientas/servir_sitio.py 8322 --bind 127.0.0.1 --directory sitio
"""
from __future__ import annotations

import argparse
import http.server
import os
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit, unquote


def _existe_tal_cual(carpeta: Path, relativa: str) -> bool:
    """Si el fichero existe con **esas** mayúsculas, trozo a trozo.

    `Path.is_file()` en Windows dice que sí a `codigo-br-01.html` cuando lo que
    hay es `codigo-BR-01.html`. Vercel no, así que aquí tampoco.
    """
    actual = carpeta
    for trozo in [t for t in relativa.split("/") if t]:
        try:
            nombres = os.listdir(actual)
        except (FileNotFoundError, NotADirectoryError):
            return False
        if trozo not in nombres:
            return False
        actual = actual / trozo
    return actual.is_file()


class ComoVercel(http.server.SimpleHTTPRequestHandler):
    """`cleanUrls`, `trailingSlash: false` y `404.html`, como en `vercel.json`."""

    def _redirigir(self, destino: str, consulta: str) -> None:
        self.send_response(308)
        self.send_header("Location", destino + (f"?{consulta}" if consulta else ""))
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _no_hay(self) -> None:
        pagina = Path(self.directory) / "404.html"
        cuerpo = pagina.read_bytes() if pagina.is_file() else b"404"
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(cuerpo)

    def _resolver(self) -> bool:
        """Deja `self.path` apuntando al fichero, o contesta él y da `False`."""
        partes = urlsplit(self.path)
        ruta = unquote(partes.path)
        carpeta = Path(self.directory)
        if ruta != "/" and ruta.endswith("/"):
            self._redirigir(ruta.rstrip("/") or "/", partes.query)
            return False
        if ruta.endswith(".html"):
            limpia = ruta[: -len(".html")]
            self._redirigir("/" if limpia == "/index" else limpia, partes.query)
            return False
        if ruta == "/":
            relativa = "index.html"
        elif _existe_tal_cual(carpeta, ruta.lstrip("/")):
            relativa = ruta.lstrip("/")
        elif _existe_tal_cual(carpeta, ruta.lstrip("/") + ".html"):
            relativa = ruta.lstrip("/") + ".html"
        else:
            self._no_hay()
            return False
        self.path = "/" + relativa
        return True

    def do_GET(self) -> None:  # noqa: N802 — el nombre lo pone http.server
        if self._resolver():
            super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        if self._resolver():
            super().do_HEAD()


def main(argumentos: list[str] | None = None) -> None:
    analizador = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analizador.add_argument("puerto", type=int, nargs="?", default=8322)
    analizador.add_argument("--bind", default="127.0.0.1")
    analizador.add_argument("--directory", default="sitio")
    opciones = analizador.parse_args(argumentos)
    manejador = partial(ComoVercel, directory=str(Path(opciones.directory).resolve()))
    with http.server.ThreadingHTTPServer((opciones.bind, opciones.puerto), manejador) as servidor:
        print(f"Sirviendo {opciones.directory} como Vercel en "
              f"http://{opciones.bind}:{opciones.puerto}/")
        servidor.serve_forever()


if __name__ == "__main__":
    main()
