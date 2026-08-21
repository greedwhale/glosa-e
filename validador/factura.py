"""El orquestador: todas las reglas sobre el mismo documento, de una pasada.

Hasta aquí había dos módulos de reglas que no se hablaban. `en16931` mira lo
que exige la norma europea; `codigo_unico` mira lo que exige el RD 238/2026 y
que ningún validador europeo comprueba. Quien recibe una factura necesita las
dos cosas a la vez y no le importa de qué reglamento sale cada queja.

Este módulo hace tres cosas que no salen gratis de sumar las dos listas:

1. **Un solo árbol.** El documento se parsea una vez y se les pasa ya parseado
   a los dos conjuntos de reglas, en lugar de que cada uno se lo monte por su
   cuenta.
2. **No decir dos veces lo mismo.** BR-02 y CU-02 son la misma queja escrita
   por dos reglamentos distintos. Si ya lo ha dicho la norma europea, la
   española se calla.
3. **Mirar el lote entero.** Un duplicado entre dos ficheros no se ve validando
   cada fichero por separado, por definición. `validar_lote` valida uno a uno y
   después pasa una segunda vez sobre el montón completo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from lxml import etree

from validador import codigo_unico, en16931
from validador.formato import CII, FACTURAE, UBL, Deteccion, detectar, parser
from validador.incidencias import ERROR, Incidencia, Informe

# Familias que son XML y por tanto se pueden parsear. EDIFACT no lo es.
_FAMILIAS_XML = (UBL, FACTURAE, CII)

# Cuando la queja de la izquierda ya ha saltado, la de la derecha sobra: dicen
# lo mismo con las palabras de dos reglamentos distintos.
_SOBRA_SI: dict[str, tuple[str, ...]] = {
    "CU-00": ("BR-02", "BR-03"),
    "CU-02": ("BR-02",),
}

# De qué reglamento sale cada queja, por el prefijo de su código.
EUROPEA = "EN 16931"
ESPANOLA = "RD 238/2026"
OTRA = "Formato"


def origen(incidencia: Incidencia) -> str:
    """A qué norma responde una incidencia."""
    if incidencia.codigo.startswith("BR-"):
        return EUROPEA
    if incidencia.codigo.startswith("CU-"):
        return ESPANOLA
    return OTRA


def _arbol(datos: bytes, deteccion: Deteccion):
    """El documento parseado, o None si no es XML."""
    if not deteccion or deteccion.familia not in _FAMILIAS_XML:
        return None
    try:
        return etree.fromstring(datos, parser=parser())
    except etree.XMLSyntaxError:
        # `detectar` ya lo parseó sin problemas, así que llegar aquí sería
        # raro. Aun así, mejor no reventar el lote entero por un fichero.
        return None


def _podar(incidencias: list[Incidencia]) -> list[Incidencia]:
    """Quita las quejas que ya ha dicho otra regla con otras palabras."""
    presentes = {i.codigo for i in incidencias}
    return [
        i
        for i in incidencias
        if not any(otro in presentes for otro in _SOBRA_SI.get(i.codigo, ()))
    ]


def _senia(incidencia: Incidencia) -> tuple:
    """Identifica una incidencia sin mirar su redacción.

    Hace falta porque la misma queja se redacta distinto según de dónde salga:
    en un lote, el mensaje añade de qué fichero venía la factura anterior. Si
    se compararan los textos, nunca coincidirían y todo se contaría dos veces.
    """
    return (
        incidencia.codigo,
        incidencia.campo,
        incidencia.esperado,
        incidencia.encontrado,
    )


def _reglas(raiz, deteccion: Deteccion, hoy: date | None) -> list[Incidencia]:
    """Todas las reglas sobre un documento ya parseado y ya identificado."""
    incidencias = list(en16931.reglas(raiz, deteccion))
    incidencias.extend(codigo_unico.reglas(raiz, deteccion, hoy=hoy))
    return _podar(incidencias)


def validar(datos: bytes | str, hoy: date | None = None) -> Informe:
    """Valida un documento contra las reglas europeas y las españolas."""
    deteccion = detectar(datos)
    informe = Informe(deteccion=deteccion)
    if not deteccion:
        return informe
    if isinstance(datos, str):
        datos = datos.encode("utf-8")
    informe.incidencias.extend(_reglas(_arbol(datos, deteccion), deteccion, hoy))
    return informe


def validar_archivo(ruta: str | Path, hoy: date | None = None) -> Informe:
    """Igual que `validar`, leyendo de un fichero."""
    camino = Path(ruta)
    try:
        return validar(camino.read_bytes(), hoy=hoy)
    except OSError as error:
        return Informe(deteccion=_no_se_puede_leer(camino, error))


def _no_se_puede_leer(camino: Path, error: OSError) -> Deteccion:
    if isinstance(error, FileNotFoundError):
        return Deteccion(motivo=f"No existe el fichero {camino}.")
    return Deteccion(motivo=f"No se ha podido leer {camino}: {error}")


# --- Un lote de ficheros ---------------------------------------------------


@dataclass
class InformeLote:
    """Lo que sale de validar varios ficheros juntos.

    `cruzadas` son las incidencias que solo aparecen al mirar todos los
    ficheros a la vez: la misma factura en dos ficheros distintos, o una serie
    con huecos repartida entre varios. No están en ningún informe individual
    porque, mirando un fichero solo, no hay nada que ver.
    """

    informes: list[tuple[Path, Informe]] = field(default_factory=list)
    cruzadas: list[Incidencia] = field(default_factory=list)

    @property
    def errores(self) -> list[Incidencia]:
        de_cada_uno = [i for _, informe in self.informes for i in informe.errores]
        return de_cada_uno + [i for i in self.cruzadas if i.gravedad == ERROR]

    @property
    def conforme(self) -> bool:
        return not self.errores

    def __bool__(self) -> bool:
        return self.conforme

    def resumen(self) -> str:
        correctos = sum(1 for _, informe in self.informes if informe.conforme)
        partes = [
            f"{len(self.informes)} fichero(s)",
            f"{correctos} correcto(s)",
            f"{len(self.informes) - correctos} con errores",
        ]
        if self.cruzadas:
            partes.append(f"{len(self.cruzadas)} incidencia(s) entre ficheros")
        return " · ".join(partes) + "."

    def detalle(self) -> str:
        lineas: list[str] = []
        for camino, informe in self.informes:
            lineas.append(str(camino))
            lineas.append(f"  {informe.resumen()}")
            for incidencia in informe.errores + informe.avisos:
                lineas.append("")
                lineas.append(_sangrar(str(incidencia), "  "))
            lineas.append("")
        if self.cruzadas:
            lineas.append("Entre ficheros:")
            for incidencia in self.cruzadas:
                lineas.append("")
                lineas.append(_sangrar(str(incidencia), "  "))
            lineas.append("")
        lineas.append(self.resumen())
        return "\n".join(lineas)


def _sangrar(texto: str, margen: str) -> str:
    return "\n".join(margen + linea for linea in texto.splitlines())


def validar_lote(rutas: list[str | Path], hoy: date | None = None) -> InformeLote:
    """Valida varios ficheros y además los compara entre sí.

    Cada fichero se valida por su cuenta y después se juntan todas las facturas
    de todos los ficheros para las reglas de conjunto. Esa segunda pasada es la
    razón de ser de esta función: un duplicado entre dos ficheros no puede
    detectarlo ninguno de los dos por separado.
    """
    lote = InformeLote()
    todos: list[codigo_unico.CodigoUnico] = []
    procedencias: list[str] = []

    for ruta in rutas:
        camino = Path(ruta)
        try:
            datos = camino.read_bytes()
        except OSError as error:
            lote.informes.append(
                (camino, Informe(deteccion=_no_se_puede_leer(camino, error)))
            )
            continue

        deteccion = detectar(datos)
        raiz = _arbol(datos, deteccion)
        informe = Informe(deteccion=deteccion)
        if deteccion:
            informe.incidencias.extend(_reglas(raiz, deteccion, hoy))
        lote.informes.append((camino, informe))

        for codigo in codigo_unico.extraer_de(raiz, deteccion):
            todos.append(codigo)
            procedencias.append(camino.name)

    # Solo interesa lo que cruza ficheros. Lo que ya dijo el informe de un
    # fichero sobre sus propias facturas no se repite aquí.
    dentro_de_uno = {
        _senia(i) for _, informe in lote.informes for i in informe.incidencias
    }
    lote.cruzadas = [
        i
        for i in codigo_unico.reglas_de_lote(todos, procedencias=procedencias)
        if _senia(i) not in dentro_de_uno
    ]
    return lote
