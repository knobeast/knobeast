# ui.py — dibuja la pantalla (128x64) a partir del estado.
import framebuf
from i18n import t

_FOLD = {"á": "a", "à": "a", "â": "a", "ä": "a", "ã": "a", "é": "e", "è": "e", "ê": "e", "ë": "e",
         "í": "i", "ì": "i", "î": "i", "ï": "i", "ó": "o", "ò": "o", "ô": "o", "ö": "o", "õ": "o",
         "ú": "u", "ù": "u", "û": "u", "ü": "u", "ñ": "n", "ç": "c", "Á": "A", "À": "A", "Â": "A",
         "Ä": "A", "É": "E", "È": "E", "Ê": "E", "Í": "I", "Ó": "O", "Ö": "O", "Ú": "U", "Ü": "U",
         "Ñ": "N", "Ç": "C", "¿": "", "¡": "", "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-",
         "—": "-", "…": "...", "·": "-", "ß": "ss", "Ã": "A", "Õ": "O", "Ô": "O", "Û": "U", "Î": "I",
         "Ë": "E", "Ï": "I", "Ù": "U", "Ò": "O", "Ì": "I", "œ": "oe", "Œ": "OE", "«": '"', "»": '"',
         "„": '"', "\u00a0": " "}


def fold(s):
    """La fuente de la pantalla solo tiene ASCII: quita acentos."""
    out = []
    for ch in s:
        if ord(ch) < 128:
            out.append(ch)
        else:
            out.append(_FOLD.get(ch, "?"))
    return "".join(out)


def big_text(fb, s, x, y, scale):
    w = 8 * len(s)
    raw = bytearray(w)
    tmp = framebuf.FrameBuffer(raw, w, 8, framebuf.MONO_VLSB)
    tmp.text(s, 0, 0, 1)
    for i in range(w):
        col = raw[i]
        if col:
            for j in range(8):
                if col & (1 << j):
                    fb.fill_rect(x + i * scale, y + j * scale, scale, scale, 1)
    return w * scale


def _play(fb, x, y):
    for i in range(5):
        fb.vline(x + i, y + i, 9 - 2 * i, 1)


def _pause(fb, x, y):
    fb.fill_rect(x, y, 2, 9, 1)
    fb.fill_rect(x + 4, y, 2, 9, 1)


def _speaker_off(fb, x, y):
    fb.fill_rect(x, y + 4, 4, 6, 1)
    for i in range(5):
        fb.vline(x + 4 + i, y + 4 - i, 6 + 2 * i, 1)
    fb.line(x + 12, y + 3, x + 19, y + 10, 1)
    fb.line(x + 19, y + 3, x + 12, y + 10, 1)
    fb.line(x + 13, y + 3, x + 20, y + 10, 1)
    fb.line(x + 20, y + 3, x + 13, y + 10, 1)


_BOLT = ("0011", "0110", "1111", "0110", "1100", "1000")    # rayo de "cargando" (4x6)


def _battery(fb, right, y, pct, charging=None):
    """Icono de pila (13x8) pegado al borde derecho y el % a su izquierda.
    Enchufado: pila llena con un rayo. Devuelve el ancho ocupado."""
    x = right - 13
    fb.rect(x, y, 12, 8, 1)
    fb.fill_rect(x + 12, y + 2, 1, 4, 1)
    if charging:
        fb.fill_rect(x + 1, y + 1, 10, 6, 1)
        for r, row in enumerate(_BOLT):
            for c, b in enumerate(row):
                if b == "1":
                    fb.pixel(x + 4 + c, y + 1 + r, 0)
    elif pct is not None:
        w = 10 * pct // 100
        if w > 0:
            fb.fill_rect(x + 1, y + 1, w, 6, 1)
    txt = "%d%%" % pct if pct is not None and not charging else ""   # cargando, el % engaña (sube)
    if txt:
        fb.text(txt, x - 2 - 8 * len(txt), y, 1)
    return 13 + (2 + 8 * len(txt) if txt else 0)


def render(fb, st, now_ms, shift=0):
    fb.fill(0)
    room = fold(st.get("room") or "Sonos").upper()
    batt = st.get("battery")
    chg = st.get("charging")
    used = 0
    if batt is not None or chg is not None:
        used = _battery(fb, 127, 0, batt, chg)
    fb.text(room[:(128 - used - 2) // 8 if used else 16], shift, 0, 1)
    fb.hline(0, 10, 128, 1)

    mode = st.get("mode")
    if mode != "ok":
        msg = {"wifi": (t("connecting1"), t("connecting2")),
               "search": (t("searching1"), (room[:12] + "...")),
               "error": (t("noconn1"), t("noconn2"))}.get(mode, ("", ""))
        m0 = fold(msg[0])
        if len(m0) <= 8:
            big_text(fb, m0, shift, 18, 2)
        else:
            fb.text(m0[:16], shift, 22, 1)
        fb.text(fold(msg[1])[:16], shift, 42, 1)
        detail = fold(st.get("detail") or "")
        if detail:
            fb.text(detail[:16], shift, 54, 1)
        return

    vol = st.get("volume")
    if st.get("mute"):
        _speaker_off(fb, 2 + shift, 20)
        big_text(fb, fold(t("mute"))[:5], 34 + shift, 18, 2)
        if vol is not None:
            fb.text(fold(t("vol", vol)), 34 + shift, 38, 1)
    elif vol is not None:
        w = big_text(fb, str(vol), shift, 16, 3)
        x0 = max(56, w + 6) + shift
        fb.rect(x0, 22, 127 - x0, 12, 1)
        fill = (125 - x0) * vol // 100
        if fill > 0:
            fb.fill_rect(x0 + 1, 23, fill, 10, 1)

    # pie: estado + título con desplazamiento
    y = 54
    title = fold(st.get("title") or "")
    playing = st.get("state") == "PLAYING"
    if not title and not playing:
        title = fold(t("paused"))
    tw = 8 * len(title)
    avail = 118
    if tw > avail:
        gap = 32
        off = (now_ms // 45) % (tw + gap)
        fb.text(title, 10 - off, y, 1)
        fb.text(title, 10 - off + tw + gap, y, 1)
    else:
        fb.text(title, 10, y, 1)
    fb.fill_rect(0, y - 1, 10, 10, 0)
    if playing:
        _play(fb, 0, y - 1)
    elif st.get("state") == "TRANSITIONING":
        fb.text(".", 0, y, 1)
    else:
        _pause(fb, 0, y - 1)


MENU_ROWS = 5


def render_menu(fb, sel, title, labels, mark=None):
    """Lista de opciones con la elegida resaltada. mark: índice a marcar con '*' (p. ej. idioma actual)."""
    fb.fill(0)
    fb.text(fold(title)[:16], 0, 0, 1)
    fb.hline(0, 10, 128, 1)
    top = 0 if sel < MENU_ROWS else sel - MENU_ROWS + 1
    for row in range(MENU_ROWS):
        i = top + row
        if i >= len(labels):
            break
        y = 14 + row * 10
        txt = ("*" if i == mark else (">" if i == sel else " ")) + fold(labels[i])[:15]
        if i == sel:
            fb.fill_rect(0, y - 1, 128, 10, 1)
            fb.text(txt, 0, y, 0)
        else:
            fb.text(txt, 0, y, 1)


ROWS = 4          # filas visibles en la lista de altavoces


def render_rooms(fb, items, sel, top, msg=""):
    """Lista de habitaciones con casillas. items: (tipo, nombre, marcada, grupo)
    tipo 'room' | 'save' | 'cancel'; grupo: 0 = sola, 1, 2... = agrupada en Sonos, -1 = no aparece."""
    fb.fill(0)
    fb.text(fold(t("rooms_title"))[:14], 0, 0, 1)
    n = 0
    for it in items:
        if it[0] == "room" and it[2]:
            n += 1
    c = "%d" % n
    fb.text(c, 128 - 8 * len(c), 0, 1)
    fb.hline(0, 10, 128, 1)
    if msg:
        fb.fill_rect(0, 24, 128, 18, 0)
        fb.rect(0, 24, 128, 18, 1)
        m = fold(msg)[:15]
        fb.text(m, (128 - 8 * len(m)) // 2, 29, 1)
        return
    for row in range(ROWS):
        i = top + row
        if i >= len(items):
            break
        kind, name, checked, grp = items[i][:4]
        y = 13 + row * 12
        on = i == sel
        if on:
            fb.fill_rect(0, y, 128, 12, 1)
        col = 0 if on else 1
        if kind == "room":
            fb.rect(2, y + 2, 8, 8, col)
            if checked:
                fb.fill_rect(4, y + 4, 4, 4, col)
            fb.text(fold(name)[:11 if grp else 14], 14, y + 2, col)
            if grp:
                g = "?" if grp < 0 else "G%d" % grp
                fb.text(g, 128 - 8 * len(g), y + 2, col)
        else:
            fb.text(fold(t("save") if kind == "save" else t("cancel"))[:14], 14, y + 2, col)
    # barra de desplazamiento si no cabe todo
    if len(items) > ROWS:
        h = max(4, 48 * ROWS // len(items))
        y0 = 13 + (48 - h) * top // (len(items) - ROWS)
        fb.vline(0, 13, 48, 0)
        fb.vline(0, y0, h, 1)


def render_splash(fb, title, version, stage, pct):
    """Pantalla de arranque: nombre grande, versión, qué está haciendo y barra de progreso."""
    fb.fill(0)
    title = fold(title)
    scale = 2 if len(title) * 16 <= 128 else 1
    w = len(title) * 8 * scale
    if scale == 2:
        big_text(fb, title, (128 - w) // 2, 6, 2)
    else:
        fb.text(title[:16], (128 - w) // 2, 10, 1)
    v = fold(version)[:16]
    fb.text(v, (128 - 8 * len(v)) // 2, 26, 1)
    st = fold(stage)[:16]
    fb.text(st, (128 - 8 * len(st)) // 2, 40, 1)
    fb.rect(8, 53, 112, 8, 1)
    fill = 108 * max(0, min(100, pct)) // 100
    if fill > 0:
        fb.fill_rect(10, 55, fill, 4, 1)


def render_info(fb, title, line1, line2=""):
    fb.fill(0)
    fb.text(fold(title)[:16], 0, 0, 1)
    fb.hline(0, 10, 128, 1)
    fb.text(fold(line1)[:16], 0, 26, 1)
    fb.text(fold(line2)[:16], 0, 40, 1)


def render_hold(fb, ms, total):
    """Barra de 'mantén pulsado' encima de lo que haya en pantalla."""
    fb.fill_rect(6, 16, 116, 34, 0)
    fb.rect(6, 16, 116, 34, 1)
    h = fold(t("hold"))
    fb.text(h, 64 - 4 * len(h), 21, 1)
    fb.rect(14, 34, 100, 10, 1)
    w = 98 * min(ms, total) // total
    if w > 0:
        fb.fill_rect(15, 35, w, 8, 1)


def render_setup(fb, ap_name, ap_pass, status, page=0, qrm=None):
    """Pantalla del modo configuración. Página 0: red y clave en texto. Página 1: código QR."""
    fb.fill(0)
    if page == 1 and qrm:
        n = len(qrm) + 2
        scale = 2 if n * 2 <= 64 else 1
        import qr
        qr.draw(fb, qrm, 0, (64 - n * scale) // 2, scale)
        x = n * scale + 4
        for i, k in enumerate(("setup_qr1", "setup_qr2", "setup_qr3")):
            fb.text(fold(t(k))[:(128 - x) // 8], x, 14 + i * 12, 1)
        return
    fb.text(fold(t("setup_title"))[:16], 0, 0, 1)
    fb.hline(0, 10, 128, 1)
    fb.text(fold(t("setup_join"))[:16], 0, 13, 1)
    fb.text(fold(ap_name)[:16], 0, 22, 1)
    fb.text(fold(t("setup_pass"))[:16], 0, 33, 1)
    fb.text(ap_pass[:16], 0, 42, 1)
    fb.text(fold(status)[:16], 0, 55, 1)
