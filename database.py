# -*- coding: utf-8 -*-
"""
Capa de datos del sistema de control de caja de garrafas.
Usa SQLite (incluido en Python) y guarda todo en el archivo garrafas.db,
junto al programa.
"""

import os
import sys
import sqlite3
import hashlib
import secrets
import json
from contextlib import contextmanager
from datetime import datetime, date

from permisos import (puede as _puede_permiso, RANGOS,
                      PERMISOS as PERMISOS_BASE,
                      permisos_de as _permisos_de_rango,
                      PERMISOS_VERSION, pendientes as _pendientes)

# Carpeta de datos: junto al .exe si está compilado, o junto al código
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "garrafas.db")

# ---------------------------------------------------------------------------
# Constantes del negocio
# ---------------------------------------------------------------------------

# Denominaciones de billetes para el conteo físico (arqueo)
DENOMINACIONES = [100, 200, 500, 1000, 2000, 10000, 20000]

# Medios de pago
MEDIOS_PAGO = ["Efectivo", "Transferencia", "Tarjeta de débito", "Tarjeta de crédito", "BONO"]

# Columna del resumen asociada a cada medio de pago
CLAVE_MEDIO = {
    "Efectivo": "efectivo",
    "Transferencia": "transferencias",
    "Tarjeta de débito": "debito",
    "Tarjeta de crédito": "credito",
    "BONO": "bono",
}

# Permiso que se necesita para registrar un cobro con cada medio de pago
MEDIO_PERMISO = {
    "Efectivo": "pago_efectivo",
    "Transferencia": "pago_transferencia",
    "Tarjeta de débito": "pago_debito",
    "Tarjeta de crédito": "pago_credito",
    "BONO": "pago_bono",
}

# Productos iniciales (precios de ejemplo, se pueden cambiar en Configuración).
# Los 5 primeros son garrafas con gas; los "Envase ..." son envases sueltos,
# que se venden por separado de la carga de gas.
PRODUCTOS_BASE = [
    ("Garrafa 10 kg", 10000),
    ("Garrafa 15 kg", 15000),
    ("Garrafa ME", 16000),
    ("Garrafa 45 kg", 45000),
    ("Garrafa ECO PROPANO", 17000),
    ("Envase 10 kg", 8000),
    ("Envase 15 kg", 10000),
    ("Envase 45 kg", 20000),
    ("Envase ME", 11000),
    ("Envase ECO PROPANO", 12000),
]

# Renombres de productos en bases creadas con versiones anteriores
RENOMBROS_PRODUCTOS = {
    "Garrafa 15ME": "Garrafa ME",
}

PASSWORD_POR_DEFECTO = "admin"


# ---------------------------------------------------------------------------
# Conexión
# ---------------------------------------------------------------------------

@contextmanager
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Configuración general (clave/valor)
# ---------------------------------------------------------------------------

def get_config(clave, defecto=None):
    with db() as con:
        fila = con.execute("SELECT valor FROM config WHERE clave = ?", (clave,)).fetchone()
    return fila["valor"] if fila else defecto


def set_config(clave, valor):
    with db() as con:
        con.execute(
            "INSERT INTO config (clave, valor) VALUES (?, ?) "
            "ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor",
            (clave, str(valor)),
        )


def get_fondo_inicial():
    try:
        return float(get_config("fondo_inicial", "0") or 0)
    except ValueError:
        return 0.0


def set_fondo_inicial(valor):
    set_config("fondo_inicial", repr(float(valor)))


# ---------------------------------------------------------------------------
# Contraseña (guardada con sal, nunca en texto plano)
# ---------------------------------------------------------------------------

def _hash(sal, texto):
    return hashlib.sha256((sal + texto).encode("utf-8")).hexdigest()


def set_password(nueva):
    sal = secrets.token_hex(8)
    set_config("password", sal + "$" + _hash(sal, nueva))


def check_password(intento):
    guardado = get_config("password")
    if not guardado or "$" not in guardado:
        return False
    sal, h = guardado.split("$", 1)
    return _hash(sal, intento) == h


def _nuevo_hash(texto):
    """Genera un hash nuevo con sal aleatoria (formato sal$hash)."""
    sal = secrets.token_hex(8)
    return sal + "$" + _hash(sal, texto)


def _password_ok(guardado, intento):
    if not guardado or "$" not in guardado:
        return False
    sal, h = guardado.split("$", 1)
    return _hash(sal, intento) == h


# ---------------------------------------------------------------------------
# Usuarios, sesión, aperturas y registro de actividad
# ---------------------------------------------------------------------------

def listar_usuarios():
    with db() as con:
        filas = con.execute(
            "SELECT * FROM usuarios ORDER BY "
            "CASE rango WHEN 'DESARROLLADOR' THEN 0 ELSE 1 END, usuario"
        ).fetchall()
    return [dict(f) for f in filas]


def usuario_por_id(uid):
    with db() as con:
        fila = con.execute("SELECT * FROM usuarios WHERE id = ?", (uid,)).fetchone()
    return dict(fila) if fila else None


def usuario_por_nombre(nombre):
    with db() as con:
        fila = con.execute(
            "SELECT * FROM usuarios WHERE usuario = ? COLLATE NOCASE",
            ((nombre or "").strip(),),
        ).fetchone()
    return dict(fila) if fila else None


def validar_credenciales(usuario, password):
    """Devuelve el usuario (dict) si las credenciales son válidas y está activo."""
    u = usuario_por_nombre(usuario)
    if not u or not u["activo"]:
        return None
    if not _password_ok(u["password"], password or ""):
        return None
    return u


def crear_usuario(usuario, password, rango="USUARIO", permisos=None):
    """
    Alta de usuario. Devuelve el usuario creado o lanza ValueError.
    permisos: lista de permisos individuales (None = los del rango).
    """
    nombre = (usuario or "").strip()
    if not nombre:
        raise ValueError("El nombre de usuario no puede estar vacío.")
    if rango not in RANGOS:
        raise ValueError(f"Rango inválido: {rango}")
    if not password or len(str(password)) < 4:
        raise ValueError("La contraseña debe tener al menos 4 caracteres.")
    if usuario_por_nombre(nombre):
        raise ValueError("Ya existe un usuario con ese nombre.")
    valor_permisos = _valor_permisos(permisos, rango)
    with db() as con:
        cur = con.execute(
            "INSERT INTO usuarios (usuario, password, rango, activo, creado, "
            "permisos, permisos_v) VALUES (?, ?, ?, 1, ?, ?, ?)",
            (nombre, _nuevo_hash(str(password)), rango,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"), valor_permisos,
             PERMISOS_VERSION),
        )
        nuevo_id = cur.lastrowid
    detalle = f"{nombre} — rango {rango}"
    if valor_permisos:
        detalle += f" — {len(valor_permisos.split(','))} permisos asignados"
    log_actividad("Usuario creado", detalle)
    return usuario_por_id(nuevo_id)


def actualizar_usuario(uid, usuario=None, rango=None, activo=None, permisos=None):
    """Modifica datos de un usuario (nombre, rango, estado y/o permisos)."""
    actual = usuario_por_id(uid)
    if not actual:
        raise ValueError("El usuario no existe.")
    if rango is not None and rango not in RANGOS:
        raise ValueError(f"Rango inválido: {rango}")
    # No permitir que el sistema quede sin ningún DESARROLLADOR activo
    if (actual["rango"] == "DESARROLLADOR" and actual["activo"]
            and rango not in (None, "DESARROLLADOR")):
        otros = [x for x in listar_usuarios()
                 if x["id"] != uid and x["rango"] == "DESARROLLADOR" and x["activo"]]
        if not otros:
            raise ValueError("Debe existir al menos un DESARROLLADOR activo. "
                             "Creá otro usuario DESARROLLADOR antes de cambiar este.")
    nombre = (usuario or actual["usuario"]).strip()
    if usuario and usuario_por_nombre(nombre) and \
            usuario_por_nombre(nombre)["id"] != uid:
        raise ValueError("Ya existe un usuario con ese nombre.")

    rango_final = rango if rango is not None else actual["rango"]
    with db() as con:
        con.execute(
            "UPDATE usuarios SET usuario = ?, rango = ?, activo = ? WHERE id = ?",
            (nombre, rango_final,
             int(activo) if activo is not None else actual["activo"], uid),
        )
        if permisos is not None:
            con.execute("UPDATE usuarios SET permisos = ?, permisos_v = ? "
                        "WHERE id = ?",
                        (_valor_permisos(permisos, rango_final),
                         PERMISOS_VERSION, uid))
    cambios = []
    if nombre != actual["usuario"]:
        cambios.append(f"nombre → {nombre}")
    if rango and rango != actual["rango"]:
        cambios.append(f"rango → {rango}")
    if activo is not None and int(activo) != actual["activo"]:
        cambios.append("activado" if activo else "desactivado")
    if permisos is not None and rango_final != "DESARROLLADOR":
        cambios.append(f"{len([p for p in permisos if p in PERMISOS_BASE])} "
                       f"permisos asignados")
    if cambios:
        log_actividad("Usuario modificado", f"{actual['usuario']}: " + ", ".join(cambios))
    return usuario_por_id(uid)


def cambiar_password(uid, nueva):
    if not nueva or len(str(nueva)) < 4:
        raise ValueError("La contraseña debe tener al menos 4 caracteres.")
    u = usuario_por_id(uid)
    if not u:
        raise ValueError("El usuario no existe.")
    with db() as con:
        con.execute("UPDATE usuarios SET password = ? WHERE id = ?",
                    (_nuevo_hash(str(nueva)), uid))
    log_actividad("Contraseña modificada", f"Usuario: {u['usuario']}")


def eliminar_usuario(uid):
    """Elimina un usuario. No permite borrarse a sí mismo ni al último DESARROLLADOR."""
    u = usuario_por_id(uid)
    if not u:
        raise ValueError("El usuario no existe.")
    sesion = usuario_sesion()
    if sesion and sesion["id"] == uid:
        raise ValueError("No podés eliminar el usuario con el que estás conectado.")
    activos = [x for x in listar_usuarios()
               if x["rango"] == "DESARROLLADOR" and x["activo"]]
    if u["rango"] == "DESARROLLADOR" and (len(activos) <= 1):
        raise ValueError("No se puede eliminar el último DESARROLLADOR activo.")
    with db() as con:
        con.execute("DELETE FROM usuarios WHERE id = ?", (uid,))
    log_actividad("Usuario eliminado",
                  f"{u['usuario']} — rango {u['rango']}")


def iniciar_sesion(usuario, password):
    """Valida credenciales, guarda la sesión y devuelve el usuario, o None."""
    u = validar_credenciales(usuario, password)
    if not u:
        log_actividad("Inicio de sesión rechazado",
                      f"Usuario intentado: {(usuario or '').strip()}",
                      {"id": None, "usuario": "sistema"})
        return None
    set_config("sesion", str(u["id"]))
    with db() as con:
        con.execute("UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), u["id"]))
    log_actividad("Inicio de sesión", f"Usuario: {u['usuario']} ({u['rango']})", u)
    return usuario_por_id(u["id"])


def cerrar_sesion():
    u = usuario_sesion()
    set_config("sesion", "")
    if u:
        log_actividad("Cierre de sesión", f"Usuario: {u['usuario']}", u)


def usuario_sesion():
    """Usuario conectado (dict) o None. Descarta sesiones de usuarios borrados."""
    uid = get_config("sesion")
    if not uid:
        return None
    try:
        u = usuario_por_id(int(uid))
    except (TypeError, ValueError):
        return None
    if not u or not u["activo"]:
        set_config("sesion", "")
        return None
    return u


def puede(permiso, rango=None):
    """
    True si la sesión actual (o el rango indicado) tiene el permiso.

    Con rango explícito responde como ese rango (para consultas de la UI).
    Sin rango, aplica: DESARROLLADOR = siempre; si el usuario tiene permisos
    asignados uno por uno, esos; si no, los de su rango.
    """
    if rango is not None:
        return _puede_permiso(permiso, rango)
    u = usuario_sesion()
    if not u:
        return False
    if u["rango"] == "DESARROLLADOR":
        return True
    propios = permisos_explicitos(u["id"])
    if propios is not None:
        return permiso in propios
    return _puede_permiso(permiso, u["rango"])


def permisos_explicitos(uid):
    """Permisos asignados a mano a un usuario, o None si usa los de su rango."""
    u = usuario_por_id(uid)
    if not u or u.get("permisos") is None:
        return None
    return [p for p in str(u["permisos"]).split(",") if p]


def permisos_efectivos(uid):
    """Lista de permisos con los que realmente opera ese usuario."""
    u = usuario_por_id(uid)
    if not u:
        return []
    if u["rango"] == "DESARROLLADOR":
        return list(PERMISOS_BASE)
    propios = permisos_explicitos(uid)
    if propios is not None:
        return propios
    return _permisos_de_rango(u["rango"])


def _valor_permisos(permisos, rango):
    """Texto a guardar en usuarios.permisos (None = usar los del rango)."""
    if permisos is None or rango == "DESARROLLADOR":
        return None
    validos = {p for p in permisos if p in PERMISOS_BASE}
    return ",".join(sorted(validos))


def set_permisos_usuario(uid, permisos):
    """Asigna los permisos individuales de un usuario (lista de permisos)."""
    u = usuario_por_id(uid)
    if not u:
        raise ValueError("El usuario no existe.")
    valor = _valor_permisos(permisos, u["rango"])
    with db() as con:
        con.execute("UPDATE usuarios SET permisos = ?, permisos_v = ? "
                    "WHERE id = ?", (valor, PERMISOS_VERSION, uid))
    n = 0 if valor is None else len(valor.split(","))
    log_actividad("Permisos modificados",
                  f"{u['usuario']}: {n} permisos asignados")
    return usuario_por_id(uid)


def validar_password_sesion(password):
    """Valida la contraseña del usuario conectado actualmente."""
    u = usuario_sesion()
    if not u:
        return False
    return _password_ok(u["password"], password or "")


def log_actividad(accion, detalle="", usuario=None):
    """
    Registra una acción importante en el registro de actividad.
    usuario: dict de usuario, id numérico, o None (usa la sesión actual).
    """
    if isinstance(usuario, dict):
        uid = usuario.get("id")
        nombre = usuario.get("usuario") or "—"
    elif usuario is None:
        u = usuario_sesion()
        uid, nombre = (u["id"], u["usuario"]) if u else (None, "—")
    else:
        u2 = usuario_por_id(usuario)
        uid = usuario
        nombre = u2["usuario"] if u2 else "(usuario eliminado)"
    with db() as con:
        con.execute(
            "INSERT INTO actividad (usuario_id, usuario, accion, detalle, fecha_hora) "
            "VALUES (?, ?, ?, ?, ?)",
            (uid, nombre, accion, detalle,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def historial_actividad(limite=300):
    """Últimas acciones registradas, ordenadas de más reciente a más antigua."""
    with db() as con:
        filas = con.execute(
            "SELECT * FROM actividad ORDER BY id DESC LIMIT ?",
            (int(limite),),
        ).fetchall()
    return [dict(f) for f in filas]


def registrar_apertura(caja_id, monto_inicial=None):
    """Registra la apertura de una caja con el usuario de la sesión actual."""
    caja = get_caja_por_id(caja_id)
    u = usuario_sesion()
    monto = get_fondo_inicial() if monto_inicial is None else float(monto_inicial)
    ahora = datetime.now()
    with db() as con:
        con.execute(
            "INSERT INTO aperturas (caja_id, usuario_id, fecha, hora, monto_inicial) "
            "VALUES (?, ?, ?, ?, ?)",
            (caja_id, u["id"] if u else None, caja["fecha"] if caja else "",
             ahora.strftime("%H:%M:%S"), monto),
        )
    log_actividad(
        "Apertura de caja",
        f"Caja del {fecha_larga(caja['fecha']) if caja else '?'} — "
        f"monto inicial ${monto:,.0f}".replace(",", "."),
        u,
    )
    return True


def apertura_de(caja_id):
    """Primera apertura registrada de la caja (usuario, fecha, hora, monto)."""
    with db() as con:
        fila = con.execute(
            """
            SELECT a.*, COALESCE(u.usuario, '(usuario eliminado)') AS usuario
            FROM aperturas a
            LEFT JOIN usuarios u ON u.id = a.usuario_id
            WHERE a.caja_id = ?
            ORDER BY a.id
            LIMIT 1
            """,
            (caja_id,),
        ).fetchone()
    return dict(fila) if fila else None


# ---------------------------------------------------------------------------
# Foto de perfil de cada usuario (imagen elegida desde el escritorio)
# ---------------------------------------------------------------------------

def dir_perfiles():
    """Carpeta de fotos de perfil: siempre junto a garrafas.db."""
    ruta = os.path.join(BASE_DIR, "perfiles")
    os.makedirs(ruta, exist_ok=True)
    return ruta


def _nombre_foto(uid):
    """Archivo propio de cada usuario: usuario_<id>.png"""
    return f"usuario_{uid}.png"


def migrar_foto_legada():
    """
    Versiones anteriores tenían UNA sola foto para todos (config "foto_perfil").
    Se la asigna al primer usuario para que cada cuenta tenga la suya.
    """
    nombre_viejo = get_config("foto_perfil")
    if not nombre_viejo:
        return
    usuarios = listar_usuarios()
    origen = os.path.join(dir_perfiles(), os.path.basename(str(nombre_viejo)))
    if usuarios and os.path.exists(origen):
        primero = usuarios[0]
        if not primero.get("foto"):
            destino_nombre = _nombre_foto(primero["id"])
            destino = os.path.join(dir_perfiles(), destino_nombre)
            if os.path.abspath(origen) != os.path.abspath(destino):
                try:
                    import shutil
                    shutil.copyfile(origen, destino)
                except OSError:
                    destino_nombre = os.path.basename(origen)
            with db() as con:
                con.execute("UPDATE usuarios SET foto = ? WHERE id = ?",
                            (destino_nombre, primero["id"]))
    set_config("foto_perfil", "")


def foto_perfil(uid=None):
    """Ruta completa de la foto de perfil del usuario (por defecto: la sesión)."""
    if uid is None:
        u = usuario_sesion()
        uid = u["id"] if u else None
    if uid is None:
        return None
    u = usuario_por_id(uid)
    if not u or not u.get("foto"):
        return None
    ruta = os.path.join(dir_perfiles(), os.path.basename(str(u["foto"])))
    return ruta if os.path.exists(ruta) else None


def set_foto_perfil(ruta_origen, uid=None):
    """Copia la imagen elegida (jpg/png/bmp/ico…) como foto del usuario."""
    from PIL import Image

    if uid is None:
        u = usuario_sesion()
        uid = u["id"] if u else None
    if uid is None:
        raise ValueError("No hay ningún usuario conectado.")
    u = usuario_por_id(uid)
    if not u:
        raise ValueError("El usuario no existe.")

    img = Image.open(ruta_origen)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    img.thumbnail((320, 320))
    nombre = _nombre_foto(uid)
    destino = os.path.join(dir_perfiles(), nombre)
    img.save(destino, "PNG")
    with db() as con:
        con.execute("UPDATE usuarios SET foto = ? WHERE id = ?", (nombre, uid))
    log_actividad("Foto de perfil actualizada",
                  f"Imagen: {os.path.basename(ruta_origen)}", usuario_sesion())
    return destino


def quitar_foto_perfil(uid=None):
    """Elimina la foto de perfil del usuario (por defecto: de la sesión)."""
    if uid is None:
        u = usuario_sesion()
        uid = u["id"] if u else None
    if uid is None:
        return
    u = usuario_por_id(uid)
    if not u or not u.get("foto"):
        return
    nombre = os.path.basename(str(u["foto"]))
    # Solo se borra el archivo si ningún otro usuario lo usa
    en_uso = any((x.get("foto") or "") == nombre
                 for x in listar_usuarios() if x["id"] != uid)
    if not en_uso:
        try:
            os.remove(os.path.join(dir_perfiles(), nombre))
        except OSError:
            pass
    with db() as con:
        con.execute("UPDATE usuarios SET foto = NULL WHERE id = ?", (uid,))
    log_actividad("Foto de perfil eliminada", "", usuario_sesion())


# ---------------------------------------------------------------------------
# Inicialización
# ---------------------------------------------------------------------------

def init():
    with db() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS productos (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT    NOT NULL,
                precio REAL    NOT NULL DEFAULT 0,
                activo INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS cajas (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha    TEXT NOT NULL UNIQUE,
                estado   TEXT NOT NULL DEFAULT 'abierta',
                creado   TEXT
            );

            -- Una venta es un TICKET: puede llevar varios productos
            -- (venta_items) y abonarse con varios medios de pago
            -- (venta_pagos), siempre que la suma de los pagos dé el total.
            CREATE TABLE IF NOT EXISTS ventas (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                caja_id        INTEGER NOT NULL REFERENCES cajas(id),
                fecha_hora     TEXT    NOT NULL,
                cliente        TEXT,
                total          REAL    NOT NULL,
                registrada_por INTEGER
            );

            CREATE TABLE IF NOT EXISTS venta_items (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id        INTEGER NOT NULL,
                producto_id     INTEGER NOT NULL,
                cantidad        INTEGER NOT NULL,
                precio_unitario REAL    NOT NULL,
                subtotal        REAL    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS venta_pagos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id    INTEGER NOT NULL,
                medio       TEXT    NOT NULL,
                importe     REAL    NOT NULL,
                comprobante TEXT
            );

            CREATE TABLE IF NOT EXISTS cierres (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                caja_id            INTEGER NOT NULL REFERENCES cajas(id),
                fecha              TEXT NOT NULL,
                hora_cierre        TEXT,
                total_garrafas     INTEGER DEFAULT 0,
                total_vendido      REAL DEFAULT 0,
                efectivo_esperado  REAL DEFAULT 0,
                efectivo_contado   REAL DEFAULT 0,
                transferencias     REAL DEFAULT 0,
                debito             REAL DEFAULT 0,
                credito            REAL DEFAULT 0,
                total_general      REAL DEFAULT 0,
                diferencia         REAL DEFAULT 0,
                estado             TEXT,
                billetes           TEXT,
                activo             INTEGER NOT NULL DEFAULT 1,
                reabierta          INTEGER NOT NULL DEFAULT 0
            );

            -- Rendición por buzón: los datos cargados en la pestaña de la
            -- planilla (detalle, secciones, cheques, observaciones) y el
            -- conteo de billetes de la calculadora. Se guarda un solo
            -- registro por día; el contenido va en JSON para poder sumar
            -- campos sin migrar la tabla.
            CREATE TABLE IF NOT EXISTS rendiciones (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha       TEXT NOT NULL UNIQUE,
                datos       TEXT NOT NULL DEFAULT '{}',
                actualizada TEXT
            );

            CREATE TABLE IF NOT EXISTS config (
                clave TEXT PRIMARY KEY,
                valor TEXT
            );

            CREATE TABLE IF NOT EXISTS usuarios (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario       TEXT NOT NULL UNIQUE,
                password      TEXT NOT NULL,
                rango         TEXT NOT NULL DEFAULT 'USUARIO',
                activo        INTEGER NOT NULL DEFAULT 1,
                creado        TEXT,
                ultimo_acceso TEXT
            );

            CREATE TABLE IF NOT EXISTS aperturas (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                caja_id       INTEGER NOT NULL REFERENCES cajas(id),
                usuario_id    INTEGER,
                fecha         TEXT NOT NULL,
                hora          TEXT NOT NULL,
                monto_inicial REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS actividad (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                usuario    TEXT,
                accion     TEXT NOT NULL,
                detalle    TEXT,
                fecha_hora TEXT NOT NULL
            );
            """
        )

        # Ejes de las tablas de detalle de cada venta (ticket)
        con.executescript(
            """
            CREATE INDEX IF NOT EXISTS ix_items_venta
                ON venta_items(venta_id);
            CREATE INDEX IF NOT EXISTS ix_pagos_venta
                ON venta_pagos(venta_id);
            """
        )

        # Migración de bases creadas con versiones anteriores: la tabla vieja
        # guardaba UN producto y UN medio por venta. Ahora cada venta es un
        # TICKET con sus productos (venta_items) y sus formas de pago
        # (venta_pagos). Las ventas viejas se pasan al formato nuevo
        # conservando id, fecha, cliente, total y comprobante.
        columnas_ventas = {r["name"] for r in con.execute("PRAGMA table_info(ventas)")}
        if "producto_id" in columnas_ventas:
            if "comprobante" not in columnas_ventas:
                con.execute("ALTER TABLE ventas ADD COLUMN comprobante TEXT")
            if "registrada_por" not in columnas_ventas:
                con.execute("ALTER TABLE ventas ADD COLUMN registrada_por INTEGER")
            if "cliente" not in columnas_ventas:
                con.execute("ALTER TABLE ventas ADD COLUMN cliente TEXT")
            con.execute("ALTER TABLE ventas RENAME TO ventas_viejas")
            con.executescript(
                """
                CREATE TABLE ventas (
                    id             INTEGER PRIMARY KEY AUTOINCREMENT,
                    caja_id        INTEGER NOT NULL,
                    fecha_hora     TEXT    NOT NULL,
                    cliente        TEXT,
                    total          REAL    NOT NULL,
                    registrada_por INTEGER
                );

                INSERT INTO ventas (id, caja_id, fecha_hora, cliente, total,
                                    registrada_por)
                    SELECT id, caja_id, fecha_hora, cliente, total,
                           registrada_por
                    FROM ventas_viejas;

                INSERT INTO venta_items (venta_id, producto_id, cantidad,
                                         precio_unitario, subtotal)
                    SELECT id, producto_id, cantidad, precio_unitario, total
                    FROM ventas_viejas;

                INSERT INTO venta_pagos (venta_id, medio, importe, comprobante)
                    SELECT id, medio, total, comprobante
                    FROM ventas_viejas;

                DROP TABLE ventas_viejas;
                """
            )

        columnas_cierres = {r["name"] for r in con.execute("PRAGMA table_info(cierres)")}
        if "n_transferencias" not in columnas_cierres:
            con.execute("ALTER TABLE cierres ADD COLUMN n_transferencias INTEGER DEFAULT 0")
        if "cerrado_por" not in columnas_cierres:
            con.execute("ALTER TABLE cierres ADD COLUMN cerrado_por INTEGER")
        if "n_operaciones" not in columnas_cierres:
            con.execute("ALTER TABLE cierres ADD COLUMN n_operaciones INTEGER DEFAULT 0")
        if "comprobantes" not in columnas_cierres:
            con.execute("ALTER TABLE cierres ADD COLUMN comprobantes TEXT")
        if "bono" not in columnas_cierres:
            con.execute("ALTER TABLE cierres ADD COLUMN bono REAL DEFAULT 0")

        # Foto propia de cada usuario y permisos asignados uno por uno
        # (NULL en "permisos" = el usuario usa los permisos de su rango)
        columnas_usuarios = {r["name"] for r in con.execute("PRAGMA table_info(usuarios)")}
        if "foto" not in columnas_usuarios:
            con.execute("ALTER TABLE usuarios ADD COLUMN foto TEXT")
        if "permisos" not in columnas_usuarios:
            con.execute("ALTER TABLE usuarios ADD COLUMN permisos TEXT")
        # Versión de la lista de permisos de cada usuario: permite agregar
        # permisos nuevos (p. ej. pago_bono) a las listas guardadas en una
        # versión anterior, sin pisar los permisos quitados a propósito.
        if "permisos_v" not in columnas_usuarios:
            con.execute("ALTER TABLE usuarios ADD COLUMN permisos_v INTEGER "
                        "DEFAULT 1")
        for f in con.execute(
                "SELECT id, rango, permisos, permisos_v FROM usuarios "
                "WHERE permisos IS NOT NULL").fetchall():
            desde = int(f["permisos_v"] or 1)
            if desde >= PERMISOS_VERSION:
                continue
            lista = [p for p in (f["permisos"] or "").split(",") if p]
            extra = [p for p in _pendientes(desde, f["rango"])
                     if p not in lista]
            if extra:
                lista = sorted(set(lista) | set(extra))
            con.execute(
                "UPDATE usuarios SET permisos = ?, permisos_v = ? WHERE id = ?",
                (",".join(lista), PERMISOS_VERSION, f["id"]),
            )

        # Productos: renombra los antiguos y completa los que falten.
        # Se busca por nombre (activo o no) para no reanimar productos
        # que el usuario dio de baja.
        for viejo, nuevo in RENOMBROS_PRODUCTOS.items():
            repetido = con.execute(
                "SELECT 1 FROM productos WHERE nombre = ?", (nuevo,)
            ).fetchone()
            if not repetido:
                con.execute(
                    "UPDATE productos SET nombre = ? WHERE nombre = ?",
                    (nuevo, viejo),
                )
        existentes = {r["nombre"] for r in
                      con.execute("SELECT nombre FROM productos").fetchall()}
        faltantes = [(n, p) for n, p in PRODUCTOS_BASE if n not in existentes]
        if faltantes:
            con.executemany(
                "INSERT INTO productos (nombre, precio) VALUES (?, ?)", faltantes
            )

    # Semilla de configuración
    if get_config("fondo_inicial") is None:
        set_config("fondo_inicial", "0")
    if get_config("password") is None:
        set_password(PASSWORD_POR_DEFECTO)

    # Semilla de usuarios: el primero nace como DESARROLLADOR.
    # Si ya existía una contraseña de reapertura, se conserva tal cual (sal + hash).
    if not listar_usuarios():
        clave_vieja = get_config("password")
        hash_guardado = (clave_vieja if clave_vieja and "$" in clave_vieja
                         else _nuevo_hash(PASSWORD_POR_DEFECTO))
        with db() as con:
            con.execute(
                "INSERT INTO usuarios (usuario, password, rango, activo, creado) "
                "VALUES (?, ?, 'DESARROLLADOR', 1, ?)",
                ("admin", hash_guardado,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
        log_actividad("Sistema", "Primer usuario creado: admin (DESARROLLADOR)",
                      {"id": None, "usuario": "sistema"})

    # La foto única de versiones anteriores queda asignada al primer usuario
    migrar_foto_legada()


# ---------------------------------------------------------------------------
# Respaldos automáticos de la base de datos
# ---------------------------------------------------------------------------

# Cantidad de respaldos que se conservan (los más viejos se borran solos)
RESPALDOS_CONSERVAR = 60


def dir_respaldos():
    """Carpeta de respaldos: siempre junto a garrafas.db."""
    return os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), "respaldos")


def respaldos_existentes():
    """Lista ordenada (más viejo primero) de los respaldos guardados."""
    carpeta = dir_respaldos()
    if not os.path.isdir(carpeta):
        return []
    nombres = [n for n in os.listdir(carpeta)
               if n.lower().startswith("garrafas_") and n.lower().endswith(".db")]
    nombres.sort()
    return [os.path.join(carpeta, n) for n in nombres]


def respaldar(motivo="manual"):
    """
    Crea una copia consistente de garrafas.db dentro de respaldos/.
    Usa el sistema de copia de SQLite (seguro aunque haya datos en uso).
    Devuelve la ruta del archivo creado.
    """
    carpeta = dir_respaldos()
    os.makedirs(carpeta, exist_ok=True)

    marca = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    destino = os.path.join(carpeta, f"garrafas_{marca}.db")
    n = 1
    while os.path.exists(destino):                 # respaldos en el mismo segundo
        destino = os.path.join(carpeta, f"garrafas_{marca}_{n}.db")
        n += 1

    origen = sqlite3.connect(DB_PATH)
    try:
        with sqlite3.connect(destino) as respaldo:
            origen.backup(respaldo)                # copia íntegra y consistente
    finally:
        origen.close()

    _podar_respaldos()
    log_actividad("Respaldo de base de datos",
                  f"{motivo} — {os.path.basename(destino)}")
    return destino


def respaldar_si_toca(motivo=""):
    """Respaldá solo si hoy todavía no hay ningún respaldo. Devuelve la ruta o None."""
    prefijo = "garrafas_" + date.today().isoformat()
    for ruta in respaldos_existentes():
        if os.path.basename(ruta).startswith(prefijo):
            return None
    return respaldar(motivo)


def _podar_respaldos():
    """Conserva solo los RESPALDOS_CONSERVAR respaldos más recientes."""
    archivos = respaldos_existentes()
    for ruta in archivos[:-RESPALDOS_CONSERVAR]:
        try:
            os.remove(ruta)
        except OSError:
            pass


def ultimo_respaldo():
    """Datos del respaldo más reciente, o None si todavía no hay."""
    archivos = respaldos_existentes()
    if not archivos:
        return None
    ruta = archivos[-1]
    st = os.stat(ruta)
    return {
        "archivo": ruta,
        "nombre": os.path.basename(ruta),
        "fecha": datetime.fromtimestamp(st.st_mtime),
        "tamano": st.st_size,
    }


def respaldo_automatico_activo():
    return get_config("respaldo_automatico", "1") == "1"


def set_respaldo_automatico(activo):
    set_config("respaldo_automatico", "1" if activo else "0")


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------

def productos(solo_activos=True):
    sql = "SELECT * FROM productos"
    if solo_activos:
        sql += " WHERE activo = 1"
    sql += " ORDER BY id"
    with db() as con:
        return [dict(r) for r in con.execute(sql).fetchall()]


def producto_por_id(pid):
    with db() as con:
        fila = con.execute("SELECT * FROM productos WHERE id = ?", (pid,)).fetchone()
    return dict(fila) if fila else None


def producto_por_nombre(nombre):
    with db() as con:
        fila = con.execute(
            "SELECT * FROM productos WHERE nombre = ? AND activo = 1", (nombre,)
        ).fetchone()
    return dict(fila) if fila else None


def actualizar_producto(pid, nombre, precio):
    with db() as con:
        con.execute(
            "UPDATE productos SET nombre = ?, precio = ? WHERE id = ?",
            (nombre.strip(), float(precio), pid),
        )


def crear_producto(nombre, precio):
    with db() as con:
        con.execute(
            "INSERT INTO productos (nombre, precio) VALUES (?, ?)",
            (nombre.strip(), float(precio)),
        )


def eliminar_producto(pid):
    """Marca el producto como inactivo (se conserva el histórico de ventas)."""
    with db() as con:
        con.execute("UPDATE productos SET activo = 0 WHERE id = ?", (pid,))


def es_envase(nombre):
    """
    True si el producto es un envase suelto (se vende sin gas) y no una
    garrafa con carga. Se decide por el nombre, así quien crea o renombra
    un producto desde Configuración no tiene que tocar nada más.
    """
    return (nombre or "").strip().lower().startswith("envase")


def productos_por_tipo(solo_activos=True):
    """(garrafas, envases) — dos listas de productos para informes."""
    garrafas, envases = [], []
    for p in productos(solo_activos):
        (envases if es_envase(p["nombre"]) else garrafas).append(p)
    return garrafas, envases


# ---------------------------------------------------------------------------
# Cajas (una por día)
# ---------------------------------------------------------------------------

def hoy():
    return date.today().isoformat()


def fecha_larga(iso):
    if not iso:
        return ""
    a, m, d = iso.split("-")
    return f"{d}/{m}/{a}"


def get_caja(fecha):
    with db() as con:
        fila = con.execute("SELECT * FROM cajas WHERE fecha = ?", (fecha,)).fetchone()
    return dict(fila) if fila else None


def crear_caja(fecha):
    """Crea la caja del día si no existe. La apertura se registra a mano
    con abrir_caja() desde el botón ABRIR CAJA de la pantalla Inicio."""
    existente = get_caja(fecha)
    if existente:
        return existente
    with db() as con:
        con.execute(
            "INSERT INTO cajas (fecha, estado, creado) VALUES (?, 'abierta', ?)",
            (fecha, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
    return get_caja(fecha)


def abrir_caja(caja_id, monto_inicial=None):
    """Registra la apertura manual de una caja (usuario, hora y monto inicial)."""
    caja = get_caja_por_id(caja_id)
    if not caja:
        raise ValueError("La caja no existe.")
    if caja["estado"] != "abierta":
        raise ValueError("La caja está cerrada: no se puede abrir.")
    if apertura_de(caja_id):
        raise ValueError("La caja ya fue abierta.")
    registrar_apertura(caja_id, monto_inicial)
    return apertura_de(caja_id)


def asegurar_caja(fecha):
    """Asegura que exista una caja para la fecha indicada."""
    return crear_caja(fecha)


def todas_las_cajas():
    with db() as con:
        filas = con.execute("SELECT * FROM cajas ORDER BY fecha DESC").fetchall()
    return [dict(f) for f in filas]


def cajas_abiertas():
    with db() as con:
        filas = con.execute(
            "SELECT * FROM cajas WHERE estado = 'abierta' ORDER BY fecha"
        ).fetchall()
    return [dict(f) for f in filas]


def caja_esta_abierta(caja_id):
    caja = get_caja_por_id(caja_id)
    return bool(caja) and caja["estado"] == "abierta"


def get_caja_por_id(caja_id):
    with db() as con:
        fila = con.execute("SELECT * FROM cajas WHERE id = ?", (caja_id,)).fetchone()
    return dict(fila) if fila else None


# ---------------------------------------------------------------------------
# Ventas = TICKETS: una venta puede tener varios productos (venta_items) y
# abonarse con uno o varios medios de pago (venta_pagos), siempre que la
# suma de los pagos dé exactamente el total de la venta.
# ---------------------------------------------------------------------------

def _items_de(con, venta_ids):
    """{venta_id: [item, ...]} con los productos de cada venta."""
    ids = list(venta_ids)
    if not ids:
        return {}
    comodines = ",".join("?" * len(ids))
    filas = con.execute(
        f"""
        SELECT i.*, p.nombre AS producto
        FROM venta_items i
        LEFT JOIN productos p ON p.id = i.producto_id
        WHERE i.venta_id IN ({comodines})
        ORDER BY i.id
        """,
        ids,
    ).fetchall()
    salida = {}
    for fila in filas:
        salida.setdefault(fila["venta_id"], []).append(dict(fila))
    return salida


def _pagos_de(con, venta_ids):
    """{venta_id: [pago, ...]} con las formas de pago de cada venta."""
    ids = list(venta_ids)
    if not ids:
        return {}
    comodines = ",".join("?" * len(ids))
    filas = con.execute(
        f"SELECT * FROM venta_pagos WHERE venta_id IN ({comodines}) ORDER BY id",
        ids,
    ).fetchall()
    salida = {}
    for fila in filas:
        salida.setdefault(fila["venta_id"], []).append(dict(fila))
    return salida


def texto_items(items):
    """'1 × Garrafa 10 kg + 2 × Garrafa 15 kg'."""
    return " + ".join(
        f"{i['cantidad']} × {i.get('producto') or 'Producto'}" for i in items
    )


def texto_pagos(pagos):
    """'Efectivo'  ·  'Efectivo + Tarjeta de débito'."""
    nombres = []
    for p in pagos:
        if p["medio"] not in nombres:
            nombres.append(p["medio"])
    return " + ".join(nombres)


def medio_principal(pagos):
    """Medio que aporta más importe (en empate, el primero cargado).

    Es el medio al que se le acreditan las UNIDADES de esa venta en los
    reportes; el dinero siempre se reparte exacto entre todos los medios.
    """
    if not pagos:
        return None
    mejor = pagos[0]
    for p in pagos[1:]:
        if float(p["importe"]) > float(mejor["importe"]):
            mejor = p
    return mejor["medio"]


def comprobante_de(pagos, medio=None):
    """N° de comprobante de un pago (si hay medio, el de ese medio)."""
    for p in pagos:
        if medio and p["medio"] != medio:
            continue
        if (p.get("comprobante") or "").strip():
            return p["comprobante"]
    return None


def _armar_ticket(fila, items, pagos):
    """Dict de una venta con sus productos, sus pagos y los datos
    heredados (producto, cantidad, medio...) que siguen usando los
    reportes y las pantallas."""
    v = dict(fila)
    items = items or []
    pagos = pagos or []
    un_solo = len(items) == 1
    primero = items[0] if items else None

    v["items"] = items
    v["pagos"] = pagos
    v["cantidad"] = sum(int(i["cantidad"]) for i in items)
    v["producto_id"] = primero["producto_id"] if un_solo else None
    v["producto"] = ((primero.get("producto") if un_solo
                      else texto_items(items)) or None)
    v["precio_unitario"] = float(primero["precio_unitario"]) if un_solo else None
    v["medio"] = medio_principal(pagos)
    v["medios_txt"] = texto_pagos(pagos)
    v["comprobante"] = (comprobante_de(pagos, "Transferencia")
                        or comprobante_de(pagos))
    return v


def _normalizar_items(items):
    """Valida y normaliza la lista de productos de un ticket."""
    salida = []
    for it in items or []:
        try:
            pid = int(it["producto_id"])
            cantidad = int(it["cantidad"])
            precio = float(it["precio_unitario"])
        except (TypeError, ValueError, KeyError):
            raise ValueError("Revisá el producto, la cantidad y el precio.")
        prod = producto_por_id(pid)
        if not prod:
            raise ValueError("El producto seleccionado ya no existe.")
        if cantidad <= 0:
            raise ValueError(
                f"La cantidad de {prod['nombre']} tiene que ser mayor a cero."
            )
        if precio <= 0:
            raise ValueError(
                f"El precio de {prod['nombre']} tiene que ser mayor a cero."
            )
        salida.append({
            "producto_id": pid,
            "cantidad": cantidad,
            "precio_unitario": precio,
            "subtotal": cantidad * precio,
            "producto": prod["nombre"],
        })
    if not salida:
        raise ValueError("La venta necesita al menos un producto.")
    return salida


def _normalizar_pagos(pagos, total):
    """Valida las formas de pago: medios válidos, importes > 0,
    comprobante obligatorio en transferencia y SUMA = total."""
    salida = []
    for pg in pagos or []:
        medio = str(pg.get("medio") or "").strip()
        try:
            importe = float(pg.get("importe") or 0)
        except (TypeError, ValueError):
            importe = 0.0
        comprobante = (pg.get("comprobante") or "").strip() or None
        if medio not in MEDIOS_PAGO:
            raise ValueError(f"Medio de pago no válido: {medio or '—'}.")
        if importe <= 0:
            raise ValueError(f"El importe en {medio} tiene que ser mayor a cero.")
        # El N° de comprobante de la transferencia es obligatorio y se pide
        # en la pantalla de ventas (ui_ventas); acá solo se guarda.
        salida.append({"medio": medio, "importe": importe,
                       "comprobante": comprobante})
    if not salida:
        raise ValueError("Falta indicar cómo se pagó la venta.")

    pagado = sum(p["importe"] for p in salida)
    if abs(pagado - float(total)) >= 0.01:
        diferencia = float(total) - pagado
        if diferencia > 0:
            raise ValueError(
                f"Faltan ${diferencia:,.0f} para completar la venta: "
                f"total ${float(total):,.0f} y ya se cargaron "
                f"${pagado:,.0f}.".replace(",", ".")
            )
        raise ValueError(
            f"Los pagos superan el total en ${-diferencia:,.0f}: "
            f"total ${float(total):,.0f} y se cargaron "
            f"${pagado:,.0f}.".replace(",", ".")
        )
    return salida


def _descripcion_ticket(t):
    """Texto de registro de actividad para una venta (ticket)."""
    texto = (f"#{t['id']} — {texto_items(t['items'])} — {t['medios_txt']} — "
             f"${t['total']:,.0f}".replace(",", "."))
    if t.get("comprobante"):
        texto += f" — Comprobante: {t['comprobante']}"
    if t.get("cliente"):
        texto += f" — Cliente: {t['cliente']}"
    return texto


def registrar_ticket(caja_id, items, pagos, cliente=None):
    """Registra una venta completa: uno o varios productos y una o varias
    formas de pago cuya suma da exactamente el total.

    items: [{"producto_id", "cantidad", "precio_unitario"}, ...]
    pagos: [{"medio", "importe", "comprobante"}, ...]
    Devuelve el ticket guardado (con id, total, items y pagos).
    """
    if not apertura_de(caja_id):
        raise ValueError(
            "La caja todavía no fue abierta. "
            "Presioná ABRIR CAJA antes de registrar ventas."
        )
    items_limpios = _normalizar_items(items)
    total = sum(i["subtotal"] for i in items_limpios)
    pagos_limpios = _normalizar_pagos(pagos, total)
    u = usuario_sesion()

    with db() as con:
        cur = con.execute(
            "INSERT INTO ventas (caja_id, fecha_hora, cliente, total, "
            "registrada_por) VALUES (?, ?, ?, ?, ?)",
            (caja_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             (cliente or "").strip() or None, total,
             u["id"] if u else None),
        )
        venta_id = cur.lastrowid
        con.executemany(
            "INSERT INTO venta_items (venta_id, producto_id, cantidad, "
            "precio_unitario, subtotal) VALUES (?, ?, ?, ?, ?)",
            [(venta_id, i["producto_id"], i["cantidad"], i["precio_unitario"],
              i["subtotal"]) for i in items_limpios],
        )
        con.executemany(
            "INSERT INTO venta_pagos (venta_id, medio, importe, comprobante) "
            "VALUES (?, ?, ?, ?)",
            [(venta_id, p["medio"], p["importe"], p["comprobante"])
             for p in pagos_limpios],
        )

    ticket = venta_por_id(venta_id)
    log_actividad("Venta registrada", _descripcion_ticket(ticket), u)
    return ticket


def registrar_venta(caja_id, producto_id, cantidad, precio_unitario, medio,
                    comprobante=None, cliente=None):
    """Atajo de UN producto y UN medio de pago. Devuelve el total
    (como en las versiones anteriores del sistema)."""
    total = float(cantidad) * float(precio_unitario)
    ticket = registrar_ticket(
        caja_id,
        [{"producto_id": producto_id, "cantidad": cantidad,
          "precio_unitario": precio_unitario}],
        [{"medio": medio, "importe": total, "comprobante": comprobante}],
        cliente=cliente,
    )
    return ticket["total"]


def ventas_de(caja_id):
    """Ventas (tickets) de una caja, con sus productos y sus pagos."""
    with db() as con:
        filas = con.execute(
            """
            SELECT v.*, COALESCE(u.usuario, '(usuario eliminado)') AS cajero
            FROM ventas v
            LEFT JOIN usuarios u ON u.id = v.registrada_por
            WHERE v.caja_id = ?
            ORDER BY v.id
            """,
            (caja_id,),
        ).fetchall()
        ids = [f["id"] for f in filas]
        items = _items_de(con, ids)
        pagos = _pagos_de(con, ids)
    return [_armar_ticket(f, items.get(f["id"], []), pagos.get(f["id"], []))
            for f in filas]


def eliminar_venta(venta_id):
    return eliminar_ventas([venta_id])


def eliminar_ventas(venta_ids):
    """Elimina varias ventas (tickets) de una sola vez. Devuelve cuántas
    borró. El registro de actividad se escribe con la transacción cerrada.
    """
    ids = [int(i) for i in venta_ids]
    if not ids:
        return 0
    comodines = ",".join("?" * len(ids))
    with db() as con:
        filas = con.execute(
            f"SELECT * FROM ventas WHERE id IN ({comodines})", ids
        ).fetchall()
        borradas = [f["id"] for f in filas]
        items = _items_de(con, borradas)
        pagos = _pagos_de(con, borradas)
        con.execute(f"DELETE FROM venta_items WHERE venta_id IN ({comodines})",
                    ids)
        con.execute(f"DELETE FROM venta_pagos WHERE venta_id IN ({comodines})",
                    ids)
        con.execute(f"DELETE FROM ventas WHERE id IN ({comodines})", ids)

    for f in filas:
        ticket = _armar_ticket(f, items.get(f["id"], []), pagos.get(f["id"], []))
        log_actividad("Venta eliminada", _descripcion_ticket(ticket))
    return len(filas)


def actualizar_ticket(venta_id, items, pagos, cliente=None):
    """Corrige una venta ya registrada: vuelve a cargar sus productos y
    sus formas de pago (recalcula el total)."""
    if not venta_por_id(venta_id):
        raise ValueError("La venta indicada ya no existe.")
    items_limpios = _normalizar_items(items)
    total = sum(i["subtotal"] for i in items_limpios)
    pagos_limpios = _normalizar_pagos(pagos, total)
    u = usuario_sesion()

    with db() as con:
        con.execute(
            "UPDATE ventas SET cliente = ?, total = ?, registrada_por = ? "
            "WHERE id = ?",
            ((cliente or "").strip() or None, total,
             u["id"] if u else None, venta_id),
        )
        con.execute("DELETE FROM venta_items WHERE venta_id = ?", (venta_id,))
        con.execute("DELETE FROM venta_pagos WHERE venta_id = ?", (venta_id,))
        con.executemany(
            "INSERT INTO venta_items (venta_id, producto_id, cantidad, "
            "precio_unitario, subtotal) VALUES (?, ?, ?, ?, ?)",
            [(venta_id, i["producto_id"], i["cantidad"], i["precio_unitario"],
              i["subtotal"]) for i in items_limpios],
        )
        con.executemany(
            "INSERT INTO venta_pagos (venta_id, medio, importe, comprobante) "
            "VALUES (?, ?, ?, ?)",
            [(venta_id, p["medio"], p["importe"], p["comprobante"])
             for p in pagos_limpios],
        )

    ticket = venta_por_id(venta_id)
    log_actividad("Venta modificada", _descripcion_ticket(ticket))
    return ticket


def actualizar_venta(venta_id, producto_id, cantidad, precio_unitario, medio,
                     comprobante=None, cliente=None):
    """Atajo para corregir una venta de UN producto y UN medio de pago.
    Devuelve el total."""
    ticket = actualizar_ticket(
        venta_id,
        [{"producto_id": producto_id, "cantidad": cantidad,
          "precio_unitario": precio_unitario}],
        [{"medio": medio, "importe": float(cantidad) * float(precio_unitario),
          "comprobante": comprobante}],
        cliente=cliente,
    )
    return ticket["total"]


def venta_por_id(venta_id):
    """Una venta (ticket) con sus productos y sus pagos, o None."""
    with db() as con:
        fila = con.execute(
            """
            SELECT v.*, COALESCE(u.usuario, '(usuario eliminado)') AS cajero
            FROM ventas v
            LEFT JOIN usuarios u ON u.id = v.registrada_por
            WHERE v.id = ?
            """,
            (venta_id,),
        ).fetchone()
        if not fila:
            return None
        items = _items_de(con, [venta_id]).get(venta_id, [])
        pagos = _pagos_de(con, [venta_id]).get(venta_id, [])
    return _armar_ticket(fila, items, pagos)


def resumen(caja_id):
    """
    Resumen completo de la caja:
      - ventas por producto (cantidad y total) sumando los ítems
      - totales por medio de pago sumando los pagos de cada ticket
      - totales generales
    """
    ventas = ventas_de(caja_id)
    nombres = {p["id"]: p["nombre"] for p in productos(solo_activos=False)}

    por_producto = {}
    for p in productos(solo_activos=True):
        por_producto[p["id"]] = {"nombre": p["nombre"], "cantidad": 0, "total": 0.0}

    medios = {clave: 0.0 for clave in CLAVE_MEDIO.values()}
    total_vendido = 0.0
    total_garrafas = 0
    transferencias_lista = []

    for v in ventas:
        # Unidades y dinero por producto: salen de los ítems del ticket
        for it in v["items"]:
            pid = it["producto_id"]
            if pid not in por_producto:
                por_producto[pid] = {
                    "nombre": it.get("producto") or nombres.get(pid, "Producto"),
                    "cantidad": 0,
                    "total": 0.0,
                }
            por_producto[pid]["cantidad"] += int(it["cantidad"])
            por_producto[pid]["total"] += float(it["subtotal"])
            total_garrafas += int(it["cantidad"])

        # Dinero por medio de pago: sale de los pagos (una venta mixta
        # reparte su total entre los medios que la cancelaron)
        for pg in v["pagos"]:
            clave = CLAVE_MEDIO.get(pg["medio"], "efectivo")
            medios[clave] += float(pg["importe"])
            if pg["medio"] == "Transferencia":
                transferencias_lista.append({
                    "id": v["id"],
                    "fecha_hora": v["fecha_hora"],
                    "comprobante": pg.get("comprobante") or "",
                    "producto": v["producto"],
                    "cantidad": v["cantidad"],
                    "total": float(pg["importe"]),
                    "medio": pg["medio"],
                })

        total_vendido += float(v["total"])

    fondo = get_fondo_inicial()
    ap = apertura_de(caja_id)
    if ap and ap["monto_inicial"] is not None:
        fondo = float(ap["monto_inicial"])
    efectivo_esperado = medios["efectivo"] + fondo
    total_general = sum(medios.values())

    return {
        "por_producto": por_producto,
        "ventas": ventas,
        "total_garrafas": total_garrafas,
        "total_vendido": total_vendido,
        "efectivo": medios["efectivo"],
        "transferencias": medios["transferencias"],
        "debito": medios["debito"],
        "credito": medios["credito"],
        "bono": medios["bono"],
        "efectivo_esperado": efectivo_esperado,
        "fondo": fondo,
        "total_general": total_general,
        "cantidad_ventas": len(ventas),
        "n_transferencias": len(transferencias_lista),
        "transferencias_detalle": transferencias_lista,
    }


# ---------------------------------------------------------------------------
# Estadísticas por rango de fechas
# ---------------------------------------------------------------------------

def ventas_rango(desde, hasta):
    """Ventas (tickets) de las cajas cuya fecha esté entre 'desde' y
    'hasta' (ISO), con sus productos y sus pagos."""
    with db() as con:
        filas = con.execute(
            """
            SELECT v.*, k.fecha AS fecha,
                   COALESCE(u.usuario, '(usuario eliminado)') AS cajero
            FROM ventas v
            JOIN cajas k ON k.id = v.caja_id
            LEFT JOIN usuarios u ON u.id = v.registrada_por
            WHERE k.fecha >= ? AND k.fecha <= ?
            ORDER BY k.fecha, v.id
            """,
            (desde, hasta),
        ).fetchall()
        ids = [f["id"] for f in filas]
        items = _items_de(con, ids)
        pagos = _pagos_de(con, ids)
    return [_armar_ticket(f, items.get(f["id"], []), pagos.get(f["id"], []))
            for f in filas]


def cierres_rango(desde, hasta):
    """Cierres vigentes dentro del rango de fechas (ISO)."""
    with db() as con:
        filas = con.execute(
            """
            SELECT * FROM cierres
            WHERE activo = 1 AND fecha >= ? AND fecha <= ?
            ORDER BY fecha
            """,
            (desde, hasta),
        ).fetchall()
    return [dict(f) for f in filas]


def estadisticas(desde, hasta):
    """
    Estadísticas consolidadas del rango [desde, hasta] (fechas ISO):
      totales, por producto, por medio de pago, evolución diaria y cierres.
    """
    ventas = ventas_rango(desde, hasta)

    por_producto = {}
    medios = {clave: 0.0 for clave in CLAVE_MEDIO.values()}
    dias = {}
    n_transferencias = 0
    transferencias = []
    total_vendido = 0.0
    total_garrafas = 0

    for v in ventas:
        for it in v["items"]:
            pid = it["producto_id"]
            if pid not in por_producto:
                por_producto[pid] = {
                    "nombre": it.get("producto") or f"Producto {pid}",
                    "cantidad": 0,
                    "total": 0.0,
                }
            por_producto[pid]["cantidad"] += int(it["cantidad"])
            por_producto[pid]["total"] += float(it["subtotal"])

        fecha = v["fecha"]
        dia = dias.setdefault(fecha, {"total": 0.0, "garrafas": 0, "ventas": 0})
        dia["total"] += float(v["total"])
        dia["garrafas"] += int(v["cantidad"])
        dia["ventas"] += 1

        for pg in v["pagos"]:
            clave = CLAVE_MEDIO.get(pg["medio"], "efectivo")
            medios[clave] += float(pg["importe"])
            if pg["medio"] == "Transferencia":
                n_transferencias += 1
                transferencias.append({
                    "id": v["id"],
                    "fecha": v.get("fecha"),
                    "fecha_hora": v["fecha_hora"],
                    "comprobante": pg.get("comprobante") or "",
                    "producto": v["producto"],
                    "cantidad": v["cantidad"],
                    "total": float(pg["importe"]),
                    "medio": pg["medio"],
                })

        total_vendido += float(v["total"])
        total_garrafas += int(v["cantidad"])

    evolucion = [
        {"fecha": f, **dias[f]} for f in sorted(dias)
    ]

    return {
        "desde": desde,
        "hasta": hasta,
        "cantidad_ventas": len(ventas),
        "total_garrafas": total_garrafas,
        "total_vendido": total_vendido,
        "por_producto": por_producto,
        "efectivo": medios["efectivo"],
        "transferencias": medios["transferencias"],
        "debito": medios["debito"],
        "credito": medios["credito"],
        "n_transferencias": n_transferencias,
        "transferencias_lista": transferencias,
        "evolucion": evolucion,
        "cierres": cierres_rango(desde, hasta),
        "dias_con_ventas": len(dias),
    }


# ---------------------------------------------------------------------------
# Arqueo de efectivo
# ---------------------------------------------------------------------------

def calcular_arqueo(conteo):
    """conteo: dict {denominacion: cantidad}. Devuelve lista de filas y total."""
    filas = []
    total = 0
    for denom in DENOMINACIONES:
        cant = int(conteo.get(denom, 0) or 0)
        subtotal = denom * cant
        filas.append(
            {"denominacion": denom, "cantidad": cant, "subtotal": subtotal}
        )
        total += subtotal
    return filas, total


def clasificar_diferencia(diferencia):
    """Devuelve (estado, etiqueta) según la diferencia contado - esperado."""
    if diferencia > 0:
        return "Sobrante", "SOBRANTE"
    if diferencia < 0:
        return "Faltante", "FALTANTE"
    return "Cuadrada", "CAJA CUADRADA"


# ---------------------------------------------------------------------------
# Cierres
# ---------------------------------------------------------------------------

def guardar_cierre(caja_id, *, total_garrafas, total_vendido, efectivo_esperado,
                   efectivo_contado, transferencias, debito, credito, bono,
                   total_general, diferencia, estado, billetes,
                   n_transferencias=0, cerrado_por=None):
    caja = get_caja_por_id(caja_id)
    if not caja:
        raise ValueError("La caja indicada no existe.")

    u = usuario_sesion() if cerrado_por is None else usuario_por_id(cerrado_por)
    hora = datetime.now().strftime("%H:%M:%S")
    with db() as con:
        # Operaciones y comprobantes de la caja, para el registro del cierre.
        # Una operación = un ticket (aunque tenga varios productos o varios
        # medios de pago); los comprobantes salen de los pagos con
        # transferencia.
        filas = con.execute(
            "SELECT id FROM ventas WHERE caja_id = ?", (caja_id,)
        ).fetchall()
        n_operaciones = len(filas)
        trans = con.execute(
            "SELECT p.comprobante FROM venta_pagos p "
            "JOIN ventas v ON v.id = p.venta_id "
            "WHERE v.caja_id = ? AND p.medio = 'Transferencia' "
            "ORDER BY p.id",
            (caja_id,),
        ).fetchall()
        comprobantes = ", ".join(
            (t["comprobante"] or "—") for t in trans
        )

        # Si había un cierre previo activo, se marca como reabierto/anulado
        con.execute(
            "UPDATE cierres SET activo = 0 WHERE caja_id = ? AND activo = 1",
            (caja_id,),
        )
        con.execute(
            """
            INSERT INTO cierres (caja_id, fecha, hora_cierre, total_garrafas,
                total_vendido, efectivo_esperado, efectivo_contado, transferencias,
                debito, credito, bono, total_general, diferencia, estado, billetes,
                activo, reabierta, n_transferencias, cerrado_por, n_operaciones,
                comprobantes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, ?)
            """,
            (
                caja_id,
                caja["fecha"],
                hora,
                int(total_garrafas),
                float(total_vendido),
                float(efectivo_esperado),
                float(efectivo_contado),
                float(transferencias),
                float(debito),
                float(credito),
                float(bono),
                float(total_general),
                float(diferencia),
                estado,
                json.dumps(billetes, ensure_ascii=False),
                int(n_transferencias),
                u["id"] if u else None,
                n_operaciones,
                comprobantes or None,
            ),
        )
        con.execute("UPDATE cajas SET estado = 'cerrada' WHERE id = ?", (caja_id,))

    log_actividad(
        "Cierre de caja",
        f"Caja del {fecha_larga(caja['fecha'])} — total "
        f"${total_general:,.0f}".replace(",", ".") +
        f" — diferencia ${diferencia:,.0f}".replace(",", ".") +
        f" — {estado} — {n_operaciones} operaciones",
        u,
    )
    return hora


def _cargar_cierre(fila):
    dato = dict(fila)
    try:
        dato["billetes_dict"] = json.loads(dato.get("billetes") or "{}")
    except (TypeError, ValueError):
        dato["billetes_dict"] = {}
    return dato


def get_cierre_activo(caja_id):
    with db() as con:
        fila = con.execute(
            """
            SELECT c.*, caja_id AS cid,
                   COALESCE(u.usuario, '(usuario eliminado)') AS cerrado_por_nombre
            FROM cierres c
            LEFT JOIN usuarios u ON u.id = c.cerrado_por
            WHERE c.caja_id = ? AND c.activo = 1
            """,
            (caja_id,),
        ).fetchone()
    if not fila:
        return None
    return _cargar_cierre(fila)


def historial_cierres():
    """Cierres vigentes (sin contar los anulados por reapertura)."""
    with db() as con:
        filas = con.execute(
            """
            SELECT c.*, caja_id AS cid,
                   COALESCE(u.usuario, '(usuario eliminado)') AS cerrado_por_nombre
            FROM cierres c
            LEFT JOIN usuarios u ON u.id = c.cerrado_por
            WHERE c.activo = 1
            ORDER BY c.fecha DESC
            """
        ).fetchall()
    return [_cargar_cierre(f) for f in filas]


def reabrir_caja(caja_id):
    """Anula el cierre vigente y devuelve la caja a estado 'abierta'."""
    caja = get_caja_por_id(caja_id)
    with db() as con:
        con.execute(
            "UPDATE cierres SET activo = 0, reabierta = 1 WHERE caja_id = ? AND activo = 1",
            (caja_id,),
        )
        con.execute("UPDATE cajas SET estado = 'abierta' WHERE id = ?", (caja_id,))
    log_actividad(
        "Reapertura de caja",
        f"Caja del {fecha_larga(caja['fecha']) if caja else '?'} reabierta",
    )


def cierre_pendiente():
    """True si existe alguna caja sin cerrar (de hoy u otro día)."""
    return len(cajas_abiertas()) > 0


# ---------------------------------------------------------------------------
# Rendiciones (planilla por buzón)
# ---------------------------------------------------------------------------

def guardar_rendicion(fecha, datos, *, loguear=True):
    """Guarda (o actualiza) la rendición de un día.

    `datos` es un dict con todo lo cargado en la pestaña CARGA / RENDICIÓN
    y el conteo de billetes de la calculadora: se serializa a JSON para que
    la tabla no tenga que migrar cada vez que aparece un campo nuevo.
    Hay un único registro por fecha.
    """
    if not fecha:
        raise ValueError("La rendición necesita una fecha.")
    texto = json.dumps(datos if isinstance(datos, dict) else {},
                       ensure_ascii=False)
    marca = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with db() as con:
        previo = con.execute(
            "SELECT id FROM rendiciones WHERE fecha = ?", (fecha,)
        ).fetchone()
        if previo:
            con.execute(
                "UPDATE rendiciones SET datos = ?, actualizada = ? "
                "WHERE fecha = ?",
                (texto, marca, fecha),
            )
        else:
            con.execute(
                "INSERT INTO rendiciones (fecha, datos, actualizada) "
                "VALUES (?, ?, ?)",
                (fecha, texto, marca),
            )
    if loguear:
        log_actividad("Rendición",
                      f"Rendición del {fecha_larga(fecha)} guardada")
    return rendicion_de(fecha)


def rendicion_de(fecha):
    """Rendición guardada de una fecha (dict vacío si todavía no hay)."""
    if not fecha:
        return {}
    with db() as con:
        fila = con.execute(
            "SELECT datos FROM rendiciones WHERE fecha = ?", (fecha,)
        ).fetchone()
    if not fila or not fila[0]:
        return {}
    try:
        datos = json.loads(fila[0])
    except (TypeError, ValueError):
        return {}
    return datos if isinstance(datos, dict) else {}


def rendiciones():
    """Todas las rendiciones guardadas, de la más nueva a la más vieja."""
    with db() as con:
        filas = con.execute(
            "SELECT fecha, datos, actualizada FROM rendiciones "
            "ORDER BY fecha DESC"
        ).fetchall()
    out = []
    for f in filas:
        try:
            datos = json.loads(f["datos"]) if f["datos"] else {}
        except (TypeError, ValueError):
            datos = {}
        out.append({"fecha": f["fecha"],
                    "datos": datos if isinstance(datos, dict) else {},
                    "actualizada": f["actualizada"]})
    return out


def borrar_rendicion(fecha):
    """Quita la rendición guardada de una fecha (para recargarla de cero)."""
    with db() as con:
        con.execute("DELETE FROM rendiciones WHERE fecha = ?", (fecha,))
