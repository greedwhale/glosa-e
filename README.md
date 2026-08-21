# Factura-e

Validador de facturas electrónicas españolas y control de plazos de estados,
según el RD 238/2026.

## Estado actual

| Módulo | Qué hace | Estado |
|---|---|---|
| `validador/nif.py` | Valida NIF, NIE y CIF con sus dígitos de control | Terminado |
| `validador/calendario.py` | Días hábiles españoles y plazo de 4 días de los estados | Terminado |
| `validador/formato.py` | Detección de formato y versión (Facturae, UBL, CII, EDIFACT) | Terminado |
| `validador/en16931.py` | Reglas de negocio EN 16931 sobre UBL **y CII**, con mensajes en castellano | Terminado |
| `validador/codigo_unico.py` | Código único de factura: duplicados, numeración y fechas | Terminado |
| `validador/incidencias.py` | Tipos comunes (`Incidencia`, `Informe`) que comparten los módulos de reglas | Terminado |
| `validador/esquema.py` | Validación de forma contra los XSD oficiales, con los errores traducidos | Terminado |
| `validador/factura.py` | El orquestador: forma y contenido sobre el mismo documento, y lotes | Terminado |
| `validador/__main__.py` | La línea de órdenes | Terminado |
| Reglas para Facturae | EN 16931 no es su modelo; haría falta un mapa aparte | Pendiente |

296 tests, todos en verde.

```bash
.venv/Scripts/python.exe -m pytest -q
```

## Cómo se usa

```bash
python -m validador ejemplos --hoy 2026-09-20
```

Acepta ficheros sueltos, carpetas o comodines. Devuelve 0 si todo está bien, 1
si hay algún error y 2 si no hay nada que mirar, para poder encadenarlo en un
script. Con `--solo-errores` calla los avisos y deja solo lo que impide cobrar.
Con `--esquemas CARPETA` comprueba además la forma; ver más abajo.

En la carpeta `ejemplos/` hay cinco facturas preparadas: dos correctas, una
repetida en otro fichero, otra cuyas líneas no cuadran con el total, y una en
sintaxis CII con la base imponible mal calculada. Sale esto:

```
ejemplos\cii-A-0001.xml
  CII vD16B (factura) · conforme EN 16931 — 1 error(es).

  [BR-CO-13] La base imponible no cuadra con las líneas menos los descuentos
  más los cargos.
    Campo: Base imponible total
    Debería ser: 90.00  (100.00 - 10.00 de descuentos)
    Tiene: 100.00

ejemplos\f-0006.xml
  UBL v2.1 (factura) · conforme EN 16931 — 1 error(es).

  [BR-CO-10] La suma de importes de línea que declara la factura no coincide
  con la suma real de sus líneas. Suele ser una línea añadida o modificada sin
  recalcular el total.
    Campo: Suma de importes de línea
    Debería ser: 90.00 (suma de la única línea)
    Tiene: 100.00

Entre ficheros:

  [CU-10] Esta factura ya estaba registrada: mismo emisor, mismo número y misma
  fecha. Es la misma factura dos veces. La primera viene en f-0002-bis.xml y
  esta en f-0002.xml.
    Campo: Código único
    Tiene: B12345674|F-2026-0002|2026-03-05

  [CU-13] La serie tiene huecos: falta(n) 3 número(s) entre el primero y el
  último. Si son facturas anuladas, no pasa nada; si no, la numeración no es
  correlativa.
    Campo: Serie F-2026-*
    Debería ser: del 0001 al 0006 sin saltos
    Tiene: falta(n) 0003 al 0005

5 fichero(s) · 3 correcto(s) · 2 con errores · 2 incidencia(s) entre ficheros.
```

También se puede usar como biblioteca:

```python
from validador import factura

informe = factura.validar_archivo("factura.xml")
print(informe.detalle())

lote = factura.validar_lote(["a.xml", "b.xml"])   # además los compara entre sí
```

## Lo que la norma exige (verificado)

Del RD 238/2026, de 25 de marzo:

- **Formatos estructurados admitidos**: Facturae, UBL, EDIFACT o CII.
- **Formato de referencia**: la norma europea **EN 16931**.
- **Sintaxis de referencia de la solución pública**: **UBL**.
- **Código único por factura**: combina NIF del emisor, número y serie, y fecha
  de expedición.
- **Estados de factura**: el destinatario debe comunicar al emisor, en un
  máximo de **4 días hábiles** (excluidos sábados, domingos y festivos
  nacionales): la aceptación o el rechazo comercial, y el pago efectivo
  completo con su fecha.
- **El silencio equivale a aceptación**: la ausencia de rechazo expreso se
  entiende como aceptación de la factura.
- **Estados opcionales**: pago parcial, cesión a terceros, aceptación o rechazo
  parcial. No afectan al cómputo del plazo legal de pago.
- **Prórroga para los pequeños**: autónomos y entidades con ingresos por debajo
  de 8 millones de euros tienen doce meses adicionales para la obligación de
  informar estados. Hasta entonces es voluntaria.
- **Solución pública gratuita**: la AEAT ofrece una plataforma en su sede
  electrónica para quienes facturan menos de 8 millones.

## ⚠️ Corrección importante sobre las fechas

**Las fechas que se citan por ahí no están confirmadas.** Al contrastar
fuentes encontré versiones incompatibles: unas dicen 1 de enero de 2027 para
empresas y 1 de julio de 2027 para autónomos; otras hablan de octubre de 2027
y octubre de 2028; otras incluso de enero de 2026.

Lo que sí parece sólido y explica la discrepancia:

> Los plazos **empiezan a contar desde la entrada en vigor de la Orden
> Ministerial técnica**, que todavía no se ha publicado y se espera para
> finales de 2026.

Consecuencias prácticas para este proyecto:

1. **La fecha límite es real, pero aún no está fijada.** No prometas fechas
   concretas a nadie hasta que salga la Orden Ministerial.
2. **La especificación técnica tampoco es definitiva.** La Orden Ministerial
   concretará los requisitos del sistema. Construir hoy el producto completo de
   cumplimiento sería prematuro.
3. **Lo que sí es seguro construir ahora** es justo lo que hay hecho: reglas que
   no dependen de esa orden. Los dígitos de control del NIF llevan décadas sin
   cambiar; el cómputo de días hábiles tampoco va a cambiar; y las reglas
   Schematron de EN 16931 son estables y de código abierto.

## Validación de forma: los esquemas XSD

Hay dos maneras de que rechacen una factura. Una es de **contenido**: el
documento está bien formado pero las cuentas no cuadran, y de eso se ocupan
`en16931` y `codigo_unico`. La otra es de **forma**: el documento no respeta el
esquema, y ahí el receptor ni siquiera llega a mirar los números.

La comprobación en sí la hace libxml2 y no hay nada que reinventar. **El
trabajo está en traducir el resultado.** Este es un caso real, el mismo
documento visto por los dos:

```
-- lo que dice libxml2 --
Element {urn:oasis:names:specification:ubl:schema:xsd:CommonBasic
Components-2}IssueDate: This element is not expected. Expected is (
{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID ).

-- lo que dice el validador --
[XSD-ORDEN] «IssueDate» y «ID» están cambiados de sitio. En XML el orden de
los elementos es parte del formato: «ID» tiene que ir antes.
  Campo: IssueDate (línea 3)
  Debería ser: «ID»
  Tiene: IssueDate
```

### Instalar los esquemas

No vienen dentro del repositorio: son de OASIS, de UN/CEFACT y del Ministerio,
pesan lo suyo y tienen sus propias licencias. Hay que descargarlos y dejarlos
en una carpeta:

| Formato | Fichero que se busca | De dónde sale |
|---|---|---|
| UBL 2.1 | `UBL-Invoice-2.1.xsd`, `UBL-CreditNote-2.1.xsd` | paquete UBL 2.1 de OASIS |
| CII | `CrossIndustryInvoice_100pD16B.xsd` | paquete D16B de UN/CEFACT |
| Facturae | `Facturaev3_2_2.xsd` y equivalentes | sede de facturae.gob.es |

El catálogo **busca por nombre de fichero en toda la carpeta**, no por una ruta
fija. Cada paquete oficial se descomprime con su propio arbolito y no tiene
sentido obligar a nadie a recolocarlo a mano: se descomprime donde sea, dentro
de `esquemas/`, y ya está. La carpeta se cambia con `--esquemas` o con la
variable de entorno `FACTURAE_ESQUEMAS`.

Si no hay ninguno instalado, **no se comprueba la forma y se dice**, una vez al
final y no una por factura. Callar y aparentar que todo está bien sería lo peor
que podría hacer un validador.

### Lo que traduce

| Código | Qué ha pasado |
|---|---|
| `XSD-ORDEN` | Un elemento no cabe ahí: está cambiado de sitio, repetido, o no existe |
| `XSD-FALTA` | A un elemento le falta un hijo obligatorio |
| `XSD-VALOR` | El valor no está en la lista cerrada que admite el esquema |
| `XSD-TIPO` | El valor no tiene la pinta de su tipo (fecha, importe, número...) |
| `XSD-LONGITUD` | Demasiado largo o demasiado corto |
| `XSD-PATRON` | No encaja con la expresión que exige el esquema |
| `XSD-ATRIBUTO` | Falta un atributo obligatorio, o sobra uno |
| `XSD-TEXTO` | Texto suelto donde solo caben elementos |
| `XSD-RAIZ` | El documento no empieza por donde el esquema espera |
| `XSD-OTRO` | Algo que no se sabe redactar mejor; se pasa tal cual |

Lo último no es pereza: **nunca se pierde un incumplimiento por no saber
traducirlo**. Si aparece un mensaje que las reglas no reconocen, sale igual con
el texto original.

Los dos que más se ganan al traducirlos son los tópicos españoles:

```
[XSD-TIPO] «02/03/2026» no vale como contenido de «IssueDate».
Una fecha se escribe AAAA-MM-DD: 2026-03-02.

[XSD-TIPO] «1.234,56» no vale como contenido de «PayableAmount». Un importe
lleva punto decimal, sin símbolo de moneda ni separador de miles: 1234.56,
no 1.234,56 EUR.
```

### Decisiones y sorpresas

**«No esperado» significa tres cosas distintas.** libxml2 dice lo mismo si un
elemento está cambiado de orden, si está repetido o si no existe en el esquema.
Para quien tiene que arreglar la factura son tres problemas diferentes, así que
se mira el documento: si lo que se esperaba aparece más adelante entre los
hermanos, están al revés; si el nombre sale dos veces, sobra uno. **El repetido
se comprueba antes que el desordenado**, porque con `<ID/><ID/><Fecha/>` lo
esperado también aparece más adelante y diría «cambiados de sitio» cuando lo
que pasa es que uno sobra.

**El `path` de libxml2 lleva los prefijos del documento.** Viene como
`/*/cbc:IssueDate`, y evaluarlo sin más revienta con «Undefined namespace
prefix». Hay que pasarle los prefijos recogidos de todo el árbol, no solo de la
raíz. Como reserva se busca por número de línea, aunque eso no sirve en un XML
escrito todo seguido, que es justo como los genera media industria.

**El esquema se compila una vez por lote.** Compilar UBL 2.1 no es barato y en
trescientos ficheros se notaría; el `Catalogo` los cachea.

**Se cortan a veinte.** Un documento roto de verdad da cientos de
incumplimientos, casi todos consecuencia del primero. Pasado el tope se dice
cuántos quedan y que se arreglen los de arriba primero.

**libxml2 se para en el primer error de estructura.** Los errores de tipo se
acumulan, pero en cuanto el modelo de contenido se tuerce, abandona ese
elemento. Así que puede hacer falta más de una pasada: se arregla el orden, se
vuelve a pasar, y entonces aparecen los valores mal escritos.

## Las mismas reglas sobre dos sintaxis

EN 16931 define un **modelo semántico** —los campos BT-1, BT-109, BT-112…— y
después UBL y CII lo escriben de dos maneras completamente distintas. Que la
base imponible más los impuestos den el total es verdad en las dos: lo único
que cambia es dónde está escrito cada número.

Por eso el mapa de rutas es un dato y las reglas son código:

```python
@dataclass(frozen=True)
class Sintaxis:
    nombre: str
    espacios: dict[str, str]
    base: str            # dónde vive BT-109
    con_impuestos: str   # dónde vive BT-112
    ...
```

`SINTAXIS_UBL` dice `./cac:LegalMonetaryTotal/cbc:TaxExclusiveAmount`.
`SINTAXIS_CII` dice `./rsm:SupplyChainTradeTransaction/ram:Applicable
HeaderTradeSettlement/ram:SpecifiedTradeSettlementHeaderMonetarySummation/
ram:TaxBasisTotalAmount`. La aritmética y los mensajes no se enteran de la
diferencia, y **los tests corren dos veces**, una por sintaxis, con el mismo
documento semántico montado de las dos formas. Si una regla dejara de
funcionar en una de ellas, la mitad de la suite caería.

Añadir una sintaxis nueva debería ser rellenar otra `Sintaxis` sin tocar
ninguna regla.

### El truco de CII

En UBL casi todo cuelga de la raíz. En CII hay tres bloques bajo
`SupplyChainTradeTransaction` —lo pactado (`Agreement`), la entrega
(`Delivery`) y el cobro (`Settlement`)— y la cabecera va aparte, en
`ExchangedDocument`. Las líneas también son hermanas de esos bloques, no hijas
de ninguno. Cuesta más leerlo, pero es el mismo modelo.

### Dos fallos que el port sacó a la luz

**Los contenedores no están vacíos por no tener texto.** La regla de campo
obligatorio decidía si un elemento era un contenedor mirando si su ruta acababa
en `PostalAddress`. En UBL colaba; en CII el elemento se llama
`PostalTradeAddress`, así que **toda factura CII correcta habría dado BR-08 y
BR-10** como «el elemento existe pero está vacío». Ahora la tabla lo declara
explícitamente.

**El total de impuestos puede venir dos veces.** Las dos sintaxis permiten
declararlo en la moneda de la factura (BT-110) y en la de contabilidad
(BT-111), distinguidos por el atributo `currencyID`. Coger el primero que
aparezca es coger uno al azar:

```
con la selección por moneda: sin errores
cogiendo el primero        : 1 error(es)
    BR-CO-15 | 123.10  (100.00 + 23.10 de impuestos) -> 121.00
```

Una factura perfectamente válida rechazada por leer el importe en dólares.
Afectaba también a UBL, así que el port de CII acabó arreglando un fallo que
ya estaba.

## El orquestador

`en16931` mira lo que exige la norma europea y `codigo_unico` lo que exige el
RD 238/2026. Quien recibe una factura necesita las dos cosas a la vez y no le
importa de qué reglamento sale cada queja. `factura.py` las junta, y hace tres
cosas que no salen gratis de concatenar las dos listas.

**Un solo árbol.** El documento se parsea una vez y se les pasa ya parseado a
los dos conjuntos de reglas. Por eso `en16931.reglas()` y `codigo_unico.reglas()`
existen aparte de sus respectivos `validar()`: reciben el árbol, no los bytes.

**No decir dos veces lo mismo.** BR-02 («falta el número de factura») y CU-00
(«no se puede componer el código único») son la misma queja escrita por dos
reglamentos distintos. Si ya lo ha dicho la norma europea, la española se
calla. La tabla de qué tapa a qué está en `_SOBRA_SI` y es explícita a
propósito: es una decisión editorial, no una deducción.

**Mirar el lote entero.** Un duplicado entre dos ficheros no lo puede detectar
ninguno de los dos por separado; es una propiedad del conjunto. `validar_lote`
valida fichero a fichero y después pasa una segunda vez sobre todas las
facturas juntas, y lo que sale de ahí va en `InformeLote.cruzadas`.

**Facturae se beneficia aunque EN 16931 no esté portado.** Las reglas BR solo
están sobre UBL, así que un Facturae recibe un aviso `SIN-SOPORTE`. Pero el
código único sí se le comprueba, y ahí es donde están las reglas españolas. Un
Facturae con el NIF mal cantará `CU-01` igualmente.

### Un detalle que costó un fallo

Las incidencias del lote y las del fichero **no se pueden comparar por su
texto**. El mensaje del lote añade de qué fichero venía la factura anterior y
el del fichero no, así que dos quejas idénticas nunca coincidían y un duplicado
dentro de un mismo fichero salía dos veces en el informe. Se comparan por
`(código, campo, esperado, encontrado)`, que es lo que identifica la queja sin
depender de cómo esté redactada.

## El código único de factura

Es la primera regla del proyecto que **no** está en EN 16931. Ningún validador
europeo la comprueba, porque es española: sale del artículo 6 del Reglamento de
Facturación —numeración correlativa dentro de cada serie— y del sistema de
facturación del RD 238/2026.

Una factura queda identificada de forma inequívoca por tres datos: **NIF del
emisor**, **serie y número**, y **fecha de expedición**. `codigo_unico.py` los
extrae de UBL, Facturae o CII, y comprueba dos cosas distintas.

**Un código suelto:**

| Código | Qué mira | Gravedad |
|---|---|---|
| CU-01 | El NIF del emisor es válido (reutiliza `nif.py`) | Error |
| CU-02 | Hay número de factura | Error |
| CU-03 | El número cabe en 60 caracteres | Error |
| CU-04 | El número no lleva caracteres de control; si lleva no-ASCII, avisa | Error / Aviso |
| CU-05 | El número no tiene espacios sobrantes | Aviso |
| CU-06 | La fecha de expedición no es futura | Error |
| CU-07 | La fecha no es anterior a la prescripción | Aviso |

**Un lote de facturas**, que es donde está el valor real, porque un duplicado
entre trescientas facturas no se ve a ojo:

| Código | Qué mira | Gravedad |
|---|---|---|
| CU-10 | La misma factura dos veces | Error |
| CU-11 | Mismo número con otra fecha: numeración reutilizada | Error |
| CU-12 | Dos facturas que solo se distinguen por mayúsculas o espacios | Error |
| CU-13 | Huecos en la numeración de una serie | Aviso |
| CU-14 | La fecha retrocede al avanzar el número | Aviso |
| CU-15 | El mismo ordinal con distinto relleno de ceros | Aviso |

Los huecos y los retrocesos van como aviso a propósito: un hueco puede ser una
factura anulada, y un lote parcial no tiene por qué estar completo. Marcarlos
como error daría falsos positivos constantes.

```
[CU-13] La serie tiene huecos: falta(n) 3 número(s) entre el primero y el
último. Si son facturas anuladas, no pasa nada; si no, la numeración no es
correlativa.
  Campo: Serie F-2026-*
  Debería ser: del 0001 al 0007 sin saltos
  Tiene: falta(n) 0003 al 0005
```

### Decisiones concretas de este módulo

**La huella se calcula con las longitudes por delante.** `huella()` devuelve un
SHA-256 del código único, para poder indexar sin guardar los datos. Se cifra
`9:B12345674` + `10:F-2026-001` + `10:2026-09-07`, no la concatenación a pelo:
sin la longitud, un emisor vacío con número `B12345674X` y el emisor
`B12345674` con número `X` producirían la misma cadena y compartirían huella.

**Repetir no es lo mismo que reutilizar, ni que escribir distinto.** Son tres
problemas con tres consecuencias diferentes, y por eso hay tres códigos en vez
de un «duplicado» genérico. CU-10 es un reenvío. CU-11 es una infracción de la
numeración correlativa. CU-12 es el peor de los tres, porque cada sistema cree
tener una factura distinta y ninguno detecta nada.

**El tope de 60 caracteres está tomado de Verifactu.** La Orden Ministerial del
RD 238/2026 no se ha publicado y podría fijar otro. Es una constante justo para
poder cambiarla en una línea.

**La búsqueda del NIF es relativa al vendedor, no absoluta.** Con `//` en lugar
de `./`, la consulta arranca de la raíz del documento aunque se lance desde el
nodo del vendedor: en una factura donde el vendedor solo trae
`PartyLegalEntity` y el comprador sí trae `PartyTaxScheme`, el código único
acababa llevando **el NIF del comprador**. Hay un test que lo fija.

## Decisiones de diseño

**Los festivos son un dato, no una constante.** El calendario laboral que
publica el BOE cada año puede trasladar festivos que caen en domingo, y las
comunidades autónomas añaden los suyos. Por eso `Calendario` acepta
`festivos_extra` y no hay una lista enterrada en el código.

**Los mensajes de error van en castellano llano.** La validación EN 16931 son
955 reglas con códigos tipo `BR-CO-10`, y ese es exactamente el motivo por el
que la gente paga a alguien que se lo traduzca. Cada `Resultado` lleva un campo
`motivo` que explica qué falla y qué debería poner en su lugar.

**El día de partida no cuenta en los plazos.** Si recibes una factura el lunes
y el plazo es de cuatro días hábiles, vence el viernes.

**La versión no se deduce solo del namespace.** Facturae cambió de convención
de namespace entre versiones, y hay documentación que se contradice sobre la
3.2.1: unas fuentes dan `facturae.es/Facturae/2014/v3.2.1/Facturae` y otras
`facturae.gob.es/formato/Versiones/Facturaev3_2_1.xml`. Se aceptan las dos, se
usa el namespace solo para identificar la familia, y la versión se toma del
campo `SchemaVersion` del propio documento. Si el namespace es desconocido pero
la raíz se llama `Facturae`, se reconoce igual y se avisa.

**El parser está endurecido.** El servicio va a recibir XML de terceros, así
que se parsea con `resolve_entities=False` y `no_network=True`. Sin eso, un XML
con una entidad externa podría leer ficheros del servidor. Hay dos tests que lo
comprueban, y el de XXE verifica primero que el documento **sí** se parsea, para
que la comprobación de fuga no pueda pasar en vacío.

**Las reglas van en Python, no en Schematron.** Los artefactos oficiales de
CEN/TC 434 son Schematron, que compila a XSLT 2.0. lxml solo habla XSLT 1.0, y
`saxonche` —la vía habitual para XSLT 2.0 en Python— todavía no publica ruedas
para Python 3.14. Comprobado, no supuesto.

Lejos de ser un problema, resulta ser lo correcto: el valor del producto está
en el mensaje, no en la regla. Las reglas son públicas y las tiene cualquiera;
lo que nadie da es una frase que explique qué hay que corregir. Escribirlas en
Python permite controlar cada mensaje y calcular el importe que *debería*
figurar, no solo señalar que está mal.

**El dinero se maneja con `Decimal`, nunca con `float`.** Con float,
`0.1 + 0.2 != 0.3`, y una factura correcta se rechazaría por un céntimo
fantasma. Hay un test que lo deja por escrito.

**Nada de caracteres exóticos en los mensajes.** El signo menos tipográfico
(U+2212) reventaba al imprimir en una consola Windows con cp1252. Los mensajes
se quedan en caracteres que sobreviven a una terminal española.

## Ejemplo de salida

```
UBL v2.1 (factura) · conforme EN 16931 — 4 error(es).

[BR-CO-10] La suma de importes de línea que declara la factura no coincide
con la suma real de sus líneas. Suele ser una línea añadida o modificada sin
recalcular el total.
  Campo: Suma de importes de línea
  Debería ser: 90.00 (suma de las 2 líneas)
  Tiene: 100.00
```

## Siguiente paso

Los dos tipos de rechazo que existen —el de forma y el de contenido— ya están
cubiertos. Lo que queda es de otra clase:

**Probarlo contra facturas reales.** Todo lo de aquí está comprobado contra
documentos escritos a mano para provocar cada error. Falta pasarle un lote de
facturas de verdad, con sus rarezas, y ver qué mensajes salen mal redactados o
qué formato no se reconoce. Es el trabajo que decide si esto sirve.

**Reglas de negocio para Facturae.** Se queda fuera a propósito: no es una
sintaxis de EN 16931 sino un formato nacional con su propio modelo, así que no
basta con rellenar otra `Sintaxis`. Haría falta un mapa distinto y decidir qué
reglas tienen equivalente. Mientras tanto, a un Facturae sí se le comprueba la
forma contra su XSD y el código único, que es donde están las reglas españolas.

**Las reglas de IVA de EN 16931** (BR-S-*, BR-E-*, BR-Z-*...): que cada
categoría de impuesto cuadre con su base y su tipo. Son unas cuantas y siguen
el mismo patrón que las BR-CO-*, así que caben en el diseño que ya hay.

## Fuentes

- [RD 238/2026 en el Observatorio de Contratación Pública](https://obcp.es/noticias/real-decreto-2382026-de-25-de-marzo-por-el-que-se-desarrolla-el-sistema-de-facturacion)
- [Qué cambia de verdad tras el RD 238/2026 — ASSET](https://asset.es/factura-electronica-b2b-en-espana-que-cambia-de-verdad-tras-el-rd-238-2026/)
- [Guía RD 238/2026: estados y plazos de pago](https://www.lealtadis.es/factura-electronica-b2b-estados-pago-pymes/)
- [Artefactos oficiales de validación EN 16931 (CEN/TC 434)](https://github.com/ConnectingEurope/eInvoicing-EN16931)
