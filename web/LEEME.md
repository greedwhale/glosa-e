# El validador dentro del navegador

En `web/` hay dos páginas y un módulo que las dos cargan:

| Fichero | Qué es |
|---|---|
| `index.html` | **Glosa-e**, la herramienta: se suelta una factura y sale su glosa |
| `banco.html` | el banco de pruebas, que es de lo que trata este documento |
| `glosa.js` | arrancar Pyodide, instalar el wheel y traer el paquete |

Este documento va del **banco**. No es la web del producto: es la prueba de que
el producto es posible, y comprueba que Factura-e funciona entero dentro de un
navegador, sin servidor y sin que la factura salga del ordenador de quien la
mira.

Las dos páginas arrancan igual y con el mismo código, y eso importa: lo que el
banco comprueba es exactamente lo que la herramienta ejecuta. Si el arranque
viviera dos veces, un día arreglarían cosas distintas y el banco daría verde
sobre algo que la herramienta no hace.

La pregunta que contesta no es «¿arranca Python en el navegador?» —eso ya se
sabía— sino **«¿trae esta compilación de lxml todo lo que el validador usa?»**.
libxml2 se puede compilar sin soporte de esquemas XSD, y `esquema.py` entero
depende de `etree.XMLSchema`. Si faltara, habría que reescribir esa parte.

Trae soporte de XSD. Compila un esquema, acepta lo válido, rechaza lo inválido
y llena el `error_log` del que salen los mensajes.

Al añadirse la firma apareció una segunda pregunta del mismo calibre: **¿esta
compilación canonicaliza igual que la de fuera?** También sí, byte a byte. Y la
cadena de confianza encadena aquí igual, que era menos dudoso —es aritmética de
enteros— pero se ha mirado en vez de suponerlo.

## Cómo ejecutarla

Hacen falta dos cosas: el paquete construido como *wheel*, y un servidor local
—un `file://` no vale, porque el navegador no deja cargar módulos así.

```
python -m validador --traer-pyodide
python -m build --wheel --outdir dist
python -m http.server 8765
```

Eso sirve las plantillas de `web/`. El **sitio montado** (`--sitio`) no se
mira así: enlaza por la dirección limpia —`./legal`, no `./legal.html`—, igual
que en producción, y `http.server` le da 404. Para ese está
`python herramientas/servir_sitio.py 8322 --bind 127.0.0.1 --directory sitio`,
que sirve como Vercel.

Lo primero solo hace falta una vez: baja el intérprete de Python para
WebAssembly —unos 15 MB— a `vendor/pyodide/`, que no se versiona. Se sirve
desde aquí en vez de pedírselo a un CDN, porque cada visita a un CDN ajeno
manda la IP de quien mira la página a un tercero, y la página promete que no
habla con nadie. `--sitio` **se niega a montar** si falta.

Y abrir <http://127.0.0.1:8765/web/> para la herramienta, o
<http://127.0.0.1:8765/web/banco.html> para el banco.

La página busca sola el `.whl` más reciente de `dist/`, así que no hay que
tocar nada al subir la versión en `pyproject.toml`.

**Hay que reconstruirlo cada vez que se toque `validador/`.** La página carga
el wheel, no la carpeta, así que un wheel viejo ejecuta código viejo. Y si
mientras tanto ha aparecido un módulo nuevo, ni siquiera arranca: `factura.py`
lo importa y el wheel no lo trae. Pasó al añadir `facturae.py` —la página
quedó rota sin que nada lo dijera, porque `dist/` no se versiona y los tests
corren contra la carpeta, no contra el paquete—.

Volvió a pasar al añadir `revocacion.py`, y la comprobación «el paquete
validador importa» pasó a **recorrer el paquete instalado e importarlos todos**
en vez de llevar una lista escrita a mano. Y eso, por sí solo, estaba mal: se
volvió a comprobar al añadir `edifact.py`, con un wheel de la víspera dentro, y
esa comprobación salió **en verde** diciendo «los 17 módulos» sin `edifact`
entre ellos; el fallo apareció cinco pruebas más abajo como un `ImportError`.

Recorrer el paquete pregunta qué trae el wheel, no si el wheel es el de ahora.
Una lista escrita a mano se queda corta —y entonces **falla**, que es lo que
tiene que pasar—; recorrer el paquete hace que **pase**. De los dos fallos, el
caro es el segundo. Así que ahora hace las dos cosas: los recorre y los importa
todos, y además comprueba que estén los que tienen que estar, diciendo cuál
falta y que hay que reconstruir el wheel. La página,
además, le añade un `?v=` a la URL del wheel: el nombre no cambia entre
compilaciones de la misma versión, y sin eso el navegador puede servir el de su
caché —todo verde, y no es lo que crees que has probado—.

## Qué mirar

Arriba, el tiempo de arranque. Abajo, 43 comprobaciones que deben salir todas
en verde; 32 están marcadas como **críticas** y son las que, si fallan, tumban
la idea entera. Están todas, en el orden en que corren, y esa lista completa
no es cosmética: la tabla se quedó corta durante meses, con críticas sin
fila que nadie echaba de menos, y una comprobación que no aparece en la lista de lo
que hay que mirar es, para quien lee, una comprobación que no existe. Lo
guarda `tests/test_cifras_publicadas.py`, que compara esta tabla con el banco
en los dos sentidos.

| Comprobación | Por qué es crítica |
|---|---|
| lxml carga en WebAssembly | sin esto no hay nada |
| libxml2 trae soporte de esquemas XSD | de ello depende `esquema.py` |
| el paquete validador importa | el wheel se instala de verdad |
| el parser endurecido no expande entidades | una factura ajena no debe poder leer ficheros |
| una factura correcta sale conforme | sin falsos positivos |
| una factura rota se caza | sin falsos negativos |
| lxml canonicaliza igual que fuera del navegador | de ello depende `firma.py` entero |
| se verifica una firma RSA de verdad | sin `cryptography`, que aquí no hay |
| la cadena de confianza se encadena aquí también | de ello depende `cadena.py` |
| el informe declara de dónde salen las anclas | es la condición para traerlas puestas |
| una lista de revocación se lee y se comprueba aquí | de ello depende `revocacion.py` |
| una respuesta OCSP del documento se verifica aquí | un XAdES-XL moderno guarda OCSP y a menudo no guarda CRL: sin esto, de esos documentos la revocación no se comprueba nunca. Y es el único sitio donde entra SHA-1 |
| se verifica una firma de curva elíptica | un tercio de las autoridades españolas firma así |
| las curvas son las de verdad, también aquí | una errata en un parámetro no da error: da «no verifica» |
| una lista de confianza se comprueba y se monta aquí | de ello depende `tsl.py`, y con él de dónde salen las anclas |
| una lista de confianza manipulada no monta nada | un almacén mal montado no da un error: da un aprobado |
| una autoridad retirada solo vale para lo de antes | si la ventana no se aplica, 135 autoridades caducadas pasan a ser de confianza |
| un sello de tiempo se lee y se comprueba aquí | de la fecha del sello cuelgan la caducidad y la revocación |
| un sello sin permiso para sellar no vale | su firma es válida: lo único que falla es el permiso, y eso no salta solo |
| las anclas de sellado van aparte de las de firma | juntas, 11 autoridades pasarían a avalar firmas de facturas |
| un EDIFACT plano se lee y se valida aquí | es el cuarto formato de la ley, y el único que no es XML |
| las rutas de EDIFACT valen con este libxml2 | van con predicados y con el eje `self::`, más XPath del que usan UBL y CII; si fallaran no darían error, darían una factura sin líneas ni desglose —o sea, sin nada que comprobar— y diría que está bien |
| un UNA de cinco caracteres se lee igual | el hueco reservado del `UNA` cambia los separadores del intercambio entero; leerlo mal deja el fichero sin ningún mensaje, y eso se cuenta como «aquí no hay nada que validar» |
| un separador sin soltar no tumba el lote | un fichero mal escrito de un remitente no puede llevarse por delante a los demás del lote |
| la promesa del informe cuadra con los esquemas y las anclas que hay | el informe dice qué ha comprobado y qué no; si esa frase se desacopla de lo que trae el paquete, la línea de alcance miente en la dirección peligrosa |
| los esquemas viajan con la página y comprueban la forma | sin ellos la página comprueba el contenido y no la forma, y lo que no se comprueba se da por bueno |
| el esquema de Facturae compila sin red | los XSD del formato nacional importan la firma XMLDSig **por dirección web**; aquí no hay adónde salir, y sin la copia local no compilan |
| los esquemas de entrada compilan con este libxml2 | al empaquetar se compilan con el lxml de fuera, y aquí va otra libxml2: uno que no compile deja cada factura de su formato con `XSD-ESQUEMA-ROTO` y sin la forma comprobada |
| los mensajes de libxml2 se traducen igual con esta versión | las regex de la traducción se escribieron leyendo el libxml2 de fuera; si este redacta una sola frase distinta, todos los errores de forma salen en inglés y solo en el navegador |
| las anclas viajan con la página y dicen de cuándo son | sin ellas no se sabe de quién es el certificado, y sin su fecha un conjunto viejo sigue creyendo a autoridades a las que el Estado ya retiró la cualificación |
| el paquete que ha llegado es el que la ficha dice | un zip truncado se descomprime **sin error** y deja al validador con menos anclas de las que la página dice traer: aprobados de más repartidos en silencio |
| esta página no le pide nada a nadie | es la cifra de cabecera de la privacidad, y `pyodide.js` lleva dentro la dirección de su CDN como respaldo |

Las dos de EDIFACT son las que más costaba prever, y la de las rutas es la que
de verdad podía doler: el mapa de ese formato no puede nombrar los grupos —su
numeración cambia con la versión del directorio— y por eso pregunta por lo que
hay dentro, con más XPath del que necesitan los otros dos. Esta compilación de
libxml2 es más vieja que la de fuera.

Las de la firma —canonicalización, RSA, curvas, cadena, revocación, OCSP,
lista de confianza y sellos— son el bloque más grande, y la de la
canonicalización es la que más podía
doler. `firma.py` calcula el resumen de un documento canonicalizado y lo compara
con el que guarda la firma. Si lxml en WebAssembly escribiera un solo byte
distinto —un atributo en otro orden, un namespace colocado de otra manera— el
resumen saldría distinto y **todas las facturas firmadas se denunciarían como
manipuladas dentro del navegador y solo dentro del navegador**. El valor
esperado está medido fuera, con CPython.

Al final hay una zona donde soltar una factura de verdad. Esa parte es
exactamente la interacción del producto: leer el fichero en el navegador,
validarlo ahí y enseñar el informe. La red no se toca.

## El recuento, al pie del informe

Desde el 19-10-2026, cada informe acaba con el mismo texto que `--recuento` en
consola (en un desplegable cerrado hasta el 25-10-2026; desde entonces, a la
vista, con una línea para escribir si hay dudas): los códigos, en cuántos documentos sale
cada uno y cuántas veces, y los formatos, sin nombres de fichero ni nada de
dentro de las facturas. El botón lo copia al portapapeles, y si el navegador no
lo deja, lo deja seleccionado y lo dice. Copiar no pide nada a la red (medido el
19-10-2026: 24 peticiones antes del clic y 24 después), y el
testigo no cambia.

## La barra y el pie

Desde el 25-10-2026 la barra de arriba enseña cinco entradas fijas: Validar,
Qué significa cada aviso, Sobre Glosa-e, Bitácora y Escríbeme. Hasta ese día
todo iba en una pestaña desplegable, y quien llegaba no veía qué había en el
sitio sin abrirla. En el móvil las cinco no caben y sigue la pestaña, con las
mismas cinco; cada ancho enseña una y esconde la otra, sin JavaScript.

El pie lleva todas las páginas, y es el mismo en las ocho, como el menú. Tres
pruebas lo sostienen: que el pie no se separe entre páginas, que lleve todo lo
que lleva la barra y que la barra no pase de cinco. Lo que hizo desplegable la
barra la primera vez fue eso, crecer con cada página; ahora lo nuevo va al pie.

## El código de cada incidencia, con su ficha

Desde el 25-10-2026, en el sitio montado el código de cada incidencia es un
enlace a su ficha (`./codigo-BR-CO-10`), en otra pestaña para no perder el
informe. Solo enlazan los códigos que tienen ficha: la lista la pone el
montaje en `data-fichas` y la página no la deduce. Servida `web/` a secas la
lista está vacía y el informe sale en texto. Medido el 25-10-2026 con
`f-0006.xml` en el servidor `sitio`: cada código del informe salió enlazado,
y cada enlace contestó 200.

## Las novedades y su canal Atom

Desde el 25-10-2026, `novedades.html` junta cada regla nueva o retirada, por
fecha, y `novedades.xml` dice lo mismo en Atom; los artículos tienen el suyo,
`bitacora.xml`. La página sale de su plantilla y de `novedades.txt`, que no
se copian tal cual, y lleva el botón Seguir las novedades, que se despliega
sin guion (es un `<details>`); el guion solo copia la dirección de cada
canal. La portada anuncia los dos canales con un `<link rel="alternate">`
para los lectores que los buscan solos, el catálogo el de las novedades y la
bitácora el suyo, que heredan sus artículos. Medido el
25-10-2026 en el servidor `sitio`: cada enlace de la página contestó 200, sin
errores en la consola y sin desbordar a 375 px, en claro y en oscuro.

## Resultados medidos

En Chrome, sobre esta máquina, con Pyodide 314.0.6:

| | |
|---|---|
| lxml / libxml2 | 6.0.2 / **2.9.10** |
| Arranque en frío del todo (primera visita) | ~42 s |
| Arranque con la CDN ya cacheada | 11,25 s |
| Arranque con la caché ya caliente | ~4,8 s |
| Validar una factura de una línea | 17–23 ms (el 15-09: 416–463) |
| Validar los 10 de `ejemplos/` | 363 ms, mediana de 7 (el 06-09: 798) |
| Validar una factura de 1.000 líneas | 1,1 s (el 15-09: 5,7) |
| Validar una factura de 4.000 líneas | 4,2–5,3 s (el 15-09: 20,5–23,8) |
| Verificar una firma XAdES | 17 ms |
| Encadenar hasta un ancla de confianza | 3,2 ms |
| Leer y verificar una lista de revocación | 4,8 ms |
| Leer y verificar una respuesta OCSP del documento | 5,7–7,7 ms |
| Declarar el ancla en el informe | 1,5 ms |
| Verificar una firma ECDSA (P-256 / P-384 / P-521) | 10 / 16 / 29 ms |
| Verificar una lista de confianza y montar el ancla | 20,8 ms |
| Rechazar una lista de confianza manipulada | 14,1 ms |
| Validar un lote de 200 | 2,05 s · 10,3 ms cada una · 23 MB de memoria (sin anotar con qué facturas) |
| Lote de la solución pública, de principio a fin, informe pintado (20-10-2026) | 200: 2,7 s · 1.000: 10,7 s · 3.000: 31,4 s |
| Lo más que la página pasa sin contestar durante ese lote | 0,65 s (antes del 20-10, el lote entero) |
| Lo que descomprime el navegador | 17,07 MB (15-09-2026; eran 14,71) |
| Lo que baja por el cable la primera vez | 9,86 MB en 25 peticiones, todas a `www.glosa-e.com` (15-09-2026; eran 24: desde el 20-09 la rueda se pide dos veces y la segunda sale de la caché, 0 bytes medidos) |

Las filas de validar cambiaron el 20-09-2026 y aquí decían de más. «5–120 ms»
se había medido sobre las facturas de ejemplo, que tienen una línea o dos, y se
publicaba como si fuera lo que cuesta validar **una factura**: la auditoría del
15-09-2026 soltó una de 4.000 líneas y la pestaña se quedó bloqueada. Eran dos
cosas, las dos aburridas:

- cada ruta XPath se compilaba en cada uso. Una factura de 800 líneas hacía
  31.235 llamadas a `texto()` y 16.080 a `_nodos()`, compilando las mismas
  cuatro docenas de rutas una y otra vez. Compilándolas una sola vez, medido
  fuera del navegador: una factura de 4.000 líneas pasa de 4.137 ms a 1.705;
- el catálogo de esquemas y el almacén de anclas se rehacían **en cada
  validación**, y no cambian nunca. Fuera del navegador: 70 ms frente a 1,9.
  Esa es la que se nota en una factura normal.

Lo que sigue siendo verdad: 4.000 líneas son 4 segundos largos con la pestaña
parada, porque esto valida en el hilo de la página. Cuatro segundos no son
treinta y ocho, pero tampoco son nada, y quien tenga facturas así conviene que
lo sepa antes de soltarlas.

La fila de los 10 ejemplos se midió el 06-09-2026 sobre `www.glosa-e.com`, con
cuatro pasadas de calentamiento y la mediana de siete, **y con la máquina en
reposo**. Esa última condición no es adorno: la misma medida tomada mientras el
ordenador compilaba ruedas daba 1,4 s, y estuve a punto de publicar eso como si
fuera un dato del validador. Lo que descartó la sospecha de que el código
hubiera empeorado fue cambiar solo la rueda en el mismo navegador: la de antes
del binding tarda 1.367 ms y la de ahora 829, así que va más rápido, no más
lento.

Cuidado con los tiempos de arranque, que son tres cosas distintas: la primera
visita de verdad baja los 14,71 MB; con la CDN cacheada solo se pagan los
11,25 s de montar el intérprete —en la última medición se transfirieron
0,13 MB, todo lo demás salió de la caché—; y con la página ya visitada son
menos de 5 s.

Los 43 resultados coinciden exactamente con los de la misma prueba
ejecutada con Python nativo: mismos códigos, mismos resúmenes, mismos importes.
Es la comprobación que de verdad importa, porque libxml2 aquí es **2.9.10** y
en local es 2.11.9. Dos versiones distintas que dicen lo mismo, **canonicalización
incluida**.

Eso último dejó de ser una curiosidad al entrar la lista de confianza: una TSL
se verifica canonicalizándola, así que un byte de diferencia entre las dos
compilaciones no daría un falso aprobado —daría una lista rechazada y una
página sin anclas—. Verificar y montar cuesta 20,8 ms allí.

## La prueba de soltar una factura firmada

No basta con que las 43 salgan verdes: la zona de arrastre es la
interacción del producto, y hay que verla funcionar. Soltando
`ejemplos/fe-0001.xml`, que es un Facturae 3.2.2 firmado:

```
/entrada/fe-0001.xml
  Facturae v3.2.2 (factura) · firmado — sin errores, 1 aviso(s).
```

Y la misma factura con el total cambiado de 121,00 a 999,00, que es lo que
prueba que no está dando todo por bueno:

```
/entrada/fe-0001-manipulada.xml
  Facturae v3.2.2 (factura) · firmado — 4 error(es), 1 aviso(s).

  [FE-LOTE-TOTAL · formato Facturae] El total de facturas que declara la
  cabecera no es la suma de las facturas que trae dentro.
  [FE-TOTAL · formato Facturae] El total de la factura no es la base más los
  impuestos repercutidos menos los retenidos.
  [FE-PENDIENTE · formato Facturae] El total a pagar no cuadra con el total de
  la factura menos las subvenciones y los anticipos.
  [FIRMA-ALTERADA · firma electrónica] El documento se ha modificado después
  de firmarlo: el documento entero ya no coincide con el resumen que guarda la
  firma. La factura no vale como documento firmado.
```

Cuatro reglas de tres módulos distintos cazándola a la vez, dentro de
WebAssembly, sin que el fichero salga del ordenador.

## Lo que queda por resolver antes de que esto sea un producto

- **Los 9,9 MB del primer arranque.** Eso es lo que viaja por el cable con
  Brotli puesto —el `.wasm` pesa 9,6 MB en disco y 3,6 por el cable—, y no hay
  mucho que rascar sin quitar cosas: 3,6 el intérprete, 2,5 la biblioteca
  estándar, 1,6 lxml, 1,2 los esquemas y las anclas. La primera visita nunca va
  a ser instantánea, y la página lo dice en vez de parecer rota.

  Eran 9,4 hasta el 11-09-2026, cuando entraron los 18 esquemas de UBL 2.5. El
  zip ya viene comprimido y Brotli no le saca nada, así que lo que crece por el
  cable es exactamente lo que crece en disco: 0,25 MB. El 15-09-2026 eran
  9,86, y de esa medida sale el «unos 10 MB» de la portada. El 26-10-2026
  entró el esquema del acuse de la solución pública, y el zip creció 3 KB:
  hoy van 19 esquemas de UBL 2.5.

  Vuelto a medir el 22-09-2026 contra `www.glosa-e.com`, pidiendo con Brotli
  las 24 direcciones que carga una primera visita: **9.966.246 bytes, 9,97 MB**.
  En disco, sin comprimir, esas mismas 24 suman 17.133.045 —el `.wasm` baja de
  9.598.218 a 3.577.499 y `pyodide.asm.mjs` de 1.250.344 a 265.085; lo que ya
  viene comprimido, `paquete.zip` y `python_stdlib.zip`, viaja igual que está—.
  La diferencia entre las dos cifras es la trampa que ya nos costó una
  corrección el 15-09: **medir la red en `localhost:8322` da el tamaño de
  disco**, porque `http.server` no comprime. Ahí el testigo pinta 17,7 MB y no
  es lo que le cuesta a nadie.

  Lo que sí se arregló es **la segunda visita**, que estaba rota de una forma
  que no se veía. Cada fichero se pedía con `?v=` y la hora dentro, para que el
  navegador no sirviera de su caché un wheel de ayer —pasó de verdad, y más de
  una vez—. Cumplía. Y el precio era que la dirección cambiaba en cada visita,
  así que 1,2 MB (el paquete, el wheel y los 10 ejemplos) **no se podían
  guardar nunca**: se bajaban enteros la décima vez igual que la primera. A eso
  se sumaba que Vercel servía todo con `max-age=0, must-revalidate`, o sea 23
  peticiones de ida y vuelta antes de empezar.

  Ahora `--sitio` firma cada fichero por su contenido y lo anuncia en
  `dist/rueda.json`; la página pide `?v=<huella>`, que cambia cuando el fichero
  cambia y no cuando no. Con eso se puede servir el sitio diciendo `immutable,
  max-age=1 año` sin mentir. El manifiesto es lo único que se pide siempre
  fresco: es la raíz de la cadena.

  El intérprete va bajo `/pyodide/314.0.6/` por lo mismo. Sin la versión en la
  dirección, prometer un año de caché sería una trampa: el día que se subiera
  de versión habría gente corriendo la vieja durante un año y ninguna forma de
  avisarles. `--sitio` **se niega a montar** si `glosa.js` y `paquete.py` no
  declaran la misma versión.
- **Los esquemas XSD oficiales sí están aquí**, y esto decía lo contrario. Van
  dentro de `paquete.zip`: 43 ficheros —Facturae 3.0, 3.1, 3.2, 3.2.1 y 3.2.2,
  CII D16B, UBL 2.1 y **UBL 2.5**, que es la referencia de la solución
  pública—, y la página los enseña contados en «lo que trae». Lo que
  sigue siendo cierto es lo otro, y son dos cosas distintas que esta lista tenía
  juntas: **no están versionados** —`git ls-files esquemas` no devuelve nada— y
  **la suite corre sin ellos a propósito**, porque un test cuyo resultado
  dependa de si quien lo ejecuta se ha bajado los XSD no prueba nada.

  De modo que en el navegador la comprobación de forma **se hace**. Lo que
  falta de verdad aquí no es tenerlos: es que el peso del paquete crece con
  ellos, y eso ya está contado arriba en los 9,9 MB.
- **Las anclas de confianza, en el navegador.** Encadenar funciona aquí —está
  comprobado—, y las anclas hay que meterlas en el disco virtual, igual que las
  facturas de ejemplo: unos cientos de KB que se cachean.

  Quién las pone **ya está decidido: las pone la página.** El argumento que lo
  desaconsejaba en el repositorio no aplica aquí, porque **quien pueda servir
  la página ya es dueño del validador entero**: las anclas y el código llegan
  por el mismo canal, y quien pudiera cambiar unas puede cambiar el otro. No
  traerlas no compra seguridad; compra que la comprobación no se haga nunca, y
  un informe que dice «sin errores» sin haber mirado de quién es la firma es
  peor que no tenerlo.

  De dónde salen también está resuelto: de la lista de confianza del Estado,
  verificada. El conjunto se monta con `--montar-anclas` y se mete en el disco
  virtual ya montado, con su `PROCEDENCIA.txt` al lado —que es lo que hace que
  el informe sepa decir de dónde vienen sin que la página tenga que acordarse
  de contarlo—. **Y la página ya enseña de cuándo es el que trae**: la fecha en
  que se montó, de qué lista salió y cuándo toca renovarla, con aviso en ámbar
  si esa fecha ya pasó. Lo que queda es lo único que no puede resolver el
  código: cada cuánto se vuelve a montar, que es una costumbre y no una
  función.

  Lo que sí es innegociable es **decirlo**. El informe declara a qué ancla ha
  llegado, de dónde salió y con qué huella —`Almacen(..., procedencia="viene
  con esta página")`— y hay una comprobación crítica que lo vigila. Traerlas y
  callarlo sería fabricar confianza en silencio, que es exactamente lo que este
  validador existe para no hacer.
- **Las listas de revocación, en cambio, no.** Un ancla es conocimiento que
  dura décadas; una CRL es una noticia que caduca en días. Traerlas con la
  página sería repartir una foto vieja de quién está anulado. Aquí el orden es:
  leer lo que traiga el documento (XAdES-XL), dejar soltar un `.crl` junto a la
  factura, y como mucho un botón que diga qué descarga y de dónde. Nunca de
  fondo.

Un lote de 200 facturas sí se ha medido: 2 segundos y 23 MB. Eso significa que
la parte de pago —el lote del mes de una gestoría— también cabe en el
navegador, sin servidor que mantener ni datos que custodiar.

Esa fila no dice con qué facturas se midió, y el 20-10-2026 se volvió a medir
con miles, de las que pide la solución pública (UBL 2.5; de cada diez, siete
correctas, dos con retención y una rectificativa, todas con su número), con
los esquemas dentro, el panel del navegador oculto y la máquina en reposo:

| Facturas | De principio a fin, informe pintado | Lo más que la página pasa sin contestar | En consola |
|---|---|---|---|
| 200 | 2,7 s | 0,67 s | 1,6 s |
| 1.000 | 10,7 s | 0,22 s | 5,4 s |
| 3.000 | 31,4 s | 0,65 s | 15,4 s |

Con 3.000 sale un solo recuento, el de todo el lote, de 32 líneas.

**Con 10.000**, el mismo día y con la máquina mucho más lenta (en ese momento
3.000 tardaban 67 s en consola, no 15,4; un bucle de Python, de tres a cinco
veces más): 6 min 27 s en el navegador y 3 min en consola, sin un solo error y
con un solo recuento. Lo que crece lo hace en proporción: cada tramo de 1.000
facturas tardó lo mismo de principio a fin (de 12,8 a 14,5 s en consola), y
las reglas entre ficheros y el recuento de las 10.000, 0,2 s cada uno. La
pausa más larga, al juntar el informe: 11,6 s, que bajaron a 4,8 cediendo el
turno también ahí. Después de validar, JavaScript vuelve a 38 MB, el disco
virtual queda vacío y el intérprete ocupa 136 MB, que no devuelve.

Una primera pasada de 10.000 en consola salió en 7 min 44 s: era el antivirus
leyendo los ficheros recién escritos, 26 ms por fichero al abrirlo (medido con
el perfilador). Más de 10.000 no se ha medido, ni con el panel a la vista.

Hasta ese día la página validaba el lote de un tirón: Python corre en el mismo
hilo que pinta, así que se quedaba quieta, sin atender un clic ni decir cómo
iba, todo lo que durase. Ahora el lote cede el turno cada décima de segundo
(`LoteEnMarcha` en `factura.py`, el `await` de `INFORME`) y la página dice
cuántas van. Ceder cuesta: 1.000 facturas, 10,4 s cediendo y 8,2 s sin ceder,
en la misma pestaña, porque en cada pausa se espera a que el navegador pinte
(hasta 20 ms). Es el precio de que se vea cómo va. Y pintar cada informe abierto costaba más que
validar (con 3.000, 21,6 s y 50.000 elementos por cada 1.000): pasados 50
ficheros cada uno sale cerrado, y lo suyo se pinta al abrirlo.

**La primera medida de ese día salió de cuatro a siete veces más lenta, y era
falsa**: la consola y el navegador corrían a la vez y se quitaban la máquina el
uno al otro. Es lo mismo que pasó el 06-09 con la fila de los ejemplos, aquí
arriba. Las de la tabla se tomaron de una en una.
