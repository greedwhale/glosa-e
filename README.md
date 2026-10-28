# Factura-e

Validador de facturas electrónicas españolas y control de plazos de estados,
según el RD 238/2026.

## Estado actual

| Módulo | Qué hace | Estado |
|---|---|---|
| `validador/nif.py` | Valida NIF, NIE y CIF con sus dígitos de control | Terminado |
| `validador/calendario.py` | Días hábiles españoles y plazo de 4 días de los estados | Terminado |
| `validador/formato.py` | Detección de formato y versión (Facturae, UBL, CII, EDIFACT, las respuestas `ApplicationResponse` de UBL y los acuses `DocumentStatus` de la solución pública) | Terminado |
| `validador/acuses.py` | Los acuses de la solución pública: la cabecera, el estado de cada factura y su localizador | Terminado |
| `validador/sintaxis.py` | El mapa: dónde vive cada campo de EN 16931 en UBL, CII y EDIFACT | Terminado |
| `validador/en16931.py` | Campos obligatorios y cuadre aritmético, sobre UBL, CII y EDIFACT | Terminado |
| `validador/iva.py` | El desglose de IVA: bases, cuotas, categorías y exenciones | Terminado |
| `validador/codigo_unico.py` | Código único de factura: duplicados, numeración y fechas | Terminado |
| `validador/cuentas_de_cobro.py` | Las cuentas en que cada emisor pide el pago, comparadas entre sus facturas | Terminado |
| `validador/solucion_publica.py` | El anexo I: lo que la solución pública pide a una factura UBL que declara su CIUS | Sobre la orden publicada el 05-10-2026; sus reglas nuevas, todavía no |
| `validador/qr_fiscal.py` | La dirección del QR de VERI*FACTU o de TicketBAI, comparada con la factura que la lleva | Terminado |
| `validador/incidencias.py` | Tipos comunes (`Incidencia`, `Informe`) que comparten los módulos de reglas | Terminado |
| `validador/cifras.py` | Cómo se escriben cifras y fechas en lo que lee una persona: coma decimal, miles, «Tiene» tal cual y dd-mm-aaaa | Terminado |
| `validador/esquema.py` | Validación de forma contra los XSD oficiales, con los errores traducidos | Terminado |
| `validador/facturae.py` | La aritmética del formato nacional: totales, líneas, impuestos y lote, y los tres órganos de FACe | Terminado |
| `validador/firma.py` | La firma XAdES: integridad del documento y verificación RSA y ECDSA, sin salir a la red | Terminado |
| `validador/cadena.py` | De quién es el certificado: la cadena hasta un ancla de confianza instalada | Terminado |
| `validador/revocacion.py` | Si anularon el certificado: listas de revocación (CRL), sin salir a la red | Terminado |
| `validador/ocsp.py` | Las respuestas OCSP que el documento trae dentro: leídas, verificadas y consultadas por el informe | Terminado |
| `validador/tsl.py` | De dónde salen las anclas: la lista de confianza (TSL) del Estado, verificada | Terminado |
| `validador/sellos.py` | El sello de tiempo (RFC 3161 dentro de XAdES): quién acredita la fecha de la firma | Terminado |
| `validador/edifact.py` | El cuarto formato: la tira de ISO 9735, sus grupos y sus cuentas | Terminado |
| `validador/factura.py` | El orquestador: forma y contenido sobre el mismo documento, y lotes | Terminado |
| `validador/bitacora.py` | La bitácora del sitio: índice y artículos, generados de una plantilla | Terminado |
| `validador/novedades.py` | Las novedades: cada regla nueva o retirada del validador, en una página y en un canal Atom | Terminado |
| `validador/atom.py` | Los dos canales Atom del sitio, el de las novedades y el de la bitácora, con el mismo molde | Terminado |
| `validador/indexnow.py` | El aviso a Bing, por IndexNow, de las páginas que cambiaron desde el último | Terminado |
| `validador/__main__.py` | La línea de órdenes | Terminado |

3803 tests, todos en verde.

```bash
.venv/Scripts/python.exe -m pip install --no-deps -r requisitos-pruebas.txt
.venv/Scripts/python.exe -m pytest -q
```

Corren también en GitHub, en cada push y en cada pull request
(`.github/workflows/pruebas.yml`), sobre una copia recién sacada y con las
versiones de `requisitos-pruebas.txt`. Allí se saltan las que necesitan lo que
no se versiona —facturas de terceros, el anexo de Hacienda, los esquemas y las
anclas montados— y el registro dice cuáles.

Ese número lo vigila `tests/test_documentacion.py`: recolecta la suite y se
pone rojo si esta línea se queda atrás. Antes decía 985 y hacía meses que no
era cierto —nadie mintió, es lo que hacen los números escritos a mano—, y en
la primera pantalla de un producto cuya tesis es no afirmar de más eso pesa.

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

Acepta ficheros sueltos, carpetas —**enteras**, subcarpetas incluidas— o comodines. Devuelve 0 si todo está bien, 1
si hay algún error y 2 si no hay nada que mirar, para poder encadenarlo en un
script. Con `--solo-errores` calla los avisos y deja solo lo que impide cobrar.
Con `--esquemas CARPETA` comprueba además la forma, con `--anclas CARPETA` de
quién es la firma y con `--revocaciones CARPETA` si el certificado sigue vivo;
ver más abajo. `--ver-anclas` y `--ver-revocaciones` enseñan lo que hay
instalado y no validan nada.

**`--recuento`, para mandar el resultado a otra persona, desde el 19-10-2026.**
En vez del informe de cada fichero saca cuántas veces sale cada código y en
cuántos documentos, con su gravedad y su norma, y cuántos documentos hay de
cada formato. Es lo que pide el informe de brecha: quien factura lo pasa en su
equipo y manda solo eso. El informe normal no vale para mandarlo, porque se
hizo para quien tiene las facturas delante: dice el nombre de cada fichero, el
valor que está mal y, entre ficheros, el código único, que es el NIF, el
número y la fecha. El recuento no lleva mensajes ni campos (un mensaje puede
citar el valor), ni las carpetas de los esquemas y las anclas, que pueden
llevar el nombre de usuario del equipo. Lo vigila
`tests/test_recuento.py`, que no mira una lista de datos escrita a mano: saca
todos los textos de las facturas de `ejemplos/` (cada valor y cada atributo
del XML, cada elemento del EDIFACT) y los nombres de los ficheros, y falla si
alguno sale. Cuatro roturas provocadas la ponen en rojo: el nombre del fichero
en los formatos, el valor de la incidencia en su línea, contar las veces por
documento y que la consola imprima el informe normal. La tercera no mordía con
los ejemplos, donde ningún código sale dos veces en la misma factura, y por eso
hay una prueba con un lote hecho a mano.

**Con las combinaciones, también desde el 19-10-2026.** El recuento dice además
cuántos documentos llevan exactamente los mismos códigos, y en los formatos, el
código del tipo de factura (380, 381, 384...; en Facturae, el tipo y la clase,
como FC OO). Lo pidió la prueba del informe de ejemplo (paso 14b): con solo las
cuentas, que las 18 facturas de `SPFE-RETENCION` fueran las mismas 18 de
`BR-CO-16` se deducía de que los números coincidían, y el informe tenía que
decirlo como deducción. Con las combinaciones se lee: una línea de 18
documentos con los dos códigos juntos, y otra con las 3 rectificativas (384),
que son las que sí cuadran el total. Lo que llevan todos los documentos se
dice una vez arriba y no se repite en cada línea, porque las dos notas que
lleva cualquier factura de la solución pública tapaban lo demás; con un solo
documento no se saca nada en común. El tipo es texto del documento, así que
solo sale si es un código: tres cifras, o los de las listas cerradas de
Facturae; si trae otra cosa, dice "tipo sin código" y no lo copia. Seis
roturas provocadas lo ponen en rojo: contar lo que contiene en vez de lo
exacto, sacar lo común de un documento solo, quitar el filtro del tipo, poner
el formato en cada línea con un formato solo, y perder el tipo en Facturae o en
los abonos de UBL; y dos más, el tipo en CII y en EDIFACT.

Y antes de las combinaciones, **los códigos que van siempre juntos**: los que
salen exactamente en los mismos documentos, ni uno más ni uno menos, que casi
siempre son el mismo fallo visto por dos reglas. Las combinaciones lo dicen
también, pero en un lote desordenado no se ve. Medido el 19-10-2026 sobre las
146 muestras públicas de `muestras/`, de 11 formatos y con los esquemas (sin
ellos sale una combinación menos): 89 combinaciones, 70 de un solo documento y
diez con más de veinte códigos;
y 10 grupos de códigos juntos, el primero de 73 documentos (`BR-13` y `BR-14`,
los dos totales del documento) y el segundo de 31 (`BR-07` y `BR-10`, el
nombre y la dirección del comprador). Se agrupa por el conjunto de documentos y
no por la cuenta: dos códigos con 18 cada uno en facturas distintas no van
juntos, y la prueba lo provoca. Lo que sale en todos no se repite aquí.

**Y en la web, desde el mismo día.** Al pie de cada informe va el mismo
recuento, con un botón para copiarlo y una línea para escribir si hay dudas.
Iba cerrado en un desplegable hasta el 25-10-2026, y se titulaba por para quién
era y no por lo que era; ahora se ve entero. Lo escribe la misma
función de Python (`InformeLote.recuento`), y la página solo lo pinta, así que
no puede llevar algo que la consola no lleve; la prueba de los textos de las
facturas se repite con el Python de `glosa.js` tal cual corre allí. Si el
navegador no deja usar el portapapeles, el texto queda seleccionado y se dice
que se copie con Ctrl+C: medido el 19-10-2026 en el navegador de Claude, que
no lo deja ni con un clic de verdad. Para un fabricante pequeño, que antes
tenía que instalar Python y el programa para sacarlo, es la diferencia entre
probarlo y no probarlo.

**Cada fichero cae en uno de tres estados, no de dos:** correcto, con errores,
o **sin comprobar**. Lo tercero es el fichero que no existe, no se puede leer o
cuyo formato no se reconoce, y la respuesta de UBL a la que no se le ha podido
pasar su esquema (ver «Las respuestas: `ApplicationResponse`»). No es correcto
ni incorrecto: es que no se ha mirado, y también devuelve 1.

```
1 fichero(s) · 0 correcto(s) · 0 con errores · 1 SIN COMPROBAR.
```

Parece un detalle y no lo es. Antes ese fichero se contaba entre los buenos y
el programa devolvía 0, así que **una letra de más en la ruta daba un lote
entero por bueno sin haber abierto nada.** Dar por válido lo que no se ha visto
es lo peor que puede hacer un validador; era el fallo más grave que ha tenido
este proyecto y no lo cazó ningún test: lo cazó un usuario escribiendo mal una
carpeta.

En la carpeta `ejemplos/` hay diez documentos preparados: dos facturas
correctas, una repetida en otro fichero, otra cuyas líneas no cuadran con el
total, una en sintaxis CII con dos tipos de IVA en las líneas y uno solo en el
desglose, un abono correcto, un Facturae 3.2.2 firmado (`fe-0001.xml`) y tres
en EDIFACT: `edi-0001.edi`, correcta; `edi-0002-cortado.edi`, a la que le
faltan tres segmentos y lo único que la delata es que la cuenta del sobre no
sale; y `edi-0003-una-de-cinco.edi`, correcta salvo el UNA, que trae cinco
caracteres de los seis que manda ISO 9735 y se lee con una nota.

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
  CII vD16B (factura) · dice seguir EN 16931 — 2 error(es).

  [BR-S-08 · EN 16931] La base declarada para S (tipo general) al 21% no
  coincide con la suma de lo que va a ese tipo.
    Campo: Base imponible de S (tipo general) al 21%
    Debería ser: 100,00 (línea 1)
    Tiene: 150.00

  [IVA-TIPO-SIN-DESGLOSE · De la casa] Hay 50,00 a S (tipo general) al 10%,
  pero el desglose no trae ninguna entrada a ese tipo. El desglose va por
  categoría y tipo, no solo por categoría.
    Campo: Desglose de IVA
    Debería ser: una entrada al 10%
    Tiene: línea 2

ejemplos\f-0006.xml
  UBL v2.1 (factura) · dice seguir EN 16931 — 2 error(es).

  [BR-CO-10 · EN 16931] La suma de importes de línea que declara la factura
  no coincide con la suma real de sus líneas. Suele ser una línea añadida o
  modificada sin recalcular el total.
    Campo: Suma de importes de línea
    Debería ser: 90,00 (suma de la única línea)
    Tiene: 100.00

  [BR-S-08 · EN 16931] La base declarada para S (tipo general) al 21% no
  coincide con la suma de lo que va a ese tipo.
    Debería ser: 90,00 (línea 1)
    Tiene: 100.00

ejemplos\fe-0001.xml
  Facturae v3.2.2 (factura) · firmado — sin errores, 1 aviso(s).

  [FIRMA-DEBIL · Firma electrónica] La clave del certificado es de 512 bits.
  Para firma electrónica se piden 2048 como mínimo.
    Campo: Clave del certificado
    Debería ser: 2048 bits o más
    Tiene: 512 bits

ejemplos\r-0001.xml
  UBL v2.1 (abono) · dice seguir EN 16931 — sin errores.

Entre ficheros:

  [CU-10 · RD 238/2026] Esta factura ya estaba registrada: mismo emisor,
  mismo número y misma fecha. Es la misma factura dos veces, salvo que sean
  los duplicados de una operación con varios destinatarios (art. 14.2 del
  Reglamento de facturación), que repiten el número a propósito. La primera
  viene en f-0002-bis.xml y esta en f-0002.xml.
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
- **Prórroga para informar estados** (disposición transitoria tercera): son las
  **personas físicas y las entidades en régimen de atribución de rentas** en el
  IRPF cuyo volumen de operaciones no haya excedido de 8 millones las que
  tienen doce meses adicionales para los artículos 10 y 12. Hasta esa fecha
  informar estados es voluntario. El umbral de ocho millones **solo** aparece
  en las disposiciones transitorias segunda y tercera: no gradúa el acceso a la
  solución pública, que no tiene umbral.
- **Solución pública gratuita**: la desarrolla y gestiona la AEAT (art. 11.1) y
  **no está limitada por volumen de facturación**: el artículo 11 no pone
  ningún umbral. Lo que sí impone es la **sintaxis**: quien la use «deberá
  emplear la sintaxis UBL» (art. 11.2). Es decir que la vía gratuita **no
  admite Facturae ni EDIFACT**, y quien emita en esos formatos tiene que
  transformar antes.
- **Transformar entre las cuatro sintaxis es obligación legal de las
  plataformas privadas** (art. 7.2): «deberán tener capacidad de transformar el
  mensaje de factura entre todos los formatos admitidos garantizando la
  preservación de la autenticidad de su origen y la integridad de su
  contenido». Y cuando el emisor y el destinatario usan plataformas distintas,
  la transformación **recae en la del emisor y ocurre antes de la firma**
  (art. 7.4).
- **El PDF de acompañamiento, el primer año** (disposición transitoria
  segunda): quien supere los 8 millones deberá acompañar cada factura
  electrónica de un PDF legible durante los doce meses siguientes a que el
  decreto le sea aplicable, salvo que el destinatario acepte expresamente
  recibirla en su formato original. Ese PDF **no** se remite a la solución
  pública.

## ⚠️ Corrección importante sobre las fechas

**Desde el 06-10-2026 las fechas están fijadas, y el plazo ya corre.** Hasta
ese día no lo estaban. Al contrastar fuentes salían versiones incompatibles
—unas decían 1 de enero de 2027 para empresas y 1 de julio de 2027 para
autónomos; otras, octubre de 2027 y octubre de 2028; otras incluso enero de
2026—, y lo único sólido era que los plazos empezaban a contar desde la
entrada en vigor de una orden ministerial que no había salido.

Salió. La **Orden HAC/1028/2026** se publicó en el BOE del **05-10-2026**
(BOE-A-2026-20587) y entró en vigor el **06-10-2026**: su disposición final
única dice «el día siguiente al de su publicación», y con ella empieza el
cómputo. Lo que el RD 238/2026 cuenta desde ahí, en su disposición final
cuarta, contado de fecha a fecha:

| Quién o qué | Lo que dice el decreto | Desde |
|---|---|---|
| Quien facturó más de 8 millones de euros el año anterior | apartado 1, a): «Doce meses después» | **06-10-2027** |
| El resto | apartado 1, b): «Veinticuatro meses después» | **06-10-2028** |
| La copia fiel, la interconexión y los requisitos de las plataformas privadas | apartado 2: «transcurridos doce meses desde la entrada en vigor de la referida orden» | **06-10-2027** |

Comprobado leyendo el XML del BOE el 07-10-2026. Cómo se llegó aquí, y lo que
se escribió antes, está en «El binding EN 16931 de Facturae, que no existía»,
más abajo.

Consecuencias prácticas para este proyecto:

1. **La fecha límite es real y está fijada.** Hasta el 06-10-2026 este punto
   pedía no prometer ninguna; ahora se pueden dar las de arriba, con su cita al
   lado.
2. **El anexo I es definitivo; las especificaciones técnicas viven en otro
   sitio.** La orden fija el contenido de la factura en su anexo I y deja «las
   especificaciones técnicas y volumetría» a lo que conste en la Sede
   electrónica de la AEAT (artículo 3.1), que no es el BOE: lo que se mida
   contra ellas hay que vigilarlo como una fuente que se mueve. Lo que el
   validador mide del anexo se está poniendo al texto publicado por tandas (ver
   «La orden en el BOE, y la primera tanda»).
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
[BR-S-08] La base declarada para S (tipo general) al 21% no coincide con la
suma de lo que va a ese tipo.
  Debería ser: 100,00 (línea 1)
  Tiene: 150.00

[IVA-TIPO-SIN-DESGLOSE] Hay 50,00 a S (tipo general) al 10%, pero el desglose
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
| `BR-{X}-5` | El tipo que exige cada categoría en cada línea, descuento y cargo, y que esté: solo lo no sujeto va sin tipo |
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
| `IVA-CERO-ESQUEMATRON` | El IGIC a cero en CII: la norma lo admite y su esquematrón oficial no (nota) |

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
| UBL 2.5 | `UBL-Invoice-2.5.xsd`, `UBL-CreditNote-2.5.xsd`, `UBL-ApplicationResponse-2.5.xsd` | `docs.oasis-open.org/ubl/os-UBL-2.5/` |
| UBL 2.1 | `UBL-Invoice-2.1.xsd`, `UBL-CreditNote-2.1.xsd` | paquete UBL 2.1 de OASIS |
| CII | `CrossIndustryInvoice_100pD16B.xsd` | paquete D16B de UN/CEFACT |
| Facturae | `Facturaev3_2_2.xsd` y equivalentes | sede de facturae.gob.es |

### Qué versión de UBL se le mide a cada documento

Hacen falta las dos, y por una razón que no es de coleccionista: **la solución
pública solo admite UBL 2.5** y todo lo que circula hoy —Peppol, FACeB2B, lo
que sale de cualquier ERP— es UBL 2.1. Van a convivir años.

La regla es que **se puede subir de versión y nunca bajar**. Primero se busca
el esquema de la versión que el documento declara en su `UBLVersionID`, que es
contra el que lo escribieron; si no está, valen los posteriores y ninguno
anterior.

**De la 2.0 no se sube.** Medido el 29-09-2026: `ExtensionContent`, el hueco de
UBL para lo que cada uno quiera meter, era opcional y admitía cualquier cosa en
la 2.0, y desde la 2.1 es obligatorio y solo admite contenido de otro
namespace. Una factura 2.0 con uno vacío es válida en su versión y la rechazan
la 2.1 y la 2.5. Un documento que declara la 2.0 se mide con
`UBL-Invoice-2.0.xsd` o con ninguno, y el aviso dice cuál falta. El coste es
que las facturas 2.0 se quedan sin comprobar la forma mientras ese esquema no
esté instalado; cuántas circulan no está medido.

Las dos mitades están medidas, porque de otro modo serían una suposición
—para las facturas, aquí; para las respuestas, en el apartado siguiente—:

- **Subir vale.** UBL no cambia de namespace entre versiones menores
  —`...:xsd:Invoice-2` es el mismo en la 2.0 y en la 2.5— y cada versión añade
  elementos opcionales sin quitar ni mover los de antes: la secuencia de
  `Invoice` pasa de 53 hijos a 62, no desaparece ninguno y los 53 siguen en el
  mismo orden. Los cinco ejemplos UBL de `ejemplos/` pasan igual los dos
  esquemas.
- **Bajar no.** Una factura 2.5 con un `DefaultLanguageCode` pasa el esquema
  2.5 y **falla** contra el 2.1. Si el validador se dejara caer a la versión de
  al lado, el informe se llenaría de `XSD-ORDEN` inventados contra una factura
  correcta, y quien lo leyera se pondría a arreglar lo que no está roto.

Cuando el esquema que toca no está, se dice cuál falta y no se comprueba la
forma. Es la diferencia entre no saber y equivocarse en voz alta.

Y hay un caso en que la versión se deduce: a un documento **sin**
`UBLVersionID` que declare en su `CustomizationID` un identificador de la
AEAT (`urn:aeat.es:`) se le supone UBL 2.5, porque la solución pública solo
existe sobre esa versión y media docena de sus campos cuelgan de
`cac:CollectionInvoiceLine`, que en UBL 2.1 no existe. Suponerle 2.1 no era
redondear: era mandar a medirla con un esquema que la rechaza entera. Con
el CIUS de abril o el identificador del ejemplo, la suposición se apoya en
que la AEAT ha dicho que la solución pública solo admite UBL 2.5; con otro
de la AEAT que no se conoce, es solo una suposición. Hasta
el 05-10-2026 la deducción colgaba del nombre del CIUS de abril, y el ejemplo
de la propia AEAT, que declara otro identificador y no lleva versión, se
medía como 2.1.

### Las respuestas: `ApplicationResponse`

Un `ApplicationResponse` de UBL es una respuesta a otro documento —aceptada,
rechazada, en trámite—, y lo es el **mensaje de anulación** que la solución
pública incorporará. Hasta el 29-09-2026 salía «No se ha podido validar»: igual
roto que bueno. Ahora se **reconoce, se le mide la forma contra
`UBL-ApplicationResponse-2.5.xsd` y, si la trae, la firma**. Nada más, y el
informe lo dice: la columna del contenido pone «Sin mirar» y la frase final
«No se comprueba [...] el contenido de las respuestas (ApplicationResponse)».

Lo que no se hace es tan importante como lo que sí:

- **No pasa por las reglas de factura.** Tiene familia propia en `formato.py`,
  no `UBL`. Medido con una respuesta que valida contra su esquema: como `UBL`
  recibía 16 errores que no le tocan —`XSD-RAIZ`, 13 reglas `BR-*` y dos
  `CU-*`—, y con el CIUS declarado, `SPFE-TIPO-DE-FACTURA` («es un abono») en
  lugar de `BR-01`. Con una familia propia, todo `if familia == X` contesta
  «no me toca».
- **Los mensajes de la orden sí se miden, desde el 12-10-2026.** El de
  anulación (`cbc:ResponseCode` «CANCELINVOICE», en el anexo I) y los ocho del
  anexo II se reconocen por su código y se miden con su tabla, además de la
  forma y la firma (ver «Los mensajes de la orden: la anulación y los ocho
  estados»). A una respuesta con otro código se le sigue mirando solo lo de
  aquí.
- **Sin esquema, no es «correcta».** La forma es lo que se le comprueba a una
  respuesta, así que sin un `UBL-ApplicationResponse-*.xsd` que compile sale
  **SIN COMPROBAR** con código de salida 1, no «correcto» con 0, aunque traiga
  una firma en pie: que nadie la haya tocado no dice que esté bien escrita.
  **Salvo que se le haya encontrado un error por otro lado** —la firma tocada,
  una entidad en el XML—: entonces sale «con errores», porque eso ya es un
  veredicto. Con una factura sin esquemas todavía se le miden las cuentas, y
  eso no cambia.
- **De la 2.0 no se sube**, como con las facturas (ver arriba), y de la 2.1 a la
  2.4 sí. Medido sobre todos los tipos alcanzables desde `ApplicationResponse`
  —38, 41, 45 y 45—: 0 violaciones al subir a la 2.5, y 400 documentos
  generados desde cada esquema viejo pasan los 400 en el 2.5. Los esquemas
  viejos son copias de `phax/ph-ubl`, no de OASIS, y el de la 2.1 es la CS1: es
  lo que había al alcance. Está en `HALLAZGOS.md`.
- **Subir no vale al revés, y el informe no lo dice.** Lo que es válido en la
  2.1 lo es en la 2.5; lo que es válido en la 2.5 no tiene por qué serlo en la
  2.1. Como solo viaja el esquema de la 2.5, una respuesta que declara la 2.1
  —lo corriente en Peppol— y trae algo que solo existe desde después, como un
  `ext:UBLExtensions` dentro de `cac:DocumentResponse`, sale aquí «sin
  errores», y un receptor que la mire con la 2.1 la rechaza (medido con los dos
  esquemas). La línea del informe dice «v2.1» y no dice con qué esquema se
  midió. Con las facturas pasa lo mismo de la 2.2 a la 2.4; con las respuestas
  es el caso de todos los días.
- **Aunque declare el CIUS de la solución pública**, no recibe `SPFE-ALCANCE`
  ni ninguna otra nota: el anexo I no se le pasa, y lo dice la columna del
  contenido. A una factura que lo declara sí se le pone, porque a ella sí se le
  mide.
- **Un cambio visible.** Antes, una respuesta salía siempre «sin comprobar» y el
  código de salida era 1; una respuesta que valida sale ahora con 0. Quien
  encadene el validador en un guion con una carpeta de respuestas lo notará.

Lo que **no está medido**: el navegador (Pyodide trae libxml2 2.9.10 y el
esquema de `ApplicationResponse` no se ha compilado allí; el banco de
`web/prueba.py` tampoco lleva ninguna respuesta), y ninguna respuesta real de
terceros —no hay ninguna en el repositorio; las de las pruebas son nuestras—.

El catálogo **busca por nombre de fichero en toda la carpeta**, no por una ruta
fija. Cada paquete oficial se descomprime con su propio arbolito y no tiene
sentido obligar a nadie a recolocarlo a mano: se descomprime donde sea, dentro
de `esquemas/`, y ya está. La carpeta se cambia con `--esquemas` o con la
variable de entorno `FACTURAE_ESQUEMAS`.

Si no hay ninguno instalado, **no se comprueba la forma y se dice**, una vez al
final y no una por factura. Callar y aparentar que todo está bien sería lo peor
que podría hacer un validador.

### Los acuses de la solución pública: `DocumentStatus`

A todos sus servicios menos a las dos descargas, la solución pública contesta
con un `DocumentStatus` de UBL: lo dicen el documento de formatos de entrada y
salida de la AEAT (versión 0.1.2, del 20-10-2026, apartado 5.1.1) y su
catálogo de servicios (versión 0.1.3). **Hasta el 26-10-2026 no se
reconocía**: el acuse del ejemplo oficial de remisión (`SendInvoicesSOAP.zip`,
del 15-10-2026) salía SIN COMPROBAR y con salida 1, como un fichero que no se
sabe qué es.

Desde ese día se reconoce, se le pasa el esquema de OASIS
(`UBL-DocumentStatus-2.5.xsd`, que va en el paquete de la página) y se lee lo
poco que está publicado, que es el apartado 5.2.2 del documento de formatos y
el ejemplo:

- **La cabecera**, `cac:DocumentResponse/cac:Response/cbc:ResponseCode`: 200
  si todas las facturas se aceptaron, 406 si solo una parte y 400 si ninguna.
  Sale en una NOTA, `SPFE-ACUSE-RESULTADO`, con la cuenta de facturas. Si falta
  o es otro, un AVISO, `SPFE-ACUSE-CABECERA`.
- **Cada factura**, un `cac:DocumentReference`. Con `cbc:DocumentStatusCode`
  200, que es el del ejemplo, una NOTA con su localizador, que es con lo que se
  descarga después (el catálogo recomienda la descarga por localizador frente
  a la descarga por identificador). Con otro, o sin ninguno, un AVISO: no
  consta como dada de alta.
- **Que digan lo mismo**: un 200 con alguna factura que no lo es, un 400 con
  alguna que sí o un 406 con todas iguales salen con `SPFE-ACUSE-NO-CUADRA`.

Lo que se decidió en cada una:

- **Los códigos de error de una factura no se traducen.** La AEAT no los ha
  publicado: el único estado de factura que se ha visto es el 200 del ejemplo.
  Inventarles un significado sería prometer de más, así que el aviso trae el
  código y la descripción tal cual vienen.
- **El acuse del ejemplo tiene un error de forma, y sale con él.** Le falta
  `cbc:IssueDate`, que `DocumentStatus` exige una vez. Medido el 26-10-2026
  con lxml contra el esquema de OASIS: es su único fallo, y con la fecha
  puesta valida. Lo decidió el titular ese día: un fallo de forma es un error
  venga de quien venga. Lo que contesta el esquema es `XSD-ORDEN` sobre
  `cac:DocumentResponse` («no puede ir en este sitio»), que no deja ver que lo
  que falta es la fecha, y por eso va con una NOTA, `SPFE-ACUSE-FECHA`, que lo
  dice. La AEAT lo confirmó por correo el 28-10-2026: la fecha es necesaria y
  corregirá el ejemplo publicado. El corregido que adjuntó la lleva y pasa sin
  errores, medido ese día.
- **Sin versión es de la 2.5**, no de la 2.1 como lo demás: quien contesta con
  `DocumentStatus` es la solución pública, que solo existe sobre UBL 2.5, y el
  acuse del ejemplo no trae ni versión ni especificación.
- **No se mira el sobre ebXML**, que es el que dice a qué servicio contesta el
  acuse y a qué envío, ni que las facturas existan o que el localizador valga.
  Lo dice la nota que va siempre, `SPFE-ACUSE-ALCANCE`, y también que el acuse
  no dice de quién es.
- **La norma de las fichas es «Servicios web de la AEAT»** y no la orden: la
  orden no define estos acuses, dice que sus servicios se ajustarán a lo que
  la AEAT publique en su Sede.

Las pruebas están en `tests/test_acuses.py`, y cada comprobación se ha roto a
propósito una vez para verla en rojo: sin la detección, sin el esquema, sin las
reglas, sin la nota de la fecha, con todo cuadrando, con el 406 sin mirar, con
otro estado de alta, con el localizador callado, sin contar los
`cac:AdditionalDocumentResponse` y sin la frase del lote. Las diez saltan.

**Medido en el navegador** el 26-10-2026, con el sitio montado en local: un
acuse con la forma del del ejemplo sale con el `XSD-ORDEN` y sus cuatro notas,
igual que en consola, en 16,5 s desde la página recién abierta, con el
arranque de Pyodide dentro. Lo que **no está medido**: ningún acuse real, solo
el ejemplo de la AEAT y los de las pruebas, que son nuestros.

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

**A un árbol con entidades sin expandir no se le pasa el esquema.** libxml2 no
se queja de esquema: levanta `XMLSchemaValidateError: Internal error in XML
Schema validation`, y eso salía por el informe como `VALIDADOR-SE-ATRAGANTA`
—una línea, en inglés, y ninguna otra comprobación del fichero—. Aquí las
entidades no se expanden a propósito, así que lo que se hace es no darle a
libxml2 un árbol que no sabe validar, y decir lo que pasa con `XML-ENTIDADES`,
que es error: el campo que llevaba la entidad se lee vacío, y quien reciba esa
factura puede expandirla y leer otra cosa.

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
enmudecían de golpe BR-24, BR-CO-10, BR-S-08 y todo el IVA: **acusado en falso
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
[BR-S-08 · EN 16931]              te lo rechaza el receptor
[CU-10 · RD 238/2026]            te lo rechaza Hacienda
[XSD-ORDEN · Esquema XSD]        no pasa ni de la puerta
[IVA-TIPO-SIN-DESGLOSE · De la casa]   opinamos nosotros
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
| CU-16 | Dos facturas distintas que dan el mismo código único | Error |

Los huecos y los retrocesos van como aviso a propósito: un hueco puede ser una
factura anulada, y un lote parcial no tiene por qué estar completo. Marcarlos
como error daría falsos positivos constantes.

**CU-16 es la consecuencia de cómo se forma el código.** Serie y número se
pegan sin nada en medio, que es como los trata Verifactu, así que la serie «A»
con el número «12» y la serie «A1» con el número «2» dan las dos `A12`. No es
un duplicado —son dos facturas y quien las emitió no ha hecho nada raro— pero
para cualquier registro que las indexe por su código único son la misma: la
segunda tapa a la primera. Hasta el 22-09-2026 esto salía como CU-10, «es la
misma factura dos veces», que manda a buscar una copia que no existe.

Sólo puede salir cuando la serie viaja en un campo suyo, y de las tres
sintaxis eso sólo pasa en **Facturae**: UBL y CII llevan el número entero en
uno solo —`cbc:ID`, `ram:ID`—, así que dos UBL con el mismo número son un
duplicado de verdad y siguen saliendo como CU-10. Comprobado en el navegador
con las dos parejas. El caso más feo es el mixto —una Facturae con serie `A` y
número `12` contra un UBL cuyo `cbc:ID` es `A12`—, porque ahí cada fichero cree
tener su propio número y ninguno de los dos está mal escrito.

**Los NIF que empiezan por K, L o M son de persona física**, y hasta el
20-09-2026 CU-01 los daba por inválidos todos. Son las claves que asigna la
AEAT a quien no tiene DNI ni NIE: K para menores de catorce años residentes en
España, L para españoles que viven fuera y M para extranjeros sin NIE. Estaban
en la tabla de tipos de entidad, así que se les medía el control del CIF
—letra de la J a la I, o dígito—, y el suyo es el del DNI: el resto de dividir
entre 23. Un `M1234567L` correcto ni siquiera llegaba a comprobarse, porque la
forma del CIF no admite una L de control: salía «el formato no corresponde a un
NIF, NIE ni CIF español» y con ello un error sobre una factura buena. La AEAT
publica la composición —letra, siete caracteres y un carácter de verificación—
pero no el algoritmo, así que se aceptan solo con siete **dígitos**: con letras
en medio no hay nada que dividir entre 23, y lo que no se sabe comprobar no se
da por bueno.

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

**El tope de 60 caracteres está tomado de Verifactu.** La orden del RD 238/2026,
la HAC/1028/2026, salió en el BOE el 05-10-2026 y no fija ninguno: su anexo I
describe `BT-1` como «Serie y número que identifican la factura emitida», sin
longitud, y deja las especificaciones técnicas a lo que conste en la Sede
electrónica de la AEAT (artículo 3.1). Si el tope sale de ahí, puede ser otro.
Es una constante justo para poder cambiarla en una línea.

**La búsqueda del NIF es relativa al vendedor, no absoluta.** Con `//` en lugar
de `./`, la consulta arranca de la raíz del documento aunque se lance desde el
nodo del vendedor: en una factura donde el vendedor solo trae
`PartyLegalEntity` y el comprador sí trae `PartyTaxScheme`, el código único
acababa llevando **el NIF del comprador**. Hay un test que lo fija.

## Las cuentas de cobro: el mismo emisor, otra cuenta

El fraude más caro que llega con una factura no tiene nada mal escrito. Es una
factura correcta, de un proveedor de verdad, que pide el pago en otra cuenta:
alguien ha entrado en el correo del proveedor, o se hace pasar por él, y lo
único que cambia es el IBAN. INCIBE lo describe en su página sobre el fraude
del correo comprometido y aconseja comprobar la cuenta "mediante un canal de
comunicación ajeno al correo electrónico".

Ninguna regla de forma ni de contenido puede verlo, porque mirada sola cada
factura está bien. Se ve poniendo juntas las de un mismo emisor, que es lo que
hace un lote: `validador/cuentas_de_cobro.py` junta, por el NIF de quien emite,
las cuentas de cobro (BT-84) de sus facturas, y **`CUENTA-DISTINTA`** avisa
cuando no son las mismas. Dice cuáles, en cuántas facturas sale cada una y en
qué ficheros, con la que sale en menos al final.

Las decisiones:

- **Aviso, y de la casa.** Cobrar en dos cuentas es legal y corriente. El
  aviso no dice que haya fraude: dice que la cuenta cambia, para que quien va
  a pagar lo confirme antes. Ninguna norma de facturación lo pide.
- **El emisor es el NIF del código único**, leído por el mismo camino, para
  que una factura no pueda ser de un emisor para el código y de otro para las
  cuentas. Pero entran todas las facturas, también las extranjeras: el código
  único solo compara las españolas porque las numeraciones de otros países no
  tienen nada que ver entre sí, y una cuenta nueva es la misma señal venga de
  donde venga.
- **Se compara el juego de cuentas de cada factura**, no cada cuenta suelta:
  dos facturas que ofrecen las mismas dos cuentas no han cambiado nada. La
  cuenta se compara sin espacios y en mayúsculas, porque el IBAN se escribe en
  grupos de cuatro en papel y de corrido en el fichero.
- **Dentro de un fichero también**, porque un Facturae trae varias facturas. Y
  lo que ya dijo un Facturae de sí mismo no se repite entre ficheros: lo que se
  compara para no repetirlo no lleva nombres de fichero, que el informe de un
  fichero solo no conoce.
- **EDIFACT no entra**: su instrucción de pago no tiene mapa. Tampoco las
  facturas sin cuenta, que no han cambiado de cuenta, sino que no dan ninguna.

Medido sobre los 101 ficheros de muestra y de ejemplo: 76 facturas leídas, 61
con cuenta de cobro, de 26 emisores, 12 de ellos con más de una factura. Salen
**tres avisos, los tres entre ficheros de prueba**: dos en las suites europeas
y uno en las facturas de prueba del cliente @firma, que reutilizan el mismo
vendedor en ejemplos distintos con cuentas distintas. Es justo lo que tiene que
decir: mismo NIF, otra cuenta.

Y lo que cuesta: en un lote de 1.000 facturas UBL, 3,05 s con la lectura de
las cuentas y 2,93 s sin ella, el mejor de tres en esta máquina el 25-10-2026.
Dentro de un fichero solo se mira en Facturae: un UBL o un CII es una sola
factura y no puede no cuadrar consigo mismo.

## La bitácora, y por qué se genera

`www.glosa-e.com/bitacora.html`. Es donde se publica lo que este proyecto mide
—hallazgos sobre facturas y normas reales— para quien no va a abrir un
repositorio de GitHub a leer `HALLAZGOS.md`.

Se escribe **solo el artículo**, en `web/bitacora/<nombre>.html`, y el armazón
—cabecera, menú, pie, aviso legal— se lo pone `bitacora.html`, que es la
plantilla. La razón es la de siempre en esta casa: el menú es el mismo letra
por letra en las seis páginas y hay una prueba que se niega a dejarlo
diverger. Si cada entrada fuera una página entera, publicar la sexta sería
copiar el menú por sexta vez y el día que cambie el aviso legal habría que
acordarse de siete sitios. Aquí no hay nada que recordar: las entradas lo
llevan por construcción.

Cada artículo se monta al lado de la plantilla, como `bitacora-<nombre>.html`
y no dentro de una carpeta. Es más feo en la barra de direcciones y es a
propósito: la cabecera compartida enlaza `./glosa.css` y el sello de la huella
busca esa línea letra por letra, así que una entrada un nivel más abajo
obligaría a reescribir rutas a `../`. Esa reescritura **no da error cuando se
hace mal** —la página sale, y sale sin estilo—, y este repositorio ya ha tenido
cuatro veces el mismo fallo con otro disfraz.

### El guardián: fecha y fuente

`SinEntrada`, y no se monta el sitio. Una entrada tiene que declarar
`data-fecha` en forma ISO, `data-titulo`, `data-entradilla` y un
`<footer class="fuentes">` con al menos un enlace.

Las dos que importan son la primera y la última, y las dos por el mismo
motivo: **no se notan en la página publicada**. Sale bien, se lee bien, y no
hay forma de saber de cuándo es la medida ni de dónde salió. Una entrada sin
fecha no es una medida, es una opinión con tipografía; una sin fuente le pide
al lector que se fíe, que es justo lo que esta herramienta dice no hacer.

Las siete negativas están provocadas en `tests/test_bitacora.py`, cada una
rompiendo una entrada por un sitio distinto, y ninguna escribe sobre `web/`.

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
comprueban. Facturae no numera sus reglas como EN 16931 numera las `BR-*`, y
un «FE-07» sonaría a oficial: quien lo buscara en una norma no lo encontraría.

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

### Los tres órganos de una factura a la Administración

Una factura a la Administración tiene que decir a qué tres órganos va: la
oficina contable, el órgano gestor y la unidad tramitadora. Lo pide la Ley
9/2017 de Contratos del Sector Público, en su disposición adicional 32.ª,
apartado 2 (los pliegos los identifican, y "deberán constar en la factura
correspondiente"), y FACe lo comprueba al recibirla: el punto 8 del anexo II
de la Orden HAP/492/2014, que añadió la Orden HAP/1650/2015, valida que los
tres códigos DIR3 tengan valor, que existan y que la relación entre ellos esté
dada de alta.

Facturae los escribe como centros administrativos del comprador, cada uno con
su rol. La pareja de rol y órgano sale del manual del proveedor de FACe
(v1.2.2): el órgano gestor con el rol `02` (receptor), la unidad tramitadora
con el `03` (pagador) y la oficina contable con el `01` (fiscal). La tabla del
mismo manual, pasada a texto, sale con la columna de la descripción corrida una
fila; leída así, cambiaría el órgano gestor por la unidad tramitadora. Vale la
frase, que no se puede leer de dos maneras.

- **`FE-DIR3-FALTA`, aviso.** Cuando el NIF del comprador es de una entidad
  pública (empieza por P, Q o S: artículo 3 de la Orden EHA/451/2008) y falta
  alguno de los tres. Dice cuál, y los dos tropiezos que se ven desde el
  fichero: los centros puestos en el vendedor, donde FACe no los busca, y un
  código sin rol. Es aviso y no error porque **el fichero no dice si va a
  FACe**, y hay entidades con esas letras que no reciben por ahí.
- **`FE-DIR3-ALCANCE`, nota.** Cuando están los tres: sus códigos, y que no se
  ha comprobado que existan en el directorio ni que la relación esté dada de
  alta, porque el directorio no viaja con el validador. Sin la nota, tres
  códigos inventados saldrían sin una palabra y se leería que están bien.

No se mira la forma de cada código: DIR3 tiene varias según el tipo de unidad,
el esquema solo pide diez caracteres como mucho, y una forma mal deducida
rechazaría códigos buenos.

Medido sobre las nueve facturas Facturae de prueba de fuentes oficiales: cinco
van a un comprador con NIF de entidad pública y **ninguna lleva los centros**.
Las cinco son de 2007 a 2012, en las versiones 3.0 y 3.1, que FACe ya no
admite (punto 1 del mismo anexo); hoy saldrían con el aviso, y salen.

## El binding EN 16931 de Facturae, que no existía

Añadido el **06-09-2026**. Hasta ese día `en16931.py` devolvía lista vacía ante
un Facturae, con este motivo escrito al lado:

> «Facturae no es un perfil de EN 16931 y no tiene por qué serlo: es el formato
> nacional, con su propio esquema y su propia aritmética.»

Era cierto, y dejó de serlo. El **artículo 7.1 del RD 238/2026** exige que la
factura se ajuste al modelo semántico EN 16931 **bajo cualquiera de las cuatro
sintaxis admitidas**, y Facturae es la cuarta.

**Cuándo obliga, que no es lo que aquí se escribió primero.** El decreto está
en vigor desde el 20-04-2026, pero su aplicación efectiva queda **diferida**:
su disposición final cuarta, apartado 1, la cuenta «desde la entrada en vigor
de la orden ministerial prevista en el apartado 1 de la disposición final
tercera». Esa orden es la HAC/1028/2026, publicada en el BOE el 05-10-2026 y
en vigor desde el **06-10-2026**, el día siguiente. De ahí salen «Doce meses
después» para quien facture más de 8 M€ (**06-10-2027**) y «Veinticuatro
meses después» para el resto (**06-10-2028**), contados de fecha a fecha; y el
apartado 2 lleva al 06-10-2027 la copia fiel, la interconexión y los
requisitos de las plataformas privadas. El 06-10-2026 no obliga a nadie: es
cuando empieza a contar. Hasta el 07-10-2026 aquí ponía 01-10-2027 y
01-10-2028: la orden era un proyecto, publicado el 16-04-2026, con entrada en
vigor prevista el 01-10-2026.

### No hay mapa oficial, y por eso hay que escribirlo

CEN publicó `CEN/TS 16931-3-2` para UBL, `-3-3` para CII y `-3-4` para
EDIFACT —tres ediciones, 2017, 2020 y 2026, y esta última mapea a `UN/CEFACT
INVOIC D.24A S4` aunque su portada siga diciendo `D16B`, que no se actualizó—.
**Para Facturae no publicó nada.** No existe ninguna parte de la norma que diga
qué elemento de Facturae es qué término de negocio, así que el mapa de
`SINTAXIS_FACTURAE` está escrito aquí y las decisiones son nuestras. Por eso
cada hueco lleva escrito el porqué, y por eso están aquí también.

Un detalle de forma que sale gratis: **solo la raíz lleva espacio de nombres**.
Medido sobre `ejemplos/fe-0001.xml` —116 elementos, 27 con espacio de nombres y
los 27 son la firma XAdES—. Como la única diferencia entre 3.0, 3.1, 3.2, 3.2.1
y 3.2.2 es la URI de esa raíz, que el mapa no nombra nunca, **el mismo mapa vale
para las cinco versiones**.

### Los seis huecos, y qué se decidió en cada uno

| Término | Qué pide EN 16931 | Qué tiene Facturae | Decisión |
|---|---|---|---|
| **BT-24** | identificador de especificación | nada. Lo más parecido es `SchemaVersion`, que dice «3.2.2» | `SIN_MAPA`; BR-01 sale como **NOTA** |
| **BT-118** | categoría de IVA de la lista UNCL5305 (S, Z, E, AE, K, G, O, L, M) | `TaxTypeCode`, que dice **qué impuesto** es (01 IVA, 02 IPSI…), no de qué categoría | `SIN_MAPA`; una NOTA por documento |
| **BT-112** | total con impuestos = base + IVA | `InvoiceTotal`, que además **resta las retenciones** | `SIN_MAPA` |
| **BT-110** | suma de las cuotas de IVA por categoría | `TotalTaxOutputs`, que además **suma el recargo de equivalencia** | `SIN_MAPA` |
| **BT-126** | identificador de línea | nada. `SequenceNumber` existe pero significa el orden en un pedido | `SIN_MAPA` |
| **BT-114** | redondeo | nada | `SIN_MAPA`, igual que en EDIFACT |

La decisión de BT-24 es la que sostiene el resto. Aplicando BR-01 en estricto,
**todas las facturas de España suspenden**, hoy y siempre, y no por estar mal
hechas sino porque el formato no tiene dónde escribirlo. Un validador que
devuelva eso no informa de nada.

Por eso sale NOTA y no error. NOTA es la gravedad que existe para decir *qué se
aceptó y con qué base*, y esto es exactamente eso: no hay nada que arreglar en
el documento.

Y no es lo mismo que AVISO, aunque las dos digan «no se ha podido comprobar».
Lo que las separa es **de quién es el hueco**: `REVOCACION-SIN-COMPROBAR` sale
como aviso porque falta la lista y con otra lista podría salir otra cosa —queda
algo pendiente—, y `BR-01` sale como nota porque el formato no tiene dónde
guardar ese dato y no hay nada que esperar. La portada lo decía mal hasta el
22-09-2026: daba «no se ha podido comprobar» como definición de aviso, que es
la frase que llevan dentro varias notas. Está en HALLAZGOS, punto 35.

### Los totales de Facturae son superconjuntos de los europeos

BT-112 y BT-110 son el mismo descubrimiento dos veces, y es el más importante
de todos porque **no se ve leyendo: solo aparece midiendo**.

España carga en la factura impuestos que el modelo básico de EN 16931 no
modela. El `InvoiceTotal` de Facturae resta las retenciones —el IRPF de una
factura profesional— y su `TotalTaxOutputs` suma el recargo de equivalencia,
que no es IVA. Los importes se llaman igual que los europeos y **miden cosas
distintas**.

Con el mapa directo, sobre las 13 Facturae reales disponibles:

| | Facturas acusadas | Facturas realmente defectuosas |
|---|---|---|
| BR-CO-15 (total con IVA) | 6 | 0 |
| BR-CO-14 (total de IVA) | 4 | 0 |

Diez acusaciones falsas sobre facturas correctas. Una de ellas al céntimo:
`1.163,52 + 279,24 = 1.442,76`, menos `58,18` de retención, da exactamente los
`1.384,58` que escribe el fichero.

Se podría leer la retención y el recargo y ajustar la resta, pero entonces lo
que se compara ya no es BT-112 ni BT-117, y la regla diría comprobar una cosa
mientras comprueba otra. La aritmética que Facturae **sí** garantiza —la que
escriben las anotaciones de su propio esquema— ya la comprueba `facturae.py`
con los códigos `FE-*`, que conocen el recargo y la retención y los tratan como
lo que son.

No es que Facturae esté mal escrito ni que la norma se quede corta: es que
miden cosas distintas, y llamarlas igual sería el error.

### Dos fallos que este binding destapó en código que ya estaba

Ninguno de los dos daba error: los dos devolvían una respuesta plausible.

**`texto()` cogía la primera letra.** Una ruta que llama a una función de XPath
devuelve el valor suelto y no una lista de nodos, así que `encontrados[0]`
sacaba un carácter: `name(.)` daba «D» en vez de «Discount» y «C» en vez de
«Charge». Ningún cargo casaba con su marca, todos se restaban como descuentos,
y dos facturas correctas salían incumpliendo BR-CO-11. Hasta Facturae ninguna
sintaxis necesitaba una función en una ruta, así que la rama no existía.

**`marcas_de_cargo` se compara en minúscula.** Quien compara pasa la marca por
`.lower()` antes —por eso EDIFACT lleva `("c",)`—, y el mapa nuevo llevaba
`("Charge",)`. Mismo síntoma que el anterior y encontrado detrás de él.

### El fallo que destapó

`_reglas_obligatorios` no conocía `SIN_MAPA`. EDIFACT ya traía dos huecos
—BT-114 y BT-121— pero ninguno cae en la tabla de campos obligatorios, así que
nunca llegó a verse. Facturae es la primera sintaxis que pone un hueco en un
campo obligatorio, y sin arreglarlo BR-01 salía como `ERROR · (falta)` en todas
las facturas del país.

Ahora la regla distingue dos cosas que se parecen y no son iguales: **que la
factura no haya escrito el campo**, que es un defecto suyo, y **que la sintaxis
no tenga dónde escribirlo**, que no lo es. Lo mismo se arregló en `iva.py` para
BR-47 y para `IVA-SIN-CATEGORIA`.

### Otras dos divergencias que no son huecos

No impiden leer el dato, pero significan cosas distintas a los dos lados y
constan aquí para que nadie las dé por equivalentes:

- **BT-3, el tipo de documento.** EN 16931 usa UNCL1001 —380 factura, 381
  abono—. Facturae usa `InvoiceDocumentType` con FC, FA y AF, más
  `InvoiceClass` con OO, OR, OC, CO, CR y CC. Se lee el elemento tal cual y
  **no se traduce**: BR-04 comprueba lo que puede comprobar, que el documento
  diga de qué tipo es.
- **BT-40, el país.** Facturae escribe `ESP`, en ISO 3166-1 alfa-3; EN 16931
  pide alfa-2, `ES`. BR-09 solo mira que esté, así que hoy no salta.

### Lo que el binding añade de verdad, medido

Comparado con lo que ya había —el XSD oficial más las reglas de `facturae.py`—
el solape es alto y hay que decirlo: de cinco defectos inyectados, **el XSD ya
cazaba cuatro** (sin nombre del comprador, sin país del vendedor, sin líneas,
sin fecha). Las reglas de campo obligatorio de EN 16931 sobre Facturae en gran
parte repiten lo que el esquema ya obliga, con mejor mensaje y nombrando el BT.

Donde sí añade es donde **el XSD de Facturae es más permisivo que la norma**, y
eso ya no es teoría: sobre las 13 Facturae reales disponibles, **10 salen sin un
solo error** y las 3 que quedan fallan `BR-46` por el mismo motivo —una entrada
del desglose sin `TaxAmount`, que el esquema declara opcional (`TaxAmount?`) y
EN 16931 exige—. Son ficheros que pasan el XSD oficial y pasan las reglas de
`facturae.py`.

El otro caso de la misma familia es `UnitOfMeasure`, opcional en Facturae y
obligatorio en EN 16931 por BR-23.

## BR-22, BR-23 y BR-26: lo que toda línea tiene que traer

Añadidas el **06-09-2026**, y son las tres que separan «esta factura está bien
formada» de «esta factura dice qué se vendió»:

| Regla | Término | Qué exige |
|---|---|---|
| **BR-22** | BT-129 | cada línea dice **cuántas** unidades factura |
| **BR-23** | BT-130 | y **en qué unidad** se miden |
| **BR-26** | BT-146 | y a **qué precio** por unidad, sin impuestos |

Sin las tres, una línea es una descripción y un importe: se puede pagar, pero
no se puede comprobar, ni casar con un albarán, ni discutir.

Los mapas salen del esquematrón oficial de CEN, no de la memoria. Para EDIFACT,
literal: `BR-22 = S_QTY/C_C186[D_6063='47']/D_6060`, `BR-23` el mismo compuesto
un dato más allá (`D_6411`), y `BR-26 = S_PRI/C_C509[D_5125='AAA']/D_5118`. En
UBL la unidad **va en un atributo** (`InvoicedQuantity/@unitCode`), que es el
único campo de todo el mapa que lo hace, y en un abono la cantidad se llama
`CreditedQuantity`: la unión coge la que haya, o BR-22 y BR-23 saldrían
inventadas en todos los abonos correctos.

### El resultado, con su control

Nueve ficheros EDIFACT escritos por la Comisión Europea frente a nueve
EANCOM reales del gran consumo español:

| | Ficheros | BR-22 | BR-23 | BR-26 |
|---|---:|---:|---:|---:|
| Ejemplos oficiales de CEF | 9 | 0 | 0 | 0 |
| **EANCOM real español** | 9 | 0 | **8** | **7** |

**El control es la primera fila.** Que los ejemplos de quien escribió la norma
salgan a cero es lo que dice que las reglas están bien puestas; si fallaran
también ahí, el defecto sería del mapa y no de las facturas. Sobre las 157
facturas de terceros disponibles en total, CII sale a cero en las tres y UBL
falla una de 43: no hay ruido.

La segunda fila es el hallazgo. **Ocho de cada nueve facturas EANCOM reales no
dicen en qué unidad miden lo que facturan**, y siete no traen precio unitario.
No es un descuido de un emisor: es cómo se factura en el sector.

Y en Facturae, 3 de 13 fallan BR-23 por la misma razón que documenta la sección
anterior: `UnitOfMeasure` es opcional en el esquema nacional y obligatoria en la
norma europea. Son ficheros que pasan el XSD oficial.

### BR-21 y BR-25: quién es cada línea y qué se factura en ella

Las dos que faltaban del mismo grupo. BR-21 pide que cada línea lleve
identificador (BT-126) y BR-25 que diga qué se factura (BT-153).

| Sintaxis | BT-126 | BT-153 |
|---|---|---|
| UBL | `./cbc:ID` | `./cac:Item/cbc:Name` |
| CII | `./ram:AssociatedDocumentLineDocument/ram:LineID` | `./ram:SpecifiedTradeProduct/ram:Name` |
| EDIFACT | `./S_LIN/D_1082` | `./S_IMD/C_C273/D_7008` |
| Facturae | **no existe** | `./ItemDescription` |

Sobre 157 facturas de terceros: BR-21 en 15 y BR-25 en 14. Los 13 BR-21 de
Facturae **no son un defecto de esas facturas**: el formato no tiene dónde
escribir un identificador de línea, y por eso salen como nota y no como error.

### BT-118: deducir la categoría de IVA que Facturae no escribe

Facturae no tiene categoría UNCL5305. Su `TaxTypeCode` contesta a otra
pregunta —qué impuesto es: 01 IVA, 02 IPSI, 03 IGIC— y durante un tiempo eso
dejó **todas** las reglas de categoría calladas en toda factura española.

Ahora se deduce lo que se puede deducir:

| Lo escrito | Se deduce | Por qué |
|---|---|---|
| `01` con tipo > 0 | **S** | IVA a tipo positivo solo puede ser sujeta y no exenta |
| `03` | **L** (BR-IG-*) | el IGIC identifica su familia de reglas |
| `02` | **M** (BR-IP-*) | ídem el IPSI |
| `01` con tipo 0 | **nada** | y se dice |

La última fila es la importante. Un cero en Facturae puede ser exenta, no
sujeta, intracomunitaria, exportación o inversión del sujeto pasivo —Z, E, O, K,
G o AE—. Elegir la más probable y presentarla como leída sería inventar; en su
lugar sale `IVA-CATEGORIA-A-CERO`, una vez por documento y como nota. Pasa en
3 de 13 facturas Facturae de terceros.

**Aquí había una frase falsa, y estuvo publicada.** Decía que «no hay ningún
campo donde se haya escrito cuál». Lo hay a medias: Facturae 3.2.2 tiene
`SpecialTaxableEvent/SpecialTaxableEventCode` a nivel de línea, con dos únicos
valores —`01` operación sujeta y exenta, `02` operación no sujeta—, que separan
**E** de **O**. Es opcional, así que puede no venir; y no dice nada de Z, K, G
ni AE, que siguen siendo indistinguibles. Pero cuando está, dice algo, y
nosotros afirmábamos que no existía sin haberlo mirado. Es el fallo de siempre:
**deducir una ausencia sin ir a ver**.

**Ya se lee.** `linea_fiscalidad_especial` en `sintaxis.py` y
`_categoria_de_las_lineas` en `iva.py`, con tres condiciones a la vez: que haya
líneas a tipo cero, que **todas** traigan el código y que **todas digan lo
mismo**. Si una sola calla, su cero puede ser una Z, una K o una G, y
atribuirle la categoría de sus vecinas sería el dedazo de siempre: se devuelve
`None` y vuelve a salir `IVA-CATEGORIA-A-CERO`.

Lo que fija `tests/test_fiscalidad_especial.py` no es el caso bonito sino el
borde —**basta una línea muda para que no se conteste**—, y se provocó dejando
la lectura sin efecto: caen las cuatro pruebas del caso que sí contesta y
ninguna de las otras cinco.

Lo que esto abre: las reglas BR-S-*, BR-IG-* y BR-IP-* ya corren de verdad
sobre facturas españolas, que antes no las miraba nadie.

### BT-3 y el país: traducir el vocabulario, y negarse cuando no se puede

Los dos huecos que quedaban del binding. Los dos son lo mismo: Facturae escribe
un dato **en su vocabulario** y EN 16931 lo pide en el suyo.

**El país.** Facturae lo escribe en tres letras (`ESP`) y la norma lo pide en
dos (`ES`). La tabla de `validador/paises.py` se construyó contrastando por los
dos extremos: los 235 códigos de `CountryType` del XSD oficial de Facturae
contra los 249 de la lista ISO 3166 que UN/CEFACT publica con los esquemas CII.
Resultado: **233 parejas y cero discrepancias**.

Los dos que no tienen pareja son `ANT` y `ZAR` —Antillas Neerlandesas y Zaire—,
que Facturae sigue admitiendo e ISO retiró. No se traducen: convertir `ZAR` en
`CD` sería decidir qué quiso decir quien escribió esa factura. Sale
`FE-PAIS-RETIRADO`.

Esto arregló de paso algo peor. `pais_emisor` devolvía `"ES"` para todo
Facturae **sin leer el país**, con el argumento de que es el formato nacional
español. Lo es, y su emisor no siempre lo es: a un proveedor extranjero que
factura a una administración española se le estaban aplicando las reglas CU-*
del RD 238/2026 sin mirar. Es la misma familia del fallo grande que abre
`HALLAZGOS.md`.

**El tipo de documento.** Aquí lo que uno esperaría está mal: `InvoiceDocumentType`
distingue factura completa de simplificada, que es otra pregunta, y su tercer
valor —AF, autofactura— **está en desuso** desde el RD 1789/2010. Lo que fija
BT-3 son otros dos campos:

| Lo escrito | BT-3 | Por qué |
|---|---|---|
| `InvoiceIssuerType` = RE | **389** | «self-billed invoice: an invoice the invoicee is producing instead of the seller» |
| `InvoiceClass` OO, OC, CO, CC | **380** | original, recapitulativa o copia siguen siendo factura ordinaria |
| `InvoiceClass` OR, CR | **según el método** | ver abajo |

Una rectificativa española es 384 (factura corregida) o 381 (abono) según cómo
rectifique, y eso lo dice `CorrectionMethod`. Aquí se dijo durante meses que su
lista de valores «no se ha podido contrastar contra fuente oficial», y era
falso: está en `CorrectionMethodType` del esquema `Facturaev3_2_2.xsd`, que
**este repositorio sirve dentro de `web/paquete.zip`**. Se buscó fuera, en un
PDF del Ministerio y en UNECE, y no se abrió lo que ya estaba dentro. Es el
mismo fallo que con la fiscalidad especial, dos secciones más arriba, y la
misma semana.

Con la lista delante, de los cuatro métodos **dos se traducen y dos no**:

| Método | Qué es | BT-3 | Por qué |
|---|---|---|---|
| `01` | rectificación íntegra | **384** | rehace la factura entera con los datos corregidos, que es la definición literal de 384: «revised information differing from an earlier submission of the same invoice» |
| `03` | descuento por volumen en un periodo | **381** | solo puede restar de lo ya facturado, y eso es un abono |
| `02` | por diferencias | **no se decide** | factura solo la diferencia, y si sube o baja no lo dice el método sino los importes. Sacarlo del signo sería deducir el tipo de una cuenta y no leerlo del documento |
| `04` | autorizada por la Agencia Tributaria | **no se decide** | dice quién la autorizó, no cómo rectifica |

Cuando se traduce **sale dicho con qué base**, en una `FE-TIPO-POR-METODO`:
la correspondencia sale de las definiciones del propio esquema de Facturae y
no de ningún mapa publicado —el anexo I del proyecto de orden no mencionaba
Facturae ni una vez, y la orden publicada el 05-10-2026 tampoco, ni en sus
artículos ni en sus anexos—. Cuando no, sigue saliendo
`FE-TIPO-SIN-EQUIVALENTE`, y ahora dice cuál de las dos razones es.

Y con la traducción puesta se pudo encender **BR-CL-01**: que el tipo salga de
la lista UNTDID 1001. Los 62 códigos admitidos se sacaron del esquematrón
oficial de la Comisión, no de memoria. Sobre 157 facturas de terceros salta
**una**, un EDIFACT cuyo BGM declara `220` —que es «pedido», no una factura—.

## La firma XAdES

En Facturae la firma no es un adorno. Lo dice el propio esquema, en la
anotación de su bloque `Signature`:

> «Se define como opcional para facilitar la verificación y el tránsito del
> fichero. No obstante, debe cumplimentarse este bloque de firma electrónica
> para que se considere una factura electrónica válida legalmente frente a
> terceros.»

### Y en UBL, CII y EDIFACT, la nota del art. 7.3

En esas tres sintaxis la firma no es parte del formato: se pone por fuera, en
el sobre del envío, y en EDIFACT no hay manera de llevarla dentro. Por eso a un
UBL sin firma no se le da `FIRMA-FALTA`, que sería inventarse un requisito que
la sintaxis no tiene. Pero el requisito existe, y lo pone el real decreto:

> "Todas las facturas electrónicas emitidas por medio de plataformas privadas
> de intercambio de facturas electrónicas deberán estar firmadas con firma
> electrónica avanzada, ya sea directamente por el emisor o mediante firma
> delegada autorizada [...]" (RD 238/2026, art. 7.3)

Desde el 21-10-2026, una factura española en UBL, CII o EDIFACT que no trae la
firma dentro lleva la **NOTA `FIRMA-POR-FUERA`**, con esa base. Es nota y no
aviso porque el fichero no dice las dos cosas que decidirían si falta: si pasó
por una plataforma privada (la solución pública y el envío directo entre dos
empresas no están en el artículo) y si la firma viaja aparte. Si la factura sí
trae la firma, la nota no sale y la firma se comprueba como se cuenta abajo. A
una factura extranjera no se le pone, porque el artículo es del real decreto,
ni a una respuesta (`ApplicationResponse`), porque no es una factura.

`firma.reglas` exige que quien la llama diga si el documento es español, sin
valor por defecto: callar por defecto dejaría sin la nota a todas las facturas
el día que alguien la llame sin pasarlo, y hablar por defecto se la pondría a
las extranjeras.

Lo que falta es el segundo paso: aceptar la firma en un fichero aparte, junto
a la factura, y comprobarla con lo que ya existe. Espera a que la Sede diga
cómo viaja; la orden solo dice que las facturas interconectadas "podrán
remitirse junto con la firma electrónica" (art. 3.6).

### Qué se comprueba

Todo esto sin salir a la red:

1. **Que nadie haya tocado el documento desde que se firmó.** Cada `Reference`
   de la firma lleva el resumen de un trozo del documento. Se canonicaliza ese
   trozo, se le rehace el resumen y se compara. Es solo *hash*: no hace falta
   ninguna clave, y es lo que caza el fallo más común de todos —alguien edita
   el XML después de firmarlo, o una herramienta lo vuelve a guardar y lo
   rompe—. Basta un espacio de más.
2. **Que la firma la hiciera la clave privada del certificado que se enseña.**
3. **Que lo que la firma cubre sea esta factura**, y no otra cosa.
4. **Que el certificado estuviera vigente** el día que la firma declara —fecha
   que se lee de lo firmado, no de cualquier parte del documento—.
5. **Que el certificado presentado sea el que XAdES dice haber usado.**
6. **Que los algoritmos no estén retirados.**
7. **Que el certificado sirva para firmar**, según lo que él mismo declara en
   su `keyUsage`. Uno de cifrado o de autenticación en web puede firmar un XML
   perfectamente; lo que dice esta comprobación es que quien lo emitió no lo
   emitió para eso (`FIRMA-USO-NO-PERMITIDO`, aviso).

La tercera y el inciso de la cuarta son del 15-09-2026 y salen de una
auditoría; el porqué está más abajo, en «Una firma auténtica sobre otra cosa».
La séptima es del 20-09-2026 y sale de la misma auditoría.

### Qué no, y por qué se dice

- **De quién es el certificado.** Exige la lista de confianza europea (TSL),
  que cambia y hay que descargar.
- **Si está revocado.** Exige OCSP o CRL, o sea red.
- **Los sellos de tiempo.** Sin ellos la fecha de firma la escribe quien firma;
  sirve para contrastarla con la vigencia del certificado, no para demostrar
  cuándo se firmó.

Traducido: responde **«¿ha cambiado alguien este documento después de
firmarlo?»** y **«¿es esta factura lo que se firmó?»**. No responde «¿de quién
es este certificado?». Un documento firmado con un certificado que el remitente
se ha inventado pasa las seis comprobaciones —de hecho es justo lo que hacen los
tests—, y por eso el informe dice lo que no mira:

```
No se comprueba de quién es el certificado ni si está anulado (sin
anclas de confianza no se sabe a qué autoridad llega, y sin eso no se
puede creer ninguna prueba de revocación), ni si lo que dice la
factura es cierto.
```

Hasta el 05-10-2026 decía que lo segundo necesitaba «salir a la red».
No: la prueba puede venir dentro del documento, y lo que falta sin
anclas es saber a quién creérsela.

Ese párrafo cambia solo cuando el lote trae firmas. Sobre uno sin firmar sería
explicar qué mitad de algo que no hay se comprueba.

Y cambia también **cuando alguna firma no se ha sabido comprobar**. La frase
decía «se ha comprobado que las firmas no estén rotas» aunque la única firma
del lote fuera una que nadie ha podido mirar: el documento lo decía en su línea
de estado y en su aviso, y la frase que resume el informe entero se lo callaba.
Ahora la promesa cuelga de haber comprobado alguna, y las que no se han sabido
mirar se cuentan al otro lado:

```
No se comprueba la firma de este documento —su aviso dice por qué—,
ni si lo que dice la factura es cierto.
```

El porqué no se repite ahí: son cuatro motivos distintos —un algoritmo que no
se conoce, una canonicalización que no se sabe reproducir, un `SignedInfo` que
no está en su sitio, un certificado ilegible— y cada documento lleva el suyo
escrito. Una firma que se ha mirado y está rota **sí** cuenta como comprobada:
ahí la promesa se cumple, y de que esté rota se queja el error.

Lo mismo con la cadena, desde el 16-09-2026. «Se ha comprobado que ese
certificado lleve a una autoridad de confianza» salía en cuanto había
anclas puestas, también con `CADENA-DESCONOCIDA` en el informe: un aviso, así
que el veredicto seguía siendo «sin errores» debajo de una frase que prometía
lo que el aviso negaba. Ahora se promete si **todas** las firmas que se
sostienen llegan a un ancla —se cuenta una nota de confianza por firma—, y los
documentos que no llegan van al otro lado: «no se comprueba de quién es el
certificado de este documento —su aviso dice por qué—».

Y con la revocación, desde el 05-10-2026. La promesa colgaba de un solo
interruptor, «¿hay alguna lista en la carpeta?», que no miraba lo que pasó
con cada documento. En la página, donde no hay carpeta, salía «No se
comprueba si el certificado está anulado (hace falta la lista de revocación
de su autoridad)» al lado de un `REVOCADO` sacado de la lista que traía la
propia factura; en consola, una lista de otra autoridad bastaba para
prometer la revocación de todo el lote. Ahora se cuenta por documento: se
promete cuando la cadena llega y ninguna firma lleva uno de los avisos de
`revocacion.SIN_CONTESTAR` (no se sabe del que firma, o solo con una lista
vencida), y los demás van al otro lado: «no se comprueba si está anulado el
certificado de este documento (su aviso dice por qué)».

Y el código único se promete solo donde se mira: en UBL, CII y Facturae. De un
EDIFACT no se saca, y la frase decía haberlo comprobado sobre dos copias
idénticas que salían «2 correctos». Con EDIFACT en el lote, ahora dice que el
suyo no se comprueba; y un lote en el que no se ha podido leer nada dice «no se
ha comprobado nada», que antes salía como «se ha comprobado el código único».

### Una firma auténtica sobre otra cosa

Las dos primeras comprobaciones —los resúmenes cuadran, el valor de la firma
cuadra— se pueden cumplir enteras **sobre otro documento**. Una firma XAdES
cualquiera, hecha por quien sea sobre lo que sea, se despega de su documento y
se cuelga de una factura inventada: si la referencia va por identificador y la
canonicalización es exclusiva —que es lo corriente—, lo que cubre viaja con
ella y sigue verificando. No hace falta ninguna clave privada: basta una firma
suya sobre cualquier cosa, y un certificado suyo lo hay en cada factura que
manda.

Hasta el 15-09-2026 eso salía **sin un solo error**, y con la nota que nombra al
firmante y a la autoridad que lo avala. Ahora se exige que alguna referencia
comprobada cubra la factura que se está leyendo, y si ninguna lo hace sale
`FIRMA-NO-CUBRE` en error.

La misma maniobra dentro de un solo fichero es el señuelo. En una firma
envolvente —la factura va dentro de un `ds:Object` al que la firma apunta por
identificador, que es como referencian su contenido 9 de las 24 firmas del
corpus— basta meter un `Facturae` inventado **delante** del que está firmado:
`formato.detectar`, `facturae.py` y
`en16931.py` se quedan con el primero, y la firma sigue cubriendo el segundo.
Por eso «cubrir» no es «tener una referencia que verifique», sino cubrir el
elemento que las reglas leen como factura.

Tres cosas más salieron del mismo sitio, y son la misma idea con tres caras:

- **Las referencias son las del `SignedInfo`, y solo esas.** Estaban cogidas de
  cualquier parte de la firma. Un resumen lo rehace cualquiera sin ninguna
  clave, así que bastaba colgar de un `ds:Object` una referencia al documento
  con su resumen bien calculado. Con el `SignedInfo` fuera de su sitio, además,
  no quedaba valor de firma que comprobar y el informe salía sin una sola queja
  de firma.
- **La fecha y el certificado declarados se leen de las propiedades firmadas.**
  `SigningTime` y `SigningCertificate` se buscaban con `.//` y mandaba el
  primero en orden de documento. Un `ds:Object` sin firmar metido delante del
  de verdad no rompe ningún resumen y decidía la fecha con la que se miden la
  caducidad del certificado y su revocación: un tercero que ni firmó borraba un
  `FIRMA-CADUCADA` del informe.
- **Un identificador repetido no se resuelve a ciegas.** Quedarse con el primer
  elemento que lleve ese `Id` es la maniobra clásica contra los verificadores de
  XML firmado. Ahora, si aparece más de uno, se dice que no se sabe cuál es el
  firmado en vez de elegir.

Y la puerta que lo ata todo: **`cadena.py` no dice de quién es un certificado
cuya firma no se ha comprobado.** Era el agujero de fondo. `firma.py` decía
correctamente «no se ha podido comprobar la firma» —con un método de firma
inventado basta— y `cadena.py`, que miraba por su cuenta, escribía igual «La
firma de Fulano llega a tal autoridad». Esa nota es la única frase del informe
que nombra a alguien. Ahora las dos preguntan a la misma función, `examinar`, y
la nota sale solo si la firma se sostiene: el valor cuadra, ninguna referencia
está alterada y alguna cubre la factura.

Y la última pieza, del 15-09-2026: **la línea de estado dice en qué quedó la
firma, no que haya una.** Decía «· firmado» por el mero hecho de traer un
bloque `Signature`, así que una factura falsificada —certificado ajeno copiado,
resúmenes rehechos, algoritmo de firma inventado para que nadie llegue a
comprobar el valor— se leía así:

```
Facturae v3.2.2 (factura) · firmado — sin errores, 2 aviso(s).
```

Ya no se nombraba a nadie y un aviso decía que la firma no se había podido
comprobar, pero encima de «sin errores» la palabra que se lleva quien lee es
«firmado». Ahora hay cuatro etiquetas y la diferencia entre las dos malas
importa:

| Cuándo | Qué dice |
|---|---|
| todas las firmas se sostienen | `· firmado` |
| se ha mirado y no se sostiene: el valor no cuadra, alguien tocó un trozo firmado, o lo que firma no es esta factura | `· firma que no se sostiene` |
| no se ha sabido mirar —un algoritmo que aquí no se conoce— | `· firma sin comprobar` |
| nadie la ha mirado: una detección a secas, sin validar | `· con firma` |

«Sin comprobar» y «no se sostiene» van aparte a propósito: hay algoritmos
legítimos fuera de la tabla —RSA-PSS, sin ir más lejos— y acusar a una firma
correcta de estar rota es el error simétrico del que se acaba de cerrar. Con
varias firmas manda la peor: que una cuadre no arregla que otra no.

El estado sale de los **mismos** exámenes con los que se escriben las glosas de
la firma, hechos una sola vez y pasados a las dos partes. Que cada uno mirara
por su cuenta es exactamente lo que dejó a `cadena.py` nombrando al firmante de
una firma sin comprobar; repetirlo en la línea de estado habría costado otra
pasada entera y habría permitido que la línea dijera una cosa y las glosas
otra.

Lo que cuesta, medido: 0,9 ms de examen en una factura de 3 KB y 160 ms en una
de 1 MB con 4.000 líneas; se hace tres veces por firma —el informe, la cadena y
los sellos— y sale a un 4 % del tiempo de validar la grande. No se guarda en
caché a propósito: una caché que no sepa cuándo el documento dejó de ser el
mismo es el fallo que este repositorio ya ha tenido cuatro veces.

Las 19 facturas firmadas del corpus dan exactamente el mismo informe que antes
del arreglo, código por código y campo por campo.

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

### La firma con curva elíptica

Este validador nació verificando solo RSA, y estaba dicho. Dejó de ser
aceptable con un dato concreto: **46 de las 129 autoridades cualificadas
concedidas de la lista española firman con curva elíptica**. Un tercio de las
autoridades de España se quedaba fuera del almacén, y sus facturas salían como
«no llega a ninguna autoridad conocida» sin que ese fuera el motivo real.

Ahora se verifican las tres curvas que aparecen de verdad en esa lista —P-256,
P-384 y P-521, sin ninguna brainpool— y el conjunto pasa de **87 a 133 anclas**.

Sigue sin haber dependencias nuevas. Una curva es aritmética de enteros módulo
un primo, igual que RSA; lo que cambia es que el grupo no son los números sino
los puntos de la curva, y hay que escribir la suma.

**Los parámetros van escritos a mano, y por eso se comprueban.** Una errata en
una de esas constantes no da un error: da «esta firma no verifica», que es
indistinguible de una firma falsificada. Se comprueba con la definición —que el
generador esté en la curva y que n·G sea el punto del infinito— y no es
ceremonia: al escribirlos se perdieron dos dígitos de la `n` de P-521 en un
corte de línea, y esa comprobación fue quien lo cazó, antes de escribir ni una
línea de ECDSA.

**Coordenadas jacobianas, y una prueba que las vigila.** En coordenadas
normales cada suma de puntos necesita un inverso modular, y una verificación
son cientos de sumas: P-521 tardaba 200 ms. En jacobianas —un solo inverso al
final— baja a 33, y con el truco de Shamir para hacer las dos multiplicaciones
a la vez. El precio es que las fórmulas no se leen solas; la defensa es que hay
una prueba que las contrasta contra la versión lenta y evidente, que sí se lee.

Medido dentro del navegador, que era la duda: **P-256 10 ms, P-384 16 ms,
P-521 29 ms**. Prácticamente lo mismo que fuera.

**Dos trampas que costaron su comprobación cada una:**

- **La firma viene en dos formatos distintos.** Dentro de un certificado o una
  CRL es DER —`SEQUENCE { r, s }`—; dentro de una firma XML son los dos números
  pegados y rellenos con ceros. Confundirlos no da un error de formato: daría
  una firma buena que no verifica, y hay una prueba que exige que cada
  codificación se rechace en el sitio de la otra.
- **El resumen hay que recortarlo.** Cuando el resumen es más largo que la
  curva —P-256 firmado con SHA-384, que existe— la norma manda quedarse con los
  bits de la izquierda. Quien no lo haga verifica mal exactamente esas. Hay un
  vector de `openssl` para ese caso concreto.

**Y la fuerza de la clave, que había que separar.** 256 bits de curva equivalen
a unos 3072 de RSA. Con un solo mínimo —los 2048 de RSA— toda clave de curva
saldría avisada por «corta», que es justo al revés de la realidad, y ahora que
son un tercio de las autoridades el informe se habría llenado de un aviso
falso.

**Cómo se prueba.** Con `openssl`, que es lo que saca esto del círculo: se le
pide una clave, un certificado autofirmado y una firma por cada curva, y se
verifican con la aritmética de aquí. Y una autoridad de curva entera —CA P-384
que emite una hoja P-256, la revoca y publica su CRL— para comprobar que
`cadena.py` encadena firmas ECDSA y que `revocacion.py` se cree una CRL firmada
con ECDSA, que son los dos sitios donde el despachador tenía que enterarse de
que la clave no es RSA.

## El sello de tiempo: quién pone la fecha

Hasta aquí la fecha de una firma salía de `SigningTime`, que **la escribe quien
firma**. No es un detalle de formato: es la bisagra de la que cuelgan las dos
comprobaciones más caras de todo el validador.

- La **vigencia** del certificado se mide contra esa fecha.
- La **revocación** también: «se anuló el 3 de marzo» solo dice algo si se sabe
  si la factura es de antes o de después.

Con la fecha en manos del firmante las dos se esquivan a la vez y con el mismo
gesto: fechar hacia atrás. Un certificado caducado o anulado ayer firma hoy una
factura que dice ser del año pasado, y las dos reglas la dan por buena.

Un sello de tiempo cierra eso. Una autoridad de sellado —una TSA— firma «he
visto estos bytes en este instante». Los bytes que ve son el `SignatureValue`,
que no se puede fabricar sin la clave privada; así que el sello demuestra que
**la firma ya existía** entonces. La fecha deja de ser una afirmación del
interesado y pasa a ser el testimonio de otro.

### Lo que se comprueba

Un sello es un `TimeStampToken` de RFC 3161: un CMS `SignedData` con un
`TSTInfo` dentro, metido en las propiedades XAdES que la firma **no** cubre
—que es lo que permite sellar después de firmar—.

1. Que lo que la autoridad firmó sea **este** sello y no otro. El atributo
   `messageDigest`, que va dentro de lo firmado, tiene que ser el resumen del
   `TSTInfo` que trae el documento.
2. Que la firma de la autoridad cuadre con su certificado.
3. Que el certificado del sello sea el que la autoridad dice haber usado
   (`signingCertificate`, lo mismo que XAdES hace por fuera).
4. Que ese certificado **esté autorizado a sellar el tiempo**.
5. Que el sello sea **de esta firma**: su resumen tiene que ser el del
   `ds:SignatureValue` canonicalizado.

Y con la fecha ya acreditada, dos cosas que antes no se podían ni mirar: que el
sello no sea anterior a la emisión del certificado —imposible— y que no sea
posterior a su caducidad —posible, pero entonces nada acredita que la firma se
hiciera mientras el certificado valía—.

### La comprobación que no es criptografía, y es la que más pesa

La cuarta. RFC 3161 lo pide con una rotundidad rara en una norma: la extensión
de uso extendido tiene que estar, tiene que llevar `id-kp-timeStamping` y **no
puede llevar nada más**. Sin eso, cualquiera con un certificado de firma
corriente se fabrica los sellos que quiera, y la fecha vuelve a ser suya.

Que la norma sea estricta no la hace realista, así que se contrastó contra la
lista española. De los **69 certificados de sellado concedidos**, 60 son
certificados de firma —los que de verdad sellan— y **los 60 llevan la
extensión, con ese uso y solo ese**. Los otros nueve son autoridades de
certificación, que no sellan nada: son los emisores, y ahí la regla no aplica
(seis la llevan igual y tres no).

Hay un vector de prueba dedicado a esto, y es el más importante de los dos: un
sello **perfectamente firmado**, cuya firma verifica y cuyo resumen cubre lo
que dice cubrir, emitido por un certificado que no está autorizado a sellar. Se
rechaza. Si un día alguien afloja esa comprobación, esa es la única prueba que
se pone roja —y la misma comprobación está marcada como crítica en el
navegador, porque es de sobre-confianza y esas no avisan solas—.

### Dos trampas que solo se ven probando

Las dos salieron de contrastar el código contra un sello hecho con `openssl`,
no de leer la norma:

- **La firma no va sobre los atributos tal y como vienen.** En el DER los
  atributos firmados llevan la etiqueta `[0]`; lo que se firma es esa misma
  secuencia **reetiquetada como `SET OF`**. Verificar sobre los bytes tal cual
  falla en todos los sellos del mundo, que es un fallo ruidoso y por tanto
  benigno; hay una prueba que exige que la forma ingenua **no** verifique.
- **El algoritmo de resumen no sale de donde parece.** El `signatureAlgorithm`
  del firmante suele ser `rsaEncryption` a secas, sin decir con qué resumen. El
  bueno es el `digestAlgorithm`, que va aparte.

Y una tercera que costó encontrar porque falla en silencio hacia el lado malo:
**el resumen por defecto del certificado no es el mismo en las dos versiones
del atributo**. En `SigningCertificate` es SHA-1 siempre; en
`SigningCertificateV2`, SHA-256. Escribir un único valor por defecto —lo
natural— hace que la comprobación del certificado no case en ningún sello
moderno, que es exactamente donde hace falta.

Cuando cuadra, sale así:

```
[SELLO-TIEMPO · Firma electrónica] La firma lleva un sello de tiempo de «TSU de
prueba» del 27-08-2026 a las 22:32:13 UTC, con una precisión de ±1 s 500 ms
100 µs, y el sello cuadra: esa autoridad vio esta firma ese día, así que la
firma ya existía entonces. Esa es la fecha que se usa para la vigencia y la
revocación, en vez de la que declara quien firma. Lo que todavía no se
comprueba es quién es esa autoridad: que el sello sea coherente no dice que
esté en la lista de confianza del Estado.
```

### La fecha acreditada gana, y se nota en el veredicto

Leer el sello no arregla nada por sí solo. Lo que arregla el agujero es que la
fecha del sello **sustituya** a la declarada en todo lo que cuelga de ella, y
eso cambia resultados:

```
[REVOCACION-POSTERIOR · Firma electrónica] El certificado que firma se anuló el
02-03-2026, después del 01-01-2026 en que el sello de tiempo de «TSU de prueba»
acredita que esta firma ya existía. La factura se firmó cuando el certificado
aún valía, y eso no depende de lo que declare quien firma.
```

Ese mismo caso, sin sello, es un **aviso** que acaba diciendo «esa fecha la
escribe quien firma: sin un sello de tiempo de un tercero no hay forma de
comprobarla». Con sello es una **nota**: ya no hay nada de que avisar, solo que
declarar en qué se ha confiado. El hecho es el mismo; lo que cambia es quién
responde por la fecha.

Al revés también: una anulación anterior al sello sigue siendo un error, y
ahora lo dice sin rodeos —«estaba ya anulado cuando el sello acredita que ya
existía esta firma»—, que es una acusación que antes no se podía sostener.

### Cuando no hay sello, se dice

```
[SELLO-FALTA · Firma electrónica] La firma no lleva sello de tiempo de un
tercero. La fecha que se ha usado para comprobar la vigencia del certificado y
la revocación es la que declara quien firma, el 02-03-2026: quien firma puede
escribir la que quiera, y fechando hacia atrás se esquivan las dos
comprobaciones a la vez.
```

Ninguna de las muestras del Gobierno lleva sello de origen, así que esta nota
es lo que sale en la práctica con lo que se descarga de `facturae.gob.es`. Es la misma política que con las anclas: **una
decisión tomada por otro solo es aceptable si se declara**.

### De quién es la autoridad que sella

Que el sello cuadre no dice quién lo puso. Es la otra mitad, y el reparto es el
mismo que con la firma: `sellos.py` dice que el sello se sostiene, `cadena.py`
dice de quién es. Primero que cuadre, después de quién es.

La fuente es la misma lista del Estado, que publica **69 servicios de sellado
concedidos**. Se montan con la misma orden y en el mismo momento que las otras,
porque salen de la misma lista:

```
Montadas 133 anclas en anclas.
  de 243 servicios: 129 concedidos, 114 retirados (fuera), 0 sin certificado (fuera).

Montadas 69 anclas de sellado en anclas-sellos.
  de 120 servicios de sellado: 69 concedidos, 51 retirados (aparte).
  van en otra carpeta a propósito: una autoridad cualificada solo para sellar
  el tiempo no avala la firma de una factura.
```

Y cuando la autoridad se reconoce, se declara igual que con las anclas de
firma:

```
[SELLO-CONFIANZA · Firma electrónica] La fecha la acredita «TSU de prueba», que
está publicada como autoridad de sellado en la lista de confianza del Estado:
de la lista de confianza de ES, publicada por MINISTERIO DE ASUNTOS ECONOMICOS
Y TRANSFORMACION DIGITAL el 06-08-2026.
```

Cuando no:

```
[SELLO-TSA-DESCONOCIDA · Firma electrónica] El sello de tiempo de «TSU de
prueba» cuadra, pero esa autoridad no llega a ninguna de las de sellado que hay
instaladas: la cadena se queda en «AC de sellos de prueba», que no está entre
ellas. El sello es coherente; lo que no consta es que quien lo firmó sea una
autoridad de sellado cualificada.
```

Y cuando no hay ninguna instalada, se dice eso y no se calla, que es la misma
política que con las anclas de firma:

```
[SELLO-SIN-CONTRASTAR · Firma electrónica] El sello de tiempo de «TSU de
prueba» cuadra, pero no hay anclas de sellado instaladas, así que no se ha
comprobado que sea una autoridad cualificada. Un sello se puede fabricar
entero, autoridad incluida, y este pasaría igual: la fecha vale lo que valga
esa autoridad, y de eso aquí no consta nada.
```

### Dos carpetas, y por qué no una

`anclas/` y `anclas-sellos/`, hermanas y no una dentro de otra. Es la misma
lección de las retiradas —**ampliar el conjunto no debe ampliar la
confianza**— aplicada a otra cosa.

Los números lo dicen mejor que el argumento. De las 121 anclas de sellado que
salen de la lista española, **solo 2 están también entre las de firma**. Las
otras 119 son autoridades que el Estado tiene por cualificadas para sellar el
tiempo y **no** para avalar la firma de una factura, y **once de ellas son
autoridades de certificación**: juntando las carpetas, esas once pasarían a
poder emitir certificados que el validador aceptaría como firmantes de
facturas. Nadie lo habría decidido y nada lo diría.

Que sean hermanas y no una dentro de la otra tiene un motivo concreto: el
almacén recorre su carpeta entera con `rglob`, así que un subdirectorio se
leería como anclas de firma. Puestas al lado, el error posible es el contrario
—olvidarse de copiar la carpeta—, y entonces no se reconoce ninguna autoridad
de sellado y **se dice**. Ese es el lado por el que hay que fallar.

El almacén encuentra a su hermana solo, así que no hay que acordarse de nada:
`anclas/` busca `anclas-sellos/` al lado, o donde diga `FACTURAE_ANCLAS_SELLOS`.

### Pasado por sellos de verdad

Las pruebas de arriba las escribe el mismo que escribió el código. Lo que dice
si el módulo sirve es otra cosa: **tokens que no ha hecho este proyecto**.

**Facturae con sello no hay publicadas.** Una factura sellada lleva datos
reales de una empresa real, así que nadie las sube; en el índice de código de
GitHub no aparece ninguna. Así que se hicieron dos cosas.

**Una: sellos españoles de verdad, aunque no sean de facturas.** El repositorio
del cliente de firma oficial del Estado —`clienteafirma`— trae documentos
XAdES-XL y XAdES-A firmados de verdad, con sellos de «Sello de tiempo TS@ -
@firma», la autoridad de sellado del Estado, entre 2015 y 2019. Son **18
tokens**: los 18 se leen y los 18 verifican, con su cadena, sus OCSP y sus CRL
dentro.

**Dos: una factura española de verdad con un sello cualificado de verdad.** A
las facturas firmadas oficiales de `facturae.gob.es` se les pidió un sello a la
TSA pública de la **ACCV** —la Generalitat Valenciana, que está en la lista de
confianza del Estado—. El sello es real y cualificado, y la factura no sale del
ordenador: a una TSA se le mandan 59 bytes con el resumen del valor de la
firma, que es exactamente para lo que existe.

Y entonces el camino entero, sobre una factura del Gobierno de 2007:

```
[SELLO-TIEMPO · Firma electrónica] La firma lleva un sello de tiempo de «TSA1
ACCV 2016» del 27-08-2026 a las 23:53:44 UTC, con una precisión de ±0 s 500 ms
1 µs, y el sello cuadra: esa autoridad vio esta firma ese día, así que la firma
ya existía entonces. Esa es la fecha que se usa para la vigencia y la
revocación, en vez de la que declara quien firma.

[SELLO-CONFIANZA · Firma electrónica] La fecha la acredita «TSA1 ACCV 2016»,
que está publicada como autoridad de sellado en la lista de confianza del
Estado: de la lista de confianza de ES, publicada por MINISTERIO DE ASUNTOS
ECONOMICOS Y TRANSFORMACION DIGITAL el 06-08-2026.

[SELLO-DESPUES-DE-CADUCAR · Firma electrónica] El certificado (Usuario ejemplo
FacturaE) caducó el 10-12-2008, y lo único que hay acreditado de esta firma es
que ya existía el 27-08-2026, después. …
```

La última es correcta y conviene entenderla: son facturas de 2007-2009 selladas
hoy, así que lo único acreditado de esas firmas es posterior a la caducidad de
sus certificados. El aviso dice justo eso.

### Dos defectos que solo enseñó el fichero real

Los dos de la clase que no avisa sola.

**Un sello que no sabemos leer se daba por un sello que no está.** XAdES admite
el token de dos formas: en base64 —`EncapsulatedTimeStamp`, la que se usa— y el
mismo sello escrito como XML. Solo se lee la primera, que está bien; lo que no
estaba bien es que la segunda se ignorara **en silencio**. Sobre
`XAdES-XL_con_sello_xml.xml`, un documento con tres sellos del Estado dentro,
el informe decía «La firma no lleva sello de tiempo de un tercero».

**Y de ahí colgaba uno peor.** La misma frase salía con *cualquier* sello
inservible: roto, ilegible o copiado de otro documento. Las dos situaciones
acaban en la misma fecha —la que declara quien firma— pero no son la misma
noticia: a un documento sin sello hay que ponerle uno; a uno que ya lo lleva,
decirle que no lo lleva manda a poner dos veces lo mismo. Ahora son
`SELLO-FALTA` y `SELLO-SIN-USAR`, y hay una prueba de cada una que exige que la
otra no salga.

### Y una confirmación que vale más que el argumento

El sello de @firma lo firma un certificado que emite «DEFENSA-EC-WPG2016». Esa
autoridad **sí está entre las anclas de firma y no entre las de sellado**: el
Estado la publica para emitir certificados, no para sellar el tiempo.

Con las carpetas separadas, el validador dice la verdad —no consta que sea una
autoridad de sellado cualificada—. Juntándolas, encadena, y afirmaría que lo
es. No es un caso de laboratorio: pasa con un fichero del cliente de firma
oficial del Estado. Es la razón de que `anclas/` y `anclas-sellos/` sean
carpetas distintas, vista en un documento real, y hay una prueba que la fija en
las dos direcciones.

### Cómo se prueba sin ningún sello real

Ninguna muestra trae uno, así que el círculo se rompe igual que con las curvas:
**el sello no lo fabrica este código**. Los vectores los hizo `openssl`, y el
bueno está sellado sobre el `SignatureValue` exacto del documento de pruebas
—determinista— canonicalizado por lxml. Los bytes que la autoridad selló no los
eligió este módulo: los eligió la norma, los serializó lxml y los resumió
`openssl`.

Van escritos en el fichero de pruebas para que corran sin `openssl` instalado y
dentro del navegador. Las que necesitan sellar bytes a medida —las que cruzan
la fecha del sello con otra cosa— montan una autoridad entera con `openssl` y
se saltan solas cuando no está.

## Las anclas de confianza

`firma.py` responde «este documento no se ha tocado y la firma cuadra con el
certificado que trae dentro». Falta lo otro: **de quién es ese certificado**.
Sin eso, un documento firmado con un certificado que el propio remitente se ha
inventado pasa todas las comprobaciones.

`cadena.py` lo responde encadenando: el certificado de la factura lo emitió
otro, y ese otro lo emitió otro, hasta llegar a uno que ya conocemos. Los que
conocemos son las **anclas de confianza**.

### Esto no necesita red, y esa es la idea

Un ancla no se consulta: se conoce. El navegador no llama a nadie para saber
qué es una autoridad raíz; las lleva dentro. El sistema operativo, igual.

Así que las anclas se instalan en una carpeta —como los esquemas XSD— y a
partir de ahí encadenar es aritmética local: la misma verificación RSA que ya
estaba escrita, aplicada hacia arriba. **La promesa de que la factura no sale
del ordenador queda intacta.**

```bash
factura-e facturas/ --anclas anclas/
```

Por defecto busca en `./anclas` o en la variable `FACTURAE_ANCLAS`. Lee `.cer`,
`.crt`, `.der` y `.pem`, y un `.pem` con varios certificados dentro.

### Por qué no vienen en el repositorio

Porque meter un certificado raíz en el paquete es una decisión de seguridad, no
de comodidad: **quien controle ese fichero controla a quién cree el
validador.** Bajarlos «como sea» y hornearlos dentro sería crear justo el
problema que este módulo viene a resolver.

Se instalan a mano, y el validador enseña la huella de cada uno para poder
contrastarla con la que publica su autoridad:

```bash
factura-e --ver-anclas
```

```
Anclas de confianza en anclas:

  Talleres Ejemplo SL
    SHA-256  85:71:67:71:3B:24:89:78:09:D5:C5:4D:4C:49:64:1C:53:73:C6:15:A8:14:83:E6:A9:1F:F1:B1:CA:9C:3E:89

Contrasta cada huella con la que publica su autoridad antes de fiarte de ella.
```

Esa de ahí arriba es la del certificado de juguete de `ejemplos/fe-0001.xml`,
que es lo que hay a mano para enseñar el formato. **No se copian huellas de
aquí ni de ningún sitio que no sea la propia autoridad**: el sentido de la
huella es cortar la cadena de «me fío de quien me lo pasó», y una huella
copiada de un README la reanuda.

No hay que fiarse de por dónde llegó el fichero: se comprueba.

### Cómo se mantienen al día

No hay que suscribirse a nada, y no conviene. **Un almacén de confianza que se
actualiza solo por la red es un almacén con mando a distancia**: quien pueda
servirte ese fichero decide en quién crees. Los navegadores no lo hacen así
—las raíces les llegan dentro de una actualización firmada del sistema—, y aquí
tampoco.

Lo que sí hace falta es saber **cuándo hay que tocarlo**, y para eso hay tres
mecanismos, ninguno de ellos una descarga automática:

1. **La caducidad, que es lo único que se apaga solo.** Una raíz dura veinte o
   treinta años; una intermedia, cinco o diez. `--ver-anclas` dice cuándo
   caduca cada una y avisa de las que están a menos de 90 días o ya vencidas.

   ```
     Raiz de pruebas
       SHA-256  7B:52:69:B5:…  (aquí sale entera; se corta para no invitar a copiarla)
       caduca   2027-03-02  (quedan 46 días)

   Hay 1 ancla(s) caducada(s) o a punto: consigue la nueva en la web de su
   autoridad y comprueba su huella allí mismo.
   ```

2. **Lo que te falta te lo dicen tus propias facturas.** Cuando una cadena no
   llega, el informe nombra a la autoridad que falta: *«no tenemos el
   certificado de «AC DNIE 001»»*. Se instala lo que hace falta para lo que de
   verdad recibes, no un paquete entero de raíces del mundo por si acaso.
   Cuantas menos anclas, menos gente en la que estás confiando.

3. **La huella, para comprobar lo que instalas.** Cada vez que se añade o
   renueva un ancla, se contrasta su SHA-256 con la que publica su autoridad.
   Es lo que corta la cadena de «me fío de quien me lo pasó».

Para instalar muchas de golpe —recibir facturas de cualquiera, sin saber de
antemano de qué autoridad— el catálogo con autoridad para esto en la UE es la
**lista de confianza (TSL)** que publica cada Estado miembro, y ya se lee: ver
«La lista de confianza» más abajo. Sigue siendo un catálogo que se baja a mano
y se verifica, no un canal de actualización.

En la práctica: media hora dos veces al año, y cuando el validador te lo pida.

### El informe dice en qué ha confiado

Hasta aquí este validador solo sabía hablar de lo que está mal, y el silencio
hacía de aprobado. Con las anclas eso deja de valer: **que una firma llegue a
una autoridad no es la ausencia de un problema, es una decisión** —creerle a esa
autoridad— y quien la toma no es quien lee el informe.

Así que hay un tercer nivel además de error y aviso: la **nota**, que dice lo
que se ha dado por bueno y con qué.

```
[CONFIANZA-ANCLA · Firma electrónica] La firma de «Talleres Paco SL» llega a
«CA intermedia» en 2 eslabones. Esta validación se fía de esa autoridad porque
es un ancla instalada en anclas/intermedia.cer, con huella SHA-256
EE:CA:8D:AA:…

[CONFIANZA-REVOCACION · Firma electrónica] No consta anulado ningún
certificado de la cadena: se ha comprobado 1 certificado contra la lista de
«CA intermedia», publicada el 18-09-2026. Una lista solo responde por lo que
se sabía el día que se publicó.
```

La huella entera va a propósito, aunque ocupe: **es lo que hace la validación
reproducible.** Quien guarde ese informe puede demostrar años después contra
qué se contrastó, que es lo que pide una inspección y lo que ninguna captura de
un tic verde puede dar. Con `--solo-errores` desaparecen, como los avisos.

Y si las anclas no las instaló quien valida, la ruta de un fichero no le dice
nada. Quien distribuya un conjunto de anclas declara su procedencia y manda esa:

```python
Almacen(carpeta, procedencia="viene con esta página")
```

Es la condición que hace aceptable traer anclas puestas en una distribución:
**la decisión se toma por quien lee, así que hay que decírsela.** Traerlas y
callarlo sería fabricar confianza en silencio, que es justo lo que este
validador existe para no hacer.

### Los cinco fallos clásicos, y dónde se paran

1. **`basicConstraints`.** Un certificado que no es de autoridad no puede haber
   emitido a otro. Los validadores que no lo miraban —que fueron muchos y
   grandes— dejaban que cualquiera con un certificado normal emitiera
   certificados a nombre de quien quisiera. Es `ERROR`.

   Y **tampoco vale el que no dice nada**. La extensión es opcional: un
   certificado puede traerla diciendo «no soy autoridad» o no traerla en
   absoluto, y aquí solo se miraba el primer caso. Con eso, un certificado sin
   extensiones —o con un `keyUsage` puesto a mano— hacía de eslabón y la cadena
   subía por él hasta una raíz de verdad. Lo encontró la auditoría del
   15-09-2026; desde el 20-09-2026 un eslabón tiene que **declararse**
   autoridad.
2. **Encadenar solo por el nombre.** Que el emisor declarado coincida con el
   sujeto del siguiente no prueba nada: los nombres los escribe quien hace el
   certificado. Cada eslabón se **verifica criptográficamente**.
3. **Una raíz falsa con el nombre de una buena.** El almacén compara **byte a
   byte**, no por sujeto.
4. **Una extensión crítica que no se entiende.** En X.509, «crítica» quiere
   decir exactamente esto: quien no sepa aplicarla no puede dar el certificado
   por bueno. La que importa es `nameConstraints`, que limita a qué nombres
   puede emitir una autoridad —saltársela es aceptar certificados que esa
   autoridad no tenía derecho a emitir—. Aplicarla de verdad no está hecho, así
   que la cadena **no llega** y se dice por qué, en vez de afirmar que llega.
5. **Firmar con un certificado que no es para firmar.** El `keyUsage` del que
   firma el documento —no el del que emite certificados— tiene que traer
   `digitalSignature` o `contentCommitment`. Si declara otros usos y ninguno de
   esos dos, sale `FIRMA-USO-NO-PERMITIDO`, y es **aviso**: la firma puede
   cuadrar, lo que no cuadra es para qué se emitió ese certificado. Si no
   declara ninguno, no se dice nada: en X.509 eso significa «sin restricción».

Las tres primeras van sobre cualquier eslabón **menos el ancla**, y eso es
deliberado: un ancla no es un hallazgo, es la decisión de quien montó el
almacén, y X.509 tampoco procesa sus extensiones. Exigírselas dejaría fuera
raíces viejas sin extensiones y dos de las 268 anclas instaladas aquí, que
traen una crítica que este validador no lee. Lo que viaja **dentro del
documento** lo elige quien firma: ahí no se afloja nada.

Cada una de estas defensas tiene un test que se pone rojo al quitarla:
comprobado desactivándolas una por una.

### Lo que sale cuando no llega

```
[CADENA-DESCONOCIDA · Firma electrónica] El certificado que firma no lleva a
ninguna autoridad conocida: no tenemos el certificado de «AC DNIE 001». Puede
ser que falte un certificado en el almacén, o que no lo emitiera nadie de
fiar. No es lo mismo y desde aquí no se distingue.
```

Es **aviso, no error**, y la distinción importa: «no lo reconozco» no es «es
falso». Hacerlo error llenaría de acusaciones falsas a quien tenga el almacén
incompleto —que al principio es todo el mundo—. El mensaje nombra la autoridad
que falta, que es lo accionable.

Lo que sí es error es una cadena **mal formada**: una hoja emitiendo
certificados, o un eslabón cuya firma no verifica. Eso no es desconocimiento,
es que algo está mal.

### Un dato práctico

Ninguna de las nueve muestras del Gobierno trae sus certificados intermedios:
solo el de quien firma. Así que para encadenar de verdad hay que instalar la
raíz **y** los intermedios, no solo la raíz. Es el caso normal, no el raro.

### Quién avisa de que hay que renovarlas

De que las anclas vencen avisaban tres cosas, y ninguna avisaba a quien tiene
que arreglarlo:

| Quién | Cuándo | A quién |
|---|---|---|
| `--montar-anclas` y `--empaquetar` | 90 días antes, por pantalla | a quien los ejecute |
| `--empaquetar` | el día después: **se niega**, `SinRenovar` | a quien lo ejecute |
| El informe y la página | el día después, en cada visita | **a quien entra** |

El paquete está montado y versionado, así que no hay ningún motivo para volver
a ejecutar nada: el día que venzan, **el sitio se lo dice a quien lo visita
antes que a quien lo mantiene**, y la suite sigue verde, y el gancho de empujar
deja publicar tan tranquilo. El reparto de papeles al revés.

`tests/test_anclas_al_dia.py` lo pone del derecho. Mira lo único que de verdad
está publicado —`web/PAQUETE.json`, que se versiona a propósito— y compara su
`siguiente` con el día de hoy: **en rojo pasada la fecha**, y con aviso de
pytest desde los 90 días, el mismo margen que usan las dos órdenes. En rojo
significa que el gancho de `git push` no deja publicar, que es donde hacía
falta que apareciera.

Y no se pone en rojo antes de tiempo a propósito: una fecha que se acerca es un
recordatorio, y bloquear los empujes con un mes por delante sólo enseña a
saltarse el gancho.

Hay una segunda prueba, y es la que sostiene a la primera: si el manifiesto se
queda sin el campo `siguiente` —porque la lista del Estado deje de decirlo o
porque alguien lo quite al tocar el formato—, la de arriba se salta sola con un
`skip` **verde**. Provocado: quitando el campo, la primera dice «skipped» y la
segunda se pone en rojo.

Lo que esto **no** hace, también a propósito: no rompe el despliegue. Vercel
monta con `--sitio --exigir-paquete`, y negarse ahí dejaría en pie el despliegue
anterior —con el mismo paquete vencido— y de paso bloquearía cualquier arreglo
que no tenga que ver. La página ya dice la verdad sobre sus anclas cuando
vencen; lo que faltaba era que se enterara su autor.

## La revocación

Es la última pregunta de la firma y la única que un certificado no puede
contestar sobre sí mismo: **si lo anularon antes de usarlo**. Un certificado no
sabe que ha muerto. Lleva su fecha de caducidad dentro, pero no lleva —no puede
llevar— la noticia de que su titular perdió la clave el mes pasado.

```bash
factura-e facturas/ --anclas anclas/ --revocaciones revocaciones/
```

Por defecto busca en `./revocaciones` o en la variable
`FACTURAE_REVOCACIONES`. Lee `.crl`, `.der` y `.pem`.

### Este paquete no abre ni una conexión

Y se puede comprobar con un `grep`. Las pruebas de revocación salen de dos
sitios, los dos locales:

1. **De dentro del documento.** XAdES-XL guarda las listas del momento en que
   se firmó, que es lo que la norma inventó para poder comprobar una firma
   dentro de veinte años, cuando la autoridad que la emitió ya no exista. Se
   leen y se usan.
2. **De una carpeta**, como los esquemas y las anclas. Solo en consola.

Bajar una lista es un acto explícito de quien usa la herramienta. Lo que hace
el validador es decir **cuál le falta y dónde dice el propio certificado que
está**:

```
[REVOCACION-SIN-COMPROBAR · Firma electrónica] No se ha comprobado si el
certificado está anulado: no hay ninguna lista de esa autoridad. El propio
certificado dice que su lista está en http://…/crl.crl; bájala y ponla en la
carpeta de revocaciones.
```

### En la página, solo la prueba que trae la factura

En la página no hay carpeta ni forma de poner una lista, y hasta el
05-10-2026 el aviso de arriba salía igual: mandaba a hacer algo imposible, y
la portada prometía la revocación «si el documento trae la prueba o la tienes
instalada». Ahora la página arma su almacén de listas con
`AlmacenDeListas.sin_carpeta()`, y el aviso cuenta lo que pasó de verdad, sin
mandar a ninguna parte:

```
No se ha comprobado si el certificado está anulado: el documento no trae
dentro la lista de revocación de la autoridad que emitió el certificado, ni
una respuesta OCSP, y aquí no se sale a buscarlas.
```

Los otros dos casos ya llevaban su motivo: la lista que trae es anterior a la
firma («se publicó el …, 1 hora antes de la fecha de la firma, así que no pudo
enterarse de una anulación posterior»), o el respondedor OCSP contestó
«unknown». Se decidió así, la opción A del informe del 05-10-2026, porque es
lo mismo que se hizo con los esquemas: decir lo que trae la página y no lo que
podría traer. Dejar soltar un `.crl` junto a la factura (la B) queda para
cuando alguien lo pida; bajarla el navegador por su cuenta rompería «dominios
de terceros: 0», y repartir listas con la página sería un visto bueno sacado
de una foto vieja.

### Por qué CRL y no OCSP

Las dos contestan lo mismo y filtran cosas muy distintas.

Una **CRL** es la lista entera de anulados de una autoridad. Al bajarla no
dices qué certificado te interesa: los pides todos.

Una consulta **OCSP** lleva dentro el número de serie. Le dice a la autoridad
exactamente qué certificado estás mirando y a qué hora: o sea, de qué factura
se trata y cuándo te llegó. Para un validador cuya promesa es que la factura no
sale de tu ordenador, la diferencia no es un detalle.

Y no es teórico. De las cinco facturas firmadas de muestra, **cuatro apuntan a
una CRL y la firmada con DNIe no publica CRL ninguna**: solo OCSP. Con ese
certificado no hay forma de comprobar la revocación sin decirle al emisor qué
estás mirando. Se dice, y que elija quien valida:

```
[REVOCACION-SOLO-OCSP · Firma electrónica] No se ha comprobado si el
certificado está anulado: su autoridad no publica lista de revocación, solo un
servicio de consulta (http://ocsp.dnie.es). Preguntarle lleva dentro el número
de serie del certificado, o sea que le diría a la autoridad qué factura se está
mirando y cuándo. Esa consulta no se hace desde aquí.
```

### Y la respuesta OCSP que ya viene dentro, que sí se lee

Preguntar es una cosa. **Leer la respuesta que el documento ya trae** es la
contraria: no abre ninguna conexión, no le cuenta nada a nadie, y aprovecha
algo que el firmante metió ahí justamente para que se pudiera comprobar sin
red. Un XAdES-XL moderno guarda OCSP y muchas veces no guarda CRL, así que sin
esto la revocación de esos documentos no se comprobaba nunca.

Que la traiga quien firma no la hace de fiar, y ahí está el trabajo: la mete él,
así que sin verificarla cualquiera adjunta un «este certificado está
perfectamente» escrito por sí mismo. Se le exigen tres cosas —las mismas que a
una lista—: que el `CertID` cuadre con este certificado y su emisor, que la
firme la autoridad o un respondedor con `id-kp-OCSPSigning` **emitido por ella
de verdad**, y que la firma cuadre. Si falla una, la respuesta no se usa y se
dice cuál falló.

**Y el hueco de los 27 segundos.** Un XAdES-XL se construye preguntando el
estado, firmando y sellando, por ese orden: la respuesta es *anterior* a la
firma casi siempre. Medido sobre los seis documentos de muestra que traen OCSP,
el hueco va de 27 segundos a poco más de una hora. Tratarlo como «no se sabe»
levantaría el aviso en prácticamente toda factura archivada, y un aviso que
sale siempre deja de leerse.

Quien dice si la respuesta seguía valiendo en el momento de firmar no es este
validador: es el respondedor, con su `nextUpdate`. Si lo cubre, se acepta y la
nota dice el hueco y en qué se apoya. Si el respondedor no dijo hasta cuándo
valía —su manera de pedir que no se guarde— o dijo que ya no, se sigue sin
saber:

```
[CONFIANZA-REVOCACION · Firma electrónica] No consta anulado ningún certificado
de la cadena: se ha comprobado 1 certificado contra la respuesta OCSP de
«Servidor de OCSP - Fabrica Nacional de Moneda y Timbre Q2826004J» que trae el
propio documento, del 16-12-2015 a las 14:41:55 UTC (mirada 27 segundos antes
de la firma, y el propio respondedor la daba por vigente hasta el 16-12-2015 a
las 18:42:22 UTC). Una respuesta OCSP dice cómo estaba el certificado el día y la
hora en que se miró, no cómo está hoy.
```

Cuando la respuesta que trae el documento no sirve, se dice cuál era el
problema en vez de dejarlo en un «no se ha comprobado» genérico:

```
[REVOCACION-OCSP-NO-VALE · Firma electrónica] El documento trae dentro 4
respuestas OCSP, y con ellas no se ha podido comprobar si el certificado estaba
anulado: el respondedor contestó que no sabe nada de ese certificado
(«unknown»), que no es lo mismo que decir que está bien.
```

La lista (CRL) se queda más estricta a propósito: una publicada antes de la
firma no cuenta, aunque su plazo llegue. La ventana de una respuesta OCSP se
mide en horas y la de una lista en días o semanas, así que aplicar allí el
mismo argumento se tragaría un plazo mucho mayor. Queda dicho, que es distinto
de quedar escondido.

### El problema de las fechas, que casi nadie cuenta

Una revocación tiene fecha, y la firma también. Que un certificado esté anulado
**hoy** no invalida una factura firmada **hace dos años**: en su momento valía.
Rechazarla sería tirar una factura buena, que es el error caro de esta parte.

Salvo que lo anularan porque le robaron la clave, y entonces al revés: todo lo
que esa clave firmó pasa a ser sospechoso, **también lo anterior a la
denuncia**, porque quien la robó pudo firmar con fecha atrasada.

| Situación | Qué sale |
|---|---|
| Anulado antes de la fecha de firma | `REVOCADO`, error |
| Anulado por clave comprometida, sea cuando sea | `REVOCACION-COMPROMISO`, error |
| Anulado después de la fecha de firma, por otro motivo | `REVOCACION-POSTERIOR`, aviso |
| Suspendido (`certificateHold`) | `REVOCACION-SUSPENDIDO`, aviso |

Y hay una vuelta más, que también se dice: **la fecha de firma la escribe quien
firma**. Sin un sello de tiempo de un tercero —XAdES-T, que ninguna muestra
trae— comparar las dos fechas es fiarse de su palabra.

### La trampa de la respuesta negativa

«No está en la lista» solo significa «no está revocado» si la lista está
firmada por la autoridad que toca, es posterior al momento que se juzga y cubre
a ese certificado. Si falla cualquiera de las tres, la ausencia no prueba nada
—y es justo ahí donde un validador tiene la tentación de pintar el tic verde—.
Aquí no se pinta. Casos en que se dice «no se sabe» en vez de «vigente»:

- La lista **no la firmó** quien dice. Es el ataque con más sentido contra esta
  parte: una CRL vacía a nombre de la autoridad «demuestra» que un certificado
  revocado sigue vivo. Se verifica su firma con la clave del emisor.
- El emisor **no tenía permiso** para firmar listas (`cRLSign`).
- La lista es **incremental** (delta CRL). Es el fallo más traicionero, porque
  parece una lista normal: solo trae los cambios desde otra, así que quien la
  lea como completa dará por vigente a todo el que no aparezca. Sí puede
  acusar; lo que no puede es absolver.
- La lista está **acotada** a otra clase de certificados
  (`issuingDistributionPoint`).
- La lista trae una **extensión crítica** que no sabemos leer.
- La lista es **anterior** a la fecha de la firma: no pudo enterarse de una
  anulación posterior.
- La lista de la carpeta está **vencida**: `REVOCACION-LISTA-VIEJA`, porque
  no aparecer en una lista caducada no es lo mismo que estar vigente. Se mide
  con `--hoy` o, sin él, con la fecha de hoy: hasta el 05-10-2026 sin `--hoy`
  no se medía, y una lista vencida el 01-04-2026 daba «no consta anulado»
  medio año después. Una lista que trae el documento no avisa, igual que una
  respuesta OCSP: si ha servido para contestar es posterior a la firma, y lo
  que dice de aquel momento no caduca. Avisar ahí llenaría de ruido toda
  factura archivada.

Manda **la lista más nueva, y solo ella**. Recorrerlas todas buscando el número
de serie parece más prudente y es lo contrario: una suspensión que se levanta
desaparece de las listas siguientes, y una lista vieja resucitaría una
anulación que ya no existe.

Cada una de estas defensas tiene un test que se pone rojo al quitarla:
comprobado desactivándolas una por una, las nueve.

### Ver lo que hay instalado

```bash
factura-e --ver-revocaciones
```

```
Listas de revocación en revocaciones:

  CA intermedia
    anulados  1
    publicada 2026-09-18
    vale      hasta 2027-04-06
```

### Lo que sigue sin comprobarse

- **Las respuestas OCSP que vengan dentro del documento.** Se detectan y se
  dice que están, pero no se leen todavía.
- **Si anularon el certificado después de la última lista que tengas.** Eso no
  lo arregla ningún validador: ninguna lista sabe lo que pasó después de
  publicarse.

## Ejemplo de salida

```
UBL v2.1 (factura) · dice seguir EN 16931 — 4 error(es).

[BR-CO-10] La suma de importes de línea que declara la factura no coincide
con la suma real de sus líneas. Suele ser una línea añadida o modificada sin
recalcular el total.
  Campo: Suma de importes de línea
  Debería ser: 90,00 (suma de las 2 líneas)
  Tiene: 100.00
```

## La lista de confianza: de dónde salen las anclas

Encadenar hasta un ancla contesta «de quién es este certificado». Debajo hay
otra pregunta, y es la que decide si lo demás significa algo: **¿de dónde ha
salido esa ancla?** Es el único sitio de este validador donde equivocarse no
produce un error, produce un aprobado.

Recopilar raíces a mano no vale, y no por trabajo: **quien elige el montón
elige a quién cree el validador**. La respuesta correcta ya existe, es pública
y va firmada.

### La respuesta la da el artículo 22 de eIDAS

Cada Estado miembro está obligado a publicar, firmada y en formato procesable,
la lista de sus prestadores cualificados: quién es autoridad de certificación
cualificada, desde cuándo y con qué certificado. El formato es **ETSI TS 119
612** y se le llama TSL. La Comisión publica además la lista de esas listas
(LOTL).

O sea que «¿en quién hay que confiar?» tiene respuesta oficial, publicada,
firmada y con fecha. No hay que inventar el conjunto: hay que leerlo.

### La cadena de la cadena, y dónde acaba

Una lista bajada de una dirección no vale nada por sí sola: si no compruebas
quién la firmó, has aceptado la lista de en quién confiar de manos de quien
contestara al DNS. Así que hay que verificarla contra algo que ya sepas, y ese
algo es otra lista:

| # | Quién | Dice | Se comprueba contra |
|---|---|---|---|
| 1 | El **DOUE** | dónde está la LOTL y qué certificados la firman | nada: es el final, y está fuera de internet |
| 2 | La **LOTL** | dónde está la lista de cada país y quién la firma | la huella del DOUE |
| 3 | La **lista del país** | qué autoridades son cualificadas | los certificados que dice la LOTL |

Lo bonito del asunto es dónde termina: en un **documento del Diario Oficial**,
con número de expediente. La raíz de toda esta confianza no es un servidor, es
un boletín. Encaja exactamente con la idea de la que sale este proyecto: las
reglas son públicas.

### Las direcciones, verificadas y no escritas de memoria

Están en este README y **no en el código**, a propósito: una dirección metida
en el código parece un dato de confianza y no lo es.

- **Lista de listas (LOTL):** `https://ec.europa.eu/tools/lotl/eu-lotl.xml`,
  con los seis certificados que pueden firmarla y sus huellas SHA-256, en el
  anexo del **DOUE C/2026/1944, de 15 de abril de 2026**.
- **Lista de España:** `https://tsl.digital.gob.es/TSL.xml` (3,0 MB), que
  publica el Ministerio para la Transformación Digital y de la Función Pública.
  Al lado hay una versión legible (`TSL.pdf`), su resumen (`TSL.sha2`) y el
  registro de cambios (`cambiosTSL.pdf`).

Merece la pena contar por qué me molesté en comprobarlas. La dirección del
ministerio que yo tenía en la cabeza —`sede.serviciosmin.gob.es`— **ya no
existe**: responde con una redirección permanente a otro sitio. Es exactamente
el fallo que iba a cometer, y del que ya había una constancia en este mismo
fichero: una huella inventada de memoria. Por eso la lista de España no se
escribe en ningún sitio del programa: **la dice la LOTL**, que es quien tiene
autoridad para decirla, y `--ver-tsl` la enseña.

### Mirar una lista

```
python -m validador --ver-tsl TSL.xml
```

```
  territorio  ES
  operador    MINISTERIO DE ASUNTOS ECONOMICOS Y TRANSFORMACION DIGITAL
  secuencia   188
  publicada   2026-08-06
  siguiente   2027-02-02

Servicios que emiten certificados cualificados: 243
  concedidos       129
  retirados        114
  sin certificado  0
  no utilizables   0

  anclas que saldrían: 133

Retirados —no se instalan, y las facturas que firmaron antes de
retirarse eran buenas—:
  2016-06-30  withdrawn    Banco Santander, S.A.
  2016-06-30  withdrawn    Fábrica Nacional de Moneda y Timbre - Real Casa …
  2023-09-14  withdrawn    Dirección General de la Policía
  …

La firma de esta lista no se ha comprobado aquí: mirarla es una cosa y
creérsela es otra. Para lo segundo, --montar-anclas.
```

Eso es la lista española de verdad, la del 6 de agosto de 2026.

Sobre la lista de listas enseña la dirección de cada país y cuántos
certificados pueden firmarla. Eso es lo que evita escribir ninguna a mano.

### Montar el conjunto

```
python -m validador --montar-anclas TSL.xml --segun eu-lotl.xml \
                    --firmante <huella del DOUE> --en anclas/
```

Y lo que pasa si te saltas un paso:

```
$ python -m validador --montar-anclas TSL.xml --en anclas/
Falta decir quién tenía que firmar la lista, y sin eso no se monta nada:
verificarla contra el certificado que ella misma trae dentro no demuestra
nada, porque cualquiera firma su propia lista.
  --firmante HUELLA   la huella SHA-256 de quien la firma
  --segun LOTL        sacarla de la lista de listas europea
```

```
$ python -m validador --montar-anclas TSL.xml --segun eu-lotl.xml --en anclas/
Falta --firmante. La lista de listas también hay que comprobarla: si te la
crees porque sí, lo que has hecho es elegir en quién confiar a partir de un
fichero que no has verificado.
```

**Se niega, no avisa.** Un aviso deja la decisión en manos de quien tiene
prisa, y lo que sale de aquí es la raíz de confianza de todo lo demás.

### Cómo se renueva el conjunto

Tres cosas se quedan viejas aquí, y **cada una tiene su propio reloj**. Vale la
pena no mezclarlas, porque la respuesta a «¿cada cuánto hay que tocar esto?» es
distinta para cada una.

| Qué | Cada cuánto | Cómo te enteras |
|---|---|---|
| Las **listas** (`listas/`) | se republican varias veces al año | la lista dice hasta cuándo responde por sí misma |
| Las **anclas** (`anclas/`) | cuando cambia la lista | `--ver-anclas`, que avisa a 90 días de caducar |
| Las **retiradas** (`anclas/retiradas/`) | se acumulan, no caducan | no hay que vigilarlas: solo amparan lo de antes |
| Las de **sellado** (`anclas-sellos/`) | a la vez que las otras | salen de la misma orden y de la misma lista |
| Las **huellas del DOUE** | años | un anuncio nuevo en el Diario Oficial |

El mandato es siempre el mismo, y lo único que cambia entre una vez y la
siguiente son los dos ficheros de `listas/`:

```
python -m validador --montar-anclas listas/TSL.xml --segun listas/eu-lotl.xml \
                    --firmante <huella> [--firmante <otra>...]
```

Sin `--en`, escribe en `anclas/`, que es donde el validador las busca sola. La
carpeta se **rehace entera**, no se parchea: por eso el manifiesto dice «no se
edita a mano, se vuelve a montar».

**Qué mirar cuando ya está montado.** `--ver-anclas` lo dice todo de un vistazo:
de dónde salió el conjunto, qué hay dentro, con qué huella y qué se está
apagando. De las de agosto de 2026, dos caducan el 31 de diciembre; el resto aguanta
años, y hay tres que llegan a 2047.

**Cuándo hay que rehacerlo, en la práctica.** La lista española del 6 de agosto
de 2026 promete volver a publicarse antes del 2 de febrero de 2027, pero se
republica bastante más a menudo —iba por la secuencia 188—. Con revisarlo cada
tres meses sobra, y hay dos avisos que lo piden solos:

- `--ver-anclas` marca lo que caduca en menos de 90 días;
- una factura cuyo informe diga *«no tenemos el certificado de X»* con X en la
  lista, que significa que el conjunto se quedó atrás.

**Lo único que no se automatiza, y a propósito:** las huellas del Diario
Oficial. Ahí acaba la cadena, y si se cogen de un fichero del disco en vez de
del boletín, la cadena deja de acabar en ninguna parte. Se comprueban a mano,
las pocas veces que cambian.

### Una lista no es un montón de certificados

Es la trampa del formato, y es la misma forma que ya tenía la revocación: **un
servicio de la lista es un certificado con un estado y una fecha**. Quien se
quede solo con los certificados monta un conjunto que incluye a las autoridades
retiradas, que es justo lo contrario de lo que se pretendía.

Aquí se filtra por tipo (solo lo que emite certificados cualificados: ni sellos
de tiempo ni servicios de estado) y por estado (solo `granted`), se quitan los
repetidos —una autoridad que emite para firma y para sello aparece dos veces
con el mismo certificado— y se cuenta lo que se deja fuera, incluidos los
servicios que se identifican **sin** certificado, que son legales y no dan
ancla.

### Lo que no resuelve, dicho

Que una autoridad esté cualificada **hoy** no dice que lo estuviera cuando se
firmó la factura. Una autoridad retirada el año pasado firmó certificados
buenos hace dos, y con este conjunto sus facturas antiguas salen como «no llega
a ninguna autoridad conocida»: un aviso, no un error, y el mensaje ya dice que
eso no se distingue de que falte un certificado. La lista trae la fecha de cada
cambio de estado y aquí se lee, se cuenta y se anota en el manifiesto; cerrarlo
del todo es darle al almacén una ventana de validez por ancla, que es otro
trabajo.

Y lo más gordo, que se descubrió al pasarlo por la lista de verdad: **46 de
las 129 autoridades cualificadas concedidas usan curva elíptica**, y este
validador solo verifica RSA. Se dice y se cuenta; ver abajo.

### Pasado por las listas de verdad

Ya está hecho, y era lo que faltaba. Las dos listas bajadas de donde dice
arriba, el 27 de agosto de 2026:

| | Lista de listas | Lista de España |
|---|---|---|
| tamaño | 478 KB | 3,0 MB |
| secuencia | 392 | 188 |
| publicada | 2026-08-25 | 2026-08-06 |
| vuelve a publicarse | 2027-02-17 | 2027-02-02 |
| la firma | EUROPEAN COMMISSION, 4096 bits | SPANISH TRUST SCHEME OPERATOR |
| comprobada contra | las seis huellas del DOUE | lo que dice la lista de listas |

Las dos verifican. Y de propina, el ministerio publica el SHA-256 de su lista
en `TSL.sha2`: **cuadra** con el fichero bajado, que es una confirmación
independiente de que la descarga llegó entera.

De los 436 servicios de la lista española, 243 emiten certificados
cualificados: **129 concedidos y 114 retirados**. De ahí salen **133 anclas de
33 prestadores** —87 de RSA y 46 de curva elíptica— —la Fábrica Nacional de Moneda y Timbre, la Dirección General
de la Policía, Camerfirma, Izenpe, Firmaprofesional, ANF, el Consejo General de
la Abogacía...—. Leer la lista cuesta 0,5 s y verificarla 0,2 s.

Y **5 de cada 6 anclas no son autofirmadas**, que confirma sobre datos reales
lo que ya se había arreglado a ciegas: una lista de confianza publica las CA
**emisoras**, no las raíces.

### Lo que se encontró al pasarlas: 46 autoridades que el validador no sabía usar

De los 129 servicios concedidos, **46 traen un certificado de curva elíptica**.
El validador solo verificaba RSA, así que esas 46 autoridades cualificadas se
quedaban fuera del conjunto —87 anclas en vez de 133—. No era un fallo de la
lista ni del certificado: el corto era este validador.

**Ya está resuelto**: ver «La firma con curva elíptica». La cuenta se conserva
igualmente, porque la maquinaria que la lleva sigue haciendo falta —hay
certificados de Ed25519 y curvas fuera de las tres, y el día que aparezca uno
tiene que salir contado y con su motivo, no desaparecer en silencio—:

```
  no utilizables  0  (traen certificado y no sabemos usarlo)
```

Y se cuenta aparte de las retiradas a propósito, porque **no es la misma
noticia**: una autoridad retirada dejó de ser cualificada; una que no sabemos
usar sigue siéndolo. Las facturas de ambas salen igual —«no llega a ninguna
autoridad conocida»— y el manifiesto explica la diferencia.

### Cuatro fallos que solo enseñó el fichero real

Ninguno de los cuatro se ve con listas inventadas, y los cuatro son de los que
no dan error: dan un resultado que parece bueno.

1. **El puntero de un país apuntaba al PDF.** En la lista de listas, once
   países aparecen **dos veces** —una entrada para la versión legible y otra
   para el XML—, y la del PDF va primero. España es uno de los once. Quedarse
   con «la primera que case» mandaba a bajar un documento que ninguna máquina
   va a leer, y de paso daba por buenos los certificados de esa entrada
   confiando en que fueran los mismos que los de la otra: hoy lo son, y nadie
   lo ha prometido. Ahora se mira el tipo de fichero declarado.

2. **La lista de España pasaba por lista de listas.** Porque trae un puntero
   —de vuelta a la lista de listas, que el formato se lo exige—, y yo estaba
   distinguiéndolas por «¿trae punteros?». Resultado: `--ver-tsl` sobre la
   lista española enseñaba el puntero de vuelta en lugar de sus 243
   autoridades. Ahora manda el tipo que la lista declara de sí misma, que
   además va dentro de lo firmado.

3. **«Sin certificado: 425».** Un servicio sano trae **varias** formas de
   identificarse —el certificado, el nombre del sujeto, la huella de la clave—
   y yo contaba «las que no son un certificado»: dos de cada tres en cada
   servicio correcto. Un número enorme, sin significado, y que además **tapaba**
   la noticia de verdad, que era la de las 46. Ahora se cuentan servicios, que
   es lo que se pierde: autoridades, no líneas.

4. **«DER truncado» sobre un certificado impecable.** Al intentar leer el punto
   de una curva elíptica como si fuera una pareja de enteros salían tres
   errores distintos —«DER truncado», «longitud DER indefinida o truncada», «no
   parece una clave RSA»— acusando al fichero de estar roto. Ahora se mira el
   OID del algoritmo **antes** de leer la clave, y sale una sola frase que es
   verdad. Hay una excepción propia, `ClaveNoSoportada`, para que quien lea una
   carpeta de certificados pueda distinguir «este fichero está roto» de «este
   fichero está bien y el corto soy yo».

### Y una comprobación que salió al revés, que también vale

Ninguna de las cinco muestras firmadas del Gobierno encadena hasta las 87
anclas. El motivo no es el conjunto: **cada una lleva dentro un solo
certificado, el del firmante, sin ningún intermedio**. Sin el intermedio no hay
cadena que construir por muy completo que sea el almacén, y el informe ya lo
dice con esas palabras: *«no tenemos el certificado de «AC DNIE 001»»*.

La del DNIe además tiene el otro problema, y es el ejemplo real del hueco
temporal que queda abierto: su raíz —«AC RAIZ DNIE»— figura en la lista como
**retirada el 14 de septiembre de 2023**. La factura es de antes y era buena
entonces.

### Las autoridades retiradas, y la fecha de la firma

Una factura se guarda años. La autoridad que la firmó puede haber dejado de ser
cualificada desde entonces, y eso **no** invalida la factura: en la lista
española hay 114 autoridades retiradas entre 2016 y 2026, y todas emitieron
certificados buenos mientras estuvieron.

Montando solo lo concedido hoy, esas facturas salían como «no llega a ninguna
autoridad conocida»: ni era verdad ni era el motivo.

Ahora la carpeta de anclas tiene dos plantas:

```
anclas/
  ESTADOS.tsv                      qué dice la lista de cada una
  ac-camerfirma-…-2016-3a80….cer   133 vigentes
  …
  retiradas/
    ac-de-antano-…-7f21….cer       135 retiradas, con su fecha
```

Una retirada solo ampara lo que se firmó **antes** de la fecha en que la
retiraron. Fuera de ahí no es que falle la firma: es que esa autoridad ya no
respondía por ella, y se dice con un código propio.

```
[CADENA-RETIRADA · Firma electrónica] El certificado que firma lleva a una
autoridad que ya no era cualificada cuando se firmó: «AC de antaño» dejó de ser
una autoridad cualificada el 01-02-2025, antes de la fecha de la firma. La
firma puede ser auténtica; lo que no la ampara es la lista de confianza del
Estado.
```

Y cuando sí ampara, **se declara**, porque aceptar una firma por una autoridad
que ya no lo es —aunque sea correcto— es una decisión más discutible que la
normal:

```
[CONFIANZA-ANCLA · Firma electrónica] … Esa autoridad dejó de ser cualificada
el 01-02-2025: se acepta porque la factura es anterior, no porque siga vigente.
```

**Por qué van en una subcarpeta, y no mezcladas.** Porque ampliar el conjunto
no debe ampliar la confianza. Si estuvieran revueltas con las vigentes, copiar
la carpeta sin `ESTADOS.tsv` convertiría 135 autoridades caducadas en 135
autoridades de confianza sin fecha de caducidad, y nada en el informe lo diría.
Separadas y con la tabla aparte, **si falta la fila, el ancla no se usa**: una
ventana que no se sabe dónde acaba no es una ventana. Hay una prueba para eso,
y otra en el navegador.

**Una asimetría a propósito: solo se mira el final de la ventana.** El final es
real —si el Estado retiró a una autoridad el 14 de septiembre de 2023, lo
firmado después no está amparado—. El principio no dice lo que parece: casi
todas las anclas concedidas ponen 2016-06-30, que no es el día en que esa
autoridad se volvió fiable sino el día en que empezó a aplicarse eIDAS.
Rechazar por ahí tiraría todas las facturas anteriores a 2016 de autoridades
que existían y valían, contestando a una pregunta que la lista no responde.

**Sin fecha de firma, una retirada no se usa.** Su único aval es la fecha; sin
nada que comparar, dar por buena la lectura más generosa sería lo contrario de
lo que hace este validador.

### La procedencia viaja con los ficheros

Montar el conjunto deja un `PROCEDENCIA.txt` en la carpeta, y su primera línea
es la que sale en el informe de cada factura:

```
de la lista de confianza de ES, publicada por Ministerio para la
Transformacion Digital el 01-08-2026
```

Va en un fichero y no en el código de quien construye el almacén porque **la
procedencia tiene que viajar con los ficheros**. Si hay que acordarse de
pasarla en la llamada, el día que alguien copie la carpeta a otro sitio se
quedará sin ella, y un conjunto de anclas que no dice de dónde viene es
exactamente lo que habíamos quedado en no repartir.

El resto del fichero es para quien lo abra a mano: la secuencia de la lista,
cuándo se publicó, cuándo prometía volver a publicarse, quién la firmó y con
qué huella, cuántas anclas salieron y cuántas se quedaron fuera y por qué.

### Dos fallos que salieron montando esto

**`"".join(texto.split())` se come los espacios de dentro.** Servía para el
base64 de un certificado, donde hay que quitar los saltos de línea, y es
destructivo para un nombre: la lista española habría acabado diciendo
«FABRICANACIONALDEMONEDAYTIMBRE» en el informe de cada factura. No sale con
datos inventados de una sola palabra; sale en cuanto el nombre lleva un
espacio, o sea siempre. Lo cazó la primera prueba que puso un nombre realista.

**El aviso de SHA-1 disparaba contra el propio ancla.** La regla excluía las
raíces autofirmadas —su firma no la comprueba nadie, así que su algoritmo da
igual— y eso es lo mismo que excluir el ancla **solo mientras las anclas son
raíces**. Una TSL no publica raíces: publica las CA **emisoras**, que están
firmadas por alguien. Con el conjunto montado desde la lista, el validador
avisaba de la autoridad de media España por un algoritmo que aquí no se usa
para nada. Reproducido con una sonda antes de tocar el código, y la prueba de
regresión se pone roja al deshacer el arreglo.

## Lo que falta para estar operativo del todo

Los tres tipos de rechazo que existen —el de forma, el de contenido y el de
firma— están cubiertos, y probados contra 82 facturas ajenas. La firma está
entera y sin red: integridad, RSA y ECDSA, cadena hasta una autoridad de la
lista de confianza del Estado, ventana de validez por ancla y revocación contra
listas locales.

Lo que queda, ordenado por lo que de verdad estorba.

### Cobertura de validación

| Hueco | Por qué importa | Tamaño |
|---|---|---|
| **El directorio de EDIFACT, por partes** | Se leen los segmentos que INVOIC usa de verdad, no el directorio entero. Un segmento que no esté escrito se guarda por posiciones y no lo mira ninguna regla | pequeño |
| **Los mensajes de estado del RD** | `calendario.py` calcula el plazo de cuatro días hábiles, pero no se valida un documento de estado en sí | medio |
| **El IVA por línea** | Que el tipo de cada línea case con lo que se vende no es EN 16931: es la Ley del IVA, y hace falta saber qué se vende | dudoso |

**EDIFACT ya está**, que era el más gordo por ser un cuarto del alcance legal
declarado. Se lee en sus dos formas, los nueve ejemplos de la Comisión pasan
limpios, y 64 ficheros ajenos con 265 mensajes dentro —siete versiones del
directorio, de 1993 a 2007— cuadran con las cuentas que traen dentro. Lo que queda de esa parte es de grado, no de fondo: dos campos sin
situar —el redondeo (BT-114) y el código del motivo de exención (BT-121)—, que
constan como hueco declarado en el mapa en vez de leerse de un sitio
equivocado, porque un importe sacado del cajón de al lado entra en las cuentas
y las descuadra sin avisar.

**El sellado ya está entero**: un sello se lee, se comprueba, se contrasta
contra las autoridades de sellado del Estado y su fecha manda sobre la que
declara quien firma. Lo que queda de esa parte no es código sino ficheros:
ninguna de las muestras que hay trae sello, así que todo lo que se sabe de cómo
se comportan los sellos españoles de verdad está por ver.

### Producto

- ~~La página de verdad.~~ **Hecha**: `web/index.html` es **Glosa-e**, la
  herramienta —se suelta una factura y sale su glosa, con las incidencias
  separadas por gravedad y el alcance debajo—, y el banco de pruebas se ha
  movido a `web/banco.html`, que sigue siendo la prueba de que todo esto corre
  en el navegador de quien la usa. Lo que queda no es interfaz: es qué se
  vende encima.
- ~~Alojar Pyodide aquí.~~ **Hecho**: `--traer-pyodide` lo baja y `--sitio` lo
  mete dentro, y se niega a montar si falta. Medido después: **cero** dominios
  de terceros.
- **Los 9,4 MB del primer arranque** (15 en disco, 9,4 por el cable). Hay compilaciones de Pyodide más
  ligeras. La primera visita no va a ser instantánea nunca, y la página tiene
  que decirlo en vez de parecer rota.
- ~~Repartir los esquemas y las anclas con la página.~~ **Hecho**:
  `--empaquetar` arma el zip, la página lo carga y enseña de qué lista salen
  las anclas, de cuándo son y cuándo toca renovarlas. Ver «Lo que la página se
  lleva puesto».
- **Facturas de un cliente de verdad.** Es lo único que va a decir si los
  mensajes están bien escritos, y suele mover la lista entera. Los sellos ya
  se han pasado por documentos reales del Estado y por una TSA cualificada
  —ver «Pasado por sellos de verdad»—, y de ahí salieron dos defectos.

### Deuda conocida

- **Numeración con barra** (`1/2026`): CU-13 y CU-14 no llegan a dispararse.
- **`Catalogo` no es seguro entre hilos.** Da igual en consola; no daría igual
  en un servidor.
- **Control de CIF tipo L y M** sin contrastar contra la AEAT.
- **Claves comprimidas, Ed25519 y RSA-PSS**: se dicen por su nombre y no se
  verifican. No corre prisa —no hay ninguna en la lista española— y el día que
  aparezca una, sale contada y con su motivo en vez de desaparecer.

### Por dónde empezaría

1. **Facturas reales de un cliente**, que ya no es programar sino
   conseguirlas. Es lo único que va a decir si los mensajes están bien
   escritos, y ahora hay cuatro formatos que enseñar en vez de tres.
2. **Las respuestas OCSP embebidas**, que completan la revocación sin red.
3. ~~La página de verdad.~~ **Hecha.** Lo que queda es lo de después:
   publicarla, y decidir qué servicio va encima de la herramienta gratis.

## EDIFACT: el cuarto formato

El RD 238/2026 admite cuatro formatos y este validador entendía tres. A un
EDIFACT le contestaba «solo se ha identificado, no validado», que para quien
recibe la factura es lo mismo que no tener validador.

Y había algo peor de lo que decía el aviso: **los ejemplos EDIFACT de la propia
Comisión Europea ni siquiera llegaban a esa frase**. Se publican en ISO 20625
—el mismo mensaje escrito como XML— y, como su raíz no es Facturae ni UBL ni
CII, salían por la puerta de «formato no reconocido». El validador decía no
saber qué era el fichero de referencia de uno de los cuatro formatos que admite
la ley.

### Por qué EDIFACT cuesta más que añadir un mapa

Los otros tres formatos son XML: se parsean con lxml y se leen con XPath, y por
eso a cada uno le basta con rellenar una `Sintaxis` en `sintaxis.py`. EDIFACT no
es XML. Es una tira de segmentos separados por apóstrofos donde **el significado
de cada dato es su posición**:

```
NAD+SU+++OTTO HARRASSOWITZ+KREUZBERGER RING 7C-D+WIESBADEN++65174+DE
```

Ahí no pone «nombre» ni «país» en ninguna parte. Pone que el cuarto elemento del
NAD es el nombre y el noveno el país, y eso hay que saberlo de antes.

**Y la dificultad de verdad: EDIFACT tampoco marca los grupos.** En XML, que una
línea tenga su propio IVA se ve porque el IVA está dentro de la línea. Aquí va
todo al mismo nivel y quién cuelga de quién se deduce del orden:

```
LIN+1   QTY+47:100   MOA+203:18550   TAX+7+VAT+++:::21+S   LIN+2
```

Ese TAX es el de la línea 1, y se sabe solo porque viene detrás del LIN y antes
del siguiente. Reconstruir esa jerarquía es casi todo el módulo, y es la parte
que puede fallar **en silencio**: un IVA de línea colgado del documento no da
error de lectura, da un desglose equivocado.

### La decisión que ahorra el resto

Una vez reconstruida la jerarquía se escribe como XML, con la forma de
ISO 20625. A partir de ahí no hay nada especial: las reglas de EN 16931 y la
aritmética del IVA son las de siempre, sobre un árbol y con XPath. Las dos
maneras de traer un EDIFACT —la tira y el XML— acaban en el mismo sitio, y las
reglas se escriben una sola vez.

`sintaxis.py` prometía desde el primer día que «añadir una sintaxis nueva
debería ser rellenar otra `Sintaxis` sin tocar ninguna regla». Nadie lo había
comprobado. Resultó ser cierto salvo en **un campo**: UBL y CII escriben «esto
suma» con un booleano y EDIFACT con una letra —C de cargo, A de descuento—, así
que la comparación con «true» daba descuento en todos los cargos y los restaba
en vez de sumarlos. Es un campo más en el mapa, no un `if` en las reglas.

### El mapa no nombra ningún grupo, y es lo importante

En EDIFACT los grupos van numerados —SG1, SG2, SG27— y **esa numeración depende
de la versión del directorio**. En la D.14B que publica la Comisión, las líneas
son el SG27; en otras versiones, otro. Un mapa con el número dentro obligaría a
una tabla por versión y a no saber leer las que no estuvieran, y las facturas
reales no usan la misma versión que los ejemplos oficiales.

Preguntando en cambio por lo que hay dentro —«el grupo que contiene un
`S_LIN`»— la misma ruta vale para las dos, y para las que vengan.

### El hueco que no era inofensivo

La tabla de qué cuelga de qué se dedujo al principio de los nueve ejemplos de
la Comisión, y le faltaba media docena de segmentos que esos nueve no usan.
Parecía inofensivo: lo que no está en la tabla, no se lee.

No es eso lo que pasa. **Un segmento que no está en el grupo no se queda fuera:
lo cierra.** Un `PAC` —el embalaje de una línea, que muchas facturas de almacén
llevan— cerraba la línea, y el `MOA` que viniera detrás dejaba de ser el
importe de esa línea para convertirse en un total de la factura. Sin un solo
error por ninguna parte: los importes de las líneas contados como totales.

Así que la tabla se contrastó contra la gramática D.96A de `bots-edi`, un
proyecto de EDI que no tiene nada que ver con este. Salieron once grupos que
faltaban, y la tabla de ahora es la unión de las dos: lo que enseñan los
ejemplos de la D.14B y lo que dice esa gramática de la D.96A. La prueba del
`PAC` va con su control: quitando ese segmento de la tabla, el importe de la
línea se pierde.

La D.93A, que es la de EANCOM 93, se contrastó igual el 13-10-2026: contra su
gramática en `bots-edi` y contra el directorio que publican edifactory.de y
Stylus Studio, que dicen lo mismo. Faltaban dos segmentos que la D.96A ya no
tiene: `QVA`, las diferencias de cantidad, suelto en la línea, y `API`, la
información adicional del precio, en el grupo del precio. Con cualquiera de
los dos, la línea perdía su importe o su IVA, y una factura correcta salía con
BR-24, BR-26 y BR-CO-04. Están en la tabla desde ese día, con su prueba y su
control. Las posiciones de los datos que leen las reglas son las mismas en la
D.93A que en la D.96A.

Queda un caso que la tabla no sabe distinguir, porque no mira el contexto: un
`RFF` detrás del `MOA` de una línea se cuelga del `MOA`, y no de la línea. Detrás
del `MOA` de los totales sí es suyo. Ninguna regla lee el `RFF` de una línea.
Medido con un segundo lector que coloca cada segmento según la gramática, pasa
en 2 de los 247 segmentos de los cuatro mensajes D.93A del corpus, y en 9 de
los 46.949 de los 258 D.96A.

Lo que distingue un dato de otro no es dónde está sino el **cualificador**: el
total sin impuestos y el importe de una línea son los dos un `MOA`, y lo único
que los separa es que uno dice 389 y el otro 203. Esos códigos no se copiaron de
una tabla: se comprobaron **haciendo la cuenta en los nueve ejemplos de la
Comisión**. El 79 es la suma de los 203 en los nueve; el 388 es el 389 más el
176 en los nueve. Es la única manera de saber que un cualificador significa lo
que uno cree.

### Contra ficheros que no ha escrito este proyecto

**Los nueve ejemplos de la Comisión pasan sin un solo error.** Antes ni se
reconocían. Y no es que no se lea nada: hay una prueba de que a los nueve se les
encuentran las líneas, el desglose y los totales, porque una factura de la que
no se saca ningún importe tampoco da errores de cuadre.

**Y cuatro facturas en tira, de las que viajan.** Estas traen dentro su propia
respuesta: el UNT declara cuántos segmentos lleva el mensaje y el UNZ cuántos
mensajes el sobre. Esas cuentas las escribió quien emitió la factura, así que
cuadrar con ellas es una prueba que no se aprueba uno solo.

La de **Otto Harrassowitz** es la que más dice: una librería alemana facturando
suscripciones a una biblioteca universitaria, 2.964 caracteres en una sola tira
sin un salto de línea, con apóstrofos dentro de los títulos de las revistas.
Declara 138 segmentos. **Salen 138 si el carácter de escape se trata bien y 139
si no**, y hay una prueba de las dos cosas: la que comprueba que salen, y la que
comprueba que sin tratarlo no saldrían.

De ese lote, una viene mal de origen: la de `ballerina` dice llevar dos grupos
funcionales y lleva uno. Es un fichero de demostración y está mal; que salte es
lo correcto, y la prueba lo dice con su nombre en vez de bajar el listón.

### Lo que la norma obliga a contar

Un EDIFACT al que le falta un trozo **sigue pareciendo legible**: los segmentos
que quedan están perfectamente formados. Lo único que lo delata es que la cuenta
no sale. Por eso `ejemplos/edi-0002-cortado.edi` es la misma factura que
`edi-0001.edi` con tres segmentos menos y sin tocar el UNT:

```
ejemplos\edi-0002-cortado.edi
  EDIFACT v96A (factura) · dice seguir EN 16931 — 1 error(es), 1 aviso(s).

  [EDI-MENSAJE-DESCONTADO · ISO 9735] El mensaje dice tener un número de
  segmentos distinto del que tiene. Esa cuenta incluye el UNH y el UNT, y es
  lo único que delata un fichero al que le falta un trozo.
    Campo: UNT, número de segmentos
    Debería ser: 38
    Tiene: 35
```

### Un total que está, pero con el código de antes de la norma

EN 16931 fijó qué cualificador va en cada campo, pero las facturas EDIFACT
llevan décadas circulando con las guías de cada sector, que eligieron otros.

Lo que se vio primero en cuatro facturas reales no es que se ignore la norma,
sino algo más incómodo: **se solapan**. Y contando los 64 ficheros ajenos —251
mensajes con totales— la cosa sale más nítida de lo que parecía:

| Cualificador | Qué es | En cuántos de los 64 |
|---|---|---|
| `79` | suma de las líneas — **de la norma** | 47 |
| `125` | base por categoría — **de la norma** | 44 |
| `124` | cuota por categoría — **de la norma** | 40 |
| `77` | total del documento — *no es de la norma* | 31 |
| `9` | lo que hay que pagar — **de la norma** | 20 |
| `86`, `131`, `129`, `128` | totales de guías de sector | 16, 6, 6, 1 |
| `388` | total con impuestos — **de la norma** | 1 |
| `389` | total sin impuestos — **de la norma** | **0** |

Los códigos de la norma para las **líneas** están en casi todos: el 79 en 47 de
los 64. Los códigos de la norma para el **total del documento** casi no están:
el 389 no aparece ni una sola vez en 265 mensajes, y el 388 en uno solo. En su
lugar, el 77 en 31 ficheros.

De los 251 mensajes que llevan totales, **192 no usan ninguno** de los tres
que EN 16931 mira, 43 los mezclan con otros y 16 usan solo los suyos.

O sea que un documento puede ir con los códigos de la norma en casi todo y
salirse justo en el que más se mira. Y no es una rareza de un emisor: es lo
normal.

Sin decirlo, esa factura recibe «falta el importe total con impuestos
incluidos». Es verdad que falta donde la norma lo pone, pero quien lo lee
entiende que no está y se va a buscar un dato que su factura ya trae. Decirlo
entero cuesta una línea y cambia la tarea:

```
[EDI-TOTALES-DE-OTRA-GUIA · ISO 9735] Los totales de esta factura no llevan los
códigos que usa EN 16931, sino estos: 128 (el total). Por eso las reglas
europeas dan por ausente el total sin impuestos, el total con impuestos y lo
que hay que pagar: el importe está escrito, pero con un código que la norma no
mira. Es lo normal en las facturas EDIFACT de antes de la norma, y para
cumplirla hay que cambiar el código, no añadir el importe.
  Debería ser: 389 sin impuestos, 388 con impuestos, 9 a pagar
  Tiene: 128
```

### Tres cosas que se saltaban en silencio

Salieron al conectar EDIFACT, y ninguna es de EDIFACT:

- **`codigo_unico.extraer` reventaba** con un `XMLSyntaxError` ante cualquier
  EDIFACT plano. Era verdad que no es XML, y no venía a cuento. Estaba así desde
  antes de esta rama, y se comprobó en un árbol de trabajo del commit anterior
  para no atribuirse un fallo ajeno ni escaparse de uno propio.
- **Apuntar a una carpeta no recogía los `.edi`**, y el resumen contaba los
  ficheros que sí había mirado. Es la forma exacta de dejar a alguien creyendo
  que ha revisado un lote entero.
- **El navegador no dejaba ni elegir un EDIFACT**: el selector admitía `.xml` y
  `.xsig`, así que el cuarto formato era invisible ahí.

### Y dos frases que prometían de más

Prometer de más es el peor fallo que puede tener un informe, porque lo que
promete es de lo que se fía quien lo lee.

La primera decía «no se ha comprobado la forma: **falta** el esquema de este
formato. Los que le tocan se llaman **(ninguno)**» —dos mitades que se
contradicen— sobre algo que no tiene esquema porque no es XML. Ahora es una
nota, que es lo que corresponde a algo que se ha dado por bueno y con qué:

```
[XSD-NO-APLICA · Esquema XSD] La forma no se ha comprobado contra un esquema
XSD, y no hace falta: EDIFACT no es XML y no tiene ninguno. En su lugar se han
comprobado las cuentas que la propia norma obliga a llevar en el sobre.
```

La segunda es la frase del final, la que dice de qué se ha fiado quien lee. Se
apuntaba «se ha comprobado la forma contra el esquema XSD» en un lote de puro
EDIFACT, donde no se había mirado ningún esquema, y a la vez **no se apuntaba
las reglas EN 16931**, que sí se habían pasado. Prometía de más por un lado y de
menos por el otro.

### Contra 64 ficheros que no ha escrito nadie de aquí

Los nueve ejemplos de la Comisión son facturas conformes hechas por quien
escribió la norma, y por eso valen para comprobar el mapa de campos. Pero no
se parecen a lo que llega: son limpios, todos del mismo directorio, y todos
declaran los separadores de siempre. Así que se buscaron ficheros EDIFACT
INVOIC en repositorios públicos de proyectos de EDI que traen casos de
prueba, y se bajaron **64**: facturas de Otto Harrassowitz a bibliotecas
universitarias, de Casalini Libri y W.S. Hein a Cornell, del mercado
energético alemán, y un corpus anonimizado de un proyecto de validación.
Siete versiones del directorio —D.93A, D.96A, D.96B, D.97A, D.01B, D.06A,
D.07A—, seis subconjuntos de sector, y **265 mensajes**.

**Lo que aguantó**, que es lo que más importa: la reconstrucción de grupos,
la parte que puede fallar sin dar error. En los 64 se comprobaron tres
cuentas que no dependen de este código —que cada `LIN` del fichero plano
salga como una línea del árbol, que ningún `MOA+203` acabe fuera de su línea,
y que las etiquetas sean etiquetas—. Las tres cuadran en todos. No apareció
ningún caso nuevo del tipo del `PAC`.

**Lo que no aguantó**: dos averías, y las dos de aquí.

#### El UNA de cinco caracteres

El UNA es lo que declara los separadores, y la norma dice seis caracteres:
componente, elemento, decimal, escape, un hueco reservado y terminador. **23
de los 64 escriben cinco**, saltándose el hueco: `UNA:+.?'UNB…` en vez de
`UNA:+. Son 18 emisores distintos en el UNB, asi que
no es la mania de uno.? 'UNB…`.

El lector cogía el sexto carácter, que era la `U` del `UNB`, y partía el
fichero por cada letra U. Ni un solo `UNH`, y la respuesta era esta:

```
[EDI-SIN-MENSAJE · ISO 9735] El fichero no trae ningún segmento UNH, que es
el que abre un mensaje. Sin él no hay nada que validar: lo que hay es un
sobre vacío.
```

Sobre un fichero con veinticuatro facturas dentro. Eso no se parece a un
fallo: no hay excepción, no hay aviso a medias. Hay una frase entera, en buen
castellano, que explica con precisión algo que no ha ocurrido — y quien la
lea archivará el fichero como vacío.

Leerlo bien no es adivinar. Detrás del UNA solo puede venir el UNB, porque
ISO 9735 no admite otra cosa ahí; así que se prueban las dos longitudes y se
queda la que deja un UNB detrás. Se acepta, y **se dice sobre qué base**:

```
[EDI-UNA-DE-CINCO · ISO 9735] El UNA declara cinco caracteres de servicio en
vez de los seis que manda ISO 9735: falta el hueco reservado. Se ha leído el
último como terminador de segmento, que es la única lectura posible porque
detrás del UNA solo puede venir el UNB.
```

#### Un apóstrofo sin soltar, y una traza de Python

Tres de los 64 traen un carácter de servicio dentro de un dato sin soltar con
`?`: el título de una revista checa en uno, un nombre de empresa con
apóstrofo —«…ER'S HANDELSGESELLSCHAFT MBH»— en los otros dos. El segmento se
parte por ahí, y el trozo de detrás no es un segmento: su «etiqueta» era
`A HISTORICKY <FORMERLY`. Con eso `lxml` no puede montar un elemento y
levanta un `ValueError` — que no salía por el informe sino por la consola,
como una traza, **y se llevaba por delante los otros 63 ficheros del lote**.

Conviene decir de quién es el destrozo, porque no es de quien parece. Ese
fichero es **la misma factura** que la de Harrassowitz que ya estaba entre
las muestras —número 246816, 8 de febrero de 2021—, publicada en otro
repositorio como caso de prueba: le quitaron la dirección del comprador y le
metieron el apóstrofo. El emisor escribe bien el escape; lo rompió quien lo
manipuló después. En el corpus anonimizado pasa algo parecido, con el
anonimizador sustituyendo un nombre de empresa. Da igual: ficheros así
circulan, y la respuesta a uno de ellos no puede ser una traza.

Ahora se aparta el trozo y se dice qué pasa. Apartarlo importa por algo más
que por no reventar: un trozo con una etiqueta que no está en la tabla de
grupos no se queda fuera del grupo, **lo cierra**, que es exactamente lo del
`PAC`. Si el corte cae dentro de una línea, los importes de esa línea pasan a
contarse como totales de la factura sin dar ningún error.

Y hay una forma de saber que apartarlo era lo correcto y no una comodidad:
**la cuenta la lleva otro**. A ese fichero le tocaron el título pero no el
UNT, que sigue declarando 138 segmentos. Con el trozo dentro salen 139;
apartándolo, 138. El otro declara 32 y salen 35; apartando los tres, 32. Es
decir: la cuenta que escribió el emisor sirve para detectar un destrozo
posterior al emisor.

Es además el reverso exacto de la muestra que ya había. En el original de esa
misma factura el escape está bien puesto y los 138 solo salen si se trata; en
la copia manipulada falta uno y los 138 solo salen si se aparta el trozo. La
misma comprobación caza las dos cosas, en las dos direcciones, porque el 138
no lo ha escrito este código.

#### Y un fichero que se llevaba el lote por delante

Ese `ValueError` está arreglado, pero que se llevara el lote es otra cosa y
había que arreglarla aparte. Apuntar a una carpeta de quinientas facturas y
que la séptima esté mal terminaba en una traza y **ninguna** de las otras
cuatrocientas noventa y nueve revisada; desde un script, en un código de
salida distinto de cero, que es el mismo que se ve cuando hay facturas con
errores.

Los ficheros son de otros y siempre habrá uno que traiga algo no previsto.
Ahora eso se cuenta como un error del fichero —para que el lote no dé por
bueno lo que no ha mirado— y se dice de quién es la culpa:

```
[VALIDADOR-SE-ATRAGANTA · Fichero] Este fichero ha hecho fallar al validador:
ValueError: … El fallo es del validador, no necesariamente de la factura, y
hay que arreglarlo aquí. Los demás ficheros del lote sí se han revisado.
```

#### Lo que los ficheros traían mal de origen

De los 64, unos cuantos vienen con defectos suyos, y separarlos de los de
aquí es la prueba de que las cuentas del sobre sirven:

- **W.S. Hein** cierra el intercambio con una referencia distinta de la que
  abrió: el UNB dice `000000767` y el UNZ `000000751`. Es también el único de
  los 64 con separadores propios —`UNA^<.? >`: componente `^`, elemento `<`,
  terminador `>`—, que es justo para lo que existe el UNA y hasta este
  fichero no había ninguno que lo demostrara. Todos los demás declaran los de
  por defecto, así que un lector que se saltara el UNA habría pasado igual.
- Varios del corpus anonimizado declaran en el UNZ más mensajes de los que
  llevan: se extrajo un trozo del intercambio y no se rehízo la cuenta.
- Uno declara 48 segmentos en un mensaje y lleva 47. Los otros seis mensajes
  del mismo fichero cuadran exactamente, y eso es lo que dice que el
  descuadre es suyo y no de la lectura.

Cinco de los 64 se han quedado como muestras permanentes, con su procedencia
anotada. Como el resto de `muestras/`, no se versionan: son facturas de
terceros.

## Sin servidor: el validador dentro del navegador

`web/` no es la página del producto, es la prueba de que la página es posible.
Pyodide compila Python a WebAssembly y lxml está entre los paquetes portados,
así que el validador entero corre dentro del navegador de quien mira la
factura. **El fichero no se sube a ningún sitio**, lo que ahorra a la vez un
servidor que mantener y la custodia de datos fiscales ajenos.

La duda real no era si arrancaba Python, sino si esa compilación de lxml traía
soporte de esquemas XSD: libxml2 se puede compilar sin él, y `esquema.py`
entero depende de `etree.XMLSchema`. Lo trae.

Las treinta y siete comprobaciones de `web/prueba.py` dan el mismo resultado
que en Python nativo —mismos códigos, mismos importes— pese a que ahí libxml2
es 2.9.10 y en local 2.11.9. Veintisiete son críticas: dos de curva elíptica, tres
de la lista de confianza y tres de sellos de tiempo: que se verifique y se monte allí, y que una lista manipulada no
monte nada. Esa parte depende de la canonicalización, que es lo más frágil de
esa compilación. Medido: 42 s el primer arranque, 4,8 s con la caché caliente,
10 ms por factura, y un lote de 200 en 2 segundos. Con facturas de la
solución pública, medido el 20-10-2026 de principio a fin con el informe
pintado: 200 en 2,7 s, 1.000 en 10,7 s y 3.000 en 31,4 s, con la página
contestando mientras tanto (el detalle, en `web/LEEME.md`).

```
python -m build --wheel --outdir dist
python -m http.server 8765
```

Y abrir <http://127.0.0.1:8765/web/>. Los detalles, en [`web/LEEME.md`](web/LEEME.md).

## Lo que la página se lleva puesto

El validador comprueba tres cosas —la forma, el contenido y la firma— pero dos
de las tres necesitan ficheros que no están en el código: los esquemas XSD, que
son de sus organismos, y las anclas de confianza, que salen de la lista del
Estado. Quien usa la consola se los instala. **Quien entra en una página no se
instala nada**, así que o viajan con la página o esa página comprueba una de
las tres y tiene que decirlo.

Ahora viajan. `python -m validador --empaquetar` arma un ZIP con las tres
carpetas dentro y un resumen al lado; el navegador lo baja de una vez y lo
descomprime en su disco virtual, y el validador las encuentra por las mismas
variables de entorno que usa fuera. Son **1,19 MB** —8,26 MB de ficheros, que
comprimen bien— al lado de los 14,7 MB de Pyodide.

Creció 0,25 MB el 11-09-2026, al entrar los 18 esquemas de UBL 2.5. Es lo que
cuesta poder comprobar la forma del único formato que la solución pública
admite, y se paga una vez por visita.

```
Escrito web/paquete.zip (1.19 MB)
  SHA-256  858f36e257e4b922831e59a5771e0dd99244d70c7014a68a36adfccc58af4050

  esquemas XSD          43
  anclas de firma       268
  anclas de sellado     121

  de la lista de confianza de ES, publicada por MINISTERIO DE ASUNTOS
  ECONOMICOS Y TRANSFORMACION DIGITAL el 06-08-2026
  montadas el 27-08-2026, la lista se renueva el 02-02-2027
```

Las carpetas de las que sale no se versionan; el zip sí, desde que la página se
publica. Estuvo fuera mientras se servía en local, donde cada uno armaba el
suyo. Al publicarla dejó de tener sentido: el sitio se construye desde este
repositorio, y sin el zip comprobaría el contenido y nada más.

La razón de no versionar anclas —**quien controle ese fichero controla en quién
cree el validador**— no se va por dejarlo fuera del repositorio: publicar la
página las reparte igual, a más gente y sin que nadie las mire. Lo que hace
falta es poder contrastarlas, y para eso está el SHA-256 de arriba, que va en
`PAQUETE.json` dentro del zip y fuera, y sale en la página.

**Y esa huella tiene que poder rehacerla otro**, o dice bastante menos de lo
que aquí estaba escrito: sin reproducibilidad solo prueba que la descarga
llegó entera, no que el paquete sea el de estas carpetas. No la daba. Armar
dos veces las mismas carpetas producía dos ficheros distintos, y la diferencia
está medida hasta el fondo: de las 436 entradas del zip, las 436 con el
contenido idéntico byte a byte y **una sola** con la fecha cambiada, la del
`PAQUETE.json` de dentro, a la que `writestr` le ponía la hora del reloj. Hoy
lleva la fecha del día en que se arma —que ya es un dato del propio paquete— y
dos vueltas dan el mismo fichero. La prueba mueve el reloj una hora entre las
dos, porque sin moverlo pasaba con el fallo dentro.

Hay que rehacerlo cada vez que se renueve la lista de confianza, unos seis
meses. Si se olvida, lo dice el propio validador: `ANCLAS-SIN-RENOVAR` sale en
cada informe y en el recuadro de la página.

### Y lo demás que viaja, que hasta el 20-09-2026 no lo miraba nadie

El zip se contrasta con su SHA-256 desde el 06-09-2026. Lo que viaja al lado
—el intérprete, la rueda del validador, las diez facturas de ejemplo y el
fichero de comprobaciones del banco— no se contrastaba con nada, y son bastante
más de 15 MB corriendo dentro del navegador de un desconocido.

**El intérprete.** `--traer-pyodide` dejaba un `HUELLAS.txt` al lado de lo
bajado. Parecía lo mismo y no lo es: se calcula de lo que llega, vive dentro de
`vendor/`, que no se versiona, y por lo tanto no viaja. Era un recibo —«esto
llegó»— haciéndose pasar por un contrato —«esto tenía que llegar»—. La
diferencia se ve en lo que permite: un día que el CDN sirviera otra cosa, la
construcción la bajaría, la apuntaría como buena y la publicaría. Y como
reutilizaba lo que ya estuviera en la carpeta sin mirarlo, una descarga cortada
de ayer se apuntaba hoy como buena.

Ahora las seis huellas están escritas en `validador/paquete.py`, versionadas, y
lo que no cuadra no se baja, no se monta y no se publica. Contrastadas dos
veces contra el CDN, con tres semanas de diferencia —30-08-2026 y
20-09-2026—, byte a byte iguales las seis. Subir de versión pasa a ser lo que
es: cambiar el intérprete que corre en el ordenador de otro, y se hace a mano.

**Lo que se baja al abrir la página.** `rueda.json` lleva la huella de cada
fichero desde que existe, y solo servía para que el navegador no sirviera una
copia vieja: iban detrás de la dirección, en el `?v=`, y **no las miraba
nadie**. Medido: con un byte de más en la rueda, la página arrancaba y ponía
«Listo». Ahora se comparan, y provocado sale así:

```
El validador (factura_e-0.1.0-py3-none-any.whl) no es lo que la pagina dice
traer: rueda.json publica e05dcb664e11... y lo que ha llegado resume
9419bf446c0a... . No se usa.
```

Lo mismo con un ejemplo cambiado y con `prueba.py`, que es el que más importa:
un fichero de comprobaciones servido de una caché vieja corre las pruebas de
ayer contra el código de hoy y sale todo verde. Ya pasó.

Esto **no es una frontera de seguridad** y no se va a decir que lo sea: el
manifiesto y los ficheros salen del mismo sitio, y quien pudiera cambiar uno
cambiaría el otro. Lo que caza es el fallo de esta casa —algo servido de una
caché haciéndose pasar por lo de hoy— y su pariente, la descarga a medias, que
no da ningún error: deja el fichero corto y sigue.

Queda una grieta, y se dice porque está medida: la rueda se baja dos veces. Lo
ideal sería bajarla una y darle los bytes a `loadPackage`, pero solo acepta una
dirección y la pide él. `emfs:`, que sirve para instalar desde el disco virtual
del navegador, lo bloquea la propia política de contenido de la página
—`connect-src 'self'` no admite ese esquema— y **no falla**: `loadPackage`
escribe un aviso en la consola y devuelve tan contento; lo cazó el `pyimport`
que ya estaba puesto detrás por esto mismo. Así que se mira la copia que se
baja y se instala la que pide él, que en el sitio publicado sale de la caché.

### Dos cosas que el paquete se niega a hacer

No empaqueta anclas **sin manifiesto**, porque un conjunto que no dice de dónde
viene es justo lo que habíamos quedado en no repartir: quien lo recibe estaría
creyendo a unas autoridades que nadie le ha dicho cuáles son.

Y no empaqueta anclas **cuya lista debía haberse renovado**. Esta es la que
importa y la que no era evidente.

### Un conjunto de anclas no caduca; la lista de la que salió, sí

Los certificados de dentro valen veinte o treinta años. Lo que vale seis meses
es la lista de **quién sigue estando autorizado**, que es otra cosa. A una
autoridad a la que el Estado le retire la cualificación en enero se le sigue
creyendo en un conjunto montado en agosto: su certificado está en vigor, la
cadena llega, y no hay nada en el documento que lo delate.

Que la lista estuviera vencida se comprobaba **solo al montarla**. Después no
se volvía a mirar nunca. Mientras las anclas se las instala quien valida eso
casi se nota, porque las montó él; en cuanto un conjunto viaja con una
herramienta, quien la usa no eligió nada y no tiene forma de enterarse.

Así que ahora se mira en tres sitios, y los tres hacen falta:

- Al **empaquetar**, negándose, porque quien arma el paquete es quien puede
  arreglarlo con una orden.
- En **cada informe**, como aviso —no como error: la firma es la que dice ser,
  lo que no se puede afirmar es que la autoridad siga cualificada hoy—.
- En **la página**, en un recuadro que dice qué trae, de qué lista sale, de
  cuándo es y cuándo toca renovarla.

Y cuando el paquete no está, el recuadro dice lo que deja de mirarse:

```
Esquemas XSD              no están
Anclas de confianza       no están
Entonces no se comprueba  la forma ni de quién es el certificado
Para arreglarlo           python -m validador --empaquetar
```

El informe de cada factura dice además que las anclas **vienen con la página**.
Que salgan de la lista del Estado es verdad y no es suficiente: lo que quien
valida aquí no puede saber es que no las ha elegido él.

### Y el agujero que apareció al no tener red

Con el paquete puesto, la primera factura Facturae que pasó por el navegador
contestó esto:

```
[XSD-ESQUEMA-ROTO] No se ha comprobado la forma: el esquema que le toca a este
documento está ahí pero no se puede leer. Suele ser una descarga a medias;
vuelve a bajarlo.
```

El fichero estaba entero. Lo que pasa es que los cinco XSD de Facturae importan
la firma XMLDSig **por dirección web**, en su tercera línea:

```xml
<xs:import namespace="http://www.w3.org/2000/09/xmldsig#"
  schemaLocation="http://www.w3.org/TR/xmldsig-core/xmldsig-core-schema.xsd"/>
```

El parser de `formato.py` lleva `no_network=True` desde el principio, con un
comentario que dice que un fichero de fuera no debe poder hacer peticiones
salientes. Eso vale para **leer el documento**. Compilar un esquema lo hace
libxml2 por su cuenta y se saltaba el parser: comprobar la forma de una factura
del formato nacional se bajaba un fichero de w3.org **cada vez**, y eso no
estaba escrito en ninguna parte.

No se veía porque funcionaba. Se ve donde no hay red. Confirmado aquí fuera
apuntando el proxy a un puerto muerto:

```
con proxy muerto -> FALLA: The QName value 'Signature' does not resolve
                    to a(n) element declaration., line 35
```

Los cinco de Facturae fallan; UBL y CII no, porque sus importaciones son
relativas. Ahora se resuelve con la copia de XMLDSig que trae el paquete de UBL
—mismo `targetNamespace`, mismo `Signature`—, sin bajar nada nuevo, y el
resolvedor **se niega** a ir a buscar cualquier otra dirección de fuera en vez
de dejar que libxml2 la baje. Cuando no hay copia local se dice la causa de
verdad, en vez de mandar a rebajar un fichero que está perfectamente.

La comprobación que lo prueba solo puede hacerse en el navegador, que es el
único sitio donde «sin red» no es una opción sino un hecho.

## El CIUS español, que no es UBL a secas

El RD 238/2026 admite cuatro sintaxis. La solución pública de la AEAT admite
**una**, y ni siquiera es UBL sin más: la respuesta de la Agencia en su
seminario del 19-05-2026 fue *«La SPFE solo admitirá facturas compatibles con
UBL 2.5 de acuerdo a la semántica europea EN16931 y ajustadas al contenido
mínimo del Anexo I»*. Ese anexo, el borrador de abril, define un CIUS español
propio, `urn:aeat.es:CIUS-ES-SPFE:1.0.0`, sobre la edición de 2026 de la norma.

**Lo que se cuenta de aquí a «Que no cambie en silencio» es, sobre todo, la
lectura de ese borrador**, que es de donde salió `validador/cius_es.py` hasta
el 11-10-2026. El anexo que rige desde el 06-10-2026 es el de la Orden
HAC/1028/2026, publicada en el BOE el 05-10-2026: declara otro identificador,
`urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:1.0.0:extended`, numera
de otra manera sus campos españoles y ya no da grupo propio al recargo de
equivalencia ni al grupo de entidades. Desde el 11-10-2026 `cius_es` sale del
XML del BOE y las reglas miden la orden: en «La orden en el BOE» y «La segunda
tanda», más abajo.

Lo que trae el borrador, contado: **174 filas, 155 identificadores distintos y
once listas de códigos**, de los cuales **52 son campos que la EN 16931 no
tiene** —el recargo de equivalencia, las retenciones, los suplidos, las
minoraciones, el régimen de grupo de entidades a nivel avanzado y el QR
fiscal—. Y no se publica como esquema ni como esquematrón: se publica como una
tabla dentro de un PDF. La orden tampoco trae esquema ni esquematrón, pero su
tabla viene también en el XML del BOE, que se lee sin coordenadas: 176 filas,
149 identificadores distintos y catorce listas.

Así que se leía el PDF, hasta el 11-10-2026: `herramientas/anexo_i.py` lo
sacaba a `validador/cius_es.py`, y no por columnas de texto sino por las
coordenadas de cada pieza, porque las columnas de texto mienten: `BT-179` sale partido en dos
renglones y el `21` de `BT-ES-21` aparece dentro de la columna del término. Un
parser que se fíe de eso da 174 filas plausibles y equivocadas.

### Cómo se sabe que la lectura es buena

Por dos caminos que no comparten una línea de código: las coordenadas, y una
expresión regular sobre el mismo PDF leído en plano. Los dos dan **el mismo
conjunto de 155 identificadores**, sin ninguno en uno y no en el otro. Los
recuentos brutos difieren y las dos diferencias están explicadas: sobran dos
menciones, que son las citas a `BT-179` y `BT-114` dentro de la descripción de
`BT-115`; y sobran cuatro cardinalidades, que son las de la introducción cuando
explica qué quiere decir `1..1`.

**Eso valía para la tabla, no para las listas**, y no se miró. Las listas de
códigos se leían también por coordenadas, y en cinco de las once —L3A, L3B,
L3C, L5 y L6— las descripciones salían corridas una fila: en una celda de dos
renglones el código va centrado entre los dos, y al repartir por altura el
primer renglón caía en el código de arriba. El 01 de L6 decía «País Vasco y
Navarra», que es justo lo que excluye. Los códigos estaban bien, y por eso no
saltó nada. Desde el 14-09-2026 las listas se leen en el orden en que el PDF
escribe el texto, que va por celdas, y una prueba compara descripciones
concretas contra el PDF. De paso salió lo que el extractor tiraba: debajo del
título de cada lista de claves de régimen va un «CALIFICADOR IVA», «IGIC» o
«IPSI», que es el valor de `BT-ES-44`.

### Dos cosas que el borrador hace mal

**El identificador no es una clave.** El anexo reutiliza a propósito unos
cuantos términos europeos como cajones para sus extensiones: `BG-34`, `BT-179`
y `BT-180` aparecen cinco veces cada uno, uno por grupo español. Lo que
distingue una fila de otra es su ruta UBL.

**Y hay un fallo de numeración**: `BT-ES-2` está puesto en dos términos que no
tienen nada que ver, «Identificador de la extensión para la gestión de facturas
rectificativas» y «Tipo de factura rectificativa». No es un fallo de
extracción: los dos métodos de lectura lo ven igual.

### Lo que esto obliga a corregir aquí

La lista L1 —los tipos de factura admitidos— es `380, 384, 388, 389, 471`, y
**no lleva el 381**. En España una rectificativa es siempre 384, o 471 si la
expide el destinatario; que rectifique por diferencias o por sustitución no se
dice en el BT-3 sino en `BT-ES-3`, con la lista L2.B (`I` o `S`).

`en16931.py` traduce hoy el `CorrectionMethod` 03 de Facturae a **381**, que es
correcto para la EN 16931 a secas y no vale dentro de este CIUS. Es decir: la
decisión que se documentó [más arriba](#bt-3-y-el-país-traducir-el-vocabulario-y-negarse-cuando-no-se-puede)
está bien razonada para la norma europea y hay que rehacerla para España. Sale
de leer el anexo cuatro días después de haberla escrito.

La otra diferencia está en la categoría de IVA, y aquí se contó al revés. Se
escribió que la lista L4 añade `L` y `M` —IGIC e IPSI— «que la UNCL5305 de la
norma europea no tiene». Sí las tiene: la lista que admite el esquematrón en
BR-CL-18 es `AE L M E S Z G O K B`, con reglas propias para las dos. Lo que
hace L4 es lo contrario, **quitar**: `S Z E AE O G L M`, sin `K` —la entrega
intracomunitaria— ni `B`. Corregido el 13-09-2026, el mismo día que la tabla del
IVA; las dos equivocaciones salían de la misma suposición.

### Las rutas UBL, y qué hay que hacerles para poder usarlas

De las 52 filas españolas, **50 traen su ruta UBL** —`BG-ES-4` y `BG-ES-34` se
quedan sin ella en el borrador— y son lo único que dice dónde se escribe cada
cosa: para los campos europeos el anexo deja la columna vacía, porque esos ya
los coloca el binding del CEN.

Están en `sintaxis.RUTAS_CIUS_ES`, y **no copiadas a mano**: se derivan de la
tabla al importar. Una tabla copiada se queda vieja el día que salga otro anexo
y no se entera nadie; una derivada cambia sola, y lo que se toca a mano es una
lista corta de excepciones con el porqué de cada una.

Tal y como vienen no se pueden evaluar. Hay que:

1. **Quitarles la raíz**, que viene absoluta: `/in:Invoice/…`.
2. **Arreglarles la caja.** Cinco de las cincuenta escriben `/in:invoice/` en
   minúscula. En XML eso no es estilo: es otro elemento, y no existe ninguno
   que se llame así.
3. **Deshacer el prefijo `aeat:`**, que el anexo usa en 26 pasos y **no declara
   en ninguna parte**. Esos pasos van por nombre local. No es elegante y es
   honrado: lo que identifica cada extensión no es su namespace sino el valor
   de su `ext:UBLExtension/cbc:ID`, y ese sí está publicado.

### Dieciséis campos que el anexo no distingue, y sí distingue

Seis rutas las comparten dieciséis campos —se escribió «diecisiete» hasta el
14-09-2026; ahora los cuenta una prueba—. Tal y como se publican, preguntar
por «la oficina destinataria» devuelve el órgano, y preguntar por «la
identificación de la retención» devuelve el suplido.

Pero el anexo **sí dice cómo se separan**: no en la columna de la ruta, sino en
la descripción de al lado.

| Rutas repartidas | Lo que las separa, dicho por el anexo |
|---|---|
| `BT-ES-9`, `BT-ES-10`, `BT-ES-11` | *«Atributos obligatorios: usar `schemeName="Organo"`»*, y «Unidad» y «Oficina» |
| `BT-ES-16`/`BT-ES-17` frente a `BT-ES-18`/`BT-ES-19` | *«Valor obligatorio: usar "false"»* en el descuento, *«"true"»* en el cargo |
| `BT-ES-40` y `BT-ES-41` | lo mismo, dentro de la línea |
| `BT-ES-20`, `BT-ES-21`, `BT-ES-27`, `BT-ES-31`, `BT-ES-32` | cada uno lleva su URN fijo: `…:SUPL`, `…:MINO`, `…:REEQ`, `…:REGE`, `…:RETE` |
| `BT-ES-43` y `BT-ES-44` | el nombre de la propiedad, que fija `BT-160`: *«Adoptará el valor fijo "RCAT"»* en la referencia catastral, *«"REGI"»* en la clave de régimen |

Así que el predicado se le añade a la ruta, y cada uno lleva apuntado **en qué
campo del anexo está escrito el valor**. Eso es lo que impide que esto se
convierta en opinión: hay una prueba que va a esa descripción y comprueba que
el literal sigue ahí. Si el anexo cambia de criterio, salta.

Después de eso no queda ninguna repartida, y `sintaxis.AMBIGUAS` está vacío.
Hasta el 14-09-2026 quedaban `BT-ES-43` y `BT-ES-44` —«situación del inmueble»
y «tipo de impuesto nacional», las dos en el `ValueQualifier` de un
`AdditionalItemProperty`—, declaradas con la frase «lo que las separaría es el
`cbc:Name` de esa propiedad, y el anexo no dice cuál». Lo dice, en la fila de
al lado: `BT-160`. Se leyó la ruta y no la fila.

### Dos rutas del anexo que no llevan a ninguna parte

Que una ruta compile como XPath no dice nada: `cac:Loquesea/cbc:Tal` compila
perfectamente. Lo que hay que comprobar es que **exista donde la ruta dice**,
paso a paso desde `InvoiceType`, y eso se hace recorriendo el esquema de UBL
2.5. Con las cincuenta:

- **`cac:ThirdPartyInvoicing` no existe en UBL.** Ni en la 2.1 ni en la 2.5:
  cero apariciones en los 18 ficheros del paquete. Es la ruta de `BT-ES-15`, y
  el anexo se delata solo, porque la descripción de ese mismo campo dice que
  «ThirdPartyInvoicing» es el **valor** que hay que escribir en el código.
  Alguien lo pegó dentro del camino. Lo correcto es
  `cac:ServiceProviderParty/cbc:ServiceTypeCode`.
- **`BG-ES-1` no cuelga de donde dice.** El grupo escribe `aeat:Extension` y
  sus seis hijos escriben `aeat:InvoiceExtension`. Uno contra seis, y el resto
  del anexo sigue el mismo patrón —`aeat:CollectionInvoiceLineExtension` en
  `BT-ES-30`—, así que el raro es el padre.

Arregladas esas dos, **las cincuenta andan enteras**. Y la prueba que lo
comprueba mide también la de antes del arreglo, para que la corrección esté
sostenida por una medida y no por lo que parece.

### Por qué la SPFE no puede admitir UBL 2.1

Aquí se ve, y es una sola línea de la tabla: **trece de los campos españoles
cuelgan de `cac:CollectionInvoiceLine`** —suplidos, minoraciones, recargo de
equivalencia, régimen de grupo de entidades y la contraprestación de la
retención—, y ese elemento **no existe en UBL 2.1**. No es una preferencia de
la Agencia: en 2.1 no hay dónde escribirlos.

### El anexo solo habla de facturas

Las cincuenta rutas arrancan en `/in:Invoice/`, y la lista L1 **no admite el
381**, que es el código del abono en la EN 16931. En este CIUS una rectificativa
es un `Invoice` con el código 384. Así que aquí no se inventan rutas de
`CreditNote`: el día que el anexo las traiga, se derivarán solas.

### Que no cambie en silencio

Era un borrador cuando se escribió esto, y la AEAT había dicho que el anexo
*«se alineará plenamente»* con UBL 2.5; la orden salió en el BOE el 05-10-2026,
con el anexo cambiado (ver «La orden en el BOE», más abajo). Una tabla generada
de una fuente que se mueve es justo lo que en este repositorio se rompe sin
avisar, así que hay dos guardianes, los dos provocados: la **huella SHA-256 de
la fuente** (el PDF de abril hasta el 11-10-2026, el XML del BOE desde
entonces) va declarada en el módulo generado y una prueba la comprueba, y otra
vuelve a extraer y exige que salga exactamente lo mismo, por si alguien toca el
extractor y la tabla se queda vieja. Con el XML compara cada fila entera y
cada lista con sus descripciones: una frase cambiada en una fila la pone en
rojo (provocado el 11-10-2026).

Ni el PDF ni el XML se versionan, porque son de Hacienda. El XML se baja a
`anexos/orden-hac-1028-2026.xml`, y sin él las dos pruebas se saltan diciendo
por qué; en GitHub no está, y allí se saltan.

### Las reglas del anexo, y a quién se le aplican

Leído el anexo, `validador/solucion_publica.py` le pide a la factura lo que el
anexo pide. **32 códigos, todos con el prefijo `SPFE-`** y la etiqueta «Anexo
I» en el informe, que no es la del real decreto: es el anexo de la Orden
HAC/1028/2026. Hasta el 07-10-2026 decía «Anexo I (borrador)», y hasta el
11-10-2026 eran 24 y medían en buena parte el borrador de abril. Ese día
quedaron en 22 al ponerlos al texto de la orden, y llegaron a 32 con lo que la
orden pide y no se medía (en «La segunda tanda», «Lo que la orden pide y no se
medía», «Los impuestos y tasas, y la información de la línea» y «La
autorización, los ficheros embebidos y lo que se quitaba sin una queja», más
abajo) y con `SPFE-CALIFICADOR`, que sale de la respuesta del buzón del
13-10-2026 (en la sección de la consulta del 07-10-2026, más abajo), y con
`SPFE-GARANTIA` y `SPFE-CANJE`, dos notas del 19-10-2026 (en la lista de lo
que se comprueba, más abajo).

**Solo a las facturas UBL que declaran la solución pública** en su
`CustomizationID`: con el identificador de la orden, o con el CIUS del
borrador de abril, que se reconoce para decir en ERROR que ya no vale. Otro
identificador que nombre a la AEAT (`urn:aeat.es:`) recibe un AVISO,
`SPFE-ESPECIFICACION`, que dice que el anexo no se ha comprobado. El
anexo describe los campos en UBL y en nada más, y a qué corresponden en
Facturae, CII o EDIFACT no lo publica nadie —la Agencia contestó el 17-09-2026
que no le toca a ella, como se cuenta más abajo—: aplicarlo a otra sintaxis
sería inventarse esa correspondencia. Un documento de otra sintaxis que declare el
CIUS recibe `SPFE-SINTAXIS`, un aviso de que no se ha comprobado, que es
distinto de callar. Y una factura UBL que no lo declara no se mide con el
anexo: quien emite para Peppol o para una plataforma privada no se ha
comprometido con este CIUS. Quien lo declara sí acepta sus listas, y con ellas
se le mide.

Lo que se comprueba:

| Qué | Códigos |
|---|---|
| La cabecera: el identificador de la orden en `BT-24`, su proceso `B2B` en `BT-23`, el que no lleva `ubl:` (el del BOE, que lo lleva, en AVISO desde el 13-10-2026), el tipo de factura de L1, el euro como moneda del IVA y la fecha efectiva de pago (`BT-ES-2`), una como mucho y del día de la operación al de la expedición; y, en notas, la factura sin indicador de copia, el importe pagado y la fecha de pago que no se puede comparar o que no libera de comunicar el pago | `SPFE-ESPECIFICACION`, `-PROCESO`, `-TIPO-DE-FACTURA`, `-MONEDA-DEL-IVA`, `-FECHA-DE-PAGO`, `-COPIA`, `-IMPORTE-PAGADO` |
| Los datos de la rectificativa en toda 384 y 471: un `BG-24` `RECT:TIPO` y uno `RECT:MODALIDAD`, con su código en `cbc:DocumentTypeCode`, de L2.A y L2.B; y, si los lleva, los `RECT:IMPORTES`, cada uno con su código de L2.C y su importe: más de cinco es ERROR, un código repetido un AVISO (`BT-3` dice hasta tres, el grupo es `0..5` en el BOE y `0..1` en el anexo corregido que mandó la AEAT el 13-10-2026, con un ejemplo de uno por código), y con la modalidad `I`, un AVISO, porque el grupo es para la sustitución | `SPFE-RECTIFICATIVA` |
| Las partes: el NIF de las dos en un esquema «VAT», con el prefijo ES, o en uno «LOC» con «FC», y en ese caso el registro legal del vendedor (`BT-30`), que tiene que ser su NIF; la dirección entera cuando está en España; y el tercero que expide la factura, con su razón social, su NIF y su tipología. El prefijo del comprador va en ERROR, como el del vendedor: su fila dice NIF del vendedor, y la AEAT contestó el 13-10-2026 que es una errata de la descripción; hasta ese día iba en AVISO | `SPFE-NIF`, `-DIRECCION`, `-TERCERO` |
| Lo que la norma deja opcional y el anexo no: la fecha de la factura referenciada y el motivo en texto de descuentos y cargos | `SPFE-FACTURA-REFERENCIADA`, `-MOTIVO` |
| El IVA: «VAT» en los descuentos y cargos, las líneas y el desglose, y que esté; la categoría de L4, sin `K` ni `B`; el tipo también en la entrada no sujeta (`O`), que la norma deja sin él; el código de exención, solo VATEX-EU o VATEX-ES; y la `N`, la `D` y la `F` de la orden, en una nota | `SPFE-TIPO-DE-IMPUESTO`, `-CATEGORIA`, `-TIPO-DE-IVA`, `-EXENCION` |
| Cada línea: una o dos claves de régimen en la lista de su impuesto (la L3A de la orden ya no tiene la 18, la 19 ni la 20), como mucho una referencia catastral con su situación de L6, y ninguna otra propiedad del artículo que la información adicional, `INFO` (en AVISO) | `SPFE-CLAVE-DE-REGIMEN`, `-REFERENCIA-CATASTRAL`, `-INFORMACION-ADICIONAL` |
| Los impuestos y tasas que no son el IVA: el código de L9 en cada cargo de línea y en cada impuesto cobrado como cargo del documento, con su cuota en el impuesto y en el total del cargo, y la misma; el desglose del que se cobra en nombre de un tercero, con «VAT» y «S»; y la cuota de cada uno, la base por el tipo con el margen de la del IVA. Con dos impuestos en un cargo, una nota; y un cargo con el total del impuesto y sin su detalle no dice qué impuesto es | `SPFE-IMPUESTO-O-TASA` |
| Las líneas de cobro: un valor de la L7 de la orden, con su calificador delante (sin él, lo dice `SPFE-CALIFICADOR`), y un solo grupo de retenciones; las retenciones con su suma, su línea de cobro y su concepto de L5, y sus dos cuentas: cada una es su base por su porcentaje, y la suma es la de todas, y si no se detalla ninguna, una nota; y el QR fiscal, uno como mucho, con su dirección y, si lleva descripción, VERIFACTU o TICKETBAI (el escrito con la URN de abril no es el QR, y una nota lo dice) | `SPFE-LINEA-DE-COBRO`, `-RETENCION`, `-QR` |
| La dirección del QR (`BT-ES-25`) contra la factura: el NIF, la serie y el número, la fecha y el importe, y en TicketBAI sus dos CRC; una dirección que no es de la AEAT ni de una hacienda foral, y el entorno de pruebas de la AEAT. Todo en AVISO; en otra moneda que el euro el importe no se compara, y una nota lo dice | `SPFE-QR-URL` |
| La autorización de facturación: cada `BG-24` `AUT`, los que haya, con su número (`BT-ES-26`) | `SPFE-AUTORIZACION` |
| Los valores de L7, L8 y L10 con el calificador de su lista delante, como contestó la AEAT el 13-10-2026: sin él, un AVISO por factura con todos los que lo llevan solo. Se siguen reconociendo de las dos formas, para medir lo demás | `SPFE-CALIFICADOR` |
| Ningún fichero dentro de la factura, ni en la original ni en la copia fiel, que no lo dice el anexo sino los artículos 3 y 4 de la orden; la firma vale en la original, y en la copia fiel es un aviso | `SPFE-FICHERO-EMBEBIDO` |

Y dos notas: `SPFE-ALCANCE`, que sale en cada factura que se mide con el
anexo y dice con qué se ha medido y, por su nombre, lo que no se puede
comprobar (`NO_SE_COMPRUEBA`, cuyo porqué copia la ficha de la nota); si
algún día la orden pide algo que aquí todavía no se mide, va en
`LO_QUE_TODAVIA_NO_SE_MIDE`, vacía desde el 11-10-2026, y la nota y el
glosario lo dicen letra a letra, porque que no salga ninguna queja no
quiere decir que cumpla la orden; y `SPFE-TOTAL-A-PAGAR`, que sale cuando hay
líneas de cobro y es lo que sigue (con retenciones solas, en AVISO si el
total no cuadra). Un abono que declara la orden no recibe
`SPFE-ALCANCE`: no se le mide con el anexo, y `SPFE-TIPO-DE-FACTURA` ya lo
dice.

**Una regla europea que daba por mala una factura bien hecha.** El anexo dice
que el total a pagar suma «los importes correspondientes a los conceptos
BT-179» junto con el total con IVA. En la orden, `BT-179` es el importe de
cada grupo `BG-34`: los suplidos (`SUPL`), los impuestos y tasas cobrados en
nombre de un tercero, como el IEDMT (`IEDMT` y `OTROS`), las minoraciones
(`MINO`) y las retenciones (`RETE`). Hasta el 07-10-2026 esta lista era la
del borrador: suplidos, minoraciones, recargo y retenciones; y hasta el
11-10-2026 se aceptaban además las dos líneas de abril que la orden ya no
tiene, el recargo de equivalencia (`REEQ`) y el grupo de entidades (`REGE`),
que ahora son ERROR.
BR-CO-16, que es de la edición de 2017, no conoce esos importes: medido el
14-09-2026, una
factura del CIUS con un suplido de 50 euros sumado como manda el anexo salía
con BR-CO-16 en error. Y esos importes no se pueden sumar aquí, porque ni el
borrador ni la orden dicen dónde se escriben: son `BT-179`, un término de la
edición de 2026 sin ruta. Así que con líneas de cobro la nota dice que el
cuadre no se ha comprobado, y BR-CO-16 no sale. Sin líneas de cobro se
comprueba como siempre.

**Las retenciones sí tienen cifra, desde el 19-10-2026.** La orden define el
`BT-179` de su grupo y `BT-ES-17` con la misma frase ("sumatorio de todas las
retenciones practicadas en factura"), y `BT-ES-17` tiene ruta. Así que, si las
únicas líneas de cobro son retenciones, el total a pagar se cuadra: total con
IVA, menos lo pagado, más el redondeo, menos lo retenido. La orden no escribe
el signo ("junto con"), y se resta porque eso es una retención y porque
Facturae hace lo mismo (`TotalExecutableAmount`); por no estar escrito, lo que
no cuadra es un AVISO y no un ERROR, y si el total es justo el que saldría sin
restar, lo dice. Con suplidos, minoraciones o impuestos y tasas se queda la
nota: su importe no tiene ruta o el desglose es opcional, y medio cuadre sería
un aviso falso. Medido antes del arreglo: una factura de 121,00 con su
retención y 500,00 a pagar salía con la nota y sin una queja, con IRPF y con
la retención de concepto 11, que es como cabe la retención de garantía de una
obra. Las pruebas usan la factura de la orden de las pruebas, que escribió el
proyecto: el ejemplo de la AEAT no trae totales. Cuatro roturas provocadas (el
signo, la condición de solo retenciones, la frase de la retención olvidada y
la gravedad) ponen en rojo su prueba.

**Qué sale del anexo y qué no.** Las rutas de los campos españoles vienen de
`RUTAS_CIUS_ES`, y las de dentro de un grupo se piden relativas a él. Los
valores fijos —los URN, «VAT», «S», «WTH», «EUR»— se leen de la descripción de
su fila. Y cada campo que se exige tiene que ser obligatorio en la tabla. Todo
eso se comprueba **al importar**: si un anexo nuevo relaja un campo, cambia un
valor o mueve una ruta, el módulo lanza `AnexoCambiado` y no se monta. Las tres
formas están provocadas en las pruebas; la de la ruta, en un proceso aparte,
porque las rutas las calcula `sintaxis` al importarse y recargarlo en mitad de
la suite estropea a los demás módulos. Hasta el 11-10-2026 de esa se probaba
solo el trozo que se niega (en HALLAZGOS).

Los campos que la norma ya tiene no traen ruta en el anexo, ni en el borrador
ni en la orden —remiten a la vinculación de 2026, la
`UNE-CEN/TS 16931-3-2:2026`, que es de pago y aquí no se ha podido leer— y
van por la de 2017. Que esos elementos existen en UBL 2.5 donde se buscan está
comprobado contra el esquema; que la vinculación de 2026 los use para lo mismo
no se sabrá sin leerla.

**Lo que no se comprueba** está en `NO_SE_COMPRUEBA`, con el porqué. Entre
otras cosas: el importe y la descripción de los cobros (`BT-179`, `BT-180`),
que la orden tampoco ubica, y todo lo que depende de ellos; la restricción de
`BT-195` a VATEX-EU y VATEX-ES; que la tipología del tercero sea
«FacturaciónPorTercero» —«ThirdPartyInvoicing» en el borrador—, obligatoria en
un caso que no se ve en el documento; y las especificaciones técnicas que la
orden deja a la Sede electrónica de la Agencia. Lo que la orden pide y aquí
todavía no se mide, aunque se podría, no va ahí sino en
`LO_QUE_TODAVIA_NO_SE_MIDE`, que desde el 11-10-2026 está vacía: lo último
fue el número de la autorización de facturación. La nota `SPFE-ALCANCE`
nombra lo que no se comprueba en cada factura, y su ficha dice el porqué de
cada cosa. Hasta el 11-10-2026 la primera no
llegaba al informe, y la portada y la política de privacidad dicen que lo que
no se mide lo dice el informe (en HALLAZGOS).

**No hay facturas de verdad con las que medir.** La solución pública no está en
marcha y en el corpus hay cero documentos que declaren el CIUS. Las pruebas
van sobre una factura escrita al pie de la letra de la orden y veintinueve
variantes (la rectificativa, el tercero, los cobros, las categorías `N`, `D`,
`F`, `O` y `E`, la autorización, la fecha de la operación, los impuestos y
tasas, la información adicional, un documento por su dirección, la firma en
un fichero), que pasan **el validador entero** sin un
error ni un aviso: forma contra UBL 2.5, norma europea, código único y anexo. La forma,
con los esquemas de `web/paquete.zip`: la suite corre sin esquemas, y hasta el
11-10-2026 esto lo decía sin que se mirara (en HALLAZGOS). De ahí se rompe
cada regla. Hasta el 11-10-2026 la de partida era una escrita con el
borrador de abril; lo que solo decía el borrador se prueba ahora aparte, para
ver que sale en ERROR. Provocado al escribir el módulo: 37 roturas, las 37 en
rojo; al ponerlo al texto de la orden, catorce más (diez y una frase de la
tabla en la primera tanda, tres en la segunda), en la revisión antes de
publicar, catorce y luego nueve, y con lo que la orden pide y no se medía,
dieciocho, diecisiete y diecinueve (en HALLAZGOS).

**La frase de alcance lo dice, y solo cuando toca.** «Sin errores» en una
factura del CIUS quiere decir también algo del anexo, así que la línea del
informe que dice qué se ha mirado lo añade cuando en el lote hay una factura
que lo declara: «parte de» lo que el anexo pide, «lo que se puede comprobar en
UBL», y que lo que no se mide lo dice la nota `SPFE-ALCANCE` (hasta el
11-10-2026, «lo que todavía no se mide», que es la lista que ese día se quedó
vacía). Hasta el 07-10-2026 decía «el borrador del anexo I», y «sin errores» quería decir que
cumplía el borrador; hasta el 11-10-2026, que se medía lo que ya pedía el
borrador. En un lote sin ninguna no lo dice. Y cuelga de la nota, no de lo que
el documento declara: un lote con solo un abono que declara la orden lo
contaba como medido.

### La dirección del QR, contra la factura

La orden pide en `BT-ES-25` "la URL correspondiente al QR VERI*FACTU o
TICKETBAI, según corresponda conforme normativa aplicable", y no dice más.
Hasta el 22-10-2026 aquí se miraba que estuviera, y nada de lo que decía: una
dirección con el NIF de otro, la fecha de otra factura o el servidor de pruebas
de la AEAT pasaba sin una palabra. Es lo que el receptor escanea para cotejar
la factura con Hacienda.

La forma de la dirección no está en la orden: la dan dos especificaciones, que
`validador/qr_fiscal.py` cita con su dirección y su huella SHA-256. Las copias
no se versionan.

- **VERI\*FACTU**, la especificación técnica del QR de la AEAT, versión 0.5.0
  de 10-12-2025. La dirección del servicio de cotejo, de producción
  (`www2.agenciatributaria.gob.es`) o de pruebas (`prewww2.aeat.es`), lleva
  "únicamente" cuatro parámetros: `nif`, `numserie`, `fecha` en DD-MM-AAAA e
  `importe` con punto decimal. Se comparan con el NIF del vendedor, `BT-1`,
  `BT-2` y `BT-112`. El idioma y el formato los admite el servicio, pero no el
  QR, y del formato la especificación dice que "nunca podrá incorporarse".
- **TicketBAI**, la especificación de 2020, versión 1.1. El identificador
  `TBAI-NIF-DDMMAA-firma-CRC` lleva el NIF y la fecha, y la dirección la serie
  (`s`), el número (`nf`), el importe con IVA (`i`) y, la última, su CRC-8
  (`cr`). Los dos CRC se recalculan, con el algoritmo de su anexo 3 y
  comprobado con sus dos ejemplos. La serie y el número, juntos, son `BT-1`,
  como contestó el buzón el 13-10-2026.

Tres decisiones:

- **Todo es AVISO.** La orden no copia esas especificaciones en su anexo, y el
  validador no sabe qué sistema de facturación usó el emisor.
- **En otra moneda el importe no se compara.** Las especificaciones dicen
  "importe total de la factura" y no dicen en qué moneda; una nota lo dice.
- **Araba tiene dos direcciones.** La especificación de 2020 da
  `https://ticketbai.araba.eus/TBAI/QRTBAI`, sin barra final, y el anexo V de su
  orden foral `https://ticketbai.araba.eus/tbai/qrtbai/`, con ella. Se aceptan
  las dos. El CRC se calcula sobre la dirección tal cual va, así que no depende
  de cuál se elija.

Lo que no se hace: validar el registro de VERI\*FACTU ni su encadenamiento, ni
preguntar a la AEAT si la factura está registrada. Eso pide red y el registro,
que no viaja con la factura. Tampoco se publica una dirección de pruebas de
TicketBAI, porque ninguna de las dos especificaciones la da: una dirección que
no es de las publicadas sale como tal, sin comparar sus datos.

### Lo que contestó la Agencia, y lo que dejó abierto

La pregunta de arriba —qué le corresponde en Facturae, CII o EDIFACT a cada
campo del anexo— se le hizo por escrito al buzón técnico de la AEAT el
**10-09-2026**, con acuse el 11 y respuesta el **17-09-2026**. Tres preguntas,
tres respuestas, y es la única fuente directa de la Agencia que hay aquí:

| Se preguntó | Contestó |
|---|---|
| Si la Agencia piensa publicar la correspondencia entre Facturae 3.2.2, CII y EDIFACT INVOIC y los elementos del anexo I, o si recae en cada plataforma al amparo del artículo 7.2 | Que «cae en la responsabilidad de las plataformas privadas, o en su caso, de la definición por parte del Ministerio de Economía que regula la interconexión entre plataformas privadas y sus formatos» |
| Qué hacer en la copia fiel del artículo 4.2 con un concepto del original que no tiene equivalente en la sintaxis de la solución pública: omitirlo o recogerlo en una extensión | Que «se pueden omitir o incluirlos en una extensión», y que «si el concepto del original no es equivalente, no se realizará la validación del dato» |
| Si los documentos de validación del portal de desarrolladores cubrirán las extensiones propias del anexo I o solo las reglas de negocio de la EN 16931 | Que «cubrirán principalmente las personalizaciones realizadas en el anexo I» |

**Lo que cambia aquí es una frase, no una comprobación.** Hasta ese día el
validador decía que no constaba publicada esa correspondencia, que es lo único
que se puede sostener mirando lo que hay. Ahora consta que quien podría
publicarla ha dicho que no lo hará, y `SPFE-SINTAXIS` lo dice con fecha. El
aviso sigue saliendo igual: una correspondencia que cada plataforma escriba
para sí misma no es una que este validador pueda dar por buena.

**Lo de la copia fiel es una decisión de diseño que se gana por adelantado.**
El día que se mida una copia fiel, que le falte un concepto del original no
puede ser un error: la propia Agencia dice que se puede omitir. Y tampoco puede
serlo un dato que viaje en una extensión.

**Y los documentos del portal son el contraste que hoy no existe.** Las
reglas `SPFE-` salen de leer una tabla, la de la orden desde el 11-10-2026
(hasta entonces, en buena parte, la de un borrador), y una tabla que se lee no
es algo con qué comparar lo leído. Cuando se publiquen esos
documentos habrá por fin con qué, y cubren justo lo español. Por eso el portal
de desarrolladores entra en la vigilancia mensual de las fuentes.

**Dos cosas que hay que leer con cuidado, porque no las dice la respuesta.** La
primera: la lista de normas que adjunta llama «Facturae» a
`UNE-CEN/TS 16931-3-4:2026`, cuyo título propio —el que la respuesta copia a
continuación— es el de UN/EDIFACT. **Facturae sigue sin ninguna parte CEN**, que
es exactamente lo que sostiene que el mapa de `SINTAXIS_FACTURAE` esté escrito
aquí y sus decisiones sean de esta casa. Es además el envoltorio desatendido de
siempre, ahora dentro de la respuesta de la Agencia: esa portada dice `D16B` y
la revisión de 2026 mapea `D.24A S4`. La segunda: lo que remite es la semántica
europea —`16931-3-2` para UBL, `-3-3` para CII y `-3-4` para EDIFACT,
ratificadas por UNE en septiembre de 2026 y de pago—, y esas partes mapean la
EN 16931, no los campos españoles del anexo. Lo preguntado sigue sin existir.

Lo que la respuesta no toca, porque no estaba preguntado: a qué edición de la
EN 16931 apunta el artículo 7.1, y si el anexo mantendrá el 381 fuera de L1 y la
`K` fuera de L4. **Las dos se preguntaron después, y las dos están contestadas.**
La edición, el 22-09-2026: son las de 2026, y para todo el sistema. El 381 y la
`K`, el 23-09-2026, y siguen fuera: «no se aceptan InvoiceType de tipo 381 en
L1. Tampoco se aceptará la categoría K en L4». Con eso el precio deja de ser
una deducción de esta casa y pasa a ser una cita: una factura válida según la
EN 16931 —el 381 es el tipo con el que media Europa emite un abono, y la `K` es
la categoría de las entregas intracomunitarias— no pasa el anexo español. La
Agencia añadía que **eleva la cuestión a gestión para que reevalúen el
criterio**, así que quedó confirmado y vivo a la vez, y por eso se aparcaron
aquí el `BT-3`/381 y la L4. La orden publicada el 05-10-2026 deja las dos
listas como estaban —su L1 no tiene el 381 y su L4 no tiene la `K`—, así que
cambiarlo pediría ya otra orden. Qué se hace con lo aparcado está por decidir.

### El anexo cambió antes que el texto

Este apartado se empezó el 17-09-2026, con el texto nuevo sin publicar. Salió
en el BOE el 05-10-2026, y lo que se hizo entonces está en «La orden en el
BOE, y la primera tanda», más abajo. Hasta el 07-10-2026 este apartado se
titulaba «El anexo ya cambió, y el texto no está publicado»; la columna de la
derecha de la tabla está al día, y el resto es cómo se llegó.

Mirando el portal de entidades desarrolladoras el **17-09-2026** —se fue a
buscar dónde saldrán esos documentos de validación— apareció otra cosa: un
**seminario del 10-09-2026** con tres presentaciones, y una se titula
«Principales novedades anexo I». O sea que el anexo sobre el que estaban
escritas las 24 reglas `SPFE-` **ya no era el último**, la orden se quería en
vigor el **01-10-2026**, y el texto nuevo no estaba publicado: solo había
transparencias.

Es el fallo de siempre de esta casa con otro disfraz. La vigilancia mensual de
las fuentes miraba la huella del PDF del anexo, y esa huella no había cambiado
—porque lo que hay de nuevo es **otro documento en otro sitio**—. La fuente
seguía verde y el contenido estaba viejo.

Lo anunciado, y a qué regla le da:

| Novedad del 10-09-2026 | Qué pasa aquí hoy |
|---|---|
| La extensión de rectificativas **desaparece**: se usa `BG-24`, con L10 para el uso y las L2 para tipo, modalidad e importe | **Confirmado por escrito el 22-09-2026**. L10 entera —`QR`, `AUT`, `RECT:TIPO`, `RECT:MODALIDAD`, `RECT:IMPORTES`— la repitió el correo del **23**, pero ya estaba en la diapositiva 8 de este seminario, como imagen, y no se vio hasta el 05-10-2026. `SPFE-RECTIFICATIVA` ya no exige la extensión y **reconoce** los calificadores: dice cuáles hay y cuál falta, en una NOTA. Desde el ejemplo del **02-10-2026** comprueba también el **valor**, en `cbc:DocumentTypeCode`, y avisa del que no está en su L2 (ver «El ejemplo del 02-10-2026», abajo). La orden lo confirma: no tiene extensión de rectificativas. Desde el 11-10-2026 todo esto sale en ERROR, y la extensión de abril ya no cuenta |
| El indicador de copia pasa a `0..1` | Confirmado por la orden. Desde el 07-10-2026, `SPFE-COPIA` es una NOTA |
| El **389** para la factura expedida por el destinatario, junto al 471: «La expedición de facturas por el destinatario o por tercero está plenamente contemplada en el Anexo I» | No es nuevo: la L1 de abril ya lo trae, y aquí se escribió que entraba. La de la orden es la misma, `380, 384, 388, 389, 471`, y `SPFE-TIPO-DE-FACTURA` mide con ella |
| El NIF del vendedor va en `BT-31` o en `BT-32`, este con esquema «LOC» y `@schemeID` «FC» | Confirmado por la orden. Desde el 07-10-2026, `SPFE-NIF` admite las dos formas |
| L4 gana las categorías de la EN 16931:2026, entre ellas la `N`; y se han pedido códigos VATEX propios de España | La L4 de la orden trae la `N`, la `D` y la `F`. Desde el 07-10-2026 se aceptan en las facturas de la solución pública, con una NOTA |
| L3A se recorta: fuera el recargo de equivalencia, el de agricultura, ganadería y pesca y el simplificado | Confirmado por la orden: sin la 18, la 19 ni la 20. `SPFE-CLAVE-DE-REGIMEN` las dio por buenas hasta el 11-10-2026; desde entonces, ERROR |
| `BG-34` (`BT-179`, `BT-180`) se usa para el IEDMT | Confirmado por la orden: el grupo «IMPUESTOS Y TASAS», con `IEDMT` u `OTROS` en `cac:CollectionInvoiceLine/cbc:ID`. Desde el 07-10-2026, `SPFE-LINEA-DE-COBRO` acepta los dos. `BT-179` y `BT-180` siguen en `NO_SE_COMPRUEBA`: son términos de la edición de 2026 y la orden tampoco les da ruta UBL |
| Mensaje de anulación de factura, un `ApplicationResponse` de UBL | Documento nuevo. Desde el 29-09-2026 **se reconoce y se le mide la forma y la firma**, y desde el 12-10-2026 también su tabla del anexo I de la orden (ver «Los mensajes de la orden: la anulación y los ocho estados») |

**No se tocó ni una regla, y fue a propósito.** Unas transparencias no son
un texto normativo: dicen qué va a cambiar, no cómo queda redactado. Reescribir
24 reglas sobre ocho viñetas es exactamente lo que este repositorio no hace. Lo
que sí se hizo fue **decirlo donde se ve**: la NOTA `SPFE-BORRADOR` que lleva
cada factura medida decía, hasta el 07-10-2026, que el anexo cambió el
10-09-2026 y que el texto no estaba publicado, así que alguna regla podía
haber quedado vieja; desde ese día dijo que el anexo es el de la orden y qué
se había puesto ya al día, y desde el 11-10-2026 se llama `SPFE-ALCANCE` y
dice qué de la orden falta por medir. La lista de arriba vivió también en la
cabecera de `validador/solucion_publica.py`, como lo que había que revisar el
día que saliera el texto. Salió, se revisó, y la cabecera cuenta ahora qué
cambió en cada paso.

**Y una cosa que la tercera presentación deja escrita.** La técnica, del
Departamento de Informática Tributaria, dice contra qué valida la solución
pública: `UNE-EN 16931-1:2026`, la de junio, y `UNE-CEN/TS 16931-3-2:2026`, la
de septiembre. Es la **edición de 2026**, la misma pregunta que quedó abierta
en `HALLAZGOS.md` al discutir a qué edición apunta el artículo 7.1. **Desde el
22-09-2026 ya no está abierta**: preguntado el buzón, contesta que esas dos son
las versiones ratificadas aplicables «al sistema español de facturación
electrónica en su conjunto», y nombra los tres casos —la SPFE, el envío de
copias fieles y el intercambio privado del artículo 7.1—. Sigue sin ser el
boletín, que es la cautela que hay escrita allí, pero ya no es una
transparencia de la solución pública: es la Agencia contestando por escrito por
el sistema entero. La misma presentación dice que los documentos de validación, el
catálogo de servicios y los WSDL se publicarán en ese portal antes de que haya
entorno de pruebas, con octubre de 2026 como referencia. Por eso el portal
entra ahora en la vigilancia mensual.

### El ejemplo del 02-10-2026, y dos identificadores que nadie explicó

El 23-09-2026 se le preguntaron al buzón tres cosas de L10: si su esquema lleva
`ubl:`, en qué campo del `BG-24` va el valor del calificador y dónde va el
número de la autorización. La respuesta llegó el **02-10-2026** y es toda ella
una captura de un XML de ejemplo, sin una frase de criterio: una cabecera y
cuatro `AdditionalDocumentReference`, sin partes, totales ni líneas. Contesta
las tres:

| Se preguntó | Lo que enseña el ejemplo |
|---|---|
| Si el esquema de L10 lleva `ubl:` | No, en los cuatro calificadores, el del QR incluido: `urn:aeat:names:specification:schema:QR` |
| En qué campo va el valor | En `cbc:DocumentTypeCode`: `R1` en `RECT:TIPO`, `S` en `RECT:MODALIDAD`. La descripción lleva un texto libre |
| Dónde va el número de la autorización | En `cbc:UUID`, como la dirección del QR. El calificador ocupa el `cbc:ID` |

Aquí se había apostado por la descripción, por analogía con el QR, y no se
programó porque razonable no es publicado. Fue lo correcto: programado, hoy
daría por malas las facturas escritas como enseña la Agencia.

**Y trae dos cosas que no se preguntaron.** Otro `CustomizationID`,
`urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:1.0.0:extended`, y otro
`ProfileID`, `urn:aeat:names:specification:schema:profile:B2B`. Ninguno es el
del anexo de abril, y el correo no explica el cambio. En la práctica de la
EN 16931, `#compliant#` marca un CIUS y `#conformant#` una extensión; si va en
serio, la AEAT declara su formato como extensión. Es inferencia: el texto de la
norma que lo define no se ha podido leer. Iba en serio con el primero: la
orden, tres días después, fija en `BT-24` ese mismo identificador, letra a
letra. El segundo no: en `BT-23` pone
`urn:aeat:names:specification:ubl:schema:profile:B2B`, con `ubl:`.

Medido el 05-10-2026 sobre `main`, antes de tocar nada: con el identificador
del ejemplo **no se aplicaba ni una regla del anexo y nada lo decía**, se le
suponía UBL 2.1 por no llevar `UBLVersionID`, el QR escrito sin `ubl:` no era
el QR y la autorización no se reconocía. Una rectificativa que no dice qué
rectifica salía «sin errores». Es el fallo de siempre, esta vez con el disfraz
de un ejemplo de la propia Agencia. El detalle está en `HALLAZGOS.md`.

Lo que se hizo, sin ninguna regla nueva que dé ERROR:

| Qué | Cómo sale |
|---|---|
| El identificador del ejemplo | Se reconoce por el valor entero y se mide con el anexo. Hasta el 07-10-2026 se medía con el de abril y `SPFE-ESPECIFICACION` lo decía en una NOTA; desde ese día no sale nota, porque es el de la orden |
| Otro identificador que nombre a la AEAT (`urn:aeat.es:`) y no lleve `CIUS-ES-SPFE` | `SPFE-ESPECIFICACION` como AVISO, y no se le aplica el anexo. La forma y la norma europea se miden como siempre, así que con líneas de cobro sale `BR-CO-16`, que solo se quita cuando se mide con el anexo. Si lleva `CIUS-ES-SPFE`, es otra versión del CIUS y sale ERROR, como antes |
| Sin `UBLVersionID` | Se supone UBL 2.5 con cualquier identificador de la AEAT, y no solo con el de abril |
| El `ProfileID` del ejemplo | `SPFE-PROCESO` como NOTA, con cualquiera de los dos identificadores |
| `QR` y `AUT` | Se reconocen con y sin `ubl:`, sin mirar los espacios de alrededor del identificador, y ninguno de los dos cuenta como dato de la rectificativa |
| `RECT:TIPO` y `RECT:MODALIDAD` | El código se lee en `cbc:DocumentTypeCode` y se compara con L2.A y L2.B: el que está se dice comprobado, y el que no, AVISO. Si un calificador viene repetido se leen todos, y la nota lo dice |

**Lo que sí cambia de gravedad, y hay que decirlo.** Ninguna regla nueva da
ERROR, pero lo que antes se colaba por no reconocerse recibe ahora los ERROR
que ya existían:

- **Todo el anexo, con el identificador del ejemplo.** Antes no se le aplicaba
  ninguna regla `SPFE-`; ahora todas. Una factura así sin `ProfileID`, con el
  tipo 381, escrita como `CreditNote` o con la moneda del IVA en dólares da el
  ERROR de su regla, y una 384 que no dice qué rectifica, el de
  `SPFE-RECTIFICATIVA`. Sin `CopyIndicator` o con el NIF en el esquema «LOC»
  también daba ERROR, hasta el 07-10-2026: desde ese día la falta de
  `CopyIndicator` es una NOTA y el NIF en «LOC» con «FC» se acepta, porque la
  orden admite las dos cosas. «LOC» sin «FC» sigue siendo ERROR.
- **Una 384 cuyo único `BG-24` es el QR escrito sin `ubl:`, o la
  autorización**, con cualquiera de los dos identificadores.
- **Un QR sin `ubl:` repetido, o sin dirección.** Sin descripción también,
  hasta el 07-10-2026: la orden la deja opcional (`BT-123`, `0..1`).
- **Un QR con espacios alrededor del identificador**, con o sin `ubl:`. Antes
  se buscaba por igualdad exacta y ahora se lee como los demás calificadores,
  sin esos espacios.

Antes salían limpios porque no se miraban, no porque estuvieran bien.

**Lo que no se hizo.** Un ejemplo no es el BOE, así que lo que enseñaba entró
como NOTA o AVISO. El texto salió en el BOE el 05-10-2026, y la negativa de L10
de `solucion_publica.py` salta el día que se regenere `cius_es` desde su XML,
que trae L10: es la tanda siguiente. Ese día el módulo no se dejaría importar
hasta confirmar el sitio del valor, exigir los importes cuando la modalidad es
S y pasar a ERROR lo que entonces no lo era. Se hizo el 11-10-2026: el sitio
del valor sale de las filas de la orden, lo que era NOTA o AVISO es ERROR, y
la modalidad S sin importes quedó en NOTA, porque la orden solo los prevé si
se optó por una única factura. Tampoco se resuelve la regla UBL-SR-43
del esquematrón de sintaxis de CEN, de la vinculación de 2017 y de nivel
fatal, que en un `AdditionalDocumentReference` solo admite el código 130 (o el
50 en un abono): `R1` y `S` la incumplen. Aquí no se cargan esas reglas, y si
la vinculación de 2026 la mantiene no se sabe; eso queda por preguntar. Se
preguntó, y el 13-10-2026 la AEAT contestó que se basa en la semántica de la
EN 16931, que no impone esa restricción: la solución pública no la aplica, y
aquí sigue sin cargarse. Las
otras dos cosas que quedaban las contesta la orden. Los importes rectificados,
que el ejemplo no enseñaba —es una S—: cada uno en su `BG-24`
`RECT:IMPORTES`, con el importe en `BT-123`, como texto, y su código de L2.C
(`Base`, `Cuota`, `CuotaRecargo`) en `cbc:DocumentTypeCode`. Se leen desde el
11-10-2026. Y si L7 pierde también el `ubl:`: sí, su calificador es
`urn:aeat:names:specification:schema:add:`.

**Y una lección de proceso.** La L10 sin `ubl:` ya estaba en la diapositiva 8
de «Principales novedades anexo I», la del 10-09-2026, como imagen: `pdftotext`
no saca las tablas que van en imagen, y nadie la vio. Las transparencias se
miran como imagen.

### La orden en el BOE, y la primera tanda: dejar de condenar

La Orden HAC/1028/2026 salió en el BOE del **05-10-2026** (BOE-A-2026-20587) y
está en vigor desde el día siguiente. El XML del BOE trae las tablas del anexo
enteras, sin PDF que leer por coordenadas. Bajado el 07-10-2026: el XML pesa
249.350 bytes, con SHA-256
`14bb2dad06a5ce3278c395232db9185f18052b08602cae472a9b2af3ae9c354a`, y el PDF,
963.876 bytes, con
`6384b2bb755404829f184fc18d7e2b99ce013436387ffed12ff4124ee99cd5d7`. Ninguno se
versiona.

Medido ese día sobre `6b4a165`, antes de tocar nada, con una factura escrita al
pie de la letra del anexo publicado —el proceso de la orden, sin indicador de
copia, el vendedor en `BT-32` con «LOC» y «FC», un anticipo pagado y la
retención con el calificador de L7—: **seis ERROR** de reglas `SPFE-` que la
orden ya no sostiene. Con variantes, más: el tercero escrito como la orden, el
comprador en `BT-47`, el QR sin descripción, la clave de régimen con el
calificador de L8, y la categoría `N`, que tumbaban `BR-CL-17` y `BR-CL-18` y
dos avisos de IVA.

| Lo que la orden admite | Antes | Ahora |
|---|---|---|
| El proceso `urn:aeat:names:specification:ubl:schema:profile:B2B` | `SPFE-PROCESO`, ERROR | Se acepta. El del ejemplo del 02-10-2026, sin `ubl:`, sale en una NOTA que dice que la orden fija otro |
| La especificación del ejemplo, que es letra a letra la de la orden | NOTA: «un ejemplo no es el BOE» | Sin nota |
| La factura sin `CopyIndicator` (`0..1`, «False (o sin informar): original») | `SPFE-COPIA`, ERROR | NOTA: la orden la toma por el original, y una copia fiel tiene que decirlo ahí (artículo 4, apartado 3) |
| Un importe pagado distinto de cero | `SPFE-IMPORTE-PAGADO`, ERROR | NOTA: lo que la orden prohíbe, un anticipo con el IVA devengado (artículo 75.Dos de la Ley del IVA), no se ve en la factura |
| El NIF con «LOC» y el atributo `schemeID` «FC», en `BT-32`, en `BT-47` y en el tercero | `SPFE-NIF` y `SPFE-TERCERO`, ERROR | Se acepta. «LOC» sin «FC», no |
| La L7 de la orden —`SUPL`, `MINO`, `RETE`, `IEDMT` y `OTROS`—, con su calificador `urn:aeat:names:specification:schema:add:` delante o sin él | `SPFE-LINEA-DE-COBRO` y `SPFE-RETENCION`, ERROR | Se aceptan, y la de abril también, todavía |
| El nombre del tercero en `cac:PartyLegalEntity/cbc:RegistrationName` | `SPFE-TERCERO`, ERROR | Se acepta, y en `cac:PartyName` también |
| El QR sin descripción (`BT-123`, `0..1`) | `SPFE-QR`, ERROR | Se acepta. La dirección sigue siendo obligatoria |
| La clave de régimen con el calificador de L8, `urn:aeat:names:specification:schema:lin:REGI` | `SPFE-CLAVE-DE-REGIMEN`, ERROR | Se acepta, y `REGI` a secas también |
| Las categorías `N`, `D` y `F` de la L4 | `BR-CL-17` y `BR-CL-18`, ERROR; `IVA-CATEGORIA-RARA` e `IVA-TIPO`, AVISO | `SPFE-CATEGORIA`, NOTA, y solo en las facturas de la solución pública: no en sus abonos, a los que no se mide con el anexo |
| La base de la `N` desligada de las líneas: el grupo de entidades la informa a coste (`BT-116`) y en la línea la contraprestación (`BT-131`), y el recargo de equivalencia va en el desglose sin línea propia; en la `D` y la `F` la base puede ser el margen | `IVA-BASE`, ERROR | No se compara con las líneas en la solución pública. `BR-CO-17`, la cuota con su base y su tipo, sigue |
| El registro del comprador (`BT-47`) en un `cac:PartyTaxScheme` con «LOC» y «FC», que es donde lo pone la fila de la orden | `BR-AE-02`, ERROR, en una inversión del sujeto pasivo | Cuenta, en la solución pública. Fuera de ella, `BT-47` es el de la vinculación de 2017 |
| El calificador de L10 a secas, `QR`, `AUT`, `RECT:TIPO` | No se reconocía: un QR así no se miraba | Se reconoce, como en L7 y L8 |
| La referencia catastral con el calificador de L8, `…:lin:RCAT` | No se leía: una situación fuera de L6 pasaba | Se lee, como la clave de régimen |

Esta tabla es la del 07-10-2026. La segunda tanda, el 11-10-2026, quitó lo que
la columna «Ahora» todavía aceptaba de abril (la L7 de abril y el nombre del
tercero en `cac:PartyName`) y la nota de la que habla el párrafo siguiente, que
pasó a ser `SPFE-ALCANCE`.

La nota `SPFE-BORRADOR` ya no dice que el anexo no está publicado: dice que es
el de la orden, que aquí se mide todavía en buena parte con el borrador de
abril, la lista entera de lo que ya se admite, y que «ninguna queja» no quiere
decir que la factura cumpla la orden. La lista está escrita una vez,
`solucion_publica.LO_QUE_YA_SE_ADMITE`; el glosario la copia letra a letra, y
cada frase tiene en las pruebas las facturas que la demuestran y que pasan el
validador entero sin una queja. La etiqueta del informe deja de ser «Anexo I
(borrador)» y pasa a «Anexo I», sin versión: mientras queden reglas que solo
existen en el borrador, como el recargo de equivalencia, ponerles el nombre de
la orden sería atribuirle quejas que no hace, y la ficha de la familia dice
las dos fuentes. La frase de alcance dice «parte de» lo que el anexo pide, y
cuál: lo que ya pedía el borrador, sin las reglas nuevas de la orden.

**Lo que se decidió sin preguntar, y por qué.**

- **Los calificadores de L7 y L8.** La orden da cada valor —«usar «RETE»»— y,
  aparte, el calificador de su lista, sin decir cómo se juntan. Se aceptan las
  dos lecturas: el calificador delante, que es como la AEAT escribió los de
  L10 en su ejemplo, y el valor solo, que es lo que dice la fila. Elegir una
  daría por mala una factura que siga la otra. Es una pregunta para el buzón.
- **La `N`, la `D` y la `F`, solo en la solución pública.** Ahí lo dice la L4
  de la orden. Qué lista rige para quien declara la edición de 2026 sin
  declarar la solución pública es una decisión del titular que no está
  tomada, y entretanto esa factura se mide como siempre: la `N` le sigue dando
  `BR-CL-17` y `BR-CL-18`.
- **Se ensancha la lista y no se borra la queja.** `factura` le pasa a las
  reglas europeas las categorías de la orden que la lista de 2017 no tiene
  —calculadas restando, no escritas—, y `BR-CL-17` y `BR-CL-18` las cuentan
  como buenas. Con `_SOBRA_SI`, que apaga el código entero, una `X` en otra
  línea de la misma factura se habría callado. Así sigue saliendo, y sola.
- **`BT-47` donde lo pone la orden, para la norma.** `BR-AE-02` pide el
  identificador de IVA del comprador o su registro legal, `BT-47`. La orden
  llama `BT-47` al NIF con «LOC» y «FC» en `cac:PartyTaxScheme`; la
  vinculación de 2017, a `cac:PartyLegalEntity/cbc:CompanyID`. Que la orden
  rotulara mal su fila también se puede sostener, y entonces el ERROR sería
  bueno; se elige la lectura que no condena lo que el texto admite.
- **`BR-G-02` se queda.** La exportación pide en la norma el identificador de
  IVA del vendedor (`BT-31`), y la orden deja elegir `BT-31` o `BT-32`. Pero
  el anexo es un mínimo, el artículo 3.1 exige la EN 16931 y nada deroga esa
  regla: con el vendedor solo en `BT-32`, una exportación sigue en ERROR.
- **Las constantes de la orden, a mano y juntas.** `cius_es` todavía sale del
  PDF de abril. Lo que esta tanda toma de la orden va escrito en un solo
  bloque de `solucion_publica.py`, con la fila de la que sale, y la guarda de
  L10 se niega a importar el módulo el día que la tabla traiga L10, que la del
  BOE trae: no hay que acordarse de moverlas.

**La revisión, antes de publicar.** Tres miradas sobre el cambio —que el
código haga lo que dice, que no acepte de más, que las pruebas lo fijen—, cada
hallazgo verificado aparte por otra, y el revisor de promesas. Cuatro fallos:
la rama de `BR-CO-18`, la de la factura sin desglose, no le pasaba a
`BR-AE-02` el `BT-47` de la orden; «LOC» y «FC» con un espacio alrededor
valían en `SPFE-NIF` y no en `BR-AE-02`, en el mismo informe; un abono que
declara la solución pública recibía la L4 de la orden sin la nota que lo dice;
y la `N` salía en `BR-CO-17` como «categoría no reconocida» junto a la nota
que la daba por buena. Siete cosas que el cambio hacía y ninguna prueba
fijaba: la `D` y la `F`, los calificadores de L10 a secas que no son el QR, dos
mensajes de la rectificativa, la etiqueta «Anexo I», el filtro de «LOC» del
`BT-47`, la `RCAT` con calificador y la fila del adjunto en la copia fiel. Y
frases que prometían de más: la nota, el alcance, la ficha de la familia, la
portada y la política. Arreglado todo, con la prueba en rojo antes.

**Lo que la revisión propuso y se quedó como estaba.**

- **`IVA-BASE` e `IVA-TIPO` siguen sin mirar la `N`, la `D` y la `F`** en la
  solución pública. Se propuso volver a pedir que la base tenga líneas
  detrás, salvo una `N` con la misma base que otra entrada. Rompía una factura
  buena: el recargo de equivalencia solo grava las entregas de bienes
  (artículo 154 de la Ley del IVA), y a un minorista con 80 de mercancía y 20
  de un servicio le toca una `S` con base 100 y una `N` al 5,2% con base 80,
  que no es la de ninguna otra entrada. Y en la `D` y la `F`, con la base en el
  precio y la cuota sobre el margen, `BR-CO-17` obliga a un tipo que no está
  en la tabla, y el aviso de tipos saltaría en falso. La nota `SPFE-CATEGORIA`
  nombra las reglas que no se les aplican.
- **Los espacios alrededor de `REGI` o de la línea `RETE`** se recortan, como
  en todo el módulo: el tipo de factura, el identificador del QR y el valor de
  la propia clave ya se recortaban. Antes, una línea `RETE` con espacios era
  buena para `SPFE-LINEA-DE-COBRO` y le faltaba a `SPFE-RETENCION` en el mismo
  informe.
- **La 384 con un `BG-24` ajeno** y **el proceso del ejemplo del
  02-10-2026** siguen en NOTA. Pasarlos a ERROR es poner las reglas al texto,
  que es la tanda siguiente, y la nota lo dice: lo que la orden no admite
  todavía no siempre se rechaza.

**Lo que no se hizo, a propósito.** Rechazar lo que la orden ya no admite —las
claves 18, 19 y 20 de L3A, las líneas `REEQ` y `REGE`, el proceso y la
especificación de abril— y medir sus reglas nuevas. Las dos cosas piden
regenerar `cius_es` desde el XML del BOE y poner cada regla al texto, y van en
la tanda siguiente. Hasta entonces, la nota lo dice en cada factura.

### La segunda tanda: las reglas, al texto de la orden

El 11-10-2026 `cius_es` se regeneró del XML del BOE, con
`herramientas/anexo_i.py` reescrito para leer la tabla del XML en vez de las
coordenadas del PDF: 176 filas, 149 identificadores distintos, 39 grupos y
catorce listas. No trae la tabla del mensaje de anulación ni el anexo II, que
son de las reglas nuevas. Las rutas de los campos españoles
(`RUTAS_CIUS_ES`) salen de ahí, con sus arreglos a la vista.

Medido antes de tocar nada, sobre `faa3f5f`: una factura escrita con el
borrador de abril (su identificador, su proceso, la URN de abril en la
retención y en el QR, y la clave 18 del IVA) pasaba el validador entero **sin
un error**. Con las reglas al texto de la orden, sale con cinco.

| Lo que cambió | En `faa3f5f` | Ahora |
|---|---|---|
| El identificador de especificación del borrador | Era el que se pedía, y el de la orden se aceptaba como «el del ejemplo» | ERROR, que dice que es el de abril; vale el de la orden |
| El proceso del borrador, `urn:aeat:names:specification:ubl:schema:B2B` | Se aceptaba | ERROR |
| Las claves 18, 19 y 20 en el IVA | Se aceptaban | ERROR: la L3A de la orden no las tiene |
| Las líneas de cobro `REEQ` y `REGE` | Se medían con sus reglas, `SPFE-RECARGO-DE-EQUIVALENCIA` y `SPFE-GRUPO-DE-ENTIDADES` | ERROR en `SPFE-LINEA-DE-COBRO`, que dice que eran del borrador: la orden pone los dos regímenes en el desglose, con la `N`. Las dos reglas desaparecen |
| La 384 con un tipo de rectificativa fuera de L2.A | AVISO | ERROR. La extensión de rectificativas de abril ya no cuenta |
| La rectificativa bien escrita | NOTA | Nada |
| El QR con una descripción que no es VERIFACTU ni TICKETBAI | Se aceptaba | ERROR |
| El QR con la URN de abril | Era el QR | No es el QR de la orden. Como el QR es `0..1`, no llevarlo no es un fallo; desde la revisión antes de publicar, una NOTA lo dice |
| El nombre del tercero en `cac:PartyName` | Se aceptaba | ERROR: la orden lo pone en la razón social |
| La nota de cada factura | `SPFE-BORRADOR`: medida en buena parte con el borrador, y la lista de lo ya admitido | `SPFE-ALCANCE`: la orden, las nueve cosas que todavía no se miden y, por su nombre, las que no se pueden comprobar |

**Lo que todavía no se mide**, y es el paso siguiente: la fecha efectiva de
pago (`BT-ES-2`); el registro legal del vendedor cuando su NIF va con «LOC»
(`BT-30`); el prefijo ES del NIF-IVA del vendedor (`BT-31`) y el del
comprador (`BT-48`); el tipo de cada
entrada del desglose (`BT-119`); los impuestos y tasas que no son el IVA, con
su lista L9; el número de la autorización de facturación (`BT-ES-26`); la
información adicional de cada línea (`INFO` de L8); y los códigos de
exención, que solo pueden ser VATEX-EU o VATEX-ES. Fuera de esa lista, porque
no son de la factura, el mensaje de anulación y los del anexo II. Seis de las
nueve se miden desde el mismo día (en la sección siguiente).

**La `N`, la `D` y la `F` fuera de la solución pública.** Lo decidió el
titular el 11-10-2026: fuera de ella rige la lista de la norma, y `BR-CL-17` y
`BR-CL-18` las siguen dando por malas. Pero decían «no es de UNCL 5305» y nada
más, y quien escribió la `N` la sacó de la orden: ahora la queja añade que es
de la L4 de la orden, que solo rige en las facturas UBL que declaran en `BT-24`
el identificador de la orden, y lo escribe entero, y nombra la lista como lo
que es, «UNCL 5305 tal como la recoge la norma», porque la D y la F sí están
en la UNTDID 5305 entera; y que son facturas
(`Invoice`), no abonos (`CreditNote`), porque un abono UBL que declara la orden
lo leía como si cumpliera. Solo nombra los códigos que
son de la orden: una `X` junto a la `N` sale en la misma queja, sin la frase.

**Lo que se decidió sin preguntar, y por qué.**

- **El QR con la URN de abril no es el QR**: ni se le pide la dirección ni
  cuenta para estar repetido. La factura escrita con abril ya sale con su
  identificador en ERROR, y decirle además que su QR no tiene dirección sería
  medirle con el borrador. Pero se dice en una NOTA: con el identificador de
  la orden, ese QR sin dirección pasaba sin nada, y la factura parecía llevar
  un QR que para la orden no lleva.
- **El margen de las retenciones.** La orden define cada retención (`BT-ES-19`)
  como la base por el porcentaje y la suma (`BT-ES-17`) como la de todas, y no
  da margen. Se usan los de la norma para lo mismo: la retención es la cuenta
  de la cuota del IVA con otro porcentaje, y tiene el de `BR-CO-17`, una
  unidad, con una NOTA que dice cuánto se aparta si no cuadra al céntimo; la
  suma va exacta, como las de la cabecera. Sin ese margen, una retención
  calculada por líneas sería un ERROR que la norma no pondría en la cuota.
- **Cuántos importes rectificados.** La orden dice tres en `BT-3` y cinco en el
  grupo. Hasta el 13-10-2026 se aceptaba con el grupo, y con cuatro o cinco una
  NOTA decía la contradicción. Ese día la AEAT contestó que el grupo pasa a
  `0..1`, y mandó un ejemplo con tres, uno por código de L2.C: las tres cifras
  solo casan leídas como uno por código. Un código repetido sale en AVISO, y
  más de cinco sigue en ERROR, porque es lo que dice el BOE. Los importes con la
  modalidad `I` van en AVISO y no en ERROR: el grupo se describe para la
  sustitución, pero ninguna frase de la orden lo prohíbe en la otra.
- **Lo que no se mide va en la nota, y no en un AVISO.** No son fallos de la
  factura sino límites del validador, y un AVISO en cada factura de la
  solución pública diría lo contrario.
- **El calificador de L10 delante o sin él**, como los de L7 y L8: la orden da
  el valor en la fila y el calificador en la lista, sin decir cómo se juntan.
  Está entre lo preguntado al buzón el 07-10-2026.

El detalle de lo medido y las catorce roturas provocadas (diez y una frase de
la tabla en la primera tanda, tres en la segunda), en HALLAZGOS.

### Lo que la orden pide y no se medía: la fecha de pago, el NIF y el desglose

El 11-10-2026 se miden seis de las nueve cosas que la orden pide y aquí no se
medían. Medido antes de tocar nada, sobre `a7c9c8c`, con el validador entero
y los esquemas de `web/paquete.zip`:

| Factura | En `a7c9c8c` | Ahora |
|---|---|---|
| la fecha efectiva de pago, posterior a la expedición | sin errores | ERROR `SPFE-FECHA-DE-PAGO` |
| anterior a la operación (`BT-7`) | sin errores | ERROR |
| anterior a la expedición, sin `BT-7` | sin errores | ERROR: sin `BT-7`, la operación es del día de la expedición |
| dos fechas de pago, una del día antes | sin errores | dos ERROR: que son dos, y que la segunda es anterior |
| posterior a la operación y anterior a la expedición | sin errores | NOTA: la fila la admite, y el apartado 4 del artículo 7 no libera con ella de comunicar el pago |
| anterior a la expedición, con un periodo (`BG-14`) en vez de `BT-7` | sin errores | NOTA: la orden no dice con qué fecha del periodo se compara |
| el NIF del vendedor con «LOC» y sin registro legal (`BT-30`) | `BR-CO-26` | `BR-CO-26` y `SPFE-NIF` |
| lo mismo, con el identificador del vendedor (`BT-29`) | **sin errores** | `SPFE-NIF` |
| el NIF-IVA del vendedor con FR | `CU-01` | `SPFE-NIF` y `CU-01` |
| el del comprador con FR | sin errores | AVISO `SPFE-NIF` |
| la entrada no sujeta (`O`) sin tipo | sin errores | ERROR `SPFE-TIPO-DE-IVA` |
| la no sujeta con tipo 0 | sin errores | sin errores |
| la exención con un VATEX-EU | sin errores | sin errores |
| con un VATEX-FR | sin errores | ERROR `SPFE-EXENCION` |
| con un VATEX-ES que no está en la lista | `BR-CL-22` | `BR-CL-22` |

**Lo que se decidió sin preguntar, y por qué.**

- **El prefijo del comprador, en AVISO hasta el 13-10-2026, y desde entonces
  en ERROR.** La fila `BT-48` copia la `BT-31` hasta en la descripción, que
  dice NIF a efectos de IVA del vendedor, y no se sabía si el prefijo ES era
  para el comprador. La AEAT contestó ese día que es una errata de la
  descripción, y su anexo corregido dice del comprador, con el prefijo de
  España. Esa frase del BOE se lee al importar: si la orden la corrige, el
  módulo no se monta hasta mirarlo otra vez.
- **`BT-30` sale aunque salga `BR-CO-26`.** No dicen lo mismo: la norma pide
  uno de tres identificadores del vendedor, y la orden pide este cuando el
  NIF va con «LOC». Con el identificador del vendedor (`BT-29`) la norma se
  calla y solo habla la orden. La orden no le da ruta, y se busca donde lo
  pone la vinculación de 2017, `cac:PartyLegalEntity/cbc:CompanyID`; si un
  anexo nuevo le da una, el módulo no se monta.
- **El FC en el registro legal sigue en ERROR, y se dice por qué.** El
  ejemplo UBL de la AEAT pone `schemeID="FC"` en
  `cac:PartyLegalEntity/cbc:CompanyID` (BT-30), y `BR-CL-11` lo da por malo:
  la norma pide un esquema de ISO 6523 o ninguno, y la orden pone el FC en el
  NIF de BT-32, en `cac:PartyTaxScheme`, sin darle esquema a BT-30. Como
  `BR-G-02`, la regla de la norma se queda. Desde el 18-10-2026 el mensaje dice
  de dónde sale el FC, que no se sabe si la solución pública lo acepta y que
  basta quitar el atributo. Está en HALLAZGOS y se le pregunta al buzón.
- **`BT-119` solo en la no sujeta.** En las demás categorías, que falte el
  tipo ya lo dice `BR-48`, y dos quejas por lo mismo no dicen más que una.
  Medido: en Glosa, una entrada `O` con tipo 0 no hace saltar ninguna regla
  de la norma, así que lo que la orden pide se puede cumplir sin romper nada.
- **Los VATEX-ES los juzga `BR-CL-22`.** Hasta el 24-10-2026 la lista
  CEF-VATEX que llevaba Glosa-e no tenía ninguno; desde la 1.3.17 trae
  dieciocho, que valen con la nota `IVA-VATEX-ES`, y uno que no está en la
  lista sale ahí. La regla nueva solo dice lo que la norma admite y la orden
  no: los de otros países.
- **La fecha de pago sin `BT-7`.** La orden pide `BT-7` solo cuando la
  operación es de otro día que la expedición, así que sin él la operación es
  del día de la expedición, y un pago anterior es anterior a la operación.
  Salvo con un periodo de facturación: la orden no dice con qué fecha del
  periodo se compara, y sale una nota en vez de un error.
- **Lo que la fila admite y el artículo no libera.** La fila `BT-ES-2` pide
  el pago del día de la operación al de la expedición; el apartado 4 del
  artículo 7 da por comunicado el pago solo si coincide con la operación. Lo
  primero es la regla, y lo segundo, una nota: la factura está bien, pero
  quien la recibe tiene que comunicar el pago igual. Se vio al cotejar la
  ficha con el artículo, que decía que con la fecha no había que comunicarlo,
  sin más.

Quedaban sin medirse los impuestos y tasas que no son el IVA, con su lista
L9; el número de la autorización de facturación (`BT-ES-26`); y la
información adicional de cada línea (`INFO` de L8). Los primeros y la última
se miden desde el mismo día, en la sección siguiente. El detalle y las
dieciocho roturas provocadas, en HALLAZGOS.

### Los impuestos y tasas, y la información de la línea

El mismo 11-10-2026, la orden pide tres cosas de los impuestos y tasas que no
son el IVA, cada uno con su código de la lista L9 (`IEH`, `IEE`, `IMPTAS`… y
`RESTO` para lo que no es un impuesto): el código en cada cargo de línea
(`BT-ES-22`), el detalle de un impuesto cobrado como cargo del documento
(`BG-ES-2`) y el desglose del que se cobra en nombre de un tercero (`BG-ES-3`).
Y la información adicional de la línea es una propiedad del artículo con el
nombre fijo `INFO`. Medido antes de tocar nada, sobre `93a88c6`:

| Factura | En `93a88c6` | Ahora |
|---|---|---|
| un cargo de línea con `RESTO` o con `IEE` | sin errores | sin errores |
| sin código, o con uno que no es de L9 | sin errores | ERROR `SPFE-IMPUESTO-O-TASA` |
| un impuesto cobrado como cargo del documento, bien escrito | sin errores | sin errores |
| sin código, o con uno que no es de L9 | sin errores | ERROR |
| con una cuota en el impuesto y otra en el total del cargo | sin errores | ERROR |
| con una cuota que no es la base por el tipo | sin errores | ERROR |
| con dos impuestos en el mismo cargo | sin errores | NOTA |
| sin base ni tipo | sin errores | sin errores: no hay cuenta que hacer |
| el IEDMT cobrado para un tercero, con su desglose | sin errores | sin errores |
| con «IGIC» o con la categoría `E` en ese desglose | sin errores | ERROR |
| con una cuota que no sale | sin errores | ERROR |
| una propiedad `INFO`, con el calificador de L8 o sin él | sin errores | sin errores |
| una propiedad «Color» | sin errores | ERROR `SPFE-INFORMACION-ADICIONAL` (AVISO desde el 12-10-2026, abajo) |

**Lo que se decidió sin preguntar, y por qué.**

- **Con dos impuestos en un cargo, una nota.** La fila `BT-ES-8` pide «el
  mismo importe» en el impuesto y en el total del cargo, y un cargo de UBL
  tiene un solo total: con dos impuestos no se puede cumplir. Es la pregunta 4
  de la consulta del 07-10-2026, y hasta que la Agencia conteste no se
  compara. Con un impuesto, sí, y en ERROR.
- **La cuota es la base por el tipo, con el margen de la del IVA.** Las filas
  `BT-ES-8` y `BT-ES-14` la definen así, como la de las retenciones, y se le
  da el mismo trato: hasta una unidad, una nota que dice cuánto se aparta. La
  cuenta es una sola para las tres cosas, y la de las retenciones pasa a
  usarla. Sin base o sin tipo, que son `0..1`, no hay cuenta que hacer.
- **Sin dividir por cien, error y con la causa, desde el 19-10-2026.** Si la
  cuota es justo la base por el tipo sin dividir por cien, o el tipo va como
  fracción (0,0511 por un 5,11 %) o es un impuesto por unidad, con la cantidad
  en la base y el importe por unidad en el tipo. Es el caso de casi toda la
  L9: hidrocarburos, alcohol y tabaco por litro o por mil unidades, el
  plástico a 0,45 euros por kilo. La orden define la base como un importe y el
  tipo como un porcentaje, así que lo que cabe es dar solo la cuota, y el
  mensaje lo dice con las dos causas; los kilos que pide la Ley 7/2022 (art.
  82.9.a) no tienen campo. Antes daba la cuenta y no la causa, y por debajo de
  una unidad era una nota que la daba por buena: 1,11 kilos a 0,45 euros con
  cuota 0,50 salían así con un error del cien por cien. Ahora es ERROR aunque
  se aparte menos de una unidad, porque eso no es redondeo. Quitar la
  detección o el paso a ERROR pone en rojo su prueba.
- **La retención de garantía escrita como descuento, una nota desde el
  19-10-2026** (`SPFE-GARANTIA`). Ni la norma europea ni la orden tienen campo
  para ella, y un descuento rebaja la base. Lo correcto depende del contrato,
  que la factura no trae: si la certificación es un pago anticipado, lo
  retenido no entra en su base (consulta V2823-23 de la DGT); si es la
  factura de la entrega, la base es el importe entero; y la obra para un
  promotor o un contratista va por inversión del sujeto pasivo, sin cuota. La
  nota da las tres lecturas y no decide. Se reconoce por el texto del motivo,
  que es lo único que hay: un descuento de garantía con otro motivo no se ve.
  Antes pasaba sin una palabra.
- **El canje sin la simplificada que sustituye, una nota desde el 19-10-2026**
  (`SPFE-CANJE`). Un 388 sin BG-3 no dice qué tickets sustituye. La orden no
  lo exige (el grupo es opcional) y el Reglamento tampoco (art. 15.6), así que
  no es un error. Antes pasaba sin una palabra.
- **«VAT» y «S» en el desglose de un cobro**, aunque no sea el IVA. Lo dice
  el grupo: «su uso implica» los dos valores. Se lee de la columna de la ruta,
  como los de las retenciones.
- **Cualquier propiedad que no sea de L8 se dice.** La norma deja el nombre
  libre, y la orden lo fija: `INFO` para la información adicional, `REGI` y
  `RCAT` para las otras dos. Un «Color: rojo» se escribe como `INFO` con el
  texto en el valor. Era un error hasta el 12-10-2026, y desde entonces es un
  aviso (en «Lo que el auditor encontró en las reglas de la factura»).

**Lo que salió al provocar.** La negativa de `BT-160` salió en verde: se
comprobaba que la fila dijera «valor fijo INFO», y «valor fijo INFORMACION»
lo dice. Las de `REGI` y `RCAT`, escritas así desde antes, tenían el mismo
hueco: un `REGIX` en la orden pasaba por `REGI`. Ahora el valor se lee entero,
entre sus comillas, y las tres roturas salen en rojo.

Quedaba el número de la autorización de facturación (`BT-ES-26`), que se
mide desde el mismo día, en la sección siguiente. El detalle y las diecisiete
roturas provocadas, en HALLAZGOS.

### La autorización, los ficheros embebidos y lo que se quitaba sin una queja

El mismo 11-10-2026 quedaba en `LO_QUE_TODAVIA_NO_SE_MIDE` el número de la
autorización de facturación (`BT-ES-26`), y fuera del anexo, en el articulado
de la orden, dos prohibiciones: las facturas emitidas o interconectadas «no
podrán incorporar otros ficheros integrados o embebidos» (apartado 6 del
artículo 3), salvo la firma de las interconectadas, y las copias fieles
tampoco, sin esa salvedad (apartado 4 del artículo 4).

Antes de dar la lista por vacía se quitó cada elemento de las veintiocho
facturas buenas, uno a uno, y se pasó el validador entero con los esquemas:
33 rutas salían sin una queja. Casi todas son opcionales en el anexo. Tres
eran cosas que la orden pide: el número de la autorización, el «VAT» del
impuesto en las líneas, el desglose y los cargos, y el detalle de un impuesto
cobrado como cargo. Y la suma de retenciones sin ninguna retención pasaba sin
una palabra. Medido antes de tocar nada, sobre `d839f64`:

| Factura | En `d839f64` | Ahora |
|---|---|---|
| una autorización con su número | sin errores | sin errores |
| sin número, a secas o con el número vacío | sin errores | ERROR `SPFE-AUTORIZACION` |
| dos, y la segunda sin número | sin errores | ERROR, que dice cuál |
| un contrato en PDF, o en texto, dentro de un documento | sin errores | ERROR `SPFE-FICHERO-EMBEBIDO` |
| el QR con su imagen dentro | sin errores | ERROR |
| un contrato por su dirección | sin errores | sin errores |
| la original con la firma en un fichero | sin errores | sin errores |
| la copia fiel con la firma en un fichero | sin errores | AVISO |
| la copia fiel con la firma envuelta | los de la firma, que en la prueba no se sostiene | los mismos, y un AVISO |
| la copia fiel con un contrato en PDF | sin errores | ERROR, con el artículo 4 |
| sin «VAT» en la línea, en el desglose o en un cargo | sin errores | ERROR `SPFE-TIPO-DE-IMPUESTO` |
| un cargo con el total del impuesto y sin su detalle | sin errores | ERROR `SPFE-IMPUESTO-O-TASA` |
| la suma de retenciones sin ninguna retención | sin errores | sin errores, y una NOTA |

**Lo que se decidió sin preguntar, y por qué.**

- **La firma en la copia fiel, en AVISO.** El artículo 3 deja ir con la firma
  a las facturas interconectadas; el 4 prohíbe los ficheros a las copias
  fieles sin esa salvedad, y la orden no dice si la firma es uno de ellos.
- **La firma envuelta cuenta como firma.** Un `ds:Signature` dentro del XML
  no es un fichero pegado, pero es la firma que el artículo 3 exceptúa, y se
  trata como la que va en un fichero. Una `cac:Signature` que solo nombra la
  firma, sin llevarla, no es una firma.
- **Un documento por su dirección no es un fichero dentro**, y no se mira: la
  orden prohíbe incorporar ficheros, no nombrarlos.
- **Si lo que va dentro es un PDF, el error dice dónde va el del primer
  año** (añadido el 19-10-2026, al leer la sección de la Sede). Durante doce
  meses, quien factura más de 8 millones tiene que acompañar cada factura con
  un PDF legible, y lo natural es pegarlo dentro; el Real Decreto 238/2026 lo
  manda por cualquier medio y nunca a la solución pública (disposición
  transitoria segunda, apartado 2). Se reconoce por el tipo
  (`application/pdf`, sin mirar mayúsculas) o por el nombre, y no se dice en
  la copia fiel.
- **El «VAT» que falta es el mismo error que el que no es «VAT».** Las filas
  dicen que «su uso implica» que la ruta tome el valor, como las del desglose
  de los cobros y las de las retenciones, donde faltar ya era un error.
- **La suma de retenciones sin ninguna, en una nota.** La orden deja el
  detalle en `0..n`: sin él no hay con qué comparar la suma, y darla por mala
  sería suponer que lo que falta es el detalle y no la cifra.
- **Lo que la orden deja a la Sede, en lo que no se comprueba.** Las
  especificaciones técnicas, la volumetría y el tamaño máximo de las copias
  fieles (apartado 1 del artículo 3 y apartado 2 del 4) no son el anexo. Con
  `LO_QUE_TODAVIA_NO_SE_MIDE` vacía, la nota tenía que seguir diciendo que eso
  no se mide.

**Lo que salió al medir.** La cifra en negrita del principio de esta parte
decía 25 códigos cuando ya eran 27: la tanda anterior cambió la frase de
debajo y no esa. Ahora una prueba cuenta los códigos que el módulo escribe y
compara las dos cifras del README.

Desde ese día `LO_QUE_TODAVIA_NO_SE_MIDE` está vacía, y la nota
`SPFE-ALCANCE` deja de decir que falta algo del anexo: dice lo que no se puede
comprobar, con su porqué, y que una factura sin quejas no por eso cumple la
orden. Fuera de la nota quedan el mensaje de anulación y los del anexo II, que
no son facturas: se miden desde el 12-10-2026, con su propia nota (en la
sección siguiente). El detalle y las diecinueve roturas provocadas, en
HALLAZGOS.

### Lo que el auditor encontró en las reglas de la factura

El 12-10-2026, antes de publicar, el auditor rompió `solucion_publica.py`
sobre una copia y miró qué roturas pasaban la suite: pasaban cuatro. Y vio
dos reglas que decían más o menos de lo que dice la orden. Todo reproducido
antes de arreglarlo:

| Lo que pasaba | Ahora |
|---|---|
| un registro mercantil en `BT-30`, o el NIF de otro, pasaba sin una queja: se miraba que estuviera y no qué llevaba | tiene que ser el NIF del vendedor: ERROR con su NIF en `BT-32`, donde la orden lo pide, y AVISO sin él |
| una propiedad «Color» en la línea salía en ERROR | AVISO: la factura interconectada puede llevar contenido adicional que cumpla la norma |
| la ficha de `SPFE-IMPUESTO-O-TASA` decía que la norma «no tiene nada de esto» | dice también que el esquematrón de UBL del CEN avisa de la ruta de `BT-ES-22` (`UBL-CR-558`) |

Las cuatro roturas que la suite no veía: mirar solo el primer cargo de cada
línea, solo la primera entrada del desglose para `BT-119`, la copia fiel con
`true` y no con `1`, y pedir `BT-30` también con «LOC» sin «FC». Cada una
tiene ahora su prueba.

**Lo que se decidió, y por qué.**

- **`BT-30` es el NIF del vendedor**, porque la orden lo describe así:
  «Número de identificación fiscal (NIF) del vendedor». Esa frase se lee al
  importar, y si cambia el módulo no se monta. Vale con el prefijo ES o sin
  él, y se compara con el NIF que el vendedor da en `BT-31` o `BT-32` si
  alguno se lee como NIF español: con uno de otro país no hay con qué
  comparar, y su prefijo ya lo dice `SPFE-NIF`.
- **Sin `BT-32`, un aviso.** Entonces la orden no lo pide, y la norma admite
  en `BT-30` el identificador de cualquier registro oficial.
- **«INFO», en AVISO.** La factura que se emite con la solución pública se
  ajusta al anexo I (apartado 2 del artículo 3), pero la interconectada lo
  lleva «como mínimo» y puede incluir contenido adicional que cumpla la norma
  europea (apartado 3), que deja el nombre libre. Desde el fichero no se sabe
  por cuál de las dos va.
- **`UBL-CR-558`, en la ficha y no en el informe.** Es un aviso del
  esquematrón de sintaxis de UBL (`EN16931-UBL-syntax.sch`, `flag="warning"`),
  y esas reglas no se corren aquí (`test_norma_oficial`): decir una sola haría
  pensar que se miraron las demás. Con el IGIC a cero en CII es distinto,
  porque allí el esquematrón rechaza lo que la norma admite.

**Lo que se dejó como estaba.** El margen de una unidad en la cuota de los
impuestos y tasas, que es el de la cuota del IVA (`BR-CO-17`), y el cero del
IGIC en EDIFACT, que no se dice como no se dicen los márgenes de ese
esquematrón. De lo segundo solo se arregló el comentario de `sintaxis.py`, que
decía «hoy es una».

**En el corpus** no cambia nada: ninguna factura declara la solución pública,
y salen 1346 incidencias antes y después con el validador entero
(`factura.validar`) sin esquemas ni anclas. Provocado once veces, las once en
rojo (en HALLAZGOS).

### Los mensajes de la orden: la anulación y los ocho estados

La orden define nueve mensajes `ApplicationResponse`, cada uno con su tabla y
su `cbc:ResponseCode`: la anulación de una factura o copia fiel
(`CANCELINVOICE`, la segunda tabla del anexo I) y los ocho del anexo II. Son
el pago y el rechazo con sus bajas, que manda el destinatario (`PAYMENT`,
`CANCELPAYMENT`, `REJECTION`, `CANCELREJECTION`), y el cobro y el impago con
las suyas, que el emisor manda si quiere (`SETTLEMENT`, `CANCELSETTLEMENT`,
`DEFAULT`, `CANCELDEFAULT`). Hasta el 12-10-2026 a una respuesta se le miraba
la forma y la firma, y del contenido el informe decía que no se miraba.
Medido ese día sobre `9ce8c0e`, con mensajes escritos aquí y los esquemas de
`web/paquete.zip`, de nueve rotos ocho salían sin una queja:

| Mensaje | En `9ce8c0e` | Ahora |
|---|---|---|
| los nueve, bien escritos | sin errores | sin errores, y la NOTA `SPFE-MENSAJE-ALCANCE` |
| una anulación, un pago o un impago sin su fecha | sin errores | ERROR `SPFE-MENSAJE-FECHA` |
| un pago sin la fecha de vencimiento | sin errores | ERROR `SPFE-MENSAJE-VENCIMIENTO` |
| un rechazo sin motivo, o con el `03` | sin errores | ERROR `SPFE-MENSAJE-MOTIVO` |
| un pago sin el NIF ni el nombre del emisor | sin errores | ERROR `SPFE-MENSAJE-FACTURA` |
| la baja de un pago sin la fecha de la factura | sin errores | ERROR `SPFE-MENSAJE-FACTURA` |
| la anulación escrita como dice el BOE | ERROR `XSD-ORDEN` | el mismo, y sus datos se leen donde los pone la tabla |

**Cómo se reconocen.** Por su código, que es lo que dice cuál es cada uno: la
orden no les da identificador de especificación. Ninguno de los nueve está en
la lista de códigos de respuesta que usa Peppol (la UNCL 4343: `AP`, `RE`,
`AB`…), así que una respuesta de otra red sigue como estaba. El código se lee
letra a letra: `payment` no es `PAYMENT`, y no se mide.

**De dónde sale cada comprobación.** Las tablas se leen del mismo XML del BOE
que el anexo I, con `herramientas/mensajes.py`, y van a
`validador/mensajes_es.py` con su huella: nueve mensajes, 59 filas y la L1 de
motivos de rechazo, que no es la L1 del anexo I. `validador/mensajes.py` las
lee fila a fila al importar, y una fila que no sepa medir, un dato de la
factura que deje de ser obligatorio o un mensaje nuevo hacen que no se
importe. Una prueba vuelve a extraer y exige el mismo fichero, byte a byte.

**Las erratas.** La columna de la ruta trae tres clases de errata de
escritura, que se arreglan al leerla y se cuentan: un renglón partido detrás
de una barra (16), un espacio donde va una barra (1) y una barra doble (1).
Si el BOE corrige una, la cuenta cambia y una prueba salta. Se cuentan
también las celdas con dos rutas (8), la de la fecha y la de su condición,
cada una en su párrafo, que no son una errata: hasta el 12-10-2026 se
contaban entre ellas, porque al leer la celda los dos párrafos se juntan con
un espacio. La tabla de la anulación trae además las dos que se le
preguntaron al buzón el 07-10-2026 y que contestó el 13-10-2026 (en la sección
de esa consulta, abajo): la factura colgada de `cac:Response`, que sobra, y
cuyos datos se buscan donde los pone el anexo II, en `cac:DocumentResponse`, y
también donde los pone la tabla, para no decir que faltan cuando están; y el
nombre del vendedor dentro de `cac:PartyTaxScheme`, que va en
`cac:PartyLegalEntity`, como en el anexo II. En el otro arreglo posible, el
`cbc:RegistrationName` de `cac:PartyTaxScheme`, se encuentra y sale un AVISO.
Las dice la nota de cada anulación, porque un mensaje escrito al pie de la
letra no pasa el esquema. Que las rutas arregladas andan por UBL 2.5, y las dos de la
anulación tal cual no, lo comprueba una prueba con el esquema.

**Lo que se decidió sin preguntar, y por qué.**

- **El NIF, sin el prefijo ES, y con el `cac:TaxScheme` vacío.** Hasta el
  13-10-2026 se aceptaba con el prefijo y sin él, y con cualquier
  `cac:TaxScheme`, porque la tabla lo pone donde la factura de la orden pone
  el NIF-IVA y el NIF (`BT-31` y `BT-32`) y el esquema exige un
  `cac:TaxScheme` que ninguna tabla da. Ese día la AEAT contestó que va sin
  ES, y que `<cac:TaxScheme />` sin contenido vale. Con el prefijo se sigue
  aceptando, porque del código único dijo que si viene el sistema lo trata
  igual sin él. Si van los dos, se mira cada uno. Uno de otro país sale en
  AVISO, y uno español con el control mal, en ERROR.
- **La fecha de vencimiento, en su propia regla.** Es la única fecha
  obligatoria que va en un `cac:Status`, y es lo que el apartado 1 del
  artículo 7 obliga a comunicar con el pago. Las demás fechas con condición
  son opcionales: si van, con su fecha y una vez.
- **Una fecha por `cac:Status`.** El esquema admite un `cbc:ReferenceDate`
  con varias condiciones, y la tabla pone cada fecha en su `cac:Status`: dos
  condiciones con una sola fecha salen en ERROR, porque no se sabe de cuál es.
- **Lo que la tabla no prevé, en AVISO.** Una condición, un
  `cbc:StatusReason` o un `cbc:ConditionCode` que el mensaje no lleva puede
  ser una errata (`Duedate` por `DueDate`), y entonces lo que quería decir no
  se ha leído; pero el mensaje no está mal por llevar algo de más.
- **Una sola factura en los del anexo II.** Su tabla le da `1..1`; la de la
  anulación, `1..n`.
- **Cada `cac:DocumentResponse` es un mensaje.** Un `ApplicationResponse`
  puede traer varias respuestas, y cada una se mide con su tabla: el `1..1`
  de la factura es de cada una. La orden no dice si cada comunicación va en
  su documento; el apartado 3 del artículo 8 habla de la «relación de
  comunicaciones» admitidas, así que un envío puede llevar varias.
- **Lo que no se mide lo dice la nota**: lo que la orden deja a la Sede
  electrónica, la cabecera de la respuesta
  (quién la manda, a quién, su número y su fecha), que el esquema exige y las
  tablas no definen, y que la factura exista o que las fechas sean ciertas.

**En el informe.** La frase del final dice que se ha mirado «parte de lo que
la orden de la solución pública pide a sus mensajes de anulación y de estado»
solo si a alguno se le midió, y de las demás respuestas, también de las que
van en el mismo documento que un mensaje de la orden, sigue diciendo que su
contenido no se mira. La norma de cada queja es «Anexo II» en las tres que
solo miden estados y «Anexos I y II» en las otras tres. Sin el esquema de `ApplicationResponse`, una respuesta sigue
saliendo SIN COMPROBAR aunque se le haya medido la tabla: su comprobación
principal sigue siendo la forma. Seis códigos nuevos, de 395 a 401. Lo que no
está medido: ningún mensaje real, porque los de las pruebas están escritos
aquí, con las tablas. En el navegador se midió al publicar, en la página de
producción, y sale lo mismo que en la consola (en HALLAZGOS).

### La consulta del 07-10-2026, y la respuesta del 13-10-2026

Con la orden publicada se le escribió otra vez al buzón el **07-10-2026**. Cada
dato del correo se midió ese día contra el XML del BOE —el de la huella de
arriba— y contra los esquemas de UBL 2.5, escribiendo cada variante y
validándola. Lo que consta aquí es el borrador: si cambió algo al mandarlo, no
está recogido. Lo que se preguntó, y qué cambia aquí con cada respuesta:

| Se preguntó | Por qué: lo medido | Qué cambia aquí con la respuesta |
|---|---|---|
| La ruta del mensaje de anulación del anexo I (`CANCELINVOICE`; la tabla se titula «Mensaje de anulación» y los artículos 3.5 y 5 lo llaman «mensaje de baja») | Toda la factura anulada cuelga de `cac:Response/cac:DocumentReference`, y en UBL 2.5 `cac:Response` no lo admite, mientras que `cac:DocumentResponse` lo exige: al pie de la letra, el esquema la rechaza. Los ocho mensajes del anexo II cuelgan lo mismo de `cac:DocumentResponse/cac:DocumentReference` | `validador/mensajes.py`, que desde el 12-10-2026 busca los datos de la factura en `cac:DocumentResponse`, donde los pone el anexo II, y también donde los pone la tabla, y lo dice en la nota de cada anulación |
| Dónde va el nombre del vendedor en esa misma anulación | `cac:PartyLegalEntity` no puede ir dentro de `cac:PartyTaxScheme`, y caben dos rutas válidas: `cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName`, la del anexo II, y `cac:IssuerParty/cac:PartyTaxScheme/cbc:RegistrationName` | Lo mismo. Mientras no se sepa, no se puede dar por mala ninguna de las dos, y desde el 12-10-2026 se buscan las dos |
| Qué `cac:TaxScheme/cbc:ID` lleva el NIF del vendedor en los nueve mensajes de estado —la anulación y los ocho del anexo II—, y si va con «ES» | Va en `cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID`; `cac:PartyTaxScheme` exige `cac:TaxScheme` y ninguna fila lo da: sin él, el esquema rechaza los nueve | La medida de los mensajes, que desde el 12-10-2026 acepta el NIF con «ES» y sin él y no mira el `cac:TaxScheme` |
| Si en `BT-ES-8` va la suma de las cuotas | La fila pide el mismo importe en `cac:AllowanceCharge/cac:TaxTotal/cbc:TaxAmount` y en su `cac:TaxSubtotal`, y `BG-ES-2` es `0..n` dentro de cada cargo; `cac:AllowanceCharge` admite un solo `cac:TaxTotal` con un solo `cbc:TaxAmount`. Con dos impuestos en el mismo cargo no se puede cumplir | Lo que se mida de esos cargos cuando se midan los impuestos y tasas, que es de las reglas nuevas |
| El `ProfileID`: el de `BT-23`, con `ubl:`, o el del ejemplo del 02-10-2026, sin él | `BT-23` es el único sitio del XML con `specification:ubl:schema:`; los calificadores de L7, L8 y L10 van sin `ubl:`. El `CustomizationID` del ejemplo sí es el de la orden | `SPFE-PROCESO`, que hoy acepta el de la orden y deja el del ejemplo en NOTA |
| Si el servicio de validación de PRE pedirá certificado | El artículo 11.1 lo exige para «la utilización de la solución pública», y la orden no nombra ningún entorno de pruebas ni servicio de validación aparte del envío | Si PRE puede servir aquí de contraste sin certificado |
| El formato del código único | El artículo 6 lo remite al anexo I, y el anexo I no lo trae: ni orden, ni separador, ni formato de fecha, ni qué NIF —`BT-31` con «ES» o `BT-32` sin él—, ni si serie y número son el `cbc:ID` entero. El título del artículo habla de su «inserción en la sintaxis de la factura», y no hay campo para él | `codigo_unico.py` y sus reglas `CU-`, que suponen lo de VeriFactu: serie y número pegados sin separador y un tope de 60 caracteres |
| Si los calificadores de L7, L8 y L10 se escriben delante del valor | Las filas dan solo el valor —«usar «QR»» en `BT-122`, «usar «SUPL»» en `BT-ES-10`, «INFO» en `BT-160`— y cada lista trae aparte su calificador; el ejemplo del 02-10-2026 escribe los dos juntos en `cbc:ID`: `urn:aeat:names:specification:schema:RECT:TIPO` | Desde el 07-10-2026 se aceptan las dos formas donde se miran —las líneas de cobro de L7, la clave de régimen y la referencia catastral de L8, los `BG-24` de L10—; con la respuesta, solo una |

Se dijeron además, sin pregunta, dos erratas menores —el grupo `RECT:IMPORTES`
es `0..5` y `BT-3` habla de «hasta tres grupos»; la descripción de `BT-48`, el
NIF-IVA del comprador, dice «del vendedor»— y las rutas que tienen una sola
corrección posible, como se leen aquí salvo que la Agencia diga otra cosa: en
`BT-ES-5`, `cbc:ServiceTypeCode` cuelga de `cac:ServiceProviderParty` y no de su
`cac:Party`; en `BT-ES-6` a `BT-ES-9` sobra `cac:Invoice` y `cac:TaxSubTotal` es
`cac:TaxSubtotal`; en `BT-ES-23` y `BT-ES-24`, `/in:invoice` es `/in:Invoice`.

**La respuesta, el 13-10-2026.** Llegaron dos correos ese día. El de esta
consulta empieza agradeciendo *las diferentes observaciones planteadas que nos
permiten realizar nuevas correcciones*, contesta cada punto y adjunta el anexo
I corregido, una versión 2.0 que dice que publicará en su Portal de
Desarrolladores. El otro contesta la consulta anterior, la de la
correspondencia y el ejemplo, y adjunta otro anexo y un ejemplo de los
importes rectificados, `importes.xml`. Los adjuntos se guardan fuera del
repositorio, en `informes/`, con su SHA-256, y no se publican aquí: son
documentos que la AEAT todavía no ha publicado.

| Se preguntó | Contestó | Qué cambió aquí |
|---|---|---|
| La ruta de la anulación | Sobra `cac:Response`, y lo corrige | Los datos se siguen buscando en los dos sitios, para no decir que faltan cuando están; la forma la dice `XSD-ORDEN`, y la nota de cada anulación dice lo que contestó |
| El nombre del vendedor en la anulación | Como en el anexo II: `cac:PartyLegalEntity` | En `cac:PartyTaxScheme/cbc:RegistrationName` se encuentra, y sale un AVISO de `SPFE-MENSAJE-FACTURA` |
| El `cac:TaxScheme` y el ES del NIF de los mensajes | `<cac:TaxScheme />` sin contenido vale, y el NIF va sin ES | La nota lo dice. Con ES se sigue aceptando, por lo que contestó del código único |
| `BT-ES-8` con dos impuestos | Lo están evaluando, la duda es pertinente, y piden mandar el caso en dos semanas | Sigue la NOTA. El caso se manda antes del 27-10-2026 |
| El `ProfileID` | Sin `ubl:`, como el resto de campos. El otro correo, lo mismo: los identificadores del ejemplo son los correctos | `SPFE-PROCESO`: el del ejemplo, limpio; el del BOE, AVISO. Hasta ese día era al revés |
| El servicio de validación de PRE | Exigirá certificado | PRE no sirve aquí de contraste, porque no hay certificado. Se mide contra el BOE, el anexo corregido cuando se publique y los ejemplos de la AEAT |
| El código único | La concatenación no es literal: son los tres datos por separado. La fecha, en AAAA-MM-DD; el NIF, sin ES, y si viene se trata igual; `BT-1`, la serie y luego el número, sin separador | Nada: es lo que `codigo_unico.py` ya hacía. La longitud no la dijo, y el tope de 60 sigue siendo el de VeriFactu |
| Los calificadores de L7, L8 y L10 | Se escribirá tal y como lo habéis montado, es decir, el calificador seguido del valor. El otro correo lo dice de L7 con todas las letras: `urn:aeat:names:specification:schema:add:` más SUPL, MINO... | `SPFE-CALIFICADOR`, nuevo: el valor solo sale en AVISO, una vez por factura, y se sigue reconociendo para medir lo demás |
| Las rutas con una sola corrección (`BT-ES-5`, `BT-ES-6` a `BT-ES-9`, `BT-ES-23` y `BT-ES-24`) | También corregido | Nada: ya se leían así |
| `RECT:IMPORTES`, `0..5` contra los tres de `BT-3` | Corregido a `0..1` | Un código de L2.C repetido sale en AVISO, y más de cinco sigue en ERROR. El ejemplo de ese día lleva tres, uno por código, y es la única lectura en la que casan las tres cifras |
| La descripción de `BT-48`, que dice del vendedor | Corregida | El prefijo ES del comprador pasa de AVISO a ERROR, como el del vendedor |

**El anexo 2.0, medido contra el BOE.** Se pasaron los dos PDF a texto con
`pdftotext` y con `pypdf`, y se compararon con el anexo del BOE. La versión
2.0 trae cuatro de las correcciones: la descripción de `BT-48`, que ya dice
del comprador; `cac:TaxSubtotal` en `BT-ES-6` a `BT-ES-8`; `/in:Invoice` en
`BT-ES-23` y `BT-ES-24`; y el grupo `RECT:IMPORTES` en `0..1`. **Las demás no
están en ella**: la anulación sigue colgando de `cac:Response`, el nombre sigue
en `cac:PartyTaxScheme/cac:PartyLegalEntity`, `BT-ES-5` sigue con su
`cac:Party`, `BT-ES-6` a `BT-ES-9` siguen con `cac:Invoice`, `BT-3` sigue
diciendo hasta tres grupos y `BT-23` sigue con `ubl:`. Por eso nada de aquí
sale de la versión 2.0 sin una respuesta escrita que lo diga, y lo que sale
de una respuesta va en AVISO, no en ERROR, cuando el BOE dice otra cosa. El
prefijo del comprador va en ERROR porque el BOE ya lo pide en su fila: lo que
dudaba era de quién era la fila. El otro anexo,
el que el segundo correo llama versión definitiva, es el texto del BOE. Al
comparar con `pdftotext -layout`, las descripciones de `BT-ES-6` a `BT-ES-8`
parecían corridas una fila en la 2.0; con `pypdf` están en su sitio. Era la
maquetación de la extracción, no el anexo.

**UBL-SR-43**, que no estaba en esta consulta, se había preguntado en la
anterior, y la contestó el segundo correo: la solución pública se basa en la
semántica de la EN 16931, que no impone esa restricción (en la sección del
ejemplo del 02-10-2026, arriba).

### El anexo del portal, del 21-10-2026

El 21-10-2026 la AEAT subió los anexos I y II a la página de la solución
pública de su Portal de Entidades Desarrolladoras, como `A1-Proyecto-OM-FE.pdf`
y `A2-Proyecto-OM-FE.pdf`. El nombre conserva el *Proyecto*, pero no es el
borrador de abril: lleva los 29 `BT-ES` del BOE con su numeración. Se midió el
24-10-2026. El anexo I se pasó a texto con `pdftotext -layout`, se comparó
renglón a renglón con los dos que mandó el buzón el 13-10-2026, y cada errata
medida en el BOE se buscó en él:

| Qué | BOE | Anexo 2.0, 13-10 | Portal, 21-10 |
|---|---|---|---|
| `BT-23`, el proceso | con `ubl:` | con `ubl:` | sin `ubl:` |
| `BT-48`, la descripción | del vendedor | del comprador | del comprador |
| `BT-ES-5`, `cbc:ServiceTypeCode` | bajo `cac:Party` | bajo `cac:Party` | bajo `cac:ServiceProviderParty` |
| `BT-ES-6` a `BT-ES-9` | con `cac:Invoice` y `cac:TaxSubTotal` | con `cac:Invoice` | `/in:Invoice/cac:AllowanceCharge/cac:TaxTotal/cac:TaxSubtotal/…` |
| `BG-ES-2`, impuestos o tasas por cargo | `0..n` | `0..n` | **`0..1`** |
| `BT-ES-23` y `BT-ES-24` | `/in:invoice` | `/in:Invoice` | `/in:Invoice` |
| `BG-24` de `RECT:IMPORTES` | `0..5` | `0..1` | **`0..3`** |
| La anulación | la factura en `cac:Response`, el nombre en `cac:PartyTaxScheme` | igual | la factura en `cac:DocumentResponse`, el nombre en `cac:PartyLegalEntity` |
| `BT-10` | `0..n` | `0..n` | `0..n`: la errata sigue |

Trae todo lo que el buzón dijo que corregía, también lo que la versión 2.0
dejó sin corregir, y el `ProfileID`, que el buzón no dijo que fuera a
corregir. Y dos cardinalidades que no salen de ninguna respuesta: un solo
impuesto o tasa por cargo, y tres importes rectificados en vez del `0..1` que
contestó el buzón. Los tres de `BT-3` y los tres códigos de L2.C casan ahora
con el grupo.

El anexo II del portal, comparado palabra a palabra con el del BOE, solo
cambia la maquetación: la barra doble de `cac:Response//cac:Status` sigue en
una de sus rutas. Los niveles de sus filas no se compararon.

**Qué cambió aquí.**

- `SPFE-IMPUESTO-O-TASA`, con más de un impuesto en un cargo, pasa de NOTA a
  AVISO. No es un error porque el BOE lo admite; el anexo del portal no, y el
  caso que se le mandó al buzón el 13-10-2026 sigue sin respuesta. La cuota
  de esos cargos sigue sin compararse.
- `SPFE-RECTIFICATIVA`: el aviso de un código repetido decía que la AEAT
  dejaba el grupo en `0..1`, y su anexo publicado le da `0..3`. La regla no
  cambia: con tres códigos, cuatro o cinco grupos ya repiten uno y salen en
  ese aviso, y más de cinco sigue en ERROR.
- Los textos que decían que la AEAT lo corregía en un anexo por publicar
  (la anulación, el nombre del vendedor) dicen ahora que el del portal ya lo
  escribe así, y el aviso del `ProfileID` del BOE lo dice también.

**Lo que no cambia.** Las tablas salen del BOE: `cius_es` se genera de su
XML, que es la norma, y el anexo del portal no es la orden. Si la AEAT
publica en el BOE una corrección de errores, `cius_es` se regenera y el
módulo deja de importar en cada fila que cambie. Los PDF del portal se
guardan en `informes/`, con su SHA-256, junto a los del buzón.

### La copia fiel, y el número que cambia

Hasta el 07-10-2026 este apartado se titulaba «La copia fiel, y los dos números
que cambian»: el recargo de equivalencia era el segundo, y con la orden ya no
lo es (abajo). Las familias se escribieron contra el anexo de abril; donde la
orden dice otra cosa, la fila lo dice con fecha.

Quien no emita por la solución pública tiene que mandarle una **copia fiel** en
UBL de cada factura, a la vez que la emite. El original sigue siendo el que es
—Facturae, CII, EDIFACT— y a la AEAT viaja una copia escrita en otra sintaxis.
Esa traducción **no la publica nadie**, y desde el 17-09-2026 consta que no la
va a publicar la Agencia. La respuesta del buzón trae además la regla que
decide el tono: un concepto sin equivalente **se puede omitir o llevar en una
extensión**, y lo que no sea equivalente no se valida. Es decir, que a la copia
le falte algo del original no es el fallo de nadie. Por eso todo lo que sale de
`validador/copia_fiel.py` es **NOTA**.

**Por dónde se empezó, y por qué por ahí.** Midiendo, el 20-09-2026, qué llevan
de verdad las facturas que hay aquí. Lo primero que salió fue la asimetría
entre sintaxis:

| Sintaxis | Facturas miradas | Rutas del mapa | Caminos con datos que el mapa no lee |
|---|---:|---:|---:|
| CII | 20 | 100 | **12**, todos términos europeos conocidos |
| Facturae | 14 | 50 | **67** |

Y dentro de esos 67, lo que decidió el orden de trabajo: no es que falten
datos, es que **cambia una cifra**. El esquema de Facturae define su total como
la base más los impuestos repercutidos **menos los retenidos**, y `BT-112` es
la base más las cuotas, sin restar nada. Quien copie campo a campo pondrá en la
copia un total que no es el suyo, y un número equivocado no se ve, mientras que
un hueco sí.

**Hasta el 07-10-2026 aquí se contaban dos cifras, y la otra era la cuota.** El
total de impuestos repercutidos de Facturae incluye el **recargo de
equivalencia**, y se escribió que `BT-110` no lo lleva, porque el borrador de
abril le daba al recargo un grupo propio. La orden no tiene ese grupo: el
recargo va en el desglose del IVA, `BG-23` —«También proporcionará información
sobre el desglose del recargo de equivalencia, en su caso»—, con su cuota en
`BT-117` y su tipo en `BT-119`, y con la categoría `N` de L4. Y como la orden
exige ajustarse a la EN 16931 (artículo 3.1), cuya BR-CO-14 hace de `BT-110` la
suma de los `BT-117`, la cuota total de la copia **lleva el recargo**, igual que
la de Facturae, y `BT-112` es la base más esas cuotas. De las dos cifras, al
copiar una Facturae solo cambia el total, y solo por la retención.

**Cuántas facturas están en ese caso: 6 de las 14**, las seis que llevan
retenciones. Cuatro llevan recargo, las cuatro dentro de las seis, y el recargo
ya no cambia ninguna cifra. Dos llevan suplidos.

**La segunda familia: lo evidente**, escrita el mismo día. Se llama evidente
porque casi todas sus filas son «llega igual» —la calle, la población, el
código postal, la provincia, el país, el teléfono y el correo pasan de un campo
a otro sin discusión, y el anexo los recoge uno a uno—. Se escribió entera por
las tres que estaban escondidas entre ellas, que no son evidentes y sí son
frecuentes:

| Lo que no era evidente | De 14 | Qué pasa |
|---|---:|---|
| La **serie** va pegada al número | 8 | el anexo tiene **un solo campo**, `BT-1`, «número y serie de la factura», y Facturae tiene dos. Nadie dice cómo se juntan: aquí se pegan sin separador, que es como los junta el código único del RD 238/2026 |
| La dirección **de fuera de España** junta código postal y población | 3 | `PostCodeAndTown` es un campo y la copia pide dos. Ni el esquema de Facturae ni el anexo dicen por dónde se corta la cadena |
| El **periodo de facturación** no estaba en el anexo | 9 | la norma tiene `BG-14` y el anexo de abril no lo recoge, aunque el esquema de Facturae lo hace obligatorio en las recapitulativas. La orden sí lo recoge, desde el 05-10-2026: «PERIODO DE LA FACTURA RECAPITULATIVA», `0..1`, con `BT-73` y `BT-74` |

Y lo que se queda en el original, que no lo dice nadie: el **idioma** (11 de
14), el **lugar de expedición** (8), y el fax, la página web y el CNAE de las
partes (5). Salen en **una sola nota** con la lista entera, no en cinco notas
seguidas: los importes con su cifra —uno que se queda fuera ya no cuadra con
ningún total de la copia— y los demás solo nombrados.

**La tercera familia: las líneas** (21-09-2026): lo que se factura, con su
cantidad, su precio y su IVA. Es la más larga de las tres y la que más se queda
fuera, pero lo que la hace útil son tres filas que desde los totales no se ven:

| Lo que esconde una línea | De 14 | Qué pasa |
|---|---:|---|
| El **identificador de línea** no existe | 14 | `BT-126` es obligatorio en el anexo y Facturae no tiene ninguno. Su esquema da `SequenceNumber`, pero significa otra cosa —el orden de la línea en un pedido— y 11 de las 14 no traen ni uno. Lo pone quien copia, y tiene que ponerlo **siempre igual**: si la misma factura se copia hoy con las líneas numeradas de una manera y mañana de otra, las dos copias dicen cosas distintas del mismo original |
| La **unidad de medida** es de otra lista | 11 | Facturae tiene la suya, 36 códigos de dos dígitos, y la norma pide UN/ECE, recomendaciones 20 y 21. De esos 36: 13 llevan el europeo en su propia etiqueta y valen tal cual, 16 lo llevan pero necesitan una `X` delante —los de embalaje—, 1 solo cuadra en mayúsculas y **6 no lo llevan**. Entre esos seis está `01`, «Units», que es justo el que escriben las 18 líneas medidas aquí: en la copia es `C62`. Viaja como atributo de la cantidad, y en el anexo de abril ni siquiera tenía fila: `BT-130` no estaba. En la orden sí está, desde el 05-10-2026, y obligatorio (`1..1`) |
| El **importe neto** se puede copiar del campo de al lado | 6 | `BT-131` es `GrossAmount` y no `TotalCost`, aunque el nombre invite a lo contrario. El esquema define `TotalCost` como cantidad por precio y `GrossAmount` como «TotalCost − DiscountAmount + ChargeAmount», y lo que la norma pide es el importe **después** de los descuentos de la línea |

Y lo que el anexo no pide de una línea: la **nota** (6 de 14), el **código de
artículo** (3) y la **fecha de la línea** (3). No sacan nota, y es la misma
regla de siempre: lo que llega no se cuenta, aunque no lo mire nadie.

**Las referencias que Facturae mete dentro de la línea** —pedido, contrato,
expediente, albarán— no son de esta familia a propósito: son las mismas que las
del documento, el anexo tampoco las recoge, y partir esa historia en dos sería
contarla dos veces a medias. Van con la sexta, dos apartados más abajo, donde
se ve que lo de «dentro de la línea» es justamente el problema.

**La cuarta familia: los cargos y las minoraciones** (21-09-2026). Facturae los
pone en dos sitios —dentro de la línea y sobre el total— y la norma también, así
que la mayor parte pasa sin discusión: el importe, el texto del motivo y las tres
sumas. Lo que no pasa es el IVA de los generales:

| Lo que esconde un descuento | De 14 | Qué pasa |
|---|---:|---|
| El **general no lleva IVA propio** | 6 | la norma agrupa las minoraciones y los cargos del documento **por categoría de IVA** —`BT-95` y `BT-96` van dentro del grupo, `BT-102` y `BT-103` en el de cargos— y Facturae los aplica antes del desglose, sobre la base entera. Con una sola categoría la cuenta está forzada y basta con escribirla; **con dos o más hay que repartir** cada descuento entre ellas, y no lo dice ningún texto: a prorrata de la base de cada una es lo único que deja cuadrar el desglose de la copia. Aquí pasa en 1 de las 14 |
| El **porcentaje no tiene sitio** | 12 | Facturae define el descuento con un porcentaje y un importe, y el anexo no recoge ni el porcentaje —`BT-94`, `BT-138`— ni la base sobre la que se calcula —`BT-93`, `BT-137`—. A la copia llega el importe, que es lo que cuadra las cuentas; de dónde salía, no |
| El **código del motivo** tampoco | 0 | `BT-98`, `BT-105`, `BT-140` y `BT-145` no están en el anexo, y aquí no se pierde nada porque Facturae tampoco los tiene: escribe el motivo en texto, y ése sí pasa |

Y un cabo de la familia anterior que se cierra aquí: un descuento de línea hay
que escribirlo **dos veces** en la copia —como grupo `BG-27` y restado dentro de
`BT-131`—, que es exactamente la cuenta que hace `GrossAmount` en Facturae.

**La quinta familia: el pago** (21-09-2026). Aquí está el choque más feo de
toda la tabla, y no se ve sin abrir las dos listas a la vez:

| Lo que esconde el pago | De 14 | Qué pasa |
|---|---:|---|
| El **medio de pago** dice otra cosa | 12 | Facturae tiene 19 códigos propios y la norma pide UNCL4461. Medido contra la lista que trae el esquematrón oficial: **los 19 existen también en UNCL4461** —diez tal cual, y los nueve que empiezan por cero en cuanto se les quita—, así que copiar el dígito no da un error: da un código válido que dice otra cosa. El `19` de Facturae es la tarjeta y el `19` europeo es un adeudo de cámara de compensación; el `04` es la transferencia y el `4` europeo es la reversión de un adeudo. Glosa traduce **cinco**, las que se sostienen por nombre, y de las demás dice que hay que elegirlas |
| **Varios vencimientos** no caben | 0 | `Installment` es `maxOccurs="unbounded"` en Facturae y el anexo tiene `BG-16` con cardinalidad 0..1 y una sola fecha en `BT-9`. Hay que elegir cuál viaja. **Ninguna de las 14 de aquí trae más de uno: el corte existe y no se ha visto**, así que se prueba provocado |
| La **cuenta de cargo** no está en el anexo | 8 | `BT-91` es término de la norma y el anexo no lo recoge —y la traen más facturas que la de abono, que sí viaja— |
| La **dirección de la sucursal** no viaja | 8 | de la cuenta, la norma se queda con el identificador y, como mucho, el BIC. Sale en la nota de lo que se queda en el original |

**La sexta familia: las referencias** (22-09-2026). Es la única que se
escribe sabiendo de antemano que casi nada llega, y aun así es de las que más
falta hacían, porque lo que se pierde no lo avisa ninguna regla:

| Lo que pasa con una referencia | De 14 | Qué pasa |
|---|---:|---|
| **Ninguna tiene campo** en la copia | 8 | Facturae sabe llevar siete referencias —el pedido y el contrato, cada uno del emisor y del receptor, el expediente, el albarán y el número de línea del pedido— y el anexo **no recoge ni una**: de `BT-11` a `BT-19` no hay ninguna, ni tampoco `BT-132`, ni en el anexo de abril ni en el de la orden. Se omiten o van en una extensión, y no las valida nadie |
| Queda **un hueco libre**, y no es para ellas | — | el anexo sí conserva una referencia de documento: `BT-10`, «un identificador asignado por el comprador para especificar rutas internas de la factura». Es el único sitio donde cabría algo, y meter ahí el pedido deja una copia válida que dice otra cosa: el mismo fallo que copiar el dígito del medio de pago. Lo que en Facturae sí encamina —los centros administrativos— tiene sus propios campos españoles, `BT-ES-9`, `BT-ES-10` y `BT-ES-11` |
| Viven **dentro de la línea** | 8 | y la norma las pone en el documento. Ninguna de las 14 escribe una referencia en la cabecera, aunque el esquema lo permita: las 8 que traen alguna la traen en la línea, y **3 traen más de un albarán distinto**, así que este corte, al revés que el de los vencimientos, sí se ha visto |
| Las **fechas** no existen para la norma | 3 | Facturae le pone fecha a cada referencia —seis en total, contando la del albarán— y para la norma una referencia es un identificador suelto: ninguna de `BT-12` a `BT-17` lleva fecha al lado |
| La **factura anterior** pide una fecha que no hay | 0 | `BG-3` es el único grupo de referencia que sí viaja, y el anexo pone `BT-26` —la fecha de expedición de la referenciada— en **1..1**, donde la norma europea no obliga. La factura asociada de Facturae no lleva ninguna, y la rectificativa solo está obligada a escribir la suya con los criterios 01 y 02: sin fecha no se monta el grupo. Ninguna de las 14 se refiere a otra factura, así que se prueba provocado |
| El **adjunto** no cabe, y el grupo está ocupado | 2 | `BT-125` no está en el anexo, ni en el de abril ni en el de la orden, y el grupo donde iría, `BG-24`, lo usa para otra cosa: el **QR fiscal** —con valores fijos y la dirección aparte, en `BT-ES-47` en abril y en `cbc:UUID` en la orden— y el número de la **autorización** del Departamento de Gestión Tributaria. Las dos son contenido que la factura no tiene: las pone quien copia, sacándolas de su sistema. Desde la orden, `BG-24` lleva además los datos de la rectificativa: `RECT:TIPO`, `RECT:MODALIDAD` y `RECT:IMPORTES` |

De propina, el que cierra el cabo de la tercera familia: `SequenceNumber`, el
que no servía como identificador de línea, es `BT-132` —la línea **del
pedido**—, que tampoco está en el anexo. El esquema lo declara `xs:double`, así
que las tres facturas que lo traen escriben `1.0` y `2.0`: una referencia con
decimales.

**La séptima familia: el desglose del IVA** (22-09-2026). Base, cuota y tipo
llegan igual. Lo caro es lo otro:

| Lo que esconde el desglose | De 14 | Qué pasa |
|---|---:|---|
| Al **0 %** no se sabe de qué categoría es | 3 | `BT-118` es obligatorio y el código de impuesto de Facturae dice **qué impuesto** es, no de qué categoría. A tipo positivo la deducción está forzada —IVA a tipo positivo es la `S`—; un cero puede ser `E`, `O`, `Z`, `K`, `G` o `AE`. Lo único que lo estrecha es la fiscalidad especial de la línea, y solo a dos: su `01` es la `E` y su `02` es la `O` |
| El **motivo de la exención** está en prosa | 3 | la norma lo quiere colgando de la entrada del desglose y Facturae lo escribe en texto libre dentro de la línea, precedido del código del impuesto —lo manda su propio esquema: «07 exenta por…»—. Hay que **leer esa cadena**, y ni el prefijo es fiable: la muestra oficial del Ministerio no lo escribe. Y si no se lee, el motivo no llega por ningún otro sitio, porque `BT-127` no está en el anexo. En la copia deja de ser opcional en cuanto la categoría es `E`: lo exige `BR-E-10` |
| El **código del motivo** no existe en Facturae | 0 | el anexo pide la lista **CEF VATEX** —solo `VATEX-EU` y `VATEX-ES`—, en el desglose y en la línea. Facturae escribe prosa: el código lo elige quien copia |

Y una fila que hasta el 22-09-2026 estaba **mal** y se ha corregido: la **clave
de régimen**. Decía que era `SpecialTaxableEventCode` y que llegaba a `BG-32`.
No lo es. La clave de régimen es la lista L3A y el anexo la pide **obligatoria**,
una o dos por línea; `SpecialTaxableEventCode` solo distingue dos casos —`01`
«sujeta y exenta» y `02` «no sujeta»— y en L3A el `01` es «operación de régimen
general», que es lo contrario. El mismo dígito diciendo lo otro, como en el
medio de pago. Las 3 facturas de aquí que traen fiscalidad especial traen el
`01`.

**La octava familia: la cabecera** (22-09-2026). Es la que más «lo pone quien
copia» tiene, y no por casualidad: la cabecera es donde la copia se identifica a
sí misma, y eso no está en el original.

| Lo que esconde la cabecera | De 14 | Qué pasa |
|---|---:|---|
| La **moneda del IVA** no hay que copiarla | 14 | y es el único caso de toda la tabla en el que el fallo es copiar **de más**. `TaxCurrencyCode` es obligatorio en Facturae y repite la moneda de la factura; `BT-6` solo tiene sentido cuando el IVA se contabiliza en otra. En cuanto se escribe, `BR-53` exige `BT-111` —la cuota en esa moneda—, que Facturae no lleva: lleva el tipo de cambio. Copiar el campo por estar escrito deja una copia que **no cumple la norma** por un dato que no aportaba nada |
| El **tipo de factura** se arma con tres campos | 14 | `BT-3` sale de `InvoiceDocumentType`, de `InvoiceClass` y de `FileHeader/InvoiceIssuerType`, que está fuera de la factura y es lo que separa la 380 de la **389** y la 384 de la **471**. Las 14 de aquí son `FC` + `OO`, o sea 380 |
| La **especificación** la escribe quien copia | 14 | `BT-23` y `BT-24` son obligatorias y de valor fijo: el proceso (`urn:aeat:names:specification:ubl:schema:profile:B2B`, fijo, ni siquiera distingue el B2G) y la especificación que sigue el documento (`urn:cen.eu:en16931:2026#conformant#urn:aeat.es:spfe:1.0.0:extended`). Son los de la orden; hasta el 07-10-2026 aquí estaban los de abril, que terminaban en `…:schema:B2B` y `…:CIUS-ES-SPFE:1.0.0`. Una factura no dice eso de sí misma |
| Cinco **huecos** sin origen | — | `BT-10`, `BT-20`, `BT-21`, `BT-114` y `BT-166` son opcionales y Facturae no tiene ninguno: la referencia interna del comprador, las condiciones de pago, el código de la nota, el importe de redondeo y la hora de expedición. Lo correcto es dejarlos vacíos; el fallo no es olvidarlos, es rellenarlos con lo que más se les parezca |

**La novena familia: las partes** (22-09-2026). Las direcciones y los contactos
ya estaban en la segunda. Lo que quedaba es quién es cada uno, y la nota sale de
la fila que menos se espera:

| Lo que esconde una parte | De 14 | Qué pasa |
|---|---:|---|
| El **nombre de una persona física** va en tres campos | 7 | `Name`, `FirstSurname` y `SecondSurname`, y en la copia va en uno solo y obligatorio. Nadie dice en qué orden ni con qué separador: no es lo mismo «Juana Mauriño» que «Mauriño, Juana» para quien busque la factura por su titular. Y quedarse solo con el nombre —que es lo que hace el validador para **leer** la factura, porque pegarle los apellidos sería inventar un formato— aquí perdería dos apellidos |
| Los **datos registrales** son seis campos | 8 | libro, registro, hoja, folio, sección y tomo, y `BT-33` es una línea de texto libre. Hay que redactarla, no copiarla |
| El **NIF** es la fila que mueve la orden | 14 | en Facturae es un solo campo por parte, y la orden publicada el 05-10-2026 da dos sitios a cada una: el vendedor en `BT-31`, con «VAT» y el prefijo de España, o en `BT-32` con esquema «LOC» y `@schemeID` «FC»; el comprador en `BT-48` con «VAT» o en `BT-47` con «LOC» y «FC». `BT-31` ni estaba en el anexo de abril. Hasta el 07-10-2026 esta fila decía que el texto nuevo la movería seguro, con lo anunciado el 10-09-2026 |
| El **nombre comercial** no está en el anexo | 8 | ni `BT-28` ni ninguno de los identificadores de las partes. De las dos, el anexo se queda con el nombre y el NIF |

Lo que dice el módulo, con los importes al lado:

| Nota | Cuándo sale | Qué dice |
|---|---|---|
| `COPIA-TOTAL` | hay retenciones | el total de la copia es la base más las cuotas, sin restar la retención |
| `COPIA-SERIE` | la serie trae texto | en la copia, el número de la factura es la serie y el número juntos |
| `COPIA-DIRECCION` | hay dirección de fuera de España | el código postal y la población hay que partirlos en dos campos |
| `COPIA-PAGO-MEDIO` | hay medio de pago | el código es de la lista de Facturae y en la europea significa otra cosa |
| `COPIA-VENCIMIENTOS` | hay más de un vencimiento | en la copia cabe uno |
| `COPIA-CARGO-IVA` | hay descuentos o cargos generales | en la copia van agrupados por categoría de IVA, y aquí no la llevan |
| `COPIA-LINEA-UNIDAD` | una línea trae unidad de medida | el código es de la lista de Facturae y la copia pide uno de UN/ECE |
| `COPIA-LINEA-NETO` | `TotalCost` y `GrossAmount` no valen lo mismo | el importe neto de la línea es el segundo, no el primero |
| `COPIA-MONEDA-DEL-IVA` | hay moneda de contabilización del IVA | en la copia no debe ir si repite la de la factura: pide `BT-111` |
| `COPIA-DESGLOSE-CERO` | hay una entrada al 0 % | la copia necesita una categoría que el código de impuesto no dice |
| `COPIA-NOMBRE` | una parte es persona física | su nombre va en tres campos y en la copia va en uno |
| `COPIA-REFERENCIAS` | hay pedido, contrato, expediente o albarán | ninguna tiene campo en la copia, y el hueco que queda libre no es el suyo |
| `COPIA-FACTURA-PREVIA` | se refiere a otra factura | el número va con su serie, y la fecha de la referenciada es obligatoria |
| `COPIA-SUPLIDO` | hay suplidos | son `BT-179` y `BT-180`, de la edición de 2026: la orden los pone en el `BG-34` de los cargos en nombre de un tercero, con «SUPL» en `cac:CollectionInvoiceLine/cbc:ID`, y no les da ruta |
| `COPIA-SIN-SITIO` | hay algo que no viaja | la lista de lo que se queda en el original |

Hasta el 07-10-2026 había una nota más, `COPIA-CUOTA`, que salía con recargo de
equivalencia y decía que la cuota de la copia no lo lleva porque el anexo le
daba grupo propio; y `COPIA-TOTAL` salía también con recargo, no solo con
retenciones. Con la orden el recargo va en el desglose del IVA y la cuota de la
copia lo lleva (arriba, al principio del apartado), así que la una desaparece y
la otra sale solo cuando hay retenciones.

Sobre las 14 facturas de aquí: **las 14 sacan alguna nota**. Eran 11 hasta la
tercera familia, y las tres que callaban no eran facturas más limpias: eran las
que no tocaban ningún concepto de los once primeros. Todas tienen líneas. El
ejemplo publicado `ejemplos/fe-0001.xml` saca cinco —su serie, su idioma, la
unidad de su línea, su medio de pago y su moneda del IVA— y sigue saliendo
conforme, porque ninguna es un error.

**La tabla se escribe entera, con el porqué de cada fila**, en
`CORRESPONDENCIAS`: **107 conceptos** que nombran **los 33 campos españoles y
104 de los 116 términos europeos** de la orden, cada uno con lo que le pasa y
de dónde sale esa decisión. Hasta el 11-10-2026, con el anexo de abril, eran
97 que nombraban 92 de 104 europeos; ese día, 98 que nombraban 96 de 116; y el
13-10-2026, antes de mirar los españoles, 100 que nombraban 102. Los 12
europeos que quedan sin nombrar no son un hueco: son **los grupos**,
contenedores (`BG-4` a `BG-9`, `BG-22`, `BG-25`, `BG-29` a `BG-31` y `BG-33`).
Lo que se deja vacío a propósito sí tiene fila, la de los huecos: `BT-154`, la
descripción del artículo, `BT-149`, la cantidad a la que se aplica el precio,
y siete campos más que Facturae no tiene.

Los siete términos que la orden trae y el borrador no se miraron el
13-10-2026. El NIF va como NIF-IVA (`BT-31`), con el prefijo ES que Facturae
no escribe, o como NIF, y entonces el del vendedor va dos veces (`BT-32` y
`BT-30`); el del comprador, en `BT-48` o en `BT-47`, que la orden reutiliza.
La unidad de medida es `BT-130`, y no `BT-129` como decía la fila con abril.
La base de un impuesto de la línea que no es IVA es `BT-142`: en la copia ese
impuesto va como cargo de la línea, con un código de la L9 que Facturae no
tiene (su 07 vale para todos los impuestos especiales). Y el tipo de cambio es
`BT-167`, que se queda en «no se sabe»: en qué elemento va y en qué sentido se
lee lo dice `UNE-CEN/TS 16931-3-2:2026`, que aquí no está.

Los 33 campos españoles (`BT-ES-` y `BG-ES-`) se miraron el mismo día. Casi
todos tienen origen en la factura, y muy pocos llegan tal cual:

- **las retenciones** van en su grupo, pero el concepto de cada una
  (`BT-ES-21`, de la L5: siete supuestos del reglamento del IRPF, tres del de
  Sociedades y «Otros») no está en Facturae, que dice qué impuesto se retiene
  y no por qué;
- **un impuesto que no es IVA** va como cargo, en la línea o en el documento y
  nunca en los dos sitios, porque los dos suman a la base;
- **los anticipos** no van enteros a `BT-113`: la orden aparta los que
  devengaron el IVA, y la fecha de pago (`BT-ES-2`) es una sola, y solo si la
  factura quedó pagada;
- **la rectificativa**: el motivo de Facturae dice qué dato estaba mal, y la
  L2.A al amparo de qué artículo. Se traducen el 82, el 83 y el 84 (R1) y el
  85 (R2); el R3, los créditos incobrables, no tiene código en Facturae;
- **el indicador de copia** (`BT-ES-1`) es siempre «true» en una copia fiel, y
  no sale de `InvoiceClass`, que tiene su propia «copia» y habla de otra cosa.

Dos no salen de ninguna parte, la minoración en nombre de un tercero y la
situación del inmueble, y van a la fila de los huecos. Al mirarlos salieron
dos frases de la tabla que ya no eran verdad: la del tipo de factura contaba
las 14 de aquí como 380, y una la expide el destinatario (389); y la del
nombre comercial daba `BT-30` y `BT-47` por no recogidos, cuando la orden los
recoge para el NIF.

Los estados son nueve, y los cuatro que fueron añadiéndose
familia a familia son los que no se pueden juntar con ningún otro sin borrar
justo lo que hay que decidir:

| Estado | Qué significa | Ejemplo |
|---|---|---|
| llega igual | mismo dato, mismo sitio | la población, `BT-37` |
| llega, pero en la extensión española | el anexo le da grupo propio | las retenciones |
| llega con otro número | el importe de la copia no es el de la factura | `BT-112` |
| **llega, pero cortado de otra manera** | el dato viaja entero y los campos no se cortan igual en los dos formatos | la serie, que se junta; el código postal de fuera, que se parte |
| **llega, pero el anexo no lo pide** | la norma tiene el término y el anexo no lo lista: llega y no lo mira nadie | la persona de contacto; el porcentaje del cargo del documento |
| **llega, pero el código es de otra lista** | el campo existe en los dos sitios y el valor no vale: cada formato lo escribe con su vocabulario | la unidad de medida, `01` frente a `C62` |
| **no está en la factura: lo pone quien copia** | el anexo pide un campo que Facturae no tiene | el identificador de línea |
| no tiene sitio | se queda en el original | el idioma |
| no se sabe todavía | lo desbloquearía una ruta para `BT-179`, que tampoco da la orden publicada | el total a pagar |

Tres filas siguen en «no se sabe» a propósito: el total a pagar (la misma duda
de `SPFE-TOTAL-A-PAGAR`), los importes retenidos que no son de impuestos y el
tipo de cambio. Los suplidos salieron de aquí el 07-10-2026, al leer la orden.

Y tres cepos, porque una nota cuyo porqué ya no está escrito es peor que no
tenerla:

- si alguien quita una fila de la tabla y deja la regla que la usa, **el
  paquete no se monta** (`TablaIncompleta`);
- y los términos que cada fila nombra **se comparan con el anexo**, con los
  116 europeos y los 33 españoles de `cius_es.CAMPOS`: una fila que diga que
  algo llega a un término que el anexo no recoge, o que diga «el anexo no lo
  pide» de uno que sí recoge, deja la suite en rojo. Provocado por los dos
  lados;
- y ningún término del anexo se queda sin fila, europeo o español, salvo los
  grupos europeos: uno que ninguna fila nombre deja la suite en rojo. Hasta el
  13-10-2026 apartaba además los dos campos que se dejan vacíos; desde
  entonces tienen fila, la de los huecos, y el cepo no tiene excepciones.
  Provocado.

El segundo cepo saltó como se esperaba el 11-10-2026, al salir `cius_es` del
XML del BOE, en dos filas que decían «el anexo no lo pide» de términos que la
orden sí pide: el periodo de facturación (`BG-14`) y el porcentaje del cargo
de línea (`BT-143`). Las dos se corrigieron, la segunda partiéndose en dos. Lo
que ese cepo no veía eran los términos nuevos que ninguna fila nombra: así
pasaron dos días los siete de arriba sin que nada saltara. Para eso es el
tercero, del 13-10-2026.

Lo que esto **no** es: no convierte nada (aquí no se escribe ninguna copia) y
no valida la copia, que es otro documento con sus propias reglas `SPFE-`. Hasta
el 13-10-2026 decía también que no adivinaba de dónde salen en Facturae los
campos españoles del anexo. Ahora la tabla lo dice, con su porqué, y es
lectura de aquí: la orden los describe en UBL y de Facturae no dice nada.

## Que a esto se llegue desde fuera

Una herramienta que nadie encuentra no le sirve a nadie, y esto no se nota
desde dentro: la página funciona perfectamente para quien ya sabe la dirección.
Se notó buscando `"glosa-e.com"` en un buscador el 11-09-2026 y comprobando que
**no salía ni una vez**. No estaba abajo: no estaba.

No había `robots.txt`, ni `sitemap.xml`, ni canónica, ni tarjeta social. Ahora
las tres cosas se escriben al montar, sobre lo que haya quedado en la carpeta,
y no página a página: así no puede pasar que una página nueva salga sin ellas y
no se entere nadie.

### Los 160 códigos, cada uno con su dirección

El catálogo ya traía los 160 con su ancla. **Un ancla no es una página**:
`incidencias.html#BR-CO-10` es, para un buscador, la misma dirección que
`incidencias.html`, así que esas 160 puertas contaban como una.

Y son exactamente lo que se teclea. Nadie busca «validador de facturas
electrónicas»: busca **el código que le acaba de escribir su programa**, con el
problema delante y ahora mismo. Son 160 búsquedas de poquísimo volumen cada una
y de intención altísima.

Cada código tiene ahora su página —`/codigo-BR-CO-10`— con lo que el catálogo
ya sabía y una cosa más, que es la que ningún otro validador puede imprimir:

| | |
|---|---|
| De dónde viene | EN 16931 — la norma europea de factura electrónica |
| Lo escribe | `validador/en16931.py:412` |
| Puede salir como | error |

La línea del fuente que emite el aviso. Es la tesis del proyecto puesta en una
fila de una tabla, ciento sesenta veces.

Se generan del mismo catálogo y del mismo armazón que la página de todos, así
que no hay una segunda verdad que mantener: un código nuevo en `firma.py`
aparece con su página sin que nadie se acuerde de nada. Lo que es sólo del
catálogo —su titular y el buscador— va marcado en la plantilla con
`<!-- SOLO EL CATALOGO -->` y se quita al generar cada ficha; si esa marca
desaparece, **no se monta**, porque 160 páginas con el titular «Qué significa
cada aviso» y un buscador que no filtra nada es de las cosas que no dan error.

### El fallo que casi se publica: 160 páginas y 27 descripciones

De los 160 códigos, aquel día sólo **15 tenían explicación propia**. Los otros
145 llevaban la de su familia, y eso estaba dicho en la página. Hoy la llevan
los 214, uno a uno; lo de abajo cuenta cómo se cerró. Poniendo esa explicación como
descripción de la página —que es lo natural, y lo primero que se escribió— el
recuento salía así:

```
descripciones distintas: 27 de 160
```

Ciento cuarenta y cinco páginas que en un buscador salen con la misma frase. No
falla nada, no se cae nada: simplemente quien viera cuatro resultados idénticos
no sabría cuál abrir, y probablemente no abriría ninguno.

La descripción empieza ahora por el código, que es lo único que los distingue a
todos, y sigue con la explicación:

> `BR-CO-10` en una factura electrónica: error de EN 16931. Reglas de negocio
> de la norma europea EN 16931. No las pone este validador: las pone la norma…

Son 160 de 160, y encima la primera línea contesta ya lo que se ha venido a
preguntar. Hay una prueba que lo comprueba, porque esto se estropea solo: basta
con que alguien «simplifique» la descripción para que vuelvan a ser 27.

### Los que no estaban escritos: de 160 a 206

El catálogo se lee del fuente, y eso deja fuera a los que no están escritos.
`iva.py` compone seis de sus códigos al validar, pegándole la categoría de la
operación a un patrón:

```python
Incidencia(f"BR-{regla.codigo}-08", ERROR, …)
```

Ahí no hay una cadena que leer: cuál es no se sabe hasta que hay una factura
delante. Se contaban a la vista como huecos —la página decía «otros 6 se
componen al validar»—, que era honrado y dejaba a **46 códigos reales sin
página**. Le salen a alguien en su informe y no tiene dónde mirar. `BR-E-10`
sale en once de las 179 facturas medidas aquí, que lo pondría entre los veinte
más frecuentes de todo el catálogo.

Ahora el módulo que los compone **declara lo que compone**, en un
`CODIGOS_COMPUESTOS` pegado a la tabla de la que salen, y `codigos.py` lo
recoge. Sigue sin adivinarse nada: lo que no esté declarado sigue contándose
como hueco, y `HUECOS_CONOCIDOS` —hoy vacía— sigue poniéndose en rojo el día
que aparezca una forma nueva de emitir un código.

**Aquí ponía «son 46 y no 54», y era falso.** Se decía que IGIC e IPSI
llevan `tipo = cualquiera` y `motivo = libre`, que por eso ocho de esos
códigos no se disparan nunca y que publicarlos sería inventarlos. Lo primero
era verdad del código y lo segundo no era verdad de la norma: el esquematrón
tiene esas ocho reglas. Son 54. La corrección está en la sección siguiente, y
esto se deja escrito en vez de borrado.

Por eso la declaración no se cree sola. `tests/test_compuestos.py` la sostiene
con tres opiniones que tienen que coincidir, y una cuarta al revés:

| Quién lo dice | Qué aporta |
|---|---|
| La lista escrita a mano en la prueba | envejece, y por eso está: se pone en rojo si la derivación cambia sin que nadie lo diga |
| Lo que `iva.py` declara | sale de la tabla de reglas, no de la memoria |
| Lo que sale al provocar las cuatro reglas con cada categoría | la medida, contra las dos lecturas |
| ~~Los ocho que no existen~~ | comprobaba que **no** salían, y era la equivocación: se sustituyó por el texto del esquematrón, ver abajo |

Las 46 explicaciones se escribieron antes de enchufar nada, y el catálogo pasó
de 160 a 206 en un solo movimiento. Es deliberado: hacerlo al revés habría
publicado «46 códigos con la explicación de su familia» el día siguiente de
haber publicado que no quedaba ninguno.

### Los ocho que se dieron por inexistentes, y treinta y nueve códigos sin su cero

La sección de arriba publicó que eran 46 y no 54, y era falso. Se vio al día
siguiente, el 13-09-2026, al hacer lo que no se había hecho: medir la
cobertura contra el esquematrón oficial (`eInvoicing-EN16931`, v1.3.16,
`EN16931-model.sch`, 201 reglas) regla por regla y no contra la tabla propia.
Salieron dos cosas.

**La primera, los nombres.** Buscando los códigos de aquí en el esquematrón
coincidían 43. Quitando los ceros, 82. La norma escribe `BR-S-08` y `BR-O-05`,
y el IVA de aquí publicaba `BR-S-8` y `BR-O-5`: treinta y nueve códigos con
otro nombre. Quien copiara el código de un rechazo de otro validador para
buscarlo en la página de incidencias no encontraba la ficha. Ninguna prueba lo
vio porque todas estaban escritas con el mismo nombre que el código.

Ahora `iva.py` compone con dos cifras; un guardián en `tests/test_codigos.py`
exige esa forma a todo código `BR-` del catálogo —la forma y no una lista, que
la escribiría mal la misma mano—, y `vercel.json` lleva una redirección
permanente de cada nombre sin cero a su ficha. Son 46: las 39 direcciones que
llegaron a publicarse, más `BR-CL-1` y las seis de abajo, porque sin el cero
es como lo teclea de memoria quien lo busca. Otras dos pruebas comprueban que
no falte ninguna y que ninguna tape una ficha o lleve a una que no existe; las
dos se provocaron rompiendo `vercel.json`.

**Toda ficha que existió, en la lista.** Lo que impide que retirar un código
deje su ficha en un 404 es `tests/fichas_publicadas.txt`: lo que está ahí y ya
no en el catálogo tiene que redirigir. Pero se escribió el 11-10-2026, y
`COPIA-CUOTA`, retirada el 07-10, dio 404 hasta el 25-10 con la prueba en
verde. Desde ese día la lista sale de la historia y no de la memoria:
`herramientas/fichas_que_existieron.py` recorre cada commit desde el primero
con fichas y junta los códigos de cada catálogo (con el lector de hoy, y con
el suyo los de antes del 23-09, que el de hoy no entiende). Ese día dio esas
39 direcciones de septiembre, que redirigían como alias pero no estaban
apuntadas, y nada más; con `--produccion`, cada retirado acabó en 200.

El recorrido entero lleva unos diez minutos y en GitHub la copia viene sin
historia, así que no va en la suite. Lo que va, y se provocó: que cada ficha
redirigida esté en la lista (o sea el alias sin cero de una que lo esté); que
la lista solo crezca, comparada con cada commit que la tocó, que es lo único
que ve quitar a la vez una línea y su redirección; y que la herramienta siga
sabiendo leer, sobre tres commits: ve irse `COPIA-CUOTA` y lee uno de
septiembre con su propio lector. Las dos últimas se saltan en una copia sin
historia.

**La segunda, IGIC e IPSI.** La tabla de `iva.py` les ponía `tipo = cualquiera`
y `motivo = libre`, con un comentario que decía que la norma no ataba a esas
dos categorías. Nadie lo había leído en el esquematrón. Dice esto:

| Regla | Texto |
|---|---|
| BR-AF-05, 06, 07 | el tipo del IGIC *«shall be 0 (zero) or greater than zero»* |
| BR-AF-10 | la entrada de IGIC *«shall not have a VAT exemption reason»* |
| BR-AG-05 a 10 | lo mismo para el IPSI |

Reproducido antes de tocar nada: una entrada «IGIC al 7%, Régimen especial de
Canarias» salía **limpia**, y una línea de IGIC al −7% también. La norma rechaza
las dos. Y la prueba que lo sostenía se llamaba *«del IGIC y el IPSI no se
opina»*: exigía que esa factura pasara.

El arreglo es un estado nuevo, `NO_NEGATIVO`, y el motivo `PROHIBIDO`, y se
quitaron `CUALQUIERA` y `LIBRE`, que solo existían para esto. Lo que hace que
no vuelva a pasar son tres cosas, y las tres se provocaron:

| Guardián | Rompiéndolo |
|---|---|
| `test_la_tabla_dice_lo_que_dice_el_esquematron`, con el texto de cada regla copiado en la prueba | devolver el motivo a obligatorio en el IGIC: nueve pruebas en rojo |
| las pruebas de IGIC e IPSI de `test_iva.py`, por UBL y por CII | dejar de cazar el negativo: seis en rojo |
| la tabla se niega a cargar con un estado que las reglas no saben comprobar | poner `"cualquiera"` al IPSI: `ValueError` al importar |

La tercera es la importante. El estado mudo entró por un `else: mal = False`:
un estado que no se queja de nada no rompe nada y no se nota nunca. Ahora esa
rama no existe.

**Lo que no cambió, medido.** Las 179 facturas del corpus dan las mismas 1241
incidencias antes y después: nueve salen con el nombre nuevo y no hay ninguna
queja nueva, porque ninguna lleva IGIC o IPSI con motivo ni con tipo negativo.
El catálogo pasa de 206 a 214 códigos.

**Por qué no lo cazó la comprobación de cuatro opiniones.** Porque tres
opiniones que salen de la misma tabla coinciden también cuando la tabla está
mal. La cuarta, «los ocho que no existen no salen», comprobaba justo la
equivocación. Lo que faltaba era una opinión de fuera del repositorio, y ahora
está: el texto del esquematrón, escrito en la prueba.

### El sitemap, el robots y la canónica

`vercel.json` lleva `cleanUrls`, así que lo que se sirve de verdad es
`/incidencias` y `/incidencias.html` contesta con un 308. El sitemap y la
canónica dicen **la de destino**, no la que redirige: mandar a un buscador a
una mudanza es hacerle perder el viaje.

**Y los enlaces de una página a otra también**, desde el 25-09-2026. Hasta
entonces seguían diciendo `./legal.html`: 225 por ficha de código y 396 en el
catálogo, cada uno un 308. Search Console contaba las dos formas de la misma
página por separado. Las plantillas de `web/` siguen escribiendo `.html`,
porque se sirven en local con `http.server`, que no sabe de `cleanUrls`. Es el
montaje el que los pasa a la forma limpia, y **se niega** si queda un enlace
de casa con `.html` que no ha sabido limpiar. Para ver en local el sitio
montado como lo sirve Vercel —direcciones limpias, 308, `404.html` y
mayúsculas distinguidas— está `herramientas/servir_sitio.py`, que es el
servidor `sitio` de `.claude/launch.json`.

**Y al pie de cada ficha, los vecinos y no la familia entera.** La familia
europea tiene 219 códigos y cada ficha suya enlazaba a los otros 218: en BR-47
eran 223 de sus 532 palabras visibles. Por encima de 24 hermanos se enlazan los
12 más cercanos de la misma serie, y la familia entera queda a un clic, en el
catálogo. Que eso fuera lo que frenaba la indexación era una hipótesis, y a
las cuatro semanas no se sostiene: el 23-10-2026 Search Console tenía 98
páginas indexadas (eran 110) y 321 descubiertas sin visitar (eran 295).

**La portada enlaza los tres últimos artículos de la bitácora.** Ese mismo
23-10, de los seis artículos, cuatro estaban sin visitar y otro rastreado sin
indexar, y la portada, que es lo que Google más visita, no llevaba a ninguno.
La sección la rellena el montaje en el hueco `<!-- AQUI VA LO ULTIMO DE LA
BITACORA -->` de `index.html`, y se niega a montar si hay entradas y el hueco
ha desaparecido. Que esto haga que se indexen también es una hipótesis: se
mira el 20-11-2026.

El sitemap lleva **`lastmod` solo donde la fecha es cierta**: en las entradas
de la bitácora y en su índice. La de cada entrada es la más reciente entre su
`data-fecha` y sus marcas de «Corregida el…» o «Actualizada el…», porque las
hay que se tocaron un mes después de publicarse. Para el resto lo único que se
podría poner es la fecha en que se montó el sitio, que es la misma para todas
y no dice nada de si el contenido cambió. Una fecha que miente vale menos que
ninguna.

**El código de cada incidencia del informe enlaza su ficha**, desde el
25-10-2026, y se abre en otra pestaña: el informe se pinta en la página con el
fichero que se soltó, y saliendo de ella se pierde. El informe lo pinta el
navegador, así que la página tiene que saber qué códigos tienen ficha, y se lo
dice el montaje: escribe la lista de las fichas que acaba de escribir en el
`data-fichas=""` del `#informe` de `index.html`, y se niega a montar si hay
catálogo y el hueco no está una vez. Sin montar la lista está vacía y el
informe sale en texto, como antes. Son 4,8 KB más en la portada con los 408
códigos.

**Y cada artículo y cada ficha acaban en Sigue las novedades**, una línea con X
y el perfil de LinkedIn, que salen de `CUENTA_DE_LA_MARCA` y
`PERFIL_DEL_TITULAR`. El plan pide tres formas de seguir: el canal Atom
existe desde el mismo día (abajo), y la línea lo nombra solo cuando el sitio
monta las novedades; el boletín de LinkedIn todavía no, y una línea que manda
a un canal que no hay es un cartel. Va detrás del único `</article>` de la
página, y el montaje se niega, antes de escribir nada, si un artículo trae
otro o el armazón de las fichas trae uno suyo.

**Las novedades, en una página y en un canal Atom**, desde el 25-10-2026:
`novedades.html` y `novedades.xml`, con cada regla nueva o retirada, por
fecha. Nacieron con los artículos de la bitácora mezclados, y ese mismo día
se quitaron: cada artículo se contaba dos veces, en su índice y aquí. Los
artículos tienen su propio canal, `bitacora.xml`, que el montaje escribe de
las mismas entradas que el índice y solo si hay alguna. Las reglas se apuntan
a mano en `web/novedades.txt`, porque lo que mira un código nuevo y por qué
no está escrito en ningún sitio del que se pueda sacar. Y como lo que
se apunta a mano se queda atrás, **el montaje se niega** (`SinNovedades`, que
hereda de `NoSeMonta`) si el catálogo no cuadra con lo apuntado: un código
que no sale ni en la partida ni en ninguna novedad, uno que se da por
retirado y sigue, uno que se va sin decirlo, o uno que se retira sin haber
estado. Provocado: con BR-CO-09 quitado de la partida, `--sitio` sale con
`exit 2` y no deja carpeta.

La partida son los 390 códigos del 06-10-2026, el día que entró en vigor la
orden, medidos en `598f34c`, el último commit de ese día. La historia de
después se midió leyendo el catálogo de cada commit con el lector de hoy:
los códigos compuestos del IVA solo se resuelven con el `codigos.py` en su
carpeta, así que se copió el de hoy en cada commit antiguo. Salen 9
novedades, del 07-10 al 24-10, y hoy el catálogo tiene 408. Lo que esto
**no** vigila es el cambio de una regla que ya estaba: no se puede medir
desde fuera, y la página lo dice.

Los dos canales se sirven como `application/atom+xml`, su tipo (RFC 4287),
con una cabecera cada uno en `vercel.json`. Por eso la línea de seguir lleva
a la página y no al `.xml`: un navegador puede bajarlo como fichero en vez de
enseñarlo. En la página, **el botón Seguir las novedades** se despliega con
cada sitio donde recibirlas y lo que llega a cada uno: X, a diario; el canal
de las novedades, cada regla; el de la bitácora, cada artículo, este solo si
hay bitácora. Cada canal tiene un botón que copia su dirección entera, que es
lo que se pega en un lector; si el navegador no deja copiar, el botón se
cambia por la dirección a la vista. El boletín de LinkedIn entra el primero
el día que `BOLETIN_DE_LINKEDIN` tenga su dirección, y no antes. Correo
propio no hay a propósito: el plan del 22-10-2026 lo descartó (LSSI,
artículo 21, y guardar direcciones de terceros). La hora no se apunta en
ningún sitio y va la medianoche UTC del día. El id de cada entrada es el
ancla (`/novedades#id`) o la dirección del artículo, la misma que tenía
cuando los artículos iban en las novedades, y no cambia al corregir el
título, que es lo que hace que un lector no enseñe dos veces lo mismo. Quién
los lee no se mide.

### La prueba en directo de Google, y el arranque al primer gesto

Medido el 26-10-2026 en Search Console, con la sesión del titular: la prueba
en directo de la portada salía con "Se ha producido un error", y con ella
Solicitar indexación, que la hace primero. No era la cuota (esa dice "Cuota
superada"), ni el navegador (lo mismo en Chrome que en Brave), ni el sitemap
(leído ese día, 424 páginas), ni la dirección: `/?prueba=1` fallaba igual. El
rastreo normal sí funcionaba: la portada estaba indexada, rastreada el 23-10.
Lo que no funcionaba era pedirlo.

La primera lectura fue mala, y se queda escrita. Las dos que fallaban, la
portada y el banco, eran las dos que bajan el validador al abrirse, unos
10 MB, y se hizo que esperaran al primer gesto de una persona, contando mover
el ratón (4adc6e9). Publicado eso, seguían fallando.

Desde fuera no se ve qué hace el robot, así que se publicaron copias de las
dos, cada una con una sola cosa quitada, y se probaron una a una:

| Copia | Prueba en directo |
|---|---|
| el banco tal cual | error |
| el banco sin ningún script | bien |
| el banco solo con `glosa.js` | bien |
| el banco sin los oyentes del gesto | bien |
| la portada tal cual | error |
| la portada sin los oyentes del gesto | bien |

Y una página que no arrancaba nada y solo apuntaba en su HTML lo que le
llegaba, leída en el HTML probado: `pointerover`, `mouseover`, `pointermove` y
`mousemove` a los 121 ms, una vez cada uno, y dos `resize`. Ni clic, ni tecla,
ni dedo, ni rueda, ni arrastre. **El robot mueve el ratón**, y con
`pointermove` entre los gestos el validador arrancaba mientras él leía.

Así que el arranque espera a un gesto que el robot no hace: tocar, hacer clic,
una tecla, la rueda o arrastrar un fichero (`alPrimerGesto`, en `glosa.js`).
Quien solo pasa el ratón por encima arranca en el primer clic, antes de soltar
una factura. El `scroll` tampoco cuenta, porque lo dispara la propia página al
abrir una pregunta por su ancla. Lo vigila
`tests/test_arranque_al_primer_gesto.py`, con la lista de lo que hizo el
robot, y la comprobación de producción le da el gesto con un `keydown`,
porque abierta por un script la página se quedaba esperando sin error.

Publicado eso (25928a6), la prueba en directo de la portada y la del banco
salieron bien el mismo día, a las 12:26 y a las 12:27, y la portada en
producción seguía arrancando con una tecla, lista en 13,2 s.

Y el mismo día las cinco páginas sin fecha propia (portada, banco, Sobre
Glosa-e, aviso legal y catálogo) la llevan en el sitemap, de
`web/fechas.txt`. Cada fecha va con la huella de su página, sin comentarios,
y `tests/test_fechas_del_sitemap.py` se niega si la página cambia y la fecha
no. El catálogo lleva además la de la última novedad, si es más nueva.

### El aviso a Bing, por IndexNow

Desde el 23-10-2026, al final de cada tanda, después de publicar y de
comprobar producción:

```
./.venv/Scripts/python.exe -m validador --avisar-indexnow
```

IndexNow es el protocolo con el que se le dice a Bing qué páginas cambiaron,
en vez de esperar a que pase por el sitemap. Ese día Bing tenía indexadas 138
páginas, más que Google, y su panel decía que Copilot había citado una ficha
siete veces el 13-10.
**Google no lo usa**: no está entre los buscadores de su FAQ, así que esto no
toca las 321 páginas descubiertas sin indexar de Google.

**La clave se publica, y no es un secreto.** El protocolo pide un fichero
`<clave>.txt` en la raíz que la lleve dentro, y el buscador lo lee de ahí
para creerse que el aviso es del dueño del dominio. Cualquiera la puede leer,
y solo sirve para avisar de direcciones de `www.glosa-e.com`. Está en
`paquete.CLAVE_DE_INDEXNOW` y el montaje escribe su fichero junto a
`robots.txt`. La regla de no manejar claves va por las que abren algo; esta
excepción la decidió el titular el 23-10-2026.

Tres decisiones, cada una con su negativa y su prueba rota a propósito:

- **Solo lo que cambió.** La FAQ de IndexNow dice que no está pensado para
  mandar el sitio entero, y que avisar de lo que no cambia gasta la cuota de
  rastreo. Se apunta lo avisado (en `glosa-indexnow.json`, dentro de la
  carpeta común de git, que no se versiona y comparten los worktrees) y se
  compara con lo montado. Lo que cuenta es el contenido: sin la huella `?v=`,
  los scripts, los estilos ni la política de contenido. Sin eso, tocar
  `glosa.css` cambiaba las 418 páginas a la vez. La primera vez solo apunta.
- **Que producción sirva ya lo que se avisa.** Se compara lo montado con las
  huellas de `dist/rueda.json` de producción, que lleva la de cada fichero
  publicado. Medido el 23-10-2026: coinciden las 419 páginas HTML, una vez
  igualados los saltos de línea de Windows. Pedir las 418 páginas una a una
  costaba 201 s y 23 cortes desde la conexión desde la que se publica; con
  `rueda.json` es una petición. Si no cuadra (el despliegue no ha terminado, o
  lo montado no es de `main`), no se manda nada.
- **Que la clave se sirva**, porque sin ella Bing contesta 403 y no indexa
  nada de lo avisado.

Cualquier negativa sale con código 2 y no apunta nada: lo que no se avisó hoy
se avisa la próxima vez, porque se compara con lo último avisado y no con el
último despliegue. Si el sitio se monta y se publica sin correr esto, no se
pierde nada; se queda esperando.

### La tarjeta social

Cuando alguien pega la dirección en LinkedIn, en un grupo de WhatsApp o en un
correo, lo que sale no es la página: es lo que digan las etiquetas `og:`. Sin
`og:image` sale un rectángulo gris, y un rectángulo gris al lado de un enlace
es lo que la gente no pulsa.

Ninguna red social admite SVG ahí —ni X, ni LinkedIn, ni WhatsApp, ni
Facebook—, así que tiene que ser un PNG de 1200×630. Lo genera
`herramientas/tarjeta.py` con la Literata que sirve la página y los mismos
colores de `glosa.css`, y va versionado ya hecho: armarlo al montar obligaría
a instalar Pillow **en cada despliegue**, para producir un fichero que cambia
una vez cada seis meses. Es lo mismo que ya hacía `web/marca/trazar.py` con el
logotipo.

Hasta el 24-09-2026 el guion pedía bajar Literata de Google Fonts, y por eso,
cuando la hoja cambió de gris el 23-09-2026, la tarjeta se quedó con el viejo.
Ahora pinta con `web/letra/literata.woff2`, que ya viene con el eje óptico en
12 y los pesos de 400 a 600, y `tests/test_tarjeta.py` pinta la tarjeta y la
compara con la publicada: 0 píxeles distintos con la de hoy, 5475 con la del
gris viejo.

La marca de la tarjeta es la de la cabecera —el signo en `--acento`, con sus
tres líneas, y el nombre en Literata 600— y no el bloque del favicon, que es
lo que pintaba hasta el 24-09-2026: la cabecera lo dejó el 23-09-2026 y la
tarjeta se quedó atrás. El guion copia las cifras de `.marca` y la prueba las
lee de la hoja y las compara, sin Pillow, así que corre también en GitHub.

Y va con negativa, por lo mismo que la letra: un `og:image` que apunta a una
dirección que da 404 no rompe nada y no da error **aquí**. Da error en la casa
de otro, ya publicado.

**Y la dirección lleva la huella de la imagen** desde el 25-09-2026: `og:image`
dice `tarjeta.png?v=` con los ocho primeros del SHA-256 de la tarjeta que se
publica, como el estilo y el cargador. Hasta ese día decía `tarjeta.png` a
secas, y Telegram enseñó la tarjeta de antes dos horas después de publicar la
nueva: quien pinta la vista previa de un enlace la guarda por dirección, y una
dirección que no cambia no tiene por qué volver a pedirse. Lo que la huella no
arregla, y no se puede arreglar desde aquí: Telegram guarda también la vista
previa **de la página**, y hasta que vuelva a leerla enseña la que tiene. Para
eso está su @WebpageBot, que la vuelve a leer cuando se le manda el enlace.

Desde el 25-09-2026 la tarjeta es **la glosa al margen**: el titular de la
portada a la izquierda y, a la derecha, un trozo de factura de muestra con la
glosa que le pondría la página —BR-CO-15, un total que no es la base más el
IVA—. La eligió el titular entre tres propuestas porque es la única que enseña
lo que hace la herramienta en vez de decirlo. La frase sale del glosario y la
cuenta la hace el guion, y `tests/test_tarjeta.py` comprueba las dos cosas:
una tarjeta que explicara un código de otra manera que la página sería la peor
forma de presentarse. Todo va en Literata, también las cifras y el código,
aunque la página los ponga en su mono: la mono de la página es la del sistema,
y una tarjeta pintada con la letra de la máquina que la regenera sale distinta
en cada una.

Hasta ese día, abajo decía *forma, contenido y firma* y el porqué escrito aquí
era que **la firma es la que no hace ningún otro validador gratuito**. No era
verdad: el estudio de mercado del 24-09-2026 encontró a B2Brouter y a
FacturaView verificándola gratis. La tarjeta nueva no presume de nada que no
enseñe.

### El buzón para quien encuentre un fallo

`/.well-known/security.txt`, que es el RFC 9116: el fichero donde mira quien
investiga **antes** de avisar a nadie. Si no encuentra a dónde escribir, lo
normal es que publique el fallo en vez de contarlo, y en una herramienta que
verifica firmas eso importa.

La dirección de `Contact` no está escrita ahí: sale del `TITULAR` de
`glosa.js`, que es donde vive la única copia buena. Si esa ficha se queda sin
correo —y puede, que es justo lo que mira `hayIdentificacion()`—, **el sitio no
se monta**: un `security.txt` que promete un buzón que no existe es peor que no
tenerlo.

El `Expires` es obligatorio y es una fecha, o sea de las que se pudren. Se
calcula al montar, un año por delante, y por eso no está escrito a mano: cada
despliegue la renueva, y si el sitio pasa un año sin desplegarse caduca — que
es exactamente lo que hay que decirle a quien pase por ahí.

### Los enlaces que se van del sitio

`target="_blank"` y `rel="noopener noreferrer"`, puestos al montar y no a mano
en cada página. A mano se escriben los de hoy y se olvidan los de mañana, y aquí
eso está garantizado: la bitácora **exige** un pie de fuentes con un enlace, así
que cada entrada nueva trae los suyos.

`noopener` no es comodidad. Sin él, la página que se abre recibe un puntero a
esta por `window.opener` y puede cambiarla de sitio desde su propia pestaña; con
`noreferrer`, además, no se le va contando a un tercero desde dónde se llega.
Lo que ya traía `rel` no se pierde: el `nofollow` de los dos validadores que se
citan en la portada está puesto a propósito, que una cosa es citarlos y otra
regalarles posición.

### La línea de autoría, y lo que no dice

En el pie de las siete páginas: **© 2026 Glosa-e**. Hasta el 24-09-2026
seguía «· Los textos, de su autor.», y el titular la dejó en eso: de quién es
cada cosa ya lo dice el aviso legal, con la licencia del código al lado.

No dice «todos los derechos reservados», que es lo que se estila, por dos
razones. La primera es que esa fórmula viene de un tratado americano de 1910 y
dejó de tener efecto en 2000, cuando el último país que faltaba entró en el
Convenio de Berna; hoy no reserva nada que no estuviera reservado igual. La
segunda es que **aquí sería falsa**: el validador se publica bajo AGPL-3.0-only
y su código entero viaja al navegador de quien abre la página. Decir que todos
los derechos están reservados contradiría la licencia que el propio sitio
publica en el aviso legal. Hay una prueba que lo comprueba.

Hasta el 15-09-2026 no la publicaba: el aviso legal decía que el código y los
textos «son de su autor», y la licencia solo salía en `security.txt`. Ahora el
apartado «De quién es cada cosa» dice AGPL-3.0-only, que el código viaja entero
en la rueda, y lo que es de otros y viaja con la página —Pyodide, MPL 2.0, con
el intérprete bajo la licencia de la PSF; lxml, BSD; Literata, OFL 1.1—.
`test_el_aviso_legal_dice_bajo_que_licencia_se_publica` compara esa sección
con la etiqueta de `pyproject.toml`.

Lo que sí está reservado son los textos, que es lo que la línea dice. Y quién es
dueño de cada cosa —los XSD de la AEAT, de OASIS y de UN/CEFACT; las anclas, del
Estado— ya lo desglosa el aviso legal, que dice más que un símbolo.

## Contra las pruebas oficiales de la norma

Lo de IGIC e IPSI dejó una lección que no cabe en una regla: **las
comprobaciones que salen de la misma tabla coinciden también cuando la tabla
está mal.** Hacía falta una opinión que no saliera de este repositorio, y
existe. `ConnectingEurope/eInvoicing-EN16931`, donde la Comisión mantiene el
esquematrón oficial para el comité CEN/TC 434, publica al lado **una prueba
unitaria por regla**: un fragmento de factura y la regla que tiene que saltar
o no saltar. Son las pruebas con las que el comité comprueba su esquematrón.

Aquí se usan al revés, para comprobar el validador. `herramientas/norma_oficial.py`
trae una copia fijada a un commit —el de la v1.3.17, desde el 24-10-2026— a `tests/en16931-oficial/`:
279 ficheros de pruebas, el esquematrón del modelo, el de listas de códigos, la
vinculación de cada sintaxis —UBL, CII y EDIFACT, que es donde está la
expresión que se evalúa— y la EUPL 1.2, que es su licencia.
`tests/test_norma_oficial.py` hace seis cosas:

| Qué comprueba | Contra qué |
|---|---|
| que la copia es la fijada | su huella SHA-256, escrita en la prueba |
| que cada una de las **223 reglas** está hecha o pendiente, y ningún `BR-` del catálogo es inventado | las reglas leídas del esquematrón, no de una lista |
| que la gravedad es la de la norma | el `flag` de cada regla |
| que en cada caso oficial de cada regla hecha se dice lo mismo que la prueba | los 567 casos, uno a uno |
| que el margen de BR-CO-17, de cada BR-{X}-08 y de cada BR-{X}-09 es el de cada sintaxis | la expresión de la regla en la vinculación de UBL, CII y EDIFACT |
| que el desglose de EDIFACT se lee donde lo lee la norma | el grupo `VAT_breakdown` de la vinculación de EDIFACT, letra a letra |

**Se versiona, a diferencia del anexo de la AEAT**, y a propósito. Las pruebas
del anexo se saltan si falta el PDF; aquí eso sería un verde que no ha
comprobado nada en la máquina donde falta la copia, y lo que se comprueba es
si el motor dice lo mismo que la norma. No son facturas de nadie: son
fragmentos sintéticos del comité, bajo EUPL, 1,4 MB.

### Lo que salió el primer día

De las 223 reglas, **91 implementadas y 132 pendientes**, las 132 escritas en
la prueba por grupos. Y de las 90 implementadas que tienen prueba oficial
—`BR-IC-10` no tiene ninguna—, **coincidían en todos los casos 49**. Las otras
41 discrepaban en 107 casos, y no son 107 fallos sueltos: son seis motivos.

| Motivo | Reglas | Qué pasaba |
|---|---|---|
| sin desglose | 27 | sin desglose de IVA el módulo se paraba en BR-CO-18 y no miraba el tipo de ninguna línea, descuento o cargo |
| el desglose | 9 | lo mismo para la categoría que falta en el desglose, y además: los conceptos sin importe se descartaban, y en las categorías que exigen un desglose **y solo uno** no se contaban los repetidos |
| el céntimo | 2 | la norma exige que las sumas cuadren exactas; aquí se toleraba un céntimo |
| el céntimo y la cuenta | 1 | lo del céntimo, y BR-CO-15 exige además un único total de impuestos en la moneda del documento |
| la unidad | 1 | al revés: BR-CO-17 admite que la cuota se aparte hasta **una unidad** de base por tipo, y aquí se exigía el céntimo. Rechazaba lo que la norma acepta |
| el perfil | 1 | BR-01 solo pide que el identificador esté; aquí se usaba para opinar sobre lo que dice |

Los 107 casos están declarados en `DISCREPANCIAS`, cada uno con su motivo, y
la lista se comprueba en los dos sentidos: una discrepancia nueva es rojo, y
una declarada que ya no discrepa también. Así no puede quedarse vieja diciendo
que falla lo que ya funciona, que es como envejecen todas las listas de
excepciones. Los cinco guardianes se provocaron: tocar un byte de la copia,
borrar una pendiente, quitar y añadir una discrepancia, y bajar `BR-CL-01` a
aviso.

**Lo que no cubre**, dicho igual de alto: las pruebas oficiales son de UBL
—de CII hay dos ficheros— y no tocan EDIFACT ni Facturae, cuyos mapas se
siguen sosteniendo con sus propias pruebas. Y quedan fuera las 756 reglas de
sintaxis del esquematrón, que aquí no se han implementado.

### Lo que se arregló, y cómo compara de verdad la norma

Los 107 casos se cerraron en la tanda siguiente, y la lista `DISCREPANCIAS`
quedó vacía. Lo que hubo que cambiar, por orden de lo que pesa:

**Las cuentas no se comparaban como compara la norma.** Aquí todo usaba un
céntimo de margen. El esquematrón oficial no lo usa en ninguna regla:

| Reglas | Cómo compara el esquematrón | Qué pasaba aquí |
|---|---|---|
| BR-CO-10 a BR-CO-16, las sumas de la cabecera | redondea la suma a dos decimales y compara **sin margen** | un céntimo de diferencia salía limpio |
| BR-CO-17, la cuota de cada entrada | admite **hasta una unidad** de distancia a base por tipo | se rechazaba a partir de dos céntimos |

Lo segundo era lo peor: rechazar lo que la norma acepta. Una de las facturas de
ejemplo de la Comisión, en forintos, llevaba desde el principio anotada en
HALLAZGOS como «por la letra de BR-CO-17 tenemos razón»; la letra decía otra
cosa. Lo que la norma acepta y no cuadra al céntimo no se calla: sale como
`IVA-CUOTA-REDONDEO`, una nota con la distancia y la base con la que se dio por
buena. Y el redondeo es el de XPath —las mitades hacia arriba, sobre el valor
absoluto—, no el de `Decimal`, porque en el borde de la unidad eso decide.

Lo que se escribe como «Debería ser» sale de esa misma cuenta, desde el
05-10-2026. La regla comparaba con `redondear` y el texto escribía la cifra con
`:.2f`, que es el redondeo de `Decimal` y lleva las mitades al par: una línea de
100.125 con suma declarada 100.12 daba BR-CO-10 con «Debería ser: 100.12 ·
Tiene: 100.12», un error que decía que estaba bien. Pasaba igual en BR-CO-11 a
BR-CO-16, en la base de cada tipo y en negativo. Ahora cada regla escribe la
cifra que comparó, 100,13 en ese caso.

**Y los dos esquematrones oficiales no dicen lo mismo en el borde.** A
exactamente una unidad, el de UBL escribe `<` y el de CII `<=`, y las pruebas
de cada uno prueban ese punto. Aquí se sigue a cada uno en su sintaxis, con un
campo del mapa que dice cuál: `cuota_admite_la_unidad_justa`.

**Sin desglose, el IVA dejaba de mirar.** Se paraba en BR-CO-18. Ahora sigue
con el tipo de cada concepto y con la categoría que falta, y los conceptos sin
importe ya no desaparecen: una línea al tipo general con un 0% y sin importe
es un BR-S-05 aunque no entre en ninguna suma.

**Una sola entrada donde la norma dice una sola.** Tipo cero, exenta,
inversión del sujeto pasivo, intracomunitaria, exportación y no sujeta admiten
exactamente una entrada del desglose; el tipo general, el IGIC y el IPSI, al
menos una. La tabla del IVA lo lleva ahora como cuarta columna, y la prueba
que la compara con el texto del esquematrón también.

**BR-01 dejó de opinar.** Pide que el identificador de especificación esté.
Que no nombre a EN 16931 sigue siendo útil saberlo, y sale como
`PERFIL-SIN-EN16931`, un aviso de la casa.

**Un total de impuestos por moneda.** BR-CO-15 falla con dos en la moneda de
la factura. Solo se cuenta donde el importe dice su moneda: en EDIFACT el
`MOA+176` sale una vez en el resumen y otra por tipo, y contarlos acusaba a
cuatro facturas reales de algo que no hacen. Eso se vio al pasar el corpus, no
en ninguna prueba.

**Lo que cambió sobre las 179 facturas del corpus**: de 1241 incidencias a
1168. Se van 84 `BR-01` de aviso —74 eran EDIFACT sin identificador, que ya
tenían su `BR-01` de error, y 10 pasan a `PERFIL-SIN-EN16931`—; dos `BR-CO-17`
pasan a nota, entre ellas la de los forintos; y aparece un `BR-E-01`.

**Ese `BR-E-01` destapa algo que no es de esta tanda.** Es una factura EANCOM
con el mismo `TAX+7+VAT+++:::0+E` en la cabecera y en el resumen, y el mapa de
EDIFACT leía los dos como entradas del desglose. Aquí se escribió ese día que de
eso salían los `BR-45` y `BR-46` de 37 de las 73 facturas EDIFACT del corpus.
**Era falso**: 37 son las facturas que tenían la queja, no las que la tenían
por eso. Lo medido está en la sección siguiente.

### Las cifras: con coma, y «Tiene» tal cual

Hasta el 05-10-2026 el informe escribía todas las cifras con `:.2f`, cada
módulo con su `_fmt`: con punto decimal, que en castellano se lee como
separador de miles («Debería ser: 90.00», «se aparta 0.50»), y redondeando
también lo que copiaba del fichero. «Tiene» no decía lo que tenía: un 100
salía 100.00, y un 21.005 salía 21.00, una cifra que no está en el fichero.
Ahora todas pasan por `validador/cifras.py`, que tiene tres puertas según de
dónde sale la cifra:

| Función | Para | Cómo sale |
|---|---|---|
| `calculada` | lo que calcula el validador | `100,13`: coma, dos decimales y el redondeo de la regla |
| `en_castellano` | una cifra del fichero dentro de una frase o de la cuenta que explica un «Debería ser» | `0,125`: coma, sin redondear y con dos decimales como mínimo, para que la cuenta sume |
| `tiene` | una cifra del fichero, sola, en «Tiene» | `21.005`: tal cual, con su punto, que es lo que se busca en el XML |

Los miles van con punto desde cinco cifras (12.345,67, y 1234,56 sin él), que
es lo que hace `toLocaleString("es-ES")` en la portada. En «Tiene», nunca.
Lo que no se guarda es lo que `Decimal` no guarda: un «+» delante o ceros a
la izquierda. Y en EDIFACT con la coma como marca decimal, «Tiene» sale con
punto, porque el árbol que se valida ya lo trae así.

Dos guardias: ninguna línea de `validador/` escribe una cifra con `:.2f` ni
con un `fmt` propio (fuera de `cifras.py`, de `sintaxis.py`, que define el
`fmt` que ya no usa nadie, y de los megas que `__main__` escribe al montar), y
ningún mensaje ni «Debería ser» lleva un punto decimal, sobre las muestras y
sobre facturas con las cuentas rotas de los cuatro motores.

### Lo que se lee: tildes, fechas y bytes

El 06-10-2026, lo que quedaba del repaso del 05-10 en lo que lee una persona.

**Las tildes.** Si la página no arrancaba, decía «No esta el interprete en
./pyodide/. Traelo con `python -m validador --traer-pyodide`»: sin tildes, con
una ruta y con una orden que quien abre la página no puede dar. Ahora
`glosa.js` lanza esos fallos con `averia(paraQuienMira, paraQuienMantiene)`.
Lo primero es lo que sale en pantalla («No ha llegado el intérprete de Python
con el que corre la página. Recarga la página; si sigue igual, el fallo es de
la página y no de tu navegador.»), y lo segundo va a la consola del navegador
y viaja en `cause`. La portada y el banco enseñan `error.message`, sin el
«Error:» delante. En el banco, 13 de las 42 comprobaciones llevaban el nombre
sin tildes, y unas sesenta cadenas en total; también la ayuda de la consola.

La guardia está en `tests/test_voz.py`: una red de palabras que en castellano
no existen sin su tilde («aqui», «pagina», «deberia», «ningun», las acabadas en
«-cion»), sobre el texto de las páginas, las cadenas de `glosa.js` (y las del
Python que lleva dentro), las del banco y las del motor. Las que existen con y
sin tilde («esta», «valida», «solo», «que», «donde») cambian de sentido y no
de ortografía, y se quedan fuera: esas se corrigen leyendo. Otra en
`tests/test_fallos_de_la_pagina.py`: ningún `new Error` llega a la pantalla
sin pasar por `averia`, salvo dos con su motivo, y lo que lee quien mira pide
que recargue y no lleva rutas, huellas ni órdenes.

**Las fechas**, en dd-mm-aaaa, como el resto del sitio. La ficha del paquete
decía «Montadas el 2026-08-27» y el informe escribía así unas cincuenta.
`cifras.fecha` las escribe en el informe y `cifras.momento` cuando llevan hora
(«16-12-2015 a las 14:41:55 UTC»); en la portada y el banco, `Glosa.fecha`.
Se quedan en ISO, por función y con su motivo en `EN_ISO`
(`tests/test_cifras.py`): la fecha del fichero en «Tiene», que va tal cual
como las cifras; `PAQUETE.json` y las líneas del manifiesto de las anclas,
que son para máquina; y los inventarios de consola (`--ver-anclas`,
`--ver-revocaciones`, `--ver-tsl`), que son columnas y en ISO se ordenan
solas.

La frase de procedencia lleva la fecha **dentro del manifiesto** de las
anclas, que viaja en el paquete publicado: «publicada por ... el 2026-08-06».
Montar de nuevo ya la escribe en dd-mm-aaaa, pero el paquete de hoy no se
vuelve a montar hasta antes del 02-02-2027. Por eso se pasa al leerla, en
`Almacen.declarada` y en `Glosa.fecha`, que admite una frase con fechas dentro.

**Los bytes** con punto de miles: el banco decía «1247225 bytes», y ahora
«1.247.225», con `cifras.recuento` en Python y `toLocaleString("es-ES")` en
`glosa.js`.

### Un esquema que no compila no se publica

El 06-10-2026. `XSD-ESQUEMA-ROTO` sale cuando el esquema que le toca a un
documento está y no compila. Con el paquete publicado no salía, pero si hubiera
salido en la página habría dicho la ruta del disco virtual del navegador
(«/opt/factura-e/esquemas/ubl/maindoc/...») y «Suele ser una descarga a medias;
vuelve a bajarlo», que allí no se puede. Reproducido con el código de antes y
un `UBL-Invoice-2.1.xsd` cortado por la mitad en un catálogo con la procedencia
de la página.

Ahora hace lo mismo que `XSD-SIN-ESQUEMA`: con procedencia, dice que el
esquema «está entre los esquemas que vienen con esta página pero no se puede
leer», que es un fallo de la página y no de la factura y que recargar no lo
arregla; en «Tiene», el motivo de libxml2 sin la carpeta delante
(«ubl/maindoc/UBL-Invoice-2.1.xsd, line 501»). En consola sigue diciendo dónde
está y que se vuelva a bajar.

Y para que no llegue a salir, dos puertas:

| Dónde | Qué | Con qué libxml2 |
|---|---|---|
| `--empaquetar` | compila los esquemas de entrada uno a uno y se niega con `EsquemaQueNoCompila` si alguno no compila | la de esta máquina, 2.11.9 |
| el banco | «los esquemas de entrada compilan con este libxml2», crítica | la del navegador, 2.9.10 |

Hacen falta las dos porque compilar aquí no prueba lo de allí. Los de entrada
son los que `_nombres_esperados` puede pedir (`_DE_ENTRADA`, y una prueba
comprueba que todo lo que pide encaja): once en el paquete de hoy, que compilan
en un segundo aquí y en 1,85 s en el navegador, medido el 06-10-2026. Hasta
entonces, en el banco solo se compilaba el de Facturae.

Las negativas de `--empaquetar` eran dos y `__main__` las cazaba por su nombre.
Con la tercera se les puso raíz, `NoSeEmpaqueta`, como `NoSeMonta` la tiene
para `--sitio`, y la prueba que recorre `paquete.py` exige que toda excepción
cuelgue de una de las dos.

### El desglose de EDIFACT, y el margen de la base

Las dos cosas que la tanda anterior dejó apuntadas se cerraron el 14-09-2026, y
las dos con el texto oficial delante en vez de con una lectura.

**El desglose de EDIFACT es el grupo 54.** El esquematrón oficial de EDIFACT
—que existe, y no se había mirado— lo nombra así:
`/M_INVOIC/G_SG54[S_TAX/D_5283='7' and S_TAX/C_C241/D_5153='VAT']`, el grupo
de impuesto que va después del `UNS`, y solo si es de IVA. El mapa de aquí
pedía `./*[S_TAX]`, cualquier grupo de impuesto colgado de la raíz, y entraban
dos que no lo son: el de la cabecera, que es el impuesto del documento entero,
y uno del resumen que no dice de qué impuesto es. Ahora pide lo mismo que el
oficial, y una prueba compara el filtro letra a letra con la copia fijada.

**Y lo que se había escrito del corpus, medido antes de arreglarlo.** De las 85
facturas EDIFACT, **13** traen un TAX en la cabecera y **2** uno al final sin el
tipo VAT; esas 15 son las que cambian. En las demás la queja es buena: en 21
facturas la base, el `MOA+125`, va escrita fuera del grupo de impuesto, y no
dentro, que es donde la norma la lee; en otras la cuota viene con el
cualificador 150, 161 o 176 en vez del 124.

| Facturas EDIFACT, de 85 | antes | después |
|---|---|---|
| con `BR-45` | 37 | 25 |
| con `BR-46` | 26 | 14 |
| con `BR-CO-18` | 20 | 30 |

**Diez facturas pasan a «no trae desglose», y no se quedan ahí.** Donde el
único TAX estaba en la cabecera, o al final sin el tipo VAT, sale ahora
`BR-CO-18`. Es verdad donde la norma lo lee, pero quien lo lee va a buscar un
TAX que tiene delante; por eso sale al lado `EDI-IVA-FUERA-DEL-DESGLOSE`, un
aviso que dice cuál hay y por qué no cuenta. Es la idea de
`EDI-TOTALES-DE-OTRA-GUIA`, con el impuesto.

**El margen de la base, BR-{X}-08, sale ahora del esquematrón.** El modelo
abstracto solo dice `$BR-S-08`; la comparación de verdad está en la vinculación
de cada sintaxis, que desde hoy viaja en la copia oficial. Leída de ahí:

| Categoría | UBL | CII | EDIFACT, de 2017 |
|---|---|---|---|
| S, L, M | menos de una unidad | exacta | exacta |
| Z, E, AE, K, G | exacta | menos de una unidad | exacta |
| O | exacta | exacta | exacta |

Aquí había un céntimo para todas, y se equivocaba en las dos direcciones y en
las dos sintaxis: un céntimo de diferencia en la base del tipo general salía
limpio y el esquematrón de CII lo rechaza, y en UBL pasaba lo mismo con la
exenta. Ahora se sigue a cada esquematrón, y lo que dice `sintaxis.py` lo
comprueba una prueba que lee la expresión de cada regla: si el comité la cambia,
se pone en rojo. Lo que pasa por el margen no se calla: sale como
`IVA-BASE-TOLERADA`, un aviso y no una nota, porque una base es una suma y no
tiene redondeo que la explique.

**EDIFACT y Facturae siguen a UBL, y es una decisión.** El esquematrón de
EDIFACT compara todo exacto, BR-CO-17 incluida, pero su último cambio de
contenido es de febrero de 2017; los márgenes de UBL y CII llegaron después y
ese no se tocó. Seguirlo sería volver a rechazar lo que la norma ya acepta.
Facturae no tiene esquematrón europeo. Una prueba comprueba que el de EDIFACT
sigue sin márgenes: el día que un commit nuevo se los ponga, hay que volver a
decidir.

**Y las categorías de una sola entrada se suman sin mirar el tipo**, que es
como lo hacen los dos esquematrones. En el corpus lo cambia una factura: una
línea a tipo cero con un 20% escrito salía con tres errores —el tipo, la base
y la línea sin desglose— y sale con uno, `BR-Z-05`, que es el defecto que
tiene.

**Lo que cambió en las 179 facturas del corpus**: de 1168 incidencias a 1134.
Cada pieza se provocó rompiéndola —quitar el UNS, quitar el filtro de IVA, dar
a UBL el margen de CII, poner a EDIFACT el de 2017, volver al céntimo, volver
a la clave con tipo— y cada una se puso en rojo en su prueba.

**Los precios con el IVA dentro, desde el 18-10-2026.** La norma solo conoce
precios sin IVA, y el libro, el ticket que se canjea por factura y la tienda
los fijan con el IVA incluido. Para escribirlos hay que dividir por (1 + tipo)
y redondear, y el redondeo se multiplica por la cantidad. Quien factura así
suele cuadrar el total con lo cobrado y sacar la cuota por diferencia, y la
cuota se aparta de la base por el tipo: la nota `IVA-CUOTA-REDONDEO` si es
menos de una unidad, `BR-CO-17` si no. Medido con siete facturas de libros al
4%:

| La factura | Cómo cierra | Qué da |
|---|---|---|
| 157 libros, precio sin IVA a 4 decimales | a la letra de la norma, con o sin `BT-114` | limpia |
| 400 líneas de un ejemplar, a 4 decimales | cuota por diferencia | nota, 0,55 |
| 25.000 ejemplares en 3 líneas, a 4 decimales | cuota por diferencia | nota, 0,30 |
| los mismos, a 2 decimales | cuota por diferencia | `BR-CO-17` y `BR-S-09`, 28,80 de cuota de más |

El ERROR es justo, porque la base se queda 27,69 corta de lo cobrado sin IVA.
Lo que faltaba era decir por qué. Ahora, si cada precio por (1 + tipo),
redondeado al céntimo, da un precio con IVA y esos precios por sus cantidades
suman **justo** la base más la cuota, el mensaje lo dice y reparte el total en
base y cuota. Con precios sin IVA de verdad y un error cualquiera, que eso
cuadre al céntimo sería casualidad. No se dice nada si la entrada tiene
cargos o descuentos, si un precio no es por unidad (`BT-149`) o si una línea
no es su precio por su cantidad, ni en EDIFACT y Facturae, donde no se lee la
cantidad base del precio. En el corpus local (172 facturas) no sale en
ninguna: las cuatro con `BR-CO-17` o la nota no cuadran con precios con IVA.
Cada condición se provocó quitándola, y su prueba se puso en rojo. Está en
`tests/test_precios_con_iva.py` y en HALLAZGOS.

**La S se llama régimen general, y no tipo general**, desde el mismo día. En
España la S lleva el 21 %, el 10 % y el 4 %, y el tipo general es solo el
21 %: un libro salía como "S (tipo general) al 4%". El nombre es el de la
lista L4 de la Orden HAC/1028/2026, "Operaciones en régimen general", y una
prueba recorre el glosario para que no vuelva.

### Las reglas pendientes, por grupos: la cuota de cada categoría

De las 132 reglas pendientes, las que se hacen primero son las que tienen
prueba oficial: 101 la tienen y 31 no —las 21 de decimales, entre ellas—, y
una regla sin prueba oficial solo tiene la opinión de aquí. Cada una sale de
`PENDIENTES` al hacerse, y en ese momento sus casos oficiales pasan a
comprobarse uno a uno.

**La primera tanda es BR-{X}-09, la cuota de cada categoría: nueve reglas.**
Son dos reglas con el mismo número:

| Categorías | Qué pide | En qué se diferencia de BR-CO-17 |
|---|---|---|
| Z, E, AE, K, G, O | cuota **cero exacto** | BR-CO-17 redondea a entero a tipo cero y deja pasar 0,40 |
| S, L, M | base por tipo, a menos de una unidad | la misma cuenta; en CII, BR-CO-17 admite la unidad justa y BR-S-09 no |

Y otra vez las dos sintaxis no dicen lo mismo: el esquematrón de CII da las
09 del IGIC y del IPSI (sus BR-IP-09 y BR-IG-09 desde la 1.3.17, que cruzó los
nombres) por duplicadas de BR-CO-17 y las deja en `true()`. Aquí se
sigue a cada uno —EDIFACT y Facturae con UBL—, y qué categorías mira cada
sintaxis lo lee de la vinculación la misma prueba que lee los márgenes.

**Dos reglas de la norma son dos incidencias.** Donde BR-S-09 falla falla
también BR-CO-17, casi siempre, y salen las dos, que es lo que hace el
validador oficial. El caso en que no coinciden es el borde de CII —una cuota a
exactamente una unidad—, y ahí la nota `IVA-CUOTA-REDONDEO` se retira: no se
puede decir a la vez que la norma lo admite y que no.

**En el corpus**, tres facturas: dos EDIFACT con la cuota del tipo general
descuadrada, que ya tenían BR-CO-17 y ahora llevan también BR-S-09, y una con
inversión del sujeto pasivo que cobra 19,13 de cuota y hasta hoy salía sin
ninguna queja sobre la cuota. De 1134 incidencias a 1138.

Provocado cinco veces: el tipo cero con redondeo a entero, CII mirando el IGIC,
la unidad justa que pasa, la nota que no se retira y la regla de tipo cero
quitada; esta última se pone en rojo también en los casos oficiales. Quedan
123 pendientes.

### Los identificadores fiscales de cada categoría

**La segunda tanda es BR-{X}-02, 03 y 04: veintisiete reglas**, las de más
casos oficiales de todas —214—. Si una línea (02), un descuento de documento
(03) o un cargo (04) usa una categoría, la factura tiene que identificar a
quien esa categoría pide:

| Categorías | Del vendedor | Del comprador |
|---|---|---|
| S, Z, E, L, M | cualquiera: BT-31, BT-32 o el del representante, BT-63 | — |
| AE | cualquiera | su identificador de IVA, BT-48, o su registro, BT-47 |
| K | el de IVA: BT-31 o BT-63 | el de IVA, BT-48 |
| G | el de IVA: BT-31 o BT-63 | — |
| O | **ninguno** de IVA | **ninguno** de IVA |

La tabla vive en `iva.py` y una prueba la compara con el texto de cada una de
las veintisiete reglas en la vinculación de UBL: qué identificadores nombra, y
si los nombra para exigirlos o, en la no sujeta, para prohibirlos. Los mapas
miran si el elemento está, como el esquematrón: el `PartyTaxScheme`
de UBL separado por su esquema, el `schemeID` de CII, y en EDIFACT la
referencia VA, FC o GN detrás del NAD de cada parte. GN, el registro del
comprador, es una lectura por analogía: el esquematrón de EDIFACT lo usa para el
del vendedor y no nombra el del comprador en ninguna regla.

**Facturae no dice qué clase de identificador trae, y aquí no se elige.** Cada
parte lleva un `TaxIdentificationNumber`, obligatorio por esquema, y nada dice
si es el de IVA o otro. La regla se evalúa con tres valores —está, no
está, no se sabe—, y con «no se sabe» se calla: en las categorías que se
conforman con cualquiera no hace falta, porque el esquema ya exige el número;
en la intracomunitaria, la exportación y la no sujeta, que dependen de la
clase, no se afirma nada. El borrador del CIUS español sí elegía: leía el
número del comprador como BT-48. Con esa lectura, **toda factura no sujeta que
lleve el NIF del comprador sería error de BR-O-02**, que prohíbe BT-48 en la no
sujeta. Era una consecuencia del borrador, no de la norma. La orden publicada
el 05-10-2026 ya no elige uno solo: admite el NIF del comprador en BT-48, con
«VAT», o en BT-47, con «LOC» y el atributo «FC». Así que una no sujeta tiene
dónde llevarlo sin chocar con BR-O-02: en BT-47, que la regla no nombra y su
esquematrón de UBL no mira, porque busca el `PartyTaxScheme` del comprador con
«VAT».

**Las facturas correctas de las pruebas no tenían identificador.** Cincuenta
pruebas se pusieron en rojo el primer día: las facturas de ejemplo de UBL, CII y
EDIFACT montadas para «pasar limpias» no identificaban al vendedor, y la norma
lo pide. Ahora lo llevan, y las de la no sujeta no llevan ninguno de IVA.

**En el corpus**, cuatro facturas EDIFACT sin la referencia de IVA del
vendedor, y en una ni siquiera su NAD: de 1138 incidencias a 1142. Provocado
siete veces —la intracomunitaria conformándose con cualquiera, la inversión sin
comprador, la no sujeta sin prohibir, «no se sabe» leído como «no está», los
descuentos y cargos contados como líneas, el de IVA de UBL sin filtrar por
esquema y el NIF de EDIFACT buscado en el comprador—, y las siete en rojo.
Quedan 96 pendientes.

### La no sujeta sin nada más, y la entrega intracomunitaria

**Cinco reglas que cierran el IVA por categorías.** BR-O-12, 13 y 14: con una
entrada no sujeta en el desglose, ninguna línea, descuento o cargo de otra
categoría —BR-O-11 ya lo miraba en el desglose; estas lo miran en lo que lo
alimenta—. BR-IC-11 y 12: una entrega intracomunitaria dice cuándo, con la
fecha de entrega o el periodo, y adónde, con el país de entrega.

**Un elemento con solo un comentario dentro está vacío.** Es lo que salió al
pasar los casos oficiales: dos traen `<cbc:ActualDeliveryDate><!--comment
only--></cbc:ActualDeliveryDate>`, y lxml cuenta el comentario como hijo. El
esquematrón mide el texto, `string-length(...) > 1`, y aquí se mide igual.

**Y el esquematrón de CII no encuentra el periodo.** Lo busca con `../../`
desde la raíz del documento, que no lleva a ninguna parte, así que en CII solo
le vale la fecha de entrega. La norma dice «la fecha de entrega o el periodo»,
y aquí se sigue a la norma. En Facturae el periodo tiene sitio y se lee; la
fecha de entrega y el país no, y no se reclaman.

**En el corpus no cambia nada**: ninguna factura mezcla lo no sujeto ni trae
una entrega intracomunitaria incompleta. Provocado cinco veces, las cinco en
rojo; la del comentario, en los casos oficiales. Quedan 91 pendientes.

### Los grupos y lo que tienen que llevar dentro: 42 reglas

**Casi la mitad de lo que quedaba dice lo mismo**: si hay un X, tiene que traer
un Y. Si hay representante fiscal, su nombre, su dirección y su NIF (BR-18 a
BR-20 y BR-56); si hay un descuento o un cargo, su importe, su categoría y su
motivo (BR-31 a BR-33, BR-36 a BR-38, BR-41 a BR-44); si hay una instrucción de
pago, el medio, y si es transferencia, la cuenta (BR-49, BR-50, BR-61). Y las
de su familia: el beneficiario (BR-17), los precios no negativos (BR-27 y 28),
los periodos (BR-29, BR-30, BR-CO-19 y 20), la tarjeta (BR-51), la moneda de
contabilidad (BR-53), los atributos (BR-54), la factura anterior (BR-55), la
dirección de entrega (BR-57), los esquemas de los identificadores (BR-62 a
BR-65), la fecha de devengo (BR-CO-03), la categoría de cada línea (BR-CO-04),
el prefijo del NIF (BR-CO-09), el vendedor identificado (BR-CO-26) y cuatro
repetidas (BR-CO-21 a 24). Viven en `validador/modelo.py`, con 45 campos
nuevos en los cuatro mapas.

**Una tabla de grupos y no de campos.** El esquematrón evalúa cada una sobre un
contexto: sin representante fiscal, BR-18 no corre. Cada fila dice qué grupo,
qué pide y si pide que el elemento esté o que diga algo —texto solo donde las
dos vinculaciones lo piden, que son cuatro—.

**Lo que se decidió, uno a uno:**

| Qué | Decisión |
|---|---|
| Tres valores | Lo que la sintaxis no tiene dónde escribir no se reclama. Con una excepción marcada: la alternativa que una sintaxis no tiene —el código de un motivo en Facturae— no es «no se sabe», es «no está» |
| Las repetidas | BR-CO-21 a 24 piden lo mismo que BR-33, 38, 42 y 44. El oficial las da las dos y aquí salen las dos; una prueba comprueba que la expresión es la misma en UBL y en CII y la fila la misma aquí |
| BR-17 | Las dos vinculaciones dan por error un beneficiario que es el propio vendedor. La de UBL lo compara con el nombre comercial y la de CII con el legal; aquí con los dos |
| BR-53 | Con la moneda de contabilidad igual a la de la factura vale el total de siempre, como en UBL. La de CII exige que sean distintas, y la regla no lo dice |
| BR-CO-09 | La lista de prefijos es la de UBL, comparada con la oficial: la de CII trae AN, que ya no existe, y le falta SS |
| BR-51 | Aviso, como en la norma, y el informe no repite el número de la tarjeta |
| EDIFACT | Representante fiscal el NAD+LC (27 reglas del oficial) y no el AE (una). Sin instrucción de pago: no hay grupo que lo sea. El ALC de línea con importe 509 es el descuento sobre el precio y no uno de línea: 1.498 de bruto menos 225 son los 1.273 de neto del ejemplo 2 de la Comisión, igual que en su gemelo UBL |
| EDIFACT, BR-CO-09 | Se evalúa, aunque el esquematrón de EDIFACT la deje en `true()`: es de la norma, y el esquematrón no se ha tocado desde 2017. Los ejemplos 2 y 6 de la Comisión no la cumplen —`123456789MVA` sin el NO—, y sus gemelos UBL sí |
| Facturae | La transferencia es el 04 de su propia lista, y su esquema también exige la cuenta. Sin representante, beneficiario, direcciones electrónicas ni adjuntos con referencia: no se mira. `Corrective` no es BG-3, porque puede rectificar un periodo sin nombrar factura |

**Y salió uno en casa.** La factura de ejemplo, `ejemplos/fe-0001.xml`, pagaba
por transferencia sin cuenta de abono. Está en HALLAZGOS.

**Medido.** Los 218 casos oficiales de estas reglas pasan a la primera, y las
de CII, EDIFACT y Facturae se montan en `tests/test_modelo.py`. El corpus pasa
de 1142 a 1276 incidencias: 133 de las nuevas caen en 57 facturas EDIFACT y una
en una UBL de prueba sin nada en la línea. De esas 58, 56 ya tenían algún
error; las dos que cambian de veredicto son los ejemplos de la Comisión, por el
prefijo. Provocado quince veces, las quince en rojo. Quedan 49 pendientes.

### Cuántos decimales lleva cada importe: 21 reglas

**Dos como mucho, en todos los importes**: los descuentos y cargos y sus bases,
los totales, el desglose y el neto de cada línea (BR-DEC-01 a BR-DEC-28). Los
precios y las cantidades pueden llevar más. Viven en `validador/decimales.py`, y
buscan los descuentos, los cargos y las líneas con `modelo.grupos`: «descuento 2»
es el mismo en BR-DEC-01 que en BR-31.

**Lo escrito o el valor.** ¿`10.500` son tres decimales? Casi todas las
vinculaciones oficiales dicen que sí, porque cuentan los caracteres que hay
detrás del punto. Dos dicen que no: las de CII para el total del impuesto
redondean y comparan. Aquí se hace lo que haga cada una, regla a regla. Lo
guarda `Sintaxis.decimales_por_valor`, y `test_norma_oficial` lo lee de la
copia oficial. Cuando lo que sobra son ceros, el informe lo dice: el importe
está bien y basta con no escribirlos.

| Qué | Decisión |
|---|---|
| Facturae | Se mira el valor en las veintiuna: su esquema escribe los importes con hasta ocho decimales (`DoubleUpToEightDecimalType`), y `1500.00000000` es un importe de dos. No escribe la base de un descuento, y el total con IVA, el total del impuesto y el redondeo no se leen (ver sus mapas): esas ocho no se miran |
| BR-DEC-13 y 15 en UBL | La vinculación compara la moneda del importe con un `cbc:DocumentCurrencyCode` que busca dentro del importe. El filtro no deja pasar ninguno y la regla se cumple siempre; está medido evaluándola tal cual en `tests/test_decimales.py`. Aquí se miran como dice la norma |
| BR-DEC-15 | El total cuya moneda es la de contabilidad, lo sea también de la factura o no, como en la vinculación de CII |
| EDIFACT | Se cuenta lo escrito, como en su vinculación. BR-DEC-15 y 17 no se miran, porque la moneda de contabilidad y el redondeo no se leen |

**Y cambió cómo se nombra un descuento de línea.** El informe junta los sitios
con comas, y el nombre llevaba otra: «línea 1, cargo 2, línea 1, cargo 3». Ahora
es «cargo 2 de la línea 1», también en BR-41 a BR-44.

**Medido.** No hay ni una prueba oficial de estas reglas. Las 165 de
`tests/test_decimales.py` montan cada importe en las cuatro sintaxis y
comprueban que salte esa regla y ninguna otra. El corpus pasa de 1276 a 1291
incidencias. Las 15 nuevas caen en cuatro facturas EDIFACT que ya tenían
errores, y las 15 son ceros de más —`9999.990000`—; en UBL, CII y Facturae no
sale ninguna. Provocado diecisiete veces, las diecisiete en rojo. Las dos que
quitaban la llamada desde el validador salieron en verde a la primera, porque
las pruebas llamaban al módulo directamente; ahora hay una que pasa por la
entrada. Quedan 28 pendientes.

### Los códigos que tienen que salir de una lista: 22 reglas

**La moneda es de ISO 4217, el país de ISO 3166, la unidad de la recomendación
20 de UN/ECE**, y así hasta veintidós (BR-CL-03 a BR-CL-26). Viven en
`validador/listas_de_codigos.py`, con las listas escritas enteras: la copia
oficial vive en `tests/` y no viaja en la rueda. Las escribe
`python -m herramientas.listas_de_codigos` desde esa copia, y
`test_norma_oficial` las compara una a una con ella.

**Hicieron falta dos esquematrones más.** La copia oficial tenía el de códigos
de UBL y no los de CII y EDIFACT, y sin ellos no se podía saber si decían lo
mismo. Se trajeron del mismo commit con `herramientas/norma_oficial.py`; los
otros 285 ficheros salieron idénticos y la huella cambió por los dos nuevos.

**Una lista por regla, la más al día.** Los esquematrones de UBL y CII dicen la
misma lista en todas las reglas menos en cuatro, y una prueba lo comprueba:

| Qué | Decisión |
|---|---|
| Países (BR-CL-14 y 15) | La de UBL. La de CII todavía tiene AN, las Antillas Neerlandesas, disueltas en 2010, y le falta SS, Sudán del Sur. Es la diferencia de los prefijos de BR-CO-09 |
| Asunto de la nota (BR-CL-08) | La de CII, que tiene los 383 códigos de la de UBL y 18 más. En UBL el asunto va dentro del texto, `#AAI#Texto`, y se lee como en su vinculación |
| Fecha de devengo (BR-CL-06) | Otra lista en cada sintaxis: 3, 35 y 432 en UBL (UNTDID 2005); 5, 29 y 72 en CII (UNTDID 2475). Va en el mapa, `codigos_de_devengo` |
| Categoría del desglose | BR-CL-17, como en la norma y en UBL. El esquematrón de CII la mira con BR-CL-18 porque el elemento se llama igual que el de la línea |
| EDIFACT | Su esquematrón de códigos es de 2017, mira cada elemento de datos en cualquier sitio y ninguna comprobación tiene nombre de regla. Se miran los campos de la norma con las listas de hoy: moneda, países, categorías, motivos y unidades |
| Otra lista | Lo que la sintaxis escribe con una lista suya no se mide contra la europea: en Facturae el medio de pago, el impuesto y la unidad; en EDIFACT el esquema del identificador del artículo (UNTDID 7143) y el devengo, que es el cualificador del DTM. Lo dice `codigos_con_otra_lista` |

**Y salió uno en casa, otra vez.** Los tres ejemplos EDIFACT decían `PCE` como
unidad, que es la pieza de EANCOM y no está en la lista de la norma, ni en la
de hoy ni en la de EDIFACT de 2017. Está en HALLAZGOS.

**Medido.** Los 46 casos oficiales de las 18 reglas que los tienen pasan a la
primera. De las otras cuatro no hay ninguno. Las 43 pruebas de
`tests/test_listas_de_codigos.py` montan cada regla en CII y las que caben en
EDIFACT y Facturae, y exigen que salte esa y ninguna otra. El corpus pasa de
1291 a 1376 incidencias en 58 facturas:

- **53 son EDIFACT.** BR-CL-23 sale en 32, y siempre por `PCE`. BR-CL-19 y
  BR-CL-20 salen por códigos de motivo como `TD`, `DI`, `SF` o `G74`, que no
  están en ninguna de las listas. Solo `ADR`, `ADO` y `ZZZ` son de UNCL 7161
  escritos en un descuento, donde la norma pide UNCL 5189.
- **Las otras cinco son muestras de la extensión de XRechnung**, que usan a
  propósito códigos que la extensión admite y la norma no: `application/xml`,
  `XR01`, `CVD`. Son las únicas que cambian de veredicto.

Provocado dieciocho veces, las dieciocho en rojo. Con eso se vio que comprobar
si un código lleva un espacio dentro era código muerto, porque ninguna lista
tiene uno así, y se quitó. Quedan 6 pendientes.

### Las seis últimas: dos que se hacen y cuatro que no se pueden hacer

**El pago fraccionado italiano, BR-B-01 y BR-B-02.** La categoría B es un
régimen del IVA de Italia —*split payment*—, y la norma le pone dos
condiciones: que la factura sea nacional italiana y que no mezcle la B con la
S. Viven en `modelo.py`. «Nacional» se lee como en la vinculación de CII, con
los países de las direcciones. La de UBL mira todos los `IdentificationCode` y
cuenta así el país de origen de los artículos, que no dice dónde está nadie.

**BR-CO-05 a BR-CO-08 no se pueden comprobar, y no se hacen.** Piden que el
código del motivo de un descuento o de un cargo y el motivo escrito «indiquen
lo mismo»: que el 95 vaya con «descuento» y no con «transporte». Eso es
entender una frase, en cualquier idioma, y las tres vinculaciones oficiales las
escriben como `true()`. Están en `NO_EVALUABLES`, una tercera lista junto a
las hechas y las pendientes, y dos pruebas vigilan la decisión: que siguen
siendo `true()` en UBL, CII y EDIFACT, y que ninguna prueba oficial las hace
saltar. Si el comité les pone una expresión, se ponen en rojo.

**Con esto no queda ninguna pendiente.** Las 223 reglas de la norma están
hechas, 219, o declaradas imposibles con la prueba que lo sostiene, 4. De las
seis de esta tanda no hay ni un caso oficial, y sus pruebas están en
`tests/test_modelo.py`. En el corpus no sale ninguna B, y no cambia nada.
Provocado nueve veces. La primera pasada dejó una en verde: una guarda para
cuando no se sabe el país no hacía nada que no hiciera ya la ruta vacía, y se
quitó.

### El tipo que falta en la línea, el descuento y el cargo

**`BR-{X}-05`, `06` y `07` callaban cuando el tipo no estaba.** Piden el tipo
que toca a cada categoría en cada línea (`BT-152`), descuento (`BT-96`) y
cargo (`BT-103`) de documento. Aquí se miraba el valor cuando lo había, y si
faltaba se daba por bueno con un comentario: «que el tipo falte lo dice
BR-48». BR-48 es del desglose. Una línea exenta sin tipo, con su entrada del
desglose a cero, pasaba sin una queja. Salió el 11-10-2026, al quitar uno a
uno los elementos de las facturas buenas de la orden: el anexo deja esos tres
términos en `0..1`, como la norma, que los necesita opcionales para la O.

**La norma no lo deja ir.** En el esquematrón oficial las tres reglas son una
comparación con el tipo en las tres vinculaciones (`xs:decimal(cbc:Percent) =
0` en UBL, `ram:RateApplicablePercent = 0` en CII, `C_C243/D_5278 = 0` en
EDIFACT), y en XPath una comparación con nada es falsa: la regla salta. En la
O, que pide `not(...)`, es al revés. Las pruebas unitarias oficiales no lo
prueban: de los 78 conceptos que montan en sus casos de estas reglas, ninguno
va sin tipo fuera de la O. Medido antes de tocar nada, sobre `cbf52b4`:

| Factura | En `cbf52b4` | Ahora |
|---|---|---|
| el caso bueno de cada prueba oficial `BR-{X}-05`, `06` y `07`, sin el tipo: ocho categorías por tres conceptos | sin la regla, en los 24 | la regla, en los 24 |
| lo mismo en la O | sin la regla | sin la regla |
| la de la orden con AE, o la exenta, sin el tipo de la línea | sin errores | `BR-AE-05`, `BR-E-05` |
| las de la orden a tipo general, sin el tipo de la línea | `BR-S-08` e `IVA-TIPO-SIN-DESGLOSE` | los mismos y `BR-S-05`, que es la causa |

**Lo que se hizo.** En `iva.py` el tipo que falta cuenta como mal en todas las
categorías menos en la O, con su propio mensaje: dice que falta y no que no
está a cero, y en «Tiene» pone «(sin tipo)», como BR-48. «Falta» es lo mismo
que en BR-48, que no haya un número que leer; un tipo escrito que no es un
número lo denuncia además el XSD. Las fichas de las 24 reglas lo dicen, y la
de `BR-AG-05`, que decía lo contrario, se reescribió. No hay código nuevo ni
cambia ninguna gravedad.

**Lo que hace que no vuelva.** `test_norma_oficial` evalúa con lxml el texto
de las 27 reglas en las tres vinculaciones sobre un concepto sin tipo y lo
compara con lo que dice el motor. lxml habla XPath 1 y no conoce `xs:decimal`:
se cambia por `number`, que con el tipo ausente da lo mismo, y es la única
traducción. Si el comité reescribe alguna para admitir el tipo ausente, se
pone en rojo. No es correr el esquematrón, que aquí no se corre: es evaluar su
expresión en el único caso que importa.

**En el corpus**, de 157 facturas leídas y con el motor de la norma europea
solo (`en16931.validar`): de 1106 incidencias a 1108. Son dos
`BR-E-05`, en dos facturas EDIFACT con tres líneas exentas sin tipo cada una,
que ya traían otros nueve códigos de error de la norma. Provocado once veces,
las once en rojo (en HALLAZGOS).

### El IGIC a cero en CII: se sigue a la norma, y se dice

**`BR-AF-05`, `06` y `07` no dicen lo mismo en cada vinculación.** El texto de
la regla pide para el IGIC un tipo «0 (zero) or greater than zero». La
vinculación de UBL lo escribe `>= 0`; la de CII, `> 0`, y la del IPSI en CII,
al lado, `>= 0`. Una línea de IGIC al 0 % en CII es mala para el esquematrón
oficial de CII y buena para la norma. Está denunciado en el repositorio
oficial: la issue 519, abierta el 07-09-2026, se cerró el 29-09-2026 cambiando
los nombres de las reglas y no la comparación, que el 12-10-2026 seguía igual
en `master` (leído en la web, no descargado).

**Se sigue al texto.** Es lo que se hizo con el periodo que el esquematrón de
CII no encuentra y con el `D_D4461` de EDIFACT: cuando una vinculación no hace
lo que dice el texto de su propia regla, manda el texto. Con los márgenes es al
revés porque ahí el texto no dice nada. **Y se dice en una nota**,
`IVA-CERO-ESQUEMATRON`: quien reciba la factura y la pase por el esquematrón
de CII la verá rechazada, y eso no se calla. No es un aviso porque en la
factura no hay nada que arreglar.

Qué sintaxis rechaza qué está en `Sintaxis.cero_que_rechaza_su_esquematron`,
`{"L"}` en CII, y `test_norma_oficial` lo lee de cada vinculación con un cero
escrito: si el comité arregla CII, se pone en rojo. EDIFACT, cuyo esquematrón
rechaza también el cero del IPSI, va con UBL, como en los márgenes. En el
corpus no cambia nada: de las 19 facturas CII, ninguna lleva IGIC. De 394
códigos a 395. Provocado once veces, las once en rojo (en HALLAZGOS), donde
está también lo que se vio de paso: en `master` las reglas del IGIC y del IPSI
cambian de nombre, y en CII el cambio salió cruzado.

**Y lo que se decía de esos nombres era falso.** Al pasar a `BR-AF-*` y
`BR-AG-*`, el 26-08-2026, se contó que `BR-IG-*` y `BR-IP-*` eran un invento
de este proyecto y que no existían en ninguna norma, y la frase se fue
copiando: ese día en este README, en la cabecera de `facturae.py` y en el
comentario de `iva.REGLAS`; el 06-09, en otro de `iva.py`, y el 12-09, en la
ficha de `BR-AG-01`, que sale en la página. El esquematrón del CEN los usó en
UBL en todas sus versiones publicadas, de la 1.0.0 (2018) a la 1.3.13; la
1.3.14 los cambió por `BR-AF-*` y `BR-AG-*`, que CII había usado siempre, y la
1.3.17, del 12-10-2026, vuelve a ellos. En EDIFACT, el texto de los mensajes
dice `BR-IG` y `BR-IP` también en la 1.3.16. Lo encontró la auditoría de la
1.3.17, el mismo día que salió. Se siguieron enseñando `BR-AF-*` y `BR-AG-*`,
que eran los de la copia fijada, hasta que se trajo la 1.3.17 (abajo). Y la
ficha de `BR-AF-01` contaba una familia de seis reglas, y son diez.

Una prueba de `test_documentacion.py` lee el validador y el README y se niega
si una frase nombra esos códigos y, ella o la de al lado, dice que no existen,
que se inventaron o que salieron por analogía, salvo que diga también que eso
es falso. Otras dos atan las fichas a la copia: las de `BR-IG-01` y `BR-IP-01`
tienen que nombrar la versión fijada, y la de `BR-IG-01`, contar las reglas
`BR-IG` que trae. Se pusieron en rojo al traer la 1.3.17, como estaba previsto,
y se volverán a poner el día que se traiga otra.

### La 1.3.17: los nombres de antes, EL y los VATEX-ES

El 24-10-2026 la copia fijada pasó de la 1.3.16 a la **1.3.17**, la del
12-10-2026 (commit `6e35e0ab`, huella `1f67b2a5…` en `test_norma_oficial`).
Sigue siendo la edición de 2017 de la norma. Con la copia nueva y nada más se
pusieron en rojo veinte pruebas, y cada una dijo una cosa que había cambiado.
Lo decidió el titular el 12-10-2026, con la auditoría delante.

**Los nombres del IGIC y del IPSI.** Aquí vuelven a ser `BR-IG-*` y `BR-IP-*`
en todas las sintaxis, que es como los llama el modelo de la norma en la 1.3.17
y como los llama UBL. CII los cruzó (su `BR-IP-*` es el IGIC y su `BR-IG-*`, el
IPSI) y EDIFACT sigue con `BR-AF-*` y `BR-AG-*`. Qué nombre da cada
esquematrón está en `Sintaxis.familias_de_su_esquematron`, y
`test_norma_oficial` ya no lo escribe a mano: lo lee de cada vinculación por la
categoría que nombra cada regla, no por su nombre. Con el mapa escrito por
nombre, el IGIC de CII se habría comparado con el IPSI de aquí sin que nada lo
dijera. La nota del cero cita las dos, `BR-IP-05 (aquí, BR-IG-05)`, porque la
primera es la que verá quien la valide con el esquematrón de CII. Las fichas
`BR-IG-01` y `BR-IP-01` cuentan los tres nombres, y las otras dieciocho dicen
en una frase que en CII es al revés y cuál es su ficha.

**Las direcciones.** Las veinte fichas `BR-AF-*` y `BR-AG-*` estaban
publicadas y en el sitemap: redirigen con un 308 a la de su categoría, número
a número. Las dieciocho sin cero que ya había (`/codigo-BR-AF-1`) van directas
a la nueva, sin cadena, y hay dieciocho nuevas para `BR-IG-1` y `BR-IP-1` a
9. Dos pruebas lo guardan: que cada vieja vaya a la de su categoría y no a la
otra, y que ninguna redirección lleve a otra.

**EL, Grecia.** La 1.3.17 lo quitó de la lista de `BR-CO-09` al ponerla al día
con ISO 3166, donde Grecia es GR. Pero EL es como escribe Grecia su prefijo en
el IVA europeo: el artículo 215 de la Directiva 2006/112/CE la autoriza, y el
VIES lo da así. Aquí se sigue admitiendo, con la nota `IVA-PREFIJO-EL`, que
dice que la 1.3.17 lo rechaza y la 1.3.16, la que usa Peppol, no.
`test_norma_oficial` se pone en rojo si el CEN lo devuelve (se le pidió en la
issue 532), y entonces la nota sobra.

**Los VATEX-ES.** La lista CEF-VATEX trae dieciocho códigos de exención de
España, del IVA, del IGIC y del IPSI, que el CEN anunció para usarse en la
norma desde noviembre de 2026 (issue 525 de su repositorio). Valen, con la nota
`IVA-VATEX-ES`, que dice que la 1.3.16 no los tiene y los rechaza con
`BR-CL-22`. El día lo da el registro de la Comisión Europea, leído el
26-10-2026: la versión 9.0 de la lista y la 1.3.17, publicadas el 12-10-2026,
hay que tenerlas en uso desde el 15 de noviembre, y como ese día cae en domingo,
desde el lunes 16. La nota dice el mes.

**Las listas.** Se regeneraron las catorce. Además de los VATEX-ES: STD sale de
las monedas y entra STN (São Tomé cambió de moneda en 2018), ISO 6523 gana
0249, 0250 y 0251, y EAS pierde 0219 y 0220 y gana 9960. Y dos diferencias
entre UBL y CII que esto contaba desaparecen: los países de CII ya no traen AN
ni les falta SS, y los asuntos de nota de la vinculación de UBL son ya los
mismos que los de CII. `BR-DEC-13` y `15` de CII envuelven el valor en
`xs:decimal`, y siguen mirando el valor.

## Por qué este y no otro, contestado sin pedir fe

**Quitada el 25-10-2026.** La portada se acortó y esta sección salió
entera, con la tabla y su nota de procedencia. La tabla era una foto del
15-09-2026 que envejece sola y nombraba a otros por lo que hacen mal, y lo
que defendía ya lo prueban el testigo de la portada y el banco. Queda una
línea, "Compruébalo tú", que cuenta las comprobaciones y lleva al banco, y se
corren allí. Con la tabla se fue su guardián
(`test_lo_que_la_portada_dice_de_otros_lleva_fecha_y_donde_mirarlo`), y la
cifra de esa línea la vigila
`test_la_portada_dice_cuantas_comprobaciones_hay_en_el_banco`. Las anclas,
con su fecha y la de renovarse, las enseña el banco en "Lo que trae puesto".
Lo que sigue cuenta cómo era y por qué se hizo así.

Las fichas de la portada decían **qué** es esto —dónde corre, contra qué,
formatos, precio— y ninguna decía por qué este y no el de al lado. Además, la
del precio no distinguía nada: los validadores gratuitos son gratuitos. En su
sitio va **la firma** —cadena, revocación y sello—, que es la comprobación que
ninguno de los que se miraron hace entera, y el precio baja una línea, al lema.

Lo otro es más difícil. Una lista de virtudes la escribe cualquiera y quien lee
no tiene forma de distinguir al que ha hecho el trabajo del que dice que lo ha
hecho — es el mismo problema que tiene un informe que pone «FACTURA VÁLIDA» sin
decir contra qué, que es lo que este proyecto entero se dedica a no hacer. Así
que la sección nueva de la portada no enumera nada: **corre**. Un botón, y las
comprobaciones del banco se ejecutan en el navegador de quien mira, contra el
mismo código que acaba de leer su factura, con su resultado y su tiempo.

Una de ellas es «esta página no le pide nada a nadie». O sea que **la promesa
de privacidad del aviso legal se comprueba desde la portada, apretando un
botón**, sin creerse a nadie. Eso es lo que no puede copiar una lista de
virtudes: no es una afirmación mejor redactada, es una afirmación que se puede
ejecutar.

Se corren las que hay, todas, y no una selección: una demostración recortada es
otra forma de pedir fe. Y si falta el paquete de esquemas y anclas, el
resultado lo dice en la misma frase en que da el recuento — «pasan todas»
encima de una página que no comprueba ni la forma ni de quién es el certificado
sería exactamente la falsa tranquilidad que el resto de la página evita.

### Lo que se dice de los demás va con fecha, enlace y un sitio donde quejarse

La sección afirma dos cosas sobre terceros: que ninguno de los validadores
gratuitos que se miraron enseña sus comprobaciones corriendo, y que de la firma
dicen poco o no dicen nada. Las dos fueron verdad el **11-09-2026** y pueden
dejar de serlo mañana sin que aquí se entere nadie, que es lo peor que le puede
pasar a una afirmación.

Lo único que se le puede exigir a un dato así es que diga de qué día es, dónde
comprobarlo y por dónde avisar de que ya no vale. Eso es lo que vigila
`test_lo_que_la_portada_dice_de_otros_lleva_fecha_y_donde_mirarlo`: la nota de
procedencia tiene que llevar fecha en dígitos, dos enlaces como mínimo a lo que
cada uno publica de sí mismo, y una dirección de correo.

El segundo guardián es de otra clase. La sección entera dice «compruébalo tú», y
si el botón deja de funcionar **no da error**: se queda apagado, o se queda
«Corriendo…» para siempre, y justo la página que invita a comprobar es la que
ha dejado de poder comprobarse. `test_lo_que_las_paginas_llaman_existe_en_glosa_js`
compara cada `Glosa.loquesea` que llaman las seis páginas con lo que
`window.Glosa` entrega de verdad.

## Lo publicado, repasado contra lo hecho

El 15-09-2026 se leyó lo que dice la web contra lo que hace el repositorio, y
seis cosas se habían quedado atrás. Ninguna era mentira el día que se escribió:

| Qué decía | Qué pasaba |
|---|---|
| la portada: la ficha de quien está detrás «no está publicada» | lo estaba desde el 31-08, nombre y correo, en el aviso legal |
| el aviso legal: «Última actualización: 30 de agosto» | la política cambió el 31, con el buzón en Estados Unidos y la ficha |
| lo medido de la privacidad, «el 28 de agosto» | se volvió a medir: 23 ficheros al abrir, todos de `www.glosa-e.com`; 0 peticiones al validar `fe-0001.xml`; sin cookies y sin nada guardado |
| «Son unos 15 MB la primera vez» | 9,86 MB por el cable, con el HTML; 15 era lo que ocupa en disco |
| el alcance: «EN 16931 y RD 238/2026» | faltaban las 223 reglas —219 hechas y 4 imposibles—, el contraste con las pruebas oficiales y el borrador del anexo I |
| la licencia | ver «La línea de autoría» |

Dos guardianes nuevos, para que no vuelva a pasar por el mismo sitio:

- **Las cifras de la norma en la web** —portada, aviso legal y libro blanco—
  se leen de las páginas y se comparan con lo que mide `test_norma_oficial.py`:
  reglas, hechas, imposibles, cuántas tienen casos oficiales y cuántos casos.
  «Dice lo mismo que la prueba» exige además `DISCREPANCIAS` vacía.
- **La fecha de la política va atada a su texto.** Una fecha no se deduce de
  nada, así que `test_documentacion.py` guarda la huella SHA-256 de lo que la
  página dice —sin marcado, sin comentarios, con la ficha de `glosa.js`, que
  es de donde salen el responsable y el correo— al lado de la fecha. Cambiar
  una palabra sin cambiar la fecha es rojo.

Los dos se provocaron: una palabra de la política, solo la fecha, el correo de
la ficha, la licencia quitada, una regla de menos en la portada, otros casos en
el aviso legal, la frase reescrita y una discrepancia declarada, ocho rojos. Un
comentario HTML cambiado sigue en verde, que es lo que tiene que pasar.

## Lo que distingue a esto, contado por el navegador de quien mira

Que la factura no sale del ordenador, que no hay terceros, que no hay cookies
ni analítica: eso lo escribe cualquiera en una línea, y quien lee no distingue
al que lo cumple del que lo dice. Estaba en el aviso legal, medido, y en la
portada no se veía; en el móvil, «no se sube a ningún sitio» ni siquiera cabía
en la primera pantalla.

### El testigo

Debajo del lema, a la izquierda de la herramienta, un panel que **cuenta**
en lugar de afirmar: cuántos ficheros
ha pedido la página y a qué dominios, cuántas cookies hay, si hay algo guardado
en el navegador, y —en cuanto se suelta una factura— cuántas peticiones se han
hecho mientras se leía. Las cifras las da el propio navegador (Resource
Timing), suben en directo mientras se descarga el validador, y la lista de
ficheros con su peso está a un clic.

Cuatro decisiones, y las cuatro salen de no pintar una cifra que nadie ha
contado:

- **Un observador, no el búfer.** `performance.getEntriesByType` deja de
  apuntar a partir de 250 entradas, y el contador se quedaría quieto diciendo
  cero. Provocado con el búfer a 1: el búfer se quedó en 23 y el testigo contó
  24.
- **La ventana de la lectura se cierra al hacer otra cosa, no al acabar.** Una
  petición se apunta cuando termina, y cerrar antes la dejaría fuera. Si cae
  algo de más, se cuenta de más.
- **Dice lo que no ve.** Las cookies HttpOnly y lo que hagan las extensiones no
  se ven desde la página, y el pie lo dice —en el móvil, a un toque—. Si el
  navegador no deja contar, el testigo dice «sin contar» en vez de ceros.
- **Cuenta lo que ha viajado, no lo que ocupa.** Apuntaba
  `encodedBodySize` —el tamaño del cuerpo, venga de donde venga— y lo pintaba
  como red. Medido en una segunda visita: 21 de 23 ficheros no pasaron por la
  red y el testigo seguía diciendo 17,7 MB. Ahora se apunta también
  `transferSize`, que es cero cuando algo sale de la caché, y se enseñan las
  dos: «10,2 MB por la red y 7,5 MB de tu caché». Son tres casos y no dos,
  porque un dominio ajeno sin `Timing-Allow-Origin` deja las dos cifras a cero
  y eso no es venir de la caché: ese sale con una raya.

Provocado en el navegador: una imagen de otro dominio lo pone en rojo con el
nombre del dominio, una cookie y un dato guardado aparecen a los dos segundos,
y una petición ajena durante la lectura sale en rojo en la fila de la factura.

El mismo recuento va al pie del veredicto de cada informe: «Mientras se leía,
tu navegador no ha hecho ninguna petición».

### La política de contenido: de «no lo hace» a «no puede»

Contar las peticiones dice que no han pasado. `--sitio` pone ahora en cada
página, como primera cosa del `<head>`, una política de contenido que le
prohíbe al navegador pedir scripts, datos, imágenes o letras a otro dominio. Va
en un `<meta>` y no en una cabecera por tres razones: viaja con el sitio, se
prueba en local igual que en producción, y los scripts en línea se autorizan
**por su huella**, calculada sobre la página que se publica —y sobre el texto
con LF, que es como lo lee el navegador, no sobre los CRLF de Windows—.
`frame-ancestors`, que un `<meta>` no admite, va de cabecera en `vercel.json`
junto a `nosniff` y `Referrer-Policy: no-referrer`.

Medido antes de escribir nada: Pyodide arranca, valida y corre el banco con la
política puesta, sin una sola violación. Le basta `'wasm-unsafe-eval'`, que no
abre el `eval` de JavaScript.

Lo que la política bloquearía **en silencio** no se monta (`SinPolitica`): un
`onclick=`, un `href="javascript:"`, un `<script>` en línea con atributos, o
una página sin `<meta charset>` donde ponerla primero. Cinco roturas del
montaje, cinco rojos.

Y el banco tiene una comprobación nueva, la 42, «el navegador tiene orden de no
pedir nada fuera»: que la política está, que dice lo que tiene que decir, y
que el navegador la cumple. Esto último sin tocar la red: la política no
permite `eval`, así que si `eval` corre, está escrita y nadie la aplica. Probarlo
con una petición a otro dominio sería justo lo que la página no hace, y un
intento bloqueado deja apunte en Resource Timing y pondría en rojo al testigo.
Provocada en la página montada: sin la política, con `connect-src` abierto y con
la política movida al `<body>` —donde el navegador la ignora—, tres rojos con su
motivo. Un script tocado después de montar no llega a correr.

No es crítica: en la carpeta `web/` sin montar sale en rojo, y es verdad.

### Frente a los demás, con fecha y sin suponer

«Por qué este» lleva una tabla de seis preguntas —adónde va la factura, quién
más se entera, qué deja en el navegador, la firma, si se ve cómo comprueba y qué
formatos lee— con dos respuestas: la de los seis validadores gratuitos de
facturas españolas que salen buscando, y la de aquí. Sin nombres en la tabla;
van al pie, con su enlace, la fecha y un correo para avisar de que algo cambió.

Antes de escribir una celda se abrieron los seis el **15-09-2026**, sin aceptar
nada y sin subirles ninguna factura: lo que apuntó el navegador al abrir cada
herramienta, su formulario y lo que cada uno publica de sí mismo.

| | Lo medido |
|---|---|
| la factura | tres la envían a su servidor con un formulario `multipart`; dos dicen que se lee en el navegador; uno no lo aclara |
| terceros al abrir | cuatro le piden algo a Google: analítica o etiquetas |
| lo que dejan | tres ponen cookies sin aceptar nada, de 2 a 10; dos guardan datos en el navegador; cuatro en total |
| la firma | ninguno dice contra qué lista la comprueba ni si mira la revocación; dos solo miran que esté |
| las comprobaciones | ninguno las enseña corriendo |
| formatos | cuatro leen solo Facturae |

**Lo que no se esperaba, y va en la tabla igual:** dos de los seis dicen, como
esta página, que la factura no sale del navegador, y uno de ellos no le pide
nada a nadie al abrir. La frase «tu factura no se sube» no distingue a nadie.
Lo que distingue es poder comprobarla —el testigo, la política, el banco— y lo
que viene detrás: la firma hasta la lista del Estado y los cuatro formatos.
Escrita de memoria, la tabla habría dicho que «los demás la suben», y era falso
para un tercio.

### Una sola voz

La web hablaba en tres personas: «te decimos», «no nos gusta», «Escríbenos» al
lado de «Escríbeme», y el informe decía «no sabemos reproducir» junto a «solo
se sabe verificar RSA». Ahora habla como el informe, en impersonal, y en
primera del singular solo para el contacto. Cambiaron la portada, el aviso
legal, el banco, el libro blanco, el menú de las seis páginas, la entrada de la
bitácora y veintiún mensajes del informe —«aquí no se sabe reproducir»—.

`tests/test_voz.py` lo vigila con una red de forma: -amos, -emos, -imos, -áis,
-éis, nos, nuestro, en las páginas sin comentarios, en el JavaScript y en las
cadenas del informe y del banco sin docstrings. Primero se comprueba que la red
caza las frases que ya se colaron; lo que caiga sin ser un verbo va a una lista
con su motivo, que hoy tiene una palabra: «tramos». Provocado en el lema, en la
bitácora, en un mensaje del informe y en un texto que pinta el JavaScript:
cuatro rojos. En un comentario HTML, verde.

### Quién responde

La política decía «Responsable del tratamiento: Glosa-e», que es una marca y no
identifica a nadie ante quien ejercer un derecho. Desde el 15-09-2026 la ficha
de `glosa.js` lleva el nombre de quien responde —**Dunior Hernández Martínez**—
y la marca en su propio campo, y el aviso legal pinta las dos cosas.
`test_el_responsable_del_tratamiento_es_alguien_y_no_la_marca` impide que el
nombre vuelva a ser la marca. NIF y domicilio siguen sin publicarse, por lo de
siempre.

De paso se corrigió la nota interna sobre el representante en la Unión, que lo
ataba a cobrar: el artículo 3.2 del RGPD alcanza la oferta de servicios aunque
sea gratis. Lo que puede eximir es el 27.2, el tratamiento ocasional, y queda
para un asesor.

### Las cifras, en la portada

La ficha cambia «Dónde corre», que ya lo cuenta el testigo, por **219 de sus 223
reglas**; el botón del banco dice cuántas corre, y «Qué mira» cuántos códigos
hay explicados. Las tres con guardián contra lo que se mide.

Desde el 25-10-2026 el botón ya no está: la cifra del banco la dice la línea
"Compruébalo tú", y la de los códigos, la fila "Cada código, explicado" de la
lista "Qué hace". Los guardianes siguen, leyendo esas frases.

## La portada, repasada contra las de al lado

El 23-09-2026 se miró la página, en escritorio y en móvil, contra once que
hacen lo mismo o algo parecido: los cinco validadores españoles que siguen en
pie, Docuflair, el validador oficial de Baden-Württemberg, el HTTP Observatory
de Mozilla, Squoosh, FACe y ecosio. En ninguna se soltó una factura. De ahí
salieron dos direcciones, dibujadas en un lienzo privado
(<https://claude.ai/artifact/TUWiqfritYmasTkNcdnctm>), y diez propuestas.
**Se eligió la B, el folio glosado**: la zona de soltar dentro de un informe de
muestra, con tres glosas de verdad al margen.

Lo que se midió en la nuestra antes de proponer nada:

- **La zona de soltar empieza a 834 px** en cualquier escritorio. A 1366×768 no
  asoma, a 1440×900 asoman 66 de sus 208 px, y solo a 1920×1080 se ve entera.
  Los cinco españoles ponen la herramienta en la primera pantalla.
- **En el informe, el texto del margen pisa el filete**: 2 px en los 33
  rótulos de un informe medido a 1100 px. El cuerpo se corre 1,35rem a la
  izquierda y el hueco entre columnas es de 1,25rem.
- **El informe de ejemplo enseñaba los asteriscos** de «\*\*existen los 19\*\*».

### Las diez, en orden, y la tanda de cada una

Se hacen por tandas, con un commit por tanda y sin publicar ninguna; al final
se repasa todo junto y entonces se publica y se comprueba en producción.

1. **Las marcas que se ven tal cual.** No era un mensaje: eran seis, y además
   quince páginas de códigos que imprimían las explicaciones de `glosario.py`
   con sus `**` y sus comillas invertidas. — *Tanda 1, hecha.*
2. **La herramienta en la primera pantalla, con forma de informe.** A la
   derecha del titular, un folio con tres glosas de las facturas de muestra
   —un error, un aviso y una nota, con su texto de verdad— y, en el mismo
   folio, la zona de soltar: «Y aquí, al margen, las de la tuya». Enseña lo
   que da la herramienta antes de pedir nada. Sale de los españoles (la
   herramienta arriba), de Baden-Württemberg (la explicación a un lado, la
   herramienta al otro) y de Squoosh (la zona es la portada). — *Tanda 3, hecha.*
3. **Cuatro facturas de muestra en vez de una**: Facturae firmada, UBL, CII y
   EDIFACT. Hoy solo se puede ver cómo es un aviso, nunca un error. Ya viajan
   con la página, así que no pesan nada. De Squoosh. — *Tanda 3, hecha.*
4. **El informe, pasado a limpio.** El veredicto en Literata con la cuenta
   dentro de la frase, un «Qué se ha mirado» en tres columnas —la forma, el
   contenido y la firma— antes del detalle, aire entre el margen y el filete,
   y un corchete del color de la gravedad en vez de la raya lateral. Lo del
   resumen antes del detalle sale del Observatory. — *Tanda 2, hecha.*
5. **El testigo, compacto en el móvil**: tres líneas y un enlace a lo que ha
   pedido la página. Así la zona entra en la primera pantalla sin quitar el
   testigo de delante; a cambio, las explicaciones quedan a un toque. —
   *Tanda 3 y 4, hecha*: en una ventana de 375×812 la zona está entera en
   la primera pantalla, de 610 a 809 px, y el folio pone la zona delante de
   sus glosas por debajo de 54rem. En el teléfono el navegador se queda parte
   de la pantalla para sus barras: a 375×667 entra el rótulo y no el botón.
6. **La cabecera: el signo y el nombre en vez del bloque gris**, que a 40 px de
   alto parece una imagen que no ha cargado. **Reabre una decisión de
   [MARCA.md](MARCA.md)** —el bloque plateado es la firma—, así que la decidía
   el titular: la aprobó el 23-09-2026. — *Tanda 3, hecha.*
7. **Pegar el XML**, además de soltar el fichero, para quien lo tiene copiado
   de un correo o de su programa de facturación. De Docuflair. — *Tanda 5,
   hecha.*
8. **«Desconecta la red y suelta la factura»**: una prueba que cualquiera hace
   por sí mismo. Medido antes de escribirlo: con la página cargada y el
   servidor apagado, las cuatro muestras dan el mismo informe y ninguna
   petición. Va con su condición, «Listo». — *Tanda 6, hecha.*
9. **El HTTP Observatory de Mozilla, con fecha**: A+, 140/100 y 12 de 12
   pruebas el 23-09-2026. Es un tercero que lo mide. En la política, con su
   fecha y su enlace. — *Tanda 6, hecha.*
10. **Decir cuál es la herramienta oficial** para la validez legal de una
    firma, como hace FacturaView con VALIDe. Antes hay que comprobar que la
    referencia es la buena y sigue viva: el enlace de FACe a su validador ya
    da «página no encontrada». VALIDe contestaba el 24-09-2026; va en la
    pregunta de la Agencia Tributaria, diciendo que allí la factura se envía.
    — *Tanda 6, hecha.*

Lo que se vio en los demás y **no** se copia: pastillas del tipo «100 %
Privado», rejillas de iconos, pasos 01/02/03, degradados, bloques de venta y
avisos de cookies.

Fuera de la lista, de antes: la tarjeta social (`web/marca/tarjeta.png`)
seguía pintada con el gris anterior al del 23-09-2026. Regenerada el
24-09-2026, con la Literata que sirve la página y sin bajar nada.

## La marca

Lo construido se llama **Glosa-e**, y en [MARCA.md](MARCA.md) está por qué y qué
promete.

Una glosa es la explicación que se escribe al lado de un texto que no se
entiende solo: va en el margen, no toca el original y no lo sustituye. Es lo
que hace esto con un XML que nadie puede leer.

Lo que decidió el nombre fue lo que hay que descartar. **Cotejo**, que por
significado era el mejor, es la palabra oficial de la AEAT —la app de la
Agencia tiene «Cotejo de facturas VERI\*FACTU»—, y con ella prometeríamos
comprobar contra el registro de Hacienda, que no es lo que hacemos. Y queda
fuera todo nombre que signifique certificar o dar fe: el valor de este informe
es que **no afirma de más**, y un nombre que prometa fe pública pelea con el
producto todos los días. Una glosa explica; no certifica.

> Glosa-e — lo que dice tu factura, y lo que no se ha podido mirar.

## La licencia

**AGPL-3.0-only**, desde el 1 de septiembre de 2026. El texto entero está en
[`LICENSE`](LICENSE) y viaja **dentro de la propia rueda**, en
`factura_e-0.1.0.dist-info/licenses/LICENSE`.

**Antes era MIT, y MIT no encajaba con lo que esto es.** Aquí no hay un
servidor que guarde el motor: la página se lo baja al navegador de quien la
abre, y lo que se baja es un `.whl` con los veinticuatro módulos **en claro**.
Es decir que el código fuente completo se entrega, sin excepción, a todo el que
visita la página. Eso no es un descuido —es la arquitectura, y es lo que hace
que la factura no salga del ordenador—, pero con MIT significaba regalar el
producto con permiso para cerrarlo.

**La AGPL no impide llevárselo. Impide llevárselo y cerrarlo.** Cualquiera
puede seguir bajando la rueda, leerla, estudiarla, modificarla y usarla; lo que
tiene que hacer si la distribuye es entregar su fuente bajo la misma licencia.
El artículo 13 añade el caso de la red, pero empieza diciendo «if you modify the
Program»: solo alcanza a las versiones modificadas que se ofrecen por red. Quien
monte un servicio web con la rueda sin tocarla no debe nada, y el uso interno no
dispara la licencia en ningún caso. Es menos de lo que suele contarse de la
AGPL, y se escribe así porque dar por cerrado lo que no lo está es justo el
fallo que este repositorio persigue.

**`only` y no `or-later`, a propósito.** Es la misma regla que con Pyodide y
lxml: las versiones se fijan y no se siguen a `latest`. Lo que se cede tiene
que estar escrito y no moverse solo, y si algún día hay licencia comercial —el
otro lado de una copyleft— los términos que se dispensan han de ser unos
concretos y conocidos.

**Lo que la AGPL no arregla, y conviene no confundir.** No hace privado nada:
el repositorio puede seguir cerrado, pero quien recibe la rueda recibe con ella
el derecho a redistribuirla. Tampoco convierte en infracción competir; solo
obliga a que quien la distribuya juegue con las mismas cartas.

Glosa y Glosa-e son marcas del titular; la licencia AGPL cubre el código, no el
nombre.

## Fuentes

- [RD 238/2026 en el Observatorio de Contratación Pública](https://obcp.es/noticias/real-decreto-2382026-de-25-de-marzo-por-el-que-se-desarrolla-el-sistema-de-facturacion)
- [Qué cambia de verdad tras el RD 238/2026 — ASSET](https://asset.es/factura-electronica-b2b-en-espana-que-cambia-de-verdad-tras-el-rd-238-2026/)
- [Guía RD 238/2026: estados y plazos de pago](https://www.lealtadis.es/factura-electronica-b2b-estados-pago-pymes/)
- [Artefactos oficiales de validación EN 16931 (CEN/TC 434)](https://github.com/ConnectingEurope/eInvoicing-EN16931)
- [Ubicación de la lista de listas (LOTL) y certificados que la firman — DOUE C/2026/1944](https://eur-lex.europa.eu/eli/C/2026/1944/oj/eng)
- [Lista de confianza española (TSL) — Ministerio para la Transformación Digital](https://digital.sede.gob.es/pagina?id=Lista-de-confianza-de-prestadores-cualificados-de-servicios-electr%C3%B3nicos-de-confianza)
