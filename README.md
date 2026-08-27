# Factura-e

Validador de facturas electrónicas españolas y control de plazos de estados,
según el RD 238/2026.

## Estado actual

| Módulo | Qué hace | Estado |
|---|---|---|
| `validador/nif.py` | Valida NIF, NIE y CIF con sus dígitos de control | Terminado |
| `validador/calendario.py` | Días hábiles españoles y plazo de 4 días de los estados | Terminado |
| `validador/formato.py` | Detección de formato y versión (Facturae, UBL, CII, EDIFACT) | Terminado |
| `validador/sintaxis.py` | El mapa: dónde vive cada campo de EN 16931 en UBL y en CII | Terminado |
| `validador/en16931.py` | Campos obligatorios y cuadre aritmético, sobre UBL y CII | Terminado |
| `validador/iva.py` | El desglose de IVA: bases, cuotas, categorías y exenciones | Terminado |
| `validador/codigo_unico.py` | Código único de factura: duplicados, numeración y fechas | Terminado |
| `validador/incidencias.py` | Tipos comunes (`Incidencia`, `Informe`) que comparten los módulos de reglas | Terminado |
| `validador/esquema.py` | Validación de forma contra los XSD oficiales, con los errores traducidos | Terminado |
| `validador/facturae.py` | La aritmética del formato nacional: totales, líneas, impuestos y lote | Terminado |
| `validador/firma.py` | La firma XAdES: integridad del documento y verificación RSA, sin salir a la red | Terminado |
| `validador/factura.py` | El orquestador: forma y contenido sobre el mismo documento, y lotes | Terminado |
| `validador/__main__.py` | La línea de órdenes | Terminado |

563 tests, todos en verde.

```bash
.venv/Scripts/python.exe -m pytest -q
```

## Instalación

Una sola dependencia, lxml, y no es opcional: el parser endurecido, la
validación XSD y el XPath sobre namespaces salen todos de ahí.

```bash
pip install -e .
```

Deja disponible el mandato `factura-e` y también `python -m validador`, que
hacen lo mismo. Para pasar los tests, `pip install -e ".[dev]"`.

Necesita Python 3.10 o posterior. Está probado en 3.14.

## Cómo se usa

```bash
factura-e ejemplos --hoy 2026-09-20
```

Acepta ficheros sueltos, carpetas o comodines. Devuelve 0 si todo está bien, 1
si hay algún error y 2 si no hay nada que mirar, para poder encadenarlo en un
script. Con `--solo-errores` calla los avisos y deja solo lo que impide cobrar.
Con `--esquemas CARPETA` comprueba además la forma; ver más abajo.

**Cada fichero cae en uno de tres estados, no de dos:** correcto, con errores,
o **sin comprobar**. Lo tercero es el fichero que no existe, no se puede leer o
cuyo formato no se reconoce. No es correcto ni incorrecto: es que no se ha
mirado, y también devuelve 1.

```
1 fichero(s) · 0 correcto(s) · 0 con errores · 1 SIN COMPROBAR.
```

Parece un detalle y no lo es. Antes ese fichero se contaba entre los buenos y
el programa devolvía 0, así que **una letra de más en la ruta daba un lote
entero por bueno sin haber abierto nada.** Dar por válido lo que no se ha visto
es lo peor que puede hacer un validador; era el fallo más grave que ha tenido
este proyecto y no lo cazó ningún test: lo cazó un usuario escribiendo mal una
carpeta.

En la carpeta `ejemplos/` hay siete documentos preparados: dos facturas
correctas, una repetida en otro fichero, otra cuyas líneas no cuadran con el
total, una en sintaxis CII con dos tipos de IVA en las líneas y uno solo en el
desglose, un abono correcto, y un Facturae 3.2.2 firmado (`fe-0001.xml`).

La firma de ese último está hecha con la clave de juguete de
`tests/test_firma.py`, y el fichero lo dice en un comentario: sirve para
comprobar que el documento no se ha tocado, **no** acredita a nadie, porque no
la avala ninguna autoridad de certificación. Un test se encarga de que siga
verificando: quien lo edite para cambiar un importe y no lo vuelva a firmar se
entera al pasar la suite, no al enseñarlo.

Junto al código va **de qué reglamento sale la queja**, porque cambia lo que
hay que hacer con ella: lo que firma una norma te lo rechaza el receptor, lo
que firmamos nosotros es una opinión que puedes discutir. Sale esto:

```
ejemplos\cii-A-0001.xml
  CII vD16B (factura) · conforme EN 16931 — 2 error(es).

  [BR-S-8 · EN 16931] La base declarada para S (tipo general) al 21% no
  coincide con la suma de lo que va a ese tipo.
    Campo: Base imponible de S (tipo general) al 21%
    Debería ser: 100.00 (línea 1)
    Tiene: 150.00

  [IVA-TIPO-SIN-DESGLOSE · de la casa] Hay 50.00 a S (tipo general) al 10%,
  pero el desglose no trae ninguna entrada a ese tipo. El desglose va por
  categoría y tipo, no solo por categoría.
    Campo: Desglose de IVA
    Debería ser: una entrada al 10%
    Tiene: línea 2

ejemplos\f-0006.xml
  UBL v2.1 (factura) · conforme EN 16931 — 2 error(es).

  [BR-CO-10 · EN 16931] La suma de importes de línea que declara la factura
  no coincide con la suma real de sus líneas. Suele ser una línea añadida o
  modificada sin recalcular el total.
    Campo: Suma de importes de línea
    Debería ser: 90.00 (suma de la única línea)
    Tiene: 100.00

  [BR-S-8 · EN 16931] La base declarada para S (tipo general) al 21% no
  coincide con la suma de lo que va a ese tipo.
    Debería ser: 90.00 (línea 1)
    Tiene: 100.00

ejemplos\fe-0001.xml
  Facturae v3.2.2 (factura) · firmado — sin errores, 1 aviso(s).

  [FIRMA-DEBIL · firma electrónica] La clave del certificado es de 512 bits.
  Para firma electrónica se piden 2048 como mínimo.
    Campo: Clave del certificado
    Debería ser: 2048 bits o más
    Tiene: 512 bits

ejemplos\r-0001.xml
  UBL v2.1 (abono) · conforme EN 16931 — sin errores.

Entre ficheros:

  [CU-10 · RD 238/2026] Esta factura ya estaba registrada: mismo emisor,
  mismo número y misma fecha. Es la misma factura dos veces. La primera viene
  en f-0002-bis.xml y esta en f-0002.xml.
    Campo: Código único
    Tiene: B12345674|F-2026-0002|2026-03-05

  [CU-13 · RD 238/2026] La serie tiene huecos: falta(n) 3 número(s) entre el
  primero y el último. Si son facturas anuladas, no pasa nada; si no, la
  numeración no es correlativa.
    Campo: Serie F-2026-*
    Debería ser: del 0001 al 0006 sin saltos
    Tiene: falta(n) 0003 al 0005

7 fichero(s) · 3 correcto(s) · 4 con errores · 2 incidencia(s) entre ficheros.
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

## El desglose de IVA

Una factura no lleva un solo importe de impuesto: lleva un **desglose**, con
una entrada por cada combinación de categoría y tipo. Un hotel que factura
alojamiento al 10% y minibar al 21% tiene dos entradas, y cada una declara su
base y su cuota.

Ahí se cuela el error más caro y más difícil de ver. Alguien cambia el tipo de
una línea y no rehace el desglose: **las cuentas generales siguen cuadrando**
—la suma de líneas es la misma— y sin embargo la factura declara mal el IVA,
que es justo lo que mira Hacienda. Ninguna de las reglas BR-CO-* se entera.

```
[BR-S-8] La base declarada para S (tipo general) al 21% no coincide con la
suma de lo que va a ese tipo.
  Debería ser: 100.00 (línea 1)
  Tiene: 150.00

[IVA-TIPO-SIN-DESGLOSE] Hay 50.00 a S (tipo general) al 10%, pero el desglose
no trae ninguna entrada a ese tipo. El desglose va por categoría y tipo, no
solo por categoría.
  Debería ser: una entrada al 10%
  Tiene: línea 2
```

Dos quejas para un solo error, cada una por un lado: lo que sobra en el 21% y
lo que falta en el 10%.

### Las categorías, en castellano

La norma usa los códigos de la lista UNCL 5305. Las dos últimas son españolas y
casi ninguna herramienta europea las nombra:

| Código | Qué es | Tipo | Motivo de exención |
|---|---|---|---|
| `S` | tipo general | mayor que 0 | no debe llevarlo |
| `Z` | tipo cero | 0 | no debe llevarlo |
| `E` | operación exenta | 0 | **obligatorio** |
| `AE` | inversión del sujeto pasivo | 0 | **obligatorio** |
| `K` | entrega intracomunitaria | 0 | **obligatorio** |
| `G` | exportación fuera de la UE | 0 | **obligatorio** |
| `O` | operación no sujeta | ninguno | **obligatorio** |
| `L` | IGIC (Canarias) | el suyo | libre |
| `M` | IPSI (Ceuta y Melilla) | el suyo | libre |

El motivo de exención no es burocracia: sin él, quien recibe la factura no
puede justificar por qué no le repercuten IVA. Y por eso la norma no solo lo
exige donde hace falta: también lo **prohíbe** donde no (`BR-S-10`, `BR-Z-10`).
Son tres estados y no dos. Con un booleano —«obligatorio» o no— «no
obligatorio» y «prohibido» eran lo mismo, y una entrada a tipo cero con motivo
de exención pasaba entera. Llevarlo ahí es señal de que la categoría está mal
elegida, y eso sí cuesta dinero: el receptor se deduce un IVA que no debería, o
al revés.

### Qué se comprueba

**De la norma** (prefijo `BR-`):

| Código | Qué mira |
|---|---|
| `BR-CO-18` | La factura trae al menos una entrada de desglose |
| `BR-45` / `BR-46` | Cada entrada declara su base y su cuota |
| `BR-47` | Cada entrada declara su categoría |
| `BR-48` | Cada entrada declara su tipo, salvo lo no sujeto |
| `BR-CO-14` | El IVA total es la suma de las cuotas del desglose |
| `BR-CO-17` | Cuota = base × tipo / 100, redondeada a dos decimales |
| `BR-CO-11` / `BR-CO-12` | El total de descuentos y de cargos es la suma de los detallados |
| `BR-{X}-8` | La base de cada entrada es la suma de lo que va a ese tipo |
| `BR-{X}-5` | El tipo que exige cada categoría |
| `BR-{X}-10` | El motivo de exención, presente o ausente según toque |
| `BR-{X}-1` | Cada categoría usada aparece en el desglose |
| `BR-O-11` | Lo no sujeto no se mezcla con lo sujeto en la misma factura |

**De la casa** (prefijo `IVA-`), que no están en EN 16931 pero tienen sentido
para quien factura en España:

| Código | Qué mira |
|---|---|
| `IVA-TIPO-SIN-DESGLOSE` | Un tipo usado en las líneas sin entrada en el desglose |
| `IVA-TIPO` | Un tipo que no es 21, 10, 4 ni 0 (aviso: legal fuera de España) |
| `IVA-CATEGORIA-RARA` | Una categoría que no está en la lista de la norma |
| `IVA-CATEGORIA-SIN-DESGLOSE` | Una categoría de fuera de la norma, sin entrada en el desglose |
| `IVA-SIN-CATEGORIA` | Líneas sin categoría de IVA (aviso: no se ha podido comprobar) |
| `IVA-AJUSTES-SIN-DETALLAR` | Descuentos globales sin decir a qué tipo van |
| `IVA-SIN-TOTAL` | No hay importe total de impuestos que comprobar |

La separación es deliberada: **que se vea de un vistazo qué exige la norma y
qué opinamos nosotros.**

### Decisiones

**No acusar cuando no se puede saber.** Si la factura declara descuentos
globales pero no los detalla, no hay forma de repartirlos entre los tipos, y
comprobar la base sería inventarse un error. En ese caso se salta `BR-{X}-8` y
se dice que no se ha podido comprobar. Decir «no lo sé» es mejor que acusar en
falso.

**Y la queja, en el campo que está mal.** El caso hermano: los descuentos
vienen detallados, pero no suman lo que declara el total de la factura.
Entonces tampoco son de fiar —no se sabe cuál de las dos cifras es la buena—
así que también se calla `BR-{X}-8`. Lo dicen `BR-CO-11` y `BR-CO-12`, que
señalan el total del descuento y no el desglose de IVA. Antes de tenerlas, el
error salía igual pero apuntando al sitio equivocado: la queja llegaba, la
dirección no.

**La base fantasma.** `BR-{X}-8` comparaba la base declarada con la suma de lo
suyo, y si no había nada suyo se callaba: la suma daba cero y no había con qué
comparar. Un desglose que cobra sobre algo que no está en ninguna parte pasaba
entero. Ahora se dice, y se dice de otra forma —«150.00 sin nada detrás»—
porque «debería ser 0.00» no ayuda a nadie. Solo si el documento clasifica sus
conceptos: si ninguna línea lleva categoría, no es que falten, es que no se han
podido leer.

**`BR-CO-14` estaba mal usado.** Llevaba ese código un aviso propio —«la
factura no declara el importe total de impuestos»— cuando BR-CO-14 es de la
norma y significa otra cosa: que el total de IVA sea la suma de las cuotas del
desglose. Ahora esa regla está implementada de verdad y el aviso lleva el
código `IVA-SIN-TOTAL`, que es de la casa. Un código oficial en una
comprobación inventada es peor que no tener código.

**Y el error espejo, que también estaba.** `IVA-SIN-CATEGORIA` sobre una
entrada del desglose es `BR-47` («cada entrada del desglose se define por su
código de categoría»), y `IVA-SIN-DESGLOSE` es `BR-CO-18` («la factura tendrá
al menos un desglose»). Un código inventado donde la norma ya tiene uno cuesta
lo mismo en la otra dirección: el lector no puede buscarlo, ni saber si se lo
van a rechazar. Los dos llevan ya su código oficial.

`BR-CO-18` además **era un aviso**, y solo saltaba si el IVA declarado no era
cero. Una factura sin desglose y sin total salía «conforme, sin errores». Ese
es el peor fallo posible en un validador: no el falso positivo, sino el falso
negativo, porque el usuario se fía y la manda.

**Y una tercera, aprendida después.** Esa salvaguarda de «no acusar cuando no
se puede saber» decidía si un apunte era un ajuste **leyendo su descripción**:

```python
detallados = any(a.descripcion.startswith(("cargo", "descuento")) for a in apuntes)
```

La descripción es texto para el usuario. Colgar de ella una decisión de
negocio significa que el día que alguien reescriba «descuento 1» como «dto. 1»,
la salvaguarda se apaga sola y **los tests siguen en verde**, porque ninguno
mira ese camino. Ahora es un campo, `Apunte.es_ajuste`. Los dos totales
—descuentos y cargos— también se miran por separado en vez de sumados: sumando,
un descuento y un cargo del mismo importe se anulan y la factura parece no
declarar ninguno.

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
| `XSD-ESQUEMA-ROTO` | El esquema está instalado pero no se puede leer |

`XSD-OTRO` no es pereza: **nunca se pierde un incumplimiento por no saber
traducirlo**. Si aparece un mensaje que las reglas no reconocen, sale igual con
el texto original —eso sí, sin los namespaces, que era lo único que ese camino
seguía enseñando en crudo—.

`XSD-ESQUEMA-ROTO` salió de un experimento que no iba de eso. Al medir el
catálogo con una carpeta de esquemas falsos, la excepción de lxml subió sin que
nadie la parase y **se llevó por delante el lote entero**: una descarga a
medias en la carpeta de esquemas y trescientas facturas sin validar, con un
traceback en vez de una frase. Ahora el esquema que no compila se anota, se
dice, y las demás facturas siguen su camino.

Los dos que más se ganan al traducirlos son los tópicos españoles:

```
[XSD-TIPO] «02/03/2026» no vale como contenido de «IssueDate».
Una fecha se escribe AAAA-MM-DD: 2026-03-02.

[XSD-TIPO] «1.234,56» no vale como contenido de «PayableAmount». Un importe
lleva punto decimal, sin símbolo de moneda ni separador de miles: 1234.56,
no 1.234,56 EUR.
```

### Una medición que salió al revés

El catálogo miraba el disco en cada consulta: dos o tres veces por factura,
una para saber si había esquemas y las demás probando nombres. Escrito así
parece caro, y en la revisión lo di por caro. Al medirlo, no lo era:

```
        ficheros    esquema   una búsqueda
             500  enterrado        0.3 ms
            2000  enterrado        0.4 ms
            8000  enterrado        0.5 ms
```

`next(ruta.rglob(nombre), None)` es perezoso —corta en cuanto encuentra— y
`pathlib` con un nombre literal baja por directorios sin enumerar los ficheros
de cada uno. De ahí que el coste apenas suba de 500 a 8.000 ficheros. En un
lote de trescientas facturas se ahorran décimas de segundo, no minutos.

El índice se queda igualmente: hacer el recorrido una vez es más simple de
razonar y no depende de dónde caiga el fichero dentro del árbol. Pero la razón
es esa y no el rendimiento, y conviene que quede escrito, porque **una
optimización justificada con una cifra inventada es la que nadie se atreve a
quitar después.**

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

### El abono, que se había quedado fuera del mapa

Un abono no es un documento exótico: es con lo que se corrige una factura. En
UBL cambian tres nombres —el elemento raíz, `CreditNoteTypeCode` en vez de
`InvoiceTypeCode` y `CreditNoteLine` en vez de `InvoiceLine`— y todo lo demás
es idéntico. El mapa solo conocía los nombres de la factura, así que **un
abono correcto salía con dos errores inventados**:

```
[BR-04] La factura debe indicar de qué tipo es.
[BR-16] La factura no tiene ninguna línea.
```

Y lo grave no eran los falsos positivos. Al no encontrársele las líneas,
enmudecían de golpe BR-24, BR-CO-10, BR-S-8 y todo el IVA: **acusado en falso
y sin comprobar a la vez.** El mapa ahora usa una unión XPath (`a|b`) y coge el
nombre que haya, que es más seguro que mantener dos mapas y elegir uno.

Sobrevivió porque **ningún test pasaba las reglas de negocio sobre un abono**.
Había tests de detección de abonos y de qué esquema les toca, pero ninguno de
contenido. Ahora hay un `fixture` que corre cada regla dependiente de las
líneas sobre los dos documentos, generando el abono a partir de la factura
para que no se pueda arreglar uno y olvidar el otro. Sin el arreglo, cinco de
esos tests caen.

La moraleja no es sobre abonos: es que **reconocer un tipo de documento en un
módulo y no mapearlo en otro no da error, da silencio.**

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

**Tres reglamentos sobre el mismo documento.** A un UBL o un CII se le miden
las reglas europeas; a un Facturae, la aritmética de su propio esquema; a los
tres, la forma contra el XSD y el código único del RD 238/2026. Ninguno sabe de
los otros, y quien recibe la factura no tiene por qué saber de qué reglamento
sale cada queja.

**Y decir de dónde sale cada queja.** Junto al código va la norma que la firma:

```
[BR-S-8 · EN 16931]              te lo rechaza el receptor
[CU-10 · RD 238/2026]            te lo rechaza Hacienda
[XSD-ORDEN · Esquema XSD]        no pasa ni de la puerta
[IVA-TIPO-SIN-DESGLOSE · de la casa]   opinamos nosotros
```

No es adorno: cambia lo que hay que hacer con la queja. Lo que firma una norma
hay que arreglarlo; lo que firmamos nosotros se puede discutir, y quien lo lea
tiene derecho a saber cuál es cuál sin ir a buscar la tabla del README.

Esto ya estaba escrito —`origen()` existía desde el primer día— pero **no
llegaba al informe** y solo lo ejercitaban los tests. De paso tenía un fallo:
las comprobaciones propias de IVA, que empiezan por `IVA-`, caían en el cajón
de «Formato», que es el de «no reconozco este fichero». Un aviso sobre el
desglose de IVA no es un problema de formato.

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

## Facturae: la aritmética del formato nacional

Facturae es el formato que España usa de verdad y el único que la
Administración acepta por FACe. Hasta ahora este validador lo reconocía, le
comprobaba la forma contra el XSD y le sacaba el código único —pero **no le
miraba ni un número**. Un Facturae con el total inventado salía «sin errores».

Se demostró inyectando nueve defectos de uno en uno sobre una factura oficial
de prueba: total a 999.999,99, cuota de IVA a 1,00, una línea que ya no suma,
tipo al 77 %, el coste que no es la cantidad por el precio... **Nueve defectos,
nueve silencios.** Los mismos nueve, hoy, dan veinte quejas.

### De dónde salen estas reglas

Del propio esquema, no de la memoria de nadie. El XSD de Facturae lleva la
aritmética escrita en sus anotaciones, en castellano:

> **TotalGrossAmountBeforeTaxes.** Total importe bruto antes de impuestos.
> Resultado de: TotalGrossAmount - TotalGeneralDiscounts +
> TotalGeneralSurcharges.

Cada regla cita en su comentario la frase de la que sale. Es la misma
disciplina que en su día encontró que toda la familia `BR-{X}-05` colgaba de la
línea y no del desglose: ir al artefacto normativo en vez de recordarlo.

La cadena entera, tal como la escribe el esquema:

```
TotalGrossAmount            = Σ GrossAmount de las líneas
TotalGrossAmountBeforeTaxes = TotalGrossAmount − descuentos + cargos generales
TotalTaxOutputs             = Σ cuotas y recargos de equivalencia
InvoiceTotal                = base + repercutidos − retenidos
TotalOutstandingAmount      = InvoiceTotal − subvenciones − anticipos
TotalExecutableAmount       = a pagar − retenido − especie + suplidos + financieros
```

Y en cada línea: `TotalCost = Quantity × UnitPriceWithoutTax`, y
`GrossAmount = TotalCost − descuentos + cargos`.

### Dónde el esquema se abstiene, nosotros también

`TaxAmount` lleva esta anotación: «La legislación del impuesto correspondiente
determina cómo se calcula la cuota». Y `TaxRate`: «Téngase en cuenta que no
siempre son porcentajes».

Así que `FE-CUOTA` va como **aviso**, no como error —al revés que `BR-CO-17`,
que en UBL y CII sí es error porque la norma europea sí lo manda—, y no se le
mide la cuota a los impuestos que no se liquidan por porcentaje: los especiales
van por litro o por kilo, y multiplicar su «tipo» por la base no significa
nada.

Los códigos (`FE-BASE`, `FE-TOTAL`...) son **nuestros** y se llaman por lo que
comprueban. Facturae no numera sus reglas como EN 16931 numera las `BR-*`, e
inventar un «FE-07» que suene a oficial es exactamente el error que ya se
cometió aquí una vez con unos `BR-IG-*` que no existen en ninguna norma.

### Lo que se factura y no se grava

La comprobación que más dinero mueve no está escrita como fórmula en ninguna
parte: que la base declarada en el desglose cubra lo que la factura cobra. Va
como aviso, porque hay regímenes —agencias de viajes, grupo de entidades— donde
la base del impuesto legítimamente no es el importe facturado.

Sale sola en **dos de las nueve facturas oficiales de prueba**: 33,75 € en una
y 22,08 € en otra, facturados y sin base declarada. Las mismas dos cifras que
un revisor independiente había encontrado antes a mano, al céntimo.

### Un fichero Facturae son varias facturas

`Facturae/Invoices/Invoice*`, con una cabecera de lote encima que declara
cuántas hay y cuánto suman. En UBL y en CII el fichero *es* la factura. Por eso
no basta con rellenar otra `Sintaxis`: hay una capa de reglas —`FE-LOTE-*`— que
en las otras sintaxis no existe, y cuando hay más de una factura cada queja
tiene que decir de cuál habla.

### La tolerancia depende de cuántas cifras se sumen

Cada importe se escribe redondeado, así que al sumarlos los medios céntimos se
acumulan: para N cifras, la desviación legítima llega a `0,005 × (N+1)`. Con
una sola cifra eso es el céntimo de siempre.

No es teórico. `alphp_factura-prueba-v1-2-0.xml`, que es correcta, suma tres
cuotas —34,91 + 34,91 + 209,43 = 279,25— y declara 279,24: con la tolerancia
fija se salva por el pelo, y con una cuota más ya no. **Y se cuentan cifras, no
entradas**: una entrada de impuesto con recargo de equivalencia aporta dos
importes redondeados, no uno. Ese detalle lo cazó un test, no la lectura.

### El resultado sobre las muestras

Nueve ficheros oficiales que no hemos escrito nosotros, ninguna queja de
aritmética sobre las que están bien —incluida la más enrevesada, con descuento
general, descuento y cargo de línea, dos impuestos repercutidos, recargo de
equivalencia y retención— y las dos defectuosas señaladas con la cifra exacta.

## La firma XAdES

En Facturae la firma no es un adorno. Lo dice el propio esquema, en la
anotación de su bloque `Signature`:

> «Se define como opcional para facilitar la verificación y el tránsito del
> fichero. No obstante, debe cumplimentarse este bloque de firma electrónica
> para que se considere una factura electrónica válida legalmente frente a
> terceros.»

### Qué se comprueba

Todo esto sin salir a la red:

1. **Que nadie haya tocado el documento desde que se firmó.** Cada `Reference`
   de la firma lleva el resumen de un trozo del documento. Se canonicaliza ese
   trozo, se le rehace el resumen y se compara. Es solo *hash*: no hace falta
   ninguna clave, y es lo que caza el fallo más común de todos —alguien edita
   el XML después de firmarlo, o una herramienta lo vuelve a guardar y lo
   rompe—. Basta un espacio de más.
2. **Que la firma la hiciera la clave privada del certificado que se enseña.**
3. **Que el certificado estuviera vigente** el día que la firma declara.
4. **Que el certificado presentado sea el que XAdES dice haber usado.**
5. **Que los algoritmos no estén retirados.**

### Qué no, y por qué se dice

- **De quién es el certificado.** Exige la lista de confianza europea (TSL),
  que cambia y hay que descargar.
- **Si está revocado.** Exige OCSP o CRL, o sea red.
- **Los sellos de tiempo.** Sin ellos la fecha de firma la escribe quien firma;
  sirve para contrastarla con la vigencia del certificado, no para demostrar
  cuándo se firmó.

Traducido: responde **«¿ha cambiado alguien este documento después de
firmarlo?»**. No responde «¿de quién es este certificado?». Un documento
firmado con un certificado que el remitente se ha inventado pasa las cinco
comprobaciones —de hecho es justo lo que hacen los tests—, y por eso el informe
dice lo que no mira:

```
No se comprueba de quién es el certificado ni si está revocado
—para eso hace falta la lista de confianza europea y salir a la
red—, ni si lo que dice la factura es cierto.
```

Ese párrafo cambia solo cuando el lote trae firmas. Sobre uno sin firmar sería
explicar qué mitad de algo que no hay se comprueba.

### Sin dependencias nuevas

Verificar RSA es `pow(firma, e, n)`: aritmética de enteros, que Python hace
nativa y con precisión arbitraria. Leer la clave pública del certificado son
unas líneas de DER.

Traer `cryptography` habría costado una extensión compilada, y esto está
pensado para correr dentro del navegador con Pyodide: cada dependencia nativa
es otro *wheel* que buscar, otra versión que casar y varios megas de descarga.
`firma.py` **no añade ni un byte a la descarga**: son unos kilobytes dentro del
wheel de 97 KB que ya se bajaba. Medido después de añadirlo, el navegador
descomprime 14,71 MB, y todo eso es Pyodide y lxml. Cuesta 3-5 ms por factura
firmada.

Aquí no se firma nada: no hay ninguna clave privada de por medio y por tanto no
hay secreto que filtrar por tiempos de ejecución. El riesgo de una
implementación propia es el contrario —dar por buena una firma falsa—, y contra
eso está escrita.

### El detalle que no se deja al azar

`_verificar_rsa` reconstruye el bloque PKCS#1 entero y compara bytes. La forma
natural de escribirlo es la contraria —abrir el bloque descifrado, saltarse el
relleno y leer el resumen de dentro—, y así se escribió durante años en medio
mundo. Un lector permisivo acepta bloques con el relleno corto y basura detrás,
y con eso se fabrican firmas falsas sin tener la clave privada: es el fallo de
Bleichenbacher de 2006, que volvió en 2014 como «BERserk».

Que la diferencia es real está comprobado, no supuesto. Sobre el mismo bloque
forjado `00 01 FF 00 <DigestInfo> <basura>`, la versión ingenua da la firma por
buena y esta la rechaza.

Con precisión, porque conviene no exagerar: fabricar uno de esos bloques exige
que el exponente público sea pequeño —3 o 17—, y con 65537, que es lo normal,
no se puede. Pero certificados con exponente 3 los hay, escribirlo bien cuesta
cero, y la alternativa es un validador que da por buena una firma falsa.

### Cómo se prueba sin facturas firmadas

`MuestrasFE/` no se versiona, así que los tests **firman de verdad**: montan un
certificado X.509 a mano en DER y firman con una clave RSA de 512 bits cuyos
primos están escritos en el fichero de tests.

Tener la clave privada es lo que permite lo que ninguna factura real permite:
fabricar bloques PKCS#1 a medida —incluida la falsificación de arriba— y
comprobar que se rechazan uno por uno.

### El resultado sobre las muestras

Las cinco muestras firmadas del Gobierno verifican enteras, resúmenes y RSA.
Una de ellas, `sample-factura-firmada-31`, sale con el certificado **caducado**:
vencía el 31-01-2009 y la firma declara el 25-02-2009. Es la misma factura que
ya traía el descuadre de 22,08 € en la base imponible.

Las cinco usan RSA-SHA1 y cuatro tienen claves de 1024 bits, así que salen con
aviso y no con error: la firma puede ser auténtica, el algoritmo ya no da
garantías.

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

Los tres tipos de rechazo que existen —el de forma, el de contenido y el de
firma— ya están cubiertos. Probarlo contra facturas ajenas también está hecho:
73 europeas y 9 españolas, ninguna escrita aquí, y cada pasada encontró fallos
que la inspección del código no había encontrado. Lo que queda es de otra
clase:

**La cadena de confianza de las firmas.** Hoy se comprueba que el documento no
se haya tocado y que la firma cuadre con su certificado. Falta saber de quién
es ese certificado y si sigue vivo, y eso exige la lista de confianza europea y
consultas OCSP. Es la primera decisión de producto de verdad: obliga a salir a
la red, y salir a la red rompe la promesa de que nada sube a ningún sitio.

**Las reglas de IVA por línea.** Ahora se comprueba el desglose contra las
líneas, pero no que el tipo declarado en cada línea sea coherente con el
producto. Eso ya no es EN 16931: es la Ley del IVA, y hace falta saber qué se
vende.

**Un servicio, no solo una herramienta.** Todo esto se usa desde la consola o
como biblioteca. Lo que hace falta para venderlo es que alguien pueda soltar un
fichero y ver el informe sin instalar nada. Eso ya está comprobado que se puede
hacer sin servidor: ver más abajo.

## Sin servidor: el validador dentro del navegador

`web/` no es la página del producto, es la prueba de que la página es posible.
Pyodide compila Python a WebAssembly y lxml está entre los paquetes portados,
así que el validador entero corre dentro del navegador de quien mira la
factura. **El fichero no se sube a ningún sitio**, lo que ahorra a la vez un
servidor que mantener y la custodia de datos fiscales ajenos.

La duda real no era si arrancaba Python, sino si esa compilación de lxml traía
soporte de esquemas XSD: libxml2 se puede compilar sin él, y `esquema.py`
entero depende de `etree.XMLSchema`. Lo trae.

Las doce comprobaciones de `web/prueba.py` dan el mismo resultado que en Python
nativo —mismos códigos, mismos importes— pese a que ahí libxml2 es 2.9.10 y en
local 2.11.9. Medido: 42 s el primer arranque, 4,8 s con la caché caliente,
10 ms por factura, y un lote de 200 en 2 segundos.

```
python -m build --wheel --outdir dist
python -m http.server 8765
```

Y abrir <http://127.0.0.1:8765/web/>. Los detalles, en [`web/LEEME.md`](web/LEEME.md).

## Fuentes

- [RD 238/2026 en el Observatorio de Contratación Pública](https://obcp.es/noticias/real-decreto-2382026-de-25-de-marzo-por-el-que-se-desarrolla-el-sistema-de-facturacion)
- [Qué cambia de verdad tras el RD 238/2026 — ASSET](https://asset.es/factura-electronica-b2b-en-espana-que-cambia-de-verdad-tras-el-rd-238-2026/)
- [Guía RD 238/2026: estados y plazos de pago](https://www.lealtadis.es/factura-electronica-b2b-estados-pago-pymes/)
- [Artefactos oficiales de validación EN 16931 (CEN/TC 434)](https://github.com/ConnectingEurope/eInvoicing-EN16931)
