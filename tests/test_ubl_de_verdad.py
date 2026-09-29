"""Lo que dicen los esquemas de UBL de verdad, no los de doce líneas.

`test_esquema.py` prueba la traducción con esquemas de juguete, y está bien
para lo que prueba. Lo que no puede probar es lo que hace **libxml2 con los de
verdad**: sus mensajes cambian según cómo esté declarado el tipo, y en UBL los
importes, y en la 2.5 las fechas y las horas, están declarados de una manera
que un esquema de doce líneas no reproduce.

Se sacan de `web/paquete.zip`, que sí se versiona, y no de `esquemas/`, que no:
estas pruebas corren en GitHub y en una copia recién clonada, no solo donde
alguien se bajó los XSD. Ver la fixture `esquemas_del_paquete`.
"""

import re
from pathlib import Path

import pytest
from lxml import etree

from validador import esquema
from validador.esquema import Catalogo

RAIZ = Path(__file__).resolve().parent.parent
XS = "http://www.w3.org/2001/XMLSchema"

# El ejemplo se toma con la versión que toque en cada prueba. Sin
# `UBLVersionID` se asumiría la 2.1 y no se probaría lo de la 2.5.
FACTURA = (RAIZ / "ejemplos" / "f-0001.xml").read_text(encoding="utf-8")


def _con_version(version: str) -> str:
    viejo = "<cbc:UBLVersionID>2.1</cbc:UBLVersionID>"
    assert viejo in FACTURA, "el ejemplo ha cambiado de forma"
    return FACTURA.replace(viejo, f"<cbc:UBLVersionID>{version}</cbc:UBLVersionID>")


def _cambiando(version: str, viejo: str, nuevo: str) -> str:
    texto = _con_version(version)
    assert viejo in texto, f"el ejemplo ya no trae {viejo!r}"
    return texto.replace(viejo, nuevo, 1)


@pytest.fixture
def catalogo(esquemas_del_paquete):
    return Catalogo(esquemas_del_paquete)


def _codigos(informe) -> list[str]:
    return [i.codigo for i in informe.incidencias]


@pytest.mark.parametrize("version", ["2.1", "2.5"])
class TestUnErrorDeTipoSeTraduceConElEsquemaDeVerdad:
    """Sin nombre de tipo que dar, libxml2 dice otra frase, y salía en inglés.

    Reproducido el 29-09-2026: con `PayableAmount` `1.234,56` —la coma decimal,
    el fallo más corriente de una factura hecha a mano— el informe traía
    `XSD-OTRO` y «is not a valid value of the local atomic type». En la 2.5,
    además, cualquier fecha imposible: y la 2.5 es la única versión que admite
    la solución pública.
    """

    def test_una_coma_decimal_en_un_importe(self, catalogo, version):
        texto = _cambiando(
            version,
            '<cbc:PayableAmount currencyID="EUR">121.00',
            '<cbc:PayableAmount currencyID="EUR">1.234,56',
        )
        informe = esquema.validar(texto, catalogo)
        assert _codigos(informe) == ["XSD-TIPO"], informe.detalle()
        assert "punto decimal" in informe.incidencias[0].mensaje
        assert informe.incidencias[0].encontrado == "1.234,56"

    def test_un_dia_que_no_existe(self, catalogo, version):
        texto = _cambiando(
            version,
            "<cbc:IssueDate>2026-03-02</cbc:IssueDate>",
            "<cbc:IssueDate>2026-02-31</cbc:IssueDate>",
        )
        informe = esquema.validar(texto, catalogo)
        assert _codigos(informe) == ["XSD-TIPO"], informe.detalle()
        # La pista mira el valor: no le dice «AAAA-MM-DD» a quien ya lo escribió así.
        assert "febrero de 2026 tiene 28 días" in informe.incidencias[0].mensaje

    def test_una_fecha_que_no_es_una_fecha(self, catalogo, version):
        texto = _cambiando(
            version,
            "<cbc:IssueDate>2026-03-02</cbc:IssueDate>",
            "<cbc:IssueDate>ayer</cbc:IssueDate>",
        )
        informe = esquema.validar(texto, catalogo)
        assert _codigos(informe) == ["XSD-TIPO"], informe.detalle()
        assert "AAAA-MM-DD" in informe.incidencias[0].mensaje

    def test_un_porcentaje_con_letras(self, catalogo, version):
        texto = _cambiando(
            version, "<cbc:Percent>21</cbc:Percent>", "<cbc:Percent>veinte</cbc:Percent>"
        )
        informe = esquema.validar(texto, catalogo)
        assert _codigos(informe) == ["XSD-TIPO"], informe.detalle()

    def test_nada_sale_en_ingles(self, catalogo, version):
        texto = _cambiando(
            version,
            "<cbc:IssueDate>2026-03-02</cbc:IssueDate>",
            "<cbc:IssueDate>2026-13-01</cbc:IssueDate>",
        )
        informe = esquema.validar(texto, catalogo)
        assert "atomic type" not in informe.detalle()


def _tipos_y_elementos_cbc(carpeta: Path):
    """Todos los tipos con nombre y los elementos de `CommonBasicComponents`."""
    tipos, elementos = {}, {}
    for ruta in carpeta.rglob("*.xsd"):
        raiz = etree.parse(str(ruta)).getroot()
        destino = raiz.get("targetNamespace")
        for tipo in list(raiz.iter(f"{{{XS}}}complexType")) + list(
            raiz.iter(f"{{{XS}}}simpleType")
        ):
            if tipo.get("name") and tipo.getparent() is raiz:
                tipos.setdefault((destino, tipo.get("name")), tipo)
        if destino and destino.endswith("CommonBasicComponents-2"):
            for elemento in raiz.findall(f"{{{XS}}}element"):
                elementos[elemento.get("name")] = (
                    destino,
                    elemento.get("type").split(":")[-1],
                )
    return tipos, elementos


def _cualificado(nombre: str, nodo) -> tuple[str | None, str]:
    if ":" in nombre:
        prefijo, local = nombre.split(":", 1)
        return nodo.nsmap.get(prefijo), local
    return nodo.nsmap.get(None) or nodo.getroottree().getroot().get(
        "targetNamespace"
    ), nombre


def _primitivo(clave, tipos, visto=()) -> str:
    """El tipo primitivo de XSD que hay al fondo de un tipo de UBL."""
    destino, nombre = clave
    if destino == XS:
        return nombre
    assert clave not in visto, f"el tipo {nombre} se define a partir de sí mismo"
    tipo = tipos.get(clave)
    assert tipo is not None, f"no se encuentra el tipo {nombre}"
    for etiqueta in ("extension", "restriction"):
        for derivacion in tipo.iter(f"{{{XS}}}{etiqueta}"):
            if derivacion.get("base") is not None:
                return _primitivo(
                    _cualificado(derivacion.get("base"), derivacion),
                    tipos,
                    visto + (clave,),
                )
    return "union"


# Los elementos que acaban como uno decimal y no lo son. Es un texto: no puede
# dar el error de tipo, así que el sufijo se equivoca sin consecuencia.
NO_ES_LO_QUE_DICE_SU_NOMBRE = {"TimeAmount"}


@pytest.mark.parametrize("carpeta", ["ubl", "ubl-2.5"])
def test_el_sufijo_del_nombre_dice_el_tipo_de_todos_los_elementos_de_ubl(
    esquemas_del_paquete, carpeta
):
    """Es lo que sostiene el comentario de `_tipo_por_nombre`.

    El mensaje de libxml2 no trae el tipo y se deduce del nombre. Eso es una
    apuesta, y se cierra igual que las demás de este repositorio: midiéndola en
    todos los elementos de `CommonBasicComponents`, no en los tres que se
    probaron a mano. Si una versión nueva de UBL declara una fecha que no acaba
    en `Date`, o un decimal con otro sufijo, se sabe aquí.
    """
    tipos, elementos = _tipos_y_elementos_cbc(esquemas_del_paquete / carpeta)
    assert len(elementos) > 800, "no se han leído los elementos"

    de_mas, de_menos = [], []
    for nombre, (destino, tipo) in sorted(elementos.items()):
        primitivo = _primitivo((destino, tipo), tipos)
        deducido = esquema._tipo_por_nombre(nombre)
        deducido = deducido.removeprefix("xs:") if deducido else None
        if primitivo in ("date", "time", "dateTime", "decimal"):
            if deducido != primitivo:
                de_menos.append((nombre, primitivo, deducido))
        elif deducido is not None and nombre not in NO_ES_LO_QUE_DICE_SU_NOMBRE:
            de_mas.append((nombre, primitivo, deducido))

    assert not de_menos, f"el nombre no dice el tipo de: {de_menos}"
    assert not de_mas, f"el nombre dice un tipo que no es: {de_mas}"


def test_la_unica_excepcion_sigue_siendo_una(esquemas_del_paquete):
    """Si las excepciones crecen, el sufijo ha dejado de servir y hay que saberlo."""
    for carpeta in ("ubl", "ubl-2.5"):
        tipos, elementos = _tipos_y_elementos_cbc(esquemas_del_paquete / carpeta)
        excepciones = {
            nombre
            for nombre, (destino, tipo) in elementos.items()
            if esquema._tipo_por_nombre(nombre)
            and _primitivo((destino, tipo), tipos)
            != esquema._tipo_por_nombre(nombre).removeprefix("xs:")
        }
        assert excepciones == NO_ES_LO_QUE_DICE_SU_NOMBRE, carpeta


def test_lo_que_no_se_reconoce_no_se_inventa():
    """Un nombre sin sufijo conocido no tiene tipo deducido: pista genérica."""
    assert esquema._tipo_por_nombre("Note") is None
    assert esquema._tipo_por_nombre("CompanyID") is None
    assert not re.search(r"atomic", esquema._pista("xs:time", "25:99:00"))
