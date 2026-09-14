# De dónde sale esta carpeta

Copia sin tocar de <https://github.com/ConnectingEurope/eInvoicing-EN16931>, commit `b6c9e06a59812fb1a83585da40923b3678a649ad`.
No la ha escrito este proyecto y no se edita a mano: se rehace con
`python -m herramientas.norma_oficial <commit>`.

- 279 ficheros de pruebas unitarias: `test/Invoice-unit-UBL`, `test/CreditNote-unit-UBL`, `test/cii`.
- `EN16931-model.sch` y `EN16931-UBL-codes.sch`, de `ubl/schematron/`.
- `EN16931-CII-codes.sch` y `EN16931-EDIFACT-codes.sch`: las listas de
  códigos sobre los elementos de CII y de EDIFACT.
- `EN16931-UBL-model.sch`, `EN16931-CII-model.sch` y
  `EN16931-EDIFACT-model.sch`: la vinculación de cada sintaxis, con las
  expresiones que se evalúan.
- `LICENSE.txt`: European Union Public Licence 1.2, la licencia de
  todo lo anterior.

Huella del contenido (SHA-256, finales de línea normalizados):
`9359948d767adf8cc86c21243e2d7f87159b9c3e408f09b1dcfde0a044b6187d`
