---
name: comprobar-produccion
description: Comprueba el sitio publicado de Glosa después de un despliegue — que arranca, que valida bien, que el banco pasa entero, que las cabeceras de caché están puestas y que no se habla con ningún dominio ajeno. Úsala tras cada push a main.
disable-model-invocation: true
---

# Comprobar el sitio publicado

Esto es el ritual de después de desplegar, escrito para no tener que acordarse
de las siete cosas que hay que mirar. **Se comprueba contra producción, no
contra local**, porque lo que se rompe al publicar es justo lo que en local no
se ve: las cabeceras que pone Vercel, las rutas reales y lo que el navegador de
un desconocido pide de verdad.

Sitio: **<https://www.glosa-e.com>**, que es el dominio canónico desde el
31-08-2026 —el ápice redirige a él con un 308—. <https://glosa-dhm7.vercel.app>
sigue sirviendo el mismo despliegue, pero lo que hay que comprobar es lo que
visita la gente: las cabeceras y las redirecciones son del dominio, no del
despliegue.

## 1. Que el despliegue nuevo esté arriba

El manifiesto es lo único que se sirve siempre fresco, así que es lo que dice
si ya está lo de ahora:

```bash
curl -s https://www.glosa-e.com/dist/rueda.json | head -5
```

El wheel viaja bajo una carpeta con su huella (`c628aa92/factura_e-…whl`) y esa
huella **cambia en cada construcción** —los wheels no son reproducibles byte a
byte—, así que sirve para saber si el despliegue es el nuevo.

## 2. Las cabeceras de caché

Nueve reglas en `vercel.json`. Lo que se guarda un año y lo que no:

```bash
u=https://www.glosa-e.com
for f in /pyodide/314.0.6/pyodide.asm.wasm /paquete.zip /ejemplos/fe-0001.xml /glosa.js /glosa.css /prueba.py /PAQUETE.json /dist/rueda.json /; do
  printf "  %-42s %s\n" "$f" "$(curl -sI "$u$f" | grep -i '^cache-control' | tr -d '\r' | sed 's/[Cc]ache-[Cc]ontrol: //')"
done
```

**Lo que tiene que salir:** `immutable, max-age=31536000` en todo menos en
`/dist/rueda.json` y `/`, que llevan `max-age=0, must-revalidate`. Si el
manifiesto o la portada salieran `immutable`, el sitio quedaría congelado para
quien ya lo haya visitado y no habría forma de avisarle.

## 3. Que arranque, valide y no hable con nadie

Con el panel del navegador, sobre la página publicada. Espera al arranque y
mide:

```js
const t0=performance.now();
while(!document.getElementById('arranque').classList.contains('listo') && performance.now()-t0<180000){
  await new Promise(r=>setTimeout(r,200));
}
const r=performance.getEntriesByType('resource');
({total: document.getElementById('arranque-titulo').textContent,
  fases: [...document.querySelectorAll('#fases .hecha')].map(e=>e.textContent),
  kb: Math.round(r.reduce((a,x)=>a+(x.transferSize||0),0)/1024),
  desde_cache: r.filter(x=>x.transferSize===0).length,
  peticiones: r.length,
  // Los `data:` y `blob:` se descuentan a proposito: no son de nadie -no
  // salen del navegador- y `new URL('data:…').origin` devuelve la cadena
  // "null", que aqui se leia como un dominio ajeno.
  ajenos: [...new Set(r.map(x=>new URL(x.name).origin))]
            .filter(o=>o!==location.origin && o!=='null')})
```

**`ajenos` tiene que ser `[]`.** No es cosmética: la política de privacidad
publica una tabla medida que dice «0 dominios de terceros», y `pyodide.js`
lleva dentro la dirección del CDN como respaldo. Es exactamente lo que hay que
mirar y no suponer.

Desde el 06-09-2026 esto **ya no depende de que alguien se acuerde**: el banco
trae «esta página no le pide nada a nadie», que mide lo mismo desde dentro y
en cada visita, y la suite trae `tests/test_sin_terceros.py`, que lo mira
antes de publicar. Lo de aquí sigue valiendo igual, porque es la única medida
que se hace sobre la página real con un navegador de verdad y con la caché en
el estado en que esté.

El filtro del `"null"` se añadió el 06-09-2026, y hace falta: en frío salía
`[]` y en caliente salía `["null"]`, que es un `data:image/svg+xml` en línea
del CSS —cero bytes, ninguna red—. Una comprobación de privacidad que da la
alarma cuando no pasa nada se deja de leer, y entonces no avisa el día que
pase. Si alguna vez sale algo aquí, mira `r.filter(...)` con la URL entera
antes de dar nada por bueno **o por malo**.

Referencia medida (30 ago 2026): en frío 23 peticiones y ~9.175 KB; en caliente
1 KB con 21 de 22 de caché y «Listo en 5,31 s». Vuelto a medir en frío el
**21-09-2026**: 24 peticiones, 9.681 KB, `ajenos: []` y «Listo en 66,52 s». El
tiempo no se compara con los 5,31 s, que son de caliente: para el frío no hay
referencia de tiempo, y por eso lo que se mira aquí son las peticiones, los
bytes y los ajenos.

## 4. Que el veredicto siga siendo el mismo

```js
const b = await (await fetch("/ejemplos/fe-0001.xml")).blob();
const d = await window.Glosa.validar([new File([b], "fe-0001.xml")]);
const inc = d.documentos.flatMap(x => x.incidencias || []);
const p = window.Glosa.paquete;
({conforme: d.conforme, alcance: !!d.alcance,
  incidencias: inc.map(i => i.codigo + " · " + i.gravedad),
  esquemas: p.esquemas, anclas: p.anclas, sellos: p.anclas_de_sellos, publicada: p.publicada})
```

**Lo esperado** (medido el 21-09-2026 sobre `www.glosa-e.com`):
`conforme: true`, **42 esquemas**, 268 anclas de firma, 121 de sellado, y estas
**ocho** incidencias:

```
FIRMA-DEBIL · aviso
CADENA-DESCONOCIDA · aviso
BR-01 · nota
BR-14 · nota
BR-21 · nota
COPIA-SERIE · nota
COPIA-SIN-SITIO · nota
SELLO-FALTA · nota
```

La cifra de esquemas sale de `web/PAQUETE.json` y la lista de códigos de
`tests/test_ejemplos.py`: **si no cuadran, la que manda es la del repositorio**,
y lo que hay que mirar es cuál de las dos se quedó atrás.

El código va al lado de la gravedad **a propósito**. Antes aquí ponía
`["nota","aviso","aviso"]` a secas y se quedó atrás: las tres incidencias
seguían siendo exactamente las mismas y lo único que cambió fue el orden, pero
con tres palabras sueltas eso no se distingue de una incidencia que ha
desaparecido —y quien corre esto se queda sin saber si mirar o seguir—. Con el
código delante, un cambio se lee de un vistazo. Y sirvió: el 06-09-2026
aparecieron tres notas nuevas y se supo en el acto que no había desaparecido
ninguna.

**Ninguna de las seis notas es un defecto de la factura**, y conviene saber
de dónde viene cada una, porque son tres grupos distintos:

- `BR-01`, `BR-14` y `BR-21` son **del binding de Facturae**, que entró el
  06-09-2026: los sitios donde esa sintaxis no tiene dónde escribir lo que la
  norma pide —`BT-24`, el identificador de especificación; el `BT-14`; y
  `BT-126`, el identificador de línea, que no existe, así que la regla no se
  puede comprobar y se dice—.
- `COPIA-SERIE` y `COPIA-SIN-SITIO` son **de la tabla de la copia fiel**
  (20 y 21-09-2026): este ejemplo lleva serie —«FE» y «0001», que en la copia
  son un solo campo— e idioma, que en la copia no tiene dónde ir.
- `SELLO-FALTA` es de siempre.

**`IVA-CATEGORIA-SIN-MAPA` ya no sale**, y no es una nota perdida: desde que la
categoría se deduce del `TaxTypeCode` y del tipo, esta factura va a `S` al 21 %
y las `BR-S-*` corren de verdad sobre ella. Un código que desaparece porque
ahora se sabe la respuesta es lo contrario de un hueco.

Salen como NOTA porque NOTA es la gravedad que existe aquí para decir qué se
aceptó y con qué base.

Si el número de anclas ha cambiado sin que nadie haya montado el paquete, algo
va mal.

## 5. El banco, en producción

En `/banco`. **Esa página no tiene `#arranque`** —lleva `#veredicto`, `#fases`,
`#trae` y `#tabla`—, así que el bucle de espera del punto 3 revienta aquí con
un `Cannot read properties of null`.

Y esperar a que exista `window.Glosa.correrBanco` **tampoco vale**, aunque lo
parezca: la función está puesta desde el primer momento y el intérprete no,
así que se llama antes de tiempo y revienta con `Cannot read properties of
null (reading 'runPythonAsync')`. Es el mismo error con otro disfraz —creer
que algo está listo porque se le puede nombrar—. Lo que dice de verdad si ya
se puede es **`#veredicto`, que arranca con la clase `esperando` y la pierde**
cuando el banco está montado (pasa a `veredicto si`). Medido: 6,3 s.

```js
const v = document.getElementById('veredicto');
const t0=performance.now();
while(v.classList.contains('esperando') && performance.now()-t0<180000){
  await new Promise(r=>setTimeout(r,300));
}
const res = await window.Glosa.correrBanco();
const c = res.comprobaciones || res;
({comprobaciones: c.length, fallan: c.filter(x=>!x.ok).length,
  criticas_que_fallan: c.filter(x=>x.critica && !x.ok).map(x=>x.nombre),
  detalle: c.filter(x=>!x.ok).map(x=>x.nombre + ' :: ' + (x.detalle||''))})
```

El campo es **`ok`**, no `pasa`. Esperado: **42 comprobaciones, 0 fallan**
(medido el 21-09-2026; `web/prueba.py` trae 42 `@comprobar`).

Esa cifra sube cada vez que entra una comprobación al banco, así que **la que
manda es la de `web/prueba.py`**: si no cuadra con la de aquí, mira primero cuál
de las dos se ha quedado atrás antes de dar nada por roto.

`detalle` va en la consulta desde el 06-09-2026 y no es adorno. Ese día
salieron tres críticas en rojo y sin el detalle no se sabía por qué; con él, la
primera línea ya decía `[BR-22] Cada línea debe decir cuántas unidades se
facturan`, que es el diagnóstico entero.

**Desde el 06-09-2026 el banco corre también en la suite**, en
`tests/test_banco.py`, con CPython y los ejemplos del repositorio. Eso no
sustituye a esto: allí el lxml es el del sistema y aquí es una compilación de
libxml2 para WebAssembly, y medio banco existe justo para comprobar que esa
compilación trae lo que hace falta. Lo que cambia es que **un ejemplo roto ya
no llega hasta aquí**: se cae en `pytest`, en tres segundos, en vez de en
producción. Que hiciera falta lo demostró ese mismo día —se desplegó dos veces
con tres críticas en rojo y la suite en verde—.

## 6. La ficha dice quién está detrás, y la tienda sigue apagada

Desde el 31-08-2026 son **dos puertas y no una**, así que aquí se miran dos
cosas distintas:

```js
({identificacion: window.Glosa.hayIdentificacion(),
  puedeVender: window.Glosa.puedeVender(),
  correo: window.Glosa.titular.correo,
  nif: window.Glosa.titular.nif, domicilio: window.Glosa.titular.domicilio})
```

**Lo esperado hoy:** `identificacion: true`, `puedeVender: false`, el correo
puesto, y NIF y domicilio vacíos. En `/legal` tiene que salir la ficha con el
titular y el correo —y el responsable del tratamiento, arriba en privacidad—,
sin filas de NIF ni de domicilio. En la portada, `#escalon` **oculto**.

Que la tienda cuelgue de `puedeVender()` es lo que no puede aflojarse: el
artículo 10 de la LSSI pide la ficha entera antes de cobrar. Si algún día
`puedeVender()` saliera `true` sin NIF y sin domicilio, eso sí es un fallo.
Aquí se mira; que no pueda ocurrir lo guardan dos pruebas de
`tests/test_documentacion.py`.

## Al terminar

Di qué salió y qué no, con los números. Si algo no cuadra, **no lo arregles sin
reproducirlo antes**: es la regla de la casa y esta comprobación existe
precisamente para que los fallos se vean, no para que se tapen.
