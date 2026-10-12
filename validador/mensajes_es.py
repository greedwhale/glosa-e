"""Los mensajes de la solución pública, tal y como los publica el BOE.

Esto **no se escribe a mano**: lo genera `herramientas/mensajes.py` leyendo el
XML del BOE. Si algo de aquí no cuadra con la orden, lo que está mal es el
extractor, no esta tabla.

De dónde sale
-------------
De la Orden HAC/1028/2026, BOE núm. 247 del 05-10-2026 (BOE-A-2026-20587), en vigor
desde el 06-10-2026: la tabla del mensaje de anulación del anexo I y las
ocho del anexo II, «Contenido y estructura de los campos del mensaje relativo
a los estados de pago, rechazo, cobro o impago de las facturas conforme al
modelo UBL», con su lista de códigos.

    https://www.boe.es/eli/es/o/2026/10/02/hac1028
    https://www.boe.es/diario_boe/xml.php?id=BOE-A-2026-20587
    SHA-256 14bb2dad06a5ce3278c395232db9185f18052b08602cae472a9b2af3ae9c354a

Qué trae: 9 mensajes, 59 filas y 1 lista de códigos.

Lo que hay que tener presente al usarlo
---------------------------------------
**La clave de cada mensaje es su `cbc:ResponseCode`**, que el BOE pone en la
cabecera de su tabla y no en una fila. Las filas no traen identificador: no
son términos de la norma europea.

**La columna de la ruta se copia tal cual**, con sus erratas: rutas que no
existen en UBL 2.5, dos rutas seguidas en una celda, un espacio donde va una
barra. Separarlas y arreglarlas lo hace `validador/mensajes.py`, a la vista y
con el porqué de cada arreglo.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Fila:
    """Una fila de la tabla de un mensaje. `nivel` es 1 para `+`, 3 para `+++`."""

    nivel: int
    cardinalidad: str
    termino: str
    descripcion: str
    tipo: str
    ruta: str

    @property
    def obligatorio(self) -> bool:
        return self.cardinalidad.startswith("1")

    @property
    def repetible(self) -> bool:
        return not self.cardinalidad.endswith("..1")


@dataclass(frozen=True)
class Mensaje:
    anexo: str
    titulo: str
    filas: tuple


@dataclass(frozen=True)
class Lista:
    titulo: str
    valores: dict


# Dónde pone cada mensaje su código. Es la misma en los nueve, y si un día no
# lo es, el extractor se niega.
RUTA_DEL_CODIGO = "ApplicationResponse/cac:DocumentResponse/cac:Response/cbc:ResponseCode"

MENSAJES = {
    "CANCELINVOICE": Mensaje("I",
        "FACTURA ELECTRÓNICA O COPIA FIEL– Mensaje de anulación", (
        Fila(1, "1..1", "Fecha de la anulación.",
             "Fecha en la que se produce la anulación de la factura.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:Response/cbc:EffectiveDate"),
        Fila(1, "1..n", "FACTURA ANULADA",
             "Datos de la factura que se anula.",
             "", "ApplicationResponse/cac:DocumentResponse/cac:Response/cac:DocumentReference"),
        Fila(2, "1..1", "Número de factura (ID)",
             "Serie y número de la factura anulada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:Response/cac:DocumentReference/cbc:ID"),
        Fila(2, "1..1", "Fecha de expedición de la factura",
             "Fecha de expedición de la factura anulada.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:Response/cac:DocumentReference/cbc:IssueDate"),
        Fila(2, "1..1", "DATOS DEL VENDEDOR",
             "Grupo de términos de negocio que proporcionan información sobre el vendedor identificado en la factura.",
             "", "ApplicationResponse/cac:DocumentResponse/cac:Response/cac:DocumentReference/cac:IssuerParty"),
        Fila(3, "1..1", "NIF del vendedor",
             "Número de identificación fiscal (NIF) del vendedor en la factura anulada.",
             "Identificador", "ApplicationResponse/cac:DocumentResponse/cac:Response/cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"),
        Fila(3, "1..1", "Nombre o razón social del vendedor",
             "Nombre y apellidos o razón social del vendedor.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:Response/cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme/cac:PartyLegalEntity/cbc:RegistrationName"),
    )),
    "PAYMENT": Mensaje("II",
        "COMUNICACIÓN DE PAGOS POR EL DESTINATARIO - Mensaje de alta", (
        Fila(1, "1..1", "Fecha de efecto",
             "Fecha de expedición del pago o situación del pago.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:Response/cbc:EffectiveDate"),
        Fila(1, "1..1", "Fecha de vencimiento del plazo de pago",
             "Fecha de vencimiento del plazo de pago, calculada de acuerdo con lo dispuesto en el artículo 4 de la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales o en la normativa específica que resulte de aplicación.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:Response/cac:Status/cbc:ReferenceDate ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cac:Condition/cbc:AttributeID=DueDate"),
        Fila(1, "0..1", "Fecha de recepción de las mercancías o de los servicios prestados",
             "Campos opcionales, a informar si, de acuerdo con el artículo 4 de la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales, esta información resulta relevante. Si no se informan, de acuerdo con lo dispuesto en la D.A. 7.ª del Real Decreto 238/2026, de 25 de marzo, por el que se desarrolla el sistema de facturación electrónica obligatoria entre empresarios y profesionales y por el que se modifica el Reglamento por el que se regulan las obligaciones de facturación, aprobado por el Real Decreto 1619/2012, de 30 de noviembre, se entenderá como fecha de inicio del plazo de pago la fecha de expedición de la factura.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cbc:ReferenceDate ApplicationResponse/cac:DocumentResponse cac:Response//cac:Status/cac:Condition/cbc:AttributeID=ShipmentDate"),
        Fila(1, "0..1", "Fecha de recepción de la factura",
             "Campos opcionales, a informar si, de acuerdo con el artículo 4 de la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales, esta información resulta relevante. Si no se informan, de acuerdo con lo dispuesto en la D.A. 7.ª del Real Decreto 238/2026, de 25 de marzo, por el que se desarrolla el sistema de facturación electrónica obligatoria entre empresarios y profesionales y por el que se modifica el Reglamento por el que se regulan las obligaciones de facturación, aprobado por el Real Decreto 1619/2012, de 30 de noviembre, se entenderá como fecha de inicio del plazo de pago la fecha de expedición de la factura.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cbc:ReferenceDate ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cac:Condition/cbc:AttributeID=ReceptionDate"),
        Fila(1, "0..1", "Factura rectificada",
             "Factura que ha sido previamente rectificada (y la confirmación no necesariamente será por el importe de la factura original)",
             "Indicador", "ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cbc:StatusReason=CorrectedInvoice"),
        Fila(1, "0..1", "Factura rectificativa",
             "Factura sin pago asociado (factura rectificativa negativa)",
             "Indicador", "ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cbc:StatusReason=NegativeAmountInvoice"),
        Fila(1, "1..1", "FACTURA INFORMADA",
             "Datos de la factura sobre la que se informa el pago",
             "", ""),
        Fila(2, "1..1", "Número de factura (ID)",
             "Serie y número que identifican la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:ID"),
        Fila(2, "1..1", "Fecha de expedición de la factura.",
             "Fecha de expedición de la factura informada.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:IssueDate"),
        Fila(2, "1..1", "NIF emisor",
             "Número de identificación fiscal (NIF) del vendedor en la factura informada.",
             "Identificador", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"),
        Fila(2, "1..1", "Nombre / Razón social emisor",
             "Nombre o razón social del vendedor en la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName"),
    )),
    "CANCELPAYMENT": Mensaje("II",
        "COMUNICACIÓN DE PAGOS POR EL DESTINATARIO - Mensaje de baja", (
        Fila(1, "1..1", "Número de factura (ID)",
             "Serie y número que identifican la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:ID"),
        Fila(1, "1..1", "Fecha de emisión factura",
             "Fecha de expedición de la factura informada.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:IssueDate"),
        Fila(1, "1..1", "NIF emisor",
             "Número de identificación fiscal (NIF) del vendedor en la factura informada.",
             "Identificador", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"),
        Fila(2, "1..1", "Nombre / Razón social emisor",
             "Nombre o razón social del vendedor en la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName"),
    )),
    "REJECTION": Mensaje("II",
        "COMUNICACIÓN DE RECHAZO POR EL DESTINATARIO- Mensaje de alta", (
        Fila(1, "1..1", "Fecha de rechazo",
             "Fecha de rechazo por el destinatario.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:Response/cbc:EffectiveDate"),
        Fila(1, "1..1", "Motivo de rechazo",
             "Motivo por el que se rechaza la factura. Admite dos valores posibles: - Rechazo comercial. - Rechazo por ser un consumo particular o no estar afectado a la actividad.",
             "Código (L1)", "ApplicationResponse/cac:DocumentResponse/cac:Response/cac:Status/cbc:ConditionCode"),
        Fila(1, "1..1", "FACTURA INFORMADA",
             "Datos de la factura sobre la que se informa el rechazo",
             "", ""),
        Fila(2, "1..1", "Número de factura (ID)",
             "Serie y número que identifican la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:ID"),
        Fila(2, "1..1", "Fecha de emisión factura",
             "Fecha de expedición de la factura informada.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:IssueDate"),
        Fila(2, "1..1", "NIF emisor",
             "Número de identificación fiscal (NIF) del vendedor en la factura informada.",
             "Identificador", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"),
        Fila(2, "1..1", "Nombre / Razón social emisor",
             "Nombre o razón social del vendedor en la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName"),
    )),
    "CANCELREJECTION": Mensaje("II",
        "COMUNICACIÓN DE RECHAZO POR EL DESTINATARIO - Mensaje de baja", (
        Fila(1, "1..1", "Número de factura (ID)",
             "Serie y número que identifican la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:ID"),
        Fila(1, "1..1", "Fecha de emisión factura",
             "Fecha de expedición de la factura informada.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:IssueDate"),
        Fila(1, "1..1", "NIF emisor",
             "Número de identificación fiscal (NIF) del vendedor en la factura informada.",
             "Identificador", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"),
        Fila(2, "1..1", "Nombre / Razón social emisor",
             "Nombre o razón social del vendedor en la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName"),
    )),
    "SETTLEMENT": Mensaje("II",
        "COMUNICACIÓN DE COBRO POR EL EMISOR - Mensaje de alta", (
        Fila(1, "1..1", "Fecha del cobro",
             "Fecha de cobro por el emisor.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:Response/cbc:EffectiveDate"),
        Fila(1, "0..1", "Fecha de vencimiento del pago",
             "Fecha de vencimiento del pago, calculada de acuerdo con lo dispuesto en el artículo 4 de la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales o en la normativa específica que resulte de aplicación.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cbc:ReferenceDate ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cac:Condition/cbc:AttributeID=DueDate"),
        Fila(1, "0..1", "Mecanismo de financiación",
             "Indicador de si el cobro se ha producido a través de un mecanismo de financiación concertado por el emisor.",
             "Indicador", "ApplicationResponse/cac:DocumentResponse/cac:Response/cac:Status/cac:Condition/cbc:AttributeID=FinancingArrangement"),
        Fila(1, "0..1", "Fecha de recepción de las mercancías o de los servicios prestados",
             "Campos opcionales, a informar si, de acuerdo con el artículo 4 de la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales, esta información resulta relevante. Si no se informan, de acuerdo con lo dispuesto en la D.A. 7.ª del Real Decreto 238/2026, de 25 de marzo, por el que se desarrolla el sistema de facturación electrónica obligatoria entre empresarios y profesionales y por el que se modifica el Reglamento por el que se regulan las obligaciones de facturación, aprobado por el Real Decreto 1619/2012, de 30 de noviembre, se entenderá como fecha de inicio del plazo de pago la fecha de expedición de la factura.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cbc:ReferenceDate ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cac:Condition/cbc:AttributeID=ShipmentDate"),
        Fila(1, "0..1", "Fecha de recepción de la factura",
             "Campos opcionales, a informar si, de acuerdo con el artículo 4 de la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales, esta información resulta relevante. Si no se informan, de acuerdo con lo dispuesto en la D.A. 7.ª del Real Decreto 238/2026, de 25 de marzo, por el que se desarrolla el sistema de facturación electrónica obligatoria entre empresarios y profesionales y por el que se modifica el Reglamento por el que se regulan las obligaciones de facturación, aprobado por el Real Decreto 1619/2012, de 30 de noviembre, se entenderá como fecha de inicio del plazo de pago la fecha de expedición de la factura.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cbc:ReferenceDate ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cac:Condition/cbc:AttributeID=ReceptionDate"),
        Fila(1, "1..1", "FACTURA INFORMADA",
             "Datos de la factura sobre la que se informa el pago",
             "", ""),
        Fila(2, "1..1", "Número de factura (ID)",
             "Serie y número que identifican la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:ID"),
        Fila(2, "1..1", "Fecha de emisión factura",
             "Fecha de expedición de la factura informada.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:IssueDate"),
        Fila(2, "1..1", "NIF emisor",
             "Número de identificación fiscal (NIF) del vendedor en la factura informada.",
             "Identificador", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"),
        Fila(2, "1..1", "Nombre / Razón social emisor",
             "Nombre o razón social del vendedor en la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName"),
    )),
    "CANCELSETTLEMENT": Mensaje("II",
        "COMUNICACIÓN DE COBRO POR EL EMISOR - Mensaje de baja", (
        Fila(1, "1..1", "Número de factura (ID)",
             "Serie y número que identifican la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:ID"),
        Fila(1, "1..1", "Fecha de emisión factura",
             "Fecha de expedición de la factura informada.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:IssueDate"),
        Fila(1, "1..1", "NIF emisor",
             "Número de identificación fiscal (NIF) del vendedor en la factura informada.",
             "Identificador", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"),
        Fila(2, "1..1", "Nombre / Razón social emisor",
             "Nombre o razón social del vendedor en la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName"),
    )),
    "DEFAULT": Mensaje("II",
        "COMUNICACIÓN DE IMPAGO POR EL EMISOR - Mensaje de alta", (
        Fila(1, "1..1", "Fecha de vencimiento del pago",
             "Fecha de vencimiento del pago, calculada de acuerdo con lo dispuesto en el artículo 4 de la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales o en la normativa específica que resulte de aplicación.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:Response/cbc:EffectiveDate"),
        Fila(1, "0..1", "Fecha de recepción de las mercancías o de los servicios prestados",
             "Campos opcionales, a informar si, de acuerdo con el artículo 4 de la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales, esta información resulta relevante. Si no se informan, de acuerdo con lo dispuesto en la D.A. 7.ª del Real Decreto 238/2026, de 25 de marzo, por el que se desarrolla el sistema de facturación electrónica obligatoria entre empresarios y profesionales y por el que se modifica el Reglamento por el que se regulan las obligaciones de facturación, aprobado por el Real Decreto 1619/2012, de 30 de noviembre, se entenderá como fecha de inicio del plazo de pago la fecha de expedición de la factura.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cbc:ReferenceDate ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cac:Condition/cbc:AttributeID=ShipmentDate"),
        Fila(1, "0..1", "Fecha de recepción de la factura",
             "Campos opcionales, a informar si, de acuerdo con el artículo 4 de la Ley 3/2004, de 29 de diciembre, por la que se establecen medidas de lucha contra la morosidad en las operaciones comerciales, esta información resulta relevante. Si no se informan, de acuerdo con lo dispuesto en la D.A. 7.ª del Real Decreto 238/2026, de 25 de marzo, por el que se desarrolla el sistema de facturación electrónica obligatoria entre empresarios y profesionales y por el que se modifica el Reglamento por el que se regulan las obligaciones de facturación, aprobado por el Real Decreto 1619/2012, de 30 de noviembre, se entenderá como fecha de inicio del plazo de pago la fecha de expedición de la factura.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cbc:ReferenceDate ApplicationResponse/cac:DocumentResponse/ cac:Response/cac:Status/cac:Condition/cbc:AttributeID=ReceptionDate"),
        Fila(1, "1..1", "FACTURA INFORMADA",
             "Datos de la factura sobre la que se informa el pago",
             "", ""),
        Fila(2, "1..1", "Número de factura (ID)",
             "Serie y número que identifican la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:ID"),
        Fila(2, "1..1", "Fecha de emisión factura",
             "Fecha de expedición de la factura informada.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:IssueDate"),
        Fila(2, "1..1", "NIF emisor",
             "Número de identificación fiscal (NIF) del vendedor en la factura informada.",
             "Identificador", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"),
        Fila(2, "1..1", "Nombre / Razón social emisor",
             "Nombre o razón social del vendedor en la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName"),
    )),
    "CANCELDEFAULT": Mensaje("II",
        "COMUNICACIÓN DE IMPAGO POR EL EMISOR - Mensaje de baja", (
        Fila(1, "1..1", "Número de factura (ID)",
             "Serie y número que identifican la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:ID"),
        Fila(1, "1..1", "Fecha de emisión factura",
             "Fecha de expedición de la factura informada.",
             "Fecha", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cbc:IssueDate"),
        Fila(1, "1..1", "NIF emisor",
             "Número de identificación fiscal (NIF) del vendedor en la factura informada.",
             "Identificador", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyTaxScheme/cbc:CompanyID"),
        Fila(2, "1..1", "Nombre / Razón social emisor",
             "Nombre o razón social del vendedor en la factura informada.",
             "Texto", "ApplicationResponse/cac:DocumentResponse/cac:DocumentReference/cac:IssuerParty/cac:PartyLegalEntity/cbc:RegistrationName"),
    )),
}

LISTAS = {
    "L1": Lista("Motivos de rechazo", {
        "01": "Rechazo comercial",
        "02": "Rechazo por ser un consumo particular o no estar afectado a la actividad.",
    }),
}
