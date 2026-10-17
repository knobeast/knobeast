# main.py — arranque seguro. MicroPython lo ejecuta al encender.
#
# Este archivo NO se cambia al actualizar desde la web, para que el mando siempre pueda
# recuperarse:
#  - Si una actualización falla al arrancar, vuelve sola a la versión anterior.
#  - Si se queda colgada, basta con apagar y encender 3 veces: vuelve a la anterior.
#  - Encender con la rueda pulsada entra directamente en Ajustes (la página del móvil).
import sys
import os
from machine import Pin, reset
from time import sleep_ms

STATE = "actualizacion.json"     # {"pending": True, "boots": n, "files": [...], "new": [...]}
BACKUP = "anterior"              # copia de los archivos que sustituyó la última actualización
MAX_BOOTS = 3


def _load():
    try:
        import json
        with open(STATE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save(d):
    import json
    with open(STATE, "w") as f:
        json.dump(d, f)


def _copy(src, dst):
    with open(src, "rb") as a, open(dst, "wb") as b:
        while True:
            chunk = a.read(1024)
            if not chunk:
                break
            b.write(chunk)


def rollback(reason):
    st = _load()
    print("Volviendo a la version anterior:", reason)
    for name in st.get("files", []):
        try:
            _copy(BACKUP + "/" + name, name)
        except OSError:
            pass
    for name in st.get("new", []):          # archivos que no existían antes
        try:
            os.remove(name)
        except OSError:
            pass
    _save({"rolled_back": str(reason)[:120]})
    sleep_ms(200)
    reset()


def confirm():
    """La versión nueva ha llegado a controlar Sonos: se da por buena."""
    st = _load()
    if st.get("pending"):
        st.pop("pending")
        st.pop("boots", None)
        _save(st)
        print("Actualizacion confirmada")


def _log_error(e):
    try:
        if os.stat("errores.txt")[6] > 8000:
            os.remove("errores.txt")
    except OSError:
        pass
    try:
        with open("errores.txt", "a") as f:
            sys.print_exception(e, f)
    except Exception:
        pass


def boot():
    st = _load()
    pending = st.get("pending")
    try:
        import config
        sw = config.PIN_ENC_SW
    except Exception:
        sw = 12
    recovery = Pin(sw, Pin.IN, Pin.PULL_UP).value() == 0
    if pending and not recovery:
        st["boots"] = st.get("boots", 0) + 1
        _save(st)
        if st["boots"] > MAX_BOOTS:
            rollback("no llego a conectar tras %d arranques" % MAX_BOOTS)
            return
    try:
        import knob
        knob.start(recovery, confirm)
    except Exception as e:
        sys.print_exception(e)
        _log_error(e)
        if pending:
            rollback(repr(e))
            return
        sleep_ms(3000)
        reset()


boot()
