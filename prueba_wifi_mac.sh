#!/bin/bash
# Prueba de la wifi del mando por USB: busca las redes, mira si está la guardada y prueba a conectar.
# No muestra la contraseña (solo su longitud y si tiene espacios o caracteres raros).
#   bash prueba_wifi_mac.sh   (desde la carpeta del proyecto, con la Pico enchufada al Mac sin BOOTSEL)
cd "$(dirname "$0")"
LOG=/tmp/knob-wifi.log
PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)
[ -n "$PORT" ] || { echo "No encuentro la Pico por USB. Desenchúfala y vuelve a enchufarla (sin BOOTSEL)."; exit 1; }
echo "Pico en $PORT — probando la wifi (unos 40 s)…"
python3 -m mpremote connect "$PORT" exec "$(cat <<'PY'
import network, time, json
try:
    import rp2
except ImportError:
    rp2 = None
s = {}
try:
    s = json.loads(open('settings.json').read())
except Exception:
    pass
import config as cfg
ssid = s.get('WIFI_SSID', getattr(cfg, 'WIFI_SSID', ''))
pw = s.get('WIFI_PASS', getattr(cfg, 'WIFI_PASS', ''))
country = s.get('WIFI_COUNTRY', getattr(cfg, 'WIFI_COUNTRY', '?'))
print('== version:', open('version.py').read().split('\n')[0])
print('== red guardada: %r (%d caracteres)' % (ssid, len(ssid)))
print('== contraseña: %d caracteres, espacio al principio/final: %s, caracteres no ASCII: %s'
      % (len(pw), pw != pw.strip(), any(ord(c) > 127 for c in pw)))
print('== pais wifi:', country)
if rp2:
    try:
        rp2.country(country)
    except Exception as e:
        print('   pais:', e)
w = network.WLAN(network.STA_IF)
w.active(True)
time.sleep(1)
print('== MAC del mando:', ':'.join('%02x' % b for b in w.config('mac')))
redes = []
for _ in range(2):
    try:
        redes += w.scan()
    except Exception as e:
        print('scan:', e)
    time.sleep(1)
vistas = {}
for r in redes:
    n = r[0].decode('utf-8', 'replace')
    k = (n, r[1])
    if k not in vistas or r[3] > vistas[k][3]:
        vistas[k] = r
print('== redes que ve el mando (solo 2,4 GHz):')
for (n, b), r in sorted(vistas.items(), key=lambda x: -x[1][3]):
    print('   %-32s canal %2d  señal %4d dBm  seguridad %s%s' % (repr(n), r[2], r[3], r[4], '  OCULTA' if r[5] else ''))
nombres = set(n for n, b in vistas)
if ssid in nombres:
    print('== la red guardada SÍ aparece')
else:
    parecidas = [n for n in nombres if n.strip().lower() == ssid.strip().lower()]
    print('== la red guardada NO aparece' + ('; parecidas: %r' % parecidas if parecidas else
          ' (¿solo 5 GHz, oculta o mal escrita?)'))
NOMBRE = {0: 'parado', 1: 'conectando', 2: 'conectado sin IP (DHCP)', 3: 'CONECTADO con IP',
          -1: 'fallo de conexión', -2: 'red no encontrada', -3: 'CONTRASEÑA INCORRECTA'}
print('== conectando a %r…' % ssid)
w.disconnect()
time.sleep(0.5)
w.connect(ssid, pw)
ant = None
t0 = time.ticks_ms()
while time.ticks_diff(time.ticks_ms(), t0) < 25000:
    st = w.status()
    if st != ant:
        print('   %5.1f s  estado %d = %s' % (time.ticks_diff(time.ticks_ms(), t0) / 1000, st, NOMBRE.get(st, '?')))
        ant = st
    if st == 3 or st < 0:
        break
    time.sleep_ms(200)
if w.isconnected():
    print('== IP, máscara, puerta de enlace, DNS:', w.ifconfig())
    print('== señal:', w.status('rssi'), 'dBm')
else:
    print('== NO conecta. Último estado:', ant, NOMBRE.get(ant, '?'))
w.disconnect()
PY
)" 2>&1 | tee "$LOG"
python3 -m mpremote connect "$PORT" reset >/dev/null 2>&1
pbcopy < "$LOG" 2>/dev/null && echo ">>> Resultado copiado al portapapeles: pégalo donde pidas ayuda (Cmd+V), p. ej. en una incidencia de GitHub."
