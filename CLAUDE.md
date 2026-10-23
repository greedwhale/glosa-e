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
- **`informes/` tampoco se versiona**: guarda los informes y planes para el
  titular, y no son para publicar. **Léelo antes de proponer nada
  comercial.** El plan en curso y la N de Search Console están en
  `informes/LEEME.md`.
- **La excepción, decidida a propósito:** `web/paquete.zip` y
  `web/PAQUETE.json` **sí** se versionan, con su SHA-256 publicado al lado.
  Es lo que hace que el sitio se pueda construir sin tener las carpetas fuente.
- **Nunca pedir ni manejar tokens, contraseñas ni claves.** GitHub y Vercel los
  autentica el usuario en su navegador. No se piden, no se reciben, no se
  escriben. **La de IndexNow no es de estas**, y está en
  `paquete.CLAVE_DE_INDEXNOW` a propósito: el protocolo la publica en la raíz
  del sitio, no abre nada y solo sirve para avisar de páginas de este dominio.
  Lo decidió el titular el 23-10-2026; el porqué, en el README.

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
byte a byte **y también por su licencia**, porque `--sitio` no lo construye—,
`PyodideQueNoCuadra` —lo que se baja contra las huellas fijadas en
`HUELLAS_DE_PYODIDE`— y la negativa cuando `glosa.js` y `paquete.py` declaran
versiones distintas de Pyodide. Es el patrón de este proyecto; úsalo antes que
un comentario que pida memoria.

Todas cuelgan de **`paquete.NoSeMonta`**, y `__main__` caza esa clase, no una
lista escrita a mano: la lista ya se quedó atrás una vez (en HALLAZGOS). Una
negativa nueva hereda de `NoSeMonta` y ya está cazada; hay prueba que recorre
el módulo y no deja ninguna suelta. Las de `--empaquetar` (`SinManifiesto`,
`SinRenovar` y `EsquemaQueNoCompila`, que compila todos los esquemas de
entrada) cuelgan de la otra raíz, **`paquete.NoSeEmpaqueta`**, por lo mismo.

**El código es AGPL-3.0-only.** Desde el 01-09-2026; antes era MIT. El motor
entero viaja al navegador de quien abre la página, en claro, dentro del `.whl`:
con MIT eso era regalar el producto con permiso para cerrarlo. La AGPL no
impide llevárselo, impide cerrarlo —artículo 13, el caso del servicio web—. Va
en tres sitios que tienen que decir lo mismo, y hay guardián para cada salto:
`pyproject.toml`, el fichero `LICENSE`, y el `dist-info` de la rueda. El porqué
entero está en el README.

**Las versiones se fijan y no se siguen a `latest`.** Lo que se prueba es una
combinación concreta; si se mueve sola, el día que algo se rompa no se sabrá
qué cambió. Son dos juegos distintos y conviene no confundirlos:

| Dónde | Qué | Escrito en |
|---|---|---|
| en el navegador | Pyodide 314.0.6 y su lxml 6.0.2 | `paquete.py` y `glosa.js`, que tienen que decir lo mismo |
| en lo que construye | lxml 6.1.2, setuptools 84.0.0 | `vercel.json`, `requisitos-pruebas.txt` y `[build-system]` |

setuptools va en `pyproject.toml` y no en la orden de Vercel porque `pip wheel`
construye en un entorno aislado y se trae el que diga `requires`. Y los seis
ficheros de Pyodide llevan su SHA-256 fijado en `HUELLAS_DE_PYODIDE`:
`HUELLAS.txt` no valía para esto —se calcula de lo que se baja y vive en
`vendor/`, que no se versiona—.

**No prometer de más.** Es la tesis del producto y la razón del nombre —una
glosa explica, no certifica—. Ni el informe, ni la página, ni la política de
privacidad afirman nada que no se haya comprobado. Las tres gravedades son
`ERROR`, `AVISO` y `NOTA`, y NOTA existe para decir *qué se aceptó y con qué
base*.

## El fallo que se repite

Cinco veces ha pasado lo mismo con distinto disfraz: **algo servido de una
caché haciéndose pasar por lo de hoy**. Un wheel viejo, un `prueba.py` viejo,
una comprobación incapaz de detectar el wheel viejo, un `index.html` viejo, y
la tarjeta social vieja en la vista previa de Telegram.
Nunca se rompe nada: sale todo verde y no es lo que crees que has probado.

Ante cualquier cosa que se sirva al navegador, la pregunta es *cómo se entera
de que cambió*. La respuesta de este repositorio es la huella del contenido:
`?v=<sha256[:8]>` para lo normal, y **en la ruta** cuando quien la consume no
admite query (`dist/<huella>/x.whl`, porque `loadPackage` rechaza cualquier cosa
detrás del `.whl`).

## Los ganchos, y por qué el cableado no viaja con ellos

Hay tres. La suite antes de publicar la corre **git**, no Claude Code:

| Gancho | Dispara con | Hace |
|---|---|---|
| `.githooks/pre-push` → `.githooks/antes-de-empujar.py`, versionados | **todo** `git push` de esta copia: Claude Code, la consola, un alias, un guion | se niega si lo que se empuja no es HEAD o hay cambios sin commit —lo probado tiene que ser lo publicado—, y si la suite no pasa, se cuelga o no arranca. Git cancela con cualquier código distinto de 0. Corre también con `--dry-run`: git no le dice que es un ensayo. El intérprete lo saca de la **copia principal** —`--git-common-dir`—, porque un worktree no tiene `.venv` propio |
| `.claude/hooks/antes-de-empujar.py`, versionado, `PreToolUse` | `Bash`, `PowerShell` | el **portero**: con código 2, no deja que una orden sobre Factura-e se salte a git —`--no-verify`, `git send-pack`, tocar `core.hooksPath`, un alias con `--no-verify`— ni empujar mientras el gancho de git no esté puesto. Qué es «sobre Factura-e» lo dice **git** y no la ruta: un worktree vive fuera de la carpeta del repositorio y se colaba como «otro proyecto» |
| `.claude/hooks/guardian-de-rutas.py` de la **carpeta de trabajo**, fuera del repositorio, `PreToolUse` | `Write`, `Edit`, `NotebookEdit` | se niega a escribir en lo que no se toca, y solo dentro de `C:\Users\PC\Claude\`, para no estorbar en otros proyectos de la máquina. Mira **todas** las rutas que manda la herramienta —`NotebookEdit` manda `notebook_path`, no `file_path`— y **sin mirar mayúsculas**, porque Windows no las distingue: `Sitio/` es `sitio/`. Sus decisiones se prueban en `tests/test_guardian_de_rutas.py`, que se salta donde el gancho no está |

**Por qué la suite la corre git.** Git llama a su gancho en todo push, se
escriba como se escriba. Un gancho de Claude Code que decide leyendo la orden
con una expresión regular se salta —la auditoría del 15-09-2026 le encontró
nueve maneras, en HALLAZGOS—, prueba la carpeta y no lo empujado, y no ve un
push desde la consola.

**Y además, dentro de GitHub.** `.github/workflows/pruebas.yml` corre la suite
en cada push y cada pull request, sobre una copia recién sacada y en Linux, se
empuje desde donde se empuje. Es la única de estas puertas que no depende de la
copia: una prueba que lea `esquemas/`, `anclas/` o `muestras/`, que escriba
fuera de su carpeta temporal o que dependa de cómo ordena rutas el sistema pasa
aquí y falla allí (lo que destapó al montarla está en HALLAZGOS).
`tests/test_pruebas_en_github.py` vigila que allí corra la suite entera, con el
Python del flujo, las versiones de `requisitos-pruebas.txt` y la comprobación
llamada `suite`. **No está enganchado a Vercel, a propósito**: lo que la
convierte en puerta es la **protección de `main`**, que exige `suite` de la
aplicación de GitHub Actions (no basta otra que pinte un verde con el mismo
nombre), también al dueño, y no admite pushes forzados ni que se borre. Se
activó el 21-10-2026, al hacer público el repositorio, porque en privado y con
el plan gratuito GitHub no la ofrece (la API contestaba 403). Medido ese día:
un push directo a `main` con un commit que GitHub no ha probado se rechaza con
`GH006`. **Se publica en dos pasos**: primero a una rama, `git push origin
HEAD:refs/heads/<rama>`, y cuando `suite` sale verde allí, el mismo commit a
`main` con `git push origin HEAD:main`, que ya lo encuentra probado.

**Nada de esto viaja entero con el repositorio.** Los guiones sí; el cableado
no:

- **Un worktree hereda la configuración y no el entorno.** `git worktree add`
  deja una copia de Factura-e donde le digas, compartiendo el mismo `.git`:
  `core.hooksPath` viaja, `.githooks/` está ahí por versionado, y `.venv` no,
  porque no se versiona. Por eso los dos ganchos reconocen el repositorio
  preguntando a git y no por la ruta, y el de git saca el intérprete de la
  copia principal (la tabla de arriba).
- `core.hooksPath` es configuración local de git. En una copia nueva hay que
  ponerlo una vez: `git config core.hooksPath .githooks`. Sin él, un push desde
  la consola publica sin probar; desde Claude Code, el portero se niega.
- Los de Claude Code **se declaran en los ajustes de usuario**,
  `C:\Users\PC\.claude\settings.json`, no en los del proyecto. Medido: con la
  declaración en `C:\Users\PC\Claude\.claude\settings.json` —la carpeta de
  trabajo—, una sesión arrancada en `Factura-e` no los cargaba y dejaban pasar
  todo. Los ajustes de proyecto se leen de la raíz de la sesión, no de sus
  ancestros; los de usuario se leen siempre.

Es el disfraz de siempre —sale todo verde y no es lo que crees que has
probado—, así que **la única comprobación que vale es provocarlos**, no leer la
configuración ni fiarse de que los ficheros existan:

```
git init --bare /tmp/prueba.git
git push /tmp/prueba.git HEAD:refs/heads/prueba   # con un fichero sin commit: se niega en ~1 s
git push --no-verify /tmp/prueba.git HEAD         # desde Claude Code: bloqueado por el portero
```

Empujar a un repositorio desnudo de usar y tirar no publica nada. Ya no vale
`git push remoto-que-no-existe`: git falla al buscar el remoto antes de llamar
al gancho, con gancho o sin él. Y un `Write` a `sitio/loquesea` tiene que salir
bloqueado. El panel de `/hooks` solo existe en la terminal interactiva, y allí
tampoco prueba que corran: prueba que están escritos.

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
- **Los dos servidores de `launch.json` escuchan en `127.0.0.1`** y no en
  todas las interfaces. `python -m http.server` a secas escucha en `0.0.0.0`:
  medido, el de `web` contestaba en la IP de la red local sirviendo el
  repositorio entero —`.git/HEAD`, `muestras/`, `anclas/`—. Que otro equipo
  llegue depende del cortafuegos, y eso no se ha medido; lo que se arregla con
  `--bind` no hace falta medirlo.
- **El sitio se monta, no se sube el repositorio**:
  ```
  ./.venv/Scripts/python.exe -m validador --traer-pyodide   # una vez
  ./.venv/Scripts/python.exe -m validador --sitio sitio
  ```
  En local se monta **sin** el paquete de esquemas y anclas si no está: se
  avisa por pantalla y se sale con 0, que es lo que hace falta para probar sin
  armar 389 anclas. **El despliegue pasa `--exigir-paquete`** y entonces se
  niega: Vercel solo mira el código de salida, así que un aviso perfecto y un
  `return 0` publicaban igual un validador que no comprueba ni la forma ni de
  quién es la firma.
- **La bitácora se escribe en `web/bitacora/`**, un fichero por artículo y
  solo el artículo: el armazón se lo pone `bitacora.html` al montar. Sin
  `data-fecha`, `data-titulo`, `data-entradilla` y un pie de fuentes con un
  enlace, **el sitio no se monta**. Lo que se publique ahí no lleva datos de
  terceros ni nada que perjudique el negocio: recuentos agregados, nunca un
  nombre, un NIF ni un GLN.
- **Un push a `main` despliega a producción** (Vercel lee `vercel.json`), y
  solo entra lo que ya pasó `suite` en GitHub: los dos pasos, arriba.
  La dirección es **`glosa-e.com`**, registrada en Vercel el 31-08-2026. El
  dominio canónico es **`www.glosa-e.com`** y el ápice redirige a él con un
  308; <https://glosa-dhm7.vercel.app> sigue sirviendo lo mismo. El porqué del
  nombre y los vecinos, en `MARCA.md`.
- **Después de publicar, se avisa a Bing** con
  `./.venv/Scripts/python.exe -m validador --avisar-indexnow`, con `sitio/`
  montado desde el commit de `main`. Solo manda las páginas que cambiaron
  desde el último aviso, y se niega con código 2 si producción no sirve lo
  montado. No va en la construcción de Vercel porque esa corre antes de que el
  despliegue esté en el aire.
- **El repositorio es `greedwhale/glosa-e`** desde el 21-10-2026. Se rehízo la
  historia para poder abrirla sin datos personales (el porqué, en el commit
  `7e9eff8`), y el de antes, `greedwhale/factura-e`, ya no se usa.
- **Cada commit va a nombre del titular**, `greedwhale
  <318060669+greedwhale@users.noreply.github.com>`, y sin línea de coautoría.
  Una sesión de Claude Code en la nube firma con su propia identidad, y así
  entraron en octubre cuatro commits a nombre de Claude: allí, antes del
  primer commit, se ponen `user.name` y `user.email` con esos dos valores.

## Las dos puertas de la ficha del titular

`TITULAR` en `web/glosa.js` ya no está vacío: lleva **el nombre de quien
responde, la marca y el correo**, y nada más. El nombre es el de una persona
—Dunior Hernández Martínez, desde el 15-09-2026— y no «Glosa-e», porque el RGPD
pide la identidad del responsable del tratamiento y una marca no identifica a
nadie; hay prueba de que no vuelva a ser la marca. De ahí salen dos puertas
distintas, y la diferencia es lo que hay que respetar al tocarlo:

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
