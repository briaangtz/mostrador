# -*- coding: utf-8 -*-
"""
Publica una versión nueva de MOSTRADOR (para el que programa).

Hace todo de una:
  1. Sube el número de versión en ``version.py``.
  2. Compila ``MOSTRADOR.exe`` y ``Actualizador.exe``.
  3. Guarda el cambio de versión en el repositorio del código.
  4. Crea la release ``vX.Y.Z`` en el repositorio PÚBLICO con los ejecutables.

Uso: doble clic en "Publicar actualización.bat".
"""

import hashlib
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RAIZ)
import version as _v                                  # noqa: E402

RELEASES_REPO = _v.RELEASES_REPO
VERSION_PY = os.path.join(RAIZ, "version.py")
DIST = os.path.join(RAIZ, "dist")


def leer_version():
    with open(VERSION_PY, encoding="utf-8") as f:
        m = re.search(r'VERSION\s*=\s*"([^"]+)"', f.read())
    return m.group(1) if m else "0.0.0"


def escribir_version(nueva):
    with open(VERSION_PY, encoding="utf-8") as f:
        txt = f.read()
    txt = re.sub(r'(VERSION\s*=\s*")[^"]+(")', r"\g<1>%s\g<2>" % nueva, txt)
    with open(VERSION_PY, "w", encoding="utf-8") as f:
        f.write(txt)


def subir_patch(v):
    partes = v.split(".")
    while len(partes) < 3:
        partes.append("0")
    try:
        partes[-1] = str(int(partes[-1]) + 1)
    except ValueError:
        partes[-1] = "1"
    return ".".join(partes)


def correr(cmd, **kw):
    print("> " + " ".join(cmd))
    subprocess.run(cmd, check=True, **kw)


def main():
    actual = leer_version()
    print("Versión actual: %s\n" % actual)
    sugerida = subir_patch(actual)
    nueva = input("Nueva versión [%s]: " % sugerida).strip() or sugerida
    if not re.fullmatch(r"\d+(\.\d+)*", nueva):
        print("\nVersión inválida. Usá números separados por punto (ej. 1.0.1).")
        return 1

    escribir_version(nueva)
    print("version.py -> %s\n" % nueva)

    # 1) Compilar los dos ejecutables.
    #    --manifest app.manifest: sin elevación (asInvoker) y texto nítido
    #    en pantallas de alta resolución (hallazgo AppSec #6).
    #    --noupx: NO comprimir con UPX: los antivirus suelen tomar los
    #    binarios UPX como sospechosos (falsos positivos en la clientela).
    correr([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
            "--windowed", "--noupx", "--name", "MOSTRADOR",
            "--icon", "icono.ico", "--manifest", "app.manifest",
            "--add-data", "icono.ico;.", "main.py"], cwd=RAIZ)
    correr([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
            "--windowed", "--noupx", "--name", "Actualizador",
            "--manifest", "app.manifest", "actualizador.py"], cwd=RAIZ)

    # 1b) Revisión de las mitigaciones PE (ASLR/DEP) antes de publicar
    correr([sys.executable, os.path.join("tools", "pe_check.py"),
            os.path.join(DIST, "MOSTRADOR.exe"),
            os.path.join(DIST, "Actualizador.exe")], cwd=RAIZ)

    # 2) version.txt que viaja junto a la instalación
    with open(os.path.join(DIST, "version.txt"), "w", encoding="utf-8") as f:
        f.write(nueva + "\n")

    # 2b) SHA256SUMS.txt: el actualizador EXIGE este asset para instalar
    #     (sin él, o con el hash distinto, no reemplaza el programa).
    def _sha256(ruta):
        h = hashlib.sha256()
        with open(ruta, "rb") as f:
            for bloque in iter(lambda: f.read(1 << 20), b""):
                h.update(bloque)
        return h.hexdigest()

    nombres = ("MOSTRADOR.exe", "Actualizador.exe")
    lineas = ["%s  %s" % (_sha256(os.path.join(DIST, n)), n)
              for n in nombres if os.path.exists(os.path.join(DIST, n))]
    with open(os.path.join(DIST, "SHA256SUMS.txt"), "w",
              encoding="ascii", newline="\n") as f:
        f.write("\n".join(lineas) + "\n")
    hash_programa = lineas[0].split()[0] if lineas else "?"

    # 3) Guardar TODOS los cambios en el repo del código (privado)
    try:
        correr(["git", "add", "-A"], cwd=RAIZ)
        correr(["git", "commit", "-m", "Versión %s" % nueva], cwd=RAIZ)
        correr(["git", "push"], cwd=RAIZ)
    except subprocess.CalledProcessError as e:
        print("\n(Aviso: no se pudo subir el commit: %s)" % e)

    # 4) Crear la release en el repo público
    tag = "v" + nueva
    notas = ("Versión %s de MOSTRADOR.\n\n"
             "SHA256 de MOSTRADOR.exe: `%s`\n" % (nueva, hash_programa))
    correr(["gh", "release", "create", tag,
            os.path.join("dist", "MOSTRADOR.exe"),
            os.path.join("dist", "Actualizador.exe"),
            os.path.join("dist", "version.txt"),
            os.path.join("dist", "SHA256SUMS.txt"),
            "--repo", RELEASES_REPO,
            "--title", "MOSTRADOR %s" % nueva,
            "--notes", notas], cwd=RAIZ)

    print("\nLISTO: publicada la versión %s." % nueva)
    print("Las PC se actualizan solas la próxima vez que abran el programa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
