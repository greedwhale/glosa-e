# -*- coding: utf-8 -*-
"""Qué significa cada código de incidencia, en castellano.

`codigos.py` saca del código fuente **qué códigos existen**. Esto dice **qué
quieren decir**, y es lo único de las dos cosas que hay que escribir a mano: el
mensaje del informe se compone en tiempo de ejecución con los datos de la
factura, así que no hay ninguna frase fija que extraer.

La regla de la casa se aplica igual aquí: **lo que no está explicado se dice
que no lo está**. Un catálogo que rellena huecos con paráfrasis del propio
código —«CU-07: no cumple la regla CU-07»— es peor que uno con huecos, porque
el hueco al menos se ve. Los que faltan salen contados en la página.

Dos niveles, y por qué
----------------------
Por **familia**, porque el prefijo dice de dónde viene la exigencia y eso ya
contesta la mitad de la pregunta: un `BR-` lo pide la norma europea y no este
validador, y saberlo cambia a quién hay que reclamar.

Por **código**, cuando hay algo que decir que no se deduce de la familia. No
están todos, y los que están son los que se han escrito con el módulo delante.
"""
from __future__ import annotations

__all__ = ["FAMILIAS", "CODIGOS", "explicar"]

# --- Qué es cada familia ---------------------------------------------------

FAMILIAS: dict[str, str] = {
    "BR": (
        "Reglas de negocio de la norma europea EN 16931. No las pone este "
        "validador: las pone la norma, y son las mismas para cualquier factura "
        "electrónica europea. Si una salta, la factura no es conforme a "
        "EN 16931 aunque el fichero esté perfectamente formado."
    ),
    "CU": (
        "El código único de factura del Real Decreto 238/2026, la parte "
        "española. Es el identificador que hace que una factura no se pueda "
        "sustituir por otra sin que se note, y tiene reglas propias de "
        "formato, de contenido y de fecha."
    ),
    "XSD": (
        "La forma del fichero, comprobada contra el esquema oficial de su "
        "formato. Es lo primero que se mira: si el documento no cuadra con su "
        "propio esquema, lo que digan las reglas de negocio sobre él vale poco."
    ),
    "FE": (
        "Reglas propias de Facturae, el formato español. No salen de EN 16931 "
        "sino de la especificación de Facturae y de lo que la Administración "
        "espera de ella."
    ),
    "EDI": (
        "Sintaxis EDIFACT. Es el cuarto formato de la ley y el único que no es "
        "XML: se lee por segmentos separados por apóstrofos, con sus propias "
        "formas de venir roto."
    ),
    "IVA": (
        "El desglose de impuestos: que las bases, los tipos y las cuotas "
        "cuadren entre sí y con los totales. Cuando la comprobación viene de "
        "la norma europea sale como `BR-`; estas son las que no."
    ),
    "NIF": (
        "El número de identificación fiscal: su forma y su dígito de control. "
        "No lo exige el RD 238/2026 —el código único solo usa el del emisor—, "
        "así que esta comprobación es de la casa y se dice."
    ),
    "FIRMA": (
        "La firma electrónica del documento: que exista, que la aritmética "
        "cuadre y que el documento no se haya tocado después de firmarlo. "
        "Responde a una sola pregunta: ¿esto es lo que se firmó?"
    ),
    "CADENA": (
        "De quién es el certificado que firma. Se sigue la cadena hacia arriba "
        "hasta un ancla de confianza instalada. Que la firma cuadre no dice "
        "nada de quién la hizo: eso lo dice la cadena."
    ),
    "REVOCACION": (
        "Si anularon el certificado antes de firmar con él. Es la única "
        "pregunta que un certificado no puede contestar sobre sí mismo, y hace "
        "falta una prueba de fuera: una lista de revocación (CRL) o una "
        "respuesta OCSP de las que el propio documento trae dentro."
    ),
    "REVOCADO": (
        "El certificado consta anulado. No es un problema de formato ni de la "
        "lista: es el resultado de haberla leído y haberlo encontrado dentro."
    ),
    "SELLO": (
        "Los sellos de tiempo. Importan más de lo que parece: la fecha de "
        "firma la escribe quien firma, y sin un sello de un tercero no hay "
        "forma de comprobarla. De esa fecha cuelgan la caducidad del "
        "certificado y su revocación."
    ),
    "CONFIANZA": (
        "Notas que declaran **con qué** se ha comprobado algo: qué ancla, de "
        "qué lista, de qué día. No son quejas. Existen porque «no consta "
        "anulado» sin decir según qué prueba es un tic verde con más letras."
    ),
    "ANCLAS": (
        "El estado del conjunto de anclas de confianza que trae la página. Una "
        "lista vieja sigue creyendo a autoridades a las que el Estado ya les "
        "retiró la cualificación."
    ),
    "SIN": (
        "No se ha podido mirar el documento: no se reconoce el formato, o el "
        "fichero no es una factura. Es distinto de «está mal», y se dice "
        "aparte para que no se confunda con un aprobado."
    ),
    "VALIDADOR": (
        "Algo que le ha pasado al propio validador, no a la factura."
    ),
}

# --- Lo que no se deduce de la familia -------------------------------------

CODIGOS: dict[str, str] = {
    # Revocación: lo que más se malinterpreta, porque «no se ha comprobado» se
    # lee como «está bien» si no se dice con todas las letras que no lo es.
    "REVOCADO": (
        "El certificado que firma estaba ya anulado el día que se firmó. Una "
        "firma hecha con un certificado anulado no vale, aunque la aritmética "
        "de la firma cuadre."
    ),
    "REVOCACION-COMPROMISO": (
        "Lo anularon porque la clave privada acabó en malas manos. Este motivo "
        "mira hacia atrás y no sólo a lo que se firmara después de la denuncia: todo lo que esa clave firmó pasa a ser "
        "sospechoso, también lo anterior a la denuncia, porque quien la robó "
        "pudo firmar con fecha atrasada."
    ),
    "REVOCACION-SUSPENDIDO": (
        "Está en suspenso, que no es lo mismo que anulado: una suspensión "
        "puede levantarse y entonces el certificado vuelve a valer. Hoy no "
        "vale, y la prueba no dice desde cuándo dejó de valer."
    ),
    "REVOCACION-POSTERIOR": (
        "Lo anularon después de la fecha de firma, y ese después lo es todo. Sale como aviso cuando "
        "esa fecha la declara quien firma —que es fiarse de su palabra— y como "
        "nota cuando un sello de tiempo de un tercero acredita que la firma ya "
        "existía. Es el mismo hecho con dos valores distintos de prueba."
    ),
    "REVOCACION-SIN-COMPROBAR": (
        "No se ha podido saber si está anulado, y se dice cuál es la lista que "
        "falta y dónde dice el propio certificado que está. Este validador no "
        "sale a la red a buscarla: bajarla es un acto explícito de quien usa "
        "la herramienta."
    ),
    "REVOCACION-SOLO-OCSP": (
        "La autoridad no publica lista de revocación, solo un servicio de "
        "consulta OCSP. Preguntarle lleva dentro el número de serie del "
        "certificado, o sea que le diría a la autoridad qué factura se está "
        "mirando y cuándo. Esa consulta no se hace desde aquí."
    ),
    "REVOCACION-OCSP-NO-VALE": (
        "El documento traía respuestas OCSP y ninguna sirve para este "
        "certificado, y se dice por qué: porque no habla de él, porque no la "
        "firma quien puede firmarla, porque el respondedor contestó «unknown» "
        "—que no es «está bien»— o porque se miró antes de la firma y su "
        "propio plazo no llegaba hasta ella."
    ),
    "REVOCACION-LISTA-VIEJA": (
        "No aparece anulado, pero la lista que lo dice ya venció y desde "
        "entonces puede haber anulaciones que no recoge. No aparecer en una "
        "lista caducada no es lo mismo que estar vigente."
    ),
    "CONFIANZA-REVOCACION": (
        "Nota: no consta anulado ningún certificado de la cadena, y se declara "
        "contra qué se ha comprobado —qué lista o qué respuesta OCSP, de quién "
        "y de qué día—. Una prueba solo responde por el momento en que se hizo."
    ),
    "CONFIANZA-ANCLA": (
        "Nota: a qué autoridad llega la cadena, por qué se cree a esa "
        "autoridad y con qué huella. Quien lee el informe no eligió las "
        "anclas, así que hay que decirle de dónde salen."
    ),
    "CADENA-DESCONOCIDA": (
        "El certificado no lleva a ninguna autoridad conocida. Puede ser que "
        "falte un certificado intermedio o que no lo emitiera nadie de fiar: "
        "no es lo mismo, y desde aquí no se distingue."
    ),
    "CADENA-RETIRADA": (
        "La cadena llega a una autoridad que ya no era cualificada cuando se "
        "firmó. La firma puede ser auténtica; lo que no la ampara es la lista "
        "de confianza del Estado."
    ),
    "CADENA-ROTA": (
        "Un eslabón de la cadena no cuadra: o la firma del certificado no la "
        "hizo quien dice, o quien lo emitió no era una autoridad."
    ),
    "CADENA-SIN-ANCLAS": (
        "No hay anclas de confianza instaladas, así que solo se ha comprobado "
        "que la firma cuadra con su certificado. Un certificado que el "
        "remitente se haya inventado pasaría igual."
    ),
    "BR-01": (
        'El campo donde la factura declara a qué especificación se ajusta: '
        'el CustomizationID en UBL, el '
        'GuidelineSpecifiedDocumentContextParameter en CII. Sale por dos '
        'motivos que no se parecen: error cuando no está o está vacío, y '
        'aviso cuando está pero no nombra a EN 16931 —el caso típico del ERP '
        'configurado para otro país—. En Facturae sale como nota y no hay '
        'nada que arreglar: la sintaxis española no tiene ningún elemento '
        'con ese significado. Es el campo por el que un receptor de Peppol '
        'rechaza un documento antes de mirar un solo importe.'
    ),
    "BR-14": (
        'El importe total con impuestos incluidos, en la cabecera. Se mira '
        'que el elemento esté y que no venga vacío, porque para quien lo lee '
        'un elemento presente y sin contenido vale lo mismo que uno ausente. '
        'En EDIFACT este total va en un MOA con el cualificador 388, y ahí '
        'está el motivo más frecuente de que salte teniendo la factura el '
        'dato delante: el importe está escrito, pero con el cualificador de '
        'otra guía sectorial, y la regla europea no mira ese sitio. Cuando '
        'pasa eso, EDI-TOTALES-DE-OTRA-GUIA lo dice al lado.'
    ),
    "XSD-NO-APLICA": (
        'Sólo sale en EDIFACT. La forma del documento no se ha comprobado '
        'contra ningún esquema XSD porque EDIFACT no es XML y no tiene '
        'ninguno. No falta un fichero por instalar ni hay nada que arreglar '
        'en el documento; es una decisión de quien lee —dar por buena la '
        'forma sin esquema— y por eso se declara en vez de callarla. En su '
        'lugar se comprueban las cuentas que la propia norma obliga a llevar '
        'en el sobre: que el UNT repita la referencia de su UNH y cuente '
        'bien sus segmentos, y que el UNZ cuadre con los mensajes que hay. '
        'De eso se ocupan los códigos EDI-.'
    ),
    "IVA-TIPO": (
        'No lo exige ninguna norma: compara cada tipo del desglose con los '
        'que están vigentes en España —21%, 10%, 4% y 0%— y avisa del que no '
        'sea ninguno. Un 19% o un 7% es perfectamente legal si la operación '
        'tributa en otro país, y por eso es aviso y no error; lo que caza de '
        'verdad es el dedazo, el 12% donde iba un 21%. Las categorías L y M '
        'se saltan a propósito: el IGIC y el IPSI tienen sus propios tipos y '
        'compararlos con los peninsulares sería acusarlos de existir.'
    ),
    "BR-23": (
        'Cada línea tiene que decir en qué unidad mide lo que factura: '
        'unidades, kilos, horas. Se dice una vez por documento y no una por '
        'línea —cien líneas sin unidad son un problema, no cien— y el campo '
        'enumera cuáles. En EDIFACT la unidad es el tercer componente del '
        'QTY, y ahí está la causa que se ve en las facturas de verdad: el '
        'cualificador es el correcto y la cantidad está, pero se escribe '
        'QTY+47:5 en vez de QTY+47:5:PCE y el hueco de la unidad se queda '
        'sin rellenar. Si la sintaxis no tiene dónde escribirla, sale como '
        'nota y no hay nada que corregir.'
    ),
    "BR-13": (
        'El total sin impuestos de la cabecera: lo que suman las líneas '
        'después de descuentos y cargos y antes del IVA. Es uno de los '
        'cuatro totales que EN 16931 exige por separado —sin impuestos, con '
        'impuestos, a pagar y suma de líneas—, y la norma los pide todos '
        'aunque unos se puedan deducir de otros, precisamente para poder '
        'contrastarlos. Se mira que esté y que no venga vacío. En EDIFACT le '
        'toca el MOA con cualificador 389, y es corriente que el importe '
        'esté escrito con el código de otra guía.'
    ),
    "IVA-SIN-CATEGORIA": (
        'No lo exige ninguna norma: avisa de que hay conceptos de línea sin '
        'categoría de IVA, y el campo los nombra uno a uno. Importa porque '
        'sin categoría en la línea no hay forma de contrastar el desglose '
        'con lo que de verdad se facturó: las reglas de cuadre se quedan '
        'mirando un desglose que puede estar impecable por dentro y no '
        'corresponderse con ninguna línea. Cuando es la sintaxis la que no '
        'tiene ese campo, esto se calla: acusar a una factura de no escribir '
        'lo que su formato no puede escribir es acusarla de nada.'
    ),
    "BR-46": (
        'Cada entrada del desglose tiene que decir cuánto impuesto sale, no '
        'sólo sobre cuánto se calcula. Es de las que más importan porque su '
        'ausencia enmudece a las demás: las reglas de cuadre se saltan lo '
        'que viene sin valor, así que una entrada sin cuota hacía que el '
        'desglose más roto posible saliera en el informe más limpio, y de '
        'paso dejaba a BR-CO-14 sumando cuotas sin encontrar ninguna que '
        'sumar. Salta una vez por entrada, y el campo dice de cuál: la del '
        '21%, la exenta, la que sea.'
    ),
    "EDI-TOTALES-DE-OTRA-GUIA": (
        'Existe para que una queja no mande a buscar un dato que la factura ya '
        'trae. EN 16931 espera los totales en segmentos MOA con '
        'tres cualificadores concretos —389 sin impuestos, 388 con '
        'impuestos, 9 a pagar—, pero las facturas EDIFACT llevan décadas '
        'circulando con las guías de cada sector, que eligieron otros: el '
        '128, el 129, el 86. Cuando eso pasa, las reglas europeas dan por '
        'ausente un importe que está escrito, y este aviso enseña con qué '
        'códigos viene. Para cumplir la norma hay que cambiar el código, no '
        'añadir el importe.'
    ),
    "BR-15": (
        'Lo que hay que pagar de verdad, que no siempre es el total con '
        'impuestos: de ahí se descuentan los anticipos ya cobrados y se suma '
        'lo que se redondee. Por eso la norma lo pide aparte en vez de darlo '
        'por deducido — es el único de los cuatro totales que puede diferir '
        'legítimamente de la cuenta hecha con los otros tres, y es el que '
        'mira quien va a ordenar la transferencia. Se comprueba que esté y '
        'que no venga vacío.'
    ),
    "EDI-UNA-DE-CINCO": (
        'Nota de EDIFACT sobre el UNA, el segmento que abre el fichero y '
        'declara qué caracteres hacen de separadores. ISO 9735 manda seis y '
        'éste trae cinco: falta el hueco reservado, que en la práctica es un '
        'espacio que alguien no escribió. Se ha leído el quinto carácter '
        'como terminador de segmento porque es la única lectura posible '
        '—detrás del UNA sólo puede venir el UNB—, así que el fichero se ha '
        'partido bien y no se ha perdido nada. Se dice porque es una '
        'interpretación de quien lee, y las interpretaciones se declaran.'
    ),
    "BR-26": (
        'Cada línea tiene que llevar el precio por unidad, sin impuestos. '
        'Junto con la cantidad y la unidad es lo que separa una factura que '
        'se puede comprobar de una que sólo se puede pagar: con el importe a '
        'secas no hay forma de casar la línea con un albarán ni de discutir '
        'una tarifa. El precio unitario y el importe de la línea son campos '
        'distintos: una línea puede traer sus 1.250 € perfectamente y no '
        'decir en ningún sitio que salen de 25 unidades a 50 €.'
    ),
    "BR-45": (
        'Cada entrada del desglose tiene que declarar sobre cuánto se '
        'calcula el impuesto. Es la pareja de BR-46 y falla por lo mismo: '
        'sin base, la regla que comprueba que la cuota es el tipo aplicado a '
        'la base no tiene contra qué comprobarla, y se salta la entrada en '
        'silencio. El caso corriente es el documento que trae el total de '
        'impuestos y no el detalle: la norma pide una entrada por cada tipo, '
        'y cada una con su base y su cuota.'
    ),
    "BR-21": (
        'Cada línea debe llevar un identificador que la distinga de las '
        'demás. No es burocracia: sin él, una queja sobre «la línea 3» no se '
        'refiere a nada que exista dentro del documento, y este validador '
        'tiene que nombrar las líneas por su posición, que es lo primero que '
        'se descuadra en cuanto alguien reordena el fichero. En Facturae '
        'sale como nota en todas las facturas y no hay nada que arreglar: la '
        'sintaxis española no tiene ese campo y sus líneas se nombran por el '
        'orden en que vienen.'
    ),
    "BR-07": (
        'El nombre o la razón social de quien recibe la factura, que es cosa '
        'distinta de su identificador fiscal y de su GLN. Salta cuando el '
        'elemento no está o está vacío. En las facturas EDIFACT reales el '
        'motivo es casi siempre el mismo: el NAD del comprador identifica a '
        'la parte sólo con su código y deja sin escribir el componente del '
        'nombre, porque entre dos empresas que llevan años intercambiando '
        'ficheros el código basta para saber quién es. Para EN 16931 no '
        'basta: el nombre tiene que estar escrito en la factura.'
    ),
    "ANCLAS-SIN-RENOVAR": (
        "Las anclas salen de una lista que decía renovarse antes de hoy. La "
        "cadena llega igual, pero que una autoridad estuviera cualificada "
        "entonces no dice que lo esté ahora."
    ),
}


def explicar(codigo: str, familia: str) -> tuple[str, bool]:
    """La explicación de un código y si es suya o heredada de su familia.

    Devuelve `(texto, es_propia)`. Cuando no hay ninguna de las dos, el texto
    va vacío: la página lo cuenta como hueco en vez de inventarse una frase.
    """
    propia = CODIGOS.get(codigo)
    if propia:
        return propia, True
    return FAMILIAS.get(familia, ""), False
