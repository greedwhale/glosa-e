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

# Y cómo debe ser el motivo de exención. Son tres estados y no dos: la norma
# no solo exige el motivo donde hace falta, también lo **prohíbe** donde no
# (BR-S-10 y BR-Z-10). Con un booleano, «no obligatorio» y «prohibido» eran lo
# mismo, y una entrada a tipo cero con motivo de exención pasaba sin más.
OBLIGATORIO = "obligatorio"
PROHIBIDO = "prohibido"
LIBRE = "libre"  # la norma no se pronuncia, y nosotros tampoco


@dataclass(frozen=True)
class ReglaCategoria:
    """Lo que la norma exige a una categoría concreta."""

    codigo: str  # el sufijo del grupo de reglas: BR-S-*, BR-AE-*...
    tipo: str
    motivo: str


REGLAS: dict[str, ReglaCategoria] = {
    "S": ReglaCategoria("S", POSITIVO, PROHIBIDO),
    "Z": ReglaCategoria("Z", CERO, PROHIBIDO),
    "E": ReglaCategoria("E", CERO, OBLIGATORIO),
    "AE": ReglaCategoria("AE", CERO, OBLIGATORIO),
    "K": ReglaCategoria("IC", CERO, OBLIGATORIO),
    "G": ReglaCategoria("G", CERO, OBLIGATORIO),
    "O": ReglaCategoria("O", SIN_TIPO, OBLIGATORIO),
    # IGIC e IPSI llevan tipos propios y la norma no los ata como a las demás.
    # Se exige que declaren tipo y no se opina sobre el motivo.
    "L": ReglaCategoria("IG", CUALQUIERA, LIBRE),
    "M": ReglaCategoria("IP", CUALQUIERA, LIBRE),
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

    `es_ajuste` distingue el cargo o descuento de la línea normal. Es un campo
    y no una lectura de `descripcion` a propósito: la descripción es texto
    para el usuario, y colgar de ella una decisión de negocio significa que el
    día que alguien la reescriba, la lógica cambia sin que nadie se entere.
    """

    descripcion: str
    importe: Decimal
    categoria: str | None
    tipo: Decimal | None
    es_ajuste: bool = False

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
                es_ajuste=True,
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
    descuentos = importe(raiz, sintaxis.descuentos_total, sintaxis) or Decimal(0)
    cargos = importe(raiz, sintaxis.cargos_total, sintaxis) or Decimal(0)
    # Por separado y no sumados: sumándolos, un descuento y un cargo del mismo
    # importe se anulan y la factura parecería no declarar ninguno.
    declarados = descuentos != 0 or cargos != 0
    return declarados and not any(a.es_ajuste for a in apuntes)


def _ajustes_no_cuadran(raiz, sintaxis: Sintaxis, apuntes: list[Apunte]) -> bool:
    """Los ajustes vienen detallados, pero no suman lo que declara la factura.

    Entonces tampoco son de fiar para repartir la base por tipos: no se sabe
    cuál de las dos cifras es la buena. Aquí no se dice nada porque ya lo dicen
    BR-CO-11 y BR-CO-12 desde `en16931`, y lo dicen señalando el campo que está
    mal. Comprobar además la base por tipo sacaría una segunda queja apuntando
    al desglose, que es donde no está el problema.
    """
    detallados = [a for a in apuntes if a.es_ajuste]
    if not detallados:
        return False
    descuentos = sum((-a.importe for a in detallados if a.importe < 0), Decimal(0))
    cargos = sum((a.importe for a in detallados if a.importe > 0), Decimal(0))
    declarado_descuentos = importe(raiz, sintaxis.descuentos_total, sintaxis)
    declarado_cargos = importe(raiz, sintaxis.cargos_total, sintaxis)
    return (
        declarado_descuentos is not None
        and not cuadra(descuentos, declarado_descuentos)
    ) or (declarado_cargos is not None and not cuadra(cargos, declarado_cargos))


def _regla_base_por_grupo(grupo: Grupo, apuntes: list[Apunte]) -> list[Incidencia]:
    """BR-{X}-8: la base de cada entrada del desglose es la suma de lo suyo."""
    if grupo.base is None or grupo.categoria is None:
        return []
    regla = REGLAS.get(grupo.categoria)
    codigo = f"BR-{regla.codigo}-8" if regla else "IVA-BASE"
    suyos = [a for a in apuntes if a.clave == grupo.clave]

    if not suyos:
        # Base fantasma: el desglose cobra sobre algo que no está en ninguna
        # parte. La suma de lo suyo es cero, así que técnicamente es la misma
        # regla, pero decirlo como «debería ser 0.00» no ayuda a nadie.
        #
        # Solo se dice si el documento clasifica sus conceptos. Si ninguno
        # lleva categoría no es que falten: es que no se han podido leer, y de
        # eso avisa IVA-SIN-CATEGORIA.
        if grupo.base == 0 or not any(a.categoria for a in apuntes):
            return []
        return [
            Incidencia(
                codigo,
                ERROR,
                f"El desglose declara base para {grupo}, pero no hay ningún "
                "concepto a ese tipo. O sobra esa entrada del desglose, o hay "
                "una línea con la categoría o el tipo cambiados.",
                campo=f"Base imponible de {grupo}",
                esperado="algún concepto que vaya a ese tipo",
                encontrado=f"{grupo.base:.2f} sin nada detrás",
            )
        ]

    suma = sum((a.importe for a in suyos), Decimal(0))
    if cuadra(suma, grupo.base):
        return []
    return [
        Incidencia(
            codigo,
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


def _reglas_campos_del_grupo(grupo: Grupo) -> list[Incidencia]:
    """BR-45 a BR-48: los cuatro datos que toda entrada del desglose debe traer.

    Sin esto, una entrada a la que le faltaba la base y la cuota era invisible:
    las reglas de cuadre se saltan lo que está a None, así que el desglose más
    roto posible salía en el informe más limpio. De paso enmudecía BR-CO-14,
    que suma cuotas y no encontraba ninguna que sumar.
    """
    incidencias: list[Incidencia] = []

    if grupo.base is None:
        incidencias.append(
            Incidencia(
                "BR-45",
                ERROR,
                "Hay una entrada del desglose sin base imponible. Cada tipo "
                "debe declarar sobre cuánto se calcula.",
                campo=f"Base imponible de {grupo}",
                encontrado="(falta)",
            )
        )

    if grupo.cuota is None:
        incidencias.append(
            Incidencia(
                "BR-46",
                ERROR,
                "Hay una entrada del desglose sin importe de IVA. Cada tipo "
                "debe declarar cuánto impuesto sale.",
                campo=f"Cuota de {grupo}",
                encontrado="(falta)",
            )
        )

    if grupo.categoria is None:
        incidencias.append(
            Incidencia(
                "BR-47",
                ERROR,
                "Hay una entrada del desglose sin categoría de IVA. Sin ella no "
                "se sabe si es tipo general, exenta o no sujeta.",
                campo="Desglose de IVA",
                encontrado="(sin categoría)",
            )
        )

    # BR-48: el tipo es obligatorio salvo en lo no sujeto, que no tiene tipo
    # que aplicar. Aquí se mira solo si **falta**; que el valor sea el que le
    # toca a la categoría lo miran las BR-{X}-5.
    if grupo.tipo is None and grupo.categoria != "O":
        incidencias.append(
            Incidencia(
                "BR-48",
                ERROR,
                "Hay una entrada del desglose sin tipo de IVA. Solo lo no "
                "sujeto (categoría O) puede ir sin tipo.",
                campo=f"Tipo de {nombre_categoria(grupo.categoria)}",
                encontrado="(sin tipo)",
            )
        )

    return incidencias


def _regla_forma_del_grupo(grupo: Grupo) -> list[Incidencia]:
    """BR-{X}-5 y BR-{X}-10: el tipo y el motivo que pide cada categoría."""
    if grupo.categoria is None:
        return []  # de eso ya se queja BR-47

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

    # Que el tipo **falte** lo dice BR-48, una sola vez para todas las
    # categorías. Aquí se mira si el valor es el que le toca a esta: dos
    # quejas para un mismo tipo ausente sería decir lo mismo dos veces.
    if regla.tipo == SIN_TIPO:
        if grupo.tipo is not None:
            incidencias.append(
                Incidencia(
                    f"BR-{regla.codigo}-5",
                    ERROR,
                    f"Una operación a {nombre} no debe declarar tipo de IVA: si "
                    "no está sujeta, no hay tipo que aplicar.",
                    campo=f"Tipo de {nombre}",
                    esperado="(sin tipo)",
                    encontrado=fmt_tipo(grupo.tipo),
                )
            )
    elif grupo.tipo is None:
        pass  # ya lo ha dicho BR-48
    elif regla.tipo == POSITIVO and grupo.tipo <= 0:
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
    elif regla.tipo == CERO and grupo.tipo != 0:
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

    if regla.motivo == OBLIGATORIO and not grupo.motivo:
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
    elif regla.motivo == PROHIBIDO and grupo.motivo:
        incidencias.append(
            Incidencia(
                f"BR-{regla.codigo}-10",
                ERROR,
                f"Una operación a {nombre} no debe llevar motivo de exención: "
                "esa categoría no es una exención, y el motivo es justamente "
                "lo que justifica una. Si la operación de verdad está exenta, "
                "la categoría es otra: E, AE, K o G según el caso.",
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
                # Sin `regla` la categoría no es ninguna de la norma, así que
                # no hay BR-{X}-1 que citar. `IVA-SIN-DESGLOSE` era un nombre
                # prestado y ahora confundiría con BR-CO-18, que es el que dice
                # que no hay desglose ninguno.
                f"BR-{regla.codigo}-1" if regla else "IVA-CATEGORIA-SIN-DESGLOSE",
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
        # BR-CO-18: toda factura tiene que traer al menos un desglose. No es un
        # aviso ni depende de que se declare importe de impuestos: sin desglose
        # no hay nada que comprobar y el receptor lo rechaza. Antes esto era un
        # aviso propio y solo saltaba si el IVA declarado no era cero, así que
        # una factura sin desglose y sin total pasaba en silencio.
        moneda = texto(raiz, sintaxis.moneda, sintaxis)
        declarado = importe_en_moneda(raiz, sintaxis.impuestos, sintaxis, moneda)
        return [
            Incidencia(
                "BR-CO-18",
                ERROR,
                "La factura no trae el desglose de IVA. Hace falta una entrada "
                "por cada combinación de categoría y tipo, con su base y su "
                "cuota; sin eso no se puede comprobar el impuesto.",
                campo="Desglose de IVA",
                esperado="al menos una entrada del desglose",
                encontrado=(
                    "(no hay ninguna)"
                    if declarado is None
                    else f"{declarado:.2f} de IVA sin desglosar"
                ),
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

    # Con los ajustes sin detallar no se puede repartir la base; con los
    # ajustes detallados pero descuadrados, tampoco, y encima ya hay quien lo
    # dice mejor (BR-CO-11 y BR-CO-12). En los dos casos se calla BR-{X}-8.
    a_ciegas = a_ciegas or _ajustes_no_cuadran(raiz, sintaxis, apuntes)

    for grupo in grupos:
        incidencias.extend(_reglas_campos_del_grupo(grupo))
        incidencias.extend(_regla_forma_del_grupo(grupo))
        if not a_ciegas:
            incidencias.extend(_regla_base_por_grupo(grupo, apuntes))
        incidencias.extend(_regla_cuota_por_grupo(grupo))
    incidencias.extend(_regla_hay_desglose(grupos, apuntes))
    incidencias.extend(_regla_no_sujeta_a_solas(grupos))
    incidencias.extend(_regla_tipos_espanoles(grupos))
    incidencias.extend(_regla_lineas_con_categoria(apuntes))
    return incidencias
