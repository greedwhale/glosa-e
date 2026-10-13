"""De quién es el certificado: la cadena hasta un ancla de confianza.

Para probar un validador de cadenas hace falta una jerarquía de verdad —una
raíz que emite a una intermedia y una intermedia que emite a la hoja— y las
claves privadas de todas, para poder falsificar. Aquí se monta entera: cuatro
pares de claves RSA de 512 bits escritos abajo, y un constructor de X.509 que
firma de verdad.

Con eso se pueden fabricar los ataques que este módulo tiene que parar:

- una hoja que se pone a emitir certificados sin ser autoridad;
- una autoridad que emite por debajo del nivel que tiene permitido;
- un certificado cuyos nombres encadenan perfectamente pero cuya firma la hizo
  otra clave;
- una raíz falsa que dice llamarse igual que la buena.

Un validador que se los trague no protege de nada, y sin la clave privada no
hay forma de comprobarlo.
"""

import hashlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from validador import cadena, firma
from validador.cadena import Almacen, construir
from validador.incidencias import AVISO, ERROR, NOTA
from test_firma import _der, _entero, _nombre, _secuencia, _tiempo

E = 65537
RAIZ = (
    6918895701153146409809682255196961273454307169805984041052015093287494722681869290049469580358876067905215164504416866936966329266434706622641007507928799,
    1952877499426749809857935248129047555371130415293209832482112016046387191665259940444292405008310169784172162652934253777033555472877225166472683355546033,
)
INTERMEDIA = (
    9009682399399060128307024169088463891738782848927225747742209304135803765553874725749639803164858671703324703109166636434889813848631110098600143460014101,
    2113399263407872672726305484709354340413816755978428085204403369584810279504047919328581728959584676867519297979679556834786840183124081714987321107579873,
)
HOJA = (
    7118795234332802458335747299963382483395955829797613312177481990761602171099888509286717208516369310384663848986567652800534510342268989983966661755187313,
    2255546989348316875159708144769208802168500584490401459135532806478243878769026338111755310708825020534778030038561774074094359154123778154957053987815573,
)
INTRUSO = (
    5233184974019807874173975711338640440303684975913139717275658041696076518205187511587846773346782791352432018706975120703996750687835323522984763462511961,
    1006360227468020181549576817522939491724481464690683123378017277255529736773702532184977284228391007949170687046390071162442292455007767729243033219308173,
)

HOY = datetime(2026, 3, 2, 12, 0, tzinfo=timezone.utc)

_OID_SHA256_RSA = b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x0b"
_OID_SHA1_RSA = b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x05"
_OID_BASIC = b"\x55\x1d\x13"
_OID_USO = b"\x55\x1d\x0f"


def _extension(oid: bytes, contenido: bytes, critica: bool = True) -> bytes:
    partes = [_der(0x06, oid)]
    if critica:
        partes.append(_der(0x01, b"\xff"))
    partes.append(_der(0x04, contenido))
    return _secuencia(*partes)


def _basic_constraints(es_ca: bool, profundidad=None) -> bytes:
    dentro = [_der(0x01, b"\xff")] if es_ca else []
    if profundidad is not None:
        dentro.append(_entero(profundidad))
    return _extension(_OID_BASIC, _secuencia(*dentro))


def _key_usage(*cuales: str) -> bytes:
    # Bits en el orden de X.509: 0 digitalSignature ... 5 keyCertSign.
    orden = [
        "firma",
        "no_repudio",
        "cifrar_clave",
        "cifrar_datos",
        "acuerdo_clave",
        "firmar_certificados",
        "firmar_crl",
    ]
    numero = 0
    for nombre in cuales:
        numero |= 1 << (7 - orden.index(nombre))
    return _extension(_OID_USO, _der(0x03, bytes([0, numero])))


def certificado(
    sujeto: str,
    emisor: str,
    clave,
    clave_emisor,
    es_ca: bool = False,
    profundidad=None,
    usos=None,
    desde=None,
    hasta=None,
    alg: str = "sha256",
    serie: int = 1,
    extensiones: bytes = b"",
    spki: bytes | None = None,
) -> bytes:
    """Un X.509 firmado de verdad por `clave_emisor`.

    `clave` es el par del sujeto —solo se usa el módulo, que va dentro— y
    `clave_emisor` el del que firma. Para una raíz autofirmada, los dos el
    mismo.
    """
    modulo, _ = clave
    desde = desde or HOY - timedelta(days=365)
    hasta = hasta or HOY + timedelta(days=365)
    oid = _OID_SHA256_RSA if alg == "sha256" else _OID_SHA1_RSA

    spki = spki or _secuencia(
        _secuencia(_der(0x06, b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01"), _der(0x05, b"")),
        _der(0x03, b"\x00" + _secuencia(_entero(modulo), _entero(E))),
    )
    if usos is None:
        usos = ("firmar_certificados", "firmar_crl") if es_ca else ("firma", "no_repudio")
    bloque = extensiones or (
        _basic_constraints(es_ca, profundidad) + (_key_usage(*usos) if usos else b"")
    )
    tbs = _secuencia(
        _der(0xA0, _entero(2)),
        _entero(serie),
        _secuencia(_der(0x06, oid)),
        _nombre(emisor),
        _secuencia(_tiempo(desde), _tiempo(hasta)),
        _nombre(sujeto),
        spki,
        _der(0xA3, _secuencia(bloque)) if bloque else b"",
    )
    n_emisor, d_emisor = clave_emisor
    tamanio = (n_emisor.bit_length() + 7) // 8
    di = firma._DIGESTINFO[alg] + hashlib.new(alg, tbs).digest()
    relleno = b"\x00\x01" + b"\xff" * (tamanio - len(di) - 3) + b"\x00" + di
    valor = pow(int.from_bytes(relleno, "big"), d_emisor, n_emisor).to_bytes(
        tamanio, "big"
    )
    return _secuencia(tbs, _secuencia(_der(0x06, oid)), _der(0x03, b"\x00" + valor))


# --- La jerarquía de siempre -----------------------------------------------


def raiz(**opciones):
    opciones.setdefault("es_ca", True)
    return certificado("Raiz de pruebas", "Raiz de pruebas", RAIZ, RAIZ, **opciones)


def intermedia(**opciones):
    opciones.setdefault("es_ca", True)
    return certificado(
        "CA intermedia", "Raiz de pruebas", INTERMEDIA, RAIZ, serie=2, **opciones
    )


def hoja(**opciones):
    return certificado(
        "Talleres Paco SL", "CA intermedia", HOJA, INTERMEDIA, serie=3, **opciones
    )


def almacen_con(*ders, tmp_path) -> Almacen:
    for indice, der in enumerate(ders):
        (tmp_path / f"ancla{indice}.cer").write_bytes(der)
    return Almacen(tmp_path)


def leer(der):
    return firma.leer_certificado(der)


def cadena_de(hoja_der, anclas, sueltos=(), tmp_path=None):
    almacen = almacen_con(*anclas, tmp_path=tmp_path)
    return construir(leer(hoja_der), almacen, [leer(s) for s in sueltos])


# --- Que la cadena buena llegue --------------------------------------------


class TestLaCadenaBuena:
    def test_hoja_intermedia_raiz(self, tmp_path):
        # Si esto falla, ninguna otra prueba del fichero significa nada.
        resultado = cadena_de(hoja(), [raiz()], [intermedia()], tmp_path=tmp_path)
        assert resultado.llega, resultado.motivo
        assert [c.sujeto for c in resultado.eslabones] == [
            "Talleres Paco SL",
            "CA intermedia",
            "Raiz de pruebas",
        ]
        assert resultado.ancla.sujeto == "Raiz de pruebas"

    def test_la_intermedia_tambien_vale_como_ancla(self, tmp_path):
        """Quien no quiera confiar en la raíz entera puede anclar más abajo."""
        resultado = cadena_de(hoja(), [intermedia()], tmp_path=tmp_path)
        assert resultado.llega
        assert resultado.ancla.sujeto == "CA intermedia"

    def test_el_propio_certificado_como_ancla(self, tmp_path):
        der = hoja()
        resultado = cadena_de(der, [der], tmp_path=tmp_path)
        assert resultado.llega and "es un ancla" in resultado.motivo

    def test_sin_la_intermedia_no_llega(self, tmp_path):
        """Y esto importa: ninguna de las muestras del Gobierno trae sus
        intermedios, así que este es el caso normal, no el raro."""
        resultado = cadena_de(hoja(), [raiz()], tmp_path=tmp_path)
        assert not resultado.llega
        assert "CA intermedia" in resultado.motivo


# --- Los ataques -----------------------------------------------------------


class TestLoQueTieneQueParar:
    def test_una_hoja_haciendose_pasar_por_autoridad(self, tmp_path):
        """El fallo clásico de `basicConstraints`.

        Un certificado normal —el de cualquiera— emite otro a nombre de quien
        le da la gana. Si no se mira `cA`, la cadena sube por él hasta la raíz
        de verdad y todo parece correcto. Fue un agujero real y grande.
        """
        falsa = certificado(
            "Banco Importante SA", "Talleres Paco SL", INTRUSO, HOJA, serie=99
        )
        resultado = cadena_de(
            falsa, [raiz()], [hoja(), intermedia()], tmp_path=tmp_path
        )
        assert not resultado.llega
        assert "no es un certificado de autoridad" in resultado.motivo

    def test_una_intermedia_que_nunca_dijo_ser_autoridad(self, tmp_path):
        """El mismo fallo de arriba, pero callándose en vez de mintiendo.

        `basicConstraints` es opcional en X.509: un certificado puede no
        traerla, y entonces no dice ni que sea autoridad ni que no lo sea. Se
        miraba solo el «no lo soy», así que a este se le dejaba pasar y la
        cadena subía por él hasta la raíz de verdad: tres eslabones y el
        informe diciendo que la firma llegaba a la autoridad.
        """
        sin_basic = certificado(
            "CA intermedia", "Raiz de pruebas", INTERMEDIA, RAIZ, serie=2,
            extensiones=_key_usage("firmar_certificados"),
        )
        falsa = certificado(
            "Banco Importante SA", "CA intermedia", INTRUSO, INTERMEDIA, serie=99
        )
        resultado = cadena_de(falsa, [raiz()], [sin_basic], tmp_path=tmp_path)
        assert not resultado.llega
        assert "no dice ser un certificado de autoridad" in resultado.motivo

    def test_una_intermedia_con_una_extension_critica_que_no_entendemos(self, tmp_path):
        """«Crítica» quiere decir: si no la entiendes, no lo aceptes.

        El caso que importa es `nameConstraints`, que limita a qué nombres
        puede emitir una autoridad. Aplicarla no está hecho; saltársela es
        aceptar certificados que esa autoridad no tenía derecho a emitir, y
        decir además que la cadena llega.
        """
        con_limites = certificado(
            "CA intermedia", "Raiz de pruebas", INTERMEDIA, RAIZ, serie=2,
            extensiones=(
                _basic_constraints(True)
                + _key_usage("firmar_certificados")
                + _extension(b"\x55\x1d\x1e", b"\x30\x00", critica=True)
            ),
        )
        hija = certificado(
            "Talleres Paco SL", "CA intermedia", HOJA, INTERMEDIA, serie=3
        )
        resultado = cadena_de(hija, [raiz()], [con_limites], tmp_path=tmp_path)
        assert not resultado.llega
        assert "nameConstraints" in resultado.motivo

    def test_al_ancla_no_se_le_piden_esas_dos_cosas(self, tmp_path):
        """Y esto también hace falta: un ancla es una decisión, no un hallazgo.

        Quien monta el almacén decide en quién cree. X.509 tampoco procesa las
        extensiones del ancla, y exigírselas dejaría fuera a las raíces viejas
        —sin extensiones— y a las dos de las 268 instaladas que traen una
        crítica que este validador no lee. Lo que viaja dentro del documento sí
        lo elige quien firma, y a eso no se le afloja nada.
        """
        vieja = certificado(
            "Raiz vieja", "Raiz vieja", RAIZ, RAIZ,
            extensiones=_extension(b"\x55\x1d\x1e", b"\x30\x00", critica=True),
        )
        hija = certificado("CA intermedia", "Raiz vieja", INTERMEDIA, RAIZ, serie=2,
                           es_ca=True)
        hoja_de = certificado(
            "Talleres Paco SL", "CA intermedia", HOJA, INTERMEDIA, serie=3
        )
        resultado = cadena_de(hoja_de, [vieja], [hija], tmp_path=tmp_path)
        assert resultado.llega, resultado.motivo

    def test_y_con_ca_puesto_pero_sin_permiso_de_firmar(self, tmp_path):
        """`keyUsage` sin `keyCertSign`: dice ser autoridad y no puede firmar."""
        coja = certificado(
            "CA intermedia",
            "Raiz de pruebas",
            INTERMEDIA,
            RAIZ,
            es_ca=True,
            usos=("firma",),
            serie=2,
        )
        resultado = cadena_de(hoja(), [raiz()], [coja], tmp_path=tmp_path)
        assert not resultado.llega
        assert "no tiene permiso para firmar certificados" in resultado.motivo

    def test_por_debajo_de_la_profundidad_permitida(self, tmp_path):
        """`pathLenConstraint`: una CA con 0 solo puede emitir hojas."""
        limitada = certificado(
            "CA intermedia",
            "Raiz de pruebas",
            INTERMEDIA,
            RAIZ,
            es_ca=True,
            profundidad=0,
            serie=2,
        )
        subca = certificado(
            "CA de segundo nivel", "CA intermedia", INTRUSO, INTERMEDIA, es_ca=True
        )
        nieta = certificado(
            "Talleres Paco SL", "CA de segundo nivel", HOJA, INTRUSO
        )
        resultado = cadena_de(
            nieta, [raiz()], [subca, limitada], tmp_path=tmp_path
        )
        assert not resultado.llega
        assert "nivel" in resultado.motivo

    def test_los_nombres_encajan_pero_la_firma_no(self, tmp_path):
        """La prueba de que no se encadena solo por el nombre.

        Este certificado dice estar emitido por «CA intermedia» y lo firmó otra
        clave. Los nombres cuadran perfectamente; la criptografía no.
        """
        impostora = certificado(
            "Talleres Paco SL", "CA intermedia", HOJA, INTRUSO, serie=3
        )
        resultado = cadena_de(
            impostora, [raiz()], [intermedia()], tmp_path=tmp_path
        )
        assert not resultado.llega
        assert "no la hizo" in resultado.motivo

    def test_una_raiz_falsa_con_el_nombre_de_la_buena(self, tmp_path):
        """El almacén compara byte a byte, no por nombre.

        Si bastara el sujeto, cualquiera fabrica una raíz que dice llamarse
        igual que una conocida y entra por la puerta grande.
        """
        falsa = certificado(
            "Raiz de pruebas", "Raiz de pruebas", INTRUSO, INTRUSO, es_ca=True
        )
        assert leer(falsa).sujeto_der == leer(raiz()).sujeto_der
        almacen = almacen_con(raiz(), tmp_path=tmp_path)
        assert not almacen.contiene(leer(falsa))

    def test_y_lo_que_emita_esa_raiz_falsa_no_llega(self, tmp_path):
        falsa = certificado(
            "Raiz de pruebas", "Raiz de pruebas", INTRUSO, INTRUSO, es_ca=True
        )
        suya = certificado("Talleres Paco SL", "Raiz de pruebas", HOJA, INTRUSO)
        resultado = cadena_de(suya, [raiz()], [falsa], tmp_path=tmp_path)
        assert not resultado.llega

    def test_una_cadena_circular_no_da_vueltas(self, tmp_path):
        a = certificado("A", "B", INTERMEDIA, INTRUSO, es_ca=True)
        b = certificado("B", "A", INTRUSO, INTERMEDIA, es_ca=True)
        resultado = cadena_de(hoja(), [raiz()], [a, b], tmp_path=tmp_path)
        assert not resultado.llega
        assert len(resultado.eslabones) <= cadena.PROFUNDIDAD_MAXIMA + 1


# --- El almacén ------------------------------------------------------------


class TestElAlmacen:
    def test_lee_der_y_pem(self, tmp_path):
        import base64

        (tmp_path / "una.cer").write_bytes(raiz())
        pem = base64.b64encode(intermedia()).decode()
        (tmp_path / "otra.pem").write_text(
            "-----BEGIN CERTIFICATE-----\n"
            + "\n".join(pem[i : i + 64] for i in range(0, len(pem), 64))
            + "\n-----END CERTIFICATE-----\n"
        )
        almacen = Almacen(tmp_path)
        assert len(almacen.todas()) == 2
        assert {c.sujeto for c in almacen.todas()} == {
            "Raiz de pruebas",
            "CA intermedia",
        }

    def test_varios_certificados_en_un_pem(self, tmp_path):
        import base64

        def bloque(der):
            b = base64.b64encode(der).decode()
            return (
                "-----BEGIN CERTIFICATE-----\n"
                + "\n".join(b[i : i + 64] for i in range(0, len(b), 64))
                + "\n-----END CERTIFICATE-----\n"
            )

        (tmp_path / "paquete.pem").write_text(bloque(raiz()) + bloque(intermedia()))
        assert len(Almacen(tmp_path).todas()) == 2

    def test_un_fichero_ilegible_no_tumba_el_almacen(self, tmp_path):
        (tmp_path / "buena.cer").write_bytes(raiz())
        (tmp_path / "rota.cer").write_bytes(b"esto no es un certificado")
        almacen = Almacen(tmp_path)
        assert len(almacen.todas()) == 1
        assert len(almacen.ilegibles) == 1

    def test_el_inventario_enseña_las_huellas(self, tmp_path):
        """Es lo que permite comprobar un ancla sin fiarse de por dónde llegó."""
        almacen = almacen_con(raiz(), tmp_path=tmp_path)
        linea = almacen.inventario()[0]
        assert "Raiz de pruebas" in linea
        esperada = hashlib.sha256(raiz()).hexdigest().upper()
        assert linea.split(" · ")[1].strip().replace(":", "") == esperada

    def test_una_carpeta_que_no_existe(self, tmp_path):
        assert Almacen(tmp_path / "no-esta").vacio


# --- Lo que sale en el informe ---------------------------------------------


def quejas(hoja_der, anclas, sueltos=(), tmp_path=None, cuando=HOY):
    almacen = almacen_con(*anclas, tmp_path=tmp_path)
    certs = [leer(hoja_der)] + [leer(s) for s in sueltos]
    return cadena.reglas(certs, almacen, cuando=cuando)


def codigos(incidencias, gravedad=None):
    return {i.codigo for i in incidencias if gravedad is None or i.gravedad == gravedad}


class TestElInforme:
    def test_una_cadena_buena_no_se_queja_pero_declara(self, tmp_path):
        """Ni una queja; una nota diciendo en qué se ha confiado, y lo que falta.

        Antes esto era `== []`: el silencio hacía de aprobado. Pero que una
        firma llegue a una autoridad no es la ausencia de un problema, es una
        decisión —creerle a esa autoridad— que toma el almacén y no quien lee.
        """
        salen = quejas(hoja(), [raiz()], [intermedia()], tmp_path=tmp_path)
        assert codigos(salen, ERROR) == set()
        assert codigos(salen, AVISO) == {"REVOCACION-SIN-COMPROBAR"}
        assert codigos(salen, NOTA) == {"CONFIANZA-ANCLA"}

    def test_la_nota_dice_a_que_ancla_llega_y_con_que_huella(self, tmp_path):
        salen = quejas(hoja(), [raiz()], [intermedia()], tmp_path=tmp_path)
        nota = next(i for i in salen if i.codigo == "CONFIANZA-ANCLA")
        assert "Raiz de pruebas" in nota.mensaje
        assert leer(raiz()).huella() in nota.mensaje
        assert "3 eslabones" in nota.mensaje

    def test_la_nota_dice_de_donde_salio_el_ancla(self, tmp_path):
        """Es la mitad que importa cuando las anclas no las pusiste tú."""
        salen = quejas(hoja(), [raiz()], [intermedia()], tmp_path=tmp_path)
        nota = next(i for i in salen if i.codigo == "CONFIANZA-ANCLA")
        assert "ancla0.cer" in nota.mensaje

    def test_un_almacen_que_declara_su_procedencia_manda(self, tmp_path):
        """La ruta de un fichero no le dice nada a quien no lo instaló; a quien
        abre la página web hay que decirle que las anclas vienen con ella."""
        almacen = Almacen(tmp_path, procedencia="viene con esta página")
        (tmp_path / "ancla0.cer").write_bytes(raiz())
        salen = cadena.reglas(
            [leer(hoja()), leer(intermedia())], almacen, cuando=HOY
        )
        nota = next(i for i in salen if i.codigo == "CONFIANZA-ANCLA")
        assert "viene con esta página" in nota.mensaje
        assert str(tmp_path) not in nota.mensaje

    def test_si_el_certificado_es_su_propia_ancla_se_dice_asi(self, tmp_path):
        salen = quejas(hoja(), [hoja()], tmp_path=tmp_path)
        nota = next(i for i in salen if i.codigo == "CONFIANZA-ANCLA")
        assert "es él mismo un ancla" in nota.mensaje

    def test_sin_llegar_a_ningun_ancla_no_hay_nada_que_declarar(self, tmp_path):
        """Lo peor sería una nota tranquilizadora sobre una cadena que no
        llega: la nota dice en qué se ha confiado, y aquí no se ha confiado."""
        salen = quejas(hoja(), [raiz()], tmp_path=tmp_path)
        assert codigos(salen, NOTA) == set()

    def test_sin_anclas_avisa_y_no_inventa(self, tmp_path):
        salen = quejas(hoja(), [], tmp_path=tmp_path)
        assert codigos(salen) == {"CADENA-SIN-ANCLAS"}
        assert salen[0].gravedad == AVISO
        assert "se haya inventado" in salen[0].mensaje

    def test_desconocida_es_aviso_no_error(self, tmp_path):
        """«No lo reconozco» no es «es falso», y confundirlos llenaría de
        errores falsos a quien tenga el almacén incompleto."""
        salen = quejas(hoja(), [raiz()], tmp_path=tmp_path)
        assert codigos(salen) == {"CADENA-DESCONOCIDA"}
        assert salen[0].gravedad == AVISO

    def test_pero_una_cadena_mal_formada_si_es_error(self, tmp_path):
        falsa = certificado(
            "Banco Importante SA", "Talleres Paco SL", INTRUSO, HOJA, serie=99
        )
        salen = quejas(
            falsa, [raiz()], [hoja(), intermedia()], tmp_path=tmp_path
        )
        assert "CADENA-ROTA" in codigos(salen, ERROR)

    def test_un_eslabon_caducado_al_firmar(self, tmp_path):
        vieja = certificado(
            "CA intermedia",
            "Raiz de pruebas",
            INTERMEDIA,
            RAIZ,
            es_ca=True,
            desde=HOY - timedelta(days=900),
            hasta=HOY - timedelta(days=10),
            serie=2,
        )
        salen = quejas(hoja(), [raiz()], [vieja], tmp_path=tmp_path)
        assert "CADENA-CADUCADA" in codigos(salen, ERROR)

    def test_sha1_en_la_cadena_avisa(self, tmp_path):
        debil = certificado(
            "CA intermedia", "Raiz de pruebas", INTERMEDIA, RAIZ,
            es_ca=True, alg="sha1", serie=2,
        )
        salen = quejas(hoja(), [raiz()], [debil], tmp_path=tmp_path)
        assert "CADENA-DEBIL" in codigos(salen, AVISO)

    def test_una_raiz_autofirmada_con_sha1_no_molesta(self, tmp_path):
        """Su firma no la comprueba nadie: se confía en ella porque está en el
        almacén. Avisar de casi todas las raíces en circulación sería ruido."""
        vieja = certificado(
            "Raiz de pruebas", "Raiz de pruebas", RAIZ, RAIZ, es_ca=True, alg="sha1"
        )
        salen = quejas(hoja(), [vieja], [intermedia()], tmp_path=tmp_path)
        assert "CADENA-DEBIL" not in codigos(salen)

    def test_un_ancla_que_no_es_raiz_tampoco_molesta(self, tmp_path):
        """Lo mismo, y es el caso normal cuando las anclas salen de una lista
        de confianza: una TSL publica las CA **emisoras**, no las raíces, así
        que el ancla está firmada por alguien —y su firma tampoco la comprueba
        nadie—. La exclusión estaba escrita sobre «autofirmado», que es lo
        mismo solo mientras las anclas son raíces."""
        debil = certificado(
            "CA intermedia", "Raiz de pruebas", INTERMEDIA, RAIZ,
            es_ca=True, alg="sha1", serie=2,
        )
        salen = quejas(hoja(), [debil], tmp_path=tmp_path)
        assert "CADENA-DEBIL" not in codigos(salen)

    def test_los_certificados_del_documento_no_bastan(self, tmp_path):
        """Aunque el documento traiga la cadena entera, sin ancla no vale: los
        de dentro los eligió quien firmó."""
        salen = quejas(
            hoja(), [], [intermedia(), raiz()], tmp_path=tmp_path
        )
        assert codigos(salen) == {"CADENA-SIN-ANCLAS"}


# --- Sobre una factura de verdad -------------------------------------------

EJEMPLO = Path(__file__).resolve().parent.parent / "ejemplos" / "fe-0001.xml"
tiene_ejemplo = pytest.mark.skipif(not EJEMPLO.exists(), reason="no está el ejemplo")


def _certificado_del_ejemplo() -> bytes:
    import base64

    from lxml import etree

    raiz_xml = etree.parse(str(EJEMPLO)).getroot()
    texto = raiz_xml.xpath("//*[local-name()='X509Certificate']/text()")[0]
    return base64.b64decode("".join(texto.split()))


class TestSobreUnaFacturaDeVerdad:
    """De punta a punta: el documento entero, no un certificado suelto."""

    @tiene_ejemplo
    def test_sin_anclas_lo_dice(self, tmp_path):
        from validador import factura

        informe = factura.validar_archivo(EJEMPLO, almacen=Almacen(tmp_path))
        assert "CADENA-SIN-ANCLAS" in {i.codigo for i in informe.incidencias}

    @tiene_ejemplo
    def test_sin_anclas_en_la_pagina_no_da_la_carpeta(self, tmp_path):
        """En consola, dónde se instalan; en la página, que se recargue.

        Con procedencia las anclas vienen con la herramienta y quien valida no
        las puede poner. Sin ella, una página cuyo paquete no llegó decía «Se
        instalan en «anclas»», que es una carpeta de su disco virtual.
        """
        from validador import factura

        carpeta = tmp_path / "anclas"
        en_consola = factura.validar_archivo(EJEMPLO, almacen=Almacen(carpeta))
        en_la_pagina = factura.validar_archivo(
            EJEMPLO, almacen=Almacen(carpeta, "que viene con esta página")
        )
        [consola] = [
            i for i in en_consola.incidencias if i.codigo == "CADENA-SIN-ANCLAS"
        ]
        [pagina] = [
            i for i in en_la_pagina.incidencias if i.codigo == "CADENA-SIN-ANCLAS"
        ]
        assert f"Se instalan en \"{carpeta}\"." in consola.mensaje
        assert str(carpeta) not in pagina.mensaje
        assert "instala" not in pagina.mensaje
        assert "recargarla las vuelve a pedir" in pagina.mensaje

    @tiene_ejemplo
    def test_con_su_certificado_de_ancla_la_cadena_llega(self, tmp_path):
        from validador import factura

        (tmp_path / "ejemplo.cer").write_bytes(_certificado_del_ejemplo())
        informe = factura.validar_archivo(EJEMPLO, almacen=Almacen(tmp_path))
        assert not [
            i for i in informe.incidencias if i.codigo.startswith("CADENA-")
        ]
        assert informe.conforme

    @tiene_ejemplo
    def test_con_otra_ancla_no_llega_y_lo_dice(self, tmp_path):
        from validador import factura

        (tmp_path / "otra.cer").write_bytes(raiz())
        informe = factura.validar_archivo(EJEMPLO, almacen=Almacen(tmp_path))
        salta = [i for i in informe.incidencias if i.codigo == "CADENA-DESCONOCIDA"]
        assert salta
        # Dos cosas distintas y las dos hacen falta: el **emisor que falta** va
        # en el mensaje, porque es lo que hay que instalar; y el certificado
        # desde el que se intentó subir va en `encontrado`, porque es de quien
        # se está hablando. La primera es la accionable.
        assert "CA de pruebas" in salta[0].mensaje
        assert "Talleres Ejemplo SL" in salta[0].encontrado

    @tiene_ejemplo
    def test_la_queja_sale_como_de_la_firma(self, tmp_path):
        from validador import factura

        informe = factura.validar_archivo(EJEMPLO, almacen=Almacen(tmp_path))
        salta = [i for i in informe.incidencias if i.codigo.startswith("CADENA-")][0]
        assert factura.origen(salta) == factura.SELLO

    @tiene_ejemplo
    def test_el_alcance_cambia_segun_haya_anclas(self, tmp_path):
        """El informe no puede prometer lo mismo en los dos casos."""
        from validador import factura

        lote = factura.validar_lote([EJEMPLO], almacen=Almacen(tmp_path))
        sin = lote.alcance(forma=False, anclas=False)
        con = lote.alcance(forma=False, anclas=True)
        assert "sin anclas de confianza no se sabe" in sin
        assert "sin anclas de confianza no se sabe" not in con
        # Y con anclas tampoco promete que la cadena llegue: la del ejemplo no
        # llega a ninguna, y hasta el 16-09-2026 esta prueba pedía justo esa
        # promesa. Lo que se dice es que no se sabe de quién es, y dónde mirar
        # por qué. Que la promesa sale cuando sí llega lo prueba `test_firma`.
        assert "lleve a un ancla de confianza" not in con
        assert "de quién es el certificado de este documento" in con

    def test_un_documento_sin_firma_no_dice_nada_de_cadenas(self, tmp_path):
        from validador import factura

        (tmp_path / "una.cer").write_bytes(raiz())
        ubl = (
            '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">'
            "</Invoice>"
        )
        informe = factura.validar(ubl.encode(), almacen=Almacen(tmp_path))
        assert not [
            i for i in informe.incidencias if i.codigo.startswith("CADENA-")
        ]


# --- De cuándo son las anclas ----------------------------------------------


def _manifiesto_de(carpeta, publicada="2026-08-06", siguiente="2027-02-02"):
    """Un manifiesto como el que deja `--montar-anclas`, con sus fechas.

    Se escribe a mano aquí y no se monta una lista de verdad porque lo que se
    prueba es la reacción a las fechas, no cómo se escriben. Que las dos
    puntas —lo que escribe `tsl` y lo que lee `Almacen`— siguen entendiéndose
    lo prueba `TestDeCuandoSonLasAnclas` en `test_tsl.py`, con una lista de
    confianza firmada de verdad.
    """
    (carpeta / cadena.NOMBRE_DEL_MANIFIESTO).write_text(
        "de la lista de confianza de ES, publicada por el Ministerio\n"
        "\n"
        f"  publicada        {publicada}\n"
        f"  siguiente        {siguiente}\n"
        "  montada          2026-08-27\n",
        encoding="utf-8",
    )


class TestLasAnclasSinRenovar:
    """Un conjunto de anclas no caduca; la lista de la que salió, sí.

    Los certificados de dentro valen veinte años. Lo que vale seis meses es la
    lista de **quién sigue estando autorizado**, y a una autoridad a la que le
    retiren la cualificación en enero se le sigue creyendo en un conjunto
    montado en agosto: su certificado está en vigor y la cadena llega.

    Que la lista estuviera vencida se comprobaba **solo al montarla**, y
    después no se volvía a mirar nunca. Mientras las anclas las instala quien
    valida eso casi se nota, porque las montó él. En cuanto un conjunto viaja
    con una herramienta —con la página, por ejemplo— quien lo usa no eligió
    nada y no tiene forma de enterarse.
    """

    @tiene_ejemplo
    def test_pasada_la_fecha_se_avisa(self, tmp_path):
        from validador import factura

        (tmp_path / "ejemplo.cer").write_bytes(_certificado_del_ejemplo())
        _manifiesto_de(tmp_path)
        informe = factura.validar_archivo(
            EJEMPLO, almacen=Almacen(tmp_path), hoy=date(2027, 3, 4)
        )
        salta = [i for i in informe.incidencias if i.codigo == "ANCLAS-SIN-RENOVAR"]
        assert len(salta) == 1
        assert salta[0].gravedad == AVISO
        # Los días de atraso, para que no haya que restar de cabeza.
        assert "30 días" in salta[0].mensaje
        assert "La cadena de esta firma llega, pero" in salta[0].mensaje
        # En consola, la orden con que se arregla.
        assert "python -m validador --montar-anclas" in salta[0].mensaje

    @tiene_ejemplo
    def test_si_la_cadena_no_llega_no_dice_que_llega(self, tmp_path):
        """Decía «la cadena de esta firma llega igual» encima de un CADENA-DESCONOCIDA.

        El aviso se queda, porque con unas anclas viejas puede ser justo eso:
        una autoridad que el Estado añadió a su lista después de montarlas.
        """
        from validador import factura

        (tmp_path / "otra.cer").write_bytes(raiz())
        _manifiesto_de(tmp_path)
        informe = factura.validar_archivo(
            EJEMPLO, almacen=Almacen(tmp_path), hoy=date(2027, 3, 4)
        )
        codigos_salen = {i.codigo for i in informe.incidencias}
        assert "CADENA-DESCONOCIDA" in codigos_salen
        [salta] = [i for i in informe.incidencias if i.codigo == "ANCLAS-SIN-RENOVAR"]
        assert "llega, pero" not in salta.mensaje
        assert "no llega a ninguna" in salta.mensaje

    @tiene_ejemplo
    def test_un_dia_va_en_singular(self, tmp_path):
        """«y de eso hace 1 días». Medido con las fechas del paquete publicado."""
        from validador import factura

        (tmp_path / "ejemplo.cer").write_bytes(_certificado_del_ejemplo())
        _manifiesto_de(tmp_path)
        informe = factura.validar_archivo(
            EJEMPLO, almacen=Almacen(tmp_path), hoy=date(2027, 2, 3)
        )
        [salta] = [i for i in informe.incidencias if i.codigo == "ANCLAS-SIN-RENOVAR"]
        assert "hace un día," in salta.mensaje
        assert "1 días" not in salta.mensaje

    @tiene_ejemplo
    def test_en_la_pagina_no_manda_a_la_consola(self, tmp_path):
        """Las anclas de la página las trae ella: la orden no se puede dar allí.

        Desde el 03-02-2027, si el paquete no se vuelve a montar antes, toda
        factura firmada sacaría en la página «Hay que volver a montarlas con
        python -m validador --montar-anclas». La procedencia es lo que le dice
        al motor que las anclas vienen con la herramienta.
        """
        from validador import factura

        (tmp_path / "ejemplo.cer").write_bytes(_certificado_del_ejemplo())
        _manifiesto_de(tmp_path)
        almacen = Almacen(tmp_path, "que viene con esta página")
        informe = factura.validar_archivo(EJEMPLO, almacen=almacen, hoy=date(2027, 3, 4))
        [salta] = [i for i in informe.incidencias if i.codigo == "ANCLAS-SIN-RENOVAR"]
        assert "python -m" not in salta.mensaje
        assert "--montar-anclas" not in salta.mensaje
        assert "quien mantiene esta página" in salta.mensaje

    @tiene_ejemplo
    def test_antes_de_la_fecha_no_se_dice_nada(self, tmp_path):
        from validador import factura

        (tmp_path / "ejemplo.cer").write_bytes(_certificado_del_ejemplo())
        _manifiesto_de(tmp_path)
        informe = factura.validar_archivo(
            EJEMPLO, almacen=Almacen(tmp_path), hoy=date(2026, 9, 20)
        )
        assert "ANCLAS-SIN-RENOVAR" not in {i.codigo for i in informe.incidencias}

    @tiene_ejemplo
    def test_la_cadena_sigue_llegando(self, tmp_path):
        """Es un aviso, no un error: la firma es la que dice ser.

        Lo que no se puede afirmar es que la autoridad siga cualificada hoy.
        Convertirlo en error rechazaría facturas correctas por una lista sin
        renovar, que es un problema de quien valida y no de quien factura.
        """
        from validador import factura

        (tmp_path / "ejemplo.cer").write_bytes(_certificado_del_ejemplo())
        _manifiesto_de(tmp_path)
        informe = factura.validar_archivo(
            EJEMPLO, almacen=Almacen(tmp_path), hoy=date(2027, 3, 4)
        )
        assert not [
            i for i in informe.incidencias if i.codigo.startswith("CADENA-")
        ]
        assert informe.conforme

    @tiene_ejemplo
    def test_una_carpeta_sin_manifiesto_no_se_inventa_la_fecha(self, tmp_path):
        """Sin fechas no se puede decir que esté vencida. Se calla."""
        from validador import factura

        (tmp_path / "ejemplo.cer").write_bytes(_certificado_del_ejemplo())
        informe = factura.validar_archivo(
            EJEMPLO, almacen=Almacen(tmp_path), hoy=date(2030, 1, 1)
        )
        assert "ANCLAS-SIN-RENOVAR" not in {i.codigo for i in informe.incidencias}

    @tiene_ejemplo
    def test_sin_anclas_la_queja_es_la_otra(self, tmp_path):
        """Un almacén vacío no está sin renovar: está vacío, y ya se dice."""
        from validador import factura

        _manifiesto_de(tmp_path)
        informe = factura.validar_archivo(
            EJEMPLO, almacen=Almacen(tmp_path), hoy=date(2027, 3, 4)
        )
        codigos_salen = {i.codigo for i in informe.incidencias}
        assert "CADENA-SIN-ANCLAS" in codigos_salen
        assert "ANCLAS-SIN-RENOVAR" not in codigos_salen

    def test_un_documento_sin_firma_no_dice_nada(self, tmp_path):
        """El almacén solo importa si hay algo que contrastar con él."""
        from validador import factura

        (tmp_path / "una.cer").write_bytes(raiz())
        _manifiesto_de(tmp_path)
        ubl = (
            '<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2">'
            "</Invoice>"
        )
        informe = factura.validar(
            ubl.encode(), almacen=Almacen(tmp_path), hoy=date(2027, 3, 4)
        )
        assert "ANCLAS-SIN-RENOVAR" not in {i.codigo for i in informe.incidencias}

    @tiene_ejemplo
    def test_sale_una_vez_y_no_una_por_firma(self, tmp_path):
        """Es una propiedad del almacén, no de cada firma que se mire.

        `cadena.reglas` corre una vez por firma; si la queja saliera de ahí,
        un documento con tres firmas la diría tres veces. Sale del nivel de
        arriba, y aquí se comprueba que abajo no está.
        """
        (tmp_path / "ejemplo.cer").write_bytes(_certificado_del_ejemplo())
        _manifiesto_de(tmp_path)
        quejas = cadena.reglas(
            [firma.leer_certificado(_certificado_del_ejemplo())],
            Almacen(tmp_path),
            hoy=date(2027, 3, 4),
        )
        assert "ANCLAS-SIN-RENOVAR" not in {i.codigo for i in quejas}


class TestDondeBuscaLasAnclasDeSellado:
    """La carpeta hermana, y quién puede cambiarla.

    Salió al empaquetar las anclas para la página. La página pone
    `FACTURAE_ANCLAS_SELLOS` para que el validador encuentre las que trae
    dentro, y con esa variable puesta **cualquier** almacén —incluido uno
    creado a mano con una carpeta concreta— dejaba de mirar su propia hermana
    y se iba a la del entorno. Para un programa con un solo almacén da igual;
    para uno con dos, uno de los dos contesta por el otro, y lo que contesta
    es qué autoridades pueden sellar el tiempo.
    """

    def _dos_carpetas(self, tmp_path):
        firma_ = tmp_path / "mias"
        sellado = tmp_path / ("mias" + cadena.SUFIJO_DE_SELLOS)
        firma_.mkdir()
        sellado.mkdir()
        (sellado / "tsu.cer").write_bytes(raiz())
        return firma_, sellado

    def test_la_hermana_se_encuentra_sola(self, tmp_path):
        firma_, sellado = self._dos_carpetas(tmp_path)
        assert Almacen(firma_).sellos.carpeta == sellado
        assert not Almacen(firma_).sellos.vacio

    def test_el_entorno_no_desvia_un_almacen_con_nombre(self, tmp_path, monkeypatch):
        firma_, sellado = self._dos_carpetas(tmp_path)
        otra = tmp_path / "de-otro-sitio"
        otra.mkdir()
        monkeypatch.setenv(cadena.VARIABLE_DE_SELLOS, str(otra))
        # Quien nombra una carpeta ya ha dicho cuál quiere.
        assert Almacen(firma_).sellos.carpeta == sellado

    def test_pero_si_manda_sobre_el_almacen_por_defecto(self, tmp_path, monkeypatch):
        """Que es para lo que existe la variable: decir dónde están las tuyas."""
        _, sellado = self._dos_carpetas(tmp_path)
        monkeypatch.setenv(cadena.VARIABLE_DE_SELLOS, str(sellado))
        assert Almacen.por_defecto().sellos.carpeta == sellado

    def test_y_se_puede_decir_al_construirlo(self, tmp_path):
        firma_, sellado = self._dos_carpetas(tmp_path)
        almacen = Almacen(firma_, "", sellado)
        assert almacen.sellos.carpeta == sellado
