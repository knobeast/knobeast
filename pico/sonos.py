# sonos.py — cliente Sonos mínimo (UPnP/SOAP) para MicroPython y Python normal.
#
# Busca los altavoces en la red (SSDP), localiza la habitación por su NOMBRE
# leyendo la topología de grupos, y manda las órdenes de volumen, silencio y
# reproducción. No necesita conocer ninguna IP de antemano.

try:
    import usocket as socket
except ImportError:
    import socket
try:
    from time import ticks_ms, ticks_diff
except ImportError:
    import time as _t

    def ticks_ms():
        return int(_t.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

SSDP_ADDR = "239.255.255.250"
SSDP_PORT = 1900
SSDP_ST = "urn:schemas-upnp-org:device:ZonePlayer:1"

RC = ("/MediaRenderer/RenderingControl/Control", "urn:schemas-upnp-org:service:RenderingControl:1")
AVT = ("/MediaRenderer/AVTransport/Control", "urn:schemas-upnp-org:service:AVTransport:1")
ZGT = ("/ZoneGroupTopology/Control", "urn:schemas-upnp-org:service:ZoneGroupTopology:1")
GRC = ("/MediaRenderer/GroupRenderingControl/Control", "urn:schemas-upnp-org:service:GroupRenderingControl:1")


class SonosError(Exception):
    pass


# ----------------------------------------------------------------------------- utilidades

def unescape(s):
    if "&" not in s:
        return s
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
             .replace("&apos;", "'").replace("&#39;", "'").replace("&amp;", "&"))


def tag(xml, name):
    """Texto del primer <name>...</name> (sin espacios de nombres complicados)."""
    i = xml.find("<" + name)
    if i < 0:
        return ""
    i = xml.find(">", i)
    if i < 0 or xml[i - 1] == "/":
        return ""
    j = xml.find("</" + name + ">", i)
    return xml[i + 1:j] if j > 0 else ""


def attr(t, name):
    k = t.find(" " + name + '="')
    if k < 0:
        return ""
    k += len(name) + 3
    return t[k:t.find('"', k)]


def ip_from_url(url):
    # http://192.168.0.63:1400/xml/device_description.xml -> 192.168.0.63
    i = url.find("//")
    if i < 0:
        return ""
    rest = url[i + 2:]
    return rest.split("/")[0].split(":")[0]


# ----------------------------------------------------------------------------- HTTP

def _recv_all(s, sink=None, limit=16384):
    """Lee la respuesta HTTP. Si hay sink, le pasa el cuerpo a trozos (para respuestas grandes)."""
    head = b""
    while b"\r\n\r\n" not in head:
        d = s.recv(512)
        if not d:
            break
        head += d
    hdr, _, body = head.partition(b"\r\n\r\n")
    hdr = hdr.decode()
    status = int(hdr.split(" ", 2)[1]) if " " in hdr else 0
    chunked = "chunked" in hdr.lower()
    out = []
    size = 0

    def emit(b):
        nonlocal size
        if not b:
            return
        if sink:
            sink(b)
        elif size < limit:
            out.append(b)
            size += len(b)

    if chunked:
        buf = body
        while True:
            while b"\r\n" not in buf:
                d = s.recv(1024)
                if not d:
                    break
                buf += d
            line, _, buf = buf.partition(b"\r\n")
            try:
                n = int(line.split(b";")[0], 16)
            except ValueError:
                break
            if n == 0:
                break
            while len(buf) < n + 2:
                d = s.recv(1024)
                if not d:
                    break
                buf += d
            emit(buf[:n])
            buf = buf[n + 2:]
    else:
        emit(body)
        while True:
            d = s.recv(1024)
            if not d:
                break
            emit(d)
    return status, b"".join(out)


def soap(ip, service, action, args="", sink=None, timeout=3):
    path, urn = service
    body = ('<?xml version="1.0" encoding="utf-8"?>'
            '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
            's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
            '<u:%s xmlns:u="%s">%s</u:%s></s:Body></s:Envelope>' % (action, urn, args, action)).encode()
    req = ("POST %s HTTP/1.0\r\nHost: %s:1400\r\nContent-Type: text/xml; charset=\"utf-8\"\r\n"
           "SOAPACTION: \"%s#%s\"\r\nContent-Length: %d\r\nConnection: close\r\n\r\n"
           % (path, ip, urn, action, len(body))).encode()
    s = socket.socket()
    try:
        s.settimeout(timeout)
        s.connect(socket.getaddrinfo(ip, 1400)[0][-1])
        data = req + body
        while data:
            n = s.send(data)
            data = data[n:]
        status, raw = _recv_all(s, sink)
    finally:
        s.close()
    if status != 200:
        raise SonosError("%s -> HTTP %d" % (action, status))
    return raw.decode() if raw else ""


# ----------------------------------------------------------------------------- descubrimiento

def ssdp_search(timeout_ms=2500):
    """Devuelve las IPs de los Sonos que contestan."""
    msg = ("M-SEARCH * HTTP/1.1\r\nHOST: %s:%d\r\nMAN: \"ssdp:discover\"\r\nMX: 1\r\nST: %s\r\n\r\n"
           % (SSDP_ADDR, SSDP_PORT, SSDP_ST)).encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ips = []
    try:
        s.settimeout(0.3)
        dest = socket.getaddrinfo(SSDP_ADDR, SSDP_PORT)[0][-1]
        t0 = ticks_ms()
        sent = 0
        while ticks_diff(ticks_ms(), t0) < timeout_ms:
            if sent < 3 and ticks_diff(ticks_ms(), t0) >= sent * 700:
                s.sendto(msg, dest)
                sent += 1
            try:
                data, _ = s.recvfrom(1024)
            except OSError:
                if ips and ticks_diff(ticks_ms(), t0) > 1200:
                    break
                continue
            txt = data.decode()
            for line in txt.split("\r\n"):
                if line.lower().startswith("location:"):
                    ip = ip_from_url(line.split(":", 1)[1].strip())
                    if ip and ip not in ips:
                        ips.append(ip)
    finally:
        s.close()
    return ips


class _TopologyParser:
    """Lee GetZoneGroupState por trozos (puede ocupar decenas de KB) sin cargarlo entero."""

    def __init__(self):
        self.raw = ""            # texto aún escapado pendiente (una entidad &xxx; a medias)
        self.text = ""           # texto ya desescapado pendiente de analizar
        self.coordinator = ""
        self.members = []        # (uuid, ip, nombre, uuid_coordinador)

    def feed(self, chunk):
        self.raw += chunk.decode() if isinstance(chunk, bytes) else chunk
        amp = self.raw.rfind("&")
        if amp >= 0 and ";" not in self.raw[amp:]:
            work, self.raw = self.raw[:amp], self.raw[amp:]
        else:
            work, self.raw = self.raw, ""
        self.text += unescape(work)
        text, pos = self.text, 0
        while True:
            a = text.find("<ZoneGroup", pos)
            if a < 0:
                break
            b = text.find(">", a)
            if b < 0:
                break
            t = text[a:b + 1]
            if t.startswith("<ZoneGroupMember"):
                if attr(t, "Invisible") != "1":
                    self.members.append((attr(t, "UUID"), ip_from_url(attr(t, "Location")),
                                         attr(t, "ZoneName"), self.coordinator))
            elif t.startswith("<ZoneGroup ") or t.startswith("<ZoneGroup>"):
                self.coordinator = attr(t, "Coordinator")
            pos = b + 1
        rest = text[pos:]
        cut = rest.rfind("<")
        self.text = rest[cut:] if cut >= 0 else ""
        if len(self.text) > 4096:
            self.text = self.text[-2048:]


def topology(hint_ips=()):
    """Lista de habitaciones visibles: [(uuid, ip, nombre, uuid_coordinador)].
    Prueba primero las IPs conocidas; si no contestan, busca en la red."""
    tried, last = [], None
    for phase in (0, 1):
        ips = list(hint_ips) if phase == 0 else [ip for ip in ssdp_search() if ip not in tried]
        for ip in ips:
            tried.append(ip)
            p = _TopologyParser()
            try:
                soap(ip, ZGT, "GetZoneGroupState", sink=p.feed, timeout=4)
            except Exception as e:
                last = e
                continue
            if p.members:
                return p.members
    if not tried:
        raise SonosError("No contesta ningun Sonos")
    raise SonosError("Sin respuesta de topologia (%s)" % last)


def _http_get(ip, path, limit=8192, timeout=3):
    s = socket.socket()
    try:
        s.settimeout(timeout)
        s.connect(socket.getaddrinfo(ip, 1400)[0][-1])
        req = ("GET %s HTTP/1.0\r\nHost: %s:1400\r\nConnection: close\r\n\r\n" % (path, ip)).encode()
        while req:
            req = req[s.send(req):]
        status, raw = _recv_all(s, None, limit)
    finally:
        s.close()
    return raw.decode() if status == 200 and raw else ""


def model(ip):
    """'Port', 'Arc', 'Five'... (para distinguir altavoces con el mismo nombre)."""
    try:
        m = tag(_http_get(ip, "/xml/device_description.xml"), "modelName")
    except Exception:
        return ""
    return m[6:] if m.startswith("Sonos ") else m


def fixed_output(ip):
    """True si la salida tiene el volumen fijo (p. ej. un Port con la salida de línea en 'Fijo')."""
    try:
        r = soap(ip, RC, "GetOutputFixed", "<InstanceID>0</InstanceID>")
        return tag(r, "CurrentFixed") == "1"
    except Exception:
        return False


def entry_key(e):
    """Una habitación elegida se guarda como 'RINCON_xxx|Nombre' (o solo 'Nombre', como antes)."""
    k, _, label = e.partition("|")
    return k, (label or k)


def list_rooms(hint_ips=()):
    """[(uuid, nombre, etiqueta, n_grupo)] ordenado. n_grupo: 0 sola, 1, 2... agrupada.
    Si varios altavoces se llaman igual, la etiqueta lleva el modelo o un número para distinguirlos."""
    members = topology(hint_ips)
    count = {}
    for (_, _, _, c) in members:
        count[c] = count.get(c, 0) + 1
    same = {}
    for (_, _, n, _) in members:
        same[n.lower()] = same.get(n.lower(), 0) + 1
    groups = {}
    out = []
    seen = {}
    for (u, i, n, c) in sorted(members, key=lambda m: (m[2].lower(), m[0])):
        g = 0
        if count[c] > 1:
            if c not in groups:
                groups[c] = len(groups) + 1
            g = groups[c]
        label = n
        if same[n.lower()] > 1:
            k = seen.get(n.lower(), 0) + 1
            seen[n.lower()] = k
            mdl = model(i)
            label = "%s %s" % (n, mdl) if mdl else "%s %d" % (n, k)
        out.append((u, n, label, g))
    # si dos siguen igual (mismo nombre y modelo), numerarlas
    labels = [o[2] for o in out]
    fixed = []
    for idx, o in enumerate(out):
        if labels.count(o[2]) > 1:
            k = labels[:idx + 1].count(o[2])
            o = (o[0], o[1], "%s %d" % (o[2], k), o[3])
        fixed.append(o)
    return fixed


def find_room(room, hint_ips=()):
    """Compatibilidad: (ip_habitacion, ip_coordinador, nombre_exacto)."""
    r = Rooms([room])
    r.hint = list(hint_ips)
    r.locate()
    return r.ip, r.coord, r.names[0]


def _starts(s, prefixes):
    for p in prefixes:
        if s.startswith(p):
            return True
    return False


# ----------------------------------------------------------------------------- órdenes

def _vol(ip):
    return int(tag(soap(ip, RC, "GetVolume", "<InstanceID>0</InstanceID><Channel>Master</Channel>"),
                   "CurrentVolume") or 0)


def _set_vol(ip, v):
    soap(ip, RC, "SetVolume", "<InstanceID>0</InstanceID><Channel>Master</Channel><DesiredVolume>%d</DesiredVolume>" % v)


def _rel_vol(ip, d):
    r = soap(ip, RC, "SetRelativeVolume",
             "<InstanceID>0</InstanceID><Channel>Master</Channel><Adjustment>%d</Adjustment>" % d)
    return int(tag(r, "NewVolume") or 0)


def _mute(ip):
    return tag(soap(ip, RC, "GetMute", "<InstanceID>0</InstanceID><Channel>Master</Channel>"), "CurrentMute") == "1"


def _set_mute(ip, m):
    soap(ip, RC, "SetMute",
         "<InstanceID>0</InstanceID><Channel>Master</Channel><DesiredMute>%d</DesiredMute>" % (1 if m else 0))


def _clamp(cur, delta, top):
    """Subir nunca pasa del tope (pero no baja algo que ya estaba por encima); bajar llega hasta 0."""
    if delta > 0:
        return max(cur, min(top, cur + delta))
    return max(0, cur + delta)


class Rooms:
    """Controla una o varias habitaciones.
    - Una habitación: su propio volumen (aunque esté agrupada); play/pausa a su grupo.
    - Varias que forman EXACTAMENTE un grupo de Sonos: volumen de grupo (como la barra general de la app).
    - Varias sueltas (o mezcladas con otras): cada clic sube/baja lo mismo en cada una.
    Play/pausa y silencio actúan sobre todas las elegidas."""

    def __init__(self, rooms):
        if isinstance(rooms, str):
            rooms = [rooms]
        self.rooms = list(rooms)             # 'RINCON_xxx|Nombre' o 'Nombre'
        self.names = []
        for e in self.rooms:
            n = entry_key(e)[1]
            if n not in self.names:
                self.names.append(n)
        self.room = "+".join(self.names)
        self.ip = None              # primera habitación (None = sin localizar)
        self.coord = None           # coordinador de la primera
        self.ips = []
        self.coords = []
        self.group = None           # IP del coordinador si se usa volumen de grupo
        self.vols = {}
        self.hint = []
        self.missing = []           # elegidas pero apagadas/desaparecidas (se reintentan cada minuto)

    def locate(self):
        members = topology(self.hint or [x for x in [self.ip] + self.coords if x])
        uuid_ip = {}
        for (u, i, n, c) in members:
            uuid_ip[u] = i
        chosen, missing = [], []
        self.vols = {}
        for want in self.rooms:
            key, label = entry_key(want)
            found = False
            for mm in members:
                if (mm[0] == key) if key.startswith("RINCON_") else (mm[2].lower() == key.lower()):
                    found = True
                    if mm not in chosen:
                        chosen.append(mm)
            if not found:
                missing.append(label)
        if len(chosen) > 1:
            # con varias, una apagada no debe dejar sin control a las demás
            ok = []
            for m in chosen:
                try:
                    self.vols[m[1]] = _vol(m[1])
                    ok.append(m)
                except Exception:
                    missing.append(m[2])
            chosen = ok
        self.missing = missing
        if not chosen:
            names = []
            for (_, _, n, _) in members:
                if n not in names:
                    names.append(n)
            raise SonosError("No hay '%s'. Hay: %s" % ("', '".join(missing), ", ".join(sorted(names))))
        self.names = []
        for m in chosen:
            if m[2] not in self.names:
                self.names.append(m[2])
        self.room = "+".join(self.names)
        self.all_ips = [m[1] for m in chosen]
        # las que tienen volumen fijo no se pueden subir ni bajar (sí play/pausa)
        if not hasattr(self, "_fixed"):
            self._fixed = {}
        for m in chosen:
            if m[0] not in self._fixed:
                self._fixed[m[0]] = fixed_output(m[1])
        vol_chosen = [m for m in chosen if not self._fixed.get(m[0])]
        if not vol_chosen:
            raise SonosError("Volumen fijo en %s" % self.room)
        self.ips = [m[1] for m in vol_chosen]
        self.vols = dict((ip, v) for ip, v in self.vols.items() if ip in self.ips)
        self.coords = []
        for m in chosen:
            cip = uuid_ip.get(m[3], m[1])
            if cip not in self.coords:
                self.coords.append(cip)
        self.group = None
        if len(chosen) > 1 and len(self.coords) == 1 and len(vol_chosen) == len(chosen):
            c = chosen[0][3]
            in_group = sorted(u for (u, _, _, cc) in members if cc == c)
            if in_group == sorted(m[0] for m in chosen):
                self.group = self.coords[0]
        self.hint = list(set(self.all_ips + self.coords))
        self.ip, self.coord = self.ips[0], self.coords[0]
        return self.ip

    # ---- volumen
    def get_volume(self):
        if self.group:
            return int(tag(soap(self.group, GRC, "GetGroupVolume", "<InstanceID>0</InstanceID>"), "CurrentVolume") or 0)
        for ip in self.ips:
            self.vols[ip] = _vol(ip)
        return sum(self.vols.values()) // len(self.vols)

    def nudge(self, delta, top):
        """Sube/baja 'delta' respetando el tope. Devuelve el volumen a mostrar."""
        if self.group:
            cur = self.get_volume()
            target = _clamp(cur, delta, top)
            if target == cur:
                return cur
            r = soap(self.group, GRC, "SetRelativeGroupVolume",
                     "<InstanceID>0</InstanceID><Adjustment>%d</Adjustment>" % (target - cur))
            return int(tag(r, "NewVolume") or target)
        for ip in self.ips:
            cur = self.vols.get(ip)
            if cur is None:
                cur = _vol(ip)
            target = _clamp(cur, delta, top)
            if target != cur:
                adj = target - cur
                new = _rel_vol(ip, adj)
                # si el volumen guardado estaba desfasado (lo cambiaron desde la app), corregir
                want = _clamp(new - adj, delta, top)
                if want != new:
                    _set_vol(ip, want)
                    new = want
                cur = new
            self.vols[ip] = cur
        return sum(self.vols.values()) // len(self.vols)

    def change_volume(self, delta):
        return self.nudge(delta, 100)

    def set_volume(self, v):
        if self.group:
            soap(self.group, GRC, "SetGroupVolume", "<InstanceID>0</InstanceID><DesiredVolume>%d</DesiredVolume>" % v)
        else:
            for ip in self.ips:
                _set_vol(ip, v)
                self.vols[ip] = v
        return v

    def get_mute(self):
        if self.group:
            return tag(soap(self.group, GRC, "GetGroupMute", "<InstanceID>0</InstanceID>"), "CurrentMute") == "1"
        for ip in self.ips:
            if not _mute(ip):
                return False
        return True

    def set_mute(self, m):
        if self.group:
            soap(self.group, GRC, "SetGroupMute", "<InstanceID>0</InstanceID><DesiredMute>%d</DesiredMute>" % (1 if m else 0))
        else:
            for ip in self.ips:
                _set_mute(ip, m)

    # ---- reproducción (sobre los coordinadores de los grupos implicados)
    def get_state(self):
        states = [tag(soap(c, AVT, "GetTransportInfo", "<InstanceID>0</InstanceID>"), "CurrentTransportState")
                  for c in self.coords]
        for st in ("PLAYING", "TRANSITIONING"):
            if st in states:
                return st
        return states[0] if states and states[0] else "STOPPED"

    def _all(self, action, args):
        ok, err = 0, None
        for c in self.coords:
            try:
                soap(c, AVT, action, args)
                ok += 1
            except Exception as e:
                err = e
        if not ok and err:
            raise err

    def play(self):
        self._all("Play", "<InstanceID>0</InstanceID><Speed>1</Speed>")

    def pause(self):
        self._all("Pause", "<InstanceID>0</InstanceID>")

    def get_title(self):
        c = self.coord
        r = soap(c, AVT, "GetPositionInfo", "<InstanceID>0</InstanceID>")
        meta = unescape(tag(r, "TrackMetaData"))
        stream = unescape(tag(meta, "r:streamContent"))
        title = unescape(tag(meta, "dc:title"))
        artist = unescape(tag(meta, "dc:creator"))
        if stream and not stream.startswith("ZPSTR_"):
            return stream
        if _starts(title, ("x-sonos", "x-rincon", "http", "ZPSTR_")):
            title = ""
        if not title:
            m = unescape(tag(soap(c, AVT, "GetMediaInfo", "<InstanceID>0</InstanceID>"), "CurrentURIMetaData"))
            title = unescape(tag(m, "dc:title"))
            artist = ""
        if artist and title:
            return artist + " - " + title
        return title


Sonos = Rooms     # compatibilidad con el nombre anterior
