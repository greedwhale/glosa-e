"""El orquestador: todas las reglas sobre el mismo documento, de una pasada.

Hay tres reglamentos en juego y ninguno se habla con los otros. `en16931` mira
lo que exige la norma europea sobre UBL y CII; `facturae` mira la aritmética
que el esquema del formato nacional escribe en sus propias anotaciones;
`codigo_unico` mira lo que exige el RD 238/2026 y que ningún validador europeo
comprueba. Quien recibe una factura las necesita todas a la vez y no le importa
de qué reglamento sale cada queja.

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

import re

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from lxml import etree

from validador import (
    cadena,
    codigo_unico,
    copia_fiel,
    cuentas_de_cobro,
    edifact,
    en16931,
    esquema,
    facturae,
    firma,
    mensajes,
    normas,
    revocacion,
    sellos,
    sintaxis,
    solucion_publica,
)
from validador.formato import (
    CII,
    EDIFACT,
    FACTURAE,
    FIRMA_EN_PIE,
    FIRMA_ROTA,
    RESPUESTA,
    UBL,
    Deteccion,
    detectar,
    entidades_sin_resolver,
    parser,
)
from validador.cadena import Almacen
from validador.revocacion import AlmacenDeListas
from validador.esquema import Catalogo
from validador.incidencias import (
    AVISO,
    ERROR,
    NOTA,
    Incidencia,
    Informe,
    familia_de,
)

# Familias que vienen escritas en XML y se parsean tal cual.
#
# **Una familia de XML que falte aquí no falla: absuelve.** `_arbol` devuelve
# entonces `raiz=None`, y sin árbol no se pasa ni el esquema ni la firma. Medido
# con una respuesta a la que le sobraba un elemento, y con otra firmada y
# tocada después de firmar: las dos salían «1 correcto(s)», sin errores y con
# código de salida 0, con la columna de la forma diciendo «Sin errores». Por eso
# `test_respuesta.py` recorre las familias de `formato.py` y no deja ninguna
# fuera de esta lista ni de EDIFACT.
_FAMILIAS_XML = (UBL, FACTURAE, CII, RESPUESTA)

# EDIFACT también acaba en un árbol, pero por dos caminos: si viene en XML
# —la forma de ISO 20625, que es la que publica la Comisión— se parsea como
# los demás, y si viene en tira se convierte antes. A partir de ahí las
# reglas no notan la diferencia, que es justamente la idea.

# La queja de la izquierda sobra cuando ya ha saltado alguna de la derecha:
# dicen lo mismo con las palabras de dos reglamentos distintos. Hasta el
# 14-09-2026 este comentario lo decía al revés —«la de la derecha sobra»— y
# la primera entrada que se escribió fiándose de él salió al revés también.
_SOBRA_SI: dict[str, tuple[str, ...]] = {
    "CU-00": ("BR-02", "BR-03"),
    "CU-02": ("BR-02",),
    # Esta no dice lo mismo que su nota: la nota dice que el cuadre no se puede
    # hacer. Con líneas de cobro, el anexo suma al total a pagar unos importes
    # que la edición de 2017 no conoce, y BR-CO-16 daba por mal una factura
    # hecha como manda el anexo. Medido el 14-09-2026 con un suplido.
    "BR-CO-16": ("SPFE-TOTAL-A-PAGAR",),
}

# De qué reglamento sale cada queja. Va en el informe, junto al código, porque
# cambia lo que hay que hacer con ella: lo que firma una norma te lo rechaza el
# receptor, lo que firmamos nosotros es una opinión que puedes discutir.
#
# La tabla está en `normas.py` y no aquí desde el 20-09-2026: la página del
# catálogo tenía su propia copia y las dos dejaron de decir lo mismo en 16
# códigos. Estos nombres se quedan porque los usan las pruebas y quien importe
# `factura`; el que ya no está es `OTRA`, el cajón de por defecto, que se leía
# «Formato» y se tragaba códigos que son de la casa.
EUROPEA = normas.EUROPEA
ESPANOLA = normas.ESPANOLA
SOLUCION_PUBLICA = normas.SOLUCION_PUBLICA
FORMA = normas.FORMA
NACIONAL = normas.NACIONAL
SELLO = normas.SELLO
SINTAXIS_EDI = normas.SINTAXIS_EDI
CASA = normas.CASA


def origen(incidencia: Incidencia) -> str:
    """A qué norma responde una incidencia."""
    return normas.norma(incidencia.codigo)[0]


def _arbol(datos: bytes, deteccion: Deteccion):
    """El documento parseado y lo que se haya visto al parsearlo.

    Devuelve el árbol —o None si no lo hay— y las quejas que salen de la
    lectura misma. Solo EDIFACT trae de las segundas: las cuentas del sobre
    (cuántos segmentos dice llevar el mensaje, cuántos mensajes el
    intercambio) se comprueban al partir la tira y no se pueden mirar después,
    porque el árbol ya no sabe cómo estaba escrito.
    """
    if not deteccion:
        return None, []
    if deteccion.familia == EDIFACT and edifact.es_plano(datos):
        return edifact.convertir(datos)
    if deteccion.familia not in _FAMILIAS_XML + (EDIFACT,):
        return None, []
    try:
        raiz = etree.fromstring(datos, parser=parser())
    except etree.XMLSyntaxError:
        # `detectar` ya lo parseó sin problemas, así que llegar aquí sería
        # raro. Aun así, mejor no reventar el lote entero por un fichero.
        return None, []
    return raiz, _entidades(raiz)


def _entidades(raiz) -> list[Incidencia]:
    """La queja de un documento que mete entidades XML en su contenido.

    Reproducido el 21-09-2026 con un Facturae con `<!ENTITY monto "1.00">`
    usado en un `TotalAmount`: el validador salía con **una sola** incidencia,
    `VALIDADOR-SE-ATRAGANTA`, porque `XMLSchema.validate` revienta con
    `Internal error in XML Schema validation` —en inglés, dentro del informe—
    en cuanto el árbol trae un nodo de referencia a entidad. Todo lo demás se
    callaba.

    Es error y no aviso, y no es una queja sobre este programa: el documento no
    dice un importe, dice un nombre que hay que ir a buscar a su propio
    prólogo. Quien lo reciba puede expandir la entidad o no —la norma XML deja
    al procesador no validante la opción de no hacerlo—, así que el mismo
    fichero se lee con dos importes distintos según quién lo abra. Una factura
    tiene que decir lo que dice sin depender de eso.
    """
    afectados = entidades_sin_resolver(raiz)
    if not afectados:
        return []
    return [
        Incidencia(
            "XML-ENTIDADES",
            ERROR,
            "El documento declara entidades XML en su prólogo y las usa en el "
            "contenido. Aquí no se expanden (un fichero de fuera no debe poder "
            "leer ficheros del servidor), así que esos campos se leen vacíos; "
            "y quien lo reciba puede expandirlas y leer otra cosa. Escribe los "
            "valores tal cual y quita el DOCTYPE. Mientras esté, la forma no "
            "se ha comprobado contra el esquema.",
            campo="Prólogo del XML",
            esperado="un documento sin DOCTYPE ni entidades",
            encontrado=", ".join(afectados[:6])
            + (f" y {len(afectados) - 6} más" if len(afectados) > 6 else ""),
        )
    ]


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


def _reglas(
    raiz,
    deteccion: Deteccion,
    hoy: date | None,
    catalogo: Catalogo | None,
    almacen: Almacen | None = None,
    listas: AlmacenDeListas | None = None,
    sintacticas: list[Incidencia] | None = None,
) -> tuple[list[Incidencia], str | None, int]:
    """Todas las reglas sobre un documento ya parseado y ya identificado.

    La forma va primero porque es lo primero que mira un receptor: si el
    documento no cumple el esquema, ni llega a leer los numeros.

    Devuelve además en qué quedó la firma, que no es una queja sino el estado
    del documento: lo pinta la línea de estado del informe. Y cuántas firmas se
    sostienen, que es lo que necesita la frase del final. Sale de los mismos
    exámenes con los que se escriben las glosas de la firma —una sola pasada, y
    sin que la línea pueda decir una cosa y las glosas otra.
    """
    # Las cuentas, con precisión de sobra: con la de `Decimal` por defecto un
    # importe de treinta cifras se llevaba el informe entero al redondear. Ver
    # `sintaxis.cuentas`.
    with sintaxis.cuentas():
        return _reglas_con_cuentas(
            raiz, deteccion, hoy, catalogo, almacen, listas, sintacticas
        )


def _reglas_con_cuentas(
    raiz, deteccion, hoy, catalogo, almacen, listas, sintacticas
) -> tuple[list[Incidencia], str | None, int]:
    # Una sola vez, y sirve para los dos bandos: el reglamento español no
    # aplica a una factura extranjera, y tampoco tiene sentido medirle los
    # tipos de IVA contra los que se usan aquí.
    espanola = codigo_unico.obligado_en_espania(raiz, deteccion)
    incidencias = list(sintacticas or [])
    incidencias.extend(esquema.reglas(raiz, deteccion, catalogo))
    # Lo que la orden admite y la vinculación de 2017 no conoce, si la factura
    # declara la solución pública: las categorías de su L4 que la lista de 2017
    # no tiene, y el sitio donde pone el registro del comprador (BT-47). Se
    # deciden aquí porque aquí se saben las dos cosas, y `en16931` no puede
    # preguntárselo a `solucion_publica`.
    incidencias.extend(en16931.reglas(
        raiz, deteccion, espanola=espanola,
        categorias_de_mas=solucion_publica.categorias_que_la_norma_no_tiene(raiz, deteccion),
        comprador_registro_de_mas=solucion_publica.bt47_de_la_orden(raiz, deteccion)))
    incidencias.extend(solucion_publica.reglas(raiz, deteccion))
    # Los mensajes de la orden, que son respuestas y no facturas: la anulación
    # y los ocho estados del anexo II. A todo lo demás no le toca.
    incidencias.extend(mensajes.reglas(raiz, deteccion))
    incidencias.extend(edifact.totales_de_otra_guia(raiz, deteccion))
    incidencias.extend(edifact.iva_fuera_del_desglose(raiz, deteccion))
    incidencias.extend(facturae.reglas(raiz, deteccion))
    # Después de las suyas: lo de la copia fiel no es un fallo de la factura,
    # es lo que le va a pasar al copiarse a la solución pública.
    incidencias.extend(copia_fiel.reglas(raiz, deteccion))
    examenes = firma.examinar_todas(raiz) if raiz is not None else ()
    incidencias.extend(firma.reglas(raiz, deteccion, examenes, espanola=espanola))
    incidencias.extend(sellos.reglas_de_documento(raiz, deteccion))
    incidencias.extend(
        cadena.reglas_de_documento(raiz, deteccion, almacen, listas, hoy)
    )
    incidencias.extend(
        cadena.sellos_del_documento(
            raiz, deteccion, almacen.sellos if almacen is not None else None
        )
    )
    incidencias.extend(codigo_unico.reglas(raiz, deteccion, hoy=hoy))
    # Las cuentas de cobro de un mismo emisor, que dentro de un fichero solo
    # pueden no cuadrar en Facturae, que trae varias facturas. Entre ficheros
    # lo mira el lote.
    incidencias.extend(cuentas_de_cobro.reglas(raiz, deteccion))
    return (
        _podar(incidencias),
        firma.estado_de_la_firma(examenes),
        sum(1 for examen in examenes if examen.verificada),
    )


def validar(
    datos: bytes | str,
    hoy: date | None = None,
    catalogo: Catalogo | None = None,
    almacen: Almacen | None = None,
    listas: AlmacenDeListas | None = None,
) -> Informe:
    """Valida un documento: su forma, las reglas europeas y las españolas."""
    deteccion = detectar(datos)
    informe = Informe(deteccion=deteccion)
    if not deteccion:
        return informe
    if isinstance(datos, str):
        datos = datos.encode("utf-8")
    raiz, sintacticas = _arbol(datos, deteccion)
    # Uno solo para las reglas y para `_mirado`: `Catalogo.por_defecto()` en cada
    # sitio compilaba dos veces el esquema de una respuesta.
    catalogo = catalogo or Catalogo.por_defecto()
    incidencias, informe.firma, informe.firmas_verificadas = _reglas(
        raiz, deteccion, hoy, catalogo, almacen, listas, sintacticas
    )
    informe.incidencias.extend(incidencias)
    informe.mirado = _mirado(deteccion, catalogo)
    informe.contenido_medido = mensajes.medido_entero(raiz, deteccion)
    return informe


def _mirado(deteccion: Deteccion, catalogo: Catalogo | None) -> bool:
    """¿Se le ha podido pasar a este documento su comprobación principal?

    Con una factura, siempre: aunque no haya esquemas se le miden las cuentas y
    el código único. Con una respuesta, no: **su comprobación principal es la
    forma**, y sin un esquema que se pueda usar no queda más que la firma, si la
    trae, y que el XML no traiga entidades. Darla
    por correcta —«1 correcto(s)», código de salida 0— sería lo que
    `Informe.validado` existe para evitar: aparecer entre los buenos un fichero
    que nadie ha abierto. Medido antes de escribir esto: con `esquemas/` vacío,
    una respuesta con la forma rota salía correcta.
    """
    if deteccion.familia != RESPUESTA:
        return True
    return esquema.se_puede_comprobar(deteccion, catalogo)


def validar_archivo(
    ruta: str | Path,
    hoy: date | None = None,
    catalogo: Catalogo | None = None,
    almacen: Almacen | None = None,
    listas: AlmacenDeListas | None = None,
) -> Informe:
    """Igual que `validar`, leyendo de un fichero."""
    camino = Path(ruta)
    try:
        datos = camino.read_bytes()
    except OSError as error:
        return Informe(deteccion=_no_se_puede_leer(camino, error))
    try:
        return validar(
            datos,
            hoy=hoy,
            catalogo=catalogo,
            almacen=almacen,
            listas=listas,
        )
    except Exception as error:  # noqa: BLE001 - ver `_se_atraganta`
        return _se_atraganta(camino, error)


def _se_atraganta(camino: Path, error: Exception, nombre: str | None = None) -> Informe:
    """El informe de un fichero que ha hecho fallar al validador mismo.

    Esto no es una queja sobre la factura: es una queja sobre este programa.
    Un fichero de otro puede venir de cualquier manera, y ninguna de ellas
    justifica que el validador se caiga; pero mientras se cae, lo grave no es
    la caída sino lo que se lleva por delante. Antes de esto, apuntar a una
    carpeta de quinientas facturas y que la séptima estuviera mal terminaba en
    una traza de Python y **ninguna** de las otras cuatrocientas noventa y
    nueve revisada. Quien lo lanzara desde un script veía un código de salida
    distinto de cero, que es lo mismo que ve cuando hay facturas con errores.

    Así que se cuenta como un error del fichero —para que el lote no dé por
    bueno lo que no ha mirado— y se dice de quién es la culpa.

    `nombre` es el del lote, cuando lo hay. En la página la ruta es la del disco
    virtual, `/entrada/0/factura__.xml`, con el nombre ya limpiado para poder
    escribirlo; quien lo soltó lo llamaba «factura ñ.xml», y es el que sale en
    la cabecera del documento. El resumen ya empieza por «No se ha podido
    validar.»: el motivo no lo repite.
    """
    nombre = nombre or camino.name
    informe = Informe(
        deteccion=Deteccion(motivo=f"El validador ha fallado con \"{nombre}\".")
    )
    informe.incidencias.append(
        Incidencia(
            "VALIDADOR-SE-ATRAGANTA",
            ERROR,
            f"Este fichero ha hecho fallar al validador: {type(error).__name__}: "
            f"{error}. El fallo es del validador, no necesariamente de la "
            "factura, y hay que arreglarlo aquí. Los demás ficheros del lote "
            "sí se han revisado.",
            campo="Fichero",
            encontrado=nombre,
        )
    )
    return informe


def _no_se_puede_leer(camino: Path, error: OSError) -> Deteccion:
    if isinstance(error, FileNotFoundError):
        return Deteccion(motivo=f"No existe el fichero {camino}.")
    return Deteccion(motivo=f"No se ha podido leer {camino}: {error}")


# --- Un lote de ficheros ---------------------------------------------------

# Las tres partes de lo que se mira, con los nombres y en el orden de «Qué
# mira» en la portada, donde van numeradas: el informe las numera igual para
# que se reconozcan. Y es el orden en que se miran: sin forma no hay contenido
# que leer.
PARTE_FORMA = "La forma"
PARTE_CONTENIDO = "El contenido"
PARTE_FIRMA = "La firma"
PARTES = (PARTE_FORMA, PARTE_CONTENIDO, PARTE_FIRMA)

# De qué parte es cada familia de códigos. Cerrada a propósito, y en los dos
# sentidos: una familia nueva que no esté aquí, o una de aquí que ya no exista,
# pone en rojo `tests/test_informe_por_partes.py` antes de publicarse, en vez
# de contarse en la columna que caiga. `VALIDADOR` no es de ninguna: dice que
# el fichero no se ha llegado a mirar.
PARTE_DE_LA_FAMILIA: dict[str, str | None] = {
    "XSD": PARTE_FORMA, "XML": PARTE_FORMA,
    "BR": PARTE_CONTENIDO, "COPIA": PARTE_CONTENIDO, "CU": PARTE_CONTENIDO,
    "CUENTA": PARTE_CONTENIDO,
    "EDI": PARTE_CONTENIDO, "FE": PARTE_CONTENIDO, "IVA": PARTE_CONTENIDO,
    "NIF": PARTE_CONTENIDO, "PERFIL": PARTE_CONTENIDO, "SIN": PARTE_CONTENIDO,
    "SPFE": PARTE_CONTENIDO,
    "ANCLAS": PARTE_FIRMA, "CADENA": PARTE_FIRMA, "CONFIANZA": PARTE_FIRMA,
    "FIRMA": PARTE_FIRMA, "REVOCACION": PARTE_FIRMA, "REVOCADO": PARTE_FIRMA,
    "SELLO": PARTE_FIRMA,
    "VALIDADOR": None,
}

# Lo que no se mira en ninguna de las tres.
EN_NINGUNA = "si lo que dice la factura es cierto"


@dataclass(frozen=True)
class Parte:
    """Una de las tres, como la pinta la página."""

    nombre: str
    resultado: str          # «Sin errores», «2 avisos», «No aplica», «Sin firma»…
    gravedad: str | None    # la peor que ha salido en ella, para el color
    mirado: str             # lo que se ha comprobado, en una frase; o vacía
    sin_mirar: str          # «No se comprueba…»; o vacía


def _cuantas(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}" if n else ""


def _frase(trozos: list[str]) -> str:
    """Los trozos de `alcance`, en una frase que empieza en mayúscula."""
    if not trozos:
        return ""
    texto = ", ".join(trozos)
    return texto[0].upper() + texto[1:] + "."


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
    # Cómo se llama cada fichero en el informe, en el mismo orden que
    # `informes` y sin repetir ninguno. Ver `nombres_unicos`.
    nombres: list[str] = field(default_factory=list)

    @property
    def nombrados(self) -> list[tuple[Path, Informe, str]]:
        """Cada informe con el nombre por el que se le conoce en el lote.

        Hasta aquí cada fichero se identificaba por `camino.name`, y dos
        ficheros con el mismo nombre en carpetas distintas eran el mismo para
        el lote: un duplicado entre dos de ellos marcaba también al tercero, y
        la queja decía «las dos vienen en factura.xml». En el navegador era
        peor, porque el nombre se limpia antes de escribirlo y «factura ñ.xml»
        y «factura ç.xml» acababan en el mismo fichero: uno pisaba al otro y
        **el primero no se validaba nunca**.
        """
        nombres = self.nombres or nombres_unicos([c for c, _ in self.informes])
        return [
            (camino, informe, nombre)
            for (camino, informe), nombre in zip(self.informes, nombres, strict=True)
        ]

    @property
    def errores(self) -> list[Incidencia]:
        de_cada_uno = [i for _, informe in self.informes for i in informe.errores]
        return de_cada_uno + [i for i in self.cruzadas if i.gravedad == ERROR]

    @property
    def senialados(self) -> set[str]:
        """Ficheros a los que apunta alguna incidencia de conjunto grave.

        Un duplicado no es de ninguno de los dos ficheros por separado: cada
        uno, mirado solo, está perfecto. Sin esto, los dos se imprimían «sin
        errores», los dos se contaban entre los correctos, y el error aparecía
        al final huérfano —de forma que el resumen podía decir «10 correctos, 0
        con errores» sobre un lote que sí tiene un error—.
        """
        return {
            nombre
            for i in self.cruzadas
            if i.gravedad == ERROR
            for nombre in i.ficheros
        }

    @property
    def sin_comprobar(self) -> list[tuple[Path, Informe]]:
        """Ficheros que no se han podido mirar.

        No existen, no se pueden leer, no se reconoce su formato, o se reconoce
        y no hay con qué pasarle su comprobación principal (una respuesta sin
        su esquema, y sin ningún error encontrado por otro lado). Van
        aparte de los correctos y de los que tienen errores porque son un
        tercer estado, y confundirlos con los buenos es justo el fallo que
        deja a alguien creyendo que ha revisado un lote entero cuando se
        equivocó de carpeta.
        """
        return [(c, i) for c, i in self.informes if not i.validado]

    @property
    def conforme(self) -> bool:
        # Un fichero que no se ha podido abrir no cuenta como aprobado. Si
        # contara, `factura-e` devolvería 0 —«todo en orden»— por un lote que
        # nadie ha llegado a leer, y un guion encadenado se lo creería.
        return not self.errores and not self.sin_comprobar

    def __bool__(self) -> bool:
        return self.conforme

    def resumen(self) -> str:
        senialados = self.senialados
        mirados = [
            (nombre, informe)
            for _, informe, nombre in self.nombrados
            if informe.validado
        ]
        correctos = sum(
            1
            for nombre, informe in mirados
            if informe.conforme and nombre not in senialados
        )
        partes = [
            f"{len(self.informes)} fichero(s)",
            f"{correctos} correcto(s)",
            f"{len(mirados) - correctos} con errores",
        ]
        if self.sin_comprobar:
            partes.append(f"{len(self.sin_comprobar)} SIN COMPROBAR")
        if self.cruzadas:
            partes.append(f"{len(self.cruzadas)} incidencia(s) entre ficheros")
        return " · ".join(partes) + "."

    @property
    def firmados(self) -> bool:
        """¿Venía firmado alguno de los ficheros del lote?

        Cambia lo que el informe puede prometer: sobre un lote sin firmas no
        tiene sentido explicar qué parte de la firma se mira y cuál no.
        """
        return any(
            informe.deteccion is not None and informe.deteccion.firmado
            for _, informe in self.informes
        )

    @property
    def con_firma_comprobada(self) -> int:
        """Cuántos documentos traen una firma a la que se ha llegado a mirar.

        Mirarla y que esté mal cuenta: lo que no cuenta es no haber sabido
        mirarla. Nada que ver con `sin_comprobar`, que son los ficheros que no
        se han podido abrir siquiera.
        """
        return sum(
            1
            for _, informe in self.informes
            if informe.firma in (FIRMA_EN_PIE, FIRMA_ROTA)
        )

    @property
    def con_firma_sin_comprobar(self) -> int:
        """Cuántos traen firma y nadie ha podido decir si se sostiene.

        Un algoritmo que aquí no se conoce, una canonicalización que no se sabe
        reproducir, un `SignedInfo` que no está donde tiene que estar. Cada uno
        lleva su aviso; esto es para que la frase del final no se apunte una
        comprobación que sobre ellos no se ha hecho.
        """
        return sum(
            1
            for _, informe in self.informes
            if informe.deteccion is not None
            and informe.deteccion.firmado
            and informe.firma not in (FIRMA_EN_PIE, FIRMA_ROTA)
        )

    def _llegan(self, informe: Informe) -> bool | None:
        """¿Llegan a un ancla todas las firmas verificadas? `None` si no hay.

        Una nota de confianza por cada firma que llega, y solo por esas: si hay
        menos notas que firmas verificadas, alguna no llegó —`CADENA-
        DESCONOCIDA`, `CADENA-RETIRADA`, `CADENA-ROTA`—, sin tener que llevar
        aquí la lista de las maneras de no llegar.
        """
        if not informe.firmas_verificadas:
            return None
        notas = sum(
            1 for i in informe.incidencias if i.codigo == cadena.NOTA_DE_CONFIANZA
        )
        return notas >= informe.firmas_verificadas

    @property
    def con_cadena_que_llega(self) -> int:
        """Documentos cuyas firmas verificadas llegan, todas, a un ancla."""
        return sum(1 for _, informe in self.informes if self._llegan(informe) is True)

    @property
    def con_cadena_que_no_llega(self) -> int:
        """Documentos con alguna firma verificada que no llega a ningún ancla."""
        return sum(1 for _, informe in self.informes if self._llegan(informe) is False)

    def _anulado_contestado(self, informe: Informe) -> bool | None:
        """¿Se sabe si estaba anulado el certificado que firma? `None` si no viene a cuento.

        Solo viene a cuento cuando las firmas llegan a un ancla: antes de eso
        no se mira la revocación. Y se sabe cuando ninguna de ellas lleva un
        aviso de `revocacion.SIN_CONTESTAR`, que salen justo cuando del que
        firma no se ha podido saber nada, o solo con una lista vencida.

        No vale contar la nota de «no consta anulado», que también sale con
        una lista de la raíz sola y el aviso del que firma al lado. Y no vale
        lo que hacía la frase antes de esto: preguntar si había alguna lista en
        la carpeta, que no mira lo que pasó con cada documento.
        """
        if self._llegan(informe) is not True:
            return None
        return not any(
            i.codigo in revocacion.SIN_CONTESTAR for i in informe.incidencias
        )

    @property
    def con_revocacion_contestada(self) -> int:
        return sum(
            1 for _, informe in self.informes
            if self._anulado_contestado(informe) is True
        )

    @property
    def con_revocacion_sin_contestar(self) -> int:
        return sum(
            1 for _, informe in self.informes
            if self._anulado_contestado(informe) is False
        )

    def _familias(self) -> set[str]:
        return {
            informe.deteccion.familia
            for _, informe in self.informes
            if informe.deteccion is not None and informe.deteccion.familia
        }

    def _alcance_por_partes(
        self, forma: bool, anclas: bool
    ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """Lo que se ha mirado y lo que no, repartido entre las tres partes.

        Es la cuenta que `alcance` escribía de corrido, y la leen dos: la frase
        del final y las tres columnas con que empieza el informe en la página.
        Se hace aquí una sola vez porque hecha dos veces, un día una de las dos
        diría que se ha comprobado lo que la otra dice que no.
        """
        mirado: dict[str, list[str]] = {parte: [] for parte in PARTES}
        sin_mirar: dict[str, list[str]] = {parte: [] for parte in PARTES}
        familias = self._familias()
        # El esquema solo se le puede pasar a lo que es XML. Un lote de puro
        # EDIFACT no ha visto ningún XSD, y decir que sí sería apuntarse una
        # comprobación que no se ha hecho, que es el peor error que puede
        # tener esta frase: lo que promete es de lo que se fiará quien la lee.
        #
        # Y una respuesta cuenta solo si se le pudo pasar el suyo: con un
        # lote de respuestas y el esquema de `ApplicationResponse` sin
        # instalar, decir «la forma contra el esquema XSD» sería apuntarse una
        # comprobación que no se ha hecho.
        con_esquema = (familias - {EDIFACT, RESPUESTA}) | (
            {RESPUESTA} if self._alguna_respuesta_mirada() else set()
        )
        if forma and con_esquema:
            mirado[PARTE_FORMA].append("la forma contra el esquema XSD")
        contenido = mirado[PARTE_CONTENIDO]
        if EDIFACT in familias:
            contenido.append(
                "las cuentas que EDIFACT obliga a llevar en el sobre (que el "
                "mensaje traiga los segmentos que dice traer)"
            )
        if familias & {UBL, CII, EDIFACT}:
            contenido.append(
                "las reglas EN 16931 (campos obligatorios, cuadre de totales y "
                "desglose de IVA)"
            )
        if FACTURAE in familias:
            contenido.append(
                "la aritmética del formato Facturae (líneas, totales, impuestos "
                "y cabecera de lote)"
            )
        # Solo donde se mira. Iba siempre, y se prometía sobre un lote de
        # EDIFACT —dos copias idénticas salían «2 correctos», sin el duplicado:
        # de un EDIFACT no se saca el código único— y hasta sobre un lote de
        # ficheros que no se habían podido leer.
        if familias & {UBL, FACTURAE, CII}:
            contenido.append("el código único del RD 238/2026")
        if any(
            incidencia.codigo == "SPFE-ALCANCE"
            for _, informe in self.informes
            for incidencia in informe.incidencias
        ):
            # Solo si alguna factura lo declara: a las demás no se les mide, y
            # decirlo en un lote sin ninguna sería apuntarse lo que no se ha
            # hecho. Y «lo que se puede comprobar», porque hay campos del
            # anexo sin ruta que no se miran (`NO_SE_COMPRUEBA`). Sin comas
            # dentro: la frase entera se une con comas, y «…del RD 238/2026, en
            # las facturas que…, lo que…» se leía como dos cosas distintas.
            # Hasta el 07-10-2026 decía «el borrador del anexo I»: la orden
            # salió en el BOE el 05-10-2026, y lo que es verdad ahora es la
            # mezcla, que va entre paréntesis para no meter otra coma. Y
            # «parte de», porque lo que se mide es lo que ya pedía el borrador
            # de abril: con «lo que el anexo pide… (medido en parte con el
            # borrador)» salían «sin errores» facturas que incumplen la orden
            # en cosas que en UBL sí se pueden ver —la clave 18 del IVA, el
            # proceso de abril, un QR con la descripción equivocada—. Lo midió
            # el revisor de promesas el 07-10-2026. Desde el 11-10-2026 las
            # reglas miden la orden, y lo que de ella falta lo enumera la nota
            # SPFE-ALCANCE de cada factura (`LO_QUE_TODAVIA_NO_SE_MIDE` y
            # `NO_SE_COMPRUEBA`): aquí se manda a ella en vez de copiar la
            # lista, que ya estuvo escrita dos veces y dejó de decir lo mismo.
            # Decía «lo que todavía no se mide», y desde que esa lista está
            # vacía lo que queda es lo que no se puede comprobar: «lo que no
            # se mide» vale para las dos. Y cuelga de esa nota, no de
            # lo que el documento declara: un abono que declara la orden no se
            # mide con el anexo, que solo define facturas, y hasta el
            # 11-10-2026 esta frase lo contaba como medido. Lo vio el revisor
            # de promesas.
            contenido.append(
                "parte de lo que el anexo I de la solución pública pide a las "
                "facturas que la declaran (lo que se puede comprobar en UBL; lo "
                "que no se mide lo dice la nota SPFE-ALCANCE)"
            )
        if self._respuestas_medidas():
            # Cuelga de la nota, como lo del anexo I: solo se apunta si a
            # alguna respuesta del lote se le midió su tabla, y lo que no se
            # mide lo dice ella. Y «parte de», como en el anexo I: la nota
            # enumera lo que la orden les pide y aquí no se mide. Sin él, la
            # frase daba por comprobado todo lo que la orden pide a sus
            # mensajes. Lo vio el revisor de promesas.
            contenido.append(
                "parte de lo que la orden de la solución pública pide a sus "
                "mensajes de anulación y de estado (lo que no se mide lo dice la "
                "nota SPFE-MENSAJE-ALCANCE)"
            )
        de_la_firma = mirado[PARTE_FIRMA]
        sin_la_firma = sin_mirar[PARTE_FIRMA]
        if self.firmados:
            # Todo lo que esta frase promete de la firma cuelga de haber podido
            # comprobar alguna. Con una firma que no se ha sabido mirar —basta
            # un método de firma inventado—, decía «se ha comprobado que las
            # firmas no estén rotas» sobre la única firma del lote, que nadie
            # había mirado. El documento lo decía en su aviso y en su línea de
            # estado; la frase que resume el informe entero se lo callaba, y es
            # la que se lee para saber qué vale el «sin errores».
            if self.con_firma_comprobada:
                de_la_firma.append(
                    "que las firmas no estén rotas: que nadie haya tocado el "
                    "documento desde que se firmó, y que la firma cuadre con el "
                    "certificado que trae dentro"
                )
                if anclas:
                    # Lo mismo que con la firma. «Se ha comprobado que ese
                    # certificado lleve a una autoridad de confianza» salía
                    # también con `CADENA-DESCONOCIDA` en el informe, que es un
                    # aviso y deja el veredicto en «sin errores»: la frase
                    # prometía justo lo que el aviso de encima negaba.
                    if self.con_cadena_que_llega:
                        # «Instalada» no: en la página las anclas vienen con
                        # ella y nadie ha instalado nada. De dónde salen lo
                        # dice la nota de cada firma, con su huella.
                        de_la_firma.append(
                            "que ese certificado lleve a un ancla de confianza "
                            "(la nota de cada firma dice de dónde sale)"
                        )
                        # Por documento, como la cadena: con la prueba que
                        # trae cada uno o con la carpeta, y solo si contestó
                        # por el que firma. Ver `_anulado_contestado`.
                        if self.con_revocacion_contestada:
                            de_la_firma.append(
                                "que no lo hayan anulado, con la prueba de "
                                "revocación que cita cada documento"
                            )
                            # Lo que queda no es un defecto del validador:
                            # ninguna prueba sabe lo que pasó después.
                            sin_la_firma.append(
                                "si lo anularon después de la fecha de esa "
                                "prueba"
                            )
                        sin_la_firma.extend(
                            self._de_cuantos(
                                self.con_revocacion_sin_contestar,
                                "si está anulado el certificado",
                            )
                        )
                    sin_la_firma.extend(
                        self._de_cuantos(
                            self.con_cadena_que_no_llega,
                            "de quién es el certificado",
                        )
                    )
                else:
                    # Decir «firma comprobada» a secas dejaría creer que también
                    # se sabe de quién es, que es la mitad que más importa. Y
                    # la revocación no es cosa de salir a la red, como decía:
                    # sin saber a qué autoridad llega no hay a quién creerle
                    # una lista, venga de donde venga.
                    sin_la_firma.append(
                        "de quién es el certificado ni si está anulado (sin "
                        "anclas de confianza no se sabe a qué autoridad llega, "
                        "y sin eso no se puede creer ninguna prueba de "
                        "revocación)"
                    )
            # El porqué no se repite aquí: son cuatro motivos distintos y cada
            # documento lleva el suyo escrito en su aviso. Esta frase solo
            # tiene que dejar de apuntarse la comprobación.
            sin_la_firma.extend(
                self._de_cuantos(self.con_firma_sin_comprobar, "la firma")
            )
        else:
            sin_la_firma.append("la validez de las firmas electrónicas")
        if EDIFACT in familias:
            sin_mirar[PARTE_CONTENIDO].append(
                "el código único de las facturas EDIFACT"
            )
        medidas = self._respuestas_medidas()
        if RESPUESTA in familias and self._respuestas_con_contenido_sin_mirar():
            # De una respuesta solo se mira la forma y, si la trae, la firma.
            # Sin esta línea, la columna del contenido salía «Sin mirar» sin
            # decir de qué, y la frase de arriba solo hablaba de facturas.
            #
            # Sin comas dentro, como el trozo del anexo I, y sin decir aquí qué
            # sí se mira: llevaba «de las que solo se mira la forma y la firma»,
            # que se leía como dos cosas, y lo prometía también sobre una
            # respuesta sin esquema y sin firma. Lo que sí se ha mirado ya lo
            # dicen las otras dos columnas, y lo dicen de este lote.
            #
            # Desde el 12-10-2026 a los mensajes de la orden sí se les mide el
            # contenido, y la frase no puede decir de todas que no: «las
            # demás» cuando a alguna se le midió, y la de siempre cuando a
            # ninguna. Y se cuentan respuestas, no documentos: ver
            # `_respuestas_con_contenido_sin_mirar`.
            sin_mirar[PARTE_CONTENIDO].append(
                "el contenido de las demás respuestas (ApplicationResponse)"
                if medidas else
                "el contenido de las respuestas (ApplicationResponse)"
            )
        return mirado, sin_mirar

    def _respuestas_con_contenido_sin_mirar(self) -> int:
        """Cuántas respuestas del lote traen algo cuyo contenido no se ha medido.

        Por documento con la nota no basta: uno con un pago y una respuesta de
        otra red la lleva, y solo se ha medido el pago. Hasta el 12-10-2026 se
        contaban así, y la frase daba el contenido por mirado y callaba el de
        la segunda. Lo vio el revisor de promesas.
        """
        return sum(
            1 for _, informe in self.informes
            if informe.deteccion is not None
            and informe.deteccion.familia == RESPUESTA
            and not informe.contenido_medido
        )

    def _respuestas_medidas(self) -> int:
        """Cuántas respuestas del lote son mensajes de la orden, medidos.

        Se cuentan por la nota SPFE-MENSAJE-ALCANCE, que sale una vez por
        documento en cuanto uno de sus `cac:DocumentResponse` lleva un código
        de la orden. Un documento que mezcla mensajes de la orden con otras
        respuestas cuenta aquí, y lo que no se le midió lo cuenta
        `_respuestas_con_contenido_sin_mirar`.
        """
        return sum(
            1 for _, informe in self.informes
            if any(i.codigo == "SPFE-MENSAJE-ALCANCE" for i in informe.incidencias)
        )

    def _alguna_respuesta_mirada(self) -> bool:
        """¿Se le pudo pasar su esquema a alguna de las respuestas del lote?

        Alguna y no todas, con el mismo criterio que las facturas: a una
        factura cuyo esquema falta tampoco se le quita la frase de la forma al
        resto del lote. La que no se miró lleva su aviso y sale SIN COMPROBAR,
        así que el lote no puede salir «sin errores».
        """
        return any(
            informe.mirado
            for _, informe in self.informes
            if informe.deteccion is not None
            and informe.deteccion.familia == RESPUESTA
        )

    def alcance(self, forma: bool = True, anclas: bool = False) -> str:
        """Qué se ha mirado, dicho una vez y al final del informe.

        `forma` dice si había esquemas XSD con los que comprobarla y `anclas`
        si había anclas de confianza. Sin este
        dato la frase decía «se ha comprobado la forma contra el esquema XSD»
        justo encima del recordatorio de que no hay esquemas puestos: dos
        líneas seguidas contradiciéndose, que es peor que no decir nada y es
        exactamente el defecto que esta función viene a arreglar.

        «Sin errores» es el mensaje más peligroso que da este programa. No
        quiere decir «esta factura está bien»: quiere decir «no ha fallado
        ninguna de las comprobaciones que existen», y quien lo lee no tiene por
        qué saber cuáles son. La diferencia entre las dos lecturas es la que
        separa una herramienta útil de una que da falsa tranquilidad.

        Va una sola vez al final, no como aviso en cada fichero, por lo mismo
        que el recordatorio de los esquemas: en un lote de doscientos, cien
        repeticiones de la misma advertencia son ruido y se dejan de leer.
        """
        mirado, sin_mirar = self._alcance_por_partes(forma, anclas)
        dicho = [m for parte in PARTES for m in mirado[parte]]
        if not dicho:
            # Solo pasa si no se ha podido comprobar ningún fichero: cualquiera
            # que se lea como factura aporta al menos sus reglas, y una
            # respuesta, su forma o su firma. Llega aquí un lote de ficheros
            # que no se han podido leer o reconocer, y uno de respuestas sin su
            # esquema y sin firma; por eso dice «comprobar» y no «leer como
            # factura», que de una respuesta sería falso. Antes esto no podía
            # pasar, porque el código único se prometía siempre —hasta sobre un
            # lote de ficheros que no existían—.
            return (
                "No se ha comprobado nada: ninguno de los ficheros se ha podido "
                "comprobar."
            )
        # Lo que no se mira de la firma va delante del código único de EDIFACT,
        # que es el orden en que se escribió la frase y en el que se lee.
        callado = sin_mirar[PARTE_FIRMA] + sin_mirar[PARTE_CONTENIDO] + [EN_NINGUNA]
        return (
            "Que no haya errores quiere decir que se ha comprobado "
            + ", ".join(dicho)
            + ".\nNo se comprueba "
            + ", ni ".join(callado)
            + "."
        )

    def partes(self, forma: bool = True, anclas: bool = False) -> list[Parte]:
        """La forma, el contenido y la firma, cada una con lo que ha salido.

        Es `alcance` repartido en tres, con la cuenta de cada parte al lado,
        para que la página lo enseñe **antes** del detalle y no al final: quien
        lee «sin errores» tiene que saber en ese momento contra qué, no
        después de treinta glosas. La idea es la del resumen del HTTP
        Observatory de Mozilla, que pone lo comprobado encima de las pruebas.

        La cuenta se hace por familia de código —`PARTE_DE_LA_FAMILIA`— y lo
        mirado sale de la misma cuenta que la frase, así que las dos no pueden
        prometer cosas distintas. Vacía si no se ha podido leer ningún
        fichero: no hay partes que enseñar, y eso ya lo dice `alcance`.
        """
        mirado, sin_mirar = self._alcance_por_partes(forma, anclas)
        if not any(mirado.values()):
            return []
        cuentas = {parte: {ERROR: 0, AVISO: 0, NOTA: 0} for parte in PARTES}
        todas = [i for _, informe in self.informes for i in informe.incidencias]
        for incidencia in todas + self.cruzadas:
            parte = PARTE_DE_LA_FAMILIA[familia_de(incidencia.codigo)]
            if parte is not None:
                cuentas[parte][incidencia.gravedad] += 1

        salida = []
        for parte in PARTES:
            errores, avisos = cuentas[parte][ERROR], cuentas[parte][AVISO]
            no = list(sin_mirar[parte])
            if errores or avisos:
                resultado = " y ".join(
                    c for c in (_cuantas(errores, "error", "errores"),
                                _cuantas(avisos, "aviso", "avisos")) if c
                )
            elif mirado[parte]:
                resultado = "Sin errores"
            elif parte == PARTE_FORMA and not (self._familias() - {EDIFACT}):
                resultado = "No aplica"
                no.append("la forma: EDIFACT no tiene esquema XSD")
            elif parte == PARTE_FORMA:
                # «Sin errores» aquí sería el peor fallo posible: la forma sin
                # mirar, y el titular de la columna diciendo que está bien.
                resultado = "Sin mirar"
                no.append("la forma: no hay esquemas XSD con que mirarla")
            elif parte == PARTE_FIRMA and not self.firmados:
                resultado = "Sin firma"
            else:
                resultado = "Sin mirar"
            salida.append(Parte(
                nombre=parte,
                resultado=resultado,
                gravedad=ERROR if errores else AVISO if avisos else None,
                mirado=_frase(mirado[parte]),
                sin_mirar="No se comprueba " + ", ni ".join(no) + "." if no else "",
            ))
        return salida

    def _de_cuantos(self, cuantos: int, que: str) -> list[str]:
        """«la firma de este documento —su aviso dice por qué—», y sus plurales.

        El porqué no se repite en la frase: cada documento lo lleva escrito en
        su aviso, y son varios motivos distintos.
        """
        if not cuantos:
            return []
        if len(self.informes) == 1:
            return [f"{que} de este documento (su aviso dice por qué)"]
        if cuantos == 1:
            return [f"{que} de uno de los documentos (su aviso dice por qué)"]
        return [f"{que} de {cuantos} de los documentos (sus avisos dicen por qué)"]

    def detalle(self, forma: bool = True, anclas: bool = False) -> str:
        senialados = self.senialados
        lineas: list[str] = []
        for camino, informe, nombre in self.nombrados:
            lineas.append(str(camino))
            resumen = informe.resumen()
            if nombre in senialados and informe.conforme:
                # Decirlo aquí y no solo al final. Quien revisa un lote de
                # doscientos ficheros lee la línea de cada uno; si esta dice
                # «sin errores» a secas, no vuelve a bajar a mirar.
                resumen = resumen.rstrip(".") + (
                    ", pero choca con otro fichero (ver abajo)."
                )
            lineas.append(f"  {resumen}")
            for incidencia in informe.notas + informe.errores + informe.avisos:
                lineas.append("")
                lineas.append(_sangrar(incidencia.texto(origen(incidencia)), "  "))
            lineas.append("")
        if self.cruzadas:
            lineas.append("Entre ficheros:")
            for incidencia in self.cruzadas:
                lineas.append("")
                lineas.append(_sangrar(incidencia.texto(origen(incidencia)), "  "))
            lineas.append("")
        lineas.append(self.resumen())
        lineas.append("")
        lineas.append(self.alcance(forma, anclas))
        return "\n".join(lineas)

    def recuento(self, forma: bool = True, anclas: bool = False) -> str:
        """El lote contado, para mandárselo a otra persona.

        Es lo que hace falta para el informe de brecha: quien factura pasa
        Glosa-e en su ordenador y manda solo esto. `detalle` no vale para eso,
        porque se hizo para quien tiene las facturas delante: dice el nombre de
        cada fichero, el valor que está mal («Tiene:») y, entre ficheros, el
        código único, que es el NIF, el número y la fecha (medido el
        25-09-2026 sobre `ejemplos/`: `B12345674|F-2026-0002|2026-03-05`).

        Aquí solo salen códigos, gravedades, normas, formatos y cuentas. Ni el
        mensaje de cada incidencia, que a veces cita el valor, ni su campo, ni
        las rutas de los esquemas y las anclas, que llevan el nombre de usuario
        del equipo. Lo vigila una prueba que pasa por aquí facturas de ejemplo
        y falla si cualquier texto de dentro, o el nombre de un fichero,
        aparece en la salida.

        Desde el 19-10-2026 lleva además las combinaciones: cuántos documentos
        tienen exactamente los mismos códigos. Sin ellas, que las 18 facturas de
        un código fueran las mismas 18 de otro había que deducirlo de que las
        cuentas coincidían, y el informe de brecha lo decía como deducción (lo
        vio la prueba del informe de ejemplo, paso 14b). Lo que sale en todos
        los documentos se dice una vez arriba y no se repite en cada línea:
        si no, las dos notas que lleva cualquier factura de la solución pública
        tapaban lo que distingue a unas de otras. Y en los formatos va el
        código del tipo de factura (380, 384...), que es lo que separa una
        rectificativa de las demás; solo si es un código, ver
        `_tipo_que_se_cuenta`.
        """
        orden = {ERROR: 0, AVISO: 1, NOTA: 2}
        formatos: dict[str, int] = {}
        en_documentos: dict[tuple[str, str], int] = {}
        veces: dict[tuple[str, str], int] = {}
        de_cada_uno: list[tuple[str, frozenset[tuple[str, str]]]] = []
        for _, informe in self.informes:
            deteccion = informe.deteccion
            if deteccion:
                formato = " ".join(x for x in (deteccion.familia, deteccion.version) if x)
                tipo = " ".join(x for x in (deteccion.tipo_documento, _tipo_que_se_cuenta(deteccion)) if x)
                if tipo:
                    formato += f" ({tipo})"
            else:
                formato = "sin reconocer o sin leer"
            formatos[formato] = formatos.get(formato, 0) + 1
            vistas: set[tuple[str, str]] = set()
            for incidencia in informe.incidencias:
                clave = (incidencia.gravedad, incidencia.codigo)
                veces[clave] = veces.get(clave, 0) + 1
                if clave not in vistas:
                    vistas.add(clave)
                    en_documentos[clave] = en_documentos.get(clave, 0) + 1
            de_cada_uno.append((formato, frozenset(vistas)))
        cruzadas: dict[tuple[str, str], int] = {}
        for incidencia in self.cruzadas:
            clave = (incidencia.gravedad, incidencia.codigo)
            cruzadas[clave] = cruzadas.get(clave, 0) + 1

        def ordenadas(cuentas: dict[tuple[str, str], int]) -> list[tuple[str, str]]:
            return sorted(cuentas, key=lambda c: (orden.get(c[0], 9), -cuentas[c], c[1]))

        def norma(codigo: str) -> str:
            return normas.norma(codigo)[0]

        lineas = [
            "Recuento de Glosa-e",
            "Solo códigos y cuentas: no lleva nombres de fichero, NIF, números de "
            "factura, fechas, importes ni nombres. Léelo antes de enviarlo.",
            "",
            self.resumen(),
            "",
            "Formatos:",
        ]
        for formato in sorted(formatos, key=lambda f: (-formatos[f], f)):
            lineas.append(f"  {formatos[formato]:>5}  {formato}")
        lineas.append("")
        lineas.append("Códigos de cada documento (en cuántos documentos sale y cuántas veces):")
        if en_documentos:
            ancho = max(len(c[1]) for c in en_documentos)
            for gravedad, codigo in ordenadas(en_documentos):
                clave = (gravedad, codigo)
                lineas.append(
                    f"  {gravedad.upper():<5}  {codigo:<{ancho}}  {en_documentos[clave]:>5} doc.  "
                    f"{_veces(veces[clave])}  · {norma(codigo)}"
                )
        else:
            lineas.append("  Ninguno.")
        if len(de_cada_uno) > 1:
            lineas.append("")
            lineas.extend(_siempre_juntos(de_cada_uno, orden))
        if de_cada_uno:
            lineas.append("")
            lineas.extend(_combinaciones(de_cada_uno, orden))
        if cruzadas:
            lineas.append("")
            lineas.append("Entre ficheros (cuántas veces):")
            ancho = max(len(c[1]) for c in cruzadas)
            for gravedad, codigo in ordenadas(cruzadas):
                lineas.append(
                    f"  {gravedad.upper():<5}  {codigo:<{ancho}}  {_veces(cruzadas[(gravedad, codigo)])}"
                    f"  · {norma(codigo)}"
                )
        lineas.append("")
        lineas.append(self.alcance(forma, anclas))
        if not forma:
            lineas.append("No se ha comprobado la forma: no había esquemas XSD.")
        if not anclas and self.firmados:
            lineas.append("No se ha comprobado de quién son las firmas: no había anclas de confianza.")
        return "\n".join(lineas)


# Lo único del tipo que el recuento enseña: un código de tres cifras (el BT-3
# de UBL, CII y EDIFACT) o los de las listas cerradas de Facturae. El tipo es
# texto del documento, y el recuento no lleva texto del documento: una factura
# mal hecha que traiga ahí otra cosa (un nombre, una referencia) no la saca.
_TIPOS_DE_FACTURAE = {"FC", "FA", "AF"}
_CLASES_DE_FACTURAE = {"OO", "OR", "OC", "CO", "CR", "CC"}


def _tipo_que_se_cuenta(deteccion: Deteccion) -> str | None:
    codigo = (deteccion.codigo_tipo or "").strip()
    if re.fullmatch(r"[0-9]{3}", codigo):
        return codigo
    partes = codigo.split()
    if len(partes) == 2 and partes[0] in _TIPOS_DE_FACTURAE and partes[1] in _CLASES_DE_FACTURAE:
        return codigo
    return "tipo sin código" if codigo else None


def _siempre_juntos(de_cada_uno: list[tuple[str, frozenset[tuple[str, str]]]],
                    orden: dict[str, int]) -> list[str]:
    """Los códigos que salen exactamente en los mismos documentos.

    Es la prueba de "una causa, varios códigos": dos códigos que van juntos en
    las mismas 18 facturas, ni una más ni una menos, casi siempre son el mismo
    fallo visto por dos reglas. Las combinaciones lo dicen también, pero en un
    lote desordenado no se ve: medido el 19-10-2026 sobre las 146 muestras
    públicas de `muestras/`, salían 89 combinaciones, 70 de un solo documento,
    y alguna con más de veinte códigos en la línea. Se agrupa por el conjunto
    de documentos y no por la cuenta: dos códigos con 18 cada uno en facturas
    distintas no van juntos. Lo que sale en todos no va aquí, porque ya lo dice
    la primera línea de las combinaciones.
    """
    donde: dict[tuple[str, str], set[int]] = {}
    for indice, (_, codigos) in enumerate(de_cada_uno):
        for clave in codigos:
            donde.setdefault(clave, set()).add(indice)
    grupos: dict[frozenset[int], list[tuple[str, str]]] = {}
    for clave, documentos in donde.items():
        if len(documentos) < len(de_cada_uno):
            grupos.setdefault(frozenset(documentos), []).append(clave)
    juntos = [(len(documentos), sorted(claves, key=lambda c: (orden.get(c[0], 9), c[1])))
              for documentos, claves in grupos.items() if len(claves) > 1]
    lineas = ["Códigos que van siempre juntos (salen en los mismos documentos, ni uno más ni uno menos):"]
    if not juntos:
        lineas.append("  Ninguno.")
    for cuantos, claves in sorted(juntos, key=lambda j: (-j[0], orden.get(j[1][0][0], 9), j[1])):
        lineas.append(f"  {cuantos:>5} doc.  " + " + ".join(f"{g.upper()} {c}" for g, c in claves))
    return lineas


def _combinaciones(de_cada_uno: list[tuple[str, frozenset[tuple[str, str]]]],
                   orden: dict[str, int]) -> list[str]:
    """Cuántos documentos llevan exactamente lo mismo.

    Con un solo documento no se saca nada en común: todo lo suyo sería "en
    todos", y la línea de abajo diría "nada más" de un documento con errores.
    El formato va en cada línea solo si el lote tiene más de uno; con uno, es
    el mismo en todas y no dice nada.
    """
    en_todos: frozenset[tuple[str, str]] = frozenset()
    if len(de_cada_uno) > 1:
        en_todos = frozenset.intersection(*(codigos for _, codigos in de_cada_uno))

    def escritos(codigos) -> str:
        ordenados = sorted(codigos, key=lambda c: (orden.get(c[0], 9), c[1]))
        return " + ".join(f"{gravedad.upper()} {codigo}" for gravedad, codigo in ordenados)

    cuentas: dict[tuple[str, frozenset[tuple[str, str]]], int] = {}
    for formato, codigos in de_cada_uno:
        clave = (formato, codigos - en_todos)
        cuentas[clave] = cuentas.get(clave, 0) + 1
    varios_formatos = len({formato for formato, _ in de_cada_uno}) > 1
    ancho = max(len(formato) for formato, _ in de_cada_uno)
    lineas = ["Combinaciones (cuántos documentos llevan exactamente lo mismo):"]
    if en_todos:
        lineas.append(f"  En todos, y por eso no se repite abajo: {escritos(en_todos)}.")
    resto = "nada más" if en_todos else "ningún código"

    def peso(clave):
        formato, codigos = clave
        peor = min((orden.get(g, 9) for g, _ in codigos), default=9)
        return (-cuentas[clave], peor, formato, escritos(codigos))

    for clave in sorted(cuentas, key=peso):
        formato, codigos = clave
        columna = f"{formato:<{ancho}}  " if varios_formatos else ""
        lineas.append(f"  {cuentas[clave]:>5}  {columna}{escritos(codigos) or resto}")
    return lineas


def _veces(cuantas: int) -> str:
    return f"{cuantas:>5} {'vez' if cuantas == 1 else 'veces':<5}"


def _sangrar(texto: str, margen: str) -> str:
    return "\n".join(margen + linea for linea in texto.splitlines())


def nombres_unicos(
    caminos: list[Path], dados: list[str] | None = None
) -> list[str]:
    """Un nombre por fichero, corto y sin que se repita ninguno.

    El de la ruta, o el que se da. Si dos rutas distintas acaban igual, se sube
    por sus carpetas hasta que se distingan —`a/factura.xml` y
    `b/factura.xml`—, que es lo que quien lee reconoce. Lo que siga repetido
    después —la misma ruta dos veces, o dos nombres dados iguales— se numera:
    `factura.xml (2)`. Numerado y no fundido, porque son dos entradas del lote
    y cada una tiene su informe.
    """
    if dados is not None and len(dados) != len(caminos):
        raise ValueError(
            f"hay {len(caminos)} ficheros y {len(dados)} nombres para ellos"
        )
    nombres = list(dados) if dados is not None else [c.name for c in caminos]
    if dados is None:
        hondo = max((len(c.parts) for c in caminos), default=1)
        for cuantas in range(2, hondo + 1):
            # Solo se sube por un nombre que llevan rutas **distintas**. La
            # misma ruta dos veces no se distingue subiendo —se llegaba a la
            # ruta entera, `C:/Users/...`, y seguían iguales—: esa se numera.
            rutas: dict[str, set[Path]] = {}
            for camino, nombre in zip(caminos, nombres):
                rutas.setdefault(nombre, set()).add(camino)
            repetidos = {n for n, cuales in rutas.items() if len(cuales) > 1}
            if not repetidos:
                break
            nombres = [
                Path(*c.parts[-cuantas:]).as_posix() if n in repetidos else n
                for c, n in zip(caminos, nombres)
            ]
    usados: set[str] = set()
    salida = []
    for nombre in nombres:
        propuesto, vez = nombre, 1
        while propuesto in usados:
            vez += 1
            propuesto = f"{nombre} ({vez})"
        usados.add(propuesto)
        salida.append(propuesto)
    return salida


def validar_lote(
    rutas: list[str | Path],
    hoy: date | None = None,
    catalogo: Catalogo | None = None,
    almacen: Almacen | None = None,
    listas: AlmacenDeListas | None = None,
    nombres: list[str] | None = None,
) -> InformeLote:
    """Valida varios ficheros y además los compara entre sí.

    Cada fichero se valida por su cuenta y después se juntan todas las facturas
    de todos los ficheros para las reglas de conjunto. Esa segunda pasada es la
    razón de ser de esta función: un duplicado entre dos ficheros no puede
    detectarlo ninguno de los dos por separado.

    `nombres` es cómo se llama cada fichero para quien lee, si no es el de su
    ruta: en el navegador la ruta es la del disco virtual y el nombre, el que
    tenía en el ordenador de quien lo soltó.

    Es `LoteEnMarcha` recorrido de un tirón: en consola no hay nadie a quien
    ceder el turno.
    """
    marcha = LoteEnMarcha(rutas, hoy=hoy, catalogo=catalogo, almacen=almacen,
                          listas=listas, nombres=nombres)
    for _ in marcha:
        pass
    return marcha.lote


class LoteEnMarcha:
    """`validar_lote`, un fichero cada vez.

    Existe por el navegador. Allí Python corre en el mismo hilo que pinta la
    página, y mientras valida no se pinta nada ni se atiende un clic. Medido el
    20-10-2026 con 3.000 facturas de la solución pública: 108 segundos con la
    pestaña congelada y sin decir cómo iba, que es exactamente lo que hace que
    alguien la cierre creyendo que se ha colgado.

    Recorrerlo da, después de cada fichero, cuántos van. Quien lo recorre
    decide cuándo parar a pintar; el lote es el mismo que saldría de un tirón,
    porque es el mismo código: `validar_lote` no es otra cosa que esto sin
    pararse. Las reglas entre ficheros corren al final, con todos dentro, y
    `lote` no existe hasta entonces.
    """

    def __init__(
        self,
        rutas: list[str | Path],
        hoy: date | None = None,
        catalogo: Catalogo | None = None,
        almacen: Almacen | None = None,
        listas: AlmacenDeListas | None = None,
        nombres: list[str] | None = None,
    ) -> None:
        self._caminos = [Path(ruta) for ruta in rutas]
        # Los nombres se resuelven aquí y no al recorrerlo: si no cuadran con
        # las rutas, quien llama se entera al crearlo, como con validar_lote.
        self._nombres = nombres_unicos(self._caminos, nombres)
        self._hoy = hoy
        # Un solo catalogo para todo el lote: asi el esquema se compila una vez
        # y no una por fichero, que es lo que de verdad cuesta.
        self._catalogo = catalogo or Catalogo.por_defecto()
        # Un solo almacen para todo el lote, por lo mismo que el catalogo: leer
        # y parsear las anclas una vez, no una por fichero.
        self._almacen = almacen if almacen is not None else Almacen.por_defecto()
        self._listas = listas if listas is not None else AlmacenDeListas.por_defecto()
        self.total = len(self._caminos)
        self.lote: InformeLote | None = None
        self._empezado = False

    def __iter__(self):
        # Una vez y no más. Recorrerlo dos veces validaría dos veces y dejaría
        # en `lote` el segundo; mejor que se note.
        if self._empezado:
            raise RuntimeError("este lote ya se ha recorrido")
        self._empezado = True
        lote = InformeLote(nombres=self._nombres)
        todos: list[codigo_unico.CodigoUnico] = []
        procedencias: list[str] = []
        cobros: list[cuentas_de_cobro.Cobro] = []
        de_donde_cobros: list[str] = []

        for hechas, (camino, nombre) in enumerate(
            zip(self._caminos, lote.nombres, strict=True), start=1
        ):
            informe, codigos, suyos = self._uno(camino, nombre)
            lote.informes.append((camino, informe))
            todos.extend(codigos)
            procedencias.extend([nombre] * len(codigos))
            cobros.extend(suyos)
            de_donde_cobros.extend([nombre] * len(suyos))
            yield hechas

        # Solo interesa lo que cruza ficheros. Lo que ya dijo el informe de un
        # fichero sobre sus propias facturas no se repite aquí.
        dentro_de_uno = {
            _senia(i) for _, informe in lote.informes for i in informe.incidencias
        }
        lote.cruzadas = [
            i
            for i in (
                codigo_unico.reglas_de_lote(todos, procedencias=procedencias)
                + cuentas_de_cobro.reglas_de_lote(cobros, procedencias=de_donde_cobros)
            )
            if _senia(i) not in dentro_de_uno
        ]
        self.lote = lote

    def _uno(
        self, camino: Path, nombre: str
    ) -> tuple[Informe, list[codigo_unico.CodigoUnico], list[cuentas_de_cobro.Cobro]]:
        """El informe de un fichero, y sus facturas para las reglas de conjunto:
        los códigos únicos y las cuentas de cobro."""
        try:
            datos = camino.read_bytes()
        except OSError as error:
            return Informe(deteccion=_no_se_puede_leer(camino, error)), [], []

        try:
            deteccion = detectar(datos)
            raiz, sintacticas = _arbol(datos, deteccion)
            informe = Informe(deteccion=deteccion)
            if deteccion:
                incidencias, informe.firma, informe.firmas_verificadas = _reglas(
                    raiz, deteccion, self._hoy, self._catalogo, self._almacen,
                    self._listas, sintacticas
                )
                informe.incidencias.extend(incidencias)
                informe.mirado = _mirado(deteccion, self._catalogo)
                informe.contenido_medido = mensajes.medido_entero(raiz, deteccion)
        except Exception as error:  # noqa: BLE001 - ver `_se_atraganta`
            return _se_atraganta(camino, error, nombre), [], []

        # Al montón del lote solo van las facturas sujetas al reglamento
        # español. Comparar series y duplicados entre una factura holandesa y
        # una alemana no significa nada: no comparten numeración ni tienen por
        # qué. Sin este filtro salían «duplicados» entre dos suites de prueba
        # que solo tenían en común el número de ejemplo.
        #
        # Las cuentas de cobro, en cambio, de todas: que un proveedor holandés
        # pida el pago en otra cuenta es la misma señal que si fuera español.
        cobros = cuentas_de_cobro.extraer_de(raiz, deteccion)
        if codigo_unico.obligado_en_espania(raiz, deteccion):
            return informe, list(codigo_unico.extraer_de(raiz, deteccion)), cobros
        return informe, [], cobros
