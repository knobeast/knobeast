# knob.py — el mando: entradas, pantalla, wifi y bucle principal. Lo arranca main.py.
from machine import Pin, I2C, ADC, disable_irq, enable_irq, reset
from time import ticks_ms, ticks_diff, sleep_ms
import network
import config as cfg
import settings

settings.apply(cfg)            # lo guardado desde el móvil manda sobre config.py
import i18n
i18n.set_lang(getattr(cfg, "LANG", "es"))
from sh1106 import SH1106
from app import App

_TABLE = (0, -1, 1, 0, 1, 0, 0, -1, -1, 0, 0, 1, 0, 1, -1, 0)


class Inputs:
    """Encoder por interrupciones + su pulsador, con antirrebote y pulsación larga."""

    def __init__(self):
        if cfg.PIN_ENC_VCC is not None:
            Pin(cfg.PIN_ENC_VCC, Pin.OUT, value=1)
        self.a = Pin(cfg.PIN_ENC_CLK, Pin.IN, Pin.PULL_UP)
        self.b = Pin(cfg.PIN_ENC_DT, Pin.IN, Pin.PULL_UP)
        self._st = (self.a.value() << 1) | self.b.value()
        self._q = 0
        for p in (self.a, self.b):
            p.irq(self._irq, Pin.IRQ_RISING | Pin.IRQ_FALLING)
        self.buttons = [("enc", Pin(cfg.PIN_ENC_SW, Pin.IN, Pin.PULL_UP))]
        self._down = {}
        self._fired = {}

    def _irq(self, _):
        s = (self.a.value() << 1) | self.b.value()
        self._q += _TABLE[(self._st << 2) | s]
        self._st = s

    def encoder_steps(self):
        st = disable_irq()
        n = int(self._q / cfg.ENC_DIVIDER)
        if n:
            self._q -= n * cfg.ENC_DIVIDER
        enable_irq(st)
        return n

    def events(self):
        """enc_short al soltar; enc_long al llegar a LONG_MS; enc_menu al llegar a MENU_MS."""
        out = []
        now = ticks_ms()
        for name, pin in self.buttons:
            pressed = pin.value() == 0
            t0 = self._down.get(name)
            if pressed and t0 is None:
                self._down[name] = now
                self._fired[name] = 0
            elif pressed:
                held = ticks_diff(now, t0)
                if self._fired[name] < 1 and held >= cfg.LONG_MS:
                    self._fired[name] = 1
                    out.append(name + "_long")
                if self._fired[name] < 2 and held >= cfg.MENU_MS:
                    self._fired[name] = 2
                    out.append(name + "_menu")
            elif t0 is not None:
                if not self._fired[name] and ticks_diff(now, t0) >= 30:
                    out.append(name + "_short")
                self._down[name] = None
        return out

    def held(self, name):
        t0 = self._down.get(name)
        if t0 is None or self._fired.get(name) == 2:
            return 0
        return ticks_diff(ticks_ms(), t0)


class Battery:
    """Porcentaje aproximado de una LiPo a partir de su tensión (divisor en un pin ADC)."""
    CURVE = ((4.20, 100), (4.10, 90), (4.00, 80), (3.90, 66), (3.80, 50), (3.75, 40),
             (3.70, 30), (3.65, 20), (3.55, 10), (3.40, 4), (3.30, 0))

    def __init__(self, pin, ratio, charge_pin=None):
        self.adc = ADC(Pin(pin)) if pin is not None else None
        self.ratio = ratio
        # USB-C enchufado: divisor desde IN+ del cargador (5 V -> ~3,3 V) a un pin
        self.chg = Pin(charge_pin, Pin.IN) if charge_pin is not None else None

    def charging(self):
        """True = cargador enchufado, False = con batería, None = no se sabe (sin cable al pin)."""
        if self.chg is None:
            return None
        return self.chg.value() == 1

    def volts(self):
        total = 0
        for _ in range(16):
            total += self.adc.read_u16()
        return total / 16 * 3.3 / 65535 * self.ratio

    def read(self):
        if self.adc is None:
            return None
        v = self.volts()
        if v < 2.5:                     # sin divisor o mal conectado
            return None
        c = self.CURVE
        if v >= c[0][0]:
            return 100
        for (v1, p1), (v0, p0) in zip(c, c[1:]):
            if v >= v0:
                return int(p0 + (p1 - p0) * (v - v0) / (v1 - v0))
        return 0


class Net:
    def __init__(self):
        try:
            import rp2
            rp2.country(cfg.WIFI_COUNTRY)
        except Exception:
            pass
        try:
            network.hostname("sonos-knob")
        except Exception:
            pass
        self.w = network.WLAN(network.STA_IF)
        self.w.active(True)
        self._last = None

    def connected(self):
        return self.w.isconnected()

    def connect(self, c):
        """No bloquea: lanza la conexión y vuelve; se reintenta cada 15 s."""
        now = ticks_ms()
        if self._last is not None and ticks_diff(now, self._last) < 15000:
            return
        self._last = now
        print("Conectando a", c.WIFI_SSID)
        try:
            self.w.disconnect()
        except Exception:
            pass
        self.w.connect(c.WIFI_SSID, c.WIFI_PASS)


def start(recovery=False, confirm=None):
    """recovery=True: se encendió con la rueda pulsada -> directo a ajustes (para actualizar aunque algo falle)."""
    # 200 kHz: más tolerante con cables largos o soldaduras justas que 400 kHz
    i2c = I2C(0, sda=Pin(cfg.PIN_SDA), scl=Pin(cfg.PIN_SCL), freq=getattr(cfg, "I2C_FREQ", 200000))
    display = SH1106(i2c, rotate180=cfg.OLED_ROTATE_180)
    chg_pin = getattr(cfg, "CHARGE_PIN", None)
    battery = (Battery(cfg.BATTERY_PIN, cfg.BATTERY_RATIO, chg_pin)
               if cfg.BATTERY_PIN is not None or chg_pin is not None else None)
    inputs = Inputs()
    try:                                      # pantalla de arranque cuanto antes
        import ui
        from i18n import t
        from version import VERSION
        ui.render_splash(display.fb, getattr(cfg, "SPLASH_TITLE", "") or "knobeast",
                         "v" + VERSION.split(" ")[0], t("splash_boot"), 5)
        display.show()
    except Exception as e:
        print("splash:", e)

    def setup():
        import portal
        portal.run(cfg, display, inputs, network.WLAN(network.STA_IF), network.WLAN(network.AP_IF), reset)

    if recovery or not cfg.WIFI_SSID:      # rueda pulsada al encender, o primera vez sin wifi guardada
        if recovery:
            while inputs.buttons[0][1].value() == 0:     # esperar a que suelte la rueda
                sleep_ms(20)
            inputs.events()
        setup()
    App(cfg, display, inputs, Net(), battery=battery,
        hooks={"setup": setup, "reboot": reset, "ok": confirm}).run()
