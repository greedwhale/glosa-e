# Factura-e

Validador de facturas electrónicas españolas (EN 16931, RD 238/2026, Facturae,
UBL, CII, EDIFACT) con los errores explicados en castellano. Corre en consola y
dentro del navegador, sobre Pyodide, con la marca **Glosa**.

El detalle está en cuatro documentos y este fichero no los repite:

| Dónde | Qué hay |
|---|---|
| `README.md` | las reglas, de dónde salen y qué se decidió en cada una |
| `HALLAZGOS.md` | los fallos encontrados, cómo se reprodujeron y qué los cerró |
| `MARCA.md` | el nombre, qué promete y qué no puede prometer nunca |
| `web/LEEME.md` | el validador dentro del navegador, y lo medido |

---

## Lo que no se toca

- **`../Proyecto 1/` no es de este proyecto.** Es del usuario y lo lleva
  él. No escribir ahí.
- **Nunca se versionan** `anclas/`, `anclas-*/`, `revocaciones/`, `listas/`
  (material de confianza: caduca, y repartir una foto vieja es peor que no
  repartir nada) ni `muestras/`, `MuestrasFE/`, `Pfactura3/` (facturas de
  terceros). Tampoco `vendor/` ni `sitio/`, que se construyen.
- **La excepción, decidida a propósito:** `web/paquete.zip` y
  `web/PAQUETE.json` **sí** se versionan, con su SHA-256 publicado al lado.
  Es lo que hace que el sitio se pueda construir sin tener las carpetas fuente.
- **Nunca pedir ni manejar tokens, contraseñas ni claves.** GitHub y Vercel los
  autentica el usuario en su navegador. No se piden, no se reciben, no se
  escriben.

## Cómo se trabaja aquí

**Todo en castellano**: comentarios, documentación, mensajes de commit,
nombres de funciones y variables. Los comentarios explican **por qué**, no qué,
y pueden ser largos: son la mitad del valor del repositorio.

**Se mide, no se supone.** Ninguna afirmación sobre rendimiento, red o
comportamiento entra sin el número que la sostiene. Si no está medido, se dice
que no está medido.

**Todo fallo se reproduce antes de arreglarlo, y todo arreglo se prueba
rompiéndolo.** Quitar el `.wasm` y ver el `exit 2`; apuntar el manifiesto a un
wheel inexistente y ver la página fallar. Un arreglo que solo se ha visto
funcionar no se ha visto.

**Negarse vale más que acordarse.** Cuando algo puede romperse en silencio, la
solución es que **no se pueda montar** sin enterarse: `SinRueda`, `SinPagina`,
`SinPyodide`, y la negativa cuando `glosa.js` y `paquete.py` declaran versiones
distintas de Pyodide. Es el patrón de este proyecto; úsalo antes que un
comentario que pida memoria.

**Las versiones se fijan y no se siguen a `latest`.** Pyodide 314.0.6, lxml
6.0.2. Lo que se prueba es una combinación concreta; si se mueve sola, el día
que algo se rompa no se sabrá qué cambió.

**No prometer de más.** Es la tesis del producto y la razón del nombre —una
glosa explica, no certifica—. Ni el informe, ni la página, ni la política de
privacidad afirman nada que no se haya comprobado. Las tres gravedades son
`ERROR`, `AVISO` y `NOTA`, y NOTA existe para decir *qué se aceptó y con qué
base*.

## El fallo que se repite

Cuatro veces ha pasado lo mismo con distinto disfraz: **algo servido de una
caché haciéndose pasar por lo de hoy**. Un wheel viejo, un `prueba.py` viejo,
una comprobación incapaz de detectar el wheel viejo, un `index.html` viejo.
Nunca se rompe nada: sale todo verde y no es lo que crees que has probado.

Ante cualquier cosa que se sirva al navegador, la pregunta es *cómo se entera
de que cambió*. La respuesta de este repositorio es la huella del contenido:
`?v=<sha256[:8]>` para lo normal, y **en la ruta** cuando quien la consume no
admite query (`dist/<huella>/x.whl`, porque `loadPackage` rechaza cualquier cosa
detrás del `.whl`).

## Detalles operativos

- **La carpeta de trabajo es la padre**, `C:\Users\PC\Claude`. Los enlaces
  markdown se resuelven desde ahí: se escriben `Factura-e/web/legal.html`, no
  `web/legal.html`.
- **Hay venv y hace falta**: lxml no está en el Python del sistema.
  ```
  ./.venv/Scripts/python.exe -m pytest -q
  ```
- **Los parches se escriben a un fichero y se ejecutan**, no en un heredoc. Un
  `\\n` dentro de `<<'FIN'` se convirtió en un salto real y produjo un
  `SyntaxError` en un fichero de 400 líneas. Usa `Write` y luego `python
  el_parche.py`.
- **El sitio se monta, no se sube el repositorio**:
  ```
  ./.venv/Scripts/python.exe -m validador --traer-pyodide   # una vez
  ./.venv/Scripts/python.exe -m validador --sitio sitio
  ```
- **Un push a `main` despliega a producción** (Vercel lee `vercel.json`).
  Publicado en <https://glosa-dhm7.vercel.app>. No hay dominio propio todavía.

## Lo que está sin decidir

Los datos del titular (`TITULAR` en `web/glosa.js`) están vacíos **a
propósito**: mientras no haya actividad económica, el artículo 10 de la LSSI no
obliga a identificarse. Rellenarlos enciende a la vez el aviso legal y la
sección comercial, y no hay forma de encender lo uno sin lo otro. Eso no es un
descuido: es el diseño.
