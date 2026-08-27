"""De dónde salen las anclas: leer una lista de confianza y no creérsela.

Este módulo es el único del validador donde equivocarse sale en verde: un
almacén de anclas mal montado no produce un error, produce un aprobado. Así
que lo que hay que probar no es que sepa leer el XML —eso es lo fácil— sino
que **se niegue** cuando toca:

- una lista sin firma;
- una lista firmada por otro;
- una lista tocada después de firmarla;
- una firma auténtica que no cubre la lista, solo un trozo;
- montar anclas sin haber dicho quién tenía que firmarla.

Para eso hace falta una lista de confianza firmada de verdad, con la clave
privada a mano para poder falsificarla. Se monta aquí con las mismas claves de
juguete de `test_cadena`, y el constructor firma con RSA de verdad: si la
comprobación de firma se rompiera, estas pruebas se ponen rojas.

Lo que aquí **no** puede probarse es que el fichero de verdad tenga la forma
que tiene este constructor: un constructor y un lector escritos por la misma
mano comparten los malentendidos y se dan la razón. Eso se cerró pasándolo por
la lista de listas europea y por la lista española reales, que sacaron cuatro
fallos que ninguna lista inventada iba a sacar —el puntero al PDF, la lista de
un país que parecía la de listas, la cuenta de «sin certificado» y el «DER
truncado» sobre certificados impecables—. Las pruebas de aquí abajo son las que
quedaron de aquello: cada una es un fallo que ya ocurrió.
"""

import base64
import hashlib
from collections import namedtuple
from datetime import datetime, timezone

import pytest
from lxml import etree

from validador import cadena, tsl
from validador.__main__ import main
from validador.cadena import Almacen
from validador.tsl import CA_CUALIFICADA, CONCEDIDO, RAIZ_NACIONAL

from test_cadena import HOJA, INTERMEDIA, INTRUSO, RAIZ, certificado, hoja, intermedia
from test_firma import _c14n, _der, _firmar, _resumen, _secuencia

NS_TSL = "http://uri.etsi.org/02231/v2#"
NS_DS = "http://www.w3.org/2000/09/xmldsig#"

RETIRADO = "http://uri.etsi.org/TrstSvc/TrustedList/Svcstatus/withdrawn"
SELLO_DE_TIEMPO = "http://uri.etsi.org/TrstSvc/Svctype/TSA/QTST"
TIPO_PAIS = "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUgeneric"
TIPO_LISTA_DE_LISTAS = (
    "http://uri.etsi.org/TrstSvc/TrustedList/TSLType/EUlistofthelists"
)

_URI_SHA = {
    "sha1": "http://www.w3.org/2000/09/xmldsig#sha1",
    "sha256": "http://www.w3.org/2001/04/xmlenc#sha256",
}
_URI_FIRMA = {
    "sha1": "http://www.w3.org/2000/09/xmldsig#rsa-sha1",
    "sha256": "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
}
C14N = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"

HOY = datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc)

Serv = namedtuple(
    "Serv",
    "prestador nombre tipo estado desde certificados sueltos",
    defaults=("Certificadora Paco", "CA de pruebas", CA_CUALIFICADA, CONCEDIDO,
              "2016-07-01T00:00:00Z", (), 0),
)
Punt = namedtuple(
    "Punt", "territorio donde tipo firmantes mime",
    defaults=("PT", "https://ejemplo.invalid/pt.xml", TIPO_PAIS, (),
              tsl.MIME_PROCESABLE),
)

MIME_PDF = "application/pdf"


def _spki_de_curva() -> bytes:
    """Un `SubjectPublicKeyInfo` de curva elíptica P-256, bien formado.

    Los 64 bytes del punto son relleno: lo que se prueba no es la curva, es que
    el lector mire el OID del algoritmo **antes** de intentar leer la clave.
    """
    return _secuencia(
        _secuencia(
            _der(0x06, b"\x2a\x86\x48\xce\x3d\x02\x01"),  # id-ecPublicKey
            _der(0x06, b"\x2a\x86\x48\xce\x3d\x03\x01\x07"),  # prime256v1
        ),
        _der(0x03, b"\x00\x04" + bytes(64)),
    )


def ca_de_curva(nombre="AC de curva eliptica"):
    return certificado(
        nombre, "Raiz de pruebas", INTERMEDIA, RAIZ, es_ca=True, serie=55,
        spki=_spki_de_curva(),
    )


# --- El ministerio de juguete que firma la lista ---------------------------


def firmante(clave=HOJA, emisor=RAIZ, nombre="Ministerio de pruebas") -> bytes:
    return certificado(nombre, "Raiz de pruebas", clave, emisor, serie=40)


def _t(padre, nombre, texto=None, **atributos):
    hijo = etree.SubElement(padre, f"{{{NS_TSL}}}{nombre}", **atributos)
    if texto is not None:
        hijo.text = texto
    return hijo


def _con_nombre(padre, etiqueta, texto):
    caja = _t(padre, etiqueta)
    _t(caja, "Name", texto)
    return caja


def lista(
    territorio="ES",
    operador="Ministerio de pruebas",
    tipo=TIPO_PAIS,
    secuencia="7",
    emitida="2026-08-01T00:00:00Z",
    siguiente="2026-11-01T00:00:00Z",
    servicios=(),
    punteros=(),
    firma_de=(HOJA, None),
    alg="sha256",
    cubre="",
    sin_firmar=False,
) -> bytes:
    """Una lista de confianza ETSI TS 119 612, firmada de verdad.

    `firma_de` es (par de claves, certificado). Con el certificado a None se
    fabrica uno con esa misma clave, que es el caso normal; pasándolos
    descabalados se falsifica —una firma hecha con una clave que no es la del
    certificado que la lista enseña—, que es lo que hay que cazar.

    `cubre` es la URI de la referencia. Con "" cubre la lista entera, que es lo
    correcto; con "#SchemeInfo" se fabrica una firma auténtica sobre un trozo.
    """
    claves, cert = firma_de
    if cert is None:
        cert = firmante(claves)

    raiz = etree.Element(f"{{{NS_TSL}}}TrustServiceStatusList")
    cabecera = _t(raiz, "SchemeInformation", Id="SchemeInfo")
    _t(cabecera, "TSLVersionIdentifier", "5")
    _t(cabecera, "TSLSequenceNumber", secuencia)
    if tipo:
        _t(cabecera, "TSLType", tipo)
    _con_nombre(cabecera, "SchemeOperatorName", operador)
    if territorio:
        _t(cabecera, "SchemeTerritory", territorio)
    if punteros:
        # Va **antes** de la fecha de emisión, como en el esquema de verdad: es
        # justo lo que hace que buscar por descendiente sea peligroso.
        caja = _t(cabecera, "PointersToOtherTSL")
        for uno in punteros:
            puntero = _t(caja, "OtherTSLPointer")
            identidades = _t(puntero, "ServiceDigitalIdentities")
            for der in uno.firmantes:
                identidad = _t(identidades, "ServiceDigitalIdentity")
                digital = _t(identidad, "DigitalId")
                _t(digital, "X509Certificate", base64.b64encode(der).decode())
            _t(puntero, "TSLLocation", uno.donde)
            extra = _t(puntero, "AdditionalInformation")
            _t(_t(extra, "OtherInformation"), "SchemeTerritory", uno.territorio)
            _t(_t(extra, "OtherInformation"), "TSLType", uno.tipo)
            if uno.mime:
                _t(_t(extra, "OtherInformation"), "MimeType", uno.mime)
    _t(cabecera, "ListIssueDateTime", emitida)
    if siguiente:
        _t(_t(cabecera, "NextUpdate"), "dateTime", siguiente)

    if servicios:
        prestadores = _t(raiz, "TrustServiceProviderList")
        for uno in servicios:
            prestador = _t(prestadores, "TrustServiceProvider")
            _con_nombre(_t(prestador, "TSPInformation"), "TSPName", uno.prestador)
            caja = _t(prestador, "TSPServices")
            servicio = _t(_t(caja, "TSPService"), "ServiceInformation")
            _t(servicio, "ServiceTypeIdentifier", uno.tipo)
            _con_nombre(servicio, "ServiceName", uno.nombre)
            identidad = _t(servicio, "ServiceDigitalIdentity")
            for der in uno.certificados:
                _t(
                    _t(identidad, "DigitalId"),
                    "X509Certificate",
                    base64.b64encode(der).decode(),
                )
            for _ in range(uno.sueltos):
                # Un servicio identificado sin certificado: solo por el nombre
                # del sujeto. Es legal y no da ancla.
                _t(_t(identidad, "DigitalId"), "X509SubjectName", "CN=sin cert")
            _t(servicio, "ServiceStatus", uno.estado)
            _t(servicio, "StatusStartingTime", uno.desde)

    if sin_firmar:
        return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")

    objetivo = raiz if cubre == "" else cabecera
    resumen = _resumen(_c14n(objetivo), alg)

    ds = lambda n: f"{{{NS_DS}}}{n}"  # noqa: E731
    firma_el = etree.SubElement(raiz, ds("Signature"), Id="TSLSig")
    firmado = etree.SubElement(firma_el, ds("SignedInfo"))
    etree.SubElement(firmado, ds("CanonicalizationMethod")).set("Algorithm", C14N)
    etree.SubElement(firmado, ds("SignatureMethod")).set("Algorithm", _URI_FIRMA[alg])
    referencia = etree.SubElement(firmado, ds("Reference"), URI=cubre)
    if cubre == "":
        transformadas = etree.SubElement(referencia, ds("Transforms"))
        etree.SubElement(transformadas, ds("Transform")).set(
            "Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature"
        )
    etree.SubElement(referencia, ds("DigestMethod")).set("Algorithm", _URI_SHA[alg])
    etree.SubElement(referencia, ds("DigestValue")).text = resumen

    valor = _firmar(_c14n(firmado), alg, claves[0], claves[1])
    etree.SubElement(firma_el, ds("SignatureValue")).text = base64.b64encode(
        valor
    ).decode()
    datos = etree.SubElement(
        etree.SubElement(firma_el, ds("KeyInfo")), ds("X509Data")
    )
    etree.SubElement(datos, ds("X509Certificate")).text = base64.b64encode(
        cert
    ).decode()
    return etree.tostring(raiz, xml_declaration=True, encoding="UTF-8")


def huella_de(der: bytes) -> str:
    crudo = hashlib.sha256(der).hexdigest().upper()
    return ":".join(crudo[i : i + 2] for i in range(0, len(crudo), 2))


def creida(datos: bytes, esperados=None) -> tsl.Lista:
    """Una lista ya comprobada, para las pruebas que van de otra cosa."""
    una = tsl.leer(datos)
    fallo = tsl.comprobar_firma(una, esperados or [huella_de(firmante())])
    assert fallo == "", fallo
    return una


# --- Lo que dice la lista --------------------------------------------------


class TestLoQueDiceLaLista:
    def test_la_cabecera(self):
        una = tsl.leer(lista(secuencia="42"))
        assert una.territorio == "ES"
        assert una.operador == "Ministerio de pruebas"
        assert una.secuencia == "42"
        assert una.emitida.date().isoformat() == "2026-08-01"
        assert una.siguiente.date().isoformat() == "2026-11-01"

    def test_un_servicio_con_su_estado_y_su_fecha(self):
        una = tsl.leer(lista(servicios=[Serv(certificados=(intermedia(),))]))
        assert len(una.servicios) == 1
        servicio = una.servicios[0]
        assert servicio.prestador == "Certificadora Paco"
        assert servicio.concedido
        assert servicio.emite_cualificados
        assert servicio.desde.date().isoformat() == "2016-07-01"
        assert servicio.certificados[0].sujeto == "CA intermedia"

    def test_un_servicio_retirado_se_lee_y_no_se_esconde(self):
        # Que la lista traiga a los retirados es la mitad de su valor: dice
        # quién dejó de ser autoridad y desde cuándo.
        una = tsl.leer(
            lista(
                servicios=[
                    Serv(estado=RETIRADO, desde="2025-02-01T00:00:00Z",
                         certificados=(intermedia(),))
                ]
            )
        )
        servicio = una.servicios[0]
        assert not servicio.concedido
        assert servicio.estado_corto == "withdrawn"
        assert servicio.desde.date().isoformat() == "2025-02-01"

    def test_un_servicio_sin_certificado(self):
        # Identificarse sin certificado —por el nombre del sujeto, o por la
        # huella de la clave— es legal y no da ancla.
        una = tsl.leer(lista(servicios=[Serv(sueltos=2)]))
        servicio = una.servicios[0]
        assert servicio.sin_certificado
        assert servicio.certificados == ()
        assert servicio.no_usables == ()

    def test_un_servicio_normal_no_cuenta_como_sin_certificado(self):
        # Un servicio sano trae **varias** identidades: el certificado, el
        # nombre del sujeto y la huella de la clave. Contar «las que no son un
        # certificado» daba 2 de 3 en cada servicio sano —425 en la lista
        # española— y con ese número encima nadie iba a ver el que importaba.
        una = tsl.leer(
            lista(servicios=[Serv(certificados=(intermedia(),), sueltos=2)])
        )
        servicio = una.servicios[0]
        assert not servicio.sin_certificado
        assert len(servicio.certificados) == 1
        assert tsl.cuentas(una).sin_certificado == 0

    def test_un_certificado_de_curva_eliptica_no_es_un_fichero_roto(self):
        # La noticia no es «hay un servicio menos»: es que esa autoridad sigue
        # siendo cualificada y el corto es este validador. Si se cuenta junto
        # con lo demás, no se entera nadie.
        una = tsl.leer(lista(servicios=[Serv(certificados=(ca_de_curva(),))]))
        servicio = una.servicios[0]
        assert servicio.certificados == ()
        assert not servicio.sin_certificado
        assert len(servicio.no_usables) == 1
        assert "curva elíptica" in servicio.no_usables[0]

    def test_sin_fecha_de_siguiente_actualizacion(self):
        una = tsl.leer(lista(siguiente=""))
        assert una.siguiente is None
        assert not una.vencida(HOY)

    def test_una_lista_vencida_se_sabe(self):
        una = tsl.leer(lista(siguiente="2026-01-01T00:00:00Z"))
        assert una.vencida(HOY)


# --- Creérsela, que es lo otro --------------------------------------------


class TestCreerselaOno:
    def test_la_firma_buena_con_el_firmante_que_toca(self):
        una = tsl.leer(lista())
        assert tsl.comprobar_firma(una, [huella_de(firmante())]) == ""
        assert una.verificada
        assert una.firmante.sujeto == "Ministerio de pruebas"

    def test_la_huella_vale_escrita_de_cualquier_forma(self):
        # Se copia a mano de un diario oficial: con espacios, sin dos puntos,
        # en minúsculas. Rechazarla por el formato sería empujar a la gente a
        # saltarse la comprobación.
        una = tsl.leer(lista())
        cruda = huella_de(firmante()).replace(":", "").lower()
        assert tsl.comprobar_firma(una, [cruda]) == ""

    def test_sin_decir_quien_no_se_comprueba_nada(self):
        # Es el punto entero del módulo: comprobar la firma contra el
        # certificado que la propia lista trae dentro no demuestra nada.
        una = tsl.leer(lista())
        assert "no se ha dicho quién" in tsl.comprobar_firma(una, [])
        assert not una.verificada

    def test_firmada_por_otro(self):
        una = tsl.leer(lista())
        fallo = tsl.comprobar_firma(una, [huella_de(intermedia())])
        assert "no es ninguno de los" in fallo
        assert "Ministerio de pruebas" in fallo
        assert not una.verificada

    def test_una_lista_sin_firma(self):
        una = tsl.leer(lista(sin_firmar=True))
        assert "no viene firmada" in tsl.comprobar_firma(
            una, [huella_de(firmante())]
        )

    def test_tocada_despues_de_firmarla(self):
        datos = lista(operador="Ministerio de pruebas")
        tocada = datos.replace(b"Ministerio de pruebas", b"Ministerio del timo")
        assert tocada != datos
        una = tsl.leer(tocada)
        # La huella del firmante sigue cuadrando —el certificado no se ha
        # tocado—, así que lo que tiene que saltar es el resumen.
        assert "se ha modificado" in tsl.comprobar_firma(
            una, [huella_de(firmante())]
        )

    def test_le_han_metido_una_autoridad_despues_de_firmar(self):
        # El ataque que de verdad importa: colar un ancla en una lista buena.
        buena = lista(servicios=[Serv(certificados=(intermedia(),))])
        colada = buena.replace(
            base64.b64encode(intermedia()),
            base64.b64encode(certificado(
                "CA intermedia", "Raiz falsa", INTRUSO, INTRUSO, es_ca=True
            )),
        )
        assert "se ha modificado" in tsl.comprobar_firma(
            tsl.leer(colada), [huella_de(firmante())]
        )

    def test_la_firma_la_hizo_otra_clave(self):
        # El certificado que enseña es el correcto y su huella cuadra; lo que
        # no cuadra es la firma, hecha con una clave que no es la suya.
        una = tsl.leer(lista(firma_de=(INTRUSO, firmante())))
        assert "no cuadra con el certificado" in tsl.comprobar_firma(
            una, [huella_de(firmante())]
        )

    def test_una_firma_autentica_que_no_cubre_la_lista(self):
        # Verifica perfectamente y no garantiza nada: cubre solo la cabecera,
        # así que la lista de autoridades se puede cambiar entera.
        una = tsl.leer(
            lista(cubre="#SchemeInfo", servicios=[Serv(certificados=(intermedia(),))])
        )
        assert "no cubre la lista entera" in tsl.comprobar_firma(
            una, [huella_de(firmante())]
        )
        assert not una.verificada


# --- El conjunto que sale --------------------------------------------------


class TestElConjunto:
    def test_solo_los_concedidos(self):
        una = creida(
            lista(
                servicios=[
                    Serv(nombre="buena", certificados=(intermedia(),)),
                    Serv(nombre="retirada", estado=RETIRADO,
                         certificados=(certificado(
                             "CA retirada", "Raiz de pruebas", INTRUSO, RAIZ,
                             es_ca=True),)),
                ]
            )
        )
        sujetos = {c.sujeto for c, _ in tsl.anclas_de(una)}
        assert sujetos == {"CA intermedia"}

    def test_los_que_no_emiten_certificados_se_quedan_fuera(self):
        # Un sello de tiempo cualificado está en la misma lista y no es un ancla
        # para validar una factura. Meterlo sería ampliar la confianza sin
        # motivo, que es exactamente de lo que va este módulo.
        una = creida(
            lista(
                servicios=[
                    Serv(tipo=SELLO_DE_TIEMPO, certificados=(intermedia(),)),
                ]
            )
        )
        assert tsl.anclas_de(una) == []

    def test_una_raiz_nacional_si_cuenta(self):
        una = creida(
            lista(servicios=[Serv(tipo=RAIZ_NACIONAL, certificados=(intermedia(),))])
        )
        assert len(tsl.anclas_de(una)) == 1

    def test_el_mismo_certificado_en_dos_servicios_sale_una_vez(self):
        # Una autoridad que emite para firma y para sello aparece dos veces con
        # el mismo certificado. Sin quitar repetidos, el mismo fichero se
        # escribiría dos veces y la cuenta del manifiesto mentiría.
        misma = intermedia()
        una = creida(
            lista(
                servicios=[
                    Serv(nombre="para firma", certificados=(misma,)),
                    Serv(nombre="para sello", certificados=(misma,)),
                ]
            )
        )
        assert len(tsl.anclas_de(una)) == 1
        assert una.servicios[0].certificados[0].der == misma
        assert tsl.cuentas(una).repetidos == 1

    def test_las_cuentas_cuadran_con_lo_que_se_deja_fuera(self):
        una = creida(
            lista(
                servicios=[
                    Serv(nombre="a", certificados=(intermedia(),)),
                    Serv(nombre="b", estado=RETIRADO, certificados=(hoja(),)),
                    Serv(nombre="c", sueltos=3),
                    Serv(nombre="d", tipo=SELLO_DE_TIEMPO, certificados=(hoja(),)),
                ]
            )
        )
        cuentas = tsl.cuentas(una)
        assert cuentas.servicios_mirados == 3  # el sello de tiempo no se mira
        assert cuentas.concedidos == 2
        assert cuentas.retirados == 1
        # Un servicio, no tres identidades: lo que se pierde son autoridades.
        assert cuentas.sin_certificado == 1
        assert cuentas.no_usables == 0
        assert cuentas.escritas == 1

    def test_las_cuentas_separan_lo_que_falta_de_lo_que_no_sabemos_usar(self):
        una = creida(
            lista(
                servicios=[
                    Serv(nombre="a", certificados=(intermedia(),)),
                    Serv(nombre="b", sueltos=1),
                    Serv(nombre="c", certificados=(ca_de_curva(),)),
                ]
            )
        )
        cuentas = tsl.cuentas(una)
        assert cuentas.concedidos == 3
        assert cuentas.sin_certificado == 1
        assert cuentas.no_usables == 1
        assert cuentas.escritas == 1
        assert len(cuentas.motivos) == 1
        cual, cuantos = cuentas.motivos[0]
        assert cuantos == 1 and "curva elíptica" in cual


# --- Montarlo en una carpeta ----------------------------------------------


class TestMontar:
    def test_de_una_lista_sin_comprobar_no_se_monta_nada(self, tmp_path):
        # Se niega, no avisa. La salida de esto es la raíz de confianza de todo
        # lo demás, y un aviso en un informe que nadie lee no es una defensa.
        una = tsl.leer(lista(servicios=[Serv(certificados=(intermedia(),))]))
        with pytest.raises(ValueError, match="no se ha comprobado"):
            tsl.montar(una, tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_escribe_las_anclas_y_su_manifiesto(self, tmp_path):
        una = creida(lista(servicios=[Serv(certificados=(intermedia(),))]))
        resumen = tsl.montar(una, tmp_path, cuando=HOY)
        assert resumen.escritas == 1
        certificados = sorted(tmp_path.glob("*.cer"))
        assert len(certificados) == 1
        assert certificados[0].read_bytes() == intermedia()
        manifiesto = (tmp_path / cadena.NOMBRE_DEL_MANIFIESTO).read_text("utf-8")
        assert "lista de confianza de ES" in manifiesto
        assert "2026-08-01" in manifiesto
        assert huella_de(firmante()) in manifiesto

    def test_el_manifiesto_dice_lo_que_se_ha_dejado_fuera(self, tmp_path):
        una = creida(
            lista(
                servicios=[
                    Serv(nombre="a", certificados=(intermedia(),)),
                    Serv(nombre="b", estado=RETIRADO, certificados=(hoja(),)),
                ]
            )
        )
        tsl.montar(una, tmp_path, cuando=HOY)
        manifiesto = (tmp_path / cadena.NOMBRE_DEL_MANIFIESTO).read_text("utf-8")
        assert "retirados       1" in manifiesto
        # Y por qué importa, no solo cuántos.
        assert "no llega a ninguna" in manifiesto

    def test_el_manifiesto_dice_que_autoridades_no_sabemos_usar_y_por_que(
        self, tmp_path
    ):
        una = creida(
            lista(
                servicios=[
                    Serv(nombre="a", certificados=(intermedia(),)),
                    Serv(nombre="b", certificados=(ca_de_curva(),)),
                ]
            )
        )
        tsl.montar(una, tmp_path, cuando=HOY)
        manifiesto = (tmp_path / cadena.NOMBRE_DEL_MANIFIESTO).read_text("utf-8")
        assert "no utilizables  1" in manifiesto
        assert "curva elíptica" in manifiesto
        # Y que no las mete en el mismo saco que las retiradas, porque no es
        # la misma noticia: esa autoridad sigue siendo cualificada.
        assert "el corto es este validador" in manifiesto

    def test_dos_autoridades_con_el_mismo_nombre_no_se_pisan(self, tmp_path):
        # Una autoridad que renueva su certificado se llama igual que ella
        # misma, y las dos son buenas a la vez. Sin la huella en el nombre del
        # fichero, la segunda machacaría a la primera y el conjunto saldría
        # corto sin que nadie se enterara.
        vieja = intermedia()
        nueva = certificado(
            "CA intermedia", "Raiz de pruebas", INTERMEDIA, RAIZ,
            es_ca=True, serie=99,
        )
        assert vieja != nueva
        una = creida(
            lista(
                servicios=[
                    Serv(nombre="vieja", certificados=(vieja,)),
                    Serv(nombre="nueva", certificados=(nueva,)),
                ]
            )
        )
        resumen = tsl.montar(una, tmp_path, cuando=HOY)
        assert resumen.escritas == 2
        assert len(list(tmp_path.glob("*.cer"))) == 2

    def test_lo_montado_encadena_de_verdad(self, tmp_path):
        # La prueba que de verdad importa: que la carpeta que sale de aquí
        # sirva como almacén de anclas sin tocar nada más.
        una = creida(lista(servicios=[Serv(certificados=(intermedia(),))]))
        tsl.montar(una, tmp_path, cuando=HOY)
        almacen = Almacen(tmp_path)
        resultado = cadena.construir(
            cadena.leer_certificado(hoja()), almacen
        )
        assert resultado.llega
        assert resultado.ancla.sujeto == "CA intermedia"

    def test_el_manifiesto_no_se_cuela_como_ancla(self, tmp_path):
        # `Almacen` recorre la carpeta entera. Un .txt no tiene extensión de
        # certificado, pero conviene que quede probado y no supuesto.
        una = creida(lista(servicios=[Serv(certificados=(intermedia(),))]))
        tsl.montar(una, tmp_path, cuando=HOY)
        almacen = Almacen(tmp_path)
        assert len(almacen.todas()) == 1
        assert almacen.ilegibles == []


# --- Que el conjunto diga de dónde viene -----------------------------------


class TestLaProcedencia:
    def test_el_almacen_lee_el_manifiesto(self, tmp_path):
        una = creida(lista(servicios=[Serv(certificados=(intermedia(),))]))
        tsl.montar(una, tmp_path, cuando=HOY)
        almacen = Almacen(tmp_path)
        procedencia = almacen.procedencia_de(almacen.todas()[0])
        assert procedencia.startswith("de la lista de confianza de ES")
        assert "Ministerio de pruebas" in procedencia
        assert "2026-08-01" in procedencia

    def test_sin_manifiesto_se_dice_la_ruta(self, tmp_path):
        (tmp_path / "una.cer").write_bytes(intermedia())
        almacen = Almacen(tmp_path)
        assert "instalada en" in almacen.procedencia_de(almacen.todas()[0])

    def test_la_declarada_a_mano_manda_sobre_el_manifiesto(self, tmp_path):
        # Quien distribuye un conjunto sabe mejor que el manifiesto cómo llega
        # a quien lo recibe: «viene con esta página» es más útil que la ruta o
        # que el origen, porque es lo que quien lee no puede saber.
        una = creida(lista(servicios=[Serv(certificados=(intermedia(),))]))
        tsl.montar(una, tmp_path, cuando=HOY)
        almacen = Almacen(tmp_path, procedencia="viene con esta página")
        assert almacen.procedencia_de(almacen.todas()[0]) == "viene con esta página"

    def test_un_manifiesto_ilegible_no_revienta_nada(self, tmp_path):
        una = creida(lista(servicios=[Serv(certificados=(intermedia(),))]))
        tsl.montar(una, tmp_path, cuando=HOY)
        (tmp_path / cadena.NOMBRE_DEL_MANIFIESTO).write_bytes(b"\xff\xfe\x00rot")
        almacen = Almacen(tmp_path)
        assert "instalada en" in almacen.procedencia_de(almacen.todas()[0])

    def test_el_informe_de_una_factura_lo_dice(self, tmp_path):
        # La condición que hace aceptable traer las anclas puestas: que el
        # informe diga de dónde salieron. Aquí se comprueba de punta a punta,
        # desde la lista de confianza hasta la línea que lee una persona.
        una = creida(lista(servicios=[Serv(certificados=(intermedia(),))]))
        tsl.montar(una, tmp_path, cuando=HOY)
        quejas = cadena.reglas(
            [cadena.leer_certificado(hoja())], Almacen(tmp_path), cuando=HOY
        )
        notas = [q for q in quejas if q.codigo == "CONFIANZA-ANCLA"]
        assert len(notas) == 1
        assert "de la lista de confianza de ES" in notas[0].mensaje
        assert huella_de(intermedia()) in notas[0].mensaje


# --- La lista de listas ----------------------------------------------------


class TestLaListaDeListas:
    def test_dice_donde_esta_la_de_cada_pais_y_quien_la_firma(self):
        una = tsl.leer(
            lista(
                territorio="EU",
                tipo=TIPO_LISTA_DE_LISTAS,
                punteros=[
                    Punt("ES", "https://ejemplo.invalid/es.xml",
                         firmantes=(firmante(),)),
                    Punt("PT", "https://ejemplo.invalid/pt.xml"),
                ],
            )
        )
        assert una.es_lista_de_listas
        espania = una.puntero_de("es")
        assert espania.donde == "https://ejemplo.invalid/es.xml"
        assert len(espania.firmantes) == 1
        assert espania.firmantes[0].sujeto == "Ministerio de pruebas"

    def test_el_territorio_de_un_puntero_no_es_el_de_la_lista(self):
        # Los punteros cuelgan de la misma `SchemeInformation` que la cabecera
        # y repiten sus etiquetas. Buscando por descendiente, una lista de
        # listas sin territorio propio —los hay— dice ser la de otro país, y a
        # partir de ahí `puntero_de` busca lo que no es.
        una = tsl.leer(
            lista(
                territorio="",
                tipo=TIPO_LISTA_DE_LISTAS,
                punteros=[Punt("AT", "https://ejemplo.invalid/at.xml")],
            )
        )
        assert una.territorio == ""
        assert una.puntero_de("AT") is not None

    def test_el_tipo_de_la_cabecera_tampoco(self):
        una = tsl.leer(
            lista(
                tipo="",
                punteros=[Punt("AT", "https://ejemplo.invalid/at.xml",
                               tipo=TIPO_PAIS)],
            )
        )
        assert una.tipo == ""

    def test_la_lista_de_un_pais_tambien_trae_un_puntero(self):
        # Y no por eso es una lista de listas. El formato le exige a cada país
        # apuntar de vuelta a la LOTL, así que «trae punteros» no distingue
        # nada: con ese criterio la lista española pasaba por lista de listas
        # y `--ver-tsl` enseñaba el puntero de vuelta en lugar de sus 243
        # autoridades. Lo que las separa es el tipo que declaran.
        una = tsl.leer(
            lista(
                territorio="ES",
                tipo=TIPO_PAIS,
                punteros=[Punt("EU", "https://ejemplo.invalid/eu-lotl.xml")],
                servicios=[Serv(certificados=(intermedia(),))],
            )
        )
        assert not una.es_lista_de_listas
        assert len(una.punteros) == 1

    def test_manda_el_tipo_declarado_y_no_la_forma(self):
        # «Trae punteros y ningún servicio» acierta con las listas de hoy, pero
        # es una conjetura sobre la forma. El tipo es lo que la lista **declara
        # de sí misma**, y va dentro de lo firmado: si una lista de listas trae
        # además un servicio, la conjetura falla y el tipo no.
        una = tsl.leer(
            lista(
                territorio="EU",
                tipo=TIPO_LISTA_DE_LISTAS,
                punteros=[Punt("ES", "https://ejemplo.invalid/es.xml")],
                servicios=[Serv(certificados=(intermedia(),))],
            )
        )
        assert una.es_lista_de_listas

    def test_sin_tipo_declarado_lo_distingue_la_forma(self):
        con_servicios = tsl.leer(
            lista(tipo="", punteros=[Punt("EU", "x")],
                  servicios=[Serv(certificados=(intermedia(),))])
        )
        assert not con_servicios.es_lista_de_listas
        sin_servicios = tsl.leer(lista(tipo="", punteros=[Punt("ES", "x")]))
        assert sin_servicios.es_lista_de_listas

    def test_el_puntero_de_un_pais_es_el_del_fichero_procesable(self):
        # En la lista de listas de verdad, once países aparecen **dos veces**:
        # una entrada para el PDF legible y otra para el XML, y la del PDF va
        # primero. Quedarse con la primera que case mandaba a bajar el PDF —y
        # daba por buenos los certificados de esa entrada, confiando en que
        # fueran los mismos que los de la otra—.
        otro = firmante(INTERMEDIA, nombre="Otro firmante")
        una = tsl.leer(
            lista(
                territorio="EU",
                tipo=TIPO_LISTA_DE_LISTAS,
                punteros=[
                    Punt("ES", "https://ejemplo.invalid/es.pdf", mime=MIME_PDF,
                         firmantes=(otro,)),
                    Punt("ES", "https://ejemplo.invalid/es.xml",
                         firmantes=(firmante(),)),
                ],
            )
        )
        espania = una.puntero_de("ES")
        assert espania.donde.endswith(".xml")
        assert espania.procesable
        assert espania.firmantes[0].sujeto == "Ministerio de pruebas"

    def test_sin_tipo_de_fichero_se_devuelve_lo_que_haya(self):
        # Hay listas antiguas que no declaran el tipo. Quedarse callado sería
        # peor que devolver lo único que hay.
        una = tsl.leer(
            lista(
                territorio="EU",
                tipo=TIPO_LISTA_DE_LISTAS,
                punteros=[Punt("ES", "https://ejemplo.invalid/es.xml", mime="")],
            )
        )
        assert una.puntero_de("ES") is not None

    def test_una_lista_de_listas_no_trae_anclas(self):
        una = creida(
            lista(territorio="EU", tipo=TIPO_LISTA_DE_LISTAS,
                  punteros=[Punt("ES", "https://ejemplo.invalid/es.xml")])
        )
        assert tsl.anclas_de(una) == []


# --- La consola ------------------------------------------------------------


def _escribir(tmp_path, nombre, datos):
    ruta = tmp_path / nombre
    ruta.write_bytes(datos)
    return ruta


class TestLaConsola:
    def test_ver_tsl_cuenta_lo_de_dentro(self, tmp_path, capsys):
        ruta = _escribir(
            tmp_path,
            "es.xml",
            lista(
                servicios=[
                    Serv(nombre="a", certificados=(intermedia(),)),
                    Serv(prestador="La que se fue", estado=RETIRADO,
                         desde="2025-02-01T00:00:00Z", certificados=(hoja(),)),
                ]
            ),
        )
        assert main(["--ver-tsl", str(ruta), "--hoy", "2026-03-02"]) == 0
        salida = capsys.readouterr().out
        assert "territorio  ES" in salida
        assert "concedidos       1" in salida
        assert "retirados        1" in salida
        assert "La que se fue" in salida
        # Y que deja claro que mirar no es creerse.
        assert "no se ha comprobado" in salida

    def test_ver_tsl_de_una_lista_de_listas_enseña_las_direcciones(
        self, tmp_path, capsys
    ):
        # Esto es lo que evita escribir de memoria la dirección de un país.
        ruta = _escribir(
            tmp_path,
            "lotl.xml",
            lista(territorio="EU", tipo=TIPO_LISTA_DE_LISTAS,
                  punteros=[Punt("ES", "https://ejemplo.invalid/es.xml",
                                 firmantes=(firmante(),))]),
        )
        assert main(["--ver-tsl", str(ruta)]) == 0
        salida = capsys.readouterr().out
        assert "lista de listas" in salida
        assert "https://ejemplo.invalid/es.xml" in salida

    def test_montar_sin_firmante_se_niega_y_explica(self, tmp_path, capsys):
        ruta = _escribir(tmp_path, "es.xml",
                         lista(servicios=[Serv(certificados=(intermedia(),))]))
        destino = tmp_path / "anclas"
        assert main(["--montar-anclas", str(ruta), "--en", str(destino)]) == 2
        error = capsys.readouterr().err
        assert "no demuestra nada" in error
        assert "--firmante" in error
        assert not destino.exists()

    def test_montar_con_el_firmante_equivocado_no_escribe_nada(
        self, tmp_path, capsys
    ):
        ruta = _escribir(tmp_path, "es.xml",
                         lista(servicios=[Serv(certificados=(intermedia(),))]))
        destino = tmp_path / "anclas"
        codigo = main([
            "--montar-anclas", str(ruta),
            "--firmante", huella_de(intermedia()),
            "--en", str(destino),
        ])
        assert codigo == 1
        assert "No me creo" in capsys.readouterr().err
        assert not destino.exists()

    def test_montar_bien(self, tmp_path, capsys):
        ruta = _escribir(tmp_path, "es.xml",
                         lista(servicios=[Serv(certificados=(intermedia(),))]))
        destino = tmp_path / "anclas"
        codigo = main([
            "--montar-anclas", str(ruta),
            "--firmante", huella_de(firmante()),
            "--en", str(destino),
        ])
        assert codigo == 0
        salida = capsys.readouterr().out
        assert "Montadas 1 anclas" in salida
        assert len(list(destino.glob("*.cer"))) == 1
        assert (destino / cadena.NOMBRE_DEL_MANIFIESTO).exists()

    def test_montar_avisa_de_una_lista_vencida(self, tmp_path, capsys):
        ruta = _escribir(
            tmp_path, "es.xml",
            lista(siguiente="2026-01-01T00:00:00Z",
                  servicios=[Serv(certificados=(intermedia(),))]),
        )
        codigo = main([
            "--montar-anclas", str(ruta),
            "--firmante", huella_de(firmante()),
            "--en", str(tmp_path / "anclas"),
            "--hoy", "2026-03-02",
        ])
        assert codigo == 0
        assert "ya ha pasado" in capsys.readouterr().out

    def test_montar_de_una_lista_sin_autoridades(self, tmp_path, capsys):
        ruta = _escribir(tmp_path, "es.xml", lista())
        destino = tmp_path / "anclas"
        codigo = main([
            "--montar-anclas", str(ruta),
            "--firmante", huella_de(firmante()),
            "--en", str(destino),
        ])
        assert codigo == 2
        assert "no hay anclas que montar" in capsys.readouterr().err
        assert not destino.exists()

    def test_segun_una_lista_de_listas_sin_comprobarla_se_niega(
        self, tmp_path, capsys
    ):
        # La trampa evidente: creerse la LOTL porque sí y usarla para
        # verificar la de España. Eso es elegir en quién confiar a partir de un
        # fichero que no se ha comprobado.
        pais = _escribir(tmp_path, "es.xml",
                         lista(servicios=[Serv(certificados=(intermedia(),))]))
        lotl = _escribir(tmp_path, "lotl.xml",
                         lista(territorio="EU", tipo=TIPO_LISTA_DE_LISTAS,
                               punteros=[Punt("ES", "x", firmantes=(firmante(),))]))
        codigo = main([
            "--montar-anclas", str(pais), "--segun", str(lotl),
            "--en", str(tmp_path / "anclas"),
        ])
        assert codigo == 2
        assert "también hay que comprobarla" in capsys.readouterr().err

    def test_la_cadena_entera_desde_la_lista_de_listas(self, tmp_path, capsys):
        # El camino de verdad: se comprueba la LOTL contra una huella del
        # diario oficial, la LOTL dice quién firma la de España, y con eso se
        # comprueba la de España. Ninguna dirección escrita a mano.
        pais = _escribir(tmp_path, "es.xml",
                         lista(servicios=[Serv(certificados=(intermedia(),))]))
        firmante_lotl = firmante(INTERMEDIA, nombre="Comision de pruebas")
        lotl = _escribir(
            tmp_path, "lotl.xml",
            lista(territorio="EU", tipo=TIPO_LISTA_DE_LISTAS,
                  firma_de=(INTERMEDIA, firmante_lotl),
                  punteros=[Punt("ES", "https://ejemplo.invalid/es.xml",
                                 firmantes=(firmante(),))]),
        )
        destino = tmp_path / "anclas"
        codigo = main([
            "--montar-anclas", str(pais), "--segun", str(lotl),
            "--firmante", huella_de(firmante_lotl), "--en", str(destino),
        ])
        assert codigo == 0
        salida = capsys.readouterr().out
        assert "está comprobada" in salida
        assert len(list(destino.glob("*.cer"))) == 1

    def test_si_la_lista_de_listas_no_conoce_al_pais(self, tmp_path, capsys):
        pais = _escribir(tmp_path, "es.xml",
                         lista(servicios=[Serv(certificados=(intermedia(),))]))
        firmante_lotl = firmante(INTERMEDIA, nombre="Comision de pruebas")
        lotl = _escribir(
            tmp_path, "lotl.xml",
            lista(territorio="EU", tipo=TIPO_LISTA_DE_LISTAS,
                  firma_de=(INTERMEDIA, firmante_lotl),
                  punteros=[Punt("PT", "https://ejemplo.invalid/pt.xml")]),
        )
        codigo = main([
            "--montar-anclas", str(pais), "--segun", str(lotl),
            "--firmante", huella_de(firmante_lotl),
            "--en", str(tmp_path / "anclas"),
        ])
        assert codigo == 1
        assert "no dice nada de «ES»" in capsys.readouterr().err

    def test_un_fichero_que_no_es_una_lista(self, tmp_path, capsys):
        ruta = _escribir(tmp_path, "no.xml", b"esto no es XML ni de lejos")
        assert main(["--ver-tsl", str(ruta)]) == 2
        assert "no parece una lista de confianza" in capsys.readouterr().err
