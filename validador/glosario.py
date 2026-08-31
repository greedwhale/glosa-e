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
        "mira hacia atrás: **todo** lo que esa clave firmó pasa a ser "
        "sospechoso, también lo anterior a la denuncia, porque quien la robó "
        "pudo firmar con fecha atrasada."
    ),
    "REVOCACION-SUSPENDIDO": (
        "Está en suspenso, que no es lo mismo que anulado: una suspensión "
        "puede levantarse y entonces el certificado vuelve a valer. Hoy no "
        "vale, y la prueba no dice desde cuándo dejó de valer."
    ),
    "REVOCACION-POSTERIOR": (
        "Lo anularon **después** de la fecha de firma. Sale como aviso cuando "
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
