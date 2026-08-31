"""¿Anularon el certificado antes de firmar con él?

Para probar esto hacen falta listas de revocación de verdad, firmadas por la
clave de la autoridad que dice publicarlas. Se reutiliza la jerarquía de
`test_cadena` —raíz, intermedia, hoja e intruso, con sus claves privadas— y se
añade aquí un constructor de CRL que firma igual que el de certificados.

Lo que estas pruebas tienen que cazar es de dos clases muy distintas:

- **Creerse una lista que no vale.** Una CRL con el nombre de la autoridad pero
  firmada por otro; una que la autoridad no tenía permiso para firmar; una
  incremental leída como si fuera completa; una acotada a otra clase de
  certificados. En todas ellas la ausencia del certificado no prueba nada, y un
  validador que las dé por buenas dirá «vigente» sin saberlo.
- **Contar mal las fechas.** Una anulación posterior a la firma no invalida la
  firma; una por clave comprometida sí, incluso hacia atrás. Confundirlas es
  rechazar facturas buenas o admitir facturas malas, según por dónde se falle.

Hay además una prueba que sale del círculo: si en la máquina hay `openssl`, se
fabrica con él una autoridad, un certificado y una CRL reales y se leen con
este módulo. Las demás pruebas usan un codificador escrito aquí, y un
codificador y un lector escritos por la misma mano pueden compartir el mismo
malentendido y darse la razón mutuamente. `openssl` no comparte nada.
"""

import re
import shutil
import subprocess
from datetime import datetime, timedelta, timezone

import pytest

from validador import __main__ as consola
from validador import cadena, firma, ocsp, revocacion
from validador.incidencias import AVISO, ERROR, NOTA
from validador.revocacion import AlmacenDeListas, comprobar, leer_lista
from test_cadena import (
    HOJA,
    HOY,
    INTERMEDIA,
    INTRUSO,
    RAIZ,
    _extension,
    almacen_con,
    certificado,
    hoja,
    intermedia,
    leer,
    raiz,
)
from test_firma import _der, _entero, _nombre, _secuencia, _tiempo
from test_ocsp import (
    BUENO,
    SIN_SABER,
    _anulado as _anulado_ocsp,
    _basica,
    _certid,
    _envuelta,
    _single,
)

_OID_SHA256_RSA = b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x0b"
_OID_NUMERO = b"\x55\x1d\x14"
_OID_DELTA = b"\x55\x1d\x1b"
_OID_ALCANCE = b"\x55\x1d\x1c"
_OID_MOTIVO = b"\x55\x1d\x15"
_OID_INVALIDA = b"\x55\x1d\x18"
_OID_PUNTOS = b"\x55\x1d\x1f"
_OID_ACCESOS = b"\x2b\x06\x01\x05\x05\x07\x01\x01"
_OID_OCSP = b"\x2b\x06\x01\x05\x05\x07\x30\x01"
_OID_INVENTADO = b"\x55\x1d\x37"  # 2.5.29.55, que este módulo no conoce

# `hasta=None` querría decir «la de por defecto»; hace falta poder decir además
# «esta lista no trae fecha de caducidad», que es un caso distinto y es el que
# hace que se lea la primera línea de anulados como si fuera la fecha.
SIN_CADUCIDAD = object()


# --- Fabricar listas -------------------------------------------------------


def _linea(serie: int, cuando=None, motivo=None, invalida_desde=None) -> bytes:
    """Una línea de la lista: a quién se anula, cuándo y por qué."""
    extras = []
    if motivo is not None:
        extras.append(_extension(_OID_MOTIVO, _der(0x0A, bytes([motivo])), critica=False))
    if invalida_desde is not None:
        extras.append(
            _extension(_OID_INVALIDA, _tiempo(invalida_desde), critica=False)
        )
    partes = [_entero(serie), _tiempo(cuando or HOY - timedelta(days=30))]
    if extras:
        partes.append(_secuencia(*extras))
    return _secuencia(*partes)


def lista(
    emisor: str = "CA intermedia",
    clave_emisor=INTERMEDIA,
    lineas=(),
    desde=None,
    hasta=None,
    numero: int = 1,
    delta_de=None,
    solo_autoridades: bool = False,
    solo_usuarios: bool = False,
    critica_rara: bool = False,
    alg: str = "sha256",
) -> bytes:
    """Una CRL firmada de verdad por `clave_emisor`."""
    desde = desde or HOY - timedelta(days=1)
    if hasta is None:
        hasta = HOY + timedelta(days=30)
    elif hasta is SIN_CADUCIDAD:
        hasta = None

    extensiones = [_extension(_OID_NUMERO, _entero(numero), critica=False)]
    if delta_de is not None:
        extensiones.append(_extension(_OID_DELTA, _entero(delta_de)))
    if solo_autoridades or solo_usuarios:
        campo = _der(0x82 if solo_autoridades else 0x81, b"\xff")
        extensiones.append(_extension(_OID_ALCANCE, _secuencia(campo)))
    if critica_rara:
        extensiones.append(_extension(_OID_INVENTADO, _der(0x05, b"")))

    tbs = _secuencia(
        _entero(1),  # v2
        _secuencia(_der(0x06, _OID_SHA256_RSA)),
        _nombre(emisor),
        _tiempo(desde),
        _tiempo(hasta) if hasta is not None else b"",
        _secuencia(*lineas) if lineas else b"",
        _der(0xA0, _secuencia(*extensiones)),
    )
    import hashlib

    n, d = clave_emisor
    tamanio = (n.bit_length() + 7) // 8
    di = firma._DIGESTINFO[alg] + hashlib.new(alg, tbs).digest()
    relleno = b"\x00\x01" + b"\xff" * (tamanio - len(di) - 3) + b"\x00" + di
    valor = pow(int.from_bytes(relleno, "big"), d, n).to_bytes(tamanio, "big")
    return _secuencia(
        tbs, _secuencia(_der(0x06, _OID_SHA256_RSA)), _der(0x03, b"\x00" + valor)
    )


def _puntos(url: str) -> bytes:
    """La extensión `cRLDistributionPoints`, con sus tres capas."""
    return _extension(
        _OID_PUNTOS,
        _secuencia(_secuencia(_der(0xA0, _der(0xA0, _der(0x86, url.encode()))))),
        critica=False,
    )


def _acceso_ocsp(url: str) -> bytes:
    return _extension(
        _OID_ACCESOS,
        _secuencia(_secuencia(_der(0x06, _OID_OCSP), _der(0x86, url.encode()))),
        critica=False,
    )


HOJA_SERIE = 3
LA_HOJA = leer(hoja())
LA_INTERMEDIA = leer(intermedia())


def veredicto(*lineas_de_lista, cert=None, emisor=None, cuando=None, **opciones):
    listas = [leer_lista(lista(lineas=lineas_de_lista, **opciones))]
    return comprobar(cert or LA_HOJA, emisor or LA_INTERMEDIA, listas, cuando)


# --- Que se lea lo que pone ------------------------------------------------


class TestLoQueDiceLaLista:
    def test_una_lista_vacia_se_lee(self):
        una = leer_lista(lista())
        assert una.emisor_nombre == "CA intermedia"
        assert una.anulaciones == {}
        assert una.numero == 1
        assert una.desde == HOY - timedelta(days=1)
        assert una.hasta == HOY + timedelta(days=30)

    def test_una_lista_sin_fecha_de_caducidad(self):
        """`nextUpdate` es opcional, y sin este caso se leería la primera línea
        de anulados como si fuera la fecha."""
        una = leer_lista(lista(hasta=SIN_CADUCIDAD, lineas=[_linea(3)]))
        assert una.hasta is None
        assert 3 in una.anulaciones

    def test_se_lee_a_quien_anula_y_por_que(self):
        una = leer_lista(
            lista(lineas=[_linea(3, HOY - timedelta(days=10), motivo=1)])
        )
        anulacion = una.anulaciones[3]
        assert anulacion.cuando == HOY - timedelta(days=10)
        assert anulacion.motivo == 1
        assert anulacion.compromiso
        assert "comprometida" in anulacion.texto_motivo

    def test_se_lee_desde_cuando_se_cree_comprometida(self):
        cuando = HOY - timedelta(days=90)
        una = leer_lista(lista(lineas=[_linea(3, motivo=1, invalida_desde=cuando)]))
        assert una.anulaciones[3].invalida_desde == cuando

    def test_varias_lineas(self):
        una = leer_lista(lista(lineas=[_linea(3), _linea(7, motivo=6)]))
        assert set(una.anulaciones) == {3, 7}
        assert una.anulaciones[7].suspension

    def test_una_lista_incremental_se_reconoce(self):
        una = leer_lista(lista(delta_de=1))
        assert una.es_delta
        assert "incremental" in una.parcial

    def test_una_lista_acotada_se_reconoce(self):
        assert leer_lista(lista(solo_autoridades=True)).solo_autoridades
        assert leer_lista(lista(solo_usuarios=True)).solo_usuarios

    def test_una_critica_que_no_entendemos_se_apunta(self):
        una = leer_lista(lista(critica_rara=True))
        assert una.criticas_sin_entender == frozenset({"551d37"})

    def test_lo_que_no_es_una_lista(self):
        with pytest.raises(ValueError):
            leer_lista(b"\x30\x03\x02\x01\x01")


# --- Que no se crea listas que no valen ------------------------------------


class TestLoQueTieneQueParar:
    def test_la_lista_buena_contesta(self):
        # Si esto falla, ninguna otra prueba de la clase significa nada.
        assert veredicto().estado == "vigente"
        assert veredicto(_linea(HOJA_SERIE)).estado == "anulado"

    def test_una_lista_firmada_por_otro_no_vale(self):
        """El nombre del emisor lo escribe quien fabrica la lista.

        Sin verificar la firma, cualquiera fabrica una CRL vacía a nombre de la
        autoridad y con ella «demuestra» que su certificado revocado sigue
        vigente. Es el ataque que más sentido tiene contra esta parte.
        """
        falsa = leer_lista(lista(clave_emisor=INTRUSO))
        salida = comprobar(LA_HOJA, LA_INTERMEDIA, [falsa])
        assert salida.estado == "sin_saber"
        assert "no la firmó" in salida.motivo

    def test_una_lista_falsa_no_puede_tapar_a_una_buena(self):
        buena = leer_lista(lista(lineas=[_linea(HOJA_SERIE)], numero=1))
        falsa = leer_lista(
            lista(clave_emisor=INTRUSO, numero=2, desde=HOY)  # más nueva
        )
        assert comprobar(LA_HOJA, LA_INTERMEDIA, [falsa, buena]).estado == "anulado"

    def test_sin_permiso_para_firmar_listas_no_se_le_cree(self):
        sin_permiso = leer(
            intermedia(usos=("firmar_certificados",))
        )
        una = leer_lista(lista())
        salida = comprobar(LA_HOJA, sin_permiso, [una])
        assert salida.estado == "sin_saber"
        assert "no tiene permiso para firmar listas" in salida.motivo

    def test_una_incremental_no_puede_decir_que_esta_vigente(self):
        """El fallo más traicionero: parece una lista normal.

        Quien la lea como completa dará por vigente a todo el que no aparezca,
        cuando lo único que dice es qué ha cambiado desde la lista base.
        """
        salida = veredicto(delta_de=1)
        assert salida.estado == "sin_saber"
        assert "incremental" in salida.motivo

    def test_pero_una_incremental_si_puede_acusar(self):
        """Negar y afirmar no cuestan lo mismo: para acusar basta con estar."""
        assert veredicto(_linea(HOJA_SERIE), delta_de=1).estado == "anulado"

    def test_una_lista_de_autoridades_no_contesta_por_una_hoja(self):
        salida = veredicto(solo_autoridades=True)
        assert salida.estado == "sin_saber"
        assert "autoridad" in salida.motivo

    def test_una_lista_de_usuarios_no_contesta_por_una_autoridad(self):
        salida = comprobar(
            LA_INTERMEDIA,
            leer(raiz()),
            [leer_lista(lista(emisor="Raiz de pruebas", clave_emisor=RAIZ, solo_usuarios=True))],
        )
        assert salida.estado == "sin_saber"

    def test_una_critica_que_no_se_entiende_inutiliza_la_lista(self):
        """Lo manda el RFC 5280 y tiene su lógica: si la autoridad marcó algo
        como imprescindible y no lo entendemos, no sabemos qué estamos
        leyendo."""
        salida = veredicto(critica_rara=True)
        assert salida.estado == "sin_saber"
        assert "imprescindible" in salida.motivo

    def test_una_lista_anterior_a_la_firma_no_puede_negar(self):
        salida = veredicto(
            desde=HOY - timedelta(days=300), cuando=HOY - timedelta(days=10)
        )
        assert salida.estado == "sin_saber"
        assert "no pudo enterarse" in salida.motivo

    def test_sin_listas_no_se_inventa_nada(self):
        salida = comprobar(LA_HOJA, LA_INTERMEDIA, [])
        assert salida.estado == "sin_saber"

    def test_manda_la_mas_nueva_y_solo_ella(self):
        """Una suspensión levantada desaparece de las listas siguientes.

        Recorrer todas las listas buscando el número de serie parece más
        prudente y es lo contrario: resucita anulaciones que ya no existen.
        """
        vieja = leer_lista(
            lista(lineas=[_linea(HOJA_SERIE, motivo=6)], desde=HOY - timedelta(days=60))
        )
        nueva = leer_lista(lista(desde=HOY, numero=2))
        assert comprobar(LA_HOJA, LA_INTERMEDIA, [vieja, nueva]).estado == "vigente"


# --- Las fechas ------------------------------------------------------------


def quejas(*lineas_de_lista, cuando=None, hoy=None, sello=None, **opciones):
    listas = [leer_lista(lista(lineas=lineas_de_lista, **opciones))]
    return revocacion.reglas(
        [LA_HOJA, LA_INTERMEDIA, leer(raiz())], listas, cuando=cuando, hoy=hoy,
        sello=sello,
    )


def codigos(incidencias, gravedad=None):
    return {i.codigo for i in incidencias if gravedad is None or i.gravedad == gravedad}


class TestLasFechas:
    def test_anulado_antes_de_firmar_es_error(self):
        salen = quejas(
            _linea(HOJA_SERIE, HOY - timedelta(days=30)), cuando=HOY
        )
        assert codigos(salen) == {"REVOCADO"}
        assert salen[0].gravedad == ERROR

    def test_anulado_despues_de_firmar_es_aviso(self):
        """En su momento valía. Decir que la factura no vale sería rechazar una
        factura buena, que es el fallo caro de esta parte."""
        salen = quejas(
            _linea(HOJA_SERIE, HOY), cuando=HOY - timedelta(days=60)
        )
        assert codigos(salen) == {"REVOCACION-POSTERIOR"}
        assert salen[0].gravedad == AVISO
        assert "la escribe quien firma" in salen[0].mensaje

    def test_con_sello_de_tiempo_la_anulacion_posterior_es_una_nota(self):
        """El mismo hecho, otro veredicto, porque la fecha ya no es de parte.

        Sin sello, «se anuló después de firmar» es un aviso: puede ser verdad,
        pero la fecha la escribe quien firma. Con un sello, la fecha la
        acredita un tercero y ya no hay nada que avisar; queda una nota, que es
        lo que este informe usa para decir qué se ha dado por bueno y con qué.
        """
        from tests.test_sellos import token
        from validador import sellos as _sellos

        sello = _sellos.leer(token())
        salen = quejas(
            _linea(HOJA_SERIE, HOY), cuando=HOY - timedelta(days=60), sello=sello
        )
        assert codigos(salen) == {"REVOCACION-POSTERIOR"}
        assert salen[0].gravedad == NOTA
        assert "TSU de prueba" in salen[0].mensaje
        assert "la escribe quien firma" not in salen[0].mensaje

    def test_anulado_antes_del_sello_sigue_siendo_error(self):
        """El sello no es un salvoconducto: acredita la fecha, no la validez."""
        from tests.test_sellos import token
        from validador import sellos as _sellos

        sello = _sellos.leer(token())
        salen = quejas(
            _linea(HOJA_SERIE, HOY - timedelta(days=30)), cuando=HOY, sello=sello
        )
        assert codigos(salen) == {"REVOCADO"}
        assert salen[0].gravedad == ERROR
        assert "TSU de prueba" in salen[0].mensaje

    def test_la_clave_comprometida_mira_hacia_atras(self):
        """Aunque la denuncia sea posterior a la firma: quien robó la clave
        pudo firmar con la fecha que quisiera."""
        salen = quejas(
            _linea(HOJA_SERIE, HOY, motivo=1), cuando=HOY - timedelta(days=60)
        )
        assert codigos(salen) == {"REVOCACION-COMPROMISO"}
        assert salen[0].gravedad == ERROR

    def test_se_dice_desde_cuando_se_cree_comprometida(self):
        salen = quejas(
            _linea(HOJA_SERIE, HOY, motivo=1, invalida_desde=HOY - timedelta(days=90)),
            cuando=HOY - timedelta(days=60),
        )
        assert (HOY - timedelta(days=90)).date().isoformat() in salen[0].mensaje

    def test_una_suspension_es_aviso_no_error(self):
        salen = quejas(_linea(HOJA_SERIE, HOY - timedelta(days=30), motivo=6), cuando=HOY)
        assert codigos(salen) == {"REVOCACION-SUSPENDIDO"}
        assert salen[0].gravedad == AVISO
        assert "puede levantarse" in salen[0].mensaje

    def test_sin_fecha_de_firma_se_da_por_anulado(self):
        """Sin nada con que compararla, la anulación es lo único que se sabe."""
        salen = quejas(_linea(HOJA_SERIE), cuando=None)
        assert codigos(salen) == {"REVOCADO"}

    def test_una_lista_vencida_no_da_un_visto_bueno_limpio(self):
        salen = quejas(
            hasta=HOY - timedelta(days=5), hoy=HOY.date(), cuando=HOY - timedelta(days=40)
        )
        assert codigos(salen, AVISO) == {"REVOCACION-LISTA-VIEJA"}
        aviso = next(i for i in salen if i.codigo == "REVOCACION-LISTA-VIEJA")
        assert "no es lo mismo que estar vigente" in aviso.mensaje

    def test_una_lista_al_dia_y_limpia_declara_contra_que_ha_mirado(self):
        """No basta con callar. «No consta anulado» sin decir según qué lista y
        de qué día es un tic verde con más letras."""
        salen = quejas(hoy=HOY.date(), cuando=HOY - timedelta(days=40))
        assert codigos(salen, ERROR) == set()
        assert codigos(salen, AVISO) == set()
        assert codigos(salen, NOTA) == {"CONFIANZA-REVOCACION"}
        assert "CA intermedia" in salen[0].mensaje
        assert (HOY - timedelta(days=1)).date().isoformat() in salen[0].mensaje

    def test_una_sola_nota_por_firma_aunque_se_comprueben_varios(self):
        """En un lote de doscientas, una línea por cada eslabón de cada cadena
        deja de leerse; y lo que hay que poder leer es de qué día es la lista."""
        salen = quejas(hoy=HOY.date(), cuando=HOY - timedelta(days=40))
        assert len([i for i in salen if i.codigo == "CONFIANZA-REVOCACION"]) == 1
        assert "se ha comprobado 1 certificado" in salen[0].mensaje

    def test_si_esta_anulado_no_hay_nota_tranquilizadora(self):
        salen = quejas(_linea(HOJA_SERIE, HOY - timedelta(days=30)), cuando=HOY)
        assert codigos(salen, NOTA) == set()

    def test_una_autoridad_anulada_tambien_se_ve(self):
        """Si anulan la intermedia, todo lo que cuelga de ella deja de valer."""
        de_la_raiz = leer_lista(
            lista(emisor="Raiz de pruebas", clave_emisor=RAIZ, lineas=[_linea(2)])
        )
        salen = revocacion.reglas(
            [LA_HOJA, LA_INTERMEDIA, leer(raiz())], [de_la_raiz], cuando=HOY
        )
        # Salen dos cosas y las dos son ciertas: de la hoja no se sabe nada
        # —no tenemos ninguna lista de su emisor— y la intermedia está anulada.
        assert codigos(salen) == {"REVOCACION-SIN-COMPROBAR", "REVOCADO"}
        anulada = next(i for i in salen if i.codigo == "REVOCADO")
        assert anulada.gravedad == ERROR
        assert "por encima" in anulada.mensaje

    def test_el_ancla_no_se_mira(self):
        """Por encima de un ancla no hay nadie que pueda firmar una lista que
        la anule: para dejar de creerla se la saca del almacén."""
        assert revocacion.reglas([LA_HOJA], [], cuando=HOY) == []


# --- Dónde está la lista ---------------------------------------------------


class TestDondeBuscarla:
    def test_se_lee_la_direccion_que_da_el_certificado(self):
        con_punto = leer(
            hoja(extensiones=_puntos("http://pki.ejemplo.es/ca.crl"))
        )
        assert revocacion.donde_esta_la_lista(con_punto) == [
            "http://pki.ejemplo.es/ca.crl"
        ]

    def test_y_se_dice_en_el_aviso(self):
        con_punto = leer(hoja(extensiones=_puntos("http://pki.ejemplo.es/ca.crl")))
        salen = revocacion.reglas([con_punto, LA_INTERMEDIA], [], cuando=HOY)
        assert codigos(salen) == {"REVOCACION-SIN-COMPROBAR"}
        assert "http://pki.ejemplo.es/ca.crl" in salen[0].mensaje

    def test_una_autoridad_que_solo_ofrece_ocsp_se_dice_aparte(self):
        """No hay nada que instalar, y la única salida cuesta privacidad: hay
        que poder decirlo, no dejarlo en «no se ha comprobado»."""
        solo_ocsp = leer(hoja(extensiones=_acceso_ocsp("http://ocsp.ejemplo.es")))
        assert revocacion.donde_esta_el_ocsp(solo_ocsp) == ["http://ocsp.ejemplo.es"]
        salen = revocacion.reglas([solo_ocsp, LA_INTERMEDIA], [], cuando=HOY)
        assert codigos(salen) == {"REVOCACION-SOLO-OCSP"}
        assert "número de serie" in salen[0].mensaje

    def test_un_certificado_sin_direcciones_no_inventa_ninguna(self):
        assert revocacion.donde_esta_la_lista(LA_HOJA) == []
        assert revocacion.donde_esta_el_ocsp(LA_HOJA) == []


# --- El almacén ------------------------------------------------------------


class TestElAlmacen:
    def test_lee_una_carpeta(self, tmp_path):
        (tmp_path / "ca.crl").write_bytes(lista(lineas=[_linea(3)]))
        almacen = AlmacenDeListas(tmp_path)
        assert not almacen.vacio
        assert len(almacen.todas()) == 1
        assert almacen.de(LA_HOJA)[0].emisor_nombre == "CA intermedia"

    def test_tambien_en_pem(self, tmp_path):
        import base64

        crudo = base64.b64encode(lista()).decode()
        (tmp_path / "ca.pem").write_text(
            "-----BEGIN X509 CRL-----\n" + crudo + "\n-----END X509 CRL-----\n"
        )
        assert len(AlmacenDeListas(tmp_path).todas()) == 1

    def test_una_carpeta_que_no_existe_no_revienta(self, tmp_path):
        assert AlmacenDeListas(tmp_path / "no-esta").vacio

    def test_admite_una_ruta_de_texto(self, tmp_path):
        """`AlmacenDeListas("revocaciones")` es lo natural de escribir, y sin
        esto no reventaba hasta la primera consulta, en mitad de un lote."""
        (tmp_path / "ca.crl").write_bytes(lista())
        assert not AlmacenDeListas(str(tmp_path)).vacio

    def test_un_fichero_ilegible_se_dice_y_no_para_al_resto(self, tmp_path):
        (tmp_path / "buena.crl").write_bytes(lista())
        (tmp_path / "rota.crl").write_bytes(b"esto no es una lista")
        almacen = AlmacenDeListas(tmp_path)
        assert len(almacen.todas()) == 1
        assert len(almacen.ilegibles) == 1

    def test_el_inventario_dice_de_quien_y_hasta_cuando(self, tmp_path):
        (tmp_path / "ca.crl").write_bytes(lista(lineas=[_linea(3), _linea(4)]))
        texto = AlmacenDeListas(tmp_path).inventario()[0]
        assert "CA intermedia" in texto
        assert "2 anulado(s)" in texto
        assert (HOY + timedelta(days=30)).date().isoformat() in texto

    def test_el_inventario_marca_las_incrementales(self, tmp_path):
        (tmp_path / "ca.crl").write_bytes(lista(delta_de=1))
        assert "INCREMENTAL" in AlmacenDeListas(tmp_path).inventario()[0]


# --- Todo junto, sobre un documento ----------------------------------------


class TestElInforme:
    def test_una_factura_con_el_certificado_anulado(self, tmp_path):
        almacen = almacen_con(raiz(), tmp_path=tmp_path)
        listas = [leer_lista(lista(lineas=[_linea(HOJA_SERIE, HOY - timedelta(days=30))]))]
        salen = cadena.reglas(
            [LA_HOJA, LA_INTERMEDIA],
            almacen,
            cuando=HOY,
            listas=listas,
        )
        assert "REVOCADO" in codigos(salen)
        assert codigos(salen, ERROR) == {"REVOCADO"}

    def test_si_la_cadena_no_llega_no_se_habla_de_revocacion(self, tmp_path):
        """Preguntar si está anulado un certificado que no lleva a ninguna
        autoridad conocida es contestar a la pregunta equivocada."""
        almacen = almacen_con(raiz(), tmp_path=tmp_path)
        salen = cadena.reglas([LA_HOJA], almacen, cuando=HOY, listas=[])
        assert codigos(salen) == {"CADENA-DESCONOCIDA"}

    def test_sin_anclas_tampoco(self, tmp_path):
        salen = cadena.reglas([LA_HOJA], almacen_con(tmp_path=tmp_path), cuando=HOY)
        assert codigos(salen) == {"CADENA-SIN-ANCLAS"}

    def test_una_lista_que_venga_dentro_del_documento_vale(self, tmp_path):
        """XAdES-XL: la prueba viaja con la factura y no hay que salir a nada."""
        almacen = almacen_con(raiz(), tmp_path=tmp_path)
        dentro = [leer_lista(lista(lineas=[_linea(HOJA_SERIE, HOY - timedelta(days=30))]))]
        salen = cadena.reglas(
            [LA_HOJA, LA_INTERMEDIA],
            almacen,
            cuando=HOY,
            listas=[],
            listas_dentro=dentro,
        )
        assert "REVOCADO" in codigos(salen)


# --- Sobre facturas de verdad ----------------------------------------------


MUESTRAS = pytest.importorskip("pathlib").Path("MuestrasFE")


class TestSobreFacturasDeVerdad:
    @pytest.mark.skipif(
        not (MUESTRAS / "gob_sample-factura-firmada-30.xml").exists(),
        reason="hacen falta las muestras del Gobierno",
    )
    def test_la_del_ministerio_dice_donde_esta_su_lista(self):
        from lxml import etree

        raiz_xml = etree.parse(
            str(MUESTRAS / "gob_sample-factura-firmada-30.xml")
        ).getroot()
        cert = firma.certificados_de(firma.hay_firma(raiz_xml)[0])[0]
        assert revocacion.donde_esta_la_lista(cert) == [
            "http://minister-8jgxy9.mityc.age/PKI/crl.crl"
        ]

    @pytest.mark.skipif(
        not (MUESTRAS / "gob_sample-facturae-firmada.xsig.xml").exists(),
        reason="hacen falta las muestras del Gobierno",
    )
    def test_la_del_dnie_no_publica_lista_ninguna(self):
        """El caso que obliga a explicar lo del OCSP: con este certificado no
        hay forma de comprobar la revocación sin decirle a la autoridad qué se
        está mirando."""
        from lxml import etree

        raiz_xml = etree.parse(
            str(MUESTRAS / "gob_sample-facturae-firmada.xsig.xml")
        ).getroot()
        cert = firma.certificados_de(firma.hay_firma(raiz_xml)[0])[0]
        assert revocacion.donde_esta_la_lista(cert) == []
        assert revocacion.donde_esta_el_ocsp(cert) == ["http://ocsp.dnie.es"]


# --- Lo que se ve desde la consola -----------------------------------------


def _ancla_sin_fecha() -> bytes:
    """Un certificado por lo demás correcto cuya validez no se puede leer.

    No es rebuscado: basta un `GeneralizedTime` que no case con el formato
    —lo escribe cualquier herramienta que se salga de la norma— para que
    `Certificado.hasta` se quede en None.
    """
    import hashlib

    modulo, _ = RAIZ
    spki = _secuencia(
        _secuencia(
            _der(0x06, b"\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01"), _der(0x05, b"")
        ),
        _der(0x03, b"\x00" + _secuencia(_entero(modulo), _entero(65537))),
    )
    basura = _der(0x18, b"cuando sea")
    tbs = _secuencia(
        _der(0xA0, _entero(2)),
        _entero(99),
        _secuencia(_der(0x06, _OID_SHA256_RSA)),
        _nombre("Sin fecha legible"),
        _secuencia(basura, basura),
        _nombre("Sin fecha legible"),
        spki,
    )
    n, d = RAIZ
    tamanio = (n.bit_length() + 7) // 8
    di = firma._DIGESTINFO["sha256"] + hashlib.sha256(tbs).digest()
    relleno = b"\x00\x01" + b"\xff" * (tamanio - len(di) - 3) + b"\x00" + di
    valor = pow(int.from_bytes(relleno, "big"), d, n).to_bytes(tamanio, "big")
    return _secuencia(
        tbs, _secuencia(_der(0x06, _OID_SHA256_RSA)), _der(0x03, b"\x00" + valor)
    )


def factura_de_la_cadena(carpeta):
    """Un Facturae firmado por la hoja de la jerarquía de `test_cadena`."""
    from test_firma import documento

    ruta = carpeta / "factura.xml"
    ruta.write_bytes(
        documento(cert=hoja(), modulo=HOJA[0], privada=HOJA[1], firmado_el=HOY)
    )
    return ruta


class TestLaConsola:
    def test_ver_revocaciones_enseña_lo_que_hay(self, tmp_path, capsys):
        (tmp_path / "ca.crl").write_bytes(lista(lineas=[_linea(3)]))
        assert consola.main(["--revocaciones", str(tmp_path), "--ver-revocaciones"]) == 0
        salida = capsys.readouterr().out
        assert "CA intermedia" in salida
        assert "anulados  1" in salida

    def test_ver_revocaciones_sin_ninguna_dice_que_no_las_baja(self, tmp_path, capsys):
        assert consola.main(["--revocaciones", str(tmp_path), "--ver-revocaciones"]) == 2
        assert "no las baja solo" in capsys.readouterr().out

    def test_ver_revocaciones_avisa_de_las_vencidas(self, tmp_path, capsys):
        (tmp_path / "ca.crl").write_bytes(lista(hasta=HOY - timedelta(days=5)))
        consola.main(
            ["--revocaciones", str(tmp_path), "--ver-revocaciones", "--hoy", "2026-03-02"]
        )
        salida = capsys.readouterr().out
        assert "VENCIDA" in salida
        assert "no demuestra que un certificado siga vigente" in salida

    def test_ver_anclas_dice_cuando_caducan(self, tmp_path, capsys):
        """Es la respuesta a «¿y esto hay que mantenerlo?»: lo que se apaga es
        la caducidad, y hay que poder verla sin abrir el certificado."""
        (tmp_path / "raiz.cer").write_bytes(raiz())
        consola.main(["--anclas", str(tmp_path), "--ver-anclas", "--hoy", "2026-03-02"])
        salida = capsys.readouterr().out
        assert "caduca   2027-03-02" in salida
        assert "quedan" not in salida  # todavía queda más de un año

    def test_ver_anclas_avisa_de_las_que_se_apagan(self, tmp_path, capsys):
        (tmp_path / "raiz.cer").write_bytes(raiz())
        consola.main(["--anclas", str(tmp_path), "--ver-anclas", "--hoy", "2027-01-15"])
        salida = capsys.readouterr().out
        assert "quedan 46 días" in salida
        assert "consigue la nueva en la web de su autoridad" in salida

    def test_ver_anclas_aguanta_un_ancla_sin_fecha_legible(self, tmp_path, capsys):
        """Reventaba a media impresión, con la cabecera ya escrita.

        `hasta` se queda en None cuando la fecha del certificado no se puede
        leer, y ordenar por caducidad mezclaba entonces una fecha con hora y
        otra sin ella. Python se niega a comparar las dos, así que un solo
        fichero raro en la carpeta tiraba el listado entero.
        """
        (tmp_path / "buena.cer").write_bytes(raiz())
        (tmp_path / "rara.cer").write_bytes(_ancla_sin_fecha())
        assert consola.main(["--anclas", str(tmp_path), "--ver-anclas"]) == 0
        salida = capsys.readouterr().out
        assert "Raiz de pruebas" in salida
        assert "no se ha podido leer" in salida

    def test_ver_anclas_avisa_de_las_ya_caducadas(self, tmp_path, capsys):
        (tmp_path / "raiz.cer").write_bytes(raiz())
        consola.main(["--anclas", str(tmp_path), "--ver-anclas", "--hoy", "2028-01-15"])
        assert "YA CADUCADA" in capsys.readouterr().out

    def test_con_anclas_y_sin_listas_se_recuerda_al_final(self, tmp_path, capsys):
        anclas = tmp_path / "anclas"
        anclas.mkdir()
        (anclas / "raiz.cer").write_bytes(raiz())
        (anclas / "intermedia.cer").write_bytes(intermedia())
        facturas = tmp_path / "facturas"
        facturas.mkdir()
        factura_de_la_cadena(facturas)
        consola.main(
            [str(facturas), "--anclas", str(anclas), "--revocaciones", str(tmp_path / "no-hay")]
        )
        salida = capsys.readouterr().out
        assert "no hay listas de revocación" in salida

    def test_sin_anclas_no_se_pide_el_segundo_paso_antes_que_el_primero(
        self, tmp_path, capsys
    ):
        """Sin anclas no se sabe ni de quién es el certificado. Echar de menos
        además su lista de revocación sería ruido: el primer paso es otro."""
        facturas = tmp_path / "facturas"
        facturas.mkdir()
        factura_de_la_cadena(facturas)
        consola.main(
            [
                str(facturas),
                "--anclas",
                str(tmp_path / "no-hay"),
                "--revocaciones",
                str(tmp_path / "tampoco"),
            ]
        )
        salida = capsys.readouterr().out
        assert "no hay anclas de confianza" in salida
        assert "no hay listas de revocación" not in salida

    def test_el_alcance_cambia_segun_haya_listas(self, tmp_path):
        from validador import factura as modulo

        facturas = tmp_path / "facturas"
        facturas.mkdir()
        factura_de_la_cadena(facturas)
        anclas = tmp_path / "anclas"
        anclas.mkdir()
        (anclas / "raiz.cer").write_bytes(raiz())
        (anclas / "intermedia.cer").write_bytes(intermedia())
        lote = modulo.validar_lote(
            sorted(facturas.iterdir()),
            almacen=cadena.Almacen(anclas),
            listas=AlmacenDeListas(tmp_path / "no-hay"),
        )
        con = lote.alcance(anclas=True, listas=True)
        sin = lote.alcance(anclas=True, listas=False)
        assert "que no lo hayan anulado" in con
        assert "que no lo hayan anulado" not in sin
        assert "hace falta la lista de revocación" in sin


# --- Fuera del círculo -----------------------------------------------------


@pytest.mark.skipif(shutil.which("openssl") is None, reason="hace falta openssl")
def test_una_lista_hecha_por_openssl_se_lee_igual(tmp_path):
    """La única prueba de este fichero que no se la escribe a sí misma.

    Todas las demás usan el codificador de arriba, escrito por la misma mano
    que el lector: si los dos comparten un malentendido sobre el DER, se dan la
    razón y no se enteran. `openssl` no comparte nada, así que si su CRL se lee
    igual que su `openssl crl -text`, el lector entiende el formato de verdad.
    """
    conf = tmp_path / "ca.cnf"
    conf.write_text(
        "[ca]\ndefault_ca=CA\n\n[CA]\ndir=.\ndatabase=./indice.txt\n"
        "new_certs_dir=./nuevos\ncertificate=./ca.crt\nserial=./serie\n"
        "crlnumber=./crlnum\nprivate_key=./ca.key\ndefault_days=3650\n"
        "default_crl_days=30\ndefault_md=sha256\npolicy=politica\n"
        "email_in_dn=no\nunique_subject=no\n\n[politica]\ncommonName=supplied\n\n"
        "[req]\ndistinguished_name=dn\nprompt=no\n\n[dn]\nCN=CA de pruebas\n\n"
        "[v3_ca]\nbasicConstraints=critical,CA:true\n"
        "keyUsage=critical,keyCertSign,cRLSign\n\n"
        "[v3_hoja]\nbasicConstraints=CA:false\nkeyUsage=critical,digitalSignature\n"
        "crlDistributionPoints=URI:http://pki.ejemplo.invalid/ca.crl\n",
        encoding="ascii",
    )
    (tmp_path / "nuevos").mkdir()
    (tmp_path / "indice.txt").write_text("")
    (tmp_path / "serie").write_text("1000\n")
    (tmp_path / "crlnum").write_text("1000\n")

    def openssl(*orden):
        return subprocess.run(
            ["openssl", *orden],
            cwd=tmp_path,
            capture_output=True,
            check=True,
        )

    openssl("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "ca.key",
            "-out", "ca.crt", "-days", "7300", "-config", "ca.cnf",
            "-extensions", "v3_ca")
    openssl("req", "-newkey", "rsa:2048", "-nodes", "-keyout", "hoja.key",
            # Una sola barra: la doble es el apaño de MSYS para que su shell no
            # convierta el argumento en una ruta, y aquí no hay shell de por
            # medio —`subprocess` llama al ejecutable directamente—.
            "-out", "hoja.csr", "-subj", "/CN=Hoja de pruebas")
    openssl("ca", "-batch", "-config", "ca.cnf", "-extensions", "v3_hoja",
            "-in", "hoja.csr", "-out", "hoja.crt")
    openssl("ca", "-config", "ca.cnf", "-revoke", "hoja.crt",
            "-crl_reason", "keyCompromise")
    openssl("ca", "-config", "ca.cnf", "-gencrl", "-out", "ca.crl")

    def pem(nombre, marca):
        datos = (tmp_path / nombre).read_bytes()
        import base64

        patron = ("-----BEGIN %s-----(.*?)-----END %s-----" % (marca, marca)).encode()
        return base64.b64decode(re.search(patron, datos, re.S).group(1))

    ca = firma.leer_certificado(pem("ca.crt", "CERTIFICATE"))
    la_hoja = firma.leer_certificado(pem("hoja.crt", "CERTIFICATE"))
    una = leer_lista(pem("ca.crl", "X509 CRL"))

    # Lo que dice `openssl crl -text`, comprobado campo a campo.
    assert una.emisor_nombre == "CA de pruebas"
    assert una.numero == 4096  # 0x1000, el que se dejó en ./crlnum
    assert una.hasta is not None and una.desde is not None
    assert not una.es_delta and not una.parcial
    assert set(una.anulaciones) == {la_hoja.serie}
    assert una.anulaciones[la_hoja.serie].motivo == 1

    # Y que su firma la comprueba nuestra propia aritmética.
    assert comprobar(la_hoja, ca, [una]).estado == "anulado"
    assert revocacion.donde_esta_la_lista(la_hoja) == [
        "http://pki.ejemplo.invalid/ca.crl"
    ]


# --- Las respuestas OCSP que trae el documento -----------------------------
#
# `test_ocsp.py` prueba que se leen y que se verifican. Lo que se prueba aquí
# es lo otro, que es lo que ve quien valida una factura: que el informe las
# consulta, que las trata con las mismas reglas de fecha que a una CRL, y que
# ninguna de las maneras de no valer se convierte en un tic verde.
#
# La fábrica es la de `test_ocsp`, apuntada a la jerarquía de este fichero: la
# hoja es «Talleres Paco SL» con serie 3, y quien la emitió —y por tanto quien
# puede responder por ella— es «CA intermedia».


def _respuesta(
    estado=BUENO, mirada=None, quien="CA intermedia", clave=INTERMEDIA, serie=3,
    hasta=None,
):
    """Una respuesta OCSP sobre la hoja de este fichero, ya troceada."""
    single = _single(
        _certid("CA intermedia", INTERMEDIA, serie), estado,
        mirada=mirada or HOY, hasta=hasta,
    )
    return ocsp.leer_respuesta(
        _envuelta(_basica([single], quien, clave))
    )


def con_ocsp(*respuestas, listas=(), cuando=None, hoy=None):
    return revocacion.reglas(
        [LA_HOJA, LA_INTERMEDIA, leer(raiz())],
        list(listas),
        cuando=cuando,
        hoy=hoy,
        respuestas_ocsp=list(respuestas),
    )


class TestElInformeConsultaElOcsp:
    def test_una_respuesta_buena_cierra_la_pregunta(self):
        """Sin ninguna CRL, y aun así no queda nada por comprobar."""
        salen = con_ocsp(_respuesta(), cuando=HOY - timedelta(days=1))
        assert codigos(salen, ERROR) == set()
        assert codigos(salen, AVISO) == set()
        assert codigos(salen, NOTA) == {"CONFIANZA-REVOCACION"}

    def test_y_dice_de_dónde_salió_lo_que_afirma(self):
        """«No consta anulado» sin decir según qué prueba y de qué día es un
        tic verde con más letras, igual que con las listas."""
        salen = con_ocsp(_respuesta(), cuando=HOY - timedelta(days=1))
        assert "respuesta OCSP" in salen[0].mensaje
        assert "CA intermedia" in salen[0].mensaje
        assert HOY.date().isoformat() in salen[0].mensaje
        # Y que no promete de hoy lo que solo sabe de aquel día.
        assert "no cómo está hoy" in salen[0].mensaje

    def test_anulado_antes_de_firmar_es_error(self):
        salen = con_ocsp(
            _respuesta(_anulado_ocsp(HOY - timedelta(days=30))), cuando=HOY
        )
        assert codigos(salen) == {"REVOCADO"}
        assert salen[0].gravedad == ERROR
        assert "respuesta OCSP" in salen[0].encontrado

    def test_anulado_por_clave_robada_sigue_siendo_error_hacia_atrás(self):
        """El motivo pesa más que la fecha, venga de una lista o de aquí."""
        salen = con_ocsp(
            _respuesta(_anulado_ocsp(HOY, motivo=1)), cuando=HOY - timedelta(days=90)
        )
        assert codigos(salen) == {"REVOCACION-COMPROMISO"}
        assert salen[0].gravedad == ERROR

    def test_anulado_después_de_firmar_es_aviso(self):
        salen = con_ocsp(
            _respuesta(_anulado_ocsp(HOY - timedelta(days=1))),
            cuando=HOY - timedelta(days=30),
        )
        assert codigos(salen) == {"REVOCACION-POSTERIOR"}
        assert salen[0].gravedad == AVISO

    def test_un_no_lo_sé_no_es_un_visto_bueno(self):
        """«unknown» es el fallo que caería del lado peligroso."""
        salen = con_ocsp(_respuesta(SIN_SABER), cuando=HOY - timedelta(days=1))
        assert codigos(salen) == {"REVOCACION-OCSP-NO-VALE"}
        assert codigos(salen, NOTA) == set()
        assert "unknown" in salen[0].mensaje

    def test_una_respuesta_firmada_por_otro_no_vale(self):
        """Es la que importa: la respuesta la mete quien firma el documento, y
        sin comprobarla cualquiera adjunta un «está perfectamente» suyo."""
        salen = con_ocsp(
            _respuesta(quien="CA intermedia", clave=INTRUSO),
            cuando=HOY - timedelta(days=1),
        )
        assert codigos(salen) == {"REVOCACION-OCSP-NO-VALE"}
        assert codigos(salen, NOTA) == set()

    def test_una_respuesta_de_otro_certificado_no_lo_cubre(self):
        """Mismo emisor, otra serie: no habla de este."""
        salen = con_ocsp(_respuesta(serie=999), cuando=HOY - timedelta(days=1))
        assert codigos(salen) == {"REVOCACION-OCSP-NO-VALE"}
        assert "ninguna" in salen[0].mensaje

    def test_una_respuesta_anterior_sin_plazo_no_dice_nada_de_la_firma(self):
        """Se miró antes de firmar y el respondedor no dijo hasta cuándo valía,
        que es su manera de pedir que no se guarde."""
        salen = con_ocsp(
            _respuesta(mirada=HOY - timedelta(days=30)), cuando=HOY
        )
        assert codigos(salen) == {"REVOCACION-OCSP-NO-VALE"}
        assert "30 días antes de esta firma" in salen[0].mensaje
        assert "no dijo hasta cuándo" in salen[0].mensaje

    def test_una_respuesta_anterior_pero_todavía_vigente_sí_vale(self):
        """El caso de verdad, medido: en `78353__XAdES_A_Detached.xml` la
        respuesta se pidió 27 segundos antes de la firma y se daba por vigente
        cuatro horas. Así se hace un XAdES-XL —preguntar, firmar, sellar—, y
        tratarlo como «no se sabe» levantaría el aviso en casi toda factura
        archivada. Quien dice que seguía valiendo no es este validador: es el
        respondedor, con su `nextUpdate`."""
        salen = con_ocsp(
            _respuesta(
                mirada=HOY - timedelta(seconds=27),
                hasta=HOY + timedelta(hours=4),
            ),
            cuando=HOY,
        )
        assert codigos(salen, AVISO) == set()
        assert codigos(salen, NOTA) == {"CONFIANZA-REVOCACION"}
        # Y la nota tiene que decir sobre qué se aceptó, no callarlo.
        assert "27 segundos antes de la firma" in salen[0].mensaje
        assert "el propio respondedor la daba por vigente hasta" in salen[0].mensaje

    def test_una_respuesta_anterior_y_ya_caducada_no_vale(self):
        """Si el plazo que se dio a sí misma acabó antes de la firma, no llega
        hasta ella y volvemos a no saber."""
        salen = con_ocsp(
            _respuesta(
                mirada=HOY - timedelta(days=3), hasta=HOY - timedelta(days=2)
            ),
            cuando=HOY,
        )
        assert codigos(salen) == {"REVOCACION-OCSP-NO-VALE"}
        assert "solo la daba por vigente hasta" in salen[0].mensaje

    def test_una_ilegible_no_pasa_por_no_haber_traído_nada(self):
        """Un documento con una respuesta rota no es un documento sin pruebas,
        y decir «no tenemos ninguna lista de esa autoridad» sería falso."""
        rota = ocsp.Respuesta(
            estado_global=-1, ilegible="el base64 no se descodifica"
        )
        salen = con_ocsp(rota, cuando=HOY)
        assert codigos(salen) == {"REVOCACION-OCSP-NO-VALE"}
        assert "no se pudo ni abrir" in salen[0].mensaje

    def test_sin_respuestas_el_aviso_es_el_de_siempre(self):
        """Que exista el camino nuevo no puede cambiar el viejo."""
        salen = revocacion.reglas(
            [LA_HOJA, LA_INTERMEDIA, leer(raiz())], [], cuando=HOY
        )
        assert codigos(salen) == {"REVOCACION-SIN-COMPROBAR"}


class TestCuandoLasDosPruebasNoDicenLoMismo:
    """Una CRL y una respuesta OCSP contestan lo mismo y pueden discrepar.

    La regla es la que `comprobar` ya aplica entre dos CRL: manda la más nueva
    de las que contestan. Y tiene el mismo motivo, que no es la comodidad sino
    las suspensiones: una que se levanta desaparece de la prueba siguiente, así
    que quedarse con la vieja resucitaría una anulación que ya no existe.
    """

    def test_una_acusación_nueva_gana_a_una_lista_limpia_vieja(self):
        # Las dos se contradicen a propósito: una lista publicada después de
        # la firma y sin la hoja dentro, y una respuesta más nueva que dice que
        # se anuló antes. Es artificial, y es la única forma de fijar la regla
        # sin que se cuele la coincidencia.
        limpia = leer_lista(lista(lineas=[], desde=HOY - timedelta(days=10)))
        salen = con_ocsp(
            _respuesta(_anulado_ocsp(HOY - timedelta(days=30)), mirada=HOY),
            listas=[limpia],
            cuando=HOY - timedelta(days=20),
        )
        assert codigos(salen) == {"REVOCADO"}

    def test_y_un_visto_bueno_nuevo_gana_a_una_acusación_vieja(self):
        """Es el caso de la suspensión levantada, y por eso no se puede
        contestar «lo que acuse, gana»: se rechazaría una factura buena."""
        acusa = leer_lista(
            lista(
                lineas=[_linea(HOJA_SERIE, HOY - timedelta(days=50), motivo=6)],
                desde=HOY - timedelta(days=40),
            )
        )
        salen = con_ocsp(
            _respuesta(mirada=HOY - timedelta(days=1)),
            listas=[acusa],
            cuando=HOY - timedelta(days=2),
        )
        assert codigos(salen, ERROR) == set()
        assert codigos(salen, AVISO) == set()
        assert codigos(salen, NOTA) == {"CONFIANZA-REVOCACION"}

    def test_y_al_revés_también_manda_la_lista_si_es_la_nueva(self):
        """La simétrica de la anterior, y no sobra: sin ella, «se queda con la
        respuesta OCSP» y «se queda con la prueba más nueva» dan lo mismo en
        todas las pruebas del fichero, que es como una regla se convierte en
        una casualidad que nadie vigila."""
        acusa = leer_lista(
            lista(
                lineas=[_linea(HOJA_SERIE, HOY - timedelta(days=50))],
                desde=HOY - timedelta(days=5),
            )
        )
        salen = con_ocsp(
            _respuesta(mirada=HOY - timedelta(days=30)),
            listas=[acusa],
            cuando=HOY - timedelta(days=40),
        )
        assert codigos(salen) == {"REVOCADO"}
        assert "según la lista de" in salen[0].encontrado

    def test_si_ninguna_sabe_se_cuenta_lo_del_ocsp_y_dónde_bajar_la_lista(self):
        """Las dos cosas son ciertas y las dos hacen falta: por qué no sirvió
        lo que traía el documento, y qué se puede instalar para saberlo."""
        con_punto = leer(hoja(extensiones=_puntos("http://pki.ejemplo.es/ca.crl")))
        salen = revocacion.reglas(
            [con_punto, LA_INTERMEDIA],
            [],
            cuando=HOY,
            respuestas_ocsp=[_respuesta(SIN_SABER)],
        )
        assert codigos(salen) == {"REVOCACION-OCSP-NO-VALE"}
        assert "unknown" in salen[0].mensaje
        assert "http://pki.ejemplo.es/ca.crl" in salen[0].mensaje
