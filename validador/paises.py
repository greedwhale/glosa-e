# -*- coding: utf-8 -*-
"""Del país como lo escribe Facturae al país como lo pide EN 16931.

Facturae escribe el país en **tres letras** —`ESP`, `FRA`, `PRT`— y la norma
europea lo pide en dos, que es lo que dicen BT-40 y BT-55. Son la misma
información en dos alfabetos, y sin esta tabla el dato no se puede comparar
con nada.

De dónde sale, y cómo se ha comprobado
--------------------------------------
La tabla se construyó el 06-09-2026 y se contrastó **por los dos extremos**,
que es lo que la hace fiable:

- Los 235 códigos de tres letras salen de `CountryType` en el propio
  `Facturaev3_2_2.xsd` oficial, que es la lista exacta de lo que una factura
  española puede escribir.
- Los 249 códigos de dos letras salen de
  `ISO_ISOTwo-letterCountryCode_SecondEdition2006.xsd`, la lista ISO 3166 que
  UN/CEFACT publica con los esquemas CII y que viaja en los artefactos de la
  Comisión Europea.

El emparejamiento se hizo con la tabla pública de `datasets/country-codes`,
que trae las dos columnas. **Esa no es la fuente oficial: es el puente.** Lo
que la hace de fiar es que sus dos extremos se comprobaron contra las listas
de arriba, y el resultado fue 233 parejas y **cero** discrepancias: ni un solo
código de dos letras que no estuviera en la lista de ISO.

Los dos que no tienen pareja, y por qué no se inventan
------------------------------------------------------
`ANT` y `ZAR`. Facturae los sigue admitiendo y la lista ISO vigente ya no los
tiene: son las Antillas Neerlandesas, disueltas en 2010, y Zaire, que en 1997
pasó a ser la República Democrática del Congo (`CD`). ISO los retira a su
parte 3, la de nombres de países usados en el pasado.

Se quedan fuera **a propósito**. Traducir `ZAR` a `CD` sería decidir que quien
escribió esa factura quería decir Congo, y eso no lo sabemos: puede ser un
sistema viejo que nunca actualizó su lista, o un dato copiado de un archivo de
1995. Cuando un país no se puede traducir se dice —`FE-PAIS-RETIRADO`— en vez
de elegir por el emisor.
"""
from __future__ import annotations

__all__ = ["ALPHA2", "alpha2"]

# alpha-3 de Facturae -> alpha-2 de ISO 3166-1. Escrita entera y no generada
# al vuelo: lo que se publica tiene que poder leerse y auditarse sin correr
# nada, y una lista de códigos de países no cambia de mes en mes.
ALPHA2: dict[str, str] = {
    "ABW": "AW",
    "AFG": "AF",
    "AGO": "AO",
    "AIA": "AI",
    "ALB": "AL",
    "AND": "AD",
    "ARE": "AE",
    "ARG": "AR",
    "ARM": "AM",
    "ASM": "AS",
    "ATG": "AG",
    "AUS": "AU",
    "AUT": "AT",
    "AZE": "AZ",
    "BDI": "BI",
    "BEL": "BE",
    "BEN": "BJ",
    "BFA": "BF",
    "BGD": "BD",
    "BGR": "BG",
    "BHR": "BH",
    "BHS": "BS",
    "BIH": "BA",
    "BLR": "BY",
    "BLZ": "BZ",
    "BMU": "BM",
    "BOL": "BO",
    "BRA": "BR",
    "BRB": "BB",
    "BRN": "BN",
    "BTN": "BT",
    "BWA": "BW",
    "CAF": "CF",
    "CAN": "CA",
    "CHE": "CH",
    "CHL": "CL",
    "CHN": "CN",
    "CIV": "CI",
    "CMR": "CM",
    "COD": "CD",
    "COG": "CG",
    "COK": "CK",
    "COL": "CO",
    "COM": "KM",
    "CPV": "CV",
    "CRI": "CR",
    "CUB": "CU",
    "CYM": "KY",
    "CYP": "CY",
    "CZE": "CZ",
    "DEU": "DE",
    "DJI": "DJ",
    "DMA": "DM",
    "DNK": "DK",
    "DOM": "DO",
    "DZA": "DZ",
    "ECU": "EC",
    "EGY": "EG",
    "ERI": "ER",
    "ESH": "EH",
    "ESP": "ES",
    "EST": "EE",
    "ETH": "ET",
    "FIN": "FI",
    "FJI": "FJ",
    "FLK": "FK",
    "FRA": "FR",
    "FRO": "FO",
    "FSM": "FM",
    "GAB": "GA",
    "GBR": "GB",
    "GEO": "GE",
    "GGY": "GG",
    "GHA": "GH",
    "GIB": "GI",
    "GIN": "GN",
    "GLP": "GP",
    "GMB": "GM",
    "GNB": "GW",
    "GNQ": "GQ",
    "GRC": "GR",
    "GRD": "GD",
    "GRL": "GL",
    "GTM": "GT",
    "GUF": "GF",
    "GUM": "GU",
    "GUY": "GY",
    "HKG": "HK",
    "HND": "HN",
    "HRV": "HR",
    "HTI": "HT",
    "HUN": "HU",
    "IDN": "ID",
    "IMN": "IM",
    "IND": "IN",
    "IRL": "IE",
    "IRN": "IR",
    "IRQ": "IQ",
    "ISL": "IS",
    "ISR": "IL",
    "ITA": "IT",
    "JAM": "JM",
    "JEY": "JE",
    "JOR": "JO",
    "JPN": "JP",
    "KAZ": "KZ",
    "KEN": "KE",
    "KGZ": "KG",
    "KHM": "KH",
    "KIR": "KI",
    "KNA": "KN",
    "KOR": "KR",
    "KWT": "KW",
    "LAO": "LA",
    "LBN": "LB",
    "LBR": "LR",
    "LBY": "LY",
    "LCA": "LC",
    "LIE": "LI",
    "LKA": "LK",
    "LSO": "LS",
    "LTU": "LT",
    "LUX": "LU",
    "LVA": "LV",
    "MAC": "MO",
    "MAR": "MA",
    "MCO": "MC",
    "MDA": "MD",
    "MDG": "MG",
    "MDV": "MV",
    "MEX": "MX",
    "MHL": "MH",
    "MKD": "MK",
    "MLI": "ML",
    "MLT": "MT",
    "MMR": "MM",
    "MNE": "ME",
    "MNG": "MN",
    "MNP": "MP",
    "MOZ": "MZ",
    "MRT": "MR",
    "MSR": "MS",
    "MTQ": "MQ",
    "MUS": "MU",
    "MWI": "MW",
    "MYS": "MY",
    "MYT": "YT",
    "NAM": "NA",
    "NCL": "NC",
    "NER": "NE",
    "NFK": "NF",
    "NGA": "NG",
    "NIC": "NI",
    "NIU": "NU",
    "NLD": "NL",
    "NOR": "NO",
    "NPL": "NP",
    "NRU": "NR",
    "NZL": "NZ",
    "OMN": "OM",
    "PAK": "PK",
    "PAN": "PA",
    "PCN": "PN",
    "PER": "PE",
    "PHL": "PH",
    "PLW": "PW",
    "PNG": "PG",
    "POL": "PL",
    "PRI": "PR",
    "PRK": "KP",
    "PRT": "PT",
    "PRY": "PY",
    "PSE": "PS",
    "PYF": "PF",
    "QAT": "QA",
    "REU": "RE",
    "ROU": "RO",
    "RUS": "RU",
    "RWA": "RW",
    "SAU": "SA",
    "SDN": "SD",
    "SEN": "SN",
    "SGP": "SG",
    "SHN": "SH",
    "SJM": "SJ",
    "SLB": "SB",
    "SLE": "SL",
    "SLV": "SV",
    "SMR": "SM",
    "SOM": "SO",
    "SPM": "PM",
    "SRB": "RS",
    "STP": "ST",
    "SUR": "SR",
    "SVK": "SK",
    "SVN": "SI",
    "SWE": "SE",
    "SWZ": "SZ",
    "SYC": "SC",
    "SYR": "SY",
    "TCA": "TC",
    "TCD": "TD",
    "TGO": "TG",
    "THA": "TH",
    "TJK": "TJ",
    "TKL": "TK",
    "TKM": "TM",
    "TLS": "TL",
    "TON": "TO",
    "TTO": "TT",
    "TUN": "TN",
    "TUR": "TR",
    "TUV": "TV",
    "TWN": "TW",
    "TZA": "TZ",
    "UGA": "UG",
    "UKR": "UA",
    "URY": "UY",
    "USA": "US",
    "UZB": "UZ",
    "VAT": "VA",
    "VCT": "VC",
    "VEN": "VE",
    "VGB": "VG",
    "VIR": "VI",
    "VNM": "VN",
    "VUT": "VU",
    "WLF": "WF",
    "WSM": "WS",
    "YEM": "YE",
    "ZAF": "ZA",
    "ZMB": "ZM",
    "ZWE": "ZW",
}


def alpha2(escrito: str | None) -> str | None:
    """El país en dos letras, o None si no se puede saber cuál es.

    Devuelve None en tres casos que son distintos entre sí y que a quien
    llama le da igual distinguir: que no venga nada, que venga algo que no es
    un código de tres letras, y que sea uno de los dos retirados. De los tres,
    lo correcto es no afirmar de qué país es.
    """
    if not escrito:
        return None
    return ALPHA2.get(escrito.strip().upper())
