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
`SinPyodide`, `RuedaVieja` —el `.whl` de `dist/` comparado con el paquete
byte a byte **y también por su licencia**, porque `--sitio` no lo construye—, y
la negativa cuando `glosa.js` y `paquete.py` declaran versiones
distintas de Pyodide. Es el patrón de este proyecto; úsalo antes que un
comentario que pida memoria.

**El código es AGPL-3.0-only.** Desde el 01-09-2026; antes era MIT. El motor
entero viaja al navegador de quien abre la página, en claro, dentro del `.whl`:
con MIT eso era regalar el producto con permiso para cerrarlo. La AGPL no
impide llevárselo, impide cerrarlo —artículo 13, el caso del servicio web—. Va
en tres sitios que tienen que decir lo mismo, y hay guardián para cada salto:
`pyproject.toml`, el fichero `LICENSE`, y el `dist-info` de la rueda. El porqué
entero está en el README.

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

## Los ganchos, y por qué el cableado no viaja con ellos

Hay dos, los dos `PreToolUse`, los dos bloquean con **código 2**:

| Gancho | Dispara con | Hace |
|---|---|---|
| `.claude/hooks/antes-de-empujar.py`, versionado | `Bash`, `PowerShell` | ante un `git push`, corre la suite antes y no deja publicar en rojo (36 s medidos el 2026-08-30; `--dry-run` se aparta, que no publica). **Y no deja publicar tampoco cuando no puede comprobar**: la suite colgada, el intérprete que no arranca o una entrada que no se deja leer salen con 2, no con 1. Hasta el 06-09-2026 salían con 1 y el push pasaba *después* de que el gancho fallara |
| `.claude/hooks/guardian-de-rutas.py` de la **carpeta de trabajo**, fuera del repositorio | `Write`, `Edit`, `NotebookEdit` | se niega a escribir en lo que no se toca, y solo dentro de `C:\Users\PC\Claude\`, para no estorbar en otros proyectos de la máquina |

**Se declaran en los ajustes de usuario**, `C:\Users\PC\.claude\settings.json`,
no en los del proyecto. La razón está medida: con la declaración en
`C:\Users\PC\Claude\.claude\settings.json` —la carpeta de trabajo—, una
sesión arrancada en `Factura-e` no los cargaba y los dos dejaban pasar todo.
Los ajustes de proyecto se leen de la raíz de la sesión, no de sus ancestros;
los de usuario se leen siempre.

**El script viaja con el repositorio; la declaración no.** En una máquina nueva
`antes-de-empujar.py` está ahí y la puerta no existe: no falla, no avisa, y el
push publica igual. Es el disfraz de siempre —sale todo verde y no es lo que
crees que has probado—, así que **la única comprobación que vale es
provocarlos**, no leer el `settings.json` ni fiarse de que el fichero exista:

```
git push remoto-que-no-existe main   # con gancho tarda ~36 s; sin él, uno
```

y un `Write` a `sitio/loquesea` tiene que salir bloqueado. El panel de `/hooks`
solo existe en la terminal interactiva, y allí tampoco prueba que corran:
prueba que están escritos.

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
  La dirección es **`glosa-e.com`**, registrada en Vercel el 31-08-2026. El
  dominio canónico es **`www.glosa-e.com`** y el ápice redirige a él con un
  308; <https://glosa-dhm7.vercel.app> sigue sirviendo lo mismo. El porqué del
  nombre y los vecinos, en `MARCA.md`.

## Las dos puertas de la ficha del titular

`TITULAR` en `web/glosa.js` ya no está vacío: lleva **nombre comercial y
correo**, y nada más. De ahí salen dos puertas distintas, y la diferencia es lo
que hay que respetar al tocarlo:

| Puerta | Pide | Enciende |
|---|---|---|
| `hayIdentificacion()` | nombre y correo | la ficha del aviso legal y el responsable del tratamiento |
| `puedeVender()` | además, NIF y domicilio | la sección comercial de la portada |

**La tienda cuelga de la segunda y tiene que seguir colgando de ella**: el
artículo 10 de la LSSI pide la ficha entera *antes de cobrar*, no antes de
existir. Antes las dos cosas colgaban de la misma puerta y obligaban a elegir
mal —o no decir quién está detrás, o encender la tienda para poder decirlo—.
Lo guardan dos pruebas en `tests/test_documentacion.py`, las dos provocadas.

No se publican NIF ni domicilio **a propósito**: mientras no haya actividad
económica no hacen falta, y lo que se publica no se despublica.
