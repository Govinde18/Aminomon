"""Reto diario (los mismos 5 combates para todos ese día) y gimnasio de repaso
(preguntas que sacan tus puntos débiles, con balance al final)."""

import copy
import curses
import datetime
import random

import combate
import datos
import dibujo as d
import preguntas
import progreso
import quimica
import sonido
from idioma import tr

RONDAS = 5
PREGUNTAS_GIMNASIO = 10

MODIFICADORES = [
    ("normal", tr("Sin modificador: pH natural de cada zona."), None, False),
    ("acido", tr("Día ácido: todos los combates empiezan a pH 5.0. La His se carga y el Asp y el "
                 "Glu se protonan."), 5.0, False),
    ("basico", tr("Día básico: todos los combates empiezan a pH 9.0. La Cys y la Tyr pierden su H+ "
                  "y se cargan −."), 9.0, False),
    ("ciego", tr("Día ciego: el grupo del rival no se revela solo. Hay que deducirlo [D]."),
     None, True),
]


def hoy():
    return datetime.date.today()


def plan(fecha):
    """Los 5 combates del día: salen de la fecha, así que son iguales para todos."""
    rng = random.Random(int(fecha.strftime("%Y%m%d")))
    modificador = MODIFICADORES[rng.randrange(len(MODIFICADORES))]
    zonas = [z for z, info in datos.ZONAS.items() if info["aminos"]]
    rondas = []
    for _ in range(RONDAS):
        zona = rng.choice(zonas)
        info = datos.ZONAS[zona]
        rondas.append((rng.choice(info["aminos"]), rng.randint(*info["niveles"]), zona))
    return modificador, rondas


def _estado(juego):
    return juego.setdefault("diario", {})


def hecho_hoy(juego):
    return _estado(juego).get("fecha") == hoy().isoformat()


def _puntos_ronda(resultado, c):
    if resultado != "capturado":
        return 10 if resultado in ("huiste", "huyo") else 0
    p = 100 + 10 * min(c.racha_max, 8)
    if c.turno <= 6:
        p += 30
    if c.dano_total == 0:
        p += 25
    if c.criticos >= 3:
        p += 15
    return p


def _registrar(juego, puntos):
    """Guarda el resultado del día y actualiza la racha de días seguidos."""
    e = _estado(juego)
    ayer = (hoy() - datetime.timedelta(days=1)).isoformat()
    e["racha"] = e.get("racha", 0) + 1 if e.get("fecha") == ayer else 1
    e["fecha"] = hoy().isoformat()
    e["puntos"] = puntos
    e["mejor"] = max(e.get("mejor", 0), puntos)
    e["dias"] = e.get("dias", 0) + 1
    e["mejor_racha"] = max(e.get("mejor_racha", 0), e["racha"])


def diario(win, juego):
    """Pantalla del reto diario. Devuelve True si cambió la partida."""
    fecha = hoy()
    modificador, rondas = plan(fecha)
    e = _estado(juego)
    ya = hecho_hoy(juego)
    racha = e.get("racha", 0) if (ya or e.get("fecha") == (fecha - datetime.timedelta(days=1)).isoformat()) else 0
    lineas = [tr("Reto de hoy: {fecha}", fecha=fecha.isoformat()), "",
              tr("Racha: {n} día(s)   ·   Mejor puntaje: {m}   ·   Días jugados: {t}",
                 n=racha, m=e.get("mejor", 0), t=e.get("dias", 0)), "", modificador[1], "",
              tr("5 combates de entrenamiento con tu equipo (se cura al empezar). Los aminoácidos "
                 "no se unen a tu equipo, pero el ATP y el XP que ganes sí cuentan. Todos reciben "
                 "los mismos rivales hoy."), ""]
    for i, (aa, nivel, zona) in enumerate(rondas):
        lineas.append(f" {i + 1}. {datos.ZONAS[zona]['nombre']}  ·  " + tr("nivel {n}", n=nivel))
    if ya:
        lineas += ["", tr("Hoy ya lo completaste: {p} puntos. Vuelve mañana para seguir la racha.",
                          p=e.get("puntos", 0))]
        d.popup(win, "\n".join(lineas), tr("Reto diario"), ancho=76)
        return False
    d.popup(win, "\n".join(lineas), tr("Reto diario"), ancho=76)
    if not juego["equipo"] or d.menu(win, tr("¿Empezar el reto de hoy?"),
                                     [tr("Sí, empezar"), tr("Ahora no")]) != 0:
        return False

    # trabajo sobre una copia: lo que se pierde o se gasta aquí no toca tu partida
    trabajo = copy.deepcopy(juego)
    progreso.curar_equipo(trabajo)
    trabajo["objetos"]["ATP"] = max(3, trabajo["objetos"]["ATP"])
    total, detalle = 0, []
    for i, (aa, nivel, zona) in enumerate(rondas):
        win.erase()
        d.popup(win, tr("Ronda {i}/{n}: un aminoácido salvaje (nivel {nivel}) en {zona}.", i=i + 1,
                        n=RONDAS, nivel=nivel, zona=datos.ZONAS[zona]["nombre"]),
                tr("Reto diario"), ancho=56)
        resultado, c = combate.combate_con_datos(win, trabajo, aa, nivel, zona,
                                                 ph=modificador[2], sparring=True,
                                                 ciego=modificador[3])
        pts = _puntos_ronda(resultado, c)
        total += pts
        detalle.append((zona, resultado, pts))
        if resultado == "derrota":
            break
    # lo que sí se conserva: repaso espaciado y bonificaciones
    juego["aciertos"], juego["fallos"] = trabajo["aciertos"], trabajo["fallos"]
    _registrar(juego, total)
    premio_atp = 2 + (1 if total >= 400 else 0)
    juego["objetos"]["ATP"] += premio_atp
    for m in juego["equipo"]:
        progreso.dar_xp(m, 5 + min(10, total // 100))
    sonido.reproducir("logro")
    nombres = {"capturado": tr("unido"), "huiste": tr("huiste"), "huyo": tr("escapó"),
               "derrota": tr("derrota")}
    res = [f"{i + 1}. {datos.ZONAS[z]['nombre'][:24]:<24} {nombres.get(r, r):<8} {p:>4}"
           for i, (z, r, p) in enumerate(detalle)]
    d.popup(win, tr("Puntaje total: {p}", p=total) + "\n\n" + "\n".join(res) + "\n\n"
            + tr("Racha: {n} día(s). Premio: +{a} ATP y algo de XP para tu equipo.",
                 n=_estado(juego)["racha"], a=premio_atp), tr("Reto diario"), ancho=62,
            attr=d.c("bien"))
    return True


# --------------------------------------------------------------- gimnasio
NOMBRE_TIPO = {
    "nombre": tr("reconocer el nombre"), "tres": tr("código de 3 letras"),
    "una": tr("código de 1 letra"), "carga": tr("carga a pH 7"), "grupo": tr("grupo de Lehninger"),
    "nutricion": tr("nutrición"), "codon": tr("codones"), "hidro": tr("hidropatía"),
    "pka": tr("pKR"), "pi": tr("pI"), "calc_pi": tr("cálculo del pI"),
}


def _candidatos(juego):
    conocidos = [aa for aa in datos.ORDEN if juego["capturados"].get(aa) or aa in juego["vistos"]]
    tipos = preguntas.RECONOCER + [t for t in preguntas.TIPOS_PROPIEDAD]
    return [(aa, t) for aa in conocidos for t in tipos if preguntas.aplica(aa, t)]


def _elegir(juego, claves, n):
    """n pares (aa, tipo) sin repetir, más probables cuanto más los fallas."""
    elegidos, restantes = [], list(claves)
    while restantes and len(elegidos) < n:
        pesos = [progreso.peso(juego, f"{aa}:{t}") ** 1.5 for aa, t in restantes]
        elegidos.append(restantes.pop(random.choices(range(len(restantes)), pesos)[0]))
    return elegidos


def gimnasio(win, juego):
    """Preguntas de tus puntos débiles. Devuelve True si hubo sesión."""
    claves = _candidatos(juego)
    if len(claves) < 5:
        d.popup(win, tr("Captura o encuentra algunos aminoácidos antes de entrenar."),
                tr("Gimnasio de repaso"))
        return False
    d.popup(win, tr("El gimnasio elige preguntas de los aminoácidos y propiedades que más fallas, "
                    "y al final te dice qué repasar. {n} preguntas. Esc abandona."
                    , n=PREGUNTAS_GIMNASIO), tr("Gimnasio de repaso"), ancho=60)
    antes = dict(juego["fallos"])
    elegidos = _elegir(juego, claves, PREGUNTAS_GIMNASIO)
    aciertos = hechas = 0
    for i, (aa, tipo) in enumerate(elegidos):
        alto, ancho = win.getmaxyx()
        win.erase()
        d.reiniciar_regiones()
        d.put(win, 0, 1, tr("GIMNASIO DE REPASO · {i}/{total} · aciertos {n}", i=i + 1,
                            total=len(elegidos), n=aciertos), d.c("titulo", curses.A_BOLD))
        arte = datos.forma(aa)["arte"]
        d.estructura(win, 2, 1, arte)
        x = d.ancho_estructura(arte) + 4
        if ancho - x < 40:
            y, x = len(arte) + 3, 1
        else:
            y = 2
        bien = preguntas.preguntar(win, juego, aa, tipo, y, x, min(64, ancho - x - 1),
                                   estructura=tipo in preguntas.RECONOCER, opciones=True,
                                   salir=True)
        if bien is None:
            break
        aciertos += bien
        hechas += 1
    progreso.contar(juego, "gym_sesiones")
    if not hechas:
        return False
    if hechas == PREGUNTAS_GIMNASIO and aciertos == hechas:
        progreso.contar(juego, "gym_perfecto")
        juego["objetos"]["ATP"] += 1
        sonido.reproducir("logro")
    pendientes = [k for k, v in juego["fallos"].items() if v > antes.get(k, 0)]
    lineas = [tr("{n}/{total} correctas.", n=aciertos, total=hechas), ""]
    if pendientes:
        lineas.append(tr("A repasar:"))
        pares = preguntas.pares()
        for k in pendientes[:5]:
            aa, tipo = k.split(":")
            nota = pares.get(aa, (None, ""))[1] if tipo in preguntas.RECONOCER else ""
            lineas.append(f"• {datos.AMINOACIDOS[aa]['nombre']} ({aa}) — {NOMBRE_TIPO.get(tipo, tipo)}"
                          + (f"\n   {nota}" if nota else ""))
        if len(pendientes) > 5:
            lineas.append(tr("… y {n} más.", n=len(pendientes) - 5))
        lineas += ["", tr("Saldrán más seguido en el campo y en la próxima sesión.")]
    else:
        lineas.append(tr("Sin fallos: ¡ningún punto débil esta vez!") + (
            " " + tr("+1 ATP.") if hechas == PREGUNTAS_GIMNASIO else ""))
    d.popup(win, "\n".join(lineas), tr("Balance del gimnasio"), ancho=74,
            attr=d.c("bien" if aciertos >= 0.8 * hechas else "texto"))
    return True
