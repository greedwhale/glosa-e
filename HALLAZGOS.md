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
