# Contributing to knobeast

Thanks for helping! knobeast is a small open project: a physical volume knob for Sonos built on a Raspberry Pi Pico 2 W.

## Ways to help

- **Bugs:** open an [issue](https://github.com/knobeast/knobeast/issues). Include:
  - the firmware version (menu → System → Info);
  - your Sonos setup (models, groups, Port line-out Variable/Fixed);
  - what you expected and what happened.

  The output of `bash diagnostico_mac.sh` helps a lot.
- **Ideas:** open an issue first so we can discuss it before you write code. For example:
  - favourite stations or playlists;
  - Home Assistant;
  - other audio systems;
  - new gestures.
- **Translations:** UI texts live in `pico/lang_xx.py`. Screen strings have a maximum of 16 characters, and accents are folded on the display. To add a language:
  1. copy `lang_en.py`;
  2. translate it;
  3. add it to `LANGS` in `pico/i18n.py`.
- **Case designs:** new cases, knobs or mounts are very welcome. Keep the OpenSCAD source next to the STL files.
- **Docs:** fixes and English translations of code comments.

## Code guidelines

- MicroPython on the Pico 2 W: keep memory use low and avoid big new dependencies.
- Keep `main.py` minimal. It is the safe loader and is never updated over the air.
- Test on real hardware when you can. `prueba_mac.py` lets you test the Sonos logic from a computer.
- One topic per pull request, with a short description of what you tested.

## Security

Never open a public issue for a vulnerability. Email **security@knobeast.com** (see [SECURITY.md](SECURITY.md)).

## Licences

By contributing you agree that your contribution is licensed like the part of the repository it touches:
- firmware and scripts under GPL-3.0;
- hardware under CERN-OHL-S-2.0;
- documentation under CC BY-SA 4.0.

See the README.

## Contact

contact@knobeast.com
