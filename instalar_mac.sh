#!/bin/bash
# Graba MicroPython en la Raspberry Pi Pico 2 W y copia el programa. Se ejecuta en el Mac:
#   bash instalar_mac.sh                  # primera vez
#   bash instalar_mac.sh --solo-programa  # después: solo copia los .py
#
# ¡IMPORTANTE! Pon el interruptor en OFF (batería desconectada) antes de enchufar la Pico al Mac.
set -e
cd "$(dirname "$0")"

echo "==> Herramienta mpremote"
if ! python3 -m mpremote --help >/dev/null 2>&1; then
  python3 -m pip install --user -q mpremote 2>/dev/null \
    || python3 -m pip install --user -q --break-system-packages mpremote 2>/dev/null
fi
python3 -m mpremote --help >/dev/null 2>&1 || { echo "No he podido instalar mpremote. Copia este error en una incidencia: https://github.com/knobeast/knobeast/issues"; python3 -m pip install --user mpremote; exit 1; }

if [ "$1" != "--solo-programa" ]; then
  echo
  echo "1) Pon el interruptor de la caja en OFF."
  echo "2) Mantén pulsado el botón BOOTSEL de la Pico y conéctala al Mac con el cable micro-USB."
  echo "3) Suelta el botón. Aparecerá un disco llamado RP2350."
  echo -n "Esperando el disco RP2350"
  for i in $(seq 1 120); do
    [ -d /Volumes/RP2350 ] && break
    echo -n "."; sleep 1
  done
  echo
  [ -d /Volumes/RP2350 ] || { echo "No aparece el disco RP2350. Repite los pasos 2 y 3."; exit 1; }

  echo "==> Descargando la última versión estable de MicroPython para Pico 2 W"
  REL=$(curl -fsSL https://micropython.org/download/RPI_PICO2_W/ \
        | grep -oE '/resources/firmware/RPI_PICO2_W-[0-9]{8}-v[0-9]+\.[0-9]+(\.[0-9]+)?\.uf2' | head -1)
  if [ -z "$REL" ]; then
    echo "No he podido leer la web de MicroPython. Descarga el .uf2 de https://micropython.org/download/RPI_PICO2_W/"
    echo "guárdalo en esta carpeta como firmware.uf2 y vuelve a ejecutar el script."
    [ -f firmware.uf2 ] || exit 1
  else
    echo "   $REL"
    curl -fsSL -o firmware.uf2 "https://micropython.org$REL"
  fi
  echo "==> Grabando (la Pico se reinicia sola al terminar)"
  cp firmware.uf2 /Volumes/RP2350/ || true
  sleep 6
fi

PORT=""
for i in $(seq 1 20); do
  PORT=$(ls /dev/cu.usbmodem* 2>/dev/null | head -1 || true)
  [ -n "$PORT" ] && break
  sleep 1
done
[ -n "$PORT" ] || { echo "No encuentro la Pico. Desenchúfala y vuelve a enchufarla (sin pulsar BOOTSEL)."; exit 1; }
echo "Pico en $PORT"

echo "==> Copiando el programa"
python3 -m mpremote connect "$PORT" cp pico/*.py :
if [ -f firma/clave_publica.py ]; then
  # edición oficial: el mando acepta las versiones firmadas con firma/knobeast_privada.key
  python3 -m mpremote connect "$PORT" cp firma/clave_publica.py :clave_publica.py
  echo "   Edición oficial: se actualizará solo por internet (versiones firmadas)."
else
  echo "   Edición comunidad: sin actualizaciones por internet. Para actualizar, vuelve a"
  echo "   ejecutar este script con --solo-programa o sube los .py desde la página de Ajustes."
fi
echo "==> Identidad del mando (para la pegatina de debajo de la caja)"
INFO=$(python3 -m mpremote connect "$PORT" exec "import config, device; print('%s;%s;%s' % (device.info()['id'], device.ap_name(config), device.info()['ap_pass']))" | tr -d '\r' | tail -1)
ID=$(echo "$INFO" | cut -d';' -f1); RED=$(echo "$INFO" | cut -d';' -f2); CLAVE=$(echo "$INFO" | cut -d';' -f3)
echo "   Red de configuración: $RED"
echo "   Contraseña:           $CLAVE"
echo "   (guardado en mandos.csv)"
[ -f mandos.csv ] || echo "fecha;id;red;clave" > mandos.csv
echo "$(date +%Y-%m-%d);$ID;$RED;$CLAVE" >> mandos.csv
python3 -m mpremote connect "$PORT" reset
echo
echo "Listo. La primera vez la pantalla dirá CONFIGURACION: conecta el móvil a la red $RED"
echo "(contraseña $CLAVE, o escanea el QR de la pantalla), elige la wifi de casa y pulsa Guardar."
echo "Para ver lo que va haciendo:   python3 -m mpremote connect $PORT"
echo "Recuerda: desenchufa la Pico del Mac ANTES de volver a poner el interruptor en ON."
