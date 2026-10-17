#!/usr/bin/env python3
"""Publica la versión de la carpeta pico/ para que los mandos la instalen por internet.

    python3 publicar_actualizacion.py --crear-claves   # solo la primera vez (lo hace instalar_mac.sh)
    python3 publicar_actualizacion.py --preparar      # firma y deja todo en ./publicado/ (sin subir)
    python3 publicar_actualizacion.py                 # firma, sube al servidor y comprueba

Firma:
  - Clave PRIVADA: firma/knobeast_privada.key. Nunca se sube a ningún sitio ni va en el mando.
    Guárdala con copia de seguridad: sin ella no se pueden publicar versiones que los mandos acepten.
  - Clave PÚBLICA: firma/clave_publica.py (con la dirección de las actualizaciones). instalar_mac.sh la
    graba en cada mando y va dentro de cada versión publicada. La de pico/ está vacía a propósito: es
    la edición comunidad de GitHub, que no se actualiza por internet.
  - Antes de publicar, sube BUILD en pico/version.py: los mandos no aceptan builds menores al suyo.

Servidor: se lee de .servidor.json (junto a este script, no se sube a GitHub) o de variables de entorno:
    {"IP": "1.2.3.4", "USUARIO": "admin", "CARPETA_WEB": "/var/www/tudominio", "LLAVE": "~/ruta/llave.pem", "DOMINIO": "tudominio.com"}
    IP=… USUARIO=… CARPETA_WEB=… LLAVE=… DOMINIO=… python3 publicar_actualizacion.py
Los archivos quedan en https://DOMINIO/ota/ (en los mandos, UPDATE_URL de config.py).
"""
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
PICO = os.path.join(HERE, "pico")
sys.path.insert(0, PICO)
import ed25519  # noqa: E402

PRODUCT = "knobeast"
PRIVATE = os.path.join(HERE, "firma", "knobeast_privada.key")
PUBLIC_PY = os.path.join(HERE, "firma", "clave_publica.py")   # edición oficial (privada de cada publicador)
OUT = os.path.join(HERE, "publicado")
try:
    _SRV = json.load(open(os.path.join(HERE, ".servidor.json")))
except (OSError, ValueError):
    _SRV = {}
def _srv(k, default=""):
    return os.environ.get(k) or _SRV.get(k) or default
SERVER = _srv("IP")                               # a dónde se entra por SSH
USER = _srv("USUARIO", "admin")
WEB = _srv("CARPETA_WEB", "/var/www/knobeast.com")
DOMAIN = _srv("DOMINIO", "knobeast.com")
KEY = os.path.expanduser(_srv("LLAVE"))
FOLDER = "ota"
URL = "https://%s/%s/" % (DOMAIN, FOLDER)
NET_PROTECTED = ("main.py", "config.py")          # igual que en ota.py
MICROPYTHON = "MicroPython (RPI_PICO2_W, versión estable usada por instalar_mac.sh)"


def fail(msg):
    sys.exit("\n✗ " + msg)


def create_keys():
    if os.path.exists(PRIVATE):
        print("Ya hay clave privada en %s (no la cambio)." % PRIVATE)
        secret = bytes.fromhex(open(PRIVATE).read().strip())
    else:
        os.makedirs(os.path.dirname(PRIVATE), exist_ok=True)
        secret = secrets.token_bytes(32)
        with open(PRIVATE, "w") as f:
            f.write(secret.hex() + "\n")
        os.chmod(PRIVATE, 0o600)
        print("Clave privada creada: %s  ← haz copia de seguridad y no la compartas" % PRIVATE)
    pub = ed25519.public_key(secret).hex()
    with open(PUBLIC_PY, "w") as f:
        f.write("# clave_publica.py — EDICIÓN OFICIAL: clave pública y dirección de las actualizaciones.\n"
                "# La privada está solo en el ordenador que publica (firma/knobeast_privada.key).\n"
                "PUBLIC = \"%s\"\nUPDATE_URL = \"%s\"\n" % (pub, URL))
    print("Clave pública escrita en %s" % PUBLIC_PY)


def src(name):
    """Archivo que va en la versión publicada: el de pico/, salvo la clave, que es la oficial."""
    return PUBLIC_PY if name == "clave_publica.py" else os.path.join(PICO, name)


def canonical(m):
    out = [m["product"], str(m["build"]), m["version"]]
    for f in sorted(m["files"], key=lambda f: f["name"]):
        out.append("%s %d %s" % (f["name"], f["size"], f["sha256"]))
    return ("\n".join(out) + "\n").encode()


def build_manifest():
    if not os.path.exists(PRIVATE):
        fail("No encuentro la clave privada %s.\nSi es la primera vez: python3 %s --crear-claves"
             % (PRIVATE, os.path.basename(__file__)))
    secret = bytes.fromhex(open(PRIVATE).read().strip())
    if not os.path.exists(PUBLIC_PY):
        fail("No encuentro %s. Créala con: python3 %s --crear-claves" % (PUBLIC_PY, os.path.basename(__file__)))
    pub = re.search(r'PUBLIC\s*=\s*"([0-9a-f]+)"', open(PUBLIC_PY).read()).group(1)
    if ed25519.public_key(secret).hex() != pub:
        fail("firma/clave_publica.py no corresponde a la clave privada. ¿Las has cambiado?")
    vtxt = open(os.path.join(PICO, "version.py")).read()
    version = re.search(r'VERSION\s*=\s*"([^"]+)"', vtxt).group(1)
    build = int(re.search(r'BUILD\s*=\s*(\d+)', vtxt).group(1))
    files = []
    for name in sorted(os.listdir(PICO)):
        if not name.endswith(".py") or name in NET_PROTECTED:
            continue
        data = open(src(name), "rb").read()
        compile(data, name, "exec")          # nada con errores de sintaxis
        files.append({"name": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    m = {"product": PRODUCT, "build": build, "version": version, "files": files}
    m["sig"] = ed25519.sign(secret, canonical(m)).hex()
    assert ed25519.verify(bytes.fromhex(pub), canonical(m), bytes.fromhex(m["sig"]))
    return m


def sbom(m):
    """Lista de componentes (CycloneDX) que pide la Ley de Ciberresiliencia."""
    return {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"component": {"type": "firmware", "name": "knobeast", "version": m["version"],
                                   "properties": [{"name": "build", "value": str(m["build"])}]}},
        "components": [
            {"type": "firmware", "name": "MicroPython", "description": MICROPYTHON,
             "licenses": [{"license": {"id": "MIT"}}], "purl": "pkg:github/micropython/micropython"},
            {"type": "library", "name": "Mbed TLS", "description": "Incluida en MicroPython",
             "licenses": [{"license": {"id": "Apache-2.0"}}]},
        ] + [{"type": "file", "name": f["name"], "hashes": [{"alg": "SHA-256", "content": f["sha256"]}]}
             for f in m["files"]],
    }


def prepare():
    m = build_manifest()
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    for f in m["files"]:
        shutil.copy(src(f["name"]), os.path.join(OUT, f["name"]))
    # paquete: todos los archivos seguidos, comprimidos (zlib, ventana de 4 KB para la Pico).
    # No va dentro de la firma: el mando comprueba cada archivo extraído con su sha256 firmado.
    raw = b"".join(open(src(f["name"]), "rb").read() for f in m["files"])
    c = zlib.compressobj(9, zlib.DEFLATED, 12)
    packed = c.compress(raw) + c.flush()
    bname = "knobeast-b%d.bin" % m["build"]
    open(os.path.join(OUT, bname), "wb").write(packed)
    m["bundle"] = {"file": bname, "format": "zlib", "size": len(packed),
                   "sha256": hashlib.sha256(packed).hexdigest(), "raw": len(raw)}
    print("Paquete %s: %d KB (sin comprimir %d KB)" % (bname, len(packed) // 1024, len(raw) // 1024))
    json.dump(sbom(m), open(os.path.join(OUT, "sbom.cdx.json"), "w"), indent=1)
    json.dump(m, open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    print("Versión %s (build %d): %d archivos firmados en %s" % (m["version"], m["build"], len(m["files"]), OUT))
    return m


def upload(m):
    if not SERVER or not KEY:
        fail("Falta el servidor: crea .servidor.json (ver arriba) o usa IP=… LLAVE=… (o --preparar para no subir)")
    ssh =["ssh", "-i", KEY, "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
           "-o", "StrictHostKeyChecking=accept-new", "%s@%s" % (USER, SERVER)]
    if not os.path.exists(KEY):
        fail("No encuentro la llave SSH %s" % KEY)
    os.chmod(KEY, 0o600)
    tmp = "/tmp/knobeast-ota"
    r = subprocess.run(ssh + ["rm -rf %s && mkdir -p %s" % (tmp, tmp)], capture_output=True, text=True)
    if r.returncode:
        fail("No puedo entrar por SSH a %s@%s:\n%s" % (USER, SERVER, r.stderr))
    files = [os.path.join(OUT, n) for n in os.listdir(OUT)]
    r = subprocess.run(["scp", "-q", "-i", KEY, "-o", "BatchMode=yes"] + files + ["%s@%s:%s/" % (USER, SERVER, tmp)],
                       capture_output=True, text=True)
    if r.returncode:
        fail("Falló la copia: %s" % r.stderr)
    # los .py primero y el manifest el último, para que nadie vea un manifest sin sus archivos
    script = """set -e
D="%s/%s"; NEW="%s"; sudo mkdir -p "$D"
sudo cp %s/*.py %s/*.bin %s/sbom.cdx.json "$D/"
sudo cp %s/manifest.json "$D/manifest.json.new" && sudo mv "$D/manifest.json.new" "$D/manifest.json"
for f in "$D"/knobeast-b*.bin; do [ "$(basename "$f")" = "$NEW" ] || sudo rm -f "$f"; done
sudo chmod 755 "$D"; sudo chmod 644 "$D"/*; rm -rf %s; echo subido""" % (WEB, FOLDER, m["bundle"]["file"],
                                                                         tmp, tmp, tmp, tmp, tmp)
    r = subprocess.run(ssh + ["bash", "-s"], input=script, capture_output=True, text=True)
    if "subido" not in r.stdout:
        fail("No se pudo copiar en %s/%s:\n%s" % (WEB, FOLDER, r.stderr))
    r = subprocess.run(["curl", "-fsSL", "-m", "20", URL + "manifest.json?x=%d" % os.getpid()],
                       capture_output=True, text=True)
    try:
        ok = json.loads(r.stdout)["sig"] == m["sig"]
    except Exception:
        ok = False
    if not ok:
        # ¿falta el HTTPS o las DNS? Comprobar directamente contra el servidor
        r2 = subprocess.run(["curl", "-fsSL", "-m", "20", "--resolve", "%s:80:%s" % (DOMAIN, SERVER),
                             "http://%s/%s/manifest.json" % (DOMAIN, FOLDER)], capture_output=True, text=True)
        try:
            ok2 = json.loads(r2.stdout)["sig"] == m["sig"]
        except Exception:
            ok2 = False
        if ok2:
            print("\n✓ Subida la versión %s (build %d) al servidor." % (m["version"], m["build"]))
            print("  Pero %s aún no responde por HTTPS (¿DNS o certificado pendientes?)." % URL)
            print("  Lanza knobeast-servidor.sh cuando las DNS apunten al servidor.")
            return
        fail("Subido, pero %smanifest.json no devuelve lo esperado.\n%s" % (URL, (r.stdout or r.stderr)[:300]))
    print("\n✓ Publicada la versión %s (build %d) en %s" % (m["version"], m["build"], URL))


if __name__ == "__main__":
    if "--crear-claves" in sys.argv:
        create_keys()
    elif "--preparar" in sys.argv:
        prepare()
    else:
        upload(prepare())
