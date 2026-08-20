# Factura-e

Validador de facturas electrónicas españolas y control de plazos de estados,
según el RD 238/2026.

## Estado actual

| Módulo | Qué hace | Estado |
|---|---|---|
| `validador/nif.py` | Valida NIF, NIE y CIF con sus dígitos de control | Terminado |
| `validador/calendario.py` | Días hábiles españoles y plazo de 4 días de los estados | Terminado |
| `validador/formato.py` | Detección de formato y versión (Facturae, UBL, CII, EDIFACT) | Terminado |
| `validador/en16931.py` | Validación XSD + Schematron contra EN 16931 | Pendiente |
| `validador/informe.py` | Traducción de errores BR-* a castellano llano | Pendiente |

65 tests, todos en verde.

```bash
.venv/Scripts/python.exe -m pytest -q
```

## Lo que la norma exige (verificado)

Del RD 238/2026, de 25 de marzo:

- **Formatos estructurados admitidos**: Facturae, UBL, EDIFACT o CII.
- **Formato de referencia**: la norma europea **EN 16931**.
- **Sintaxis de referencia de la solución pública**: **UBL**.
- **Código único por factura**: combina NIF del emisor, número y serie, y fecha
  de expedición.
- **Estados de factura**: el destinatario debe comunicar al emisor, en un
  máximo de **4 días hábiles** (excluidos sábados, domingos y festivos
  nacionales): la aceptación o el rechazo comercial, y el pago efectivo
  completo con su fecha.
- **El silencio equivale a aceptación**: la ausencia de rechazo expreso se
  entiende como aceptación de la factura.
- **Estados opcionales**: pago parcial, cesión a terceros, aceptación o rechazo
  parcial. No afectan al cómputo del plazo legal de pago.
- **Prórroga para los pequeños**: autónomos y entidades con ingresos por debajo
  de 8 millones de euros tienen doce meses adicionales para la obligación de
  informar estados. Hasta entonces es voluntaria.
- **Solución pública gratuita**: la AEAT ofrece una plataforma en su sede
  electrónica para quienes facturan menos de 8 millones.

## ⚠️ Corrección importante sobre las fechas

**Las fechas que se citan por ahí no están confirmadas.** Al contrastar
fuentes encontré versiones incompatibles: unas dicen 1 de enero de 2027 para
empresas y 1 de julio de 2027 para autónomos; otras hablan de octubre de 2027
y octubre de 2028; otras incluso de enero de 2026.

Lo que sí parece sólido y explica la discrepancia:

> Los plazos **empiezan a contar desde la entrada en vigor de la Orden
> Ministerial técnica**, que todavía no se ha publicado y se espera para
> finales de 2026.

Consecuencias prácticas para este proyecto:

1. **La fecha límite es real, pero aún no está fijada.** No prometas fechas
   concretas a nadie hasta que salga la Orden Ministerial.
2. **La especificación técnica tampoco es definitiva.** La Orden Ministerial
   concretará los requisitos del sistema. Construir hoy el producto completo de
   cumplimiento sería prematuro.
3. **Lo que sí es seguro construir ahora** es justo lo que hay hecho: reglas que
   no dependen de esa orden. Los dígitos de control del NIF llevan décadas sin
   cambiar; el cómputo de días hábiles tampoco va a cambiar; y las reglas
   Schematron de EN 16931 son estables y de código abierto.

## Decisiones de diseño

**Los festivos son un dato, no una constante.** El calendario laboral que
publica el BOE cada año puede trasladar festivos que caen en domingo, y las
comunidades autónomas añaden los suyos. Por eso `Calendario` acepta
`festivos_extra` y no hay una lista enterrada en el código.

**Los mensajes de error van en castellano llano.** La validación EN 16931 son
955 reglas con códigos tipo `BR-CO-10`, y ese es exactamente el motivo por el
que la gente paga a alguien que se lo traduzca. Cada `Resultado` lleva un campo
`motivo` que explica qué falla y qué debería poner en su lugar.

**El día de partida no cuenta en los plazos.** Si recibes una factura el lunes
y el plazo es de cuatro días hábiles, vence el viernes.

**La versión no se deduce solo del namespace.** Facturae cambió de convención
de namespace entre versiones, y hay documentación que se contradice sobre la
3.2.1: unas fuentes dan `facturae.es/Facturae/2014/v3.2.1/Facturae` y otras
`facturae.gob.es/formato/Versiones/Facturaev3_2_1.xml`. Se aceptan las dos, se
usa el namespace solo para identificar la familia, y la versión se toma del
campo `SchemaVersion` del propio documento. Si el namespace es desconocido pero
la raíz se llama `Facturae`, se reconoce igual y se avisa.

**El parser está endurecido.** El servicio va a recibir XML de terceros, así
que se parsea con `resolve_entities=False` y `no_network=True`. Sin eso, un XML
con una entidad externa podría leer ficheros del servidor. Hay dos tests que lo
comprueban, y el de XXE verifica primero que el documento **sí** se parsea, para
que la comprobación de fuga no pueda pasar en vacío.

## Siguiente paso

`validador/en16931.py`: enchufar los artefactos oficiales de validación de
CEN/TC 434 — XSD para la forma y Schematron para las reglas de negocio. Son
955 reglas y ahí es donde se produce la mayoría de los rechazos.

Después, `informe.py`: traducir códigos como `BR-CO-10` a una frase que diga
qué falta y dónde. Esa traducción es el producto; las reglas son de todos.

## Fuentes

- [RD 238/2026 en el Observatorio de Contratación Pública](https://obcp.es/noticias/real-decreto-2382026-de-25-de-marzo-por-el-que-se-desarrolla-el-sistema-de-facturacion)
- [Qué cambia de verdad tras el RD 238/2026 — ASSET](https://asset.es/factura-electronica-b2b-en-espana-que-cambia-de-verdad-tras-el-rd-238-2026/)
- [Guía RD 238/2026: estados y plazos de pago](https://www.lealtadis.es/factura-electronica-b2b-estados-pago-pymes/)
- [Artefactos oficiales de validación EN 16931 (CEN/TC 434)](https://github.com/ConnectingEurope/eInvoicing-EN16931)
