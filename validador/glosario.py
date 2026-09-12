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
    "BR-10": (
        'La dirección postal de quien recibe la factura. En UBL y en CII es '
        'un elemento que la contiene entera y basta con que exista; en '
        'EDIFACT no hay tal elemento —la calle, la ciudad, el código postal y '
        'el país son cuatro posiciones sueltas del NAD—, así que se pregunta '
        'por las cuatro y con una que esté, la dirección está. La diferencia '
        'no es teórica: el EDIFACT_EXAMPLE6 de la propia Comisión trae el '
        'país y no la calle, y con la ruta estricta salía acusado de no '
        'llevar dirección. Que esté completa es otra cosa, y de la parte que '
        'la norma sí exige —el país— se ocupa BR-11.'
    ),
    "BR-06": (
        'El nombre o la razón social de quien emite la factura. Tiene una '
        'trampa en UBL que no se ve leyendo el documento: el campo que la '
        'norma pide es el nombre registral, '
        'PartyLegalEntity/RegistrationName, y no el nombre comercial, '
        'PartyName/Name. Una factura que sólo trae el segundo se lee '
        'perfectamente, lleva el nombre del vendedor a la vista de '
        'cualquiera, y salta igual, porque para EN 16931 ese campo está '
        'vacío. En EDIFACT el nombre va en el NAD del vendedor, y falta '
        'cuando la parte se identifica sólo con su código.'
    ),
    "BR-08": (
        'La dirección postal de quien emite la factura, y lo que se comprueba '
        'es que exista, no que esté completa. Suena poco, y es lo que la '
        'norma pide: de la única parte que EN 16931 considera imprescindible '
        '—el país— se ocupa BR-09 por separado, precisamente porque una '
        'dirección sin país no sirve para decidir dónde tributa la operación. '
        'En EDIFACT se busca en las cuatro posiciones del NAD que pueden '
        'llevarla, igual que en la del comprador.'
    ),
    "EDI-VARIOS-MENSAJES": (
        'El fichero trae varios mensajes dentro del mismo sobre UNB…UNZ, y '
        'este validador sólo mira el primero. Es lo corriente en EDIFACT de '
        'verdad: un sobre con la facturación de un mes entero, decenas de '
        'INVOIC seguidos, es la forma normal de enviarla, y en el corpus de '
        'facturas reales pasa en más de un tercio de los ficheros. No es un '
        'defecto del documento y por eso es aviso: lo que dice es qué parte '
        'del fichero se ha mirado, para que nadie dé por revisado lo que no '
        'se ha revisado. Para verlos todos hay que separarlos en ficheros '
        'aparte.'
    ),
    "BR-12": (
        'La suma de los importes netos de las líneas, declarada en la '
        'cabecera. Es el único de los cuatro totales que no es un total del '
        'documento sino un subtotal: va antes de los descuentos y los cargos '
        'de documento, y existe para que se pueda comprobar la parte de '
        'arriba de la factura contra la de abajo. Sin él, BR-CO-10 —que '
        'compara esa cifra con lo que suman las líneas de verdad— se queda '
        'sin nada que comparar. En EDIFACT le toca el MOA con cualificador '
        '79, y de las facturas reales del corpus que lo incumplen, 19 de 20 '
        'no traen ese segmento en absoluto.'
    ),
    "BR-CO-18": (
        'La factura no trae desglose de IVA: ni una sola entrada. La norma '
        'pide una por cada combinación de categoría y tipo, con su base y su '
        'cuota, y sin ninguna no hay nada que comprobar del impuesto — el '
        'receptor la rechaza y con razón. Es error y no aviso desde que se '
        'vio cómo fallaba antes: era un aviso que sólo saltaba si el IVA '
        'declarado no era cero, así que una factura sin desglose y sin total '
        'de impuestos pasaba en silencio, que es el caso peor de los dos. '
        'Cuando hay un total de impuestos pero no el detalle, el informe lo '
        'dice con esas palabras: tanto de IVA sin desglosar.'
    ),
    "BR-CO-12": (
        'El total de cargos de documento que declara la factura no es lo que '
        'suman los cargos que detalla. Es la pareja de BR-CO-11, que hace lo '
        'mismo con los descuentos, y las dos se saltan enteras si el '
        'documento no detalla ningún ajuste: de esa factura ya se queja otra '
        'regla, y ahí el consejo útil es «detállalos» y no «la resta no '
        'cuadra». Basta con que haya alguno detallado, de cualquiera de los '
        'dos lados, y esa decisión tiene motivo: una factura que detalla sus '
        'cargos y además declara un total de descuentos que no detalla deja '
        'ese total fantasma a la vista de esta regla y de ninguna otra.'
    ),
    "BR-47": (
        'Una entrada del desglose sin categoría de IVA: sin ella no se sabe '
        'si es tipo general, exenta, no sujeta o inversión del sujeto pasivo, '
        'y de eso depende todo lo demás que se compruebe sobre esa entrada. '
        'Lo que hay que saber de este código es cuándo no salta: cuando es la '
        'sintaxis la que no tiene dónde escribirla. Facturae es ese caso —su '
        'TaxTypeCode dice qué impuesto es, no de qué categoría UNCL5305— y '
        'sin esa distinción BR-47 salía como error en todas las facturas de '
        'España, siempre, hicieran lo que hicieran. De ese hueco se informa '
        'una vez y como nota.'
    ),
    "FIRMA-DEBIL": (
        'La firma está hecha con SHA-1, retirado para firma electrónica desde '
        'hace años porque se sabe fabricar dos documentos distintos con el '
        'mismo resumen. La firma puede ser perfectamente auténtica y la '
        'aritmética cuadrar: lo que ya no da garantías es el algoritmo, y por '
        'eso es aviso y no error. No es un caso raro ni antiguo: sale en diez '
        'de los ficheros firmados que hay aquí para probar, varios de ellos '
        'de los que la Administración publica como ejemplo.'
    ),
    "BR-25": (
        'Cada línea tiene que decir qué se factura en ella, con palabras. En '
        'EDIFACT esa descripción va en el IMD en formato libre, y falta a '
        'menudo por un motivo que tiene su lógica: la línea identifica el '
        'artículo con su código de catálogo y quien recibe la factura ya sabe '
        'qué es ese código, así que escribir el nombre parece redundante. '
        'Para EN 16931 no lo es — una factura tiene que poder leerla alguien '
        'que no tenga el catálogo delante, empezando por quien la audite.'
    ),
    "CU-07": (
        'La fecha de expedición tiene más de cuatro años, que es el plazo de '
        'prescripción. Es aviso y no error porque una factura vieja puede ser '
        'legítima —se está revisando un ejercicio cerrado, se reemite algo—, '
        'pero la causa habitual es mucho más tonta: el año mal tecleado. '
        'Aparece en trece de los catorce ficheros Facturae que hay aquí, y no '
        'porque estén mal: son los ejemplos que publica la Administración, '
        'fechados entre 2007 y 2013.'
    ),
    "EDI-MENSAJE-DESCONTADO": (
        'El UNT declara un número de segmentos distinto del que tiene el '
        'mensaje. Esa cuenta incluye al propio UNH y al UNT, y es lo único en '
        'todo el fichero que delata que falta un trozo: un EDIFACT al que se '
        'le han perdido veinte segmentos por el camino se sigue leyendo sin '
        'protestar, con sus líneas y sus totales, sólo que son menos de las '
        'que salieron. Por eso la norma obliga a llevar la cuenta y por eso '
        'esto es error: es el mecanismo de integridad del formato, y cuando '
        'no cuadra, lo que se haya validado del mensaje vale poco.'
    ),
    "BR-24": (
        'Hay líneas sin importe neto, y el campo dice cuáles — por su '
        'identificador si la sintaxis lo tiene, y por su posición si no. '
        'Además de ser obligatorio por sí mismo, este dato es el que alimenta '
        'el cuadre: BR-CO-10 sólo compara la suma declarada con la suma real '
        'de las líneas cuando todas tienen importe, porque sumar las que haya '
        'e ignorar las demás daría un descuadre inventado. Así que una línea '
        'sin importe no es un hueco suelto: deja muda a la comprobación que '
        'caza los totales retocados a mano.'
    ),
    "CU-01": (
        'El NIF del emisor no pasa su dígito de control, y eso invalida el '
        'código único entero, porque el NIF forma parte de él: el código '
        'único del RD 238/2026 se compone con el NIF de quien emite, el '
        'número de la factura y su fecha. Sólo se comprueba cuando el '
        'documento está sujeto a la facturación española — medirle el dígito '
        'de control español a un identificador holandés es inventarse un '
        'error, y eso es exactamente lo que hacía esta regla en 61 de 62 '
        'facturas ajenas antes de acotarla. Salta en ocho de los catorce '
        'ficheros Facturae de ejemplo que hay aquí, los de la propia '
        'Administración incluidos.'
    ),
    "NIF-RECEPTOR": (
        'El NIF de quien recibe la factura no pasa su dígito de control. No '
        'lleva prefijo CU- a propósito: el código único del RD 238/2026 sólo '
        'usa el NIF del emisor, y firmar con una norma una queja que esa '
        'norma no hace es de las cosas que este validador no hace. Sale como '
        'aviso de la casa, y sale porque a quien recibe la factura le importa '
        'mucho: con el NIF mal no puede deducirse el IVA soportado y la '
        'devuelve. Sólo se mide en documentos sujetos a la facturación '
        'española, y nunca sobre un identificador que se ve que es de fuera.'
    ),
    "BR-CO-10": (
        'La suma de importes de línea que declara la cabecera no coincide con '
        'lo que suman las líneas de verdad. Es la comprobación que caza el '
        'retoque a mano: una línea añadida, borrada o cambiada de importe sin '
        'volver a calcular el total de arriba. Sólo se hace cuando todas las '
        'líneas tienen su importe —si falta alguno salta BR-24 y ésta se '
        'calla, porque sumar las que haya e ignorar las demás daría un '
        'descuadre inventado—, y el informe enseña las dos cifras y de '
        'cuántas líneas sale la suma real, que es lo que hace falta para '
        'encontrar la que baila.'
    ),
    "BR-22": (
        'Cada línea tiene que decir cuántas unidades factura. Es la pareja de '
        'BR-23, que mira la unidad de medida, y en EDIFACT las dos viajan en '
        'el mismo sitio: el compuesto del QTY con cualificador 47, donde la '
        'cifra y la unidad son dos posiciones seguidas. Por eso se suelen ver '
        'juntas, y por eso conviene mirarlas juntas: si falta la cantidad, es '
        'que falta el QTY entero o que lleva otro cualificador; si sólo falta '
        'la unidad, el segmento está y le falta un trozo.'
    ),
    "BR-48": (
        'Una entrada del desglose sin tipo de IVA. La única que puede ir sin '
        'él es la categoría O, lo no sujeto, porque no hay nada que aplicar; '
        'en todas las demás el tipo es obligatorio, incluida la exenta —cuyo '
        'tipo es cero, que no es lo mismo que no tener tipo—. Aquí sólo se '
        'mira que el tipo esté. Que sea el que le corresponde a su categoría '
        'lo miran otras reglas, las BR-{X}-5, una por cada categoría.'
    ),
    "EDI-SOBRE-DESCUADRADO": (
        'El UNZ que cierra el intercambio no repite la referencia que puso el '
        'UNB al abrirlo. Esa referencia es lo que ata el principio con el '
        'final: si no coinciden, o el fichero junta trozos de dos '
        'intercambios distintos, o alguien reescribió una de las dos puntas. '
        'Es uno de los dos controles que EDIFACT lleva incorporados en el '
        'sobre —el otro es el recuento— y son los únicos que hay, porque un '
        'EDIFACT no tiene esquema contra el que medirse.'
    ),
    "SELLO-FALTA": (
        'La firma no lleva sello de tiempo de un tercero, y eso no es una '
        'queja sino un dato. '
        'Importa porque para saber si un certificado estaba vigente y sin '
        'anular al firmar hace falta saber cuándo se firmó, y sin sello la '
        'única fecha disponible es la que declara quien firma — o sea, su '
        'palabra. La nota dice cuál se ha usado y con qué valor, que es '
        'exactamente lo que hay que saber para decidir cuánto vale el resto '
        'del informe. Un sello de una autoridad de sellado convierte esa '
        'palabra en una prueba.'
    ),
    "EDI-SOBRE-DESCONTADO": (
        'El UNZ dice llevar un número de mensajes distinto del que hay. Es el '
        'control de integridad del sobre, hermano del UNT de cada mensaje, y '
        'sirve para lo mismo: delatar un fichero al que le falta un trozo, '
        'que por dentro se sigue leyendo sin protestar. Tiene una trampa que '
        'aquí está contemplada: cuando el intercambio lleva grupos '
        'funcionales, UNG…UNE, el UNZ cuenta grupos y no mensajes, así que '
        'contar mensajes contra ese número acusaría en falso a un fichero '
        'perfectamente correcto.'
    ),
    "FE-SIN-GRAVAR": (
        'La factura declara una base antes de impuestos y sólo una parte de '
        'ella aparece como base de un impuesto: queda dinero facturado sin '
        'gravar ni justificar, y el informe dice cuánto exactamente. Es aviso '
        'y no error porque el esquema de Facturae no lo escribe como fórmula '
        'y hay regímenes donde la base del impuesto no es el importe '
        'facturado —el especial del grupo de entidades, el de agencias de '
        'viajes—. Pero es la comprobación que caza el fallo que más dinero '
        'mueve, y sin ella dos de las nueve facturas oficiales de prueba '
        'pasan sin que nadie diga que les falta base por gravar.'
    ),
    "IVA-TIPO-SIN-DESGLOSE": (
        'Hay conceptos a un tipo que el desglose no recoge. La norma habla de '
        'categorías, pero el desglose va por categoría y tipo, y ahí se cuela '
        'media factura: si hay conceptos al 21% y al 10% y el desglose sólo '
        'trae el 21%, la categoría está declarada, las reglas europeas quedan '
        'contentas y falta la mitad del impuesto. Sin esta comprobación sólo '
        'se veía la otra mitad del error —la base que no cuadra—, que es la '
        'consecuencia y no la causa. El informe dice cuánto hay a ese tipo y '
        'en qué conceptos.'
    ),
    "BR-03": (
        'La fecha de expedición de la factura. Se comprueba que esté y que no '
        'venga vacía; de que sea razonable se ocupan las reglas del código '
        'único, que miran si es futura o si tiene más años que el plazo de '
        'prescripción. En EDIFACT hay un sitio donde buscarla y sólo uno: el '
        'DTM con cualificador 137. Una factura que traiga sus fechas con '
        'otros cualificadores —la de entrega, la del pedido, la de '
        'vencimiento— tiene fechas de sobra y ninguna que la norma acepte '
        'como la de expedición.'
    ),
    "BR-CO-17": (
        'La cuota declarada para una entrada del desglose no sale de aplicar '
        'su tipo a su base. La cuenta es exactamente ésa —base por tipo entre '
        'cien, redondeada a dos decimales— y el informe enseña la operación '
        'hecha, no sólo el resultado, para que se vea dónde está la '
        'diferencia. El caso corriente no es un error de multiplicación: es '
        'redondear línea a línea y luego sumar, que da un céntimo de más o de '
        'menos frente a redondear el total una sola vez. Un céntimo basta '
        'para que un receptor automático rechace la factura.'
    ),
    "EDI-ETIQUETA-IMPOSIBLE": (
        'Hay texto donde tenía que empezar un segmento. Una etiqueta EDIFACT '
        'son tres caracteres, así que lo que hay ahí no es una. Lo que suele '
        'haber detrás es concreto y tiene arreglo: un apóstrofo dentro de un '
        'dato —un nombre, una dirección— escrito sin el carácter de escape '
        'delante, y el segmento se partió por ahí como si hubiera terminado. '
        'El trozo suelto se deja fuera para no arrastrar el fallo al resto '
        'del fichero, pero el dato que llevara está perdido, y eso hay que '
        'saberlo.'
    ),
    "BR-09": (
        'La dirección del vendedor no incluye el código de país. Es la única '
        'parte de una dirección postal que EN 16931 considera imprescindible, '
        'y no por pulcritud: de dónde está establecido quien emite depende '
        'dónde tributa la operación, y eso lo decide un código de dos letras. '
        'Esta regla no salta cuando no hay dirección ninguna —de eso ya se '
        'queja BR-08, y con mejor consejo—: sólo cuando hay dirección y le '
        'falta el país, que es un descuido distinto.'
    ),
    "BR-CO-11": (
        'El total de descuentos de documento que declara la factura no es lo '
        'que suman los descuentos que detalla. Los descuentos de documento '
        'son los que se aplican a la factura entera y no a una línea —el '
        'pronto pago, el rappel—, y el error típico es declarar el total y no '
        'detallarlo, o detallar uno y declarar dos. Es la pareja de BR-CO-12, '
        'que hace lo mismo con los cargos, y las dos callan si el documento '
        'no detalla ningún ajuste, porque entonces el consejo útil es otro.'
    ),
    "FE-LINEA-SIN-GRAVAR": (
        'Una línea factura un importe y declara como base de impuesto menos '
        'de lo que factura: queda una parte sin gravar ni justificar, y el '
        'aviso dice cuánto y en qué línea. Es la versión por línea de '
        'FE-SIN-GRAVAR, y la que más sirve de las dos: el descuadre del total '
        'dice que falta dinero por gravar, y éste dice en qué concepto. Es '
        'aviso porque el esquema de Facturae no lo escribe como fórmula, y '
        'aun así es donde se ve antes el fallo más caro que puede tener una '
        'factura: facturar algo y no declararlo.'
    ),
    "BR-05": (
        'La factura tiene que decir en qué moneda está. Sin eso, todos los '
        'importes del documento son números sin unidad, y un receptor que '
        'suponga euros donde había libras se equivoca en un 15% sin que salte '
        'nada. En EDIFACT la moneda va en el CUX con cualificador 2, y es el '
        'único sitio donde esta regla mira: una factura que la declare con '
        'otro cualificador la lleva escrita, se lee perfectamente, y para la '
        'norma no está.'
    ),
    "BR-16": (
        'La factura no detalla ningún concepto. Importa más de lo que parece '
        'porque, sin líneas, se callan de golpe todas las reglas que miran '
        'líneas —la cantidad, la unidad, el importe, el cuadre de BR-CO-10 y '
        'el desglose entero—, y el informe de una factura vacía sale más '
        'limpio que el de una con un solo fallo. Por eso ésta se dice aparte '
        'y las demás se apartan cuando no hay ninguna: lo que hay que '
        'arreglar es esto, no las cuarenta consecuencias. En UBL se buscan '
        'dos elementos, InvoiceLine y CreditNoteLine, porque un abono llama a '
        'los suyos de otra manera y con el mapa de la factura salía acusado '
        'de no tener ninguno.'
    ),
    "FIRMA-CADUCADA": (
        'La factura dice haberse firmado un día en que el certificado ya no '
        'valía, o todavía no. Se compara esa fecha con las dos que trae '
        'dentro el propio certificado, y el informe enseña las tres. Lo que '
        'hace que la regla sea seria o no es de dónde sale la fecha de la '
        'firma: si hay sello de tiempo de una autoridad, es una fecha '
        'acreditada; si no, es la que escribe quien firma, o sea su palabra, '
        'y eso lo dice SELLO-FALTA en el mismo informe. El caso que hay aquí '
        'está entre las facturas de ejemplo que publica la Administración: '
        'certificado válido hasta el 31 de enero de 2009 y firma fechada el '
        '25 de febrero.'
    ),
    "FIRMA-FALTA": (
        'La factura de Facturae no está firmada. Sólo se echa de menos en '
        'Facturae, y no es un olvido con UBL y CII: en esas dos la firma no '
        'es parte del formato —se pone por fuera, en el sobre del envío—, y '
        'pedirla aquí sería inventarse un requisito que esas sintaxis no '
        'tienen. Que en Facturae sí haga falta no lo decide este validador: '
        'lo dice el propio esquema en la documentación de su bloque de firma. '
        'De las nueve facturas de ejemplo que publica la Administración, '
        'cuatro vienen sin firmar, que es lo corriente en un ejemplo hecho '
        'para enseñar la forma del XML y no para valer frente a nadie.'
    ),
    "IVA-AJUSTES-SIN-DETALLAR": (
        'La factura declara un total de descuentos o de cargos de documento '
        'pero no dice cuáles son. Sin saber a qué tipo va cada ajuste no se '
        'puede repartir la base entre los tipos, y comprobarla entonces sería '
        'inventarse un error: este aviso existe para decir «no se ha podido '
        'comprobar» y para que se callen, esa vez, las reglas que cuadran la '
        'base de cada categoría. Los dos totales se miran por separado y no '
        'sumados, que es un detalle que costó una comprobación: sumándolos, '
        'un descuento y un cargo del mismo importe se anulan y la factura '
        'parecería no declarar ninguno.'
    ),
    "SELLO-CONFIANZA": (
        'Quién acredita la fecha, y por qué se le cree. Un sello de tiempo se '
        'puede fabricar entero, autoridad incluida, así que comprobar que '
        'cuadra no basta: hace falta que el certificado de quien selló llegue '
        'a una de las anclas de sellado instaladas, y esas anclas salen de la '
        'lista de confianza del Estado. Esta nota dice a cuál llega y de qué '
        'lista viene, que es lo que permite juzgar cuánto vale la fecha. '
        'Cuando la autoridad dejó de ser cualificada después de sellar, '
        'también lo dice: el sello se acepta porque es anterior a esa fecha, '
        'no porque la autoridad siga vigente hoy.'
    ),
    "SELLO-DESPUES-DE-CADUCAR": (
        'Lo único acreditado de esta firma es posterior a la caducidad del '
        'certificado. No es una imposibilidad, y por eso no es un error: la '
        'firma pudo hacerse antes, cuando el certificado aún valía, y lo más '
        'probable es que así fuera. Lo que pasa es que nada lo demuestra, '
        'porque el único dato que lo diría es la fecha que escribe quien '
        'firma. Sellar tarde es legítimo y pasa a diario, así que rechazar la '
        'factura sería rechazar facturas buenas; callarlo sería peor, porque '
        'ésta es justo la maniobra para la que sirve un sello: firmar con un '
        'certificado caducado y fechar hacia atrás. Aquí se ha visto en '
        'facturas con certificados vencidos entre 2008 y 2012 selladas de '
        'verdad en 2026.'
    ),
    "SELLO-TIEMPO": (
        'Lo que se ha dado por bueno, y con qué. La nota dice qué autoridad '
        'selló, cuándo, con qué precisión declarada y con qué número de '
        'serie, y lo que importa viene después: ésa es la fecha que se usa '
        'para mirar la vigencia del certificado y su revocación, en lugar de '
        'la que declara quien firma. Un sello que cuadra demuestra que la '
        'firma ya existía ese día, que es una cota y no una fecha exacta —se '
        'puede sellar meses después—, y por eso las demás reglas la usan sólo '
        'por arriba. Sin esta nota el informe daría por acreditada una fecha '
        'sin decir de dónde la saca.'
    ),
    "IVA-SIN-TOTAL": (
        'La factura trae base imponible y total con impuestos, pero no dice '
        'cuánto impuesto hay, así que no se ha podido comprobar que el uno '
        'salga del otro. Es la ausencia de una comprobación y no un defecto '
        'del documento, y por eso se dice en vez de callarse: un informe mudo '
        'aquí tendría exactamente el mismo aspecto que el de una factura '
        'donde BR-CO-15 cuadra, y no es lo mismo haber comprobado que no '
        'haber podido. La norma pide el dato, es BT-110, y sin él la cadena '
        'aritmética se queda partida por la mitad.'
    ),
    "XSD-ORDEN": (
        'Un elemento que el esquema no espera en ese sitio. La biblioteca que '
        'valida dice exactamente lo mismo para tres problemas distintos '
        '—sobra, falta, o están cambiados de orden—, así que aquí se mira el '
        'documento antes de hablar: si lo que se esperaba aparece más '
        'adelante entre los hermanos, están al revés y se dice cuál va antes. '
        'El caso visto aquí explica por qué se hace así: un '
        'AdditionalDocumentReference colocado detrás del bloque de entrega, '
        'en una factura UBL que admite ese elemento tantas veces como haga '
        'falta. Contando apariciones, el informe habría dicho que aparece dos '
        'veces y que el esquema no admite tantas, y quien lo leyera habría '
        'borrado uno sin arreglar nada.'
    ),
    "BR-04": (
        'El documento no dice de qué tipo es. Es lo que distingue una factura '
        'de un abono, y cada sintaxis lo escribe en su sitio: UBL en '
        'InvoiceTypeCode o en CreditNoteTypeCode según sea una cosa u otra, '
        'CII en el TypeCode de la cabecera, EDIFACT en el BGM. Aquí sólo se '
        'mira que esté; que el código sea de los que admite la norma lo mira '
        'BR-CL-01, y son dos fallos distintos. En Facturae se lee '
        'InvoiceDocumentType, que dice FC, FA o AF: no es la lista europea y '
        'no lo será nunca, pero es lo que hay, y la regla comprueba lo que se '
        'puede comprobar. De las 179 facturas medidas aquí, sólo una no lo '
        'trae.'
    ),
    "BR-CL-01": (
        'El tipo de documento no es de los que admite EN 16931. La norma no '
        'acepta cualquier código de UNTDID 1001 sino sesenta y dos de ellos, '
        'y esa lista no está escrita de memoria: se sacó de los artefactos '
        'oficiales de la Comisión, que es la misma regla que aplican los '
        'validadores de PEPPOL y de XRechnung. El caso visto aquí es un '
        'EDIFACT que declara 220 en el BGM: un código que en UNTDID 1001 '
        'existe y significa pedido, o sea un documento bien escrito que dice '
        'de sí mismo que no es una factura. En Facturae, donde el código '
        'europeo no se escribe en ninguna parte, se deduce del tipo y del '
        'método de rectificación, y cuando no se puede deducir se dice en vez '
        'de acusar.'
    ),
    "BR-CO-14": (
        'El total de IVA que declara la factura no es la suma de las cuotas '
        'del desglose. Es el cuadre interno del impuesto, y suele romperse al '
        'cambiar el tipo de una línea sin rehacer el desglose; el informe '
        'enseña las dos cifras y de cuántas entradas sale la suma. Se calla '
        'cuando no hay total declarado o cuando ninguna entrada trae cuota, '
        'que es un problema anterior y lo dicen BR-45 a BR-48. En Facturae no '
        'se mide contra el total repercutido a propósito: ese total incluye '
        'el recargo de equivalencia, que no es IVA. Medido en una muestra: '
        '279,24 repercutidos frente a 244,34 de cuotas, y los 34,90 de '
        'diferencia eran recargo. La factura estaba bien y la regla la '
        'acusaba.'
    ),
    "BR-CO-16": (
        'El importe a pagar no cuadra. La cuenta es el total con impuestos '
        'menos lo ya anticipado más el redondeo, y es la última de la cadena '
        'aritmética: la única cifra de toda la factura que alguien va a '
        'transferir de verdad. El informe enseña la operación con sus '
        'sumandos cuando hay anticipos o redondeo, y dice llanamente que se '
        'esperaba el total con impuestos cuando no hay ninguno de los dos, '
        'porque entonces no hay cuenta que enseñar. El caso visto aquí es de '
        'los que no se encuentran leyendo: un total con impuestos de 336,90 y '
        'un a pagar de 366,86, con treinta euros que aparecen de la nada y '
        'ningún anticipo declarado que los explique.'
    ),
    "EDI-MENSAJE-DESCUADRADO": (
        'El UNT que cierra el mensaje no repite la referencia que puso el UNH '
        'al abrirlo. Es el mismo control que EDI-SOBRE-DESCUADRADO hace con '
        'el sobre, un escalón más adentro: el sobre ata el UNB con el UNZ y '
        'el mensaje ata el UNH con el UNT, y en un intercambio de varios '
        'mensajes es lo único que dice dónde acaba cada uno. El caso que hay '
        'aquí es el error típico: el cierre lleva 1256685, que es el número '
        'de la factura, donde la cabecera había puesto 4, que era la '
        'referencia del mensaje. Quien lo escribió puso en ese hueco el dato '
        'que tenía más a mano.'
    ),
    "EDI-NO-ES-FACTURA": (
        'El mensaje no es un INVOIC. EDIFACT es una familia de mensajes que '
        'comparten sobre y sintaxis —pedidos, albaranes, avisos de pago, '
        'respuestas—, así que un fichero que no es una factura se abre, se '
        'lee y se recorre igual de bien, y sólo el tipo declarado en el UNH '
        'dice qué es. Se para aquí porque seguir sería peor que no mirar: las '
        'reglas siguientes buscarían en un pedido las cosas de una factura y '
        'el informe se llenaría de faltas que no faltan. En el corpus medido '
        'hay uno, y es un ORDERS.'
    ),
    "IVA-CATEGORIA-RARA": (
        'El desglose trae una categoría de IVA que no es ninguna de las de la '
        'norma. Son nueve y la lista está cerrada: AE, E, G, K, L, M, O, S y '
        'Z. Cuando aparece otra no hay nada que aplicarle —toda la familia de '
        'reglas por categoría, la del tipo y la del motivo de exención, '
        'cuelga de saber cuál es—, así que esa entrada se queda sin comprobar '
        'y eso se dice. El caso visto aquí es una letra suelta, B, en una '
        'factura UBL: no significa nada en la norma, y basta para que esa '
        'parte del impuesto pase sin que nadie la mire.'
    ),
    "BR-02": (
        'La factura no lleva número. Es el dato con el que la va a buscar '
        'todo el mundo después —el receptor para pagarla, quien la emite para '
        'cobrarla, la Administración para cruzarla— y aquí sólo se mira que '
        'esté y que no venga vacío. Que sea único, que la serie no se repita '
        'y que no haya saltos no lo comprueba ningún validador de un fichero '
        'suelto, porque para eso hay que ver todas las demás facturas, y eso '
        'se dice en vez de dejarlo creer. Si una sintaxis no tuviera dónde '
        'escribir el número, la queja bajaría a nota: el hueco sería del '
        'formato y no del documento.'
    ),
    "BR-11": (
        'La dirección del comprador no incluye el código de país. Es la '
        'pareja de BR-09, que pide lo mismo del vendedor, y el par existe '
        'porque de los dos países depende qué impuesto lleva la operación: '
        'mismo país, IVA repercutido; países distintos dentro de la Unión, '
        'inversión del sujeto pasivo o entrega intracomunitaria; fuera, '
        'exportación. Un código de dos letras decide cuál de las tres. Como '
        'BR-09, no salta cuando no hay dirección ninguna —de eso se queja '
        'BR-10, y con mejor consejo—: sólo cuando hay dirección y le falta el '
        'país.'
    ),
    "BR-CO-13": (
        'La base imponible no es la suma de las líneas menos los descuentos '
        'de documento más los cargos. Es el eslabón del medio de la cadena '
        'aritmética: BR-CO-10 cuadra las líneas contra su total, ésta lleva '
        'ese total hasta la base, BR-CO-15 lleva la base hasta el total con '
        'impuestos y BR-CO-16 hasta lo que de verdad se paga. Por eso importa '
        'el orden al leer un informe: cuando saltan varias seguidas casi '
        'siempre hay un solo error arriba y las demás son su eco. El informe '
        'escribe la cuenta con los sumandos que haya y no menciona los '
        'descuentos cuando no hay descuentos, para que la operación se pueda '
        'seguir con el papel delante.'
    ),
    "BR-CO-15": (
        'El total con impuestos no es la base imponible más el importe de '
        'impuestos. Es la suma más simple de toda la factura, y por eso el '
        'fallo casi nunca está aquí: cuando salta, lo normal es que uno de '
        'los dos sumandos venga ya mal de antes —la base la cuadra BR-CO-13 y '
        'el importe de impuestos lo cuadra BR-CO-14 contra el desglose—. '
        'Cuando falta el importe total de impuestos esta regla no puede '
        'correr, y entonces se dice con el código IVA-SIN-TOTAL en vez de '
        'callarse: un informe mudo aquí se parece demasiado a uno que ha '
        'comprobado y le ha salido bien.'
    ),
    "XSD-FALTA": (
        'A un elemento le falta dentro algo que el esquema exige. Es el '
        'incumplimiento de forma más corriente y el más fácil de arreglar, '
        'siempre que el informe diga qué falta: el esquema lleva escritos los '
        'nombres de los hijos que esperaba en ese punto, así que se sacan de '
        'ahí y se enumeran en vez de decir «falta algo». Va con la línea del '
        'documento donde está el elemento incompleto, porque en un XML de mil '
        'líneas «falta el identificador» sin decir dónde sirve casi tan poco '
        'como no decir nada.'
    ),
    "XSD-VALOR": (
        'El contenido de un elemento no es ninguno de los que el esquema '
        'admite. Hay sitios donde el formato no acepta texto libre sino una '
        'lista cerrada —el código de país, el de moneda, el de la unidad de '
        'medida, el del medio de pago—, y ahí escribir «Euro» donde iba «EUR» '
        'es un fallo de forma y no de contenido. El informe pone la lista '
        'entera de valores admitidos, y la saca del propio esquema y no de lo '
        'que nadie recuerde: es de los pocos errores que se arreglan sin '
        'saber nada de la norma, sólo mirando la lista.'
    ),
    "XSD-TIPO": (
        'El contenido de un elemento no vale para lo que el esquema espera '
        'ahí: un texto donde iba un número, un decimal con coma, una fecha '
        'que no existe. La pista que acompaña al error depende del valor y no '
        'sólo del tipo, y eso se hizo por un caso concreto: a «2012-02-31» '
        'contestarle que una fecha se escribe AAAA-MM-DD es no haber mirado '
        'el valor, porque ya está escrita así; quien lo lea comprobará el '
        'formato, lo verá bien y no encontrará el fallo. Lo que pasa es que '
        'febrero de 2012 tiene veintinueve días, y eso es lo que dice el '
        'informe.'
    ),
    "XSD-RAIZ": (
        'El esquema no reconoce el elemento con el que empieza el documento. '
        'Sale cuando el fichero no es del formato que aparenta —una '
        'plantilla, un fragmento, un XML de otra cosa con la extensión '
        'cambiada— y también cuando le falta la declaración de espacio de '
        'nombres, que es lo que hace que un Invoice de UBL sea ése y no otro '
        'cualquiera. Los dos casos se dicen juntos porque desde fuera son '
        'indistinguibles, y el segundo es más frecuente de lo que parece: el '
        'documento está bien escrito de arriba abajo y le falta una línea.'
    ),
    "XSD-SIN-ESQUEMA": (
        'La forma no se ha comprobado porque el esquema de ese formato no '
        'está instalado. Es un aviso sobre este validador y no sobre la '
        'factura: dice qué formato y qué versión se han reconocido, cómo se '
        'llamaría el fichero que falta y en qué carpeta se ha buscado, que es '
        'lo que hace falta para arreglarlo. Existe porque la alternativa era '
        'peor: sin esquema instalado, el informe salía sin una sola queja de '
        'forma y quien lo leyera tenía todo el derecho a entender que la '
        'forma estaba bien.'
    ),
    "XSD-DEMASIADOS": (
        'Hay más incumplimientos del esquema de los que el informe enumera. '
        'La lista se corta a propósito y el número de los que faltan se dice '
        'en vez de esconderse: un documento con el espacio de nombres mal '
        'declarado produce un fallo por cada elemento que tiene, y volcar mil '
        'quejas iguales no informa, entierra. Las que no se listan casi '
        'siempre son consecuencia de las primeras, así que el consejo es '
        'literal: arregla ésas y vuelve a pasarlo. Lo que no se hace es decir '
        'que hay errores sin decir cuántos se han dejado fuera.'
    ),
    "FIRMA-NO-CUADRA": (
        'La firma no verifica contra el certificado que trae el documento. '
        'Dicho sin rodeos: o la firma se ha manipulado, o el certificado que '
        'viene dentro no es el que se usó para firmar. Es distinto de '
        'FIRMA-ALTERADA, que dice que cambió el documento; esto dice que no '
        'cuadra la firma misma. Lleva un detalle que se paga caro si se pasa '
        'por alto: en XML-DSig una firma de curva elíptica son los dos '
        'números pegados y rellenos con ceros, no el DER que llevan los '
        'certificados, y comprobarla como si fuera DER da «no verifica» en '
        'firmas perfectamente buenas.'
    ),
    "FIRMA-ALTERADA": (
        'El documento se ha modificado después de firmarlo. Es la '
        'comprobación que más vale de todo el módulo de firma y la que menos '
        'necesita: no hace falta clave ninguna ni autoridad ninguna, es un '
        'resumen criptográfico contra otro. La firma guarda el resumen de '
        'cada trozo que cubre; se vuelve a calcular y se comparan, y si no '
        'coinciden el documento ya no es el que se firmó, sea de quien sea el '
        'certificado. La causa no siempre es mala fe: una herramienta que '
        'reabre el XML y lo vuelve a guardar cambiando saltos de línea o el '
        'orden de dos atributos deja la firma rota igual.'
    ),
    "FIRMA-VACIA": (
        'La firma no cubre nada. El bloque está entero —su valor, su '
        'algoritmo— y no tiene ni una sola referencia a una parte del '
        'documento: está puesta y no garantiza ninguna. Es de las cosas que '
        'sólo se ven mirando dentro, porque por fuera el documento parece '
        'firmado y cualquier comprobación superficial dirá que lo está. Lo '
        'que hace una firma es fijar unos trozos concretos de un fichero '
        'concreto; una sin referencias es un papel en blanco firmado y '
        'grapado a la factura.'
    ),
    "FIRMA-SIN-CERTIFICADO": (
        'La firma no trae dentro el certificado con el que se hizo, así que '
        'no hay con qué comprobarla. XML-DSig lo permite, porque da por '
        'supuesto que quien recibe ya lo tiene o sabe dónde buscarlo, y en '
        'una factura electrónica eso rara vez es cierto: quien la recibe es '
        'alguien a quien no conoces. Va como aviso y no como error porque el '
        'documento no incumple nada; lo que pasa es que todo lo que este '
        'validador podría decir de esa firma se queda sin decir, y eso vale '
        'más saberlo que suponerlo.'
    ),
    "VALIDADOR-SE-ATRAGANTA": (
        'Este fichero ha hecho fallar al validador. No es una queja sobre la '
        'factura: es una queja sobre este programa, y lleva el nombre de la '
        'excepción para poder arreglarlo aquí. Sale como error del fichero a '
        'propósito, y el porqué está medido: apuntar a una carpeta de '
        'quinientas facturas y que la séptima estuviera mal terminaba en una '
        'traza de Python y ninguna de las otras cuatrocientas noventa y nueve '
        'revisada, con un código de salida idéntico al de «hay facturas con '
        'errores». Ahora el lote sigue, el fichero que se atragantó se cuenta '
        'como no revisado, y se dice de quién es la culpa.'
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
