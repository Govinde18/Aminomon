"""Ajustes globales (sonido, ratón, modo difícil), guardados en
~/.aminomon_ajustes.json. Son del jugador, no de una partida."""

import json
import os

ARCHIVO = os.path.expanduser("~/.aminomon_ajustes.json")
PREDETERMINADOS = {"sonido": True, "raton": True, "dificil": False}
_DATOS = {}


def _cargar():
    if _DATOS:
        return
    _DATOS.update(PREDETERMINADOS)
    try:
        with open(ARCHIVO, encoding="utf-8") as f:
            guardado = json.load(f)
        for k in PREDETERMINADOS:
            if isinstance(guardado.get(k), bool):
                _DATOS[k] = guardado[k]
    except (OSError, ValueError):
        pass


def obtener(clave):
    _cargar()
    return _DATOS.get(clave, PREDETERMINADOS.get(clave))


def poner(clave, valor):
    _cargar()
    _DATOS[clave] = bool(valor)
    try:
        with open(ARCHIVO, "w", encoding="utf-8") as f:
            json.dump(_DATOS, f, indent=1)
    except OSError:
        pass


def alternar(clave):
    poner(clave, not obtener(clave))
    return obtener(clave)
