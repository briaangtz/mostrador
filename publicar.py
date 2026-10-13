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

    # 1) Compilar los dos ejecutables
    correr([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
            "--windowed", "--name", "MOSTRADOR", "--icon", "icono.ico",
            "--add-data", "icono.ico;.", "main.py"], cwd=RAIZ)
    correr([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
            "--windowed", "--name", "Actualizador", "actualizador.py"], cwd=RAIZ)

    # 2) version.txt que viaja junto a la instalación
    with open(os.path.join(DIST, "version.txt"), "w", encoding="utf-8") as f:
        f.write(nueva + "\n")

    # 3) Guardar TODOS los cambios en el repo del código (privado)
    try:
        correr(["git", "add", "-A"], cwd=RAIZ)
        correr(["git", "commit", "-m", "Versión %s" % nueva], cwd=RAIZ)
        correr(["git", "push"], cwd=RAIZ)
    except subprocess.CalledProcessError as e:
        print("\n(Aviso: no se pudo subir el commit: %s)" % e)

    # 4) Crear la release en el repo público
    tag = "v" + nueva
    correr(["gh", "release", "create", tag,
            os.path.join("dist", "MOSTRADOR.exe"),
            os.path.join("dist", "Actualizador.exe"),
            os.path.join("dist", "version.txt"),
            "--repo", RELEASES_REPO,
            "--title", "MOSTRADOR %s" % nueva,
            "--notes", "Versión %s de MOSTRADOR." % nueva], cwd=RAIZ)

    print("\nLISTO: publicada la versión %s." % nueva)
    print("Las PC se actualizan solas la próxima vez que abran el programa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
