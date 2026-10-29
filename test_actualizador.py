# -*- coding: utf-8 -*-
"""Prueba la comprobación de integridad del actualizador (hallazgo AppSec #1):
sin SHA256SUMS.txt o con hash distinto, NO se reemplaza el programa."""
import hashlib
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Consola Windows (cp1252): sin esto, imprimir "…" corta la ejecución.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import actualizador as ac

ok = 0


def check(cond, msg):
    global ok
    if not cond:
        raise AssertionError(msg)
    ok += 1
    print("  OK:", msg)


# ---------------------------------------------------------------- utilidades
def sha256_txt(bloques):
    return hashlib.sha256(bloques).hexdigest()


def entorno():
    """Carpeta temporal con un MOSTRADOR.exe 'viejo' instalado."""
    base = tempfile.mkdtemp(prefix="acctest_")
    with open(os.path.join(base, "MOSTRADOR.exe"), "wb") as f:
        f.write(b"EXE VIEJO")
    return base


aviso_llamado = []


def instalar_red(base, contenido_exe, texto_sums):
    """Reemplaza la red por dobles que escriben en la carpeta de prueba."""
    ac.BASE = base
    ac.pedir_json = lambda url: {
        "tag_name": "v9.9.9",
        "assets": [
            {"name": "MOSTRADOR.exe",
             "browser_download_url": "https://x/MOSTRADOR.exe"},
        ] + ([{"name": "SHA256SUMS.txt",
               "browser_download_url": "https://x/SHA256SUMS.txt"}]
             if texto_sums is not None else []),
    }

    def _bajar(url, destino):
        with open(destino, "wb") as f:
            f.write(contenido_exe)

    ac.bajar = _bajar
    ac.bajar_texto = lambda url: texto_sums
    aviso_llamado.clear()
    ac.aviso = lambda t, m, i=0x40: aviso_llamado.append((t, str(m), i))


def log_de(base):
    ruta = os.path.join(base, ac.LOG_FILE)
    if not os.path.exists(ruta):
        return ""
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def ruta_exe(base):
    return os.path.join(base, "MOSTRADOR.exe")


def contenido_exe(base):
    with open(ruta_exe(base), "rb") as f:
        return f.read()


# ------------------------------------------------------------ url_segura
check(ac.url_segura("https://api.github.com/repos/x/releases"),
      "url_segura acepta la API de GitHub")
check(ac.url_segura("https://github.com/x/y/releases/download/v1/M.exe"),
      "url_segura acepta github.com")
check(ac.url_segura("https://objects.githubusercontent.com/abc"),
      "url_segura acepta los hosts de descarga de GitHub")
check(not ac.url_segura("http://api.github.com/repos/x"),
      "url_segura RECHAZA http (sin cifrar)")
check(not ac.url_segura("file:///C:/Windows/System32/calc.exe"),
      "url_segura rechaza file://")
check(not ac.url_segura("https://evil.com/api.github.com"),
      "url_segura rechaza un host que solo CONTIENE github.com")
check(not ac.url_segura("https://github.com.evil.com/x"),
      "url_segura rechaza el truco github.com.evil.com")
check(not ac.url_segura(""),
      "url_segura rechaza la URL vacía")

# Las tres funciones de red rechazan la URL ANTES de abrirla
_base_url = entorno()
for _nombre, _fn in (("bajar",
                      lambda: ac.bajar("file:///C:/calc.exe",
                                       os.path.join(_base_url, "x"))),
                     ("bajar_texto",
                      lambda: ac.bajar_texto("http://inseguro.com/SUMS")),
                     ("pedir_json",
                      lambda: ac.pedir_json("ftp://raro.com/api"))):
    try:
        _fn()
        check(False, "%s debería haber rechazado la URL" % _nombre)
    except ValueError:
        check(True, "%s rechaza la URL no permitida antes de tocar la red"
              % _nombre)
check(not os.path.exists(os.path.join(_base_url, "x")),
      "no se escribió ningún archivo con la URL rechazada")
shutil.rmtree(_base_url, ignore_errors=True)

# ------------------------------------------------------------- sha256_de
base = entorno()
check(ac.sha256_de(ruta_exe(base)) == sha256_txt(b"EXE VIEJO"),
      "sha256_de calcula el hash del contenido del archivo")
grande_bin = os.path.join(base, "grande.bin")
with open(grande_bin, "wb") as f:
    f.write(b"x" * (3 * (1 << 20) + 17))       # más de un bloque de 1 MB
check(ac.sha256_de(grande_bin) == sha256_txt(b"x" * (3 * (1 << 20) + 17)),
      "sha256_de procesa archivos de más de 1 MB por bloques")
shutil.rmtree(base, ignore_errors=True)

# ---------------------------------------------------------- hash_esperado
_h1, _h2 = "a" * 64, "B" * 64
sums = "%s  MOSTRADOR.exe\n%s *Actualizador.exe\n" % (_h1, _h2)
check(ac.hash_esperado(sums, "MOSTRADOR.exe") == _h1,
      "hash_esperado lee la línea con doble espacio")
check(ac.hash_esperado(sums, "Actualizador.exe") == _h2.lower(),
      "hash_esperado acepta el formato binario '*' y normaliza a minúsculas")
check(ac.hash_esperado(sums, "OTRO.exe") is None,
      "hash_esperado devuelve None si el archivo no figura")
check(ac.hash_esperado("", "MOSTRADOR.exe") is None,
      "hash_esperado devuelve None con el archivo vacío")
check(ac.hash_esperado("no-es-hash  MOSTRADOR.exe\n", "MOSTRADOR.exe") is None,
      "hash_esperado rechaza una línea sin hash de 64 hexadecimales")

# ------------------------------------------- actualizar() SIN el archivo
base = entorno()
instalar_red(base, b"EXE NUEVO", None)
check(ac.actualizar() is False,
      "sin SHA256SUMS.txt en la release no se actualiza")
check(contenido_exe(base) == b"EXE VIEJO",
      "sin SHA256SUMS.txt el programa viejo queda intacto")
check("CANCELADA" in log_de(base),
      "el log deja constancia de la cancelación por seguridad")
check(any(i == 0x30 for _t, _m, i in aviso_llamado),
      "al usuario se lo avisa con una alerta (no un cartel informativo)")
shutil.rmtree(base, ignore_errors=True)

# --------------------------------------- actualizar() con hash INCORRECTO
base = entorno()
_malo = sha256_txt(b"OTRO CONTENIDO")
instalar_red(base, b"EXE NUEVO FALSO",
             "%s  MOSTRADOR.exe\n" % _malo)
check(ac.actualizar() is False,
      "con el hash distinto no se actualiza")
check(contenido_exe(base) == b"EXE VIEJO",
      "con el hash distinto el programa viejo queda intacto")
check(not os.path.exists(os.path.join(base, "MOSTRADOR.exe.download")),
      "la descarga fallida se elimina del disco")
check("NO coincide" in log_de(base),
      "el log registra el desajuste de hash")
check(any("hash publicado" in m for _t, m, _i in aviso_llamado),
      "al usuario se lo avisa que la descarga no coincide")
shutil.rmtree(base, ignore_errors=True)

# --------------------------------------------- actualizar() con hash OK
base = entorno()
_bueno = b"EXE NUEVO VERIFICADO"
instalar_red(base, _bueno, "%s  MOSTRADOR.exe\n" % sha256_txt(_bueno))
check(ac.actualizar() is True,
      "con el hash correcto la actualización se instala")
check(contenido_exe(base) == _bueno,
      "el ejecutable nuevo quedó reemplazado")
with open(os.path.join(base, ac.VERSION_FILE), encoding="utf-8") as f:
    check(f.read().strip() == "9.9.9", "quedó registrada la versión nueva")
check(not os.path.exists(os.path.join(base, "MOSTRADOR.exe.download")),
      "no quedan archivos temporales colgados")
shutil.rmtree(base, ignore_errors=True)

print("\nTODAS LAS PRUEBAS DEL ACTUALIZADOR PASARON (%d verificaciones)"
      % ok)
