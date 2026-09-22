"""El vigilante de la descarga, en `web/glosa.js`.

Aquí no hay Node, así que el JavaScript no se ejecuta en la suite: lo que se
comprueba es que el vigilante **sigue escrito** y que sigue siendo de bytes y
no de reloj. La prueba de verdad se hizo en el navegador el 09-09-2026 y las
cifras están abajo, porque una prueba de texto que no diga qué se midió es
justo la clase de verde que este repositorio no se cree.

Lo que se midió, sobre el sitio montado en local:

| Caso                                             | Qué hizo                |
|--------------------------------------------------|-------------------------|
| Carga sana                                       | «Listo en 7,80 s»       |
| Conexión muerta (petición abierta, cero bytes)   | `SinDescarga` a los 30 s|
| Conexión lenta (un trozo cada 9 s, 37 s en total)| arrancó bien            |
| La página, con la conexión muerta                | «No ha arrancado»       |

El tercero es el que manda. Un límite de tiempo habría cortado esa carga a los
30 s, y esa carga era buena: el arranque desde la conexión del autor tarda 78 s
en producción, con 41 s solo de intérprete. Por eso se cuentan bytes.

Y contar bytes tampoco bastaba, porque **el que cuenta también se para**. El
22-09-2026 el vigilante tumbó un arranque bueno, y se reprodujo dos veces con
el sitio servido por un tubo de 30 KB/s: se cayó a los 494 s diciendo que no
llegaba ni un byte cuando el servidor llevaba escritos 1.566.927 de los
1.637.748 del wheel de lxml. La pestaña estaba de fondo y sus tics, que venían
cada 2 s, se espaciaron 46 s y 60 s: Chrome aprieta los temporizadores de una
página oculta hasta uno por minuto. Lo que se paró fue el vigilante.

De ahí la tercera regla: **solo puede jurar por el tiempo en que estuvo
mirando**. Lo de después, medido igual:

| Caso                                              | Antes           | Después          |
|---------------------------------------------------|-----------------|------------------|
| El sitio entero a 30 KB/s, pestaña de fondo       | se cae a 494 s  | «Listo en 575,41 s» |
| Conexión muerta                                   | salta a 30,4 s  | salta a 30,2 s   |
| Muerta tras 20 s con el hilo atascado             | salta a 50,8 s  | salta a 52,0 s   |
| Lenta pero viva (1,2 MB a 25 KB/s)                | no salta        | no salta         |

Las tres últimas son las que importan: enseñan que el perdón de las lagunas no
ha apagado la negativa, que es lo que hay que demostrar al tocar un guardián.
El porqué entero, en `HALLAZGOS.md`.
"""

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parent.parent
GLOSA_JS = RAIZ / "web" / "glosa.js"


def _codigo() -> str:
    return GLOSA_JS.read_text(encoding="utf-8")


class TestElVigilanteSigueAhi:
    """Que no se caiga en una limpieza sin que nadie se entere."""

    def test_existe_la_negativa(self):
        codigo = _codigo()
        assert "class SinDescarga extends Error" in codigo
        assert "new SinDescarga(" in codigo, (
            "SinDescarga está declarada pero no se lanza en ningún sitio: "
            "una negativa que no se llega a dar no es una negativa"
        )

    def test_el_arranque_pasa_por_el_vigilante(self):
        codigo = _codigo()
        assert "return conVigilante(() => arrancarDeVerdad(avisar));" in codigo, (
            "`arrancar` ya no delega en `conVigilante`: el arranque volvería a "
            "poder quedarse colgado sin decirlo"
        )

    def test_se_cuentan_bytes_y_no_segundos(self):
        """La condición lleva `abiertas > 0`, y esa mitad es la que importa.

        Sin ella el vigilante saltaría mientras se compila el `.wasm`, que es
        un rato largo sin red y sin nada roto.
        """
        codigo = _codigo()
        assert re.search(
            r"abiertas > 0 && ahora - ultimoByte > SIN_BYTES", codigo
        ), "la condición ya no exige que haya una petición abierta"

    def test_la_respuesta_de_pyodide_no_se_toca(self):
        """Se cuenta sobre `clone()`, no sobre lo que se devuelve.

        Reconstruir la respuesta deja a `instantiateStreaming` sin su
        `content-type` y cambia un fallo silencioso por otro.
        """
        codigo = _codigo()
        assert "contar(respuesta.clone());" in codigo
        assert "return respuesta;" in codigo

    def test_el_fetch_bueno_se_devuelve(self):
        """Si el vigilante se queda puesto, la página valida con él para siempre."""
        codigo = _codigo()
        assert "globalThis.fetch = deVerdad;" in codigo
        assert "} finally {" in codigo

    def test_el_limite_es_el_medido(self):
        codigo = _codigo()
        assert "const SIN_BYTES = 30000;" in codigo, (
            "si se cambia el límite hay que volver a medir los tres casos del "
            "encabezado de este fichero, no solo el número"
        )


class TestAlAbandonarSeAbandonaDeVerdad:
    """Punto 22 de la auditoría, medido el 20-09-2026 y peor de lo que parecía.

    `Promise.race` no para al que pierde. El vigilante saltaba, la página
    pintaba «No ha arrancado»... y la descarga seguía por detrás.

    Provocado con un servidor que sirve el sitio y se atasca a propósito:
    manda 64 KB de `python_stdlib.zip`, se calla 45 s y después intenta
    escribir el resto. Lo que se mide es si el cliente sigue al otro lado.

    | | Antes | Después |
    |---|---|---|
    | El vigilante salta | a los 30 s | a los 30 s |
    | Lo que se bajó después de «No ha arrancado» | lxml, el wheel, el paquete y los diez ejemplos: unos 5 MB | nada |
    | `Glosa.validarEjemplo()` con la zona apagada | devolvía el informe entero | `pyodide` es `null` |

    Lo segundo es lo que convierte esto en el fallo de esta casa y no en un
    desperdicio de ancho de banda: lo que había en pantalla no era lo que
    estaba pasando.

    **Lo que no hace**, porque se midió y conviene no prometerlo: la petición
    que estaba en vuelo no se corta del lado del servidor. Al escribir el resto
    a los 45 s, el servidor no ve ningún error —Chrome se traga lo que quedaba
    para poder reutilizar la conexión—. Lo que se para es la cadena: esa
    respuesta ya no va a ninguna parte y detrás de ella no se pide nada más.
    """

    def test_hay_un_mando_para_abandonar(self):
        codigo = _codigo()
        assert "const mando = new AbortController();" in codigo
        assert "mando.abort(error);" in codigo, (
            "el vigilante avisa y no abandona: sin `abort`, todo lo demás es "
            "un cartel"
        )

    def test_la_senial_va_en_cada_peticion(self):
        codigo = _codigo()
        assert "signal: mando.signal" in codigo
        assert "AbortSignal.any([suya, mando.signal])" in codigo, (
            "quien traiga su propia señal se quedaría sin ella"
        )

    def test_el_fetch_bueno_se_devuelve_cuando_acaba_la_faena(self):
        """Y no cuando acaba la carrera, que es antes.

        Devolviéndolo en el `finally` de la carrera, lo que siguiera bajando
        después ya no pasaba por el vigilante y no lo contaba nadie.
        """
        codigo = _codigo()
        assert "const enMarcha = faena();" in codigo
        assert re.search(
            r"enMarcha\s*\n\s*\.finally\(\(\) => \{\s*\n\s*clearInterval\(reloj\);"
            r"\s*\n\s*globalThis\.fetch = deVerdad;", codigo
        ), "el `fetch` bueno ya no se devuelve al acabar la faena"


class TestElVigilanteNoJuraPorLoQueNoVio:
    """El fallo del 22-09-2026: se durmió y condenó lo que pasó mientras.

    Reproducido dos veces con el sitio servido a 30 KB/s y la pestaña de fondo.
    El servidor llevaba escritos 1.566.927 de los 1.637.748 bytes del wheel
    cuando la página dijo que no llegaba ninguno; de esa petición no había
    llegado ni la cabecera, y los tics del vigilante se habían espaciado 46 s y
    60 s. Con el arreglo, ese mismo arranque termina: «Listo en 575,41 s».

    Lo que no se toca al mirar esto: la sospecha apuntada era el `clone()` con
    que se cuentan los bytes, y **era falsa**. Medido: con la respuesta
    original sin leer, la rama clonada recibió 1.600.000 bytes con un hueco
    máximo de 0,13 s, y doce megas con 0,10 s.
    """

    def test_una_laguna_no_cuenta_como_silencio(self):
        """Cada tic mide su propio retraso, y lo que no vio no lo jura.

        Es la pieza del arreglo. Sin ella vuelve el fallo entero: basta que el
        navegador aparte la página un rato —de fondo, o con el hilo ocupado
        instanciando el `.wasm`— para que al volver le parezca que la conexión
        lleva medio minuto muerta.
        """
        codigo = _codigo()
        assert "const tardanza = ahora - ultimoTic;" in codigo, (
            "el tic ya no mide cuánto ha tardado en llegar: sin eso, una "
            "laguna del navegador es indistinguible de una conexión cortada"
        )
        assert re.search(r"if \(tardanza > DORMIDO\) \{", codigo), (
            "ya no se perdona la laguna"
        )

    def test_el_perdon_esta_topado(self):
        """Y topado en ahora mismo, o sería inmunidad a plazos.

        Si un byte entra justo al despertar, `ultimoByte` ya es de hace un
        instante; sumarle la laguna entera lo dejaría en el futuro y el
        vigilante se quedaría ciego lo que durase ese crédito.
        """
        codigo = _codigo()
        assert "ultimoByte = Math.min(ahora, ultimoByte + tardanza - CADA);" in codigo, (
            "el perdón ya no está topado: una laguna larga dejaría al "
            "vigilante sin mirar durante todo lo que se le regale"
        )

    def test_no_se_juzga_en_el_tic_de_la_laguna(self):
        """Se sale del tic, para que entre lo que estaba esperando.

        Las respuestas que el navegador tenía guardadas llegan en cuanto la
        página vuelve a correr; si se juzga en ese mismo tic, se juzga antes de
        que entren.
        """
        codigo = _codigo()
        laguna = codigo.index("if (tardanza > DORMIDO) {")
        juicio = codigo.index("abiertas > 0 && ahora - ultimoByte > SIN_BYTES")
        assert "return;" in codigo[laguna:juicio], (
            "el tic de la laguna ya no se sale antes de juzgar"
        )

    def test_los_dos_listos_son_los_medidos(self):
        """`CADA` es lo que el tic dice durar y `DORMIDO` lo que lo delata.

        Los 3 s no son redondos por gusto: dejan pasar los 2 s medidos de una
        página de fondo que sigue viva, y cazan las lagunas de verdad, que se
        miden en decenas de segundos. Si se cambian, hay que volver a medir los
        cinco casos de la cabecera de este fichero.
        """
        codigo = _codigo()
        assert "const CADA = 1000;" in codigo
        assert "const DORMIDO = 3000;" in codigo
        assert "}, CADA);" in codigo, "el tic ya no dura lo que dice `CADA`"
