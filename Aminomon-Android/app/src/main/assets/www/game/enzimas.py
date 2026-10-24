"""Enzimas que piden encargos y estaciones de vesículas (viaje rápido).

Cada enzima (Ω en el mapa) te pide algo que se aprende jugando; al cumplirlo
da un premio. Las vesículas (¤) se descubren pisándolas y, con dos o más, te
llevan de una a otra."""

import curses

import datos
import dibujo as d
import mapa
import motivos
import progreso
import sonido
from idioma import tr

SOLO = {"pS", "pT", "pY"}


def _tiene_fosfo(juego, base):
    n = sum(1 for m in juego["equipo"] if m["id"] in SOLO)
    return n >= 1, tr("residuos fosforilados en tu equipo: {n}/1", n=min(n, 1))


def _captura_ph(juego, base):
    n = juego.get("stats", {}).get("capt_ph", 0) - base
    return n >= 2, tr("capturas tras cambiar el pH: {n}/2", n=max(0, n))


def _motivo(clave):
    def comprobar(juego, base):
        ok = motivos.activo(juego, clave)
        if ok:
            return True, tr("motivo activo")
        return False, tr("te falta: {lista}", lista=motivos.texto_faltan(juego, clave))
    return comprobar


MISIONES = {
    "enz_quinasa": dict(
        nombre=tr("Quinasa"),
        saludo=tr("Soy una proteína quinasa: tomo el fosfato γ de un ATP y lo pego al OH "
                  "de una Ser, Thr o Tyr. Esa carga − enciende o apaga a la proteína."),
        pedido=tr("Fosforila uno de tus residuos: ten una pSer, pThr o pTyr en tu equipo."),
        pista=tr("Elige una Ser, Thr o Tyr en Equipo [E] y pulsa V. Pide ATP y un nivel mínimo."),
        comprobar=_tiene_fosfo, iniciar=lambda j: 0,
        premio=dict(ATP=3, xp=10),
    ),
    "enz_catepsina": dict(
        nombre=tr("Catepsina"),
        saludo=tr("Soy una catepsina: una cisteín-proteasa que solo trabaja bien con el "
                  "pH ácido del lisosoma. Todo en la célula depende del pH."),
        pedido=tr("Captura 2 aminoácidos después de cambiar el pH del arena en el combate [P]."),
        pista=tr("En un combate, pulsa P y gasta 1 ATP para subir o bajar el pH. La His, el Asp, "
                 "el Glu, la Cys y la Tyr cambian de carga."),
        comprobar=_captura_ph, iniciar=lambda j: j.get("stats", {}).get("capt_ph", 0),
        premio=dict(ATP=2, vit_c=1),
    ),
    "enz_prolil": dict(
        nombre=tr("Prolil hidroxilasa"),
        saludo=tr("Soy la prolil hidroxilasa: pongo OH a las prolinas del colágeno usando "
                  "vitamina C. Sin mí, la triple hélice no se estabiliza."),
        pedido=tr("Reúne en tu equipo Gly, Pro e Hyp para formar la triple hélice de colágeno."),
        pista=tr("La Hyp es una Pro modificada con vitamina C (hay en la matriz extracelular)."),
        comprobar=_motivo("colageno"), iniciar=lambda j: 0,
        premio=dict(ATP=2, vit_c=1),
    ),
    "enz_tripsina": dict(
        nombre=tr("Tripsina"),
        saludo=tr("Soy una serina-proteasa: corto proteínas justo después de una Lys o una "
                  "Arg. Mi sitio activo es una tríada de tres residuos."),
        pedido=tr("Reúne en tu equipo la tríada catalítica: Ser, His y Asp."),
        pista=tr("La Ser vive en el citosol, la His en el lisosoma y el Asp en el retículo."),
        comprobar=_motivo("triada"), iniciar=lambda j: 0,
        premio=dict(ATP=3, vit_k=1),
    ),
}
TOTAL = len(MISIONES)


def hechas(juego):
    return sum(1 for m in juego.get("misiones", {}).values() if m.get("estado") == "hecha")


def _entregar(juego, premio):
    partes = []
    if premio.get("ATP"):
        juego["objetos"]["ATP"] += premio["ATP"]
        partes.append(f"+{premio['ATP']} ATP")
    for clave, objeto in (("vit_c", "Vitamina C"), ("vit_k", "Vitamina K")):
        if premio.get(clave):
            antes = juego["objetos"].get(objeto, 0)
            juego["objetos"][objeto] = min(3, antes + premio[clave])
            if juego["objetos"][objeto] > antes:
                partes.append(f"+1 {tr(objeto)}")
    if premio.get("xp"):
        for m in juego["equipo"]:
            progreso.dar_xp(m, premio["xp"])
        partes.append(tr("+{n} XP para todo tu equipo", n=premio["xp"]))
    return ", ".join(partes)


def hablar(win, juego, nombre):
    """Conversación con una enzima. Devuelve True si cambió la partida."""
    m = MISIONES[nombre]
    misiones = juego.setdefault("misiones", {})
    est = misiones.get(nombre)
    titulo = m["nombre"]
    if est is None:
        d.popup(win, m["saludo"] + "\n\n" + tr("Encargo: {pedido}", pedido=m["pedido"]), titulo, ancho=64)
        if d.menu(win, tr("¿Aceptas el encargo de la {nombre}?", nombre=titulo),
                  [tr("Sí, acepto"), tr("Ahora no")]) == 0:
            misiones[nombre] = dict(estado="activa", base=m["iniciar"](juego))
            d.popup(win, tr("Encargo aceptado: {pedido}", pedido=m["pedido"]), titulo, ancho=64)
            return True
        return False
    if est["estado"] == "hecha":
        d.popup(win, tr("¡Gracias! Cuando necesites más química, aquí sigo."), titulo)
        return False
    ok, progreso_txt = m["comprobar"](juego, est.get("base", 0))
    if not ok:
        d.popup(win, tr("Encargo: {pedido}", pedido=m["pedido"]) + "\n\n"
                + tr("Progreso: {txt}", txt=progreso_txt) + "\n\n"
                + tr("Pista: {pista}", pista=m["pista"]), titulo, ancho=64)
        return False
    est["estado"] = "hecha"
    texto = _entregar(juego, m["premio"])
    sonido.reproducir("logro")
    d.popup(win, tr("¡Encargo cumplido! Premio: {premio}.", premio=texto), titulo,
            ancho=64, attr=d.c("bien"))
    return True


# ------------------------------------------------------------- vesículas
def nombre_estacion(clave):
    x, y, _ = mapa.ESPECIALES[clave]
    return datos.ZONAS[mapa.zona(x, y)]["nombre"]


def estacion(win, juego, clave):
    """Pisar una vesícula: se descubre, y con 2 o más puedes viajar.
    Devuelve (x, y) del destino o None."""
    vis = juego.setdefault("vesiculas", [])
    nueva = clave not in vis
    if nueva:
        vis.append(clave)
        sonido.reproducir("logro")
        d.popup(win, tr("Descubriste una estación de vesículas ({zona}). Las vesículas viajan por "
                        "los microtúbulos entre organelos: desde cualquier estación puedes ir a "
                        "las otras que hayas descubierto.", zona=nombre_estacion(clave)),
                tr("Vesícula"), ancho=60, attr=d.c("bien"))
    destinos = [c for c in mapa.ESTACIONES if c in vis and c != clave]
    if not destinos:
        if not nueva:
            d.popup(win, tr("Aún no has descubierto otras estaciones. Hay {n} en total."
                            , n=len(mapa.ESTACIONES)), tr("Vesícula"))
        return None
    opciones = [nombre_estacion(c) for c in destinos]
    faltan = len(mapa.ESTACIONES) - len(vis)
    ayuda = tr("Quedan {n} por descubrir", n=faltan) if faltan else tr("Las descubriste todas")
    sel = d.menu(win, tr("Viajar en vesícula"), opciones, ayuda=ayuda)
    if sel is None:
        return None
    sonido.reproducir("viaje")
    x, y, _ = mapa.ESPECIALES[destinos[sel]]
    return x, y
