# settings.py — ajustes guardados desde el móvil (settings.json). Mandan sobre config.py.
import json

FILE = "settings.json"
KEYS = ("WIFI_SSID", "WIFI_PASS", "ROOMS", "MAX_VOLUME", "LANG", "AUTO_UPDATE", "SCREEN_DIM", "SCREEN_OFF", "VOL_STEP")


def load():
    try:
        with open(FILE) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def apply(cfg):
    d = load()
    if "ROOM" in d and "ROOMS" not in d:      # ajustes de la versión anterior (una sola habitación)
        d["ROOMS"] = [d["ROOM"]]
    for k, v in d.items():
        if k in KEYS:
            setattr(cfg, k, v)
    if not getattr(cfg, "ROOMS", None):
        cfg.ROOMS = [getattr(cfg, "ROOM", "Comedor")]


def save(new):
    d = load()
    if "ROOM" in d:
        old = d.pop("ROOM")
        if "ROOMS" not in d:
            d["ROOMS"] = [old]
    for k, v in new.items():
        if k in KEYS:
            d[k] = v
    with open(FILE, "w") as f:
        json.dump(d, f)
