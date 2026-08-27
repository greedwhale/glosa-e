# El validador dentro del navegador

Esto no es la web del producto. Es la prueba de que el producto es posible:
comprueba que Factura-e funciona entero dentro de un navegador, sin servidor y
sin que la factura salga del ordenador de quien la mira.

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
python -m build --wheel --outdir dist
python -m http.server 8765
```

Y abrir <http://127.0.0.1:8765/web/>.

La página busca sola el `.whl` más reciente de `dist/`, así que no hay que
tocar nada al subir la versión en `pyproject.toml`.

**Hay que reconstruirlo cada vez que se toque `validador/`.** La página carga
el wheel, no la carpeta, así que un wheel viejo ejecuta código viejo. Y si
mientras tanto ha aparecido un módulo nuevo, ni siquiera arranca: `factura.py`
lo importa y el wheel no lo trae. Pasó al añadir `facturae.py` —la página
quedó rota sin que nada lo dijera, porque `dist/` no se versiona y los tests
corren contra la carpeta, no contra el paquete—.

Volvió a pasar al añadir `revocacion.py`, y por eso la comprobación «el paquete
validador importa» ya no lleva una lista de módulos escrita a mano: **recorre
el paquete instalado y los importa todos**, y dice cuántos y cuáles. Con la
lista a mano, un wheel viejo salía en verde y el fallo aparecía tres pruebas
más abajo disfrazado de otra cosa. Ahora sale ahí y dice qué falta. La página,
además, le añade un `?v=` a la URL del wheel: el nombre no cambia entre
compilaciones de la misma versión, y sin eso el navegador puede servir el de su
caché —todo verde, y no es lo que crees que has probado—.

## Qué mirar

Arriba, el tiempo de arranque. Abajo, veintiocho comprobaciones que deben
salir todas en verde; diecinueve están marcadas como **críticas** y son las
que, si fallan, tumban la idea entera:

| Comprobación | Por qué es crítica |
|---|---|
| lxml carga en WebAssembly | sin esto no hay nada |
| libxml2 trae soporte de esquemas XSD | de ello depende `esquema.py` |
| el paquete validador importa | el wheel se instala de verdad |
| el parser endurecido no expande entidades | una factura ajena no debe poder leer ficheros |
| una factura correcta sale conforme | sin falsos positivos |
| una factura rota se caza | sin falsos negativos |
| lxml canonicaliza igual que fuera | de ello depende `firma.py` entero |
| se verifica una firma RSA de verdad | sin `cryptography`, que aquí no hay |
| se verifica una firma de curva elíptica | un tercio de las autoridades españolas firma así |
| las curvas son las de verdad, también aquí | una errata en un parámetro no da error: da «no verifica» |
| la cadena de confianza se encadena aquí | de ello depende `cadena.py` |
| una lista de revocación se lee y se comprueba aquí | de ello depende `revocacion.py` |
| el informe declara de dónde salen las anclas | es la condición para traerlas puestas |
| una lista de confianza se comprueba y se monta aquí | de ello depende `tsl.py`, y con él de dónde salen las anclas |
| una lista de confianza manipulada no monta nada | un almacén mal montado no da un error: da un aprobado |
| una autoridad retirada solo vale para lo de antes | si la ventana no se aplica, 135 autoridades caducadas pasan a ser de confianza |
| un sello de tiempo se lee y se comprueba aquí | de la fecha del sello cuelgan la caducidad y la revocación |
| un sello sin permiso para sellar no vale | su firma es válida: lo único que falla es el permiso, y eso no salta solo |
| las anclas de sellado van aparte de las de firma | juntas, once autoridades pasarían a avalar firmas de facturas |

Las nueve últimas son de la firma, y la de la canonicalización es la que más podía
doler. `firma.py` calcula el resumen de un documento canonicalizado y lo compara
con el que guarda la firma. Si lxml en WebAssembly escribiera un solo byte
distinto —un atributo en otro orden, un namespace colocado de otra manera— el
resumen saldría distinto y **todas las facturas firmadas se denunciarían como
manipuladas dentro del navegador y solo dentro del navegador**. El valor
esperado está medido fuera, con CPython.

Al final hay una zona donde soltar una factura de verdad. Esa parte es
exactamente la interacción del producto: leer el fichero en el navegador,
validarlo ahí y enseñar el informe. La red no se toca.

## Resultados medidos

En Chrome, sobre esta máquina, con Pyodide 314.0.6:

| | |
|---|---|
| lxml / libxml2 | 6.0.2 / **2.9.10** |
| Arranque en frío del todo (primera visita) | ~42 s |
| Arranque con la CDN ya cacheada | 11,25 s |
| Arranque con la caché ya caliente | ~4,8 s |
| Validar una factura | 5–120 ms |
| Validar las siete de `ejemplos/` | 241 ms |
| Verificar una firma XAdES | 17 ms |
| Encadenar hasta un ancla de confianza | 3,2 ms |
| Leer y verificar una lista de revocación | 4,8 ms |
| Declarar el ancla en el informe | 1,5 ms |
| Verificar una firma ECDSA (P-256 / P-384 / P-521) | 10 / 16 / 29 ms |
| Verificar una lista de confianza y montar el ancla | 20,8 ms |
| Rechazar una lista de confianza manipulada | 14,1 ms |
| Validar un lote de 200 | 2,05 s · 10,3 ms cada una · 23 MB de memoria |
| Lo que descomprime el navegador | 14,71 MB |

Cuidado con los tiempos de arranque, que son tres cosas distintas: la primera
visita de verdad baja los 14,71 MB; con la CDN cacheada solo se pagan los
11,25 s de montar el intérprete —en la última medición se transfirieron
0,13 MB, todo lo demás salió de la caché—; y con la página ya visitada son
menos de cinco.

Los veintiocho resultados coinciden exactamente con los de la misma prueba
ejecutada con Python nativo: mismos códigos, mismos resúmenes, mismos importes.
Es la comprobación que de verdad importa, porque libxml2 aquí es **2.9.10** y
en local es 2.11.9. Dos versiones distintas que dicen lo mismo, **canonicalización
incluida**.

Eso último dejó de ser una curiosidad al entrar la lista de confianza: una TSL
se verifica canonicalizándola, así que un byte de diferencia entre las dos
compilaciones no daría un falso aprobado —daría una lista rechazada y una
página sin anclas—. Verificar y montar cuesta 20,8 ms allí.

## La prueba de soltar una factura firmada

No basta con que las veinte salgan verdes: la zona de arrastre es la
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

- **Los 14,7 MB del primer arranque.** Se pueden bajar: hay una compilación de
  Pyodide sin la biblioteca estándar completa, y el `.whl` de lxml es fijo y
  cacheable. Pero la primera visita nunca va a ser instantánea, y la página
  tiene que decirlo en vez de parecer rota.
- **Los esquemas XSD oficiales.** No están en el repositorio y aquí tampoco:
  la prueba los da por ausentes y comprueba que eso no revienta nada. Con ellos
  habría que bajar unos megas más.
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
  de contarlo—. Lo que falta es operativo: cada cuánto se vuelve a montar, y
  que la página enseñe de cuándo es el que trae.

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
