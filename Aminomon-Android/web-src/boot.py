"""Entry point inside the Pyodide worker: runs Aminomon on the fake curses."""
import json
import os
import sys
import traceback

import js

HOME = os.path.expanduser("~")
NAMES = (".aminomon.json", ".aminomon_ajustes.json", ".aminomon_idioma")
_visto = {}


def _leer(n):
    try:
        with open(os.path.join(HOME, n), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def guardar_si_cambio():
    for n in NAMES:
        t = _leer(n)
        if t is not None and _visto.get(n) != t:
            _visto[n] = t
            js.gvSave(n, t)


def correr():
    sys.path.insert(0, "/game")
    sys.argv = ["aminomon", "--sin-actualizar"]
    for n in NAMES:                      # lo que el sistema de archivos ya trae
        _visto[n] = _leer(n)
    import curses
    curses.set_save_hook(guardar_si_cambio)
    import aminomon
    import ajustes
    import sonido

    def reproducir(nombre):
        notas = sonido.TONOS.get(nombre)
        if notas and ajustes.obtener("sonido"):
            js.gvSound(json.dumps(notas))
    sonido.reproducir = reproducir
    sonido.disponible = lambda: True

    resultado = curses.wrapper(aminomon.main)
    guardar_si_cambio()
    if resultado == "idioma":            # los textos se traducen al importar
        js.gvRestart()
    else:
        js.gvExit()


try:
    correr()
except BaseException:  # noqa: BLE001
    js.gvFatal(traceback.format_exc())
