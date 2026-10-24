"""Colores, cajas, barras, menús y ventanas emergentes con curses."""

import contextlib
import curses
import os
import textwrap
import time

from idioma import tr

# Paleta: grises neutros + acentos desaturados (índices xterm-256).
# (color 256, respaldo de 8 colores)
_PALETA = {
    "texto": (254, curses.COLOR_WHITE),
    "tenue": (245, curses.COLOR_WHITE),
    "oscuro": (240, curses.COLOR_WHITE),
    "titulo": (187, curses.COLOR_YELLOW),
    "NP": (144, curses.COLOR_YELLOW),
    "ARO": (139, curses.COLOR_MAGENTA),
    "POL": (108, curses.COLOR_GREEN),
    "NEG": (138, curses.COLOR_RED),
    "POS": (103, curses.COLOR_BLUE),
    "NEU": (247, curses.COLOR_WHITE),
    "agua": (109, curses.COLOR_CYAN),
    "bien": (108, curses.COLOR_GREEN),
    "mal": (138, curses.COLOR_RED),
    # átomos (colores CPK lavados) y esqueleto
    "atC": (252, curses.COLOR_WHITE),
    "atH": (246, curses.COLOR_WHITE),
    "atN": (110, curses.COLOR_BLUE),
    "atO": (174, curses.COLOR_RED),
    "atS": (186, curses.COLOR_YELLOW),
    "atP": (180, curses.COLOR_YELLOW),
    "enlace": (243, curses.COLOR_WHITE),
    "esqueleto": (240, curses.COLOR_WHITE),
}
_PARES = {}
_FONDOS = {}          # (nombre, fondo) -> número de par
_SIGUIENTE = [0]

COLOR_GRUPO = {
    "alifatico": "NP", "aromatico": "ARO", "polar": "POL",
    "acido": "NEG", "basico": "POS",
}


def init_colores():
    curses.start_color()
    try:
        curses.use_default_colors()
        fondo = -1
    except curses.error:
        fondo = curses.COLOR_BLACK
    for i, (nombre, (c256, c8)) in enumerate(_PALETA.items(), start=1):
        curses.init_pair(i, _color(c256, c8), fondo)
        _PARES[nombre] = i
    _SIGUIENTE[0] = len(_PALETA) + 1
    _paleta_consola()


def _rgb(c256):
    """Índice xterm-256 → (r, g, b) de 0 a 255."""
    if c256 >= 232:
        v = 8 + 10 * (c256 - 232)
        return v, v, v
    n = c256 - 16
    niveles = (0, 95, 135, 175, 215, 255)
    return niveles[n // 36], niveles[n // 6 % 6], niveles[n % 6]


def _paleta_consola():
    """La consola de Windows solo tiene 16 colores y los trae muy saturados:
    se cambian por los de _PALETA (el primero de cada color de respaldo) y
    grises neutros. Las versiones brillantes, que salen con A_BOLD, quedan
    iguales para que la negrita no sature. PDCurses la restaura al salir."""
    if os.name != "nt" or curses.COLORS >= 256 or not curses.can_change_color():
        return
    tabla = {curses.COLOR_BLACK: (28, 28, 28), curses.COLOR_WHITE: _rgb(245)}
    for c256, c8 in _PALETA.values():
        if c8 not in tabla:
            tabla[c8] = _rgb(c256)
    for c8, rgb in tabla.items():
        r, g, b = (v * 1000 // 255 for v in rgb)
        try:
            curses.init_color(c8, r, g, b)
            if c8 not in (curses.COLOR_BLACK, curses.COLOR_WHITE) and curses.COLORS >= 16:
                curses.init_color(c8 + 8, r, g, b)
        except curses.error:
            return
    if curses.COLORS >= 16:
        for n, c256 in ((8, 240), (15, 254)):
            r, g, b = (v * 1000 // 255 for v in _rgb(c256))
            try:
                curses.init_color(n, r, g, b)
            except curses.error:
                return


def _color(c256, c8):
    """Color según lo que dé la terminal. Con 16 colores (la consola de
    Windows) los grises usan blanco brillante, gris claro y gris oscuro en
    vez de A_DIM, que ahí casi nunca se nota."""
    if curses.COLORS >= 256:
        return c256
    if curses.COLORS >= 16 and c8 == curses.COLOR_WHITE:
        return 15 if c256 >= 250 else 7 if c256 >= 244 else 8
    return c8


def c(nombre, extra=0, fondo=None):
    """Atributo de color. fondo: índice xterm-256 de gris para el fondo."""
    if nombre not in _PARES:
        return extra
    if fondo is not None and curses.COLORS >= 256:
        clave = (nombre, fondo)
        if clave not in _FONDOS:
            if _SIGUIENTE[0] >= curses.COLOR_PAIRS:
                return c(nombre, extra)
            curses.init_pair(_SIGUIENTE[0], _PALETA[nombre][0], fondo)
            _FONDOS[clave] = _SIGUIENTE[0]
            _SIGUIENTE[0] += 1
        return curses.color_pair(_FONDOS[clave]) | extra
    attr = curses.color_pair(_PARES[nombre])
    if nombre in ("tenue", "oscuro") and curses.COLORS < 16:
        attr |= curses.A_DIM
    return attr | extra


def etiqueta_tipos(win, y, x, tipos, corto=False):
    """Dibuja [Tipo][Tipo] con el color de cada tipo. Devuelve el ancho usado."""
    import datos
    cx = x
    for t in tipos:
        nombre = datos.TIPOS[t]["corto" if corto else "nombre"] if t in datos.TIPOS else "Neutro"
        texto = f" {nombre} "
        put(win, y, cx, texto, c(t, curses.A_BOLD | curses.A_REVERSE))
        cx += len(texto) + 1
    return cx - x - 1


def put(win, y, x, texto, attr=0):
    """addstr que recorta al tamaño de la ventana y nunca revienta."""
    alto, ancho = win.getmaxyx()
    if y < 0 or y >= alto or x >= ancho:
        return
    texto = str(texto)[: max(0, ancho - x - (1 if y == alto - 1 else 0))]
    try:
        win.addstr(y, x, texto, attr)
    except curses.error:
        pass


def caja(win, y, x, h, w, titulo=None, attr=None):
    attr = c("tenue") if attr is None else attr
    put(win, y, x, "┌" + "─" * (w - 2) + "┐", attr)
    for i in range(1, h - 1):
        put(win, y + i, x, "│", attr)
        put(win, y + i, x + w - 1, "│", attr)
    put(win, y + h - 1, x, "└" + "─" * (w - 2) + "┘", attr)
    if titulo:
        put(win, y, x + 2, f" {titulo} ", c("titulo", curses.A_BOLD))


def limpiar_area(win, y, x, h, w):
    for i in range(h):
        put(win, y + i, x, " " * w)


def barra(win, y, x, ancho, valor, maximo, attr):
    llenos = 0 if maximo <= 0 else round(ancho * max(0, min(valor, maximo)) / maximo)
    put(win, y, x, "█" * llenos, attr)
    put(win, y, x + llenos, "░" * (ancho - llenos), c("tenue"))


ATOMOS = {"C": "atC", "H": "atH", "N": "atN", "O": "atO", "S": "atS", "P": "atP"}
ENLACES = set("|/\\=─│")


def _filas_esqueleto(lineas):
    """Filas que pertenecen al esqueleto común (H, Cα, NH3+, COO−)."""
    n = 3 if len(lineas) >= 3 and "COO-" in lineas[2] else 0
    if n and len(lineas) > 3 and lineas[3].strip() == "|":
        n = 4
    return n


def _colorear(linea, esqueleto=False):
    """Divide una línea de estructura en (texto, color) por átomo (CPK)."""
    if esqueleto:
        return [(linea, "esqueleto")]
    trozos, ultimo, i = [], "atC", 0
    while i < len(linea):
        ch = linea[i]
        sig = linea[i + 1] if i + 1 < len(linea) else ""
        ant = linea[i - 1] if i else ""
        if ch.isupper() and sig.islower() and sig not in "αβγδε":
            j = i
            while j < len(linea) and linea[j].isalpha():
                j += 1
            trozos.append((linea[i:j], "tenue"))      # rótulo (GlcNAc, Man…)
            i = j
            continue
        if ch in ATOMOS:
            ultimo = ATOMOS[ch]
            color = ultimo
        elif ch.isdigit() or ch in "()αβγδε":
            color = ultimo
        elif ch == "+":
            color = "POS"
        elif ch == "-":
            es_carga = (ant.isalnum() or ant == ")") and sig in (" ", ")", "")
            color = "NEG" if es_carga else "enlace"
        elif ch in ENLACES:
            color = "enlace"
        else:
            color = "tenue"
        trozos.append((ch, color))
        i += 1
    return trozos


def estructura(win, y, x, lineas, attr=None, cpk=True, etiqueta_r=None, color_r="texto"):
    """Dibuja una estructura. Con cpk=True colorea por átomo, atenúa el
    esqueleto común y resalta el grupo R; etiqueta_r rotula la cadena lateral."""
    if not cpk:
        attr = c("texto") if attr is None else attr
        for i, l in enumerate(lineas):
            put(win, y + i, x, l, attr)
        return
    n_esq = _filas_esqueleto(lineas)
    for i, l in enumerate(lineas):
        cx = x
        for texto, color in _colorear(l, esqueleto=i < n_esq):
            negrita = curses.A_BOLD if i >= n_esq and color.startswith("at") else 0
            put(win, y + i, cx, texto, c(color, negrita))
            cx += len(texto)
    if etiqueta_r and n_esq < len(lineas):
        # barra de color junto a la cadena lateral y su nombre debajo
        filas_r = [l for l in lineas[n_esq:] if l.strip()]
        sangria = min(len(l) - len(l.lstrip()) for l in filas_r)
        for i in range(n_esq, len(lineas)):
            put(win, y + i, x + max(0, sangria - 2), "║", c(color_r))
        put(win, y + len(lineas) + 1, x + max(0, sangria - 2), tr("grupo R: "), c("tenue"))
        put(win, y + len(lineas) + 1, x + max(0, sangria - 2) + 9, etiqueta_r, c(color_r, curses.A_BOLD))


def ancho_estructura(lineas, etiqueta_r=None):
    """Columnas que ocupa estructura(), contando el rótulo «grupo R: …»."""
    ancho = max((len(l) for l in lineas), default=0)
    n_esq = _filas_esqueleto(lineas)
    filas_r = [l for l in lineas[n_esq:] if l.strip()]
    if etiqueta_r and filas_r:
        sangria = min(len(l) - len(l.lstrip()) for l in filas_r)
        ancho = max(ancho, max(0, sangria - 2) + 9 + len(etiqueta_r))
    return ancho


def envolver(texto, ancho):
    salida = []
    for parrafo in str(texto).split("\n"):
        salida.extend(textwrap.wrap(parrafo, ancho) or [""])
    return salida


# ----------------------------------------------------------------- ratón
# Cada pantalla registra, al dibujarse, las zonas en las que se puede hacer
# clic. Un clic se convierte en la tecla equivalente: así todo el juego se
# puede usar con el ratón sin tocar la lógica del teclado, que sigue igual.
_REGIONES = []        # (y, x, alto, ancho, valor); la última dibujada gana
_RATON = [False]
_CLIC = (curses.BUTTON1_CLICKED | curses.BUTTON1_RELEASED
         | getattr(curses, "BUTTON1_DOUBLE_CLICKED", 0)
         | getattr(curses, "BUTTON1_TRIPLE_CLICKED", 0))
_RUEDA_ARRIBA = getattr(curses, "BUTTON4_PRESSED", 0)
_RUEDA_ABAJO = getattr(curses, "BUTTON5_PRESSED", 0)


def iniciar_raton(activar=True):
    """Activa el ratón si la terminal lo soporta (el teclado funciona igual)."""
    _RATON[0] = False
    if not activar:
        try:
            curses.mousemask(0)
        except (curses.error, AttributeError):
            pass
        return False
    try:
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
        try:
            curses.mouseinterval(0)
        except curses.error:
            pass
        _RATON[0] = True
    except (curses.error, AttributeError):
        pass
    return _RATON[0]


def raton_activo():
    return _RATON[0]


def reiniciar_regiones():
    _REGIONES.clear()


def region(y, x, alto, ancho, valor):
    _REGIONES.append((y, x, alto, ancho, valor))


@contextlib.contextmanager
def capa():
    """Una ventana emergente tapa las zonas de clic de lo que hay debajo."""
    guardadas = list(_REGIONES)
    _REGIONES.clear()
    try:
        yield
    finally:
        _REGIONES[:] = guardadas


def pantalla_completa(win, valor):
    """Cualquier clic en la pantalla equivale a `valor` (p. ej. Enter)."""
    alto, ancho = win.getmaxyx()
    region(0, 0, alto, ancho, valor)


def boton(win, y, x, texto, valor, color="titulo", activo=True):
    """Dibuja un botón y lo hace clicable. Devuelve el ancho que ocupa."""
    etiqueta = f" {texto} "
    attr = c(color, curses.A_BOLD | curses.A_REVERSE) if activo else c("oscuro", curses.A_REVERSE)
    put(win, y, x, etiqueta, attr)
    if activo:
        region(y, x, 1, len(etiqueta), valor)
    return len(etiqueta)


def fila_botones(win, y, x, botones, ancho_max=None):
    """Botones en fila que pasan a la siguiente línea si no caben.
    botones: [(texto, valor[, color[, activo]])]. Devuelve las filas usadas."""
    alto, ancho = win.getmaxyx()
    limite = ancho_max if ancho_max is not None else ancho - 1
    cx, fila = x, 0
    for b in botones:
        texto, valor = b[0], b[1]
        color = b[2] if len(b) > 2 else "titulo"
        activo = b[3] if len(b) > 3 else True
        if cx + len(texto) + 2 > x + limite and cx > x:
            cx, fila = x, fila + 1
        cx += boton(win, y + fila, cx, texto, valor, color, activo) + 1
    return fila + 1


def _clic():
    """Traduce un evento del ratón en el valor de la zona pulsada (o None)."""
    try:
        _, mx, my, _, estado = curses.getmouse()
    except curses.error:
        return None
    if _RUEDA_ARRIBA and estado & _RUEDA_ARRIBA:
        return curses.KEY_UP
    if _RUEDA_ABAJO and estado & _RUEDA_ABAJO:
        return curses.KEY_DOWN
    if not estado & _CLIC:
        return None
    for y, x, alto, ancho, valor in reversed(_REGIONES):
        if y <= my < y + alto and x <= mx < x + ancho:
            return valor(mx, my) if callable(valor) else valor
    return None



MOVIMIENTO = (curses.KEY_UP, curses.KEY_DOWN, curses.KEY_LEFT, curses.KEY_RIGHT,
              "w", "a", "s", "d", "W", "A", "S", "D")


def tecla(win, texto=False):
    """Lee una tecla; devuelve int de curses o str de un carácter. Al dejar
    presionada una flecha, las repeticiones que se juntaron mientras se
    dibujaba se descartan: si no, en Windows (donde dibujar tarda más) el
    personaje sigue avanzando después de soltarla. texto=True no descarta
    nada (para escribir)."""
    while True:
        try:
            k = win.get_wch()
        except curses.error:
            continue
        if k == curses.KEY_MOUSE:
            valor = _clic()
            if valor is None or (texto and not isinstance(valor, str)):
                continue                    # al escribir solo valen las teclas de la pantalla
            return valor
        if k == curses.KEY_RESIZE and os.name == "nt":
            curses.resize_term(0, 0)        # PDCurses no actualiza el tamaño solo
        if not texto and k in MOVIMIENTO:
            _descartar_repetidas(win, k)
        return k


def _descartar_repetidas(win, k):
    win.nodelay(True)
    try:
        while True:
            try:
                sig = win.get_wch()
            except curses.error:
                return
            if sig != k:
                # la primera tecla distinta se devuelve a la cola
                if isinstance(sig, int):
                    curses.ungetch(sig)
                else:
                    curses.unget_wch(sig)
                return
    finally:
        win.nodelay(False)


def pausa(ms, desde):
    """Espera a que pasen ms desde `desde` (time.monotonic()). Lo que tardó
    dibujar el cuadro ya cuenta: en la consola de Windows dibujar es lento y
    con una pausa fija las animaciones duraban mucho más."""
    resto = ms - int((time.monotonic() - desde) * 1000)
    if resto > 0:
        curses.napms(resto)


def es(k, *opciones):
    """Compara una tecla con caracteres (sin importar mayúsculas) o códigos."""
    for o in opciones:
        if isinstance(o, str) and isinstance(k, str) and k.lower() == o.lower():
            return True
        if isinstance(o, int) and k == o:
            return True
    return False


ESC = "\x1b"
ENTER = ("\n", "\r", curses.KEY_ENTER)


def popup(win, texto, titulo=None, ancho=60, attr=None, esperar=True):
    """Ventana centrada con texto; espera una tecla."""
    alto_p, ancho_p = win.getmaxyx()
    ancho = min(ancho, ancho_p - 2)
    lineas = envolver(texto, ancho - 4)
    h = min(len(lineas) + 4, alto_p - 1)
    y0 = max(0, (alto_p - h) // 2)
    x0 = max(0, (ancho_p - ancho) // 2)
    limpiar_area(win, y0, x0, h, ancho)
    caja(win, y0, x0, h, ancho, titulo)
    for i, l in enumerate(lineas[: h - 4]):
        put(win, y0 + 1 + i, x0 + 2, l, attr if attr is not None else c("texto"))
    if esperar:
        with capa():
            pantalla_completa(win, "\n")           # un clic en cualquier lado sigue
            seguir = tr("[Enter] seguir")
            boton(win, y0 + h - 2, x0 + ancho - len(seguir) - 5, seguir, "\n", "tenue")
            win.refresh()
            while True:
                k = tecla(win)
                if k != curses.KEY_RESIZE:
                    return k
    win.refresh()


def esperar_enter(win):
    """Espera Enter o un clic (en vez de un while tecla() not in ENTER)."""
    with capa():
        pantalla_completa(win, "\n")
        while tecla(win) not in ENTER:
            pass


def esperar(win, texto=None):
    """Pausa hasta una tecla o un clic (en vez de tecla() a secas)."""
    with capa():
        pantalla_completa(win, "\n")
        if texto:
            alto, _ = win.getmaxyx()
            boton(win, alto - 1, 1, texto, "\n", "tenue")
            win.refresh()
        while True:
            k = tecla(win)
            if k != curses.KEY_RESIZE:
                return k


def dialogo(win, paginas, titulo=None):
    for p in paginas:
        win.erase()
        popup(win, p, titulo)


def menu(win, titulo, opciones, y=None, x=None, ancho=None, ayuda=None,
         inicial=0, clic_fuera=True):
    """Menú vertical. opciones: lista de str. Devuelve índice o None (Esc).
    Con el ratón: un clic elige la fila; un clic fuera del menú lo cancela
    (salvo clic_fuera=False)."""
    alto_p, ancho_p = win.getmaxyx()
    ancho = ancho or min(max([len(o) for o in opciones] + [len(titulo or "")]) + 8,
                         ancho_p - 2)
    h = min(len(opciones) + 2 + (2 if ayuda else 0), alto_p - 1)
    y = (alto_p - h) // 2 if y is None else y
    x = (ancho_p - ancho) // 2 if x is None else x
    sel = inicial
    visibles = h - 2 - (2 if ayuda else 0)
    with capa():
        while True:
            limpiar_area(win, y, x, h, ancho)
            caja(win, y, x, h, ancho, titulo)
            inicio = max(0, min(sel - visibles + 1, len(opciones) - visibles))
            inicio = max(0, min(inicio, sel))
            reiniciar_regiones()
            if clic_fuera:
                pantalla_completa(win, ESC)
            region(y, x, h, ancho, None)            # el borde del menú no cancela
            for i, o in enumerate(opciones[inicio:inicio + visibles]):
                idx = inicio + i
                marca = "► " if idx == sel else "  "
                attr = c("titulo", curses.A_BOLD) if idx == sel else c("texto")
                put(win, y + 1 + i, x + 2, (marca + o)[: ancho - 4], attr)
                region(y + 1 + i, x + 1, 1, ancho - 2, ("opt", idx))
            if ayuda:
                put(win, y + h - 2, x + 2, ayuda[: ancho - 4], c("tenue"))
            win.refresh()
            k = tecla(win)
            if isinstance(k, tuple) and k and k[0] == "opt":
                return k[1]
            if es(k, curses.KEY_UP, "k", "w"):
                sel = (sel - 1) % len(opciones)
            elif es(k, curses.KEY_DOWN, "j", "s"):
                sel = (sel + 1) % len(opciones)
            elif k in ENTER or k == " ":
                return sel
            elif k == ESC or es(k, "q"):
                return None
            elif isinstance(k, str) and k.isdigit() and 1 <= int(k) <= len(opciones):
                return int(k) - 1


def teclado_en_pantalla(win, y, x):
    """Teclado clicable (A-Z, Borrar, Enviar) para quien juega solo con el ratón."""
    letras = "ABCDEFGHIJKLM", "NOPQRSTUVWXYZ"
    for fila, grupo in enumerate(letras):
        for i, ch in enumerate(grupo):
            boton(win, y + fila, x + i * 4, ch, ch, "tenue")
    ancho = boton(win, y + 3, x, tr("Borrar"), "\x7f", "mal")
    boton(win, y + 3, x + ancho + 2, tr("Enviar"), "\n", "bien")


def pedir_texto(win, y, x, prompt, largo=10, attr=None):
    """Campo de texto simple. Devuelve str o None si se pulsa Esc. Con el ratón
    activo muestra un teclado en pantalla debajo."""
    texto = ""
    curses.curs_set(1)
    try:
        with capa():
            while True:
                reiniciar_regiones()
                put(win, y, x, prompt, attr if attr is not None else c("texto"))
                put(win, y, x + len(prompt), texto + " " * (largo - len(texto)),
                    c("titulo", curses.A_BOLD | curses.A_UNDERLINE))
                if raton_activo():
                    teclado_en_pantalla(win, y + 2, x + 2)
                try:
                    win.move(y, x + len(prompt) + len(texto))
                except curses.error:
                    pass
                win.refresh()
                k = tecla(win, texto=True)
                if k in ENTER:
                    return texto
                if k == ESC:
                    return None
                if k in (curses.KEY_BACKSPACE, "\x7f", "\b", 127, 8):
                    texto = texto[:-1]
                elif isinstance(k, str) and k.isprintable() and len(texto) < largo:
                    texto += k
    finally:
        curses.curs_set(0)


# --------------------------------------------------------------- tablas
def anchos_columnas(filas, sep=2):
    """Ancho de cada columna (el texto más largo + separación)."""
    anchos = []
    for fila in filas:
        for i, celda in enumerate(fila):
            texto = celda[0] if isinstance(celda, tuple) else celda
            if i >= len(anchos):
                anchos.append(0)
            anchos[i] = max(anchos[i], len(texto) + sep)
    return anchos


def alinear(filas, sep=2):
    """Rellena cada celda hasta el ancho de su columna (como tabuladores
    calculados según el contenido). Celdas: str o (texto, color[, attr])."""
    anchos = anchos_columnas(filas, sep)
    salida = []
    for fila in filas:
        nueva = []
        for i, celda in enumerate(fila):
            if not isinstance(celda, tuple):
                celda = (celda, "texto")
            texto, resto = celda[0], celda[1:]
            ultima = i == len(fila) - 1
            nueva.append((texto if ultima else texto.ljust(anchos[i]),) + tuple(resto))
        salida.append(nueva)
    return salida


def fila_tabla(win, y, x, celdas):
    """Dibuja una fila ya alineada con alinear()."""
    cx = x
    for celda in celdas:
        texto, color = celda[0], celda[1]
        extra = celda[2] if len(celda) > 2 else 0
        put(win, y, cx, texto, c(color, extra))
        cx += len(texto)
