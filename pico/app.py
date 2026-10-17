# app.py — lógica del mando: entradas, Sonos y pantalla. No depende del hardware,
# así que se puede probar en un ordenador con MicroPython.
from time import ticks_ms, ticks_diff, ticks_add, sleep_ms
from sonos import Rooms, list_rooms
from i18n import t, LANGS
import i18n
import ui

POLL_ORDER = ("volume", "mute", "state", "title")


class App:
    def __init__(self, cfg, display, inputs, net, sonos=None, log=print, battery=None, hooks=None):
        self.cfg, self.disp, self.inp, self.net, self.log = cfg, display, inputs, net, log
        rooms = getattr(cfg, "ROOMS", None) or [getattr(cfg, "ROOM", "Comedor")]
        self.sonos = sonos or Rooms(rooms)
        self.st = {"room": self.sonos.room, "mode": "wifi", "volume": None, "mute": False,
                   "state": "STOPPED", "title": "", "detail": "", "battery": None, "charging": None}
        self.battery = battery
        self.hooks = hooks or {}
        self.menu = None            # índice de la opción elegida cuando el menú está abierto
        self.menu_kind = "main"     # "main", "system" o "reset"
        self.menu_t = 0
        self.langsel = None         # índice en la lista de idiomas cuando está abierta
        self.picker = None          # lista de altavoces abierta: {"items", "sel", "top", "msg", "msg_t"}
        self.hold = 0
        now = ticks_ms()
        self.wifi_since = now
        self.pending = 0
        self.last_input = now
        self.last_local = ticks_add(now, -100000)
        self.next_poll = now
        self.poll_i = 0
        self.next_locate = now
        self.next_topology = ticks_add(now, 60000)
        self.next_draw = now
        self.dirty = True
        self.fails = 0
        self.next_battery = now
        self.next_charge = now
        self.next_auto = ticks_add(now, 10 * 60000)     # primera búsqueda automática a los 10 min
        self.splash = True          # pantalla de arranque hasta que controla Sonos (o 20 s, o se toca)
        self.splash_t = now
        self.splash_end = None

    # ------------------------------------------------------------------ utilidades
    def awake(self, now):
        off = self.screen_off()
        return off <= 0 or ticks_diff(now, self.last_input) < off * 1000

    def screen_off(self):
        return getattr(self.cfg, "SCREEN_OFF", 0)

    def screen_dim(self):
        return getattr(self.cfg, "SCREEN_DIM", 15)

    def wake(self, now):
        self.last_input = now
        self.dirty = True

    def _fail(self, e, now):
        self.fails += 1
        self.log("Sonos: %r" % (e,))
        # se ha movido, apagado o cambiado de IP: volver a buscarlo
        self.sonos.ip = None
        self.st["mode"] = "search"
        self.st["detail"] = ""
        self.next_locate = ticks_add(now, 2000 if self.fails < 3 else 8000)
        self.dirty = True

    # ------------------------------------------------------------------ acciones
    def do(self, action, now):
        if self.sonos.ip is None:
            return
        try:
            if action == "mute":
                m = not self.st["mute"]
                self.sonos.set_mute(m)
                self.st["mute"] = m
            elif action == "playpause":
                if self.st["state"] == "PLAYING":
                    self.sonos.pause()
                    self.st["state"] = "PAUSED_PLAYBACK"
                else:
                    self.sonos.play()
                    self.st["state"] = "PLAYING"
            self.last_local = now
            self.dirty = True
        except Exception as e:
            if "HTTP 500" in str(e):     # p. ej. play sin nada en cola: no es un fallo de red
                self.log("Accion rechazada por Sonos: %s" % e)
            else:
                self._fail(e, now)

    def apply_volume(self, now):
        delta, self.pending = self.pending, 0
        if not delta:
            return
        try:
            new = self.sonos.nudge(delta, self.cfg.MAX_VOLUME)
            if delta > 0 and self.st["mute"]:
                self.sonos.set_mute(False)
                self.st["mute"] = False
            self.st["volume"] = new
            self.last_local = now
            self.dirty = True
        except Exception as e:
            self._fail(e, now)

    def poll(self, now):
        what = POLL_ORDER[self.poll_i % len(POLL_ORDER)] if self.awake(now) else "volume"
        self.poll_i += 1
        try:
            if what == "volume":
                v = self.sonos.get_volume()
                recent = ticks_diff(now, self.last_local) < 1500
                if not recent and self.st["volume"] is not None and v != self.st["volume"]:
                    self.wake(now)          # lo han cambiado desde la app: enciende la pantalla
                if not recent:
                    self.st["volume"] = v
            elif what == "mute":
                self.st["mute"] = self.sonos.get_mute()
            elif what == "state":
                self.st["state"] = self.sonos.get_state()
            elif what == "title":
                self.st["title"] = self.sonos.get_title()
            self.fails = 0
            self.dirty = True
        except Exception as e:
            self._fail(e, now)
        gap = self.cfg.POLL_MS // len(POLL_ORDER) if self.awake(now) else self.cfg.POLL_IDLE_MS
        self.next_poll = ticks_add(now, gap)

    def locate(self, now):
        self.st["mode"] = "search"
        self.draw(now, force=True)
        try:
            ip = self.sonos.locate()
            self.log("%s -> %s (coordinador %s)%s" % (self.sonos.room, ip, self.sonos.coord,
                     " sin %s" % ", ".join(self.sonos.missing) if getattr(self.sonos, "missing", None) else ""))
            try:
                vol = self.sonos.get_volume()        # comprobar que de verdad contesta
            except Exception:
                self.sonos.ip = None
                raise Exception("%s no responde" % self.sonos.room)
            self.st["room"] = self.sonos.room
            self.st["mode"] = "ok"
            ok = self.hooks.pop("ok", None)     # primera vez que controla Sonos: versión buena
            if ok:
                try:
                    ok()
                except Exception as e:
                    self.log("confirmar: %r" % (e,))
            self.st["detail"] = ""
            self.st["volume"] = vol
            self.fails = 0
            self.next_poll = now
            self.next_topology = ticks_add(now, 60000)
        except Exception as e:
            self.log("Busqueda: %s" % e)
            self.st["mode"] = "error"
            self.st["detail"] = str(e)
            self.next_locate = ticks_add(now, 5000)
        self.dirty = True

    # ------------------------------------------------------------------ pantalla
    def draw(self, now, force=False):
        idle = ticks_diff(now, self.last_input)
        overlay = (self.menu is not None or self.picker is not None or self.langsel is not None
                   or self.hold > 0 or self.splash)
        off, dim = self.screen_off(), self.screen_dim()
        if (not overlay and off > 0 and idle >= off * 1000
                and self.st["mode"] == "ok"):
            self.disp.power(False)
            return
        self.disp.power(True)
        dimmed = dim > 0 and idle >= dim * 1000 and not overlay
        self.disp.contrast(0 if dimmed else 255)
        scrolling = len(ui.fold(self.st.get("title") or "")) * 8 > 118
        if not (force or self.dirty or scrolling):
            return
        if not force and ticks_diff(now, self.next_draw) < 0:
            return
        if self.splash:
            mode = self.st["mode"]
            stage, pct = {"wifi": ("splash_wifi", 30), "search": ("splash_sonos", 65),
                          "error": ("splash_sonos", 80), "ok": ("splash_ok", 100)}.get(mode, ("splash_boot", 10))
            if mode == "wifi":         # avanza poco a poco mientras conecta
                pct = min(55, 15 + ticks_diff(now, self.splash_t) // 200)
            ui.render_splash(self.disp.fb, self.splash_title(), self.version(), t(stage), pct)
        elif self.picker is not None:
            p = self.picker
            ui.render_rooms(self.disp.fb, p["items"], p["sel"], p["top"], p["msg"])
        elif self.langsel is not None:
            codes = [c for c, _ in LANGS]
            cur = codes.index(i18n.CODE) if i18n.CODE in codes else None
            ui.render_menu(self.disp.fb, self.langsel, t("lang_title"), [n for _, n in LANGS], cur)
        elif self.menu is not None:
            title, items = self.menu_items()
            ui.render_menu(self.disp.fb, self.menu, title, [label for _, label in items])
        else:
            shift = 0
            if off <= 0 and dimmed:
                shift = (now // 120000) % 3          # siempre encendida: mover 0-2 px para no marcar la pantalla
            ui.render(self.disp.fb, self.st, now, shift)
            if self.hold > 0:
                ui.render_hold(self.disp.fb, self.hold, self.cfg.MENU_MS)
        self.disp.show()
        self.dirty = False
        self.next_draw = ticks_add(now, 100)

    # ------------------------------------------------------------------ menú
    def version(self):
        try:
            from version import VERSION
            return "v" + VERSION.split(" ")[0]
        except Exception:
            return ""

    def splash_title(self):
        return getattr(self.cfg, "SPLASH_TITLE", "") or "knobeast"

    def splash_step(self, now, steps, events):
        self.dirty = True                         # la barra se va moviendo
        if steps or events:                       # tocar la rueda la quita al momento
            self.splash = False
        elif self.st["mode"] == "ok" and self.st["volume"] is not None:
            if self.splash_end is None:
                self.splash_end = ticks_add(now, 700)    # que se vea la barra llena un momento
            elif ticks_diff(now, self.splash_end) >= 0:
                self.splash = False
        elif ticks_diff(now, self.splash_t) > 20000:
            self.splash = False
        if not self.splash:
            self.wake(now)

    def menu_items(self):
        k = self.menu_kind
        if k == "system":
            auto = getattr(self.cfg, "AUTO_UPDATE", True)
            def secs(v):
                return t("never") if v <= 0 else ("%d s" % v if v < 60 else "%d min" % (v // 60))
            upd = [("update", t("m_update")), ("auto", t("s_auto_on" if auto else "s_auto_off"))] if self.ota_url() else []
            return t("sys_title"), upd + [("dim", t("s_dim", secs(self.screen_dim()))),
                                    ("screen", t("s_screen", secs(self.screen_off()))),
                                    ("info", t("s_info")), ("reset", t("s_reset")), ("reboot", t("m_reboot")),
                                    ("back", t("s_back"))]
        if k == "reset":
            return t("reset_title"), [("no", t("reset_no")), ("yes", t("reset_yes"))]
        return t("menu"), [("rooms", t("m_rooms")), ("lang", t("m_lang")), ("setup", t("m_setup")),
                           ("system", t("m_system"))]

    def open_menu(self, kind, now, sel=0):
        self.menu_kind, self.menu, self.menu_t = kind, sel, now
        self.dirty = True

    def menu_step(self, now, steps, events):
        _, items = self.menu_items()
        if steps:
            self.menu = (self.menu + (1 if steps > 0 else -1)) % len(items)
            self.menu_t = now
            self.dirty = True
        for ev in events:
            self.menu_t = now
            if ev != "enc_short":
                continue
            what = items[self.menu][0]
            self.log("Menu: %s" % what)
            self.dirty = True
            if what == "system":
                self.open_menu("system", now)
                return
            if what == "back":
                self.open_menu("main", now, 3)
                return
            if what == "auto":
                on = not getattr(self.cfg, "AUTO_UPDATE", True)
                self.cfg.AUTO_UPDATE = on
                self.save_setting("AUTO_UPDATE", on)
                self.info(t("sys_title"), t("s_auto_on" if on else "s_auto_off"), "", 900)
                return                                   # sigue en el menú Sistema
            if what in ("screen", "dim"):
                key, opts = (("SCREEN_OFF", (0, 300, 60, 30)) if what == "screen"
                             else ("SCREEN_DIM", (15, 30, 60, 0)))
                cur = getattr(self.cfg, key, opts[0])
                nxt = opts[(opts.index(cur) + 1) % len(opts)] if cur in opts else opts[0]
                setattr(self.cfg, key, nxt)
                self.save_setting(key, nxt)
                return                                   # sigue en el menú Sistema, con el valor nuevo
            if what == "info":
                self.show_info()
                return
            if what == "reset":
                self.open_menu("reset", now)
                return
            if what == "no":
                self.menu_kind = "system"
                self.open_menu("system", now, [k for k, _ in self.menu_items()[1]].index("reset"))
                return
            self.menu = None
            if what == "yes":
                self.factory_reset()
                return
            if what == "lang":
                codes = [c for c, _ in LANGS]
                self.langsel = codes.index(i18n.CODE) if i18n.CODE in codes else 0
                self.menu_t = now
                return
            if what == "rooms":
                self.open_picker(now)
                return
            if what == "update":
                self.update(now)
                return
            hook = self.hooks.get(what)              # "setup" o "reboot"
            if hook:
                self.draw(now, force=True)
                hook()
            return
        if ticks_diff(now, self.menu_t) > self.cfg.MENU_TIMEOUT * 1000:
            self.menu = None
            self.dirty = True

    def save_setting(self, key, value):
        try:
            import settings
            settings.save({key: value})
        except Exception as e:
            self.log("No se pudo guardar: %r" % (e,))

    def ota_url(self):
        """Dirección de las actualizaciones por internet, o "" si este mando no las tiene.
        Edición oficial: clave_publica.py trae la clave y la dirección. Edición comunidad (GitHub):
        clave vacía, así que nunca se conecta a ningún servidor; se actualiza a mano."""
        u = getattr(self, "_ota_url", None)
        if u is None:
            u = ""
            try:
                import clave_publica
                if getattr(clave_publica, "PUBLIC", ""):
                    u = getattr(clave_publica, "UPDATE_URL", "") or getattr(self.cfg, "UPDATE_URL", "") or ""
            except ImportError:
                pass
            self._ota_url = u
        return u

    def show_info(self):
        try:
            from version import VERSION
        except Exception:
            VERSION = "?"
        try:
            import device
            dev = device.info()["id"][-8:].upper()
        except Exception:
            dev = "?"
        self.info(t("s_info").upper(), t("upd_ver", VERSION.split(" ")[0]), "ID " + dev, 4000)

    def factory_reset(self):
        """Borra wifi, altavoces, idioma y ajustes. La identidad y la clave de configuración se quedan."""
        import os
        for f in ("settings.json", "errores.txt"):
            try:
                os.remove(f)
            except OSError:
                pass
        self.log("Restablecido de fabrica")
        self.info(t("s_reset").upper(), t("reset_done"), t("restarting"), 1500)
        hook = self.hooks.get("reboot")
        if hook:
            hook()

    # ------------------------------------------------------------------ idioma
    def lang_step(self, now, steps, events):
        if steps:
            self.langsel = max(0, min(len(LANGS) - 1, self.langsel + steps))
            self.menu_t = now
            self.dirty = True
        if "enc_short" in events:
            code = LANGS[self.langsel][0]
            self.langsel = None
            self.dirty = True
            i18n.set_lang(code)
            self.cfg.LANG = code
            self.save_setting("LANG", code)
            self.log("Idioma: %s" % code)
            return
        if ticks_diff(now, self.menu_t) > self.cfg.MENU_TIMEOUT * 1000:
            self.langsel = None
            self.dirty = True

    # ------------------------------------------------------------------ actualizar por internet
    def update(self, now, silent=False):
        """Busca e instala una versión nueva. silent=True: búsqueda automática (solo se ve si instala)."""
        try:
            from version import VERSION
        except Exception:
            VERSION = "?"
        have = VERSION.split(" ")[0]
        if not self.net.connected():
            if not silent:
                self.info(t("upd_title"), t("no_wifi"), "", 1500)
            return
        if not silent:
            self.info(t("upd_title"), t("upd_search"), t("upd_have", have))
        try:
            import ota
            base = self.ota_url()
            if not base:
                return
            verify = getattr(self.cfg, "VERIFY_TLS", True)
            version, todo = ota.check(base, log=self.log, verify_tls=verify)
            if not todo:
                if not silent:
                    self.info(t("upd_title"), t("upd_ok"), t("upd_ver", have), 2500)
                return
            self.info(t("upd_title"), t("upd_new", str(version).split(" ")[0]), t("upd_dl"), 800)

            newv = "v" + str(version).split(" ")[0]
            last = [-1]

            def progress(i, n, name):
                if name is None:                   # paquete: barra con el % descargado
                    pct = i * 100 // n if n else 0
                    if pct >= last[0] + 3 or pct == 100:
                        last[0] = pct
                        lbl = t("upd_dl").rstrip(".")
                        txt = "%s %d%%" % (lbl, pct) if len(ui.fold(lbl)) <= 11 else "%d%%" % pct
                        ui.render_splash(self.disp.fb, t("upd_title"), newv, txt, pct)
                        self.disp.power(True)
                        self.disp.contrast(255)
                        self.disp.show()
                else:
                    self.info(t("upd_title"), t("upd_dl_n", i, n), name)

            ota.install(base, todo, progress, log=self.log, verify_tls=verify)
        except Exception as e:
            self.log("Actualizar: %r" % (e,))
            if not silent:
                msg = str(e).strip() or e.__class__.__name__
                self.info(t("upd_title"), t("upd_fail"), msg, 3000)
            return
        self.info(t("upd_title"), t("upd_done", str(version).split(" ")[0]), t("restarting"), 1500)
        hook = self.hooks.get("reboot")
        if hook:
            hook()

    def auto_update(self, now):
        """Una vez al día, con el mando en reposo, busca actualizaciones (se puede desactivar)."""
        if ticks_diff(now, self.next_auto) < 0:
            return
        if not getattr(self.cfg, "AUTO_UPDATE", True) or not self.ota_url():
            self.next_auto = ticks_add(now, 3600000)
            return
        batt = self.st.get("battery")
        low = batt is not None and batt < 30 and not self.st.get("charging")
        if ticks_diff(now, self.last_input) < 5 * 60000 or low:
            self.next_auto = ticks_add(now, 15 * 60000)     # ahora no: en uso o poca batería
            return
        self.next_auto = ticks_add(now, 24 * 3600000)
        self.log("Busqueda automatica de actualizaciones")
        self.update(now, silent=True)
        self.dirty = True

    # ------------------------------------------------------------------ elegir altavoces
    def info(self, title, line1, line2="", ms=0):
        ui.render_info(self.disp.fb, ui.fold(title), ui.fold(line1), ui.fold(line2))
        self.disp.power(True)
        self.disp.contrast(255)
        self.disp.show()
        if ms:
            sleep_ms(ms)
        self.dirty = True

    def open_picker(self, now):
        if not self.net.connected():
            self.info(t("rooms_title"), t("no_wifi"), "", 1500)
            return
        self.info(t("rooms_title"), t("rooms_search1"), t("rooms_search2"))
        try:
            found = list_rooms(getattr(self.sonos, "hint", None) or [])
        except Exception as e:
            self.log("Lista de altavoces: %s" % e)
            self.info(t("rooms_title"), t("none_found1"), t("none_found2"), 2000)
            return
        from sonos import entry_key
        keys = [entry_key(e)[0] for e in self.sonos.rooms]
        items, seen = [], []
        for uuid, name, label, grp in found:
            on = uuid in keys or (name.lower() in [k.lower() for k in keys])
            room_w = 11 if grp else 14                        # sin marca de grupo cabe más
            if label != name and len(ui.fold(label)) > room_w:  # que se vea el modelo/número
                suffix = label[len(name) + 1:]
                label = name[:max(3, room_w - 1 - len(suffix))] + " " + suffix
            items.append(["room", label, on, grp, "%s|%s" % (uuid, name)])
            seen.append(uuid)
            seen.append(name.lower())
        for e in self.sonos.rooms:          # elegidas que ahora no aparecen (apagadas): se pueden quitar
            k, label = entry_key(e)
            if k not in seen and k.lower() not in seen:
                items.append(["room", label, True, -1, e])
        items.append(["save", "", False, 0, ""])
        items.append(["cancel", "", False, 0, ""])
        self.log("Altavoces: %s" % ", ".join("%s%s" % (i[1], "[G%d]" % i[3] if i[3] > 0 else "")
                                              for i in items if i[0] == "room"))
        self.picker = {"items": items, "sel": 0, "top": 0, "msg": "", "msg_t": 0}
        self.inp.encoder_steps()             # descartar giros hechos mientras buscaba
        self.inp.events()
        self.menu_t = ticks_ms()
        self.wake(self.menu_t)

    def picker_step(self, now, steps, events):
        p = self.picker
        if p["msg"]:
            if ticks_diff(now, p["msg_t"]) > 1200:
                p["msg"] = ""
                self.dirty = True
            return
        items = p["items"]
        if steps:
            p["sel"] = max(0, min(len(items) - 1, p["sel"] + steps))
            if p["sel"] < p["top"]:
                p["top"] = p["sel"]
            elif p["sel"] >= p["top"] + ui.ROWS:
                p["top"] = p["sel"] - ui.ROWS + 1
            self.menu_t = now
            self.dirty = True
        for ev in events:
            self.menu_t = now
            if ev != "enc_short":
                continue
            it = items[p["sel"]]
            self.dirty = True
            if it[0] == "room":
                it[2] = not it[2]
            elif it[0] == "cancel":
                self.picker = None
                return
            else:
                names = [i[4] for i in items if i[0] == "room" and i[2]]
                if not names:
                    p["msg"], p["msg_t"] = t("pick_one"), now
                    return
                self.picker = None
                self.set_rooms(names, now)
                return
        if ticks_diff(now, self.menu_t) > self.cfg.MENU_TIMEOUT * 2000:
            self.picker = None
            self.dirty = True

    def set_rooms(self, names, now):
        self.log("Nuevos altavoces: %s" % ", ".join(names))
        try:
            import settings
            settings.save({"ROOMS": names})
        except Exception as e:
            self.log("No se pudo guardar: %r" % (e,))
        self.cfg.ROOMS = names
        hint = getattr(self.sonos, "hint", [])
        self.sonos = Rooms(names)
        self.sonos.hint = hint
        self.st.update({"room": self.sonos.room, "mode": "search", "volume": None, "mute": False,
                        "title": "", "detail": ""})
        self.info(t("rooms_title"), t("saved"), self.sonos.room, 1200)
        self.next_locate = now
        self.wake(now)

    # ------------------------------------------------------------------ bucle
    def step(self):
        now = ticks_ms()
        if self.battery is not None and ticks_diff(now, self.next_battery) >= 0:
            try:
                b = self.battery.read()
                if b != self.st["battery"]:
                    self.st["battery"] = b
                    self.dirty = True
            except Exception as e:
                self.log("Bateria: %r" % (e,))
            self.next_battery = ticks_add(now, 30000)
        if self.battery is not None and ticks_diff(now, self.next_charge) >= 0:
            try:
                c = self.battery.charging()
                if c != self.st["charging"]:
                    if self.st["charging"] is not None or c:
                        self.wake(now)               # al enchufar/desenchufar se ve en pantalla
                    self.st["charging"] = c
                    self.next_battery = now          # releer el % al momento
                    self.dirty = True
            except Exception as e:
                self.log("Carga: %r" % (e,))
            self.next_charge = ticks_add(now, 1000)
        steps = self.inp.encoder_steps()
        if steps and self.cfg.ENC_REVERSE:
            steps = -steps
        events = self.inp.events()
        held = self.inp.held("enc") if hasattr(self.inp, "held") else 0
        hold = (held if held >= 1000 and self.menu is None and self.picker is None and self.langsel is None
                else 0)
        if hold != self.hold:
            self.hold = hold
            self.dirty = True
            if hold:
                self.wake(now)
        if self.splash:
            self.splash_step(now, steps, events)
            if not self.splash:
                steps, events = 0, []                # el primer toque solo quita la pantalla de arranque
        if "enc_menu" in events:
            self.menu, self.menu_kind, self.menu_t, self.hold, self.picker, self.langsel = 0, "main", now, 0, None, None
            self.pending = 0
            self.wake(now)
            self.draw(now, force=True)
            return
        if self.picker is not None:
            if steps or events:
                self.wake(now)
            self.picker_step(now, steps, events)
            self.draw(now)
            return
        if self.langsel is not None:
            if steps or events:
                self.wake(now)
            self.lang_step(now, steps, events)
            self.draw(now)
            return
        if self.menu is not None:
            if steps or events:
                self.wake(now)
            self.menu_step(now, steps, events)
            self.draw(now)
            return
        if steps:
            self.pending += steps * getattr(self.cfg, "VOL_STEP", 1)
            self.wake(now)
        for ev in events:
            self.wake(now)
            action = self.cfg.ACTIONS.get(ev)
            if action:
                self.do(action, now)

        if not self.net.connected():
            if self.st["mode"] != "wifi":
                self.st["mode"] = "wifi"
                self.wifi_since = now
                self.dirty = True
                self.sonos.ip = None
            if ticks_diff(now, self.wifi_since) > 30000 and not self.st["detail"]:
                self.st["detail"] = t("hint_menu")
                self.dirty = True
            self.draw(now)
            self.net.connect(self.cfg)
            return
        if self.st["mode"] == "wifi":
            self.st["mode"] = "search"
            self.st["detail"] = ""
            self.next_locate = now

        if self.sonos.ip is None:
            self.pending = 0
            if ticks_diff(now, self.next_locate) >= 0:
                self.locate(now)
        elif self.pending:
            self.apply_volume(now)
        elif ticks_diff(now, self.next_topology) >= 0:
            # cada minuto, por si has agrupado/desagrupado habitaciones
            try:
                self.sonos.locate()
            except Exception as e:
                self._fail(e, now)
            self.next_topology = ticks_add(now, 60000)
        elif ticks_diff(now, self.next_poll) >= 0:
            self.poll(now)
        elif self.st["mode"] == "ok":
            self.auto_update(now)
        self.draw(now)

    def run(self):
        while True:
            self.step()
            sleep_ms(5)
