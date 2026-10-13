# -*- coding: utf-8 -*-
"""
Actualizador automático de MOSTRADOR.

Va colocado junto a ``MOSTRADOR.exe`` (compilado como ``Actualizador.exe``).
Al abrirlo:

  1. Consulta en GitHub cuál es la última versión publicada.
  2. Si hay una más nueva, descarga SOLO el ejecutable del programa.
  3. Respalda ``garrafas.db`` en ``respaldos/`` (por las dudas).
  4. Reemplaza ``MOSTRADOR.exe``.
  5. Abre el programa.

La base de datos, los respaldos y las fotos NUNCA forman parte de la
actualización: se quedan intactos en cada PC.

En las PC, el acceso directo debe apuntar a ESTE archivo (``Actualizador.exe``),
no al programa directamente.
"""

import ctypes
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime

RELEASES_REPO = "briaangtz/mostrador-releases"
EXE_NAME = "MOSTRADOR.exe"
VERSION_FILE = "version.txt"
LOG_FILE = "actualizaciones.log"

API_URL = "https://api.github.com/repos/" + RELEASES_REPO + "/releases/latest"
TIMEOUT = 20
TIMEOUT_DESCARGA = 180


def carpeta_base():
    """Carpeta donde están los ejecutables (junto a la base de datos)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


BASE = carpeta_base()


def log(texto):
    """Deja constancia de lo que pasó (para poder revisarlo si algo falla)."""
    try:
        with open(os.path.join(BASE, LOG_FILE), "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                  texto))
    except OSError:
        pass


def aviso(titulo, mensaje, icono=0x40):
    """Muestra un cartel de Windows (0x10 error, 0x30 alerta, 0x40 info)."""
    try:
        ctypes.windll.user32.MessageBoxW(0, str(mensaje), str(titulo), icono)
    except Exception:
        pass


def leer_version_local():
    try:
        with open(os.path.join(BASE, VERSION_FILE), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"


def guardar_version_local(v):
    try:
        with open(os.path.join(BASE, VERSION_FILE), "w", encoding="utf-8") as f:
            f.write(v + "\n")
    except OSError as e:
        log("No se pudo escribir %s: %s" % (VERSION_FILE, e))


def tupla_version(v):
    partes = []
    for p in str(v).lstrip("vV").split("."):
        m = re.match(r"\d+", p)
        partes.append(int(m.group()) if m else 0)
    return tuple(partes) or (0,)


def es_mas_nueva(remota, local):
    a, b = tupla_version(remota), tupla_version(local)
    n = max(len(a), len(b))
    a = a + (0,) * (n - len(a))
    b = b + (0,) * (n - len(b))
    return a > b


def pedir_json(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "MOSTRADOR-Actualizador",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def bajar(url, destino):
    req = urllib.request.Request(
        url, headers={"User-Agent": "MOSTRADOR-Actualizador"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_DESCARGA) as r, \
            open(destino, "wb") as f:
        shutil.copyfileobj(r, f)


def respaldar_base():
    origen = os.path.join(BASE, "garrafas.db")
    if not os.path.exists(origen):
        return None
    carpeta = os.path.join(BASE, "respaldos")
    try:
        os.makedirs(carpeta, exist_ok=True)
        destino = os.path.join(
            carpeta,
            "pre_actualizacion_%s.db" % datetime.now().strftime("%Y%m%d_%H%M%S"))
        shutil.copy2(origen, destino)
        log("Base respaldada en %s" % destino)
        return destino
    except OSError as e:
        log("No se pudo respaldar la base: %s" % e)
        return None


def buscar_asset(assets):
    """Elige el ejecutable del programa (nunca el del actualizador)."""
    for a in assets:
        if a.get("name", "").lower() == EXE_NAME.lower():
            return a
    for a in assets:
        n = a.get("name", "").lower()
        if n.endswith(".exe") and "mostrador" in n and "actualizador" not in n:
            return a
    return None


def abrir_programa():
    exe = os.path.join(BASE, EXE_NAME)
    if not os.path.exists(exe):
        aviso("MOSTRADOR",
              "No se encontró %s en esta carpeta." % EXE_NAME, 0x10)
        return
    try:
        subprocess.Popen([exe], cwd=BASE)
    except OSError as e:
        log("No se pudo abrir el programa: %s" % e)
        aviso("MOSTRADOR", "No se pudo abrir el programa.\n\n%s" % e, 0x10)


def actualizar():
    """Devuelve True si se instaló una versión nueva."""
    local = leer_version_local()
    try:
        rel = pedir_json(API_URL)
    except (urllib.error.URLError, OSError, ValueError) as e:
        log("Sin conexión o error consultando GitHub: %s" % e)
        return False

    remota = (rel.get("tag_name") or "").lstrip("vV")
    if not remota or not es_mas_nueva(remota, local):
        log("Sin novedades (local %s, remota %s)." % (local, remota))
        return False

    asset = buscar_asset(rel.get("assets") or [])
    if not asset:
        log("La versión nueva no trae el ejecutable.")
        return False

    log("Actualizando %s -> %s" % (local, remota))
    temp = os.path.join(BASE, EXE_NAME + ".download")
    nuevo = os.path.join(BASE, EXE_NAME + ".nuevo")
    try:
        bajar(asset["browser_download_url"], temp)
        if os.path.exists(nuevo):
            os.remove(nuevo)
        os.replace(temp, nuevo)
    except (urllib.error.URLError, OSError) as e:
        log("Error descargando: %s" % e)
        for p in (temp, nuevo):
            try:
                os.remove(p)
            except OSError:
                pass
        return False

    respaldar_base()

    exe = os.path.join(BASE, EXE_NAME)
    try:
        os.replace(nuevo, exe)          # reemplazo atómico
    except OSError as e:
        log("No se pudo reemplazar %s: %s" % (EXE_NAME, e))
        aviso("MOSTRADOR",
              "No se pudo actualizar el programa "
              "(puede que esté abierto).\n\n"
              "Se abrirá la versión que ya tenías.", 0x30)
        try:
            os.remove(nuevo)
        except OSError:
            pass
        return False

    guardar_version_local(remota)
    log("Actualizado a %s." % remota)
    return True


def main():
    try:
        actualizar()
    except Exception as e:          # nunca frenar la apertura del programa
        log("Error inesperado: %s" % e)
    abrir_programa()


if __name__ == "__main__":
    main()
