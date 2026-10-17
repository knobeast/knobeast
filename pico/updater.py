# updater.py — instala archivos nuevos del programa con copia de seguridad.
# Lo usan la página de Ajustes (subiendo los .py) y ota.py (descargándolos de internet).
#
# 1. Recibe los archivos (multipart/form-data) por trozos y los deja en la carpeta "nuevo".
# 2. Comprueba que cada uno es Python válido. Si alguno falla, no se toca nada.
# 3. Copia los que se van a sustituir a "anterior", marca la actualización como pendiente
#    y pone los nuevos en su sitio. main.py vuelve atrás sola si la versión nueva no arranca.
import os
import gc

STAGE = "nuevo"
BACKUP = "anterior"
STATE = "actualizacion.json"
PROTECTED = ("main.py",)         # el arranque seguro no se cambia desde la web
MAX_TOTAL = 400000


class UpdateError(Exception):
    pass


def _exists(p):
    try:
        os.stat(p)
        return True
    except OSError:
        return False


def _clear(d):
    if not _exists(d):
        os.mkdir(d)
        return
    for name in os.listdir(d):
        os.remove(d + "/" + name)


def valid_name(name):
    if not name.endswith(".py") or len(name) > 40 or name in PROTECTED:
        return False
    for ch in name[:-3]:
        if not ("a" <= ch <= "z" or "0" <= ch <= "9" or ch == "_"):
            return False
    return True


def _filename(headers):
    i = headers.find('filename="')
    if i < 0:
        return None
    i += 10
    name = headers[i:headers.find('"', i)]
    return name.replace("\\", "/").split("/")[-1]


def receive(first, recv, length, boundary):
    """Lee el cuerpo multipart. first: bytes ya leídos; recv(n): lee más del socket.
    Devuelve (guardados, ignorados) con los nombres de archivo."""
    if length > MAX_TOTAL:
        raise UpdateError("Demasiado grande")
    _clear(STAGE)
    delim = b"\r\n--" + boundary.encode()
    left = length - len(first)
    buf = b"\r\n" + first
    saved, skipped = [], []
    out = None
    state = "delim"

    def more():
        nonlocal buf, left
        if left <= 0:
            return False
        d = recv(min(1024, left))
        if not d:
            left = 0
            return False
        left -= len(d)
        buf += d
        return True

    while True:
        if state == "delim":
            i = buf.find(delim)
            if i < 0 or len(buf) < i + len(delim) + 2:
                if not more():
                    break
                continue
            rest = buf[i + len(delim):i + len(delim) + 2]
            buf = buf[i + len(delim) + 2:]
            if rest == b"--":
                break
            state = "headers"
        elif state == "headers":
            i = buf.find(b"\r\n\r\n")
            if i < 0:
                if len(buf) > 2048 or not more():
                    break
                continue
            name = _filename(buf[:i].decode())
            buf = buf[i + 4:]
            if name and valid_name(name):
                out = open(STAGE + "/" + name, "wb")
                saved.append(name)
            else:
                out = None
                if name:
                    skipped.append(name)
            state = "data"
        else:
            i = buf.find(delim)
            if i >= 0:
                if out:
                    out.write(buf[:i])
                    out.close()
                    out = None
                buf = buf[i:]
                state = "delim"
                continue
            keep = len(delim) + 2
            if len(buf) > keep:
                if out:
                    out.write(buf[:-keep])
                buf = buf[-keep:]
            if not more():
                break
    if out:
        out.close()
        raise UpdateError("Subida incompleta")
    if state != "delim":
        raise UpdateError("Subida incompleta")
    return saved, skipped


def check(names):
    """Compila cada archivo para detectar errores de sintaxis antes de instalar."""
    for name in names:
        path = STAGE + "/" + name
        if os.stat(path)[6] == 0:
            raise UpdateError("%s esta vacio" % name)
        gc.collect()
        with open(path) as f:
            src = f.read()
        try:
            compile(src, name, "exec")
        except SyntaxError as e:
            raise UpdateError("%s: error de sintaxis (%s)" % (name, e))
        finally:
            src = None
            gc.collect()


def _copy(src, dst):
    with open(src, "rb") as a:
        with open(dst, "wb") as b:
            while True:
                chunk = a.read(1024)
                if not chunk:
                    break
                b.write(chunk)


def apply(names):
    """Copia de seguridad + marca pendiente + sustituye. Después hay que reiniciar."""
    import json
    _clear(BACKUP)
    replaced, new = [], []
    for name in names:
        if _exists(name):
            _copy(name, BACKUP + "/" + name)
            replaced.append(name)
        else:
            new.append(name)
    with open(STATE, "w") as f:
        json.dump({"pending": True, "boots": 0, "files": replaced, "new": new}, f)
    for name in names:
        if _exists(name):
            os.remove(name)
        os.rename(STAGE + "/" + name, name)


def status():
    """Para la página: versión instalada y si la última actualización se deshizo."""
    try:
        import json
        with open(STATE) as f:
            st = json.load(f)
    except Exception:
        st = {}
    try:
        with open("version.py") as f:
            v = f.read().split('"')[1]
    except Exception:
        v = "?"
    return v, st.get("pending", False), st.get("rolled_back")
