"""La mudanza a Cloudflare: que los dos alojamientos sirvan lo mismo.

Preparada el 15-11-2026. Las reglas del alojamiento se escriben una vez, en
`vercel.json`, y `--sitio` las traduce a `_headers` y `_redirects` para
Cloudflare (`validador/alojamiento.py`). Aquí se vigila lo que se separaría en
silencio: una regla que no se traduce, una configuración de Cloudflare que
apunta a otra carpeta, una versión que se mueve sola, y una herramienta de
comparar que no ve lo que tiene que ver.

Cada negativa se prueba provocándola, como pide CLAUDE.md.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from herramientas import comparar_alojamiento, construir
from validador import alojamiento, paquete

from tests.test_paquete import _armar_repositorio, _montar

RAIZ = Path(__file__).resolve().parent.parent
VERCEL = json.loads((RAIZ / "vercel.json").read_text(encoding="utf-8"))


def _wrangler() -> dict:
    """`wrangler.jsonc` sin sus comentarios, que son de línea entera."""
    texto = (RAIZ / "wrangler.jsonc").read_text(encoding="utf-8")
    return json.loads("\n".join(l for l in texto.splitlines()
                                if not l.lstrip().startswith("//")))


def _bloques(cabeceras: str) -> dict[str, list[str]]:
    bloques: dict[str, list[str]] = {}
    actual = None
    for linea in cabeceras.splitlines():
        if not linea or linea.startswith("#"):
            continue
        if not linea.startswith(" "):
            actual = linea
            bloques[actual] = []
        else:
            bloques[actual].append(linea.strip())
    return bloques


class TestLaTraduccion:
    def test_cada_regla_de_vercel_llega_a_cloudflare(self):
        bloques = _bloques(alojamiento.cabeceras(VERCEL))
        assert len(bloques) == len(VERCEL["headers"])
        for regla in VERCEL["headers"]:
            ruta = regla["source"].replace("(.*)", "*")
            for c in regla["headers"]:
                assert f"{c['key']}: {c['value']}" in bloques[ruta], (ruta, c)

    def test_las_paginas_no_se_reescriben_y_siguen_revalidando(self):
        """`no-transform` apaga la ofuscación de correos de Cloudflare, y el
        resto del valor es el que Cloudflare pondría: sin él, la portada
        podría quedarse en la caché del navegador."""
        todo = _bloques(alojamiento.cabeceras(VERCEL))["/*"]
        assert f"Cache-Control: {alojamiento.CACHE_DE_LAS_PAGINAS}" in todo
        assert "no-transform" in alojamiento.CACHE_DE_LAS_PAGINAS
        assert "must-revalidate" in alojamiento.CACHE_DE_LAS_PAGINAS

    def test_lo_que_se_vuelve_a_poner_se_suelta_antes(self):
        """Si no, Cloudflare une los dos `Cache-Control` con una coma y la
        caché de un año queda con dos `max-age` que se contradicen."""
        for ruta, lineas in _bloques(alojamiento.cabeceras(VERCEL)).items():
            if ruta == "/*":
                continue
            for i, linea in enumerate(lineas):
                if linea.startswith("Cache-Control:"):
                    assert i > 0 and lineas[i - 1] == "! Cache-Control", ruta

    def test_las_redirecciones_van_todas_y_permanentes(self):
        lineas = [l for l in alojamiento.redirecciones(VERCEL).splitlines()
                  if l and not l.startswith("#")]
        assert len(lineas) == 3 * len(VERCEL["redirects"])
        for regla in VERCEL["redirects"]:
            assert f"{regla['source']} {regla['destination']} 308" in lineas

    def test_la_forma_html_y_la_de_la_barra_llevan_al_mismo_sitio(self):
        """El 19-11-2026, cuatro días después de la mudanza, Search Console
        avisó de páginas nuevas en 404: `/tesis.html` o `/codigo-BR-AE-1.html`,
        que en Vercel llevaban a la página nueva (su `cleanUrls` quita el
        `.html` y luego aplica la redirección) y en Cloudflare no encajaban
        con ninguna regla. Lo mismo con la barra final."""
        lineas = set(alojamiento.redirecciones(VERCEL).splitlines())
        for regla in VERCEL["redirects"]:
            for forma in (f"{regla['source']}.html", f"{regla['source']}/"):
                assert f"{forma} {regla['destination']} 308" in lineas, forma

    def test_una_forma_que_ya_es_regla_no_se_repite(self):
        datos = {"redirects": [
            {"source": "/a", "destination": "/b", "permanent": True},
            {"source": "/a.html", "destination": "/c", "permanent": True},
        ]}
        lineas = [l for l in alojamiento.redirecciones(datos).splitlines()
                  if l and not l.startswith("#")]
        assert lineas.count("/a.html /c 308") == 1
        assert not any(l.startswith("/a.html /b") for l in lineas)

    def test_dentro_de_los_limites_del_plan_gratuito(self):
        assert len(VERCEL["headers"]) <= alojamiento.MAXIMO_DE_REGLAS_DE_CABECERAS
        lineas = [l for l in alojamiento.redirecciones(VERCEL).splitlines()
                  if l and not l.startswith("#")]
        assert len(lineas) <= alojamiento.MAXIMO_DE_REDIRECCIONES

    def test_pasarse_del_limite_con_las_formas_se_niega(self, monkeypatch):
        monkeypatch.setattr(alojamiento, "MAXIMO_DE_REDIRECCIONES", 3 * len(VERCEL["redirects"]) - 1)
        with pytest.raises(ValueError, match="redirecciones"):
            alojamiento.redirecciones(VERCEL)

    @pytest.mark.parametrize("fuente", ["/:camino*", "/(a|b)", "/x/(.*)/y/(.*)"])
    def test_lo_que_no_se_sabe_traducir_se_niega(self, fuente):
        datos = {"headers": [{"source": "/(.*)", "headers": []},
                             {"source": fuente, "headers": [{"key": "X", "value": "1"}]}]}
        with pytest.raises(ValueError):
            alojamiento.cabeceras(datos)

    def test_una_redireccion_con_parametros_se_niega(self):
        with pytest.raises(ValueError):
            alojamiento.redirecciones({"redirects": [
                {"source": "/viejo/:nombre", "destination": "/nuevo/:nombre",
                 "permanent": True}]})

    def test_sin_regla_para_todo_el_sitio_se_niega(self):
        with pytest.raises(ValueError):
            alojamiento.cabeceras({"headers": [
                {"source": "/glosa.js", "headers": [{"key": "X", "value": "1"}]}]})


class TestElMontaje:
    def test_escribe_las_dos_y_fuera_del_manifiesto(self, tmp_path):
        repositorio = _armar_repositorio(tmp_path)
        _montar(repositorio)
        sitio = repositorio / "sitio"
        assert (sitio / "_headers").read_text(encoding="utf-8") == alojamiento.cabeceras(VERCEL)
        assert (sitio / "_redirects").read_text(encoding="utf-8") == alojamiento.redirecciones(VERCEL)
        huellas = json.loads((sitio / "dist" / "rueda.json").read_text(encoding="utf-8"))["huellas"]
        assert "_headers" not in huellas and "_redirects" not in huellas

    def test_una_regla_que_no_se_traduce_no_monta_nada(self, tmp_path):
        """Provocado: un `vercel.json` con un parámetro con nombre."""
        repositorio = _armar_repositorio(tmp_path)
        roto = dict(VERCEL, redirects=[{"source": "/a/:b", "destination": "/c",
                                        "permanent": True}])
        configuracion = tmp_path / "vercel-roto.json"
        configuracion.write_text(json.dumps(roto), encoding="utf-8")
        with pytest.raises(paquete.AlojamientoQueNoSeTraduce):
            paquete.montar_sitio(
                repositorio / "sitio", pagina=repositorio / "web",
                ruedas=repositorio / "dist", ejemplos=repositorio / "ejemplos",
                pyodide=repositorio / "vendor" / "pyodide",
                configuracion=configuracion)
        assert not (repositorio / "sitio").exists()

    def test_sin_vercel_json_no_monta(self, tmp_path):
        repositorio = _armar_repositorio(tmp_path)
        with pytest.raises(paquete.AlojamientoQueNoSeTraduce):
            paquete.montar_sitio(
                repositorio / "sitio", pagina=repositorio / "web",
                ruedas=repositorio / "dist", ejemplos=repositorio / "ejemplos",
                pyodide=repositorio / "vendor" / "pyodide",
                configuracion=tmp_path / "no-esta.json")


class TestLaConfiguracionDeCloudflare:
    def test_publica_la_carpeta_que_monta_vercel(self):
        assert _wrangler()["assets"]["directory"] == "./" + VERCEL["outputDirectory"]

    def test_sin_script_y_con_las_direcciones_de_vercel(self):
        """Sin `main` ninguna petición ejecuta código: todas son de ficheros,
        que el plan gratuito sirve sin cuota. Y las direcciones, como
        `cleanUrls` con `trailingSlash: false`, con nuestro 404."""
        w = _wrangler()
        assert "main" not in w
        assert VERCEL["cleanUrls"] is True and VERCEL["trailingSlash"] is False
        assert w["assets"]["html_handling"] == "drop-trailing-slash"
        assert w["assets"]["not_found_handling"] == "404-page"

    def test_fecha_fijada(self):
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", _wrangler()["compatibility_date"])

    def test_wrangler_fijado_a_una_version_exacta(self):
        paquete_npm = json.loads((RAIZ / "package.json").read_text(encoding="utf-8"))
        assert re.fullmatch(r"\d+\.\d+\.\d+", paquete_npm["devDependencies"]["wrangler"])
        assert not paquete_npm.get("dependencies")


class TestLaConstruccion:
    def test_corre_la_orden_de_vercel(self):
        assert construir.orden_de_construccion() == VERCEL["buildCommand"]

    def test_el_python_es_el_de_la_suite(self):
        flujo = (RAIZ / ".github" / "workflows" / "pruebas.yml").read_text(encoding="utf-8")
        assert f'python-version: "{construir.python_de_la_suite()}"' in flujo

    def test_con_otro_python_se_niega_sin_construir(self, monkeypatch, capsys):
        """Provocado: un Python que no es el de la suite sale con 2 y no
        llega a ejecutar la orden."""
        monkeypatch.setattr(construir.platform, "python_version", lambda: "3.0.0")
        corrida = []
        monkeypatch.setattr(construir.subprocess, "run",
                            lambda *a, **k: corrida.append(a))
        assert construir.main() == 2
        assert not corrida
        assert "PYTHON_VERSION" in capsys.readouterr().err


class TestLaComparacion:
    """`herramientas/comparar_alojamiento.py`, contra un alojamiento de
    mentira: cada cosa que tiene que ver, provocada una a una."""

    HTML = b"<!doctype html><title>legal</title><p>hola</p>"
    NO_ENCONTRADA = b"<!doctype html><title>404</title>"

    def _alojamiento(self, monkeypatch, estropear=lambda ruta, r: r):
        ficheros = {
            "legal.html": self.HTML,
            "404.html": self.NO_ENCONTRADA,
            "glosa.js": b"// js",
        }
        manifiesto = json.dumps({"rueda": "x/y.whl", "huellas": {
            n: hashlib.sha256(b).hexdigest() for n, b in ficheros.items()}}).encode()
        configuracion = {
            "headers": [
                {"source": "/(.*)", "headers": [{"key": "X-Content-Type-Options", "value": "nosniff"}]},
                {"source": "/glosa.js", "headers": [{"key": "Cache-Control", "value": "public, max-age=31536000, immutable"}]},
                {"source": "/dist/rueda.json", "headers": [{"key": "Cache-Control", "value": "public, max-age=0, must-revalidate"}]},
            ],
            "redirects": [{"source": "/tesis", "destination": "/sobre", "permanent": True}],
        }
        R = comparar_alojamiento.Respuesta
        base_h = {"x-content-type-options": "nosniff"}
        revalida = dict(base_h, **{"cache-control": "public, max-age=0, must-revalidate"})

        def servir(url, seguir=True):
            ruta = url.split("://", 1)[1].split("/", 1)[1] if "/" in url.split("://", 1)[1] else ""
            if url.startswith("http://"):
                return estropear("http://" + ruta, R(301, {"location": "https://" + url[7:]}, b""))
            if ruta == "dist/rueda.json":
                r = R(200, dict(revalida), manifiesto)
            elif ruta == "tesis":
                r = R(308, {"location": "/sobre"}, b"")
            elif ruta in ("tesis.html", "tesis/"):
                # Como Vercel: primero quita el `.html` o la barra, y luego
                # redirige. Dos saltos permanentes valen.
                r = R(308, {"location": "https://prueba/tesis"}, b"")
            elif ruta in ("legal.html", "legal/") and not seguir:
                r = R(308, {"location": "/legal"}, b"")
            elif ruta in ("legal", "legal.html"):
                r = R(200, dict(revalida), self.HTML)
            elif ruta == "glosa.js":
                r = R(200, dict(base_h, **{"cache-control": "public, max-age=31536000, immutable"}), ficheros["glosa.js"])
            elif ruta == "404.html":
                r = R(200, dict(revalida), self.NO_ENCONTRADA)
            elif ruta == "":
                r = R(200, dict(revalida), self.HTML)
            else:
                r = R(404, dict(revalida), self.NO_ENCONTRADA)
            return estropear(ruta, r)

        monkeypatch.setattr(comparar_alojamiento, "pedir", servir)
        return configuracion

    def _comprobar(self, tmp_path, configuracion):
        fichero = tmp_path / "vercel.json"
        fichero.write_text(json.dumps(configuracion), encoding="utf-8")
        return comparar_alojamiento.comprobar("https://prueba", fichero)

    def test_un_alojamiento_bueno_sale_limpio(self, monkeypatch, tmp_path):
        assert self._comprobar(tmp_path, self._alojamiento(monkeypatch)) == []

    def test_ve_una_pagina_reescrita(self, monkeypatch, tmp_path):
        def con_correos_ofuscados(ruta, r):
            if ruta == "legal.html" and r.estado == 200:
                r.cuerpo += b'<script src="/cdn-cgi/scripts/x/email-decode.min.js"></script>'
            return r
        fallos = self._comprobar(tmp_path, self._alojamiento(monkeypatch, con_correos_ofuscados))
        assert any("bytes" in f for f in fallos)
        assert any("/cdn-cgi/" in f for f in fallos)

    def test_ve_una_pagina_guardada_un_ano(self, monkeypatch, tmp_path):
        def congelado(ruta, r):
            if ruta == "legal.html":
                r.cabeceras["cache-control"] = "public, max-age=31536000, immutable"
            return r
        fallos = self._comprobar(tmp_path, self._alojamiento(monkeypatch, congelado))
        assert any("revalidarse" in f for f in fallos)

    def test_ve_una_cookie(self, monkeypatch, tmp_path):
        def con_cookie(ruta, r):
            if ruta == "glosa.js":
                r.cookies = ["__cf_bm=abc; Secure"]
            return r
        fallos = self._comprobar(tmp_path, self._alojamiento(monkeypatch, con_cookie))
        assert any("cookies" in f for f in fallos)

    def test_ve_una_redireccion_temporal(self, monkeypatch, tmp_path):
        def temporal(ruta, r):
            if ruta == "tesis":
                r.estado = 302
            return r
        fallos = self._comprobar(tmp_path, self._alojamiento(monkeypatch, temporal))
        assert any("/tesis" in f for f in fallos)

    @pytest.mark.parametrize("forma", ["tesis.html", "tesis/"])
    def test_ve_la_forma_vieja_de_una_redireccion_en_404(self, monkeypatch, tmp_path, forma):
        """Lo que se escapó en la mudanza: Cloudflare contestaba 404 a
        `/tesis.html` y la comparación solo miraba `/tesis`."""
        def sin_forma(ruta, r):
            if ruta == forma:
                r.estado, r.cabeceras = 404, {}
            return r
        fallos = self._comprobar(tmp_path, self._alojamiento(monkeypatch, sin_forma))
        assert any(f"/{forma}" in f for f in fallos)

    def test_ve_una_cadena_que_no_acaba_en_el_destino(self, monkeypatch, tmp_path):
        def a_otro_sitio(ruta, r):
            if ruta == "tesis.html":
                r.cabeceras = {"location": "https://prueba/legal"}
            return r
        fallos = self._comprobar(tmp_path, self._alojamiento(monkeypatch, a_otro_sitio))
        assert any("/tesis.html" in f for f in fallos)

    def test_ve_http_sin_pasar_a_https(self, monkeypatch, tmp_path):
        """La otra que se escapó: `http://` servía la página con un 200, y en
        Vercel llevaba a `https://` con un 308."""
        def sin_https(ruta, r):
            if ruta.startswith("http://"):
                r.estado, r.cabeceras = 200, {}
            return r
        fallos = self._comprobar(tmp_path, self._alojamiento(monkeypatch, sin_https))
        assert any(f.startswith("http://") for f in fallos)

    def test_la_direccion_de_prueba_no_se_mira_por_http(self, monkeypatch, tmp_path):
        """`*.workers.dev` no es la que conoce Google, y "Usar siempre HTTPS"
        es de la zona `glosa-e.com`: medido el 19-11-2026, la de prueba
        contesta 200 por `http://`."""
        def sin_https(ruta, r):
            if ruta.startswith("http://"):
                r.estado, r.cabeceras = 200, {}
            return r
        configuracion = self._alojamiento(monkeypatch, sin_https)
        fichero = tmp_path / "vercel.json"
        fichero.write_text(json.dumps(configuracion), encoding="utf-8")
        fallos = comparar_alojamiento.comprobar("https://glosa.prueba.workers.dev", fichero)
        assert not any(f.startswith("http://") for f in fallos)

    def test_un_corte_al_leer_un_3xx_se_reintenta(self, monkeypatch):
        """El 19-11-2026 la comparación contra producción se cayó entera por un
        `TimeoutError` al leer el cuerpo de una redirección: esa lectura iba
        fuera del reintento."""
        import io
        import urllib.error

        class Cuerpo(io.BytesIO):
            def __init__(self, cortar):
                super().__init__(b"")
                self.cortar = cortar

            def read(self, *a):
                if self.cortar:
                    raise TimeoutError("The read operation timed out")
                return b""

        import email.message

        cabeceras = email.message.Message()
        cabeceras["Location"] = "/sobre"
        veces = []

        def abrir(peticion, timeout=None):
            veces.append(1)
            raise urllib.error.HTTPError(peticion.full_url, 308, "Permanent Redirect",
                                         cabeceras, Cuerpo(len(veces) == 1))

        monkeypatch.setattr(comparar_alojamiento._NO_SIGUE, "open", abrir)
        monkeypatch.setattr(comparar_alojamiento.time, "sleep", lambda s: None)
        r = comparar_alojamiento.pedir("https://prueba/tesis.html", seguir=False)
        assert (r.estado, r.cabeceras["location"], len(veces)) == (308, "/sobre", 2)

    def test_ve_un_404_que_no_es_el_nuestro(self, monkeypatch, tmp_path):
        def generico(ruta, r):
            if r.estado == 404:
                r.cuerpo = b"NOT_FOUND"
            return r
        fallos = self._comprobar(tmp_path, self._alojamiento(monkeypatch, generico))
        assert any("404" in f for f in fallos)

    def test_ve_las_mayusculas_que_no_distingue(self, monkeypatch, tmp_path):
        def sin_mayusculas(ruta, r):
            if ruta == "codigo-br-01":
                r.estado = 200
            return r
        fallos = self._comprobar(tmp_path, self._alojamiento(monkeypatch, sin_mayusculas))
        assert any("/codigo-br-01" in f for f in fallos)
