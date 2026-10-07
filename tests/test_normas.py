# -*- coding: utf-8 -*-
"""La tabla de normas, que ahora es una sola.

Por qué existe
--------------
De qué norma sale cada código estaba escrito dos veces: en `factura.origen`,
que lo pone al lado de cada queja del informe, y en `pagina_incidencias`, que
lo pone en la ficha del catálogo publicado. El 15-09-2026 los dos repartos no
decían lo mismo en 16 de los 371 códigos, y la diferencia no era cosmética:
los doce `IVA-*` salían publicados como «Ley del IVA» —o sea, exigidos por una
ley— cuando son criterio de la casa.

Aquí se prueba la tabla en sí. Que los dos caminos coincidan código a código
lo prueba `test_pagina_incidencias.py`, que es donde están los dos a mano.
"""
from __future__ import annotations

from validador import normas
from validador.codigos import codigos_del_paquete


def test_cada_codigo_del_catalogo_sale_con_su_norma():
    """Ninguno se queda sin etiqueta, ni con una vacía."""
    sin_norma = [
        c.codigo for c in codigos_del_paquete() if not normas.norma(c.codigo)[0]
    ]
    assert not sin_norma, sin_norma


def test_lo_que_no_exige_ninguna_norma_lo_dice_asi():
    """El cajón por defecto dice «De la casa», no «Formato».

    Decía «Formato» en el informe, y con eso un código nuestro —`SIN-SOPORTE`,
    `VALIDADOR-SE-ATRAGANTA`— salía como si fuera un problema del formato del
    documento. Lo que este validador opina por su cuenta se dice que lo opina
    él: es media tesis del producto.
    """
    etiqueta, detalle = normas.norma("CODIGO-QUE-NO-EXISTE")
    # La palabra escrita, no la constante: comparar contra `normas.CASA` es
    # comparar el cajón consigo mismo, y cambiarlo a «Formato» dejaba esta
    # prueba en verde. Provocado el 20-09-2026.
    assert etiqueta == "De la casa"
    assert "este validador" in detalle


def test_las_de_iva_son_de_la_casa_y_no_de_una_ley():
    """El desglose lo pide EN 16931 con sus BR-*; lo de aquí es criterio propio.

    La página los publicaba como «Ley del IVA». Decirle a alguien que una ley
    exige lo que exigimos nosotros es la clase de promesa de más que este
    proyecto no puede hacer.
    """
    for codigo in ("IVA-TIPO", "IVA-BASE", "IVA-CATEGORIA-RARA"):
        assert normas.norma(codigo)[0] == "De la casa", codigo


def test_lo_de_la_firma_no_es_un_problema_de_formato():
    """Incluidas las dos que se escapaban por no llevar guion o prefijo propio."""
    for codigo in ("FIRMA-DEBIL", "CADENA-DESCONOCIDA", "REVOCADO",
                   "SELLO-FALTA", "CONFIANZA-ANCLA", "ANCLAS-SIN-RENOVAR"):
        assert normas.norma(codigo)[0] == "Firma electrónica", codigo


def test_ningun_prefijo_tapa_a_otro():
    """Gana el primero que encaja, así que un prefijo dentro de otro decidiría
    por él sin que nadie lo hubiera querido.

    Hoy no pasa. Esto está para el día que alguien añada `FIRMA-` detrás de
    `FIRMA-USO-` y se pregunte por qué la etiqueta no cambia.
    """
    tapados = [
        (uno, otro)
        for indice, (uno, _, _) in enumerate(normas.NORMAS)
        for otro, etiqueta, _ in normas.NORMAS[indice + 1:]
        if otro.startswith(uno) and etiqueta != normas.norma(otro)[0]
    ]
    assert not tapados, tapados


def test_la_familia_spfe_dice_de_que_anexo_sale_cada_regla():
    """Contra un literal, y con las dos fuentes: la orden y el borrador de abril.

    Hasta el 07-10-2026 la ficha decía «en proyecto de orden». La primera
    versión de la frase nueva, «el anexo I de la Orden HAC/1028/2026, todavía
    medido en parte con el borrador de abril», le atribuía a la orden, en
    SPFE-RECARGO-DE-EQUIVALENCIA, una queja que solo existe en el borrador; y
    nada la fijaba: cualquier otra frase dejaba la suite verde. Lo vio el
    revisor de promesas, antes de publicar.
    """
    assert normas.norma("SPFE-RECARGO-DE-EQUIVALENCIA") == (
        "Anexo I",
        "el contenido mínimo de las facturas de la solución pública: el anexo I "
        "de la Orden HAC/1028/2026 o, en las reglas que todavía no se han puesto "
        "al día, el del borrador de abril",
    )
