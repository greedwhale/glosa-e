"""Avisar a los buscadores de lo que cambió en el sitio, por IndexNow.

    python -m validador --avisar-indexnow          # lo montado en sitio/
    python -m validador --avisar-indexnow CARPETA

Se corre **después** de publicar, cuando producción ya sirve lo nuevo: es el
último paso de una tanda, detrás de comprobar producción. No va en la
construcción de Vercel porque esa corre antes de que el despliegue esté en el
aire, y un aviso mandado entonces haría que el buscador viniera a leer la
versión de ayer, o a buscar una clave que todavía no se sirve.

Por qué existe: el 23-10-2026 Bing tenía indexadas 138 páginas, Copilot citaba
una ficha, y lo nuevo tardaba semanas en entrar solo. IndexNow es la forma que
tiene Bing de enterarse el mismo día sin esperar a pasar por el sitemap.

Tres cosas que se cuidan, cada una con su negativa:

- **Solo lo que cambió.** La FAQ de IndexNow dice que no está pensado para
  mandar el sitio entero de golpe, y que avisar una y otra vez de lo que no
  cambia gasta la cuota de rastreo. Así que se apunta lo que se avisó y se
  compara: la primera vez solo se apunta.
- **Que producción sirva ya lo que se avisa.** Se mira contra `rueda.json`,
  que lleva la huella de cada fichero publicado: con una petición se sabe si
  lo montado aquí es lo que está en el aire.
- **Que la clave se sirva.** Sin ella el buscador contesta 403 y no indexa
  nada de lo avisado.

Si algo de eso falla no se manda nada y no se apunta nada: lo que no se avisó
hoy se avisa la próxima vez, porque la comparación es contra lo último que se
avisó y no contra el último despliegue.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from validador import paquete

# A quién se avisa. IndexNow reparte lo que recibe entre todos los buscadores
# que lo usan, y su FAQ pide mandarlo a uno solo. Se manda a Bing porque es
# por quien se montó esto, y porque así lo que se mande se ve en su panel.
PUNTO_DE_AVISO = "https://www.bing.com/indexnow"

# Dónde se apunta lo avisado: dentro de la carpeta común de git, que no se
# versiona, no viaja al sitio y la comparten la copia principal y sus
# worktrees. Una copia recién sacada no la tiene, y entonces la primera vez
# solo apunta, que es lo seguro.
NOMBRE_DEL_ESTADO = "glosa-indexnow.json"

# La conexión desde donde se publica se corta a ratos: medido el 23-10-2026,
# 23 cortes en 418 peticiones a producción, y una misma página tardando 1 s,
# 6 s o colgándose 60 s. Con plazo corto y varios intentos se pasa; si ni así,
# no se manda nada y se dice.
_PLAZO = 20
_INTENTOS = 5
_CABECERAS = {"User-Agent": "Glosa-e (aviso IndexNow; +https://www.glosa-e.com)"}

# Lo que IndexNow dice de cada respuesta, de su documentación. 200 y 202 son
# las buenas: la segunda es la de la primera vez, mientras comprueba la clave.
_BUENAS = (200, 202)
_LO_QUE_DICE = {
    400: "la petición está mal formada",
    403: "la clave no vale: no encontró el fichero, o no la lleva dentro",
    422: "alguna dirección no es de este dominio, o la clave no tiene la forma "
         "que pide el protocolo",
    429: "demasiadas peticiones: lo toma por correo basura",
}

# Lo que no cuenta como cambio. Un buscador lee el texto y los enlaces, no la
# huella de `glosa.css` ni la política de contenido. Sin quitar esto, tocar el
# estilo cambiaba las 418 páginas a la vez (la huella `?v=` va en todas) y se
# avisaba del sitio entero, que es justo lo que IndexNow pide no hacer.
#
# Los datos de la portada (`application/ld+json`) se quedan: esos sí los lee.
_NO_ES_CONTENIDO = re.compile(
    r'<script\b(?![^>]*application/ld\+json)[^>]*>.*?</script>'
    r'|<style\b[^>]*>.*?</style>'
    r'|<meta http-equiv="Content-Security-Policy"[^>]*>',
    re.S | re.I,
)
_HUELLA_EN_LA_DIRECCION = re.compile(r"\?v=[0-9a-f]{8}")
_RE_LOC = re.compile(r"<loc>([^<]+)</loc>")


class NoSeAvisa(Exception):
    """La raíz de todas las negativas de avisar. Ver `paquete.NoSeMonta`.

    `__main__` caza esta y no una lista, y una prueba recorre el módulo para
    que ninguna se quede suelta.
    """


class SinSitio(NoSeAvisa):
    """No hay sitio montado con el que comparar, o no lo montó `--sitio`."""


class SinEstado(NoSeAvisa):
    """No hay dónde apuntar lo avisado, o lo apuntado no se puede leer."""


class ProduccionQueNoCuadra(NoSeAvisa):
    """Lo que sirve producción no es lo que hay montado aquí."""


class ClaveQueNoSeSirve(NoSeAvisa):
    """La clave no está en producción, o el fichero no la lleva."""


class BuscadorQueSeNiega(NoSeAvisa):
    """El buscador contestó otra cosa que 200 o 202."""


@dataclass
class Aviso:
    paginas: int
    mandadas: list[str]
    contesto: int | None
    primera: bool


def lo_que_lee_un_buscador(crudo: bytes) -> str:
    """La huella del contenido de una página, sin lo que no es contenido.

    También iguala los espacios y los saltos de línea: montado en Windows, el
    sitio sale con CRLF, y en Vercel con LF.
    """
    texto = _NO_ES_CONTENIDO.sub("", crudo.decode("utf-8"))
    texto = _HUELLA_EN_LA_DIRECCION.sub("", texto)
    return hashlib.sha256(" ".join(texto.split()).encode("utf-8")).hexdigest()


def _huella_publicada(crudo: bytes) -> str:
    """La que lleva `rueda.json` en producción: la del fichero con LF."""
    return hashlib.sha256(crudo.replace(b"\r\n", b"\n")).hexdigest()


def _fichero(direccion: str, sitio: Path) -> Path:
    """La página montada que se sirve en esa dirección. Ver `paquete._direccion`."""
    if direccion == paquete.DOMINIO + "/":
        return sitio / "index.html"
    return sitio / (direccion.removeprefix(paquete.DOMINIO + "/") + ".html")


def lo_que_cambio(antes: dict[str, str], ahora: dict[str, str]) -> list[str]:
    """Las direcciones nuevas, las cambiadas y las que ya no están.

    Las que ya no están también: el protocolo pide avisar de lo que se borra,
    para que el buscador vuelva, vea el 404 o la mudanza y la quite.
    """
    return sorted(
        {d for d, huella in ahora.items() if antes.get(d) != huella}
        | (antes.keys() - ahora.keys())
    )


def estado_por_defecto() -> Path:
    """El fichero de lo avisado, en la carpeta común de git."""
    try:
        salida = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True, check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise SinEstado(
            "No se encuentra el repositorio git donde apuntar lo avisado, y sin "
            "apuntarlo no se sabe qué cambió. Se corre desde la copia de "
            f"Factura-e. ({error})"
        ) from error
    return Path(salida.stdout.strip()) / NOMBRE_DEL_ESTADO


def _pedir(direccion: str) -> bytes | None:
    """Lo que sirve producción en esa dirección, o None si ahí no lo sirve.

    Una redirección cuenta como que no está: la clave tiene que estar en su
    sitio y no al final de una mudanza, y lo que se compara es lo de esta
    dirección.
    """
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    ultimo: OSError | None = None
    for _ in range(_INTENTOS):
        try:
            peticion = Request(direccion, headers=_CABECERAS)
            with urlopen(peticion, timeout=_PLAZO) as respuesta:  # noqa: S310
                if respuesta.geturl() != direccion:
                    return None
                return respuesta.read()
        except HTTPError as error:
            # Un 404 es una respuesta, no un corte: no se reintenta.
            if error.code == 404:
                return None
            raise
        except OSError as error:
            ultimo = error
    assert ultimo is not None
    raise ultimo


def _mandar(cuerpo: dict) -> int:
    """Manda el aviso y devuelve el código con el que contesta el buscador.

    Sin reintentos, a diferencia de `_pedir`: un corte puede ser después de que
    el buscador lo recibiera. Si se corta, no se apunta nada, y la próxima vez
    se vuelve a mandar lo mismo, que es repetir una vez y no perderlo.
    """
    from urllib.error import HTTPError
    from urllib.request import Request, urlopen

    peticion = Request(
        PUNTO_DE_AVISO,
        data=json.dumps(cuerpo).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", **_CABECERAS},
    )
    try:
        with urlopen(peticion, timeout=_PLAZO) as respuesta:  # noqa: S310
            return respuesta.status
    except HTTPError as error:
        return error.code


def _leer_estado(estado: Path) -> dict[str, str] | None:
    if not estado.is_file():
        return None
    try:
        datos = json.loads(estado.read_text(encoding="utf-8"))
        return dict(datos["paginas"])
    except (ValueError, KeyError, TypeError) as error:
        raise SinEstado(
            f"`{estado}` no se puede leer ({error}). Si se borra, la próxima "
            "vez se toma lo publicado como punto de partida y no se avisa de "
            "nada; lo que haya cambiado desde el último aviso se queda sin "
            "avisar hasta que vuelva a cambiar."
        ) from error


def avisar(
    sitio: str | Path = "sitio",
    estado: Path | None = None,
    pedir=_pedir,
    mandar=_mandar,
) -> Aviso:
    """Avisa de lo que cambió desde el último aviso, o se niega y dice por qué.

    Todo lo que puede negarse se mira antes de mandar nada, y lo avisado se
    apunta solo cuando el buscador ha dicho que sí.
    """
    sitio = Path(sitio)
    if not (sitio / paquete.TESTIGO_DEL_SITIO).is_file():
        raise SinSitio(
            f"`{sitio}` no es un sitio montado por `--sitio`, así que no hay con "
            "qué comparar lo que sirve producción. Móntalo antes desde el mismo "
            "commit que se publicó."
        )
    mapa = sitio / "sitemap.xml"
    if not mapa.is_file():
        raise SinSitio(f"`{sitio}` no tiene sitemap.xml, que es la lista de páginas.")
    direcciones = _RE_LOC.findall(mapa.read_text(encoding="utf-8"))
    faltan = [d for d in direcciones if not _fichero(d, sitio).is_file()]
    if not direcciones or faltan:
        raise SinSitio(
            f"El sitemap de `{sitio}` nombra {len(faltan)} página(s) que no están "
            f"montadas ({', '.join(faltan[:3])}), o no nombra ninguna."
        )
    estado = estado if estado is not None else estado_por_defecto()
    antes = _leer_estado(estado)

    # Que producción sirva lo montado aquí, página por página. Se miran todas
    # las HTML y no solo las cambiadas: si una sola no cuadra, lo montado no es
    # lo publicado, y lo que se calcule de aquí no vale para nada.
    crudo = pedir(f"{paquete.DOMINIO}/dist/{paquete.NOMBRE_DE_LA_RUEDA}")
    if crudo is None:
        raise ProduccionQueNoCuadra(
            f"Producción no sirve `dist/{paquete.NOMBRE_DE_LA_RUEDA}`, que es "
            "donde se ve qué está publicado. No se manda nada."
        )
    publicadas = {
        ruta: huella
        for ruta, huella in json.loads(crudo)["huellas"].items()
        if ruta.endswith(".html")
    }
    montadas = {
        p.relative_to(sitio).as_posix(): _huella_publicada(p.read_bytes())
        for p in sitio.rglob("*.html")
    }
    distintas = sorted(
        r for r in publicadas.keys() | montadas.keys()
        if publicadas.get(r) != montadas.get(r)
    )
    if distintas:
        raise ProduccionQueNoCuadra(
            f"Producción no sirve lo montado en `{sitio}`: {len(distintas)} "
            f"página(s) distintas ({', '.join(distintas[:3])}). O el despliegue "
            "no ha terminado, y basta esperar un minuto y repetir, o lo montado "
            "no es lo publicado, y hay que volver a montar con `--sitio` desde "
            "el commit que está en `main`. No se manda nada."
        )

    clave = paquete.CLAVE_DE_INDEXNOW
    donde = f"{paquete.DOMINIO}/{clave}.txt"
    servida = pedir(donde)
    if servida is None or servida.decode("utf-8", "replace").strip() != clave:
        raise ClaveQueNoSeSirve(
            f"`{donde}` no está en producción o no lleva la clave. Sin ella el "
            "buscador contesta 403 y no indexa nada de lo avisado. La escribe "
            "`--sitio`; si falta, el despliegue no es de un montaje con IndexNow."
        )

    ahora = {d: lo_que_lee_un_buscador(_fichero(d, sitio).read_bytes()) for d in direcciones}

    def apuntar() -> None:
        estado.write_text(
            json.dumps({"paginas": ahora}, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    if antes is None:
        # La primera vez no se sabe qué conocen ya los buscadores, y mandar las
        # 418 es lo que el protocolo pide no hacer. Lo publicado hasta hoy lo
        # conocen por el sitemap: desde aquí, solo lo nuevo.
        apuntar()
        return Aviso(paginas=len(ahora), mandadas=[], contesto=None, primera=True)

    cambiadas = lo_que_cambio(antes, ahora)
    if not cambiadas:
        return Aviso(paginas=len(ahora), mandadas=[], contesto=None, primera=False)

    contesto = mandar({
        "host": paquete.DOMINIO.removeprefix("https://"),
        "key": clave,
        "keyLocation": donde,
        "urlList": cambiadas,
    })
    if contesto not in _BUENAS:
        raise BuscadorQueSeNiega(
            f"{PUNTO_DE_AVISO} contestó {contesto}: "
            f"{_LO_QUE_DICE.get(contesto, 'una respuesta que el protocolo no describe')}. "
            f"No se apunta nada, así que las {len(cambiadas)} se vuelven a "
            "mandar la próxima vez."
        )
    apuntar()
    return Aviso(paginas=len(ahora), mandadas=cambiadas, contesto=contesto, primera=False)
