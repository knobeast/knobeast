# sh1106.py — controlador mínimo para pantallas OLED 1,3" SH1106 128x64 por I2C.
#
# Tolerante a fallos: si la pantalla no contesta (cable flojo, bajón de tensión al transmitir la
# wifi...) no rompe el programa. La vuelve a inicializar sola, y cada cierto tiempo le reenvía la
# configuración por si se ha reiniciado ella sola (entonces se queda en negro aunque responda).
import framebuf
from time import ticks_ms, ticks_diff

W, H = 128, 64


class SH1106:
    def __init__(self, i2c, addr=0x3C, rotate180=True):
        self.i2c, self.addr = i2c, addr
        self.buf = bytearray(W * H // 8)
        self.fb = framebuf.FrameBuffer(self.buf, W, H, framebuf.MONO_VLSB)
        self._line = bytearray(W + 1)
        self._line[0] = 0x40
        self.rotate180 = rotate180
        self.on = True
        self._c = None
        self.errors = 0
        self._last_init = ticks_ms()
        self.ok = self.init()

    def init(self, full=True):
        """Envía toda la configuración y enciende. Devuelve False si la pantalla no contesta.
        full=False: sin apagarla antes (para el repaso periódico, que así no parpadea)."""
        seg, com = (0xA0, 0xC0) if self.rotate180 else (0xA1, 0xC8)
        try:
            if full:
                self.cmd(0xAE)
            for c in (0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40, 0xAD, 0x8B, seg, com,
                      0xDA, 0x12, 0x81, self._c if self._c is not None else 0xCF,
                      0xD9, 0x22, 0xDB, 0x35, 0xA4, 0xA6):
                self.cmd(c)
            self.cmd(0xAF if self.on else 0xAE)
            self._last_init = ticks_ms()
            return True
        except OSError:
            self.errors += 1
            return False

    def cmd(self, c):
        self.i2c.writeto(self.addr, bytes((0x00, c)))

    def _fail(self):
        self.errors += 1
        self.ok = self.init()

    def show(self):
        # cada 20 s, repetir la configuración por si la pantalla se ha reiniciado sola
        if not self.ok or ticks_diff(ticks_ms(), self._last_init) > 20000:
            self.ok = self.init(full=not self.ok)
            if not self.ok:
                return
        try:
            for page in range(8):
                self.cmd(0xB0 | page)
                self.cmd(0x02)          # la RAM del SH1106 tiene 132 columnas: desplazamiento de 2
                self.cmd(0x10)
                self._line[1:] = self.buf[page * W:(page + 1) * W]
                self.i2c.writeto(self.addr, self._line)
        except OSError:
            self._fail()

    def contrast(self, v):
        """Brillo 0-255 (solo el contraste)."""
        if v != self._c:
            self._c = v
            try:
                self.cmd(0x81)
                self.cmd(v & 0xFF)
            except OSError:
                self._fail()

    def power(self, on):
        if on != self.on:
            self.on = on
            try:
                self.cmd(0xAF if on else 0xAE)
            except OSError:
                self._fail()
