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

Un código no siempre está escrito donde se emite
------------------------------------------------
Y esto es lo que durante mucho tiempo se leyó mal. Media docena de reglas de
este validador no escriben su código en la llamada: lo sacan de una tabla y lo
recorren con un `for`, que es como se evitan catorce bloques iguales seguidos.

    for codigo, atributo, campo, explicacion in _DE_LINEA:
        ...
        Incidencia(codigo, ERROR, explicacion, ...)

Ahí el código sigue estando escrito —en la tabla, una fila más arriba—, pero un
lector que solo mire el primer argumento de la llamada ve un nombre de variable
y no una cadena. Este lo hacía, y se los saltaba **en silencio**: 17 códigos
—BR-02 a BR-15, BR-22, BR-23 y BR-26— existían, se emitían y no salían en el
catálogo, mientras la página publicada decía que «aquí no puede faltar uno que
exista». Por eso ahora se desata el bucle: se busca de qué tabla sale el
nombre y se leen las filas.

Lo que queda sin leer se cuenta, no se calla
--------------------------------------------
Quedan códigos que ni así se pueden leer: los `BR-{X}-08` de `iva.py`, que se
componen en tiempo de ejecución con la categoría de la operación —f-strings
cuyo hueco solo se conoce al mirar la factura—. Esos no se pueden resolver
mirando el fuente, y fingir que sí es exactamente el fallo que se acaba de
arreglar.

Así que se devuelven aparte, por `sin_leer_del_paquete()`, con su fichero y su
línea. La página los cuenta a la vista y `tests/test_codigos.py` los compara
con una lista declarada: el día que alguien escriba una llamada nueva que este
lector no sepa leer, la prueba se pone en rojo y dice dónde. Es la diferencia
entre un hueco y una mentira —un hueco contado se puede cerrar; uno silencioso
no se sabe ni que está—.

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
import importlib
from dataclasses import dataclass
from pathlib import Path

__all__ = ["Codigo", "SinLeer", "codigos_del_paquete", "sin_leer_del_paquete"]

# Las gravedades tal como se escriben en el código: `Incidencia("X", ERROR, …)`.
_GRAVEDADES = {"ERROR": "error", "AVISO": "aviso", "NOTA": "nota"}

# Cómo se dibuja en el patrón la parte de una f-string que solo se sabe al
# ejecutarla: `f"BR-{regla.codigo}-8"` se enseña como «BR-{}-8». Se enseña el
# patrón y no el trozo de código a propósito: quien lea la prueba en rojo
# necesita reconocer el código que falta, no el nombre de la variable.
_HUECO = "{}"


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


@dataclass(frozen=True)
class SinLeer:
    """Una llamada a `Incidencia(...)` cuyo código este lector no resuelve.

    No es un error del validador: es un límite de leer el fuente sin
    ejecutarlo. Se guarda para poder contarlo, que es lo único que separa un
    hueco conocido de uno que nadie sabe que está.
    """

    modulo: str
    linea: int
    patron: str   # «BR-{}-8», «codigo»… lo que se ve desde fuera


def _tablas_del_modulo(arbol: ast.Module) -> dict[str, ast.expr]:
    """Las asignaciones de primer nivel, para poder seguir un `for … in TABLA`.

    Solo las de primer nivel: una tabla de reglas es una constante del módulo,
    y buscar también dentro de las funciones haría que un nombre reutilizado
    en un sitio cualquiera se tomara por la tabla equivocada.
    """
    tablas: dict[str, ast.expr] = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.AnnAssign) and nodo.value is not None:
            if isinstance(nodo.target, ast.Name):
                tablas[nodo.target.id] = nodo.value
        elif isinstance(nodo, ast.Assign) and len(nodo.targets) == 1:
            if isinstance(nodo.targets[0], ast.Name):
                tablas[nodo.targets[0].id] = nodo.value
    return tablas


def _filas(iterable: ast.expr, tablas: dict[str, ast.expr]) -> list[ast.Tuple]:
    """Las filas de lo que recorre un `for`, si es una tabla de tuplas.

    Vale tanto la tabla con nombre —`_OBLIGATORIOS`— como la que se escribe
    dentro del propio `for`, que es como están BR-CO-11 y BR-CO-12. Las dos son
    la misma figura: filas literales de las que una columna es el código.
    """
    if isinstance(iterable, ast.Name):
        del_modulo = tablas.get(iterable.id)
        if del_modulo is None:
            return []
        iterable = del_modulo
    if not isinstance(iterable, (ast.Tuple, ast.List)):
        return []
    filas = [e for e in iterable.elts if isinstance(e, ast.Tuple)]
    # Todas o ninguna: una tabla en la que solo algunas filas son tuplas no es
    # una tabla, y adivinar ahí sería inventarse códigos.
    return filas if filas and len(filas) == len(iterable.elts) else []


def _desatados(bucle: ast.For, tablas: dict[str, ast.expr]) -> dict[str, tuple[str, ...]]:
    """Qué puede valer cada nombre que este `for` saca de su tabla."""
    if not isinstance(bucle.target, ast.Tuple):
        return {}
    filas = _filas(bucle.iter, tablas)
    if not filas:
        return {}

    salida: dict[str, tuple[str, ...]] = {}
    for indice, destino in enumerate(bucle.target.elts):
        if not isinstance(destino, ast.Name):
            continue
        valores = [
            fila.elts[indice].value
            for fila in filas
            if indice < len(fila.elts)
            and isinstance(fila.elts[indice], ast.Constant)
            and isinstance(fila.elts[indice].value, str)
        ]
        # Solo si **todas** las filas ponen una cadena en esa columna. Si una
        # sola trae otra cosa, la columna no es de códigos y quedarse con las
        # demás sería publicar una lista incompleta creyéndola entera.
        if len(valores) == len(filas):
            salida[destino.id] = tuple(dict.fromkeys(valores))
    return salida


def _padres(arbol: ast.Module) -> dict[int, ast.AST]:
    """De cada nodo a quien lo contiene, para poder subir desde una llamada."""
    padres: dict[int, ast.AST] = {}
    for nodo in ast.walk(arbol):
        for hijo in ast.iter_child_nodes(nodo):
            padres[id(hijo)] = nodo
    return padres


def _atados(nodo: ast.AST, padres, tablas) -> dict[str, tuple[str, ...]]:
    """Los nombres que los `for` de alrededor le han atado a esta llamada.

    De dentro hacia fuera, y el primero que ate un nombre gana: si un bucle
    interior reutiliza el nombre de uno exterior, el que manda en la llamada es
    el de dentro, igual que en Python.
    """
    atados: dict[str, tuple[str, ...]] = {}
    arriba = padres.get(id(nodo))
    while arriba is not None:
        if isinstance(arriba, ast.For):
            for nombre, valores in _desatados(arriba, tablas).items():
                atados.setdefault(nombre, valores)
        arriba = padres.get(id(arriba))
    return atados


def _asignados(nodo: ast.AST, padres) -> dict[str, list[ast.expr]]:
    """Lo que se le ha asignado a cada nombre en la función que rodea a esto.

    Es la misma figura que la tabla, un piso más abajo: el código está escrito
    en el fuente, solo que en la línea de antes en vez de en el argumento.

        codigo = f"BR-{regla.codigo}-08" if regla else "IVA-BASE"
        ...
        Incidencia(codigo, ERROR, …)

    Sin esto, `IVA-BASE` no salía en el catálogo aunque esté ahí escrito. Se
    guardan **todas** las asignaciones al mismo nombre y no la última: si una
    función le da dos valores según el caso, los dos se pueden emitir.
    """
    arriba = padres.get(id(nodo))
    while arriba is not None and not isinstance(
        arriba, (ast.FunctionDef, ast.AsyncFunctionDef)
    ):
        arriba = padres.get(id(arriba))
    if arriba is None:
        return {}

    asignados: dict[str, list[ast.expr]] = {}
    for hijo in ast.walk(arriba):
        if isinstance(hijo, ast.Assign) and len(hijo.targets) == 1:
            if isinstance(hijo.targets[0], ast.Name):
                asignados.setdefault(hijo.targets[0].id, []).append(hijo.value)
    return asignados


def _patron(nodo: ast.expr) -> str:
    """Cómo enseñar un código que no se ha podido resolver."""
    if isinstance(nodo, ast.JoinedStr):
        return "".join(
            trozo.value
            if isinstance(trozo, ast.Constant) and isinstance(trozo.value, str)
            else _HUECO
            for trozo in nodo.values
        )
    return ast.unparse(nodo)


def _resolver(
    nodo: ast.expr,
    atados: dict[str, tuple[str, ...]],
    asignados: dict[str, list[ast.expr]],
    vistos: frozenset[str] = frozenset(),
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Los códigos que puede valer este argumento, y lo que no se ha sabido leer."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return (nodo.value,), ()
    if isinstance(nodo, ast.Name):
        # El bucle manda sobre la asignación, igual que en Python: si las dos
        # atan el mismo nombre, el valor que llega a la llamada es el del `for`.
        if nodo.id in atados:
            return atados[nodo.id], ()
        # `vistos` corta las vueltas: un `codigo = codigo or "X"` se resolvería
        # a sí mismo para siempre, y un lector de catálogos no puede colgarse
        # por una línea que en Python es perfectamente legal.
        if nodo.id in asignados and nodo.id not in vistos:
            codigos: tuple[str, ...] = ()
            patrones: tuple[str, ...] = ()
            for valor in asignados[nodo.id]:
                mios, suyos = _resolver(
                    valor, atados, asignados, vistos | {nodo.id}
                )
                codigos += mios
                patrones += suyos
            return codigos, patrones
    if isinstance(nodo, ast.IfExp):
        # `f"BR-{regla.codigo}-01" if regla else "IVA-CATEGORIA-SIN-DESGLOSE"`:
        # una rama se lee y la otra no, y las dos cuentan. Quedarse con la
        # llamada entera como ilegible perdería el código que sí está escrito.
        codigos_si, sin_leer_si = _resolver(nodo.body, atados, asignados, vistos)
        codigos_no, sin_leer_no = _resolver(nodo.orelse, atados, asignados, vistos)
        return codigos_si + codigos_no, sin_leer_si + sin_leer_no
    return (), (_patron(nodo),)


def _declarados_por(ruta: Path) -> dict[str, tuple[str, ...]]:
    """Lo que un módulo dice que compone, cuando lo dice.

    Hay códigos que no se pueden leer del fuente porque no están escritos:
    `f"BR-{regla.codigo}-08"` no dice cuál es hasta que hay una factura
    delante. Contarlos como huecos era honrado y dejaba a decenas de
    códigos reales sin ficha, que es un agujero distinto: le sale a alguien en
    su informe y no tiene dónde mirar.

    Así que el módulo que los compone puede declararlos en un
    `CODIGOS_COMPUESTOS`, pegado a la tabla de la que salen, y aquí se
    recogen. Sigue sin adivinarse nada: lo que no esté declarado sigue
    contándose como hueco.

    Se importa por el nombre del paquete y solo cuando la carpeta es la suya.
    Cargar un fichero suelto por su ruta volvería a ejecutar el módulo con
    otra identidad, y entonces habría dos `validador.iva` distintos en
    memoria; es el precio de leer una constante en vez de un literal, y se
    paga no haciéndolo cuando no toca.
    """
    if ruta.parent != Path(__file__).parent:
        return {}
    try:
        modulo = importlib.import_module(f"{__package__}.{ruta.stem}")
    except Exception:
        # Un módulo que no importa no invalida el catálogo entero: sus códigos
        # literales ya se han leído del fuente, que no necesita ejecutarlo.
        return {}
    declarados = getattr(modulo, "CODIGOS_COMPUESTOS", None)
    return dict(declarados) if isinstance(declarados, dict) else {}


def _de_un_fichero(
    ruta: Path,
) -> tuple[list[tuple[str, str, int]], list[tuple[int, str]]]:
    """Los códigos de un módulo, y las llamadas cuyo código no se ha resuelto."""
    arbol = ast.parse(ruta.read_text(encoding="utf-8"), filename=str(ruta))
    tablas = _tablas_del_modulo(arbol)
    padres = _padres(arbol)
    compuestos = _declarados_por(ruta)

    encontrados: list[tuple[str, str, int]] = []
    sin_leer: list[tuple[int, str]] = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call) or not nodo.args:
            continue
        if not (isinstance(nodo.func, ast.Name) and nodo.func.id == "Incidencia"):
            continue
        gravedad = ""
        if len(nodo.args) > 1 and isinstance(nodo.args[1], ast.Name):
            gravedad = _GRAVEDADES.get(nodo.args[1].id, "")
        codigos, patrones = _resolver(
            nodo.args[0],
            _atados(nodo, padres, tablas),
            _asignados(nodo, padres),
        )
        encontrados.extend((codigo, gravedad, nodo.lineno) for codigo in codigos)
        for patron in patrones:
            suyos = compuestos.get(patron)
            if suyos:
                encontrados.extend((codigo, gravedad, nodo.lineno) for codigo in suyos)
            else:
                sin_leer.append((nodo.lineno, patron))

    # Por línea y no en el orden en que `ast.walk` los encuentre: «se emite en
    # en16931.py:238» tiene que salir igual en dos montajes seguidos, o la
    # página cambia sola y no se sabe por qué.
    return sorted(encontrados, key=lambda x: x[2]), sorted(sin_leer)


def _leer(carpeta: Path | str | None) -> tuple[list[Codigo], list[SinLeer]]:
    """Una sola pasada por los módulos: los códigos y los huecos salen juntos."""
    raiz = Path(carpeta) if carpeta is not None else Path(__file__).parent
    gravedades: dict[str, set[str]] = {}
    donde: dict[str, tuple[str, int]] = {}
    huecos: list[SinLeer] = []

    for ruta in sorted(raiz.glob("*.py")):
        encontrados, sin_leer = _de_un_fichero(ruta)
        for codigo, gravedad, linea in encontrados:
            gravedades.setdefault(codigo, set())
            if gravedad:
                gravedades[codigo].add(gravedad)
            donde.setdefault(codigo, (ruta.name, linea))
        huecos.extend(SinLeer(ruta.name, linea, patron) for linea, patron in sin_leer)

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
    return sorted(salida, key=lambda c: (c.familia, c.codigo)), huecos


def codigos_del_paquete(carpeta: Path | str | None = None) -> list[Codigo]:
    """Todos los códigos, ordenados por familia y luego alfabéticamente."""
    return _leer(carpeta)[0]


def sin_leer_del_paquete(carpeta: Path | str | None = None) -> list[SinLeer]:
    """Las llamadas cuyo código no se resuelve mirando el fuente.

    Lo que hay aquí **no** está en el catálogo. Se devuelve para poder decirlo
    a la vista en la página y para que una prueba lo vigile, que es lo único
    que impide que la lista de códigos vuelva a quedarse corta en silencio.
    """
    return _leer(carpeta)[1]
