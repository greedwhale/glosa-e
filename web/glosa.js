// El arranque, compartido por la pagina y por el banco de pruebas.
//
// Las dos necesitan lo mismo: Pyodide, lxml, el wheel del validador, el
// paquete de esquemas y anclas, y las facturas de ejemplo. Estaba escrito dos
// veces —una en cada pagina— y esa es la forma de que un dia arreglen cosas
// distintas y nadie se entere de cual de las dos es la que corre.

// Esta version se fija a proposito y no se sigue a «latest»: lo que se prueba
// aqui es una combinacion concreta de Pyodide, lxml y libxml2. Si se mueve
// sola, el dia que algo se rompa no se sabra que ha cambiado.
const VERSION_PYODIDE = "314.0.6";
const RAIZ = "https://cdn.jsdelivr.net/pyodide/v" + VERSION_PYODIDE + "/full/";

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

// El nombre del wheel lleva la version dentro, asi que no se escribe a mano:
// si no, cada vez que suba la version en pyproject.toml la pagina dejaria de
// arrancar sin decir por que.
async function buscarWheel() {
  // Un sitio publicado no tiene listado de directorio: Vercel devuelve 404 y
  // aqui no habria wheel que instalar. Por eso `--sitio` deja un rueda.json al
  // lado diciendo cual es. En desarrollo no existe y se cae al listado, que es
  // lo que sirve la carpeta.
  try {
    const manifiesto = await fetch(DIST + "rueda.json?v=" + Date.now());
    if (manifiesto.ok) {
      const { rueda } = await manifiesto.json();
      if (rueda) return DIST + rueda + "?v=" + Date.now();
    }
  } catch (_) {
    // Un rueda.json ilegible no es motivo para no probar el listado.
  }
  const listado = await fetch(DIST);
  if (listado.ok) {
    const nombres = [...(await listado.text()).matchAll(/href="([^"]+\.whl)"/g)]
      .map((m) => decodeURIComponent(m[1].split("/").pop()));
    // El `?v=` es por precaucion: el nombre del wheel no cambia entre
    // compilaciones de la misma version, asi que sin esto el navegador puede
    // servir el de la cache y la pagina correria una version vieja del
    // validador sin decirlo.
    if (nombres.length) return DIST + nombres.sort().pop() + "?v=" + Date.now();
  }
  throw new Error(
    "No hay ningun .whl en " + DIST + ", ni suelto ni anunciado en rueda.json."
  );
}

async function traerPaquete() {
  // El JSON primero y aparte: es un pellizco y permite decir de donde salen
  // las anclas aunque el zip falle, que es justo cuando hace falta decirlo.
  try {
    const resumen = await fetch("./PAQUETE.json?v=" + Date.now());
    if (resumen.ok) PAQUETE = await resumen.json();
  } catch (_) {
    PAQUETE = null;
  }
  if (!PAQUETE) return;
  try {
    const zip = await fetch("./paquete.zip?v=" + Date.now());
    if (!zip.ok) throw new Error("no esta el zip");
    pyodide.FS.mkdirTree(DENTRO);
    await pyodide.unpackArchive(await zip.arrayBuffer(), "zip",
                                { extractDir: DENTRO });
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

// Arranca el validador entero. `avisar(etiqueta, segundos)` se llama al
// terminar cada fase, para que cada pagina lo cuente como quiera.
async function arrancar(avisar) {
  const decir = avisar || function () {};
  const cero = performance.now();
  let t = cero;
  const seg = (ms) => (ms / 1000).toFixed(2);

  pyodide = await loadPyodide({ indexURL: RAIZ });
  decir("Intérprete de Python (WebAssembly)", seg(performance.now() - t));

  t = performance.now();
  await pyodide.loadPackage("lxml");
  decir("lxml + libxml2", seg(performance.now() - t));

  t = performance.now();
  await pyodide.loadPackage("micropip");
  const micropip = pyodide.pyimport("micropip");
  await micropip.install(await buscarWheel());
  decir("El validador", seg(performance.now() - t));

  t = performance.now();
  await traerPaquete();
  decir("Esquemas y anclas de confianza", seg(performance.now() - t));

  t = performance.now();
  pyodide.FS.mkdirTree("/ejemplos");
  await Promise.all(EJEMPLOS.map(async (nombre) => {
    const respuesta = await fetch(EJEMPLOS_EN + nombre + "?v=" + Date.now());
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
                        _informe.notas + _informe.errores + _informe.avisos],
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

// El banco de pruebas corre su propio fichero de comprobaciones. El `?v=` es
// por lo mismo que el del wheel: sin el, el navegador sirve de su cache una
// version vieja y el banco correria sus comprobaciones de ayer contra el
// codigo de hoy, saliendo todo verde. Paso: se anadieron tres, se recargo, y
// la pagina siguio diciendo «las 33 comprobaciones pasan» tan contenta.
async function correrBanco() {
  const codigo = await (await fetch("./prueba.py?v=" + Date.now())).text();
  return JSON.parse(await pyodide.runPythonAsync(codigo));
}

window.Glosa = { arrancar, validar, correrBanco, get paquete() { return PAQUETE; } };
