"""Comprobaciones de EDIFACT: la tira de segmentos y lo que se saca de ella.

Aquí el círculo se rompe por dos sitios distintos, y conviene saber cuál prueba
qué, porque cada uno cubre lo que el otro no puede.

**Los ficheros reales, para la lectura.** Un EDIFACT de verdad trae dentro su
propia respuesta: el segmento UNT declara cuántos segmentos lleva el mensaje y
el UNZ cuántos mensajes lleva el sobre. Esas cuentas las escribió el sistema
que emitió la factura, no este código, así que cuadrar con ellas es una prueba
que no me puedo aprobar yo solo. La factura de Otto Harrassowitz es la que más
dice: 138 segmentos declarados, y solo salen 138 si el carácter de escape se
trata bien, porque lleva apóstrofos dentro de los títulos —«d?'Histoire»— que
sin tratar parten un segmento en dos.

**Los ejemplos de la Comisión, para el mapa.** Los nueve EDIFACT de
`eInvoicing-EN16931` son facturas conformes a la norma europea, hechas por
quien la escribió. Que salgan sin un solo error después de pasarles las reglas
de EN 16931 y la aritmética del IVA es lo que dice que el mapa de campos está
bien; y los cualificadores de importe —qué código lleva el total y cuál el
importe de una línea— se comprobaron haciendo la cuenta en los nueve, que es
la única forma de saber que un código significa lo que uno cree.

Ninguno de los dos se versiona: son ficheros de terceros, como el resto de
`muestras/`. Las pruebas que los usan se saltan solas cuando no están, y las
que no dependen de ellos —las de sintaxis, que son la mayoría— corren siempre.
"""

import pathlib
from decimal import Decimal

import pytest
from lxml import etree

from validador import edifact, en16931, factura, sintaxis
from validador.formato import EDIFACT, detectar
from validador.incidencias import AVISO, ERROR

MUESTRAS = pathlib.Path("muestras")
EJEMPLOS_CEF = sorted(MUESTRAS.glob("cef_EDIFACT_EXAMPLE*.xml"))
PLANOS = sorted(MUESTRAS.glob("edi_*.edi"))
HARRASSOWITZ = MUESTRAS / "edi_folio_harrassowitz_d96a.edi"
APOSTROFO = MUESTRAS / "edi_harrassowitz_apostrofo_d96a.edi"
UNA_PROPIO = MUESTRAS / "edi_wshein_una_propio_d96a.edi"
UNA_DE_CINCO = MUESTRAS / "edi_una_de_cinco_d96a.edi"

# Lo que trae mal cada fichero ajeno, escrito aquí para que se vea que se
# sabe. Los tres defectos los pusieron sus emisores; ninguno es de este código.
DEFECTOS_DE_ORIGEN = {
    # Declara dos grupos funcionales en el UNZ y trae uno.
    "edi_ballerina_ung_d96a.edi": {"EDI-SOBRE-DESCONTADO"},
    # Un apóstrofo sin soltar dentro del título de una revista checa parte un
    # segmento en dos. Se lo metieron al preparar el fichero de prueba, no el
    # emisor; pero el UNT sigue siendo el del emisor y por eso lo detecta.
    "edi_harrassowitz_apostrofo_d96a.edi": {"EDI-ETIQUETA-IMPOSIBLE"},
    # El UNZ no repite la referencia del UNB: dice 000000751 donde el UNB
    # decía 000000767.
    "edi_wshein_una_propio_d96a.edi": {"EDI-SOBRE-DESCUADRADO"},
}


def codigos(incidencias, gravedad=None) -> set[str]:
    return {i.codigo for i in incidencias if gravedad is None or i.gravedad == gravedad}


def texto_de(incidencias, codigo: str) -> str:
    return next(i.mensaje for i in incidencias if i.codigo == codigo)


def quejas(datos: bytes) -> list:
    return factura.validar(datos).incidencias


# Una factura mínima pero completa, para las pruebas que no necesitan un
# fichero real. Va en una sola tira, que es como viaja de verdad.
def sobre(cuerpo: str, referencia: str = "1", cuenta: int | None = None) -> bytes:
    """Mete un cuerpo de mensaje en su sobre, con las cuentas hechas."""
    segmentos = [s for s in cuerpo.split("'") if s.strip()]
    total = len(segmentos) + 2  # el UNH y el UNT cuentan
    tira = (
        f"UNB+UNOC:3+EMISOR+RECEPTOR+260819:1200+{referencia}'"
        f"UNH+{referencia}+INVOIC:D:96A:UN'"
        f"{cuerpo}"
        f"UNT+{total if cuenta is None else cuenta}+{referencia}'"
        f"UNZ+1+{referencia}'"
    )
    return tira.encode("utf-8")


CUERPO = (
    "BGM+380+F-2026-1'"
    "DTM+137:20260819:102'"
    "FTX+DOC+++urn:cen.eu:en16931:2017'"
    "NAD+SE+++Talleres Ejemplo SL+Calle Mayor 1+Madrid++28001+ES'"
    # BT-31, el identificador de IVA del vendedor, en su RFF detrás del NAD.
    # Sin él, la línea al tipo general es BR-S-02.
    "RFF+VA:ESB12345678'"
    "NAD+BY+++Cliente SA+Gran Via 2+Madrid++28013+ES'"
    "CUX+2:EUR:4'"
    "LIN+1'"
    # BT-153, que BR-25 exige: el nombre va en el cuarto componente del C273.
    "IMD+F++:::Concepto'"
    # El compuesto C186 lleva los tres datos juntos: cualificador, cuanto y en
    # que unidad. El «PCE» es BT-130, que EN 16931 exige por BR-23 y que antes
    # faltaba aqui: la factura de prueba decia «10» sin decir 10 de que.
    "QTY+47:10:PCE'"
    "PRI+AAA:100'"
    "MOA+203:1000'"
    "TAX+7+VAT+++:::21+S'"
    "UNS+S'"
    "MOA+79:1000'"
    "MOA+389:1000'"
    "MOA+176:210'"
    "MOA+388:1210'"
    "MOA+9:1210'"
    "TAX+7+VAT+++:::21+S'"
    "MOA+125:1000'"
    "MOA+124:210'"
)


# --- Partir la tira --------------------------------------------------------


class TestPartirLaTira:
    def test_lo_basico(self):
        segmentos, suelto = edifact.partir(
            "BGM+380+F-1'DTM+137:20260819:102'", edifact.POR_DEFECTO
        )
        assert suelto == ""
        assert [s.etiqueta for s in segmentos] == ["BGM", "DTM"]
        assert segmentos[0].dato(1) == "380"
        assert segmentos[1].dato(1, 1) == "20260819"

    def test_los_saltos_de_linea_no_son_datos(self):
        """Unos ficheros vienen en una tira y otros con un segmento por línea.

        Sin saltárselos, la etiqueta del segmento siguiente llega con un salto
        de línea pegado delante y no la reconoce nadie.
        """
        segmentos, _ = edifact.partir(
            "BGM+380+F-1'\r\nDTM+137:20260819:102'\n", edifact.POR_DEFECTO
        )
        assert [s.etiqueta for s in segmentos] == ["BGM", "DTM"]

    def test_un_elemento_vacio_no_desplaza_a_los_demas(self):
        """Los huecos son los que dicen qué posición ocupa cada dato."""
        segmentos, _ = edifact.partir("NAD+SE+++Nombre'", edifact.POR_DEFECTO)
        assert segmentos[0].dato(1) == "SE"
        assert segmentos[0].dato(2) == ""
        assert segmentos[0].dato(3) == ""
        assert segmentos[0].dato(4) == "Nombre"

    def test_lo_que_queda_sin_cerrar_se_devuelve(self):
        _, suelto = edifact.partir("BGM+380'DTM+137", edifact.POR_DEFECTO)
        assert suelto == "DTM+137"


class TestElCaracterDeEscape:
    """La trampa que parte una factura en dos sin que se note.

    El apóstrofo cierra un segmento, así que un apóstrofo dentro de un dato
    —un apellido irlandés, un título francés— tiene que ir escapado. Lo trae
    la factura de Harrassowitz de verdad, en «d?'Histoire».
    """

    def test_un_apostrofo_escapado_no_cierra_el_segmento(self):
        segmentos, _ = edifact.partir(
            "IMD+L+050+:::Revue d?'Histoire'", edifact.POR_DEFECTO
        )
        assert len(segmentos) == 1
        assert segmentos[0].dato(3, 3) == "Revue d'Histoire"

    def test_el_escape_se_escapa_a_si_mismo(self):
        segmentos, _ = edifact.partir("FTX+AAI+++por qu??'", edifact.POR_DEFECTO)
        assert segmentos[0].dato(4) == "por qu?"

    def test_sin_tratarlo_la_factura_se_parte(self):
        """El control: lo de arriba solo vale si sin ello sale mal.

        Con un carácter de escape que no aparece en el texto, el apóstrofo
        vuelve a cerrar el segmento y salen dos donde hay uno.
        """
        sin_escape = edifact.Servicio(escape="\x01")
        segmentos, _ = edifact.partir(
            "IMD+L+050+:::Revue d?'Histoire'", sin_escape
        )
        assert len(segmentos) == 2


class TestLosCaracteresDeServicio:
    def test_el_una_los_declara(self):
        servicio, desde = edifact.servicio_de("UNA:+.? 'UNB+UNOC:3+A+B'")
        assert servicio == edifact.POR_DEFECTO
        assert desde == 9

    def test_un_fichero_con_otros_separadores(self):
        """ISO 9735 deja elegirlos, y hay quien los cambia.

        Leer un fichero así con los separadores de siempre no da error: da
        basura, que es peor.
        """
        servicio, desde = edifact.servicio_de("UNA=*,! #")
        assert servicio.componente == "="
        assert servicio.elemento == "*"
        assert servicio.decimal == ","
        assert servicio.escape == "!"
        assert servicio.terminador == "#"
        segmentos, _ = edifact.partir("BGM*380*F-1#", servicio)
        assert segmentos[0].etiqueta == "BGM"
        assert segmentos[0].dato(2) == "F-1"

    def test_sin_una_valen_los_de_siempre(self):
        servicio, desde = edifact.servicio_de("UNB+UNOC:3+A+B'")
        assert servicio == edifact.POR_DEFECTO
        assert desde == 0

    def test_la_coma_decimal_se_traduce_en_los_importes(self):
        """Un importe con coma tiene que llegar al validador con punto.

        Si no, `Decimal` no lo lee y la factura sale sin totales: no es que
        estén mal, es que no se han entendido.
        """
        datos = "UNA:+,? 'UNH+1+INVOIC:D:96A:UN'UNS+S'MOA+388:1210,50'UNT+4+1'"
        raiz, _ = edifact.convertir(datos.encode("utf-8"))
        assert raiz.xpath("string(./*/S_MOA/C_C516/D_5004)") == "1210.50"

    def test_pero_no_en_los_codigos(self):
        """Un código no es una cantidad y no se toca."""
        datos = "UNA:+,? 'UNH+1+INVOIC:D:96A:UN'DTM+137:20260819:102'UNT+3+1'"
        raiz, _ = edifact.convertir(datos.encode("utf-8"))
        assert raiz.xpath("string(./S_DTM/C_C507/D_2005)") == "137"


# --- Las cuentas del sobre -------------------------------------------------


class TestLoQueCuentaElSobre:
    """ISO 9735 hace contar, y es lo único que caza un fichero cortado.

    Un EDIFACT al que le falta un trozo sigue pareciendo legible: los
    segmentos que quedan están bien formados. Lo único que lo delata es que la
    cuenta no sale.
    """

    def test_una_factura_entera_no_se_queja(self):
        assert not [
            i for i in edifact.leer(sobre(CUERPO))[2] if i.gravedad == ERROR
        ]

    def test_los_segmentos_declarados_de_menos(self):
        incidencias = edifact.leer(sobre(CUERPO, cuenta=5))[2]
        assert "EDI-MENSAJE-DESCONTADO" in codigos(incidencias, ERROR)

    def test_la_referencia_del_cierre_tiene_que_ser_la_de_la_cabecera(self):
        tira = sobre(CUERPO)
        cierre = tira[tira.rindex(b"UNT+") : tira.rindex(b"UNZ")]
        tira = tira.replace(cierre, cierre.replace(b"+1'", b"+9'"))
        incidencias = edifact.leer(tira)[2]
        assert "EDI-MENSAJE-DESCUADRADO" in codigos(incidencias, ERROR)

    def test_un_sobre_sin_cerrar(self):
        tira = sobre(CUERPO).replace(b"UNZ+1+1'", b"")
        assert "EDI-SOBRE-SIN-CERRAR" in codigos(edifact.leer(tira)[2], ERROR)

    def test_un_sobre_que_dice_llevar_mas_mensajes_de_los_que_lleva(self):
        tira = sobre(CUERPO).replace(b"UNZ+1+1'", b"UNZ+3+1'")
        assert "EDI-SOBRE-DESCONTADO" in codigos(edifact.leer(tira)[2], ERROR)

    def test_la_referencia_del_sobre(self):
        tira = sobre(CUERPO).replace(b"UNZ+1+1'", b"UNZ+1+7'")
        assert "EDI-SOBRE-DESCUADRADO" in codigos(edifact.leer(tira)[2], ERROR)

    def test_un_fichero_cortado_por_la_mitad(self):
        tira = sobre(CUERPO)[:-12]
        incidencias = edifact.leer(tira)[2]
        assert "EDI-SEGMENTO-SIN-CERRAR" in codigos(incidencias, ERROR)

    def test_un_mensaje_que_no_es_una_factura(self):
        tira = b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+ORDERS:D:96A:UN'UNT+2+1'UNZ+1+1'"
        incidencias = edifact.leer(tira)[2]
        assert "EDI-NO-ES-FACTURA" in codigos(incidencias, ERROR)
        assert "ORDERS" in texto_de(incidencias, "EDI-NO-ES-FACTURA")

    def test_un_sobre_sin_ningun_mensaje(self):
        incidencias = edifact.leer(b"UNB+UNOC:3+A+B+260819:1200+1'UNZ+0+1'")[2]
        assert "EDI-SIN-MENSAJE" in codigos(incidencias, ERROR)

    def test_con_grupos_funcionales_el_sobre_cuenta_grupos(self):
        """Y no mensajes, que es lo que parece si uno no lee la norma.

        Con un UNG por medio, el UNZ cuenta grupos. Contando mensajes contra
        ese número, un fichero correcto sale acusado de descuadrar.
        """
        tira = (
            b"UNB+UNOC:3+A+B+260819:1200+1'"
            b"UNG+INVOIC+A+B+260819:1200+1+UN+D:96A:UN'"
            b"UNH+1+INVOIC:D:96A:UN'BGM+380+F-1'UNT+3+1'"
            b"UNH+2+INVOIC:D:96A:UN'BGM+380+F-2'UNT+3+2'"
            b"UNE+2+1'UNZ+1+1'"
        )
        incidencias = edifact.leer(tira)[2]
        assert "EDI-SOBRE-DESCONTADO" not in codigos(incidencias)

    def test_varios_mensajes_se_avisan(self):
        tira = (
            b"UNB+UNOC:3+A+B+260819:1200+1'"
            b"UNH+1+INVOIC:D:96A:UN'BGM+380+F-1'UNT+3+1'"
            b"UNH+2+INVOIC:D:96A:UN'BGM+380+F-2'UNT+3+2'"
            b"UNZ+2+1'"
        )
        incidencias = edifact.leer(tira)[2]
        assert "EDI-VARIOS-MENSAJES" in codigos(incidencias, AVISO)


# --- Reconstruir los grupos ------------------------------------------------


class TestLosGrupos:
    """Lo que EDIFACT no escribe y hay que deducir del orden.

    Es la parte que de verdad puede salir mal en silencio: si un IVA de línea
    se cuelga del documento, la factura no da error de lectura —da un desglose
    equivocado, que es mucho peor—.
    """

    def test_el_iva_de_una_linea_es_de_su_linea(self):
        raiz, _ = edifact.convertir(sobre(CUERPO))
        lineas = raiz.xpath(".//*[S_LIN]")
        assert len(lineas) == 1
        assert lineas[0].xpath("string(./*[S_TAX]/S_TAX/C_C243/D_5278)") == "21"

    def test_y_no_se_cuenta_como_desglose_del_documento(self):
        """El desglose del documento es solo el de después del UNS.

        Con el de la línea colado dentro saldrían dos entradas donde hay una,
        y el cuadre del IVA fallaría sobre una factura correcta.
        """
        raiz, _ = edifact.convertir(sobre(CUERPO))
        assert len(raiz.xpath(sintaxis.SINTAXIS_EDIFACT.desglose)) == 1

    def test_el_iva_de_la_cabecera_tampoco(self):
        """El TAX de la cabecera no es una entrada del desglose.

        Cuelga de la raíz igual que el del resumen, así que por el sitio no se
        distinguen: se distinguen por el UNS. El de la cabecera es el grupo 6,
        el impuesto del documento entero, sin base ni cuota; el desglose es el
        grupo 54, y el esquematrón oficial de EDIFACT lo pide con ese nombre.
        Leído como desglose salían dos entradas donde hay una, las dos a
        medias, y con ellas BR-45 y BR-46 sobre una factura correcta.
        """
        cuerpo = CUERPO.replace("CUX+2:EUR:4'", "CUX+2:EUR:4'TAX+7+VAT+++:::21+S'")
        raiz, _ = edifact.convertir(sobre(cuerpo))
        assert len(raiz.xpath(sintaxis.SINTAXIS_EDIFACT.desglose)) == 1
        assert not codigos(quejas(sobre(cuerpo)), ERROR)

    def test_ni_un_impuesto_que_no_es_el_iva(self):
        """Un TAX del resumen que no es de IVA no entra en el desglose del IVA.

        El esquematrón oficial lo filtra por las dos cosas: función 7, impuesto,
        y tipo VAT. Sin el filtro, un impuesto especial declarado al final se
        leía como una entrada del desglose sin categoría ni base.
        """
        cuerpo = CUERPO + "TAX+7+EXC'MOA+124:0'"
        raiz, _ = edifact.convertir(sobre(cuerpo))
        assert len(raiz.xpath(sintaxis.SINTAXIS_EDIFACT.desglose)) == 1
        assert not codigos(quejas(sobre(cuerpo)), ERROR)

    def test_una_referencia_detras_de_una_parte_es_de_esa_parte(self):
        """El NIF del vendedor va en un RFF detrás de su NAD, y es suyo.

        La factura de estas pruebas lo lleva desde que BR-S-02 lo pide: es el
        `RFF+VA` que va detrás del `NAD+SE`, y no puede acabar colgando del
        comprador, que viene justo después.
        """
        raiz, _ = edifact.convertir(sobre(CUERPO))
        vendedor = raiz.xpath("./*[S_NAD/D_3035='SE']")[0]
        comprador = raiz.xpath("./*[S_NAD/D_3035='BY']")[0]
        assert vendedor.xpath("string(.//S_RFF/C_C506/D_1154)") == "ESB12345678"
        assert not comprador.xpath(".//S_RFF")
        assert raiz.xpath(sintaxis.SINTAXIS_EDIFACT.vendedor_nif)

    def test_un_segmento_repetido_abre_un_grupo_nuevo(self):
        """Dos líneas son dos grupos, no uno con dos LIN dentro."""
        cuerpo = CUERPO.replace(
            "UNS+S'", "LIN+2'QTY+47:5'MOA+203:500'TAX+7+VAT+++:::21+S'UNS+S'"
        )
        raiz, _ = edifact.convertir(sobre(cuerpo))
        lineas = raiz.xpath(".//*[S_LIN]")
        assert len(lineas) == 2
        assert [x.xpath("string(./S_LIN/D_1082)") for x in lineas] == ["1", "2"]

    def test_el_uns_cierra_lo_que_hubiera_abierto(self):
        """Sin eso, los totales acabarían dentro de la última línea."""
        raiz, _ = edifact.convertir(sobre(CUERPO))
        assert raiz.xpath("string(./*/S_MOA/C_C516[D_5025='388']/D_5004)") == "1210"

    def test_un_descuento_de_linea_no_es_el_iva_de_la_linea(self):
        """Un ALC dentro de una línea trae su propio TAX, un piso más abajo.

        Si ese TAX se leyera como el de la línea, el tipo de la línea saldría
        el del descuento.
        """
        cuerpo = CUERPO.replace(
            "TAX+7+VAT+++:::21+S'UNS",
            "TAX+7+VAT+++:::21+S'ALC+A++++DI'MOA+8:50'TAX+7+VAT+++:::4+S'UNS",
        )
        raiz, _ = edifact.convertir(sobre(cuerpo))
        linea = raiz.xpath(".//*[S_LIN]")[0]
        assert linea.xpath("string(./*[S_TAX]/S_TAX/C_C243/D_5278)") == "21"

    def test_un_segmento_que_no_este_en_la_tabla_cierra_la_linea(self):
        """El fallo que enseño contrastar la tabla con una gramatica ajena.

        Un segmento que no esta en el grupo no se queda fuera: **lo cierra**.
        Un PAC —el embalaje de una linea— cerraba la linea, y el MOA de detras
        dejaba de ser el importe de esa linea para convertirse en un total de
        la factura. Sin dar ningun error: una factura con embalajes salia con
        los importes de sus lineas contados como totales.
        """
        cuerpo = CUERPO.replace(
            "QTY+47:10:PCE'", "QTY+47:10:PCE'PAC+2++CT'MEA+PD+AAB+KGM:12'"
        )
        raiz, _ = edifact.convertir(sobre(cuerpo))
        linea = raiz.xpath(".//*[S_LIN]")[0]
        mapa = sintaxis.SINTAXIS_EDIFACT
        assert sintaxis.importe(linea, mapa.linea_importe, mapa) == Decimal("1000")

    def test_y_el_control_de_esa(self):
        """Sacando PAC de la tabla, el importe de la linea se pierde."""
        marco = edifact.GRUPOS["LIN"]
        recortado = edifact.Grupo(
            sueltos=marco.sueltos, dentro=marco.dentro - {"PAC"}
        )
        cuerpo = CUERPO.replace(
            "QTY+47:10:PCE'", "QTY+47:10:PCE'PAC+2++CT'MEA+PD+AAB+KGM:12'"
        )
        original = edifact.GRUPOS["LIN"]
        edifact.GRUPOS["LIN"] = recortado
        try:
            raiz, _ = edifact.convertir(sobre(cuerpo))
        finally:
            edifact.GRUPOS["LIN"] = original
        linea = raiz.xpath(".//*[S_LIN]")[0]
        mapa = sintaxis.SINTAXIS_EDIFACT
        assert sintaxis.importe(linea, mapa.linea_importe, mapa) is None


class TestElDirectorio:
    """Qué dato hay en cada posición. Se equivoca uno y el número cambia de sitio."""

    def test_el_tipo_de_iva_va_en_la_quinta_posicion_del_tax(self):
        """La cuarta es un dato simple, no el compuesto del tipo.

        Escribirlo de memoria y poner el compuesto en la cuarta deja el
        porcentaje fuera de sitio en todas las facturas. Lo enseñaron los
        ficheros reales: «TAX+7+VAT+++:::21+S» solo cuadra con la quinta.
        """
        raiz, _ = edifact.convertir(sobre("TAX+7+VAT+++:::21+S'"))
        assert raiz.xpath("string(.//S_TAX/C_C243/D_5278)") == "21"
        assert raiz.xpath("string(.//S_TAX/D_5305)") == "S"

    def test_la_direccion_de_una_parte(self):
        raiz, _ = edifact.convertir(sobre(CUERPO))
        vendedor = raiz.xpath("./*[S_NAD/D_3035='SE']/S_NAD")[0]
        assert vendedor.xpath("string(./C_C080/D_3036)") == "Talleres Ejemplo SL"
        assert vendedor.xpath("string(./C_C059/D_3042)") == "Calle Mayor 1"
        assert vendedor.xpath("string(./D_3164)") == "Madrid"
        assert vendedor.xpath("string(./D_3251)") == "28001"
        assert vendedor.xpath("string(./D_3207)") == "ES"

    def test_un_segmento_que_no_esta_en_el_directorio_no_se_tira(self):
        """Se escribe por posiciones. No lo lee ninguna regla, pero se ve."""
        raiz, _ = edifact.convertir(sobre("ZZZ+algo+otro'"))
        assert raiz.xpath("string(.//S_ZZZ/E_01)") == "algo"


# --- El formato se reconoce ------------------------------------------------


class TestSeReconoce:
    def test_la_tira(self):
        deteccion = detectar(sobre(CUERPO))
        assert deteccion.familia == EDIFACT
        assert deteccion.version == "96A"
        assert deteccion.tipo_documento == "factura"
        assert deteccion.conforme_en16931

    def test_el_mismo_edifact_escrito_como_xml(self):
        """ISO 20625. Es la forma en que la Comisión publica sus ejemplos.

        Antes salía por la puerta de «formato no reconocido»: el validador
        decía no saber qué era uno de los cuatro formatos que admite la ley, y
        encima el de referencia.
        """
        xml = b"""<?xml version="1.0"?>
<M_INVOIC><S_UNH><D_0062>1</D_0062>
<C_S009><D_0065>INVOIC</D_0065><D_0054>14B</D_0054></C_S009></S_UNH>
<S_BGM><C_C002><D_1001>380</D_1001></C_C002></S_BGM></M_INVOIC>"""
        deteccion = detectar(xml)
        assert deteccion.familia == EDIFACT
        assert deteccion.version == "14B"
        assert deteccion.tipo_documento == "factura"


# --- Las reglas de siempre, sobre EDIFACT ----------------------------------


class TestLasReglasCorren:
    """Lo que se gana con todo lo anterior: las reglas no cambian.

    EN 16931 define un modelo semántico y luego cada sintaxis lo escribe a su
    manera. Si el mapa está bien, las mismas reglas que miran un UBL miran un
    EDIFACT sin enterarse de que lo es.
    """

    def test_una_factura_correcta_pasa(self):
        incidencias = quejas(sobre(CUERPO))
        assert not [i for i in incidencias if i.gravedad == ERROR]

    def test_sin_numero_se_reclama(self):
        incidencias = quejas(sobre(CUERPO.replace("BGM+380+F-2026-1'", "BGM+380'")))
        assert "BR-02" in codigos(incidencias, ERROR)

    def test_el_iva_tiene_que_cuadrar(self):
        """La aritmética es la misma; solo cambia dónde está escrito cada número."""
        incidencias = quejas(sobre(CUERPO.replace("MOA+124:210'", "MOA+124:999'")))
        assert "BR-CO-14" in codigos(incidencias, ERROR)

    def test_el_total_tiene_que_ser_la_base_mas_el_impuesto(self):
        incidencias = quejas(sobre(CUERPO.replace("MOA+388:1210'", "MOA+388:9999'")))
        assert "BR-CO-15" in codigos(incidencias, ERROR)

    def test_un_cargo_suma_y_un_descuento_resta(self):
        """En EDIFACT eso se escribe con una letra, no con un booleano.

        UBL y CII lo dicen con «true»/«false». EDIFACT usa C de cargo y A de
        *allowance*. Comparando con «true», todos los cargos salían restados.
        """
        cuerpo = CUERPO.replace(
            "LIN+1'", "ALC+C++++FC'MOA+23:100'TAX+7+VAT+++:::21+S'LIN+1'"
        )
        cuerpo = cuerpo.replace("MOA+389:1000'", "MOA+389:1100'")
        cuerpo = cuerpo.replace("MOA+259:", "MOA+259:")
        cuerpo = cuerpo.replace("MOA+176:210'", "MOA+259:100'MOA+176:231'")
        cuerpo = cuerpo.replace("MOA+388:1210'", "MOA+388:1331'")
        cuerpo = cuerpo.replace("MOA+9:1210'", "MOA+9:1331'")
        cuerpo = cuerpo.replace("MOA+125:1000'", "MOA+125:1100'")
        cuerpo = cuerpo.replace("MOA+124:210'", "MOA+124:231'")
        incidencias = quejas(sobre(cuerpo))
        assert "BR-CO-12" not in codigos(incidencias, ERROR)
        assert "BR-CO-15" not in codigos(incidencias, ERROR)

    def test_sin_el_rff_del_vendedor_no_esta_identificado(self):
        """BR-S-02 en EDIFACT: el identificador es la referencia VA de su NAD."""
        incidencias = quejas(sobre(CUERPO.replace("RFF+VA:ESB12345678'", "")))
        assert "BR-S-02" in codigos(incidencias, ERROR)

    def test_el_codigo_unico_no_se_reprocha(self):
        """No es que falte: es que EDIFACT no tiene dónde escribirlo."""
        assert "CU-00" not in codigos(quejas(sobre(CUERPO)))


class TestElIvaFueraDelDesglose:
    """Un impuesto escrito, pero donde la norma no busca el desglose.

    Desde que el desglose es solo el grupo 54, una factura que declara su IVA
    en la cabecera, o al final pero sin decir que es IVA, recibe un BR-CO-18:
    «no trae el desglose». Es verdad donde la norma lo lee, y quien lo lee va
    a buscar un TAX que tiene delante. El aviso dice cuál tiene y por qué no
    cuenta.
    """

    SIN_RESUMEN = CUERPO.replace("TAX+7+VAT+++:::21+S'MOA+125:1000'MOA+124:210'", "")

    def test_el_de_la_cabecera(self):
        cuerpo = self.SIN_RESUMEN.replace("CUX+2:EUR:4'", "CUX+2:EUR:4'TAX+7+VAT+++:::21+S'")
        incidencias = quejas(sobre(cuerpo))
        assert "BR-CO-18" in codigos(incidencias, ERROR)
        assert "EDI-IVA-FUERA-DEL-DESGLOSE" in codigos(incidencias, AVISO)
        assert "cabecera" in texto_de(incidencias, "EDI-IVA-FUERA-DEL-DESGLOSE")

    def test_el_del_resumen_sin_decir_que_es_iva(self):
        """El caso de dos facturas reales del corpus: `TAX+7++++…+E`, sin VAT."""
        cuerpo = self.SIN_RESUMEN + "TAX+7++++:::21+S'MOA+125:1000'MOA+124:210'"
        incidencias = quejas(sobre(cuerpo))
        assert "BR-CO-18" in codigos(incidencias, ERROR)
        assert "EDI-IVA-FUERA-DEL-DESGLOSE" in codigos(incidencias, AVISO)
        assert "VAT" in texto_de(incidencias, "EDI-IVA-FUERA-DEL-DESGLOSE")

    def test_con_desglose_no_se_avisa_aunque_haya_otro_en_la_cabecera(self):
        """El TAX de la cabecera es EDIFACT legítimo: solo estorba si es el único."""
        cuerpo = CUERPO.replace("CUX+2:EUR:4'", "CUX+2:EUR:4'TAX+7+VAT+++:::21+S'")
        assert "EDI-IVA-FUERA-DEL-DESGLOSE" not in codigos(quejas(sobre(cuerpo)))

    def test_sin_ningun_tax_tampoco(self):
        """Si no hay nada escrito, BR-CO-18 ya lo dice todo."""
        incidencias = quejas(sobre(self.SIN_RESUMEN))
        assert "BR-CO-18" in codigos(incidencias, ERROR)
        assert "EDI-IVA-FUERA-DEL-DESGLOSE" not in codigos(incidencias)


class TestLosTotalesDeOtraGuia:
    """Un total que está, pero escrito con el código de antes de la norma.

    Es el caso de casi todas las facturas EDIFACT que circulan. Decir «falta
    el importe total» manda a añadir un dato que la factura ya trae.
    """

    def test_se_dice_donde_esta(self):
        cuerpo = (
            CUERPO.replace("MOA+389:1000'", "")
            .replace("MOA+388:1210'", "MOA+128:1210'")
            .replace("MOA+9:1210'", "")
        )
        incidencias = quejas(sobre(cuerpo))
        assert "EDI-TOTALES-DE-OTRA-GUIA" in codigos(incidencias, AVISO)
        queja = next(
            i for i in incidencias if i.codigo == "EDI-TOTALES-DE-OTRA-GUIA"
        )
        # Qué código trae la factura, y cuál esperaba la norma. Las dos mitades
        # hacen falta: con una sola, quien lo lee no sabe qué cambiar.
        assert "128" in queja.encontrado
        assert "389" in queja.esperado
        assert "el total sin impuestos" in queja.mensaje

    def test_una_factura_con_los_codigos_de_la_norma_no_lo_recibe(self):
        assert "EDI-TOTALES-DE-OTRA-GUIA" not in codigos(quejas(sobre(CUERPO)))

    def test_ni_una_a_la_que_de_verdad_le_falte_el_total(self):
        """Si no hay ningún importe de otra guía, lo que falta, falta."""
        cuerpo = CUERPO.replace("MOA+388:1210'", "")
        incidencias = quejas(sobre(cuerpo))
        assert "EDI-TOTALES-DE-OTRA-GUIA" not in codigos(incidencias)
        assert "BR-14" in codigos(incidencias, ERROR)


class TestNadaRevienta:
    """Las puertas de entrada devuelven un informe, no una excepción.

    `codigo_unico.extraer` reventaba con un `XMLSyntaxError` ante cualquier
    EDIFACT plano: era verdad que no es XML, y no venía a cuento.
    """

    @pytest.mark.parametrize(
        "datos",
        [
            b"UNB+UNOC:3+A+B+260819:1200+1'UNH+1+INVOIC:D:96A:UN'",
            b"UNA:+.? 'UNB+UNOC:3+A+B'",
            b"UNH+1+INVOIC:D:96A:UN'",
            b"UNB",
        ],
    )
    def test_no_salta_ninguna_excepcion(self, datos):
        from validador import codigo_unico

        assert factura.validar(datos) is not None
        assert en16931.validar(datos) is not None
        assert codigo_unico.extraer(datos) == []


# --- Contra ficheros que no ha escrito este código -------------------------


@pytest.mark.skipif(not EJEMPLOS_CEF, reason="no están las muestras de la Comisión")
class TestContraLosEjemplosDeLaComision:
    """Los nueve EDIFACT de `eInvoicing-EN16931`, en ISO 20625.

    Son facturas conformes hechas por quien escribió la norma. Que pasen
    limpias es lo que dice que el mapa de campos está bien.
    """

    def test_los_nueve_se_reconocen(self):
        for ruta in EJEMPLOS_CEF:
            deteccion = detectar(ruta.read_bytes())
            assert deteccion.familia == EDIFACT, ruta.name
            assert deteccion.conforme_en16931, ruta.name

    # Lo único que no pasan, y es de la norma de después. Sus identificadores
    # de IVA noruegos van sin el NO delante —`123456789MVA`—, y BR-CO-09 pide
    # el código del país. El esquematrón oficial de EDIFACT deja esa regla en
    # `true()`: no se ha tocado desde 2017, y los ejemplos son de entonces. Los
    # gemelos UBL de los mismos ejemplos ya llevan el prefijo. Aquí EDIFACT
    # sigue a la norma, como en los márgenes.
    SIN_PREFIJO = {"cef_EDIFACT_EXAMPLE2.xml", "cef_EDIFACT_EXAMPLE6.xml"}

    def test_ninguno_da_un_error(self):
        for ruta in EJEMPLOS_CEF:
            informe = factura.validar(ruta.read_bytes())
            errores = [i.codigo for i in informe.incidencias if i.gravedad == ERROR]
            esperados = ["BR-CO-09"] if ruta.name in self.SIN_PREFIJO else []
            assert errores == esperados, f"{ruta.name}: {errores}"

    def test_y_se_les_leen_los_numeros(self):
        """Que no haya errores no basta: podría ser que no se lea nada.

        Una factura de la que no se saca ningún importe tampoco da errores de
        cuadre, por la misma razón por la que no da nada.
        """
        for ruta in EJEMPLOS_CEF:
            raiz = etree.fromstring(ruta.read_bytes())
            mapa = sintaxis.SINTAXIS_EDIFACT
            assert sintaxis.importe(raiz, mapa.suma_lineas, mapa) is not None, ruta.name
            assert raiz.xpath(mapa.lineas), ruta.name
            assert raiz.xpath(mapa.desglose), ruta.name

    def test_la_suma_de_las_lineas_es_el_total_de_lineas(self):
        """El cualificador 79 significa esto, y así se comprobó.

        No se copió de una tabla: se hizo la cuenta en los nueve.
        """
        mapa = sintaxis.SINTAXIS_EDIFACT
        for ruta in EJEMPLOS_CEF:
            raiz = etree.fromstring(ruta.read_bytes())
            declarado = sintaxis.importe(raiz, mapa.suma_lineas, mapa)
            sumado = sum(
                sintaxis.importe(linea, mapa.linea_importe, mapa) or 0
                for linea in raiz.xpath(mapa.lineas)
            )
            assert sintaxis.cuadra(declarado, sumado), ruta.name


@pytest.mark.skipif(not PLANOS, reason="no están las facturas planas")
class TestContraFacturasPlanasDeVerdad:
    """Ficheros EDIFACT tal y como viajan, con las cuentas que traen dentro."""

    def test_todas_se_parten_y_se_convierten(self):
        for ruta in PLANOS:
            raiz, _ = edifact.convertir(ruta.read_bytes())
            assert raiz is not None, ruta.name
            assert raiz.xpath("./S_BGM"), ruta.name

    def test_las_cuentas_que_traen_dentro_cuadran(self):
        """Menos tres, que vienen mal de origen y se dice cuál y por qué.

        Ninguno de los tres defectos es de aquí: son ficheros de otros, y lo
        que se comprueba es que se detecte exactamente el que traen y ninguno
        más. Un fichero de un tercero que salta por donde no es sería peor
        que uno que no salta.
        """
        for ruta in PLANOS:
            incidencias = edifact.leer(ruta.read_bytes())[2]
            salen = codigos(incidencias, ERROR)
            assert salen == DEFECTOS_DE_ORIGEN.get(ruta.name, set()), ruta.name


@pytest.mark.skipif(
    not HARRASSOWITZ.exists(), reason="no está la factura de Harrassowitz"
)
class TestLaFacturaDeHarrassowitz:
    """Una factura de producción de verdad, y la prueba que no me puedo aprobar.

    Son 138 segmentos en una sola tira, con apóstrofos dentro de los títulos
    de las revistas. El número 138 lo escribió el sistema de Otto Harrassowitz
    en el UNT, no este código.
    """

    def test_salen_los_segmentos_que_dice_que_tiene(self):
        segmentos, _, incidencias = edifact.leer(HARRASSOWITZ.read_bytes())
        inicio, fin = edifact._mensajes(segmentos)[0]
        assert segmentos[fin].dato(1) == "138"
        assert fin - inicio + 1 == 138
        assert not codigos(incidencias, ERROR)

    def test_sin_tratar_el_escape_no_saldrian(self):
        """El control. Sale 139 porque un título parte un segmento en dos."""
        texto = edifact.descifrar(HARRASSOWITZ.read_bytes())
        sin_escape = edifact.Servicio(escape="\x01")
        segmentos, _ = edifact.partir(texto[9:], sin_escape)
        inicio, fin = edifact._mensajes(segmentos)[0]
        assert fin - inicio + 1 != 138

    def test_se_le_leen_los_datos(self):
        raiz, _ = edifact.convertir(HARRASSOWITZ.read_bytes())
        mapa = sintaxis.SINTAXIS_EDIFACT
        assert sintaxis.texto(raiz, mapa.vendedor_nombre, mapa) == "OTTO HARRASSOWITZ"
        assert sintaxis.texto(raiz, mapa.vendedor_pais, mapa) == "DE"
        assert sintaxis.texto(raiz, mapa.numero, mapa) == "246816"
        assert sintaxis.texto(raiz, mapa.fecha, mapa) == "20210208"
        assert sintaxis.texto(raiz, mapa.moneda, mapa) == "USD"
        assert len(raiz.xpath(mapa.lineas)) == 8


class TestLoQueElResumenPromete:
    """La frase del final dice de qué se ha fiado quien lee el informe.

    Prometer de más es el peor fallo que puede tener: quien la lee se fía de
    una comprobación que no se ha hecho.
    """

    def test_un_lote_de_edifact_no_promete_un_esquema_xsd(self):
        """Porque no lo hay: EDIFACT no es XML."""
        carpeta = pathlib.Path("muestras")
        lote = factura.validar_lote([carpeta / "edi_apiome_tipica_d96a.edi"])
        frase = lote.alcance(forma=True)
        assert "esquema XSD" not in frase
        assert "cuentas que EDIFACT obliga" in frase

    def test_pero_si_promete_las_reglas_europeas(self):
        """Que sí se le han pasado, y son la mayor parte del trabajo."""
        carpeta = pathlib.Path("muestras")
        lote = factura.validar_lote([carpeta / "edi_apiome_tipica_d96a.edi"])
        assert "EN 16931" in lote.alcance(forma=True)

    def test_en_un_lote_mezclado_el_esquema_vuelve(self):
        """Con un UBL delante sí hay forma que comprobar, y se dice."""
        carpeta = pathlib.Path("muestras")
        lote = factura.validar_lote([
            carpeta / "edi_apiome_tipica_d96a.edi",
            carpeta / "cef_BIS3_Invoice_positive.XML",
        ])
        frase = lote.alcance(forma=True)
        assert "esquema XSD" in frase
        assert "cuentas que EDIFACT obliga" in frase


class TestElUnaDeCinco:
    """Un UNA de cinco caracteres en vez de seis.

    La norma manda seis: componente, elemento, decimal, escape, un hueco
    reservado y terminador. Hay quien se salta el hueco. De los 64 ficheros
    ajenos con los que se ha probado esto lo hacen 23, con 18 emisores
    distintos en el UNB, asi que no es la mania de uno.

    Leerlo no es adivinar: detrás del UNA solo puede venir el UNB, y eso
    decide cuál de las dos longitudes es.
    """

    CINCO = (
        b"UNA:+.?'UNB+UNOC:3+A+B+260819:1200+1'"
        b"UNH+1+INVOIC:D:96A:UN'BGM+380+F1'LIN+1'MOA+203:100'"
        b"UNS+S'MOA+79:100'UNT+7+1'UNZ+1+1'"
    )
    SEIS = CINCO.replace(b"UNA:+.?'UNB", b"UNA:+.? 'UNB", 1)

    def test_se_lee_igual_que_el_de_seis(self):
        cinco = edifact.leer(self.CINCO)
        seis = edifact.leer(self.SEIS)
        assert cinco[1].terminador == seis[1].terminador == "'"
        assert len(cinco[0]) == len(seis[0])
        assert not codigos(cinco[2], ERROR)

    def test_se_dice_que_venia_de_cinco(self):
        """Se acepta, y se deja escrito sobre qué base se ha aceptado."""
        incidencias = edifact.leer(self.CINCO)[2]
        assert "EDI-UNA-DE-CINCO" in codigos(incidencias)
        assert not codigos(edifact.leer(self.SEIS)[2])

    def test_sin_esto_no_aparece_ningun_mensaje(self):
        """El control: leyendo seis a la fuerza, el terminador sale «U».

        Y entonces el fichero se parte por cada U, no hay ningún UNH, y la
        respuesta es «este fichero no trae ningún mensaje» sobre una factura
        que está entera.
        """
        limpio = self.CINCO.decode()
        servicio = edifact.Servicio(terminador=limpio[8])
        segmentos, _ = edifact.partir(limpio[9:], servicio)
        assert servicio.terminador == "U"
        assert not [s for s in segmentos if s.etiqueta == "UNH"]

    def test_un_una_sin_unb_detras_se_lee_como_manda_la_norma(self):
        """Si no hay UNB, no hay nada que decida: se cree lo que dice la norma."""
        servicio, desde = edifact.servicio_de("UNA=*,! #")
        assert servicio.terminador == "#"
        assert desde == 9


class TestLasEtiquetasImposibles:
    """Un carácter de servicio dentro de un dato, sin soltar con «?».

    Sale en tres de los 64 ficheros ajenos: un título de revista en checo y
    dos nombres de empresa con apóstrofo —«…ER\'S HANDELSGESELLSCHAFT»—. En
    los dos que se han podido rastrear, el apóstrofo no lo dejó suelto quien
    emitió la factura: lo dejó suelto quien la manipuló después, al recortar
    un fichero de prueba o al anonimizarlo. Da igual de quién sea: ficheros
    así circulan, y lo que hacía este código con ellos era levantar un
    `ValueError` de `lxml` y llevarse el lote entero por delante.
    """

    ROTO = (
        b"UNB+UNOC:2+A+B+260819:1200+1'"
        b"UNH+1+INVOIC:D:96A:UN'BGM+380+F1'"
        b"LIN+1'IMD+L+050+:::Cesky Casopis'a Historicky'MOA+203:100'"
        b"UNS+S'MOA+79:100'UNT+8+1'UNZ+1+1'"
    )
    ENTERO = ROTO.replace(b"Casopis'a", b"Casopis?'a", 1)

    # El UNT dice 8, que son los que el emisor quiso escribir. Con el
    # apostrofo suelto salen 9, y apartando el trozo roto vuelven a salir 8:
    # es la misma cuenta que confirma la reparacion en el fichero de verdad.

    def test_se_dice_y_no_revienta(self):
        raiz, incidencias = edifact.convertir(self.ROTO)
        assert raiz is not None
        # Y solo esa. Apartando el trozo roto, los segmentos vuelven a ser los
        # 8 que declara el UNT, asi que el descuadre no se queja por duplicado
        # de la misma cosa.
        assert codigos(incidencias, ERROR) == {"EDI-ETIQUETA-IMPOSIBLE"}

    def test_el_trozo_roto_no_cierra_la_linea(self):
        """Lo que de verdad hacía falta arreglar.

        Un trozo con una etiqueta que no está en la tabla de grupos no se
        queda fuera del grupo: **lo cierra**. Sin apartarlo, el `MOA+203` de
        detrás dejaba de ser el importe de la línea y pasaba a contarse como
        total de la factura, sin dar ningún error.
        """
        raiz, _ = edifact.convertir(self.ROTO)
        mapa = sintaxis.SINTAXIS_EDIFACT
        lineas = raiz.xpath(mapa.lineas)
        assert len(lineas) == 1
        assert sintaxis.importe(lineas[0], mapa.linea_importe, mapa) == Decimal("100")

    def test_con_el_escape_puesto_no_hay_queja(self):
        """El control. El mismo fichero con «?'» y no salta nada."""
        raiz, incidencias = edifact.convertir(self.ENTERO)
        assert not codigos(incidencias, ERROR)
        assert raiz.xpath(".//*[S_LIN]//S_IMD//text()")


@pytest.mark.skipif(not APOSTROFO.exists(), reason="no está la muestra")
class TestLaOtraDeHarrassowitz:
    """La misma factura que la de 138 segmentos, retocada por el camino.

    Es el mismo documento —Otto Harrassowitz, número 246816, 8 de febrero de
    2021— publicado en otro repositorio como fichero de prueba: le han
    quitado la dirección del comprador y, sin querer o queriendo, le han
    metido un apóstrofo en el título de una revista checa que parte el
    segmento en dos.

    Lo que la hace valiosa es que **no le tocaron el UNT**. Sigue declarando
    138 segmentos, así que la cuenta del emisor sirve para detectar un
    destrozo posterior al emisor. La misma comprobación caza las dos cosas —el
    escape bien puesto en el original y el trozo roto en la copia— porque el
    138 no lo ha escrito este código.
    """

    def test_el_apostrofo_suelto_se_dice(self):
        incidencias = edifact.leer(APOSTROFO.read_bytes())[2]
        assert codigos(incidencias, ERROR) == {"EDI-ETIQUETA-IMPOSIBLE"}

    def test_apartando_el_trozo_roto_vuelven_a_salir_los_138(self):
        """La prueba de que apartarlo era lo correcto, y no una comodidad."""
        segmentos = edifact.leer(APOSTROFO.read_bytes())[0]
        inicio, fin = edifact._mensajes(segmentos)[0]
        assert segmentos[fin].dato(1) == "138"
        assert fin - inicio + 1 == 138

    def test_sin_apartarlo_sale_uno_de_mas(self):
        """El control: con el trozo dentro salen 139 y la línea se parte."""
        texto = edifact.descifrar(APOSTROFO.read_bytes())
        servicio, desde = edifact.servicio_de(texto)
        segmentos, _ = edifact.partir(texto[desde:], servicio)
        inicio, fin = edifact._mensajes(segmentos)[0]
        assert fin - inicio + 1 == 139

    def test_se_le_leen_las_ocho_lineas_igual(self):
        raiz, _ = edifact.convertir(APOSTROFO.read_bytes())
        mapa = sintaxis.SINTAXIS_EDIFACT
        assert sintaxis.texto(raiz, mapa.vendedor_nombre, mapa) == "OTTO HARRASSOWITZ"
        assert len(raiz.xpath(mapa.lineas)) == 8


@pytest.mark.skipif(not UNA_PROPIO.exists(), reason="no está la muestra")
class TestElUnaConCaracteresPropios:
    """El único de los 64 que no usa los separadores de siempre.

    W.S. Hein factura a Cornell con `UNA^<.? >`: el componente es `^`, el
    elemento `<` y el terminador `>`. Para eso existe el UNA, y hasta este
    fichero no había ninguno que lo demostrara: todos los demás declaran los
    de por defecto, así que un lector que se los saltara habría pasado igual.
    """

    def test_se_leen_los_que_declara_y_no_los_de_siempre(self):
        servicio = edifact.leer(UNA_PROPIO.read_bytes())[1]
        assert servicio.componente == "^"
        assert servicio.elemento == "<"
        assert servicio.terminador == ">"

    def test_se_le_leen_los_datos(self):
        raiz, _ = edifact.convertir(UNA_PROPIO.read_bytes())
        mapa = sintaxis.SINTAXIS_EDIFACT
        assert len(raiz.xpath(mapa.lineas)) == 4
        assert sintaxis.texto(raiz, mapa.numero, mapa)

    def test_el_unz_no_repite_la_referencia_del_unb(self):
        """Un defecto de verdad del fichero, no de la lectura."""
        incidencias = edifact.leer(UNA_PROPIO.read_bytes())[2]
        assert codigos(incidencias, ERROR) == {"EDI-SOBRE-DESCUADRADO"}


@pytest.mark.skipif(not UNA_DE_CINCO.exists(), reason="no está la muestra")
class TestUnFicheroDeVerdadConUnaDeCinco:
    """Y lo mismo, en uno que no ha escrito nadie de aquí."""

    def test_se_lee_entero(self):
        raiz, incidencias = edifact.convertir(UNA_DE_CINCO.read_bytes())
        mapa = sintaxis.SINTAXIS_EDIFACT
        assert not codigos(incidencias, ERROR)
        assert "EDI-UNA-DE-CINCO" in codigos(incidencias)
        assert len(raiz.xpath(mapa.lineas)) == 9


# --- Dos roturas del sobre que nadie provocaba -----------------------------


class TestElSobreQueNoSeSostiene:
    """Las dos que el guardián del catálogo encontró sin provocar.

    Las dos hablan de un fichero que ni siquiera llega a tener forma de
    intercambio, y ese es justo el caso en el que un validador puede acabar
    diciendo «no he visto nada mal» sobre algo que no ha leído.
    """

    def test_un_fichero_que_no_se_puede_partir_en_segmentos(self):
        """Se provoca en el lector y no en `factura.validar` a propósito.

        Para llegar aquí desde fuera, `detectar` tendría que reconocer como
        EDIFACT un fichero sin un solo segmento, y no lo hace ni debe: lo
        manda a «formato desconocido», que es la respuesta correcta. Este
        aviso es para quien llama al lector directamente.
        """
        _, incidencias = edifact.convertir(b"esto no es EDIFACT, ni lo pretende")
        salta = [i for i in incidencias if i.codigo == "EDI-SIN-SEGMENTOS"]
        assert salta and salta[0].gravedad == ERROR

    def test_un_mensaje_que_empieza_y_no_cierra(self):
        """Un UNH sin su UNT: el mensaje está cortado y no se sabe por dónde."""
        tira = (
            "UNB+UNOC:3+EMISOR+RECEPTOR+260819:1200+1'"
            "UNH+1+INVOIC:D:96A:UN'"
            "BGM+380+F-2026-1'"
            "UNZ+1+1'"
        ).encode("utf-8")
        salta = [i for i in quejas(tira) if i.codigo == "EDI-MENSAJE-SIN-CERRAR"]
        assert salta and salta[0].gravedad == ERROR

    def test_un_intercambio_entero_si_cierra(self):
        """El control: sin esto, lo de arriba no distingue nada."""
        assert "EDI-MENSAJE-SIN-CERRAR" not in codigos(quejas(sobre(CUERPO)))
        assert "EDI-SIN-SEGMENTOS" not in codigos(quejas(sobre(CUERPO)))
