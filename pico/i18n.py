# i18n.py — idioma de la pantalla y de la página de Ajustes. Los textos están en lang_xx.py.
LANGS = (("es", "Español"), ("en", "English"), ("fr", "Français"), ("de", "Deutsch"),
         ("it", "Italiano"), ("pt", "Português"))
CODE = "es"
_T = {}


def set_lang(code):
    global CODE, _T
    import sys
    try:
        mod = __import__("lang_" + code)
    except ImportError:
        if code != "es":
            return set_lang("es")
        raise
    for c, _ in LANGS:                      # liberar el idioma anterior
        if c != code:
            sys.modules.pop("lang_" + c, None)
    CODE, _T = code, mod.T


def t(key, *args):
    if not _T:
        set_lang(CODE)
    s = _T.get(key)
    if s is None:
        s = key
    return s % args if args else s
