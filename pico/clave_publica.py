# clave_publica.py — clave con la que el mando comprueba las actualizaciones por internet.
#
# Edición comunidad (la de GitHub): vacía. El mando no busca actualizaciones ni se conecta a ningún
# servidor; se actualiza a mano (USB o página de Ajustes). Ver docs/guia-montaje.md, apartado 7.
#
# Si publicas tus propias versiones firmadas: python3 publicar_actualizacion.py --crear-claves crea
# firma/clave_publica.py (con tu clave y tu UPDATE_URL) e instalar_mac.sh la graba en cada mando.
PUBLIC = ""
UPDATE_URL = ""
