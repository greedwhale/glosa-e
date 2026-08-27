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

---

# Portar las reglas de negocio a Facturae

El hallazgo número 1 de la auditoría, resuelto. Era el que decidía si esto vale
para el mercado español: el formato que España usa de verdad era el que menos
se validaba.

## Se fue al esquema, no a la memoria

El XSD de Facturae lleva la aritmética escrita en sus anotaciones, en
castellano y campo por campo:

> **TotalGrossAmountBeforeTaxes.** Resultado de: TotalGrossAmount -
> TotalGeneralDiscounts + TotalGeneralSurcharges.

> **TotalExecutableAmount.** Resultado de: TotalOutstandingAmount -
> WithholdingAmount - PaymentInKindAmount + TotalReimbursableExpenses +
> TotalFinancialExpenses.

Cada regla de `validador/facturae.py` cita la frase de la que sale. Es la misma
disciplina que encontró que `BR-{X}-05` colgaba de la línea y no del desglose.

**Y se comprobó la lectura antes de escribir una sola regla.** La cadena de
totales de `gob_sample-factura-firmada-31.xml` cuadra al céntimo con la fórmula
tal como la leí: 468,10 − 2,34 − 0 + 20,99 + 2,99 = 489,74, que es exactamente
lo que declara. Una fórmula que reconstruye un fichero oficial que no he escrito
yo no es una suposición.

## Nueve defectos, nueve silencios, veinte quejas

Se repitió la demostración del auditor sobre `gob_factura_sinFirmar.xml`, y
además se midió el «antes» en vez de recordarlo: se ejecutó el mismo lote con
el módulo nuevo desactivado.

| Defecto inyectado | Antes | Ahora |
|---|---|---|
| total de factura a 999.999,99 | 0 | `FE-TOTAL`, `FE-PENDIENTE`, `FE-LOTE-TOTAL` |
| cuota de IVA a 1,00 | 0 | `FE-CUOTA`, `FE-REPERCUTIDOS` |
| una línea que ya no suma | 0 | `FE-LINEA-BRUTO`, `FE-LINEA-SIN-GRAVAR`, `FE-BRUTO` |
| tipo de IVA al 77 % | 0 | `FE-CUOTA` |
| base antes de impuestos falsa | 0 | `FE-BASE`, `FE-TOTAL`, `FE-SIN-GRAVAR` |
| coste ≠ cantidad × precio | 0 | `FE-LINEA-COSTE`, `FE-LINEA-BRUTO` |
| total a pagar descuadrado | 0 | `FE-PENDIENTE`, `FE-EJECUTAR`, `FE-LOTE-PENDIENTE` |
| total a ejecutar descuadrado | 0 | `FE-EJECUTAR`, `FE-LOTE-EJECUTAR` |
| la cabecera del lote miente | 0 | `FE-LOTE-CUENTA` |
| **total** | **0** | **20** |

## Y los dos defectos reales, al céntimo

Sobre las nueve muestras oficiales, sin tocar ninguna:

- `gob_facturae_32v1.xml` (y su duplicado firmado): **33,75 € facturados y sin
  gravar**, señalados dos veces —en la línea «Flores», que es donde está el
  fallo, y en el desglose de la factura.
- `gob_sample-factura-firmada-31.xml`: **22,08 €**, la base declarada es la de
  antes de descuentos y recargos.

Las mismas dos cifras que el auditor había sacado a mano. **Cero quejas de
aritmética sobre las otras siete**, incluida `alphp_factura-prueba-v1-2-0.xml`,
que es la más enrevesada del lote: descuento general, descuento y cargo de
línea, dos impuestos repercutidos sobre la misma base, recargo de equivalencia
y retención de IRPF. Que esa salga limpia es la prueba de que las fórmulas
están bien leídas.

El corpus europeo no se movió: 73 · 52 correctas · 10 con errores · 11 sin
comprobar, igual que antes. Las reglas nuevas no tocan UBL ni CII.

## Tres cosas que salieron al escribirlo

**El recargo de equivalencia cuenta en el total repercutido.** «Sumatorio de
todas Cuotas *y Recargos de Equivalencia*». Sin leer esa mitad de la frase,
`alphp` habría dado 244,34 frente a los 279,24 que declara: 35 € de queja falsa
sobre una factura correcta.

**No se pueden sumar todas las bases del desglose.** Una operación puede llevar
dos impuestos distintos sobre la misma base —IPSI e IVA— y sumarlas daría el
doble. Se agrupa por clase de impuesto. `alphp` lo hace, y sin agrupar habría
recibido un descuadre inventado del 100 %.

**La tolerancia se cuenta en cifras, no en entradas.** Una entrada de impuesto
con recargo aporta *dos* importes redondeados a la suma. Contando entradas, la
holgura se quedaba corta y una factura correcta con dos impuestos y un recargo
se rechazaba por dos céntimos. **Esto lo cazó un test, no la lectura**: fue
justo el test que hubo que reescribir porque no distinguía nada.

## Sobre los tests

37 nuevos, 502 en total. Comprobado por reversión:

- Con el módulo desactivado, **30 de los 37 se ponen rojos**.
- Los 7 que sobreviven son los que vigilan *falsos positivos*, y por definición
  pasan cuando el módulo calla. Para probar que distinguen algo se rompió a
  propósito la defensa concreta que cada uno guarda: agrupar bases por
  impuesto, desenvolver la firma XAdES, callar el `SIN-SOPORTE`. Todos se
  pusieron rojos menos uno.
- **Ese uno no distinguía nada.** El de la tolerancia pasaba igual con el
  céntimo fijo, porque el caso que probaba caía dentro de las dos. Se reescribió
  con un desvío de dos céntimos, que separa las dos implementaciones —y al
  reescribirlo destapó el fallo de contar entradas en vez de cifras.

## Lo que este trabajo *no* arregla

Facturae no tiene categorías de IVA —la letra S, Z, E, AE, K, G, O de
EN 16931—, así que toda la familia `BR-{X}-*` sigue sin equivalente y no lo
tendrá: no hay dónde mapearla. Lo que se comprueba ahora es la aritmética, que
es donde estaba el agujero. La firma XAdES tampoco se validaba entonces; se
hizo después, y está al final de este documento.

---

# Los siete arreglos restantes

Hallazgos 3 a 9 de la auditoría. Cerrados los nueve.

Cada uno se reprodujo antes de tocar nada, y cada test nuevo se comprobó
revirtiendo su arreglo por separado.

## 3. `CU-07` no cubría lo que su mensaje promete

Decía «más de 4 años» y comparaba **años de calendario**. Reproducido: del 20
de septiembre de 2026, una factura del 1 de enero de 2022 —cuatro años y siete
meses— pasaba sin decir nada, y una del 31 de diciembre de 2021, **tres semanas
más vieja**, sí saltaba. La diferencia real entre las dos es de tres semanas y
la respuesta del programa era la contraria.

Ahora se comparan fechas, con el 29 de febrero resuelto al 28. Un test antiguo
—«fecha dentro de prescripción no avisa», con 2022-05-01, que son cuatro años y
medio— pasaba **solo porque la comprobación miraba años de calendario**.

## 4. `BR-09` y `BR-11` se evaluaban desde la raíz

En el esquematrón normativo cuelgan de la dirección postal. Sin dirección, la
norma dispara `BR-08` y calla. Aquí salían las dos, y el informe contaba dos
defectos donde había uno, con el segundo además mal descrito: no es que a la
dirección le falte el país, es que no hay dirección.

Misma familia que el `BR-{X}-05` que se comprobaba sobre el desglose en vez de
sobre la línea. Va con la prueba que impide «arreglarlo» borrando la regla: con
dirección y sin país, `BR-09` sigue saltando.

## 5. `CU-14` afirmaba algo que no había pasado

Reproducido literalmente:

```
[CU-11] El número de factura está repetido con otra fecha.
[CU-14] La fecha retrocede al avanzar el número.
        Tiene: F-001 el 2026-03-05, pero F-001 el 2026-03-02
```

El número no había avanzado: es el mismo. Las entradas de una serie se ordenan
solo por ordinal, y al empatar quedan en el orden en que llegaron —el de los
ficheros de la carpeta—. De ese caso ya se queja `CU-11`, que sí sabe lo que
es.

## 6. `XSD-TIPO` diagnosticaba lo que no era

A `2012-02-31` respondía «una fecha se escribe AAAA-MM-DD». Ya está escrita
así. Quien lee eso comprueba el formato, lo ve bien y no encuentra el fallo.

La pista era un literal fijo por tipo. Ahora, en las fechas, mira el valor: «la
forma está bien, pero ese día no existe: febrero de 2012 tiene 29 días». Y sabe
de años bisiestos —`2011-02-29` da 28— y de meses que no existen.

## 7. «Sin errores» prometía más de lo hecho

El mensaje más peligroso del programa. No quiere decir «esta factura está
bien»: quiere decir «no ha fallado ninguna de las comprobaciones que existen»,
y quien lo lee no tiene por qué saber cuáles son.

La mitad grande se cerró portando la aritmética de Facturae. Lo que quedaba se
dice ahora al final del informe, una sola vez —como el recordatorio de los
esquemas, y por lo mismo: en un lote de doscientos, cien repeticiones de la
misma advertencia son ruido—:

```
«Sin errores» quiere decir que se ha comprobado la forma contra el esquema
XSD, la aritmética del formato Facturae (líneas, totales, impuestos y cabecera
de lote), el código único del RD 238/2026.
No se comprueba la validez de las firmas electrónicas, ni si lo que dice la
factura es cierto.
```

La frase se ajusta a lo que había en el lote: a un Facturae no le promete
reglas europeas, a un UBL no le promete las de Facturae, y **si no hay esquemas
XSD puestos no promete la forma** —decirlo justo encima del recordatorio de que
no hay esquemas eran dos líneas seguidas contradiciéndose, que es peor que no
decir nada y es exactamente el defecto que esta línea viene a arreglar—.

Y el `SIN-SOPORTE` que decía lo contrario en la otra dirección ya no sale sobre
Facturae. Sobre EDIFACT sí, que ahí es cierto.

## 8. Un fichero podía decir «sin errores» y ser medio duplicado

Un duplicado no es de ninguno de los dos ficheros por separado: cada uno,
mirado solo, está perfecto. Los dos se imprimían «sin errores», los dos se
contaban entre los correctos, y el error aparecía al final huérfano. El resumen
podía decir «2 correctos, 0 con errores» sobre un lote que sí tiene un error.

Ahora una incidencia sabe a qué ficheros apunta, el recuento los deja fuera de
los correctos, y la línea de cada uno lo dice: «sin errores, pero choca con
otro fichero (ver abajo)». Sobre las nueve muestras españolas, de 4 correctas a
2 —y las dos que quedan son las que de verdad no chocan con nada—.

Límite conocido: se atribuyen las tres incidencias de conjunto que son error
(`CU-10`, `CU-11`, `CU-12`). Las de serie (`CU-13`, `CU-14`, `CU-15`) son
avisos y no cambian el recuento, así que no se les ha hilado la procedencia.

## 9. El NIF del receptor no se validaba nunca

Ahora sí, pero como **aviso «de la casa» y sin prefijo `CU-`**: el código único
solo usa el del emisor, así que el RD 238/2026 no firma esta queja y no puede
salir con su etiqueta. Es el mismo cuidado que falló con unos `BR-IG-*`
inventados.

Al escribir la guarda de «esta factura no es española» **salió mal a la
primera**: un `NL999999999B01` recibía la queja igualmente, que es exactamente
el fallo que costó 61 quejas falsas en 62 facturas ajenas. Lo cazó el test. La
pista —dos letras seguidas al principio son prefijo de país, y ningún NIF, NIE
ni CIF español empieza así— vivía solo en `obligado_en_espania` y al copiarla se
copió mal; ahora las dos la leen del mismo sitio.

## Lo que sigue sin comprobarse, y ahora se dice

La validez criptográfica de las firmas XAdES, que en Facturae es lo que le da
validez legal frente a terceros. Y si lo que dice la factura es cierto, que no
lo puede saber ningún validador.

527 tests.

---

# La firma XAdES

El único punto que quedaba abierto de la lista de arriba. Se cierra a medias, y
la mitad que no se cierra se dice con todas las letras.

## Lo que se comprobó antes de escribir nada

La pregunta que decidía si esto era viable: **¿se puede reproducir el resumen de
un documento firmado por el Gobierno?** Si la respuesta era no —por
canonicalización, por saltos de línea, por lo que fuera—, no había módulo que
escribir.

Sobre `gob_sample-facturae-firmada.xsig.xml`, con C14N 1.0 no exclusiva:

| referencia | resultado |
|---|---|
| `#Signature-SignedProperties` | coincide |
| `` (documento entero, enveloped) | coincide |
| `#Certificate1` | coincide |

Las tres, exactas. Y las cinco muestras firmadas verifican enteras, resúmenes y
RSA. Solo entonces se escribió el módulo.

## Sin dependencias nuevas, y por qué importa

Verificar RSA es `pow(firma, e, n)`: aritmética de enteros, que Python hace
nativa. Leer la clave pública del certificado son unas líneas de DER. Traer
`cryptography` habría costado una extensión compilada, y esto corre dentro del
navegador con Pyodide: cada dependencia nativa es otro wheel que buscar, otra
versión que casar y varios megas de descarga. **Este módulo no añade ni un byte
a la descarga**: son unos kilobytes dentro del wheel que ya se bajaba. Medido
en el navegador después de añadirlo, se descomprimen 14,71 MB y todo eso es
Pyodide y lxml. Cuesta 3-5 ms por factura firmada.

## El detalle que no se deja al azar

`_verificar_rsa` reconstruye el bloque PKCS#1 entero y compara bytes. La forma
natural de escribirlo es la contraria —abrir el bloque descifrado, saltarse el
relleno y leer el resumen de dentro—, y así se escribió durante años en medio
mundo. Un lector permisivo acepta bloques con el relleno corto y basura detrás,
y con eso se fabrican firmas falsas sin tener la clave privada: el fallo de
Bleichenbacher de 2006, que volvió en 2014 como «BERserk».

Comprobado que la diferencia es real, no teórica. Sobre el mismo bloque forjado
`00 01 FF 00 <DigestInfo> <basura>`:

| bloque | versión ingenua | la nuestra |
|---|---|---|
| el correcto | acepta | acepta |
| relleno corto + basura | **acepta** | rechaza |
| sin byte separador | rechaza | rechaza |
| resumen de otro mensaje | rechaza | rechaza |

Con precisión, porque conviene no exagerar: fabricar uno de esos bloques exige
exponente público pequeño —3 o 17—, y con 65537 no se puede. Pero certificados
con exponente 3 los hay, escribirlo bien cuesta cero, y la alternativa es un
validador que da por buena una firma falsa.

## Lo que salió al pasarlo por las muestras

`gob_sample-factura-firmada-31.xml` firma con un certificado **caducado**:
vencía el 31-01-2009 y la firma declara el 25-02-2009, veinticinco días
después. Es la misma factura que ya traía el descuadre de 22,08 € en la base
imponible. Las otras cuatro firmadas verifican sin una queja de integridad.

Las cinco usan RSA-SHA1 y cuatro tienen claves de 1024 bits, así que salen con
aviso —no error—: la firma puede ser auténtica, el algoritmo ya no da
garantías.

## Dos cosas que costaron

**`getpath` frente a `getelementpath`.** Para calcular el resumen del documento
entero hay que quitarle la firma, y sobre una copia hay que volver a localizar
la misma firma. `getpath` devuelve una ruta con prefijos de namespace que la
copia no tiene declarados: lxml responde «Undefined namespace prefix» en
cualquier documento con prefijos, o sea en todos los Facturae firmados.
`getelementpath` usa notación `{namespace}etiqueta` y no depende de prefijos.

**Una prueba que no probaba nada.** El primer intento de sustituir el
certificado por otro hacía un `replace` sobre el texto del fichero con el
base64 que devuelve lxml. Al parsear, lxml normaliza CRLF a LF: el texto
devuelto no está literalmente en el fichero, el `replace` no encontraba nada, y
la prueba pasaba sin sustituir nada. Se rehízo sacando el base64 crudo con una
expresión regular, y entonces sí falló como debía.

## Sobre los tests

Los 33 nuevos no dependen de `MuestrasFE/`, que no se versiona: **firman de
verdad**. Se construye un certificado X.509 a mano en DER —versión, serie,
emisor, validez, sujeto y la clave— y se firma con una clave RSA de 512 bits
cuyos primos están escritos en el fichero.

Tener la clave privada es lo que permite lo que ninguna factura real permite:
fabricar bloques PKCS#1 a medida y comprobar que se rechazan uno por uno.

Que un certificado inventado a mano valga para esto es exactamente lo que el
módulo dice de sí mismo: comprueba que la firma cuadra con el certificado,
**no** de quién es el certificado.

## Lo que sigue sin comprobarse, ahora de verdad

- **De quién es el certificado.** Exige la lista de confianza europea (TSL),
  que cambia y se descarga.
- **Si está revocado.** Exige OCSP o CRL, o sea red.
- **Los sellos de tiempo** (XAdES-T y por encima). Sin ellos, la fecha de firma
  la escribe quien firma y puede poner la que quiera; sirve para contrastarla
  con la vigencia del certificado, no para demostrar cuándo se firmó.
- **Si quien firma está autorizado a facturar por ese NIF.**

Traducido: el validador responde «¿ha cambiado alguien este documento después
de firmarlo?» y «¿la firma cuadra con el certificado que trae dentro?». No
responde «¿de quién es este certificado?». Un documento firmado con un
certificado que el propio remitente se ha inventado pasa todas las
comprobaciones —de hecho es lo que hacen los tests—, y el informe lo dice.

560 tests.
