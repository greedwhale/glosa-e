"""Dónde vive cada campo de EN 16931 en UBL y en CII.

La norma define un modelo semántico —los campos BT-1, BT-109, BT-117…— y
después cada sintaxis lo escribe a su manera. Este módulo es el diccionario
entre las dos: solo rutas XPath y las utilidades para leerlas.

Estaba dentro de `en16931`, pero las reglas de IVA también lo necesitan y no
tiene sentido que un módulo dependa del otro solo para consultar un mapa.
Añadir una sintaxis nueva debería ser rellenar otra `Sintaxis` sin tocar
ninguna regla.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

NS_UBL = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}

NS_CII = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": (
        "urn:un:unece:uncefact:data:standard:"
        "ReusableAggregateBusinessInformationEntity:100"
    ),
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}

# Un campo que esta sintaxis no sabe dónde escribe. No es lo mismo que un
# campo vacío: es que **no se ha podido averiguar** dónde va, y leerlo de un
# sitio equivocado sería peor que no leerlo, porque un importe sacado del
# cajonón de al lado entra en las cuentas y las descuadra sin avisar.
#
# Es una ruta válida que no encuentra nada nunca, para que quien la lea en el
# mapa vea que el hueco es a propósito y no un olvido. Lo que falte por aquí
# consta en el README.
SIN_MAPA = "./sin-correspondencia-en-esta-sintaxis"

# La norma trabaja con importes redondeados a dos decimales, así que una
# diferencia de un céntimo no es un error: es el redondeo permitido.
TOLERANCIA = Decimal("0.01")


@dataclass(frozen=True)
class Sintaxis:
    """El mapa de una sintaxis. Solo rutas: aquí no hay lógica."""

    nombre: str
    espacios: dict[str, str]
    nombre_perfil: str  # cómo se llama el campo del perfil en esta sintaxis

    perfil: str
    numero: str
    fecha: str
    tipo: str
    moneda: str

    vendedor_nombre: str
    vendedor_direccion: str
    vendedor_pais: str
    comprador_nombre: str
    comprador_direccion: str
    comprador_pais: str

    lineas: str
    linea_id: str  # relativa a una línea
    linea_importe: str  # relativa a una línea
    linea_categoria: str  # relativa a una línea: BT-151
    linea_tipo: str  # relativa a una línea: BT-152

    # El desglose por tipo de IVA (BG-23), que es donde se apoya casi toda la
    # comprobación del impuesto.
    desglose: str
    desglose_base: str  # BT-116, relativa a un grupo
    desglose_cuota: str  # BT-117
    desglose_categoria: str  # BT-118
    desglose_tipo: str  # BT-119
    desglose_motivo: str  # BT-120
    desglose_motivo_codigo: str  # BT-121

    # Descuentos y cargos a nivel de documento (BG-20 y BG-21), que entran en
    # la base de su categoría igual que las líneas.
    cargos: str
    cargo_es_cargo: str  # relativa: true si suma, false si resta
    cargo_importe: str
    cargo_categoria: str
    cargo_tipo: str

    suma_lineas: str
    base: str
    con_impuestos: str
    a_pagar: str
    descuentos_total: str
    cargos_total: str
    anticipos: str
    redondeo: str
    impuestos: str

    # Con qué se escribe «esto suma» en `cargo_es_cargo`. UBL y CII usan un
    # booleano, y por eso durante dos sintaxis esto no hizo falta. EDIFACT lo
    # escribe con una letra —C de cargo, A de descuento (*allowance*)—, así
    # que la comparación con «true» daba descuento en todos los cargos: los
    # restaba en vez de sumarlos y descuadraba la factura entera.
    marcas_de_cargo: tuple[str, ...] = ("true", "1")


_TOTAL_UBL = "./cac:LegalMonetaryTotal"
_VENDEDOR_UBL = "./cac:AccountingSupplierParty/cac:Party"
_COMPRADOR_UBL = "./cac:AccountingCustomerParty/cac:Party"

# UBL escribe dos elementos distintos para lo mismo según el documento sea una
# factura o un abono: `InvoiceTypeCode` frente a `CreditNoteTypeCode`, e
# `InvoiceLine` frente a `CreditNoteLine`. Todo lo demás —partes, totales,
# desglose de IVA— se llama igual en los dos.
#
# La unión XPath («a|b») coge el que haya, que es más seguro que mantener dos
# mapas y elegir uno: si se elige mal, las reglas leen el documento
# equivocado. Con el mapa de la factura a secas, un abono correcto salía con
# BR-04 y BR-16 inventados y, al no encontrársele las líneas, enmudecían de
# golpe BR-24, BR-CO-10 y todo el IVA. Acusado en falso y sin comprobar.
_TIPO_UBL = "./cbc:InvoiceTypeCode|./cbc:CreditNoteTypeCode"
_LINEAS_UBL = "./cac:InvoiceLine|./cac:CreditNoteLine"

SINTAXIS_UBL = Sintaxis(
    nombre="UBL",
    espacios=NS_UBL,
    nombre_perfil="CustomizationID",
    perfil="./cbc:CustomizationID",
    numero="./cbc:ID",
    fecha="./cbc:IssueDate",
    tipo=_TIPO_UBL,
    moneda="./cbc:DocumentCurrencyCode",
    vendedor_nombre=f"{_VENDEDOR_UBL}/cac:PartyLegalEntity/cbc:RegistrationName",
    vendedor_direccion=f"{_VENDEDOR_UBL}/cac:PostalAddress",
    vendedor_pais=(
        f"{_VENDEDOR_UBL}/cac:PostalAddress/cac:Country/cbc:IdentificationCode"
    ),
    comprador_nombre=f"{_COMPRADOR_UBL}/cac:PartyLegalEntity/cbc:RegistrationName",
    comprador_direccion=f"{_COMPRADOR_UBL}/cac:PostalAddress",
    comprador_pais=(
        f"{_COMPRADOR_UBL}/cac:PostalAddress/cac:Country/cbc:IdentificationCode"
    ),
    lineas=_LINEAS_UBL,
    linea_id="./cbc:ID",
    linea_importe="./cbc:LineExtensionAmount",
    linea_categoria="./cac:Item/cac:ClassifiedTaxCategory/cbc:ID",
    linea_tipo="./cac:Item/cac:ClassifiedTaxCategory/cbc:Percent",
    desglose="./cac:TaxTotal/cac:TaxSubtotal",
    desglose_base="./cbc:TaxableAmount",
    desglose_cuota="./cbc:TaxAmount",
    desglose_categoria="./cac:TaxCategory/cbc:ID",
    desglose_tipo="./cac:TaxCategory/cbc:Percent",
    desglose_motivo="./cac:TaxCategory/cbc:TaxExemptionReason",
    desglose_motivo_codigo="./cac:TaxCategory/cbc:TaxExemptionReasonCode",
    cargos="./cac:AllowanceCharge",
    cargo_es_cargo="./cbc:ChargeIndicator",
    cargo_importe="./cbc:Amount",
    cargo_categoria="./cac:TaxCategory/cbc:ID",
    cargo_tipo="./cac:TaxCategory/cbc:Percent",
    suma_lineas=f"{_TOTAL_UBL}/cbc:LineExtensionAmount",
    base=f"{_TOTAL_UBL}/cbc:TaxExclusiveAmount",
    con_impuestos=f"{_TOTAL_UBL}/cbc:TaxInclusiveAmount",
    a_pagar=f"{_TOTAL_UBL}/cbc:PayableAmount",
    descuentos_total=f"{_TOTAL_UBL}/cbc:AllowanceTotalAmount",
    cargos_total=f"{_TOTAL_UBL}/cbc:ChargeTotalAmount",
    anticipos=f"{_TOTAL_UBL}/cbc:PrepaidAmount",
    redondeo=f"{_TOTAL_UBL}/cbc:PayableRoundingAmount",
    impuestos="./cac:TaxTotal/cbc:TaxAmount",
)

# En CII casi todo cuelga de SupplyChainTradeTransaction, repartido en tres
# bloques: lo pactado (Agreement), la entrega (Delivery) y el cobro
# (Settlement). Los totales viven en el Settlement, y la cabecera —número,
# fecha y tipo— va aparte, en ExchangedDocument.
_TRANSACCION = "./rsm:SupplyChainTradeTransaction"
_ACUERDO = f"{_TRANSACCION}/ram:ApplicableHeaderTradeAgreement"
_COBRO = f"{_TRANSACCION}/ram:ApplicableHeaderTradeSettlement"
_SUMARIO = f"{_COBRO}/ram:SpecifiedTradeSettlementHeaderMonetarySummation"
_CABECERA = "./rsm:ExchangedDocument"

SINTAXIS_CII = Sintaxis(
    nombre="CII",
    espacios=NS_CII,
    nombre_perfil="GuidelineSpecifiedDocumentContextParameter",
    perfil=(
        "./rsm:ExchangedDocumentContext"
        "/ram:GuidelineSpecifiedDocumentContextParameter/ram:ID"
    ),
    numero=f"{_CABECERA}/ram:ID",
    fecha=f"{_CABECERA}/ram:IssueDateTime/udt:DateTimeString",
    tipo=f"{_CABECERA}/ram:TypeCode",
    moneda=f"{_COBRO}/ram:InvoiceCurrencyCode",
    vendedor_nombre=f"{_ACUERDO}/ram:SellerTradeParty/ram:Name",
    vendedor_direccion=f"{_ACUERDO}/ram:SellerTradeParty/ram:PostalTradeAddress",
    vendedor_pais=(
        f"{_ACUERDO}/ram:SellerTradeParty/ram:PostalTradeAddress/ram:CountryID"
    ),
    comprador_nombre=f"{_ACUERDO}/ram:BuyerTradeParty/ram:Name",
    comprador_direccion=f"{_ACUERDO}/ram:BuyerTradeParty/ram:PostalTradeAddress",
    comprador_pais=(
        f"{_ACUERDO}/ram:BuyerTradeParty/ram:PostalTradeAddress/ram:CountryID"
    ),
    lineas=f"{_TRANSACCION}/ram:IncludedSupplyChainTradeLineItem",
    linea_id="./ram:AssociatedDocumentLineDocument/ram:LineID",
    linea_importe=(
        "./ram:SpecifiedLineTradeSettlement"
        "/ram:SpecifiedTradeSettlementLineMonetarySummation/ram:LineTotalAmount"
    ),
    linea_categoria=(
        "./ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax"
        "/ram:CategoryCode"
    ),
    linea_tipo=(
        "./ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax"
        "/ram:RateApplicablePercent"
    ),
    desglose=f"{_COBRO}/ram:ApplicableTradeTax",
    desglose_base="./ram:BasisAmount",
    desglose_cuota="./ram:CalculatedAmount",
    desglose_categoria="./ram:CategoryCode",
    desglose_tipo="./ram:RateApplicablePercent",
    desglose_motivo="./ram:ExemptionReason",
    desglose_motivo_codigo="./ram:ExemptionReasonCode",
    cargos=f"{_COBRO}/ram:SpecifiedTradeAllowanceCharge",
    cargo_es_cargo="./ram:ChargeIndicator/udt:Indicator",
    cargo_importe="./ram:ActualAmount",
    cargo_categoria="./ram:CategoryTradeTax/ram:CategoryCode",
    cargo_tipo="./ram:CategoryTradeTax/ram:RateApplicablePercent",
    suma_lineas=f"{_SUMARIO}/ram:LineTotalAmount",
    base=f"{_SUMARIO}/ram:TaxBasisTotalAmount",
    con_impuestos=f"{_SUMARIO}/ram:GrandTotalAmount",
    a_pagar=f"{_SUMARIO}/ram:DuePayableAmount",
    descuentos_total=f"{_SUMARIO}/ram:AllowanceTotalAmount",
    cargos_total=f"{_SUMARIO}/ram:ChargeTotalAmount",
    anticipos=f"{_SUMARIO}/ram:TotalPrepaidAmount",
    redondeo=f"{_SUMARIO}/ram:RoundingAmount",
    impuestos=f"{_SUMARIO}/ram:TaxTotalAmount",
)

# --- EDIFACT ---------------------------------------------------------------

# EDIFACT no nombra sus campos: los coloca. El módulo `edifact` deshace eso y
# entrega un árbol con los nombres del directorio —`S_NAD`, `C_C080`,
# `D_3036`—, que es la forma que ISO 20625 le da al mismo mensaje escrito como
# XML y la que usa la Comisión Europea en sus ejemplos. Desde aquí ya es XML
# y se lee con XPath como los otros dos.
#
# **Estas rutas no nombran ningún grupo, y es lo importante.** En EDIFACT los
# grupos van numerados y la numeración cambia con la versión del directorio:
# las líneas son el grupo 26 en la D.96A que traen las facturas de verdad y el
# 27 en la D.14B que publica la Comisión. Una ruta con el número dentro
# obligaría a un mapa por versión. Preguntando en cambio por *lo que hay
# dentro* —«el grupo que contiene un S_LIN»— la misma ruta vale para las dos, y
# para las que vengan.
#
# Lo que distingue un dato de otro es el **cualificador**, no el sitio: el
# total sin impuestos y el importe de una línea son los dos un `MOA`, y lo
# único que los separa es que uno dice 389 y el otro 203. Esos códigos no se
# han copiado de una tabla: se comprobaron contra los nueve ejemplos de la
# Comisión haciendo la cuenta —el 79 es la suma de los 203 en los nueve, y el
# 388 es el 389 más el 176 en los nueve—, que es la única manera de saber que
# un cualificador significa lo que uno cree.
_VENDEDOR_EDI = "./*[S_NAD/D_3035='SE' or S_NAD/D_3035='SU']"
_COMPRADOR_EDI = "./*[S_NAD/D_3035='BY']"


def _direccion_edi(parte: str) -> str:
    """La dirección postal de una parte, entendida como en la norma.

    En UBL y en CII la dirección es un elemento que la contiene entera, y con
    que exista basta. EDIFACT no tiene ese elemento: la calle, la ciudad, el
    código postal y el país son cuatro posiciones sueltas del NAD. Preguntar
    solo por la calle no es lo mismo que preguntar por la dirección, y la
    diferencia no es teórica: `EDIFACT_EXAMPLE6` de la Comisión trae el país
    y no la calle, y salía acusado de no llevar dirección cuando lleva la que
    la norma exige.
    """
    campos = ("C_C059", "D_3164", "D_3251", "D_3207", "C_C819")
    return " | ".join(f"{parte}/S_NAD/{campo}" for campo in campos)


def _total_edi(cualificador: str) -> str:
    """Un total de la factura, por su cualificador de importe.

    Se pide como hijo de un grupo que cuelga de la raíz —`./*/S_MOA`— y no en
    cualquier sitio: los importes de línea viven más hondo y con `.//` se
    colarían en los totales.
    """
    return f"./*/S_MOA/C_C516[D_5025='{cualificador}']/D_5004"


SINTAXIS_EDIFACT = Sintaxis(
    nombre="EDIFACT",
    espacios={},
    nombre_perfil="FTX+DOC",
    perfil="./S_FTX[D_4451='DOC']/C_C108/D_4440",
    numero="./S_BGM/C_C106/D_1004",
    fecha="./S_DTM/C_C507[D_2005='137']/D_2380",
    tipo="./S_BGM/C_C002/D_1001",
    moneda="./*/S_CUX/C_C504[D_6347='2']/D_6345",
    vendedor_nombre=f"{_VENDEDOR_EDI}/S_NAD/C_C080/D_3036",
    vendedor_direccion=_direccion_edi(_VENDEDOR_EDI),
    vendedor_pais=f"{_VENDEDOR_EDI}/S_NAD/D_3207",
    comprador_nombre=f"{_COMPRADOR_EDI}/S_NAD/C_C080/D_3036",
    comprador_direccion=_direccion_edi(_COMPRADOR_EDI),
    comprador_pais=f"{_COMPRADOR_EDI}/S_NAD/D_3207",
    # Cualquier grupo que contenga una línea, se llame como se llame.
    lineas=".//*[S_LIN]",
    linea_id="./S_LIN/D_1082",
    linea_importe="./*/S_MOA/C_C516[D_5025='203']/D_5004",
    # El IVA propio de la línea es el del grupo que cuelga directamente de
    # ella. El de un descuento de línea cuelga del descuento, un piso más
    # abajo, y por eso no entra aquí.
    linea_categoria="./*[S_TAX]/S_TAX/D_5305",
    linea_tipo="./*[S_TAX]/S_TAX/C_C243/D_5278",
    # El desglose del documento son los grupos de impuesto que cuelgan de la
    # raíz. Los de línea y los de un descuento cuelgan de otra cosa.
    desglose="./*[S_TAX]",
    desglose_base="./S_MOA/C_C516[D_5025='125']/D_5004",
    desglose_cuota="./S_MOA/C_C516[D_5025='124']/D_5004",
    desglose_categoria="./S_TAX/D_5305",
    desglose_tipo="./S_TAX/C_C243/D_5278",
    # El motivo de una exención (BT-120) no va dentro del grupo de impuesto,
    # como en UBL y en CII, sino suelto en un FTX del documento con el
    # cualificador AGM. Lo único que lo ata a una categoría es que explica la
    # que no tributa, y por eso ese vínculo lo tiene que poner la ruta: el
    # documento no lo escribe en ninguna parte.
    #
    # De ahí las dos mitades. El «..» sube del grupo al documento a buscar el
    # FTX; el filtro de delante deja fuera las categorías que **no** pueden
    # llevar motivo. Sin él, un documento con dos tipos normales y uno exento
    # —el `EDIFACT_EXAMPLE2` de la Comisión— le pasaba el motivo del exento a
    # los otros dos y salían acusados de llevar un motivo que no llevan.
    #
    # Queda una limitación, y es de la norma y no de aquí: con dos categorías
    # exentas y dos motivos no hay forma de saber cuál es de cuál.
    desglose_motivo=(
        "self::*[not(S_TAX/D_5305='S' or S_TAX/D_5305='Z')]"
        "/../S_FTX[D_4451='AGM']/C_C108/D_4440"
    ),
    # El código del motivo (BT-121) se queda sin leer, como el redondeo: no
    # aparece en ninguna muestra y no se ha podido confirmar dónde se escribe.
    desglose_motivo_codigo=SIN_MAPA,
    cargos="./*[S_ALC]",
    cargo_es_cargo="./S_ALC/D_5463",
    # Tres cualificadores para lo mismo porque así viene: la Comisión escribe
    # 204 el descuento y 23 el cargo, y las facturas de verdad usan el 8 para
    # los dos. El 25, que aparece al lado, es la base sobre la que se calcula
    # y no el importe; meterlo aquí doblaría el descuento.
    cargo_importe=(
        "./*/S_MOA/C_C516[D_5025='8' or D_5025='23' or D_5025='204']/D_5004"
    ),
    cargo_categoria="./*[S_TAX]/S_TAX/D_5305",
    cargo_tipo="./*[S_TAX]/S_TAX/C_C243/D_5278",
    suma_lineas=_total_edi("79"),
    base=_total_edi("389"),
    con_impuestos=_total_edi("388"),
    a_pagar=_total_edi("9"),
    descuentos_total=_total_edi("260"),
    cargos_total=_total_edi("259"),
    anticipos=_total_edi("113"),
    # El redondeo (BT-114) se queda sin leer a propósito: no hay ninguna
    # muestra que lo traiga y no se ha podido confirmar con qué cualificador
    # se escribe. Inventarlo sería peor que no leerlo —un cualificador
    # equivocado se tragaría un importe ajeno y lo sumaría al total—, y no
    # leerlo equivale a que no lo haya, que es el caso de todas las facturas
    # vistas. Consta en el README como lo que falta.
    redondeo=SIN_MAPA,
    impuestos=_total_edi("176"),
    marcas_de_cargo=("c",),
)


# Nombres de familia sin importar `formato`, que no hace falta aquí.
SINTAXIS: dict[str, Sintaxis] = {
    "UBL": SINTAXIS_UBL,
    "CII": SINTAXIS_CII,
    "EDIFACT": SINTAXIS_EDIFACT,
}


# --- Lectura ---------------------------------------------------------------


def texto(nodo, ruta: str, sintaxis: Sintaxis) -> str | None:
    encontrados = nodo.xpath(ruta, namespaces=sintaxis.espacios)
    if not encontrados:
        return None
    valor = encontrados[0]
    crudo = valor if isinstance(valor, str) else (valor.text or "")
    crudo = crudo.strip()
    return crudo or None


def a_decimal(bruto: str | None) -> Decimal | None:
    if bruto is None:
        return None
    try:
        return Decimal(bruto.strip())
    except InvalidOperation:
        return None


def importe(nodo, ruta: str, sintaxis: Sintaxis) -> Decimal | None:
    """Lee un importe como Decimal. Devuelve None si falta o no es un número."""
    return a_decimal(texto(nodo, ruta, sintaxis))


def importe_en_moneda(
    nodo, ruta: str, sintaxis: Sintaxis, moneda: str | None
) -> Decimal | None:
    """El importe declarado en la moneda de la factura.

    Tanto UBL como CII permiten declarar el total de impuestos dos veces: una
    en la moneda de la factura (BT-110) y otra en la moneda de contabilidad
    (BT-111), distinguidas por el atributo `currencyID`. Coger el primero que
    aparezca es coger uno al azar: si el documento las trae en el otro orden,
    el cuadre falla por una factura que está bien.
    """
    encontrados = nodo.xpath(ruta, namespaces=sintaxis.espacios)
    if not encontrados:
        return None
    elegido = encontrados[0]
    if moneda:
        for candidato in encontrados:
            if candidato.get("currencyID") == moneda:
                elegido = candidato
                break
    return a_decimal(elegido.text)


def cuadra(a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= TOLERANCIA


def fmt(valor: Decimal | None) -> str:
    return "(vacío)" if valor is None else f"{valor:.2f}"


def fmt_tipo(valor: Decimal | None) -> str:
    """Un tipo de IVA, sin ceros de adorno: 21 y no 21.00."""
    if valor is None:
        return "(sin tipo)"
    normalizado = valor.normalize()
    if normalizado == normalizado.to_integral_value():
        normalizado = normalizado.quantize(Decimal(1))
    return f"{normalizado}%"
