# qr.py — generador de códigos QR pequeño (modo byte, corrección L, versiones 1 a 5).
# Basta para el QR de la wifi de configuración ("WIFI:T:WPA;S:...;P:...;;").
# Devuelve una lista de filas; cada fila es una lista de 0/1 (1 = módulo negro).

_EC = {1: (19, 7), 2: (34, 10), 3: (55, 15), 4: (80, 20), 5: (108, 26)}   # (datos, corrección)
_ALIGN = {1: (), 2: (6, 18), 3: (6, 22), 4: (6, 26), 5: (6, 30)}

# ---------------------------------------------------------------- Reed-Solomon en GF(256)
_EXP = [0] * 512
_LOG = [0] * 256
_x = 1
for _i in range(255):
    _EXP[_i] = _x
    _LOG[_x] = _i
    _x <<= 1
    if _x & 0x100:
        _x ^= 0x11D
for _i in range(255, 512):
    _EXP[_i] = _EXP[_i - 255]


def _gmul(a, b):
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _rs(data, n):
    gen = [1]
    for i in range(n):
        nxt = [0] * (len(gen) + 1)
        for j, g in enumerate(gen):
            nxt[j] ^= g
            nxt[j + 1] ^= _gmul(g, _EXP[i])
        gen = nxt
    rem = [0] * n
    for byte in data:
        f = byte ^ rem[0]
        rem = rem[1:] + [0]
        for j in range(n):
            rem[j] ^= _gmul(gen[j + 1], f)
    return rem


# ---------------------------------------------------------------- matriz
def _format_bits(mask):
    data = (0b01 << 3) | mask              # nivel L = 01
    rem = data
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * 0x537)
    return ((data << 10) | rem) ^ 0x5412


def _mask_fn(m, r, c):
    if m == 0:
        return (r + c) % 2 == 0
    if m == 1:
        return r % 2 == 0
    if m == 2:
        return c % 3 == 0
    if m == 3:
        return (r + c) % 3 == 0
    if m == 4:
        return (r // 2 + c // 3) % 2 == 0
    if m == 5:
        return (r * c) % 2 + (r * c) % 3 == 0
    if m == 6:
        return ((r * c) % 2 + (r * c) % 3) % 2 == 0
    return ((r + c) % 2 + (r * c) % 3) % 2 == 0


def _base(ver):
    n = 17 + 4 * ver
    m = [[0] * n for _ in range(n)]
    fixed = [[False] * n for _ in range(n)]

    def put(r, c, v):
        if 0 <= r < n and 0 <= c < n:
            m[r][c] = v
            fixed[r][c] = True

    for (r0, c0) in ((0, 0), (0, n - 7), (n - 7, 0)):        # buscadores + separadores
        for r in range(-1, 8):
            for c in range(-1, 8):
                inside = 0 <= r <= 6 and 0 <= c <= 6
                v = inside and (r in (0, 6) or c in (0, 6) or (2 <= r <= 4 and 2 <= c <= 4))
                put(r0 + r, c0 + c, 1 if v else 0)
    for i in range(8, n - 8):                                 # patrones de tiempo
        put(6, i, 1 if i % 2 == 0 else 0)
        put(i, 6, 1 if i % 2 == 0 else 0)
    al = _ALIGN[ver]
    for r in al:                                              # alineación
        for c in al:
            if fixed[r][c]:
                continue
            for dr in range(-2, 3):
                for dc in range(-2, 3):
                    put(r + dr, c + dc, 1 if max(abs(dr), abs(dc)) != 1 else 0)
    put(n - 8, 8, 1)                                          # módulo oscuro
    for i in range(9):                                        # reservar zona de formato
        if not fixed[8][i]:
            fixed[8][i] = True
        if not fixed[i][8]:
            fixed[i][8] = True
    for i in range(8):
        fixed[8][n - 1 - i] = True
        fixed[n - 1 - i][8] = True
    return m, fixed


def _place(m, fixed, bits):
    n = len(m)
    i = 0
    up = True
    c = n - 1
    while c > 0:
        if c == 6:
            c -= 1
        rows = range(n - 1, -1, -1) if up else range(n)
        for r in rows:
            for cc in (c, c - 1):
                if not fixed[r][cc]:
                    m[r][cc] = bits[i] if i < len(bits) else 0
                    i += 1
        up = not up
        c -= 2


def _put_format(m, mask):
    n = len(m)
    f = _format_bits(mask)
    bits = [(f >> (14 - i)) & 1 for i in range(15)]
    pos1 = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8)]
    pos2 = [(n - 1, 8), (n - 2, 8), (n - 3, 8), (n - 4, 8), (n - 5, 8), (n - 6, 8), (n - 7, 8),
            (8, n - 8), (8, n - 7), (8, n - 6), (8, n - 5), (8, n - 4), (8, n - 3), (8, n - 2), (8, n - 1)]
    for b, (r, c) in zip(bits, pos1):
        m[r][c] = b
    for b, (r, c) in zip(bits, pos2):
        m[r][c] = b


def _penalty(m):
    n = len(m)
    p = 0
    for grid in (m, [list(col) for col in zip(*m)]):
        for row in grid:
            run, last = 0, -1
            for v in row:
                if v == last:
                    run += 1
                else:
                    if run >= 5:
                        p += run - 2
                    run, last = 1, v
            if run >= 5:
                p += run - 2
            s = "".join("1" if v else "0" for v in row)
            p += 40 * (s.count("10111010000") + s.count("00001011101"))
    for r in range(n - 1):
        for c in range(n - 1):
            v = m[r][c]
            if v == m[r][c + 1] == m[r + 1][c] == m[r + 1][c + 1]:
                p += 3
    dark = sum(sum(row) for row in m)
    p += 10 * (abs(dark * 20 - n * n * 10) // (n * n))
    return p


def encode(text):
    data = text.encode() if isinstance(text, str) else bytes(text)
    ver = None
    for v in range(1, 6):
        if len(data) + 2 <= _EC[v][0]:       # 4 bits modo + 8 bits longitud + datos
            ver = v
            break
    if ver is None:
        raise ValueError("texto demasiado largo para el QR")
    ndata, nec = _EC[ver]
    bits = [0, 1, 0, 0] + [(len(data) >> (7 - i)) & 1 for i in range(8)]
    for b in data:
        bits += [(b >> (7 - i)) & 1 for i in range(8)]
    bits += [0] * min(4, ndata * 8 - len(bits))
    bits += [0] * ((8 - len(bits) % 8) % 8)
    words = [int("".join(str(x) for x in bits[i:i + 8]), 2) for i in range(0, len(bits), 8)]
    pad = (0xEC, 0x11)
    i = 0
    while len(words) < ndata:
        words.append(pad[i % 2])
        i += 1
    words += _rs(words, nec)
    stream = []
    for w in words:
        stream += [(w >> (7 - i)) & 1 for i in range(8)]
    best, best_p = None, None
    for mask in range(8):
        m, fixed = _base(ver)
        _place(m, fixed, stream)
        n = len(m)
        for r in range(n):
            for c in range(n):
                if not fixed[r][c] and _mask_fn(mask, r, c):
                    m[r][c] ^= 1
        _put_format(m, mask)
        p = _penalty(m)
        if best_p is None or p < best_p:
            best, best_p = m, p
    return best


def wifi_text(ssid, password):
    def esc(s):
        out = ""
        for ch in s:
            if ch in '\\;,:"':
                out += "\\"
            out += ch
        return out
    return "WIFI:T:WPA;S:%s;P:%s;;" % (esc(ssid), esc(password))


def draw(fb, matrix, x, y, scale):
    """Dibuja en un framebuf: fondo encendido (blanco) y módulos negros, con margen de 1 módulo."""
    n = len(matrix)
    fb.fill_rect(x, y, (n + 2) * scale, (n + 2) * scale, 1)
    for r in range(n):
        row = matrix[r]
        for c in range(n):
            if row[c]:
                fb.fill_rect(x + (c + 1) * scale, y + (r + 1) * scale, scale, scale, 0)
