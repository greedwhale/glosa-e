# -*- coding: utf-8 -*-
"""El guía: lo que contesta, de dónde lo saca y a dónde manda.

La búsqueda corre en el navegador y aquí no hay con qué ejecutar JavaScript,
así que lo que se prueba es la implementación de `validador/guia.py`, que es
la que calcula el índice y la que fija qué tiene que contestar el asistente.
Que la copia de `web/guia.js` conteste lo mismo se mira en el navegador,
abriendo cualquier página con `#comprobar-guia`: las comprobaciones viajan en
`guia.json` y el asistente las repite. Lo que sí se vigila desde aquí es que
esa copia siga escrita con las mismas reglas, por su forma.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pytest

from validador import bitacora, guia, pagina_incidencias
from validador.codigos import codigos_del_paquete

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web"
ASISTENTE = WEB / guia.CODIGO


def _armar(correo: str = "alguien@example.org") -> dict:
    return guia.armar(
        WEB, codigos_del_paquete(), bitacora.leer_entradas(WEB / bitacora.CARPETA),
        pagina_incidencias.nombre_de, pagina_incidencias.NOMBRE, correo)


@pytest.fixture(scope="module")
def datos() -> dict:
    return _armar()


def _ids(datos: dict, consulta: str) -> list[str]:
    return [datos["fichas"][n]["id"] for n in guia.buscar(datos, consulta)]


# --- Lo que contesta -------------------------------------------------------------


class TestLoQueContesta:
    def test_un_codigo_nombrado_gana_a_todo_lo_demas(self, datos):
        assert _ids(datos, "qué significa br-co-10") == ["BR-CO-10"]

    def test_varios_codigos_salen_en_el_orden_en_que_se_nombran(self, datos):
        assert _ids(datos, "tengo FIRMA-CADUCADA y luego BR-CO-10, y otra vez "
                           "firma-caducada") == ["FIRMA-CADUCADA", "BR-CO-10"]

    @pytest.mark.parametrize("consulta, primera", [
        ("¿desde cuándo es obligatoria?", "tema-fechas"),
        ("me rechazan la factura por el IVA", "pregunta-rechaza"),
        ("¿esto certifica que mi factura es válida?", "pregunta-certifica"),
        ("mis datos se suben a algun sitio", "pregunta-sube"),
        ("como te contacto", "sobre-escribeme"),
        ("certificado revocado", "REVOCADO"),
        ("que es una glosa", "sobre-que-es"),
        ("¿sirve para VeriFactu?", "sobre-no-hace"),
    ])
    def test_la_primera_respuesta_es_la_que_toca(self, datos, consulta, primera):
        assert _ids(datos, consulta)[0] == primera

    @pytest.mark.parametrize("consulta", [
        "", "   ", "hola", "receta de paella valenciana",
        "que pasa si no cumplo",
    ])
    def test_cuando_no_sabe_no_contesta(self, datos, consulta):
        """Es la mitad de la promesa de la página: si no encuentra, lo dice."""
        assert guia.buscar(datos, consulta) == []

    def test_nunca_da_mas_que_la_respuesta_y_sus_alternativas(self, datos):
        for consulta in ("iva", "firma", "nif", "factura electronica obligatoria"):
            assert len(guia.buscar(datos, consulta)) <= 1 + guia.OTRAS

    def test_facturae_no_se_confunde_con_factura(self):
        assert guia.trocear("Facturae") == ["facturae"]
        assert guia.trocear("facturas") != guia.trocear("Facturae")

    def test_los_acentos_y_las_mayusculas_no_cambian_la_pregunta(self):
        assert guia.trocear("¿Cuándo OBLIGA?") == guia.trocear("cuando obliga")

    def test_un_codigo_se_lee_entero_aunque_lleve_guiones(self):
        assert guia.trocear("BR-CO-10") == ["brco10"]


# --- De dónde lo saca ------------------------------------------------------------


class TestDeDondeLoSaca:
    def test_cada_codigo_del_catalogo_tiene_su_ficha(self, datos):
        codigos = {c.codigo for c in codigos_del_paquete()}
        assert set(datos["codigos"]) == codigos
        for codigo, n in datos["codigos"].items():
            assert datos["fichas"][n]["id"] == codigo

    def test_ninguna_ficha_sale_vacia(self, datos):
        cojas = [f["id"] for f in datos["fichas"]
                 if not (f["titulo"] and f["texto"] and f["pie"])]
        assert not cojas, f"fichas a las que les falta algo que enseñar: {cojas}"

    def test_cada_ficha_lleva_a_su_pagina_o_cita_su_fuente(self, datos):
        """Los temas no tienen página en el sitio: su salida es el BOE. Todo lo
        demás se lee entero en la página de la que sale."""
        for ficha in datos["fichas"]:
            if ficha["tipo"] == "tema":
                assert ficha["fuentes"] and not ficha.get("url"), ficha["id"]
            else:
                assert ficha["url"] and ficha["enlace"], ficha["id"]

    def test_lo_que_solo_sirve_para_indexar_no_viaja(self, datos):
        de_mas = {k for f in datos["fichas"] for k in f if k.startswith("_")}
        assert not de_mas

    def test_cada_tema_cita_el_boe(self, datos):
        temas = [f for f in datos["fichas"] if f["tipo"] == "tema"]
        assert len(temas) >= 6
        for tema in temas:
            assert tema["fuentes"], tema["id"]
            for _, url in tema["fuentes"]:
                assert url.startswith("https://www.boe.es/"), (tema["id"], url)
            assert tema["aviso"] == guia._NO_CERTIFICA

    def test_un_tema_sin_fuente_oficial_no_se_monta(self, monkeypatch):
        """Provocado: el tema que cita un blog en vez del BOE tumba el montaje."""
        de_verdad = guia._temas()
        trucado = [dict(de_verdad[0], fuentes=[("Un blog", "https://example.org/")])]
        monkeypatch.setattr(guia, "_temas", lambda: trucado + de_verdad[1:])
        with pytest.raises(guia.GuiaMal, match="tema-"):
            _armar()

    def test_un_tema_sin_ninguna_fuente_tampoco(self, monkeypatch):
        de_verdad = guia._temas()
        monkeypatch.setattr(guia, "_temas",
                            lambda: [dict(de_verdad[0], fuentes=[])] + de_verdad[1:])
        with pytest.raises(guia.GuiaMal):
            _armar()


class TestLaLecturaDeLosTemas:
    """Los temas son lo único del guía que no se rehace solo al montar, así
    que su lectura del BOE caduca. Las fechas se pasan a mano: una prueba que
    dependiera del día en que corre fallaría sola un día cualquiera."""

    def test_el_ultimo_dia_del_plazo_todavia_vale(self):
        vence = guia.TEMAS_LEIDOS_EL + dt.timedelta(days=guia.TEMAS_VALEN_DIAS)
        guia.revisar_la_lectura(guia.TEMAS_LEIDOS_EL)
        guia.revisar_la_lectura(vence)

    def test_el_dia_despues_no_se_monta(self):
        """Provocado: un día después del plazo, el guía no se arma."""
        despues = guia.TEMAS_LEIDOS_EL + dt.timedelta(days=guia.TEMAS_VALEN_DIAS + 1)
        with pytest.raises(guia.GuiaMal, match="TEMAS_LEIDOS_EL"):
            guia.revisar_la_lectura(despues)

    def test_armar_pasa_por_el_freno(self):
        """Provocado por el camino de verdad: `armar` con un hoy pasado el
        plazo. Si alguien quitara la llamada, esta es la que se pondría roja."""
        despues = guia.TEMAS_LEIDOS_EL + dt.timedelta(days=guia.TEMAS_VALEN_DIAS + 1)
        with pytest.raises(guia.GuiaMal, match="se leyeron en el BOE"):
            guia.armar(
                WEB, codigos_del_paquete(), bitacora.leer_entradas(WEB / bitacora.CARPETA),
                pagina_incidencias.nombre_de, pagina_incidencias.NOMBRE,
                "alguien@example.org", hoy=despues)

    def test_una_lectura_en_el_futuro_tampoco(self):
        """Provocado: la errata de poner un año de más al cambiar la fecha
        dejaría el plazo sin vencer nunca."""
        antes = guia.TEMAS_LEIDOS_EL - dt.timedelta(days=1)
        with pytest.raises(guia.GuiaMal, match="no ha pasado"):
            guia.revisar_la_lectura(antes)

    def test_el_plazo_es_de_treinta_dias(self):
        """Decidido el 20-11-2026: cabe en el repaso de cada mes. Si se cambia,
        que sea a propósito y con su porqué al lado de la constante."""
        assert guia.TEMAS_VALEN_DIAS == 30

    def test_cada_respuesta_del_cuestionario_cita_el_boe(self, datos):
        todo = datos["cuestionario"]
        assert todo["aviso"] == guia._NO_CERTIFICA
        for nombre, respuesta in todo["respuestas"].items():
            assert respuesta["fuentes"], nombre
            for _, url in respuesta["fuentes"]:
                assert url.startswith("https://www.boe.es/"), (nombre, url)

    def test_el_cuestionario_no_tiene_callejones(self, datos):
        """Toda salida lleva a otro paso o a una respuesta, y todo se alcanza."""
        todo = datos["cuestionario"]
        vistos, por_ver = set(), [todo["inicio"]]
        while por_ver:
            nombre = por_ver.pop()
            if nombre in vistos:
                continue
            vistos.add(nombre)
            if nombre in todo["respuestas"]:
                continue
            assert nombre in todo["pasos"], f"«{nombre}» no es paso ni respuesta"
            por_ver += [destino for _, destino in todo["pasos"][nombre]["salidas"]]
        assert vistos == set(todo["pasos"]) | set(todo["respuestas"])

    def test_las_fechas_salen_de_la_entrada_en_vigor_de_la_orden(self):
        """La orden entró en vigor el 06-10-2026 y el RD cuenta desde ahí:
        doce meses, veinticuatro, treinta y seis, y la solución pública diez."""
        assert guia.ORDEN_EN_VIGOR == dt.date(2026, 10, 6)
        assert guia.FECHA_GRANDES == dt.date(2027, 10, 6)
        assert guia.FECHA_RESTO == dt.date(2028, 10, 6)
        assert guia.FECHA_ESTADOS == dt.date(2029, 10, 6)
        assert guia.FECHA_SOLUCION == dt.date(2027, 8, 6)

    def test_palabras_para_una_ficha_que_ya_no_existe_no_se_montan(self, monkeypatch):
        """Provocado: si se renombra un apartado, sus palabras no se quedan
        colgando de nadie sin que se sepa."""
        monkeypatch.setitem(guia.PALABRAS_DE_MAS, "sobre-que-ya-no-esta", "algo")
        with pytest.raises(guia.GuiaMal, match="sobre-que-ya-no-esta"):
            _armar()

    def test_lo_escrito_a_mano_no_lleva_rayas_ni_comillas_angulares(self):
        escrito = repr(guia._temas()) + repr(guia._cuestionario())
        for signo in ("—", "«", "»"):
            assert signo not in escrito


# --- A dónde manda ---------------------------------------------------------------


def _anclas_de(nombre: str) -> set[str]:
    return set(re.findall(r'\bid="([^"]+)"', (WEB / nombre).read_text(encoding="utf-8")))


class TestADondeManda:
    def test_cada_enlace_lleva_a_algo_que_existe(self, datos):
        """Un guía que manda a una página que no está es peor que uno que
        calla. Cada dirección se resuelve contra lo que el sitio monta."""
        fichas_de_codigo = {pagina_incidencias.nombre_de(c.codigo)
                            for c in codigos_del_paquete()}
        del_blog = {e.nombre for e in bitacora.leer_entradas(WEB / bitacora.CARPETA)}
        # Las secciones del catálogo no están en la plantilla: las escribe el
        # montaje, una por familia, con este mismo nombre.
        del_catalogo = {f"familia-{c.familia}" for c in codigos_del_paquete()}
        rotos = []
        for ficha in datos["fichas"]:
            url = ficha.get("url")
            if not url:
                continue
            assert url.startswith("./"), (ficha["id"], url)
            camino, _, ancla = url[2:].partition("#")
            nombre = (camino or "index") + ".html"
            if nombre in fichas_de_codigo or nombre in del_blog:
                continue
            if not (WEB / nombre).is_file():
                rotos.append(f"{ficha['id']}: {url} (no hay {nombre})")
            elif nombre == pagina_incidencias.NOMBRE and ancla in del_catalogo:
                continue
            elif ancla and ancla not in _anclas_de(nombre):
                rotos.append(f"{ficha['id']}: {url} (no hay id=\"{ancla}\")")
        assert not rotos, "; ".join(rotos)

    def test_nada_de_lo_que_sabe_nombra_otro_subdominio(self, datos, tmp_path):
        guia.montar(WEB, tmp_path, codigos_del_paquete(),
                    bitacora.leer_entradas(WEB / bitacora.CARPETA),
                    pagina_incidencias.nombre_de, pagina_incidencias.NOMBRE,
                    "alguien@example.org")
        guia.revisar_los_subdominios(tmp_path)

    def test_un_subdominio_que_no_existe_no_se_monta(self, tmp_path):
        """Provocado, en una página y en los datos."""
        (tmp_path / "una.html").write_text(
            '<a href="https://www.glosa-e.com/">bien</a>', encoding="utf-8")
        guia.revisar_los_subdominios(tmp_path)
        (tmp_path / "otra.html").write_text(
            '<a href="https://tienda.glosa-e.com/">mal</a>', encoding="utf-8")
        with pytest.raises(guia.GuiaMal, match="otra.html.*tienda"):
            guia.revisar_los_subdominios(tmp_path)
        (tmp_path / "otra.html").unlink()
        (tmp_path / guia.DATOS).write_text(
            '{"url":"https://Tienda.Glosa-e.com/"}', encoding="utf-8")
        with pytest.raises(guia.GuiaMal, match="tienda"):
            guia.revisar_los_subdominios(tmp_path)

    def test_el_correo_es_el_que_se_le_da_y_no_uno_escrito_aqui(self):
        assert _armar("otro@example.org")["correo"] == "otro@example.org"


# --- La huella y las comprobaciones ----------------------------------------------


class TestLoQueViaja:
    def test_la_huella_es_la_del_fichero_escrito(self, tmp_path):
        import hashlib
        huella, cuantas = guia.montar(
            WEB, tmp_path, codigos_del_paquete(),
            bitacora.leer_entradas(WEB / bitacora.CARPETA),
            pagina_incidencias.nombre_de, pagina_incidencias.NOMBRE, "a@example.org")
        escrito = (tmp_path / guia.DATOS).read_bytes()
        assert huella == hashlib.sha256(escrito).hexdigest()[:8]
        assert cuantas > 400
        assert b"\r" not in escrito

    def test_dos_montajes_de_lo_mismo_dan_el_mismo_fichero(self, tmp_path):
        """Si no, la dirección cambiaría en cada despliegue sin haber cambiado
        nada, y el navegador volvería a bajarse el índice entero."""
        huellas = []
        for nombre in ("uno", "dos"):
            (tmp_path / nombre).mkdir()
            huellas.append(guia.montar(
                WEB, tmp_path / nombre, codigos_del_paquete(),
                bitacora.leer_entradas(WEB / bitacora.CARPETA),
                pagina_incidencias.nombre_de, pagina_incidencias.NOMBRE,
                "a@example.org")[0])
        assert huellas[0] == huellas[1]

    def test_las_comprobaciones_dicen_lo_que_contesta_esta_implementacion(self, datos):
        casos = datos["comprobaciones"]
        assert len(casos) >= 12
        for consulta, esperado in casos:
            assert _ids(datos, consulta) == esperado
        # Tienen que probar las tres salidas: un código, una búsqueda y nada.
        assert any(e == [] for _, e in casos)
        assert any(len(e) == 1 and e[0] in datos["codigos"] for _, e in casos)
        assert any(e and e[0] not in datos["codigos"] for _, e in casos)


# --- El asistente ---------------------------------------------------------------


class TestElAsistente:
    """La copia en JavaScript no se puede ejecutar aquí. Se vigila por su
    forma: que siga escrita con las reglas de la implementación de Python, y
    que cumpla lo que el sitio promete de sí mismo."""

    @pytest.fixture
    def texto(self) -> str:
        return ASISTENTE.read_text(encoding="utf-8")

    def test_dice_donde_estan_los_datos_una_sola_vez(self, texto):
        assert texto.count(guia.LLAMADA_A_LOS_DATOS) == 1

    def test_trocea_con_la_misma_expresion(self, texto):
        assert "/" + guia._RE_PIEZA.pattern + "/g" in texto

    def test_pide_los_mismos_aciertos(self, texto):
        assert "Math.floor((2 * piezas.length + 2) / 3)" in texto
        assert "datos.umbral" in texto and "datos.cerca" in texto and "datos.otras" in texto

    def test_no_lleva_escritas_las_cifras_que_viajan_en_los_datos(self, texto):
        """El umbral y las palabras vacías se leen de `guia.json`. Escritos
        también aquí serían una segunda copia que se queda atrás."""
        assert f">= {guia.UMBRAL}" not in texto
        assert "new Set([" not in texto

    def test_lo_que_escribe_el_visitante_no_entra_como_html(self, texto):
        for peligro in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"):
            assert peligro not in texto

    def test_no_guarda_nada_en_el_navegador(self, texto):
        """El aviso legal publica medido el almacenamiento vacío y ninguna
        cookie. Por eso el aviso del minuto vuelve en cada página."""
        for guardar in ("localStorage", "sessionStorage", "document.cookie", "indexedDB"):
            assert guardar not in texto

    def test_no_pide_los_datos_al_abrir_ni_con_el_raton(self, texto):
        for gesto in ("mousemove", "mouseover", "pointermove", "pointerover",
                      "DOMContentLoaded", '"load"', '"scroll"', '"resize"'):
            assert gesto not in texto
        # Los datos se piden en un solo sitio, y a ese sitio se llega al abrir
        # el panel o al preguntar: nunca desde el aviso del minuto.
        assert texto.count("fetch(") == 1
        aviso = texto[texto.index("function preguntarSiHayDudas"):]
        aviso = aviso[:aviso.index("setTimeout(")]
        assert "cargar(" not in aviso and "fetch(" not in aviso
        # La única carga sin gesto es la de la comprobación, que se pide a mano.
        assert texto.count("conDatos(comprobar)") == 1

    def test_pregunta_al_minuto_lo_que_pidio_el_titular(self, texto):
        assert "const AL_MINUTO = 60 * 1000;" in texto
        assert "setTimeout(preguntarSiHayDudas, AL_MINUTO);" in texto
        assert '"¿Tienes alguna pregunta?"' in texto

    def test_no_pide_nada_fuera_del_sitio(self, texto):
        sin_el_espacio_de_nombres = texto.replace('"http://www.w3.org/2000/svg"', "")
        assert "http://" not in sin_el_espacio_de_nombres
        assert "https://" not in sin_el_espacio_de_nombres
        assert "fetch(DATOS_EN)" in texto

    def test_dice_lo_que_es_y_lo_que_no(self, texto):
        for promesa in ("No es una inteligencia artificial", "No sale de tu navegador",
                        "Cuando no sabe, lo dice", "No certifica", "No estudia tu caso"):
            assert promesa in texto

    def test_ni_rayas_ni_comillas_angulares(self, texto):
        for signo in ("\u2014", "\u00ab", "\u00bb"):
            assert signo not in texto

    def test_cada_enlace_de_ayuda_lleva_a_una_pagina_que_existe(self, texto):
        for camino in re.findall(r'\["[^"]+", "\./([^"#]*)(?:#[^"]*)?"\]', texto):
            assert (WEB / ((camino or "index") + ".html")).is_file(), camino
