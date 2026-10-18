# config.py — lo único que tienes que editar.

# La wifi se configura desde el móvil: la primera vez (o manteniendo la rueda pulsada 4 s
# -> Ajustes (wifi)) el mando crea su propia red (con clave, ver pantalla) y eliges tu wifi.
# Lo que se guarda desde el móvil (wifi, volumen máximo) o desde el menú Altavoces manda
# sobre este archivo.
WIFI_SSID = ""
WIFI_PASS = ""
WIFI_COUNTRY = "ES"                  # permite los canales 12 y 13 del wifi en España
AP_NAME = ""                         # red de configuración; vacío = "Knobeast-XXXX" (único por mando)
SETUP_TIMEOUT = 900                  # segundos en modo configuración antes de reiniciarse sola

# Habitaciones que controla la rueda, tal como salen en la app de Sonos. Se eligen desde
# el mando: rueda pulsada 2 s y soltar. Si pones varias, actúa sobre todas a la vez.
ROOMS = []               # vacío = se eligen desde el mando la primera vez
MAX_VOLUME = 60         # la rueda nunca pasará de aquí
VOL_STEP = 1            # puntos de volumen por cada clic de la rueda (también en la página de Ajustes)

# Qué hace pulsar la rueda: "playpause", "mute" o None
ACTIONS = {
    "enc_short": "playpause",   # una pulsación
    "enc_long": None,           # mantener 1 s (pon "mute" si quieres silencio)
}
LONG_MS = 800
HOLD_ROOMS_MS = 2000    # mantener la rueda 2 s y soltar: elegir altavoces
HOLD_MENU_MS = 4000     # seguir hasta 4 s: se abre el menú
MENU_TIMEOUT = 15       # segundos sin tocar nada para cerrar el menú

# Actualizaciones por internet. La edición comunidad (GitHub) no las tiene: se actualiza a mano.
# Solo se activan si clave_publica.py lleva una clave (edición oficial o tu propio servidor); la
# dirección va también en clave_publica.py. Las versiones van firmadas con Ed25519.
UPDATE_URL = ""
VERIFY_TLS = True       # comprobar el certificado del servidor (necesita la hora por NTP)
AUTO_UPDATE = True      # buscar una vez al día, en reposo (también se cambia en Sistema)

# Idioma de la pantalla y de la página de Ajustes: "es", "en", "fr", "de", "it" o "pt".
# También se cambia desde el mando (menú -> Idioma) o desde la página de Ajustes.
LANG = "es"

# Pantalla
OLED_ROTATE_180 = True  # True = pines de la pantalla hacia el frente (borde bajo) de la caja
SCREEN_DIM = 15         # segundos sin tocar hasta atenuar (0 = nunca). También en Sistema -> Atenuar
SCREEN_OFF = 0          # segundos sin tocar hasta apagar (0 = nunca). También en Sistema -> Apagar
SPLASH_TITLE = ""       # texto grande al arrancar; vacío = "knobeast"

# Pines de la Raspberry Pi Pico 2 W (número GPx; entre paréntesis, el pin físico)
PIN_SDA = 4             # GP4  (pin 6)
PIN_SCL = 5             # GP5  (pin 7)
PIN_ENC_CLK = 10        # GP10 (pin 14)
PIN_ENC_DT = 11         # GP11 (pin 15)
PIN_ENC_SW = 12         # GP12 (pin 16)
PIN_ENC_VCC = None      # el "+" del encoder va soldado a 3V3 OUT (pin 36), junto con la pantalla
ENC_REVERSE = False     # True si la rueda va al revés
ENC_DIVIDER = 4         # transiciones por clic (4 en el KY-040; prueba 2 si va "a medias")

# Batería: divisor de 2 resistencias de 100 kΩ entre VSYS y GND, con el punto medio en GP26 (pin 31).
# Cargando: divisor desde IN+ del cargador (10k) a GP27 (pin 32) y 20k de GP27 a GND.
# Con None el mando detecta solo si están las resistencias (GP26 y GP27). Si no las pones, no
# se muestra nada. Pon otro número si las conectas a otro pin, o BATTERY_AUTO = False para no detectar.
BATTERY_PIN = None      # None = automático (GP26)
BATTERY_RATIO = 2.0     # 100k + 100k -> la mitad de la tensión
CHARGE_PIN = None       # None = automático (GP27, si hay batería)
BATTERY_AUTO = True

# Consulta del estado del altavoz
POLL_MS = 1000          # ciclo completo con la pantalla encendida
POLL_IDLE_MS = 4000     # con la pantalla apagada (solo el volumen)
