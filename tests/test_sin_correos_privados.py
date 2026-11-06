"""Nada de lo versionado cita como aval lo que la AEAT contestó por correo.

Por qué existe
--------------
El 06-11-2026 el titular encontró, validando una factura en la web, una nota
que decía «que es lo que contestó la AEAT el 17-09-2026». Es una respuesta
privada a una consulta, y quien lee el informe no la puede comprobar: citada en
público es una afirmación sin prueba, aunque sea cierta. Salía en unos treinta
textos del informe y de las fichas, en tres artículos del blog, en el README,
en HALLAZGOS y en los comentarios del código, y el repositorio es público.

Lo que se decidió: lo que se publica dice qué hace Glosa-e y en qué se apoya,
citando solo lo que cualquiera puede leer (el BOE, los documentos y ejemplos
del portal de la AEAT, los esquemas, la norma europea). Si una decisión se
apoya solo en una respuesta privada, se da como criterio de Glosa-e. El
registro de qué se preguntó, qué se contestó y qué se decidió con ello vive en
`informes/consultas-a-la-aeat/`, que no se versiona.

Esto recorre todo lo que git versiona, no una lista de ficheros: el texto entró
en sitios que nadie habría puesto en una lista (un docstring de una prueba, una
entrada de novedades). Las expresiones se escriben troceadas para que este
fichero no se encuentre a sí mismo.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

_AEAT = r"(?:la\s+AEAT|la\s+Agencia|AEAT)"
_DIJO = r"(?:contest|respond|confirm[óo]|lo\s+confirm|nos\s+dij|dijo\s+por|por\s+escrito|por\s+correo)"
CITAS = [
    # El buzón de la AEAT, no cualquiera: el aviso legal habla del del titular.
    re.compile(r"(?:\bal|\bdel)\s+buz" + r"[óo]n|buz[óo]n\s+(?:t[ée]cnico|de\s+la\s+AEAT)"
               r"|\bel\s+buz[óo]n\s+(?:contest|respond|dijo)"
               r"|(?:contest|respond|pregunt)\w*\s+(?:a\s+)?el\s+buz[óo]n", re.I),
    # El punto corta la frase, salvo el de una versión: «la AEAT admite la 2.5,
    # pero contestó…» es la misma frase.
    re.compile(_AEAT + r"\b(?:[^.;:]|\.(?=\d)){0,50}?\b" + _DIJO, re.I),
    re.compile(r"\b(?:contest|respondi|confirm)\w*\s+(?:ese\s+d[ií]a\s+|tambi[ée]n\s+|por\s+escrito\s+)?" + _AEAT, re.I),
    re.compile("consulta" + r"\s+de\s+Glosa", re.I),
    re.compile("facturaelectronica" + "@", re.I),
    re.compile(r"correos?\s+(?:de|con|a)\s+" + _AEAT, re.I),
    re.compile("pregunt" + r"\w*\s+(?:a\s+)?" + _AEAT, re.I),
    # Lo que llegó adjunto a un correo y no se publicó: el ejemplo del
    # 02-10-2026, que fue toda la respuesta a una consulta, y el anexo 2.0 que
    # vino con la del 13-10-2026. El que vale es el del portal, del 21-10-2026.
    re.compile(r"ejemplo\s+(?:de\s+la\s+AEAT\s+)?del\s+(?:0?2-10-2026|2\s+de\s+octubre)", re.I),
    re.compile(r"\bmand[óo]\s+" + r"por\s+correo|\banexo\s+2\.0\b", re.I),
]

_TEXTO = {".py", ".md", ".html", ".txt", ".js", ".json", ".toml", ".yml", ".css", ".xml"}


def _versionados() -> list[Path]:
    salida = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True,
                            text=True, encoding="utf-8", check=True).stdout
    return [RAIZ / r for r in salida.splitlines()
            if Path(r).suffix in _TEXTO and Path(r).name != Path(__file__).name]


def _plano(texto: str) -> str:
    """El texto con los renglones juntos: una cita partida en dos líneas, o en
    dos literales de Python, también es una cita."""
    texto = re.sub(r"[\"']\s*\n\s*f?[\"']", "", texto)
    texto = re.sub(r"\s*\n\s*(?:#+|\*|//)?\s*", " ", texto)
    return texto


def test_nada_versionado_cita_un_correo_de_la_aeat():
    halladas = []
    for ruta in _versionados():
        if not ruta.exists():
            continue
        plano = _plano(ruta.read_text(encoding="utf-8", errors="replace"))
        for patron in CITAS:
            for m in patron.finditer(plano):
                trozo = plano[max(0, m.start() - 40):m.end() + 40]
                halladas.append(f"{ruta.relative_to(RAIZ)}: ...{trozo}...")
    assert not halladas, (
        f"{len(halladas)} citas de respuestas privadas de la AEAT en lo "
        "versionado. Lo publicado dice qué hace Glosa-e y en qué se apoya, con "
        "fuentes que cualquiera puede leer; el registro de lo preguntado va en "
        "informes/consultas-a-la-aeat/, que no se versiona.\n" + "\n".join(halladas))
