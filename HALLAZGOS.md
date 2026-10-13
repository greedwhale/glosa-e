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

**Corregido el 12-10-2026: esto último era falso.** `BR-IG-*` y `BR-IP-*` son
los nombres que el esquematrón del CEN dio en UBL al IGIC y al IPSI desde 2017
hasta la 1.3.13. La 1.3.14 los cambió por `BR-AF-*` y `BR-AG-*`, que es lo que
traía el esquematrón oficial con el que se comprobó, el 26-08-2026, y CII los
había llamado así siempre. Está en «BR-IG y BR-IP sí existían», más abajo.

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

**Cerrado el 13-09-2026, y no a nuestro favor.** Lo que hacía el validador
oficial estaba escrito en su esquematrón desde siempre: BR-CO-17 admite hasta
**una unidad** de distancia entre la cuota y base por tipo, en cualquier
moneda. «Por la letra de BR-CO-17 tenemos razón» era falso: la letra que se
leyó fue la de la descripción, no la de la regla. El fichero sale ahora con
`IVA-CUOTA-REDONDEO`, una nota. Lo cuenta «107 casos en los que la norma decía
otra cosa», al final.

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
salir con su etiqueta. Es el mismo cuidado que se creyó que había fallado con
unos `BR-IG-*` inventados; no lo eran (corregido el 12-10-2026, en
«BR-IG y BR-IP sí existían», más abajo).

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

# La revocación

## Dos afirmaciones de la lista de arriba que resultaron falsas

La lista «lo que sigue sin comprobarse» que cierra el apartado anterior decía
que saber de quién es un certificado «exige la lista de confianza europea
(TSL), que cambia y se descarga», y que saber si está revocado «exige OCSP o
CRL, o sea red». Las dos son de la misma familia de error: **confundir de dónde
sale un dato con cuándo hay que ir a buscarlo.**

- Un ancla de confianza **no se consulta: se conoce**. El navegador no llama a
  nadie para saber qué es una autoridad raíz. Se instala una vez, como los
  esquemas XSD, y a partir de ahí encadenar es aritmética local.
- Una CRL **es un fichero**. Se baja una vez y contesta por todas las facturas
  de esa autoridad hasta que caduque. La red hace falta para conseguirla, no
  para usarla, que es una diferencia de la que depende la promesa entera del
  producto.

Lo que sí obliga a preguntar en el momento es OCSP, y por eso no se usa.

## Por qué CRL y no OCSP, con un dato de las muestras

Las dos contestan lo mismo y filtran cosas muy distintas. Una CRL es la lista
entera de anulados: al bajarla no dices qué certificado te interesa. Una
consulta OCSP lleva dentro el número de serie, o sea que le dice a la autoridad
qué factura estás mirando y cuándo te llegó.

Se fue a mirar qué publican de verdad los certificados de las muestras, en vez
de suponerlo:

| Muestra | CRL | OCSP |
|---|---|---|
| `gob_sample-factura-firmada-30` | `http://minister-…/PKI/crl.crl` | — |
| `gob_sample-factura-firmada-31` | la misma | — |
| `gob_sample-factura-firmada-32v1` | la misma | — |
| `gob_xades_122_facturae` | la misma | — |
| `gob_sample-facturae-firmada` (DNIe) | **ninguna** | `http://ocsp.dnie.es` |

O sea: con un DNIe **no hay forma de comprobar la revocación sin decirle al
emisor qué estás mirando**. No es una postura sobre privacidad, es lo que hay.
El validador lo dice con su propio código (`REVOCACION-SOLO-OCSP`) en vez de
esconderlo en un «no comprobado» genérico.

## El experimento decisivo, otra vez antes del código

El mismo método que con la firma: antes de escribir el módulo, comprobar que se
entiende el formato. Se fabricó con `openssl` una autoridad, un certificado y
una CRL de verdad, se revocó con motivo `keyCompromise` y se comparó lo que
`openssl crl -text` dice con lo que sacaba un lector escrito para la ocasión:
emisor, fechas, número de serie, motivo, `cRLNumber`. Todo cuadró, y la firma
de la lista la verificó el mismo `pow(sig, e, n)` que ya estaba escrito.

Eso quedó como test permanente, saltado si no hay `openssl` en la máquina. Es
la única prueba del fichero que no se la escribe a sí misma: **un codificador y
un lector escritos por la misma mano pueden compartir el mismo malentendido
sobre el DER y darse la razón mutuamente**. `openssl` no comparte nada.

## El problema de las fechas

Es la parte que casi nadie cuenta y donde es fácil equivocarse en las dos
direcciones.

Que un certificado esté anulado **hoy** no invalida una factura firmada hace
dos años: en su momento valía, y rechazarla sería tirar una factura buena.
Salvo que lo anularan porque le robaron la clave, y entonces al revés: todo lo
que esa clave firmó pasa a ser sospechoso, **también lo anterior a la
denuncia**, porque quien la robó pudo firmar con fecha atrasada.

| Situación | Qué sale |
|---|---|
| Anulado antes de la fecha de firma | `REVOCADO`, error |
| Anulado por clave comprometida, sea cuando sea | `REVOCACION-COMPROMISO`, error |
| Anulado después, por otro motivo | `REVOCACION-POSTERIOR`, aviso |
| Suspendido (`certificateHold`) | `REVOCACION-SUSPENDIDO`, aviso |

Y la vuelta de tuerca: **la fecha de firma la escribe quien firma**. Sin sello
de tiempo de un tercero, comparar las dos fechas es fiarse de su palabra. El
mensaje lo dice; el tic verde no lo diría.

## La trampa de la respuesta negativa

«No está en la lista» solo significa «no está revocado» si la lista está
firmada por quien toca, es posterior al momento que se juzga y cubre a ese
certificado. Si falla cualquiera de las tres, la ausencia no prueba nada, y es
justo ahí donde un validador tiene la tentación de pintar el tic verde.

Se dice «no se sabe» —nunca «vigente»— cuando la lista no la firmó quien dice,
cuando su emisor no tenía `cRLSign`, cuando es incremental (delta), cuando está
acotada a otra clase de certificados, cuando trae una extensión crítica que no
sabemos leer, cuando es anterior a la firma o cuando está vencida.

La delta es la más traicionera porque **parece una lista normal**: solo trae los
cambios desde otra, así que quien la lea como completa dará por vigente a todo
el que no aparezca. Sí puede acusar; lo que no puede es absolver, y esa
asimetría está escrita en el código.

## Un error que se coló y lo cazó una prueba

La primera versión recorría todas las listas buscando el número de serie, que
parece lo prudente. Es lo contrario: **una suspensión que se levanta desaparece
de las listas siguientes**, así que una lista vieja resucitaría una anulación
que ya no existe. Manda la más nueva, y solo ella; las demás solo se consultan
cuando la más nueva es una delta y por tanto no puede absolver.

## Sobre los tests, y sobre el arnés de los tests

58 tests nuevos. Los nueve mecanismos de defensa se desactivaron uno por uno
para comprobar que alguna prueba se pone roja: los nueve están cubiertos.

Con una vuelta que merece anotarse. La primera pasada del arnés dijo que dos
defensas no las vigilaba nadie. Era mentira del arnés: parcheaba
`revocacion.comprobar`, pero el fichero de pruebas hace `from
validador.revocacion import comprobar` y se queda con su propia referencia, así
que el sabotaje no llegaba a probarse. **El arnés que comprueba las pruebas
también hay que comprobarlo.**

## Tres fallos propios, encontrados con sondas

1. **Las extensiones del certificado no se guardaban.** Una sustitución de
   texto falló en silencio y `Certificado.extensiones` quedaba siempre vacío.
   Los 593 tests seguían en verde porque nadie lo usaba todavía; lo cazó una
   sonda contra un certificado real de `openssl` que sí traía
   `cRLDistributionPoints` y del que salía una lista vacía.
2. **El `authorityInfoAccess` se leía un nivel por encima**, así que la
   dirección OCSP del DNIe no aparecía nunca. Misma sonda, mismo momento.
3. **La comprobación del navegador «el paquete validador importa» llevaba una
   lista de módulos escrita a mano** y se quedó corta: salía en verde con un
   wheel viejo instalado y el fallo aparecía tres pruebas más abajo disfrazado
   de `ModuleNotFoundError`. Ahora recorre el paquete instalado y los importa
   todos.

## En el navegador

19 de 19 comprobaciones en verde, dos de ellas nuevas: se fabrica una CRL
firmada dentro del propio navegador, se lee, se verifica su firma, se le cambia
un byte y se comprueba que deja de valer; y se comprueba que una lista
incremental no da a nadie por vigente. 4,8 ms y 8,5 ms.

651 tests.

# Decir en qué se ha confiado

## El silencio no puede seguir haciendo de aprobado

Hasta aquí este informe solo sabía hablar de lo que está mal. Con las anclas de
confianza eso deja de valer, y no por elegancia: **que una firma llegue a una
autoridad no es la ausencia de un problema, es una decisión** —creerle a esa
autoridad— y quien la toma es el almacén, no quien lee el informe. Una decisión
tomada por otro solo es aceptable si se declara.

De ahí un tercer nivel junto a `ERROR` y `AVISO`: `NOTA`. No es un fallo ni un
riesgo; es lo que se ha dado por bueno y con qué.

```
[CONFIANZA-ANCLA] La firma de «Talleres Paco SL» llega a «CA intermedia» en 2
eslabones. Esta validación se fía de esa autoridad porque es un ancla instalada
en anclas/intermedia.cer, con huella SHA-256 EE:CA:8D:AA:…

[CONFIANZA-REVOCACION] No consta anulado ningún certificado de la cadena: se ha
comprobado 1 certificado contra la lista de «CA intermedia», publicada el
2026-09-18. Una lista solo responde por lo que se sabía el día que se publicó.
```

Las notas van **antes** que las quejas: dicen sobre qué base se ha juzgado, y
eso se lee antes que el juicio. Enterradas debajo de cuatro errores no las
vería nadie, y son justo lo que hay que ver para saber si el resultado
significa algo.

## La huella entera, aunque ocupe

Es lo que hace la validación **reproducible**. Quien guarde ese informe puede
demostrar años después contra qué se contrastó, que es lo que pide una
inspección y lo que ninguna captura de pantalla de un tic verde puede dar. Con
`--solo-errores` desaparece, como los avisos.

## La procedencia, que es la mitad que importa

La ruta de un fichero no le dice nada a quien no instaló ese fichero. Por eso
`Almacen` acepta una procedencia declarada, y manda sobre la ruta:

    Almacen(carpeta, procedencia="viene con esta página")

## Por qué esto cambia la decisión sobre el navegador

En el repositorio, la razón para no traer anclas puestas era que **quien
controle ese fichero controla a quién cree el validador**. En la página web ese
argumento no aplica: **quien pueda servir la página ya es dueño del validador
entero.** El código es Python que llega por el mismo canal; alguien capaz de
cambiar el fichero de anclas puede cambiar `firma.py` para que devuelva «todo
bien» y ahorrarse el rodeo.

O sea que no traerlas no compra seguridad. Compra que la comprobación no se
haga nunca —porque nadie va a buscar e instalar un certificado raíz antes de
soltar una factura— y entonces el informe dice «sin errores» habiéndose saltado
la mitad que más importa.

El único camino de verdad malo es el intermedio: **traerlas y no decirlo**. Eso
fabrica confianza en silencio, que es exactamente lo que este validador existe
para no hacer. De ahí que la nota se escribiera **antes** de meter la primera
ancla en la página, y no después.

Y la asimetría que conviene no perder: **anclas sí, listas de revocación no.**
Un ancla es conocimiento que dura décadas; una CRL es una noticia que caduca en
días. Traer CRL con la página sería repartir una foto vieja de quién está
anulado, que es justo lo que no sirve.

## Sobre los tests

Siete nuevos, y el orden importa: la nota es una afirmación, así que lo que hay
que probar no es solo que aparezca, sino **que no aparezca cuando no toca**.

- Que dice a qué ancla llega, en cuántos eslabones y con qué huella.
- Que dice de qué fichero salió.
- Que una procedencia declarada tapa a la ruta, y que la ruta no se cuela.
- Que un certificado que es su propia ancla se cuenta como tal y no como cadena.
- Que **una cadena que no llega a ningún ancla no deja ninguna nota**: lo peor
  posible sería una línea tranquilizadora sobre una firma que no se ha podido
  atribuir a nadie.
- Que un certificado anulado no lleva la nota de «no consta anulado».
- Una sola nota de revocación por firma, aunque se comprueben varios eslabones:
  en un lote de doscientas, una línea por certificado deja de leerse.

Quitando la línea que emite la nota, cinco pruebas se ponen rojas. Comprobado.

## En el navegador

20 de 20. La comprobación nueva es **crítica** y monta el caso de verdad: un
almacén con `procedencia="viene con la pagina"`, y se exige que el informe la
diga, que lleve la huella y que **no** se cuele la ruta del disco virtual. Es
la condición que hace aceptable traer las anclas puestas, así que si se rompe,
se rompe la decisión de producto entera.

659 tests.


# De dónde salen las anclas

## La pregunta de debajo

Encadenar hasta un ancla contesta «de quién es este certificado». Debajo hay
otra, y es la que decide si lo anterior significa algo: **¿de dónde ha salido
esa ancla?** Es el único sitio de este validador donde equivocarse no produce
un error, produce un aprobado.

La respuesta fácil —recopilar raíces de por ahí— es exactamente el problema:
**quien elige el montón elige a quién cree el validador**. La respuesta
correcta ya existe: el artículo 22 de eIDAS obliga a cada Estado a publicar,
firmada y en formato procesable, la lista de sus prestadores cualificados
(ETSI TS 119 612, la TSL). No hay que inventar el conjunto: hay que leerlo.

## Dónde acaba la cadena, que es lo bonito

| Quién | Dice | Se comprueba contra |
|---|---|---|
| El **DOUE** | dónde está la lista de listas y qué la firma | nada: es el final |
| La **LOTL** | dónde está la lista de cada país y quién la firma | la huella del DOUE |
| La **lista del país** | qué autoridades son cualificadas | lo que dice la LOTL |

La raíz de toda esta confianza no es un servidor: es **un documento del Diario
Oficial**, con número de expediente y fuera de internet. Encaja con la idea de
la que sale el proyecto entero: las reglas son públicas.

Por eso `montar` **se niega** a producir anclas de una lista cuya firma no ha
comprobado, y por eso `--segun` exige `--firmante` para la propia LOTL:
creérsela porque sí sería elegir en quién confiar a partir de un fichero sin
verificar. Se niega, no avisa. Un aviso deja la decisión en manos de quien
tiene prisa.

## Verificar la dirección era el punto, y menos mal

Me había comprometido a comprobar las direcciones contra la fuente en vez de
escribirlas de memoria, porque en este mismo repositorio ya había constancia de
una huella inventada. Resultado: la del ministerio que yo tenía en la cabeza
—`sede.serviciosmin.gob.es`— **ya no existe**, responde con una redirección
permanente.

Las buenas, verificadas: la LOTL en `https://ec.europa.eu/tools/lotl/eu-lotl.xml`,
publicada con sus seis certificados y sus huellas en el **DOUE C/2026/1944, de
15 de abril de 2026**; y la española en `https://tsl.digital.gob.es/TSL.xml`.

La conclusión de diseño es más fuerte que la anécdota: **la dirección de la
lista de un país no se escribe en ninguna parte del programa**. La dice la
LOTL, que es quien tiene autoridad para decirla, y `--ver-tsl` la enseña.

## Una lista no es un montón de certificados

Es la trampa del formato, y tiene la misma forma que ya tenía la revocación:
**un servicio es un certificado con un estado y una fecha**. Quien se quede
solo con los certificados monta un conjunto que incluye a las autoridades
retiradas.

Se filtra por tipo —solo lo que emite certificados cualificados; ni sellos de
tiempo ni servicios de estado— y por estado, se quitan los repetidos (una
autoridad que emite para firma y para sello aparece dos veces con el mismo
certificado) y se cuenta lo que se deja fuera, incluidos los servicios
identificados **sin** certificado, que son legales y no dan ancla.

Lo que queda abierto y está dicho: una autoridad retirada hoy firmó
certificados buenos hace dos años. Sus facturas antiguas salen como «no llega a
ninguna autoridad conocida» —aviso, no error— y el mensaje ya avisa de que eso
no se distingue de que falte un certificado. Cerrarlo es darle al almacén una
ventana de validez por ancla.

## La procedencia viaja con los ficheros

Montar deja un `PROCEDENCIA.txt`, y su primera línea acaba en el informe de
cada factura:

```
de la lista de confianza de ES, publicada por Ministerio para la
Transformacion Digital el 2026-08-01
```

En un fichero y no en el código de quien construye el almacén, a propósito. Si
hay que acordarse de pasarla en la llamada, el día que alguien copie la carpeta
se queda sin ella, y un conjunto de anclas que no dice de dónde viene es
exactamente lo que habíamos quedado en no repartir.

## Dos fallos, y cómo salieron

**`"".join(texto.split())` se come los espacios de dentro.** Sirve para el
base64 de un certificado y es destructivo para un nombre: la lista española
habría acabado diciendo «FABRICANACIONALDEMONEDAYTIMBRE» en el informe de cada
factura. No sale con datos inventados de una sola palabra; sale en cuanto el
nombre lleva un espacio, o sea siempre. Lo cazó la primera prueba que usó un
nombre realista, que es el argumento entero a favor de escribir los datos de
prueba como son y no como es cómodo.

**El aviso de SHA-1 disparaba contra el propio ancla.** La regla excluía las
raíces autofirmadas —su firma no la comprueba nadie, así que su algoritmo da
igual—, y eso es lo mismo que excluir el ancla **solo mientras las anclas son
raíces**. Una TSL no publica raíces: publica las CA emisoras, que están
firmadas por alguien. Montado el conjunto desde la lista, el validador avisaba
de la autoridad de media España por un algoritmo que aquí no se usa para nada.
Sospechado al leer el formato, reproducido con una sonda antes de tocar nada, y
la prueba de regresión se pone roja al deshacer el arreglo.

## Sobre las pruebas

Lo que hay que probar aquí no es que lea el XML: es que **se niegue**. Hay un
constructor de listas de confianza que firma de verdad, con la clave privada a
mano para poder falsificar, y con él se fabrican los casos que importan:

- una lista sin firma;
- una lista firmada por otro;
- una lista tocada después de firmarla, y el caso concreto de colarle una
  autoridad a una lista buena;
- una firma hecha con una clave que no es la del certificado que enseña;
- **una firma auténtica que solo cubre la cabecera**: verifica perfectamente y
  no garantiza nada, porque la lista de autoridades se puede cambiar entera;
- montar sin haber dicho quién tenía que firmarla.

Deshaciendo cada defensa por separado, la prueba que le corresponde se pone
roja. Comprobado una por una.

Lo que ninguna de esas pruebas puede dar es que el fichero de verdad tenga la
forma que tiene mi constructor: un constructor y un lector escritos por la misma
mano comparten los malentendidos y se dan la razón mutuamente. Eso se cerró
bajando las listas reales. Ver la sección siguiente: sacaron cuatro fallos y una
noticia.

## En el navegador

22 de 22, trece críticas. Las dos nuevas lo son, y una depende de lo más frágil
de esa compilación: una TSL se verifica **canonicalizándola**, y allí libxml2
es 2.9.10 frente a 2.11.9 en local. Un byte de diferencia no daría un falso
aprobado —daría una lista rechazada y una página sin anclas—, pero daría igual
al revés: la comprobación no se hace. Verificar y montar cuesta 20,8 ms allí;
rechazar una manipulada, 14,1 ms.

720 tests.


# Lo que enseñaron las listas de verdad

Bajadas el 27 de agosto de 2026: la lista de listas europea (478 KB) y la
española (3,0 MB). Las dos verifican —la primera contra las seis huellas del
Diario Oficial, la segunda contra lo que dice la primera— y de la española
salen **87 anclas de 33 prestadores**. El ministerio publica además el SHA-256
de su lista y cuadra.

## La noticia: 46 autoridades que este validador no sabe usar

De los 129 servicios concedidos que emiten certificados cualificados, **46
traen un certificado de curva elíptica**. Este validador solo verifica RSA, así
que esas 46 autoridades cualificadas se quedan fuera del conjunto de anclas.

No es un fallo de la lista ni del certificado: **el corto es este validador**, y
ahora se dice con esas palabras en `--ver-tsl`, en el resumen de
`--montar-anclas` y en el manifiesto. Se separa a propósito de las retiradas
porque no es la misma noticia: una retirada dejó de ser cualificada, una que no
sabemos usar lo sigue siendo. Es, con diferencia, lo que más cobertura añadiría
de una sola vez.

## Cuatro fallos que ninguna lista inventada iba a sacar

Los cuatro son de los que no dan error: dan un resultado que parece bueno.

1. **El puntero de un país apuntaba al PDF.** Once países aparecen dos veces en
   la lista de listas —versión legible y XML—, la del PDF primero, y España es
   uno de los once. «La primera que case» mandaba a bajar un PDF y daba por
   buenos los certificados de esa entrada confiando en que fueran los mismos
   que los de la otra: hoy lo son, y nadie lo ha prometido.

2. **La lista de España pasaba por lista de listas**, porque trae un puntero de
   vuelta —el formato se lo exige— y yo las distinguía por «¿trae punteros?».
   `--ver-tsl` enseñaba ese puntero en lugar de las 243 autoridades. Manda el
   tipo que la lista declara de sí misma, que va dentro de lo firmado.

3. **«Sin certificado: 425».** Un servicio sano trae varias identidades —el
   certificado, el nombre del sujeto, la huella de la clave— y yo contaba las
   que no eran un certificado: dos de cada tres en cada servicio correcto. Un
   número enorme, sin significado, y que además **tapaba** la noticia de las 46.
   Se cuentan servicios, que es lo que se pierde: autoridades, no líneas.

4. **«DER truncado» sobre un certificado impecable.** Leer el punto de una curva
   elíptica como si fuera una pareja de enteros daba tres errores distintos,
   todos acusando al fichero. Ahora se mira el OID del algoritmo antes de leer
   la clave. Y hay una excepción propia, `ClaveNoSoportada`, para poder
   distinguir «este fichero está roto» de «este fichero está bien y el corto soy
   yo», que no llevan a la misma acción.

Los cuatro se reprodujeron sobre el fichero real antes de tocar el código, y
cada uno tiene una prueba que se pone roja al deshacer el arreglo.

## La comprobación que salió al revés

Ninguna de las cinco muestras firmadas del Gobierno encadena hasta las 87
anclas, y el motivo no es el conjunto: **cada una lleva dentro un solo
certificado, el del firmante, sin ningún intermedio**. Sin intermedio no hay
cadena que construir por completo que esté el almacén, y el informe ya lo decía
con esas palabras.

La del DNIe tiene además el hueco temporal, y es el ejemplo real de lo que
estaba anotado como hipótesis: su raíz figura en la lista como **retirada el 14
de septiembre de 2023**. La factura es anterior y era buena entonces.

## Un detalle que confirma un arreglo hecho a ciegas

Cinco de cada seis anclas de la lista española **no son autofirmadas**. Es
exactamente lo que decía la sospecha que llevó a arreglar el aviso de SHA-1:
una lista de confianza publica las CA emisoras, no las raíces. Estaba
arreglado antes de poder comprobarlo; ahora está comprobado.

720 tests, 22 de 22 en el navegador.


# La curva elíptica

## Por qué, y no por completitud

46 de las 129 autoridades cualificadas concedidas de la lista española firman
con curva. Sin ECDSA, un tercio de las autoridades de España se quedaba fuera
del almacén de anclas y sus facturas salían como «no llega a ninguna autoridad
conocida», que no era el motivo. El conjunto pasa de **87 a 133 anclas**.

Empíricamente son tres curvas —P-256, P-384 y P-521— y ninguna brainpool. Se
soportan esas tres y se dice claramente cuando aparece otra: escribir soporte
para curvas que nadie usa es código que nadie ejerce.

## Lo que cazó la comprobación de las constantes

Los parámetros de las curvas van escritos a mano, y una errata **no da un
error**: da «esta firma no verifica», indistinguible de una firma falsificada.
Antes de escribir una línea de ECDSA se comprobaron con la definición: que el
generador esté en la curva, y que n·G sea el punto del infinito.

Saltó a la primera. La `n` de P-521 salía de 517 bits en vez de 521: se habían
perdido dos dígitos en un corte de línea. Escrita ahora como `"01" + "f"*64 +
cola`, porque contar efes a ojo es exactamente lo que falló.

## La velocidad, que aquí sí importa

En coordenadas afines cada suma de puntos paga un inverso modular y una
verificación son cientos de sumas: P-521 tardaba 200 ms, y esto corre también
dentro del navegador. En jacobianas —un solo inverso al final— más el truco de
Shamir para las dos multiplicaciones a la vez: **33 ms**.

El precio es que las fórmulas dejan de leerse solas. La defensa es una prueba
que las contrasta, curva por curva y con escalares al azar, contra la versión
lenta y evidente escrita en el propio fichero de pruebas.

Medido en WebAssembly: P-256 10 ms, P-384 16 ms, P-521 29 ms. Prácticamente lo
mismo que fuera, que no era obvio.

## Dos trampas

**La firma viene en dos formatos.** DER dentro de un certificado o una CRL;
los dos números pegados y rellenos con ceros dentro de una firma XML.
Confundirlos no da un error de formato: daría una firma buena que no verifica.
Hay una prueba que exige que cada codificación se rechace en el sitio de la
otra, con material de `openssl`.

**El resumen se recorta por la izquierda** cuando es más largo que la curva.
P-256 firmado con SHA-384 existe, y quien no recorte verifica mal justo esas.
Hay un vector de `openssl` para ese caso, y al deshacer el recorte se pone
roja.

## La fuerza de la clave, que había que separar

256 bits de curva equivalen a unos 3072 de RSA. Con un solo mínimo —los 2048 de
RSA— **toda** clave de curva saldría marcada como corta, que es justo al revés
de la realidad; y ahora que son un tercio de las autoridades, el informe se
habría llenado de un aviso falso.

## Una prueba que no probaba nada, y qué se hizo

Escribí una comprobación de que un punto fuera de la curva se rechaza al
verificar. Pasaba con y sin la comprobación: con un punto de fuera la
aritmética devuelve algo, ese algo no coincide con `r` y la firma se rechaza
igual. O sea que la prueba pasaba por casualidad.

La comprobación que sí manda está al **leer el certificado**: uno cuya clave
dice ser de una curva y no lo es no se llega a construir. Ahí sí se pone roja
al quitarla, y ahí es donde está ahora la prueba. La de `_verificar_ecdsa` se
queda como defensa a mayores, dicho en su sitio y sin fingir que está cubierta.

## Fuera del círculo

`openssl` firma con cada curva y se verifica aquí; se monta además una
autoridad de curva entera —CA P-384 que emite una hoja P-256, la revoca y
publica su CRL— para comprobar que `cadena.py` encadena firmas ECDSA y que
`revocacion.py` se cree una CRL firmada con ECDSA. Son los dos sitios donde el
despachador tenía que enterarse de que la clave no es RSA.

783 tests, 24 de 24 en el navegador (15 críticas).


# La fecha de la firma manda sobre el ancla

## El hueco que quedaba

Una factura se guarda años, y la autoridad que la firmó puede haber dejado de
ser cualificada desde entonces. Eso **no** invalida la factura: en la lista
española hay 114 autoridades retiradas entre 2016 y 2026 —135 certificados— y
todas emitieron certificados buenos mientras estuvieron.

Montando solo lo concedido hoy, esas facturas salían como «no llega a ninguna
autoridad conocida». Ni era verdad ni era el motivo, y el aviso no distinguía
un conjunto incompleto de un certificado que nadie avala.

## Ampliar el conjunto sin ampliar la confianza

Es el problema de verdad de esta parte. Meter 135 certificados más en la
carpeta de anclas es, literalmente, aumentar en 135 la lista de autoridades en
las que el validador cree. Lo que lo hace aceptable es que **cada una solo vale
dentro de su ventana**, y lo que hace que eso se sostenga es la forma de
guardarlo:

- van en una subcarpeta, `anclas/retiradas/`, visible para cualquiera que abra
  la carpeta;
- su fecha va en una tabla aparte, `ESTADOS.tsv`;
- **si falta la fila, el ancla no se usa.**

Esa última es la que importa. Sin ella, copiar la carpeta a medias —o soltar un
`.cer` a mano en la subcarpeta— convertiría autoridades caducadas en
autoridades de confianza sin fecha de caducidad, y nada en el informe lo diría.
Hay una prueba que borra la tabla y exige que las retiradas queden inertes, y
otra igual en el navegador, marcada como crítica: es una comprobación de
**sobre**-confianza, y esas no avisan solas.

## La asimetría de la ventana

Solo se comprueba el final, no el principio, y parece un descuido.

El final es real: si el Estado retiró a una autoridad el 14 de septiembre de
2023, lo firmado después no está amparado por ella.

El principio no dice lo que parece. Casi todas las anclas concedidas de la
lista española ponen 2016-06-30, que no es el día en que esa autoridad se
volvió fiable: es el día en que empezó a aplicarse eIDAS. Rechazar por ahí
tiraría todas las facturas anteriores a 2016 de autoridades que existían y
valían, contestando a una pregunta que la lista no responde.

## Dos cosas que se dicen y antes no

**Cuando no ampara**, la queja tiene código propio, `CADENA-RETIRADA`, y no se
confunde con «no la reconozco»: aquí sí sabemos quién es la autoridad y sabemos
que ya no valía. Son diagnósticos distintos y llevan a acciones distintas.

**Cuando sí ampara**, se declara en la nota: «se acepta porque la factura es
anterior, no porque siga vigente». Aceptar una firma por una autoridad que ya
no lo es, aunque sea correcto, es una decisión más discutible que la normal, y
quien lea el informe tiene que poder verla en vez de deducirla.

## Un detalle de orden que sí se puede probar

Las anclas fuera de ventana se descartan **antes** de encadenar, no después.
Con dos instaladas —una vigente y una retirada— y la firma fuera del plazo de
la retirada, descartar al final haría que la mala tapara a la buena: el
resultado sería un aviso en vez de una firma correctamente atribuida. Hay una
prueba que lo fija y se pone roja al mover el filtro.

## Lo que esto no arregla

Las cinco muestras firmadas del Gobierno siguen sin encadenar, y ahora se sabe
con certeza que no es por el conjunto: **cada una lleva dentro un solo
certificado, sin intermedios**. La del DNIe, además, la emitió «AC DNIE 001»,
una subordinada que la lista no nombra —la lista publica su raíz, «AC RAIZ
DNIE», retirada el 14 de septiembre de 2023—. Sin el intermedio no hay cadena
que construir por completo que esté el almacén.

797 tests, 25 de 25 en el navegador (16 críticas).


# El sello de tiempo, y las tres trampas del RFC 3161

## Por qué era el primero de la lista

La fecha de una firma salía de `SigningTime`, que la escribe quien firma. De
ese dato cuelgan las dos comprobaciones más caras del validador —la vigencia
del certificado y la revocación—, así que las dos se esquivan con el mismo
gesto: fechar hacia atrás. Un certificado caducado o anulado ayer firma hoy una
factura que dice ser del año pasado, y las dos reglas la dan por buena.

## Las tres trampas

Ninguna sale de leer la norma; las tres salieron de contrastar el código contra
un `TimeStampToken` hecho con `openssl`.

**Uno: la firma no va sobre los atributos tal y como vienen.** En el DER los
atributos firmados llevan la etiqueta `[0]`; lo que se firma es esa secuencia
reetiquetada como `SET OF`. Esta es benigna —falla en todos los sellos del
mundo, y a gritos—, pero hay una prueba que exige que la forma ingenua **no**
verifique, porque el día que alguien la «simplifique» conviene que se entere.

**Dos: el algoritmo de resumen no sale de donde parece.** El
`signatureAlgorithm` del firmante es casi siempre `rsaEncryption` a secas, sin
decir con qué resumen se hizo. El bueno es el `digestAlgorithm`, que va aparte.

**Tres, y esta sí falla en silencio hacia el lado malo: el resumen por defecto
del certificado no es el mismo en las dos versiones del atributo.** En
`SigningCertificate` es SHA-1 siempre y no se escribe; en
`SigningCertificateV2`, SHA-256. Escribir un único valor por defecto —lo
natural, y lo que yo escribí— hace que la comprobación no case en ningún sello
moderno. Se vio contrastando contra el vector: con SHA-256 casa, con SHA-1 no,
y hay una prueba que lo fija en las dos direcciones.

## La comprobación que no es criptografía

RFC 3161 §2.3 pide que el certificado de la autoridad lleve la extensión de uso
extendido con `id-kp-timeStamping` y **nada más**. Es la comprobación que más
pesa y la única que no es aritmética: sin ella, cualquiera con un certificado de
firma corriente se fabrica la fecha que quiera.

Que la norma sea estricta no la hace realista, así que se contrastó contra la
lista española. De los **69 certificados de sellado concedidos**, 60 son
certificados de firma —los que sellan— y los 60 llevan la extensión con ese uso
y solo ese. Los otros nueve son autoridades de certificación: no sellan nada, y
la regla no les aplica porque lo que se comprueba es el certificado que **firma
el sello**, que siempre es una hoja. De esos nueve, seis la llevan y tres no.

Hay un vector dedicado: un sello perfectamente firmado, cuya firma verifica y
cuyo resumen cubre lo que dice cubrir, emitido por un certificado sin permiso.
Se rechaza, y es la única prueba que se pone roja si alguien afloja esa
comprobación. La misma va marcada como crítica en el navegador.

## Que la fecha llegue abajo, que era lo que importaba

Leer el sello y escribir una nota bonita no arregla nada. El agujero se cierra
cuando la fecha acreditada **sustituye** a la declarada, y eso cambia
veredictos: una anulación posterior a la firma pasa de **aviso** —«esa fecha la
escribe quien firma»— a **nota** —«el sello acredita que la firma ya existía»—.
Mismo hecho, distinta confianza, y por eso distinta gravedad.

Los siete cables entre `sellos.py` y el resto se comprobaron uno a uno
deshaciéndolos y exigiendo que alguna prueba se pusiera roja. **Seis lo
hicieron; uno no.**

## El que no: una prueba que no probaba nada

La regla dice que con varios sellos buenos manda **el más antiguo** —lo que un
sello demuestra es «ya existía entonces», así que el más antiguo es la cota más
ajustada—. La prueba montaba dos sellos y exigía que ganara el menor.

Cambiando `min` por `max` la prueba seguía verde. Los dos sellos se pedían
seguidos, la TSA de pruebas sellaba con precisión de un segundo, y los dos caían
en el mismo instante: `min` y `max` daban lo mismo. Estaba comprobando una
igualdad consigo misma.

Se arregló poniendo la TSA de pruebas a sellar con milisegundos, lo que además
cubrió de paso la lectura de la fracción de segundo del `genTime`, que estaba
escrita y no la miraba nadie. Ahora `max` se pone roja.

Es la segunda vez en este proyecto que aparece una prueba que pasa con y sin lo
que dice probar. Las dos veces la encontró el mismo método: deshacer la defensa
a propósito y exigir el rojo.

## Un hueco que abrió el propio arreglo

Con la fecha del sello mandando, apareció un caso que antes no se podía ni ver:
la fecha declarada cae dentro de la vigencia del certificado, el sello cae
fuera, y nadie se quejaba. `firma.py` mide la vigencia contra la declarada, que
es lo único que tenía.

Eso es exactamente la maniobra contra la que sirve un sello. Se añadió un aviso
—no un error: sellar tarde es legítimo y pasa— que dice que lo único acreditado
de esa firma es posterior a la caducidad, y que si se firmó antes eso solo lo
dice la fecha que escribe quien firma.

## Lo que sigue abierto

**De quién es la autoridad de sellado.** El sello se comprueba entero; que ese
certificado sea de una TSA cualificada, todavía no. Un sello se puede fabricar
entero, autoridad incluida, y pasa todas las comprobaciones. La nota que emite
el validador lo dice con todas las letras en vez de dar un visto bueno a secas,
que es la misma política que se siguió con la firma antes de que existiera
`cadena.py`: primero que cuadre, después de quién es.

849 tests, 27 de 27 en el navegador (18 críticas).


# Las anclas de sellado: dos carpetas, y por qué no una

El sello de tiempo se comprobaba entero salvo lo principal: **de quién era la
autoridad**. Sin eso, un sello se fabrica completo —autoridad incluida— y pasa
todas las comprobaciones. La fuente estaba donde las demás: la lista del Estado
publica 69 servicios de sellado concedidos.

## Por qué no comparten carpeta

Parecía una decisión de orden y es de confianza. El almacén recorre su carpeta
entera con `rglob`, así que meter las de sellado en un subdirectorio de
`anclas/` las convierte en anclas de firma.

Los números de la lista española lo dejan claro. De las **121 anclas de sellado**
que salen de ella, **solo 2 están también entre las de firma**. Las otras 119
son autoridades cualificadas para sellar el tiempo y no para avalar la firma de
una factura, y **once son autoridades de certificación**: juntas, esas once
pasarían a poder emitir certificados que el validador aceptaría como firmantes.
Nadie lo habría decidido y nada lo diría.

Hermanas y no anidadas, además, porque el error posible cambia de lado. Anidadas,
el olvido es una exclusión que alguien quita y once autoridades se cuelan en
silencio. Al lado, el olvido es no copiar la carpeta, y entonces no se reconoce
ninguna autoridad de sellado y **se dice**. Ese es el lado por el que hay que
fallar.

Para que nadie tenga que acordarse, el almacén encuentra a su hermana solo:
`anclas/` busca `anclas-sellos/` al lado. Y las dos se montan con la misma orden
y de la misma lista, porque dos órdenes serían dos conjuntos con dos fechas y
uno de los dos se quedaría sin montar el día que alguien tuviera prisa.

## Un mensaje que mandaba a buscar un ciclo que no existe

La primera versión sacaba al informe el motivo interno de `construir`, y sobre
un sello desconocido salía **«cadena circular»**. No es un fallo del motivo: es
literalmente lo que pasa cuando el sello trae su propia autoridad dentro y esa
autoridad no es un ancla, o sea el caso corriente de «no la conozco». Pero a
quien lee el informe le manda a buscar un ciclo.

Ahora dice dónde se queda: «la cadena se queda en «AC de sellos de prueba», que
no está entre ellas». El motivo interno solo sale cuando dice algo —cuando el
ancla estaba retirada—. Hay una prueba que exige que la palabra «circular» no
aparezca.

## Y una que no se veía desde dentro

`--montar-anclas` escribe ahora una carpeta hermana, y `.gitignore` decía
`anclas/`, que no la cubre. La primera vez que alguien montara el conjunto se le
habrían versionado 120 certificados de autoridades de sellado sin enterarse, en
un repositorio cuya regla es que las anclas no se versionan **nunca**. El patrón
lleva comodín desde antes de que eso pudiera pasar.

860 tests, 28 de 28 en el navegador (19 críticas).


# Contra sellos de verdad: dos defectos y una confirmación

## Qué se pudo conseguir

Facturae con sello **no hay publicadas**. Una factura sellada lleva datos
reales de una empresa real, así que nadie las sube; en el índice de código de
GitHub no aparece ninguna. Así que se hicieron dos cosas distintas.

**Sellos españoles reales, aunque no de facturas.** El repositorio del cliente
de firma oficial del Estado, `clienteafirma`, trae documentos XAdES-XL y
XAdES-A firmados de verdad, sellados por «Sello de tiempo TS@ - @firma» entre
2015 y 2019. Son 18 tokens; los 18 se leen y los 18 verifican.

**Una factura española real con un sello cualificado real.** A las facturas
firmadas oficiales de `facturae.gob.es` se les pidió un sello a la TSA pública
de la ACCV, que está en la lista de confianza del Estado. Camino entero
recorrido sobre una factura del Gobierno de 2007: sello leído, sello
verificado, autoridad contrastada contra las anclas montadas de la TSL.

De la factura no sale nada del ordenador: a una TSA se le mandan 59 bytes con
el resumen del valor de la firma.

## Defecto 1: un sello que no se sabe leer no es un sello que no está

XAdES admite el token de dos formas: en base64 —`EncapsulatedTimeStamp`— y el
mismo sello escrito como XML. Aquí solo se lee la primera, que es lo razonable.
Lo que no era razonable es que la segunda se ignorara **en silencio**.

Sobre `XAdES-XL_con_sello_xml.xml`, que lleva tres sellos del Estado dentro, el
informe decía: «La firma no lleva sello de tiempo de un tercero». Es falso, y
es falso en la dirección mala: da a entender que la fecha no la respalda nadie
cuando sí la respalda alguien, solo que no sabemos leerlo.

## Defecto 2: el que colgaba del primero, y es peor

Al arreglarlo se vio que la frase no era exclusiva del caso XML: salía con
**cualquier** sello inservible —roto, ilegible, o copiado de otro documento—.
Una prueba escrita antes lo daba por bueno explícitamente.

Los dos casos acaban en la misma fecha y no en la misma noticia. A un documento
sin sello hay que ponerle uno; a uno que ya lo lleva, decirle que no lo lleva
manda a poner dos veces lo mismo y a no mirar el sello que falla. Ahora son
`SELLO-FALTA` y `SELLO-SIN-USAR`, con una prueba de cada una que exige que la
otra no aparezca.

## La confirmación: por qué las anclas van en dos carpetas

Esto ya estaba decidido y argumentado, y el argumento era abstracto: «once
autoridades de certificación pasarían a avalar firmas». El fichero real da el
caso concreto y al revés.

El sello de @firma lo firma un certificado que emite «DEFENSA-EC-WPG2016». Esa
autoridad **está entre las anclas de firma y no entre las de sellado**: el
Estado la publica como autoridad de certificación, no como autoridad de
sellado.

  · Separadas: «no consta que sea una autoridad de sellado cualificada». Cierto.
  · Juntas:    encadena, y el validador afirma que lo es. Falso.

Se comprobó copiando las dos carpetas en una y volviendo a preguntar. Hay una
prueba que lo fija en las dos direcciones —que no encadene separadas, y que sí
encadenaría juntas—, porque un test que solo comprueba la mitad buena no
distingue una defensa que funciona de una que no está.

## Lo que no se encontró

Ningún fallo de lectura: 18 de 18 tokens reales leídos, 18 de 18 verificados,
ninguna excepción. La reetiquetación a `SET OF`, el resumen sacado del
`digestAlgorithm` y el SHA-256 por defecto del `ESSCertIDv2` —las tres trampas
que salieron de `openssl`— se comportan igual contra tokens de @firma y de la
ACCV, que no comparten nada con este código.

Tampoco cambió nada que no debiera: comparando cada factura antes y después de
sellarla, lo único que se mueve son los cuatro códigos del sello. La firma
original sigue verificando byte a byte, que es lo que tiene que pasar cuando el
sello va donde XAdES lo pone.

865 tests, 28 de 28 en el navegador (19 críticas).


# EDIFACT: lo que enseñó conectar el cuarto formato

## Lo que estaba peor de lo que decía el aviso

El README decía que un EDIFACT «se detecta y se contesta *no se ha podido
validar*». Eso era verdad para la tira de toda la vida. Para los **ejemplos
oficiales de la Comisión Europea** no: se publican en ISO 20625 —el mismo
mensaje escrito como XML— y salían por la puerta de «formato no reconocido».

El validador decía no saber qué era el fichero de referencia de uno de los
cuatro formatos que admite la ley. Y lo decía el propio README, sin enterarse,
porque nadie había pasado esos nueve ficheros por el validador.

## La parte que puede fallar sin dar error

Leer los segmentos es mecánico. Lo que no lo es: **EDIFACT no marca los
grupos**. Todo va al mismo nivel y quién cuelga de quién se deduce del orden.

```
LIN+1   QTY+47:100   MOA+203:18550   TAX+7+VAT+++:::21+S   LIN+2
```

Ese TAX es el de la línea 1 porque viene detrás del LIN y antes del siguiente.
Si se colgara del documento, no habría error de lectura por ninguna parte:
habría un desglose de IVA con una entrada de más, y una factura correcta
saldría descuadrada. O al revés, y una mala pasaría.

Por eso el algoritmo es una pila y no una lista de casos, y por eso hay una
prueba de que un ALC dentro de una línea —un descuento de línea, que trae su
propio TAX un piso más abajo— no se confunde con el IVA de esa línea.

## Los cualificadores no se copian: se comprueban

En EDIFACT el total sin impuestos y el importe de una línea son los dos un
`MOA`. Lo único que los distingue es el código de al lado: 389 y 203. Escribir
ese mapa de memoria es la forma más fácil de que un importe entre en las
cuentas por el sitio equivocado.

Se comprobaron haciendo la cuenta en los nueve ejemplos de la Comisión: el 79
es la suma de los 203 en los nueve, el 388 es el 389 más el 176 en los nueve.
Con eso, los nueve pasan ahora sin un solo error.

Lo mismo con el directorio de posiciones, y ahí los ficheros reales corrigieron
lo que estaba escrito de memoria: en el segmento TAX la cuarta posición es un
dato simple y el compuesto con el tipo impositivo es el **quinto**. Puesto en
la cuarta, el porcentaje del IVA se va de sitio en todas las facturas.
`TAX+7+VAT+++:::21+S` solo cuadra con la quinta.

## Lo que no se lee no se queda fuera: cierra el grupo

La tabla de qué cuelga de qué se dedujo de los nueve ejemplos de la Comisión.
Le faltaba media docena de segmentos que esos nueve no usan, y eso parecía
inofensivo: lo que no está en la tabla no se lee.

No es lo que pasa. Un segmento desconocido **cierra** el grupo abierto. Un
`PAC` —el embalaje de una línea— cerraba la línea, y el `MOA` de detrás dejaba
de ser el importe de esa línea para convertirse en un total de la factura. Sin
un solo error: una factura de almacén saldría con los importes de sus líneas
contados como totales.

Se contrastó contra la gramática D.96A de `bots-edi`, un proyecto de EDI ajeno
a este, y salieron once grupos que faltaban. La tabla de ahora es la unión: lo
que enseñan los ejemplos de la D.14B y lo que dice esa gramática de la D.96A.

De paso, esa gramática confirmó lo que sí estaba: `LIN` con sus `ALC`, `MOA` y
`TAX` dentro, `NAD` con sus `RFF` y `CTA`, `TAX` con su `MOA`, y los grupos de
totales después del `UNS`. Coincidir con una fuente que no es la tuya vale más
que volver a leerse la propia.

## Tres campos que el mapa no supo situar, y qué se hizo con ellos

El redondeo (BT-114) y el código del motivo de exención (BT-121) no aparecen en
ninguna muestra y no se pudo confirmar con qué código se escriben. Están en el
mapa como `SIN_MAPA`: una ruta válida que no encuentra nada nunca, con una
prueba de que de verdad no encuentra nada.

Es a propósito. Un cualificador inventado no da error: se traga el importe del
cajón de al lado y lo mete en las cuentas. No leerlo equivale a que no lo haya,
que es el caso de todas las facturas vistas; leerlo mal, no.

El tercero sí se situó, y de una forma que costó dos intentos. El motivo de una
exención no va dentro del grupo de impuesto sino suelto en un `FTX+AGM` del
documento, y lo único que lo ata a una categoría es que explica la que no
tributa. Al subir a buscarlo desde el grupo, el motivo del tipo exento se le
aparecía también a los tipos generales, y `EDIFACT_EXAMPLE2` salía con dos
`BR-S-10` inventados: acusado de llevar un motivo que no lleva. El vínculo lo
tiene que poner la ruta, porque el documento no lo escribe.

## Tres cosas que se saltaban en silencio, y ninguna es de EDIFACT

- **`codigo_unico.extraer` reventaba** con un `XMLSyntaxError` ante cualquier
  EDIFACT plano. Se comprobó en un árbol de trabajo del commit anterior para
  saber de quién era: era de antes, no de esta rama. Un fallo ajeno no se
  atribuye, y uno propio no se escapa.
- **Apuntar a una carpeta no recogía los `.edi`**, y el resumen contaba los
  ficheros que sí había mirado. Es la forma exacta de dejar a alguien creyendo
  que ha revisado un lote entero. Se recogen `.edi` y `.edifact`, y **no**
  `.txt`: una carpeta de facturas suele traer además un leeme, y recogerlo
  llenaría el informe de «formato no reconocido» sobre ficheros que nadie dijo
  que fueran facturas. Un `.txt` que sí lo sea se valida nombrándolo.
- **El navegador no dejaba ni elegir un EDIFACT.** El selector admitía `.xml` y
  `.xsig`, así que el cuarto formato era invisible ahí por mucho que el motor
  lo entendiera.

## Y dos frases que prometían de más

Es el peor fallo que puede tener un informe: lo que promete es de lo que se fía
quien lo lee.

La primera se contradecía en dos mitades —«**falta** el esquema de este
formato. Los que le tocan se llaman **(ninguno)**»— sobre algo que no tiene
esquema porque no es XML. Ahora es una nota, que es el nivel de lo que se ha
dado por bueno y con qué.

La segunda es la frase del final, la que enumera de qué se ha fiado quien lee.
Se apuntaba «se ha comprobado la forma contra el esquema XSD» en un lote de
puro EDIFACT, donde no se había mirado ninguno, y a la vez **no se apuntaba las
reglas EN 16931**, que sí se habían pasado. Prometía de más por un lado y de
menos por el otro, que son el mismo defecto.

## Lo que dijeron los ficheros que no ha escrito este proyecto

18 tokens de sello, en su día. Ahora: nueve ejemplos de la Comisión, cero
errores; cuatro facturas en tira, y las cuentas que traen dentro cuadran.

La de Otto Harrassowitz declara 138 segmentos en su UNT. Salen 138 si el
carácter de escape se trata bien y 139 si no, porque lleva apóstrofos dentro de
los títulos de las revistas. Ese número lo escribió el sistema de una librería
alemana en 2021, y es la clase de prueba que no se aprueba uno solo.

Una de ellas viene mal de origen: dice llevar dos grupos funcionales y lleva
uno. Es un fichero de demostración y está mal. La prueba lo dice con su nombre
en vez de bajar el listón para que pase.

Y una cosa que no se esperaba: los cualificadores de las guías antiguas **no
sustituyen** a los de la norma, se mezclan con ellos. Se vio en cuatro facturas
y se confirmó en 64, con 251 mensajes que llevan totales:

- El `79` —la suma de las líneas, código de la norma— sale en 47 de los 64.
- El `389` —el total sin impuestos, código de la norma— **no sale ni una vez**.
- El `388` —el total con impuestos, código de la norma— sale en uno.
- El `77`, que no es de la norma, sale en 31.

192 de los 251 mensajes no usan ninguno de los tres cualificadores de total que
EN 16931 mira. Un documento puede ir con los códigos de la norma en casi todo y
salirse justo en el que más se mira, que es exactamente el caso en que «falta el
importe total» manda a buscar un dato que está escrito dos líneas más arriba.
No es la rareza de un emisor: en EDIFACT es lo normal, y por eso la queja tenía
que decir el código que sí lleva en vez de dar el importe por ausente.

932 tests, 31 comprobaciones en el navegador (21 críticas). Diez defensas
comprobadas al revés: deshechas una a una, las diez ponen algo en rojo.


## Una frase entera, bien escrita y falsa

De 64 ficheros EDIFACT bajados de repositorios públicos de proyectos de EDI,
23 escriben el UNA con cinco caracteres en vez de los seis que manda la norma:
se saltan el hueco reservado. El lector cogía el sexto, que era la `U` del
`UNB` que viene detrás, y partía el fichero por cada letra U. No aparecía
ningún `UNH`, y la respuesta era «el fichero no trae ningún mensaje» sobre un
fichero con veinticuatro facturas dentro.

Lo que hace de esto un hallazgo y no un fallo cualquiera es que no se parece a
un fallo: no hay excepción, no hay aviso a medias, no hay nada raro en la
salida. Hay una frase en buen castellano que explica con precisión algo que no
ha ocurrido. Quien la lea archivará el fichero como vacío.

La lectura correcta no es una adivinanza: detrás del UNA solo puede venir el
UNB, así que se prueban las dos longitudes y se queda la que deja un UNB
detrás. Se acepta y se deja escrito sobre qué base, que es para lo que están
las notas.

## Que la cuenta la lleve otro

Tres de los 64 traen un carácter de servicio dentro de un dato sin soltar con
`?` —un apóstrofo en el título de una revista checa, otro en un nombre de
empresa—, y el segmento se parte por ahí. El trozo de detrás no es un
segmento, y montar un elemento XML con su «etiqueta» levantaba un `ValueError`
que se llevaba por delante el lote entero.

Rastreando de dónde salen, la sorpresa: el apóstrofo no lo dejó suelto el
emisor. Ese fichero es la misma factura de Harrassowitz que ya estaba entre
las muestras, republicada como caso de prueba en otro repositorio con la
dirección del comprador recortada y el título de una revista retocado. En el
corpus anonimizado, lo mismo con un anonimizador y un nombre de empresa.

Y ahí está lo que vale la pena guardar. Al retocarlo **no tocaron el UNT**,
que sigue declarando los 138 segmentos que escribió el emisor. Con el trozo
roto dentro salen 139; apartándolo, 138. En el otro, 35 donde dice 32; los
tres trozos apartados, 32. Una cuenta escrita por quien emitió la factura
sirve para detectar un destrozo hecho por alguien que vino después.

Es además el reverso de la comprobación que ya había: en el original de esa
misma factura los 138 solo salen si el carácter de escape se trata bien, y en
la copia manipulada solo salen si se aparta el trozo roto. La misma cuenta,
las dos direcciones, y ninguna de las dos la aprueba quien la escribe.

## El lote que se para en el séptimo

El `ValueError` era un fallo concreto y está arreglado. Que se llevara los
otros 63 ficheros por delante es otra cosa, y es peor: apuntar a una carpeta
de quinientas facturas y que la séptima venga mal daba una traza de Python y
ninguna de las cuatrocientas noventa y nueve restantes revisada. Desde un
script, un código de salida distinto de cero — el mismo que cuando hay
facturas con errores.

Un validador de ficheros ajenos tiene que dar por hecho que le van a llegar
cosas no previstas. Ahora eso se cuenta como error del fichero, para que el
lote no dé por bueno lo que no ha mirado, y se dice que la culpa es del
validador y no de la factura.


## Recorrer el paquete no pregunta si el paquete es el de ahora

El banco de pruebas del navegador instala el `.whl` que haya en `dist/`. Al
pasarle las comprobaciones nuevas de EDIFACT salieron cinco en rojo, y una
decía `ImportError: cannot import name 'edifact'`. El wheel era de la víspera.

Lo que importa no es el despiste, que se arregla reconstruyendo. Lo que importa
es que **la comprobación que existe justo para esto salió en verde**: «el
paquete validador importa — los 17 módulos: …», tan tranquila, sin `edifact` en
la lista y sin que a nadie le chirriara. El fallo apareció cinco pruebas más
abajo, disfrazado de otra cosa.

Y esa comprobación estaba escrita así **a propósito**, con un comentario encima
explicando por qué: antes nombraba los módulos a mano, la lista se quedó corta
cuando entró `revocacion`, y se cambió a recorrer el paquete para que no
volviera a pasar. El comentario describe el fallo, y el código de debajo lo
reintroduce.

Porque las dos formas fallan, pero no igual:

- Una lista escrita a mano se queda corta cuando entra un módulo nuevo, y
  entonces **la comprobación falla**. Es un fallo molesto y barato: se lee el
  mensaje y se añade el nombre.
- Recorrer el paquete pregunta *qué trae el wheel*, no *si el wheel es el de
  ahora*, así que con un wheel viejo dentro **la comprobación pasa**. Es un
  fallo cómodo y caro: la página dice que todo está en verde probando código
  que ya no existe.

Ahora hace las dos cosas: recorre el paquete —para importarlos todos— y además
comprueba que estén los que tienen que estar. Sobrar no molesta; faltar lo dice
por su nombre y con lo que hay que teclear:

```
al wheel de dist/ le faltan estos modulos: edifact. Suele querer decir que es
de antes: python -m build --wheel --outdir dist
```

Comprobado quitando `edifact.py` del wheel a mano: la queja sale en la tercera
comprobación, que es donde está la causa, y no veintitantas más abajo.


## Un parser endurecido, y el compilador de esquemas pasando por al lado

`formato.py` tiene una función `parser()` con `no_network=True` y un comentario
encima que dice, desde el primer día, que un fichero que llega de fuera no debe
poder hacer peticiones salientes. Se usa en todas partes. Y sin embargo:

```
con proxy muerto -> FALLA: The QName value 'Signature' does not resolve
                    to a(n) element declaration., line 35
```

Los cinco XSD de Facturae importan la firma XMLDSig **por dirección web**, en su
tercera línea. Ese parser endurecido vale para **leer un documento**; las
importaciones de un esquema las resuelve libxml2 por su cuenta y no pasan por
él. Así que comprobar la forma de una factura del formato nacional se bajaba un
fichero de w3.org cada vez que se compilaba el esquema.

Lo interesante no es el fallo, que se arregla con un resolvedor de veinte
líneas. Es cómo se escondía:

- **Funcionaba.** Con red, que es lo que hay en la máquina de quien programa,
  el import se resuelve y no pasa nada. No hay error, no hay log, no hay
  lentitud apreciable.
- **Había un comentario diciendo lo contrario.** Un `no_network=True` con su
  explicación al lado es exactamente lo que hace que nadie vuelva a mirar. La
  frase era cierta sobre lo que cubría, y lo que no cubría no se le veía.
- **Solo se cae donde no hay red.** Apareció al meter los esquemas en la
  página: en el navegador no hay a dónde salir, y el esquema no compiló.

Y cuando se caía, mentía sobre la causa: «el esquema está ahí pero no se puede
leer, suele ser una descarga a medias, vuelve a bajarlo», sobre un fichero
entero y correcto. El mensaje mandaba a rehacer lo único que estaba bien.

Ahora el resolvedor contesta con la copia de XMLDSig que trae el paquete de UBL
y **se niega** a ir a buscar cualquier otra dirección de fuera. Negarse importa:
devolver `None` ahí es lo natural de escribir y es justo lo que devuelve el
control a libxml2, que la baja él. Hay una prueba que lo fija.

## Lo que caduca no es lo que parece

Un conjunto de anclas de confianza no caduca. Los certificados de dentro valen
veinte o treinta años, y el día que caduquen se dice. Lo que caduca cada seis
meses es otra cosa: **la lista de quién sigue estando autorizado**.

La diferencia es toda. A una autoridad a la que el Estado le retire la
cualificación en enero se le sigue creyendo en un conjunto montado en agosto:
su certificado está en vigor, la cadena llega hasta ella, y no hay nada en el
documento ni en el certificado que lo delate. Solo lo sabe la lista, y la lista
es la que no se ha vuelto a mirar.

Se comprobaba que la lista no estuviera vencida **al montarla**, y ahí se
acababa. Después, nunca. Y eso casi se aguanta mientras las anclas se las
instala quien valida —las montó él, sabe cuándo—; deja de aguantarse en cuanto
un conjunto viaja con una herramienta. Quien entra en una página no eligió esas
anclas ni sabe de cuándo son.

Ahora se dice en los tres sitios donde alguien puede hacer algo: al empaquetar
—negándose—, en cada informe donde una firma llega a un ancla, y en la página.
Como aviso y no como error: la firma es la que dice ser, y lo que no se puede
afirmar es otra cosa.

## Una variable de entorno mandando sobre quien no la había llamado

`FACTURAE_ANCLAS_SELLOS` dice dónde están las anclas de sellado de tiempo. Se
leía dentro de `Almacen.sellos`, así que con esa variable puesta **cualquier**
almacén —incluido uno construido a mano con una carpeta concreta— dejaba de
mirar su carpeta hermana y se iba a la del entorno.

Para un programa con un solo almacén da igual, y por eso llevaba así desde
siempre. La página tiene dos: el suyo y el que fabrica cada comprobación del
banco. Lo cazó una comprobación crítica que ya existía —la que vigila que las
anclas de sellado no se mezclen con las de firma— en cuanto la página empezó a
poner la variable.

La variable es un valor **por defecto**: dice dónde están las tuyas cuando no
has dicho nada. Ahora la lee `por_defecto`, que es quien construye «el almacén
de este programa». Quien nombra una carpeta ya ha dicho cuál quiere.

## El banco corriendo su propia versión de ayer

Se añadieron tres comprobaciones al banco del navegador, se recargó la página, y
siguió diciendo «las 33 comprobaciones pasan» tan contenta. El navegador servía
`prueba.py` de su caché.

El wheel sí llevaba un `?v=` con un comentario explicando exactamente este
peligro —«sale todo verde y no es lo que crees que has probado»—. El fichero que
contiene las comprobaciones, no. Ni las facturas de ejemplo contra las que se
comprueban.

Es la tercera vez en este proyecto que el mismo fallo aparece un nivel más
arriba: primero el wheel viejo, luego la lista de módulos que no detectaba el
wheel viejo, y ahora el banco entero. Cada vez, lo que falla no es la
comprobación sino **de qué copia de sí misma se está fiando**.


# La página no hacía ninguna petición, menos siete

Escribiendo la política de privacidad había que decir qué peticiones hace la
página. La respuesta parecía obvia —ninguna, ese es el argumento— así que en
vez de escribirla se midió.

```
localhost         15 peticiones   1.221 KB
cdn.jsdelivr.net   7 peticiones   7.795 KB
```

Los siete son Pyodide: el intérprete, la biblioteca estándar, lxml y micropip.
Salen al **abrir** la página, antes de que el visitante toque nada, y llevan su
IP y su navegador a un tercero.

Lo que se prometía sigue siendo verdad: **la factura no sale**. Eso también se
midió, y es un cero limpio —cero peticiones al validar, cero cookies, cero
almacenamiento antes y después—. Pero «no se hace ninguna petición a nadie» no
era verdad, y es la clase de frase que se dice de más sin darse cuenta porque
uno está pensando en el fichero del usuario, no en el arranque.

Lo que hace que valga la pena contarlo es que **este mismo criterio ya se había
aplicado, y bien, en la misma página**. Al elegir tipografía se descartó Google
Fonts por escrito, con este comentario en el CSS:

> Ningún tipo de letra viene de fuera. Podría: quedaría mejor. Pero la página
> promete que el fichero no sale de este ordenador, y pedirle la letra a un
> servidor ajeno cada visita es contradecirlo en la primera línea del HTML.

La letra se miró. Los 7,8 MB de intérprete que van justo al lado, no: llevaban
ahí desde el primer día del banco de pruebas, cuando la página era un
experimento y nadie iba a visitarla. Lo que era una decisión de comodidad se
quedó puesto cuando el contexto cambió y pasó a ser una promesa pública.

**Arreglado el mismo día.** Los siete ficheros se bajan al construir con
`python -m validador --traer-pyodide` y se sirven desde el propio sitio. Medido
otra vez después:

```
antes   localhost  15 peticiones     cdn.jsdelivr.net  7 peticiones  7.795 KB
ahora   localhost  23 peticiones     terceros          0
```

Lo que sostiene el arreglo no es haberlo hecho, es que **no se pueda deshacer
sin enterarse**. `--sitio` se niega a montar si falta un solo fichero del
intérprete, y lo dice con esas palabras: «la página volvería a pedírselos a un
CDN ajeno, y la política de privacidad dice que no lo hace». Sin esa negativa,
el día que alguien clone el repositorio y monte el sitio sin haberlos bajado,
lo que se publicaría es una página que vuelve al CDN con un documento al lado
jurando que no lo hace.

Hay un detalle que obligaba a comprobarlo en vez de darlo por hecho: el propio
`pyodide.js` lleva dentro la dirección del CDN como respaldo, para cuando no se
le pasa `indexURL`. Se le pasa. Pero eso es exactamente lo que hay que mirar y
no suponer, así que se cargó la página y se contaron las peticiones.


# La regla correcta que habría avisado en todas las facturas

Al enchufar las respuestas OCSP al informe, la regla salió sola y por analogía
con las listas: si la prueba es **anterior** a la firma, no puede saber lo que
pasó después, así que no cierra la pregunta. Todas las pruebas en verde, ocho
sabotajes cazados, y el módulo entero probado rompiéndolo.

Después se pasó por los seis documentos reales que traen OCSP dentro. Esto es
lo que decía el informe:

```
[AVISO] El documento trae dentro 4 respuestas OCSP, y con ellas no se ha podido
comprobar si el certificado estaba anulado: la respuesta OCSP miró el estado del
certificado el 2015-12-16 y la firma dice ser del 2015-12-16: se miró antes.
```

**La misma fecha a los dos lados, y una frase diciendo que una es anterior a la
otra.** Eso es lo que se veía. Lo que había debajo, al medirlo:

| Documento | Se miró el estado | Firma acreditada | Hueco |
|---|---|---|---|
| `78353__XAdES_A_Detached` | 14:41:55 | 14:42:22 | **27 s** |
| `78353__XAdES_A_Enveloping` | 14:51:00 | 14:51:38 | 38 s |
| `firma_cofirma_xades_longeva` | 09:51:34 | 10:58:13 | 1 h 07 min |
| `XAdES-XL_con_sello_binario` | 15:42:48 | 15:42:47.9 | posterior |
| `XAdES-XL_con_sello_xml` | 12:22:28 | 12:20:20 | posterior |

Un XAdES-XL se construye así y no de otra manera: **se pregunta el estado, se
firma, se sella**. La respuesta es anterior a la firma casi siempre, y por
segundos. La regla no estaba mal razonada —una foto de hace 27 segundos no
prueba lo de ahora—; estaba mal calibrada, y habría levantado el aviso en
prácticamente toda factura archivada de verdad. Un aviso que sale siempre deja
de leerse, y entonces no avisa de nada.

Lo que lo cerró no fue elegir un margen. Elegir «medio minuto pasa» habría sido
inventarse una cifra y llamarla criterio. **Quien dice si una respuesta seguía
valiendo en un momento dado es el respondedor**, y lo dice por escrito dentro de
la propia respuesta: `nextUpdate`. En la de los 27 segundos son las 18:42:22,
cuatro horas por delante de la firma. Si el plazo llega a la firma, se acepta y
la nota dice el hueco y en qué se apoya; si el respondedor no dijo hasta cuándo
valía —su manera de pedir que no se guarde— o dijo que ya no, se sigue sin
saber. El umbral no lo pone este validador.

Quedan dos cosas dichas y no escondidas. Una, que la CRL se queda más estricta:
su ventana se mide en días o semanas y la de una respuesta OCSP en horas, así
que el mismo argumento allí se tragaría un plazo mucho mayor. Y otra, la que de
verdad importa: **las pruebas no lo habrían encontrado nunca**. Estaban
todas verdes, y todas escritas contra fechas inventadas por la misma mano que
escribió la regla. Lo encontró abrir seis ficheros que no ha escrito este
proyecto y leer lo que salía.

## El catálogo publicaba 127 códigos de 153, y prometía que eso no podía pasar

Salió al ir a commitear BR-22, BR-23 y BR-26: los tres códigos nuevos no
aparecían en la página que los explica. No fallaba nada. La página se montaba,
los 127 códigos que traía estaban bien, y ninguna prueba se ponía en rojo.

`codigos.py` lee los códigos del propio fuente con `ast`, que es lo correcto
—una lista escrita a mano se queda atrás—, pero solo miraba el **primer
argumento** de cada `Incidencia(...)`. Si no era una cadena, seguía adelante:

```python
    primero = nodo.args[0]
    if not (isinstance(primero, ast.Constant) and isinstance(primero.value, str)):
        # Un código calculado no se puede leer de aquí. Hoy no hay ninguno;
        continue
```

Ese comentario llevaba tiempo siendo falso. Había **catorce sitios** que no
escriben el código en la llamada, y no por rareza: media docena de reglas los
sacan de una tabla y la recorren con un `for`, que es como se evitan catorce
bloques iguales seguidos.

```python
    for codigo, atributo, campo, explicacion in _DE_LINEA:
        ...
        Incidencia(codigo, ERROR, explicacion, ...)
```

El código sigue escrito —en la tabla, unas líneas más arriba—, pero el lector
veía un nombre de variable y se lo saltaba **sin decir nada**.

### Lo que faltaba

| De dónde salía el código | Cuántos | Cuáles |
|---|---:|---|
| Una tabla del módulo recorrida con `for` | 17 | BR-02 a BR-15, BR-22, BR-23, BR-26 |
| Una tabla escrita dentro del propio `for` | 7 | BR-CO-11, BR-CO-12, FE-CARGOS, FE-DESCUENTOS y los tres FE-LOTE-* |
| Una variable asignada una línea antes | 2 | IVA-BASE, IVA-CATEGORIA-SIN-DESGLOSE |

**127 códigos publicados de 153.** Uno de cada seis no estaba, y entre ellos
casi toda la familia de campos obligatorios de la norma: quien recibiera un
`BR-06` en un informe y fuera a buscarlo a la página no encontraba nada.

Lo peor no era el hueco. Era que la página publicaba, encima de la lista, esta
frase: *«se leen de las propias llamadas a `Incidencia(...)` al montar esta
página, así que aquí no puede faltar uno que exista»*. Una promesa de
completitud, escrita al lado de la prueba de que no se cumplía.

### Qué lo cerró

Desatar el bucle. Cuando el argumento es un nombre, se busca de qué `for` sale
—de dentro hacia fuera, que es como manda Python—, se resuelve la tabla que
recorre y se leen las filas. Igual con la asignación de una línea antes. Vale
tanto la tabla con nombre como la escrita dentro del `for`: son la misma
figura. Si una sola fila de la tabla no es una tupla literal, no se lee
ninguna, porque media tabla leída publicaría una lista incompleta creyéndola
entera.

Quedan **seis** que no se pueden leer y no se van a poder: los `BR-{X}-8`,
`BR-{X}-10` y `BR-{X}-1` de `iva.py`, que llevan dentro la categoría de la
operación y no existen hasta que hay una factura delante. Eso no tiene arreglo
mirando el fuente, así que se cuentan: `sin_leer_del_paquete()` los devuelve
con su fichero, su línea y su patrón —«BR-{}-8»—, la página los publica en la
ficha de arriba como «Compuestos al validar: 6», y la frase de la promesa se
ha reescrito para que diga la verdad.

### Y el guardián, que es lo que faltaba de verdad

Un hueco contado se puede cerrar; uno silencioso no se sabe ni que está. Así
que `tests/test_codigos.py` declara los seis y los compara con lo que hay:
el día que alguien escriba una llamada que este lector no sepa leer, la prueba
se pone en rojo **con el fichero y la línea** y dice las dos salidas —escribirlo
de forma legible, o añadirlo sabiendo que queda fuera—. Si uno se arregla,
también salta, para que la lista no se quede larga de más.

Siete de las doce pruebas nuevas son provocadas: la tabla con una fila que no es
tupla, el bucle de dentro tapando al de fuera, la rama legible de un `if` que
no puede perderse por culpa de la otra, y un `codigo = codigo` que a un
resolvedor ingenuo lo deja dando vueltas para siempre.

Es el mismo disfraz de siempre, el cuarto o el quinto: todo verde, nada roto, y
no era lo que creíamos haber comprobado.

## Tres comprobaciones críticas en rojo en producción, con la suite en verde

El 6 de septiembre de 2026, después de fusionar y desplegar dos veces, el banco
del navegador tenía **tres comprobaciones críticas fallando en la página
publicada**: `una factura correcta sale conforme`, `un EDIFACT plano se lee y se
valida aquí` y `un UNA de cinco caracteres se lee igual`. Las 1.106 pruebas
pasaban. Nada estaba roto en rojo en ninguna parte donde alguien fuera a mirar.

Lo destapó abrir `/banco` durante el ritual de después de desplegar. Era la
única forma que había de verlo.

### El síntoma

Las tres las rompían BR-22, BR-23 y BR-26, las reglas de línea que habían
entrado ese mismo día. Las reglas estaban bien. Lo que estaba mal eran los
ejemplos: **ocho de los diez de `ejemplos/`** no dicen cuántas unidades
facturan, ni en qué unidad, ni a qué precio.

| Sintaxis | Ficheros | Qué les faltaba |
|---|---|---|
| UBL | `f-0001`, `f-0002`, `f-0002-bis`, `f-0006` | `InvoicedQuantity` y `Price` |
| CII | `cii-A-0001` | `SpecifiedLineTradeAgreement` y `SpecifiedLineTradeDelivery`, enteros |
| EDIFACT | los tres `.edi` | la unidad del `C186`: `QTY+47:40'` |

En su día se arreglaron `fe-0001.xml` y `r-0001.xml` **porque eran los que
rompían pruebas**. Los otros ocho no rompían ninguna, así que no se miraron.
Ahí estaba el aviso, y lo que faltaba era quien lo diera.

Que ninguno cambiara lo que demuestra se comprobó, no se supuso: se validó el
árbol de `ejemplos/` de `9e17465` con el validador de hoy y se comparó queja a
queja con el de ahora. Descontando las tres nuevas, **cero diferencias en los
diez**. Los que están rotos a propósito —`cii-A-0001`, `edi-0002-cortado`,
`f-0006`— siguen rotos por lo mismo.

### El fallo de verdad

No es ninguno de esos ocho ficheros. Es que **el banco no lo corría nadie
aquí**. `web/prueba.py` está escrito para que lo ejecute Pyodide dentro del
navegador: `pytest` no lo tocaba, no aparecía en ninguna cuenta, y la única
señal posible era que a una persona se le ocurriera abrir una página concreta.

Es el disfraz de siempre de este proyecto, con una variante nueva. Las cuatro
veces anteriores era **algo de una caché haciéndose pasar por lo de hoy**: un
wheel viejo, un `prueba.py` viejo, un `index.html` viejo. Esta vez no había
nada viejo. Había un banco entero de 38 comprobaciones que sencillamente no
estaba en el alcance de nada, y por eso no podía salir en rojo aunque lo
estuviera.

### Qué lo cerró

`tests/test_banco.py`: se ejecuta `web/prueba.py` con CPython, con `EJEMPLOS`
apuntando a la carpeta del repositorio, y se exige que las 38 pasen **y que
hayan corrido las 38** —una comprobación que ni se ejecuta no sale en rojo,
desaparece—. Tarda 3,2 s.

Probado rompiéndolo: quitarle el `unitCode` a `f-0001.xml` saca
`--- una factura correcta sale conforme (CRÍTICA)` con el `[BR-23]` entero
debajo.

**No sustituye a abrir `/banco`, y está dicho en el propio fichero.** Aquí el
lxml es el del sistema y allí es una compilación de libxml2 para WebAssembly;
medio banco existe justo para comprobar que esa compilación trae la
canonicalización y los esquemas XSD. Lo que cambia es que un ejemplo roto ya no
llega a producción: se cae en `pytest`, en tres segundos.

### Y el propio ritual llevaba tres cosas mal

Salieron al usarlo, no al leerlo, que es la única forma en que salen:

1. El punto 4 esperaba tres incidencias y salen seis. Las tres nuevas son las
   notas del binding de Facturae diciendo qué no pudo comprobar. Que se supiera
   en el acto que no había desaparecido ninguna es mérito del propio ritual,
   que desde el 31-08 escribe el código al lado de la gravedad justo para esto.
2. El punto 5 mandaba esperar a `#arranque` en `/banco`, y esa página no lo
   tiene: revienta con un `Cannot read properties of null`.
3. Y el arreglo del punto 5 —esperar a que exista `window.Glosa.correrBanco`—
   **también estaba mal, y lo escribí yo media hora antes**. La función está
   puesta desde el primer momento y el intérprete no, así que se llama antes de
   tiempo y revienta con `reading 'runPythonAsync'`. Creer que algo está listo
   porque se le puede nombrar es el mismo error con otro disfraz. Lo que lo
   dice de verdad es `#veredicto`, que arranca con la clase `esperando` y la
   pierde cuando el banco está montado.

Y una cuarta, en la comprobación de privacidad, que estaba desde el principio:
`ajenos` se calculaba como todo origen distinto del propio, y
`new URL('data:…').origin` devuelve la cadena `"null"`. En frío salía `[]` y en
caliente salía `["null"]`, que es un SVG en línea del CSS —cero bytes, ninguna
red—. La afirmación de «0 dominios de terceros» se sostiene, pero **una
comprobación de privacidad que da la alarma cuando no pasa nada se deja de
leer, y entonces no avisa el día que pase**.

## Seis superficies vigiladas por nadie, y el gancho que fallaba abriendo

El 6 de septiembre de 2026, con lo del banco recién cerrado, un agente
independiente recorrió el repositorio buscando lo mismo una vez más: **cosas
que existen y no están en ninguna cuenta**. No encontró nada roto. Encontró
seis sitios donde, si algo se rompiera, no se enteraría nadie. Van por orden de
lo que costaba cada uno.

### 1. El gancho de la puerta de producción fallaba abriendo

No hay CI. Entre un test rojo y la página publicada solo está
`.claude/hooks/antes-de-empujar.py`, y Claude Code únicamente bloquea una orden
cuando el gancho **sale con código 2**.

Dentro había un `subprocess.run(..., timeout=600)` sin recoger. Un
`TimeoutExpired` —o un `OSError` al arrancar el intérprete— subía hasta
`sys.exit(main())`, imprimía una traza y salía con **1**. Con 1 la orden sigue
adelante: el push se publicaba *después de que el gancho hubiera fallado*.

Reproducido antes de tocarlo, apuntando `PYTHON` a un fichero que existe y no
es un ejecutable —un `OSError [WinError 193]` de verdad, no simulado—:

```
el gancho de HEAD  ->  traza y exit 1   (no bloquea)
el gancho de ahora ->  «No se ha podido correr la suite: …»  y salida 2
```

Ahora todo camino de fallo sale con 2, incluida la entrada que no se deja leer:
si el JSON no parsea se mira el texto crudo, y si se parece a un push se para.
Sin eso, el día que cambiara la forma de la entrada el gancho devolvería 0 a
todo y seguiría pareciendo que guarda la puerta. `tests/test_ganchos.py`
provoca los seis caminos y comprueba que ninguno sale con 1.

### 2. Los mensajes de libxml2, escritos para la versión que no corre en la web

`esquema.py` traduce los mensajes de libxml2 con doce expresiones regulares, y
de esa traducción salen los códigos que ve quien valida —`XSD-ORDEN`,
`XSD-TIPO`, `XSD-VALOR`— y la explicación en castellano, que es el producto.
Cuando ninguna encaja hay una salida de emergencia: `XSD-OTRO`, que copia el
mensaje inglés tal cual.

Las regex se escribieron leyendo **libxml2 2.11.9**, el de los tests. En el
navegador hay **2.9.10**. Si esa versión redactara una sola de esas frases de
otra manera, no fallaría nada: todos los errores de forma saldrían en inglés
**solo en la página**, que es donde está la gente que no sabe leer un mensaje
de libxml2. Nadie lo había mirado nunca.

Ahora el banco provoca los trece incumplimientos —falta un hijo, orden
cambiado, elemento desconocido, valor fuera de lista, fecha, importe con coma,
longitud, patrón, atributo que falta, atributo que sobra, texto suelto, raíz
que el esquema no declara— contra un esquema de juguete que viaja en el propio
fichero, y exige el código exacto. La suite corre esa misma tabla con el otro
libxml2, y un guardián lee el AST de `traducir()` para que ninguna regex nueva
se quede sin provocar.

**Medido el 06-09-2026: los 13 salen igual con 2.9.10 que con 2.11.9.** Era la
respuesta que faltaba, y ahora se vuelve a medir en cada despliegue.

### 3. La huella del paquete se publicaba y no la comprobaba nadie

`web/paquete.zip` y `web/PAQUETE.json` son la excepción decidida a propósito
del control de versiones, y van juntos «con su SHA-256 publicado al lado». Ese
*al lado* no lo miraba nadie: `glosa.js` se bajaba el zip, lo descomprimía y
seguía.

No es una frontera de seguridad —el zip y su ficha vienen del mismo sitio— y no
se dice que lo sea. Lo que caza es el fallo que este repositorio ya ha tenido
cuatro veces con distinto disfraz, la caché vieja, y su pariente: **un zip
truncado se descomprime sin error** y deja al validador con menos anclas de las
que la página dice traer. Eso son aprobados de más repartidos en silencio.

Ahora se comprueba antes de descomprimir y, si no cuadra, la página no arranca.
Probado rompiéndolo, cambiando cuatro dígitos de la huella publicada:

```
No ha arrancado: El paquete de esquemas y anclas no es el que la pagina dice
traer: PAQUETE.json publica dead71b73376… y lo que ha llegado resume
364071b73376… . No se descomprime.
```

También se mira el tamaño, que es lo único que queda cuando no hay
`crypto.subtle` —sirviendo esto por http en una red local—, y `pytest` compara
el par versionado antes de publicar, que es más barato.

### 4. «0 dominios de terceros» lo comprobaba una persona acordándose

Es la cifra de cabecera de la privacidad y de ella cuelga que aquí no haya
tratamiento que declarar. La medía alguien abriendo el panel del navegador
durante el ritual de despliegue. Un `@import` en el CSS o una tipografía de
Google la habrían vuelto falsa sin romper nada.

Ahora hay dos guardianes y hacen falta los dos. Uno estático
(`tests/test_sin_terceros.py`) mira lo que se escribe: ningún `<link>`,
`<script>`, `url()` ni `@import` apunta fuera —y distingue un enlace, que es
una dirección que se ofrece, de una petición, que es una que se hace—. El otro
está en el banco y mide lo que el navegador ha pedido de verdad, que es lo
único que cazaría un respaldo a la CDN de Pyodide: esa dirección va escrita
dentro de `pyodide.js` y no en ningún fichero de aquí.

Probado rompiéndolo por los tres sitios —una tipografía en `index.html`, un
`@import` en `glosa.css` y una dirección de analítica en `glosa.js`—: los tres
en rojo.

### 5. La página del catálogo se ejecutaba por primera vez en Vercel

`pagina_incidencias.py` genera `incidencias.html`, el catálogo público de los
códigos. Ninguna prueba lo ejecutaba: la única que lo tocaba comprobaba que la
plantilla siguiera llevando su marca. El generador entero —**29,8 % de líneas
ejecutadas**— corría por primera vez durante la construcción del sitio. Un
`KeyError` ahí no es un test rojo: es un despliegue roto, o peor, una página
publicada con media tabla.

Ahora se monta de verdad en `pytest`, con la plantilla y los códigos de hoy, y
se comprueba lo que hace la página útil o inútil: que cada código tenga su
ancla —sin ella el enlace del informe no lleva a ninguna parte—, que ninguna se
repita, que la cifra del titular sea la de la tabla de abajo, y que lo que no
se sabe se diga en vez de rellenarse. Cobertura medida después: **98 %**.

### 6. Diez códigos publicados que nadie había visto salir

El catálogo se titula «los códigos que **puede sacar** este validador», y ese
*puede* es una afirmación. Al preguntarle al revés —¿qué código del catálogo no
nombra ninguna prueba ni el banco?— salieron **diez de 159**:

```
BR-CL-01  EDI-MENSAJE-SIN-CERRAR  EDI-SIN-SEGMENTOS  FE-CARGOS
FE-LOTE-EJECUTAR  FE-LOTE-PENDIENTE  FE-PAIS-RETIRADO
FE-TIPO-SIN-EQUIVALENTE  IVA-BASE  SELLO-ALGORITMO-VIEJO
```

Tres se habían añadido la víspera, con el binding de Facturae: estaban probados
por el **valor** que salía de la regla, no por la queja, así que un código mal
escrito habría pasado igual —y el código es justo lo que se publica y lo que se
busca—. Otros tres son la mitad no probada de una tabla: los descuentos
generales sí y los cargos no, el total del fichero sí y el pendiente y el
ejecutable no. Es el sitio exacto donde se cuela una errata, porque la rama
probada tapa a la que no lo está.

Los diez provocados, y `test_inventario.py` no deja que vuelva a haber uno
suelto. De paso se cerró `IVA-CATEGORIA-SIN-MAPA`, que desde que la categoría
de Facturae se deduce **no lo puede sacar ningún fichero real**: no se ha
borrado —es lo que dirá el validador el día que entre una sintaxis sin sitio
donde escribir la categoría, y sin él esa sintaxis se saltaría todas esas
reglas en silencio— sino que se provoca con un mapa al que se le quita la ruta.

## «Validar las siete de `ejemplos/`», con diez ficheros en la carpeta

Aparte de las seis, `web/LEEME.md` —el documento de lo medido— llevaba **cinco
cifras caducadas a la vez**: siete ejemplos cuando había diez, veintisiete
comprobaciones críticas cuando eran veintiocho, treinta y siete resultados
cuando eran treinta y ocho, «las veinte» cuando eran treinta y ocho, y una
tabla de críticas a la que le faltaban seis filas.

Lo interesante no es que se quedaran atrás: es **por qué esas y no otras**. El
README lleva guardián desde hace meses —«1.212 tests, todos en verde»— y no se
queda atrás nunca. La tesis igual. La diferencia es que aquellas están en
dígitos y hay un `re` que las busca; estas estaban escritas **en letra**, y una
cifra escrita «treinta y siete» no la encuentra ningún guardián. Sobrevive a
todo porque es invisible.

Así que el arreglo no es cambiar los números. `tests/test_cifras_publicadas.py`
hace tres cosas:

1. Declara cada cifra con su patrón y su forma de medirla, y falla si el patrón
   deja de encontrar nada: una frase reescrita no puede dejar ciego al guardián
   sin que se note.
2. Ata la tabla de comprobaciones críticas al banco **en los dos sentidos**:
   ninguna crítica sin fila, ninguna fila sin crítica.
3. Y el cepo, que es lo que evita la próxima: cualquier línea del documento que
   afirme una cantidad sobre algo que este repositorio sabe contar tiene que
   estar vigilada, o declarada en `SIN_VIGILAR` con el motivo por el que no se
   puede medir. Una cifra nueva sin guardián deja la suite en rojo.

El cepo cazó dos líneas que acababa de escribir yo mientras arreglaba esto, y
esa es la prueba de que hacía falta.

## Un aviso perfecto y un `return 0`

La séptima de la ronda, y la que quedaba sin cerrar. `--sitio` monta lo que se
publica, y cuando no encuentra el paquete de esquemas y anclas **lo dice muy
bien**:

```
  esquemas y anclas     NO VAN

  Este sitio arranca y valida el contenido, pero no comprueba ni la
  forma ni de quién es la firma, y lo dirá en cada informe.
```

Y sale con 0. Eso está bien mientras quien monta sea una persona, que es para
lo que se escribió: en local hace falta poder montar sin armar 389 anclas. Pero
quien monta lo que se publica es la construcción de Vercel, y una construcción
no lee recuadros: mira el código de salida. Un despliegue al que le faltara el
paquete habría publicado un validador que comprueba **una de las tres cosas**,
con la página diciéndolo en letra pequeña y el despliegue en verde.

Es el mismo par de siempre —un comentario que pide memoria frente a un guardián
que no deja montar— y hasta ahora esto estaba del lado malo.

Ahora `--sitio` admite `--exigir-paquete`, `vercel.json` la pasa, y sin ella no
cambia nada. Provocado con un repositorio de mentira al que se le quitan el zip
y su ficha:

```
sin bandera  ->  salida 0   sitio montado, con su aviso
con bandera  ->  salida 2   y ni una carpeta escrita
```

Dos detalles que costaron una vuelta cada uno. El primero: la negativa mira
**que el paquete traiga algo**, no solo que el fichero exista; un zip armado
sin anclas se copia, se sirve y se descomprime sin error mientras la ficha de
la página anuncia 268 anclas que no están. El segundo: la revisión va **detrás**
de `RuedaVieja` y no delante, aunque las dos ocurran antes de escribir el primer
byte, porque cuando las dos cosas fallan a la vez conviene leer primero la del
wheel viejo, que es el fallo que este repositorio ha tenido cuatro veces.

Y una prueba que no comprueba el código sino el despliegue: que `vercel.json`
siga pasando la bandera. Una bandera que existe y que nadie pasa es exactamente
lo que ya pasó con el gancho de `antes-de-empujar.py`, que estuvo meses escrito
y sin declarar. No fallaba: dejaba pasar.

## Una regresión de 3,6x que no existía

Este no es un fallo del validador. Es un fallo de medición, y va escrito porque
estuvo a punto de acabar publicado como una cifra del producto —y porque la
regla de la casa es «se mide, no se supone», que también significa saber cuándo
lo que se ha hecho **no** es medir.

### Lo que parecía

Recién desplegado el binding de Facturae, midiendo en producción los 10
ejemplos: **1.450 ms**. Sobre el despliegue anterior había medido **400 ms**.
Tres veces y media peor, y con una explicación a mano y creíble: acababan de
entrar las reglas de línea, la categoría de IVA deducida, la traducción del
país y BT-3. Trabajo nuevo en el camino caliente.

Lo cómodo era darlo por bueno y ponerse a optimizar. Habría sido optimizar algo
que no estaba mal.

### Lo que lo desmontó

Primero, lo barato: los mismos diez ficheros con CPython, con los esquemas
puestos, comparando el código de antes y el de ahora en dos árboles distintos.

```
antes (a83564b)   192,5 ms        ahora   179,4 ms
```

Más rápido, no más lento. Pero eso solo no bastaba y por eso no se paró ahí:
aquí corre libxml2 2.11.9 y en la página 2.9.10, así que una lentitud que
apareciera **solo** en WebAssembly habría dado exactamente este resultado. Ya
hay medio banco dedicado a que esa diferencia no se dé por supuesta.

Lo que lo cerró fue medir donde pasa: el mismo navegador, la misma máquina, la
misma página, cambiando **solo la rueda** —dos wheels construidos de los dos
commits, servidos por turnos desde `dist/`—.

```
rueda de antes    1.367 ms        rueda de ahora   829 ms
```

El código nuevo es un 40 % más rápido. No había regresión que arreglar.

### Qué estaba pasando de verdad

Que estaba midiendo con el ordenador compilando ruedas y corriendo la suite en
otra ventana. Con la máquina en reposo, producción da **798 ms** de mediana
sobre siete pasadas, que cuadra con los 829 del servidor local. Las lecturas de
1,4 s eran mías, no del validador.

### Y los 400 ms tampoco valían

Es la parte que más cuesta escribir. La cifra vieja tampoco se pudo reproducir:
si la rueda de antes tarda 1.367 ms en el mismo navegador, aquel 400 no podía
ser cierto para aquel código. No es que la nueva medida corrigiera a la vieja
—es que **ninguna de las dos estaba tomada en condiciones**, y la vieja llevaba
un rato en `web/LEEME.md`.

Así que no se ha «actualizado» el número: se ha tirado y se ha medido otra vez,
diciendo cómo. La fila ahora lleva al lado el método —cuatro pasadas de
calentamiento, mediana de siete, máquina en reposo— y la condición que la
mueve, porque es la única fila del cuadro cuyo valor depende de lo que esté
haciendo el ordenador en ese momento.

**Una medida sin las condiciones en las que se tomó no es una medida**, y es
más peligrosa que no tener ninguna: la que falta se busca, y la que está mal se
cita.


## «Las dos sintaxis sin binding CEN», y una de las dos sí lo tenía

Este no es un fallo del validador ni del repositorio: es una afirmación falsa
que escribí **en público**, en el hilo
[ConnectingEurope/eInvoicing-EN16931#518](https://github.com/ConnectingEurope/eInvoicing-EN16931/issues/518),
el 04-09-2026. Va aquí porque es el mismo defecto de método que la medida mal
tomada de más arriba, con otro disfraz, y porque una comparación con la que se
argumenta en público **es una medida**.

### Lo que escribí

> «los dos que el decreto deja sin definir son exactamente los dos sin binding
> sintáctico CEN: EDIFACT, cuyos artefactos aquí están congelados en v1.0.0
> (2018), y Facturae, que nunca tuvo una parte `CEN/TS 16931-3-x`».

La mitad de Facturae es cierta. La de EDIFACT es falsa.

### Lo que lo desmontó

Lo corrigió Svante Schubert en el propio hilo el 06-09-2026 —dirigió el
proyecto de binding CEN de UBL y CII de 2026—. `CEN/TS 16931-3-4` existe,
se titula «*Syntax binding for UN/EDIFACT INVOIC D16B*» —y ese título es
parte del problema, como se ve al final de esta entrada—, y **tiene tres
ediciones**:

| Edición | Publicada |
|---|---|
| `CEN/TS 16931-3-4:2017` | 30-11-2017 |
| `CEN/TS 16931-3-4:2020` | 15-05-2020 |
| **`CEN/TS 16931-3-4:2026`** | **17-08-2026** |

La última se publicó **seis semanas antes** de que empiece a contar el
artículo 7.1 del RD 238/2026. La redactó Jenny Herzfeld, de la VDA alemana,
generada con GEFEG.FX sobre los modelos UN/CEFACT.

### De dónde salió el error

De deducir la ausencia de la **norma** a partir del abandono de los
**artefactos**. Lo que yo había mirado era el repositorio de GitHub, donde el
esquematrón de EDIFACT lleva en v1.0.0 desde el 08-02-2018 mientras UBL y CII
van por v1.3.16 (10-04-2026). De ahí a «no hay binding» hay un paso, y ese paso
es exactamente el que no se puede dar: **un artefacto que no se actualiza no
demuestra que no exista la norma que implementa**. Son dos cosas distintas y se
publican en sitios distintos —una en GitHub y gratis, la otra en los organismos
de normalización y de pago—, que es justo lo que hace fácil confundirlas.

Y el repositorio, mientras tanto, lo tenía bien. `README.md` y
`validador/sintaxis.py` decían desde el principio «`-3-2` para UBL, `-3-3` para
CII y `-3-4` para EDIFACT, y para Facturae nada». **El código sabía lo que el
autor había dejado de saber**, que es lo que pasa cuando una nota escrita con
la fuente delante se cita meses después de memoria.

### Lo que queda en su lugar, medido

El hallazgo bueno no era el que yo creía, y es más concreto. Contados los
directorios que declaran los `UNH` de las facturas EDIFACT de terceros que hay
aquí —70 mensajes con directorio legible—:

| Directorio | Mensajes |
|---|---:|
| `D:96A` | 55 |
| `D:97A` | 3 |
| `D:93A` | 4 |
| `D:96B` | 3 |
| `D:01B`, `D:06A`, `D:07A` | 5 |
| **`D.24A`**, que es el que la norma mapea | **0** |
| **`D16B`**, que es el que su portada dice | **0** |

Ni uno de ninguno de los dos. El directorio mayoritario es de **1996**, y el esquema que acompaña a
los artefactos es de otro distinto más —`INVOIC_D14B_ISO20625.xsd`, con su
carpeta sin tocar desde 2017—. Tres versiones de EDIFACT en juego, y con la que
la norma pide de verdad son cuatro.

Esto no se arregla con una corrección: es la pregunta que queda abierta, y es
mejor pregunta que la que yo llevaba.

### Y volvió a pasar dos días después, con el mismo mecanismo

La corrección de arriba se publicó en el hilo el 07-09-2026 a la una de la
madrugada. A las siete y media, el mismo Svante Schubert contestó corrigiendo
**la corrección**. Dos cosas:

**Una.** Yo había escrito que `-3-4` «vincula EN 16931 a `INVOIC D16B`». Eso es
lo que dice el **título de la portada**, y la portada no se actualizó: la
referencia de versión tenían que haberla cambiado en el CCMC —el centro de
gestión de CEN-CENELEC— y no se hizo. La revisión de 2026 mapea de verdad a
**`UN/CEFACT INVOIC D.24A S4`**. Lo mismo pasa con las otras dos, cuyos títulos
tampoco lo dicen: la de UBL de 2026 pide **UBL 2.5** como mínimo y la de CII,
**CII D.25A**. Se corregirá en las próximas modificaciones.

**Dos.** «En vigor desde el 17-08-2026» era mío y no lo dice nadie más. Que CEN
o un organismo nacional publiquen una norma no la hace legalmente aplicable:
eso lo decide la legislación, con las referencias del Diario Oficial de la UE.
A nivel CEN **conviven** la revisión de 2017 —con su modificación de 2020— y la
de 2026; la de 2017 está programada para retirarse el **31-03-2029**. Hay
periodo transitorio, y qué edición hay que usar, o si valen las dos a la vez,
lo dice la ley aplicable y no la fecha de publicación.

Lo que hay que ver aquí no son los dos datos, sino que **es el mismo mecanismo
dos veces seguidas y no lo reconocí la segunda**. Primero deduje la norma por
el estado del artefacto. Después deduje el mapeo por el título de la portada.
Las dos veces leí el envoltorio y afirmé algo sobre el contenido; las dos veces
el envoltorio estaba desatendido, que es la condición normal de los envoltorios.
Y la segunda la cometí **dentro del texto en el que estaba explicando la
primera**, que es lo más incómodo de escribir aquí y la razón de que se escriba.

Queda además una pregunta que sí es del producto y que no puedo contestar
midiendo, porque es de derecho: **a qué edición de EN 16931 apunta el artículo
7.1 del RD 238/2026**. Si apunta a la de 2026, la semántica que hay que validar
es la que pide UBL 2.5, CII D.25A y EDIFACT D.24A S4. Si apunta a la de 2017,
es otra. Hasta saberlo, aquí no se afirma ninguna de las dos.

**Contestada el 22-09-2026**, y por escrito. Se preguntó al buzón de la AEAT si
la edición de junio de 2026 vale también fuera de la solución pública, y la
respuesta nombra las dos partes y dice a qué alcanzan: `UNE-EN 16931-1:2026`
—junio, el modelo semántico— y `UNE-CEN/TS 16931-3-2:2026` —septiembre, la
correspondencia sintáctica UBL 2.5 / ISO/IEC 19845— son las versiones
ratificadas aplicables «al sistema español de facturación electrónica en su
conjunto», y enumera los tres casos: la emisión e interconexión en la SPFE, el
**envío de copias fieles** y el **intercambio privado entre plataformas
regulado en el artículo 7.1**.

Con la cautela que este mismo apartado exige, porque es la que lo trajo aquí:
**esto no es el boletín**. Que la Agencia diga a qué edición valida no es lo
mismo que una referencia en el Diario Oficial, y la de 2017 sigue viva hasta el
31-03-2029. Lo que cambia es que ya no hay que elegir a ciegas entre dos
ediciones: hay una respuesta de la administración que lo aplica, por escrito y
citable, y es la que se sigue aquí mientras no salga la orden. Las dos
consecuencias que tiene dentro: la copia fiel es **UBL 2.5** y no «UBL» a
secas, y `BT-179` y `BT-180` dejan de estar fuera de la edición aplicable —lo
que les sigue faltando es la ruta del anexo, que es otra cosa—.

### Y el propio repositorio lo puso por escrito, el 25-09-2026

Oriol Bausa, colaborador del repositorio, escribió en el hilo el
[comentario 16](https://github.com/ConnectingEurope/eInvoicing-EN16931/issues/518#issuecomment-5829018081)
y cerró con «We forward it to TC434»: la consulta pasa al comité. Lo que dice
del artefacto, resumido:

- los artefactos EDIFACT se hicieron contra la edición de 2017 de
  `CEN/TS 16931-3-4` y salieron como v1.0.0 en febrero de 2018, y no se han
  puesto al día ni para la modificación de 2020 ni para la revisión de 2026;
- la v1.0.0 hay que leerla como una foto del binding de 2017;
- hasta que salgan los nuevos, quien implemente no debe tomar el esquematrón
  EDIFACT de hoy como representativo de la 3-4:2020 ni de la :2026.

Es la confirmación, de quien publica los artefactos, de lo que aquí se había
medido del **envoltorio**: que el artefacto está parado. Y no dice nada del
**contenido** de la norma, que es justo la distinción de esta entrada.

**Él mismo avisa de que el texto está escrito con IA**, así que se comprobó
antes de citarlo, contra las notas de versión y la historia de la carpeta:

| Lo que dice | Lo que hay |
|---|---|
| sin actualizaciones desde la v1.0.0 | sin **versión** desde la v1.0.0 (08-02-2018). La carpeta `edifact/` sí recibió cambios hasta el 16-11-2020 —entre ellos «Updated Schematrons for #86», el 13-12-2018—, y ninguno salió en una versión |
| todas las notas desde la v1.1.0 dicen que EDIFACT está en pausa | todas las versiones desde la v1.1.0 son «UBL and CII only»; la **pausa** la escriben dos, la v1.1.0 y la v1.2.0: «its development is currently paused/stalled» |

Lo esencial se sostiene. Los dos matices son de los que un resumen redondea, y
por eso aquí se cita lo comprobado y no la frase.

### La regla

La de siempre, aplicada a un sitio donde no la había aplicado: **se mide, no se
supone**, y eso incluye lo que uno afirma discutiendo. La diferencia con un
error dentro del repositorio es que aquí no hay guardián posible ni `git
revert`: un comentario está publicado en el momento en que se escribe. Lo único
que queda es corregirlo en el mismo sitio.

## La conexión se cortó y la página siguió diciendo «Descargando»

Salió comprobando un despliegue, no buscándolo. El 08-09-2026, cargando
`www.glosa-e.com` desde la conexión del autor, la página se quedó
para siempre en «Descargando el validador». No dio error, no reintentó, no dijo
nada. La zona de soltar ficheros seguía aceptando facturas con el mensaje «se
validan en cuanto termine», y no iba a terminar.

### Lo que se midió

En el registro de red del navegador, una petición entre nueve:

```
GET /pyodide/314.0.6/python_stdlib.zip → 200  [FAILED: net::ERR_CONNECTION_RESET]
```

**El servidor había contestado 200.** Lo que se rompió fue el transporte, a la
mitad del cuerpo. Y `loadPyodide` ni rechazó ni resolvió: se quedó esperando.

Que era el enlace y no el sitio se comprobó aparte: `HEAD` sobre el `.wasm`
devolvió `200` con `Content-Length: 9598218`, exactamente los bytes del fichero
local, y la segunda carga —con la caché ya caliente— completó entera en 78,39 s.

### Por qué es el fallo de siempre

El `catch` de `index.html` estaba escrito, y bien: marca el fallo, apaga la
zona y se lo cuenta a quien hubiera soltado una factura mientras cargaba. No
corrió **porque nadie rechazó**. No hubo excepción que capturar.

Es el patrón de esta casa otra vez: no se rompe nada, no sale ningún error, y
lo que hay en pantalla no es lo que está pasando. Antes fue un wheel viejo
sirviéndose de una caché; esta vez es una promesa que no vuelve.

### El arreglo que no valía

Un tiempo máximo de arranque. Es lo primero que se piensa y es justo lo que no
se puede hacer aquí, y la razón está medida:

| Etapa | Desde la conexión del autor |
|---|---:|
| Intérprete de Python (WebAssembly) | 40,97 s |
| lxml + libxml2 | 20,28 s |
| El validador | 3,13 s |
| Esquemas y anclas de confianza | 13,60 s |
| Facturas de ejemplo | 0,41 s |
| **Listo** | **78,39 s** |

Cualquier límite lo bastante corto para servir de algo habría roto la página
**justo a quien más le cuesta cargarla**, que es exactamente el usuario para el
que se estaba arreglando.

### Lo que se hizo

`SinDescarga`, en `web/glosa.js`. No mide cuánto tarda: mide **si llega algo**.
Con una petición abierta y ni un byte en treinta segundos, la conexión está
muerta y no lenta, y entonces se rechaza y sale por el `catch` que ya existía.

Las dos mitades de la condición cuentan:

- **`ultimoByte`** se refresca leyendo el cuerpo de cada respuesta. El conteo
  va sobre `clone()`, no sobre lo que se devuelve: Pyodide recibe la respuesta
  intacta, con su `url` y su `content-type`. Reconstruirla con un flujo propio
  gastaba menos memoria y dejaba a `instantiateStreaming` sin el tipo que
  necesita, que es cambiar un fallo silencioso por otro.
- **`abiertas > 0`** exige que haya algo descargándose. Sin esa mitad el
  vigilante saltaría mientras se compila el `.wasm`, que es un rato largo sin
  red y sin nada roto.

### Probado rompiéndolo

Aquí no hay Node y el JavaScript no corre en la suite, así que se provocó en el
navegador, sobre el sitio montado en local, el 09-09-2026:

| Caso | Qué hizo |
|---|---|
| Carga sana, con el vigilante puesto | «Listo en 7,80 s» |
| Conexión muerta: petición abierta, cero bytes | `SinDescarga` a los 30 s |
| Conexión lenta: un trozo cada 9 s, 37 s en total | **arrancó bien** |
| La página entera, con la conexión muerta | «No ha arrancado», zona apagada |

El tercero es el que importa: 37 segundos son siete más que el límite, y no
saltó, porque los bytes seguían llegando. Es la diferencia entre un vigilante y
un cronómetro.

`tests/test_vigilante.py` fija lo que no se puede perder en una limpieza —la
negativa, la delegación de `arrancar`, el `abiertas > 0`, el `clone()` y la
devolución del `fetch` bueno— y se provocó quitando la mitad de la condición:
falla `test_se_cuentan_bytes_y_no_segundos` y solo esa.

## El BT-3 que razonamos bien y España no admite

Cuatro días después de cerrar la traducción del `CorrectionMethod` de Facturae
a UNTDID 1001 —01 a 384, 03 a 381, y negarse con 02 y 04— se leyó el anexo I
del proyecto de orden de la solución pública. Su lista L1, la de tipos de
factura admitidos, es:

```
380  Factura (art. 6, 7.2 y 7.3 del RD 1619/2012)
384  Factura rectificativa
388  Factura emitida en sustitución de facturas simplificadas
389  Factura emitida por el destinatario
471  Factura rectificativa emitida por el destinatario
```

**No está el 381.** En España una rectificativa es 384, o 471 si la expide el
destinatario, y da igual cómo rectifique: que sea por diferencias o por
sustitución no se dice en el BT-3 sino en `BT-ES-3`, con la lista L2.B, que
solo tiene dos valores, `I` y `S`.

Así que la decisión anterior no estaba mal razonada: estaba razonada sobre la
norma europea a secas, que es donde 381 es el abono. Dentro del CIUS español no
cabe. Y el caso que se dejó sin decidir —el `02`, «por diferencias», porque el
método no dice si suma o resta— resulta que tiene un sitio limpio donde ir; solo
que no es el BT-3.

Queda anotado y sin arreglar a propósito: el anexo es un borrador, no está en
el BOE y la propia AEAT ha dicho que lo alineará con UBL 2.5. Cambiar el motor
para cuadrar con un documento que va a cambiar es correr detrás de un blanco
móvil. Lo que sí está hecho es que **no se pueda olvidar**: hay una prueba,
`test_l1_no_admite_el_381`, que dice por qué existe.

## Un PDF leído por columnas da 174 filas plausibles y equivocadas

El CIUS español no se publica como esquema ni como esquematrón. Se publica como
una tabla dentro de un PDF, así que hay que sacarlo de ahí.

El primer intento usó el modo `layout` de pypdf, que reconstruye las columnas
con espacios. Salieron 174 filas con buena pinta. No valían:

```
517 '   BT-        +++         1..1       Suma de las cuotas del           '
518 '   179                               recargo de equivalencia'
```

`BT-179` partido en dos renglones. Y peor:

```
508 ' ES-                                       21 minoración en nombre de '
```

El `21` de `BT-ES-21` **dentro de la columna del término**. El PDF coloca los
dígitos donde le cuadra, así que cualquier reparto por posición de carácter
reparte mal, y lo hace en silencio: la tabla sale llena, con identificadores
que parecen identificadores, y no son los que el anexo dice.

Es el fallo de siempre de este repositorio con otro disfraz —sale verde y no es
lo que crees haber comprobado—, y aquí habría sido de los caros: toda la
migración a EN 16931:2026 se apoya en esa tabla.

### Lo que sí vale

Leer las piezas con su `(x, y)` de verdad y repartir por geometría. Y no
fiarse tampoco de eso: contrastarlo contra una segunda lectura que no comparta
una línea de código, que aquí fue una expresión regular sobre el mismo PDF en
plano. Las dos dan **el mismo conjunto de 155 identificadores**, y las
diferencias de recuento bruto están explicadas una a una:

| Método | Cuenta | Por qué difiere |
|---|---|---|
| Coordenadas | 174 filas | — |
| Regex en plano | 176 menciones | dos citas a `BT-179` y `BT-114` dentro de la descripción de `BT-115` |
| Cardinalidades en plano | 178 | las cuatro de la introducción, que explica qué es `1..1` |

### Cuatro trampas que solo enseñó el fichero

- **La cabecera ocupa tres renglones** y el tercero solo lleva las
  continuaciones «lidad» y «de dato». Sin quitarlas, el tipo semántico de
  varias filas acababa siendo «Texto de dato».
- **El sello de audiencia pública comparte renglón con contenido de verdad.**
  Tirar el renglón entero por llevar el sello perdía el número de `BT-ES-31`.
  Hay que tirar la pieza, no la línea.
- **Las páginas de después no son la tabla.** Detrás vienen las listas de
  códigos, con otras columnas. Sin cortar, la última fila se tragaba entera la
  lista de claves de régimen: 416 caracteres de nivel y media página de
  cardinalidad.
- **La cabecera de las listas de códigos no sirve para repartirlas.** En L5 el
  rótulo «Descripción» está en la x 333 y las descripciones de sus filas
  empiezan en la 170. La frontera hay que sacarla de los datos, no del rótulo.

### Y dos cosas que el borrador hace mal

Ninguna es de la extracción; los dos métodos las ven igual.

- `BT-ES-2` está puesto en dos términos que no tienen que ver.
- `BG-34`, `BT-179` y `BT-180` aparecen cinco veces cada uno. Esto sí es
  deliberado: el anexo los usa como cajones para cada grupo español, y lo que
  distingue una fila de otra es su ruta UBL. El identificador no es una clave,
  y conviene saberlo antes de construir un índice con él.

## Tres maneras de acusar en falso a una factura correcta de UBL 2.5

La solución pública solo admite UBL 2.5. Antes de escribir nada de eso hicimos
lo que dice la casa: pasarle al validador de hoy una factura de mañana y mirar
qué contesta. Contestaba mal de tres maneras distintas, y las tres eran del
mismo tipo —**no callarse, sino equivocarse en voz alta contra un documento que
está bien**—, que es peor que no saber.

### 1. El esquema de al lado

`_nombres_esperados` devolvía `("UBL-Invoice-2.1.xsd", "UBL-Invoice-2.0.xsd")`
para cualquier documento UBL, dijera lo que dijera su `UBLVersionID`. Con solo
la 2.1 instalada, una factura 2.5 correcta se medía contra el esquema 2.1 y
salía con un `XSD-ORDEN` por cada elemento nuevo. Reproducido con la suite:

```
Extra items in the left set:  'XSD-ORDEN'
Extra items in the right set: 'XSD-SIN-ESQUEMA'
```

Los elementos «inventados» eran los de verdad. `cac:CollectionInvoiceLine`, del
que cuelgan **trece** campos del CIUS español —suplidos, minoraciones, recargo
de equivalencia, régimen de grupo de entidades—, no existe en UBL 2.1: medido
contra los dos esquemas, sobre los 1.548 elementos globales de la 2.1 y los
2.129 de la 2.5.

La regla que lo cierra: **se puede subir de versión y nunca bajar.** Las dos
mitades, medidas y no supuestas:

| | Medido |
|---|---|
| Subir vale | los cinco ejemplos UBL de `ejemplos/` pasan igual el esquema 2.1 y el 2.5; la secuencia de `Invoice` pasa de 53 hijos a 62 sin perder ni mover ninguno |
| Bajar no | una factura con `DefaultLanguageCode` pasa la 2.5 y **falla** la 2.1 |

Y cuando el que toca no está, se dice cuál falta. No se comprueba la forma, y
se dice que no se ha comprobado.

### 2. «No declara conformidad con EN 16931», por declararla

`MARCADOR_EN16931` era un literal: `urn:cen.eu:en16931:2017`. La EN 16931-1
tiene **dos ediciones vivas** desde mayo de 2026, y el CIUS español pide la
otra:

```
urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0
```

que no empieza por el literal. Resultado: `conforme_en16931` en falso y BR-01
avisando de que el documento no dice a qué norma se ajusta, cuando lo decía
con la edición correcta. En EDIFACT lo mismo, que busca el marcador en los
bytes del FTX.

### 3. Suponer 2.1 cuando el documento ya había dicho quién es

Un UBL sin `UBLVersionID` se daba por 2.1 «que es lo habitual», y para lo que
circula hoy lo es. Pero un documento que declara el CIUS de la solución pública
en su `CustomizationID` **no puede ser 2.1**: la mitad de sus campos usan
elementos que ahí no existen. Ahora, sin versión y con ese CIUS, se deduce 2.5
y se dice por qué en el motivo de la detección. Lo que el documento declare
sigue mandando siempre: se rellena el hueco, no se corrige al que habla.

### De paso, dos cosas que había que ir a mirar

**UBL 2.5 ya no es un borrador.** Es OASIS Standard desde el 12-08-2026; la
Committee Specification del 15-04-2026 está superada. Los dos juegos de XSD
declaran exactamente los mismos elementos —923 en `CommonAggregateComponents`,
1.201 en `CommonBasicComponents`, comprobado— y solo cambian las cabeceras, así
que lo que se instala es el OS.

**`cac:ThirdPartyInvoicing` no existe en UBL.** Ni en la 2.1 ni en la 2.5: cero
apariciones en los 18 ficheros del paquete. Es la ruta que el anexo I le da a
`BT-ES-15`, y es un fallo del borrador con diagnóstico: la descripción del
propio campo dice que «ThirdPartyInvoicing» es el **valor** que hay que
escribir en `ServiceTypeCode`, y alguien lo pegó dentro del camino.

## El SHA-256 del paquete no lo podía rehacer nadie

El README ofrece la huella de `web/paquete.zip` para poder contrastar las
anclas de confianza que se reparten con la página. Para eso hace falta que
quien arme el paquete de las mismas carpetas obtenga el mismo fichero.

No lo obtenía. Tres vueltas seguidas, tres huellas:

```
33921e83…   19:38
092bac89…   19:39
16b8d8a7…   19:40
```

La diferencia está medida hasta el fondo: de las **436 entradas** del zip, las
436 con el contenido idéntico byte a byte y **una sola** con la fecha cambiada,
la del `PAQUETE.json` de dentro. `zipfile.writestr` con un nombre a secas le
pone a la entrada la hora del reloj.

Así que la huella probaba que la descarga llegó entera —que también hace
falta— y no lo otro, que es lo que estaba escrito. Ahora esa entrada lleva la
fecha del día en que se arma, que ya es un dato del propio paquete, y dos
vueltas dan el mismo fichero.

**Y la prueba de eso casi nace inservible.** Armar dos veces y comparar bytes
pasaba **con el fallo dentro**: las dos vueltas caían en el mismo segundo y la
fecha salía igual. Una prueba de reproducibilidad que no reproducía nada, que
es el disfraz más fino que se le ha visto aquí al fallo de siempre. Se arregla
moviendo el reloj una hora entre las dos vueltas, a propósito.

## Las rutas del anexo, andadas una a una por el esquema

Las cincuenta rutas UBL que el anexo I da para los campos españoles compilan
como XPath. Todas. Eso no dice nada: `cac:Loquesea/cbc:Tal` también compila.

Lo que hay que preguntarles es si el elemento existe **donde la ruta dice**,
que es otra cosa, y para eso hay que andarlas paso a paso desde `InvoiceType`
por el esquema de UBL 2.5. Andadas así, **49 llegan y una se rompe**:

```
BT-ES-15  Tipologia de tercero   «ThirdPartyInvoicing» no es hijo de PartyType
```

`cac:ThirdPartyInvoicing` no existe en UBL. Ni en la 2.1 ni en la 2.5: cero
apariciones en los 18 ficheros del paquete. Y el anexo se delata solo, porque
la descripción de ese mismo campo dice que «ThirdPartyInvoicing» es el **valor**
que hay que escribir en el código:

> Código que define el tipo de tercero informado. En el caso de un tercero que
> expide materialmente la factura en lugar del vendedor, se debe usar
> obligatoriamente el código "ThirdPartyInvoicing".

Alguien pegó el valor dentro del camino. Lo correcto es
`cac:ServiceProviderParty/cbc:ServiceTypeCode`, porque `ServiceTypeCode` cuelga
de `ServiceProviderPartyType` —cuyos hijos son `ID`, `ServiceTypeCode`,
`ServiceType`, `Party` y `SellerContact`— y no del `Party` de dentro.

### Diecisiete campos que preguntados devolvían lo de al lado

Seis rutas se las reparten diecisiete campos. Tal y como el anexo las publica,
preguntar por la oficina destinataria devuelve el órgano, y preguntar por la
identificación de la retención devuelve la del suplido. No falla: contesta otra
cosa, que es peor.

El anexo sí dice cómo se separan —en la descripción, no en la columna de la
ruta—, así que el predicado se puede escribir sin inventar nada:

| Se reparten | Lo que las separa, dicho por el anexo |
|---|---|
| `BT-ES-9/10/11` | `schemeName="Organo"`, `"Unidad"`, `"Oficina"` |
| `BT-ES-16/17` frente a `BT-ES-18/19` | `ChargeIndicator` «false» en el descuento, «true» en el cargo |
| `BT-ES-40` y `BT-ES-41` | lo mismo, dentro de la línea |
| `BT-ES-20/21/27/31/32` | su URN fijo: SUPL, MINO, REEQ, REGE, RETE |

Cada predicado lleva apuntado **en qué campo del anexo está escrito su valor**,
y una prueba va a esa descripción a comprobar que sigue estando. Sin eso, esto
dejaría de ser una lectura del anexo y pasaría a ser una opinión sobre él —y
las opiniones sobre la norma son exactamente lo que este validador no vende—.
Hizo falta apuntarlo: `BT-ES-17` y `BT-ES-19` no dicen «false» ni «true» en su
propia descripción, lo dice su hermano el indicador.

La única que queda repartida después de eso son `BT-ES-43` y `BT-ES-44`, las
dos en el `ValueQualifier` de un `AdditionalItemProperty`. Lo que las separaría
es el `cbc:Name` de esa propiedad, y el anexo no lo dice. Va declarada en
`sintaxis.AMBIGUAS` en vez de resuelta a ojo.

### Otras tres del mismo PDF

- **Cinco rutas escriben `/in:invoice/` en minúscula**, de cincuenta. En XML eso
  no es un descuido de estilo: es otro elemento, y no existe ninguno así.
- **El prefijo `aeat:` no está declarado en ninguna parte.** Se usa en 26 pasos
  y el anexo no da su namespace, así que como prefijo XPath no vale. Van por
  nombre local, que es lo honrado: lo que identifica cada extensión no es su
  namespace sino el valor de su `ext:UBLExtension/cbc:ID`, y ese sí se publica.
- **`BG-ES-1` no cuelga de donde dice**: escribe `aeat:Extension` y sus seis
  hijos escriben `aeat:InvoiceExtension`. Uno contra seis.

### Y una que explica el resto de la migración

**Trece de los campos españoles cuelgan de `cac:CollectionInvoiceLine`**, que no
existe en UBL 2.1. Ahí está, en una línea, por qué la solución pública no puede
admitir la versión que usa todo el mundo: no es una preferencia de la Agencia,
es que en 2.1 no hay dónde escribir los suplidos, las minoraciones, el recargo
de equivalencia ni el régimen de grupo de entidades.

## La página existía y para los buscadores no

Buscando `"glosa-e.com"` el 11-09-2026 no salía **ni una vez**. No estaba
abajo: no estaba. Y no es un fallo que se vea desde dentro, porque la página
funciona perfectamente para quien ya sabe la dirección.

Faltaba todo lo elemental —`robots.txt`, `sitemap.xml`, canónica, tarjeta
social— y faltaba lo que de verdad importaba aquí: **el catálogo de 160 códigos
era una sola página**. Un ancla no es una página. `incidencias.html#BR-CO-10`
es, para un buscador, la misma dirección que `incidencias.html`, así que ciento
sesenta puertas contaban como una.

Y son exactamente lo que la gente teclea, porque nadie busca «validador de
facturas electrónicas»: busca el código que le acaba de escribir su programa.

### Ciento sesenta páginas y veintisiete descripciones

Partirlo en 160 salió a la primera y estaba mal, con el disfraz de siempre: no
fallaba nada.

De los 160 códigos sólo **15 tienen explicación propia**; los otros 145 llevan
la de su familia, lo cual está dicho en la página y es correcto. Poniendo esa
explicación como descripción —que es lo natural— el recuento era este:

```
descripciones distintas: 27 de 160
```

Ciento cuarenta y cinco páginas saliendo en el buscador con la misma frase.
Nada se cae; simplemente quien viera cuatro resultados idénticos no sabría cuál
abrir. Se arregla empezando la descripción por el código, que es lo único que
los distingue a todos: 160 de 160, y con la respuesta —qué gravedad y de qué
norma— en la primera línea.

Hay prueba, porque esto se estropea solo: basta con que alguien «simplifique»
la descripción para volver a 27.

### Y una comilla que el guardián viejo cazó al vuelo

Al hacer que cada código del catálogo enlazara a su página, el enlace se
escribió así:

```python
f'<a class="codigo" href="./{nombre_de(uno.codigo)}">'
```

Sin escapar. Los códigos salen del fuente, pero el catálogo no los pasa por el
filtro de nombres de fichero, así que un código con una comilla dentro rompía
el atributo y metía detrás lo que quisiera. Lo cazó
`test_lo_que_viene_de_fuera_va_escapado`, que llevaba meses escrito esperando
exactamente esto.

## La frase sobre los demás que casi se publica sin medir

La portada nueva tenía que decir en qué se diferencia esto de los demás, y la
frase que salió sola fue la que se venía diciendo de memoria: *los validadores
gratuitos no miran la firma*.

Antes de escribirla se fue a mirar, el 11-09-2026. Y es falsa. El visualizador
de Facturae de firma-e publica que hace «Validación de Firma (verifica que la
firma de la factura sea correcta)»: no dice contra qué lista de autoridades, ni
si comprueba la revocación, pero decir que no la mira habría sido mentira. El
de aiDoks sí dice de sí mismo que no la verifica criptográficamente y remite a
AutoFirma o a VALIDe.

Así que la afirmación se estrechó hasta lo que se puede sostener: de los que se
miraron ese día, ninguno enseña sus comprobaciones corriendo, y de la firma
dicen poco o no dicen nada. Con fecha, con los dos enlaces a lo que cada uno
publica de sí mismo y con una dirección para avisar de que algo ha cambiado.

No la habría cazado ninguna prueba: una frase sobre un tercero es la única
clase de afirmación que este repositorio no puede medir sola. Por eso lo que
vigila el guardián no es el contenido sino la forma —fecha, enlaces, correo—,
que es lo único que hace falta para que cualquiera que la lea pueda desmentirla.

## Ocho reglas que la norma tiene y aquí se publicaron como inexistentes

El 12-09-2026 se publicó, en el README y en el mensaje del commit, que los
códigos compuestos del IVA eran 46 y no 54: que BR-AF-05, 06, 07 y 10 y sus
cuatro hermanos de BR-AG «no existen», y que anunciarlos sería inventarlos. Una
prueba lo sostenía provocando las reglas y viendo que no salían.

No salían porque la tabla de `iva.py` decía, sin haberlo leído en ninguna
parte, que la norma no ata el tipo ni el motivo del IGIC y el IPSI. El
esquematrón oficial los ata: tipo cero o positivo, y motivo de exención
prohibido, igual que en el tipo general.

**Reproducido** el 13-09-2026, antes de tocar el motor:

```
IGIC al 7 %, motivo «Régimen especial de Canarias»   →  sin incidencias
IGIC con tipo −7 % en la línea                       →  sin incidencias
```

La norma rechaza las dos. Y el mismo día, al medir contra el esquematrón,
apareció lo otro: treinta y nueve códigos del IVA publicados sin su cero
—`BR-S-8` donde la norma dice `BR-S-08`—, que es por lo que la primera cuenta
de coincidencias salió en 43 de 201 y, quitando ceros, en 82.

**Lo que lo cerró**: el estado `NO_NEGATIVO` y el motivo `PROHIBIDO` para las dos
categorías; una prueba con el texto de cada regla del esquematrón copiado; una
tabla que se niega a cargar con un estado que las reglas no saben comprobar; y
los códigos con dos cifras, con redirección permanente desde cada nombre viejo.
Las 179 facturas del corpus dan las mismas 1241 incidencias antes y después.

**Por qué pasó.** Tres comprobaciones que tenían que coincidir —la lista a mano,
la derivación y lo que sale al provocar— coincidían, y las tres salían de la
misma tabla. Coincidir entre sí no dice nada de si coinciden con la norma. Fue
el fallo de siempre con otro disfraz: todo en verde, y no era lo que se creía
haber comprobado.

De paso cayó otra frase con el mismo origen: que la lista L4 del anexo español
«añade L y M, que la UNCL5305 no tiene». Las tiene. L4 no añade: quita `K` y `B`.

## 107 casos en los que la norma decía otra cosa

El 13-09-2026 se trajeron las pruebas unitarias oficiales de la EN 16931 —las
que usa el comité para su esquematrón, una por regla— y se pasó este validador
por ellas. De las 90 reglas implementadas que tienen prueba, **41 discrepaban
en 107 de 567 casos**.

No eran 107 fallos: eran seis ideas equivocadas, y ninguna la había cazado
ninguna prueba, porque las pruebas estaban escritas desde las mismas ideas.

1. **Un céntimo de margen en todas las cuentas.** La norma no lo da en
   ninguna: las sumas de cabecera las exige exactas y la cuota de cada tipo la
   admite hasta una unidad. Aquí se aceptaba un total descuadrado en un céntimo
   y se rechazaba una cuota que la norma da por buena.
2. **Sin desglose, el IVA callaba.** Se paraba en BR-CO-18 y no miraba el tipo
   de ninguna línea.
3. **Los conceptos sin importe desaparecían**, y con ellos su categoría.
4. **Las categorías que admiten un solo desglose admitían varios.**
5. **Un total de impuestos repetido se leía una vez.**
6. **BR-01 opinaba** sobre lo que dice el identificador, cuando pide que esté.

**Reproducido** antes de tocar nada, en la propia prueba: la lista de las 107
se escribió en `tests/test_norma_oficial.py`, comprobada en los dos sentidos,
y se fue vaciando conforme se arreglaba. Cada arreglo se provocó quitándolo:
volver a pararse sin desglose, dejar de contar desgloses repetidos, dar a UBL
el borde de CII, volver al céntimo en BR-CO-10. Cada uno se puso en rojo en
su prueba y en la oficial.

**Lo que cambió en las 179 facturas del corpus**, medido antes y después: de
1241 incidencias a 1168, casi todo un aviso de BR-01 duplicado en EDIFACT.
Una sola queja nueva, y es la pista de lo siguiente: el mapa de EDIFACT lee el
grupo de impuesto de la cabecera como si fuera una entrada del desglose. Aquí se
escribió que de eso salían `BR-45` y `BR-46` en 37 de las 73 facturas EDIFACT de
terceros del corpus. No era así, y lo cuenta la sección siguiente.

## El TAX de la cabecera, leído como desglose, y un recuento que no se midió

**Qué pasaba.** El mapa de EDIFACT leía como entrada del desglose de IVA
cualquier grupo de impuesto colgado de la raíz. En EDIFACT cuelgan de la raíz
dos que no lo son: el de la cabecera —el grupo 6, el impuesto del documento
entero, sin base ni cuota— y los del resumen que no llevan el tipo VAT. El
esquematrón oficial de EDIFACT pide el grupo 54: después del `UNS`, función 7 y
tipo VAT. Con el de la cabecera dentro salían dos entradas donde había una, las
dos a medias, y con ellas `BR-45` y `BR-46` sobre facturas que traían su base y
su cuota.

**Lo que se había escrito, y no se había medido.** El 13-09-2026 se anotó que
de ahí salían los `BR-45` y `BR-46` de 37 de las 73 facturas EDIFACT de
terceros. 37 eran las facturas con la queja, y se les atribuyó una causa sin
mirarla. Medido el 14-09-2026, antes de tocar nada: 13 de las 85 facturas
EDIFACT del corpus traen un TAX en la cabecera, y las 13 tenían los dos errores;
otras 2 traen el del resumen sin el tipo VAT. En las demás la queja es buena: en
21 la base va escrita fuera del grupo de impuesto; en otras la cuota lleva el
cualificador 150, 161 o 176 en vez del 124. Las facturas con `BR-45` pasan de
37 a 25, y las que tienen `BR-46`, de 26 a 14.

**Reproducido** con la factura mínima de las pruebas y un
`TAX+7+VAT+++:::21+S` en la cabecera: dos entradas del desglose y dos errores.
Y con un `TAX+7+EXC` al final: dos entradas, una de un impuesto que no es el
IVA.

**Arreglado** con la ruta del oficial, y una prueba que compara el filtro con
la copia fijada. **Provocado**: sin la condición del `UNS` vuelve la entrada de
la cabecera, sin el filtro vuelve la del impuesto especial, y cada prueba se
pone en rojo.

**Lo que trajo detrás.** Diez facturas pasan de «a esta entrada le falta la
base» a «no hay desglose», que es lo que dice la norma de ellas. Para que eso
no mande a buscar un TAX que está a la vista, sale al lado
`EDI-IVA-FUERA-DEL-DESGLOSE`.

## Un céntimo para la base de cada entrada, que no era el de ninguna sintaxis

**Qué pasaba.** BR-{X}-08 —la base de cada entrada del desglose es la suma de
sus conceptos— se comprobaba con un céntimo de margen en todas las categorías.
Los dos esquematrones mantenidos no lo hacen así, y no coinciden entre sí: el de
UBL admite menos de una unidad en S, L y M y exige exactas las demás; el de CII,
al revés, salvo O, exacta en los dos. El céntimo fallaba en las dos direcciones:
dejaba pasar un céntimo que CII rechaza en el tipo general y UBL en la exenta.

**Por qué no se vio.** La tanda anterior lo dejó escrito como pendiente, y
leído a mano. Las pruebas oficiales no prueban ese borde, y el margen está en la
expresión de la vinculación de cada sintaxis, que no estaba en la copia.

**Arreglado** trayendo las tres vinculaciones a la copia oficial y leyendo el
margen de ahí: `test_norma_oficial` saca de la expresión de cada regla si
compara exacto, con `<` o con `<=`, y lo compara con `sintaxis.py`. Lo que pasa
por el margen sale como `IVA-BASE-TOLERADA`, aviso. EDIFACT y Facturae siguen a
UBL: el esquematrón de EDIFACT compara todo exacto, pero no ha cambiado de
contenido desde 2017, y hay una prueba que se pone en rojo si un día cambia.

**Provocado** seis veces: UBL con el margen de CII, EDIFACT con el de 2017, sin
margen, con la unidad justa, vuelta al céntimo y la clave con tipo en las
categorías de una sola entrada. Las seis, en rojo.

**En el corpus** cambia una factura, y para bien: una línea a tipo cero con un
20% escrito salía con tres errores y sale con el que tiene, `BR-Z-05`.

## La factura de ejemplo pagaba por transferencia sin decir a qué cuenta

**Qué pasaba.** `ejemplos/fe-0001.xml`, la factura Facturae que se enseña en la
portada y que usan cinco ficheros de pruebas y el banco, declaraba un plazo de
pago por transferencia —`PaymentMeans` 04— sin `AccountToBeCredited`. Una
transferencia sin cuenta no se puede hacer.

**Por qué no se vio.** Porque ninguna regla lo miraba. EN 16931 lo pide en
BR-61, que estaba pendiente, y el propio esquema de Facturae lo dice en la
documentación del elemento —«cuando la forma de pago sea transferencia este
dato será obligatorio»—, pero lo dice en una anotación y no en la estructura: el
XSD lo declara opcional y la validación de forma lo deja pasar. Las pruebas
comprobaban que el ejemplo sale conforme, y salía.

**Cómo se reprodujo.** Al implementar BR-61, la primera pasada de la suite dio
22 rojos; cinco eran este ejemplo, visto desde la cadena, la firma, el binding
de Facturae y la lista de ejemplos.

**Arreglado** poniéndole la cuenta —el IBAN de ejemplo de la documentación
bancaria— y volviendo a firmar con la clave de juguete de `tests/test_firma.py`.
Solo cambia el resumen del documento: el de las propiedades firmadas es el
mismo, y el script lo comprueba antes de firmar. El comentario de cabecera lo
cuenta.

**Provocado**: sin la cuenta vuelve BR-61, y con la cuenta y la firma vieja
sale `FIRMA-ALTERADA`, que es la firma haciendo su trabajo.

## Los ejemplos EDIFACT medían en una unidad que no es de la norma

**Qué pasaba.** `ejemplos/edi-0001.edi`, `edi-0002-cortado.edi` y
`edi-0003-una-de-cinco.edi` escribían la cantidad de cada línea como
`QTY+47:40:PCE`. `PCE` es la pieza en EANCOM, y EN 16931 pide la unidad de las
recomendaciones 20 y 21 de UN/ECE, donde la pieza es `H87`. `PCE` no está en la
lista de hoy ni en la del esquematrón de EDIFACT de 2017.

**Por qué no se vio.** Porque ninguna regla miraba la lista. BR-23 comprueba que
la unidad esté, y estaba; BR-CL-23, la de la lista, estaba pendiente. El
comentario de `tests/test_edifact.py` contaba incluso cómo se había añadido el
`PCE` para cumplir BR-23.

**Cómo se reprodujo.** Al implementar las listas de códigos, la suite dio trece
rojos. Siete eran esto: los tres ejemplos, el banco de la página —que valida
`edi-0001.edi`— y tres pruebas de EDIFACT montadas con la misma línea.

**Arreglado** cambiando `PCE` por `H87` en los tres ejemplos y en las pruebas.
Los EDIFACT no llevan firma, así que no hubo que rehacer nada más.

**Provocado**: con `PCE` vuelve BR-CL-23 en los tres. Y en el corpus es lo más
repetido entre las facturas EDIFACT: 32 de las 53 que cambian.

## Cuatro fallos que las pruebas no veían, vistos al revisar antes de publicar

**Qué pasaba.** Con las 223 reglas hechas o descartadas y la suite en verde, se
revisó línea a línea todo lo que no estaba publicado —diez commits— antes de
subirlo. Salieron cuatro fallos de verdad, y los cuatro pasaban las pruebas:

| Dónde | Qué hacía mal |
|---|---|
| BR-CO-03 en EDIFACT | El código de devengo se buscaba con fecha, y en EDIFACT es el cualificador del DTM y va sin ella. Un `DTM+131` con fecha y un `DTM+3` sin fecha no daban el error, y la vinculación oficial sí lo da |
| Los totales de EDIFACT | Se leían en cualquier grupo colgado de la raíz, también en los de impuesto. EANCOM repite ahí el `MOA+176` con el impuesto de cada tipo, y BR-DEC-13 informaba del importe de un tipo como si fuera el total de la factura |
| BR-51 | Se quitaban todos los espacios del número de la tarjeta antes de contar. La vinculación los junta, no los quita: `123456 7890` son once caracteres y salía sin aviso |
| El aviso del IVA fuera del desglose | Contaba un `TAX+7+EXC` como IVA al que le falta decir que lo es. Un grupo que dice qué impuesto es y no es el IVA no está mal escrito |

Y una afirmación de más: el comentario de BR-17 decía que las dos
vinculaciones solo difieren en el nombre con el que comparan. La de CII
compara también el registro legal, y aquí se hace como en CII. Ahora lo dice,
y hay una prueba.

**Por qué no se vio.** Las pruebas estaban escritas desde el mapa: montaban el
DTM+3 con fecha porque la ruta pedía fecha, y los totales sin grupo de impuesto
detrás. Probaban lo que el código hacía, no lo que dice la vinculación.

**Cómo se reprodujo.** Una prueba por fallo, escrita antes del arreglo; las
cuatro en rojo. La de BR-17 ya pasaba, porque ahí lo que fallaba era el
comentario.

**Arreglado** en el mapa de EDIFACT, en `modelo.py` y en `edifact.py`. El corpus
no cambia: 1376 incidencias antes y después, en los mismos ficheros.

**Quedan dos limpiezas sin hacer, a propósito.** `decimales.py` y
`listas_de_codigos.py` repiten dos lectores pequeños de `modelo.py`, y no son
iguales: el de las listas no quita espacios, porque el tipo de un adjunto se
compara tal cual. Y `listas_de_codigos.lista()` busca cada lista por su nombre;
una errata saldría al validar y no al importar, pero la prueba que recorre
todas las filas la caza igual.

## Cinco cosas mal dichas o mal hechas, vistas al escribir las reglas del anexo I

Las reglas del anexo se escribieron leyendo otra vez el PDF entero, y no la
tabla que ya se tenía de él. Salieron cinco cosas, y ninguna rompía una prueba.

**1. Las descripciones de cinco listas estaban corridas una fila.** L3A, L3B,
L3C, L5 y L6 se leían por coordenadas, y en una celda de dos renglones el
código va centrado entre los dos: al repartir por altura, el primer renglón
caía en el código de arriba. El 01 de L6 decía «País Vasco y Navarra», que es
justo lo que excluye, y el 02 decía «Navarra». Los códigos estaban bien, que es
lo único que se comprobaba. *Reproducido* con una prueba que compara
descripciones concretas con el PDF, en rojo. *Arreglado* leyendo las listas en
el orden en que el PDF escribe el texto, que va por celdas. Provocado dos
veces: sin filtrar las minúsculas, el «DE» de una cabecera sale como código; sin
quitar la cabecera de cada página, su número también. Las dos en rojo.

**2. «El anexo no dice cuál» era falso.** `BT-ES-43` y `BT-ES-44` —situación del
inmueble y tipo de impuesto nacional— van en el mismo `ValueQualifier` y
estaban declaradas en `sintaxis.AMBIGUAS` como imposibles de separar. El anexo
lo dice en la fila de al lado: `BT-160` fija el nombre de la propiedad en
«RCAT» y en «REGI». *Reproducido* con una línea que lleva las dos propiedades:
la situación del inmueble devolvía «IVA». *Arreglado* con dos distintivos más,
y `AMBIGUAS` queda vacío. En la misma lectura salió que debajo del título de
cada lista de claves de régimen hay un «CALIFICADOR IVA», «IGIC» o «IPSI», que
el extractor tiraba y es el valor de `BT-ES-44`.

**3. Eran dieciséis campos, no diecisiete.** El README, este fichero y
`sintaxis.py` decían que el anexo reparte seis rutas entre diecisiete campos.
Contados son dieciséis. Ahora los cuenta una prueba.

**4. El comentario de `factura._SOBRA_SI` decía lo contrario que el código.**
«Cuando la queja de la izquierda ya ha saltado, la de la derecha sobra», y el
código quita la de la izquierda cuando está la de la derecha. Se vio porque la
primera entrada nueva se escribió fiándose del comentario, y la prueba de
reproducción siguió enseñando la queja que tenía que desaparecer.

**5. BR-CO-16 daba por mala una factura del CIUS hecha como manda el anexo.**
El anexo suma al total a pagar los importes de terceros —suplidos,
minoraciones, recargo, retenciones— y la edición de 2017 de la norma no los
conoce. *Reproducido* con una factura del CIUS con un suplido de 50 euros:
`BR-CO-16` en error, esperando 121,00 donde había 171,00. Esos importes no se
pueden sumar aquí porque el anexo no dice dónde se escriben (`BT-179` no tiene
ruta), así que no se arregla la cuenta: se dice. Con líneas de cobro sale la
nota `SPFE-TOTAL-A-PAGAR` y BR-CO-16 no sale; sin ellas, se comprueba como
siempre. Las dos cosas tienen prueba, y quitar la poda las pone en rojo.

**Por qué no se vio antes.** Las cuatro primeras son lecturas que se dieron por
buenas porque salían con buena pinta: una tabla de códigos correctos, una
frase razonable sobre lo que el anexo no dice, una cifra, un comentario. La
quinta no podía verse: hasta hoy ninguna regla miraba una factura del CIUS.

**Las reglas en sí**, 24 códigos `SPFE-`, están en el README. Se provocaron 37
roturas del módulo, de su cableado y de la frase de alcance, y las 37 salieron
en rojo.

## Tres maneras de dar por buena la firma de otro, y la nota que nombraba al inocente

Salieron de una auditoría de seguridad del 15-09-2026 sobre el proyecto entero.
Las tres son de la misma familia y ninguna necesita la clave privada de nadie:
basta el certificado público de la víctima —que viaja en cada factura que
manda— o una firma suya sobre cualquier otra cosa.

**El fondo es uno solo.** `firma.py` sabía decir «no he podido comprobar esta
firma», y lo decía bien. Pero `cadena.py` miraba por su cuenta, y escribía
igual la única frase del informe que nombra a una persona:

```
[CONFIANZA-ANCLA] La firma de «EMPRESA VICTIMA SL» llega a «AC DE JUGUETE»
en 2 eslabones. Esta validación se fía de esa autoridad porque es un ancla…
```

### 1. Una firma que nadie ha comprobado

**Qué pasaba.** Con un `SignatureMethod` inventado —`urn:un-algoritmo-inventado`
o cualquier URI que no esté en la tabla— el valor de la firma no se comprueba y
sale un aviso, que es lo correcto. Lo que no era correcto es que la cadena
siguiera adelante. Con eso, cualquiera fabrica una factura entera, le pone el
certificado de la víctima, rehace el resumen del documento —que es un hash, no
hace falta clave— y pone basura donde va la firma.

**Cómo se reprodujo.** Una autoridad de juguete instalada como ancla, un
certificado suyo a nombre de «EMPRESA VICTIMA SL» y una factura del atacante:

```
sin errores, 2 aviso(s)   ← la falsificada
sin errores, 2 aviso(s)   ← la auténtica
```

El mismo veredicto, y en las dos la nota con el nombre de la víctima. En
consola, las dos salen con código 0.

**Arreglado**: `cadena.reglas_de_documento` y `cadena.sellos_del_documento`
preguntan antes a `firma.examinar(...).verificada`, que es «el valor cuadra,
ninguna referencia está alterada y alguna cubre la factura». Sin eso no se dice
de quién es el certificado ni se escribe la nota. No se añade ninguna queja
nueva: de que la firma no se sostiene ya se queja `firma.py`, con el motivo.

### 2. Una firma auténtica sobre otra cosa, y el señuelo

**Qué pasaba.** Nadie comprobaba **qué** cubría la firma. Una firma XAdES real
de la víctima sobre un acuse de recibo —referencia por identificador,
canonicalización exclusiva— se despega y se cuelga de una factura inventada:
verifica entera, porque lo que cubre viaja con ella.

Y la variante de dentro de un fichero: en una firma envolvente, un `Facturae`
de mentira metido delante del que está firmado. Las reglas leen el primero
—`formato.detectar`, `facturae.py` y `en16931.py` se quedan con
`//*[local-name()='Facturae']`— y la firma sigue cubriendo el segundo.

**Cómo se reprodujo.** Las dos, con la clave de juguete de los tests: la
trasplantada salía «sin errores, 3 avisos», y el señuelo enseñaba en el informe
el total inventado con la firma dada por buena.

**Arreglado** con `FIRMA-NO-CUBRE`, en error: tiene que haber una referencia
comprobada que cubra el elemento que las reglas leen como factura. Una
contrafirma es el caso aparte y lo que tiene que cubrir es el valor de la firma
de la que cuelga. De paso, tres agujeros del mismo sitio:

| Dónde | Qué pasaba |
|---|---|
| `referencias_de` | Las `Reference` se cogían con `.//`, o sea de cualquier parte de la firma. Un resumen lo rehace cualquiera: bastaba colgar de un `ds:Object` una referencia al documento. Con el `SignedInfo` fuera de su sitio, además, no había valor que comprobar y el informe salía **sin una sola queja de firma** |
| `_con_identificador` | Con dos elementos con el mismo `Id`, se cogía el primero. Ahora se dice que no se sabe cuál es el firmado |
| `certificados_de` | El certificado salía del primer `X509Certificate` de toda la firma, no del `KeyInfo`. No falsifica nada —la firma tiene que cuadrar con el que se elija— pero acusa en falso a un documento correcto al que alguien cuelgue un certificado de adorno |

Lo mismo estaba en `tsl.py`, que es de donde salen las anclas: comprobaba que
la firma cubriera la lista entera —eso ya estaba bien visto— pero buscando las
referencias con `.//`, así que una referencia `URI=""` colgada de un `ds:Object`
daba por cubierta una lista a la que se le hubieran añadido autoridades después
de firmarla.

### 3. La fecha y el certificado que la firma declara

**Qué pasaba.** `SigningTime` y `SigningCertificate` se leían con `.//` y
mandaba el primero en orden de documento. Un `ds:Object` sin firmar, metido
detrás del `KeyInfo` —o sea, delante del de verdad—, no rompe ningún resumen
porque no lo cubre nadie.

Con eso, alguien que ni firmó ni tiene clave borraba un error del informe:

```
4a  firmada con el certificado ya caducado   1 error(es)  ← FIRMA-CADUCADA
4b  con un SigningTime inyectado             sin errores
```

Esa misma fecha es con la que se mide la revocación, y el `SigningCertificate`
inyectado tapaba justo la sustitución de certificado que esa comprobación
existe para cazar.

**Arreglado**: las dos cosas se leen de las `SignedProperties` que una
referencia del `SignedInfo` cubre y cuyo resumen cuadra (`propiedades_firmadas`).
Unas propiedades XAdES que la firma no cubre ya no la hacen XAdES: sale
`FIRMA-NO-XADES` diciendo que están sin firmar. Y una fecha con el resumen roto
no se usa **para nada**, ni para dar por bueno ni para acusar.

### 4. Y la palabra que quedaba: «firmado»

**Qué pasaba.** Cerradas las tres, la factura falsificada del caso 1 ya no
nombraba a nadie y llevaba su aviso. Pero la línea de estado se escribía en la
detección, que no comprueba nada, y salía así:

```
Facturae v3.2.2 (factura) · firmado — sin errores, 2 aviso(s).
```

«Firmado» ahí es el titular, y lo único que había detrás era que el documento
traía un bloque `Signature`. Es la misma clase de fallo que los tres de arriba
—afirmar de la firma algo que no se ha comprobado—, solo que en la línea que se
lee primero.

**Arreglado**: cuatro etiquetas, y las dos malas separadas. `· firmado` solo si
todas las firmas se sostienen; `· firma que no se sostiene` si se ha mirado y
está mal; `· firma sin comprobar` si no se ha sabido mirar —un algoritmo fuera
de la tabla, y RSA-PSS es legítimo—; `· con firma` cuando nadie la ha mirado.
Con varias firmas manda la peor.

El estado sale de los mismos exámenes con los que se escriben las glosas, una
sola pasada para los dos. Que cada uno mirara por su cuenta es justo lo que
produjo el caso 1.

### 5. Y la frase que resume el informe, diciendo lo mismo

**Qué pasaba.** «Qué se ha mirado» es la frase que dice cuánto vale el «sin
errores». Sobre cualquier lote con firmas decía «se ha comprobado que las
firmas no estén rotas», aunque la única firma fuera una que nadie había sabido
comprobar. El documento lo decía en su línea de estado y en su aviso; el
resumen del informe entero se lo callaba, y es el que se lee para saber qué
vale el veredicto.

**Arreglado**: la promesa cuelga de haber comprobado alguna
(`con_firma_comprobada`), y las que no se han sabido mirar se cuentan al otro
lado, donde va lo que no se comprueba. Una firma mirada y rota sí cuenta como
comprobada: ahí la promesa se cumple. Sobre una factura falsificada sola, la
frase queda así:

```
No se comprueba la firma de este documento —su aviso dice por qué—,
ni si lo que dice la factura es cierto.
```

### Lo que se probó, y cómo

31 pruebas nuevas, las 31 en rojo antes del arreglo. Después, **14 roturas
provocadas** —quitar la puerta de `cadena.py`, volver a `.//Reference`, quitar
la exigencia de cubrir, resolver el identificador repetido a ciegas, leer la
fecha de cualquier sitio, no comprobar el resumen de las propiedades, sacar el
certificado de cualquier parte, devolver `tsl.py` a `.//`, volver a poner
«firmado» en las cuatro etiquetas, dar el estado por bueno en cuanto hay firma,
no distinguir rota de sin comprobar, pintar la cabecera sin mirar en qué quedó
la firma, y devolverle a la frase del final las firmas que no ha mirado, de las
dos maneras— y las 14 salieron en rojo.

La suite entera en verde, y **las 19 facturas firmadas del corpus dan el mismo
informe que antes**, código por código y campo por campo: lo que se ha cerrado
no era una firma legítima de nadie. De los 20 ficheros con bloque de firma del
corpus, los 10 que además son facturas reconocidas siguen diciendo `· firmado`;
los otros 10 son XAdES sueltos que no son facturas y su línea sigue siendo
«Formato no reconocido».

**Lo que cuesta**: 0,9 ms de examen en una factura de 3 KB y 160 ms en una de
1 MB con 4.000 líneas, tres veces por firma. Un 4 % del tiempo de validar la
grande. Sin caché a propósito.

**Lo que sigue abierto y no es de aquí**: un certificado sin `basicConstraints`
ni `keyUsage` se sigue aceptando como emisor —RFC 5280 dice que no—, las
extensiones críticas de un certificado no se aplican, y el `keyUsage` de la
hoja no se mira. Es la revisión de `cadena.py`, no la de `firma.py`.


## Cinco puertas que se abrían solas: la parte alta de la auditoría

Los puntos 4 a 8 de la auditoría del 15-09-2026. Ninguno falsifica una factura,
como los tres primeros; todos hacen algo peor de lo que prometen sin decirlo.
Los cinco se reprodujeron antes de tocar nada.

### 4. `--sitio` borraba la carpeta que se le dijera

**Qué pasaba.** Montar el sitio empieza por `shutil.rmtree(destino)`, sin mirar
qué es el destino. Probado en una carpeta temporal que hacía de carpeta de
trabajo, con un `anclas/` y un `Proyecto 1/` dentro: los dos borrados, y código
de salida 0. Un `--sitio ..` lanzado desde Factura-e hacía eso de verdad.

**Arreglado**: cada montaje deja un testigo, `.montado-por-glosa`, y lo deja
**lo primero**, para que un montaje que se para a medias se pueda repetir. Solo
se borra una carpeta vacía o una con el testigo; la carpeta desde la que se
trabaja, o una que la contenga, no se borra nunca, lleve lo que lleve. La
misma prueba de antes sale ahora con código 2, `NoEsUnSitio`, y los dos
ficheros en su sitio.

Un sitio montado antes de que existiera el testigo también se niega: se borra a
mano una vez. Aceptarlo por parecerse a un sitio habría sido acordarse de algo
para siempre.

### 5. La puerta de producción, con nueve maneras de pasar

**Qué pasaba.** El gancho de Claude Code corría la suite antes de un push, y
decidía si la orden era un push con una expresión regular. No reconocía
`git -C . push`, `git -c x=y push`, `git.exe push` ni la ruta entera de git; un
`--dry-run` en cualquier parte lo apagaba, hasta en un comentario; solo miraba
el primer `cd`. Al reproducirlo salieron dos más: `Set-Location` de PowerShell
y `git send-pack`. Y dos de fondo: probaba la carpeta, no lo que se empujaba, y
**un push desde la consola no pasaba por él**. Vercel no corre las pruebas.

**Arreglado cambiando quién guarda la puerta.** La suite la corre ahora git, en
`.githooks/pre-push`, que git llama en todo push de la copia —desde Claude
Code, desde la consola, con un alias—, con las referencias que se empujan por
la entrada. Se niega si lo empujado no es HEAD o si hay cambios sin commit, y
así lo probado es lo publicado; y si la suite no pasa, se cuelga o no arranca.

Medido con git 2.55 en un repositorio de usar y tirar antes de escribirlo:
git llama al gancho también con `--dry-run`, y **no** lo llama con
`--no-verify` ni con `git send-pack`. Eso es lo que queda para el gancho de
Claude Code, que pasa a portero: se niega a esas dos, a cualquier orden que
toque `core.hooksPath` —con `-c`, con `--config-env`, con
`GIT_CONFIG_PARAMETERS`, con `git config`— salvo para ponerlo en `.githooks`,
a un alias con `--no-verify` dentro, y a empujar Factura-e mientras el gancho
de git no esté puesto. Con los otros proyectos de la carpeta no se mete.

`core.hooksPath` es configuración local y no viaja: está puesto en esta copia,
y `CLAUDE.md` dice cómo ponerlo y cómo provocarlo. Provocado aquí, empujando a
un repositorio desnudo temporal con la carpeta sin commit: se niega en 0,8 s.

### 6. Dos ficheros que se llamaban igual eran uno

**Qué pasaba.** El lote identificaba cada fichero por `camino.name`. En
consola, con `a/factura.xml` y `b/factura.xml` duplicados y `c/factura.xml`
distinto: «0 correctos, 3 con errores», y la queja decía «las dos vienen en
factura.xml». En el navegador era peor: el nombre se limpia antes de escribirlo
en el disco virtual, `factura ñ.xml` y `factura ç.xml` acababan los dos en
`factura__.xml`, el segundo pisaba al primero y **el primero no se validaba
nunca**.

**Arreglado**: cada fichero tiene un nombre único en el lote. De la ruta se
sube por las carpetas hasta que se distinguen —`a/factura.xml`—; lo que sigue
repetido se numera. En el navegador cada fichero va a su propia carpeta y el
informe usa el nombre que tenía en el ordenador de quien lo soltó. La consola
dice ahora «1 correcto, 2 con errores» y nombra `a/` y `b/`.

### 7. Un importe raro se llevaba el informe entero

**Qué pasaba.** `Decimal` lee «NaN», «Infinity» y números de treinta cifras
sin quejarse. La primera comparación o el primer redondeo a céntimos lanzaba
`InvalidOperation` y salía «no se ha podido validar»: se perdía la forma, la
firma, todo, por un campo. La sonda de la auditoría cambia cada número de los
ejemplos por diez valores raros: **198 combinaciones** tumbaban el informe.

**Arreglado en dos sitios.** El lector de números solo acepta la forma de
`xs:decimal` —signo, cifras y un punto—, que es también la de los patrones de
Facturae: lo demás se lee como lo que es, texto que no es un número, y de eso
se queja el esquema, sin una segunda queja de aritmética hecha con él. Y las
reglas corren con 400 cifras de precisión, en un contexto local, así que un
importe de treinta cifras —válido para `xs:decimal`— se mide en vez de
reventar. Aquí solo se multiplica, se suma y se divide entre potencias de diez:
la precisión no alarga ninguna cifra que se enseñe.

La misma sonda: **0 combinaciones**. Lo que cuesta, medido alternando las dos
precisiones: los siete ejemplos, 1.422–1.430 ms con 400 y 1.412–1.433 ms con
28; una factura de 1.000 líneas, 4.121 ms y 4.112–4.124 ms. No se distingue del
ruido.

### 8. «Qué se ha mirado» prometía lo que no se miró

**Qué pasaba.** Tres promesas falsas en la frase que dice cuánto vale el «sin
errores»:

```
1. dos copias de un EDIFACT     «2 correctos», y la frase: «se ha comprobado el código único»
2. firma con CADENA-DESCONOCIDA  la frase: «que ese certificado lleve a una autoridad de confianza»
3. ficheros que no existen       la frase: «se ha comprobado el código único»
```

**Arreglado**: el código único se promete solo si hay alguna factura UBL, CII o
Facturae; con EDIFACT se dice que su código único no se comprueba. Que la
cadena llega se promete solo si llega, contado por firma —una nota de
confianza por cada firma que se sostiene— y lo que no llega va al otro lado:
«no se comprueba de quién es el certificado de este documento —su aviso dice
por qué—». Y un lote sin nada legible dice «no se ha comprobado nada», en vez
de una frase que acababa en «se ha comprobado .».

Tres pruebas pedían la promesa falsa y se han cambiado: una de `test_cadena`,
una de `test_paquete` y una comprobación del banco, las tres sobre el ejemplo
firmado, cuya cadena no llega a ninguna de las anclas del paquete.

### Lo que se probó, y cómo

Cada uno reproducido primero, con la prueba de concepto de la auditoría o una
nueva. Después, **42 roturas provocadas** con un guion que mete cada fallo, corre
las pruebas que lo tienen que cazar y lo deshace: 4 del punto 4, 18 del 5, 7 del
6, 6 del 7 y 7 del 8. Las 42 en rojo. Dos salieron en verde la primera vez y
destaparon pruebas que no probaban nada: la de que la precisión no se queda
cambiada leía el «antes» ya contaminado por otra prueba, y ninguna tenía un
documento con dos firmas de las que solo llegara una. Las dos se rehicieron
hasta ponerse en rojo.

La suite entera, 2168 pruebas, en verde.


## La suite solo pasaba en esta carpeta

El 16-09-2026 la suite pasó a correr también dentro de GitHub, en cada push y
cada pull request (`.github/workflows/pruebas.yml`), para que dejara de
depender del gancho de la copia que empuja. Antes de escribir el flujo se corrió
la suite en una copia recién clonada, que es lo que ve GitHub. Salió en rojo.

### Qué pasaba

**En una copia limpia, en Windows: 6 fallos, 2128 pasan, 34 saltadas.** Aquí
pasaban porque esta carpeta tiene lo que no se versiona:

- las dos de `test_paises` leían `esquemas/Facturaev3_2_2.xsd` y su docstring
  decía que ese esquema «sí está en el repositorio»;
- tres de `test_edifact` validaban dos facturas de terceros de `muestras/`, y
  sin ellas la frase decía «no se ha comprobado nada»;
- `fe-0001.xml` en `test_ejemplos` decía `CADENA-DESCONOCIDA` aquí, con
  `anclas/` instaladas, y `CADENA-SIN-ANCLAS` en la copia limpia. `conftest.py`
  ya aislaba los esquemas por esta misma razón, y las anclas no.

**En GitHub, en Linux, dos más: 2 fallos, 2138 pasan, en 23 s.**

- **El banco escribía en la raíz del disco.** `web/prueba.py` monta anclas en
  `/anclas`, `/anclas-tsl` y cuatro más: en el navegador es el disco virtual de
  Pyodide, y en `test_banco.py` era el disco de quien corría la suite. En Linux,
  `PermissionError` y cinco comprobaciones críticas en rojo. En Windows no
  fallaba, que es peor: había seis carpetas `anclas*` en `C:\` desde el
  27-08-2026, reescritas en cada vuelta y reutilizadas de una a la siguiente.
- **La huella de la copia oficial dependía del sistema.** Se ordenaba con
  `sorted` sobre rutas, que en Windows no distingue mayúsculas y en Linux sí:
  `cii/BR-CO-15-2.xml` iba delante de `CreditNote-unit-UBL/` en una máquina y
  detrás en la otra. La misma copia daba dos huellas.

### Arreglado

- `test_paises` lee el esquema de `web/paquete.zip`, que se versiona y es lo
  que se publica.
- `test_edifact` usa `ejemplos/edi-0001.edi` y `ejemplos/f-0001.xml`: lo que se
  prueba es la frase, no aquellas facturas.
- `conftest.py` aísla también las anclas, y `fe-0001.xml` dice en la tabla lo
  que dice sin ellas. Con un ancla que no le corresponde ya lo fija
  `test_cadena.py`, con un almacén propio. Las revocaciones se probaron igual,
  con una lista ilegible en el entorno, y la suite salía idéntica: no se aíslan.
- El banco escribe en `DISCO_DEL_BANCO`, que en el navegador sigue siendo `/` y
  en `test_banco.py` una carpeta temporal nueva. Una prueba mira que monte ahí y
  que no quede ninguna ruta `/anclas` en el banco. Las seis carpetas de `C:\` no
  se han borrado desde aquí: son de fuera del proyecto.
- La huella ordena por el texto de la ruta. El valor fijado cambió sin que
  cambiara un byte, y en Windows sale ahora el mismo que en Linux.

Y para que el verde de GitHub hable de lo mismo que el de aquí,
`requisitos-pruebas.txt` fija las versiones, y `test_pruebas_en_github.py`
comprueba que lo instalado es lo fijado, que el Python es el del flujo, que se
dispara sin filtros, que hay un solo trabajo y se llama `suite`, que pytest no
lleva opciones de más ni `continue-on-error` ni `if:`, y que las acciones van
por commit.

### Lo que no se ha podido cerrar

Que `main` **rechace** lo que no pase. Eso es la protección de la rama, y en un
repositorio privado con el plan gratuito GitHub no la ofrece: la API contesta
403, «Upgrade to GitHub Pro or make this repository public», tanto a la
protección clásica como a los rulesets. Medido con un pull request de
provocación con la comprobación en rojo: GitHub lo daba por `MERGEABLE`. Hoy el
rojo de GitHub avisa, y a la vista, pero no impide.

### Lo que se probó

- **27 roturas provocadas**, las 27 en rojo: 16 del flujo y sus versiones, 7 de
  las pruebas que dependían de la carpeta y 4 de lo de Linux.
- Copia limpia en Windows: **2140 pasan, 34 saltadas, 0 fallos**.
- GitHub: **2141 pasan, 34 saltadas**, 25 s de suite y 45 s de trabajo.
- Un rojo de verdad dentro de GitHub, con una aserción que solo falla allí para
  poder empujarla sin saltarse el gancho: en rojo en el push y en el pull
  request, con el fallo en el registro. El pull request se cerró sin fusionar y
  la rama se borró.

La suite entera, 2175 pruebas, en verde.


## Siete de la parte media: lo que decía de más y lo que no miraba

Los puntos 9, 10 y 15 a 19 de la auditoría del 15-09-2026. Ninguno falsifica
una factura; cinco de los siete hacen lo mismo con distinto disfraz: **afirmar
algo que no se ha comprobado**, o negar algo correcto.

### 9. Un certificado que nunca dijo ser autoridad, haciendo de autoridad

**Qué pasaba.** `basicConstraints` es opcional en X.509: un certificado puede
decir «no soy autoridad», decir «lo soy», o no decir nada. Se miraba solo el
primer caso. Reproducido con una «intermedia» sin esa extensión, con un
`keyUsage` puesto a mano: la cadena **llegaba**, tres eslabones, y el informe
daba por buena la firma de un «Banco Importante SA» emitido por quien quiso.

Y dos cosas más que la auditoría nombraba al lado: las extensiones **críticas**
que este validador no sabe leer se ignoraban —`nameConstraints` es la que
importa: limita a qué nombres puede emitir una autoridad—, y del certificado
que **firma el documento** no se miraba su `keyUsage`, solo el de los que
emiten certificados.

**Arreglado.** Un eslabón tiene que declararse autoridad; una extensión crítica
que no se entiende corta la cadena diciendo cuál es, en vez de afirmar que
llega; y un certificado que declara usos y no incluye `digitalSignature` ni
`contentCommitment` saca `FIRMA-USO-NO-PERMITIDO`, aviso —la firma puede
cuadrar; lo que no cuadra es para qué se emitió—. Nada de esto se le exige al
**ancla**: no es un hallazgo, es la decisión de quien montó el almacén, y X.509
tampoco procesa sus extensiones.

**Medido antes de decidirlo**, que es lo que dice hasta dónde se puede apretar
sin inventar problemas: las 268 anclas instaladas declaran ser autoridad las
268, y dos traen una crítica que este validador no lee (`extendedKeyUsage` y
`certificatePolicies`). En 38 certificados sacados de 20 facturas reales de
`MuestrasFE/` y `Pfactura3/`: todas las intermedias declaran `cA` y
`keyCertSign`; los dos únicos con una crítica desconocida son certificados de
sello de tiempo, no intermedias; y de los 36 que declaran usos, todos los que
firman traen `digitalSignature` o el no repudio.

### 10. Una firma sin `SignedInfo` que no decía nada

La auditoría la encontró muda en una instalación sin esquemas. Ya no lo está:
lo cerró el trabajo sobre los tres puntos críticos del 16-09-2026, y hoy saca
`FIRMA-VACIA`, `FIRMA-NO-XADES` y `FIRMA-SIN-COMPROBAR`, con la línea de estado
diciendo «firma que no se sostiene». Lo que faltaba era la prueba que lo fija,
y ahora está.

### 15. «Conforme EN 16931» en una factura con dos errores

La línea de estado salía así: `UBL v2.1 (factura) · conforme EN 16931 — 2
error(es)`. Contradiciéndose en ocho palabras. Lo único que se había mirado
para escribir esa etiqueta es el identificador de perfil que el documento lleva
dentro, y lo escribe quien emite la factura. Ahora dice **«· dice seguir
EN 16931»**: si cumple o no lo dicen los errores.

### 16. Un NIF correcto que se rechazaba entero

`M1234567L` es un NIF válido y salía «el formato no corresponde a un NIF, NIE
ni CIF español», o sea `CU-01` en error sobre una factura buena. Las claves K,
L y M son de **persona física** —menores de catorce años, españoles que viven
fuera, extranjeros sin NIE— y estaban en la tabla de tipos de entidad, con el
control del CIF: una letra de la J a la I o un dígito. El suyo es el del DNI,
el resto de dividir entre 23, y por eso ni siquiera pasaban la forma.

Ahora se comprueban como lo que son. Se aceptan solo con siete **dígitos**: la
AEAT publica la composición —letra, siete caracteres y un carácter de
verificación— pero no el algoritmo, y con letras en medio no hay nada que
dividir entre 23. Lo que no se sabe comprobar no se da por bueno.

### 17. El hallazgo n.º 1 del proyecto, de vuelta por EDIFACT

Una factura alemana al 19 % recibía `IVA-TIPO`: «19% no es un tipo de IVA
vigente en España». Es exactamente el fallo grande que abre este documento
—reglas españolas cayendo sobre facturas de fuera— volviendo por el único
formato que no es XML. `pais_emisor` tenía una tabla de rutas con UBL y CII, y
EDIFACT no estaba: contestaba «no se sabe» siempre, y como de EDIFACT no se
sacan códigos únicos, la pista de reserva se quedaba sin nada que mirar y las
daba todas por españolas.

Ahora el país se lee del NAD del sobre con el mapa de sintaxis, como el resto
de los campos de EDIFACT, y si no está queda el número de IVA del vendedor.

### 18. Tres bytes del Bloc de notas

Un `.edi` guardado con el Bloc de notas de Windows lleva delante la marca de
orden de bytes de UTF-8. Con ella, la tira deja de empezar por UNA, UNB o UNH:
el fichero se caía al otro lado —«no es XML válido y tampoco EDIFACT»— y no se
comprobaba **nada**. En XML no pasa: el parser la reconoce.

Al arreglar la detección salió un segundo fallo detrás, que es el que enseña
por qué esto se prueba dos veces: `es_plano` decidía aparte si la tira se podía
leer y también miraba los bytes con la marca. El resultado era peor que el
original, porque no se veía: la factura se reconocía y salía un `SIN-SOPORTE`
—«identificado, pero no se ha podido leer»— sobre un documento perfectamente
legible.

### 19. La misma queja, dos normas distintas según dónde se leyera

De qué norma sale cada código estaba escrito dos veces: en el informe y en la
ficha del catálogo publicado. El comentario de la segunda decía «el mismo
reparto que `factura.origen`» y explicaba por qué se copiaba —importar
`factura` arrastra lxml entero para contestar una tabla de prefijos—. La razón
era buena; el resultado, que **16 de los 371 códigos no decían lo mismo en los
dos sitios**:

- los doce `IVA-*` salían publicados como «Ley del IVA» y en el informe como
  criterio propio, que es lo que son: lo que pide la norma es el desglose, con
  sus `BR-*`;
- `PERFIL-SIN-EN16931`, `SIN-SOPORTE` y `VALIDADOR-SE-ATRAGANTA` caían en el
  informe en un cajón por defecto que se leía «Formato»;
- `ANCLAS-SIN-RENOVAR` era firma en la página y «Formato» en el informe.

Ahora la tabla vive en `validador/normas.py`, un módulo sin dependencias que
pueden leer los dos, y el cajón por defecto dice «De la casa». Una prueba
compara los dos caminos código a código sobre el catálogo entero: no impide que
alguien se equivoque, impide que vuelva a haber dos tablas.

### Lo que se probó, y cómo

Los siete reproducidos antes de tocar nada. Después, **22 roturas provocadas**
con un guion que mete cada fallo, corre las pruebas que lo tienen que cazar y lo
deshace: 7 del punto 9, 1 del 10, 1 del 15, 3 del 16, 3 del 17, 3 del 18 y 4 del
19. Las 22 en rojo.

Dos salieron en verde la primera vez, y las dos por el mismo motivo —la prueba
se apoyaba en otra cosa—:

- la del EDIFACT alemán seguía pasando sin leer el país, porque el número de
  IVA de esa factura empieza por `DE` y la pista de reserva la salvaba. Se
  rehízo con una factura alemana cuyo número de IVA viene **sin** prefijo, que
  es un caso real y el único que prueba lo que dice probar;
- la del cajón por defecto comparaba contra la propia constante que se estaba
  rompiendo: al cambiar «De la casa» por «Formato» cambiaban las dos a la vez.
  Ahora compara contra la palabra escrita.

Y un fallo propio, cazado por una prueba que ya estaba: la lectura nueva del
país reventaba con un EDIFACT que no se puede convertir —`raiz` a `None`—, y lo
paró `TestNadaRevienta`, que precisamente existe para eso.

La suite entera, 2209 pruebas, en verde.


## Siete de la parte media: lo que viajaba sin mirarse y lo que seguía por detrás

Los puntos 11 a 14 y 21 a 23 de la auditoría del 15-09-2026. Ninguno da un
aprobado falso a una factura. Tres son de la misma familia —**algo que llega al
navegador de un desconocido sin que nadie lo contraste**— y dos son el fallo de
esta casa otra vez: lo que hay en pantalla no es lo que está pasando.

### 11. La cadena de suministro, sin fijar

Tres agujeros con la misma forma.

**El intérprete.** `--traer-pyodide` escribía un `HUELLAS.txt` al lado de lo
bajado, y parecía que eso era fijarlo. No lo era: se calcula de lo que llega,
vive dentro de `vendor/`, que no se versiona, y por lo tanto no viaja. Un
recibo —«esto llegó»— haciéndose pasar por un contrato —«esto tenía que
llegar»—. La diferencia está en lo que permite: el día que el CDN sirviera otra
cosa, la construcción de Vercel la bajaría, la apuntaría como buena y la
publicaría. Y peor, porque no hace falta que nadie ataque nada: reutilizaba lo
que ya estuviera en la carpeta **sin mirarlo**, así que una descarga cortada de
ayer se apuntaba hoy como buena.

Reproducido cortando `pyodide.js` a 5.000 bytes: `--traer-pyodide` lo daba por
bueno y `--sitio` lo publicaba. Ahora las seis huellas están escritas en
`validador/paquete.py`, y lo que no cuadra no se baja, no se monta y no se
publica. Contrastadas contra el CDN dos veces con tres semanas en medio
—30-08-2026 y 20-09-2026—, byte a byte iguales las seis. Hay dos capas, porque
son dos preguntas distintas: al traerlo se compara con la tabla fijada, y al
montar con `HUELLAS.txt`, que caza lo que se estropee **después** de traerlo.

**Lo que se instala al construir.** `vercel.json` instalaba `lxml` sin versión,
y setuptools ni eso. Fijados: lxml 6.1.2, la misma que corre la suite —hay
prueba que compara los dos sitios—, y setuptools 84.0.0 en
`[build-system] requires`, que es donde de verdad se lee: `pip wheel` construye
en un entorno aislado y se trae el que diga ahí, no el que haya al lado.

**Lo que la página se baja.** `rueda.json` lleva la huella de cada fichero
desde que existe, y solo servía de `?v=` para que el navegador no sirviera una
copia vieja: **no las miraba nadie**. Medido: con un byte de más en la rueda, la
página arrancaba y ponía «Listo en 5 s». Ahora la rueda, los diez ejemplos y
`prueba.py` se comparan con lo publicado, y provocado sale así:

```
El validador (factura_e-0.1.0-py3-none-any.whl) no es lo que la pagina dice
traer: rueda.json publica e05dcb664e11... y lo que ha llegado resume
9419bf446c0a... . No se usa.
```

Las huellas del manifiesto pasan a ser enteras; en el `?v=` se siguen
escribiendo los ocho primeros, así que ninguna dirección cambia y la caché de
quien ya haya pasado sigue valiendo. Ocho caracteres bastan para saber que algo
cambió y no bastan para comparar.

Y una grieta que se queda, dicha porque está medida: la rueda se baja dos
veces. Lo ideal sería bajarla una y darle los bytes a `loadPackage`, pero solo
acepta una dirección y la pide él. `emfs:`, que sirve para instalar desde el
disco virtual, lo bloquea la propia política de contenido de la página
—`connect-src 'self'` no admite ese esquema— y **no falla**: `loadPackage`
escribe un aviso en la consola y devuelve tan contento. Lo cazó el `pyimport`
que ya estaba detrás, puesto por esta misma razón hace dos semanas.

### 12. El guardián de rutas, con dos puertas abiertas

`Sitio/index.html`, `ANCLAS/x.pem` y `proyecto 1/estrategia.py` pasaban los
tres. En Windows son las mismas carpetas que las prohibidas —medido: `ls
SITIO/` lista lo mismo que `ls sitio/`—, así que el gancho estaba mirando el
nombre y no el sitio. Y `NotebookEdit` pasaba **siempre**, porque el gancho lee
`file_path` y esa herramienta manda `notebook_path`.

Ahora compara sin mirar mayúsculas y mira todas las rutas que manda la
herramienta, cualquier campo que acabe en «path»: enumerar los nombres es lo que
ya falló una vez. Sus decisiones se prueban en `tests/test_guardian_de_rutas.py`
—18 casos, seis que tienen que parar y tres que no—, y se saltan donde el gancho
no está, que es todo sitio que no sea esta máquina.

### 13. Con barra final, la página sin CSS ni JS

`https://www.glosa-e.com/banco/` contestaba 200 con el HTML del banco, y
`/banco/glosa.css`, `/banco/glosa.js` y `/banco/prueba.py` contestaban 404: la
página cargaba desnuda y el banco se quedaba colgado. Es lo que pasa cuando
`cleanUrls` sirve `/banco/` y la página busca sus cosas con rutas relativas.
Una línea en `vercel.json`: `"trailingSlash": false`, que redirige `/banco/` a
`/banco` con un 308.

### 14. Una factura de 4.000 líneas, cuatro segundos en vez de veinte

`LEEME.md` publicaba «Validar una factura: 5–120 ms». Se había medido sobre las
facturas de ejemplo, que tienen una línea o dos, y se publicaba como si fuera lo
que cuesta validar una factura. La auditoría soltó una de 4.000 líneas y la
pestaña se quedó parada.

Dos causas, las dos aburridas y ninguna de algoritmo:

- **cada ruta XPath se compilaba en cada uso.** Una factura de 800 líneas hacía
  31.235 llamadas a `texto()` y 16.080 a `_nodos()`, compilando las mismas
  cuatro docenas de rutas una y otra vez. Medido aparte: 8.000 evaluaciones de
  la misma ruta cuestan 315 ms sueltas y 32 compilándola una vez;
- **el catálogo de esquemas y el almacén de anclas se rehacían en cada
  validación**, y no cambian nunca. Construirlos no cuesta nada —son
  perezosos—, pero el esquema compilado y los certificados leídos viven dentro,
  así que uno nuevo tira ese trabajo y lo vuelve a hacer.

Medido en el navegador, sobre el sitio montado en local, antes y después, con
la misma factura y el mismo Chrome:

| Líneas | Antes | Después |
|---|---|---|
| 1 | 416–463 ms | 17–23 ms (la primera, 460: arma el catálogo) |
| 100 | 1.009–1.206 ms | ~130 ms |
| 1.000 | 5,7 s | ~1,1 s |
| 4.000 | 20,5–23,8 s | 4,2–5,3 s |

Y fuera del navegador, que es donde se ve la causa limpia: 4.000 líneas pasan
de 4.137 ms a 1.705, y la factura de ejemplo de 70 ms a 1,9 rehaciendo o no el
catálogo.

La primera medición de esto salió mal y conviene apuntarlo: una tanda daba
4.396 ms donde la siguiente daba 729, y no había cambiado el código —estaba el
navegador cargando Pyodide al lado—. Es exactamente lo que `LEEME.md` ya avisa
desde el 06-09. Las cifras de arriba son con calentamiento y mediana de cinco.

Lo que sigue siendo verdad, y ahora está escrito donde se publica: 4.000 líneas
son cuatro segundos largos con la pestaña parada, porque esto valida en el hilo
de la página. Cuatro segundos no son veinte, pero tampoco son nada.

### 21. Una negativa que salía con traza de Python

Una página con un `onclick=` levantaba `SinPolitica`, y `--sitio` **no la
cazaba**: traza de Python, código 1, y 409 ficheros montados sin `rueda.json`.
Una carpeta a medias con cara de sitio, que es lo que el paso siguiente publica
sin enterarse —la misma lección que ya había dejado la bitácora, escrita en su
propia prueba—.

El fallo no es que faltara una excepción en un `except`: es que hubiera una
lista escrita a mano. Ahora todas cuelgan de `paquete.NoSeMonta`, `__main__`
caza la raíz, y una prueba recorre el módulo para que ninguna quede suelta. Y
lo que no depende de nada de lo que pasa por el medio —un `onclick=`, un enlace
`javascript:`, un `<script defer>` en línea— se mira **antes** de tocar el
destino, así que no queda nada montado. El charset se sigue mirando al
escribir, porque adelantarlo cambiaba el diagnóstico de una página sin
cabecera: se llevaba una queja sobre la política en vez de la que dice qué le
pasa.

Al arreglarlo apareció el mismo fallo en el otro sitio: `--traer-pyodide`
tampoco cazaba nada y la huella que no cuadra habría salido igual, con traza.

### 22. «No ha arrancado» mientras la descarga seguía

La auditoría lo vio una vez y dudaba de si lo había contaminado la propia
prueba. No: es reproducible y es peor de lo que parecía.

Provocado con un servidor que sirve el sitio y se atasca a propósito: manda
64 KB de `python_stdlib.zip`, se calla 45 s y después intenta escribir el resto,
que es la conexión que se murió en producción el 08-09-2026. El vigilante saltó
a los 30 s y la página pintó «No ha arrancado». Y entonces:

- a los 45 s el servidor escribió los 2,48 MB que faltaban y **el cliente
  seguía ahí**;
- detrás se bajaron lxml, la rueda, el paquete de esquemas y anclas y los diez
  ejemplos: unos 5 MB, con la página diciendo que no había arrancado;
- y el validador acababa **vivo**: `Glosa.validarEjemplo("f-0001.xml")`
  devolvía el informe entero con la zona de arrastre apagada.

`Promise.race` no para al que pierde. Ahora hay un `AbortController` cuya señal
va en cada petición, y al saltar el vigilante se abandona de verdad. Medido con
el mismo servidor: después de «No ha arrancado» no se pide nada más, y
`pyodide` se queda en `null`.

Lo que **no** hace, porque se midió y no se va a prometer: la petición que
estaba en vuelo no se corta del lado del servidor. Al escribir el resto, el
servidor no ve ningún error; Chrome se traga lo que quedaba para reutilizar la
conexión. Lo que se para es la cadena.

Y una segunda mitad del mismo fallo: el `fetch` bueno se devolvía al acabar la
carrera, no al acabar la faena, así que lo que siguiera bajando después ya no
pasaba por el vigilante y no lo contaba nadie.

### 23. El servidor de desarrollo, abierto a la red

`python -m http.server` sin `--bind` escucha en `0.0.0.0` y en `[::]`. Medido:
el servidor de `web` contestaba en la IP de la red local de esta máquina
sirviendo el repositorio entero —`.git/HEAD` devolvía `ref: refs/heads/main`, y
`muestras/` y `anclas/` daban 200—. Si otro equipo llega o no depende del
cortafuegos de Windows, y eso no se ha medido: hay una regla de entrada para un
`python.exe`, pero para el del sistema, no para el del entorno virtual que usa
`launch.json`.

No hacía falta seguir midiendo. Los dos servidores llevan `--bind 127.0.0.1`.

### Lo que se probó, y cómo

Los siete reproducidos antes de tocar nada, y cinco de los siete provocados
**en el navegador**, que es donde viven: la rueda con un byte de más, un ejemplo
cambiado, `prueba.py` cambiado, el intérprete cortado y la conexión que se
muere. La suite no ejecuta JavaScript y no se va a fingir que sí: lo que guarda
en verde es que el código siga escrito, y lo que se midió está en el
docstring de cada prueba, con sus cifras.

Y un fallo propio por el camino, que es el que mejor enseña por qué esto se
prueba dos veces. Probé si `loadPackage` admitía instalar desde el disco
virtual con `emfs:`, salió sin excepción y lo di por bueno; el sitio montado se
quedó sin validador. `loadPackage` no lanza: escribe un aviso en la consola y
devuelve. Lo cazó la línea que ya estaba puesta detrás por esa razón, y la
lección es la de siempre aquí: que no falle no es que funcione.

## Los dos ganchos, vistos desde un worktree

No sale de la auditoría sino de una pregunta previa: si se reparte trabajo
entre varios agentes, cada uno en su propia copia de git, ¿siguen valiendo las
puertas? La respuesta corta es que **una no valía y la otra valía por
accidente**, y las dos se ven en cuanto se prueba, porque `git worktree add`
deja una copia de Factura-e donde le digan.

Lo que sí aguantó, y conviene decirlo primero: los ganchos **llegan** a un
subagente. Un `Write` pedido por uno salió rechazado con el mismo mensaje que
si lo pide la sesión. Y el guardián de rutas decide por el **destino**, no por
dónde esté quien escribe, así que `Proyecto 1`, `anclas/`, `muestras/` y el
`sitio/` de la copia buena siguen protegidos desde cualquier worktree. Lo único
que deja pasar son las carpetas construidas del worktree de fuera, que no
viajan a ningún sitio. El problema estaba en los otros dos.

### El portero tomaba un worktree por otro proyecto

`de_factura_e()` decidía comparando rutas: si la carpeta cuelga de
`Factura-e/`, es nuestra; si cuelga de la carpeta de trabajo pero no de
`Factura-e/`, es otro proyecto y tiene sus reglas —`Proyecto 1` no es asunto
suyo—. Un worktree cae justo en el segundo caso. Medido el 21-09-2026 con uno
en `C:\Users\PC\Claude\copia-de-prueba`:

```
git push --no-verify <repositorio> HEAD:refs/heads/saltada
 * [new branch]      HEAD -> saltada
codigo 0
```

Con un fichero sin commit, sin correr la suite y sin que nadie dijera nada.
Contra `origin` eso es un despliegue a producción sin probar. El fallo de fondo
es el de siempre en esta casa: **reconocer una cadena de texto en vez de
reconocer la cosa**, el mismo del `file_path` del guardián que dejaba pasar
`notebook_path`.

Ahora se le pregunta a git. `rev-parse --path-format=absolute --git-common-dir`
resuelve al `.git` de la copia principal desde cualquier worktree suyo, porque
es el que comparten; si no contesta, no es de aquí. Comprobado que `Proyecto 1`
sigue sin ser asunto del portero.

### El gancho de git estaba cerrado por accidente

`.githooks/pre-push` acababa en una línea con dos rutas relativas:

```
exec ./.venv/Scripts/python.exe .githooks/antes-de-empujar.py "$@"
```

`.venv` no se versiona, así que un worktree no tiene el suyo:

```
.githooks/pre-push: line 17: .../copia-de-prueba/.venv/Scripts/python.exe: No such file or directory
```

Git cancela con cualquier código distinto de 0, así que el push no salía. Pero
no salía **ninguno**, tampoco el bueno: nunca corrió la suite, nunca miró si
había cambios sin commit, y lo que se leía era un error de shell en vez del
motivo. Un cierre que depende de que un fichero falte se abre el día que
alguien monte un `.venv` ahí para trabajar más cómodo.

Ahora `pre-push` le pregunta a git cuál es la copia principal y coge el
intérprete de allí, y si no lo encuentra se niega con palabras. La suite se
sigue corriendo sobre la copia desde la que se empuja, que es la que se
publica: lo probado tiene que ser lo publicado. Y el guion que la corre usa
`sys.executable` —el intérprete que `pre-push` ya eligió— en vez de volver a
buscarlo al lado.

Provocado donde estaba el fallo: desde el worktree, el push que antes daba un
error de shell ahora dice qué falta, y el `--no-verify` que publicaba sale
bloqueado.

### Y una prueba que salió verde por coincidencia

La primera versión de la prueba del intérprete comparaba `PYTHON` con
`sys.executable`. En la copia principal esos dos son **el mismo fichero**, así
que salía verde con el arreglo puesto y con el arreglo quitado. Se vio al
provocarla, que es exactamente para lo que se provoca. Ahora carga el guion con
un segundo intérprete y mira a cuál de los dos sigue.

## Los dieciséis de la parte baja, barridos en abanico

Los puntos 24 a 39 de la auditoría del 15-09-2026, los que se habían dejado
para el final por ser de gravedad baja. **Dos no lo eran**: los dos dicen «sin
errores» de algo que no se ha mirado, que es el peor fallo que puede tener un
validador porque no falla —dice que sí—. Los dos están cerrados aquí. Los
catorce restantes están medidos y escritos más abajo.

### Cómo se barrieron, y por qué eso importa

Seis lectores en paralelo, uno por familia de puntos, sin permiso de escritura
—ni `Write`, ni `Edit`, ni push— y con el navegador reservado a uno solo para
que no se pisaran. Cada uno devolvía la misma ficha por punto: si se reproduce,
con qué orden exacta, qué sale, dónde está, si alguna prueba lo caza hoy, si
puede dar un aprobado falso y qué costaría cerrarlo.

La verificación **no la hizo otro modelo**: como cada ficha traía la orden
copiable, se volvieron a correr aquí. Doce de los dieciséis se comprobaron así,
de primera mano; los otros cuatro —31, 33, 34 y 36— se dan por buenos con la
evidencia que trajeron, y eso queda dicho porque no es lo mismo.

Mereció la pena por lo que corrigió. Un lector afirmó que `huella()` ya se
protegía de la colisión del punto 26 y que bastaba con imitarla; al repetirlo
aquí, las dos facturas **también** comparten huella. `huella()` pone la
longitud por delante de tres partes —NIF, `numero_completo` y fecha— pero
`numero_completo` ya ha juntado serie y número antes: la defensa está un nivel
por encima de donde ocurre el choque, y el comentario que la justifica describe
literalmente el caso que no para. Otros dos detalles de la auditoría estaban
mal situados: las fichas de códigos no viven en `/reglas/<código>` sino en
`/codigo-<CÓDIGO>`, y el `escapar()` del punto 39 no está en `glosa.js` —ahí no
hay ninguno— sino duplicado en `index.html` y `banco.html`.

Y algo que no era un punto de la auditoría: **la lista de los dieciséis no
estaba en ninguna parte del repositorio**. Hubo que sacarla del registro de una
sesión anterior. Por eso está aquí abajo entera.

### 29. Una carpeta se miraba por encima, y salía con 0

`expandir()` recorría la carpeta con `iterdir()`, que solo da el primer nivel.
Una carpeta de facturas viene organizada por mes o por cliente casi siempre.

Reproducido con una carpeta con una factura correcta arriba y un EDIFACT con
errores dentro de una subcarpeta:

```
el fichero escondido, validado suelto -> código 1 (1 error)
la carpeta entera                     -> código 0 · 1 correcto(s) · 0 con errores
¿se nombra el de la subcarpeta?          no
```

Ni se nombraba, ni se contaba, ni se avisaba. Para quien encadena guiones, ese
0 dice «todo revisado y todo bien». Ahora se recorre entera con `rglob`, y la
misma carpeta sale «2 fichero(s) · 1 correcto(s) · 1 con errores», código 1,
nombrando el de dentro. Filtrando por `is_file()`, porque `rglob("*")` devuelve
también los directorios y uno llamado `cosas.xml` habría colado como factura
—hay prueba de eso, que es la clase de cosa que se arregla y se rompe en el
mismo movimiento—.

### 32. El navegador podía pintar el informe de otra factura

`_rutas` y `_nombres` son globales de Pyodide. La llamada las escribía y
`INFORME` las leía cuando el Python llegaba a ejecutarse; entre esas dos cosas
hay un `await`, y ahí cabía otra llamada entera, que las pisaba.

Medido en producción, dos facturas propias soltadas en el mismo tick, una con
errores y otra sin ellos:

| Cuándo | Informes de la mala que salían conformes |
|---|---|
| antes, en el mismo tick | **20 de 20**, hablando de la buena |
| antes, con 1 ms de separación | 0 de 8 |
| después, en el mismo tick | **0 de 20** |

El informe de la factura con errores volvía diciendo «1 fichero(s) · 1
correcto(s) · 0 con errores» y `conforme: true`. No era una carrera rara: era
lo que pasaba **siempre** que dos validaciones arrancaban juntas.

Ahora hay una fila: una validación cada vez. Encolar no hace esperar más de lo
que ya se esperaba —Pyodide corre Python en el hilo principal, así que dos
validaciones nunca fueron simultáneas de verdad; lo único que hacían a la vez
era corromperse—. La cola se traga el error de la que falla, porque si no, una
factura ilegible dejaba la página sin poder validar nada más; provocado con una
que revienta dentro de la fila, y la siguiente sigue funcionando.

Lo que guarda esto no es un comentario sino una prueba que recorre `glosa.js` y
exige que **nadie** escriba `_rutas` ni corra `INFORME` fuera de las dos
funciones que solo se alcanzan por la fila, y que las públicas sigan siendo las
que se exportan. Una entrada nueva que se olvide de encolar devuelve el fallo
entero.

### Los catorce que quedan, medidos

Todos se reproducen. Ninguno da un aprobado falso. **Cuatro de ellos —24, 25a,
25b y 28— se cerraron el mismo día**; la lista al día está al final de la
entrada siguiente.

| # | Qué pasa | Medido |
|---|---|---|
| 24 | Un DOCTYPE con una entidad usada en un importe atraganta al validador | `Internal error in XML Schema validation`, en inglés, dentro del informe |
| 25a | La expresión regular del número de factura es cuadrática | ×4,00 y ×4,31 al doblar el tamaño; 2.425 ms con 20.000 caracteres. Un número realista: 0,059 ms |
| 25b | `int()` revienta con números larguísimos | 4.300 dígitos: solo `CU-03`. 4.301: `ValueError`. `validar_archivo` lo atrapa; `validar()` no |
| 26 | Series que se tocan comparten código único | `A`+`12` y `A1`+`2` dan `B12345674\|A12\|…` las dos: `CU-10` a dos facturas distintas. Y también la misma `huella()` |
| 27 | Un céntimo de descuadre da dos quejas | `BR-CO-12` y `IVA-BASE-TOLERADA` a la vez. `en16931` compara sin margen desde el 13-09-2026 y la guardia de `iva.py` se quedó con el de 0,01 |
| 28 | Un `X509Certificate` que no es base64 calla el resto | De **23 incidencias a 1**. El `b64decode` quedó fuera del `try` que protege la línea de debajo |
| 30 | Un `UNA` con separadores propios | «Mensaje EDIFACT, pero sin cabecera UNH», que es falso: el partidor sí la encuentra |
| 31 | Un ejemplo que da 404 se escribe como si fuera la factura | En producción lo para la huella de `rueda.json`, de rebote; sin ella, pasa |
| 33 | `/entrada` no se vacía nunca | 6 validaciones → 6 ficheros, 480.438 B, todos vivos |
| 34 | Mensajes de libxml2 en inglés dentro del informe | `Premature end of data in tag FileHeader`, `xmlParseEntityRef: no name`… |
| 35 | Las gravedades no casan con lo que promete la página | `BR-01/14/21` y `SELLO-FALTA` salen NOTA contra la definición de la propia FAQ; y la portada promete «revocación» sin decir bajo qué condición |
| 36 | El testigo de red cuenta lo servido de caché | Pinta 10,4 MB cuando por el cable fueron 17.769 bytes: usa `encodedBodySize` en vez de `transferSize` |
| 37 | `legal.html` dice «no se guarda nada» | Y `index.html`, en el mismo sitio, dice «unos 10 MB… se queda en el navegador». Seis ficheros con `immutable` a un año suman ≈15,1 MB |
| 38 | El 404 y las minúsculas | `/codigo-BR-01` → 200, `/codigo-br-01` → 404. El 404 es el genérico de Vercel, en inglés y sin marca |
| 39 | Cinco menores | HSTS sin `includeSubDomains` —el `.vercel.app` sí lo lleva—, faltan `Permissions-Policy`, COOP y CORP, `prueba.py` como `octet-stream`, `escapar()` sin comillas —hoy sin impacto: solo recibe `error`, `aviso` o `nota`— y el subdominio de Vercel no redirige |

## Los cuatro que se atragantaban

La tanda A de los puntos que quedaban de la auditoría del 15-09-2026: 24, 25a,
25b y 28. Los cuatro tienen el mismo final —`VALIDADOR-SE-ATRAGANTA`— y el
mismo motivo de fondo: **la red de seguridad funciona, y lo que cae en ella se
pierde**. Esa red convierte un fichero que revienta el validador en un error
del fichero, para que un lote de quinientas facturas no se detenga en la
séptima; pero el informe de esa séptima queda reducido a una sola línea, con el
nombre de una excepción de Python y el mensaje de la librería en inglés.

Medido hoy, en los cuatro casos: de 23 incidencias a 1, o de 4 a 1. Lo que se
callaba no eran quejas sobre la firma ni sobre el XML: eran todas las demás.

### 24. Un DOCTYPE con una entidad usada en un importe

`<!ENTITY monto "1.00">` en el prólogo y `&monto;` dentro de un `TotalAmount`.
El parser de este proyecto lleva `resolve_entities=False` desde el principio
—un fichero de un tercero no debe poder leer ficheros del servidor, y hay
prueba de ello desde antes—, así que la referencia se queda sin expandir. Y
libxml2 se niega a validar contra un XSD un árbol que las trae:

```
VALIDADOR-SE-ATRAGANTA  error
  Este fichero ha hecho fallar al validador: XMLSchemaValidateError:
  Internal error in XML Schema validation
```

Una línea, en inglés, y ninguna otra comprobación. Ahora salen cuatro, en
castellano, encabezadas por `XML-ENTIDADES`, que es código nuevo y familia
nueva.

**Y lo que de verdad importaba no era la caída.** Medido con lxml: en ese
documento, `TotalAmount.text` vale `None`. El importe no está mal escrito: no
está. Si la caída se arreglara a secas, la factura pasaría a validarse con un
total vacío y sin que nadie lo dijera —un falso aprobado de los caros—. Por eso
`XML-ENTIDADES` es error y no aviso, y por eso no se arregla expandiendo las
entidades: la norma XML permite a un procesador no validante no expandirlas, o
sea que el mismo fichero se lee con dos importes distintos según quién lo abra.
Una factura que dice dos cosas no dice ninguna.

La familia se llama `XML` y no `XSD` a propósito. El esquema no prohíbe esto;
lo decide este validador, y la etiqueta de la ficha tiene que decir «De la
casa» y no «Esquema XSD».

### 25a. La expresión regular del número de factura era cuadrática

Partir `F-2026-001` en el prefijo `F-2026-` y el ordinal `001` es lo que
permite ver los huecos de una serie, y se hacía con
`^(?P<prefijo>.*?)(?P<digitos>\d+)$`. Con un número que **no** acaba en dígito,
el motor prueba todos los cortes posibles y ninguno vale:

| Caracteres | La expresión regular | Recorrerlo del final hacia delante |
|---|---|---|
| 5.000 | 237 ms | 0,0004 ms |
| 10.000 | 923 ms | 0,0003 ms |
| 20.000 | **8.291 ms** | 0,0009 ms |

El mismo número de 20.000 caracteres acabado en dígitos: 0,2 ms. No es un fallo
del motor, es lo que hace un `.*?` perezoso delante de algo que nunca encaja.

### 25b. `int()` se niega con más de 4.300 dígitos

Con el ordinal en la mano se hace `int()`, y desde Python 3.11 hay un tope de
4.300 dígitos —la defensa contra un `int()` cuadrático—. Medido sobre
`ejemplos/f-0001.xml` con el `<cbc:ID>` sustituido:

```
4.300 unos -> CU-03, y nada más
4.301 unos -> ValueError, en codigo_unico.py:427
```

Los dos arreglos son el mismo: `partir_ordinal()` recorre el número del final
hacia delante y **no toca** los que son más largos de lo que cabe en el campo.
De un número de sesenta y un caracteres ya se ha quejado CU-03, y de un número
que no es válido no hay correlatividad que reconstruir. Con eso, el `int()` no
puede ver nunca más de sesenta dígitos: que el tope sea el mismo que el de
CU-03 no es casualidad, es el motivo.

Hay prueba de las dos mitades por separado, y la del recorrido levanta el tope
a propósito: el tope es la defensa de hoy, que sea lineal es la de mañana.

### 28. Un `X509Certificate` que no es base64 callaba el resto

`certificados_de` hacía el `base64.b64decode` **fuera** del `try` que protege
la línea de debajo. Dos letras bastan:

```
23 incidencias  ->  1
                    Incorrect padding
```

Las 22 que se perdían no eran sobre la firma. Movido el `b64decode` dentro del
`try`, la misma factura vuelve a salir con 23, y dos de ellas son nuevas:
`FIRMA-SIN-COMPROBAR` —«no se ha podido leer el certificado, así que no se ha
comprobado la firma»— y `XSD-TIPO`, porque el esquema también tiene algo que
decir de un `X509Certificate` que no es base64. Saltarse el certificado
ilegible no es darlo por bueno: es dejar que lo diga quien sabe decirlo.

### Y una que salió al paso: la descripción de las fichas

Añadir `XML-ENTIDADES` puso en rojo una prueba que no era de ninguno de los
cuatro puntos: la ficha `/codigo-XML-ENTIDADES` tenía una descripción de 168
caracteres donde caben 165. El corte medía el texto y lo que acaba en el
atributo `content` es el texto **escapado**, donde un `<` ocupa cuatro. Una
explicación que nombre una etiqueta XML en su primera frase se pasaba.

Le pasaba a **una** de 382, y por eso no se había visto nunca. Ahora el
presupuesto se cuenta ya escapado; las otras 381 descripciones no cambian ni un
carácter —comprobado una a una—. La destapó la prueba, no la página.

### Nueve roturas provocadas, las nueve en rojo

Y una de ellas enseñó algo. «El esquema vuelve a ver el árbol con entidades»
salió **verde** a la primera: la suite corre sin esquemas instalados a
propósito —lo dice `conftest.py`, y con razón—, así que la validación de forma
ni llegaba a ejecutarse y la regresión pasaba sin que nada se enterara. La
prueba se reescribió con un catálogo propio, de los de juguete, y con una
hermana que comprueba que el atajo no se ha llevado por delante la validación
entera.

### Los once que quedan

**Tres de ellos —26, 27 y 30— se cerraron al día siguiente**; la lista al día
está al final de la entrada que viene después.

| # | Qué pasa | Medido |
|---|---|---|
| 26 | Series que se tocan comparten código único | `A`+`12` y `A1`+`2` dan `B12345674\|A12\|…` las dos: `CU-10` a dos facturas distintas. Y también la misma `huella()` |
| 27 | Un céntimo de descuadre da dos quejas | `BR-CO-12` y `IVA-BASE-TOLERADA` a la vez. `en16931` compara sin margen desde el 13-09-2026 y la guardia de `iva.py` se quedó con el de 0,01 |
| 30 | Un `UNA` con separadores propios | «Mensaje EDIFACT, pero sin cabecera UNH», que es falso: el partidor sí la encuentra |
| 31 | Un ejemplo que da 404 se escribe como si fuera la factura | En producción lo para la huella de `rueda.json`, de rebote; sin ella, pasa |
| 33 | `/entrada` no se vacía nunca | 6 validaciones → 6 ficheros, 480.438 B, todos vivos |
| 34 | Mensajes de libxml2 en inglés dentro del informe | `Premature end of data in tag FileHeader`, `xmlParseEntityRef: no name`… |
| 35 | Las gravedades no casan con lo que promete la página | `BR-01/14/21` y `SELLO-FALTA` salen NOTA contra la definición de la propia FAQ; y la portada promete «revocación» sin decir bajo qué condición |
| 36 | El testigo de red cuenta lo servido de caché | Pinta 10,4 MB cuando por el cable fueron 17.769 bytes: usa `encodedBodySize` en vez de `transferSize` |
| 37 | `legal.html` dice «no se guarda nada» | Y `index.html`, en el mismo sitio, dice «unos 10 MB… se queda en el navegador». Seis ficheros con `immutable` a un año suman ≈15,1 MB |
| 38 | El 404 y las minúsculas | `/codigo-BR-01` → 200, `/codigo-br-01` → 404. El 404 es el genérico de Vercel, en inglés y sin marca |
| 39 | Cinco menores | HSTS sin `includeSubDomains` —el `.vercel.app` sí lo lleva—, faltan `Permissions-Policy`, COOP y CORP, `prueba.py` como `octet-stream`, `escapar()` sin comillas —hoy sin impacto: solo recibe `error`, `aviso` o `nota`— y el subdominio de Vercel no redirige |

El 34 es hermano del 24 y se queda para su tanda: son los mensajes de libxml2
que sí llegan al informe cuando el documento está mal formado, y ahí no hay una
caída que evitar sino una traducción que escribir.

## Los tres en los que el programa se contradecía

La tanda B de la auditoría del 15-09-2026: los puntos 26, 27 y 30. Ninguno de
los tres es un fallo leyendo una factura. Los tres son **dos partes de este
programa que habían dejado de decir lo mismo**, y en los tres casos la que
hablaba de cara al informe era la equivocada:

| Quién dice una cosa | Quién dice la contraria |
|---|---|
| el docstring de `huella()`: «dos facturas distintas no comparten huella» | `huella()`, que las hacía compartirla |
| `iva.py`, que se calla «porque ya lo dice BR-CO-12» | `en16931.py`, que con un céntimo sí lo dice, y entonces salen los dos |
| `formato.py`: «Mensaje EDIFACT, pero sin cabecera UNH» | `edifact.py`, que encuentra esa cabecera dos líneas después |

### 26. Dos facturas distintas con el mismo código único

El código único pega la serie y el número sin nada en medio —así los trata
Verifactu, y si la serie necesita un guion ya lo lleva dentro—. La consecuencia
es aritmética: la serie `A` con el número `12` y la serie `A1` con el número
`2` dan las dos `A12`.

```
serie 'A'  + número '12' -> B12345674|A12|2026-09-07
serie 'A1' + número '2'  -> B12345674|A12|2026-09-07
```

Son dos cosas distintas y hay que separarlas.

**La huella prometía no colisionar, y colisionaba.** Su docstring lo dice con
todas las letras: las partes se cifran con su longitud por delante para que
`("AB", "C")` y `("A", "BC")` no den lo mismo. Pero la longitud se le ponía a
`numero_completo`, que ya ha pegado serie y número: **la defensa estaba un
nivel por encima de donde ocurre el choque**. Y había prueba —
`test_la_huella_no_colisiona_al_partir_distinto`—, en verde, porque probaba el
otro borde, el de NIF contra número. Un guardián mirando la puerta de al lado.
Ahora las cuatro partes van por separado y hay prueba del borde que faltaba.

**Y el código canónico sí choca, porque así se forma.** Eso no se arregla: es
la definición. Lo que se arregla es lo que se decía de ello. Salía `CU-10`,
«esta factura ya estaba registrada… es la misma factura dos veces», que es
**falso** y además manda a buscar una copia que no existe. Ahora sale `CU-16`,
que dice lo que de verdad pasa —son dos facturas, y para cualquier registro que
las indexe por su código son una: la segunda tapa a la primera— y enseña las
dos particiones al lado, porque sin verlas la queja no se entiende.

Un duplicado de verdad sigue siendo `CU-10`; hay prueba de que el arreglo no se
lo traga, que es la mitad que se rompe sola al arreglar la otra.

**Y sólo puede pasar en Facturae**, que conviene decirlo porque acota el
hallazgo. De las tres sintaxis es la única que guarda la serie en un campo
suyo; UBL y CII llevan el número entero en uno solo —`cbc:ID`, `ram:ID`—, así
que de ahí sale siempre `serie=None` y mismo código canónico implica mismo
número: dos UBL con el mismo número son un duplicado de verdad y siguen
saliendo `CU-10`. Comprobado en el navegador con las dos parejas, y hay prueba
de las dos. El caso más feo es el mixto —una Facturae con serie `A` y número
`12` contra un UBL cuyo `cbc:ID` es `A12`—, porque ahí cada fichero cree tener
su propio número y ninguno de los dos está mal escrito.

### 27. Un céntimo, dos quejas

`iva.py` tiene un guardián con un propósito explícito en su docstring: cuando
los ajustes declarados no cuadran con los detallados, no comprobar la base por
tipo, **porque de eso ya se quejan BR-CO-11 y BR-CO-12 señalando el campo que
está mal**, y hacerlo sacaría una segunda queja apuntando al desglose, que es
donde no está el problema.

El 13-09-2026, al medir contra el esquematrón oficial, BR-CO-11 y BR-CO-12
pasaron a comparar **sin margen**. El guardián se quedó con el de un céntimo de
antes. El hueco entre los dos márgenes valía exactamente un céntimo, y ahí el
guardián decía que todo cuadraba mientras la regla se quejaba:

```
cargo detallado 10,00 · total declarado 10,01

BR-CO-12           error   Total de cargos de documento
                           esperado 10.00 · encontrado 10.01
IVA-BASE-TOLERADA  aviso   Base imponible de S (tipo general) al 21%
                           esperado 110.00 · encontrado 110.01
```

Dos quejas por el mismo céntimo, y la segunda manda a mirar el desglose, que es
justo lo que el guardián existe para evitar. Ahora compara igual que la regla a
la que cede el paso: una queja, en el campo que está mal.

### 30. Un UNA con separadores propios

El UNA es el segmento que existe **para** declarar separadores distintos de los
de siempre. La detección los llevaba escritos a pelo —`+` entre elementos, `:`
entre componentes, `'` al final del segmento— así que con un UNA propio no
casaba nada y contestaba:

```
Mensaje EDIFACT, pero sin cabecera UNH: no se ve de qué tipo es.
```

Es falso. `edifact.py` la encuentra sin despeinarse, porque él sí lee el UNA. Y
no era un caso de laboratorio: **la factura de W.S. Hein del corpus declara
`UNA^<.? >`**, y es el único de los 64 ficheros ajenos con separadores propios
—por eso esto aguantó tanto sin verse—. Medido sobre ella:

| | familia | versión | tipo de documento |
|---|---|---|---|
| antes | EDIFACT | — | — |
| ahora | EDIFACT | 96A | factura |

**Lo que no cambia es el veredicto**, y conviene decirlo: las 22 incidencias de
esa factura son las mismas antes y después. Lo que cambiaba era la frase que
describe el documento, y esa frase era mentira. También se arreglan de paso dos
cosas que colgaban de lo mismo: el BGM se buscaba igual de mal —de ahí el tipo
en blanco— y un mensaje que no fuera un INVOIC salía como «sin cabecera UNH» en
vez de «de tipo ORDERS, que no es una factura».

Ahora quien sabe leer un UNA sigue siendo `edifact.py`, y la detección se lo
pregunta a él en vez de escribirlo otra vez. Las dos expresiones se montan con
los separadores del fichero y se cachean por juego de caracteres. Hay prueba de
que la misma factura escrita de las dos maneras se describe igual, palabra por
palabra.

### Ocho roturas provocadas, las ocho en rojo

Las ocho a la primera, que es lo que cabía esperar de tres arreglos pequeños
con prueba escrita antes. Dos merecen mención porque no prueban el arreglo sino
que no se ha llevado nada por delante: «ahora un duplicado de verdad sale como
CU-16» tumba once pruebas, y «solo se arregla el UNH y el BGM se queda atrás»
tumba cuatro. Son las dos mitades que se rompen sola al arreglar la otra.

### Los ocho que quedan

*Superada: la tabla vigente está al final de la sección siguiente.*

| # | Qué pasa | Medido |
|---|---|---|
| 31 | Un ejemplo que da 404 se escribe como si fuera la factura | En producción lo para la huella de `rueda.json`, de rebote; sin ella, pasa |
| 33 | `/entrada` no se vacía nunca | 6 validaciones → 6 ficheros, 480.438 B, todos vivos |
| 34 | Mensajes de libxml2 en inglés dentro del informe | `Premature end of data in tag FileHeader`, `xmlParseEntityRef: no name`… |
| 35 | Las gravedades no casan con lo que promete la página | `BR-01/14/21` y `SELLO-FALTA` salen NOTA contra la definición de la propia FAQ; y la portada promete «revocación» sin decir bajo qué condición |
| 36 | El testigo de red cuenta lo servido de caché | Pinta 10,4 MB cuando por el cable fueron 17.769 bytes: usa `encodedBodySize` en vez de `transferSize` |
| 37 | `legal.html` dice «no se guarda nada» | Y `index.html`, en el mismo sitio, dice «unos 10 MB… se queda en el navegador». Seis ficheros con `immutable` a un año suman ≈15,1 MB |
| 38 | El 404 y las minúsculas | `/codigo-BR-01` → 200, `/codigo-br-01` → 404. El 404 es el genérico de Vercel, en inglés y sin marca |
| 39 | Cinco menores | HSTS sin `includeSubDomains` —el `.vercel.app` sí lo lleva—, faltan `Permissions-Policy`, COOP y CORP, `prueba.py` como `octet-stream`, `escapar()` sin comillas —hoy sin impacto: solo recibe `error`, `aviso` o `nota`— y el subdominio de Vercel no redirige |

## Los dos en los que la página iba por su cuenta

La tanda C de la auditoría del 15-09-2026: los puntos 35 y 37. Ninguno de los
dos es un fallo del validador. En los dos, **el programa hacía lo correcto y la
página lo contaba mal**, que es peor de lo que suena: lo que se publica es lo
único que ve quien todavía no se fía.

Los tres textos los decidió el usuario, porque la decisión no era técnica.

### 35. Una definición que dejaba fuera la mitad de sus propias notas

La FAQ de la portada repartía las tres gravedades así:

```
Error: algo incumple una norma y hay que arreglarlo.
Aviso: algo no se ha podido comprobar, o se ha comprobado y depende de un
       dato del que no hay que fiarse del todo.
Nota:  no es una queja — dice qué se ha dado por bueno y con qué base.
```

Y el informe, sobre una Facturae cualquiera, contesta esto:

```
BR-01  nota   Falta el código de referencia del pedido. La sintaxis Facturae
              no tiene ningún elemento con ese significado, así que no se ha
              podido comprobar. No es un defecto del documento.
```

La frase que la FAQ da como **definición de aviso** —«no se ha podido
comprobar»— sale escrita dentro de una **nota**. No es un caso de laboratorio:
son `BR-01`, `BR-02`, `BR-03`, `BR-14` y `BR-21` en `en16931.py`, y
`SELLO-FALTA` en `sellos.py`. De los 390 códigos, 53 pueden salir como nota y
32 no salen de ninguna otra forma.

**La que estaba mal era la FAQ.** El código lleva su motivo escrito desde que
se escribió —«NOTA es la gravedad que existe para decir qué se aceptó y con qué
base, y esto es exactamente eso; no hay nada que arreglar en el documento»— y
lo que faltaba era el criterio que separa los dos casos, que la definición no
daba. Están los dos en el propio catálogo, uno al lado del otro:

| Código | Gravedad | Por qué |
|---|---|---|
| `REVOCACION-SIN-COMPROBAR` | **aviso** | falta la lista con la que se miraría; con otra lista podría salir otra cosa |
| `BR-01` en Facturae | **nota** | el formato no tiene dónde guardar ese dato; no hay nada pendiente |

Las dos dicen «no se ha podido comprobar» y no son lo mismo: lo que cambia no
es si se miró, sino **si al lector le queda algo por hacer**. Eso es lo que
ahora dice la FAQ, con `BR-01` de ejemplo.

Un ejemplo metido en un texto es un hecho del código que se puede mover, así
que hay guardián: si `BR-01` deja de tener rama de nota, o si la FAQ deja de
nombrarlo, la suite se para.

**Y la revocación, prometida arriba y matizada abajo.** El mismo punto traía
otra cosa, que es de orden de lectura y no de exactitud. Nada era falso:

| Dónde | Qué decía |
|---|---|
| la ficha, en lo primero que se ve | «Cadena, revocación y sello» |
| la tabla comparativa | «Hasta la lista de confianza del Estado, con revocación y sello de tiempo» |
| una FAQ, 300 líneas más abajo | «si el documento no la trae y no la tienes instalada, no hay forma de saberlo sin salir a preguntar. Aquí no se pregunta» |

De las tres cosas que se miran de una firma, la revocación es la única que
puede quedarse sin contestar, y era la única cuya condición había que ir a
buscar. Ahora la ficha dice «Cadena, sello y revocación **si hay lista**» y la
tabla dice de qué depende, en la misma celda donde lo promete. También hay
guardián, porque una celda de cuatro palabras es justo lo que alguien acorta
para que quepa mejor.

### 37. «No se guarda nada» contra «se queda en el navegador»

Dos frases del mismo sitio, contradiciéndose palabra por palabra:

```
legal.html   …no hay identificadores, y no se guarda nada en tu navegador
             entre visitas.
index.html   Son unos 10 MB la primera vez. Después se queda en el navegador
             y no vuelve a bajarse.
```

Las dos eran ciertas y hablaban de cosas distintas —**datos tuyos** contra
**ficheros públicos en la caché**—, pero eso no estaba escrito en ninguna de
las dos, así que quien leía las dos tenía que elegir cuál se creía. Ahora el
aviso legal dice «no se guarda ningún dato tuyo» y lleva al lado un párrafo que
explica qué sí se queda, cuánto ocupa y cuánto dura; y la portada dice
«marcado para un año» en vez de dejarlo en «se queda».

**Y la cifra estaba bien, aunque la auditoría dijera que no.** El punto 35 del
barrido apuntó «seis ficheros con `immutable` a un año suman ≈15,1 MB» contra
los «unos 10 MB» de la portada. Vuelto a medir el 22-09-2026, las dos cosas son
verdad y no se estaban comparando con la misma vara:

| Qué se mide | Bytes | |
|---|---|---|
| lo que ocupa en disco, sin comprimir | 17.133.045 | 17,13 MB |
| **lo que baja por el cable**, con Brotli, contra `www.glosa-e.com` | **9.966.246** | **9,97 MB** |

Son 24 peticiones, la página incluida. El `.wasm` pesa 9.598.218 en disco y
3.577.499 por el cable; `pyodide.asm.mjs`, 1.250.344 y 265.085. Lo que no baja
nada es lo que ya viene comprimido: `paquete.zip`, `python_stdlib.zip` y la
letra viajan igual que están. «Unos 10 MB» es exacto y no se toca.

Lo que merece quedar escrito es **cómo se equivocó la auditoría**, porque el
fallo ya estaba catalogado en este repositorio: el 15-09-2026 la portada decía
«unos 15 MB» y se corrigió a 9,86 por el cable, con su fila en la tabla de «lo
publicado, repasado contra lo hecho». El barrido volvió a medir contra el
servidor local —que no comprime— y sacó otra vez la cifra de disco. Es el fallo
de siempre de este proyecto con un disfraz nuevo: **no era una caché sirviendo
lo de ayer, era un servidor de pruebas contestando lo que producción no
contesta**. Cualquier cifra de red medida en `localhost:8322` es de disco,
diga lo que diga el testigo.

### Cuatro roturas provocadas, las cuatro en rojo

Las de siempre, y una que saltó sola: al tocar el párrafo de las cookies, el
guardián que ata la fecha de la política a la huella de su texto paró la suite
y pidió la fecha de hoy. Es exactamente para lo que existe, y es la única de
las cuatro que no hubo que provocar.

### Los seis que quedan

*Superada: la tabla vigente está al final de la sección siguiente.*

| # | Qué pasa | Medido |
|---|---|---|
| 31 | Un ejemplo que da 404 se escribe como si fuera la factura | En producción lo para la huella de `rueda.json`, de rebote; sin ella, pasa |
| 33 | `/entrada` no se vacía nunca | 6 validaciones → 6 ficheros, 480.438 B, todos vivos |
| 34 | Mensajes de libxml2 en inglés dentro del informe | `Premature end of data in tag FileHeader`, `xmlParseEntityRef: no name`… |
| 36 | El testigo de red cuenta lo servido de caché | Pinta 17,7 MB de 24 ficheros en local, que es lo que ocupan en disco: usa `encodedBodySize` en vez de `transferSize` |
| 38 | El 404 y las minúsculas | `/codigo-BR-01` → 200, `/codigo-br-01` → 404. El 404 es el genérico de Vercel, en inglés y sin marca |
| 39 | Cinco menores | HSTS sin `includeSubDomains` —el `.vercel.app` sí lo lleva—, faltan `Permissions-Policy`, COOP y CORP, `prueba.py` como `octet-stream`, `escapar()` sin comillas —hoy sin impacto: solo recibe `error`, `aviso` o `nota`— y el subdominio de Vercel no redirige |

## El inglés del informe y la cifra del testigo

Los puntos 34 y 36, que cierran la tanda C. Los dos son lo mismo visto de dos
maneras: **enseñar una cifra o una frase que no es la que se ha medido**. En el
34 el informe repetía las palabras de libxml2 como si fueran suyas; en el 36 el
testigo contaba lo que ocupan los ficheros y lo llamaba red.

### 34. El informe hablaba inglés cuando el XML no abría

Un fichero cortado a medias se contestaba así:

```
No es XML válido y tampoco EDIFACT. Detalle: Premature end of data in tag
FileHeader line 3, line 4, column 1
```

Y un `&` suelto en una razón social, así: `xmlParseEntityRef: no name`. Es toda
la documentación que recibe quien acaba de mandar una factura que no abre.

**Por qué llevaba tanto sin verse.** Medido el 22-09-2026 sobre los 172
ficheros ajenos de los tres corpus —`muestras`, `MuestrasFE`, `Pfactura3`—:
**cero**. Ni una sola vez. Un fichero que llega a un corpus es un fichero que
alguien pudo abrir; esto sólo sale con uno roto, que es justo cuando quien lo
recibe menos sabe dónde mirar.

**La traducción se cuelga del código y no de la frase.** La frase es texto de
libxml2 y cambia entre versiones; el código es su enumeración y no. Y no es una
precaución teórica: aquí corre lxml 6.1.2 y en el navegador 6.0.2, y **el mismo
fichero cortado da dos códigos distintos** —`ERR_TAG_NOT_FINISHED` aquí,
`ERR_LTSLASH_REQUIRED` allí—. Eso no se vio leyendo el código ni corriendo la
suite: se vio soltándole a la página los veintidós ficheros rotos y encontrando
que uno se colaba por el remate. Sin el remate habría salido una traza.

Son dieciséis códigos, medidos rompiendo un XML de veinticinco maneras. Del
mensaje se saca además el nombre del elemento cuando lo trae, con una expresión
por código; si algún día deja de casar se pierde el nombre y queda la
explicación, que es la degradación correcta. La misma factura de antes ahora
dice:

```
No es XML válido y tampoco EDIFACT: una etiqueta «FileHeader» se abre y el
fichero se acaba sin cerrarla. Suele ser una copia o una descarga a medias.
Línea 4, columna 1.
```

La columna se cuenta desde uno, como la cuenta libxml2 y no como la da
`offset`, que empieza en cero: sin sumar uno el informe mandaba a mirar un
carácter antes de donde está la cosa.

**Lo que no se traduce se dice de quién es.** Un código fuera de la tabla no se
inventa: se pasan las palabras del analizador **diciendo que son suyas**, que
es distinto de colarlas como si fueran de este validador. Lo mismo se ha hecho
con `XSD-OTRO`, el fallo de esquema cuya forma no se reconoce, que pasaba el
inglés a pelo. `VALIDADOR-SE-ATRAGANTA` se queda como está a propósito: ahí el
texto en inglés es la excepción de Python, y esa incidencia ya dice con todas
las letras que el fallo es del validador y no de la factura.

### 36. El testigo contaba el fichero y decía «red»

El panel que cuenta lo que pide la página apuntaba `encodedBodySize`, que es lo
que ocupa el cuerpo del fichero **venga de donde venga**. Lo que hace falta ahí
es `transferSize`, que vale cero cuando algo sale de la caché. Reproducido el
22-09-2026, segunda visita sobre el sitio montado:

| | |
|---|---|
| lo que pintaba el testigo | **17,7 MB** |
| lo que fue por el cable | **9,64 MB** |
| ficheros que no pasaron por la red | **21 de 23** |

En producción es peor, porque allí todo lo pesado va con `immutable` a un año:
la segunda visita no baja casi nada y el testigo habría seguido diciendo lo
mismo que la primera. Un panel que existe para **contar en lugar de afirmar**
estaba afirmando.

Ahora se apuntan las dos cifras y se enseña la que toca: «Ver cuáles · 10,2 MB
por la red y 7,5 MB de tu caché», y cada fichero de la lista dice «de caché» si
no viajó. Se distinguen tres casos y no dos, porque un dominio ajeno sin
`Timing-Allow-Origin` deja las dos cifras a cero, y eso no es lo mismo que
venir de la caché: ese sale con una raya, como antes.

**Ojo con dónde se mide.** Estas cifras son del sitio servido en local, y ahí
`http.server` no comprime: lo que baja es el tamaño en disco. Es la misma
trampa del punto 37, y por eso conviene que quede escrita dos veces.

### Seis roturas provocadas, las seis en rojo

Un código caído de la tabla, la columna contada desde cero otra vez, el nombre
con la coma de libxml2 pegada, un nombre que esta versión no conoce, el remate
colando el inglés como si fuera nuestro, y el testigo volviendo a contar el
cuerpo. Las seis en rojo a la primera.

### Los cuatro que quedan

| # | Qué pasa | Medido |
|---|---|---|
| 31 | Un ejemplo que da 404 se escribe como si fuera la factura | En producción lo para la huella de `rueda.json`, de rebote; sin ella, pasa |
| 33 | `/entrada` no se vacía nunca | 6 validaciones → 6 ficheros, 480.438 B, todos vivos |
| 38 | El 404 y las minúsculas | `/codigo-BR-01` → 200, `/codigo-br-01` → 404. El 404 es el genérico de Vercel, en inglés y sin marca |
| 39 | Cinco menores | HSTS sin `includeSubDomains` —el `.vercel.app` sí lo lleva—, faltan `Permissions-Policy`, COOP y CORP, `prueba.py` como `octet-stream`, `escapar()` sin comillas —hoy sin impacto: solo recibe `error`, `aviso` o `nota`— y el subdominio de Vercel no redirige |


## El vigilante dormido: condenó a una conexión que estaba entregando el 96 %

El 22-09-2026, comprobando producción después de cerrar la tabla de la copia
fiel, el arranque de `www.glosa-e.com` se cayó solo con su propio `SinDescarga`:
«lleva 30 segundos sin llegar un solo byte». El sitio servía bien —`200`,
1.637.748 bytes, `X-Vercel-Cache: HIT`— y la máquina bajaba a ~30 KB/s, así que
lo primero que pareció es que el vigilante se había equivocado con un enlace
lento. Leyendo ese mismo wheel a mano desde la misma página, los trozos llegaban
con un hueco máximo de 1,06 s.

Pero eso no lo demostraba: aquella era **otra** petición, posterior y en
condiciones distintas. Que una lectura nueva fuera bien no dice nada de si la
que se abortó estaba viva. Quedó apuntado como medido y sin arreglar, que es lo
honesto cuando lo que se tiene es un indicio.

### Reproducido, con el cable bajo control

Un servidor de usar y tirar sirviendo el sitio entero por un **cubo de fichas
compartido de 30 KB/s** —un enlace lento es eso, y no un límite por respuesta—,
más un instrumento inyectado delante de la página que apunta, petición a
petición, cuándo llegó su cabecera y cuándo su último byte. **Se cayó las dos
veces**, en el mismo sitio y con la misma cara:

| | Primera | Segunda |
|---|---:|---:|
| Cuándo se cayó | 495 s | 494 s |
| Lo que el servidor llevaba escrito del wheel de lxml | 1.001.782 de 1.637.748 | **1.566.927 de 1.637.748** |
| Lo que la página había contado de esa petición | 0 bytes, ni la cabecera | 0 bytes, ni la cabecera |

El 96 % del fichero estaba escrito en el socket cuando la página dijo que no
llegaba ni un byte. Así que el vigilante sí se equivocaba —y no por el enlace.

### La sospecha que era falsa

Estaba apuntado que el culpable probable era el `respuesta.clone()` con que se
cuentan los bytes: la rama clonada podía quedarse sin recibir nada mientras
Pyodide consume la otra. **Medido y desmentido**: con la original sin leer, la
rama que cuenta recibió 1.600.000 bytes con un hueco máximo de 0,13 s, y doce
megas con 0,10 s. El clon no tiene nada que ver.

### Lo que sí era

El registro de tics del instrumento, en la segunda caída:

```
... 1998  1999  2006  2001  2008  1992  1995  1998  ...   (38 tics, cada 2 s)
                                          45999  60001    (y entonces)
```

La pestaña estaba de fondo. Chrome le junta los tics a una página oculta —de
1 s pasaron a 2 s— y a los cinco minutos la aprieta hasta **uno por minuto**.
En esas lagunas no corre el contador de bytes ni se entregan las respuestas: la
petición del wheel llevaba 49,9 s pedida y ni siquiera había llegado su
cabecera, mientras el servidor escribía sin parar.

Y entonces, en el primer tic después de la laguna, el vigilante mira el reloj,
ve cincuenta segundos sin bytes y condena. **Lo que se paró fue él, no la
conexión.** Es el fallo de esta casa con el disfraz más difícil: el que mide se
apaga, y al volver no distingue entre «no ha pasado nada» y «no estaba yo».

Le tocaba, además, justo a quien más tarda en cargar la página, que es a quien
el comentario del propio vigilante dice que no hay que romper. El precio no era
solo el susto: al saltar, abandona de verdad —eso se arregló el 20-09— y se
llevó por delante 1,5 MB ya descargados.

### El arreglo

**El vigilante solo puede jurar por el tiempo en que estuvo mirando.** Cada tic
mide ahora su propio retraso; si llega más tarde de `DORMIDO` —3 s, que deja
pasar los 2 s medidos de una página oculta pero viva—, eso no es una noticia,
es una laguna: se le perdona al reloj el rato que no vio y no se juzga en ese
tic, para que las respuestas que estaban esperando entren antes del siguiente.
El perdón está topado en el instante actual, porque si un byte entra justo al
despertar, sumarle la laguna entera dejaría al vigilante ciego un minuto más.

No hace falta preguntar por `document.hidden`: lo que importa no es si la
pestaña se ve, sino si el vigilante pudo mirar, y el retraso del tic mide
exactamente eso.

### Probado rompiéndolo

Aquí no hay Node, así que otra vez en el navegador. Lo de antes y lo de ahora,
con el mismo servidor estrecho y las mismas facturas:

| Caso | Antes | Después |
|---|---|---|
| El sitio entero a 30 KB/s, pestaña de fondo | `SinDescarga` a los 494 s, con el 96 % del wheel escrito | **«Listo en 575,41 s»**, las 19 peticiones completas |
| Conexión muerta: 200, un pellizco y silencio | salta a los 30,4 s | salta a los **30,2 s** |
| Muerta después de 20 s con el hilo atascado | salta a los 50,8 s | salta a los **52,0 s** |
| Lenta pero viva: 1,2 MB a 25 KB/s | no salta, 47,2 s | no salta, 47,1 s |
| Se pide algo y el hilo se atasca 35 s | no salta, 53,8 s | no salta, 53,7 s |

Las dos primeras filas son el arreglo; las tres siguientes son la prueba de que
no lo he apagado, que es lo que de verdad hay que demostrar cuando lo que se
toca es una negativa. En la carrera buena, el registro de tics enseña las
lagunas perdonadas: 17 s, y luego cuatro de 60 s seguidas.

`tests/test_vigilante.py` fija las tres piezas, y las tres se provocaron
quitándolas del código una a una:

| Lo que se le quitó | Quién se queja |
|---|---|
| El perdón entero | las tres: `test_una_laguna_no_cuenta_como_silencio`, `test_el_perdon_esta_topado` y `test_no_se_juzga_en_el_tic_de_la_laguna` |
| Solo el tope del perdón | `test_el_perdon_esta_topado` |
| Solo el salirse del tic | `test_no_se_juzga_en_el_tic_de_la_laguna` |
| La medida del retraso (`tardanza` a cero) | `test_una_laguna_no_cuenta_como_silencio` |

La última es la que más importa de las cuatro: deja el perdón escrito y
aparentemente sano, pero midiendo cero, que es la forma en que esto volvería a
romperse sin que se notara en la lectura.


## Dos de la auditoría que llevaban abiertos: lo que no llegó, y lo que no se iba

De los cuatro que quedaban de la auditoría, estos dos son de código y no de
configuración, y los dos se reprodujeron antes de tocar nada. Ninguno da un
aprobado falso; los dos hacen que la página diga algo que no es.

### 31. Un ejemplo que da 404 se escribe como si fuera la factura

Un `fetch` **no falla** porque el servidor conteste 404: devuelve la respuesta
con el cuerpo del error dentro. Dos de los siete del fichero no miraban el
estado, y uno de ellos era el de las facturas de ejemplo.

Reproducido sirviendo el repositorio **como en desarrollo** —que es la
condición en la que esto pasa: sin `dist/rueda.json` no hay huellas, y
`comprobar()` devuelve `null` en vez de quejarse— con
`ejemplos/f-0001.xml` devolviendo un 404 de cuatro líneas:

| | Antes | Después |
|---|---|---|
| El arranque | «Listo en 10,80 s» | «No ha arrancado» |
| Lo que quedaba con nombre de factura | **164 bytes de «404 Not Found»** | nada |
| Lo que decía la página | nada | «El ejemplo «f-0001.xml» no ha llegado: `../ejemplos/f-0001.xml` contesta 404.» |

Y al pedir el informe de ese ejemplo salía un veredicto entero: «1 fichero(s) ·
0 correcto(s) · 0 con errores · **1 SIN COMPROBAR**», hablando de un documento
que nunca llegó. No miente sobre su contenido —dice que no lo pudo
comprobar— pero le pone el nombre de una factura a una página de error de un
servidor.

En producción esto lo paraba la huella del manifiesto, y conviene ver **cómo**:
de rebote. No porque nadie mirara el estado, sino porque lo que llegó no
cuadraba con lo publicado. Una comprobación que solo funciona mientras exista
otra cosa no es una comprobación, es una casualidad con suerte.

El arreglo es una función, `pedir(direccion, queEs)`, y la regla que la
acompaña: **lo que tiene que estar se pide mirando el estado**. Los cuatro
`fetch` que pueden faltar a propósito —el manifiesto, el listado de `dist/`, el
resumen del paquete y el zip— lo miraban ya, cada uno con su porqué escrito al
lado. La prueba no exige que todos pasen por `pedir`: exige que **ninguno** se
salte el estado, que es la regla de fondo y caza el fallo en un sitio nuevo.

### 33. La factura que se soltaba se quedaba en la pestaña

El disco virtual de Pyodide vive en la memoria de la pestaña y no se vacía
solo. Cada validación escribe el fichero en `/entrada/<n>/` y ahí se quedaba
hasta cerrar la pestaña.

| | Antes | Después |
|---|---|---|
| Tres validaciones seguidas | tres facturas vivas en `/entrada/0`, **8.343 bytes** | `/entrada` vacío: ni ficheros ni carpetas |
| Seis validaciones | 480.438 bytes | — |
| Con el Python roto a propósito | — | el error sale, `/entrada` queda vacío y la siguiente validación funciona |

**No es que salieran de ahí.** A ningún sitio se suben, y eso que promete la
página al lado de la zona sigue siendo verdad, medido. Es que son de quien las
soltó y, entregado el informe, ya no hacen falta: quedarse con algo que nadie
ha pedido que se guarde es lo contrario de lo que dice la página.

El borrado va en un `finally`, y eso es la mitad del arreglo: si la validación
revienta, la factura tiene que irse igual, y es justo cuando más fácil es
olvidarse. Se comprobó rompiendo `runPythonAsync` a propósito. La otra mitad es
que cada borrado va en su propio `try`: si la limpieza fallara, taparía el
fallo de la validación, que es el que importa.

### Probado rompiéndolo

Cinco roturas provocadas sobre `web/glosa.js`, cada una con su prueba en
`tests/test_disco_del_navegador.py`:

| Lo que se le quitó | Quién se queja |
|---|---|
| El ejemplo, pedido con `fetch` pelado | `test_ningun_fetch_se_salta_el_estado` y `test_los_tres_que_tienen_que_estar_pasan_por_pedir` |
| `pedir` sin la negativa, solo avisando por consola | `test_hay_una_manera_de_pedir_lo_que_tiene_que_estar` |
| Sin borrar lo soltado | `test_se_borra_aunque_la_validacion_reviente` |
| Borrando solo cuando todo va bien (`catch` en vez de `finally`) | `test_se_borra_aunque_la_validacion_reviente` |
| La limpieza sin proteger pieza a pieza | `test_la_limpieza_no_puede_tapar_el_fallo_de_la_validacion` |

La cuarta es la que más vale: deja el borrado escrito y a la vista, y solo
quita el caso en el que hace falta acordarse.

### Los dos que quedan

| # | Qué pasa | Medido |
|---|---|---|
| 38 | El 404 y las minúsculas | `/codigo-BR-01` → 200, `/codigo-br-01` → 404. El 404 es el genérico de Vercel, en inglés y sin marca |
| 39 | Cinco menores | HSTS sin `includeSubDomains` —el `.vercel.app` sí lo lleva—, faltan `Permissions-Policy`, COOP y CORP, `prueba.py` como `octet-stream`, `escapar()` sin comillas —hoy sin impacto: solo recibe `error`, `aviso` o `nota`— y el subdominio de Vercel no redirige |


## Los dos últimos de la auditoría: el callejón sin salida y las cinco menores

Con estos se cierra la lista. Ninguno hace que el validador diga algo falso de
una factura; los dos son de cómo llega esto a quien lo abre.

### 38. Un código escrito en minúsculas acababa en la página de Vercel

Las fichas de los códigos se sirven con el código tal cual, en mayúsculas, y el
servidor distingue. Medido sobre `www.glosa-e.com` antes de tocar nada:

| Dirección | Antes |
|---|---|
| `/codigo-BR-01` | 200 |
| `/codigo-br-01` | **404 con 79 bytes que dicen `NOT_FOUND`** |

Esos 79 bytes son la página genérica de Vercel: en inglés, sin decir de quién
es el sitio y sin ninguna salida. Quien teclea un código de memoria —que es
justo como se teclea un código— se queda ahí.

**No se arregla con una redirección**, y conviene decir por qué: a Vercel no se
le puede pedir «pon esto en mayúsculas», así que habría que escribir una regla
por código. Ya hay 100 escritas a mano para la familia `BR-AE-1` → `BR-AE-01`,
y esa lista se sostiene porque es cerrada; 390 más, una por código y por cada
forma de escribirlo mal, es la clase de lista que se queda atrás el día que
entra un código nuevo.

Así que se arregla donde se nota: una página de 404 propia, que además rescata.
Si la dirección se parece a la ficha de un código, la pone en mayúsculas,
**comprueba con un HEAD que esa ficha existe** y solo entonces ofrece el
enlace. Ofrecer uno que vuelva a dar 404 sería un cartel, que es lo que este
repositorio no hace.

Probado sirviendo el sitio montado **como lo sirve Vercel** —`cleanUrls`, y
`404.html` en lo que no encuentra—, con una vuelta que merece estar escrita:
la primera versión del servidor de pruebas daba `200` a `/codigo-br-01`, porque
**Windows no distingue mayúsculas y Linux sí**. Es el disfraz de siempre: sale
verde en esta máquina y no es lo que pasa en producción. Con el servidor
distinguiendo a mano:

| Dirección | Después |
|---|---|
| `/codigo-BR-01` | 200 |
| `/codigo-br-01` | 404 con la página propia y un enlace a `/codigo-BR-01` |
| `/lo-que-sea` | 404 con la página propia, sin rescate |

La página lleva el mismo menú que las demás —letra por letra, y la prueba que
lo vigila ahora cuenta siete páginas y no seis— y se queda **fuera del
sitemap** y sin tarjeta social, con su `noindex` puesto: una página de error no
es contenido, y meterla en el sitemap es decirle a un buscador que indexe el
sitio por donde no hay nada.

### 39. Las cinco menores

Cuatro se arreglan y una se deja, dicha:

| Qué | Antes | Después |
|---|---|---|
| HSTS | `max-age=63072000`, sin subdominios —y el `.vercel.app` sí los llevaba— | con `includeSubDomains` |
| `Permissions-Policy` | no estaba | cámara, micrófono, ubicación y cinco más, apagadas |
| COOP y CORP | no estaban | las dos, `same-origin` |
| `prueba.py` | `application/octet-stream`: abrirlo lo descargaba | `text/plain; charset=utf-8` |
| `escapar()` | escapaba `&`, `<` y `>` | los cinco |

De la HSTS **no se pide `preload`**, y es una decisión: esa lista es fácil de
entrar y difícil de dejar, y esto se puede querer deshacer.

Lo de `prueba.py` no es cosmético: es el fichero que dice si el validador hace
lo que promete, y la página invita a leerlo. Si al abrirlo el navegador lo
descarga en vez de enseñarlo, media promesa se queda en el aire.

Y `escapar()` estaba copiada en dos páginas y escapaba tres caracteres de los
cinco, con su resultado pegándose **dentro de un atributo** —`class='glosa " +
escapar(...) + "'`—, donde una comilla cierra el atributo. Hoy por ahí solo
pasan «error», «aviso» y «nota», así que no tenía impacto; el día que pase otra
cosa, el fallo sería de esa línea. Van las dos copias, y hay prueba de que
sigan siendo la misma: dos copias de una función se separan solas, igual que
dos menús.

**La que se deja: el subdominio de Vercel no redirige.**
`glosa-dhm7.vercel.app` sigue sirviendo el mismo despliegue en vez de mandar al
dominio. Se puede cerrar con una redirección y hoy no se hace, pero la primera
versión de este párrafo sostenía eso con dos cosas que no eran, y quedan
corregidas aquí porque el error es más instructivo que el acierto:

- **No lo documenta el `README.md`.** No menciona ese subdominio en ninguna
  línea. Lo mencionan `CLAUDE.md` y la receta de comprobar producción, y lo
  que dicen es un hecho —«sigue sirviendo lo mismo»—, no una decisión tomada.
- **No es «la única puerta si el dominio falla».** Cubre un problema del
  dominio —una renovación, un registro DNS mal puesto, el certificado del
  dominio propio— y nada más: `glosa-e.com` está registrado *en* Vercel y su
  DNS también es de Vercel, así que una caída del alojamiento se lleva las dos
  direcciones por delante. Es una puerta de repuesto para un fallo del
  dominio, no para uno del despliegue.

Lo que sí está medido es lo que cuesta dejarlo, y es poco:
`https://glosa-dhm7.vercel.app/` contesta 200 y sirve
`<link rel="canonical" href="https://www.glosa-e.com/">`, que lo pone el propio
montaje. El motivo habitual para cerrar un subdominio así —que dos direcciones
sirvan lo mismo y un buscador no sepa cuál indexar— ya está cubierto. Queda
abierto para que se decida a propósito, ahora con la base de verdad debajo.

### Probado rompiéndolo

Diez roturas provocadas, cada una en su prueba:

| Lo que se le quitó | Quién se queja |
|---|---|
| La HSTS sin `includeSubDomains` | `test_las_cabeceras_que_no_pone_nadie_por_nosotros` |
| La HSTS **con** `preload` | la misma |
| Sin COOP | la misma |
| `prueba.py` otra vez como descarga | `test_el_fichero_de_comprobaciones_se_puede_leer_de_un_clic` |
| El rescate sin mayúsculas | `test_rescata_el_codigo_escrito_en_minusculas` |
| El rescate sin comprobar con HEAD | la misma |
| La 404 sin decir de quién es el sitio | `test_dice_de_quien_es_el_sitio` |
| La 404 sin montarse con el sitio | `test_existe_y_se_monta_con_el_sitio` |
| La 404 dentro del índice | `test_no_se_indexa` |
| `escapar()` sin las comillas | `test_escapar_escapa_las_cinco` y `test_escapar_es_la_misma_en_las_dos_paginas` |

La quinta salió mal la primera vez y por eso está escrita: la prueba buscaba
`toUpperCase()` en la página, y quitándoselo a la dirección seguía pasando,
porque la misma palabra está en la línea que pinta el texto del enlace. Una
prueba que busca una palabra suelta no sujeta nada; ahora mira la dirección que
se arma.

### La lista de la auditoría se cierra

Los 39 puntos están cerrados o dichos. De los cuatro que quedaban ayer, dos se
arreglaron en el código del navegador y dos aquí; el único que sigue abierto es
el subdominio de Vercel, y está abierto **a propósito**, con su porqué escrito
arriba.


## L10: seis facturas distintas salían con la misma frase

El 22-09-2026 se dejó de dar por mala la forma nueva de las rectificativas, y
la NOTA que quedó decía lo único que entonces se podía decir: que había un
`BG-24` y que no se había leído. El 23-09-2026 la AEAT contestó **qué
calificadores lleva**, y eso convirtió aquella prudencia en pereza.

### Lo que se midió antes de tocar nada

Seis rectificativas, todas con un `BG-24`, y el mismo veredicto:

| Lo que llevaba el `BG-24` | Salía |
|---|---|
| `RECT:TIPO` R4 y `RECT:MODALIDAD` S, completa y bien escrita | `un BG-24 sin leer` |
| solo el tipo, sin la modalidad | `un BG-24 sin leer` |
| un tipo inventado, `R9` | `un BG-24 sin leer` |
| el prefijo del anexo en vez del del correo | `un BG-24 sin leer` |
| una modalidad `S` sin importes | `un BG-24 sin leer` |
| **un albarán colgado de la factura** | `un BG-24 sin leer` |

La última fila es la que duele: una rectificativa escrita exactamente como la
AEAT manda y un albarán que no pinta nada salían iguales.

### Lo único nuevo de aquella respuesta es L10

Conviene decirlo porque parece más de lo que es. Las dos sublistas L2 que
mandó la AEAT —`R1` a `R4`, y `I` y `S`— son **palabra por palabra** las que
el anexo de abril ya trae y el validador ya importaba. Lo que cambió no son
los códigos: es el envase, de la extensión `BG-ES-1` al `BG-24` de la norma.

L10 sí es nueva: el anexo de abril tiene de `L1` a `L8`, y **ni `L9` ni
`L10`** —medido sobre la tabla importada—. Son cinco calificadores, `QR`,
`AUT` y los tres de la rectificativa, y son justo lo que hace legible un
`BG-24`, que es lo que el propio anexo daba por imposible: ahí está escrito
que el `BG-24` de la autorización «no trae ni ruta ni valor fijo con que
distinguirlo de cualquier otro documento adjunto».

### Lo que se puede leer, y lo que no, con el porqué

Se puede decir **cuál** es cada calificador. No se puede decir **cuánto
vale**, y el motivo no es prudencia: es que no está escrito en ninguna parte.
Los dos `BG-24` que el anexo sí publica ponen el valor en sitios distintos:

| `BG-24` | Qué va en el `cbc:ID` (BT-122) | Qué va en la descripción (BT-123) |
|---|---|---|
| el del QR | la URN fija `…:ubl:schema:QR` | «VERIFACTU» |
| el de la autorización | **el número de la autorización** | un texto libre |

Si el calificador pasa a ocupar el `cbc:ID`, el valor tiene que irse a otro
campo, y la respuesta no dice a cuál. Lo razonable es la descripción, por
analogía con el QR —y de paso deja sin sitio al número de la autorización—,
pero razonable no es publicado: comprobar `R4` contra L2.A leyendo un campo
adivinado sería prometer una comprobación que no se ha hecho. Está preguntado.

### La contradicción del esquema, que no se resuelve eligiendo

El correo escribe el esquema `urn:aeat:names:specification:schema:`, **sin
`ubl:`**. El anexo publicado escribe `urn:aeat:names:specification:ubl:schema:QR`
para el QR, que es la primera entrada de esa misma L10. Los dos textos se
contradicen en el único valor comprobable, así que uno de los dos está mal.

Elegir el prefijo equivocado **no daría un fallo**: daría un validador que no
encuentra nada, no se queja de nada y se calla. Es el disfraz de siempre de
este repositorio. Así que se reconoce por la **cola** del identificador y se
aceptan los dos, pidiendo las dos mitades —que empiece por el espacio de
nombres de la AEAT y que el calificador venga detrás de sus dos puntos— para
que un `MIRECT:TIPO` de cualquiera no cuele por el final.

### Lo que falta, escrito como negativa

Quedan dos reglas sin aplicar, las dos porque dependen de saber dónde va el
valor: comprobar el tipo contra L2.A y la modalidad contra L2.B, y **exigir
los importes cuando la modalidad es `S`** —que es más estricto que el anexo de
abril, el cual solo pide la base *si* se informan los importes—.

No se dejan en un comentario que pida memoria. El día que el anexo traiga
`L10`, el módulo **se niega a importarse** y dice qué falta. Es el patrón de
la casa: negarse vale más que acordarse.

### Probado rompiéndolo

Nueve roturas provocadas, cada una con quien se queja:

| Lo que se le quitó | Quién se queja |
|---|---|
| Aceptar solo el esquema del anexo | `test_los_dos_esquemas_se_leen_igual` y tres más |
| No mirar el espacio de nombres | `test_la_cola_sola_no_basta` |
| La cola sin sus dos puntos | la misma |
| No decir cuál de los dos falta | `test_dice_cual_de_los_dos_falta` |
| Leer el valor como si estuviera publicado | `test_no_promete_haber_comprobado_el_valor` |
| No decir que el valor no se lee | la misma |
| Dar cualquier `BG-24` por reconocido | `test_un_bg24_ajeno_sigue_sin_leerse` y tres más |
| Dar por mala la forma nueva | `test_reconoce_el_tipo_y_la_modalidad` |
| Quitar la negativa de `L10` | `test_si_aparece_l10_se_niega_hasta_terminar_de_leer_el_bg24` |

### Y lo que la misma respuesta confirma sin cambiar nada

El **381 sigue fuera de la L1 y la `K` fuera de la L4**, por escrito: «no se
aceptan InvoiceType de tipo 381 en L1. Tampoco se aceptará la categoría K en
L4». Ninguna regla cambia —ya medían eso—, pero el hallazgo pasa de deducción
a cita: una factura válida según la EN 16931 no pasa el anexo español, y lo
dice la Agencia. Añade que **eleva la cuestión a gestión para que reevalúen el
criterio**, así que está confirmado y vivo a la vez, y por eso el `BT-3`/381 y
la L4 siguen aparcados.

## El portero no se reconocía a sí mismo desde un worktree

Salió comprobando el punto 20 de la auditoría —«la suite no es hermética»—, que
se cierra corriéndola en una copia limpia. La primera copia limpia fue un
`git worktree`, y allí la suite **no** salía en verde:

```
2 failed, 2358 passed, 54 skipped
tests/test_ganchos.py::TestUnWorktreeDeEstaCopiaNoEsOtroProyecto
    test_git_reconoce_un_worktree_viva_donde_viva
    test_la_copia_buena_y_lo_que_cuelga_de_ella
```

En un clon de verdad pasan las 2360, así que **no era falta de hermetismo**:
era el portero.

### Lo que pasaba

`del_repositorio()` le pregunta a git cuál es el `.git` común de una carpeta
—eso estaba bien, y es lo que hace que un worktree no se cuele por «otro
proyecto»— y lo comparaba con `REPO / ".git"`. `REPO` sale de la ruta del
propio fichero:

```python
REPO = Path(__file__).resolve().parents[2]
```

Cuando el gancho que se carga es **el del worktree** —y es el que se carga si
la suite corre allí—, `REPO` es el worktree, y el `.git` de un worktree es un
**fichero** que apunta al de la copia principal, no un directorio. Así que la
comparación fallaba siempre y el portero no reconocía ni su propia copia.

Era medio arreglo: le preguntaba a git por la carpeta de la orden y daba por
hecha la suya. Ahora le pregunta **por las dos** y compara común con común. En
la copia principal no cambia nada, porque allí su `.git` es el común.

### Por qué importaba, y no era sólo una prueba en rojo

El gancho de git corre la suite **sobre la copia desde la que se empuja**. Con
dos pruebas en rojo, un push desde un worktree se niega, y un worktree es justo
donde este repositorio recomienda abrir la segunda sesión cuando hay dos a la
vez. La recomendación y el arreglo se contradecían sin que nadie lo hubiera
notado, porque nadie había corrido la suite desde allí.

### Lo que lo guarda

Las dos pruebas que fallaban no lo cazan desde aquí: cargan el gancho de **esta**
copia, donde el medio arreglo bastaba. La nueva monta un worktree, le copia el
gancho de ahora —si no, iría un commit por detrás— y le pregunta por las tres
carpetas: la suya, la principal y una que no es del repositorio.

Provocado:

| Lo que se le quitó | Qué pasa |
|---|---|
| vuelve el medio arreglo, `REPO / ".git"` | rojo |
| git no contesta nunca | rojo |
| todo es del repositorio, hasta lo que no | rojo |

Y de punta a punta, que es lo que vale: desde el worktree, `git push
--no-verify` a un repositorio desnudo de usar y tirar sale **bloqueado por el
portero**, y la suite entera allí da 2360 en verde.

## En un móvil: lo que no se puede partir, y un gris que no llegaba a AA

Salió de un repaso del sitio en móvil y en los dos temas, el 23-09-2026, antes
de tocar nada del diseño. Dos fallos de los que no se ven en un escritorio.

### Las páginas que se salían de lado

Medidas las 399 páginas del sitio montado a 320 px, que es el ancho con que
WCAG mide el reflujo:

| Página | Se salía | Por |
|---|---|---|
| `incidencias.html` | 109 px, y asomaban 285 de las 390 fichas | la línea del fuente en mono y la URN del anexo en la prosa |
| `codigo-*.html` | 40 de las 390 | la línea del fuente, en «Lo escribe» |
| la entrada de la copia fiel | 7 px | `TotalGrossAmountBeforeTaxes`, en negrita |

Las otras siete, en 0. Siempre lo mismo: **algo que no se puede partir por un
espacio**. La URN es `urn:cen.eu:en16931:2026#compliant#urn:aeat.es:CIUS-ES-SPFE:1.0.0`,
64 caracteres seguidos; `validador/solucion_publica.py:651` son 33.

La primera hipótesis estaba mal a medias. El repaso había señalado la línea
del fuente, y ponerle `overflow-wrap: anywhere` a ella sola **no movió ni un
píxel**: las fichas comparten columna en `.fichas`, y la URN de una sola ficha
bastaba para ensanchar las 390. Se encontró quitando culpables de uno en uno
en el navegador hasta que el que quedaba era la prosa.

### Las dos maneras de dejar partir, que no son la misma

| | Qué hace | Dónde |
|---|---|---|
| `overflow-wrap: anywhere` | la rejilla cuenta la palabra como partible **al medir** su columna | las fichas y la página de un código, que son rejillas |
| `overflow-wrap: break-word` | sólo parte **al pintar** | la bitácora, que es texto corrido |

Las dos cosas, medidas: con `break-word` en las fichas la página seguía
saliéndose los mismos 109 px; con `anywhere` en la bitácora, sus tablas —que
se desplazan dentro de `.cuadro`— encogían partiendo palabras en dos celdas.

En escritorio no cambia nada: a 1280 px, la altura de las 390 fichas con la
regla y sin ella es la misma, píxel a píxel, y la de la bitácora también.

### El gris

`--tenue` es el color de los rótulos y los pies, y en claro daba 4,51:1 sobre
el papel, 4,20:1 sobre `--panel-2` y 4,10:1 sobre los fondos flojos del
veredicto. AA pide 4,5 para texto normal. En la página pintada fallaban cuatro
textos: el pie del testigo, el aviso del arranque y dos rótulos del informe.

El repaso dijo que en oscuro no fallaba ninguno, y **era verdad de la página
medida y no del tema**: cuando se arrastra un fichero encima, la zona se tiñe
de `--acento-flojo` y su pie queda a 4,37:1. La página medida no tenía a nadie
arrastrando nada. Por eso la prueba no mira las parejas que hoy se pintan,
sino todas: ocho colores de texto contra ocho fondos, en los dos temas.

| Tema | Antes | Después | Peor fondo |
|---|---|---|---|
| claro | `#6e747e` | `#676c76` | 4,10 → 4,59 sobre `--error-flojo` |
| oscuro | `#868d99` | `#89909b` | 4,37 → 4,54 sobre `--acento-flojo` |

Mismo tono y misma saturación; sólo se movió la luminosidad, de medio en medio
punto, hasta pasar en los ocho fondos. En la página pintada, con el informe
abierto: 364 textos, ninguno por debajo, en claro, en oscuro y en oscuro con la
zona en «arrastrando encima».

`herramientas/tarjeta.py` copia los colores del tema claro a mano y se había
quedado con el gris viejo. Ya no puede: una prueba compara. **La tarjeta PNG no
se ha regenerado** —hace falta bajar Literata— y lleva el gris de antes, que
sobre su papel da 4,51 y pasa.

### Lo que lo guarda

`tests/test_en_un_movil.py` vigila que cada plantilla siga dejando partir, y
con cuál de las dos maneras; `tests/test_contraste.py`, las 128 parejas, que
ningún tema se quede sin un color y que la tarjeta pinte con los de la hoja.
Sin navegador en la suite, lo primero vigila la regla y no los píxeles: los
píxeles se midieron aquí.

Provocado, ocho roturas y ocho rojos: quitar la regla de las fichas, cambiarla
por `break-word`, meterla sólo en un `@media`, ponerle `anywhere` a la
bitácora, volver al gris viejo en cada tema, quitarle un fondo al oscuro y
devolverle el gris viejo a la tarjeta.

### Y la caché, otra vez

Al medir el sitio recién montado, el navegador sirvió el `incidencias.html` de
antes —con `glosa.css?v=b9c1a4cf`, la hoja vieja—, y la primera medida dio los
mismos 109 px. En disco estaba `aa4725bb`. La huella protege la hoja, pero
`python -m http.server` sirve el HTML sin `Cache-Control` y el navegador lo
guarda por su cuenta. Es el fallo de siempre con otro disfraz; se midió de
nuevo pidiendo cada página con una consulta de más.

### Y el orden de la portada, que no era un descuido

El mismo repaso encontró que en un móvil la zona de soltar empezaba a **1,59
pantallas**, detrás del testigo, y propuso subirla. No era un descuido: el
comentario de arriba de `index.html` dice que el testigo va en la primera
pantalla «también en el movil», y ya se había encogido de 540 px para eso.

Medido a 375x812, moviendo los bloques en el navegador, las dos cosas no caben:
lo de arriba acaba en 390 px, el testigo mide 508 y la herramienta con su barra
de arranque unos 560. Hubo que elegir, y se eligió conservar el testigo delante
y bajar lo que sobraba entre los dos, la ficha:

| | Zona de soltar, antes | Después |
|---|---|---|
| 375x812 | 1.292 px — 1,59 pantallas | 994 px — 1,22 |
| 768x1024 | 943–1.151 px, asomando | 768–976 px, entera en la primera |
| 1280x800 | 834 px | 834 px, y todo lo demás igual, píxel a píxel |
| 320x700 | — | 0 px de desborde |

Con `display: contents` y `order` en la media query de estrecho, y no moviendo
el HTML, porque en ancho la ficha tiene que seguir debajo del lema. Eso separa
el orden que se ve del orden del documento, y sólo se puede porque la ficha no
tiene nada que se pueda pulsar: el tabulador sigue yendo del testigo a la zona,
que es lo que se ve. Si un día la ficha lleva un enlace, hay que moverla en el
HTML, y una prueba lo dice.

La prueba calcula el orden como lo haría el navegador —el `order` de cada pieza
y, a igual `order`, el del documento— y exige titular, lema, testigo,
herramienta, ficha y el resto. Seis roturas provocadas, seis rojos: sin
`contents`, sin flex, la ficha delante, la ficha al fondo de la página, el
testigo detrás de la herramienta y un enlace en la ficha.

Queda una diferencia a sabiendas: con el informe abierto, en estrecho la ficha
sale detrás del informe y no detrás de la zona, porque el informe vive dentro
de la misma sección que la herramienta.

## Las marcas con que se escribe, a la vista de quien lee

Salió del repaso de la portada del 23-09-2026, leyendo el informe de ejemplo:
«los 19 códigos de Facturae \*\*existen los 19\*\* en la lista europea». Se
tiró del hilo y no era uno.

| Dónde | Cuántos | Por qué se veían |
|---|---|---|
| mensajes del informe | 6: uno en `cadena.py`, cuatro en `copia_fiel.py` y uno en `firma.py` | el mismo texto va a la consola, al JSON y a la página, y ninguno de los tres pinta marcas |
| la página de códigos | 15 páginas —14 fichas y el catálogo—, cinco también en la descripción del buscador | `pagina_incidencias.py` escapaba las explicaciones de `glosario.py` y nada más |

De los seis mensajes, en los diez ejemplos solo sale uno, `COPIA-PAGO-MEDIO`,
y lo saca `fe-0001.xml`: justo la factura del botón «Ver un informe de
ejemplo». Los otros cinco esperaban a una factura que los encendiera.

### Por qué se arreglan distinto

Un mensaje del informe es texto llano que va a tres sitios, así que ahí no
caben marcas: se quitan, y lo que hay que apartar —el nombre de una etiqueta—
va entre «», como en el resto de mensajes. `GrossAmount` pasa a
«GrossAmount», y el `python -m validador --montar-anclas` de
`ANCLAS-SIN-RENOVAR` se queda sin comillas: es una orden para copiar.

Las explicaciones del glosario solo van a HTML, y allí las marcas dicen algo
que quien las escribió quería decir. Se traducen a `<strong>` y a `<code>`
**después** de escapar: al revés, una explicación que nombrara `<Invoice>`
entre comillas invertidas metería una etiqueta de verdad en la página. En la
descripción, que el buscador enseña como texto, se quitan.

### Lo que lo guarda

`tests/test_sin_marcas.py`, desde tres lados, porque ninguno ve todo:

- **el fuente**: las 1.376 cadenas escritas dentro de `Incidencia(...)` en 16
  módulos. No ve un mensaje que se componga fuera de la llamada;
- **lo que sale**: los diez ejemplos validados, campo a campo. Ve eso, pero
  solo en lo que los ejemplos encienden;
- **la página montada**: el catálogo y las 390 fichas, el texto que pinta el
  navegador y la descripción. Y además que la negrita y la mono lleguen, no
  solo que las marcas desaparezcan: quitarlas también dejaba la página limpia,
  perdiendo lo que querían decir.

Provocado, cuatro roturas y cuatro rojos: traducir antes de escapar, pintar la
ficha sin traducir, la descripción con marcas y un mensaje con asteriscos.

Las cadenas con marcas que quedan en `validador/` no llegan a nadie: la tabla
de la copia fiel y los arreglos de rutas de `sintaxis.py` no se imprimen, y
las negativas de `paquete.py` son para quien monta el sitio.

## El informe, pasado a limpio

Tanda 2 del rediseño de la portada, el 23-09-2026. Un defecto medido y dos
cambios de forma que salieron del repaso contra las de al lado.

### El margen pisaba el filete

En el informe de la página, el texto del margen —la gravedad, el código y la
norma— tocaba la raya de color de la glosa: medido a 1100 px, **2 px de
solape en los 33 rótulos** del informe de ejemplo. Salía de dos medidas que
tenían que casar y no casaban: el cuerpo se corría 1,35rem a la izquierda
sobre un hueco entre columnas de 1,25rem.

Ahora el filete es el borde derecho del margen y el aire es su relleno, así
que no queda nada que casar. Medido igual, en claro y en oscuro: **19,6 px**
de aire en los 34 renglones, y 0 px de desborde a 320.

La raya de color se fue con él. Era el recurso de tarjeta más visto de la web
y aquí no decía nada que no dijera ya el rótulo; en su sitio va un corchete
del color de la gravedad, que es el signo de la marca. En el móvil, con el
margen encima, el corchete abraza la glosa entera. Y `word-break: break-all`
pasó a `overflow-wrap: anywhere` en el código y en los datos: el primero
parte cualquier palabra al final del renglón, también las de «Debería ser»,
que son prosa.

### Lo que se ha mirado, antes del detalle

El informe decía qué se había comprobado **al final**, en una frase de
corrido debajo de todas las glosas. Quien leía «Sin errores» arriba no sabía
contra qué hasta haber bajado entero. Ahora lo dice antes de ninguna queja,
en tres columnas —la forma, el contenido y la firma— numeradas como en «Qué
mira» de la portada, cada una con su cuenta. Es la idea del resumen del HTTP
Observatory de Mozilla, que pone lo comprobado encima de las pruebas.

El peligro de decirlo en dos sitios es que un día digan cosas distintas, y
aquí lo distinto sería una columna con «Sin errores» de algo que no se ha
mirado. Por eso no hay dos cuentas: `InformeLote._alcance_por_partes` reparte
lo mirado entre las tres partes, y de ahí salen la frase de siempre, que sigue
en la consola letra por letra —pasan sin tocarlas las 627 pruebas que la
vigilan—, y `InformeLote.partes()`, que es lo que pinta la página. La cuenta
de cada columna se hace por familia de código, con una tabla cerrada:
`PARTE_DE_LA_FAMILIA`. Y `familia_de` pasó a `incidencias.py` para que el
catálogo y el informe agrupen con la misma regla.

Lo que no estaba en la frase y la columna necesita: por qué no se ha mirado la
forma. Con EDIFACT, «No aplica»; sin esquemas, «Sin mirar». Nunca «Sin
errores».

Así sale `fe-0001.xml` en el sitio montado:

| Parte | Cuenta | Lo que dice |
|---|---|---|
| 1 · La forma | Sin errores | la forma contra el esquema XSD |
| 2 · El contenido | Sin errores | la aritmética de Facturae y el código único |
| 3 · La firma | 2 avisos | que no esté rota; y no se comprueba de quién es el certificado |

### El veredicto

Era una tarjeta con una raya de color y la cuenta en pastillas; ahora es una
frase en Literata con la cuenta dentro —«Sin errores, con 2 avisos.»— y las
notas nombradas debajo. Las pastillas se miran como un semáforo, que es
justo lo que esto no es. El banco de la portada usa el mismo veredicto y cambia
con él: también sin caja.

### Lo que lo guarda

`tests/test_informe_por_partes.py`, 98 pruebas. Que la tabla de familias esté
cerrada en los dos sentidos; que, con los diez ejemplos y las ocho
combinaciones de esquemas, anclas y listas, ninguna columna diga «Sin
errores» sin haber mirado nada y todo lo que diga esté, tal cual, en la
frase; que las cuentas de las tres sumen las quejas que hay; y en la página,
que las columnas salgan de lo que manda Python y que el cuerpo de la glosa no
vuelva a correrse hacia el margen.

Provocado, cinco roturas y cinco rojos: una familia sin parte, la forma sin
mirar diciendo «Sin errores», el cuerpo corrido otra vez, las partes pedidas
con otras banderas que la frase, y la firma contada como contenido.

## La portada B: la herramienta en la primera pantalla

Tanda 3 del rediseño, el 23-09-2026. El repaso contra las de al lado midió que
**la zona de soltar empezaba a 834 px en cualquier escritorio**: a 1366×768
no asomaba, a 1440×900 asomaban 66 de sus 208 px, y solo a 1920×1080 se veía
entera. Los cinco validadores españoles que siguen en pie ponen la
herramienta en la primera pantalla. De las dos direcciones que se dibujaron,
el titular eligió la B, «el folio glosado».

### Qué es

A la izquierda, el titular, el lema y el testigo. A la derecha, un folio con
la forma exacta del informe: tres glosas de las facturas de muestra —un
error, un aviso y una nota— y, en el sitio de la glosa siguiente, la zona de
soltar, con «Y aquí, al margen, las de la tuya». Enseña lo que devuelve esto
antes de pedir nada, que es lo que hace Squoosh con sus imágenes de prueba.

| Escritorio | Zona de soltar, antes | Ahora |
|---|---|---|
| 1280×800 | 834 px, fuera | 503–662 px, entera |
| 1366×768 | 834 px, fuera | 503–662 px, entera |
| 1920×1080 | 834–1042 px | 503–662 px, entera |

Y debajo, en la misma primera pantalla, las muestras: acaban a 755 px.

### Las glosas del folio no se pueden desviar

Están escritas a mano, porque tienen que verse antes de que el validador
termine de bajar. Resumidas —el campo con lo que tiene la factura, y una o dos
frases del mensaje—, y la barra del folio lo dice. Todo lo escrito a mano se
desvía, así que `tests/test_portada.py` valida cada muestra y exige que el
código, la gravedad, la norma, el campo y lo que tiene sean los del validador,
y que cada frase sea frase entera del mensaje de verdad.

### Cuatro muestras en vez de una

Había una sola, `fe-0001.xml`, y con ella se veía cómo es un aviso y nunca
cómo es un error. Ahora son cuatro, una por formato: Facturae firmada, UBL,
CII y EDIFACT, y entre las cuatro salen las tres gravedades. Ya viajaban con la
página, así que no pesan nada. La etiqueta de cada una se comprueba contra lo
que detecta el validador.

### El testigo, compacto

Cada fila enseña su cifra, y debajo va lo que ha pedido la página con la lista
a un clic. Las dos explicaciones que iban en las filas —la de la factura y la
de lo guardado— solo aparecen cuando dicen algo que la cifra no dice: después
de leer una factura, o cuando hay algo guardado en el navegador. Provocado:
una cookie y un dato guardado salen a los dos segundos, la cookie en rojo, y
al borrarlos el testigo vuelve a como estaba.

### Y el orden, sin trucos

La ficha, que iba entre el lema y la herramienta, pasa debajo de la portada en
todos los anchos. Con eso el documento queda en el orden en que se ve, y el
`display: contents` con `order` de la media query de estrecho ya no hace
falta: la prueba de `tests/test_en_un_movil.py` mira ahora el documento, y que
nada lo reordene por encima.

Provocado, cuatro roturas y cuatro rojos: otra cifra en una glosa del folio,
una frase que el validador no escribe, una muestra con el formato cambiado y
un `order` en la herramienta.

**En el móvil, esta tanda deja la zona peor**: a 375×812 empieza en 2,05
pantallas, porque las tres glosas de muestra van delante de ella. Se arregla
en la tanda siguiente, antes de publicar nada.

## La zona de soltar, en la primera pantalla del móvil

Tanda 4 del rediseño, el 24-09-2026, y la deuda que dejó la 3: la portada B
subió la zona de soltar a 503 px en cualquier escritorio y **la bajó en el
móvil**. En una columna el folio enseñaba primero sus tres glosas de muestra,
que a 375 de ancho ocupaban 765 px, y la zona iba detrás.

| Ancho | Zona de soltar, antes de la B | Con la B | Ahora |
|---|---|---|---|
| 375×812 | 1,22 pantallas | 1661 px, 2,05 pantallas | 610–809 px, entera |
| 768×1024 | — | 962 px, asomaban 62 de 159 | 613–751 px, entera |
| 1366×768 | 834 px | 503–662 px | 503–662 px, sin tocar |

A 375×812 está entera también mientras carga, que es cuando el texto de la
zona es más largo; a 320×640 empieza a 1,04 pantallas, sin nada que se salga
de lado. Son ventanas: en el teléfono el navegador se queda parte de la
pantalla para sus barras, y a 375×667 entra el rótulo de la zona (631–660 px)
y no el botón (733 px).

### El folio, en estrecho, con la zona delante

Por debajo de 54rem el folio pone la zona y las muestras primero, el arranque
después y, debajo, «Así sale el informe» con las tres glosas. «Y aquí, al
margen, las de la tuya» se va, porque ya no tiene glosas encima.

Es la única excepción a que nada reordene la portada, y se puede hacer porque
**lo que se mueve no se enfoca**: ni las glosas, ni su barra, ni el arranque
tienen un enlace, un botón o un `tabindex`, así que el tabulador sigue
recorriendo lo que se ve en el orden en que se ve.
`tests/test_en_un_movil.py` lee los hijos del folio, los ordena como los
pinta la hoja en estrecho y exige las dos cosas; y que no haya un `order`
fuera del folio.

### El testigo, en tres filas y un toque

Era la propuesta 5: tres filas y un enlace a lo que ha pedido la página, para
que la zona entre sin quitar el testigo de delante. En el móvil el testigo
apilaba cada rótulo encima de su cifra, y eso ya no hacía falta: en escritorio
va en una columna de 19rem, más estrecha que un móvil, y cabe en filas. Y su
pie —lo pedido, la lista y la nota de lo que no alcanza a ver— es ahora un
`<details>`: plegado en el móvil, «Qué ha pedido la página, y cómo se mide»,
y abierto en ancho, sin rótulo que pulsar. El testigo pasa de 392 a 208 px.

**Lo abre la hoja y no JavaScript**, con `::details-content`. El script corre
después de pintar: abierto de salida, el móvil lo pintaba y lo recogía, y la
zona saltaba; cerrado de salida, saltaba el escritorio. Medido en este
Chromium que la regla lo abre. Un navegador sin `::details-content` —Firefox
antes de la 143, Safari antes de la 18.4— lo deja plegado también en ancho:
la nota queda a un toque, como en el móvil, y no se esconde. En esos dos no se
ha probado.

Provocado, seis roturas y seis rojos: las glosas sin su `order`, el folio
sin `display: flex` —y entonces el `order` no hace nada—, un botón dentro de
una glosa de muestra, el pie abierto de salida, la regla que lo abre sin
`content-visibility` y un `order` fuera del folio. Quitarle el
`order` a la zona no rompe nada, y la prueba lo deja pasar con razón: con 0
sigue delante de 2, 3 y 4.

## Pegar la factura como texto

Tanda 5 del rediseño, el 24-09-2026: la propuesta 7, que sale de Docuflair.
Hay quien tiene la factura copiada de un correo o de su programa de
facturación y no guardada en un fichero. Debajo de las muestras, plegado —es
el camino de unos pocos, y la zona es el de todos—, «O pégala como texto, si
la tienes copiada»: un cuadro y «Validar lo pegado».

**Lo pegado se hace fichero y entra por `soltar()`**, el mismo camino que uno
soltado. Una ruta aparte podría portarse distinto, y lo pegado y el fichero
dejarían de dar el mismo informe. Medido en el navegador: `f-0006.xml` pegada
—con blancos delante, como llega de un correo— y abierta con su botón de
muestra dan el mismo veredicto, las mismas tres partes y los mismos códigos;
y lo mismo `fe-0001.xml`, firmada, con la firma intacta. Y pegar tampoco
pide nada: con `fe-0001.xml` pegada, 0 peticiones mientras se leía —lo cuenta
el propio testigo, y `performance` dice lo mismo—, ni cookies ni nada guardado
en el navegador.

### Lo que cambia al pegar

- **El portapapeles da letras, no bytes.** Reproducido con lxml: «España»
  escrita en UTF-8 bajo una declaración ISO-8859-1 se lee
  `Espa\xc3\xb1a`, y sin un error. En la página, una moneda «EUÑ» salía en
  el informe como «EUÃ». Ahora la declaración se reescribe a UTF-8 y encima
  del informe se dice: «Su declaración decía «ISO-8859-1», pero el
  portapapeles da letras y no bytes: se ha leído en UTF-8». Con el arreglo,
  «EUÑ».
- **Lo que se pierda al copiar cambia lo que cubre la firma.** Provocado: un
  salto de línea detrás de `<FileHeader>` en `fe-0001.xml` da FIRMA-ALTERADA.
  Así que, cuando lo pegado lleva firma, el informe avisa de que para
  comprobarla mejor el fichero. Sin firma no se dice, porque no hay nada que
  pueda dejar de cuadrar.
- **Los blancos de delante se quitan.** Son del correo, no de la factura, y
  delante de la declaración XML hacen que no abra: «XML declaration allowed
  only at the start of the document».

Y en un teléfono el cuadro lleva letra de 16 px: con menos, Safari amplía la
página al tocarlo.

### Cómo se prueba sin navegador

`tests/test_pegar.py` saca de la página las expresiones regulares de
`comoFichero`, que valen igual en Python, y las prueba contra las muestras de
verdad —que declaran UTF-8 con comillas dobles y con simples— y contra
declaraciones ISO-8859-1, windows-1252 e iso-8859-15. La reescritura la repite
en Python, y una prueba exige que la página diga exactamente lo que repite,
porque la primera versión de estas pruebas **no cazaba que se quitara**: la
copia en Python seguía reescribiendo por su cuenta.

Provocado, siete roturas y siete rojos: una ruta aparte en vez de `soltar()`,
la declaración solo con comillas dobles, sin reescribir, «utf8» sin guion
tomado por otra codificación, sin quitar los blancos, la advertencia de la
firma siempre y el cuadro sin su letra de teléfono.

## Tres cosas que se dicen de fuera: sin red, el Observatory y VALIDe

Tanda 6 del rediseño, el 24-09-2026: las propuestas 8, 9 y 10. Las tres
afirman algo que la página no comprueba sola, así que cada una se midió o se
vio viva antes de escribirla, y cada una va con la condición que la hace
cierta.

### «Desconecta la red y suelta tu factura»

Estaba en la lista como **sin medir**, y se midió: con la página cargada y
«Listo», se apagó el servidor —`curl` ya no conectaba— y se validaron las
cuatro facturas de muestra, pegadas y abiertas con su botón. Las ocho dieron
el mismo veredicto que con el servidor encendido, `performance` no apuntó ni
una petición y la consola no dio un error. Ahora lo dicen la nota de «Listo»,
la pregunta de si la factura se sube y la política de privacidad, que es una
prueba que cualquiera hace sin herramientas de desarrollo.

La condición es «Listo»: antes, sin red el validador no arranca. Por eso la
invitación solo sale en la rama en que ha arrancado, y quien invite a
desconectar en la portada o en la política tiene que decir «Listo»:
`tests/test_lo_que_se_cita.py`.

### El HTTP Observatory de Mozilla, con su fecha

En la política, detrás del párrafo de la política de contenido, que es una de
las cabeceras que mira: A+, 140 sobre 100 y 12 pruebas de 12, el 23-09-2026, con enlace a
su medición de `www.glosa-e.com` y la advertencia de que el enlace lleva a la
última, que puede ser de otro día. Una nota de un tercero cambia, y sin fecha
acabaría diciendo lo que el Observatory ya no dice: hay prueba de que ninguna
página cite su nota sin fecha.

### VALIDe, la herramienta oficial para la firma

La lista pedía comprobar antes que la referencia era la buena y seguía viva,
porque el enlace de FACe a su validador ya daba «página no encontrada». VALIDe
contestaba el 24-09-2026, y lo que se dice de él sale de sus propias páginas:
que es la «aplicación de validación de firma y certificados online» de
@firma, que valida en línea firmas y certificados —facturas electrónicas
incluidas—, y que los documentos **se le envían** y su aviso de datos dice que
se borran al terminar.

Va en la pregunta de si esto vale ante la Agencia Tributaria o FACe, y dice
las dos cosas: que allí se mira en línea lo que aquí se queda a medias por no
salir a la red, y que a cambio la factura se envía. Recomendarlo sin lo
segundo sería mandar a alguien a subir su factura sin avisarle, desde la
página que presume de no hacerlo; hay prueba de que no pase.

Provocado, cinco roturas y cinco rojos: la invitación también en la rama sin
paquete, la pregunta sin «Listo», el Observatory sin fecha o enlazando otro
sitio, y VALIDe sin decir que allí se envía.

## El repaso de las seis tandas, antes de publicarlas

El 24-09-2026, con las seis tandas del rediseño en `main` y sin publicar, se
repasó todo junto: lo que se va, contra producción, en claro y en oscuro, en
escritorio y en móvil, con un informe abierto y la política montada.

Salió una frase vieja. La tanda 2 subió lo mirado al principio del informe y
cambió «Qué mira» y la política, pero la pregunta «¿Esto certifica que mi
factura es válida?» seguía diciendo que el informe «termina siempre con una
línea que dice qué se ha mirado». Ahora dice que empieza por ello, y
`tests/test_informe_por_partes.py` no deja que ninguna página vuelva a decir
que el informe acaba con lo mirado: con la frase de antes, rojo.

Los números de las tres partes del informe —«1 · La forma»— se miraron por
si eran los pasos 01/02/03 que la lista dice que no se copian, y no lo son:
repiten los de «Qué mira», que ya estaban, y dicen algo cierto, que son las
mismas tres comprobaciones.

## La tarjeta social, con el gris de la hoja

El 23-09-2026 la hoja cambió de gris y `herramientas/tarjeta.py` se puso al
día, pero **la tarjeta PNG no se regeneró**: hacía falta bajar Literata. La
que ve quien pega el enlace en otro sitio llevaba el pie en `#6e747e`, y la
hoja, `#676c76`.

Regenerada el 24-09-2026, y sin bajar nada: el guion pinta ahora con
`web/letra/literata.woff2`, la Literata que sirve la página. Vale igual que la
de Google Fonts —el eje óptico ya viene en 12, el de la marca, y los pesos
llegan de 400 a 600, los dos de la tarjeta; y trae todas sus letras—, y se
midió: el titular sale con los mismos 22 459 píxeles de tinta que con la de
Google. Los ejes se ponen ahora por nombre, porque esta trae uno y la otra dos,
y por posición un «[12, peso]» pedía un peso de 12.

`tests/test_tarjeta.py` pinta la tarjeta y la compara con la publicada: 0
píxeles distintos con la de hoy, 5475 con la del gris viejo. Donde no hay
Pillow —GitHub— se salta, porque no es dependencia del proyecto. Y comprueba
que el titular y el lema son los de la portada, que el guion prometía y nadie
miraba.

Provocado, cuatro roturas y cuatro rojos: la tarjeta vieja de vuelta, otro gris
en el guion sin repintar, otro titular, y el pie de las páginas con texto de
más —que es la otra cosa de ese día: la línea de autoría pasó a ser
«© 2026 Glosa-e» a secas, por decisión del titular, y una prueba lo exige—.

## El filtro del catálogo contaba bien y no escondía nada

En «Qué significa cada aviso», escribir en «Filtrar por código o por texto» no
cambiaba la lista. Lo encontró el titular y se reprodujo en producción el
24-09-2026: con `BR-01`, el contador decía «2 códigos de 390», las familias sin
coincidencias desaparecían, y se seguían viendo las 390 fichas.

El guion no fallaba: marcaba 388 fichas con `hidden`. Lo que fallaba era
`hidden`. El navegador lo cumple con un `display: none` de su propia hoja, que
es la que menos manda, y `.codigo-ficha` dice `display: grid`. Cualquier regla
nuestra con `display` le gana. Las secciones sí se escondían porque nadie les
había puesto `display`.

El arreglo va en `glosa.css`, la hoja de todas las páginas, y no en el
catálogo: `[hidden] { display: none !important; }`. El `!important` hace falta
y se midió: sin él las dos reglas pesan lo mismo, gana la última, y la de cada
página va detrás de la hoja compartida; con `BR-01` se veían 220 fichas en vez
de 2. Antes de ponerla se miró que no cambiara nada más: en la portada, el
aviso legal, el banco, la tesis, la bitácora, la 404 y una ficha de código,
ningún elemento con `hidden` se estaba viendo.

`TestElFiltro`, en `tests/test_pagina_incidencias.py`, exige la regla fuera de
cualquier `@media` y con `!important`, y que el filtro siga escondiendo con
`hidden`, que es lo que la hace necesaria. Provocado, cuatro roturas y cuatro
rojos: sin la regla, sin `!important`, dentro de un `@media`, y el filtro
cambiado a una clase.

### Y después, lo que enseñaba

Arreglado el `hidden`, el titular probó «sello» y seguía sin filtrar bien. Se
midió: salían 19 fichas, las 16 de la familia SELLO y tres de otras familias
—CADENA-CADUCADA, FIRMA-CADUCADA, REVOCACION-POSTERIOR— que solo nombran «el
sello de tiempo» en su explicación. Esas tres van antes en la página, así que
eran lo primero que se veía; la familia SELLO empezaba 2300 px más abajo, por
debajo de un resumen del catálogo que no se movía, y cada familia seguía
titulada «6 códigos» o «12 códigos» encima de una sola ficha. El filtro
acertaba y parecía roto.

Ahora el nombre manda: si lo buscado está en el nombre de algún código, salen
esos. Las que solo lo mencionan en la explicación se cuentan y se ofrecen
—«Ver 3 más que lo mencionan en la explicación»—, no se esconden sin decirlo; y
si no está en ningún nombre, se busca en el texto, como antes. Se busca sin
tildes y, en el nombre, sin separadores: «revocacion» encuentra REVOCACION-*,
«sello tiempo» encuentra SELLO-TIEMPO y «br01», BR-01. Mientras se filtra, el
resumen se aparta y cada familia dice cuántas enseña: «1 de 6 códigos».

Comprobado en el navegador con nueve búsquedas, también a 375 px. En las
pruebas no hay navegador, así que se hizo lo de `test_pegar.py`: la función
que elige va copiada tal cual en `TestLoQueEnseniaElFiltro`, que se niega si
la de la página cambia, y la misma lógica se corre en Python contra las 390
fichas de verdad. Provocado, cuatro roturas y cuatro rojos: que vuelva a
mandar el texto, sin quitar tildes, el resumen quieto y los títulos sin
contar.

## La tarjeta social llevaba otra marca

Lo vio el titular: la marca de la tarjeta no era la de la página. Medido en el
código el 24-09-2026:

| | Cabecera (`.marca`) | Tarjeta |
|---|---|---|
| Signo | corchete y **tres** líneas, la última más corta | corchete y **dos** líneas: el dibujo del favicon |
| Color | trazo en `--acento`, sin caja | trazo blanco sobre el **bloque plata** |
| Nombre | Literata **600**, `letter-spacing: -.01em` | Literata **400** |

Es el mismo disfraz de siempre, en pequeño: el 23-09-2026 el bloque salió de la
cabecera, `MARCA.md` dejó escrito que seguía en «el favicon, `glosa-e.svg` y
la tarjeta social», y la tarjeta ni siquiera llevaba ese bloque, sino el del
favicon, que es otro dibujo. Nada lo comparaba con nada.

`herramientas/tarjeta.py` pinta ahora la marca de la cabecera con sus mismas
cifras —la máscara de 48 × 40 con trazo de 3,5, la caja de 1,85 × 1,55 rem por
cada 1,3 rem de nombre, el hueco de ,6 rem— y la línea de base del nombre donde
la pone el navegador, que se midió allí: 0,4408 em bajo el centro del signo. El
signo se pinta a cuatro veces y se reduce, porque Pillow no suaviza trazos y el
viejo salía dentado. Con el nombre a 50 px, la marca entera mide 272,6 px en el
navegador y 274,2 en la tarjeta: Pillow no tiene aquí `raqm` y no aplica el
espaciado de pares de la letra, que es la diferencia.

`test_la_marca_de_la_tarjeta_es_la_de_la_cabecera` lee esas cifras de
`glosa.css` y del guion —sin importarlo, así que corre donde no hay Pillow— y
las compara. `test_contraste.py` perdonaba el gris del bloque en la tarjeta, y
ya no. Provocado, cinco roturas y cinco rojos: el signo con dos líneas, el
nombre en 400, el bloque de vuelta, el signo en tinta y la tarjeta vieja
publicada.

Y una cosa de proceso, que no es de la tarjeta: el push anterior —el del
filtro— se negó porque, mientras el gancho pasaba la suite, se estaba editando
este guion en el mismo árbol, y la prueba de la tarjeta vio un dibujo que ya no
era el publicado. El gancho hizo lo que tenía que hacer. Mientras corre, el
árbol no se toca.

## La tarjeta presumía de algo que no era verdad

La tarjeta vieja decía abajo «forma, contenido y firma», y el README lo
justificaba: la firma iba primero porque **ningún otro validador gratuito la
comprueba**. El estudio de mercado del 24-09-2026 lo desmiente: B2Brouter tiene
un validador gratuito que mira XSD, esquematrón y firma, y FacturaView verifica
la firma XAdES en el navegador. Era una afirmación sin medir, puesta en lo
primero que ve quien recibe el enlace.

La tarjeta nueva, elegida por el titular el 25-09-2026, no dice qué hace:
lo enseña. Un trozo de factura de muestra —rotulada así, «factura de muestra»—
con un total que no cuadra y su glosa, BR-CO-15, con la primera frase que
escribe el glosario. `test_la_glosa_de_la_tarjeta_es_la_del_glosario` exige que
el código exista, que salga como error, que la frase sea la del glosario y que
el total de muestra no cuadre. Provocado: otra frase, un código que sale como
nota, un código que no existe y un total que cuadra, cuatro rojos; y la tarjeta
anterior publicada, rojo en la comparación de píxeles.

## La tarjeta de Telegram era la de antes, y la pestaña llevaba otra marca

Lo vio el titular el 25-09-2026, con dos capturas. En la primera, el enlace a
la portada pegado en Telegram enseñaba **la tarjeta de antes** —el bloque gris
y «Forma, contenido y firma»—, dos horas después de publicar la nueva. En la
segunda, la pestaña del navegador llevaba el cuadro gris con el signo en
blanco, que tampoco es la marca de la cabecera.

**La tarjeta.** Producción servía la nueva: 73.265 bytes y la misma huella que
el fichero del repositorio. Lo que no cambiaba era la dirección: `og:image`
decía `https://www.glosa-e.com/marca/tarjeta.png` desde el primer día, y quien
pinta la vista previa de un enlace la guarda por dirección. Es el fallo de
siempre, la quinta vez: **algo servido de una caché haciéndose pasar por lo de
hoy**, y todo verde por dentro. La prueba de píxeles comparaba bien el
fichero; el fichero no era lo que se veía fuera.

Ahora `og:image` lleva `?v=` con los ocho primeros del SHA-256 de la tarjeta
que se publica, como el estilo y el cargador: cambia cuando la imagen cambia, y
no cuando no. `test_la_tarjeta_lleva_la_huella_de_la_que_se_publica` y
`test_otra_tarjeta_es_otra_direccion` lo guardan. Queda una parte que no se
arregla desde aquí y **no está medida**: Telegram guarda también la vista
previa de la página, y hasta que la vuelva a leer enseña la que tiene. Se
fuerza mandándole el enlace a @WebpageBot, y eso lo hace quien tiene la
cuenta.

**La pestaña.** `MARCA.md` decía que el favicon era «un segundo dibujo»: el
cuadro plata con el signo en blanco y dos líneas. Cuando la cabecera pasó al
signo en `--acento` el 23-09-2026 y la tarjeta la siguió el 24, la pestaña se
quedó sola con la marca vieja. Es la misma desviación que la de la tarjeta, un
día después, y por lo mismo: nada comparaba el favicon con la cabecera, solo
las copias del favicon entre sí, y solo tres de las siete páginas.

Ahora el favicon es el signo de la cabecera —los cuatro trazos, el grosor de
3,5, los remates redondos— en `#1c4e80` de día y `#8ab4e0` de noche, que son los
dos `--acento` de la hoja, con `prefers-color-scheme` dentro del propio SVG:
una imagen no ve la hoja, y con un color solo el azul de día se pierde en una
barra de pestañas oscura. Recortado a su tinta en un cuadrado de 42 unidades,
para que a 16 px sea todo lo grande que puede. Mirado en el navegador a 16 y a
32 px, sobre barra clara y oscura, en los dos temas.

`tests/test_marca.py` lo compara ahora con la máscara de `.marca::before`
—trazos, grosor, remates— y con los dos acentos de la hoja, en las siete
páginas, y se niega si el recorte corta el dibujo. Provocado, ocho roturas y
ocho rojos: el cuadro viejo en una página, en las siete, dos líneas en vez de
tres, sin color de noche, otro azul de día, un recorte que se come el remate,
otro grosor y la tarjeta sin huella.

Con esto, el bloque plata ya no sale en ninguna página publicada. Vive en
`web/marca/glosa-e.svg`, que no se publica.

## Los enlaces de casa pasaban por una redirección

Salió al abrir Search Console por primera vez, el 25-09-2026, con 13 días de
datos. Google tenía 110 páginas indexadas de 398, y 327 sin indexar: 295
«descubiertas» y todavía sin visitar, 13 «rastreadas» y sin indexar —todas
fichas BR-— y 19 «página con redirección». Y dos páginas recibían impresiones
por partida doble: `codigo-BR-47` y `codigo-BR-47.html`, y lo mismo con
BR-51.

La canónica y el sitemap decían la dirección limpia desde el principio, y hay
prueba para eso. Lo que nadie miraba eran los enlaces de una página a otra.
Medido en producción: 225 por ficha de código, 396 en el catálogo y 9 en la
bitácora, todos a `./nombre.html`, que con `cleanUrls` contesta 308. A un
dominio nuevo, con 295 páginas en cola, cada enlace le costaba al buscador dos
peticiones en lugar de una.

**Por qué no se había visto.** Las pruebas miraban lo que se le dice al
buscador —el sitemap y la canónica—, no el camino que sigue para llegar. Y en
local no se nota nada, porque `http.server` sirve `legal.html` tal cual y no
hay redirección que ver.

**El arreglo.**

- Al montar, los enlaces `./nombre.html` pasan a `./nombre`, y `./index.html`
  pasa a `./`. Las plantillas no se tocan: en local las sirve `http.server`,
  que no sabe de `cleanUrls`.
- El montaje **se niega** si queda un enlace de casa con `.html` que no ha
  sabido limpiar.
- La vista previa del sitio montado pasa a `herramientas/servir_sitio.py`, que
  sirve como Vercel: direcciones limpias, 308, `404.html` y **mayúsculas
  distinguidas**, porque Windows no las distingue y Vercel sí.
- Las pruebas pasan la limpieza por las plantillas de verdad, los artículos,
  el catálogo y las 390 fichas.
- Montado de verdad: 399 páginas, 9.965 enlaces de casa limpios y ninguno con
  `.html`.

**Y la lista de hermanos.** Cada ficha de la familia europea enlazaba a los
otros 218 códigos. Bien medido, en BR-47 eran 223 de sus 532 palabras
visibles, un 42 %. Ahora van los 12 vecinos de la serie y un enlace a la
familia en el catálogo: la ficha queda en 331 palabras. **Que esto sea lo que
frenaba la indexación no está demostrado**: Google no dice por qué no indexa.
Se comprueba el 23-10-2026, comparando con estas cifras.

**Una medida mal hecha por el camino.** La primera cuenta de BR-47 dio 304
palabras con 218 de lista, y así se le contó al titular. Estaba mal:
`text_content()` de lxml junta los enlaces seguidos sin espacio, y la lista
entera contaba casi como una palabra. Se vio al medir la página ya arreglada:
con 206 enlaces menos tenía **más** palabras que antes, lo que no podía ser.
Rehecha con `itertext()`, las cifras buenas son las de arriba.

Provocado, ocho roturas y ocho rojos:

- sin limpiar;
- sin la negativa;
- la portada como `./index`;
- la familia entera otra vez;
- sin el enlace al catálogo;
- la ventana pegada al principio;
- el servidor sin distinguir mayúsculas;
- el servidor sin la redirección.

Una de las ocho salió verde la primera vez, y el fallo era de la rotura: rompía
una línea a la que no se llega, porque las mayúsculas se comprueban antes.
Rota donde toca, rojo.

## La bitácora decía que un total mal copiado no se ve

La entrada del 21-09-2026, «Copia fiel: lo que nadie traduce», decía que una
copia con el total de Facturae llevado a su homónimo «cuadra consigo mismo,
pasa las validaciones de la copia». La cabecera de `copia_fiel.py` lo decía
con otras palabras: «un hueco se ve mientras que un número equivocado no».
Lo encontró el 26-09-2026 una revisión independiente, y **no era cierto**.

**Reproducido** con las cifras del propio artículo, pasando dos copias por el
validador: 1.000 de base, 210 de IVA en el desglose, y la cuota y el total a
elegir.

| Copia | Cuota (BT-110) | Total (BT-112) | Qué sale |
|---|---|---|---|
| Bien traducida | 210 | 1.210 | nada |
| Con los importes de Facturae | 262 | 1.112 | `BR-CO-14` y `BR-CO-15` |
| Con los 262 también en el desglose | 262 | 1.112 | `BR-CO-15`, `BR-CO-17` y `BR-S-09` |

La copia deja de cuadrar consigo misma, y las reglas de coherencia de la norma
lo cazan. Lo que de verdad pasa sin error es otra fila de la tabla: el medio
de pago, porque los códigos de Facturae existen en UNCL4461 queriendo decir
otra cosa.

**Por qué se escribió.** La frase venía del razonamiento con que se empezó la
tabla —«no falta un dato, cambia una cifra»— y se dio por buena sin pasar una
copia por el propio validador. Se midió la diferencia entre los dos
documentos, pero no qué pasaba al validar la copia.

**El arreglo.**

- La entrada lleva un aviso de corrección arriba y el párrafo reescrito. La
  entradilla lo dice, como en la corrección del 07-09.
- La cabecera y el comentario de `copia_fiel.py` dicen ahora que la cifra se
  ve, y que lo que aportan las notas es el porqué y la cifra que va.
- `test_el_total_copiado_tal_cual_no_pasa_las_reglas_de_la_copia` fija las
  dos mitades: la copia bien traducida sale limpia y la copiada da
  exactamente `BR-CO-14` y `BR-CO-15`.

**Provocado:** con la comprobación exacta de `BR-CO-15` apagada en
`en16931.py`, la prueba sale en rojo con `{'BR-CO-14'}`. Restaurada, verde.

## Una coma decimal salía en inglés, y en UBL 2.5 también las fechas

Lo encontró el 29-09-2026, buscando qué pasaba con las respuestas de UBL, y no
es de las respuestas: es de todo UBL. Con el esquema de verdad, no con los de
doce líneas de `test_esquema.py`, el fallo más corriente de una factura hecha a
mano, una coma decimal, no se traducía.

**Reproducido** con `ejemplos/f-0001.xml`, pasado por `esquema.validar` con los
XSD que viajan en `web/paquete.zip`:

| Se cambia | UBL 2.1 | UBL 2.5 |
|---|---|---|
| `PayableAmount` a `1.234,56` | `XSD-OTRO` | `XSD-OTRO` |
| `Percent` a `veinte` | `XSD-TIPO` | `XSD-OTRO` |
| `IssueDate` a `2026-02-31`, `ayer` o `2026-13-01` | `XSD-TIPO` | `XSD-OTRO` |

Y el `XSD-OTRO` decía «esta queja no se ha sabido traducir» y una frase de
libxml2: `'1.234,56' is not a valid value of the local atomic type.` Lo que se
había escrito para este caso —«un importe lleva punto decimal, sin separador de
miles: 1234.56, no 1.234,56 EUR»— no se enseñaba nunca sobre un importe de UBL.

**Por qué.** `_RE_TIPO` solo conocía la frase con nombre de tipo, «of the atomic
type 'xs:decimal'». En UBL los importes son un tipo complejo que extiende el
primitivo —desde la 2.1—, y en la 2.5 también las fechas y las horas: el valor
se juzga contra un tipo anónimo y libxml2 dice «local». Las pruebas usaban
`xs:decimal` a secas y nunca vieron esa frase. La 2.5 es lo único que admite la
solución pública, así que el fallo caía justo donde iba a haber más facturas.

**El arreglo.** Una segunda frase, `_RE_TIPO_LOCAL`, que da `XSD-TIPO`. Como la
frase no trae el tipo, se deduce del nombre del elemento (`_tipo_por_nombre`), y
eso es una apuesta que se midió antes de escribirla: sobre los **873 elementos
`cbc:` de UBL 2.1 y los 1.202 de UBL 2.5**, resolviendo cada uno hasta su
primitivo, todo lo que acaba en `Date` es fecha y en `Time` es hora, y los 196
(2.1) y 260 (2.5) decimales acaban todos en `Amount`, `Quantity`, `Measure`,
`Percent`, `Rate` o `Numeric`. Una excepción, `TimeAmount`, que es un
texto y no puede dar este error. Un nombre sin sufijo conocido recibe una pista
genérica y no se inventa un tipo.

**Provocado.** `tests/test_ubl_de_verdad.py` corre en GitHub porque saca los
esquemas del zip versionado. Sin la rama de `_RE_TIPO_LOCAL`, fallan 6 pruebas;
quitando `Percent` del sufijo, 2; con `Date` sin fecha, 4; con `Time` sin hora,
2; y con un sufijo de más (`Name`), 3. El sufijo se vuelve a medir en cada
corrida: una versión de UBL que declare una fecha con otro nombre lo dice ahí y
no en un informe.

**Sin medir:** el navegador. Pyodide trae libxml2 2.9.10 y estas frases se han
visto con 2.14.6; si cambian, el caso vuelve a `XSD-OTRO`, que es lo de antes y
no algo peor.

**Después, en la revisión del 29-09-2026.** El sufijo llevaba `Factor` y una
rama para `DateTime` puestos por si acaso: contado, ningún elemento `cbc:` acaba
así ni en la 2.1 ni en la 2.5, y nada los probaba. Fuera; si una versión los
trae, la prueba del sufijo se pone en rojo. Y tres ramas de la traducción que
ninguna prueba ejecutaba, ahora con la suya: el valor vacío (una plantilla sin
rellenar; con `.+` en vez de `.*` caen tres de cuatro, la cuarta es la fecha de
la 2.1, que tiene tipo con nombre y va por la otra frase), la pista de la hora
con `IssueTime` y la pista genérica con un adjunto en base64 roto, que es lo
que la alcanza con datos de verdad. Provocadas las cuatro: rojo.

## De la 2.0 de UBL no se puede subir

Salió midiendo si a un `ApplicationResponse` se le puede aplicar la regla de
«se sube de versión y nunca se baja» (la siguiente entrada). La regla estaba
medida entre la 2.1 y la 2.5, y `_VERSIONES_UBL` la aplicaba también a la 2.0
sin que nadie hubiera abierto un esquema 2.0.

**Reproducido** el 29-09-2026 con `UBL-Invoice-2.0.xsd`, una copia de
`phax/ph-ubl` (sha256 `4b2fd813…7791`; docs.oasis-open.org no contesta desde
donde se midió, así que no se ha cotejado con la distribución de OASIS), contra
el 2.1 y el 2.5 del paquete. La factura es `ejemplos/f-0001.xml` con
`UBLVersionID` 2.0:

| Factura | 2.0 | 2.1 | 2.5 |
|---|---|---|---|
| sin extensiones | válida | válida | válida |
| `ext:ExtensionContent` vacío | válida | **inválida** | **inválida** |
| contenido de extensión sin namespace | válida | **inválida** | **inválida** |

Con `ApplicationResponse`, que comparte la extensión: 400 documentos generados
desde el esquema 2.0, 400 válidos en 2.0 y **227 en 2.5**; los 173 que fallan lo
hacen todos por `ExtensionContent`. Con el contenido de extensión siempre de
otro namespace, 400 de 400.

**La causa** es un solo tipo, `ExtensionContentType`: en la 2.0, `xsd:any
namespace="##any" processContents="skip" minOccurs="0"`; desde la 2.1,
`##other`, `lax` y `minOccurs="1"`. Todo lo demás cuadra: los otros 28 tipos
alcanzables desde `ApplicationResponse` son subsecuencia ordenada del 2.5 y
ninguno pide más.

**El arreglo.** `_NO_SUBEN = ("2.0",)`: un documento que declara la 2.0 se
mide con el esquema 2.0 o con ninguno, y `XSD-SIN-ESQUEMA` dice cuál falta. Es
lo mismo que se hace con una versión que no se conoce. El coste es real y se
dice: el paquete no trae la 2.0, así que las facturas 2.0 se quedan sin
comprobar la forma hasta que alguien instale ese esquema. Cuántas facturas 2.0
circulan **no está medido**.

**Provocado:** sin la línea de `_versiones_ubl` que corta la subida, fallan
`test_de_la_2_0_no_se_sube` y `test_sin_el_esquema_de_la_2_0_se_dice_cual_falta`.
El caso de la tabla no puede ir en una prueba porque el esquema 2.0 no está en
el repositorio; lo que se fija es lo que hace el código con él.

## Un `ApplicationResponse` salía «sin comprobar», y había dos maneras de arreglarlo mal

El 29-09-2026 el titular pidió que `esquema.py` validara también
`UBL-ApplicationResponse-2.5.xsd`, que ya viajaba en `web/paquete.zip` sin que
nada lo pidiera. El esquema era la parte fácil: el documento ni siquiera se
reconocía.

**Reproducido.** Una respuesta que valida contra su esquema, y la misma con un
`IssueDate` repetido, salían igual, `No se ha podido validar. XML válido, pero su
elemento raíz «ApplicationResponse» no corresponde a Facturae, UBL, CII ni
EDIFACT`, con código de salida 1. Una respuesta rota y una buena no se
distinguían.

**Las dos maneras de arreglarlo mal**, medidas antes de escribir nada, en el
orden en que se le ocurren a uno:

| Cómo se reconoce | Respuesta buena | Respuesta con la forma rota |
|---|---|---|
| Como `UBL` (factura) | **16 errores** que no le tocan: `XSD-RAIZ`, 13 reglas `BR-*` y dos `CU-*`; con el CIUS declarado, `SPFE-TIPO-DE-FACTURA` («es un abono») | los mismos |
| Familia nueva, sin más | sin quejas | **`conforme`, sin errores**: sin árbol no se pasa esquema ni firma |
| Familia nueva en `_FAMILIAS_XML`, con guardias | sin quejas | `XSD-ORDEN` |

La primera es el «acusar en falso» de siempre: hay nueve sitios que deciden por
`familia == UBL` —`codigo_unico.py` cuatro, `esquema.py`, `factura.py` tres y
`solucion_publica.py`—, todos suponen una factura, y cada uno habría que
enseñarlo a excluir la respuesta; el olvido se paga con una acusación. La
segunda es **peor porque no se ve**: una respuesta tocada después de firmar
tampoco se enteraba. Absolver en silencio es lo que este repositorio existe
para no hacer.

**El arreglo.** `RESPUESTA = "ApplicationResponse"` es una familia propia en
`formato.py`, sin `tipo_documento` y con `conforme_en16931` siempre falso
—declarar el perfil de una factura no la hace factura—. Con
ella, todo `if familia == X` y todo `SINTAXIS.get(familia)` contestan «no me
toca» por su cuenta, y solo hay que enseñar lo que sí le toca:

- `factura._FAMILIAS_XML` la lleva, para que se parsee y pase por el esquema, el
  DOCTYPE y la firma. Sin ella, lo de la tabla.
- `esquema._nombres_esperados` pide `UBL-ApplicationResponse-{versión}.xsd`.
- Tres guardias que se leen mal si faltan: `en16931.reglas` (sin ella,
  `SIN-SOPORTE` diciendo «solo se ha identificado, no validado» junto a la
  columna de la forma diciendo «Sin errores»), `solucion_publica.reglas` (sin
  ella, `SPFE-SINTAXIS` diciendo que el anexo «solo define» el CIUS sobre UBL,
  y la respuesta es UBL) y `codigo_unico.validar` (sin ella, `CU-00`).
- **`Informe.mirado`.** La forma es lo que se le comprueba a una respuesta, así
  que sin esquema no queda más que la firma. Medido con `esquemas/` vacío —el
  caso por defecto del CLI—: una respuesta rota salía «1 correcto(s)», código
  de salida 0 y «No se ha comprobado nada» escrito justo debajo. Ahora es `SIN
  COMPROBAR` y sale con 1, como un fichero que no se pudo abrir. Una factura sin
  esquemas sigue siendo correcta: todavía se le miden las cuentas.
- La frase del final y las columnas dicen «el contenido de las respuestas
  (ApplicationResponse)», y ya no prometen la forma en un lote de respuestas
  sin su esquema.

**Se subió de versión con medida.** Los esquemas 2.1, 2.2, 2.3 y 2.4 de
`ApplicationResponse` son copias de `phax/ph-ubl`, rama `master` bajada el
29-09-2026 (docs.oasis-open.org no contesta desde donde se midió; el 2.1 es la
CS1, no la OS), y se compararon con el 2.5 del paquete. Sus sha256, para saber
qué se midió aunque `master` se mueva:

| Versión | sha256 de `UBL-ApplicationResponse-2.x.xsd` |
|---|---|
| 2.0 | `ce9084f683184ecf37d418c63ee69585beb89f5b80ca4a0c9bf83ab1551dabac` |
| 2.1 | `9420edfe126e86eb3aa051a872940935a4badef12e56322c1a76d2cbcb07ad18` |
| 2.2 | `cc25bb23861c8b56e2c2131fa7d50eaa9dba5d429b86266249da5d44deba2ea9` |
| 2.3 | `82b0bb8858b8e024398e552d33e9cdf87ca449a76734b986e022d207e22cccef` |
| 2.4 | `aaff6aadc5da3450deea777bc581ce703a035292df656c0f74b9f3532bdb19da` |

Los de `common/` no van aquí; el generador de los 400 documentos tampoco se
versionó, así que esa cifra **no se puede repetir** desde el repositorio. Sobre todos los
tipos alcanzables desde el elemento —38, 41, 45 y 45—: cada uno es subsecuencia
ordenada del 2.5, ningún `minOccurs` sube ni `maxOccurs` baja, los elementos
nuevos son todos opcionales y los elementos hoja (158 a 180) tienen un tipo
idéntico.
400 documentos generados desde cada esquema viejo pasan los 400 contra el 2.5.
Con la 2.0 no: la entrada anterior.

**Lo que no está medido:** el navegador; ninguna respuesta real de terceros ni
el mensaje de anulación de la solución pública, cuyo texto no está publicado;
los patrones de las restricciones se compararon como texto, no como lenguajes;
y los esquemas viejos frente al oficial.

**Lo que cambia para quien ya usaba esto:** una respuesta que valida pasa de
salir con 1 a salir con 0. Ningún test lo fijaba. Y hay frases que dicen «la
factura» o «Facturae» sobre una respuesta: las de firma (`FIRMA-ALTERADA`, las
de la revocación, y `FIRMA-NO-XADES`, que dice que Facturae pide XAdES, y ya lo
decía de una factura UBL), y la última línea del alcance, «ni si lo que dice
la factura es cierto», que sale también en un lote de solo respuestas. Son
ciertas de fondo y se dejan anotadas aquí, sin arreglar: la última viaja a la
página como constante, y cambiarla es tocar `glosa.js`.

**Lo que encontró la revisión, y se cerró antes del commit.** Una revisión
independiente —regresión contra el commit anterior sobre los ejemplos, el
corpus oficial y cientos de mutantes suyos; respuestas hostiles escritas con lo
esperado apuntado antes; fuzz contra lxml a secas; y mutación del código
nuevo— no encontró ninguna acusación en falso ni ninguna absolución. Sus
cifras son suyas y no se repiten aquí. Encontró esto:

- **Un error encontrado se contaba SIN COMPROBAR.** Reproducido con una
  respuesta 2.0 firmada y tocada después de firmar: el lote decía «0 con errores
  · 1 SIN COMPROBAR» encima del propio `FIRMA-ALTERADA`, la línea del fichero
  decía «no se ha podido comprobar» sin nombrarlo, y la página ponía de
  titular «Hay ficheros que no se han podido mirar». El veredicto y el código
  de salida eran buenos; el desglose no. Ahora `validado` es también cierto
  con un error encontrado, y la línea dice los errores y que la forma no se
  miró. Un error no hace correcto a nadie, así que por ahí no se absuelve.
- **«No hay esquema» con el esquema instalado y roto.** La línea de estado lo
  decía encima del `XSD-ESQUEMA-ROTO` que dice que está. Ahora dice «no hay un
  esquema que se pueda usar».
- **`esquema.validar`**, la función pública de solo la forma, daba por validada
  una respuesta sin esquema. Solo la usan las pruebas; ahora dice lo mismo que
  `factura.validar`. `en16931.validar` y `codigo_unico.validar`, que tampoco usa
  nadie más, siguen dándola por buena: no le miden nada, y su «sin errores» es
  de sus reglas.
- **El trozo del contenido llevaba una coma** —«…(ApplicationResponse), de las
  que solo se mira la forma y la firma»— en una lista que se une con comas, y
  prometía la firma también sin firma. Ahora es solo lo que no se mira.
- **El mensaje de un documento que no se reconoce** decía que un `Order` de UBL
  «no corresponde a Facturae, UBL, CII ni EDIFACT», y es UBL. Ahora da la lista
  entera de lo que se valida, y si la raíz se llama como uno de ellos con otro
  namespace, dice el namespace que tendría que llevar.
- **La portada** decía que lo que no es de los cuatro formatos no se valida.
  La pregunta de los formatos dice ahora lo de las respuestas, y que la forma
  se mide con el esquema de la 2.5.
- **Pruebas que no podían fallar**: una del ID de una respuesta igual al de una
  factura (la clave del código único lleva el NIF del emisor, y una respuesta no
  lo trae; se ha quitado), y la que recorre `formato.py`, que no veía una familia
  escrita como cadena (medido: `familia="Order"` pasaba). Ahora exige constantes
  con nombre y ningún `Deteccion` por posición.
- **Más huecos de la red**, cerrados con su prueba: el esquema que está
  y no compila, el recuento de «0 correcto(s)», la firma en pie sin esquema, el
  anexo que no se promete, el lote con una respuesta mirada y otra no, la
  consola sin esquemas, la columna de la forma, el reconocimiento por nombre y
  namespace a la vez, la versión con otro perfil, la subida sin depender del
  zip, una sola compilación del esquema, y las frases enteras.

**Provocado otra vez.** Veintiuna guardias, una a una, en una copia: cada una
pone en rojo la prueba que le toca.

**Lo que se dejó sin hacer, y por qué:** que el informe diga con qué versión
de esquema se midió cuando no es la declarada (ver el README, «Subir no vale al
revés»); haría falta un código nuevo en el catálogo publicado, y eso lo decide
el titular.

**Provocado.** `tests/test_respuesta.py` corre en GitHub porque saca los esquemas
del zip versionado. Quitando cada guardia, una a una, se ponen en rojo las
pruebas que le tocan: la familia fuera de `_FAMILIAS_XML` (las de forma, las de
firma y la que recorre `formato.py`), los nombres de esquema, las tres guardias
de reglas, la frase del contenido, `mirado` (entre otras, la de la consola con
1), la frase que promete la forma sin esquema, la respuesta que «dice seguir la
EN 16931», la que entra como `UBL`, la versión por el CIUS, `Informe.validado` y
la 2.0 que sube. Una prueba lee `formato.py` y no deja que una familia nueva
salga de él sin estar en `_FAMILIAS_XML` o ser EDIFACT.

**Y la portada prometía de más.** Comprobado en producción el mismo día, con las
respuestas pasadas por el navegador de verdad: la buena salió correcta, la de
un `IssueDate` repetido `XSD-ORDEN`, la del 31 de febrero `XSD-TIPO` con «febrero
de 2026 tiene 28 días», y la 2.0 `XSD-SIN-ESQUEMA` y sin comprobar. Pero la
pregunta de los formatos, publicada con el cambio, decía que la forma se mira
con el esquema 2.5 «aunque declaren otra versión», y con la 2.0 no es así. Ahora
dice de la 2.1 a la 2.4, que la 2.0 sale sin comprobar y que sin versión se le
supone la 2.1. Una prueba compara la frase con `_NO_SUBEN`; provocada con la
frase de antes, rojo.

## La página enseñaba su disco por dentro, y los segundos con punto

Visto en producción el 29-09-2026, al comprobar las respuestas de UBL con el
navegador de verdad. Una respuesta que declara la 2.0 salía con este aviso:

> No se ha comprobado la forma: falta el esquema de este formato. El que le
> toca se llama UBL-ApplicationResponse-2.0.xsd, y se busca dentro de
> /opt/factura-e/esquemas.

`/opt/factura-e` es donde `glosa.js` descomprime el paquete, en el disco virtual
del navegador. Nadie puede abrir esa carpeta, y en la página no se puede añadir
un esquema: la frase servía en consola, donde la carpeta es la de quien valida,
y se había copiado tal cual a un sitio donde no significa nada. Y el arranque
decía «Listo en 46.67 s»: `toFixed` escribe el punto en cualquier navegador,
mire el idioma que mire.

**Reproducido** antes de tocar nada: el bloque `INFORME` de `glosa.js`, corrido
en CPython con `web/paquete.zip` descomprimido como lo descomprime la página,
da la frase de arriba con la carpeta de la prueba. Las ocho pruebas nuevas
salían en rojo, también en una copia de `main` con la prueba encima.

**Lo que se hizo.** `Catalogo` tiene ahora una `procedencia`, como `Almacen` con
las anclas, y la página la pone: el aviso dice «…y no está entre los esquemas
que vienen con esta página». En consola no hay procedencia y sigue diciendo la
carpeta, que es lo que hace falta para poner el esquema. Los segundos del
arranque y los milisegundos del banco salen con coma, como ya salía el tiempo
del banco en la portada.

**Buscando dónde más pasaba**, cuatro lectores por separado (rutas en lo que
devuelve el motor, órdenes de consola, cifras de la web y cifras del motor), y
un quinto repasando lo que traían, fichero:línea. De la misma familia, y arreglados aquí:

- **El fichero que tumba al validador** salía como «No se ha podido validar. No
  se ha podido validar /entrada/0/factura__.xml.»: la ruta del disco virtual,
  el nombre ya limpiado para poder escribirlo («factura ñ.xml» pasa a
  «factura__.xml») y la frase dos veces. Ahora: «No se ha podido validar. El
  validador ha fallado con «factura ñ.xml».», con el nombre que tiene en el
  ordenador de quien lo soltó. Se alcanza de verdad: una Facturae con un
  `TaxRate` de 400 nueves revienta en `facturae.py` con `InvalidOperation`.
- **La procedencia de las anclas** decía «que viene con esta pagina», sin tilde,
  en cada firma que llega a una autoridad de la lista. Era texto del informe
  escrito dentro de un fichero cuyos comentarios van sin tildes, y se contagió.
- **La explicación de `XSD-SIN-ESQUEMA`** en la página de códigos decía que el
  aviso da la carpeta «que es lo que hace falta para arreglarlo». Ahora cuenta
  las dos: la carpeta en consola, y en la página que no está entre los que trae.

**Una revisión aparte** encontró dos huecos en las pruebas nuevas, y los dos
se han cerrado:

- **La guardia de la familia entera estaba ciega en Windows.** Buscaba la ruta
  en el texto de `json.dumps`, que escribe cada barra invertida dos veces: en
  la máquina donde corre el gancho que no deja empujar, la ruta no salía nunca
  aunque estuviera. Medido emulando Windows con una carpeta que lleva `\`: con
  el aviso de antes dentro, la prueba pasaba en verde. Ahora busca en lo que la
  página lee, ya descodificado, y la carpeta de la prueba lleva una barra
  invertida también en Linux, para que GitHub la ejercite.
- **La de la coma solo miraba la definición de `seg`.** Con un
  `total: Math.round(…) / 1000` al final del arranque, la página volvía a
  decir «Listo en 46.672 s» con todo en verde; y un `toFixed(CIFRAS)` o un
  `toFixed( 1 )` no los veía. Ahora exige que cada cifra del arranque pase por
  `seg`, y la coma detrás de todo `toFixed` que no sea un cero escrito tal
  cual, también en las subcarpetas de `web/`.

**Provocado.** Catorce roturas, una a una, en una copia: la página sin
procedencia, el aviso que dice siempre la carpeta, `por_defecto` que se come la
procedencia, el arranque y el banco con punto, un `toFixed(1)` nuevo sin coma,
uno con una constante y otro con espacios, el total sin `seg`, el lote que no
pasa el nombre a la caída, la caída que vuelve a decir la ruta o la lleva en su
mensaje, la ruta del catálogo en el «tiene» del aviso, y la procedencia sin
tilde. Las catorce ponen en rojo la prueba que les toca. La que vigila la
familia entera corre los ejemplos de la portada, una factura 2.0 y una
respuesta 2.0 por el `INFORME` de la página y mira que ni la carpeta del
paquete ni la de los ficheros soltados salgan en nada de lo que vuelve:
mensaje, campo, «tiene», resumen o las partes.

**Lo que se dejó sin hacer, y por qué.** Salió al buscar y no es de este
arreglo; cada cosa pide una decisión o un cambio aparte:

- **La revocación, en la página.** Toda firma que llega a un ancla y cuyo
  certificado dice dónde está su lista sale con «bájala y ponla en la carpeta
  de revocaciones»; la columna de la firma dice que hace falta esa lista, y la
  tabla de la portada, «o la tienes instalada». En la página no hay dónde
  ponerla. Arreglarlo es decidir qué promete la página sobre la revocación.
- **Las cifras del motor van con punto**: unos 45 sitios, en el «debería ser»,
  en el «tiene» y a veces en el mensaje. Es una decisión: el punto es como va
  escrito el XML, y la coma es como se lee, y toca `sintaxis.fmt`. Al paso, con importes de tres decimales acabados en 5 el aviso se
  contradice: una línea de 100.125 con suma declarada 100.12 da BR-CO-10
  «Debería ser: 100.12 · Tiene: 100.12», porque `:.2f` redondea al par y la
  regla redondea las mitades hacia arriba. Medido.
- **Una Facturae con un `TaxRate` de 400 dígitos tumba al validador**
  (`InvalidOperation` en `facturae.py`), y el aviso de la caída enseña el nombre
  de la excepción de Python.
- **Desde el 03-02-2027**, cuando venza la renovación de las anclas del
  paquete, toda factura firmada sacará en la página «Hay que volver a montarlas
  con python -m validador --montar-anclas», y dirá que la cadena llega aunque
  no llegue.
- Menores: «almacén» e «instalada» en los avisos de una firma que no llega a
  ningún ancla, que salen hoy con el ejemplo `fe-0001.xml`; los mensajes de
  error de `glosa.js` y los nombres de las comprobaciones del banco van sin
  tildes; el banco dice «1247225 bytes» sin punto de miles; y
  `XSD-ESQUEMA-ROTO` pondría la ruta del disco virtual, aunque con el paquete
  de hoy no sale.

**Sin medir:** el navegador. Esto se ha medido corriendo en CPython, con lxml
6.1.2, el mismo bloque de Python que corre la página; en Pyodide va lxml 6.0.2. Se verá en
producción después de fusionar.

## El ejemplo de la AEAT pasaba sin que se le mirara nada

**Qué pasó.** El 02-10-2026 el buzón técnico de la AEAT contestó a la consulta
del 23-09-2026 con una captura de un XML de ejemplo y ni una frase de criterio.
Se transcribió el 05-10-2026 de una grabación de pantalla que subió Jefe. El
ejemplo resolvía las tres preguntas de L10 (ver
el README, «El ejemplo del 02-10-2026») y traía, sin anunciarlo en el correo,
otro `CustomizationID` y otro `ProfileID`. Se escribió la cabecera del ejemplo
sobre el cuerpo de la factura de pruebas del CIUS y se pasó por el validador
entero, en `main` (`6f8364c`):

| Se midió | Salía |
|---|---|
| Una 384 con el identificador del ejemplo y sin más `BG-24` que el QR de abril, con `ubl:` | «sin errores», exit 0. Con el identificador de abril, ERROR |
| La misma, sin `UBLVersionID` y con líneas de cobro | UBL 2.1 supuesta, un XSD-ORDEN falso («cambiados de sitio») y un BR-CO-16 falso que con el CIUS se quita a propósito |
| Un QR escrito como el ejemplo, sin `ubl:` y sin dirección | nada: `SPFE-QR` muda |
| Una 384 cuyo único `BG-24` es el QR sin `ubl:` o la autorización | una NOTA que decía que «ninguno de sus identificadores es un calificador de L10», y `AUT` sí lo es |
| `R1`/`S` frente a `R9`/`X`, en el sitio del ejemplo | la misma NOTA para los dos |
| El `ProfileID` del ejemplo con el identificador de abril | ERROR de `SPFE-PROCESO` |

**Por qué.** Tres cosas colgaban de la misma cadena, `urn:aeat.es:CIUS-ES-SPFE`
(`formato.MARCADOR_CIUS_ES`): reconocer la solución pública, suponerle UBL 2.5
sin `UBLVersionID` y, a través de lo primero, aplicar el anexo y nombrarlo en la
frase de alcance. El ejemplo no lleva esa cadena. El QR se buscaba solo con el
esquema del anexo, con `ubl:`, aunque los calificadores de la rectificativa ya
se leían con los dos desde el 23-09-2026. Y `AUT` solo salía en los comentarios:
ninguna constante del código lo reconocía.

Al paso, el reconocimiento se hizo más estricto. Antes valía cualquier
identificador que empezara por `urn:aeat:names:specification:` y acabara en el
calificador; ahora, uno de los dos esquemas escritos, con y sin `ubl:`, y el
calificador entero detrás. Un tercero sale como «un BG-24 sin leer», que es NOTA
igual que antes.

La deducción de la versión ya se había cerrado una vez («Suponer 2.1 ahí no era
una imprecisión», en `formato.py`). Volvió porque el arreglo de entonces
colgaba de un nombre, y el nombre cambió. Ahora cuelga de que el identificador
nombre a la AEAT, `urn:aeat.es:`, y hay una prueba que comprueba que los dos
identificadores conocidos lo llevan.

**La apuesta que no se programó.** Hasta el 02-10-2026 el repositorio decía que
lo razonable era leer el valor del calificador en la descripción, por analogía
con el QR, y que razonable no es publicado. El ejemplo lo pone en
`cbc:DocumentTypeCode`. Si se hubiera programado la apuesta, hoy saldrían malas
las facturas escritas como enseña la Agencia. No adivinar fue lo que salvó esto.

**Lo que no se vio.** La L10 sin `ubl:` estaba en la diapositiva 8 de las
novedades del 10-09-2026, como imagen, y aquí se escribió que era lo nuevo del
correo del 23-09-2026. `pdftotext` no saca las tablas en imagen. La diapositiva
6 trae otra tabla en imagen que tampoco se recogió (`SUPL`, `MINO`, `RETE`,
`IEDMT` y `OTROS`, sin `REEQ` ni `REGE`); que sea la L7 nueva es inferencia, y
no se ha tocado nada por ella.

**Lo que encontraron dos revisiones a la contra**, una del código y otra de lo
que el cambio afirma, antes de darlo por terminado:

- Con un calificador repetido, dos `RECT:TIPO`, se leía el primero y el resto
  desaparecía sin decirlo: un `R9` detrás de un `R1` no salía, y la nota daba
  el tipo por comprobado. Ahora se leen todos y la nota dice cuántos hay.
- La lista de lo que cambia de gravedad se quedaba en tres casos, y con el
  identificador del ejemplo se aplica el anexo entero (el README la da completa).
  Faltaba también el QR con espacios alrededor del identificador.
- Tres frases decían más de lo medido: que el anexo se aplica «solo» al CIUS, en
  el glosario y en el README; que un identificador desconocido de la AEAT sale
  «sin medir nada», cuando la forma y la norma europea sí se miden; y la frase
  de alcance de un lote, que con «dicen ser de la solución pública» abarcaba
  también al desconocido. `SPFE-SINTAXIS` decía «declara el CIUS» de un CII con
  el identificador del ejemplo, que según el propio ejemplo no sería un CIUS.
- Una prueba, la del namespace de las extensiones del ejemplo, pasaba sin probar
  nada: la factura no llevaba ni un elemento `aeat:`. Ahora lleva una extensión
  y se comprueba que se lee.
- La cita del 389 no era literal, y la fecha en que Jefe vio el correo no tenía
  fuente. Corregidas.

**Cómo se probó rompiéndolo.** Cada arreglo se deshizo, uno a uno, se corrió la
suite entera y se miró qué pruebas se ponían en rojo (sin contar la de la
versión de Python de GitHub, que en este contenedor falla siempre, ni la de la
cifra de pruebas del README, que fallaba en todas por haber pruebas nuevas):

| Se rompió | En rojo |
|---|---:|
| El identificador del ejemplo deja de ser de la solución pública | 9 |
| Sin versión, 2.5 solo con el CIUS de abril | 4 |
| L10 solo con el esquema del anexo, con `ubl:` | 16 |
| El QR y la autorización cuentan como datos de la rectificativa | 4 |
| El código se busca en la descripción | 12 |
| El código fuera de su lista no se avisa | 2 |
| El identificador desconocido de la AEAT se calla | 2 |
| El `ProfileID` del ejemplo vuelve a ser ERROR | 3 |
| El identificador del ejemplo es ERROR en `SPFE-ESPECIFICACION` | 3 |
| La frase de la sustitución sin importes no sale | 3 |
| De un calificador repetido solo se lee el primero | 3 |
| Una respuesta recibe el aviso del identificador desconocido | 1 |
| El calificador vale con cualquier prefijo de la AEAT, como antes | 1 |
| La S solo se mira en la primera modalidad | 1 |

Ninguna rotura pasó sin que la cazara una prueba.

**Lo que se dejó sin hacer, y por qué.**

- **La entrada de la bitácora** `rectificativas-sin-bg-es-1.html` dice que lo
  razonable sería la descripción, que el número de la autorización «hoy va en
  el identificador» y que Glosa «no comprueba lo que vale cada uno»; el ejemplo
  desmiente lo primero y lo segundo, y este cambio lo último. Es texto
  publicado y fechado, y
  si se corrige, o se le añade una entrada nueva, lo decide Jefe.
- **UBL-SR-43**, del esquematrón de sintaxis de CEN (2017, nivel fatal), solo
  admite 130, o 50 en un abono, en el `DocumentTypeCode` de un
  `AdditionalDocumentReference`, y el ejemplo pone `R1` y `S`. Aquí no se
  cargan las reglas de sintaxis de CEN. Queda por preguntar. Preguntado, y
  contestado el 13-10-2026: la solución pública se basa en la semántica de
  la EN 16931, que no impone esa restricción.
- **L7 sin `ubl:`**. Si las líneas de cobro pierden el `ubl:` como L10, Glosa
  daría ERROR falso: medido con `SUPL` sin `ubl:`. No se ha tocado porque nada
  publicado lo dice.
- **Los importes rectificados.** El ejemplo es una S y no los enseña, y
  `DocumentReference` no tiene ningún elemento de importe.

**Sin medir:** el navegador, como siempre que se toca el motor. Se ha medido en
CPython con lxml 6.1.2; en Pyodide va lxml 6.0.2.

## Lo visto en producción el 05-10-2026, y las tandas que lo cierran

Al comprobar en producción los PR #7 y #8 salieron once cosas por arreglar
(el informe está fuera del repositorio, en `informes/Infoerrores/`). Cuatro
pedían una decisión de Jefe, y el 05-10-2026 se tomaron las recomendadas:

1. La página promete la revocación **solo con la prueba que trae la factura**
   (la opción A). Dejar soltar un `.crl` junto a la factura (B) queda para
   cuando alguien lo pida.
2. Las listas que vienen dentro de la factura **no avisan de caducidad**, igual
   que ya no avisaban las respuestas OCSP. La fecha de hoy solo se aplica a
   las listas de la carpeta de revocaciones, en consola.
3. En «Tiene» va la cifra **tal cual está en el fichero**, con su punto: es lo
   que se busca en el XML. Lo calculado va con coma decimal. Los miles no
   tenían recomendación; se agrupan con punto a partir de cinco cifras, como
   ya hace la portada con `toLocaleString("es-ES")`.
4. Que el propio sitio baje la lista por quien valida (la variante E): no.

Las tandas, un commit cada una y en este orden:

| Tanda | Cosas | Qué |
|---|---|---|
| 1 | 1, 4 y el código de la 3 | La página deja de hablar de instalar, de carpetas y de órdenes de consola. La revocación se cuenta por documento |
| 2 | 2 | El redondeo que se contradice en BR-CO-10 |
| 3 | 5 y 10 | Las cifras del motor con coma, y los ejemplos de BR-DEC |
| 4 | 6, 7 y 9 | Tildes, fechas en dd-mm-aaaa y bytes con punto de miles |
| 5 | 11 | `XSD-ESQUEMA-ROTO` sin ruta, y una guardia que compile los esquemas |

Fuera de las tandas: la cosa 8 (una Facturae de 400 cifras tumba al
validador) se deja como está, porque reventar ahí es lo honrado y está
escrito en `sintaxis.py`. Y el paquete de anclas hay que volver a montarlo
**antes del 02-02-2027**, desde el equipo donde están las anclas.

### Tanda 1: la revocación en la página, y las anclas que no se instalan

**Reproducido** antes de tocar nada: el bloque `INFORME` de `glosa.js`, corrido
en CPython sobre el paquete descomprimido como lo descomprime la página, con la
raíz y la intermedia de `test_cadena` añadidas a las anclas. Cuatro casos: sin
prueba dentro, con una lista dentro anterior a la firma, con una posterior y
limpia, y con una posterior que lo anula. En los cuatro la página mandaba a
«bájala y ponla en la carpeta de revocaciones», o la columna de la firma decía
«hace falta la lista de revocación de su autoridad»; en el último, al lado del
`REVOCADO` que salía de esa misma lista. La frase hablaba de una «autoridad de
confianza instalada», y la lista anterior a la firma daba «la lista es del
2026-03-02 y la firma dice ser del 2026-03-02»: dos fechas iguales para decir
que una va antes que otra.

**Lo que se hizo.**

- **La página arma su almacén de listas sin carpeta**,
  `AlmacenDeListas.sin_carpeta()`. Sin carpeta, el aviso dice qué traía el
  documento y por qué no ha servido, y no manda a ninguna parte: «el documento
  no trae dentro la lista de revocación de la autoridad que emitió el
  certificado, ni una respuesta OCSP, y aquí no se sale a buscarlas». La lista
  anterior a la firma dice cuánto antes: «se publicó el 2026-03-02, 1 hora
  antes de la fecha de la firma».
- **La frase y la columna cuentan por documento**, como ya hacían con la
  cadena. Antes colgaban de «¿hay alguna lista en la carpeta?»: en la página
  nunca la hay, y en consola una lista de otra autoridad prometía la
  revocación de todo el lote. Ahora se promete cuando la cadena llega y
  ninguna firma lleva un aviso de `revocacion.SIN_CONTESTAR`, y la línea final
  de la consola, «no hay listas de revocación», sale solo si algún documento
  se quedó sin contestar.
- **La nota de «no consta anulado»** decía «ningún certificado de la cadena»
  con solo la lista de la raíz, al lado del aviso de que el que firma no se
  había mirado. Ahora dice «ninguno de los certificados que están por encima
  del que firma».
- **`REVOCACION-LISTA-VIEJA`, solo para las listas de la carpeta.** Las que
  trae el documento no avisan, como no avisaban las respuestas OCSP. Y al
  medirlo salió otra cosa: sin `--hoy` no se pasaba ninguna fecha, así que una
  lista de la carpeta vencida el 01-04-2026 daba «no consta anulado» sin decir
  nada. Ahora se mide con la fecha de hoy.
- **Las anclas, que en la página no se instalan.** `glosa.js` declara siempre
  la procedencia, también si el paquete no ha llegado; sin ella, la página sin
  paquete daba la carpeta del disco virtual donde «se instalan». Con
  procedencia, `CADENA-SIN-ANCLAS` dice que vienen con la página y que
  recargarla las vuelve a pedir, y `ANCLAS-SIN-RENOVAR` dice que las vuelve a
  montar quien mantiene la página, en vez de la orden de consola.
- **`ANCLAS-SIN-RENOVAR` decía que la cadena llega aunque no llegara.** Ahora
  tiene tres textos: llega, no llega («y puede ser por eso: una autoridad que
  el Estado haya añadido después no está entre estas anclas»), o no se ha
  verificado ninguna firma y no dice nada de la cadena. Y «hace un día» va en
  singular.
- **Fuera «instalada» y «almacén»** de los avisos de la cadena y del sello,
  de nueve entradas del glosario y de la portada: la ficha dice «Cadena, sello
  y revocación del firmante si trae la prueba», y la tabla y la pregunta
  frecuente ya no dicen «o la tienes instalada».

**Las pruebas.** En `test_revocacion.py`, la frase por documento (seis casos,
también en consola), el almacén sin carpeta (cinco), las listas de dentro que
no caducan (dos) y la nota que no promete por el firmante. En `test_cadena.py`,
cuatro sobre las anclas: en la página, con la cadena que no llega y el
singular. En `test_lo_que_ensena_la_pagina.py`, la revocación pasada por el `INFORME` de la
página con los tres casos, la portada, y una guardia que corre los ejemplos y
la página sin paquete y mira que nada de lo que vuelve diga «almacén»,
«instalad», «python -m», «--montar», «carpeta de revocaciones», «bájala» ni
«ponla en». La de `test_informe_por_partes.py` pierde la bandera de las
listas, que ya no existe: de ocho combinaciones a cuatro, y por eso la suite
baja de 2754 a 2737 aunque haya veintitrés pruebas nuevas.

**Provocado.** Dieciséis roturas, una a una, y cada una pone en rojo la prueba
que le toca: el aviso que da la dirección sin carpeta, el motivo de siempre
sin carpeta, la página sin almacén de listas, la frase que promete por lote,
las listas de dentro que caducan, el vencimiento sin `--hoy`, la nota que
promete por el firmante, la consola que echa de menos la carpeta aunque se
contestara, `CADENA-SIN-ANCLAS` con la carpeta en la página, `ANCLAS-SIN-RENOVAR`
que dice que llega, «hace 1 días», la orden de consola en la página, la página
sin procedencia cuando no hay paquete, la ficha con «si hay lista», la tabla
con «o la tienes instalada» y la lista anterior con las dos fechas.

**Lo que queda.** Un `.crl` soltado junto a la factura sigue saliendo como un
fichero que no se puede validar: dejar soltarlo es la opción B, y no se ha
hecho. Las fechas de los avisos van todavía en aaaa-mm-dd; eso es de la
tanda 4.

**Sin medir:** el navegador. Medido en CPython con lxml 6.1.2, corriendo el
mismo bloque de Python que la página; en Pyodide va lxml 6.0.2. Se verá en
producción después de fusionar.

### Tanda 2: «Debería ser» sale de la cuenta que decide el error

**Reproducido** con el constructor de `test_en16931.py`. Las reglas de la
cabecera comparan con `cuadra_exacto`, que redondea las mitades hacia arriba
como el esquematrón; el texto escribía la cifra con `:.2f`, que es el redondeo
de `Decimal` y las lleva al par. Con tres decimales acabados en 5, las dos
cuentas se separan un céntimo y el error se contradice:

| Caso | Salía | La regla comparó |
|---|---|---|
| línea de 100.125, suma 100.12 | BR-CO-10, «Debería ser: 100.12 · Tiene: 100.12» | 100.13 |
| 100.00 más 0.125 de cargos, base 100.12 | BR-CO-13, 100.12 y 100.12 | 100.13 |
| 21.005 de impuestos, total 121.00 | BR-CO-15, 121.00 y 121.00; BR-CO-14, 21.00 y 21.00 | 121.01 y 21.01 |
| 0.015 de anticipos, a pagar 120.98 | BR-CO-16, 120.98 y 120.98 | 120.99 |
| línea de -100.135, suma -100.14 | BR-CO-10, -100.14 y -100.14 | -100.13 |

Lo mismo en BR-CO-11 y BR-CO-12 (un descuento detallado de 10.005) y en la base
de cada tipo, BR-{X}-08 e `IVA-BASE-TOLERADA`, que además decía «se aparta
0.00» de una base de 100.00 contra una línea de 100.005.

**Lo que se hizo.** Cada regla escribe la cifra que comparó, `redondear(…)`, en
los diez sitios: seis en `en16931` (BR-CO-16 tiene dos ramas) y tres en `iva`,
más lo que se aparta en `IVA-BASE-TOLERADA`. BR-CO-17 ya lo hacía. Facturae no lo necesita: compara
con margen (`facturae._cuadra`), y dos cifras que se escriben igual caben
dentro de él.

**Provocado.** Diez roturas, quitando el `redondear` de cada sitio uno a uno, y
cada una pone en rojo su caso: once pruebas nuevas, nueve en `test_en16931.py`
y dos en `test_iva.py`.

**Lo que queda, para la tanda 3.** La cifra del fichero se sigue escribiendo
con `:.2f`, en «Tiene» y dentro del paréntesis que explica la cuenta. Así que
el caso de 21.005 dice «Debería ser: 21.01 · Tiene: 21.00», y el de los
cargos, «100.13 (100.00 + 0.12 de cargos)», que no suma. Es la decisión 3:
«Tiene» como está en el fichero.

### Tanda 3: las cifras con coma, y «Tiene» tal cual

**Lo que había.** Cada módulo escribía sus cifras con `:.2f` o con su propio
`_fmt`: unas 110 líneas entre `en16931`, `iva`, `facturae` y `copia_fiel`.
Con punto decimal, que en castellano se lee como miles («Debería ser: 90.00»,
«se aparta 0.50»), y redondeando también lo que copiaba del fichero: en
«Tiene» un 100 salía 100.00 y un 21.005 salía 21.00. En el glosario, «10.500 son tres
decimales» y «21.000 vale» se leían diez mil quinientos y veintiún mil, 37
veces en 19 fichas de BR-DEC.

**Lo que se hizo.** Un módulo nuevo, `validador/cifras.py`, con tres puertas
según de dónde sale la cifra, y una para los tipos:

- `calculada`: lo que calcula el validador. `100,13`, con coma, dos decimales
  y el redondeo de las reglas.
- `en_castellano`: una cifra del fichero dentro de una frase o de la cuenta
  que explica un «Debería ser». Sin redondear y con dos decimales como mínimo:
  «100,13 (100,00 + 0,125 de cargos)», que ahora suma.
- `tiene`: la cifra del fichero sola en «Tiene», tal cual, con su punto.
- `tipo`: 21% y 6,5%. De paso, `COPIA-CARGO-IVA` escribía el tipo con el texto
  del fichero y un espacio: «al 21.00 %».

Los miles con punto desde cinco cifras (12.345,67, y 1234,56 sin él), como
`toLocaleString("es-ES")` en la portada; en el glosario, 1.163,52 y 1.250 € pasan
a 1163,52 y 1250 €. Los ejemplos de BR-DEC van entre comillas invertidas, como
ya iba en el glosario lo escrito en el XML, y también los dos identificadores
de la solución pública. `facturae` tenía una variable local `cifras` que
habría tapado el módulo: se llama `cuantas`.

**Lo que se decidió sin preguntar, y por qué.** El informe recomendaba «Tiene»
tal cual y «entre «»». Va tal cual y **sin** las comillas: el resto de avisos
(la forma, BR-DEC, el anexo) ya ponían en «Tiene» el texto del fichero sin
ellas, y ponérselas solo a las cuentas dejaba dos maneras de escribir lo mismo.
Los miles desde cinco cifras no tenían recomendación; se eligió eso por ser lo
que ya hace la portada.

**Las pruebas.** `tests/test_cifras.py`, 29: las cuatro funciones; una guardia
que lee `validador/` y no deja una cifra con `:.2f` ni con un `fmt` propio
fuera de `cifras.py` (y de `sintaxis.py`, que define el `fmt` que ya no usa
nadie, y de los megas de `__main__`, escritos con su porqué); y otra que pasa
por el validador las muestras y facturas con las cuentas rotas de los cuatro
motores, con importes de tres decimales y de cinco cifras, y mira que ningún
mensaje ni «Debería ser» lleve un punto decimal. Exige además que sigan
saliendo once códigos de cuentas, para que un constructor que cambie no la deje
en verde sin mirar nada. En `test_glosario.py`, una que no deja una cifra con
punto fuera de comillas invertidas, salvo la versión 2.5 de SPFE-SINTAXIS,
escrita. Cambiaron 47 líneas de prueba que fijaban el punto en lo calculado.

**Provocado.** Trece roturas, una a una: la coma vuelve a ser punto, sin miles,
miles desde cuatro cifras, lo calculado con el redondeo de `Decimal`, la cuenta
del paréntesis redondeada, sin los dos decimales, «Tiene» redondeado, el tipo
con punto, un `:.2f` nuevo en `iva`, una cifra cruda en una frase de Facturae,
el tipo crudo en `COPIA-CARGO-IVA`, un ejemplo de BR-DEC sin comillas y un
1.163,52 en el glosario. Las trece en rojo; la última solo después de hacer
estrictas las dos guardias, que daban por buenos unos miles desde cuatro
cifras.

**Lo que queda.** En EDIFACT con la coma como marca decimal, «Tiene» sale con
punto: el árbol que se valida ya la trae cambiada (`edifact._valor`), y
guardarla tocaría la lectura, que está en `sintaxis.py`. Un «+» delante o unos
ceros a la izquierda tampoco se conservan, porque `Decimal` no los guarda. Y en
la descripción para buscadores de cada código las comillas invertidas se
quitan, así que allí `10.500` sigue sin ellas.

### Lo que se le escapó a la tanda 1: el banco buscaba las frases de antes

Al repasar los nombres del banco para la tanda 4 salió que la comprobación
«la promesa del informe cuadra con lo que hay instalado» buscaba en la frase
«necesita anclas de confianza instaladas» y «autoridad de confianza
instalada», las dos que la tanda 1 quitó. Con anclas pasaba en verde sin
mirar nada, porque las dos ausencias coincidían con lo esperado; sin anclas,
fallaba. La suite entera estaba en verde porque `test_banco.py` monta el banco
en un fixture de módulo, que se monta antes que el aislamiento por prueba de
`conftest.py` y veía las `anclas/` y los `esquemas/` de esta carpeta. En GitHub,
donde no los hay, habría salido en rojo al primer push.

Ahora el banco busca las frases nuevas, y el fixture apunta esquemas y anclas a
carpetas que no existen, como el resto de la suite. **Provocado:** con el
`prueba.py` de antes y el fixture nuevo, la comprobación sale en rojo, como en
GitHub; con las anclas de verdad, las 42 en verde.

### Tanda 4: tildes, fechas en dd-mm-aaaa y bytes con punto de miles

**Lo que había.** Si la página no arrancaba, quien la abría leía «No esta el
interprete en ./pyodide/. Traelo con `python -m validador --traer-pyodide`», o
«El validador (factura_e-0.1.0-py3-none-any.whl) no es lo que la pagina dice
traer: rueda.json publica...»: sin tildes, con rutas y huellas, y con una
orden que no puede dar. En el banco, 13 de las 42 comprobaciones llevaban el
nombre sin tildes, y 66 cadenas cambiaron en total; la ayuda de la consola,
igual. La ficha del paquete decía «Montadas el 2026-08-27», el informe
escribía así las fechas de sus frases, y el banco decía «1247225 bytes».

**Lo que se hizo.**

- `glosa.js` lanza los fallos con `averia(paraQuienMira, paraQuienMantiene)`.
  En pantalla, qué ha pasado y «Recarga la página; si sigue igual, el fallo es
  de la página y no de tu navegador.». En la consola del navegador, el detalle,
  que además viaja en `cause`. La portada y el banco enseñan `error.message`,
  sin el «Error:» que antepone `String`.
- Las cadenas del banco, de `glosa.js` y de la ayuda de la consola, con sus
  tildes. Una errata del glosario de paso: «código unico».
- `cifras.fecha` (06-08-2026) y `cifras.momento` (16-12-2015 a las 14:41:55
  UTC), y 50 fechas del informe y de los avisos de consola que pasan por ellas,
  en ocho módulos. En la portada y el banco, `Glosa.fecha`, una sola para las
  dos páginas, que pintan la misma ficha.
- `cifras.recuento` para los bytes del banco, y `toLocaleString("es-ES")` para
  los de `glosa.js`.

**Lo que se decidió sin preguntar, y por qué.**

- Se quedan en ISO, cada uno con su motivo escrito en `EN_ISO`: la fecha del
  fichero en «Tiene», que va tal cual como las cifras; `PAQUETE.json` y las
  líneas del manifiesto de las anclas, que son para máquina; y los
  inventarios de consola (`--ver-anclas`, `--ver-revocaciones`, `--ver-tsl`),
  que son columnas y en ISO se ordenan solas. Los avisos de consola que son
  frases sí cambian.
- La frase de procedencia lleva la fecha **escrita dentro del manifiesto** de
  las anclas, y ese manifiesto viaja en el paquete publicado. Montar de nuevo
  ya la escribe bien, pero el paquete de hoy no se monta hasta antes del
  02-02-2027, así que la fecha se pasa al leerla: en `Almacen.declarada` y en
  `Glosa.fecha`, que admite una frase con fechas dentro.
- El banco, sin paquete, decía «Para arreglarlo: python -m validador
  --empaquetar». Ahora dice que se recargue: la orden está en el README.
- La comprobación «la promesa del informe cuadra con lo que hay instalado» se
  llama ahora «... con los esquemas y las anclas que hay»: en la página no se
  instala nada, que es lo que quitó la tanda 1.
- En el README, «Las cifras» de la tanda 3 estaba metida en medio de otra
  sección y le dejaba los párrafos huérfanos. Se movió al final de esa sección.

**Las pruebas.** 63 nuevas. En `tests/test_voz.py`, una red de palabras que en
castellano no existen sin tilde («aqui», «pagina», «deberia», «ningun», las
acabadas en «-cion») sobre el texto de las seis páginas y los tres artículos de la bitácora, las
cadenas de `glosa.js` y del Python que lleva dentro, las del banco y las del
motor. Las que existen con y sin tilde («esta», «valida», «solo», «donde») se
quedan fuera a propósito: cambian de sentido, no de ortografía. En
`tests/test_fallos_de_la_pagina.py`, que ningún `new Error` llegue a la
pantalla sin pasar por `averia` (salvo dos, con su motivo), que lo que lee
quien mira pida recargar y no lleve rutas, huellas ni órdenes, y que el
detalle vaya a la consola. En `tests/test_cifras.py`, las tres funciones
nuevas, la procedencia vieja leída en dd-mm-aaaa, y una guardia que recorre
`validador/` con `ast` y no deja un `isoformat` ni un `strftime` fuera de las
funciones de `EN_ISO`: por función y no por línea, porque lo que decide si una
fecha es para leer o para máquina es para qué sirve lo que la escribe.

**Provocado.** Catorce roturas, una a una: una tilde menos en el banco, en
`glosa.js`, en la portada y en la ayuda de la consola; la orden de consola
otra vez en pantalla; un `new Error` sin avería; una avería sin recargar; el
detalle fuera de la consola; la portada con `String(error)`; una fecha del
informe con `isoformat`; la hora con `isoformat`; `cifras.fecha` en ISO; la
procedencia vieja sin pasar; y los bytes sin miles. Las catorce en rojo, pero
la de `glosa.js` **solo después de arreglar la guardia**: sacaba las cadenas
con una expresión regular, y `glosa.js` lleva `/href="([^"]+\.whl)"/g`, con
comillas dentro. Desde ahí cada cadena salía con el principio de la siguiente,
y una «pagina» sin tilde pasaba en verde. Ahora las saca un lector que salta
comentarios y expresiones regulares.

**Visto en el navegador**, con el sitio montado como en producción
(`--sitio --exigir-paquete`): las 42 del banco en verde, «son 1.247.225
bytes», «sello de TSU de prueba del 27-08-2026», «de una lista del
06-08-2026»; la ficha con «Montadas el 27-08-2026», «Se renuevan el
02-02-2027» y la procedencia en dd-mm-aaaa; y el informe de la muestra firmada
sin una sola fecha en ISO. Para ver un fallo, con la huella del validador
cambiada en `rueda.json`: la portada dice «No ha arrancado» y «El validador ha
llegado distinto de lo publicado, seguramente una copia vieja que guardaba el
navegador, y no se usa. Recarga la página; si sigue igual, el fallo es de la
página y no de tu navegador.»; el banco, lo mismo tras «No ha arrancado:»; y
la consola, «Glosa: dist/7182b289/factura_e-0.1.0-py3-none-any.whl: rueda.json
publica 000000000000... y lo que ha llegado resume 7182b289ad37...». Con
`rueda.json` devuelto, «Listo en 8,96 s».

El primer intento de provocarlo fue quitar `pyodide.js` del sitio, y la página
arrancó igual: el navegador lo tenía guardado. Es el disfraz de siempre, y por
eso se provocó por `rueda.json`, que es lo único que se pide siempre fresco.

**Lo que queda.** En «Tiene», la fecha de una factura CII saldría en ISO y no
como la escribe el fichero (`20260302`): `leer_fecha` la lee y `revisar` la
escribe con `isoformat`. Lo dice el código; con una factura no se ha visto.
Es la misma decisión que la coma de EDIFACT en la tanda 3, y se toca en la
lectura. En desarrollo, sin `--sitio`, el banco sigue fallando «el navegador
tiene orden de no pedir nada fuera», porque la política de contenido la pone
el montaje; es lo esperado.

### Tanda 5: un esquema que no compila no se publica

**Lo que había.** `XSD-ESQUEMA-ROTO` no salía con el paquete publicado, pero
si hubiera salido en la página habría enseñado la ruta del disco virtual del
navegador y «Suele ser una descarga a medias; vuelve a bajarlo», en una página
donde no se baja nada. **Reproducido** con el validador de antes (una copia de
HEAD aparte) y un `UBL-Invoice-2.1.xsd` cortado por la mitad en un catálogo
con la procedencia de la página: el campo era la ruta entera, y en «Tiene» iba
otra vez, con su `file:/` delante. Y nada impedía publicar un esquema así: al
empaquetar no se compilaba ninguno, y en el banco solo el de Facturae.

**Lo que se hizo.**

- `XSD-ESQUEMA-ROTO` hace lo que ya hacía `XSD-SIN-ESQUEMA`: con procedencia
  dice que el esquema está entre los que vienen con la página y no se puede
  leer, que es un fallo de la página y no de la factura y que recargar no lo
  arregla. En «Tiene», el motivo de libxml2 sin la carpeta delante, también en
  su forma `file:`. En consola, dónde está y que se vuelva a bajar.
- Los esquemas de entrada tienen nombre propio en `esquema.py`, `_DE_ENTRADA`:
  los que `_nombres_esperados` puede pedir. `Catalogo.los_que_no_compilan()`
  los compila todos.
- `--empaquetar` se niega con `EsquemaQueNoCompila` si alguno no compila.
- En el banco, una crítica nueva: «los esquemas de entrada compilan con este
  libxml2». La 43.

**Lo que se decidió sin preguntar, y por qué.**

- Las negativas de `--empaquetar` eran dos y `__main__` las cazaba por su
  nombre, que es la lista escrita a mano que ya se quedó atrás una vez con
  `--sitio`. La tercera hacía falta añadirla a esa lista. En vez de eso se les
  puso raíz, `NoSeEmpaqueta`, y la prueba que recorre `paquete.py` exige ahora
  que toda excepción cuelgue de `NoSeMonta` o de `NoSeEmpaqueta`. Va escrito
  también en CLAUDE.md, al lado de `NoSeMonta`.
- Se compilan solo los de entrada: un fichero que no importa nadie no rompe
  ninguna factura. Uno roto que sí importa un esquema de entrada rompe a ese,
  y se dice por el de entrada, que es el que falla en la página.

**Las pruebas.** Ocho nuevas: el aviso en la página sin rutas ni «bajar», y
en consola con ellas; que todo lo que pide `_nombres_esperados` (UBL de la 2.0
a la 2.5 y una desconocida, facturas, abonos y respuestas; CII; Facturae de la
3.0 a la 3.2.2) es de entrada, y que lo que importan no; que se compilan todos
y se dicen los rotos; la negativa, que no la provoca un fichero suelto, y la
orden saliendo con 2.

**Provocado.** Siete roturas, las siete en rojo: el aviso de la página otra vez
con «vuelve a bajarlo», la ruta otra vez en «Tiene», empaquetar sin compilar,
`__main__` cazando por nombre, `SinRenovar` sin raíz, las respuestas fuera de
los de entrada, y `los_que_no_compilan` sin compilar de verdad. Y dos de punta
a punta, con el paquete descomprimido y `UBL-Invoice-2.5.xsd` cortado: el banco
en Python da 42 de 43, con la nueva en rojo y el motivo de libxml2; y
`--empaquetar` de verdad se niega con salida 2, nombra el fichero y no deja
zip.

**Visto en el navegador**, con el sitio montado: las 43 en verde, y la nueva
dice «los 11 compilan con libxml2 2.9.10» en 1,85 s. Aquí compilan en un
segundo con la 2.11.9. Los 43 resultados son los mismos que en Python nativo
con el mismo paquete: solo cambian las versiones, los tiempos, la barra de una
ruta y las tres que solo pueden medirse en el navegador. Lo que no se ha visto
en el navegador es el aviso nuevo: hacerlo salir allí pide un paquete con un
esquema roto y su huella publicada, y `--empaquetar` ya no lo arma. Lo cubre
la prueba que monta el catálogo como lo monta la página.

**Lo que vio GitHub y aquí no.** Publicada la tanda, la suite de GitHub salió
en rojo en una prueba: pedía que «Tiene» dijera `ubl/UBL-Invoice-2.1.xsd`, que
es como lo escribe la libxml2 de Windows, y en Linux libxml2 pone solo el
nombre del fichero. El código estaba bien (en ninguno de los dos sale la
carpeta); la prueba pedía la forma de una máquina. Ahora pide el nombre, y que
la carpeta no esté.

## El gancho de git no corría en Linux

**Lo que había.** `.githooks/pre-push` estaba en el índice como `100644`, sin
permiso de ejecución. En Windows no se notaba: Git for Windows no mira ese
permiso (`core.fileMode` falso) y llama al gancho igual. En Linux y en macOS,
git se lo salta, deja una pista y sigue.

**Reproducido** el 07-10-2026 en una copia recién clonada en Linux, la de una
sesión de Claude Code en la nube, con `core.hooksPath` puesto en `.githooks` y
un fichero sin commit:

```
hint: The '.githooks/pre-push' hook was ignored because it's not set as executable.
```

El push a un repositorio desnudo de usar y tirar no lo paró el gancho. Falló
por otra cosa (la copia es superficial y el desnudo no acepta eso), así que
salió en rojo y no por lo que se creía. Es el disfraz de siempre: la
comprobación de `CLAUDE.md`, hecha al pie de la letra, no habría distinguido
una cosa de la otra. Hay que leer el motivo, no solo el código de salida.

**Lo que se hizo.** `git update-index --chmod=+x .githooks/pre-push`, y una
prueba en `tests/test_ganchos.py` que lee el modo del **índice** y se niega si
no es `100755`. El índice y no el disco: el permiso que viaja con el
repositorio es el del índice, y en Windows el disco no lo tiene nunca, así que
la prueba vale en las dos máquinas.

**Provocado.** La prueba, escrita antes del arreglo, en rojo con `100644`; en
verde con `100755`; y en rojo otra vez quitándole el permiso en el índice. Y el
gancho de verdad, con el permiso puesto y el mismo fichero sin commit: se negó
en 0,1 s con «Hay cambios sin guardar en un commit».

**Lo que cambia en Linux, y se decidió sin preguntar.** Con el gancho ya
ejecutable, una copia en Linux sin `.venv/Scripts/python.exe` se niega a
empujar con «No se empuja: no está el entorno que corre las pruebas». Es cerrar
con palabras, que es lo que se quiere. En la sesión de la nube se montó el
`.venv` con Python 3.14.6 y las versiones de `requisitos-pruebas.txt`, y un
enlace `Scripts` → `bin` para que el gancho lo encuentre. No se ha tocado la
ruta que busca el gancho: la copia principal es la de Windows, y enseñarle a
buscar también `.venv/bin/python` es otro cambio, para cuando haga falta.

## La orden salió en el BOE y Glosa daba por mala una factura hecha como dice

**Lo que había.** La Orden HAC/1028/2026 se publicó en el BOE del 05-10-2026
(BOE-A-2026-20587) y entró en vigor el 06-10-2026. Su anexo I no es el
borrador de abril con el que se escribieron las reglas `SPFE-`: cambia la
cardinalidad de campos, los valores fijos, las listas y los sitios. La nota
`SPFE-BORRADOR` de cada factura seguía diciendo que el anexo «no está
publicado en el BOE», y la etiqueta del informe, «Anexo I (borrador)».

**Reproducido** el 07-10-2026 sobre `cc0a935`, desde una sesión en la nube,
con el XML del BOE bajado ese día (249.350 bytes, SHA-256
`14bb2dad06a5ce3278c395232db9185f18052b08602cae472a9b2af3ae9c354a`) y
extraído a tablas con un guion de cuarenta líneas. Una factura escrita al pie
de la letra del anexo publicado —el proceso de la orden, sin indicador de
copia, el vendedor en `BT-32` con «LOC» y «FC» y en `BT-30`, un anticipo
pagado y la retención con el calificador de L7—, por el validador entero:

| Código | Gravedad | Lo que decía | Lo que dice la orden |
|---|---|---|---|
| `SPFE-PROCESO` | ERROR | esperaba `urn:aeat:names:specification:ubl:schema:B2B` | BT-23: `urn:aeat:names:specification:ubl:schema:profile:B2B` |
| `SPFE-COPIA` | ERROR | falta el indicador | BT-ES-1, `0..1`: «False (o sin informar): original» |
| `SPFE-IMPORTE-PAGADO` | ERROR | esperaba 0, había 20,00 | BT-113 ya no dice «solo puede ser 0» |
| `SPFE-NIF` | ERROR | el NIF «con el impuesto LOC» | BT-32: «LOC» y `@schemeID` «FC» |
| `SPFE-LINEA-DE-COBRO` | ERROR | `urn:aeat:names:specification:schema:add:RETE` no es de L7 | L7: `RETE`, con el calificador `urn:aeat:names:specification:schema:add:` |
| `SPFE-RETENCION` | ERROR | falta la línea que identifica la retención | la línea estaba; la ruta de abril llevaba la URN de abril dentro |

Son los seis que nombraba el plan del 06-10. Con variantes salieron más: el
tercero escrito como la orden —nombre en `cac:PartyLegalEntity`, NIF con
«LOC»— daba `SPFE-TERCERO`; el comprador en `BT-47`, `SPFE-NIF`; el QR sin
descripción (`BT-123`, `0..1` en la orden), `SPFE-QR`; la clave de régimen
con el calificador de L8 delante, `SPFE-CLAVE-DE-REGIMEN`; y una línea y un
desglose en la categoría `N` de la L4 de la orden, `BR-CL-17` y `BR-CL-18` en
ERROR más `IVA-CATEGORIA-RARA` e `IVA-TIPO` en AVISO («5,2% no es un tipo de
IVA vigente en España», que es el del recargo de equivalencia).

**Lo que se hizo.** Dejar de condenar lo que la orden admite, y nada más:

- `SPFE-PROCESO` acepta el de la orden; el del ejemplo del 02-10-2026 sigue en
  NOTA, que ahora dice que la orden fija otro, y el ERROR pide el de la orden.
- `SPFE-ESPECIFICACION` deja de anotar el identificador del ejemplo, que es
  letra a letra el de la fila BT-24; su ERROR pide ese.
- `SPFE-COPIA` e `SPFE-IMPORTE-PAGADO` pasan a NOTA: lo que la orden supone
  sin indicador (el original, y una copia fiel tiene que decirlo), y lo que
  prohíbe y no se ve (un anticipo con el IVA devengado).
- `SPFE-NIF` y `SPFE-TERCERO` aceptan «VAT» o «LOC» con «FC»; el tercero, el
  nombre en la razón social.
- `_cobro` reconoce una línea de cobro por su valor de L7: la URN de abril
  entera, o un valor de la L7 de la orden con su calificador o sin él.
  `SPFE-LINEA-DE-COBRO` y `SPFE-RETENCION` lo usan, y las retenciones
  repetidas se cuentan por valor, no por cómo se escriben.
- `SPFE-QR` ya no pide la descripción; la dirección, sí.
- `_propiedades` busca la clave de régimen y la referencia catastral por su
  nombre de L8, con el calificador de la orden o sin él.
- La `N`, la `D` y la `F`: `factura` pasa a `en16931` las categorías de la L4
  de la orden que la lista de 2017 no tiene, calculadas restando, solo cuando
  la factura declara la solución pública. `BR-CL-17` y `BR-CL-18` las cuentan
  como buenas y los dos avisos de IVA no las miran. `SPFE-CATEGORIA` lo dice
  en una NOTA, con lo que no se ha comprobado.
- `SPFE-BORRADOR`, la etiqueta («Anexo I»), la frase de alcance, el glosario,
  el aviso legal (con su fecha) y la portada dicen lo que es verdad hoy: la
  orden publicada, medida todavía en parte con el borrador de abril.

**Lo que se decidió sin preguntar, y por qué.**

- **Las dos lecturas de los calificadores de L7 y L8.** La orden da el valor
  en la fila y el calificador aparte, sin decir cómo se juntan. Se aceptan el
  calificador delante —como escribió la AEAT los de L10 en su ejemplo— y el
  valor solo, que es lo que dice la fila. Lo que no es de ninguna de las dos
  (un `REEQ` con el calificador de la orden, un `XRETE`, un `IEDMT` con la URN
  de abril) sigue siendo ERROR.
- **La lista ancha, y no `_SOBRA_SI`.** `_SOBRA_SI` apaga un código entero si
  sale otro. Con él, una `X` inválida en otra línea de una factura con `N` se
  habría callado. Ensanchando la lista, la `X` sigue saliendo, y sola.
- **La `N` solo con la solución pública.** Qué lista rige para quien declara
  la edición de 2026 sin declarar la solución pública es decisión del titular.
  Hasta entonces, esa factura se mide como siempre.
- **Las constantes de la orden, a mano y juntas**, porque `cius_es` sale del
  PDF de abril. La guarda de L10, que ya se negaba a importar el módulo el día
  que el anexo trajera L10, nombra ahora también esas constantes: la tabla del
  BOE trae L10.
- **La etiqueta sin versión.** «Orden HAC/1028/2026» sería falso mientras haya
  reglas que solo existen en el borrador, como el recargo de equivalencia.

**Las pruebas.** Una factura escrita como la orden y ocho variantes, que
tienen que pasar el validador entero sin un ERROR ni un AVISO; las notas que
dicen qué se aceptó; y las roturas que prueban que lo que la orden prohíbe
sigue saliendo: «LOC» sin «FC», cinco identificadores de línea de cobro que no
son de ninguna L7, dos retenciones escritas distinto, la orden sin la suma de
retenciones, el tercero sin nombre o sin «FC», tres parecidos de `REGI`, la
`K`, una `X` junto a la `N`, y la `N` sin declarar la solución pública. Contra
el código de antes, 14 de las 19 primeras salían en rojo; las otras cinco son
de las que tienen que pasar en los dos.

**Provocado.** Veintidós roturas, una por arreglo, las veintidós en rojo: cada
forma de la orden dejando de aceptarse, cada NOTA volviendo a ERROR, la L7
aceptando cualquier cosa que acabe en el valor o aceptando `REEQ`, las
retenciones contadas por cómo se escriben, la nota diciendo otra vez que no
está publicado, la lista ancha sin llegar a `BR-CL-17` o a los avisos de IVA,
las categorías de la orden dadas a cualquier factura, y la `K` callada al
estar la `N`.

**Lo que no se hizo, a propósito.** Rechazar lo que la orden ya no admite —las
claves 18, 19 y 20 de L3A, las líneas `REEQ` y `REGE`, el proceso y la
especificación de abril— y medir sus reglas nuevas. Las dos cosas piden
regenerar `cius_es` desde el XML del BOE, y van en la tanda siguiente.

### El repaso, regla por regla contra el texto

Con los arreglos de arriba hechos, cuatro análisis por separado —la cabecera y
los textos, las partes y las líneas, el IVA y las categorías, los cobros y el
BG-24— leyeron cada regla contra las filas del BOE, con la consigna de
reproducir cada hallazgo con una factura que cumpla la orden. Salieron 59. De
los del paso 1 que no estaban ya arreglados, estos eran veredictos falsos, y
los tres se reprodujeron otra vez antes de tocar nada:

- **`IVA-BASE` con la `N`**, en ERROR. En el grupo de entidades de nivel
  avanzado la orden pone en la línea la contraprestación entera (BT-131) y en
  el desglose la base a coste (BT-116): con 150 y 100, «esperado 150,00».
  Y el recargo de equivalencia, escrito como la orden —una entrada N al 5,2%
  en el desglose, sin línea, porque una línea solo tiene un tipo—, salía como
  «base fantasma». La base de N, D y F ya no se compara con las líneas en las
  facturas de la solución pública; en la D y la F, porque puede ser el margen y
  la orden no lo aclara. `BR-CO-17` sigue atando la cuota a su base y su tipo,
  y hay prueba de que una cuota mala del recargo sigue saliendo.
- **`BR-AE-02` con el comprador en `BT-47`**, en ERROR. La orden pone `BT-47`
  en un `cac:PartyTaxScheme` con «LOC» y «FC»; la regla lo buscaba en
  `cac:PartyLegalEntity`, que es donde lo pone la vinculación de 2017. En las
  facturas de la solución pública cuenta también el sitio de la orden, por el
  mismo canal que las categorías (`solucion_publica.bt47_de_la_orden`). Fuera
  de ellas, y con «LOC» sin «FC», sigue saliendo.
- **El calificador de L10 a secas** —`QR`, `AUT`, `RECT:TIPO`— no se
  reconocía: un QR así no se miraba, y una 384 así salía con una nota de «un
  BG-24 sin leer». Se aceptan las dos lecturas, como en L7 y L8.

Y frases que hoy eran falsas en lo que se lee: la rectificativa en BG-24
(cinco que decían que el anexo nuevo «no está publicado»), el 381 (mandaba a la
extensión de abril), el identificador de la AEAT que no es ninguno (llamaba
«del ejemplo» al de la orden), el total a pagar (la L7 de abril), el recargo y
el grupo de entidades (como si la orden los pidiera), los identificadores de
abril en los mensajes (`BT-ES-32` a `BT-ES-39`, `BT-ES-43`, `BT-ES-44`, que en
la orden son otros campos o no existen), `NO_SE_COMPRUEBA` (decía que la
vinculación UBL de 2026 no está publicada: lo está, como UNE-CEN/TS
16931-3-2:2026, y lo que pasa es que aquí no se ha podido leer), la ficha de la
familia `SPFE` y siete entradas más del glosario. Y fuera de `solucion_publica`:
`copia_fiel` decía que en la copia el recargo va fuera de la cuota de IVA, que
con la orden es al revés; el README, en una docena de sitios; y tres artículos
de la bitácora, que se corrigen con un aviso fechado, como el que ya tenía el
de EDIFACT, y no reescribiéndolos.

**Un código que se retira: `COPIA-CUOTA`.** Decía que en la copia fiel la
cuota de IVA (`BT-110`) va sin el recargo de equivalencia, porque el borrador
de abril le daba un grupo propio. Con la orden el recargo va en el desglose del
IVA y `BR-CO-14` lo suma a la cuota, así que la cuota de la copia es el
`TotalTaxOutputs` de Facturae tal cual y la nota no tiene nada que decir. Se
quita la regla y su entrada del glosario, que la prueba de explicaciones
sobrantes no deja dejar, y con ella su página de código: los códigos
publicados pasan de 390 a 389, y la portada y la tesis lo dicen. `COPIA-TOTAL`
sale ahora solo con retenciones y suma el recargo (con base 100, IVA 21,
recargo 5,20 y retención 15, el total de la copia es 126,20). Contra el
`copia_fiel.py` de antes, las 9 pruebas que lo fijan —7 nuevas y 2 que ya
estaban, reescritas— salen en rojo.

**Provocado otra vez.** Ocho roturas más, una por arreglo de esta vuelta: la
base de la `N` comparada otra vez con las líneas, el `BT-47` de la orden sin
llegar a `BR-AE-02` por dos caminos, dado a cualquier factura o sin «FC», la
L10 a secas sin reconocer, y la rectificativa y el total a pagar con sus
frases de antes. Con las de arriba, treinta, y las treinta en rojo (corridas
sobre una copia del árbol, para no cambiarle los ficheros a nadie a mitad).

**Las fechas de obligación, leídas y no supuestas.** Hasta hoy el README daba
el 01-10-2027 y el 01-10-2028, del proyecto de abril. La disposición final
cuarta del RD 238/2026, leída en el XML del BOE (BOE-A-2026-7295), cuenta los
plazos «desde la entrada en vigor de la orden ministerial prevista en el
apartado 1 de la disposición final tercera»: doce meses para quien facturó más
de 8 M€, veinticuatro para el resto. Con la orden en vigor el 06-10-2026, el
06-10-2027 y el 06-10-2028, contados de fecha a fecha.

**Lo que se dejó, y por qué.**

- **`BR-G-02`** con el vendedor solo en `BT-32`: la exportación pide en la
  norma el identificador de IVA del vendedor (`BT-31`), y la orden deja elegir
  entre `BT-31` y `BT-32` sin excepción por categoría. Pero el anexo es un
  mínimo, el artículo 3.1 exige ajustarse a la EN 16931, y nada en la orden
  deroga esa regla. El ERROR es de la norma y se queda.
- **La `B` en `IVA-CATEGORIA-RARA`**: el aviso dice que no es una categoría de
  la norma, y lo es (está en UNCL 5305 y tiene `BR-B-01` y `BR-B-02`). No viene
  de la orden, que no la trae, y no es de esta tanda. Queda apuntado.
- **La ruta de `BT-ES-5` en la orden** (`…/cac:ServiceProviderParty/cac:Party/
  cbc:ServiceTypeCode`) no es UBL válido, y **las de `BG-ES-2`** llevan
  `cac:Invoice` dentro de la factura y `TaxSubTotal` con mayúscula. Hoy no las
  lee ninguna regla; son de la tanda que regenera la tabla, que tendrá que
  arreglarlas a la vista y con su porqué, como ya se hace con las de abril.

### La revisión antes de publicar: cuatro fallos, siete huecos y seis que se quedan

Antes de empujar, tres miradas sobre el cambio entero, cada una con la consigna
de reproducir lo que encontrara con una factura y un guion: que el código haga
lo que dice, que no acepte de más, y que las pruebas lo fijen. Cada hallazgo lo
verificó después otra mirada, que intentó tumbarlo. Aparte, el revisor de
promesas leyó lo que Glosa afirma contra lo que hace.

**Los cuatro fallos, reproducidos y con su prueba en rojo antes de tocar
nada:**

- **`BR-AE-02` en la factura sin desglose.** La rama de `BR-CO-18` llamaba a
  `_regla_identificadores` sin el `BT-47` de la orden. La factura AE con el
  comprador como dice la orden, sin su `cac:TaxTotal`, salía con `BR-AE-02`
  («ninguno · línea 1») además de con `BR-CO-18`; con el desglose, o con el
  comprador en `BT-48`, no.
- **«LOC» y «FC» con espacios.** `_nif_bien_puesto` los lee con `_valor`, que
  recorta, y el `BT-47` de la orden se buscaba con el texto exacto. Con
  `schemeID="FC "`, con «LOC » o con «LOC» entre saltos de línea, `SPFE-NIF`
  daba el NIF por bien puesto y `BR-AE-02` al comprador por no identificado.
  Ahora el XPath usa `normalize-space`, como la vinculación de 2017 con el
  «VAT» de `BT-48`; «loc» en minúscula sigue sin valer en las dos.
- **El abono.** Un abono es UBL y puede declarar la solución pública, y
  recibía la L4 de la orden: la `N` pasaba sin `BR-CL-17`, `BR-CL-18` ni los
  avisos de IVA, y sin la nota `SPFE-CATEGORIA`, porque `reglas` se para en el
  abono antes de llegar a ella. Ahora las dos funciones que ensanchan la norma
  miran también que la raíz sea `Invoice` (`_se_mide_con_el_anexo`).
- **«N (categoría no reconocida)».** Con la cuota del recargo mal,
  `BR-CO-17` la nombraba así en el mismo informe en que `SPFE-CATEGORIA` decía
  que la orden la admite. Los nombres de la N, la D y la F van en un
  diccionario aparte (`iva.CATEGORIAS_DE_LA_ORDEN`): `CATEGORIAS` es la lista
  de la norma y da el «Las admitidas son…» de `IVA-CATEGORIA-RARA`.

**Los siete huecos.** Cosas que el cambio hacía y que se podían deshacer con
la suite entera en verde, cada una comprobada rompiéndola: la `D` y la `F`
(con la L4 reducida a la `N`, las dos volvían a `BR-CL-17` y `BR-CL-18`); los
calificadores de L10 a secas que no son el QR (dejando solo el QR, una 384 con
`AUT` a secas bajaba de ERROR a NOTA); dos mensajes de la rectificativa que
ninguna prueba alcanzaba y que podían volver a decir «no está publicado»; la
etiqueta, que la prueba comparaba con la misma constante que debía fijar; el
filtro de «LOC» del `BT-47`, que solo se probaba quitando el «FC»; la `RCAT`
con calificador; y la fila del adjunto en la copia fiel, que podía volver a
«llega, pero el anexo no lo pide».

**Las promesas.** La nota `SPFE-BORRADOR` decía «lo que el borrador daba por
malo», y la N, la D y la F las condenaban reglas de la norma, no del borrador;
decía «el NIF con «LOC»» sin la excepción de la exportación (`BR-G-02` sigue);
callaba el `BT-47` y que la base de N, D y F no se compara; y su lista estaba
escrita dos veces y ya no decía lo mismo, porque el glosario se había dejado
la clave de régimen. Ahora es una sola tupla, el glosario la copia letra a
letra, y cada frase tiene sus facturas en una prueba que se niega si sale una
frase sin factura. La línea de alcance decía «lo que el anexo pide… (medido en
parte con el borrador)», y salían «sin errores» facturas que incumplen la
orden en cosas que en UBL sí se ven —la clave 18, el proceso de abril, un QR
con la descripción equivocada—: ahora dice «parte de», y cuál. La ficha de la
familia `SPFE` le atribuía a la orden, en `SPFE-RECARGO-DE-EQUIVALENCIA`, una
queja que solo existe en el borrador. Y la portada (el panel, la pregunta y el
pie) y la política decían que se comprueba el anexo de la orden sin el «en
buena parte». La política cambia de huella; la fecha ya era la de hoy.

**Lo que se propuso y se queda.** Seis cosas que la mirada de las
aceptaciones dio por aceptadas de más; la verificación las tumbó todas, y el
README cuenta el porqué de cada una. La que pesa: volver a atar la base de la
`N` sin líneas a la de otra entrada rompía una factura legítima —el recargo
solo grava los bienes, y 80 de mercancía con 20 de servicio dan una `N` con
base 80 junto a una `S` con base 100—, y se comprobó con el parche propuesto
puesto en una copia.

**Provocado.** Una rotura por cada arreglo y por cada hueco, sobre una copia
del árbol: con las treinta de antes, cuarenta y tres. Y ocho más para las
promesas —una frase de la nota sin su factura, el glosario sin la clave de
régimen, el «no siempre», el alcance, la ficha de la familia, el pie de la
portada, la nota de categoría y la política cambiada sin cambiar de huella—:
cincuenta y una, y las cincuenta y una en rojo. El guion de las roturas ahora
se niega a empezar si la base no está en verde: con una prueba ya roja y `-x`,
cada rotura saldría roja por la que ya fallaba, y diría que todo está
provocado sin haber provocado nada.

## Cuatro sitios seguían diciendo que la orden no estaba publicada

**Lo que había.** El 07-10-2026 la nota `SPFE-BORRADOR` dejó de decir que la
orden no estaba publicada, y con ella las frases que vio la revisión. Quedaron
otras. El 11-10-2026, al guardar en el README la consulta al buzón,
se vio que la cabecera de `codigo_unico.py` seguía diciendo que «la Orden
Ministerial técnica del RD 238/2026 aún no se ha publicado». La ficha de
`CU-03` decía lo mismo con «todavía», y esa se publica en la página.

**Reproducido** con una prueba nueva antes de tocar nada:
`test_el_validador_no_dice_que_la_orden_este_por_publicar`, en
`tests/test_documentacion.py`. Lee cada módulo de `validador/` con `tokenize`
—cadenas y comentarios juntos, partidos en frases— y se niega si una frase dice
que algo no se ha publicado y a la vez nombra la orden. En rojo encontró
**cuatro** sitios, no dos:

- la cabecera de `codigo_unico.py`;
- la ficha de `CU-03` en `glosario.py`, con la frase partida en dos cadenas:
  «todavía» al final de una y «no se ha publicado» en la siguiente;
- la cabecera de la tabla de abril, `cius_es.py`: «No está publicado en el BOE,
  la orden tampoco»;
- una frase de la historia de `solucion_publica.py` escrita en presente: «El
  texto nuevo no está publicado».

Un `grep` el mismo día vio solo las dos primeras. Las otras dos dicen «no está
publicado», y en la consola de la nube, sin configuración regional, `[aá]` no
casa con la «á»: son dos bytes y el corchete cuenta uno. Medido: la misma orden
con `LC_ALL=C.UTF-8` sí la encuentra. Y la de `CU-03`, partida en dos cadenas,
no sale buscando «todavía no se ha publicado» entero. Por eso la prueba lee con
Python y no con una expresión sobre el fichero.

**Lo que se hizo.** Las cuatro dicen ahora lo que hay. La orden salió en el
BOE el 05-10-2026 y no fija ningún tope: su anexo I describe `BT-1` sin
longitud, y su artículo 6 remite el formato del código único a ese anexo, que
no lo trae. Por eso el tope de 60 caracteres sigue tomado de Verifactu, y se
dice de dónde sale y que se ha preguntado al buzón. La cabecera de la tabla de
abril se cambió también en `herramientas/anexo_i.py`, que es quien la escribe:
si no, la próxima vez que se generara volvería la frase vieja.

**Provocado.** Cada uno de los cuatro arreglos, deshecho de uno en uno sobre
el árbol: los cuatro en rojo. El guion se niega a empezar si la prueba no está
en verde con todo puesto.

## El revisor de promesas no se cargó nunca

**Lo que había.** `.claude/agents/revisor-de-promesas.md` existe desde el
26-09-2026 y ninguna sesión lo ha tenido disponible. Su `description` llevaba
un «: » sin comillas («cuando un cambio toque una de ellas: la política…»), y
en YAML eso abre un mapa dentro de otro. Claude Code no lo dice en la sesión:
salta el fichero y lo apunta solo en el registro de `--debug`.

**Reproducido** el 11-10-2026: `claude plugin validate .claude/agents` dio
«YAML frontmatter failed to parse … At runtime this agent does not load at
all», con salida 1. Y no estaba en la lista de agentes de esta sesión.

**Lo que se hizo.**

- La `description`, entre comillas dobles. `validate` pasa con salida 0.
- Dos agentes nuevos, que dejan escrito lo que hasta ahora se repetía en cada
  encargo. `auditor` (opus) intenta tumbar la tesis, exige reproducir antes de
  afirmar y anota aparte lo que la refuerza. `localizador` (haiku) devuelve
  `fichero:línea` o la URL con la cita literal, y nada más: el abanico localiza
  y no concluye. Sin `model` en la llamada, Explore corre en el modelo de la
  sesión, Opus 5.5 a 4 $/20 $ el millón; Haiku 5.5 cuesta 0,10 $/0,50 $.
- `tests/test_agentes.py`: una comprobación más estricta que YAML, que corre
  también en GitHub, y `claude plugin validate` donde Claude Code está
  instalado.

**Provocado.** Con la cabecera del 26-09 en su sitio, la prueba sale en rojo y
nombra la línea 3. `validate` rechaza la cabecera rota de ejemplo (salida 1)
antes de dar por buenas las de verdad. Cuatro cabeceras rotas (los dos puntos,
la cabecera tarde, sin `name`, un `model` raro) salen en rojo cada una por su
motivo.

**Visto en la sesión.** Según la documentación, Claude Code vigila
`.claude/agents/` y recoge un fichero nuevo en segundos. En la sesión del
escritorio no fue así: dentro del mismo turno, `localizador` seguía sin existir
minutos después («Agent type 'localizador' not found»). Los tres aparecieron
al empezar el turno siguiente del titular, `revisor-de-promesas` incluido, por
primera vez. Un agente nuevo, por tanto, se puede usar desde el turno
siguiente, no desde el mismo.

## Las reglas, al texto de la orden

**Lo que había.** Desde el 07-10-2026 las reglas `SPFE-` dejaban de condenar
lo que la orden admite, pero seguían midiendo el borrador de abril: la tabla
`cius_es` salía del PDF de abril, el identificador de especificación que se
pedía era el de abril, y lo que la orden quitó se seguía aceptando. La nota
`SPFE-BORRADOR` lo decía en cada factura.

**Reproducido** el 11-10-2026 sobre `5d4f135`: once facturas escritas a partir
de la de la orden, por el validador entero, en un worktree de `HEAD` y en la
copia de trabajo ya cambiada.

| Factura | En `5d4f135` | Ahora |
|---|---|---|
| la de la orden | sin errores | sin errores |
| escrita con el borrador: su identificador, su proceso, la URN de abril en la retención y en el QR, y la clave 18 | **sin errores** | cinco ERROR: `ESPECIFICACION`, `PROCESO`, `LINEA-DE-COBRO`, `RETENCION` y `CLAVE-DE-REGIMEN` |
| la clave 18 del IVA | **sin errores** | `CLAVE-DE-REGIMEN` |
| una línea `REEQ` con la URN de abril | `RECARGO-DE-EQUIVALENCIA` | `LINEA-DE-COBRO`, que dice que era del borrador |
| una 384 con el tipo `R9` | AVISO | ERROR |
| la rectificativa de la orden, bien escrita | NOTA | nada |
| el QR con la descripción «VeriFactu» | **sin errores** | `QR` |
| el nombre del tercero en `cac:PartyName`, delante de `cac:PartyTaxScheme` (medido otra vez en la revisión: la primera vez iba detrás y salía `XSD-ORDEN`) | **sin errores** | `TERCERO` |
| el QR con la URN de abril y sin dirección | `QR` | nada: no es el QR de la orden |

**Lo que se hizo.**

- `cius_es` se regenera del XML del BOE (`anexos/orden-hac-1028-2026.xml`,
  SHA-256 `14bb2dad06a5ce3278c395232db9185f18052b08602cae472a9b2af3ae9c354a`)
  con `herramientas/anexo_i.py`: 176 filas, 149 identificadores, 39 grupos y
  14 listas. La prueba vuelve a extraer el XML y compara la tabla entera.
- El identificador de especificación se da la vuelta: vale el de la orden, y
  el de abril es ERROR con un mensaje que dice de dónde sale. `formato`
  reconoce los dos, para medirlos.
- Fuera `SPFE-RECARGO-DE-EQUIVALENCIA` y `SPFE-GRUPO-DE-ENTIDADES`: la orden
  pone los dos regímenes en el desglose del IVA, con la categoría N. Las
  líneas `REEQ` y `REGE` son ERROR en `SPFE-LINEA-DE-COBRO`.
- Las claves 18, 19 y 20 dejan de pasar en el IVA: la L3A es la de la orden.
- `SPFE-RECTIFICATIVA`, en ERROR: los BG-24 de L10 con su código en
  `cbc:DocumentTypeCode`, cada uno de su lista (L2.A, L2.B y L2.C) y con su
  máximo. La extensión de rectificativas de abril ya no cuenta. La sustitución
  sin importes rectificados queda en NOTA, porque la orden solo los prevé si
  se optó por una única factura.
- `SPFE-QR`: uno como mucho, con su dirección, y si lleva descripción,
  VERIFACTU o TICKETBAI.
- `SPFE-TERCERO`: el nombre en la razón social, la tipología, y el NIF escrito
  como el del vendedor.
- `SPFE-BORRADOR` pasa a ser `SPFE-ALCANCE`: dice con qué se mide y las ocho
  cosas de la orden que todavía no (`LO_QUE_TODAVIA_NO_SE_MIDE`), y el glosario
  las copia letra a letra. La línea de alcance del informe manda a esa nota.
  De 24 códigos `SPFE-` quedan 22, y de 389 en total, 387.
- La portada, la tesis y el aviso legal (con su fecha y su huella) dicen
  «parte del anexo I» y no «en buena parte con el borrador».
- `copia_fiel`: 116 términos europeos; el periodo de facturación pasa a
  IGUAL, y el porcentaje del cargo se parte en dos filas, el del documento
  (que la orden no pide) y el de la línea (que sí). Quedan 98 filas.
- `NO_SE_COMPRUEBA` pierde `BG-17`, que la orden deja en `0..n`.

**Lo que se decidió sin preguntar, y por qué.**

- **El QR con la URN de abril no es el QR**: ni se le pide la dirección ni
  cuenta para estar repetido. La orden deja el QR en `0..1`, así que no
  llevarlo no es un fallo, y una factura escrita con abril ya sale con su
  identificador en ERROR.
- **Lo que no se mide va en la nota y no en un AVISO.** No son fallos de la
  factura sino límites del validador, y un AVISO en cada factura de la
  solución pública diría lo contrario. Son el paso 7.
- **El calificador de L10 delante o sin él**, como ya se hacía con los de L7
  y L8: la orden da el valor en la fila y el calificador en la lista, sin
  decir cómo se juntan.

**Las pruebas.** `tests/test_solucion_publica.py` se reescribe sobre la
factura de la orden, que pasa a ser la de partida, con 157 pruebas: la de la
orden y veinte variantes pasan el validador entero sin un ERROR ni un AVISO, y
lo que solo decía el borrador va aparte, en `TestLoQueSoloDeciaElBorrador`.

**Provocado.** Diez roturas, las diez en rojo: `REEQ` y `REGE` vuelven a valer
(4 pruebas en rojo), la URN de abril vuelve a ser de L10 (2), la rectificativa
sin documentos vuelve a NOTA (5), las claves 18, 19 y 20 vuelven a valer (5),
el identificador de abril vuelve a valer (2), lo que no se mide nombra una
fila que no existe (2), el glosario dice otra lista (1), la línea de alcance
deja de mandar a la nota (1), el QR admite otra descripción (2) y el formato
deja de reconocer el identificador de la orden (116). Y una frase cambiada en
una fila de `cius_es`: `test_volver_a_extraer_da_exactamente_lo_mismo`, en
rojo.

La primera versión de la rotura del glosario salió **verde**: añadía texto
delante de la entrada, y la prueba mira que la lista esté dentro, no que no
haya nada más. Se cambió por una que quita un trozo de la lista, y salió roja.

**Lo que queda.** El mensaje de `BR-CL-17` y `BR-CL-18` para la N, la D y la
F fuera de la solución pública (decidido el 11-10-2026: la lista de la norma,
y un mensaje que diga que el código es de la L4 de la orden); el README al
día; y el paso 7, las reglas nuevas de la orden.

### La N fuera de la solución pública: el mensaje decía «no es de UNCL 5305» y nada más

**Lo que había.** El titular decidió el 11-10-2026 que la N, la D y la F, que
la L4 de la orden trae y la lista de la norma no, valen solo en las facturas que declaran
la solución pública. Fuera de ella, `BR-CL-17` y `BR-CL-18` las dan por malas,
y eso no cambia. Lo que faltaba era el porqué.

**Reproducido** sobre `354b6bd`, con la factura de la orden en la N y en la D
y el identificador cambiado a `urn:cen.eu:en16931:2026`: `BR-CL-17` y
`BR-CL-18` en ERROR, con «El código no es de UNCL 5305, que es la lista de la
que tiene que salir», y ni una palabra de la orden. Quien escribió la N la
sacó de la orden, y lo que le falta es declarar la solución pública, no
cambiar de código: el mensaje mandaba a buscar el fallo donde no está.

**Lo que se hizo.** `listas_de_codigos` resta la L4 de la orden menos UNCL
5305, y cuando un código que falla es de esa resta, la queja añade una frase:
que es de la lista L4 de la Orden HAC/1028/2026, que solo rige en las facturas
UBL que declaran en BT-24 el identificador de la orden (escrito entero), y que
en cualquier otra rige la de la norma. Solo nombra los que son de la orden:
con una X junto a la N, la queja lleva las dos y la frase solo la N. El
glosario de las dos reglas lo dice también.

La resta se hace en cada llamada y no junto a las listas: lo que hay debajo de
la marca lo reescribe `herramientas/listas_de_codigos.py`. Y se hace en dos
módulos, el de las listas y `solucion_publica`, así que hay prueba de que las
dos dan `{N, D, F}`.

**Lo que no se hizo, a propósito.** `IVA-CATEGORIA-RARA` sigue diciendo «no
es una categoría de IVA de la norma» sin nombrar la orden: es verdad, va en
AVISO, y la decisión era sobre las dos reglas que condenan.

**Provocado.** Seis pruebas nuevas o ampliadas, las seis en rojo contra
`354b6bd` y en verde con el arreglo. Y tres roturas del arreglo, las tres en
rojo: la frase nombrando todo lo que falla (1), la resta en cualquier lista
(1) y la frase sin el identificador (3).

### Tres fichas publicadas que se quedaban en un 404

**Lo que había.** La primera tanda quitó tres códigos del glosario:
`SPFE-BORRADOR`, que pasó a ser `SPFE-ALCANCE`, y `SPFE-RECARGO-DE-EQUIVALENCIA`
y `SPFE-GRUPO-DE-ENTIDADES`, que la orden ya no tiene. Cada código tiene su
ficha en el sitio, y el sitio se monta del glosario: sin el código, no hay
ficha.

**Reproducido** el 11-10-2026: `https://www.glosa-e.com/codigo-SPFE-BORRADOR`
contestaba 200 y las tres estaban en el `sitemap.xml` de producción. Montado
el sitio con `6f7f186`, las tres fichas no salen. Publicar así dejaba tres
direcciones que los buscadores ya tienen apuntando a nada.

**Lo que se hizo.** Tres redirecciones permanentes en `vercel.json`: la del
borrador a `SPFE-ALCANCE`, y las dos líneas de abril a `SPFE-LINEA-DE-COBRO`,
que es lo que dan ahora `REEQ` y `REGE`. La prueba salió en rojo antes de
escribirlas.

**Y que no vuelva a pasar sin enterarse.** El sitemap se construye y no se
versiona, así que desde una prueba no se sabe qué se publicó. Ahora se sabe:
`tests/fichas_publicadas.txt` lleva los 390 códigos que tienen o tuvieron
ficha (los 387 del glosario y los tres retirados). Un código del glosario que
no esté apuntado deja la suite en rojo, y uno apuntado que ya no esté en el
glosario también, si su ficha no lleva a otra de forma permanente. La que ya
había comprueba que ninguna redirección lleve a una ficha que no existe.
Provocado por los dos lados: quitando una redirección (dos pruebas en rojo) y
quitando un código de la lista (una).

### La revisión antes de publicar: lo que el informe callaba

**Lo que había.** Antes de publicar las cuatro tandas, el revisor de promesas y
un auditor, cada uno por su lado, midieron lo que Glosa dice contra lo que
hace. La portada y la política de privacidad dicen que lo que de la orden no
se mide «lo dice cada informe», y había cosas que la orden pide, que no se
comprobaban y que ningún informe nombraba.

**Reproducido**, todo con `factura.validar` sobre `31e38a7`:

| Qué | Lo que salía | La orden |
|---|---|---|
| La suma de retenciones a 999 con una retención de 15 | sin errores | `BT-ES-17`: «sumatorio de todas las retenciones practicadas» |
| Una retención de 77 sobre 100 al 15 % | sin errores | `BT-ES-19`: «resultado de aplicar a la base imponible de la retención el porcentaje» |
| El NIF-IVA del comprador con prefijo FR | sin errores, y la nota no lo nombraba | `BT-48`: «con el prefijo correspondiente a España» |
| Importes rectificados con la modalidad `I` | nada | el grupo es para «los casos en los que se proceda a la rectificación por sustitución» |
| Cuatro o cinco importes rectificados | nada | `BT-3` dice «hasta tres grupos» y el grupo es `0..5` |
| Lo de `NO_SE_COMPRUEBA` | de ocho entradas llegaban al informe dos, `BT-115` y `BT-113`, por sus propias notas | |
| El QR escrito con la URN de abril y sin dirección, con el identificador de la orden | nada | para la orden no es el QR |
| Un abono que declara la orden | `SPFE-ALCANCE` decía «se mide con el anexo I» junto a `SPFE-TIPO-DE-FACTURA`, que dice que el resto no se ha comprobado, y la línea de alcance del lote lo contaba como medido | el anexo solo define facturas |
| Ese abono con la `N` | `BR-CL-18` decía que la N vale en las facturas «que van en UBL y declaran» el identificador de la orden, y el abono es UBL y lo declara | |

Y la nota acababa en «no quiere decir que la factura cumpla la orden en eso»,
como si lo que no enumeraba estuviera medido entero. El artículo de la
bitácora sobre las rectificativas, publicado, decía que la extensión de abril
«todavía se acepta» y que lo que falta sale en AVISO o en NOTA, falso desde la
primera tanda.

**Lo que se hizo.**

- Las dos cuentas de las retenciones se hacen, con los márgenes de la norma
  para lo mismo: la retención, el de la cuota del IVA (`BR-CO-17`, una unidad,
  con una NOTA si no cuadra al céntimo); la suma, exacta, como las de la
  cabecera. Las dos definiciones se leen de su fila al importar.
- Los importes rectificados con `I` salen en AVISO, y cuatro o cinco en una
  NOTA que dice que la orden se contradice. Las dos frases, leídas de su fila.
- `BT-48` entra en la lista de lo que todavía no se mide, como ya estaba
  `BT-31`. Una prueba lo ata: el día que se mida, se pone en rojo.
- La nota nombra también lo que no se puede comprobar, y su ficha copia el
  porqué de cada cosa letra a letra. Acaba en «no quiere decir que la factura
  cumpla la orden», sin más.
- El abono no recibe la nota, y la línea de alcance del lote cuelga de la nota
  y no de lo que el documento declara. La queja de la N dice «como factura
  (Invoice), no como abono (CreditNote)».
- El QR con la URN de abril sale en una NOTA: sigue sin ser el QR, y se dice.
- El artículo, al día. Y una prueba por cada frase de su sección «hoy», con la
  factura que la comprueba: si una regla cambia, el artículo no se queda atrás
  sin que nadie se entere.

**Lo que no se hizo.** Que la cifra de cada importe rectificado sea la buena
sigue sin comprobarse: la factura original no viaja con la rectificativa, y no
hay con qué compararla. El artículo lo dice. Lo demás que encontró el auditor
es de precisión y no del informe, y va en la tanda siguiente.

**Provocado.** Veintiuna pruebas nuevas o cambiadas, en rojo contra el código
de `31e38a7` y en verde con el arreglo. Y catorce roturas del arreglo, las
catorce en rojo: el cuadre fuera de las reglas (3 pruebas en rojo), la nota de
la retención convertida en error (1), la nota sin lo que no se puede (1),
otra vez «en eso» (1), `BT-48` fuera de la lista (1), el abono medido como
factura (1), la línea del lote por lo que se declara (1), la frase de la N sin
el abono (1), el QR de abril callado (1), los importes con `I` callados (1),
cuatro importes callados (2), la definición de `BT-ES-17` sin leer (1), la
bitácora con otra gravedad (1) y la ficha sin un porqué (1).

### La revisión antes de publicar: lo que no era exacto

**Lo que había.** El mismo auditor encontró cosas que no tocan al informe de
una factura sino a lo que se escribió para explicarlo o para probarlo. Cada
una, reproducida aquí antes de arreglarla:

- **Una medida de esta tanda, hecha con una factura inválida.** La fila del
  nombre del tercero en `cac:PartyName` decía «sin errores» en `5d4f135`, y la
  factura lo ponía detrás de `cac:PartyTaxScheme`, donde UBL no lo admite:
  con `5d4f135` sale `XSD-ORDEN`, y con lo de hoy `XSD-ORDEN` y
  `SPFE-TERCERO`. La prueba no lo veía porque solo miraba el anexo. Bien
  colocado, `5d4f135` da nada y hoy `SPFE-TERCERO`: la conclusión vale, la
  medida no. La prueba lleva ahora la factura bien escrita y pasa el
  validador entero, y la fila dice cómo se midió.
- **«UNCL 5305 no tiene la D ni la F».** Lo decían el código, esta misma
  sección y el mensaje de `BR-CL-17` y `BR-CL-18`, que llamaba «UNCL 5305» a
  secas a la lista de la norma. La UNTDID 5305 entera tiene la D y la F desde
  su edición D16A (el margen de las agencias de viajes y el de los bienes
  usados), y la N no la tiene; leído en edifactory el 11-10-2026. La norma usa
  su versión, con diez códigos. El mensaje dice ahora «UNCL 5305 tal como la
  recoge la norma». Y la orden, que dice sacar la L4 de la UNTDID 5305, trae
  una N que no está en ella.
- **La tipología del tercero, en la ruta que escribe la orden.** Ahí UBL no la
  admite y sale `XSD-ORDEN`; `SPFE-TERCERO` decía además «le falta la
  tipología», y no faltaba. Ahora dice que está en su `cac:Party` y dónde va.
- **Dos pruebas que no podían fallar.** Una comparaba la L7 de la tabla
  consigo misma, y la otra repetía una negativa que el módulo ya hace al
  importar. Ahora comparan con la lista escrita en la prueba.
- **«Las tres formas están provocadas».** La de la ruta movida solo se
  probaba llamando a `_relativa`. Reproducido: con la ruta de `BT-ES-18`
  movida en la tabla y solo `solucion_publica` recargado, importa sin
  negarse, porque las rutas las calcula `sintaxis` al importarse; recargando
  los dos, se niega. Ahora hay prueba de eso, en un proceso aparte.
- **«Trece roturas»**, donde fueron catorce si se cuenta la frase cambiada en
  la tabla. El README dice ahora las dos cosas.
- **Las claves 18, 19 y 20 en otro orden.** Eran el recargo, la agricultura y
  el simplificado, y un comentario, una prueba y el README las nombraban al
  revés.

**Lo que no se hizo.** Una 380 con un `RECT:TIPO` pasa sin nada. La orden ata
el tipo de rectificativa a la 384 y la 471, pero no dice que otra factura no
pueda llevarlo, y el auditor lo dejó como sospecha. Queda así.

**Provocado.** Cinco pruebas nuevas o cambiadas en rojo contra `6865cbd` (la
tipología y las tres categorías con su mensaje, y la que dice que la D y la F
sí son de la UNTDID 5305). Y nueve roturas, una por arreglo, las nueve en
rojo: el nombre del tercero otra vez detrás de `cac:PartyTaxScheme` (1 prueba
en rojo), la tipología en su `cac:Party` dada otra vez por ausente (1), sin el
arreglo de esa ruta en `sintaxis` (1, al importar), la lista otra vez «UNCL
5305» a secas (3), el glosario igual (1), la L7 de la tabla cambiada con su
fila a juego (1), la L10 igual (1), una de las buenas con un elemento fuera de
su sitio (1) y una ruta que deja de colgar de su grupo sin que el módulo se
niegue (1).

**Lo que salió al provocar.** La primera rotura, el nombre del tercero otra
vez detrás, salió en verde. La prueba ya pasaba la factura por «el validador
entero», pero la suite corre sin esquemas (`conftest.py`), y sin esquemas el
validador no mira la forma: `XSD-ORDEN` no podía salir. Lo mismo con las
veintiuna buenas, de las que el README y el módulo de pruebas decían que
pasaban la forma contra UBL 2.5 sin que la suite lo comprobara. Ahora esas
pruebas cargan los esquemas de `web/paquete.zip`, que se versiona: las
veintiuna pasan la forma, en 1,16 s medido. Las dos roturas que tocan la forma
son las dos que se añadieron por esto, y salen en rojo.

## Lo que la orden pide y no se medía: la fecha de pago, el NIF y el desglose

**Lo que había.** Desde el 11-10-2026 la nota `SPFE-ALCANCE` decía nueve cosas
que la orden pide y aquí no se medían. Seis se podían escribir con lo que el
anexo ya dice: la fecha efectiva de pago (`BT-ES-2`), el registro legal del
vendedor cuando su NIF va con «LOC» (`BT-30`), el prefijo ES del NIF-IVA del
vendedor (`BT-31`) y el del comprador (`BT-48`), el tipo de la entrada no
sujeta del desglose (`BT-119`) y los códigos de exención (`BT-121`).

**Reproducido** el 11-10-2026 sobre `ab3e4b3`: dieciséis facturas escritas a
partir de la de la orden, por el validador entero y con los esquemas de
`web/paquete.zip`, en una copia de `HEAD` y en la de trabajo ya cambiada.

| Factura | En `ab3e4b3` | Ahora |
|---|---|---|
| la de la orden | sin errores | sin errores |
| la fecha de pago posterior a la expedición | **sin errores** | `FECHA-DE-PAGO` |
| anterior a la operación (`BT-7`) | **sin errores** | `FECHA-DE-PAGO` |
| posterior a la operación y anterior a la expedición | sin errores | sin errores, y una NOTA |
| anterior a la expedición, sin `BT-7` | **sin errores** | `FECHA-DE-PAGO` |
| dos fechas de pago, la segunda del día antes | **sin errores** | dos `FECHA-DE-PAGO` |
| anterior a la expedición, con un periodo | sin errores | sin errores, y una NOTA |
| el NIF del vendedor con «LOC» y sin `BT-30` | `BR-CO-26` | `BR-CO-26` y `NIF` |
| lo mismo, con `BT-29` | **sin errores** | `NIF` |
| el NIF-IVA del vendedor con FR | `CU-01` | `NIF` y `CU-01` |
| el del comprador con FR | **sin errores** | `NIF`, en AVISO |
| la no sujeta sin tipo en el desglose | **sin errores** | `TIPO-DE-IVA` |
| la no sujeta con tipo 0 | sin errores | sin errores |
| la exenta con VATEX-EU | sin errores | sin errores |
| la exenta con VATEX-FR | **sin errores** | `EXENCION` |
| la exenta con un VATEX-ES | `BR-CL-22` | `BR-CL-22` |

**Lo que se hizo.**

- `SPFE-FECHA-DE-PAGO`, nuevo: una como mucho, no posterior a la expedición
  ni anterior a la operación. Sin `BT-7` la operación es del día de la
  expedición, porque la orden pide `BT-7` solo cuando es de otro día; con un
  periodo de facturación en su lugar, una NOTA dice que no se ha comparado.
- `SPFE-NIF` pide `BT-30` cuando el NIF del vendedor va en `BT-32`, y el
  prefijo ES en `BT-31` (ERROR) y en `BT-48` (AVISO).
- `SPFE-TIPO-DE-IVA`, nuevo: el tipo en la entrada no sujeta del desglose.
- `SPFE-EXENCION`, nuevo: el código de exención, VATEX-EU o VATEX-ES.
- Al importar se leen las frases de las filas `BT-ES-2`, `BT-7`, `BT-30`,
  `BT-31`, `BT-48` y `BT-121` de las que salen las reglas, la cardinalidad de
  `BT-ES-2`, que `BT-119` sea obligatorio y que `BT-30` siga sin ruta. Si
  cambian, `AnexoCambiado`.
- `LO_QUE_TODAVIA_NO_SE_MIDE` se queda en tres, y la ficha de `SPFE-ALCANCE`
  se regenera de ella. De 22 códigos `SPFE-` se pasa a 25, y de 387 en total,
  a 390: la portada y la tesis lo dicen.

**Lo que salió al cotejar la ficha con el artículo.** La primera ficha de
`SPFE-FECHA-DE-PAGO` decía que con esa fecha el destinatario no tiene que
comunicar el pago (apartado 4 del artículo 7). El artículo lo dice solo de
una fecha que coincide con la de la operación, y la fila admite también una
posterior. La ficha dice ahora las dos cosas, y un pago posterior a la
operación sale con una NOTA que lo explica. La factura está bien; lo que
cambia es lo que tiene que hacer quien la recibe.

**Lo que salió al medir.** El caso de `BT-30` que se había escrito para la
prueba ya salía en `BR-CO-26`, porque al quitar el registro legal el vendedor
se quedaba sin ninguno de los tres identificadores que pide la norma. Con
`BT-29` la norma se calla: es el caso en que solo habla la orden, y la prueba
lo mira con el validador entero. La primera versión de esa aserción usaba el
ayudante `codigos`, que solo devuelve las `SPFE-`: `BR-CO-26` no podía salir,
y la aserción pasaba sin mirar nada. Ahora mira las dos cosas, que con
`BT-29` no sale y que sin él sí.

**Las pruebas.** Tres facturas buenas más, 24 en total, que pasan el
validador entero sin un ERROR ni un AVISO: con la fecha de la operación, la
no sujeta con su tipo y la exenta con VATEX-EU. `TestLaFechaDePago` (ocho
pruebas), tres más en `TestPartes`, `TestElDesglose` (cuatro), y las frases
y cardinalidades del anexo, provocadas una a una al importar.

**Provocado.** Dieciocho roturas, las dieciocho en rojo: el pago posterior a
la expedición vuelve a valer (1 prueba en rojo), el anterior a la operación
(1), sin la nota del artículo 7 (1), con un periodo otra vez ERROR (1), sin
`BT-7` el pago anterior vuelve a valer (1), dos fechas vuelven a valer (1),
`BT-30` deja de pedirse (1), el prefijo FR vale como el ES (2), lo del
comprador en ERROR (1), `BT-119` mira otra categoría (1), `BT-119` en todas,
repitiendo `BR-48` (1), cualquier VATEX vale (1), y seis lecturas del anexo
que dejan de hacerse: la cardinalidad de `BT-ES-2`, la obligación de `BT-119`,
la ruta de `BT-30`, la errata de `BT-48`, la restricción de `BT-121` y la
frase de `BT-7` (1 cada una).

**Lo que queda del paso 7.** Los impuestos y tasas que no son el IVA, con su
lista L9 (`BG-ES-2`, `BT-ES-22`, `BG-ES-3`); la información adicional de cada
línea (`INFO` de L8); el número de la autorización (`BT-ES-26`); los ficheros
embebidos (artículos 3.6 y 4.4); y el mensaje de anulación y los del anexo II.

## Los impuestos y tasas que no son el IVA, y la información de la línea

**Lo que había.** Después de la tanda anterior, la nota `SPFE-ALCANCE` decía
tres cosas que la orden pide y aquí no se medían: los impuestos y tasas que no
son el IVA, con su lista L9 (`BT-ES-22`, `BG-ES-2` y `BG-ES-3`); el número de
la autorización de facturación (`BT-ES-26`); y la información adicional de
cada línea (`BT-160` con `INFO`).

**Reproducido** el 11-10-2026 sobre `e51de10`: diecinueve facturas escritas a
partir de la de la orden, por el validador entero y con los esquemas de
`web/paquete.zip`. Las diecinueve salían **sin un error ni un aviso**, también
las diez que la orden da por malas:

| Factura | En `e51de10` | Ahora |
|---|---|---|
| la de la orden | sin errores | sin errores |
| un cargo de línea con `RESTO`, o con `IEE` | sin errores | sin errores |
| un cargo de línea sin código | **sin errores** | `IMPUESTO-O-TASA` |
| con `XYZ` | **sin errores** | `IMPUESTO-O-TASA` |
| un impuesto cobrado como cargo del documento, con `IEE` | sin errores | sin errores |
| sin código | **sin errores** | `IMPUESTO-O-TASA` |
| con `XYZ` | **sin errores** | `IMPUESTO-O-TASA` |
| con 5 en el impuesto y 6 en el total del cargo | **sin errores** | `IMPUESTO-O-TASA` |
| con 7 de cuota sobre 100 al 5 % | **sin errores** | `IMPUESTO-O-TASA` |
| con dos impuestos en el mismo cargo | sin errores | sin errores, y una NOTA |
| sin base ni tipo | sin errores | sin errores |
| el IEDMT cobrado para un tercero, con su desglose | sin errores | sin errores |
| con «IGIC» en el desglose | **sin errores** | `IMPUESTO-O-TASA` |
| con la categoría `E` | **sin errores** | `IMPUESTO-O-TASA` |
| con 150 de cuota sobre 2000 al 6 % | **sin errores** | `IMPUESTO-O-TASA` |
| una propiedad `INFO`, y con el calificador de L8 | sin errores | sin errores |
| una propiedad «Color» | **sin errores** | `INFORMACION-ADICIONAL` |

**Lo que se hizo.**

- `SPFE-IMPUESTO-O-TASA`, nuevo: el código de L9 en cada cargo de línea y en
  cada impuesto de un cargo del documento; en ese cargo, la misma cuota en el
  impuesto y en el total, y con dos impuestos una NOTA, porque no se puede
  (la pregunta 4 al buzón, del 07-10-2026); «VAT» y «S» en el desglose de un
  cobro; y la cuota de cada uno, la base por el tipo.
- La cuenta de la cuota se saca a `_cuenta_de_la_cuota`, con el margen de la
  del IVA (hasta una unidad, NOTA), y las retenciones pasan a usarla: la
  misma cuenta en tres sitios, escrita una vez.
- `SPFE-INFORMACION-ADICIONAL`, nuevo: el nombre de cada propiedad del
  artículo, de L8, con su calificador o sin él.
- Al importar se leen las filas `BT-ES-8`, `BT-ES-9`, `BT-ES-14`, `BT-ES-22`,
  `BG-ES-2`, `BG-ES-3`, `BG-32` y `BT-161` de la información adicional, que la
  L9 no traiga calificador y que la L8 sean las tres propiedades. Si cambian,
  `AnexoCambiado`. `_cuantos` acepta ahora un máximo sin límite, «0..n».
- `LO_QUE_TODAVIA_NO_SE_MIDE` se queda en una cosa, `BT-ES-26`, y la nota la
  dice sin el punto y coma de las listas. De 25 códigos `SPFE-` se pasa a 27,
  y de 390 en total, a 392.
- `NO_SE_COMPRUEBA` decía dónde se miran las cardinalidades máximas y no
  nombraba la fecha efectiva de pago, que la tanda anterior mira «una como
  mucho». Ahora la nombra.

**Lo que salió al provocar.**

- La negativa de `BT-160` salió en **verde**. Se comprobaba que la fila
  dijera «valor fijo INFO», y una fila que dijera «valor fijo INFORMACION» lo
  dice también. Las de `REGI` y `RCAT` llevaban el mismo hueco desde que se
  escribieron: un `REGIX` en la orden pasaba por `REGI`. Ahora `_valor_fijo`
  lee el valor entero entre sus comillas, y las tres roturas (`INFO`, `REGI`,
  `RCAT`) salen en rojo.
- La prueba de que lo que no se mide no lo mida nadie llevaba los
  identificadores escritos a mano, y cada tanda tenía que acordarse de
  quitarlos de los dos sitios. Ahora los saca de la propia lista: devolver la
  información adicional a la lista la pone en rojo.

**Las pruebas.** Cuatro facturas buenas más, 28 en total, que pasan el
validador entero sin un ERROR ni un AVISO: un cargo de línea con su código, un
impuesto cobrado como cargo, el desglose del IEDMT y una línea con `INFO`.
`TestLosImpuestosYTasas` (once casos), uno más en `TestLineas`, y las
filas y listas del anexo, provocadas una a una al importar.

**Provocado.** Diecisiete roturas, las diecisiete en rojo: el cargo de línea
sin código vuelve a valer (1 prueba en rojo), con un código fuera de L9 (1),
el impuesto del cargo sin código (1), fuera de L9 (1), las dos cuotas del
cargo dejan de compararse (1), con dos impuestos se compara el primero (1),
la cuota deja de contarse (2), sin el margen de la cuota del IVA (1), el
desglose del cobro sin «VAT» y «S» vuelve a valer (2), cualquier nombre de
propiedad vuelve a valer (1), `INFO` con calificador deja de leerse (1), la
información adicional vuelve a la lista de lo que no se mide (1), el valor
fijo otra vez como trozo de frase (2), y cuatro lecturas del anexo que dejan
de negarse: la L9 con calificador, la L8 con otra propiedad, `BT-ES-8` en una
sola ruta y `BT-ES-22` fuera de L9 (1 cada una).

**Lo que queda del paso 7.** El número de la autorización (`BT-ES-26`); los
ficheros embebidos (artículos 3.6 y 4.4); y el mensaje de anulación y los del
anexo II.

## La autorización, los ficheros embebidos y lo que se quitaba sin una queja

**Lo que había.** Después de la tanda anterior, `LO_QUE_TODAVIA_NO_SE_MIDE`
decía una cosa: el número de la autorización de facturación (`BT-ES-26`). Y la
orden prohíbe en su articulado, no en el anexo, los ficheros integrados o
embebidos: a las facturas emitidas o interconectadas (apartado 6 del artículo
3), salvo la firma de las interconectadas, y a las copias fieles (apartado 4
del artículo 4). Nada de eso se miraba.

**Reproducido** el 11-10-2026 sobre `cae90d3`: dieciocho facturas escritas a
partir de la de la orden, por el validador entero y con los esquemas de
`web/paquete.zip`. Ninguna sacaba una queja del anexo, tampoco las ocho que
la orden da por malas ni las dos copias fieles con la firma, que la orden no
dice si valen:

| Factura | En `cae90d3` | Ahora |
|---|---|---|
| la de la orden, y con una autorización con su número | sin errores | sin errores |
| la autorización sin número | **sin errores** | `AUTORIZACION` |
| a secas y sin número | **sin errores** | `AUTORIZACION` |
| con el número vacío | **sin errores** | `AUTORIZACION` |
| dos, la segunda sin número | **sin errores** | `AUTORIZACION`, que dice cuál |
| un contrato en PDF dentro de un documento | **sin errores** | `FICHERO-EMBEBIDO` |
| un contrato en texto | **sin errores** | `FICHERO-EMBEBIDO` |
| un contrato por su dirección | sin errores | sin errores |
| el QR con su imagen dentro | **sin errores** | `FICHERO-EMBEBIDO` |
| la original con la firma en un fichero, o nombrada | sin errores | sin errores |
| la original con la firma envuelta | los de la firma | los mismos |
| la copia fiel sin firma, o con la firma nombrada | sin errores | sin errores |
| la copia fiel con la firma en un fichero | **sin errores** | AVISO `FICHERO-EMBEBIDO` |
| con la firma envuelta | los de la firma | los mismos, y el AVISO |
| con un contrato en PDF | **sin errores** | `FICHERO-EMBEBIDO`, con el artículo 4 |

La firma envuelta de la prueba es de mentira, y las reglas de la firma lo
dicen igual antes y después.

**Antes de vaciar la lista** había que saber si quedaba algo más. Se quitó
cada elemento de las veintiocho facturas buenas, uno a uno, y se pasó el
validador entero: 33 rutas salían sin una queja. Casi todas son opcionales en
el anexo (el QR, el tercero, los cargos, la fecha de pago, el tipo de la línea
exenta…). Cuatro no:

| Factura | En `cae90d3` | Ahora |
|---|---|---|
| la línea sin «VAT» en el impuesto | **sin errores** | `TIPO-DE-IMPUESTO` |
| el desglose sin «VAT» | **sin errores** | `TIPO-DE-IMPUESTO` |
| un cargo sin «VAT» | **sin errores** | `TIPO-DE-IMPUESTO` |
| un cargo con el total del impuesto y sin su detalle | **sin errores** | `IMPUESTO-O-TASA` |
| la suma de retenciones sin ninguna retención | sin errores | sin errores, y una NOTA |

El «VAT» se miraba solo cuando estaba escrito: una factura sin un solo «VAT»
pasaba. Las filas BG-30, BG-23, BT-95 y BT-102 dicen que «su uso implica» que
la ruta tome el valor, y sin el elemento no lo toma. Y un cargo que lleva el
total del impuesto sin su detalle tiene la cuota en una sola de sus dos rutas
(`BT-ES-8`) y nada que diga qué impuesto es.

**Lo que se hizo.**

- `SPFE-AUTORIZACION`, nuevo: cada `BG-24` `AUT`, con el calificador de L10
  o sin él, con su número en `cbc:UUID`. Se leen al importar la fila
  `BT-ES-26` (obligatoria y su descripción) y el grupo, `0..n`.
- `SPFE-FICHERO-EMBEBIDO`, nuevo: un `cbc:EmbeddedDocumentBinaryObject` o un
  `cbc:EmbeddedDocument` fuera de `cac:Signature` es ERROR, en la original con
  el artículo 3 y en la copia fiel con el 4. La copia fiel con la firma, en un
  fichero o envuelta, es AVISO: el artículo 4 no hace la salvedad del 3, y la
  orden no dice si la firma es uno de esos ficheros. Esos dos textos no están
  en `cius_es`, y no hay fila que leer al importar.
- `SPFE-TIPO-DE-IMPUESTO` mira desde la categoría de cada sitio, y la que no
  lleva `cac:TaxScheme/cbc:ID` sale con «(falta)».
- `SPFE-IMPUESTO-O-TASA`: el cargo con el total del impuesto y sin su
  detalle, sin código.
- `SPFE-RETENCION`: con la suma y sin ninguna retención, una NOTA que dice
  que no hay con qué compararla. Se lee al importar que `BG-ES-4` siga en
  `0..n`.
- `LO_QUE_TODAVIA_NO_SE_MIDE` queda vacía, y la nota y su ficha dejan de
  nombrarla. `NO_SE_COMPRUEBA` gana lo que la orden deja a la Sede (las
  especificaciones técnicas, la volumetría y el tamaño máximo de las copias
  fieles), que no es el anexo. La frase de alcance del informe decía «lo que
  todavía no se mide lo dice la nota»: ahora, «lo que no se mide».
- De 27 códigos `SPFE-` se pasa a 29, y de 392 en total, a 394.

**Lo que salió al medir.** El README decía en negrita «25 códigos» y, dos
líneas más abajo, «llegaron a 27». La tanda anterior cambió la segunda cifra y
no la primera. Ahora `test_el_readme_dice_cuantos_codigos_hay` cuenta los
códigos que escribe el módulo y compara las dos: salió en rojo con el 25
antes de arreglarlo.

**Las pruebas.** Dos facturas buenas más, 30 en total, que pasan el
validador entero sin un ERROR ni un AVISO: un documento por su dirección y la
original con la firma en un fichero. `TestLaAutorizacion` (cinco casos),
`TestLosFicherosEmbebidos` (diez), `TestLoQueSeQuitabaSinUnaQueja` (dos), el
tipo de impuesto que falta en sus tres sitios, que la nota diga lo de la Sede,
y las filas del anexo, provocadas una a una al importar.

**Provocado.** Diecinueve roturas, las diecinueve en rojo: la autorización sin
número vuelve a valer, un fichero dentro vuelve a valer, la firma deja de
exceptuarse, la copia fiel con la firma deja de avisarse, la firma envuelta
deja de contar, la copia deja de citar el artículo 4, un documento por su
dirección pasa por fichero, el tipo de impuesto que falta vuelve a valer, el
total del impuesto sin su detalle vuelve a valer, la suma sin retenciones deja
de decirse, la suma a cero también se nota, la autorización vuelve a la lista
de lo que no se mide, la nota dice que falta algo con la lista vacía, lo de la
Sede sale de lo que no se comprueba, el README vuelve a decir 27 códigos, y
cuatro lecturas del anexo que dejan de negarse (el grupo de la autorización,
`BT-ES-26` obligatoria y su descripción, y `BG-ES-4`).

**Lo que queda del paso 7.** El mensaje de anulación y los del anexo II, que
no son facturas.

## El tipo que falta en la línea, el descuento y el cargo

**Lo que había.** Las reglas `BR-{X}-05`, `06` y `07` piden el tipo que toca a
cada categoría en cada línea (`BT-152`), descuento (`BT-96`) y cargo
(`BT-103`) de documento. `iva._regla_tipo_de_los_conceptos` miraba el valor
cuando lo había, y si faltaba ponía `mal = False`, con este comentario: «Que
el tipo **falte** lo dice BR-48, una sola vez para toda la factura». BR-48 es
del desglose (`BT-119`), no de la línea. Salió al vaciar
`LO_QUE_TODAVIA_NO_SE_MIDE`: entre los elementos que se quitaban sin una queja
estaba el tipo de la línea exenta y el de la AE, y se apuntó como opcional en
el anexo, que lo es. Quedaba mirar si la norma lo deja ir.

**La norma no lo deja ir.** En el esquematrón oficial las tres reglas son, en
las tres vinculaciones, una comparación con el tipo:
`xs:decimal(cbc:Percent) = 0` en UBL, `ram:RateApplicablePercent = 0` en CII,
`C_C243/D_5278 = 0` en EDIFACT (y `> 0` o `>= 0` en la S, el IGIC y el IPSI).
En XPath una comparación con nada es falsa, así que sin tipo la regla salta. En
la O es al revés, `not(...)`. Las pruebas unitarias oficiales no lo prueban:
de los 78 conceptos que montan sus casos de estas reglas, ninguno va sin tipo
fuera de la O. Aquí no hay un motor de XPath 2 para correr el esquematrón; lo
que se hizo fue evaluar con lxml la expresión de cada regla sobre un concepto
vacío, cambiando `xs:decimal` por `number`, que con el tipo ausente da lo
mismo.

**Reproducido** el 11-10-2026 sobre `a08a8a3`:

| Factura | En `a08a8a3` | Ahora |
|---|---|---|
| el caso bueno de cada prueba oficial `BR-{X}-05`, `06` y `07`, sin el tipo: ocho categorías por tres conceptos | **sin la regla**, en los 24 | la regla, en los 24 |
| lo mismo en la O | sin la regla | sin la regla |
| la de la orden con AE, sin el tipo de la línea | **sin errores** | `BR-AE-05` |
| la exenta con VATEX-EU de la orden, sin el tipo de la línea | **sin errores** | `BR-E-05` |
| las de la orden a tipo general, sin el tipo de la línea | `BR-S-08` e `IVA-TIPO-SIN-DESGLOSE` | los mismos y `BR-S-05`, que es la causa |
| el motor contra el texto oficial de las 27 reglas en UBL, CII y EDIFACT, sobre un concepto sin tipo: 81 | **distinto en 72**, todas las que no son de la O | lo mismo en las 81 |

En las de tipo general no callaba del todo: la línea sin tipo no casaba con
ninguna entrada del desglose y saltaban el cuadre y el aviso. Pero la queja
era la consecuencia, no la causa.

**Lo que se hizo.**

- En `iva.py`, el tipo que falta cuenta como mal en todas las categorías menos
  en la O. «Falta» es lo mismo que en BR-48: que no haya un número que leer; un
  tipo escrito que no es número lo denuncia además el XSD.
- El mensaje es otro: dice que falta, no que no está a cero; «Debería» dice lo
  que pide la categoría y «Tiene», «(sin tipo)», como BR-48. Se agrupa por
  tipo como siempre, así que el que falta no se mezcla con el cero.
- Las fichas de las 24 reglas lo dicen. La de `BR-AG-05` decía lo contrario,
  «Si la línea no trae tipo ninguno, la queja no es ésta sino BR-48», y se
  reescribió.
- No hay código nuevo ni cambia ninguna gravedad: son las mismas reglas, en
  ERROR, que es su `flag` en la norma.

**En el corpus**, 157 facturas leídas, con el motor de la norma europea solo
(`en16931.validar`): de 1106 incidencias a 1108. Son dos
`BR-E-05`, en dos facturas EDIFACT con tres líneas exentas sin tipo cada una,
que ya traían otros nueve códigos de error de la norma (sin desglose, entre
ellos).

**Las pruebas.** `TestElTipoQueFalta`, en `tests/test_iva.py`, en UBL y CII:
la línea, el descuento y el cargo sin tipo en las ocho categorías, que con su
tipo no salta, el mensaje, las dos quejas separadas, la O sin tipo, y que la
ficha de cada una lo dice. Y
`test_sin_tipo_saltan_las_del_tipo_salvo_en_la_no_sujeta`, en
`tests/test_norma_oficial.py`, que evalúa el texto oficial de cada vinculación
y lo compara con el motor: si el comité reescribe alguna para admitir el tipo
ausente, se pone en rojo.

**Provocado.** Once roturas, las once en rojo: el tipo que falta vuelve a
valer, la O sin tipo salta, la falta solo en la línea, solo en los ajustes, el
mensaje de «no está a cero», «Tiene» con «(vacío)», «Debería» con otra cifra,
el que falta y el malo en una sola queja, la ficha de `BR-AG-05` con su texto
de antes, una ficha sin la frase, y el comité que admite el tipo ausente en
`BR-E-05`.

**Lo que se vio de paso y no se toca aquí.** El IGIC en CII:
`BR-AF-05`, `06` y `07` comparan con `> 0`, cuando en UBL es `>= 0` y la norma
dice «0 (zero) or greater than zero». Una línea de IGIC al 0% en CII es mala
para su esquematrón y buena aquí. (El de EDIFACT dice `> 0` también en el
IPSI, pero EDIFACT ya se decidió que va con UBL.) Es otra decisión, la de qué
vinculación se sigue cuando no dicen lo mismo, y va aparte.

## El IGIC a cero en CII: la norma lo admite y su esquematrón no

**Lo que había.** `BR-AF-05`, `06` y `07` (el IGIC, categoría L) dicen en el
texto de la norma que el tipo «shall be 0 (zero) or greater than zero». La
vinculación de UBL lo escribe `(cbc:Percent) >= 0`; la de CII,
`ram:RateApplicablePercent > 0`, y la del IPSI en CII, al lado, `>= 0`. La de
EDIFACT, `> 0` en las dos. Aquí el IGIC y el IPSI son `NO_NEGATIVO` en todas
las sintaxis, y nadie había decidido nada sobre la de CII: salió al comparar
las tres vinculaciones el 11-10-2026, mirando el tipo que falta.

**Reproducido** el 12-10-2026 sobre `2ae7722`, con una línea, un descuento y
un cargo al 0 %, y evaluando con lxml la expresión de cada vinculación sobre
un concepto con el tipo a cero:

| | UBL | CII | EDIFACT |
|---|---|---|---|
| el esquematrón, IGIC al 0 % | lo admite | **lo rechaza**, `BR-AF-05` a `07` | lo rechaza |
| el esquematrón, IPSI al 0 % | lo admite | lo admite | lo rechaza |
| el motor en `2ae7722` | sin nada | sin nada | no se midió |
| el motor ahora, IGIC al 0 % | sin nada | NOTA `IVA-CERO-ESQUEMATRON` | sin nada |

**En el repositorio oficial ya se sabe.** La issue 519 de
`ConnectingEurope/eInvoicing-EN16931`, abierta el 07-09-2026, dice que las dos
reglas del cero no admiten el cero en los artefactos aunque el texto lo
admita. Se cerró el 29-09-2026, en el hito 1.3.17 (noviembre de 2026), con un
commit que cambia los **nombres** y no la comparación. Leído en la web del
repositorio el 12-10-2026, sin descargarlo: en `master` la regla del IGIC en
CII sigue con `> 0`.

**Lo que se decidió, y por qué.**

- **Se sigue al texto de la norma, no a la vinculación de CII.** Es lo que
  se hizo con el periodo que el esquematrón de CII no encuentra y con el
  `D_D4461` de EDIFACT: cuando una vinculación no hace lo que dice el texto de su
  propia regla, se sigue al texto. Los márgenes son otra cosa: ahí el texto
  no dice nada y cada vinculación decide, y por eso se siguen las dos. Aquí el
  texto dice «0 (zero) or greater than zero», la vinculación de UBL lo
  respeta, la del IPSI en CII también, y el fallo está denunciado. Y el tipo
  cero del IGIC existe: dar por mala una factura canaria correcta sería
  prometer de más en la otra dirección.
- **Y se dice en una nota.** Quien reciba esa factura y la pase por el
  esquematrón oficial de CII la verá rechazada con `BR-AF-05`, y eso no se
  calla. Es una nota y no un aviso porque en la factura no hay nada que
  arreglar: dice qué se dio por bueno y con qué base, que es para lo que están
  las notas.
- **EDIFACT no la lleva.** Su esquematrón rechaza también el cero del IPSI,
  pero EDIFACT ya va con UBL: el de EDIFACT es de 2017 y tampoco se avisa de
  sus márgenes. Facturae no tiene esquematrón europeo.

**Lo que se hizo.**

- `Sintaxis.cero_que_rechaza_su_esquematron`: `{"L"}` en CII y vacío en las
  demás. `test_norma_oficial` lo lee de la vinculación de cada sintaxis
  evaluando la regla con un cero escrito, y comprueba que el texto de las seis
  reglas sigue diciendo «0 (zero) or greater than zero». Si el comité arregla
  CII, o rompe UBL, se pone en rojo.
- `IVA-CERO-ESQUEMATRON`, una NOTA por factura con los conceptos y las reglas
  que el esquematrón de CII levantaría. Corre también sin desglose, como las
  del tipo.
- La ficha nueva, y una frase en las de `BR-AF-05`, `06` y `07`, que es lo que
  buscará quien vea su CII rechazada.
- De 394 códigos a 395.

**En el corpus**, 157 facturas, 19 de ellas CII: no cambia nada, 1108
incidencias antes y después con el motor de la norma europea solo
(`en16931.validar`). Ninguna lleva IGIC.

**Provocado.** Once roturas, las once en rojo: CII deja de decir el IGIC, UBL
y EDIFACT lo dicen, Facturae sigue a otro, la nota sale también con el tipo
negativo, la nota es un aviso, la nota es el error de CII, solo las líneas, no
corre con desglose, no corre sin él, una ficha de `BR-AF` sin la frase, y el
comité que arregla CII.

**Lo que se vio de paso, y no se toca.** El commit que cerró la issue 519
cambia los nombres de las reglas en `master`. En UBL el IGIC pasa de `BR-AF`
a `BR-IG` y el IPSI de `BR-AG` a `BR-IP`, que es como los llama la norma. En
CII el cambio salió cruzado: `BR-AF` pasó a `BR-IP` y `BR-AG` a `BR-IG`, así
que allí la regla del IGIC (contexto de la categoría L, texto de IGIC) se
llama `BR-IP-05`. No estaba publicado ese día: era del hito 1.3.17, que salió
el 12-10-2026 (en «BR-IG y BR-IP sí existían», más abajo).
La copia fijada aquí es `b6c9e06` y sigue con `BR-AF` y `BR-AG`; el día que
se traiga la nueva, `test_norma_oficial` lo dirá, y habrá que decidir qué
código se enseña cuando UBL y CII no llaman igual a la misma regla.

## Los mensajes de la orden: nueve tablas que nadie medía

**Lo que había.** La Orden HAC/1028/2026 define nueve mensajes
`ApplicationResponse`, cada uno con su tabla y su `cbc:ResponseCode`: la
anulación de una factura o copia fiel (`CANCELINVOICE`, la segunda tabla del
anexo I) y los ocho del anexo II, el pago, el rechazo, el cobro y el impago con
sus bajas. Desde el 29-09-2026 una respuesta se reconocía y se le miraba la
forma y la firma, y el informe decía que su contenido no se miraba. Era
verdad, y era el paso 7 del plan.

**Reproducido** el 12-10-2026 sobre `26e9a5d`, con doce mensajes escritos aquí
y los esquemas de `web/paquete.zip`:

| Mensaje | En `26e9a5d` |
|---|---|
| una anulación, un pago y un cobro bien escritos | sin errores |
| la anulación sin su fecha, el pago sin la de efecto, el impago sin la suya | sin errores |
| el pago sin la fecha de vencimiento | sin errores |
| el pago sin el NIF ni el nombre del emisor | sin errores |
| el rechazo sin motivo, o con el motivo `03` | sin errores |
| la baja de un pago sin la fecha de la factura | sin errores |
| la anulación escrita como dice el BOE | `XSD-ORDEN`, y nada más |

De nueve rotos, ocho sin una queja. El informe no mentía, porque la columna
del contenido decía «Sin mirar», pero un mensaje sin la fecha de vencimiento
del pago, que es lo que el apartado 1 del artículo 7 obliga a comunicar, salía
sin una sola queja.

**Lo que se decidió, y por qué.**

- **Se reconocen por el código.** La orden no les da identificador de
  especificación: ninguna de las nueve tablas tiene fila para
  `cbc:CustomizationID`. Ninguno de los nueve códigos es de la UNCL 4343, la
  lista de Peppol, así que una respuesta de otra red sigue como estaba. Se lee
  letra a letra.
- **Las tablas salen del XML del BOE**, como el anexo I: `herramientas/mensajes.py`
  escribe `validador/mensajes_es.py` con la huella del XML, y
  `validador/mensajes.py` las lee fila a fila al importar. Una fila que no se
  sepa medir, un dato de la factura que deje de ser obligatorio o un mensaje
  nuevo hacen que no se importe.
- **Las erratas de escritura se arreglan y se cuentan**: un renglón partido
  detrás de una barra (16), un espacio donde va una barra (1) y una barra
  doble (1). Se cuentan también las celdas con dos rutas, cada una en su
  párrafo (8), que no son una errata (abajo). Si el BOE corrige una, la cuenta
  cambia y una prueba salta. Una celda que ocupa dos filas (`rowspan`) se pone en las
  dos, que es lo que se ve impreso.
- **Las dos de la anulación, leídas como el anexo II, y dichas.** La factura
  colgada de `cac:Response`, que no la admite, se busca en
  `cac:DocumentResponse`, donde la pone el anexo II, y también donde la pone
  la tabla (abajo). El nombre del vendedor
  dentro de `cac:PartyTaxScheme/cac:PartyLegalEntity` tiene dos arreglos de
  un paso, y se buscan los dos. Están preguntadas al buzón desde el
  07-10-2026, y la nota de cada anulación dice cómo se han leído.
- **El NIF, con el prefijo ES y sin él, y con cualquier `cac:TaxScheme`.**
  También está preguntado; hasta la respuesta no se da por mala ninguna forma.
- **Seis códigos**, de 395 a 401: `SPFE-MENSAJE-ALCANCE` (nota),
  `-FECHA`, `-VENCIMIENTO`, `-ESTADO`, `-MOTIVO` y `-FACTURA`. Lo que la tabla
  no prevé (`Duedate` por `DueDate`, un `cbc:StatusReason` libre) sale en
  aviso: puede ser una errata, pero un mensaje no está mal por llevar algo de
  más.
- **La frase del final** dice que se mide parte de lo que la orden pide a sus
  mensajes solo si a alguno se le midió, y de las demás respuestas sigue
  diciendo que su contenido no se mira. Sin esquema, una respuesta sigue saliendo SIN
  COMPROBAR aunque se le haya medido la tabla.

**Ahora**, los nueve rotos tienen su queja, y los nueve bien escritos salen
sin errores con la nota. En el corpus no cambia nada: de 169 ficheros (los
`.xml`, `.edi` y `.xsig` de las tres carpetas) se leen 157 y ninguno es una
respuesta; 1346 incidencias con las reglas y sin ellas, con el validador
entero (`factura.validar`) sin esquemas ni anclas. Con los esquemas salen
más, por las de forma, y no es la misma medida.

**Provocado.** Quince roturas, las quince en rojo: las reglas no corren, el
código se lee sin mayúsculas, la fecha no se pide, el vencimiento vale sin su
fecha, cualquier motivo vale, varias facturas en el anexo II, el NIF con ES no
vale, lo no previsto es un error, el nombre de la anulación en un solo sitio,
la anulación sin arreglar la factura (no se importa), la frase promete los
mensajes sin la nota, la frase dice de todas las respuestas que no, la celda
de dos filas no se arrastra, el BOE corrige la barra doble, y un mensaje sin
nombre (no se importa).

**Lo que no está medido.** Ningún mensaje real: los de las pruebas están
escritos aquí, con las tablas. El navegador se midió al publicar (al final).

**Lo que vieron el revisor de promesas y el auditor**, el mismo día, antes de
publicar. Todo reproducido antes de arreglarlo:

| Lo que pasaba | Ahora |
|---|---|
| un emisor con dos NIF buenos, el NIF-IVA y el NIF, daba «no es válido»: se juntaban en uno | se mira cada uno |
| una fecha para el vencimiento y la recepción, en el mismo `cac:Status`, pasaba sin queja | ERROR `SPFE-MENSAJE-ESTADO` |
| un `cbc:StatusReason` repetido en una fila `0..1`, sin queja | ERROR `SPFE-MENSAJE-ESTADO` |
| la anulación escrita como el BOE recibía «le faltan» con los tres datos en el fichero | se buscan también allí; la forma la dice `XSD-ORDEN` |
| un pago y un `AP` en un documento: la frase y la columna daban el contenido por mirado | se cuentan respuestas, no documentos |
| la frase decía «lo que la orden pide a sus mensajes», entero | «parte de», como con el anexo I |
| las seis quejas salían con la norma «Anexo I», también las del anexo II | «Anexo II» en las tres de estados, «Anexos I y II» en las otras |
| la nota decía que la Sede «todavía no lo ha sacado», sin fecha y sin mirarlo | dice lo que deja la orden a la Sede, y nada de la Sede |
| la nota daba el NIF solo como `BT-31`, «y lleva el prefijo» | el `BT-31` con el prefijo, o el `BT-32` sin él |
| la ficha de `SPFE-MENSAJE-ESTADO` ponía el vencimiento del impago en `cac:Status` | en el impago es la fecha del mensaje |
| la portada decía «lo que todavía no se mide», con esa lista vacía | «lo que no se mide», y los mensajes |
| el docstring y esta entrada contaban como errata las celdas con dos rutas | cada ruta va en su párrafo en el XML: no es una errata |

Y el auditor rompió `mensajes.py` sobre una copia, y once roturas pasaban la
suite entera: solo se medía la primera respuesta del documento,
solo la primera factura de la anulación, un NIF con `ES` y el control mal, el
NIF buscado también en `cac:PartyLegalEntity`, la fecha del vencimiento sacada
de otro `cac:Status`, un indicador repetido, la factura buscada dentro de
`cac:Response` en todos los mensajes y cuatro negativas de `_plan` (el motivo,
la fecha del mensaje y el vendedor que dejan de ser obligatorios, y dos grupos
de factura). Cada una tiene ahora su prueba.

**Provocado.** Veintitrés roturas, las veintitrés en rojo: once de la tabla
(todas menos la última, que es de un comentario), las siete del auditor que
eran de comportamiento, con la de `cac:Response` al revés (buscarla allí en
todos los mensajes), sus cuatro negativas de `_plan` y el indicador repetido
diciendo «cuál vale».

**Y las reglas de la factura**, el mismo día. El auditor rompió
`solucion_publica.py` sobre una copia, y cuatro roturas pasaban la suite
entera: solo el primer cargo de cada línea, `BT-119` solo en la primera
entrada del desglose, la copia fiel con `true` y no con `1`, y `BT-30` pedido
también con «LOC» sin «FC», que daba dos quejas por lo mismo. Reproducido:
las cuatro en verde.

Y dos reglas que no decían lo que la orden dice, también reproducidas:

| Lo que pasaba | Ahora |
|---|---|
| `BT-30` con «RM Madrid T.1 F.2», o con el NIF del comprador: sin una queja | ERROR con el NIF en `BT-32`, AVISO sin él |
| una propiedad «Color» en la línea, en ERROR | AVISO: la interconectada admite contenido adicional que cumpla la norma (apartado 3 del artículo 3) |
| la ficha de `SPFE-IMPUESTO-O-TASA`: «la norma europea no tiene nada de esto» | y el esquematrón de UBL del CEN avisa de la ruta de `BT-ES-22` (`UBL-CR-558`, comprobado en `EN16931-UBL-syntax.sch`: `flag="warning"`) |
| el comentario de `sintaxis.py`: «hoy es una», el IGIC en CII | el de EDIFACT rechaza también el cero, y no se dice |
| las cifras de 1106 y 1108 incidencias, sin decir con qué se midieron | con el motor de la norma europea solo, `en16931.validar` |
| `pyproject.toml`: «los 24 módulos van dentro del `.whl`» | «todos los módulos», que no se queda viejo |

**Provocado.** Once roturas, las once en rojo: las cuatro del auditor; `BT-30`
aceptando cualquier cosa, cualquier NIF, en ERROR también sin `BT-32`, sin
leer que la orden lo describe como el NIF y comparado con un NIF-IVA de otro
país; «INFO» otra vez en ERROR; y la ficha sin `UBL-CR-558`. En el corpus,
1346 incidencias antes y después: ninguna factura declara la solución pública.

**Visto en el navegador**, en www.glosa-e.com después de publicar `65a24ca`,
pegando el texto en la portada. El pago sin vencimiento: la forma sin errores
contra el esquema, ERROR `SPFE-MENSAJE-VENCIMIENTO` con la norma «Anexo II», la
nota con «Anexos I y II» y, en el contenido, «Parte de lo que la orden de la
solución pública pide a sus mensajes de anulación y de estado». El pago con su
vencimiento: sin errores, con la nota. Y la factura de la orden con «RM Madrid
T.1 F.2» en `BT-30`: ERROR `SPFE-NIF` y cuatro notas, lo que solo hace la
tanda de este día, así que la rueda servida es la nueva. Los tres, código a
código, lo mismo que `factura.validar` en la consola.

## BR-IG y BR-IP sí existían: la página decía que no

**Lo que había.** El 26-08-2026 las reglas del IGIC y del IPSI pasaron aquí
de `BR-IG-*` y `BR-IP-*` a `BR-AF-*` y `BR-AG-*`, al comprobarlas contra el
esquematrón oficial (el commit `6ef9804` no dice qué versión; la última
publicada era la 1.3.16, y la copia fija no llegó hasta el 13-09). El cambio
era bueno; lo que se contó de él, no. La ficha de `BR-AG-01`, que se publica
en la página, decía que `BR-IP-*` se había escrito «por analogía con el
intracomunitario (o sea, inventado)» y que una factura de Ceuta «recibía el
nombre de una regla que no existe en ninguna norma». La frase se fue copiando:
el 26-08 en el README, en la cabecera de `facturae.py` y en el comentario de
`iva.REGLAS`; el 06-09 en otro comentario de `iva.py`; el 12-09 en la ficha.
Además, en dos pruebas y en dos sitios de este fichero.

**Cómo se vio.** El 12-10-2026 salió la 1.3.17 del CEN, y la auditoría de lo
que trae miró la historia de los nombres en el repositorio oficial. El commit
`9995d37`, del 27-01-2017, se titula «Change rule name from BR-L to BR-IG and
BR-M to BR-IP». Leído en las 26 versiones publicadas, de etiqueta en
etiqueta:

| Versiones | UBL | CII |
|---|---|---|
| de la 1.0.0 (07-02-2018) a la 1.3.13 (08-10-2024) | `BR-IG` el IGIC, `BR-IP` el IPSI | `BR-AF` y `BR-AG` |
| de la 1.3.14 (15-04-2025) a la 1.3.16 | `BR-AF` y `BR-AG` | `BR-AF` y `BR-AG` |
| 1.3.17 (12-10-2026) | `BR-IG` y `BR-IP` | cruzados: `BR-IP` el IGIC |

En la 1.3.13, `$VATIG` es la categoría L y el texto de `BR-IG-01` dice
«IGIC». En EDIFACT el código es `BR-AF` y `BR-AG`, pero el texto de sus
mensajes dice `[BR-IG-01]` y `[BR-IP-01]` también en la 1.3.16 (en el
abstracto, que no viene en la copia fijada). Los nombres de la primera versión
de Glosa coincidían con los de UBL hasta 2024; lo que no salía de ningún sitio
era decir que no existían.

**Reproducido.** En producción, `/codigo-BR-AG-01` devolvía la frase el
12-10-2026. Y una prueba nueva, escrita antes de tocar nada, salió en rojo con
cinco frases en cuatro ficheros: `facturae.py`, `glosario.py`, dos de
`iva.py` y el README.

**Lo que se hizo.** La ficha dice ahora cómo se han llamado esas reglas en UBL,
en CII y en EDIFACT, y por qué aquí se usa `BR-AG-*`: es el nombre en la copia
oficial con la que se compara. La historia completa va en el comentario de
`iva.REGLAS`, y los demás sitios dejan de repetirla. Lo de `facturae.py` y el
README sigue diciendo por qué los códigos de Facturae son nuestros, sin el
ejemplo, que era falso. **No cambia ningún código**: el renombre a `BR-IG` y
`BR-IP` va con la tanda que traiga la 1.3.17, después de leer Search Console el
23-10 (para no mover 20 direcciones antes de esa lectura) y antes del 15-11,
cuando rige la lista VATEX nueva. La suite entera cazó una cosa más: la prueba
de las cifras con punto de las fichas leyó «1.3.13» como miles. Las cuatro
versiones que cita la ficha van en su lista, como el 2.5 de UBL.

**Lo que encontró el revisor de promesas**, antes del commit, y se cambió:

| Lo que decía el cambio | Lo que consta |
|---|---|
| el comentario de la prueba: el cambio de nombre fue el 13-09-2026 | el 26-08-2026 (`6ef9804`); el 13-09 llegó la copia fija |
| «al comprobarlo contra la 1.3.16» | el commit no dice la versión: se dice así |
| «desde 2017» | en el repositorio, desde 2017; en lo publicado, desde la 1.0.0, de 2018 |
| la ficha: «en CII fueron siempre `BR-AG-*`» | hasta la 1.3.16; en la 1.3.17 el IPSI es `BR-IG` en CII |
| la ficha y `iva.REGLAS`: UBL y CII | también EDIFACT, que Glosa valida |
| la ficha: «todavía no se ha traído», sin nada que la ate | fuera; la versión fijada la ata una prueba |
| el README: la prueba ve «se inventaron» | no lo veía, ni «un invento», ni el nombre y la frase en dos frases, ni lo que va detrás de una comilla de cierre |
| «en la última entrada», en tres sitios de este fichero | deja de ser cierto con la entrada siguiente: el título |
| «cada arreglo deshecho de uno en uno» | lo provocado eran frases nuevas: ahora se deshace de verdad (abajo) |

Y de paso, fuera de lo que se miraba: **la ficha de `BR-AF-01`, en
producción, contaba una «familia entera de seis reglas»**, y la copia trae
diez, de `BR-AF-01` a `BR-AF-10`, con su ficha cada una. Faltaban las tres que
piden identificar al vendedor y la de la cuota.

**Lo que hace que no vuelva.** Tres pruebas en `test_documentacion.py`:

- la primera lee cada módulo de `validador/` con `tokenize`, cadenas y
  comentarios juntos, y el README; los parte en frases sin cortar detrás de
  una comilla de cierre, y se niega si una frase nombra `BR-IG`, `BR-IP`, «IG
  e IP» o «IG/IP» y en ella o en la de al lado aparece «no exist…», «nunca
  exist…», «inexistente», «invent…», «no aparece en ninguna» o «por
  analogía», salvo que ahí mismo se diga que era falso;
- la segunda ata la ficha de `BR-AG-01` a la copia: tiene que decir «la
  1.3.16», y la huella fijada tiene que ser la de la 1.3.16;
- la tercera cuenta las reglas `BR-AF` de la copia y exige que la ficha de
  `BR-AF-01` diga ese número.

Las dos últimas se ponen en rojo el día que se traiga la 1.3.17, y eso es lo
que se quiere: esas fichas cuentan lo que trae la copia.

**Provocado**, con 19 roturas, cada una sola y con el fichero devuelto byte a
byte:

- **Deshecho de verdad.** Cada trozo cambiado en el validador y en el README,
  devuelto al texto de `425689d` de uno en uno: ocho trozos. Los seis que
  llevaban la frase falsa o las seis reglas, en rojo; la ficha de `BR-AG-01`
  pone en rojo dos pruebas, la de la frase y la de la copia. Los otros dos
  salen en verde, y es lo que toca: son la cifra de pruebas del README y
  quitar el párrafo nuevo.
- **Los huecos del revisor**, escritos donde nadie los había puesto: el nombre
  detrás de una comilla de cierre (en un módulo y en el README), «no existe»
  en la frase siguiente, «se inventaron», «un invento», «IG y IP» e «IG/IP».
  Los siete, en rojo.
- **Contado como historia falsa** («se dijo que BR-IG no existía, y era
  falso»): en verde, que es lo que se quiere.
- **La copia**: otra huella fijada, la ficha nombrando la 1.3.17 y una regla
  `BR-AF` más en la copia. Las tres, en rojo.

**Lo que no se toca.** Las fichas de `BR-AF-*` y `BR-AG-*` siguen en las
mismas direcciones hasta la tanda de la 1.3.17. En el corpus no cambia nada:
solo cambian textos.

## La copia fiel, contra la orden: siete términos sin fila

**Lo que había.** El 11-10-2026, al salir `cius_es` del XML del BOE, la tabla
de la copia fiel se quedó en 98 filas que nombraban 96 de los 116 términos
europeos de la orden. Siete términos que el borrador de abril no tenía no los
nombraba ninguna fila, y nada lo decía en rojo: el cepo de los destinos
compara con el anexo lo que cada fila nombra, y no ve lo que no nombra
ninguna. Dos filas seguían además con abril. La del NIF decía «llega igual» a
`BT-32` y `BT-48`, y la de la unidad de medida apuntaba a `BT-129`, que es la
cantidad. La nota `COPIA-LINEA-UNIDAD` lo repetía en su campo («el atributo de
BT-129 en la copia») y decía que en la copia la unidad no tiene campo propio;
la orden le da `BT-130`.

**Reproducido** el 13-10-2026. La prueba nueva, corrida contra la tabla de
`527ff7f`, sale en rojo con seis términos sin fila: `BT-30`, `BT-31`, `BT-47`,
`BT-130`, `BT-142` y `BT-167`. El séptimo, `BT-149`, es el que se deja vacío a
propósito, y en `527ff7f` ninguna fila decía por qué.

**Lo que se hizo.** Cada término, contra el esquema de Facturae 3.2.2 y el
texto de la orden:

| Término | Qué es en la orden | De dónde sale en Facturae | Fila |
|---|---|---|---|
| `BT-31` | el NIF-IVA del vendedor, con «VAT» y el prefijo ES | `TaxIdentificationNumber`, que solo lleva prefijo en las operaciones intracomunitarias | la del NIF, que pasa a «cortado de otra manera» |
| `BT-30` | el identificador de inscripción legal del vendedor; la orden lo describe como su NIF y lo pide cuando el NIF va en `BT-32` | el mismo `TaxIdentificationNumber`: por esa vía el número va dos veces | la del NIF |
| `BT-47` | el NIF del comprador, con «LOC» y «FC»; en la norma es su registro legal, y la orden lo reutiliza | `TaxIdentificationNumber` | la del NIF |
| `BT-130` | la unidad de medida, obligatoria | `UnitOfMeasure`, opcional y de otra lista | la de la unidad, que deja `BT-129` |
| `BT-142` | la base de un cargo, una tasa o un impuesto de la línea | la base de un impuesto de la línea que no es IVA; los cargos de Facturae no la llevan | nueva: ese impuesto va como cargo de la línea, con un código de la L9 que Facturae no tiene (su 07 vale para todos los impuestos especiales) |
| `BT-149` | la cantidad a la que se aplica el precio, opcional | ninguno: el precio de Facturae es el de una unidad | ninguna, a propósito, como `BT-154` |
| `BT-167` | el tipo de cambio para contabilizar el IVA, de la edición de 2026, sin ruta | `ExchangeRate` | nueva, en «no se sabe»: en qué elemento va y en qué sentido se lee lo dice `UNE-CEN/TS 16931-3-2:2026`, que aquí no está |

Quedan 100 filas que nombran 102 de los 116 términos. La fila de los cargos
de la línea dice además que la orden les pide `BT-ES-22`, un código de la L9,
y que para un cargo de Facturae, que no es un impuesto, es «RESTO».

Medido antes de escribirlo, sobre los ficheros Facturae de terceros que hay
aquí y solo en recuentos: ninguno escribe el prefijo de país en el NIF; tres
tienen alguna línea sin unidad, y en los tres sale `BR-23`; ninguno trae tipo
de cambio, ni en sus líneas otro impuesto que el 01 o el 02. Y el NIF copiado
tal cual en `BT-31` sale con `SPFE-NIF` en ERROR, medido con la factura de la
orden de las pruebas.

**Lo que se decidió sin preguntar, y por qué.**

- **`BT-149` se queda vacío y no tiene fila.** Es la regla que ya se aplicó a
  `BT-154`: un campo opcional sin origen no se rellena. La fila del precio
  dice por qué, y la prueba exige que alguna fila lo diga.
- **`BT-167` tiene fila aunque no se sepa escribir.** El dato está en
  Facturae; lo que falta es la especificación. Con la fila en «no se sabe»
  queda escrito qué falta, en vez de un hueco.
- **El NIF no saca nota.** Saldría en todas las facturas, y lo que puede salir
  mal (el prefijo, el `BT-30`) lo acusa `SPFE-NIF` en la copia.

**Provocado.** Nueve roturas de la tabla, en memoria: la unidad otra vez en
`BT-129`; el NIF otra vez con abril; sin la fila del tipo de cambio; sin la
del impuesto de la línea; `BT-149` nombrado en el precio; `BT-149` vacío sin
que ninguna fila diga por qué; el cargo de la línea sin «RESTO»; el tipo de
cambio sin la especificación que lo decide; y un término inventado en el
anexo. Las nueve, en rojo, y en verde sin romper nada. En disco, la nota con
`BT-129` en su campo: en rojo, y el fichero restaurado con la misma huella.

**Lo que se vio de paso, y no se toca aquí.** Las filas citan «las 14
facturas de aquí», y no son 14 facturas de terceros: son 13 ficheros Facturae
de terceros, uno repetido (12 facturas distintas), más el ejemplo publicado
`ejemplos/fe-0001.xml`, que es de aquí. Se reconstruyó contando: con esos 14
salen las 11 que traen unidad y las 18 líneas que la escriben, como dice la
fila. Las cifras de las filas nuevas no dependen de esa base. Rehacer las
demás es otra tanda.

## La copia fiel, contra la orden: los 33 campos españoles

**Lo que había.** Después de los siete términos, la tabla de la copia fiel
nombraba 102 de los 116 términos europeos y **ninguno de los 33 campos
españoles** de la orden (`BT-ES-` y `BG-ES-`). Cinco los citaba alguna fila en
su porqué (`BT-ES-10`, `BT-ES-16`, `BT-ES-17`, `BT-ES-22` y `BT-ES-25`), y
ninguno en su destino. Los dos cepos contaban con `B[TG]-\d+`, que no ve un
`BT-ES-`, y el de los destinos no miraba las filas de «la extensión
española». La cabecera del módulo decía que dónde se escriben en Facturae no
se adivinaba. Y la fila de los anticipos decía «llega igual» a `BT-113`.

**Reproducido** el 13-10-2026. El cepo de los términos, con la expresión
nueva y contra la tabla de `aa50e90`, sale en rojo con 35 sin fila: los 33
españoles, `BT-149` y `BT-154`.

**Lo que se hizo.** Cada campo, contra el esquema de Facturae 3.2.2 y el texto
de la orden:

| Campos | Qué son en la orden | De dónde salen en Facturae | Fila |
|---|---|---|---|
| `BT-ES-1` | el indicador de copia | de ninguno: `InvoiceClass` tiene su propia «copia», y es otra cosa | nueva, «lo pone quien copia»: siempre «true» |
| `BT-ES-2` | la fecha efectiva de pago, si se pagó antes de expedir o ese día | la de un anticipo, si la paga entera | la de los anticipos, que deja «llega igual» |
| `BG-ES-1` (`BT-ES-3` a `BT-ES-5`) | el tercero que expide la factura | `ThirdParty`, con `TE` | nueva, «cortado de otra manera», como el NIF y el nombre |
| `BG-ES-2` (`BT-ES-6` a `BT-ES-9`) | un impuesto que no es IVA, como cargo del documento | `TaxesOutputs` con otro código que 01, 02 o 03 | la del impuesto que no es IVA, que ahora da las dos maneras |
| `BT-ES-22` | el código de la L9 en un cargo de línea | el mismo impuesto; el código no se copia | la misma |
| `BT-ES-10` a `BT-ES-14` y `BG-ES-3` | la línea de un suplido, o la de un impuesto o tasa con su desglose | `ReimbursableExpenses`, que no distingue | la de los suplidos |
| `BT-ES-15` | la minoración en nombre de un tercero | de ninguno; las subvenciones no lo son | la de los huecos |
| `BT-ES-16` y `BT-ES-17` | la línea de la retención y su suma | `TotalTaxesWithheld` | la de las retenciones |
| `BG-ES-4` (`BT-ES-18` a `BT-ES-20`) | cada retención | `TaxesWithheld` | nueva, «en la extensión española» |
| `BT-ES-21` | el concepto de la retención, de la L5 | de ninguno: Facturae dice qué impuesto se retiene, no por qué | nueva, «lo pone quien copia» |
| `BT-ES-23` | la situación del inmueble, de la L6 | de ninguno | la de los huecos |
| `BT-ES-24` | el calificador de la clave de régimen: IVA, IGIC o IPSI | `TaxTypeCode` de la línea: 01, 03 y 02 | la de la categoría de la línea |
| `BT-ES-25` y `BT-ES-26` | la dirección del QR y el número de la autorización | de ninguno | la del QR y la autorización |
| `BT-ES-27` | el tipo de rectificativa, de la L2.A | `ReasonCode`, en parte | nueva, «de otra lista» |
| `BT-ES-28` | la modalidad, de la L2.B | `CorrectionMethod`, el 01 y el 02 | nueva, «de otra lista» |
| `BT-ES-29` | los importes rectificados, de la L2.C | de ninguno | nueva, «lo pone quien copia» |

Quedan 107 filas que nombran los 33 españoles y 104 de los 116 europeos; los
doce que no nombran son los grupos. Los cepos cuentan desde hoy con
`B[TG]-(?:ES-)?\d+`, y el de los destinos mira también las filas de «la
extensión española».

Medido antes de escribirlo, sobre los ficheros Facturae de terceros que hay
aquí y solo en recuentos: ninguno trae tercero, rectificativa, anticipos ni
subvenciones; seis retienen, y los seis lo escriben en las líneas y en el
documento, con el código 04 dos veces, el 05 tres y el 03 (el IGIC) una; dos
traen suplidos y dos importes retenidos; ninguno, un impuesto que no sea el
01 o el 02; y todos son `OO`.

**Lo que se decidió sin preguntar, y por qué.**

- **`BT-ES-1` tiene fila aunque sea siempre lo mismo.** La trampa es
  `InvoiceClass`, que distingue el original de la copia de la factura: quien
  copie campo a campo escribirá «false» para un `OO`.
- **El tercero, «cortado de otra manera» y no «llega igual».** Lleva el NIF y
  el nombre, y a los dos les pasa lo mismo que en las partes.
- **Las subvenciones no son una minoración.** La orden tiene un grupo que
  resta del total a pagar, y es el sitio donde un conversor las metería;
  minora lo que se cobró en nombre de otro, y eso la factura no lo dice. La
  fila de las subvenciones sigue en «no tiene sitio» y dice por qué.
- **`BT-149` y `BT-154` pasan a la fila de los huecos.** Por la mañana se
  dejaron sin fila, con la prueba apartándolos en una lista; con los huecos
  españoles en la misma fila, el cepo se queda sin excepciones. Lo que se
  decidió entonces (dejarlos vacíos) no cambia.
- **Del motivo de la rectificativa se traduce solo lo que el código dice.**
  El 82, el 83 y el 84 son el artículo 80, apartados uno y dos (R1), y el 85
  el concurso del 80.3 (R2). Del 01 al 16, el 80 y el 81 dicen qué dato o
  qué cálculo estaba mal y no por qué, que es lo que separa el R1 del R4.
- **Los importes retenidos siguen en «no se sabe»**, ahora apuntando a
  `BG-ES-4`: su lista de conceptos acaba en «Otros», y no dice si eso abarca
  lo que no es una retención fiscal.

**Provocado.** Contra la tabla de `aa50e90`, en rojo nueve de las diez
pruebas; la de los destinos sigue en verde, y es lo esperado: aquella tabla
no nombraba ningún campo español con número, así que no había nada mal que
cazar. Por eso se rompió aparte: una fila de la extensión española que nombra
un `BT-ES-99`, en rojo. Y quince roturas más, en memoria: sin la fila del
tercero; sin la del indicador de copia; `BT-149` fuera de los huecos; el
calificador fuera de la categoría de la línea; esa fila sin «IPSI»; el
impuesto que no es IVA sin decir que se cuenta dos veces; los anticipos otra
vez «llega igual»; el motivo de la rectificativa sin el R3; el método que
traduce el 02 por una D; las subvenciones sin decir por qué no son «MINO»; el
tercero confundido con el destinatario; y tres listas del anexo movidas (la
L5 con un supuesto más del IRPF, la L2.A con un R5 y la L3C con otro
calificador). Todas en rojo, y las diez en verde sin romper nada.

**Lo que se vio de paso, y se arregló aquí.** Dos frases de la tabla que ya
no eran verdad. La del tipo de factura decía que las 14 de aquí son 380, y
una la expide el destinatario (`RE`): es una 389. Y la del nombre comercial
contaba `BT-30` y `BT-47` entre los identificadores que el anexo no recoge,
cuando la orden los recoge para el NIF desde el 05-10-2026; la comprobación
de los destinos no lo veía porque los nombraba en el porqué y no en el
destino. La base de «las 14» sigue sin rehacer en las filas viejas.

## La respuesta del buzón del 13-10-2026: lo que cambia, y una frase de más

Dos correos de la AEAT el mismo día contestaron las dos consultas pendientes
(el detalle, en el README, en la sección de la consulta del 07-10-2026). Seis
reglas cambian de gravedad o nacen:

| Qué | Antes | Desde el 13-10-2026 |
|---|---|---|
| `ProfileID` del BOE, con `ubl:` | limpio | AVISO de `SPFE-PROCESO` |
| `ProfileID` del ejemplo, sin `ubl:` | NOTA | limpio |
| Valor de L7, L8 o L10 sin su calificador | limpio | AVISO de `SPFE-CALIFICADOR`, código nuevo |
| NIF-IVA del comprador sin ES | AVISO | ERROR de `SPFE-NIF` |
| Un código de L2.C repetido en `RECT:IMPORTES` | NOTA con cuatro o cinco, nada con dos o tres | AVISO de `SPFE-RECTIFICATIVA` |
| Nombre del emisor de una anulación solo en `cac:PartyTaxScheme/cbc:RegistrationName` | limpio | AVISO de `SPFE-MENSAJE-FACTURA` |

Las facturas de prueba se escribieron de nuevo con el calificador delante,
que es la forma que vale: con el valor solo, 40 pruebas salían en rojo por el
AVISO nuevo, y casi todas por la misma `REGI` de la factura base.

**La frase de más.** El primer borrador de estos mensajes decía que la AEAT
corrige el `ProfileID` en el anexo que publicará en su Portal de
Desarrolladores. No lo dijo: dijo que vale sin `ubl:`, y el anexo 2.0 que
mandó ese mismo día todavía lo lleva con él. Se vio al medir el PDF, y la
prueba del AVISO comprueba ahora que el mensaje no nombra el Portal. Es el
mismo cuidado que pide la tesis: lo que se atribuye a otro tiene que ser lo
que dijo.

**Provocado.** Cada regla, rota a mano y con su prueba en rojo: el `ProfileID`
del BOE otra vez limpio; sin la negativa de la fila `BT-23`; el nombre de la
anulación callado, y el aviso aunque el nombre esté donde va; `SPFE-CALIFICADOR`
fuera de la lista de reglas, sin mirar L8, sin mirar L10, en ERROR, y sin
apuntar en `tests/fichas_publicadas.txt`; el código repetido callado, sin la
negativa de la L2.C, y tres códigos distintos tomados por repetidos; y el
comprador otra vez en AVISO. Trece roturas, trece en rojo.

## La D.93A: dos segmentos que cerraban la línea

Antes de ofrecerle a un proveedor EDI leer sus INVOIC D.93A, había que
comprobar que Glosa-e los lee enteros. El corpus trae cuatro mensajes D.93A:
tres EANCOM 93 (`EAN007`) de proveedores de bibliotecas y uno `EDIT30`. Los
cuatro pasaban: se partían, cuadraba el `UNT` y salían sus once líneas con su
importe. Eso no dice nada de lo que esos cuatro no usan.

Así que la tabla de grupos se contrastó con la estructura entera del INVOIC
D.93A, sacada de tres fuentes que coinciden: la gramática D.93A de `bots-edi`
(leída con `ast`, sin ejecutarla) y el directorio que publican edifactory.de y
Stylus Studio. El de UNECE no se pudo abrir: pide una verificación contra
bots. Salieron dos huecos:

| Segmento | Dónde lo pone la D.93A | Qué pone ahí la D.96A |
|---|---|---|
| `QVA`, diferencias de cantidad | suelto en la línea | `QVR` |
| `API`, información adicional del precio | en el grupo del precio | `APR` |

**Reproducido** con una factura D.93A inventada que pasaba limpia. Con un
`QVA`, la línea se quedaba sin importe y sin IVA, y salían BR-24, BR-26 y
BR-CO-04. Con un `API`, sin IVA, y salía BR-CO-04. Es el mecanismo del `PAC`:
lo que no está en la tabla cierra el grupo, y lo de detrás se va a la cabecera.

**Arreglado** con los dos en la tabla. Un segundo lector, que coloca cada
segmento según la gramática, da el mismo grupo que Glosa-e en los 247
segmentos de los cuatro mensajes reales y en los 24 de la inventada, salvo dos
`RFF` de línea (abajo). Las posiciones de los datos que leen las reglas (`BGM`,
`DTM`, `NAD`, `RFF`, `CUX`, `LIN`, `IMD`, `QTY`, `PRI`, `MOA`, `TAX`, `ALC` y
`FTX`) son las mismas en la D.93A; lo que cambia está en datos que ninguna
regla lee.

**Provocado.** Con el arreglo quitado de `edifact.py`, cuatro pruebas en rojo:
para cada segmento, la línea pierde el importe y el IVA, y la factura da
ERROR. Los controles, que sacan el segmento de la tabla dentro de la prueba,
dejan la línea sin importe.

**Lo que queda.** Un `RFF` detrás del `MOA` de una línea se cuelga del `MOA`, y
no de la línea, porque la tabla no mira el contexto: detrás del `MOA` de los
totales, el `RFF` sí es suyo. Ninguna regla lee el `RFF` de una línea. Pasa en
2 de esos 247 segmentos, y en 9 de los 46.949 de los 258 mensajes D.96A.

**Lo que no está probado.** Ninguno de los cuatro mensajes es de un emisor
español: un EANCOM 93 escrito con la guía de AECOC no se ha visto nunca. Y de
un intercambio con varias facturas se valida la primera, con el AVISO
`EDI-VARIOS-MENSAJES`.
