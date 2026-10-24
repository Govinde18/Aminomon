"""Química del pH en el combate.

Cada zona tiene su pH. El jugador puede cambiarlo durante un combate (bomba
de protones: baja 1; base: sube 1) y la carga de las cadenas laterales se
calcula con Henderson-Hasselbalch (datos.carga_cadena). Lo que cuenta es el
cambio respecto al pH natural de la zona: en el pH natural todo funciona como
en la tabla de Lehninger.

  - Los puentes salinos y las repulsiones dependen de cuánta carga conserva
    cada cadena (His: pKR 6, se protona al acidificar y se apaga al alcalinizar).
  - Asp y Glu se protonan al bajar mucho el pH y dejan de ser aniones.
  - Cys y Tyr pierden el H+ de su cadena al subir el pH y se vuelven aniones.
"""

import datos
from idioma import tr

PH_MIN, PH_MAX = 3.5, 10.5

PH_ZONA = {
    "membrana": 7.4, "interfase": 7.4, "citosol": 7.2, "ribosomas": 7.2,
    "nucleo": 7.4, "nucleolo": 7.4, "re": 7.2, "golgi": 6.3, "lisosoma": 4.8,
    "mec": 7.4, "mitocondria": 8.0,
}
IONICOS = ("POS", "NEG")


def ph_de_zona(zona):
    return PH_ZONA.get(zona, 7.4)


def limitar(ph):
    return max(PH_MIN, min(PH_MAX, round(ph, 1)))


def carga(aa, ph):
    """Carga de la cadena lateral a ese pH (0 si no se ioniza)."""
    return datos.carga_cadena(aa, ph)


def factor(aa, ph, ph_ref):
    """Cuánta de su carga conserva respecto a la que tiene en el pH natural de
    la zona. 1.0 = igual; 0 = neutra; hasta 1.5 = más cargada que de costumbre."""
    if aa not in datos.PKA_IONIZABLES:
        return 1.0
    q0 = abs(carga(aa, ph_ref))
    if q0 < 1e-6:
        return 1.0
    return max(0.0, min(1.5, abs(carga(aa, ph)) / q0))


def tipos_efectivos(aa, tipos, ph):
    """Tipos de un aminoácido salvaje al pH actual (los de Lehninger, salvo que
    el pH le quite o le ponga una carga)."""
    if aa in ("D", "E") and carga(aa, ph) > -0.5:
        return ("POL",)                     # el carboxilo se protona: COOH
    if aa == "C" and carga(aa, ph) <= -0.5:
        return ("NEG",)                     # tiolato S-
    if aa == "Y" and carga(aa, ph) <= -0.5:
        return ("ARO", "NEG")               # fenolato
    return tuple(tipos)


def ajustar_ionica(pm, f):
    """Ajusta un multiplicador de interacción iónica según la carga relativa f."""
    if pm > 1:
        return 1 + (pm - 1) * f             # puente salino, catión-pi
    if pm == 0:
        return max(0.0, 1 - f)              # repulsión: se apaga si no hay carga
    return pm


def explicar(aa, ph, ph_ref):
    """Texto corto con la ionización de la cadena a ese pH (o None)."""
    if aa not in datos.PKA_IONIZABLES:
        return None
    q = abs(carga(aa, ph))
    nombre = datos.AMINOACIDOS[aa]["tres"]
    return tr("{aa} a pH {ph}: carga {q:.0%} de la máxima", aa=nombre, ph=f"{ph:.1f}", q=q)


def nota_ph(ph, ph_ref):
    """Descripción del pH del arena para el recuadro."""
    if abs(ph - ph_ref) < 0.05:
        return tr("pH {ph}", ph=f"{ph:.1f}")
    flecha = "▼" if ph < ph_ref else "▲"
    return tr("pH {ph} {flecha} (natural {ref})", ph=f"{ph:.1f}", flecha=flecha,
              ref=f"{ph_ref:.1f}")
