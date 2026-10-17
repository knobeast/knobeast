# Changelog

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
