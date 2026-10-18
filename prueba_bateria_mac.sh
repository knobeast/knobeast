#!/bin/bash
# Prueba de las resistencias de batería (GP26) y carga (GP27) por USB.
#   bash prueba_bateria_mac.sh   (con la Pico enchufada al Mac sin BOOTSEL; mejor con el interruptor en ON)
cd "$(dirname "$0")"
LOG=/tmp/knob-bateria.log
PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
[ -n "$PORT" ] || { echo "No encuentro la Pico por USB. Desenchúfala y vuelve a enchufarla (sin BOOTSEL)."; exit 1; }
python3 -m mpremote connect "$PORT" exec "$(cat <<'PY'
import time, json
from machine import ADC, Pin
print('== version:', open('version.py').read().split('\n')[0])
import config as cfg
s = {}
try:
    s = json.loads(open('settings.json').read())
except Exception:
    pass
print('== config: BATTERY_PIN=%r CHARGE_PIN=%r BATTERY_AUTO=%r BATTERY_RATIO=%r' % (
    getattr(cfg, 'BATTERY_PIN', '-'), getattr(cfg, 'CHARGE_PIN', '-'), getattr(cfg, 'BATTERY_AUTO', '-'),
    getattr(cfg, 'BATTERY_RATIO', '-')))
def lento(n):
    a = ADC(Pin(n)); t = 0
    for _ in range(32):
        t += a.read_u16()
    return t / 32 * 3.3 / 65535
def rapido(n):
    Pin(n, Pin.OUT, value=0)
    time.sleep_us(20)
    a = ADC(Pin(n)); t = 0
    for _ in range(8):
        t += a.read_u16()
    return t / 8 * 3.3 / 65535
for i in range(3):
    print('GP26: %.2f V (rapido %.2f V) -> bateria/VSYS ~%.2f V | GP27: %.2f V (rapido %.2f V)' % (
        lento(26), rapido(26), rapido(26) * 2, lento(27), rapido(27)))
    time.sleep(0.5)
try:
    import knob
    if hasattr(knob, 'battery_pins'):
        print('== deteccion automatica ->', knob.battery_pins(cfg))
    else:
        print('== esta version no tiene deteccion automatica (antes de 2.0.3)')
except Exception as e:
    print('== knob:', e)
PY
)" 2>&1 | tee "$LOG"
python3 -m mpremote connect "$PORT" reset >/dev/null 2>&1
pbcopy < "$LOG" 2>/dev/null && echo ">>> Resultado copiado al portapapeles: pégalo donde pidas ayuda (Cmd+V), p. ej. en una incidencia de GitHub."
