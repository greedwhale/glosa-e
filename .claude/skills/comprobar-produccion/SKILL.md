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

Sitio: <https://glosa-dhm7.vercel.app>

## 1. Que el despliegue nuevo esté arriba

El manifiesto es lo único que se sirve siempre fresco, así que es lo que dice
si ya está lo de ahora:

```bash
curl -s https://glosa-dhm7.vercel.app/dist/rueda.json | head -5
```

El wheel viaja bajo una carpeta con su huella (`c628aa92/factura_e-…whl`) y esa
huella **cambia en cada construcción** —los wheels no son reproducibles byte a
byte—, así que sirve para saber si el despliegue es el nuevo.

## 2. Las cabeceras de caché

Nueve reglas en `vercel.json`. Lo que se guarda un año y lo que no:

```bash
u=https://glosa-dhm7.vercel.app
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
  ajenos: [...new Set(r.map(x=>new URL(x.name).origin))].filter(o=>o!==location.origin)})
```

**`ajenos` tiene que ser `[]`.** No es cosmética: la política de privacidad
publica una tabla medida que dice «0 dominios de terceros», y `pyodide.js`
lleva dentro la dirección del CDN como respaldo. Es exactamente lo que hay que
mirar y no suponer.

Referencia medida (30 ago 2026): en frío 23 peticiones y ~9.175 KB; en caliente
1 KB con 21 de 22 de caché y «Listo en 5,31 s».

## 4. Que el veredicto siga siendo el mismo

```js
const b = await (await fetch("/ejemplos/fe-0001.xml")).blob();
const d = await window.Glosa.validar([new File([b], "fe-0001.xml")]);
const inc = d.documentos.flatMap(x => x.incidencias || []);
const p = window.Glosa.paquete;
({conforme: d.conforme, gravedades: inc.map(i=>i.gravedad), alcance: !!d.alcance,
  esquemas: p.esquemas, anclas: p.anclas, sellos: p.anclas_de_sellos, publicada: p.publicada})
```

**Lo esperado:** `conforme: true`, gravedades `["nota","aviso","aviso"]`, 24
esquemas, 268 anclas de firma, 121 de sellado. Si el número de anclas ha
cambiado sin que nadie haya montado el paquete, algo va mal.

## 5. El banco, en producción

En `/banco`, con el arranque terminado:

```js
const res = await window.Glosa.correrBanco();
const c = res.comprobaciones || res;
({comprobaciones: c.length, fallan: c.filter(x=>!x.ok).length,
  criticas_que_fallan: c.filter(x=>x.critica && !x.ok).map(x=>x.nombre)})
```

El campo es **`ok`**, no `pasa`. Esperado: 37 comprobaciones, 0 fallan.

## 6. La ficha del titular sigue oculta

En `/legal`, mientras `TITULAR` esté vacío en `glosa.js`, la ficha de
identificación no puede aparecer —y la sección comercial de la portada tampoco—.
Las dos están atadas al mismo `puedeVender()` a propósito: no se ofrece un
servicio de pago sin decir quién lo ofrece.

## Al terminar

Di qué salió y qué no, con los números. Si algo no cuadra, **no lo arregles sin
reproducirlo antes**: es la regla de la casa y esta comprobación existe
precisamente para que los fallos se vean, no para que se tapen.
