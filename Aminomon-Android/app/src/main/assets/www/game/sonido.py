"""Efectos de sonido con winsound (solo Windows; en otros sistemas no hace
nada). Los pitidos suenan en un hilo aparte para no frenar el juego y, si ya
suena uno, el nuevo se descarta en vez de acumularse."""

import threading

import ajustes

try:
    import winsound
except ImportError:          # Linux y macOS
    winsound = None

# nombre -> [(frecuencia en Hz, duración en ms)]
TONOS = {
    "correcto": [(880, 60), (1175, 80)],
    "error": [(247, 130)],
    "golpe": [(311, 70)],
    "critico": [(660, 45), (990, 45), (1320, 80)],
    "captura": [(523, 70), (659, 70), (784, 70), (1047, 150)],
    "nivel": [(659, 60), (784, 60), (988, 60), (1319, 120)],
    "logro": [(784, 80), (988, 80), (1175, 80), (1568, 180)],
    "huida": [(392, 70), (294, 110)],
    "ph": [(523, 50), (415, 50)],
    "paso": [(1000, 20)],
    "menu": [(700, 20)],
    "viaje": [(440, 50), (660, 50), (880, 50)],
}
_CERROJO = threading.Lock()


def disponible():
    return winsound is not None


def _tocar(notas):
    if not _CERROJO.acquire(blocking=False):
        return
    try:
        for frecuencia, ms in notas:
            winsound.Beep(frecuencia, ms)
    except Exception:  # noqa: BLE001 (sin tarjeta de sonido, etc.)
        pass
    finally:
        _CERROJO.release()


def reproducir(nombre):
    if winsound is None or not ajustes.obtener("sonido"):
        return
    notas = TONOS.get(nombre)
    if notas:
        threading.Thread(target=_tocar, args=(notas,), daemon=True).start()
