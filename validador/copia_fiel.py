# -*- coding: utf-8 -*-
"""Qué le pasa a una factura cuando se copia a la solución pública.

Qué es una copia fiel
---------------------
Quien no emita por la solución pública tiene que mandarle una **copia fiel** de
cada factura, en UBL, a la vez que la emite (RD 238/2026, y el artículo 4 del
proyecto de orden). La factura original sigue siendo la que es —Facturae, CII,
EDIFACT—; lo que viaja a la AEAT es una copia escrita en otra sintaxis.

Esa traducción no la publica nadie. Preguntada por escrito si pensaba publicar
la correspondencia entre las sintaxis del artículo 7.1 y los campos del anexo I,
la AEAT contestó el **17-09-2026** que no: «cae en la responsabilidad de las
plataformas privadas, o en su caso, de la definición por parte del Ministerio de
Economía que regula la interconexión». Así que cada plataforma escribe la suya,
y esta es la de aquí, con sus porqués a la vista.

La respuesta trae además la regla que decide el tono de todo este módulo: un
concepto del original que no tenga equivalente **se puede omitir o llevar en una
extensión**, y «si el concepto del original no es equivalente, no se realizará
la validación del dato». Es decir: que a la copia le falte algo del original no
es un fallo de nadie. Por eso todo lo que sale de aquí es **NOTA**.

Lo que no es esto
-----------------
No es un conversor: aquí no se escribe ninguna copia. No valida la copia, que
es otro documento y se mide con sus propias reglas —las `SPFE-`—. Y no adivina
dónde se escriben en Facturae los campos españoles del anexo: el anexo los
describe en UBL, y el 10-09-2026 la AEAT anunció que cambian.

Lo que sí hace es decir cuatro cosas distintas sobre la factura que se está
mirando, y las dos últimas son las que no dice nadie:

1. **Lo que llega igual.** La mayor parte.
2. **Lo que no tiene sitio** y habrá que omitir o meter en una extensión.
3. **Lo que llega con otro número.** Los totales de Facturae no son los
   europeos: `InvoiceTotal` **resta las retenciones** y `TotalTaxOutputs`
   **suma el recargo de equivalencia**, y está en el esquema del formato, no en
   una interpretación. Quien copie campo a campo pondrá esos importes en
   `BT-112` y `BT-110` y serán otros. Medido el 20-09-2026 sobre las facturas
   de terceros que hay aquí: **6 de 14 llevan retenciones o recargo**.
4. **Lo que llega cortado de otra manera.** El dato viaja entero, pero los dos
   formatos no cortan los campos por el mismo sitio: la serie y el número son
   dos campos aquí y uno solo en la copia, y el código postal de una dirección
   de fuera de España es uno aquí y dos en la copia. Medido el mismo día sobre
   las mismas 14: **8 traen serie y 3 traen dirección de fuera**.

De dónde sale cada fila
-----------------------
De las fórmulas que el propio esquema de Facturae escribe en su documentación y
que `facturae.py` ya comprueba una a una —`FE-TOTAL`, `FE-PENDIENTE`,
`FE-EJECUTAR`—, y de dónde pone el anexo I cada importe español. Lo que no se
sabe va marcado `POR_DECIDIR` y se dice así, en vez de colocarlo donde suene
bien.

El destino de una fila no se escribe de memoria: el anexo recoge **104
términos europeos distintos** y están en `cius_es.CAMPOS`, con su nombre y su
cardinalidad. Una prueba compara la tabla con esa lista, así que un BT-
inventado o un BT- que el anexo no tenga no pasan de aquí.

Las familias, y en qué orden
----------------------------
La tabla se escribe por familias y no de una vez, porque cada una se sostiene
en una fuente distinta y alguna todavía no tiene fuente:

1. **Los importes** (20-09-2026). Se empezó por ahí porque copiar campo a campo
   no omite un dato: **cambia una cifra**, y un hueco se ve mientras que un
   número equivocado no.
2. **Lo evidente** (20-09-2026): la dirección postal, el contacto, la serie y
   las fechas. Se llama evidente porque casi todas sus filas son «llega igual»,
   y se escribe entera justamente por las que no lo son y quedan escondidas
   entre ellas: dos campos que se juntan en uno, uno que hay que partir en dos,
   y datos que el esquema de Facturae obliga a escribir y el anexo no recoge.

Quedan **80 de los 104 términos europeos sin fila** —la tabla nombra 24,
medido el 21-09-2026—, y es importante no confundir lo que falta con lo que
espera, porque no son lo mismo:

3. **Las líneas** (`BG-25`, `BG-29`, `BG-30`, `BG-31`): las traen las 14. Es
   además donde más se queda fuera —`BT-127`, `BT-128`, `BT-130`, `BT-132`,
   `BT-133`, `BT-150`, `BT-155` a `BT-159` y `BG-26` no están en el anexo—.
   Limpia del anuncio salvo la clave de régimen, cuya lista `L3A` se recorta.
4. **Los cargos y las minoraciones** (`BG-20`, `BG-21`, `BG-27`, `BG-28`): 12
   de 14 traen descuentos y 6 cargos. Facturae escribe el **porcentaje** y la
   norma pide el importe.
5. **El pago** (`BG-16`, `BG-17`): 12 de 14. Facturae admite varios
   vencimientos y la copia tiene un solo `BT-9`.
6. **Las referencias** (`BT-10`, `BG-3`, `BG-24`): el albarán en 11 y el pedido
   del comprador en 8 de 14, y el anexo **no recoge ninguna** de `BT-11` a
   `BT-19`. Se escribe sin la parte de rectificativas, que espera.

Las tres primeras y la mitad de la cuarta **el anuncio del 10-09-2026 no las
toca**, que es la razón de que vayan delante: escritas hoy no hay que
reescribirlas. Las tres que quedan sí quedan debajo de él y se escriben después:

7. **El desglose del IVA** —la `L4` gana categorías nuevas—, **la cabecera**
   —entra el `389` en la `L1`— y **las partes** —el NIF del vendedor podrá ir
   en `BT-31`, que hoy no está en el anexo, o en `BT-32` con esquema «LOC»—.

Y esperan, éstas sí porque no hay de dónde sacarlas: **los campos españoles del
anexo**, **los centros administrativos**, **el lote** y las tres filas que
están en `POR_DECIDIR`. Unas transparencias dicen qué va a cambiar, no cómo
queda redactado, y una fila cuyo porqué es una diapositiva no vale nada.

**No todas las filas sacan una nota**, y es a propósito: lo que llega igual no
se dice. Un informe que celebre cada campo que sí viaja no lo lee nadie. Sale
nota cuando hay algo que decidir, algo que cambia de valor o algo que se queda
fuera.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from validador.formato import FACTURAE, Deteccion
from validador.incidencias import NOTA, Incidencia
from validador.sintaxis import a_decimal

# Qué le pasa a un concepto al copiarse. Son siete estados y ninguno sobra: la
# tentación es juntarlos en «llega» y «no llega», y eso borra justo lo que hay
# que decidir.
#
#   - «no se sabe» no es «no tiene sitio»: el primero se resuelve leyendo el
#     anexo nuevo cuando salga, el segundo no se resuelve.
#   - «cortado de otra manera» no es «llega igual»: el dato viaja entero, pero
#     los dos formatos no cortan los campos por el mismo sitio y quien copia
#     tiene que decidir dónde pega o por dónde parte. Pasa en las dos
#     direcciones, y las dos están medidas más abajo.
#   - «el anexo no lo pide» no es «no tiene sitio»: la norma sí tiene el
#     término y la copia sitio donde escribirlo; lo que no hay es un campo del
#     anexo, así que llega y no lo mira nadie.
IGUAL = "llega igual"
APARTE = "llega, pero en la extensión española"
CAMBIA = "llega con otro número"
OTRO_CORTE = "llega, pero cortado de otra manera"
NO_LO_PIDEN = "llega, pero el anexo no lo pide"
SIN_SITIO = "no tiene sitio"
POR_DECIDIR = "no se sabe todavía"


@dataclass(frozen=True)
class Correspondencia:
    """Una fila de la tabla: de dónde sale, adónde va y qué le pasa."""

    concepto: str
    facturae: str  # el elemento de Facturae, tal y como lo llama su esquema
    destino: str  # el término europeo o el campo del anexo
    efecto: str
    porque: str


# La primera familia: los importes. Se empieza por aquí porque es donde copiar
# campo a campo no omite un dato, sino que **cambia una cifra**, que es peor:
# un hueco se ve y un número equivocado no.
CORRESPONDENCIAS: tuple[Correspondencia, ...] = (
    Correspondencia(
        "base antes de impuestos", "TotalGrossAmountBeforeTaxes", "BT-109", IGUAL,
        "las dos son el importe bruto menos descuentos más cargos generales",
    ),
    Correspondencia(
        "cuotas repercutidas", "TotalTaxOutputs", "BT-110", CAMBIA,
        "el esquema de Facturae dice «sumatorio de todas las cuotas y recargos "
        "repercutidos»: lleva dentro el recargo de equivalencia, que en el "
        "anexo va en su propio grupo y no en la cuota de IVA",
    ),
    Correspondencia(
        "total de la factura", "InvoiceTotal", "BT-112", CAMBIA,
        "el esquema lo define como base más repercutidos **menos retenidos**, y "
        "BT-112 es base más cuotas: la retención no es un impuesto de la "
        "factura para la norma europea",
    ),
    Correspondencia(
        "anticipos", "TotalPaymentsOnAccount", "BT-113", IGUAL,
        "lo ya pagado antes de emitir, que la norma también tiene",
    ),
    Correspondencia(
        "total a pagar", "TotalExecutableAmount", "BT-115", POR_DECIDIR,
        "es el que más se le parece —descuenta retenciones y suma suplidos y "
        "gastos financieros—, pero el anexo manda sumar los importes de "
        "terceros «junto con» el total con IVA y esa cuenta no se puede "
        "comprobar todavía: es la misma duda de SPFE-TOTAL-A-PAGAR",
    ),
    Correspondencia(
        "retenciones de impuestos", "TotalTaxesWithheld", "anexo I: suma de retenciones",
        APARTE,
        "la norma europea no tiene término para la retención; el anexo sí, con "
        "su base, su tipo y su concepto",
    ),
    Correspondencia(
        "importes retenidos", "AmountsWithheld", "anexo I: retención aplicada",
        POR_DECIDIR,
        "Facturae distingue la retención de impuestos de otros importes "
        "retenidos —la retención de garantía de una obra, por ejemplo— y el "
        "anexo describe un solo grupo de retención: si el segundo cabe ahí no "
        "lo dice nadie",
    ),
    Correspondencia(
        "recargo de equivalencia", "EquivalenceSurchargeAmount",
        "anexo I: recargo de equivalencia", APARTE,
        "el anexo le da grupo propio, con base, tipo y cuota, fuera de la cuota "
        "de IVA",
    ),
    Correspondencia(
        "suplidos", "TotalReimbursableExpenses", "BG-34 (BT-179 y BT-180)", POR_DECIDIR,
        "los importes de terceros son términos de la edición de 2026 de la "
        "norma, y el anexo de abril no les da ruta: hasta que salga el texto "
        "nuevo no se sabe dónde se escriben",
    ),
    Correspondencia(
        "gastos financieros", "TotalFinancialExpenses", "", SIN_SITIO,
        "ni la norma europea ni el anexo tienen dónde ponerlos",
    ),
    Correspondencia(
        "subvenciones", "Subsidies", "", SIN_SITIO,
        "restan del total a pagar en Facturae y no tienen término europeo; "
        "quien copie tendrá que dejarlas fuera o inventarse una extensión",
    ),

    # Segunda familia: lo evidente. La dirección postal y el contacto son las
    # filas que cualquiera daría por supuestas, y están escritas por las tres
    # que hay entre medias y que nadie da por supuestas: la serie, la dirección
    # de fuera de España y el periodo de facturación.
    Correspondencia(
        "serie y número", "InvoiceSeriesCode", "BT-1", OTRO_CORTE,
        "Facturae los guarda en dos elementos y el anexo tiene **un solo "
        "campo** para los dos, que llama «número y serie de la factura»: en la "
        "copia van juntos, y nadie dice cómo se juntan. Aquí se pegan sin "
        "separador, que es como los trata Verifactu y como los junta el código "
        "único de esta misma herramienta —`CodigoUnico.numero_completo`—. Si "
        "la copia llevara solo el número, la copia y el original no "
        "identificarían la misma factura. Medido el 20-09-2026: 8 de las 14 "
        "facturas de aquí traen serie con texto",
    ),
    Correspondencia(
        "fecha de operación", "OperationDate", "BT-7", IGUAL,
        "es el único sitio que hay: el anexo no recoge BT-72, la fecha de "
        "entrega. Y le cambia el nombre al término —en la norma BT-7 es la "
        "fecha de devengo del IVA, que no siempre es la de la operación—, pero "
        "lo define con la misma condición que el esquema de Facturae: la fecha "
        "de la operación cuando no sea la de expedición. Por eso el mapa de "
        "sintaxis deja la de devengo sin ruta en Facturae y aquí sí hay "
        "destino: allí se lee la norma, y aquí se lee el anexo",
    ),
    Correspondencia(
        "calle", "Address", "BT-35 del vendedor, BT-50 del comprador", IGUAL,
        "una línea de texto a una línea de texto; el anexo no recoge la "
        "segunda línea de la dirección y Facturae tampoco la tiene",
    ),
    Correspondencia(
        "población", "Town", "BT-37 del vendedor, BT-52 del comprador", IGUAL,
        "el anexo pide el municipio, y lo hace obligatorio cuando la dirección "
        "está en España",
    ),
    Correspondencia(
        "código postal", "PostCode", "BT-38 del vendedor, BT-53 del comprador",
        IGUAL,
        "igual de obligatorio que la población cuando la dirección está en "
        "España",
    ),
    Correspondencia(
        "provincia", "Province", "BT-39 del vendedor, BT-54 del comprador",
        IGUAL,
        "el término europeo es la subdivisión del país, y el anexo escribe «se "
        "consignará la provincia»: es el mismo campo con otro nombre",
    ),
    Correspondencia(
        "país", "CountryCode", "BT-40 del vendedor, BT-55 del comprador", IGUAL,
        "los dos usan los códigos de ISO 3166-1, y de lo que ISO ya retiró se "
        "encarga `paises.py`",
    ),
    Correspondencia(
        "código postal y población de fuera de España", "PostCodeAndTown",
        "BT-38 y BT-37 del vendedor, BT-53 y BT-52 del comprador", OTRO_CORTE,
        "la dirección de fuera de España los junta en **un solo elemento** y la "
        "copia los pide en dos campos: hay que partir la cadena, y ni el "
        "esquema de Facturae ni el anexo dicen por dónde. Medido el "
        "20-09-2026: 3 de las 14 facturas de aquí llevan una",
    ),
    Correspondencia(
        "persona de contacto", "ContactPersons",
        "BT-41 del vendedor, BT-56 del comprador", NO_LO_PIDEN,
        "la norma tiene el término y el anexo no lo lista: en su grupo de "
        "contacto solo están el teléfono y el correo. Llega a la copia porque "
        "la sintaxis tiene dónde escribirlo, y no es contenido que la solución "
        "pública pida ni mire",
    ),
    Correspondencia(
        "teléfono", "Telephone", "BT-42 del vendedor, BT-57 del comprador",
        IGUAL,
        "el anexo lo recoge para las dos partes, y es el mismo dato",
    ),
    Correspondencia(
        "correo electrónico", "ElectronicMail",
        "BT-43 del vendedor, BT-58 del comprador", IGUAL,
        "el anexo lo recoge para las dos partes, y es el mismo dato. Ojo con "
        "confundirlo con la dirección electrónica de la parte (BT-34 y BT-49), "
        "que es a dónde se manda la factura y no está en el anexo",
    ),
    Correspondencia(
        "fax", "TeleFax", "", SIN_SITIO,
        "no hay término para el fax entre los 104 que recoge el anexo, ni "
        "equivalente en la norma",
    ),
    Correspondencia(
        "página web", "WebAddress", "", SIN_SITIO,
        "la dirección web de una parte no es contenido de la factura para el "
        "anexo: no está entre sus términos",
    ),
    Correspondencia(
        "CNAE", "CnoCnae", "", SIN_SITIO,
        "el código de la actividad económica es un dato español de la parte, y "
        "el anexo —que es español— tampoco lo recoge",
    ),
    Correspondencia(
        "otros datos de contacto", "AdditionalContactDetails", "", SIN_SITIO,
        "texto libre de Facturae para lo que no cabe en los demás campos de "
        "contacto; sin equivalente y sin destino",
    ),
    Correspondencia(
        "idioma", "LanguageName", "", SIN_SITIO,
        "Facturae declara en qué idioma está escrita la factura y el anexo no "
        "tiene campo para eso. Medido el 20-09-2026: 11 de las 14 facturas de "
        "aquí lo traen, y se queda en el original",
    ),
    Correspondencia(
        "lugar de expedición", "PlaceOfIssue", "", SIN_SITIO,
        "la plaza donde se expide el documento no es la dirección del vendedor "
        "y no tiene campo en el anexo. Medido: 8 de las 14 lo traen",
    ),
    Correspondencia(
        "periodo de facturación", "InvoicingPeriod", "BG-14 (BT-73 y BT-74)",
        NO_LO_PIDEN,
        "la norma tiene el grupo y el anexo de abril no lo recoge, y no es un "
        "dato menor: el esquema de Facturae lo hace **obligatorio** en las "
        "recapitulativas y en el servicio prestado temporalmente. Medido: 9 de "
        "las 14 facturas de aquí lo traen",
    ),
)

# Lo que la tabla tiene que cubrir para que las reglas de abajo no hablen de
# nada. Es el cepo de este módulo: si alguien quita una fila y deja la regla,
# el paquete no se monta. Un comentario pidiendo memoria no lo evitaría.
_LO_QUE_SE_MIRA = (
    "TotalTaxOutputs", "InvoiceTotal", "TotalTaxesWithheld",
    "EquivalenceSurchargeAmount", "TotalReimbursableExpenses",
    "TotalFinancialExpenses", "Subsidies",
    "InvoiceSeriesCode", "PostCodeAndTown",
    "LanguageName", "PlaceOfIssue",
    "TeleFax", "WebAddress", "CnoCnae", "AdditionalContactDetails",
)


class TablaIncompleta(Exception):
    """La tabla ya no cubre lo que las reglas dicen mirar."""


def _comprobar_la_tabla() -> None:
    escritos = {fila.facturae for fila in CORRESPONDENCIAS}
    faltan = [nombre for nombre in _LO_QUE_SE_MIRA if nombre not in escritos]
    if faltan:
        raise TablaIncompleta(
            "las reglas de la copia fiel miran campos que ya no están en la "
            "tabla de correspondencias: " + ", ".join(faltan) + ". O vuelve la "
            "fila, o se quita la regla: una queja sin su porqué escrito no sale "
            "de aquí."
        )


_comprobar_la_tabla()


def _hijos(nodo, *nombres: str) -> list:
    actuales = [nodo]
    for nombre in nombres:
        siguientes = []
        for uno in actuales:
            siguientes.extend(uno.xpath(f"./*[local-name()='{nombre}']"))
        actuales = siguientes
    return actuales


def _numero(nodo, *nombres: str) -> Decimal:
    for encontrado in _hijos(nodo, *nombres):
        cantidad = a_decimal((encontrado.text or "").strip())
        if cantidad is not None:
            return cantidad
    return Decimal(0)


def _texto(nodo, *nombres: str) -> str:
    for encontrado in _hijos(nodo, *nombres):
        escrito = (encontrado.text or "").strip()
        if escrito:
            return escrito
    return ""


# Lo que se queda en el original, y cómo se llama en el informe. Se imprime el
# concepto y no el elemento: quien lee el informe tiene delante su factura, no
# el esquema de Facturae. Van en dos listas porque cuelgan de sitios distintos
# —unos de cada factura y otros de las partes, que son del fichero entero— y
# la ruta se escribe entera, sin buscar por todo el documento: un `PostCode`
# suelto vive en dos sitios que no significan lo mismo.
_SIN_SITIO_EN_LA_FACTURA = (
    (("InvoiceIssueData", "LanguageName"), "idioma"),
    (("InvoiceIssueData", "PlaceOfIssue"), "lugar de expedición"),
)
_SIN_SITIO_EN_LAS_PARTES = (
    ("TeleFax", "fax"),
    ("WebAddress", "página web"),
    ("CnoCnae", "CNAE"),
    ("AdditionalContactDetails", "otros datos de contacto"),
)


def _suma_profunda(nodo, nombre: str) -> Decimal:
    """Lo que suman todos los elementos con ese nombre, estén donde estén.

    El recargo de equivalencia se declara por tipo impositivo, así que hay uno
    por cada línea del desglose y el documento no trae su total.
    """
    total = Decimal(0)
    for encontrado in nodo.xpath(f".//*[local-name()='{nombre}']"):
        cantidad = a_decimal(" ".join(encontrado.itertext()).strip())
        if cantidad is not None:
            total += cantidad
    return total


def _fmt(cantidad: Decimal) -> str:
    return f"{cantidad:.2f}"


def _de_una_factura(
    factura, etiqueta: str, del_documento: tuple[str, ...] = ()
) -> list[Incidencia]:
    incidencias = []

    # La serie va antes del corte de los totales a propósito: no depende de
    # ellos. Una factura sin `InvoiceTotals` es inválida por esquema y el
    # informe ya lo dice por su cuenta, pero su número sigue siendo su número.
    serie = _texto(factura, "InvoiceHeader", "InvoiceSeriesCode")
    numero = _texto(factura, "InvoiceHeader", "InvoiceNumber")
    if serie and numero:
        incidencias.append(
            Incidencia(
                "COPIA-SERIE",
                NOTA,
                "En la copia, el número de esta factura no es el que lleva "
                "aquí. Facturae guarda la serie y el número en dos campos, y "
                "el anexo tiene uno solo —BT-1, «número y serie de la "
                "factura»—. Nadie dice cómo se juntan: aquí se pegan sin "
                "separador, que es como los trata Verifactu y como los junta "
                "el código único. Si la copia llevara solo el número, la copia "
                "y el original no identificarían la misma factura.",
                campo=f"{etiqueta}Número de factura (BT-1 en la copia)",
                esperado=f"{serie}{numero} en la copia: serie y número juntos",
                encontrado=f"{numero} en esta factura, con la serie {serie} "
                           f"en su propio campo",
            )
        )

    totales = _hijos(factura, "InvoiceTotals")
    if not totales:
        return incidencias
    totales = totales[0]
    base = _numero(totales, "TotalGrossAmountBeforeTaxes")
    repercutido = _numero(totales, "TotalTaxOutputs")
    retenido = _numero(totales, "TotalTaxesWithheld")
    total = _numero(totales, "InvoiceTotal")
    suplidos = _numero(totales, "TotalReimbursableExpenses")
    financieros = _numero(totales, "TotalFinancialExpenses")
    recargo = _suma_profunda(factura, "EquivalenceSurchargeAmount")
    # El documento no trae el total de las subvenciones: hay un bloque por
    # cada una, como con el recargo.
    subvenciones = Decimal(0)
    for grupo in _hijos(totales, "Subsidies"):
        subvenciones += _suma_profunda(grupo, "SubsidyAmount")

    if recargo:
        # BT-110 es la suma de las cuotas de IVA y nada más. El recargo tiene
        # grupo propio en el anexo, así que sale de aquí.
        incidencias.append(
            Incidencia(
                "COPIA-CUOTA",
                NOTA,
                "La cuota que lleva esta factura no es la que iría en la copia. "
                "El total de impuestos repercutidos de Facturae suma también el "
                "recargo de equivalencia, y en la copia el recargo va en su "
                "propio grupo, fuera de la cuota de IVA.",
                # Sin flechas ni nada fuera del latín de siempre: esto se
                # imprime en consolas que todavía hablan cp1252, y un carácter
                # que no esté ahí no sale mal: revienta el informe entero.
                campo=f"{etiqueta}Total de impuestos repercutidos (BT-110 en la copia)",
                # Con «en la copia» y «en esta factura» pegados al número: el
                # informe rotula estas dos líneas «Debería ser» y «Tiene», y
                # sin el añadido se leería que la factura está mal, que es
                # justo lo contrario de lo que dice la nota.
                esperado=f"{_fmt(repercutido - recargo)} en la copia, sin el recargo",
                encontrado=f"{_fmt(repercutido)} en esta factura, "
                           f"con {_fmt(recargo)} de recargo dentro",
            )
        )
    if retenido or recargo:
        # BT-112 es base más cuotas de IVA. Ni la retención se resta —no es un
        # impuesto de la factura para la norma— ni el recargo se suma ahí.
        europeo = base + repercutido - recargo
        detalle = f"{_fmt(total)} en esta factura"
        if retenido:
            detalle += f", que ya tiene restados {_fmt(retenido)} de retenciones"
        incidencias.append(
            Incidencia(
                "COPIA-TOTAL",
                NOTA,
                "El total de esta factura no es el que iría en la copia. El "
                "total de Facturae resta las retenciones, y el total con "
                "impuestos de la copia es la base más las cuotas de IVA: la "
                "retención viaja aparte, en la extensión española.",
                campo=f"{etiqueta}Total factura (BT-112 en la copia)",
                esperado=f"{_fmt(europeo)} en la copia: base más cuotas de IVA",
                encontrado=detalle,
            )
        )
    if suplidos:
        incidencias.append(
            Incidencia(
                "COPIA-SUPLIDO",
                NOTA,
                "Esta factura lleva suplidos, y no se sabe dónde se escriben en "
                "la copia. Son importes de terceros: términos de la edición de "
                "2026 de la norma europea, y el anexo I de abril no les da "
                "ruta. El 10-09-2026 la AEAT dijo que el anexo nuevo los usa, "
                "pero ese texto no está publicado.",
                campo=f"{etiqueta}Total de suplidos",
                encontrado=_fmt(suplidos),
            )
        )
    # Todo lo que se queda fuera, en **una** nota. Cinco notas seguidas
    # diciendo cada una «esto tampoco» no las lee nadie, y lo que hay que saber
    # es la lista entera de un vistazo. Los importes van con su cifra porque un
    # importe que se queda fuera ya no cuadra con ningún total de la copia; los
    # demás son datos y basta con nombrarlos.
    se_quedan = []
    if financieros:
        se_quedan.append(f"gastos financieros ({_fmt(financieros)})")
    if subvenciones:
        se_quedan.append(f"subvenciones ({_fmt(subvenciones)})")
    for ruta, concepto in _SIN_SITIO_EN_LA_FACTURA:
        if _hijos(factura, *ruta):
            se_quedan.append(concepto)
    se_quedan.extend(del_documento)
    if se_quedan:
        incidencias.append(
            Incidencia(
                "COPIA-SIN-SITIO",
                NOTA,
                "Esta factura lleva datos que en la copia no tienen dónde "
                "ponerse: no hay término de la norma que les corresponda ni "
                "campo del anexo donde escribirlos. Se pueden omitir o llevar "
                "en una extensión, que es lo que contestó la AEAT el "
                "17-09-2026 para los conceptos sin equivalente.",
                campo=f"{etiqueta}Lo que se queda en el original",
                encontrado=", ".join(se_quedan),
            )
        )
    return incidencias


def _de_las_partes(raiz) -> tuple[str, ...]:
    """Lo que no tiene sitio y vive en las partes, no en cada factura.

    Se busca por debajo de `Parties` y no en todo el documento: así cuenta
    también lo que cuelgue de un centro administrativo —que tampoco viaja— sin
    arrastrar nada de fuera.
    """
    encontrados = []
    for elemento, concepto in _SIN_SITIO_EN_LAS_PARTES:
        if raiz.xpath(
            f"./*[local-name()='Parties']//*[local-name()='{elemento}']"
        ):
            encontrados.append(concepto)
    return tuple(encontrados)


def _direcciones_de_fuera(raiz) -> list[Incidencia]:
    """Las direcciones de fuera de España, que juntan el código postal y la
    población en un solo campo.

    Solo las de las partes. Un centro administrativo también puede tener la
    suya —medido el 20-09-2026: 3 de las 6 direcciones de fuera que hay aquí
    cuelgan de uno—, y esa no tiene este destino: del centro, el anexo se queda
    con sus tres identificadores y no con su domicilio. Es otra familia y
    espera al texto nuevo.
    """
    incidencias = []
    for parte, quien, postal, poblacion in (
        ("SellerParty", "del vendedor", "BT-38", "BT-37"),
        ("BuyerParty", "del comprador", "BT-53", "BT-52"),
    ):
        for juntos in raiz.xpath(
            f"./*[local-name()='Parties']/*[local-name()='{parte}']"
            f"/*[local-name()='LegalEntity' or local-name()='Individual']"
            f"/*[local-name()='OverseasAddress']"
            f"/*[local-name()='PostCodeAndTown']"
        ):
            escrito = (juntos.text or "").strip()
            if not escrito:
                continue
            incidencias.append(
                Incidencia(
                    "COPIA-DIRECCION",
                    NOTA,
                    "La dirección de fuera de España junta el código postal y "
                    "la población en un solo campo, y la copia los pide en "
                    "dos. Hay que partir la cadena, y ni el esquema de "
                    "Facturae ni el anexo dicen por dónde: lo decide quien "
                    "copia.",
                    campo=f"Código postal y población {quien} "
                          f"({postal} y {poblacion} en la copia)",
                    esperado="dos campos en la copia",
                    encontrado=f"{escrito}, en uno solo",
                )
            )
    return incidencias


def reglas(raiz, deteccion: Deteccion) -> list[Incidencia]:
    """Lo que le pasaría a este documento al copiarlo a la solución pública.

    Solo sobre Facturae, que es donde la copia cambia números. En CII y en
    EDIFACT la correspondencia con la norma la publica CEN y los importes son
    los mismos; en UBL no hay nada que copiar.
    """
    if raiz is None or not deteccion or deteccion.familia != FACTURAE:
        return []
    if raiz.xpath("local-name()") != "Facturae":
        internos = raiz.xpath("//*[local-name()='Facturae']")
        if not internos:
            return []
        raiz = internos[0]
    facturas = _hijos(raiz, "Invoices", "Invoice")
    # Lo de las partes se busca una vez y se repite en cada factura del
    # fichero: las partes son las mismas para todas, y la copia de cada una se
    # las lleva igual de incompletas.
    del_documento = _de_las_partes(raiz)
    incidencias = list(_direcciones_de_fuera(raiz))
    for numero, factura in enumerate(facturas, 1):
        etiqueta = f"Factura {numero}: " if len(facturas) > 1 else ""
        incidencias.extend(_de_una_factura(factura, etiqueta, del_documento))
    return incidencias
