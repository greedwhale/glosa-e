"""Tipos comunes para contar lo que está mal en una factura.

Estaban dentro de `en16931`, pero las reglas españolas del RD 238/2026 —el
código único, por ejemplo— también necesitan devolver incidencias, y no tiene
sentido que un módulo de reglas nacionales dependa del de la norma europea.
Viven aquí para que ambos puedan usarlos sin importarse el uno al otro.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from validador.formato import Deteccion

ERROR = "error"
AVISO = "aviso"


@dataclass(frozen=True)
class Incidencia:
    """Un incumplimiento concreto, explicado para quien tiene que arreglarlo."""

    codigo: str
    gravedad: str
    mensaje: str
    campo: str | None = None
    esperado: str | None = None
    encontrado: str | None = None

    def texto(self, norma: str | None = None) -> str:
        """La queja escrita, con la norma de la que sale si se sabe.

        Saber si una queja la firma EN 16931 o la firmamos nosotros cambia lo
        que hay que hacer con ella: la primera te la rechaza el receptor, la
        segunda es una opinión. Quién lo decide no es asunto de este módulo
        —aquí no se sabe qué reglamentos existen—, así que la etiqueta llega
        de fuera ya resuelta.
        """
        etiqueta = self.codigo if not norma else f"{self.codigo} · {norma}"
        partes = [f"[{etiqueta}] {self.mensaje}"]
        if self.campo:
            partes.append(f"  Campo: {self.campo}")
        if self.esperado is not None:
            partes.append(f"  Debería ser: {self.esperado}")
        if self.encontrado is not None:
            partes.append(f"  Tiene: {self.encontrado}")
        return "\n".join(partes)

    def __str__(self) -> str:
        return self.texto()


@dataclass
class Informe:
    """Resultado de validar un documento."""

    deteccion: Deteccion | None = None
    incidencias: list[Incidencia] = field(default_factory=list)

    @property
    def errores(self) -> list[Incidencia]:
        return [i for i in self.incidencias if i.gravedad == ERROR]

    @property
    def avisos(self) -> list[Incidencia]:
        return [i for i in self.incidencias if i.gravedad == AVISO]

    @property
    def conforme(self) -> bool:
        return not self.errores

    @property
    def validado(self) -> bool:
        """Se ha podido identificar el documento y aplicarle reglas.

        Falso cuando el fichero no existe, no se puede leer, o no se reconoce
        su formato. Un documento así **no es correcto ni incorrecto: es que no
        se ha mirado**, y hay que contarlo aparte.

        Sin esta distinción, `conforme` decía que sí —no hay errores porque no
        hay nada— y un fichero inexistente aparecía en el resumen entre los
        buenos. Dar por bueno lo que no se ha visto es lo peor que puede hacer
        un validador: quien se equivoca al escribir una ruta se queda tan
        tranquilo creyendo que ha revisado un lote que nadie ha abierto.
        """
        return self.deteccion is not None and bool(self.deteccion)

    def __bool__(self) -> bool:
        return self.conforme

    def resumen(self) -> str:
        # Ojo: `Deteccion` define __bool__, así que hay que preguntar por None
        # explícitamente. Escrito como `self.deteccion and not self.deteccion`
        # la condición es siempre falsa y el mensaje no salía nunca.
        if self.deteccion is not None and not self.deteccion:
            return f"No se ha podido validar. {self.deteccion.motivo}"
        cabecera = self.deteccion.resumen() if self.deteccion else "Documento"
        if self.conforme:
            cola = "sin errores"
            if self.avisos:
                cola += f", {len(self.avisos)} aviso(s)"
            return f"{cabecera} — {cola}."
        return (
            f"{cabecera} — {len(self.errores)} error(es)"
            f"{f', {len(self.avisos)} aviso(s)' if self.avisos else ''}."
        )

    def detalle(self, norma=None) -> str:
        """El informe entero. `norma` dice de qué reglamento sale cada queja.

        Es una función `Incidencia -> str`; quien orquesta pasa la suya
        (`factura.origen`). Sin ella el informe sale como siempre.
        """
        lineas = [self.resumen()]
        for incidencia in self.errores + self.avisos:
            lineas.append("")
            lineas.append(incidencia.texto(norma(incidencia) if norma else None))
        return "\n".join(lineas)
