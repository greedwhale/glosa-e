// El arranque, compartido por la pagina y por el banco de pruebas.
//
// Las dos necesitan lo mismo: Pyodide, lxml, el wheel del validador, el
// paquete de esquemas y anclas, y las facturas de ejemplo. Estaba escrito dos
// veces —una en cada pagina— y esa es la forma de que un dia arreglen cosas
// distintas y nadie se entere de cual de las dos es la que corre.

// --- Quien esta detras -----------------------------------------------------
//
// El nombre de quien responde, la marca y el correo, y nada mas. Lo que falta
// no es un hueco olvidado.
//
// El nombre es el de una persona y no el de la marca, desde el 15-09-2026. El
// RGPD pide la identidad del responsable del tratamiento, y «Glosa-e» es un
// nombre comercial: no identifica a nadie ante quien ejercer un derecho.
//
// Mientras no haya empresa ni nada de pago, esto es una herramienta gratuita
// sin actividad economica, y el articulo 10 de la LSSI no pide todavia NIF ni
// domicilio. Lo que si hace falta desde el primer dia es que quien usa esto
// sepa a quien escribe, y para eso bastan el nombre y el correo. Lo demas no
// se publica antes de hacer falta, porque lo que se publica no se despublica.
//
// En cuanto se ofrezca un servicio de pago hay que rellenar el resto, y **sin
// titular completo no se pinta la seccion comercial**: no se puede ofrecer
// una auditoria sin decir quien la hace, y la forma de garantizarlo es que no
// haya forma de encender lo uno sin lo otro.
const TITULAR = {
  nombre: "Dunior Hernández Martínez",   // el titular y responsable del tratamiento
  marca: "Glosa-e",                      // el nombre comercial, que no identifica a nadie
  nif: "",
  domicilio: "",
  correo: "contacto@glosa-e.com",
  registro: "",   // datos de inscripcion registral, solo si es sociedad
};

// Dos puertas, y la diferencia entre ellas es la razon de que existan.
//
// `hayIdentificacion()` es lo minimo para que quien usa esto sepa a quien le
// escribe: un nombre y un correo. Con eso se pinta la ficha del aviso legal y
// el correo donde se ejercen los derechos del RGPD.
//
// `puedeVender()` es lo que el articulo 10 de la LSSI pide **antes de cobrar**:
// ademas de lo anterior, NIF y domicilio. La seccion comercial de la portada
// sigue colgando de esta, asi que no se puede ofrecer nada de pago sin decir
// quien lo ofrece.
//
// Antes las dos cosas colgaban de la misma puerta, y eso obligaba a elegir mal:
// o no se decia quien esta detras, o se encendia la tienda para poder decirlo.
// Separarlas permite lo que hace falta hoy —identificarse gratis— sin aflojar
// lo que importa: la tienda sigue necesitando la ficha entera.
function hayIdentificacion() {
  return Boolean(TITULAR.nombre && TITULAR.correo);
}

function puedeVender() {
  return Boolean(TITULAR.nombre && TITULAR.nif && TITULAR.domicilio &&
                 TITULAR.correo);
}

// Esta version se fija a proposito y no se sigue a «latest»: lo que se prueba
// aqui es una combinacion concreta de Pyodide, lxml y libxml2. Si se mueve
// sola, el dia que algo se rompa no se sabra que ha cambiado.
//
// En el sitio publicado esta version **va dentro de la direccion**:
// `./pyodide/314.0.6/`. No es un adorno. Esos ficheros se sirven con permiso
// para guardarlos un ano entero, y eso solo se puede prometer si al subir la
// version la direccion cambia; si no, un navegador seguiria un ano con el
// interprete viejo y no habria forma de avisarle. `--sitio` monta la carpeta
// con este numero y **se niega a montar** si este de aqui y el de
// `validador/paquete.py` no dicen lo mismo.
const VERSION_PYODIDE = "314.0.6";
// De donde sale el interprete. **No de un CDN ajeno**, y esto no es manía.
//
// La pagina promete que la factura no sale de este ordenador, y es verdad: al
// validar hace cero peticiones, medido. Lo que no era verdad es la frase de al
// lado —«no se hace ninguna peticion a nadie»—: al abrir, el navegador pedia
// siete ficheros y 7,8 MB a cdn.jsdelivr.net, y esa peticion lleva la IP de
// quien visita a un tercero antes de que haya tocado nada.
//
// Se bajan con `python -m validador --traer-pyodide` y se sirven desde aqui.
// `--sitio` cambia esta linea al montar, y **se niega a montar si no estan**:
// sin eso, un despiste publicaria una pagina que vuelve al CDN con una
// politica de privacidad al lado diciendo que no lo hace.
const PYODIDE_EN = "../vendor/pyodide/";

// Donde estan el wheel y las facturas de ejemplo. Sirviendo el repositorio
// entero quedan un nivel mas arriba; en el sitio publicado van al lado de la
// pagina. `python -m validador --sitio` cambia estas dos lineas al montarlo,
// asi que aqui se dejan tal como funcionan en desarrollo.
const DIST = "../dist/";
const EJEMPLOS_EN = "../ejemplos/";

const EJEMPLOS = ["f-0001.xml", "f-0002.xml", "f-0002-bis.xml", "f-0006.xml",
                  "r-0001.xml", "cii-A-0001.xml", "fe-0001.xml",
                  "edi-0001.edi", "edi-0002-cortado.edi",
                  "edi-0003-una-de-cinco.edi"];

// Donde se descomprime el paquete dentro del disco virtual del navegador. Las
// tres carpetas van tal cual salen del zip y el validador las encuentra por
// las mismas variables de entorno que usa en consola: asi la pagina no le pasa
// rutas a nadie, y lo que corre aqui es el mismo codigo que corre fuera.
const DENTRO = "/opt/factura-e";

let pyodide = null;
let PAQUETE = null;
let MANIFIESTO = null;

// El manifiesto que `--sitio` deja en dist/: dice cual es el wheel y la huella
// de cada fichero que la pagina se baja. Es lo unico que se pide **siempre**
// fresco, porque es la raiz de la cadena: si este se sirviera de la cache, las
// huellas serian las de ayer y todo lo demas tambien.
//
// En desarrollo no existe, y no pasa nada: se cae al listado de directorio,
// que es lo que sirve `python -m http.server`.
async function leerElManifiesto() {
  if (MANIFIESTO !== null) return MANIFIESTO;
  try {
    const respuesta = await fetch(DIST + "rueda.json?v=" + Date.now());
    MANIFIESTO = respuesta.ok ? await respuesta.json() : {};
  } catch (_) {
    MANIFIESTO = {};
  }
  return MANIFIESTO;
}

// La direccion de un fichero con su huella detras.
//
// Antes aqui habia `?v=" + Date.now()`, y estaba puesto por un motivo real: sin
// nada, el navegador servia de su cache el wheel de ayer y la pagina corria una
// version vieja del validador sin decirlo. Paso de verdad, y mas de una vez.
//
// Lo que no se vio entonces es lo que costaba. `Date.now()` cambia en cada
// visita, asi que ninguno de esos ficheros se podia guardar **jamas**: el
// paquete de esquemas y anclas, el wheel y los diez ejemplos —1,2 MB— se
// bajaban enteros cada vez que alguien abria la pagina, para siempre, tambien
// la decima vez y aunque no hubiera cambiado una coma.
//
// La huella del contenido hace las dos cosas a la vez: cambia cuando el
// fichero cambia —asi que el de ayer sigue sin poder servirse— y no cambia
// cuando no cambia, asi que el navegador puede guardarlo un ano.
function conHuella(direccion, clave) {
  const huella = MANIFIESTO && MANIFIESTO.huellas && MANIFIESTO.huellas[clave];
  return direccion + "?v=" + (huella || Date.now());
}

// El nombre del wheel lleva la version dentro, asi que no se escribe a mano:
// si no, cada vez que suba la version en pyproject.toml la pagina dejaria de
// arrancar sin decir por que.
//
// La direccion que devuelve **acaba en `.whl` y no lleva `?v=`**, y eso no es
// un detalle de estilo: `loadPackage` saca el nombre y la version del propio
// nombre del fichero con `/^.*?([^\/]*)\.whl$/`, asi que una query detras se
// la rechaza en la cara —«is not a valid package name or URL»—. Comprobado.
//
// Por eso la huella del wheel viaja **en la ruta**: `--sitio` lo monta en
// `dist/<huella>/nombre.whl`. Sigue estando protegido contra la cache —si el
// wheel cambia, cambia la carpeta y con ella la direccion— y ademas se puede
// servir con permiso para guardarlo un ano.
async function buscarWheel() {
  // Un sitio publicado no tiene listado de directorio: Vercel devuelve 404 y
  // aqui no habria wheel que instalar. Por eso `--sitio` deja el manifiesto al
  // lado diciendo cual es. En desarrollo no existe y se cae al listado, que es
  // lo que sirve la carpeta.
  const { rueda } = await leerElManifiesto();
  if (rueda) return DIST + rueda;

  const listado = await fetch(DIST);
  if (listado.ok) {
    const nombres = [...(await listado.text()).matchAll(/href="([^"]+\.whl)"/g)]
      .map((m) => decodeURIComponent(m[1].split("/").pop()));
    if (nombres.length) {
      const donde = DIST + nombres.sort().pop();
      // En desarrollo el nombre del wheel no cambia entre compilaciones de la
      // misma version, asi que sin esto el navegador sirve el de ayer y la
      // pagina corre un validador viejo sin decirlo. Paso de verdad.
      //
      // Aqui no vale el `?v=` de siempre, porque `loadPackage` lo rechaza. Lo
      // que si vale es pedirlo una vez con `cache: "reload"`: **misma**
      // direccion, pero obligando al navegador a bajarlo otra vez y a dejar
      // esa copia en su cache. Cuando `loadPackage` pida esa direccion, lo que
      // encuentre ya es lo de hoy.
      //
      // En el sitio publicado esto no corre —hay manifiesto y la huella va en
      // la ruta—, que es lo que hay que hacer alli: nada.
      await fetch(donde, { cache: "reload" });
      return donde;
    }
  }
  throw new Error(
    "No hay ningun .whl en " + DIST + ", ni suelto ni anunciado en rueda.json."
  );
}

// El SHA-256 de unos bytes, o `null` cuando el navegador no puede calcularlo.
//
// `crypto.subtle` solo existe en contexto seguro: en https y en localhost si,
// y en `http://192.168.x.x` no. Cuando no esta, devuelve `null` y quien
// pregunta dice que **no se ha comprobado**, que no es lo mismo que decir que
// esta bien.
async function huellaDe(bytes) {
  if (!(self.crypto && self.crypto.subtle)) return null;
  const resumen = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(resumen))
    .map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function traerPaquete() {
  // El JSON primero y aparte: es un pellizco y permite decir de donde salen
  // las anclas aunque el zip falle, que es justo cuando hace falta decirlo.
  try {
    const resumen = await fetch(conHuella("./PAQUETE.json", "PAQUETE.json"));
    if (resumen.ok) PAQUETE = await resumen.json();
  } catch (_) {
    PAQUETE = null;
  }
  if (!PAQUETE) return;

  // El zip aparte del resto: lo que llega hay que mirarlo **antes** de
  // descomprimirlo, y un fallo de descarga no es lo mismo que un fallo de
  // contenido. Lo primero deja la pagina sin esquemas y lo dice; lo segundo
  // significa que lo que ha llegado no es lo que la pagina afirma traer, y
  // eso no se descomprime.
  let crudo = null;
  try {
    const zip = await fetch(conHuella("./paquete.zip", "paquete.zip"));
    if (!zip.ok) throw new Error("no esta el zip");
    crudo = await zip.arrayBuffer();
  } catch (_) {
    PAQUETE = null;
    return;
  }

  // La huella publicada, comprobada de verdad.
  //
  // `PAQUETE.json` lleva el SHA-256 del zip escrito al lado desde el
  // principio, y hasta el 06-09-2026 **no lo miraba nadie**: se publicaba una
  // huella y se descomprimia lo que llegara.
  //
  // Esto no es una frontera de seguridad y no se va a decir que lo sea: el
  // manifiesto y el zip vienen del mismo sitio, y quien pudiera cambiar uno
  // cambiaria el otro. Lo que caza es el fallo que este repositorio ya ha
  // tenido cuatro veces con distinto disfraz —algo servido de una cache
  // haciendose pasar por lo de hoy— y su pariente, la descarga a medias: un
  // zip truncado se descomprime **sin error** y deja al validador con menos
  // anclas de las que la ficha dice que trae, que es un aprobado de mas
  // repartido en silencio.
  const medida = await huellaDe(crudo);
  PAQUETE.huella_comprobada = medida === null ? null : medida === PAQUETE.huella;
  if (PAQUETE.huella_comprobada === false) {
    throw new Error(
      "El paquete de esquemas y anclas no es el que la pagina dice traer: " +
      "PAQUETE.json publica " + String(PAQUETE.huella).slice(0, 12) +
      "... y lo que ha llegado resume " + medida.slice(0, 12) + "... . " +
      "No se descomprime."
    );
  }
  // El tamano no sobra aunque se haya mirado la huella: es lo unico que se
  // puede comprobar cuando `crypto.subtle` no esta, que es exactamente el
  // caso de servir esto en una red local por http.
  if (PAQUETE.bytes && crudo.byteLength !== PAQUETE.bytes) {
    throw new Error(
      "El paquete de esquemas y anclas ha llegado con " + crudo.byteLength +
      " bytes y la ficha dice " + PAQUETE.bytes + ". Es una descarga a medias."
    );
  }

  try {
    pyodide.FS.mkdirTree(DENTRO);
    await pyodide.unpackArchive(crudo, "zip", { extractDir: DENTRO });
    pyodide.runPython(
      "import os\n" +
      "from pathlib import Path\n" +
      "_d = Path(" + JSON.stringify(DENTRO) + ")\n" +
      // Se comprueba que las tres carpetas han llegado de verdad en vez de
      // darlo por hecho. Descomprimir sin error y dejarlas en otro sitio deja
      // al validador con `Catalogo.vacio` y `Almacen.vacio`: la situacion de
      // no traer nada, pero contada como si trajera.
      "assert (_d / 'esquemas').is_dir(), 'sin esquemas'\n" +
      "assert (_d / 'anclas').is_dir(), 'sin anclas'\n" +
      "assert (_d / 'anclas-sellos').is_dir(), 'sin anclas de sellado'\n" +
      "os.environ['FACTURAE_ESQUEMAS'] = str(_d / 'esquemas')\n" +
      "os.environ['FACTURAE_ANCLAS'] = str(_d / 'anclas')\n" +
      "os.environ['FACTURAE_ANCLAS_SELLOS'] = str(_d / 'anclas-sellos')\n"
    );
  } catch (_) {
    PAQUETE = null;
  }
}

// `pyodide.js` se carga desde aqui y no con una etiqueta <script> en cada
// pagina. Escrito en el HTML estaria tres veces —la herramienta, el banco y el
// legal— y habria tres sitios donde acordarse de cambiar la direccion; con
// esto solo hay uno, y es el mismo que `--sitio` sustituye al montar.
function cargarElArranque() {
  if (window.loadPyodide) return Promise.resolve();
  return new Promise((bien, mal) => {
    const etiqueta = document.createElement("script");
    etiqueta.src = PYODIDE_EN + "pyodide.js";
    etiqueta.onload = bien;
    etiqueta.onerror = () =>
      mal(new Error(
        "No esta el interprete en " + PYODIDE_EN + ". Traelo con " +
        "`python -m validador --traer-pyodide`."
      ));
    document.head.appendChild(etiqueta);
  });
}

// --- El vigilante de la descarga -------------------------------------------
//
// Un `fetch` que se corta a la mitad no siempre falla. Medido en produccion el
// 08-09-2026: `python_stdlib.zip` se rompio con `net::ERR_CONNECTION_RESET`
// —el servidor habia contestado 200— y `loadPyodide` ni rechazo ni resolvio.
// La pagina se quedo diciendo «Descargando el validador» para siempre, con la
// zona aceptando facturas que ya no se iban a validar nunca.
//
// Es el fallo de esta casa con otro disfraz: no se rompe nada, no sale ningun
// error, y lo que hay en pantalla no es lo que esta pasando.
//
// Lo que **no** vale como arreglo es un tiempo maximo de arranque. En la
// conexion desde la que se escribe esto el arranque bueno tarda 78 s y solo el
// interprete 41 s; cualquier limite lo bastante corto para servir de algo
// rompe la pagina justo a quien mas le cuesta cargarla.
//
// Asi que no se mide cuanto tarda, se mide **si llega algo**: con una peticion
// abierta y ni un byte en treinta segundos, la conexion esta muerta y no
// lenta. Y sin ninguna peticion abierta no se cuenta nada, porque ahi no se
// descarga sino que se compila, y eso puede tardar lo que quiera.
class SinDescarga extends Error {
  constructor(mensaje) {
    super(mensaje);
    this.name = "SinDescarga";
  }
}

// Treinta segundos **sin un solo byte**, no treinta segundos de descarga.
const SIN_BYTES = 30000;

// Envuelve `fetch` mientras dura `faena()` para contar lo que entra.
//
// El conteo va sobre `clone()` y no sobre la respuesta que se devuelve: la
// original sale de aqui intacta —con su `url`, su `content-type` y su cuerpo
// sin tocar— y Pyodide recibe exactamente lo que habria recibido sin
// vigilante. Reconstruir la respuesta con un `ReadableStream` propio gastaba
// menos memoria y dejaba a `instantiateStreaming` sin el tipo que necesita,
// que es cambiar un fallo silencioso por otro.
async function conVigilante(faena) {
  const deVerdad = globalThis.fetch;
  let abiertas = 0;
  let ultimoByte = Date.now();
  let reloj = null;

  // Se lee la copia hasta el final solo para saber que sigue llegando. Lo que
  // trae no se guarda: quien lo usa es Pyodide, en la otra rama del clon.
  const contar = async (copia) => {
    try {
      const lector = copia.body.getReader();
      for (;;) {
        const { done } = await lector.read();
        if (done) break;
        ultimoByte = Date.now();
      }
    } catch (_) {
      // Que la copia se rompa no es noticia: lo que importa es que dejan de
      // llegar bytes, y de eso ya se entera el reloj.
    } finally {
      abiertas -= 1;
    }
  };

  globalThis.fetch = async (...args) => {
    abiertas += 1;
    ultimoByte = Date.now();
    let respuesta;
    try {
      respuesta = await deVerdad(...args);
    } catch (error) {
      abiertas -= 1;
      throw error;
    }
    ultimoByte = Date.now();
    if (!respuesta.body) {
      abiertas -= 1;
      return respuesta;
    }
    contar(respuesta.clone());
    return respuesta;
  };

  try {
    return await Promise.race([
      faena(),
      new Promise((_, mal) => {
        reloj = setInterval(() => {
          if (abiertas > 0 && Date.now() - ultimoByte > SIN_BYTES) {
            mal(new SinDescarga(
              "La descarga se ha cortado. No es que vaya lenta: lleva " +
              Math.round(SIN_BYTES / 1000) + " segundos sin llegar un solo " +
              "byte. Recarga la página para volver a intentarlo."));
          }
        }, 1000);
      }),
    ]);
  } finally {
    clearInterval(reloj);
    globalThis.fetch = deVerdad;
  }
}

// Arranca el validador entero. `avisar(etiqueta, segundos)` se llama al
// terminar cada fase, para que cada pagina lo cuente como quiera.
//
// Va envuelto en el vigilante para que una conexion que se muere a la mitad
// salga por el `catch` de la pagina en vez de quedarse cargando para siempre.
async function arrancar(avisar) {
  return conVigilante(() => arrancarDeVerdad(avisar));
}

async function arrancarDeVerdad(avisar) {
  const decir = avisar || function () {};
  const cero = performance.now();
  let t = cero;
  const seg = (ms) => (ms / 1000).toFixed(2);

  // Lo primero de todo, y antes de los quince megas del interprete: es un
  // pellizco y de el salen las huellas con las que se piden los demas.
  await leerElManifiesto();

  await cargarElArranque();
  pyodide = await loadPyodide({ indexURL: PYODIDE_EN });
  decir("Intérprete de Python (WebAssembly)", seg(performance.now() - t));

  t = performance.now();
  await pyodide.loadPackage("lxml");
  decir("lxml + libxml2", seg(performance.now() - t));

  // Aqui habia tres pasos —bajar micropip, importarlo, y pedirle que resolviera
  // e instalara— para meter **un** wheel del que ya sabemos el nombre, la
  // version y que no tiene dependencias (se construye con `--no-deps`).
  // `loadPackage` acepta la direccion de un `.whl` directamente, asi que
  // micropip sobraba: eran 115 KB de descarga y un paso de resolucion que no
  // resolvia nada.
  t = performance.now();
  const elWheel = await buscarWheel();
  await pyodide.loadPackage(elWheel);
  // `loadPackage` **no se queja** si el wheel no llega: escribe un aviso en la
  // consola y devuelve como si todo hubiera ido bien. Con micropip esto fallaba
  // aqui mismo; sin el, el arranque dice «Listo en 5 s» sin validador dentro y
  // el fallo sale mucho despues, al soltar una factura, disfrazado de
  // `ModuleNotFoundError`. Comprobado apuntando el manifiesto a un wheel que no
  // existe: la pagina se pintaba lista y rota a la vez.
  //
  // Asi que se mira. Es una linea, y es la diferencia entre fallar donde pasa
  // el fallo y fallar en otro sitio media hora despues.
  try {
    pyodide.pyimport("validador");
  } catch (_) {
    throw new Error(
      "El validador no ha llegado: `" + elWheel + "` no se ha podido instalar."
    );
  }
  decir("El validador", seg(performance.now() - t));

  t = performance.now();
  await traerPaquete();
  decir("Esquemas y anclas de confianza", seg(performance.now() - t));

  t = performance.now();
  pyodide.FS.mkdirTree("/ejemplos");
  await Promise.all(EJEMPLOS.map(async (nombre) => {
    const respuesta = await fetch(
      conHuella(EJEMPLOS_EN + nombre, "ejemplos/" + nombre));
    pyodide.FS.writeFile("/ejemplos/" + nombre,
                         new Uint8Array(await respuesta.arrayBuffer()));
  }));
  decir("Facturas de ejemplo", seg(performance.now() - t));

  return { total: seg(performance.now() - cero), paquete: PAQUETE };
}

// El informe, en estructurado.
//
// La redaccion de cada queja y la frase del final salen de Python tal cual:
// son el producto, y reescribirlas en JavaScript seria tener dos versiones de
// lo que dice el validador y creerse la que no corre.
//
// La procedencia de las anclas se declara a mano y no se deja en la del
// manifiesto. El manifiesto dice de que lista salen, que es verdad y no es
// suficiente: lo que quien valida aqui no puede saber es que **no las ha
// elegido el**. Esa frase acaba en el informe, al lado de la huella.
const INFORME = `
import json
from validador import factura
from validador.cadena import Almacen
from validador.esquema import Catalogo

_a = Almacen.por_defecto()
if _a.declarada:
    _a = Almacen(_a.carpeta, 'que viene con esta pagina, ' + _a.declarada,
                 _a.sellos_en)
_c = Catalogo.por_defecto()
_lote = factura.validar_lote(list(_rutas), catalogo=_c, almacen=_a)

def _inc(i):
    return {
        "codigo": i.codigo, "gravedad": i.gravedad, "mensaje": i.mensaje,
        "campo": i.campo, "esperado": i.esperado, "encontrado": i.encontrado,
        "norma": factura.origen(i),
    }

_senialados = _lote.senialados
_docs = []
for _camino, _informe in _lote.informes:
    _docs.append({
        "nombre": _camino.name,
        "resumen": _informe.resumen(),
        "conforme": _informe.conforme,
        "validado": _informe.validado,
        "choca": _camino.name in _senialados,
        "incidencias": [_inc(i) for i in
                        # Por gravedad y de mayor a menor: lo que hay que
                        # arreglar primero, y las notas al final. Estaban en
                        # notas-errores-avisos, que no es ninguno de los dos
                        # ordenes posibles y dejaba el error debajo de tres
                        # parrafos de contexto. Las notas cierran a proposito:
                        # dicen que se dio por bueno y con que base, y eso se
                        # lee mejor despues de saber que fallo.
                        _informe.errores + _informe.avisos + _informe.notas],
    })

json.dumps({
    "resumen": _lote.resumen(),
    "conforme": _lote.conforme,
    # La frase que dice de que se ha fiado quien lee. Tiene que decir lo que ha
    # pasado de verdad: con los defectos —forma si, anclas no— prometia haber
    # comprobado la forma en una pagina sin esquemas y se callaba las anclas
    # justo cuando las trae puestas.
    "alcance": _lote.alcance(forma=not _c.vacio, anclas=not _a.vacio),
    "cruzadas": [_inc(i) for i in _lote.cruzadas],
    "documentos": _docs,
}, ensure_ascii=False)
`;

// Valida ficheros del disco de quien mira. No salen de su ordenador: se
// escriben en el disco virtual del navegador, que vive en su memoria.
async function validar(ficheros) {
  pyodide.FS.mkdirTree("/entrada");
  const rutas = [];
  for (const f of ficheros) {
    // El nombre se limpia porque acaba siendo una ruta en el disco virtual.
    const destino = "/entrada/" + f.name.replace(/[^\w.\-]/g, "_");
    pyodide.FS.writeFile(destino, new Uint8Array(await f.arrayBuffer()));
    rutas.push(destino);
  }
  pyodide.globals.set("_rutas", rutas);
  return JSON.parse(await pyodide.runPythonAsync(INFORME));
}

// La misma maquinaria, sobre una factura que ya viene con la pagina.
//
// Existe para que se pueda ver un informe **antes** de soltar nada. Quien
// llega por primera vez no sabe si esto le sirve, y pedirle la factura por
// delante es pedirle confianza antes de haberla dado.
//
// No baja nada: los ejemplos ya estan en el disco virtual desde el arranque,
// asi que esto es exactamente el mismo camino que sigue una factura de
// verdad, sin una ruta aparte que pudiera portarse distinto. Si el ejemplo no
// esta, se dice cual falta en vez de devolver un informe vacio.
async function validarEjemplo(nombre) {
  if (!EJEMPLOS.includes(nombre)) {
    throw new Error(
      "«" + nombre + "» no es una de las facturas que trae la pagina.");
  }
  pyodide.globals.set("_rutas", ["/ejemplos/" + nombre]);
  return JSON.parse(await pyodide.runPythonAsync(INFORME));
}

// El banco de pruebas corre su propio fichero de comprobaciones. La huella es
// por lo mismo que la del wheel: sin ella, el navegador sirve de su cache una
// version vieja y el banco correria sus comprobaciones de ayer contra el
// codigo de hoy, saliendo todo verde. Paso: se anadieron tres, se recargo, y
// la pagina siguio diciendo «las 33 comprobaciones pasan» tan contenta.
async function correrBanco() {
  await leerElManifiesto();
  const codigo = await (
    await fetch(conHuella("./prueba.py", "prueba.py"))).text();
  return JSON.parse(await pyodide.runPythonAsync(codigo));
}

window.Glosa = {
  arrancar, validar, validarEjemplo, correrBanco, puedeVender,
  hayIdentificacion,
  titular: TITULAR,
  get paquete() { return PAQUETE; },
};
