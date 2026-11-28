// El guía: un asistente en la esquina de cada página.
//
// Un botón abajo a la derecha abre un panel con tres pestañas: Inicio, con lo
// que más se pregunta; Preguntas, donde se escribe la duda y sale la
// respuesta; y Ayuda, que dice qué es esto y qué no. Desde el 17-11-2026, por
// decisión del titular, que no quería una página aparte sino algo que
// acompañe al que navega, como los asistentes de otros sitios.
//
// No es un modelo de lenguaje y no redacta nada: busca entre textos ya
// publicados y comprobados, y cuando no encuentra, lo dice. Lo que sabe viaja
// en `guia.json`, que arma `validador/guia.py` al montar el sitio, y no se
// pide hasta que alguien abre el panel. La pregunta no sale del navegador.
//
// No se escribe en ninguna página: la etiqueta que lo carga la pone el
// montaje en todas, con la huella de este fichero en la dirección. Así no hay
// ocho copias que se separen, y una página nueva lo lleva sin acordarse.
//
// Al minuto en la misma página, si nadie lo ha abierto, pregunta si hay
// alguna duda. Es un temporizador y no un oyente: el robot de la prueba en
// directo de Google mueve el ratón (ver tests/test_arranque_al_primer_gesto.py),
// y nada de esto arranca con el ratón. Tampoco se apunta en el navegador que
// ya se dijo: el aviso legal publica el almacenamiento vacío, así que en la
// página siguiente, al minuto, vuelve a preguntar.
(function () {
  "use strict";
  // Dónde está lo que el guía sabe. Al montar el sitio se le pone la huella
  // del fichero, así que esta línea tiene que seguir escrita tal cual.
  const DATOS_EN = "./guia.json";
  const AL_MINUTO = 60 * 1000;
  const SVG = "http://www.w3.org/2000/svg";

  let datos = null;
  let pidiendo = null;
  let abiertoAlgunaVez = false;
  let aviso = null;

  // --- Los dibujos ----------------------------------------------------------
  // El signo es el de la marca, el corchete con las líneas de la glosa: el
  // mismo trazo que pinta `.marca::before` en glosa.css.
  //
  // El globo es la forma del botón: un mensaje, con la cola abajo a la
  // derecha, hacia la esquina de la que sale. Desde el 17-11-2026, por
  // decisión del titular; antes el botón era un círculo. El cuerpo mide 60
  // por 44 y la cola baja hasta 55; el signo va en el centro del cuerpo.

  const TRAZOS = {
    globo: ["0 0 60 56", "M18 0H42A18 18 0 0 1 60 18V55Q54 49 44 44H18A18 18 0 0 1 0 26V18A18 18 0 0 1 18 0Z"],
    signo: ["0 0 48 40", "M16 7 H8 V33 H16", "M25 12 h21", "M25 20 h21", "M25 28 h13"],
    bajar: ["0 0 24 24", "M6 9l6 6 6-6"],
    cerrar: ["0 0 24 24", "M6 6l12 12", "M18 6L6 18"],
    seguir: ["0 0 24 24", "M5 12h14", "M13 6l6 6-6 6"],
    fuera: ["0 0 24 24", "M14 4h6v6", "M20 4l-9 9", "M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"],
    buscar: ["0 0 24 24", "M11 4a7 7 0 1 0 0 14a7 7 0 1 0 0-14z", "M20 20l-4.2-4.2"],
    inicio: ["0 0 24 24", "M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6h-6v6H5a1 1 0 0 1-1-1z"],
    preguntas: ["0 0 24 24", "M4 5h16v11H9l-5 4z", "M8 9h8", "M8 12h5"],
    ayuda: ["0 0 24 24", "M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18z", "M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .8-1 1.5v.7", "M12 17h.01"],
    enviar: ["0 0 24 24", "M4 12l16-8-6 16-2.5-6.5z"],
  };

  function dibujo(nombre, clase) {
    const [caja, ...trazos] = TRAZOS[nombre];
    const svg = document.createElementNS(SVG, "svg");
    svg.setAttribute("viewBox", caja);
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    svg.setAttribute("class", clase || "guia-dibujo");
    trazos.forEach(function (d) {
      const trazo = document.createElementNS(SVG, "path");
      trazo.setAttribute("d", d);
      svg.appendChild(trazo);
    });
    return svg;
  }

  // Todo con nodos y textContent: lo que escribe el visitante nunca entra en
  // la página como HTML.
  function nodo(etiqueta, clase, texto) {
    const nuevo = document.createElement(etiqueta);
    if (clase) nuevo.className = clase;
    if (texto) nuevo.textContent = texto;
    return nuevo;
  }

  function enlace(texto, url, deFuera) {
    const a = nodo("a", "", texto);
    a.href = url;
    if (deFuera) { a.target = "_blank"; a.rel = "noopener noreferrer"; }
    return a;
  }

  function boton(clase, texto) {
    const b = nodo("button", clase, texto);
    b.type = "button";
    return b;
  }

  // --- Los datos ------------------------------------------------------------

  function cargar() {
    if (!pidiendo) {
      pidiendo = fetch(DATOS_EN).then(function (respuesta) {
        if (!respuesta.ok) throw new Error("HTTP " + respuesta.status);
        return respuesta.json();
      }).then(function (leido) {
        leido.lasVacias = new Set(leido.vacias);
        leido.lasPropias = new Set(leido.propias);
        datos = leido;
        tarjetaDeCorreo.href = "mailto:" + leido.correo + "?subject=" +
          encodeURIComponent("Glosa-e: pregunta");
        tarjetaDeCorreo.hidden = false;
        return leido;
      }).catch(function (error) {
        pidiendo = null;
        throw error;
      });
    }
    return pidiendo;
  }

  // --- Trocear y buscar -----------------------------------------------------
  // Lo mismo que hace validador/guia.py, que es la referencia y la que tiene
  // pruebas. Para que estas dos copias no se separen sin que nadie lo vea, el
  // fichero trae preguntas con la respuesta que da aquella, y el guía las
  // repite al abrir cualquier página con #comprobar-guia.

  function tiene(objeto, clave) { return Object.prototype.hasOwnProperty.call(objeto, clave); }

  function sinAcentos(texto) {
    return texto.toLowerCase().normalize("NFD").replace(/\p{Mn}/gu, "");
  }

  function raiz(palabra) {
    if (!/^[a-z]+$/.test(palabra) || datos.lasPropias.has(palabra)) return palabra;
    if (palabra.length > 4 && palabra.endsWith("es")) palabra = palabra.slice(0, -2);
    else if (palabra.length > 4 && palabra.endsWith("s")) palabra = palabra.slice(0, -1);
    if (palabra.length > 3 && palabra.endsWith("e")) palabra = palabra.slice(0, -1);
    return palabra;
  }

  function trocear(texto) {
    const piezas = [];
    const encajes = sinAcentos(texto).match(/[a-z0-9]+(?:-[a-z0-9]+)*/g) || [];
    encajes.forEach(function (encaje) {
      const partes = (encaje.indexOf("-") >= 0 && /[0-9]/.test(encaje))
        ? [encaje.split("-").join("")] : encaje.split("-");
      partes.forEach(function (parte) {
        if (datos.lasVacias.has(parte) || parte.length < 2) return;
        const suya = raiz(parte);
        piezas.push(tiene(datos.iguales, suya) ? datos.iguales[suya] : suya);
      });
    });
    return piezas;
  }

  function referencias(consulta) {
    const texto = sinAcentos(consulta).toUpperCase().replace(/[\u2010-\u2014\u2212]/g, "-");
    const encajes = texto.match(new RegExp(datos.patron_codigo, "g")) || [];
    const desconocido = new RegExp(datos.patron_desconocido);
    return Array.from(new Set(encajes.map(c => c.replace(/[ -]+/g, "-"))))
      .filter(c => tiene(datos.referencias, c) || desconocido.test(c));
  }

  function buscar(consulta) {
    const nombrados = referencias(consulta);
    if (nombrados.length) {
      return nombrados.filter(c => tiene(datos.referencias, c)).map(c => datos.referencias[c]);
    }
    const texto = sinAcentos(consulta);
    if (new RegExp(datos.rechazo_ambiguo).test(texto)) return [];
    for (const [numero, patrones] of datos.consultas_directas) {
      if (patrones.every(p => new RegExp(p).test(texto))) {
        if (datos.fichas[numero].id === "pagina-incidencias" &&
            new RegExp(datos.fuera_de_codigos).test(texto)) continue;
        return [numero];
      }
    }
    const piezas = Array.from(new Set(trocear(consulta))).filter(function (pieza) {
      return tiene(datos.indice, pieza);
    });
    if (!piezas.length) return [];
    const puntos = new Map();
    const aciertos = new Map();
    piezas.forEach(function (pieza) {
      datos.indice[pieza].forEach(function (par) {
        puntos.set(par[0], (puntos.get(par[0]) || 0) + par[1]);
        aciertos.set(par[0], (aciertos.get(par[0]) || 0) + 1);
      });
    });
    const hacenFalta = Math.floor((2 * piezas.length + 2) / 3);
    const problema = new RegExp(datos.problema_de_uso).test(texto);
    const validas = Array.from(puntos.keys()).filter(function (n) {
      return aciertos.get(n) >= hacenFalta && puntos.get(n) >= datos.umbral &&
        (!problema || datos.fichas[n].tipo !== "articulo");
    });
    if (!validas.length) return [];
    validas.sort(function (a, b) { return (puntos.get(b) - puntos.get(a)) || (a - b); });
    const mejor = puntos.get(validas[0]);
    return validas.slice(0, 1 + datos.otras).filter(function (n) {
      return puntos.get(n) * 100 >= mejor * datos.cerca &&
        (datos.fichas[n].tipo !== "articulo" || n === validas[0] ||
         datos.fichas[validas[0]].tipo === "articulo");
    });
  }

  // --- El armazón -----------------------------------------------------------

  const raizDelGuia = nodo("div", "guia");

  const lanzador = boton("guia-lanzador");
  lanzador.setAttribute("aria-expanded", "false");
  lanzador.setAttribute("aria-controls", "guia-panel");
  lanzador.setAttribute("aria-label", "Abrir el guía");
  lanzador.appendChild(dibujo("globo", "guia-globo"));
  lanzador.appendChild(dibujo("signo", "guia-dibujo guia-signo"));
  lanzador.appendChild(dibujo("bajar", "guia-dibujo guia-bajar"));

  // Un `div` y no un `section`, y la cabecera tampoco es un `header`: la hoja
  // del sitio da relleno a toda `section` y hace pegajosa y translúcida toda
  // `header`, y dentro del panel eso apagaba el color de la cabecera.
  const panel = nodo("div", "guia-panel");
  panel.id = "guia-panel";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-labelledby", "guia-titulo");
  panel.hidden = true;

  const cabeza = nodo("div", "guia-cabeza");
  const firma = nodo("p", "guia-firma");
  firma.appendChild(dibujo("signo", "guia-dibujo guia-signo"));
  firma.appendChild(nodo("span", "", "Guía de Glosa-e"));
  const cerrar = boton("guia-cerrar");
  cerrar.setAttribute("aria-label", "Cerrar el guía");
  cerrar.appendChild(dibujo("cerrar"));
  const titulo = nodo("h2", "guia-titulo", "¿Tienes una duda?");
  titulo.id = "guia-titulo";
  const entradilla = nodo("p", "guia-entradilla",
    "Pregunta por un código o por una duda sobre la factura electrónica. " +
    "El Guía busca la explicación en Glosa-e y te muestra el enlace. " +
    "Lo que escribes no sale de tu navegador.");
  cabeza.append(firma, cerrar, titulo, entradilla);

  // Inicio: lo que más se pregunta, en tarjetas.
  const vistaInicio = nodo("div", "guia-vista guia-inicio");
  const buscador = nodo("form", "guia-tarjeta guia-buscador");
  const etiqueta = nodo("label", "guia-tapada", "Tu duda");
  etiqueta.htmlFor = "guia-duda-inicio";
  const cajaInicio = nodo("input");
  cajaInicio.id = "guia-duda-inicio";
  cajaInicio.type = "text";
  cajaInicio.autocomplete = "off";
  cajaInicio.maxLength = 300;
  cajaInicio.placeholder = "Escribe tu duda o un código";
  const lupa = nodo("button", "guia-icono");
  lupa.type = "submit";
  lupa.setAttribute("aria-label", "Preguntar");
  lupa.appendChild(dibujo("buscar"));
  buscador.append(etiqueta, cajaInicio, lupa);

  function tarjeta(etiquetaHtml, principal, secundario, cual) {
    const t = nodo(etiquetaHtml, "guia-tarjeta guia-salida");
    if (etiquetaHtml === "button") t.type = "button";
    const textos = nodo("span", "guia-textos");
    textos.append(nodo("span", "guia-principal", principal), nodo("span", "guia-secundario", secundario));
    t.append(textos, dibujo(cual));
    return t;
  }
  const tarjetaObliga = tarjeta("button", "¿Me obliga, y desde cuándo?",
    "Tres preguntas, con la cita del BOE", "seguir");
  const tarjetaCodigos = tarjeta("button", "Tengo un informe con códigos",
    "Pega los códigos y se explica cada uno", "seguir");
  const tarjetaDeCorreo = tarjeta("a", "Escríbeme",
    "Si tu duda no cabe aquí", "fuera");
  tarjetaDeCorreo.hidden = true;
  vistaInicio.append(buscador, tarjetaObliga, tarjetaCodigos, tarjetaDeCorreo);

  // Preguntas: el hilo, con la caja abajo.
  const vistaPreguntas = nodo("div", "guia-vista guia-preguntas");
  const hilo = nodo("div", "guia-hilo");
  hilo.setAttribute("aria-live", "polite");
  const vacio = nodo("p", "guia-vacio", "Todavía no has preguntado nada. " +
    "Escribe abajo tu duda con tus palabras, o el código tal como sale en el informe.");
  hilo.appendChild(vacio);
  const escribir = nodo("form", "guia-escribir");
  const etiqueta2 = nodo("label", "guia-tapada", "Tu duda");
  etiqueta2.htmlFor = "guia-duda";
  const caja = nodo("input");
  caja.id = "guia-duda";
  caja.type = "text";
  caja.autocomplete = "off";
  caja.maxLength = 300;
  caja.placeholder = "me rechazan la factura por el IVA";
  const mandar = nodo("button", "guia-icono");
  mandar.type = "submit";
  mandar.setAttribute("aria-label", "Preguntar");
  mandar.appendChild(dibujo("enviar"));
  escribir.append(etiqueta2, caja, mandar);
  vistaPreguntas.append(hilo, escribir);

  // Ayuda: qué es esto y qué no, y dónde está todo entero.
  const vistaAyuda = nodo("div", "guia-vista guia-ayuda");
  const filas = nodo("ul", "guia-filas");
  [
    ["No es una inteligencia artificial", "No redacta. Busca entre textos ya " +
      "escritos y comprobados, y enseña el que mejor encaja, con su enlace."],
    ["No sale de tu navegador", "Lo que escribes no se manda a ningún sitio. " +
      "La búsqueda corre aquí, igual que el validador."],
    ["Cuando no sabe, lo dice", "Si no encuentra nada que conteste, no " +
      "improvisa: lo dice y te deja escribirme."],
    ["No certifica", "Lo de las fechas y la obligación sale del BOE, con la " +
      "cita al lado. Orienta; lo que cuenta es el texto de la norma."],
    ["No estudia tu caso", "Explica qué significa cada cosa. No ordena los " +
      "fallos de tus facturas ni dice a quién le toca arreglarlos."],
  ].forEach(function (fila) {
    const li = nodo("li");
    li.append(nodo("b", "", fila[0]), nodo("span", "", fila[1]));
    filas.appendChild(li);
  });
  const dondeTitulo = nodo("h3", "guia-subtitulo", "Dónde seguir leyendo");
  const donde = nodo("ul", "guia-donde");
  [
    ["Qué significa cada aviso", "./incidencias"],
    ["Preguntas frecuentes", "./#preguntas"],
    ["Blog", "./bitacora"],
    ["Sobre Glosa-e", "./sobre"],
  ].forEach(function (par) {
    const li = nodo("li");
    li.appendChild(enlace(par[0], par[1], false));
    donde.appendChild(li);
  });
  vistaAyuda.append(nodo("h3", "guia-subtitulo", "Qué es este guía, y qué no"),
    filas, dondeTitulo, donde);

  // Las pestañas, abajo, como en los asistentes que se conocen.
  const pestanas = nodo("nav", "guia-pestanas");
  pestanas.setAttribute("aria-label", "Partes del guía");
  const VISTAS = {
    inicio: [vistaInicio, "Inicio", "¿Tienes una duda?"],
    preguntas: [vistaPreguntas, "Preguntas", "Preguntas"],
    ayuda: [vistaAyuda, "Ayuda", "Ayuda"],
  };
  const botonesDePestana = {};
  Object.keys(VISTAS).forEach(function (cual) {
    const b = boton("guia-pestana");
    b.append(dibujo(cual), nodo("span", "", VISTAS[cual][1]));
    b.addEventListener("click", function () { mostrar(cual); });
    botonesDePestana[cual] = b;
    pestanas.appendChild(b);
  });

  const cuerpo = nodo("div", "guia-cuerpo");
  cuerpo.append(vistaInicio, vistaPreguntas, vistaAyuda);
  panel.append(cabeza, cuerpo, pestanas);

  // El aviso del minuto.
  function crearAviso() {
    const caja = nodo("div", "guia-aviso");
    const abrirlo = boton("guia-aviso-texto", "¿Tienes alguna pregunta?");
    abrirlo.addEventListener("click", function () { abrir("inicio"); });
    const quitar = boton("guia-aviso-quitar");
    quitar.setAttribute("aria-label", "Quitar el aviso");
    quitar.appendChild(dibujo("cerrar"));
    quitar.addEventListener("click", function () { caja.remove(); lanzador.focus(); });
    caja.append(abrirlo, quitar);
    return caja;
  }

  raizDelGuia.append(panel, lanzador);
  document.body.appendChild(raizDelGuia);

  // --- Abrir, cerrar, cambiar de pestaña ------------------------------------

  function mostrar(cual) {
    Object.keys(VISTAS).forEach(function (otra) {
      VISTAS[otra][0].hidden = otra !== cual;
      if (otra === cual) botonesDePestana[otra].setAttribute("aria-current", "page");
      else botonesDePestana[otra].removeAttribute("aria-current");
    });
    panel.setAttribute("data-vista", cual);
    titulo.textContent = VISTAS[cual][2];
  }

  function abrir(cual) {
    abiertoAlgunaVez = true;
    if (aviso) { aviso.remove(); aviso = null; }
    panel.hidden = false;
    raizDelGuia.setAttribute("data-abierto", "si");
    lanzador.setAttribute("aria-expanded", "true");
    lanzador.setAttribute("aria-label", "Cerrar el guía");
    mostrar(cual || "inicio");
    ajustarVentana();
    cargar().catch(function () { /* lo dice quien pregunte */ });
    if ((cual || "inicio") === "inicio") cajaInicio.focus();
    else caja.focus();
  }

  function ajustarVentana() {
    if (!window.visualViewport || panel.hidden) return;
    const { height, offsetTop } = window.visualViewport;
    panel.style.setProperty("--guia-ventana-alto", height + "px");
    panel.style.setProperty("--guia-ventana-arriba", offsetTop + "px");
  }

  if (window.visualViewport) {
    window.visualViewport.addEventListener("resize", ajustarVentana);
    window.visualViewport.addEventListener("scroll", ajustarVentana);
  }

  function cerrarElPanel() {
    panel.hidden = true;
    raizDelGuia.removeAttribute("data-abierto");
    lanzador.setAttribute("aria-expanded", "false");
    lanzador.setAttribute("aria-label", "Abrir el guía");
    lanzador.focus();
  }

  lanzador.addEventListener("click", function () {
    if (panel.hidden) abrir("inicio"); else cerrarElPanel();
  });
  cerrar.addEventListener("click", cerrarElPanel);
  panel.addEventListener("keydown", function (evento) {
    if (evento.key === "Escape") cerrarElPanel();
  });

  // --- Pintar las respuestas ------------------------------------------------

  // Una entrada del hilo: lo que se preguntó y, debajo, lo que contesta.
  // Como en una conversación, la última va abajo, junto a la caja. Se lleva
  // a la vista por su principio y no por su final: una respuesta larga se
  // lee desde el título.
  function entrada(pregunta) {
    if (vacio.parentNode) vacio.remove();
    const una = nodo("article", "guia-entrada");
    if (pregunta) una.appendChild(nodo("p", "guia-tuya", pregunta));
    const respuesta = nodo("div", "guia-respuesta");
    respuesta.tabIndex = -1;
    una.appendChild(respuesta);
    hilo.appendChild(una);
    requestAnimationFrame(function () { hilo.scrollTop = una.offsetTop - 12; });
    return respuesta;
  }

  function fuentes(lista) {
    const ul = nodo("ul", "guia-fuentes");
    lista.forEach(function (fuente) {
      const li = nodo("li", "", "Fuente: ");
      li.appendChild(enlace(fuente[0], fuente[1], true));
      ul.appendChild(li);
    });
    return ul;
  }

  function pintarFicha(donde, ficha) {
    donde.appendChild(nodo("h3", "", ficha.titulo));
    donde.appendChild(nodo("p", "guia-de-donde", ficha.pie));
    if (ficha.corta) donde.appendChild(nodo("p", "guia-corta", ficha.corta + "."));
    donde.appendChild(nodo("p", "", ficha.texto));
    if (ficha.mensajes) {
      const mensajes = nodo("ul");
      ficha.mensajes.forEach(mensaje => mensajes.appendChild(nodo("li", "", mensaje)));
      donde.appendChild(mensajes);
      if (ficha.mensajes.length > 1) compararMensaje(donde, ficha.mensajes);
    }
    if (ficha.aviso) donde.appendChild(nodo("p", "guia-advertencia", ficha.aviso));
    if (ficha.fuentes) donde.appendChild(fuentes(ficha.fuentes));
    if (ficha.url) {
      const p = nodo("p", "guia-ir");
      p.appendChild(enlace(ficha.enlace, ficha.url, false));
      donde.appendChild(p);
    }
  }

  function compararMensaje(donde, mensajes) {
    const formulario = nodo("form", "guia-codigo-directo");
    const etiqueta = nodo("label", "", "Mensaje del acuse");
    const texto = nodo("input");
    texto.required = true;
    texto.maxLength = 600;
    etiqueta.appendChild(texto);
    const enviar = nodo("button", "guia-boton", "Comparar el mensaje");
    enviar.type = "submit";
    const resultado = nodo("p");
    resultado.setAttribute("aria-live", "polite");
    const limpiar = valor => valor.trim().replace(/^"+|"+$/g, "").trim().replace(/\s+/g, " ");
    formulario.addEventListener("submit", function (evento) {
      evento.preventDefault();
      const leido = limpiar(texto.value);
      if (!leido) return;
      const coincide = mensajes.some(function (mensaje) {
        const partes = limpiar(mensaje).split("%s");
        if (!partes[0].trim()) return false;
        const patron = partes.map(parte => parte.replace(/[.*+?^$\x24{}()|[\]\\]/g, "\\$&"));
        return new RegExp("^" + patron.join(".*?")).test(leido);
      });
      resultado.textContent = coincide ? "Coincide con uno de los mensajes de esta regla."
        : "No coincide con los mensajes de esta regla. Puede ser un mensaje general del acuse.";
    });
    formulario.append(etiqueta, enviar);
    donde.append(formulario, resultado);
  }

  function pintarCodigos(donde, numeros) {
    const lista = nodo("div", "guia-codigos");
    numeros.forEach(function (n) {
      const ficha = datos.fichas[n];
      const uno = nodo("div", "guia-codigo");
      if (ficha.tipo === "aeat") {
        pintarFicha(uno, ficha);
        lista.appendChild(uno);
        return;
      }
      uno.appendChild(enlace(ficha.titulo, ficha.url, false));
      uno.appendChild(nodo("span", "guia-gravedad", ficha.pie));
      uno.appendChild(nodo("p", "", ficha.texto));
      lista.appendChild(uno);
    });
    donde.appendChild(lista);
  }

  function sinFicha(donde, nombres) {
    const faltan = nombres.filter(c => !tiene(datos.referencias, c));
    if (faltan.length) donde.appendChild(nodo("p", "", "No encuentro ficha para " +
      faltan.join(", ") + ". Comprueba si el código está escrito tal como sale en el informe."));
  }

  function noLoSe(donde) {
    donde.appendChild(nodo("h3", "", "No lo sé."));
    donde.appendChild(nodo("p", "", "¿Es un aviso del informe o una duda sobre la web? " +
      "Si tienes un aviso, pega su código. Si algo falla en la web, dime en qué paso."));
    const p = nodo("p", "", "Si tu duda no cabe aquí, ");
    p.appendChild(enlace("escríbeme", "mailto:" + datos.correo + "?subject=" +
      encodeURIComponent("Glosa-e: pregunta"), false));
    p.appendChild(document.createTextNode("."));
    donde.appendChild(p);
  }

  function explicarAvisos(donde, ficha) {
    donde.appendChild(nodo("h3", "", "Dónde consultar los códigos"));
    donde.appendChild(nodo("p", "", "Pulsa el código junto al aviso en el informe, " +
      "o pégalo aquí para ver qué significa."));
    const formulario = nodo("form", "guia-codigo-directo");
    const etiqueta = nodo("label", "", "Código del aviso");
    const campo = nodo("input");
    campo.required = true;
    campo.maxLength = 300;
    campo.autocomplete = "off";
    campo.placeholder = "BR-CO-10";
    etiqueta.appendChild(campo);
    const enviar = nodo("button", "guia-boton", "Explicar el código");
    enviar.type = "submit";
    formulario.append(etiqueta, enviar);
    formulario.addEventListener("submit", evento => alPreguntar(evento, campo));
    donde.append(formulario, enlace(ficha.titulo, ficha.url, false));
  }

  function responder(pregunta) {
    const donde = entrada(pregunta);
    donde.focus({ preventScroll: true });
    const encontradas = buscar(pregunta);
    const nombres = referencias(pregunta);
    if (nombres.length) {
      if (encontradas.length === 1) pintarFicha(donde, datos.fichas[encontradas[0]]);
      else if (encontradas.length > 1) pintarCodigos(donde, encontradas);
      sinFicha(donde, nombres);
      return;
    }
    if (new RegExp(datos.rechazo_ambiguo).test(sinAcentos(pregunta))) {
      donde.appendChild(nodo("h3", "", "¿Qué quieres saber sobre el rechazo?"));
      const opciones = nodo("div", "guia-opciones");
      for (const [rotulo, consulta] of [
        ["El plazo para rechazar", "Hasta cuándo puedo rechazar una factura"],
        ["Por qué falla la validación", "Me rechazan la factura al validar"],
      ]) {
        const opcion = boton("guia-opcion", rotulo);
        opcion.addEventListener("click", () => responder(consulta));
        opciones.appendChild(opcion);
      }
      donde.appendChild(opciones);
      return;
    }
    if (!encontradas.length) { noLoSe(donde); return; }
    const primera = datos.fichas[encontradas[0]];
    if (primera.id === "pagina-incidencias") explicarAvisos(donde, primera);
    else pintarFicha(donde, primera);
    if (encontradas.length > 1) {
      const mas = nodo("div", "guia-tambien");
      mas.appendChild(nodo("p", "", "Más sobre la pregunta"));
      const ul = nodo("ul");
      encontradas.slice(1).forEach(function (n) {
        const li = nodo("li");
        const otra = boton("guia-otra", datos.fichas[n].titulo);
        otra.addEventListener("click", function () {
          pintarFicha(entrada(pregunta), datos.fichas[n]);
        });
        li.appendChild(otra);
        ul.appendChild(li);
      });
      mas.appendChild(ul);
      donde.appendChild(mas);
    }
  }

  function cuestionario() {
    const todo = datos.cuestionario;
    const donde = entrada(todo.titulo);
    function paso(nombre) {
      if (tiene(todo.respuestas, nombre)) {
        const final = todo.respuestas[nombre];
        donde.appendChild(nodo("h3", "", final.texto));
        donde.appendChild(fuentes(final.fuentes));
        donde.appendChild(nodo("p", "guia-advertencia", todo.aviso));
        return;
      }
      const este = todo.pasos[nombre];
      donde.appendChild(nodo("p", "guia-paso", este.pregunta));
      const salidas = nodo("div", "guia-opciones");
      este.salidas.forEach(function (salida) {
        const opcion = boton("guia-opcion", salida[0]);
        opcion.addEventListener("click", function () {
          donde.replaceChild(nodo("p", "guia-elegido", salida[0]), salidas);
          paso(salida[1]);
        });
        salidas.appendChild(opcion);
      });
      donde.appendChild(salidas);
      const primera = salidas.querySelector("button");
      if (primera) primera.focus();
    }
    paso(todo.inicio);
  }

  function informe() {
    const donde = entrada("Tengo un informe con códigos");
    donde.appendChild(nodo("p", "", "Pega aquí los códigos de tu informe, o " +
      "el informe entero. Solo se leen los códigos, y no sale de tu navegador."));
    const area = nodo("textarea", "guia-area");
    area.setAttribute("aria-label", "Los códigos de tu informe");
    const explicar = boton("guia-boton", "Explicarlos");
    const resultado = nodo("div");
    explicar.addEventListener("click", function () {
      resultado.textContent = "";
      const nombres = referencias(area.value);
      if (!nombres.length) {
        resultado.appendChild(nodo("p", "", "No he encontrado ningún código " +
          "en ese texto. Son como BR-CO-10 o FIRMA-CADUCADA, y salen a la " +
          "izquierda de cada aviso del informe."));
        return;
      }
      const numeros = nombres.filter(c => tiene(datos.referencias, c)).map(c => datos.referencias[c]);
      if (numeros.length) pintarCodigos(resultado, numeros);
      sinFicha(resultado, nombres);
    });
    donde.append(area, explicar, resultado);
    area.focus();
  }

  // Que esta copia busca igual que la de Python. Se pide a mano, abriendo
  // cualquier página con #comprobar-guia, y lo cuenta en el hilo.
  function comprobar() {
    const donde = entrada("#comprobar-guia");
    const fallos = [];
    datos.comprobaciones.forEach(function (caso) {
      const aqui = buscar(caso[0]).map(function (n) { return datos.fichas[n].id; });
      if (JSON.stringify(aqui) !== JSON.stringify(caso[1])) {
        fallos.push(JSON.stringify(caso[0]) + ": aquí " + JSON.stringify(aqui) +
          ", al montar " + JSON.stringify(caso[1]));
      }
    });
    const total = datos.comprobaciones.length;
    const dicho = nodo("h3", "", (total - fallos.length) + " de " + total +
      " comprobaciones coinciden con las del montaje.");
    dicho.id = "comprobado";
    dicho.setAttribute("data-fallos", String(fallos.length));
    donde.appendChild(dicho);
    fallos.forEach(function (fallo) { donde.appendChild(nodo("p", "", fallo)); });
  }

  // --- Los gestos -----------------------------------------------------------

  function conDatos(hacer) {
    mostrar("preguntas");
    cargar().then(hacer).catch(function () {
      const donde = entrada("");
      donde.appendChild(nodo("h3", "", "El guía no ha podido cargar lo que sabe."));
      donde.appendChild(nodo("p", "", "Vuelve a intentarlo dentro de un momento. " +
        "Mientras tanto, lo mismo está en Qué significa cada aviso, en las " +
        "preguntas frecuentes y en el blog."));
    });
  }

  function alPreguntar(evento, desde) {
    evento.preventDefault();
    const pregunta = desde.value.trim();
    if (!pregunta) { desde.focus(); return; }
    desde.value = "";
    conDatos(function () { responder(pregunta); });
  }
  buscador.addEventListener("submit", function (evento) { alPreguntar(evento, cajaInicio); });
  escribir.addEventListener("submit", function (evento) { alPreguntar(evento, caja); });
  tarjetaObliga.addEventListener("click", function () { conDatos(cuestionario); });
  tarjetaCodigos.addEventListener("click", function () { conDatos(informe); });

  if (location.hash === "#comprobar-guia") {
    abrir("preguntas");
    conDatos(comprobar);
  }

  // Al minuto, si no se ha abierto. Si la pestaña está escondida en ese
  // momento se espera a que vuelva: preguntar a nadie no llama la atención.
  function preguntarSiHayDudas() {
    if (abiertoAlgunaVez || aviso) return;
    if (document.hidden) {
      document.addEventListener("visibilitychange", function alVolver() {
        if (document.hidden) return;
        document.removeEventListener("visibilitychange", alVolver);
        preguntarSiHayDudas();
      });
      return;
    }
    aviso = crearAviso();
    raizDelGuia.insertBefore(aviso, lanzador);
  }
  setTimeout(preguntarSiHayDudas, AL_MINUTO);
})();
