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

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from validador import cifras
from validador.incidencias import AVISO, ERROR, NOTA, Incidencia
from validador.sintaxis import (
    SIN_MAPA,
    Sintaxis,
    a_menos_de_una_unidad,
    cuadra,
    cuadra_exacto,
    importe,
    importe_en_moneda,
    redondear,
    texto,
)

# Categorías de IVA de la norma (lista UNCL 5305), en castellano. Las dos
# últimas son impuestos españoles, y **están en la lista de la norma europea**
# con reglas propias, igual que las demás: BR-CL-18 las admite y el esquematrón
# tiene una familia BR-AF-* para el IGIC y otra BR-AG-* para el IPSI. Aquí se
# llegó a escribir lo contrario, y de ahí salió el fallo que cuenta `REGLAS`.
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
NO_NEGATIVO = "cero o positivo"  # tiene que haber tipo y no ser negativo

# Y cómo debe ser el motivo de exención. La norma no solo lo exige donde hace
# falta: también lo **prohíbe** donde no (BR-S-10, BR-Z-10, BR-AF-10,
# BR-AG-10). Con un solo «¿lo exige?», «no obligatorio» y «prohibido» eran lo
# mismo, y una entrada a tipo cero con motivo de exención pasaba sin más.
#
# Hubo un tercer estado, `LIBRE` —«la norma no se pronuncia»—, y con él un
# `CUALQUIERA` para el tipo. Los dos existían solo para IGIC e IPSI, y los dos
# estaban mal: se quitaron el 13-09-2026. Lo cuenta `REGLAS`.
OBLIGATORIO = "obligatorio"
PROHIBIDO = "prohibido"

# Y cuántas entradas del desglose admite (BR-{X}-01). El tipo general, el IGIC
# y el IPSI pueden llevar varias —una por tipo: el 21 y el 10 son dos—; las
# categorías que van a cero o sin tipo, **una y solo una**. Aquí solo se miraba
# que estuviera, y dos entradas exentas pasaban: lo cazaron las pruebas
# oficiales el 13-09-2026, que traen justo ese caso.
AL_MENOS_UNA = "al menos una"
UNA_SOLA = "una sola"


@dataclass(frozen=True)
class ReglaCategoria:
    """Lo que la norma exige a una categoría concreta."""

    codigo: str  # el sufijo del grupo de reglas: BR-S-*, BR-AE-*...
    tipo: str
    motivo: str
    desgloses: str


REGLAS: dict[str, ReglaCategoria] = {
    "S": ReglaCategoria("S", POSITIVO, PROHIBIDO, AL_MENOS_UNA),
    "Z": ReglaCategoria("Z", CERO, PROHIBIDO, UNA_SOLA),
    "E": ReglaCategoria("E", CERO, OBLIGATORIO, UNA_SOLA),
    "AE": ReglaCategoria("AE", CERO, OBLIGATORIO, UNA_SOLA),
    "K": ReglaCategoria("IC", CERO, OBLIGATORIO, UNA_SOLA),
    "G": ReglaCategoria("G", CERO, OBLIGATORIO, UNA_SOLA),
    "O": ReglaCategoria("O", SIN_TIPO, OBLIGATORIO, UNA_SOLA),
    # IGIC e IPSI: el tipo puede ser cero o positivo, nunca negativo
    # (BR-AF-05 a 07, «0 (zero) or greater than zero»), y el motivo de
    # exención está prohibido (BR-AF-10, «shall not have»), igual que en el
    # tipo general. Lo mismo con BR-AG-* para el IPSI.
    #
    # **Hasta el 13-09-2026 aquí ponía lo contrario**: que la norma no ataba a
    # estas dos categorías, con `CUALQUIERA` para el tipo y `LIBRE` para el
    # motivo. Nadie lo había leído en el esquematrón; se supuso por ser
    # impuestos propios. Con eso un IGIC con tipo negativo o con un artículo de
    # exención pegado pasaba limpio, y ocho reglas que la norma sí tiene se
    # publicaron como inexistentes. Salió al medir la cobertura contra el
    # esquematrón oficial (v1.3.16), no de ninguna prueba: las pruebas estaban
    # escritas desde la misma suposición que el código.
    #
    # Los códigos son AF y AG, no IG e IP. Lo de antes se lo inventó quien
    # escribió esto —o sea, nosotros— por analogía con IC, y da la casualidad
    # de que IGIC es el impuesto de Canarias: una factura canaria recibía una
    # regla «BR-IG-5» que no existe en ninguna norma. Comprobado en el
    # esquematrón oficial: $VATIG lleva BR-AF-* y $VATIP lleva BR-AG-*.
    "L": ReglaCategoria("AF", NO_NEGATIVO, PROHIBIDO, AL_MENOS_UNA),
    "M": ReglaCategoria("AG", NO_NEGATIVO, PROHIBIDO, AL_MENOS_UNA),
}

# Que no vuelva a entrar un estado que no se queja de nada. Si una categoría
# lleva un tipo o un motivo que las reglas no saben comprobar, el módulo no se
# carga: preferible a un validador que pasa en limpio lo que no mira.
for _categoria, _regla in REGLAS.items():
    if _regla.tipo not in (POSITIVO, CERO, SIN_TIPO, NO_NEGATIVO):
        raise ValueError(f"{_categoria}: tipo sin comprobación, {_regla.tipo!r}")
    if _regla.motivo not in (OBLIGATORIO, PROHIBIDO):
        raise ValueError(f"{_categoria}: motivo sin comprobación, {_regla.motivo!r}")
    if _regla.desgloses not in (AL_MENOS_UNA, UNA_SOLA):
        raise ValueError(f"{_categoria}: desgloses sin comprobación, {_regla.desgloses!r}")


# Los códigos que este módulo compone en tiempo de ejecución, y que por eso no
# se pueden leer del fuente: `f"BR-{regla.codigo}-08"` no dice cuál es hasta que
# hay una factura delante. Se declaran aquí, pegados a la tabla de la que
# salen, y `codigos.py` los recoge para que tengan su ficha como los demás.
#
# Son nueve categorías por diez reglas, 90, y ninguna rama se queda muda: cada
# estado del tipo rechaza algún valor y cada estado del motivo se queja por
# algún lado. Durante un día se declararon 46, con ocho de IGIC e IPSI dados
# por inexistentes porque la tabla de arriba decía que la norma no ataba a esas
# categorías; la norma sí las ata. Fueron 54 hasta el 14-09-2026, cuando llegaron
# la cuota de cada categoría, BR-{X}-09, y los identificadores, 02 a 04.
#
# Las condiciones son las mismas que aplican las reglas, y eso es una
# duplicación a la vista: la sostiene una prueba que provoca las cuatro reglas
# con cada categoría y compara lo que sale de verdad con lo que aquí se
# declara, y otra que compara la tabla con el texto del esquematrón, porque las
# dos primeras pueden coincidir y estar mal a la vez. Pasó.
def _codigos_compuestos() -> dict[str, tuple[str, ...]]:
    por_patron: dict[str, list[str]] = {}
    for regla in REGLAS.values():
        # La categoría usada que el desglose no recoge, y la base de la
        # entrada contra lo suyo.
        por_patron.setdefault("BR-{}-01", []).append(f"BR-{regla.codigo}-01")
        por_patron.setdefault("BR-{}-08", []).append(f"BR-{regla.codigo}-08")
        # La cuota de la entrada: cero donde no hay impuesto, base por tipo
        # donde lo hay.
        por_patron.setdefault("BR-{}-09", []).append(f"BR-{regla.codigo}-09")
        # El tipo del concepto, partido en tres según de qué cuelgue.
        for sufijo in ("05", "06", "07"):
            por_patron.setdefault("BR-{}-{}", []).append(
                f"BR-{regla.codigo}-{sufijo}"
            )
        # El motivo de exención, que falte o que sobre.
        por_patron.setdefault("BR-{}-10", []).append(f"BR-{regla.codigo}-10")
        # Los identificadores fiscales que la categoría exige o prohíbe, según
        # la use una línea, un descuento o un cargo.
        for cifra in ("2", "3", "4"):
            por_patron.setdefault("BR-{}-0{}", []).append(
                f"BR-{regla.codigo}-0{cifra}"
            )
    return {patron: tuple(sorted(set(suyos))) for patron, suyos in por_patron.items()}


CODIGOS_COMPUESTOS: dict[str, tuple[str, ...]] = _codigos_compuestos()


def _clave(
    categoria: str | None, tipo: Decimal | None
) -> tuple[str | None, Decimal | None]:
    """Cómo se emparejan el desglose y los conceptos que lo alimentan.

    Por categoría **y tipo**, porque así va el desglose: material al 21% y
    comida al 10% son dos entradas aunque las dos sean categoría S.

    La excepción son las categorías de **una sola entrada** —Z, E, AE, K, G y
    O—: todo lo que va a ellas se declara junto, y así lo suman los dos
    esquematrones oficiales en BR-{X}-08, por categoría y sin mirar el tipo.
    Empezó por O, donde la norma prohíbe declarar tipo: si las líneas venían
    sin él y el desglose traía un `0.0000`, caían en cubos distintos y una
    factura correcta salía con tres quejas que se contradecían entre sí. Pasaba
    lo mismo, en pequeño, con una línea exenta que trae un 5% escrito: quedaba
    fuera de su entrada y salían la base descuadrada y la línea sin desglose,
    cuando el defecto es uno y ya lo dice BR-E-05. Desde el 14-09-2026 la
    excepción es la de la norma, las seis.
    """
    regla = REGLAS.get(categoria)
    if regla is not None and regla.desgloses == UNA_SOLA:
        return (categoria, None)
    return (categoria, tipo)


# Las tres categorías que la L4 de la Orden HAC/1028/2026 añade a la lista de
# la norma, con los nombres que les da la orden. Van **aparte** de
# `CATEGORIAS` a propósito: aquélla es la lista de la norma, la que da el «Las
# admitidas son…» de IVA-CATEGORIA-RARA, y meterlas ahí las daría por buenas en
# cualquier factura. Aquí solo sirven para nombrarlas. Sin ellas, el mismo
# informe que en SPFE-CATEGORIA decía que la orden admite la N la llamaba en
# BR-CO-17 «N (categoría no reconocida)»: lo vio la revisión del 07-10-2026,
# antes de publicar.
CATEGORIAS_DE_LA_ORDEN: dict[str, str] = {
    "N": "regímenes nacionales de IVA, de la L4 de la orden",
    "D": "agencias de viajes, de la L4 de la orden",
    "F": "bienes usados, de la L4 de la orden",
}


def nombre_categoria(codigo: str | None) -> str:
    if not codigo:
        return "sin categoría"
    nombre = CATEGORIAS.get(codigo) or CATEGORIAS_DE_LA_ORDEN.get(codigo)
    return f"{codigo} ({nombre or 'categoría no reconocida'})"


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
        return _clave(self.categoria, self.tipo)

    def __str__(self) -> str:
        return f"{nombre_categoria(self.categoria)} al {cifras.tipo(self.tipo)}"


@dataclass(frozen=True)
class Apunte:
    """Algo que entra en la base de una categoría: una línea o un cargo.

    Los descuentos entran con importe negativo, que es lo que los hace restar
    sin necesidad de tratarlos aparte.

    El importe puede faltar. Antes, una línea o un cargo sin importe no llegaba
    aquí —«de eso ya se queja BR-24»—, y con ello desaparecía también su
    categoría y su tipo: una línea al tipo general con un 0% escrito y sin
    importe no le daba a BR-S-05 nada que mirar. La norma mira el tipo aunque
    falte el importe, y las pruebas oficiales lo prueban justo así. Quien suma
    se salta los que no tienen; quien mira la categoría, no.

    `es_ajuste` distingue el cargo o descuento de la línea normal. Es un campo
    y no una lectura de `descripcion` a propósito: la descripción es texto
    para el usuario, y colgar de ella una decisión de negocio significa que el
    día que alguien la reescriba, la lógica cambia sin que nadie se entere.
    """

    descripcion: str
    importe: Decimal | None
    categoria: str | None
    tipo: Decimal | None
    es_ajuste: bool = False
    es_cargo: bool = False

    @property
    def clave(self) -> tuple[str | None, Decimal | None]:
        return _clave(self.categoria, self.tipo)


# Lo que Facturae escribe donde EN 16931 espera una categoría, y a qué
# categoría corresponde cuando corresponde a alguna.
#
# `TaxTypeCode` contesta a otra pregunta: **qué impuesto es**, no de qué
# categoría UNCL5305. Aun así, tres de sus valores fijan la categoría sin
# ambigüedad, porque la norma tiene una familia de reglas para cada uno:
# el IGIC canario es AF —$VATIG en el esquematrón— y el IPSI de Ceuta y
# Melilla es AG. Comprobado ahí, no deducido por analogía: la primera versión
# de esto se inventó «IG» e «IP» y una factura canaria recibía una regla
# «BR-IG-5» que no existe en ninguna norma.
_IMPUESTO_DE_FACTURAE = {
    "01": "S",   # IVA
    "03": "L",   # IGIC  -> BR-AF-*
    "02": "M",   # IPSI  -> BR-AG-*
}


# Los dos únicos valores de `SpecialTaxableEventCode` en Facturae 3.2.2, y a
# qué categoría de UNCL5305 corresponde cada uno. No hay más: el esquema los
# enumera y son estos dos.
_FISCALIDAD_ESPECIAL = {"01": "E", "02": "O"}


def _categoria_de_las_lineas(raiz, sintaxis: Sintaxis) -> str | None:
    """Lo que las líneas a tipo cero dicen de sí mismas, si lo dicen todas.

    Facturae sí tiene dónde escribir media respuesta a esto, y aquí se afirmó
    lo contrario durante semanas sin haber ido a mirar el esquema. Cada línea
    puede llevar `SpecialTaxableEvent/SpecialTaxableEventCode`, con dos
    valores: `01` operación sujeta y exenta, que es la **E**, y `02` operación
    no sujeta, que es la **O**.

    **Contesta solo cuando no hay nada que suponer**, y son tres condiciones a
    la vez: que haya líneas a tipo cero, que **todas** traigan el código, y que
    todas digan **lo mismo**. Si una sola calla, su cero puede ser una Z, una K
    o una G, y atribuirle la categoría de sus vecinas sería exactamente el
    dedazo que este validador no da. Con una sola línea muda se devuelve None y
    vuelve a salir `IVA-CATEGORIA-A-CERO`.
    """
    if sintaxis.linea_fiscalidad_especial == SIN_MAPA:
        return None
    codigos = []
    for linea in raiz.xpath(sintaxis.lineas, namespaces=sintaxis.espacios):
        tipo = importe(linea, sintaxis.linea_tipo, sintaxis)
        if tipo is None or tipo != 0:
            continue
        codigos.append(
            texto(linea, sintaxis.linea_fiscalidad_especial, sintaxis))
    if not codigos or None in codigos or len(set(codigos)) != 1:
        return None
    return _FISCALIDAD_ESPECIAL.get(codigos[0])


def _derivar_categoria(
    escrito: str | None,
    tipo: Decimal | None,
    de_las_lineas: str | None = None,
) -> str | None:
    """La categoría de IVA de una entrada de Facturae, cuando se puede saber.

    Se puede con IVA a tipo positivo: eso es «operación sujeta y no exenta»,
    que es la S, y no hay otra lectura. Con IGIC y con IPSI se puede siempre,
    porque el impuesto ya identifica la familia de reglas.

    **A tipo cero depende de lo que digan las líneas.** Un cero en Facturae
    puede ser una exenta del artículo 20, una no sujeta, una intracomunitaria,
    una exportación o una inversión del sujeto pasivo —Z, E, O, K, G o AE—. El
    `TaxTypeCode` del desglose no lo distingue, pero la línea puede traer
    `SpecialTaxableEvent`, y cuando lo traen todas y coinciden, `de_las_lineas`
    llega con la E o la O leídas del documento. Cuando no, se devuelve None a
    propósito y de eso avisa `IVA-CATEGORIA-A-CERO`, una vez y como nota:
    elegir la más probable y presentarla como leída es lo que este validador
    no hace.
    """
    familia = _IMPUESTO_DE_FACTURAE.get((escrito or "").strip())
    if familia is None:
        return None      # 04 IRPF, 05 otro… no son IVA ni se les parecen
    if familia != "S":
        return familia   # IGIC e IPSI no dependen del tipo
    if tipo is not None and tipo > 0:
        return "S"
    return de_las_lineas


def _categoria(
    nodo,
    ruta: str,
    sintaxis: Sintaxis,
    tipo: Decimal | None,
    de_las_lineas: str | None = None,
):
    """Lo que dice la sintaxis, traducido si esta sintaxis necesita traducción."""
    escrito = texto(nodo, ruta, sintaxis)
    if sintaxis.categoria_derivada == "facturae":
        return _derivar_categoria(escrito, tipo, de_las_lineas)
    return escrito


def _leer_grupos(raiz, sintaxis: Sintaxis) -> list[Grupo]:
    # Se lee una vez y no una por grupo: la fiscalidad especial es una
    # propiedad de las líneas del documento, no de cada entrada del desglose.
    de_las_lineas = _categoria_de_las_lineas(raiz, sintaxis)
    grupos = []
    for nodo in raiz.xpath(sintaxis.desglose, namespaces=sintaxis.espacios):
        motivo = texto(nodo, sintaxis.desglose_motivo, sintaxis) or texto(
            nodo, sintaxis.desglose_motivo_codigo, sintaxis
        )
        tipo = importe(nodo, sintaxis.desglose_tipo, sintaxis)
        grupos.append(
            Grupo(
                categoria=_categoria(
                    nodo, sintaxis.desglose_categoria, sintaxis, tipo,
                    de_las_lineas),
                tipo=tipo,
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
        identificador = texto(nodo, sintaxis.linea_id, sintaxis) or str(indice)
        tipo = importe(nodo, sintaxis.linea_tipo, sintaxis)
        apuntes.append(
            Apunte(
                descripcion=f"línea {identificador}",
                importe=cantidad,
                categoria=_categoria(
                    nodo, sintaxis.linea_categoria, sintaxis, tipo),
                tipo=tipo,
            )
        )

    for indice, nodo in enumerate(
        raiz.xpath(sintaxis.cargos, namespaces=sintaxis.espacios), start=1
    ):
        cantidad = importe(nodo, sintaxis.cargo_importe, sintaxis)
        marca = (texto(nodo, sintaxis.cargo_es_cargo, sintaxis) or "").lower()
        es_cargo = marca in sintaxis.marcas_de_cargo
        if cantidad is not None and not es_cargo:
            cantidad = -cantidad
        apuntes.append(
            Apunte(
                descripcion=("cargo" if es_cargo else "descuento") + f" {indice}",
                importe=cantidad,
                categoria=texto(nodo, sintaxis.cargo_categoria, sintaxis),
                tipo=importe(nodo, sintaxis.cargo_tipo, sintaxis),
                es_ajuste=True,
                es_cargo=es_cargo,
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
    if cuadra_exacto(suma, declarado):
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
                f"{cifras.calculada(redondear(suma))} (suma de "
                + (
                    "la única entrada"
                    if len(con_cuota) == 1
                    else f"las {len(con_cuota)} entradas"
                )
                + " del desglose)"
            ),
            encontrado=cifras.tiene(declarado),
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
    # Detallado quiere decir con su importe: un bloque de descuento sin importe
    # no dice cuánto va a cada tipo, que es lo que aquí hace falta saber.
    return declarados and not any(
        a.es_ajuste and a.importe is not None for a in apuntes)


def _ajustes_no_cuadran(raiz, sintaxis: Sintaxis, apuntes: list[Apunte]) -> bool:
    """Los ajustes vienen detallados, pero no suman lo que declara la factura.

    Entonces tampoco son de fiar para repartir la base por tipos: no se sabe
    cuál de las dos cifras es la buena. Aquí no se dice nada porque ya lo dicen
    BR-CO-11 y BR-CO-12 desde `en16931`, y lo dicen señalando el campo que está
    mal. Comprobar además la base por tipo sacaría una segunda queja apuntando
    al desglose, que es donde no está el problema.

    **Se compara igual que la regla a la que cede el paso**, con
    `cuadra_exacto`. Es lo que hace `en16931._reglas_ajustes` desde el
    13-09-2026, y este guardián se quedó con el margen de un céntimo de antes.
    El hueco entre los dos márgenes era justo de un céntimo, y ahí volvía a
    pasar lo que esto existe para evitar: medido el 22-09-2026 con un cargo de
    10,00 declarado como 10,01, salían `BR-CO-12` señalando el total de cargos
    —correcto— y además `IVA-BASE-TOLERADA` señalando el desglose, que es
    donde no está el problema. Dos quejas por el mismo céntimo, y la segunda
    manda a mirar donde no hay nada que arreglar.
    """
    detallados = [a for a in apuntes if a.es_ajuste and a.importe is not None]
    if not detallados:
        return False
    descuentos = sum((-a.importe for a in detallados if a.importe < 0), Decimal(0))
    cargos = sum((a.importe for a in detallados if a.importe > 0), Decimal(0))
    declarado_descuentos = importe(raiz, sintaxis.descuentos_total, sintaxis)
    declarado_cargos = importe(raiz, sintaxis.cargos_total, sintaxis)
    return (
        declarado_descuentos is not None
        and not cuadra_exacto(descuentos, declarado_descuentos)
    ) or (
        declarado_cargos is not None
        and not cuadra_exacto(cargos, declarado_cargos)
    )


def _regla_base_por_grupo(
    grupo: Grupo, apuntes: list[Apunte], sintaxis: Sintaxis
) -> list[Incidencia]:
    """BR-{X}-08: la base de cada entrada del desglose es la suma de lo suyo.

    Exacta, redondeada a dos decimales, o a menos de una unidad: depende de la
    categoría y de la sintaxis, porque así lo escribe el esquematrón oficial de
    cada una (`Sintaxis.base_admite_una_unidad`). Lo que se admite por el
    margen no se calla: sale como IVA-BASE-TOLERADA, un aviso, porque a
    diferencia de la cuota aquí no hay redondeo que lo explique. Una base es
    una suma de importes de dos decimales, y si no cuadra al céntimo es que
    algo no está donde dice.
    """
    if grupo.base is None or grupo.categoria is None:
        return []
    regla = REGLAS.get(grupo.categoria)
    codigo = f"BR-{regla.codigo}-08" if regla else "IVA-BASE"
    suyos = [a for a in apuntes if a.clave == grupo.clave]
    if any(a.importe is None for a in suyos):
        # Con un concepto sin importe la suma no se puede hacer, y de ese
        # concepto ya se queja su regla —BR-24 la línea, BR-31 y BR-36 el
        # descuento y el cargo—. Sumar lo que hay acusaría a la base de un
        # descuadre que no es suyo.
        return []

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
                encontrado=f"{cifras.tiene(grupo.base)} sin nada detrás",
            )
        ]

    suma = sum((a.importe for a in suyos), Decimal(0))
    if cuadra_exacto(suma, grupo.base):
        return []
    # Lo que se escribe es lo que se comparó, `redondear(suma)`, y no la
    # suma con `:.2f`: ver BR-CO-10 en `en16931`. Y lo que se aparta, de
    # esa misma cifra, o una base de 100.00 contra 100.005 diría que se
    # aparta 0.00.
    debida = redondear(suma)
    de_que = ", ".join(a.descripcion for a in suyos)
    if (grupo.categoria in sintaxis.base_admite_una_unidad
            and abs(grupo.base - suma) < 1):
        return [
            Incidencia(
                "IVA-BASE-TOLERADA",
                AVISO,
                f"La base declarada para {grupo} se aparta "
                f"{cifras.calculada(abs(grupo.base - debida))} de la suma de "
                "lo que va a ese "
                f"tipo. El esquematrón oficial de {sintaxis.nombre} lo deja "
                "pasar porque es menos de una unidad, y por eso no es un "
                f"error de {codigo}; pero una base es una suma y no tiene "
                "redondeo que la explique, así que algo no está donde dice.",
                campo=f"Base imponible de {grupo}",
                esperado=f"{cifras.calculada(debida)} ({de_que})",
                encontrado=cifras.tiene(grupo.base),
            )
        ]
    return [
        Incidencia(
            codigo,
            ERROR,
            f"La base declarada para {grupo} no coincide con la suma de lo que "
            "va a ese tipo.",
            campo=f"Base imponible de {grupo}",
            esperado=f"{cifras.calculada(debida)} ({de_que})",
            encontrado=cifras.tiene(grupo.base),
        )
    ]


def _cuota_esperada(calculada: Decimal, grupo: Grupo) -> str:
    """«21,03 (100,12 x 21%)»: la cuota que sale y la cuenta que la da.

    La base va como está en el fichero, sin redondear, para que la cuenta se
    pueda rehacer a mano; ver `cifras`.
    """
    return (
        f"{cifras.calculada(calculada)} "
        f"({cifras.en_castellano(grupo.base)} x {cifras.tipo(grupo.tipo)})"
    )


def _regla_cuota_por_grupo(grupo: Grupo, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-CO-17: cuota = base x tipo / 100, con el margen que da la norma.

    El margen no es un céntimo, que es lo que se aplicó aquí durante meses: es
    **una unidad**. El redondeo línea a línea aparta legítimamente la cuota de
    la base por el tipo, y el esquematrón oficial lo admite. Con el céntimo,
    este validador rechazaba facturas que la norma acepta; lo cazaron las
    pruebas oficiales de CII el 13-09-2026, que prueban justo el borde.

    Lo que la norma acepta y aquí no cuadra al céntimo no se calla: sale como
    `IVA-CUOTA-REDONDEO`, una nota que dice cuánto se aparta y con qué base se
    ha dado por buena.

    A tipo cero —o uno que redondeado a entero da cero— la norma no mira la
    base: pide que la cuota, redondeada a entero, sea cero.
    """
    if grupo.cuota is None:
        return []
    if grupo.tipo is None or redondear(grupo.tipo, 0) == 0:
        if redondear(grupo.cuota, 0) == 0:
            return []
        return [
            Incidencia(
                "BR-CO-17",
                ERROR,
                f"La entrada {grupo} va a tipo cero y declara cuota. A tipo "
                "cero la cuota tiene que ser cero.",
                campo=f"Cuota de {grupo}",
                esperado="0,00",
                encontrado=cifras.tiene(grupo.cuota),
            )
        ]
    if grupo.base is None:
        return []
    # Como el esquematrón: se redondea la base **en valor absoluto** por el
    # tipo, y el signo se pone después. Redondear con el signo lleva las
    # mitades hacia el otro lado en un abono —-13,775 da -13,77 y no -13,78—,
    # y en el borde de la unidad eso decide.
    exacta = abs(grupo.base) * grupo.tipo / Decimal(100)
    calculada = redondear(exacta) * (-1 if grupo.base < 0 else 1)
    distancia = abs(redondear(exacta) - abs(grupo.cuota))
    admitida = a_menos_de_una_unidad(exacta, grupo.cuota) or (
        sintaxis.cuota_admite_la_unidad_justa and distancia == 1)
    if admitida:
        if cuadra(calculada, grupo.cuota):
            return []
        return [
            Incidencia(
                "IVA-CUOTA-REDONDEO",
                NOTA,
                f"La cuota de {grupo} se aparta {cifras.calculada(distancia)} "
                "de aplicar el tipo a la base. La norma lo admite (hasta una "
                "unidad, por el redondeo línea a línea) y se ha dado por "
                "buena. Si no hay "
                "redondeo por líneas que lo explique, conviene revisarla.",
                campo=f"Cuota de {grupo}",
                esperado=_cuota_esperada(calculada, grupo),
                encontrado=cifras.tiene(grupo.cuota),
            )
        ]
    return [
        Incidencia(
            "BR-CO-17",
            ERROR,
            f"La cuota de IVA de {grupo} no sale de aplicar el tipo a la base.",
            campo=f"Cuota de {grupo}",
            esperado=_cuota_esperada(calculada, grupo),
            encontrado=cifras.tiene(grupo.cuota),
        )
    ]


def _regla_cuota_de_la_categoria(
    grupo: Grupo, sintaxis: Sintaxis
) -> list[Incidencia]:
    """BR-{X}-09: la cuota que corresponde a cada categoría.

    Son dos reglas con el mismo número. En las seis categorías sin impuesto
    —Z, E, AE, K, G y O— la cuota es **cero exacto**, y eso no lo dice
    BR-CO-17: a tipo cero aquella redondea a entero y deja pasar 0,40. En las
    tres con impuesto —S, L y M— es la cuenta de BR-CO-17 otra vez, con menos
    de una unidad de margen, y no en todas las sintaxis: el esquematrón de CII
    la da por duplicada en el IGIC y el IPSI y no la evalúa
    (`Sintaxis.comprueba_la_cuota_por_tipo`).

    Sin cuota, sin base o sin tipo no se calcula nada: de que falten ya se
    quejan BR-45, BR-46 y BR-48.
    """
    regla = REGLAS.get(grupo.categoria)
    if regla is None or grupo.cuota is None:
        return []
    codigo = f"BR-{regla.codigo}-09"
    if regla.tipo in (CERO, SIN_TIPO):
        if grupo.cuota == 0:
            return []
        return [
            Incidencia(
                codigo,
                ERROR,
                f"La entrada {grupo} declara cuota, y en "
                f"{nombre_categoria(grupo.categoria)} no hay impuesto que "
                "repercutir: la cuota tiene que ser cero, sin redondeo.",
                campo=f"Cuota de {grupo}",
                esperado="0,00",
                encontrado=cifras.tiene(grupo.cuota),
            )
        ]
    if grupo.categoria not in sintaxis.comprueba_la_cuota_por_tipo:
        return []
    if grupo.base is None or grupo.tipo is None:
        return []
    # La misma cuenta que BR-CO-17 y el mismo redondeo, sobre el valor
    # absoluto. Lo único distinto es el borde: aquí `<` en las dos sintaxis.
    exacta = abs(grupo.base) * grupo.tipo / Decimal(100)
    if abs(redondear(exacta) - abs(grupo.cuota)) < 1:
        return []
    calculada = redondear(exacta) * (-1 if grupo.base < 0 else 1)
    return [
        Incidencia(
            codigo,
            ERROR,
            f"La cuota de {grupo} se aparta una unidad o más de aplicar el "
            "tipo a la base.",
            campo=f"Cuota de {grupo}",
            esperado=_cuota_esperada(calculada, grupo),
            encontrado=cifras.tiene(grupo.cuota),
        )
    ]


def _reglas_cuota(grupo: Grupo, sintaxis: Sintaxis) -> list[Incidencia]:
    """BR-CO-17 y BR-{X}-09 sobre una entrada, dichas juntas.

    Juntas por un borde. En CII, una cuota a exactamente una unidad pasa
    BR-CO-17, que escribe `<=`, y no pasa BR-S-09, que escribe `<`. Por
    separado saldrían la nota «la norma lo admite» y el error «la norma no lo
    admite» sobre la misma cifra. Cuando BR-{X}-09 falla, la nota se retira:
    el error ya lo dice, y lo dice bien.
    """
    de_la_categoria = _regla_cuota_de_la_categoria(grupo, sintaxis)
    de_la_cuota = _regla_cuota_por_grupo(grupo, sintaxis)
    if de_la_categoria:
        de_la_cuota = [i for i in de_la_cuota if i.codigo != "IVA-CUOTA-REDONDEO"]
    return de_la_cuota + de_la_categoria


# --- Los identificadores fiscales de cada categoría (BR-{X}-02 a 04) ----------

# Qué identificadores sirven, por quién. Cada categoría exige una lista de
# requisitos y cada requisito se cumple con cualquiera de sus campos. Sale del
# texto de cada regla en la vinculación oficial de UBL, y `test_norma_oficial`
# lo compara con ese texto.
_VENDEDOR_CUALQUIERA = (
    "vendedor",
    ("vendedor_nif", "vendedor_registro_fiscal", "representante_nif"),
    "su identificador de IVA (BT-31), otro identificador fiscal suyo (BT-32) "
    "o el de IVA de su representante fiscal (BT-63)",
)
_VENDEDOR_IVA = (
    "vendedor",
    ("vendedor_nif", "representante_nif"),
    "su identificador de IVA (BT-31) o el de su representante fiscal (BT-63)",
)
_COMPRADOR_CUALQUIERA = (
    "comprador",
    ("comprador_nif", "comprador_registro"),
    "su identificador de IVA (BT-48) o su registro legal (BT-47)",
)
_COMPRADOR_IVA = (
    "comprador",
    ("comprador_nif",),
    "su identificador de IVA (BT-48)",
)
IDENTIFICADORES_EXIGIDOS: dict[str, tuple[tuple[str, tuple[str, ...], str], ...]] = {
    "S": (_VENDEDOR_CUALQUIERA,),
    "Z": (_VENDEDOR_CUALQUIERA,),
    "E": (_VENDEDOR_CUALQUIERA,),
    "L": (_VENDEDOR_CUALQUIERA,),
    "M": (_VENDEDOR_CUALQUIERA,),
    "AE": (_VENDEDOR_CUALQUIERA, _COMPRADOR_CUALQUIERA),
    "K": (_VENDEDOR_IVA, _COMPRADOR_IVA),
    "G": (_VENDEDOR_IVA,),
}
# La no sujeta es la única que prohíbe: ni el de IVA del vendedor, ni el de su
# representante, ni el del comprador. Lo que no está sujeto no tiene a quién
# identificar ante el IVA.
IDENTIFICADORES_PROHIBIDOS: dict[str, tuple[str, ...]] = {
    "O": ("vendedor_nif", "representante_nif", "comprador_nif"),
}
_NOMBRE_DEL_IDENTIFICADOR = {
    "vendedor_nif": "el de IVA del vendedor (BT-31)",
    "representante_nif": "el de IVA de su representante fiscal (BT-63)",
    "comprador_nif": "el de IVA del comprador (BT-48)",
}


def _esta(raiz, ruta: str, sintaxis: Sintaxis) -> bool | None:
    """Si el documento trae el elemento; None si la sintaxis no tiene dónde.

    Tres valores y no dos, a propósito. Un identificador que la sintaxis no
    distingue no está ausente: no se sabe. Con dos valores, «no se sabe» se
    convertía en «no está», y la regla acusaba a Facturae de algo que no puede
    escribir; o en «está», y la no sujeta la acusaba de lo contrario.
    """
    if ruta == SIN_MAPA:
        return None
    return bool(raiz.xpath(ruta, namespaces=sintaxis.espacios))


def _alguno(valores: list[bool | None]) -> bool | None:
    if True in valores:
        return True
    return None if None in valores else False


# La segunda cifra del código según de qué cuelgue la categoría. Se escribe
# como una cifra y no como «02» para que el código salga de `f"BR-…-0{cifra}"`,
# un patrón que `codigos.py` reconoce como suyo y no confunde con el de 05 a 07.
_DE_QUE_CUELGA = {
    "2": ("una línea", "líneas"),
    "3": ("un descuento de documento", "descuentos de documento"),
    "4": ("un cargo de documento", "cargos de documento"),
}


def _cifra_de_identificadores(apunte: Apunte) -> str:
    if not apunte.es_ajuste:
        return "2"
    return "4" if apunte.es_cargo else "3"


def _regla_identificadores(
    raiz, sintaxis: Sintaxis, apuntes: list[Apunte],
    comprador_registro_de_mas: tuple[str, ...] = (),
) -> list[Incidencia]:
    """BR-{X}-02, 03 y 04: los identificadores que exige cada categoría.

    Si una línea (02), un descuento (03) o un cargo (04) usa una categoría, la
    factura tiene que identificar a quien la norma pide para ella. Una
    incidencia por categoría y por clase de concepto, que nombra los conceptos:
    cien líneas al tipo general sin NIF del vendedor son un defecto, no cien.

    Cuando lo que pide la regla depende de un campo que la sintaxis no
    distingue, la regla se calla: no se sabe si se cumple, y no se afirma
    ninguna de las dos cosas.

    `comprador_registro_de_mas` son otros sitios donde puede ir el registro del
    comprador (BT-47). Hoy, el de la orden de la solución pública: la fila BT-47
    de la Orden HAC/1028/2026 lo pone en un cac:PartyTaxScheme con «LOC» y el
    atributo «FC», y no en cac:PartyLegalEntity, que es donde lo escribe la
    vinculación de 2017. Hasta el 07-10-2026, una factura AE de la solución
    pública con el comprador escrito como la orden salía con BR-AE-02.
    """
    usos: dict[tuple[str, str], list[str]] = {}
    for apunte in apuntes:
        if apunte.categoria in REGLAS:
            clave = (apunte.categoria, _cifra_de_identificadores(apunte))
            usos.setdefault(clave, []).append(apunte.descripcion)
    if not usos:
        return []
    hay = {
        campo: _esta(raiz, getattr(sintaxis, campo), sintaxis)
        for campo in (
            "vendedor_nif", "vendedor_registro_fiscal", "representante_nif",
            "comprador_nif", "comprador_registro",
        )
    }
    hay["comprador_registro"] = _alguno(
        [hay["comprador_registro"]]
        + [_esta(raiz, ruta, sintaxis) for ruta in comprador_registro_de_mas])
    incidencias = []
    for (categoria, cifra), suyos in sorted(usos.items()):
        regla = REGLAS[categoria]
        uno, varios = _DE_QUE_CUELGA[cifra]
        conceptos = f"{uno if len(suyos) == 1 else varios} a {nombre_categoria(categoria)}"
        for quien, campos, cuales in IDENTIFICADORES_EXIGIDOS.get(categoria, ()):
            if _alguno([hay[c] for c in campos]) is not False:
                continue
            incidencias.append(
                Incidencia(
                    f"BR-{regla.codigo}-0{cifra}",
                    ERROR,
                    f"La factura tiene {conceptos} y no identifica fiscalmente "
                    f"al {quien}. La norma pide para esa categoría {cuales}.",
                    campo=f"Identificador fiscal del {quien}",
                    esperado=cuales,
                    encontrado="ninguno · " + ", ".join(suyos),
                )
            )
        prohibidos = IDENTIFICADORES_PROHIBIDOS.get(categoria, ())
        if prohibidos and None not in [hay[c] for c in prohibidos]:
            sobran = [_NOMBRE_DEL_IDENTIFICADOR[c] for c in prohibidos if hay[c]]
            if sobran:
                incidencias.append(
                    Incidencia(
                        f"BR-{regla.codigo}-0{cifra}",
                        ERROR,
                        f"La factura tiene {conceptos} y trae identificadores "
                        "de IVA que en esa categoría no pueden estar: "
                        f"{', '.join(sobran)}. Lo que no está sujeto no se "
                        "identifica ante el IVA.",
                        campo="Identificadores de IVA",
                        esperado="ninguno de IVA",
                        encontrado=", ".join(sobran),
                    )
                )
    return incidencias


def _reglas_campos_del_grupo(grupo: Grupo, sintaxis: Sintaxis) -> list[Incidencia]:
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

    if grupo.categoria is None and sintaxis.desglose_categoria != SIN_MAPA:
        # La segunda mitad de la condición separa dos cosas que se parecen y no
        # son iguales: que la factura no haya escrito la categoría, que es un
        # defecto suyo, y que la sintaxis no tenga dónde escribirla, que no lo
        # es. Facturae es el segundo caso —su `TaxTypeCode` dice qué impuesto
        # es, no de qué categoría UNCL5305— y sin esta comprobación BR-47
        # salía como error en todas las facturas de España. De ese hueco se
        # informa una vez, arriba, y como NOTA.
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
    # toca a la categoría lo miran las BR-{X}-05.
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
    """BR-{X}-05 y BR-{X}-10: el tipo y el motivo que pide cada categoría."""
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

    # El tipo del desglose no se mira aquí. La familia BR-{X}-05 es de la
    # **línea**, no de la entrada del desglose: en el esquematrón oficial
    # BR-O-05 cuelga de `$VATO_Line` y BR-S-05 de `$VATS_Line`. Está en
    # `_regla_tipo_de_los_conceptos`. Que el tipo del desglose no cuadre con
    # su categoría lo caza igual la aritmética, porque BR-CO-17 exige que la
    # cuota salga de aplicarlo a la base.

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
        if regla.tipo == NO_NEGATIVO:
            # IGIC e IPSI: no se les sugiere otra categoría. Qué categoría
            # europea le toca a una operación exenta de IGIC no lo dice el
            # esquematrón, y aquí no se va a inventar.
            mensaje = (
                f"Una operación a {nombre} no debe llevar motivo de exención: "
                "la norma europea no lo admite en esta categoría. Admite el "
                "tipo cero, que se declara como cero y sin motivo."
            )
        else:
            mensaje = (
                f"Una operación a {nombre} no debe llevar motivo de exención: "
                "esa categoría no es una exención, y el motivo es justamente "
                "lo que justifica una. Si la operación de verdad está exenta, "
                "la categoría es otra: E, AE, K o G según el caso."
            )
        incidencias.append(
            Incidencia(
                f"BR-{regla.codigo}-10",
                ERROR,
                mensaje,
                campo=f"Motivo de {nombre}",
                esperado="(sin motivo)",
                encontrado=grupo.motivo,
            )
        )

    return incidencias


def _regla_hay_desglose(
    grupos: list[Grupo], apuntes: list[Apunte]
) -> list[Incidencia]:
    """BR-{X}-01: cada categoría usada tiene que aparecer en el desglose.

    Y en las categorías que van a cero o sin tipo, **una sola vez**: dos
    entradas exentas en el desglose incumplen BR-E-01 aunque las líneas estén
    bien, porque la norma pide exactamente una. Eso se mira con conceptos o
    sin ellos: los dos esquematrones oficiales cuentan las entradas del
    desglose por su cuenta.
    """
    declaradas = {g.categoria for g in grupos if g.categoria}
    cuantas = Counter(g.categoria for g in grupos if g.categoria)
    incidencias = []
    for categoria in sorted(cuantas):
        regla = REGLAS.get(categoria)
        if regla is None or regla.desgloses != UNA_SOLA or cuantas[categoria] < 2:
            continue
        incidencias.append(
            Incidencia(
                f"BR-{regla.codigo}-01",
                ERROR,
                f"El desglose de IVA trae {cuantas[categoria]} entradas a "
                f"{nombre_categoria(categoria)}, y la norma pide una sola: "
                "todo lo que va a esa categoría se declara junto, con una base "
                "y un motivo.",
                campo="Desglose de IVA",
                esperado=f"una sola entrada para {categoria}",
                encontrado=f"{cuantas[categoria]} entradas",
            )
        )
    for categoria in sorted({a.categoria for a in apuntes if a.categoria}):
        if categoria in declaradas:
            continue
        regla = REGLAS.get(categoria)
        usados = [a.descripcion for a in apuntes if a.categoria == categoria]
        incidencias.append(
            Incidencia(
                # Sin `regla` la categoría no es ninguna de la norma, así que
                # no hay BR-{X}-01 que citar. `IVA-SIN-DESGLOSE` era un nombre
                # prestado y ahora confundiría con BR-CO-18, que es el que dice
                # que no hay desglose ninguno.
                f"BR-{regla.codigo}-01" if regla else "IVA-CATEGORIA-SIN-DESGLOSE",
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
        suma = sum((a.importe for a in apuntes
                    if a.clave == apunte.clave and a.importe is not None), Decimal(0))
        incidencias.append(
            Incidencia(
                "IVA-TIPO-SIN-DESGLOSE",
                ERROR,
                f"Hay {cifras.calculada(suma)} a "
                f"{nombre_categoria(apunte.categoria)} al "
                f"{cifras.tipo(apunte.tipo)}, pero el desglose no trae ninguna "
                "entrada a ese tipo. El desglose va por categoría y tipo, no "
                "solo por categoría.",
                campo="Desglose de IVA",
                esperado=f"una entrada al {cifras.tipo(apunte.tipo)}",
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


# Qué código sale según de qué cuelgue lo que no es no sujeto. Tabla de filas y
# no diccionario: `codigos.py` lee los códigos de las filas de una tabla que
# recorre un `for`, y no de una búsqueda por clave.
_NO_SUJETA_CON_OTRAS = (
    ("2", "BR-O-12"),
    ("3", "BR-O-13"),
    ("4", "BR-O-14"),
)


def _regla_no_sujeta_sin_otras(
    grupos: list[Grupo], apuntes: list[Apunte]
) -> list[Incidencia]:
    """BR-O-12, 13 y 14: con desglose no sujeto, ningún concepto de otra categoría.

    BR-O-11 lo mira en el desglose; estas tres en lo que lo alimenta. Un
    concepto sin categoría no cuenta, como en el esquematrón, que pregunta por
    los que dicen una distinta de O: sin categoría no dice ninguna, y de eso
    se quejan BR-CO-04 y las de su familia.
    """
    if not any(g.categoria == "O" for g in grupos):
        return []
    otros: dict[str, list[str]] = {}
    for apunte in apuntes:
        if apunte.categoria and apunte.categoria != "O":
            cifra = _cifra_de_identificadores(apunte)
            otros.setdefault(cifra, []).append(
                f"{apunte.descripcion} ({apunte.categoria})")
    incidencias = []
    for cifra, codigo in _NO_SUJETA_CON_OTRAS:
        suyos = otros.get(cifra)
        if not suyos:
            continue
        incidencias.append(
            Incidencia(
                codigo,
                ERROR,
                "El desglose declara operaciones no sujetas y la factura trae "
                f"{_DE_QUE_CUELGA[cifra][1]} de otra categoría. Con lo no sujeto "
                "no puede ir nada más: va en factura aparte.",
                campo="Categoría de IVA",
                esperado="O en todo",
                encontrado=", ".join(suyos),
            )
        )
    return incidencias


def _regla_intracomunitaria(raiz, sintaxis: Sintaxis, grupos: list[Grupo]) -> list[Incidencia]:
    """BR-IC-11 y 12: una entrega intracomunitaria dice cuándo y adónde.

    La exención de estas entregas se sostiene en que la mercancía sale hacia
    otro Estado miembro; la factura tiene que decir en qué fecha —la de
    entrega o el periodo facturado— y a qué país. El esquematrón de UBL pide
    más de un carácter en la fecha y en el país; aquí se pide lo mismo.

    Con tres valores, como los identificadores: lo que la sintaxis no tiene
    dónde escribir no se reclama.
    """
    if not any(g.categoria == "K" for g in grupos):
        return []

    def escrito(ruta: str) -> bool | None:
        # Como el esquematrón: `string-length(...) > 1`, sobre el texto del
        # elemento. Un elemento que solo lleva un comentario está vacío; las
        # pruebas oficiales traen justo ese caso, y contando hijos de lxml
        # —que cuenta el comentario como hijo— salía escrito.
        if ruta == SIN_MAPA:
            return None
        return any(len(n.xpath("string()") if not isinstance(n, str) else n) > 1
                   for n in raiz.xpath(ruta, namespaces=sintaxis.espacios))

    def hay(ruta: str) -> bool | None:
        # El periodo no se mide: basta con que tenga alguna fecha dentro.
        if ruta == SIN_MAPA:
            return None
        return bool(raiz.xpath(ruta, namespaces=sintaxis.espacios))

    incidencias = []
    if _alguno([escrito(sintaxis.fecha_entrega), hay(sintaxis.periodo)]) is False:
        incidencias.append(
            Incidencia(
                "BR-IC-11",
                ERROR,
                "La factura declara una entrega intracomunitaria y no dice "
                "cuándo: ni la fecha de entrega ni el periodo facturado.",
                campo="Fecha de entrega o periodo de facturación",
                esperado="la fecha de entrega (BT-72) o el periodo (BG-14)",
                encontrado="(ninguno)",
            )
        )
    if escrito(sintaxis.pais_entrega) is False:
        incidencias.append(
            Incidencia(
                "BR-IC-12",
                ERROR,
                "La factura declara una entrega intracomunitaria y no dice a "
                "qué país se entrega.",
                campo="País de entrega",
                esperado="el código de país de la dirección de entrega (BT-80)",
                encontrado="(falta)",
            )
        )
    return incidencias


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
                f"{cifras.tipo(grupo.tipo)} no es un tipo de IVA vigente en "
                "España. Es legal si la operación tributa en otro país, pero "
                "si no, es un dedo torcido.",
                campo=f"Tipo de {nombre_categoria(grupo.categoria)}",
                esperado="21%, 10%, 4% o 0%",
                encontrado=cifras.tiene(grupo.tipo),
            )
        )
    return incidencias


def _sufijo_del_concepto(apunte: Apunte) -> str:
    """Qué número de regla le toca a cada clase de concepto.

    La norma parte la misma comprobación en tres según de qué cuelgue: BR-{X}-05
    para la línea, BR-{X}-06 para el descuento de documento y BR-{X}-07 para el
    cargo de documento.

    Con dos cifras, que es como los escribe la norma y como sale en el
    rechazo de cualquier otro validador. Aquí se escribieron durante un
    tiempo con una —`BR-S-5`, `BR-O-8`—, y quien copiaba el código de ese
    rechazo para buscarlo en la página de incidencias no encontraba nada.
    """
    if not apunte.es_ajuste:
        return "05"
    return "07" if apunte.es_cargo else "06"


def _regla_tipo_de_los_conceptos(apuntes: list[Apunte]) -> list[Incidencia]:
    """BR-{X}-05, BR-{X}-06 y BR-{X}-07: el tipo que le toca a cada concepto.

    Estas reglas son de la línea, del descuento o del cargo; no del desglose.
    Se comprobaban sobre la entrada del desglose, que casi siempre lleva el
    mismo tipo que sus líneas, y por eso el error nunca se notó. En la
    categoría O se separan —el desglose puede traer un `0.0000` que las líneas
    no llevan— y ahí salía una queja falsa contra una factura correcta.

    Se agrupa por regla y por tipo para no repetir la misma queja veinte veces
    en una factura de veinte líneas iguales.
    """
    fallos: dict[tuple[str, str, str, Decimal | None], list[str]] = {}
    for apunte in apuntes:
        regla = REGLAS.get(apunte.categoria) if apunte.categoria else None
        if regla is None:
            continue  # sin categoría o con una que no es de la norma: otros lo dicen
        # Que el tipo **falte** también es esto. Hasta el 11-10-2026 aquí ponía
        # `mal = False`, con un comentario que decía que la falta la cuenta
        # BR-48. BR-48 es del desglose y no de la línea: una línea exenta sin
        # tipo con su entrada del desglose a cero pasaba sin una queja. En el
        # esquematrón oficial, en las tres vinculaciones, estas reglas son una
        # comparación con el tipo, y sin tipo la comparación es falsa y la
        # regla salta. Solo la no sujeta va sin tipo, y ahí es al revés.
        # `test_norma_oficial` evalúa el texto de cada vinculación sobre un
        # concepto sin tipo y lo compara con esto.
        #
        # «Falta» es aquí lo mismo que en BR-48: que no haya un número que
        # leer. Un tipo escrito que no es un número lo denuncia además el XSD.
        if regla.tipo == SIN_TIPO:
            mal = apunte.tipo is not None
        elif apunte.tipo is None:
            mal = True
        elif regla.tipo == POSITIVO:
            mal = apunte.tipo <= 0
        elif regla.tipo == CERO:
            mal = apunte.tipo != 0
        elif regla.tipo == NO_NEGATIVO:
            mal = apunte.tipo < 0
        else:
            # Antes aquí ponía `mal = False`, y por esa puerta pasó el
            # `CUALQUIERA` del IGIC: un estado que no se queja de nada no
            # rompe nada y no se nota nunca. Un estado sin rama no se calla.
            raise ValueError(f"estado de tipo sin comprobación: {regla.tipo!r}")
        if mal:
            clave = (
                regla.codigo,
                _sufijo_del_concepto(apunte),
                apunte.categoria,
                apunte.tipo,
            )
            fallos.setdefault(clave, []).append(apunte.descripcion)

    incidencias = []
    for (codigo, sufijo, categoria, tipo), suyos in fallos.items():
        regla = REGLAS[categoria]
        nombre = nombre_categoria(categoria)
        if regla.tipo == SIN_TIPO:
            mensaje = (
                f"Hay conceptos a {nombre} que declaran tipo de IVA: si no "
                "está sujeta, no hay tipo que aplicar."
            )
            esperado = "(sin tipo)"
        elif tipo is None:
            esperado = _TIPO_QUE_PIDE[regla.tipo]
            mensaje = (
                f"Hay conceptos a {nombre} sin tipo de IVA. Solo lo no sujeto "
                "(categoría O) va sin tipo: en esta categoría la norma pide "
                f"{_LO_QUE_PIDE[regla.tipo]}, aunque el desglose ya lo diga."
            )
        elif regla.tipo == POSITIVO:
            mensaje = (
                f"Hay conceptos a {nombre} con un tipo que no es mayor que "
                "cero. Si de verdad no llevan impuesto, la categoría es otra: "
                "Z para tipo cero, E para exenta, O para no sujeta."
            )
            esperado = "mayor que 0"
        elif regla.tipo == NO_NEGATIVO:
            mensaje = (
                f"Hay conceptos a {nombre} con un tipo negativo. La norma "
                "admite el cero o un tipo positivo, nunca uno negativo: lo "
                "que se devuelve o se descuenta va con importe negativo, no "
                "con tipo negativo."
            )
            esperado = "0 o mayor que 0"
        else:
            mensaje = f"Hay conceptos a {nombre} cuyo tipo no está a cero."
            esperado = "0"
        incidencias.append(
            Incidencia(
                f"BR-{codigo}-{sufijo}",
                ERROR,
                mensaje,
                campo="Conceptos: " + ", ".join(suyos),
                esperado=esperado,
                encontrado="(sin tipo)" if tipo is None else cifras.tiene(tipo),
            )
        )
    return incidencias


# Lo que cada estado pide cuando el tipo falta: en «Debería» y en la frase.
_TIPO_QUE_PIDE = {POSITIVO: "mayor que 0", CERO: "0", NO_NEGATIVO: "0 o mayor que 0"}
_LO_QUE_PIDE = {POSITIVO: "un tipo mayor que cero", CERO: "el tipo, a cero",
                NO_NEGATIVO: "el tipo, a cero o positivo"}


def _regla_lineas_con_categoria(
    apuntes: list[Apunte], sintaxis: Sintaxis
) -> list[Incidencia]:
    """De la casa: sin categoría en la línea no hay desglose que comprobar."""
    if sintaxis.linea_categoria == SIN_MAPA:
        # Mismo motivo que en BR-47: si la sintaxis no tiene el campo, la
        # línea no está incompleta. Avisar aquí sería repetir con otro código
        # lo que la nota del desglose ya dice una sola vez.
        return []
    # Solo los que tienen importe: el aviso habla de que el desglose no se ha
    # podido cuadrar con ellos, y uno sin importe no entraba en ninguna cuenta.
    # Que toda línea lleve categoría, tenga importe o no, es BR-CO-04, que es
    # de la norma y va por su lado.
    huerfanos = [a.descripcion for a in apuntes
                 if not a.categoria and a.importe is not None]
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


def reglas(raiz, sintaxis: Sintaxis, espanola: bool = True,
           categorias_de_mas: frozenset[str] = frozenset(),
           comprador_registro_de_mas: tuple[str, ...] = ()) -> list[Incidencia]:
    """Todas las comprobaciones de IVA sobre un documento ya parseado.

    `espanola` dice si el documento está sujeto a la facturación española. Solo
    afecta a `IVA-TIPO`, que compara contra los tipos vigentes en España y no
    significa nada sobre una factura danesa. Por defecto sí, porque para eso
    existe esta herramienta y porque llamar a `reglas` sin decir nada no puede
    apagar comprobaciones en silencio.

    `categorias_de_mas` son categorías que el documento puede usar aunque la
    norma de 2017 no las tenga. Hoy, las de la L4 de la Orden HAC/1028/2026 en
    una factura de la solución pública: N, D y F. No son «raras» para esa
    factura, y sus tipos no son los de la tabla española —la N cubre el
    recargo de equivalencia, al 5,2%, al 1,4% o al 0,5%—, así que ni
    IVA-CATEGORIA-RARA ni IVA-TIPO dicen nada de ellas. Su base tampoco se
    compara con las líneas (IVA-BASE): el porqué, donde se salta. Lo que la
    edición de 2026 de la norma les pida no se comprueba, y la nota
    SPFE-CATEGORIA lo dice.

    `comprador_registro_de_mas`: ver `_regla_identificadores`.
    """
    grupos = _leer_grupos(raiz, sintaxis)
    apuntes = _leer_apuntes(raiz, sintaxis)

    if not grupos:
        # BR-CO-18: toda factura tiene que traer al menos un desglose. No es un
        # aviso ni depende de que se declare importe de impuestos: sin desglose
        # el receptor lo rechaza. Antes esto era un aviso propio y solo saltaba
        # si el IVA declarado no era cero, así que una factura sin desglose y
        # sin total pasaba en silencio.
        #
        # **Y no se para aquí.** Hasta el 13-09-2026 esta rama devolvía
        # BR-CO-18 y nada más, con la idea de que sin desglose no había nada
        # que comprobar. Sí lo hay: el tipo de cada línea, descuento y cargo
        # (BR-{X}-05 a 07) y que su categoría falte en el desglose
        # (BR-{X}-01) no dependen de que el desglose exista. Una línea al tipo
        # general con un 0% son dos defectos, y la norma dice los dos; aquí se
        # decía uno, y el segundo aparecía el día que se arreglaba el primero.
        moneda = texto(raiz, sintaxis.moneda, sintaxis)
        declarado = importe_en_moneda(raiz, sintaxis.impuestos, sintaxis, moneda)
        # Con el mismo `comprador_registro_de_mas` que la otra llamada. Sin
        # él, una AE de la solución pública sin desglose salía con BR-AE-02
        # por tener al comprador donde lo pone la orden: lo vio la revisión
        # del 07-10-2026, antes de publicar.
        return _regla_tipo_de_los_conceptos(apuntes) + _regla_identificadores(
            raiz, sintaxis, apuntes, comprador_registro_de_mas) + _regla_hay_desglose(
            grupos, apuntes) + [
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
                    else f"{cifras.tiene(declarado)} de IVA sin desglosar"
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
    # dice mejor (BR-CO-11 y BR-CO-12). En los dos casos se calla BR-{X}-08.
    a_ciegas = a_ciegas or _ajustes_no_cuadran(raiz, sintaxis, apuntes)

    for grupo in grupos:
        incidencias.extend(_reglas_campos_del_grupo(grupo, sintaxis))
        if grupo.categoria not in categorias_de_mas:
            incidencias.extend(_regla_forma_del_grupo(grupo))
        # La base de N, D y F no se compara con las líneas: la orden la desliga.
        # En la N, el grupo de entidades de nivel avanzado informa la base a
        # coste (BT-116) y en la línea la contraprestación entera (BT-131), y el
        # recargo de equivalencia no tiene línea propia que vaya a su tipo. En
        # la D y la F la base puede ser el margen, y la orden no dice si es
        # eso o el precio. Medido el 07-10-2026: las dos primeras daban
        # IVA-BASE en ERROR. Lo que sigue atando esas entradas es BR-CO-17, su
        # cuota con su base y su tipo, y BR-CO-14, la suma de las cuotas.
        if not a_ciegas and grupo.categoria not in categorias_de_mas:
            incidencias.extend(_regla_base_por_grupo(grupo, apuntes, sintaxis))
        incidencias.extend(_reglas_cuota(grupo, sintaxis))
    incidencias.extend(_regla_tipo_de_los_conceptos(apuntes))
    incidencias.extend(_regla_identificadores(
        raiz, sintaxis, apuntes, comprador_registro_de_mas))
    incidencias.extend(_regla_hay_desglose(grupos, apuntes))
    incidencias.extend(_regla_no_sujeta_a_solas(grupos))
    incidencias.extend(_regla_no_sujeta_sin_otras(grupos, apuntes))
    incidencias.extend(_regla_intracomunitaria(raiz, sintaxis, grupos))
    if espanola:
        # Sobre una factura extranjera este aviso no dice nada: el 25% danés y
        # el 19% alemán son sus tipos generales, no un dedazo. Sin esta
        # condición era 64 quejas en 50 de las 73 facturas europeas de
        # `muestras/` —el 70% de todo lo que decía el programa— y la señal útil
        # quedaba enterrada debajo.
        incidencias.extend(_regla_tipos_espanoles(
            [g for g in grupos if g.categoria not in categorias_de_mas]))
    if sintaxis.categoria_derivada:
        # Lo que la deducción no alcanza, dicho una vez y con su porqué. Es la
        # otra mitad de `_derivar_categoria` y de `_categoria_de_las_lineas`:
        # allí se explica cuándo el documento contesta y cuándo no, y aquí se
        # dice que esta vez no lo ha hecho.
        a_ciegas_por_cero = [
            g for g in grupos if g.categoria is None and g.tipo == 0
        ]
        if a_ciegas_por_cero:
            cuantas = len(a_ciegas_por_cero)
            incidencias.append(
                Incidencia(
                    "IVA-CATEGORIA-A-CERO",
                    NOTA,
                    f"{'Una entrada' if cuantas == 1 else f'{cuantas} entradas'} "
                    "del desglose van a tipo cero, y en "
                    f"{sintaxis.nombre} eso no dice cuál de las categorías de "
                    "EN 16931 es: exenta, no sujeta, intracomunitaria, "
                    "exportación o inversión del sujeto pasivo se escriben "
                    "todas igual. La línea puede aclarar parte con la "
                    "«fiscalidad especial», que separa la exenta de la no "
                    "sujeta, pero aquí no la traen todas o no dicen lo mismo. "
                    "Las reglas que dependen de la categoría no "
                    "se han comprobado ahí. El resto del IVA sí: las bases, "
                    "las cuotas y que el desglose cuadre.",
                    campo="Categoría de IVA",
                    encontrado="tipo 0 sin categoría que lo distinga",
                )
            )

    if sintaxis.desglose_categoria == SIN_MAPA:
        # Se declara una vez por documento, no una por entrada del desglose:
        # es una propiedad de la sintaxis, no de la factura, y repetirla por
        # cada tipo de IVA daría la impresión de que hay varios defectos.
        incidencias.append(
            Incidencia(
                "IVA-CATEGORIA-SIN-MAPA",
                NOTA,
                f"La sintaxis {sintaxis.nombre} no tiene categoría de IVA en "
                "el sentido de EN 16931 (la lista UNCL5305: general, exento, "
                "inversión del sujeto pasivo, no sujeto…), así que las reglas "
                "que dependen de ella no se han podido comprobar. El resto "
                "del IVA sí: las bases, las cuotas y que el desglose cuadre.",
                campo="Categoría de IVA",
                encontrado="(sin correspondencia en esta sintaxis)",
            )
        )
    incidencias.extend(_regla_lineas_con_categoria(apuntes, sintaxis))
    return incidencias
