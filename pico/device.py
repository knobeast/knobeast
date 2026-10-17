# device.py — identidad de este mando: un número único y la contraseña de su wifi de
# configuración. Se crean la primera vez que arranca y ya no cambian nunca: no las tocan las
# actualizaciones ni «Restablecer». Se guardan en dispositivo.json.
import json
import os

FILE = "dispositivo.json"
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"     # sin i, l, o, 0, 1 para que no se confundan
PASS_LEN = 10
_cache = None


def _random_password():
    out = ""
    limit = 256 - 256 % len(ALPHABET)            # sin sesgo
    while len(out) < PASS_LEN:
        for b in os.urandom(16):
            if b < limit and len(out) < PASS_LEN:
                out += ALPHABET[b % len(ALPHABET)]
    return out


def _unique_id():
    try:
        import machine
        import binascii
        return binascii.hexlify(machine.unique_id()).decode()
    except Exception:
        import binascii
        return binascii.hexlify(os.urandom(8)).decode()


def info():
    """{"id": "...", "ap_pass": "..."}"""
    global _cache
    if _cache:
        return _cache
    try:
        with open(FILE) as f:
            d = json.load(f)
        if len(d.get("ap_pass", "")) >= 8 and d.get("id"):
            _cache = d
            return d
    except Exception:
        pass
    d = {"id": _unique_id(), "ap_pass": _random_password()}
    with open(FILE, "w") as f:
        json.dump(d, f)
    print("Identidad nueva: %s / clave wifi de configuracion: %s" % (d["id"], d["ap_pass"]))
    _cache = d
    return d


def ap_name(cfg):
    name = getattr(cfg, "AP_NAME", "") or ""
    return name or "Knobeast-" + info()["id"][-4:].upper()
