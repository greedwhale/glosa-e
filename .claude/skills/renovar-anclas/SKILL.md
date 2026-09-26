---
name: renovar-anclas
description: Rehace las anclas de confianza desde la lista del Estado y vuelve a armar el paquete que viaja con la página. Úsala cuando el aviso ANCLAS-SIN-RENOVAR salte, o cuando la lista española pase de su fecha de renovación.
disable-model-invocation: true
---

# Renovar las anclas de confianza

## Por qué existe esta orden

Un certificado raíz dura veinte o treinta años. **La lista de quién sigue
estando autorizado se renueva cada seis meses.** Son dos cosas distintas y esa
diferencia es justo la que se olvida: las anclas no caducan, caduca el permiso
para seguir creyéndoselas.

Por eso el informe saca `ANCLAS-SIN-RENOVAR` como AVISO en cuanto se pasa la
fecha, y por eso ese aviso no se apaga solo. Esta orden es lo único que lo
apaga, y hay que ejecutarla de verdad: no se edita el manifiesto a mano.

Antes de tocar nada, apunta el estado del paquete que se publica ahora mismo.
Se lee de `web/PAQUETE.json`, que es el que manda:

```bash
./.venv/Scripts/python.exe -c "import json; d = json.load(open('web/PAQUETE.json', encoding='utf-8')); print({k: d[k] for k in ('publicada', 'siguiente', 'armado', 'esquemas', 'anclas', 'anclas_de_sellos')})"
```

`publicada` es la fecha de la lista; `siguiente`, cuándo habría que renovarla;
y `armado`, cuándo se montó el paquete.

## Lo que hace falta bajar

Las direcciones están en el `README.md` y **no en el código**, a propósito: una
dirección dentro del programa parece un dato de confianza y no lo es. Son
estas, y conviene releerlas en el README antes de usarlas por si han cambiado:

- **LOTL europea:** `https://ec.europa.eu/tools/lotl/eu-lotl.xml`
- **Lista de España:** `https://tsl.digital.gob.es/TSL.xml` (unos 3 MB)

Las huellas SHA-256 de los seis certificados que pueden firmar la LOTL están en
el anexo del **DOUE C/2026/1944, de 15 de abril de 2026**. Ese es el final de
la cadena y está fuera de internet: es lo único que no se comprueba contra
nada, porque es contra lo que se comprueba todo lo demás.

Las dos se dejan en `listas/`, que **no se versiona**.

## Los pasos

**1. Mirar qué trae la lista nueva, antes de montar nada.**

```bash
./.venv/Scripts/python.exe -m validador --ver-tsl listas/TSL.xml
```

Dice de quién es, de cuándo, y cuántas autoridades trae concedidas y retiradas.
Si la fecha de publicación no ha avanzado, no hay nada que renovar.

**2. Montar las anclas.** La carpeta se rehace entera, no se parchea:

```bash
./.venv/Scripts/python.exe -m validador --montar-anclas listas/TSL.xml \
    --segun listas/eu-lotl.xml --firmante <huella del DOUE> [--firmante <otra>...]
```

De una lista sin comprobar no se monta nada: es una negativa del programa, no
una recomendación.

**3. Ver qué ha entrado y qué se ha ido.**

```bash
./.venv/Scripts/python.exe -m validador --ver-anclas
```

**Compara los números con los que apuntaste al principio y di la
diferencia en voz alta.** Un salto grande sin explicación es motivo para parar
y mirar, no para seguir. De las de agosto de 2026, dos caducaban el 31 de
diciembre.

**4. Rearmar el paquete de la página.**

```bash
./.venv/Scripts/python.exe -m validador --empaquetar
```

No empaqueta anclas sin manifiesto ni anclas cuya lista debiera haberse
renovado. Si se queja, la respuesta correcta casi nunca es
`--aunque-esten-vencidas`: eso es para probar, no para repartir.

**5. Comprobar que el aviso se ha apagado**, validando un ejemplo firmado:

```bash
./.venv/Scripts/python.exe -m validador ejemplos/fe-0001.xml
```

`ANCLAS-SIN-RENOVAR` no debe salir. Si sigue saliendo, algo del paso 4 no se
guardó donde se cree.

**6. Los tests, el sitio y el push.**

```bash
./.venv/Scripts/python.exe -m pytest -q
./.venv/Scripts/python.exe -m validador --sitio sitio
```

`web/paquete.zip` y `web/PAQUETE.json` **sí se versionan** —son la excepción
deliberada— así que entran en el commit. Las carpetas fuente (`anclas/`,
`listas/`) no.

## Al terminar

Cuenta cuántas anclas entran, cuántas salen y de qué fecha es la lista nueva.
Publica el SHA-256 del paquete en el mensaje del commit, que es lo que permite
contrastar lo que viaja con lo que se armó.

Y después: `/comprobar-produccion`, que el panel de la página enseña la fecha de
la lista y es donde se ve si de verdad llegó.
