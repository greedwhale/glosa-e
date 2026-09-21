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
5. **Lo que llega con otro código.** Facturae escribe listas suyas donde la
   norma pide las europeas, y eso no es una sospecha: el binding ya lo tiene
   reconocido en `sintaxis.SINTAXIS_FACTURAE.codigos_con_otra_lista`, que
   silencia cuatro reglas `BR-CL-` para no acusar a todas las facturas de la
   sintaxis de algo que es de la sintaxis. Lo que allí se calla, aquí se dice:
   **qué hay que escribir en la copia**. Medido el 21-09-2026: **11 de las 14
   llevan unidad de medida, y las 18 líneas que la traen escriben `01`**, que
   en la lista de Facturae es «Units» y en la copia es `C62`. Y el peor de los
   cuatro es el medio de pago, porque no se ve: los **19 códigos de Facturae
   existen los 19 en UNCL4461** queriendo decir otra cosa, así que el dígito
   copiado pasa la validación diciendo que se paga de otra manera.

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

3. **Las líneas** (21-09-2026): lo que se factura, con su cantidad, su precio
   y su IVA. Las traen las 14, y esconde tres cosas que desde los totales no
   se ven: un campo que **la copia pide y la factura no tiene** —el
   identificador de línea—, un importe que se puede copiar del campo de al
   lado y parecer bueno —`GrossAmount` y `TotalCost` no valen lo mismo en 6 de
   las 14— y dos códigos escritos en otro vocabulario. Las referencias que
   Facturae mete **dentro** de la línea no son de esta familia: son las mismas
   que las del documento y se escriben con ellas, que si no la misma historia
   se cuenta dos veces a medias.

4. **Los cargos y las minoraciones** (21-09-2026): los de línea y los del
   documento. Casi todo pasa sin discusión —el importe, el motivo, las tres
   sumas— y lo que no pasa es **el IVA de los generales**: la norma agrupa las
   minoraciones del documento por categoría de IVA y Facturae las aplica sobre
   la base entera, sin IVA propio. Con una categoría la cuenta está forzada;
   con dos hay que repartir. Medido: 6 de 14 llevan alguno, y **una** tiene más
   de una categoría.

5. **El pago** (21-09-2026): dónde y cómo se cobra. Trae el choque más feo
   de la tabla: los **19 códigos de medio de pago de Facturae existen los 19**
   en la lista europea queriendo decir otra cosa, así que el dígito copiado no
   da un error, da una factura que dice que se paga de otra manera. Medido: 12
   de 14 traen medio de pago.

Quedan **46 de los 104 términos europeos sin fila** —la tabla nombra 58,
medido el 21-09-2026—, y es importante no confundir lo que falta con lo que
espera, porque no son lo mismo:

6. **Las referencias** (`BT-10`, `BG-3`, `BG-24`): el albarán en 11 y el pedido
   del comprador en 8 de 14, y el anexo **no recoge ninguna** de `BT-11` a
   `BT-19`. Se escribe sin la parte de rectificativas, que espera.

La mitad de la primera **el anuncio del 10-09-2026 no la toca**, que es la
razón de que vaya delante: escrita hoy no hay que reescribirla. Las tres que
quedan sí quedan debajo de él y se escriben después:

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
#   - «el código es de otra lista» no es «llega igual»: el dato viaja, el campo
#     existe en los dos sitios y el valor **no vale**, porque cada formato lo
#     escribe con su vocabulario. Copiarlo tal cual pone en la copia un código
#     que su lista no tiene.
#   - «lo pone quien copia» es la única fila que no sale de la factura: el
#     anexo pide un campo que Facturae no tiene, así que la copia se lo
#     inventa. Se escribe porque inventárselo mal —o distinto cada vez— rompe
#     la correspondencia entre la copia y el original, y eso no lo avisa nadie.
IGUAL = "llega igual"
APARTE = "llega, pero en la extensión española"
CAMBIA = "llega con otro número"
OTRO_CORTE = "llega, pero cortado de otra manera"
NO_LO_PIDEN = "llega, pero el anexo no lo pide"
OTRA_LISTA = "llega, pero el código es de otra lista"
SE_INVENTA = "no está en la factura: lo pone quien copia"
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

    # La tercera familia: las líneas. Es la más larga de las tres y la que más
    # se queda fuera, pero lo que la hace útil son tres filas: un campo que la
    # copia pide y la factura no tiene, un importe que se puede copiar del
    # sitio equivocado, y dos códigos escritos en otro idioma.
    #
    # Las referencias que Facturae mete **dentro** de la línea -pedido,
    # contrato, expediente, albarán- no están aquí a propósito: son las mismas
    # que las del documento, el anexo tampoco las recoge, y contarlas dos veces
    # partiría en dos una historia que se entiende de una pieza. Van con la
    # familia de las referencias.
    Correspondencia(
        "identificador de línea", "(no lo tiene)", "BT-126", SE_INVENTA,
        "el anexo pide un identificador por línea y Facturae no tiene ninguno. "
        "Su esquema da `SequenceNumber`, pero significa otra cosa -el orden de "
        "la línea en un pedido-, es opcional y casi nadie lo escribe: 11 de las "
        "14 facturas de aquí no traen ni uno. Así que lo pone quien copia, y "
        "tiene que ponerlo **siempre igual**: si la misma factura se copia hoy "
        "con las líneas numeradas de una manera y mañana de otra, las dos "
        "copias dicen cosas distintas del mismo original. `BR-21` ya avisa de "
        "que aquí no está, y por eso esta fila no saca nota propia",
    ),
    Correspondencia(
        "nombre del artículo", "ItemDescription", "BT-153", IGUAL,
        "el anexo tiene dos campos -BT-153 el nombre y BT-154 la descripción- "
        "y Facturae tiene uno. El que es obligatorio en los dos sitios es el "
        "nombre, así que ahí va; BT-154 se queda vacío, que es lo que hay que "
        "hacer con un campo opcional sin origen",
    ),
    Correspondencia(
        "cantidad", "Quantity", "BT-129", IGUAL,
        "mismo dato y obligatorio en los dos esquemas",
    ),
    Correspondencia(
        "unidad de medida", "UnitOfMeasure",
        "BT-129 (el atributo de la cantidad)", OTRA_LISTA,
        "dos cosas a la vez, y las dos hay que hacerlas. En la copia no hay "
        "campo propio -BT-130 no está en el anexo, que mete la unidad en un "
        "atributo de BT-129-, y el código **no es el mismo vocabulario**: "
        "Facturae tiene su lista de 36 valores de dos dígitos y la norma pide "
        "UN/ECE, recomendaciones 20 y 21. Medido el 21-09-2026 sobre el propio "
        "esquema de Facturae: de sus 36 códigos, 13 llevan el europeo en su "
        "etiqueta y vale tal cual, 16 lo llevan pero hay que ponerle una `X` "
        "delante -son códigos de embalaje, de la 21-, 1 solo cuadra en "
        "mayúsculas (`KWh`) y **6 no lo llevan en absoluto**. Entre esos seis "
        "está `01`, «Units», que es justo el que escriben las 18 líneas "
        "medidas aquí: en la copia es `C62`, y eso lo decide quien copia",
    ),
    Correspondencia(
        "precio unitario", "UnitPriceWithoutTax", "BT-146", IGUAL,
        "el precio neto del artículo, sin impuestos, en los dos sitios",
    ),
    Correspondencia(
        "importe neto de la línea", "GrossAmount", "BT-131", IGUAL,
        "y es `GrossAmount` pese al nombre, no `TotalCost`: el esquema define "
        "`TotalCost` como cantidad por precio y `GrossAmount` como "
        "«TotalCost - DiscountAmount + ChargeAmount», y BT-131 es el importe "
        "de la línea **después** de sus descuentos. El que cuadra con la suma "
        "de líneas es el segundo. Copiar el primero no deja un hueco: deja un "
        "número que parece bueno y no lo es. Medido: en 6 de las 14 los dos "
        "campos no valen lo mismo",
    ),
    Correspondencia(
        "categoría de IVA de la línea", "TaxTypeCode", "BT-151", OTRA_LISTA,
        "el mismo hueco que un piso más arriba: Facturae dice **qué impuesto "
        "es** -01 IVA, 03 IGIC- y la norma pide de qué **categoría** es -S, Z, "
        "E, AE, K- en la lista UNCL5305. No es traducir un código por otro: "
        "hay que deducirlo del impuesto y del tipo, y el validador ya lo hace "
        "para poder correr las BR-S-*",
    ),
    Correspondencia(
        "tipo de IVA de la línea", "TaxRate", "BT-152", IGUAL,
        "el porcentaje, que es un número y no un código",
    ),
    Correspondencia(
        "clave de régimen", "SpecialTaxableEventCode", "BG-32 (BT-160 y BT-161)",
        APARTE,
        "el anexo le da grupo propio, con el nombre de la propiedad en BT-160 "
        "y el código en BT-161, y su lista es la española L3A. Ojo al "
        "copiarla: el 10-09-2026 la AEAT anunció que **L3A se recorta** -fuera "
        "el régimen simplificado, el recargo de equivalencia y el de "
        "agricultura, ganadería y pesca-, así que ésta es la única fila de "
        "esta familia que el texto nuevo puede mover. Medido: 3 de 14",
    ),
    Correspondencia(
        "nota de la línea", "AdditionalLineItemInformation", "BT-127",
        NO_LO_PIDEN,
        "la norma tiene la nota de línea y el anexo no la recoge. Medido: 6 de "
        "14, y es donde Facturae deja lo que no cabe en otro sitio",
    ),
    Correspondencia(
        "código de artículo", "ArticleCode", "BT-155", NO_LO_PIDEN,
        "es el código que le da el vendedor a lo que vende, BT-155, y el anexo "
        "no recoge ninguno de los identificadores de artículo: ni el del "
        "vendedor, ni el del comprador (BT-156), ni el normalizado (BT-157), "
        "ni la clasificación (BT-158). Medido: 3 de 14",
    ),
    Correspondencia(
        "fecha de la línea", "TransactionDate", "BG-26 (BT-134 y BT-135)",
        NO_LO_PIDEN,
        "cuándo se hizo lo de esa línea. La norma tiene el periodo de línea y "
        "el anexo no lo recoge, igual que no recoge el del documento. Medido: "
        "3 de 14",
    ),

    # La cuarta familia: los cargos y las minoraciones. Facturae los pone en
    # dos sitios -en la línea y sobre el total- y la norma también, así que la
    # mayor parte pasa sin discusión. Lo que no pasa es **el IVA de los
    # generales**: la norma clasifica cada descuento del documento por
    # categoría de IVA y Facturae no clasifica ninguno, porque los aplica
    # antes del desglose y sobre la base entera.
    Correspondencia(
        "descuento general", "GeneralDiscounts", "BG-20 (BT-92, BT-95 y BT-96)",
        OTRO_CORTE,
        "el importe pasa sin discusión, pero el grupo no: la norma tiene **un "
        "grupo de minoraciones por categoría de IVA** -de ahí que BT-95 y "
        "BT-96 vayan dentro- y Facturae tiene un descuento sobre el total, sin "
        "IVA propio. Con una sola categoría en la factura la cuenta está "
        "forzada y no hay nada que decidir; con dos o más hay que **repartir** "
        "el descuento entre ellas y ningún texto dice cómo. Medido el "
        "21-09-2026: 6 de las 14 llevan descuento o cargo general, y de esas "
        "**una** tiene más de una categoría",
    ),
    Correspondencia(
        "cargo general", "GeneralSurcharges", "BG-21 (BT-99, BT-102 y BT-103)",
        OTRO_CORTE,
        "lo mismo que el descuento general y por lo mismo: en la norma el "
        "cargo del documento lleva su categoría de IVA y su tipo, y el de "
        "Facturae se aplica sobre la base entera. Medido: 2 de 14",
    ),
    Correspondencia(
        "porcentaje del descuento", "DiscountRate", "BT-94 y BT-138",
        NO_LO_PIDEN,
        "Facturae define el descuento con un porcentaje y un importe, y el "
        "anexo no recoge ni el porcentaje ni la base sobre la que se calcula "
        "-BT-93 y BT-137 tampoco están-. A la copia llega el importe, que es "
        "lo que cuadra las cuentas; de dónde salía, no. Medido: 12 de 14 "
        "escriben el porcentaje en alguna línea",
    ),
    Correspondencia(
        "porcentaje del cargo", "ChargeRate", "BT-101 y BT-143", NO_LO_PIDEN,
        "el mismo caso que el del descuento, en el otro sentido. Medido: 3 de 14",
    ),
    Correspondencia(
        "motivo del descuento", "DiscountReason",
        "BT-97 en el documento, BT-139 en la línea", IGUAL,
        "el texto del motivo pasa igual en los dos niveles. El **código** del "
        "motivo -BT-98, BT-105, BT-140 y BT-145- no está en el anexo, y aquí "
        "no se pierde nada: Facturae tampoco lo tiene. Medido: 12 de 14 "
        "escriben el motivo",
    ),
    Correspondencia(
        "motivo del cargo", "ChargeReason",
        "BT-104 en el documento, BT-144 en la línea", IGUAL,
        "igual que el del descuento. Medido: 6 de 14",
    ),
    Correspondencia(
        "descuentos de la línea", "DiscountsAndRebates", "BG-27 (BT-136 y BT-139)",
        IGUAL,
        "el grupo existe en los dos sitios y con el mismo sentido. Ojo a que "
        "hay que escribirlo **dos veces** en la copia: como grupo propio y "
        "restado dentro de BT-131, que es el importe neto de la línea. Es la "
        "misma cuenta que hace `GrossAmount` aquí. Medido: 12 de 14",
    ),
    Correspondencia(
        "cargos de la línea", "Charges", "BG-28 (BT-141 y BT-144)", IGUAL,
        "lo mismo que los descuentos de línea, sumando en vez de restar. "
        "Medido: 6 de 14",
    ),
    Correspondencia(
        "suma de las líneas", "TotalGrossAmount", "BT-106", IGUAL,
        "el esquema lo define como la suma de los importes brutos de los "
        "detalles, que es exactamente la suma de los importes netos de línea "
        "de la norma: los dos van después de los descuentos de cada línea y "
        "antes de los generales",
    ),
    Correspondencia(
        "suma de descuentos generales", "TotalGeneralDiscounts", "BT-107", IGUAL,
        "la suma de los descuentos del documento, que es lo mismo en los dos",
    ),
    Correspondencia(
        "suma de cargos generales", "TotalGeneralSurcharges", "BT-108", IGUAL,
        "la suma de los cargos del documento, que es lo mismo en los dos",
    ),

    # La quinta familia: el pago. Es la del choque más feo de todos, y no se ve
    # sin abrir las dos listas a la vez: los 19 códigos de medio de pago de
    # Facturae **existen los 19** en la lista europea queriendo decir otra
    # cosa, así que el que copie el dígito no se lleva un error, se lleva una
    # factura que dice que se paga de otra manera.
    Correspondencia(
        "forma de pago", "Installment", "BG-16", OTRO_CORTE,
        "Facturae admite **varios vencimientos** -`Installment` es "
        "`maxOccurs=\"unbounded\"`- y el anexo tiene un solo grupo de "
        "instrucciones de pago, `BG-16` con cardinalidad 0..1, y una sola "
        "fecha en `BT-9`. Con un vencimiento la copia lo recoge entero; con "
        "dos hay que elegir cuál viaja. Medido el 21-09-2026: ninguna de las "
        "14 facturas de aquí trae más de uno, así que **el corte existe y no "
        "se ha visto**",
    ),
    Correspondencia(
        "fecha de vencimiento", "InstallmentDueDate", "BT-9", IGUAL,
        "la fecha de vencimiento del pago, igual en los dos. Medido: 12 de 14",
    ),
    Correspondencia(
        "importe del vencimiento", "InstallmentAmount", "", SIN_SITIO,
        "la norma no tiene importe por vencimiento: lo más parecido es "
        "`BT-115`, el importe a pagar, que es uno para toda la factura. Con un "
        "solo vencimiento son el mismo número y no se pierde nada; con dos, el "
        "reparto se queda en el original",
    ),
    Correspondencia(
        "medio de pago", "PaymentMeans", "BT-81", OTRA_LISTA,
        "y es el caso más peligroso de la tabla. Facturae tiene 19 códigos "
        "propios y la norma pide UNCL4461. Medido el 21-09-2026 contra la "
        "lista que el esquematrón oficial trae: los **19 existen también en "
        "UNCL4461** -diez tal cual, y los nueve que empiezan por cero en "
        "cuanto se les quita-, así que copiar el dígito no da un error: da un "
        "código válido que dice otra cosa. El 19 de Facturae es «pago "
        "mediante tarjeta» y el 19 europeo es un adeudo de cámara de "
        "compensación; el 04 es «transferencia» y el 4 europeo es la reversión "
        "de un adeudo. Ninguna etiqueta del esquema trae el código europeo, "
        "así que la tabla se escribe a mano: aquí van las cinco que se pueden "
        "sostener por nombre",
    ),
    Correspondencia(
        "cuenta de abono", "AccountToBeCredited", "BG-17 (BT-84)", IGUAL,
        "la cuenta donde se cobra. El IBAN pasa a `BT-84` sin discusión. "
        "Medido: 9 de 14",
    ),
    Correspondencia(
        "cuenta de cargo", "AccountToBeDebited", "BT-91", NO_LO_PIDEN,
        "la norma tiene la cuenta que se adeuda y el anexo no la recoge. "
        "Medido: 8 de 14 la traen, que son más de las que traen la de abono",
    ),
    Correspondencia(
        "referencia de la remesa", "PaymentReconciliationReference", "BT-83",
        NO_LO_PIDEN,
        "la norma tiene la información de remesa -lo que el pagador escribe en "
        "el concepto para que el cobro se reconozca- y el anexo no la recoge. "
        "Medido: 5 de 14",
    ),
    Correspondencia(
        "dirección de la sucursal", "BranchInSpainAddress", "", SIN_SITIO,
        "el domicilio de la oficina bancaria. La norma no tiene nada parecido: "
        "de la cuenta se queda con el identificador y, como mucho, con el BIC. "
        "Medido: 5 de 14",
    ),
    Correspondencia(
        "dirección de la sucursal de fuera", "OverseasBranchAddress", "",
        SIN_SITIO,
        "la misma dirección cuando el banco no es español, y con el mismo "
        "destino: ninguno. Medido: 3 de 14",
    ),
    Correspondencia(
        "información adicional del cobro", "CollectionAdditionalInformation",
        "", SIN_SITIO,
        "texto libre sobre el cobro, que en la copia no tiene dónde ir. "
        "Medido: ninguna de las 14 lo trae, y se escribe igual porque la tabla "
        "describe el formato y no esta carpeta",
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
    "UnitOfMeasure", "GrossAmount",
    "GeneralDiscounts", "GeneralSurcharges",
    "Installment", "InstallmentDueDate", "PaymentMeans",
    "BranchInSpainAddress", "OverseasBranchAddress",
    "CollectionAdditionalInformation",
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


# Los cinco medios de pago que se pueden traducir por su nombre, y solo esos.
#
# Los 19 de Facturae existen los 19 en UNCL4461 con otro significado, así que
# no hay ninguna traducción automática posible: hay que ir código a código. Se
# escriben aquí los cinco en los que el nombre de Facturae y el de la lista
# europea dicen exactamente lo mismo -comprobados contra la lista publicada de
# UNCL4461 el 21-09-2026- y **no se inventan los demás**: una letra aceptada o
# un crédito documentario no tienen un equivalente que se pueda sostener, y
# ponerle uno «parecido» es justo el fallo del que avisa esta nota.
#
# En dos hay una elección que no se puede tomar desde aquí: la transferencia y
# la domiciliación tienen un código genérico y otro SEPA -30 y 58, 49 y 59-.
# Va el genérico, que vale siempre; el SEPA lo sabe quien emite, no quien lee.
_MEDIOS_DE_PAGO = {
    "01": ("al contado", "10", "in cash"),
    "02": ("recibo domiciliado", "49", "direct debit"),
    "04": ("transferencia", "30", "credit transfer"),
    "11": ("cheque", "20", "cheque"),
    "19": ("pago mediante tarjeta", "48", "bank card"),
}


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
_SIN_SITIO_EN_EL_PAGO = (
    ("BranchInSpainAddress", "dirección de la sucursal del banco"),
    ("OverseasBranchAddress", "dirección de la sucursal del banco"),
    ("CollectionAdditionalInformation", "información adicional del cobro"),
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


def _de_las_lineas(factura, etiqueta: str) -> list[Incidencia]:
    """Lo que hay que decidir al copiar las líneas: el código y el importe.

    De la familia de las líneas solo salen estas dos notas, y no es por
    ahorrar: las demás filas son «llega igual» -que no se dice- o «el anexo no
    lo pide» -que llega, y no lo mira nadie-. Lo que hay que contar es lo que
    obliga a decidir algo o lo que puede acabar en un número equivocado.
    """
    incidencias: list[Incidencia] = []
    lineas = _hijos(factura, "Items", "InvoiceLine")
    if not lineas:
        return incidencias

    unidades: list[str] = []
    descuadradas = 0
    coste_de_esas = Decimal(0)
    bruto_de_esas = Decimal(0)
    for linea in lineas:
        unidad = _texto(linea, "UnitOfMeasure")
        if unidad and unidad not in unidades:
            unidades.append(unidad)
        # Los dos tienen que estar escritos para compararlos: `_numero`
        # devuelve cero cuando falta, y un cero contra un importe daría una
        # queja inventada en una factura a la que solo le falta un campo.
        if _texto(linea, "TotalCost") and _texto(linea, "GrossAmount"):
            coste = _numero(linea, "TotalCost")
            bruto = _numero(linea, "GrossAmount")
            if coste != bruto:
                descuadradas += 1
                coste_de_esas += coste
                bruto_de_esas += bruto

    if unidades:
        incidencias.append(
            Incidencia(
                "COPIA-LINEA-UNIDAD",
                NOTA,
                "La unidad de medida de esta factura no vale escrita así en la "
                "copia. Facturae tiene su propia lista de unidades, de dos "
                "dígitos, y la norma pide un código de UN/ECE, recomendaciones "
                "20 y 21. Hay que traducirlo, y el propio esquema de Facturae "
                "solo ayuda a medias: de sus 36 códigos, 13 llevan el europeo "
                "en la etiqueta, 16 lo llevan pero hay que ponerle una X "
                "delante, y 6 no lo llevan. En la copia tampoco tiene campo "
                "propio: va en un atributo de la cantidad.",
                campo=f"{etiqueta}Unidad de medida (el atributo de BT-129 en la copia)",
                esperado=(
                    "C62 en la copia, que es la unidad suelta en UN/ECE Rec 20"
                    if "01" in unidades
                    else "un código de UN/ECE, recomendaciones 20 y 21"
                ),
                encontrado=f"{', '.join(unidades)} en esta factura, "
                           f"de la lista de Facturae",
            )
        )
    if descuadradas:
        incidencias.append(
            Incidencia(
                "COPIA-LINEA-NETO",
                NOTA,
                "El importe neto de una línea de la copia es `GrossAmount` y "
                "no `TotalCost`, y en esta factura los dos no valen lo mismo. "
                "El esquema define `TotalCost` como cantidad por precio y "
                "`GrossAmount` como «TotalCost - DiscountAmount + "
                "ChargeAmount»; BT-131 es el importe de la línea después de "
                "sus descuentos y cargos, que es el que cuadra con la suma de "
                "líneas. Copiar el otro no deja un hueco: deja un número que "
                "parece bueno.",
                campo=f"{etiqueta}Importe neto de las líneas (BT-131 en la copia)",
                esperado=f"{_fmt(bruto_de_esas)} en la copia, que es lo que "
                         f"suman sus GrossAmount",
                encontrado=f"{_fmt(coste_de_esas)} si se copiara TotalCost, "
                           f"en {descuadradas} de {len(lineas)} líneas",
            )
        )
    return incidencias


def _del_pago(factura, etiqueta: str) -> tuple[list[Incidencia], list[str]]:
    """El medio de pago, los vencimientos, y lo que del banco no viaja.

    Devuelve dos cosas: sus notas y la lista de lo que se queda en el
    original, que se junta con la de la factura para salir en **una** nota y
    no en tres.
    """
    plazos = _hijos(factura, "PaymentDetails", "Installment")
    if not plazos:
        return [], []

    incidencias: list[Incidencia] = []
    medios: list[str] = []
    fechas: list[str] = []
    for plazo in plazos:
        medio = _texto(plazo, "PaymentMeans")
        if medio and medio not in medios:
            medios.append(medio)
        fecha = _texto(plazo, "InstallmentDueDate")
        if fecha:
            fechas.append(fecha)

    se_quedan: list[str] = []
    for nombre, concepto in _SIN_SITIO_EN_EL_PAGO:
        hay = any(plazo.xpath(f".//*[local-name()='{nombre}']")
                  for plazo in plazos)
        if hay and concepto not in se_quedan:
            se_quedan.append(concepto)

    if medios:
        conocidos = [m for m in medios if m in _MEDIOS_DE_PAGO]
        if conocidos:
            esperado = ", ".join(
                f"{_MEDIOS_DE_PAGO[m][1]} en la copia "
                f"(«{_MEDIOS_DE_PAGO[m][2]}» en UNCL4461)" for m in conocidos
            )
        else:
            esperado = ("un código de UNCL4461 elegido a mano: para éste no "
                        "hay equivalente que se pueda sostener")
        encontrado = ", ".join(
            f"{m} en esta factura"
            + (f", que aquí es «{_MEDIOS_DE_PAGO[m][0]}»"
               if m in _MEDIOS_DE_PAGO else "")
            for m in medios
        )
        incidencias.append(
            Incidencia(
                "COPIA-PAGO-MEDIO",
                NOTA,
                "El medio de pago de esta factura está escrito con la lista de "
                "Facturae, y la copia lo pide con la europea, UNCL4461. No es "
                "como la unidad de medida, donde un código malo se ve: los 19 "
                "códigos de Facturae **existen los 19** en la lista europea "
                "queriendo decir otra cosa -diez tal cual y los nueve que "
                "empiezan por cero en cuanto se les quita-, así que copiar el "
                "dígito no da un error, da una factura válida que dice que se "
                "paga de otra manera. El 19 de aquí es la tarjeta y el 19 "
                "europeo es un adeudo de cámara de compensación.",
                campo=f"{etiqueta}Medio de pago (BT-81 en la copia)",
                esperado=esperado,
                encontrado=encontrado,
            )
        )
    if len(plazos) > 1:
        incidencias.append(
            Incidencia(
                "COPIA-VENCIMIENTOS",
                NOTA,
                "Esta factura se paga en varios vencimientos y la copia solo "
                "admite uno. El anexo tiene un grupo de instrucciones de pago, "
                "BG-16, con cardinalidad 0..1, y una sola fecha de "
                "vencimiento, BT-9; Facturae deja repetir el vencimiento "
                "tantas veces como haga falta. Hay que elegir cuál viaja, y el "
                "reparto de importes se queda en el original: la norma no "
                "tiene importe por vencimiento.",
                campo=f"{etiqueta}Vencimientos (BG-16 y BT-9 en la copia)",
                esperado="un solo vencimiento en la copia",
                encontrado=f"{len(plazos)} en esta factura"
                           + (f": {', '.join(fechas)}" if fechas else ""),
            )
        )
    return incidencias, se_quedan


def _de_los_cargos(factura, etiqueta: str) -> list[Incidencia]:
    """El IVA que los descuentos generales de Facturae no llevan.

    Es la única nota de la familia, y sale por donde los dos modelos no se
    parecen: la norma tiene **un grupo de minoraciones por categoría de IVA**
    y Facturae tiene un descuento sobre el total. El resto de la familia
    -importes, motivos, sumas, descuentos de línea- pasa sin discusión, y lo
    que pasa no se cuenta.
    """
    totales = _hijos(factura, "InvoiceTotals")
    if not totales:
        return []
    grupos = (_hijos(totales[0], "GeneralDiscounts", "Discount")
              + _hijos(totales[0], "GeneralSurcharges", "Charge"))
    if not grupos:
        return []

    # Las categorías se cuentan por pareja impuesto-tipo y solo de
    # `TaxesOutputs`: una retención también escribe un `TaxRate` y contarla
    # diría que la factura tiene dos categorías cuando tiene una.
    categorias: list[tuple[str, str]] = []
    for tax in _hijos(factura, "TaxesOutputs", "Tax"):
        pareja = (_texto(tax, "TaxTypeCode"), _texto(tax, "TaxRate"))
        if pareja not in categorias:
            categorias.append(pareja)

    if len(categorias) > 1:
        esperado = (f"repartidos entre las {len(categorias)} categorías de IVA "
                    "de la factura, a prorrata de la base de cada una")
    elif categorias:
        esperado = (f"la categoría de la factura, al {categorias[0][1]} %, "
                    "en cada uno de los grupos de la copia")
    else:
        esperado = "una categoría de IVA en cada grupo de la copia"
    return [
        Incidencia(
            "COPIA-CARGO-IVA",
            NOTA,
            "Los descuentos y cargos generales de esta factura no llevan IVA "
            "propio, y en la copia tienen que llevarlo. La norma agrupa las "
            "minoraciones y los cargos del documento **por categoría de IVA** "
            "-BT-95 y BT-96 en las minoraciones, BT-102 y BT-103 en los "
            "cargos-, y Facturae los aplica antes del desglose y sobre la "
            "base entera. Con una sola categoría la cuenta está forzada. Con "
            "dos o más hay que repartir cada descuento entre ellas, y no lo "
            "dice ningún texto: a prorrata de cada base es lo único que deja "
            "cuadrar el desglose de la copia.",
            campo=f"{etiqueta}Descuentos y cargos generales "
                  f"(BG-20 y BG-21 en la copia)",
            esperado=esperado,
            encontrado=f"{len(grupos)} en esta factura, sin categoría ni tipo",
        )
    ]


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

    incidencias.extend(_de_las_lineas(factura, etiqueta))
    incidencias.extend(_de_los_cargos(factura, etiqueta))
    del_pago, se_queda_del_pago = _del_pago(factura, etiqueta)
    incidencias.extend(del_pago)

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
    se_quedan.extend(se_queda_del_pago)
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
