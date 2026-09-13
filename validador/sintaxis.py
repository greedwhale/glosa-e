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

import re
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal, InvalidOperation

from validador import cius_es

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
    # Sin valor por defecto a propósito: una sintaxis nueva no puede olvidarse
    # de contestar a estas tres. Si se les pusiera `SIN_MAPA` por defecto, el
    # olvido saldría como un hueco declarado, que es justo la mentira que el
    # centinela existe para evitar.
    linea_cantidad: str  # relativa a una línea: BT-129
    linea_unidad: str  # relativa a una línea: BT-130
    linea_precio: str  # relativa a una línea: BT-146
    linea_nombre: str  # relativa a una línea: BT-153
    # Qué vocabulario usa esta sintaxis para la categoría de IVA (BT-118).
    # Vacío quiere decir «ya viene en UNCL5305, tal cual»: es el caso de UBL,
    # CII y EDIFACT, que escriben la S o la E directamente. Facturae escribe
    # otra cosa —qué impuesto es, no de qué categoría— y hay que deducirla;
    # cómo, en `iva._derivar_categoria`, que es donde vive lo del IVA.
    #
    # Sigue siendo un dato y no una regla: aquí se dice cuál se aplica, no qué
    # hace.
    categoria_derivada: str
    # Lo mismo para BT-3, el codigo de tipo de documento. UBL, CII y EDIFACT
    # escriben directamente el 380 o el 381 de UNTDID 1001; Facturae escribe
    # su propio vocabulario y hace falta traducirlo. Los dos campos de abajo
    # son de donde sale esa traduccion y solo Facturae los usa.
    tipo_derivado: str
    tipo_clase: str    # Facturae: original, rectificativa, copia...
    tipo_emisor: str   # Facturae: quien emite, que es lo que distingue el 389
    # Cómo rectifica una rectificativa, que es lo que decide su código europeo.
    # La lista de valores es la del esquema oficial, no una reconstruida: está
    # en `CorrectionMethodType` de `Facturaev3_2_2.xsd`. Aquí se dijo durante
    # meses que «no se ha podido contrastar contra una fuente oficial», y la
    # fuente oficial iba dentro de `web/paquete.zip` todo el tiempo.
    tipo_metodo: str   # Facturae: 01 integra, 02 diferencias, 03 volumen, 04 AEAT
    linea_categoria: str  # relativa a una línea: BT-151
    linea_tipo: str  # relativa a una línea: BT-152
    # La fiscalidad especial de Facturae, que es media respuesta a BT-118.
    #
    # Durante un tiempo este repositorio afirmó que Facturae no tiene «ningún
    # campo donde se haya escrito cuál» es la categoría de un tipo cero. Era
    # falso, y lo era porque nadie fue a mirar el esquema que nosotros mismos
    # servimos: `SpecialTaxableEvent/SpecialTaxableEventCode` existe en la
    # línea, con dos valores —`01` sujeta y exenta, `02` no sujeta—, que son
    # la E y la O de UNCL5305.
    #
    # Media respuesta y no una entera: Z, K, G y AE se siguen escribiendo
    # igual, y el elemento es opcional. Las otras tres sintaxis escriben la
    # categoría directamente y no necesitan esto, así que va `SIN_MAPA`.
    linea_fiscalidad_especial: str

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

    # Si en BR-CO-17 una cuota a **exactamente** una unidad de base por tipo
    # vale o no. Es un borde, y los dos esquematrones oficiales lo resuelven al
    # revés: el de UBL escribe `<` y el de CII `<=`, y las pruebas unitarias de
    # cada uno prueban justo ese punto —1000 al 25% con 251 de cuota es error
    # en UBL; -72,50 al 19% con -12,78 es correcto en CII—. Sin valor por
    # defecto: una sintaxis nueva tiene que decir cuál sigue.
    cuota_admite_la_unidad_justa: bool

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
    # La cantidad se llama distinto en un abono, como las líneas y el tipo de
    # documento. La unión coge la que haya; con una sola, BR-22 y BR-23
    # saldrían inventadas en todos los abonos correctos.
    linea_cantidad="./cbc:InvoicedQuantity|./cbc:CreditedQuantity",
    # BT-130 va en un **atributo**, no en un elemento. Es el único campo del
    # mapa que lo hace, y por eso la ruta acaba en `@`.
    linea_unidad="./cbc:InvoicedQuantity/@unitCode|./cbc:CreditedQuantity/@unitCode",
    linea_precio="./cac:Price/cbc:PriceAmount",
    linea_nombre="./cac:Item/cbc:Name",
    categoria_derivada="",
    tipo_derivado="",
    tipo_clase=SIN_MAPA,
    tipo_emisor=SIN_MAPA,
    tipo_metodo=SIN_MAPA,
    linea_categoria="./cac:Item/cac:ClassifiedTaxCategory/cbc:ID",
    linea_tipo="./cac:Item/cac:ClassifiedTaxCategory/cbc:Percent",
    desglose="./cac:TaxTotal/cac:TaxSubtotal",
    linea_fiscalidad_especial=SIN_MAPA,
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
    cuota_admite_la_unidad_justa=False,  # el esquematrón de UBL: desigualdad estricta
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
    # En CII no hay dos nombres para factura y abono: la cantidad es la misma
    # `BilledQuantity` en los dos, y lo que cambia es el signo.
    linea_cantidad="./ram:SpecifiedLineTradeDelivery/ram:BilledQuantity",
    linea_unidad="./ram:SpecifiedLineTradeDelivery/ram:BilledQuantity/@unitCode",
    linea_precio=(
        "./ram:SpecifiedLineTradeAgreement"
        "/ram:NetPriceProductTradePrice/ram:ChargeAmount"
    ),
    linea_nombre="./ram:SpecifiedTradeProduct/ram:Name",
    categoria_derivada="",
    tipo_derivado="",
    tipo_clase=SIN_MAPA,
    tipo_emisor=SIN_MAPA,
    linea_categoria=(
        "./ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax"
        "/ram:CategoryCode"
    ),
    linea_tipo=(
        "./ram:SpecifiedLineTradeSettlement/ram:ApplicableTradeTax"
        "/ram:RateApplicablePercent"
    ),
    tipo_metodo=SIN_MAPA,
    desglose=f"{_COBRO}/ram:ApplicableTradeTax",
    linea_fiscalidad_especial=SIN_MAPA,
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
    cuota_admite_la_unidad_justa=True,  # el esquematrón de CII: `<=`
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
    # Cualificador 47 = «cantidad facturada». El esquematrón oficial lo pide
    # así en BR-22 y BR-23, y en EDIFACT los dos datos —la cifra y la unidad—
    # viajan en el mismo compuesto: D_6060 es cuánto y D_6411 en qué unidad.
    linea_cantidad="./S_QTY/C_C186[D_6063='47']/D_6060",
    linea_unidad="./S_QTY/C_C186[D_6063='47']/D_6411",
    # El binding oficial dice `G_SG30/S_PRI/...`. Aquí se pide como hijo de
    # cualquier grupo de la línea, igual que se hace con el importe: en las
    # facturas reales el precio no siempre cuelga del grupo que la norma
    # nombra, y con la ruta estricta BR-26 saldría en todas.
    linea_precio="./*/S_PRI/C_C509[D_5125='AAA']/D_5118",
    # El nombre del concepto: IMD+F++:::<texto>, cuarto componente del
    # C273. Comprobado sobre `ejemplos/edi-0001.edi`.
    linea_nombre="./S_IMD/C_C273/D_7008",
    categoria_derivada="",
    tipo_derivado="",
    tipo_clase=SIN_MAPA,
    tipo_emisor=SIN_MAPA,
    # El IVA propio de la línea es el del grupo que cuelga directamente de
    # ella. El de un descuento de línea cuelga del descuento, un piso más
    # abajo, y por eso no entra aquí.
    tipo_metodo=SIN_MAPA,
    linea_categoria="./*[S_TAX]/S_TAX/D_5305",
    linea_tipo="./*[S_TAX]/S_TAX/C_C243/D_5278",
    # El desglose del documento son los grupos de impuesto que cuelgan de la
    # raíz. Los de línea y los de un descuento cuelgan de otra cosa.
    desglose="./*[S_TAX]",
    linea_fiscalidad_especial=SIN_MAPA,
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
    cuota_admite_la_unidad_justa=False,  # sin prueba oficial que lo decida; se sigue el de UBL
    marcas_de_cargo=("c",),
)


# --- Facturae ---------------------------------------------------------------
#
# Este mapa no existe en ninguna norma. CEN publicó `CEN/TS 16931-3-2` para
# UBL, `-3-3` para CII y `-3-4` para EDIFACT —esta última con tres ediciones,
# 2017, 2020 y 2026—, y **para Facturae no
# publicó nada**: no hay parte que diga qué elemento de Facturae es qué término
# de negocio. Hasta marzo de 2026 eso no importaba, porque Facturae era el formato
# nacional y EN 16931 no se le exigía. El artículo 7.1 del RD 238/2026 lo
# cambió: la factura debe ajustarse al modelo semántico EN 16931 **bajo
# cualquiera de las cuatro sintaxis admitidas**, y Facturae es una de ellas.
#
# Cuándo obliga es otra cosa y aquí se escribió mal una vez: el decreto está en
# vigor desde el 20-04-2026, pero su aplicación efectiva se cuenta desde una
# orden ministerial que todavía es un proyecto, así que la obligación cae en
# 10-2027 para quien factura más de 8 M€ y en 10-2028 para el resto. Da igual
# para este mapa —hay que escribirlo de todas formas— y no da igual para lo que
# se publica: la fecha estuvo unas horas en la página diciendo otra cosa.
#
# Así que el mapa hay que escribirlo, y escribirlo es tomar decisiones que
# nadie ha refrendado. La regla de esta casa es que una decisión tomada por
# quien lee solo vale si se declara, y por eso cada hueco de aquí abajo lleva
# escrito **por qué** está vacío. Lo que no se puede leer no se inventa: se
# marca `SIN_MAPA` y la regla correspondiente calla o avisa, pero no acusa.
#
# Un detalle de forma que ahorra mucho: **solo la raíz lleva espacio de
# nombres**. Medido sobre `ejemplos/fe-0001.xml`, de 116 elementos hay 27 con
# espacio de nombres —los 27 son la firma XAdES— y 89 sin él. Los esquemas de
# Facturae dejan los hijos sin cualificar, así que ninguna ruta de este mapa
# necesita prefijo. Y como la única diferencia entre 3.0, 3.1, 3.2, 3.2.1 y
# 3.2.2 es la URI de esa raíz, que aquí no se nombra nunca, **el mismo mapa
# sirve para las cinco versiones**.
#
# Las rutas se evalúan sobre un `<Invoice>`, no sobre la raíz: un fichero
# Facturae es un lote y puede traer varias. Por eso las partes, que están
# fuera de la factura y son comunes al lote, se piden subiendo dos pisos.
_VENDEDOR_FE = "../../Parties/SellerParty"
_COMPRADOR_FE = "../../Parties/BuyerParty"


def _nombre_fe(parte: str) -> str:
    """El nombre de una parte, sea persona jurídica o física.

    Facturae las escribe en dos sitios distintos y excluyentes:
    `LegalEntity/CorporateName` para una sociedad, `Individual/Name` para una
    persona. EN 16931 tiene un solo BT-27, así que la unión coge el que haya.
    Del apellido se prescinde a propósito: BT-27 es un nombre, no un nombre
    estructurado, y pegar `Name` y `FirstSurname` aquí sería inventar formato.
    """
    return f"{parte}/LegalEntity/CorporateName|{parte}/Individual/Name"


def _direccion_fe(parte: str) -> str:
    """La calle de una parte, esté en España o fuera.

    `AddressInSpain` y `OverseasAddress` son dos tipos distintos del esquema y
    solo puede haber uno. Coinciden en `Address` y en `CountryCode`, que es lo
    que se lee aquí, y difieren en el resto —la de fuera junta código postal y
    población en `PostCodeAndTown`—, que no hace falta para BR-08.
    """
    return f"{parte}/*/AddressInSpain/Address|{parte}/*/OverseasAddress/Address"


def _pais_fe(parte: str) -> str:
    return (
        f"{parte}/*/AddressInSpain/CountryCode"
        f"|{parte}/*/OverseasAddress/CountryCode"
    )


SINTAXIS_FACTURAE = Sintaxis(
    nombre="Facturae",
    # Vacío a propósito: los hijos no van cualificados. Ver arriba.
    espacios={},
    nombre_perfil="(ninguno)",
    # BT-24, y es el hueco que define este mapa entero.
    #
    # EN 16931 exige que la factura declare a qué especificación se ajusta.
    # **Facturae no tiene ese campo.** Lo único parecido es `SchemaVersion`,
    # que dice «3.2.2», y eso no es lo mismo: declara la versión del esquema de
    # Facturae, no conformidad con una norma europea. Buscado en el esquema
    # oficial: de «Version», «Specification», «Guideline», «Customization» y
    # «Profile», lo único que existe es `SchemaVersion`.
    #
    # La consecuencia es incómoda y hay que decirla entera: aplicando BR-01 en
    # estricto, **todas las facturas de España suspenden**, hoy y siempre, y no
    # por estar mal hechas sino porque el formato no tiene dónde escribirlo.
    # Un validador que devuelva eso no informa de nada. Por eso aquí BR-01 sale
    # como NOTA y no como error, y la nota explica que el hueco es del formato.
    # Esa decisión se toma en `en16931.py` y se declara en el informe.
    perfil=SIN_MAPA,
    numero="./InvoiceHeader/InvoiceNumber",
    fecha="./InvoiceIssueData/IssueDate",
    # BT-3. Ojo: **no es la misma lista de códigos**. EN 16931 usa UNCL1001
    # —380 factura, 381 abono—, y Facturae usa `InvoiceDocumentType` con FC
    # (completa), FA (simplificada) y AF (autofactura), más `InvoiceClass` con
    # OO, OR, OC, CO, CR y CC para original, rectificativa y copia.
    #
    # Se lee el elemento tal cual y **no se traduce aquí**: este fichero es
    # solo rutas. Que «FC» no sea «380» es cierto y hay que decirlo, pero
    # decirlo es trabajo de una regla, no de un mapa. Mientras tanto BR-04
    # comprueba lo que puede comprobar: que el documento diga de qué tipo es.
    tipo="./InvoiceHeader/InvoiceDocumentType",
    moneda="./InvoiceIssueData/InvoiceCurrencyCode",
    vendedor_nombre=_nombre_fe(_VENDEDOR_FE),
    vendedor_direccion=_direccion_fe(_VENDEDOR_FE),
    vendedor_pais=_pais_fe(_VENDEDOR_FE),
    comprador_nombre=_nombre_fe(_COMPRADOR_FE),
    comprador_direccion=_direccion_fe(_COMPRADOR_FE),
    comprador_pais=_pais_fe(_COMPRADOR_FE),
    lineas="./Items/InvoiceLine",
    # BT-126, el identificador de línea, **no existe en Facturae**. El esquema
    # da `SequenceNumber`, pero es opcional y significa otra cosa —el orden de
    # la línea en un pedido—, así que usarlo como identificador sería ponerle
    # un nombre que nadie le ha dado. Sin mapa: la regla que lo pide se calla.
    linea_id=SIN_MAPA,
    # BT-131 es el importe neto de la línea, y en Facturae es `GrossAmount`
    # pese al nombre: `TotalCost` es cantidad por precio **antes** de los
    # descuentos de línea, y `GrossAmount` es lo que queda después. El que
    # cuadra con la suma de líneas es el segundo.
    linea_importe="./GrossAmount",
    # BT-129 y BT-146 los tiene Facturae, y obligatorios en su propio esquema.
    linea_cantidad="./Quantity",
    linea_precio="./UnitPriceWithoutTax",
    linea_nombre="./ItemDescription",
    categoria_derivada="facturae",
    tipo_derivado="facturae",
    tipo_clase="./InvoiceHeader/InvoiceClass",
    # Va en la cabecera del fichero, no en la factura: por eso sube dos
    # niveles, igual que el vendedor y el comprador.
    tipo_emisor="../../FileHeader/InvoiceIssuerType",
    # BT-130, y **aquí está la divergencia que hace útil todo este binding**.
    #
    # `UnitOfMeasure` existe en Facturae pero el esquema lo declara opcional
    # (`minOccurs="0"`), y EN 16931 lo exige en toda línea por BR-23. O sea:
    # una factura puede pasar el XSD oficial, pasar las reglas del propio
    # formato, y aun así no cumplir la norma que le exige el artículo 7.1.
    #
    # No lleva `SIN_MAPA` justamente por eso: el campo existe y se puede leer.
    # Que falte es un defecto del documento y no un hueco de la sintaxis, así
    # que BR-23 acusa, y acusa con razón.
    linea_unidad="./UnitOfMeasure",
    # BT-151, la categoría de IVA de la línea, tampoco existe. Ver la nota de
    # `desglose_categoria`, que es el mismo hueco un piso más arriba.
    tipo_metodo="./InvoiceHeader/Corrective/CorrectionMethod",
    linea_categoria="./TaxesOutputs/Tax/TaxTypeCode",
    linea_tipo="./TaxesOutputs/Tax/TaxRate",
    desglose="./TaxesOutputs/Tax",
    linea_fiscalidad_especial="./SpecialTaxableEvent/SpecialTaxableEventCode",
    desglose_base="./TaxableBase/TotalAmount",
    desglose_cuota="./TaxAmount/TotalAmount",
    # BT-118, y es el segundo hueco grande.
    #
    # EN 16931 pide una categoría de IVA de la lista UNCL5305: S (tipo
    # normal), Z (tipo cero), E (exento), AE (inversión del sujeto pasivo), K
    # (entrega intracomunitaria), G (exportación), O (no sujeto), L y M
    # (Canarias, Ceuta y Melilla). Facturae **no tiene ese concepto**: su
    # `TaxTypeCode` dice qué impuesto es —01 IVA, 02 IPSI, 03 IGIC…—, que es
    # una pregunta distinta.
    #
    # Esa deducción ya está escrita y contrastada —desde el 06-09-2026, en
    # `iva._derivar_categoria`—, así que aquí sí hay ruta: se lee el
    # `TaxTypeCode` y quien deduce es el módulo del IVA, con el tipo delante.
    # Lo que no se puede deducir se sigue diciendo en vez de inventarse: a
    # tipo cero, Facturae no distingue exenta de no sujeta ni de inversión
    # del sujeto pasivo, y no hay campo del que sacarlo.
    desglose_categoria="./TaxTypeCode",
    desglose_tipo="./TaxRate",
    # BT-120 y BT-121, el motivo de la exención y su código. Facturae no los
    # lleva en el bloque de impuestos. Sin categoría (arriba) tampoco habría a
    # qué atarlos, así que el hueco es coherente con el anterior.
    desglose_motivo=SIN_MAPA,
    desglose_motivo_codigo=SIN_MAPA,
    # Facturae separa en dos contenedores lo que UBL y CII meten en uno con un
    # booleano: `GeneralDiscounts/Discount` resta y `GeneralSurcharges/Charge`
    # suma. La unión coge los dos y `cargo_es_cargo` los distingue por el
    # nombre del propio elemento, que es lo único que los diferencia.
    cargos=(
        "./InvoiceTotals/GeneralDiscounts/Discount"
        "|./InvoiceTotals/GeneralSurcharges/Charge"
    ),
    cargo_es_cargo="name(.)",
    cargo_importe="./DiscountAmount|./ChargeAmount",
    # Un descuento o cargo general de Facturae no lleva IVA propio: se aplica
    # antes del desglose y afecta a la base entera.
    cargo_categoria=SIN_MAPA,
    cargo_tipo=SIN_MAPA,
    suma_lineas="./InvoiceTotals/TotalGrossAmount",
    base="./InvoiceTotals/TotalGrossAmountBeforeTaxes",
    # BT-112, y aquí `InvoiceTotal` **no siempre es** BT-112.
    #
    # EN 16931 dice que el total con impuestos es la base más el IVA, y ya.
    # Facturae, además, **resta las retenciones**: su `InvoiceTotal` es
    # `TotalGrossAmountBeforeTaxes + TotalTaxOutputs - TotalTaxesWithheld`. El
    # IRPF de una factura profesional no está en el modelo básico de EN 16931,
    # así que los dos importes se llaman igual y valen cosas distintas.
    #
    # Medido sobre las 13 Facturae reales que hay a mano: las 7 sin retención
    # cuadran, y las 6 con retención no. Una de ellas, al céntimo:
    # 1.163,52 + 279,24 = 1.442,76, menos 58,18 de retención, da los 1.384,58
    # que escribe el fichero. **Las seis son correctas** y con el mapa directo
    # salían las seis acusadas de incumplir BR-CO-15.
    #
    # El primer intento fue filtrar la ruta para que solo leyera `InvoiceTotal`
    # cuando la retención es cero. Quitaba las seis acusaciones de BR-CO-15 y
    # ponía seis de BR-14 en su sitio: la regla de campo obligatorio veía que
    # la ruta no encontraba nada y decía que **faltaba** el total. Estaba, y
    # con el importe correcto; lo que pasa es que no es el importe que la
    # norma pide.
    #
    # Así que el hueco es hueco y se declara como tal: **Facturae no tiene
    # ningún elemento que sea BT-112**. Tiene uno que coincide con BT-112
    # cuando no hay retención, que es otra cosa.
    #
    # No se pierde cobertura por esto. La cuenta que Facturae sí garantiza
    # —`InvoiceTotal = base + IVA - retenciones`, que es la fórmula escrita en
    # las anotaciones de su propio esquema— ya la comprueba `facturae.py` con
    # el código `FE-TOTAL`. Repetirla aquí en una versión peor no añadiría
    # nada; decir que no se ha comprobado, sí.
    con_impuestos=SIN_MAPA,
    a_pagar="./InvoiceTotals/TotalExecutableAmount",
    descuentos_total="./InvoiceTotals/TotalGeneralDiscounts",
    cargos_total="./InvoiceTotals/TotalGeneralSurcharges",
    anticipos="./InvoiceTotals/TotalPaymentsOnAccount",
    # BT-114, el redondeo, no tiene equivalente. Igual que en EDIFACT: no
    # leerlo equivale a que no lo haya, y eso es cierto en Facturae siempre.
    redondeo=SIN_MAPA,
    # BT-110, y es el mismo caso que BT-112 una vez más.
    #
    # `TotalTaxOutputs` suma **todo lo repercutido**, y en España eso incluye
    # el recargo de equivalencia, que no es IVA sino un impuesto propio.
    # BT-110 de EN 16931 es la suma de las cuotas de IVA por categoría (BT-117)
    # y nada más. Medido: en una de las muestras el total repercutido dice
    # 279,24 y las cuotas de IVA que se leen suman 244,34; los 34,90 que faltan
    # son un recargo. La factura es correcta y BR-CO-14 la acusaba.
    #
    # Se podría leer el recargo y sumarlo, pero entonces lo que se compara ya
    # no es BT-117 y la regla diría comprobar una cosa mientras comprueba otra.
    # Igual que con BT-112: la aritmética que Facturae sí garantiza la
    # comprueba `facturae.py`, que conoce el recargo y lo trata como lo que es.
    #
    # Es el mismo patrón tres veces, y merece decirse entero: **los totales de
    # Facturae son superconjuntos de los de EN 16931**, porque el formato
    # nacional carga impuestos que el modelo básico europeo no modela. No es
    # que Facturae esté mal escrito ni que la norma se quede corta: es que
    # miden cosas distintas y llamarlas igual sería el error.
    impuestos=SIN_MAPA,
    cuota_admite_la_unidad_justa=False,  # Facturae no tiene esquematrón europeo; se sigue el de UBL
    # `cargo_es_cargo` devuelve el nombre del elemento, no un booleano. En
    # minúscula porque quien compara pasa la marca por `.lower()` antes, igual
    # que la «c» de EDIFACT: con «Charge» no casaba ninguno y los cargos se
    # contaban como descuentos.
    marcas_de_cargo=("charge",),
)


# Nombres de familia sin importar `formato`, que no hace falta aquí.
SINTAXIS: dict[str, Sintaxis] = {
    "UBL": SINTAXIS_UBL,
    "CII": SINTAXIS_CII,
    "EDIFACT": SINTAXIS_EDIFACT,
    "Facturae": SINTAXIS_FACTURAE,
}


# --- Lectura ---------------------------------------------------------------


def texto(nodo, ruta: str, sintaxis: Sintaxis) -> str | None:
    encontrados = nodo.xpath(ruta, namespaces=sintaxis.espacios)
    # Una ruta que llama a una función de XPath devuelve **el valor suelto**,
    # no una lista de nodos. Hasta Facturae ninguna lo hacía y esta rama no
    # existía, así que `encontrados[0]` cogía la primera letra de la cadena:
    # `name(.)` daba «D» en vez de «Discount» y «C» en vez de «Charge», con lo
    # cual ningún cargo casaba con su marca y todos se restaban como
    # descuentos. Dos facturas correctas salían incumpliendo BR-CO-11.
    #
    # No falla ruidosamente, que es lo peor que tiene: devuelve una letra, que
    # es un texto perfectamente válido, y el error aparece tres reglas después
    # convertido en una acusación de aritmética.
    if isinstance(encontrados, str):
        return encontrados.strip() or None
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


# --- Cómo compara el esquematrón oficial ------------------------------------
#
# Durante meses todo lo de arriba se comparó con `cuadra`: un céntimo de
# margen, para todas las reglas por igual. Se decidió aquí, razonando que la
# norma redondea a dos decimales. Medido contra el esquematrón oficial y sus
# pruebas unitarias el 13-09-2026, la norma no hace eso en ninguna regla:
#
# - las sumas de la cabecera (BR-CO-10 a BR-CO-16) se redondean a dos
#   decimales y **tienen que coincidir exactas**: un céntimo de diferencia es
#   un error, y aquí salía limpio;
# - la cuota de cada entrada del desglose (BR-CO-17) se admite **hasta una
#   unidad** por encima o por debajo de base por tipo, porque el redondeo
#   línea a línea la aparta de ahí legítimamente; aquí se rechazaba a partir
#   de dos céntimos, que es rechazar lo que la norma acepta.
#
# `cuadra` sigue existiendo para lo que no es ninguna de esas reglas.


def redondear(valor: Decimal, decimales: int = 2) -> Decimal:
    """El `round()` de XPath, que es con el que redondea el esquematrón.

    Las mitades van hacia arriba —hacia más infinito—: `round(0.125)` a dos
    decimales es 0.13 y `round(-2.5)` es -2. No es el redondeo de `Decimal`,
    que por defecto lleva las mitades al par y deja 0.125 en 0.12: la regla
    discreparía de la oficial justo en el céntimo que decide.
    """
    escala = Decimal(1).scaleb(-decimales)
    return (valor / escala + Decimal("0.5")).to_integral_value(
        rounding=ROUND_FLOOR) * escala


def cuadra_exacto(calculado: Decimal, declarado: Decimal) -> bool:
    """BR-CO-10 a BR-CO-16: lo declarado es lo calculado redondeado, sin margen."""
    return declarado == redondear(calculado)


def a_menos_de_una_unidad(calculado: Decimal, declarado: Decimal) -> bool:
    """BR-CO-17: las dos cifras, en valor absoluto, se separan menos de una unidad.

    Es la forma del esquematrón para UBL, con desigualdad estricta. El de CII
    escribe `<=`, así que a una distancia de exactamente 1,00 los dos
    oficiales dicen cosas distintas; aquí se sigue el de UBL, que es de donde
    salen casi todas las pruebas unitarias.
    """
    return abs(redondear(abs(calculado)) - abs(declarado)) < 1


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


# --- El CIUS español, que no es UBL a secas ---------------------------------

# La solución pública no admite UBL: admite **su** UBL, con 51 campos que la
# EN 16931 no tiene —retenciones, suplidos, minoraciones, recargo de
# equivalencia, régimen de grupo de entidades, QR fiscal—. Y no los publica
# como esquema ni como esquematrón, sino como una columna de rutas dentro de
# una tabla en PDF, que es lo que `validador/cius_es.py` trae ya leído.
#
# Aquí no se copian esas rutas: se **derivan** de esa tabla al importar. Una
# tabla copiada a mano se queda vieja el día que salga otro anexo y no se
# entera nadie; una derivada cambia sola, y lo que se toca a mano es una lista
# corta de excepciones que dice, una a una, por qué se toca.
#
# Lo que hay que hacerles a las rutas del anexo para poder usarlas:
#
# 1. **Quitarles la raíz.** Vienen absolutas, `/in:Invoice/…`, y aquí todo es
#    relativo al documento como en el resto del módulo.
# 2. **Arreglarles la caja.** Cinco de las cincuenta escriben `/in:invoice/`
#    en minúscula. En XML eso no es un descuido de estilo: es otro elemento,
#    y no existe ninguno que se llame así.
# 3. **Deshacer el prefijo `aeat:`.** El anexo lo usa en 26 pasos y **no
#    declara en ninguna parte a qué namespace corresponde**, así que como
#    prefijo XPath no vale para nada. Esos pasos van por nombre local, que
#    encuentra el elemento esté donde esté. No es elegante y es honrado: lo
#    que identifica cada extensión no es su namespace sino el valor de su
#    `ext:UBLExtension/cbc:ID`, y ese sí está publicado.

NS_CIUS_ES = dict(
    NS_UBL,
    ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
)

_RAIZ_DEL_ANEXO = re.compile(r"^/in:[Ii]nvoice/")
_PASO_AEAT = re.compile(r"\baeat:([A-Za-z]+)")


# Las rutas que el anexo da mal, con el arreglo y el porqué de cada uno. Dos
# de cincuenta; lo demás va tal y como viene.
_ARREGLOS: dict[str, tuple[str, str, str]] = {
    "BT-ES-15": (
        "cac:ServiceProviderParty/cac:Party/cac:ThirdPartyInvoicing/cbc:ServiceTypeCode",
        "cac:ServiceProviderParty/cbc:ServiceTypeCode",
        "«ThirdPartyInvoicing» no existe en UBL: cero apariciones en los 18 "
        "ficheros de la 2.5 y otras tantas en la 2.1. Y el anexo se delata "
        "solo, porque la descripción del propio campo dice que "
        "«ThirdPartyInvoicing» es el **valor** que hay que escribir en el "
        "código. Alguien lo pegó dentro del camino. `ServiceTypeCode` cuelga "
        "directamente de `ServiceProviderParty`, no de su `Party`.",
    ),
    "BG-ES-1": (
        "aeat:Extension/aeat:Correction",
        "aeat:InvoiceExtension/aeat:Correction",
        "El grupo dice `aeat:Extension` y sus seis hijos dicen "
        "`aeat:InvoiceExtension`. Uno contra seis, y el resto del anexo sigue "
        "el mismo patrón —`aeat:CollectionInvoiceLineExtension` en BT-ES-30—, "
        "así que el raro es el padre.",
    ),
}


# Diecisiete campos se reparten seis rutas, y **el anexo dice cómo se
# distinguen**: no en la columna de la ruta, sino en la descripción. Lo que va
# aquí sale de ahí, y hay una prueba que comprueba que sigue saliendo de ahí.
#
# Sin esto, `POR_ID` devolvería la misma ruta para «identificación del cargo
# en nombre de un tercero» y para «identificación de retención», que son dos
# cosas que no se parecen en nada.
_SUPL = "urn:aeat:names:specification:ubl:schema:SUPL"
_MINO = "urn:aeat:names:specification:ubl:schema:MINO"
_REEQ = "urn:aeat:names:specification:ubl:schema:REEQ"
_REGE = "urn:aeat:names:specification:ubl:schema:REGE"
_RETE = "urn:aeat:names:specification:ubl:schema:RETE"


# Cada entrada lleva tres cosas: qué trozo de la ruta se sustituye, por qué se
# sustituye, y **en qué campo del anexo está escrito el valor** que se mete en
# el predicado. Lo tercero es lo que impide que esto se convierta en opinión:
# hay una prueba que va a esa descripción y comprueba que el literal sigue
# ahí. Casi siempre es el campo mismo; en dos casos —BT-ES-17 y BT-ES-19, que
# son el «tipo de impuesto» del descuento y el del cargo— quien lo dice es su
# hermano, el indicador, y por eso hace falta apuntarlo.


def _linea_de(urn: str, dicho_en: str) -> tuple[str, str, str]:
    """La `CollectionInvoiceLine` que lleva un identificador concreto."""
    return (
        "cac:CollectionInvoiceLine",
        f"cac:CollectionInvoiceLine[cbc:ID='{urn}']",
        dicho_en,
    )


def _cargo(indicador: str, dicho_en: str, dentro: str = "") -> tuple[str, str, str]:
    """El `AllowanceCharge` que resta (false) o el que suma (true)."""
    return (
        f"{dentro}cac:AllowanceCharge",
        f"{dentro}cac:AllowanceCharge[cbc:ChargeIndicator='{indicador}']",
        dicho_en,
    )


def _sede(cual: str, dicho_en: str) -> tuple[str, str, str]:
    """Órgano, unidad y oficina se distinguen por su `schemeName`."""
    return ("cbc:ID", f"cbc:ID[@schemeName='{cual}']", dicho_en)


_DISTINTIVOS: dict[str, tuple[str, str, str]] = {
    # «Atributos obligatorios: usar schemeName="Organo"», dice el anexo.
    "BT-ES-9": _sede("Organo", "BT-ES-9"),
    "BT-ES-10": _sede("Unidad", "BT-ES-10"),
    "BT-ES-11": _sede("Oficina", "BT-ES-11"),
    # «Valor obligatorio: usar "false"» / «"true"».
    "BT-ES-16": _cargo("false", "BT-ES-16"),
    "BT-ES-17": _cargo("false", "BT-ES-16"),
    "BT-ES-18": _cargo("true", "BT-ES-18"),
    "BT-ES-19": _cargo("true", "BT-ES-18"),
    "BT-ES-40": _cargo("false", "BT-ES-40", "cac:InvoiceLine/"),
    "BT-ES-41": _cargo("true", "BT-ES-41", "cac:InvoiceLine/"),
    # «Código obligatorio, usar "urn:aeat:…:SUPL"», y así los cinco.
    "BT-ES-20": _linea_de(_SUPL, "BT-ES-20"),
    "BT-ES-21": _linea_de(_MINO, "BT-ES-21"),
    "BT-ES-27": _linea_de(_REEQ, "BT-ES-27"),
    "BT-ES-31": _linea_de(_REGE, "BT-ES-31"),
    "BT-ES-32": _linea_de(_RETE, "BT-ES-32"),
}


@dataclass(frozen=True)
class RutaEs:
    """Dónde vive un campo español, y qué se le ha tocado a la del anexo."""

    id: str
    termino: str
    ruta: str  # relativa al documento; `SIN_MAPA` si el anexo no la da
    anexo: str  # tal y como la escribe el anexo, para poder comparar
    porque: str = ""  # por qué difiere, si difiere

    @property
    def tocada(self) -> bool:
        return bool(self.porque)


def _normalizar(ruta: str, identificador: str) -> tuple[str, str]:
    """La ruta del anexo convertida en una que se pueda evaluar."""
    if not ruta:
        return SIN_MAPA, ""
    porque = ""
    arreglo = _ARREGLOS.get(identificador)
    if arreglo and arreglo[0] in ruta:
        ruta = ruta.replace(arreglo[0], arreglo[1], 1)
        porque = arreglo[2]
    limpia = _RAIZ_DEL_ANEXO.sub("", ruta)
    # Los pasos `aeat:` se deshacen **antes** de meter el distintivo, y no
    # después. Cinco de los distintivos son URN de la propia Agencia
    # —`urn:aeat:names:specification:…`— y al revés el `aeat:names` de dentro
    # del literal también casaba con el patrón: la ruta salía con un
    # `local-name()` incrustado en mitad del URN y no encontraba nada nunca.
    limpia = _PASO_AEAT.sub(lambda m: f"*[local-name()='{m.group(1)}']", limpia)
    distintivo = _DISTINTIVOS.get(identificador)
    if distintivo and distintivo[0] in limpia:
        limpia = limpia.replace(distintivo[0], distintivo[1], 1)
    return "./" + limpia, porque


def _tabla_cius() -> tuple[RutaEs, ...]:
    filas = []
    for campo in cius_es.CAMPOS:
        if not campo.espanol:
            continue
        ruta, porque = _normalizar(campo.ruta, campo.id)
        filas.append(
            RutaEs(campo.id, campo.termino, ruta, campo.ruta, porque)
        )
    return tuple(filas)


RUTAS_CIUS_ES: tuple[RutaEs, ...] = _tabla_cius()

POR_ID: dict[str, tuple[RutaEs, ...]] = {}
for _r in RUTAS_CIUS_ES:
    POR_ID[_r.id] = POR_ID.get(_r.id, ()) + (_r,)

# Lo que sigue sin poder distinguirse después de todo lo de arriba, y por eso
# va dicho en voz alta en vez de disimulado. Son dos campos que comparten la
# misma ruta y a los que el anexo **no** da ningún distintivo: «situación del
# inmueble» y «tipo de impuesto nacional», los dos en el `ValueQualifier` de
# un `AdditionalItemProperty`. Lo que los separaría es el `cbc:Name` de esa
# propiedad, y el anexo no dice cuál.
AMBIGUAS: dict[str, tuple[str, ...]] = {}
for _r in RUTAS_CIUS_ES:
    if _r.ruta != SIN_MAPA:
        AMBIGUAS[_r.ruta] = AMBIGUAS.get(_r.ruta, ()) + (_r.id,)
AMBIGUAS = {r: ids for r, ids in AMBIGUAS.items() if len(ids) > 1}


def campos_es(nodo, identificador: str) -> list:
    """Los elementos que le tocan a un campo español, si están.

    Devuelve nodos y no texto a propósito: de varios de estos campos lo que
    hace falta es el atributo, o saber cuántos hay, y no su contenido.
    """
    encontrados = []
    for ruta in POR_ID.get(identificador, ()):
        if ruta.ruta == SIN_MAPA:
            continue
        encontrados.extend(nodo.xpath(ruta.ruta, namespaces=NS_CIUS_ES))
    return encontrados


def texto_es(nodo, identificador: str) -> str | None:
    """El contenido del primer elemento que le toca a un campo español."""
    for elemento in campos_es(nodo, identificador):
        crudo = elemento if isinstance(elemento, str) else (elemento.text or "")
        crudo = crudo.strip()
        if crudo:
            return crudo
    return None
