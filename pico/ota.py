# ota.py — busca e instala actualizaciones desde internet (menú -> Sistema -> Actualizar, o solo
# una vez al día si está activada la actualización automática).
#
# En el servidor hay una carpeta con los .py y un manifest.json:
#   {"product": "knobeast", "build": 14, "version": "1.4",
#    "files": [{"name": "app.py", "size": 1234, "sha256": "..."}], "sig": "..."}
# Seguridad:
#  - "sig" es una firma Ed25519. El mando solo tiene la clave PÚBLICA (clave_publica.py); la
#    privada está únicamente en el ordenador que publica. Nadie más puede fabricar una versión
#    que el mando acepte, ni siquiera quien saque la clave de otro mando.
#  - "build" no puede ser menor que el instalado: no se puede volver a una versión antigua.
#  - La conexión HTTPS comprueba el certificado del servidor (raíces de certs.py) y la hora (NTP).
#  - Cada archivo se comprueba con su sha256; updater.py guarda copia y main.py vuelve atrás
#    sola si la versión nueva no arranca.
import socket
import hashlib
import binascii
import json
import os
import gc
import updater

DEFAULT_URL = ""        # sin URL no se busca nada (la edición oficial la trae en clave_publica.py)
NET_PROTECTED = ("main.py", "config.py")      # no llegan nunca por internet
PRODUCT = "knobeast"
_time_ok = False
_manifest = None        # el último manifest verificado (para saber si hay paquete)


class OtaError(Exception):
    pass


def _split(url):
    if url.startswith("https://"):
        tls, rest, port = True, url[8:], 443
    elif url.startswith("http://"):
        tls, rest, port = False, url[7:], 80
    else:
        raise OtaError("URL rara")
    host, _, path = rest.partition("/")
    if ":" in host:
        host, p = host.split(":")
        port = int(p)
    return tls, host, port, "/" + path


def sync_time():
    """La comprobación del certificado necesita la hora buena: se pide por NTP una vez."""
    global _time_ok
    if _time_ok:
        return
    try:
        import ntptime
        ntptime.settime()
        _time_ok = True
    except ImportError:          # en el ordenador no hace falta
        _time_ok = True
    except Exception as e:
        raise OtaError("Sin hora (NTP)")


def get(url, sink, timeout=20, redirects=3, verify_tls=True):
    """Descarga url y va pasando el cuerpo a sink(bytes). Sigue redirecciones."""
    tls, host, port, path = _split(url)
    s = socket.socket()
    try:
        s.settimeout(timeout)
        s.connect(socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0][-1])
        if tls:
            import ssl
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if verify_tls:
                import certs
                ctx.verify_mode = ssl.CERT_REQUIRED
                for ca in certs.ROOTS:
                    ctx.load_verify_locations(cadata=ca)
            else:
                ctx.verify_mode = ssl.CERT_NONE
            try:
                s = ctx.wrap_socket(s, server_hostname=host)
            except ValueError as e:              # mbedtls: certificado o nombre no válidos
                raise OtaError("Certificado no valido")
        s.write(("GET %s HTTP/1.0\r\nHost: %s\r\nUser-Agent: sonos-knob\r\nConnection: close\r\n\r\n"
                 % (path, host)).encode())
        head = b""
        while b"\r\n\r\n" not in head:
            d = s.read(256)
            if not d:
                break
            head += d
            if len(head) > 8192:
                raise OtaError("Cabecera enorme")
        hdr, _, body = head.partition(b"\r\n\r\n")
        lines = hdr.decode().split("\r\n")
        try:
            status = int(lines[0].split(" ")[1])
        except Exception:
            raise OtaError("Respuesta rara")
        if status in (301, 302, 303, 307, 308) and redirects > 0:
            loc = ""
            for ln in lines[1:]:
                if ln.lower().startswith("location:"):
                    loc = ln.split(":", 1)[1].strip()
            if loc.startswith("/"):
                default = 443 if tls else 80
                loc = ("https://" if tls else "http://") + host + ("" if port == default else ":%d" % port) + loc
            s.close()
            return get(loc, sink, timeout, redirects - 1, verify_tls)
        if status != 200:
            raise OtaError("HTTP %d" % status)
        if body:
            sink(body)
        while True:
            try:
                d = s.read(1024)
            except OSError:          # algunos servidores cierran TLS sin avisar
                break
            if not d:
                break
            sink(d)
        return status
    finally:
        try:
            s.close()
        except Exception:
            pass


def _hex(b):
    return binascii.hexlify(b).decode()


def canonical(m):
    """Texto que se firma (el mismo que genera publicar_actualizacion.py)."""
    out = [str(m.get("product")), str(int(m["build"])), str(m["version"])]
    for f in sorted(m["files"], key=lambda f: f["name"]):
        out.append("%s %d %s" % (f["name"], int(f["size"]), f["sha256"]))
    return ("\n".join(out) + "\n").encode()


def verify_manifest(m):
    try:
        import clave_publica
        pub = binascii.unhexlify(clave_publica.PUBLIC)
    except Exception:
        raise OtaError("Falta clave publica")
    if len(pub) != 32:
        raise OtaError("Sin actualizaciones")
    import ed25519
    try:
        sig = binascii.unhexlify(m.get("sig", ""))
    except Exception:
        sig = b""
    gc.collect()
    if m.get("product") != PRODUCT or not ed25519.verify(pub, canonical(m), sig):
        raise OtaError("Firma no valida")


def local_build():
    try:
        import version
        return int(getattr(version, "BUILD", 0))
    except Exception:
        return 0


def file_sha(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(1024)
                if not b:
                    break
                h.update(b)
    except OSError:
        return None
    return _hex(h.digest())


def check(base, log=print, verify_tls=True):
    """Descarga y verifica el manifest. Devuelve (version, archivos_a_actualizar)."""
    if not base.endswith("/"):
        base += "/"
    buf = []
    size = [0]

    def sink(b):
        size[0] += len(b)
        if size[0] > 16384:
            raise OtaError("Manifest enorme")
        buf.append(b)

    gc.collect()
    if verify_tls and base.startswith("https"):
        sync_time()
    get(base + "manifest.json", sink, verify_tls=verify_tls)
    try:
        m = json.loads(b"".join(buf))
        int(m["build"])
    except Exception:
        raise OtaError("Manifest roto")
    verify_manifest(m)
    if int(m["build"]) < local_build():
        raise OtaError("Version antigua")
    todo = []
    for f in m["files"]:
        name = f["name"]
        if name in NET_PROTECTED or not updater.valid_name(name):
            continue
        if file_sha(name) != f["sha256"]:
            todo.append(f)
    global _manifest
    _manifest = m
    log("Servidor: build %s (%s), cambian %d archivos" % (m["build"], m["version"], len(todo)))
    return m["version"], todo


def _download(url, path, f, verify_tls):
    """Descarga un archivo a 'path' comprobando tamaño y sha256. Lanza OtaError/OSError si falla."""
    gc.collect()
    h = hashlib.sha256()
    n = [0]
    out = open(path, "wb")

    def sink(b):
        n[0] += len(b)
        if n[0] > f["size"]:
            raise OtaError("%s: tamano" % f["name"])
        h.update(b)
        out.write(b)

    try:
        get(url, sink, verify_tls=verify_tls)
    finally:
        out.close()
    if n[0] != f["size"] or _hex(h.digest()) != f["sha256"]:
        raise OtaError("%s llego mal" % f["name"])


def _bundle_ok(m):
    b = m.get("bundle") if m else None
    if not b or b.get("format") != "zlib":
        return False
    try:
        import deflate      # noqa: F401
        return True
    except ImportError:
        return False


def _install_bundle(base, m, todo, progress, log, verify_tls, tries):
    """Descarga el paquete comprimido (un solo archivo), lo descomprime y deja en 'nuevo' los
    archivos que cambian. Cada uno se comprueba con el sha256 firmado del manifest."""
    import deflate
    from time import sleep_ms
    b = m["bundle"]
    tmp = updater.STAGE + "/_paquete"
    for attempt in range(tries):
        try:
            gc.collect()
            h = hashlib.sha256()
            n = [0]
            out = open(tmp, "wb")

            def sink(x):
                n[0] += len(x)
                if n[0] > b["size"]:
                    raise OtaError("Paquete: tamano")
                h.update(x)
                out.write(x)
                if progress:
                    progress(n[0], b["size"], None)

            try:
                get(base + b["file"], sink, verify_tls=verify_tls)
            finally:
                out.close()
            if n[0] != b["size"] or _hex(h.digest()) != b["sha256"]:
                raise OtaError("Paquete llego mal")
            break
        except Exception as e:
            log("Paquete: intento %d fallido (%r)" % (attempt + 1, e))
            if attempt == tries - 1:
                raise
            sleep_ms(1500 * (attempt + 1))
    need = [f["name"] for f in todo]
    gc.collect()
    with open(tmp, "rb") as f:
        z = deflate.DeflateIO(f, deflate.ZLIB)
        for fi in m["files"]:                 # mismo orden con el que se empaquetó
            left = fi["size"]
            hh = hashlib.sha256()
            o = open(updater.STAGE + "/" + fi["name"], "wb") if fi["name"] in need else None
            try:
                while left > 0:
                    chunk = z.read(min(1024, left))
                    if not chunk:
                        raise OtaError("Paquete corto")
                    left -= len(chunk)
                    hh.update(chunk)
                    if o:
                        o.write(chunk)
            finally:
                if o:
                    o.close()
            if _hex(hh.digest()) != fi["sha256"]:
                raise OtaError("%s llego mal" % fi["name"])
    os.remove(tmp)
    return need


def install(base, todo, progress=None, log=print, verify_tls=True, tries=4):
    """Instala lo que cambia. Si el servidor ofrece paquete comprimido, se baja en una sola
    descarga; si no, archivo a archivo. progress(hecho, total, nombre|None)."""
    if not base.endswith("/"):
        base += "/"
    m = _manifest
    if _bundle_ok(m):
        try:
            os.mkdir(updater.STAGE)
        except OSError:
            pass
        names = _install_bundle(base, m, todo, progress, log, verify_tls, tries)
        updater.check(names)
        updater.apply(names)
        updater._clear(updater.STAGE)
        log("Instalados (paquete): %s" % ", ".join(names))
        return names
    return _install_files(base, todo, progress, log, verify_tls, tries)


def _install_files(base, todo, progress=None, log=print, verify_tls=True, tries=4):
    """Descarga los archivos a 'nuevo', comprueba sha256 y sintaxis, e instala. Luego hay que reiniciar.
    Cada archivo se reintenta varias veces si la red falla, y lo ya descargado bien se conserva
    para el siguiente intento (si se corta, no vuelve a empezar de cero)."""
    from time import sleep_ms
    if not base.endswith("/"):
        base += "/"
    try:
        os.mkdir(updater.STAGE)
    except OSError:
        pass
    names = []
    for i, f in enumerate(todo):
        name = f["name"]
        path = updater.STAGE + "/" + name
        if progress:
            progress(i + 1, len(todo), name)
        if file_sha(path) != f["sha256"]:
            for attempt in range(tries):
                try:
                    _download(base + name, path, f, verify_tls)
                    break
                except Exception as e:
                    log("%s: intento %d fallido (%r)" % (name, attempt + 1, e))
                    if attempt == tries - 1:
                        raise
                    sleep_ms(1500 * (attempt + 1))
        names.append(name)
    updater.check(names)
    updater.apply(names)
    updater._clear(updater.STAGE)
    log("Instalados: %s" % ", ".join(names))
    return names
