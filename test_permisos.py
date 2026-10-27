# -*- coding: utf-8 -*-
"""Prueba la migración de permisos: usuarios con lista vieja reciben los
permisos nuevos; los quitados a propósito NO vuelven."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
from permisos import PERMISOS_VERSION

TMP = os.path.join(tempfile.gettempdir(), "garrafas_permisos_test.db")
if os.path.exists(TMP):
    os.remove(TMP)
db.DB_PATH = TMP

ok = 0


def check(cond, msg):
    global ok
    if not cond:
        raise AssertionError(msg)
    ok += 1
    print("  OK:", msg)


def fila(uid):
    import sqlite3
    con = sqlite3.connect(TMP)
    con.row_factory = sqlite3.Row
    r = con.execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone()
    con.close()
    return dict(r)


# ---- Base base: init crea admin ----
db.init()
admin = db.usuario_por_nombre("admin")
check(admin is not None, "init crea el admin")

# ---- 1. Usuario con lista VIEJA (sin pago_bono, sin versión) ----
import sqlite3
con = sqlite3.connect(TMP)
con.execute(
    "INSERT INTO usuarios (usuario, password, rango, activo, creado, permisos) "
    "VALUES ('viejo', 'x', 'USUARIO', 1, '2026-10-01', "
    "'abrir_caja,cerrar_caja,pago_efectivo,ventas')")   # sin permisos_v
con.commit()
con.close()
v1 = db.usuario_por_nombre("viejo")["id"]

db.init()   # re-inicializa → corre la migración
f = fila(v1)
check("pago_bono" in (f["permisos"] or ""),
      "lista vieja RECIBE pago_bono en la migración")
check(int(f["permisos_v"] or 0) == PERMISOS_VERSION,
      f"lista vieja queda marcada en versión {PERMISOS_VERSION}")
check("ventas" in f["permisos"] and "pago_efectivo" in f["permisos"],
      "los permisos que ya tenía se conservan")

# ---- 2. Usuario que le quitaron pago_bono a propósito (versión actual) ----
con = sqlite3.connect(TMP)
con.execute(
    "INSERT INTO usuarios (usuario, password, rango, activo, creado, "
    "permisos, permisos_v) VALUES ('sin_bono', 'x', 'USUARIO', 1, "
    f"'2026-10-25', 'abrir_caja,pago_efectivo', {PERMISOS_VERSION})")
con.commit()
con.close()
v2 = db.usuario_por_nombre("sin_bono")["id"]

db.init()
f2 = fila(v2)
check("pago_bono" not in (f2["permisos"] or ""),
      "quitado a propósito NO vuelve a aparecer")

# ---- 3. Guardar permisos nueva versión ----
db.set_permisos_usuario(v2, ["abrir_caja", "pago_bono"])
f3 = fila(v2)
check("pago_bono" in f3["permisos"]
      and int(f3["permisos_v"]) == PERMISOS_VERSION,
      "set_permisos_usuario guarda la lista y la versión")

db.actualizar_usuario(v2, permisos=["abrir_caja"])
f4 = fila(v2)
check("pago_bono" not in f4["permisos"]
      and int(f4["permisos_v"]) == PERMISOS_VERSION,
      "actualizar_usuario guarda versión actual (permiso quitado se respeta)")

# ---- 4. El permiso funciona en la práctica ----
db.set_permisos_usuario(v2, ["abrir_caja", "pago_bono", "ventas"])
db.set_config("sesion", str(v2))
check(db.puede("pago_bono") is True,
      "el usuario con pago_bono asignado PUEDE cobrar con BONO")
db.set_permisos_usuario(v2, ["abrir_caja", "ventas"])
check(db.puede("pago_bono") is False,
      "sin pago_bono en su lista NO puede cobrar con BONO")

# ---- 5. Usuario sin permisos propios sigue al rango ----
con = sqlite3.connect(TMP)
con.execute(
    "INSERT INTO usuarios (usuario, password, rango, activo, creado) "
    "VALUES ('rango', 'xxxx', 'USUARIO', 1, '2026-10-26')")
con.commit()
con.close()
r = db.usuario_por_nombre("rango")
check(r["permisos"] is None, "usuario sin lista propia queda en NULL")
db.set_config("sesion", str(r["id"]))
check(db.puede("pago_bono") is True,
      "usuario que sigue los permisos de su rango PUEDE cobrar con BONO")

os.remove(TMP)
print(f"\nTODAS LAS PRUEBAS DE PERMISOS PASARON ({ok} verificaciones)")
