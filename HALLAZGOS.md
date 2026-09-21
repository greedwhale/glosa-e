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
árbol de `ejemplos/` de `9601360` con el validador de hoy y se comparó queja a
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
antes (ea91466)   192,5 ms        ahora   179,4 ms
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
