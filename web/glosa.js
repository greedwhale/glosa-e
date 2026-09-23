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
  const huella = laHuellaDe(clave);
  // Los ocho primeros y no la huella entera: para que la direccion cambie
  // cuando el fichero cambia bastan, y son los mismos ocho de siempre, asi
  // que a quien ya haya pasado por aqui le sigue valiendo lo que tiene
  // guardado. La huella entera esta para compararla, no para escribirla.
  return direccion + "?v=" + (huella ? huella.slice(0, 8) : Date.now());
}

function laHuellaDe(clave) {
  return (MANIFIESTO && MANIFIESTO.huellas && MANIFIESTO.huellas[clave]) || null;
}

// Lo que ha llegado, contra lo que el manifiesto dice que tenia que llegar.
//
// Hasta el 20-09-2026 esas huellas solo servian de `?v=`: iban detras de la
// direccion para que el navegador no sirviera una copia vieja, y **no las
// miraba nadie**. Medido: con un byte de mas en el wheel, la pagina arrancaba
// y ponia «Listo».
//
// Esto no es una frontera de seguridad y no se va a decir que lo sea: el
// manifiesto y los ficheros salen del mismo sitio, y quien pudiera cambiar uno
// cambiaria el otro. Lo que caza es el fallo de esta casa —algo servido de una
// cache haciendose pasar por lo de hoy— y su pariente, la descarga a medias,
// que no da error: deja un fichero corto y sigue.
//
// Devuelve `true` si cuadra, y `null` cuando **no se ha podido comprobar**: en
// desarrollo no hay manifiesto, y `crypto.subtle` no existe fuera de https y
// localhost. No comprobado no es lo mismo que comprobado y bien, y por eso no
// devuelve `false` ahi.
async function comprobar(clave, bytes, queEs) {
  const publicada = laHuellaDe(clave);
  if (!publicada) return null;
  const medida = await huellaDe(bytes);
  if (medida === null) return null;
  if (medida !== publicada) {
    throw new Error(
      queEs + " no es lo que la pagina dice traer: rueda.json publica " +
      publicada.slice(0, 12) + "... y lo que ha llegado resume " +
      medida.slice(0, 12) + "... . No se usa.");
  }
  return true;
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
  if (rueda) return { donde: DIST + rueda, clave: "dist/" + rueda, fresco: false };

  const listado = await fetch(DIST);
  if (listado.ok) {
    const nombres = [...(await listado.text()).matchAll(/href="([^"]+\.whl)"/g)]
      .map((m) => decodeURIComponent(m[1].split("/").pop()));
    if (nombres.length) {
      // En desarrollo el nombre del wheel no cambia entre compilaciones de la
      // misma version, asi que sin `cache: "reload"` el navegador sirve el de
      // ayer y la pagina corre un validador viejo sin decirlo. Paso de verdad.
      // En el sitio publicado no hace falta: la huella va en la ruta, y ademas
      // ahora se compara.
      return { donde: DIST + nombres.sort().pop(), clave: null, fresco: true };
    }
  }
  throw new Error(
    "No hay ningun .whl en " + DIST + ", ni suelto ni anunciado en rueda.json."
  );
}

// Instala el validador, mirando antes lo que llega.
//
// **Se baja dos veces, y eso tiene un porque.** Lo ideal seria bajarlo una vez
// y darle los bytes a `loadPackage`, para que lo comprobado y lo instalado
// fueran literalmente lo mismo. No se puede: `loadPackage` solo acepta un
// nombre o una direccion, y la direccion la pide el con `fetch`. Tampoco vale
// `emfs:`, que sirve para instalar desde el disco virtual —medido el
// 20-09-2026: la politica de contenido lo bloquea, porque `connect-src 'self'`
// no admite ese esquema, y `loadPackage` no se queja: escribe un aviso en la
// consola y devuelve tan contento; lo cazo el `pyimport` de abajo—.
//
// La segunda peticion no cuesta cable. Medido en produccion el 20-09-2026 con
// `performance.getEntriesByType("resource")`: la primera transfiere 503.469
// bytes y tarda 11,5 s; la segunda transfiere **0** y tarda 21 ms, servida de
// la cache. Es lo que compra la cabecera `immutable` del sitio publicado. En
// local se ven las dos por el cable, porque `python -m http.server` no manda
// esa cabecera.
//
// Y lo que queda: entre la copia que se mira y la que instala `loadPackage`
// cabe, en teoria, que no sean la misma. Esto no es una frontera de seguridad
// y no se va a decir que lo sea. Lo que caza es lo que de verdad pasa aqui
// —una copia vieja de la cache, una descarga a medias—, y para eso las dos
// vienen del mismo sitio y valen igual.
async function instalarElValidador() {
  const { donde, clave, fresco } = await buscarWheel();
  const respuesta = await pedir(donde, "El validador",
                               fresco ? { cache: "reload" } : undefined);
  const crudo = new Uint8Array(await respuesta.arrayBuffer());
  await comprobar(clave, crudo, "El validador (" + donde.split("/").pop() + ")");
  await pyodide.loadPackage(donde);
  return donde;
}

// Pedir algo que **tiene que estar**.
//
// Un `fetch` no falla porque el servidor conteste 404: devuelve la respuesta
// con el cuerpo del error dentro, y quien no mire el estado se lleva la pagina
// de error como si fuera lo que pidio.
//
// Medido el 22-09-2026, sirviendo el repositorio como en desarrollo y con
// `ejemplos/f-0001.xml` devolviendo un 404: la pagina arrancaba tan contenta
// —«Listo en 10,80 s»— y el ejemplo quedaba en el disco virtual como **164
// bytes de «404 Not Found»**, con su nombre de factura puesto. Al pedir su
// informe salia un veredicto —«1 fichero(s) · 0 correcto(s) · 0 con errores ·
// 1 SIN COMPROBAR»— sobre un documento que nunca llego.
//
// En el sitio publicado esto lo paraba la huella del manifiesto, pero **de
// rebote**: no por mirar el estado, sino porque lo que llego no cuadraba con
// lo publicado. En desarrollo no hay manifiesto y pasaba entero. Mirar el
// estado es una linea y no depende de que exista otra cosa.
//
// Aqui no valen todos los `fetch` de este fichero: el manifiesto y el listado
// de `dist/` **pueden** faltar y eso esta decidido a proposito, cada uno con
// su porque escrito al lado.
async function pedir(direccion, queEs, opciones) {
  const respuesta = await fetch(direccion, opciones);
  if (!respuesta.ok) {
    throw new Error(queEs + " no ha llegado: " + direccion.split("?")[0] +
                    " contesta " + respuesta.status + ".");
  }
  return respuesta;
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
//
// Y aun asi se equivocaba, porque «si llega algo» lo mira el hilo de la propia
// pagina, y ese hilo se para. Reproducido el 22-09-2026 con el sitio servido
// por un tubo de 30 KB/s, dos veces seguidas: el arranque se cayo solo
// diciendo «lleva 30 segundos sin llegar un solo byte» cuando el servidor
// llevaba escritos **1.566.927 de los 1.637.748 bytes** del wheel de lxml —el
// 96 %—, y de la peticion no habia llegado ni la cabecera. La pestana estaba
// de fondo: los tics del vigilante, que venian cada 2 s, se espaciaron 46 s y
// luego 60 s, que es lo que hace Chrome con una pagina oculta a los cinco
// minutos. No es que no llegaran bytes; es que no habia nadie contandolos.
//
// De ahi la tercera regla, y la que faltaba: **el vigilante solo puede jurar
// por el tiempo en que estuvo mirando**. Cada tic mide su propio retraso, y lo
// que se durmio no lo cuenta como silencio. Lo que se para tambien es lo que
// mira, asi que un vigilante que no se entera de sus lagunas acaba condenando
// justo a quien mas tarda en cargar, que es a quien dice que no hay que
// romper.
class SinDescarga extends Error {
  constructor(mensaje) {
    super(mensaje);
    this.name = "SinDescarga";
  }
}

// Treinta segundos **sin un solo byte**, no treinta segundos de descarga.
const SIN_BYTES = 30000;

// Cada cuanto mira, y a partir de que retraso se da por dormido.
//
// Un `setInterval` no es un reloj: es una cita a la que el navegador lleva a
// quien puede. Con la pagina de fondo, Chrome junta los tics —medido: de 1 s
// pasan a 2 s, y a los cinco minutos ocultos, a uno cada 46 y 60 s—, y con el
// hilo ocupado instanciando quince megas de wasm no hay tic ninguno. En esas
// lagunas tampoco se entregan las respuestas, asi que los bytes que si estan
// llegando no los cuenta nadie.
//
// DORMIDO es el listo para distinguir las dos cosas. Tres segundos deja pasar
// el tic tarde de una pagina oculta que sigue viva —los 2 s medidos— y caza la
// laguna de verdad, que se mide en decenas de segundos.
const CADA = 1000;
const DORMIDO = 3000;

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
  // El mando para abandonar. `Promise.race` no para al que pierde: sin esto,
  // el vigilante saltaba, la pagina decia «No ha arrancado» y la descarga
  // seguia por detras. Medido el 20-09-2026 con un servidor que se atasca a
  // proposito: el vigilante salto a los 30 s, y a los 45 el servidor escribio
  // el resto de `python_stdlib.zip` y **el cliente seguia ahi**; detras se
  // bajaron lxml, el wheel, el paquete y los diez ejemplos, casi 5 MB, con la
  // pagina puesta en que no habia arrancado. Y el validador acababa vivo: se
  // le podia pedir un informe por consola mientras la zona estaba apagada.
  //
  // Es lo de siempre con otro disfraz: lo que hay en pantalla no es lo que
  // esta pasando. Ademas duele donde mas: en una conexion que se esta muriendo,
  // esas peticiones abiertas son lo que le queda.
  const mando = new AbortController();
  let abiertas = 0;
  let ultimoByte = Date.now();
  // Cuando mire por ultima vez, que no es lo mismo que cuando entro el ultimo
  // byte: aquello dice si la conexion da senales, y esto si el vigilante
  // estaba en condiciones de verlas.
  let ultimoTic = Date.now();
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

  // La senial de abandono se le engancha a cada peticion. Si quien llama traia
  // la suya, se juntan las dos con `AbortSignal.any`, que es lo unico que
  // permite no quitarle la suya a nadie; donde no exista, manda la nuestra,
  // porque aqui nadie pasa senial —Pyodide pide con `fetch(url)`— y quedarse
  // sin poder abandonar es peor.
  const conSenial = (opciones) => {
    const suya = opciones && opciones.signal;
    if (suya && typeof AbortSignal.any === "function") {
      return { ...opciones, signal: AbortSignal.any([suya, mando.signal]) };
    }
    return { ...(opciones || {}), signal: mando.signal };
  };

  globalThis.fetch = async (entrada, opciones) => {
    abiertas += 1;
    ultimoByte = Date.now();
    let respuesta;
    try {
      // Un `Request` ya trae su senial dentro y no se le puede cambiar: hay
      // que rehacerlo. Lo demas va por el camino normal.
      respuesta = entrada instanceof Request
        ? await deVerdad(new Request(entrada, { signal: mando.signal }))
        : await deVerdad(entrada, conSenial(opciones));
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

  // La faena, aparte de la carrera a proposito: el `fetch` bueno se devuelve
  // **cuando ella acaba**, no cuando acaba la carrera. Devolviendolo en el
  // `finally` de la carrera, lo que siguiera bajando despues ya no pasaba por
  // aqui y no lo contaba nadie.
  const enMarcha = faena();
  enMarcha
    .finally(() => {
      clearInterval(reloj);
      globalThis.fetch = deVerdad;
    })
    // Que se abandone no puede dejar una promesa rechazada sin dueno, que en
    // el navegador sale por la consola como si fuera un fallo aparte.
    .catch(() => {});

  try {
    return await Promise.race([
      enMarcha,
      new Promise((_, mal) => {
        reloj = setInterval(() => {
          const ahora = Date.now();
          const tardanza = ahora - ultimoTic;
          ultimoTic = ahora;

          // Un tic que llega tarde no trae noticias: trae una laguna. Durante
          // ella no corrio el contador de bytes, asi que una descarga que iba
          // bien se ve exactamente igual que una cortada, y lo que hay que
          // hacer con lo que no se ha visto es no jurar sobre ello.
          //
          // Se le perdona al reloj el rato que no miro, tope hasta ahora mismo
          // —sin ese tope, una laguna larga saldria regalando inmunidad para
          // despues—, y no se juzga en este tic, para que las respuestas que
          // estaban esperando entren antes del siguiente. Si la conexion
          // estaba muerta de verdad, el silencio vuelve a contar desde ya y el
          // vigilante salta treinta segundos mas tarde.
          if (tardanza > DORMIDO) {
            ultimoByte = Math.min(ahora, ultimoByte + tardanza - CADA);
            return;
          }

          if (abiertas > 0 && ahora - ultimoByte > SIN_BYTES) {
            mal(new SinDescarga(
              "La descarga se ha cortado. No es que vaya lenta: lleva " +
              Math.round(SIN_BYTES / 1000) + " segundos sin llegar un solo " +
              "byte. Recarga la página para volver a intentarlo."));
          }
        }, CADA);
      }),
    ]);
  } catch (error) {
    clearInterval(reloj);
    // Aqui es donde se abandona de verdad. Sin esta linea todo lo de arriba es
    // un cartel.
    mando.abort(error);
    throw error;
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
  const elWheel = await instalarElValidador();
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
    const clave = "ejemplos/" + nombre;
    const respuesta = await pedir(conHuella(EJEMPLOS_EN + nombre, clave),
                                  "El ejemplo «" + nombre + "»");
    const crudo = new Uint8Array(await respuesta.arrayBuffer());
    // Tambien estos. Son las facturas con las que alguien decide si esto le
    // sirve, antes de soltar una suya: un ejemplo servido a medias daria un
    // informe que no es el que esa factura merece, sin que nada pareciera
    // roto.
    await comprobar(clave, crudo, "El ejemplo «" + nombre + "»");
    pyodide.FS.writeFile("/ejemplos/" + nombre, crudo);
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

# El catalogo y el almacen se arman **una vez** y se guardan.
#
# Construirlos no cuesta nada —son perezosos—, pero el esquema compilado y los
# certificados leidos viven dentro de cada uno, asi que uno nuevo en cada
# validacion tira ese trabajo y lo vuelve a hacer. Medido en esta maquina, con
# la factura de ejemplo: 70 ms rehaciendolos y 1,9 ms reusandolos. Eso se
# pagaba **en cada factura soltada**, y en el navegador cuesta bastante mas.
#
# Se puede guardar porque aqui no cambian: las carpetas salen del paquete que
# se descomprimio al arrancar, y eso pasa una vez. En consola no hay nada que
# guardar, porque cada orden es un proceso nuevo.
if "_c" not in globals():
    _a = Almacen.por_defecto()
    if _a.declarada:
        _a = Almacen(_a.carpeta, 'que viene con esta pagina, ' + _a.declarada,
                     _a.sellos_en)
    _c = Catalogo.por_defecto()

_lote = factura.validar_lote(list(_rutas), catalogo=_c, almacen=_a,
                             nombres=list(_nombres))

def _inc(i):
    return {
        "codigo": i.codigo, "gravedad": i.gravedad, "mensaje": i.mensaje,
        "campo": i.campo, "esperado": i.esperado, "encontrado": i.encontrado,
        "norma": factura.origen(i),
    }

_senialados = _lote.senialados
_docs = []
for _camino, _informe, _nombre in _lote.nombrados:
    _docs.append({
        "nombre": _nombre,
        "resumen": _informe.resumen(),
        "conforme": _informe.conforme,
        "validado": _informe.validado,
        "choca": _nombre in _senialados,
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

// Una validacion cada vez, y las demas esperan su turno.
//
// `_rutas` y `_nombres` son globales de Pyodide: la llamada las escribe y
// luego `INFORME` las lee cuando el Python llega a ejecutarse. Entre esas dos
// cosas hay un `await`, y ahi cabia otra llamada entera. La segunda pisaba las
// globales de la primera y las dos salian describiendo los ficheros de la
// segunda.
//
// Medido en produccion el 21-09-2026, dos facturas propias soltadas en el
// mismo tick, una con errores y otra sin ellos: **20 de 20** informes de la
// mala volvieron hablando de la buena, con «1 fichero(s) · 1 correcto(s) · 0
// con errores» y `conforme: true`. Es decir, el peor fallo posible aqui: decir
// que esta bien algo que no se ha mirado. Con 1 ms de separacion no pasaba
// ninguna vez de ocho, asi que no es una carrera rara: es lo que ocurre
// siempre que dos validaciones arrancan juntas.
//
// Encolar no hace esperar mas de lo que ya se esperaba. Pyodide corre Python
// en el hilo principal, asi que dos validaciones nunca fueron simultaneas de
// verdad; lo unico que hacian a la vez era corromperse. Esto solo lo hace
// explicito.
let _cola = Promise.resolve();

function enFila(faena) {
  const mio = _cola.then(faena);
  // La cola no se rompe porque una falle: el error se lo queda quien llamo y
  // aqui se traga, asi que la siguiente arranca igual. Sin esto, una
  // validacion con error dejaria la pagina sin poder validar nada mas.
  //
  // Y por eso `_cola.then(faena)` lleva un solo argumento: con un segundo
  // —el manejador de rechazo— la faena se correria **otra vez** el dia que la
  // cola si se rompiera. Es la clase de cosa que hoy no pasa y manana si.
  _cola = mio.then(() => {}, () => {});
  return mio;
}

// Valida ficheros del disco de quien mira. No salen de su ordenador: se
// escriben en el disco virtual del navegador, que vive en su memoria.
async function validar(ficheros) {
  return enFila(() => _validarAhora(ficheros));
}

async function _validarAhora(ficheros) {
  const rutas = [];
  const nombres = [];
  let orden = 0;
  for (const f of ficheros) {
    // El nombre se limpia porque acaba siendo una ruta en el disco virtual. Y
    // cada fichero va en su propia carpeta, porque limpio deja de ser único:
    // «factura ñ.xml» y «factura ç.xml» salían los dos «factura__.xml», el
    // segundo pisaba al primero, y el primero no se validaba nunca —el informe
    // traía dos veces el segundo, «sin errores», y un duplicado que no era—.
    const carpeta = "/entrada/" + orden++;
    pyodide.FS.mkdirTree(carpeta);
    const destino = carpeta + "/" + f.name.replace(/[^\w.\-]/g, "_");
    pyodide.FS.writeFile(destino, new Uint8Array(await f.arrayBuffer()));
    rutas.push(destino);
    // Y en el informe, el nombre que tenía en su ordenador, no el limpio.
    nombres.push(f.name);
  }
  pyodide.globals.set("_rutas", rutas);
  pyodide.globals.set("_nombres", nombres);
  try {
    return JSON.parse(await pyodide.runPythonAsync(INFORME));
  } finally {
    borrarLoSoltado(rutas);
  }
}

// Lo que se solto, fuera en cuanto el informe esta hecho.
//
// El disco virtual vive en la memoria de la pestaña y **no se vacia solo**.
// Medido el 22-09-2026: tres validaciones seguidas dejaban las tres facturas
// en `/entrada/0` —8.343 bytes— vivas despues de entregar el informe, y asi
// hasta cerrar la pestaña. Con seis eran 480.438 bytes.
//
// No es que salgan de aqui: a ningun sitio se suben, y eso que promete la
// pagina sigue siendo verdad. Es que son de quien las solto y ya no hacen
// falta. Guardar algo que nadie ha pedido que se guarde es lo contrario de lo
// que dice la pagina al lado de la zona.
//
// Va en un `finally` a proposito: si la validacion revienta, la factura tiene
// que irse igual, y es justo cuando mas facil es olvidarse. Y cada borrado va
// por su cuenta porque el fallo que importa es el de la validacion, no el de
// la limpieza: si esto reventara, taparia aquel.
function borrarLoSoltado(rutas) {
  for (const ruta of rutas) {
    try { pyodide.FS.unlink(ruta); } catch (_) { /* no estaba */ }
    try { pyodide.FS.rmdir(ruta.slice(0, ruta.lastIndexOf("/"))); } catch (_) { /* ya no */ }
  }
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
  // El nombre se mira fuera de la fila: si no es un ejemplo, no hay nada que
  // encolar y quien llama se entera ahora y no cuando le toque el turno.
  if (!EJEMPLOS.includes(nombre)) {
    throw new Error(
      "«" + nombre + "» no es una de las facturas que trae la pagina.");
  }
  return enFila(() => _validarEjemploAhora(nombre));
}

async function _validarEjemploAhora(nombre) {
  pyodide.globals.set("_rutas", ["/ejemplos/" + nombre]);
  pyodide.globals.set("_nombres", [nombre]);
  return JSON.parse(await pyodide.runPythonAsync(INFORME));
}

// El banco de pruebas corre su propio fichero de comprobaciones. La huella es
// por lo mismo que la del wheel: sin ella, el navegador sirve de su cache una
// version vieja y el banco correria sus comprobaciones de ayer contra el
// codigo de hoy, saliendo todo verde. Paso: se anadieron tres, se recargo, y
// la pagina siguio diciendo «las 33 comprobaciones pasan» tan contenta.
async function correrBanco() {
  await leerElManifiesto();
  const respuesta = await pedir(conHuella("./prueba.py", "prueba.py"),
                                "El fichero de comprobaciones");
  const crudo = new Uint8Array(await respuesta.arrayBuffer());
  // Y este el que mas: es el fichero que dice si el validador hace lo que
  // promete. Uno servido de una cache vieja corre las comprobaciones de ayer
  // contra el codigo de hoy y sale todo verde, que ya paso.
  await comprobar("prueba.py", crudo, "El fichero de comprobaciones");
  const codigo = new TextDecoder("utf-8").decode(crudo);
  return JSON.parse(await pyodide.runPythonAsync(codigo));
}

window.Glosa = {
  arrancar, validar, validarEjemplo, correrBanco, puedeVender,
  hayIdentificacion,
  titular: TITULAR,
  get paquete() { return PAQUETE; },
};
