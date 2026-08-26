# La primera prueba contra facturas ajenas

Hasta aquí, todo lo que este validador había visto lo habíamos escrito nosotros:
las seis de `ejemplos/` y las de los 444 tests. Eso comprueba que el código hace
lo que creemos que debe hacer. No dice nada sobre si acierta con documentos que
no salieron de nuestra cabeza.

El 26 de agosto de 2026 se le pasaron **73 facturas de tres suites oficiales**,
ninguna escrita por nosotros:

| Fuente | Qué es | Ficheros |
|---|---|---|
| [ConnectingEurope/eInvoicing-EN16931](https://github.com/ConnectingEurope/eInvoicing-EN16931) | los artefactos de validación oficiales de la norma europea | 43 |
| [OpenPEPPOL/peppol-bis-invoice-3](https://github.com/OpenPEPPOL/peppol-bis-invoice-3) | ejemplos de PEPPOL BIS Billing 3.0, incluidos los nacionales | 12 |
| [itplr-kosit/validator-configuration-xrechnung](https://github.com/itplr-kosit/validator-configuration-xrechnung) | la suite de pruebas del validador alemán XRechnung | 18 |

Están en `muestras/`, que no se versiona: son de terceros y cada una tiene su
licencia. `muestras/PROCEDENCIA.txt` dice de dónde sale cada fichero.

## El resultado en crudo

```
73 fichero(s) · 0 correcto(s) · 62 con errores · 11 SIN COMPROBAR
```

Cero correctos asusta hasta que se separa qué es cada cosa. **52 de las 62
facturas que se pudieron mirar no tienen ni una sola queja europea.** Lo que
las tumba a todas es una regla española aplicada donde no toca, y eso es un
fallo nuestro, no suyo.

## 1. El fallo grande: reglas españolas sobre facturas extranjeras

**CU-01 salta en 61 de las 62.** Ni una es española:

```
 17 NL   10 DE    9 DK    8 GB    5 NO    4 (sin prefijo)
  1 cada: IT XX HU SE HR BE EL AT
```

Se le está aplicando el dígito de control del NIF español a identificadores
holandeses, alemanes y daneses. Ninguno lo pasa, porque no es su algoritmo.

Es el fallo con más consecuencias de todos los encontrados: una gestoría
española con un solo proveedor europeo vería un muro de errores inventados el
primer día. Y el que se lleva un error falso la primera vez no vuelve.

Las reglas `CU-*` salen del RD 238/2026, que obliga a quien factura **en
España**. Una factura de un proveedor holandés a un cliente español no está
sujeta a ese reglamento.

**Arreglado.** `codigo_unico.obligado_en_espania` mira el país de la dirección
del vendedor; si falta, el prefijo del identificador fiscal; y si tampoco lo
hay, responde que sí, porque no saber no puede ser excusa para no mirar.
Facturae es español por definición. El filtro se aplica también a las reglas de
conjunto del lote: dos numeraciones de países distintos no tienen por qué
guardar relación, y se estaban denunciando como duplicados.

## 2. El fallo propio: la categoría O agrupada por tipo

Un solo fichero, `cef_XRechnung-O.xml`, saca **tres quejas que se contradicen
entre sí**:

- `BR-O-5` dice que una operación a O declara tipo 0%.
- `BR-O-8` dice que el desglose declara base a O **al 0%** y no hay líneas a ese
  tipo.
- `IVA-TIPO-SIN-DESGLOSE` dice que hay líneas a O **sin tipo** y no hay entrada
  del desglose a ese tipo.

Las dos últimas son la misma discrepancia contada desde los dos lados. La causa
está en `iva.py`: la clave de agrupación es `(categoría, tipo)` tanto para el
desglose como para las líneas. En este documento las líneas van a O sin tipo y
el desglose va a O con tipo `0.0000`, así que caen en dos cubos distintos y se
fabrica un desajuste que no existe.

**Para la categoría O el tipo no significa nada** —la norma prohíbe declararlo,
porque una operación no sujeta no tiene tipo que aplicar—, así que no debe
formar parte de la clave.

**Arreglado, y por debajo había más.** Al ir a buscar el texto normativo de
BR-O-05 al esquematrón oficial resultó que **toda la familia `BR-{X}-05` es de
la línea, no del desglose**: BR-O-05 cuelga de `$VATO_Line` y BR-S-05 de
`$VATS_Line`. Se comprobaban sobre la entrada del desglose, que casi siempre
lleva el mismo tipo que sus líneas —por eso 444 tests no lo notaron—. En la
categoría O se separan, y ahí salía la queja falsa. Ahora la familia se aplica
a los conceptos, con su sufijo según de qué cuelgue: 5 para la línea, 6 para el
descuento de documento y 7 para el cargo.

De paso apareció un tercer fallo: los códigos de IGIC e IPSI eran `BR-IG-*` y
`BR-IP-*`, inventados aquí por analogía con `BR-IC-*`. La norma los llama
**`BR-AF-*` y `BR-AG-*`**. Importa más de lo que parece, porque el IGIC es el
impuesto de Canarias: una factura canaria recibía una regla con un código que
no existe en ningún reglamento.

## 3. Lo que hay que decidir: monedas sin céntimos

`cef_huf_example_cii.xml` está en forintos húngaros. Declara base 69.180,00 al
27% y cuota 18.679,00. La cuenta exacta da 18.678,60: una diferencia de 0,40,
muy por encima de la tolerancia de ±0,01.

Por la letra de BR-CO-17 tenemos razón. Pero el forinto se factura redondeado a
la unidad, y ese fichero está en la carpeta de ejemplos oficiales precisamente
para enseñar el caso. La tolerancia está pensada para monedas de dos decimales.

**Sin tocar, a propósito.** No afecta a ninguna factura española y conviene
comprobar antes qué hace el validador oficial con ese mismo fichero. Es el
único de los tres que sigue abierto.

## 4. Lo que el validador acertó

Ocho de las diez facturas con queja europea la merecían, y en varios casos se
puede demostrar:

| Fichero | Queja | Por qué es cierta |
|---|---|---|
| `xrech_ubl002` | BR-06 sin nombre del vendedor | el `RegistrationName` está comentado, con un `<!-- Error -->` al lado |
| `xrech_ubl003` | BR-09 sin país | ídem, comentado a propósito |
| `xrech_ubl005` | BR-03 sin fecha | ídem |
| `xrech_ubl006` | BR-01 sin especificación | ídem |
| `xrech_ubl008` | BR-24 línea sin importe | es un **abono**, y la línea no lleva importe |
| `xrech_ubl-br-dex-09` | BR-CO-16 total a pagar | el propio fichero lleva una instrucción `<?xmute … schematron-invalid ?>`: está roto adrede |

El mejor de todos es **`xrech_cii001.xml`**, que no viene marcado como
defectuoso. El desglose al 21% declara base 46,57 y cuota 9,74. Pero las líneas
a ese tipo suman 46,37 —y 46,37 × 21% = **9,74**, la cuota que el propio fichero
escribe—. La base tiene una errata: dice 46,57 donde debía decir 46,37. La
aritmética no miente, y ninguno de nuestros ejemplos habría enseñado esto.

También acertaron los once **SIN COMPROBAR**, que es donde más se nota la última
corrección:

- `xrech_bin001.xml` es un **BMP con extensión `.xml`**. Justo el caso para el
  que se escribió el tercer estado. No sale como correcto.
- `xrech_ubl007.xml` termina en `<!-- WFR violation -->` con el cierre
  `</Invoice>` comentado: no es XML bien formado, a propósito.
- Los otros nueve son EDIFACT con raíz `M_INVOIC`. No es una de las tres
  sintaxis que soportamos y se dice, en vez de callarse.

Ninguno de los once contó como aprobado. Antes del arreglo, los once habrían
salido entre los buenos y la consola habría devuelto 0.

## Un mensaje correcto que aun así está mal

`peppol_GR-base-example-TaxRepresentative.xml` no tiene
`PartyLegalEntity/RegistrationName`, que es donde EN 16931 pone el nombre del
vendedor (BT-27). BR-06 salta con razón. Pero el nombre **sí está** en el
fichero, en `PartyName/Name`.

Decirle a alguien «falta el nombre del vendedor» cuando el nombre está delante
de sus ojos es la clase de mensaje que hace desconfiar de la herramienta
entera. Debería decir dónde está y dónde tenía que estar.

Esto no es un fallo de la validación. Es un fallo del producto, que es lo que
vendemos.

## Lo que esta prueba todavía no cubre

- **Facturae.** Ninguna de las tres suites lo incluye, porque es un formato
  nacional español y ellas son europeas. Es justo el formato que más se emite
  aquí, y sigue sin probarse contra ficheros ajenos.
- **Facturas de producción.** Estas son ficheros de prueba de organismos de
  normalización: limpios, pequeños y pensados para ilustrar reglas. Una factura
  real de un programa de facturación español trae adjuntos, firma, extensiones
  y rarezas que aquí no aparecen.

## Después de los arreglos

Los mismos 73 ficheros, sin tocar ni uno:

```
antes:    73 fichero(s) · 0 correcto(s) · 62 con errores · 11 SIN COMPROBAR
después:  73 fichero(s) · 53 correcto(s) · 9 con errores · 11 SIN COMPROBAR
```

Las nueve que siguen dando error son las ocho que la merecían y la húngara, que
se ha dejado a propósito. Ninguna regla española salta ya sobre una factura
extranjera.

460 tests. Los dieciséis nuevos fallan con el código anterior: se ha comprobado
revirtiendo cada arreglo por separado y volviéndolos a pasar.

## Con los esquemas XSD oficiales puestos

Hasta aquí la validación de forma no se había ejercitado nunca contra ficheros
reales: `esquemas/` estaba vacía y el validador lo decía al final de cada
informe. Se instalaron los oficiales —Facturae 3.0, 3.1, 3.2, 3.2.1 y 3.2.2 de
[facturae.gob.es](https://www.facturae.gob.es/), UBL 2.1 de OASIS y CII D16B de
los artefactos de la Comisión—, 24 ficheros y 3,8 MB. No se versionan.

Las nueve españolas **cumplen todas su esquema**. Antes de creérselo se
comprobó que la comprobación está viva: metiéndoles a mano una etiqueta
inventada, un importe con letras y una cabecera renombrada, salta en los tres
casos. De las 73 europeas, tres no cumplen.

Y ahí aparecieron dos cosas más.

### Un mensaje que mandaba a borrar lo que no sobraba

`peppol_GR-base-example-correct.xml` —que se llama «correct»— tiene dos
`AdditionalDocumentReference` colocados después del cliente, cuando UBL 2.1 los
pone antes del proveedor. El esquema lo rechaza con razón. Pero el mensaje
decía:

> «AdditionalDocumentReference» aparece 2 veces y el esquema no admite tantas.

Y UBL sí admite tantas: ese elemento es `maxOccurs="unbounded"`. Lo que está
mal es **dónde** están, no cuántos hay. Quien leyera ese mensaje borraría uno y
no arreglaría nada.

La causa, en `_por_que_no_encaja`: se contaban los hermanos con el mismo nombre
y, si había más de uno, se daba por repetido antes de mirar el orden. Contar no
distingue los dos casos. Lo que hace que uno sobre es que **otro igual haya
pasado ya por su sitio bueno**; si el que se queja es el primero, el problema es
la posición. Ahora se mira eso, y el mensaje nombra qué elementos tenían que ir
delante.

### La suite de tests no era hermética

Al poner los esquemas, **doce tests que llevaban meses en verde se pusieron
rojos**. Ninguno era sobre esquemas: eran los de `factura.py`, que construyen
facturas mínimas —lo justo para retorcer una regla de negocio— y por eso no
cumplen el XSD completo, donde `PartyTaxScheme` exige su `TaxScheme` dentro.

El fallo real no era de esos tests sino del conjunto: `Catalogo.por_defecto()`
lee la carpeta `esquemas/` del directorio actual, así que **el resultado de la
suite dependía de si quien la ejecuta se había bajado los XSD**. Verde en una
máquina y rojo en otra, sin que cambie una línea de código.

`tests/conftest.py` lo declara ahora en voz alta: los tests apuntan a una
carpeta de esquemas que no existe. Quien quiera probar la validación de forma
monta su propio `Catalogo`, que es lo que ya hacía `test_esquema.py`.

## La auditoría independiente

Se encargó a un revisor independiente decidir, con pruebas, si la herramienta
hace su trabajo. Con el encargo explícito de no dar nada por bueno porque lo
diga esta documentación: todo lo que hay aquí lo ha escrito el mismo autor cuya
obra se audita, comentarios incluidos.

Su veredicto: **hace bien la parte que hace —forma XSD y código único, sin un
solo error de los que denuncia— pero sobre Facturae no comprueba ni un número,
y lo dice de una manera que se lee como aprobado.**

### Lo que confirmó, y cómo

- **El algoritmo del CIF es correcto.** Lo implementó desde su definición, sin
  leer ni importar `nif.py`, y comparó ocho identificadores. Coincidencia total,
  incluidos los dos inválidos de las muestras oficiales, que por casualidad
  piden el mismo dígito. Prueba adicional: inyectó un CIF con el dígito de
  control cambiado y la herramienta pidió el mismo que da su implementación.
- **Los tres duplicados de `CU-10` son reales.** Uno es idéntico byte a byte;
  los otros dos son el mismo cuerpo con y sin firma.
- **Las cuatro facturas que salen limpias cuadran de verdad.** Escribió su
  propio comprobador aritmético y las repasó.

### Lo que encontró y ya está arreglado

**`IVA-TIPO` se aplicaba a facturas que no son españolas.** El filtro
`obligado_en_espania` se cableó a la familia `CU-*` y se olvidó esta. Resultado:
**64 quejas en 50 de las 73 facturas europeas**, denunciando el 25 % danés, el
19 % alemán y el 27 % húngaro como si fueran dedazos. Eran **el 70 % de todo lo
que decía el programa**, y enterraban la señal útil debajo.

Es el mismo error diagnosticado y corregido una vez, sin terminar de aplicarlo.
Ahora `iva.reglas` recibe si el documento es español y el orquestador lo decide
una sola vez para los dos bandos. El corpus europeo pasa de 91 incidencias a 27.

### Lo que encontró y sigue abierto

Por orden de gravedad:

1. **Sobre Facturae no se valida ninguna aritmética, y se demostró.** Copió una
   factura oficial e inyectó nueve defectos de uno en uno: total a 999.999,99,
   cuota de IVA a 1,00, una línea que ya no suma la base, cantidad cambiada sin
   tocar el importe, tipo al 77 %, total negativo, NIF del receptor inválido...
   **Nueve defectos, nueve silencios.** La capacidad existe —el mismo defecto en
   un UBL salta como `BR-CO-16`— pero no se enchufa: `en16931.reglas` devuelve
   solo `SIN-SOPORTE` si la familia no es UBL o CII, y `iva.reglas` se llama
   dentro de esa rama.

   Cuantificado: de los 64 códigos de regla implementados, sobre un Facturae
   solo pueden dispararse 25 (los `XSD-*` y los `CU-*`). De los que son
   comprobación de negocio, 14 de 53. **De la aritmética, cero.**

2. **Dos muestras oficiales tienen la base mal repartida y no lo decimos.** En
   `gob_facturae_32v1.xml` el total antes de impuestos es 59,75 pero las bases
   del desglose suman 26,00: quedan 33,75 € sin gravar. En
   `gob_sample-factura-firmada-31.xml` la base declarada es la de antes de
   descuentos y recargos: 22,08 € de diferencia. En UBL las cazarían `BR-CO-10`
   y `BR-CO-13`.

3. **`CU-07` no cubre lo que su mensaje promete.** Dice «más de 4 años» pero
   compara años de calendario: `fecha.year < hoy.year - 4`. Una factura de
   2022-01-01, con 4 años y 7 meses, no salta. Se pierde todo el tramo entre 4
   y casi 5 años.

4. **`BR-09` y `BR-11` se evalúan desde la raíz.** En el esquematrón normativo
   cuelgan de la dirección postal del vendedor y del comprador. Si falta la
   dirección entera, la norma dispara solo `BR-08`; aquí salen las dos, y se
   duplica la queja sobre un solo defecto. Es la misma familia de error que el
   `BR-{X}-05` ya corregido. Comprobado quitando el bloque de dirección.

5. **`CU-14` afirma algo que no ha pasado.** Dice «la fecha retrocede al avanzar
   el número» sobre dos facturas con el **mismo** número. Las entradas se
   ordenan solo por ordinal y, al empatar, el orden entre ellas es el de
   llegada. La incidencia real —número repetido— ya la había dicho `CU-11`.

6. **`XSD-TIPO` diagnostica lo que no es en las fechas imposibles.** Con
   `2012-02-31` responde «una fecha se escribe AAAA-MM-DD». Ya está escrita así:
   lo que pasa es que el 31 de febrero no existe. La pista es un literal fijo
   por tipo, no depende del fallo concreto.

7. **«Sin errores» promete más de lo hecho.** Es el mensaje más peligroso del
   programa. Sobre un Facturae significa exactamente «cumple el XSD y su código
   único es formable y no está repetido», y se lee como «esta factura está
   bien». Y `SIN-SOPORTE` dice lo contrario en la otra dirección —«solo se ha
   identificado, no validado»— que tampoco es cierto, porque XSD y `CU-*` sí se
   han aplicado. Las dos frases juntas dejan al lector sin saber qué se ha
   mirado.

8. **La cabecera de un fichero puede decir «sin errores» y ser un error.** Los
   duplicados salen como incidencia de lote, así que cada fichero del par se
   imprime como limpio y el recuento final los cuenta entre los correctos.

9. **El NIF del receptor no se valida nunca.** Es defendible —el código único
   solo usa el del emisor— pero conviene saberlo.

### Lo que el auditor no verificó

La validez criptográfica de las firmas XAdES; el texto del RD 238/2026 en sí
—comprobó que los cálculos son correctos, no que la norma diga lo que el código
afirma—; y el contexto de las reglas `BR-*` en la sintaxis CII, porque solo
descargó el esquematrón de UBL.
