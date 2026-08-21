"""Las reglas de IVA de EN 16931: el desglose por tipo tiene que cuadrar.

Una factura no lleva un solo importe de impuesto: lleva un **desglose** (el
grupo BG-23 de la norma), con una entrada por cada combinación de categoría y
tipo. Una factura con material al 21% y comida al 10% tiene dos entradas, y
cada una debe declarar su base y su cuota.

Ahí es donde se cuela el error más caro y más difícil de ver: alguien cambia el
tipo de una línea y no recalcula el desglose. Las cuentas generales siguen
cuadrando —la suma de líneas es la misma— y sin embargo la factura declara mal
el IVA, que es justo lo que mira Hacienda.

La norma tiene una familia de reglas por categoría: BR-S-* para el tipo
general, BR-E-* para las exentas, BR-AE-* para la inversión del sujeto pasivo,
y así. Todas siguen el mismo patrón, así que aquí las categorías son datos y
las comprobaciones son código, igual que con las sintaxis.

Sobre los códigos: los que empiezan por `BR-` son de la norma. Los que empiezan
por `IVA-` son de la casa, comprobaciones que no están en EN 16931 pero que
tienen sentido para quien factura en España; van marcadas aparte para que no
haya duda de qué exige la norma y qué opinamos nosotros.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from validador.incidencias import AVISO, ERROR, Incidencia
from validador.sintaxis import (
    Sintaxis,
    a_decimal,
    cuadra,
    fmt,
    fmt_tipo,
    importe,
    importe_en_moneda,
    texto,
)

# Categorías de IVA de la norma (lista UNCL 5305), en castellano. Las dos
# últimas son españolas y casi ninguna herramienta europea las nombra.
CATEGORIAS: dict[str, str] = {
    "S": "tipo general",
    "Z": "tipo cero",
    "E": "operación exenta",
    "AE": "inversión del sujeto pasivo",
    "K": "entrega intracomunitaria",
    "G": "exportación fuera de la UE",
    "O": "operación no sujeta",
    "L": "IGIC (Canarias)",
    "M": "IPSI (Ceuta y Melilla)",
}

# Tipos de IVA vigentes en España. No es una regla de EN 16931 —la norma no
# sabe de tipos nacionales— pero un 15% en una factura española es casi seguro
# un dedo torcido, así que se avisa.
TIPOS_ESPANOLES = (Decimal(21), Decimal(10), Decimal(4), Decimal(0))

# Cómo debe ser el tipo de cada categoría.
POSITIVO = "positivo"  # tiene que haber tipo y ser mayor que cero
CERO = "cero"  # tiene que haber tipo y ser cero
SIN_TIPO = "sin tipo"  # no debe declararse tipo
CUALQUIERA = "cualquiera"  # tiene que haber tipo, del valor que sea


@dataclass(frozen=True)
class ReglaCategoria:
    """Lo que la norma exige a una categoría concreta."""

    codigo: str  # el sufijo del grupo de reglas: BR-S-*, BR-AE-*...
    tipo: str
    motivo_obligatorio: bool


REGLAS: dict[str, ReglaCategoria] = {
    "S": ReglaCategoria("S", POSITIVO, False),
    "Z": ReglaCategoria("Z", CERO, False),
    "E": ReglaCategoria("E", CERO, True),
    "AE": ReglaCategoria("AE", CERO, True),
    "K": ReglaCategoria("IC", CERO, True),
    "G": ReglaCategoria("G", CERO, True),
    "O": ReglaCategoria("O", SIN_TIPO, True),
    # IGIC e IPSI llevan tipos propios y la norma no los ata como a las demás.
    # Se exige que declaren tipo y no se opina sobre el motivo.
    "L": ReglaCategoria("IG", CUALQUIERA, False),
    "M": ReglaCategoria("IP", CUALQUIERA, False),
}


def nombre_categoria(codigo: str | None) -> str:
    if not codigo:
        return "sin categoría"
    return f"{codigo} ({CATEGORIAS.get(codigo, 'categoría no reconocida')})"


# --- Lo que hay escrito en la factura --------------------------------------


@dataclass(frozen=True)
class Grupo:
    """Una entrada del desglose de IVA: BG-23."""

    categoria: str | None
    tipo: Decimal | None
    base: Decimal | None
    cuota: Decimal | None
    motivo: str | None

    @property
    def clave(self) -> tuple[str | None, Decimal | None]:
        return (self.categoria, self.tipo)

    def __str__(self) -> str:
        return f"{nombre_categoria(self.categoria)} al {fmt_tipo(self.tipo)}"


@dataclass(frozen=True)
class Apunte:
    """Algo que entra en la base de una categoría: una línea o un cargo.

    Los descuentos entran con importe negativo, que es lo que los hace restar
    sin necesidad de tratarlos aparte.
    """

    descripcion: str
    importe: Decimal
    categoria: str | None
    tipo: Decimal | None

    @property
    def clave(self) -> tuple[str | None, Decimal | None]:
        return (self.categoria, self.tipo)


def _leer_grupos(raiz, sintaxis: Sintaxis) -> list[Grupo]:
    grupos = []
    for nodo in raiz.xpath(sintaxis.desglose, namespaces=sintaxis.espacios):
        motivo = texto(nodo, sintaxis.desglose_motivo, sintaxis) or texto(
            nodo, sintaxis.desglose_motivo_codigo, sintaxis
        )
        grupos.append(
            Grupo(
                categoria=texto(nodo, sintaxis.desglose_categoria, sintaxis),
                tipo=importe(nodo, sintaxis.desglose_tipo, sintaxis),
                base=importe(nodo, sintaxis.desglose_base, sintaxis),
                cuota=importe(nodo, sintaxis.desglose_cuota, sintaxis),
                motivo=motivo,
            )
        )
    return grupos


def _leer_apuntes(raiz, sintaxis: Sintaxis) -> list[Apunte]:
    apuntes = []
    for indice, nodo in enumerate(
        raiz.xpath(sintaxis.lineas, namespaces=sintaxis.espacios), start=1
    ):
        cantidad = importe(nodo, sintaxis.linea_importe, sintaxis)
        if cantidad is None:
            continue  # de la línea sin importe ya se queja BR-24
        identificador = texto(nodo, sintaxis.linea_id, sintaxis) or str(indice)
        apuntes.append(
            Apunte(
                descripcion=f"línea {identificador}",
                importe=cantidad,
                categoria=texto(nodo, sintaxis.linea_categoria, sintaxis),
                tipo=importe(nodo, sintaxis.linea_tipo, sintaxis),
            )
        )

    for indice, nodo in enumerate(
        raiz.xpath(sintaxis.cargos, namespaces=sintaxis.espacios), start=1
    ):
        cantidad = importe(nodo, sintaxis.cargo_importe, sintaxis)
        if cantidad is None:
            continue
        marca = (texto(nodo, sintaxis.cargo_es_cargo, sintaxis) or "").lower()
        es_cargo = marca in ("true", "1")
        apuntes.append(
            Apunte(
                descripcion=("cargo" if es_cargo else "descuento") + f" {indice}",
                importe=cantidad if es_cargo else -cantidad,
                categoria=texto(nodo, sintaxis.cargo_categoria, sintaxis),
                tipo=importe(nodo, sintaxis.cargo_tipo, sintaxis),
            )
        )
    return apuntes


# --- Reglas ----------------------------------------------------------------


def _regla_total(raiz, sintaxis: Sintaxis, grupos: list[Grupo]) -> list[Incidencia]:
    """BR-CO-14: el total de IVA es la suma de las cuotas del desglose."""
    moneda = texto(raiz, sintaxis.moneda, sintaxis)
    declarado = importe_en_moneda(raiz, sintaxis.impuestos, sintaxis, moneda)
    if declarado is None:
        return []
    con_cuota = [g for g in grupos if g.cuota is not None]
    if not con_cuota:
        return []
    suma = sum((g.cuota for g in con_cuota), Decimal(0))
    if cuadra(suma, declarado):
        return []
    return [
        Incidencia(
            "BR-CO-14",
            ERROR,
            "El importe total de IVA no coincide con la suma de las cuotas del "
            "desglose. Suele pasar al cambiar el tipo de una línea sin "
            "rehacer el desglose.",
            campo="Importe total de impuestos",
            esperado=(
                f"{suma:.2f} (suma de "
                + (
                    "la única entrada"
                    if len(con_cuota) == 1
                    else f"las {len(con_cuota)} entradas"
                )
                + " del desglose)"
            ),
            encontrado=fmt(declarado),
        )
    ]


def _ajustes_sin_detallar(raiz, sintaxis: Sintaxis, apuntes: list[Apunte]) -> bool:
    """La factura declara descuentos o cargos globales pero no los detalla.

    Cuando pasa eso no se sabe a qué tipo de IVA va cada ajuste, así que la
    base por categoría no puede cuadrar y comprobarla sería inventarse un
    error. La norma exige detallarlos (BR-CO-11 y BR-CO-12), pero es mejor
    decir «no se ha podido comprobar» que acusar en falso.
    """
    declarados = (importe(raiz, sintaxis.descuentos_total, sintaxis) or Decimal(0)) + (
        importe(raiz, sintaxis.cargos_total, sintaxis) or Decimal(0)
    )
    detallados = any(a.descripcion.startswith(("cargo", "descuento")) for a in apuntes)
    return declarados != 0 and not detallados


def _regla_base_por_grupo(grupo: Grupo, apuntes: list[Apunte]) -> list[Incidencia]:
    """BR-{X}-8: la base de cada entrada del desglose es la suma de lo suyo."""
    if grupo.base is None or grupo.categoria is None:
        return []
    suyos = [a for a in apuntes if a.clave == grupo.clave]
    if not suyos:
        return []
    suma = sum((a.importe for a in suyos), Decimal(0))
    if cuadra(suma, grupo.base):
        return []
    regla = REGLAS.get(grupo.categoria)
    return [
        Incidencia(
            f"BR-{regla.codigo}-8" if regla else "IVA-BASE",
            ERROR,
            f"La base declarada para {grupo} no coincide con la suma de lo que "
            "va a ese tipo.",
            campo=f"Base imponible de {grupo}",
            esperado=f"{suma:.2f} ({', '.join(a.descripcion for a in suyos)})",
            encontrado=fmt(grupo.base),
        )
    ]


def _regla_cuota_por_grupo(grupo: Grupo) -> list[Incidencia]:
    """BR-CO-17: cuota = base x tipo / 100, redondeada a dos decimales."""
    if grupo.base is None or grupo.cuota is None or grupo.tipo is None:
        return []
    calculada = (grupo.base * grupo.tipo / Decimal(100)).quantize(Decimal("0.01"))
    if cuadra(calculada, grupo.cuota):
        return []
    return [
        Incidencia(
            "BR-CO-17",
            ERROR,
            f"La cuota de IVA de {grupo} no sale de aplicar el tipo a la base.",
            campo=f"Cuota de {grupo}",
            esperado=(
                f"{calculada:.2f} ({grupo.base:.2f} x {fmt_tipo(grupo.tipo)})"
            ),
            encontrado=fmt(grupo.cuota),
        )
    ]


def _regla_forma_del_grupo(grupo: Grupo) -> list[Incidencia]:
    """BR-{X}-5 y BR-{X}-10: el tipo y el motivo que pide cada categoría."""
    if grupo.categoria is None:
        return [
            Incidencia(
                "IVA-SIN-CATEGORIA",
                ERROR,
                "Hay una entrada del desglose sin categoría de IVA. Sin ella no "
                "se sabe si es tipo general, exenta o no sujeta.",
                campo="Desglose de IVA",
                encontrado="(sin categoría)",
            )
        ]

    regla = REGLAS.get(grupo.categoria)
    if regla is None:
        return [
            Incidencia(
                "IVA-CATEGORIA-RARA",
                AVISO,
                f"«{grupo.categoria}» no es una categoría de IVA de la norma. "
                "Las admitidas son " + ", ".join(sorted(CATEGORIAS)) + ".",
                campo="Desglose de IVA",
                encontrado=grupo.categoria,
            )
        ]

    incidencias: list[Incidencia] = []
    nombre = nombre_categoria(grupo.categoria)

    if regla.tipo == POSITIVO and not (grupo.tipo and grupo.tipo > 0):
        incidencias.append(
            Incidencia(
                f"BR-{regla.codigo}-5",
                ERROR,
                f"Una operación a {nombre} tiene que llevar un tipo mayor que "
                "cero. Si de verdad no lleva impuesto, la categoría es otra: Z "
                "para tipo cero, E para exenta, O para no sujeta.",
                campo=f"Tipo de {nombre}",
                esperado="mayor que 0",
                encontrado=fmt_tipo(grupo.tipo),
            )
        )
    elif regla.tipo == CERO and (grupo.tipo is None or grupo.tipo != 0):
        incidencias.append(
            Incidencia(
                f"BR-{regla.codigo}-5",
                ERROR,
                f"Una operación a {nombre} tiene que llevar el tipo a cero.",
                campo=f"Tipo de {nombre}",
                esperado="0",
                encontrado=fmt_tipo(grupo.tipo),
            )
        )
    elif regla.tipo == SIN_TIPO and grupo.tipo is not None:
        incidencias.append(
            Incidencia(
                f"BR-{regla.codigo}-5",
                ERROR,
                f"Una operación a {nombre} no debe declarar tipo de IVA: si no "
                "está sujeta, no hay tipo que aplicar.",
                campo=f"Tipo de {nombre}",
                esperado="(sin tipo)",
                encontrado=fmt_tipo(grupo.tipo),
            )
        )
    elif regla.tipo == CUALQUIERA and grupo.tipo is None:
        incidencias.append(
            Incidencia(
                f"BR-{regla.codigo}-5",
                ERROR,
                f"Una operación a {nombre} tiene que declarar su tipo.",
                campo=f"Tipo de {nombre}",
                encontrado="(sin tipo)",
            )
        )

    if regla.motivo_obligatorio and not grupo.motivo:
        incidencias.append(
            Incidencia(
                f"BR-{regla.codigo}-10",
                ERROR,
                f"Una operación a {nombre} tiene que explicar por qué no lleva "
                "IVA. Sin ese motivo, el receptor no puede justificar la "
                "deducción.",
                campo=f"Motivo de {nombre}",
                esperado="el artículo o la razón de la exención",
                encontrado="(sin motivo)",
            )
        )
    elif not regla.motivo_obligatorio and grupo.motivo and regla.tipo == POSITIVO:
        incidencias.append(
            Incidencia(
                f"BR-{regla.codigo}-10",
                ERROR,
                f"Una operación a {nombre} no debe llevar motivo de exención: "
                "si se cobra IVA, no hay nada que eximir.",
                campo=f"Motivo de {nombre}",
                esperado="(sin motivo)",
                encontrado=grupo.motivo,
            )
        )

    return incidencias


def _regla_hay_desglose(
    grupos: list[Grupo], apuntes: list[Apunte]
) -> list[Incidencia]:
    """BR-{X}-1: cada categoría usada tiene que aparecer en el desglose."""
    declaradas = {g.categoria for g in grupos if g.categoria}
    incidencias = []
    for categoria in sorted({a.categoria for a in apuntes if a.categoria}):
        if categoria in declaradas:
            continue
        regla = REGLAS.get(categoria)
        usados = [a.descripcion for a in apuntes if a.categoria == categoria]
        incidencias.append(
            Incidencia(
                f"BR-{regla.codigo}-1" if regla else "IVA-SIN-DESGLOSE",
                ERROR,
                f"Hay operaciones a {nombre_categoria(categoria)} pero el "
                "desglose de IVA no recoge esa categoría.",
                campo="Desglose de IVA",
                esperado=f"una entrada del desglose para {categoria}",
                encontrado=", ".join(usados),
            )
        )

    # De la casa: la norma habla de categorías, pero el desglose va por
    # categoría **y tipo**. Si hay conceptos al 10% y el desglose solo trae el
    # 21%, la categoría está declarada y aun así falta media factura. Sin
    # esto solo se veía la otra mitad del error, la base que no cuadra.
    claves_declaradas = {g.clave for g in grupos}
    vistas: set[tuple[str | None, Decimal | None]] = set()
    for apunte in apuntes:
        if not apunte.categoria or apunte.categoria not in declaradas:
            continue
        if apunte.clave in claves_declaradas or apunte.clave in vistas:
            continue
        vistas.add(apunte.clave)
        suyos = [a.descripcion for a in apuntes if a.clave == apunte.clave]
        suma = sum((a.importe for a in apuntes if a.clave == apunte.clave), Decimal(0))
        incidencias.append(
            Incidencia(
                "IVA-TIPO-SIN-DESGLOSE",
                ERROR,
                f"Hay {suma:.2f} a {nombre_categoria(apunte.categoria)} al "
                f"{fmt_tipo(apunte.tipo)}, pero el desglose no trae ninguna "
                "entrada a ese tipo. El desglose va por categoría y tipo, no "
                "solo por categoría.",
                campo="Desglose de IVA",
                esperado=f"una entrada al {fmt_tipo(apunte.tipo)}",
                encontrado=", ".join(suyos),
            )
        )
    return incidencias


def _regla_no_sujeta_a_solas(grupos: list[Grupo]) -> list[Incidencia]:
    """BR-O-11: si algo no está sujeto, no puede haber nada más en la factura."""
    categorias = {g.categoria for g in grupos if g.categoria}
    if "O" not in categorias or len(categorias) == 1:
        return []
    return [
        Incidencia(
            "BR-O-11",
            ERROR,
            "La factura mezcla operaciones no sujetas con operaciones sujetas. "
            "Lo no sujeto va en factura aparte.",
            campo="Desglose de IVA",
            esperado="solo la categoría O",
            encontrado=", ".join(sorted(categorias)),
        )
    ]


def _regla_tipos_espanoles(grupos: list[Grupo]) -> list[Incidencia]:
    """De la casa: un tipo que no existe en España casi siempre es un dedazo."""
    incidencias = []
    for grupo in grupos:
        if grupo.tipo is None or grupo.tipo in TIPOS_ESPANOLES:
            continue
        if grupo.categoria in ("L", "M"):
            continue  # IGIC e IPSI tienen sus propios tipos
        incidencias.append(
            Incidencia(
                "IVA-TIPO",
                AVISO,
                f"{fmt_tipo(grupo.tipo)} no es un tipo de IVA vigente en "
                "España. Es legal si la operación tributa en otro país, pero "
                "si no, es un dedo torcido.",
                campo=f"Tipo de {nombre_categoria(grupo.categoria)}",
                esperado="21%, 10%, 4% o 0%",
                encontrado=fmt_tipo(grupo.tipo),
            )
        )
    return incidencias


def _regla_lineas_con_categoria(apuntes: list[Apunte]) -> list[Incidencia]:
    """De la casa: sin categoría en la línea no hay desglose que comprobar."""
    huerfanos = [a.descripcion for a in apuntes if not a.categoria]
    if not huerfanos:
        return []
    return [
        Incidencia(
            "IVA-SIN-CATEGORIA",
            AVISO,
            "Hay conceptos sin categoría de IVA, así que no se ha podido "
            "comprobar que el desglose cuadre con ellos.",
            campo="Conceptos: " + ", ".join(huerfanos),
            encontrado="(sin categoría de IVA)",
        )
    ]


# --- Entrada pública -------------------------------------------------------


def reglas(raiz, sintaxis: Sintaxis) -> list[Incidencia]:
    """Todas las comprobaciones de IVA sobre un documento ya parseado."""
    grupos = _leer_grupos(raiz, sintaxis)
    apuntes = _leer_apuntes(raiz, sintaxis)

    if not grupos:
        moneda = texto(raiz, sintaxis.moneda, sintaxis)
        declarado = importe_en_moneda(raiz, sintaxis.impuestos, sintaxis, moneda)
        if declarado is None or declarado == 0:
            return []
        return [
            Incidencia(
                "IVA-SIN-DESGLOSE",
                AVISO,
                "La factura declara un importe de IVA pero no trae el desglose "
                "por tipo. Sin él no se puede comprobar que el impuesto esté "
                "bien calculado, y un receptor estricto lo rechazará.",
                campo="Desglose de IVA",
                esperado="una entrada por cada combinación de categoría y tipo",
                encontrado=f"{declarado:.2f} de IVA sin desglosar",
            )
        ]

    incidencias: list[Incidencia] = []
    incidencias.extend(_regla_total(raiz, sintaxis, grupos))

    a_ciegas = _ajustes_sin_detallar(raiz, sintaxis, apuntes)
    if a_ciegas:
        incidencias.append(
            Incidencia(
                "IVA-AJUSTES-SIN-DETALLAR",
                AVISO,
                "La factura declara descuentos o cargos globales pero no dice "
                "cuáles son ni a qué tipo van, así que no se ha podido "
                "comprobar la base de cada tipo. La norma pide detallarlos.",
                campo="Descuentos y cargos de documento",
                esperado="un bloque por cada descuento o cargo, con su tipo",
                encontrado="solo el total",
            )
        )

    for grupo in grupos:
        incidencias.extend(_regla_forma_del_grupo(grupo))
        if not a_ciegas:
            incidencias.extend(_regla_base_por_grupo(grupo, apuntes))
        incidencias.extend(_regla_cuota_por_grupo(grupo))
    incidencias.extend(_regla_hay_desglose(grupos, apuntes))
    incidencias.extend(_regla_no_sujeta_a_solas(grupos))
    incidencias.extend(_regla_tipos_espanoles(grupos))
    incidencias.extend(_regla_lineas_con_categoria(apuntes))
    return incidencias
