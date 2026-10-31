# -*- coding: utf-8 -*-
"""
Actualizador automático de MOSTRADOR.

Va colocado junto a ``MOSTRADOR.exe`` (compilado como ``Actualizador.exe``).
Al abrirlo:

  1. Consulta en GitHub cuál es la última versión publicada.
  2. Verifica la INTEGRIDAD de la descarga contra ``SHA256SUMS.txt``
     (asset de la release). Sin ese archivo o con el hash distinto,
     NO instala nada y se queda la versión actual.
  3. Si hay una más nueva, descarga SOLO el ejecutable del programa.
  4. Respalda ``garrafas.db`` en ``respaldos/`` (por las dudas).
  5. Reemplaza ``MOSTRADOR.exe``.
  6. Abre el programa.

La base de datos, los respaldos y las fotos NUNCA forman parte de la
actualización: se quedan intactos en cada PC.

OJO con los permisos: el programa suele estar en ``C:\\Program Files\\MOSTRADOR``
y este actualizador corre SIN elevación (``app.manifest`` es asInvoker),
así que ahí Windows no deja escribir nada. Por eso la descarga se hace en
``%TEMP%`` y, si el destino no admite escritura, se vuelve a lanzarse a sí
mismo pidiendo permiso de administrador (aviso de Control de Cuentas) para
hacer el reemplazo. Sin esa elevación la actualización era imposible.

En las PC, el acceso directo debe apuntar a ESTE archivo (``Actualizador.exe``),
no al programa directamente.
"""

import ctypes
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from util import carpeta_datos

RELEASES_REPO = "briaangtz/mostrador-releases"
EXE_NAME = "MOSTRADOR.exe"
VERSION_FILE = "version.txt"
LAST_INSTALLED_FILE = "last_installed.txt"
LOG_FILE = "actualizaciones.log"
SUMS_FILE = "SHA256SUMS.txt"

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


def carpeta_temp():
    """Carpeta donde SÍ se puede escribir sin permisos de administrador.

    El programa suele estar en ``C:\\Program Files\\MOSTRADOR`` y el
    actualizador corre SIN elevación (``app.manifest`` es asInvoker), así
    que ahí Windows no deja ni crear archivos. Por eso la descarga se hace
    en ``%TEMP%`` y recién después se intenta mover al destino.
    """
    return tempfile.gettempdir()


def puede_escribir_en(ruta):
    """¿Se puede crear/archivar un archivo en esa carpeta?"""
    prueba = os.path.join(ruta, ".permiso_%d.tmp" % os.getpid())
    try:
        with open(prueba, "w"):
            pass
        os.remove(prueba)
        return True
    except OSError:
        return False


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


def leer_last_installed():
    """Lee la última versión que se instaló realmente (para forzar actualizaciones)."""
    try:
        with open(os.path.join(BASE, LAST_INSTALLED_FILE), encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return "0.0.0"


def guardar_version_local(v):
    try:
        with open(os.path.join(BASE, VERSION_FILE), "w", encoding="utf-8") as f:
            f.write(v + "\n")
    except OSError as e:
        log("No se pudo escribir %s: %s" % (VERSION_FILE, e))


def guardar_last_installed(v):
    try:
        with open(os.path.join(BASE, LAST_INSTALLED_FILE), "w", encoding="utf-8") as f:
            f.write(v + "\n")
    except OSError as e:
        log("No se pudo escribir %s: %s" % (LAST_INSTALLED_FILE, e))


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


def url_segura(url):
    """¿La URL es https y de un host de confianza (GitHub)?

    Bandit marca todo ``urlopen`` (B310). Acá no alcanza con confiar en la
    API: la URL de descarga viene de la respuesta JSON, así que se valida
    esquema y host ANTES de tocar la red. Si mañana GitHub sirviera las
    descargas de otro host, hay que sumarlo a esta lista.
    """
    u = urllib.parse.urlparse(str(url))
    host = (u.hostname or "").lower()
    return (u.scheme == "https"
            and (host == "github.com"
                 or host.endswith(".github.com")
                 or host.endswith(".githubusercontent.com")))


def pedir_json(url):
    if not url_segura(url):
        raise ValueError("URL no permitida: %s" % url)
    req = urllib.request.Request(url, headers={
        "User-Agent": "MOSTRADOR-Actualizador",
        "Accept": "application/vnd.github+json",
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:   # nosec B310
        return json.loads(r.read().decode("utf-8"))


def bajar(url, destino):
    if not url_segura(url):
        raise ValueError("URL no permitida: %s" % url)
    req = urllib.request.Request(
        url, headers={"User-Agent": "MOSTRADOR-Actualizador"})
    r = urllib.request.urlopen(req, timeout=TIMEOUT_DESCARGA)   # nosec B310
    with r, open(destino, "wb") as f:
        shutil.copyfileobj(r, f)


def bajar_texto(url):
    """Descarga un archivo chico como texto (SHA256SUMS.txt)."""
    if not url_segura(url):
        raise ValueError("URL no permitida: %s" % url)
    req = urllib.request.Request(
        url, headers={"User-Agent": "MOSTRADOR-Actualizador"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:   # nosec B310
        return r.read().decode("utf-8", "replace")


def sha256_de(ruta):
    """Hash SHA-256 del contenido de un archivo (en bloques de 1 MB)."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def hash_esperado(texto_sums, nombre):
    """Devuelve el hash de 'nombre' dentro de un SHA256SUMS.txt, o None.

    Formato admitido (estilo coreutils):  <hex>  <archivo>
    también acepta el modo binario:      <hex> *<archivo>
    """
    objetivo = nombre.lower()
    for linea in texto_sums.splitlines():
        partes = linea.split()
        if len(partes) >= 2 and re.fullmatch(r"[0-9a-fA-F]{64}", partes[0]):
            if partes[-1].lstrip("*").lower() == objetivo:
                return partes[0].lower()
    return None


def respaldar_base():
    """Respalda la base ANTES de tocar el programa.

    La base NO vive junto al .exe: está en %LOCALAPPDATA%\\Garrafas
    (ver ``util.carpeta_datos``). Si la carpeta del .exe fuera de solo
    lectura igual se intenta el respaldo ahí, por si acaso.
    """
    origenes = [os.path.join(carpeta_datos(), "garrafas.db"),
                os.path.join(BASE, "garrafas.db")]
    for origen in origenes:
        if not os.path.exists(origen):
            continue
        carpeta = os.path.join(os.path.dirname(origen), "respaldos")
        try:
            os.makedirs(carpeta, exist_ok=True)
            destino = os.path.join(
                carpeta,
                "pre_actualizacion_%s.db"
                % datetime.now().strftime("%Y%m%d_%H%M%S"))
            shutil.copy2(origen, destino)
            log("Base respaldada en %s" % destino)
            return destino
        except OSError as e:
            log("No se pudo respaldar la base de %s: %s" % (origen, e))
    log("No se encontró ninguna base para respaldar.")
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
    """Devuelve True si se instaló una versión nueva.
    Compara contra last_installed (no contra version.txt) para permitir
    actualizaciones forzadas aunque version.txt diga una versión mayor (ej. 1.1)."""
    local = leer_version_local()
    last_installed = leer_last_installed()
    try:
        rel = pedir_json(API_URL)
    except (urllib.error.URLError, OSError, ValueError) as e:
        log("Sin conexión o error consultando GitHub: %s" % e)
        return False

    remota = (rel.get("tag_name") or "").lstrip("vV")
    if not remota or remota == last_installed:
        log("Sin novedades (instalada %s, remota %s)." % (last_installed, remota))
        return False

    assets = rel.get("assets") or []
    asset = buscar_asset(assets)
    if not asset:
        log("La versión nueva no trae el ejecutable.")
        return False

    # --- Integridad: sin SHA256SUMS.txt (o con hash distinto) NO se instala ---
    sums = next((a for a in assets
                 if str(a.get("name", "")).lower() == SUMS_FILE.lower()), None)
    if not sums:
        log("La release no trae %s: actualizacion CANCELADA por seguridad."
            % SUMS_FILE)
        aviso("MOSTRADOR",
              "No se pudo verificar la integridad de la actualización.\n"
              "Se mantiene la versión actual.", 0x30)
        return False
    try:
        texto_sums = bajar_texto(sums["browser_download_url"])
    except (urllib.error.URLError, OSError, ValueError) as e:
        log("No se pudo leer %s (%s): actualizacion cancelada."
            % (SUMS_FILE, e))
        return False
    esperado = hash_esperado(texto_sums, EXE_NAME)
    if not esperado:
        log("%s no incluye %s: actualizacion CANCELADA."
            % (SUMS_FILE, EXE_NAME))
        aviso("MOSTRADOR",
              "No se pudo verificar la integridad de la actualización.\n"
              "Se mantiene la versión actual.", 0x30)
        return False

    log("Actualizando %s -> %s" % (local, remota))
    # La descarga va a %TEMP%: en Program Files Windows no deja escribir
    # al actualizador (corre sin elevación), y ahí se rompía siempre.
    temp = os.path.join(carpeta_temp(), EXE_NAME + ".download")
    nuevo = os.path.join(carpeta_temp(), EXE_NAME + ".nuevo")
    try:
        bajar(asset["browser_download_url"], temp)
    except (urllib.error.URLError, OSError, ValueError) as e:
        log("Error descargando: %s" % e)
        for p in (temp, nuevo):
            try:
                os.remove(p)
            except OSError:
                pass
        return False

    # El binario descargado tiene que coincidir byte a byte con el hash publicado
    obtenido = sha256_de(temp)
    if not hmac.compare_digest(esperado, obtenido.lower()):
        log("Hash de %s NO coincide (esperado %s…, obtenido %s…): "
            "actualizacion CANCELADA."
            % (EXE_NAME, esperado[:12], obtenido[:12]))
        try:
            os.remove(temp)
        except OSError:
            pass
        aviso("MOSTRADOR",
              "La descarga no coincide con el hash publicado.\n"
              "Actualización cancelada; se mantiene la versión actual.",
              0x30)
        return False

    try:
        if os.path.exists(nuevo):
            os.remove(nuevo)
        os.replace(temp, nuevo)
    except OSError as e:
        log("No se pudo preparar el reemplazo: %s" % e)
        for p in (temp, nuevo):
            try:
                os.remove(p)
            except OSError:
                pass
        return False

    respaldar_base()

    exe = os.path.join(BASE, EXE_NAME)
    if not puede_escribir_en(BASE):
        # Caso típico: el programa está en Program Files y este proceso
        # corre sin permisos de administrador. Se pide elevación (UAC) y
        # un proceso hermano, YA elevado, hace el reemplazo.
        log("Sin permiso de escritura en %s: pidiendo elevación." % BASE)
        ok_elevado = pedir_elevacion(nuevo, exe, remota)
        if not ok_elevado:
            try:
                os.remove(nuevo)
            except OSError:
                pass
        return ok_elevado

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
    guardar_last_installed(remota)
    log("Actualizado a %s." % remota)
    return True


MODO_REEMPLAZAR = "--reemplazar"


def aplicar_reemplazo(nuevo, exe, version):
    """Mueve el .exe nuevo sobre el viejo. Corre ELEVADO (ver main)."""
    try:
        if os.path.exists(exe):
            os.replace(nuevo, exe)
        else:
            shutil.move(nuevo, exe)
    except OSError as e:
        log("Elevado: no se pudo reemplazar %s: %s" % (EXE_NAME, e))
        return 1
    guardar_version_local(version)
    guardar_last_installed(version)
    log("Actualizado a %s (con permisos de administrador)." % version)
    return 0


def _codigo_elevacion(args):
    """Lanza este mismo ejecutable elevado (UAC) y devuelve el código.

    Separado de ``pedir_elevacion`` para poder probarlo sin invocar de
    verdad el aviso de Control de Cuentas.
    """
    return ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, args, None, 1)


def pedir_elevacion(nuevo, exe, version):
    """Vuelve a lanzarse a sí mismo pidiendo permiso de administrador.

    Windows muestra el aviso de Control de Cuentas (UAC); si el usuario
    acepta, el proceso hermano corre elevado y ejecuta
    ``aplicar_reemplazo``. Se espera hasta 120 s a que consuma el archivo.

    Ojo: si el usuario CANCELA el aviso, ``ShellExecuteW`` devuelve 1223
    (ERROR_CANCELLED), que es mayor que 32, así que hay que chequearlo a
    parte del "menor o igual a 32" de las fallas normales.
    """
    if not getattr(sys, "frozen", False):
        log("Sin compilar no se puede pedir elevación.")
        return False
    args = '"%s" %s "%s" "%s" "%s"' % (
        sys.executable, MODO_REEMPLAZAR, nuevo, exe, version)
    try:
        codigo = int(_codigo_elevacion(args))
    except Exception as e:                      # pragma: no cover
        log("No se pudo pedir elevación: %s" % e)
        return False
    if codigo <= 32 or codigo == 1223:          # 1223 = ERROR_CANCELLED
        log("El usuario canceló el aviso de permisos (código %s)." % codigo)
        aviso("MOSTRADOR",
              "Se necesita permiso de administrador para actualizar.\n"
              "Se mantiene la versión actual.", 0x30)
        return False

    # El proceso elevado mueve el archivo: esperamos a que desaparezca.
    for _ in range(240):
        if not os.path.exists(nuevo):
            return True
        time.sleep(0.5)
    log("El proceso elevado no completó el reemplazo a tiempo.")
    return False


def main():
    if len(sys.argv) >= 5 and sys.argv[1] == MODO_REEMPLAZAR:
        sys.exit(aplicar_reemplazo(sys.argv[2], sys.argv[3], sys.argv[4]))
    try:
        actualizar()
    except Exception as e:          # nunca frenar la apertura del programa
        log("Error inesperado: %s" % e)
    abrir_programa()


if __name__ == "__main__":
    main()
