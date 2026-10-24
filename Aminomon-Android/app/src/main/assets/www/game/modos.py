"""Modos de juego: Fácil (estructura) → Medio (propiedades e interacciones
simples) → Difícil (el juego completo). Se desbloquean capturando."""

import curses

import dibujo as d
import sonido
from idioma import tr

NIVELES = ["facil", "medio", "dificil"]
# (contador de capturas, cuántas hacen falta) para abrir cada modo
META = {"medio": ("capt_facil", 5), "dificil": ("capt_medio", 6)}
PROPIEDADES_MEDIO = ["carga", "grupo", "nutricion"]

INFO = {
    "facil": dict(
        nombre=tr("Fácil"), lema=tr("Aprende la estructura"),
        desc=tr("Solo la estructura: reconoce al aminoácido por su nombre, su código de 3 letras "
                "y su código de 1 letra, con opciones para elegir. No hay energía ni daño y no "
                "puedes perder: si te equivocas, ves la respuesta y lo intentas otra vez.")),
    "medio": dict(
        nombre=tr("Medio"), lema=tr("Propiedades e interacciones simples"),
        desc=tr("Ves el grupo del rival desde el principio y eliges interacciones para subir la "
                "afinidad. Con afinidad 50 o más, el ARNt siempre se une si aciertas la pregunta "
                "(carga, grupo de Lehninger o nutrición). Sin pH, sin rasgos y con poco daño.")),
    "dificil": dict(
        nombre=tr("Difícil"), lema=tr("El juego completo"),
        desc=tr("Deducir el grupo, pH del arena, rasgos de cada aminoácido, motivos, "
                "probabilidad del ARNt y todas las preguntas: pKR, pI, codones, hidropatía.")),
}


def actual(juego):
    m = juego.get("modo", "facil")
    return m if m in NIVELES and m in abiertos(juego) else "facil"


def abiertos(juego):
    ab = juego.setdefault("modos_abiertos", ["facil"])
    if "facil" not in ab:
        ab.insert(0, "facil")
    return ab


def avance(juego, modo):
    """(llevas, meta) para abrir el modo, o None si ya está abierto."""
    if modo in abiertos(juego):
        return None
    clave, meta = META[modo]
    return min(juego.get("stats", {}).get(clave, 0), meta), meta


def revisar(juego):
    """Abre los modos cuyo requisito se cumple. Devuelve los recién abiertos."""
    nuevos = []
    for modo in NIVELES[1:]:
        av = avance(juego, modo)
        if av and av[0] >= av[1]:
            abiertos(juego).append(modo)
            nuevos.append(modo)
    return nuevos


def avisar(win, juego):
    nuevos = revisar(juego)
    for modo in nuevos:
        info = INFO[modo]
        sonido.reproducir("logro")
        d.popup(win, tr("¡Modo {nombre} desbloqueado!", nombre=info["nombre"]) + "\n\n"
                + info["desc"] + "\n\n" + tr("Cámbialo cuando quieras en el menú [N]."),
                tr("Nuevo modo"), ancho=64, attr=d.c("bien"))
    return nuevos


def _fila(juego, modo):
    info = INFO[modo]
    if modo not in abiertos(juego):
        v, meta = avance(juego, modo)
        origen = INFO[NIVELES[NIVELES.index(modo) - 1]]["nombre"]
        return tr("{nombre}  ·  bloqueado: captura {n} en {origen} ({v}/{n})",
                  nombre=info["nombre"], n=meta, origen=origen, v=v)
    marca = "►" if modo == actual(juego) else " "
    return f"{marca} {info['nombre']}  ·  {info['lema']}"


def elegir(win, juego):
    """Menú para cambiar de modo. Devuelve True si cambió."""
    sel = NIVELES.index(actual(juego))
    while True:
        sel = d.menu(win, tr("Modo de juego"), [_fila(juego, m) for m in NIVELES],
                     inicial=sel, ancho=72, ayuda=tr("Enter o clic para elegir"))
        if sel is None:
            return False
        modo = NIVELES[sel]
        d.popup(win, INFO[modo]["desc"], INFO[modo]["nombre"], ancho=64)
        if modo not in abiertos(juego):
            continue
        if modo != actual(juego):
            juego["modo"] = modo
            return True
        return False
