"""Los mensajes de error de la solución pública, tal y como los publica la AEAT.

Esto **no se escribe a mano**: lo genera `herramientas/errores_de_la_aeat.py`
leyendo el fichero de la AEAT. Si algo de aquí no cuadra con él, lo que está
mal es el lector, no esta tabla.

De dónde sale
-------------
Del «Listado de códigos de error» del Portal de Desarrolladores de la AEAT,
«SPFE - Validaciones y errores», publicado el 23-11-2026: los errores de
negocio. El portal avisa de que puede cambiar al acabar el periodo de pruebas.

    https://www.agenciatributaria.es/static_files/AEAT_Desarrolladores/EEDD/Facturacion-electronica/errores_negocio.properties
    SHA-256 374926f3137704835fac9900257e4b4b4b4ba1cc5fe9b8c3e9e146820c90a687

Qué trae: 316 reglas con 461 mensajes, y 52 mensajes generales.

Lo que hay que tener presente al usarlo
---------------------------------------
**La clave de `REGLAS` es el código** que la solución pública pone en el
estado de la factura (`SPFE-CORE-18`), y sus mensajes son las formas de
incumplir esa regla, en el orden del fichero.

**El mensaje que llega no es siempre uno de los de su regla.** La solución
pública manda también los de `GENERALES` con el código de una regla: en su
ejemplo del validador previo, `SPFE-IDEN-02` llega con «El NIF tiene un
formato erróneo», que es general. Cuándo usa cada uno no lo dice el fichero.

**Los `%s` son huecos** que el programa de la AEAT rellena con el valor del
campo, y se copian tal cual, como las erratas.
"""

PUBLICADA = "23-11-2026"

REGLAS = {
    "BR-01": (
        "La factura debe tener un identificador de especificación (%s).",
    ),
    "BR-02": (
        "La factura debe tener un número de factura (%s).",
    ),
    "BR-03": (
        "La factura debe tener una fecha de expedición de la factura (%s).",
    ),
    "BR-04": (
        "La factura debe tener un código del tipo de factura (%s).",
    ),
    "BR-05": (
        "La factura debe tener un código de la divisa de la factura (%s).",
    ),
    "BR-06": (
        "La factura debe contener el nombre del Vendedor (%s).",
    ),
    "BR-07": (
        "La factura debe contener el nombre del Comprador (%s).",
    ),
    "BR-08": (
        "La factura debe contener la dirección postal del Vendedor (%s).",
    ),
    "BR-09": (
        "La dirección postal del Vendedor (%s) debe contener el código de país del Vendedor (%s).",
    ),
    "BR-10": (
        "La factura debe contener la dirección postal del Comprador (%s).",
    ),
    "BR-11": (
        "La dirección postal del Comprador debe contener el código de país del Comprador (BT-55) (%s).",
    ),
    "BR-12": (
        "La factura debe tener la suma del importe neto a nivel de línea de la factura (%s).",
    ),
    "BR-13": (
        "La factura debe tener el importe total de factura, IVA excluido (%s).",
    ),
    "BR-14": (
        "La factura debe tener el importe total de factura, IVA incluido (%s).",
    ),
    "BR-15": (
        "La factura debe tener el importe total a pagar (%s).",
    ),
    "BR-16": (
        "La factura debe tener al menos una línea de factura (%s).",
    ),
    "BR-17": (
        "El nombre del Acreedor del pago (%s) debe ser incluido en la factura si dicho Acreedor del pago (%s) es distinto al Vendedor (%s).",
    ),
    "BR-18": (
        "El nombre del representante fiscal del Vendedor (%s) debe ser incluido en la factura si el Vendedor (%s) tiene un representante fiscal (%s).",
    ),
    "BR-19": (
        "La dirección postal del Representante fiscal del Vendedor (%s) debe ser incluido en la factura si el Vendedor (%s) tiene un representante fiscal (%s).",
    ),
    "BR-20": (
        "La dirección postal del representante fiscal del Vendedor (%s) debe contener el código país del representante fiscal (%s) si el Vendedor (%s) tiene un representante fiscal (%s).",
    ),
    "BR-21": (
        "Cada línea de la factura (%s) debe tener un identificador de línea de factura (%s).",
    ),
    "BR-22": (
        "Cada línea de factura (%s) debe tener un Importe de Factura (BT-129) (%s).",
    ),
    "BR-23": (
        "Una línea de la factura (BG-25)(%s) debe tener un código de unidad de medida de la cantidad facturada (BT-130)(%s).",
    ),
    "BR-24": (
        "Cada línea de factura (BG-25)(%s) debe tener un importe neto a nivel de línea de factura (BT-131)(%s).",
    ),
    "BR-25": (
        "Cada línea de factura (BG-25)(%s) debe contener el nombre del artículo (BT-153)(%s).",
    ),
    "BR-26": (
        "Cada línea de factura (BG-25)(%s) debe contener el precio neto del artículo (BT-146)(%s).",
    ),
    "BR-27": (
        "El precio neto del artículo (BT-146)(%s) no debe ser negativo.",
    ),
    "BR-28": (
        "El precio bruto del artículo (BT-148)(%s) no debe ser negativo.",
    ),
    "BR-29": (
        "La fecha de fin del período (BT-74)(%s) debe ser posterior o igual a la fecha de inicio (BT-73)(%s)",
    ),
    "BR-30": (
        "La fecha de fin del período a nivel de línea (BT-135)(%s) debe ser posterior o igual a la fecha de inicio a nivel de línea (BT-134)(%s)",
    ),
    "BR-31": (
        "Cada minoración a nivel de documento (BG-20)(%s) debe tener un importe de la minoración a nivel de documento (BT-92)(%s).",
    ),
    "BR-32": (
        "Cada minoración a nivel de documento (BG-20)(%s) debe tener un Código de categoría de IVA de la minoración a nivel de documento (BT-95)(%s).",
        "Cada minoración a nivel de documento (BG-20)(%s) debe tener un Código de impuesto de IVA de la minoración a nivel de documento (BT-95-1)(%s).",
    ),
    "BR-33": (
        "Cada minoración a nivel de documento (BG-20)(%s) debe tener una Razón de la minoración a nivel de documento (BT-97)(%s) o un Código de razón de la minoración a nivel de documento (BT-98)(%s).",
    ),
    "BR-36": (
        "Cada Cargo a nivel de documento (BG-21) debe tener un Importe de cargo a nivel de documento (BT-99).",
    ),
    "BR-37": (
        "Cada Cargo a nivel de documento (BG-21)(%s) debe tener un Código de categoría de IVA del cargo a nivel de documento (BT-102)(%s).",
        "Cada Cargo a nivel de documento (BG-21)(%s) debe tener un Código de impuesto de IVA del cargo a nivel de documento (BT-95-1)(%s).",
    ),
    "BR-38": (
        "Cada Cargo a nivel de documento (BG-21)(%s) debe tener una Razón del cargo a nivel de documento (BT-104)(%s) o un Código de razón del cargo a nivel de documento (BT-105)(%s).",
    ),
    "BR-41": (
        "Cada Minoración a nivel de línea (BG-27)(%s) debe tener un Importe de la minoración a nivel de línea (BT-136)(%s).",
    ),
    "BR-42": (
        "Cada Minoración a nivel de línea (BG-27)(%s) debe tener una Razón de la minoración a nivel de línea (BT-139)(%s) o un Código de razón de la minoración a nivel de línea (BT-140)(%s).",
    ),
    "BR-43": (
        "Cada Cargo a nivel de línea (BG-28)(%s) debe tener un Importe del cargo a nivel de línea (BT-141)(%s).",
    ),
    "BR-44": (
        "Cada Cargo a nivel de línea (BG-28)(%s) debe tener una Razón del cargo a nivel de línea (BT-144)(%s) o un Código de razón del cargo a nivel de línea (BT-145)(%s).",
    ),
    "BR-45": (
        "Cada Desglose del IVA (BG-23)(%s) debe tener una Base Imponible por categoría de IVA (BT-116)(%s).%s",
    ),
    "BR-46": (
        "Cada Desglose del IVA (BG-23)(%s) debe tener un Importe por categoría de IVA (BT-117)(%s) excepto para las las categorías de impuestos del Régimen de Margen.%s",
        "El Importe por categoría de IVA (BT-117) debe ser distinto de cero excepto para las las categorías de impuestos del Régimen de Margen. %s",
    ),
    "BR-47": (
        "Cada Desglose del IVA (BG-23)(%s) debe ser definido a través de un Código de categoría de IVA (BT-118)(%s).%s",
    ),
    "BR-48": (
        "Cada Desglose del IVA (BG-23)(%s) debe tener un Tipo Impositivo de categoría de IVA (BT-119)(%s), salvo cuando la factura no esté sujeta al IVA ('O').%s",
    ),
    "BR-49": (
        "Unas Instrucciones de pago (BG-16) deben especificar el Código del tipo de medio de pago (BT-81)(%s).",
    ),
    "BR-50": (
        "El Identificador de la cuenta de pago (BT-84)(%s) debe ser especificada si se ofrece información en la factura sobre Transferencia bancaria (BG-16)(%s).",
    ),
    "BR-51": (
        "De conformidad con los estándares de seguridad de pagos con tarjeta, una factura nunca debe incluir un número completo de cuenta principal de tarjeta (BT-87)(%s). Actualmente, el PCI Security Standards Council ha definido que los primeros 6 dígitos y los últimos 4 dígitos son el número máximo de dígitos que se pueden mostrar (BT-122)",
    ),
    "BR-52": (
        "Cada Documento complementario adicional (BG-24) debe contener una Referencia de documento complementario (%s) (BT-122).",
    ),
    "BR-53": (
        "Si el Código de divisa de cálculo del IVA se encuentra presente (BT-6)(%s), entonces debe incluir el Importe total, en la divisa de cálculo, de la cuota de IVA (BT-111)(%s).",
    ),
    "BR-54": (
        "Cada Característica del Artículo debe contener un Nombre de característica de atributo (BT-160) o un código de característica de atributo (BT-211) o ambos, y un Valor de característica de atributo (BT-161) (%s)",
    ),
    "BR-55": (
        "Cada Grupo de Referencia de las Factura Precedentes (BG-3) debe contener una referencia a la factura precedente (BT-25)(%s).",
        "El campo referencia a la factura precedente (BT-25)(%s) es obligatorio.",
    ),
    "BR-56": (
        "Cada Representante fiscal del Vendedor (BG-11)(%s) debe contener un Identificador IVA de representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-57": (
        "Cada Dirección de entrega (BG-15)(%s) debe contener un Código país de entrega (BT-80)(%s).",
        "Dirección de entrega (BG-15)(%s) es obligatorio",
    ),
    "BR-61": (
        "Si el valor de Código de tipo de medio de pago (BT-81) '%s' %s debe estar presente un Identificador de cuenta de pago (BT-84)(%s).",
    ),
    "BR-62": (
        "La dirección electrónica del Vendedor debe tener un Identificador de esquema (%s).",
    ),
    "BR-63": (
        "La dirección electrónica del Comprador debe tener un Identificador de esquema (%s).",
    ),
    "BR-64": (
        "El Identificador estándar del artículo (%s) debe tener un Identificador de esquema.",
    ),
    "BR-65": (
        "El Identificador de clasificación del artículo (%s) debe tener un identificador de esquema.",
    ),
    "BR-66": (
        "Si la factura tiene uno o más adjuntos, los detalles del adjunto deben especificarse en attached document.BT-125: EmbeddedDocumentBinaryObject DEBE tener @mimeCode y @filename. Contexto: %s",
    ),
    "BR-67": (
        "Si el importe neto de la línea de factura (BT-131) es negativo, la cantidad facturada (BT-129) debe ser negativa o la suma de las minoraciones de la línea de factura (BG-27) debe ser mayor que la suma de los cargos y los impuestos de la línea (BG-28) más el precio de la línea. Contexto: %s",
        "El campo BT-149 (%s) debe estar relleno y tener valor diferente a cero",
    ),
    "BR-68": (
        "El código de razón de exención del IVA '%s' tiene textos de razón inconsistentes. Contexto: %s | Esperado: '%s' | Encontrado: '%s'",
    ),
    "BR-69": (
        "El identificador del Vendedor (BT-29) (%s) debe tener un identificador de esquema (@schemeID) (%s)",
    ),
    "BR-70": (
        "El identificador de registro legal del Vendedor (BT-30)(%s) debe tener un identificador de esquema (@schemeID) %s",
    ),
    "BR-71": (
        "El identificador del Comprador (BT-46) debe tener un identificador de esquema (@schemeID). Contexto: %s",
    ),
    "BR-72": (
        "El identificador de registro legal del Comprador (BT-47) debe tener un identificador de esquema (@schemeID). Contexto: %s",
    ),
    "BR-73": (
        "El identificador del Acreedor (BT-60) debe tener un identificador de esquema (@schemeID). Contexto: %s",
    ),
    "BR-74": (
        "El identificador de registro legal del Acreedor (BT-61) debe tener un identificador de esquema (@schemeID). Contexto: %s",
    ),
    "BR-75": (
        "El identificador de ubicación de entrega (BT-71) debe tener un identificador de esquema (@schemeID). Contexto: %s",
    ),
    "BR-AE-01": (
        "Una factura que contiene una línea de factura (BG-25)(%s), una minoración a nivel de documento (BG-20)(%s) o una cuota o cargo a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-151, BT-95 o BT-102)(%s, %s o %s) es \"Inversión del Sujeto Pasivo\" debe contener en el desglose del IVA (BG-23)(%s) un código de categoría de IVA (BT-118)(%s) igual a \"Inversión del Sujeto Pasivo\": uno por cada motivo de exención (BT-120, BT-121, BT-173, BT-174, BT-175, BT-176, BT-194, BT-195)(%s,%s,%s,%s,%s,%s,%s,%s).",
    ),
    "BR-AE-02": (
        "Una factura que contiene una línea de factura (BG-25)(%s) en la que el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"Inversión del Sujeto Pasivo\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s) y el Identificador a efectos del IVA del Comprador (BT-48)(%s) y/o el identificador del registro legal del Comprador (BT-47)(%s).",
    ),
    "BR-AE-03": (
        "Una factura que contiene una minoración a nivel de documento (BG-20)(%s) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95)(%s) es \"Inversión del Sujeto Pasivo\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s) y el Identificador a efectos del IVA del Comprador (BT-48)(%s) y/o el identificador del registro legal del Comprador (BT-47)(%s).",
    ),
    "BR-AE-04": (
        "Una factura que contiene un cargo a nivel de documento (BG-21)(%s) donde el código de categoría de IVA del cargo a nivel de documento (BT-102)(%s) es \"Inversión del Sujeto Pasivo\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s) y el Identificador a efectos del IVA del Comprador (BT-48)(%s) y/o el identificador del registro legal del Comprador (BT-47)(%s).",
    ),
    "BR-AE-05": (
        "En una línea de factura (BG-25)(%s), cuando el código de categoría de IVA del artículo facturado (BT-151)(%s) es 'Inversión del Sujeto Pasivo', el tipo de IVA del artículo facturado (BT-152)(%s) deberá ser 0 (cero). Contexto: %s.",
    ),
    "BR-AE-06": (
        "En una deducción a nivel de documento (BG-20)(%s), cuando el código de categoría de IVA de la deducción a nivel de documento (BT-95)(%s) es 'Inversión del Sujeto Pasivo', el tipo de IVA de la deducción a nivel de documento (BT-96)(%s) deberá ser 0 (cero). Contexto: %s.",
    ),
    "BR-AE-07": (
        "En un cargo a nivel de documento (BG-21)(%s), cuando el código de categoría de IVA del cargo a nivel de documento (BT-102)(%s) es 'Inversión del Sujeto Pasivo', el tipo de IVA del cargo a nivel de documento (BT-103)(%s) deberá ser 0 (cero). Contexto: %s.",
    ),
    "BR-AE-08": (
        "En un desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Inversión del Sujeto Pasivo\", la base imponible del categoría de IVA (BT-116) debe ser igual a la suma de los importes netos de las líneas de factura (BT-131) menos la suma de los importes de las minoraciones a nivel de documento (BT-92) más la suma de los importes de los cargos a nivel de documento (BT-99) donde los códigos de categoría de IVA (BT-151, BT-95, BT-102) son \"Inversión del Sujeto Pasivo\".",
    ),
    "BR-AE-09": (
        "El importe del IVA por cada categoría de IVA (BT-117) en el desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Inversión del Sujeto Pasivo\" debe ser 0 (cero).",
    ),
    "BR-AE-10": (
        "Un desglose de IVA (BG-23)(%s) con código de categoría de IVA (BT-118)(%s) \"Inversión del Sujeto Pasivo\" debe tener un código de razón de exención del IVA (BT-121)(%s), que signifique \"Inversión del Sujeto Pasivo\" o el texto de razón de exención del IVA (BT-120)(%s) \"Inversión del Sujeto Pasivo\" (o el texto estándar equivalente en otro idioma).Contexto: %s",
    ),
    "BR-CO-03": (
        "La fecha valor del IVA (BT-7)(%s) y el código de la fecha valor IVA (BT-8)(%s) son mutuamente excluyentes.",
    ),
    "BR-CO-04": (
        "Cada línea de factura (BG-25) debe tener un código de categoría de IVA del artículo facturado (BT-151)(%s).",
        "Cada línea de factura (BG-25) debe tener información del IVA a nivel de línea (BT-30)(%s).",
    ),
    "BR-CO-05": (
        "El código de razón de la minoración a nivel de documento (BT-98) y la razón de la minoración a nivel de documento (BT-97) deben indicar el mismo tipo de minoración.",
    ),
    "BR-CO-06": (
        "El código de razón del cargo a nivel de documento (BT-105) y la razón del cargo a nivel de documento (BT-104) deben indicar el mismo tipo de cargo.",
    ),
    "BR-CO-07": (
        "El código de razón de la minoración a nivel de línea (BT-149) y la razón de la minoración a nivel de línea (BT-139) deben indicar el mismo tipo de motivo de la minoración.",
    ),
    "BR-CO-08": (
        "El código de razón del cargo a nivel de línea (BT-145) y la razón del cargo a nivel de línea (BT-139) deben indicar el mismo tipo de motivo del cargo.",
    ),
    "BR-CO-09": (
        "El identificador de IVA del vendedor (BT-31)(%s) debe tener un prefijo de acuerdo con el código ISO 3166-1 alfa-2 mediante el cual puede identificarse el país de emisión. No obstante, Grecia puede utilizar el prefijo EL. Identificador '%s' Prefijo encontrado '%s'",
        "El identificador de IVA del comprador (BT-48)(%s) debe tener un prefijo de acuerdo con el código ISO 3166-1 alfa-2 mediante el cual puede identificarse el país de emisión. No obstante, Grecia puede utilizar el prefijo EL. Identificador '%s' Prefijo encontrado '%s'",
        "El identificador de IVA del representante fiscal del vendedor (BT-63)(%s) debe tener un prefijo de acuerdo con el código ISO 3166-1 alfa-2 mediante el cual puede identificarse el país de emisión. No obstante, Grecia puede utilizar el prefijo EL. Identificador '%s' Prefijo encontrado '%s'",
    ),
    "BR-CO-10": (
        "La suma de los importes netos a nivel de línea (BT-106)(%s) debe ser igual al ∑ Importe neto a nivel de línea de factura (BT-131) (%s). %s vs %s.",
    ),
    "BR-CO-11": (
        "La suma de las minoraciones a nivel de documento (BT-107)(%s) debe ser igual al ∑ Importe de las minoraciones a nivel de documento (BT-92) (%s). %s vs %s.",
    ),
    "BR-CO-12": (
        "La suma de los cargos a nivel de documento (BT-108) (%s) debe ser igual al ∑ Importe de los Cargos a nivel de documento (BT-99) (%s). %s vs %s.",
    ),
    "BR-CO-13": (
        "El importe total de la factura, IVA excluido (BT-109) (%s) debe ser igual al ∑ Importe neto a nivel de línea (BT-131)(%s) – Suma de las minoraciones a nivel de documento (BT-107)(%s) + Suma de los cargos a nivel de documento (BT-108)(%s). %s vs %s.",
    ),
    "BR-CO-14": (
        "Cuota total del IVA de la factura (BT-110) (%s) debe ser igual al ∑ Importe de cuota por categoría de IVA (BT-117) (%s). %s vs %s.",
    ),
    "BR-CO-15": (
        "El Importe total de factura, IVA incluido (BT-112) debe ser igual al Importe total de la factura, IVA excluido (BT-109) + Cuota total del IVA de la factura (BT-110). Esperado: %s, Encontrado: %s.",
        "La Cuota total del IVA de la factura (BT-110)(%s) es obligatoria",
        "Debe haber un solo código de moneda de Cuota total del IVA de la factura (BT-110-1)(%s) con el código de la moneda de la factura (BT-5)(%s). El valor %s encontrado %s veces",
    ),
    "BR-CO-16": (
        "Importe a pagar (BT-115) = Importe total de factura, IVA incluido (BT-112) – Importe pagado (BT-113) + Importe del cargo cobrado en nombre de un tercero (BT-179) + Importe de redondeo (BT-114). Esperado: %s, Encontrado: %s.",
    ),
    "BR-CO-18": (
        "Una factura debe tener al menos un grupo de desglose de IVA (BG-23).",
        "La factura tiene un grupo de desglose de IVA (BG-23) duplicado. Cada combinación de Código de categoría de IVA (BT-151), Tipo impositivo de IVA (BT-152), Razón de exención (BT-120/BT-121) y código de bienes/servicios (BT-196, BT-213, BT-214). Clave dupicada: [%s].",
    ),
    "BR-CO-19": (
        "Si se utiliza el período de facturación (BG-14), la fecha de inicio del período de facturación (BT-73) o la fecha de fin del período de facturación (BT-74) deben estar completados, o ambos.",
    ),
    "BR-CO-20": (
        "Si se utiliza el período de la línea %s (BG-26)(%s), la fecha de inicio del período de la línea %s (BT-134)(%s) o la fecha de fin del período de la línea %s (BT-135)(%s) deben estar completados, o ambos.",
    ),
    "BR-CO-21": (
        "Cada minoración a nivel de documento (BG-20)(%s) debe contener una razón de la minoración a nivel de documento (BT-97)(%s) o un código de razón de la minoración a nivel de documento (BT-98)(%s), o ambas.",
    ),
    "BR-CO-22": (
        "Cada cargo o impuesto a nivel de documento (BG-21) debe contener una razón del cargo o impuesto a nivel de documento (BT-104) o un código de razón del cargo a nivel de documento (BT-105) o un código de impuesto no IVA a nivel de documento (BT-177), o ambas razón y código.",
    ),
    "BR-CO-23": (
        "Cada minoración a nivel de línea de factura (BG-27)(%s) debe contener una razón de la minoración a nivel de línea de factura (BT-139)(%s) o un código de razón de la minoración a nivel de línea de factura (BT-140)(%s), o ambas. En línea de factura (%s) en la minoracion (%s)",
    ),
    "BR-CO-24": (
        "Cada cargo a nivel de línea de factura (BG-28)(%s) debe contener una razón del cargo a nivel de línea de factura (BT-144)(%s) o un código de razón del cargo a nivel de línea de factura (BT-145)(%s), o ambas.",
    ),
    "BR-CO-25": (
        "En caso de que el importe a pagar (BT-115)(%s) sea positivo (%s), debe figurar la fecha de vencimiento del pago (BT-9)(%s) o los términos de pago (BT-20)(%s).",
    ),
    "BR-CO-26": (
        "A efectos de que el Comprador pueda identificar automáticamente al Vendedor, el identificador del Vendedor (BT-29)(%s), el número de inscripción registral del Vendedor (BT-30)(%s) y/o el identificador IVA del Vendedor (BT-31)(%s) deben estar presentes.",
    ),
    "BR-CO-28": (
        "Un pedido de compra puede ser referenciado a nivel de documento (BT-13) o a nivel de línea (BT-188) pero no ambos. Contexto: %s",
    ),
    "BR-CO-29": (
        "Una nota de envío puede ser referenciada a nivel de documento (BT-16) o a nivel de línea (BT-189) pero no ambos. Contexto: %s",
    ),
    "BR-CO-30": (
        "Una nota de recepción puede ser referenciada a nivel de documento (BT-15) o a nivel de línea (BT-191) pero no ambos. Contexto: %s",
    ),
    "BR-CO-31": (
        "La cantidad base de precio del artículo (BT-149) NO debe ser negativa. Contexto: %s",
    ),
    "BR-CO-32": (
        "El importe neto de la línea de factura (BT-131) no coincide con el cálculo esperado. Contexto: %s",
    ),
    "BR-CO-34": (
        "En los cargos e impuestos a nivel de documento (BG-21)(%s), debe usarse bien el código de razón del cargo a nivel de documento (BT-105)(%s) o el código de impuesto no IVA a nivel de documento (BT-177)(%s), no ambos.",
    ),
    "BR-CO-35": (
        "En los cargos e impuestos a nivel de línea de factura (BG-28)(%s), debe usarse bien el código de razón del cargo a nivel de línea de factura (BT-145)(%s) o el código de tipo de impuesto no IVA a nivel de línea de factura (BT-193)(%s), no ambos.",
    ),
    "BR-CO-36": (
        "Si se usan los dos campos a la vez, el importe de descuento declarado (BT-172)(%s) debe coincidir con el porcentaje (BT-171)(%s) multiplicado por BT-112(%s), dentro de un margen de tolerancia variable min(max(0.001xBT-172(%s), 0.01), 1) Esperado: %s, Diferencia: %s, Tolerancia: %s.",
    ),
    "BR-CO-38": (
        "Importe de la minoración a nivel de documento (BT-92)(%s) debe ser igual al porcentaje de la minoración a nivel de documento (BT-94)(%s) multiplicado por el importe base de la minoración a nivel de documento (BT-93)(%s), redondeado a (%s) decimal(es) (Decimales ISO 4217 para (%s)). Esperado %s, encontrado %s, diferencia %s, tolerancia %s",
    ),
    "BR-CO-39": (
        "Importe del cargo o impuesto a nivel de documento (BT-99)(%s) debe ser igual al importe base del cargo o impuesto a nivel de documento (BT-100)(%s) multiplicado por el porcentaje del cargo o impuesto a nivel de documento (BT-101)(%s), redondeado al número de decimales de la moneda (%s). Esperado %s, encontrado %s, diferencia %s, tolerancia %s",
    ),
    "BR-CO-40": (
        "INFORMACIÓN DE ENTREGA debe especificarse a nivel de cabecera (BG-13)(%s) o a nivel de línea de factura (BG-37)(%s) pero no ambos.",
    ),
    "BR-CO-45": (
        "La referencia de la nota de entrega, si está presente, debe especificarse a nivel de cabecera (BT-197)(%s) o a nivel de línea de factura (BT-198)(%s), no ambas.",
    ),
    "BR-CO-46": (
        "La referencia del pedido de venta, si está presente, debe especificarse a nivel de cabecera (BT-14)(%s) o a nivel de línea de factura (BT-200)(%s), no ambas.",
        "No se cumplen las precondiciones para BR-CO-46 (no existe Sales order reference en cabecera ni en líneas)",
    ),
    "BR-CO-47": (
        "La referencia de la factura previa, si existe, deberá especificarse a nivel de cabecera (BT-25)(%s) o a nivel de línea de factura (BT-217)(%s), pero no en ambos lugares.",
    ),
    "BR-CO-48": (
        "El importe total de IVA de la factura en la moneda de contabilidad del IVA (BT-111)(%s) debe ser igual al importe total de IVA de la factura (BT-110)(%s) multiplicado por el tipo de cambio de la moneda de contabilidad del IVA (BT-167)(%s).",
        "El importe total de IVA de la factura en la moneda de contabilidad del IVA (BT-111)(%s) debe ser igual al importe total de IVA de la factura (BT-110)(%s) multiplicado por el tipo de cambio de la moneda de contabilidad del IVA (BT-167)(%s). Esperado: %d, tolerancia: %d, Encontrado: %d",
    ),
    "BR-CO-49": (
        "El importe imponible de la categoría de IVA (BT-116)(%s) en la moneda de contabilidad del IVA debe ser igual al importe imponible de la categoría de IVA en la moneda de facturación multiplicado por BT-167(%s) (tipo de cambio). Esperado: %s ± Tolerancia: %s Encontrado: %s",
    ),
    "BR-CO-5": (
        "El código de razón de la minoración a nivel de documento (BT-98) y la razón de la minoración a nivel de documento (BT-97) deben indicar el mismo tipo de minoración. Contexto: %s",
    ),
    "BR-CO-6": (
        "La razón del cargo o impuesto a nivel de documento (BT-104) y el código de razón (BT-105 o BT-177), si está presente, no deben estar vacíos. Contexto: %s",
    ),
    "BR-CO-7": (
        "La razón de la minoración a nivel de línea de factura (BT-139) y el código de razón (BT-140), si está presente, no deben estar vacíos. Contexto: %s",
    ),
    "BR-CO-8": (
        "La razón del cargo a nivel de línea de factura (BT-144) y el código de razón (BT-145 o BT-193), si está presente, no deben estar vacíos. Contexto: %s",
    ),
    "BR-CO-50": (
        "El importe del impuesto por categoría de IVA (BT-117)(%s) en la moneda contable del IVA debe ser igual al importe del impuesto por categoría de IVA en la moneda de facturación multiplicado por BT-167(%s) (tipo de cambio). Esperado: (%s) ± Tolerancia: (%s), Encontrado: (%s)",
    ),
    "BR-CO-51": (
        "La unidad de medida de la cantidad facturada (BT-130)(%s) es obligatoria cuando está presente la unidad de medida de la cantidad base del precio del artículo (BT-150)(%s). Línea: %s",
        "La unidad de medida de la cantidad base del precio del artículo (BT-150)(%s) debe ser la misma que la unidad de medida de la cantidad facturada (BT-130)(%s). Línea: %s",
    ),
    "BR-E-01": (
        "Una factura que contiene una línea de factura (BG-25)(%s), una minoración a nivel de documento (BG-20)(%s) o una cuota o cargo a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-151, BT-95 o BT-102)(%s, %s o %s) es \"Exento\" debe contener en el desglose del IVA (BG-23)(%s) al menos un código de categoría de IVA (BT-118)(%s) igual a \"Exento\": uno por cada motivo de exención (BT-120, BT-121, BT-173, BT-174, BT-175, BT-176, BT-194, BT-195)(%s,%s,%s,%s,%s,%s,%s,%s).",
    ),
    "BR-E-02": (
        "Una factura que contiene una línea de factura (BG-25)(%s) en la que el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"Exento de IVA\" debe contener el identificador a efectos del IVA del Vendedor (BT-31)(%s), el identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-E-03": (
        "Una factura que contiene una minoración a nivel de documento (BG-20) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95) es \"Exento de IVA\" debe contener el identificador a efectos del IVA del Vendedor (BT-31), el identificador fiscal del Vendedor (BT-32) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63).",
    ),
    "BR-E-04": (
        "Una factura que contiene un cargo a nivel de documento (BG-21)(%s) donde el código de categoría de IVA del cargo a nivel de documento (BT-102)(%s) es \"Exento de IVA\" debe contener el identificador a efectos del IVA del Vendedor (BT-31)(%s), el identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-E-05": (
        "En una línea de factura (BG-25)(%s) donde el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"Exento de IVA\", el tipo de IVA del artículo facturado (BT-152)(%s) debe ser 0 (cero). Contexto: %s",
    ),
    "BR-E-06": (
        "La deduccion a nivel de documento (BG-20)(%s) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95)(%s) es \"Exento de IVA\", el tipo de IVA de la minoración a nivel de documento (BT-96)(%s) debe ser 0 (cero).Contexto %s",
    ),
    "BR-E-07": (
        "En un cargo o impuesto a nivel de documento (BG-21) donde el código de categoría de IVA del cargo a nivel de documento (BT-102) es \"Exento de IVA\", el tipo de IVA del cargo a nivel de documento (BT-103) debe ser 0 (cero).",
    ),
    "BR-E-08": (
        "En un desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Exento de IVA\", la base imponible del categoría de IVA (BT-116) debe ser igual a la suma de los importes netos de las líneas de factura (BT-131) menos la suma de los importes de las minoraciones a nivel de documento (BT-92) más la suma de los importes de los cargos a nivel de documento (BT-99) donde el código de categoría de IVA (BT-151, BT-102, BT-95) es \"Exento de IVA\".",
    ),
    "BR-E-09": (
        "La cuota de IVA por cada categoría de IVA (BT-117) en el desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Exento de IVA\" debe ser igual a 0 (cero).",
    ),
    "BR-E-10": (
        "Un desglose de IVA (BG-23)(%s) con un código de categoría de IVA (BT-118)(%s) \"Exento de IVA\" debe tener un código de razón de exención del IVA (BT-121)(%s) o un texto de razón de exención del IVA (BT-120)(%s).",
    ),
    "BR-G-01": (
        "Una factura que contiene una línea de factura (BG-25)(%s), una minoración a nivel de documento (BG-20)(%s) o un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-151)(%s), (BT-95)(%s) o (BT-102)(%s) es \"Exportación fuera de la UE\" debe contener en el desglose del IVA (BG-23)(%s) exactamente un código de categoría de IVA (BT-118)(%s) igual a \"Exportación fuera de la UE\".",
    ),
    "BR-G-02": (
        "Una factura que contiene una línea de factura (BG-25)(%s) en la que el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"Exportación fuera de la UE\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s) o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-G-03": (
        "Una factura que contiene una minoración a nivel de documento (BG-20)(%s) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95)(%s) es \"Exportación fuera de la UE\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s) o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-G-04": (
        "Una factura que contiene un cargo a nivel de documento (BG-21)(%s) donde el código de categoría de IVA del cargo a nivel de documento (BT-102)(%s) es \"Exportación fuera de la UE\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s) o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-G-05": (
        "En una línea de factura (BG-25) donde el código de categoría de IVA del artículo facturado (BT-151) es \"Exportación fuera de la UE\" el tipo de IVA del artículo facturado (BT-152) debe ser 0 (cero).",
    ),
    "BR-G-06": (
        "En una minoración a nivel de documento (BG-20) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95) es \"Exportación fuera de la UE\" el tipo de IVA de la minoración a nivel de documento (BT-96) debe ser 0 (cero).",
    ),
    "BR-G-07": (
        "En un cargo o impuesto a nivel de documento (BG-21) donde el código de categoría de IVA del cargo a nivel de documento (BT-102) es \"Exportación fuera de la UE\" el tipo de IVA del cargo a nivel de documento (BT-103) debe ser 0 (cero).",
    ),
    "BR-G-08": (
        "En un desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Exportación fuera de la UE\", la base imponible del categoría de IVA (BT-116) debe ser igual a la suma de los importes netos de las líneas de factura (BT-131) menos la suma de los importes de las minoraciones a nivel de documento (BT-92) más la suma de los importes de los cargos a nivel de documento (BT-99) donde los códigos de categoría de IVA (BT-151, BT-95, BT-102) son \"Exportación fuera de la UE\".",
    ),
    "BR-G-09": (
        "El importe del IVA por cada categoría de IVA (BT-117) en el desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Exportación fuera de la UE\" debe ser 0 (cero).",
    ),
    "BR-G-10": (
        "Un desglose de IVA (BG-23) con un código de categoría de IVA (BT-118) \"Exportación fuera de la UE\" debe tener un código de razón de exención del IVA (BT-121), que signifique \"Exportación fuera de la UE\" o el texto de razón de exención del IVA (BT-120) \"Exportación fuera de la UE\" (o el texto estándar equivalente en otro idioma).",
    ),
    "BR-IC-01": (
        "Una factura que contiene una línea de factura (BG-25)(%s), una minoración a nivel de documento (BG-20)(%s) o un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-151)(%s), (BT-95)(%s) o (BT-102)(%s) es \"Suministro Intracomunitario\" debe contener en el desglose del IVA (BG-23)(%s) exactamente un código de categoría de IVA (BT-118)(%s) igual a \"Suministro Intracomunitario\".",
    ),
    "BR-IC-02": (
        "Una factura que contiene una línea de factura (BG-25)(%s) en la que el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"Suministro Intracomunitario\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s) o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s) y el Identificador a efectos del IVA del Comprador (BT-48)(%s).",
    ),
    "BR-IC-03": (
        "Una factura que contiene una minoración a nivel de documento (BG-20)(%s) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95)(%s) es \"Suministro Intracomunitario\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s) o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s) y el Identificador a efectos del IVA del Comprador (BT-48)(%s).",
    ),
    "BR-IC-04": (
        "Una factura que contiene un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA del cargo a nivel de documento (BT-102)(%s) es \"Suministro Intracomunitario\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s) o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s) y el Identificador a efectos del IVA del Comprador (BT-48)(%s).",
    ),
    "BR-IC-05": (
        "En una línea de factura (BG-25) donde el código de categoría de IVA del artículo facturado (BT-151) es \"Suministro Intracomunitario\" el tipo de IVA del artículo facturado (BT-152) debe ser 0 (cero).",
    ),
    "BR-IC-06": (
        "En una minoración a nivel de documento (BG-20) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95) es \"Suministro Intracomunitario\" el tipo de IVA de la minoración a nivel de documento (BT-96) debe ser 0 (cero).",
    ),
    "BR-IC-07": (
        "En un cargo o impuesto a nivel de documento (BG-21) donde el código de categoría de IVA del cargo a nivel de documento (BT-102) es \"Suministro Intracomunitario\" el tipo de IVA del cargo a nivel de documento (BT-103) debe ser 0 (cero).",
    ),
    "BR-IC-08": (
        "En un desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Suministro Intracomunitario\", la base imponible del categoría de IVA (BT-116) debe ser igual a la suma de los importes netos de las líneas de factura (BT-131) menos la suma de los importes de las minoraciones a nivel de documento (BT-92) más la suma de los importes de los cargos a nivel de documento (BT-99) donde los códigos de categoría de IVA (BT-151, BT-95, BT-102) son \"Suministro Intracomunitario\".",
    ),
    "BR-IC-09": (
        "El importe del IVA por cada categoría de IVA (BT-117) en el desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Suministro Intracomunitario\" debe ser 0 (cero).",
    ),
    "BR-IC-10": (
        "Un desglose de IVA (BG-23) con un código de categoría de IVA (BT-118) \"Suministro Intracomunitario\" debe tener un código de razón de exención del IVA (BT-121), que signifique \"Suministro Intracomunitario\" o el texto de razón de exención del IVA (BT-120) \"Suministro Intracomunitario\" (o el texto estándar equivalente en otro idioma).",
    ),
    "BR-IC-11": (
        "En una factura con un desglose de IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Suministro Intracomunitario\", la fecha efectiva de entrega (BT-72) o el período de facturación (BG-14) no debe estar en blanco.",
    ),
    "BR-IC-12": (
        "En una factura con un desglose de IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Suministro Intracomunitario\", el código de país de entrega (BT-80) no debe estar en blanco.",
    ),
    "BR-IG-01": (
        "Una factura que contiene una línea de factura (BG-25)(%s), una minoración a nivel de documento (BG-20)(%s) o un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-151)(%s), (BT-95)(%s) o (BT-102)(%s) es \"IGIC\" debe contener en el desglose del IVA (BG-23)(%s) al menos un código de categoría de IVA (BT-118)(%s) igual a \"IGIC\".",
    ),
    "BR-IG-02": (
        "Una factura que contiene una línea de factura (BG-25)(%s) donde el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"IGIC\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-IG-03": (
        "Una factura que contiene una minoración a nivel de documento (BG-20)(%s) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95)(%s) es \"IGIC\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-IG-04": (
        "Una factura que contiene un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA del cargo a nivel de documento (BT-102)(%s) es \"IGIC\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-IG-05": (
        "En una línea de factura (BG-25)(%s) donde el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"IGIC\" el tipo de IVA del artículo facturado (BT-152)(%s) debe ser 0 (cero) o mayor que cero. Contexto: %s",
    ),
    "BR-IG-06": (
        "La deducción a nivel de documento (BG-20)(%s) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95)(%s) es \"IGIC\" el tipo de IVA de la minoración a nivel de documento (BT-96)(%s) debe ser 0 (cero) o mayor que cero. Contexto %s",
    ),
    "BR-IG-07": (
        "En un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA del cargo a nivel de documento (BT-102)(%s) es \"IGIC\" el tipo de IVA del cargo a nivel de documento (BT-103)(%s) debe ser 0 (cero) o mayor que cero. Contexto %s",
    ),
    "BR-IG-08": (
        "Para cada valor diferente de tipo impositivo de categoría de IVA (BT-119) donde el código de categoría de IVA (BT-118) es \"IGIC\", la base imponible del categoría de IVA (BT-116) en un desglose del IVA (BG-23) debe ser igual a la suma de los importes netos de las líneas de factura (BT-131) más la suma de los importes de los cargos a nivel de documento (BT-99) menos la suma de los importes de las minoraciones a nivel de documento (BT-92) donde el código de categoría de IVA (BT-151, BT-102, BT-95) es \"IGIC\" y el tipo de IVA (BT-152, BT-103, BT-96) igual al tipo de categoría de IVA (BT-119).",
    ),
    "BR-IG-09": (
        "El importe del IVA por cada categoría de IVA (BT-117) en el desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"IGIC\" debe ser igual a la base imponible de la categoría de IVA (BT-116) multiplicada por el tipo de categoría de IVA (BT-119).",
    ),
    "BR-IP-01": (
        "Una factura que contiene una línea de factura (BG-25)(%s), una minoración a nivel de documento (BG-20)(%s) o un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-151)(%s), (BT-95)(%s) o (BT-102)(%s) es \"IPSI\" debe contener en el desglose del IVA (BG-23)(%s) al menos un código de categoría de IVA (BT-118)(%s) igual a \"IPSI\".",
    ),
    "BR-IP-02": (
        "Una factura que contiene una línea de factura (BG-25)(%s) en la que el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"IPSI\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-IP-03": (
        "Una factura que contiene una minoración a nivel de documento (BG-20)(%s) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95)(%s) es \"IPSI\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-IP-04": (
        "Una factura que contiene un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA del cargo a nivel de documento (BT-102)(%s) es \"IPSI\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-IP-05": (
        "En una línea de factura (BG-25)(%s) donde el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"IPSI\" el tipo de IVA del artículo facturado (BT-152)(%s) debe ser 0 (cero) o mayor que cero. Contexto: %s",
    ),
    "BR-IP-06": (
        "La deducción a nivel de documento (BG-20)(%s) donde el código de categoría de IVA de la minoración a nivel de documento (BT-95)(%s) es \"IPSI\" el tipo de IVA de la minoración a nivel de documento (BT-96)(%s) debe ser 0 (cero) o mayor que cero. Contexto: (%s)",
    ),
    "BR-IP-07": (
        "En un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA del cargo a nivel de documento (BT-102)(%s) es \"IPSI\" el tipo de IVA del cargo a nivel de documento (BT-103)(%s) debe ser 0 (cero) o mayor que cero. Contexto: %s",
    ),
    "BR-IP-08": (
        "Para cada valor diferente de tipo impositivo de categoría de IVA (BT-119) donde el código de categoría de IVA (BT-118) es \"IPSI\", la base imponible del categoría de IVA (BT-116) en un desglose del IVA (BG-23) debe ser igual a la suma de los importes netos de las líneas de factura (BT-131) más la suma de los importes de los cargos a nivel de documento (BT-99) menos la suma de los importes de las minoraciones a nivel de documento (BT-92) donde el código de categoría de IVA (BT-151, BT-102, BT-95) es \"IPSI\" y el tipo de IVA (BT-152, BT-103, BT-96) igual al tipo de categoría de IVA (BT-119).",
    ),
    "BR-IP-09": (
        "El importe del IVA por cada categoría de IVA (BT-117) en el desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"IPSI\" debe ser igual a la base imponible de la categoría de IVA (BT-116) multiplicada por el tipo de categoría de IVA (BT-119).",
    ),
    "BR-N-02": (
        "Una factura que contiene una línea de factura (BG-25) donde el código de categoría de IVA del artículo facturado (BT-151) es 'N', 'D', 'F', 'I' o 'J' debe contener el identificador de IVA del vendedor (BT-31), el identificador de registro fiscal del vendedor (BT-32) y/o el identificador de IVA del representante fiscal del vendedor (BT-63).",
    ),
    "BR-N-03": (
        "Una factura que contiene una bonificación a nivel de documento (BG-20) donde el código de categoría de IVA de la bonificación a nivel de documento (BT-95) es 'N', 'D', 'F', 'I' o 'J' debe contener el identificador de IVA del vendedor (BT-31), el identificador de registro fiscal del vendedor (BT-32) y/o el identificador de IVA del representante fiscal del vendedor (BT-63).",
    ),
    "BR-N-04": (
        "Una factura que contiene un cargo o impuesto a nivel de documento (BG-21) donde el código de categoría de IVA del cargo o impuesto a nivel de documento (BT-102) es 'N', 'D', 'F', 'I' o 'J' debe contener el identificador de IVA del vendedor (BT-31), el identificador de registro fiscal del vendedor (BT-32) y/o el identificador de IVA del representante fiscal del vendedor (BT-63).",
    ),
    "BR-O-01": (
        "Una factura que contiene una línea de factura (BG-25)(%s), una minoración a nivel de documento (BG-20)(%s) o una cuota o cargo a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-151, BT-95 o BT-102)((%s, %s o %s) es \"No sujeto a IVA\" debe contener un grupo de desglose del IVA (BG-23)(%s) con el código de categoría de IVA (BT-118)(%s), igual a \"No sujeto a IVA\": uno por cada motivo de exención (BT-173, BT-174, BT-175, BT-176, BT-194, BT-195)(%s,%s,%s,%s,%s,%s).",
    ),
    "BR-O-05": (
        "Una línea de factura (BG-25)(%s) en la que el código de categoría del IVA (BT-151)(%s) es 'No sujeto a IVA' no debe contener una tasa de IVA del elemento facturado (BT-152)(%s). Contexto: %s.",
    ),
    "BR-O-06": (
        "La deducción a nivel de documento (BG-20)(%s) en la que el código de categoría del IVA (BT-95)(%s) es 'No sujeto a IVA' no debe contener una tasa de IVA de deducción a nivel de documento (BT-96)(%s). Contexto: %s.",
    ),
    "BR-O-07": (
        "Un cargo a nivel de documento (BG-21)(%s) en el que el código de categoría del IVA (BT-102)(%s) es 'No sujeto a IVA' no debe contener una tasa de IVA de cargo a nivel de documento (BT-103)(%s). Contexto: %s.",
    ),
    "BR-O-08": (
        "En un desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"No sujeto a IVA\", la base imponible del categoría de IVA (BT-116) debe ser igual a la suma de los importes netos de las líneas de factura (BT-131) menos la suma de los importes de las minoraciones a nivel de documento (BT-92) más la suma de los importes de los cargos a nivel de documento (BT-99) donde los códigos de categoría de IVA (BT-151, BT-95, BT-102) son \"No sujeto a IVA\".",
    ),
    "BR-O-09": (
        "El importe del IVA por cada categoría de IVA (BT-117) en el desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"No sujeto a IVA\" debe ser 0 (cero).",
    ),
    "BR-O-10": (
        "El desglose del IVA para la categoría '%s' (%s) debe tener un código de motivo de exención del IVA (BT-121)(%s) o un texto de motivo de exención del IVA (BT-120)(%s) que indique 'No sujeto a IVA' (o el texto estándar equivalente en otro idioma). Contexto: %s",
    ),
    "BR-S-01": (
        "Una factura que contiene una línea de factura (BG-25)(%s), cargo o impuesto a nivel de documento (BG-20)(%s) o un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-151)(%s), (BT-95)(%s) o (BT-102)(%s) es \"Gravamen general\" debe contener en el desglose del IVA (BG-23)(%s) al menos un código de categoría de IVA (BT-118)(%s) igual a \"Gravamen general\".",
    ),
    "BR-S-02": (
        "Una factura que contiene una línea de factura (BG-25)(%s) en la que el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"Gravamen general\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-S-03": (
        "Una factura que contiene una minoración a nivel de documento (BG-20)(%s) donde el código de categoría de IVA (BT-95)(%s) es \"Gravamen general\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-S-04": (
        "Una factura que contiene un cargo o impuesto o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-102)(%s) es \"Gravamen general\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-S-05": (
        "En una línea de factura (BG-25)(%s) donde el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"Gravamen general\" el tipo de IVA del artículo facturado (BT-152)(%s) debe ser mayor que cero. Contexto: %s",
    ),
    "BR-S-06": (
        "La deducción a nivel de documento (BG-20)(%s) donde el código de categoría de IVA (BT-95)(%s) es \"Gravamen general\", el tipo de IVA de la minoración (BT-96)(%s) debe ser mayor que cero. Contexto %s",
    ),
    "BR-S-07": (
        "En un cargo o impuesto o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-102)(%s) es \"Gravamen general\", el tipo de IVA del cargo (BT-103)(%s) debe ser mayor que cero. Contexto: %s",
    ),
    "BR-S-08": (
        "Para cada valor diferente de tipo impositivo de categoría de IVA (BT-119) donde el código de categoría de IVA (BT-118) es \"Gravamen general\", la base imponible (BT-116) en un desglose del IVA (BG-23) debe ser igual a la suma de los importes netos de las líneas de factura (BT-131) más la suma de los importes de los cargos a nivel de documento (BT-99) menos la suma de los importes de las minoraciones a nivel de documento (BT-92) donde el código de categoría de IVA (BT-151, BT-102, BT-95) es \"Gravamen general\" y el tipo de IVA (BT-152, BT-103, BT-96) igual al tipo de categoría de IVA (BT-119).",
    ),
    "BR-S-09": (
        "El importe del IVA por cada categoría de IVA (BT-117) en el desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Gravamen general\" debe ser igual a la base imponible de la categoría de IVA (BT-116) multiplicada por el tipo de categoría de IVA (BT-119).",
    ),
    "BR-Z-01": (
        "Una factura que contiene una línea de factura (BG-25)(%s), cargo o impuesto a nivel de documento (BG-20)(%s) o un cargo a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-151)(%s), (BT-95)(%s) o (BT-102)(%s) es \"Gravamen Cero\" debe contener en el desglose del IVA (BG-23)(%s) al menos un código de categoría de IVA (BT-118)(%s) igual a \"Gravamen Cero\".",
    ),
    "BR-Z-02": (
        "Una factura que contiene una línea de factura donde el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"Gravamen Cero\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-Z-03": (
        "Una factura que contiene una minoración a nivel de documento (BG-20)(%s) donde el código de categoría de IVA de la minoración (BT-95)(%s) es \"Gravamen Cero\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-Z-04": (
        "Una factura que contiene un cargo o impuesto a nivel de documento (BG-21)(%s) donde el código de categoría de IVA del cargo (BT-102)(%s) es \"Gravamen Cero\" debe contener el Identificador a efectos del IVA del Vendedor (BT-31)(%s), el Identificador fiscal del Vendedor (BT-32)(%s) y/o el identificador a efectos del IVA del representante fiscal del Vendedor (BT-63)(%s).",
    ),
    "BR-Z-05": (
        "En una línea de factura (BG-25)(%s) donde el código de categoría de IVA del artículo facturado (BT-151)(%s) es \"Gravamen Cero\" el tipo de IVA del artículo facturado (BT-152)(%s) debe ser 0 (cero). Contexto: %s",
    ),
    "BR-Z-06": (
        "La deducción a nivel de documento (BG-20)(%s) donde el código de categoría de IVA (BT-95)(%s) es \"Gravamen Cero\", el tipo de IVA de la minoración (BT-96)(%s) debe ser 0 (cero). Contexto: %s",
    ),
    "BR-Z-07": (
        "En un cargo a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-102)(%s) es \"Gravamen Cero\", el tipo de IVA del cargo (BT-103)(%s) debe ser 0 (cero). Contexto %s",
        "En un cargo a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-102)(%s) es \"Gravamen Cero\", falta el tipo de IVA (BT-103)(%s) pero debe ser 0 (cero). Contexto %s",
        "En un cargo a nivel de documento (BG-21)(%s) donde el código de categoría de IVA (BT-102)(%s) es \"Gravamen Cero\", el tipo de IVA del cargo (BT-103)(%s) debe ser 0 (cero) pero es %s. Contexto %s",
    ),
    "BR-Z-08": (
        "En un desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Gravamen Cero\", la base imponible del categoría de IVA (BT-116) debe ser igual a la suma de los importes netos de las líneas de factura (BT-131) menos la suma de los importes de las minoraciones (BT-92) más la suma de los importes de los cargos (BT-99) donde el código de categoría de IVA (BT-151, BT-102, BT-95) es \"Gravamen Cero\".",
    ),
    "BR-Z-09": (
        "El importe del IVA por categoría (BT-117) en el desglose del IVA (BG-23) donde el código de categoría de IVA (BT-118) es \"Gravamen Cero\" debe ser igual a 0 (cero).",
    ),
    "BR-ES-01": (
        "La fecha de realización de las operaciones (BT-7), cuando se informe, debe ser distinta de la fecha de expedición de la factura (BT-2).",
    ),
    "BR-ES-02": (
        "La fecha efectiva de pago (BT-ES-2), cuando se informe, debe ser igual o anterior a la fecha de expedición de la factura (BT-2).",
    ),
    "BR-ES-03": (
        "La fecha efectiva de pago (BT-ES-2), cuando se informe la fecha de realización de las operaciones (BT-7), debe ser igual o posterior a esta última.",
    ),
    "BR-ES-04": (
        "Cuando se informen la fecha de realización de las operaciones (BT-7) y la fecha de vencimiento del pago (BT-9), esta última deberá ser igual o posterior a la fecha de realización de las operaciones.",
    ),
    "BR-ES-05": (
        "Cuando no se informe la fecha de realización de las operaciones (BT-7), la fecha de vencimiento del pago (BT-9), cuando se informe, deberá ser igual o posterior a la fecha de expedición de la factura (BT-2), salvo que el código de tipo de factura (BT-3) sea 384 o 471.",
    ),
    "BR-ES-06": (
        "El campo Tipo de proceso de negocio (BT-23) es obligatorio",
    ),
    "BR-ES-07": (
        "Si se ha cumplimentado BillingReference el identificador de la factura referenciada (BT-25) es obligatorio",
        "Si se ha cumplimentado BillingReference la fecha de expedición de la factura referenciada (BT-26) es obligatoria",
    ),
    "SPFE-ACTION-01": (
        "No existe factura sobre la que actuar",
    ),
    "SPFE-ACTION-02": (
        "No existe factura sobre la que actuar",
        "Acción no valida sobre la factura",
        "Acción %s no permitida para el servicio %s",
        "El estado %s ya fue aplicado anteriormente sobre esta factura",
        "No se puede aplicar el estado %s porque la factura ya está en el estado %s",
    ),
    "SPFE-ACTION-03": (
        "El campo EffectiveDate es obligatorio",
    ),
    "SPFE-ACTION-04": (
        "El campo DueDate es obligatorio",
    ),
    "SPFE-ACTION-05": (
        "El campo IssueDate del Documento es obligatorio",
    ),
    "SPFE-ACTION-06": (
        "El campo CompanyID del Documento es obligatorio",
    ),
    "SPFE-ACTION-07": (
        "El campo RegistrationName del Documento es obligatorio",
    ),
    "SPFE-ACTION-08": (
        "Motivo del rechazo es obligatorio y sus valores deben ser los de la Lista",
    ),
    "SPFE-ACTION-09": (
        "La fecha de pago/rechazo puede ser igual o posterior que la fecha de emisión de la factura hasta la fecha del sistema (fecha de comunicación del pago).",
        "No existe la fecha efectiva sobre la que actuar.",
        "La fecha de pago/rechazo no puede ser anterior a la fecha de emisión de la factura.",
        "La fecha de pago no puede ser posterior a la fecha actual del sistema.",
    ),
    "SPFE-CORE-01": (
        "La identificación del emisor es obligatoria",
    ),
    "SPFE-CORE-02": (
        "El nombre del emisor es obligatorio",
    ),
    "SPFE-CORE-03": (
        "La identificación del destinatario es obligatoria (BT-48)",
    ),
    "SPFE-CORE-04": (
        "El nombre del destinatario es obligatorio",
    ),
    "SPFE-CORE-05": (
        "Error en la identificación del tercero",
    ),
    "SPFE-CORE-06": (
        "Error en la identificación del destinatario",
    ),
    "SPFE-CORE-07": (
        "Error en la identificación del emisor",
    ),
    "SPFE-CORE-08": (
        "El campo CopyIndicator es obligatorio",
    ),
    "SPFE-CORE-09": (
        "El campo moneda es obligatorio",
        "El valor del campo moneda es incorrecto.",
    ),
    "SPFE-CORE-10": (
        "El campo Total importe bruto antes de impuestos (BT-109) es obligatorio",
    ),
    "SPFE-CORE-11": (
        "El campo Importe total de la factura es obligatorio",
    ),
    "SPFE-CORE-12": (
        "Si se han cumplimentado los datos de Tercero su identificación es obligatoria",
    ),
    "SPFE-CORE-13": (
        "Si se han cumplimentado los datos de Tercero su nombre es obligatorio",
    ),
    "SPFE-CORE-14": (
        "El valor del campo Código de la nota de factura (BT-21) no es válido",
        "Si viene relleno el grupo nota de la factura (BG-1), el campo Nota de la factura es obligatorio (BT-22)",
        "Si viene relleno el grupo nota de la factura (BG-1), solo se permite un campo Nota de la factura (BT-22)",
    ),
    "SPFE-CORE-15": (
        "Si se ha cumplimentado BillingReference el identificador de la factura referenciada (BT-25) es obligatorio",
    ),
    "SPFE-CORE-16": (
        "Si se ha cumplimentado BillingReference la fecha de expedición de la factura referenciada (BT-26) es obligatoria",
    ),
    "SPFE-CORE-17": (
        "Si se ha cumplimentado PaymentMeans (BG-16) solo se permite uno",
    ),
    "SPFE-CORE-18": (
        "Si se ha cumplimentado el campo código de tipo de medio de pago (BT-81) con valor '30' o '49' el identificador de la cuenta de pago (BT-84) es obligatorio",
        "Si se ha cumplimentado el campo código de tipo de medio de pago (BT-81) con valor diferente a '30' o '49' el identificador de la cuenta de pago (BT-84) debe estar vacío",
        "El valor del identificador de la cuenta de pago (BT-84) debe ser un IBAN válido",
        "El valor del atributo schemeID del ID está vacío o tiene un valor incorrecto",
    ),
    "SPFE-CORE-19": (
        "Si se ha cumplimentado AdditionalDocumentReference solo se permite uno de tipo QR",
        "El valor del atributo schemeAgencyID está vacío o tiene un valor incorrecto",
        "El campo url del QR es obligatorio",
        "El url del QR debe ser una URL válida",
        "Si el campo Descripción de QR está relleno solo puedo haber uno",
        "El valor del campo es incorrecto, debe ser una URL válida para la validación del QR de VERI*FACTU",
        "El valor del campo es incorrecto si la URL es de VERI*FACTU",
        "El valor del campo tiene un valor no permitido de los tipos de QR permitidos",
    ),
    "SPFE-CORE-20": (
        "El valor del atributo schemeName en los datos del comprador está vacío o tiene un valor incorrecto",
    ),
    "SPFE-CORE-21": (
        "El valor del correo electrónico del vendedor debe tener un valor válido",
    ),
    "SPFE-CORE-22": (
        "El valor del correo electrónico del comprador debe tener un valor válido",
    ),
    "SPFE-CORE-23": (
        "El valor del campo teléfono del vendedor debe ser un teléfono válido",
    ),
    "SPFE-CORE-24": (
        "El valor del campo teléfono del comprador debe ser un teléfono válido",
    ),
    "SPFE-CORE-25": (
        "El valor del campo Identificador de especificación está vacío o tiene un valor incorrecto.",
    ),
    "SPFE-CORE-26": (
        "El valor del campo Tipo de Proceso de negocio está vacío o tiene un valor incorrecto.",
    ),
    "SPFE-CORE-27": (
        "La página web del vendedor debe ser una URL válida",
    ),
    "SPFE-CORE-28": (
        "Los valores de los campos de identificación del vendedor deben ser iguales",
    ),
    "SPFE-CORE-29": (
        "Los valores de los campos de identificación del comprador deben ser iguales",
    ),
    "SPFE-CORE-30": (
        "Los valores de los campos de identificación del tercero deben ser iguales",
    ),
    "SPFE-CORE-31": (
        "El campo código de moneda de contabilización del IVA (BT-6) es obligatorio y con valor 'EUR' si código de moneda de la factura (BT-5) tiene un valor diferente a 'EUR'",
        "El valor del campo código de moneda de contabilización del IVA (BT-6) es incorrecto.",
    ),
    "SPFE-CORE-32": (
        "La página web del comprador debe ser una URL válida",
    ),
    "SPFE-CORE-33": (
        "El valor del campo identificación del contacto del vendedor debe ser igual a la identificación del vendedor",
    ),
    "SPFE-CORE-34": (
        "El valor del campo nombre del contacto del vendedor debe ser igual al nombre del vendedor",
    ),
    "SPFE-CORE-35": (
        "El valor del campo identificación del contacto del comprador debe ser igual a la identificación del comprador",
    ),
    "SPFE-CORE-36": (
        "El valor del campo nombre del contacto del comprador debe ser igual al nombre del comprador",
    ),
    "SPFE-CORE-37": (
        "No puede haber identificadores de línea de factura duplicados",
    ),
    "SPFE-CORE-38": (
        "El valor de la dirección del vendedor no puede estar vacío",
        "El valor del código del país del vendedor no puede estar vacío",
        "Cuando el país de la dirección postal del vendedor sea España (ES), los campos ciudad, código postal y provincia deben cumplimentarse obligatoriamente.",
    ),
    "SPFE-CORE-39": (
        "El valor de la dirección del comprador no puede estar vacío",
        "El valor del código del país del comprador no puede estar vacío",
        "Cuando el país de la dirección postal del comprador sea España (ES), los campos ciudad, código postal y provincia deben cumplimentarse obligatoriamente.",
    ),
    "SPFE-CORE-40": (
        "El valor de la dirección del tercero no puede estar vacío",
        "El valor del código del país del tercero no puede estar vacío",
        "Cuando el país de la dirección postal del tercero sea España (ES), los campos ciudad, código postal y provincia deben cumplimentarse obligatoriamente.",
    ),
    "SPFE-CORE-41": (
        "La dirección del vendedor (BG-5) no es válida",
        "Error en la validación de la dirección del vendedor (BG-5)",
    ),
    "SPFE-CORE-42": (
        "La dirección del comprador (BG-8) no es válida",
        "Error en la validación de la dirección del comprador (BG-8)",
    ),
    "SPFE-CORE-43": (
        "La dirección del tercero no es válida",
        "Error en la validación de la dirección del tercero",
    ),
    "SPFE-CORE-44": (
        "Si hay minoraciones en nombre de un tercero el campo Importe de la minoración es obligatorio",
        "El valor del atributo currencyID del importe de minoraciones en nombre de un tercero es incorrecto.",
        "Si hay minoraciones en nombre de un tercero el campo Descripción de la minoración es obligatorio",
    ),
    "SPFE-CORE-45": (
        "El valor del atributo currencyID de uno de los campos importe de recargo de equivalencia es incorrecto.",
        "Si hay recargo de equivalencia los campos son obligatorios",
        "Solo se permite un valor del campo TaxTotal para recargo de equivalencia",
        "El valor del campo Tipo de operación en Recargo de equivalencia no puede estar vacío o tiene un valor incorrecto",
        "El valor del campo Tipo de IVA en Recargo de equivalencia está vacío o tiene un valor incorrecto.",
        "El valor del campo Tipo de impuesto en Recargo de equivalencia está vacío o tiene un valor incorrecto",
    ),
    "SPFE-CORE-46": (
        "Solo se permite un de Grupo de Entidades",
        "El campo Importe de la contraprestación adicional es obligatorio para Grupo de Entidades",
        "El campo Base imponible de la operación es obligatorio para Grupo de Entidades",
        "El campo Descripción operaciones es obligatorio para Grupo de Entidades",
        "El valor del atributo currencyID en uno de los importes del grupo de entidades es incorrecto.",
    ),
    "SPFE-CORE-47": (
        "El valor del atributo currencyID de uno de los campos de retenciones es incorrecto.",
        "Los valores de los campos de retención aplicada no pueden estar vacíos o tienen un valor incorrecto",
        "Solo se permite un valor del campo TaxSubTotal para cada retención aplicada",
        "El campo TaxSubTotal en retención aplicada es obligatorio",
        "Si hay Retención Aplicada debe existir Retenciones",
        "El valor de la suma de las retenciones debe ser igual que al total de la retención",
        "Error en el cálculo del total de la retención (%s) se esperaba: %s y se ha encontrado: %s",
    ),
    "SPFE-CORE-48": (
        "El valor del atributo currencyID del campo Total Retenciones es incorrecto.",
        "El campo Total de las Retenciones es obligatorio",
        "Solo se permite un valor del campo Identificación de retención",
        "Si hay Retenciones debe existir Retención Aplicada",
        "Si hay Retenciones debe existir la suma de las retenciones aplicadas",
        "La suma de las retenciones no coincide con el valor del campo Total retención",
        "El campo Descripción de la retención es obligatorio",
    ),
    "SPFE-CORE-49": (
        "El valor del campo del importe del cargo en nombre de un tercero es obligatorio",
        "El valor del atributo currencyID del importe del cargo en nombre de un tercero es incorrecto.",
        "El valor del campo Descripción del cargo en nombre de un tercero es obligatorio",
    ),
    "SPFE-CORE-50": (
        "Solo se permite un valor de instrucciones de pago",
    ),
    "SPFE-CORE-51": (
        "Si la factura es rectificativa el valor del campo Tipo de factura rectificativa debe estar relleno y solo puedo hacer uno",
        "Si la factura es rectificativa el valor del campo Modalidad rectificativa debe estar relleno y solo puedo hacer uno",
        "Si la factura es rectificativa los campos de importes rectificados son obligatorios",
        "Si la factura es rectificativa el valor del campo Tipo de factura rectificativa no puede estar vacío o tiene un valor incorrecto",
        "Si la factura es rectificativa el valor del campo Descripción del Tipo de factura rectificativa no puede estar vacío",
        "Si la factura es rectificativa el valor del campo Modalidad de factura rectificativa no puede estar vacío o tiene un valor incorrecto",
        "Si la factura es rectificativa el valor del campo Descripción de la Modalidad de factura rectificativa no puede estar vacío",
        "Si la factura no es rectificativa el campo Tipo de factura rectificativa no puede estar relleno",
        "Si la factura no es rectificativa el campo Modalidad de factura rectificativa no puede estar relleno",
        "Si la factura es rectificativa solo puedo haber un valor del campo Descripción del Tipo de factura rectificativa",
        "Si la factura es rectificativa solo puedo haber un valor del campo Descripción de la Modalidad de factura rectificativa",
    ),
    "SPFE-CORE-52": (
        "Si la factura no es rectificativa no puede haber importes rectificados",
        "Si la factura es rectificativa por diferencias no puede haber importes rectificados",
        "Si la factura es rectificativa por sustitución el valor de los campos de importes rectificados son obligatorios y solo uno de cada tipo",
        "Si la factura es rectificativa por sustitución el importe rectificativo Base imponible es obligatorio y solo puede haber uno",
        "Si la factura es rectificativa por sustitución el importe rectificativo Cuota repercutida es obligatorio y solo puede haber uno",
        "Si la factura es rectificativa por sustitución el importe rectificativo Cuota recargo de equivalencia es obligatorio y solo puede haber uno",
        "El formato del importe rectificativo Base imponible es incorrecto",
        "El formato del importe rectificativo Cuota repercutida es incorrecto",
        "El formato del importe rectificativo Cuota recargo de equivalencia es incorrecto",
        "Si la factura es rectificativa por sustitución el importe rectificativo de tipo Base imponible no puede ser igual a su base (BT-106)",
    ),
    "SPFE-CORE-53": (
        "Solo puede haber un valor de periodo de la factura recapitulativa (BG-14)(%s)",
    ),
    "SPFE-CORE-54": (
        "Solo puede haber una descripción de las condiciones de pago (BT-20)(%s) por cada condición de pago (BG-33)(%s)",
    ),
    "SPFE-CORE-55": (
        "El valor del atributo currencyID de uno de los campos importe de Impuestos y tasas es incorrecto.",
        "Si hay Impuestos y tasas los campos son obligatorios",
        "Solo se permite un valor del campo TaxTotal para Impuestos y tasas",
        "El valor del campo Tipo de operación en Impuestos y tasas no puede estar vacío o tiene un valor incorrecto",
        "El valor del campo Tipo de IVA en Impuestos y tasas está vacío o tiene un valor incorrecto.",
        "El valor del campo Tipo de impuesto en Impuestos y tasas está vacío o tiene un valor incorrecto",
    ),
    "SPFE-CORE-56": (
        "No se permiten archivos adjuntos dentro de la factura",
    ),
    "SPFE-CORE-57": (
        "El campo número de referencia de la autorización concedida es obligatorio",
        "Si el campo Descripción de documento justificativo de autorización facturación está relleno solo puedo haber uno",
    ),
    "SPFE-CORE-58": (
        "El id del a factura no esta dentro del rango de caracteres permitidos",
    ),
    "SPFE-CORE-59": (
        "Cada minoracion a nivel de documento (BG-20) debe tener una Razón de la minoración a nivel de documento (BT-97)",
        "Cada minoracion a nivel de documento (BG-20) solo puede tener una Razón de la minoración a nivel de documento (BT-97)",
        "La Razón de la minoración a nivel de documento (BT-97) tiene un valor inválido",
    ),
    "SPFE-CORE-60": (
        "Cada cargo a nivel de documento (BG-21) debe tener una Razón del cargo a nivel de documento (BT-104)",
        "Cada cargo a nivel de documento (BG-21) solo puede tener una Razón del cargo a nivel de documento (BT-104)",
        "La Razón Razón de cargo a nivel de documento (BT-104) tiene un valor inválido",
    ),
    "SPFE-CORE-61": (
        "Solo puede haber un valor del grupo pago anticipado (%s)",
    ),
    "SPFE-CORE-62": (
        "El localizador proporcionado no es válido",
    ),
    "SPFE-CORE-63": (
        "El valor del campo identificación del contacto del tercero debe ser igual a la identificación del tercero",
    ),
    "SPFE-CORE-64": (
        "El valor del campo teléfono del tercero debe ser un teléfono válido",
    ),
    "SPFE-CORE-65": (
        "El valor del correo electrónico del tercero debe tener un valor válido",
    ),
    "SPFE-CORE-66": (
        "La página web del tercero debe ser una URL válida",
    ),
    "SPFE-CORE-67": (
        "El valor del campo nombre del contacto del tercero debe ser igual al nombre del tercero",
    ),
    "SPFE-IDEN-01": (
        "IdOtro no permitido en emisor",
    ),
    "SPFE-IDEN-02": (
        "Nif del Emisor no permitido",
    ),
    "SPFE-IDEN-03": (
        "Nif del Tercero no permitido",
    ),
    "SPFE-IDEN-04": (
        "IdOtro no permitido en destinatario de la factura",
    ),
    "SPFE-IDEN-05": (
        "Nif del Destinatario no permitido",
    ),
    "SPFE-IDEN-06": (
        "Nif del EndPoint no permitido",
        "El valor del atributo schemeID del EndPoint está vacío o tiene un valor incorrecto",
    ),
    "SPFE-IDEN-07": (
        "IdOtro no permitido en Tercero de la factura",
    ),
    "SPFE-IDEN-08": (
        "IdOtro no permitido en la factura a consultar/descargar",
    ),
    "SPFE-IDEN-09": (
        "Nif no permitido en la factura a consultar/descargar",
    ),
    "SPFE-IDEN-10": (
        "En la consulta por emisor, el emisor de la consulta y de la factura a consultar tienen que ser el mismo",
    ),
    "SPFE-IDEN-11": (
        "IdOtro no permitido en la identificacion en la consulta por filtro",
    ),
    "SPFE-IDEN-12": (
        "Nif en la consulta por filtro no permitido",
    ),
    "SPFE-REPR-01": (
        "Error al comprobar la representación",
        "No se existe la factura en el sistema",
        "No está autorizado para consultar la factura por su tipo de representación",
        "No está autorizado para realizar la consulta por su tipo de representación",
        "Acción desconocida",
    ),
    "SPFE-LIST-01": (
        "El valor del campo Código de tipo de factura es incorrecto.",
    ),
    "SPFE-LIST-02": (
        "El valor del campo Código de tipo de medios de pago está vacío o tiene un valor incorrecto.",
    ),
    "SPFE-LIST-03": (
        "El valor del campo código de país de la dirección del vendedor es incorrecto.",
    ),
    "SPFE-LIST-04": (
        "El valor del campo código de país de la dirección del tercero es incorrecto.",
    ),
    "SPFE-LIST-05": (
        "El valor del campo código de país de la dirección del comprador es incorrecto.",
    ),
    "SPFE-LIST-06": (
        "El valor del atributo currencyID de uno de los importes de los totales de la factura es incorrecto.",
    ),
    "SPFE-LIST-07": (
        "El valor del atributo currencyID del campo importe de minoración/cargo a nivel de documento (BT-92) es incorrecto",
    ),
    "SPFE-LIST-08": (
        "El valor del campo Tipo de IVA de la minoración/cargo a nivel de documento es incorrecto",
        "En Minoraciones o cargos a nivel de documento en Desglose del IVA el valor del código de exención no puede estar relleno si el código de categoría de IVA no tiene alguno de estos valores 'E', 'AE', 'O'",
        "El valor del campo Código de categoría de IVA de la minoración/cargo a nivel de documento no puede estar vacío o tiene un valor incorrecto",
        "El valor del campo Tipo de impuesto de la minoración/cargo a nivel de documento no puede estar vacío o tiene un valor incorrecto",
    ),
    "SPFE-LIST-09": (
        "El valor del atributo currencyID de un campo importe en el Desglose de IVA no puede estar vacío o tiene un valor incorrecto",
        "El valor del campo Tipo de IVA en Desglose de IVA está vacío o tiene un valor no válido",
        "En desglose del IVA el valor del Código de razón de exención no puede estar relleno si el código de categoría de IVA no tiene alguno de estos valores 'E', 'AE', 'O', 'D', 'F'",
        "El valor del campo Código de cuota tributaria por categoría de IVA en Desglose del IVA no puede estar vacío o tiene un valor incorrecto",
        "El valor del campo Tipo de impuesto en Desglose de IVA no puede estar vacío o tiene un valor incorrecto",
        "El valor del campo Código de razón de exención a nivel de documento no puede estar vacío o tiene un valor incorrecto",
    ),
    "SPFE-LIST-10": (
        "El valor del atributo unitCode no puede estar vacío o tiene un valor incorrecto",
        "El valor del atributo currencyID en alguno de los campos de importe de la línea de factura no puede estar vacío o tiene un valor incorrecto",
        "El valor del campo Nombre de Propiedad en la línea de factura tiene un valor no permitido",
        "Debe existir al menos un grupo de Clave de Régimen y no superar el número de grupos permitidos",
        "El valor de Clave de Régimen es incorrecto para ese tipo de Impuesto",
        "El valor del Código de razón de exención a nivel de línea no puede estar relleno si el código de categoría de IVA a nivel de línea no tiene alguno de estos valores 'E', 'AE', 'O', 'D', 'F'",
        "El valor del campo Código de razón de exención a nivel de línea no puede estar vacío o tiene un valor incorrecto",
        "El campo Cantidad facturada a nivel de línea de factura es obligatorio",
        "Solo puede haber un solo valor para Referencia Catastral",
        "Solo puede haber un solo valor del campo Razón de minoración/cargo de línea de factura",
        "El valor del campo es incorrecto para la situación del inmueble de la Referencia Catastral",
        "El campo es obligatorio para Referencia Catastral",
        "Error técnico al comprobar la Clave de Régimen",
        "No puede haber Clave de Régimen duplicadas",
        "Solo puede haber un solo valor del campo Nombre de artículo",
        "Solo puede haber un solo valor del grupo Información del IVA a nivel de línea de factura",
        "Solo puede haber un solo valor del campo Situación del inmueble de la Referencia Catastral",
        "El valor del campo Código de clave de régimen es obligatorio",
        "El valor del campo Tipo de impuesto nacional en clave de régimen es obligatorio",
        "El valor del campo Tipo de impuesto nacional en clave de régimen es incorrecto.",
        "El valor del campo Código de categoría de IVA del artículo facturado en la línea de factura es incorrecto",
        "El valor del campo Tipo impositivo de IVA del artículo facturado en la línea de factura es incorrecto",
        "El valor del campo Tipo de impuesto del artículo facturado en la línea de factura es incorrecto",
        "El campo Importe neto a nivel de línea de factura es obligatorio",
        "El campo Razón de minoración/cargo de línea de factura es obligatorio",
        "El campo Precio neto del artículo es obligatorio",
        "El campo Nombre de artículo es obligatorio",
        "El grupo Información del IVA a nivel de línea de factura es obligatorio",
        "El campo descripción es obligatorio si hay Información adicional sobre la regulación aplicable",
        "El grupo de categoria de impuesto en cargo de línea de factura es obligatorio y solo puede haber uno",
        "El campo Código del tipo de impuesto incluido en cargo de línea de factura no puede estar vacío o tiene un valor incorrecto",
    ),
    "SPFE-LIST-11": (
        "El valor del campo Tipo de impuesto del vendedor no puede estar vacío o tiene un valor incorrecto",
    ),
    "SPFE-LIST-12": (
        "El valor del campo Tipo de impuesto del comprador no puede estar vacío o tiene un valor incorrecto",
    ),
    "SPFE-LIST-13": (
        "El valor del campo Tipo de impuesto del tercero no puede estar vacío o tiene un valor incorrecto",
    ),
    "SPFE-LIST-14": (
        "El valor del campo Tipología de tercero no puede estar vacío o tiene un valor incorrecto",
    ),
    "SPFE-LIST-15": (
        "El valor del campo identificador de CollectionInvoiceLine tiene un valor incorrecto",
    ),
    "SPFE-LIST-16": (
        "El valor del campo código de tipo de medios de pago no está permitido",
    ),
    "SPFE-LIST-17": (
        "El valor del campo Importe pagado de los totales de la factura solo puede ser cero o venir vacío",
    ),
    "SPFE-LIST-18": (
        "El valor del campo Referencia de documento justificativo tiene un valor incorrecto",
    ),
    "SPFE-PLAT-01": (
        "No está autorizado para realizar la consulta",
    ),
}

GENERALES = (
    ("ERROR_IDENTIFICACION_NIF", "El NIF no esta identificado"),
    ("ERROR_NIF_FORMATO_INCORRECTO", "El NIF tiene un formato erróneo"),
    ("ERROR_IDENTIF_NIF_NO_CENSADO", "El campo ID no contiene un NIF con formato correcto"),
    ("ERROR_TECNICO_IDENTIFICACION_ID_OTRO", "El campo ID no esta identificado"),
    ("MENSAJE_CAMPO_ID_TIPO_PERSONA_NO_VALIDA", "El valor del campo ID ha de ser el NIF de una persona física cuando el campo IDType tiene valor No Censado (07)."),
    ("MENSAJE_CAMPO_ID_INCORRECTO", "Valor del campo ID incorrecto"),
    ("MENSAJE_CAMPO_IDTYPE_INCORRECTO", "Valor del campo IDType incorrecto"),
    ("MENSAJE_CODIGO_PAIS_IDTYPE_NO_COMPATIBLES", "El valor del CodigoPais solo puede ser 'ES' cuando el IDType sea '07' o '03'. Si IDType es '07' el CodigoPais debe ser 'ES'"),
    ("MENSAJE_CAMPO_CODIGO_PAIS_INCORRECTO", "Valor del campo CodigoPais es incorrecto"),
    ("MENSAJE_CAMPO_CODIGO_PAIS_NECESARIO", "CodigoPais es obligatorio cuando IDType es distinto de 02"),
    ("MENSAJE_CODIGO_PAIS_ID_NOCOINCIDE", "El campo CodigoPais indicado no coincide con los dos primeros dígitos del identificador\""),
    ("MENSAJE_CAMPO_IDOTRO_TERCERO_DISTINTO_NOCENSADO", "El bloque Tercero no puede estar identificado cuando el campo IDType tiene valor No Censado (07)"),
    ("MENSAJE_ERROR_CAMPO_ID_XI", "Si FechaOperacion (FechaExpedicionFactura si no se informa FechaOperacion) es anterior a 01/01/2021 no se permite el valor 'XI' para Identificaciones NIF-IVA"),
    ("MENSAJE_ERROR_CAMPO_ID_GB", "Si FechaOperacion (FechaExpedicionFactura si no se informa FechaOperacion) es mayor o igual que 01/02/2021 no se permite el valor 'GB' para Identificaciones NIF-IVA"),
    ("MENSAJE_CODIGO_PAIS_INCORRECTO_ES", "El valor del campo identificación no debe empezar por 'ES'"),
    ("TITULAR_CERTIFICADO_NO_COLABORADOR_SOCIAL_Y_NO_APODERADO", "El titular del certificado debe ser ObligadoEmision, Colaborador Social, Apoderado o Sucesor."),
    ("MENSAJE_CODIGO_PAIS_INCORRECTO_VAT_ES", "El valor del campo identificación debe empezar por 'ES' si el valor del campo Tipo de impuesto en la identificación es 'VAT'"),
    ("MENSAJE_CODIGO_PAIS_INCORRECTO_LOC_ES", "El valor del campo identificación no debe empezar por 'ES' si el valor del campo Tipo de impuesto en la identificación es 'LOC'"),
    ("MENSAJE_TIPO_IMPUESTO_IDENTIFICACION_INCORRECTO", "El valor del campo Tipo de impuesto en la identificación no puede estar vacío o tiene un valor incorrecto"),
    ("MENSAJE_TIPO_IMPUESTO_VAT_IDEN_SCHEMEID", "Si el valor del campo Tipo de impuesto en la identificación es 'VAT', la identificación no puede tener el atributo schemeID"),
    ("MENSAJE_TIPO_IMPUESTO_LOC_IDEN_SCHEMEID", "Si el valor del campo Tipo de impuesto en la identificación es 'LOC', en la identificación el atributo schemeID no puede estar vacío o tiene un valor incorrecto"),
    ("ERROR_VALIDACION_CP", "Error en la validacion del código postal"),
    ("ERROR_CODIGO_POSTAL_NO_VALIDO", "El valor del campo código postal no es válido"),
    ("ERROR_PROVINCIA_NO_VALIDA", "El valor del campo provincia no es válido"),
    ("ERROR_CP_PROVINCIA_NO_VALIDA", "El valor del campo código postal no corresponde a ninguna provincia"),
    ("ERROR_CP_PROVINCIA_NO_CORRESPONDE", "El valor del campo código postal no corresponde al valor del campo provincia"),
    ("ERROR_CP_MUNICIPIO", "No se encuentran municipios para el valor del campo código postal"),
    ("ERROR_MUNICIPIO_VALIDO", "El valor del campo ciudad no se corresponde con el valor de código postal"),
    ("ERROR_VALIDAR_IVA", "Error al comprobar el IVA"),
    ("ERROR_VALIDAR_RECARGO_EQUIVALENCIA", "Error al comprobar el Recargo de Equivalencia"),
    ("ERROR_CODIGO_INVALIDO", "Código no válido: %s.Solo se permiten las acciones %s"),
    ("ERROR_CODIGO_NO_RECONOCIDO", "Código no válido o no reconocido: %s"),
    ("ERROR_CONFLICTO_CODIGOS", "\"Error: Múltiples conflictos para factura: %s; Fecha_Exp:%s; Nif %s . Ya se encontró: %s.La acción %s es contradictoria con alguna previa y además está duplicada. Todos los documentos se rechazan.\";"),
    ("ERROR_CONTRADICTORIO_CODIGOS", "Error: Acción contradictoria para facturaNum_serie %s; Fecha_Exp:%s; Nif %s. Ya se encontró %s, no se puede aplicar %s"),
    ("ERROR_CODIGO_DUPLICADO", "Error: Acción duplicada %s para factura: Num_serie %s; Fecha_Exp:%s; Nif %s.\" Todos los documentos se rechazan."),
    ("ERROR_CODIGO_NO_RECONOCIDO", "ninguna (servicio no reconocido: %s)"),
    ("ERROR_EN_LA_REGLA", "Error en la regla"),
    ("ERROR_EN_LA_LINEA", "Error en la línea %s"),
    ("MENSAJE_EN_LA_LINEA", "%s en la línea %s"),
    ("MENSAJE_DEBE_TENER_VALOR", "%s debe tener valor %s"),
    ("MENSAJE_NO_SE_CUMPLEN_PRECONDICIONES", "No se cumplen las precondiciones para la evaluación"),
    ("MENSAJE_EN_EL_NODO", "%s en el nodo %s"),
    ("ERROR_EN_EL_NODO", "Error en el nodo %s"),
    ("NO_EXISTE_FACTURA", "No existe factura sobre la que actuar"),
    ("BR-X-09_TAXAMOUNTMISSING", "Falta el campo TaxAmount en el desglose de IVA para la categoría '%s' (%s). Contexto: %s"),
    ("BR-X-09-TAXABLEAMOUNTMISSING", "Falta el campo TaxableAmount en el desglose de IVA para la categoría '%s'(%s). Contexto: %s"),
    ("BR-X-09-TAXRATEMISSING", "Falta la tasa de la categoría de IVA (Porcentaje) para calcular TaxAmount para la categoría '%s' (%s). Contexto: %s"),
    ("BR-X-09-TAXAMOUNTMUSTBEZERO", "Para la categoría '%s' (%s), el campo TaxAmount debe ser 0, pero es %s. Contexto: %s"),
    ("BR-X-09-TAXAMOUNTMISMATCH", "El campo TaxAmount para la categoría '%s' (%s) debe ser %s = %s × ( %s %/100), pero es %s. Contexto: %s"),
    ("BR-X-08-TAXAMOUNTMISMATCH", "La base imponible para la categoría %s (%s) debe ser %s, pero es %s. Fórmula: líneas de la categoría - deducciones de la categoría + recargos de la categoría. Contexto: %s"),
    ("BR-O-09-TAXAMOUNTMISSING", "Falta TaxAmount en el desglose del IVA para la categoría '%s' (%s); debe ser 0. Contexto: %s"),
    ("BR-X-ALLOWANCECHARGE-TAXCATEGORY", "Falta el bloque TaxCategory dentro de cargo o minoración a nivel de documento (%s)"),
)
