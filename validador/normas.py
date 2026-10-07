# -*- coding: utf-8 -*-
"""De qué norma sale cada código, en un solo sitio.

Por qué existe
--------------
Esto estaba escrito dos veces: `factura.origen`, que pone la etiqueta al lado
de cada queja del informe, y `pagina_incidencias._norma`, que la pone en la
ficha de cada código del catálogo publicado. El comentario de la segunda decía
«el mismo reparto que `factura.origen`, pero por prefijo», y explicaba por qué
se copiaba: importar `factura` arrastra lxml y el catálogo entero para
contestar una pregunta que es una tabla de prefijos.

La razón era buena y el resultado no: **el 15-09-2026 los dos repartos no
decían lo mismo en 16 de los 371 códigos**. Los doce `IVA-*` salían en la
página como «Ley del IVA» —o sea, que lo exige una ley— cuando en el informe
salían, con razón, como criterio propio; `PERFIL-SIN-EN16931`, `SIN-SOPORTE` y
`VALIDADOR-SE-ATRAGANTA` caían en el informe en un cajón que se leía «Formato»;
y `ANCLAS-SIN-RENOVAR` salía como «Formato» en el informe y como firma en la
página. Lo que decide si una queja es de una norma o es una opinión nuestra no
puede depender de dónde la leas.

Así que la tabla vive aquí, en un módulo sin dependencias —ni lxml, ni
catálogo, ni nada—, para que las dos puedan usarla sin arrastrar nada. Lo
guarda `tests/test_pagina_incidencias.py`, que compara los dos caminos código
a código sobre el catálogo entero.

La etiqueta se escribe una sola vez y se lee en dos sitios: en el informe, al
lado del código —`[IVA-TIPO · De la casa]`—, y en la ficha de la página, bajo
«Norma». Por eso empieza en mayúscula: en la ficha es un título.
"""

from __future__ import annotations

# Lo que se dice cuando ninguna norma lo exige. Es la respuesta por defecto, y
# es la honrada: si no se sabe de qué norma sale una queja, lo que no se puede
# hacer es dar a entender que sale de alguna.
CASA = "De la casa"
_DETALLE_CASA = "no lo exige ninguna norma concreta, es criterio de este validador"

EUROPEA = "EN 16931"
ESPANOLA = "RD 238/2026"
# El contenido mínimo de la solución pública. No es el real decreto: es el
# anexo I de la Orden HAC/1028/2026. Hasta el 07-10-2026 la etiqueta decía
# «Anexo I (borrador)», y desde el BOE del 05-10-2026 eso ya no es verdad.
# Tampoco puede decir la orden a secas mientras queden reglas que miden lo que
# solo está en el borrador de abril —el recargo de equivalencia, el grupo de
# entidades—: pondría el nombre de la orden a quejas que la orden no hace. Así
# que dice el anexo, sin versión, y la nota SPFE-BORRADOR de cada factura dice
# con qué se ha medido. Cuando todas las reglas midan la orden, la etiqueta
# podrá nombrarla.
SOLUCION_PUBLICA = "Anexo I"
FORMA = "Esquema XSD"
NACIONAL = "Formato Facturae"
SELLO = "Firma electrónica"
# La norma que manda en la sintaxis de EDIFACT: cómo se separan los segmentos,
# y sobre todo las cuentas del sobre.
SINTAXIS_EDI = "ISO 9735"

# Prefijo -> (etiqueta, de qué se trata). El orden importa solo en que el
# primero que encaja gana; hoy no hay prefijos que se solapen.
#
# «REVOCA» y no «REVOCACION-» a propósito: el código de la anulación
# confirmada es `REVOCADO`, a secas, y sin esto salía en el cajón de por
# defecto. Lo mismo le pasaba a todo lo de los sellos de tiempo, que es lo
# contrario de un problema de formato: es de lo que cuelga la fecha de la firma.
NORMAS: tuple[tuple[str, str, str], ...] = (
    ("BR-", EUROPEA, "la norma europea de factura electrónica"),
    ("CU-", ESPANOLA, "el real decreto español del código único"),
    # «O, en las reglas que todavía no…»: con la orden a secas, la ficha de
    # SPFE-RECARGO-DE-EQUIVALENCIA, que solo existe en el borrador, decía «De
    # dónde viene: el anexo I de la Orden HAC/1028/2026» dos líneas por debajo
    # de decir que la orden ya no tiene esa línea. Lo vio el revisor de
    # promesas el 07-10-2026, antes de publicar.
    ("SPFE-", SOLUCION_PUBLICA,
     "el contenido mínimo de las facturas de la solución pública: el anexo I de la "
     "Orden HAC/1028/2026 o, en las reglas que todavía no se han puesto al día, el "
     "del borrador de abril"),
    ("XSD-", FORMA, "el esquema oficial del formato"),
    ("FE-", NACIONAL, "la especificación española de Facturae"),
    ("EDI-", SINTAXIS_EDI, "la sintaxis de EDIFACT"),
    ("FIRMA-", SELLO, "eIDAS y las normas ETSI de firma"),
    ("CADENA-", SELLO, "eIDAS y las normas ETSI de firma"),
    ("REVOCA", SELLO, "eIDAS y las normas ETSI de firma"),
    ("CONFIANZA-", SELLO, "eIDAS y las normas ETSI de firma"),
    ("SELLO-", SELLO, "eIDAS y las normas ETSI de firma"),
    ("ANCLAS-", SELLO, "eIDAS y las normas ETSI de firma"),
    # El NIF del receptor no lo firma el RD 238/2026 —el código único solo usa
    # el del emisor—, así que no puede salir con su etiqueta.
    ("NIF-", CASA, "no lo exige ninguna norma de las anteriores"),
    # Las de IVA son nuestras. La página las daba por «Ley del IVA», que es
    # decir que las exige una ley: el desglose lo pide EN 16931 con sus BR-*, y
    # lo que comprueban estas —tipos vigentes, categorías, redondeos— es
    # criterio de la casa.
    ("IVA-", CASA, "el desglose de impuestos, con criterio de este validador"),
    # La copia fiel la manda el real decreto, pero **la correspondencia entre
    # sintaxis no la publica nadie**: preguntada por escrito, la AEAT contestó
    # el 17-09-2026 que es cosa de cada plataforma privada. Así que estas notas
    # salen de leer las fórmulas del esquema de Facturae y el anexo, y eso es
    # criterio de la casa mientras no haya un texto que las firme.
    ("COPIA-", CASA, "la correspondencia con la copia fiel, que no publica nadie"),
)


def norma(codigo: str) -> tuple[str, str]:
    """La etiqueta de la norma de un código, y de qué trata esa norma."""
    for prefijo, etiqueta, detalle in NORMAS:
        if codigo.startswith(prefijo):
            return etiqueta, detalle
    return CASA, _DETALLE_CASA
