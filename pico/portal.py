# portal.py — modo configuración: la Pico crea su propia wifi y sirve una página
# (con DNS "cautivo" para que el móvil la abra solo) donde se elige la red de casa.
import socket
import select
from time import ticks_ms, ticks_diff, sleep_ms
import settings
import ui
import updater
import device
import i18n
from i18n import t

PAGE_CSS = ("body{font-family:-apple-system,Helvetica,sans-serif;margin:0;padding:24px;background:#111;color:#eee}"
            "h1{font-size:22px;margin:0 0 4px}p{color:#aaa;margin:0 0 20px}"
            "label{display:block;margin:16px 0 6px;font-weight:600}"
            "input,select{width:100%;box-sizing:border-box;font-size:17px;padding:12px;border-radius:10px;"
            "border:1px solid #444;background:#222;color:#eee}"
            "button{margin-top:24px;width:100%;font-size:18px;padding:14px;border:0;border-radius:12px;"
            "background:#e8b04a;color:#111;font-weight:700}small{color:#888}"
            "h2{font-size:18px;margin:40px 0 4px;padding-top:24px;border-top:1px solid #333}"
            ".warn{background:#4a2a10;color:#fc9;padding:12px;border-radius:10px}"
            ".langs{text-align:right;margin:0 0 8px;font-size:15px}"
            "input[type=file]{padding:10px}.b2{background:#444;color:#eee}")


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _unquote(s):
    s = s.replace("+", " ")
    out = bytearray()
    i = 0
    b = s.encode()
    while i < len(b):
        c = b[i]
        if c == 37 and i + 2 < len(b):      # '%'
            try:
                out.append(int(b[i + 1:i + 3], 16))
                i += 3
                continue
            except ValueError:
                pass
        out.append(c)
        i += 1
    return out.decode()


def parse_form(body):
    d = {}
    for part in body.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            d[_unquote(k)] = _unquote(v)
    return d


def _head(title=""):
    return ("<!doctype html><html lang='%s'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>%s</title><style>%s</style></head><body>" % (i18n.CODE, _esc(title), PAGE_CSS))


def lang_links():
    out = []
    for code, name in i18n.LANGS:
        if code == i18n.CODE:
            out.append("<b>%s</b>" % code.upper())
        else:
            out.append("<a href='/?lang=%s' title='%s' style='color:#e8b04a'>%s</a>" % (code, _esc(name), code.upper()))
    return "<p class='langs'>%s</p>" % " · ".join(out)


def update_section():
    v, pending, rolled = updater.status()
    warn = ""
    if rolled:
        warn = "<p class='warn'>%s<br><small>%s</small></p>" % (t("p_upd_rolled"), _esc(rolled))
    elif pending:
        warn = "<p class='warn'>%s</p>" % t("p_upd_pending")
    return ("<h2>%s</h2><p>%s <b>%s</b></p>%s"
            "<form method='post' action='/actualizar' enctype='multipart/form-data'>"
            "<label>%s <small>%s</small></label>"
            "<input type='file' name='f' multiple>"
            "<button type='submit' class='b2'>%s</button></form>"
            "<p style='margin-top:12px'><small>%s</small></p>"
            % (t("p_upd_title"), t("p_upd_ver"), _esc(v), warn, t("p_upd_files"), t("p_upd_files_small"),
               t("p_upd_btn"), t("p_upd_note")))


def _secs(v):
    return t("never") if v <= 0 else ("%d s" % v if v < 60 else "%d min" % (v // 60))


def _select(name, current, options):
    o = "".join("<option value='%d'%s>%s</option>" % (v, " selected" if v == current else "", _secs(v))
                for v in options)
    return "<select name='%s'>%s</select>" % (name, o)


def screen_fields(cfg):
    dim, off = getattr(cfg, "SCREEN_DIM", 15), getattr(cfg, "SCREEN_OFF", 0)
    step = getattr(cfg, "VOL_STEP", 1)
    steps = "".join("<option value='%d'%s>%d</option>" % (v, " selected" if v == step else "", v)
                    for v in (1, 2, 3, 5))
    return ("<label>%s</label><select name='step'>%s</select>"
            "<h2 style='margin-top:28px;padding-top:16px'>%s</h2>"
            "<label>%s</label>%s<label>%s</label>%s"
            % (t("p_step"), steps, t("p_screen"), t("p_dim"), _select("dim", dim, (15, 30, 60, 300, 0)),
               t("p_off"), _select("off", off, (0, 30, 60, 300, 900))))


def form_page(cfg, networks):
    cur = cfg.WIFI_SSID or ""
    opts = []
    names = [n for n, _ in networks]
    if cur and cur not in names:
        names.insert(0, cur)
    for n in names:
        sel = " selected" if n == cur else ""
        opts.append('<option value="%s"%s>%s</option>' % (_esc(n), sel, _esc(n)))
    name = device.ap_name(cfg)
    return (_head(name) + lang_links() +
            "<h1>%s</h1><p>%s</p>"
            "<form method='post' action='/guardar'>"
            "<label>%s</label><select name='ssid_sel'>%s</select>"
            "<label>%s <small>%s</small></label>"
            "<input name='ssid_txt' autocapitalize='off' autocorrect='off'>"
            "<label>%s</label><input name='pass' type='password' autocomplete='off'>"
            "<small>%s</small>"
            "<label>%s</label><input name='maxvol' type='number' min='5' max='100' value='%d'>"
            "%s"
            "<button type='submit'>%s</button></form>"
            "<p style='margin-top:24px'><small>%s<br>%s</small></p>%s</body></html>"
            % (_esc(name), t("p_sub"), t("p_wifi"), "".join(opts), t("p_or"), t("p_or_small"),
               t("p_pass"), t("p_keep") if cur else "", t("p_maxvol"), int(cfg.MAX_VOLUME), screen_fields(cfg),
               t("p_save"),
               t("p_rooms", _esc(", ".join(cfg.ROOMS))), t("p_rooms_how", t("m_rooms")), update_section()))


def done_page(ssid):
    return (_head() + "<h1>%s</h1><p>%s</p></body></html>" % (t("p_done_title"), t("p_done", _esc(ssid))))


def message_page(title, text, back=True):
    return (_head() + "<h1>%s</h1><p>%s</p>%s</body></html>"
            % (title, text, "<p><a href='/' style='color:#e8b04a'>%s</a></p>" % t("p_back") if back else ""))


def handle_form(cfg, form, networks=()):
    # Ojo: los espacios del principio o del final SON parte del nombre de una wifi ("CasaIndiana ").
    # El de la lista se guarda tal cual; el escrito a mano se ajusta al de la lista si solo cambian espacios.
    txt = form.get("ssid_txt") or ""
    ssid = txt if txt.strip() else (form.get("ssid_sel") or "")
    if not ssid.strip():
        return None
    names = [n for n, _ in networks]
    if ssid not in names:
        ssid = next((n for n in names if n.strip() == ssid.strip()), ssid.strip())
    new = {"WIFI_SSID": ssid}
    pw = form.get("pass") or ""
    if pw or ssid != cfg.WIFI_SSID:
        new["WIFI_PASS"] = pw
    try:
        v = int(form.get("maxvol") or cfg.MAX_VOLUME)
        new["MAX_VOLUME"] = max(5, min(100, v))
    except ValueError:
        pass
    try:
        if form.get("step"):
            new["VOL_STEP"] = max(1, min(10, int(form["step"])))
    except ValueError:
        pass
    for field, key in (("dim", "SCREEN_DIM"), ("off", "SCREEN_OFF")):
        try:
            if form.get(field) is not None:
                new[key] = max(0, min(3600, int(form[field])))
        except ValueError:
            pass
    settings.save(new)
    return ssid


def dns_reply(data, ip):
    if len(data) < 17:
        return None
    i = 12
    while i < len(data) and data[i] != 0:
        i += data[i] + 1
    q = data[12:i + 5]
    return (data[:2] + b"\x81\x80" + data[4:6] + data[4:6] + b"\x00\x00\x00\x00" + q +
            b"\xc0\x0c\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04" + bytes([int(x) for x in ip.split(".")]))


def _read_head(cl):
    """Lee la cabecera HTTP. Devuelve (método, ruta, cabeceras en minúsculas, cuerpo ya leído)."""
    cl.settimeout(5)
    data = b""
    while b"\r\n\r\n" not in data and len(data) < 4096:
        chunk = cl.recv(512)
        if not chunk:
            break
        data += chunk
    head, _, body = data.partition(b"\r\n\r\n")
    lines = head.decode().split("\r\n")
    method, path = (lines[0].split(" ") + ["", ""])[:2]
    hdrs = {}
    for ln in lines[1:]:
        if ":" in ln:
            k, v = ln.split(":", 1)
            hdrs[k.strip().lower()] = v.strip()
    return method, path, hdrs, body


def _read_body(cl, hdrs, body):
    length = int(hdrs.get("content-length") or 0)
    while len(body) < length:
        chunk = cl.recv(512)
        if not chunk:
            break
        body += chunk
    return body.decode()


def handle_upload(cl, hdrs, body):
    """Devuelve (ok, html)."""
    ctype = hdrs.get("content-type", "")
    i = ctype.find("boundary=")
    if i < 0:
        return False, message_page(t("p_err"), t("p_nofile"))
    boundary = ctype[i + 9:].split(";")[0].strip().strip('"')
    try:
        saved, skipped = updater.receive(body, cl.recv, int(hdrs.get("content-length") or 0), boundary)
        if not saved:
            return False, message_page(t("p_nothing_t"), t("p_nothing") +
                                       (" " + t("p_ignored", _esc(", ".join(skipped))) if skipped else ""))
        updater.check(saved)
        updater.apply(saved)
    except Exception as e:
        return False, message_page(t("p_notinst_t"), "%s<br>%s" % (_esc(e), t("p_unchanged")))
    txt = t("p_installed", "<b>%s</b>" % _esc(", ".join(saved)))
    if skipped:
        txt += "<br><small>%s</small>" % t("p_ignored", _esc(", ".join(skipped)))
    txt += "<br><br>" + t("p_inst_note")
    return True, message_page(t("p_updated_t"), txt, back=False)


def _send(cl, code, html):
    b = html.encode()
    cl.send(("HTTP/1.0 %s\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: %d\r\n"
             "Cache-Control: no-store\r\nConnection: close\r\n\r\n" % (code, len(b))).encode())
    i = 0
    while i < len(b):
        i += cl.send(b[i:i + 1024])


def scan(sta):
    best = {}
    try:
        sta.active(True)
        for n in sta.scan():
            name = n[0].decode() if isinstance(n[0], bytes) else n[0]
            if name and (name not in best or n[3] > best[name]):
                best[name] = n[3]
    except Exception as e:
        print("scan:", e)
    return sorted(best.items(), key=lambda x: -x[1])


def start_ap(ap, name, password):
    """Red de configuración con WPA2 y la contraseña propia de este mando."""
    try:
        ap.config(essid=name, password=password)
    except Exception:
        ap.config(ssid=name, key=password)
    ap.active(True)
    for _ in range(50):
        if ap.active():
            break
        sleep_ms(100)
    return ap.ifconfig()[0]


def run(cfg, disp, inputs, sta, ap, reset, http_port=80, dns_port=53, log=print):
    name = device.ap_name(cfg)
    password = device.info()["ap_pass"]
    state = {"status": "", "page": 0, "t": ticks_ms(), "qr": None}

    def show(status=None, page=None):
        if status is not None:
            state["status"] = status
            state["page"] = 0
            state["t"] = ticks_ms()
        if page is not None:
            state["page"] = page
            state["t"] = ticks_ms()
        ui.render_setup(disp.fb, name, password, state["status"], state["page"], state["qr"])
        disp.power(True)
        disp.contrast(255)
        disp.show()

    ip = "192.168.4.1"
    show(t("st_scanning"))
    networks = scan(sta)
    log("Redes: %s" % [n for n, _ in networks])
    try:
        sta.disconnect()
    except Exception:
        pass
    try:
        sta.active(False)
    except Exception:
        pass
    ip = start_ap(ap, name, password)
    log("Punto de acceso %s (WPA2) en %s" % (name, ip))
    try:
        import qr
        state["qr"] = qr.encode(qr.wifi_text(name, password))
    except Exception as e:
        log("qr: %r" % (e,))
    show(t("st_waiting"))

    dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dns.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    dns.bind(socket.getaddrinfo("0.0.0.0", dns_port)[0][-1])
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(socket.getaddrinfo("0.0.0.0", http_port)[0][-1])
    srv.listen(3)
    poller = select.poll()
    poller.register(dns, select.POLLIN)
    poller.register(srv, select.POLLIN)
    t0 = ticks_ms()
    try:
        while True:
            steps = inputs.encoder_steps() if hasattr(inputs, "encoder_steps") else 0
            if (steps or ticks_diff(ticks_ms(), state["t"]) > 5000) and state["qr"]:
                show(page=1 - state["page"])          # alterna texto / código QR
            for ev in inputs.events():
                if ev == "enc_short":
                    log("Configuracion cancelada")
                    show(t("st_cancel"))
                    sleep_ms(800)
                    reset()
                    return
            if ticks_diff(ticks_ms(), t0) > cfg.SETUP_TIMEOUT * 1000:
                log("Configuracion: tiempo agotado")
                reset()
                return
            for obj, _ in poller.poll(100):
                if obj is dns:
                    try:
                        data, addr = dns.recvfrom(512)
                        r = dns_reply(data, ip)
                        if r:
                            dns.sendto(r, addr)
                    except Exception as e:
                        log("dns: %r" % (e,))
                elif obj is srv:
                    cl, _ = srv.accept()
                    try:
                        method, path, hdrs, body = _read_head(cl)
                        if path.startswith("/favicon"):
                            _send(cl, "404 Not Found", "")
                        elif method == "POST" and path.startswith("/actualizar"):
                            show(t("st_recv"))
                            ok, page = handle_upload(cl, hdrs, body)
                            _send(cl, "200 OK", page)
                            if ok:
                                cl.close()
                                log("Actualizado")
                                show(t("st_updated"))
                                sleep_ms(1500)
                                reset()
                                return
                            show(t("st_phone"))
                        elif method == "POST" and path.startswith("/guardar"):
                            ssid = handle_form(cfg, parse_form(_read_body(cl, hdrs, body)), networks)
                            if ssid:
                                _send(cl, "200 OK", done_page(ssid))
                                cl.close()
                                log("Guardado: %s" % ssid)
                                show(t("st_saved"))
                                sleep_ms(1500)
                                reset()
                                return
                            _send(cl, "200 OK", form_page(cfg, networks))
                        else:
                            i = path.find("lang=")
                            if i >= 0:
                                code = path[i + 5:i + 7]
                                if code in [c for c, _ in i18n.LANGS]:
                                    i18n.set_lang(code)
                                    cfg.LANG = code
                                    settings.save({"LANG": code})
                            show(t("st_phone"))
                            _send(cl, "200 OK", form_page(cfg, networks))
                    except Exception as e:
                        log("http: %r" % (e,))
                    finally:
                        try:
                            cl.close()
                        except Exception:
                            pass
    finally:
        dns.close()
        srv.close()
