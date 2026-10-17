#!/bin/bash
# Diagnóstico del mando por USB (interruptor en OFF, Pico enchufada al Mac sin BOOTSEL).
# Arranca el programa 25 segundos mostrando lo que hace, y copia el resultado al portapapeles.
#   bash diagnostico_mac.sh   (desde la carpeta del proyecto)
cd "$(dirname "$0")"
LOG=/tmp/knob-diagnostico.log
PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
[ -n "$PORT" ] || { echo "No encuentro la Pico por USB. Desenchúfala y vuelve a enchufarla (sin BOOTSEL)."; exit 1; }
echo "Pico en $PORT — mira la pantalla mientras tanto (25 s)…"
python3 -m mpremote connect "$PORT" exec "$(cat <<'PY'
import sys, time, os
def leer(n, cola=1500):
    try:
        return open(n).read()[-cola:]
    except Exception as e:
        return '-'
print('== version:', leer('version.py').strip())
try:
    import json
    _s = json.loads(open('settings.json').read())
    if _s.get('WIFI_PASS'):
        _s['WIFI_PASS'] = '****'
    print('== settings:', _s)
except Exception:
    print('== settings: -')
print('== actualizacion:', leer('actualizacion.json'))
print('== errores:', leer('errores.txt'))
print('== archivos:', sorted(os.listdir()))
import config as cfg
print('== config:', [(k, getattr(cfg, k, None)) for k in ('OLED_ROTATE_180', 'SCREEN_DIM', 'SCREEN_OFF',
      'DIM_AFTER', 'OFF_AFTER', 'VOL_STEP', 'STEP', 'PIN_SDA', 'PIN_SCL', 'BATTERY_PIN')])
import sh1106
_p, _c, _s = sh1106.SH1106.power, sh1106.SH1106.contrast, sh1106.SH1106.show
n = {'show': 0}
def p(self, on):
    if on != self.on:
        print('PANTALLA power', on, time.ticks_ms())
    _p(self, on)
def c(self, v):
    if v != getattr(self, '_c', None):
        print('PANTALLA brillo', v, time.ticks_ms())
    _c(self, v)
def s(self):
    n['show'] += 1
    if n['show'] in (1, 2, 5, 20, 100):
        print('PANTALLA dibujo n.', n['show'], time.ticks_ms())
    _s(self)
sh1106.SH1106.power, sh1106.SH1106.contrast, sh1106.SH1106.show = p, c, s
import knob
from app import App
T0 = time.ticks_ms()
_step = App.step
def step(self):
    if time.ticks_diff(time.ticks_ms(), T0) > 25000:
        print('== FIN 25 s · dibujos:', n['show'], '· modo:', self.st.get('mode'), '· splash:', self.splash,
              '· vol:', self.st.get('volume'), '· apagada:', not self.disp.on)
        raise SystemExit
    _step(self)
App.step = step
try:
    knob.start(False, None)
except SystemExit:
    pass
except Exception as e:
    print('== EXCEPCION')
    sys.print_exception(e)
PY
)" 2>&1 | tee "$LOG"
python3 -m mpremote connect "$PORT" reset >/dev/null 2>&1
pbcopy < "$LOG" 2>/dev/null && echo ">>> Resultado copiado al portapapeles: pégalo donde pidas ayuda (Cmd+V), p. ej. en una incidencia de GitHub."
