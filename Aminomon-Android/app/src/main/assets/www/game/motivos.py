"""Motivos estructurales: combinaciones de residuos en tu equipo que dan una
bonificación en combate. Son motivos reales de las proteínas.

Cada requisito es (letras, cantidad): vale cualquiera de las letras y se
cuenta por forma (la Hyp es una forma distinta de la Pro)."""

import curses

import datos
import dibujo as d
from idioma import tr

MOTIVOS = {
    "triada": dict(
        nombre=tr("Tríada catalítica"),
        req=[("S", 1), ("H", 1), ("D", 1)],
        efecto=tr("+30% de afinidad en cada interacción."),
        bio=tr("Ser–His–Asp: la tríada de las serina-proteasas (quimotripsina, tripsina). "
               "La His activa el OH de la Ser para atacar el enlace peptídico y la Asp "
               "orienta a la His."),
    ),
    "zinc": dict(
        nombre=tr("Dedo de zinc C2H2"),
        req=[("C", 2), ("H", 2)],
        efecto=tr("Una vez por combate, tu residuo resiste y se queda con 1 de energía."),
        bio=tr("Dos Cys y dos His sujetan un ion Zn2+ y pliegan un dominio pequeño que "
               "reconoce el ADN. Sin el zinc, el dedo se desordena."),
    ),
    "cremallera": dict(
        nombre=tr("Cremallera de leucina"),
        req=[("L", 3), ("KR", 1)],
        efecto=tr("Empiezas cada combate con +1 ATP (máximo 9)."),
        bio=tr("Una Leu cada 7 residuos forma una cara hidrofóbica por la que dos hélices "
               "se enrollan. Una región básica (Lys o Arg) agarra el ADN."),
    ),
    "colageno": dict(
        nombre=tr("Triple hélice de colágeno"),
        req=[("G", 1), ("P", 1), ("Hyp", 1)],
        efecto=tr("Recibes 3 de daño menos por turno (mínimo 1)."),
        bio=tr("Gly–Pro–Hyp es el tripéptido que se repite en el colágeno. La Hyp, hecha "
               "con vitamina C, estabiliza la triple hélice."),
    ),
    "rgd": dict(
        nombre=tr("Motivo RGD"),
        req=[("R", 1), ("G", 1), ("D", 1)],
        efecto=tr("+20 puntos de probabilidad al lanzar el ARNt."),
        bio=tr("Arg–Gly–Asp: la secuencia que reconocen las integrinas para pegar las "
               "células a la fibronectina de la matriz extracelular."),
    ),
}
ORDEN = list(MOTIVOS)


def _conteo(juego):
    conteo = {}
    for m in juego["equipo"]:
        conteo[m["id"]] = conteo.get(m["id"], 0) + 1
    return conteo


def _falta(juego, motivo):
    """Lista de (letras, cantidad que falta) para completar el motivo."""
    conteo = _conteo(juego)
    faltan = []
    for letras, n in MOTIVOS[motivo]["req"]:
        # las letras de un grupo se consumen en orden; cada residuo vale una vez
        hay = sum(conteo.get(c, 0) for c in (letras if letras != "Hyp" else ["Hyp"]))
        if hay < n:
            faltan.append((letras, n - hay))
    return faltan


def activo(juego, motivo):
    return not _falta(juego, motivo)


def activos(juego):
    return [m for m in ORDEN if activo(juego, m)]


def nombre_residuo(letras):
    """«Lys o Arg» para ("KR"), «Hyp» para ("Hyp")."""
    if letras == "Hyp":
        return datos.MODIFICACIONES["Hyp"]["nombre"]
    return tr(" o ").join(datos.AMINOACIDOS[c]["tres"] for c in letras)


def texto_requisitos(motivo):
    partes = []
    for letras, n in MOTIVOS[motivo]["req"]:
        partes.append((f"{n}× " if n > 1 else "") + nombre_residuo(letras))
    return " + ".join(partes)


def texto_faltan(juego, motivo):
    return ", ".join(f"{n}× " + nombre_residuo(letras) for letras, n in _falta(juego, motivo))


def nuevos(juego):
    """Motivos activos que aún no se habían avisado (y los marca como vistos)."""
    vistos = juego.setdefault("motivos_vistos", [])
    nuevos_ = [m for m in activos(juego) if m not in vistos]
    vistos.extend(nuevos_)
    return nuevos_


def mostrar(win, juego):
    """Lista de motivos con lo que tienes y lo que te falta."""
    sel = 0
    while True:
        alto, ancho = win.getmaxyx()
        win.erase()
        d.reiniciar_regiones()
        d.put(win, 0, 1, tr("MOTIVOS ESTRUCTURALES  ·  combinaciones de tu equipo que dan bonificaciones"),
              d.c("titulo", curses.A_BOLD))
        d.put(win, 1, 0, "─" * ancho, d.c("tenue"))
        for i, m in enumerate(ORDEN):
            ok = activo(juego, m)
            attr = d.c("bien" if ok else "texto", curses.A_BOLD if ok else 0)
            if i == sel:
                attr |= curses.A_REVERSE
            d.put(win, 2 + i, 1, f"{'♦' if ok else '◊'} {MOTIVOS[m]['nombre']:<30}", attr)
            d.region(2 + i, 0, 1, 36, ("sel", i))
        m = ORDEN[sel]
        info = MOTIVOS[m]
        y = 4 + len(ORDEN)
        d.put(win, y, 1, tr("Necesitas: {req}", req=texto_requisitos(m)), d.c("titulo"))
        y += 1
        if activo(juego, m):
            d.put(win, y, 1, tr("¡Activo!"), d.c("bien", curses.A_BOLD))
        else:
            d.put(win, y, 1, tr("Te falta: {lista}", lista=texto_faltan(juego, m)), d.c("mal"))
        y += 2
        d.put(win, y, 1, tr("Efecto: {efecto}", efecto=info["efecto"]), d.c("texto", curses.A_BOLD))
        y += 2
        for linea in d.envolver(info["bio"], min(ancho - 4, 96)):
            d.put(win, y, 1, linea, d.c("tenue"))
            y += 1
        d.fila_botones(win, alto - 1, 1, [(tr("Cerrar [Esc]"), d.ESC)])
        win.refresh()
        k = d.tecla(win)
        if isinstance(k, tuple) and k[0] == "sel":
            sel = k[1]
        elif k == d.ESC or d.es(k, "q", "k"):
            return
        elif d.es(k, curses.KEY_DOWN, "j", "s"):
            sel = (sel + 1) % len(ORDEN)
        elif d.es(k, curses.KEY_UP, "w"):
            sel = (sel - 1) % len(ORDEN)
