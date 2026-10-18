# Changelog

## 2.0.6 — 2026-10-17

- **Easier speaker picking:** hold the dial 2 s and let go to open the speaker list; keep holding to 4 s for the menu. The hold bar shows which one you get.
- The main menu ends with **Back**, to leave without changing anything.
- **Volume step** (1/2/3/5) is now also in *Menu → System*.
- **No default room:** after a reset the device no longer assumes a room called «Comedor»; once on Wi-Fi it opens the speaker list.
- **Wi-Fi names with leading or trailing spaces** (e.g. `"Home "`) are now saved exactly, and devices that saved them trimmed find the network anyway.
- **Battery and charging detected automatically** (100k/100k on GP26, 10k/20k on GP27): no need to edit `config.py`.
- New USB test scripts: `prueba_wifi_mac.sh` (networks seen, saved name, exact connection error) and `prueba_bateria_mac.sh` (battery and charge voltages).
- **Case:** new display mount. Pins towards the knob, two screws on the flex side and two slotted tabs on the pin side; no posts touching the glass any more. Rear switch hole is now round, Ø12 mm.
- Docs: the TP4056 USB-C board must have the 5.1 kΩ CC resistors to charge from USB-C-to-USB-C cables.

## 2.0.2 — 2026-10-17

- Display: the periodic display check no longer makes some SH1106 panels blink every 20 seconds while idle. Full re-initialisation now happens only after a communication error.

## 2.0.1 — 2026-10-17 · first public release (community edition)

- **Sonos control:**
  - volume with the dial (step 1/2/3/5) and play/pause with a press;
  - control of one room, several rooms or a Sonos group;
  - speakers with the same name are told apart by model;
  - fixed line-outs are detected and skipped;
  - maximum volume limit.
- **Display:**
  - room, volume, now playing and battery/charging;
  - startup screen with a progress bar;
  - configurable dimming and sleep, with pixel shift when always on;
  - display driver that recovers from I²C errors.
- **Setup:**
  - WPA2 setup network with a unique, permanent password for each device, shown with a QR code;
  - web settings page in six languages.
- **Updates:**
  - community edition: no internet updates and no connection to any server; update by hand over USB or from the settings page;
  - automatic rollback if a new version fails to boot;
  - optional self-hosted signed updates: Ed25519, HTTPS with certificate checks, anti-rollback, compressed bundle with retries and resume.
- **Languages:** English, Spanish, French, German, Italian and Portuguese.
- **Case v2:**
  - square face with the screen at the top and a large knob at the bottom;
  - 13° tilt on a table, flat on the wall with a magnetic wall bracket;
  - hidden USB-C;
  - engraved logo.
