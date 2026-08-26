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

## Qué mirar

Arriba, el tiempo de arranque en frío. Abajo, doce comprobaciones que deben
salir todas en verde; cuatro están marcadas como **críticas** y son las que, si
fallan, tumban la idea entera:

| Comprobación | Por qué es crítica |
|---|---|
| lxml carga en WebAssembly | sin esto no hay nada |
| libxml2 trae soporte de esquemas XSD | de ello depende `esquema.py` |
| el paquete validador importa | el wheel se instala de verdad |
| el parser endurecido no expande entidades | una factura ajena no debe poder leer ficheros |
| una factura correcta sale conforme | sin falsos positivos |
| una factura rota se caza | sin falsos negativos |

Al final hay una zona donde soltar una factura de verdad. Esa parte es
exactamente la interacción del producto: leer el fichero en el navegador,
validarlo ahí y enseñar el informe. La red no se toca.

## Resultados medidos

En Chrome, sobre esta máquina, con Pyodide 314.0.6:

| | |
|---|---|
| lxml / libxml2 | 6.0.2 / **2.9.10** |
| Arranque en frío (descarga incluida) | ~42 s |
| Arranque con la caché ya caliente | ~4,8 s |
| Validar una factura | 5–120 ms |
| Validar las seis de `ejemplos/` | ~70 ms |
| Validar un lote de 200 | 2,05 s · 10,3 ms cada una · 23 MB de memoria |
| Bytes que baja el navegador | ~13,8 MB |

Los doce resultados coinciden exactamente con los de la misma prueba ejecutada
con Python nativo: mismos códigos, mismos resúmenes, mismos importes. Es la
comprobación que de verdad importa, porque libxml2 aquí es **2.9.10** y en
local es 2.11.9. Dos versiones distintas que dicen lo mismo.

## Lo que queda por resolver antes de que esto sea un producto

- **Los 13,8 MB del primer arranque.** Se pueden bajar: hay una compilación de
  Pyodide sin la biblioteca estándar completa, y el `.whl` de lxml es fijo y
  cacheable. Pero la primera visita nunca va a ser instantánea, y la página
  tiene que decirlo en vez de parecer rota.
- **Los esquemas XSD oficiales.** No están en el repositorio y aquí tampoco:
  la prueba los da por ausentes y comprueba que eso no revienta nada. Con ellos
  habría que bajar unos megas más.
- **Facturas de verdad.** Todo lo que se valida aquí sale de `ejemplos/`, que
  está escrito por nosotros. Que funcione en el navegador no dice nada sobre si
  las reglas aciertan con lo que emiten los programas de facturación reales.
  Eso es otra prueba, y es la que falta.

Un lote de 200 facturas sí se ha medido: 2 segundos y 23 MB. Eso significa que
la parte de pago —el lote del mes de una gestoría— también cabe en el
navegador, sin servidor que mantener ni datos que custodiar.
