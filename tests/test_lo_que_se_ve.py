"""Lo que se lee de un fichero no puede hacerse pasar por otra cosa al verse.

Salió del escaneo de seguridad del 01 al 03-11-2026 y lo cuenta HALLAZGOS. Son
dos sitios donde el validador y quien mira no ven lo mismo:

- **El servidor del QR fiscal.** Se leía con `urlsplit(...).hostname`, que corta
  el servidor solo en `/ ? #` y se queda con lo que va detrás de la última `@`.
  Un navegador, según la norma URL de WHATWG, trata la barra invertida como `/`
  en https: `https://atacante.example\\@www2.agenciatributaria.gob.es/...` es
  la AEAT para el validador y `atacante.example` para quien la abre.
  Reproducido el 08-11-2026 sobre `5998df7`: esa dirección, una con usuario
  delante y una con el puerto 8443 salían sin una queja.
- **La terminal.** Lo que el EDIFACT trae fuera del árbol XML, como la
  referencia del UNB, no pasa por lxml, que es quien rechaza los caracteres de
  control en el resto, y se imprimía tal cual. Reproducido el mismo día: una
  referencia con `ESC [2J` y `ESC ] 0;título BEL` llegaba entera a la salida,
  y con ella se borra la pantalla o se cambia el título de la ventana.
"""

from __future__ import annotations

from datetime import date

import pytest

from validador import __main__ as consola
from validador import qr_fiscal
from validador.incidencias import AVISO

from test_edifact import CUERPO, sobre

CONSULTA = "?nif=B12345674&numserie=F-2026-0101&fecha=06-10-2026&importe=121.00"
RUTA = "/wlpl/TIKE-CONT/ValidarQR"
LA_FACTURA = {"nifs_del_vendedor": {"B12345674"}, "numero": "F-2026-0101",
              "fecha": date(2026, 10, 6), "total": "121.00", "moneda": "EUR"}


def revisar(direccion: str):
    return qr_fiscal.revisar(direccion, "VERIFACTU", **LA_FACTURA)


class TestElServidorDelQr:
    def test_la_de_la_aeat_sigue_sin_queja(self):
        assert revisar(f"https://www2.agenciatributaria.gob.es{RUTA}{CONSULTA}") == []

    def test_el_servidor_en_mayusculas_sigue_siendo_el_mismo(self):
        # Los nombres de servidor no distinguen mayúsculas, ni aquí ni en un
        # navegador: esto no es una dirección trucada.
        assert revisar(f"https://WWW2.AgenciaTributaria.gob.es{RUTA}{CONSULTA}") == []

    @pytest.mark.parametrize("delante", [
        # El caso del escaneo: el navegador abre atacante.example.
        "atacante.example\\@www2.agenciatributaria.gob.es",
        # Un usuario delante. Aquí sí coinciden los dos en el servidor, pero
        # una dirección con usuario no es la que publica nadie, y es la forma
        # de esconder el servidor de verdad al final de una tira larga.
        "www2.agenciatributaria.gob.es@www2.agenciatributaria.gob.es",
        "atacante@www2.agenciatributaria.gob.es",
        # Un puerto que no es el de https: otro servicio en la misma máquina.
        "www2.agenciatributaria.gob.es:8443",
        # Y el de https escrito a mano: es el mismo servidor, pero ninguna de
        # las direcciones publicadas lo escribe, y aceptarlo pediría decidir
        # qué más se normaliza. Mejor un aviso de más que uno de menos.
        "www2.agenciatributaria.gob.es:443",
    ])
    def test_lo_que_va_junto_al_servidor_no_cuela(self, delante):
        quejas = revisar(f"https://{delante}{RUTA}{CONSULTA}")
        assert len(quejas) == 1, quejas
        assert quejas[0].codigo == "SPFE-QR-URL" and quejas[0].gravedad == AVISO
        assert "no se han comparado" in quejas[0].mensaje
        assert quejas[0].encontrado == delante

    def test_tambien_con_las_haciendas_forales(self):
        quejas = qr_fiscal.revisar(
            "https://atacante.example\\@batuz.eus/QRTBAI/?id=TBAI-00000006Y-251019-"
            "btFpwP8dcLGAF-237&s=T&nf=27174&i=4.70&cr=007", "TICKETBAI",
            nifs_del_vendedor={"00000006Y"}, numero="T27174",
            fecha=date(2019, 10, 25), total="4.70", moneda="EUR")
        assert [q.codigo for q in quejas] == ["SPFE-QR-URL"]
        assert "no se han comparado" in quejas[0].mensaje


# La referencia del UNB con tres cosas que una terminal obedece: borrar la
# pantalla, cambiar el título (OSC acabado en BEL) y el CSI de un solo byte,
# 0x9B, que en UNOC (latin-1) llega como U+009B.
TRUCO = b"\x1b[2J\x1b]0;titulo\x07\x9b2J"


def _salida(tmp_path, capsys) -> str:
    tira = sobre(CUERPO).replace(b"+260819:1200+1'", b"+260819:1200+1" + TRUCO + b"'", 1)
    ruta = tmp_path / "escape.edi"
    ruta.write_bytes(tira)
    consola.main([str(ruta), "--hoy", "2026-11-08"])
    return capsys.readouterr().out


class TestLaTerminal:
    def test_la_referencia_llega_al_informe(self, tmp_path, capsys):
        # Control: sin esto, que no salga ningún carácter de control podría
        # deberse a que la referencia ya no se imprime, y la prueba de abajo
        # no estaría mirando nada.
        assert "EDI-SOBRE-DESCUADRADO" in _salida(tmp_path, capsys)

    def test_ningun_caracter_de_control_llega_a_la_terminal(self, tmp_path, capsys):
        salida = _salida(tmp_path, capsys)
        sueltos = sorted({hex(ord(c)) for c in salida
                          if (ord(c) < 0x20 and c not in "\n\t") or 0x7F <= ord(c) <= 0x9F})
        assert sueltos == []

    def test_se_ven_escritos(self, tmp_path, capsys):
        salida = _salida(tmp_path, capsys)
        assert "\\x1b[2J\\x1b]0;titulo\\x07\\x9b2J" in salida

    def test_ningun_separador_parte_la_linea(self, tmp_path, capsys):
        # Visto en una terminal de verdad el 08-11-2026: el retorno de carro no
        # salía como \x0d sino como una línea nueva, con su sangría, porque
        # `_sangrar` partía con `splitlines()`, que corta también en \r, \x0b,
        # \x0c, \x1c a \x1e y \x85. La queja ya no borraba nada, pero la
        # factura podía añadir líneas que parecieran del informe.
        tira = sobre(CUERPO).replace(
            b"+260819:1200+1'", b"+260819:1200+1\rA\x0bB\x0cC\x1cD\x1dE\x1eF\x85G'", 1)
        ruta = tmp_path / "separadores.edi"
        ruta.write_bytes(tira)
        consola.main([str(ruta), "--hoy", "2026-11-08"])
        lineas = capsys.readouterr().out.split("\n")
        deberia = [l for l in lineas if "Debería ser: 1" in l]
        assert deberia == [
            "    Debería ser: 1\\x0dA\\x0bB\\x0cC\\x1cD\\x1dE\\x1eF\\x85G"], deberia

    def test_lo_demas_queda_igual(self):
        texto = "Línea uno\n\tcon tabulador, ñ, €, ¿? y un 1E+3"
        assert consola.a_la_vista(texto) == texto

    @pytest.mark.parametrize("caracter, visto", [
        ("\x00", "\\x00"), ("\r", "\\x0d"), ("\x1b", "\\x1b"), ("\x7f", "\\x7f"),
        ("\x85", "\\x85"), ("\x9b", "\\x9b"), ("\x9f", "\\x9f"),
    ])
    def test_cada_uno_se_escribe(self, caracter, visto):
        assert consola.a_la_vista(f"a{caracter}b") == f"a{visto}b"
