# -*- coding: utf-8 -*-
"""Recupera el acceso cuando se olvidó el usuario o la contraseña.

Las contraseñas NO se pueden "ver": se guardan como hash (PBKDF2-SHA256
con sal de 32 bytes y 600.000 vueltas), así que no hay forma de leerlas ni
de revertirlas. Lo que sí se puede desde acá es **poner una nueva** con el
mismo hash que usa el programa, y **ver los nombres de usuario** (esos sí
se guardan tal cual).

La base vive en  %LOCALAPPDATA%\\Garrafas\\garrafas.db  (en la otra PC es
la misma ruta, dentro del Windows de esa máquina).

Uso (desde la carpeta del proyecto):

    python tools/recuperar_clave.py --listar
        Muestra los usuarios: nombre, rango, activo y último acceso.

    python tools/recuperar_clave.py --probar admin --password INTENTO
        Prueba una contraseña contra ese usuario sin modificar nada.

    python tools/recuperar_clave.py --usuario admin --password NUEVA
        Pone la contraseña NUEVA. Si no se pasa --password la pide por
        teclado (dos veces).

    --db "D:\\otra_pc\\Garrafas\\garrafas.db"
        Trabaja sobre OTRA base: la de la otra PC, copiada a un pendrive.
        Cerrá el programa en esa PC antes de copiarlo, y volvé a copiar el
        archivo cuando termine.

Antes de escribir deja una copia de seguridad del archivo al lado
(*.ante_cambio_AAAAMMDD_HHMMSS).

Si la contraseña que queda es la de fábrica (admin), el programa obliga a
elegir una propia en el próximo inicio de sesión.
"""
import argparse
import getpass
import os
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db          # noqa: E402


def _salir(mensaje):
    print("ERROR:", mensaje)
    sys.exit(1)


def _base(explicita=None):
    """Ruta de la base a usar, con una chequeada."""
    ruta = os.path.abspath(explicita) if explicita else db.DB_PATH
    if not os.path.isfile(ruta):
        _salir("no existe la base:\n       %s\n"
               "       Si es la de la otra PC, copiá garrafas.db a esta "
               "máquina y pasala con --db." % ruta)
    db.DB_PATH = ruta
    return ruta


def _respaldo(ruta):
    """Copia consistente de la base, al lado del original."""
    destino = "%s.ante_cambio_%s" % (
        ruta, datetime.now().strftime("%Y%m%d_%H%M%S"))
    origen = sqlite3.connect(ruta)
    try:
        copia = sqlite3.connect(destino)
        try:
            with copia:
                origen.backup(copia)
        finally:
            copia.close()
    finally:
        origen.close()
    return destino


def listar(_ruta):
    filas = db.listar_usuarios()
    if not filas:
        print("La base todavía no tiene usuarios.")
        return
    print("%-4s %-20s %-15s %-8s %s" % ("id", "usuario", "rango",
                                        "activo", "último acceso"))
    print("-" * 72)
    for u in filas:
        print("%-4s %-20s %-15s %-8s %s" % (
            u["id"], u["usuario"], u["rango"],
            "sí" if u["activo"] else "NO",
            u.get("ultimo_acceso") or "—"))
    print("\nLa contraseña no figura: se guarda hasheada y no se puede leer.")
    print("Para poner una nueva:  --usuario NOMBRE --password NUEVA")


def _usuario_de(nombre):
    u = db.usuario_por_nombre(nombre)
    if not u:
        nombres = ", ".join(x["usuario"] for x in db.listar_usuarios()) or "(ninguno)"
        _salir("no existe el usuario '%s'.  Los que hay: %s" % (nombre, nombres))
    if not u["activo"]:
        _salir("el usuario '%s' está dado de baja." % u["usuario"])
    return u


def probar(ruta, nombre, password):
    u = _usuario_de(nombre)
    if db._password_ok(u["password"], password):
        print("CORRECTA: '%s' entra con esa contraseña." % u["usuario"])
        return 0
    print("No: la contraseña '%s' no corresponde a '%s'."
          % (password, u["usuario"]))
    return 1


def cambiar(ruta, nombre, password):
    u = _usuario_de(nombre)
    if not password or len(str(password)) < 4:
        _salir("la contraseña debe tener al menos 4 caracteres.")
    copia = _respaldo(ruta)
    db.cambiar_password(u["id"], password)
    guardada = db.usuario_por_id(u["id"])["password"]
    if not db._password_ok(guardada, password):
        _salir("no quedó guardada; revisá la base. Copia de seguridad: %s"
               % copia)
    print("Listo: '%s' ya entra con la contraseña nueva." % u["usuario"])
    print("  Base: %s" % ruta)
    print("  Copia de seguridad previa: %s" % copia)
    if password == db.PASSWORD_POR_DEFECTO:
        print("  Ojo: dejaste la contraseña de fábrica (admin); el programa "
              "va a\n  obligarte a crear una propia apenas entres.")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Recupera el usuario/contraseña de MOSTRADOR (las claves "
                    "no se pueden leer, solo reponer).",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", metavar="RUTA",
                   help="ruta de garrafas.db (por defecto, la de esta PC)")
    p.add_argument("--listar", action="store_true",
                   help="muestra los usuarios de la base")
    p.add_argument("--probar", metavar="USUARIO",
                   help="prueba --password contra ese usuario, sin cambiar nada")
    p.add_argument("--usuario", metavar="USUARIO",
                   help="usuario al que poner la contraseña nueva")
    p.add_argument("--password", metavar="CLAVE",
                   help="contraseña (si se omite, la pide por teclado)")
    args = p.parse_args(argv)

    modos = bool(args.listar) + bool(args.probar) + bool(args.usuario)
    if modos != 1:
        p.error("elegí UN modo: --listar, --probar USUARIO o "
                "--usuario USUARIO [--password CLAVE]")

    password = args.password
    if not password and (args.probar or args.usuario):
        password = getpass.getpass("Contraseña: ")
        if args.usuario:
            repetir = getpass.getpass("Repetila:   ")
            if password != repetir:
                _salir("no coinciden.")

    if args.listar:
        return listar(_base(args.db)) or 0
    if args.probar:
        return probar(_base(args.db), args.probar, password)
    return cambiar(_base(args.db), args.usuario, password)


if __name__ == "__main__":
    sys.exit(main())
