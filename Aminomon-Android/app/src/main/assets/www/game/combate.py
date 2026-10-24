"""Combate por turnos: subir la afinidad del salvaje y capturarlo con un ARNt."""

import curses
import random

import ajustes
import animaciones as anim
import datos
import dibujo as d
import manual
import modos
import motivos
import preguntas
import progreso
import quimica
import sonido
from idioma import tr

AFINIDAD_TRNA = 50
PROB_MIN, PROB_FALLO_EXTRA = 0.30, 0.10   # probabilidad de unión con afinidad 50; bono por fallo
PROB_RARA = 0.06                          # variante rara (el doble en modo difícil)
AFINIDAD_RECONOCER = 15    # bono por reconocer al aparecer uno ya capturado
TURNOS_PARA_REVELAR = 3
SPRITE_W = 24

# Grupo químico de la cadena lateral, escrito para el lado izquierdo (─X) y
# para el derecho (X─) de la arena.
GRUPO = {
    "G": ("─H", "H─"), "A": ("─CH3", "H3C─"), "V": ("─CH(CH3)2", "(H3C)2CH─"),
    "L": ("─CH2CH(CH3)2", "(H3C)2CHCH2─"), "I": ("─CH(CH3)C2H5", "H5C2(H3C)CH─"),
    "M": ("─CH2CH2SCH3", "H3CSCH2CH2─"), "P": (tr("─pirrolidina"), tr("pirrolidina─")),
    "F": (tr("─CH2─fenilo"), tr("fenilo─CH2─")), "Y": (tr("─fenol─OH"), tr("HO─fenol─")),
    "W": (tr("─indol(N─H)"), tr("(H─N)indol─")), "S": ("─CH2─OH", "HO─CH2─"),
    "T": ("─CH(CH3)OH", "HO(H3C)CH─"), "C": ("─CH2─SH", "HS─CH2─"),
    "N": ("─CONH2", "H2NOC─"), "Q": ("─CH2CONH2", "H2NOCCH2─"),
    "D": ("─COO−", "−OOC─"), "E": ("─CH2COO−", "−OOCCH2─"),
    "K": ("─NH3+", "+H3N─"), "R": (tr("─guanidinio+"), tr("+guanidinio─")),
    "H": (tr("─imidazol(H+)"), tr("(H+)imidazol─")),
    "Hyp": (tr("─pirrolidina─OH"), tr("HO─pirrolidina─")), "Hyl": ("─NH3+", "+H3N─"),
    "Kac": ("─NH─COCH3", "H3COC─NH─"), "Kme3": ("─N+(CH3)3", "(H3C)3N+─"),
    "pS": ("─O─PO3²−", "²−O3P─O─"), "pT": ("─O─PO3²−", "²−O3P─O─"),
    "pY": (tr("─fenil─O─PO3²−"), tr("²−O3P─O─fenil─")), "Cis": ("─S─S─", "─S─S─"),
    "Gla": ("─CH(COO−)2", "(−OOC)2CH─"), "Nglc": (tr("─CONH─glicano"), tr("glicano─HNOC─")),
    "Cit": ("─NH─CO─NH2", "H2N─OC─NH─"),
    "gS": ("─CH2─O─GalNAc", "GalNAc─O─CH2─"), "gT": ("─CH(CH3)─O─GalNAc", "GalNAc─O─CH─"),
}

# Puentes de H: papel del grupo polar (D = donador, A = aceptor) y cómo se
# escribe con el átomo que participa pegado a la línea de puntos.
#            papel  donador_izq   aceptor_izq    donador_der    aceptor_der
HB = {
    "S": ("DA", "─O─H", "─(H)O:", "H─O─", ":O(H)─"),
    "T": ("DA", "─O─H", "─(H)O:", "H─O─", ":O(H)─"),
    "Y": ("DA", tr("─fenol─O─H"), tr("─fenol(H)O:"), tr("H─O─fenol─"), tr(":O(H)─fenol─")),
    "W": ("D", tr("─indol─N─H"), None, tr("H─N─indol─"), None),
    "N": ("DA", "─CON(H)─H", "─(H2N)C═O:", "H─N(H)OC─", ":O═C(NH2)─"),
    "Q": ("DA", "─CON(H)─H", "─(H2N)C═O:", "H─N(H)OC─", ":O═C(NH2)─"),
    "C": ("DA", "─S─H", "─(H)S:", "H─S─", ":S(H)─"),
    "Hyp": ("DA", "─O─H", "─(H)O:", "H─O─", ":O(H)─"),
    "Kac": ("DA", "─N(Ac)─H", "─(HN)C═O:", "H─N(Ac)─", ":O═C(NH)─"),
    "Nglc": ("DA", "─CON(H)─H", "─(HN)C═O:", "H─N(H)OC─", ":O═C(NH)─"),
    "Cit": ("DA", "─CON(H)─H", "─(H2N)C═O:", "H─N(H)OC─", ":O═C(NH2)─"),
    "gS": ("DA", "─GalNAc─O─H", "─GalNAc(H)O:", "H─O─GalNAc─", ":O(H)GalNAc─"),
    "gT": ("DA", "─GalNAc─O─H", "─GalNAc(H)O:", "H─O─GalNAc─", ":O(H)GalNAc─"),
    "H": ("DA", tr("─imidazol─N─H"), tr("─imidazol─N:"), tr("H─N─imidazol─"), tr(":N─imidazol─")),
}
CARGADO = {
    "POS": ("D", "─NH3+", "+H3N─"),
    "NEG": ("A", "─COO−", "−OOC─"),
}
INTERACCION_H = {("POL", "POL"), ("POL", "POS"), ("POL", "NEG"),
                 ("POS", "POL"), ("NEG", "POL")}

# Personalidades: lo que hace cada aminoácido salvaje además de la química.
RASGOS = {
    "G": (tr("Flexible"), tr("Sin cadena lateral, gira con libertad: a veces se desliza y "
                             "pierdes afinidad.")),
    "P": (tr("Torcedura"), tr("Su anillo rígido dobla el esqueleto: a veces tu próxima "
                              "interacción pierde la mitad.")),
    "H": (tr("Tampón"), tr("Su imidazol amortigua el pH: tus cambios de pH valen la mitad.")),
    "W": (tr("Voluminoso"), tr("Es el residuo más grande: su agitación hace más daño.")),
    "D": (tr("Quelante"), tr("Atrapa cationes: a veces te roba 1 ATP.")),
    "E": (tr("Quelante"), tr("Atrapa cationes: a veces te roba 1 ATP.")),
    "N": (tr("Desamidación"), tr("Su amida se hidroliza: cada 4 turnos pierde algo de afinidad.")),
    "Q": (tr("Desamidación"), tr("Su amida se hidroliza: cada 4 turnos pierde algo de afinidad.")),
    "M": (tr("Iniciadora"), tr("Toda proteína empieza con ella: arranca con +10 de afinidad.")),
}
RACHA_MAX_BONO = 6        # cada acierto seguido suma 8% de afinidad, hasta 6


def flechas(m):
    if m == 0:
        return "x"
    if m >= 4:
        return "▲▲"
    if m >= 2:
        return "▲"
    if m < 1:
        return "▼"
    return ""


class Combate:
    def __init__(self, win, juego, aa, nivel, zona, ph=None, sparring=False, ciego=False):
        self.win, self.juego, self.zona = win, juego, zona
        self.sparring = sparring              # entrenamiento: no se captura de verdad
        self.ciego = ciego                    # el grupo del rival nunca se revela solo
        self.aa = aa
        conocido = progreso.capturado(juego, aa)
        self.salvaje = dict(nivel=nivel, afinidad=0)
        self.modo = modos.actual(juego)          # facil / medio / dificil
        self.facil = self.modo == "facil"
        self.completo = self.modo == "dificil"   # pH, rasgos, probabilidad del ARNt…
        self.dificil = False
        # pH del arena: el de la zona; se puede cambiar gastando ATP
        self.ph_zona = quimica.ph_de_zona(zona)
        self.ph = quimica.limitar(ph) if (ph is not None and self.completo) else self.ph_zona
        self.racha = self.racha_max = 0       # aciertos seguidos (combo)
        self.dano_total = 0                   # para la captura limpia
        self.torcido = False                  # Pro: tu próxima interacción pierde la mitad
        self.rasgo_visto = False
        self.zinc_usado = False
        self.fallos_trna = 0
        self.criticos = 0
        self.ph_cambios = 0
        self.rara = random.random() < PROB_RARA * (2 if self.dificil else 1)
        self.motivos = motivos.activos(juego)
        if aa == "M" and self.completo:       # rasgo Iniciadora
            self.salvaje["afinidad"] = 10
        # aunque ya lo hayas capturado, su nombre se ve solo si lo reconoces
        self.nombre_visible = False
        self.tipos_visible = conocido or not self.completo
        self.turno = 1
        self.turnos_jugador = 0
        self.log = []
        self.ultimo_mult = 1.0
        self.cuadro = []
        self.activo = self._primer_vivo()
        self._reiniciar_estado()
        juego.setdefault("ajustes", {}).setdefault("velocidad", "lenta")
        if aa not in juego["vistos"]:
            juego["vistos"].append(aa)

    # ---------------------------------------------------------- utilidades
    def _primer_vivo(self):
        for i, m in enumerate(self.juego["equipo"]):
            if m["energia"] > 0:
                return i
        return None

    def _reiniciar_estado(self):
        pass

    @property
    def mon(self):
        return self.juego["equipo"][self.activo]

    def tipos_mio(self):
        return datos.forma(self.mon["id"])["tipos"]

    def tipos_naturales(self):
        """Los grupos de Lehninger del salvaje (los que se preguntan y se muestran)."""
        return datos.AMINOACIDOS[self.aa]["tipos"]

    def tipos_salvaje(self):
        """Grupos con los que interactúa al pH actual: un Asp/Glu muy protonado ya no
        es un anión, y una Cys o Tyr a pH alto sí lo es."""
        return quimica.tipos_efectivos(self.aa, self.tipos_naturales(), self.ph)

    def base_mia(self):
        """Aminoácido estándar de tu residuo activo, o None si es una forma modificada."""
        fid = self.mon["id"]
        return fid if fid in datos.AMINOACIDOS else None

    def nombre_salvaje(self):
        return datos.AMINOACIDOS[self.aa]["nombre"] if self.nombre_visible else tr("¿¿??")

    def movimientos(self):
        return datos.forma(self.mon["id"])["movs"]

    def decir(self, texto):
        self.log.append(texto)
        self.log = self.log[-8:]

    # ----------------------------------------------- combo, pH y capturas
    def sumar_racha(self):
        self.racha += 1
        self.racha_max = max(self.racha_max, self.racha)
        if self.racha >= 2:
            self.decir(tr("Combo ×{n}: +{pct}% de afinidad en tus interacciones.",
                          n=self.racha, pct=int(self.bono_racha() * 100 - 100)))

    def perder_racha(self):
        if self.racha >= 2:
            self.decir(tr("Se rompe el combo."))
        self.racha = 0

    def bono_racha(self):
        return 1 + 0.08 * min(self.racha, RACHA_MAX_BONO)

    def prob_captura(self):
        """Probabilidad de que el ARNt se una: 30% con afinidad 50 y 100% con 100."""
        if not self.completo:
            return 1.0
        a = self.salvaje["afinidad"]
        p = PROB_MIN + (1 - PROB_MIN) * (a - AFINIDAD_TRNA) / (100 - AFINIDAD_TRNA)
        p += PROB_FALLO_EXTRA * self.fallos_trna
        if "rgd" in self.motivos:
            p += 0.20
        if self.dificil:
            p -= 0.10
        return max(0.10, min(1.0, p))

    def rasgo(self):
        return RASGOS.get(self.aa) if self.completo else None

    def mostrar_rasgo(self):
        r = self.rasgo()
        if r and not self.rasgo_visto:
            self.rasgo_visto = True
            self.decir(tr("Rasgo: {nombre}. {desc}", nombre=r[0], desc=r[1]))

    def cambiar_ph(self):
        """Menú del pH del arena. Devuelve True si gastó el turno."""
        if not self.completo:
            self.decir(tr("El pH del arena se desbloquea en el modo Difícil."))
            return False
        atp = self.juego["objetos"]["ATP"]
        paso = 0.5 if self.aa == "H" else 1.0
        opciones, acciones = [], []
        if self.ph - paso >= quimica.PH_MIN:
            opciones.append(tr("Bomba de protones: pH −{n}  (1 ATP)", n=f"{paso:g}"))
            acciones.append(-paso)
        if self.ph + paso <= quimica.PH_MAX:
            opciones.append(tr("Base: pH +{n}  (1 ATP)", n=f"{paso:g}"))
            acciones.append(paso)
        if abs(self.ph - self.ph_zona) >= 0.05:
            opciones.append(tr("Volver al pH natural, {ph}  (1 ATP)", ph=f"{self.ph_zona:.1f}"))
            acciones.append(0)
        if not opciones:
            return False
        if atp < 1:
            d.popup(self.win, tr("No tienes ATP: cada cambio de pH cuesta 1 ATP. La mitocondria "
                                 "(☼) lo recarga."), tr("Sin ATP"))
            return False
        ayuda = tr("His: + al acidificar · Asp/Glu: se protonan · Cys/Tyr: − al alcalinizar")
        sel = d.menu(self.win, tr("pH del arena: {ph}", ph=f"{self.ph:.1f}"), opciones, ayuda=ayuda)
        if sel is None:
            return False
        anterior = self.ph
        self.ph = self.ph_zona if acciones[sel] == 0 else quimica.limitar(self.ph + acciones[sel])
        self.juego["objetos"]["ATP"] = atp - 1
        self.ph_cambios += 1
        progreso.contar(self.juego, "ph_cambios")
        sonido.reproducir("ph")
        self.decir(tr("El pH del arena pasa de {a} a {b}.", a=f"{anterior:.1f}", b=f"{self.ph:.1f}"))
        for aa_ in (self.aa, self.base_mia()):
            texto = quimica.explicar(aa_, self.ph, self.ph_zona) if aa_ else None
            if texto:
                self.decir(texto)
        if self.aa == "H":
            self.mostrar_rasgo()
        nuevos = self.tipos_salvaje()
        if tuple(nuevos) != tuple(self.tipos_naturales()):
            self.decir(tr("A este pH interactúa como: {grupo}.", grupo=datos.nombre_tipos(nuevos)))
        return True

    def rasgos_del_turno(self):
        """Lo que hace el salvaje por su personalidad al terminar su turno."""
        if not self.completo:
            return
        a, s = self.aa, self.salvaje
        nombre = self.nombre_salvaje()
        if a == "P" and random.random() < 0.30:
            self.torcido = True
            self.mostrar_rasgo()
            self.decir(tr("{nombre} tuerce el esqueleto: tu próxima interacción pierde la mitad.",
                          nombre=nombre))
        elif a in ("D", "E") and random.random() < 0.25 and self.juego["objetos"]["ATP"] > 0:
            self.juego["objetos"]["ATP"] -= 1
            self.mostrar_rasgo()
            self.decir(tr("{nombre} quela cationes y te roba 1 ATP.", nombre=nombre))
        elif a in ("N", "Q") and self.turno % 4 == 0 and s["afinidad"] > 0:
            s["afinidad"] = max(0, s["afinidad"] - 5)
            self.mostrar_rasgo()
            self.decir(tr("{nombre} se desamida (−5 afinidad).", nombre=nombre))

    def finalizar(self, resultado):
        """Estadísticas para los logros."""
        j = self.juego
        if self.sparring:
            return resultado
        progreso.maximo(j, "combo_max", self.racha_max)
        if self.criticos:
            progreso.contar(j, "criticos", self.criticos)
        return resultado

    @property
    def velocidad(self):
        return self.juego["ajustes"]["velocidad"]

    # ------------------------------------------------------ química real
    def _papel_mio(self, tipo_mov):
        if self.mon["id"] == "Kme3":
            return ""            # N+(CH3)3: sin H que donar ni par libre
        if tipo_mov in CARGADO:
            return CARGADO[tipo_mov][0]
        return HB.get(self.mon["id"], ("DA",))[0]

    def _papel_rival(self, tipo):
        if tipo in CARGADO:
            return CARGADO[tipo][0]
        return HB.get(self.aa, ("DA",))[0]

    def _hb_posible(self, tipo_mov, tipo_rival):
        a, b = self._papel_mio(tipo_mov), self._papel_rival(tipo_rival)
        return ("D" in a and "A" in b) or ("A" in a and "D" in b)

    def _mult_mov(self, mid):
        m = datos.MOVIMIENTOS[mid]
        if m["efecto"] == "disulfuro":
            if self.aa == "C":
                return 2.0, [("POL", 2, tr("puente disulfuro (covalente)"))]
            return 0.0, [(self.tipos_salvaje()[0], 0, tr("sin otra Cys no hay disulfuro"))]
        mult, partes = datos.multiplicador(m["tipo"], self.tipos_salvaje())
        if m["tipo"] == datos.NEUTRO:
            texto = tr("puente de H del esqueleto") if mid == "puente_h_esqueleto" else "van der Waals"
            return mult, [(t, pm, texto) for t, pm, _ in partes]
        nuevas = []
        for t, pm, texto in partes:
            if (m["tipo"], t) in INTERACCION_H and not self._hb_posible(m["tipo"], t):
                if m["tipo"] == "POL":
                    pm, texto = 0.5, tr("sin puente de H (falta donador/aceptor)")
                else:
                    pm, texto = 1, tr("atracción ion–dipolo")
            pm, texto = self._ajuste_ph(m["tipo"], t, pm, texto)
            nuevas.append((t, pm, texto))
        total = 1.0
        for _, pm, _ in nuevas:
            total *= pm
        return total, nuevas

    def _ajuste_ph(self, tipo_mov, tipo_rival, pm, texto):
        """Los puentes salinos y las repulsiones dependen de cuánta carga conserva
        cada cadena al pH del arena (Henderson-Hasselbalch)."""
        if abs(self.ph - self.ph_zona) < 0.05:
            return pm, texto
        mio, rival = tipo_mov in quimica.IONICOS, tipo_rival in quimica.IONICOS
        if not (mio or rival) or pm == 1:
            return pm, texto
        f = 1.0
        if mio and self.base_mia():
            f *= quimica.factor(self.base_mia(), self.ph, self.ph_zona)
        if rival:
            f *= quimica.factor(self.aa, self.ph, self.ph_zona)
        f = min(1.5, f)
        nuevo = quimica.ajustar_ionica(pm, f)
        if abs(nuevo - pm) < 0.01:
            return pm, texto
        if pm == 0 and nuevo > 0:
            texto = tr("ya casi no se repelen: a pH {ph} les queda poca carga", ph=f"{self.ph:.1f}")
        else:
            texto = tr("{texto} · a pH {ph} su carga es {f:.0%}", texto=texto,
                       ph=f"{self.ph:.1f}", f=f)
        return nuevo, texto

    @staticmethod
    def _interaccion_principal(partes):
        if any(pm == 0 for _, pm, _ in partes):
            return next(tx for _, pm, tx in partes if pm == 0)
        return max(partes, key=lambda p: p[1])[2] if partes else tr("interacción")

    # -------------------------------------------------------------- layout
    def layout(self):
        H, W = self.win.getmaxyx()
        amplio = W >= 110 and H >= 34
        x0 = SPRITE_W + 2
        libre = W - x0 - (SPRITE_W + 2 if amplio else 1)
        cw = min(libre, 92)
        x0 += (libre - cw) // 2 if amplio else 0
        ah = 10 if H >= 34 else (8 if H >= 28 else 6)
        nmov = len(self.movimientos())
        L = dict(W=W, H=H, amplio=amplio, x=x0, w=cw)
        L["rival"] = 1
        L["arena"] = 5
        L["ah"] = ah
        L["yo"] = 5 + ah
        L["movs"] = L["yo"] + 4
        L["nmov"] = nmov
        L["log"] = L["movs"] + nmov + 2
        sobra = L["log"] + 1 - (H - 1)
        if sobra > 0:
            # en terminales chicas la arena cede filas
            L["ah"] -= sobra
            for k in ("yo", "movs", "log"):
                L[k] -= sobra
        L["nlog"] = max(1, H - 1 - L["log"])
        return L

    # ------------------------------------------------------------- dibujo
    def dibujar(self):
        w = self.win
        w.erase()
        d.reiniciar_regiones()
        L = self.layout()
        x, cw = L["x"], L["w"]
        a = datos.AMINOACIDOS[self.aa]
        zona = datos.ZONAS[self.zona]["nombre"]
        d.put(w, 0, 1, tr("Aminoácido salvaje  ·  {zona}  ·  turno {n}", zona=zona, n=self.turno),
              d.c("titulo", curses.A_BOLD))
        # pH del arena y combo, arriba a la derecha de la cabecera
        if self.completo:
            info_ph = quimica.nota_ph(self.ph, self.ph_zona)
            attr_ph = d.c("agua" if abs(self.ph - self.ph_zona) < 0.05 else "titulo", curses.A_BOLD)
            pie_x = max(60, L["W"] - len(info_ph) - 3)
            d.put(w, 0, pie_x, info_ph, attr_ph)
            d.region(0, pie_x, 1, len(info_ph), "p")
        else:
            pie_x = max(60, L["W"] - 24)
            d.put(w, 0, pie_x, tr("Modo {m}", m=modos.INFO[self.modo]["nombre"]),
                  d.c("tenue", curses.A_BOLD))
        if self.dificil:
            d.put(w, 0, pie_x - 12, tr("[DIFÍCIL]"), d.c("mal", curses.A_BOLD))

        color = a["tipos"][0] if self.tipos_visible else "texto"
        d.estructura(w, 2, 1, datos.forma(self.aa)["arte"], d.c(color))

        d.caja(w, L["rival"], x, 4, cw, tr("Salvaje"))
        y = L["rival"] + 1
        d.put(w, y, x + 2, self.nombre_salvaje(), d.c("texto", curses.A_BOLD))
        if self.rara and (self.nombre_visible or self.tipos_visible):
            d.put(w, y, x + 15, "♥", d.c("mal", curses.A_BOLD))
        d.put(w, y, x + 17, tr("Nv {n}", n=self.salvaje["nivel"]), d.c("tenue"))
        if self.tipos_visible:
            # con recuadros angostos los nombres largos de dos tipos no caben
            d.etiqueta_tipos(w, y, x + 24, a["tipos"], corto=cw < 64)
        else:
            d.put(w, y, x + 24, tr("[¿grupo?]  D: deducir"), d.c("tenue"))
        y += 1
        d.put(w, y, x + 2, tr("Afinidad"), d.c("texto"))
        listo = self.salvaje["afinidad"] >= AFINIDAD_TRNA
        # etiqueta(11) + barra + número(9) + "listo: [T] ARNt"(15) + borde(2)
        ancho_barra = max(10, cw - 38)
        d.barra(w, y, x + 11, ancho_barra, self.salvaje["afinidad"], 100,
                d.c("bien" if listo else "agua"))
        d.put(w, y, x + 12 + ancho_barra, f"{int(self.salvaje['afinidad']):3d}/100", d.c("tenue"))
        if listo:
            aviso = tr("listo: [T] ARNt") if cw - 23 - ancho_barra >= 15 else tr("[T] ARNt")
            if cw - 23 - ancho_barra >= 24:
                aviso += f" {self.prob_captura():.0%}"
            d.put(w, y, x + 21 + ancho_barra, aviso, d.c("bien", curses.A_BOLD))
            d.region(y, x + 21 + ancho_barra, 1, len(aviso), "t")

        d.caja(w, L["arena"], x, L["ah"], cw, None, d.c("oscuro"))
        anim.dibujar_cuadro(w, L["arena"] + 1, x + 1, L["ah"] - 2, cw - 2, self.cuadro)
        rasgo = self.rasgo()
        if rasgo and (self.nombre_visible or self.rasgo_visto) and L["ah"] >= 5:
            d.put(w, L["arena"] + L["ah"] - 2, x + 2, f"◊ {rasgo[0]}", d.c("titulo"))
        if self.racha >= 2:
            combo = tr("COMBO ×{n}", n=self.racha)
            d.put(w, L["arena"] + 1, x + cw - len(combo) - 3, combo, d.c("bien", curses.A_BOLD))
        if self.motivos and L["ah"] >= 5:
            d.put(w, L["arena"] + L["ah"] - 2, max(x + 20, x + cw - 3 - 12 * len(self.motivos)),
                  "".join(f"[{motivos.MOTIVOS[m]['nombre'][:9]}]" for m in self.motivos)[: cw - 24],
                  d.c("POL"))

        f = datos.forma(self.mon["id"])
        tipos = self.tipos_mio()
        d.caja(w, L["yo"], x, 4, cw, tr("Tu aminoácido"))
        y = L["yo"] + 1
        d.put(w, y, x + 2, f["nombre"][:20], d.c("texto", curses.A_BOLD))
        d.put(w, y, x + 23, tr("Nv {n}", n=self.mon["nivel"]), d.c("tenue"))
        d.etiqueta_tipos(w, y, x + 30, tipos, corto=True)
        y += 1
        emax = progreso.energia_max(self.mon)
        d.put(w, y, x + 2, tr("Energía"), d.c("texto"))
        d.barra(w, y, x + 11, ancho_barra, self.mon["energia"], emax, d.c("titulo"))
        d.put(w, y, x + 12 + ancho_barra, f"{self.mon['energia']:3d}/{emax}", d.c("tenue"))
        d.put(w, y, x + 21 + ancho_barra, f"ATP {self.juego['objetos']['ATP']}", d.c("tenue"))

        d.caja(w, L["movs"], x, L["nmov"] + 2, cw, tr("Interacciones"))
        con_chip = cw >= 90       # si no cabe la etiqueta, el color del nombre indica el grupo
        filas = []
        for i, mid in enumerate(self.movimientos()):
            m = datos.MOVIMIENTOS[mid]
            nombre_t = datos.TIPOS[m["tipo"]]["corto"] if m["tipo"] in datos.TIPOS else tr("Neutro")
            fila = [(f"{i + 1}) {m['nombre']}", "texto" if con_chip else m["tipo"])]
            if con_chip:
                fila.append((f" {nombre_t} ", m["tipo"], curses.A_BOLD | curses.A_REVERSE))
            fila.append((f"{m['poder']:>3}", "tenue"))
            if self.tipos_visible:
                mult, partes = self._mult_mov(mid)
                col = "bien" if mult >= 2 else "mal" if mult == 0 else "tenue" if mult < 1 else "texto"
                fila.append((f"×{datos.fmt_mult(mult)} {flechas(mult)}", col,
                             curses.A_BOLD if mult != 1 else 0))
                fila.append((self._interaccion_principal(partes), "tenue"))
            else:
                fila.append(("×?", "tenue"))
            filas.append(fila)
        filas = d.alinear(filas)
        for fila in filas:
            # la última columna (la interacción concreta) se recorta al ancho del recuadro
            usado = sum(len(celda[0]) for celda in fila[:-1])
            libre = cw - 4 - usado
            ultima = fila[-1]
            if self.tipos_visible and libre < 16:
                fila.pop()                     # no cabe: se ve en el registro y con [I]
            elif len(ultima[0]) > libre:
                fila[-1] = (ultima[0][: max(0, libre - 1)] + "…",) + tuple(ultima[1:])
        for i, fila in enumerate(filas):
            d.fila_tabla(w, L["movs"] + 1 + i, x + 2, fila)
            d.region(L["movs"] + 1 + i, x + 1, 1, cw - 2, str(i + 1))

        lineas = self.log[-L["nlog"]:]
        for i, l in enumerate(lineas):
            ultimo = i == len(lineas) - 1
            d.put(w, L["log"] + i, x, ("› " + l)[:cw].ljust(cw), d.c("texto" if ultimo else "tenue"))
        # el registro se desplaza cada turno: se repintan esas filas completas
        w.redrawln(L["log"], L["nlog"])
        # botones clicables (también funcionan con las teclas indicadas)
        ancho_btn = L["W"] - 2
        botones = [(tr("ARNt [T]"), "t", "bien", self.salvaje["afinidad"] >= AFINIDAD_TRNA),
                   (tr("Deducir [D]"), "d", "titulo", not self.tipos_visible),
                   (tr("pH [P]"), "p", "agua", self.completo), (tr("Cambiar [C]"), "c", "POL"),
                   (tr("Huir [H]"), "h", "mal"), (tr("Info [I]"), "i", "tenue"),
                   (tr("Manual [M]"), "m", "tenue"),
                   (tr("Vel: {v} [V]", v=tr(self.velocidad)), "v", "tenue"),
                   (tr("Sonido {e} [S]", e=tr("sí") if ajustes.obtener("sonido") else tr("no")), "s", "tenue")]
        filas_btn = 1 if ancho_btn >= 128 else 2 if ancho_btn >= 70 else 3
        d.fila_botones(w, max(L["log"] + 1, L["H"] - filas_btn), 1, botones, ancho_btn)
        if L["amplio"]:
            arte = f["arte"]
            xs = min(L["W"] - SPRITE_W - 1, x + cw + 3)
            yy = min(L["yo"], max(1, L["H"] - len(arte) - 2))
            d.put(w, yy, xs, tr("tu {tres}", tres=f["tres"]), d.c("tenue"))
            d.estructura(w, yy + 1, xs, arte, d.c(tipos[0]))
        w.refresh()

    # ------------------------------------------------------- animaciones
    def ctx_base(self, tipo_rival=None):
        tm = self.tipos_mio()
        ts = self.tipos_salvaje()
        t_rival = tipo_rival or ts[0]
        visible = self.nombre_visible or self.tipos_visible
        fid = self.mon["id"]
        mio = GRUPO.get(fid, ("─R", "R─"))[0]
        rival = GRUPO[self.aa][1] if visible else "R?─"
        return dict(
            mio=mio, rival=rival,
            color_mio=tm[0], color_rival=t_rival if self.tipos_visible else "texto",
            carga_mio="+" if "POS" in tm else "−" if "NEG" in tm else "δ",
            carga_rival="+" if "POS" in ts else "−" if "NEG" in ts else "δ",
            tres=datos.forma(fid)["tres"],
        )

    def animar(self, nombre, ctx, veredicto=None):
        L = self.layout()
        self.dibujar()
        self.cuadro = anim.reproducir(self.win, L["arena"] + 1, L["x"] + 1,
                                      L["ah"] - 2, L["w"] - 2, nombre, ctx, self.velocidad)
        if veredicto:
            texto, color = veredicto
            self.cuadro = self.cuadro + [(0, L["w"] - 3 - len(texto), texto, color)]

    def animacion_interaccion(self, mid, partes):
        """Elige la animación según la interacción física que de verdad ocurre."""
        m = datos.MOVIMIENTOS[mid]
        T = m["tipo"]
        if T == datos.NEUTRO:
            nombre = {"puente_h_esqueleto": "esqueleto", "lamina_beta": "lamina",
                      "triple_helice": "esqueleto_triple"}.get(mid, "vdw")
            return nombre, self.ctx_base()
        if mid == "puente_disulfuro" and self.aa == "C":
            return "disulfuro", self.ctx_base()
        if mid == "entrecruzar":
            return "enlace", self.ctx_base()
        if any(pm == 0 for _, pm, _ in partes):
            return "repulsion", self.ctx_base()
        rt = max(partes, key=lambda p: p[1])[0]
        ctx = self.ctx_base(rt)
        par = (T, rt)
        if par in (("NP", "NP"), ("NP", "ARO"), ("ARO", "NP")):
            return "hidrofobico", ctx
        if par == ("ARO", "ARO"):
            return "pi", ctx
        if par in (("ARO", "POS"), ("POS", "ARO")):
            mio_cat = T == "POS"
            ctx.update(cation=(ctx["mio"].lstrip("─") if mio_cat else ctx["rival"].rstrip("─")),
                       color_cation=ctx["color_mio"] if mio_cat else ctx["color_rival"],
                       color_anillo=ctx["color_rival"] if mio_cat else ctx["color_mio"])
            return "cation_pi", ctx
        if par in (("POS", "NEG"), ("NEG", "POS")):
            return "salino", ctx
        if par in (("POS", "POS"), ("NEG", "NEG")):
            return "vdw", ctx          # la repulsión se apagó por el pH: queda van der Waals
        if par in (("POL", "ARO"), ("ARO", "POL")):
            if T == "POL":
                don = HB.get(self.mon["id"], ("DA", "─X─H"))[1].lstrip("─")
                ctx.update(donador_txt=don, color_donador=ctx["color_mio"],
                           color_anillo=ctx["color_rival"])
            else:
                don = HB.get(self.aa, ("DA", "", "", "H─X─"))[3]
                ctx.update(donador_txt=don, color_donador=ctx["color_rival"],
                           color_anillo=ctx["color_mio"])
            return "oh_pi", ctx
        if par in INTERACCION_H:
            if T in CARGADO and not self._hb_posible(T, rt):
                return "vdw", ctx          # solo atracción ion–dipolo
            return self._ctx_puente_h(T, rt, ctx)
        # no polar o anión frente a un grupo polar/cargado: el agua los separa
        ctx["polar_lado"] = "der" if rt in ("POL", "POS", "NEG") else "izq"
        return "solvatacion", ctx

    def _ctx_puente_h(self, T, rt, ctx):
        papel_m = self._papel_mio(T)
        papel_r = self._papel_rival(rt)
        relleno = ("DA", "─X─H", "─X:", "H─X─", ":X─")
        if T in CARGADO:
            mio_d = mio_a = CARGADO[T][1]
        else:
            fila = HB.get(self.mon["id"], relleno)
            mio_d, mio_a = fila[1], fila[2] or fila[1]
        if rt in CARGADO:
            riv_d = riv_a = CARGADO[rt][2]
        else:
            fila = HB.get(self.aa, relleno)
            riv_d, riv_a = fila[3], fila[4] or fila[3]
        if "D" in papel_m and "A" in papel_r:
            ctx.update(hb_izq=mio_d, hb_der=riv_a, donador="izq")
            return "puente_h", ctx
        if "A" in papel_m and "D" in papel_r:
            ctx.update(hb_izq=mio_a, hb_der=riv_d, donador="der")
            return "puente_h", ctx
        motivo = tr("los dos solo pueden donar H") if "D" in papel_m else tr("los dos solo pueden aceptar H")
        ctx.update(hb_izq=mio_d, hb_der=riv_d, motivo=motivo)
        return "sin_puente_h", ctx

    def sacudir_salvaje(self):
        a = datos.AMINOACIDOS[self.aa]
        color = a["tipos"][0] if self.tipos_visible else "texto"
        anim.sacudir(self.win, 2, 1, datos.forma(self.aa)["arte"], color)

    # ---------------------------------------------------------- acciones
    def usar(self, mid):
        """Forma la interacción con el rival."""
        m = datos.MOVIMIENTOS[mid]
        f = datos.forma(self.mon["id"])
        self.decir(f"{f['nombre']}: {m['nombre']}.")
        mult, partes = self._mult_mov(mid)
        principal = self._interaccion_principal(partes)
        texto_m = f"×{datos.fmt_mult(mult)} {flechas(mult)}".strip()

        if m["efecto"] == "disulfuro" and self.aa != "C":
            self.animar("sin_puente_h", dict(self.ctx_base(), hb_izq="─CH2─S─H",
                                             hb_der=GRUPO[self.aa][1] if self.nombre_visible else "R?─",
                                             motivo=tr("el disulfuro solo se forma entre dos Cys"),
                                             nombre=tr("sin otra Cys no hay disulfuro")))
            self.decir(tr("Sin otra Cys no hay disulfuro: no se forma ninguna interacción."))
            self.ultimo_mult = 1.0
            return

        nombre_anim, ctx = self.animacion_interaccion(mid, partes)
        ctx["nombre"] = f"{principal} ({texto_m})"
        color_v = "bien" if mult >= 2 else "mal" if mult == 0 else "tenue" if mult < 1 else "texto"
        self.animar(nombre_anim, ctx, (texto_m, color_v))

        if m["efecto"] == "disulfuro":
            self.salvaje["afinidad"] = 100
            self.ultimo_mult = 2.0
            self.decir(tr("Enlace covalente S–S entre las dos Cys: afinidad máxima."))
            self.sumar_racha()
            sonido.reproducir("critico")
            progreso.dar_xp(self.mon, 3)
            return

        factor = (1 + self.mon["nivel"] / 8) * (1 - min(0.4, self.salvaje["nivel"] / 30))
        bono = self.bono_racha()
        if "triada" in self.motivos:
            bono *= 1.30
        if self.torcido:
            bono *= 0.5
            self.torcido = False
            self.decir(tr("Tu interacción llega torcida: solo la mitad de afinidad."))
        ganancia = m["poder"] * 0.45 * mult * factor * bono * random.uniform(0.85, 1.15)
        self.salvaje["afinidad"] = min(100, self.salvaje["afinidad"] + ganancia)
        self.ultimo_mult = mult
        if self.completo and self.aa == "G" and ganancia > 0 and random.random() < 0.25:
            self.salvaje["afinidad"] = max(0, self.salvaje["afinidad"] - 8)
            self.mostrar_rasgo()
            self.decir(tr("{nombre} se desliza: −8 afinidad.", nombre=self.nombre_salvaje()))

        if len(partes) > 1 and self.tipos_visible:
            desglose = " · ".join(f"{datos.TIPOS[t]['corto']} ×{datos.fmt_mult(pm)}"
                                  for t, pm, _ in partes)
            self.decir(f"{principal[:1].upper() + principal[1:]}: {desglose} → ×{datos.fmt_mult(mult)}")
        else:
            self.decir(f"{principal[:1].upper() + principal[1:]} (×{datos.fmt_mult(mult)})")
        if mult == 0:
            self.decir(tr("Sin afinidad: se repelen."))
            self.perder_racha()
            sonido.reproducir("error")
        elif mult >= 2:
            self.decir(tr("Muy afín: +{n} de afinidad", n=int(ganancia)))
            self.criticos += 1
            self.sumar_racha()
            sonido.reproducir("critico")
            self.sacudir_salvaje()
            msgs = progreso.dar_xp(self.mon, 3)
            if msgs:
                sonido.reproducir("nivel")
            for msg in msgs:
                self.decir(msg)
        else:
            self.decir(tr("+{n} de afinidad", n=int(ganancia)) + (tr("  (poco afín)") if mult < 1 else ""))
            if mult < 1:
                self.perder_racha()

    def turno_salvaje(self):
        """Devuelve 'huyo' si el salvaje escapa."""
        s = self.salvaje
        nombre = self.nombre_salvaje()
        resultado = None
        if self.ultimo_mult == 0 and random.random() < 0.35:
            self.decir(tr("La repulsión aleja a {nombre}: escapó.", nombre=nombre))
            resultado = "huyo"
        else:
            dano = random.randint(3, 6) + s["nivel"]
            if self.aa == "W" and self.completo:
                dano += 4
                self.mostrar_rasgo()
            if self.dificil:
                dano = int(dano * 1.25)
            if not self.completo:
                dano = max(1, int(dano * 0.6))
            if "colageno" in self.motivos:
                dano = max(1, dano - 3)
            self.animar("agitacion", self.ctx_base())
            self.dano_total += dano
            self.mon["energia"] = max(0, self.mon["energia"] - dano)
            sonido.reproducir("golpe")
            self.decir(tr("Agitación térmica de {nombre}: −{n} de energía.", nombre=nombre, n=dano))
            if self.mon["energia"] <= 0 and "zinc" in self.motivos and not self.zinc_usado:
                self.zinc_usado = True
                self.mon["energia"] = 1
                self.decir(tr("¡Dedo de zinc! El Zn2+ mantiene plegado a tu residuo: 1 de energía."))
            if s["afinidad"] > 0 and random.random() < 0.2:
                s["afinidad"] = max(0, s["afinidad"] - 6)
                self.decir(tr("{nombre} se desordena un poco (−6 afinidad).", nombre=nombre))
                self.perder_racha()
            self.rasgos_del_turno()
        self.turno += 1
        return resultado

    def tras_mi_turno(self):
        self.turnos_jugador += 1
        if not self.tipos_visible and self.turnos_jugador >= TURNOS_PARA_REVELAR \
                and not (self.dificil or self.ciego):
            self.tipos_visible = True
            self.decir(tr("Su grupo ya es evidente: {grupo}.", grupo=datos.nombre_tipos(self.tipos_naturales())))

    def deducir(self):
        """Adivinar el grupo del salvaje. Devuelve True si gastó el turno."""
        if self.tipos_visible:
            self.decir(tr("Ya conoces su grupo."))
            return False
        nombres = [datos.TIPOS[t]["nombre"] for t in datos.ORDEN_TIPOS]
        p = d.menu(self.win, tr("¿Grupo de Lehninger?"), nombres,
                   ayuda=tr("¿Solo C/H? ¿anillo? ¿OH/SH/amida? ¿NH3+? ¿COO−?"))
        if p is None:
            return False
        elegidos = (datos.ORDEN_TIPOS[p],)
        if elegidos == ("ARO",):
            s = d.menu(self.win, tr("¿Y su carácter?"), [tr("Más no polar (sin OH ni N–H)"),
                                                         tr("Algo polar (tiene OH o N–H)")])
            if s is None:
                return False
            elegidos = ("ARO", "NP" if s == 0 else "POL")
        self.tipos_visible = True
        if set(elegidos) == set(self.tipos_naturales()):
            self.salvaje["afinidad"] = min(100, self.salvaje["afinidad"] + 10)
            msgs = progreso.dar_xp(self.mon, 5)
            self.decir(tr("Correcto: {grupo}. +10 afinidad, +5 XP",
                          grupo=datos.nombre_tipos(self.tipos_naturales())))
            self.sumar_racha()
            sonido.reproducir("correcto")
            for msg in msgs:
                self.decir(msg)
            return False      # acertar no gasta el turno
        self.decir(tr("No. Era {grupo}. Pierdes el turno.", grupo=datos.nombre_tipos(self.tipos_naturales())))
        self.perder_racha()
        sonido.reproducir("error")
        return True

    def cambiar(self, forzado=False):
        equipo = self.juego["equipo"]
        filas, indices = [], []
        for i, m in enumerate(equipo):
            if i == self.activo or m["energia"] <= 0:
                continue
            f = datos.forma(m["id"])
            filas.append([f["nombre"], tr("Nv {n}", n=m["nivel"]),
                          datos.nombre_tipos(f["tipos"], corto=True),
                          tr("energía {n}", n=m["energia"])])
            indices.append(i)
        opciones = ["".join(c[0] for c in fila) for fila in d.alinear(filas)]
        if not opciones:
            return False
        while True:
            sel = d.menu(self.win, tr("¿Quién entra?"), opciones)
            if sel is not None:
                break
            if not forzado:
                return False
        self.activo = indices[sel]
        self._reiniciar_estado()
        self.decir(tr("Entra {nombre}.", nombre=datos.forma(self.mon["id"])["nombre"]))
        return True

    def preguntar(self, tipo):
        """Pregunta sobre el rival. En las de reconocimiento solo cuenta la
        estructura: se ocultan su nombre y el registro, que lo menciona."""
        visible, log = self.nombre_visible, self.log
        if tipo in preguntas.RECONOCER:
            self.nombre_visible, self.log = False, []
        self.dibujar()
        L = self.layout()
        # la pregunta tapa la arena y tu recuadro completos, sin salirse; la
        # estructura queda a la izquierda, a la vista
        bien = preguntas.preguntar(self.win, self.juego, self.aa, tipo,
                                   L["arena"], L["x"], L["w"],
                                   alto_min=L["yo"] + 4 - L["arena"], estructura=True)
        self.nombre_visible, self.log = visible, log
        return bien

    def reconocer(self):
        """Al aparecer uno que ya capturaste: si lo reconoces, se une más fácil."""
        if self.preguntar(preguntas.elegir_reconocer(self.juego, self.aa)):
            self.nombre_visible = True
            self.salvaje["afinidad"] = min(100, self.salvaje["afinidad"] + AFINIDAD_RECONOCER)
            self.decir(tr("Lo reconociste: +{n} de afinidad.", n=AFINIDAD_RECONOCER))
        else:
            self.decir(tr("No lo reconociste: su nombre queda oculto."))

    def lanzar_trna(self):
        """Devuelve 'capturado', 'huyo' o None."""
        if self.salvaje["afinidad"] < AFINIDAD_TRNA:
            self.decir(tr("El ARNt no se une: la afinidad debe ser ≥ {n}.", n=AFINIDAD_TRNA))
            return None
        bien = self.preguntar(preguntas.elegir_tipo(self.juego, self.aa, self.propiedades_permitidas()))
        a = datos.AMINOACIDOS[self.aa]
        if bien:
            self.nombre_visible = self.tipos_visible = True
            p = self.prob_captura()
            if random.random() >= p:
                # reconociste al aminoácido, pero el ARNt no se acopló al codón
                self.fallos_trna += 1
                self.salvaje["afinidad"] = max(0, self.salvaje["afinidad"] - 10)
                self.perder_racha()
                sonido.reproducir("error")
                self.decir(tr("El ARNt se acopla mal (tenía {p} de probabilidad): −10 afinidad. "
                              "El próximo intento será más fácil.", p=f"{p:.0%}"))
                return self.turno_salvaje()
            ctx = self.ctx_base()
            ctx["codon"] = random.choice(a["codones"])
            ctx["tres"] = a["tres"]
            ctx["color_rival"] = a["tipos"][0]
            self.animar("trna", ctx)
            return self.registrar_captura()
        self.salvaje["afinidad"] = max(0, self.salvaje["afinidad"] - 20)
        self.perder_racha()
        self.decir(tr("El ARNt se suelta (−20 afinidad)."))
        if random.random() < 0.3:
            self.decir(tr("{nombre} aprovechó para escapar.", nombre=self.nombre_salvaje()))
            return "huyo"
        return self.turno_salvaje()

    def registrar_captura(self):
        """El aminoácido se une a tu equipo (o es un entrenamiento). Devuelve 'capturado'."""
        a = datos.AMINOACIDOS[self.aa]
        limpia = self.dano_total == 0 and not self.facil
        perfecta = self.salvaje["afinidad"] >= 90
        if self.sparring:
            sonido.reproducir("captura")
            d.popup(self.win, tr("¡El ARNt se acopla! Es un entrenamiento: el aminoácido no se "
                                 "une a tu equipo."), tr("Captura de entrenamiento"),
                    attr=d.c("bien"))
            return "capturado"
        nivel = self.salvaje["nivel"] + (2 if self.rara else 0)
        progreso.capturar(self.juego, self.aa, nivel, self.rara)
        progreso.contar(self.juego, "salvajes")
        progreso.contar(self.juego, "capt_" + self.modo)
        if self.ph_cambios:
            progreso.contar(self.juego, "capt_ph")
        xp = 15 + (10 if perfecta else 0) + (30 if self.rara else 0)
        if self.dificil:
            xp = int(xp * 1.5)
        msgs = progreso.dar_xp(self.mon, xp)
        sonido.reproducir("captura")
        texto = tr("{nombre} ({tres}, {una}) se une a tu equipo.\n\nGrupo: {grupo}\n"
                   "Ficha completa en la Aminodex [X].", nombre=a["nombre"], tres=a["tres"],
                   una=self.aa, grupo=datos.nombre_tipos(a["tipos"]))
        extras = []
        if self.rara:
            progreso.contar(self.juego, "raras")
            self.juego["objetos"]["ATP"] = min(9, self.juego["objetos"]["ATP"] + 2)
            extras.append(tr("♥ ¡Variante rara! Nivel +2 y +2 ATP."))
        if limpia:
            progreso.contar(self.juego, "limpias")
            extras.append(tr("Captura limpia: no recibiste daño."))
        if perfecta:
            extras.append(tr("Afinidad ≥ 90: +10 XP."))
        if extras:
            texto += "\n\n" + "\n".join(extras)
        if msgs:
            texto += "\n\n" + "\n".join(msgs)
        d.popup(self.win, texto, tr("Captura"), attr=d.c("bien"))
        return "capturado"

    def propiedades_permitidas(self):
        """Preguntas de propiedades según el modo (None = todas)."""
        return None if self.completo else modos.PROPIEDADES_MEDIO

    # ----------------------------------------------------- modo Fácil
    def _zona_pregunta(self):
        alto, ancho = self.win.getmaxyx()
        arte = datos.forma(self.aa)["arte"]
        x = d.ancho_estructura(arte) + 4
        if ancho - x < 40:
            return len(arte) + 3, 1, min(64, ancho - 2)
        return 2, x, min(64, ancho - x - 1)

    def dibujar_facil(self, paso):
        w = self.win
        alto, ancho = w.getmaxyx()
        w.erase()
        d.reiniciar_regiones()
        d.put(w, 0, 1, tr("Aminoácido salvaje  ·  {zona}  ·  modo Fácil",
                          zona=datos.ZONAS[self.zona]["nombre"]), d.c("titulo", curses.A_BOLD))
        d.put(w, 1, 1, tr("Reconoce su estructura: {n}/3", n=paso) + "  "
              + ("♥ " if self.rara else ""), d.c("texto", curses.A_BOLD))
        d.barra(w, 1, 34, 18, paso, 3, d.c("bien"))
        arte = datos.forma(self.aa)["arte"]
        d.estructura(w, 2, 1, arte)
        for i, l in enumerate(self.log[-3:]):
            d.put(w, alto - 4 + i, 1, ("› " + l)[:ancho - 2], d.c("texto" if i == len(self.log[-3:]) - 1 else "tenue"))
        d.fila_botones(w, alto - 1, 1, [(tr("Huir [Esc]"), d.ESC)], ancho - 2)
        w.refresh()

    def _bucle_facil(self):
        if not self.juego["equipo"]:
            return "derrota"
        if self.activo is None:
            self.activo = 0                  # en Fácil no hay daño: sirve cualquiera
        paso = errores = 0
        self.decir(tr("Para atraparlo, reconoce su estructura: nombre, código de 3 letras y de 1 letra."))
        while paso < 3:
            self.dibujar_facil(paso)
            y, x, ancho = self._zona_pregunta()
            bien = preguntas.preguntar(self.win, self.juego, self.aa, preguntas.RECONOCER[paso],
                                       y, x, ancho, estructura=True, opciones=True, salir=True)
            if bien is None:
                if d.menu(self.win, tr("¿Dejar al aminoácido?"),
                          [tr("Seguir intentando"), tr("Huir")]) == 1:
                    return "huiste"
                continue
            if bien:
                paso += 1
                self.nombre_visible = True
                self.salvaje["afinidad"] = int(100 * paso / 3) if errores else 100 * paso // 3 + 1
                sonido.reproducir("correcto")
                self.decir(tr("¡Bien! {n}/3.", n=paso))
            else:
                errores += 1
                sonido.reproducir("error")
                self.decir(tr("Casi: mira la estructura e inténtalo de nuevo."))
        self.nombre_visible = self.tipos_visible = True
        self.salvaje["afinidad"] = 100 if errores == 0 else 80
        return self.registrar_captura()

    def info(self):
        f = datos.forma(self.mon["id"])
        nombre_r = datos.GRUPO_R.get(f["base"], ("", "", ""))
        lineas = [tr("Grupo: {grupo}", grupo=datos.nombre_tipos(f["tipos"]))]
        if not f["evo"]:
            lineas.append(tr("Grupo R: {nombre}  {formula}  ({clase})", nombre=nombre_r[0],
                             formula=nombre_r[1], clase=nombre_r[2]))
        lineas.append(tr("pH del arena: {ph} (natural en esta zona: {ref})  [P] para cambiarlo",
                         ph=f"{self.ph:.1f}", ref=f"{self.ph_zona:.1f}"))
        r = self.rasgo()
        if r and (self.nombre_visible or self.rasgo_visto):
            lineas.append(tr("Rasgo del rival, {nombre}: {desc}", nombre=r[0], desc=r[1]))
        if self.motivos:
            lineas.append(tr("Motivos activos: {lista}",
                             lista=", ".join(motivos.MOTIVOS[m]["nombre"] for m in self.motivos)))
        lineas.append("")
        for i, mid in enumerate(self.movimientos()):
            m = datos.MOVIMIENTOS[mid]
            tipo = datos.TIPOS[m["tipo"]]["nombre"] if m["tipo"] in datos.TIPOS else tr("Neutro")
            contra = ""
            if self.tipos_visible:
                mult, partes = self._mult_mov(mid)
                contra = f"  → {self._interaccion_principal(partes)} ×{datos.fmt_mult(mult)}"
            lineas.append(tr("{i}) {nombre} [{tipo}] poder {poder}{contra}", i=i + 1, nombre=m["nombre"],
                             tipo=tipo, poder=m["poder"], contra=contra))
            lineas.append(f"   {m['desc']}")
            if m.get("ciencia"):
                lineas.append(f"   └ {m['ciencia']}")
        d.popup(self.win, "\n".join(lineas), tr("Interacciones de {nombre}", nombre=f["nombre"]), ancho=86)

    # -------------------------------------------------------------- bucle
    def jugar(self):
        resultado = self._bucle()
        return self.finalizar(resultado)

    def _bucle(self):
        if self.facil:
            return self._bucle_facil()
        if self.activo is None:
            return "derrota"
        if progreso.capturado(self.juego, self.aa):
            self.reconocer()
        if self.completo:
            self.decir(tr("Deduce su grupo [D] o interactúa [1-5]."))
        else:
            self.decir(tr("Elige una interacción [1-5] para subir la afinidad; con 50 o más, lanza el ARNt [T]."))
        if "cremallera" in self.motivos and self.juego["objetos"]["ATP"] < 9:
            self.juego["objetos"]["ATP"] += 1
            self.decir(tr("Cremallera de leucina: +1 ATP."))
        while True:
            self.dibujar()
            k = d.tecla(self.win)
            resultado = None
            movs = self.movimientos()
            if isinstance(k, str) and k.isdigit() and 1 <= int(k) <= len(movs):
                self.usar(movs[int(k) - 1])
                self.tras_mi_turno()
                resultado = self.turno_salvaje()
            elif d.es(k, "t"):
                resultado = self.lanzar_trna()
                if resultado == "capturado":
                    return resultado
            elif d.es(k, "d"):
                if self.deducir():
                    resultado = self.turno_salvaje()
            elif d.es(k, "p"):
                if self.cambiar_ph():
                    resultado = self.turno_salvaje()
            elif d.es(k, "c"):
                if self.cambiar():
                    self.perder_racha()
                    resultado = self.turno_salvaje()
            elif d.es(k, "h"):
                if random.random() < 0.8:
                    sonido.reproducir("huida")
                    return "huiste"
                self.decir(tr("No lograste escapar."))
                resultado = self.turno_salvaje()
            elif d.es(k, "v"):
                i = anim.ORDEN_VEL.index(self.velocidad)
                self.juego["ajustes"]["velocidad"] = anim.ORDEN_VEL[(i + 1) % len(anim.ORDEN_VEL)]
                self.decir(tr("Velocidad de animación: {vel}.", vel=tr(self.velocidad)))
            elif d.es(k, "s"):
                activo = ajustes.alternar("sonido")
                self.decir(tr("Sonido activado.") if activo else tr("Sonido desactivado."))
                if not sonido.disponible():
                    self.decir(tr("Este sistema no tiene winsound: solo suena en Windows."))
            elif d.es(k, "m", "?"):
                tipos = self.tipos_salvaje() if self.tipos_visible else None
                manual.mostrar(self.win, self.juego, "afinidad", rival=tipos)
            elif d.es(k, "i"):
                self.info()
            if resultado == "huyo":
                self.dibujar()
                d.popup(self.win, tr("{nombre} se escapó.", nombre=self.nombre_salvaje()), tr("Combate"))
                return "huyo"
            if self.mon["energia"] <= 0:
                nombre = datos.forma(self.mon["id"])["nombre"]
                self.decir(tr("{nombre} se desnaturalizó.", nombre=nombre))
                self.perder_racha()
                self.dibujar()
                if not self.cambiar(forzado=True):
                    return "derrota"


def combate(win, juego, aa, nivel, zona, ph=None):
    return Combate(win, juego, aa, nivel, zona, ph).jugar()


def combate_con_datos(win, juego, aa, nivel, zona, ph=None, sparring=False, ciego=False):
    """Igual que combate(), pero devuelve también el combate (turnos, combo, daño)."""
    c = Combate(win, juego, aa, nivel, zona, ph, sparring, ciego)
    return c.jugar(), c
