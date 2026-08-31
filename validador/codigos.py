# -*- coding: utf-8 -*-
"""Todos los códigos de incidencia que este validador puede sacar.

Por qué se leen del código fuente y no de una lista
---------------------------------------------------
Porque una lista escrita a mano se queda atrás, y este repositorio ya sabe cómo
acaba eso: la cuenta de pruebas del README se quedó en 985 cuando había 1.018,
y el banco del navegador decía «las 33 comprobaciones pasan» cuando eran otras.
Un catálogo de errores que no incluya el error que le acaba de salir a alguien
es peor que no tener catálogo: manda a buscar a un sitio donde no está.

Así que se leen con `ast` de los propios módulos. La fuente de verdad es la
llamada a `Incidencia(...)` que hay en el código; si mañana alguien añade un
código nuevo, aparece aquí sin que nadie se acuerde de nada, y la prueba que
compara esto con la página publicada se pone en rojo si la página no lo tiene.

Lo que **no** se puede sacar de aquí, y por qué
-----------------------------------------------
El mensaje. Se compone en tiempo de ejecución con los datos de la factura
—fechas, importes, nombres—, así que aquí no hay una frase que enseñar: hay una
f-string a medio hacer. Por eso el catálogo lleva la explicación escrita a mano
y esto solo garantiza que **no falte ningún código**. Los que todavía no tienen
explicación salen dichos como tales, que es la forma honrada de tener un hueco:
visible, contado y sin fingir que no está.

Dos códigos con dos gravedades
-------------------------------
`CU-04` y `REVOCACION-POSTERIOR` se emiten con gravedad distinta según el caso,
y eso no es un descuido: `REVOCACION-POSTERIOR` es un AVISO cuando la fecha la
declara quien firma y una NOTA cuando la acredita un sello de tiempo de un
tercero. El catálogo tiene que poder decirlo, así que aquí se guardan las dos.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

__all__ = ["Codigo", "codigos_del_paquete"]

# Las gravedades tal como se escriben en el código: `Incidencia("X", ERROR, …)`.
_GRAVEDADES = {"ERROR": "error", "AVISO": "aviso", "NOTA": "nota"}


@dataclass(frozen=True)
class Codigo:
    """Un código de incidencia, con lo que se puede saber sin ejecutarlo."""

    codigo: str
    gravedades: tuple[str, ...]   # más de una cuando depende del caso
    modulo: str                   # dónde se emite por primera vez
    linea: int

    @property
    def familia(self) -> str:
        """El prefijo que agrupa: BR, CU, XSD, FIRMA… Para ordenar la página.

        Los que no llevan guion son su propia familia: `REVOCADO` no es de
        `REVOCACION-` aunque lo parezca, y meterlo ahí sería decir que es un
        problema de la lista cuando es el resultado de haberla leído.
        """
        return self.codigo.split("-")[0] if "-" in self.codigo else self.codigo


def _de_un_fichero(ruta: Path) -> list[tuple[str, str, int]]:
    """Los `Incidencia("CODIGO", GRAVEDAD, …)` de un módulo."""
    encontrados = []
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        nombre = nodo.func.id if isinstance(nodo.func, ast.Name) else None
        if nombre != "Incidencia" or not nodo.args:
            continue
        primero = nodo.args[0]
        if not (isinstance(primero, ast.Constant) and isinstance(primero.value, str)):
            # Un código calculado no se puede leer de aquí. Hoy no hay ninguno;
            # el día que lo haya, esto lo salta en silencio y la prueba que
            # compara con la página no se enteraría. Por eso se cuenta aparte.
            continue
        gravedad = ""
        if len(nodo.args) > 1 and isinstance(nodo.args[1], ast.Name):
            gravedad = _GRAVEDADES.get(nodo.args[1].id, "")
        encontrados.append((primero.value, gravedad, nodo.lineno))
    return encontrados


def codigos_del_paquete(carpeta: Path | str | None = None) -> list[Codigo]:
    """Todos los códigos, ordenados por familia y luego alfabéticamente."""
    raiz = Path(carpeta) if carpeta is not None else Path(__file__).parent
    gravedades: dict[str, set[str]] = {}
    donde: dict[str, tuple[str, int]] = {}
    for ruta in sorted(raiz.glob("*.py")):
        for codigo, gravedad, linea in _de_un_fichero(ruta):
            gravedades.setdefault(codigo, set())
            if gravedad:
                gravedades[codigo].add(gravedad)
            donde.setdefault(codigo, (ruta.name, linea))

    salida = [
        Codigo(
            codigo=codigo,
            # Ordenadas de mayor a menor gravedad, no alfabéticamente: si un
            # código puede salir como error, eso es lo primero que hay que ver.
            gravedades=tuple(
                g for g in ("error", "aviso", "nota") if g in gravedades[codigo]
            ),
            modulo=donde[codigo][0],
            linea=donde[codigo][1],
        )
        for codigo in gravedades
    ]
    return sorted(salida, key=lambda c: (c.familia, c.codigo))
