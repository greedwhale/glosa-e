# -*- coding: utf-8 -*-
"""El aviso a los buscadores, con producción de mentira y rota a propósito.

Por qué existe
--------------
`indexnow.py` habla con producción y con Bing, y lo hace al final de una
tanda, cuando ya está todo publicado. Un fallo ahí no se ve: el aviso sale o
no sale, y si avisa de lo que no es, o antes de tiempo, nadie se entera. Aquí
no se abre ninguna conexión: producción es un diccionario y el buscador una
función que apunta lo que le mandan.

Lo que se comprueba, en este orden de importancia:

1. **Que no se mande nada cuando no toca**: producción sirve otra cosa, la
   clave no está, o el buscador dice que no. Y que entonces no se apunte nada,
   para que la próxima vez se mande lo mismo.
2. **Que solo se avise de lo que cambió**, y que tocar el estilo no cuente.
3. Que la primera vez solo se apunte, y que lo apuntado sirva la vez siguiente.
"""
from __future__ import annotations

import hashlib
import inspect
import json
from pathlib import Path

import pytest

from validador import indexnow, paquete

D = paquete.DOMINIO
CLAVE = paquete.CLAVE_DE_INDEXNOW


def _pagina(texto: str, huella: str = "0123abcd") -> bytes:
    return (
        "<!DOCTYPE html>\n<html><head>\n"
        '<meta charset="utf-8">\n'
        "<meta http-equiv=\"Content-Security-Policy\" content=\"script-src "
        f"'sha256-{huella}'\">\n"
        f'<link rel="stylesheet" href="./glosa.css?v={huella}">\n'
        "<style>body { color: red }</style>\n"
        f"<title>{texto}</title>\n</head>\n<body><p>{texto}</p>\n"
        f'<script src="./glosa.js?v={huella}"></script>\n'
        "<script>var tema = 1;</script>\n</body></html>\n"
    ).encode("utf-8")


class Produccion:
    """Lo que sirve producción y lo que recibe el buscador, sin red."""

    def __init__(self, sitio: Path):
        self.sitio = sitio
        self.ficheros: dict[str, bytes] = {}
        self.mandado: list[dict] = []
        self.contesta = 200
        self.publicar()

    def publicar(self) -> None:
        """Lo de producción pasa a ser lo montado, como al desplegar."""
        huellas = {
            p.relative_to(self.sitio).as_posix():
                hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for p in self.sitio.rglob("*") if p.is_file()
        }
        self.ficheros = {
            f"{D}/dist/{paquete.NOMBRE_DE_LA_RUEDA}":
                json.dumps({"rueda": "x.whl", "huellas": huellas}).encode(),
            f"{D}/{CLAVE}.txt": CLAVE.encode(),
        }

    def pedir(self, direccion: str) -> bytes | None:
        return self.ficheros.get(direccion)

    def mandar(self, cuerpo: dict) -> int:
        self.mandado.append(cuerpo)
        return self.contesta


@pytest.fixture
def sitio(tmp_path):
    """Un sitio montado en pequeño: el testigo, tres páginas y su sitemap."""
    carpeta = tmp_path / "sitio"
    carpeta.mkdir()
    (carpeta / paquete.TESTIGO_DEL_SITIO).write_text("montado\n", encoding="utf-8")
    (carpeta / "index.html").write_bytes(_pagina("Portada"))
    (carpeta / "tesis.html").write_bytes(_pagina("Tesis"))
    (carpeta / "codigo-BR-01.html").write_bytes(_pagina("BR-01"))
    (carpeta / "404.html").write_bytes(_pagina("No está"))
    _sitemap(carpeta, ["", "tesis", "codigo-BR-01"])
    return carpeta


def _sitemap(carpeta: Path, nombres: list[str]) -> None:
    urls = "".join(f"<url><loc>{D}/{n}</loc></url>\n" for n in nombres)
    (carpeta / "sitemap.xml").write_text(f"<urlset>\n{urls}</urlset>\n", encoding="utf-8")


@pytest.fixture
def estado(tmp_path):
    return tmp_path / "git" / indexnow.NOMBRE_DEL_ESTADO


def _avisar(sitio, estado, prod):
    (estado.parent).mkdir(parents=True, exist_ok=True)
    return indexnow.avisar(sitio, estado, pedir=prod.pedir, mandar=prod.mandar)


def _primera_vez(sitio, estado):
    prod = Produccion(sitio)
    _avisar(sitio, estado, prod)
    return prod


class TestLoQueCuentaComoCambio:
    """Lo que lee un buscador, y no lo que cambia al tocar lo compartido."""

    def test_la_huella_del_estilo_y_del_cargador_no_cuenta(self):
        assert (indexnow.lo_que_lee_un_buscador(_pagina("Hola", "0123abcd"))
                == indexnow.lo_que_lee_un_buscador(_pagina("Hola", "fedc9876")))

    def test_los_saltos_de_windows_no_cuentan(self):
        crudo = _pagina("Hola")
        assert (indexnow.lo_que_lee_un_buscador(crudo)
                == indexnow.lo_que_lee_un_buscador(crudo.replace(b"\n", b"\r\n")))

    def test_un_script_o_un_estilo_en_linea_no_cuentan(self):
        crudo = _pagina("Hola")
        otro = crudo.replace(b"var tema = 1;", b"var tema = 2;").replace(
            b"color: red", b"color: blue")
        assert indexnow.lo_que_lee_un_buscador(crudo) == indexnow.lo_que_lee_un_buscador(otro)

    def test_el_texto_si_cuenta(self):
        assert (indexnow.lo_que_lee_un_buscador(_pagina("Hola"))
                != indexnow.lo_que_lee_un_buscador(_pagina("Adiós")))

    def test_los_datos_de_la_portada_si_cuentan(self):
        """`application/ld+json` lo lee el buscador: no se quita con los scripts."""
        def con_datos(nombre):
            return _pagina("Hola").replace(
                b"</head>",
                b'<script type="application/ld+json">{"name": "' + nombre + b'"}</script></head>')
        assert (indexnow.lo_que_lee_un_buscador(con_datos(b"Glosa-e"))
                != indexnow.lo_que_lee_un_buscador(con_datos(b"Otra")))

    def test_lo_que_cambio_lleva_las_nuevas_las_cambiadas_y_las_quitadas(self):
        antes = {"a": "1", "b": "2", "c": "3"}
        ahora = {"a": "1", "b": "9", "d": "4"}
        assert indexnow.lo_que_cambio(antes, ahora) == ["b", "c", "d"]


class TestLaPrimeraVez:

    def test_solo_apunta_y_no_manda_nada(self, sitio, estado):
        prod = Produccion(sitio)
        aviso = _avisar(sitio, estado, prod)
        assert aviso.primera and aviso.mandadas == [] and aviso.contesto is None
        assert prod.mandado == []
        apuntadas = json.loads(estado.read_text(encoding="utf-8"))["paginas"]
        assert sorted(apuntadas) == [f"{D}/", f"{D}/codigo-BR-01", f"{D}/tesis"]

    def test_la_segunda_sin_cambios_tampoco_manda(self, sitio, estado):
        prod = _primera_vez(sitio, estado)
        aviso = _avisar(sitio, estado, prod)
        assert not aviso.primera and aviso.mandadas == []
        assert prod.mandado == []


class TestSoloLoQueCambio:

    def test_avisa_de_la_pagina_cambiada_y_de_ninguna_mas(self, sitio, estado):
        prod = _primera_vez(sitio, estado)
        (sitio / "tesis.html").write_bytes(_pagina("Tesis, corregida"))
        prod.publicar()
        aviso = _avisar(sitio, estado, prod)
        assert aviso.mandadas == [f"{D}/tesis"] and aviso.contesto == 200
        assert prod.mandado == [{
            "host": "www.glosa-e.com",
            "key": CLAVE,
            "keyLocation": f"{D}/{CLAVE}.txt",
            "urlList": [f"{D}/tesis"],
        }]

    def test_lo_avisado_se_apunta_y_no_se_repite(self, sitio, estado):
        prod = _primera_vez(sitio, estado)
        (sitio / "tesis.html").write_bytes(_pagina("Tesis, corregida"))
        prod.publicar()
        _avisar(sitio, estado, prod)
        assert _avisar(sitio, estado, prod).mandadas == []
        assert len(prod.mandado) == 1

    def test_tocar_el_estilo_de_todas_no_avisa_de_ninguna(self, sitio, estado):
        """El caso por el que existe `lo_que_lee_un_buscador`: sin él, cambiar
        `glosa.css` mandaba el sitio entero."""
        prod = _primera_vez(sitio, estado)
        for nombre, texto in (("index", "Portada"), ("tesis", "Tesis"),
                              ("codigo-BR-01", "BR-01")):
            (sitio / f"{nombre}.html").write_bytes(_pagina(texto, "99999999"))
        prod.publicar()
        assert _avisar(sitio, estado, prod).mandadas == []
        assert prod.mandado == []

    def test_una_pagina_quitada_tambien_se_avisa(self, sitio, estado):
        prod = _primera_vez(sitio, estado)
        (sitio / "codigo-BR-01.html").unlink()
        _sitemap(sitio, ["", "tesis"])
        prod.publicar()
        assert _avisar(sitio, estado, prod).mandadas == [f"{D}/codigo-BR-01"]

    def test_lo_202_de_la_primera_vez_vale(self, sitio, estado):
        prod = _primera_vez(sitio, estado)
        (sitio / "tesis.html").write_bytes(_pagina("Tesis, corregida"))
        prod.publicar()
        prod.contesta = 202
        assert _avisar(sitio, estado, prod).contesto == 202


class TestNoSeMandaNada:
    """Cada negativa, provocada. En todas: ni se manda ni se apunta."""

    def _con_un_cambio(self, sitio, estado):
        prod = _primera_vez(sitio, estado)
        (sitio / "tesis.html").write_bytes(_pagina("Tesis, corregida"))
        return prod, estado.read_text(encoding="utf-8")

    def test_si_el_despliegue_no_ha_terminado(self, sitio, estado):
        """Producción sigue sirviendo lo de antes: el cambio no está publicado."""
        prod, apuntado = self._con_un_cambio(sitio, estado)
        with pytest.raises(indexnow.ProduccionQueNoCuadra, match="tesis.html"):
            _avisar(sitio, estado, prod)
        assert prod.mandado == []
        assert estado.read_text(encoding="utf-8") == apuntado

    def test_si_produccion_no_sirve_la_rueda(self, sitio, estado):
        prod, apuntado = self._con_un_cambio(sitio, estado)
        prod.publicar()
        del prod.ficheros[f"{D}/dist/{paquete.NOMBRE_DE_LA_RUEDA}"]
        with pytest.raises(indexnow.ProduccionQueNoCuadra):
            _avisar(sitio, estado, prod)
        assert prod.mandado == [] and estado.read_text(encoding="utf-8") == apuntado

    def test_si_falta_la_clave(self, sitio, estado):
        prod, apuntado = self._con_un_cambio(sitio, estado)
        prod.publicar()
        del prod.ficheros[f"{D}/{CLAVE}.txt"]
        with pytest.raises(indexnow.ClaveQueNoSeSirve):
            _avisar(sitio, estado, prod)
        assert prod.mandado == [] and estado.read_text(encoding="utf-8") == apuntado

    def test_si_la_clave_servida_es_otra(self, sitio, estado):
        prod, apuntado = self._con_un_cambio(sitio, estado)
        prod.publicar()
        prod.ficheros[f"{D}/{CLAVE}.txt"] = b"otra-clave-cualquiera"
        with pytest.raises(indexnow.ClaveQueNoSeSirve):
            _avisar(sitio, estado, prod)
        assert prod.mandado == []

    def test_si_el_buscador_dice_que_no_no_se_apunta(self, sitio, estado):
        prod, apuntado = self._con_un_cambio(sitio, estado)
        prod.publicar()
        prod.contesta = 403
        with pytest.raises(indexnow.BuscadorQueSeNiega, match="403"):
            _avisar(sitio, estado, prod)
        assert estado.read_text(encoding="utf-8") == apuntado
        # Y la próxima vez se manda lo mismo.
        prod.contesta = 200
        assert _avisar(sitio, estado, prod).mandadas == [f"{D}/tesis"]

    def test_sin_sitio_montado(self, tmp_path, estado):
        vacia = tmp_path / "vacia"
        vacia.mkdir()
        prod = Produccion(vacia)
        with pytest.raises(indexnow.SinSitio):
            _avisar(vacia, estado, prod)

    def test_con_una_pagina_del_sitemap_sin_montar(self, sitio, estado):
        (sitio / "tesis.html").unlink()
        with pytest.raises(indexnow.SinSitio, match="tesis"):
            _avisar(sitio, estado, Produccion(sitio))

    def test_con_lo_apuntado_ilegible(self, sitio, estado):
        estado.parent.mkdir(parents=True)
        estado.write_text("{ esto no es json", encoding="utf-8")
        with pytest.raises(indexnow.SinEstado):
            _avisar(sitio, estado, Produccion(sitio))


class TestLasNegativasCuelganDeSuRaiz:
    """Como en `paquete`: la que se escriba mañana ya está cazada."""

    def test_todas_heredan_de_no_se_avisa(self):
        sueltas = [
            nombre for nombre, cosa in vars(indexnow).items()
            if inspect.isclass(cosa) and issubclass(cosa, Exception)
            and cosa.__module__ == indexnow.__name__
            and cosa is not indexnow.NoSeAvisa
            and not issubclass(cosa, indexnow.NoSeAvisa)
        ]
        assert not sueltas, sueltas

    def test_no_se_mezclan_con_las_de_montar(self):
        assert not issubclass(indexnow.NoSeAvisa, paquete.NoSeMonta)


class TestLaOrden:
    """`--avisar-indexnow`: lo que dice y con qué código sale."""

    def test_una_negativa_sale_con_2_y_cuenta_el_motivo(self, monkeypatch, capsys):
        from validador import __main__

        def negarse(*_, **__):
            raise indexnow.ProduccionQueNoCuadra("el despliegue de mentira")

        monkeypatch.setattr(indexnow, "avisar", negarse)
        assert __main__.main(["--avisar-indexnow"]) == 2
        error = capsys.readouterr().err
        assert "No se ha avisado de nada" in error
        assert "el despliegue de mentira" in error

    def test_un_corte_sale_con_2(self, monkeypatch, capsys):
        from validador import __main__

        def cortarse(*_, **__):
            raise TimeoutError("se colgó")

        monkeypatch.setattr(indexnow, "avisar", cortarse)
        assert __main__.main(["--avisar-indexnow", "otra"]) == 2
        assert "No se ha apuntado nada" in capsys.readouterr().err

    def test_lo_avisado_sale_por_pantalla(self, monkeypatch, capsys):
        from validador import __main__

        monkeypatch.setattr(indexnow, "avisar", lambda sitio: indexnow.Aviso(
            paginas=3, mandadas=[f"{D}/tesis"], contesto=202, primera=False))
        assert __main__.main(["--avisar-indexnow"]) == 0
        salida = capsys.readouterr().out
        assert "Avisado de 1 página(s)" in salida and "202" in salida
        assert f"{D}/tesis" in salida


class TestLaClave:

    def test_tiene_la_forma_que_pide_el_protocolo(self):
        """De 8 a 128 caracteres, letras, cifras o guiones (indexnow.org)."""
        import re
        assert re.fullmatch(r"[A-Za-z0-9-]{8,128}", CLAVE)
