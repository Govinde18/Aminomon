"""Logros: se desbloquean solos al cumplir su condición y se ven en una pantalla
con barras de avance. Los contadores viven en juego["stats"]."""

import curses

import datos
import dibujo as d
import enzimas
import jefes
import mapa
import modos
import motivos
import progreso
import sonido
from idioma import tr


def _stat(clave):
    return lambda j: j.get("stats", {}).get(clave, 0)


def _aromaticos(j):
    return sum(1 for c in "FYW" if progreso.capturado(j, c))


def _diario(j):
    return j.get("diario", {}).get("racha", 0)


# (id, nombre, descripción, función de avance, meta)
LOGROS = [
    ("primera", tr("Primer contacto"), tr("Captura tu primer aminoácido salvaje."), _stat("salvajes"), 1),
    ("diez", tr("Coleccionista"), tr("Captura 10 aminoácidos salvajes."), _stat("salvajes"), 10),
    ("treinta", tr("Biblioteca"), tr("Captura 30 aminoácidos salvajes."), _stat("salvajes"), 30),
    ("aromaticos", tr("Anillos de colección"), tr("Captura Phe, Tyr y Trp."), _aromaticos, 3),
    ("aminodex", tr("Los veinte"), tr("Completa la Aminodex."),
     lambda j: sum(1 for c in datos.ORDEN if progreso.capturado(j, c)), 20),
    ("combo5", tr("Racha química"), tr("Encadena un combo ×5 en un combate."), _stat("combo_max"), 5),
    ("criticos", tr("Afinidad total"), tr("Haz 25 interacciones muy afines (×2 o más)."),
     _stat("criticos"), 25),
    ("limpias", tr("Capturas limpias"), tr("Captura 10 aminoácidos sin recibir daño."),
     _stat("limpias"), 10),
    ("ph", tr("Maestro del tampón"), tr("Cambia el pH del arena 10 veces."), _stat("ph_cambios"), 10),
    ("raras", tr("Variante rara"), tr("Captura una variante rara (♥)."), _stat("raras"), 1),
    ("motivos", tr("Arquitecto de motivos"), tr("Activa los 5 motivos estructurales."),
     lambda j: len(j.get("motivos_vistos", [])), len(motivos.ORDEN)),
    ("insignias", tr("Campeón de la célula"), tr("Consigue todas las insignias de zona."),
     lambda j: len(j.get("insignias", [])), len(jefes.JEFES)),
    ("ptm", tr("Modificado"), tr("Consigue todas las modificaciones postraduccionales."),
     lambda j: sum(1 for e in datos.MODIFICACIONES if e in j.get("evos_vistas", [])),
     len(datos.MODIFICACIONES)),
    ("misiones", tr("Mano derecha de las enzimas"), tr("Cumple los encargos de todas las enzimas."),
     enzimas.hechas, enzimas.TOTAL),
    ("viajes", tr("Red de vesículas"), tr("Descubre todas las estaciones de vesículas."),
     lambda j: len(j.get("vesiculas", [])), len(mapa.ESTACIONES)),
    ("diario3", tr("Constancia"), tr("Completa el reto diario 3 días seguidos."), _diario, 3),
    ("diario7", tr("Hábito"), tr("Completa el reto diario 7 días seguidos."), _diario, 7),
    ("modo_dificil", tr("Bioquímico"), tr("Desbloquea el modo Difícil."),
     lambda j: int("dificil" in modos.abiertos(j)), 1),
    ("gym", tr("Sin puntos débiles"), tr("Saca 10/10 en el gimnasio de repaso."),
     _stat("gym_perfecto"), 1),
]
POR_ID = {l[0]: l for l in LOGROS}


def avance(juego, logro):
    _, _, _, f, meta = logro
    return min(f(juego), meta), meta


def revisar(juego):
    """Desbloquea los logros cumplidos. Devuelve la lista de recién ganados."""
    ganados = juego.setdefault("logros", [])
    nuevos = []
    for logro in LOGROS:
        if logro[0] in ganados:
            continue
        v, meta = avance(juego, logro)
        if v >= meta:
            ganados.append(logro[0])
            nuevos.append(logro)
    return nuevos


def avisar(win, juego):
    """Revisa y muestra un aviso por cada logro nuevo."""
    for lid, nombre, desc, _, _ in revisar(juego):
        sonido.reproducir("logro")
        d.popup(win, f"{nombre}\n\n{desc}", tr("Logro desbloqueado"), ancho=52, attr=d.c("bien"))


def mostrar(win, juego):
    sel = 0
    while True:
        alto, ancho = win.getmaxyx()
        win.erase()
        d.reiniciar_regiones()
        ganados = set(juego.get("logros", []))
        d.put(win, 0, 1, tr("LOGROS  {n}/{total}", n=len(ganados), total=len(LOGROS)),
              d.c("titulo", curses.A_BOLD))
        d.put(win, 1, 0, "─" * ancho, d.c("tenue"))
        visibles = max(3, alto - 5)
        inicio = max(0, min(sel - visibles // 2, len(LOGROS) - visibles))
        ancho_barra = 14
        for fila, i in enumerate(range(inicio, min(len(LOGROS), inicio + visibles))):
            lid, nombre, desc, _, _ = LOGROS[i]
            v, meta = avance(juego, LOGROS[i])
            ok = lid in ganados
            y = 2 + fila
            attr = d.c("titulo", curses.A_BOLD) if ok else d.c("texto")
            if i == sel:
                attr |= curses.A_REVERSE
            d.put(win, y, 1, f"{'♦' if ok else '◊'} {nombre[:30]:<30}", attr)
            d.barra(win, y, 35, ancho_barra, v, meta, d.c("bien" if ok else "agua"))
            d.put(win, y, 35 + ancho_barra + 1, f"{v}/{meta}", d.c("tenue"))
            d.region(y, 0, 1, ancho, ("sel", i))
        lid, nombre, desc, _, _ = LOGROS[sel]
        y = alto - 3
        for k, linea in enumerate(d.envolver(desc, ancho - 4)[:2]):
            d.put(win, y + k, 2, linea, d.c("texto"))
        d.fila_botones(win, alto - 1, 1, [(tr("Cerrar [Esc]"), d.ESC)])
        win.refresh()
        k = d.tecla(win)
        if isinstance(k, tuple) and k[0] == "sel":
            sel = k[1]
        elif k == d.ESC or d.es(k, "q", "l"):
            return
        elif d.es(k, curses.KEY_DOWN, "j", "s"):
            sel = (sel + 1) % len(LOGROS)
        elif d.es(k, curses.KEY_UP, "k", "w"):
            sel = (sel - 1) % len(LOGROS)
