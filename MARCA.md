# La marca

**Glosa-e.**

Una glosa es la explicación que se escribe al lado de un texto que no se
entiende por sí solo. Se pone en el margen, no dentro: no toca el original, no
lo sustituye y no lo mejora. Solo lo hace legible.

Eso es exactamente lo que hay construido aquí. Una factura electrónica es un
XML que nadie puede leer, con una firma que nadie puede comprobar a ojo, y
detrás una norma —EN 16931, el RD 238/2026— que sí es pública y que sí se puede
aplicar. El validador no añade nada al documento. Lo lee y dice qué pone.

Encaja con la tesis del proyecto, que no ha cambiado: **las reglas son
públicas, el mensaje es el producto.** La glosa es el mensaje.

## Por qué no se llama de las otras maneras

**No se llama Cotejo**, que era el nombre obvio y el mejor por significado
—cotejar es comparar una copia contra el original—. Está cogido, y por quien
peor viene: «cotejo» es la palabra **oficial de la AEAT**. La app de la Agencia
Tributaria tiene una sección «Notificaciones y cotejo» y dentro «Cotejo de
facturas VERI\*FACTU», que comprueba contra el registro de Hacienda si una
factura consta. Llamarse así prometería justo lo que esto no hace.

Lo mismo tumba toda la familia *veri-*: en España esa raíz ya la ocupa
VeriFactu, y usarla es o pedir un pleito o dar a entender que somos oficiales.

**No se llama nada que signifique «certifica», «acredita», «da fe» o
«garantiza».** Esta es la regla de fondo, y va más allá del nombre. El valor de
lo que hemos hecho es precisamente que **no afirma de más**: el informe dice
qué ha mirado, con qué, y qué se ha quedado sin mirar. Un nombre que prometa fe
pública pelea contra el producto todos los días. *Fedatario* además es un
título regulado y no lo somos.

Una glosa no certifica. Explica. Es la promesa que sí se puede cumplir.

## Cómo se dice

**La glosa** es también el nombre del informe. Cada factura tiene la suya.

> «Pásale la glosa a esa factura.»
> «En la glosa pone que la firma llega a una autoridad de la lista del Estado.»

Las tres gravedades no cambian: **ERROR**, **AVISO**, **NOTA**. La NOTA es la
más nuestra y conviene no perderla: es lo que se ha dado por bueno y **con qué
base**.

## La frase

> **Glosa-e — lo que dice tu factura, y lo que no se ha podido mirar.**

Las dos mitades hacen falta. La primera es lo que se compra; la segunda es por
qué se puede creer la primera. Casi nadie pone la segunda, y ahí está el hueco.

De apoyo, según dónde:

- *La factura electrónica, en castellano.*
- *Se lee en tu ordenador. No sale de ahí.*
- *Las reglas son públicas. El trabajo es leerlas por ti.*

La segunda vale mucho comercialmente y es verdad comprobable: la página lleva
Pyodide, los esquemas y las anclas dentro, y no hay servidor al que subir nada.
Un competidor que valide en la nube no puede decirla.

## Cómo se escribe

**Glosa-e**, con ge alta y con guion. Decidido el 30 de agosto de 2026, y es un
cambio de lo que decía este mismo documento: el wordmark estaba fijado en
minúscula —«glosa»— porque las mayúsculas de alarma son lo contrario del tono.
Queda escrito que se cambió, en vez de borrado.

Nunca «GLOSA-E» en versales. Eso sí sigue en pie.

**Lo que arrastra el «-e», dicho aquí y no en una nota al pie.** *Factura-e* es
el nombre del formato del Estado, y este documento descartó toda la familia
*veri-* precisamente por eso: por dar a entender que somos oficiales. *Glosa-e*
se construye igual que *Factura-e*. Se ha elegido con ese riesgo encima de la
mesa —dice a qué mundo pertenece la herramienta—, pero es el riesgo que este
documento decidió no correr en agosto. Si algún día llega una queja, vendrá por
aquí.

### La marca gráfica

Un bloque apaisado de plata, con el signo en blanco a la izquierda y el nombre
en negro a la derecha.

**La marca ya no hereda el color del sitio.** Se trae el suyo, y por eso se ve
igual sobre el papel claro y sobre el oscuro. Es lo contrario de lo que decía
la versión anterior —monocroma, con `currentColor`— y es a propósito: con el
nombre dentro del dibujo, el negro sobre el papel de noche daba **1,16:1**, que
no es que se leyera mal, es que no estaba.

El signo es el corchete al margen: lo que se pone, desde siempre, para señalar
el pasaje que se comenta. Abarca el texto entero y no toca una sola línea.

| Qué | Valor |
|---|---|
| Plata del bloque | `#949494` |
| Signo | blanco `#ffffff` |
| Nombre | negro `#000000` |
| Proporción | 2,85:1 |
| En la cabecera | ya no va: signo y nombre desde el 23-09-2026 (abajo) |

**Por qué esa plata y no la plata.** Se pidió `#C0C0C0`. Con ella el signo
blanco queda en **1,82:1** sobre su propio fondo, y el mínimo para que una
forma gráfica se distinga es 3:1. `#949494` es el gris más claro que llega
—**3,03:1**— y no perjudica al nombre, que se queda en **6,92:1** cuando el
texto pequeño pide 4,5:1. Medido con la fórmula de WCAG 2.1; las cifras salen
de un cálculo, no de mirarlo.

**La palabra va trazada, no como texto.** Desde que el nombre vive dentro del
dibujo, si viajara como `<text>` cada máquina lo compondría con la serif que
tuviera a mano —Iowan Old Style en un Mac, Palatino Linotype en Windows,
Georgia si no hay ninguna— y la marca cambiaría de forma sin que nadie la
tocara. Trazada, es la misma en todas partes.

**Está trazada de Literata, peso 400** (Google, 2017), bajo **SIL Open Font
License 1.1**.

**Y estuvo trazada de Palatino Linotype durante unas horas del 30 de agosto de
2026.** Se cambió el mismo día, y no por gusto: Palatino viene con Windows, no
es redistribuible, y su licencia no dice nada de llevar sus contornos dentro de
una marca. O sea que la marca colgaba de un permiso que nadie había mirado. La
OFL sí lo dice —*«permission… to use, study, copy, merge, embed, modify,
redistribute, and sell»*—, y sus dos condiciones que podrían morder aquí no
muerden: no vender la fuente suelta, y acompañar el fichero de su licencia si
se redistribuye. Una marca no lleva el fichero dentro, solo contornos. No es un
dictamen legal y sigo sin ser quien para darlo; la diferencia es que ahora hay
un texto que autoriza, y antes no había ninguno.

**Se eligió mirando las cuatro, y se eligió la que menos se nota.** La marca se
aprobó mirándola, así que el cambio de letra tenía que costar lo menos posible:
la palabra en Literata sale de **126,8** unidades de ancho contra las **124,9**
de Palatino sobre un bloque de 285, y la altura de la equis es **507/1000**
contra **519**. Las otras tres candidatas —Source Serif 4, EB Garamond y Libre
Baskerville, las tres OFL— quedaron descartadas por lo mismo al revés: EB
Garamond tiene la equis en 400/1000 y a 15 px se afina; Libre Baskerville sale
ancha y con aire de libro inglés. La geometría no se tocó en ninguna prueba
—bloque 2,85:1, signo al 62 %, mismo hueco, misma altura de tinta— para que lo
único que se estuviera comparando fuera la letra.

**Y la página ya se compone en la misma letra.** Esto decía que los titulares
salían con la serif que cada máquina tuviera a mano, y que coincidirían con la
marca el día que se sirviera Literata. Ese día llegó: `glosa.css` la sirve
desde el propio sitio, con el mismo `opsz` que la marca —el porqué, arriba de
la hoja—, y los titulares y la marca son hoy la misma letra.

**El favicon es el signo de la cabecera, desde el 25-09-2026.** A 16 px el
nombre no cabe de ninguna manera, así que la pestaña lleva el signo solo: los
mismos cuatro trazos, el mismo grosor y los mismos remates que `.marca::before`,
recortado a su tinta en un cuadrado para que a ese tamaño sea todo lo grande
que puede. Hasta ese día llevaba el cuadro plata con el signo en blanco y dos
líneas, y la cabecera y la pestaña eran dos marcas: lo vio el titular en una
captura de la pestaña. Y como una imagen no ve la hoja de estilo, lleva
escritos los dos `--acento`, cada uno con su `prefers-color-scheme` dentro del
propio dibujo: con uno solo, el azul de día se perdería en una barra de
pestañas de noche.

**En la zona de soltar va el signo solo**, heredando `--acento`. El signo es
lengua de la marca; el bloque plateado es la firma, y una firma puesta de
adorno dentro de la propia herramienta sobra.

**Y en la cabecera, desde el 23-09-2026, el signo y el nombre.** Hasta ese día
la cabecera llevaba el bloque entero, a 114 × 40 px, y a ese tamaño un
rectángulo gris en la esquina se lee como una imagen que no ha cargado: era lo
primero que se veía de la página. Salió del repaso de la portada contra las de
al lado —el porqué entero, en el README— y la decisión fue del titular,
porque cambiaba lo que este documento había fijado.

Lo que cambia es dónde va el bloque, no la marca. El bloque sigue siendo la
firma donde va suelto —`web/marca/glosa-e.svg`; el favicon también lo fue, hasta el 25-09-2026—, y en la cabecera la llevan el signo, pintado con `--acento`, y el
nombre en Literata 600, como texto. Como texto porque ya se puede: la razón
de trazarlo era que cada máquina lo compondría con la serif que tuviera, y
desde que la página sirve Literata eso ya no pasa. Y con los colores de la
hoja la cabecera cambia con el tema sin traerse un fondo propio, que es lo
que el bloque tuvo que hacer para leerse de noche.

| En la cabecera | Claro | Oscuro |
|---|---|---|
| Signo, `--acento` sobre `--papel` | `#1c4e80`, 8,21:1 | `#8ab4e0`, 8,35:1 |
| Nombre, `--tinta` sobre `--papel` | `#16181c`, 17,03:1 | `#e8eaee`, 15,04:1 |

**Dónde vive.** El bloque, en `web/marca/glosa-e.svg`. El signo de la
cabecera, una sola vez en `web/glosa.css` como máscara de `.marca::before`,
y es el mismo dibujo que el de la zona de soltar; las siete páginas solo
llevan el enlace, con el nombre dentro, y el favicon, que es una copia del
signo en cada una. Dos copias de un dibujo se acaban
separando, y una marca que dice una cosa en la portada y otra en el aviso
legal no se nota hasta que ya está publicada.

**La tarjeta social, desde el 24-09-2026, lleva la marca de la cabecera**, por
decisión del titular: es lo primero que se ve de la página antes de abrirla,
y tiene que ser la página. La que llevaba ni siquiera era el bloque: era el
dibujo del favicon —dos líneas y no tres, en blanco sobre la plata— con el
nombre fuera y en 400. `herramientas/tarjeta.py` copia las cifras de
`.marca` y `tests/test_tarjeta.py` las compara con la hoja.

**Y se regenera, no se redibuja.** `web/marca/trazar.py` vuelve a trazar el
bloque de la fuente. Hasta el 23-09-2026 escribía además su copia en la hoja
de estilo; ya no hay copia que escribir. Y `tests/test_marca.py` se pone rojo
si el bloque vuelve a la hoja —sería una copia que nadie regenera—, si el
signo de la cabecera deja de ser el de la zona o de pintarse con `--acento`,
si los siete favicons dejan de ser el mismo o de ser el signo de la cabecera
con sus dos acentos, o si la plata cambia y estas
cifras de contraste pasan a ser falsas. Cada una se ha provocado: sin verlas
rojas no valdrían nada.

## El tono, que ya estaba escrito

No es nuevo: es lo que llevan el informe y los mensajes de error desde el
principio. Queda aquí para que la página no se salga.

1. **Castellano llano.** Nada de «validación exitosa». Sale bien o no sale.
2. **Sin anglicismos** cuando hay palabra: informe, no *report*; ancla, no
   *trust anchor*; sello de tiempo, no *timestamp*.
3. **Nunca «válida» a secas.** Válida contra qué, y qué ha quedado fuera.
4. **La queja lleva el arreglo al lado.** Si un esquema no compila, se dice qué
   falta, no «vuelve a bajarlo» sobre un fichero que está entero.
5. **Lo que no se ha mirado se dice igual de alto que lo que se ha mirado.**
6. **Ninguna cifra sin poder enseñar de dónde sale.**
7. **Una sola voz, la del informe.** Impersonal: «se ha comprobado», «aquí no
   se sabe reproducir». La primera persona del singular, solo para el contacto
   —«Escríbeme», «dímelo y lo corrijo»—, porque quien contesta un correo es una
   persona. Nunca el plural: hasta el 15-09-2026 convivían «te decimos», «no
   nos gusta» y «Escríbenos» con «Escríbeme», y el informe decía «no sabemos»
   al lado de «solo se sabe». Lo vigila `tests/test_voz.py`.

## Lo que la marca no puede prometer nunca

- Que una factura es válida **a secas**, sin decir contra qué norma y con qué
  instalado.
- Que somos oficiales, de la AEAT, del FACe o de nadie.
- Que una firma es de fiar cuando la lista de confianza está sin renovar. Eso
  es un aviso, y sale.
- Conformidad con VeriFactu, que es otra cosa y no la hacemos.

## Estado de la marca a 30 de agosto de 2026

Comprobado por mí, y no es una búsqueda legal.

### La dirección: `glosa-e.com`

**La página se llama Glosa-e y su dirección es `glosa-e.com`.** Decidido el 30
de agosto de 2026 y **registrado el 31**, en Vercel. Sirve desde entonces, con
`www.glosa-e.com` como dirección canónica y el ápice redirigiendo con un 308.

Lo que sigue se midió el 28 y el 30 de agosto, *antes* de comprarlo, y se deja
tal cual: es lo que sostenía la decisión, y un porqué reescrito después de
acertar no vale nada.

Medido contra el **RDAP de Verisign**, que es el registro del `.com` y no un
revendedor con interés en que algo parezca libre:

| Dominio | RDAP | Qué hay |
|---|---|---|
| `glosa-e.com` | 404, sin cuerpo | **libre**, y sin servidores de nombres |
| `glosae.com` | 200 | registrado el 25-06-2026 en Name.com, apuntando a Vercel |
| `laglosa.com` | 200 | registrado el 22-08-2026 en Name.com, apuntando a Vercel |
| `glosa.com` | 200 | registrado el 27-07-1995, hoy en Dynadot y servido desde `namepros-dns.com` |
| `google.com` | 200 | el control |

El control no está de adorno. En la primera pasada el `curl` de un 404 dejaba
el fichero de la respuesta anterior sin tocar, así que un dominio libre
parecía devolver la ficha de `google.com`. Es el fallo de siempre de este
repositorio —algo viejo haciéndose pasar por lo de hoy— y por eso cada consulta
borra su fichero antes y se comprueba que el `ldhName` que vuelve es el que se
preguntó.

**El guion no es un adorno: es lo que deja el dominio libre.** `glosae.com`,
que es este mismo nombre sin guion, lo registró un tercero en junio de 2026 y
lo tiene servido desde Vercel, igual que este proyecto. Quien teclee el nombre
de memoria y se salte el guion acabará ahí. No impide nada —son dominios
distintos y la marca es *Glosa-e*, con guion, desde el 30 de agosto— pero
obliga a dos cosas: escribir siempre el guion, y no dar por hecho que el
vecino esté disponible el día que se quiera comprar como defensa.

**Y lo que hay en los vecinos está mirado, no supuesto.** `glosae.com` sirve
una aplicación de aprender idiomas y `laglosa.com` un sitio mexicano de
opinión política. Ninguno de los dos está en facturación, y eso convierte el
guion perdido en lo que es: una visita despistada, no una confusión de marca
dentro del propio mercado. Si algún día cambia lo que sirven, cambia el
tamaño del problema.

`laglosa.com` también es de un tercero y también está en Vercel. Se registró
el 22-08-2026, seis días antes del estudio anterior, que proponía justamente
salir con `laglosa.es`. Esa salida ya no existe.

`glosa.com` lleva registrado desde 1995 y hoy se sirve desde los servidores de
NamePros, que es el foro donde se compran y venden dominios: encaja con lo que
decía el estudio anterior —un inversor— y ahora está medido en vez de supuesto.

**El `.es` no se ha medido, y no se va a fingir que sí.** El whois del puerto
43 de `nic.es` solo atiende a direcciones IP autorizadas por Red.es, y no hay
RDAP público del `.es`. Lo único que se puede ver desde fuera es que
`glosa-e.es` y `glosae.es` no tienen servidores de nombres, y eso **no
significa libre**: un dominio registrado y sin delegar se ve exactamente
igual. Si alguna vez se quiere `glosa-e.es` como defensa, hay que mirarlo en
otro sitio.

### `glosa-electronica`, mirado y descartado el 30-08-2026

Se midió igual, contra el RDAP de Verisign, con `verisign.net` de control:

| Dominio | RDAP | Qué hay |
|---|---|---|
| `glosa-electronica.com` | 404, sin cuerpo | libre |
| `glosaelectronica.com` | 404, sin cuerpo | libre |
| `glosa-electronica.net` | 404, sin cuerpo | libre |
| `glosaelectronica.net` | 404, sin cuerpo | libre |

Las cuatro libres, que es más de lo que puede decir `glosa-e`: ahí el gemelo
sin guion ya está cogido. Aun así se descarta, por tres razones y en este
orden:

- **No es el nombre.** La marca dice *Glosa-e*, el bloque plateado dice
  *Glosa-e* y los títulos de las tres páginas dicen *Glosa-e*. Una dirección
  distinta del nombre obliga a explicarla cada vez que se dice en voz alta.
- **«Glosa electrónica» no existe.** Lo que existe es *factura* electrónica.
  La dirección se inventaría una categoría, y de paso empujaría justo donde
  este documento ya avisa: se leería todavía más como la web de un formato
  oficial que `glosa-e.com`. El riesgo que se aceptó a sabiendas subiría en
  vez de bajar.
- **El único argumento serio a favor se cayó al mirar.** Era la confusión con
  el vecino sin guion; el vecino resultó ser una aplicación de idiomas.

**Lo que sí valdría la pena, y no lo he hecho porque no compro dominios:**
registrar `glosa-electronica.com` y `glosaelectronica.com` y redirigirlos a
`glosa-e.com`. Hoy están libres las dos grafías, cuestan poco, atrapan a quien
busque el término en castellano y no obligan a nada. Es defensa barata, no un
cambio de dirección.

**Lo que se pierde al elegir `.com`.** Un `.es` diría «España» sin decirlo, y
esto valida facturas españolas contra normas españolas. Se ha elegido `.com`
sabiéndolo. Y se apila con el riesgo que ya estaba escrito arriba: *Factura-e*
es el nombre del formato del Estado, así que `glosa-e.com` se lee, de un
vistazo, como la web de un formato oficial. Es el mismo riesgo de siempre, en
la dirección esta vez.

### Lo demás, que sigue siendo de «Glosa» y no se ha vuelto a mirar

- **No hay ninguna empresa de software llamada Glosa en España.** Hay una
  *Glosa Ten S.L.* en Móstoles, de impresión de bolsas de plástico, y una
  *Editorial Glosa S.L.* en Barcelona, de libros. Actividades distintas y
  clases distintas de las nuestras (9 y 42). Comprobado el 28-08-2026 para
  «Glosa»; para «Glosa-e» no se ha repetido.

Falta, y no lo he hecho porque no me toca: la búsqueda de marca en la **OEPM**
y en **EUIPO** para las clases 9 y 42, y la reserva de **denominación social**
en el Registro Mercantil Central, que es un trámite distinto del de la marca y
va antes de la escritura.

## Lo que no se toca todavía

El repositorio sigue llamándose `Factura-e` y el paquete `validador`. No hay
prisa: la marca es la cara, no el módulo. Cuando la página esté hecha se
decide si el paquete pasa a llamarse `glosa` —tiene sentido para publicar en
PyPI— o se queda.

## Segundos y terceros, por si no convence

> Los dominios de esta sección se miraron el 28-08-2026 por sus servidores de nombres, que es la medición floja que se acaba de tirar arriba. Los nombres valen; el «libre» de cada uno, no.

- **Veedor.** El que mira por cuenta de otro; un oficio español de verdad
  (veedor de cuentas, de obras). Mira e informa, no certifica: mismo acierto de
  fondo que Glosa. Suena más antiguo, y `veedor.es` y `veedor.com` están
  cogidos; `elveedor.es` libre.
- **Que conste.** «Que conste» es lo que hace el informe: dejar constancia de
  lo mirado y de lo no mirado. Cálido, muy español, memorable. Suena algo
  defensivo y como frase no aguanta bien de razón social. `queconste.es` libre.
- **Testigo.** Doble sentido bueno: el que da fe de lo que vio, y la marca de
  yeso que se pone sobre una grieta para que un movimiento invisible se vea.
  Eso último es el proyecto entero —cazar lo que pasa en silencio—. Palabra
  demasiado común para buscarla en internet, y `testigo.es` está aparcado en
  venta.
