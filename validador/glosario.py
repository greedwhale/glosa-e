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
    "CU-00": (
        'No se ha podido componer el código único porque falta el número de '
        'la factura, la fecha de expedición, o las dos cosas. El código único '
        'del RD 238/2026 son tres datos pegados —NIF de quien emite, serie y '
        'número, fecha— y con dos no se hace uno: sin una de las piezas no '
        'hay nada que comprobar, ni duplicados, ni numeración reutilizada, ni '
        'huecos en la serie. Por eso se dice aparte y como error. Las demás '
        'reglas de esta familia no se callan entonces por estar todo '
        'conforme, sino porque no tienen sobre qué correr, y un informe que '
        'no lo dijera dejaría creer justo lo contrario.'
    ),
    "CU-02": (
        'La factura no tiene número, y sin número no hay código único que '
        'componer. Es la misma falta que señala BR-02, vista desde la otra '
        'norma, y las dos se dicen a propósito: BR-02 dice que EN 16931 exige '
        'el número, y ésta dice que sin él la factura no puede identificarse '
        'de forma inequívoca ante la Administración española. Cuando pasa, '
        'las comprobaciones de forma del número se apagan —no hay forma que '
        'mirar—, pero las de la fecha siguen corriendo, porque la fecha sí '
        'está y sus problemas son suyos.'
    ),
    "CU-03": (
        'El número de factura no cabe. El tope son sesenta caracteres, serie '
        'incluida, y de dónde sale ese número importa tanto como la '
        'comprobación: la Orden Ministerial técnica del RD 238/2026 todavía '
        'no se ha publicado, así que se ha tomado del esquema de Verifactu, '
        'donde el campo equivalente admite sesenta. Está escrito en una '
        'constante y en un solo sitio, de modo que el día que la Orden fije '
        'otro se cambia ahí y ya está. Un límite sin procedencia es un límite '
        'que nadie puede discutir.'
    ),
    "CU-04": (
        'El número de factura lleva caracteres que no sobreviven a un viaje '
        'entre sistemas. Son dos casos con dos gravedades distintas. Si hay '
        'caracteres de control —un salto de línea, un tabulador— es error, y '
        'casi siempre viene de un copiar y pegar que se trajo el salto. Si '
        'hay caracteres fuera del ASCII —una eñe, un acento, una comilla '
        'tipográfica— es aviso: es legal y perfectamente válido, pero al '
        'pasar por un sistema antiguo puede transformarse, y entonces el '
        'código único deja de coincidir con el que quedó registrado. El '
        'informe enseña el número tal cual y lista aparte los caracteres '
        'raros, porque a simple vista no se ven.'
    ),
    "CU-05": (
        'El número de factura tiene espacios de más: al principio, al final o '
        'repetidos en medio. Invisibles al ojo y letales al comparar, que es '
        'todo lo que hace el código único. «F-001» y «F-001 » son la misma '
        'factura para cualquiera que las lea, y dos facturas distintas para '
        'dos sistemas que traten los espacios de forma distinta. Va como '
        'aviso porque no incumple nada escrito, y el informe pone el número '
        'entre comillas con su forma limpia al lado, que es la única manera '
        'de enseñar un espacio.'
    ),
    "CU-06": (
        'La fecha de expedición es posterior a hoy. Una factura no puede '
        'emitirse con fecha futura: la fecha de expedición es cuándo se '
        'expidió, no cuándo se espera cobrarla ni cuándo empieza el servicio. '
        'Es la pareja de CU-07, que mira el otro extremo —más de cuatro años '
        'atrás—, y las dos existen por lo mismo: la fecha forma parte del '
        'código único, así que un año mal tecleado no es una errata, es otra '
        'factura. El informe dice con qué día se ha comparado, porque quien '
        'lea ese informe dentro de un mes tiene derecho a saber contra qué se '
        'midió.'
    ),
    "CU-10": (
        'La misma factura otra vez: mismo emisor, mismo número y misma fecha. '
        'Es el duplicado limpio —un reenvío, un fichero procesado dos veces— '
        'y el más fácil de los tres que se cazan aquí. Cuando las facturas '
        'vienen de un lote, la queja dice en qué fichero estaba la primera y '
        'en cuál está ésta, que es lo primero que uno pregunta: para quitar '
        'un duplicado hay que saber cuál de los dos sobra. Es una '
        'comprobación que sólo tiene sentido sobre un montón de facturas; un '
        'fichero suelto no la dispara nunca.'
    ),
    "CU-11": (
        'El mismo número de factura con otra fecha. Dentro de una serie, un '
        'número no puede usarse dos veces, y esto es justo lo que el código '
        'único existe para impedir: dos facturas que se llaman igual sin ser '
        'la misma. El informe dice cuándo se usó el número la primera vez y '
        'cuándo se ha vuelto a usar, y de qué ficheros salen las dos. Es '
        'distinto de CU-10, que es la misma factura repetida, y de CU-12, que '
        'es la misma escrita de dos maneras: aquí hay dos facturas de verdad '
        'distintas peleándose por un número.'
    ),
    "CU-12": (
        'Dos facturas que sólo se distinguen por mayúsculas o por espacios. '
        'Es peor que un duplicado y por eso se dice aparte: en un duplicado '
        'los dos sistemas ven lo mismo dos veces y alguien acaba dándose '
        'cuenta; aquí cada sistema cree tener una factura diferente, y a cada '
        'uno le cuadran las cuentas por separado. «f-001» y «F-001 » son la '
        'misma factura para una persona y dos códigos únicos para una '
        'máquina. El informe pone las dos formas entre comillas, porque sin '
        'comillas la diferencia no se ve.'
    ),
    "CU-13": (
        'La serie tiene huecos: entre el primer número y el último faltan '
        'ordinales. El artículo 6 del Reglamento de Facturación exige '
        'numeración correlativa dentro de cada serie, pero un hueco no es '
        'automáticamente una infracción —puede ser una factura anulada—, así '
        'que va como aviso. El número se parte por donde acaban los dígitos: '
        '«F-2026-001» es la serie «F-2026-» y el ordinal 1, y eso es lo que '
        'permite ver los saltos. El informe enumera los tramos que faltan, y '
        'si son muchos dice los cinco primeros y cuántos quedan, porque una '
        'lista de doscientos huecos no la lee nadie.'
    ),
    "CU-14": (
        'Dentro de una serie, la fecha retrocede al avanzar el número. Una '
        'factura posterior no debería llevar fecha anterior, y cuando ocurre '
        'suele ser una factura metida a posteriori en un hueco. Hay un caso '
        'que esta regla deja pasar a propósito: cuando dos entradas tienen el '
        'mismo ordinal, el número no ha avanzado, así que decir que la fecha '
        'retrocede al avanzar el número sería afirmar algo que no ha pasado '
        '—la queja salía enseñando F-001 y F-001—. De ése ya se queja CU-11, '
        'que sí sabe lo que es: un número reutilizado.'
    ),
    "CU-15": (
        'El mismo ordinal escrito con distinto relleno de ceros. «F-001» y '
        '«F-1» son la misma factura para una persona y dos códigos únicos '
        'para una máquina, y en una serie donde conviven las dos formas la '
        'correlatividad deja de poder comprobarse. Se comparan las formas ya '
        'normalizadas, sin espacios y en mayúsculas, y eso es deliberado: si '
        'dos números se diferencian además en eso, el problema es otro y ya '
        'lo canta CU-12. Aquí interesa sólo el relleno.'
    ),
    "FIRMA-NO-XADES": (
        'La firma es XML-DSig a secas, sin las propiedades XAdES. Es una '
        'firma de verdad —cubre el documento y se puede verificar—, pero le '
        'falta todo lo que convierte una firma en la firma de una factura: la '
        'fecha de firma declarada, el certificado que el firmante dice haber '
        'usado y la política de firma. Sin esas propiedades, media docena de '
        'comprobaciones de este validador se quedan sin nada que mirar, y la '
        'vigencia del certificado no se puede situar en el tiempo. Facturae '
        'pide XAdES, y por eso esto va como aviso y no como una nota.'
    ),
    "FIRMA-OTRO-CERTIFICADO": (
        'El certificado que viene en el documento no es el que la firma dice '
        'haber usado. XAdES guarda el resumen del certificado firmante dentro '
        'de las propiedades que la propia firma cubre, así que ese dato no se '
        'puede cambiar sin romper la firma; el certificado que viaja en el '
        'bloque de claves, en cambio, sí. Cuando los dos no coinciden, '
        'alguien ha sustituido el segundo. Es exactamente la maniobra que '
        'esta comprobación existe para cazar: cambiar el certificado por el '
        'de alguien con mejor nombre y dejar la firma intacta, contando con '
        'que el receptor mire el nombre y no el resumen.'
    ),
    "FIRMA-SIN-COMPROBAR": (
        'Hay una parte de la firma que este validador no ha podido comprobar, '
        'y lo dice en vez de dar por buena la parte que sí ha mirado. Sale '
        'por tres causas distintas y las tres van con su motivo escrito: una '
        'canonicalización que no sabemos reproducir, una parte firmada que no '
        'se ha podido resolver, o un certificado ilegible. Ninguna acusa al '
        'documento, y todas cambian lo que vale el resto del informe. La '
        'alternativa sería un informe sin quejas de firma, que es exactamente '
        'el aspecto que tiene un documento bien firmado.'
    ),
    "SELLO-SIN-USAR": (
        'La firma lleva sello de tiempo y ninguno ha servido. Es distinto de '
        'no llevar ninguno aunque se acabe en la misma fecha, y por eso se '
        'dice aparte: a un documento sin sello hay que sellarlo, y a éste ya '
        'lo sellaron —el motivo por el que cada uno de sus sellos no vale '
        'está más arriba, en su propia queja—. Decirle que no lleva sello '
        'sería mandarle a hacer dos veces lo que ya hizo, y el fallo salió '
        'con un fichero real que traía el sello escrito en XML. La nota dice '
        'qué fecha se ha usado en su lugar y para qué sirve saberlo: fechando '
        'hacia atrás se esquivan la caducidad y la revocación a la vez.'
    ),
    "SELLO-NO-COMPROBADO": (
        'El sello está, pero es de una clase que este validador todavía no '
        'comprueba. XAdES define seis: el de la firma, el de la firma con las '
        'referencias de validación, el de sólo las referencias, el de '
        'archivo, el de todo lo firmado y el de un objeto concreto. Aquí se '
        'comprueba el primero contra lo que dice cubrir; de los demás se dice '
        'que están, de qué clase son y qué fecha declaran, y que no se han '
        'mirado. Callarlos sería peor que no comprobarlos, porque un informe '
        'sin mención de sello se lee como un documento que no traía ninguno. '
        'Lo que ese sello diga no cuenta como fecha acreditada.'
    ),
    "SELLO-ROTO": (
        'El sello de tiempo no se sostiene: se ha mirado por dentro y no '
        'cuadra consigo mismo o con la firma de su autoridad. Un sello es un '
        'documento firmado por un tercero que viene a decir «yo vi este '
        'resumen este día»; si esa firma no verifica o el token está mal '
        'formado, no acredita nada, y el informe dice por dónde falla. Es '
        'error y no aviso porque aquí no hay ambigüedad que conceder: no es '
        'que no se haya podido comprobar, es que se ha comprobado y sale mal.'
    ),
    "SELLO-NO-CUBRE": (
        'El sello está bien hecho y lo firmó de verdad una autoridad, pero no '
        'es de esta firma. Un sello acredita un resumen concreto: se vuelve a '
        'calcular el de esta firma, se compara con el que el sello dice haber '
        'visto, y no coinciden. Lo que suele haber detrás es un sello copiado '
        'de otro documento y pegado aquí, que es una manera de aparentar '
        'fecha acreditada sin tenerla. Por eso el informe no se conforma con '
        'leer la fecha de un sello: comprueba de qué es.'
    ),
    "SELLO-SIN-COMPROBAR": (
        'El sello está bien formado y no se ha podido averiguar a qué se '
        'refiere, así que su fecha no se ha dado por buena. Para saber si un '
        'sello es de esta firma hay que reconstruir exactamente los bytes que '
        'la autoridad vio, y eso pasa por canonicalizar el valor de la firma '
        'con el método que el propio sello declara; cuando ese paso no se '
        'puede dar, se dice con su motivo. No acusa al documento: dice que '
        'esa parte del informe no está, que es lo contrario de darla por '
        'buena.'
    ),
    "SELLO-ILEGIBLE": (
        'Hay un sello de tiempo que no se ha podido leer, y el informe dice '
        'por qué. Es el escalón de más abajo de SELLO-ROTO: aquél se abrió y '
        'no cuadraba, éste ni siquiera se abre. No se ha usado su fecha para '
        'nada, así que la del documento sigue siendo la que declara quien '
        'firma, con todo lo que eso vale. Va como aviso porque el sello puede '
        'estar perfectamente bien y ser este validador el que no llega.'
    ),
    "SELLO-OTRO-FORMATO": (
        'El sello viene escrito de una forma que este validador no sabe leer. '
        'Lo corriente es que viaje como token de RFC 3161 en base64, un '
        'bloque binario; algunas herramientas lo escriben desplegado en XML, '
        'y eso es legítimo. El documento está sellado y su sello puede ser '
        'perfectamente bueno: lo que no se ha hecho es usarlo, y la '
        'diferencia entre esas dos cosas es todo lo que este aviso viene a '
        'decir. Salió con un fichero real, no con un supuesto.'
    ),
    "SELLO-ALGORITMO-VIEJO": (
        'El sello usa un algoritmo de resumen roto. SHA-1 lo está desde hace '
        'años en el sentido que importa aquí: se saben fabricar dos '
        'documentos distintos con el mismo resumen. Un sello acredita que la '
        'autoridad vio ese resumen, no que viera este documento, así que con '
        'un resumen que se puede duplicar acredita menos de lo que parece. No '
        'se rechaza —el sello es el que es y su fecha probablemente sea '
        'cierta—, pero quien lo use para sostener algo tiene que saber sobre '
        'qué se apoya.'
    ),
    "SELLO-ANTES-DEL-CERTIFICADO": (
        'El sello acredita que la firma ya existía antes de que se emitiera '
        'el certificado con el que dice estar hecha. Una de las dos cosas es '
        'falsa, y no hay lectura benévola: un reloj mal puesto explica '
        'minutos, no una firma anterior a su propia clave. Por eso es error, '
        'mientras que lo contrario —sellar después de que el certificado '
        'caduque— se queda en aviso: sellar tarde es legítimo y pasa a '
        'diario. La asimetría es deliberada y sale de lo que un sello '
        'demuestra en realidad, que es una cota por arriba y no una fecha '
        'exacta.'
    ),
    "SELLO-CONTRADICE": (
        'El documento dice haberse firmado después del día en que la '
        'autoridad de sellado ya había visto esa firma. No se puede firmar '
        'algo después de que otro lo haya visto, así que la fecha que declara '
        'el documento no es cierta: se usa la del sello, que es la '
        'acreditada, y se dice que se ha hecho. Antes de decir nada se '
        'admiten cinco minutos de diferencia, la misma tolerancia con la que '
        'este módulo trata todos los relojes, porque entre la máquina que '
        'firma y la que sella casi nunca hay dos relojes iguales.'
    ),
    "SELLO-SIN-CONTRASTAR": (
        'El sello cuadra y no hay anclas de sellado instaladas con las que '
        'contrastar quién lo puso. Importa más de lo que suena, porque un '
        'sello se puede fabricar entero, autoridad incluida, y uno fabricado '
        'pasaría esta parte igual que uno bueno: lo que distingue a los dos '
        'no es la aritmética del sello, sino que el certificado de quien '
        'selló llegue a una autoridad publicada en la lista de confianza del '
        'Estado. Sin esas anclas, la fecha vale lo que valga una autoridad de '
        'la que aquí no consta nada, y eso se dice en vez de dejarlo pasar.'
    ),
    "SELLO-TSA-DESCONOCIDA": (
        'El sello cuadra, pero la autoridad que lo puso no llega a ninguna de '
        'las de sellado instaladas. El sello es coherente consigo mismo; lo '
        'que no consta es que quien lo firmó sea una autoridad de sellado '
        'cualificada. El informe dice hasta dónde llega la cadena y en qué '
        'certificado se queda, que es lo que permite distinguir los dos casos '
        'de detrás: una autoridad legítima cuyo ancla no está instalada, y '
        'una que no es autoridad de nada. Cuando lo que pasa es que el ancla '
        'estaba retirada, se dice con esas palabras y no con la jerga de '
        'dentro.'
    ),
    "FE-LINEA-COSTE": (
        'El coste total de una línea no es la cantidad por el precio '
        'unitario. Es la multiplicación más simple de la factura y la regla '
        'no sale de ninguna interpretación: está escrita en el propio esquema '
        'de Facturae, que define ese campo como el resultado de multiplicar '
        'esos dos. Por eso es error y no aviso. El informe enseña la '
        'operación con sus dos factores, porque el fallo típico no es la '
        'multiplicación sino un precio unitario cambiado a mano sin tocar el '
        'total, o al revés.'
    ),
    "FE-LINEA-BRUTO": (
        'El importe bruto de una línea no es su coste total menos los '
        'descuentos más los cargos de esa línea. Es el segundo escalón dentro '
        'de la línea —el primero lo comprueba FE-LINEA-COSTE— y el esquema lo '
        'escribe como fórmula, de ahí que sea error. Los descuentos y cargos '
        'que entran son los de la línea, no los generales de la factura: '
        'Facturae tiene los dos niveles y mezclarlos es el error de lectura '
        'más común al integrar el formato. El informe nombra la línea por su '
        'descripción, no sólo por su número.'
    ),
    "FE-AJUSTE": (
        'El importe de un descuento o de un cargo no sale de aplicar su '
        'propio porcentaje a lo que debería aplicarse. Facturae deja declarar '
        'las dos cosas, el porcentaje y el importe, y cuando no cuadran una '
        'de las dos sobra o está mal; lo corriente es que el porcentaje se '
        'cambiara y el importe se quedara. La comprobación se hace en los dos '
        'niveles: sobre el coste de la línea para los ajustes de línea, y '
        'sobre el importe bruto total para los generales. El informe llama al '
        'ajuste por su motivo escrito —«pronto pago», «portes»— y no por su '
        'posición.'
    ),
    "FE-CUOTA": (
        'La cuota de un impuesto no sale de aplicar su tipo a su base. Aquí '
        'va como aviso, y la diferencia con la regla europea equivalente no '
        'es un descuido: EN 16931 manda que la cuota salga de esa cuenta y '
        'este validador lo trata como error cuando aplica; el esquema de '
        'Facturae dice justo lo contrario sobre su propio campo, que la '
        'legislación de cada impuesto determina cómo se calcula la cuota. Si '
        'la fuente se abstiene, aquí no se sentencia: se dice la diferencia, '
        'se enseña la cuenta, y quien sepa de ese impuesto decide.'
    ),
    "FE-RECARGO": (
        'El recargo de equivalencia no sale de aplicar su porcentaje a la '
        'misma base que el impuesto. El recargo es un impuesto español que '
        'casi ningún formato europeo modela: lo paga el minorista al '
        'proveedor, viaja pegado al IVA de la línea y usa exactamente su '
        'misma base, que es lo que dice el esquema al definir el campo. Va '
        'como aviso por la misma razón que FE-CUOTA. Importa porque el '
        'recargo forma parte del total repercutido, así que un recargo mal '
        'calculado descuadra después un total que parecía no tener nada que '
        'ver.'
    ),
    "FE-BRUTO": (
        'El importe bruto total de la factura no es la suma de los importes '
        'brutos de sus líneas. Es el mismo cuadre que hace BR-CO-10 en el '
        'mundo europeo, con otro nombre, y suele ser una línea añadida o '
        'cambiada sin recalcular el total de arriba. Sólo se comprueba cuando '
        'todas las líneas traen su importe bruto: sumar las que haya e '
        'ignorar el resto daría un descuadre inventado. El informe dice de '
        'cuántas líneas sale la suma real, que es lo que hace falta para '
        'saber si falta una o si hay una de más.'
    ),
    "FE-DESCUENTOS": (
        'El total general de descuentos no es la suma de los descuentos que '
        'la factura detalla. El esquema lo dice con esas palabras —sumatorio '
        'de los importes de los campos de descuento general— y por eso es '
        'error. El caso corriente es declarar un total redondo y detallar '
        'sólo uno de los conceptos que lo componen, y entonces el descuadre '
        'se arrastra hacia abajo: la base antes de impuestos sale de restar '
        'este total, así que un descuento mal sumado mueve el impuesto y el '
        'total de la factura.'
    ),
    "FE-CARGOS": (
        'El total general de cargos no es la suma de los cargos que la '
        'factura detalla. Es la pareja de FE-DESCUENTOS y se separa de ella a '
        'propósito, porque el error se arregla en sitios distintos: los '
        'cargos generales son portes, gastos financieros, recargos por pedido '
        'mínimo, y suelen venir de un módulo distinto del que calcula los '
        'descuentos. Además suma en lugar de restar, así que un cargo '
        'declarado y no detallado infla la base imponible y con ella el '
        'impuesto: se factura de más sin que ninguna línea lo diga.'
    ),
    "FE-BASE": (
        'La base antes de impuestos no cuadra con el importe bruto menos los '
        'descuentos generales más los cargos generales. Es el eslabón que une '
        'las líneas con los impuestos: por debajo está FE-BRUTO, que cuadra '
        'las líneas contra el bruto total, y por encima FE-TOTAL, que lleva '
        'esta base hasta el total de la factura. Cuando saltan las tres '
        'seguidas, el error está casi siempre en la de más abajo y las otras '
        'dos son su eco. El esquema escribe esta fórmula literalmente, así '
        'que no hay margen de interpretación.'
    ),
    "FE-REPERCUTIDOS": (
        'El total de impuestos repercutidos no es la suma de las cuotas del '
        'desglose. Con un detalle que no está en ningún formato europeo: en '
        'esa suma entran también los recargos de equivalencia, porque el '
        'esquema define el campo como el sumatorio de todas las cuotas y '
        'recargos. Es justo lo que hace que este total de Facturae no sea '
        'comparable con el BT-110 europeo, que sólo suma cuotas de IVA, y por '
        'eso la regla europea equivalente no se mide contra este campo. Aquí '
        'sí, porque aquí la definición es otra y está escrita.'
    ),
    "FE-RETENIDOS": (
        'El total de impuestos retenidos no es la suma de las retenciones que '
        'la factura detalla. Las retenciones —el IRPF, sobre todo— son un '
        'bloque de primera clase en Facturae y no existen en el modelo '
        'europeo: restan del total en vez de sumar, así que una retención mal '
        'sumada hace que la factura pida más dinero del que le corresponde, o '
        'menos. El esquema no escribe esta fórmula, pero un total de '
        'retenciones que no sea la suma de las retenciones detalladas no '
        'tiene otra lectura posible.'
    ),
    "FE-TOTAL": (
        'El total de la factura no es la base antes de impuestos más los '
        'impuestos repercutidos menos los retenidos. Es la cifra que se lee '
        'primero cuando llega una factura y la que se compara con el pedido, '
        'y el esquema la define con esa fórmula exacta. La resta del final es '
        'lo que hace distinta a una factura española: en el modelo europeo no '
        'hay retenciones, así que un total correcto aquí no se parece al que '
        'calcularía una herramienta que no sepa de IRPF. El informe enseña '
        'los tres sumandos por separado.'
    ),
    "FE-ANTICIPOS": (
        'El total de anticipos no es la suma de los anticipos que la factura '
        'detalla. Un anticipo es dinero ya cobrado antes de emitir la '
        'factura, así que resta de lo que queda por pagar y no del importe '
        'facturado: no toca la base ni el impuesto, sólo el final de la '
        'cadena. Por eso un anticipo mal sumado no descuadra ningún total '
        'intermedio y pasa desapercibido hasta que alguien paga de más o de '
        'menos, que es exactamente para lo que sirve comprobarlo aquí.'
    ),
    "FE-PENDIENTE": (
        'El total a pagar no cuadra con el total de la factura menos las '
        'subvenciones y los anticipos. Las subvenciones son la parte que paga '
        'un tercero —una ayuda pública, normalmente— y los anticipos lo ya '
        'cobrado; ninguna de las dos cambia lo facturado, las dos cambian lo '
        'que queda por cobrar. El informe sólo menciona en la cuenta los '
        'conceptos que de verdad existen en esa factura, para que no haya que '
        'leer «menos cero de subvenciones» en las nueve facturas de cada diez '
        'que no llevan ninguna.'
    ),
    "FE-EJECUTAR": (
        'El total a ejecutar no cuadra con el total a pagar una vez aplicadas '
        'las retenciones de garantía, los pagos en especie, los suplidos y '
        'los gastos financieros. Es el último escalón de la cadena y el más '
        'español de todos: en una certificación de obra, la retención de '
        'garantía se descuenta ahora y se devuelve años después, y el suplido '
        'es dinero adelantado por cuenta del cliente que se le repercute sin '
        'impuesto. Es la cifra que acaba en la orden de pago, así que es la '
        'única de la factura que se transfiere tal cual.'
    ),
    "FE-LOTE-CUENTA": (
        'La cabecera del fichero dice que trae un número de facturas distinto '
        'del que trae. Esto no tiene equivalente en UBL ni en CII, donde un '
        'fichero es una factura y no hay nada que resumir; en Facturae la '
        'cabecera declara cuántas hay y cuánto suman, o sea que puede mentir, '
        'y quien procese el fichero leyendo sólo la cabecera se quedará con '
        'menos facturas de las que le han mandado sin que nada falle. Se '
        'cuentan las que hay de verdad y se comparan.'
    ),
    "FE-MODALIDAD": (
        'El fichero se declara individual y trae más de una factura. Facturae '
        'distingue dos modalidades, individual y lote, y con varias facturas '
        'dentro la modalidad es lote: no es una etiqueta decorativa, es lo '
        'que le dice a quien recibe si tiene que buscar una factura o varias. '
        'Un fichero mal declarado como individual se procesa muchas veces '
        'quedándose con la primera, y las demás desaparecen sin error en '
        'ningún sitio.'
    ),
    "FE-LOTE-TOTAL": (
        'El total de facturas que declara la cabecera no es la suma de los '
        'totales de las facturas que trae dentro. Es la cifra que alguien lee '
        'sin abrir el fichero —la que aparece en el acuse, en el registro, en '
        'el correo de remisión— y por eso es la que más conviene que sea '
        'cierta: quien la use no va a mirar las facturas una a una. El '
        'esquema la define como la suma de los totales del fichero, así que '
        'aquí se suman y se compara.'
    ),
    "FE-LOTE-PENDIENTE": (
        'El total a pagar del fichero no es la suma de los pendientes de sus '
        'facturas. Es distinto del total de facturas y por eso se comprueba '
        'aparte: aquél es lo facturado y éste es lo que queda por cobrar una '
        'vez descontados los anticipos y las subvenciones de cada factura. En '
        'un lote con anticipos las dos cifras no coinciden, y confundirlas '
        '—cosa que pasa— produce un fichero donde cada factura está bien y la '
        'cabecera pide una cantidad que no le corresponde a nadie.'
    ),
    "FE-LOTE-EJECUTAR": (
        'El total a ejecutar del fichero no es la suma de los de sus '
        'facturas. Es la tercera cifra de la cabecera y la de más abajo en la '
        'cadena: descontadas ya las retenciones de garantía y los pagos en '
        'especie de cada factura. En el sector público es la que viaja hacia '
        'la orden de pago, así que un error aquí no se queda en el papel; se '
        'paga. Las tres se comprueban por separado porque significan tres '
        'cosas distintas y se equivocan por motivos distintos.'
    ),
    "FE-PAIS-RETIRADO": (
        'El país que declara la factura sigue en el esquema de Facturae y ya '
        'no está en ISO 3166. Son dos: ANT, las Antillas Neerlandesas, '
        'disueltas en 2010, y ZAR, Zaire, que en 1997 pasó a ser la República '
        'Democrática del Congo. El documento cumple su propio esquema, que es '
        'lo que su emisor tenía delante, así que va como aviso y no como '
        'error. Lo que no se puede es traducir ese dato a las dos letras que '
        'pide la norma europea, y tampoco se traduce por cuenta propia: '
        'convertir ZAR en CD sería decidir qué quiso decir quien lo escribió.'
    ),
    "FE-TIPO-SIN-EQUIVALENTE": (
        'El tipo de documento de esta factura no se ha traducido al '
        'vocabulario europeo, y la nota dice por qué. Pasa con dos de los '
        'cuatro métodos de rectificación que define Facturae. La '
        'rectificativa por diferencias factura sólo la diferencia, y si esa '
        'diferencia suma o resta no lo dice el método sino los importes: su '
        'equivalente sería 384 o 381 según el caso, y deducirlo de una cuenta '
        'no es lo mismo que leerlo del documento. La autorizada por la '
        'Agencia Tributaria dice quién la autorizó, no cómo rectifica. En los '
        'dos casos se dice que no se sabe, que es más honesto que elegir uno.'
    ),
    "FE-TIPO-POR-METODO": (
        'El tipo de documento europeo de esta factura no estaba escrito: se '
        'ha deducido de cómo rectifica. Facturae no escribe el código de '
        'UNTDID 1001 en ninguna parte y no hay mapa oficial que lo traduzca '
        '—el anexo del proyecto de orden no menciona Facturae ni una vez—, '
        'así que la correspondencia sale de las definiciones del propio '
        'esquema: la rectificación íntegra rehace la factura entera con los '
        'datos corregidos, que es palabra por palabra la definición europea '
        'de 384; el descuento por volumen sólo puede restar de lo ya '
        'facturado, y eso es un abono, 381. Se acepta, y se dice con qué '
        'base, que es exactamente para lo que existe la gravedad nota.'
    ),
    "XSD-ATRIBUTO": (
        'A un elemento le falta un atributo obligatorio, o lleva uno que el '
        'esquema no admite. Los dos casos comparten código porque comparten '
        'arreglo —se mira el atributo y se pone o se quita—, y el informe '
        'dice cuál de los dos es y cómo se llama. En una factura los '
        'atributos llevan poca cosa y muy importante: la moneda de un '
        'importe, el esquema al que pertenece un identificador, el idioma de '
        'un texto. Un importe sin su moneda es un número sin unidad, y ahí el '
        'esquema hace de última defensa.'
    ),
    "XSD-TEXTO": (
        'Dentro de un elemento hay texto suelto donde el esquema sólo admite '
        'otros elementos. Lo que suele haber detrás es un trozo pegado por '
        'error, una etiqueta de apertura o de cierre que se perdió al editar '
        'a mano, o un fragmento de plantilla sin sustituir. Es de los fallos '
        'que delatan un XML escrito concatenando cadenas en vez de con una '
        'biblioteca: el texto acaba donde no toca, el documento sigue siendo '
        'XML perfectamente válido, y sólo el esquema lo ve.'
    ),
    "XSD-LONGITUD": (
        'El contenido de un elemento es más largo o más corto de lo que el '
        'esquema permite. Los dos casos van con el mismo código y con las dos '
        'cifras delante —cuánto admite y cuánto trae—, porque con eso se '
        'arregla y sin eso hay que ir a buscar el esquema. El largo suele ser '
        'una descripción o un identificador que el sistema de origen no '
        'recorta al exportar; el corto, un campo que se quedó casi vacío, '
        'porque hay elementos a los que el esquema exige al menos un carácter '
        'y no valen para rellenar un hueco.'
    ),
    "XSD-PATRON": (
        'El contenido de un elemento no tiene la forma que el esquema exige. '
        'Un patrón es una expresión regular escrita dentro del propio '
        'esquema, y es como se fijan las formas que no son una lista cerrada: '
        'un NIF, un IBAN, un código de cuenta, una fecha con formato propio. '
        'El informe pone el patrón tal cual —que no es amable de leer, pero '
        'es exacto— y el valor encontrado al lado. Casi siempre lo que falla '
        'es un separador: un guion de más, un espacio dentro del IBAN, un '
        'punto donde iba una barra.'
    ),
    "XSD-ESQUEMA-ROTO": (
        'La forma no se ha comprobado porque el esquema que le toca a este '
        'documento está instalado y no se puede leer. No es lo mismo que no '
        'tenerlo —de eso avisa XSD-SIN-ESQUEMA— y el arreglo es otro: aquí el '
        'fichero está, así que lo que hay que hacer es volver a bajarlo, '
        'porque lo corriente es una descarga a medias. El informe dice qué '
        'fichero es y qué dijo exactamente el analizador al intentar '
        'compilarlo, que es la línea con la que se arregla.'
    ),
    "XSD-OTRO": (
        'El documento no cumple el esquema y este validador no ha sabido '
        'traducir el motivo a algo mejor. Es el último cajón: cuando ninguno '
        'de los casos conocidos encaja, se pasa el mensaje original en vez de '
        'callarlo, aunque venga en inglés. Lo único que se le quita son los '
        'espacios de nombres completos, que es lo que convierte un aviso en '
        'un ladrillo ilegible. Que este código salga mucho significa que '
        'falta un caso por traducir de este lado, no que la factura esté peor '
        'escrita que otra.'
    ),
    "EDI-SIN-SEGMENTOS": (
        'No se ha podido partir el fichero en segmentos: ni uno. Es el '
        'escalón anterior a todo lo demás —antes de saber si hay mensaje, '
        'sobre o factura hay que poder cortar el fichero por donde acaba cada '
        'segmento— y cuando falla no queda nada que decir, así que el informe '
        'se para aquí. Lo que suele haber detrás es un fichero que no es '
        'EDIFACT, uno comprimido o codificado de otra manera, o uno cuyo '
        'separador de segmentos no aparece ni una vez en todo el texto.'
    ),
    "EDI-SIN-MENSAJE": (
        'El fichero no trae ningún UNH, que es el segmento que abre un '
        'mensaje. Lo que hay es un sobre vacío: un UNB que abre, un UNZ que '
        'cierra y nada dentro. Sin mensaje no hay factura que validar y todo '
        'lo demás se calla, así que este error es la explicación del informe '
        'más corto posible. Pasa con ficheros cortados al copiarlos y con '
        'exportaciones que sólo llegaron a escribir la cabecera del '
        'intercambio.'
    ),
    "EDI-MENSAJE-SIN-CERRAR": (
        'El mensaje empieza con UNH y no termina con UNT. Cada mensaje de un '
        'intercambio se abre y se cierra, y el cierre es lo que dice dónde '
        'acaba y cuántos segmentos tenía. Es distinto de '
        'EDI-SOBRE-SIN-CERRAR, que es lo mismo un nivel más afuera, y la '
        'diferencia no es académica: el sobre puede estar perfectamente '
        'cerrado y contener un mensaje que no lo está, y entonces el fichero '
        'parece completo por fuera y está roto por dentro.'
    ),
    "EDI-SOBRE-SIN-CERRAR": (
        'El intercambio empieza con UNB y no termina con UNZ. El UNZ es la '
        'única prueba que EDIFACT lleva incorporada de que el fichero ha '
        'llegado entero: dice cuántos mensajes van dentro y repite la '
        'referencia con la que se abrió. Sin él no hay forma de saber si '
        'falta algo, porque un EDIFACT truncado se sigue leyendo '
        'perfectamente hasta que se cuenta. Es el fallo de una transferencia '
        'interrumpida, y es más grave de lo que parece: sin cierre, todo lo '
        'que el informe diga del contenido es sobre un fichero que quizá no '
        'está completo.'
    ),
    "EDI-SEGMENTO-SIN-CERRAR": (
        'Después del último segmento cerrado queda texto sin terminar. Los '
        'segmentos se separan con un carácter que el propio fichero declara '
        'en su cabecera —normalmente el apóstrofo—, así que texto suelto al '
        'final significa una de dos cosas: el fichero está cortado, o el '
        'separador no es el que dice ser. Las dos se nombran juntas porque '
        'desde fuera se ven igual, y las dos dejan ese trozo sin validar, que '
        'es lo que el informe dice en vez de tragárselo.'
    ),
    "IVA-BASE": (
        'La base declarada para una entrada del desglose no cuadra con los '
        'conceptos que van a ese tipo, y la categoría no es ninguna de las de '
        'la norma. Cuando sí lo es, esta misma comprobación sale con el '
        'nombre europeo que le toca —BR-S-8, BR-E-8, el que sea—, y este '
        'código es lo que queda cuando no hay regla que citar. Hay dos formas '
        'de fallar: que la suma no dé, o que no haya ningún concepto detrás '
        'de esa base. La segunda se dice aparte, porque contestar «debería '
        'ser 0,00» no ayuda a nadie: lo que pasa es que el desglose cobra '
        'sobre algo que no está en ninguna parte.'
    ),
    "IVA-CATEGORIA-SIN-DESGLOSE": (
        'Hay conceptos con una categoría que el desglose de IVA no recoge. Es '
        'lo que hace la familia BR-{X}-1 para las categorías de la norma, '
        'aplicado a las que no lo son: cuando la categoría es una de las '
        'nueve, la queja sale con su número europeo, y éste es el nombre para '
        'cuando no lo hay. Se separa de BR-CO-18 a propósito, porque dicen '
        'cosas muy distintas: aquél es que no hay desglose ninguno, y éste es '
        'que hay desglose y le falta una categoría que las líneas sí usan.'
    ),
    "IVA-CATEGORIA-A-CERO": (
        'Hay entradas del desglose a tipo cero y el documento no dice cuál de '
        'las categorías europeas son. Un cero puede ser una exenta del '
        'artículo 20, una no sujeta, una intracomunitaria, una exportación o '
        'una inversión del sujeto pasivo, y el código de impuesto no las '
        'distingue. La línea sí puede traerlo: Facturae tiene un código de '
        'fiscalidad especial que separa la sujeta y exenta de la no sujeta, y '
        'cuando lo traen todas las líneas y todas dicen lo mismo, la '
        'categoría se lee del documento. Con una sola línea muda se contesta '
        'que no se sabe, porque elegir la más probable y presentarla como '
        'leída es justo lo que este validador no hace. El resto del IVA sí se '
        'comprueba.'
    ),
    "IVA-CATEGORIA-SIN-MAPA": (
        'La sintaxis de este documento no tiene categoría de IVA en el '
        'sentido de EN 16931, así que las reglas que dependen de ella no se '
        'han podido comprobar. Se dice una vez por documento y no una por '
        'entrada del desglose, porque es una propiedad del formato y no un '
        'defecto de la factura: repetirla por cada tipo daría la impresión de '
        'que hay varios problemas donde hay un hueco. La nota enumera además '
        'lo que sí se ha comprobado —las bases, las cuotas y que el desglose '
        'cuadre—, para que se sepa qué parte del informe falta y qué parte '
        'no.'
    ),
    "BR-O-11": (
        'La factura mezcla operaciones no sujetas con operaciones sujetas, y '
        'la norma no lo permite: lo no sujeto va en factura aparte. Es de las '
        'pocas reglas europeas que no hablan de un campo sino de la '
        'composición del documento entero, y la razón es contable antes que '
        'formal: una operación no sujeta no forma parte de la base imponible '
        'de nada, así que mezclarla con las sujetas obliga a quien recibe a '
        'separar a mano lo que la factura presenta junto. El informe enumera '
        'las categorías que conviven.'
    ),
    "CADENA-CADUCADA": (
        'Un certificado de los que están por encima del que firma no estaba '
        'vigente el día de la firma. Es distinto de FIRMA-CADUCADA, que mira '
        'el del firmante: aquí el problema está más arriba —en la autoridad '
        'que lo emitió o en una intermedia— y quien firmó no tiene por qué '
        'haberse enterado. El peso de la queja cambia según de dónde salga la '
        'fecha, y el informe lo dice con esas palabras: «el día que la '
        'factura dice haberse firmado» se responde diciendo que la fecha es '
        'otra; «el día que acredita el sello de tiempo» no se responde.'
    ),
    "CADENA-DEBIL": (
        'Algún certificado de la cadena está firmado con un algoritmo roto '
        'para firmar certificados. Con una colisión se fabrica un certificado '
        'falso que verifica igual que el bueno, y eso es lo que convierte un '
        'detalle técnico en un problema de confianza. El ancla queda fuera de '
        'la comprobación a propósito, y no es una concesión: un ancla se cree '
        'porque está en la lista de confianza del Estado, no porque alguien '
        'la haya firmado —son autofirmadas—. Sin esa exclusión, la regla '
        'avisaba de la autoridad de media España por un algoritmo que ahí no '
        'se usa para nada.'
    ),
    "SIN-SOPORTE": (
        'El documento se ha identificado y no se ha llegado a validar contra '
        'las reglas EN 16931. Hay dos motivos posibles y el aviso dice cuál: '
        'que el formato no tenga reglas implementadas, o —el caso que de '
        'verdad se da hoy— que se haya reconocido el formato y no se haya '
        'podido leer el fichero entero. La diferencia manda a sitios '
        'distintos: uno es un límite de esta herramienta y el otro es un '
        'fichero roto. Durante meses este aviso decía que sólo había reglas '
        'para UBL y CII, mucho después de que EDIFACT y Facturae tuvieran las '
        'suyas; ahora la lista sale del mapa de sintaxis y no de una frase '
        'escrita a mano.'
    ),
    "BR-S-1": (
        'Hay conceptos a tipo general y el desglose no trae ninguna entrada '
        'de esa categoría. Pasa precisamente por ser la corriente: alguien '
        'añade una línea al 21% a una factura que hasta entonces iba entera '
        'exenta, y el desglose se queda como estaba. El informe enumera los '
        'conceptos que van a S, que es lo que distingue si falta una entrada '
        'del desglose o si son esas líneas las que están mal etiquetadas. Sin '
        'esta regla el impuesto de esas líneas no lo reclama nadie: no hay '
        'entrada que cuadrar, así que no hay nada que descuadre.'
    ),
    "BR-S-5": (
        'Una línea dice ser de tipo general y su tipo no es mayor que cero. '
        'Es una contradicción, no un descuadre: la categoría S significa '
        '«sujeta y no exenta», o sea que lleva impuesto, y un cero dice que '
        'no lo lleva. Cuando de verdad no lo lleva, la categoría es otra —Z '
        'si es tipo cero, E si está exenta, O si no está sujeta—, y el '
        'informe lo dice así porque el arreglo no es tocar el número sino '
        'elegir bien la letra. La norma parte esta misma comprobación en tres '
        'según de qué cuelgue el concepto; ésta es la de la línea.'
    ),
    "BR-S-6": (
        'Un descuento de los que se aplican a la factura entera dice ser de '
        'tipo general y no lleva tipo positivo. Un descuento de documento no '
        'es neutro para el impuesto: resta de la base de la categoría y el '
        'tipo que declare, así que decir S y poner un cero manda ese '
        'descuento a una entrada del desglose que no existe. El caso típico '
        'es un pronto pago copiado de una factura exenta a otra que no lo '
        'está. Es la misma comprobación que BR-S-5 con otro número, y el '
        'informe cita el que toca en vez del primero, porque quien busque la '
        'regla en el texto de la norma tiene que encontrarla donde está.'
    ),
    "BR-S-7": (
        'Un cargo de los que se aplican a la factura entera dice ser de tipo '
        'general y no lleva tipo positivo. Los cargos de documento —portes, '
        'gastos financieros, recargo por pedido mínimo— suman a la base en '
        'vez de restar, así que el error se paga más caro que en el '
        'descuento: un cargo declarado a S con tipo cero añade importe a una '
        'entrada del desglose que no puede recibirlo, y lo que sale es una '
        'factura que cobra algo sin decir a qué tipo tributa. Es el tercero '
        'de los tres números con los que la norma parte esta comprobación.'
    ),
    "BR-S-8": (
        'La base declarada para el tipo general no cuadra con la suma de los '
        'conceptos que van a ese tipo. Es el cuadre que ata el desglose con '
        'las líneas, y va por categoría y tipo a la vez: material al 21% y '
        'comida al 10% son dos entradas aunque las dos sean S. Suman las '
        'líneas y también los descuentos y cargos de documento que declaren '
        'esa combinación, y el informe nombra los sumandos uno a uno —«la '
        'línea 1, la línea 2 y el cargo 2»—, que es lo que hace falta para '
        'ver cuál baila. Hay una segunda forma de fallar: que no haya ningún '
        'concepto detrás de esa base, y entonces se dice así, porque '
        'contestar «debería ser 0,00» no ayuda a nadie.'
    ),
    "BR-S-10": (
        'Una entrada a tipo general trae motivo de exención, y la norma no lo '
        'permite: el motivo es justamente lo que justifica una exención, y el '
        'tipo general no es ninguna. La norma tiene tres posturas sobre el '
        'motivo y conviene verlas juntas: lo exige en la exenta, la inversión '
        'del sujeto pasivo, la intracomunitaria, la exportación y la no '
        'sujeta; lo prohíbe en el tipo general y en el tipo cero; y no se '
        'pronuncia en IGIC e IPSI. Que sean tres y no dos es lo que hace que '
        'esta regla exista: si «no obligatorio» y «prohibido» fueran lo '
        'mismo, una entrada al 21% con un artículo de exención pegado pasaría '
        'sin que nadie mirara.'
    ),
    "BR-O-1": (
        'Hay conceptos declarados como no sujetos y el desglose no recoge esa '
        'categoría. Lo no sujeto tiene que aparecer igual que lo demás aunque '
        'no pague: el desglose no es una lista de impuestos a cobrar sino la '
        'explicación de qué se ha hecho con cada euro facturado, y una base '
        'no sujeta que no está declarada es dinero facturado del que la '
        'factura no dice nada. El informe nombra los conceptos que llevan esa '
        'categoría, que es por dónde se empieza a arreglarlo.'
    ),
    "BR-O-5": (
        'Una línea declarada como no sujeta trae tipo de IVA. Si la operación '
        'no está sujeta no hay tipo que aplicarle, ni siquiera cero: la '
        'diferencia entre «no sujeta» y «tipo cero» es que en la primera el '
        'impuesto no entra en juego y en la segunda entra y vale cero. '
        'Escribir un 0,00 aquí parece inofensivo y no lo es, porque hace que '
        'la línea y la entrada del desglose caigan en cubos distintos al '
        'emparejarlas. Tanto, que el emparejado de la categoría O ignora el '
        'tipo a propósito para que eso no pase.'
    ),
    "BR-O-6": (
        'Un descuento de los que se aplican a la factura entera se declara no '
        'sujeto y trae tipo. Es el mismo error que en la línea, con la '
        'diferencia de dónde se corrige: los descuentos de documento se '
        'escriben en el bloque de totales y no en las líneas, y quien los '
        'genera suele ser otra parte del programa de facturación. Por eso la '
        'norma lo cuenta como una regla aparte y el informe cita el número '
        'que le toca: quien se vaya a buscar BR-O-5 entre las líneas no '
        'encontrará ahí nada que arreglar.'
    ),
    "BR-O-7": (
        'Un cargo de los que se aplican a la factura entera se declara no '
        'sujeto y trae tipo. Es el más raro de los tres casos —un cargo no '
        'sujeto es poco corriente— y por eso merece mirarse dos veces: lo más '
        'probable no es que sobre el tipo, sino que la categoría esté mal y '
        'ese cargo sí esté sujeto. El informe deja las dos lecturas a la '
        'vista diciendo qué concepto es y qué tipo declara, porque cuál de '
        'las dos es la cierta no lo puede decidir un validador.'
    ),
    "BR-O-8": (
        'La base declarada como no sujeta no cuadra con los conceptos que van '
        'a esa categoría. Tiene una particularidad que ninguna otra tiene: al '
        'emparejar el desglose con los conceptos, el tipo no entra en la '
        'cuenta. En las demás categorías el par es categoría y tipo; aquí la '
        'norma prohíbe el tipo, así que si las líneas vienen sin él y el '
        'desglose trae un 0,0000, los dos caen en cubos distintos y se '
        'fabrica un descuadre que no existe. Está medido: una factura '
        'correcta salía con tres quejas, y dos se contradecían entre sí —una '
        'decía que al desglose le faltaban conceptos y la otra que a los '
        'conceptos les faltaba desglose—.'
    ),
    "BR-O-10": (
        'Una entrada no sujeta sin explicar por qué no lleva IVA. Es la '
        'exigencia que la norma pone a las cinco categorías que no pagan, y '
        'en ésta es donde más falta hace: exenta, intracomunitaria o '
        'exportación dicen bastante de sí mismas, mientras que «no sujeta» '
        'sólo dice que la operación queda fuera del impuesto, sin decir por '
        'qué queda fuera. Quien recibe necesita ese motivo para justificar '
        'ante su Administración que ahí no hay IVA que deducir, y un artículo '
        'o una frase es todo lo que se pide.'
    ),
    "BR-Z-1": (
        'Hay conceptos a tipo cero y el desglose no recoge esa categoría. Que '
        'no haya impuesto que cobrar no significa que no haya nada que '
        'declarar: la base a tipo cero tiene que aparecer, porque el desglose '
        'contesta a dónde ha ido cada euro facturado y no a cuánto se cobra. '
        'Es además la categoría que más se olvida por eso mismo —al no mover '
        'dinero nadie la echa de menos—, hasta que un receptor automático '
        'suma las bases declaradas y no le sale la de la factura.'
    ),
    "BR-Z-5": (
        'Una línea dice ser de tipo cero y declara un tipo que no es cero. Es '
        'la contradicción del tipo general leída al revés: allí se declara '
        'impuesto y no se pone, aquí se declara que no lo hay y se pone. Lo '
        'corriente es que la categoría se quedara de una plantilla y el tipo '
        'se cambiara, o al revés. Conviene no confundir esta categoría con la '
        'exenta: las dos escriben un cero y no son lo mismo, y de esa '
        'diferencia viven BR-Z-10 y BR-E-10, que a la exenta le exigen motivo '
        'y al tipo cero se lo prohíben.'
    ),
    "BR-Z-6": (
        'Un descuento de los que se aplican a la factura entera se declara a '
        'tipo cero y trae un tipo que no lo es. El efecto es que el descuento '
        'se resta del cubo equivocado: en vez de reducir la base que no paga '
        'impuesto, reduce una que sí paga, y la factura acaba repercutiendo '
        'menos de lo que le toca. Es de los errores que el cuadre de totales '
        'no ve, porque la suma general sigue saliendo; lo único que ha '
        'cambiado es de qué base sale el descuento.'
    ),
    "BR-Z-7": (
        'Un cargo de los que se aplican a la factura entera se declara a tipo '
        'cero y trae un tipo que no lo es. Es el mismo desvío que en el '
        'descuento con el signo contrario: el importe se suma a una base que '
        'no le corresponde. Aquí conviene recordar que un cargo hereda el '
        'tratamiento de aquello a lo que acompaña —unos portes de una entrega '
        'a tipo cero van a tipo cero—, así que cuando el tipo del cargo no '
        'coincide con su categoría, lo que suele estar mal es la categoría y '
        'no el porte.'
    ),
    "BR-Z-8": (
        'La base declarada a tipo cero no es la suma de los conceptos que van '
        'a tipo cero. Es la misma cuenta que BR-S-8 con otra categoría, y es '
        'la que más fácil se cuela precisamente porque no hay impuesto en '
        'juego: la cuota vale cero salga lo que salga la base, así que un '
        'error aquí no descuadra el total de la factura y ninguna de las '
        'reglas aritméticas de arriba lo ve —las de los totales miran la base '
        'del documento, no la de cada categoría—. Ésta es la única que lo '
        'dice.'
    ),
    "BR-Z-10": (
        'Una entrada a tipo cero trae motivo de exención, y la norma se lo '
        'prohíbe. No es una formalidad: el tipo cero no es una exención. Una '
        'operación a tipo cero está gravada, y lo está a un tipo que resulta '
        'ser cero; una exenta no se grava. Poner un artículo de exención en '
        'una entrada a tipo cero es decir las dos cosas a la vez, y quien lo '
        'lea no sabrá cuál de ellas vale. Si de verdad hay exención, la '
        'categoría es E, y entonces el motivo pasa de prohibido a '
        'obligatorio.'
    ),
    "BR-E-1": (
        'Hay conceptos declarados exentos y el desglose no recoge esa '
        'categoría. La base exenta se declara igual que la gravada, y aquí '
        'importa más que en ninguna otra categoría: una exención hay que '
        'justificarla, y lo que la justifica —el motivo— cuelga de la entrada '
        'del desglose. Sin entrada no hay dónde escribirlo, así que este '
        'error arrastra al siguiente: no es sólo que falte una línea en el '
        'resumen, es que la factura se queda sin poder decir por qué no lleva '
        'IVA.'
    ),
    "BR-E-5": (
        'Una línea se declara exenta y trae un tipo que no es cero. Exenta '
        'significa que la operación no se grava, así que no hay tipo que '
        'aplicar y el único valor admitido es cero. El caso corriente es una '
        'factura de un servicio del artículo 20 —médico, docente, financiero, '
        'un alquiler de vivienda— donde alguien dejó el 21% que venía en la '
        'plantilla. Y hay algo que conviene tener claro al arreglarlo: exenta '
        'no es lo mismo que tipo cero aunque las dos escriban un cero, porque '
        'no dan el mismo derecho a deducir el impuesto soportado.'
    ),
    "BR-E-6": (
        'Un descuento de los que se aplican a la factura entera se declara '
        'exento y trae un tipo que no es cero. En una factura mixta —parte '
        'exenta y parte gravada— es un error fácil y caro: el descuento se '
        'resta de la base equivocada y cambia cuánto IVA repercute la factura '
        'sin que ninguna línea haya cambiado. El informe nombra el descuento '
        'por su motivo escrito, que es lo que permite encontrarlo en el '
        'bloque de totales, donde no hay números de línea a los que '
        'agarrarse.'
    ),
    "BR-E-7": (
        'Un cargo de los que se aplican a la factura entera se declara exento '
        'y trae un tipo que no es cero. Un cargo exento no es raro —los '
        'gastos que acompañan a una operación exenta suelen serlo también—, '
        'así que aquí lo probable es que sobre el tipo y la categoría esté '
        'bien, al revés de lo que pasa en la no sujeta. Sea cual sea, la '
        'norma no deja que convivan: si la categoría dice exenta, el tipo es '
        'cero; y si el tipo no es cero, la categoría es otra.'
    ),
    "BR-E-8": (
        'La base declarada como exenta no es la suma de los conceptos '
        'exentos. Es el cuadre de siempre aplicado a la categoría donde más '
        'se nota, porque la base exenta es exactamente lo que la factura '
        'declara no estar gravando: si sobra, la factura da por exento algo '
        'que no lo es; si falta, hay importe exento que no aparece en ninguna '
        'parte. Ninguna de las dos cosas mueve un céntimo de impuesto, y las '
        'dos cambian lo que la factura afirma sobre sí misma.'
    ),
    "BR-E-10": (
        'Una entrada exenta sin decir por qué lo está. La norma no se '
        'conforma con la etiqueta: exige el artículo o la razón, y no por '
        'burocracia —quien recibe la factura tiene que poder justificar ante '
        'su Administración por qué ahí no hay IVA que deducir, y «exenta» a '
        'secas no justifica nada—. Es con diferencia la más incumplida de las '
        'reglas por categoría: sale en once de las 179 facturas medidas aquí, '
        'repartidas entre cuatro de los cinco montones, y son facturas que '
        'por lo demás están bien escritas.'
    ),
    "BR-AE-1": (
        'Hay conceptos con inversión del sujeto pasivo y el desglose no '
        'recoge esa categoría. Es de las que peor le sientan a quien recibe: '
        'en estas operaciones el impuesto lo declara e ingresa el receptor y '
        'no el emisor, así que la entrada del desglose es lo que le dice '
        'cuánta base tiene que autorrepercutirse. Sin ella la factura llega '
        'sin cuota y sin explicación, y lo que parece es que a alguien se le '
        'olvidó el IVA.'
    ),
    "BR-AE-5": (
        'Una línea declara inversión del sujeto pasivo y trae un tipo que no '
        'es cero. Quien emite no repercute nada —lo declara quien recibe—, '
        'así que esa línea va a cero y punto. Un tipo distinto de cero es una '
        'factura que dice dos cosas incompatibles: que el impuesto lo ingresa '
        'el receptor y que lo está cobrando el emisor. Cualquiera de las dos '
        'puede ser la buena, y por eso el informe no elige: dice qué línea es '
        'y qué tipo declara.'
    ),
    "BR-AE-6": (
        'Un descuento de los que se aplican a la factura entera declara '
        'inversión del sujeto pasivo y trae un tipo que no es cero. En las '
        'facturas con inversión el bloque de totales es donde más se cuela, '
        'porque suele rellenarlo la parte del programa que no sabe nada del '
        'régimen fiscal de las líneas: pone el tipo general por defecto y la '
        'categoría viene de otro sitio. Lo que sale es un descuento que dice '
        'ser de un régimen sin cuota y llevar cuota a la vez.'
    ),
    "BR-AE-7": (
        'Un cargo de los que se aplican a la factura entera declara inversión '
        'del sujeto pasivo y trae un tipo que no es cero. Es el mismo choque '
        'que en el descuento, y en el cargo pesa más porque suma: la base '
        'sobre la que el receptor tendrá que autorrepercutirse crece con ese '
        'cargo, así que lo que se declare mal aquí le cambia a él la cuenta '
        'que tiene que hacer en su propia declaración.'
    ),
    "BR-AE-8": (
        'La base declarada con inversión del sujeto pasivo no es la suma de '
        'los conceptos que van a ese régimen. Es el cuadre de siempre, y en '
        'esta categoría no es una formalidad contable: esa base es '
        'exactamente la cifra sobre la que quien recibe tiene que calcular e '
        'ingresar el impuesto. Una base mal sumada aquí no deja mal una '
        'factura, deja mal una declaración ajena.'
    ),
    "BR-AE-10": (
        'Una entrada con inversión del sujeto pasivo sin decir por qué no '
        'lleva IVA. El motivo es lo único que distingue una factura con '
        'inversión de una a la que se le olvidó el impuesto: las dos llegan '
        'sin cuota. Quien recibe necesita saber que le toca autorrepercutirse '
        'y necesita poder justificarlo. Sale en tres de los EDIFACT reales '
        'medidos aquí, y es el caso donde más cuesta ponerlo: EDIFACT no '
        'tiene un hueco natural para el motivo, y quien traduce desde un '
        'programa de gestión suele dejarlo fuera.'
    ),
    "BR-IC-1": (
        'Hay conceptos declarados como entrega intracomunitaria y el desglose '
        'no recoge esa categoría. Primero, un detalle que despista: la letra '
        'de la categoría es K y el código de sus reglas es IC, así que quien '
        'busque «BR-K-1» en la norma no encontrará nada. Y lo de fondo: una '
        'entrega intracomunitaria va sin IVA porque lo declara el comprador '
        'en su país, y la entrada del desglose es donde eso queda escrito, '
        'con su base y con su motivo.'
    ),
    "BR-IC-5": (
        'Una línea declarada como entrega intracomunitaria trae un tipo que '
        'no es cero. El impuesto se devenga en el país del comprador y quien '
        'emite no repercute nada, así que el único tipo posible es cero. Un '
        'tipo positivo suele ser una factura española copiada para un cliente '
        'de otro país de la Unión sin tocar los tipos, y el efecto es doble: '
        'se cobra un IVA que no corresponde y se declara una operación que no '
        'es la que se está facturando.'
    ),
    "BR-IC-6": (
        'Un descuento de los que se aplican a la factura entera se declara '
        'intracomunitario y trae un tipo que no es cero. En estas facturas '
        'todo el documento suele ir a cero, así que un descuento con tipo '
        'positivo canta: casi siempre es un valor por defecto del programa '
        'que nadie ha tocado, porque no cambia ningún total —el descuento se '
        'resta igual—. Lo que cambia es de qué base se resta, y eso el cuadre '
        'general no lo ve.'
    ),
    "BR-IC-7": (
        'Un cargo de los que se aplican a la factura entera se declara '
        'intracomunitario y trae un tipo que no es cero. En una entrega '
        'intracomunitaria los gastos que acompañan a la entrega —el '
        'transporte, sobre todo— siguen su misma suerte y van también sin '
        'repercusión. Un cargo de transporte al 21% en una factura '
        'intracomunitaria es la señal de que ese cargo se calculó con las '
        'reglas del mercado nacional.'
    ),
    "BR-IC-8": (
        'La base declarada como entrega intracomunitaria no es la suma de los '
        'conceptos que van a ese régimen. Esta cifra viaja más lejos que las '
        'demás: es la que acaba en la declaración recapitulativa de '
        'operaciones intracomunitarias, que se cruza con lo que declare el '
        'comprador en su país. Cuando las dos no coinciden, quien tiene que '
        'explicarlo es quien emitió la factura, y lo que hay que explicar '
        'sale de aquí.'
    ),
    "BR-G-1": (
        'Hay conceptos declarados como exportación y el desglose no recoge '
        'esa categoría. Una exportación fuera de la Unión va sin IVA, y como '
        'toda exención hay que declararla y justificarla: sin entrada en el '
        'desglose no hay base exportada ni motivo que la sostenga, y lo que '
        'queda es una factura sin impuesto y sin razón aparente para no '
        'llevarlo.'
    ),
    "BR-G-5": (
        'Una línea declarada como exportación trae un tipo que no es cero. '
        'Una venta a un país de fuera de la Unión no lleva IVA español, así '
        'que el tipo es cero. Un tipo positivo aquí es casi siempre el mismo '
        'caso que en la intracomunitaria —la factura nacional reutilizada— '
        'con una diferencia práctica: en la exportación quien recibe pagará '
        'los impuestos de su país al entrar la mercancía, así que un IVA '
        'español cobrado de más acaba siendo un impuesto pagado dos veces.'
    ),
    "BR-G-6": (
        'Un descuento de los que se aplican a la factura entera se declara '
        'como exportación y trae un tipo que no es cero. Vale lo mismo que en '
        'la línea, con el añadido de dónde se corrige: el bloque de totales '
        'lo suele rellenar un módulo distinto del que factura, y ahí es donde '
        'se quedan los valores por defecto. El informe nombra el descuento '
        'por su motivo escrito para que se pueda encontrar, porque en los '
        'totales no hay números de línea.'
    ),
    "BR-G-7": (
        'Un cargo de los que se aplican a la factura entera se declara como '
        'exportación y trae un tipo que no es cero. El caso corriente es el '
        'transporte internacional, que acompaña a la mercancía exportada y '
        'sigue su tratamiento. Cuando ese cargo aparece con tipo, lo que '
        'suele haber detrás es un porte calculado con la tarifa nacional y '
        'pegado a una factura de exportación sin revisarlo.'
    ),
    "BR-G-8": (
        'La base declarada como exportación no es la suma de los conceptos '
        'exportados. Es la cifra que acaba comparándose con el documento '
        'aduanero, así que aquí el cuadre no se queda en la factura: una base '
        'exportada que no coincide con lo que salió por la aduana es '
        'exactamente lo que pone en duda una exención. El informe enumera los '
        'conceptos que van a esa categoría, que es lo que permite compararlos '
        'con el envío.'
    ),
    "BR-AF-1": (
        'Hay conceptos con IGIC y el desglose no recoge esa categoría. El '
        'IGIC es el impuesto canario, que ocupa el lugar del IVA en las '
        'islas, y la norma europea lo trata como una categoría más con su '
        'propia familia de reglas. De esa familia aquí sólo pueden salir dos, '
        'ésta y la del cuadre de la base: la norma no ata el tipo del IGIC ni '
        'se pronuncia sobre su motivo, así que las reglas del tipo y del '
        'motivo no tienen nada que exigirle. Anunciar que existen sería '
        'inventarlas.'
    ),
    "BR-AF-8": (
        'La base declarada con IGIC no es la suma de los conceptos que van a '
        'ese impuesto y tipo. Es el mismo cuadre que en las demás categorías, '
        'con una diferencia que conviene saber: el IGIC tiene tipos propios, '
        'que no son los del IVA peninsular, y este validador no opina sobre '
        'cuáles —la regla que avisa de un tipo que no existe en España se '
        'aparta a propósito en Canarias y en Ceuta y Melilla—. Lo que sí se '
        'comprueba es que la base declarada sea la de los conceptos que van '
        'ahí.'
    ),
    "BR-AG-1": (
        'Hay conceptos con IPSI y el desglose no recoge esa categoría. El '
        'IPSI es el impuesto de Ceuta y Melilla, y el código de sus reglas '
        'merece una nota: no es BR-IP-* como parecería, sino BR-AG-*. Aquí se '
        'llegó a escribir BR-IP-* por analogía con el intracomunitario —o '
        'sea, inventado— hasta que se comprobó contra el esquematrón oficial '
        'de la Comisión y se corrigió. Una factura de Ceuta recibía el nombre '
        'de una regla que no existe en ninguna norma.'
    ),
    "BR-AG-8": (
        'La base declarada con IPSI no es la suma de los conceptos que van a '
        'ese impuesto y tipo. El caso medido está entre las facturas de '
        'ejemplo que publica la Administración: 1.163,52 de base al 3% y '
        'ninguna línea a ese tipo detrás. Eso es una de dos cosas, y se '
        'arreglan en sitios distintos: o sobra esa entrada del desglose, o '
        'hay una línea con la categoría o el tipo cambiados. El informe lo '
        'dice con esas palabras en vez de pedir una suma que daría cero.'
    ),
    "BR-IC-10": (
        'Una entrega intracomunitaria sin decir por qué no lleva IVA. La '
        'factura tiene que declarar la razón de la exención, y aquí el motivo '
        'no es un trámite: una entrega intracomunitaria se sostiene sobre '
        'tres cosas —que el comprador tenga número de operador '
        'intracomunitario, que la mercancía salga de verdad hacia otro Estado '
        'y que la factura lo diga—, y ésta es la única de las tres que se '
        'puede comprobar leyendo el documento. Sin ella, lo que hay es una '
        'factura sin IVA y sin explicación, que es lo que se mira primero '
        'cuando se revisa una exención.'
    ),
    "BR-G-10": (
        'Una exportación sin decir por qué no lleva IVA. Lo que de verdad '
        'sostiene la exención es el documento aduanero, no la factura, pero '
        'la factura tiene que declarar la razón igual: es lo que ata el papel '
        'de la venta con el de la salida de la mercancía. Sin motivo, una '
        'exportación y un error de tipo se leen igual desde fuera —las dos '
        'son una factura a cero—, y distinguirlas es justo lo que esta regla '
        'pide que no haya que adivinar.'
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
