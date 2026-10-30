# -*- coding: utf-8 -*-
"""Qué le pasa a una factura cuando se copia a la solución pública.

Qué es una copia fiel
---------------------
Quien no emita por la solución pública tiene que mandarle una **copia fiel** de
cada factura, en UBL, a la vez que la emite (RD 238/2026, y el artículo 4 de
la Orden HAC/1028/2026, en el BOE del 05-10-2026). La factura original sigue
siendo la que es —Facturae, CII, EDIFACT—; lo que viaja a la AEAT es una copia
escrita en otra sintaxis.

En **UBL 2.5**, desde el 22-09-2026 y por escrito: preguntada si la edición de
junio de 2026 de la norma vale también fuera de la solución pública, la AEAT
contestó que `UNE-EN 16931-1:2026` y `UNE-CEN/TS 16931-3-2:2026` —la
correspondencia sintáctica UBL 2.5 / ISO/IEC 19845— son las aplicables «al
sistema español de facturación electrónica en su conjunto», y nombró entre los
casos el envío de copias fieles. Aquí eso no cambia ninguna fila: esta tabla
dice a qué **término** del anexo va cada cosa, no en qué elemento se escribe.
Lo que cambia es que ya no hay que decir «UBL» a secas.

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
es un fallo de nadie. Por eso todo lo que sale de aquí es **NOTA**. La orden
dice lo mismo con otras palabras (artículo 4.2): la copia lleva los conceptos
del original «que tengan correspondencia semántica equivalente».

Lo que no es esto
-----------------
No es un conversor: aquí no se escribe ninguna copia. No valida la copia, que
es otro documento y se mide con sus propias reglas (las `SPFE-`). Los campos
españoles del anexo, la orden los describe en UBL y de Facturae no dice nada:
de dónde sale cada uno, o que no sale de ninguna parte, lo dice esta tabla
desde el 13-10-2026, y es lectura de aquí, como todo lo demás. Hasta entonces
este párrafo decía que eso no se adivinaba.

Lo que sí hace es decir seis cosas distintas sobre la factura que se está
mirando, y las cuatro últimas son las que no dice nadie:

1. **Lo que llega igual.** La mayor parte.
2. **Lo que no tiene sitio** y habrá que omitir o meter en una extensión.
3. **Lo que llega con otro número.** El total de Facturae no es el europeo:
   `InvoiceTotal` **resta las retenciones**, y está en el esquema del formato,
   no en una interpretación. Quien copie campo a campo pondrá ese importe en
   `BT-112` y será otro. Hasta el 07-10-2026 se decía lo mismo de
   `TotalTaxOutputs`, que **suma el recargo de equivalencia**: el borrador de
   abril daba al recargo un grupo propio, fuera de `BT-110`. La orden lo pone
   en el desglose del IVA, así que `BT-110` lo lleva y la cuota llega igual.
   Medido el 20-09-2026 sobre las facturas de terceros que hay aquí: **6 de
   14 llevan retenciones o recargo**; cuántas de esas seis llevan retención,
   que es lo que hoy cambia el número, no está medido.
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
6. **Lo que no hay que copiar.** Es el último que apareció y el más raro:
   copiar campo a campo no siempre omite ni cambia, a veces **añade**, y lo
   añadido rompe la copia. `TaxCurrencyCode` —la moneda en la que se
   contabiliza el IVA— es obligatorio en Facturae y las 14 facturas de aquí
   escriben en él la moneda de la propia factura. Llevado a `BT-6`, que en la
   norma solo tiene sentido cuando son distintas, obliga a escribir `BT-111`
   —`BR-53`—, que Facturae no tiene. Un campo que no aportaba nada deja la
   copia sin cumplir la norma.

De dónde sale cada fila
-----------------------
De las fórmulas que el propio esquema de Facturae escribe en su documentación y
que `facturae.py` ya comprueba una a una —`FE-TOTAL`, `FE-PENDIENTE`,
`FE-EJECUTAR`—, y de dónde pone el anexo I cada importe español. Lo que no se
sabe va marcado `POR_DECIDIR` y se dice así, en vez de colocarlo donde suene
bien.

El destino de una fila no se escribe de memoria: el anexo de la orden recoge
**116 términos europeos distintos** (el de abril, 104) y están en
`cius_es.CAMPOS`, con su nombre y su cardinalidad. Una prueba compara la tabla con esa lista, así que un BT-
inventado o un BT- que el anexo no tenga no pasan de aquí.

Las familias, y en qué orden
----------------------------
La tabla se escribe por familias y no de una vez, porque cada una se sostiene
en una fuente distinta y alguna todavía no tiene fuente:

1. **Los importes** (20-09-2026). Se empezó por ahí porque copiar campo a campo
   no omite un dato: **cambia una cifra**, y es lo primero con lo que tropieza
   quien copie así en cuanto la factura lleve retención. Tropieza porque se
   ve: la copia deja de cuadrar consigo misma y la rechaza `BR-CO-15`. Hasta
   el 26-09-2026 aquí se decía lo contrario —«un número equivocado no se
   ve»— y no era cierto; lo fija
   `test_el_total_copiado_tal_cual_no_pasa_las_reglas_de_la_copia`. Hasta el
   07-10-2026 se decía además «retención o recargo» y se sumaba `BR-CO-14`,
   que era el borrador de abril: con la orden, la cuota de Facturae es la de
   la copia. Lo que pasa en silencio de verdad es el medio de pago, en la
   quinta familia.
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

6. **Las referencias** (22-09-2026): el pedido, el contrato, el expediente,
   el albarán y la factura anterior. Es la única familia que se escribe
   sabiendo que casi nada llega: de las siete referencias que Facturae sabe
   llevar, el anexo **no recoge ninguna** —de `BT-11` a `BT-19` no hay ni una
   en sus 104 términos, ni en los 116 de la orden—. Y aun así saca nota, por el hueco que queda libre:
   `BT-10` es la referencia del comprador, la de sus rutas internas, y quien
   meta ahí el pedido repite el fallo del medio de pago. Medido: 8 de 14 traen
   alguna, y las 8 dentro de la línea.

7. **El desglose del IVA** (22-09-2026): base, cuota y tipo llegan igual, y
   lo caro es la categoría. `BT-118` es obligatorio y el código de impuesto de
   Facturae dice qué impuesto es, no de qué categoría; **a tipo positivo la
   deducción está forzada y al 0 % no**, que aquí pasa en 3 de 14. Y el motivo
   de la exención, que en la copia deja de ser opcional en cuanto la categoría
   es `E`, Facturae lo escribe en texto libre dentro de una línea.

8. **La cabecera** (22-09-2026): la familia con más «lo pone quien copia», y
   con la única fila de toda la tabla en la que el fallo es copiar **de más**:
   la moneda del IVA, explicada arriba.

9. **Las partes** (22-09-2026): quién es cada uno. Las direcciones y los
   contactos ya estaban en la segunda familia; lo que quedaba esconde el
   nombre de una persona física, que Facturae guarda en tres campos y la copia
   pide en uno solo y obligatorio. Medido: 7 de 14.

Con eso la tabla queda escrita: **97 filas que nombran 92 de los 104 términos
europeos** del anexo, medido el 22-09-2026. Los 12 que no se nombran son los
**grupos** —`BG-4` a `BG-9`, `BG-22`, `BG-25`, `BG-29` a `BG-31`— y `BT-154`,
que la tercera familia deja vacío a propósito: contenedores, no datos.

La tabla entera está medida contra el borrador de abril del anexo, que es el
que tiene `cius_es.CAMPOS`, y las tres últimas familias se escribieron
debajo del anuncio del 10-09-2026, marcando en su fila lo que podía moverse.
Desde el 05-10-2026 el anexo es el de la Orden HAC/1028/2026, y lo movió:
el NIF del vendedor (`BT-31`, o `BT-32` con «LOC» y «FC»), el recorte de la
`L3A` —fuera las claves 18, 19 y 20— y las categorías N, D y F de la `L4`.
El `389` de la lista de tipos no era nuevo: ya estaba en la L1 de abril.

El 07-10-2026 se corrigieron aquí las filas que la orden contradice de
frente: el recargo de equivalencia, que pasa al desglose con la categoría N;
las cuotas repercutidas, que por eso llegan igual; el grupo de entidades,
que sale del mismo `BG-34`; los suplidos y las retenciones, que ya tienen
grupo, y lo que se decía del texto como si no hubiera salido. El resto se
vuelve a mirar entero cuando `cius_es.CAMPOS` se regenere desde el BOE, y no
hace falta acordarse: medido el 07-10-2026, el anexo de la orden trae **116
términos europeos**, los 104 de abril y doce más (`BG-14`, `BG-33`, `BT-30`,
`BT-31`, `BT-47`, `BT-73`, `BT-74`, `BT-130`, `BT-142`, `BT-143`, `BT-149`
y `BT-167`), así que `test_el_anexo_sigue_teniendo_los_terminos_que_dice_la_cabecera`
salta ese día, y `test_el_destino_de_cada_fila_existe_en_el_anexo` con él
en cada fila «el anexo no lo pide» que nombre un término que la orden sí
pide, como el periodo de facturación (`BG-14`).

Saltaron el 11-10-2026, al regenerarse `cius_es.CAMPOS` del XML del BOE, y
en dos filas: el periodo de facturación, que la orden recoge como el de la
factura recapitulativa, y el porcentaje del cargo, que la orden recoge en la
línea (`BT-143`, junto con su base, `BT-142`, para los impuestos y tasas de
cada línea) y no en el documento (`BT-101`). Esa fila se partió en dos, y la
tabla tuvo desde entonces 98, que nombraban 96 de los 116 términos europeos.
Sin nombrar quedaban los doce grupos (los once de antes y `BG-33`), `BT-154` y
siete términos que la orden trae y el borrador no.

Los siete se miraron el 13-10-2026, contra el esquema de Facturae y el texto
de la orden. Seis tienen origen en la factura: el NIF va como NIF-IVA
(`BT-31`) o como NIF, y entonces el del vendedor dos veces (`BT-32` y
`BT-30`), y el del comprador en `BT-48` o en `BT-47`; la unidad de medida es
`BT-130`; la base de un impuesto de la línea que no es IVA es `BT-142`; y el
tipo de cambio es `BT-167`, que se queda en «no se sabe» porque cómo se
escribe lo dice una especificación de 2026 que aquí no está. El séptimo,
`BT-149`, la cantidad a la que se aplica el precio, no tiene origen y es
opcional: se queda vacío, como `BT-154`. La tabla tuvo entonces 100 filas,
que nombraban 102 de los 116 términos, y lo fija
`test_ningun_termino_del_anexo_se_queda_sin_mirar`: si el anexo trae un
término que ninguna fila nombra, la suite se pone en rojo.

El mismo día se miraron los **33 campos españoles** de la orden, los
`BT-ES-` y los `BG-ES-`. Casi todos tienen origen en la factura, y van con
la fila de lo que les da origen: la fecha de pago con los anticipos, las
retenciones con los importes, el impuesto que no es IVA con los cargos, el
tercero que expide la factura con las partes, y la rectificativa, el QR y la
autorización con los documentos justificativos. Uno sale siempre igual: el
indicador de copia, que en una copia fiel es «true». Y dos no salen de
ninguna parte, la minoración en nombre de un tercero y la situación del
inmueble: van a la fila de los huecos, y con ellos `BT-149` y `BT-154`, que
hasta entonces se decían vacíos solo en su fila. La tabla tiene desde
entonces **107 filas, que nombran los 33 campos españoles y 104 de los 116
términos europeos**; los doce que no nombra son los grupos, y la prueba ya no
tiene excepciones.

Y esperan **el lote** y las tres filas que están en `POR_DECIDIR`. Eran tres hasta el 07-10-2026, cuando la de los
suplidos salió al leer la orden, y el 13-10-2026 entró la del tipo de cambio.
**Los centros administrativos** ya no esperan nada: el anexo de la orden no
los recoge.

**No todas las filas sacan una nota**, y es a propósito: lo que llega igual no
se dice. Un informe que celebre cada campo que sí viaja no lo lee nadie. Sale
nota cuando hay algo que decidir, algo que cambia de valor o algo que se queda
fuera.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from validador import cifras
from validador.formato import FACTURAE, Deteccion
from validador.incidencias import NOTA, Incidencia
from validador.sintaxis import a_decimal

# Qué le pasa a un concepto al copiarse. Son nueve estados y ninguno sobra: la
# tentación es juntarlos en «llega» y «no llega», y eso borra justo lo que hay
# que decidir.
#
#   - «no se sabe» no es «no tiene sitio»: el primero se resuelve leyendo un
#     texto que diga dónde va, el segundo no se resuelve. Leer la orden ya ha
#     sacado de aquí los suplidos; lo que queda espera a otro texto.
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
# campo a campo no omite un dato, sino que **cambia una cifra**. Esa cifra se
# ve —la copia deja de cuadrar y la rechazan `BR-CO-14` y `BR-CO-15`—, pero
# esas reglas dicen que no cuadra, no por qué ni qué cifra va. Eso es lo que
# ponen las notas de esta familia.
CORRESPONDENCIAS: tuple[Correspondencia, ...] = (
    Correspondencia(
        "base antes de impuestos", "TotalGrossAmountBeforeTaxes", "BT-109", IGUAL,
        "las dos son el importe bruto menos descuentos más cargos generales",
    ),
    Correspondencia(
        "cuotas repercutidas", "TotalTaxOutputs", "BT-110", IGUAL,
        "el esquema de Facturae dice «sumatorio de todas las cuotas y recargos "
        "repercutidos», y BT-110 es la suma de las cuotas del desglose "
        "(BR-CO-14), donde la orden pone también el recargo de equivalencia: "
        "son el mismo número. Hasta el 07-10-2026 esta fila decía «llega con "
        "otro número», porque el borrador de abril daba al recargo un grupo "
        "propio fuera de la cuota de IVA. Vale mientras todo lo de "
        "`TaxesOutputs` sea IVA, IGIC o IPSI, que son los que tienen "
        "categoría en la L4: un impuesto que no sea ninguno de los tres "
        "-Facturae admite ahí desde el 05 «otro» hasta los especiales- en la "
        "copia va como cargo y no entra en BT-110. Ese caso no se ha visto: "
        "medido el 22-09-2026, las 14 escriben el 01 o el 02",
    ),
    Correspondencia(
        "total de la factura", "InvoiceTotal", "BT-112", CAMBIA,
        "el esquema lo define como base más repercutidos **menos retenidos**, y "
        "BT-112 es base más cuotas del desglose, recargo incluido: la "
        "retención no es un impuesto de la factura para la norma europea, y "
        "la orden la lleva aparte, en su grupo de retenciones",
    ),
    Correspondencia(
        "anticipos", "TotalPaymentsOnAccount", "BT-113 y BT-ES-2", OTRO_CORTE,
        "lo ya pagado antes de emitir, que la norma también tiene, pero la "
        "orden lo corta por otro sitio. `BT-113` no vale para los anticipos "
        "que devengaron el IVA (artículo 75.Dos de la Ley del IVA), y "
        "Facturae no dice cuáles lo devengaron: por eso `SPFE-IMPORTE-PAGADO` "
        "es una nota. Y la fecha va aparte: Facturae guarda la de cada "
        "anticipo (`PaymentOnAccountDate`), y la orden pide una sola, la "
        "fecha efectiva de pago (`BT-ES-2`), y solo si la factura quedó "
        "pagada antes de expedirse o ese mismo día, y no antes de la "
        "operación. Con anticipos que no la pagan entera no hay fecha que "
        "poner. Hasta el 13-10-2026 esta fila decía «llega igual». Medido: "
        "ninguna de las facturas de aquí trae anticipos",
    ),
    Correspondencia(
        "total a pagar", "TotalExecutableAmount", "BT-115", POR_DECIDIR,
        "es el que más se le parece (descuenta retenciones y suma suplidos y "
        "gastos financieros), pero el anexo manda sumar los importes de "
        "terceros «junto con» el total con IVA, y esa cuenta solo se "
        "comprueba cuando no hay más que retenciones: es la misma duda de "
        "SPFE-TOTAL-A-PAGAR",
    ),
    Correspondencia(
        "retenciones de impuestos", "TotalTaxesWithheld",
        "BG-34 en la línea RETE (BT-ES-16, BT-179 y BT-180) y BT-ES-17", APARTE,
        "la norma europea no tiene término para la retención; la orden sí: un "
        "grupo de retenciones, uno por factura, con su línea de cobro "
        "identificada con «RETE» (BT-ES-16) y la suma dos veces, en BT-179 y "
        "en cac:WithholdingTaxTotal (BT-ES-17). Lleva además una descripción "
        "del motivo, BT-180, que es obligatoria y que Facturae no tiene: la "
        "pone quien copia. Cada retención va en las dos filas siguientes",
    ),
    Correspondencia(
        "cada retención", "TaxesWithheld",
        "BG-ES-4 (BT-ES-18, BT-ES-19 y BT-ES-20)", APARTE,
        "la base, el importe y el porcentaje de cada una, con la categoría "
        "«S» y el esquema «WTH», que son fijos. Van en el documento, donde "
        "Facturae las resume: las de cada línea no tienen sitio propio en la "
        "copia. El importe puede que haya que calcularlo: en Facturae es "
        "opcional y en la copia obligatorio, y la orden lo define como la "
        "base por el porcentaje, que es la cuenta que hace `SPFE-RETENCION`. "
        "Medido: las facturas de aquí que retienen, 6, lo escriben en las "
        "líneas y en el documento",
    ),
    Correspondencia(
        "concepto de la retención", "(no lo tiene)", "BT-ES-21", SE_INVENTA,
        "obligatorio y de la L5: siete supuestos del reglamento del IRPF "
        "(actividades profesionales, arrendamientos de locales, propiedad "
        "intelectual...), tres del de Sociedades y un 11, «Otros». Facturae "
        "dice qué impuesto se retiene, con el mismo código que los "
        "repercutidos (04 IRPF, 05 otro), y no por qué: el 04 vale para "
        "todos los rendimientos del IRPF, como el 07 para todos los "
        "impuestos especiales. Lo pone quien copia, que sabe qué ha "
        "facturado. Medido: las facturas de aquí que retienen escriben el 04 "
        "dos veces, el 05 tres y una el 03, que es el IGIC",
    ),
    Correspondencia(
        "importes retenidos", "AmountsWithheld", "BG-ES-4, la retención aplicada",
        POR_DECIDIR,
        "Facturae distingue la retención de impuestos de otros importes "
        "retenidos (la retención de garantía de una obra, por ejemplo) y el "
        "anexo describe un solo grupo de retención: si el segundo cabe ahí no "
        "lo dice nadie. La orden no lo aclara: los conceptos del grupo, la "
        "L5, son siete supuestos del reglamento del IRPF, tres del de "
        "Sociedades y un 11, «Otros», que no dice si abarca lo que no es una "
        "retención fiscal. Medido: dos facturas distintas de las de aquí lo "
        "traen",
    ),
    Correspondencia(
        "recargo de equivalencia", "EquivalenceSurchargeAmount",
        "BG-23 (BT-116, BT-117, BT-118 y BT-119)", OTRO_CORTE,
        "la orden lo pone en el desglose del IVA: BG-23 «también "
        "proporcionará información sobre el desglose del recargo de "
        "equivalencia», BT-117 lleva «la cuota de dicho recargo» y BT-119 su "
        "tipo, con la categoría N de la L4, que es «régimen especial del "
        "recargo de equivalencia». Facturae lo escribe dentro de la entrada "
        "del IVA, con su tipo y su cuota al lado, y una entrada del desglose "
        "lleva un solo tipo y una sola cuota: hay que partirla en dos. La "
        "base de la segunda la orden no la explica para el recargo; la de "
        "Facturae es «la misma que para el IVA». Como el recargo entra en el "
        "desglose, entra también en BT-110 y en BT-112, y por eso no saca "
        "nota. Hasta el 07-10-2026 esta fila decía que el anexo le daba grupo "
        "propio, fuera de la cuota de IVA: era el borrador de abril, un BG-34 "
        "con la línea REEQ, y la orden lo quitó",
    ),
    Correspondencia(
        "suplidos", "TotalReimbursableExpenses",
        "BG-34 (BT-ES-10, BT-179 y BT-180), en la línea SUPL; si es un "
        "impuesto o una tasa, BT-ES-11 y BG-ES-3 (BT-ES-12, BT-ES-13 y "
        "BT-ES-14)", APARTE,
        "la orden los pone en el grupo de cargos en nombre de un tercero, "
        "BG-34, que no entra en el total con impuestos y se suma al total a "
        "pagar, igual que en Facturae. El grupo va en una línea de cobro "
        "identificada con «SUPL» en cac:CollectionInvoiceLine/cbc:ID "
        "(BT-ES-10). El importe y la descripción son BT-179 y BT-180, "
        "términos de la edición de 2026 de la norma, y la orden no les da "
        "ruta UBL, y no es un olvido: el anexo solo escribe la ruta de lo que "
        "no tiene término en la norma. La de los términos europeos es la de "
        "su correspondencia UBL, que para la edición de 2026 es "
        "UNE-CEN/TS 16931-3-2:2026 -la que la AEAT dio por aplicable el "
        "22-09-2026-, de pago y aquí sin leer. Y BT-180 es obligatoria y Facturae "
        "no la tiene: de un suplido guarda las partes, la fecha, la factura "
        "de origen y el importe. Si lo adelantado es un impuesto o una tasa, "
        "la orden le da otra línea: «IEDMT» para el impuesto especial sobre "
        "determinados medios de transporte, el de matriculación, y «OTROS» "
        "para el resto (BT-ES-11), con su desglose en BG-ES-3 (la base, el "
        "tipo y la cuota, BT-ES-12 a BT-ES-14). Facturae no distingue un "
        "suplido de otro, así que cuál de las dos va lo decide quien copia, "
        "y el desglose también: un suplido de Facturae solo trae el importe, "
        "que es la cuota, y la base y el tipo son opcionales. Medido: dos "
        "facturas distintas de las de aquí traen suplidos. "
        "Hasta el 07-10-2026 esta fila estaba en «no se "
        "sabe todavía», porque el borrador de abril no les daba ruta y el "
        "texto que iba a dársela no había salido",
    ),
    Correspondencia(
        "gastos financieros", "TotalFinancialExpenses", "", SIN_SITIO,
        "ni la norma europea ni el anexo tienen dónde ponerlos",
    ),
    Correspondencia(
        "subvenciones", "Subsidies", "", SIN_SITIO,
        "restan del total a pagar en Facturae y no tienen término europeo; "
        "quien copie tendrá que dejarlas fuera o inventarse una extensión. "
        "La orden tiene un grupo que también resta del total a pagar, el de "
        "las minoraciones en nombre de un tercero («MINO», BT-ES-15), y no "
        "es para esto: minora lo que se cobró en nombre de otro, y su "
        "ejemplo es la devolución de un suplido. Meter ahí una subvención "
        "sería decir que se cobró en nombre de alguien, y la factura no lo "
        "dice. Medido: ninguna de las facturas de aquí trae subvenciones",
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
        "único de esta misma herramienta (`CodigoUnico.numero_completo`). Si "
        "la copia llevara solo el número, la copia y el original no "
        "identificarían la misma factura. Medido el 20-09-2026: 8 de las 14 "
        "facturas de aquí traen serie con texto",
    ),
    Correspondencia(
        "fecha de operación", "OperationDate", "BT-7", IGUAL,
        "es el único sitio que hay: el anexo no recoge BT-72, la fecha de "
        "entrega. Y le cambia el nombre al término (en la norma BT-7 es la "
        "fecha de devengo del IVA, que no siempre es la de la operación), pero "
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
        "no hay término para el fax entre los 116 que recoge el anexo, ni "
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
        "el anexo (que es español) tampoco lo recoge",
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
        IGUAL,
        "la orden recoge el grupo, que el borrador de abril no tenía, como el "
        "periodo de la factura recapitulativa: la fecha de inicio y la de fin "
        "llegan igual. El esquema de Facturae lo hace **obligatorio** en las "
        "recapitulativas y en el servicio prestado temporalmente; la orden "
        "solo habla de las recapitulativas. Medido: 9 de las 14 facturas de "
        "aquí lo traen",
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
        "unidad de medida", "UnitOfMeasure", "BT-130", OTRA_LISTA,
        "dos cosas a la vez, y las dos hay que hacerlas. En la copia es "
        "`BT-130`, que en UBL va en el atributo `unitCode` de la cantidad "
        "(hasta el 13-10-2026 esta fila decía BT-129, porque el borrador de "
        "abril no tenía BT-130 y la orden sí), y el código **no es el "
        "mismo vocabulario**: "
        "Facturae tiene su lista de 36 valores de dos dígitos y la norma pide "
        "UN/ECE, recomendaciones 20 y 21. Medido el 21-09-2026 sobre el propio "
        "esquema de Facturae: de sus 36 códigos, 13 llevan el europeo en su "
        "etiqueta y vale tal cual, 16 lo llevan pero hay que ponerle una `X` "
        "delante -son códigos de embalaje, de la 21-, 1 solo cuadra en "
        "mayúsculas (`KWh`) y **6 no lo llevan en absoluto**. Entre esos seis "
        "está `01`, «Units», que es justo el que escriben las 18 líneas "
        "medidas aquí: en la copia es `C62`, y eso lo decide quien copia. "
        "Y una tercera cuando falta: `BT-130` es obligatorio y "
        "`UnitOfMeasure` no, así que una línea sin unidad no se copia sin que "
        "quien copia le ponga una. Eso ya lo dice `BR-23` de la propia "
        "factura, y por eso no hay nota aquí. Medido: 3 de las facturas de "
        "aquí traen alguna línea sin unidad",
    ),
    Correspondencia(
        "precio unitario", "UnitPriceWithoutTax", "BT-146", IGUAL,
        "el precio neto del artículo, sin impuestos, en los dos sitios, y el "
        "de una unidad: «precio de la unidad de bien o servicio», dice el "
        "esquema de Facturae. La orden recoge además `BT-149`, el número de "
        "unidades a las que se aplica el precio, que es opcional y Facturae "
        "no tiene, así que se queda vacío, como `BT-154`: un campo opcional "
        "sin origen",
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
        "categoría de IVA de la línea", "TaxTypeCode", "BT-151 y BT-ES-24",
        OTRA_LISTA,
        "el mismo hueco que un piso más arriba: Facturae dice **qué impuesto "
        "es** -01 IVA, 03 IGIC- y la norma pide de qué **categoría** es -S, Z, "
        "E, AE, K- en la lista UNCL5305. No es traducir un código por otro: "
        "hay que deducirlo del impuesto y del tipo, y el validador ya lo hace "
        "para poder correr las BR-S-*. Del mismo código sale `BT-ES-24`, el "
        "calificador de la clave de régimen de la línea, que dice de qué "
        "impuesto es: el 01 de Facturae es «IVA», el 03 «IGIC» y el 02 "
        "«IPSI». Esa parte sí se traduce uno por uno; la clave misma no, "
        "ver su fila",
    ),
    Correspondencia(
        "tipo de IVA de la línea", "TaxRate", "BT-152", IGUAL,
        "el porcentaje, que es un número y no un código",
    ),
    Correspondencia(
        "clave de régimen", "(no lo tiene)", "BG-32 (BT-160 y BT-161)",
        SE_INVENTA,
        "y es de las filas más caras de toda la tabla, porque el destino es "
        "**obligatorio**: el anexo pide una clave de régimen por línea, 1..2, "
        "como una propiedad del artículo llamada «REGI», con su lista L3A, "
        "L3B o L3C según el impuesto -`SPFE-CLAVE-DE-REGIMEN` ya lo exige del "
        "lado de la copia-. Facturae **no tiene ese concepto**. Esta fila dijo "
        "hasta el 22-09-2026 que lo tenía, y era `SpecialTaxableEventCode`, y "
        "estaba mal: ése solo distingue dos casos -01 «operación sujeta y "
        "exenta» y 02 «operación no sujeta»- y en L3A el `01` es «operación "
        "de régimen general no incluida en otras claves», que es justo lo "
        "contrario. El mismo dígito diciendo lo otro, como en el medio de "
        "pago. Medido: las 3 facturas de aquí que traen fiscalidad especial "
        "traen el `01`. Lo que hay que escribir en la copia lo decide quien "
        "copia, y en el caso corriente es `01` por régimen general. Ojo "
        "además a que la L3A de la orden **viene recortada**: no trae las "
        "claves 18, 19 y 20 del borrador de abril -el recargo de "
        "equivalencia, el de agricultura, ganadería y pesca y el régimen "
        "simplificado-, que es lo que la AEAT había anunciado el 10-09-2026. "
        "El recargo ya no se dice con una clave: se dice con la categoría N "
        "en el desglose, ver su fila en la primera familia. El calificador de "
        "la clave, `BT-ES-24`, sí sale de la factura: ver la fila de la "
        "categoría de la línea",
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
        "porcentaje del cargo del documento", "ChargeRate", "BT-101", NO_LO_PIDEN,
        "el mismo caso que el del descuento, en el otro sentido. Medido en los "
        "dos niveles juntos, el del documento y el de la línea: 3 de 14",
    ),
    Correspondencia(
        "porcentaje del cargo de línea", "ChargeRate", "BT-143", IGUAL,
        "la orden recoge en la línea el porcentaje del cargo y su base (BT-143 "
        "y BT-142), que el borrador de abril no tenía, para los impuestos y "
        "tasas de cada línea. El porcentaje llega igual. Hasta el 11-10-2026 "
        "esta fila iba junto con la del documento, «el anexo no lo pide». La "
        "base no llega: Facturae no la escribe en sus cargos (su esquema dice "
        "que el porcentaje es «sobre el TIB», y ese importe no va en el "
        "cargo), así que `BT-142`, que es opcional, se queda vacío. Donde sí "
        "hay base es en los impuestos de la línea que no son IVA, en su "
        "propia fila",
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
        "lo mismo que los descuentos de línea, sumando en vez de restar. Con "
        "una cosa más que poner: la orden hace obligatorio en cada cargo de "
        "línea `BT-ES-22`, un código de la L9, que es la lista de impuestos y "
        "tasas, y un cargo de Facturae no es ninguna de las dos cosas. Para "
        "él la L9 tiene «RESTO», otros cargos, y lo pone quien copia, siempre "
        "el mismo; sin él, `SPFE-IMPUESTO-O-TASA` acusa la copia. Los cargos "
        "del documento no lo piden: allí el código va solo con un impuesto. "
        "Medido: 6 de 14",
    ),
    Correspondencia(
        "impuesto que no es IVA", "TaxesOutputs",
        "BG-28 (BT-141, BT-142, BT-143 y BT-ES-22), o BG-21 (BT-99) con "
        "BG-ES-2 (BT-ES-6, BT-ES-7, BT-ES-8 y BT-ES-9)", OTRA_LISTA,
        "Facturae escribe en los impuestos repercutidos de cada línea, junto "
        "al IVA, cualquier otro de su lista (el 05 «otro», el 07 de los "
        "impuestos especiales y los demás), con su base, su tipo y su cuota. "
        "En la copia, lo que no es IVA, IGIC ni IPSI no tiene categoría en la "
        "L4 y va como cargo, de una de dos maneras y solo de una. En la "
        "línea, que es para lo que la orden recoge la base y el tipo: la "
        "cuota en `BT-141`, la base en `BT-142` y el tipo en `BT-143`. O en "
        "el documento, como un cargo con su detalle (BG-ES-2: la base, el "
        "tipo, la cuota y el código, `BT-ES-6` a `BT-ES-9`). Los dos suman a "
        "la base de la factura (`BT-109`), así que escrito en los dos sitios "
        "se cuenta dos veces. Lo que no se copia es el código: `BT-ES-22` en "
        "la línea y `BT-ES-9` en el documento son obligatorios y salen de la "
        "L9, que tiene uno por cada impuesto especial (hidrocarburos, "
        "cerveza, electricidad, carbón...) donde Facturae tiene un solo 07 "
        "para todos: cuál es no lo dice la factura, y lo pone quien copia "
        "sabiendo qué impuesto cobró. Tampoco tiene Facturae la razón del "
        "cargo de línea, `BT-144`, que también es obligatoria. Y en la línea, "
        "como cargo suma: el importe neto (`BT-131`) lo lleva dentro, y deja "
        "de ser el `GrossAmount` de Facturae. Hasta el 13-10-2026 esta fila "
        "solo daba la línea. Medido: ninguna de las facturas de aquí lo trae; "
        "en sus líneas escriben el 01 o el 02",
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
        "mediante tarjeta» y el 19 europeo es un abono de cámara de "
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

    # La sexta familia: las referencias. Se escribe sabiendo que casi nada
    # llega, y por eso hay que escribirla. Facturae sabe llevar siete
    # referencias -el pedido y el contrato, cada uno del emisor y del
    # receptor, el expediente, el albarán y el número de línea del pedido- y
    # el anexo **no recoge ninguna**: en sus 116 términos no está ni uno de
    # `BT-11` a `BT-19`, ni `BT-132`. Medido el 22-09-2026 sobre las 14: 8
    # traen alguna referencia escrita y **ninguna de las 14 la trae en la
    # cabecera**, que es el otro hallazgo de aquí.
    #
    # Porque Facturae las escribe **dentro de cada línea** y la norma las pone
    # en el documento. Una factura puede traer dos albaranes distintos donde
    # la copia tiene un campo: 3 de las 11 que traen albarán traen más de uno.
    #
    # Y queda libre un hueco de referencia, `BT-10`, que no es para esto. El
    # anexo lo define como «un identificador asignado por el comprador para
    # especificar rutas internas de la factura». Poner ahí el pedido es el
    # fallo del medio de pago otra vez: la copia vale y dice otra cosa. Por eso
    # esta familia saca nota siendo toda «el anexo no lo pide», que es la
    # primera vez que pasa: lo que se avisa no es la falta, es el hueco.
    #
    # Hasta el 07-10-2026 aquí se añadía que lo que en Facturae encamina -los
    # centros administrativos- tenía sus propios campos españoles, `BT-ES-9`,
    # `BT-ES-10` y `BT-ES-11`. Era el borrador de abril. El anexo de la orden
    # no recoge los centros, y esos tres números son ahora otra cosa: `BT-ES-10`
    # es la línea `SUPL` de los suplidos. Si los centros acaban en `BT-10`, la
    # orden no lo dice.
    Correspondencia(
        "referencia del pedido del comprador", "ReceiverTransactionReference",
        "BT-13", NO_LO_PIDEN,
        "«Referencia de pedido», dice el esquema, y el pedido lo hace el "
        "comprador: es BT-13. La norma lo tiene y el anexo no lo recoge, así "
        "que llega a la copia si quien copia lo escribe y no lo mira nadie. Lo "
        "que no se puede es ponerlo en BT-10 para que no se pierda. Medido el "
        "22-09-2026: 5 de 14, las 5 dentro de la línea y ninguna en la "
        "cabecera, que es donde Facturae también lo admite",
    ),
    Correspondencia(
        "referencia del pedido del vendedor", "IssuerTransactionReference",
        "BT-14", NO_LO_PIDEN,
        "el mismo dato por el otro lado -el número que el vendedor le da a la "
        "operación-, que en la norma es otro término, BT-14. Tampoco está en "
        "el anexo. Medido: 5 de 14, y siempre junto al del comprador",
    ),
    Correspondencia(
        "referencia del contrato del comprador", "ReceiverContractReference",
        "BT-12", NO_LO_PIDEN,
        "aquí los dos formatos ni siquiera cuentan igual: Facturae guarda el "
        "contrato del emisor y el del receptor en dos elementos y la norma "
        "tiene **un solo** BT-12. Si hubiera que escribirlo habría que elegir "
        "cuál de los dos es el contrato de la factura; como el anexo no lo "
        "recoge, la elección no llega a hacerse. Medido: 5 de 14",
    ),
    Correspondencia(
        "referencia del contrato del vendedor", "IssuerContractReference",
        "BT-12", NO_LO_PIDEN,
        "el otro de los dos, con el mismo destino y el mismo final. Medido: 5 "
        "de 14",
    ),
    Correspondencia(
        "expediente de contratación", "FileReference", "BT-17", NO_LO_PIDEN,
        "el código del expediente, que en la norma es la referencia de la "
        "licitación o el lote, BT-17. El anexo no lo recoge, y es el que más "
        "raro resulta que no esté: una factura a una administración lo lleva "
        "casi siempre, y en FACe es parte de lo que la encamina. Medido: 3 de "
        "14",
    ),
    Correspondencia(
        "albarán", "DeliveryNotesReferences", "BT-16", NO_LO_PIDEN,
        "el aviso de entrega, BT-16. Además de no estar en el anexo, es donde "
        "se ve el corte: Facturae pone los albaranes **dentro de cada línea** "
        "y `DeliveryNote` es `maxOccurs=\"unbounded\"`, mientras que la norma "
        "tiene una referencia por documento. Medido: 11 de las 14 traen el "
        "bloque, 8 escriben algo dentro -en 3 el número es un espacio en "
        "blanco- y **3 traen más de un albarán distinto**, así que este corte "
        "sí se ha visto, al revés que el de los vencimientos",
    ),
    Correspondencia(
        "número de línea del pedido", "SequenceNumber", "BT-132", NO_LO_PIDEN,
        "éste es el que la familia de las líneas se negó a usar como "
        "identificador de línea, y aquí se ve por qué: significa la línea "
        "**del pedido**, que en la norma es BT-132, y el anexo no lo recoge. "
        "De propina, el esquema lo declara `xs:double`, así que las tres "
        "facturas que lo traen escriben `1.0` y `2.0`: una referencia con "
        "decimales. Medido: 3 de 14",
    ),
    Correspondencia(
        "las fechas de las referencias",
        "IssuerTransactionDate, ReceiverTransactionDate, IssuerContractDate, "
        "ReceiverContractDate, FileDate y DeliveryNoteDate", "", SIN_SITIO,
        "seis fechas que no tienen adónde ir **aunque sus referencias sí lo "
        "tuvieran**: para la norma una referencia es un identificador suelto y "
        "ninguna de BT-12 a BT-17 lleva fecha al lado. Se quedan en el "
        "original y no entran en la lista de lo que se queda, porque su "
        "referencia tampoco viaja y decirlo dos veces no ayuda a nadie. "
        "Medido: 3 de 14 traen las cinco de la línea y 3 la del albarán",
    ),
    Correspondencia(
        "factura asociada", "RelatedInvoice", "BG-3 (BT-25)", IGUAL,
        "«Número y Serie de acuerdo Emisor/Receptor», y ya viene **junto**: es "
        "el único sitio de Facturae donde la serie y el número van en un solo "
        "campo, justo como los quiere BT-25. Da la vuelta a lo de BT-1, donde "
        "hay que pegarlos. Lo que se complica es lo de al lado, dos filas más "
        "abajo. Medido: ninguna de las 14 la trae",
    ),
    Correspondencia(
        "factura rectificada", "Corrective", "BG-3 (BT-25)", OTRO_CORTE,
        "el bloque de la rectificativa guarda el número y la serie de la "
        "rectificada en dos elementos, y BT-25 los pide juntos: se pegan como "
        "en BT-1 y por la misma razón. Que esta fila exista no contradice a "
        "`sintaxis.py`, que deja `facturas_previas` sin mapa en Facturae: allí "
        "se decide **qué se puede validar** -y con el criterio 03 se rectifica "
        "un periodo entero, sin número, así que leer el bloque como BG-3 "
        "acusaría a esas de no llevar referencia- y aquí se dice **qué se "
        "escribe** cuando sí lo hay. Son dos preguntas distintas sobre el "
        "mismo elemento, como con la unidad de medida. El resto de la "
        "rectificativa va en las filas de debajo: en la orden, el tipo, la "
        "modalidad y los importes rectificados van en tres usos más de BG-24, "
        "con «RECT:TIPO», «RECT:MODALIDAD» y «RECT:IMPORTES». Hasta el "
        "07-10-2026 aquí se decía que esperaban, en la extensión española "
        "`BG-ES-1` del borrador de abril, a que saliera el texto que los "
        "movía; salió, y en la orden `BG-ES-1` son los datos del tercero",
    ),
    Correspondencia(
        "fecha de la factura rectificada", "InvoiceIssueDate", "BT-26", IGUAL,
        "el mismo dato, y aun así hay que mirarlo: el anexo pone BT-26 en "
        "**1..1** dentro de BG-3 y Facturae solo obliga a escribir esta fecha "
        "cuando el criterio de rectificación es 01 o 02. Sin ella no se monta "
        "el grupo, y no hay de dónde sacarla: la factura asociada de la fila "
        "de arriba no trae ninguna",
    ),
    Correspondencia(
        "motivo de la rectificación", "ReasonCode",
        "BG-24 (BT-ES-27), con «RECT:TIPO»", OTRA_LISTA,
        "Facturae dice qué se corrige (del 01 al 16, qué dato estaba mal: el "
        "número, el NIF, la base...; el 80 y el 81, qué cuotas se calcularon "
        "mal; del 82 al 85, por qué cambió la base) y "
        "la L2.A de la orden dice al amparo de qué: R1 el error fundado en "
        "derecho y los apartados uno, dos y seis del artículo 80 de la Ley "
        "del IVA, R2 el concurso del 80.3, R3 los créditos incobrables del "
        "80.4 y R4 el resto. Una parte se traduce: el 82 (envases devueltos) "
        "y el 83 (descuentos) son el 80.1 y el 84 (resolución firme) el "
        "80.2, o sea R1, y el 85 es el concurso, R2. El resto no: del 01 al "
        "16, el 80 y el 81 dicen qué estaba mal y no por qué, que es lo "
        "que separa el R1 del R4, y el R3 no tiene código en Facturae. "
        "Copiado tal cual, el código no está en la L2.A y "
        "`SPFE-RECTIFICATIVA` lo da por error. Medido: ninguna de las "
        "facturas de aquí es rectificativa",
    ),
    Correspondencia(
        "método de la rectificación", "CorrectionMethod",
        "BG-24 (BT-ES-28), con «RECT:MODALIDAD»", OTRA_LISTA,
        "Facturae tiene cuatro métodos y la L2.B dos modalidades. Dos se "
        "traducen: el 01, rectificación íntegra, es la S de sustitución, y "
        "el 02, por diferencias, es la I. Los otros dos dicen otra cosa: el "
        "03 es un descuento por volumen sobre un periodo (la rectificativa "
        "que no señala a ninguna factura, ver la fila de la factura "
        "rectificada) y el 04 dice que la rectificación la autorizó la "
        "Agencia Tributaria. Ninguno de los dos dice si se sustituye o se "
        "corrige la diferencia, y eso lo pone quien copia",
    ),
    Correspondencia(
        "importes rectificados", "(no lo tiene)",
        "BG-24 (BT-123 y BT-ES-29), con «RECT:IMPORTES»", SE_INVENTA,
        "solo en una sustitución que se hace con una sola factura, la que "
        "lleva los importes correctos: la orden pide entonces lo que decía "
        "la rectificada, hasta cinco veces, cada uno con su código de la "
        "L2.C (la base, la cuota o la cuota del recargo) y el importe en "
        "BT-123. Facturae no guarda los importes de la factura rectificada, "
        "ni en el bloque de la rectificativa ni en ninguna parte: los saca "
        "quien copia de la original. Sin ellos, en una sustitución, "
        "`SPFE-RECTIFICATIVA` sale como nota, porque la factura no dice si "
        "se optó por una sola",
    ),
    Correspondencia(
        "documento adjunto", "Attachment", "", SIN_SITIO,
        "el fichero pegado a la factura, en base64, y la copia no puede "
        "llevarlo: «las copias fieles remitidas a la solución pública de "
        "facturación electrónica no podrán incorporar otros ficheros "
        "integrados o embebidos», dice el artículo 4.4 de la orden. Hasta el "
        "07-10-2026 esta fila decía «llega, pero el anexo no lo pide», con "
        "destino BT-125: la norma tiene el término, y el anexo no recoge ni "
        "ése ni BT-124, la dirección del documento externo. Tampoco habría "
        "grupo: el anexo de la orden usa BG-24 cinco veces, todas con valores "
        "fijos y para otra cosa -el QR, la autorización y tres para las "
        "rectificativas-, y un adjunto de Facturae no tiene referencia -lleva "
        "el fichero- y BT-122 es obligatorio en el grupo. Medido: 2 de 14",
    ),
    Correspondencia(
        "el QR y la autorización", "(no lo tiene)",
        "BG-24 (BT-122, BT-123, BT-ES-25 y BT-ES-26)", SE_INVENTA,
        "dos de los cinco usos que el anexo de la orden da al grupo de "
        "documentos justificativos son contenido que la factura no tiene: el "
        "**QR fiscal** del artículo 6.5 del RD 1619/2012 -BT-122 con «QR» de "
        "la L10, `urn:aeat:names:specification:schema:QR`; BT-123 con "
        "«VERIFACTU» o «TICKETBAI», que la orden deja opcional, y la "
        "dirección en cbc:UUID, `BT-ES-25`- y el **número de la "
        "autorización** de facturación, con «AUT» y el número en cbc:UUID "
        "(`BT-ES-26`). Ninguno de los dos está en "
        "Facturae, así que quien copia los saca de su sistema o deja el grupo "
        "vacío, que los dos son opcionales. Se escribe porque un conversor que "
        "solo mire el XML no puede ponerlos, y eso hay que saberlo antes y no "
        "después. Hasta el 07-10-2026 esta fila daba lo del borrador de "
        "abril: el valor con «ubl:», la descripción obligatoria y la "
        "dirección en `BT-ES-47`",
    ),

    # La séptima familia: el desglose del IVA. Las tres primeras filas son de
    # las que no dan trabajo -base, cuota y tipo, mismo dato- y están escritas
    # por las tres que vienen detrás, que son de las caras: la categoría, que
    # hay que deducir; el motivo de la exención, que Facturae guarda en texto
    # libre dentro de una línea; y su código, que sale de una lista que el
    # formato no conoce.
    #
    # Medido el 22-09-2026 sobre las 14: 4 traen más de una entrada en el
    # desglose, los impuestos escritos son 17 veces el `01` -IVA- y una el
    # `02` -IPSI-, y **3 ficheros traen una entrada al 0 %**. Esos tres son la
    # misma factura firmada de tres maneras, y se dicen como tres porque la
    # tabla cuenta ficheros; lo que importa es que el caso existe aquí.
    Correspondencia(
        "base por categoría", "TaxableBase", "BG-23 (BT-116)", IGUAL,
        "la base de cada entrada del desglose, que es el mismo dato en los "
        "dos. Lo que cambia es **por qué se agrupa**: Facturae abre una "
        "entrada por impuesto y tipo, y la norma una por categoría y tipo. "
        "Con un solo impuesto coinciden; con IVA e IPSI en la misma factura "
        "-que aquí pasa en una- son dos categorías distintas y el reparto ya "
        "viene hecho. Hay una excepción, el régimen del grupo de entidades: "
        "ahí BT-116 no es esta base, ver su fila más abajo",
    ),
    Correspondencia(
        "cuota por categoría", "TaxAmount", "BT-117", IGUAL,
        "la cuota de esa misma entrada. Ojo con el recargo de equivalencia, "
        "que Facturae declara dentro de la misma entrada que el IVA y la "
        "orden pone en una entrada más del desglose, con la categoría N: su "
        "cuota también es un BT-117, y por eso la cuota total llega igual. "
        "Está en la primera familia. Hasta el 07-10-2026 aquí se decía que la "
        "copia se lo llevaba a un grupo español, que era el borrador de abril",
    ),
    Correspondencia(
        "impuesto del desglose", "TaxTypeCode", "BT-118", OTRA_LISTA,
        "el mismo hueco que en la línea, y aquí es **obligatorio**: BT-118 es "
        "1..1 en el anexo. Facturae dice qué impuesto es -01 IVA, 02 IPSI, 03 "
        "IGIC- y la norma pide de qué categoría es, en UNCL5305. Con tipo "
        "positivo la deducción está forzada y el validador ya la hace; **al "
        "0 % no**: un cero puede ser exenta, no sujeta, tipo cero, "
        "intracomunitaria, exportación o inversión del sujeto pasivo -E, O, "
        "Z, K, G o AE-, y el código del impuesto no distingue ninguna. Medido: "
        "3 de 14 traen una entrada al 0 %",
    ),
    Correspondencia(
        "fiscalidad especial", "SpecialTaxableEventCode", "BT-118", OTRA_LISTA,
        "esto es lo único con lo que Facturae estrecha ese cero, y estrecha a "
        "dos: su `01` es «operación sujeta y exenta», que en UNCL5305 es la "
        "**E**, y su `02` es «operación no sujeta», que es la **O**. Vive en "
        "la línea y no en el impuesto, así que hay que mirarlas todas y que "
        "coincidan; el validador ya lo hace para poder correr las BR-E-* y "
        "BR-O-*. Lo que no se puede es confundirlo con la clave de régimen, "
        "que es otra lista y otra cosa: ver su fila en la familia de las "
        "líneas",
    ),
    Correspondencia(
        "tipo por categoría", "TaxRate", "BT-119", IGUAL,
        "el porcentaje, igual que en la línea. Con dos avisos del propio "
        "esquema de Facturae, que la copia no hereda: admite **ocho "
        "decimales** donde la norma trabaja con dos, y dice que «no siempre "
        "son porcentajes» -hay impuestos con tipos por unidad-, mientras que "
        "BT-119 es un porcentaje y nada más",
    ),
    Correspondencia(
        "motivo de la exención", "SpecialTaxableEventReason", "BT-120",
        OTRO_CORTE,
        "y es el corte más incómodo de toda la tabla, porque hay que **leer "
        "texto libre**. La norma quiere el motivo colgando de la entrada del "
        "desglose; Facturae lo pone en la línea y en una cadena que empieza "
        "por el código del impuesto al que se refiere -lo manda su propio "
        "esquema: «el motivo irá precedido del código del impuesto; por "
        "ejemplo: 07 exenta por…»-. Quien copie tiene que partir esa cadena "
        "para saber de qué impuesto habla, y ni eso es fiable: la muestra "
        "oficial del Ministerio escribe «Concepto exento por el motivo aquí "
        "definido», sin código delante. Y si no lo hace, el motivo no "
        "llega por ningún otro sitio: la nota de línea, BT-127, no está en el "
        "anexo. Importa porque en la copia el motivo deja de ser opcional en "
        "cuanto la categoría es E: lo exige BR-E-10",
    ),
    Correspondencia(
        "código del motivo de la exención", "(no lo tiene)", "BT-121 y BT-195",
        SE_INVENTA,
        "el anexo pide el código de la lista **CEF VATEX** -y dice que solo "
        "valen los `VATEX-EU` y `VATEX-ES`-, en el desglose y también en la "
        "línea. Facturae no tiene ese código en ninguna parte: escribe el "
        "motivo en prosa. Lo elige quien copia, leyendo esa prosa, o deja los "
        "dos campos vacíos y se queda con el texto",
    ),
    Correspondencia(
        "base del grupo de entidades", "SpecialTaxableBase",
        "BG-23 (BT-116)", OTRO_CORTE,
        "el régimen especial del grupo de entidades obliga a escribir dos "
        "bases para la misma operación -la del coste de adquisición y la que "
        "habría sido sin el régimen-, y Facturae las pone juntas en la "
        "entrada del impuesto: ésta y `TaxableBase`. La orden, para el nivel "
        "avanzado, las separa: en el desglose, BT-116 lleva «la base "
        "imponible a coste», que es ésta, "
        "con la categoría N de la L4, y en la línea BT-131 lleva «el importe "
        "total de la contraprestación». Así que en esa entrada BT-116 no es "
        "`TaxableBase`, que es lo que sale de copiar campo a campo. Hasta el "
        "07-10-2026 esta fila decía que el anexo le daba uno de sus grupos "
        "españoles, un BG-34 con la línea REGE: era el borrador de abril, y "
        "la orden lo quitó. Medido: ninguna de las 14 lo trae",
    ),

    # La octava familia: la cabecera. Es la que más filas tiene con «lo pone
    # quien copia», y no por casualidad: la cabecera es donde la copia se
    # identifica a sí misma -qué norma sigue, qué proceso es- y eso no está
    # en el original, que no sabe que va a copiarse.
    Correspondencia(
        "fecha de expedición", "IssueDate", "BT-2", IGUAL,
        "el mismo dato y obligatorio en los dos. La de operación, que es la "
        "otra fecha de la cabecera, está en la segunda familia",
    ),
    Correspondencia(
        "tipo de factura", "InvoiceDocumentType", "BT-3", OTRA_LISTA,
        "y hay que mirar en **tres sitios** para escribir un solo código. "
        "Facturae reparte lo que la norma junta en BT-3: `InvoiceDocumentType` "
        "dice si es completa, abreviada o rectificativa; `InvoiceClass` si es "
        "original, rectificativa o recapitulativa; y quién la expide está más "
        "arriba todavía, en `FileHeader/InvoiceIssuerType` -`EM` emisor, `RE` "
        "receptor, `TE` tercero-, que es lo que separa la 380 de la **389** y "
        "la 384 de la **471**. Medido: las 14 de aquí son `FC` y `OO`, y una "
        "la expide el destinatario (`RE`): 13 son 380 y una 389. Hasta el "
        "13-10-2026 aquí se decía que las 14 eran 380, sin haber mirado quién "
        "las expide. La L1 de la orden admite el 389 y el 471, igual que la de abril; "
        "hasta el 07-10-2026 aquí se decía que el 389 lo metía el anuncio del "
        "10-09-2026, y no era nuevo. Ojo a que `en16931.py` traduce hoy el "
        "criterio 03 a un **381** que la L1 española no tiene: está en "
        "HALLAZGOS y sigue pendiente",
    ),
    Correspondencia(
        "moneda de la factura", "InvoiceCurrencyCode", "BT-5", IGUAL,
        "el código ISO 4217, igual en los dos, y obligatorio en los dos. "
        "Medido: las 14 son EUR",
    ),
    Correspondencia(
        "moneda del impuesto", "TaxCurrencyCode", "BT-6", IGUAL,
        "el mismo código, y aun así es de las filas peligrosas: en Facturae "
        "este campo es **obligatorio** y en la norma BT-6 solo tiene sentido "
        "cuando la contabilidad del IVA va en otra moneda. Copiarlo siempre "
        "-que es lo que sale de copiar campo a campo- obliga a escribir "
        "también BT-111, porque `BR-53` lo exige en cuanto BT-6 está "
        "presente, y ese número Facturae no lo tiene. Medido: las 14 escriben "
        "la misma moneda que la factura, así que copiarlo no aporta nada y "
        "rompe la copia",
    ),
    Correspondencia(
        "cuota en la moneda de contabilización", "(no lo tiene)", "BT-111",
        SE_INVENTA,
        "la otra mitad de la fila anterior. El anexo lo pide cuando la moneda "
        "de la factura no es el euro, y Facturae no lleva la cuota en la "
        "moneda de contabilización: lleva el tipo de cambio y su fecha "
        "-`ExchangeRateDetails`-, así que el número hay que **calcularlo**, y "
        "cómo se redondea lo decide quien copia. Con la misma moneda es el "
        "mismo importe que BT-110, que es la salida más sencilla si se ha "
        "escrito BT-6. Medido: ninguna de las 14 trae tipo de cambio",
    ),
    Correspondencia(
        "tipo de cambio", "ExchangeRate", "BT-167", POR_DECIDIR,
        "el dato es el mismo: Facturae lo define como el cambio vendedor del "
        "Banco de España vigente en el devengo (artículo 79.once de la ley "
        "del IVA), y la orden pide en `BT-167` el tipo de cambio aplicado "
        "para contabilizar el IVA cuando la factura no va en euros. Lo que no "
        "se sabe es cómo se escribe. `BT-167` es de la edición de 2026 de la "
        "norma, la orden no le da ruta y lo declara «Importe», y en qué "
        "elemento de UBL va y en qué sentido se lee (euros por unidad de la "
        "otra moneda, o al revés) lo dice `UNE-CEN/TS 16931-3-2:2026`, que "
        "aquí no está. La fecha del cambio, `ExchangeRateDate`, no tiene "
        "término en el anexo. Medido: ninguna de las facturas de aquí trae "
        "tipo de cambio",
    ),
    Correspondencia(
        "descripción de la factura", "InvoiceDescription", "BG-1 (BT-22)",
        OTRO_CORTE,
        "la norma tiene **un grupo repetible** de notas y Facturae reparte lo "
        "mismo en tres campos que no se parecen entre sí: la descripción "
        "general de la cabecera, los `LegalLiterals` -los textos que la ley "
        "obliga a imprimir, «operación exenta por el artículo…»- y la "
        "información adicional del bloque de datos adicionales. Quien copie "
        "decide cuáles van y en qué orden, porque BT-22 es obligatorio dentro "
        "del grupo y no admite matices. Medido: ninguna de las 14 trae "
        "ninguno de los tres",
    ),
    Correspondencia(
        "identificador de la especificación", "(no lo tiene)",
        "BG-2 (BT-23 y BT-24)", SE_INVENTA,
        "las dos son **obligatorias** y de valor fijo, y son la fila que "
        "mejor explica por qué la copia no es la factura: BT-24 declara qué "
        "especificación sigue el documento, "
        "`urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:1.0.0:extended`, "
        "y BT-23 qué proceso es, "
        "`urn:aeat:names:specification:schema:profile:B2B`, fijo (ni siquiera "
        "distingue el B2G). La orden lo escribe con `ubl:` y la AEAT contestó "
        "el 13-10-2026 que el bueno es sin él, como va en el anexo de su portal "
        "del 21-10-2026. Una factura no dice eso de sí misma; "
        "lo dice quien la copia. Y de paso deja escrito que la copia se mide "
        "con la edición **2026** de la norma, que es la que trae términos como "
        "BT-179 y BT-180, a los que la orden pone sitio y no ruta. Hasta el "
        "07-10-2026 esta fila daba los dos valores del borrador de abril, "
        "`...2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0` y "
        "`...ubl:schema:B2B`, sin «profile:»",
    ),
    Correspondencia(
        "original o copia", "(no lo tiene)", "BT-ES-1", SE_INVENTA,
        "en una copia fiel, siempre «true»: el artículo 4.3 de la orden pide "
        "que la copia se identifique ahí, y sin él la toma por el original "
        "(`SPFE-COPIA`). Se escribe porque Facturae tiene algo que se le "
        "parece y no es esto: `InvoiceClass` distingue el original (`OO`, "
        "`OR`, `OC`) de la copia (`CO`, `CR`, `CC`), y habla de la factura, "
        "no de lo que se manda a la AEAT. La copia fiel lleva «true» sea "
        "cual sea su clase. Medido: todas las de aquí son `OO`",
    ),
    Correspondencia(
        "los huecos que el anexo deja abiertos", "(no lo tiene)",
        "BT-10, BT-20, BT-21, BT-114, BT-149, BT-154, BT-166, BT-ES-15 y "
        "BT-ES-23", SE_INVENTA,
        "nueve campos que el anexo recoge, que son opcionales o van en un "
        "grupo opcional, y que en Facturae no tienen origen ninguno: la "
        "referencia interna del comprador -ver la familia de las "
        "referencias-, las condiciones de pago en texto, el código de la "
        "nota de la lista UNTDID 4451 -las notas de Facturae no llevan "
        "código-, el importe de redondeo -sus totales ya vienen "
        "redondeados-, la cantidad a la que se aplica el precio y la "
        "descripción del artículo (ver sus filas, en la familia de las "
        "líneas), la hora de expedición, que el formato no guarda en "
        "ninguna parte, la minoración en nombre de un tercero (`BT-ES-15`, "
        "«MINO»: su ejemplo en la orden es la devolución de un suplido, y "
        "Facturae no tiene ese concepto; las subvenciones no son eso, ver su "
        "fila) y la "
        "situación del inmueble (`BT-ES-23`, de la L6), que va con la "
        "referencia catastral de la línea, y Facturae no guarda ninguna de "
        "las dos. Copiando de la factura, lo correcto es dejarlos vacíos. Se "
        "escriben porque el fallo aquí no es olvidarlos: es rellenarlos con "
        "lo que más se les parezca. Hasta el 13-10-2026 eran cinco, y "
        "`BT-149` y `BT-154` se decían vacíos solo en sus filas",
    ),

    # La novena familia: las partes. Las direcciones y los contactos ya están
    # en la segunda -son las filas «evidentes»- y lo que queda aquí es quién
    # es cada uno. Sale una sola nota, y de la fila que menos se espera: el
    # nombre.
    Correspondencia(
        "razón social", "CorporateName", "BT-27 del vendedor, BT-44 del comprador",
        IGUAL,
        "de una persona jurídica, el mismo dato: un nombre en un campo. "
        "Medido: 10 de 14 el vendedor y 11 el comprador",
    ),
    Correspondencia(
        "nombre de una persona física", "Individual",
        "BT-27 del vendedor, BT-44 del comprador", OTRO_CORTE,
        "y aquí Facturae guarda en **tres** campos -`Name`, `FirstSurname` y "
        "`SecondSurname`- lo que la copia pide en uno solo, que además es "
        "obligatorio. Nadie dice cómo se juntan: ni el orden -«Juana Mauriño» "
        "o «Mauriño, Juana»- ni qué hacer con el segundo apellido cuando "
        "falta, que es la mitad de los casos de aquí. Es el mismo problema de "
        "la serie y el número, con una diferencia que lo empeora: la serie se "
        "pega y ya está, y un nombre mal ordenado deja a la copia "
        "identificando a alguien de otra manera que el original. Ojo a que "
        "`sintaxis.py` resuelve esto mismo al revés y con razón: para **leer** "
        "una factura se queda solo con `Name`, porque pegarle los apellidos "
        "sería inventar un formato que nadie ha fijado. Para **escribir** la "
        "copia no vale prescindir de ellos: allí se pierden dos apellidos, y "
        "eso ya no es prudencia. Medido: 4 de "
        "14 el vendedor y 3 el comprador, y **solo uno de los siete** trae los "
        "tres campos escritos",
    ),
    Correspondencia(
        "NIF", "TaxIdentificationNumber",
        "BT-31, o BT-32 y BT-30, del vendedor; BT-48 o BT-47 del comprador",
        OTRO_CORTE,
        "el mismo número, y la orden le da dos sitios: como NIF-IVA, con "
        "«VAT» (`BT-31` del vendedor, `BT-48` del comprador), o como NIF, con "
        "«LOC» y el atributo `@schemeID` «FC» (`BT-32` y `BT-47`). En "
        "ninguno de los dos va tal cual. Como NIF-IVA lleva delante el "
        "prefijo ES, que la orden pide y que Facturae solo escribe en las "
        "operaciones intracomunitarias. Como NIF, el del vendedor va **dos "
        "veces**: la orden pide además `BT-30`, el identificador de "
        "inscripción legal, y lo describe como su NIF. `SPFE-NIF` acusa las "
        "dos cosas en la copia. Ojo a que `BT-47` es un término reutilizado: "
        "en la norma es el registro legal del comprador, en "
        "`cac:PartyLegalEntity`, y la orden lo pone en el mismo "
        "`cac:PartyTaxScheme` que el NIF. Hasta el 13-10-2026 esta fila "
        "decía «llega igual» a `BT-32` y `BT-48`, que es como lo tenía el "
        "borrador de abril, solo con «VAT». Medido: ninguna de las facturas "
        "de aquí escribe el prefijo de país, así que el número copiado tal "
        "cual en `BT-31` sale con `SPFE-NIF`",
    ),
    Correspondencia(
        "tercero que expide la factura", "ThirdParty",
        "BG-ES-1 (BT-ES-3, BT-ES-4 y BT-ES-5)", OTRO_CORTE,
        "Facturae lo escribe en la cabecera del fichero cuando quien expide "
        "es un tercero (`InvoiceIssuerType` `TE`), y la orden dentro del "
        "vendedor, con tres campos obligatorios: el nombre (`BT-ES-3`), el "
        "NIF (`BT-ES-4`) y la tipología (`BT-ES-5`), que para el que expide "
        "en lugar del vendedor es siempre «FacturaciónPorTercero». Llega con "
        "lo que les pasa a las partes: el NIF con sus dos sitios, con «VAT» "
        "y el prefijo ES o con «LOC» y «FC», y el nombre de una persona "
        "física en tres campos que la copia pide en uno; ver las dos filas "
        "de arriba. Ojo a que `RE`, la factura que expide el destinatario, "
        "no es esto: quien la expide es el comprador, y eso se dice en el "
        "tipo de factura (389 o 471), no en este grupo. Medido: ninguna de "
        "las facturas de aquí la expide un tercero",
    ),
    Correspondencia(
        "nombre comercial", "TradeName", "BT-28", NO_LO_PIDEN,
        "la norma tiene el nombre comercial del vendedor y el anexo no lo "
        "recoge, ni ése ni los demás identificadores de las partes: BT-29 y "
        "BT-34 del vendedor, BT-45, BT-46 y BT-49 del comprador. `BT-30` y "
        "`BT-47` sí los recoge, pero para el NIF (ver su fila); hasta el "
        "13-10-2026 esta fila los contaba entre los que no. De los dos, el "
        "anexo se queda con el nombre y el NIF. "
        "Medido: 8 de 14 el vendedor y 4 el comprador",
    ),
    Correspondencia(
        "datos registrales", "RegistrationData", "BT-33", OTRO_CORTE,
        "el registro mercantil es en Facturae un bloque con **seis** campos "
        "-libro, registro, hoja, folio, sección y tomo- y BT-33 es una línea "
        "de texto libre. Hay que redactarla, no copiarla, y cómo se redacta "
        "no lo dice ningún texto. Medido: 8 de 14 el vendedor y 3 el "
        "comprador",
    ),
    Correspondencia(
        "tipo de residencia", "ResidenceTypeCode", "", SIN_SITIO,
        "`R` residente, `E` extranjero, `U` residente en la UE. No hay "
        "término europeo, y no entra en la lista de lo que se queda en el "
        "original porque no se pierde nada: el país de la dirección dice lo "
        "mismo, y es obligatorio en los dos formatos. Se escribe la fila "
        "igual, porque al copiar campo a campo este es de los que tientan a "
        "buscarle sitio. Medido: las 14 lo traen, por obligación del esquema",
    ),
)

# Lo que la tabla tiene que cubrir para que las reglas de abajo no hablen de
# nada. Es el cepo de este módulo: si alguien quita una fila y deja la regla,
# el paquete no se monta. Un comentario pidiendo memoria no lo evitaría.
#
# `EquivalenceSurchargeAmount` salió de aquí el 07-10-2026, con la nota que lo
# miraba: con la orden, el recargo no cambia ninguna cifra de la copia. Su fila
# se queda en la tabla, que dice adónde va; lo que no hay es regla.
_LO_QUE_SE_MIRA = (
    "TotalTaxOutputs", "InvoiceTotal", "TotalTaxesWithheld",
    "TotalReimbursableExpenses",
    "TotalFinancialExpenses", "Subsidies",
    "InvoiceSeriesCode", "PostCodeAndTown",
    "LanguageName", "PlaceOfIssue",
    "TeleFax", "WebAddress", "CnoCnae", "AdditionalContactDetails",
    "UnitOfMeasure", "GrossAmount",
    "GeneralDiscounts", "GeneralSurcharges",
    "Installment", "InstallmentDueDate", "PaymentMeans",
    "BranchInSpainAddress", "OverseasBranchAddress",
    "CollectionAdditionalInformation",
    "ReceiverTransactionReference", "IssuerTransactionReference",
    "ReceiverContractReference", "IssuerContractReference",
    "FileReference", "DeliveryNotesReferences", "SequenceNumber",
    "RelatedInvoice", "Corrective",
    "TaxTypeCode", "TaxRate", "SpecialTaxableEventCode",
    "SpecialTaxableEventReason",
    "InvoiceCurrencyCode", "TaxCurrencyCode", "Individual",
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
# Las referencias que Facturae sabe llevar, con el nombre que se imprime. El
# orden es el del informe y no el del esquema: primero lo que más se usa.
#
# Las dos banderas dicen dónde se busca y qué se cuenta. `en_cabecera`: las
# tres primeras las admite también `InvoiceIssueData`, y las otras tres solo
# existen dentro de la línea. `del_documento`: si el término europeo es de
# documento, que varias líneas traigan valores distintos es algo que hay que
# elegir y se dice cuántos hay. El número de línea del pedido no lo es
# —BT-132 es de línea en los dos formatos—, así que ahí uno por línea es lo
# correcto y contarlos sería inventar un problema.
_REFERENCIAS = (
    ("ReceiverTransactionReference", "pedido del comprador", True, True),
    ("IssuerTransactionReference", "pedido del vendedor", False, True),
    ("ReceiverContractReference", "contrato del comprador", True, True),
    ("IssuerContractReference", "contrato del vendedor", False, True),
    ("FileReference", "expediente", True, True),
    ("SequenceNumber", "número de línea del pedido", False, False),
)

# Los dos valores de la fiscalidad especial de Facturae y la categoría
# europea que significan. No hay más: su esquema solo admite esos dos, y por
# eso al 0 % estrechan a dos de las seis posibles y no a una.
_FISCALIDAD_ESPECIAL = {
    "01": ("operación sujeta y exenta", "E"),
    "02": ("operación no sujeta", "O"),
}

_SIN_SITIO_EN_LAS_PARTES = (
    ("TeleFax", "fax"),
    ("WebAddress", "página web"),
    ("CnoCnae", "CNAE"),
    ("AdditionalContactDetails", "otros datos de contacto"),
)


def _suma_profunda(nodo, nombre: str) -> Decimal:
    """Lo que suman todos los elementos con ese nombre, estén donde estén.

    Para lo que Facturae escribe por partes sin poner el total al lado: las
    subvenciones van en un bloque cada una. Hasta el 07-10-2026 servía también
    para el recargo de equivalencia, que se declara en cada entrada del
    desglose; con la orden ya no hay nota que lo sume.
    """
    total = Decimal(0)
    for encontrado in nodo.xpath(f".//*[local-name()='{nombre}']"):
        cantidad = a_decimal(" ".join(encontrado.itertext()).strip())
        if cantidad is not None:
            total += cantidad
    return total


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
                "delante, y 6 no lo llevan. En la copia es BT-130, que en UBL "
                "va en un atributo de la cantidad.",
                campo=f"{etiqueta}Unidad de medida (BT-130 en la copia)",
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
                "El importe neto de una línea de la copia es GrossAmount y "
                "no TotalCost, y en esta factura los dos no valen lo mismo. "
                "El esquema define TotalCost como cantidad por precio y "
                "GrossAmount como TotalCost - DiscountAmount + "
                "ChargeAmount; BT-131 es el importe de la línea después de "
                "sus descuentos y cargos, que es el que cuadra con la suma de "
                "líneas. Copiar el otro no deja un hueco: deja un número que "
                "parece bueno.",
                campo=f"{etiqueta}Importe neto de las líneas (BT-131 en la copia)",
                esperado=f"{cifras.calculada(bruto_de_esas)} en la copia, que es "
                         "lo que suman sus GrossAmount",
                encontrado=f"{cifras.calculada(coste_de_esas)} si se copiara "
                           f"TotalCost, en {descuadradas} de {len(lineas)} líneas",
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
                f"(en UNCL4461, {_MEDIOS_DE_PAGO[m][2]})" for m in conocidos
            )
        else:
            esperado = ("un código de UNCL4461 elegido a mano: para éste no "
                        "hay equivalente que se pueda sostener")
        encontrado = ", ".join(
            f"{m} en esta factura"
            + (f", que aquí es {_MEDIOS_DE_PAGO[m][0]}"
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
                "códigos de Facturae existen los 19 en la lista europea "
                "queriendo decir otra cosa -diez tal cual y los nueve que "
                "empiezan por cero en cuanto se les quita-, así que copiar el "
                "dígito no da un error, da una factura válida que dice que se "
                "paga de otra manera. El 19 de aquí es la tarjeta y el 19 "
                "europeo es un abono de cámara de compensación.",
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
        # El tipo como se escribe en el resto del informe, 21% o 6,5%: el
        # texto del fichero con un espacio delante del signo decía «al
        # 21.00 %», con punto, en un «Debería ser».
        tipo = cifras.tipo(a_decimal(categorias[0][1]))
        esperado = (f"la categoría de la factura, al {tipo}, "
                    "en cada uno de los grupos de la copia")
    else:
        esperado = "una categoría de IVA en cada grupo de la copia"
    return [
        Incidencia(
            "COPIA-CARGO-IVA",
            NOTA,
            "Los descuentos y cargos generales de esta factura no llevan IVA "
            "propio, y en la copia tienen que llevarlo. La norma agrupa las "
            "minoraciones y los cargos del documento por categoría de IVA "
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


def _de_las_referencias(factura, etiqueta: str) -> list[Incidencia]:
    """Las referencias del original, que en la copia no tienen campo.

    Ésta es la primera nota que sale de filas que son todas «el anexo no lo
    pide», y hace falta decir por qué, porque la regla de este módulo es que
    eso no se cuenta: lo que llega y no mira nadie no es noticia.

    Aquí sí, por el hueco. El anexo se queda con **una** referencia de
    documento, `BT-10`, y no es ninguna de éstas: es el identificador que el
    comprador usa para encaminar la factura por dentro. Quien copie y no
    quiera perder el pedido lo va a poner ahí, porque es el único sitio que
    queda libre, y entonces la copia vale y dice otra cosa —el mismo fallo
    que copiar el dígito del medio de pago—. Avisar de eso sí es noticia.
    """
    lineas = _hijos(factura, "Items", "InvoiceLine")
    emision = _hijos(factura, "InvoiceIssueData")

    encontradas: list[str] = []
    for elemento, concepto, en_cabecera, del_documento in _REFERENCIAS:
        valores = []
        for linea in lineas:
            escrito = _texto(linea, elemento)
            if escrito and escrito not in valores:
                valores.append(escrito)
        if en_cabecera and emision:
            escrito = _texto(emision[0], elemento)
            if escrito and escrito not in valores:
                valores.append(escrito)
        if valores:
            encontradas.append(
                f"{concepto} ({len(valores)} distintos)"
                if del_documento and len(valores) > 1 else concepto
            )

    # El albarán cuelga de dos niveles más y se repite sin límite, así que se
    # cuenta aparte: es el que enseña el corte.
    albaranes: list[str] = []
    for linea in lineas:
        for uno in _hijos(linea, "DeliveryNotesReferences", "DeliveryNote"):
            escrito = _texto(uno, "DeliveryNoteNumber")
            if escrito and escrito not in albaranes:
                albaranes.append(escrito)
    if albaranes:
        encontradas.insert(
            0,
            "albarán" if len(albaranes) == 1
            else f"albarán ({len(albaranes)} distintos)",
        )

    if not encontradas:
        return []
    return [
        Incidencia(
            "COPIA-REFERENCIAS",
            NOTA,
            "Las referencias de esta factura no tienen campo en la copia. El "
            "anexo no recoge ninguno de los términos de referencia de la "
            "norma -de BT-11 a BT-19: pedido, contrato, albarán, "
            "expediente-, ni las fechas que Facturae les pone al lado, así "
            "que se omiten o van en una extensión y no las mira nadie. Ojo "
            "con el hueco que queda libre: BT-10 es la referencia del "
            "comprador, un identificador para sus rutas internas, y no el "
            "número del pedido. Y ojo con el sitio: aquí van dentro de cada "
            "línea y en la copia irían en el documento, así que si las líneas "
            "no traen la misma hay que elegir cuál viaja.",
            campo=f"{etiqueta}Referencias de la factura "
                  f"(BT-11 a BT-19, que el anexo no recoge)",
            encontrado=", ".join(encontradas),
        )
    ]


def _de_la_factura_previa(factura, etiqueta: str) -> list[Incidencia]:
    """La referencia a otra factura: lo que hay que pegar y lo que falta.

    De las dos maneras que tiene Facturae de señalar otra factura sale la
    misma nota, porque el problema es el mismo grupo: `BG-3` pide el número
    **con** su serie y una fecha de expedición que el anexo hace obligatoria.
    """
    incidencias = []
    asociada = _texto(factura, "AdditionalData", "RelatedInvoice")
    if asociada:
        incidencias.append(_nota_de_la_previa(
            etiqueta, "la factura asociada", asociada, "", junto=True))
    for corr in _hijos(factura, "InvoiceHeader", "Corrective"):
        numero = _texto(corr, "InvoiceNumber")
        # Sin número no hay a qué referirse: con el criterio 03 se rectifica
        # un periodo entero, y esa factura no señala a ninguna.
        if not numero:
            continue
        serie = _texto(corr, "InvoiceSeriesCode")
        incidencias.append(_nota_de_la_previa(
            etiqueta, "la factura rectificada", f"{serie}{numero}",
            _texto(corr, "InvoiceIssueDate"), junto=not serie))
    return incidencias


def _nota_de_la_previa(
    etiqueta: str, cual: str, referencia: str, fecha: str, junto: bool
) -> Incidencia:
    """La misma nota para los dos caminos, con lo que cambia entre ellos.

    `junto` no es un detalle de escritura: dice si el número ya viene pegado
    a su serie -la factura asociada- o hay que pegarlo -la rectificada-, que
    es justo lo que quien copia tiene que hacer y por eso se imprime.
    """
    if fecha:
        esperado = f"{referencia} y {fecha} en la copia"
    else:
        esperado = (f"{referencia} en la copia, y una fecha de expedición "
                    f"que esta factura no trae")
    encontrado = referencia if junto else f"{referencia}, en dos campos"
    return Incidencia(
        "COPIA-FACTURA-PREVIA",
        NOTA,
        "Esta factura se refiere a otra, y el grupo de la copia pide dos "
        "cosas que hay que mirar. El número va con su serie en un solo "
        "campo, BT-25, igual que el de la propia factura. Y la fecha de "
        "expedición de la referenciada, BT-26, el anexo la pone obligatoria "
        "dentro del grupo -en la norma europea no lo es-, así que sin ella no "
        "se puede montar: o se saca de donde no está, o la referencia entera "
        "se queda fuera.",
        campo=f"{etiqueta}Referencia a {cual} (BG-3 en la copia)",
        esperado=esperado,
        encontrado=encontrado,
    )


def _del_desglose(factura, etiqueta: str) -> list[Incidencia]:
    """La categoría que al 0 % no se puede deducir, y el motivo en prosa.

    Con tipo positivo no hay nada que decidir —IVA a tipo positivo es la S— y
    por eso esta regla solo mira los ceros. El resto del desglose llega igual.
    """
    a_cero = []
    for tax in _hijos(factura, "TaxesOutputs", "Tax"):
        escrito = _texto(tax, "TaxRate")
        if escrito and a_decimal(escrito) == 0:
            a_cero.append(_texto(tax, "TaxTypeCode") or "(sin impuesto)")
    if not a_cero:
        return []

    # La fiscalidad especial cuelga de la línea y no del impuesto, así que
    # solo estrecha cuando todas las líneas que la traen dicen lo mismo: dos
    # claves distintas no deciden la categoría de una entrada del desglose.
    claves: list[str] = []
    motivos: list[str] = []
    for linea in _hijos(factura, "Items", "InvoiceLine"):
        clave = _texto(linea, "SpecialTaxableEvent", "SpecialTaxableEventCode")
        if clave and clave not in claves:
            claves.append(clave)
        motivo = _texto(linea, "SpecialTaxableEvent",
                        "SpecialTaxableEventReason")
        if motivo and motivo not in motivos:
            motivos.append(motivo)

    unica = claves[0] if len(claves) == 1 else ""
    dice, categoria = _FISCALIDAD_ESPECIAL.get(unica, ("", ""))
    if categoria:
        esperado = (f"{categoria} en la copia, que es la categoría de "
                    f"UNCL5305 para {dice}")
        encontrado = (f"{', '.join(a_cero)} al 0 % en esta factura, y la "
                      f"fiscalidad especial {unica} en las líneas")
    else:
        esperado = ("una categoría de UNCL5305 elegida a mano: al 0 % caben "
                    "E, O, Z, K, G y AE, y ninguna se deduce de aquí")
        encontrado = (f"{', '.join(a_cero)} al 0 % en esta factura, "
                      f"sin fiscalidad especial que lo estreche")
    mensaje = (
        "Esta factura declara algo al 0 % y la copia tiene que decir de qué "
        "categoría es. BT-118 es obligatorio, y el código de impuesto de "
        "Facturae no lo dice: un cero puede ser una exenta, una no sujeta, un "
        "tipo cero, una intracomunitaria, una exportación o una inversión del "
        "sujeto pasivo. Lo único que estrecha es la fiscalidad especial de "
        "las líneas, y solo a dos: su 01 es la E y su 02 es la O."
    )
    if categoria == "E":
        mensaje += (
            " Y al ser exenta, en la copia el motivo deja de ser opcional "
            "-lo exige BR-E-10-: está en la línea, en texto libre, y el "
            "esquema manda escribirlo precedido del código del impuesto."
        )
    incidencias = [
        Incidencia(
            "COPIA-DESGLOSE-CERO",
            NOTA,
            mensaje,
            campo=f"{etiqueta}Categoría del desglose al 0 % "
                  f"(BT-118 en la copia)",
            esperado=esperado,
            encontrado=encontrado + (
                f", y el motivo escrito \"{motivos[0]}\"" if motivos else ""
            ),
        )
    ]
    return incidencias


def _de_la_moneda(factura, etiqueta: str) -> list[Incidencia]:
    """El campo que Facturae obliga a escribir y la copia no debería llevar.

    De todas las filas de la cabecera esta es la única que saca nota, y es
    porque el fallo va al revés que de costumbre: no se pierde un dato, se
    copia uno de más, y copiarlo **rompe la copia** —`BR-53` pide entonces
    `BT-111`, que en Facturae no existe—.
    """
    emision = _hijos(factura, "InvoiceIssueData")
    if not emision:
        return []
    del_impuesto = _texto(emision[0], "TaxCurrencyCode")
    if not del_impuesto:
        return []
    de_la_factura = _texto(emision[0], "InvoiceCurrencyCode")
    if del_impuesto == de_la_factura:
        esperado = (f"BT-6 vacío en la copia: la contabilidad del IVA va en "
                    f"{del_impuesto}, la misma moneda de la factura")
        encontrado = (f"{del_impuesto} en esta factura, escrito porque el "
                      f"esquema de Facturae lo exige siempre")
    else:
        esperado = (f"{del_impuesto} en BT-6 y la cuota en {del_impuesto} en "
                    f"BT-111, que hay que calcular")
        encontrado = (f"{del_impuesto} en esta factura, y la factura en "
                      f"{de_la_factura or '(sin moneda)'}")
    return [
        Incidencia(
            "COPIA-MONEDA-DEL-IVA",
            NOTA,
            "La moneda de contabilización del IVA es obligatoria en Facturae "
            "y en la copia no siempre debe ir. BT-6 solo tiene sentido cuando "
            "el IVA se contabiliza en otra moneda, y en cuanto se escribe, "
            "BR-53 exige además BT-111 -la cuota total en esa moneda-, que "
            "Facturae no lleva: lleva el tipo de cambio, así que ese número "
            "hay que calcularlo. Copiar el campo por estar escrito deja una "
            "copia que no cumple la norma por un dato que no aporta nada.",
            campo=f"{etiqueta}Moneda del IVA (BT-6 y BT-111 en la copia)",
            esperado=esperado,
            encontrado=encontrado,
        )
    ]


def _de_los_nombres(raiz) -> list[Incidencia]:
    """El nombre de una persona física, que va en tres campos y cabe en uno.

    Es de las partes y no de cada factura, como las direcciones de fuera: las
    partes son del fichero entero.
    """
    incidencias = []
    for parte, quien, destino in (
        ("SellerParty", "del vendedor", "BT-27"),
        ("BuyerParty", "del comprador", "BT-44"),
    ):
        for persona in raiz.xpath(
            f"./*[local-name()='Parties']/*[local-name()='{parte}']"
            f"/*[local-name()='Individual']"
        ):
            trozos = [
                _texto(persona, campo)
                for campo in ("Name", "FirstSurname", "SecondSurname")
            ]
            if not any(trozos):
                continue
            escritos = [t for t in trozos if t]
            incidencias.append(
                Incidencia(
                    "COPIA-NOMBRE",
                    NOTA,
                    "El nombre de una persona física va en tres campos en "
                    "Facturae -nombre, primer apellido y segundo apellido- y "
                    "en la copia va en uno solo, que además es obligatorio. "
                    "Hay que juntarlos, y ni el esquema ni el anexo dicen en "
                    "qué orden ni con qué separador: para quien después busque "
                    "esta factura por su titular, no es lo mismo poner primero "
                    "el nombre que primero los apellidos. Quedarse solo con el nombre "
                    "tampoco vale aquí: en la copia se perderían los "
                    "apellidos.",
                    campo=f"Nombre {quien} ({destino} en la copia)",
                    esperado="un solo campo en la copia",
                    encontrado=f"{len(escritos)} de 3 campos en esta factura: "
                               + ", ".join(f"\"{t}\"" for t in escritos),
                )
            )
    return incidencias


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
                "el anexo tiene uno solo (BT-1, número y serie de la "
                "factura). Nadie dice cómo se juntan: aquí se pegan sin "
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
    incidencias.extend(_de_las_referencias(factura, etiqueta))
    incidencias.extend(_de_la_factura_previa(factura, etiqueta))
    incidencias.extend(_del_desglose(factura, etiqueta))
    incidencias.extend(_de_la_moneda(factura, etiqueta))
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
    # El documento no trae el total de las subvenciones: hay un bloque por
    # cada una.
    subvenciones = Decimal(0)
    for grupo in _hijos(totales, "Subsidies"):
        subvenciones += _suma_profunda(grupo, "SubsidyAmount")

    # Aquí había una nota más, `COPIA-CUOTA`, que salía con recargo de
    # equivalencia y mandaba escribir en BT-110 la cuota sin él. Era el
    # borrador de abril, que daba al recargo un grupo propio. La orden lo pone
    # en el desglose del IVA -BT-117 lleva «la cuota de dicho recargo»-, y
    # BT-110 es la suma del desglose (BR-CO-14): la cuota de Facturae, con el
    # recargo dentro, es la de la copia. Se quitó el 07-10-2026, y no por
    # prudencia: lo que mandaba hacer, hecho entero -el recargo fuera de la
    # cuota y del desglose-, no lo caza ninguna regla de cuentas. Lo mide
    # `test_el_total_copiado_tal_cual_no_pasa_las_reglas_de_la_copia`.
    if retenido:
        # BT-112 es la base más BT-110 (BR-CO-15), y BT-110 lleva el recargo,
        # así que es la base más `TotalTaxOutputs` y nada más. Lo único que
        # separa el total de Facturae del de la copia es la retención, que
        # Facturae resta y la norma no conoce: la orden la lleva en su grupo de
        # retenciones. Sin retención no hay nota, lleve recargo o no.
        europeo = base + repercutido
        incidencias.append(
            Incidencia(
                "COPIA-TOTAL",
                NOTA,
                "El total de esta factura no es el que iría en la copia. El "
                "total de Facturae resta las retenciones, y el total con "
                "impuestos de la copia (BT-112) es la base más las cuotas del "
                "desglose, recargo de equivalencia incluido: la retención "
                "viaja aparte, en el grupo de retenciones de la orden, con su "
                "línea de cobro RETE y la suma en cac:WithholdingTaxTotal.",
                # Sin flechas ni nada fuera del latín de siempre: esto se
                # imprime en consolas que todavía hablan cp1252, y un carácter
                # que no esté ahí no sale mal: revienta el informe entero.
                campo=f"{etiqueta}Total factura (BT-112 en la copia)",
                # Con «en la copia» y «en esta factura» pegados al número: el
                # informe rotula estas dos líneas «Debería ser» y «Tiene», y
                # sin el añadido se leería que la factura está mal, que es
                # justo lo contrario de lo que dice la nota.
                esperado=f"{cifras.calculada(europeo)} en la copia: base más "
                         "cuotas, sin restar la retención",
                encontrado=f"{cifras.en_castellano(total)} en esta factura, "
                           f"que ya tiene restados "
                           f"{cifras.en_castellano(retenido)} de retenciones",
            )
        )
    if suplidos:
        incidencias.append(
            Incidencia(
                "COPIA-SUPLIDO",
                NOTA,
                "Esta factura lleva suplidos, y en la copia van en el grupo de "
                "cargos en nombre de un tercero (BG-34), fuera del total con "
                "impuestos, en una línea de cobro identificada con SUPL "
                "(cac:CollectionInvoiceLine/cbc:ID, BT-ES-10 en la orden). El "
                "importe y la descripción son BT-179 y BT-180, términos de la "
                "edición de 2026 de la norma, y la orden no les da ruta UBL: "
                "dónde se escriben dentro de esa línea no lo dice. Y la "
                "descripción es obligatoria y Facturae no la tiene: de un "
                "suplido guarda las partes, la fecha, la factura de origen y "
                "el importe, así que la escribe quien copia.",
                campo=f"{etiqueta}Total de suplidos (BG-34 en la copia)",
                esperado="una línea de cobro SUPL en la copia, con su "
                         "descripción",
                encontrado=cifras.tiene(suplidos),
            )
        )
    # Todo lo que se queda fuera, en **una** nota. Cinco notas seguidas
    # diciendo cada una «esto tampoco» no las lee nadie, y lo que hay que saber
    # es la lista entera de un vistazo. Los importes van con su cifra porque un
    # importe que se queda fuera ya no cuadra con ningún total de la copia; los
    # demás son datos y basta con nombrarlos.
    se_quedan = []
    if financieros:
        se_quedan.append(f"gastos financieros ({cifras.en_castellano(financieros)})")
    if subvenciones:
        se_quedan.append(f"subvenciones ({cifras.en_castellano(subvenciones)})")
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
    cuelgan de uno—, y esa no tiene este destino: el domicilio del centro no
    es el de la parte. Hasta el 07-10-2026 se añadía que del centro el anexo se
    quedaba con sus tres identificadores; era el borrador de abril, y el anexo
    de la orden no recoge ni ésos.
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
    incidencias = list(_direcciones_de_fuera(raiz)) + _de_los_nombres(raiz)
    for numero, factura in enumerate(facturas, 1):
        etiqueta = f"Factura {numero}: " if len(facturas) > 1 else ""
        incidencias.extend(_de_una_factura(factura, etiqueta, del_documento))
    return incidencias
