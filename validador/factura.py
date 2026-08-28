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

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from lxml import etree

from validador import (
    cadena,
    codigo_unico,
    edifact,
    en16931,
    esquema,
    facturae,
    firma,
    sellos,
)
from validador.formato import (
    CII,
    EDIFACT,
    FACTURAE,
    UBL,
    Deteccion,
    detectar,
    parser,
)
from validador.cadena import Almacen
from validador.revocacion import AlmacenDeListas
from validador.esquema import Catalogo
from validador.incidencias import ERROR, Incidencia, Informe

# Familias que vienen escritas en XML y se parsean tal cual.
_FAMILIAS_XML = (UBL, FACTURAE, CII)

# EDIFACT también acaba en un árbol, pero por dos caminos: si viene en XML
# —la forma de ISO 20625, que es la que publica la Comisión— se parsea como
# los demás, y si viene en tira se convierte antes. A partir de ahí las
# reglas no notan la diferencia, que es justamente la idea.

# Cuando la queja de la izquierda ya ha saltado, la de la derecha sobra: dicen
# lo mismo con las palabras de dos reglamentos distintos.
_SOBRA_SI: dict[str, tuple[str, ...]] = {
    "CU-00": ("BR-02", "BR-03"),
    "CU-02": ("BR-02",),
}

# De qué reglamento sale cada queja, por el prefijo de su código. Va en el
# informe, junto al código, porque cambia lo que hay que hacer con la queja:
# lo que firma una norma te lo rechaza el receptor, lo que firmamos nosotros
# es una opinión que puedes discutir.
EUROPEA = "EN 16931"
ESPANOLA = "RD 238/2026"
FORMA = "Esquema XSD"
NACIONAL = "formato Facturae"
SELLO = "firma electrónica"
# La norma que manda en la sintaxis de EDIFACT: cómo se separan los
# segmentos, y sobre todo las cuentas del sobre.
SINTAXIS_EDI = "ISO 9735"
CASA = "de la casa"
OTRA = "Formato"


def origen(incidencia: Incidencia) -> str:
    """A qué norma responde una incidencia."""
    if incidencia.codigo.startswith("BR-"):
        return EUROPEA
    if incidencia.codigo.startswith("CU-"):
        return ESPANOLA
    if incidencia.codigo.startswith("XSD-"):
        return FORMA
    if incidencia.codigo.startswith("FE-"):
        return NACIONAL
    if incidencia.codigo.startswith(
        ("FIRMA-", "CADENA-", "REVOCA", "CONFIANZA-", "SELLO-")
    ):
        # «REVOCA» y no «REVOCACION-» a propósito: el código de la anulación
        # confirmada es `REVOCADO`, a secas, y sin esto salía etiquetado como
        # un problema de formato, que es justo lo que no es. Lo mismo le pasaba
        # a todo lo de los sellos de tiempo, que es lo contrario de un problema
        # de formato: es de lo que cuelga la fecha de la firma.
        return SELLO
    if incidencia.codigo.startswith("EDI-"):
        return SINTAXIS_EDI
    if incidencia.codigo.startswith("NIF-"):
        # No lo firma el RD 238/2026 —el código único solo usa el NIF del
        # emisor—, así que no puede salir con su etiqueta. Es nuestra.
        return CASA
    if incidencia.codigo.startswith("IVA-"):
        # `IVA-` es el prefijo de las comprobaciones propias. Sin esta rama
        # caían en OTRA, que se lee «Formato», y una regla de IVA no es un
        # problema de formato: es que opinamos nosotros.
        return CASA
    return OTRA


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
        return etree.fromstring(datos, parser=parser()), []
    except etree.XMLSyntaxError:
        # `detectar` ya lo parseó sin problemas, así que llegar aquí sería
        # raro. Aun así, mejor no reventar el lote entero por un fichero.
        return None, []


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
) -> list[Incidencia]:
    """Todas las reglas sobre un documento ya parseado y ya identificado.

    La forma va primero porque es lo primero que mira un receptor: si el
    documento no cumple el esquema, ni llega a leer los numeros.
    """
    # Una sola vez, y sirve para los dos bandos: el reglamento español no
    # aplica a una factura extranjera, y tampoco tiene sentido medirle los
    # tipos de IVA contra los que se usan aquí.
    espanola = codigo_unico.obligado_en_espania(raiz, deteccion)
    incidencias = list(sintacticas or [])
    incidencias.extend(esquema.reglas(raiz, deteccion, catalogo))
    incidencias.extend(en16931.reglas(raiz, deteccion, espanola=espanola))
    incidencias.extend(edifact.totales_de_otra_guia(raiz, deteccion))
    incidencias.extend(facturae.reglas(raiz, deteccion))
    incidencias.extend(firma.reglas(raiz, deteccion))
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
    return _podar(incidencias)


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
    informe.incidencias.extend(
        _reglas(
            raiz, deteccion, hoy, catalogo, almacen, listas, sintacticas
        )
    )
    return informe


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
        return validar(
            camino.read_bytes(),
            hoy=hoy,
            catalogo=catalogo,
            almacen=almacen,
            listas=listas,
        )
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

        No existen, no se pueden leer, o no se reconoce su formato. Van
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
            (camino, informe)
            for camino, informe in self.informes
            if informe.validado
        ]
        correctos = sum(
            1
            for camino, informe in mirados
            if informe.conforme and camino.name not in senialados
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

    def alcance(
        self, forma: bool = True, anclas: bool = False, listas: bool = False
    ) -> str:
        """Qué se ha mirado, dicho una vez y al final del informe.

        `forma` dice si había esquemas XSD con los que comprobarla, `anclas`
        si había anclas de confianza y `listas` si había listas de
        revocación instaladas. Sin este
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
        familias = {
            informe.deteccion.familia
            for _, informe in self.informes
            if informe.deteccion is not None and informe.deteccion.familia
        }
        # El esquema solo se le puede pasar a lo que es XML. Un lote de puro
        # EDIFACT no ha visto ningún XSD, y decir que sí sería apuntarse una
        # comprobación que no se ha hecho, que es el peor error que puede
        # tener esta frase: lo que promete es de lo que se fiará quien la lee.
        con_esquema = familias - {EDIFACT}
        mirado = ["la forma contra el esquema XSD"] if forma and con_esquema else []
        if EDIFACT in familias:
            mirado.append(
                "las cuentas que EDIFACT obliga a llevar en el sobre (que el "
                "mensaje traiga los segmentos que dice traer)"
            )
        if familias & {UBL, CII, EDIFACT}:
            mirado.append(
                "las reglas EN 16931 (campos obligatorios, cuadre de totales y "
                "desglose de IVA)"
            )
        if FACTURAE in familias:
            mirado.append(
                "la aritmética del formato Facturae (líneas, totales, impuestos "
                "y cabecera de lote)"
            )
        mirado.append("el código único del RD 238/2026")
        sin_mirar = []
        if self.firmados:
            mirado.append(
                "que las firmas no estén rotas: que nadie haya tocado el "
                "documento desde que se firmó, y que la firma cuadre con el "
                "certificado que trae dentro"
            )
            if anclas:
                mirado.append(
                    "que ese certificado lleve a una autoridad de confianza "
                    "instalada"
                )
                if listas:
                    mirado.append(
                        "que no lo hayan anulado, según las listas de "
                        "revocación instaladas"
                    )
                    # Lo que queda no es un defecto del validador: ninguna
                    # lista sabe lo que pasó después de publicarse.
                    sin_mirar.append(
                        "si lo anularon después de la última lista que tengas"
                    )
                else:
                    sin_mirar.append(
                        "si el certificado está anulado —hace falta la lista "
                        "de revocación de su autoridad—"
                    )
            else:
                # Decir «firma comprobada» a secas dejaría creer que también se
                # sabe de quién es, que es la mitad que más importa.
                sin_mirar.append(
                    "de quién es el certificado ni si está revocado —lo primero "
                    "necesita anclas de confianza instaladas, lo segundo salir "
                    "a la red—"
                )
        else:
            sin_mirar.append("la validez de las firmas electrónicas")
        sin_mirar.append("si lo que dice la factura es cierto")
        return (
            "«Sin errores» quiere decir que se ha comprobado "
            + ", ".join(mirado)
            + ".\nNo se comprueba "
            + ", ni ".join(sin_mirar)
            + "."
        )

    def detalle(
        self, forma: bool = True, anclas: bool = False, listas: bool = False
    ) -> str:
        senialados = self.senialados
        lineas: list[str] = []
        for camino, informe in self.informes:
            lineas.append(str(camino))
            resumen = informe.resumen()
            if camino.name in senialados and informe.conforme:
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
        lineas.append(self.alcance(forma, anclas, listas))
        return "\n".join(lineas)


def _sangrar(texto: str, margen: str) -> str:
    return "\n".join(margen + linea for linea in texto.splitlines())


def validar_lote(
    rutas: list[str | Path],
    hoy: date | None = None,
    catalogo: Catalogo | None = None,
    almacen: Almacen | None = None,
    listas: AlmacenDeListas | None = None,
) -> InformeLote:
    """Valida varios ficheros y además los compara entre sí.

    Cada fichero se valida por su cuenta y después se juntan todas las facturas
    de todos los ficheros para las reglas de conjunto. Esa segunda pasada es la
    razón de ser de esta función: un duplicado entre dos ficheros no puede
    detectarlo ninguno de los dos por separado.
    """
    lote = InformeLote()
    # Un solo catalogo para todo el lote: asi el esquema se compila una vez y
    # no una por fichero, que es lo que de verdad cuesta.
    catalogo = catalogo or Catalogo.por_defecto()
    # Un solo almacen para todo el lote, por lo mismo que el catalogo: leer y
    # parsear las anclas una vez, no una por fichero.
    almacen = almacen if almacen is not None else Almacen.por_defecto()
    listas = listas if listas is not None else AlmacenDeListas.por_defecto()
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
        raiz, sintacticas = _arbol(datos, deteccion)
        informe = Informe(deteccion=deteccion)
        if deteccion:
            informe.incidencias.extend(
                _reglas(
                    raiz, deteccion, hoy, catalogo, almacen, listas, sintacticas
                )
            )
        lote.informes.append((camino, informe))

        # Al montón del lote solo van las facturas sujetas al reglamento
        # español. Comparar series y duplicados entre una factura holandesa y
        # una alemana no significa nada: no comparten numeración ni tienen por
        # qué. Sin este filtro salían «duplicados» entre dos suites de prueba
        # que solo tenían en común el número de ejemplo.
        if codigo_unico.obligado_en_espania(raiz, deteccion):
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
