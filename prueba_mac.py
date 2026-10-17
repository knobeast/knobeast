#!/usr/bin/env python3
"""Prueba en el Mac la misma búsqueda y las mismas órdenes que usará el mando.

    python3 prueba_mac.py --lista               # altavoces y grupos que hay en casa
    python3 prueba_mac.py                       # busca "Comedor" y muestra su estado
    python3 prueba_mac.py --mover               # además sube 2 puntos y los vuelve a bajar
    python3 prueba_mac.py Comedor Salón --mover # varias habitaciones a la vez
"""
import os
import sys
import time

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(_here, "pico"))
import sonos  # noqa: E402

rooms = [a for a in sys.argv[1:] if not a.startswith("--")] or ["Comedor"]

t = time.time()
ips = sonos.ssdp_search()
print("Altavoces que contestan: %s  (%.1f s)" % (", ".join(ips) or "ninguno", time.time() - t))
if not ips:
    sys.exit("No ha contestado ningún Sonos. ¿Está el Mac en la misma red? ¿Firewall bloqueando UDP 1900?")

if "--lista" in sys.argv:
    print("\nHabitaciones (G1, G2... = agrupadas ahora mismo en Sonos):")
    for uuid, name, label, grp in sonos.list_rooms(ips):
        print("  %-24s %-6s %s" % (label, "G%d" % grp if grp else "sola", uuid))
    sys.exit(0)

s = sonos.Rooms(rooms)
s.hint = ips
t = time.time()
s.locate()
print("%s -> %s   coordinador(es): %s   (%.1f s)" % (s.room, ", ".join(s.ips), ", ".join(s.coords), time.time() - t))
if s.missing:
    print("No contestan: %s" % ", ".join(s.missing))
if len(s.ips) > 1:
    print("Modo: %s" % ("volumen de grupo (son exactamente un grupo de Sonos)" if s.group
                        else "cada habitación por separado, mismo salto en todas"))
print("Volumen: %d   Silencio: %s   Estado: %s" % (s.get_volume(), s.get_mute(), s.get_state()))
print("Suena: %s" % (s.get_title() or "(nada)"))

if "--mover" in sys.argv:
    print("Subo 2 ->", s.nudge(2, 100))
    time.sleep(1.5)
    print("Bajo 2 ->", s.nudge(-2, 100))
print("Todo OK: el mando podrá encontrar y controlar «%s» sin saber su IP." % s.room)
