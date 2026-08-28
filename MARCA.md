# La marca

**Glosa.**

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

> **Glosa — lo que dice tu factura, y lo que no se ha podido mirar.**

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

Wordmark en minúscula: **glosa**. Sin punto, sin eslogan pegado, sin tilde
—no la lleva—. En texto corrido, mayúscula inicial: Glosa.

Nunca «GLOSA» en versales: las mayúsculas de alarma son lo contrario del tono.

### La marca gráfica

La nota en el margen. Un bloque de texto y, fuera de él, a su izquierda, una
sola marca corta. Monocromo, sin relleno, legible a 16 px.

```svg
<svg viewBox="0 0 48 40" xmlns="http://www.w3.org/2000/svg"
     fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round">
  <path d="M2 20 h6"/>
  <path d="M18 10 h28"/>
  <path d="M18 20 h28"/>
  <path d="M18 30 h18"/>
</svg>
```

Lo que dice el dibujo: el documento es del que lo emite y no se toca. Lo
nuestro es lo de fuera, al lado.

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

## Lo que la marca no puede prometer nunca

- Que una factura es válida **a secas**, sin decir contra qué norma y con qué
  instalado.
- Que somos oficiales, de la AEAT, del FACe o de nadie.
- Que una firma es de fiar cuando la lista de confianza está sin renovar. Eso
  es un aviso, y sale.
- Conformidad con VeriFactu, que es otra cosa y no la hacemos.

## Estado de la marca a 28 de agosto de 2026

Comprobado por mí, y no es una búsqueda legal:

- **No hay ninguna empresa de software llamada Glosa en España.** Hay una
  *Glosa Ten S.L.* en Móstoles, de impresión de bolsas de plástico, y una
  *Editorial Glosa S.L.* en Barcelona, de libros. Actividades distintas y
  clases distintas de las nuestras (9 y 42).
- **Dominios**, mirando los NS el 28-08-2026:

  | Dominio | Estado |
  |---|---|
  | `laglosa.es` | libre |
  | `glosade.es` | libre |
  | `glosa.es` | registrado, sin web (hosting español) |
  | `glosa.com` | registrado por un inversor de dominios |
  | `glosa.app` | aparcado en Afternic, o sea en venta |
  | `glosa.dev` | registrado |

  Camino práctico: salir con **`laglosa.es`**, que además se dice bien en
  castellano —«La Glosa»—, y dejar `glosa.es` o `glosa.com` como compra
  posterior si el negocio lo justifica. La marca es *Glosa*; el dominio es una
  dirección.

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
